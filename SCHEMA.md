# Schema and input boundaries

Files are UTF-8 JSON Lines, except manifests/cards. JSON object keys are not an
ordering contract. Unknown resource schema versions must fail rather than be
interpreted silently. Source-file identities are SHA-256 of original bytes.

## Public query envelope

`query_id` is a stable administrative key `question_id/original` or
`question_id/amendment`. It is not model input. `model_input` contains exactly:

- `question`: the frozen natural-language English question;
- `cutoff`: an ISO-8601 UTC SEC Accepted-clock cutoff;
- `clock_protocol`: `SEC_acceptance_proxy_not_verified_publication`;
- `instruction`: the fixed instruction to select applicable visible evidence.

The loader rejects extra fields in this envelope. It does not return gold
answers, reference locators, event categories or target accession. Model prompts
must contain only the four fields plus independently constructed public evidence.

## Public filing and source metadata

`public/filings.jsonl` identifies accession, CIK, accepted time, its clock
protocol and official index URL/hash. `retrieval_corpus_documents.jsonl` adds
primary document URL/hash, form, report period, issuer name and corpus split.
`sources.jsonl` records source URL/hash, kind and accession. `bytes` can be null
for restored distractor-manifest records; they are bound by the accepted public
corpus hash and must pass SHA verification when downloaded. They were not all
downloaded again when assembling this package.

Whole source bodies are not embedded. Reference locators must not be used to
construct the autonomous retrieval corpus or prioritize evidence.

## Offline references

One row per query state contains `question_id`, `event_id`, `issuer_cik`, `phase`,
`answer`, `unit`, `period`, `accession`, `document_id`, and `evidence_locators`.
Locators retain `kind`, `url`, `sha256` and `xpath`. `reference_only` is always
true. `answer_changed_between_versions` is the retained mechanical pair flag.
`legacy_query_as_of_preserved` is historical provenance, not the operative
cutoff. `historical_evaluation_eligible` preserves the old candidate boolean;
it is not silently rewritten to express the later experimental admission.

`review_record_status` describes the accepted owner-confirmed process without
inventing a new reviewer judgment. `returned_adjudication_outcome` copies the
existing categorical decision. Any `machine_semantic_period_annotation` remains
explicitly labeled and cannot be promoted to a separate human label.

`xbrl_target_contexts.jsonl` maps each existing XML check to the query, source
URL/hash/XPath and accepted parser-result hash. Fact nodes preserve qualified
concept, original context/unit IDs, raw value, XML context/unit and dimensions.
Context-only/unit-only locator checks preserve their XML rather than inventing
numeric facts. Prefix declarations are retained by lxml serialization.

## Requests and responses for `score.py`

Each sealed request contains `query_id`, `condition`, `messages`, `evidence`,
and `input_sha256`. The message hash is SHA-256 of UTF-8
`json.dumps(messages, sort_keys=True, ensure_ascii=False)` with Python's default
separators, matching the accepted runner. The second message is a JSON object
with exactly `request` and `evidence`; the former equals the four public fields
and the latter equals the recorded evidence list. Each evidence item identifies
`chunk_id`, `accession`, `source_url`, `source_sha256`, `accepted_at_utc` and text.

Each response retains `query_id`, `condition`, `input_sha256`, `status`,
`raw_text`, `parsed`, and generated-token count. Token IDs, prompt tokens,
inference time, cache provenance and model revision remain in the original
runner record and are not replaced by this scorer. `parsed` is checked by
re-parsing raw text; it cannot be supplied independently as an unsupported
correct answer. An absent response becomes `missing_output` in the denominator.
An absent request is an invalid experiment envelope and stops scoring.

The scorer validates source identity and proxy cutoff. It does not reconstruct
excerpt bytes from HTML or establish entailment. The accepted source-rebuild and
token-replay scripts remain separate evidence for historical experiments.

## Metric definitions

`numeric_exact` requires strict protocol validity and finite Decimal equality.
In the historical `legacy` profile, `numeric_and_unit` additionally uses the
fixed USD/shares alias dictionary. New evaluations must declare their profile.
`accession_correct` requires exact accession equality. The main joint metric is
the conjunction of all three. The pair metric requires both states to satisfy
the joint criterion. False-change and stale-original flags are mechanical
diagnostics with validity guards, not semantic change explanations.

Issuer-cluster bootstrap intervals preserve correlated questions/states within
an issuer. Small changed subsets must retain their denominator and issuer count.
The independent gate is outside this package and its reported results.

## Explicit scoring profiles

`score.py` remains the immutable historical scorer. The version-3 entrypoint
`score_profiles.py` adds a preflight coverage report and defaults to `legacy`.
It refuses scoring when that profile does not support every reference unit;
unsupported cases are never silently removed from the denominator. Legacy
coverage is 564/582 train, 144/144 dev and 206/210 ordinary-test states.

`resource-native-v1` retains legacy aliases and adds these exact case-insensitive
spellings after trimming outer whitespace:

| Canonical unit | Additional accepted spellings |
|---|---|
| CAD | `CAD`, `iso4217:CAD` |
| USD/share | `USD/share`, `USD per share`, `iso4217:USD per xbrli:shares` |
| pure | `pure`, `xbrli:pure` |

No other new aliases or conversions are applied. In particular percent, `%`,
ratio, `C$`, scale qualifiers and guessed currencies are unsupported. The old
USD `$` alias remains USD and cannot match a CAD reference. Exact finite Decimal
equality, strict raw JSON parsing, source identity/cutoff verification, all
failure denominators and pair metrics otherwise retain their definitions.

Native-unit validation checks all original and amended unit strings agree and
that exact Decimal comparison agrees with the retained change flag. A future
unit-changing pair requires a new protocol; the tool refuses to infer its
meaning. No reference label is rewritten. The profile identifier, historical
scorer hash and entrypoint hash are mandatory output provenance. Historical
model tables continue using the legacy metric, including its unsupported-unit
failures. A later uniform retained-output audit used the native profile on
25,930 canonical QA records without regenerating answers. Two Qwen
complete-source diagnostic pure states changed credit (154 to 156/210 joint;
74 to 75/105 paired); autonomous main results did not change. Legacy records
remain retained and separately identified. The historical 144-state dev
replay agrees across both profiles because all dev reference units are supported;
that replay is outside this core package.

## Audit-only wording lineage

`audit/wording_lineage.jsonl` is sealed by the package manifest, outside the
unchanged scientific data manifest. It contains 468 question IDs, split/event
IDs, exact reviewed/public question strings, their SHA-256 values and the
retained transformation category. 240 strings are verbatim; 61 cutoff-applicability
and 167 prefix replacements retain the historical
`additional_human_equivalence_pending` status in that immutable audit snapshot.
Current completion status is supplied separately by `CURRENT_REVIEW_STATUS.json`
and the author's subsequent batch confirmation. The additional item-level
human-equivalence field stays null; no per-item human decision is inferred. `audit_only=true` and
`replaces_historical_model_input=false` prevent interpreting this as a silent
input migration. The reviewed text can support a separately frozen future task,
but does not inherit scores produced for the projected public request.


## Paired diagnostic v2

`paired_diagnostics_v2.py` explicitly reports comparison_assessable, unassessable reasons, unknown-unit sides, false-change/full-unchanged and false-change/assessable-unchanged denominators. Unknown units cannot imply change or stability. The old scorer/profile files remain frozen, primary metrics unchanged. See QUICKSTART_NEW_COMPONENT.md for exact output and request construction.
