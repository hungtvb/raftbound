"""Bake RAFTBOUND's real idle/walk/cast curves onto A14's 65-joint rig.

Only rig/animation generation. No paid GPU or downloaded Mixamo action.
- Cast originates from game/cast-motion.js samples (see prepare_cast_samples.js).
- Idle/walk use game.js' sinusoidal stride, swing, breathe amplitudes.
- We preserve the Quaternius skin and the rig-bound sailor equipment.
- Blender NLA tracks are exported as separate glTF AnimationClips.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

FPS=24
def args():
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True)
    p.add_argument('--cast-samples',required=True)
    p.add_argument('--out',required=True)
    p.add_argument('--report',required=True)
    return p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])


# Rotate a rig from its rest pose; imported Quaternius bones are real mesh
# deformation joints, not the custom 17-bone A07 pivots.
CHANNELS={
    'pelvis':0, 'spine_02':0, 'spine_03':0, 'Head':0,
    'thigh_l':0, 'thigh_r':0, 'calf_l':0, 'calf_r':0,
    'upperarm_l':0, 'upperarm_r':0, 'lowerarm_r':0, 'lowerarm_l':0
}
def controls(mode,t,cast_data=None):
    breathe=math.sin(t*1.6)*.025
    head=math.sin(t*1.2)*.03
    data={'spine_03':(breathe,0,0),'Head':(head,0,0)}
    if mode=='walk':
        stride=math.sin(t*10)*.47
        swing=math.sin(t*10)*.34
        data.update({
            'pelvis':(0,math.sin(t*10)*.045,0),
            'spine_02':(0,0,math.sin(t*10)*.04),
            'thigh_l':(stride,0,0),
            'thigh_r':(-stride,0,0),
            'calf_l':(max(0,-stride)*.45,0,0),
            'calf_r':(max(0,stride)*.45,0,0),
            'upperarm_l':(-swing-.06,0,-.08),
            'upperarm_r':(swing,0,.08),
            'lowerarm_r':(-.22,0,0),
            'lowerarm_l':(-.18,0,0)
        })
    elif mode=='cast':
        if cast_data is None:raise ValueError('cast must use actual game timeline samples')
        data.update({
            'spine_03':(breathe+cast_data['spineLean'],0,0),
            'upperarm_r':(cast_data['throwArm'],0,.08),
            'lowerarm_r':(-.22+cast_data['throwElbow'],0,0),
            'upperarm_l':(-.06,0,-.08),
            'lowerarm_l':(-.18,0,0)
        })
    else:
        data.update({'upperarm_l':(-.06,0,-.08),
                     'upperarm_r':(0,0,.08),
                     'lowerarm_l':(-.18,0,0),
                     'lowerarm_r':(-.22,0,0)})
    return data


def shoulder_target(arm, name, mode, t, cast_data=None):
    """Retarget T-pose shoulder to a relaxed, anatomically readable arm.

    Bones imported from glTF point along local +Y in Blender. Converting a
    *world-space* downward target into the bone's bind-local basis avoids the
    mistake in A14 V1 where Euler X changed only arm depth, retaining a T-pose.
    """
    bone=arm.pose.bones[name]
    base_world=(arm.matrix_world @ bone.bone.matrix_local).to_quaternion()
    side=1. if name.endswith('_l') else -1.
    # Default: arms angled naturally toward the sides of the hips.
    lateral=side*.27
    forward=0.
    vertical=-.963
    if mode=='walk':
        swing=math.sin(t*10)*.32
        forward=(swing if side<0 else -swing)
    elif mode=='cast' and name.endswith('_r'):
        arm_angle=float(cast_data['throwArm']) if cast_data else 0.
        # Original cast reaches +1.52rad near release. Retarget to a
        # forward/up throwing vector, with a visible windup.
        k=max(0.,min(1.,(arm_angle+.48)/2.0))
        forward=-.83*k+.25*(1-k)
        vertical=-.963*(1-k)+.45*k
        lateral=side*(.27*(1-k)+.30*k)
    direction=Vector((lateral,forward,vertical)).normalized()
    local_direction=base_world.inverted() @ direction
    return Vector((0,1,0)).rotation_difference(local_direction)


def build_clip(arm, name, sequence, fps=FPS):
    arm.animation_data_create()
    action=bpy.data.actions.new('RB_'+name)
    for sample_idx,(t, values) in enumerate(sequence):
        frame=1+t*fps
        arm.animation_data.action=action
        pose=controls(name,t,values)
        for bone_name in CHANNELS:
            joint=arm.pose.bones[bone_name]
            if bone_name in ('upperarm_l','upperarm_r'):
                joint.rotation_mode='QUATERNION'
                joint.rotation_quaternion=shoulder_target(arm,bone_name,name,t,values)
                joint.keyframe_insert(data_path='rotation_quaternion',frame=frame,group=bone_name)
            else:
                joint.rotation_mode='XYZ'
                joint.rotation_euler=pose.get(bone_name,(0.,0.,0.))
                joint.keyframe_insert(data_path='rotation_euler',frame=frame,group=bone_name)
    for fcurve in action.fcurves:
        for key in fcurve.keyframe_points:
            key.interpolation='LINEAR'
    arm.animation_data.action=None
    track=arm.animation_data.nla_tracks.new()
    track.name='RB_'+name
    track.strips.new(action.name,1,action)
    track.mute=True
    return {'name':'RB_'+name,'duration':sequence[-1][0],
            'keys':len(sequence),'channels':len(action.fcurves)}


def main():
    o=args()
    curve=json.loads(Path(o.cast_samples).read_text())
    if curve.get('source')!='game/cast-motion.js':
        raise ValueError('Cast samples MUST be generated from shipped game timeline')
    samples=curve['samples']
    if len(samples)<20 or abs(samples[-1]['time']-1.28)>.005:
        raise ValueError('Missing the full 1.28 s cast action')
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(Path(o.input).resolve()))
    armatures=[obj for obj in bpy.data.objects if obj.type=='ARMATURE']
    if len(armatures)!=1:
        raise RuntimeError('Expected exactly one humanoid rig')
    arm=armatures[0]
    missing=[n for n in CHANNELS if n not in arm.pose.bones]
    if missing:raise RuntimeError('Retarget joint mapping incomplete: '+str(missing))
    bpy.context.scene.render.fps=FPS
    sequences={
        'idle':[(i/FPS,None) for i in range(0,FPS*2+1,3)],
        'walk':[(i/FPS,None) for i in range(FPS+1)],
        'cast':[(p['time'],p) for p in samples]
    }
    clips=[build_clip(arm,name,seq) for name,seq in sequences.items()]
    # Prevent three clips from blending into rest pose during export.
    arm.animation_data.action=None
    for joint in arm.pose.bones:
        if joint.name in CHANNELS:
            if joint.name in ('upperarm_l','upperarm_r'):
                joint.rotation_mode='QUATERNION'
                joint.rotation_quaternion=(1,0,0,0)
            else:
                joint.rotation_mode='XYZ'
                joint.rotation_euler=(0,0,0)
    bpy.context.scene.frame_set(1)
    out=Path(o.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    # Blender 4.0 exports each NLA track as a separate glTF AnimationClip.
    bpy.ops.export_scene.gltf(filepath=str(out.resolve()),
        export_format='GLB',export_skins=True,
        export_animations=True,export_nla_strips=True,export_apply=False)
    if not out.is_file() or out.stat().st_size<50000:
        raise RuntimeError('Animated GLB not written')
    result={'status':'ANIMATED_RIG_TECHNICAL_CANDIDATE',
        'source':Path(o.input).name,'output':out.name,'fps':FPS,
        'source_cast':'game/cast-motion.js','clips':clips,
        'bones':len(arm.pose.bones),
        'notes':'Blender generated game-derived clips. Actual game WebGL2 loader only supports 17 bones; independent Three.js playback required before integration.'}
    Path(o.report).write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
