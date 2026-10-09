"""Resolve recorded Writer return addresses from local PE/PDB files only.

No Writer launch, attach, process-memory read or dump. Run this external helper
after the real routes exit, with a caller-enforced 120-second process deadline.
DbgHelp receives only this helper's own process handle with invade=False.
"""

import argparse
import base64
import ctypes as C
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import time
import uuid

if __package__:
    from .fetch_writer_symbols import expected_identity, pdb_identity, validate_identity
    from .pe_debug_info import codeview
else:
    from fetch_writer_symbols import expected_identity, pdb_identity, validate_identity
    from pe_debug_info import codeview


HEX = r"[0-9a-fA-F`]+"
MODULE = re.compile(rf"^\s*({HEX})\s+({HEX})\s+mergedlo\s+", re.I)
FRAME = re.compile(rf"^\s*({HEX})\s+({HEX})\s+(.+?)\s*$")
THREAD = re.compile(r"^\s*\.?\s*(\d+)\s+Id:\s+([^\s]+)")
MAX_STACK_BYTES = 4 * 1024**2
MAX_STACK_FILES = 16
MAX_FRAME_RECORDS = 1024
MAX_UNIQUE_RVAS = 256
SYMOPT_UNDNAME = 0x00000002
SYMOPT_LOAD_LINES = 0x00000010
SYMOPT_FAIL_CRITICAL_ERRORS = 0x00000200
SYMOPT_EXACT_SYMBOLS = 0x00000400
SYMOPT_IGNORE_NT_SYMPATH = 0x00001000
SYMOPT_NO_PROMPTS = 0x00080000
SYMOPT_IGNORE_IMAGEDIR = 0x00200000
SYMOPT_DISABLE_SYMSRV_AUTODETECT = 0x02000000


def number(value):
    return int(value.replace("`", ""), 16)


def symbol_location_quality(displacement, size):
    if not size:
        return None, "nearest_symbol_extent_unknown"
    if displacement < size:
        return True, "within_reported_symbol_extent"
    return False, "nearest_symbol_outside_reported_extent"


def parse_stack(text):
    """Keep lm module bounds and frame return addresses as distinct records."""
    modules = [tuple(number(value) for value in match.groups())
               for line in text.splitlines() if (match := MODULE.match(line))]
    bounds = sorted(set(modules))
    if len(bounds) != 1 or bounds[0][1] <= bounds[0][0]:
        raise ValueError("Expected one unambiguous mergedlo lm address range")
    start, end = bounds[0]
    rows = []
    thread = None
    in_frames = False
    frame_index = 0
    for line in text.splitlines():
        if match := THREAD.match(line):
            thread = {"index": int(match[1]), "id": match[2]}
            in_frames = False
            continue
        if "Child-SP" in line and "RetAddr" in line:
            in_frames = True
            frame_index = 0
            continue
        if not in_frames:
            continue
        match = FRAME.match(line)
        if not match:
            in_frames = False
            continue
        address = number(match[2])
        if start <= address < end:
            rows.append({
                "thread": thread, "frame_index": frame_index,
                "return_address": f"0x{address:x}",
                "rva": address - start,
                "original_frame_callsite_label": match[3],
                "label_note": "Original label describes this row's current frame; RetAddr belongs to its caller.",
            })
        frame_index += 1
    if len(rows) > MAX_FRAME_RECORDS:
        raise ValueError("Excessive recorded mergedlo frame count")
    return {"module_base": start, "module_end": end, "frames": rows}


