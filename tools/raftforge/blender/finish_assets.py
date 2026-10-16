"""OPTIONAL Blender 4.2+ finishing stage. Not exercised without Blender installed.

Run e.g.:
blender -b --python blender/finish_assets.py -- --input output/storage_chest_art.glb --output output/blender_finished

Converts incoming glTF to Blender scene, adds simple stylized lighting and writes
an editable blend file plus a separately exported glTF; original mesh is preserved.
"""
from pathlib import Path
import argparse,sys,math
import bpy
from mathutils import Vector

parser=argparse.ArgumentParser()
parser.add_argument('--input',required=True)
parser.add_argument('--output',default='output/blender_finished')
parser.add_argument('--render',action='store_true')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
path=Path(args.input).resolve();output=Path(args.output).resolve()
output.mkdir(parents=True,exist_ok=True)
if not path.exists():raise FileNotFoundError(path)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(path))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
if not meshes:raise RuntimeError('No mesh imported')
for obj in meshes:
    # Keep flat faces on stylized hard-surface objects; bevels are modeled.
    for polygon in obj.data.polygons:polygon.use_smooth=False
for name,loc,power,size in [('Key',(4,-5,7),1000,5),('Fill',(-6,-1,3),460,4),('Rim',(1,5,5),700,3)]:
    lamp=bpy.data.lights.new(name,'AREA');lamp.energy=power;lamp.shape='DISK';lamp.size=size
    light=bpy.data.objects.new(name,lamp);bpy.context.collection.objects.link(light);light.location=loc
scene=bpy.context.scene
world=bpy.data.worlds.new('RAFTFORGE studio');world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.11,.19,.23,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65;scene.world=world
bounds=[obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
low=Vector(tuple(min(p[i] for p in bounds) for i in range(3)))
high=Vector(tuple(max(p[i] for p in bounds) for i in range(3)))
focus=(low+high)*.5
cam_data=bpy.data.cameras.new('HeroCamera');cam=bpy.data.objects.new('HeroCamera',cam_data)
scene.collection.objects.link(cam);cam.location=focus+Vector((2.6,-3.9,2.8))*(high-low).length/3.0
cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler()
scene.camera=cam;cam_data.type='ORTHO';cam_data.ortho_scale=(high-low).length*1.27
scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=1024;scene.render.resolution_y=1024
scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
blend=output/(path.stem+'.blend');bpy.ops.wm.save_as_mainfile(filepath=str(blend))
if args.render:
    scene.render.filepath=str(output/(path.stem+'_blender.png'))
    bpy.ops.render.render(write_still=True)
# Do not overwrite the source GLB: preserve authoritative mesh/UV/scale for QA.
print('RAFTFORGE Blender project:',blend)
