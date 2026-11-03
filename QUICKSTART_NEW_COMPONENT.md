# New component quickstart

This guide connects public query inputs, independently retrieved evidence and offline scoring. Use Python 3.10+; constructing requests and scoring retained outputs require no GPU or third-party package. The package licenses and third-party exclusions are described in LICENSE and RIGHTS_SCOPE.md.

1. Verify the package: `python -B -S verify_package.py`.
2. Load public dev inputs with `Resource("data").load_inputs("dev")`. Route query_id outside the model prompt. Issuer is retrieval metadata in split membership; only model_input is serialized into the public request.
3. Fetch official source files with the manifest client if needed, respecting the existing monitored User-Agent and cache rules. Build your own chunks from publicly eligible filings. Historical exact extraction additionally requires the pinned parser/retrieval assets listed in the companion provenance; this package does not silently substitute a new chunker for them.
4. Save one evidence row per scheduled query:
   `{"query_id":"…/original","evidence":[…]}`.
   Each evidence object preserves chunk_id, accession, source_url, source_sha256, accepted_at_utc and your text. Use an empty array if no evidence is available. Never use offline_references or audit mappings for autonomous retrieval.
5. Freeze requests:
   `python -B -S build_component_requests.py --split dev --condition my_reader --evidence ../evidence.jsonl --output ../jobs.jsonl`.
   This is a new component prompt, not the historical experimental prompt. It checks source identity, issuer and cutoff, but not excerpt entailment.
6. Run your model against exactly the sealed messages, retain raw_text and input_sha256, and parse with `score.parse_response(raw_text, job["evidence"])`. Save query_id, condition, input_sha256, raw_text, status, parsed and generated_tokens. Preserve every failure. Do not trim code fences or repair answers.
7. Score offline:
   `python -B -S paired_diagnostics_v2.py --split dev --conditions my_reader --requests ../jobs.jsonl --responses ../responses.jsonl --output ../score-v2`.

A syntactically valid answer has exactly these keys:

```json
{"answer":"100","unit":"USD","accession":"the-provided-accession","citations":["E1"]}
```

Canonical abstention:

```json
{"answer":null,"unit":null,"accession":null,"citations":[]}
```

An unknown unit string can be protocol-valid but cannot receive unit/joint credit. Its paired comparison is unassessable, not evidence of either change or stability. The full denominator remains. Missing outputs also remain in the denominator. Response length limits and all historical parsing rules remain unchanged.

The loader and model-input construction exclude reference values. Only the explicit offline scoring step loads references. This is an API separation and reproducibility boundary, not a secrecy guarantee.

## Version map

- `score.py`: immutable historical USD/shares scorer.
- `score_profiles.py`: immutable legacy/native-unit profile interface.
- `paired_diagnostics_v2.py`: new assessability-aware diagnostics over resource-native-v1. Primary number, unit, accession and J/P rules are unchanged.
- `demo_no_evidence.py`: synthetic no-evidence/abstention interface demonstration. The historical model replay is retained internally and excluded from this core.
- `test_paired_diagnostics_v2.py`: synthetic diagnostic regressions.

The review repair found 239 condition-pair classifications across the frozen retained-output inventory that the old packaged diagnostic called false changes despite unknown units. They are repeated condition records, not 239 independent questions. The historical audit already guarded assessability; its reported main J/P and false-change counts are unchanged. The full report and per-record differences are retained in the research archive and are outside this core package.

Resource contact: ZiBo Zhang, 2024303090204@cau.edu.cn. These commands construct local requests and scores; they do not upload data. See RIGHTS_SCOPE.md for the adopted licenses and MAINTENANCE.md for corrections.
