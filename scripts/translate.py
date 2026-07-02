#!/usr/bin/env python3
"""
Stages 2 & 3 - Lexical Mapping + Visual Assembly

Consumes:
  - data/processed/alice_parsed.jsonl        (Stage 1 output)
  - data/processed/bliss_lexicon.json        (canonical BCI entries by id)
  - data/processed/lemma_index.json          (lemma -> bci_id reverse index)
  - data/processed/bliss_unicode_map.json    (bci_id -> char, from BlissFont)
  - data/lexicon/disambiguation_rules.json   (optional WSD seed rules)

Per token, resolves the lemma to a BCI-AV concept (with word-sense
disambiguation), then applies the morphosyntactic assembly rules from the
Translation Specification. Glyphs are rendered to Unicode via the BlissFont
map when available; unmapped ids appear as `[bci_id]` placeholders.

  * Proper nouns -> semantic neologism inside COMBINE markers (13382).
  * Verbs        -> base glyph + action indicator (8993) (+ past 9004 /
                    continuous 28043); negated verbs prefixed with NOT (15733).
  * Plural nouns -> base glyph + plural indicator (27112).
  * Unmapped     -> flagged for human review / composite construction.

Output: data/processed/alice_translated.jsonl
"""
import json
import os
from collections import Counter

PROC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))
LEXICON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "lexicon"))
SCRIPTS = os.path.dirname(os.path.abspath(__file__))
PARSED_PATH = os.path.join(PROC_DIR, "alice_parsed.jsonl")
LEXICON_PATH = os.path.join(PROC_DIR, "bliss_lexicon.json")
INDEX_PATH = os.path.join(PROC_DIR, "lemma_index.json")
UNICODE_MAP_PATH = os.path.join(PROC_DIR, "bliss_unicode_map.json")
WSD_PATH = os.path.join(LEXICON_DIR, "disambiguation_rules.json")
NEOLOGISMS_PATH = os.path.join(LEXICON_DIR, "neologisms.json")
OUT_PATH = os.path.join(PROC_DIR, "alice_translated.jsonl")

# Verified BCI ids for grammatical indicators (from BCI-AV 2025-02-15).
BCI_COMBINE_MARKER = "13382"        # 'combine marker'
BCI_NOT = "15733"                   # 'not' — minus + intensity; before a verb
BCI_OPPOSITE = "15927"              # 'opposite meaning' — antonym wrapper
BCI_ACTION_INDICATOR = "8993"       # 'indicator (action)'
BCI_PAST_INDICATOR = "9004"         # 'indicator (past action)'
BCI_CONTINUOUS_INDICATOR = "28043"  # 'indicator (continuous form)'
BCI_PLURAL_INDICATOR = "27112"      # 'plural'

# Token role classification by spaCy coarse POS.
CONTENT_POS = {"NOUN", "VERB", "ADJ", "ADV", "PROPN", "NUM", "INTJ"}
FUNCTION_POS = {"PRON", "DET", "ADP", "CCONJ", "SCONJ", "PART", "AUX"}
PUNCT_POS = {"PUNCT", "SYM", "SPACE"}

# bci_id -> unicode char. Populated by main() via load_blissfont; empty default
# means all glyphs render as `[bci_id]` placeholders (used by tests).
_UNICODE_MAP: dict[str, str] = {}


def render(bci_id: str) -> str:
    """Unicode char for a BCI id, or a `[bci_id]` placeholder if unmapped."""
    return _UNICODE_MAP.get(bci_id, f"[{bci_id}]")


