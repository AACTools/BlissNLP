#!/usr/bin/env python3
"""
Download the source corpora and reference data required by the pipeline.

Fetches:
  1. Alice's Adventures in Wonderland (Project Gutenberg #11) — source English text.
  2. BCI-AV 2025-02-15 derivations & translations spreadsheet (.xlsx) — lexical map.
  3. BCI-AV 2025-02-15 ID -> gloss map (.txt) — concept index.

Outputs are written under data/raw/ and are intentionally git-ignored.
"""
import os
import sys
import requests

# --- Source URLs -----------------------------------------------------------
# Alice in Wonderland (plain text UTF-8 from Project Gutenberg).
ALICE_URL = "https://www.gutenberg.org/cache/epub/11/pg11.txt"

# BCI-AV 2025-02-15 release (shared with the sibling BlissFont project).
BCI_BASE = "http://www.blissymbolics.net/BCI-AV_2025-02-15"
GLOSS_MAP_URL = f"{BCI_BASE}/BCI-AV_SKOG_2025-02-15_ID_to_gloss_map.txt"
DERIVATIONS_XLSX_URL = (
    f"{BCI_BASE}/BCI-AV_SKOG_2025-02-15_"
    "(en+sv+no+fi+hu+de+nl+af+ru+is+lt+lv+po+fr+es+pt+it+dk)"
    "+derivations_8483-29642.xlsx"
)

RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))

# (key, url, filename) tuples for everything we fetch.
TARGETS = [
    ("alice", ALICE_URL, "alice_wonderland.txt"),
    ("gloss_map", GLOSS_MAP_URL, "BCI-AV_SKOG_2025-02-15_ID_to_gloss_map.txt"),
    ("derivations_xlsx", DERIVATIONS_XLSX_URL,
     "BCI-AV_SKOG_2025-02-15_derivations_translations.xlsx"),
]

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/120.0.0.0 Safari/537.36")
}


def download_file(url: str, target_path: str) -> None:
    print(f"Downloading: {url}\n        -> {target_path}")
    try:
        response = requests.get(url, headers=HEADERS, stream=True, timeout=60)
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        block = 1024 * 64
        downloaded = 0
        with open(target_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=block):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded / total * 100
                        sys.stdout.write(f"\rProgress: {pct:.1f}% "
                                         f"({downloaded}/{total} bytes)")
                        sys.stdout.flush()
        print("\nDownload complete.")
    except Exception as e:
        print(f"\nError downloading {url}: {e}")
        sys.exit(1)


def main() -> None:
    os.makedirs(RAW_DIR, exist_ok=True)
    for _key, url, filename in TARGETS:
        target_path = os.path.join(RAW_DIR, filename)
        if os.path.exists(target_path):
            print(f"Already present, skipping: {target_path}")
            continue
        download_file(url, target_path)
    print("\nData bootstrap complete. Raw files are in:", RAW_DIR)


if __name__ == "__main__":
    main()
