"""Produce an OFFLINE source-only LibreOffice named-pipe LPAC prototype.

This never patches an installed binary or runs Writer. Input is an already
obtained upstream sal/osl/w32/pipe.cxx source; output must be a NEW path.
The caller must separately compile, verify identity and run the real routes.
"""
import argparse
import hashlib
import json
from pathlib import Path


SOURCE_TOKEN = '    rtl_uString_newFromAscii(&path, PIPESYSTEM);'
PROTOTYPE = r'''    // EXPERIMENTAL: AppContainer named pipes require the session-local
    // LOCAL namespace; keep the existing path for normal Windows processes.
    // Self-token query only; never grant access or change a DACL.
    rtl_uString_newFromAscii(&path, PIPESYSTEM);
    HANDLE nexusPipeSelfToken = nullptr;
    if (OpenProcessToken(GetCurrentProcess(), TOKEN_QUERY, &nexusPipeSelfToken))
    {
        DWORD nexusAppContainer = 0;
        DWORD nexusReturnSize = 0;
        if (GetTokenInformation(nexusPipeSelfToken, TokenIsAppContainer,
                                &nexusAppContainer, sizeof(nexusAppContainer),
                                &nexusReturnSize)
            && nexusAppContainer != 0)
        {
            rtl_uString_newFromAscii(&path, "\\\\.\\pipe\\LOCAL\\");
        }
        CloseHandle(nexusPipeSelfToken);
    }'''


def patch_source(source: str) -> str:
    if not source.startswith("/* -*- Mode: C++") or source.count(SOURCE_TOKEN) != 1:
        raise ValueError("LibreOffice Windows pipe source does not match baseline")
    if "sal/osl/w32" in source[:60] or "CreateNamedPipeW(" not in source:
        raise ValueError("Incorrect Windows named pipe implementation")
    if '#define PIPESYSTEM' not in source or "PIPEPREFIX" not in source:
        raise ValueError("Unexpected source constants")
    if "NEXUS_TEST" in source or "nexusPipeSelfToken" in source:
        raise ValueError("Source already modified")
    if source.count("WaitNamedPipeW(") != 1:
        raise ValueError("Expected original named pipe open path")
    output = source.replace(SOURCE_TOKEN, PROTOTYPE)
    if output.count("nexusPipeSelfToken") != 4:
        raise ValueError("Unexpected prototype structure")
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        raise SystemExit("Never modify an original LibreOffice source file in place")
    if args.output.exists() or args.source.is_symlink():
        raise SystemExit("Refusing overwrite or a symlink")
    raw = args.source.read_bytes()
    if len(raw) > 1024 * 1024 or not raw:
        raise SystemExit("Source outside bounded size")
    text = raw.decode("utf-8")
    patched = patch_source(text).encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(patched)
    print(json.dumps({
        "status": "SOURCE_PROTOTYPE_ONLY",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "output_sha256": hashlib.sha256(patched).hexdigest(),
        "bytes_added": len(patched) - len(raw),
        "source_modified": False,
        "installed_binary_modified": False,
        "writer_execution": "NOT_RUN",
        "security_changes": [],
        "known_requirement": "Compile the exact upstream revision and prove both Writer routes in real LPAC",
    }, sort_keys=True))


if __name__ == "__main__":
    main()
