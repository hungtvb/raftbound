"""RAFTBOUND A06 Blender 4.2+ 3D scene builder + review renders.

Requires Blender installed. NOT executed/visually verified in this environment.
blender -b --python assets/blender/finish_A06.py -- \
  --assets assets/glb --output blender_out/A06 --samples 24

Create editable .blend including skinned survivor, rig, 3x3 modular raft,
crafting props, lighting, camera presets, keyed pose previews.
"""
import argparse
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector, Quaternion

parser=argparse.ArgumentParser()
parser.add_argument('--assets',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--samples',type=int,default=24)
parser.add_argument('--skip-render',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
assets=args.assets.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
assert (assets/'survivor_sailor_skinned.glb').is_file(),'Missing skinned survivor'
for name in ['foundation_2m','compact_grill','solar_purifier','planter_box','storage_chest']:
 assert (assets/f'{name}.glb').is_file(), f'Missing {name}.glb'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=max(8,args.samples)
scene.render.resolution_x=1280;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.view_settings.view_transform='AgX'
world=bpy.data.worlds.new('RAFTBOUND / Open ocean sky');world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.31,.58,.69,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.75;scene.world=world

def import_glb(name,parent,location):
 before=set(bpy.context.scene.objects)
 bpy.ops.import_scene.gltf(filepath=str(assets/f'{name}.glb'))
 imported=[o for o in scene.objects if o not in before]
 anchor=bpy.data.objects.new(f'RB_A06_{name}_anchor',None);scene.collection.objects.link(anchor)
 for o in imported:
  if o.parent is None:o.parent=anchor
 anchor.location=location
 return anchor,imported

survivor,characters=import_glb('survivor_sailor_skinned',None,(0,0,0))
armatures=[o for o in characters if o.type=='ARMATURE']
assert armatures,'glTF skinned survivor did not import as an Armature'
armature=armatures[0]
for bn in ('Hips','Spine','Head','R_Shoulder','R_Elbow','R_Wrist','L_Shoulder','L_Hip','R_Hip'):
 assert bn in armature.pose.bones,'Missing required joint '+bn
skin_meshes=[o for o in characters if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
assert skin_meshes,'No skinned mesh with Armature modifier'
for bone in armature.pose.bones:bone.rotation_mode='QUATERNION'
# Bone-local X is an editable starting point; review IK/skin behavior interactively.
keyframes={
 1:{'Spine':0,'L_Shoulder':0,'R_Shoulder':0,'L_Hip':0,'R_Hip':0},
 15:{'Spine':.03},30:{'Spine':0},
 40:{'L_Hip':.44,'R_Hip':-.44,'L_Shoulder':-.31,'R_Shoulder':.32},
 50:{'L_Hip':-.44,'R_Hip':.44,'L_Shoulder':.31,'R_Shoulder':-.32},
 60:{'L_Hip':0,'R_Hip':0,'L_Shoulder':0,'R_Shoulder':0},
 66:{'R_Shoulder':-.48,'R_Elbow':-.46,'Spine':-.08},
 74:{'R_Shoulder':1.52,'R_Elbow':.20,'Spine':.16},
 88:{'R_Shoulder':1.04,'R_Elbow':.20,'Spine':.12},
 99:{'R_Shoulder':.78,'R_Elbow':.09,'Spine':.07},
 112:{'R_Shoulder':0,'R_Elbow':0,'Spine':0},
}
for frame,angles in keyframes.items():
 for name,angle in angles.items():
  pb=armature.pose.bones[name]
  pb.rotation_quaternion=Quaternion((1,0,0),angle)
  pb.keyframe_insert(data_path='rotation_quaternion',frame=frame,group='RB '+name)
scene.frame_start=1;scene.frame_end=112
for name,frame in [('IDLE',1),('WALK',40),('WINDUP',66),('RELEASE',74),('CONTACT',88),('RETURN',99)]:
 scene.timeline_markers.new(name,frame=frame)

# Ocean surface is visually separate from the physics used in the WebGL game.
water=bpy.data.materials.new('RB_A06_Ocean');water.diffuse_color=(.06,.43,.52,1)
water.use_nodes=True;bsdf=water.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value=(.035,.40,.54,1)
bsdf.inputs['Roughness'].default_value=.29
bsdf.inputs['Metallic'].default_value=.08
bpy.ops.mesh.primitive_plane_add(size=180,location=(0,0,-.47))
sea=bpy.context.object;sea.name='RB_A06_Studio_Ocean';sea.data.materials.append(water)

raft_anchors=[]
for gx in range(-1,2):
 for gy in range(-1,2):
  anchor,_=import_glb('foundation_2m',None,(gx*2,-gy*2,0))
  raft_anchors.append(anchor)
props=[]
for name,pos in [('compact_grill',(-2,0,0)),('solar_purifier',(2,0,0)),('planter_box',(0,-2,0)),('storage_chest',(2,-2,0))]:
 a,_=import_glb(name,None,pos);props.append(a)

lightdata=bpy.data.lights.new('RB_A06_Sun','SUN');lightdata.energy=2.0
sun=bpy.data.objects.new('RB_A06_Sun',lightdata);scene.collection.objects.link(sun);sun.rotation_euler=(math.radians(26),math.radians(-19),math.radians(-34))
area=bpy.data.lights.new('RB_A06_Fill','AREA');area.energy=750;area.shape='DISK';area.size=8
fill=bpy.data.objects.new('RB_A06_Fill',area);scene.collection.objects.link(fill);fill.location=(-4,-4,7)

def point_camera(camera,look_at):
 camera.rotation_euler=(Vector(look_at)-camera.location).to_track_quat('-Z','Y').to_euler()
cam_data=bpy.data.cameras.new('RB_A06_QA_Camera');cam=bpy.data.objects.new('RB_A06_QA_Camera',cam_data);scene.collection.objects.link(cam)
scene.camera=cam;cam_data.type='ORTHO'
shots=[
 ('character_front',1,(0,-5,2.25),(0,0,.97),3.25,False),
 ('character_side',1,(5,0,2.25),(0,0,.97),3.25,False),
 ('character_back',1,(0,5,2.25),(0,0,.97),3.25,False),
 ('character_cast',74,(3,-5,2.5),(0,0,.97),3.3,False),
 ('raft_overview',1,(10,-12,12),(0,0,.7),11.0,True),
]
# Hide raft props in character close-ups, keeping the character readable.
all_scene=[*raft_anchors,*props]
for label,frame,loc,target,scale,show_scene in shots:
 scene.frame_set(frame)
 cam.location=loc;point_camera(cam,target);cam_data.ortho_scale=scale
 for a in all_scene:a.hide_render=not show_scene
 sea.hide_render=not show_scene
 if args.skip_render:continue
 scene.render.filepath=str(out/(label+'.png'))
 bpy.ops.render.render(write_still=True)
for a in all_scene:a.hide_render=False
sea.hide_render=False
scene.frame_set(1)
cam.location=(10,-12,12);point_camera(cam,(0,0,.7));cam_data.ortho_scale=11
bpy.ops.wm.save_as_mainfile(filepath=str(out/'RAFTBOUND_A06_SCENE.blend'))
print('A06 Blender scene created:',out)
