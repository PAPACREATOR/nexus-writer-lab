"""Real Windows A/B; upstream Sandy helpers, unchanged Nexus runtime.

Uses Hrvoje Abraham's MIT launcher/test helpers at the pinned upstream commit.
Preparation is explicitly outside LPAC and uses only synthetic documents.
"""
import argparse
import ast
import ctypes as C
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import tomllib
import traceback
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = Path(__file__).resolve().parent / 'upstream'
UPSTREAM_SHA = 'aefeeee631518cd2d7197300a6e1a67f0c63eb63'
SANDY_SHA256 = 'cbfc30709f80e63b201f1944c34692fc430d8aa42d6cd2823fcc670675307eac'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def existing_function(path, name):
    """Reuse an existing fixture/validator without importing or starting Host."""
    tree = ast.parse(path.read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    namespace = {'io': io, 'zipfile': zipfile, 'Blocked': RuntimeError}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]


def manifest(folder):
    return {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob('*')) if p.is_file()}


def warmup(app, scratch, env, demo, evidence):
    profile, temp = scratch / 'profile', scratch / 'temp'
    seed = temp / 'initialize.fodt'
    seed.write_text(demo.DOCUMENT, encoding='utf-8')
    command = [str(app / 'program/soffice.com'), '-env:UserInstallation=' + profile.as_uri(),
               '--headless', '--norestore', '--convert-to', 'pdf', '--outdir', str(temp), str(seed)]
    started = time.monotonic()
    with (evidence / 'warmup.stdout').open('wb') as out, (evidence / 'warmup.stderr').open('wb') as err:
        p = subprocess.Popen(command, cwd=scratch / 'work', env=env, stdin=subprocess.PIPE,
                             stdout=out, stderr=err)
        p.stdin.close()
        try:
            code = p.wait(timeout=43)
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill.exe', '/PID', str(p.pid), '/T', '/F'], capture_output=True, timeout=2)
            raise RuntimeError('Synthetic unrestricted initialization exceeded 45-second budget')
    result = {'command': command, 'outside_lpac': True, 'synthetic_only': True,
              'exit_code': code, 'seconds': time.monotonic() - started}
    write(evidence / 'warmup.json', result)
    if code != 0 or not (temp / 'initialize.pdf').read_bytes().startswith(b'%PDF-'):
        raise RuntimeError('Unrestricted synthetic profile initialization failed')
    demo.finish_profile_setup(profile)
    xcu = profile / 'user/registrymodifications.xcu'
    tree = ET.parse(xcu)
    oor = 'http://openoffice.org/2001/registry'
    item = ET.SubElement(tree.getroot(), 'item', {'{' + oor + '}path': '/org.openoffice.Office.Common/Security/Scripting'})
    prop = ET.SubElement(item, 'prop', {'{' + oor + '}name': 'MacroSecurityLevel', '{' + oor + '}op': 'fuse'})
    ET.SubElement(prop, 'value').text = '3'
    tree.write(xcu, encoding='utf-8', xml_declaration=True)
    snapshot = scratch / 'profile-before'
    shutil.copytree(profile, snapshot)
    if manifest(profile) != manifest(snapshot):
        raise RuntimeError('Prepared profile backup failed exact verification')
    write(evidence / 'profile-before-hashes.json', manifest(snapshot))
    (scratch / 'initialized.json').write_text(json.dumps({'runtime': str(app), 'profile_url': profile.as_uri(),
        'build': sha(app / 'program/version.ini')}), encoding='utf-8')
    return snapshot


def elevation(pid, native):
    process = native.check(native.OpenProcess(0x1000, False, pid))
    token, size, value = native.P(), native.D(), native.D()
    try:
        native.check(native.OpenToken(process, 8, C.byref(token)))
        native.check(native.TokenInfo(token, 20, C.byref(value), C.sizeof(value), C.byref(size)))
        return bool(value.value)
    finally:
        if token: native.CloseHandle(token)
        native.CloseHandle(process)


