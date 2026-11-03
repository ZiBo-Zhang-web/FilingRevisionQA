"""Synthetic safety/metric cases only; no human labels or benchmark edits."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from frqa_resource import Resource, safe_path
from score import VALID, message_sha, metrics, numeric_equal, parse_response, score, unit, unique_index, verify_requests


class ResourceTests(unittest.TestCase):
    def setUp(self):
        self.evidence = [{"chunk_id": "E1", "accession": "0000000001-26-000001"}]
        self.value = {"answer": "12", "unit": "USD", "accession": self.evidence[0]["accession"], "citations": ["E1"]}

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            for name in ["../secrets", "C:/secret", "/tmp/secret", "a\\..\\secret"]:
                with self.assertRaises(ValueError):
                    safe_path(d, name)

    def test_gate_not_a_split(self):
        for split in ["gate", "independent_gate", "../test", "all"]:
            with self.assertRaises(ValueError):
                Resource._check_split(split)

    def test_strict_json_no_markdown_repair(self):
        self.assertEqual(parse_response("```json\n" + json.dumps(self.value) + "\n```", self.evidence)[0], "invalid_json")

    def test_nonfinite_number_fails(self):
        for v in ["NaN", "Infinity", "-Infinity"]:
            self.assertFalse(numeric_equal(v, v))
            self.assertEqual(parse_response(json.dumps({**self.value, "answer": v}), self.evidence)[0], "invalid_numeric")

    def test_numeric_exact_not_tolerance(self):
        self.assertTrue(numeric_equal("12.00", "12"))
        self.assertFalse(numeric_equal("12.00001", "12"))
        self.assertFalse(numeric_equal("1,200", "1200"))

    def test_invalid_accession_type_totalized(self):
        for value in [[], {}]:
            self.assertEqual(parse_response(json.dumps({**self.value, "accession": value}), self.evidence)[0], "invalid_schema")

    def test_unknown_citation_rejected(self):
        self.assertEqual(parse_response(json.dumps({**self.value, "citations": ["E2"]}), self.evidence)[0], "unknown_citation")

    def test_quoted_foreign_accession_rejected(self):
        self.assertEqual(parse_response(json.dumps({**self.value, "accession": "0000000001-26-000002"}), self.evidence)[0], "citation_accession_mismatch")

    def test_unit_aliases_not_arbitrary_equivalence(self):
        self.assertEqual(unit("iso4217:USD"), "USD")
        self.assertIsNone(unit("USD thousands"))
        m = metrics({"status": VALID, "parsed": self.value}, {**self.value, "unit": "shares"})
        self.assertTrue(m["numeric_exact"])
        self.assertFalse(m["numeric_unit_accession_joint"])

    def test_number_correct_wrong_version(self):
        m = metrics({"status": VALID, "parsed": self.value}, {**self.value, "accession": "other"})
        self.assertTrue(m["numeric_correct_wrong_accession"])
        self.assertFalse(m["numeric_unit_accession_joint"])

    def test_duplicate_records_fail(self):
        with self.assertRaises(ValueError):
            unique_index([{"query_id": "q/original", "condition": "x"}]*2)

    def test_duplicate_or_empty_conditions_rejected(self):
        for conditions in [["x", "x"], []]:
            with self.assertRaisesRegex(ValueError, "nonempty and unique"):
                score([], [], [], conditions)

    def test_missing_outputs_keep_denominator_and_no_false_change(self):
        refs, req = [], []
        for phase in ["original", "amendment"]:
            refs.append({"query_id": "q/"+phase, "question_id": "q", "phase": phase, "event_id": "e", "issuer_cik": "1",
                         "answer": "12", "unit": "USD", "accession": self.value["accession"], "answer_changed_between_versions": False})
            req.append({"query_id": "q/"+phase, "condition": "x", "evidence": self.evidence,
                        "messages": [], "input_sha256": message_sha([])})
        ss, pp, summary = score(refs, [], req, ["x"])
        self.assertEqual(summary["x"]["states"], 2)
        self.assertEqual(summary["x"]["status_counts"], {"missing_output": 2})
        self.assertFalse(pp[0]["false_number_or_unit_change"])
        self.assertFalse(pp[0]["both_joint_correct"])

    def test_missing_requests_not_imputed(self):
        ref = {"query_id": "q/original", "question_id": "q"}
        with self.assertRaises(ValueError):
            score([ref], [], [], ["x"])

    def test_tamper_rejected_before_loading(self):
        from frqa_resource import sha
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            f = root/"split_membership.jsonl"
            f.write_text("", encoding="utf-8")
            manifest = {"schema_version": "1.0", "independent_gate_included": False,
                        "files": [{"path": f.name, "bytes": 0, "sha256": sha(f)}]}
            (root/"manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            f.write_text("tampered", encoding="utf-8")
            with self.assertRaises(ValueError):
                Resource(root)

    def test_tampered_message_hash_rejected(self):
        refs = [{"query_id": "q/original"}]
        requests = [{"query_id": "q/original", "condition": "x", "messages": [], "input_sha256": "0"*64}]
        with self.assertRaises(ValueError):
            score(refs, [], requests, ["x"])

    def test_response_request_hash_must_match(self):
        refs = [{"query_id": "q/original"}]
        requests = [{"query_id": "q/original", "condition": "x", "messages": [], "input_sha256": message_sha([])}]
        response = [{"query_id": "q/original", "condition": "x", "status": "no_evidence", "input_sha256": "0"*64}]
        with self.assertRaises(ValueError):
            score(refs, response, requests, ["x"])

    def test_cutoff_and_source_metadata_tamper(self):
        query = {"question": "synthetic", "cutoff": "2026-01-01T00:00:00Z", "clock_protocol": "synthetic", "instruction": "synthetic"}
        evidence = [{"chunk_id": "E1", "accession": "a", "source_url": "https://www.sec.gov/synthetic", "source_sha256": "a"*64,
                     "accepted_at_utc": "2025-12-31T00:00:00Z"}]
        class MockResource:
            membership = {"q": {"issuer_cik": "1"}}
            def load_inputs(self, split): return [{"query_id": "q/original", "model_input": query}]
            def _rows(self, name):
                if name == "public/filings.jsonl":
                    return [{"accession": "a", "issuer_cik": "1", "accepted_at_utc": "2025-12-31T00:00:00Z"}]
                return [{"url": "https://www.sec.gov/synthetic", "sha256": "a"*64, "accession": "a"}]
        def job(ev, q):
            messages = [{"role": "system", "content": "synthetic"}, {"role": "user", "content": json.dumps({"request": q, "evidence": ev})}]
            return [{"query_id": "q/original", "evidence": ev, "messages": messages, "input_sha256": message_sha(messages)}]
        self.assertEqual(verify_requests(MockResource(), "dev", job(evidence, query))["future_sources"], 0)
        with self.assertRaises(ValueError):
            verify_requests(MockResource(), "dev", job(evidence, {**query, "cutoff": "2099-01-01T00:00:00Z"}))
        with self.assertRaises(ValueError):
            verify_requests(MockResource(), "dev", job([{**evidence[0], "accepted_at_utc": "2026-01-02T00:00:00Z"}], query))
        query["cutoff"] = "2025-12-30T00:00:00Z"
        with self.assertRaises(ValueError):
            verify_requests(MockResource(), "dev", job(evidence, query))

    def test_duplicate_membership_rejected(self):
        from frqa_resource import sha
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            f = root/"split_membership.jsonl"
            value = {"question_id": "q", "event_id": "e", "issuer_cik": "1", "split": "dev"}
            f.write_text((json.dumps(value)+"\n")*2, encoding="utf-8")
            manifest = {"schema_version": "1.0", "independent_gate_included": False, "question_pairs": 2, "events": 1, "issuers": 1,
                        "files": [{"path": f.name, "bytes": f.stat().st_size, "sha256": sha(f)}]}
            (root/"manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate question"):
                Resource(root)

    def test_manifest_count_mismatch_rejected(self):
        from frqa_resource import sha
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            f = root/"split_membership.jsonl"
            value = {"question_id": "q", "event_id": "e", "issuer_cik": "1", "split": "dev"}
            f.write_text(json.dumps(value)+"\n", encoding="utf-8")
            manifest = {"schema_version": "1.0", "independent_gate_included": False, "question_pairs": 2, "events": 1, "issuers": 1,
                        "files": [{"path": f.name, "bytes": f.stat().st_size, "sha256": sha(f)}]}
            (root/"manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "counts disagree"):
                Resource(root)

    def test_inputs_alone_require_both_phases(self):
        resource = object.__new__(Resource)
        resource.membership = {"q": {"split": "dev"}, "other": {"split": "dev"}}
        resource.manifest = {"counts": {"dev": {"states": 2, "question_pairs": 2}}}
        query = {"question": "synthetic", "cutoff": "2026-01-01T00:00:00Z", "clock_protocol": "synthetic", "instruction": "synthetic"}
        resource._rows = lambda name: [{"query_id": "q/original", "model_input": query}, {"query_id": "other/original", "model_input": query}]
        with self.assertRaisesRegex(ValueError, "both phases"):
            resource.load_inputs("dev")


if __name__ == "__main__":
    unittest.main(verbosity=2)
