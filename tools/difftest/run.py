"""Compare unchanged generated PPU functions with their ELF bytes in Unicorn.

No game code/keys are embedded here. Extracted sources and DLLs stay in analysis/.
Run with the project's Python on Windows; needs existing clang-cl/VS Build Tools.
"""
from __future__ import annotations
import argparse
import ctypes as C
import hashlib
import json
import random
import re
import shutil
import subprocess
from pathlib import Path

import capstone
import unicorn as U
from unicorn import ppc_const as P

ROOT = Path(__file__).resolve().parents[2]
ELF_SHA = "a9de806aff3c80fb903831dee0a854738b62bfd4090dfbeccc332f49d92609b5"
# Address, code size through actual return, descriptive coverage (not recovered names).
SELECTION = [
    (0x11B84, 12, "store32"), (0x4AE70, 16, "toc_pointer_store"),
    (0x4D338, 32, "copy64_store8_32"), (0x133B74, 12, "oris"),
    (0x2A3524, 28, "store_update"), (0x2D4970, 40, "subtract_memory"),
    (0x2FB804, 12, "add_truncate32"), (0x3027C8, 36, "sign_shift_carry"),
    (0x364EAC, 12, "rotate64_mask"), (0x47E550, 24, "unsigned_compare_branch"),
    (0x4A70D4, 36, "negate_shift_rotate"), (0x4D7784, 16, "addic_store"),
    (0x4E32F8, 48, "copy8_16_32"), (0x5DF650, 16, "or_memory64"),
    (0x5F3B00, 32, "and_sign_shift"), (0xA08C08, 12, "sign_extend16"),
    (0xAA34B8, 20, "addic_count_leading_zero"),
    (0xAA3BB4, 20, "addc_addic_truncate"),
]
MASK64 = (1 << 64) - 1
XER_MASK = 0xE000007F  # PS3 SO/OV/CA and byte count; exclude newer ISA CA32.
BASE, TOC_PAGE, STOP, SET_XER, GET_XER = 0x1000000, 0xC7C000, 0x2000000, 0x2000004, 0x2000008
EDGES = [0, 1, 2, 3, 5, 6, 7, 31, 32, 63, 64, 0x7FFF, 0x8000,
         0xFFFF, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0x100000000,
         0x7FFFFFFFFFFFFFFF, 0x8000000000000000, MASK64]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def extract(out):
    generated = ROOT / "work/recompiled_1.00"
    header = (generated / "ppu_recomp.h").read_bytes()
    (out / "ppu_recomp.h").write_bytes(header)
    wanted = {a for a, _, _ in SELECTION}
    evidence, units = {}, []
    pattern = re.compile(r"^void func_([0-9A-F]{8})\(ppu_context\* ctx\) \{", re.M)
    for path in sorted(generated.glob("ppu_recomp_*.cpp")):
        raw = path.read_bytes()
        source = raw.decode("utf-8")
        matches = list(pattern.finditer(source))
        selected = [m for m in matches if int(m[1], 16) in wanted]
        if not selected:
            continue
        # Preserve the source's original helper prefix and complete function bodies.
        prefix = source[:matches[0].start()]
        bodies = []
        for match in selected:
            end = source.index("\n}", match.end()) + 2
            body = source[match.start():end]
            # Top-level closing brace is at column 0 in lifter output.
            if body.count("{") != body.count("}"):
                raise ValueError("unbalanced generated function")
            a = int(match[1], 16)
            if a in evidence:
                raise ValueError("duplicate generated function")
            evidence[a] = {"source": str(path.relative_to(ROOT)), "source_sha256": sha(raw),
                           "body_sha256": sha(body.encode()), "helpers_sha256": sha(prefix.encode())}
            bodies.append(body)
        unit = out / path.name
        unit.write_bytes((prefix + "\n\n".join(bodies) + "\n").encode())
        units.append(unit.name)
    if wanted != evidence.keys():
        raise ValueError(f"missing generated functions: {wanted - evidence.keys()}")
    (out / "selection.h").write_text("static void (*selected[])(ppu_context*) = {\n" +
        ",\n".join(f"func_{a:08X}" for a, _, _ in SELECTION) + "\n};\n")
    shutil.copyfile(Path(__file__).with_name("bridge.cpp"), out / "bridge.cpp")
    vcvars = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat")
    compiler = Path(r"C:\Program Files\LLVM\bin\clang-cl.exe")
    if not vcvars.is_file() or not compiler.is_file():
        raise FileNotFoundError("existing clang-cl/VS paths not found; no installation attempted")
    version = subprocess.run([str(compiler), "--version"], capture_output=True, text=True, check=True).stdout
    batch = out / "build.bat"
    batch.write_text(f'@echo off\ncall "{vcvars}" >nul\nif errorlevel 1 exit /b 1\n'
        f'"{compiler}" /nologo /LD /O2 /EHsc /std:c++17 /Fe:difftest.dll bridge.cpp ' +
        " ".join(units) + "\nexit /b %errorlevel%\n")
    build = subprocess.run(["cmd.exe", "/d", "/c", str(batch)], cwd=out, capture_output=True, text=True)
    (out / "build.log").write_text(build.stdout + build.stderr)
    if build.returncode:
        raise RuntimeError(f"compilation failed; see {out / 'build.log'}")
    return evidence, {"compiler": version.strip(), "flags": "/LD /O2 /EHsc /std:c++17",
                      "header_sha256": sha(header), "dll_sha256": sha((out / "difftest.dll").read_bytes())}

