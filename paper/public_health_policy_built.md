# Model Policy Framework

## The Mortality Surveillance and Demographic Resilience Act

**A model federal framework**
**Companion to:** *Decomposing U.S. Crude Death Rates, 2010-2024* (see `paper/manuscript.md`)
**Drafting status:** Reference draft for discussion. Not introduced legislation.

---

### Read this first

This is a model policy written in federal drafting register: Titles, Sections, imperative "shall" language, appropriation authorizations, sunset provisions. It is the kind of document that goes to a legislator's policy director as a starting point, or to an agency rulemaking team as a reference framework.

It is not a research finding. Two cautions apply throughout:

The dollar authorizations are drafted at scales comparable to real programs of similar scope, but they have not been costed. They would need a CBO-style score before any legislative use. Do not cite them as analysis.

The empirical claims in the Preamble are bound to the companion paper's findings, and are now supported: the data files were populated from the committed CDC WONDER exports and attested row by row on 2026-08-30. **This file is a template.** Magnitudes in the Preamble are double-brace placeholders substituted from `data/processed/results.json` by `src/report.py`; read the generated `public_health_policy_built.md`, and do not edit numbers here by hand.

Section-by-section, the policy logic stands on its own. Where a finding cites a magnitude, that magnitude comes from the companion paper's pipeline and moves when the data does.

---

## Preamble: Findings

The Congress finds the following:

**(1)** The crude death rate is the mortality statistic most frequently reported to the public and the one most frequently misinterpreted, because it conflates change in the risk of dying at a given age with change in the age composition of the population.

**(2)** The United States is undergoing a demographic transition in which cohorts of unprecedented relative size are entering the age bands in which the large majority of deaths occur. This transition exerts sustained upward pressure on aggregate death counts independent of any change in health.

**(3)** For much of the postwar period, improvement in age-specific mortality offset this demographic pressure, holding the crude rate approximately stable. This offsetting relationship is an equilibrium sustained by two large opposing forces, not a natural constant, and it is therefore vulnerable to any sustained stall in mortality improvement.

**(4)** Mortality during the COVID-19 pandemic was concentrated among older adults: 75.7 percent of deaths for which COVID-19 was the underlying cause occurred among people aged 65 and over, across 2020 through 2024. This profile differs fundamentally from the 1918 influenza pandemic, in which mortality peaked among young and middle-aged adults. Preparedness frameworks calibrated to one profile are poorly matched to the other.

**(5)** Excess mortality monitoring during the pandemic was assembled as an emergency improvisation. The United States lacks standing infrastructure for near-real-time excess mortality surveillance.

**(6)** The interval between the end of a calendar year and the publication of final national mortality data routinely approaches three years. The National Vital Statistics Report *Deaths: Final Data for 2021* was released in October 2024 and *Deaths: Final Data for 2022* in June 2025; as of August 2026 no such report had been published for 2023 or 2024. An interval of this length is incompatible with the use of mortality data in active policymaking.

---

## TITLE I: AGE-STRATIFIED PANDEMIC PREPAREDNESS

### Sec. 101. Purpose

To align federal pandemic preparedness with the empirical age distribution of mortality risk, and to remove the assumption of a uniform age profile from planning documents, resource allocation formulas, and public communication.

### Sec. 102. Age-stratified planning requirement

(a) **In general.** Not later than 18 months after enactment, the Secretary shall revise all federal pandemic preparedness plans to specify, for each of at least three distinct pathogen age-profile scenarios, the corresponding allocation of countermeasures, protective equipment, and clinical capacity.

(b) **Required scenarios.** The scenarios shall include, at minimum:
   1. A profile concentrated in adults aged 65 and over;
   2. A profile concentrated in working-age adults, comparable to the 1918 influenza pattern;
   3. A profile with elevated pediatric mortality.

(c) **Prohibition on single-profile planning.** No plan submitted under this section may assume a single age profile as a planning baseline.

### Sec. 103. Long-term care facilities as critical public health infrastructure

(a) **Designation.** Long-term care facilities, skilled nursing facilities, and residential care communities are designated critical public health infrastructure for purposes of federal emergency planning.

