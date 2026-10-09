"""One 45-second SAL diagnostic using the original LPAC/Job/roots unchanged."""
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid

from nexus.adapters.runner import prepare_task
from nexus.tests.test_native_writer_route_real import document
from nexus.windows_sandbox import launch_confined, task_environment
from lab.observe import Observer
from lab.evidence_plugin import verified_lpac_observation


def require_standard_user():
    if os.name != 'nt':
        raise RuntimeError('The native SAL diagnostic requires Windows')
    kernel = C.WinDLL('kernel32', use_last_error=True)
    security = C.WinDLL('advapi32', use_last_error=True)
    kernel.GetCurrentProcess.restype = W.HANDLE
    kernel.CloseHandle.argtypes = [W.HANDLE]
    kernel.CloseHandle.restype = W.BOOL
    security.OpenProcessToken.argtypes = [W.HANDLE, W.DWORD, C.POINTER(W.HANDLE)]
    security.OpenProcessToken.restype = W.BOOL
    security.GetTokenInformation.argtypes = [
        W.HANDLE, C.c_int, C.c_void_p, W.DWORD, C.POINTER(W.DWORD)]
    security.GetTokenInformation.restype = W.BOOL
    token, elevated, length = W.HANDLE(), W.DWORD(), W.DWORD()
    if not security.OpenProcessToken(kernel.GetCurrentProcess(), 8, C.byref(token)):
        raise C.WinError(C.get_last_error())
    try:
        if not security.GetTokenInformation(token, 20, C.byref(elevated),
                                            C.sizeof(elevated), C.byref(length)):
            raise C.WinError(C.get_last_error())
        if elevated.value:
            raise RuntimeError('An elevated diagnostic parent is refused')
    finally:
        kernel.CloseHandle(token)


def query_job_after_communication(worker):
    """Read the existing native Job, allowing at most five seconds to empty."""
    class Accounting(C.Structure):
        _fields_ = [('user', C.c_int64), ('kernel', C.c_int64),
                    ('period_user', C.c_int64), ('period_kernel', C.c_int64),
                    ('faults', C.c_uint32), ('total', C.c_uint32),
                    ('active', C.c_uint32), ('terminated', C.c_uint32)]
    query = worker.api.k.QueryInformationJobObject
    query.argtypes = [worker.api.H, C.c_int, worker.api.P, worker.api.D, worker.api.P]
    query.restype = W.BOOL
    accounting = Accounting()
    started = time.monotonic()
    deadline = started + 5
    while True:
        C.set_last_error(0)
        ok = query(worker.job, 1, C.byref(accounting), C.sizeof(accounting), None)
        if not ok or accounting.active == 0 or time.monotonic() >= deadline:
            break
        time.sleep(min(0.05, max(0, deadline - time.monotonic())))
    record = {'query_ok': bool(ok),
              'active_processes': accounting.active if ok else None,
              'seconds': time.monotonic() - started}
    if not ok:
        record['winerror'] = C.get_last_error()
    return record


def observed_native_boundary(observation, worker_pid):
    """Require the actual child and positive independent LPAC observations."""
    if not isinstance(worker_pid, int) or worker_pid <= 0:
        return False
    events = observation.get('events', [])
    return (any(event.get('pid') == worker_pid for event in events)
            and all(event.get('appcontainer') is True
                    and verified_lpac_observation(event)
                    and event.get('same_job') is True
                    and event.get('capabilities_match_existing_boundary') is True
                    and event.get('elevated') is False for event in events))


