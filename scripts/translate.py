#!/usr/bin/env python3
"""
Stages 2 & 3 - Lexical Mapping + Visual Assembly

Consumes:
  - data/processed/alice_parsed.jsonl   (Stage 1 output)
  - data/processed/bliss_lexicon.json   (canonical BCI entries by id)
  - data/processed/lemma_index.json     (lemma -> bci_id reverse index)
  - data/lexicon/disambiguation_rules.json (optional WSD seed rules)

Per token, resolves the lemma to a BCI-AV concept (with word-sense
disambiguation), then applies the morphosyntactic assembly rules from the
Translation Specification:

  * Proper nouns  -> semantic neologism inside COMBINE markers (fallback:
                     transliteration inside NAME INDICATOR).
  * Verbs         -> base glyph + ACTION indicator (+ PAST / CONTINUOUS);
                     negated verbs wrapped with NOT (BCI 15733).
  * Plural nouns  -> base glyph + PLURAL indicator.
  * Unmapped terms-> flagged for human review / composite construction.

Negation (T-507): Bliss negation is a modifier, not a token. A negated verb is
prefixed with the Bliss NOT glyph (bci_id 15733: 'minus + intensity, also used
before a verb to create a negative sentence'); full clause inversion can use
the OPPOSITE indicator (bci_id 15927).

Outputs a draft Bliss-Unicode sequence per paragraph plus a coverage summary.
Output: data/processed/alice_translated.jsonl
"""
import json
import os
from collections import Counter

PROC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))
LEXICON_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "lexicon"))
PARSED_PATH = os.path.join(PROC_DIR, "alice_parsed.jsonl")
LEXICON_PATH = os.path.join(PROC_DIR, "bliss_lexicon.json")
INDEX_PATH = os.path.join(PROC_DIR, "lemma_index.json")
WSD_PATH = os.path.join(LEXICON_DIR, "disambiguation_rules.json")
OUT_PATH = os.path.join(PROC_DIR, "alice_translated.jsonl")

# Token role classification by spaCy coarse POS.
CONTENT_POS = {"NOUN", "VERB", "ADJ", "ADV", "PROPN", "NUM", "INTJ"}
FUNCTION_POS = {"PRON", "DET", "ADP", "CCONJ", "SCONJ", "PART", "AUX"}
PUNCT_POS = {"PUNCT", "SYM", "SPACE"}

# Verified BCI ids for grammatical indicators (resolved from BCI-AV 2025-02-15).
BCI_NOT = "15733"            # 'not' — minus + intensity; prefixed before a verb
BCI_OPPOSITE = "15927"       # 'opposite meaning' — up+down antonym wrapper
BCI_ACTION_HINT = None       # TODO: resolve action-indicator id from BlissFont Unibliss

# Placeholder codepoints until BlissFont's Unibliss.txt scalar assignment lands.
COMBINE_MARKER = "\u275e"
ACTION_INDICATOR = "\u1dc7"
PAST_INDICATOR = "\u1dc6"
CONTINUOUS_INDICATOR = "\u1dc8"
PLURAL_INDICATOR = "\u1dc5"

