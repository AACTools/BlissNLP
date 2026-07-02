#!/usr/bin/env python3
"""
Stage 1 - Syntactic Parse (The Grammatical Analyzer)

Runs the spaCy English model over Alice in Wonderland and extracts, per
paragraph, the semantic components the downstream stages need:
  - lemma, coarse POS, morphological tense/aspect
  - noun number, dependency head and relation
  - resolved_referent (anaphora/coref target) — T-208
  - clause-level negation flag on the verb head — feeds T-507

Gutenberg boilerplate (header/footer licence text) is stripped before parsing
using the standard `*** START/END OF ... ***` markers.

Output: data/processed/alice_parsed.jsonl
"""
import json
import os
import re

import spacy

RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))
PROC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))
ALICE_TXT = os.path.join(RAW_DIR, "alice_wonderland.txt")
OUT_PATH = os.path.join(PROC_DIR, "alice_parsed.jsonl")

MODEL = "en_core_web_sm"

_START_RE = re.compile(r"\*\*\*\s*START OF.*?\*\*\*", re.IGNORECASE | re.DOTALL)
_END_RE = re.compile(r"\*\*\*\s*END OF.*?\*\*\*", re.IGNORECASE | re.DOTALL)


def strip_gutenberg_boilerplate(text: str) -> str:
    """Remove the Project Gutenberg header/footer, keeping only the novel body."""
    start = _START_RE.search(text)
    if start:
        text = text[start.end():]
    # Search END *after* the start slice so indices are valid for this text.
    end = _END_RE.search(text)
    if end:
        text = text[: end.start()]
    return text.strip()


def load_paragraphs(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    body = strip_gutenberg_boilerplate(text)
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    return paragraphs


def negated_verbs(doc) -> set[int]:
    """Return token indices of verb heads whose subtree contains a `neg` child."""
    heads: set[int] = set()
    for tok in doc:
        if tok.dep_ == "neg" and tok.head.pos_ in ("VERB", "AUX"):
            heads.add(tok.head.i)
    return heads


def token_graph(tok, coref: dict, neg_heads: set[int]) -> dict:
    morph = tok.morph.to_dict()
    referent = coref.get(tok.i)
    is_pron = tok.pos_ == "PRON"
    return {
        "index": tok.i,
        "text": tok.text,
        "lemma": tok.lemma_.lower(),
        "pos": tok.pos_,                       # coarse POS (VERB, NOUN, PROPN, ...)
        "tense": morph.get("Tense"),           # Past / Pres / Fut
        "aspect": morph.get("Aspect"),         # Prog, Perf, ...
        "number": morph.get("Number"),         # Sing / Plur
        "person": morph.get("Person"),
        "is_negated": tok.i in neg_heads,
        "head": tok.head.lemma_.lower(),
        "head_index": tok.head.i,
        "dep": tok.dep_,
        # T-208: anaphora resolution. null until a coref model populates it;
        # pronouns carry the raw lemma as a placeholder referent.
        "resolved_referent": referent if referent is not None
                             else (tok.lemma_.lower() if is_pron else None),
    }


def resolve_coref(doc) -> dict[int, str]:
    """
    T-208 placeholder coreference resolver.

    Returns a {token_index: referent} map. A real implementation will plug in
    `fastcoref` or an LLM-guided pass here. For now this returns an empty map;
    pronouns keep their own lemma as referent downstream.
    """
    # TODO T-208: integrate fastcoref / LLM coref over the doc/paragraph cluster.
    return {}


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
    print(f"Stripped Gutenberg boilerplate; {len(paragraphs)} paragraphs remain.")

    with open(OUT_PATH, "w", encoding="utf-8") as out:
        for i, para in enumerate(paragraphs):
            doc = nlp(para)
            neg_heads = negated_verbs(doc)
            coref = resolve_coref(doc)
            record = {
                "paragraph_id": i,
                "text": para,
                "tokens": [token_graph(t, coref, neg_heads)
                           for t in doc if not t.is_space],
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Wrote parsed corpus -> {OUT_PATH}")


if __name__ == "__main__":
    main()
