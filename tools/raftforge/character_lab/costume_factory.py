"""RAFTFORGE A14: free Blender background costume shell generation.

Requires Blender's bundled bpy. Generates fitted costume *from the source skinned
surface* and preserves vertex groups/armature instead of constructing a new person.
Run: blender -b --python costume_factory.py -- --input base.glb --output sailor.glb
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", required=True)
    return parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])


def material(name, rgba, roughness=0.8, metallic=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgba, 1.0)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*rgba, 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return m


def select_one(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def shell(source, name, lo, hi, mat, thickness=0.007, offset=0.008):
    """Crop duplicated skinned mesh by WORLD height; retain source vertex groups.

    This is a quick art-direction proxy, not production clothing topology.
    """
    duplicate = source.copy()
    duplicate.data = source.data.copy()
    bpy.context.collection.objects.link(duplicate)
    duplicate.name = name
    # Remove other material slots, assign a single costume material.
    duplicate.data.materials.clear()
    duplicate.data.materials.append(mat)
    matrix = duplicate.matrix_world.copy()
    coords = [matrix @ v.co for v in duplicate.data.vertices]
    height = [p.z for p in coords]  # Blender Z-up
    # Blender imports glTF Y-up using a rotated parent: world-space is Z-up.
    # Remove any face crossing the cutoff so garments have clean boundaries.
    keep = {p.index for p in duplicate.data.polygons if all(lo <= height[i] <= hi for i in p.vertices)}
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(duplicate.data)
    bm.faces.ensure_lookup_table()
    for f in list(bm.faces):
        if f.index not in keep:
            bmesh.ops.delete(bm, geom=[f], context="FACES")
    bm.to_mesh(duplicate.data)
    bm.free()
    if len(duplicate.data.polygons) < 20:
        bpy.data.objects.remove(duplicate, do_unlink=True)
        return None
    select_one(duplicate)
    solid = duplicate.modifiers.new("FabricThickness", "SOLIDIFY")
    solid.thickness = thickness
    solid.offset = 1.0
    # Displace along vertex normals; original bone weights and armature retained.
    displace = duplicate.modifiers.new("FabricClearance", "DISPLACE")
    displace.strength = offset
    return duplicate


def main():
    args = arguments()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(Path(args.input).resolve()))
    bpy.context.view_layer.update()
    armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and len(o.vertices) > 0] if False else [
        o for o in bpy.data.objects if o.type == "MESH" and len(o.data.vertices) > 0
    ]
    skinned = [o for o in meshes if any(m.type == "ARMATURE" for m in o.modifiers) and len(o.vertex_groups)]
    if not armatures or not skinned:
        raise RuntimeError("A14 requires a properly skinned humanoid GLB; no procedural replacement head")
    body = max(skinned, key=lambda o: len(o.data.vertices))
    world_z = [(body.matrix_world @ v.co).z for v in body.data.vertices]
    low, high = min(world_z), max(world_z)
    h = high - low
    if h < 0.5:
        raise RuntimeError("Unreasonable avatar height")
    palette = {
        "vest": material("RB_OceanBlue_Vest", (0.08, 0.32, 0.40)),
        "pants": material("RB_Canvas_Trousers", (0.38, 0.30, 0.21)),
        "boots": material("RB_Leather_Boots", (0.16, 0.105, 0.075)),
    }
    bands = [
        ("RB_SailorVest", .48, .79, "vest", .008, .013),
        ("RB_CanvasPants", .17, .48, "pants", .009, .012),
        ("RB_LeatherBoots", .035, .18, "boots", .008, .014),
    ]
    results = []
    for name, a, b, color, thick, clearance in bands:
        obj = shell(body, name, low + a*h, low + b*h, palette[color], thick, clearance)
        results.append({"name": name, "faces": len(obj.data.polygons) if obj else 0, "created": obj is not None})
    if not any(x["created"] for x in results):
        raise RuntimeError("No clothing generated; review source topology and cutoff")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(output.resolve()), export_format="GLB",
        export_skins=True, export_animations=True, export_apply=False)
    report = {"source": Path(args.input).name, "output": output.name,
        "armatures": len(armatures), "source_skinned_meshes": len(skinned),
        "original_source_vertices": len(body.data.vertices),
        "garments": results, "status": "TECHNICAL_CANDIDATE_ONLY",
        "notes": "Surface shells can clip during animation; visual/animation QA required."}
    Path(args.report).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
