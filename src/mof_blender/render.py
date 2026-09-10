"""Run a separate Blender process and return verified artifacts."""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from .io import InputError, check_kind, digest, read_json, write_json


def find_blender(explicit=None):
    choices = [explicit, os.environ.get("BLENDER_PATH"), shutil.which("blender"),
               "/Applications/Blender.app/Contents/MacOS/Blender"]
    if os.name == "nt":
        choices += [str(p) for p in Path("C:/Program Files/Blender Foundation").glob("Blender*/blender.exe")]
    for path in choices:
        if path and Path(path).is_file():
            return str(Path(path).resolve())
    raise InputError("Blender was not found. Set BLENDER_PATH to its executable.")


def doctor():
    packages = {}
    for name in ["numpy", "scipy", "ase", "gemmi", "autografs", "mcp", "rdkit"]:
        try:
            packages[name] = version(name) if importlib.util.find_spec(name) else None
        except PackageNotFoundError:
            packages[name] = None
    try:
        path = find_blender()
        result = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=20, check=False)
        blender = {"path": path, "version": next((x for x in result.stdout.splitlines()
                                                  if x.startswith("Blender ")), "unknown")}
    except (InputError, OSError, subprocess.TimeoutExpired) as exc:
        blender = {"error": str(exc)}
    return {"packages": packages, "blender": blender,
            "ready": all(packages[x] for x in ["numpy", "scipy", "ase", "gemmi", "autografs", "mcp", "rdkit"])
                     and "path" in blender}


def render_scene(scene, output_dir, blender=None, samples=None, timeout=600, animate=False):
    data = read_json(scene)
    check_kind(data, "scene")
    if not data["objects"]:
        raise InputError("Scene is empty")
    if samples is not None:
        if isinstance(samples, bool) or not 8 <= samples <= 4096:
            raise InputError("samples must be between 8 and 4096")
        data["render"]["samples"] = int(samples)
    executable = find_blender(blender)
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=False)
    recipe = write_json(output / "scene.json", data)
    worker = Path(__file__).with_name("blender_worker.py")
    command = [executable, "--background", "--factory-startup", "--disable-autoexec",
               "--threads", "4", "--python-exit-code", "1", "--python", str(worker),
               "--", recipe, str(output)]
    if animate:
        if not data.get("animation"):
            raise InputError("Scene contains no animation")
        command.append("animate")
    start = time.monotonic()
    with (output / "blender.log").open("w", encoding="utf-8") as log:
        try:
            process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise InputError(f"Render timed out after {timeout}s. Log: {output / 'blender.log'}") from exc
    if process.returncode != 0:
        tail = (output / "blender.log").read_text(errors="replace")[-2500:]
        raise InputError(f"Blender exited {process.returncode}. Log: {output / 'blender.log'}\n{tail}")
    files = [output / name for name in ("render.png", "scene.blend", "blender_audit.json")]
    if any(not p.is_file() or p.stat().st_size == 0 for p in files):
        raise InputError(f"Blender did not produce every expected artifact: {output}")
    preview = None
    if animate:
        from PIL import Image
        frames = sorted((output / "frames").glob("frame_*.png"))
        if len(frames) != data["animation"]["frames"]:
            raise InputError("Animation frame count does not match its recipe")
        frames_rgb = []
        for path in frames:
            with Image.open(path) as im:
                rgb = Image.new("RGB", im.size, data["style"]["background"])
                rgb.paste(im, mask=im.getchannel("A"))
                frames_rgb.append(rgb)
        preview = output / "animation.gif"
        fps = data["animation"]["fps"]
        durations = [10 * (round((i + 1) * 100 / fps) - round(i * 100 / fps))
                     for i in range(len(frames_rgb))]
        frames_rgb[0].save(preview, save_all=True, append_images=frames_rgb[1:],
                           duration=durations, loop=0, disposal=2)
        files.append(preview)
    manifest = {"status": "complete", "elapsed_seconds": round(time.monotonic() - start, 2),
                "source_scene_sha256": digest(data), "geometry_sha256": digest(data["objects"]),
                "artifacts": [{"path": str(p), "bytes": p.stat().st_size,
                               "sha256": digest(p.read_bytes())} for p in files],
                "audit": read_json(output / "blender_audit.json")}
    write_json(output / "manifest.json", manifest)
    return {"image": str(files[0]), "blend": str(files[1]), "animation": str(preview) if preview else None,
            "manifest": str(output / "manifest.json"),
            "elapsed_seconds": manifest["elapsed_seconds"]}
