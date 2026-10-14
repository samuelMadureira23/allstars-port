"""Resolve exe RVAs (from a [CRASH] line) to the nearest symbol in build/MyGameRecomp.map.

Usage: python scripts/sym.py [--build build-claude] 0x449986B [0x...]
"""
import bisect
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
args = sys.argv[1:]
build = "build"
if args[:1] == ["--build"]:
    build, args = args[1], args[2:]
MAP = os.path.join(ROOT, build, "MyGameRecomp.map")
BASE = 0x140000000

syms = []
line_re = re.compile(r"^\s*[0-9a-fA-F]{4}:[0-9a-fA-F]{8}\s+(\S+)\s+([0-9a-fA-F]{16})\s")
for line in open(MAP, encoding="utf-8", errors="replace"):
    m = line_re.match(line)
    if not m:
        continue
    syms.append((int(m.group(2), 16), m.group(1)))
syms.sort()
addrs = [a for a, _ in syms]

for arg in args:
    va = BASE + int(arg, 16)
    i = bisect.bisect_right(addrs, va) - 1
    print(f"{arg}: {syms[i][1]} +0x{va - syms[i][0]:X}" if i >= 0 else f"{arg}: ?")
