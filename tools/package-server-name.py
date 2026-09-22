"""Patch the localized server label and append a verified launcher patch package.

The external pak2zip 0.4 source supplies only its XOR tables (parsed, never
executed). Original PAK files and all previous packages remain unchanged.
"""
import argparse
import ast
import copy
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import zipfile
import zlib

CODEC_SHA = '5a7389756a81b1481a3e23321d6b19434e2495ea69979924b20999d145a15188'
LOCALES = ('DEU', 'ENG', 'FRA', 'RUS')
LABEL = 'AionCL 2.4'


def uint(value):
    result = bytearray()
    while value >= 128:
        result.append((value & 127) | 128)
        value >>= 7
    result.append(value)
    return bytes(result)


def parse_xml(data):
    if data[:1] != b'\x80':
        raise ValueError('Expected binary XML')
    pos = 1

    def read():
        nonlocal pos
        value = 0
        for shift in range(0, 35, 7):
            part = data[pos]
            pos += 1
            value |= (part & 127) << shift
            if part < 128:
                return value
        raise ValueError('Invalid packed integer')

    size = read()
    table = data[pos:pos + size]
    pos += size

    def string(offset):
        tail = table[offset * 2:]
        return tail.decode('utf-16-le').split('\0', 1)[0]

    def node():
        name, flags = read(), read()
        if flags & ~5:
            raise ValueError('Unsupported serverlist XML flags')
        text = read() if flags & 1 else None
        children = [node() for _ in range(read())] if flags & 4 else []
        return dict(name=name, text=text, flags=flags, children=children)

    root = node()
    if pos != len(data):
        raise ValueError('Unexpected XML trailer')
    return table, root, string


def encode_node(node):
    result = uint(node['name']) + uint(node['flags'])
    if node['flags'] & 1:
        result += uint(node['text'])
    if node['flags'] & 4:
        result += uint(len(node['children']))
        result += b''.join(encode_node(child) for child in node['children'])
    return result


def patch_xml(data):
    table, root, string = parse_xml(data)
    if string(root['name']) != 'servers':
        raise ValueError('Unexpected server list root')
    if b'\x80' + uint(len(table)) + table + encode_node(root) != data:
        raise ValueError('Original binary XML roundtrip failed')
    targets = []
    for server in root['children']:
        fields = {string(n['name']): n for n in server['children']}
        if string(fields['id']['text']) == '1':
            targets.append(fields['name'])
    if len(targets) != 1:
        raise ValueError('Expected exactly one server with ID 1')
    original_root = copy.deepcopy(root)
    targets[0]['text'] = len(table) // 2
    new_table = table + (LABEL + '\0').encode('utf-16-le')
    patched = b'\x80' + uint(len(new_table)) + new_table + encode_node(root)
    verified_table, verified_root, verified_string = parse_xml(patched)
    if verified_root != root or verified_string(targets[0]['text']) != LABEL:
        raise ValueError('Patched binary XML roundtrip failed')
    # Every old string remains byte-identical; only one name reference changes.
    assert verified_table[:len(table)] == table
    targets[0]['text'] = next(n['text'] for server in original_root['children']
        for n in server['children'] if string(n['name']) == 'name'
        and any(string(c['name']) == 'id' and string(c['text']) == '1' for c in server['children']))
    assert root == original_root
    return patched


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_tables(path):
    data = path.read_bytes()
    if digest(data) != CODEC_SHA:
        raise ValueError('Unexpected pak2zip reference source')
    source = data.decode()
    return [ast.literal_eval('(' + re.search(
        r"table%d = array\('B',\s*(.*?)\n\)" % n, source, re.S)[1]
        + ')').encode('latin1') for n in (1, 2)]


def transform(data, tables, encode=False):
    """Convert classic PAK/ZIP headers and the first 32 compressed bytes."""
    result = bytearray(data)
    pos = 0
    while pos < len(result):
        sig = bytes(result[pos:pos + 4])
        source = (b'PK\3\4', b'PK\1\2', b'PK\5\6')
        target = (b'\xaf\xb4\xfc\xfb', b'\xaf\xb4\xfe\xfd', b'\xaf\xb4\xfa\xf9')
        if not encode:
            source, target = target, source
        if sig == source[0]:
            result[pos:pos + 4] = target[0]
            method = struct.unpack_from('<H', result, pos + 8)[0]
            crc, size, raw_size, name_size, extra_size = struct.unpack_from('<IIIHH', result, pos + 14)
            start = pos + 30 + name_size + extra_size
            if method not in (0, 8) or start + size > len(result):
                raise ValueError('Unsupported or truncated PAK entry')
            candidates = [(tables[1], size & 1023)] if encode else [
                (tables[0], (size & 31) * 32), (tables[1], size & 1023)]
            for table, offset in candidates:
                payload = bytearray(result[start:start + size])
                for i in range(min(size, 32)):
                    payload[i] ^= table[offset + i]
                if encode:
                    break
                try:
                    raw = zlib.decompress(payload, -15) if method == 8 else payload
                except zlib.error:
                    continue
                if len(raw) == raw_size and zlib.crc32(raw) == crc:
                    break
            else:
                raise ValueError('PAK entry CRC mismatch')
            result[start:start + size] = payload
            pos = start + size
        elif sig == source[1]:
            result[pos:pos + 4] = target[1]
            sizes = struct.unpack_from('<HHH', result, pos + 28)
            pos += 46 + sum(sizes)
        elif sig == source[2]:
            result[pos:pos + 4] = target[2]
            if pos + 22 + struct.unpack_from('<H', result, pos + 20)[0] != len(result):
                raise ValueError('Unexpected PAK trailer')
            return bytes(result)
        else:
            raise ValueError('Unexpected archive signature')
    raise ValueError('Missing archive trailer')


