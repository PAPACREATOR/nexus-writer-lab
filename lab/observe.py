"""Read-only sampling of the existing native job, without attaching a debugger."""
import ctypes as C
from ctypes import wintypes as W
import threading
import time


def lpac_accesscheck(process_handle):
    """Evaluate an in-memory descriptor; never grant access to an OS object.

    Chromium's CheckLpacToken uses the same three ACEs and access masks:
    https://github.com/chromium/chromium/blob/main/sandbox/win/src/app_container_test.cc
    The duplicated token is used only for AccessCheck, never impersonated or
    assigned to a process/thread. Class-46 query results remain independent.
    """
    sddl = 'O:SYG:SYD:(A;;0x3;;;WD)(A;;0x1;;;S-1-15-2-1)(A;;0x2;;;S-1-15-2-2)'
    result = {'method': 'synthetic_descriptor_accesscheck', 'descriptor_sddl': sddl,
              'desired_access': 0x02000000, 'expected_lpac_granted_access': 2,
              'api_ok': False, 'lpac': None, 'classification': 'api_error'}
    a = C.WinDLL('advapi32', use_last_error=True)
    k = C.WinDLL('kernel32', use_last_error=True)
    a.OpenProcessToken.argtypes = [W.HANDLE, W.DWORD, C.POINTER(W.HANDLE)]
    a.OpenProcessToken.restype = W.BOOL
    a.DuplicateTokenEx.argtypes = [W.HANDLE, W.DWORD, C.c_void_p, C.c_int, C.c_int, C.POINTER(W.HANDLE)]
    a.DuplicateTokenEx.restype = W.BOOL
    a.GetTokenInformation.argtypes = [W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.POINTER(W.DWORD)]
    a.GetTokenInformation.restype = W.BOOL
    a.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [W.LPCWSTR, W.DWORD, C.POINTER(C.c_void_p), C.POINTER(W.DWORD)]
    a.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = W.BOOL
    class GenericMapping(C.Structure):
        _fields_ = [('read', W.DWORD), ('write', W.DWORD), ('execute', W.DWORD), ('all', W.DWORD)]
    a.AccessCheck.argtypes = [C.c_void_p, W.HANDLE, W.DWORD, C.POINTER(GenericMapping),
                            C.c_void_p, C.POINTER(W.DWORD), C.POINTER(W.DWORD), C.POINTER(W.BOOL)]
    a.AccessCheck.restype = W.BOOL
    k.CloseHandle.argtypes = [W.HANDLE]
    k.CloseHandle.restype = W.BOOL
    k.LocalFree.argtypes = [C.c_void_p]
    k.LocalFree.restype = C.c_void_p
    primary, duplicate, descriptor = W.HANDLE(), W.HANDLE(), C.c_void_p()
    stage = 'OpenProcessToken(TOKEN_DUPLICATE)'
    try:
        if not a.OpenProcessToken(process_handle, 0x0002, C.byref(primary)):
            result.update(stage=stage, winerror=C.get_last_error()); return result
        stage = 'DuplicateTokenEx(SecurityIdentification,TOKEN_QUERY)'
        # Identification-level impersonation token, matching Chromium. No
        # TOKEN_IMPERSONATE right and no Impersonate*/SetThreadToken API call.
        if not a.DuplicateTokenEx(primary, 0x0008, None, 1, 2, C.byref(duplicate)):
            result.update(stage=stage, winerror=C.get_last_error()); return result
        stage = 'GetTokenInformation(TokenIsAppContainer)'
        contained, length = W.DWORD(), W.DWORD()
        if not a.GetTokenInformation(duplicate, 29, C.byref(contained), C.sizeof(contained), C.byref(length)):
            result.update(stage=stage, winerror=C.get_last_error()); return result
        result['appcontainer'] = bool(contained.value)
        stage = 'ConvertStringSecurityDescriptorToSecurityDescriptorW'
        if not a.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl, 1, C.byref(descriptor), None):
            result.update(stage=stage, winerror=C.get_last_error()); return result
        stage = 'AccessCheck'
        mapping, granted, status = GenericMapping(), W.DWORD(), W.BOOL()
        privileges = C.create_string_buffer(256)
        length = W.DWORD(C.sizeof(privileges))
        ok = a.AccessCheck(descriptor, duplicate, 0x02000000, C.byref(mapping), privileges,
                           C.byref(length), C.byref(granted), C.byref(status))
        if not ok and C.get_last_error() == 122 and 0 < length.value <= 65536:
            privileges = C.create_string_buffer(length.value)
            ok = a.AccessCheck(descriptor, duplicate, 0x02000000, C.byref(mapping), privileges,
                               C.byref(length), C.byref(granted), C.byref(status))
        if not ok:
            result.update(stage=stage, winerror=C.get_last_error()); return result
        result.update(api_ok=True, access_status=bool(status.value), granted_access=granted.value,
                      privilege_set_length=length.value)
        if not contained.value:
            result.update(lpac=False, classification='non_lpac')
        elif status.value and granted.value == 2:
            result.update(lpac=True, classification='lpac')
        elif status.value and granted.value & 1:
            result.update(lpac=False, classification='non_lpac')
        else:
            # A denial or an unexpected restricted-token result cannot establish
            # absence of LPAC. It remains an inconclusive observation.
            result.update(classification='inconclusive')
        return result
    finally:
        if descriptor: k.LocalFree(descriptor)
        if duplicate: k.CloseHandle(duplicate)
        if primary: k.CloseHandle(primary)


