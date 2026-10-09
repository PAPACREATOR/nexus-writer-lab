"""Synthetic PDB binding controls: no network, files, debugger, or Writer."""

import io
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import uuid

from lab.fetch_writer_symbols import MSF7, pdb_identity, validate_identity


GUID = uuid.UUID("12345678-1234-5678-9abc-def012345678")


def synthetic_pdb(info_age, dbi_age, *, guid=GUID, dbi_signature=-1,
                  dbi_version=19990903, missing_dbi=False):
    block_size = 512
    data = bytearray(block_size * 8)
    data[:56] = MSF7 + struct.pack("<6I", block_size, 1, 8, 28, 0, 2)
    struct.pack_into("<I", data, block_size * 2, 3)
    struct.pack_into("<7I", data, block_size * 3, 4, 0, 28, 0,
                     0xFFFFFFFF if missing_dbi else 64, 4, 5)
    data[block_size * 4:block_size * 4 + 28] = (
        struct.pack("<III", 20000404, 0x12345678, info_age) + guid.bytes_le
    )
    struct.pack_into("<iII", data, block_size * 5, dbi_signature, dbi_version, dbi_age)
    struct.pack_into("<HH", data, block_size * 5 + 56, 0, 0x8664)
    return bytes(data)


def parse_synthetic(data):
    with patch.object(Path, "stat", return_value=SimpleNamespace(st_size=len(data))), \
         patch.object(Path, "open", side_effect=lambda *args, **kwargs: io.BytesIO(data)):
        return pdb_identity(Path("synthetic-only.pdb"))


class SymbolBindingControls(unittest.TestCase):
    expected = {"guid": str(GUID), "age": 2}

    def test_equal_info_dbi_image_ages_bind(self):
        actual = parse_synthetic(synthetic_pdb(2, 2))
        result = validate_identity(actual, self.expected)
        self.assertEqual(result["pdb_info_age"], 2)
        self.assertEqual(result["pdb_dbi_age"], 2)

    def test_newer_info_age_same_dbi_image_age_binds(self):
        actual = parse_synthetic(synthetic_pdb(3, 2))
        result = validate_identity(actual, self.expected)
        self.assertEqual(actual["age"], 3)  # Preserve actual info age, never rewrite it.
        self.assertEqual(result["image_age"], 2)
        self.assertEqual(result["pdb_dbi_age"], 2)
        self.assertFalse(result["ignore_mismatch"])

    def test_wrong_guid_refused_even_with_matching_ages(self):
        actual = parse_synthetic(synthetic_pdb(2, 2, guid=uuid.UUID(int=1)))
        with self.assertRaisesRegex(ValueError, "GUID mismatch"):
            validate_identity(actual, self.expected)

    def test_older_info_age_refused_even_with_matching_dbi(self):
        actual = parse_synthetic(synthetic_pdb(1, 2))
        with self.assertRaisesRegex(ValueError, "predates"):
            validate_identity(actual, self.expected)

    def test_wrong_dbi_age_refused_even_with_matching_info(self):
        actual = parse_synthetic(synthetic_pdb(2, 3))
        with self.assertRaisesRegex(ValueError, "DBI age"):
            validate_identity(actual, self.expected)

    def test_matching_newer_info_and_dbi_ages_do_not_bind_older_image(self):
        actual = parse_synthetic(synthetic_pdb(3, 3))
        with self.assertRaisesRegex(ValueError, "DBI age"):
            validate_identity(actual, self.expected)

    def test_legacy_zero_dbi_age_refused(self):
        actual = parse_synthetic(synthetic_pdb(3, 0))
        with self.assertRaisesRegex(ValueError, "DBI age"):
            validate_identity(actual, self.expected)

    def test_missing_dbi_refused(self):
        with self.assertRaisesRegex(ValueError, "identity stream 3"):
            parse_synthetic(synthetic_pdb(3, 2, missing_dbi=True))

    def test_unknown_dbi_version_refused(self):
        with self.assertRaisesRegex(ValueError, "DBI stream header"):
            parse_synthetic(synthetic_pdb(3, 2, dbi_version=1))

    def test_wrong_dbi_signature_refused(self):
        with self.assertRaisesRegex(ValueError, "DBI stream header"):
            parse_synthetic(synthetic_pdb(3, 2, dbi_signature=0))

    def test_truncated_dbi_block_refused(self):
        with self.assertRaises(ValueError):
            parse_synthetic(synthetic_pdb(3, 2)[:5 * 512 + 20])


if __name__ == "__main__":
    unittest.main()
