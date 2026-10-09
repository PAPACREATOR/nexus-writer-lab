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
MAX_RVA_EVENTS = 64
MAX_RVA_INPUT_BYTES = 4 * 1024**2
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


def parse_rva_event_document(document, exact_image_size):
    """Validate persisted Procmon offsets without inventing a CDB capture."""
    if not isinstance(document, dict) or document.get("schema") != "nexus.writer.persisted-procmon-rvas.v1":
        raise ValueError("Expected a persisted Procmon RVA document")
    for key in ("source", "filtered_source"):
        reference = document.get(key)
        if key == "filtered_source" and reference is None:
            continue
        if not isinstance(reference, dict) or not isinstance(reference.get("path"), str) or not reference["path"]:
            raise ValueError("Expected a nonempty persisted source path")
        if not isinstance(reference.get("sha256"), str) or not re.fullmatch(r"[0-9a-fA-F]{64}", reference["sha256"]):
            raise ValueError("Expected a SHA256 for each persisted source reference")
    records = document.get("records")
    if not isinstance(records, list) or not 1 <= len(records) <= MAX_FRAME_RECORDS:
        raise ValueError("Expected 1 to 1024 persisted Procmon frame records")
    events, rvas = set(), set()
    for record in records:
        if not isinstance(record, dict) or record.get("module") != "mergedlo.dll":
            raise ValueError("Only persisted mergedlo.dll offsets are supported")
        rva = record.get("rva")
        if type(rva) is not int or not 0 <= rva < exact_image_size:
            raise ValueError("Persisted RVA is not an integer within the exact PE SizeOfImage")
        provenance = record.get("provenance")
        if not isinstance(provenance, dict) or type(provenance.get("pid")) is not int or provenance["pid"] <= 0:
            raise ValueError("Expected persisted event PID provenance")
        for key in ("event_time", "path", "result"):
            if not isinstance(provenance.get(key), str) or not provenance[key]:
                raise ValueError("Expected persisted event time/path/result provenance")
        original = record.get("original_stack_text")
        if not isinstance(original, str) or not original:
            raise ValueError("Expected the original persisted stack text")
        offset_pattern = r"\bmergedlo\.dll\s*\+\s*0x0*" + format(rva, "x") + r"\b"
        if not re.search(offset_pattern, original, re.I):
            raise ValueError("Persisted RVA does not occur in its original mergedlo stack text")
        events.add((provenance["pid"], provenance["event_time"], provenance["path"],
                    provenance.get("operation", ""), provenance["result"]))
        rvas.add(rva)
    if len(events) > MAX_RVA_EVENTS or len(rvas) > MAX_UNIQUE_RVAS:
        raise ValueError("Persisted Procmon input exceeds 64 events or 256 unique RVAs")
    return {"referenced_source": document["source"],
            "referenced_filtered_source": document.get("filtered_source"),
            "reference_verification": "Persisted extraction references preserved; input JSON independently hashed; original XML not reopened",
            "address_semantics": "Procmon recorded module RVA itself; no RetAddr or preceding-instruction inference",
            "event_count": len(events), "records": records}, rvas


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
    document = {"schema": "nexus.writer.persisted-procmon-rvas.v1",
                "source": {"path": "synthetic.xml", "sha256": "a" * 64},
                "records": [{"module": "mergedlo.dll", "rva": 42,
                             "provenance": {"pid": 123, "event_time": "synthetic", "path": "synthetic", "result": "ACCESS DENIED"},
                             "original_stack_text": "0: mergedlo.dll + 0x2a"}]}
    direct, rvas = parse_rva_event_document(document, 4096)
    assert rvas == {42} and direct["records"][0]["rva"] == 42
    document["records"][0]["rva"] = 4096
    try:
        parse_rva_event_document(document, 4096)
    except ValueError:
        pass
    else:
        raise AssertionError("An RVA outside the exact image was accepted")
    document["records"][0]["rva"] = True
    try:
        parse_rva_event_document(document, 4096)
    except ValueError:
        pass
    else:
        raise AssertionError("A boolean RVA was accepted as an integer")
    return {"return_address_rva": "PASS", "row_label_not_reinterpreted": "PASS",
            "conflicting_module_bases_refused": "PASS", "nearest_symbol_quality": "PASS",
            "amd64_native_structure_layouts": "PASS", "persisted_rva_input_validation": "PASS",
            "persisted_rva_not_adjusted": "PASS", "native_calls": False}


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