class ENTRY(C.Structure):
    _fields_ = [('size', W.DWORD), ('usage', W.DWORD), ('pid', W.DWORD),
               ('heap', C.c_size_t), ('module', W.DWORD), ('threads', W.DWORD),
               ('parent', W.DWORD), ('priority', W.LONG), ('flags', W.DWORD),
               ('name', W.WCHAR * 260)]


class Observer:
    def __init__(self, worker):
        self.worker = worker
        self.events = []
        self.stop = threading.Event()
        self.start = time.monotonic()
        self.known = {worker.pid}
        self.seen = set()
        self.errors = []
        self.thread = threading.Thread(target=self.sample, daemon=True)
        self.thread.start()

    def sample(self):
        k = C.WinDLL('kernel32', use_last_error=True)
        k.CreateToolhelp32Snapshot.argtypes = [W.DWORD, W.DWORD]
        k.CreateToolhelp32Snapshot.restype = W.HANDLE
        k.Process32FirstW.argtypes = k.Process32NextW.argtypes = [W.HANDLE, C.POINTER(ENTRY)]
        k.OpenProcess.argtypes = [W.DWORD, W.BOOL, W.DWORD]
        k.OpenProcess.restype = W.HANDLE
        k.CloseHandle.argtypes = [W.HANDLE]
        a = self.worker.api
        while not self.stop.is_set():
            snapshot = k.CreateToolhelp32Snapshot(2, 0)
            if snapshot == C.c_void_p(-1).value:
                self.errors.append({'snapshot_error': C.get_last_error()})
                return
            rows = []
            try:
                e = ENTRY(); e.size = C.sizeof(e)
                ok = k.Process32FirstW(snapshot, C.byref(e))
                while ok:
                    rows.append({'pid': e.pid, 'parent_pid': e.parent, 'name': e.name})
                    ok = k.Process32NextW(snapshot, C.byref(e))
            finally:
                k.CloseHandle(snapshot)
            changed = True
            while changed:
                changed = False
                for row in rows:
                    if row['parent_pid'] in self.known and row['pid'] not in self.known:
                        self.known.add(row['pid']); changed = True
            for row in rows:
                if row['pid'] not in self.known or row['pid'] in self.seen:
                    continue
                self.seen.add(row['pid'])
                row['seconds'] = time.monotonic() - self.start
                handle = k.OpenProcess(0x1000, False, row['pid'])
                if not handle:
                    row['query_error'] = C.get_last_error()
                else:
                    try:
                        try:
                            row['lpac_accesscheck'] = lpac_accesscheck(handle)
                        except Exception as error:
                            row['lpac_accesscheck'] = {'method': 'synthetic_descriptor_accesscheck',
                                'api_ok': False, 'lpac': None, 'classification': 'api_error',
                                'reader_error': str(error)}
                        token, length, contained, job, elevated = a.H(), a.D(), a.D(), a.D(), a.D()
                        if a.a.OpenProcessToken(handle, 8, C.byref(token)):
                            try:
                                if a.a.GetTokenInformation(token, 29, C.byref(contained), C.sizeof(contained), C.byref(length)):
                                    row['appcontainer'] = bool(contained.value)
                                if a.a.GetTokenInformation(token, 20, C.byref(elevated), C.sizeof(elevated), C.byref(length)):
                                    row['elevated'] = bool(elevated.value)
                                lpac = a.D()
                                if a.a.GetTokenInformation(token, 46, C.byref(lpac), C.sizeof(lpac), C.byref(length)):
                                    row['lpac'] = bool(lpac.value)
                                else:
                                    row['lpac_query_error'] = C.get_last_error()
                                    native = C.WinDLL('ntdll')
                                    native.NtQueryInformationToken.argtypes = [a.H, C.c_int, a.P, a.D, C.POINTER(a.D)]
                                    native.NtQueryInformationToken.restype = C.c_long
                                    size = a.D()
                                    native.NtQueryInformationToken(token, 46, None, 0, C.byref(size))
                                    row['lpac_native_required_length'] = size.value
                                    if size.value in (1, 4):
                                        data = C.create_string_buffer(size.value)
                                        status = native.NtQueryInformationToken(token, 46, data, size, C.byref(size))
                                        row['lpac_native_query_status'] = status
                                        if status == 0:
                                            row['lpac'] = bool(int.from_bytes(data.raw, 'little'))
                                try:
                                    a.check_capabilities(token)
                                    row['capabilities_match_existing_boundary'] = True
                                except Exception as error:
                                    row['capability_query_error'] = str(error)
                            finally:
                                k.CloseHandle(token)
                        if a.k.IsProcessInJob(handle, self.worker.job, C.byref(job)):
                            row['same_job'] = bool(job.value)
                        # ProcessCommandLineInformation is read-only. No target memory is written.
                        n = C.WinDLL('ntdll')
                        n.NtQueryInformationProcess.argtypes = [W.HANDLE, W.ULONG, C.c_void_p, W.ULONG, C.POINTER(W.ULONG)]
                        n.NtQueryInformationProcess.restype = W.LONG
                        class UNICODE(C.Structure):
                            _fields_ = [('length', W.USHORT), ('maximum', W.USHORT), ('buffer', C.c_void_p)]
                        required = W.ULONG()
                        n.NtQueryInformationProcess(handle, 60, None, 0, C.byref(required))
                        if 0 < required.value < 65536:
                            data = C.create_string_buffer(required.value)
                            status = n.NtQueryInformationProcess(handle, 60, data, required, C.byref(required))
                            if status == 0:
                                string = C.cast(data, C.POINTER(UNICODE)).contents
                                row['command_line'] = C.wstring_at(string.buffer, string.length // 2)
                            else:
                                row['command_query_status'] = status
                    except Exception as error:
                        row['observer_error'] = str(error)
                    finally:
                        k.CloseHandle(handle)
                self.events.append(row)
            self.stop.wait(0.1)

    def finish(self):
        self.stop.set(); self.thread.join(5)
        return {'sampling_interval_seconds': 0.1, 'complete_process_inventory': False,
                'events': self.events, 'errors': self.errors}
