"""Offline standard-library reader for the sanitized FilingRevisionQA preview.

Default access returns only four public input fields. References require the
explicit load_references call; no API permits an independent gate split.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path, PurePosixPath

INPUT_KEYS = {"question", "cutoff", "clock_protocol", "instruction"}
SPLITS = {"train", "dev", "test"}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_rows(path):
    return [json.loads(x) for x in Path(path).read_text(encoding="utf-8").splitlines() if x.strip()]


def safe_path(root, relative):
    if not isinstance(relative, str) or "\\" in relative or ":" in relative:
        raise ValueError("Non-portable resource path")
    posix = PurePosixPath(relative)
    if posix.is_absolute() or ".." in posix.parts or not posix.parts:
        raise ValueError("Resource path escapes its package")
    result = (Path(root)/relative).resolve()
    result.relative_to(Path(root).resolve())
    return result


class Resource:
    def __init__(self, root, expected_manifest_sha256=None):
        self.root = Path(root).resolve()
        manifest_path = self.root/"manifest.json"
        if expected_manifest_sha256 and sha(manifest_path) != expected_manifest_sha256:
            raise ValueError("Manifest fingerprint mismatch")
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if self.manifest.get("independent_gate_included") is not False:
            raise ValueError("Only the explicitly non-gate benchmark preview is supported")
        if self.manifest.get("schema_version") != "1.0":
            raise ValueError("Unsupported schema version")
        self.files = {}
        for record in self.manifest["files"]:
            name = record["path"]
            if name in self.files:
                raise ValueError("Duplicate manifest path")
            path = safe_path(self.root, name)
            if path.stat().st_size != record["bytes"] or sha(path) != record["sha256"]:
                raise ValueError("Resource file fingerprint mismatch: " + name)
            self.files[name] = path
        membership_rows = self._rows("split_membership.jsonl")
        self.membership = {r["question_id"]: r for r in membership_rows}
        if len(self.membership) != len(membership_rows):
            raise ValueError("Duplicate question membership")
        counts = (len(membership_rows), len({r["event_id"] for r in membership_rows}),
                  len({r["issuer_cik"] for r in membership_rows}))
        expected = (self.manifest["question_pairs"], self.manifest["events"], self.manifest["issuers"])
        if counts != expected:
            raise ValueError("Manifest question/event/issuer counts disagree")
        by_issuer = defaultdict(set)
        for record in self.membership.values():
            self._check_split(record["split"])
            by_issuer[record["issuer_cik"]].add(record["split"])
        if any(len(v) != 1 for v in by_issuer.values()):
            raise ValueError("Issuer crosses splits")

    @staticmethod
    def _check_split(split):
        if split not in SPLITS:
            raise ValueError("Only train/dev/test are supported; protected gate is never loaded")

    def _rows(self, name):
        if name not in self.files:
            raise ValueError("File absent from the sealed manifest: " + name)
        return read_rows(self.files[name])

    def load_inputs(self, split="dev"):
        self._check_split(split)
        result = self._rows(f"public/{split}.jsonl")
        seen = set()
        phases = defaultdict(set)
        for r in result:
            if set(r) != {"query_id", "model_input"} or set(r["model_input"]) != INPUT_KEYS:
                raise ValueError("Public input whitelist violated")
            if r["query_id"] in seen:
                raise ValueError("Duplicate query")
            seen.add(r["query_id"])
            qid, phase = r["query_id"].rsplit("/", 1)
            if phase not in {"original", "amendment"} or self.membership[qid]["split"] != split:
                raise ValueError("Query membership mismatch")
            phases[qid].add(phase)
        if len(seen) != self.manifest["counts"][split]["states"]:
            raise ValueError("Unexpected state denominator")
        expected_ids = {qid for qid, r in self.membership.items() if r["split"] == split}
        if set(phases) != expected_ids or any(v != {"original", "amendment"} for v in phases.values()):
            raise ValueError("Each split question requires both phases")
        if len(phases) != self.manifest["counts"][split]["question_pairs"]:
            raise ValueError("Split pair count disagrees with manifest")
        return result

    def load_references(self, split):
        """Explicit offline scoring API; never pass its result to an autonomous model."""
        self._check_split(split)
        result = self._rows(f"offline_references/{split}.jsonl")
        keys = [r["query_id"] for r in result]
        if len(keys) != len(set(keys)) or set(keys) != {r["query_id"] for r in self.load_inputs(split)}:
            raise ValueError("Reference coverage mismatch")
        if any(r.get("reference_only") is not True for r in result):
            raise ValueError("Reference isolation marker missing")
        return result

    def validate(self):
        for split in sorted(SPLITS):
            inputs, refs = self.load_inputs(split), self.load_references(split)
            pairs = defaultdict(set)
            for r in refs:
                pairs[r["question_id"]].add(r["phase"])
                for locator in r["evidence_locators"]:
                    if len(locator["sha256"]) != 64 or not locator["xpath"]:
                        raise ValueError("Missing source identity or locator")
            if any(p != {"original", "amendment"} for p in pairs.values()):
                raise ValueError("Incomplete paired states")
        return {"status": "passed", "version": self.manifest["version"],
                "manifest_sha256": sha(self.root/"manifest.json"), "files_verified": len(self.files),
                "counts": self.manifest["counts"], "gate_loaded": False}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path(__file__).parent/"data")
    parser.add_argument("--expected-manifest-sha256")
    a = parser.parse_args()
    print(json.dumps(Resource(a.data, a.expected_manifest_sha256).validate(), indent=2))
