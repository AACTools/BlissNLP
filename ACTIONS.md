# BlissNLP — Actions & Findings

Status of the Alice-in-Wonderland Blissymbolics translation pipeline, the
remaining gaps, and who needs to act on what. Derived from a live run against
BCI-AV 2025-02-15 and the current BlissFont fonts.

## 1. Snapshot (current run)

| Metric | Value |
| :--- | :--- |
| Source | Project Gutenberg *Alice's Adventures in Wonderland* (817 paragraphs, 1,559 sentences) |
| Content tokens (NOUN/VERB/ADJ/ADV/PROPN/NUM/INTJ) | 13,087 |
| **Rendered to a real Bliss glyph** | **9,929 (100% of mapped tokens)** |
| Resolved to a BCI id | 9,929 (75.9% of content) |
| No BCI match at all (genuinely absent concepts) | 3,158 (24.1%) |
| BlissFont glyphs mapped | **6,419 / 6,419 (100%)** — official scalars + stable Plane-15 PUA |
| Tests | 29 passing |
| Rendered artifact | 204-page A5 PDF (BlissaryFont embedded, **zero broken glyphs**) |

The pipeline runs end-to-end: `download → parse → lexicon → translate →
review → render`. WSD, negation scoping, derivation composites, de-idiomization,
proper-noun neologisms, and the reviewer feedback loop are all wired.

## 2. Where the gaps are (and who owns them)

### Gap A — Unicode scalars — ✅ CLOSED (BlissFont)
BlissFont now ships a stable Plane-15 PUA mapping (`0xF0000 + bci_id`,
commit `c6b63db`) for all 6,419 glyphs, plus official scalars for the ~1,100
already proposed and the previously-unmapped indicators (continuous 28043 →
U+167E8, plural 27112 → U+167DC, negation 15733 → U+F3D75). `load_blissfont.py`
prefers the official scalar and falls back to PUA, so **every BCI id renders**.
The old "shifting codepoint" problem is gone (BCI ids are permanent).

### Gap B — No BCI match (24.1%, 3,158 tokens) — **mostly BlissNLP / reviewers**
These are concepts the pipeline could not resolve to any BCI id. Split:

- **Lemma-form mismatch (BlissNLP-side):** the concept exists under a different
  gloss. `data/lexicon/synonyms.json` already recovers `feel`→feeling,
  `two`→2, `three`→3, `read`→read-(to), `write`→write-(to), `forget`→
  forget-(to), `sit`→sit-(to), `eat`→eat-(to), `know`→knowledge, etc. More
  aliases welcome.
- **Genuinely absent from BCI-AV (reviewers / BCI lexicography):** Alice-
  specific nouns (`dormouse`, `mock`, `croquet`, `queer`, `footman`) and the
  odd core concept. These need descriptive compounds (coinable in
  `neologisms.json`) or new BCI glyphs.

## 3. Actions for the BlissFont team

Most prior blockers are now resolved — thank you. Remaining asks are minor:

1. ✅ **Indicators** (continuous 28043, plural 27112, not 15733) — done in
   `c6b63db`. Verified: zero broken glyphs in the rendered book.
2. ✅ **Stable Plane-15 PUA mapping** (0xF0000+bci_id) — done; closes the
   shifting-codepoint problem. `load_blissfont.py` now maps all 6,419 glyphs.
3. **Latin alphabet** — accepted your pushback. BCI 12321 is the word "a/any",
   not the letter A. Proper-noun spelling now renders Latin via font fallback
   in the Typst template (font stack: BlissaryFont → body serif), the standard
   mixed-script approach. No BlissFont action needed.
4. **Official scalars** — whenever the UTC proposal advances more glyphs from
   PUA to the official U+167xx block, the loader already prefers the official
   scalar, so no BlissNLP change will be needed.
5. (Optional) keep the GPOS mark-to-base anchors aligned as indicator scalars
   move from PUA to official codepoints.

## 4. Actions for BlissNLP (our side, unblocked)

1. **Extend the lemma-synonym map** (Gap B): `data/lexicon/synonyms.json` —
   keep adding spaCy-lemma → BCI-gloss aliases for the remaining 3,158
   unmatched tokens.
2. **T-208 coreference resolution** (fastcoref or an LLM pass) so pronouns
   resolve to Alice / sister / Duchess instead of a generic person glyph. The
   `resolved_referent` field and scaffold already exist; only the resolver is a
   stub. This is the single biggest *narrative-readability* win left.
3. **T-405b embedding-based WSD** to replace keyword matching for ambiguous
   lemmas (bank/court/light).
4. **Coin descriptive compounds** in `data/lexicon/neologisms.json` for the
   genuinely-absent Alice nouns (dormouse, croquet, queer, …) — unblocked now
   that every component renders.
5. **T-604 translation-memory store** of approved clause pairs for accuracy
   growth across chapters.

## 5. Actions for end users / reviewers

The human-in-the-loop is fully wired. A certified Bliss translator:

1. Opens `data/processed/review_sheet.xlsx` (3,452 rows pre-flagged `FLAG`).
2. For each flagged token, sets `reviewer_decision` = **approve** / **reject**
   and fills `reviewer_correction` with one or more BCI ids (e.g. `15416, 14682`
   to coin a man+hat compound).
3. Runs `uv run python scripts/apply_reviews.py` — corrections are written into
   `disambiguation_rules.json` (single id) or `neologisms.json` (multiple ids),
   then `uv run python scripts/translate.py` regenerates the corpus and
   `render_book.py` re-renders the PDF.

Highest-value review targets: the genuinely-absent verbs (Gap B) and the
Alice-specific nouns (`dormouse`, `croquet`, `queer`, `footman`) — reviewers
can coin descriptive compounds for these immediately, unblocked by BlissFont.

## 6. Blocked / out of scope until BlissFont ships

- **T-503** GPOS anchor tuning, **T-506** LTR/RTL mirroring — depend on the
  font's final tables.
- **T-507 full clause-level negation** via OPPOSITE — needs `not`/`continuous`/
  `plural` scalars (BlissFont action #1).

## 7. What works now

Reproducible from scratch with `uv sync && uv run python scripts/{setup_models,
download_data,parse_corpus,build_lexicon,translate,export_review,render_book}.py`.
Produces a 204-page interlinear English/Bliss A5 PDF in BlissaryFont, a
reviewer spreadsheet, and full intermediate JSONL corpora — all backed by 29
regression tests and CI. Every resolvable token renders a real glyph.

## 8. "Broken glyph" audit of the rendered book — ✅ CLEAN

| | Before BlissFont `c6b63db` | After |
| :--- | ---: | ---: |
| Rendered Bliss words | 8,599 | 10,566 |
| Contain an embedded `[id]` placeholder | 1,843 (21%) | **0 (0%)** |
| `[27112]` plural occurrences | 480 | 0 |
| `[28043]` continuous occurrences | 321 | 0 |
| `[15733]` not occurrences | 211 | 0 |

The three indicator scalars + the stable PUA block eliminated **all** broken
glyphs in one BlissFont release. `pdftotext` confirms zero `[id]` placeholder
strings remain in the PDF. The only open rendering work is Gap B (concepts with
no BCI match), which is a lexicography/review task, not a font task.
