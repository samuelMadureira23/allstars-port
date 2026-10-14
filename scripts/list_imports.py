"""Resolve an EBOOT's firmware imports (ppu_loader *.imports.json) to names via the
ps3recomp NID database and report which ones ps3recomp already implements in HLE.

Usage: python list_imports.py <imports.json> [--md out.md]
"""
import argparse
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PS3RECOMP = os.path.join(ROOT, "src", "ps3recomp")
sys.path.insert(0, os.path.join(PS3RECOMP, "tools"))
from nid_database import get_default_db, NIDDatabase  # noqa: E402

NET_LIBS = {"sceNp", "sceNpTus", "sys_net", "cellNetCtl", "cellHttp", "cellHttpUtil",
            "cellVoice", "sceNpTrophy", "cellSysutilNpEula"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("imports")
    ap.add_argument("--md")
    a = ap.parse_args()

    db = get_default_db()
    impl = NIDDatabase()
    impl.load_implemented(PS3RECOMP)
    implemented = {nid for nid, _, _ in impl.all_entries()}

    by_lib = collections.defaultdict(list)
    for e in json.load(open(a.imports)):
        nid = int(e["nid"], 16)
        hit = db.lookup_nid(nid)
        name = hit[1] if hit else None
        by_lib[e["library"]].append((nid, name, nid in implemented, e["stub"]))

    lines = ["| Biblioteca | NID | Nome | HLE no ps3recomp |", "|---|---|---|---|"]
    total = named = done = 0
    for lib in sorted(by_lib, key=lambda l: (l not in NET_LIBS, l)):
        for nid, name, ok, stub in sorted(by_lib[lib], key=lambda t: t[1] or "~"):
            total += 1; named += bool(name); done += ok
            lines.append(f"| {lib} | 0x{nid:08x} | {name or '?'} | {'sim' if ok else 'NAO'} |")
    summary = f"{total} imports, {named} com nome, {done} com HLE implementado"
    print(summary)
    for lib in sorted(by_lib):
        rows = by_lib[lib]
        print(f"  {lib:20s} {len(rows):3d}  nomes={sum(bool(r[1]) for r in rows):3d}  hle={sum(r[2] for r in rows):3d}")
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(f"# Imports do EBOOT\n\n{summary}\n\n" + "\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
