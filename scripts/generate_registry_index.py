#!/usr/bin/env python3
"""Generate registry/index.json from sparse index entries.

This standalone version is for the samarnever-droid/llppregistry repo. It merges
published sparse-index packages into the public aggregate catalog and verifies
that every sparse-index version has a matching SHA-256 content-addressed blob.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPARSE_INDEX = ROOT / "index"
BLOB_DIR = ROOT / "blob"
AGGREGATE_INDEX = ROOT / "registry" / "index.json"
REGISTRY_URL = "https://registry.lplusplus.bond"

PACKAGE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sparse_rel_path(name: str) -> pathlib.Path:
    if not PACKAGE_NAME_RE.match(name):
        raise SystemExit(f"invalid package name: {name!r}")
    if len(name) == 1:
        return pathlib.Path("1") / name
    if len(name) == 2:
        return pathlib.Path("2") / name
    if len(name) == 3:
        return pathlib.Path("3") / name[0] / name[1:]
    return pathlib.Path(name[0:2]) / name[2:4] / name


def verify_blob(checksum: str) -> None:
    if not isinstance(checksum, str) or not SHA256_RE.match(checksum):
        raise SystemExit(f"invalid SHA-256 checksum: {checksum!r}")
    blob_path = BLOB_DIR / checksum
    if blob_path.is_symlink():
        raise SystemExit(f"refusing symlink in blob store: {blob_path}")
    if not blob_path.is_file():
        raise SystemExit(f"missing blob for checksum {checksum}: {blob_path}")
    actual = hashlib.sha256(blob_path.read_bytes()).hexdigest()
    if actual != checksum:
        raise SystemExit(
            f"blob checksum mismatch for {blob_path}: expected {checksum}, got {actual}"
        )


def sparse_entries() -> dict[str, Any]:
    packages: dict[str, Any] = {}
    if not SPARSE_INDEX.exists():
        return packages
    for item in SPARSE_INDEX.rglob("*"):
        if item.name.startswith("."):
            continue
        if item.is_symlink():
            raise SystemExit(f"refusing symlink in sparse index: {item}")
    for path in sorted(
        p for p in SPARSE_INDEX.rglob("*") if p.is_file() and not p.name.startswith(".")
    ):
        entry = load_json(path)
        name = entry.get("name")
        versions = entry.get("versions", [])
        if not isinstance(name, str) or not isinstance(versions, list) or not versions:
            raise SystemExit(f"{path}: expected non-empty IndexEntry {{name, versions}}")
        expected_rel = sparse_rel_path(name)
        actual_rel = path.relative_to(SPARSE_INDEX)
        if actual_rel != expected_rel:
            raise SystemExit(
                f"{path}: index entry for {name!r} at unexpected path {actual_rel} (expected {expected_rel})"
            )
        seen_versions: set[str] = set()
        versions_map: dict[str, Any] = {}
        for version in versions:
            ver_str = version.get("version")
            checksum = version.get("checksum", version.get("sha256", ""))
            if not isinstance(ver_str, str) or not ver_str:
                raise SystemExit(f"{path}: version entry missing version string")
            if ver_str in seen_versions:
                raise SystemExit(f"{path}: duplicate version {ver_str!r} for {name!r}")
            seen_versions.add(ver_str)
            verify_blob(checksum)
            versions_map[ver_str] = {
                **version,
                "download_url": f"{REGISTRY_URL}/blob/{checksum}",
            }
        latest = versions[-1]
        packages[name] = {
            "name": name,
            "version": latest.get("version", "0.0.0"),
            "versions": versions_map,
        }
    return packages


def normalize_packages(raw: Any) -> dict[str, Any]:
    if isinstance(raw, list):
        return {pkg["name"]: pkg for pkg in raw if isinstance(pkg, dict) and pkg.get("name")}
    if isinstance(raw, dict):
        return dict(raw)
    return {}


def main() -> int:
    packages: dict[str, Any] = {}
    if AGGREGATE_INDEX.exists():
        packages = normalize_packages(load_json(AGGREGATE_INDEX).get("packages", {}))

    for name, sparse_pkg in sparse_entries().items():
        existing = packages.get(name)
        if isinstance(existing, dict):
            merged = dict(existing)
            merged.update(sparse_pkg)
            packages[name] = merged
        else:
            packages[name] = sparse_pkg

    manifest = {
        "registry": {
            "name": "L++ Official Package Registry",
            "version": "3.0.0",
            "url": REGISTRY_URL,
            "source_of_truth": "git",
            "repository": "samarnever-droid/llppregistry",
            "description": "Official L++ package registry \u2014 git-backed, static-mirrored, SHA-256 verified",
            "package_count": len(packages),
        },
        "packages": {name: packages[name] for name in sorted(packages)},
    }
    AGGREGATE_INDEX.parent.mkdir(parents=True, exist_ok=True)
    AGGREGATE_INDEX.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"generated {AGGREGATE_INDEX.relative_to(ROOT)} ({len(packages)} packages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
