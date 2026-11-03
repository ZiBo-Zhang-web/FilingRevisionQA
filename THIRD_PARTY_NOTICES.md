# Third-party and source-derived material

Source filings were submitted by issuers and are hosted by the U.S. Securities
and Exchange Commission. Hosting is not an ownership transfer. The project
claims neither SEC endorsement nor blanket rights in issuer expression.

* `data/sources.jsonl` binds official URLs, accessions and exact SHA-256 values.
* `data/offline_references/{train,dev,test}.jsonl` binds each reference's values,
  units, periods and `evidence_locators` to its source; these are facts and pointers.
* `data/offline_references/xbrl_target_contexts.jsonl` retains source-derived
  `nodes[].context_xml`, `unit_xml`, `xml`, `dimensions[].xml`, and taxonomy names,
  IDs and numeric values. Each record supplies URL, source SHA and XPath.
  These technical fragments are excluded from our license grant. Taxonomy
  namespace URLs identify their upstream origins; no taxonomy files are mirrored.
* Financial line-item names and short labels embedded in question wording keep
  their source identity; the project's license covers its original wording only.

Full HTML/XML filings, tables as images, filing narrative passages, third-party
benchmark datasets and model weights are not distributed. FinRank, FinQA, HoH
and VersionRAG are not included. Python standard-library imports are runtime
dependencies, not vendored library copies. CC license legal text retains its
own notices. LICENSE_INVENTORY.json records excluded research dependencies.

Exact source-file restoration requires internet access and a monitored SEC
User-Agent. The downloader defaults to a zero-network plan and checks hashes
when execution is requested. Source access failures must be recorded, not
worked around by substituting unverified text or changing reference answers.
