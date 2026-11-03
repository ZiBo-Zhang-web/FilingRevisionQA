"""Synthetic profile tests; no new scoring of real test predictions."""
import copy
import json
import unittest
import score as legacy
from score_profiles import (LEGACY_SHA, UnsupportedReferenceUnits, native_unit,
                            normalizer, profile_engine, reference_coverage, score_with_profile)


def fixture(unit="iso4217:CAD", answer="12", changed=False):
    references, requests, responses = [], [], []
    for phase in ("original", "amendment"):
        accession = "synthetic-" + phase
        value = str(int(answer) + 1) if changed and phase == "amendment" else answer
        reference = {"query_id": "synthetic/" + phase, "question_id": "synthetic", "phase": phase,
                     "issuer_cik": "synthetic", "event_id": "synthetic", "answer": value,
                     "unit": unit, "accession": accession, "answer_changed_between_versions": changed}
        evidence = [{"chunk_id": "E1", "accession": accession}]
        parsed = {"answer": value, "unit": unit, "accession": accession, "citations": ["E1"]}
        request = {"query_id": reference["query_id"], "condition": "synthetic", "evidence": evidence,
                   "messages": [], "input_sha256": legacy.message_sha([])}
        responses.append({"query_id": reference["query_id"], "condition": "synthetic", "input_sha256": request["input_sha256"],
                          "raw_text": json.dumps(parsed), "parsed": parsed, "status": legacy.VALID, "generated_tokens": 20})
        references.append(reference)
        requests.append(request)
    return references, responses, requests


class ProfileTests(unittest.TestCase):
    def test_legacy_bytes_and_semantics_stay_frozen(self):
        from pathlib import Path
        self.assertEqual(legacy.sha(Path(legacy.__file__)), LEGACY_SHA)
        self.assertIsNone(legacy.unit("iso4217:CAD"))
        self.assertIsNone(legacy.unit("xbrli:pure"))

    def test_explicit_native_units_have_exact_synthetic_credit(self):
        for unit in ("iso4217:USD", "xbrli:shares", "iso4217:CAD", "iso4217:USD per xbrli:shares", "xbrli:pure"):
            refs, responses, jobs = fixture(unit)
            states, pairs, summary, coverage = score_with_profile(refs, responses, jobs, ["synthetic"], "resource-native-v1")
            self.assertEqual(summary["synthetic"]["state_metrics"]["numeric_unit_accession_joint"], 2)
            self.assertTrue(pairs[0]["both_joint_correct"])
            self.assertEqual(coverage["unsupported_states"], 0)

    def test_default_legacy_refuses_unsupported_without_dropping_rows(self):
        refs, responses, jobs = fixture()
        with self.assertRaises(UnsupportedReferenceUnits) as cm:
            score_with_profile(refs, responses, jobs, ["synthetic"])
        self.assertEqual(cm.exception.coverage["states"], 2)
        self.assertEqual(cm.exception.coverage["unsupported_states"], 2)
        self.assertEqual(cm.exception.coverage["unchanged_question_pairs"], 1)

    def test_legacy_and_native_agree_on_supported_synthetic_unit(self):
        refs, responses, jobs = fixture("USD", changed=True)
        a = score_with_profile(refs, responses, jobs, ["synthetic"], "legacy")
        b = score_with_profile(refs, responses, jobs, ["synthetic"], "resource-native-v1")
        self.assertEqual(a[:3], b[:3])

    def test_profiles_do_not_mutate_each_others_globals(self):
        new = profile_engine("resource-native-v1")
        old = profile_engine("legacy")
        self.assertEqual(new.unit("CAD"), "CAD")
        self.assertIsNone(old.unit("CAD"))
        self.assertIsNone(legacy.unit("CAD"))

    def test_percent_ratio_not_pure_and_bare_dollar_not_cad(self):
        for unit in ("%", "percent", "percentage", "ratio", "basis points"):
            self.assertIsNone(native_unit(unit))
        self.assertNotEqual(native_unit("$"), native_unit("CAD"))
        self.assertEqual(native_unit("pure"), "pure")

    def test_no_scaling_or_inferred_unit_equivalence(self):
        engine = profile_engine("resource-native-v1")
        for wrong in ("CAD thousands", "CAD millions", "USD/1000 shares", "C$"):
            self.assertIsNone(native_unit(wrong))
        ref = {"answer": "1000", "unit": "CAD", "accession": "a"}
        pred = {"status": legacy.VALID, "parsed": {"answer": "1", "unit": "CAD", "accession": "a"}}
        self.assertFalse(engine.metrics(pred, ref)["numeric_unit_accession_joint"])

    def test_unknown_profile_and_unknown_reference_units_fail(self):
        with self.assertRaises(ValueError):
            normalizer("native-latest")
        refs, responses, jobs = fixture("unreviewed-unit")
        with self.assertRaises(UnsupportedReferenceUnits):
            score_with_profile(refs, responses, jobs, ["synthetic"], "resource-native-v1")

    def test_pair_change_uses_native_values_without_rewriting_labels(self):
        refs, _, _ = fixture("xbrli:pure", changed=True)
        saved = copy.deepcopy(refs)
        c = reference_coverage(refs, "legacy")
        self.assertEqual(c["changed_question_pairs"], 1)
        self.assertEqual(c["unsupported_changed_states"], 2)
        self.assertEqual(refs, saved)
        refs[0]["answer_changed_between_versions"] = False
        with self.assertRaisesRegex(ValueError, "flag mismatch"):
            reference_coverage(refs, "resource-native-v1")

    def test_invalid_pair_structure_is_rejected(self):
        refs, _, _ = fixture()
        for case in (refs + [refs[0]], refs[:1], [refs[0], {**refs[1], "unit": "USD"}]):
            with self.assertRaises(ValueError):
                reference_coverage(case, "resource-native-v1")

    def test_raw_parser_and_missing_output_denominator_remain_strict(self):
        refs, responses, jobs = fixture()
        responses[0]["raw_text"] = "```json\n" + responses[0]["raw_text"] + "\n```"
        responses[0]["status"], responses[0]["parsed"] = legacy.parse_response(responses[0]["raw_text"], jobs[0]["evidence"])
        states, pairs, summary, _ = score_with_profile(refs, responses[:1], jobs, ["synthetic"], "resource-native-v1")
        self.assertEqual(summary["synthetic"]["status_counts"], {"missing_output": 1, "invalid_json": 1})
        self.assertEqual(len(states), 2)
        self.assertFalse(pairs[0]["both_joint_correct"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