def file_access(pid, state, native):
    """Adapted from upstream verify_writer: actual file APIs under Writer token."""
    process = native.check(native.OpenProcess(0x1000, False, pid))
    source, duplicate = native.P(), native.P()
    impersonate = native.api(native.advapi, 'SetThreadToken', native.W.BOOL, native.P, native.P)
    revert = native.api(native.advapi, 'RevertToSelf', native.W.BOOL)
    checks = []
    inside = Path(state['work']) / 'access-canary.txt'
    outside = Path(state['outside'])
    payload = b'LPAC synthetic write verified\n'
    def attempt(label, path, mask, expected, disposition=3, data=None):
        handle = native.CreateFile(str(path), mask, 7, None, disposition, 0x02000000, None)
        actual = handle != native.INVALID
        error = 0 if actual else C.get_last_error()
        row = {'check': label, 'allowed': actual, 'expected': expected, 'winerror': error,
               'pass': actual == expected and (expected or error == 5)}
        try:
            if actual and data is not None:
                count = native.D()
                native.check(native.WriteFile(handle, data, len(data), C.byref(count), None))
                row['pass'] = row['pass'] and count.value == len(data)
        finally:
            if actual: native.CloseHandle(handle)
        checks.append(row)
    try:
        native.check(native.OpenToken(process, 0xA, C.byref(source)))
        native.check(native.DuplicateToken(source, 2, C.byref(duplicate)))
        native.check(impersonate(None, duplicate))
        try:
            attempt('runtime read', Path(state['runtime']) / 'program/soffice.bin', 0x80000000, True)
            attempt('runtime write denied', Path(state['runtime']) / 'program/soffice.bin', 0x40000000, False)
            attempt('document read', Path(state['work']) / 'original.odt', 0x80000000, True)
            attempt('output create/write', inside, 0x40000000, True, 2, payload)
            attempt('external canary read denied', outside, 0x80000000, False)
            attempt('external canary write denied', outside, 0x40000000, False)
            attempt('control write denied', Path(state['scratch']) / 'initialized.json', 0x40000000, False)
            attempt('work document execute denied', Path(state['work']) / 'original.odt', 0x20, False)
            attempt('config read denied', Path(state['config']), 0x80000000, False)
        finally:
            native.check(revert())
        checks.append({'check': 'actual sandbox write bytes', 'pass': inside.read_bytes() == payload})
    finally:
        if duplicate: native.CloseHandle(duplicate)
        if source: native.CloseHandle(source)
        native.CloseHandle(process)
    return {'checks': checks, 'pass': all(c['pass'] for c in checks)}


def expected_auto_inherited_dacl(before, after):
    """Return True only when the new DACL differs by the Windows AI marker."""
    return before.startswith('D:(') and after == 'D:AI' + before[2:]


def restore_exact_lab_dacls(original, after_sandy, roots, native):
    """Restore only the metadata-only AI change on disposable, owned lab paths.

    The original DACL is reapplied unchanged with DACL_SECURITY_INFORMATION.
    SetFileSecurityW is the legacy DACL-only API; unlike SetNamedSecurityInfoW,
    it does not run auto-inheritance propagation on child objects. This is a
    lab-specific *post-process* repair, never a sandbox permission grant.
    Every unexpected flag/ACE change refuses repair and remains a hard FAIL.
    """
    repairable = []
    for name, prior in original.items():
        observed = after_sandy[name]
        if observed == prior:
            continue
        path = Path(name).resolve()
        if not any(path == root or root in path.parents for root in roots):
            raise RuntimeError('DACL restore refused outside experimental copies: ' + name)
        if not expected_auto_inherited_dacl(prior, observed):
            raise RuntimeError('DACL changed beyond AI marker; refusing repair: '
                               + name + ' before=' + prior + ' after=' + observed)
        repairable.append((path, prior, observed))
    results = []
    for path, prior, observed in repairable:
        descriptor = native.P()
        native.check(native.ConvertSDDL(prior, 1, C.byref(descriptor), None))
        try:
            restore = native.api(native.advapi, 'SetFileSecurityW',
                                 native.W.BOOL, native.W.LPCWSTR, native.D, native.P)
            native.check(restore(str(path), 4, descriptor))  # DACL only.
        finally:
            native.LocalFree(descriptor)
        verified = native.dacl(path)
        results.append({'path': str(path), 'original': prior, 'after_sandy': observed,
                        'after_exact_restore': verified, 'only_ai_changed': True})
        if verified != prior:
            raise RuntimeError('DACL exact post-restore mismatch: ' + str(path)
                               + ' expected=' + prior + ' observed=' + verified)
    return results


