"""Experimental official LibreOfficeKit call; must execute inside existing LPAC/Job."""
import ctypes as C
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import time

package_root = Path(__file__).absolute().parents[1]
spec = importlib.util.spec_from_file_location('nexus', package_root / '__init__.py', submodule_search_locations=[str(package_root)])
package = importlib.util.module_from_spec(spec)
sys.modules['nexus'] = package
spec.loader.exec_module(package)
from nexus.windows_sandbox import require_native_boundary

start = time.monotonic()


def stage(name, **values):
    record = {'stage': name, 'seconds': time.monotonic() - start, **values}
    with Path('lok-stages.jsonl').open('a', encoding='utf-8') as output:
        output.write(json.dumps(record) + '\n')
    print(json.dumps(record), flush=True)


class OfficeClass(C.Structure):
    _fields_ = [('size', C.c_size_t), ('destroy', C.c_void_p), ('document_load', C.c_void_p), ('get_error', C.c_void_p)]


class Office(C.Structure):
    _fields_ = [('klass', C.POINTER(OfficeClass))]


class DocumentClass(C.Structure):
    _fields_ = [('size', C.c_size_t), ('destroy', C.c_void_p), ('save_as', C.c_void_p)]


class Document(C.Structure):
    _fields_ = [('klass', C.POINTER(DocumentClass))]


def main():
    require_native_boundary()
    stage('native_boundary_verified')
    port = int(sys.argv[2])
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=1):
            stage('network_unexpectedly_allowed')
            return 2
    except OSError as error:
        stage('network_denied', winerror=getattr(error, 'winerror', None), errno=error.errno)
        if getattr(error, 'winerror', None) != 10013:
            return 3  # Refusal/no listener does not prove network denial.
    program = Path(sys.argv[1]).resolve()
    office_dir = Path.cwd() / 'office'
    profile = office_dir / 'profile'
    source = office_dir / 'resultado.odt'
    destination = Path.cwd() / 'resultado.pdf'
    handles = [os.add_dll_directory(str(program))]
    ure = program.parent / 'URE/bin'
    if ure.is_dir(): handles.append(os.add_dll_directory(str(ure)))
    os.environ['PATH'] = str(program) + os.pathsep + os.environ['PATH']
    stage('loading_library', library=str(program / 'mergedlo.dll'))
    library = C.CDLL(str(program / 'mergedlo.dll'))
    init = library.libreofficekit_hook_2
    init.argtypes = [C.c_char_p, C.c_char_p]
    init.restype = C.POINTER(Office)
    stage('initializing_lok', userinstallation=profile.as_uri())
    kit = init(str(program).encode('utf-8'), profile.as_uri().encode('utf-8'))
    if not kit:
        stage('init_failed'); return 4
    klass = kit.contents.klass.contents
    if klass.size < C.sizeof(OfficeClass):
        stage('unsupported_office_abi'); return 5
    stage('lok_initialized')
    load = C.CFUNCTYPE(C.POINTER(Document), C.POINTER(Office), C.c_char_p)(klass.document_load)
    document = load(kit, source.as_uri().encode('utf-8'))
    if not document:
        stage('document_load_failed'); return 6
    docclass = document.contents.klass.contents
    if docclass.size < C.sizeof(DocumentClass):
        stage('unsupported_document_abi'); return 7
    stage('document_loaded')
    save = C.CFUNCTYPE(C.c_int, C.POINTER(Document), C.c_char_p, C.c_char_p, C.c_char_p)(docclass.save_as)
    saved = save(document, destination.as_uri().encode('utf-8'), b'pdf', None)
    stage('pdf_export', result=saved)
    C.CFUNCTYPE(None, C.POINTER(Document))(docclass.destroy)(document)
    stage('document_destroyed')
    C.CFUNCTYPE(None, C.POINTER(Office))(klass.destroy)(kit)
    stage('office_destroyed')
    return 0 if saved else 8


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        stage('exception', type=type(error).__name__, message=str(error))
        raise