def inputs(address, index, seed):
    # Per-case seed makes any mismatch reproducible independently of earlier cases.
    rng = random.Random((seed << 40) ^ (address << 16) ^ index)
    regs = [rng.getrandbits(64) for _ in range(32)]
    value = EDGES[index] if index < len(EDGES) else rng.getrandbits(64)
    regs[3] = value
    if index < len(EDGES):
        regs[4] = EDGES[(index+7) % len(EDGES)]
        regs[5] = EDGES[(index+13) % len(EDGES)]
    regs[2] = 0xC84768
    regs += [rng.getrandbits(32), rng.getrandbits(32) & XER_MASK, STOP, rng.getrandbits(64)]
    memory = bytearray(rng.randbytes(8192))
    def put(a, v, n=4):
        p = a - BASE if a >= BASE else a - TOC_PAGE + 4096
        assert 0 <= p <= len(memory)-n
        memory[p:p+n] = (v & ((1 << (8*n))-1)).to_bytes(n, "big")
    # Valid, disjoint input/output objects; arithmetic operands remain unconstrained.
    if address == 0x11B84:
        regs[4] = BASE + 0x500
    if address == 0x4AE70:
        put(regs[2]-0x79AC, BASE+0x100)
        put(regs[2]-0x79A4, value)
    object_r3 = {0x4D338, 0x2A3524, 0x2D4970, 0x3027C8, 0x4D7784,
                 0x4E32F8, 0x5DF650, 0x5F3B00, 0xA08C08, 0xAA34B8}
    if address in object_r3:
        regs[3] = BASE+0x100
        for displacement, width in ((4,4),(8,4),(12,4),(16,4),(32,4),(48,2),(432,4),(688,8)):
            put(regs[3]+displacement, value, width)
    if address in {0x4D338, 0x2A3524}:
        regs[5] = BASE+0x900
    if address == 0x4E32F8:
        regs[4] = BASE+0x500
        for d, n in ((0,1),(4,4),(8,2),(12,4),(16,2)):
            put(regs[4]+d, value, n)
    return regs, memory

class Oracle:
    def __init__(self, a, code):
        self.a = a
        self.cpu = c = U.Uc(U.UC_ARCH_PPC, U.UC_MODE_64 | U.UC_MODE_BIG_ENDIAN)
        c.ctl_set_tlb_mode(U.UC_TLB_VIRTUAL)
        c.mem_map(a & ~4095, 8192)
        c.mem_write(a, code)
        for page in (BASE, TOC_PAGE, STOP):
            c.mem_map(page, 4096)
        # mtxer r7; mfxer r6. API XER access omits QEMU's split CA/OV/SO flags.
        c.mem_write(SET_XER, bytes.fromhex("7ce103a67cc102a6"))
        c.reg_write(P.UC_PPC_REG_MSR, 1 << 63)

    def run(self, regs, memory):
        c = self.cpu
        c.mem_write(BASE, bytes(memory[:4096]))
        c.mem_write(TOC_PAGE, bytes(memory[4096:]))
        c.reg_write(P.UC_PPC_REG_7, regs[33])
        c.emu_start(SET_XER, GET_XER, count=1)
        for i in range(32):
            c.reg_write(P.UC_PPC_REG_0+i, regs[i])
        for r, val in zip((P.UC_PPC_REG_CR,P.UC_PPC_REG_LR,P.UC_PPC_REG_CTR), (regs[32],regs[34],regs[35])):
            c.reg_write(r, val)
        # The instruction budget bounds even a bad branch. Avoid a timeout thread
        # per tiny invocation (very expensive on Windows).
        c.emu_start(self.a, STOP, count=128)
        if c.reg_read(P.UC_PPC_REG_PC) != STOP:
            raise RuntimeError("oracle did not return within instruction bound")
        result = [c.reg_read(P.UC_PPC_REG_0+i) for i in range(32)]
        result += [c.reg_read(P.UC_PPC_REG_CR), 0, c.reg_read(P.UC_PPC_REG_LR), c.reg_read(P.UC_PPC_REG_CTR)]
        c.emu_start(GET_XER, GET_XER+4, count=1)
        result[33] = c.reg_read(P.UC_PPC_REG_6) & XER_MASK
        return result, bytes(c.mem_read(BASE,4096)) + bytes(c.mem_read(TOC_PAGE,4096))

def native(dll, function, regs, memory, inject=0):
    r = (C.c_uint64*36)(*regs)
    m = (C.c_uint8*8192).from_buffer_copy(memory)
    status = dll.run_case(function, r, m, inject)
    if status:
        raise RuntimeError(f"native bridge status {status} (1=memory bounds, 2=function index)")
    result = list(r)
    result[33] &= XER_MASK
    return result, bytes(m)

