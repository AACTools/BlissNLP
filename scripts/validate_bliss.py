#!/usr/bin/env python3
"""
Validate every Bliss word the pipeline emits, using hlridge/bliss-svg-builder
as the structural oracle (MPL-2.0, npm dependency — see NOTICE).

Flow:
  1. alice_translated.jsonl -> data/processed/bliss_words.jsonl
     (each rendered word's codepoints converted back to Blissary B-codes via
      the BlissFont reverse map: official scalar OR Plane-15 PUA -> bci -> B)
  2. scripts/validate_bliss.mjs (node) composes each word with the builder;
     a word is INVALID if the builder emits warnings (e.g. UNKNOWN_CODE) or
     renders zero elements
  3. failures -> data/processed/invalid_bliss_words.json + console report

Usage:  uv run python scripts/validate_bliss.py
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROC = os.path.join(HERE, "..", "data", "processed")
TRANSLATED = os.path.join(PROC, "alice_translated.jsonl")
BLISSFONT_JSON = os.path.join(HERE, "..", "..", "BlissFont", "data", "processed", "bliss_character_data.json")
WORDS_OUT = os.path.join(PROC, "bliss_words.jsonl")
FAIL_OUT = os.path.join(PROC, "invalid_bliss_words.json")


def build_reverse_map() -> dict[int, str]:
    """codepoint -> Blissary B-code, via bci_id (official scalar + PUA)."""
    with open(BLISSFONT_JSON, "r", encoding="utf-8") as f:
        records = json.load(f)
    rev: dict[int, str] = {}
    for r in records:
        code = r.get("bliss_svg_builder_code")
        if not code:
            continue
        if str(r["bci_id"]).isdigit():  # stable Plane-15
            rev[0xF0000 + int(r["bci_id"])] = code
        pu = r.get("proposed_unicode")
        if pu and pu.startswith("U+"):
            try:
                rev[int(pu[2:], 16)] = code
            except ValueError:
                pass
    return rev


def main() -> None:
    rev = build_reverse_map()
    n_words = n_unmapped_cp = 0
    with open(TRANSLATED, "r", encoding="utf-8") as src, \
         open(WORDS_OUT, "w", encoding="utf-8") as out:
        for line in src:
            para = json.loads(line)
            for sent in para["sentences"]:
                for i, tok in enumerate(sent["translation"]):
                    uni = tok.get("unicode", "")
                    if tok.get("role") != "content" or not uni or uni.startswith("["):
                        continue
                    if tok.get("type") == "Transliteration":
                        continue  # Latin names — not Bliss words
                    codes, unmapped = [], 0
                    for ch in uni:
                        cp = ord(ch)
                        b = rev.get(cp)
                        if b:
                            codes.append(b)
                        elif cp >= 0xF0000 or 0x16000 <= cp <= 0x16FFF:
                            unmapped += 1  # a Bliss codepoint we can't reverse
                    if codes or unmapped:
                        n_words += 1
                        n_unmapped_cp += unmapped
                        out.write(json.dumps({
                            "para": para["paragraph_id"], "sent": sent["sentence_index"],
                            "tok": i, "lemma": tok.get("lemma"),
                            "type": tok.get("type"), "unmapped": unmapped,
                            "dsl": "/".join(codes),
                        }, ensure_ascii=False) + "\n")
    print(f"exported {n_words} words ({n_unmapped_cp} unreversible codepoints) -> {WORDS_OUT}")

    # node validator
    r = subprocess.run(
        ["node", os.path.join(HERE, "validate_bliss.mjs"), WORDS_OUT, FAIL_OUT],
        capture_output=True, text=True, check=True)
    print(r.stdout.strip())

    with open(FAIL_OUT, "r", encoding="utf-8") as f:
        fails = json.load(f)
    print(f"invalid words: {len(fails)} of {n_words} ({100 * len(fails) / max(n_words, 1):.1f}%)")
    from collections import Counter
    kinds = Counter(w.get("warning_codes", ["?"]) [0] if w.get("warning_codes") else "no-elements"
                    for w in fails)
    print("failure classes:", dict(kinds.most_common(6)))
    for w in fails[:6]:
        print(" ", w["lemma"], "|", w["dsl"][:50], "|", w.get("warning_codes"))


if __name__ == "__main__":
    main()
