"""Function-start candidates the SPU lifter misses: code right after a return.

SPU functions reached only through runtime-built pointers (C++ vtables filled by
constructors, callback tables) are invisible to the lifter's branch analysis.
Their entries almost always sit right after the previous function's end -- a
`bi $lr` (0x35000000) or an unconditional `br` -- past alignment padding
(lnop/nop/zero words). This lists those addresses that are not yet function
starts in a lifted image, for spu_lifter/build_spu_workloads --extra-funcs.

Usage: python scripts/spu_func_candidates.py <image.elf> <lifted spu_recomp.c> <prefix> [--append list.txt]
"""
import re
import struct
import sys


def main():
    elf, lifted, prefix = sys.argv[1:4]
    d = open(elf, "rb").read()
    phoff = struct.unpack(">I", d[28:32])[0]
    phnum = struct.unpack(">H", d[44:46])[0]
    base = off = size = None
    for i in range(phnum):
        t, o, va, _, fs, _, fl, _ = struct.unpack(">8I", d[phoff + i * 32: phoff + i * 32 + 32])
        if t == 1 and fl & 1:
            base, off, size = va, o, fs
            break
    words = [struct.unpack(">I", d[off + i: off + i + 4])[0] for i in range(0, size - 3, 4)]
    known = set(int(x, 16) for x in re.findall(r"^void %sspu_func_([0-9A-F]{8})\(" % re.escape(prefix),
                                               open(lifted).read(), re.M))
    pad = {0x00200000, 0x40200000, 0}
    cands = set()
    for i, w in enumerate(words):
        if w == 0x35000000 or (w >> 23) == 0x64:          # bi $lr | br
            j = i + 1
            while j < len(words) and words[j] in pad:
                j += 1
            if j < len(words):
                cands.add(base + 4 * j)
    new = sorted(cands - known)
    print(f"{len(cands)} post-return starts, {len(new)} not yet lifted as functions")
    if "--append" in sys.argv:
        path = sys.argv[sys.argv.index("--append") + 1]
        try:
            cur = [x for x in open(path).read().strip().split(",") if x]
        except FileNotFoundError:
            cur = []
        have = {int(x, 16) for x in cur}
        cur += ["0x%X" % a for a in new if a not in have]
        open(path, "w").write(",".join(cur))
        print(f"{path}: {len(cur)} entries")
    else:
        print(",".join("0x%X" % a for a in new))


if __name__ == "__main__":
    main()
