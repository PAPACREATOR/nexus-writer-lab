"""Offline controls for a complete, independently counted regression report.

These fixtures describe evidence artifacts only. They never launch Host, Writer,
or MCP and cannot stand in for the native regression itself.
"""
from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from lab.run_case import SOURCE_SHA
from lab.verify_full_coverage import verify_full_coverage


LAB_SHA = "7" * 40
CANDIDATE_SHA = "8" * 64
REPO_ROOT = Path(__file__).resolve().parents[1]
WRITER_SHA = "c0d5fabc7717c1a32a281f44798f964c458f406c90fb508ba03b98b53fa0c86c"
WRITER_VERSION = "LibreOffice 26.2.6.2 ad5cf9fd4989cacf0bca866ebefc0ec8926cb0b2"
SECURITY_MODULES = (
    "nexus/security_tests/test_authority_10000.py",
    "nexus/security_tests/test_confinement_gate.py",
    "nexus/security_tests/test_documentary_bridge.py",
    "nexus/security_tests/test_install_gate.py",
    "nexus/security_tests/test_moneyprinter_config_gate.py",
    "nexus/security_tests/test_native_boundary.py",
    "nexus/security_tests/test_state_concurrency.py",
    "nexus/security_tests/test_windows_hash.py",
)
BIDIRECTIONAL_NAMES = (
    "test_internal_bidirectional_25000_exact_roundtrips",
    "test_external_mcp_real_stdio_25000_bidirectional_calls",
    "test_declared_total_is_exactly_50000",
)
VOLUME_MODULES = (
    "nexus/tests/test_product_flows_5000.py",
    "nexus/tests/test_product_system_50000.py",
    "nexus/tests/test_product_themes_canonical_200k.py",
    "nexus/tests/test_public_product_routes_10000.py",
    "nexus/tests/test_public_product_routes_all_50000.py",
    "nexus/tests/test_windows_stack_structural_300k.py",
)
ADVERSE_NAMES = (
    *(f"test_unicode_attachment_and_docx[{kind}-{process}]"
      for kind in ("odt", "docx") for process in ("book", "convert_pdf")),
    *(f"test_invalid_input_is_blocked[{raw}-{process}]"
      for raw in ("broken office document", r"PK\x03\x04invalidzip")
      for process in ("book", "convert_pdf")),
    *(f"test_interrupted_native_job_reconciles_and_fresh_writer_works[{process}]"
      for process in ("book", "convert_pdf")),
)
JOBS = (
    *(('stress', shard) for shard in range(4)),
    *(('standard', shard) for shard in range(2)),
    *(('volume', shard) for shard in range(6)),
    ('adverse', 0),
    ('bidirectional', 0),
)


def _artifact(root: Path, suite: str, shard: int = 0) -> Path:
    return root / f"writer-candidate-{suite}-{shard}"


def _job(root: Path, suite: str, shard: int = 0) -> Path:
    return _artifact(root, suite, shard) / "standard-user" / f"candidate-{suite}-{shard}"


def _json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _selected_modules(suite: str, shard: int) -> list[str]:
    if suite == "stress":
        return ["lab/test_writer_regression.py"]
    if suite == "adverse":
        return ["lab/test_writer_adverse.py", "lab/test_candidate_regression.py"]
    if suite == "volume":
        return [VOLUME_MODULES[shard]]
    if suite == "bidirectional":
        return ["nexus/tests/test_bidirectional_50000.py"]
    excluded = {*VOLUME_MODULES, "nexus/tests/test_bidirectional_50000.py"}
    discovered = sorted(
        path.relative_to(REPO_ROOT).as_posix()
        for directory in ("nexus/tests", "nexus/security_tests")
        for path in (REPO_ROOT / directory).rglob("*.py")
        if (path.name.startswith("test_") or path.name.endswith("_test.py"))
        and path.relative_to(REPO_ROOT).as_posix() not in excluded
    )
    return discovered[shard::2]


