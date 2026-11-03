"""Load both public states of one existing dev question, without any references."""
import argparse
import json
from pathlib import Path
from frqa_resource import Resource

p=argparse.ArgumentParser()
p.add_argument('--question-id')
a=p.parse_args()
r=Resource(Path(__file__).parent/'data')
rows=r.load_inputs('dev')
qid=a.question_id or rows[0]['query_id'].rsplit('/',1)[0]
pair=[x for x in rows if x['query_id'].rsplit('/',1)[0]==qid]
if len(pair)!=2:raise ValueError('Choose an existing dev question ID')
print(json.dumps({'purpose':'Public paired inputs; route query_id outside the model prompt',
    'split':'dev','records':pair,'offline_references_loaded':False},ensure_ascii=False,indent=2))
