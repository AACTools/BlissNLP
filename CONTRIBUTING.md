# Contributing to BlissNLP

This guide covers the three most common extension points: adding a proper-noun
neologism, adding a word-sense disambiguation rule, and the human-review
workflow. All hand-authored lexical data lives under `data/lexicon/` and is
tracked in git (unlike `data/raw/` and `data/processed/`).

## Setup

```bash
uv sync
uv run python scripts/setup_models.py     # spaCy en_core_web_sm
uv run python scripts/download_data.py    # Alice + BCI-AV 2025 data
uv run pytest                             # regression tests
```

## 1. Adding a proper-noun neologism (T-402)

Bliss cannot spell arbitrary names phonetically without breaking its universal
visual intent, so proper nouns are translated as **descriptive compounds**
enclosed in COMBINE markers (BCI 13382). Edit
[`data/lexicon/neologisms.json`](./data/lexicon/neologisms.json):

```json
"mock": {
  "components": ["12378", "14947"],
  "gloss": "mock (imitation)",
  "note": "animal + intensity; placeholder"
}
```

Rules:
- The **key** is the spaCy lemma of the proper noun as it appears in Alice
  (lowercase, e.g. `"alice"`, `"hatter"`). It only fires when `pos == PROPN`,
  so a common-noun homograph (e.g. `"cat"` the animal) still uses direct
  lookup.
- **`components`** is a list of BCI ids forming the compound. Verify each id
  exists in `data/processed/bliss_lexicon.json` and ideally renders in
  `data/processed/bliss_unicode_map.json`.
- **`gloss`** is the human description shown in the review sheet.
- **`note`** documents open questions (e.g. a missing concept).

Re-run `uv run python scripts/translate.py` and check the token in the review
sheet (`data/processed/review_sheet.xlsx`).

## 2. Adding a word-sense disambiguation rule (T-405)

Ambiguous lemmas are resolved against
[`data/lexicon/disambiguation_rules.json`](./data/lexicon/disambiguation_rules.json)
before direct lookup. The first context rule whose `trigger_keywords` appear in
the sentence wins.

```json
"light": {
  "default_bci_id": "<id-of-default-sense>",
  "context_rules": [
    { "bci_id": "<id-of-not-heavy-light>", "sense_description": "not heavy",
      "trigger_keywords": ["carry", "lift", "weight"] },
    { "bci_id": null, "sense_description": "illumination",
      "derivation_components": ["<sun-id>", "<lamp-id>"],
      "trigger_keywords": ["lamp", "sun", "dark", "candle"] }
  ]
}
```

- `"bci_id": null` with `"derivation_components"` declares a **composite sense**
  for which BCI-AV has no direct glyph (e.g. riverbank → shore + slope). The
  token is emitted as a COMBINE-wrapped neologism and flagged for review.
- IDs are verified against the BCI-AV 2025 spreadsheet
  (`scripts/build_lexicon.py` output).
- TODO T-405b: replace the keyword matcher with embedding cosine similarity
  (`argmax cos(context, gloss definition)`).

## 3. Human-review workflow (T-602 / WP6)

`uv run python scripts/export_review.py` writes
`data/processed/review_sheet.xlsx` with one row per token:

| Column | Meaning |
| :--- | :--- |
| `paragraph_id`, `sentence_index` | location of the token |
| `lemma`, `resolved_referent` | source lemma and coref target (T-208) |
| `draft_gloss`, `draft_unicode` | the pipeline's proposed translation |
| `review_reason` | why it was flagged (e.g. `no BCI match`, `composite sense: ...`) |
| `reviewer_decision` | **approve** / **flag** / **reject** (human-filled; pre-set to `FLAG` for flagged tokens) |
| `reviewer_correction` | the corrected Bliss id(s) or unicode |
| `notes` | free text |

Decisions feed back (T-603): `approve`d rows strengthen the lexicon / vector
store; `reject`ed rows with corrections become new WSD rules or neologism
components.

## 4. Code style

- No comments unless a `TODO T-xxx` marker is needed — cross-reference
  [`TODO.md`](./TODO.md).
- Keep pipeline scripts runnable end-to-end and `uv run pytest` green.
- Add the spaCy model and any new deps via `uv add` so `uv.lock` stays the
  source of truth.
