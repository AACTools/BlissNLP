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
IDIOMS_PATH = os.path.join(LEXICON_DIR, "idioms.json")
SYNONYMS_PATH = os.path.join(LEXICON_DIR, "synonyms.json")
OUT_PATH = os.path.join(PROC_DIR, "alice_translated.jsonl")

# Verified BCI ids for grammatical indicators (from BCI-AV 2025-02-15).
BCI_COMBINE_MARKER = "13382"        # 'combine marker'
BCI_NAME_INDICATOR = "15691"        # 'name' — NAME INDICATOR for proper nouns
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

# lemma -> bci_id reverse index. Populated by main(); used by T-406 to resolve
# derivation-component glosses back to BCI ids.
_LEMMA_INDEX: dict[str, str] = {}


def render(bci_id: str) -> str:
    """Unicode char for a BCI id, or a `[bci_id]` placeholder if unmapped."""
    return _UNICODE_MAP.get(bci_id, f"[{bci_id}]")


def derivation_composite(base_id: str, lexicon: dict) -> list[str] | None:
    """
    T-406: if `base_id` has no Unicode scalar but its BCI derivation components
    all resolve (via the lemma index) to ids that DO render, return those
    component ids so the token can be emitted as a COMBINE-wrapped composite.
    Returns None when no full composite is possible.
    """
    entry = lexicon.get(base_id)
    if not entry:
        return None
    comp_ids = [_LEMMA_INDEX.get(c) for c in entry.get("derivations", [])
                if _LEMMA_INDEX.get(c)]
    if not comp_ids:
        return None
    # Only fall back when every resolvable component actually renders.
    if all(c in _UNICODE_MAP for c in comp_ids):
        return comp_ids
    return None


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


def load_idioms(path) -> dict:
    """Load idioms as {tuple(lemmas): {components, gloss, note}}."""
    if not os.path.exists(path):
        return {}
    data = load_json(path)
    data.pop("_meta", None)
    return {tuple(k.split()): v for k, v in data.items()}


def match_idiom(idioms: dict, lemmas: list[str], i: int):
    """
    T-404: return (entry, length) if an idiom lemma-run starts at index i,
    else None. Longer idioms take precedence over shorter ones.
    """
    best = None
    for key, entry in idioms.items():
        n = len(key)
        if i + n <= len(lemmas) and tuple(lemmas[i:i + n]) == key:
            if best is None or n > best[1]:
                best = (entry, n)
    return best


def translate_sentence(lexicon, index, wsd_rules, idioms, sent, sentence_text) -> list:
    """Translate a sentence, collapsing idiom lemma-runs into one compound."""
    toks = sent["tokens"]
    lemmas = [t["lemma"] for t in toks]
    out = []
    i = 0
    while i < len(toks):
        m = match_idiom(idioms, lemmas, i)
        if m:
            entry, length = m
            uni, comp_gloss = assemble_neologism(entry["components"], lexicon)
            span_text = " ".join(toks[j]["text"] for j in range(i, i + length))
            out.append({
                "lemma": span_text,
                "resolved_referent": None,
                "type": "Compound",
                "unicode": uni,
                "gloss": f"[idiom: {entry.get('gloss','')}] {comp_gloss}",
                "bci_id": BCI_COMBINE_MARKER,
                "review": False, "review_reason": None, "role": "content",
            })
            i += length
        else:
            out.append(translate_token(lexicon, index, wsd_rules, sentence_text, toks[i]))
            i += 1
    return out


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


# lemma -> BCI gloss-form alias (Gap B fix); populated by main().
_SYNONYMS: dict[str, str] = {}


