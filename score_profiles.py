"""Versioned resource-scoring entrypoint; historical score.py stays byte-identical.

Native-unit support is a new evaluation profile, not a correction of old model
scores. Its validation uses synthetic predictions and reference structure only.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import importlib.util
import json
from pathlib import Path

from frqa_resource import Resource, read_rows, sha
import score as legacy

LEGACY_SHA = "df78df369f9b65669994d3432874344cc42a64fd47d58fbfa7be5451ebfc427a"
PROFILES = ("legacy", "resource-native-v1")
NATIVE_EXTRA_UNITS = {
    "cad": "CAD", "iso4217:cad": "CAD",
    "usd/share": "USD/share", "usd per share": "USD/share",
    "iso4217:usd per xbrli:shares": "USD/share",
    "pure": "pure", "xbrli:pure": "pure",
}


class UnsupportedReferenceUnits(ValueError):
    def __init__(self, coverage):
        self.coverage = coverage
        super().__init__("Unsupported reference units: " + json.dumps(coverage["unsupported_units"], sort_keys=True)
                         + "; no states are excluded and no scores are produced. Select an explicitly supported profile.")


def native_unit(value):
    """Closed lexical aliases only. Never scale numbers or infer a currency."""
    old = legacy.unit(value)
    return old if old is not None else NATIVE_EXTRA_UNITS.get(str(value).strip().lower())


def normalizer(profile):
    if profile not in PROFILES:
        raise ValueError("Unknown scoring profile: " + str(profile))
    return legacy.unit if profile == "legacy" else native_unit


def reference_coverage(references, profile):
    unit_fn = normalizer(profile)
    indexed, pairs = {}, defaultdict(dict)
    for row in references:
        key = row["query_id"]
        if key in indexed:
            raise ValueError("Duplicate reference query")
        indexed[key] = row
        if row["phase"] not in {"original", "amendment"} or key != row["question_id"] + "/" + row["phase"]:
            raise ValueError("Reference phase/query mismatch")
        if not legacy.numeric_equal(row["answer"], row["answer"]):
            raise ValueError("Non-finite or invalid reference number")
        if not isinstance(row["unit"], str) or not row["unit"]:
            raise ValueError("Invalid reference unit")
        if not isinstance(row["answer_changed_between_versions"], bool):
            raise ValueError("Reference change flag is not a boolean")
        pairs[row["question_id"]][row["phase"]] = row
    changed = 0
    for question, pair in pairs.items():
        if set(pair) != {"original", "amendment"}:
            raise ValueError("Reference pair is incomplete: " + question)
        original, amendment = pair["original"], pair["amendment"]
        for field in ("issuer_cik", "event_id"):
            if original[field] != amendment[field]:
                raise ValueError("Reference pair identity differs")
        # This resource has no unit-changing pairs. Reject rather than invent a
        # conversion rule if a future snapshot does. Original labels never change.
        if original["unit"] != amendment["unit"]:
            raise ValueError("Unit-changing reference pairs require a new protocol")
        value_changed = not legacy.numeric_equal(original["answer"], amendment["answer"])
        if any(row["answer_changed_between_versions"] != value_changed for row in pair.values()):
            raise ValueError("Native-unit/Decimal change flag mismatch")
        changed += value_changed
    unsupported = [r for r in references if unit_fn(r["unit"]) is None]
    return {
        "profile": profile, "states": len(references), "question_pairs": len(pairs),
        "supported_states": len(references) - len(unsupported),
        "unsupported_states": len(unsupported),
        "unsupported_question_pairs": len({r["question_id"] for r in unsupported}),
        "unit_counts": dict(sorted(Counter(r["unit"] for r in references).items())),
        "unsupported_units": dict(sorted(Counter(r["unit"] for r in unsupported).items())),
        "unsupported_changed_states": sum(r["answer_changed_between_versions"] for r in unsupported),
        "changed_question_pairs": changed, "unchanged_question_pairs": len(pairs) - changed,
        "pair_validation": "Exact original unit strings match across each pair; finite Decimal equality agrees with all retained change flags",
        "reference_labels_modified": False,
    }


def profile_engine(profile):
    """Isolated module globals prevent one profile changing another's unit map."""
    normalizer(profile)
    path = Path(__file__).with_name("score.py")
    if sha(path) != LEGACY_SHA:
        raise ValueError("Historical scorer bytes differ from the frozen version")
    spec = importlib.util.spec_from_file_location("_frqa_profile_" + profile.replace("-", "_"), path)
    engine = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(engine)
    if profile == "resource-native-v1":
        engine.unit = native_unit
    return engine


