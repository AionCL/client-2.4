"""Suppress native Aion shop visuals without removing widgets used by game code."""
import argparse
import copy
import importlib.util
import io
from pathlib import Path
import zipfile

spec = importlib.util.spec_from_file_location('package_server_name', Path(__file__).with_name('package-server-name.py'))
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
TARGETS = {
    'ui/game_hud_s1/radar_dialog.xml': ('item_shop', 'item_shop_bg'),
    'ui/game_hud_s2/radar_dialog.xml': ('item_shop', 'item_shop_bg'),
    'ui/game/player_info_dialog.xml': ('btn_web_shop',),
}
FRAME = '-10000,-10000,0,0'
FLAGS = 'not_visible;not_active;not_enabled;not_focusable'


class BinaryXml:
    def __init__(self, data):
        if data[:1] != b'\x80':
            raise ValueError('Expected binary XML')
        self.pos = 1
        self.data = data
        size = self.read()
        if size % 2 or self.pos + size > len(data):
            raise ValueError('Invalid string table')
        self.table = data[self.pos:self.pos + size]
        self.pos += size
        self.cache = {}
        self.root = self.node()
        if self.pos != len(data) or self.encode() != data:
            raise ValueError('XML roundtrip or trailer mismatch')

    def read(self):
        value = 0
        for shift in range(0, 35, 7):
            if self.pos >= len(self.data):
                raise ValueError('Truncated XML')
            part = self.data[self.pos]
            self.pos += 1
            value |= (part & 127) << shift
            if part < 128:
                return value
        raise ValueError('Invalid packed integer')

    def string(self, offset):
        if offset not in self.cache:
            start = offset * 2
            end = start
            while end + 2 <= len(self.table) and self.table[end:end + 2] != b'\0\0':
                end += 2
            if end + 2 > len(self.table):
                raise ValueError('Invalid string reference')
            self.cache[offset] = self.table[start:end].decode('utf-16-le')
        return self.cache[offset]

    def add(self, value):
        offset = len(self.table) // 2
        self.table += (value + '\0').encode('utf-16-le')
        return offset

    def node(self):
        name, flags = self.read(), self.read()
        if flags & ~7:
            raise ValueError('Unknown XML flags')
        text = self.read() if flags & 1 else None
        attrs = [(self.read(), self.read()) for _ in range(self.read())] if flags & 2 else []
        children = [self.node() for _ in range(self.read())] if flags & 4 else []
        return dict(name=name, flags=flags, text=text, attrs=attrs, children=children)

    def attrs(self, node):
        result = {self.string(k): self.string(v) for k, v in node['attrs']}
        if len(result) != len(node['attrs']):
            raise ValueError('Duplicate attributes')
        return result

    def encode(self):
        def emit(n):
            out = base.uint(n['name']) + base.uint(n['flags'])
            if n['flags'] & 1:
                out += base.uint(n['text'])
            if n['flags'] & 2:
                out += base.uint(len(n['attrs']))
                out += b''.join(base.uint(k) + base.uint(v) for k, v in n['attrs'])
            if n['flags'] & 4:
                out += base.uint(len(n['children']))
                out += b''.join(emit(c) for c in n['children'])
            return out
        return b'\x80' + base.uint(len(self.table)) + self.table + emit(self.root)

    def walk(self, node=None):
        node = self.root if node is None else node
        yield node
        for child in node['children']:
            yield from self.walk(child)


def patch_xml(data, names):
    xml = BinaryXml(data)
    before = copy.deepcopy(xml.root)
    original_table = xml.table
    changed = []
    for name in names:
        matches = [n for n in xml.walk() if xml.string(n['name']) == 'Widget' and xml.attrs(n).get('name') == name]
        if len(matches) != 1:
            raise ValueError('Expected exactly one shop widget: ' + name)
        n = matches[0]
        attrs = xml.attrs(n)
        expected_type = 'image' if name.endswith('_bg') else 'button'
        if attrs.get('type') != expected_type:
            raise ValueError('Unexpected shop widget type: ' + name)
        saved = copy.deepcopy(n)
        # Preserve native pointer lookup and concrete widget class. The engine
        # may toggle visibility at runtime, so a hidden flag alone is inadequate.
        # No skin, preset, effect, tooltip, text, focus or clickable rectangle.
        n['attrs'] = [(k, v) for k, v in n['attrs'] if xml.string(k) in ('name', 'type')]
        n['attrs'] += [(xml.add('frame'), xml.add(FRAME)), (xml.add('flag'), xml.add(FLAGS))]
        n['children'] = []
        n['text'] = None
        n['flags'] = 2
        changed.append((n, saved))
    result = xml.encode()
    verified = BinaryXml(result)
    if verified.root != xml.root or verified.table[:len(original_table)] != original_table:
        raise ValueError('Patched XML verification failed')
    for n, saved in changed:
        n.clear()
        n.update(saved)
    if xml.root != before:
        raise ValueError('Unrelated UI node changed')
    return result


def patch_pak(data, tables):
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(base.transform(data, tables))) as source:
        keys = {n.lower(): n for n in source.namelist()}
        if len(keys) != len(source.namelist()) or not TARGETS.keys() <= keys.keys():
            raise ValueError('Missing or duplicate UI archive paths')
        changes = {keys[k]: patch_xml(source.read(keys[k]), names) for k, names in TARGETS.items()}
        with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as target:
            for info in source.infolist():
                target.writestr(copy.copy(info), changes.get(info.filename, source.read(info)))
        packed = base.transform(out.getvalue(), tables, encode=True)
        with zipfile.ZipFile(io.BytesIO(base.transform(packed, tables))) as checked:
            if checked.namelist() != source.namelist() or checked.testzip():
                raise ValueError('PAK roundtrip failed')
            for name in source.namelist():
                if checked.read(name) != changes.get(name, source.read(name)):
                    raise ValueError('Unexpected PAK change: ' + name)
    return packed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'client', 'codec', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    result = base.build(args.manifest, args.client, args.codec, args.output, args.version,
                        patcher=patch_pak, description='only five Aion shop widgets suppressed')
    print(result['packages'][-1]['name'], result['packages'][-1]['sha256'])