def entry_for(lexicon, index, lemma):
    """Direct lemma lookup -> (entry, meta). Falls back to the synonym map
    (lemma-form aliases) before giving up. Returns (None, {}) if absent."""
    bci_id = index.get(lemma)
    if not bci_id:
        alias = _SYNONYMS.get(lemma)
        if alias:
            bci_id = index.get(alias)
    if not bci_id:
        return None, {}
    return lexicon.get(bci_id), {"lookup": "synonym" if lemma in _SYNONYMS else "direct"}


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

    # spaCy's "_" lemma is the unknown-lemma placeholder -> parse noise, skip.
    if lemma == "_":
        return {"lemma": lemma, "resolved_referent": tok.get("resolved_referent"),
                "type": "Function", "unicode": "", "gloss": "[unknown-lemma]",
                "bci_id": None, "review": False, "role": "function"}

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

    # Proper nouns -> semantic neologism, else NAME INDICATOR transliteration.
    if pos == "PROPN":
        entry = _PROPER_NOUN_NEologISMS.get(lemma)
        if entry:
            uni, comp_gloss = assemble_neologism(entry["components"], lexicon)
            gloss = f"[{entry.get('gloss', lemma)}] {comp_gloss}"
            return {"lemma": lemma, "resolved_referent": tok.get("resolved_referent"),
                    "type": "Compound", "unicode": uni, "gloss": gloss,
                    "bci_id": BCI_COMBINE_MARKER, "review": False, "role": "content"}
        # T-403: no semantic neologism -> NAME INDICATOR transliteration
        # placeholder, flagged for review (letter glyphs pending BlissFont).
        nm = render(BCI_NAME_INDICATOR)
        return {"lemma": lemma, "resolved_referent": tok.get("resolved_referent"),
                "type": "Transliteration",
                "unicode": f"{nm}{lemma}{nm}",
                "gloss": f"[NAME] {lemma} (transliteration)",
                "bci_id": BCI_NAME_INDICATOR, "review": True, "role": "content",
                "review_reason": "transliteration fallback — coin a neologism"}

    # T-405: word-sense disambiguation takes precedence over naive lookup.
    wsd_id, meta = apply_wsd(lemma, sentence_text, wsd_rules)
    if wsd_id is not None:
        entry = lexicon.get(wsd_id)
        if entry:
            return _assemble(wsd_id, entry["gloss_en"], pos, tok,
                             {"sense": meta.get("sense", ""), "wsd": True}, lexicon)

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

    return _assemble(entry["bci_id"], entry["gloss_en"], pos, tok, lmeta, lexicon)


def _assemble(base_id, gloss, pos, tok, meta, lexicon) -> dict:
    """Apply morphosyntactic indicators to a resolved base glyph id."""
    # T-406: if the base glyph has no scalar, render it as a composite of its
    # derivation components (which may themselves be mapped).
    base_ids: list[str] = [base_id]
    is_composite = False
    if base_id not in _UNICODE_MAP:
        comp = derivation_composite(base_id, lexicon)
        if comp:
            base_ids = [BCI_COMBINE_MARKER] + comp + [BCI_COMBINE_MARKER]
            names = [lexicon[c]["gloss_en"] for c in comp if c in lexicon]
            gloss = f"{gloss} [composite: {' + '.join(names)}]"
            is_composite = True

    parts: list[str] = list(base_ids)

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
            "type": "Compound" if is_composite else meta.get("category", "Base Spacing"),
            "unicode": unicode_out, "gloss": gloss,
            "bci_id": base_id, "review": False, "review_reason": None,
            "role": "content"}


def main() -> None:
    global _PROPER_NOUN_NEologISMS, _LEMMA_INDEX, _SYNONYMS
    for required in (PARSED_PATH, LEXICON_PATH, INDEX_PATH):
        if not os.path.exists(required):
            raise SystemExit(
                f"Missing {required}. Run parse_corpus.py and build_lexicon.py first."
            )

    lexicon = load_json(LEXICON_PATH)
    _LEMMA_INDEX = load_json(INDEX_PATH)
    wsd_rules = load_wsd(WSD_PATH)
    idioms = load_idioms(IDIOMS_PATH)
    _SYNONYMS = load_wsd(SYNONYMS_PATH)  # same shape: dict with _meta to drop
    umap = load_unicode_map()
    if os.path.exists(NEOLOGISMS_PATH):
        neo = load_json(NEOLOGISMS_PATH)
        neo.pop("_meta", None)
        _PROPER_NOUN_NEologISMS = neo
    if wsd_rules:
        print(f"Loaded WSD rules for: {list(wsd_rules.keys())}")
    if idioms:
        print(f"Loaded {len(idioms)} idiom rules")
    if _SYNONYMS:
        print(f"Loaded {len(_SYNONYMS)} lemma synonyms")
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
                translated = translate_sentence(lexicon, _LEMMA_INDEX,
                                                wsd_rules, idioms, sent,
                                                sentence_text)
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