def differences(expected, actual):
    er, em = expected; ar, am = actual
    labels = [f"r{i}" for i in range(32)] + ["cr", "xer", "lr", "ctr"]
    result = [{"register": label, "ppc": hex(x), "native": hex(y)}
              for label, x, y in zip(labels, er, ar) if x != y]
    changed = [i for i, (x,y) in enumerate(zip(em, am)) if x != y]
    if changed:
        result.append({"memory_byte_mismatches": len(changed), "first_offsets": changed[:16]})
    return result

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--cases", type=int, default=1024, help="per function, includes boundary cases")
    ap.add_argument("--seed", type=int, default=98472)
    ap.add_argument("--out", type=Path, default=ROOT/"analysis/difftest-astra")
    ap.add_argument("--report", type=Path, default=ROOT/"reports/difftest-1.00.json")
    args = ap.parse_args()
    if args.cases < len(EDGES):
        ap.error(f"--cases must be >= {len(EDGES)}")
    out = args.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    raw = (ROOT/"work/eboot/EBOOT_1.00_disc.elf").read_bytes()
    if sha(raw) != ELF_SHA:
        raise ValueError("ELF identity differs from validated base 1.00; refusing addresses")
    sources, build = extract(out)
    dll = C.CDLL(str(out/"difftest.dll"))
    dll.run_case.argtypes = [C.c_uint, C.POINTER(C.c_uint64), C.POINTER(C.c_uint8), C.c_int]
    dll.run_case.restype = C.c_int
    dis = capstone.Cs(capstone.CS_ARCH_PPC,capstone.CS_MODE_64|capstone.CS_MODE_BIG_ENDIAN)
    report = {"elf_sha256": ELF_SHA, "seed": args.seed, "cases_per_function": args.cases,
              "unicorn_version": U.__version__, "build": build,
              "compared": "32 GPRs, CR, XER mask 0xe000007f, LR, CTR, 8192 memory bytes",
              "limits": "selected integer leaves only; synthetic valid memory; no FP/SIMD/SPU/HLE/concurrency/gameplay",
              "functions": []}
    total_bad = 0
    for fi, (a, size, label) in enumerate(SELECTION):
        code = raw[a-0x10000:a-0x10000+size]
        instructions = list(dis.disasm(code,a))
        if sum(i.size for i in instructions) != size or instructions[-1].mnemonic != "blr":
            raise ValueError(f"invalid function extent {a:x}")
        oracle = Oracle(a,code)
        result = {"address": hex(a), "label": label, "size": size, "code_sha256": sha(code),
                  **sources[a], "passed": 0, "failed": 0, "examples": [],
                  "failure_case_indices": [], "difference_patterns": {},
                  "xer_so_cases": {"0": {"passed": 0, "failed": 0}, "1": {"passed": 0, "failed": 0}},
                  "mnemonics": [i.mnemonic for i in instructions]}
        for i in range(args.cases):
            regs, memory = inputs(a,i,args.seed)
            expected = oracle.run(regs,memory)
            actual = native(dll,fi,regs,memory)
            diff = differences(expected,actual)
            result["xer_so_cases"][str(regs[33] >> 31)]["failed" if diff else "passed"] += 1
            if diff:
                result["failed"] += 1
                result["failure_case_indices"].append(i)
                for item in diff:
                    pattern = (item["register"] + " xor " + hex(int(item["ppc"],16)^int(item["native"],16))
                               if "register" in item else "memory")
                    result["difference_patterns"][pattern] = result["difference_patterns"].get(pattern,0)+1
                if len(result["examples"]) < 4:
                    result["examples"].append({"case": i, "differences": diff,
                        "input_registers": [hex(x) for x in regs], "input_memory_sha256": sha(memory)})
            else:
                result["passed"] += 1
        total_bad += result["failed"]
        report["functions"].append(result)
        print(f'{a:08X} {label}: {result["passed"]} passed, {result["failed"]} failed', flush=True)
    # Verify the comparison sees a known, deliberately corrupted output.
    regs, mem = inputs(SELECTION[0][0], 0, args.seed)
    expected = Oracle(SELECTION[0][0], raw[0x11B84-0x10000:0x11B84-0x10000+12]).run(regs,mem)
    negative = differences(expected,native(dll,0,regs,mem,inject=1))
    report["negative_control_detected"] = any(d.get("register")=="r3" for d in negative)
    # Out-of-range memory must fail rather than alias/wrap into valid memory.
    regs[4] = 0
    try:
        native(dll,0,regs,mem)
    except RuntimeError as e:
        report["memory_bounds_control_detected"] = "status 1" in str(e)
    else:
        report["memory_bounds_control_detected"] = False
    report["total_cases"] = args.cases*len(SELECTION)
    report["failed_cases"] = total_bad
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,indent=2)+"\n")
    print(f'TOTAL {report["total_cases"]}, mismatches {total_bad}; controls: '
          f'{report["negative_control_detected"]}, {report["memory_bounds_control_detected"]}')
    return int(total_bad != 0 or not report["negative_control_detected"] or not report["memory_bounds_control_detected"])

if __name__ == "__main__":
    raise SystemExit(main())
