"""Inspect ELF64 big-endian section/segment layout and embedded ELF candidates."""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from inventory import elf_header

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('elf', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
data = args.elf.read_bytes()
header = elf_header(data)
if data[:6] != b'\x7fELF\x02\x02':
    raise SystemExit('Expected ELF64 big endian')
segments = []
for i in range(header['phnum']):
    raw = struct.unpack_from('>II6Q', data, header['phoff'] + i * header['phentsize'])
    segments.append(dict(zip(['type', 'flags', 'offset', 'vaddr', 'paddr', 'filesz', 'memsz', 'align'], raw)))
sections = []
for i in range(header['shnum']):
    raw = struct.unpack_from('>II4QII2Q', data, header['shoff'] + i * header['shentsize'])
    sections.append(dict(zip(['name_offset', 'type', 'flags', 'addr', 'offset', 'size', 'link', 'info', 'align', 'entsize'], raw)))
names = sections[header['shstrndx']]
name_data = data[names['offset']:names['offset'] + names['size']]
for section in sections:
    section['name'] = name_data[section['name_offset']:].split(b'\0', 1)[0].decode('utf-8', errors='replace')
candidates = []
start = 1
while (start := data.find(b'\x7fELF', start)) >= 0:
    try:
        candidate = elf_header(data[start:start + 64])
        candidates.append({'offset': start, 'header': candidate})
    except (struct.error, IndexError):
        pass
    start += 4
report = {'path': str(args.elf.resolve()), 'sha256': hashlib.sha256(data).hexdigest(),
          'header': header, 'segments': segments, 'sections': sections,
          'embedded_elf_candidates': candidates,
          'limitations': 'Embedded signatures are candidates only; not proof of execution or complete SPU inventory.'}
args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'sha256': report['sha256'], 'sections': [(s['name'], s['size']) for s in sections],
                  'embedded_elf_candidates': len(candidates)}, indent=2))
