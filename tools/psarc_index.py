"""Index PSARC v1.4 zlib archives without extracting game resources.

Reads the TOC and decompresses only the filename manifest (entry zero).
Format reference: https://github.com/GaticusHax/libPSARC/wiki/Documentation-libPSARC-PSARC-File-Format
"""
import argparse
import json
import struct
import zlib
from collections import Counter
from pathlib import Path


def index(path):
    size = path.stat().st_size
    with path.open('rb') as stream:
        magic, version, compression, toc_size, stride, count, block_size, flags = struct.unpack('>4sI4s5I', stream.read(32))
        if (magic, version, compression, stride, block_size) != (b'PSAR', 65540, b'zlib', 30, 65536):
            raise ValueError('Unsupported PSARC profile')
        if flags & 4 or not 32 + count * stride <= toc_size <= min(size, 64 * 1024 * 1024):
            raise ValueError('Encrypted or invalid TOC')
        toc = stream.read(toc_size - 32)
        entries = []
        for i in range(count):
            raw = toc[i * stride:(i + 1) * stride]
            entries.append({'name_hash': raw[:16].hex(), 'block_index': int.from_bytes(raw[16:20], 'big'),
                            'size': int.from_bytes(raw[20:25], 'big'), 'offset': int.from_bytes(raw[25:30], 'big')})
        blocks = toc[count * stride:]
        if len(blocks) % 2 or not entries:
            raise ValueError('Invalid block table')
        first = entries[0]
        if first['size'] > 16 * 1024 * 1024:
            raise ValueError('Manifest too large')
        stream.seek(first['offset'])
        remaining = first['size']
        manifest = bytearray()
        block_index = first['block_index']
        while remaining:
            if block_index * 2 + 2 > len(blocks):
                raise ValueError('Block index out of bounds')
            stored = int.from_bytes(blocks[block_index * 2:block_index * 2 + 2], 'big') or block_size
            expected = min(remaining, block_size)
            raw = stream.read(stored)
            if len(raw) != stored:
                raise ValueError('Truncated block')
            if stored == expected:
                decoded = raw
            else:
                decoder = zlib.decompressobj()
                try:
                    decoded = decoder.decompress(raw, expected + 1)
                except zlib.error as error:
                    return {'archive': str(path), 'flags': flags, 'toc_file_count': count - 1,
                            'manifest_error': str(error), 'manifest_first_bytes': raw[:16].hex(),
                            'note': 'TOC only; names and payloads not decoded. No encryption algorithm inferred.',
                            'entries': entries[1:]}
                if not decoder.eof or decoder.unconsumed_tail or decoder.unused_data:
                    raise ValueError('Invalid compressed manifest block')
            if len(decoded) != expected:
                raise ValueError('Manifest block size mismatch')
            manifest.extend(decoded)
            remaining -= expected
            block_index += 1
        names = manifest.decode('utf-8').splitlines()
        if len(names) != count - 1:
            raise ValueError(f'Manifest count mismatch: {len(names)} versus {count - 1}')
        for entry, name in zip(entries[1:], names):
            entry['path'] = name
            if not toc_size <= entry['offset'] <= size:
                raise ValueError('Entry offset out of bounds')
        return {'archive': str(path), 'flags': flags, 'file_count': len(names),
                'extensions': dict(Counter(Path(n).suffix.lower() for n in names)), 'entries': entries[1:]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    results = []
    for path in sorted(args.directory.glob('*.psarc')):
        try:
            results.append(index(path))
        except (ValueError, OSError, struct.error, zlib.error) as error:
            results.append({'archive': str(path), 'error': str(error)})
    args.output.write_text(json.dumps(results, indent=2), encoding='utf-8')
    print(json.dumps({'archives': len(results), 'indexed_files': sum(r.get('file_count', 0) for r in results),
                      'toc_files': sum(r.get('toc_file_count', r.get('file_count', 0)) for r in results),
                      'undecoded_manifests': sum('manifest_error' in r for r in results),
                      'errors': [r for r in results if 'error' in r]}, indent=2))
