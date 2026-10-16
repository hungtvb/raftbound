"""Run from Blender background or Scripting tab after importing raft wood assets.
Project UVs and connect tileable albedo/roughness/normal to Principled BSDF.
"""
import bpy,sys,argparse
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--textures',required=True)
args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
textures=Path(args.textures).resolve()
paths={k:textures/f'wood_{k}.png' for k in ('basecolor','roughness','normal')}
assert all(p.is_file() for p in paths.values()),paths
img={k:bpy.data.images.load(str(p),check_existing=True) for k,p in paths.items()}
img['roughness'].colorspace_settings.name='Non-Color';img['normal'].colorspace_settings.name='Non-Color'
materials=[m for m in bpy.data.materials if 'wood' in m.name.lower() or 'timber' in m.name.lower()]
for mat in materials:
 mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links
 pbr=next((n for n in nodes if n.type=='BSDF_PRINCIPLED'),None)
 if not pbr:continue
 for key,y in (('basecolor',350),('roughness',90),('normal',-170)):
  n=nodes.new('ShaderNodeTexImage');n.label='RB_A03 Wood '+key;n.image=img[key];n.location=(-560,y);n.extension='REPEAT';n.interpolation='Linear'
  if key=='basecolor':links.new(n.outputs['Color'],pbr.inputs['Base Color'])
  elif key=='roughness':links.new(n.outputs['Color'],pbr.inputs['Roughness'])
  else:
   nm=nodes.new('ShaderNodeNormalMap');nm.location=(-250,-170);nm.inputs['Strength'].default_value=.38
   links.new(n.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],pbr.inputs['Normal'])
for ob in bpy.data.objects:
 if ob.type!='MESH' or not any(m in materials for m in ob.data.materials if m):continue
 mesh=ob.data
 uv=mesh.uv_layers.active or mesh.uv_layers.new(name='RB_WoodUV')
 for poly in mesh.polygons:
  nx,ny,nz=map(abs,poly.normal)
  for loop_id in poly.loop_indices:
   p=mesh.vertices[mesh.loops[loop_id].vertex_index].co
   if ny>=nx and ny>=nz:coord=(p.x*.35,p.y*.02+p.z*.5)
   elif nx>=nz:coord=(p.z*.5,p.y*.5)
   else:coord=(p.x*.35,p.y*.5)
   uv.data[loop_id].uv=coord
print('RB_A03 wood PBR attached to',len(materials),'materials')
