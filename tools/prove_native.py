"""Translate one verified leaf to native x64 and compare against Unicorn PPC64.

This is a bounded instruction-equivalence experiment, not a game port.
Dependencies: Unicorn 2.1.4 in .venv, existing MSVC x64 compiler.
"""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import unicorn
from unicorn import Uc, UC_ARCH_PPC, UC_MODE_64, UC_MODE_BIG_ENDIAN, UC_TLB_VIRTUAL
from unicorn.ppc_const import UC_PPC_REG_3, UC_PPC_REG_5, UC_PPC_REG_6, UC_PPC_REG_7, UC_PPC_REG_LR, UC_PPC_REG_MSR, UC_PPC_REG_PC

ROOT = Path(__file__).resolve().parent.parent
ADDRESS = 0x4a70d4
EXPECTED = bytes.fromhex('68a500017ca500d07ca5fe7054a3d87e5463283e3c638001386307137c6307b44e800020')
MASK = (1 << 64) - 1
C_SOURCE = r'''
/* Manual, instruction-based translation of BCUS98472 1.00 VA 0x004A70D4.
   Purpose in the game unknown. No PS3 runtime or proprietary headers needed. */
typedef unsigned long long U64;
typedef unsigned int U32;
typedef char require_u64_8[sizeof(U64) == 8 ? 1 : -1];
typedef char require_u32_4[sizeof(U32) == 4 ? 1 : -1];
static U32 rol32(U32 x, unsigned n) { return (x << n) | (x >> (32 - n)); }
__declspec(dllexport) void translated(U64 input_r5, U64 initial_xer, U64 *out) {
    U64 r5 = 0ULL - (input_r5 ^ 1ULL);          /* xori; neg */
    U32 word = (U32)r5;
    U64 carry = ((word & 0x80000000U) != 0 && (word & 0x7fffffffU) != 0);
    r5 = (word & 0x80000000U) ? ~0ULL : 0;    /* srawi r5,r5,31 */
    U32 rotate = rol32((U32)r5, 27) & 0x7fffffffU;
    U64 r3 = rol32(rotate, 5);
    r3 += 0xffffffff80010000ULL;               /* signed addis 0x8001 */
    r3 += 1811ULL;
    r3 = (r3 & 0x80000000ULL) ? (r3 | 0xffffffff00000000ULL) : (r3 & 0xffffffffULL);
    out[0] = r3;
    out[1] = r5;
    out[2] = (initial_xer & ~(1ULL << 29)) | (carry << 29);
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--cases', type=int, default=10000)
    args = parser.parse_args()
    elf = ROOT / 'analysis/base-1.00-isolated/EBOOT.elf'
    data = elf.read_bytes()
    assert hashlib.sha256(data).hexdigest() == 'a9de806aff3c80fb903831dee0a854738b62bfd4090dfbeccc332f49d92609b5'
    code = data[ADDRESS - 0x10000:ADDRESS - 0x10000 + len(EXPECTED)]
    assert code == EXPECTED
    assert struct.unpack_from('>II', data, 0xc58290) == (ADDRESS, 0xc84768)
    directory = ROOT / 'analysis/native-proof'
    directory.mkdir(parents=True, exist_ok=True)
    source, dll = directory / 'translated_leaf.c', directory / 'translated_leaf.dll'
    source.write_text(C_SOURCE, encoding='utf-8')
    environment = os.environ.copy()
    environment['PATH'] = str(args.compiler.parent) + os.pathsep + environment['PATH']
    result = subprocess.run([str(args.compiler), '/nologo', '/LD', '/O2', '/GS-',
                             str(source), '/Fe:' + str(dll), '/Fo:' + str(directory / 'translated_leaf.obj'),
                             '/link', '/NOENTRY', '/NODEFAULTLIB', '/MACHINE:X64'],
                            cwd=directory, env=environment, capture_output=True, timeout=60)
    (directory / 'build.log').write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError((result.stdout + result.stderr).decode(errors='replace'))
    native = ctypes.CDLL(str(dll)).translated
    native.argtypes = [ctypes.c_uint64, ctypes.c_uint64, ctypes.POINTER(ctypes.c_uint64)]
    native.restype = None
    cpu = Uc(UC_ARCH_PPC, UC_MODE_64 | UC_MODE_BIG_ENDIAN)
    # Virtual TLB prevents dependence on the default model's unconfigured MMU.
    cpu.ctl_set_tlb_mode(UC_TLB_VIRTUAL)
    cpu.mem_map(ADDRESS & ~0xfff, 0x1000)
    # Unicorn 2.1.4 reg_read/write(XER) touch env->xer only, while QEMU splits
    # CA/OV/SO into separate fields. Use architectural mtxer/mfxer instead.
    # Harness uses r7 for input flags and r6 for output flags; neither is used
    # by the original nine instructions.
    cpu.mem_write(ADDRESS - 4, bytes.fromhex('7ce103a6') + code + bytes.fromhex('7cc102a6'))
    cpu.reg_write(UC_PPC_REG_MSR, 1 << 63)
    rng = random.Random(98472)
    cases = [0, 1, 2, 3, 0x7ffffffe, 0x7fffffff, 0x80000000, 0x80000001,
             0xfffffffe, 0xffffffff, 0x100000000, 0x100000001, 0x7fffffffffffffff,
             0x8000000000000000, MASK]
    cases += [rng.getrandbits(64) for _ in range(args.cases)]
    digest = hashlib.sha256()
    failures = []
    for index, value in enumerate(cases):
        initial_xer = rng.choice([0, 1 << 29, 1 << 30, 1 << 31, 0xe000007f])
        cpu.reg_write(UC_PPC_REG_3, rng.getrandbits(64))
        cpu.reg_write(UC_PPC_REG_5, value)
        cpu.reg_write(UC_PPC_REG_7, initial_xer)
        cpu.reg_write(UC_PPC_REG_LR, ADDRESS + len(code))
        cpu.emu_start(ADDRESS - 4, ADDRESS + len(code) + 4, count=11)
        assert cpu.reg_read(UC_PPC_REG_PC) == ADDRESS + len(code) + 4
        expected = tuple(cpu.reg_read(r) & MASK for r in (UC_PPC_REG_3, UC_PPC_REG_5, UC_PPC_REG_6))
        # Restrict XER comparison to SO, OV, CA and byte count. The default
        # Unicorn CPU also exposes newer ISA CA32/OV32 bits, outside this proof.
        expected = (expected[0], expected[1], expected[2] & 0xe000007f)
        output = (ctypes.c_uint64 * 3)()
        native(value, initial_xer, output)
        actual = tuple(output)
        digest.update(struct.pack('>5Q', value, initial_xer, *expected))
        if actual != expected:
            failures.append({'input_r5': hex(value), 'initial_xer': hex(initial_xer),
                             'oracle': [hex(x) for x in expected], 'native': [hex(x) for x in actual]})
            if len(failures) >= 5:
                break
    report = {'status': 'passed' if not failures else 'failed', 'cases_executed': index + 1,
              'elf_sha256': hashlib.sha256(data).hexdigest(), 'address': hex(ADDRESS),
              'instructions_hex': code.hex(), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'dll_sha256': hashlib.sha256(dll.read_bytes()).hexdigest(), 'compiler': str(args.compiler),
              'oracle': 'Unicorn default PPC64 big-endian, virtual TLB, SF=1; XER initialized/read via mtxer/mfxer', 'unicorn_version': unicorn.__version__,
              'compared': ['r3', 'r5', 'XER SO/OV/CA/byte-count (mask 0xe000007f)'], 'random_seed': 98472, 'case_digest': digest.hexdigest(),
              'failures': failures,
              'limitations': 'Manual translation of one leaf. Oracle is CPU emulation, not PS3 hardware. No game boot, runtime, graphics, audio, SPU or network validation.'}
    (ROOT / 'reports/native-proof.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
