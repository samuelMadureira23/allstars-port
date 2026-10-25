"""Synthetic fixtures exercise the reader without distributing game data."""
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from psarc_index import index


class ArchiveTests(unittest.TestCase):
    def fixture(self, compressed):
        manifest = b'assets/example.texture\n'
        payload = zlib.compress(manifest) if compressed else manifest
        toc_size = 32 + 60 + 4
        def entry(block, length, offset):
            return bytes(16) + struct.pack('>I', block) + length.to_bytes(5, 'big') + offset.to_bytes(5, 'big')
        return (struct.pack('>4sI4s5I', b'PSAR', 65540, b'zlib', toc_size, 30, 2, 65536, 2)
                + entry(0, len(manifest), toc_size) + entry(1, 1, toc_size + len(payload))
                + struct.pack('>HH', len(payload), 1) + payload + b'x')

    def check_archive(self, compressed):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.psarc'
            path.write_bytes(self.fixture(compressed))
            result = index(path)
            self.assertEqual(result['file_count'], 1)
            self.assertEqual(result['entries'][0]['path'], 'assets/example.texture')

    def test_compressed_manifest(self):
        self.check_archive(True)

    def test_raw_manifest(self):
        self.check_archive(False)

    def test_invalid_toc_bounds(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'fixture.psarc'
            data = bytearray(self.fixture(False))
            struct.pack_into('>I', data, 12, 0xffffffff)
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                index(path)


if __name__ == '__main__':
    unittest.main()
