#!/usr/bin/env python3
"""Build the release assets: one deterministic zip per pack plus dist/catalog.json.

Python 3, standard library only.

    python tools/build_catalog.py --tag v1.0.0
    python tools/build_catalog.py --tag v1.0.0 --out dist --generated-at 2026-10-21T18:00:00Z

Every pack is validated first (strict); a failing pack stops the build. Zips are reproducible:
entries sorted by path, fixed 1980-01-01 timestamps, fixed permission bits, stored without
compression (so the bytes do not depend on the zlib build), no directory entries. Signing is a
separate step: tools/sign_catalog.sh.
"""
import argparse
import datetime
import hashlib
import json
import os
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate  # noqa: E402

REPO = validate.REPO
URL_PATTERN = "https://github.com/626Labs-LLC/sanduhr-widgets/releases/download/{tag}/{id}-{version}.zip"
FIXED_DATE = (1980, 1, 1, 0, 0, 0)


def zip_pack(pack_dir, dest):
    """Write a reproducible zip of every file in `pack_dir` (at the zip root) to `dest`."""
    pack_dir = Path(pack_dir)
    rels = sorted(p.relative_to(pack_dir).as_posix() for p in pack_dir.rglob("*") if p.is_file())
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_STORED) as zf:
        for rel in rels:
            info = zipfile.ZipInfo(rel, date_time=FIXED_DATE)
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            zf.writestr(info, (pack_dir / rel).read_bytes())


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def default_generated_at():
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch and epoch.isdigit():
        now = datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc)
    else:
        now = datetime.datetime.now(datetime.timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def build(packs_dir, out_dir, tag, generated_at=None):
    """Validate, zip and describe every pack. Returns the catalog dict; raises SystemExit on failure."""
    packs_dir, out_dir = Path(packs_dir), Path(out_dir)
    reports = validate.validate_paths([str(packs_dir)])
    failed = False
    for rep in reports:
        for line in rep.lines():
            print(line, file=sys.stderr)
        if rep.errors or rep.warnings:
            failed = True
    if failed or not reports:
        raise SystemExit("build_catalog: validation failed, no catalog written")

    out_dir.mkdir(parents=True, exist_ok=True)
    entries = []
    for pack_dir in validate.find_packs([str(packs_dir)]):
        manifest = json.loads((pack_dir / "pack.json").read_text(encoding="utf-8"))
        name = "%s-%s.zip" % (manifest["id"], manifest["version"])
        dest = out_dir / name
        zip_pack(pack_dir, dest)
        entries.append({
            "id": manifest["id"],
            "name": manifest["name"],
            "kind": manifest["kind"],
            "version": manifest["version"],
            "sanduhr_min": manifest["sanduhr_min"],
            "url": URL_PATTERN.format(tag=tag, id=manifest["id"], version=manifest["version"]),
            "sha256": sha256_of(dest),
            "size": dest.stat().st_size,
        })
    entries.sort(key=lambda e: e["id"])
    catalog = {
        "schema_version": 1,
        "generated_at": generated_at or default_generated_at(),
        "packs": entries,
    }
    data = (json.dumps(catalog, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    (out_dir / "catalog.json").write_bytes(data)  # binary write: LF on every platform
    return catalog


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build release zips and catalog.json.")
    ap.add_argument("--packs", default=str(REPO / "packs"), help="folder of packs (default: packs/)")
    ap.add_argument("--out", default=str(REPO / "dist"), help="output folder (default: dist/)")
    ap.add_argument("--tag", default=os.environ.get("GITHUB_REF_NAME", "dev"),
                    help="release tag the URLs point at (default: $GITHUB_REF_NAME or 'dev')")
    ap.add_argument("--generated-at", default=None, help="ISO-8601 UTC timestamp (default: now)")
    args = ap.parse_args(argv)
    catalog = build(args.packs, args.out, args.tag, args.generated_at)
    for e in catalog["packs"]:
        print("%s  %8d  %s-%s.zip" % (e["sha256"], e["size"], e["id"], e["version"]))
    print("wrote %s (%d packs, generated_at %s, tag %s)"
          % (Path(args.out) / "catalog.json", len(catalog["packs"]), catalog["generated_at"], args.tag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
