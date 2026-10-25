"""Create a segment-only analysis copy; never change the source ELF."""
import argparse
import hashlib
import json
import struct
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
data = bytearray(args.source.read_bytes())
if data[:6] != b'\x7fELF\x02\x02':
    raise SystemExit('Expected ELF64 big-endian')
source_hash = hashlib.sha256(data).hexdigest()
struct.pack_into('>Q', data, 40, 0)
struct.pack_into('>HHH', data, 58, 0, 0, 0)
with args.output.open('xb') as stream:
    stream.write(data)
args.output.with_suffix('.provenance.json').write_text(json.dumps({
    'source': str(args.source.resolve()), 'source_sha256': source_hash,
    'output_sha256': hashlib.sha256(data).hexdigest(),
    'changes': 'ELF header only: e_shoff/e_shentsize/e_shnum/e_shstrndx zeroed for segment-only import. Not for game execution.'
}, indent=2), encoding='utf-8')
