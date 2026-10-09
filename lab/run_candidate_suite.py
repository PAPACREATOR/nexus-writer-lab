"""Explicit experimental seal, original runtime restored even after failure."""
import argparse, hashlib, json, os, subprocess, sys, time
from pathlib import Path
import xml.etree.ElementTree as ET
from lab.run_case import SOURCE_SHA, ROOT

SUITE_WATCHDOG_SECONDS = 75 * 60
BIDIRECTIONAL_TESTS = {
    'test_internal_bidirectional_25000_exact_roundtrips',
    'test_external_mcp_real_stdio_25000_bidirectional_calls',
    'test_declared_total_is_exactly_50000',
}
VOLUME_MODULES = ['test_product_flows_5000.py','test_product_system_50000.py',
    'test_product_themes_canonical_200k.py','test_public_product_routes_10000.py',
    'test_public_product_routes_all_50000.py','test_windows_stack_structural_300k.py']
_deselected_items = []


def suite_modules(suite, shard):
    if suite == 'stress':
        return ['lab/test_writer_regression.py']
    if suite == 'adverse':
        return ['lab/test_writer_adverse.py','lab/test_candidate_regression.py']
    if suite == 'volume':
        return ['nexus/tests/' + VOLUME_MODULES[shard]]
    if suite == 'bidirectional':
        return ['nexus/tests/test_bidirectional_50000.py']
    modules = sorted(str(path.relative_to(ROOT)).replace('\\','/')
        for directory in ('nexus/tests','nexus/security_tests')
        for path in (ROOT/directory).rglob('*.py')
        if (path.name.startswith('test_') or path.name.endswith('_test.py'))
        and path.name not in [*VOLUME_MODULES,'test_bidirectional_50000.py'])
    return modules[shard::2]


def pytest_deselected(items):
    _deselected_items.extend(item.nodeid for item in items)


