// BlissNLP — Alice in Wonderland, interlinear English / Bliss edition.
// Template helpers. Page setup + content live in the generated alice.typ.

#let bliss-font = "BlissaryFont"
#let en-font = "Georgia"  // serif for the English line (falls back gracefully)

// Title page (its own page).
#let title-page = {
  align(center + horizon)[
    #v(2fr)
    #text(size: 34pt, weight: "bold")[Alice's Adventures]
    #v(0.1em)
    #text(size: 34pt, weight: "bold")[in Wonderland]
    #v(1.2em)
    #text(size: 13pt, fill: gray.darken(10%))[Lewis Carroll]
    #v(2em)
    #text(font: bliss-font, size: 30pt)[#sym.diamond.stroked]
    #v(0.6em)
    #text(size: 11pt, fill: gray.darken(10%))[A Blissymbolics interlinear edition]
    #v(2fr)
    #text(size: 9pt, fill: gray.darken(20%))[
      BlissNLP pipeline #h(1em) BCI-AV 2025-02-15 #h(1em) BlissaryFont
    ]
  ]
  pagebreak()
}

// Chapter opener page.
#let chapter(num, title) = {
  pagebreak(weak: true)
  v(1fr)
  align(center)[
    #text(size: 14pt, fill: gray.darken(20%), tracking: 3pt)[CHAPTER #num]
    #v(0.4em)
    #text(size: 26pt, weight: "bold")[#title]
  ]
  v(1fr)
}

// Interlinear paragraph: English line above, Bliss line beneath.
// Bliss line uses a font stack so Latin letters inside NAME INDICATOR
// transliteration blocks render via the body font (mixed-script fallback),
// per the BlissFont team's recommendation.
#let para(en, bliss) = {
  block(width: 100%, spacing: 1.4em)[
    #set align(left)
    #text(font: en-font, size: 9.5pt)[#en]
    #v(0.35em)
    #text(font: (bliss-font, en-font), size: 22pt, spacing: 80%)[#bliss]
  ]
}
