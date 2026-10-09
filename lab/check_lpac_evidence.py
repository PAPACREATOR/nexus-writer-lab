"""Validate the read-only LPAC reader against ordinary and invalid handles.

Actual confined process observations are recorded separately by lab.observe.
This helper never launches Writer, creates an AppContainer or modifies ACLs.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
from lab.observe import lpac_accesscheck


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    if os.name != 'nt':
        raise SystemExit('Windows token API control requires Windows')
    k = C.WinDLL('kernel32', use_last_error=True)
    k.GetCurrentProcess.restype = W.HANDLE
    ordinary = lpac_accesscheck(k.GetCurrentProcess())
    invalid = lpac_accesscheck(W.HANDLE())
    checks = {
        'ordinary_process_non_lpac': ordinary.get('api_ok') is True
            and ordinary.get('appcontainer') is False
            and ordinary.get('lpac') is False
            and ordinary.get('granted_access') == 3,
        'invalid_handle_remains_unknown': invalid.get('api_ok') is False
            and invalid.get('lpac') is None
            and invalid.get('classification') == 'api_error'
            and isinstance(invalid.get('winerror'), int),
    }
    result = {'checks': checks, 'ordinary_process': ordinary, 'invalid_handle': invalid,
              'passed': all(checks.values()), 'writer_executed': False,
              'os_acl_changes': False, 'token_privilege_changes': False}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': result['passed'], 'checks': checks}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
