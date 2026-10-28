# NOTICE — Data sources and attribution

## BCI Authorized Vocabulary of Blissymbolics (BCI-AV) 2025-02-15
- **Author**: Blissymbolics Communication International (BCI),
  https://www.blissymbolics.org — used for the lexicon (English + 16-language
  glosses, derivations, POS classes) built by `scripts/build_lexicon.py`.
- The BCI-AV release terms apply to lexicon derivatives; capture them before
  redistributing (task T-106).

## Project Gutenberg #11
- *Alice's Adventures in Wonderland* by Lewis Carroll (1865), public domain.
  Source text fetched by `scripts/download_data.py`.

## Sibling project BlissFont
- Unicode scalars, fonts, and the stable Plane-15 PUA mapping come from the
  sibling `BlissFont` repository (see its NOTICE.md for BCI-AV, Blissary,
  L2/23-138, and GloVe credits). `scripts/load_blissfont.py` reads its
  compiled `bliss_character_data.json` at translate time.

---
**Licence gap:** no code licence declared yet — pick one (MPL-2.0/MIT) before
public release. Reviewer-contributed lexicon data (`synonyms.json`,
`neologisms.json`, review-sheet corrections) should be contributed under the
same terms as the pipeline output.