def main():
    require_standard_user()
    root = Path(__file__).resolve().parents[1]
    output = root / 'lab-evidence/sal-path-probe'
    output.mkdir(parents=True, exist_ok=True)
    source = output / 'synthetic-input.odt'
    raw = document()
    source.write_bytes(raw)
    executable = Path(os.environ['LIBREOFFICE_EXE'])
    (output / 'libreoffice.json').write_text(
        json.dumps({'executable': str(executable)}), encoding='utf-8')
    work = output / '.nexus-task-sal-path' / 'runs' / uuid.uuid4().hex
    work.mkdir(parents=True)
    roots = prepare_task('convert_pdf', source, work, config_root=output)
    profile = work / 'office/profile'
    (profile / 'user').mkdir(parents=True)
    (profile / 'user/registrymodifications.xcu').write_text(
        '<?xml version="1.0"?><oor:items xmlns:oor="http://openoffice.org/2001/registry">'
        '<item oor:path="/org.openoffice.Office.Common/Security/Scripting">'
        '<prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value>'
        '</prop></item></oor:items>', encoding='utf-8')
    result = {
        'case': 'original_boundary_sal_paths',
        'lab_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root,
                                           text=True).strip(),
        'source_sha': 'b4d50ab8469cf60dfa3228c7c34ef9a1285ac827',
        'timeout_seconds': 45, 'input_sha256': hashlib.sha256(raw).hexdigest(),
        'parent_elevated': False, 'read_roots': [str(path) for path in roots],
        'read_dirs': [], 'security_changes': [], 'bootstrap_overrides': [],
        'writer_executed': False, 'product_routes_validated': False,
        'human_gate_validated': False, 'process_memory_read': False,
    }
    child = root / 'lab/sal_path_probe_child.py'
    result['sal_binary'] = str(executable.parent / 'sal3.dll')
    result['sal_sha256'] = hashlib.sha256(
        (executable.parent / 'sal3.dll').read_bytes()).hexdigest()
    result['child_sha256'] = hashlib.sha256(child.read_bytes()).hexdigest()
    started = time.monotonic()
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        command = [sys.executable, '-I', str(child),
                   str(executable.parent.parent), str(profile),
                   str(listener.getsockname()[1])]
        result['command'] = command
        try:
            with launch_confined(command, cwd=work, env=task_environment(work),
                                 read_roots=roots) as worker:
                result['worker_pid'] = worker.pid
                observer = Observer(worker)
                try:
                    stdout, stderr = worker.communicate(timeout=45)
                    result.update(exit_code=worker.returncode,
                                  stdout=stdout.decode('utf-8', errors='replace'),
                                  stderr=stderr.decode('utf-8', errors='replace'))
                finally:
                    try:
                        result['process_observation'] = observer.finish()
                    except Exception as error:
                        result['process_observation_error'] = {
                            'type': type(error).__name__, 'message': str(error)}
                    try:
                        result['job_after_communication'] = query_job_after_communication(worker)
                    except Exception as error:
                        result['job_after_communication'] = {
                            'query_ok': False, 'active_processes': None,
                            'error': {'type': type(error).__name__, 'message': str(error)}}
            result['job_context_closed'] = True
        except Exception as error:
            result['error'] = {'type': type(error).__name__, 'message': str(error)}
    result['seconds'] = time.monotonic() - started
    try:
        result['observations'] = [json.loads(line)
                                  for line in result.get('stdout', '').splitlines()]
    except json.JSONDecodeError as error:
        result['parse_error'] = str(error)
    observations = result.get('observations', [])
    job = result.get('job_after_communication', {})
    result['diagnostic_checks'] = {
        'child_completed': result.get('exit_code') == 0 and any(
            row.get('stage') == 'probe_complete' for row in observations),
        'network_denied': any(row.get('stage') == 'network_check'
                              and row.get('denied') is True for row in observations),
        'native_boundary_observed': observed_native_boundary(
            result.get('process_observation', {}), result.get('worker_pid')),
        'native_job_empty': job.get('query_ok') is True and job.get('active_processes') == 0,
        'job_context_closed': result.get('job_context_closed') is True,
    }
    result['diagnostic_completed'] = all(result['diagnostic_checks'].values())
    (output / 'probe.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0 if result['diagnostic_completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
