"""Verify the complete portable candidate before loading it."""
import json
from pathlib import Path
from frqa_resource import safe_path, sha

def verify(root):
    root=Path(root).resolve()
    m=json.loads((root/'PACKAGE_MANIFEST.json').read_text(encoding='utf-8'))
    if m.get('independent_gate_included') is not False:raise ValueError('Unexpected scope')
    names=set()
    for r in m['files']:
        if r['path'] in names:raise ValueError('Duplicate path')
        names.add(r['path']);p=safe_path(root,r['path'])
        if p.stat().st_size!=r['bytes'] or sha(p)!=r['sha256']:raise ValueError('Hash mismatch: '+r['path'])
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    if actual!=names|{'PACKAGE_MANIFEST.json'}:raise ValueError('Unlisted or missing package files')
    return {'status':'passed','manifest_members':len(names),'manifest_sha256':sha(root/'PACKAGE_MANIFEST.json'),
        'public_release_authorized':bool(m.get('publication_authorized', False))}

if __name__=='__main__':print(json.dumps(verify(Path(__file__).parent),indent=2))
