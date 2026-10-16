"""RAFTBOUND A03 Blender authoring stage (Blender 4.2+).
Usage:
blender --background --python blender/finish_A03.py -- \
    --source ./glb/survivor_sailor_rig.glb --textures ./textures --output ./blender-out

Creates an editable .blend, keyframed articulated node-rig, and rendered previews.
A03 is a rigid transform rig (named parent/child pivots), not armature skinning.
"""
import bpy,sys,math,argparse
from pathlib import Path
from mathutils import Vector
ap=argparse.ArgumentParser()
ap.add_argument('--source',required=True)
ap.add_argument('--textures',required=True)
ap.add_argument('--output',required=True)
ap.add_argument('--skip-render',action='store_true')
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
source=Path(args.source).resolve();textures=Path(args.textures).resolve();out=Path(args.output).resolve()
out.mkdir(parents=True,exist_ok=True)
assert source.is_file(),source
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source))
# Blender glTF importer preserves empty-pivot node objects for joint animation.
def pivot(name):
 exact=bpy.data.objects.get(name)
 if exact:return exact
 candidates=[ob for ob in bpy.data.objects if ob.name.startswith(name+'.')]
 if candidates:return sorted(candidates,key=lambda o:o.name)[0]
 raise RuntimeError('Missing animated GLB joint: '+name)
for j in ('Hips','Spine','Head','R_Shoulder','R_Elbow','R_Wrist','L_Shoulder','L_Hip','R_Hip','L_Knee','R_Knee'):
 pivot(j).rotation_mode='XYZ'

def set_key(frame,angles):
 for name,rx in angles.items():
  ob=pivot(name);ob.rotation_euler.x=rx;ob.keyframe_insert(data_path='rotation_euler',frame=frame,index=0)

# Frame ranges correspond to real-time gameplay clips: idle(1-24), walk(31-54), throw(62-96).
for f in (1,13,24):set_key(f,{'Spine':.03 if f==13 else -.015,'Head':.025 if f==13 else -.02,'R_Shoulder':0,'L_Shoulder':0,'L_Hip':0,'R_Hip':0,'R_Elbow':0})
for f,ang in ((31,0),(37,.43),(43,0),(49,-.43),(55,0)):
 set_key(f,{'L_Hip':ang,'R_Hip':-ang,'L_Shoulder':-ang*.65,'R_Shoulder':ang*.65,'Spine':.028 if f%2 else -.028})
for f,ang,el in ((62,0,0),(68,-.4,-.3),(76,.74,0),(84,1.5,.2),(94,0,0)):
 set_key(f,{'R_Shoulder':ang,'R_Elbow':el,'Spine':.1*math.sin((f-62)/32*math.pi)})
scene=bpy.context.scene
for n,f in (('IDLE_START',1),('IDLE_END',24),('WALK_START',31),('WALK_END',55),('CAST_START',62),('CAST_END',94)):
 scene.timeline_markers.new(n,frame=f)
scene.frame_start=1;scene.frame_end=94;scene.frame_set(1)
# Dedicated preview environment.
mat=bpy.data.materials.new('RB_A03_Studio');mat.diffuse_color=(.61,.76,.76,1)
bpy.ops.mesh.primitive_plane_add(size=60,location=(0,0,-.015))
plane=bpy.context.object;plane.name='RB_STUDIO_FLOOR';plane.data.materials.append(mat)
world=scene.world or bpy.data.worlds.new('RB_World');scene.world=world;world.use_nodes=True
bg=world.node_tree.nodes.get('Background');bg.inputs['Color'].default_value=(.7,.85,.9,1);bg.inputs['Strength'].default_value=.65

def target(obj,pt): obj.rotation_euler=(Vector(pt)-obj.location).to_track_quat('-Z','Y').to_euler()
ld=bpy.data.lights.new('RB_Softbox','AREA');ld.energy=700;ld.shape='DISK';ld.size=4
lo=bpy.data.objects.new('RB_Softbox',ld);scene.collection.objects.link(lo);lo.location=(2,-4,6);target(lo,(0,0,1))
cam=bpy.data.cameras.new('RB_PreviewCam');co=bpy.data.objects.new('RB_PreviewCam',cam)
scene.collection.objects.link(co);co.location=(3,-5,3);target(co,(0,0,.95));scene.camera=co;cam.type='ORTHO';cam.ortho_scale=2.9
scene.render.engine='CYCLES';scene.cycles.samples=32
scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'RAFTBOUND_A03_survivor.blend'))
if not args.skip_render:
 for name,frame in [('idle',12),('walk',37),('cast',84)]:
  scene.frame_set(frame);scene.render.filepath=str(out/f'survivor_{name}_blender.png');bpy.ops.render.render(write_still=True)
print('SAVED',out/'RAFTBOUND_A03_survivor.blend')
