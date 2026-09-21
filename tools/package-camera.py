"""Append the standalone camera helper without rebuilding any base archive."""
import argparse
import copy
import hashlib
import json
import pathlib
import re
import struct
import zipfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build(manifest_path, helper_path, output, version):
    if not re.fullmatch(r"2\.4\.[0-9]+", version):
        raise ValueError("Invalid client version")
    original = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if original["formatVersion"] != 1 or original["product"] != "AionCL":
        raise ValueError("Unsupported base manifest")
    if tuple(map(int, version.split('.'))) <= tuple(map(int, original["clientVersion"].split('.'))):
        raise ValueError("Version must increase")
    data = helper_path.read_bytes()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    if data[:2] != b"MZ" or data[pe:pe+4] != b"PE\0\0" or struct.unpack_from("<H", data, pe+4)[0] != 0x8664:
        raise ValueError("Expected x64 PE helper")
    if output.exists():
        raise FileExistsError("Output directory must be new")
    output.mkdir(parents=True)
    manifest = copy.deepcopy(original)
    number = len(manifest["packages"]) + 1
    name = f"aioncl-client-{version}-{number:03}.zip"
    path = "tools/AionCL.Camera.exe"
    archive = output / name
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zip_file:
        info = zipfile.ZipInfo(path, date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        zip_file.writestr(info, data)
    with zipfile.ZipFile(archive) as zip_file:
        if zip_file.namelist() != [path] or zip_file.read(path) != data or zip_file.testzip():
            raise ValueError("Package roundtrip failed")
    package = dict(name=name, size=archive.stat().st_size, sha256=digest(archive.read_bytes()),
                   fileCount=1, uncompressedSize=len(data),
                   mirrors=[f"https://github.com/AionCL/client-2.4/releases/download/v{version}/{name}"],
                   files=[dict(path=path, size=len(data), sha256=digest(data))])
    manifest["packages"].append(package)
    manifest["clientVersion"] = version
    manifest["sourceFileCount"] = sum(p["fileCount"] for p in manifest["packages"])
    manifest["sourceBytes"] = sum(p["uncompressedSize"] for p in manifest["packages"])
    manifest["compressedBytes"] = sum(p["size"] for p in manifest["packages"])
    manifest["buildId"] = digest(json.dumps(manifest["packages"], sort_keys=True).encode())
    assert manifest["packages"][:-1] == original["packages"]
    target = output / "install-manifest.json"
    target.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    lines = [f"{p['sha256']}  {p['name']}" for p in manifest["packages"]]
    lines.append(f"{digest(target.read_bytes())}  install-manifest.json")
    (output / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="ascii")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--helper", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    result = build(args.manifest, args.helper, args.output, args.version)
    print(result["packages"][-1]["name"], result["packages"][-1]["sha256"])
