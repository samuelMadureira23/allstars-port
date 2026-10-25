"""Read-only PS3 artifact inventory. Uses only Python's standard library."""
import argparse
import hashlib
import json
import struct
from collections import Counter
from pathlib import Path


def sfo(data):
    magic, version, keys, values, count = struct.unpack_from('<4s4I', data)
    if magic != b'\x00PSF':
        raise ValueError('Not PARAM.SFO')
    result = {}
    for i in range(count):
        key, fmt, length, maximum, offset = struct.unpack_from('<HHIII', data, 20 + i * 16)
        name = data[keys + key:].split(b'\0', 1)[0].decode('utf-8')
        raw = data[values + offset:values + offset + length]
        result[name] = (int.from_bytes(raw, 'little') if fmt == 0x404
                        else raw.rstrip(b'\0').decode('utf-8', errors='replace') if fmt == 0x204
                        else raw.hex())
    return result


def inspect(path):
    with path.open('rb') as stream:
        data = stream.read(4096)
    result = {'size': path.stat().st_size, 'magic_hex': data[:16].hex()}
    if data[:4] == b'SCE\0':
        fields = struct.unpack_from('>4sIHHIQQ', data)
        result['sce_header'] = dict(zip(
            ['version', 'flags', 'type', 'metadata_offset', 'header_length', 'data_length'], fields[1:]))
        # These offsets describe embedded ELF metadata, not decrypted executable bytes.
        if len(data) >= 112 and fields[3] == 1:
            offsets = struct.unpack_from('>10Q', data, 32)
            result['self_header'] = dict(zip(['header_type', 'app_info_offset', 'elf_offset',
                'program_headers_offset', 'section_headers_offset', 'section_info_offset',
                'version_info_offset', 'control_info_offset', 'control_info_size', 'padding'], offsets))
            elf_offset = offsets[2]
            with path.open('rb') as stream:
                stream.seek(elf_offset)
                elf = stream.read(64)
            if elf[:4] == b'\x7fELF':
                result['embedded_elf'] = elf_header(elf)
    elif data[:4] == b'\x7fELF':
        result['elf'] = elf_header(data)
    elif data[:4] == b'PSAR':
        fields = struct.unpack_from('>4sI4s5I', data)
        result['psarc_header'] = dict(zip(['version', 'compression', 'toc_length',
            'entry_size', 'entry_count', 'block_size', 'flags'], fields[1:]))
        result['psarc_header']['compression'] = fields[2].decode('ascii', errors='replace')
    return result


def elf_header(data):
    endian = '>' if data[5] == 2 else '<'
    fmt = endian + ('HHIQQQIHHHHHH' if data[4] == 2 else 'HHIIIIIHHHHHH')
    fields = struct.unpack_from(fmt, data, 16)
    return {'class_bits': 64 if data[4] == 2 else 32, 'endianness': 'big' if data[5] == 2 else 'little',
            **dict(zip(['type', 'machine', 'version', 'entry', 'phoff', 'shoff', 'flags',
                        'ehsize', 'phentsize', 'phnum', 'shentsize', 'shnum', 'shstrndx'], fields))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    root = args.source.resolve(strict=True)
    files = sorted(p for p in root.rglob('*') if p.is_file())
    records = [{'path': p.relative_to(root).as_posix(), 'size': p.stat().st_size} for p in files]
    selected = [p for p in files if p.suffix.lower() in ('.bin', '.self', '.sprx', '.elf', '.psarc')]
    details = {p.relative_to(root).as_posix(): inspect(p) for p in selected}
    for p in selected:
        if p.name == 'EBOOT.BIN':
            with p.open('rb') as stream:
                details[p.relative_to(root).as_posix()]['sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
    report = {'source': str(root), 'method': 'Python static file/header reads; not REA evidence; no target execution',
              'file_count': len(files), 'total_bytes': sum(r['size'] for r in records),
              'extensions': dict(Counter(p.suffix.lower() for p in files)),
              'param_sfo': sfo((root / 'PS3_GAME' / 'PARAM.SFO').read_bytes()),
              'artifacts': details, 'files': records}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('file_count', 'total_bytes', 'extensions', 'param_sfo')}, indent=2, ensure_ascii=False))
    print(json.dumps(details.get('PS3_GAME/USRDIR/EBOOT.BIN'), indent=2))


if __name__ == '__main__':
    main()
