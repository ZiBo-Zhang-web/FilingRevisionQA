# FilingRevisionQA

FilingRevisionQA pairs numerical questions across original and amended SEC
filings. It contains 468 question pairs, 936 states and 144 issuers, with
version-specific answers, units, filing accessions, source locators and hashes.
The tools support numerical, unit, source and paired-state evaluation.

**Version:** v1.0.0  
**Repository:** https://github.com/ZiBo-Zhang-web/FilingRevisionQA  
**Contact:** ZiBo Zhang, 2024303090204@cau.edu.cn

## Quick start

Python 3.10 or later is sufficient; no installation or GPU is needed for the
loader, scorer or examples. Download the repository ZIP, extract it into an
empty directory, and run these commands from the extracted directory:

```bash
python -B -S verify_package.py
python -B -S frqa_resource.py --data data --expected-manifest-sha256 973bd4741e0cbc5182232bcade24212d9471ce7ae0e7b4ed8054a2fcfa5468e4
python -B -S example_pair.py
python -B -S demo_no_evidence.py --output ../frqa-interface-demo
python -B -S -m unittest test_resource test_score_profiles test_standalone test_paired_diagnostics_v2 test_component_requests -v
```

`example_pair.py` loads a development question at both cutoffs. The interface
demo uses synthetic abstentions to exercise request construction and scoring;
it makes no model calls and supplies no benchmark result. Keep generated
outputs outside the extracted directory. The exact-file verifier expects the
distributed archive contents, without a local Git checkout's `.git` directory.

## Evaluate a retriever or reader

Follow [the component guide](QUICKSTART_NEW_COMPONENT.md) to load queries,
retrieve eligible evidence by issuer and cutoff, record requests and raw
responses, and score them offline. Reference answers and audit mappings are
reserved for scoring and isolated diagnostics. This interface supports new
components; historical prompts, extraction environments and model-output
archives are separate research artifacts.

## Package contents

| Location | Contents |
|---|---|
| `data/public/` | Query inputs, filing metadata and corpus routing |
| `data/offline_references/` | Answers, units and designated sources for scoring |
| `data/sources.jsonl` | 938 official source URL/hash records |
| `audit/wording_lineage.jsonl` | Reviewed/public wording mappings and transformation history |
| `CURRENT_REVIEW_STATUS.json` | Current batch-confirmed wording review scope |
| [SCHEMA.md](SCHEMA.md) | Fields, input boundaries and metric definitions |
| [RESOURCE_CARD.md](RESOURCE_CARD.md) | Population, review coverage and evaluation conditions |
| [REVIEW_AND_PROVENANCE.md](REVIEW_AND_PROVENANCE.md) | Interpretation of review and source records |

## Scope of this release

This release contains the complete 468-pair dataset, the interface for evaluating
new components, and the English and Chinese supplementary paper documents.
Historical predictions, training configurations and table-generation assets
remain outside this package. The PDFs document the experiments and review scope;
they do not replace the raw artifacts required to replay every paper result.

## Supplementary materials

- [English supplementary materials](supplementary/FilingRevisionQA_EN_Companion.pdf)
- [Chinese supplementary materials](supplementary/FilingRevisionQA_ZH_Companion.pdf)

These are the retained 3 November 2026 PDF versions. Historical preparation and
availability statements in the PDFs describe their document snapshot; the
repository files and scoped license notices describe the current package.

The data files preserve the original snapshot. In `data/manifest.json`,
`release_status` records its internal-preview origin; in `data/REVIEW_COVERAGE.json`,
`public_release_approval` records its earlier preparation status. These historical
fields do not describe the current license decision. The current scoped license
grants are in `LICENSE` and `RIGHTS_SCOPE.md`, package authorization is recorded in
`PACKAGE_MANIFEST.json`, and the maintainer is named in `RELEASE_STATUS.json`.

## Retrieve source documents

```bash
python -B -S download_sources.py --data data --cache ../source-cache
```

The default command produces an offline download plan. To fetch a source,
configure `SEC_USER_AGENT` locally with a monitored contact, select its
`--source-sha256`, and add `--execute`. The client uses official HTTPS hosts,
caching, a maximum rate of two requests per second and exact hash verification.
Keep the contact setting outside the repository. Record access failures without
substituting different source bytes. Offline integrity checks and live source
restoration are distinct checks.

## Evaluation scope

The issuer-disjoint train, development and ordinary-test splits contain
291, 72 and 105 pairs. Ordinary test was exposed during earlier research;
subsequent comparisons are supplementary, and repeated development comparisons
are exploratory. The protected independent gate is excluded. The native
scoring profile covers USD, shares, CAD, USD/share and pure, retaining failures
in the denominator. Exact designated-accession agreement measures source
identity rather than evidence sufficiency or semantic entailment. Eleven event
categories remain unresolved; their numerical QA records are retained.

## Citation, rights and maintenance

Use [CITATION.cff](CITATION.cff) for citation and [AUTHORS.json](AUTHORS.json) for
author information. No DOI has been assigned. Project-owned code uses MIT;
original project contributions to questions, annotations and documentation use
CC BY 4.0. Third-party material is excluded from these grants. See
[LICENSE](LICENSE), [RIGHTS_SCOPE.md](RIGHTS_SCOPE.md) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Full filings, external benchmark
datasets and model weights are not mirrored. [MAINTENANCE.md](MAINTENANCE.md)
describes issue reporting and versioned corrections.
