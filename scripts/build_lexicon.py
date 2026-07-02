#!/usr/bin/env python3
"""
Stage 2 (prep) - Build the Bliss lexicon from the BCI-AV 2025 spreadsheet.

Reads the BCI-AV 2025-02-15 derivations & translations .xlsx directly with
openpyxl (via pandas) and emits a normalized lexicon keyed by English lemma.

Each entry contains:
  - bci_id            : the BCI identifier
  - gloss_en          : the English gloss (used as the lookup key)
  - derivations       : composition formula components
  - translations      : {lang_code: gloss} for the 18 target languages
  - category          : best-guess category (TODO: refine)

Output: data/processed/bliss_lexicon.json
"""
import json
import os

import pandas as pd

RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))
PROC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))
XLSX_PATH = os.path.join(RAW_DIR, "BCI-AV_SKOG_2025-02-15_derivations_translations.xlsx")
GLOSS_MAP_PATH = os.path.join(RAW_DIR, "BCI-AV_SKOG_2025-02-15_ID_to_gloss_map.txt")
OUT_PATH = os.path.join(PROC_DIR, "bliss_lexicon.json")

# Expected language columns in the BCI-AV spreadsheet.
LANG_COLUMNS = ["en", "sv", "no", "fi", "hu", "de", "nl", "af", "ru",
                "is", "lt", "lv", "po", "fr", "es", "pt", "it", "dk"]


def load_gloss_map(path: str) -> dict[str, str]:
    """Load the BCI ID -> gloss mapping text file into a dict."""
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

    print("Reading BCI-AV 2025 spreadsheet (this can take a moment) ...")
    # The workbook contains a derivations sheet; sheet name may vary, so read
    # the first sheet as a baseline. Refine once the real columns are known.
    df = pd.read_excel(XLSX_PATH, sheet_name=0, engine="openpyxl")
    print(f"Loaded {len(df)} rows with columns: {list(df.columns)}")

    gloss_map = load_gloss_map(GLOSS_MAP_PATH)

    lexicon: dict[str, dict] = {}
    # TODO: map real column names from the spreadsheet. The keys below are the
    # expected logical names per the BlissFont Project Brief.
    for _, row in df.iterrows():
        bci_id = str(row.get("ID", "") or row.get("bci_id", "")).strip()
        gloss_en = str(row.get("en", "") or "").strip().lower()
        if not bci_id or not gloss_en:
            continue
        translations = {lang: str(row.get(lang, "") or "").strip()
                        for lang in LANG_COLUMNS if lang in df.columns}
        derivations_raw = str(row.get("derivations", "") or "")
        lexicon[gloss_en] = {
            "bci_id": bci_id,
            "gloss_en": gloss_en,
            "derivations": [d.strip() for d in derivations_raw.split("+") if d.strip()],
            "translations": translations,
            # Cross-reference the gloss map for a canonical gloss if present.
            "canonical_gloss": gloss_map.get(bci_id, ""),
            "category": "Base Spacing",  # TODO: classify via indicators / punctuation.
        }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(lexicon, f, ensure_ascii=False, indent=2)

    print(f"Built lexicon with {len(lexicon)} entries -> {OUT_PATH}")


if __name__ == "__main__":
    main()
