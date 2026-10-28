"""T-208 heuristic coreference tests."""
import os
import sys

import spacy

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, SCRIPTS)

from parse_corpus import resolve_coref  # noqa: E402

nlp = spacy.load("en_core_web_sm")


def test_she_resolves_to_alice():
    doc = nlp("Alice was beginning to get tired. She peeped into the book.")
    coref = resolve_coref(doc)
    she = next(t for t in doc if t.text == "She")
    assert coref.get(she.i) == "alice"


def test_he_her_disambiguation():
    doc = nlp("Alice met the Hatter. He grinned at her.")
    coref = resolve_coref(doc)
    he = next(t for t in doc if t.text == "He")
    her = next(t for t in doc if t.text == "her")
    assert coref.get(he.i) == "hatter"
    assert coref.get(her.i) == "alice"


def test_recency_prefers_last_mention():
    doc = nlp("The Hatter spoke. Then the Rabbit whispered. He hopped away.")
    coref = resolve_coref(doc)
    he = next(t for t in doc if t.text == "He")
    assert coref.get(he.i) == "rabbit"


def test_unresolvable_pronoun_left_unmapped():
    doc = nlp("It was cloudy.")  # no prior entity
    coref = resolve_coref(doc)
    it = next(t for t in doc if t.text == "It")
    assert it.i not in coref


def test_white_rabbit_grouping():
    doc = nlp("The White Rabbit hurried by. He checked his watch.")
    coref = resolve_coref(doc)
    he = next(t for t in doc if t.text == "He")
    assert coref.get(he.i) == "rabbit"
