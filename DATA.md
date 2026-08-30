# Status of the data files

**The data in this repository is not licensed, because it is not the author's
to license.**

That sentence is the whole point of this document, and it is a statement of
status rather than a grant of rights. The files under `data/raw/wonder_exports/`
and `data/raw/census/` are works of the United States federal government,
produced by CDC/NCHS and the U.S. Census Bureau. They are in the public domain
under 17 U.S.C. § 105. No copyright subsists in them, so applying BSD-3-Clause,
MIT, CC BY or CC0 to them would assert rights that do not exist and that the
author does not hold. **Do not "tidy" this file by adding a license to the
data.** A false claim of rights over public-domain government data is a worse
outcome than no license statement at all.

## What covers what

| path | status |
|---|---|
| `src/`, `tests/`, `bootstrap.*`, `notebooks/` | BSD-3-Clause — see `LICENSE` |
| `data/raw/wonder_exports/`, `data/raw/census/` | U.S. federal government works, public domain (17 U.S.C. § 105) |
| `data/raw/*.csv` (the input CSVs) | Structure and citations: BSD-3-Clause. Values, once populated from the sources: public domain, as above |
| The selection and arrangement of the data files | CC0 1.0 — see below |
| `paper/`, `figures/`, `data/processed/results.json` | CC BY 4.0 — see `paper/LICENSE` |

## Terms that do apply

Public domain is not the same as unconditional. Two things attach, and both are
already documented in full elsewhere in this repository rather than restated
here:

- **CDC WONDER Data Use Restrictions** and the public-domain assertion quoted
  from CDC's own FAQ: see the **Data redistribution** section of `README.md`.
  In short: statistical reporting and analysis only, and no reported count or
  rate based on fewer than ten deaths. This analysis is national and its
  smallest cell is in the tens of thousands.
- **Provenance for the Census files** — source URL, retrieval date and SHA-256
  per file, plus the schema notes and how the paths were found: see
  `data/raw/census/PROVENANCE.md`. A Census CSV carries no query footer the way
  a WONDER export does, so that document is the only provenance it has.

Citation is requested by both agencies rather than legally required, and is
provided. Every WONDER export carries the agency's own suggested citation inside
its footer; `data/queries/cdc_wonder_queries.md` records the database and query
behind each file.

## The compilation, and why it is called out separately

Selecting these particular extracts, at these groupings and year ranges, and
arranging them so they reconcile, is the author's work even though the
underlying figures are not. In some jurisdictions — most clearly the European
Union's *sui generis* database right — that selection and arrangement can attract
protection independently of the contents.

**That thin compilation right, and only that right, is released under
[CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/).**

The reason for stating it this precisely, rather than putting a blanket CC0 over
`data/`: a blanket CC0 would read as a claim that the author held rights in the
federal data and chose to waive them. He did not hold them, so waiving them is
not his to do, and the waiver would misrepresent the status of the underlying
figures to anyone relying on this file. Keeping the scope explicit is what stops
a later simplification from turning an accurate statement into a false one.

## Verifying the files

The committed data is hashed, and the hashes are checked rather than merely
recorded:

```bash
python -m pytest tests/test_provenance.py
```

That verifies every WONDER export against the `sha256` in `WONDER_EXPORTS`
(`src/fetch.py`) and every Census file against `data/raw/census/PROVENANCE.md`,
in both directions — a file with no recorded hash fails as surely as one whose
bytes have moved.

`.gitattributes` marks both data directories `-text` so git performs no
line-ending conversion on them. This is not housekeeping: the recorded hashes
are of the files **as the agencies served them**, so that a reviewer can
re-download and compare. Normalisation would change those bytes and break the
comparison on some platforms while leaving it passing on others.
