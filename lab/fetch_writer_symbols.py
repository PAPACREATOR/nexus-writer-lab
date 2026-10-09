"""Download and verify public symbols for the disposable Writer fixture.

Only installed-image CodeView identifiers are sent to the official public
symbol store. Product binaries and process memory are never uploaded. Symbol
files stay under RUNNER_TEMP; the report contains metadata only.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


HOST = "dev-downloads.libreoffice.org"
BASE = "https://" + HOST + "/symstore/symbols/"
MSF7 = b"Microsoft C/C++ MSF 7.00\r\n\x1aDS\x00\x00\x00"
MAX_FILE_BYTES = 2 * 1024**3
MAX_DIRECTORY_BYTES = 64 * 1024**2
OVERALL_SECONDS = 600
DOWNLOAD_SECONDS = 180
MODULES = ("mergedlo.dll", "vclplug_winlo.dll", "sal3.dll", "soffice.bin")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024**2), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cabinet_payload(path, expected_name):
    """Bound a single-file Microsoft cabinet before invoking expand.exe."""
    with Path(path).open("rb") as stream:
        header = stream.read(36)
        if len(header) != 36 or header[:4] != b"MSCF":
            raise ValueError("Compressed symbols are not a Microsoft cabinet")
        cabinet_size = struct.unpack_from("<I", header, 8)[0]
        files_offset = struct.unpack_from("<I", header, 16)[0]
        folders, files, flags = struct.unpack_from("<HHH", header, 26)
        if cabinet_size != Path(path).stat().st_size:
            raise ValueError("Truncated or unsupported cabinet size")
        if files != 1 or not folders or flags & 3:
            raise ValueError("Only single-file, non-spanning symbol cabinets are supported")
        if not 36 <= files_offset <= cabinet_size - 17:
            raise ValueError("Invalid cabinet file table")
        stream.seek(files_offset)
        entry = stream.read(16)
        size, _, folder, _, _, _ = struct.unpack("<IIHHHH", entry)
        if not 0 < size <= MAX_FILE_BYTES or folder >= folders:
            raise ValueError("Cabinet expansion size or folder is invalid")
        name = stream.read(min(260, cabinet_size - files_offset - 16))
        if b"\x00" not in name:
            raise ValueError("Unterminated cabinet member name")
        member = name.split(b"\x00", 1)[0].decode("ascii")
        if member.casefold() != expected_name.casefold():
            raise ValueError("Cabinet member does not match the CodeView PDB basename")
        return {"member": member, "declared_output_bytes": size}


def pdb_identity(path):
    """Independently read the MSF7 PDB info stream (stream 1), no debugger."""
    path = Path(path)
    length = path.stat().st_size
    if length > MAX_FILE_BYTES:
        raise ValueError("Expanded PDB exceeds the file-size limit")
    with path.open("rb") as stream:
        header = stream.read(56)
        if len(header) != 56 or header[:32] != MSF7:
            raise ValueError("Not an MSF7 PDB")
        block_size, _, block_count, directory_size, _, block_map = struct.unpack_from(
            "<6I", header, 32
        )
        if not (512 <= block_size <= 65536) or block_size & (block_size - 1):
            raise ValueError("Unsupported MSF block size")
        if not block_count or block_count * block_size > length:
            raise ValueError("Truncated MSF block table")
        if not 8 <= directory_size <= MAX_DIRECTORY_BYTES:
            raise ValueError("Invalid or excessive MSF directory size")
        directory_blocks = math.ceil(directory_size / block_size)
        # MSF7's directory block map fits in one block. Refuse unsupported
        # layouts rather than guessing an identity from unverified bytes.
        if directory_blocks * 4 > block_size or block_map >= block_count:
            raise ValueError("Unsupported MSF directory block map")

        def read_at(offset, count):
            if offset < 0 or count < 0 or offset + count > length:
                raise ValueError("MSF read outside the file")
            stream.seek(offset)
            data = stream.read(count)
            if len(data) != count:
                raise ValueError("Truncated MSF data")
            return data

        block_numbers = struct.unpack(
            "<" + "I" * directory_blocks,
            read_at(block_map * block_size, directory_blocks * 4),
        )
        if any(number >= block_count for number in block_numbers):
            raise ValueError("Invalid MSF directory block")
        directory = b"".join(
            read_at(number * block_size, block_size) for number in block_numbers
        )[:directory_size]
        stream_count = struct.unpack_from("<I", directory)[0]
        if not 2 <= stream_count <= 1_000_000 or 4 + stream_count * 4 > len(directory):
            raise ValueError("Invalid MSF stream table")
        sizes = struct.unpack_from("<" + "I" * stream_count, directory, 4)
        cursor = 4 + stream_count * 4
        info_blocks = None
        for index, size in enumerate(sizes):
            count = 0 if size == 0xFFFFFFFF else math.ceil(size / block_size)
            if cursor + count * 4 > len(directory):
                raise ValueError("Truncated MSF stream block list")
            if index == 1:
                if not 28 <= size <= MAX_FILE_BYTES:
                    raise ValueError("Invalid PDB info stream")
                info_blocks = struct.unpack_from("<" + "I" * count, directory, cursor)
                if not info_blocks or any(number >= block_count for number in info_blocks):
                    raise ValueError("Invalid PDB info stream blocks")
                # The fixed 28-byte identity header fits in the first block.
                info = read_at(info_blocks[0] * block_size, 28)
                version, signature, age = struct.unpack_from("<III", info)
                guid = uuid.UUID(bytes_le=info[12:28])
                return {
                    "format": "MSF7 info stream 1",
                    "version": version,
                    "signature": signature,
                    "guid": str(guid),
                    "age": age,
                    "key": guid.hex.upper() + format(age, "X"),
                }
            cursor += count * 4
        raise ValueError("PDB info stream missing")


def allowed_url(url):
    parsed = urllib.parse.urlsplit(url)
    return (
        parsed.scheme == "https"
        and parsed.netloc == HOST
        and parsed.path.startswith("/symstore/symbols/")
        and not parsed.query
        and not parsed.fragment
    )


class OfficialRedirectsOnly(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file, code, message, headers, new_url):
        if not allowed_url(new_url):
            raise urllib.error.HTTPError(
                request.full_url, code, "Refused redirect outside official symbol store", headers, file
            )
        return super().redirect_request(request, file, code, message, headers, new_url)


def download(url, target, deadline, attempt):
    if not allowed_url(url):
        raise ValueError("Refused non-official symbol URL")
    started = time.monotonic()
    local_deadline = min(deadline, started + DOWNLOAD_SECONDS)
    remaining = local_deadline - started
    if remaining <= 0:
        raise TimeoutError("Overall symbol-download deadline reached")
    # No auth handlers, cookies, credentials, environment tokens, or .netrc.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), OfficialRedirectsOnly())
    request = urllib.request.Request(url, headers={"User-Agent": "NexusWriterLab-symbol-metadata/1"})
    try:
        with opener.open(request, timeout=min(15, remaining)) as response:
            attempt.update(
                http_status=response.status,
                final_url=response.geturl(),
                content_type=response.headers.get("Content-Type", ""),
            )
            if not allowed_url(response.geturl()):
                raise ValueError("Refused final URL outside official symbol store")
            if response.status != 200:
                raise ValueError("Symbol response was not HTTP 200")
            if any(word in attempt["content_type"].lower() for word in ("html", "xhtml")):
                raise ValueError("Symbol response is HTML, not a symbol file")
            declared = response.headers.get("Content-Length")
            if declared is not None and not 0 < int(declared) <= MAX_FILE_BYTES:
                raise ValueError("Declared download size is invalid or excessive")
            digest = hashlib.sha256()
            total = 0
            with target.open("xb") as output:
                while True:
                    if time.monotonic() >= local_deadline:
                        raise TimeoutError("Bounded symbol download timed out")
                    # read1 returns available socket data without waiting to
                    # fill a megabyte, so the deadline is checked between reads.
                    chunk = response.read1(1024**2)
                    if not chunk:
                        break
                    if total == 0 and chunk.lstrip().lower().startswith((b"<!doctype html", b"<html")):
                        raise ValueError("Symbol response contains HTML")
                    total += len(chunk)
                    if total > MAX_FILE_BYTES:
                        raise ValueError("Download exceeded the file-size limit")
                    output.write(chunk)
                    digest.update(chunk)
                    attempt["bytes"] = total
            if not total or (declared is not None and total != int(declared)):
                raise ValueError("Empty or truncated symbol download")
            attempt["sha256"] = digest.hexdigest()
    except urllib.error.HTTPError as error:
        attempt["http_status"] = error.code
        attempt["response_url"] = error.geturl()
        raise
    finally:
        attempt["duration_seconds"] = round(time.monotonic() - started, 3)


def expected_identity(module):
    if module.get("image") not in MODULES:
        raise ValueError("Unexpected Writer module")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", module.get("sha256", "")):
        raise ValueError("Installed module SHA-256 is missing or invalid")
    records = module.get("codeview")
    if not isinstance(records, list) or len(records) != 1:
        raise ValueError("Exactly one RSDS CodeView record is required")
    record = records[0]
    guid = uuid.UUID(record["guid"])
    age = record["age"]
    if type(age) is not int or not 0 <= age <= 0xFFFFFFFF:
        raise ValueError("CodeView age is invalid")
    key = guid.hex.upper() + format(age, "X")
    if record.get("key") != key:
        raise ValueError("CodeView key disagrees with GUID and age")
    name = record["pdb_name"]
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,180}\.pdb", name, re.I):
        raise ValueError("Unsafe or unsupported CodeView PDB basename")
    if re.fullmatch(r"CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]", name.split(".", 1)[0], re.I):
        raise ValueError("Reserved Windows device basename is not a PDB filename")
    return {"guid": str(guid), "age": age, "key": key, "pdb_name": name}


def fetch_module(module, output_directory, deadline):
    result = {"image": module.get("image"), "image_sha256": module.get("sha256"), "attempts": []}
    try:
        expected = expected_identity(module)
        result["expected"] = expected
    except (KeyError, TypeError, ValueError) as error:
        result.update(status="invalid_metadata", error=str(error))
        return result
    module_directory = output_directory / module["image"]
    module_directory.mkdir()
    for compressed in (False, True):
        name = expected["pdb_name"]
        remote_name = name[:-1] + "_" if compressed else name
        url = BASE + name + "/" + expected["key"] + "/" + remote_name
        attempt = {"url": url, "compressed": compressed, "bytes": 0}
        result["attempts"].append(attempt)
        local = module_directory / remote_name
        verified = module_directory / name
        try:
            if shutil.disk_usage(output_directory).free < MAX_FILE_BYTES:
                raise OSError("Insufficient disposable storage for bounded symbol file")
            download(url, local, deadline, attempt)
            if compressed:
                attempt["cabinet"] = cabinet_payload(local, name)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Overall deadline reached before expansion")
                expand = Path(os.environ["SystemRoot"]) / "System32" / "expand.exe"
                completed = subprocess.run(
                    [str(expand), str(local), str(verified)],
                    capture_output=True, text=True, errors="replace",
                    timeout=min(90, remaining), check=False,
                )
                attempt["expand_exit_code"] = completed.returncode
                # Record bounded diagnostics only; never print symbol contents.
                attempt["expand_stdout"] = completed.stdout[-4000:]
                attempt["expand_stderr"] = completed.stderr[-4000:]
                if completed.returncode:
                    raise ValueError("Microsoft expand.exe failed")
                if verified.stat().st_size != attempt["cabinet"]["declared_output_bytes"]:
                    raise ValueError("Expanded PDB size disagrees with its cabinet")
            actual = pdb_identity(verified)
            attempt["pdb_identity"] = actual
            if actual["guid"] != expected["guid"] or actual["age"] != expected["age"]:
                raise ValueError("PDB GUID/age mismatch; refused symbol file")
            attempt["status"] = "verified"
            result.update(
                status="verified", verified_file=str(verified),
                pdb_identity=actual, pdb_bytes=verified.stat().st_size,
                pdb_sha256=sha256_file(verified),
            )
            return result
        except (OSError, ValueError, TimeoutError, urllib.error.URLError, subprocess.SubprocessError) as error:
            attempt.update(status="refused_or_unavailable", error=str(error)[:2000])
            # Only remove the two exact files created by this module attempt.
            # The fresh output directory is verified beneath RUNNER_TEMP.
            for path in {local, verified}:
                if path.is_file():
                    path.unlink()
            if time.monotonic() >= deadline:
                break
    result["status"] = "unavailable_or_unverified"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", type=Path, default=Path("lab-evidence/pe-debug-info.json"))
    parser.add_argument("--report", type=Path, default=Path("lab-evidence/writer-symbols.json"))
    parser.add_argument("--module", action="append", choices=MODULES)
    args = parser.parse_args()
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("Disposable GitHub runner only")
    temporary_root = Path(os.environ["RUNNER_TEMP"]).resolve(strict=True)
    metadata_bytes = args.metadata.read_bytes()
    if len(metadata_bytes) > 1024**2:
        raise SystemExit("Excessive CodeView metadata")
    modules = json.loads(metadata_bytes)
    if not isinstance(modules, list):
        raise SystemExit("CodeView metadata must be a list")
    selected = list(dict.fromkeys(args.module or ["mergedlo.dll"]))
    output_directory = Path(tempfile.mkdtemp(prefix="nexus-writer-symbols-", dir=temporary_root)).resolve()
    if not output_directory.is_relative_to(temporary_root):
        raise SystemExit("Symbol output escaped RUNNER_TEMP")
    report = {
        "schema": "nexus.writer.public-symbols.v1",
        "utc": datetime.now(timezone.utc).isoformat(),
        "metadata_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
        "official_host": HOST, "output_directory": str(output_directory),
        "overall_timeout_seconds": OVERALL_SECONDS,
        "download_timeout_seconds": DOWNLOAD_SECONDS,
        "socket_timeout_seconds": 15, "max_file_bytes": MAX_FILE_BYTES,
        "memory_dump": False, "uploaded_binary": False, "runtime_changes": [],
        "modules": [],
    }
    deadline = time.monotonic() + OVERALL_SECONDS
    for image in selected:
        matches = [module for module in modules if isinstance(module, dict) and module.get("image") == image]
        if len(matches) != 1:
            report["modules"].append({"image": image, "status": "invalid_metadata", "error": "Expected one module record"})
        else:
            report["modules"].append(fetch_module(matches[0], output_directory, deadline))
    report["all_selected_verified"] = all(module["status"] == "verified" for module in report["modules"])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(args.report), "all_selected_verified": report["all_selected_verified"]}))
    return 0 if report["all_selected_verified"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
