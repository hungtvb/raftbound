"""Build a native Blender staging .blend from RAFTBOUND production GLBs.

Run in Blender 4.2+:
  blender --background --python blender/build_scene.py -- --source ./glb --output ./blender-out

This creates editable Blender objects and a gallery .blend; additionally exports each
asset from Blender with pivots reset to the original authored coordinate system.
The geometry source of this kit is src/build_meshes.py, with Blender as the finishing,
materials, scene authoring, and render/export stage.
"""
import bpy, sys, json, math, argparse
from pathlib import Path
from mathutils import Vector

p=argparse.ArgumentParser()
p.add_argument('--source',required=True)
p.add_argument('--output',required=True)
p.add_argument('--skip-render',action='store_true')
args=p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
SOURCE=Path(args.source).resolve();OUTPUT=Path(args.output).resolve()
OUTPUT.mkdir(parents=True,exist_ok=True);(OUTPUT/'glb').mkdir(exist_ok=True)
assert SOURCE.exists(),f'Missing source GLB folder: {SOURCE}'
assert list(SOURCE.glob('*.glb')),'No GLB input meshes'

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
for col in list(bpy.data.collections):
    if col.name not in ('Collection',):bpy.data.collections.remove(col)

root=bpy.data.collections.new('RB_ASSET_PACK_A02')
bpy.context.scene.collection.children.link(root)
filelist=sorted(SOURCE.glob('*.glb'))
asset_index={}
cols=4;gap=3.25

def imported_assets(filepath):
    existing=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(filepath))
    return [obj for obj in bpy.data.objects if obj not in existing]

for i,filepath in enumerate(filelist):
    aid=filepath.stem; col=bpy.data.collections.new('RB_'+aid.upper());root.children.link(col)
    objs=imported_assets(filepath)
    for ob in objs:
        for old in list(ob.users_collection):old.objects.unlink(ob)
        col.objects.link(ob)
        ob['asset_id']=aid
        if ob.type=='MESH':
            for m in ob.data.materials:
                if m:
                    m.use_nodes=True
                    m.diffuse_color=m.diffuse_color
            ob.data.name=f'RB_{aid}_{ob.name}'
    col['game_tile_m']=2.0
    col['glb_source']=filepath.name
    col['units']='meter'
    col['forward']='-Z in glTF coordinate system'
    col['pivot']='local asset origin'
    asset_index[aid]={'objects':objs,'collection':col}

# Re-export asset collections with original pivots before scene gallery offsets.
# Blender's importer/exporter handles glTF Y-up <-> Blender Z-up transforms.
for aid,item in asset_index.items():
    bpy.ops.object.select_all(action='DESELECT')
    selected=[ob for ob in item['objects'] if ob.type in ('MESH','EMPTY')]
    for ob in selected: ob.select_set(True)
    if selected:
        bpy.context.view_layer.objects.active=selected[0]
        bpy.ops.export_scene.gltf(filepath=str(OUTPUT/'glb'/(aid+'.glb')),
            export_format='GLB',use_selection=True,
            export_apply=False,export_yup=True,
            export_materials='EXPORT',export_cameras=False,export_lights=False)

for i,(aid,item) in enumerate(asset_index.items()):
    col,row=i%cols,i//cols
    offset=Vector(((col-(cols-1)/2)*gap,(-row+1)*gap,0))
    for ob in item['objects']:
        if ob.parent is None: ob.location+=offset
        # Mesh can be selected in Blender Outliner by asset family.

# Add neutral environment for review render.
def material(name,color,rough=1):
    m=bpy.data.materials.new(name);m.use_nodes=True
    bsdf=m.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value=color
        bsdf.inputs['Roughness'].default_value=rough
    return m

studio=material('RB_studio_seafoam',(0.70,0.82,0.79,1))
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.34))
plane=bpy.context.object;plane.name='STUDIO_FLOOR';plane.data.materials.append(studio)

world=bpy.context.scene.world or bpy.data.worlds.new('RB_StudioWorld')
bpy.context.scene.world=world;world.use_nodes=True
bg=world.node_tree.nodes.get('Background')
if bg:
    bg.inputs['Color'].default_value=(0.75,0.84,0.84,1)
    bg.inputs['Strength'].default_value=.7

def point_at(obj, p):
    direction=Vector(p)-obj.location
    obj.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()

def area(name,location,power,size,color):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    ob=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(ob)
    ob.location=location;point_at(ob,(0,-2,0));return ob
area('RB_Key',(3,-6,9),1800,8,(1,.94,.82))
area('RB_Fill',(-6,1,7),1250,8,(.75,.88,1))
area('RB_Rim',(1,7,8),900,7,(.98,.93,.8))
cam_data=bpy.data.cameras.new('RB_Gallery_Camera')
cam=bpy.data.objects.new('RB_Gallery_Camera',cam_data)
bpy.context.scene.collection.objects.link(cam)
cam.location=(10,-17,19);point_at(cam,(0,-1.8,0))
cam_data.type='ORTHO';cam_data.ortho_scale=17.5
bpy.context.scene.camera=cam
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=24
scene.render.resolution_x=1800;scene.render.resolution_y=1200
scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX'
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(OUTPUT/'RB_A02_gallery_blender.png')
# Geometry groups, geometry names and all material nodes remain editable.
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT/'RAFTBOUND_A02.blend'))
if not args.skip_render: bpy.ops.render.render(write_still=True)
print('SAVED',str(OUTPUT/'RAFTBOUND_A02.blend'))
