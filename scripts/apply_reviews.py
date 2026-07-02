#!/usr/bin/env python3
"""
T-603: ingest reviewer decisions from the review spreadsheet back into the
hand-authored lexicon files, closing the human-in-the-loop.

Reads data/processed/review_sheet.xlsx and applies rows where a reviewer set
`reviewer_decision` + `reviewer_correction`. A correction is interpreted as
one or more BCI ids (digits, separated by any non-digit punctuation):

  - a single id   -> a direct-sense override in disambiguation_rules.json
                     (the lemma resolves to that id everywhere)
  - several ids   -> a proper-noun neologism in neologisms.json
                     (components = those ids)

Idempotent: re-running with the same sheet produces the same lexicon files.
"""
import json
import os
import re

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
PROC_DIR = os.path.abspath(os.path.join(HERE, "..", "data", "processed"))
LEXICON_DIR = os.path.abspath(os.path.join(HERE, "..", "data", "lexicon"))
REVIEW_PATH = os.path.join(PROC_DIR, "review_sheet.xlsx")
WSD_PATH = os.path.join(LEXICON_DIR, "disambiguation_rules.json")
NEOLOGISMS_PATH = os.path.join(LEXICON_DIR, "neologisms.json")

_ID_RE = re.compile(r"\d+")


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def parse_correction(text: str) -> list[str]:
    return _ID_RE.findall(str(text or ""))


def main() -> None:
    if not os.path.exists(REVIEW_PATH):
        raise SystemExit(f"Missing {REVIEW_PATH}. Run export_review.py first.")
    df = pd.read_excel(REVIEW_PATH, engine="openpyxl")
    decided = df[df["reviewer_decision"].astype(str).str.strip().str.len() > 0]
    corrected = decided[decided["reviewer_correction"].astype(str).str.strip().str.len() > 0]
    print(f"Review rows: {len(df)} | decided: {len(decided)} | with corrections: {len(corrected)}")

    wsd = load_json(WSD_PATH, {"_meta": {}})
    neo = load_json(NEOLOGISMS_PATH, {"_meta": {}})
    wsd_meta = wsd.get("_meta", {})
    neo_meta = neo.get("_meta", {})
    n_wsd = n_neo = 0

    for _, row in corrected.iterrows():
        lemma = str(row["lemma"]).strip().lower()
        ids = parse_correction(row["reviewer_correction"])
        if not ids or not lemma:
            continue
        decision = str(row["reviewer_decision"]).strip().lower()
        note = str(row.get("notes", "") or "").strip()
        if len(ids) == 1:
            wsd[lemma] = {
                "default_bci_id": ids[0],
                "default_note": f"reviewer override ({decision})" + (f": {note}" if note else ""),
            }
            n_wsd += 1
        else:
            neo[lemma] = {
                "components": ids,
                "gloss": f"reviewer coinage ({decision})",
                "note": note or "imported from review sheet",
            }
            n_neo += 1

    wsd["_meta"] = wsd_meta
    neo["_meta"] = neo_meta
    save_json(WSD_PATH, wsd)
    save_json(NEOLOGISMS_PATH, neo)

    print(f"Applied {n_wsd} sense override(s) -> {WSD_PATH}")
    print(f"Applied {n_neo} neologism coinage(s) -> {NEOLOGISMS_PATH}")
    print("Re-run translate.py to regenerate the corpus with the new mappings.")


if __name__ == "__main__":
    main()
