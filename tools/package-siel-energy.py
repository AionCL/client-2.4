"""Add account Siel packs (1/7/30 days) with no level ceiling or item expiry."""
import argparse
import copy
import importlib.util
import io
import json
from pathlib import Path
import zipfile

spec = importlib.util.spec_from_file_location('shop', Path(__file__).with_name('package-shop-icons.py'))
shop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shop)
base = shop.base
PACKS = {169700010: (30, 799900), 169700011: (1, 799902), 169700012: (7, 799904)}
CLASSES = ('warrior', 'scout', 'mage', 'cleric', 'fighter', 'knight', 'assassin', 'ranger', 'wizard', 'elementalist', 'chanter', 'priest')


def fields(xml, node):
    return {xml.string(c['name']): xml.string(c['text']) for c in node['children'] if c['text'] is not None}


def set_field(xml, node, key, value):
    matches = [c for c in node['children'] if xml.string(c['name']) == key]
    if len(matches) > 1:
        raise ValueError('Duplicate field ' + key)
    if matches:
        matches[0]['text'] = xml.add(str(value))
        matches[0]['flags'] |= 1
    else:
        node['children'].append(dict(name=xml.add(key), flags=1, text=xml.add(str(value)), attrs=[], children=[]))
        node['flags'] |= 4


def pack_name(days):
    return 'STR_AIONCL_SIEL_ENERGY_' + str(days) + 'D'


def patch_items(data):
    xml = shop.BinaryXml(data)
    candidates = [n for n in xml.root['children'] if fields(xml, n).get('id') == '169700010']
    if len(candidates) != 1:
        raise ValueError('Missing monthly source item')
    source = candidates[0]
    ids = {fields(xml, n).get('id') for n in xml.root['children']}
    if any(str(i) in ids for i in PACKS if i != 169700010):
        raise ValueError('Custom item ID collision')
    # Clone before altering the original so all packs share its native gold icon.
    originals = {i: source if i == 169700010 else copy.deepcopy(source) for i in PACKS}
    for item_id, (days, _) in PACKS.items():
        node = originals[item_id]
        node['children'] = [c for c in node['children'] if xml.string(c['name']) not in ('expire_time',) + tuple(k + '_max' for k in CLASSES)]
        values = dict(id=item_id, level=1, max_stack_count=100, cash_available_minute=days * 1440,
                      desc=pack_name(days), desc_long=pack_name(days) + '_DESC', casting_delay=0,
                      can_split='TRUE', quality='common')
        if item_id != 169700010:
            values['name'] = 'aioncl_siel_energy_' + str(days) + 'day' + ('s' if days > 1 else '')
        for key in CLASSES:
            values[key] = 1
        for key, value in values.items():
            set_field(xml, node, key, value)
        if item_id != 169700010:
            xml.root['children'].append(node)
    result = xml.encode()
    checked = shop.BinaryXml(result)
    for i, (days, _) in PACKS.items():
        nodes = [n for n in checked.root['children'] if fields(checked, n).get('id') == str(i)]
        assert len(nodes) == 1
        f = fields(checked, nodes[0])
        assert f['level'] == '1' and f['cash_available_minute'] == str(days * 1440)
        assert 'expire_time' not in f and not any(k + '_max' in f for k in CLASSES)
        assert f['icon_name'] == fields(xml, source)['icon_name']
    return result


def localized(locale, days):
    if locale == 'FRA':
        return ('Énergie de Siel (' + str(days) + (' jour)' if days == 1 else ' jours)'),
                'Active ou prolonge l’énergie de Siel de ' + str(days) + ' jour(s) pour tout le compte. '
                'Utilisable à tous les niveaux. La durée s’ajoute au temps restant et continue de s’écouler hors connexion. '
                'Double-cliquez pour l’utiliser.')
    if locale == 'DEU':
        return ('Siels Energie (' + str(days) + (' Tag)' if days == 1 else ' Tage)'),
                'Aktiviert oder verlängert Siels Energie für den gesamten Account um ' + str(days) + ' Tag(e). '
                'Auf jeder Stufe nutzbar. Die Dauer wird zur Restzeit addiert und läuft auch offline weiter. '
                'Zum Verwenden doppelklicken.')
    if locale == 'RUS':
        return ('Энергия Сиэль (' + str(days) + ' дн.)',
                'Активирует или продлевает энергию Сиэль на ' + str(days) + ' дн. для всей учётной записи. '
                'Доступно на любом уровне. Срок добавляется к оставшемуся времени и истекает также вне игры. '
                'Дважды щёлкните для использования.')
    return ("Siel's Energy (" + str(days) + (' day)' if days == 1 else ' days)'),
            "Activates or extends Siel's Energy by " + str(days) + ' day(s) for the entire account. '
            'Usable at every level. Duration is added to remaining time and continues while offline. '
            'Double-click to use.')


