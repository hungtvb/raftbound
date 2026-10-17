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


def shell(source, name, lo, hi, mat, thickness=0.007, offset=0.008,
          max_x_ratio=None, world_x_center=0.0, body_height=1.8):
    """Make a weighted clothing shell from a subset of an artist-made body.

    Selection is by triangle centroid in world space. A single BMesh delete
    operation is linear in mesh size. Existing vertex groups/armature are kept.
    This is still a PROXY garment; animation and clipping need manual review.
    """
    duplicate = source.copy()
    duplicate.data = source.data.copy()
    bpy.context.collection.objects.link(duplicate)
    duplicate.name = name
    duplicate.data.materials.clear()
    duplicate.data.materials.append(mat)
    matrix = duplicate.matrix_world.copy()
    coords = [matrix @ v.co for v in duplicate.data.vertices]
    keep = set()
    for face in duplicate.data.polygons:
        center = sum((coords[i] for i in face.vertices), Vector((0, 0, 0))) / len(face.vertices)
        if lo <= center.z <= hi and (
            max_x_ratio is None or abs(center.x-world_x_center) <= max_x_ratio*body_height
        ):
            keep.add(face.index)
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(duplicate.data)
    bm.faces.ensure_lookup_table()
    bm.faces.index_update()  # Critical: BMesh indices default to -1 after from_mesh.
    remove = [face for face in bm.faces if face.index not in keep]
    if remove:
        bmesh.ops.delete(bm, geom=remove, context="FACES")
    # Remove isolated vertices left by the face operation; preserve remaining weights.
    stray = [v for v in bm.verts if not v.link_faces]
    if stray:
        bmesh.ops.delete(bm, geom=stray, context="VERTS")
    bm.to_mesh(duplicate.data)
    bm.free()
    retained = len(duplicate.data.polygons)
    print("COSTUME_REGION", name, "selected_faces", len(keep), "retained_faces", retained,
          "range_world_z", round(lo, 4), round(hi, 4))
    if retained < 80:
        bpy.data.objects.remove(duplicate, do_unlink=True)
        return None
    # Materialize clearance directly into the base mesh. The glTF exporter
    # ignores unapplied Displace/Solidify modifiers with export_apply=False;
    # they yielded EXACT coordinate duplicates hidden inside the body in A14 CI.
    # Deforming skinned vertices locally along normals preserves their weights.
    duplicate.data.update()
    adjusted = 0
    for vertex in duplicate.data.vertices:
        normal = vertex.normal.copy()
        if normal.length_squared > 1e-10:
            vertex.co += normal.normalized() * (offset + thickness)
            adjusted += 1
    duplicate.data.update()
    print("GARMENT_REST_OFFSET", name, "vertices", adjusted,
          "clearance_m", round(offset + thickness, 5))
    if adjusted < 40:
        raise RuntimeError("Garment is missing usable normal directions")
    return duplicate


def main():
    args = arguments()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(Path(args.input).resolve()))
    bpy.context.view_layer.update()
    armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and len(o.data.vertices) > 0]
    skinned = [o for o in meshes if any(m.type == "ARMATURE" for m in o.modifiers) and len(o.vertex_groups)]
    if not armatures or not skinned:
        raise RuntimeError("A14 requires a properly skinned humanoid GLB; no procedural replacement head")
    body = max(skinned, key=lambda o: len(o.data.vertices))
    world_coords = [body.matrix_world @ v.co for v in body.data.vertices]
    world_z = [v.z for v in world_coords]
    low, high = min(world_z), max(world_z)
    center_x = (min(v.x for v in world_coords) + max(v.x for v in world_coords)) / 2
    print("BODY_WORLD_BOUNDS", {"height": high-low, "x_center": center_x, "mesh": body.name})
    h = high - low
    if h < 0.5:
        raise RuntimeError("Unreasonable avatar height")
    palette = {
        "vest": material("RB_OceanBlue_Vest", (0.08, 0.32, 0.40)),
        "pants": material("RB_Canvas_Trousers", (0.38, 0.30, 0.21)),
        "boots": material("RB_Leather_Boots", (0.16, 0.105, 0.075)),
    }
    bands = [
        ("RB_SailorVest", .48, .79, "vest", .008, .013, .20),
        ("RB_CanvasPants", .17, .48, "pants", .009, .012, None),
        ("RB_LeatherBoots", .00, .19, "boots", .008, .014, None),
    ]
    results = []
    for name, a, b, color, thick, clearance, xratio in bands:
        obj = shell(body, name, low + a*h, low + b*h, palette[color],
                    thick, clearance, max_x_ratio=xratio,
                    world_x_center=center_x, body_height=h)
        results.append({"name": name, "faces": len(obj.data.polygons) if obj else 0, "created": obj is not None})
    if not all(x["created"] for x in results):
        raise RuntimeError("Some garments have insufficient faces; do not export a partial costume")

    # Art direction from actual skinned Quaternius topology, not another cube person.
    # Decorations are parented to anatomical joints for first-pass articulation.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from style_sailor import dress_up
    details = dress_up(body, armatures[0], meshes, low, high, center_x)
    if len(details) < 10:
        raise RuntimeError("Costume identity accents failed to generate")
    print("STYLE_DETAILS", len(details), "objects")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(output.resolve()), export_format="GLB",
        export_skins=True, export_animations=True, export_apply=False)
    report = {"source": Path(args.input).name, "output": output.name,
        "armatures": len(armatures), "source_skinned_meshes": len(skinned),
        "original_source_vertices": len(body.data.vertices),
        "garments": results, "art_details": details,
        "status": "TECHNICAL_CANDIDATE_ONLY",
        "notes": "Rest-pose clearance materialized in mesh vertices; deformation, seams and collision require visual/animation QA."}
    Path(args.report).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
