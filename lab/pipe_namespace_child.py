"""Probe two ephemeral Windows named-pipe namespaces inside original LPAC/Job.

No Writer launch, no ACL edits, no extra capabilities, no process memory.
The native boundary is imported directly from the immutable Nexus package.
"""
import ctypes as C
from ctypes import wintypes as W
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys


def emit(stage, **values):
    print(json.dumps({"stage": stage, **values}, sort_keys=True), flush=True)


def require_boundary(path):
    package_root = Path(path)
    if not package_root.is_absolute() or package_root.name != "nexus":
        raise ValueError("Expected exact Nexus package path")
    spec = importlib.util.spec_from_file_location(
        "nexus", package_root / "__init__.py",
        submodule_search_locations=[str(package_root)])
    package = importlib.util.module_from_spec(spec)
    sys.modules["nexus"] = package
    spec.loader.exec_module(package)
    from nexus.windows_sandbox import require_native_boundary
    require_native_boundary()


def create_one_pipe(kernel, path):
    C.set_last_error(0)
    # Null SECURITY_ATTRIBUTES: the Windows default for the already restricted
    # per-task token. Do not create a permissive DACL.
    handle = kernel.CreateNamedPipeW(
        path, 0x00000003 | 0x40000000, 0x00000004 | 0x00000002,
        1, 4096, 4096, 0, None)
    invalid = C.c_void_p(-1).value
    ok = handle not in (None, 0, invalid)
    record = {"path": path, "ok": bool(ok),
              "winerror": 0 if ok else C.get_last_error()}
    if ok:
        record["closed"] = bool(kernel.CloseHandle(handle))
    return record


def main():
    if os.name != "nt" or C.sizeof(C.c_void_p) != 8 or len(sys.argv) != 4:
        raise RuntimeError("Only 64-bit Windows and three explicit arguments")
    require_boundary(sys.argv[1])
    name = sys.argv[2]
    if len(name) != 32 or any(char not in "0123456789abcdef" for char in name):
        raise ValueError("Expected 128-bit random synthetic name")
    port = int(sys.argv[3])
    emit("native_boundary_verified", acl_changes=False, writer_executed=False,
         process_memory_read=False)
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1):
            emit("network_probe", denied=False, detail="unexpected_connect")
            return 2
    except OSError as error:
        blocked = getattr(error, "winerror", None) == 10013
        emit("network_probe", denied=blocked,
             winerror=getattr(error, "winerror", None))
        if not blocked:
            return 3

    kernel = C.WinDLL("kernel32", use_last_error=True)
    kernel.CreateNamedPipeW.argtypes = [
        W.LPCWSTR, W.DWORD, W.DWORD, W.DWORD, W.DWORD,
        W.DWORD, W.DWORD, C.c_void_p]
    kernel.CreateNamedPipeW.restype = W.HANDLE
    kernel.CloseHandle.argtypes = [W.HANDLE]
    kernel.CloseHandle.restype = W.BOOL
    for label, prefix in (
        ("libreoffice_legacy", "\\\\.\\pipe\\"),
        ("appcontainer_local", "\\\\.\\pipe\\LOCAL\\"),
    ):
        emit("named_pipe", namespace=label,
             **create_one_pipe(kernel, prefix + "NexusWriterProbe-" + name))
    emit("complete", writer_executed=False, acl_changes=False,
         profile_changed=False, tool_installed=False)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        emit("error", type=type(error).__name__, message=str(error))
        raise SystemExit(1)
