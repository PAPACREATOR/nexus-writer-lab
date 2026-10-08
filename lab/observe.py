"""Read-only sampling of the existing native job, without attaching a debugger."""
import ctypes as C
from ctypes import wintypes as W
import threading
import time


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
