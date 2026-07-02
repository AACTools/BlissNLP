# BlissNLP — To-Do List

Living task list for the BlissNLP translation pipeline. Update statuses as we
progress. Convention: `[ ]` pending, `[~]` in progress, `[x]` done.

Legend mirrors the BlissFont brief (T-IDs, Work Packages).

---

## WP0 — Foundation & Setup

- [x] `pyproject.toml` (uv-managed: spacy, openpyxl, pandas, requests) — T-001
- [x] `.gitignore`, `.python-version` — T-002
- [x] Git repo initialised — T-003
- [x] Script skeleton (setup/download/parse/lexicon/translate/review) — T-004
- [x] README with end-to-end reproduction steps — T-005
- [x] Pin exact dependency versions in `uv.lock` and commit it — T-006
- [x] Decide Python target (3.11 vs 3.13) based on spaCy wheel availability
      — resolved: 3.13 works with spaCy 3.8 — T-007

## WP1 — Data Acquisition (Stage 0)

- [x] `scripts/setup_models.py` (spaCy `en_core_web_sm`) — T-101
- [x] `scripts/download_data.py` (Alice + BCI-AV xlsx + gloss map) — T-102
- [x] Verify the BCI-AV spreadsheet downloads cleanly and inspect real sheet
      names + column headers. Confirmed columns: `BCI-AV#`, `Blissymbol`,
      `English`, `Derivation - explanation`, `POS` (BCI class colour:
      WHITE/YELLOW/GREEN/RED/BLUE/GRAY), languages 5–23, `WinBliss`. — T-103
- [x] Verify Project Gutenberg `pg11.txt` URL is stable; boilerplate stripped
      via `*** START/END OF ... ***` markers (817 paragraphs after strip) — T-104
- [ ] Optionally reuse BlissFont's `data/raw/` instead of re-downloading
      (symlink or shared path config) — T-105
- [ ] Capture and document the BCI-AV 2025 licence/attribution terms — T-106

## WP2 — Stage 1: Syntactic Parse

- [x] `scripts/parse_corpus.py` skeleton (paragraphs → token graphs) — T-201
- [x] Strip Gutenberg header/footer boilerplate before parsing — T-202
- [x] Add sentence segmentation on top of paragraph splitting (1,552 sentences) — T-203
- [x] Handle dialogue / quoted speech and em-dashes in Victorian prose.
      Curly quotes/apostrophes normalised to ASCII before parsing (fixes
      contraction tokenisation); Gutenberg italic `_markup_` stripped. T-204
- [x] Validate tense/aspect tagging on 19th-century English (spaCy caveats) — T-205
- [x] Emit negation propagation from `neg` dep to the verb head — T-206
- [ ] **T-208 — Anaphora / Coreference Resolution layer.** Resolve pronouns
      (she/it/her/they) to their antecedent nouns *before* lexical mapping so
      the visual narrative distinguishes Alice / sister / Duchess. Emit a
      `resolved_referent` field per token. Options: `fastcoref`, or an
      LLM-guided pass. (Architectural review Extension A.)
- [x] Persist a small sample gold parse for regression checks (`tests/test_gold_sample.py`) — T-207

## WP3 — Stage 2 Prep: Build the Bliss Lexicon

- [x] `scripts/build_lexicon.py` skeleton — T-301
- [x] Map the **real** spreadsheet column names to the expected logical names
      (`BCI-AV#`, `English`, `Derivation - explanation`, `POS`, languages) — T-302
- [x] Confirm the derivations column delimiter (`+` inside parentheses) and
      parse composition formulae robustly — T-303
- [x] Auto-classify category from BCI class colour (WHITE/YELLOW/.../GRAY) — T-304
- [x] Build a reverse index: English lemma → BCI id (8,817 lemmas) — T-305
- [x] Cross-reference `BCI-AV_SKOG_..._ID_to_gloss_map.txt` for canonical
      glosses — T-306
- [x] Emit a coverage report (content-word coverage, ~71% on Alice) — T-307

## WP4 — Stage 2: Lexical Mapping & Concept Resolution

- [x] `scripts/translate.py` direct-lookup path — T-401
- [x] Curate a **proper-noun neologism registry** for Alice characters
      (Alice, White Rabbit, Hatter, Cheshire Cat, Caterpillar, Duchess,
      Mock Turtle, Gryphon, Queen/King of Hearts, Knave, Dinah, Bill, Mary)
      in `data/lexicon/neologisms.json` — T-402
- [x] Implement fallback **transliteration inside NAME INDICATOR** blocks for
      names without a semantic neologism (BCI name indicator 15691; flagged
      for review, letter glyphs pending BlissFont) — T-403
- [x] Implement **semantic de-idiomization** for Victorian idioms
      (`data/lexicon/idioms.json` + sentence-level lemma-run matcher; e.g.
      "burning with curiosity" -> desire+intensity+knowledge) — T-404
- [ ] Word-sense disambiguation for ambiguous lemmas
      (e.g. `bank` river vs money, `court` royal vs legal). **NB:** verified
      against BCI-AV — `bank`→12626 is *financial* only (riverbank needs a
      `shore`+slope composite); `court`→13428 is *not* royal. Seed rules in
      `data/lexicon/disambiguation_rules.json`. (Architectural review Ext. B.) — T-405
      - [x] T-405a Context-rule matcher over trigger keywords (in `translate.py`)
      - [ ] T-405b Embedding-based sense selection: `argmax cos(e_ctx, e_gloss)`
            using sentence + BCI derivation embeddings
