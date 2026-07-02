# BlissNLP — Actions & Findings

Status of the Alice-in-Wonderland Blissymbolics translation pipeline, the
remaining gaps, and who needs to act on what. Derived from a live run against
BCI-AV 2025-02-15 and the current BlissFont fonts.

## 1. Snapshot (current run)

| Metric | Value |
| :--- | :--- |
| Source | Project Gutenberg *Alice's Adventures in Wonderland* (817 paragraphs, 1,559 sentences) |
| Content tokens (NOUN/VERB/ADJ/ADV/PROPN/NUM/INTJ) | 13,087 |
| **Rendered to a real Bliss glyph** | **7,220 (55.2%)** |
| Resolved to a BCI id but no Unicode scalar | 3,301 (25.2%) |
| No BCI match at all | 2,566 (19.6%) |
| BlissFont scalars assigned | 1,107 / 6,419 glyphs (17.2%) |
| Tests | 29 passing |
| Rendered artifact | 216-page A5 PDF (BlissaryFont embedded, zero missing-glyph warnings) |

The pipeline runs end-to-end: `download → parse → lexicon → translate →
review → render`. WSD, negation scoping, derivation composites, de-idiomization,
proper-noun neologisms, and the reviewer feedback loop are all wired.

## 2. Where the gaps are (and who owns them)

### Gap A — BlissFont has not assigned a Unicode scalar (25.2%, 3,301 tokens) — **BlissFont team**
The lemma resolved to a BCI concept, but the glyph has no codepoint in
`bliss_character_data.json`. T-406 (derivation composites) + the synonym map
already recover the ones whose *components* are mapped; the residual 3,301 are
glyphs whose derivations don't decompose into already-mapped radicals. Only
assigning more scalars closes this.

### Gap B — No BCI match (19.6%, 2,566 tokens) — **mixed; see below**
Split into two very different causes:

- **Lemma-form mismatch (BlissNLP-side, partially recovered):** the concept
  exists in BCI under a different gloss. A synonym map (`data/lexicon/
  synonyms.json`) already recovers `feel`→feeling, `two`→2, `three`→3,
  `sit`→seat, `eat`→food, `know`→knowledge, `moment`→time, `dodo`→bird, etc.
  More aliases can be added.
- **Genuinely absent from BCI-AV (needs BlissFont/BCI lexicography):** basic
  verbs are missing from the 2025 vocabulary — verified absent: **`read`,
  `write`, `forget`**, plus Alice-specific nouns (**`dormouse`, `mock`,
  `croquet`, `queer`**). These need either new BCI glyphs or approved
  descriptive compounds.

## 3. Actions for the BlissFont team

Prioritized by impact on the rendered book.

1. **Assign Unicode scalars to the remaining grammatical indicators** (highest
   priority — they appear on almost every verb/noun). Currently unmapped:
   - `not` **15733** (negation — every negated sentence is mis-rendered)
   - `indicator (continuous form)` **28043** (present-continuous verbs)
   - `plural` **27112** (plural nouns)
   - (Already done this round: action 8993, past 9004, opposite 15927, combine
     13382, name 15691, description 8998 — thank you.)
2. **Map the Latin alphabet (A–Z) to codepoints** so the NAME INDICATOR
   transliteration fallback (T-403) can actually spell unmapped proper nouns.
   Currently only `a` (12321) is mapped (1/26).
3. **Confirm whether core verbs are truly absent from BCI-AV** — `read`,
   `write`, `forget`. If they exist under alternate glosses, surface those in
   the ID→gloss map; if genuinely absent, they are high-frequency omissions
   worth adding. (Note: `sit`/`eat` were resolvable via synonyms → seat/food.)
4. **Keep assigning scalars** for high-frequency glyphs. Each scalar BlissFont
   publishes auto-raises our render rate (the pipeline re-runs `load_blissfont`
   and picks them up). The 1,609 glyphs whose derivations don't decompose are
   the most valuable next batch.
5. **GPOS mark anchors** for the newly-mapped indicators (the team already
   shipped individual indicator anchors in `6c61625`) — verify the mark-to-base
   table covers 15733/28043/27112 once they get scalars.

## 4. Actions for BlissNLP (our side, unblocked)

1. **Lemma-synonym expansion** (Gap B, ongoing): extend `data/lexicon/
   synonyms.json` (spaCy lemma → BCI gloss form). Already recovered
   feel/two/three/sit/eat/know/moment/dodo/footman; more aliases welcome.
2. **T-208 coreference resolution** (fastcoref or an LLM pass) so pronouns
   resolve to Alice / sister / Duchess instead of a generic person glyph. The
   `resolved_referent` field and scaffold already exist; only the resolver is a
   stub. This is the single biggest *narrative-readability* win left.
3. **T-405b embedding-based WSD** to replace keyword matching for ambiguous
   lemmas (bank/court/light).
4. **Expand the idiom & neologism registries** (`data/lexicon/idioms.json`,
   `neologisms.json`) — community-editable, documented in CONTRIBUTING.md.
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
Produces a 216-page interlinear English/Bliss A5 PDF in BlissaryFont, a
reviewer spreadsheet, and full intermediate JSONL corpora — all backed by 29
regression tests and CI.
