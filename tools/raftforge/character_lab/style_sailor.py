"""Stylized survival-sailor art pass for a legally sourced skinned human base.

All detail objects are real Blender meshes, assigned PBR factors, positioned in
rest-pose world space and rigidly attached to matching bones. No paid assets.
This improves *silhouette*; it is NOT automatic skinning / animation acceptance.
"""
import math

import bpy
from mathutils import Vector


def material(name, rgb, roughness=0.82, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*rgb, 1.)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    if shader:
        shader.inputs['Base Color'].default_value = (*rgb, 1.)
        shader.inputs['Roughness'].default_value = roughness
        shader.inputs['Metallic'].default_value = metallic
    return mat


def assign_material(mesh, mat):
    mesh.data.materials.clear()
    mesh.data.materials.append(mat)
    for polygon in mesh.data.polygons:
        polygon.material_index = 0


def bone_parent(obj, armature, bone):
    if armature.pose.bones.get(bone) is None:
        raise ValueError(f'Missing attachment bone: {bone}')
    bpy.context.view_layer.update()
    original = obj.matrix_world.copy()
    obj.parent = armature
    obj.parent_type = 'BONE'
    obj.parent_bone = bone
    obj.matrix_world = original
    return obj


def rounded_box(name, location, dimensions, mat, bevel=.016):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    modifier = obj.modifiers.new('SoftCraftedEdges', 'BEVEL')
    modifier.width = min(bevel, min(dimensions) * .30)
    modifier.segments = 3
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    # Bevel already creates the required rounded face normals; a weighted-normal
    # modifier warns when legacy Blender auto-smoothing isn't enabled.
    return obj


def torus(name, center, major, minor, material_, y_scale=1., parent=None, bone=None):
    bpy.ops.mesh.primitive_torus_add(major_segments=40, minor_segments=8,
                                    location=center,
                                    major_radius=major, minor_radius=minor)
    obj = bpy.context.object
    obj.name = name
    obj.scale.y = y_scale
    obj.data.materials.append(material_)
    if parent:
        bone_parent(obj, parent, bone)
    return obj


def strap(name, a, b, radius, material_, parent=None, bone=None):
    start = Vector(a)
    end = Vector(b)
    direction = end - start
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=radius,
                                        depth=direction.length,
                                        location=(start + end) / 2)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
    obj.data.materials.append(material_)
    if parent:
        bone_parent(obj, parent, bone)
    return obj


