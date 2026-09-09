"""Rebuild the three shop packages from original ZIPs and patched PAK files.

The patched PAKs must be generated and round-trip verified by
website/tools/patch_client_shop_urls.py. This script never edits the original
ZIPs or client reference; it replaces exactly one localized data.pak entry.
"""
import argparse
import hashlib
import pathlib
import shutil
import zipfile

PACKAGES = {
    "002": "l10n/DEU/data/data.pak",
    "003": "l10n/ENG/data/data.pak",
    "004": "l10n/FRA/data/data.pak",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rebuild(original, patched, target, entry):
    with zipfile.ZipFile(original) as source, zipfile.ZipFile(
        target, "w", allowZip64=True, compression=zipfile.ZIP_DEFLATED, compresslevel=6
    ) as output:
        names = [info.filename for info in source.infolist()]
        if names.count(entry) != 1:
            raise ValueError(f"expected exactly one {entry} entry")
        for info in source.infolist():
            with source.open(info) as input_stream, output.open(info, "w", force_zip64=True) as output_stream:
                if info.filename == entry:
                    with patched.open("rb") as patched_stream:
                        shutil.copyfileobj(patched_stream, output_stream, 1024 * 1024)
                else:
                    shutil.copyfileobj(input_stream, output_stream, 1024 * 1024)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-dir", type=pathlib.Path, required=True)
    parser.add_argument("--patched-dir", type=pathlib.Path, required=True)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    parser.add_argument("--version", default="2.4.1")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for number, entry in PACKAGES.items():
        original = args.original_dir / f"aioncl-client-2.4.0-{number}.zip"
        patched = args.patched_dir / pathlib.Path(entry)
        target = args.output_dir / f"aioncl-client-{args.version}-{number}.zip"
        if not original.is_file() or not patched.is_file():
            raise FileNotFoundError(f"missing input for package {number}")
        rebuild(original, patched, target, entry)
        print(target.name, target.stat().st_size, sha256(target))


if __name__ == "__main__":
    main()
