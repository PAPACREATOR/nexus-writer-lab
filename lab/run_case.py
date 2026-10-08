"""Run one bounded experiment in a disposable checkout, restoring original bytes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

SOURCE_SHA = 'b4d50ab8469cf60dfa3228c7c34ef9a1285ac827'
ROOT = Path(__file__).resolve().parents[1]
DESCRIPTIONS = {
    'A': 'Exact original source baseline',
    'B': 'Dedicated UserInstallation: already present in A; identical repeat',
    'C': 'Precreated profile: already present in A; identical repeat',
    'D': 'Per-task SID inherited MODIFY ACL: already present in A; identical repeat, no wider grants',
    'E': '--norestore: already present in A; identical repeat',
    'F': 'A + --nolockcheck only',
    'G': 'F + --nologo only',
    'H': 'Official LibreOfficeKit C ABI in sealed office child; original Host/Gate/boundary and 45 seconds',
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('variant', choices=DESCRIPTIONS)
    args = parser.parse_args()
    output = ROOT / 'lab-evidence' / args.variant
    output.mkdir(parents=True, exist_ok=True)
    office = ROOT / 'nexus/adapters/office.py'
    manifest = ROOT / 'nexus/integrity.json'
    original, seal = office.read_bytes(), manifest.read_bytes()
    expected = subprocess.check_output(['git', 'show', SOURCE_SHA + ':nexus/adapters/office.py'], cwd=ROOT)
    if original.replace(b'\r\n', b'\n') != expected.replace(b'\r\n', b'\n'):
        raise SystemExit('Refusing a non-source office adapter')
    metadata = {'source_repository': 'PAPACREATOR/cerebro-parvo-', 'source_sha': SOURCE_SHA,
                'lab_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'variant': args.variant, 'description': DESCRIPTIONS[args.variant],
                'windows': platform.platform(), 'python': sys.version,
                'writer_timeout_seconds': 45,
                'libreoffice_executable': os.environ.get('LIBREOFFICE_EXE'),
                'original_office_sha256': hashlib.sha256(original).hexdigest(),
                'security_changes': []}
    try:
        if args.variant == 'H':
            office.write_bytes((ROOT / 'lab/candidate-office.py').read_bytes())
            hashes = json.loads(seal)
            hashes['adapters/office.py'] = hashlib.sha256(office.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf-8')
        if args.variant in ('F', 'G'):
            modified = original.decode('utf-8')
            before = '"--headless", "--norestore", "--convert-to"'
            after = '"--headless", "--norestore", "--nolockcheck", ' + ('"--nologo", ' if args.variant == 'G' else '') + '"--convert-to"'
            if modified.count(before) != 1:
                raise SystemExit('Unexpected source command')
            office.write_bytes(modified.replace(before, after).encode('utf-8'))
            hashes = json.loads(seal)
            hashes['adapters/office.py'] = hashlib.sha256(office.read_bytes()).hexdigest()
            manifest.write_text(json.dumps(hashes, indent=2) + '\n', encoding='utf-8')
        metadata['tested_office_sha256'] = hashlib.sha256(office.read_bytes()).hexdigest()
        (output / 'tested-office.py').write_bytes(office.read_bytes())
        from nexus.host import verify_integrity
        verify_integrity()
        metadata['integrity_verified'] = True
        env = {**os.environ, 'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'NEXUS_REAL_WRITER': '1',
               'LAB_EVIDENCE': str(output), 'PYTHONUTF8': '1'}
        command = [sys.executable, '-u', '-m', 'pytest', 'nexus/tests/test_native_writer_route_real.py',
                   '-vv', '-s', '--tb=short', '-p', 'lab.evidence_plugin',
                   '--basetemp=' + str(output / 'tmp'), '--junitxml=' + str(output / 'results.xml')]
        metadata['test_command'] = command
        with (output / 'console.txt').open('wb') as stream:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT)
        metadata['pytest_exit_code'] = result.returncode
        print(json.dumps(metadata))
        return result.returncode
    finally:
        office.write_bytes(original); manifest.write_bytes(seal)
        metadata['original_bytes_restored'] = office.read_bytes() == original and manifest.read_bytes() == seal
        (output / 'metadata.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')


if __name__ == '__main__':
    raise SystemExit(main())
