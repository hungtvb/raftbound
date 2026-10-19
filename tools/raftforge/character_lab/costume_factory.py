"""RAFTFORGE A14 — artist-oriented standalone garment factory.

This replaces the old triangle-cropped body-shell shirt/shorts/boots.
Generates independent fitted mesh topology and transfers 65-bone skin weights
using a nearest-neighbor body-surface field. Fully offline and free.
"""
import argparse
import json
import sys
from pathlib import Path
import bpy


def arguments():
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--report',required=True)
    return p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])


def main():
    args=arguments()
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(Path(args.input).resolve()))
    bpy.context.view_layer.update()
    armatures=[o for o in bpy.data.objects if o.type=='ARMATURE']
    meshes=[o for o in bpy.data.objects if o.type=='MESH' and len(o.data.vertices)]
    skinned=[o for o in meshes if any(m.type=='ARMATURE' for m in o.modifiers)
             and len(o.vertex_groups)>0]
    if len(armatures)!=1 or not skinned:
        raise RuntimeError('Independent outfit requires the real Quaternius skinned human')
    body=max(skinned,key=lambda o:len(o.data.vertices))
    if not body.name.startswith('SuperHero_Male'):
        raise RuntimeError('Cannot identify CC0 source body: '+body.name)
    if len(armatures[0].data.bones)<60:
        raise RuntimeError('Expected >=60 original deform bones')
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from survivor_outfit import produce
    details=produce(body,armatures[0],meshes)
    required={'RB_TShirt','RB_CrewNeck','RB_CargoShorts','RB_CanvasShoes_L',
              'RB_CanvasShoes_R','RB_ShortHair'}
    names={x['name'] for x in details}
    if not required.issubset(names):
        raise RuntimeError('New independent clothing was not fully generated')
    if any(not x['skinned'] or x['vertices']<30 for x in details):
        raise RuntimeError('Skin weight transfer failed')
    out=Path(args.output)
    out.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(out.resolve()),export_format='GLB',
        export_skins=True,export_animations=True,export_apply=False)
    if not out.exists() or out.stat().st_size<200000:
        raise RuntimeError('Expected non-empty independent garment GLB')
    report={
        'source':Path(args.input).name,'output':out.name,
        'armatures':len(armatures),'source_skinned_meshes':len(skinned),
        'original_source_vertices':len(body.data.vertices),
        'garments':details,'art_details':[],
        'method':'INDEPENDENT_LOFT_MESH_KNN_SKIN_WEIGHTS',
        'status':'TECHNICAL_CANDIDATE_ONLY',
        'notes':'New T-shirt sleeves/shorts/shoes/hair are independent geometry. '
                'Animation, self-intersection and visual art require separate QA.'}
    Path(args.report).write_text(json.dumps(report,indent=2))
    print('SURVIVOR_OUTFIT',json.dumps(report,indent=2))


if __name__=='__main__':main()
