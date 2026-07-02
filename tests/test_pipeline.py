"""Regression tests for the BlissNLP pipeline.

Run with:  uv run pytest
The scripts/ directory is not a package, so it is added to sys.path here.
"""
import json
import os
import sys

SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, SCRIPTS)

import build_lexicon  # noqa: E402
import parse_corpus  # noqa: E402
import translate  # noqa: E402


# --- build_lexicon helpers -------------------------------------------------

def test_normalise_synonyms_splits_and_lowercases():
    assert build_lexicon.normalise_synonyms("percent,percentage,%") == [
        "percent", "percentage", "%"
    ]


def test_normalise_synonyms_underscores_to_spaces():
    assert build_lexicon.normalise_synonyms("exclamation_mark") == ["exclamation mark"]
    assert build_lexicon.normalise_synonyms("") == []


def test_parse_derivations_takes_first_paren_group():
    out = build_lexicon.parse_derivations("(adult + description indicator) See also: foo")
    assert out == ["adult", "description indicator"]


def test_parse_derivations_empty():
    assert build_lexicon.parse_derivations("") == []
    assert build_lexicon.parse_derivations(None) == []


# --- parse_corpus Gutenberg stripping -------------------------------------

def test_strip_gutenberg_keeps_body():
    text = ("Header licence\n*** START OF THE PROJECT GUTENBERG EBOOK ***\n"
            "Alice was beginning to get very tired.\n"
            "*** END OF THE PROJECT GUTENBERG EBOOK ***\nFooter licence")
    body = parse_corpus.strip_gutenberg_boilerplate(text)
    assert "Alice was beginning" in body
    assert "Header licence" not in body
    assert "Footer licence" not in body


def test_strip_gutenberg_no_markers_passthrough():
    assert parse_corpus.strip_gutenberg_boilerplate("just the body") == "just the body"


# --- translate: WSD -------------------------------------------------------

WSD = {
    "bank": {
        "default_bci_id": "12626",
        "context_rules": [
            {"bci_id": None, "sense_description": "riverbank",
             "derivation_components": ["12640", "29623"],
             "trigger_keywords": ["river", "sister"]},
            {"bci_id": "12626", "sense_description": "financial",
             "trigger_keywords": ["money"]},
        ],
    }
}


def test_wsd_context_rule_wins():
    bid, meta = translate.apply_wsd("bank", "she sat by her sister on the bank", WSD)
    assert bid is None
    assert meta["derivation_components"] == ["12640", "29623"]


def test_wsd_default_when_no_trigger():
    bid, meta = translate.apply_wsd("bank", "the bank held the money", WSD)
    assert bid == "12626"


def test_wsd_unknown_lemma():
    assert translate.apply_wsd("xyzzy", "any text", WSD) == (None, {})


# --- translate: neologism assembly ---------------------------------------

LEXICON = {
    "14439": {"gloss_en": "girl"},
    "12640": {"gloss_en": "beach"},
    "29623": {"gloss_en": "slope (down)"},
}


def test_assemble_neologism_wraps_in_combine_markers():
    # Empty unicode map -> placeholder form. Combine marker id is 13382.
    translate._UNICODE_MAP = {}
    uni, gloss = translate.assemble_neologism(["12640", "29623"], LEXICON)
    assert uni.startswith("[13382]")  # combine marker placeholder
    assert uni.endswith("[13382]")
    assert "[12640]" in uni and "[29623]" in uni
    assert "beach" in gloss and "slope (down)" in gloss


def test_assemble_neologism_renders_real_unicode_when_mapped():
    translate._UNICODE_MAP = {"12640": "\U00016209", "13382": "\U00016760"}
    uni, gloss = translate.assemble_neologism(["12640"], LEXICON)
    assert uni == "\U00016760\U00016209\U00016760"  # marker + glyph + marker


def test_assemble_neologism_missing_component_marked():
    translate._UNICODE_MAP = {}
    uni, gloss = translate.assemble_neologism(["14439", "99999"], LEXICON)
    assert "?(99999)" in gloss


def test_render_falls_back_to_placeholder():
    translate._UNICODE_MAP = {}
    assert translate.render("8993") == "[8993]"
    translate._UNICODE_MAP = {"8993": "\U00016209"}
    assert translate.render("8993") == "\U00016209"


# --- translate: token role classification --------------------------------

def test_punct_passes_through_unflagged():
    tok = {"text": ",", "lemma": ",", "pos": "PUNCT"}
    out = translate.translate_token({}, {}, {}, "x", tok)
    assert out["role"] == "punct"
    assert out["review"] is False
    assert out["unicode"] == ","


def test_function_word_not_flagged():
    tok = {"text": "the", "lemma": "the", "pos": "DET"}
    out = translate.translate_token({}, {}, {}, "x", tok)
    assert out["role"] == "function"
    assert out["review"] is False


def test_unknown_content_word_flagged():
    tok = {"text": "xyzzy", "lemma": "xyzzy", "pos": "NOUN"}
    out = translate.translate_token({}, {}, {}, "x", tok)
    assert out["role"] == "content"
    assert out["review"] is True
    assert out["review_reason"] == "no BCI match"
