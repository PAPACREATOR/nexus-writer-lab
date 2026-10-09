"""Verify an unchanged disposable Office copy without loading its binaries."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time


def tree_identity(root, deadline):
    root = Path(root).absolute()
    digest = hashlib.sha256()
    files, total = 0, 0
    inventory = {}
    def inspect(path):
        if time.monotonic() > deadline:
            raise TimeoutError('Office tree identity deadline exceeded')
        value = path.lstat()
        if path.is_symlink() or getattr(value, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Reparse points are refused in the pinned Office fixture')
        return value
    if not root.is_dir():
        raise ValueError('Office fixture root is missing')
    inspect(root)
    for directory, subdirectories, names in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in sorted(subdirectories):
            child = base / name
            inspect(child)
            inventory[child.relative_to(root).as_posix() + '/'] = (0, 'directory')
        for name in sorted(names):
            path = base / name
            value = inspect(path)
            files += 1
            total += value.st_size
            if files > 100000 or total > 4 * 1024**3:
                raise ValueError('Office fixture exceeds bounded identity limits')
            content = hashlib.sha256()
            with path.open('rb') as stream:
                while block := stream.read(1024 * 1024):
                    if time.monotonic() > deadline:
                        raise TimeoutError('Office content identity deadline exceeded')
                    content.update(block)
            inventory[path.relative_to(root).as_posix()] = (value.st_size, content.hexdigest())
    for name, identity in sorted(inventory.items()):
        digest.update(json.dumps([name, *identity], ensure_ascii=True,
                                 separators=(',', ':')).encode() + b'\n')
    return {'files': files, 'bytes': total, 'tree_sha256': digest.hexdigest()}, inventory


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--copy', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = {'schema': 'nexus.writer.office-tree-identity.v1', 'status': 'FAIL',
              'source': str(args.source), 'copy': str(args.copy),
              'writer_executed': False, 'acl_changes': False, 'deadline_seconds': 240}
    started = time.monotonic()
    try:
        deadline = started + 240
        source, original = tree_identity(args.source, deadline)
        copied, replica = tree_identity(args.copy, deadline)
        mismatch = sorted(name for name in original.keys() | replica.keys()
                          if original.get(name) != replica.get(name))
        result.update(source_identity=source, copy_identity=copied,
                      mismatch_count=len(mismatch), mismatches=mismatch[:100])
        if not original or mismatch:
            raise ValueError('Office copy does not match the exact installed fixture')
        for name in ('program/soffice.bin', 'program/soffice.com', 'program/sal3.dll'):
            if name not in original:
                raise ValueError('Pinned Office fixture lacks required executable: ' + name)
        result['status'] = 'PASS'
    except Exception as error:
        result['error'] = {'type': type(error).__name__, 'message': str(error)}
    result['seconds'] = time.monotonic() - started
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
