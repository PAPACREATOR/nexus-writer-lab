"""Read only on-disk CodeView build identifiers of the installed test fixture."""
import hashlib
import json
import os
from pathlib import Path
import struct
import uuid


def codeview(path):
    data = path.read_bytes()
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    if data[:2] != b'MZ' or data[pe:pe+4] != b'PE\0\0':
        raise ValueError('Not a PE image')
    count = struct.unpack_from('<H', data, pe+6)[0]
    optional_size = struct.unpack_from('<H', data, pe+20)[0]
    optional = pe+24
    magic = struct.unpack_from('<H', data, optional)[0]
    directory = optional + {0x20b:112, 0x10b:96}[magic]
    debug_rva, debug_size = struct.unpack_from('<II', data, directory+6*8)
    sections = []
    for i in range(count):
        entry = optional + optional_size + i*40
        virtual_size, rva, raw_size, raw_offset = struct.unpack_from('<IIII', data, entry+8)
        sections.append((rva, max(virtual_size,raw_size),raw_offset))
    def offset(rva):
        for start, size, raw in sections:
            if start <= rva < start+size:
                return raw+rva-start
        raise ValueError('Unmapped RVA')
    records = []
    if debug_rva and debug_size:
        debug_offset = offset(debug_rva)
        for i in range(debug_size//28):
            fields = struct.unpack_from('<IIHHIIII',data,debug_offset+i*28)
            kind,size,ptr = fields[4],fields[5],fields[7]
            cv = data[ptr:ptr+size]
            if kind == 2 and cv[:4] == b'RSDS' and len(cv)>=25:
                guid=uuid.UUID(bytes_le=cv[4:20])
                age=struct.unpack_from('<I',cv,20)[0]
                pdb_path=cv[24:].split(b'\0',1)[0].decode('utf-8',errors='replace')
                pdb_name=pdb_path.replace('\\','/').split('/')[-1]
                records.append({'guid':str(guid),'age':age,'key':guid.hex.upper()+format(age,'X'),'pdb_name':pdb_name,'embedded_build_path':pdb_path})
    return {'image':path.name,'sha256':hashlib.sha256(data).hexdigest(),'codeview':records}


if __name__ == '__main__':
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('Disposable GitHub runner only')
    program=Path(os.environ['LIBREOFFICE_EXE']).resolve().parent
    results=[]
    for name in ('mergedlo.dll','vclplug_winlo.dll','sal3.dll','soffice.bin'):
        try: results.append(codeview(program/name))
        except Exception as error: results.append({'image':name,'error':str(error)})
    output=Path('lab-evidence/pe-debug-info.json')
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(results,indent=2),encoding='utf-8')
