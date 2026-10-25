"""Relift into an isolated directory and execute integer comparisons against PPC64.

Also repeats the 18 real-function regressions from T-007. Does not alter shared
generated code, the runtime, or the baseline report. Exit 1 means a mismatch.
"""
import argparse
import ctypes as C
import json
import random
import sys
from pathlib import Path

import run as d


def synthetic():
    result = []
    for signed in (True, False):
        for width in (32, 64):
            for immediate in (False, True):
                for bf in range(8):
                    for imm in ((0, 1, 0x7fff, 0x8000, 0xffff) if immediate else (0,)):
                        name = ('cmp' if signed else 'cmpl') + ('w' if width == 32 else 'd') + ('i' if immediate else '')
                        common = (bf << 23) | ((width == 64) << 21) | (3 << 16)
                        if immediate:
                            word = ((11 if signed else 10) << 26) | common | imm
                        else:
                            word = (31 << 26) | common | (4 << 11) | (0 if signed else 64)
                        a = 0x3000000 + len(result)*16
                        code = word.to_bytes(4,'big') + bytes.fromhex('4e800020')
                        result.append((a,code,name,bf,imm))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--label', default='fixed')
    args = ap.parse_args()
    if not args.label.isalnum():
        ap.error('label must be alphanumeric')
    out = d.ROOT/'analysis/difftest-so-astra'/args.label
    generated = out/'generated'; compiled = out/'compiled'
    generated.mkdir(parents=True,exist_ok=True); compiled.mkdir(exist_ok=True)
    source = d.ROOT/'agents/astra/ps3recomp/tools/ppu_lifter.py'
    sys.path.insert(0,str(source.parent))
    from ppu_lifter import PPULifter
    from ppu_disasm import disassemble_bytes
    raw = (d.ROOT/'work/eboot/EBOOT_1.00_disc.elf').read_bytes()
    if d.sha(raw) != d.ELF_SHA:
        raise ValueError('ELF identity differs')
    real = list(d.SELECTION)
    synth = synthetic()
    blobs = [(a,raw[a-65536:a-65536+n]) for a,n,_ in real] + [(a,c) for a,c,*_ in synth]
    lifter = PPULifter()
    instructions = []
    for a, code in blobs:
        instructions += disassemble_bytes(code,a)
    for a,code,name,_,_ in synth:
        decoded = disassemble_bytes(code,a)[0]
        if decoded.mnemonic != name:
            raise ValueError(f'encoding {name} decoded as {decoded.mnemonic}')
    for a,code in blobs:
        lifter.lift_function(instructions,a,a+len(code))
    (generated/'ppu_recomp.h').write_text(lifter.emit_header(),encoding='utf-8')
    (generated/'ppu_recomp_000.cpp').write_text(lifter.emit_source(),encoding='utf-8')
    d.SELECTION = real + [(a,len(code),name) for a,code,name,_,_ in synth]
    evidence,build = d.extract(compiled,generated)
    dll = C.CDLL(str(compiled/'difftest.dll'))
    dll.run_case.argtypes = [C.c_uint,C.POINTER(C.c_uint64),C.POINTER(C.c_uint8),C.c_int]
    dll.run_case.restype = C.c_int
    report = {'label':args.label,'lifter_sha256':d.sha(source.read_bytes()),
              'elf_sha256':d.ELF_SHA,'build':build,'functions':[],
              'total_cases':0,'failed_cases':0}
    pairs = [(0,0),(0,1),(1,0),(0xffffffff,0),(0x80000000,0x7fffffff),
             (0xffffffffffffffff,1),(0x8000000000000000,0x7fffffffffffffff),
             (0x100000000,0)]
    rng = random.Random(98472)
    pairs += [(rng.getrandbits(64),rng.getrandbits(64)) for _ in range(8)]
    for fi,(a,code) in enumerate(blobs):
        oracle = d.Oracle(a,code)
        row = {'address':hex(a),'label':d.SELECTION[fi][2],**evidence[a],
               'passed':0,'failed':0,'first_failure':None}
        cases = []
        if fi < len(real):
            cases = [d.inputs(a,i,98472) for i in range(1024)]
        else:
            for left,right in pairs:
                for flags in range(8):
                    for initial_cr in (0,0xffffffff):
                        regs,mem = d.inputs(0x2fb804,0,98472)
                        regs[3],regs[4] = left,right
                        regs[32],regs[33] = initial_cr,(flags<<29)|0x55
                        cases.append((regs,mem))
        for index,(regs,mem) in enumerate(cases):
            diff = d.differences(oracle.run(regs,mem), d.native(dll,fi,regs,mem))
            row['failed' if diff else 'passed'] += 1
            if diff and row['first_failure'] is None:
                row['first_failure'] = {'case':index,'differences':diff,
                                        'input_registers':[hex(x) for x in regs]}
        report['total_cases'] += len(cases)
        report['failed_cases'] += row['failed']
        report['functions'].append(row)
        if fi < len(real) or (fi+1)%32 == 0:
            print(f'{fi+1}/{len(blobs)} functions; {report["total_cases"]} cases; '
                  f'{report["failed_cases"]} mismatches',flush=True)
    report['real_functions'] = len(real)
    report['synthetic_functions'] = len(synth)
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    if args.label == 'fixed':
        (d.ROOT/'reports/difftest-so.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'TOTAL {report["total_cases"]}; FAILURES {report["failed_cases"]}',flush=True)
    return int(report['failed_cases'] != 0)


if __name__ == '__main__':
    raise SystemExit(main())
