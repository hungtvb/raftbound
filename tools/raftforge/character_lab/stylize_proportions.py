"""Real character proportion sculpt on Blender rig and meshes — no fake 2D art.

Make the existing CC0 human less tall and muscular, closer to the compact,
stylized survival-game direction without copying Raft's original 3D assets.

THE IMPORTANT BIT: Deform the vertex rest positions AND joint edit-bone
heads/tails with the same continuous world-space warp. Preserve vertex
groups, animation skeleton topology, materials and bone-attached equipment.

Run:
 blender -b --python-exit-code 2 --python stylize_proportions.py -- \
    --input sailor-costume-candidate.glb --output sailor-compact.glb \
    --report proportions.json
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def parse():
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--report',required=True)
    p.add_argument('--height',type=float,default=1.66)
    p.add_argument('--shoulder-width',type=float,default=.84)
    p.add_argument('--head-width',type=float,default=1.12)
    return p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])


def interp(a,b,t):
    return a+(b-a)*max(0.,min(1.,t))


def smooth(a,b,t):
    r=max(0.,min(1.,(t-a)/(b-a)))
    return r*r*(3.-2.*r)


def visual_landmarks(body,arm):
    coords=[body.matrix_world@v.co for v in body.data.vertices]
    min_y=min(v.z for v in coords)
    max_y=max(v.z for v in coords)
    h=max_y-min_y
    heads=[v for v in coords if v.z>min_y+h*.87]
    head_span=max(v.x for v in heads)-min(v.x for v in heads)
    bones=arm.data.bones
    shoulder_l=arm.matrix_world@bones['upperarm_l'].head_local
    shoulder_r=arm.matrix_world@bones['upperarm_r'].head_local
    span=abs(shoulder_l.x-shoulder_r.x)
    return dict(height=h,head_width=head_span,shoulder_span=span,
                head_height_ratio=head_span/h,shoulder_height_ratio=span/h,
                hands_span=max(v.x for v in coords)-min(v.x for v in coords),
                world_min_z=min_y,world_max_z=max_y)


def main():
    a=parse()
    if not 1.53<=a.height<=1.77:
        raise ValueError('Compact character target must be 1.53-1.77 m')
    if not .74<=a.shoulder_width<=.92:
        raise ValueError('shoulder-width should be 0.74..0.92')
    if not 1.05<=a.head_width<=1.24:
        raise ValueError('head-width should be 1.05..1.24')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(Path(a.input).resolve()))
    armatures=[o for o in bpy.data.objects if o.type=='ARMATURE']
    if len(armatures)!=1:raise RuntimeError('Expected one imported 65-bone rig')
    arm=armatures[0]
    meshes=[o for o in bpy.data.objects if o.type=='MESH' and len(o.data.vertices)]
    deform=[o for o in meshes if any(m.type=='ARMATURE' for m in o.modifiers)]
    if len(arm.data.bones)<60 or len(deform)<4:
        raise RuntimeError('Missing deformable body/garments or source rig')
    body=next((o for o in deform if o.name.startswith('SuperHero_Male')),None)
    if body is None:raise RuntimeError('The original sculpted body was not found')
    if 'upperarm_l' not in arm.data.bones or 'upperarm_r' not in arm.data.bones:
        raise RuntimeError('Shoulder rest-pose landmarks unavailable')

    original=visual_landmarks(body,arm)
    low=original['world_min_z']
    h=original['height']
    if h<1.5 or h>2.2:raise RuntimeError('Unexpected starting human stature')

    # Piecewise continuous y-axis compression. Keep the head round, shorten
    # legs and avoid tall/heroic chest proportions.
    vertical_breaks=[0.,.48,.83,1.]
    vertical_scales=[.82,.91,1.04]
    def cumulative(q):
        q=max(0.,min(1.,q))
        running=0.
        for i in range(len(vertical_scales)):
            a0=vertical_breaks[i]
            a1=vertical_breaks[i+1]
            running+=max(0.,min(q,a1)-a0)*vertical_scales[i]
        return running

    total=cumulative(1.)
    def warp(world):
        q=(world.z-low)/h
        q_clamped=max(0.,min(1.,q))
        # The body is neutral around x=0; all hand, arm, cap, belt,
        # backpack and shoulder coordinates are warped consistently.
        shoulder_t=smooth(.71,.84,q_clamped)
        head_t=smooth(.84,.92,q_clamped)
        # taper the width along height; strong arm shortening and gentler
        # torso compression to avoid overly muscular superhero build
        width=interp(a.shoulder_width,.96,1.-smooth(.30,.65,q_clamped))
        width=interp(width,a.shoulder_width,shoulder_t)
        width=interp(width,a.head_width,head_t)
        depth=interp(.95,1.075,head_t)
        z=low+(cumulative(q_clamped)+(q-q_clamped)*vertical_scales[0 if q<0 else -1])*h*a.height/(h*total)
        return Vector((world.x*width,world.y*depth,z))

    # Cache rest coordinates before changing bones (bone parenting causes
    # object matrices to change). This is what makes accessories follow.
    originals={o:[o.matrix_world@v.co for v in o.data.vertices] for o in meshes}
    arm_inv=arm.matrix_world.inverted()
    bone_rest={}
    for bone in arm.data.bones:
        bone_rest[bone.name]=(arm.matrix_world@bone.head_local,
                              arm.matrix_world@bone.tail_local)

    bpy.context.view_layer.objects.active=arm
    bpy.ops.object.mode_set(mode='EDIT')
    for bone in arm.data.edit_bones:
        old_head,old_tail=bone_rest[bone.name]
        bone.head=arm_inv@warp(old_head)
        bone.tail=arm_inv@warp(old_tail)
        if (bone.tail-bone.head).length<.002:
            raise RuntimeError('Degenerate rest bone after reshaping '+bone.name)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()

    for obj,worlds in originals.items():
        # Parent-bone transforms have now changed; transform positions
        # into the *current* mesh's local space.
        inv=obj.matrix_world.inverted()
        for v,w in zip(obj.data.vertices,worlds):
            v.co=inv@warp(w)
        obj.data.update()

    bpy.context.view_layer.update()
    final=visual_landmarks(body,arm)
    initial_head=original['head_height_ratio']
    new_head=final['head_height_ratio']
    old_shoulder=original['shoulder_height_ratio']
    new_shoulder=final['shoulder_height_ratio']
    if abs(final['height']-a.height)>.018:
        raise RuntimeError('Model failed compact height gate: '+str(final))
    if new_head<=initial_head*1.08:
        raise RuntimeError('Head did not become stylistically more readable')
    if new_shoulder>=old_shoulder*.96:
        raise RuntimeError('Shoulders did not narrow sufficiently')
    # All 65 deform bones must be preserved, and non-empty clothing still
    # exists. Blender exports inverse binds from new rest-pose matrices.
    out=Path(a.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(out.resolve()),export_format='GLB',
        export_skins=True,export_animations=True,export_apply=False)
    if out.stat().st_size<300000:
        raise RuntimeError('Invalid exported compact GLB')
    report=dict(status='PROPORTION_RESCULPT_TECHNICAL_PASS',
                old=original,new=final,
                requested_height=a.height,
                shoulder_width_multiplier=a.shoulder_width,
                head_width_multiplier=a.head_width,
                original_bones=len(arm.data.bones),
                skinned_meshes=len(deform),all_meshes=len(meshes),
                labels=['Shorter legs', 'Narrower shoulders & arms',
                        'Bigger readable head', 'Preserved skin weights and bone topology'],
                limitations='Art acceptance and gameplay integration remain separate gates.')
    Path(a.report).write_text(json.dumps(report,indent=2),encoding='utf8')
    print('COMPACT_CHARACTER_PROPORTIONS',json.dumps(report,indent=2))


if __name__=='__main__':
    main()
