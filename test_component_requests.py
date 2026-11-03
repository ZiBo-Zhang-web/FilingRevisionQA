import json,unittest
from build_component_requests import build

class PublicOnlyResource:
    membership={'q':{'issuer_cik':'1'}}
    def __init__(self):self.reads=[]
    def load_inputs(self,split):
        return [{'query_id':'q/'+phase,'model_input':{'question':'Synthetic public question','cutoff':'2026-01-01T00:00:00Z','clock_protocol':'synthetic','instruction':'Select eligible evidence'}} for phase in ('original','amendment')]
    def load_references(self,*a):raise AssertionError('Reference access is forbidden')
    def _rows(self,name):
        self.reads.append(name)
        if name=='public/filings.jsonl':return [{'accession':'a','issuer_cik':'1','accepted_at_utc':'2025-12-31T00:00:00Z'}]
        if name=='sources.jsonl':return [{'url':'https://www.sec.gov/synthetic','sha256':'a'*64,'accession':'a'}]
        raise AssertionError('Nonpublic read: '+name)

class ComponentTests(unittest.TestCase):
    def setUp(self):
        self.r=PublicOnlyResource()
        self.e=[{'chunk_id':'E1','accession':'a','source_url':'https://www.sec.gov/synthetic','source_sha256':'a'*64,'accepted_at_utc':'2025-12-31T00:00:00Z','text':'Synthetic evidence'}]
        self.rows=[{'query_id':'q/'+p,'evidence':self.e} for p in ('original','amendment')]
    def test_public_only_complete_messages(self):
        jobs=build(self.r,'dev','new',self.rows)
        self.assertEqual(len(jobs),2)
        content=json.loads(jobs[0]['messages'][1]['content'])
        self.assertEqual(set(content),{'request','evidence'})
        self.assertNotIn('answer',content['request'])
        self.assertEqual(set(self.r.reads),{'public/filings.jsonl','sources.jsonl'})
    def test_empty_evidence_preserves_all_queries(self):
        jobs=build(self.r,'dev','empty',[{**r,'evidence':[]} for r in self.rows])
        self.assertEqual(len(jobs),2)
    def test_missing_query_rejected(self):
        with self.assertRaises(ValueError):build(self.r,'dev','x',self.rows[:1])
    def test_duplicate_query_rejected(self):
        with self.assertRaises(ValueError):build(self.r,'dev','x',self.rows+[self.rows[0]])
    def test_future_timestamp_rejected(self):
        for r in self.rows:r['evidence']=[{**e,'accepted_at_utc':'2026-01-02T00:00:00Z'} for e in self.e]
        with self.assertRaises(ValueError):build(self.r,'dev','x',self.rows)
    def test_wrong_source_hash_rejected(self):
        for r in self.rows:r['evidence']=[{**e,'source_sha256':'b'*64} for e in self.e]
        with self.assertRaises(ValueError):build(self.r,'dev','x',self.rows)
    def test_evidence_object_rejected(self):
        with self.assertRaises(ValueError):build(self.r,'dev','x',[{**r,'evidence':{}} for r in self.rows])

if __name__=='__main__':unittest.main()
