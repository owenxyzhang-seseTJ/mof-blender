"""Camera-only changes with explicit direct/reciprocal lattice conventions."""
from __future__ import annotations

import copy
import math
import re

import numpy as np

from .io import InputError, check_kind, digest, read_json, write_json


def unit(vector):
    vector = np.asarray(vector, dtype=float)
    if vector.shape != (3,) or not np.isfinite(vector).all() or np.linalg.norm(vector) < 1e-10:
        raise InputError("Direction must be a finite nonzero 3-vector")
    return vector / np.linalg.norm(vector)


def lattice_direction(cell, indices, kind="uvw"):
    cell = np.asarray(cell, dtype=float)
    if kind == "uvw":
        vector = np.asarray(indices, dtype=float) @ cell
    elif kind == "hkl":
        vector = np.linalg.solve(cell, np.asarray(indices, dtype=float))
    elif kind == "cartesian":
        vector = indices
    else:
        raise InputError("Direction kind must be uvw, hkl or cartesian")
    return unit(vector).tolist()


def camera_default():
    return {"direction": unit([1.4, -1.8, 1.25]).tolist(), "up": [0, 0, 1],
            "projection": "orthographic", "zoom": 1.0, "roll_degrees": 0.0,
            "convention": "direction points from target toward camera"}


def _triple(text):
    fields = text.replace(",", " ").replace("，", " ").split()
    if len(fields) == 1 and re.fullmatch(r"[0-9]{3}", fields[0]):
        fields = list(fields[0])
    if len(fields) != 3:
        raise InputError("Use three separate signed indices, e.g. [1 0 -1]")
    return [float(x) for x in fields]


def interpret_view(instruction, cell, previous=None):
    camera = copy.deepcopy(previous or camera_default())
    text = instruction.strip().lower().replace("−", "-")
    matched = False
    direct = re.search(r"\[([^\]]+)\]", text)
    reciprocal = re.search(r"\(([^)]+)\)", text)
    axis = re.search(r"(?:沿|along\s+)([abcxyz])\s*(?:轴|axis)?", text)
    if direct:
        camera["direction"] = lattice_direction(cell, _triple(direct[1]), "uvw")
        matched = True
    elif reciprocal:
        camera["direction"] = lattice_direction(cell, _triple(reciprocal[1]), "hkl")
        matched = True
    elif axis:
        index = "abcxyz".index(axis[1]) % 3
        kind = "uvw" if axis[1] in "abc" else "cartesian"
        camera["direction"] = lattice_direction(cell, np.eye(3)[index], kind)
        matched = True
    else:
        presets = [(r"俯视|top", [0, 0, 1]), (r"仰视|bottom", [0, 0, -1]),
                   (r"正视|正面|front", [0, -1, 0]), (r"侧视|侧面|side", [1, 0, 0]),
                   (r"等轴|isometric", [1, -1, 1])]
        for pattern, direction in presets:
            if re.search(pattern, text):
                camera["direction"] = unit(direction).tolist()
                matched = True
                break
    if re.search(r"反方向|反向|opposite|reverse", text):
        camera["direction"] = (-unit(camera["direction"])).tolist()
        matched = True
    orbit = re.search(r"绕\s*([abcxyz])\s*轴?\s*(?:旋转|转动|转)\s*(-?\d+(?:\.\d+)?)", text)
    horizontal = re.search(r"(?:向|往)(左|右)(?:旋转|转动|转)\s*(\d+(?:\.\d+)?)", text)
    if orbit or horizontal:
        if orbit:
            idx = "abcxyz".index(orbit[1]) % 3
            axis_v = np.asarray(cell)[idx] if orbit[1] in "abc" else np.eye(3)[idx]
            angle = float(orbit[2])
        else:
            axis_v = camera["up"]
            angle = float(horizontal[2]) * (1 if horizontal[1] == "左" else -1)
        axis_v = unit(axis_v)
        theta = math.radians(angle)
        v = unit(camera["direction"])
        camera["direction"] = (v * math.cos(theta) + np.cross(axis_v, v) * math.sin(theta)
                               + axis_v * np.dot(axis_v, v) * (1 - math.cos(theta))).tolist()
        matched = True
    if re.search(r"正交|orthographic", text):
        camera["projection"] = "orthographic"
        matched = True
    elif re.search(r"透视|perspective", text):
        camera["projection"] = "perspective"
        matched = True
    zoom = re.search(r"(?:放大|zoom\s*)\s*(\d+(?:\.\d+)?)\s*(倍|%|x)?", text)
    if zoom:
        factor = float(zoom[1])
        if zoom[2] == "%":
            factor = 1 + factor / 100
        if not 0.1 <= factor <= 10:
            raise InputError("Zoom factor must be 0.1–10")
        camera["zoom"] *= factor
        matched = True
    if not matched:
        raise InputError("Unrecognized view instruction. Use 沿a轴看, 沿[1 1 0]看, "
                         "看(1 0 0)晶面, 俯视, 向右旋转30度, 绕c轴旋转30度, 正交 or 透视; "
                         "an agent can also supply an explicit direction vector.")
    return camera


def change_view(scene, output, instruction=None, direction=None, kind="uvw", projection=None):
    data = read_json(scene)
    check_kind(data, "scene")
    before = digest(data["objects"])
    if instruction:
        data["camera"] = interpret_view(instruction, data["cell"], data["camera"])
    if direction is not None:
        data["camera"]["direction"] = lattice_direction(data["cell"], direction, kind)
    if projection:
        if projection not in ("orthographic", "perspective"):
            raise InputError("Unknown projection")
        data["camera"]["projection"] = projection
    if not instruction and direction is None and projection is None:
        raise InputError("Supply a view instruction, direction, or projection")
    data.setdefault("history", []).append({"operation": "camera", "instruction": instruction,
                                           "geometry_sha256": before})
    assert digest(data["objects"]) == before
    return {"scene": write_json(output, data), "camera": data["camera"],
            "geometry_unchanged": True, "geometry_sha256": before}
