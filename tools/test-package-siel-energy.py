"""Verify unrestricted Siel packs using a small binary XML fixture."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('siel', Path(__file__).with_name('package-siel-energy.py'))
siel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(siel)


def fixture():
    x = object.__new__(siel.shop.BinaryXml)
    x.table = b''
    x.cache = {}
    x.root = dict(name=x.add('items'), flags=4, text=None, attrs=[], children=[])
    n = dict(name=x.add('item'), flags=4, text=None, attrs=[], children=[])
    for k, v in dict(id=169700010, name='original', icon_name='gold', level=45, expire_time=10081,
                     quality='common', warrior_max=45, warrior=1, cash_available_minute=1440).items():
        siel.set_field(x, n, k, v)
    x.root['children'].append(n)
    unrelated = copy.deepcopy(n)
    siel.set_field(x, unrelated, 'id', 100000001)
    x.root['children'].append(unrelated)
    return x


class Packs(unittest.TestCase):
    def test_unrestricted_and_unrelated_preserved(self):
        original = fixture()
        patched = siel.shop.BinaryXml(siel.patch_items(original.encode()))
        self.assertEqual(original.root['children'][1], patched.root['children'][1])
        for i, (days, _) in siel.PACKS.items():
            f = next(siel.fields(patched, n) for n in patched.root['children'] if siel.fields(patched, n)['id'] == str(i))
            self.assertEqual('gold', f['icon_name'])
            self.assertEqual('1', f['level'])
            self.assertEqual(str(days * 1440), f['cash_available_minute'])
            self.assertNotIn('warrior_max', f)
            self.assertNotIn('expire_time', f)
            self.assertEqual(siel.pack_name(days), f['desc'])

    def test_collision_rejected(self):
        x = fixture()
        siel.set_field(x, x.root['children'][1], 'id', 169700011)
        with self.assertRaises(ValueError):
            siel.patch_items(x.encode())

    def test_locales_and_string_collisions(self):
        for locale in ('FRA', 'DEU', 'ENG', 'RUS'):
            x = fixture()
            data = siel.patch_strings(x.encode(), locale)
            parsed = siel.shop.BinaryXml(data)
            for days, sid in siel.PACKS.values():
                for offset, text in enumerate(siel.localized(locale, days)):
                    f = next(siel.fields(parsed, n) for n in parsed.root['children'] if siel.fields(parsed, n)['id'] == str(sid + offset))
                    self.assertEqual(text, f['body'])
            with self.assertRaises(ValueError):
                siel.patch_strings(data, locale)


if __name__ == '__main__':
    unittest.main()
