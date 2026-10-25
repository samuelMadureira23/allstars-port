// Offline, bounded memory adapter. Game functions/helpers are extracted unchanged.
#include "ppu_recomp.h"
#include <cstring>
#include <stdexcept>
#include "selection.h"

static uint8_t* memory;
static size_t offset(uint64_t a, unsigned n) {
    if (a >= 0x1000000 && a - 0x1000000 <= 4096 - n)
        return (size_t)(a - 0x1000000);
    if (a >= 0xc7c000 && a - 0xc7c000 <= 4096 - n)
        return (size_t)(a - 0xc7c000 + 4096);
    throw std::out_of_range("guest memory");
}
static uint64_t read_be(uint64_t a, unsigned n) {
    size_t p = offset(a, n); uint64_t v = 0;
    for (unsigned i = 0; i < n; ++i) v = (v << 8) | memory[p+i];
    return v;
}
static void write_be(uint64_t a, uint64_t v, unsigned n) {
    size_t p = offset(a, n);
    for (unsigned i = 0; i < n; ++i) memory[p+n-1-i] = (uint8_t)(v >> (i*8));
}
extern "C" {
uint8_t vm_read8(uint64_t a) { return (uint8_t)read_be(a, 1); }
uint16_t vm_read16(uint64_t a) { return (uint16_t)read_be(a, 2); }
uint32_t vm_read32(uint64_t a) { return (uint32_t)read_be(a, 4); }
uint64_t vm_read64(uint64_t a) { return read_be(a, 8); }
void vm_write8(uint64_t a, uint8_t v) { write_be(a, v, 1); }
void vm_write16(uint64_t a, uint16_t v) { write_be(a, v, 2); }
void vm_write32(uint64_t a, uint32_t v) { write_be(a, v, 4); }
void vm_write64(uint64_t a, uint64_t v) { write_be(a, v, 8); }

// Flat ABI avoids ctypes assumptions about the aligned ppu_context structure.
// regs = GPR[32], CR, XER, LR, CTR; memory = two 4096-byte regions.
__declspec(dllexport) int run_case(unsigned index, uint64_t* regs, uint8_t* bytes,
                                  int inject_fault) {
    if (index >= sizeof(selected)/sizeof(selected[0])) return 2;
    ppu_context c = {};
    memcpy(c.gpr, regs, sizeof(c.gpr));
    c.cr = (uint32_t)regs[32]; c.xer = (uint32_t)regs[33];
    c.lr = regs[34]; c.ctr = regs[35]; memory = bytes;
    try { selected[index](&c); }
    catch (const std::out_of_range&) { return 1; }
    if (inject_fault) c.gpr[3] ^= 1; // negative control, never changes generated code
    memcpy(regs, c.gpr, sizeof(c.gpr));
    regs[32] = c.cr; regs[33] = c.xer; regs[34] = c.lr; regs[35] = c.ctr;
    return 0;
}
}
