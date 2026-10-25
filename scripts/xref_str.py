"""Find code that references a string (or any address) in a PS3 PPU ELF.

PS3 code rarely embeds absolute addresses: it loads a pointer from the TOC
(`lwz/ld rX, off(r2)`), or builds it with `addis rX,r2,hi` + `addi/lwz rY,rX,lo`.
Pointers can also sit in data tables. This script finds, for each target address:
  1. every 4-byte BE data word equal to it (pointer slots / tables / TOC entries);
  2. every r2-relative load or addis/addi pair that resolves to the target or a slot;
and maps each code hit to its containing function (ps3recomp loader functions.json).

Usage:
  python xref_str.py <elf> <functions.json> "Lobby Entry" 0xb11ae0 ...
"""
import bisect
import json
import struct
import sys


def load_elf(path):
    d = open(path, "rb").read()
    phoff, = struct.unpack(">Q", d[0x20:0x28])
    phentsize, phnum = struct.unpack(">HH", d[0x36:0x3a])
    segs = []
    for i in range(phnum):
        p = d[phoff + i * phentsize: phoff + (i + 1) * phentsize]
        ptype, flags, off, vaddr, _, filesz, memsz, _ = struct.unpack(">IIQQQQQQ", p)
        if ptype == 1:
            segs.append((vaddr, d[off:off + filesz], flags))
    return segs


def main():
    elf, funcs_path, *queries = sys.argv[1:]
    segs = load_elf(elf)
    funcs = sorted((int(f["start"], 16), int(f["end"], 16)) for f in json.load(open(funcs_path)))
    starts = [s for s, _ in funcs]
    toc = int(json.load(open(funcs_path))[0]["toc"], 16)

    def func_of(a):
        i = bisect.bisect_right(starts, a) - 1
        return funcs[i][0] if i >= 0 and a < funcs[i][1] else None

    code = [(v, b) for v, b, fl in segs if fl & 1]
    alldata = [(v, b) for v, b, _ in segs]

    for q in queries:
        targets = []
        if q.startswith("0x"):
            targets.append((int(q, 16), q))
        else:
            needle = q.encode()
            for v, b, _ in segs:
                i = b.find(needle)
                while i >= 0:
                    # walk back to the start of the C string
                    s = i
                    while s > 0 and b[s - 1] != 0:
                        s -= 1
                    targets.append((v + s, b[s:b.index(b"\0", s)].decode("latin1")))
                    i = b.find(needle, i + 1)
        for addr, label in targets:
            print(f"\n=== 0x{addr:x}  {label!r}")
            # 1) data pointer slots
            slots = []
            pat = struct.pack(">I", addr)
            for v, b in alldata:
                i = b.find(pat)
                while i >= 0:
                    if i % 4 == 0:
                        slots.append(v + i)
                    i = b.find(pat, i + 1)
            for s in slots:
                print(f"  ptr slot 0x{s:x}" + ("  (TOC)" if abs(s - toc) < 0x10000 else ""))
            wanted = {addr} | set(slots)
            # 2) code references (r2-relative loads, addis/addi pairs, lis/ori absolute)
            hits = []
            for v, b in code:
                n = len(b) // 4
                words = struct.unpack(f">{n}I", b[:n * 4])
                his = {}
                for k, w in enumerate(words):
                    op, rt, ra = w >> 26, (w >> 21) & 31, (w >> 16) & 31
                    simm = w & 0xFFFF
                    simm = simm - 0x10000 if simm & 0x8000 else simm
                    pc = v + k * 4
                    if op == 15:  # addis / lis
                        base = toc if ra == 2 else (0 if ra == 0 else None)
                        if base is not None:
                            his[rt] = (base + (simm << 16)) & 0xFFFFFFFF
                        continue
                    if op in (14, 32, 58, 34, 40) and ra == 2:  # addi/lwz/ld/lbz/lhz off(r2)
                        ea = (toc + (simm & ~3 if op == 58 else simm)) & 0xFFFFFFFF
                        if ea in wanted:
                            hits.append(pc)
                    elif op in (14, 32, 58) and ra in his:
                        ea = (his[ra] + (simm & ~3 if op == 58 else simm)) & 0xFFFFFFFF
                        if ea in wanted:
                            hits.append(pc)
                    elif op == 24 and ra in his:  # ori (lis/ori absolute)
                        if ((his[ra] | (w & 0xFFFF)) & 0xFFFFFFFF) in wanted:
                            hits.append(pc)
            for pc in hits:
                f = func_of(pc)
                print(f"  code 0x{pc:x}  in func_{f:08x}" if f else f"  code 0x{pc:x}")


if __name__ == "__main__":
    main()