# Descriptive neologisms for Alice proper nouns (lemma -> concept components).
# NOTE: 'dream' is not in BCI-AV; 'fancy'/'imagination' also absent — pending a
# curated concept or transliteration fallback (T-402/T-403).
PROPER_NOUN_NEologISMS = {
    "alice": ["girl"],
    "hatter": ["man", "hat"],
    "gryphon": ["bird", "animal"],
    "rabbit": ["rabbit"],
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_wsd(path):
    if not os.path.exists(path):
        return {}
    data = load_json(path)
    # Drop the `_meta` documentation key so it's not treated as a lemma rule.
    data.pop("_meta", None)
    return data


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
    """Wrap a sequence of BCI components in COMBINE markers."""
    gloss_parts = []
    for cid in component_ids:
        e = lexicon.get(cid)
        gloss_parts.append(e["gloss_en"] if e else f"?({cid})")
    return (COMBINE_MARKER + "".join(f"[{c}]" for c in component_ids) + COMBINE_MARKER,
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
    if pos == "PROPN" and lemma in PROPER_NOUN_NEologISMS:
        comp = PROPER_NOUN_NEologISMS[lemma]
        uni, gloss = assemble_neologism(comp, lexicon)
        return {"lemma": lemma, "resolved_referent": tok.get("resolved_referent"),
                "type": "Compound", "unicode": uni, "gloss": gloss,
                "bci_id": None, "review": False, "role": "content"}

    # T-405: word-sense disambiguation takes precedence over naive lookup.
    wsd_id, meta = apply_wsd(lemma, sentence_text, wsd_rules)
    if wsd_id is not None:
        entry = lexicon.get(wsd_id)
        if entry:
            base, gloss = wsd_id, entry["gloss_en"]
            sense_note = meta.get("sense", "")
            return _assemble(base, gloss, pos, tok, lexicon,
                             {"sense": sense_note, "wsd": True})

    # WSD may declare a composite sense (bci_id null with derivation_components).
    if wsd_id is None and meta.get("derivation_components"):
        uni, gloss = assemble_neologism(meta["derivation_components"], lexicon)
        return {"lemma": lemma, "resolved_referent": tok.get("resolved_referent"),
                "type": "Compound", "unicode": uni, "gloss": gloss,
                "bci_id": None, "review": True, "role": "content",
                "review_reason": f"composite sense: {meta.get('sense','')}"}


    # Direct lexical lookup.
    entry, lmeta = entry_for(lexicon, index, lemma)
    if entry is None:
        return {"lemma": lemma, "resolved_referent": tok.get("resolved_referent"),
                "type": "Unknown", "unicode": "", "gloss": f"Unmapped({lemma})",
                "bci_id": None, "review": True, "role": "content",
                "review_reason": "no BCI match"}

    base, gloss = entry["bci_id"], entry["gloss_en"]
    return _assemble(base, gloss, pos, tok, lexicon, lmeta)


def _assemble(base, gloss, pos, tok, lexicon, meta) -> dict:
    """Apply morphosyntactic indicators to a resolved base glyph."""
    review_reason = None

    # T-507: negation scoping — prefix NOT before a negated verb.
    if pos in ("VERB", "AUX") and tok.get("is_negated"):
        base = f"[{BCI_NOT}]{base}"
        gloss = "NOT + " + gloss

    if pos in ("VERB", "AUX"):
        # TODO: replace placeholder indicator once BlissFont Unibliss lands.
        base += ACTION_INDICATOR
        gloss += " + [Verb]"
        if tok.get("tense") == "Past":
            base += PAST_INDICATOR
            gloss += " + [Past]"
        elif tok.get("aspect") == "Prog":
            base += CONTINUOUS_INDICATOR
            gloss += " + [Continuous]"
    elif pos == "NOUN" and tok.get("number") == "Plur":
        base += PLURAL_INDICATOR
        gloss += " + [Plural]"

    return {"lemma": tok["lemma"], "resolved_referent": tok.get("resolved_referent"),
            "type": meta.get("category", "Base Spacing"),
            "unicode": base, "gloss": gloss,
            "bci_id": meta, "review": False, "review_reason": review_reason,
            "role": "content"}


def main() -> None:
    for required in (PARSED_PATH, LEXICON_PATH, INDEX_PATH):
        if not os.path.exists(required):
            raise SystemExit(
                f"Missing {required}. Run parse_corpus.py and build_lexicon.py first."
            )

    lexicon = load_json(LEXICON_PATH)
    index = load_json(INDEX_PATH)
    wsd_rules = load_wsd(WSD_PATH)
    if wsd_rules:
        print(f"Loaded WSD rules for: {list(wsd_rules.keys())}")

    total = 0
    outcomes = Counter()           # by role: content / function / punct
    content_review = 0
    content_total = 0

    with open(PARSED_PATH, "r", encoding="utf-8") as src, \
         open(OUT_PATH, "w", encoding="utf-8") as out:
        for line in src:
            para = json.loads(line)
            sentence_text = para["text"]
            translated = [translate_token(lexicon, index, wsd_rules,
                                          sentence_text, t)
                          for t in para["tokens"]]
            for t in translated:
                total += 1
                role = t.get("role", "content")
                outcomes[role] += 1
                if role == "content":
                    content_total += 1
                    if t["review"]:
                        content_review += 1
            out.write(json.dumps({
                "paragraph_id": para["paragraph_id"],
                "text": para["text"],
                "translation": translated,
            }, ensure_ascii=False) + "\n")

    print(f"Wrote draft translations -> {OUT_PATH}")
    # T-307: coverage report.
    content_mapped = content_total - content_review
    content_cov = (content_mapped / content_total * 100) if content_total else 0.0
    print(f"Tokens: {total} | content: {content_total} "
          f"| function: {outcomes.get('function',0)} "
          f"| punct: {outcomes.get('punct',0)}")
    print(f"Content coverage: {content_mapped}/{content_total} "
          f"({content_cov:.1f}%) | flagged for review: {content_review}")


if __name__ == "__main__":
    main()