def parsing_controls():
    sample = """.  0  Id: 1234.5678 Suspend: 0
Child-SP          RetAddr               Call Site
00000000`00001000 00000000`10000042     other!OriginalLabel+0x2
00000000`00001020 00000000`00000000     mergedlo!ApproximateExport+0x42

00000000`10000000 00000000`10001000   mergedlo   (export symbols) fixture\\mergedlo.dll
"""
    parsed = parse_stack(sample)
    assert parsed["module_base"] == 0x10000000
    assert len(parsed["frames"]) == 1
    assert parsed["frames"][0]["rva"] == 0x42
    assert parsed["frames"][0]["original_frame_callsite_label"].startswith("other!")
    try:
        parse_stack(sample + "00000000`20000000 00000000`20001000   mergedlo (deferred)\n")
    except ValueError:
        pass
    else:
        raise AssertionError("Conflicting module bases were accepted")
    assert symbol_location_quality(15, 16) == (True, "within_reported_symbol_extent")
    assert symbol_location_quality(16, 16) == (False, "nearest_symbol_outside_reported_extent")
    assert symbol_location_quality(0, 0) == (None, "nearest_symbol_extent_unknown")
    assert C.sizeof(IMAGEHLP_MODULE64) == 1680
    assert C.sizeof(SYMBOL_INFO) == 88 and SYMBOL_INFO.Name.offset == 84
    assert C.sizeof(IMAGEHLP_LINE64) == 40
    return {"return_address_rva": "PASS", "row_label_not_reinterpreted": "PASS",
            "conflicting_module_bases_refused": "PASS", "nearest_symbol_quality": "PASS",
            "amd64_native_structure_layouts": "PASS", "native_calls": False}


def read_json(path, maximum=1024**2):
    if path.stat().st_size > maximum:
        raise ValueError("Excessive metadata JSON")
    raw = path.read_bytes()
    if len(raw) > maximum:
        raise ValueError("Excessive metadata JSON")
    return json.loads(raw.decode("utf-8-sig")), hashlib.sha256(raw).hexdigest()


def hash_file(path, deadline):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024**2), b""):
            if time.monotonic() > deadline:
                raise TimeoutError("Offline metadata-hash deadline reached")
            digest.update(chunk)
    return digest.hexdigest()


def image_size(path):
    with path.open("rb") as stream:
        dos = stream.read(64)
        if len(dos) != 64 or dos[:2] != b"MZ":
            raise ValueError("Not a PE image")
        offset = struct.unpack_from("<I", dos, 0x3c)[0]
        if not 64 <= offset <= 1024**2:
            raise ValueError("Invalid PE header offset")
        stream.seek(offset)
        header = stream.read(24 + 64)
        if len(header) != 88 or header[:4] != b"PE\0\0":
            raise ValueError("Invalid PE header")
        if struct.unpack_from("<H", header, 4)[0] != 0x8664:
            raise ValueError("Only the exact AMD64 Writer fixture is supported")
        if struct.unpack_from("<H", header, 24)[0] != 0x20b:
            raise ValueError("Expected PE32+ optional header")
        size = struct.unpack_from("<I", header, 24 + 56)[0]
        if not 0 < size < 1024**3:
            raise ValueError("Invalid PE SizeOfImage")
        return size


def verified_inputs(args, deadline):
    metadata, metadata_hash = read_json(args.metadata)
    report, _ = read_json(args.symbols_report)
    if not isinstance(metadata, list) or not all(isinstance(entry, dict) for entry in metadata):
        raise ValueError("Expected a PE metadata array of module objects")
    if not isinstance(report, dict) or not isinstance(report.get("modules"), list):
        raise ValueError("Expected a symbol report with a module array")
    if not all(isinstance(entry, dict) for entry in report["modules"]):
        raise ValueError("Expected symbol module objects")
    if report.get("all_selected_verified") is not True or report.get("metadata_sha256") != metadata_hash:
        raise ValueError("Symbol report is not verified for these exact PE metadata bytes")
    modules = [entry for entry in metadata if entry.get("image") == "mergedlo.dll"]
    symbols = [entry for entry in report.get("modules", []) if entry.get("image") == "mergedlo.dll"]
    if len(modules) != 1 or len(symbols) != 1 or symbols[0].get("status") != "verified":
        raise ValueError("Expected one verified mergedlo PE/PDB pair")
    expected = expected_identity(modules[0])
    installed_image = (Path(os.environ["LIBREOFFICE_EXE"]).parent / "mergedlo.dll").resolve(strict=True)
    image = (args.image or installed_image).resolve(strict=True)
    if image != installed_image or image.name.lower() != "mergedlo.dll" or not image.is_file():
        raise ValueError("Only the installed mergedlo.dll fixture is supported")
    actual_image = codeview(image)
    if actual_image["sha256"] != modules[0]["sha256"] or expected_identity(actual_image) != expected:
        raise ValueError("Actual installed PE differs from the recorded fixture")
    if symbols[0].get("image_sha256") != actual_image["sha256"]:
        raise ValueError("Symbol report refers to another PE hash")
    temporary_root = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    pdb = Path(symbols[0]["verified_file"]).resolve(strict=True)
    if not pdb.is_relative_to(temporary_root) or pdb.name.casefold() != expected["pdb_name"].casefold():
        raise ValueError("Verified PDB escaped RUNNER_TEMP or has another basename")
    if pdb.stat().st_size != symbols[0].get("pdb_bytes"):
        raise ValueError("Verified PDB size changed")
    pdb_hash = hash_file(pdb, deadline)
    if pdb_hash != symbols[0].get("pdb_sha256"):
        raise ValueError("Verified PDB bytes changed")
    actual_pdb = pdb_identity(pdb)
    binding = validate_identity(actual_pdb, expected)
    return {"image": image, "image_sha256": actual_image["sha256"], "image_size": image_size(image),
            "pdb": pdb, "pdb_sha256": pdb_hash, "expected": expected,
            "pdb_identity": actual_pdb, "pdb_binding": binding}


