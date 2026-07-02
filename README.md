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
├── pyproject.toml             # uv-managed dependencies
├── README.md
├── Alice in Wonderland Translation Specification.md
├── example/                   # reference prototype (manual mock NLP output)
│   └── translprototype.py
├── data/
│   ├── raw/                   # [gitignored] downloaded corpora + BCI data
│   └── processed/             # [gitignored] parsed graphs, lexicon, output
└── scripts/
    ├── setup_models.py        # 0. install the spaCy English model
    ├── download_data.py       # 1. fetch Alice + BCI-AV 2025 spreadsheet
    ├── parse_corpus.py        # Stage 1: spaCy syntactic parse
    ├── build_lexicon.py       # Stage 2 prep: parse BCI Excel -> lexicon
    ├── translate.py           # Stages 2 & 3: concept mapping + glyph assembly
    └── export_review.py       # Stage 4: human review sheet export
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
| 1 — Syntactic Parse | `parse_corpus.py` | spaCy dependency + morph parse → semantic graphs |
| 2 — Lexical Mapping | `build_lexicon.py`, `translate.py` | Resolve lemmas to BCI-AV 2025 concepts |
| 3 — Visual Assembly | `translate.py` | Apply GPOS anchors / indicator morphology → Unicode |
| 4 — Human Review | `export_review.py` | Emit reviewer spreadsheet; feed approvals back |

## Status

Skeleton. The scripts are runnable end-to-end but contain `TODO` markers where
they depend on real spreadsheet column names, the final `Unibliss.txt` scalar
assignment (from BlissFont), and curated proper-noun neologisms.
