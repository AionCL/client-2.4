"""Regression coverage for native-referenced UI placeholders and PAK isolation."""
import copy
import importlib.util
import io
from pathlib import Path
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('shops', Path(__file__).with_name('package-shop-icons.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture(names=('item_shop', 'item_shop_bg')):
    table = bytearray()
    def string(value):
        offset = len(table) // 2
        table.extend((value + '\0').encode('utf-16-le'))
        return offset
    def node(tag, attrs, children=()):
        return dict(name=string(tag), flags=2 | (4 if children else 0), text=None,
                    attrs=[(string(k), string(v)) for k, v in attrs.items()], children=list(children))
    widgets = [node('Widget', dict(name=n, type='image' if n.endswith('_bg') else 'button',
                                  frame='1,2,32,32', preset='shared_skin', fx_name='webshop',
                                  tooltip='shop_tooltip'), [node('Skin', dict(name='shared_skin'))]) for n in names]
    widgets.append(node('Widget', dict(name='flight', type='button', frame='3,4,32,32', preset='shared_skin')))
    root = node('Dialog', dict(name='radar_dialog'), widgets)
    xml = object.__new__(m.BinaryXml)
    xml.table = bytes(table)
    xml.root = root
    return xml.encode()


class ShopIconTests(unittest.TestCase):
    def test_shop_visuals_and_hitboxes_removed_but_native_names_and_types_preserved(self):
        result = m.BinaryXml(m.patch_xml(fixture(), ('item_shop', 'item_shop_bg')))
        for name, kind in [('item_shop', 'button'), ('item_shop_bg', 'image')]:
            n = next(n for n in result.walk() if result.attrs(n).get('name') == name)
            self.assertEqual(result.attrs(n), dict(name=name, type=kind, frame=m.FRAME, flag=m.FLAGS))
            self.assertEqual(n['children'], [])

    def test_shared_skin_and_unrelated_flight_control_unchanged(self):
        source = m.BinaryXml(fixture())
        result = m.BinaryXml(m.patch_xml(fixture(), ('item_shop', 'item_shop_bg')))
        def flight(xml):
            return next(n for n in xml.walk() if xml.attrs(n).get('name') == 'flight')
        self.assertEqual(flight(source), flight(result))
        self.assertEqual(result.table[:len(source.table)], source.table)

    def test_missing_duplicate_and_wrong_type_fail_closed(self):
        for names in [('item_shop_bg',), ('item_shop', 'item_shop')]:
            with self.assertRaises(ValueError):
                m.patch_xml(fixture(names), ('item_shop', 'item_shop_bg'))
        x = m.BinaryXml(fixture())
        n = x.root['children'][0]
        n['attrs'] = [(k, x.add('image') if x.string(k) == 'type' else v) for k, v in n['attrs']]
        with self.assertRaises(ValueError):
            m.patch_xml(x.encode(), ('item_shop', 'item_shop_bg'))

    def test_truncated_and_trailing_data_rejected(self):
        for data in [b'<xml/>', fixture()[:-1], fixture() + b'\0']:
            with self.assertRaises(ValueError):
                m.BinaryXml(data)

    def test_idempotent_widget_state(self):
        once = m.BinaryXml(m.patch_xml(fixture(), ('item_shop', 'item_shop_bg')))
        twice = m.BinaryXml(m.patch_xml(once.encode(), ('item_shop', 'item_shop_bg')))
        self.assertEqual([once.attrs(n) for n in once.walk()], [twice.attrs(n) for n in twice.walk()])

    def test_all_other_pak_entries_and_server_label_preserved(self):
        tables = [bytes(1056), bytes(1056)]
        stream = io.BytesIO()
        contents = {key: fixture(names) for key, names in m.TARGETS.items()}
        contents['ui/serverlist.xml'] = b'AionCL 2.4 server-name fixture'
        contents['textures/shared'] = b'unrelated shared texture'
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for name, data in contents.items():
                z.writestr(name, data)
        pak = m.base.transform(stream.getvalue(), tables, encode=True)
        patched = m.patch_pak(pak, tables)
        with zipfile.ZipFile(io.BytesIO(m.base.transform(patched, tables))) as z:
            self.assertEqual(z.namelist(), list(contents))
            for name in contents.keys() - m.TARGETS.keys():
                self.assertEqual(z.read(name), contents[name])


if __name__ == '__main__':
    unittest.main()
