"""Independent checks for oracle flags, condition fields, and memory byte order."""
import unittest

import run as d


class OracleChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.elf = (d.ROOT / "work/eboot/EBOOT_1.00_disc.elf").read_bytes()
        if d.sha(cls.elf) != d.ELF_SHA:
            raise ValueError("base ELF identity mismatch")

    def code(self, a, n):
        return self.elf[a-0x10000:a-0x10000+n]

    def test_architectural_xer_roundtrip_and_register_preservation(self):
        # A bare BLR must preserve all inputs, including QEMU's split XER flags.
        oracle = d.Oracle(0x10000, bytes.fromhex("4e800020"))
        for flags in range(8):
            regs, memory = d.inputs(0x2FB804, flags, 98472)
            regs[33] = (flags << 29) | 0x55
            actual = oracle.run(regs, memory)
            self.assertEqual(d.differences((regs, memory), actual), [])

    def test_compare_unsigned_copies_so_and_preserves_other_cr_fields(self):
        a = 0x47E550
        oracle = d.Oracle(a, self.code(a,24))
        for flags in range(8):
            for value, field, answer in ((0,8,1),(2,2,1),(3,4,0),(0x100000001,8,1)):
                regs, memory = d.inputs(a,0,98472)
                regs[4] = value
                regs[32] = 0xABCDEF07
                regs[33] = flags << 29
                output, after = oracle.run(regs,memory)
                self.assertEqual(output[32],0xABCDEF00 | field | (flags >> 2))
                self.assertEqual(output[33], regs[33])
                self.assertEqual(output[3],answer)
                self.assertEqual(after,memory)

    def test_store_is_big_endian_and_does_not_touch_neighbors(self):
        a = 0x11B84
        regs, memory = d.inputs(a,0,98472)
        expected = bytearray(memory)
        expected[0x500:0x504] = b"\0\0\0\1"
        output, after = d.Oracle(a,self.code(a,12)).run(regs,memory)
        self.assertEqual(after,expected)
        self.assertEqual(output[0],1)
        self.assertEqual(output[1:],regs[1:])

    def test_comparison_detects_register_flag_and_last_memory_byte_changes(self):
        regs, memory = d.inputs(0x2FB804,0,98472)
        for index in range(36):
            altered = list(regs)
            altered[index] ^= 1
            self.assertTrue(d.differences((regs,memory),(altered,memory)))
        altered = bytearray(memory)
        altered[-1] ^= 1
        self.assertTrue(d.differences((regs,memory),(regs,altered)))


if __name__ == "__main__":
    unittest.main()
