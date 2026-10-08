"""Additional evidence around original tests; no PASS assertions are removed."""
import hashlib
import ctypes as C
import json
import os
from pathlib import Path
import time
import pytest
from lab.observe import Observer


@pytest.fixture(autouse=True)
def record_existing_launch(monkeypatch, request):
    from nexus import host
    original = host.launch_confined
    output = Path(os.environ['LAB_EVIDENCE']).resolve()
    output.mkdir(parents=True, exist_ok=True)
    launches = []

    def observed(command, **kwargs):
        record = {'command': command, 'cwd': str(kwargs['cwd']),
                  'read_roots': [str(p) for p in kwargs.get('read_roots', ())],
                  'deny_roots': [str(p) for p in kwargs.get('deny_roots', ())],
                  'writer_timeout_seconds': 45, 'launch_seconds': time.monotonic()}
        launches.append(record)
        try:
            worker = original(command, **kwargs)
        except Exception as error:
            record['launch_error'] = str(error)
            raise
        record['pid'] = worker.pid
        record['appcontainer_verified_by_existing_launcher'] = True
        record['lpac_requested_by_existing_launcher'] = True
        record['job_verified_by_existing_launcher'] = True
        observer = Observer(worker)
        communicate = worker.communicate
        def communication(*args, **options):
            start = time.monotonic()
            try:
                result = communicate(*args, **options)
                record['worker_stdout'] = result[0].decode('utf-8', errors='replace')
                record['worker_stderr'] = result[1].decode('utf-8', errors='replace')
                return result
            except Exception as error:
                record['communication_error'] = str(error)
                raise
            finally:
                record['communication_seconds'] = time.monotonic() - start
                record['worker_exit_code'] = worker.returncode
                record['process_observation'] = observer.finish()
                class Accounting(C.Structure):
                    _fields_ = [('user', C.c_longlong), ('kernel', C.c_longlong),
                                ('period_user', C.c_longlong), ('period_kernel', C.c_longlong),
                                ('faults', C.c_ulong), ('total', C.c_ulong),
                                ('active', C.c_ulong), ('terminated', C.c_ulong)]
                query = worker.api.k.QueryInformationJobObject
                query.argtypes = [worker.api.H, C.c_int, worker.api.P, worker.api.D, worker.api.P]
                query.restype = worker.api.D
                accounting = Accounting()
                deadline = time.monotonic() + 5
                while True:
                    ok = query(worker.job, 1, C.byref(accounting), C.sizeof(accounting), None)
                    if not ok or accounting.active == 0 or time.monotonic() >= deadline:
                        break
                    time.sleep(0.05)
                record['job_after_communication'] = {'query_ok': bool(ok), 'active_processes': accounting.active if ok else None}
                work = Path(kwargs['cwd'])
                record['files'] = {}
                for name in ('office/stdout.txt', 'office/stderr.txt', 'office/profile/user/registrymodifications.xcu', 'resultado.pdf'):
                    path = work / name
                    if path.is_file():
                        raw = path.read_bytes()
                        item = {'length': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
                        if not name.endswith('.pdf'):
                            item['text'] = raw[:12000].decode('utf-8', errors='replace')
                        record['files'][name] = item
                record['profile_exists'] = (work / 'office/profile').is_dir()
                record['profile_files'] = [str(p.relative_to(work)) for p in (work / 'office/profile').rglob('*') if p.is_file()]
                profile = work / 'office/profile'
                if profile.is_dir():
                    a = worker.api
                    dacl, descriptor = a.P(), a.P()
                    error = a.a.GetNamedSecurityInfoW(str(profile), 1, 4, None, None, C.byref(dacl), None, C.byref(descriptor))
                    record['profile_acl'] = {'query_error': error, 'task_sid_aces': []}
                    if not error:
                        try:
                            get_ace = a.a.GetAce
                            get_ace.argtypes = [a.P, a.D, C.POINTER(a.P)]
                            get_ace.restype = a.D
                            if dacl:
                                count = C.c_ushort.from_address(dacl.value + 4).value
                                for index in range(count):
                                    ace = a.P()
                                    if get_ace(dacl, index, C.byref(ace)):
                                        kind = C.c_ubyte.from_address(ace.value).value
                                        flags = C.c_ubyte.from_address(ace.value + 1).value
                                        if kind in (0, 1) and a.a.EqualSid(a.P(ace.value + 8), worker.sid):
                                            mask = C.c_ulong.from_address(ace.value + 4).value
                                            record['profile_acl']['task_sid_aces'].append({'type': kind, 'mask': mask, 'inherited': bool(flags & 0x10)})
                        finally:
                            if descriptor: a.k.LocalFree(descriptor)
        worker.communicate = communication
        return worker
    monkeypatch.setattr(host, 'launch_confined', observed)
    yield
    safe = request.node.name.replace('[', '-').replace(']', '')
    (output / (safe + '-launches.json')).write_text(json.dumps(launches, indent=2, ensure_ascii=False), encoding='utf-8')
    if os.environ.get('LAB_REQUIRE_NO_ORPHANS') == '1':
        assert launches, 'No real Host launch observed'
        assert all(row.get('job_after_communication') == {'query_ok': True, 'active_processes': 0} for row in launches), 'Native Job retained processes or could not be queried'
