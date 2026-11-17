"""Stage the component with its bundled library, without pip or publishing."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


def digest(path: Path) -> str:
    """Return a file's SHA256 digest."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    """Build a fresh, self-contained test bundle."""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", type=Path, default=root.parent / "pyjvcprojector")
    parser.add_argument(
        "--output", type=Path, default=root / "dist" / "jvc-bundled-test"
    )
    args = parser.parse_args()
    library = args.library.resolve()
    output = args.output.resolve()
    component = root / "custom_components" / "jvc_projector"
    if output.exists() or output.with_suffix(output.suffix + ".zip").exists():
        parser.error(f"Output already exists; choose a fresh path: {output}")
    for source in (component, root / "examples", library):
        if output == source or output.is_relative_to(source):
            parser.error(f"Output must be outside the source tree: {source}")
    manifest = json.loads((component / "manifest.json").read_text())
    if manifest.get("requirements"):
        parser.error("Expected a component without pip requirements")
    subprocess.run(
        [
            sys.executable,
            str(root / "tools" / "sync_library.py"),
            "--library",
            str(library),
            "--check",
        ],
        check=True,
    )
    shutil.copytree(
        component,
        output / "custom_components" / "jvc_projector",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copytree(root / "examples", output / "examples")
    for source, relative in (
        (root / "readme.md", "README.md"),
        (root / "docs" / "testing.md", "docs/testing.md"),
        (root / "docs" / "specs" / "README.md", "docs/specs/README.md"),
    ):
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    inventory = {
        "component_version": manifest["version"],
        "files": {
            str(path.relative_to(output)): digest(path)
            for path in sorted(output.rglob("*"))
            if path.is_file()
        },
    }
    (output / "bundle.json").write_text(json.dumps(inventory, indent=2) + "\n")
    archive = shutil.make_archive(str(output), "zip", root_dir=output)
    print(f"Test bundle: {output}\nZIP: {archive}\nNothing installed or published.")


if __name__ == "__main__":
    main()