def patch_pak(data, tables):
    decoded = transform(data, tables)
    target = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(decoded)) as original:
        matches = [n for n in original.namelist() if n.lower() == 'ui/serverlist.xml']
        if len(matches) != 1:
            raise ValueError('Expected exactly one serverlist entry')
        key = matches[0]
        patched = patch_xml(original.read(key))
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as output:
            for info in original.infolist():
                output.writestr(copy.copy(info), patched if info.filename == key else original.read(info))
        packed = transform(target.getvalue(), tables, encode=True)
        with zipfile.ZipFile(io.BytesIO(transform(packed, tables))) as verified:
            if verified.namelist() != original.namelist() or verified.testzip():
                raise ValueError('PAK roundtrip failed')
            for name in original.namelist():
                expected = patched if name == key else original.read(name)
                if verified.read(name) != expected:
                    raise ValueError('Unexpected PAK entry change: ' + name)
    return packed


def build(manifest_path, client, codec, output, version, *, patcher=patch_pak,
          description='only server label changed'):
    original = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    if not re.fullmatch(r'2\.4\.[0-9]+', version) or tuple(map(int, version.split('.'))) <= tuple(map(int, original['clientVersion'].split('.'))):
        raise ValueError('Expected a newer 2.4.N version')
    if original['formatVersion'] != 1 or original['product'] != 'AionCL':
        raise ValueError('Unsupported manifest')
    tables = load_tables(codec)
    effective = {f['path'].lower(): f for p in original['packages'] for f in p['files']}
    output.mkdir(parents=True, exist_ok=False)
    entries = {}
    for locale in LOCALES:
        path = effective[f'l10n/{locale}/data/data.pak'.lower()]['path']
        source = (client / path).read_bytes()
        expected = effective[path.lower()]
        if len(source) != expected['size'] or digest(source) != expected['sha256']:
            raise ValueError('Source differs from published manifest: ' + path)
        entries[path] = patcher(source, tables)
        print(locale + ': PASS all PAK entries verified; ' + description, flush=True)
    name = f'aioncl-client-{version}-{len(original["packages"]) + 1:03}.zip'
    archive = output / name
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path, data in entries.items():
            info = zipfile.ZipInfo(path, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
    with zipfile.ZipFile(archive) as z:
        if z.testzip() or set(z.namelist()) != set(entries):
            raise ValueError('Package roundtrip failed')
        for path, data in entries.items():
            if z.read(path) != data:
                raise ValueError('Package content mismatch')
    files = [dict(path=p, size=len(d), sha256=digest(d)) for p, d in entries.items()]
    manifest = copy.deepcopy(original)
    manifest['packages'].append(dict(name=name, size=archive.stat().st_size,
        sha256=digest(archive.read_bytes()), fileCount=len(files),
        uncompressedSize=sum(f['size'] for f in files), files=files,
        mirrors=[f'https://github.com/AionCL/client-2.4/releases/download/v{version}/{name}']))
    manifest['clientVersion'] = version
    for field, key in [('sourceFileCount', 'fileCount'), ('sourceBytes', 'uncompressedSize'), ('compressedBytes', 'size')]:
        manifest[field] = sum(p[key] for p in manifest['packages'])
    manifest['buildId'] = digest(json.dumps(manifest['packages'], sort_keys=True).encode())
    assert manifest['packages'][:-1] == original['packages']
    target = output / 'install-manifest.json'
    target.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    lines = [f"{p['sha256']}  {p['name']}" for p in manifest['packages']]
    lines.append(f'{digest(target.read_bytes())}  install-manifest.json')
    (output / 'SHA256SUMS').write_text('\n'.join(lines) + '\n', encoding='ascii')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'client', 'codec', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()
    result = build(args.manifest, args.client, args.codec, args.output, args.version)
    print(result['packages'][-1]['name'], result['packages'][-1]['sha256'])