(b) **Stockpile requirement.** The Secretary shall maintain within the Strategic National Stockpile a dedicated reserve of personal protective equipment, rapid diagnostics, and therapeutics sufficient to supply designated facilities for not fewer than 90 days at surge utilization.

(c) **Infection control capacity.** The Secretary shall establish minimum infection-prevention staffing standards for designated facilities and shall provide technical assistance and funding to facilities demonstrating inability to meet them without assistance.

(d) **Cohorting protocols.** The Secretary shall publish model protocols for resident cohorting, staff assignment restriction, and visitation policy under declared emergency, with explicit attention to the mental-health and dignity costs of isolation. Protocols shall be reviewed and reissued not less than every 3 years.

### Sec. 104. Allocation priority

Where a countermeasure is in scarce supply during a declared emergency, allocation frameworks shall weight population subgroups by observed or best-estimated age-specific mortality risk for the pathogen in question, and the Secretary shall publish the risk estimates and the resulting weights within 14 days of adopting them.

---

## TITLE II: NATIONAL EXCESS MORTALITY SURVEILLANCE SYSTEM

### Sec. 201. Establishment

There is established within the National Center for Health Statistics a National Excess Mortality Surveillance System (in this Title, "the System") as permanent standing infrastructure.

### Sec. 202. Functions

The System shall:

(a) Publish estimates of excess mortality at national and state level, updated not less frequently than every 14 days;

(b) Publish the baseline model, its parameters, its code, and the sensitivity of published estimates to reasonable alternative baseline specifications;

(c) Stratify all published estimates by age group using the standard convention established under Title III;

(d) Maintain a public application programming interface providing programmatic access to all published series without registration, fee, or rate limit inconsistent with research use;

(e) Publish, alongside each release, the completeness of the underlying data by jurisdiction, so that users can distinguish a genuine decline in deaths from a reporting lag.

### Sec. 203. Reduction of reporting latency

(a) **Target.** The Secretary shall reduce the interval between the close of a calendar year and publication of final national mortality data to not more than 9 months.

(b) **Plan.** Not later than 12 months after enactment, the Secretary shall submit to the Congress a plan for achieving the target under subsection (a), including identification of the jurisdictional reporting bottlenecks responsible for the current interval and the resources required to address them.

(c) **Reporting.** The Secretary shall report annually on progress, including the latency achieved and the jurisdictions furthest from compliance.

### Sec. 204. Independence

Publication under this Title shall not be subject to prior review or approval outside the National Center for Health Statistics. This subsection may not be waived under any emergency authority.

---

## TITLE III: DEFAULT AGE STRATIFICATION IN PUBLIC HEALTH REPORTING

### Sec. 301. Standard age convention

(a) The Secretary shall establish a standard age-group convention for federal mortality and morbidity reporting, comprising not fewer than six groups and providing separate reporting for ages 65-74, 75-84, and 85 and over.

(b) The three oldest bands may not be collapsed in any public-facing release.

### Sec. 302. Age-adjusted rates alongside crude rates

(a) **Requirement.** Any federal publication reporting a crude mortality rate or aggregate death count shall report the corresponding age-adjusted rate with equal prominence.

(b) **Decomposition requirement.** Where the crude and age-adjusted rates move in opposite directions between reporting periods, the publication shall include a decomposition attributing the change to age-specific mortality and to change in age composition.

(c) **Plain-language requirement.** Each such publication shall include a plain-language statement of what the divergence means, written for a general audience.

### Sec. 303. Communications guidance and training

The Secretary shall issue guidance to Department communications staff on the interpretation of crude and age-adjusted rates, and shall require periodic training for staff responsible for public mortality communication.

---

## TITLE IV: OFFSETTING-TRENDS PUBLIC HEALTH INVESTMENT

### Sec. 401. Findings and purpose

The offsetting relationship described in Preamble paragraph (3) holds only while age-specific mortality continues to improve. Sustaining it requires continued reduction in the causes of death that are amenable to intervention. The purpose of this Title is to maintain that improvement at a pace sufficient to absorb ongoing demographic pressure.

### Sec. 402. Authorized investment areas

The Secretary is authorized to make grants, enter cooperative agreements, and provide technical assistance in:

