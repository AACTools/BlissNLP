#!/usr/bin/env python3
"""
BlissFont integration (T-701 / T-702).

Bridges BlissNLP's BCI ids to the Unicode scalars compiled by the sibling
BlissFont project. BlissFont publishes `bliss_character_data.json` containing,
per glyph, `bci_id` and `proposed_unicode` (e.g. "U+16379"). This script
collapses that into a flat `{bci_id: char}` map cached under data/processed/.

Locating BlissFont (first match wins):
  1. `BLISSFONT_DIR` environment variable
  2. `../BlissFont` relative to this repo
  3. any explicit path passed to `build_unicode_map()`

Output: data/processed/bliss_unicode_map.json  ->  {bci_id: "U+XXXXX", ...}
"""
import json
import os

RAW_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))
PROC_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "processed"))
CACHE_PATH = os.path.join(PROC_DIR, "bliss_unicode_map.json")


def find_blissfont_dir() -> str | None:
    env = os.environ.get("BLISSFONT_DIR")
    if env and os.path.isdir(env):
        return env
    sibling = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "BlissFont"))
    if os.path.isdir(sibling):
        return sibling
    return None


def _u(code: str) -> str | None:
    """Convert a 'U+XXXXX' string to its character, or None if null/empty."""
    if not code:
        return None
    code = code.strip()
    if not code.startswith("U+") and not code.startswith("u+"):
        return None
    try:
        return chr(int(code[2:], 16))
    except ValueError:
        return None


def build_unicode_map(blissfont_dir: str | None = None) -> dict[str, str]:
    """
    Read BlissFont's bliss_character_data.json and return {bci_id: char}.

    Per id, prefer the official proposed Unicode scalar (e.g. U+167E8); when
    none is assigned, fall back to BlissFont's stable Plane-15 PUA mapping
    `0xF0000 + bci_id` (committed in BlissFont c6b63db), which the font ships
    in its cmap for all 6,419 glyphs. Falls back to the cached map if
    BlissFont is unavailable.
    """
    blissfont_dir = blissfont_dir or find_blissfont_dir()
    if not blissfont_dir:
        return _load_cache()
    src = os.path.join(blissfont_dir, "data", "processed", "bliss_character_data.json")
    if not os.path.exists(src):
        return _load_cache()

    entries = json.load(open(src, "r", encoding="utf-8"))
    mapping: dict[str, str] = {}
    for e in entries:
        bci_id = str(e.get("bci_id") or "").strip()
        if not bci_id or not bci_id.isdigit():
            continue
        char = _u(e.get("proposed_unicode"))
        if char is None:
            # Stable Plane-15 PUA fallback: 0xF0000 + bci_id.
            char = chr(0xF0000 + int(bci_id))
        mapping[bci_id] = char

    os.makedirs(PROC_DIR, exist_ok=True)
    code_cache = {bid: f"U+{ord(c):X}" for bid, c in mapping.items()}
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(code_cache, f, ensure_ascii=False, indent=2)
    return mapping


def _load_cache() -> dict[str, str]:
    if not os.path.exists(CACHE_PATH):
        return {}
    code_cache = json.load(open(CACHE_PATH, "r", encoding="utf-8"))
    return {bid: _u(cp) for bid, cp in code_cache.items() if _u(cp)}


def main() -> None:
    bf = find_blissfont_dir()
    print(f"BlissFont dir: {bf or '(not found)'}")
    mapping = build_unicode_map(bf)
    print(f"BCI id -> Unicode mappings: {len(mapping)}")
    print(f"Cached -> {CACHE_PATH}")
    for bid in ("12603", "8993", "15733", "13382", "14439"):
        c = mapping.get(bid)
        print(f"  {bid}: {('U+%05X ' % ord(c)) + c if c else '(unmapped)'}")


if __name__ == "__main__":
    main()
