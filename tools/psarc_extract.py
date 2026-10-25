"""BCUS98472 1.00 PSARC reader/extractor. Reads crypto material from ELF in RAM.

No game keys, payloads or decrypted ELF are part of this source. Requires the
existing project environment (pycryptodome). All game input is opened read-only.
"""
from __future__ import annotations
import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import zlib
from Crypto.Cipher import AES

ELF_SHA256 = 'a9de806aff3c80fb903831dee0a854738b62bfd4090dfbeccc332f49d92609b5'
SPU_VA = 0xB9F980
BLOCK_SIZE = 65536


class FormatError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise FormatError(message)


def read_at(stream, offset, size):
    require(offset >= 0 and size >= 0, 'Negative file range')
    stream.seek(offset)
    data = stream.read(size)
    require(len(data) == size, 'Truncated file range')
    return data


class BlockDecoder:
    """Opaque process-local crypto context; deliberately no serializable key."""
    def __init__(self, key: bytes, prefix: bytes):
        require(len(key) == 32 and len(prefix) == 4, 'Invalid crypto context size')
        self._key = key
        self._prefix = prefix

    @classmethod
    def from_elf(cls, path: Path):
        data = path.read_bytes()
        require(hashlib.sha256(data).hexdigest() == ELF_SHA256,
                'Unsupported ELF: requires exact BCUS98472 disc 1.00 profile (see docs/PSARC.md)')
        require(data[:6] == b'\x7fELF\x02\x02', 'Expected big-endian ELF64')
        phoff = struct.unpack_from('>Q', data, 32)[0]
        stride, count = struct.unpack_from('>HH', data, 54)

        def ppu_read(va, size):
            for i in range(count):
                kind, flags, offset, addr, _, filesz, memsz, align = struct.unpack_from('>II6Q', data, phoff + i * stride)
                if kind == 1 and addr <= va and va + size <= addr + filesz:
                    return data[offset + va - addr:offset + va - addr + size]
            raise FormatError('Crypto profile address not backed by ELF data')

        spu = ppu_read(SPU_VA, 52)
        require(spu[:6] == b'\x7fELF\x01\x02' and struct.unpack_from('>H', spu, 18)[0] == 23,
                'Expected embedded SPU ELF32')
        spu_phoff = struct.unpack_from('>I', spu, 28)[0]
        spu_stride, spu_count = struct.unpack_from('>HH', spu, 42)

        def ls_read(ls, size):
            for i in range(spu_count):
                kind, offset, addr, _, filesz, memsz, flags, align = struct.unpack('>8I', ppu_read(SPU_VA + spu_phoff + i * spu_stride, 32))
                if kind == 1 and addr <= ls and ls + size <= addr + filesz:
                    return ppu_read(SPU_VA + offset + ls - addr, size)
            raise FormatError('Crypto profile LS address not backed by SPU segment')

        require(ls_read(0x114A6, 1) != b'\0', 'ELF profile disables encrypted blocks')
        return cls(ls_read(0x114C0, 32), ls_read(0x114B0, 4))

    def decode(self, raw, expected):
        require(0 < expected <= BLOCK_SIZE, 'Invalid decoded block size')
        # PSARC stores a raw block when compressed storage is not shorter.
        if len(raw) == expected:
            return raw, 'stored'
        require(2 < len(raw) < expected, 'Invalid compressed block length')
        nonce = self._prefix + struct.pack('>I', len(raw)) + b'\0\0' + raw[:2]
        cipher = AES.new(self._key, AES.MODE_CTR, nonce=nonce, initial_value=0)
        compressed = cipher.decrypt(raw[2:])
        decoder = zlib.decompressobj(-15)
        try:
            result = decoder.decompress(compressed, expected + 1)
        except zlib.error:
            raise FormatError('Encrypted deflate block failed to decode') from None
        require(len(result) == expected and decoder.eof
                and not decoder.unconsumed_tail, 'Decoded block length/end mismatch')
        require(decoder.unused_data == struct.pack('>I', zlib.adler32(result)),
                'Missing or mismatched Adler-32 trailer')
        return result, 'aes-256-ctr/raw-deflate'


@dataclass(frozen=True)
class Entry:
    name_hash: bytes
    block_index: int
    size: int
    offset: int