def _source_cases(module: str) -> list[ET.Element]:
    tree = ast.parse((REPO_ROOT / module).read_text(encoding="utf-8-sig"))
    names = [node.name for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")]
    assert names, f"Fixture must represent tests from selected source {module}"
    return [_case(module.removesuffix(".py").replace("/", "."), name) for name in names]


def _write_collection(job: Path, modules: list[str], cases: list[ET.Element]) -> None:
    _json(job / "collection.json", {
        "schema": "nexus.writer.test-collection.v1", "collect_only": True,
        "exit_code": 0, "deselected": [],
        "test_module_sha256": {
            module: hashlib.sha256((REPO_ROOT / module).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for module in modules
        },
        "testcases": [{"classname": case.get("classname"), "name": case.get("name")} for case in cases],
    })


def _collection(root: Path, suite: str, shard: int = 0) -> dict:
    return json.loads((_job(root, suite, shard) / "collection.json").read_text(encoding="utf-8"))


def _sync_collection(root: Path, suite: str, shard: int = 0) -> None:
    _write_collection(_job(root, suite, shard),
                      _metadata(root, suite, shard)["test_modules_selected"], _cases(root, suite, shard))


def _metadata(root: Path, suite: str, shard: int = 0, **updates) -> dict:
    path = _job(root, suite, shard) / "metadata.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if updates:
        value.update(updates)
        _json(path, value)
    return value


def _write_report(path: Path, cases: list[ET.Element]) -> None:
    suite = ET.Element("testsuite", {
        "name": "pytest", "tests": str(len(cases)),
        "failures": str(sum(case.find("failure") is not None for case in cases)),
        "errors": str(sum(case.find("error") is not None for case in cases)),
        "skipped": str(sum(case.find("skipped") is not None for case in cases)),
    })
    suite.extend(cases)
    report = ET.Element("testsuites")
    report.append(suite)
    ET.ElementTree(report).write(path, encoding="utf-8", xml_declaration=True)


def _case(module: str, name: str) -> ET.Element:
    return ET.Element("testcase", {"classname": module, "name": name, "time": "0.01"})


def _cases(root: Path, suite: str, shard: int = 0) -> list[ET.Element]:
    return list(ET.parse(_job(root, suite, shard) / "results.xml").getroot().iter("testcase"))


def _replace_cases(root: Path, suite: str, cases: list[ET.Element], shard: int = 0) -> None:
    _write_report(_job(root, suite, shard) / "results.xml", cases)


def _assert_fail(root: Path) -> dict:
    result = verify_full_coverage(root)
    assert result["status"] == "FAIL", result
    assert result["errors"], result
    return result


@pytest.fixture
def complete_evidence(tmp_path: Path) -> Path:
    """Fourteen plausible successful artifacts from one sealed candidate/build."""
    root = tmp_path / "evidence"
    for suite, shard in JOBS:
        artifact = _artifact(root, suite, shard)
        job = _job(root, suite, shard)
        job.mkdir(parents=True)
        selected_modules = _selected_modules(suite, shard)
        metadata = {
            "suite": suite, "shard": shard, "source_sha": SOURCE_SHA,
            "lab_sha": LAB_SHA, "tested_office_sha256": CANDIDATE_SHA,
            "writer_binary_sha256": WRITER_SHA, "writer_timeout_seconds": 45,
            "integrity_verified": True, "original_bytes_restored": True,
            "pytest_exit_code": 0, "effective_exit_code": 0,
            "validation_status": "PASS", "checks_not_run": [],
            "security_modules_selected": [], "required_security_modules_missing": [],
            "required_security_checks_not_run": [], "required_security_status": "NOT_APPLICABLE",
            "test_modules_selected": selected_modules, "collection_exit_code": 0,
        }
        if suite == "stress":
            metadata["actual_converter_observation_status"] = "PASS"
            cases = [_case("lab.test_writer_regression", f"test_real_route_repetition[{index}-{process}]")
                     for index in range(25) for process in ("book", "convert_pdf")]
            metadata["required_stress_coverage"] = {
                "status": "PASS", "expected": 50, "observed": 50,
                "missing": [], "unexpected": [], "duplicates": [],
                "wrong_modules": [], "not_passed": [],
            }
        elif suite == "standard":
            selected = [module for module in selected_modules if module.startswith("nexus/security_tests/")]
            metadata.update(security_modules_selected=selected, required_security_status="PASS")
            cases = [case for module in selected_modules for case in _source_cases(module)]
        elif suite == "bidirectional":
            cases = [_case("nexus.tests.test_bidirectional_50000", name) for name in BIDIRECTIONAL_NAMES]
            metadata.update(bidirectional_50k_enabled=True,
                            required_bidirectional_coverage={"status": "PASS"})
        elif suite == "adverse":
            cases = [_case("lab.test_writer_adverse", name) for name in ADVERSE_NAMES]
            cases.append(_case("lab.test_candidate_regression",
                               "test_same_host_consecutive_writer_routes_preserve_approvals_and_restart"))
        else:
            cases = _source_cases(selected_modules[0])
        metadata["collected_testcases"] = len(cases)
        _json(job / "metadata.json", metadata)
        _write_report(job / "results.xml", cases)
        _write_collection(job, selected_modules, cases)
        _json(artifact / "writer-binary-hash.json", {"Algorithm": "SHA256", "Hash": WRITER_SHA.upper()})
        (artifact / "libreoffice-version.txt").write_text(WRITER_VERSION + "\n", encoding="utf-8")
        _json(artifact / "standard-user" / "standard-user-writer-hash.json", {"sha256": WRITER_SHA})
    return root


def test_complete_evidence_counts_all_100_book_and_100_pdf_routes(complete_evidence):
    result = verify_full_coverage(complete_evidence)
    assert result["status"] == "PASS", result
    assert result["errors"] == []
    assert result["checks_not_run"] == []
    assert result["stress"] == {"book": 100, "convert_pdf": 100}


@pytest.mark.parametrize("suite,shard", [("stress", 3), ("standard", 1), ("volume", 5),
                                         ("adverse", 0), ("bidirectional", 0)])
def test_missing_required_job_cannot_be_hidden_by_remaining_successes(complete_evidence, suite, shard):
    shutil.rmtree(_artifact(complete_evidence, suite, shard))
    _assert_fail(complete_evidence)


def test_duplicate_job_artifact_is_rejected_even_with_all_required_shards(complete_evidence):
    shutil.copytree(_artifact(complete_evidence, "stress", 0),
                    complete_evidence / "writer-candidate-stress-0-duplicate")
    _assert_fail(complete_evidence)


def test_truncated_stress_report_is_recounted_despite_green_metadata(complete_evidence):
    _replace_cases(complete_evidence, "stress", _cases(complete_evidence, "stress")[:-1])
    _assert_fail(complete_evidence)


@pytest.mark.parametrize("outcome", ["failure", "error", "skipped"])
def test_stress_case_must_pass_in_actual_junit(complete_evidence, outcome):
    cases = _cases(complete_evidence, "stress")
    ET.SubElement(cases[-1], outcome, {"message": "native route did not complete"})
    _replace_cases(complete_evidence, "stress", cases)
    _assert_fail(complete_evidence)


def test_duplicate_stress_identity_is_rejected_even_with_50_testcases(complete_evidence):
    cases = _cases(complete_evidence, "stress")
    cases[-1].set("name", cases[0].get("name"))
    _replace_cases(complete_evidence, "stress", cases)
    _assert_fail(complete_evidence)


def test_expected_stress_name_from_wrong_module_is_not_route_evidence(complete_evidence):
    cases = _cases(complete_evidence, "stress")
    cases[0].set("classname", "lab.synthetic_writer")
    _replace_cases(complete_evidence, "stress", cases)
    _assert_fail(complete_evidence)


@pytest.mark.parametrize("field,value", [
    ("source_sha", "1" * 40), ("lab_sha", "2" * 40),
    ("tested_office_sha256", "3" * 64), ("writer_binary_sha256", "4" * 64),
])
def test_results_from_different_source_candidate_or_build_cannot_be_combined(complete_evidence, field, value):
    _metadata(complete_evidence, "adverse", **{field: value})
    _assert_fail(complete_evidence)


@pytest.mark.parametrize("field,value", [("lab_sha", "unknown"), ("tested_office_sha256", "8" * 63),
                                         ("writer_binary_sha256", None)])
def test_unverifiable_hashes_are_not_provenance(complete_evidence, field, value):
    _metadata(complete_evidence, "volume", **{field: value})
    _assert_fail(complete_evidence)


@pytest.mark.parametrize("identity", ["installed", "copied"])
def test_actual_binary_identity_must_match_the_tested_copy(complete_evidence, identity):
    artifact = _artifact(complete_evidence, "adverse")
    if identity == "installed":
        _json(artifact / "writer-binary-hash.json", {"Algorithm": "SHA256", "Hash": "5" * 64})
    else:
        _json(artifact / "standard-user" / "standard-user-writer-hash.json", {"sha256": "5" * 64})
    _assert_fail(complete_evidence)


@pytest.mark.parametrize("identity", ["version", "buildid", "binary"])
def test_consistent_but_wrong_archived_build_is_still_rejected(complete_evidence, identity):
    for suite, shard in JOBS:
        artifact = _artifact(complete_evidence, suite, shard)
        if identity == "version":
            (artifact / "libreoffice-version.txt").write_text("LibreOffice 26.2.6.3 wrongbuild\n", encoding="utf-8")
        elif identity == "buildid":
            (artifact / "libreoffice-version.txt").write_text("LibreOffice 26.2.6.2 wrongbuild\n", encoding="utf-8")
        else:
            _json(artifact / "writer-binary-hash.json", {"Algorithm": "SHA256", "Hash": "6" * 64})
            _json(artifact / "standard-user" / "standard-user-writer-hash.json", {"sha256": "6" * 64})
            _metadata(complete_evidence, suite, shard, writer_binary_sha256="6" * 64)
    _assert_fail(complete_evidence)


@pytest.mark.parametrize("field,value", [("writer_timeout_seconds", 46), ("integrity_verified", False),
                                         ("original_bytes_restored", False)])
def test_missing_integrity_or_changed_writer_bound_is_not_accepted(complete_evidence, field, value):
    _metadata(complete_evidence, "adverse", **{field: value})
    _assert_fail(complete_evidence)


@pytest.mark.parametrize("relative", [
    "standard-user/candidate-volume-0/results.xml",
    "standard-user/candidate-volume-0/metadata.json",
    "standard-user/candidate-volume-0/collection.json",
    "writer-binary-hash.json", "libreoffice-version.txt",
    "standard-user/standard-user-writer-hash.json",
])
def test_missing_evidence_cannot_be_inferred_from_other_jobs(complete_evidence, relative):
    (_artifact(complete_evidence, "volume") / relative).unlink()
    _assert_fail(complete_evidence)


def test_broken_junit_is_failure_instead_of_missing_test_success(complete_evidence):
    (_job(complete_evidence, "volume") / "results.xml").write_text("<testsuites><testsuite>", encoding="utf-8")
    _assert_fail(complete_evidence)


def _add_optional_skip(root: Path, *, record_metadata: bool) -> dict:
    module = "nexus.tests.test_public_product_routes_mcp"
    shard = next(index for index in range(2)
                 if module.replace(".", "/") + ".py" in _metadata(root, "standard", index)["test_modules_selected"])
    cases = _cases(root, "standard", shard)
    case = next(item for item in cases if item.get("classname") == module)
    row = {"classname": module, "name": case.get("name"), "reason": "requires separate platform evidence"}
    ET.SubElement(case, "skipped", {"message": row["reason"]})
    _replace_cases(root, "standard", cases, shard)
    if record_metadata:
        _metadata(root, "standard", shard, checks_not_run=[row], validation_status="PARTIAL_NOT_RUN",
                  collected_testcases=len(cases))
    return row


def test_optional_not_run_is_retained_and_prevents_global_pass(complete_evidence):
    row = _add_optional_skip(complete_evidence, record_metadata=True)
    result = verify_full_coverage(complete_evidence)
    assert result["status"] == "PARTIAL_NOT_RUN", result
    assert result["errors"] == []
    assert any(item.get("name") == row["name"] for item in result["checks_not_run"]), result
    assert row["reason"] in json.dumps(result["checks_not_run"])
    assert result["stress"] == {"book": 100, "convert_pdf": 100}


def test_skipped_xml_cannot_be_hidden_by_green_empty_metadata(complete_evidence):
    row = _add_optional_skip(complete_evidence, record_metadata=False)
    result = verify_full_coverage(complete_evidence)
    assert result["status"] != "PASS", result
    assert any(item.get("name") == row["name"] for item in result["checks_not_run"]), result


def test_missing_security_module_is_detected_from_actual_testcases(complete_evidence):
    cases = _cases(complete_evidence, "standard")
    missing_class = cases[0].get("classname")
    _replace_cases(complete_evidence, "standard",
                   [case for case in cases if case.get("classname") != missing_class])
    _assert_fail(complete_evidence)


def test_security_module_cannot_be_omitted_from_both_selection_and_results(complete_evidence):
    metadata = _metadata(complete_evidence, "standard")
    missing_class = metadata["security_modules_selected"][0].removesuffix(".py").replace("/", ".")
    _metadata(complete_evidence, "standard", security_modules_selected=metadata["security_modules_selected"][1:])
    _replace_cases(complete_evidence, "standard", [case for case in _cases(complete_evidence, "standard")
                                                  if case.get("classname") != missing_class])
    _assert_fail(complete_evidence)


def test_duplicate_security_selection_does_not_prove_all_modules(complete_evidence):
    metadata = _metadata(complete_evidence, "standard", 1)
    duplicate = metadata["security_modules_selected"][0]
    _metadata(complete_evidence, "standard", 1,
              security_modules_selected=metadata["security_modules_selected"] + [duplicate])
    _assert_fail(complete_evidence)


def test_required_security_skip_is_failure_even_if_optional_skips_are_allowed(complete_evidence):
    cases = _cases(complete_evidence, "standard")
    ET.SubElement(cases[0], "skipped", {"message": "native security gate unavailable"})
    _replace_cases(complete_evidence, "standard", cases)
    _assert_fail(complete_evidence)


@pytest.mark.parametrize("field,value", [
    ("required_security_status", "NOT_RUN"),
    ("required_security_modules_missing", [SECURITY_MODULES[0]]),
    ("required_security_checks_not_run", [{"name": "test_required_contract", "reason": "unavailable"}]),
])
def test_failed_security_attestation_cannot_be_overruled_by_green_xml(complete_evidence, field, value):
    _metadata(complete_evidence, "standard", **{field: value})
    _assert_fail(complete_evidence)


@pytest.mark.parametrize("field,value", [("pytest_exit_code", 1), ("pytest_exit_code", None),
                                         ("effective_exit_code", 124), ("validation_status", "TIMEOUT"),
                                         ("validation_status", "FAIL"), ("validation_status", "ERROR")])
def test_failed_or_unfinished_job_is_never_global_pass(complete_evidence, field, value):
    updates = {field: value}
    if value == "TIMEOUT":
        updates["suite_watchdog_timed_out"] = True
    _metadata(complete_evidence, "volume", **updates)
    _assert_fail(complete_evidence)


def test_watchdog_timeout_cannot_be_hidden_by_stale_green_status(complete_evidence):
    _metadata(complete_evidence, "volume", suite_watchdog_timed_out=True)
    _assert_fail(complete_evidence)


def test_bidirectional_suite_requires_all_three_original_checks(complete_evidence):
    _replace_cases(complete_evidence, "bidirectional", _cases(complete_evidence, "bidirectional")[:-1])
    _assert_fail(complete_evidence)


@pytest.mark.parametrize("outcome", ["failure", "error", "skipped"])
def test_bidirectional_original_checks_must_actually_pass(complete_evidence, outcome):
    cases = _cases(complete_evidence, "bidirectional")
    ET.SubElement(cases[0], outcome, {"message": "50k roundtrip gate incomplete"})
    _replace_cases(complete_evidence, "bidirectional", cases)
    _assert_fail(complete_evidence)


def test_bidirectional_opt_in_gate_must_be_recorded_enabled(complete_evidence):
    _metadata(complete_evidence, "bidirectional", bidirectional_50k_enabled=False)
    _assert_fail(complete_evidence)


@pytest.mark.parametrize("suite,key", [("stress", "required_stress_coverage"),
                                      ("bidirectional", "required_bidirectional_coverage")])
def test_failed_required_coverage_metadata_is_not_overruled_by_green_xml(complete_evidence, suite, key):
    _metadata(complete_evidence, suite, **{key: {"status": "FAIL"}})
    _assert_fail(complete_evidence)


@pytest.mark.parametrize("status", ["PASS", "PARTIAL_NOT_RUN", "FAIL"])
def test_cli_exit_and_saved_report_require_complete_pass(complete_evidence, status):
    if status == "PARTIAL_NOT_RUN":
        _add_optional_skip(complete_evidence, record_metadata=True)
    elif status == "FAIL":
        shutil.rmtree(_artifact(complete_evidence, "bidirectional"))
    output = complete_evidence.parent / "aggregate.json"
    completed = subprocess.run(
        [sys.executable, "-m", "lab.verify_full_coverage", str(complete_evidence),
         "--output", str(output), "--lab-sha", LAB_SHA],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
        timeout=30, check=False,
    )
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == status, (report, completed.stdout, completed.stderr)
    assert (completed.returncode == 0) is (status == "PASS")


def test_explicit_expected_lab_sha_prevents_accepting_stale_matching_jobs(complete_evidence):
    result = verify_full_coverage(complete_evidence, expected_lab_sha="9" * 40)
    assert result["status"] == "FAIL", result
    assert result["errors"], result


@pytest.mark.parametrize("observation", [None, "PENDING_CANDIDATE"])
def test_pending_actual_converter_observation_blocks_global_pass(complete_evidence, observation):
    metadata = _metadata(complete_evidence, "stress")
    if observation is None:
        del metadata["actual_converter_observation_status"]
        _json(_job(complete_evidence, "stress") / "metadata.json", metadata)
    else:
        _metadata(complete_evidence, "stress", actual_converter_observation_status=observation)
    result = verify_full_coverage(complete_evidence)
    assert result["orchestration_status"] == "PASS", result
    assert result["status"] == "PARTIAL_NOT_RUN", result
    assert result["errors"] == []
    assert result["required_follow_up"], result


@pytest.mark.parametrize("suite", ["standard", "volume"])
def test_k_style_reduced_execution_cannot_pass_with_green_pytest_exit(complete_evidence, suite):
    cases = _cases(complete_evidence, suite)
    _replace_cases(complete_evidence, suite, cases[:-1])
    _metadata(complete_evidence, suite, collected_testcases=len(cases) - 1)
    _assert_fail(complete_evidence)


@pytest.mark.parametrize("corruption", ["schema", "not_collect_only", "failed_collection", "deselected",
                                        "wrong_module", "wrong_hash", "empty", "incomplete", "duplicate"])
def test_collection_receipt_must_be_complete_unfiltered_and_source_bound(complete_evidence, corruption):
    receipt = _collection(complete_evidence, "standard")
    if corruption == "schema":
        receipt["schema"] = "unverified-collection"
    elif corruption == "not_collect_only":
        receipt["collect_only"] = False
    elif corruption == "failed_collection":
        receipt["exit_code"] = 1
    elif corruption == "deselected":
        receipt["deselected"] = [receipt["testcases"][0]]
    elif corruption == "wrong_module":
        receipt["testcases"][0]["classname"] = "nexus.tests.unselected_module"
    elif corruption == "wrong_hash":
        receipt["test_module_sha256"][next(iter(receipt["test_module_sha256"]))] = "0" * 64
    elif corruption == "empty":
        receipt["testcases"] = []
    elif corruption == "incomplete":
        receipt["testcases"].pop()
    else:
        receipt["testcases"].append(receipt["testcases"][0])
    _json(_job(complete_evidence, "standard") / "collection.json", receipt)
    _assert_fail(complete_evidence)


def test_recorded_collection_failure_is_not_overruled_by_good_receipt(complete_evidence):
    _metadata(complete_evidence, "standard", collection_exit_code=1)
    _assert_fail(complete_evidence)


@pytest.mark.parametrize("inventory", [None, "not-a-testcase-list", [{"classname": "nexus.tests.example"}],
                                       [{"classname": [], "name": "test_bad_identity"}]])
def test_malformed_collection_inventory_returns_fail_without_unhandled_exception(complete_evidence, inventory):
    receipt = _collection(complete_evidence, "standard")
    receipt["testcases"] = inventory
    _json(_job(complete_evidence, "standard") / "collection.json", receipt)
    _assert_fail(complete_evidence)


def test_source_module_cannot_be_removed_from_selection_and_its_matching_receipt(complete_evidence):
    metadata = _metadata(complete_evidence, "standard")
    removed = next(module for module in metadata["test_modules_selected"] if "/security_tests/" not in module)
    _metadata(complete_evidence, "standard",
              test_modules_selected=[module for module in metadata["test_modules_selected"] if module != removed])
    cases = [case for case in _cases(complete_evidence, "standard")
             if case.get("classname") != removed.removesuffix(".py").replace("/", ".")]
    _replace_cases(complete_evidence, "standard", cases)
    _sync_collection(complete_evidence, "standard")
    _assert_fail(complete_evidence)


def test_deleted_ordinary_check_is_detected_even_when_collection_and_results_agree(complete_evidence):
    cases = _cases(complete_evidence, "standard")
    removed = next(case for case in cases if sum(
        item.get("classname") == case.get("classname") for item in cases) > 1)
    cases.remove(removed)
    _replace_cases(complete_evidence, "standard", cases)
    _metadata(complete_evidence, "standard", collected_testcases=len(cases))
    _sync_collection(complete_evidence, "standard")
    _assert_fail(complete_evidence)


@pytest.mark.parametrize("name_prefix", ["test_unicode_attachment_and_docx", "test_invalid_input_is_blocked",
                                         "test_interrupted_native_job_reconciles_and_fresh_writer_works",
                                         "test_same_host_consecutive_writer_routes_preserve_approvals_and_restart"])
def test_adverse_missing_required_check_is_not_a_complete_regression(complete_evidence, name_prefix):
    cases = _cases(complete_evidence, "adverse")
    removed = next(case for case in cases if case.get("name").startswith(name_prefix))
    cases.remove(removed)
    _replace_cases(complete_evidence, "adverse", cases)
    _metadata(complete_evidence, "adverse", collected_testcases=len(cases))
    _sync_collection(complete_evidence, "adverse")
    _assert_fail(complete_evidence)


def test_volume_receipt_from_another_module_cannot_validate_the_expected_shard(complete_evidence):
    cases = _source_cases(VOLUME_MODULES[1])
    _replace_cases(complete_evidence, "volume", cases)
    _sync_collection(complete_evidence, "volume")
    _assert_fail(complete_evidence)