DWORD = C.c_uint32
DWORD64 = C.c_uint64
BOOL = C.c_int32


class GUID(C.Structure):
    _fields_ = [("Data1", DWORD), ("Data2", C.c_uint16), ("Data3", C.c_uint16), ("Data4", C.c_ubyte * 8)]


class IMAGEHLP_MODULE64(C.Structure):
    _fields_ = [("SizeOfStruct", DWORD), ("BaseOfImage", DWORD64), ("ImageSize", DWORD),
                ("TimeDateStamp", DWORD), ("CheckSum", DWORD), ("NumSyms", DWORD), ("SymType", C.c_int32),
                ("ModuleName", C.c_char * 32), ("ImageName", C.c_char * 256),
                ("LoadedImageName", C.c_char * 256), ("LoadedPdbName", C.c_char * 256),
                ("CVSig", DWORD), ("CVData", C.c_char * 780), ("PdbSig", DWORD), ("PdbSig70", GUID),
                ("PdbAge", DWORD), ("PdbUnmatched", BOOL), ("DbgUnmatched", BOOL),
                ("LineNumbers", BOOL), ("GlobalSymbols", BOOL), ("TypeInfo", BOOL),
                ("SourceIndexed", BOOL), ("Publics", BOOL), ("MachineType", DWORD), ("Reserved", DWORD)]


class SYMBOL_INFO(C.Structure):
    _fields_ = [("SizeOfStruct", DWORD), ("TypeIndex", DWORD), ("Reserved", DWORD64 * 2),
                ("Index", DWORD), ("Size", DWORD), ("ModBase", DWORD64), ("Flags", DWORD),
                ("Value", DWORD64), ("Address", DWORD64), ("Register", DWORD), ("Scope", DWORD),
                ("Tag", DWORD), ("NameLen", DWORD), ("MaxNameLen", DWORD), ("Name", C.c_char * 1)]


class IMAGEHLP_LINE64(C.Structure):
    _fields_ = [("SizeOfStruct", DWORD), ("Key", C.c_void_p), ("LineNumber", DWORD),
                ("FileName", C.c_char_p), ("Address", DWORD64)]