class SignatureProbeError(ValueError):
    def __init__(self, message, diagnostics):
        super().__init__(message)
        self.diagnostics = diagnostics


def signature_probe(path):
    """Read an Authenticode signature in an isolated Windows PowerShell child.

    pwsh -> Python -> Windows PowerShell otherwise inherits incompatible pwsh
    modules. Remove only the child's PSModulePath, as Microsoft documents:
    https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_psmodulepath#starting-windows-powershell-from-powershell-7
    Also import the two built-in modules by absolute PSHOME paths.
    """
    powershell = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    quoted = str(path).replace("'", "''")
    script = (
        "$ErrorActionPreference='Stop';$ProgressPreference='SilentlyContinue';"
        "Import-Module ($PSHOME+'\\Modules\\Microsoft.PowerShell.Security\\Microsoft.PowerShell.Security.psd1') -ErrorAction Stop;"
        "Import-Module ($PSHOME+'\\Modules\\Microsoft.PowerShell.Utility\\Microsoft.PowerShell.Utility.psd1') -ErrorAction Stop;"
        "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new($false);"
        "$s=Microsoft.PowerShell.Security\\Get-AuthenticodeSignature -LiteralPath '" + quoted + "';"
        "@{status=$s.Status.ToString();subject=$s.SignerCertificate.Subject;"
        "powershell_version=$PSVersionTable.PSVersion.ToString()}|Microsoft.PowerShell.Utility\\ConvertTo-Json -Compress"
    )
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    child_environment = {key: value for key, value in os.environ.items() if key.upper() != "PSMODULEPATH"}
    diagnostics = {"powershell": str(powershell), "file": str(path), "timeout_seconds": 15,
                   "module_path_policy": "remove inherited PSModulePath in child only; absolute built-in module imports",
                   "signature_requirement": "Valid and Microsoft Corporation", "exit_code": None}

    def keep_output(stdout, stderr):
        for key, raw in (("stdout", stdout), ("stderr", stderr)):
            decoded = raw.decode("utf-8-sig", errors="replace") if isinstance(raw, bytes) else (raw or "")
            diagnostics[key] = decoded[:4096]
            diagnostics[key + "_truncated"] = len(decoded) > 4096

    try:
        completed = subprocess.run([str(powershell), "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                                   capture_output=True, timeout=15, check=False, env=child_environment,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
    except subprocess.TimeoutExpired as error:
        keep_output(error.stdout, error.stderr)
        diagnostics["timed_out"] = True
        raise SignatureProbeError("Windows PowerShell Authenticode probe timed out", diagnostics) from error
    except OSError as error:
        diagnostics["launch_error"] = str(error)[:4096]
        raise SignatureProbeError("Unable to launch Windows PowerShell Authenticode probe", diagnostics) from error
    diagnostics["exit_code"] = completed.returncode
    keep_output(completed.stdout, completed.stderr)
    if completed.returncode != 0:
        raise SignatureProbeError("Windows PowerShell Authenticode probe failed with exit " + str(completed.returncode), diagnostics)
    try:
        signature = json.loads(completed.stdout.decode("utf-8-sig"))
        if not isinstance(signature, dict):
            raise ValueError("Expected an Authenticode result object")
    except (UnicodeError, ValueError) as error:
        raise SignatureProbeError("Windows PowerShell returned invalid Authenticode JSON", diagnostics) from error
    signature["probe"] = diagnostics
    return signature


def microsoft_dbghelp(args):
    cdb = Path(args.debugger or os.environ["LAB_CDB_EXE"]).resolve(strict=True)
    sdk = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Windows Kits" / "10" / "Debuggers" / "x64"
    if cdb.parent != sdk.resolve(strict=True) or cdb.name.casefold() != "cdb.exe":
        raise ValueError("Expected the installed Windows SDK AMD64 CDB directory")
    dll = (cdb.parent / "dbghelp.dll").resolve(strict=True)
    signature = signature_probe(dll)
    if signature.get("status") != "Valid" or "Microsoft Corporation" not in signature.get("subject", ""):
        raise SignatureProbeError("SDK DbgHelp signature is not valid Microsoft", signature["probe"])
    return dll, signature


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
                raise ValueError("DbgHelp did not confirm matched SymPdb symbols: "
                                 f"SymType={info.SymType}, PdbUnmatched={bool(info.PdbUnmatched)}, "
                                 f"DbgUnmatched={bool(info.DbgUnmatched)}")
            if guid != self.inputs["expected"]["guid"] or info.PdbAge != self.inputs["expected"]["age"]:
                raise ValueError("DbgHelp PDB GUID/age disagrees with the verified binding: "
                                 f"GUID={guid}, PdbAge={info.PdbAge}, "
                                 f"image_age={self.inputs['expected']['age']}")
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
    parser.add_argument("--rva-events", type=Path, help="Use bounded persisted Procmon module-RVA JSON instead of CDB stack input")
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
        result["inputs"] = {key: str(value) if isinstance(value, Path) else value for key, value in inputs.items()}
        result["stage"] = "verify_dbghelp_signature"
        save_result()
        dll, signature = microsoft_dbghelp(args)
        result["dbghelp"] = {"path": str(dll), "signature": signature, "sha256": hash_file(dll, deadline)}
        if args.rva_events:
            result["stage"] = "parse_persisted_procmon_rvas"
            result["input_mode"] = "persisted_procmon_module_rvas"
            save_result()
            document, input_hash = read_json(args.rva_events, MAX_RVA_INPUT_BYTES)
            direct, rvas = parse_rva_event_document(document, inputs["image_size"])
            direct.update(input_file=str(args.rva_events), input_sha256=input_hash)
            result["rva_events"] = direct
            location_key = "recorded_stack_location"
        else:
            result["stage"] = "parse_recorded_stacks"
            result["input_mode"] = "cdb_return_addresses"
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
            location_key = "return_address_location"
        if not rvas or len(rvas) > MAX_UNIQUE_RVAS:
            raise ValueError("Expected 1 to 256 unique mergedlo return-address RVAs")
        resolved = {}
        result["stage"] = "load_matching_symbols"
        save_result()
        with OfflineSymbols(dll, inputs) as symbols:
            result["matched_module"] = symbols.module
            result["stage"] = "resolve_recorded_addresses"
            result["partial_resolutions"] = {}
            save_result()
            for rva in sorted(rvas):
                if time.monotonic() > deadline:
                    raise TimeoutError("Offline symbol lookup deadline reached")
                resolved[rva] = {location_key: symbols.resolve(rva)}
                if not args.rva_events:
                    resolved[rva]["preceding_instruction_location"] = symbols.resolve(rva - 1) if rva else None
                result["partial_resolutions"][f"0x{rva:x}"] = resolved[rva]
                save_result()
        for capture in result["captures"]:
            for row in capture.get("frames", []):
                row["offline_resolution"] = resolved[row["rva"]]
        for row in result.get("rva_events", {}).get("records", []):
            row["offline_resolution"] = resolved[row["rva"]]
        count = sum(value[location_key]["status"] == "resolved" for value in resolved.values())
        result["unique_rvas"] = len(rvas)
        result["resolved_unique_rvas"] = count
        result["symbol_extent_contains_unique_rvas"] = sum(
            value[location_key].get("within_reported_symbol_size") is True
            for value in resolved.values())
        result["status"] = "resolved" if count else "unresolved"
        result["stage"] = "finished"
        del result["partial_resolutions"]
        exit_code = 0 if count else 2
    except (OSError, ValueError, KeyError, TypeError, struct.error, subprocess.SubprocessError) as error:
        result.update(status="error", error_type=type(error).__name__, error=str(error)[:3000])
        if isinstance(error, SignatureProbeError):
            result["signature_probe"] = error.diagnostics
    finally:
        save_result()
    print(json.dumps({"report": str(args.output), "status": result["status"],
                      "resolved_unique_rvas": result.get("resolved_unique_rvas", 0)}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
