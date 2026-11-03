# Maintenance and corrections

Resource contact: **ZiBo Zhang**, **2024303090204@cau.edu.cn**.
Reports are handled through the repository issue tracker or this contact.
Response times depend on maintainer availability; no fixed service level,
funding commitment or institutional service guarantee is specified.

## Immutable releases

Use semantic versioning for the resource schema and dated immutable data
snapshots. Publish a manifest and a permanent archived copy for each paper
revision. A content correction creates a new snapshot; do not alter an archived
test answer, source hash, split or outcome in place. Keep the previous release
available, with a machine-readable migration log identifying affected IDs.

## Issue intake

Open a repository issue with the question ID, original/amended accession,
source URL/hash, locator, disputed field, expected interpretation and supporting
source text. A suspected issue does not require an authoritative accounting or
legal conclusion. Keep reviewer identities and private contact details out of
public issues. Send sensitive concerns to the maintenance email above.

## Triage and adjudication

Separate source-access failures, corrupted hashes, technical locator defects,
question ambiguity, evidence-sufficiency disputes and event-category disputes.
Technical checks can be automated. Semantic corrections and high-risk category
changes go through source review and the established human adjudication process.
AI suggestions remain provisional. Preserve the old field, proposed field,
reason, source hashes and true reviewer approval record; never backfill a blank
human approval with software output.

## Version impact

For each approved change, record affected question/state/event IDs and whether
the source bytes, question, answer, unit, period, provenance or split changed.
Rerun only the relevant validation/derived metrics under the new version name.
Do not delete failed examples to improve a reported score. Historical model
outputs remain tied to their original data hashes; a re-evaluation receives a
new run ID and is not silently substituted into the original paper table.

## Availability checks

At release and before a revision, verify archive restoration, loader/scorer
tests, manifest coverage, links and documented source-fetch behavior. If the SEC
source changes or disappears, preserve the original hash and record the access
failure; use a permission-cleared archival remedy rather than replacing it with
another year's fact. Respect the SEC declared User-Agent and conservative rate
limit. Retain license notices and review their terms when dependencies change.

## Service continuity

Issues can be reported to the contact above. No fixed response SLA is promised.
If active maintenance ends, mark the project archived and retain versioned
downloads and the last-maintained date.
