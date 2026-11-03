"""Restore listed official SEC bytes with the bundled project-owned client.

Dry-run by default. No network or reference labels are accessed on import.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse
from frqa_resource import Resource
from frqa_sec_client import SecClient

def plan(data, wanted=()):
    resource=Resource(data)
    sources=resource._rows('sources.jsonl')
    for r in sources:
        url=urlparse(r['url'])
        if url.scheme!='https' or url.hostname not in {'www.sec.gov','data.sec.gov','xbrl.sec.gov'} or url.username or url.password:
            raise ValueError('Only official HTTPS URLs without credentials are allowed')
    if wanted:
        missing=set(wanted)-{r['sha256'] for r in sources}
        if missing:raise ValueError('Requested hash absent from the sealed manifest')
        sources=[r for r in sources if r['sha256'] in wanted]
    return sources

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',type=Path,default=Path(__file__).parent/'data')
    p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--source-sha256',action='append',default=[],help='Optional exact manifest hash; repeat to restore a subset')
    p.add_argument('--execute',action='store_true')
    a=p.parse_args()
    sources=plan(a.data,a.source_sha256)
    if not a.execute:
        print(json.dumps({'mode':'plan_only','files':len(sources),'rate_limit_per_second':2,
            'checkout_required':False,'network_requests':0,
            'contact':'SEC_USER_AGENT environment variable; never recorded'},indent=2));return
    target=a.cache/'download_receipt.json'
    if target.exists():raise FileExistsError('Use a new receipt destination; do not overwrite provenance')
    client=SecClient(user_agent=os.environ.get('SEC_USER_AGENT',''),cache_dir=a.cache,requests_per_second=2)
    receipts=[]
    for r in sources:
        body=client.fetch(r['url'],cache_key=r['sha256']+'.source')
        actual=hashlib.sha256(body).hexdigest()
        if actual!=r['sha256']:
            raise ValueError('Source hash mismatch; retain expected identity and investigate: '+r['url'])
        receipts.append({'url':r['url'],'sha256':actual,'bytes':len(body),
            'retrieval':client.last_fetch_metadata})
    a.cache.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps({'files':receipts,'mode':'verified_official_source_restore'},indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':main()
