"""Client 2.4.10: make Siel packs normal tradable consumables without native recharge prompts."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import zipfile

spec = importlib.util.spec_from_file_location('siel', Path(__file__).with_name('package-siel-energy.py'))
siel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(siel)
base = siel.base
FLAGS = ('can_exchange', 'can_sell_to_npc', 'can_deposit_to_character_warehouse',
         'can_deposit_to_account_warehouse', 'can_deposit_to_guild_warehouse',
         'can_world_vendor', 'item_drop_permitted', 'can_split')


def patch_items(data):
    xml = siel.shop.BinaryXml(data)
    for item_id in siel.PACKS:
        nodes = [n for n in xml.root['children'] if siel.fields(xml, n).get('id') == str(item_id)]
        if len(nodes) != 1:
            raise ValueError('Expected one existing Siel pack: ' + str(item_id))
        node = nodes[0]
        # Account duration is applied by the server. Native recharge minutes
        # invoke the ticket/double-deduction UI; these are ordinary consumables.
        values = {k: 'TRUE' for k in FLAGS}
        values.update(cash_item=0, cash_available_minute=0, confirm_to_delete_cash_item='FALSE',
                      soul_bind='FALSE', lore='FALSE', activation_mode='Both', activation_count=1)
        for k, v in values.items():
            siel.set_field(xml, node, k, v)
    result = xml.encode()
    assert siel.shop.BinaryXml(result).root == xml.root
    return result


def build(manifest_path, client, codec, output):
    original = json.loads(manifest_path.read_text())
    if original['clientVersion'] != '2.4.9':
        raise ValueError('Expected published 2.4.9 manifest')
    effective = {f['path'].lower(): f for p in original['packages'] for f in p['files']}
    expected = effective['data/items/items.pak']
    data = (client / expected['path']).read_bytes()
    assert len(data) == expected['size'] and base.digest(data) == expected['sha256']
    result = siel.patch_archive(data, base.load_tables(codec), 'client_items.xml', patch_items)
    output.mkdir(parents=True, exist_ok=False)
    name = 'aioncl-client-2.4.10-' + str(len(original['packages']) + 1).zfill(3) + '.zip'
    archive = output / name
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(expected['path'], result)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and z.namelist() == [expected['path']]
        assert z.read(expected['path']) == result
    manifest = copy.deepcopy(original)
    files = [dict(path=expected['path'], size=len(result), sha256=base.digest(result))]
    manifest['packages'].append(dict(name=name, size=archive.stat().st_size, sha256=base.digest(archive.read_bytes()),
        fileCount=1, uncompressedSize=len(result), files=files,
        mirrors=['https://github.com/AionCL/client-2.4/releases/download/v2.4.10/' + name]))
    manifest['clientVersion'] = '2.4.10'
    for field, key in [('sourceFileCount', 'fileCount'), ('sourceBytes', 'uncompressedSize'), ('compressedBytes', 'size')]:
        manifest[field] = sum(p[key] for p in manifest['packages'])
    manifest['buildId'] = base.digest(json.dumps(manifest['packages'], sort_keys=True).encode())
    assert manifest['packages'][:-1] == original['packages']
    target = output / 'install-manifest.json'
    target.write_text(json.dumps(manifest, indent=2) + '\n')
    (output / 'SHA256SUMS').write_text('\n'.join([p['sha256'] + '  ' + p['name'] for p in manifest['packages']]
        + [base.digest(target.read_bytes()) + '  install-manifest.json']) + '\n')
    print('PASS: tradable packs; archive roundtrip; all other entries and previous packages preserved')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'client', 'codec', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    a = parser.parse_args()
    build(a.manifest, a.client, a.codec, a.output)
