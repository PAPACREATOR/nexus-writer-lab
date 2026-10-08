"""Read PE exports from disk; never load or execute LibreOffice outside LPAC."""
import hashlib
import json
from pathlib import Path
import struct
import sys


def inspect(path):
    raw = path.read_bytes()
    u16 = lambda offset: struct.unpack_from('<H', raw, offset)[0]
    u32 = lambda offset: struct.unpack_from('<I', raw, offset)[0]
    pe = u32(0x3c)
    if raw[pe:pe+4] != b'PE\0\0':
        raise ValueError('Not a PE image')
    opt = pe + 24
    directory = opt + (112 if u16(opt) == 0x20b else 96)
    section_start = opt + u16(pe + 20)
    sections = []
    for index in range(u16(pe + 6)):
        offset = section_start + 40 * index
        sections.append((u32(offset + 12), max(u32(offset + 8), u32(offset + 16)), u32(offset + 20)))
    def position(rva):
        for start, length, disk in sections:
            if start <= rva < start + length:
                return disk + rva - start
        raise ValueError('RVA outside sections')
    export = position(u32(directory))
    count = u32(export + 24)
    names = position(u32(export + 32))
    found = []
    for index in range(count):
        offset = position(u32(names + 4 * index))
        name = raw[offset:raw.index(b'\0', offset)].decode('ascii', errors='replace')
        if 'libreofficekit' in name.lower() or 'lok_preinit' in name.lower():
            found.append(name)
    return {'file': str(path), 'sha256': hashlib.sha256(raw).hexdigest(),
            'export_count': count, 'lok_exports': found, 'binary_executed': False}


if __name__ == '__main__':
    program = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('C:/Program Files/LibreOffice/program')
    results = []
    for name in ('sofficeapp.dll', 'mergedlo.dll'):
        path = program / name
        if path.is_file():
            results.append(inspect(path))
        else:
            results.append({'file': str(path), 'exists': False, 'binary_executed': False})
    print(json.dumps(results, indent=2))