# Proper-noun neologism registry: lemma -> {components, gloss, note}.
# Loaded from data/lexicon/neologisms.json in main(); the default below is a
# minimal fallback used when the file is absent (e.g. in unit tests).
_PROPER_NOUN_NEologISMS: dict[str, dict] = {
    "alice": {"components": ["14439"], "gloss": "the dreaming girl"},
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_wsd(path):
    if not os.path.exists(path):
        return {}
    data = load_json(path)
    data.pop("_meta", None)
    return data


def load_unicode_map() -> dict[str, str]:
    """Populate the module-level map from cache or BlissFont (T-701/T-702)."""
    global _UNICODE_MAP
    if os.path.exists(UNICODE_MAP_PATH):
        cache = load_json(UNICODE_MAP_PATH)
        _UNICODE_MAP = {bid: chr(int(cp[2:], 16)) for bid, cp in cache.items()
                        if str(cp).startswith("U+")}
        return _UNICODE_MAP
    # No cache yet: import the loader and build it live.
    import sys
    sys.path.insert(0, SCRIPTS)
    import load_blissfont  # noqa: WPS433
    _UNICODE_MAP = load_blissfont.build_unicode_map()
    return _UNICODE_MAP


def apply_wsd(lemma: str, sentence_text: str, wsd_rules: dict) -> tuple[str | None, dict]:
    """
    T-405: return (resolved_bci_id_or_None, rule_meta) for an ambiguous lemma.
    First matching context rule wins. Returns (None, {}) if no rules apply.
    """
    rule = wsd_rules.get(lemma)
    if not rule:
        return None, {}
    hay = sentence_text.lower()
    for cr in rule.get("context_rules", []):
        if any(kw in hay for kw in cr.get("trigger_keywords", [])):
            meta = {
                "sense": cr.get("sense_description", ""),
                "wsd_rule": True,
                "derivation_components": cr.get("derivation_components"),
                "derivation_note": cr.get("derivation_note"),
            }
            return cr.get("bci_id"), meta
    return rule.get("default_bci_id"), {"sense": rule.get("default_note", ""), "wsd_default": True}


def entry_for(lexicon, index, lemma):
    """Direct lemma lookup -> (entry, meta). Returns (None, {}) if absent."""
    bci_id = index.get(lemma)
    if not bci_id:
        return None, {}
    return lexicon.get(bci_id), {"lookup": "direct"}


def assemble_neologism(component_ids: list[str], lexicon: dict) -> tuple[str, str]:
    """Wrap a sequence of BCI components in COMBINE markers (13382)."""
    gloss_parts, rendered = [], []
    for cid in component_ids:
        e = lexicon.get(cid)
        gloss_parts.append(e["gloss_en"] if e else f"?({cid})")
        rendered.append(render(cid))
    cm = render(BCI_COMBINE_MARKER)
    return (cm + "".join(rendered) + cm,
            "[Combine] " + " + ".join(gloss_parts) + " [Combine]")


def translate_token(lexicon, index, wsd_rules, sentence_text, tok) -> dict:
    lemma = tok["lemma"]
    pos = tok["pos"]

    # Punctuation / symbols pass through verbatim, never flagged.
    if pos in PUNCT_POS:
        return {"lemma": tok["text"], "resolved_referent": tok.get("resolved_referent"),
                "type": "Punctuation", "unicode": tok["text"], "gloss": "[punct]",
                "bci_id": None, "review": False, "role": "punct"}

    # Function words are handled by grammatical indicators / coref / spatial
    # markers, not standalone glyphs. Record but don't burden the review queue.
    if pos in FUNCTION_POS:
        return {"lemma": lemma, "resolved_referent": tok.get("resolved_referent"),
                "type": "Function", "unicode": "", "gloss": f"[{pos.lower()}]",
                "bci_id": None, "review": False, "role": "function"}

    # Proper nouns -> semantic neologism.
    entry = _PROPER_NOUN_NEologISMS.get(lemma)
    if pos == "PROPN" and entry:
        uni, comp_gloss = assemble_neologism(entry["components"], lexicon)
        gloss = f"[{entry.get('gloss', lemma)}] {comp_gloss}"
        return {"lemma": lemma, "resolved_referent": tok.get("resolved_referent"),
                "type": "Compound", "unicode": uni, "gloss": gloss,
                "bci_id": BCI_COMBINE_MARKER, "review": False, "role": "content"}

    # T-405: word-sense disambiguation takes precedence over naive lookup.
    wsd_id, meta = apply_wsd(lemma, sentence_text, wsd_rules)
    if wsd_id is not None:
        entry = lexicon.get(wsd_id)
        if entry:
            return _assemble(wsd_id, entry["gloss_en"], pos, tok,
                             {"sense": meta.get("sense", ""), "wsd": True})

    # WSD may declare a composite sense (bci_id null with derivation_components).
    if wsd_id is None and meta.get("derivation_components"):
        uni, gloss = assemble_neologism(meta["derivation_components"], lexicon)
        return {"lemma": lemma, "resolved_referent": tok.get("resolved_referent"),
                "type": "Compound", "unicode": uni, "gloss": gloss,
                "bci_id": BCI_COMBINE_MARKER, "review": True, "role": "content",
                "review_reason": f"composite sense: {meta.get('sense', '')}"}

    # Direct lexical lookup.
    entry, lmeta = entry_for(lexicon, index, lemma)
    if entry is None:
        return {"lemma": lemma, "resolved_referent": tok.get("resolved_referent"),
                "type": "Unknown", "unicode": "", "gloss": f"Unmapped({lemma})",
                "bci_id": None, "review": True, "role": "content",
                "review_reason": "no BCI match"}

    return _assemble(entry["bci_id"], entry["gloss_en"], pos, tok, lmeta)


def _assemble(base_id, gloss, pos, tok, meta) -> dict:
    """Apply morphosyntactic indicators to a resolved base glyph id."""
    parts: list[str] = [base_id]

    # T-507: negation scoping — prefix NOT before a negated verb.
    if pos in ("VERB", "AUX") and tok.get("is_negated"):
        parts.insert(0, BCI_NOT)
        gloss = "NOT + " + gloss

    if pos in ("VERB", "AUX"):
        parts.append(BCI_ACTION_INDICATOR)
        gloss += " + [Verb]"
        if tok.get("tense") == "Past":
            parts.append(BCI_PAST_INDICATOR)
            gloss += " + [Past]"
        elif tok.get("aspect") == "Prog":
            parts.append(BCI_CONTINUOUS_INDICATOR)
            gloss += " + [Continuous]"
    elif pos == "NOUN" and tok.get("number") == "Plur":
        parts.append(BCI_PLURAL_INDICATOR)
        gloss += " + [Plural]"

    unicode_out = "".join(render(p) for p in parts)
    return {"lemma": tok["lemma"], "resolved_referent": tok.get("resolved_referent"),
            "type": meta.get("category", "Base Spacing"),
            "unicode": unicode_out, "gloss": gloss,
            "bci_id": base_id, "review": False, "review_reason": None,
            "role": "content"}


def main() -> None:
    global _PROPER_NOUN_NEologISMS
    for required in (PARSED_PATH, LEXICON_PATH, INDEX_PATH):
        if not os.path.exists(required):
            raise SystemExit(
                f"Missing {required}. Run parse_corpus.py and build_lexicon.py first."
            )

    lexicon = load_json(LEXICON_PATH)
    index = load_json(INDEX_PATH)
    wsd_rules = load_wsd(WSD_PATH)
    umap = load_unicode_map()
    if os.path.exists(NEOLOGISMS_PATH):
        neo = load_json(NEOLOGISMS_PATH)
        neo.pop("_meta", None)
        _PROPER_NOUN_NEologISMS = neo
    if wsd_rules:
        print(f"Loaded WSD rules for: {list(wsd_rules.keys())}")
    print(f"Loaded neologism registry: {len(_PROPER_NOUN_NEologISMS)} proper nouns")
    print(f"Unicode map: {len(umap)} glyphs (from BlissFont)")

    total = 0
    outcomes = Counter()
    content_review = 0
    content_total = 0
    rendered_glyphs = 0

    with open(PARSED_PATH, "r", encoding="utf-8") as src, \
         open(OUT_PATH, "w", encoding="utf-8") as out:
        for line in src:
            para = json.loads(line)
            out_sentences = []
            for sent in para.get("sentences", []):
                sentence_text = sent["text"]
                translated = [translate_token(lexicon, index, wsd_rules,
                                              sentence_text, t)
                              for t in sent["tokens"]]
                for t in translated:
                    total += 1
                    role = t.get("role", "content")
                    outcomes[role] += 1
                    if role == "content":
                        content_total += 1
                        if t["review"]:
                            content_review += 1
                        elif t["unicode"] and not t["unicode"].startswith("["):
                            rendered_glyphs += 1
                out_sentences.append({
                    "sentence_index": sent["sentence_index"],
                    "text": sentence_text,
                    "translation": translated,
                })
            out.write(json.dumps({
                "paragraph_id": para["paragraph_id"],
                "text": para["text"],
                "sentences": out_sentences,
            }, ensure_ascii=False) + "\n")

    print(f"Wrote draft translations -> {OUT_PATH}")
    content_mapped = content_total - content_review
    content_cov = (content_mapped / content_total * 100) if content_total else 0.0
    render_rate = (rendered_glyphs / content_mapped * 100) if content_mapped else 0.0
    print(f"Tokens: {total} | content: {content_total} "
          f"| function: {outcomes.get('function', 0)} "
          f"| punct: {outcomes.get('punct', 0)}")
    print(f"Content coverage: {content_mapped}/{content_total} ({content_cov:.1f}%) "
          f"| flagged: {content_review}")
    print(f"Rendered to real Unicode: {rendered_glyphs}/{content_mapped} "
          f"({render_rate:.1f}% of mapped content tokens)")


if __name__ == "__main__":
    main()
