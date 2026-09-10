"""Run only inside Blender. Consumes geometry JSON; never evaluates user code."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector


def linear_color(hex_color):
    components = [int(hex_color[k:k + 2], 16) / 255 for k in (1, 3, 5)]
    return [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in components]


def main():
    arguments = sys.argv[sys.argv.index("--") + 1:]
    scene_path, output_dir = map(Path, arguments[:2])
    spec = json.loads(scene_path.read_text(encoding="utf-8"))
    if spec.get("schema") != "mof-blender/scene/1":
        raise ValueError("Unknown scene schema")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.name = "MOF Blender"
    materials, collections, meshes = {}, {}, {}
    bounds = []
    animated = []

    def material(color, opacity=1.0):
        key = (color, opacity)
        if key not in materials:
            mat = bpy.data.materials.new(f"MB/{color}/{opacity}")
            mat.use_nodes = True
            shader = mat.node_tree.nodes.get("Principled BSDF")
            rgba = (*linear_color(color), opacity)
            shader.inputs["Base Color"].default_value = rgba
            shader.inputs["Roughness"].default_value = spec["style"]["roughness"]
            shader.inputs["Metallic"].default_value = spec["style"]["metallic"]
            shader.inputs["Alpha"].default_value = opacity
            shader.inputs["Specular IOR Level"].default_value = 0.32
            mat.diffuse_color = rgba
            materials[key] = mat
        return materials[key]

    def collection(name):
        if name not in collections:
            group = bpy.data.collections.new(name)
            scene.collection.children.link(group)
            collections[name] = group
        return collections[name]

    def prototype(kind, color, opacity=1):
        key = (kind, color, opacity)
        if key not in meshes:
            if kind == "sphere":
                bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1)
            elif kind == "cone":
                bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=1, radius2=0, depth=1)
            else:
                bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=1, depth=1)
            temporary = bpy.context.object
            mesh = temporary.data
            mesh.name = f"MB/{kind}/{color}"
            for face in mesh.polygons:
                face.use_smooth = kind == "sphere" or len(face.vertices) == 4
            mesh.materials.append(material(color, opacity))
            bpy.data.objects.remove(temporary, do_unlink=True)
            meshes[key] = mesh
        return meshes[key]

    def add_object(mesh, name, group):
        obj = bpy.data.objects.new(name, mesh)
        collection(group).objects.link(obj)
        return obj

    def add_rod(start, end, radius, color, group, name, kind="cylinder"):
        a, b = Vector(start), Vector(end)
        delta = b - a
        obj = add_object(prototype(kind, color), name, group)
        obj.location = (a + b) * 0.5
        obj.scale = (radius, radius, delta.length)
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
        return obj

    for index, item in enumerate(spec["objects"]):
        kind, color, group = item["type"], item["color"], item.get("group", "objects")
        if kind == "sphere":
            obj = add_object(prototype(kind, color), f"{group}/{index}", group)
            obj.location = item["position"]
            radius = item["radius"]
            obj.scale = (radius,) * 3
            for signs in ((x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)):
                bounds.append(Vector(item["position"]) + Vector(signs) * radius)
        elif kind == "cylinder":
            obj = add_rod(item["start"], item["end"], item["radius"], color, group, f"{group}/{index}")
            bounds.extend([Vector(item["start"]), Vector(item["end"])])
            if item.get("arrow"):
                a, b = Vector(item["start"]), Vector(item["end"])
                length = min((b - a).length * 0.3, item["radius"] * 6)
                add_rod(b - (b - a).normalized() * length, b, item["radius"] * 3,
                        color, group, f"{group}/{index}/tip", "cone")
        elif kind == "mesh":
            mesh = bpy.data.meshes.new(f"{group}/{index}")
            mesh.from_pydata(item["vertices"], [], item["faces"])
            mesh.update()
            mesh.materials.append(material(color, item.get("opacity", 1.0)))
            obj = add_object(mesh, f"{group}/{index}", group)
            bounds.extend(Vector(p) for p in item["vertices"])
        else:
            raise ValueError(f"Unsupported object type: {kind}")
        for field in ("atom_id", "unit_id", "degree", "geometry", "element", "image"):
            if field in item:
                obj[field] = item[field]
        if item.get("keyframes"):
            animated.append((obj, item))
            for key in item["keyframes"]:
                for field in ("position", "start", "end"):
                    if field in key:
                        bounds.append(Vector(key[field]))
    if not bounds:
        raise ValueError("Cannot render an empty scene")
    minimum = Vector(tuple(min(p[k] for p in bounds) for k in range(3)))
    maximum = Vector(tuple(max(p[k] for p in bounds) for k in range(3)))
    center = (minimum + maximum) * 0.5
    span = max((maximum - minimum).length, 1.0)
    direction = Vector(spec["camera"]["direction"]).normalized()
    up = Vector(spec["camera"]["up"]).normalized()
    if abs(up.dot(direction)) > 0.98:
        up = Vector((0, 1, 0)) if abs(direction.y) < 0.98 else Vector((1, 0, 0))
    right = up.cross(direction).normalized()
    up = direction.cross(right).normalized()
    roll = math.radians(spec["camera"].get("roll_degrees", 0))
    right, up = right * math.cos(roll) + up * math.sin(roll), up * math.cos(roll) - right * math.sin(roll)
    camera_data = bpy.data.cameras.new("Scientific camera")
    camera = add_object(camera_data, "Scientific camera", "studio")
    camera.rotation_euler = Matrix((right, up, direction)).transposed().to_euler()
    camera_data.sensor_fit = "HORIZONTAL"
    camera_data.lens = 55
    width, height = spec["render"]["width"], spec["render"]["height"]
    aspect = width / height
    projected_x = [(p - center).dot(right) for p in bounds]
    projected_y = [(p - center).dot(up) for p in bounds]
    center += right * (max(projected_x) + min(projected_x)) / 2
    center += up * (max(projected_y) + min(projected_y)) / 2
    zoom = spec["camera"].get("zoom", 1)
    if spec["camera"]["projection"] == "orthographic":
        camera_data.type = "ORTHO"
        camera_data.ortho_scale = max(max(projected_x) - min(projected_x),
                                      (max(projected_y) - min(projected_y)) * aspect) * 1.16 / zoom
        distance = span * 2
    else:
        camera_data.type = "PERSP"
        tan_x = camera_data.sensor_width / (2 * camera_data.lens)
        tan_y = tan_x / aspect
        distance = max((p - center).dot(direction) + 1.16 * max(
            abs((p - center).dot(right)) / tan_x,
            abs((p - center).dot(up)) / tan_y) for p in bounds) / zoom
    camera.location = center + direction * distance
    camera_data.clip_start = max(span * 1e-5, 0.001)
    camera_data.clip_end = span * 20
    scene.camera = camera

    world = bpy.data.worlds.new("Soft studio environment")
    world.use_nodes = True
    scene.world = world
    nodes, links = world.node_tree.nodes, world.node_tree.links
    nodes.clear()
    path = nodes.new("ShaderNodeLightPath")
    illumination = nodes.new("ShaderNodeBackground")
    illumination.inputs["Color"].default_value = (1, 1, 1, 1)
    illumination.inputs["Strength"].default_value = spec["style"]["world_strength"]
    background = nodes.new("ShaderNodeBackground")
    background.inputs["Color"].default_value = (*linear_color(spec["style"]["background"]), 1)
    background.inputs["Strength"].default_value = 1
    mix = nodes.new("ShaderNodeMixShader")
    links.new(path.outputs["Is Camera Ray"], mix.inputs[0])
    links.new(illumination.outputs[0], mix.inputs[1])
    links.new(background.outputs[0], mix.inputs[2])
    out = nodes.new("ShaderNodeOutputWorld")
    links.new(mix.outputs[0], out.inputs["Surface"])

    for name, offset, energy, size in [
        ("Large softbox", right * -0.7 + up * 1.0 + direction * 1.1, 8, 1.25),
        ("Fill", right * 1.0 + up * 0.25 + direction * 0.7, 4, 1.4),
        ("Rim", right * 0.4 + up * 0.9 - direction * 0.8, 10, 0.95),
    ]:
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy * span ** 2
        light_data.shape = "DISK"
        light_data.size = span * size
        light = add_object(light_data, name, "studio")
        light.location = center + offset * span
        light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()

    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = spec["render"]["samples"]
    scene.cycles.use_denoising = True
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.seed = 20260910
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = spec["render"]["transparent"]
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = spec["style"]["exposure"]
    scene.view_settings.gamma = 1
    scene.render.filepath = str(output_dir / "render.png")
    scene["mof_blender_provenance"] = json.dumps(spec["provenance"], ensure_ascii=False)
    scene["geometry_sha256"] = spec.get("geometry_sha256", "")
    text = bpy.data.texts.new("mof_blender_scene.json")
    text.write(json.dumps(spec, ensure_ascii=False, indent=2))
    for obj, item in animated:
        for key in item["keyframes"]:
            frame = key["frame"]
            if item["type"] == "sphere":
                obj.location = key["position"]
                obj.keyframe_insert(data_path="location", frame=frame)
            elif item["type"] == "cylinder":
                a, b = Vector(key["start"]), Vector(key["end"])
                obj.location = (a + b) * 0.5
                obj.rotation_quaternion = (b - a).to_track_quat("Z", "Y")
                obj.scale = (item["radius"], item["radius"], (b - a).length)
                for property_name in ("location", "rotation_quaternion", "scale"):
                    obj.keyframe_insert(data_path=property_name, frame=frame)
            if "visible" in key:
                obj.hide_render = not key["visible"]
                obj.hide_viewport = not key["visible"]
                obj.keyframe_insert(data_path="hide_render", frame=frame)
                obj.keyframe_insert(data_path="hide_viewport", frame=frame)
        # Blender 4.4+ actions can be layered. Iterate channels through slot bags.
        action = obj.animation_data.action
        curves = list(getattr(action, "fcurves", []))
        for layer in getattr(action, "layers", []):
            for strip in layer.strips:
                for bag in getattr(strip, "channelbags", []):
                    curves.extend(bag.fcurves)
        for curve in curves:
            interpolation = "CONSTANT" if curve.data_path.startswith("hide_") else "LINEAR"
            for point in curve.keyframe_points:
                point.interpolation = interpolation
    if spec.get("animation"):
        scene.frame_start = 1
        scene.frame_end = spec["animation"]["frames"]
        scene.render.fps = spec["animation"]["fps"]
        scene.frame_set(1)
    # Make the saved file immediately useful when opened in Blender.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_perspective = "CAMERA"
                area.spaces.active.overlay.show_overlays = False
                area.spaces.active.shading.type = "MATERIAL"
    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / "scene.blend"))
    bpy.ops.render.render(write_still=True)
    if spec.get("animation") and len(arguments) > 2 and arguments[2] == "animate":
        frames_dir = output_dir / "frames"
        frames_dir.mkdir()
        scene.render.filepath = str(frames_dir / "frame_")
        bpy.ops.render.render(animation=True)
    audit = {"blender_version": bpy.app.version_string, "objects": len(spec["objects"]),
             "resolution": [width, height], "transparent": scene.render.film_transparent,
             "engine": scene.render.engine, "samples": scene.cycles.samples,
             "camera_position": list(camera.location), "camera_direction": list(direction),
             "geometry_sha256": spec.get("geometry_sha256", "")}
    (output_dir / "blender_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
