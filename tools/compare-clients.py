#!/usr/bin/env python3
"""Compare two Aion client trees without modifying either one.

Produces JSON and CSV reports suitable for deciding what belongs in the clean
base client and what must become an optional AionCL patch.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path


def sha256(path, chunk=1024 * 1024):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while True:
            data = stream.read(chunk)
            if not data:
                break
            digest.update(data)
    return digest.hexdigest()


def inventory(root, do_hash):
    result = {}
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        rel = path.relative_to(root).as_posix()
        stat = path.stat()
        item = {"size": stat.st_size}
        if do_hash:
            item["sha256"] = sha256(path)
        result[rel] = item
    return result


def language_dirs(root):
    for candidate in (root / "l10n", root / "L10N"):
        if candidate.is_dir():
            return sorted(p.name for p in candidate.iterdir() if p.is_dir())
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=Path, help="clean/base client directory")
    parser.add_argument("candidate", type=Path, help="second client directory")
    parser.add_argument("--output", type=Path, default=Path("client-comparison"))
    parser.add_argument("--hash", action="store_true", help="hash every file; slower but authoritative")
    args = parser.parse_args()
    for root in (args.base, args.candidate):
        if not root.is_dir():
            parser.error(f"directory not found: {root}")
    args.output.mkdir(parents=True, exist_ok=True)
    left = inventory(args.base, args.hash)
    right = inventory(args.candidate, args.hash)
    rows = []
    for rel in sorted(set(left) | set(right)):
        a, b = left.get(rel), right.get(rel)
        if a is None:
            state = "candidate-only"
        elif b is None:
            state = "base-only"
        elif a.get("sha256", a["size"]) == b.get("sha256", b["size"]):
            state = "same"
        else:
            state = "different"
        rows.append({"path": rel, "state": state,
                     "base_size": "" if a is None else a["size"],
                     "candidate_size": "" if b is None else b["size"],
                     "base_sha256": "" if a is None else a.get("sha256", ""),
                     "candidate_sha256": "" if b is None else b.get("sha256", "")})
    report = {
        "base": str(args.base.resolve()),
        "candidate": str(args.candidate.resolve()),
        "hashed": args.hash,
        "languages": {"base": language_dirs(args.base), "candidate": language_dirs(args.candidate)},
        "counts": {state: sum(row["state"] == state for row in rows)
                   for state in ("same", "different", "base-only", "candidate-only")},
        "files": rows,
    }
    (args.output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (args.output / "files.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"output": str(args.output.resolve()), "languages": report["languages"], "counts": report["counts"]}, indent=2))


if __name__ == "__main__":
    main()
