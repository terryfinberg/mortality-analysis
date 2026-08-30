# medRxiv submission checklist

> ## ⚠ The preprint license is effectively irreversible once posted
>
> This manuscript is licensed **CC BY 4.0** (`paper/LICENSE`). Preprint servers
> do not, as a rule, permit relicensing a posted version, and posting a later
> version under different terms does not retract the terms the first one went
> out under. There is no undo.
>
> **Re-confirm the target journal's preprint policy against CC BY 4.0 before
> posting, not after.** A small number of journals still place conditions on
> preprints depending on the license they carry. CC BY 4.0 is the broadly
> compatible choice and medRxiv's own recommendation, but broadly compatible is
> not universally compatible, and this check costs minutes now against a
> problem that cannot be fixed later.

**Preprint server:** medRxiv (health sciences)
**Suggested category:** Epidemiology
**DOI:** *[to be minted from a tagged GitHub release via Zenodo]*

---

## Before submitting

### Data and code

- [ ] All UAT sections pass (see `UAT_CHECKLIST.md`)
- [ ] Every row in `data/raw/` has `verified_by` and `verified_date`
- [ ] Repository pushed to GitHub, public
- [ ] Release tagged (`v0.1.0` or later)
- [ ] Zenodo connected, DOI minted, DOI inserted above and in the manuscript
- [ ] `LICENSE` (BSD-3-Clause, code), `paper/LICENSE` (CC BY 4.0, manuscript) and
      `DATA.md` (public-domain status of the federal data) all present
- [ ] **Target journal's preprint policy re-confirmed against CC BY 4.0** — see the
      warning at the top of this file. Irreversible once posted.
- [ ] `python -m pytest tests/test_provenance.py` passes, so the committed data
      matches its recorded hashes at the version being cited

### Manuscript

- [ ] `manuscript_built.md` regenerated from current data
- [ ] No `{{TOKEN}}` strings remain
- [ ] Figures referenced in text match files in `figures/`
- [ ] Limitations section reflects what was actually done, including any data problems found
      during verification
- [ ] Provisional-year caveat appears wherever a provisional figure is cited
- [ ] Baseline-window sensitivity reported

### Required medRxiv declarations

- [ ] **Funding:** state source, or "None."
- [ ] **Competing interests:** state, or "The author declares no competing interests."
- [ ] **Ethics / IRB:** this analysis uses publicly available aggregate vital statistics and
      involves no identifiable individual data. State this explicitly; medRxiv screens for it.
- [ ] **Data availability:** point to the GitHub repository and the Zenodo DOI
- [ ] **Author contributions**
- [ ] **ORCID** linked

### Format

- [ ] Convert to PDF (medRxiv accepts PDF; single file preferred)
- [ ] Abstract under the word limit for the category
- [ ] Figures legible at submission resolution: the pipeline writes 300 dpi
- [ ] References complete with DOIs where available

---

## Things a reviewer is likely to raise

Worth having answers ready rather than discovering these in review.

**"Why project the adjusted rate instead of the count?"** Addressed in section 3.3. Be ready
to give the numbers both ways; the difference is the whole substance of the objection.

**"Why six age groups instead of the NCHS eleven?"** Addressed in section 2.1. The honest
answer is legibility, and a reviewer may not accept it. Consider running the decomposition at
eleven groups as a sensitivity check and reporting that the conclusion does not change, if it
does change, that is important and belongs in the paper.

**"The linear baseline is too simple."** Defensible for a decade of relatively smooth trend,
weaker if the series has visible curvature. Look at the residuals before defending it.

**"Data was transcribed, not fetched."** Acknowledged in section 6.1. The verification
attestations in the CSVs are the answer, which is why they need to be real.

---

## After posting

- [ ] Add the preprint DOI to the GitHub repository About section
- [ ] Update the Zenodo record to reference the preprint
- [ ] Note the posting date; medRxiv preprints can be revised and revisions are versioned
