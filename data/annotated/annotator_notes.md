# Annotation guidelines — gold collocations

The gold file is `gold_collocations.csv`. Each row is one phrase that the annotator accepts as a collocation worth tagging in a municipal voice memo. Columns:

- `phrase` — space-separated lemmas, the same form the pipeline emits
- `ngram` — 2 or 3
- `category` — `business`, `project`, `technical`, or `meeting`
- `frequency` — count in the preprocessed corpus (sentence-internal, lemmatized)

The list was built on 2026-10-05 from the MeetingBank subset in `data/raw_transcripts/`, after the preprocessing in `src/preprocessing.py` (lowercase, clitic repair, POS-aware lemmatization, stopwords retained). Every row was checked against those counts. Nothing below frequency 3 was kept. The current size is 104 bigrams and 40 trigrams (144 phrases).

## What counts as a domain collocation

A domain collocation is a multiword expression a tagging system should treat as a unit in council speech. It is one of:

- an institutional name or title (`city council`, `vice mayor`, `police department`)
- a fixed procedural formula (`motion to`, `roll call`, `those in favor`, `president pro tem`)
- a policy, finance, or planning term (`affordable housing`, `general fund`, `zone district`, `domestic violence`)
- a fixed place, facility, event, or personal name used as a referent (`long beach`, `mile high stadium`, `pat bowlen`)

The expression is conventional. Speakers do not freely swap the pieces (`strong housing` is not `affordable housing`; `beach long` does not occur).

Category assignment:

- `meeting` — procedure, roles, forms of address, and named people
- `business` — budget, tax, fees, housing finance, real estate, labor pay
- `project` — plans, land use, sites, facilities, and place names
- `technical` — departments, infrastructure, public safety, and code terms

Lemmatization is part of the phrase identity. `civil rights` is stored as `civil right`. `paid sick` is stored as `pay sick` because the tagger lemmatizes `paid` as a verb. `in terms of` is stored as `in term of`. The gold phrase is the string the ranker can actually emit.

## What is a random co-occurrence

A random co-occurrence is two or three words that sit next to each other without forming a reusable name or formula. Examples from this corpus that were rejected even when frequent:

- `last year`, `two week`, `year ago` — ordinary time expressions with free substitution
- `go back`, `come back`, `move forward`, `look forward` — compositional verb plus particle
- `number one`, `phase two` — a head plus a counter, not a fixed title
- `mm hmm` — a backchannel, not a tag
- name fragments that are only alphabetical residue of a longer title the annotator did not judge to be the unit (`real estate master` was kept as the start of a plan name; bare `dash two` was not)

Frequency alone never qualifies a pair. `of the` is the second most common bigram and is not gold.

## What is compositional but frequent

These recur because of grammar or discourse habit, not because the memo's topic is that phrase. They are not gold. The qualitative review may still call them acceptable discourse formulas when they are fixed, or junk when they are only syntax.

- grammatical glue: `of the`, `in the`, `to the`, `on the`, `and the`
- copula patterns after lemmatization: `this be`, `there be`, `we be` (`is` / `are` / `was` all become `be`)
- discourse formulas that are fixed but are not domain tags: `thank you`, `you know`, `kind of`, `make sure`, `as well`, `i want to`, `a lot of`
- the politeness trigram `thank you mr`

`in term of` is the exception that is on the gold list. It is the fixed discourse collocation `in terms of`, included so the stopword trade-off can be measured. It is not a topic tag. The notes in the evaluation treat it as a fixed phrase, and the inclusion criteria above would have left it off a pure topic list. It is marked `meeting`.

`motion to` and `those in favor` contain function words and are gold because they are procedural formulas, not because function words are generally allowed.

## Inclusion procedure

1. Rank bigrams and trigrams by frequency and by PMI at frequency at least 3.
2. Read the content-word slice (neither token a stopword) down through frequency 4 for bigrams and 3 for trigrams.
3. Accept a phrase only if it matches the domain-collocation definition and the count is at least 3.
4. Write the count from the same counter the pipeline uses, not from a whitespace search of the raw files.

Rejected high-frequency items were mostly grammar (`of the`), discourse (`thank you`), or compositional time and motion phrases. Rejected rare PMI pairs were mostly backchannels or pairs the annotator could not defend as a reusable tag (`mm hmm`). Some genuine names were still left out: not every `councilmember` plus surname was listed, and not every street in a site plan was listed. The file is a curated sample.

## Evaluation caveat

This list is not exhaustive. Council speech contains more fixed phrases than were labeled, including speaker names, street names, and ordinance shorthand that failed the "would I tag this" test or were simply not reached. A top-20 phrase that is absent from the gold file is therefore not automatically junk.

Precision at 20 measured against this file is a lower bound on precision against the full set of true collocations, not a claim that the other 20-minus-hits items are errors. Recall at 20 uses this list as the denominator, so it is recall against the curated list only. Do not read either number as agreement with an exhaustive reference.
