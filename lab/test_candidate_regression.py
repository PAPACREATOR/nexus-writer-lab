"""Real sequential Writer jobs share one Host and store, then restart once."""
import base64
import hashlib
import json
import os
from pathlib import Path
import time

import pytest

from nexus.contracts import Blocked
from nexus.host import Host
from nexus.tests.test_native_writer_route_real import document
from nexus.tests.test_reverse_flow import http


pytestmark = pytest.mark.skipif(
    os.name != 'nt' or os.environ.get('NEXUS_REAL_WRITER') != '1',
    reason='Actual same-Host confined Writer gate NOT RUN here')


def test_same_host_consecutive_writer_routes_preserve_approvals_and_restart(tmp_path, monkeypatch):
    from nexus import host as host_module
    launches=[]
    original_launch=host_module.launch_confined
    def observed_launch(command, **kwargs):
        worker=original_launch(command, **kwargs)
        launches.append({'command':command, 'cwd':str(kwargs['cwd']), 'pid':worker.pid})
        return worker
    monkeypatch.setattr(host_module,'launch_confined',observed_launch)
    data=tmp_path/'mesmo Host ação e espaços'
    data.mkdir()
    executable=Path(os.environ['LIBREOFFICE_EXE'])
    assert executable.is_file()
    (data/'libreoffice.json').write_text(json.dumps({'executable':str(executable)}),encoding='utf-8')
    raw=document()
    original_hash=hashlib.sha256(raw).hexdigest()
    host=Host(data)
    packages={}
    approved=[]
    used_tickets=[]
    with http(host) as call:
        for index,process in enumerate(('book','convert_pdf','book','convert_pdf')):
            release_deadline=time.monotonic()+5
            while host.busy.locked() and time.monotonic()<release_deadline:
                time.sleep(.01)
            assert not host.busy.locked(),'The previous Host job did not release its execution lock'
            run=call('/api/run',{'process':process,'text':'',
                'filename':f'São João revisão {index}.odt',
                'attachment':base64.b64encode(raw).decode('ascii')})['run_id']
            assert run not in packages
            deadline=time.monotonic()+90
            state=call('/api/runs/'+run)
            while state['status']=='RUNNING' and time.monotonic()<deadline:
                time.sleep(.1)
                state=call('/api/runs/'+run)
            assert state['status']=='HUMAN_REQUIRED',state
            assert state['result']['status']=='UNKNOWN'
            assert state['result']['ai_calls']==0
            assert (data/'runs'/run/'input.bin').read_bytes()==raw
            assert not (data/'canonical'/run).exists()
            pdf=(data/'creative'/run/'resultado.pdf').read_bytes()
            assert pdf.startswith(b'%PDF-') and b'%%EOF' in pdf[-1024:]
            pdf_hash=hashlib.sha256(pdf).hexdigest()
            assert state['result']['artifact']['sha256']==pdf_hash
            ticket=call('/api/prepare',{'run_id':run})['ticket']
            assert ticket not in used_tickets
            used_tickets.append(ticket)
            assert call('/api/approve',{'run_id':run,'ticket':ticket,'confirmed':True})['status']=='PASS'
            assert ticket not in host.tickets
            packages[run]={p.name:p.read_bytes() for p in (data/'canonical'/run).iterdir()}
            assert packages[run]['resultado.pdf']==pdf
            for previous,package in packages.items():
                assert host.store.state(previous)['status']=='PASS'
                host.store.check_commit(host.store.state(previous))
                assert {p.name:p.read_bytes() for p in (data/'canonical'/previous).iterdir()}==package
            approved.append({'sequence':index,'process':process,'run_id':run,
                             'input_sha256':original_hash,'pdf_sha256':pdf_hash,'status':'PASS'})
    assert len(launches)==4,'Every sequential request must execute exactly one actual Host worker'
    assert len({row['cwd'] for row in launches})==4,'Every request requires a distinct assigned work area'
    def no_replay(*args, **kwargs):
        pytest.fail('Restart replayed Writer or another tool')
    monkeypatch.setattr(host_module,'launch_confined',no_replay)
    monkeypatch.setattr('nexus.adapters.office.run',no_replay)
    restored=Host(data)
    assert restored.tickets=={}
    assert len(launches)==4
    for run,package in packages.items():
        assert restored.store.state(run)['status']=='PASS'
        restored.store.check_commit(restored.store.state(run))
        assert {p.name:p.read_bytes() for p in (data/'canonical'/run).iterdir()}==package
        assert (data/'runs'/run/'input.bin').read_bytes()==raw
    for item,ticket in zip(approved,used_tickets):
        with pytest.raises(Blocked):
            restored.approve(item['run_id'],ticket,True,restored.session)
        assert {p.name:p.read_bytes() for p in (data/'canonical'/item['run_id']).iterdir()}==packages[item['run_id']]
    output=Path(os.environ['LAB_EVIDENCE'])
    output.mkdir(parents=True,exist_ok=True)
    (output/'same-host-consecutive-routes.json').write_text(json.dumps({
        'requests':approved,'host_instances_before_restart':1,'launches_before_restart':len(launches),
        'launches_after_restart':len(launches),'packages_unchanged_after_restart':True,
        'stale_tickets_rejected_after_restart':True,
        'job_cleanup_gate':'LAB_REQUIRE_NO_ORPHANS=1 enforced by lab.evidence_plugin'},
        indent=2,ensure_ascii=False),encoding='utf-8')
