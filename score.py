"""Standalone mechanical B scorer; exact Decimal/alias/strict JSON policy.

Counts failures and missing outputs in the fixed denominator. Gold references
are read only by this offline process. Raw text is re-parsed against the recorded
evidence. This is not an entailment or financial-statement correctness scorer.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from datetime import datetime
import hashlib
import json
from pathlib import Path
import random

from frqa_resource import Resource, read_rows, sha

VALID = "valid_protocol_not_semantic_certification"


def message_sha(messages):
    return hashlib.sha256(json.dumps(messages, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def verify_requests(resource, split, requests):
    """Check public query, source identity, issuer and Accepted-clock cutoff.

Source bytes/text entailment require the separate source-restoration verifier;
this check does not certify that an excerpt is semantically sufficient.
"""
    queries = {r["query_id"]: r["model_input"] for r in resource.load_inputs(split)}
    filings = {r["accession"]: r for r in resource._rows("public/filings.jsonl")}
    sources = {(r["url"], r["sha256"]): r for r in resource._rows("sources.jsonl")}
    for job in requests:
        q = queries[job["query_id"]]
        messages = job["messages"]
        if job["input_sha256"] != message_sha(messages):
            raise ValueError("Frozen request/message hash mismatch")
        if len(messages) != 2 or messages[0]["role"] != "system" or messages[1]["role"] != "user":
            raise ValueError("Unsupported message envelope")
        payload = json.loads(messages[1]["content"])
        if set(payload) != {"request", "evidence"} or payload["request"] != q or payload["evidence"] != job["evidence"]:
            raise ValueError("Model message diverges from public query/evidence")
        ids = [e["chunk_id"] for e in job["evidence"]]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate evidence chunk IDs")
        issuer = resource.membership[job["query_id"].split("/")[0]]["issuer_cik"]
        cutoff = datetime.fromisoformat(q["cutoff"].replace("Z", "+00:00"))
        for e in job["evidence"]:
            f = filings[e["accession"]]
            s = sources.get((e["source_url"], e["source_sha256"]))
            if s is None or s["accession"] != e["accession"] or f["issuer_cik"] != issuer:
                raise ValueError("Evidence source identity/issuer mismatch")
            if e["accepted_at_utc"] != f["accepted_at_utc"]:
                raise ValueError("Evidence accepted-time metadata mismatch")
            if datetime.fromisoformat(e["accepted_at_utc"].replace("Z", "+00:00")) > cutoff:
                raise ValueError("Future evidence is forbidden in autonomous resource conditions")
    return {"requests_verified": len(requests), "future_sources": 0,
            "verification": "Message hash, public request, source URL/hash/accession, issuer, Accepted-time cutoff",
            "not_certified": "Excerpt byte reconstruction, semantic sufficiency, explanation faithfulness or exact publication instant"}


def unit(value):
    x = str(value).strip().lower().replace(".", "").replace(" ", "")
    return {"usd": "USD", "usdollars": "USD", "us$": "USD", "$": "USD", "iso4217:usd": "USD",
            "shares": "shares", "share": "shares", "xbrli:shares": "shares"}.get(x)


def numeric_equal(a, b):
    try:
        x, y = Decimal(str(a)), Decimal(str(b))
        return x.is_finite() and y.is_finite() and x == y
    except InvalidOperation:
        return False


def parse_response(raw, evidence):
    # Same accepted parser as resource_evidence/reader_protocol.py plus its
    # predeclared TypeError guard for list/dict accession. No Markdown repair.
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        return "invalid_json", None
    if not isinstance(value, dict) or set(value) != {"answer", "unit", "accession", "citations"}:
        return "invalid_schema", value
    if not isinstance(value["citations"], list) or not all(isinstance(x, str) for x in value["citations"]):
        return "invalid_citations", value
    ids = {e["chunk_id"]: e["accession"] for e in evidence}
    if any(x not in ids for x in value["citations"]):
        return "unknown_citation", value
    if value["answer"] is None:
        return "abstained", value
    if not isinstance(value["answer"], str) or not isinstance(value["unit"], str) or not value["citations"]:
        return "invalid_schema", value
    try:
        if not Decimal(value["answer"]).is_finite():
            return "invalid_numeric", value
    except InvalidOperation:
        return "invalid_numeric", value
    if isinstance(value["accession"], (list, dict)):
        return "invalid_schema", value
    if value["accession"] not in set(ids.values()) or any(ids[x] != value["accession"] for x in value["citations"]):
        return "citation_accession_mismatch", value
    return VALID, value


def same_number_unit(a, b):
    return bool(numeric_equal(a.get("answer"), b.get("answer")) and unit(a.get("unit")) is not None and unit(a.get("unit")) == unit(b.get("unit")))


def metrics(response, reference):
    p = response.get("parsed") if isinstance(response.get("parsed"), dict) else {}
    valid = response["status"] == VALID
    number = bool(valid and numeric_equal(p.get("answer"), reference["answer"]))
    number_unit = bool(number and unit(p.get("unit")) is not None and unit(p.get("unit")) == unit(reference["unit"]))
    accession = bool(valid and p.get("accession") == reference["accession"])
    return {"valid": valid, "numeric_exact": number, "numeric_and_unit": number_unit,
            "accession_correct": accession, "numeric_unit_accession_joint": bool(number_unit and accession),
            "numeric_correct_wrong_accession": bool(number and not accession),
            "numeric_unit_correct_wrong_accession": bool(number_unit and not accession)}


def unique_index(rows):
    out = {}
    for row in rows:
        key = row["query_id"], row["condition"]
        if key in out:
            raise ValueError("Duplicate record: " + str(key))
        out[key] = row
    return out


def percentile(values, p):
    a = sorted(values)
    index = (len(a)-1)*p
    i = int(index)
    return a[i] if i+1 == len(a) else a[i] + (index-i)*(a[i+1]-a[i])


def cluster_interval(rows, field, seed=20261027, repetitions=10000):
    if not rows:
        return {"numerator": 0, "denominator": 0, "issuer_clusters": 0, "rate": None, "ci95": None}
    groups = defaultdict(list)
    for r in rows:
        groups[r["issuer_cik"]].append(bool(r[field]))
    stats = [(len(v), sum(v)) for _, v in sorted(groups.items())]
    rng = random.Random(seed)
    samples = []
    for _ in range(repetitions):
        draw = [stats[rng.randrange(len(stats))] for _ in stats]
        samples.append(sum(n for _, n in draw)/sum(d for d, _ in draw))
    n = sum(bool(r[field]) for r in rows)
    return {"numerator": n, "denominator": len(rows), "issuer_clusters": len(stats), "rate": n/len(rows),
            "ci95": [percentile(samples, .025), percentile(samples, .975)]}


def score(references, responses, requests, conditions):
    if not conditions or len(set(conditions)) != len(conditions):
        raise ValueError("Conditions must be nonempty and unique")
    refs = {r["query_id"]: r for r in references}
    if len(refs) != len(references):
        raise ValueError("Duplicate references")
    expected = {(q, c) for q in refs for c in conditions}
    rx, jx = unique_index(responses), unique_index(requests)
    if not set(rx) <= expected or not set(jx) <= expected:
        raise ValueError("Unexpected condition/query; explicit split and conditions are required")
    if set(jx) != expected:
        raise ValueError("Sealed request coverage must be complete")
    states, pair_rows, used = [], [], {}
    for query_id, condition in sorted(expected):
        reference, job = refs[query_id], jx[query_id, condition]
        if job.get("input_sha256") != message_sha(job.get("messages")):
            raise ValueError("Frozen request/message hash mismatch")
        r = rx.get((query_id, condition), {"status": "missing_output", "parsed": None, "raw_text": None})
        if r["status"] != "missing_output" and r.get("input_sha256") != job["input_sha256"]:
            raise ValueError("Response belongs to a different frozen request")
        if r.get("raw_text") is not None:
            status, parsed = parse_response(r["raw_text"], job["evidence"])
            if r.get("generated_tokens", 0) >= 512:
                status = "output_length_limit"
            if status != r["status"] or (status != "output_length_limit" and parsed != r.get("parsed")):
                raise ValueError("Raw response does not reproduce retained parsing: " + query_id)
        elif r["status"] not in {"missing_output", "no_evidence", "input_over_budget", "inference_error", "generation_error"}:
            raise ValueError("Success/format status needs retained raw text")
        m = metrics(r, reference)
        used[query_id, condition] = {**r, "metrics": m}
        states.append({"query_id": query_id, "condition": condition, "question_id": reference["question_id"],
                       "issuer_cik": reference["issuer_cik"], "event_id": reference["event_id"],
                       "phase": reference["phase"], "status": r["status"],
                       "reference_changed": reference["answer_changed_between_versions"], **m})
    for qid in sorted({r["question_id"] for r in references}):
        for c in conditions:
            o, a = used[qid+"/original", c], used[qid+"/amendment", c]
            go, ga = refs[qid+"/original"], refs[qid+"/amendment"]
            om, am = o["metrics"], a["metrics"]
            po, pa = o.get("parsed") or {}, a.get("parsed") or {}
            both_valid = om["valid"] and am["valid"]
            changed = not same_number_unit(go, ga)
            if changed != go["answer_changed_between_versions"]:
                raise ValueError("Mechanical change flag disagrees with references")
            pair_rows.append({"question_id": qid, "condition": c, "issuer_cik": go["issuer_cik"],
                              "reference_changed": changed, "valid_both": both_valid,
                              "both_joint_correct": om["numeric_unit_accession_joint"] and am["numeric_unit_accession_joint"],
                              "original_only_joint": om["numeric_unit_accession_joint"] and not am["numeric_unit_accession_joint"],
                              "amendment_only_joint": am["numeric_unit_accession_joint"] and not om["numeric_unit_accession_joint"],
                              "false_number_or_unit_change": bool(not changed and both_valid and not same_number_unit(po, pa)),
                              "changed_reference_predicted_same": bool(changed and both_valid and same_number_unit(po, pa)),
                              "amendment_stale_original": bool(changed and am["valid"] and same_number_unit(pa, go) and not same_number_unit(pa, ga))})
    summary = {}
    for c in conditions:
        ss, pp = [r for r in states if r["condition"] == c], [r for r in pair_rows if r["condition"] == c]
        summary[c] = {"states": len(ss), "questions": len(pp), "status_counts": dict(Counter(r["status"] for r in ss)),
                      "state_metrics": {k: sum(r[k] for r in ss) for k in metrics({"status": "missing_output"}, references[0])},
                      "pair_metrics": {k: sum(bool(r[k]) for r in pp) for k in ["both_joint_correct", "original_only_joint", "amendment_only_joint", "valid_both", "false_number_or_unit_change", "changed_reference_predicted_same", "amendment_stale_original"]},
                      "joint_ci": cluster_interval(ss, "numeric_unit_accession_joint"),
                      "changed_joint_ci": cluster_interval([r for r in ss if r["reference_changed"]], "numeric_unit_accession_joint"),
                      "unchanged_joint_ci": cluster_interval([r for r in ss if not r["reference_changed"]], "numeric_unit_accession_joint")}
    return states, pair_rows, summary


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=Path(__file__).parent/"data")
    p.add_argument("--split", choices=["train", "dev", "test"], required=True)
    p.add_argument("--conditions", nargs="+", required=True)
    p.add_argument("--responses", type=Path, required=True)
    p.add_argument("--requests", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise FileExistsError("Scoring never overwrites prior results")
    resource = Resource(a.data)
    requests = read_rows(a.requests)
    provenance = verify_requests(resource, a.split, requests)
    ss, pp, result = score(resource.load_references(a.split), read_rows(a.responses), requests, a.conditions)
    a.output.mkdir(parents=True)
    for name, values in [("per_state.jsonl", ss), ("per_pair.jsonl", pp)]:
        (a.output/name).write_text("".join(json.dumps(v) + "\n" for v in values), encoding="utf-8")
    report = {"summary": result, "metric_policy": "Exact finite Decimal; predefined USD/shares aliases; exact accession; strict JSON and local citation IDs; all failures retained",
              "statistics": "10000 issuer bootstrap draws; Python Random seed20261027; descriptive intervals, not historical p-values or multiplicity-adjusted claims",
              "split": a.split, "resource_manifest_sha256": sha(a.data/"manifest.json"), "responses_sha256": sha(a.responses),
              "requests_sha256": sha(a.requests), "scorer_sha256": sha(__file__), "independent_gate_accessed": False}
    report["request_provenance_verification"] = provenance
    (a.output/"summary.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
