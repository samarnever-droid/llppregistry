#!/usr/bin/env python3
"""Generate registry/index.json from sparse index entries.

This standalone version is for the samarnever-droid/llppregistry repo. It keeps
an existing aggregate index when the sparse index is still empty, so the public
catalog can be bootstrapped before the first content-addressed package publish.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPARSE_INDEX = ROOT / "index"
AGGREGATE_INDEX = ROOT / "registry" / "index.json"
REGISTRY_URL = "https://registry.lplusplus.bond"


def load_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text())


def sparse_entries() -> dict[str, Any]:
    packages: dict[str, Any] = {}
    if not SPARSE_INDEX.exists():
        return packages
    for path in sorted(p for p in SPARSE_INDEX.rglob("*") if p.is_file() and p.name != ".gitkeep"):
        entry = load_json(path)
        name = entry.get("name")
        versions = entry.get("versions", [])
        if not isinstance(name, str) or not isinstance(versions, list):
            raise SystemExit(f"{path}: expected IndexEntry {{name, versions}}")
        latest = versions[-1] if versions else {}
        packages[name] = {
            "name": name,
            "version": latest.get("version", "0.0.0"),
            "versions": {
                version.get("version", "0.0.0"): {
                    **version,
                    "download_url": f"{REGISTRY_URL}/blob/{version.get('checksum', version.get('sha256', ''))}",
                }
                for version in versions
            },
        }
    return packages


def normalize_packages(raw: Any) -> dict[str, Any]:
    if isinstance(raw, list):
        return {pkg["name"]: pkg for pkg in raw if isinstance(pkg, dict) and pkg.get("name")}
    if isinstance(raw, dict):
        return raw
    return {}


def main() -> int:
    packages = sparse_entries()
    if not packages and AGGREGATE_INDEX.exists():
        packages = normalize_packages(load_json(AGGREGATE_INDEX).get("packages", {}))

    manifest = {
        "registry": {
            "name": "L++ Official Package Registry",
            "version": "3.0.0",
            "url": REGISTRY_URL,
            "source_of_truth": "git",
            "repository": "samarnever-droid/llppregistry",
            "description": "Official L++ package registry — git-backed, static-mirrored, SHA-256 verified",
            "package_count": len(packages),
        },
        "packages": {name: packages[name] for name in sorted(packages)},
    }
    AGGREGATE_INDEX.parent.mkdir(parents=True, exist_ok=True)
    AGGREGATE_INDEX.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    print(f"generated {AGGREGATE_INDEX.relative_to(ROOT)} ({len(packages)} packages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
