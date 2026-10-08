"""Explicit experimental seal, original runtime restored even after failure."""
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path
from lab.run_case import SOURCE_SHA, ROOT

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('suite',choices=['stress','standard','volume','adverse'])
    parser.add_argument('shard',type=int)
    args=parser.parse_args()
    output=ROOT/f'lab-evidence/candidate-{args.suite}-{args.shard}'
    output.mkdir(parents=True,exist_ok=True)
    office=ROOT/'nexus/adapters/office.py'; manifest=ROOT/'nexus/integrity.json'
    original,seal=office.read_bytes(),manifest.read_bytes()
    expected=subprocess.check_output(['git','show',SOURCE_SHA+':nexus/adapters/office.py'],cwd=ROOT)
    assert original.replace(b'\r\n',b'\n')==expected.replace(b'\r\n',b'\n')
    metadata={'source_sha':SOURCE_SHA,'lab_sha':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'suite':args.suite,'shard':args.shard,'writer_timeout_seconds':45,'security_changes':[]}
    try:
        office.write_bytes((ROOT/'lab/candidate-office.py').read_bytes())
        hashes=json.loads(seal); hashes['adapters/office.py']=hashlib.sha256(office.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
        from nexus.host import verify_integrity
        verify_integrity(); metadata['integrity_verified']=True
        metadata['tested_office_sha256']=hashes['adapters/office.py']
        (output/'tested-office.py').write_bytes(office.read_bytes())
        env={**os.environ,'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','NEXUS_REAL_WRITER':'1','LAB_SHARD':str(args.shard),'LAB_EVIDENCE':str(output)}
        volume=['test_product_flows_5000.py','test_product_system_50000.py','test_product_themes_canonical_200k.py','test_public_product_routes_10000.py','test_public_product_routes_all_50000.py','test_windows_stack_structural_300k.py']
        if args.suite=='stress':
            env['LAB_REQUIRE_NO_ORPHANS']='1'
            targets=['lab/test_writer_regression.py','-p','lab.evidence_plugin']
        elif args.suite=='adverse':
            targets=['lab/test_writer_adverse.py','-p','lab.evidence_plugin']
        elif args.suite=='volume':
            env['NEXUS_REAL_WRITER']='0'
            targets=['nexus/tests/'+volume[args.shard]]
        else:
            env['NEXUS_REAL_WRITER']='0'
            metadata['optional_real_writer_env']='0, original standard-regression default; actual confined routes run in stress/adverse suites'
            all_modules=sorted(str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'nexus/tests').rglob('*.py') if (p.name.startswith('test_') or p.name.endswith('_test.py')) and p.name not in volume)
            targets=all_modules[args.shard::2]
        command=[sys.executable,'-u','-m','pytest',*targets,'-vv','--tb=short','-p','no:cacheprovider','-o','pythonpath=.','--basetemp='+str(output/'tmp'),'--junitxml='+str(output/'results.xml')]
        metadata['test_command']=command
        with (output/'console.txt').open('wb') as stream:
            result=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
        metadata['pytest_exit_code']=result.returncode
        return result.returncode
    finally:
        office.write_bytes(original); manifest.write_bytes(seal)
        metadata['original_bytes_restored']=office.read_bytes()==original and manifest.read_bytes()==seal
        (output/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')

if __name__=='__main__': raise SystemExit(main())
