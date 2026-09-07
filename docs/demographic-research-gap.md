# Demographic Research: what conforms, and what does not

Checked 2026-09-02 against [Submission
Guidelines](https://www.demographic-research.org/authors/submissionguidelines) and the
journal's [Reference
Guidelines](https://www.demographic-research.org/files/DemRes%20Reference%20Guidelines.pdf).
Revised 2026-09-07 after the managing editor answered the two open questions below.

## What the managing editor settled

Asked, and answered:

- **A preprint is fine** and does not count as prior publication. medRxiv can go ahead.
- **The anonymisation requirement applies to the manuscript file only.** The data
  availability statement goes in the web form, editors-only, and may carry the author's name
  and the repository URL. That resolves the decision recorded at the bottom of this file:
  `--anonymous` withholds the DOI and URL from the *file*, which is the right behaviour, and
  the editorial office gets them through the form.
- **Replicability materials are provided on acceptance, not at submission.** No anonymised
  archive is needed now.

This is a gap list, not a conformance plan. Nothing here blocks the medRxiv preprint, which
has different requirements and is the nearer target.

**The format question is settled in our favour.** Demographic Research accepts, in descending
order of preference, *MS Word (.docx)*, PDF, RTF, and LaTeX. `.docx` is their **first**
preference, so `python -m src.export --docx` targets the format they most want and the LaTeX
template they publish is optional rather than expected. The mechanical requirements — real
word-processor tables, 300 dpi PNG figures, captions on everything, figures placed in the
text rather than collected at the end — are all met by the current build.

What is left is editorial, and one item of it is substantial. Of the eleven requirements
below, ten are met; item 1 is the only one that is real work.

## The gaps

| | Requirement | Where we are | Size of the job |
|---|---|---|---|
| **1** | **Structured abstract, 250 words max**, headed BACKGROUND, OBJECTIVE, METHODS, RESULTS, CONCLUSIONS, CONTRIBUTION. CONTRIBUTION is mandatory. | 548 words, unstructured, six paragraphs. | **The real work.** Needs cutting by more than half and rebuilding under six headings. |
| **2** | Author-year references: `Surname, Initials (Year). Title. Journal Volume(Issue): Pages.` Alphabetical, unnumbered, all authors named. | Vancouver style: `Kitagawa EM. Components of a difference between two rates. *JASA* 1955;50(272):1168-1194.` Six entries, and the last two break alphabetical order. | Mechanical. An hour, six entries. |
| **3** | In-text citations as surname + year; `(Author and Author 1995)`, `(Author et al. 1995)` above three. | **There are no numeric in-text citations to convert.** The paper cites narratively and by name and year — "Kitagawa published the decomposition in 1955" — with one already-parenthetical `(Noymer and Garenne 2000)`. Nothing is in Vancouver style *in the text*; only the reference list is, and DR does not want that reformatted until acceptance. | **Nothing to do mechanically.** See below for the two entries that are cited by nobody. |
| **4** | Up to ten keywords listed in the file. | Ten, read from `CITATION.cff`, printed as a visible line after the abstract in both formats, and set as the Word document property — which through `v0.1.2` it silently was **not**; see README, "Building the submission artifacts". | **Done**, and now tested against the built file. |
| **5** | Manuscript file must have author names and identifying information removed. | `--anonymous` does this. Verified in the markdown *and* in every built `.docx` and `.pdf`, against three planted leaks. | **Done.** |
| **6** | Title carries geographic and temporal focus. | "…U.S. Crude Death Rates, 2010-2024…" | **Done.** |
| **7** | Main text recommended under 8,000 words. | 4,735 (sections 1–6). Full submission 5,759. | **Done.** |
| **8** | Section headings for anything over 1,000 words. | Numbered sections throughout. | **Done.** |
| **9** | Figures 300 dpi, `.png` strongly preferred, captioned, placed in position. | `src/figures.py` writes 300 dpi PNG; all five are embedded in place with numbered captions. | **Done.** |
| **10** | Tables built with table tools, not tabs or spaces. | Pandoc emits real `<w:tbl>` Word tables. | **Done.** |
| **11** | Double-spaced, 12pt or larger, no page numbers, no headers or footers. DR states it will not edit submissions to conform. | `--journal` does all four, in both formats, and reads them back out of the built file. The ordinary build failed three of the four: 11pt, single-spaced, and typst numbers pages by default. | **Done.** |

## The abstract is the whole gap

Item 1 is not a formatting change. Demographic Research wants a 250-word abstract under six
mandatory-ish headings; ours is 548 words of continuous argument, and its structure is
rhetorical — it builds to the denominator finding rather than declaring it. CONTRIBUTION is
the heading that will take the most thought, because this paper has two contributions and the
abstract currently spends three paragraphs establishing that they are linked.

Nothing else on the list takes more than an afternoon.

## Citations: what item 3 turned out to be

There were no numeric in-text citations. The paper cites by name and year in running prose
throughout, so the conversion the item asks for has nothing to operate on, and the reference
list — the only Vancouver-styled thing in the document — is explicitly not to be reformatted
until acceptance.

What the check did surface is a different problem, and a real one: **two entries in the
reference list are cited by nothing in the text.**

| Entry | Cited in text? |
|---|---|
| Hamilton, Driscoll, and Miniño 2025 | Yes, parenthetically with a page, section 4.4. Added with that citation. |
| Kitagawa 1955 | Yes, by name and year, sections 1 and 3.2. |
| Noymer and Garenne 2000 | Yes, parenthetically, section 5.2. |
| Klein and Schoenborn 2001 | By its title only — "NCHS Statistical Notes No. 20", section 2 — never by author or year. |
| NCHS, *Deaths: Final Data* | By series name, sections 4.4 and 6.1. |
| **Woolf and Schoomaker 2019** | **No.** |
| **Human Mortality Database** | **No.** |

A reference list with uncited entries is the same defect as the uncited figure that
`tests/test_export.py` was written to catch, and it is the sort of thing a copy-editor finds
rather than a reviewer. Fixing it is an editorial judgement about the prose — either cite
them where they belong or drop them — and it belongs with the abstract rewrite, not with a
mechanical pass.

### The one direct quotation, and its page number

DR requires a page number after a direct quotation, colon-separated:
`(Leone and Hinde 2007: 162)`. Section 4.4 quotes NVSR Vol. 74 No. 11 verbatim, and it is
the manuscript's **only** direct quotation — the other quoted spans in the file are titles
and scare quotes, checked line by line.

The page is **2**, in the report's Methods section, verified against
<https://www.cdc.gov/nchs/data/nvsr/nvsr74/nvsr74-11.pdf>. The sentence recurs twice in
abbreviated form — a figure note on page 3 and a table note on page 10 — but both drop
"using blended base population estimates" and the closing clause, so page 2 is the only
place the sentence as quoted appears in full. The citation reads
`(Hamilton, Driscoll, and Miniño 2025: 2)`, with the serial comma DR's own example uses —
`(Miller, Bender, and Schuh 2005)`.

`tests/test_documents.py::test_every_direct_quotation_carries_a_page_number` holds it, and
a companion test asserts the pattern rejects a citation with no page, so a second quotation
added later cannot arrive without one.

**It is cited by its authors, not by the agency.** DR's corporate-body form sits under
*Website content*, which is for pages with no personal author. NVSR 74-11 is bylined — the
cover page reads "by Brady E. Hamilton, Ph.D., Anne K. Driscoll, Ph.D., and Arialdi M.
Miniño, M.P.H." — so the applicable template is *Research report or working paper*:
`Last name, Initials (Year). Title. Place: Institution (Series title and number).`

That surname costs the manuscript its ASCII purity, deliberately. `ñ` is now in
`ALLOWED_NON_ASCII` and mapped to `n` in `ASCII_PUNCTUATION`, because the alternative is
misspelling a cited author to keep a file plain. It is the first entry in either table that
is a letter rather than a mark.

**The list entry, checked against the cover page and now in the manuscript** under H:

> Hamilton, B.E., Driscoll, A.K., and Miniño, A.M. (2025). Trends in births and deaths:
> United States, 2010-2023. Hyattsville, MD: National Center for Health Statistics
> (National Vital Statistics Reports 74(11)).
> https://www.cdc.gov/nchs/data/nvsr/nvsr74/nvsr74-11.pdf.

Two deviations from the cover page, both correct for a reference list and both worth
recording so neither reads as a transcription slip. The cover sets the title in title case
(*Trends in Births and Deaths*); DR's style is sentence case. The cover uses an en dash in
`2010–2023`; the entry uses a hyphen, matching how every other year range in this
manuscript is written. The wording is otherwise identical, and the volume, number and date
— 74(11), August 27, 2025 — are read from the cover page too.

**This one entry was added; the other six were not.** "Not required to be reformatted until
acceptance" is about restyling the existing entries, not about omitting an entry the text
cites — a citation with nothing to resolve to is a defect in its own right, and the mirror
of the two uncited entries above. So the list now runs Hamilton, Kitagawa, Klein, Noymer,
Woolf, Human Mortality Database, National Center for Health Statistics: one entry in DR
form at the top, six in Vancouver form behind it, and still not fully alphabetical, all of
which the reformatting pass will settle at once.

`tests/test_documents.py::test_every_in_text_citation_resolves_to_a_reference` holds the
new invariant, with a companion test proving the pattern matches the citations that are
there and skips an ordinary parenthetical carrying a year.

## The AI disclosure moved

DR wants it in Methods, or in a section titled **"Disclosure about the AI use"** at the end.
It was a `**Declaration of AI assistance.**` paragraph inside Declarations. It is now its own
top-level section under DR's exact title, placed after References — the most literal reading
of "at the end", and one line to move earlier if the editorial office would rather it sat
before the reference list. The Author contributions paragraph, which cross-references it by
name, was updated with it.

## The decision this used to record, now answered

Demographic Research is **not** a blind-review journal: author names, affiliations and contact
details go on the web submission form. The anonymity rule applies to the *file*. So the
`--anonymous` build satisfies a rule about the artifact, not about the process, and the
question of how the editorial office wants a public code repository handled was genuinely
open — a DOI that resolves to a Zenodo record with the author's name on it is identifying in
a way that removing a byline does not fix.

**The managing editor has answered it.** The data availability statement goes in the web
form, editors-only, and may carry the author's name and the repository URL. The anonymised
build therefore keeps doing what it does — withholding the DOI and repository URL from the
file and saying so, rather than deleting the statement, which would read as an author who
never wrote one — and the editorial office gets them by the route the journal specified.
`ANONYMOUS_RULES` in `src/export.py` stays as it is.

## Rechecking these numbers

The word counts above are stated as of the date at the top and are not swept by
`tests/test_docs_are_current.py`, which covers `README.md`, `UAT_CHECKLIST.md` and
`STATUS.md` only. To recheck, rebuild and then run the counter, which reports both the
section slices and the count taken from the built `.docx` — the second is the one that
matches what a submission form will say, because figure captions and the keywords line exist
only in the built document:

```bash
python -m src.report
python -m src.export --journal --both
python scratch/wordcount.py manuscript-anonymous-journal.docx
```

`scratch/` is gitignored, so that script is a convenience and not part of the build. It
deliberately does **not** strip hyphens before counting: doing so splits every
"age-adjusted" and "pre-pandemic" in two, which is worth about 200 words here — an inflation
large enough to matter against a limit and invisible in the total.