def score_with_profile(references, responses, requests, conditions, profile="legacy"):
    coverage = reference_coverage(references, profile)
    if coverage["unsupported_states"]:
        raise UnsupportedReferenceUnits(coverage)
    return (*profile_engine(profile).score(references, responses, requests, conditions), coverage)


def check_references(resource):
    result = {}
    for split in ("train", "dev", "test"):
        references = resource.load_references(split)
        result[split] = {p: reference_coverage(references, p) for p in PROFILES}
    return {"status": "passed", "scope": "Reference structure and unit coverage only; no predictions read or scored",
            "resource_manifest_sha256": sha(resource.root / "manifest.json"),
            "historical_scorer_sha256": sha(Path(__file__).with_name("score.py")),
            "profile_entrypoint_sha256": sha(__file__), "splits": result,
            "states_checked": sum(v["legacy"]["states"] for v in result.values()),
            "ordinary_test_predictions_scored": False, "model_calls": 0,
            "independent_gate_accessed": False, "labels_modified": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path(__file__).parent / "data")
    parser.add_argument("--check-references", action="store_true")
    parser.add_argument("--profile", choices=PROFILES, default="legacy")
    parser.add_argument("--split", choices=("train", "dev", "test"))
    parser.add_argument("--conditions", nargs="+")
    parser.add_argument("--requests", type=Path)
    parser.add_argument("--responses", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Use a new output path; prior results never overwritten")
    resource = Resource(args.data)
    if args.check_references:
        if any(x is not None for x in (args.split, args.conditions, args.requests, args.responses)):
            parser.error("Reference-only validation cannot accept model requests/responses")
        result = check_references(resource)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, indent=2))
        return
    if any(x is None for x in (args.split, args.conditions, args.requests, args.responses)):
        parser.error("Scoring requires --split, --conditions, --requests and --responses")
    references = resource.load_references(args.split)
    coverage = reference_coverage(references, args.profile)
    if coverage["unsupported_states"]:
        print(json.dumps({"status": "refused_unsupported_reference_units", "coverage": coverage,
                          "results_written": False}, indent=2))
        raise UnsupportedReferenceUnits(coverage)
    requests = read_rows(args.requests)
    provenance = legacy.verify_requests(resource, args.split, requests)
    states, pairs, summary, coverage = score_with_profile(references, read_rows(args.responses), requests,
                                                         args.conditions, args.profile)
    args.output.mkdir(parents=True)
    for name, rows in (("per_state.jsonl", states), ("per_pair.jsonl", pairs)):
        (args.output / name).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    result = {"profile": args.profile, "summary": summary, "reference_unit_coverage": coverage,
              "historical_scorer_sha256": LEGACY_SHA, "profile_entrypoint_sha256": sha(__file__),
              "resource_manifest_sha256": sha(args.data / "manifest.json"), "split": args.split,
              "requests_sha256": sha(args.requests), "responses_sha256": sha(args.responses),
              "request_provenance_verification": provenance,
              "metric_policy": "Exact finite Decimal; closed profile-specific lexical unit aliases; exact accession; unchanged strict parser and complete denominator; no conversion/rescaling",
              "statistics": "10000 issuer bootstrap draws; Python Random seed20261027; descriptive, not historical adjusted comparisons",
              "comparability": "Different profiles must not be mixed or silently substituted for published legacy scores",
              "independent_gate_accessed": False}
    (args.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
