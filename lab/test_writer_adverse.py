"""Actual confined Writer adverse inputs, interrupted Job and fresh recovery."""
import base64, hashlib, io, json, os, time, zipfile
from pathlib import Path
import pytest
from nexus.host import Host
from nexus.tests.test_reverse_flow import http
from nexus.tests.test_native_writer_route_real import document, test_installed_writer_is_confined_and_returns_only_a_human_approved_candidate as real_route

def wait(call,run):
    end=time.monotonic()+90
    state=call('/api/runs/'+run)
    while state['status']=='RUNNING' and time.monotonic()<end:
        time.sleep(.1); state=call('/api/runs/'+run)
    return state

def configured(root):
    root.mkdir()
    (root/'libreoffice.json').write_text(json.dumps({'executable':os.environ['LIBREOFFICE_EXE']}),encoding='utf-8')
    return Host(root)

def docx():
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        z.writestr('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr('_rels/.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Lisboa ação 12 caixas.</w:t></w:r></w:p></w:body></w:document>')
    return stream.getvalue()

@pytest.mark.parametrize('process',['book','convert_pdf'])
@pytest.mark.parametrize('kind',['odt','docx'])
def test_unicode_attachment_and_docx(tmp_path,process,kind):
    raw=document() if kind=='odt' else docx()
    host=configured(tmp_path/'ação com espaços')
    with http(host) as call:
        run=call('/api/run',{'process':process,'text':'','filename':'São João revisão.'+kind,'attachment':base64.b64encode(raw).decode()})['run_id']
        state=wait(call,run)
        assert state['status']=='HUMAN_REQUIRED',state
        assert (host.store.root/'runs'/run/'input.bin').read_bytes()==raw
        pdf=(host.store.root/'creative'/run/'resultado.pdf').read_bytes()
        assert state['result']['artifact']['sha256']==hashlib.sha256(pdf).hexdigest()
        assert not (host.store.root/'canonical'/run).exists()

@pytest.mark.parametrize('process',['book','convert_pdf'])
@pytest.mark.parametrize('raw',[b'broken office document',b'PK\x03\x04invalidzip'])
def test_invalid_input_is_blocked(tmp_path,process,raw):
    host=configured(tmp_path/'data')
    with http(host) as call:
        run=call('/api/run',{'process':process,'text':'','filename':'invalid.odt','attachment':base64.b64encode(raw).decode()})['run_id']
        assert wait(call,run)['status']=='BLOCKED'
        assert (host.store.root/'runs'/run/'input.bin').read_bytes()==raw
        assert not (host.store.root/'canonical'/run).exists()

@pytest.mark.parametrize('process',['book','convert_pdf'])
def test_interrupted_native_job_reconciles_and_fresh_writer_works(tmp_path,monkeypatch,process):
    from nexus import host as module
    original=module.launch_confined
    def interrupted(command,**kwargs):
        worker=original(command,**kwargs)
        communicate=worker.communicate
        def killed(*args,**options):
            from lab.observe import Observer
            observer=Observer(worker)
            end=time.monotonic()+10
            while time.monotonic()<end and not any('--lok' in row.get('command_line','') for row in observer.events):
                time.sleep(.01)
            worker.kill()
            observed=observer.finish()
            (tmp_path/'interrupted-processes.json').write_text(json.dumps(observed,indent=2),encoding='utf-8')
            result=communicate(*args,**options)
            assert any('--lok' in row.get('command_line','') for row in observed['events']), 'No actual LOK child observed before interruption'
            return result
        worker.communicate=killed
        return worker
    host=configured(tmp_path/'crash-data')
    with monkeypatch.context() as m:
        m.setattr(module,'launch_confined',interrupted)
        with http(host) as call:
            raw=document()
            run=call('/api/run',{'process':process,'text':'','filename':'crash.odt','attachment':base64.b64encode(raw).decode()})['run_id']
            assert wait(call,run)['status']=='BLOCKED'
    restored=Host(host.store.root)
    assert restored.store.state(run)['status']=='BLOCKED'
    assert not (host.store.root/'canonical'/run).exists()
    fresh=tmp_path/'fresh'; fresh.mkdir()
    real_route(fresh,monkeypatch,process)