def pytest_sessionfinish(session, exitstatus):
    """Collection-only plugin: no fixture or test body is executed."""
    destination = os.environ.get('LAB_COLLECTION_MANIFEST')
    if not destination:
        return
    modules = [str(Path(arg).resolve().relative_to(ROOT)).replace('\\','/')
               for arg in session.config.args]
    cases = []
    for item in session.items:
        parts = item.nodeid.split('::')
        module = parts[0].replace('\\','/').removesuffix('.py').replace('/','.')
        cases.append({'classname': '.'.join([module, *parts[1:-1]]), 'name': parts[-1]})
    record = {'schema':'nexus.writer.test-collection.v1',
        'collect_only':bool(session.config.option.collectonly),'exit_code':int(exitstatus),
        'deselected':_deselected_items, 'testcases':cases,
        'test_module_sha256':{module:hashlib.sha256((ROOT/module).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
                              for module in modules}}
    Path(destination).write_text(json.dumps(record,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def run_bounded_tests(command, *, cwd, env, stream, metadata,
                      timeout=SUITE_WATCHDOG_SECONDS):
    """Bound the lab suite, retaining its console and a failing timeout record."""
    metadata['suite_watchdog_seconds'] = timeout
    metadata['suite_watchdog_timed_out'] = False
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stream,
                               stderr=subprocess.STDOUT)
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        metadata['suite_watchdog_timed_out'] = True
        metadata['validation_status'] = 'TIMEOUT'
        metadata['pytest_exit_code'] = metadata['effective_exit_code'] = 124
        # Kill only this test process family. Closing its native Job handles
        # also kills confined children; a timeout can never certify cleanup.
        if os.name == 'nt':
            try:
                termination = subprocess.run(
                    ['taskkill', '/PID', str(process.pid), '/T', '/F'],
                    stdout=stream, stderr=subprocess.STDOUT, timeout=30)
                metadata['watchdog_tree_termination_exit_code'] = termination.returncode
            except (OSError, subprocess.TimeoutExpired) as error:
                metadata['watchdog_tree_termination_error'] = str(error)
        if process.poll() is None:
            process.kill()
        process.wait(timeout=30)
        return 124

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
        if metadata.get('suite')=='bidirectional':
            names=[case.get('name','') for case in testcases]
            passed=(len(names)==3 and set(names)==BIDIRECTIONAL_TESTS and
                all(case.get('classname','').replace('.','/')=='nexus/tests/test_bidirectional_50000'
                    and not any(case.find(tag) is not None for tag in ('failure','error','skipped'))
                    for case in testcases))
            metadata['required_bidirectional_coverage']={'expected':3,'observed':len(names),
                'status':'PASS' if passed else 'FAIL'}
            if not passed:
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
    if metadata.get('suite_watchdog_timed_out'):
        metadata['validation_status']='TIMEOUT'
        effective_code=effective_code or 124
    metadata['effective_exit_code']=effective_code
    return effective_code


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('suite',choices=['stress','standard','volume','adverse','bidirectional'])
    parser.add_argument('shard',type=int)
    args=parser.parse_args()
    shards={'stress':4,'standard':2,'volume':6,'adverse':1,'bidirectional':1}
    if not 0 <= args.shard < shards[args.suite]:
        parser.error('Shard is outside the declared full-regression matrix')
    output=ROOT/f'lab-evidence/candidate-{args.suite}-{args.shard}'
    output.mkdir(parents=True,exist_ok=True)
    office=ROOT/'nexus/adapters/office.py'; manifest=ROOT/'nexus/integrity.json'
    original,seal=office.read_bytes(),manifest.read_bytes()
    expected=subprocess.check_output(['git','show',SOURCE_SHA+':nexus/adapters/office.py'],cwd=ROOT)
    assert original.replace(b'\r\n',b'\n')==expected.replace(b'\r\n',b'\n')
    metadata={'source_sha':SOURCE_SHA,'lab_sha':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'suite':args.suite,'shard':args.shard,'writer_timeout_seconds':45,'security_changes':[]}
    binary=Path(os.environ['LIBREOFFICE_EXE']).with_name('soffice.bin')
    metadata['writer_binary_sha256']=hashlib.sha256(binary.read_bytes()).hexdigest()
    try:
        office.write_bytes((ROOT/'lab/candidate-office.py').read_bytes())
        hashes=json.loads(seal); hashes['adapters/office.py']=hashlib.sha256(office.read_bytes()).hexdigest()
        manifest.write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
        from nexus.host import verify_integrity
        verify_integrity(); metadata['integrity_verified']=True
        metadata['tested_office_sha256']=hashes['adapters/office.py']
        (output/'tested-office.py').write_bytes(office.read_bytes())
        env={**os.environ,'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','NEXUS_REAL_WRITER':'1','LAB_SHARD':str(args.shard),'LAB_EVIDENCE':str(output)}
        # Inherited pytest selection must not silently reduce required coverage.
        env.pop('PYTEST_ADDOPTS',None)
        env.pop('PYTEST_PLUGINS',None)
        env['NEXUS_RUN_50K']='0'
        modules=suite_modules(args.suite,args.shard)
        metadata['test_modules_selected']=modules
        if args.suite=='stress':
            env['LAB_REQUIRE_NO_ORPHANS']='1'
            targets=[*modules,'-p','lab.evidence_plugin']
            # Mandatory TODO before accepting a final candidate: require an
            # actual converter child observation, not only the runner token.
            metadata['actual_converter_observation_status']='PENDING_CANDIDATE'
            metadata['required_follow_up']=['Verify candidate-specific actual converter child observations']
        elif args.suite=='adverse':
            env['LAB_REQUIRE_NO_ORPHANS']='1'
            targets=[*modules,'-p','lab.evidence_plugin']
            # The interrupted-job test still requires the actual nexus_lok
            # child. Review that candidate-specific match if the candidate
            # changes; a generic worker observation must never replace it.
            metadata['candidate_specific_crash_gate']='lab/test_writer_adverse.py requires an observed nexus_lok child'
        elif args.suite=='volume':
            env['NEXUS_REAL_WRITER']='0'
            targets=modules
        elif args.suite=='bidirectional':
            env['NEXUS_REAL_WRITER']='0'
            env['NEXUS_RUN_50K']='1'
            metadata['bidirectional_50k_enabled']=True
            targets=modules
        else:
            env['NEXUS_REAL_WRITER']='0'
            metadata['optional_real_writer_env']='0, original standard-regression default; actual confined routes run in stress/adverse suites'
            targets=modules
            metadata['security_modules_selected']=[p for p in targets if p.startswith('nexus/security_tests/')]
        env['NEXUS_CONFINEMENT_EVIDENCE']=str(output/'confinement.json')
        env['NEXUS_NATIVE_EVIDENCE']=str(output/'native-10000.json')
        common=['-p','no:cacheprovider','-o','pythonpath=.','--rootdir='+str(ROOT)]
        collection_command=[sys.executable,'-u','-m','pytest',*targets,*common,
            '-p','lab.run_candidate_suite','--collect-only','-q','--basetemp='+str(output/'collection-tmp')]
        collection_env={**env,'LAB_COLLECTION_MANIFEST':str(output/'collection.json')}
        started=time.monotonic()
        with (output/'collection-console.txt').open('wb') as stream:
            collection_code=run_bounded_tests(collection_command,cwd=ROOT,env=collection_env,
                stream=stream,metadata=metadata,timeout=min(300,SUITE_WATCHDOG_SECONDS))
        metadata['collection_exit_code']=collection_code
        if collection_code:
            metadata['validation_status']='TIMEOUT' if metadata['suite_watchdog_timed_out'] else 'ERROR'
            metadata['effective_exit_code']=collection_code
            return collection_code
        command=[sys.executable,'-u','-m','pytest',*targets,*common,'-vv','--tb=short',
            '--basetemp='+str(output/'tmp'),'--junitxml='+str(output/'results.xml')]
        metadata['test_command']=command
        with (output/'console.txt').open('wb') as stream:
            remaining=max(1,SUITE_WATCHDOG_SECONDS-(time.monotonic()-started))
            code=run_bounded_tests(command,cwd=ROOT,env=env,stream=stream,metadata=metadata,timeout=remaining)
        metadata['pytest_exit_code']=code
        return summarize_results(output/'results.xml',metadata,code)
    finally:
        office.write_bytes(original); manifest.write_bytes(seal)
        metadata['original_bytes_restored']=office.read_bytes()==original and manifest.read_bytes()==seal
        (output/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')

if __name__=='__main__': raise SystemExit(main())
