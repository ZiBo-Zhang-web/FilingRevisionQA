"""Zero-model interface example, explicitly synthetic and not a result."""
import argparse
import json
from pathlib import Path
from build_component_requests import build
from frqa_resource import Resource
from score import parse_response
from paired_diagnostics_v2 import score

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Choose a new output directory; preserve prior outputs')
    root = Path(__file__).resolve().parent
    if args.output.resolve().is_relative_to(root):
        raise ValueError('Keep demonstration outputs outside the immutable package')
    resource = Resource(root / 'data')
    rows = [{'query_id': r['query_id'], 'evidence': []} for r in resource.load_inputs('dev')]
    jobs = build(resource, 'dev', 'synthetic_interface_abstention', rows)
    raw = '{"answer":null,"unit":null,"accession":null,"citations":[]}'
    status, parsed = parse_response(raw, [])
    responses = [{'query_id': j['query_id'], 'condition': j['condition'],
                  'input_sha256': j['input_sha256'], 'raw_text': raw,
                  'status': status, 'parsed': parsed, 'generated_tokens': 0,
                  'synthetic_example': True} for j in jobs]
    # References enter only after synthetic responses are sealed.
    states, pairs, summary, coverage = score(resource.load_references('dev'), responses, jobs,
                                            ['synthetic_interface_abstention'])
    assert len(states) == 144 and len(pairs) == 72
    assert not any(r['numeric_unit_accession_joint'] for r in states)
    args.output.mkdir(parents=True)
    for name, items in [('requests.jsonl', jobs), ('responses.jsonl', responses),
                        ('per_state.jsonl', states), ('per_pair.jsonl', pairs)]:
        (args.output / name).write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in items), encoding='utf-8')
    receipt = {'status': 'passed', 'synthetic_example': True, 'research_result': False,
               'model_calls': 0, 'states': len(states), 'pairs': len(pairs),
               'description': 'Empty evidence plus scripted abstention; verifies request/scorer plumbing only',
               'summary': summary, 'coverage': coverage}
    (args.output / 'DEMO_RECEIPT.json').write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: receipt[k] for k in ['status','synthetic_example','research_result','model_calls','states','pairs']}))

if __name__ == '__main__':
    main()
