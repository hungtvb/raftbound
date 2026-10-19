"""Blender 4.x deformation stress harness for RAFTFORGE A14.

These are *synthetic pose stresses*, NOT shipped idle/walk/cast clips.
Every snapshot is exported as a genuine static GLB from evaluated, skinned meshes.
No GPU, paid service or motion data is required.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import kdtree


POSES = {
    'neutral': {},
    'step_stress': {
        'spine_02': ('X', 5),
        'thigh_l': ('X', 24),
        'thigh_r': ('X', -24),
        'calf_l': ('X', 14),
        'upperarm_l': ('X', -13),
        'upperarm_r': ('X', 13),
        'Head': ('Y', 9),
    },
    'arm_reach_stress': {
        'spine_03': ('Y', 10),
        'upperarm_r': ('X', 32),
        'lowerarm_r': ('Y', -32),
        'upperarm_l': ('X', -18),
        'Head': ('Y', -13),
    }
}
GARMENTS = ['RB_TShirt', 'RB_CargoShorts', 'RB_CanvasShoes_L', 'RB_CanvasShoes_R']


def opts():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--out', required=True)
    return p.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])


def world_vertices(ob, dg):
    evaluated = ob.evaluated_get(dg)
    mesh = evaluated.to_mesh()
    try:
        matrix = evaluated.matrix_world
        return [matrix @ v.co for v in mesh.vertices]
    finally:
        evaluated.to_mesh_clear()


def pose(arm, movements):
    for bone in arm.pose.bones:
        bone.rotation_mode = 'XYZ'
        bone.rotation_euler = (0, 0, 0)
    for name, (axis, angle) in movements.items():
        if name not in arm.pose.bones:
            raise RuntimeError(f'Missing pose-control bone: {name}')
        rot = arm.pose.bones[name].rotation_euler
        rot['XYZ'.index(axis)] = math.radians(angle)
    bpy.context.view_layer.update()


def measure(body, cloth, dg):
    body_points = world_vertices(body, dg)
    tree = kdtree.KDTree(len(body_points))
    for idx, p in enumerate(body_points):
        tree.insert(p, idx)
    tree.balance()
    report = {}
    for name, obj in cloth.items():
        points = world_vertices(obj, dg)
        distances = sorted(tree.find(p)[2] for p in points)
        median = distances[len(distances)//2]
        report[name] = {
            'vertices': len(points), 'median_to_body_m': round(float(median), 5),
            'fraction_gt_2mm': round(sum(v>.002 for v in distances)/len(distances), 4),
            'fraction_lt_1mm': round(sum(v<.001 for v in distances)/len(distances), 4)
        }
    return report


def snapshot(out_path, source_meshes, dg):
    clones = []
    bpy.ops.object.select_all(action='DESELECT')
    for original in source_meshes:
        evaluated = original.evaluated_get(dg)
        snapshot_mesh = bpy.data.meshes.new_from_object(evaluated,
                                preserve_all_data_layers=True, depsgraph=dg)
        result = bpy.data.objects.new('QA_'+original.name, snapshot_mesh)
        bpy.context.collection.objects.link(result)
        result.matrix_world = evaluated.matrix_world.copy()
        clones.append(result)
        result.select_set(True)
    bpy.context.view_layer.objects.active = clones[0]
    try:
        bpy.ops.export_scene.gltf(filepath=str(out_path), export_format='GLB',
                     use_selection=True, export_skins=False,
                     export_animations=False, export_apply=False)
    finally:
        for obj in clones:
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)


def main():
    args = opts()
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(Path(args.input).resolve()))
    armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
    if len(armatures) != 1:
        raise RuntimeError('Expected exactly one humanoid armature')
    arm = armatures[0]
    # Importing a rig may also create hidden Icosphere custom-bone helpers.
    # They are NOT artwork and must never be baked into posed GLB snapshots.
    accepted = ('SuperHero_Male', 'Eyes', 'Eyebrows')
    meshes = [o for o in bpy.data.objects
              if o.type == 'MESH' and
              (o.name.startswith('RB_') or any(o.name.startswith(k) for k in accepted))]
    if len(meshes) < 6:
        raise RuntimeError('Expected character, garments and accessories; none or too few selected')
    matches = [o for o in meshes if o.name.startswith('SuperHero_Male')]
    if len(matches) != 1:
        raise RuntimeError('Source base mesh not uniquely named')
    body = matches[0]
    cloth = {name: next((o for o in meshes if o.name == name), None) for name in GARMENTS}
    if any(v is None for v in cloth.values()):
        raise RuntimeError('Independent T-shirt, shorts, and both shoes must be skinned')
    for obj in cloth.values():
        if not any(m.type == 'ARMATURE' for m in obj.modifiers):
            raise RuntimeError(f'{obj.name} is not rig-deformable')

    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    evaluations = {}
    neutral_base = None
    all_meshes = list(meshes)
    for name, movement in POSES.items():
        pose(arm, movement)
        dg = bpy.context.evaluated_depsgraph_get()
        results = measure(body, cloth, dg)
        if any(v['fraction_gt_2mm'] < .50 for v in results.values()):
            raise RuntimeError(f'Pose {name} collapsed garment clearance: {results}')
        # Prove we evaluated a pose instead of just exporting neutral 3x.
        sample = world_vertices(body, dg)
        sample_xyz = np.array([list(p) for p in sample], dtype=float)
        if neutral_base is None:
            neutral_base = sample_xyz
        else:
            moved = np.linalg.norm(sample_xyz-neutral_base,axis=1)
            if np.quantile(moved,.95) < .01:
                raise RuntimeError(f'Pose {name} produced no meaningful mesh deformation')
        image_mesh = root / f'{name}.glb'
        snapshot(image_mesh, all_meshes, dg)
        if image_mesh.stat().st_size < 20000:
            raise RuntimeError('Pose snapshot empty')
        evaluations[name] = {'garments':results,'snapshot':image_mesh.name,
                             'bones_actuated':list(movement)}
        print('POSE_STRESS', name, results)
    report={'source':Path(args.input).name,
            'status':'SIMULATED_DEFORMATION_ONLY_NOT_GAMEPLAY_ANIMATION',
            'poses':evaluations,'limitations':[
                'No source idle/walk/cast motion clips were imported.',
                'Nearest-surface distance is not a signed collision/intersection test.',
                'Artist review and Three.js animation retarget remain required.'
            ]}
    (root/'report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'status':report['status'],'poses':list(evaluations)},indent=2))


if __name__ == '__main__':
    main()
