"""Exercise the lab watchdog with harmless subprocesses, never Writer."""
import os
import sys

from lab.run_candidate_suite import run_bounded_tests, summarize_results


def test_completed_process_preserves_output_and_exit_status(tmp_path):
    metadata = {}
    console = tmp_path / 'console.txt'
    with console.open('wb') as stream:
        code = run_bounded_tests([sys.executable, '-u', '-c', "print('completed')"],
            cwd=tmp_path, env=dict(os.environ), stream=stream, metadata=metadata, timeout=10)
    assert code == 0
    assert metadata['suite_watchdog_timed_out'] is False
    assert 'completed' in console.read_text()


def test_timeout_preserves_partial_evidence_and_cannot_pass(tmp_path):
    metadata = {'suite': 'standard'}
    console = tmp_path / 'console.txt'
    report = tmp_path / 'results.xml'
    script = ("from pathlib import Path;import time;"
        "Path('results.xml').write_text('<testsuite><testcase classname=\"control\" name=\"before_timeout\"/></testsuite>');"
        "print('partial evidence',flush=True);time.sleep(30)")
    with console.open('wb') as stream:
        code = run_bounded_tests([sys.executable, '-u', '-c', script],
            cwd=tmp_path, env=dict(os.environ), stream=stream, metadata=metadata, timeout=1)
    assert code == 124
    assert metadata['suite_watchdog_timed_out'] is True
    assert 'partial evidence' in console.read_text()
    assert report.is_file()
    assert summarize_results(report, metadata, code) != 0
    assert metadata['validation_status'] == 'TIMEOUT'


def test_opt_in_mcp_report_requires_all_three_original_checks(tmp_path):
    report = tmp_path / 'results.xml'
    report.write_text('<testsuite><testcase classname="nexus.tests.test_bidirectional_50000" '
                      'name="test_declared_total_is_exactly_50000"/></testsuite>')
    metadata = {'suite': 'bidirectional'}
    assert summarize_results(report, metadata, 0) != 0
    assert metadata['required_bidirectional_coverage']['status'] == 'FAIL'
