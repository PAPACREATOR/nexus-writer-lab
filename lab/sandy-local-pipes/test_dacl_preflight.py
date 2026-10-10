"""Fail-closed tests for experimental DACL restoration, without OS mutation.

The Windows API is simulated here. Only the disposable Windows CI actually
runs Sandy, Writer and security descriptors against Windows.
"""
import ctypes as C
import importlib.util
from pathlib import Path
import tempfile
import types
import unittest


spec = importlib.util.spec_from_file_location('writer_mail_compare', Path(__file__).with_name('compare.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeNative:
    P = C.c_void_p
    D = C.c_uint32
    W = types.SimpleNamespace(BOOL=C.c_int, LPCWSTR=C.c_wchar_p)
    advapi = object()

    def __init__(self, state, *, after_restore=None, convert_ok=True, set_ok=True):
        self.state = state
        self.after_restore = after_restore
        self.convert_ok = convert_ok
        self.set_ok = set_ok
        self.calls = []
        self.free_count = 0

    def dacl(self, path):
        return self.state[str(path)]

    def ConvertSDDL(self, sddl, revision, result, size):
        self.calls.append(('ConvertSDDL', sddl, revision))
        if not self.convert_ok:
            return 0
        C.cast(result, C.POINTER(C.c_void_p))[0] = C.c_void_p(333)
        return 1

    def api(self, dll, name, restype, *args):
        if name != 'SetFileSecurityW':
            raise AssertionError('Unexpected Windows API: ' + name)
        def setter(path, flag, descriptor):
            self.calls.append(('SetFileSecurityW', path, flag))
            if self.set_ok:
                self.state[path] = (self.after_restore if self.after_restore is not None
                                    else self.state[path].replace('D:AI', 'D:', 1))
            return int(self.set_ok)
        return setter

    def check(self, ok):
        if not ok:
            raise OSError('simulated Windows API failure')
        return ok

    def LocalFree(self, pointer):
        self.free_count += 1


class DaclRecoveryTests(unittest.TestCase):
    original = 'D:(A;OICIID;FA;;;SY)(A;OICIID;FA;;;BA)'

    def test_exact_ai_transition_only(self):
        self.assertTrue(module.expected_auto_inherited_dacl(self.original, 'D:AI' + self.original[2:]))
        for changed in (
            self.original,
            'D:PAI' + self.original[2:],
            'D:AI(A;OICIID;FA;;;WD)(A;OICIID;FA;;;BA)',
            'D:AI(A;OICIID;FA;;;BA)(A;OICIID;FA;;;SY)',
            'D:AR' + self.original[2:],
            'D:AI(A;OICIID;FA;;;SY)',
        ):
            with self.subTest(after=changed):
                self.assertFalse(module.expected_auto_inherited_dacl(self.original, changed))

    def test_only_ai_change_restores_exact_descriptor(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            target = root / 'work'
            target.mkdir()
            original = {str(target): self.original}
            after = {str(target): 'D:AI' + self.original[2:]}
            fake = FakeNative(dict(after))
            result = module.restore_exact_lab_dacls(original, after, (root,), fake)
            self.assertEqual(fake.dacl(target), self.original)
            self.assertEqual(len(result), 1)
            self.assertEqual(fake.calls[0], ('ConvertSDDL', self.original, 1))
            self.assertEqual(fake.calls[1], ('SetFileSecurityW', str(target), 4))
            self.assertEqual(fake.free_count, 1)

    def test_unchanged_baseline_requires_no_windows_write(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d).resolve()
            same = {str(target): self.original}
            fake = FakeNative(dict(same))
            self.assertEqual(module.restore_exact_lab_dacls(same, same, (target,), fake), [])
            self.assertFalse(fake.calls)

    def test_wrong_root_is_rejected_before_any_write(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            allowed = root / 'owned'
            denied = root / 'owned-other'
            allowed.mkdir()
            denied.mkdir()
            a = {str(denied): self.original}
            b = {str(denied): 'D:AI' + self.original[2:]}
            fake = FakeNative(dict(b))
            with self.assertRaisesRegex(RuntimeError, 'outside experimental copies'):
                module.restore_exact_lab_dacls(a, b, (allowed,), fake)
            self.assertEqual(fake.calls, [])

    def test_reject_new_or_removed_aces_without_write(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            old = {str(root): self.original}
            for new in (
                'D:AI(A;OICIID;FA;;;WD)',
                'D:AI(A;OICIID;FA;;;SY)',
                'D:PAI' + self.original[2:],
            ):
                with self.subTest(new=new):
                    fake = FakeNative({str(root): new})
                    with self.assertRaisesRegex(RuntimeError, 'beyond AI'):
                        module.restore_exact_lab_dacls(old, {str(root): new}, (root,), fake)
                    self.assertEqual(fake.calls, [])

    def test_unknown_change_prevalidated_before_repairing_any_path(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            first, second = root / 'first', root / 'second'
            first.mkdir()
            second.mkdir()
            old = {str(first): self.original, str(second): self.original}
            after = {str(first): 'D:AI' + self.original[2:],
                     str(second): 'D:AI(A;;FA;;;WD)'}
            fake = FakeNative(dict(after))
            with self.assertRaisesRegex(RuntimeError, 'beyond AI'):
                module.restore_exact_lab_dacls(old, after, (root,), fake)
            self.assertEqual(fake.calls, [])

    def test_read_and_write_api_failures_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            old = {str(root): self.original}
            after = {str(root): 'D:AI' + self.original[2:]}
            for options in ({'convert_ok': False}, {'set_ok': False}):
                with self.subTest(options=options):
                    fake = FakeNative(dict(after), **options)
                    with self.assertRaises(OSError):
                        module.restore_exact_lab_dacls(old, after, (root,), fake)
                    self.assertEqual(fake.dacl(root), after[str(root)])

    def test_restore_must_compare_exact_sddl_after_call(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            old = {str(root): self.original}
            after = {str(root): 'D:AI' + self.original[2:]}
            fake = FakeNative(dict(after), after_restore='D:PAI' + self.original[2:])
            with self.assertRaisesRegex(RuntimeError, 'exact post-restore mismatch'):
                module.restore_exact_lab_dacls(old, after, (root,), fake)


if __name__ == '__main__':
    unittest.main()
