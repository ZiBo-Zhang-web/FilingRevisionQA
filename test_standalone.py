"""Portable-boundary tests, not new semantic labels or benchmark generation."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from frqa_resource import Resource, INPUT_KEYS
from download_sources import plan
from score_profiles import check_references
from verify_package import verify
from frqa_sec_client import SecClient

ROOT=Path(__file__).parent

class StandaloneTests(unittest.TestCase):
    def test_manifest_complete(self):
        self.assertEqual(verify(ROOT)['status'],'passed')

    def test_exact_copied_dependencies(self):
        p=json.loads((ROOT/'DEPENDENCY_PROVENANCE.json').read_text(encoding='utf-8'))
        for r in p['copies']:
            self.assertEqual(hashlib.sha256((ROOT/r['target']).read_bytes()).hexdigest(),r['sha256'])

    def test_all_reference_units_keep_denominators(self):
        r=check_references(Resource(ROOT/'data'))
        self.assertEqual(r['states_checked'],936)
        self.assertEqual([r['splits'][s]['resource-native-v1']['unsupported_states'] for s in ['train','dev','test']],[0,0,0])
        self.assertEqual([r['splits'][s]['legacy']['unsupported_states'] for s in ['train','dev','test']],[18,0,4])

    def test_wording_lineage_and_pending_not_labels(self):
        rows=[json.loads(x) for x in (ROOT/'audit/wording_lineage.jsonl').read_text(encoding='utf-8').splitlines()]
        self.assertEqual(len(rows),468)
        self.assertEqual(Counter(r['transformation'] for r in rows),{'verbatim':240,'prefix_replacement':167,'cutoff_applicability':61})
        resource=Resource(ROOT/'data')
        q={r['query_id'].rsplit('/',1)[0]:r['model_input']['question'] for s in ['train','dev','test'] for r in resource.load_inputs(s)}
        for r in rows:
            self.assertEqual(r['public_question'],q[r['question_id']])
            self.assertIsNone(r['human_semantic_equivalence'])
            self.assertIsNone(r['human_date'])
            self.assertTrue(r['audit_only'])
            self.assertFalse(r['replaces_historical_model_input'])
            self.assertEqual(hashlib.sha256(r['reviewed_question'].encode()).hexdigest(),r['reviewed_question_sha256'])

    def test_public_model_input_whitelist(self):
        for r in Resource(ROOT/'data').load_inputs('dev'):
            self.assertEqual(set(r['model_input']),INPUT_KEYS)

    def test_offline_download_plan_with_network_forbidden(self):
        with patch('urllib.request.urlopen',side_effect=AssertionError('Network forbidden')):
            rows=plan(ROOT/'data')
        self.assertEqual(len(rows),938)
        subset=plan(ROOT/'data',[rows[0]['sha256']])
        self.assertTrue(subset)
        self.assertTrue(all(r['sha256']==rows[0]['sha256'] for r in subset))

    def test_unknown_source_hash_rejected(self):
        with self.assertRaises(ValueError):plan(ROOT/'data',['0'*64])

    def test_bundled_client_cache_without_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache=Path(tmp)
            (cache/'fixture.source').write_bytes(b'synthetic-cache-fixture')
            client=SecClient(user_agent='Synthetic test contact@synthetic.invalid',cache_dir=cache,requests_per_second=2)
            with patch('frqa_sec_client.urlopen',side_effect=AssertionError('Network forbidden')):
                self.assertEqual(client.fetch('https://www.sec.gov/synthetic',cache_key='fixture.source'),b'synthetic-cache-fixture')
            self.assertEqual(client.last_fetch_metadata['cache_status'],'cache_hit')
            with self.assertRaises(ValueError):client._cache_target('../outside')

    def test_archive_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'package'
            shutil.copytree(ROOT,dest,ignore=shutil.ignore_patterns('__pycache__'))
            (dest/'example_pair.py').write_text('tampered',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Hash mismatch'):verify(dest)

    def test_unlisted_file_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=Path(tmp)/'package'
            shutil.copytree(ROOT,dest,ignore=shutil.ignore_patterns('__pycache__'))
            (dest/'unlisted.txt').write_text('unexpected',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Unlisted'):verify(dest)

if __name__=='__main__':unittest.main(verbosity=2)
