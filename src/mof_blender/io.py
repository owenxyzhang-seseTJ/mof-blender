"""JSON and source-file handling shared by CLI and MCP."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


class InputError(ValueError):
    """An actionable user-input or dependency error."""


def read_json(path):
    with Path(path).expanduser().open(encoding="utf-8") as handle:
        return json.load(handle)


def digest(data):
    if not isinstance(data, bytes):
        data = json.dumps(data, sort_keys=True, allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def source_info(path):
    path = Path(path).expanduser().resolve(strict=True)
    return {"path": str(path), "sha256": digest(path.read_bytes())}


def write_json(path, value):
    """Exclusive creation keeps inputs and earlier figure revisions intact."""
    path = Path(path).expanduser().resolve()
    payload = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(payload)
    return str(path)


def check_kind(data, kind):
    if data.get("schema") != f"mof-blender/{kind}/1":
        raise InputError(f"Expected mof-blender/{kind}/1 JSON")

