"""Gold-parse regression sample (T-207 / T-801).

Asserts the Stage 1 parse of a known Alice sentence yields the expected
lemmas / POS / morphology, anchoring the pipeline against drift. Uses the
real spaCy model on an inline sentence (no file IO beyond the model load).
"""
import os
import sys

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, SCRIPTS)

import parse_corpus  # noqa: E402


# The opening sentence of Chapter I (after punctuation normalisation).
OPENING = ("Alice was beginning to get very tired of sitting by her sister "
           "on the bank, and of having nothing to do.")


def test_normalize_punctuation_curly_quotes():
    assert parse_corpus.normalize_punctuation("Alice\u2019s \u201cword\u201d") == 'Alice\'s "word"'


def test_strip_gutenberg_round_trip():
    body = parse_corpus.strip_gutenberg_boilerplate(
        "HDR\n*** START OF THESIS GUTENBERG EBOOK ***\nbody\n*** END OF ***\nftr")
    assert body == "body"


def _tokens(text):
    import spacy
    nlp = spacy.load(parse_corpus.MODEL)
    doc = nlp(parse_corpus.normalize_punctuation(text))
    neg = parse_corpus.negated_verbs(doc)
    return [parse_corpus.token_graph(t, {}, neg) for t in doc if not t.is_space]


def test_alice_opening_parse_keys():
    toks = {t["lemma"]: t for t in _tokens(OPENING)}
    # Proper noun resolved as a content token with the right lemma/pos.
    assert toks["alice"]["pos"] == "PROPN"
    # Verb lemmatised and tensed.
    assert toks["begin"]["pos"] in ("VERB", "AUX")
    assert toks["begin"]["tense"] in ("Past", "Pres")
    # "tired" recognised as an adjective.
    assert toks["tired"]["pos"] == "ADJ"
    # "sister" and "bank" are nouns.
    assert toks["sister"]["pos"] == "NOUN"
    assert toks["bank"]["pos"] == "NOUN"


def test_negation_flag_propagates_to_verb_head():
    toks = {t["lemma"]: t for t in _tokens("Alice did not see the rabbit.")}
    # "not" attaches to the lexical verb "see" (ROOT), flagging it.
    assert toks["see"]["is_negated"] is True
    # the auxiliary "did" is not itself the negation target.
    assert toks["do"]["is_negated"] is False


def test_resolved_referent_field_present():
    t = _tokens(OPENING)[0]
    # Field always emitted (null until a coref model populates it).
    assert "resolved_referent" in t
