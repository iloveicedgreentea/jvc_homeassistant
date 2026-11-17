#!/usr/bin/env python3
"""Copy reviewed library sources into the integration's private namespace."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from pathlib import Path

PACKAGE_FILES = (
    "__init__.py",
    "command.py",
    "connection.py",
    "const.py",
    "device.py",
    "error.py",
    "projector.py",
    "py.typed",
)
VENDOR_INIT = (
    b'"""Private integration dependencies; never expose top-level package aliases."""\n'
)


def library_version(source: bytes) -> str:
    """Read the literal version without importing or executing upstream code."""
    for statement in ast.parse(source).body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__version__"
            for target in statement.targets
        ):
            value = ast.literal_eval(statement.value)
            if isinstance(value, str):
                return value
    raise ValueError("The library does not declare a literal __version__")


def expected_files(library: Path) -> dict[str, bytes]:
    """Build the deterministic, dependency-free vendoring payload."""
    source = library / "jvcprojector"
    names = {path.name for path in source.glob("*.py")}
    if names != set(PACKAGE_FILES) - {"py.typed"}:
        raise ValueError(
            "Library modules changed; review and update PACKAGE_FILES first"
        )
    contents = {name: (source / name).read_bytes() for name in PACKAGE_FILES}
    contents["LICENSE"] = (library / "LICENSE").read_bytes()
    source_hash = hashlib.sha256()
    for name, data in sorted(contents.items()):
        source_hash.update(name.encode() + b"\0" + data + b"\0")
    commit = subprocess.check_output(
        ["git", "-C", str(library), "rev-parse", "HEAD"], text=True
    ).strip()
    modified = bool(
        subprocess.check_output(
            [
                "git",
                "-C",
                str(library),
                "status",
                "--porcelain",
                "--",
                "jvcprojector",
                "LICENSE",
            ],
            text=True,
        ).strip()
    )
    metadata = {
        "source_repository": "https://github.com/iloveicedgreentea/pyjvcprojector",
        "source_commit": commit,
        "source_modified": modified,
        "library_version": library_version(contents["__init__.py"]),
        "source_sha256": source_hash.hexdigest(),
        "files_sha256": {
            name: hashlib.sha256(data).hexdigest()
            for name, data in sorted(contents.items())
        },
    }
    contents["vendor_info.json"] = (
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    ).encode()
    return {
        "__init__.py": VENDOR_INIT,
        **{f"jvcprojector/{name}": data for name, data in contents.items()},
    }


def main() -> int:
    """Sync the private copy, or verify that it matches the reviewed source."""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, default=root.parent / "pyjvcprojector")
    parser.add_argument(
        "--check", action="store_true", help="Check without writing files"
    )
    args = parser.parse_args()
    library = args.library.expanduser().resolve()
    try:
        expected = expected_files(library)
    except (OSError, ValueError, subprocess.CalledProcessError) as err:
        parser.error(str(err))
    destination = root / "custom_components" / "jvc_projector" / "_vendor"
    existing = {
        path.relative_to(destination).as_posix()
        for path in destination.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    }
    stale = existing - expected.keys()
    if stale:
        parser.error(
            "Unexpected vendor files require review: " + ", ".join(sorted(stale))
        )
    mismatches = [
        name
        for name, data in expected.items()
        if not (destination / name).is_file()
        or (destination / name).read_bytes() != data
    ]
    if args.check:
        if mismatches:
            print("Vendored library differs: " + ", ".join(mismatches))
            return 1
        print("Vendored library matches the source and provenance metadata")
        return 0
    for name, data in expected.items():
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print(
        f"Synced {len(PACKAGE_FILES)} library files, MIT license, and provenance metadata"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
