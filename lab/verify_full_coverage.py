"""Fail closed on missing, mixed or partial full-regression artifacts."""
import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from lab.run_case import ROOT, SOURCE_SHA
from lab.run_candidate_suite import BIDIRECTIONAL_TESTS, suite_modules

# Identity observed after the hash-pinned official 26.2.6.2 MSI installation,
# including the independent standard-user copy in exact-msaa run 37900791913.
EXPECTED_WRITER_VERSION = 'LibreOffice 26.2.6.2 ad5cf9fd4989cacf0bca866ebefc0ec8926cb0b2'
EXPECTED_WRITER_SHA256 = 'c0d5fabc7717c1a32a281f44798f964c458f406c90fb508ba03b98b53fa0c86c'
EXPECTED_JOBS = {(suite, shard) for suite, count in
    [('stress', 4), ('standard', 2), ('volume', 6), ('adverse', 1), ('bidirectional', 1)]
    for shard in range(count)}


def _text(path):
    raw = path.read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig').strip()


def _json(path):
    value = json.loads(_text(path))
    if not isinstance(value, dict):
        raise ValueError('Expected JSON object: ' + str(path))
    return value


def _test_identities(cases):
    return Counter((case['classname'], case['name']) for case in cases)


def verify_full_coverage(evidence_root, expected_lab_sha=None):
    evidence_root = Path(evidence_root)
    result = {'schema': 'nexus.writer.full-coverage.v1', 'status': 'FAIL',
              'errors': [], 'checks_not_run': [], 'required_follow_up': [],
              'stress': {'book': 0, 'convert_pdf': 0}, 'jobs': []}
    errors = result['errors']
    found = Counter()
    identities = {'lab_sha': set(), 'tested_office_sha256': set(), 'writer_binary_sha256': set()}
    selected_security = []
    required_security = {str(path.relative_to(ROOT)).replace('\\', '/')
        for path in (ROOT / 'nexus/security_tests').rglob('*.py')
        if path.name.startswith('test_') or path.name.endswith('_test.py')}
    for report in sorted(evidence_root.rglob('metadata.json')):
        if not report.parent.name.startswith('candidate-'):
            continue
        label = str(report.relative_to(evidence_root))
        try:
            metadata = _json(report)
            suite, shard = metadata.get('suite'), metadata.get('shard')
            if not isinstance(suite, str) or type(shard) is not int or (suite, shard) not in EXPECTED_JOBS:
                raise ValueError('Unexpected suite/shard identity')
            key = (suite, shard)
            found[key] += 1
            if found[key] != 1:
                raise ValueError('Duplicate suite/shard artifact')
            artifact = next((parent for parent in report.parents
                if parent.name == f'writer-candidate-{suite}-{shard}'), None)
            if artifact is None:
                raise ValueError('Missing named job artifact directory')
            if report.parent.name != f'candidate-{suite}-{shard}':
                raise ValueError('Suite identity disagrees with evidence directory')
            if metadata.get('source_sha') != SOURCE_SHA:
                errors.append(label + ': original SOURCE_SHA mismatch')
            for name, length in [('lab_sha', 40), ('tested_office_sha256', 64), ('writer_binary_sha256', 64)]:
                value = metadata.get(name)
                if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{' + str(length) + '}', value):
                    errors.append(label + ': missing/invalid ' + name)
                else:
                    identities[name].add(value)
            if expected_lab_sha is not None and metadata.get('lab_sha') != expected_lab_sha:
                errors.append(label + ': workflow lab SHA mismatch')
            installed = _json(artifact / 'writer-binary-hash.json')
            copied = _json(report.parent.parent / 'standard-user-writer-hash.json')
            binary_hashes = [installed.get('Hash', '').lower(), copied.get('sha256'),
                             metadata.get('writer_binary_sha256')]
            if installed.get('Algorithm') != 'SHA256' or binary_hashes != [EXPECTED_WRITER_SHA256] * 3:
                errors.append(label + ': archival installed/copied/tested Writer binary mismatch')
            if _text(artifact / 'libreoffice-version.txt') != EXPECTED_WRITER_VERSION:
                errors.append(label + ': exact archival Writer version/build mismatch')
            if (metadata.get('writer_timeout_seconds') != 45 or metadata.get('integrity_verified') is not True
                    or metadata.get('original_bytes_restored') is not True):
                errors.append(label + ': timeout/integrity/restoration evidence invalid')
            if (metadata.get('pytest_exit_code') != 0 or metadata.get('effective_exit_code') != 0
                    or metadata.get('validation_status') not in ('PASS', 'PARTIAL_NOT_RUN')
                    or metadata.get('suite_watchdog_timed_out')):
                errors.append(label + ': suite failed, timed out or never completed')
            cases = list(ET.parse(report.with_name('results.xml')).getroot().iter('testcase'))
            if not cases:
                errors.append(label + ': empty test report')
            expected_modules = suite_modules(suite, shard)
            collection = _json(report.with_name('collection.json'))
            inventory = collection.get('testcases', [])
            source_hashes = {module: hashlib.sha256((ROOT/module).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
                             for module in expected_modules}
            if (metadata.get('test_modules_selected') != expected_modules
                    or metadata.get('collection_exit_code') != 0
                    or collection.get('schema') != 'nexus.writer.test-collection.v1'
                    or collection.get('collect_only') is not True
                    or collection.get('exit_code') != 0 or collection.get('deselected') != []
                    or collection.get('test_module_sha256') != source_hashes):
                errors.append(label + ': selected module/source collection attestation invalid')
            actual_inventory = [{'classname': case.get('classname',''), 'name': case.get('name','')} for case in cases]
            if not inventory or _test_identities(inventory) != _test_identities(actual_inventory):
                errors.append(label + ': executed testcase inventory differs from full collection')
            # Independently prevent a forged/reduced receipt from deleting a
            # required source function together with its JUnit testcase.
            source_functions = {(module.removesuffix('.py').replace('/','.'), node.name)
                for module in expected_modules
                for node in ast.parse((ROOT/module).read_text(encoding='utf-8-sig')).body
                if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name.startswith('test_')}
            collected_functions = {(case['classname'],case['name'].split('[',1)[0]) for case in inventory}
            if source_functions != collected_functions:
                errors.append(label + ': collection omitted or invented required source test functions')
            skips = []
            for case in cases:
                if any(case.find(tag) is not None for tag in ('failure', 'error')):
                    errors.append(label + ': failed test ' + case.get('name', ''))
                skip = case.find('skipped')
                if skip is not None:
                    skips.append({'classname': case.get('classname', ''), 'name': case.get('name', ''),
                                  'reason': skip.get('message', '') or (skip.text or '')})
            if metadata.get('checks_not_run') != skips:
                errors.append(label + ': metadata disagrees with actual NOT RUN checks')
            if metadata.get('validation_status') != ('PARTIAL_NOT_RUN' if skips else 'PASS'):
                errors.append(label + ': validation status disagrees with test report')
            result['checks_not_run'].extend({'suite': suite, 'shard': shard, **skip} for skip in skips)
            follow_up = metadata.get('required_follow_up', [])
            if not isinstance(follow_up, list) or not all(isinstance(item, str) for item in follow_up):
                errors.append(label + ': invalid pending coverage inventory')
            else:
                result['required_follow_up'].extend(follow_up)
            names = [case.get('name', '') for case in cases]
            modules = [case.get('classname', '').replace('.', '/') for case in cases]
            if suite == 'stress':
                if metadata.get('actual_converter_observation_status') != 'PASS':
                    result['required_follow_up'].append(
                        'Mandatory candidate-specific actual converter child observation gate is pending')
                expected = {f'test_real_route_repetition[{index}-{process}]'
                            for index in range(25) for process in ('book', 'convert_pdf')}
                passed = (len(names) == 50 and set(names) == expected
                    and all(module == 'lab/test_writer_regression' for module in modules)
                    and not skips and not any(case.find(tag) is not None
                        for case in cases for tag in ('failure', 'error'))
                    and metadata.get('required_stress_coverage', {}).get('status') == 'PASS')
                if not passed:
                    errors.append(label + ': incomplete/duplicate/unsuccessful 25+25 stress identities')
                else:
                    result['stress']['book'] += 25
                    result['stress']['convert_pdf'] += 25
            elif suite == 'bidirectional':
                if (len(names) != 3 or set(names) != BIDIRECTIONAL_TESTS or skips
                        or any(module != 'nexus/tests/test_bidirectional_50000' for module in modules)
                        or metadata.get('bidirectional_50k_enabled') is not True
                        or metadata.get('required_bidirectional_coverage', {}).get('status') != 'PASS'):
                    errors.append(label + ': original opt-in 50k MCP gate incomplete')
            elif suite == 'adverse':
                expected_adverse = Counter({
                    ('lab.test_writer_adverse','test_unicode_attachment_and_docx'):4,
                    ('lab.test_writer_adverse','test_invalid_input_is_blocked'):4,
                    ('lab.test_writer_adverse','test_interrupted_native_job_reconciles_and_fresh_writer_works'):2,
                    ('lab.test_candidate_regression','test_same_host_consecutive_writer_routes_preserve_approvals_and_restart'):1})
                observed_adverse = Counter((case.get('classname',''),case.get('name','').split('[',1)[0]) for case in cases)
                if observed_adverse != expected_adverse:
                    errors.append(label + ': required 11 adverse/consecutive checks incomplete')
            elif suite == 'standard':
                selected = metadata.get('security_modules_selected', [])
                if not isinstance(selected, list) or not selected or not all(isinstance(module,str) for module in selected):
                    errors.append(label + ': security module inventory missing')
                else:
                    selected_security.extend(selected)
                    if any(module.removesuffix('.py') not in modules for module in selected):
                        errors.append(label + ': selected security module has no actual test cases')
                if (metadata.get('required_security_status') != 'PASS'
                        or metadata.get('required_security_checks_not_run') != []
                        or metadata.get('required_security_modules_missing') != []
                        or any(skip['classname'].replace('.', '/').startswith('nexus/security_tests/') for skip in skips)):
                    errors.append(label + ': required native/security checks failed or NOT RUN')
            result['jobs'].append({'suite': suite, 'shard': shard, 'testcases': len(cases),
                                   'status': metadata.get('validation_status')})
        except (OSError, ValueError, TypeError, KeyError, AttributeError, SyntaxError, ET.ParseError) as error:
            errors.append(label + ': ' + str(error))
    missing = EXPECTED_JOBS - set(found)
    if missing:
        errors.append('Missing required jobs: ' + ', '.join(f'{suite}-{shard}' for suite, shard in sorted(missing)))
    for name, values in identities.items():
        if len(values) != 1:
            errors.append('Mixed or missing ' + name)
    if Counter(selected_security) != Counter(required_security):
        errors.append('Required security module inventory missing, unexpected or duplicated')
    if result['stress'] != {'book': 100, 'convert_pdf': 100}:
        errors.append('Required successful real stress total is not 100 book + 100 PDF')
    result['identity'] = {name: next(iter(values)) if len(values) == 1 else None
                          for name, values in identities.items()}
    result['source_sha'] = SOURCE_SHA
    result['required_follow_up'] = sorted(set(result['required_follow_up']))
    result['orchestration_status'] = 'FAIL' if errors else 'PASS'
    result['status'] = 'FAIL' if errors else ('PARTIAL_NOT_RUN'
        if result['checks_not_run'] or result['required_follow_up'] else 'PASS')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence_root', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--lab-sha')
    args = parser.parse_args()
    result = verify_full_coverage(args.evidence_root, args.lab_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'jobs': len(result['jobs']),
                      'stress': result['stress'], 'checks_not_run': len(result['checks_not_run']),
                      'errors': result['errors']}, ensure_ascii=False))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
