"""Read-only SAL path checks in the original native boundary; never start Writer.

The SAL string and directory handles belong only to this diagnostic process.
No debugger, process-memory reader, bootstrap override, or ACL API is used.
Signatures/layout: LibreOffice libreoffice-26.2.6.2 include/rtl/ustring.h and
include/osl/file.h; the Windows lookup is sal/osl/w32/file_dirvol.cxx:875-989.
"""
import ctypes as C
from ctypes import wintypes as W
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import time


def emit(stage, **values):
    print(json.dumps({'stage': stage, **values}), flush=True)


def load_boundary_check(package_root):
    # Match the existing isolated helper's direct package loading. No parent
    # directory enumeration or extra read root is needed for Python imports.
    package_root = Path(package_root)
    if not package_root.is_absolute() or package_root.name != 'nexus':
        raise ValueError('Expected the absolute original Nexus package root')
    spec = importlib.util.spec_from_file_location(
        'nexus', package_root / '__init__.py',
        submodule_search_locations=[str(package_root)])
    package = importlib.util.module_from_spec(spec)
    sys.modules['nexus'] = package
    spec.loader.exec_module(package)
    from nexus.windows_sandbox import require_native_boundary
    require_native_boundary()


class SalPaths:
    def __init__(self, library):
        self.library = library
        library.rtl_uString_newFromStr_WithLength.argtypes = [
            C.POINTER(C.c_void_p), C.POINTER(C.c_uint16), C.c_int32]
        library.rtl_uString_newFromStr_WithLength.restype = None
        library.rtl_uString_release.argtypes = [C.c_void_p]
        library.rtl_uString_release.restype = None
        library.osl_getDirectoryItem.argtypes = [C.c_void_p, C.POINTER(C.c_void_p)]
        library.osl_getDirectoryItem.restype = C.c_int
        library.osl_releaseDirectoryItem.argtypes = [C.c_void_p]
        library.osl_releaseDirectoryItem.restype = C.c_int

    def get(self, uri):
        raw = uri.encode('utf-16-le')
        if not raw or len(raw) > 65534 or '\x00' in uri:
            raise ValueError('Invalid bounded diagnostic URI')
        units = (C.c_uint16 * (len(raw) // 2)).from_buffer_copy(raw)
        text, item = C.c_void_p(), C.c_void_p()
        record = {'api': 'osl_getDirectoryItem', 'uri': uri}
        try:
            self.library.rtl_uString_newFromStr_WithLength(
                C.byref(text), units, len(units))
            if not text.value:
                raise RuntimeError('SAL did not allocate the diagnostic string')
            code = self.library.osl_getDirectoryItem(text, C.byref(item))
            record.update(osl_error=code, item_returned=bool(item.value))
            record['osl_error_name'] = {
                0: 'osl_File_E_None', 2: 'osl_File_E_NOENT',
                13: 'osl_File_E_ACCES', 19: 'osl_File_E_NOTDIR',
                21: 'osl_File_E_INVAL',
            }.get(code, 'other_osl_error')
            return record
        finally:
            if item.value:
                record['release_osl_error'] = self.library.osl_releaseDirectoryItem(item)
            if text.value:
                self.library.rtl_uString_release(text)


def attributes(kernel, path):
    C.set_last_error(0)
    value = kernel.GetFileAttributesW(str(path))
    result = {'api': 'GetFileAttributesW', 'path': str(path), 'attributes': value}
    if value == 0xffffffff:
        result.update(ok=False, winerror=C.get_last_error())
    else:
        result.update(ok=True, is_directory=bool(value & 0x10))
    return result


def main():
    if os.name != 'nt' or C.sizeof(C.c_void_p) != 8:
        raise RuntimeError('This diagnostic requires 64-bit Windows')
    if len(sys.argv) != 5:
        raise ValueError('Expected Office root, synthetic profile, listener port and Nexus package root')
    load_boundary_check(sys.argv[4])
    emit('native_boundary_verified', writer_executed=False, acl_changes=False,
         process_memory_read=False)
    office, profile = Path(sys.argv[1]), Path(sys.argv[2])
    if not office.is_absolute() or not profile.is_absolute():
        raise ValueError('Only absolute diagnostic paths are accepted')
    try:
        with socket.create_connection(('127.0.0.1', int(sys.argv[3])), timeout=1):
            emit('network_unexpectedly_allowed')
            return 2
    except OSError as error:
        denied = getattr(error, 'winerror', None) == 10013
        emit('network_check', denied=denied,
             winerror=getattr(error, 'winerror', None), errno=error.errno)
        if not denied:
            return 3
    kernel = C.WinDLL('kernel32', use_last_error=True)
    kernel.GetFileAttributesW.argtypes = [W.LPCWSTR]
    kernel.GetFileAttributesW.restype = W.DWORD
    program = office / 'program'
    # Only this known SAL image is loaded. It does not start an office instance.
    with os.add_dll_directory(str(program)):
        emit('loading_sal', library=str(program / 'sal3.dll'))
        sal = SalPaths(C.CDLL(str(program / 'sal3.dll')))
        targets = [
            ('office_root', office.as_uri()),
            ('office_root_trailing_slash', office.as_uri() + '/'),
            ('program_directory', program.as_uri()),
            ('soffice_ini', (program / 'soffice.ini').as_uri()),
            ('bootstrap_ini', (program / 'bootstrap.ini').as_uri()),
            ('synthetic_profile', profile.as_uri()),
        ]
        for name, uri in targets:
            emit('sal_path', name=name, **sal.get(uri))
        for name, path in [('office_root', office), ('program_directory', program),
                           ('synthetic_profile', profile)]:
            emit('win32_attributes', name=name, **attributes(kernel, path))
    emit('probe_complete', writer_executed=False, bootstrap_overrides=False,
         acl_changes=False, process_memory_read=False, product_routes_validated=False)
    return 0


if __name__ == '__main__':
    started = time.monotonic()
    try:
        raise SystemExit(main())
    except Exception as error:
        emit('exception', type=type(error).__name__, message=str(error),
             seconds=time.monotonic() - started)
        raise SystemExit(1)
