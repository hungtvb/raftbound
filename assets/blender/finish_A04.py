"""RAFTBOUND A04 Blender 4.2+ finishing script. NOT executed unless Blender installed.

blender --background --python blender/finish_A04.py -- \
  --source ./glb/survivor_sailor_skinned.glb --textures ./textures \
  --output ./blender-out

Imports the real weighted GLB glTF skin (17 joints) as editable Armature + meshes,
adds three bone-keyframed poses, studio lights, saves .blend and renders PNGs.
Raises exceptions if the importer does not recognize weighted skin/armature.
"""
import bpy,sys,math,argparse
from pathlib import Path
from mathutils import Vector
ap=argparse.ArgumentParser();ap.add_argument('--source',required=True);ap.add_argument('--textures',required=True);ap.add_argument('--output',required=True);ap.add_argument('--skip-render',action='store_true')
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
source=Path(args.source).resolve();out=Path(args.output).resolve();textures=Path(args.textures).resolve();out.mkdir(parents=True,exist_ok=True)
assert source.is_file(),source
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(source))
armatures=[o for o in bpy.data.objects if o.type=='ARMATURE']
assert armatures,'glTF import did not create a bone Armature: skinning not available'
arm=armatures[0]
for name in ('Hips','Spine','Head','R_Shoulder','R_Elbow','R_Wrist','L_Shoulder','L_Hip','R_Hip','L_Knee','R_Knee'):
 assert name in arm.pose.bones, 'Missing bone '+name
skin_meshes=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
assert len(skin_meshes)>=1,'No skinned meshes with Armature modifier'
assert sum(len(o.vertex_groups) for o in skin_meshes)>=17,'Armature has missing vertex groups'
for b in arm.pose.bones:b.rotation_mode='QUATERNION'

def rot(name,value,frame):
 pb=arm.pose.bones[name]
 # Blender bone space differs from glTF Y-up; rotate around local bone X.
 from mathutils import Quaternion
 pb.rotation_quaternion=Quaternion((1,0,0),value)
 pb.keyframe_insert(data_path='rotation_quaternion',frame=frame,group='RAFTBOUND '+name)

sequence=[
 (1,{'Spine':0,'L_Hip':0,'R_Hip':0,'R_Shoulder':0,'L_Shoulder':0}),
 (12,{'Spine':.025,'L_Hip':0,'R_Hip':0,'R_Shoulder':0,'L_Shoulder':0}),
 (24,{'Spine':0,'L_Hip':0,'R_Hip':0,'R_Shoulder':0,'L_Shoulder':0}),
 (31,{'L_Hip':0,'R_Hip':0,'L_Shoulder':0,'R_Shoulder':0}),
 (37,{'L_Hip':.43,'R_Hip':-.43,'L_Shoulder':-.3,'R_Shoulder':.3,'R_Knee':.2}),
 (43,{'L_Hip':0,'R_Hip':0,'L_Shoulder':0,'R_Shoulder':0,'R_Knee':0}),
 (49,{'L_Hip':-.43,'R_Hip':.43,'L_Shoulder':.3,'R_Shoulder':-.3,'R_Knee':0}),
 (55,{'L_Hip':0,'R_Hip':0,'L_Shoulder':0,'R_Shoulder':0}),
 (62,{'R_Shoulder':0,'R_Elbow':0,'Spine':0}),
 (68,{'R_Shoulder':-.4,'R_Elbow':-.3,'Spine':-.06}),
 (76,{'R_Shoulder':.74,'R_Elbow':0,'Spine':.1}),
 (84,{'R_Shoulder':1.5,'R_Elbow':.2,'Spine':.1}),
 (94,{'R_Shoulder':0,'R_Elbow':0,'Spine':0})]
for frame,angles in sequence:
 for bone,angle in angles.items():rot(bone,angle,frame)
scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=94
for label,frame in [('IDLE',1),('WALK',31),('CAST',62)]:scene.timeline_markers.new(label,frame=frame)
scene.frame_set(1)
# Stage for rendered material verification. Scene coordinates are Blender Z-up.
world=scene.world or bpy.data.worlds.new('RAFTBOUND A04 World');scene.world=world;world.use_nodes=True
background=world.node_tree.nodes.get('Background');background.inputs['Color'].default_value=(.65,.81,.88,1);background.inputs['Strength'].default_value=.7
mat=bpy.data.materials.new('RAFTBOUND Studio Floor');mat.use_nodes=True
bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(.42,.64,.65,1);bsdf.inputs['Roughness'].default_value=.9
bpy.ops.mesh.primitive_plane_add(size=100,location=(0,0,-.035));floor=bpy.context.object;floor.name='RB_A04_STAGE';floor.data.materials.append(mat)

# Load true A03 PBR maps as packed Blender images for the timber material demo.
wood_color=textures/'wood_basecolor.png';wood_rough=textures/'wood_roughness.png';wood_normal=textures/'wood_normal.png'
if all(p.exists() for p in (wood_color,wood_rough,wood_normal)):
 wood=bpy.data.materials.new('RB_A04_Wood_PBR');wood.use_nodes=True;nodes=wood.node_tree.nodes;links=wood.node_tree.links
 principled=nodes.get('Principled BSDF')
 color=nodes.new('ShaderNodeTexImage');color.image=bpy.data.images.load(str(wood_color),check_existing=True);color.image.pack();color.location=(-660,160)
 rough=nodes.new('ShaderNodeTexImage');rough.image=bpy.data.images.load(str(wood_rough),check_existing=True);rough.image.colorspace_settings.name='Non-Color';rough.image.pack();rough.location=(-660,-70)
 normaltex=nodes.new('ShaderNodeTexImage');normaltex.image=bpy.data.images.load(str(wood_normal),check_existing=True);normaltex.image.colorspace_settings.name='Non-Color';normaltex.image.pack();normaltex.location=(-660,-300)
 norm=nodes.new('ShaderNodeNormalMap');norm.inputs['Strength'].default_value=.4;norm.location=(-340,-280)
 links.new(color.outputs['Color'],principled.inputs['Base Color']);links.new(rough.outputs['Color'],principled.inputs['Roughness']);links.new(normaltex.outputs['Color'],norm.inputs['Color']);links.new(norm.outputs['Normal'],principled.inputs['Normal'])
 for im in (color.image,rough.image,normaltex.image): im.filepath='//'+im.name

def track(ob,target):ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
light=bpy.data.lights.new('RAFTBOUND A04 Softbox','AREA');light.energy=850;light.size=4
light_ob=bpy.data.objects.new('RAFTBOUND A04 Softbox',light);scene.collection.objects.link(light_ob);light_ob.location=(3,-4,5);track(light_ob,(0,0,1))
cam=bpy.data.cameras.new('RAFTBOUND A04 Camera');co=bpy.data.objects.new('RAFTBOUND A04 Camera',cam);scene.collection.objects.link(co)
co.location=(3,-5,2.75);track(co,(0,0,.95));scene.camera=co;cam.type='ORTHO';cam.ortho_scale=2.6
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.render.resolution_x=960;scene.render.resolution_y=960;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'RAFTBOUND_A04_WEIGHTED.blend'))
if not args.skip_render:
 for name,frame in [('idle',12),('walk',37),('cast',84)]:
  scene.frame_set(frame);scene.render.filepath=str(out/f'A04_{name}_blender.png');bpy.ops.render.render(write_still=True)
print('A04 weighted scene finished',out)