def safe_relative(name: str) -> Path:
    # Leading '/' is a virtual archive root (flags=2), never a host root.
    require(name and not name.startswith('//') and '\\' not in name, 'Unsafe archive path')
    parts = name.removeprefix('/').split('/')
    for part in parts:
        require(part not in ('', '.', '..') and not part.endswith((' ', '.')), 'Unsafe archive path component')
        require(not any(ord(c) < 32 or c in '<>:"|?*' for c in part), 'Invalid Windows path character')
        require(not re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', part, re.I), 'Windows device path')
    return Path(*parts)


class Archive:
    def __init__(self, path: Path, decoder: BlockDecoder):
        self.path, self.decoder = path, decoder
        self.file_size = path.stat().st_size
        with path.open('rb') as stream:
            magic, version, compression, toc_size, stride, count, block_size, flags = struct.unpack('>4sI4s5I', read_at(stream, 0, 32))
            require((magic, version, compression, stride, block_size, flags) == (b'PSAR', 65540, b'zlib', 30, BLOCK_SIZE, 2), 'Unsupported PSARC profile')
            require(1 <= count <= 1_000_000 and 32 + count * stride <= toc_size <= min(self.file_size, 64 * 1024**2), 'Invalid TOC bounds')
            toc = read_at(stream, 32, toc_size - 32)
        self.toc_size, self.flags = toc_size, flags
        self.entries = []
        for i in range(count):
            raw = toc[i * 30:(i + 1) * 30]
            self.entries.append(Entry(raw[:16], int.from_bytes(raw[16:20], 'big'), int.from_bytes(raw[20:25], 'big'), int.from_bytes(raw[25:30], 'big')))
        table = toc[count * stride:]
        require(len(table) % 2 == 0, 'Truncated block-size table')
        self.block_sizes = [int.from_bytes(table[i:i + 2], 'big') or BLOCK_SIZE for i in range(0, len(table), 2)]
        for entry in self.entries:
            n = (entry.size + BLOCK_SIZE - 1) // BLOCK_SIZE
            require(entry.block_index + n <= len(self.block_sizes), 'Entry block index out of range')
            stored = sum(self.block_sizes[entry.block_index:entry.block_index + n])
            require(toc_size <= entry.offset <= self.file_size and entry.offset + stored <= self.file_size, 'Entry data range outside archive')
        require(self.entries[0].size <= 16 * 1024**2, 'Manifest exceeds size limit')
        manifest = b''.join(block for block, kind in self.blocks(self.entries[0]))
        try:
            self.names = manifest.decode('utf-8').splitlines()
        except UnicodeDecodeError:
            raise FormatError('Manifest is not UTF-8') from None
        require(len(self.names) == count - 1, 'Manifest/TOC count mismatch')
        self.manifest_size = len(manifest)
        self.manifest_sha256 = hashlib.sha256(manifest).hexdigest()
        for name, entry in zip(self.names, self.entries[1:]):
            require(hashlib.md5(name.encode('utf-8')).digest() == entry.name_hash, 'Manifest name does not match TOC MD5')

    def blocks(self, entry):
        remaining = entry.size
        index = entry.block_index
        position = entry.offset
        with self.path.open('rb') as stream:
            while remaining:
                size = self.block_sizes[index]
                expected = min(remaining, BLOCK_SIZE)
                raw = read_at(stream, position, size)
                result, kind = self.decoder.decode(raw, expected)
                yield result, kind
                remaining -= expected
                position += size
                index += 1

    def index(self):
        with self.path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        return {'archive': str(self.path.resolve()), 'archive_sha256': digest, 'flags': self.flags,
                'file_count': len(self.names), 'manifest_size': self.manifest_size,
                'manifest_sha256': self.manifest_sha256, 'name_hashes_verified': True,
                'extensions': dict(Counter(Path(n).suffix.lower() for n in self.names)),
                'entries': [dict(path=name, size=e.size, offset=e.offset, block_index=e.block_index,
                                 name_hash=e.name_hash.hex()) for name, e in zip(self.names, self.entries[1:])]}

    def verify_or_extract(self, destination=None):
        root = None
        if destination is not None:
            relative = [safe_relative(name) for name in self.names]
            canonical = [str(p).casefold() for p in relative]
            require(len(canonical) == len(set(canonical)), 'Colliding destination paths')
            all_names = set(canonical)
            require(not any(str(parent).casefold() in all_names for p in relative for parent in p.parents if str(parent) != '.'), 'File/directory collision')
            # Existing output directories are refused; no existing files overwritten.
            destination.mkdir(parents=True, exist_ok=False)
            root = destination.resolve(strict=True)
        result = self.index()
        counts = Counter()
        total = 0
        for i, entry in enumerate(self.entries[1:]):
            output = None
            target = None
            try:
                if root is not None:
                    target = root / relative[i]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    require(target.resolve().is_relative_to(root), 'Extraction escaped destination')
                    # No reparse points in directories created under our fresh root.
                    require(not any(p.is_symlink() or (getattr(p.lstat(), 'st_file_attributes', 0) & 0x400)
                                    for p in [target.parent, *target.parent.parents] if p.is_relative_to(root)), 'Reparse point in extraction path')
                    output = target.open('xb')
                digest = hashlib.sha256()
                length = 0
                for block, kind in self.blocks(entry):
                    digest.update(block)
                    length += len(block)
                    counts[kind] += 1
                    if output:
                        output.write(block)
                require(length == entry.size, 'Entry decoded size mismatch')
                result['entries'][i]['sha256'] = digest.hexdigest()
                total += length
            finally:
                if output:
                    output.close()
        result.update(verified_bytes=total, decoded_blocks=dict(counts), status='verified',
                      extraction_directory=str(root) if root else None)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('index', 'verify', 'extract'))
    parser.add_argument('source', type=Path, help='One PSARC or directory of PSARC files')
    parser.add_argument('--elf', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, help='New directory, extract only')
    args = parser.parse_args()
    if args.command == 'extract' and (not args.output or not args.source.is_file()):
        parser.error('extract requires a single archive and --output')
    if args.command != 'extract' and args.output:
        parser.error('--output is for extract only')
    paths = [args.source] if args.source.is_file() else sorted(args.source.glob('*.psarc'))
    if not paths:
        parser.error('No PSARC files found')
    # Do not permit a report to overwrite any input, even when named without .json.
    require(args.report.resolve() not in [p.resolve() for p in [args.elf, *paths]], 'Report path overlaps input')
    decoder = BlockDecoder.from_elf(args.elf)
    reports = []
    for path in paths:
        try:
            archive = Archive(path, decoder)
            report = archive.index() if args.command == 'index' else archive.verify_or_extract(args.output)
            reports.append(report)
            print(f'{path.name}: {report["file_count"]} files; {report.get("status", "indexed")}', flush=True)
        except (OSError, ValueError, struct.error) as error:
            reports.append({'archive': str(path.resolve()), 'error': str(error)})
            print(f'{path.name}: ERROR {error}', file=sys.stderr, flush=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.report.with_name(args.report.name + '.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(reports, stream, indent=2, ensure_ascii=False)
    os.replace(temporary, args.report)
    raise SystemExit(1 if any('error' in report for report in reports) else 0)


if __name__ == '__main__':
    main()
