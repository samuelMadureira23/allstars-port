"""Decrypt a private copy with the locally installed RPCS3 CLI; never boot the game."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from inventory import inspect

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
parser.add_argument('rpcs3', type=Path)
parser.add_argument('output_dir', type=Path)
args = parser.parse_args()
args.output_dir.mkdir(parents=True, exist_ok=False)
copy = args.output_dir.resolve() / 'EBOOT.BIN'
shutil.copyfile(args.source, copy)
before = hashlib.sha256(copy.read_bytes()).hexdigest()
run = subprocess.run([str(args.rpcs3.resolve()), '--decrypt', str(copy)],
                     stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                     timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
(args.output_dir / 'decrypt.stdout.txt').write_bytes(run.stdout)
(args.output_dir / 'decrypt.stderr.txt').write_bytes(run.stderr)
report = {'source': str(args.source.resolve()), 'source_sha256': before,
          'rpcs3': str(args.rpcs3.resolve()), 'returncode': run.returncode,
          'source_unchanged': hashlib.sha256(args.source.read_bytes()).hexdigest() == before,
          'outputs': {p.name: inspect(p) for p in args.output_dir.iterdir() if p.suffix.upper() in ('.BIN', '.ELF')}}
(args.output_dir / 'provenance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
if not any('elf' in item for item in report['outputs'].values()):
    raise SystemExit('No decrypted ELF produced; inspect the saved logs.')
