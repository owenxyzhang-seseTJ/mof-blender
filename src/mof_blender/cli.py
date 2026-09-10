"""JSON CLI; the same operations also have typed MCP tools."""
from __future__ import annotations

import argparse
import contextlib
import json
import sys

from .io import InputError, read_json


def main():
    parser = argparse.ArgumentParser(prog="mof-blender")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor", help="Check dependencies and Blender")
    sub.add_parser("mcp", help="Start the stdio MCP server")
    sub.add_parser("tools", help="List named JSON operations")
    call = sub.add_parser("call", help="Call an operation with JSON arguments")
    call.add_argument("operation")
    inputs = call.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--json", help="JSON object (quote appropriately for your shell)")
    inputs.add_argument("--args-file", help="JSON argument file; safest for long requests")
    args = parser.parse_args()
    if args.command == "mcp":
        from .server import main as serve
        serve()
        return
    from .animation import diffusion_scene, gate_open_scene, reaction_scene
    from .layers import layer_scene
    from .render import doctor, render_scene
    from .scene import compose_scene, make_scene, molecule_scene
    from .topology import analyze_cif
    from .views import change_view
    operations = {"analyze": analyze_cif, "scene": make_scene, "molecule": molecule_scene,
                  "view": change_view, "render": render_scene, "compose": compose_scene,
                  "diffusion": diffusion_scene, "reaction": reaction_scene, "layer": layer_scene,
                  "gate-open": gate_open_scene}
    aliases = {"analyze_framework": "analyze", "create_framework_scene": "scene",
               "create_molecule_scene": "molecule", "set_view": "view",
               "compose_schematic": "compose", "create_diffusion_animation": "diffusion",
               "create_reaction_animation": "reaction", "create_layer_scene": "layer",
               "create_gate_open_animation": "gate-open", "render_figure": "render"}
    try:
        with contextlib.redirect_stdout(sys.stderr):
            if args.command == "doctor":
                result = doctor()
            elif args.command == "tools":
                import inspect
                result = {name: str(inspect.signature(fn)) for name, fn in operations.items()}
            else:
                args.operation = aliases.get(args.operation, args.operation)
                if args.operation not in operations:
                    raise InputError(f"Unknown operation {args.operation}; choose {list(operations)}")
                parameters = read_json(args.args_file) if args.args_file else json.loads(args.json)
                if not isinstance(parameters, dict):
                    raise InputError("Arguments must be a JSON object")
                result = operations[args.operation](**parameters)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except Exception as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
