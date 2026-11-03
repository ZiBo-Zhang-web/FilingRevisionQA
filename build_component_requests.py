"""Build sealed public requests for a user-supplied retrieval component.

This utility loads no offline references or wording-review mappings.
Evidence is supplied by the user's retriever, never by this utility's labels.
"""
import argparse,json
from pathlib import Path
from frqa_resource import Resource,read_rows
from score import message_sha,verify_requests
SYSTEM = ('Return exactly one JSON object with keys answer, unit, accession, citations. '
          'answer is a finite decimal string, or null to abstain. unit is a string. '
          'accession identifies a provided filing. citations is a list of provided chunk IDs. '
          'Use only the evidence and request. Do not include Markdown.')
def build(resource,split,condition,evidence_rows):
    indexed={}
    for row in evidence_rows:
        q=row["query_id"]
        if q in indexed:raise ValueError("Duplicate evidence query")
        indexed[q]=row["evidence"]
    public=list(resource.load_inputs(split));expected={r["query_id"] for r in public}
    if set(indexed)!=expected:raise ValueError("Provide evidence arrays, possibly empty, for every split query")
    jobs=[]
    for row in public:
        evidence=indexed[row["query_id"]]
        if not isinstance(evidence,list):raise ValueError("Evidence must be an array")
        messages=[{"role":"system","content":SYSTEM},{"role":"user","content":json.dumps({"request":row["model_input"],"evidence":evidence},ensure_ascii=False)}]
        jobs.append({"query_id":row["query_id"],"condition":condition,"evidence":evidence,"messages":messages,"input_sha256":message_sha(messages)})
    verify_requests(resource,split,jobs)
    return jobs
def main():
    p=argparse.ArgumentParser();p.add_argument("--data",type=Path,default=Path(__file__).parent/"data")
    p.add_argument("--split",choices=("train","dev","test"),required=True);p.add_argument("--condition",required=True)
    p.add_argument("--evidence",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    if a.output.exists():raise FileExistsError("Preserve prior sealed requests")
    jobs=build(Resource(a.data),a.split,a.condition,read_rows(a.evidence))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text("".join(json.dumps(j,ensure_ascii=False)+"\n" for j in jobs),encoding="utf-8")
    print(json.dumps({"requests":len(jobs),"reference_rows_read":0,"model_calls":0,"note":"New component interface; not a reconstruction of historical experimental prompts."}))
if __name__=="__main__":main()

