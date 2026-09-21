"""Binary server list regression tests; no installed client required."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('package_server_name', Path(__file__).with_name('package-server-name.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture(ids=('1', '2'), names=('QA1 Server 1', 'Other server')):
    table = bytearray(b'\0\0')
    def string(value):
        offset = len(table) // 2
        table.extend((value + '\0').encode('utf-16-le'))
        return offset
    def text(name, value):
        return dict(name=string(name), flags=1, text=string(value), children=[])
    root = dict(name=string('servers'), flags=4, text=None, children=[])
    for server_id, name in zip(ids, names):
        root['children'].append(dict(name=string('server'), flags=4, text=None,
            children=[text('id', server_id), text('name', name), text('lang', 'ENG')]))
    return b'\x80' + m.uint(len(table)) + table + m.encode_node(root)


def values(data):
    _, root, string = m.parse_xml(data)
    return [{string(c['name']): string(c['text']) for c in n['children']} for n in root['children']]


class ServerNameTests(unittest.TestCase):
    def test_only_server_one_changes(self):
        source = fixture()
        expected = values(source)
        expected[0]['name'] = 'AionCL 2.4'
        self.assertEqual(values(m.patch_xml(source)), expected)

    def test_short_cyrillic_name_can_grow(self):
        source = fixture(names=('Тест', 'Другой'))
        result = values(m.patch_xml(source))
        self.assertEqual(result[0]['name'], 'AionCL 2.4')
        self.assertEqual(result[1]['name'], 'Другой')

    def test_missing_or_duplicate_id_rejected(self):
        for ids in [('2', '3'), ('1', '1')]:
            with self.assertRaises(ValueError):
                m.patch_xml(fixture(ids=ids))

    def test_trailer_rejected(self):
        with self.assertRaises(ValueError):
            m.patch_xml(fixture() + b'\0')

    def test_wrong_format_rejected(self):
        with self.assertRaises(ValueError):
            m.patch_xml(b'<servers/>')


if __name__ == '__main__':
    unittest.main()
