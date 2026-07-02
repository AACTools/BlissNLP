"""Gold-sample integration test (T-801).

Exercises the Stage 2/3 translation over a hand-built, sentence-structured
parsed record (no file IO) and asserts known-good outputs for the behaviours
that matter most: proper-noun neologism, WSD composite sense, negation
wrapping, and punctuation pass-through. Acts as a regression anchor.
"""
import os
import sys

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, SCRIPTS)

import translate  # noqa: E402

# A miniature lexicon + lemma index grounded in real BCI-AV 2025 ids.
LEXICON = {
    "14439": {"bci_id": "14439", "gloss_en": "girl"},
    "14695": {"bci_id": "14695", "gloss_en": "heart"},
    "23626": {"bci_id": "23626", "gloss_en": "queen"},
    "12640": {"bci_id": "12640", "gloss_en": "beach"},
    "29623": {"bci_id": "29623", "gloss_en": "slope (down)"},
    "16747": {"bci_id": "16747", "gloss_en": "see"},
}
INDEX = {
    "girl": "14439", "heart": "14695", "queen": "23626",
    "see": "16747",
}
WSD = {
    "bank": {
        "default_bci_id": "12626",
        "context_rules": [
            {"bci_id": None, "sense_description": "riverbank",
             "derivation_components": ["12640", "29623"],
             "trigger_keywords": ["sister", "river"]},
        ],
    }
}


def setup_module(module):
    # Map a couple of ids to real chars so we can assert on rendering.
    translate._UNICODE_MAP = {
        "14439": "\U00016330",   # girl
        "13382": "\U00016760",   # combine marker
        "12640": "\U00016688",   # beach
        "16747": "\U00016244",   # see
        "8993": "\U00016001",    # action indicator
    }
    translate._PROPER_NOUN_NEologISMS = {
        "alice": {"components": ["14439"], "gloss": "the dreaming girl"},
    }


def _tok(text, lemma, pos, **extra):
    t = {"text": text, "lemma": lemma, "pos": pos,
         "resolved_referent": None, "is_negated": False,
         "tense": None, "aspect": None, "number": "Sing"}
    t.update(extra)
    return t


def test_alice_renders_as_girl_neologism():
    out = translate.translate_token(LEXICON, INDEX, WSD, "Alice sat",
                                    _tok("Alice", "alice", "PROPN"))
    assert out["type"] == "Compound"
    assert out["review"] is False
    # combine marker + girl + combine marker
    assert out["unicode"] == "\U00016760\U00016330\U00016760"


def test_bank_wsd_composite_for_riverbank():
    out = translate.translate_token(LEXICON, INDEX, WSD,
                                    "she sat by her sister on the bank",
                                    _tok("bank", "bank", "NOUN"))
    assert out["review"] is True
    assert "riverbank" in out["review_reason"]
    assert out["unicode"].startswith("\U00016760")  # wrapped in combine markers
    assert "\U00016688" in out["unicode"]           # beach rendered


def test_negated_verb_gets_not_prefix():
    out = translate.translate_token(LEXICON, INDEX, WSD, "Alice did not see",
                                    _tok("see", "see", "VERB", is_negated=True))
    # NOT (15733) is unmapped in the mini map -> placeholder [15733] first.
    assert out["unicode"].startswith("[15733]")
    assert out["gloss"].startswith("NOT + see")
    assert "[Verb]" in out["gloss"]


def test_punct_passes_through():
    out = translate.translate_token(LEXICON, INDEX, WSD, "x",
                                    _tok(".", ".", "PUNCT"))
    assert out["role"] == "punct"
    assert out["unicode"] == "."


def test_full_sentence_translation_end_to_end():
    sentence = "Alice did not see the bank by her sister."
    parsed = [_tok("Alice", "alice", "PROPN"),
              _tok("did", "do", "AUX"),
              _tok("not", "not", "PART"),
              _tok("see", "see", "VERB", is_negated=True),
              _tok("bank", "bank", "NOUN"),
              _tok(".", ".", "PUNCT")]
    results = [translate.translate_token(LEXICON, INDEX, WSD, sentence, t)
               for t in parsed]
    by_lemma = {r["lemma"]: r for r in results}
    assert by_lemma["alice"]["type"] == "Compound"
    assert by_lemma["see"]["gloss"].startswith("NOT + see")
    assert "riverbank" in by_lemma["bank"]["review_reason"]
    assert by_lemma["."]["role"] == "punct"