def patch_strings(data, locale):
    xml = shop.BinaryXml(data)
    entries = [fields(xml, n) for n in xml.root['children']]
    reserved = {str(n + offset) for _, n in PACKS.values() for offset in (0, 1)}
    names = {pack_name(d) + suffix for d, _ in PACKS.values() for suffix in ('', '_DESC')}
    if any(f.get('id') in reserved or f.get('name') in names for f in entries):
        raise ValueError('Custom string ID/name collision')
    for days, string_id in PACKS.values():
        for offset, body in enumerate(localized(locale, days)):
            node = dict(name=xml.add('string'), flags=4, text=None, attrs=[], children=[])
            for k, v in dict(id=string_id + offset, name=pack_name(days) + ('_DESC' if offset else ''), body=body).items():
                set_field(xml, node, k, v)
            xml.root['children'].append(node)
    result = xml.encode()
    assert shop.BinaryXml(result).root == xml.root
    return result


def patch_archive(data, tables, entry, patcher):
    with zipfile.ZipFile(io.BytesIO(base.transform(data, tables))) as original:
        keys = [n for n in original.namelist() if n.lower() == entry.lower()]
        if len(keys) != 1:
            raise ValueError('Missing archive entry ' + entry)
        key = keys[0]
        changed = patcher(original.read(key))
        out = io.BytesIO()
        with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as target:
            for info in original.infolist():
                target.writestr(copy.copy(info), changed if info.filename == key else original.read(info))
        packed = base.transform(out.getvalue(), tables, encode=True)
        with zipfile.ZipFile(io.BytesIO(base.transform(packed, tables))) as checked:
            assert checked.testzip() is None and checked.namelist() == original.namelist()
            for n in original.namelist():
                assert checked.read(n) == (changed if n == key else original.read(n)), n
        return packed


def build(manifest_path, client, codec, output):
    original = json.loads(manifest_path.read_text())
    if original['clientVersion'] != '2.4.8':
        raise ValueError('Expected published 2.4.8 manifest')
    effective = {f['path'].lower(): f for p in original['packages'] for f in p['files']}
    tables = base.load_tables(codec)
    entries = {}
    for path in ['data/items/items.pak'] + ['l10n/' + l + '/data/data.pak' for l in base.LOCALES]:
        expected = effective[path.lower()]
        data = (client / expected['path']).read_bytes()
        assert len(data) == expected['size'] and base.digest(data) == expected['sha256'], path
        if path.startswith('data/'):
            result = patch_archive(data, tables, 'client_items.xml', patch_items)
        else:
            locale = path.split('/')[1]
            result = patch_archive(data, tables, 'strings/client_strings_item2.xml', lambda b: patch_strings(b, locale))
        entries[expected['path']] = result
        print(path + ': PASS archive contents verified', flush=True)
    output.mkdir(parents=True, exist_ok=False)
    name = 'aioncl-client-2.4.9-' + str(len(original['packages']) + 1).zfill(3) + '.zip'
    archive = output / name
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        for path, data in entries.items():
            z.writestr(path, data)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(z.read(path) == data for path, data in entries.items())
    manifest = copy.deepcopy(original)
    files = [dict(path=p, size=len(d), sha256=base.digest(d)) for p, d in entries.items()]
    manifest['packages'].append(dict(name=name, size=archive.stat().st_size, sha256=base.digest(archive.read_bytes()),
        fileCount=len(files), uncompressedSize=sum(f['size'] for f in files), files=files,
        mirrors=['https://github.com/AionCL/client-2.4/releases/download/v2.4.9/' + name]))
    manifest['clientVersion'] = '2.4.9'
    for field, key in [('sourceFileCount', 'fileCount'), ('sourceBytes', 'uncompressedSize'), ('compressedBytes', 'size')]:
        manifest[field] = sum(p[key] for p in manifest['packages'])
    manifest['buildId'] = base.digest(json.dumps(manifest['packages'], sort_keys=True).encode())
    assert manifest['packages'][:-1] == original['packages']
    target = output / 'install-manifest.json'
    target.write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'SHA256SUMS').write_text('\n'.join([p['sha256'] + '  ' + p['name'] for p in manifest['packages']]
        + [base.digest(target.read_bytes()) + '  install-manifest.json']) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'client', 'codec', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    build(args.manifest, args.client, args.codec, args.output)