- [x] Composite neologism builder for unmapped spatial/relational phrases.
      Generalised into derivation-composite rendering (T-406b): when a glyph
      has no Unicode scalar, render it from its BCI derivation components.
      Doubled the render rate (26% -> 53% of content tokens). — T-406
- [~] **Lemma-synonym expansion** (`data/lexicon/synonyms.json`): map spaCy
      lemmas to BCI gloss forms. Recovered feel/two/three/sit/eat/know/moment/
      dodo/footman; coverage 73.6% -> 75.5%. Extend freely. — T-407

## WP5 — Stage 3: Visual Assembly

- [x] Resolve BCI id → proposed Unibliss Unicode scalar. `scripts/load_blissfont.py`
      reads BlissFont `bliss_character_data.json` → `data/processed/bliss_unicode_map.json`
      (1,060 glyphs currently assigned). — T-501
- [x] Replace placeholder indicator codepoints with verified BCI indicator ids:
      action 8993, past 9004, continuous 28043, plural 27112, not 15733,
      combine marker 13382, opposite 15927. — T-502
- [ ] Apply GPOS anchor metrics from the Human Calibration/Review Tool
      (top/bottom diacritic positioning) — T-503
- [x] Implement COMBINE marker sequences for compounds/neologisms (13382) — T-504
- [x] Validate output Unicode strings render with BlissFont .otf/.woff2.
      Verified: 203-page PDF, BlissaryFont embedded, zero missing-glyph
      warnings. — T-505
- [ ] Handle LTR/RTL directional mirroring via GSUB rules (coordinate with
      BlissFont) — T-506
- [~] **T-507 — Negation scoping as an inversion wrapper.** Real NOT (15733)
      now prefixed before negated verbs; full clause-level inversion via
      OPPOSITE (15927) and continuous/plural still pending BlissFont scalars.
      (Architectural review Extension C.)

## WP6 — Stage 4: Human Review & Feedback Loop

- [x] `scripts/export_review.py` skeleton (review spreadsheet) — T-601
- [x] Define reviewer decision vocabulary (approve / flag / reject) and a
      correction schema — documented in CONTRIBUTING.md — T-602
- [x] Build the import path: approved reviewer rows → lexicon updates
      (`scripts/apply_reviews.py` parses reviewer corrections -> WSD overrides
      / neologism coinages) — T-603
- [ ] Stand up a vector DB / translation memory of approved clause pairs to
      improve agent accuracy chapter-over-chapter — T-604
- [x] Round-trip test: re-translate a reviewed chapter and diff
      (idempotence test in `tests/test_integration.py`) — T-605

## WP7 — BlissFont Integration

- [x] Decide coupling: read BlissFont's `data/processed/bliss_character_data.json`
      (has `bci_id` + `proposed_unicode`). Loader: `scripts/load_blissfont.py`,
      configurable via `BLISSFONT_DIR` (default `../BlissFont`). — T-701
- [x] Add a loader for BlissFont `Unibliss.txt` (id → scalar). Served via
      `bliss_character_data.json` → `bliss_unicode_map.json` cache. — T-702
- [x] Document the shared data contract between BlissFont and BlissNLP
      (README "BlissFont Data Contract" section) — T-703
- [x] Verify BlissNLP output renders with the compiled BlissFont font
      (203-page A5 PDF, BlissaryFont embedded) — T-704

## WP8 — Evaluation & Quality

- [x] Build a small gold-standard sample (manually verified Bliss for a few
      Alice paragraphs). Done: `tests/test_integration.py` pins
      neologism/WSD/negation/punct/idiom/transliteration outputs and
      `tests/test_gold_sample.py` pins the Chapter I parse. — T-801
- [x] Token-level coverage metric (% content lemmas mapped vs flagged) — T-802
- [x] Per-stage unit tests for parse → lexicon → translate (`uv run pytest`) — T-803
- [x] Regression CI that runs the full pipeline on a fixed sample
      (`.github/workflows/ci.yml` runs pytest) — T-804

## WP9 — Documentation

- [x] README with quickstart — T-901
- [x] Document the intermediate JSONL schemas (parsed / lexicon / translated) — T-902
- [x] Map each `TODO` in the scripts back to a T-ID here (only T-208 remains
      inline) — T-903
- [x] Write a contributor guide for adding proper-noun neologisms (CONTRIBUTING.md) — T-904

## WP10 — Rendered Edition (Typst)

- [x] Interlinear English / Bliss book template (`book/template.typ`) — T-1001
- [x] `scripts/render_book.py`: reads alice_translated.jsonl, stages
      BlissaryFont from BlissFont, emits book/alice.typ (12 chapters) — T-1002
- [x] Verified compile to a 180-page A5 PDF with BlissaryFont embedded
      (zero missing-glyph warnings) — T-1003
- [~] Only content tokens with a real Unicode glyph render (now ~53%
      coverage after T-406 derivation composites; gaps dropped). Rises as
      BlissFont assigns more scalars — T-1004
- [ ] Add chapter drop-caps and ornaments once coverage supports full pages — T-1005