def microsoft_dbghelp(args, deadline):
    """Use the Microsoft-signed SDK DbgHelp already verified by the lab setup.

    install-stack-tools.ps1 verifies Authenticode and records path/hash/status in
    lab-evidence/stack-tools/signatures.jsonl. Reuse that evidence here instead
    of launching a second nested PowerShell verifier with different quoting/
    execution semantics.
    """
    cdb = Path(args.debugger or os.environ["LAB_CDB_EXE"]).resolve(strict=True)
    sdk = Path(os.environ.get("ProgramFiles(x86)", r"C:\\Program Files (x86)")) / "Windows Kits" / "10" / "Debuggers" / "x64"
    if cdb.parent != sdk.resolve(strict=True) or cdb.name.casefold() != "cdb.exe":
        raise ValueError("Expected the installed Windows SDK AMD64 CDB directory")
    dll = (cdb.parent / "dbghelp.dll").resolve(strict=True)

    evidence_path = Path("lab-evidence/stack-tools/signatures.jsonl")
    if not evidence_path.is_file():
        raise ValueError("Missing prior Authenticode evidence for SDK DbgHelp")
    if evidence_path.stat().st_size > 1024 * 1024:
        raise ValueError("Excessive Authenticode evidence file")

    rows = []
    for raw in evidence_path.read_text(encoding="utf-8-sig").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        row = json.loads(raw)
        if not isinstance(row, dict):
            raise ValueError("Invalid Authenticode evidence record")
        rows.append(row)

    matches = []
    for row in rows:
        try:
            recorded = Path(str(row.get("path", ""))).resolve(strict=True)
        except (OSError, RuntimeError, ValueError):
            continue
        if recorded == dll:
            matches.append(row)
    if len(matches) != 1:
        raise ValueError("Expected exactly one Authenticode record for SDK DbgHelp")

    signature = matches[0]
    if signature.get("status") != "Valid" or "Microsoft Corporation" not in str(signature.get("subject", "")):
        raise ValueError("SDK DbgHelp signature is not valid Microsoft")
    expected_hash = str(signature.get("sha256", "")).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise ValueError("Invalid recorded SDK DbgHelp SHA-256")
    actual_hash = hash_file(dll, deadline)
    if actual_hash.lower() != expected_hash:
        raise ValueError("SDK DbgHelp bytes changed after Authenticode verification")

    return dll, {
        "status": signature["status"],
        "subject": signature["subject"],
        "sha256": expected_hash,
        "evidence": str(evidence_path),
        "reused_preverified_authenticode": True,
    }


