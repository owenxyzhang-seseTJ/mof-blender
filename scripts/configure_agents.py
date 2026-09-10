"""Generate portable host snippets using this checkout's absolute runtime paths."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--python", type=Path, default=Path(sys.executable))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    executable = str(args.python.absolute())
    launcher = str(root / "scripts" / "run.py")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    server = {"command": executable, "args": [launcher, "mcp"]}
    files = {
        "mcp.json": json.dumps({"mcpServers": {"mof-blender": server}}, indent=2) + "\n",
        "vscode-mcp.json": json.dumps({"servers": {"mof-blender": {"type": "stdio", **server}}}, indent=2) + "\n",
        "codex.toml": "[mcp_servers.mof-blender]\ncommand = " + json.dumps(executable)
                      + "\nargs = " + json.dumps([launcher, "mcp"])
                      + "\nstartup_timeout_sec = 60\ntool_timeout_sec = 1800\n",
    }
    if os.name != "nt":
        command = shlex.join([executable, launcher, "mcp"])
        files["register-commands.txt"] = (
            f"codex mcp add mof-blender -- {command}\n"
            f"claude mcp add --scope user --transport stdio mof-blender -- {command}\n")
    for name, content in files.items():
        path = output / name
        with path.open("x", encoding="utf-8") as handle:
            handle.write(content)
    print(json.dumps({"generated": [str(output / name) for name in files]}, indent=2))


if __name__ == "__main__":
    main()
