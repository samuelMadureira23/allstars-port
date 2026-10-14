"""Disassemble a PPU address range of the decrypted EBOOT with capstone.

Usage: python scripts/disasm.py <start_hex> <end_hex> [elf]
"""
import os
import struct
import sys

from capstone import CS_ARCH_PPC, CS_MODE_64, CS_MODE_BIG_ENDIAN, Cs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def segments(d):
    phoff, = struct.unpack(">Q", d[0x20:0x28])
    phnum, = struct.unpack(">H", d[0x38:0x3a])
    for i in range(phnum):
        p = struct.unpack(">IIQQQQQQ", d[phoff + i * 56: phoff + i * 56 + 56])
        if p[0] == 1:
            yield p[3], p[2], p[5]


def main():
    start, end = int(sys.argv[1], 16), int(sys.argv[2], 16)
    elf = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "work", "eboot", "EBOOT_1.00_disc.elf")
    d = open(elf, "rb").read()
    for va, off, size in segments(d):
        if va <= start < va + size:
            code = d[off + start - va: off + end - va]
            md = Cs(CS_ARCH_PPC, CS_MODE_64 | CS_MODE_BIG_ENDIAN)
            for ins in md.disasm(code, start):
                print(f"{ins.address:08x}  {ins.mnemonic:8s} {ins.op_str}")
            return
    sys.exit("address not in a PT_LOAD segment")


if __name__ == "__main__":
    main()
