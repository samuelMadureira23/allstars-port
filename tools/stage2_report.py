"""Summarize observed loader/audit results; verify agreement of import parsers."""
import json
from pathlib import Path
from collections import Counter
import subprocess

root = Path(__file__).resolve().parent.parent
reports = []
for version in ('1.00', '1.12'):
    directory = root / 'analysis' / ('ppu-' + version)
    loader = json.loads((directory / 'EBOOT.loader.json').read_text())
    raw = json.loads((directory / 'EBOOT.imports.json').read_text())
    named = json.loads((directory / 'imports-named.json').read_text())
    a = {(x['library'], int(x['nid'], 16), int(x['stub'], 16)) for x in raw}
    b = {(x['lib'], int(x['nid'], 16), int(x['stub'], 16)) for x in named}
    assert a == b and len(a) == len(raw) == len(named), 'Import readers disagree or duplicate records'
    audit = json.loads((root / 'analysis' / ('audit-' + version) / 'audit.json').read_text())
    assert loader['opd_count'] == audit['descriptor_count']
    assert loader['function_count'] == audit['distinct_code_entries']
    reports.append({'version': version, 'loader': loader, 'toc_histogram': audit['toc_histogram'],
                    'imports': len(named), 'imports_by_library': dict(Counter(x['lib'] for x in named)),
                    'named_imports': sum('name' in x for x in named),
                    'unresolved_imports': [x for x in named if 'name' not in x],
                    'spu_count': len(audit['spu_images']), 'spu_hashes': [x['sha256'] for x in audit['spu_images']]})
commit = subprocess.check_output(['git', '-C', str(root / 'tools/ps3recomp'), 'rev-parse', 'HEAD'], text=True).strip()
result = {'ps3recomp_commit': commit, 'versions': reports,
          'limitations': 'OPD gives code entry points, not exhaustive functions or exact end boundaries. NID names are database-derived, not execution evidence. Imports do not establish runtime usage or online compatibility.'}
(root / 'reports/stage2.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('Crosschecks passed; ps3recomp commit:', commit)
for report in reports:
    print(report['version'], report['loader']['function_count'], 'code entries;', report['named_imports'], '/', report['imports'], 'named imports;', report['spu_count'], 'SPU images')
