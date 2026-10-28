# BlissNLP

English → Blissymbolics. spaCy parse → BCI-AV lexicon → WSD/idioms/neologisms
→ indicator assembly → reviewer spreadsheet → Typst interlinear book.

Latest full run (Alice, 817 paragraphs): **77.3% content coverage, 100% of
mapped tokens render, 900/2,062 pronouns coreference-resolved, 34 tests green.**

Pair repo: [BlissFont](https://github.com/AACTools/BlissFont) (fonts + Unicode map).

## Quickstart

```bash
uv sync
uv run python scripts/setup_models.py     # spaCy en_core_web_sm
uv run python scripts/download_data.py    # Alice + BCI-AV xlsx
uv run python scripts/parse_corpus.py     # parse + coref (T-208)
uv run python scripts/build_lexicon.py    # 8,817-lemma reverse index
uv run python scripts/translate.py        # WSD, idioms, indicators, coref
uv run python scripts/export_review.py    # reviewer spreadsheet
uv run python scripts/apply_reviews.py    # corrections → lexicon
uv run python scripts/render_book.py      # → book/alice.typ
typst compile --font-path book/fonts book/alice.typ   # → 204-page A5 PDF
```

## Stages

| stage | script | notes |
|---|---|---|
| parse | `parse_corpus.py` | POS/tense/negation + heuristic coref (gender+number+salience, paragraph-scoped) |
| lexicon | `build_lexicon.py` | BCI-AV xlsx → id/gloss/derivations; synonym bridge via `data/lexicon/` |
| translate | `translate.py` | WSD rules, idioms, `neologisms.json` compounds, indicator assembly (action 8993, past 9004, continuous 28043, plural 27112, not 15733), pronouns → antecedent glyphs |
| review | `export_review.py` / `apply_reviews.py` | human loop: spreadsheet in, corrections to lexicon out |
| render | `render_book.py` + `book/template.typ` | interlinear English/Bliss, BlissaryFont embedded |

## Reviewers

Flagged rows land in `data/processed/review_sheet.xlsx`. Set
`reviewer_decision` (approve/reject) + `reviewer_correction` (BCI ids, comma
separated), then `apply_reviews.py` → `translate.py` → `render_book.py`.
Highest value: unmapped Alice nouns (dormouse, croquet) — coin compounds.

## Data & licence

NOTICE.md — BCI-AV is CC BY-SA 4.0; Alice (Gutenberg #11) is public domain.
Status tracker: [TODO.md](./TODO.md). Contributor guide: [CONTRIBUTING.md](./CONTRIBUTING.md).
