"""RAFTBOUND Character Lab — deterministic rig integrity, composition and review gates.

Standard library + numpy/trimesh/Pillow; optional free VTK for offscreen real GLB renders.
No downloaded model or AI inference is required. Existing animations/skins are preserved
when fitting GLB geometry under a new root node.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import struct
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

GLB_MAGIC = 0x46546C67
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942


def _pad(raw: bytes, fill: bytes) -> bytes:
    return raw + fill * ((-len(raw)) % 4)


def read_glb(path: str | Path) -> tuple[dict, list[tuple[int, bytes]]]:
    blob=Path(path).read_bytes()
    if len(blob)<20:
        raise ValueError('Invalid GLB: too small')
    magic,version,length=struct.unpack_from('<III',blob)
    if (magic,version,length)!=(GLB_MAGIC,2,len(blob)):
        raise ValueError('GLB magic/version/length mismatch')
    chunks=[]; offset=12
    while offset<len(blob):
        if offset+8>len(blob): raise ValueError('Truncated chunk header')
        size,kind=struct.unpack_from('<II',blob,offset);offset+=8
        if size%4 or offset+size>len(blob):raise ValueError('Malformed GLB chunk')
        chunks.append((kind,blob[offset:offset+size]));offset+=size
    if not chunks or chunks[0][0]!=CHUNK_JSON:
        raise ValueError('GLB must begin with JSON chunk')
    return json.loads(chunks[0][1].decode('utf8').rstrip(' \t\r\n')),chunks


def write_glb(document: dict, chunks: list[tuple[int,bytes]], dst: str | Path) -> Path:
    raw=_pad(json.dumps(document,separators=(',',':'),ensure_ascii=False).encode('utf8'),b' ')
    out_chunks=[(CHUNK_JSON,raw)]+chunks[1:]
    payload=b''.join(struct.pack('<II',len(v),k)+v for k,v in out_chunks)
    target=Path(dst);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(struct.pack('<III',GLB_MAGIC,2,12+len(payload))+payload)
    return target


def _scene_bounds(path: str | Path) -> np.ndarray:
    scene=trimesh.load(path,force='scene')
    if not isinstance(scene,trimesh.Scene) or not scene.geometry:
        raise ValueError('No mesh geometry found')
    result=np.asarray(scene.bounds,dtype=float)
    if result.shape!=(2,3) or not np.isfinite(result).all():
        raise ValueError('Invalid world-space mesh bounds')
    return result


def _joint_names(document:dict) -> list[str]:
    ids={j for skin in document.get('skins',[]) for j in skin.get('joints',[])}
    return sorted(set(document['nodes'][idx].get('name',f'joint_{idx}') for idx in ids))


def audit(path:str|Path, *, target_height:float=1.8, budget:int=25000) -> dict:
    document,_=read_glb(path)
    scene=trimesh.load(path,force='scene')
    bounds=_scene_bounds(path)
    dims=bounds[1]-bounds[0]
    triangles=sum(len(g.faces) for g in scene.geometry.values())
    total_mats=len(document.get('materials',[]))
    joints=_joint_names(document)
    skins=document.get('skins',[])
    animated=document.get('animations',[])
    errs=[];notes=[]
    if triangles>budget:errs.append(f'poly_budget_exceeded: {triangles} > {budget}')
    if dims[1] <= .01:errs.append('zero_or_tiny_height')
    if max(dims[0],dims[2])/max(dims[1],1e-6)>1.25:notes.append('Check upright axis / pose / scale: unusually wide character')
    if abs(dims[1]-target_height)>0.25:notes.append('Height outside recommended playable avatar range; use fit')
    if not skins:errs.append('missing_skin: character cannot deform with skeletal animations')
    if skins and len(joints)<12:notes.append('Low joint count: review animation articulation')
    if not animated:notes.append('No embedded animation; retargeting or runtime animations required')
    # Calculate accessor weights structurally; we cannot claim a full animation stress test.
    attributes=[p.get('attributes',{}) for mesh in document.get('meshes',[]) for p in mesh.get('primitives',[])]
    has_skin_attrs=any('JOINTS_0' in a and 'WEIGHTS_0' in a for a in attributes)
    if skins and not has_skin_attrs:errs.append('skin_has_no_weighted_mesh')
    result={
      'file':Path(path).name,'bounds_m':bounds.round(4).tolist(),
      'dimensions_m':dims.round(4).tolist(),'triangles':int(triangles),
      'materials':total_mats,'mesh_primitives':len(attributes),
      'bones':len(joints),'joint_names':joints,
      'skins':len(skins),'embedded_animations':len(animated),
      'weighted_mesh':has_skin_attrs,'rig_signature':sorted(joints),
      'technical_errors':errs,'warnings':notes,'technical_pass':not errs,
      'visual_approved':False,'production_ready':False,
      'explanation':'Technical integrity is not visual quality. Requires the signed art review gate.'
    }
    return result


def fit_rigged_glb(src:str|Path,dst:str|Path,height_m:float=1.8) -> dict:
    """Uniform root-scale adjustment without rebuilding joints, inverse binds or animations.

    This manipulates glTF JSON only, using a scene root parent. GLB binary chunks are
    copied verbatim. All node IDs and animation targets remain the same.
    """
    if not (.5<=height_m<=2.5):raise ValueError('Invalid character height')
    doc,chunks=read_glb(src)
    if not doc.get('skins'):raise ValueError('Only rigged character GLB accepted')
    original=copy.deepcopy(doc)
    dims=_scene_bounds(src)[1]-_scene_bounds(src)[0]
    if dims[1]<=0:raise ValueError('No height')
    factor=height_m/float(dims[1])
    roots={}
    for scene in doc.get('scenes',[]):
        original_roots=list(scene.get('nodes',[]))
        if not original_roots:continue
        idx=len(doc['nodes'])
        doc['nodes'].append({'name':'RB_CharacterFitRoot','scale':[factor]*3,'children':original_roots})
        scene['nodes']=[idx]
        roots[str(idx)]=original_roots
    if not roots:raise ValueError('No glTF scene roots')
    path=write_glb(doc,chunks,dst)
    after,_=read_glb(path)
    if after.get('skins')!=original.get('skins') or after.get('animations')!=original.get('animations'):
        raise AssertionError('Retargeting data unexpectedly changed')
    if after['nodes'][:len(original['nodes'])]!=original['nodes']:
        raise AssertionError('Original joint nodes unexpectedly changed')
    new_size=(_scene_bounds(path)[1]-_scene_bounds(path)[0])[1]
    if not math.isclose(new_size,height_m,abs_tol=.01):
        raise ValueError(f'Character fit failed {new_size} != {height_m}')
    return {'original_height_m':round(float(dims[1]),4),'target_height_m':height_m,'new_height_m':round(float(new_size),4),'root_scale':round(factor,5),'preserved_skins':len(doc['skins']),'preserved_animations':len(doc.get('animations',[])),'output':str(path)}


def create_visual_review(candidate: str|Path,out: str|Path,reference: str|Path|None=None) -> Path:
    """Real 3D offscreen render at matching camera angles, plus 3rd-person readability.

    Does not fake production art: automatically stamps evidence as unapproved.
    """
    from .preview import render_glb
    samples=[('FRONT','front'),('THREE-QUARTER','hero'),('BACK','rear')]
    paths=[('CANDIDATE',Path(candidate))]
    if reference:paths.insert(0,('CURRENT A07',Path(reference)))
    pad=22; w=440; h=495
    sheet=Image.new('RGB',(len(samples)*w+pad*2,len(paths)*h+132),(239,244,239))
    dr=ImageDraw.Draw(sheet)
    f='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    font=ImageFont.truetype(f,30) if Path(f).exists() else ImageFont.load_default()
    sub=ImageFont.truetype(f,15) if Path(f).exists() else ImageFont.load_default()
    dr.text((pad,22),'RAFTFORGE / CHARACTER ART REVIEW',font=font,fill=(28,61,65))
    dr.text((pad,74),'TRUE GLB RENDERS  /  CONSISTENT CAMERAS  /  NO AI IMAGES',font=sub,fill=(64,97,98))
    for row,(label,path) in enumerate(paths):
        for col,(title,cam) in enumerate(samples):
            im=render_glb(path,angle=cam,size=(420,415))
            x=pad+col*w+10;y=116+row*h
            sheet.paste(im,(x,y))
            dr.text((x+8,y+421),f'{label}  /  {title}',font=sub,fill=(41,75,79))
    dr.text((pad,sheet.height-28),'STATUS: NOT ART-APPROVED   •   face, silhouette, hands, clothing, motion require review',font=sub,fill=(136,66,58))
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);sheet.save(out)
    return out


CRITERIA=['silhouette','face','hands','clothing','in_game_readability','animation_deformation']

def art_gate(scores:dict,technical:dict,minimum:int=4)->dict:
    """Explicit human scores 1-5 are needed. Never infer beauty from geometry/CI."""
    missing=[name for name in CRITERIA if name not in scores]
    if missing:raise ValueError('Art review incomplete: '+', '.join(missing))
    if any(isinstance(scores[k],bool) or not isinstance(scores[k],int) or not 1<=scores[k]<=5 for k in CRITERIA):
        raise ValueError('All art criterion scores must be integers 1..5')
    notes=scores.get('reviewer_notes','')
    if not isinstance(notes,str) or len(notes.strip())<15:
        raise ValueError('Reviewer notes (>=15 chars) required')
    failures=[k for k in CRITERIA if scores[k]<minimum]
    return {'technical_pass':technical.get('technical_pass',False),'scores':{k:scores[k] for k in CRITERIA},'failed_criteria':failures,
            'visual_approved':not failures,'production_ready':bool(technical.get('technical_pass') and not failures),
            'decision':'APPROVE_FOR_IN_GAME_REVIEW' if technical.get('technical_pass') and not failures else 'NEEDS_ART_REWORK',
            'reviewer_notes':notes}


def main():
    p=argparse.ArgumentParser(prog='character-lab',description='Offline QA to stop rigged-asset version churn')
    sub=p.add_subparsers(dest='cmd',required=True)
    a=sub.add_parser('audit');a.add_argument('glb');a.add_argument('--report')
    f=sub.add_parser('fit');f.add_argument('glb');f.add_argument('--out',required=True);f.add_argument('--height',type=float,default=1.8)
    c=sub.add_parser('compare');c.add_argument('glb');c.add_argument('--reference');c.add_argument('--out',required=True)
    r=sub.add_parser('review');r.add_argument('glb');r.add_argument('--scores',required=True);r.add_argument('--out',required=True)
    args=p.parse_args()
    if args.cmd=='audit':out=audit(args.glb)
    elif args.cmd=='fit':out=fit_rigged_glb(args.glb,args.out,args.height)
    elif args.cmd=='compare':out={'image':str(create_visual_review(args.glb,args.out,args.reference))}
    else:
        tech=audit(args.glb);scores=json.loads(Path(args.scores).read_text());out=art_gate(scores,tech)
    print(json.dumps(out,ensure_ascii=False,indent=2))
    target=getattr(args,'report',None) or (getattr(args,'out',None) if args.cmd=='review' else None)
    if target:Path(target).write_text(json.dumps(out,indent=2,ensure_ascii=False))

if __name__=='__main__':main()
