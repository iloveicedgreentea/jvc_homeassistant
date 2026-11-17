"""The installed integration must use only its private, bundled library."""

from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "jvc_projector"


@pytest.mark.parametrize("external_available", [True, False])
def test_private_library_isolated_from_external_package(tmp_path, external_available):
    """An incompatible or missing external installation cannot affect imports."""
    external = tmp_path / "jvcprojector"
    external.mkdir()
    (external / "__init__.py").write_text(
        'raise RuntimeError("The external library must not be imported")\n'
    )
    script = """
import importlib
import importlib.abc
import sys
sys.path.insert(0, ROOT)
sys.path.insert(0, SHADOW)
if not EXTERNAL_AVAILABLE:
    class NoExternalLibrary(importlib.abc.MetaPathFinder):
        def find_spec(self, fullname, path=None, target=None):
            if fullname == "jvcprojector" or fullname.startswith("jvcprojector."):
                raise ModuleNotFoundError("No external projector library", name=fullname)
    sys.meta_path.insert(0, NoExternalLibrary())
component = importlib.import_module("custom_components.jvc_projector")
private = importlib.import_module("custom_components.jvc_projector._vendor.jvcprojector.projector")
for platform in ("config_flow", "coordinator", "entity", "binary_sensor", "remote", "select", "sensor"):
    importlib.import_module("custom_components.jvc_projector." + platform)
assert component.JvcProjector is private.JvcProjector
assert private.JvcProjector.__module__.startswith("custom_components.jvc_projector._vendor.")
assert not any(name == "jvcprojector" or name.startswith("jvcprojector.") for name in sys.modules)
"""
    setup = f"ROOT={str(ROOT)!r}\nSHADOW={str(tmp_path)!r}\nEXTERNAL_AVAILABLE={external_available!r}\n"
    result = subprocess.run(
        [sys.executable, "-I", "-c", setup + script],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_manifest_requires_no_pip_install():
    """Copying the component supplies all runtime library code and metadata."""
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    assert manifest["requirements"] == []
    assert manifest["loggers"] == [
        "custom_components.jvc_projector._vendor.jvcprojector"
    ]
    private = COMPONENT / "_vendor" / "jvcprojector"
    assert (private / "py.typed").is_file()
    assert (private / "LICENSE").read_text().startswith("MIT License\n")
    info = json.loads((private / "vendor_info.json").read_text())
    assert len(info["source_commit"]) == 40
    assert len(info["source_sha256"]) == 64
    for name, checksum in info["files_sha256"].items():
        assert hashlib.sha256((private / name).read_bytes()).hexdigest() == checksum


def test_no_component_imports_the_global_library_namespace():
    """Keep explicit private imports as the integration evolves."""
    for path in COMPONENT.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Import):
                assert all(
                    not alias.name.startswith("jvcprojector") for alias in node.names
                ), path
            elif isinstance(node, ast.ImportFrom) and not node.level:
                assert not (node.module or "").startswith("jvcprojector"), path
