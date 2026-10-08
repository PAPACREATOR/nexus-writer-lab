"""Bounded document conversion through installed LibreOffice; no AI."""
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

if 'nexus' not in sys.modules:
    import importlib.util
    package_root = Path(__file__).absolute().parents[1]
    spec = importlib.util.spec_from_file_location('nexus', package_root / '__init__.py', submodule_search_locations=[str(package_root)])
    package = importlib.util.module_from_spec(spec)
    sys.modules['nexus'] = package
    spec.loader.exec_module(package)
from nexus.windows_sandbox import require_native_boundary
from nexus.contracts import Blocked, strict_json


def document_kind(raw):
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) > 2000 or sum(e.file_size for e in entries) > 20_000_000:
                raise Blocked("Documento demasiado complexo para este ensaio.")
            names = {e.filename for e in entries}
            if len(names) != len(entries):
                raise Blocked("Documento com entradas repetidas.")
            for entry in entries:
                raw_name = getattr(entry, "orig_filename", entry.filename)
                normalized_name = entry.filename
                posix = PurePosixPath(normalized_name)
                if ("\x00" in raw_name or "\\" in raw_name or raw_name.startswith("/")
                        or any(part == ".." for part in posix.parts)
                        or (posix.parts and ":" in posix.parts[0])):
                    raise Blocked("Caminho interno de documento não autorizado.")
                name = normalized_name.lower()
                if (any(word in name for word in ("vbaproject", "scripts/", "basic/", "embeddings/"))
                        or name.startswith("object ")
                        or name.startswith("objectreplacements/")):
                    raise Blocked("Conteúdo ativo ou objeto incorporado não permitido neste ensaio.")
                if name.endswith((".xml", ".rels")):
                    body = archive.read(entry).lower()
                    import re
                    if (any(word in body for word in (b'<!entity', b'<!doctype', b'<draw:object', b'<draw:object-ole'))
                            or re.search(rb'targetmode\s*=\s*[\x22\x27]external', body)
                            or re.search(rb'(?:xlink:href|href)\s*=\s*[\x22\x27](?:[a-z][a-z0-9+.-]*:|//|\\\\)', body)):
                        raise Blocked("Ligação externa ou objeto incorporado não permitido neste ensaio.")
            if "word/document.xml" in names and "[Content_Types].xml" in names:
                return ".docx"
            if "mimetype" in names and archive.read("mimetype") == b"application/vnd.oasis.opendocument.text" and "content.xml" in names:
                return ".odt"
    except (zipfile.BadZipFile, RuntimeError, OSError) as error:
        raise Blocked("Anexa um documento DOCX ou ODT válido.") from error
    raise Blocked("Anexa um documento DOCX ou ODT válido.")


def pdf_bytes(path):
    if path.is_symlink() or not path.is_file() or not 20 < path.stat().st_size <= 8_000_000:
        raise Blocked("PDF ausente ou inválido.")
    raw = path.read_bytes()
    if not raw.startswith(b"%PDF-") or b"%%EOF" not in raw[-1024:]:
        raise Blocked("PDF incompleto.")
    return raw



import ctypes as C

class OfficeClass(C.Structure):
    _fields_ = [('size', C.c_size_t), ('destroy', C.c_void_p), ('document_load', C.c_void_p), ('get_error', C.c_void_p)]


class Office(C.Structure):
    _fields_ = [('klass', C.POINTER(OfficeClass))]


class DocumentClass(C.Structure):
    _fields_ = [('size', C.c_size_t), ('destroy', C.c_void_p), ('save_as', C.c_void_p)]


class Document(C.Structure):
    _fields_ = [('klass', C.POINTER(DocumentClass))]


