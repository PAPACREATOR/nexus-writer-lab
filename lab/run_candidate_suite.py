"""Explicit experimental seal, original runtime restored even after failure."""
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path
import xml.etree.ElementTree as ET
from lab.run_case import SOURCE_SHA, ROOT

def summarize_results(report, metadata, pytest_exit_code):
    effective_code=pytest_exit_code
    try:
        testcases=list(ET.parse(report).getroot().iter('testcase'))
        skipped=[]
        for case in testcases:
            skip=case.find('skipped')
            if skip is not None:
                skipped.append({'classname':case.get('classname',''),'name':case.get('name',''),
                                'reason':skip.get('message','') or (skip.text or '')})
        metadata['collected_testcases']=len(testcases)
        metadata['checks_not_run']=skipped
        if metadata.get('suite')=='stress':
            expected={f'test_real_route_repetition[{index}-{process}]'
                      for index in range(25) for process in ('book','convert_pdf')}
            names=[case.get('name','') for case in testcases]
            duplicates=sorted({name for name in names if names.count(name)>1})
            wrong_modules=[case.get('name','') for case in testcases
                           if case.get('classname','').replace('.','/')!='lab/test_writer_regression']
            not_passed=[case.get('name','') for case in testcases
                        if any(case.find(tag) is not None for tag in ('failure','error','skipped'))]
            coverage={'expected':50,'observed':len(names),
                      'missing':sorted(expected-set(names)),
                      'unexpected':sorted(set(names)-expected),
                      'duplicates':duplicates,'wrong_modules':wrong_modules,
                      'not_passed':not_passed}
            coverage['status']='PASS' if (len(names)==50 and not any(
                coverage[key] for key in ('missing','unexpected','duplicates','wrong_modules','not_passed'))) else 'FAIL'
            metadata['required_stress_coverage']=coverage
            if coverage['status']!='PASS':
                effective_code=effective_code or 1
        security_skips=[row for row in skipped if row['classname'].replace('.','/').startswith('nexus/security_tests/')]
        metadata['required_security_checks_not_run']=security_skips
        classes={case.get('classname','').replace('.','/') for case in testcases}
        selected=metadata.get('security_modules_selected',[])
        missing=[module for module in selected if module.removesuffix('.py') not in classes]
        metadata['required_security_modules_missing']=missing
        metadata['required_security_status']=('NOT_APPLICABLE' if not selected else
            ('NOT_RUN' if security_skips or missing else ('FAIL' if pytest_exit_code else 'PASS')))
        if security_skips or missing:
            effective_code=effective_code or 1
        # Optional dependencies/platform gates retain NOT RUN status. A
        # green pytest exit alone must not be presented as total coverage.
        metadata['validation_status']='FAIL' if effective_code else ('PARTIAL_NOT_RUN' if skipped else 'PASS')
    except (OSError,ET.ParseError) as error:
        metadata['result_report_error']=str(error)
        metadata['validation_status']='ERROR'
        effective_code=effective_code or 1
    metadata['effective_exit_code']=effective_code
    return effective_code


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
            env['LAB_REQUIRE_NO_ORPHANS']='1'
            targets=['lab/test_writer_adverse.py','lab/test_candidate_regression.py','-p','lab.evidence_plugin']
            # The interrupted-job test still requires the actual nexus_lok
            # child. Review that candidate-specific match if the candidate
            # changes; a generic worker observation must never replace it.
            metadata['candidate_specific_crash_gate']='lab/test_writer_adverse.py requires an observed nexus_lok child'
        elif args.suite=='volume':
            env['NEXUS_REAL_WRITER']='0'
            targets=['nexus/tests/'+volume[args.shard]]
        else:
            env['NEXUS_REAL_WRITER']='0'
            metadata['optional_real_writer_env']='0, original standard-regression default; actual confined routes run in stress/adverse suites'
            all_modules=sorted(str(p.relative_to(ROOT)).replace('\\','/')
                for directory in ('nexus/tests','nexus/security_tests')
                for p in (ROOT/directory).rglob('*.py')
                if (p.name.startswith('test_') or p.name.endswith('_test.py')) and p.name not in volume)
            targets=all_modules[args.shard::2]
            metadata['security_modules_selected']=[p for p in targets if p.startswith('nexus/security_tests/')]
        env['NEXUS_CONFINEMENT_EVIDENCE']=str(output/'confinement.json')
        env['NEXUS_NATIVE_EVIDENCE']=str(output/'native-10000.json')
        command=[sys.executable,'-u','-m','pytest',*targets,'-vv','--tb=short','-p','no:cacheprovider','-o','pythonpath=.','--basetemp='+str(output/'tmp'),'--junitxml='+str(output/'results.xml')]
        metadata['test_command']=command
        with (output/'console.txt').open('wb') as stream:
            result=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
        metadata['pytest_exit_code']=result.returncode
        return summarize_results(output/'results.xml',metadata,result.returncode)
    finally:
        office.write_bytes(original); manifest.write_bytes(seal)
        metadata['original_bytes_restored']=office.read_bytes()==original and manifest.read_bytes()==seal
        (output/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')

if __name__=='__main__': raise SystemExit(main())
