# Demographic Research: what conforms, and what does not

Checked 2026-09-02 against [Submission
Guidelines](https://www.demographic-research.org/authors/submissionguidelines) and the
journal's [Reference
Guidelines](https://www.demographic-research.org/files/DemRes%20Reference%20Guidelines.pdf).

This is a gap list, not a conformance plan. Nothing here blocks the medRxiv preprint, which
has different requirements and is the nearer target.

**The format question is settled in our favour.** Demographic Research accepts, in descending
order of preference, *MS Word (.docx)*, PDF, RTF, and LaTeX. `.docx` is their **first**
preference, so `python -m src.export --docx` targets the format they most want and the LaTeX
template they publish is optional rather than expected. The mechanical requirements — real
word-processor tables, 300 dpi PNG figures, captions on everything, figures placed in the
text rather than collected at the end — are all met by the current build.

What is left is editorial, and one item of it is substantial.

## The gaps

| | Requirement | Where we are | Size of the job |
|---|---|---|---|
| **1** | **Structured abstract, 250 words max**, headed BACKGROUND, OBJECTIVE, METHODS, RESULTS, CONCLUSIONS, CONTRIBUTION. CONTRIBUTION is mandatory. | 548 words, unstructured, six paragraphs. | **The real work.** Needs cutting by more than half and rebuilding under six headings. |
| **2** | Author-year references: `Surname, Initials (Year). Title. Journal Volume(Issue): Pages.` Alphabetical, unnumbered, all authors named. | Vancouver style: `Kitagawa EM. Components of a difference between two rates. *JASA* 1955;50(272):1168-1194.` Six entries, and the last two break alphabetical order. | Mechanical. An hour, six entries. |
| **3** | In-text citations as surname + year; `(Author and Author 1995)`, `(Author et al. 1995)` above three. | The paper cites narratively ("Kitagawa published the decomposition in 1955") and never parenthetically. Not wrong, but thin for the venue. | Small, and partly a judgement call. |
| **4** | Up to ten keywords listed in the file. | Ten live in `CITATION.cff` and reach the DOCX as document metadata, but appear nowhere a reader sees. | Trivial: one visible line. |
| **5** | PDF submissions must have author names and identifying information removed. | `--anonymous` does this and is verified by tests. | **Done.** |
| **6** | Title carries geographic and temporal focus. | "…U.S. Crude Death Rates, 2010-2024…" | **Done.** |
| **7** | Main text recommended under 8,000 words. | 5,231. | **Done.** |
| **8** | Section headings for anything over 1,000 words. | Numbered sections throughout. | **Done.** |
| **9** | Figures 300 dpi, `.png` strongly preferred, captioned, placed in position. | `src/figures.py` writes 300 dpi PNG; all five are embedded in place with numbered captions. | **Done.** |
| **10** | Tables built with table tools, not tabs or spaces. | Pandoc emits real `<w:tbl>` Word tables. | **Done.** |

## The abstract is the whole gap

Item 1 is not a formatting change. Demographic Research wants a 250-word abstract under six
mandatory-ish headings; ours is 548 words of continuous argument, and its structure is
rhetorical — it builds to the denominator finding rather than declaring it. CONTRIBUTION is
the heading that will take the most thought, because this paper has two contributions and the
abstract currently spends three paragraphs establishing that they are linked.

Nothing else on the list takes more than an afternoon.

## One thing that is not a gap but is a decision

Demographic Research is **not** a blind-review journal: author names, affiliations and contact
details go on the web submission form. The anonymity rule applies to the *file*. So the
`--anonymous` build satisfies a rule about the artifact, not about the process, and the
question of how the editorial office wants a public code repository handled is genuinely
open — a DOI that resolves to a Zenodo record with the author's name on it is identifying in
a way that removing a byline does not fix.

The anonymised build therefore withholds the DOI and repository URL and says so in the
Declarations, rather than deleting the data availability statement. That is a defensible
default and it is reversible: if the editorial office says a public repository is fine, drop
the rule from `ANONYMOUS_RULES` in `src/export.py` and rebuild.

## Rechecking these numbers

The word counts above are stated as of the date at the top and are not swept by
`tests/test_docs_are_current.py`, which covers `README.md`, `UAT_CHECKLIST.md` and
`STATUS.md` only. To recheck:

```bash
python -m src.report        # rebuild the manuscript first
python - <<'PY'
from pathlib import Path
t = Path("paper/manuscript_built.md").read_text(encoding="utf-8")
print("abstract:", len(t.split("## Abstract",1)[1].split("\n---",1)[0].split()))
print("main text:", len(t.split("## 1. Introduction",1)[1].split("## References",1)[0].split()))
PY
```
