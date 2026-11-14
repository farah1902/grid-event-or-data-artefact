# paper/ — the manuscript for Applied Energy

LaTeX source of *Grid event or data artefact? Hierarchical weak supervision for anomaly attribution in multi-city feeder telemetry*.
The plan (structure, value thread, place of every figure, table and equation, writing order, journal rules) is [OUTLINE.md](OUTLINE.md).

## Build

```bash
python paper/tools/sync_figures.py        # copies results/figures/<stem>.pdf -> paper/figures/Figure_N.pdf (Figures 4-12)
python paper/tools/export_figures.py      # draws Figures 1-3 in submission form (no built-in title, TrueType fonts)
cd paper && latexmk -pdf main.tex         # MiKTeX: pdflatex + bibtex; elsarticle 3.5 (2026/01/09), elsarticle-num style
python paper/tools/wordcount.py           # body-text words per section vs the 8,000-8,100 target
```

## Files

| File | Content |
|---|---|
| `main.tex` | front matter (title, authors placeholder, abstract, keywords), section inputs, bibliography |
| `sections/01_introduction.tex` … `08_conclusions.tex` | one file per section; the first line holds its word budget and plan |
| `sections/declarations.tex` | data and code availability, CRediT (later), competing interest (none), funding (later) |
| `references.bib` | verified references only (see below); importable into Zotero or Mendeley |
| `figures/Figure_N.pdf` | main figures under submission names, copied by `tools/sync_figures.py` (do not edit by hand) |
| `tools/sync_figures.py` | paper figure number → source file in `results/figures/` |
| `tools/wordcount.py` | texcount-based body-text count (text + headings; captions, tables, math, abstract, declarations, references excluded) |

## Rules for anyone writing here

1. **Numbers** come only from `docs/results_summary.md` or `results/`; cite the finding (F..) or decision (D..) in a LaTeX comment next to the sentence when it is not obvious.
2. **References** are added only from their DOI record (`curl -LH "Accept: application/x-bibtex" https://doi.org/<DOI>`, Crossref or DataCite), with a comment above the entry saying when and what was checked. A claim attributed to a paper is checked against the paper itself (abstract or full text), never written from memory.
3. **Length:** 8,000–8,100 words of body text (author's decision, 2026-11-14); budgets per section in `OUTLINE.md`.
4. **Journal rules** (official guide, recorded in `OUTLINE.md`): tables with booktabs and no shading, not duplicating figures; equations numbered in order of reference; figures as separate files; abstract ≤ 250 words; 3–5 highlights ≤ 85 characters; 1–7 keywords.
5. **Wording (D77):** the southern cities "share one recording timeline" and a "common acquisition and export chain"; do not write "one data logger" (the data paper describes per-feeder meters exported manually).
6. Interpretations keep the confidence level of their finding (*solid*, *strong*, *provisional*).

## Status

| Step | Content | State |
|---|---|---|
| 1 | Outline | done (2026-11-13) |
| 2 | LaTeX skeleton, verified dataset references | done (2026-11-14) |
| 3 | §3 Data, hierarchy and typology | revised after review (2026-11-14, D78), 891 words |
| 4 | §4 Method | accepted (2026-11-14, D79, D80), 1,700 words; Eqs (3)–(22), Table 3 (rules), Fig 3; 12 method references verified |
| 5–12 | §5 Experimental design … final checks | to do |

**Figure step (to do before submission):** re-export every main figure without the title baked into the image (captions carry it), with TrueType fonts embedded (`pdf.fonttype = 42`), sized for print width with legible text; Fig 1's internal title still says "logger" (D77).
