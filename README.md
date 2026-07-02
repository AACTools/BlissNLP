# BlissNLP

Computational translation pipeline that maps English text — starting with
*Alice's Adventures in Wonderland* — into a standardized Blissymbolics digital
corpus, using the **BCI Authorized Vocabulary (BCI-AV) 2025-02-15** release.

This is the NLP / translation counterpart to the sibling
[`BlissFont`](https://github.com/aactools/BlissFont) project, which produces the
font, `Unibliss.txt` Unicode map, and the RIME input schema. BlissNLP consumes
the BCI-AV lexical data and emits translatable, reviewable Bliss-Unicode output.

See [`Alice in Wonderland Translation Specification.md`](./Alice%20in%20Wonderland%20Translation%20Specification.md)
for the full 4-stage agent pipeline this skeleton implements.

## Toolkits

* **[spaCy](https://spacy.org/)** — NLP engine for lemma extraction, part-of-
  speech tagging, tense identification, and dependency parsing of the source
  paragraphs (Stage 1).
* **OpenPyXL** (via pandas) — parses the BCI-AV Excel translations spreadsheet
  directly to build the Bliss lexicon (Stage 2 prep).
* **pandas** — corpus and review-sheet handling.
* **requests** — fetching source corpora.

## Directory Structure

```text
BlissNLP/
├── .gitignore
├── .python-version
├── pyproject.toml             # uv-managed dependencies (uv.lock is committed)
├── README.md
├── TODO.md                    # work-package task tracker
├── Alice in Wonderland Translation Specification.md
├── example/                   # reference prototype (manual mock NLP output)
│   └── translprototype.py
├── data/
│   ├── lexicon/               # hand-authored, tracked (WSD seed rules, ...)
│   │   └── disambiguation_rules.json
│   ├── raw/                   # [gitignored] downloaded corpora + BCI data
│   └── processed/             # [gitignored] parsed graphs, lexicon, output
├── scripts/
│   ├── setup_models.py        # 0. install the spaCy English model
│   ├── download_data.py       # 1. fetch Alice + BCI-AV 2025 spreadsheet
│   ├── parse_corpus.py        # Stage 1: spaCy syntactic parse
│   ├── build_lexicon.py       # Stage 2 prep: parse BCI Excel -> lexicon
│   ├── translate.py           # Stages 2 & 3: WSD + concept mapping + assembly
│   └── export_review.py       # Stage 4: human review sheet export
└── tests/
    └── test_pipeline.py       # regression tests (uv run pytest)
```

## Quickstart (end-to-end reproduction)

Requires **Python 3.11–3.13** and [**uv**](https://github.com/astral-sh/uv).
Install uv if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then run, in order:

```bash
# 0. Create the venv and install spacy, openpyxl, pandas, requests
uv sync

# 1. Install the spaCy English model (en_core_web_sm)
uv run python scripts/setup_models.py

# 2. Download Alice in Wonderland + the BCI-AV 2025 data
uv run python scripts/download_data.py

# 3. Stage 1 — syntactic parse of Alice
uv run python scripts/parse_corpus.py

# 4. Stage 2 prep — build the Bliss lexicon from the BCI Excel
uv run python scripts/build_lexicon.py

# 5. Stages 2 & 3 — lexical mapping + visual glyph assembly
uv run python scripts/translate.py

# (optional) Refresh the BCI-id -> Unicode map from the sibling BlissFont repo
# (set BLISSFONT_DIR or rely on the default ../BlissFont path)
uv run python scripts/load_blissfont.py

# 6. Stage 4 — export the human review spreadsheet
uv run python scripts/export_review.py
```

Equivalent one-off pip commands (if not using uv):

```bash
pip install spacy openpyxl pandas
python -m spacy download en_core_web_sm
```

## Pipeline Stages

| Stage | Script | Purpose |
| :--- | :--- | :--- |
| 1 — Syntactic Parse | `parse_corpus.py` | spaCy dependency + morph parse → semantic graphs; strips Gutenberg boilerplate; flags clause-level negation; emits `resolved_referent` (coref placeholder) |
| 2 — Lexical Mapping | `build_lexicon.py`, `translate.py` | Resolve lemmas to BCI-AV 2025 concepts; word-sense disambiguation via `data/lexicon/disambiguation_rules.json` |
| 3 — Visual Assembly | `translate.py` | Apply indicator morphology (action/past/continuous/plural) + negation wrapper (BCI `not` 15733) → Unicode |
| 4 — Human Review | `export_review.py` | Emit reviewer spreadsheet; feed approvals back |

## Intermediate Data Schemas (T-902)

All intermediate artifacts live under `data/processed/` (JSONL = one record per
paragraph) unless noted.

**`alice_parsed.jsonl`** — Stage 1 output (tokens grouped into sentences, T-203):
```json
{ "paragraph_id": 0, "text": "...",
  "sentences": [ { "sentence_index": 0, "text": "Alice was beginning ...",
    "tokens": [ { "index": 0, "text": "Alice", "lemma": "alice", "pos": "PROPN",
      "tense": null, "aspect": null, "number": null, "is_negated": false,
      "head": "alice", "dep": "nsubj", "resolved_referent": null } ] } ] }
```

**`bliss_lexicon.json`** (by BCI id) + **`lemma_index.json`** (`{lemma: bci_id}`):
```json
{ "14439": { "bci_id": "14439", "gloss_en": "girl",
    "synonyms": ["girl"], "derivations": ["child", "female"],
    "bci_class": "BLUE", "category": "punctuation",
    "translations": {"sv": "flicka", "de": "M\u00e4dchen", ...},
    "winbliss": "...", "canonical_gloss": "girl" } }
```

**`alice_translated.jsonl`** — Stages 2 & 3 output (per sentence, per token):
```json
{ "paragraph_id": 0, "text": "...",
  "sentences": [ { "sentence_index": 0, "text": "...",
    "translation": [ { "lemma": "bank", "role": "content", "type": "Compound",
      "unicode": "\u275e[12640][29623]\u275e",
      "gloss": "[Combine] beach + slope (down) [Combine]",
      "bci_id": "13382", "review": true,
      "review_reason": "composite sense: riverbank" } ] } ] }
```

Token `role`: `content` (NOUN/VERB/ADJ/ADV/PROPN/NUM/INTJ), `function`
(PRON/DET/ADP/CCONJ/SCONJ/PART/AUX), or `punct`. Coverage is reported over
`content` tokens only.

## BlissFont Data Contract (T-703)

BlissNLP reads a single artifact from the sibling
[`BlissFont`](https://github.com/aactools/BlissFont) repo:

| Source (BlissFont) | Field | Used for |
| :--- | :--- | :--- |
| `data/processed/bliss_character_data.json` | `bci_id`, `proposed_unicode` | building `bliss_unicode_map.json` (BCI id → char) |

Resolved by `scripts/load_blissfont.py` via `BLISSFONT_DIR` (default
`../BlissFont`). The map is cached at `data/processed/bliss_unicode_map.json`,
so BlissFont is only needed when refreshing the cache. When a BCI id is not yet
assigned a scalar in BlissFont, the token renders as a `[bci_id]` placeholder —
coverage of real Unicode rises as BlissFont assigns more scalars.

**Shared BCI ids** (verified against BCI-AV 2025-02-15, used as the bridge):
grammatical indicators — combine marker 13382, not 15733, opposite 15927,
action 8993, past 9004, continuous 28043, plural 27112.

## Verification

```bash
uv run pytest        # 14 regression tests over parse / lexicon / WSD / assembly
```

## Status

End-to-end pipeline runs against the real BCI-AV 2025 data and the Gutenberg
text of *Alice* (~817 paragraphs, ~13.5k content tokens, ~71% direct-lookup
coverage). Outstanding work is tracked in [`TODO.md`](./TODO.md); highlights:
final Unibliss scalar assignment (from BlissFont), real coreference resolution
(T-208), proper-noun neologism registry (T-402), and the reviewer feedback loop
(T-603/T-604).
