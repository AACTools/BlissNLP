#!/usr/bin/env python3
"""
Stages 2 & 3 - Lexical Mapping + Visual Assembly

Consumes:
  - data/processed/alice_parsed.jsonl   (Stage 1 output)
  - data/processed/bliss_lexicon.json   (Stage 2 prep output)

Per token, resolves the lemma to a BCI-AV concept, then applies the
morphosyntactic assembly rules described in the Translation Specification:

  * Proper nouns  -> semantic neologism inside COMBINE markers (fallback:
                     transliteration inside NAME INDICATOR).
  * Verbs          -> base glyph + ACTION indicator (+ PAST / CONTINUOUS).
  * Plural nouns   -> base glyph + PLURAL indicator.
  * Unmapped terms -> flagged for human review.

Outputs a draft Bliss-Unicode sequence per paragraph.
Output: data/processed/alice_translated.jsonl
"""
import json
import os

PROC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))
PARSED_PATH = os.path.join(PROC_DIR, "alice_parsed.jsonl")
LEXICON_PATH = os.path.join(PROC_DIR, "bliss_lexicon.json")
OUT_PATH = os.path.join(PROC_DIR, "alice_translated.jsonl")

# Grammatical indicator codepoints (per L2/23-138 / ISO JTC1/SC2/WG2 N5228).
# These are placeholders pending the final Unibliss assignment from BlissFont.
COMBINE_MARKER = "\u275e"      # enclosing combine marks
ACTION_INDICATOR = "\u1dc7"    # action / verb
PAST_INDICATOR = "\u1dc6"      # past tense
CONTINUOUS_INDICATOR = "\u1dc8"  # continuous aspect
PLURAL_INDICATOR = "\u1dc5"    # plural

# Descriptive neologisms for proper nouns in Alice.
# TODO: expand; ideally sourced from a curated glossary, not hard-coded.
PROPER_NOUN_NEologISMS = {
    "alice": ["girl", "dream"],
    "hatter": ["man", "crazy", "hat"],
    "gryphon": ["animal", "wing"],
}


def load_lexicon(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def lookup(lexicon: dict, lemma: str) -> dict | None:
    return lexicon.get(lemma)


def assemble_neologism(parts: list[str]) -> str:
    return COMBINE_MARKER + "".join(parts) + COMBINE_MARKER


def translate_token(lexicon: dict, tok: dict) -> dict:
    lemma = tok["lemma"]
    pos = tok["pos"]

    # Proper nouns -> semantic neologism.
    if pos == "PROPN" and lemma in PROPER_NOUN_NEologISMS:
        parts = [lookup(lexicon, p) for p in PROPER_NOUN_NEologISMS[lemma]]
        glyphs = [p["bci_id"] for p in parts if p]  # TODO: map bci_id -> unicode
        return {
            "lemma": lemma,
            "type": "Compound",
            "unicode": assemble_neologism("".join(glyphs)),
            "gloss": "[Combine] " + " + ".join(PROPER_NOUN_NEologISMS[lemma]) + " [Combine]",
            "review": False,
        }

    entry = lookup(lexicon, lemma)
    if entry is None:
        return {
            "lemma": lemma,
            "type": "Unknown",
            "unicode": "",
            "gloss": f"Unmapped({lemma})",
            "review": True,
        }

    # TODO: resolve the BCI id to its proposed Unibliss scalar via
    # BlissFont's Unibliss.txt once available.
    base = entry["bci_id"]
    gloss = entry["gloss_en"]

    if pos == "VERB":
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

    return {
        "lemma": lemma,
        "type": entry.get("category", "Base Spacing"),
        "unicode": base,
        "gloss": gloss,
        "review": False,
    }


def main() -> None:
    for required in (PARSED_PATH, LEXICON_PATH):
        if not os.path.exists(required):
            raise SystemExit(
                f"Missing {required}. Run parse_corpus.py and build_lexicon.py first."
            )

    lexicon = load_lexicon(LEXICON_PATH)

    with open(PARSED_PATH, "r", encoding="utf-8") as src, \
         open(OUT_PATH, "w", encoding="utf-8") as out:
        for line in src:
            para = json.loads(line)
            translated = [translate_token(lexicon, t) for t in para["tokens"]]
            out.write(json.dumps({
                "paragraph_id": para["paragraph_id"],
                "text": para["text"],
                "translation": translated,
            }, ensure_ascii=False) + "\n")

    print(f"Wrote draft translations -> {OUT_PATH}")


if __name__ == "__main__":
    main()
