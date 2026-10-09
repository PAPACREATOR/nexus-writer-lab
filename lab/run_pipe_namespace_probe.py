"""Actual Windows LPAC/Job namespace probe with unchanged Nexus launcher.

Diagnostic only: a successful probe is NOT LibreOffice Writer conversion PASS.
"""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import uuid

from nexus.adapters.runner import prepare_task
from nexus.windows_sandbox import launch_confined, task_environment
from lab.observe import Observer
from lab.run_sal_path_probe import (
    require_standard_user, query_job_after_communication, observed_native_boundary,
)


def main():
    require_standard_user()
    root = Path(__file__).resolve().parents[1]
    output = root / "lab-evidence/pipe-namespace-probe"
    output.mkdir(parents=True, exist_ok=True)
    source = output / "synthetic-input.txt"
    source.write_bytes(b"Nexus synthetic named-pipe namespace check")
    work = output / ".nexus-task-pipe-namespace" / "runs" / uuid.uuid4().hex
    work.mkdir(parents=True)
    roots = prepare_task("verify", source, work)
    child = work / "pipe_namespace_child.py"
    child.write_bytes((root / "lab/pipe_namespace_child.py").read_bytes())
    result = {
        "schema": "nexus.writer.pipe-namespaces.v1",
        "source_sha": "b4d50ab8469cf60dfa3228c7c34ef9a1285ac827",
        "lab_head": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                             cwd=root, text=True).strip(),
        "variant": "unchanged_native_lpac_namespace_probe",
        "timeout_seconds": 45,
        "parent_elevated": False,
        "security_changes": [],
        "read_roots": [str(path) for path in roots],
        "child_sha256": hashlib.sha256(child.read_bytes()).hexdigest(),
        "writer_executed": False,
        "product_routes_validated": False,
        "human_gate_validated": False,
        "no_dump": True,
    }
    started = time.monotonic()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        command = [sys.executable, "-I", str(child), str(root / "nexus"),
                   uuid.uuid4().hex, str(listener.getsockname()[1])]
        try:
            with launch_confined(command, cwd=work, env=task_environment(work),
                                 read_roots=roots) as worker:
                observer = Observer(worker)
                result["worker_pid"] = worker.pid
                try:
                    stdout, stderr = worker.communicate(timeout=45)
                    result.update(exit_code=worker.returncode,
                                  stdout=stdout.decode("utf-8", errors="replace"),
                                  stderr=stderr.decode("utf-8", errors="replace"))
                finally:
                    result["process_observation"] = observer.finish()
                    result["job_after_communication"] = query_job_after_communication(worker)
            result["job_context_closed"] = True
        except Exception as error:
            result["error"] = {"type": type(error).__name__, "message": str(error)}
    result["seconds"] = time.monotonic() - started
    try:
        records = [json.loads(line) for line in result.get("stdout", "").splitlines()]
    except json.JSONDecodeError as error:
        records = []
        result["parse_error"] = str(error)
    result["observations"] = records
    pipes = {row["namespace"]: row for row in records if row.get("stage") == "named_pipe"}
    result["comparison"] = {
        "legacy": pipes.get("libreoffice_legacy"),
        "local": pipes.get("appcontainer_local"),
        "supports_namespace_hypothesis": (
            pipes.get("libreoffice_legacy", {}).get("ok") is False
            and pipes.get("appcontainer_local", {}).get("ok") is True
        ),
    }
    checks = {
        "child_finished": result.get("exit_code") == 0
                          and any(row.get("stage") == "complete" for row in records),
        "native_lpac_job": observed_native_boundary(
            result.get("process_observation", {}), result.get("worker_pid")),
        "job_empty": result.get("job_after_communication", {}).get("query_ok") is True
                     and result.get("job_after_communication", {}).get("active_processes") == 0,
        "network_denied": any(row.get("stage") == "network_probe"
                              and row.get("denied") is True for row in records),
        "both_probes_observed": set(pipes) == {"libreoffice_legacy", "appcontainer_local"},
        "context_closed": result.get("job_context_closed") is True,
    }
    result["diagnostic_checks"] = checks
    result["diagnostic_completed"] = all(checks.values())
    (output / "probe.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["diagnostic_completed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
