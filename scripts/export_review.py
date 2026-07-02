#!/usr/bin/env python3
"""
Stage 4 - Human-in-the-Loop Validation

Loads the draft translations and emits an interactive review spreadsheet
(.xlsx) for certified Bliss translators to approve, flag, or correct each
clause. Approved rows feed back into the lexicon / vector store to improve
the translation agent's accuracy over subsequent chapters.

Output: data/processed/review_sheet.xlsx
"""
import json
import os

import pandas as pd

PROC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))
TRANSLATED_PATH = os.path.join(PROC_DIR, "alice_translated.jsonl")
OUT_PATH = os.path.join(PROC_DIR, "review_sheet.xlsx")

REVIEW_COLUMNS = [
    "paragraph_id",
    "source_text",
    "lemma",
    "resolved_referent",
    "pos_category",
    "draft_gloss",
    "draft_unicode",
    "review_reason",
    "reviewer_decision",   # approve / flag / reject (filled by humans)
    "reviewer_correction",
    "notes",
]


def main() -> None:
    if not os.path.exists(TRANSLATED_PATH):
        raise SystemExit(f"Missing {TRANSLATED_PATH}. Run translate.py first.")
    os.makedirs(PROC_DIR, exist_ok=True)

    rows = []
    with open(TRANSLATED_PATH, "r", encoding="utf-8") as f:
        for line in f:
            para = json.loads(line)
            for tok in para["translation"]:
                rows.append({
                    "paragraph_id": para["paragraph_id"],
                    "source_text": para["text"],
                    "lemma": tok["lemma"],
                    "resolved_referent": tok.get("resolved_referent") or "",
                    "pos_category": tok["type"],
                    "draft_gloss": tok["gloss"],
                    "draft_unicode": tok["unicode"],
                    "review_reason": tok.get("review_reason") or "",
                    "reviewer_decision": "FLAG" if tok.get("review") else "",
                    "reviewer_correction": "",
                    "notes": "",
                })

    df = pd.DataFrame(rows, columns=REVIEW_COLUMNS)
    df.to_excel(OUT_PATH, index=False, engine="openpyxl")
    flagged = int((df["reviewer_decision"] == "FLAG").sum())
    print(f"Wrote review sheet -> {OUT_PATH}")
    print(f"  Total tokens: {len(df)}  |  flagged for review: {flagged}")


if __name__ == "__main__":
    main()
