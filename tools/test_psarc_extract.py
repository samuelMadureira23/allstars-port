"""Generated fixtures only: the key below is dummy bytes, not game material."""
import hashlib
from pathlib import Path
import random
import struct
import tempfile
import unittest
import zlib
from Crypto.Cipher import AES
from psarc_extract import Archive, BlockDecoder, FormatError, safe_relative

DUMMY_KEY = bytes(range(32))
DUMMY_PREFIX = b'TEST'


def encrypted_block(data, corrupt_adler=False):
    raw = zlib.compress(data)[2:]
    if corrupt_adler:
        raw = raw[:-1] + bytes([raw[-1] ^ 1])
    header = b'\x12\x34'
    nonce = DUMMY_PREFIX + struct.pack('>I', len(raw) + 2) + b'\0\0' + header
    return header + AES.new(DUMMY_KEY, AES.MODE_CTR, nonce=nonce, initial_value=0).encrypt(raw)


def fixture(path, files):
    manifest = ('\n'.join(name for name, data in files)).encode()
    entries, blocks, sizes = [], [], []
    for name, data in [('', manifest), *files]:
        first = len(sizes)
        pieces = []
        for offset in range(0, len(data), 65536):
            plain = data[offset:offset + 65536]
            encoded = encrypted_block(plain)
            if len(encoded) >= len(plain):
                encoded = plain
            pieces.append(encoded)
            sizes.append(len(encoded) % 65536)
        payload = b''.join(pieces)
        entries.append((name, first, len(data), len(payload)))
        blocks.append(payload)
    toc_size = 32 + len(entries) * 30 + len(sizes) * 2
    toc = bytearray()
    position = toc_size
    for name, first, size, length in entries:
        toc.extend(hashlib.md5(name.encode()).digest() if name else bytes(16))
        toc.extend(struct.pack('>I', first) + size.to_bytes(5, 'big') + position.to_bytes(5, 'big'))
        position += length
    toc.extend(b''.join(struct.pack('>H', n) for n in sizes))
    path.write_bytes(struct.pack('>4sI4s5I', b'PSAR', 65540, b'zlib', toc_size, 30,
                                 len(entries), 65536, 2) + toc + b''.join(blocks))


class ExtractorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.decoder = BlockDecoder(DUMMY_KEY, DUMMY_PREFIX)
        self.path = self.root / 'fixture.psarc'

    def tearDown(self):
        self.temp.cleanup()

    def test_multi_block_and_stored_and_empty_round_trip(self):
        files = [('/compressed.bin', b'hello world' * 20000),
                 ('/raw/full.bin', random.Random(5).randbytes(65536)),
                 ('/raw/short.bin', bytes(range(255))), ('/empty.bin', b'')]
        fixture(self.path, files)
        archive = Archive(self.path, self.decoder)
        report = archive.verify_or_extract(self.root / 'output')
        self.assertEqual(report['verified_bytes'], sum(len(data) for _, data in files))
        self.assertGreater(report['decoded_blocks']['stored'], 0)
        self.assertGreater(report['decoded_blocks']['aes-256-ctr/raw-deflate'], 0)
        for name, data in files:
            self.assertEqual((self.root / 'output' / name.lstrip('/')).read_bytes(), data)

    def test_bad_adler_rejected(self):
        with self.assertRaisesRegex(FormatError, 'Adler'):
            self.decoder.decode(encrypted_block(b'x' * 1000, True), 1000)

    def test_wrong_key_rejected(self):
        with self.assertRaises(FormatError):
            BlockDecoder(bytes(32), DUMMY_PREFIX).decode(encrypted_block(b'x' * 1000), 1000)

    def test_expansion_beyond_declared_size_rejected(self):
        with self.assertRaises(FormatError):
            self.decoder.decode(encrypted_block(b'x' * 10000), 1000)

    def test_truncated_archive_rejected(self):
        fixture(self.path, [('/file', b'hello' * 500)])
        self.path.write_bytes(self.path.read_bytes()[:-1])
        with self.assertRaises(FormatError):
            Archive(self.path, self.decoder)

    def test_bad_block_index_rejected(self):
        fixture(self.path, [('/file', b'hello' * 500)])
        data = bytearray(self.path.read_bytes())
        struct.pack_into('>I', data, 32 + 30 + 16, 0xffffffff)
        self.path.write_bytes(data)
        with self.assertRaisesRegex(FormatError, 'block index'):
            Archive(self.path, self.decoder)

    def test_name_hash_mismatch_rejected(self):
        fixture(self.path, [('/file', b'hello' * 500)])
        data = bytearray(self.path.read_bytes())
        data[62] ^= 1
        self.path.write_bytes(data)
        with self.assertRaisesRegex(FormatError, 'MD5'):
            Archive(self.path, self.decoder)

    def test_unsafe_paths_rejected_before_writes(self):
        for name in ('/../escape', 'C:/escape', '//server/share', '/dir/../escape',
                     '/dir\\escape', '/CON.txt', '/x:stream', '/trailing.', '/x//y'):
            with self.subTest(name=name):
                fixture(self.path, [(name, b'abc')])
                with self.assertRaises(FormatError):
                    Archive(self.path, self.decoder).verify_or_extract(self.root / 'unsafe')
                self.assertFalse((self.root / 'unsafe').exists())

    def test_virtual_absolute_path_is_relative(self):
        self.assertEqual(safe_relative('/text/bra/file.bcsv'), Path('text/bra/file.bcsv'))

    def test_case_collisions_rejected(self):
        fixture(self.path, [('/A', b'a'), ('/a', b'b')])
        with self.assertRaisesRegex(FormatError, 'Colliding'):
            Archive(self.path, self.decoder).verify_or_extract(self.root / 'out')

    def test_file_directory_collision_rejected(self):
        fixture(self.path, [('/a', b'a'), ('/a/b', b'b')])
        with self.assertRaisesRegex(FormatError, 'File/directory'):
            Archive(self.path, self.decoder).verify_or_extract(self.root / 'out')

    def test_existing_output_preserved(self):
        fixture(self.path, [('/marker', b'new')])
        target = self.root / 'out'
        target.mkdir()
        (target / 'marker').write_bytes(b'old')
        with self.assertRaises(FileExistsError):
            Archive(self.path, self.decoder).verify_or_extract(target)
        self.assertEqual((target / 'marker').read_bytes(), b'old')

    def test_wrong_elf_profile_rejected(self):
        wrong = self.root / 'wrong.elf'
        wrong.write_bytes(b'not the game')
        with self.assertRaisesRegex(FormatError, 'Unsupported ELF'):
            BlockDecoder.from_elf(wrong)


if __name__ == '__main__':
    unittest.main()
