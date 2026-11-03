import json,unittest
import paired_diagnostics_v2 as d
class PairedDiagnosticsTests(unittest.TestCase):
    def refs(self,changed=False):
        return [dict(query_id="Q/"+p,question_id="Q",issuer_cik="I",event_id="E",phase=p,
                     answer="8" if changed and p=="amendment" else "7",unit="USD",
                     accession=p,answer_changed_between_versions=changed) for p in ("original","amendment")]
    def out(self,n="7",u="USD",status=None,acc="original"):
        return {"status":status or d.ENGINE.VALID,"parsed":dict(answer=n,unit=u,accession=acc,citations=["E1"])}
    def pair(self,a,b,changed=False):return d.diagnose_pair(a,b,*self.refs(changed))
    def test_identical_unknown_units_unassessable(self):
        p=self.pair(self.out(u="widgets"),self.out(u="widgets"));self.assertFalse(p["comparison_assessable"]);self.assertFalse(p["false_number_or_unit_change"])
    def test_one_unknown_unit(self):
        p=self.pair(self.out(),self.out(u="widgets"));self.assertFalse(p["comparison_assessable"]);self.assertTrue(p["unknown_unit_amendment"])
    def test_different_unknown_values_not_change_evidence(self):
        self.assertFalse(self.pair(self.out(u="widgets"),self.out("8",u="widgets"))["false_number_or_unit_change"])
    def test_same_known(self):self.assertFalse(self.pair(self.out(),self.out())["false_number_or_unit_change"])
    def test_changed_known(self):self.assertTrue(self.pair(self.out(),self.out("8"))["false_number_or_unit_change"])
    def test_alias_equivalence(self):self.assertFalse(self.pair(self.out(u="$"),self.out(u="iso4217:USD"))["false_number_or_unit_change"])
    def test_known_different_units(self):self.assertTrue(self.pair(self.out(),self.out(u="shares"))["false_number_or_unit_change"])
    def test_invalid_keeps_reason(self):
        p=self.pair(self.out(status="invalid_json"),self.out());self.assertFalse(p["comparison_assessable"]);self.assertIn("original:invalid_json",p["unassessable_reasons"])
    def test_abstention(self):self.assertFalse(self.pair(self.out(status="abstained"),self.out())["comparison_assessable"])
    def test_missing(self):self.assertFalse(self.pair({"status":"missing_output","parsed":None},self.out())["comparison_assessable"])
    def test_stale_known(self):self.assertTrue(self.pair(self.out(),self.out(acc="amendment"),True)["amendment_stale_original"])
    def test_unknown_not_stale(self):self.assertFalse(self.pair(self.out(),self.out(u="widgets"),True)["amendment_stale_original"])
    def test_primary_both(self):self.assertTrue(self.pair(self.out(),self.out(acc="amendment"))["both_joint_correct"])
    def test_denominators(self):
        pp=[self.pair(self.out(),self.out("8")),self.pair(self.out(u="widgets"),self.out(u="widgets")),self.pair(self.out(),self.out(status="abstained"))]
        s=d.summarize_pairs(pp);self.assertEqual(s["false_change_all_unchanged"]["denominator"],3);self.assertEqual(s["false_change_assessable_unchanged"]["denominator"],1)
    def test_zero_assessable_rate_none(self):self.assertIsNone(d.summarize_pairs([self.pair(self.out(u="x"),self.out(u="x"))])["false_change_assessable_unchanged"]["rate"])
    def test_reference_mismatch_rejected(self):
        g=self.refs();g[1]["answer_changed_between_versions"]=True
        with self.assertRaises(ValueError):d.diagnose_pair(self.out(),self.out(),*g)
    def test_unsupported_reference_rejected(self):
        g=self.refs();g[0]["unit"]="unknown"
        with self.assertRaises(ValueError):d.diagnose_pair(self.out(),self.out(),*g)
    def test_frozen_historical_scorer(self):self.assertEqual(d.sha(d.Path(d.__file__).with_name("score.py")),d.score_profiles.LEGACY_SHA)
if __name__=="__main__":unittest.main()

