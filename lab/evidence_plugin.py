"""Additional evidence around original tests; no PASS assertions are removed."""
import hashlib
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
        worker.communicate = communication
        return worker
    monkeypatch.setattr(host, 'launch_confined', observed)
    yield
    safe = request.node.name.replace('[', '-').replace(']', '')
    (output / (safe + '-launches.json')).write_text(json.dumps(launches, indent=2, ensure_ascii=False), encoding='utf-8')
