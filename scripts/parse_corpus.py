#!/usr/bin/env python3
"""
Stage 1 - Syntactic Parse (The Grammatical Analyzer)

Runs the spaCy English model over Alice in Wonderland and extracts, per
paragraph, the semantic components the downstream stages need:
  - lemma
  - coarse part of speech
  - morphological tense / aspect
  - dependency head and relation
  - noun-number (singular/plural)
  - negation state

Output: data/processed/alice_parsed.jsonl
        (one JSON object per paragraph with its token graph)
"""
import json
import os

import spacy

RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))
PROC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))
ALICE_TXT = os.path.join(RAW_DIR, "alice_wonderland.txt")
OUT_PATH = os.path.join(PROC_DIR, "alice_parsed.jsonl")

MODEL = "en_core_web_sm"


def load_paragraphs(path: str) -> list[str]:
    """Read the Gutenberg text and split into non-empty paragraphs."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    # TODO: optionally strip the Gutenberg header/footer boilerplate here.
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return paragraphs


def token_graph(tok) -> dict:
    """Reduce a spaCy token to the fields the translation stages consume."""
    morph = tok.morph.to_dict()
    return {
        "text": tok.text,
        "lemma": tok.lemma_.lower(),
        "pos": tok.pos_,                       # coarse POS (VERB, NOUN, PROPN, ...)
        "tense": morph.get("Tense"),           # Past / Pres / Fut
        "aspect": morph.get("Aspect"),         # Prog, Perf, ...
        "number": morph.get("Number"),         # Sing / Plur
        "is_negated": tok.dep_ == "neg",
        "head": tok.head.lemma_.lower(),
        "dep": tok.dep_,
    }


def main() -> None:
    if not os.path.exists(ALICE_TXT):
        raise SystemExit(
            f"Source text not found at {ALICE_TXT}. "
            "Run `scripts/download_data.py` first."
        )
    os.makedirs(PROC_DIR, exist_ok=True)

    print(f"Loading spaCy model '{MODEL}' ...")
    nlp = spacy.load(MODEL)

    paragraphs = load_paragraphs(ALICE_TXT)
    print(f"Parsed {len(paragraphs)} paragraphs from Alice in Wonderland.")

    with open(OUT_PATH, "w", encoding="utf-8") as out:
        for i, para in enumerate(paragraphs):
            doc = nlp(para)
            record = {
                "paragraph_id": i,
                "text": para,
                "tokens": [token_graph(t) for t in doc if not t.is_space],
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote parsed corpus -> {OUT_PATH}")


if __name__ == "__main__":
    main()
