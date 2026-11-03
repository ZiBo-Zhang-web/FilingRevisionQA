# FilingRevisionQA resource card

**Version:** v1.0.0. Repository: https://github.com/ZiBo-Zhang-web/FilingRevisionQA.
No DOI has been assigned. The data snapshot is
`human-return-v4-reconciled-20261025-resource-preview-20261027`.
Documentation packaging revision r3 retains the data and scoring code identities.

## Task and population

Same-question financial QA is paired between original and amended SEC filing
states under a declared SEC Accepted-time cutoff proxy. The resource supports
numerical, unit, designated-accession and both-state evaluation. Exact accession
matches measure compliance with the specified source task; they do not prove
citation entailment or financial reasoning. An amendment does not itself imply
a restatement, fraud, misconduct or issuer risk.

| Split | Pairs | States | Issuers | Changed pairs |
|---|---:|---:|---:|---:|
| Train |291|582|91|26|
| Dev |72|144|24|5|
| Ordinary test |105|210|29|11|
| Total |468|936|144|42|

Issuers are disjoint. The selected set comes from the historical 890-pair,
220-event construction pool, not a random SEC sample. The event-category layer
contains 59 big-R, 73 ordinary amendments, 1 little-r and 11 unresolved events.
The 11 unresolved events contain 45 questions and stay unresolved. Unchanged
answers dominate (426 pairs); the changed dev/test subsets have only 5/10
issuers respectively. Multiple states, same-issuer questions and training seeds
must not be counted as independent examples.

## Contents and provenance

The package has 936 public request envelopes with four model fields, explicit
offline references, 336 filing identities, dev/test retrieval pools of 70/84
whole public documents, and 938 official source-file URLs/hashes. Source bodies
are excluded. It retains accession, cutoff proxy, period, unit, XPath, SHA and
existing XBRL concept/context/dimension provenance. The 1,555 accepted parser
check records cover 860 XML states; 76 states use HTML. These are prior technical
checks, not newly observed human semantic review.

The source manifest and offline references are separate. `Resource.load_inputs`
does not return answers/target sources. `load_references` is an explicit offline
API. The protected independent gate is not included or exposed by the loader.
Reference source mappings must not be given to autonomous candidate systems.

Original questions/references have A/B and adjudication lineage. The public
question set contains 240 verbatim and 228 projected stems (61 temporal and 167
prefix transformations). The author subsequently confirmed completion of human
review for the projected wordings. Both wording versions, the transformation
records and the batch attestation remain traceable. The attestation does not
supply individual reviewer identities, dates or item-level decisions; historical
null fields remain unchanged. See `REVIEW_AND_PROVENANCE.md` and
`CURRENT_REVIEW_STATUS.json` for the current and historical record boundaries.

## Evaluation identity and limits

The ordinary test has been exposed in supplemental experiments; later results
are not independent confirmations. Repeated dev candidate search and seed
replication do not establish unseen-issuer generalization. Historical predictions
and failures are retained with full denominators; no test row was removed to
improve a score. Source-supported training uses a subset of the train split and
does not demonstrate uniform learnability across unsupported cases.

The historical scorer is immutable. `resource-native-v1` adds closed aliases
for CAD, USD/share and pure and is the explicit complete-unit profile. It never
rescales numeric values or relaxes syntax. The later uniform retained-output
audit covered 25,930 canonical QA records. Only 2 Qwen complete-source diagnostic
pure states changed credit: J 154→156/210, paired 74→75/105. Autonomous main results
were unchanged. This is a versioned CPU correction, not new model inference.
Legacy and native scores must be labeled and not silently mixed.

The strict output contract also measures protocol compliance. Invalid JSON,
missing answers, abstention, length limits and no-evidence failures remain in
the denominator. A citation/accession mismatch is not automatically evidence
of choosing the wrong historical filing; accession agreement does not certify
supporting text. Numeric correctness, unit agreement and source identity must
be reported alongside conjunction and pair outcomes.

## Use, availability and maintenance

This package preserves the scientific data and scorer bytes. Python
3.10+ standard library is sufficient for loading and scoring. Whole source
documents require the official URL/hash downloader and an appropriate monitored
User-Agent. The zero-model interface demo is explicitly synthetic; historical
144-state excerpt/output replay is retained internally and excluded here.
Private correspondence is replaced by a public review-scope summary, not new
labels. Authors and the designated maintainer are in AUTHORS.json. Project-held
rights use the scoped MIT/CC-BY-4.0 grants in LICENSE. RELEASE_STATUS.json
identifies the package version and repository. See RIGHTS_SCOPE.md and MAINTENANCE.md.
