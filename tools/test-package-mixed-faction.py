"""Regression tests for the validated mixed-faction warning Game.dll patch."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    'mixed',
    Path(__file__).with_name('package-mixed-faction.py')
)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class MixedFactionPatchTests(unittest.TestCase):
    def test_patch_encoding(self):
        self.assertEqual(m.OFFSET, 0x2C6080)
        self.assertEqual(m.ORIGINAL, bytes.fromhex('8b 05 1a 67 bc 00'))
        self.assertEqual(m.PATCH, bytes.fromhex('e9 7d 01 00 00 90'))

    def test_rejects_wrong_source(self):
        with self.assertRaises(ValueError):
            m.patch_game(b'\0' * 1024)


if __name__ == '__main__':
    unittest.main()
