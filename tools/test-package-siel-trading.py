import importlib.util
from pathlib import Path
import unittest


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


trading = load('trading', 'package-siel-trading.py')
fixture = load('fixture', 'test-package-siel-energy.py')


class Trading(unittest.TestCase):
    def test_trade_flags_no_native_prompt_and_unrelated_preserved(self):
        raw = trading.siel.patch_items(fixture.fixture().encode())
        before = trading.siel.shop.BinaryXml(raw)
        after = trading.siel.shop.BinaryXml(trading.patch_items(raw))
        self.assertEqual(before.root['children'][1], after.root['children'][1])
        for item_id, (days, _) in trading.siel.PACKS.items():
            f = next(trading.siel.fields(after, n) for n in after.root['children']
                     if trading.siel.fields(after, n)['id'] == str(item_id))
            for flag in trading.FLAGS:
                self.assertEqual('TRUE', f[flag])
            self.assertEqual('0', f['cash_available_minute'])
            self.assertEqual('0', f['cash_item'])
            self.assertEqual('FALSE', f['soul_bind'])
            self.assertEqual('1', f['activation_count'])
            self.assertEqual(trading.siel.pack_name(days), f['desc'])
            self.assertEqual('gold', f['icon_name'])

    def test_missing_pack_rejected(self):
        with self.assertRaises(ValueError):
            trading.patch_items(fixture.fixture().encode())


if __name__ == '__main__':
    unittest.main()
