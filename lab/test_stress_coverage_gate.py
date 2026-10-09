"""Reject incomplete, duplicate or skipped real-conversion reports."""
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from lab.run_candidate_suite import summarize_results


def report():
    suite=ET.Element('testsuite')
    for index in range(25):
        for process in ('book','convert_pdf'):
            ET.SubElement(suite,'testcase',classname='lab.test_writer_regression',
                          name=f'test_real_route_repetition[{index}-{process}]')
    return suite


def check(suite):
    metadata={'suite':'stress'}
    tree=ET.ElementTree(suite)
    with patch('lab.run_candidate_suite.ET.parse',return_value=tree):
        code=summarize_results('synthetic-only.xml',metadata,0)
    return code,metadata


class StressCoverageGate(unittest.TestCase):
    def test_complete_25_per_route_is_accepted(self):
        code,metadata=check(report())
        self.assertEqual(code,0)
        self.assertEqual(metadata['required_stress_coverage']['status'],'PASS')

    def test_missing_required_case_fails_even_with_green_pytest_exit(self):
        suite=report(); suite.remove(suite[-1])
        self.assertNotEqual(check(suite)[0],0)

    def test_duplicate_cannot_replace_missing_required_identity(self):
        suite=report(); suite[-1].set('name',suite[-2].get('name'))
        self.assertNotEqual(check(suite)[0],0)

    def test_skipped_conversion_fails_even_with_all_ids_present(self):
        suite=report(); ET.SubElement(suite[-1],'skipped',message='Writer not observed')
        self.assertNotEqual(check(suite)[0],0)

    def test_other_module_cannot_supply_matching_case_names(self):
        suite=report(); suite[-1].set('classname','unrelated.tests')
        self.assertNotEqual(check(suite)[0],0)


if __name__=='__main__':
    unittest.main()