def dress_up(body, armature, original_meshes, low, high, center_x=0.):
    """Give the sailor human skin, maritime cap, belt, pack and trim.

    Blender is Z-up. The Quaternius GLB imported as glTF faces -Y in Blender,
    which becomes +Z before RAFTBOUND's later 180-degree character orientation.
    """
    h = high - low
    points = [body.matrix_world @ vert.co for vert in body.data.vertices]
    center_y = (min(v.y for v in points) + max(v.y for v in points)) / 2.
    x = center_x
    y = center_y
    P = {
        'skin': material('RB_SunWeatheredSkin', (.68, .47, .35)),
        'eyes': material('RB_Eyes_Ivory', (.76, .80, .76)),
        'brows': material('RB_DarkBrows', (.17, .12, .10)),
        'cap': material('RB_SeafarerCap', (.055, .19, .265)),
        'cap_brim': material('RB_CapBrim', (.09, .12, .14)),
        'sand': material('RB_CanvasSand', (.78, .66, .44)),
        'leather': material('RB_PouchLeather', (.26, .14, .075)),
        'metal': material('RB_WeatheredBrass', (.71, .47, .18), roughness=.38, metallic=.60),
        'pack': material('RB_PackCanvas', (.34, .26, .17)),
    }

    # Costume duplicates were detached from the original body material already.
    assign_material(body, P['skin'])
    for obj in original_meshes:
        if obj == body:
            continue
        name = obj.name.lower()
        if 'brow' in name:
            assign_material(obj, P['brows'])
        elif 'eye' in name:
            assign_material(obj, P['eyes'])

    created = []
    def attach(obj, joint):
        bone_parent(obj, armature, joint)
        created.append({'name': obj.name, 'joint': joint,
                        'triangles': sum(max(len(poly.vertices)-2,0) for poly in obj.data.polygons)})
        return obj

    # Hat: low sculpted dome + distinct visor so the playable 120px silhouette
    # reads "survival sailor", instead of a bald superhero.
    bpy.ops.mesh.primitive_uv_sphere_add(segments=28, ring_count=14,
                                         location=(x, y, high-.024*h))
    dome = bpy.context.object
    dome.name = 'RB_FisherCap_Crown'
    dome.scale = (.135*h/1.82, .123*h/1.82, .109*h/1.82)
    dome.data.materials.append(P['cap'])
    attach(dome, 'Head')
    brim = rounded_box('RB_FisherCap_Visor',
                       (x, y-.104*h/1.82, high-.104*h/1.82),
                       (.265*h/1.82, .115*h/1.82, .024*h/1.82),
                       P['cap_brim'], .014)
    attach(brim, 'Head')
    cap_band = torus('RB_CapBand', (x, y, high-.105*h/1.82),
                     .113*h/1.82, .009*h/1.82, P['sand'], .90)
    attach(cap_band, 'Head')

    # Neck cloth hides rough clipped cloth edges and separates face from vest.
    scarf = torus('RB_Neckerchief',
                 (x, y, low+.828*h), .087*h/1.82, .016*h/1.82,
                 P['sand'], .78)
    attach(scarf, 'spine_03')

    # Belt bridges procedural jacket/trouser cut-lines in a deliberate seam.
    waist_z = low + .485*h
    belt = torus('RB_LeatherBelt', (x, y, waist_z),
                 .158*h/1.82, .020*h/1.82, P['leather'], .79)
    attach(belt, 'pelvis')
    buckle = rounded_box('RB_BrassBuckle',
                         (x, y-.139*h/1.82, waist_z),
                         (.085*h/1.82, .029*h/1.82, .060*h/1.82),
                         P['metal'], .007)
    attach(buckle, 'pelvis')

    # Compact pouch and functional backpack add strong side/rear silhouettes.
    pouch = rounded_box('RB_ToolPouch',
                        (x+.198*h/1.82, y+.035*h/1.82, low+.445*h),
                        (.142*h/1.82, .084*h/1.82, .157*h/1.82),
                        P['leather'], .025)
    attach(pouch, 'pelvis')
    pack = rounded_box('RB_WaterproofPack',
                       (x, y+.166*h/1.82, low+.692*h),
                       (.285*h/1.82, .126*h/1.82, .302*h/1.82),
                       P['pack'], .034)
    attach(pack, 'spine_03')
    flap = rounded_box('RB_PackTopFlap',
                       (x, y+.239*h/1.82, low+.783*h),
                       (.277*h/1.82, .045*h/1.82, .088*h/1.82),
                       P['leather'], .018)
    attach(flap, 'spine_03')

    # Curved geometry isn't needed for first-pass strapping: real round straps
    # add depth with modest geometry instead of two more flat color bands.
    for side in [-1, 1]:
        shoulder = (x+side*.145*h/1.82, y+.091*h/1.82, low+.786*h)
        hip = (x+side*.122*h/1.82, y+.190*h/1.82, low+.603*h)
        created_obj = strap('RB_BackStrap_'+('L' if side<0 else 'R'),
                            shoulder, hip, .013*h/1.82, P['leather'])
        attach(created_obj, 'spine_03')
        cuff = torus('RB_LeatherBootCuff_'+('L' if side<0 else 'R'),
                     (x+side*.112*h/1.82, y, low+.185*h),
                     .074*h/1.82, .013*h/1.82, P['leather'], .79)
        attach(cuff, 'calf_l' if side>0 else 'calf_r')

    return created
