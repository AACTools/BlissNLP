#!/usr/bin/env python3
"""
Stage 2 (prep) - Build the Bliss lexicon from the BCI-AV 2025 spreadsheet.

Reads the BCI-AV 2025-02-15 derivations & translations .xlsx directly with
openpyxl (via pandas) and emits:

  - data/processed/bliss_lexicon.json  : canonical entries keyed by BCI id
  - data/processed/lemma_index.json    : reverse index {lemma: bci_id}

Real spreadsheet columns (verified against the 2025-02-15 release):
    0  BCI-AV#                          BCI identifier (e.g. "12054")
    1  Blissymbol                       glyph image/formula (ignored)
    2  English                          gloss, comma-separated synonyms,
                                       underscores join multi-word terms
    3  Derivation - explanation         "(comp1 + comp2 ...)" formula
    4  POS                              BCI vocabulary class colour
                                       (WHITE/YELLOW/GREEN/RED/BLUE/GRAY)
    5..23                               Swedish .. Danish glosses
    24 WinBliss                         legacy encoding string

Gloss normalisation: synonyms split on ',', underscores -> spaces, lowercased.
"""
import json
import os
import re

import pandas as pd

RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))
PROC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))
XLSX_PATH = os.path.join(RAW_DIR, "BCI-AV_SKOG_2025-02-15_derivations_translations.xlsx")
GLOSS_MAP_PATH = os.path.join(RAW_DIR, "BCI-AV_SKOG_2025-02-15_ID_to_gloss_map.txt")
LEXICON_PATH = os.path.join(PROC_DIR, "bliss_lexicon.json")
INDEX_PATH = os.path.join(PROC_DIR, "lemma_index.json")

# Spreadsheet header name -> ISO-ish code used throughout the project.
# (Codes match the BCI-AV release URL: "po" = Polish, "dk" = Danish.)
LANG_HEADERS = {
    "Swedish": "sv", "Norwegian": "no", "Finnish": "fi", "Hungarian": "hu",
    "German": "de", "Dutch": "nl", "Afrikaans": "af", "Russian": "ru",
    "Icelandic": "is", "Lithuanian": "lt", "Latvian": "lv", "Polish": "po",
    "French": "fr", "Spanish": "es", "Portugese": "pt", "Italian": "it",
    "Danish": "dk",
}

# BCI vocabulary class colour -> human label (preliminary; refine with BCI docs).
BCI_CLASS_LABELS = {
    "WHITE": "core", "YELLOW": "extended", "GREEN": "supplementary",
    "RED": "indicator", "BLUE": "punctuation", "GRAY": "legacy", "GREY": "legacy",
}

_DERIV_RE = re.compile(r"\(([^()]*)\)")


def normalise_synonyms(raw: str) -> list[str]:
    """Split an English gloss cell into clean lowercase synonyms."""
    if not raw:
        return []
    out = []
    for part in str(raw).split(","):
        term = part.strip().replace("_", " ").lower()
        if term:
            out.append(term)
    return out


def parse_derivations(raw: str) -> list[str]:
    """Extract parenthesised '(a + b + c)' components from a derivation cell."""
    if not raw:
        return []
    text = str(raw)
    # Take the first parenthesised group as the canonical formula.
    m = _DERIV_RE.search(text)
    body = m.group(1) if m else text
    return [c.strip().lower() for c in body.split("+") if c.strip()]


def load_gloss_map(path: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    if not os.path.exists(path):
        return mapping
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or "\t" not in line:
                continue
            bci_id, gloss = line.split("\t", 1)
            mapping[bci_id.strip()] = gloss.strip()
    return mapping


def main() -> None:
    if not os.path.exists(XLSX_PATH):
        raise SystemExit(
            f"BCI spreadsheet not found at {XLSX_PATH}. "
            "Run `scripts/download_data.py` first."
        )
    os.makedirs(PROC_DIR, exist_ok=True)

    print("Reading BCI-AV 2025 spreadsheet ...")
    df = pd.read_excel(XLSX_PATH, sheet_name=0, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    print(f"  {len(df)} rows, columns: {list(df.columns)}")

    gloss_map = load_gloss_map(GLOSS_MAP_PATH)
    print(f"  gloss map entries: {len(gloss_map)}")

    # Resolve column indices robustly from the header.
    col_id = "BCI-AV#"
    col_en = "English"
    col_deriv = next((c for c in df.columns if c.startswith("Derivation")), None)
    col_pos = "POS"

    lexicon: dict[str, dict] = {}
    lemma_index: dict[str, str] = {}

    for _, row in df.iterrows():
        bci_id = str(row.get(col_id, "") or "").strip()
        if not bci_id or not bci_id.isdigit():
            continue
        synonyms = normalise_synonyms(row.get(col_en, ""))
        if not synonyms:
            continue

        bci_class = str(row.get(col_pos, "") or "").strip().upper()
        translations = {}
        for header, code in LANG_HEADERS.items():
            val = row.get(header)
            if val is not None and str(val).strip():
                translations[code] = str(val).strip()

        entry = {
            "bci_id": bci_id,
            "gloss_en": synonyms[0],
            "synonyms": synonyms,
            "derivations": parse_derivations(row.get(col_deriv, "")),
            "bci_class": bci_class,
            "category": BCI_CLASS_LABELS.get(bci_class, "unknown"),
            "translations": translations,
            "winbliss": str(row.get("WinBliss", "") or "").strip() or None,
            "canonical_gloss": gloss_map.get(bci_id, ""),
        }
        lexicon[bci_id] = entry
        for syn in synonyms:
            # First writer wins so the canonical (first listed) synonym sticks.
            lemma_index.setdefault(syn, bci_id)

    with open(LEXICON_PATH, "w", encoding="utf-8") as f:
        json.dump(lexicon, f, ensure_ascii=False, indent=2)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(lemma_index, f, ensure_ascii=False, indent=2)

    print(f"Built lexicon: {len(lexicon)} entries -> {LEXICON_PATH}")
    print(f"Built lemma index: {len(lemma_index)} lemmas -> {INDEX_PATH}")


if __name__ == "__main__":
    main()