def convert(label, mapped, args, demo, native, capability_sid, lpac_accesscheck, env, template):
    scratch, app, evidence = args.scratch, args.libreoffice, args.evidence / label
    evidence.mkdir()
    work, profile, temp = scratch / 'work', scratch / 'profile', scratch / 'temp'
    source, destination = demo.pipe_mapping(profile.as_uri())
    values = {'@APP@': str(app), '@WORK@': str(work), '@DATA@': [str(profile), str(work), str(temp)],
              '@ANCESTORS@': demo.directory_listings((app, profile, work, temp)),
              '@SOURCE@': source, '@DESTINATION@': destination}
    config = template if mapped else template.split('\n[pipes]')[0] + '\n'
    for key, value in values.items(): config = config.replace(key, json.dumps(value, ensure_ascii=False))
    config_path = evidence / 'libreoffice.toml'
    config_path.write_text(config, encoding='utf-8')
    paths = [app, scratch, profile, work, temp, *map(Path, values['@ANCESTORS@'])]
    before = {str(p): native.dacl(p) for p in dict.fromkeys(paths)}
    command = [str(args.sandy), '-c', str(config_path), '-l', str(evidence / 'sandy.log'), '-x',
               str(app / 'program/soffice.bin'), '-env:UserInstallation=' + profile.as_uri(),
               '--norestore', '--headless', '--convert-to', 'pdf:writer_pdf_Export',
               '--outdir', str(work / 'out'), str(work / 'original.odt')]
    row = {'label': label, 'mapping_enabled': mapped, 'command': command, 'limit_seconds': 45,
           'execution_budget_seconds': 43, 'termination_reserve_seconds': 2, 'config_sha256': sha(config_path),
           'pipe_source': source, 'pipe_destination': destination, 'conversion': 'NOT RUN',
           'token': None, 'pipe_observed': False, 'errors': [],
           'baseline_dacls': {str(p): before[str(p)] for p in (app, profile, work, temp)}
    state = {'runtime': str(app), 'scratch': str(scratch), 'work': str(work), 'outside': str(scratch.parent / 'host-canary.txt'), 'config': str(config_path)}
    handles = {}
    p = None
    started = time.monotonic()
    try:
        with (evidence / 'stdout.txt').open('wb') as out, (evidence / 'stderr.txt').open('wb') as err:
            p = subprocess.Popen(command, cwd=work, env=env, stdin=subprocess.PIPE, stdout=out, stderr=err)
            p.stdin.close()
            row['launcher_pid'] = p.pid
            while p.poll() is None and time.monotonic() - started < 43:
                log_path = evidence / 'sandy.log'
                log = log_path.read_text(encoding='utf-8-sig', errors='replace') if log_path.exists() else ''
                matches = re.findall(r'LAUNCH: PID (\d+),', log)
                if matches:
                    pid = int(matches[-1])
                    row['writer_pid'] = pid
                    if pid not in handles:
                        handle = native.OpenProcess(0x100000 | 0x1000, False, pid)
                        if handle: handles[pid] = handle
                    if row['token'] is None:
                        try:
                            token = native.token_proof(pid, True, 2)
                            token['elevated'] = elevation(pid, native)
                            expected = {capability_sid('registryRead'), capability_sid('lpacCom')}
                            token['exact_capabilities'] = set(token['capability_sids']) == expected
                            row['token'] = token
                            row['lpac_accesscheck'] = lpac_accesscheck(handles[pid])
                            row['file_access'] = file_access(pid, state, native)
                        except Exception as error:
                            row['errors'].append({'live_reader': str(error)})
                    if row['token'] and mapped and not row['pipe_observed']:
                        token = row['token']
                        expected_pipe = f'Sessions\\{token["session"]}\\AppContainerNamedObjects\\{token["sid"]}\\' + source[9:]
                        names = os.listdir('\\\\.\\pipe\\')
                        if expected_pipe in names:
                            row.update(pipe_observed=True, exact_native_pipe=expected_pipe)
                time.sleep(0.01)
            row['timed_out'] = p.poll() is None
            if row['timed_out']: p.terminate()  # Sandy job closes; only our launcher.
            row['exit_code'] = p.wait(timeout=max(0.05, 45 - (time.monotonic() - started)))
            wait = native.api(native.kernel, 'WaitForSingleObject', native.D, native.P, native.D)
            row['writer_wait_results'] = {str(pid): int(wait(handle, max(0, int((started + 45 - time.monotonic()) * 1000)))) for pid, handle in handles.items()}
            row['writers_terminated'] = bool(handles) and all(value == 0 for value in row['writer_wait_results'].values())
            row['seconds_including_termination'] = time.monotonic() - started
        log = (evidence / 'sandy.log').read_text(encoding='utf-8-sig', errors='replace') if (evidence / 'sandy.log').exists() else ''
        row['hook_paths'] = re.findall(r'PIPEHOOK: extracted hook DLL -> (.*?) \(\d+ bytes\)', log)
        recovery = subprocess.run([str(args.sandy), '--cleanup'], capture_output=True, timeout=15)
        (evidence / 'recovery.txt').write_bytes(recovery.stdout + recovery.stderr)
        row['recovery_exit'] = recovery.returncode
        row['hook_removed'] = all(not Path(p).exists() for p in row['hook_paths'])
        row['hook_injected'] = mapped and bool(row['hook_paths']) and 'PIPEHOOK: hook DLL injected and imports patched' in log
        status = subprocess.run([str(args.sandy), '--status'], capture_output=True, timeout=10)
        (evidence / 'status.txt').write_bytes(status.stdout + status.stderr)
        row['container_deregistered'] = status.returncode == 0 and row['token'] is not None and row['token']['sid'] not in status.stdout.decode('utf-8', errors='replace')
        after_sandy = {p: native.dacl(Path(p)) for p in before}
        row['dacl_changes_before_restore'] = {
            p: {'before': old, 'after_sandy': after_sandy[p]}
            for p, old in before.items() if old != after_sandy[p]}
        row['dacl_recovery'] = []
        # Do not change ACLs while the Writer is still running or Sandbox
        # cleanup is unverified. Never mask unknown changes to gain PASS.
        if (row['writers_terminated'] and row['hook_removed']
                and row['recovery_exit'] == 0 and row['container_deregistered']):
            try:
                row['dacl_recovery'] = restore_exact_lab_dacls(
                    before, after_sandy, (app.resolve(), scratch.resolve()), native)
            except Exception as error:
                row['errors'].append({'dacl_recovery': str(error)})
        else:
            row['errors'].append({'dacl_recovery': 'not attempted: child/cleanup not verified'})
        after = {p: native.dacl(Path(p)) for p in before}
        write(evidence / 'dacls.json', {'before': before, 'after_sandy': after_sandy,
                                      'after_exact_restore': after})
        row['dacl_changes'] = {p: {'before': old, 'after': after[p]}
                               for p, old in before.items() if old != after[p]}
        row['dacls_unchanged'] = not row['dacl_changes']
        pdf_path = work / 'out/original.pdf'
        row['within_deadline'] = row['seconds_including_termination'] <= 45
        if not row['timed_out'] and row['within_deadline'] and row['exit_code'] == 0:
            validate = existing_function(ROOT / 'nexus/adapters/office.py', 'pdf_bytes')
            raw = validate(pdf_path)
            from pypdf import PdfReader
            text = ' '.join(' '.join(page.extract_text() or '' for page in PdfReader(io.BytesIO(raw)).pages).split())
            row['pdf'] = {'sha256': hashlib.sha256(raw).hexdigest(), 'size': len(raw),
                          'text': text, 'expected_text_found': 'Lisboa recebeu 12 caixas.' in text}
            shutil.copyfile(pdf_path, evidence / 'original.pdf')
            row['conversion'] = 'PASS' if row['pdf']['expected_text_found'] else 'FAIL'
        else:
            row['conversion'] = 'FAIL'
        t = row['token'] or {}
        row['observed_boundary_pass'] = bool(t.get('exact_capabilities') and t.get('elevated') is False
            and row.get('lpac_accesscheck', {}).get('lpac') is True and row.get('file_access', {}).get('pass')
            and row['writers_terminated'] and row['dacls_unchanged'] and row['container_deregistered']
            and row['hook_removed'] and row['recovery_exit'] == 0)
    except Exception as error:
        row['errors'].append({'experiment': str(error), 'trace': traceback.format_exc()})
        row['conversion'] = 'FAIL'
    finally:
        if p is not None and p.poll() is None:
            p.terminate()
            try: p.wait(timeout=2)
            except subprocess.TimeoutExpired: row['errors'].append({'launcher_termination': 'not confirmed'})
        for handle in handles.values(): native.CloseHandle(handle)
        write(evidence / 'result.json', row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sandy', 'libreoffice', 'scratch', 'evidence'): parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    args.sandy, args.libreoffice, args.scratch, args.evidence = (p.resolve() for p in (args.sandy, args.libreoffice, args.scratch, args.evidence))
    args.evidence.mkdir(parents=True)
    report = {'base': 'e22b33190e6144e800f69a05677f458e818d6e75', 'source_commit': os.environ.get('LAB_SOURCE_COMMIT'),
              'sandy_source': UPSTREAM_SHA, 'phases': {}, 'overall': 'NOT RUN',
              'excluded': {'network_behavior': 'NOT RUN', 'clipboard_behavior': 'NOT RUN',
                  'child_creation_behavior': 'NOT RUN', 'Host_HumanGate_routes': 'NOT RUN',
                  'regression_100_plus_100': 'NOT RUN', 'personal_PC': 'NOT RUN'}}
    try:
        if os.name != 'nt': raise RuntimeError('Windows only; no simulated PASS')
        sys.path.insert(0, str(UPSTREAM / 'test'))
        sys.path.insert(0, str(ROOT))
        import test_pipe_hook as native
        from test_lpac_capabilities import capability_sid
        from lab.observe import lpac_accesscheck
        spec = importlib.util.spec_from_file_location('sandy_demo', UPSTREAM / 'docs/libreoffice-demo.py')
        demo = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(demo)
        report['host_elevated'] = elevation(os.getpid(), native)
        if report['host_elevated']: raise RuntimeError('Standard-account execution required')
        if sha(args.sandy) != SANDY_SHA256 or args.sandy.stat().st_size != 1159680:
            raise RuntimeError('Sandy release identity mismatch')
        args.scratch.mkdir()  # Refuse reuse of unknown/existing scratch.
        for relative in ('profile', 'work', 'work/out', 'profile/home', 'profile/appdata/roaming', 'profile/appdata/local', 'temp'):
            (args.scratch / relative).mkdir(parents=True, exist_ok=True)
        app, scratch = args.libreoffice, args.scratch
        home = scratch / 'profile/home'
        env = dict(os.environ)
        env.update(TEMP=str(scratch / 'temp'), TMP=str(scratch / 'temp'), HOME=str(home), USERPROFILE=str(home),
            HOMEDRIVE=home.drive, HOMEPATH=str(home)[len(home.drive):], APPDATA=str(scratch / 'profile/appdata/roaming'),
            LOCALAPPDATA=str(scratch / 'profile/appdata/local'), SAL_DISABLESKIA='1', SAL_DISABLE_OPENCL='1')
        for name in ('PYTHONHOME', 'PYTHONPATH', 'SC_FORCE_CALCULATION'): env.pop(name, None)
        binaries = {str(p): sha(p) for p in (app / 'program/soffice.bin', app / 'program/soffice.com', app / 'program/version.ini')}
        report['binary_sha256'] = binaries
        report['sandy_sha256'] = sha(args.sandy)
        version = subprocess.check_output([str(app / 'program/soffice.com'), '--version'], timeout=15).decode(errors='replace').strip()
        report['writer_version'] = version
        if '26.2.6.2' not in version: raise RuntimeError('Unexpected Writer version')
        raw = existing_function(ROOT / 'nexus/tests/test_native_writer_route_real.py', 'document')()
        original = scratch / 'work/original.odt'
        original.write_bytes(raw)
        report['input_sha256'] = sha(original)
        outside = scratch.parent / 'host-canary.txt'
        outside.write_text('Synthetic outside canary: unchanged.', encoding='utf-8')
        canary_hash = sha(outside)
        snapshot = warmup(app, scratch, env, demo, args.evidence)
        report['phases']['synthetic_unrestricted_preparation'] = 'PASS'
        shutil.copyfile(UPSTREAM / 'LICENSE', args.evidence / 'SANDY-LICENSE.txt')
        template = (UPSTREAM / 'docs/libreoffice.toml').read_text(encoding='utf-8')
        snapshots = {'profile': snapshot}
        for name in ('work', 'temp'):
            snapshots[name] = scratch / (name + '-before')
            shutil.copytree(scratch / name, snapshots[name])
            if manifest(scratch / name) != manifest(snapshots[name]):
                raise RuntimeError('Synthetic data snapshot mismatch: ' + name)
        results = []
        for label, mapped in (('A-no-mapping', False), ('B-LOCAL-mapping', True)):
            if label.startswith('B'):
                a = results[0]
                report['cases'] = results
                if not (a.get('writers_terminated') and a.get('dacls_unchanged')
                        and a.get('container_deregistered') and a.get('hook_removed')
                        and a.get('recovery_exit') == 0):
                    raise RuntimeError('A cleanup/termination not proved; B refused before profile restoration')
                for name, saved in snapshots.items():
                    (scratch / name).rename(scratch / (name + '-after-A'))
                    shutil.copytree(saved, scratch / name)
                    if manifest(scratch / name) != manifest(saved):
                        raise RuntimeError('Synthetic data restore mismatch: ' + name)
            if sha(original) != report['input_sha256'] or sha(outside) != canary_hash:
                raise RuntimeError('Input/canary changed before next variant')
            results.append(convert(label, mapped, args, demo, native, capability_sid, lpac_accesscheck, env, template))
        a, b = results
        policies = [tomllib.loads((args.evidence / x / 'libreoffice.toml').read_text()) for x in ('A-no-mapping', 'B-LOCAL-mapping')]
        pipe_map = policies[1].pop('pipes')
        report['only_mapping_differs'] = policies[0] == policies[1] and pipe_map == {b['pipe_source']: b['pipe_destination']}
        report['same_initial_security'] = a.get('baseline_dacls') == b.get('baseline_dacls')
        report['originals_unchanged'] = sha(original) == report['input_sha256'] and sha(outside) == canary_hash and all(sha(Path(p)) == old for p, old in binaries.items())
        report['cases'] = results
        pass_b = b['conversion'] == 'PASS' and b.get('observed_boundary_pass') and b['pipe_observed'] and b.get('hook_injected')
        report['overall'] = 'PASS' if (pass_b and report['only_mapping_differs']
            and report['same_initial_security'] and report['originals_unchanged']) else 'FAIL'
        report['causal_comparison'] = 'A failed / B passed' if (report['overall'] == 'PASS'
            and a['conversion'] == 'FAIL' and a.get('observed_boundary_pass')
            and a.get('writer_pid') and not a.get('errors')) else 'INCONCLUSIVE'
        report['phases']['A_B_windows_execution'] = report['overall']
        return 0 if report['overall'] == 'PASS' else 1
    except Exception as error:
        report['overall'] = 'FAIL'
        report['error'] = str(error)
        report['trace'] = traceback.format_exc()
        return 1
    finally:
        write(args.evidence / 'summary.json', report)
        print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
