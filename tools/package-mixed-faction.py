"""Package the validated Game.dll patch suppressing the obsolete mixed-faction merge warning."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import struct
import zipfile

PATH = 'bin64/Game.dll'

SOURCE_SHA256 = 'f259b60f74768c226eafff085551700bcaf3aa43a20ede7fe3925e0e31daaf0f'
PATCHED_SHA256 = '5fe3d86433122a007c9bb1b51ba6a5d380c83399a28166e3427f2d0a4a9cb9c0'

OFFSET = 0x2C6080
ORIGINAL = bytes.fromhex('8b 05 1a 67 bc 00')
TARGET = 0x2C6202
PATCH = b'\xE9' + struct.pack('<i', TARGET - (OFFSET + 5)) + b'\x90'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def patch_game(data):
    if digest(data) != SOURCE_SHA256:
        raise ValueError('Unexpected source Game.dll SHA-256')
    if data[OFFSET:OFFSET + len(ORIGINAL)] != ORIGINAL:
        raise ValueError('Unexpected bytes at Game.dll patch offset')

    result = bytearray(data)
    result[OFFSET:OFFSET + len(PATCH)] = PATCH
    result = bytes(result)

    if digest(result) != PATCHED_SHA256:
        raise ValueError('Patched Game.dll SHA-256 mismatch')
    return result


def build(manifest_path, client, output, version):
    original = json.loads(manifest_path.read_text(encoding='utf-8-sig'))

    if not re.fullmatch(r'2\.4\.[0-9]+', version):
        raise ValueError('Expected 2.4.N version')
    if tuple(map(int, version.split('.'))) <= tuple(map(int, original['clientVersion'].split('.'))):
        raise ValueError('Expected a newer client version')
    if original['formatVersion'] != 1 or original['product'] != 'AionCL':
        raise ValueError('Unsupported manifest')

    effective = {
        f['path'].lower(): f
        for package in original['packages']
        for f in package['files']
    }

    expected = effective[PATH.lower()]
    source = (client / expected['path']).read_bytes()

    if len(source) != expected['size'] or digest(source) != expected['sha256']:
        raise ValueError('Source differs from published manifest: ' + expected['path'])
    if expected['sha256'] != SOURCE_SHA256:
        raise ValueError('Published effective Game.dll is not the supported clean build')

    patched = patch_game(source)

    output.mkdir(parents=True, exist_ok=False)

    name = f'aioncl-client-{version}-{len(original["packages"]) + 1:03}.zip'
    archive = output / name

    info = zipfile.ZipInfo(PATH, date_time=(2026, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED

    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr(info, patched)

    with zipfile.ZipFile(archive) as z:
        if z.testzip() or z.namelist() != [PATH]:
            raise ValueError('Package roundtrip failed')
        if z.read(PATH) != patched:
            raise ValueError('Package content mismatch')

    files = [dict(path=PATH, size=len(patched), sha256=digest(patched))]

    manifest = copy.deepcopy(original)
    manifest['packages'].append(dict(
        name=name,
        size=archive.stat().st_size,
        sha256=digest(archive.read_bytes()),
        fileCount=1,
        uncompressedSize=len(patched),
        files=files,
        mirrors=[
            'https:' + chr(47) + chr(47) + 'github.com' + chr(47) + 'AionCL' + chr(47) + 'client-2.4' + f'{chr(47)}releases{chr(47)}download{chr(47)}v{version}{chr(47)}{name}'
        ],
    ))
    manifest['clientVersion'] = version

    for field, key in [
        ('sourceFileCount', 'fileCount'),
        ('sourceBytes', 'uncompressedSize'),
        ('compressedBytes', 'size'),
    ]:
        manifest[field] = sum(p[key] for p in manifest['packages'])

    manifest['buildId'] = digest(
        json.dumps(manifest['packages'], sort_keys=True).encode()
    )

    assert manifest['packages'][:-1] == original['packages']

    target = output / 'install-manifest.json'
    target.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

    lines = [f"{p['sha256']}  {p['name']}" for p in manifest['packages']]
    lines.append(f'{digest(target.read_bytes())}  install-manifest.json')
    (output / 'SHA256SUMS').write_text('\n'.join(lines) + '\n', encoding='ascii')

    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--client', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--version', required=True)
    args = parser.parse_args()

    result = build(args.manifest, args.client, args.output, args.version)
    print(result['packages'][-1]['name'], result['packages'][-1]['sha256'])
