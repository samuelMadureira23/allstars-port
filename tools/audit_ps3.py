"""Validate OPD bytes and extract bounded embedded SPU ELF32 images, offline."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import struct

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('layout', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
layout = json.loads(args.layout.read_text(encoding='utf-8'))
data = Path(layout['path']).read_bytes()
assert hashlib.sha256(data).hexdigest() == layout['sha256'], 'Layout is stale'
args.output.mkdir(parents=True, exist_ok=True)
entry = layout['header']['entry']
region = min((s for s in layout['sections'] if s['addr'] <= entry < s['addr'] + s['size']), key=lambda s: s['size'])
assert region['size'] % 8 == 0
code = [(s['addr'], s['addr'] + s['size']) for s in layout['sections'] if s['flags'] & 4]
descriptors = []
contexts = defaultdict(set)
for offset in range(0, region['size'], 8):
    address, toc = struct.unpack_from('>II', data, region['offset'] + offset)
    assert address % 4 == 0 and any(lo <= address < hi for lo, hi in code)
    assert any(p['type'] == 1 and p['vaddr'] <= toc < p['vaddr'] + p['memsz'] for p in layout['segments'])
    contexts[address].add(toc)
    descriptors.append({'opd': region['addr'] + offset, 'code': address, 'toc': toc})
spus = []
for candidate in layout['embedded_elf_candidates']:
    start, header = candidate['offset'], candidate['header']
    if header['machine'] != 23 or header['class_bits'] != 32 or header['endianness'] != 'big':
        continue
    assert header['phentsize'] == 32 and 0 < header['phnum'] <= 16 and header['shnum'] == 0
    end = max(52, header['phoff'] + header['phnum'] * 32)
    segments = []
    for i in range(header['phnum']):
        fields = struct.unpack_from('>8I', data, start + header['phoff'] + i * 32)
        segment = dict(zip(['type', 'offset', 'vaddr', 'paddr', 'filesz', 'memsz', 'flags', 'align'], fields))
        if segment['type'] == 1:
            assert segment['filesz'] <= segment['memsz']
            assert segment['vaddr'] + segment['memsz'] <= 0x40000, 'SPU local-store overflow'
            assert start + segment['offset'] + segment['filesz'] <= len(data)
        end = max(end, segment['offset'] + segment['filesz'])
        segments.append(segment)
    assert end <= 0x100000 and start + end <= len(data)
    assert any(s['type'] == 1 and s['flags'] & 1 and s['vaddr'] <= header['entry'] < s['vaddr'] + s['filesz'] for s in segments)
    blob = data[start:start + end]
    output = args.output / f'spu_{start:08x}.elf'
    if output.exists():
        assert output.read_bytes() == blob, 'Existing output differs'
    else:
        output.write_bytes(blob)
    spus.append({'source_offset': start, 'bytes': end, 'sha256': hashlib.sha256(blob).hexdigest(),
                 'entry': header['entry'], 'segments': segments, 'output': str(output.resolve())})
summary = {'source_sha256': layout['sha256'], 'opd_region': region, 'descriptor_count': len(descriptors),
           'distinct_code_entries': len(contexts), 'toc_histogram': dict(Counter(hex(d['toc']) for d in descriptors)),
           'entries_with_multiple_tocs': {hex(k): [hex(v) for v in sorted(values)] for k, values in contexts.items() if len(values) > 1},
           'spu_images': spus, 'limitations': 'Static structure validation; no execution, runtime task identification or full function-boundary proof.'}
(args.output / 'opd-descriptors.json').write_text(json.dumps(descriptors, indent=2), encoding='utf-8')
(args.output / 'audit.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(json.dumps({k: v for k, v in summary.items() if k not in ('opd_region', 'spu_images', 'entries_with_multiple_tocs')}, indent=2))
print('SPU images:', len(spus), 'code entries with multiple TOCs:', len(summary['entries_with_multiple_tocs']))