1. Overdose prevention, treatment, and harm reduction;
2. Cardiovascular disease prevention and management;
3. Metabolic disease prevention, including diabetes and obesity;
4. Suicide prevention and crisis response;
5. Unintentional injury prevention, including motor vehicle and fall-related injury.

### Sec. 403. Growth target

(a) The Secretary shall establish a target of not less than 10 percent real-terms growth in aggregate funding across the areas listed in section 402 over each 5-year period.

(b) Where the target is not met, the Secretary shall report to the Congress on the shortfall and its projected effect on age-specific mortality trends.

### Sec. 404. Evaluation

Each program funded under this Title shall include an evaluation component specifying the age-specific mortality outcome it is intended to affect and the timeframe over which an effect would be detectable.

---

## TITLE V: IMPLEMENTATION AND FUNDING

### Sec. 501. Authorization of appropriations

There are authorized to be appropriated:

(a) **$1,200,000,000** annually for fiscal years 2027 through 2031 to carry out Title I, of which not less than 40 percent shall be allocated to section 103;

(b) **$450,000,000** annually for fiscal years 2027 through 2031 to carry out Title II, of which not less than 60 percent shall be directed to jurisdictional reporting infrastructure under section 203;

(c) **$35,000,000** annually for fiscal years 2027 through 2031 to carry out Title III;

(d) Such sums as may be necessary to carry out Title IV, consistent with the growth target in section 403.

### Sec. 502. Coordination

The Secretary shall designate a single official responsible for coordination across Titles I through IV and for resolving conflicts between the requirements of this Act and existing reporting obligations.

### Sec. 503. State and territorial participation

Nothing in this Act preempts State authority over vital statistics collection. Funding under section 501(b) is conditioned on participation in the reporting-latency reduction plan under section 203.

---

## TITLE VI: ACCOUNTABILITY AND SUNSET

### Sec. 601. Independent evaluation

(a) The Secretary shall enter into an arrangement with the National Academies of Sciences, Engineering, and Medicine for an independent evaluation of implementation, to be delivered not later than 4 years after enactment.

(b) The evaluation shall assess, at minimum: whether the latency target in section 203 was met; whether age-stratified reporting under Title III changed the content of public communication; and whether the investment under Title IV was associated with measurable change in age-specific mortality.

### Sec. 602. Sunset and reauthorization

The authorities under Titles I, III, and IV expire on September 30, 2031, unless reauthorized. Title II does not sunset, on the finding that surveillance infrastructure assembled and dismantled on a cycle is the specific failure this Act exists to correct.

### Sec. 603. Reporting to Congress

The Secretary shall submit an annual implementation report addressing each Title separately and identifying any provision the Department has been unable to implement, with the reason.

---

## Drafting notes

*This section is for working reviewers and would be removed before public release.*

**What is stress-test ready.** The Title II and Title III provisions are the strongest part of this framework. They are procedural, they use capability that already exists inside NCHS, and they impose modest cost. Section 204 (independence) and section 602 (Title II does not sunset) are the two provisions most worth defending in negotiation, because they address the failure mode the paper actually documents: surveillance treated as an emergency measure rather than infrastructure.

**What gets renegotiated immediately.** The dollar figures in section 501, all of them. The 90-day stockpile in section 103(b) will be contested on cost and on storage practicality. The 10 percent growth target in section 403 has no analytic basis in the companion paper and would be the first thing a committee strikes; it is included because a target with a number attached forces the argument to happen, but do not defend it as a finding.

**Known weak points.** Section 103(c), minimum infection-prevention staffing standards, intrudes on an area of active dispute between federal and state regulators and would likely need to be recast as a conditions-of-participation matter rather than a direct standard. Section 104's allocation-weighting language will draw equity objections in any real process: weighting purely by age-specific mortality risk is defensible on a years-of-life-lost framing and indefensible on several others, and the draft does not resolve that tension. It should be resolved before circulation, not during.

**Scope note.** This is drafted federal. Adapting it for state adoption is largely mechanical, substituting the State department of health and scaling appropriations, but the Preamble's evidence basis would need to be rebuilt on State-level mortality data. National findings do not transfer.