class OfflineSymbols:
    def __init__(self, dll, inputs):
        self.inputs = inputs
        self.dll = C.WinDLL(str(dll), use_last_error=True)
        self.kernel = C.WinDLL("kernel32.dll", use_last_error=True)
        self.kernel.GetCurrentProcess.restype = C.c_void_p
        self.handle = self.kernel.GetCurrentProcess()
        self._declare("SymSetOptions", DWORD, [DWORD])
        self._declare("SymInitializeW", BOOL, [C.c_void_p, C.c_wchar_p, BOOL])
        self._declare("SymLoadModuleExW", DWORD64, [C.c_void_p, C.c_void_p, C.c_wchar_p, C.c_wchar_p, DWORD64, DWORD, C.c_void_p, DWORD])
        self._declare("SymGetModuleInfo64", BOOL, [C.c_void_p, DWORD64, C.POINTER(IMAGEHLP_MODULE64)])
        self._declare("SymFromAddr", BOOL, [C.c_void_p, DWORD64, C.POINTER(DWORD64), C.POINTER(SYMBOL_INFO)])
        self._declare("SymGetLineFromAddr64", BOOL, [C.c_void_p, DWORD64, C.POINTER(DWORD), C.POINTER(IMAGEHLP_LINE64)])
        self._declare("SymCleanup", BOOL, [C.c_void_p])
        self.initialized = False
        self.base = 0x10000000

    def _declare(self, name, result, arguments):
        function = getattr(self.dll, name)
        function.restype, function.argtypes = result, arguments

    def __enter__(self):
        # Exact matching, local explicit path, no symbol-server autodetection,
        # environment search path, image-directory search, prompts or export
        # fallback. Keep the real PE CodeView record enabled for validation.
        options = (SYMOPT_UNDNAME | SYMOPT_LOAD_LINES | SYMOPT_FAIL_CRITICAL_ERRORS
                   | SYMOPT_EXACT_SYMBOLS | SYMOPT_IGNORE_NT_SYMPATH
                   | SYMOPT_NO_PROMPTS | SYMOPT_IGNORE_IMAGEDIR
                   | SYMOPT_DISABLE_SYMSRV_AUTODETECT)
        self.options = int(self.dll.SymSetOptions(options))
        if self.options != options:
            raise ValueError("DbgHelp did not preserve the exact symbol-option policy")
        if not self.dll.SymInitializeW(self.handle, str(self.inputs["pdb"].parent), False):
            raise C.WinError(C.get_last_error())
        self.initialized = True
        try:
            loaded = self.dll.SymLoadModuleExW(self.handle, None, str(self.inputs["image"]), "mergedlo",
                                               self.base, self.inputs["image_size"], None, 0)
            if loaded != self.base:
                raise ValueError(f"DbgHelp did not load the recorded PE at the offline base: {C.get_last_error()}")
            info = IMAGEHLP_MODULE64(SizeOfStruct=C.sizeof(IMAGEHLP_MODULE64))
            if not self.dll.SymGetModuleInfo64(self.handle, self.base, C.byref(info)):
                raise C.WinError(C.get_last_error())
            guid = str(uuid.UUID(bytes_le=C.string_at(C.addressof(info.PdbSig70), 16)))
            loaded_pdb = bytes(info.LoadedPdbName).decode("mbcs", errors="strict")
            if info.SymType != 3 or info.PdbUnmatched or info.DbgUnmatched:
                raise ValueError("DbgHelp did not confirm matched SymPdb symbols")
            if guid != self.inputs["expected"]["guid"] or info.PdbAge != self.inputs["expected"]["age"]:
                raise ValueError("DbgHelp PDB GUID/age disagrees with the verified binding")
            if info.BaseOfImage != self.base or info.ImageSize != self.inputs["image_size"]:
                raise ValueError("DbgHelp module range differs from the exact PE image")
            if Path(loaded_pdb).resolve(strict=True) != self.inputs["pdb"]:
                raise ValueError("DbgHelp loaded another PDB file")
            self.module = {"sym_type": int(info.SymType), "pdb_unmatched": bool(info.PdbUnmatched),
                           "dbg_unmatched": bool(info.DbgUnmatched), "pdb_guid": guid, "pdb_age": int(info.PdbAge),
                           "loaded_pdb": loaded_pdb, "module_base": f"0x{self.base:x}",
                           "image_size": int(info.ImageSize), "line_numbers": bool(info.LineNumbers),
                           "options": f"0x{self.options:x}", "exact_symbols": True, "invade_process": False}
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        if self.initialized:
            self.dll.SymCleanup(self.handle)
            self.initialized = False

    def resolve(self, rva):
        result = {"rva": rva, "offline_address": f"0x{self.base + rva:x}"}
        storage = C.create_string_buffer(C.sizeof(SYMBOL_INFO) + 2048)
        symbol = C.cast(storage, C.POINTER(SYMBOL_INFO))
        symbol.contents.SizeOfStruct = C.sizeof(SYMBOL_INFO)
        symbol.contents.MaxNameLen = 2048
        displacement = DWORD64()
        if not self.dll.SymFromAddr(self.handle, self.base + rva, C.byref(displacement), symbol):
            result.update(status="unresolved", winerror=C.get_last_error())
            return result
        info = symbol.contents
        if not 0 < info.NameLen <= 2048 or info.ModBase != self.base:
            raise ValueError("Invalid or unexpected DbgHelp symbol record")
        symbol_rva = int(info.Address) - self.base
        if not 0 <= symbol_rva < self.inputs["image_size"] or symbol_rva + displacement.value != rva:
            raise ValueError("DbgHelp symbol/displacement is inconsistent with the recorded address")
        name = C.string_at(C.addressof(storage) + SYMBOL_INFO.Name.offset, info.NameLen).decode("utf-8", errors="replace")
        contains_address, quality = symbol_location_quality(int(displacement.value), int(info.Size))
        result.update(status="resolved", actual_symbol=name, symbol_rva=symbol_rva,
                      displacement=int(displacement.value), symbol_tag=int(info.Tag), symbol_size=int(info.Size),
                      within_reported_symbol_size=contains_address, symbol_location_quality=quality,
                      function_identity_claimed=False)
        line = IMAGEHLP_LINE64(SizeOfStruct=C.sizeof(IMAGEHLP_LINE64))
        line_displacement = DWORD()
        if self.dll.SymGetLineFromAddr64(self.handle, self.base + rva, C.byref(line_displacement), C.byref(line)):
            result["source"] = {"file": line.FileName.decode("utf-8", errors="replace"),
                                "line": int(line.LineNumber), "displacement": int(line_displacement.value)}
        else:
            result["source_line_winerror"] = C.get_last_error()
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, default=Path("lab-evidence/pe-debug-info.json"))
    parser.add_argument("--symbols-report", type=Path, default=Path("lab-evidence/writer-symbols.json"))
    parser.add_argument("--stacks", type=Path, default=Path("lab-evidence/standard-user-launch/stacks"))
    parser.add_argument("--output", type=Path, default=Path("lab-evidence/resolved-writer-frames.json"))
    parser.add_argument("--image", type=Path)
    parser.add_argument("--debugger", type=Path)
    parser.add_argument("--self-check", action="store_true", help="Only synthetic text/structure checks; no native API or UI calls")
    args = parser.parse_args()
    if args.self_check:
        print(json.dumps(parsing_controls()))
        return 0
    if os.environ.get("GITHUB_ACTIONS") != "true" or sys.platform != "win32" or C.sizeof(C.c_void_p) != 8:
        raise SystemExit("Disposable AMD64 Windows GitHub runner only")
    started = time.monotonic()
    deadline = started + 110
    result = {"schema": "nexus.writer.offline-symbol-frames.v1", "utc": datetime.now(timezone.utc).isoformat(),
              "status": "in_progress", "stage": "validate_inputs", "memory_dump": False, "process_attach": False,
              "writer_executed": False, "process_memory_read": False, "runtime_changes": [],
              "caller_timeout_seconds": 120, "controls": parsing_controls(), "captures": []}
    def save_result():
        result["duration_seconds"] = round(time.monotonic() - started, 3)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        pending = args.output.with_name(args.output.name + ".pending")
        pending.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(pending, args.output)

    save_result()
    exit_code = 2
    try:
        inputs = verified_inputs(args, deadline)
        dll, signature = microsoft_dbghelp(args, deadline)
        result["inputs"] = {key: str(value) if isinstance(value, Path) else value for key, value in inputs.items()}
        result["dbghelp"] = {"path": str(dll), "signature": signature, "sha256": hash_file(dll, deadline)}
        result["stage"] = "parse_recorded_stacks"
        save_result()
        stack_files = sorted(args.stacks.glob("*.stacks.txt")) if args.stacks.is_dir() else [args.stacks]
        if not 1 <= len(stack_files) <= MAX_STACK_FILES:
            raise ValueError("Expected 1 to 16 recorded stack text files")
        rvas = set()
        for path in stack_files:
            raw = path.read_bytes()
            if len(raw) > MAX_STACK_BYTES:
                raise ValueError("Excessive stack text file")
            try:
                capture = parse_stack(raw.decode("utf-8-sig", errors="strict"))
                if capture["module_end"] - capture["module_base"] != inputs["image_size"]:
                    raise ValueError("Recorded lm range differs from the exact PE SizeOfImage")
                rvas.update(row["rva"] for row in capture["frames"])
                capture.update(file=str(path), sha256=hashlib.sha256(raw).hexdigest())
                result["captures"].append(capture)
            except ValueError as error:
                result["captures"].append({"file": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "error": str(error)})
        if not rvas or len(rvas) > MAX_UNIQUE_RVAS:
            raise ValueError("Expected 1 to 256 unique mergedlo return-address RVAs")
        resolved = {}
        result["stage"] = "load_matching_symbols"
        save_result()
        with OfflineSymbols(dll, inputs) as symbols:
            result["matched_module"] = symbols.module
            result["stage"] = "resolve_return_addresses"
            result["partial_resolutions"] = {}
            save_result()
            for rva in sorted(rvas):
                if time.monotonic() > deadline:
                    raise TimeoutError("Offline symbol lookup deadline reached")
                resolved[rva] = {"return_address_location": symbols.resolve(rva),
                                 "preceding_instruction_location": symbols.resolve(rva - 1) if rva else None}
                result["partial_resolutions"][f"0x{rva:x}"] = resolved[rva]
                save_result()
        for capture in result["captures"]:
            for row in capture.get("frames", []):
                row["offline_resolution"] = resolved[row["rva"]]
        count = sum(value["return_address_location"]["status"] == "resolved" for value in resolved.values())
        result["unique_rvas"] = len(rvas)
        result["resolved_unique_rvas"] = count
        result["symbol_extent_contains_unique_rvas"] = sum(
            value["return_address_location"].get("within_reported_symbol_size") is True
            for value in resolved.values())
        result["status"] = "resolved" if count else "unresolved"
        result["stage"] = "finished"
        del result["partial_resolutions"]
        exit_code = 0 if count else 2
    except (OSError, ValueError, KeyError, TypeError, struct.error, subprocess.SubprocessError) as error:
        result.update(status="error", error_type=type(error).__name__, error=str(error)[:3000])
    finally:
        save_result()
    print(json.dumps({"report": str(args.output), "status": result["status"],
                      "resolved_unique_rvas": result.get("resolved_unique_rvas", 0)}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
