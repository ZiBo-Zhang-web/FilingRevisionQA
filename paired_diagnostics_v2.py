"""paired-diagnostics-v2: assessability-aware overlay, unchanged native J/P.

Historical score.py and score_profiles.py are retained byte for byte.
Unknown units never become evidence of either change or stability.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import score_profiles
from frqa_resource import Resource, read_rows, sha

VERSION = "paired-diagnostics-v2"
UNIT_PROFILE = "resource-native-v1"
ENGINE = score_profiles.profile_engine(UNIT_PROFILE)

def diagnose_pair(original, amendment, ref_original, ref_amendment):
    """Apply frozen paired rules to retained parsed statuses; no schema repair."""
    go, ga = ref_original, ref_amendment
    if go["question_id"] != ga["question_id"] or go["issuer_cik"] != ga["issuer_cik"]:
        raise ValueError("Pair identity mismatch")
    for g in (go, ga):
        if ENGINE.unit(g["unit"]) is None:
            raise ValueError("Unsupported reference unit")
    changed = not ENGINE.same_number_unit(go, ga)
    if any(g["answer_changed_between_versions"] != changed for g in (go,ga)):
        raise ValueError("Mechanical reference flag mismatch")
    po = original.get("parsed") if isinstance(original.get("parsed"),dict) else {}
    pa = amendment.get("parsed") if isinstance(amendment.get("parsed"),dict) else {}
    vo, va = original["status"] == ENGINE.VALID, amendment["status"] == ENGINE.VALID
    if (vo and not po) or (va and not pa):
        raise ValueError("Valid status needs parsed object")
    known_o, known_a = ENGINE.unit(po.get("unit")) is not None, ENGINE.unit(pa.get("unit")) is not None
    assess = bool(vo and va and known_o and known_a)
    reasons=[]
    for label, row, valid, known in (("original",original,vo,known_o),("amendment",amendment,va,known_a)):
        if not valid: reasons.append(label+":"+row["status"])
        elif not known: reasons.append(label+":unknown_unit")
    om, am = ENGINE.metrics(original,go), ENGINE.metrics(amendment,ga)
    oj, aj = om["numeric_unit_accession_joint"], am["numeric_unit_accession_joint"]
    return {
        "question_id":go["question_id"],"issuer_cik":go["issuer_cik"],
        "reference_changed":changed,"valid_both":vo and va,
        "comparison_assessable":assess,"comparison_status":"assessable" if assess else "unassessable",
        "unassessable_reasons":reasons,
        "unknown_unit_original":bool(vo and not known_o),"unknown_unit_amendment":bool(va and not known_a),
        "both_joint_correct":oj and aj,"original_only_joint":oj and not aj,
        "amendment_only_joint":aj and not oj,"neither_joint_correct":not oj and not aj,
        "false_number_or_unit_change":bool(not changed and assess and not ENGINE.same_number_unit(po,pa)),
        "changed_reference_predicted_same":bool(changed and assess and ENGINE.same_number_unit(po,pa)),
        "amendment_stale_original":bool(changed and va and known_a and ENGINE.same_number_unit(pa,go) and not ENGINE.same_number_unit(pa,ga)),
    }

def summarize_pairs(pairs):
    def rate(n,d):return {"numerator":n,"denominator":d,"rate":n/d if d else None}
    unchanged=[p for p in pairs if not p["reference_changed"]]
    assessed=[p for p in unchanged if p["comparison_assessable"]]
    changed=[p for p in pairs if p["reference_changed"]]
    fc=sum(p["false_number_or_unit_change"] for p in unchanged)
    return {
        "diagnostic_version":VERSION,"unit_profile":UNIT_PROFILE,"pairs":len(pairs),
        "comparison_assessable":sum(p["comparison_assessable"] for p in pairs),
        "unknown_unit_pairs":sum(p["unknown_unit_original"] or p["unknown_unit_amendment"] for p in pairs),
        "unassessable_reasons":dict(sorted(Counter(x for p in pairs for x in p["unassessable_reasons"]).items())),
        "false_change_all_unchanged":rate(fc,len(unchanged)),
        "false_change_assessable_unchanged":rate(fc,len(assessed)),
        "stale_all_changed":rate(sum(p["amendment_stale_original"] for p in changed),len(changed)),
    }

def score(references,responses,requests,conditions):
    # Original full request, retained parser, denominator and numeric checks run first.
    ss,old_pairs,summary,coverage=score_profiles.score_with_profile(references,responses,requests,conditions,UNIT_PROFILE)
    refs={g["query_id"]:g for g in references};rx=ENGINE.unique_index(responses);pp=[]
    missing={"status":"missing_output","parsed":None}
    for old in old_pairs:
        q,c=old["question_id"],old["condition"]
        p=diagnose_pair(rx.get((q+"/original",c),missing),rx.get((q+"/amendment",c),missing),
                        refs[q+"/original"],refs[q+"/amendment"])
        # J/P and all assessable pair outcomes must agree with original implementation.
        for k in ("both_joint_correct","original_only_joint","amendment_only_joint"):
            if p[k]!=old[k]: raise AssertionError("Primary paired metric drift: "+k)
        pp.append({**p,"condition":c})
    for c in conditions:
        rows=[p for p in pp if p["condition"]==c]
        for k in list(summary[c]["pair_metrics"]):
            summary[c]["pair_metrics"][k]=sum(bool(p[k]) for p in rows)
        summary[c]["paired_diagnostics"]=summarize_pairs(rows)
    return ss,pp,summary,coverage

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data",type=Path,default=Path(__file__).parent/"data")
    p.add_argument("--split",choices=("train","dev","test"),required=True)
    p.add_argument("--conditions",nargs="+",required=True)
    p.add_argument("--responses",type=Path,required=True)
    p.add_argument("--requests",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError("Choose a new output; no overwriting")
    resource=Resource(a.data);jobs=read_rows(a.requests)
    provenance=ENGINE.verify_requests(resource,a.split,jobs)
    states,pairs,summary,coverage=score(resource.load_references(a.split),read_rows(a.responses),jobs,a.conditions)
    a.output.mkdir(parents=True)
    for name,rows in (("per_state.jsonl",states),("per_pair.jsonl",pairs)):
        (a.output/name).write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in rows),encoding="utf-8")
    result={"diagnostic_version":VERSION,"unit_profile":UNIT_PROFILE,"summary":summary,
            "reference_coverage":coverage,"request_provenance":provenance,
            "scorer_sha256":sha(__file__),"historical_scorer_sha256":score_profiles.LEGACY_SHA,
            "requests_sha256":sha(a.requests),"responses_sha256":sha(a.responses),
            "resource_manifest_sha256":sha(a.data/"manifest.json"),
            "independent_gate_accessed":False,"model_calls":0}
    (a.output/"summary.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"passed","states":len(states),"pairs":len(pairs),"diagnostic_version":VERSION}))
if __name__=="__main__":main()

