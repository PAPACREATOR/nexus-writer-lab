"""Standalone render diagnostic; no product PASS or authority is conferred."""
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
from nexus.adapters.office import pdf_bytes
from nexus.tests.test_native_writer_route_real import document
from nexus.windows_sandbox import launch_confined, task_environment
from lab.observe import Observer

root = Path(__file__).resolve().parents[1]
case = sys.argv[1] if len(sys.argv) > 1 else 'baseline'
if case not in ('baseline', 'sal_log', 'long_path'):
    raise SystemExit('Unknown bounded diagnostic')
output = root / ('lab-evidence/lok-probe' if case == 'baseline' else 'lab-evidence/lok-probe-' + case)
if case == 'long_path':
    output = output / ('path ' * 15).strip()
output.mkdir(parents=True, exist_ok=True)
source = output / 'synthetic-input.odt'
raw = document(); source.write_bytes(raw)
exe = Path(os.environ['LIBREOFFICE_EXE'])
(output / 'libreoffice.json').write_text(json.dumps({'executable': str(exe)}), encoding='utf-8')
work = output / '.nexus-task-lok' / 'runs' / uuid.uuid4().hex
work.mkdir(parents=True)
roots = prepare_task('convert_pdf', source, work, config_root=output)
office = work / 'office'
profile = office / 'profile'
(profile / 'user').mkdir(parents=True)
(office / 'resultado.odt').write_bytes(raw)
(profile / 'user/registrymodifications.xcu').write_text(
    '<?xml version="1.0"?><oor:items xmlns:oor="http://openoffice.org/2001/registry">'
    '<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item></oor:items>', encoding='utf-8')
command = [sys.executable, '-I', str(root / 'nexus/lab/writer_lok_probe.py'), str(exe.parent)]
result = {'case': case, 'lab_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
          'source_sha': 'b4d50ab8469cf60dfa3228c7c34ef9a1285ac827',
          'timeout_seconds': 45, 'input_sha256': hashlib.sha256(raw).hexdigest(),
          'read_roots': [str(p) for p in roots], 'security_changes': [],
          'product_routes_validated': False, 'human_gate_validated': False}
start = time.monotonic()
with socket.socket() as listener:
    listener.bind(('127.0.0.1', 0)); listener.listen(1)
    command.append(str(listener.getsockname()[1]))
    result['command'] = command
    try:
        env = task_environment(work)
        if case == 'sal_log': env['SAL_LOG'] = '+WARN'
        with launch_confined(command, cwd=work, env=env, read_roots=roots) as worker:
            observer = Observer(worker)
            try:
                stdout, stderr = worker.communicate(timeout=45)
                result.update(exit_code=worker.returncode, stdout=stdout.decode('utf-8', errors='replace'), stderr=stderr.decode('utf-8', errors='replace'))
            finally:
                result['process_observation'] = observer.finish()
    except Exception as error:
        result['error'] = {'type': type(error).__name__, 'message': str(error)}
result['seconds'] = time.monotonic() - start
stages = work / 'lok-stages.jsonl'
if stages.is_file():
    result['stages'] = [json.loads(line) for line in stages.read_text('utf-8').splitlines()]
try:
    pdf = pdf_bytes(work / 'resultado.pdf')
    result['pdf'] = {'length': len(pdf), 'sha256': hashlib.sha256(pdf).hexdigest()}
    (output / 'resultado.pdf').write_bytes(pdf)
except Exception as error:
    result['pdf_error'] = str(error)
result['render_pass'] = result.get('exit_code') == 0 and 'pdf' in result and result['seconds'] < 45
(output / 'probe.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['render_pass'] else 1)
