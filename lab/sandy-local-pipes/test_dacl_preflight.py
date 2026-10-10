"""Pure regression tests for the lab's Windows DACL preflight (no Windows writes).

The native calls are faked: these tests MUST NOT change real OS permissions.
Only the isolated Windows CI experiment exercises SetNamedSecurityInfoW.
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
    P, D = C.c_void_p, C.c_uint32
    W = types.SimpleNamespace(LPWSTR=C.c_wchar_p)
    advapi = object()

    def __init__(self, state, *, new_value=None, get_error=0, set_error=0):
        self.state = state
        self.new_value = new_value
        self.get_error = get_error
        self.set_error = set_error
        self.set_calls = []
        self.freed = 0

    def dacl(self, path):
        return self.state[str(path)]

    def GetSecurity(self, path, object_type, info, owner, group, acl, sacl, descriptor):
        self.get_args = (path, object_type, info)
        C.cast(acl, C.POINTER(C.c_void_p))[0] = C.c_void_p(222)
        C.cast(descriptor, C.POINTER(C.c_void_p))[0] = C.c_void_p(333)
        return self.get_error

    def api(self, dll, name, restype, *argtypes):
        if name != 'SetNamedSecurityInfoW':
            raise AssertionError('unexpected Windows API')
        def setter(path, object_type, flags, owner, group, dacl, sacl):
            self.set_calls.append((path, object_type, flags, dacl))
            if not self.set_error:
                before = self.state[path]
                self.state[path] = self.new_value or 'D:AI' + before[2:]
            return self.set_error
        return setter

    def LocalFree(self, descriptor):
        self.freed += 1


class DaclControlTests(unittest.TestCase):
    def test_only_ai_control_marker_is_allowed(self):
        old = 'D:(A;OICIID;FA;;;SY)(A;OICIID;FA;;;BA)'
        self.assertTrue(module.expected_auto_inherited_dacl(old, 'D:AI' + old[2:]))
        for after in (
            old,  # Not an auto-inherit transition.
            'D:AI(A;OICIID;FA;;;WD)(A;OICIID;FA;;;BA)',  # Wider ACE.
            'D:PAI' + old[2:],  # Protected DACL.
            'D:AR' + old[2:],  # Other control flags.
            'D:AI(A;OICIID;FA;;;BA)(A;OICIID;FA;;;SY)',  # Reordered ACEs.
            'D:AI(A;OICIID;FA;;;SY)',  # Removed ACE.
        ):
            with self.subTest(after=after):
                self.assertFalse(module.expected_auto_inherited_dacl(old, after))

    def test_preflight_materializes_only_ai_on_owned_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            child = root / 'work'
            child.mkdir()
            old = 'D:(A;OICIID;FA;;;SY)(A;OICIID;FA;;;BA)'
            fake = FakeNative({str(child): old})
            result = module.normalize_lab_dacl_before_measurement(child, (root,), fake)
            self.assertEqual(result['before'], old)
            self.assertEqual(result['after'], 'D:AI' + old[2:])
            self.assertEqual(result['action'], 'materialized_auto_inheritance_only')
            self.assertEqual(fake.get_args[1:], (1, 4))
            self.assertEqual(fake.set_calls[0][1:3], (1, 0x80000004))
            self.assertEqual(fake.freed, 1)

    def test_already_auto_inherited_performs_no_write(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            old = 'D:AI(A;OICIID;FA;;;SY)'
            fake = FakeNative({str(root): old})
            result = module.normalize_lab_dacl_before_measurement(root, (root,), fake)
            self.assertEqual(result['action'], 'already_auto_inherited')
            self.assertEqual(fake.set_calls, [])

    def test_outside_lab_is_refused_before_any_security_access(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            other = root / 'outside'
            other.mkdir()
            owned = root / 'owned'
            owned.mkdir()
            fake = FakeNative({})
            with self.assertRaisesRegex(RuntimeError, 'outside isolated lab'):
                module.normalize_lab_dacl_before_measurement(other, (owned,), fake)
            self.assertEqual(fake.set_calls, [])

    def test_protected_or_unrecognized_dacl_is_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            fake = FakeNative({str(root): 'D:P(A;;FA;;;SY)'})
            with self.assertRaisesRegex(RuntimeError, 'Unrecognized or protected'):
                module.normalize_lab_dacl_before_measurement(root, (root,), fake)
            self.assertEqual(fake.set_calls, [])

    def test_any_ace_change_after_windows_call_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            old = 'D:(A;OICIID;FA;;;SY)'
            fake = FakeNative({str(root): old}, new_value='D:AI(A;;FA;;;WD)')
            with self.assertRaisesRegex(RuntimeError, 'changed ACEs'):
                module.normalize_lab_dacl_before_measurement(root, (root,), fake)

    def test_windows_read_or_write_failure_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            for params, expected in [({'get_error': 5}, 'Cannot read DACL'),
                                     ({'set_error': 5}, 'preparation failed')]:
                with self.subTest(params=params):
                    fake = FakeNative({str(root): 'D:(A;;FA;;;SY)'}, **params)
                    with self.assertRaisesRegex(RuntimeError, expected):
                        module.normalize_lab_dacl_before_measurement(root, (root,), fake)
                    self.assertEqual(fake.freed, 0 if 'get_error' in params else 1)


if __name__ == '__main__':
    unittest.main()