def _lok_convert():
    require_native_boundary()
    program, source, profile, destination = map(lambda value: Path(value).resolve(), sys.argv[2:6])
    handles = [os.add_dll_directory(str(program))]
    ure = program.parent / 'URE/bin'
    if ure.is_dir(): handles.append(os.add_dll_directory(str(ure)))
    os.environ['PATH'] = str(program) + os.pathsep + os.environ['PATH']
    print("LOK loading library", file=sys.stderr, flush=True)
    library = C.CDLL(str(program / 'mergedlo.dll'))
    init = library.libreofficekit_hook_2
    init.argtypes = [C.c_char_p, C.c_char_p]
    init.restype = C.POINTER(Office)
    print("LOK initializing", file=sys.stderr, flush=True)
    kit = init(str(program).encode('utf-8'), profile.as_uri().encode('utf-8'))
    print("LOK initialized=" + str(bool(kit)), file=sys.stderr, flush=True)
    if not kit:
        return 4
    klass = kit.contents.klass.contents
    if klass.size < C.sizeof(OfficeClass):
        return 5
    load = C.CFUNCTYPE(C.POINTER(Document), C.POINTER(Office), C.c_char_p)(klass.document_load)
    print("LOK loading document", file=sys.stderr, flush=True)
    document = load(kit, source.as_uri().encode('utf-8'))
    if not document:
        return 6
    docclass = document.contents.klass.contents
    if docclass.size < C.sizeof(DocumentClass):
        return 7
    save = C.CFUNCTYPE(C.c_int, C.POINTER(Document), C.c_char_p, C.c_char_p, C.c_char_p)(docclass.save_as)
    print("LOK exporting PDF", file=sys.stderr, flush=True)
    saved = save(document, destination.as_uri().encode('utf-8'), b'pdf', None)
    C.CFUNCTYPE(None, C.POINTER(Document))(docclass.destroy)(document)
    C.CFUNCTYPE(None, C.POINTER(Office))(klass.destroy)(kit)
    return 0 if saved else 8

def run(input_path):
    source = Path(input_path)
    raw = source.read_bytes()
    kind = document_kind(raw)
    config = strict_json((source.parent / "libreoffice.json").read_bytes())
    if not isinstance(config, dict) or set(config) != {"executable"} or not isinstance(config["executable"], str):
        raise Blocked("Configuração LibreOffice inválida.")
    executable = Path(config["executable"])
    if not executable.is_absolute() or not executable.is_file() or executable.name.lower() != "soffice.com":
        raise Blocked("LibreOffice indisponível.")
    if sys.platform == "win32":
        require_native_boundary()
    working = source.parent / "office"
    working.mkdir()
    document = working / ("resultado" + kind)
    document.write_bytes(raw)
    profile = working / "profile"
    profile.mkdir()
    (profile / "user").mkdir()
    (profile / "user/registrymodifications.xcu").write_text(
        '<?xml version="1.0"?><oor:items xmlns:oor="http://openoffice.org/2001/registry">'
        '<item oor:path="/org.openoffice.Office.Common/Security/Scripting"><prop oor:name="MacroSecurityLevel" oor:op="fuse"><value>3</value></prop></item></oor:items>', encoding="utf-8")
    command = [str(executable), "-env:UserInstallation=" + profile.as_uri(), "--headless", "--norestore", "--convert-to", "pdf:writer_pdf_Export", "--outdir", str(source.parent), str(document)]
    if sys.platform == "win32":
        command = [sys.executable, "-I", str(Path(__file__).resolve()), "nexus_lok", str(executable.parent), str(document), str(profile), str(source.parent / "resultado.pdf")]
    with (working / "stdout.txt").open("wb") as stdout, (working / "stderr.txt").open("wb") as stderr:
        proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
        proc.stdin.close()  # Explicit EOF; LPAC cannot open the global NUL device.
        try:
            code = proc.wait(timeout=45)
        except subprocess.TimeoutExpired:
            subprocess.run([str(Path(os.environ["SystemRoot"]) / "System32/taskkill.exe"), "/PID", str(proc.pid), "/T", "/F"], capture_output=True, timeout=10)
            proc.kill(); proc.wait()
            raise Blocked("Conversão excedeu o tempo permitido.") from None
    print("Writer child exit=" + str(code), file=sys.stderr, flush=True)
    if code != 0:
        raise Blocked("LibreOffice não concluiu a conversão.")
    pdf = pdf_bytes(source.parent / "resultado.pdf")
    sha = hashlib.sha256(pdf).hexdigest()
    return {"status": "UNKNOWN", "outcome": "candidate", "title": "PDF convertido",
            "markdown": "# PDF convertido\n\nO original foi conservado. Revê o PDF antes de aprovar; a conversão não prova a fidelidade do conteúdo.",
            "ai_calls": 0, "artifact": {"name": "resultado.pdf", "sha256": sha},
            "evidence": [{"capability": "libreoffice.writer-pdf", "status": "PASS", "value": sha}]}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "nexus_lok":
        raise SystemExit(_lok_convert())
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        print(json.dumps(run(sys.argv[1]), ensure_ascii=False))
    except Exception:
        print("Conversão indisponível ou documento rejeitado.", file=sys.stderr)
        raise SystemExit(1)
