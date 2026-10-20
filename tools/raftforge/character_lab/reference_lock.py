"""RAFTFORGE art-production QA: source-of-truth -> real 4-view contact sheets.

The boards are rendered from GLB geometry via free VTK. No ImageGen or
photorealistic reference hallucination is substituted for a built asset.
Baseline and candidate use the SAME camera framing and four angles.

Usage:
 PYTHONPATH=tools/raftforge python -m character_lab.reference_lock
    --baseline qa/sailor-costume-game-oriented.glb
    --candidate qa/sailor-compact-game-oriented.glb
    --proportions qa/proportions.json
    --blueprint tools/raftforge/character_lab/compact_sailor_blueprint.json
    --out qa/reference-lock
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image, ImageDraw

from .quality import audit
from .preview import font, render_glb


ANGLES = (
    ('FRONT', 'front'),
    ('3/4', 'hero'),
    ('BACK', 'rear'),
    ('TOP', 'top'),
)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_proportions(blueprint, measurements, old_qa, new_qa):
    """Mechanical screening is separate from aesthetic approval."""
    old, new = measurements['old'], measurements['new']
    target = blueprint['target']
    errors = []
    if not old_qa.get('technical_pass') or not new_qa.get('technical_pass'):
        errors.append('glb_geometry_or_skin_invalid')
    if old_qa.get('bones') != new_qa.get('bones'):
        errors.append('bone_topology_changed')
    if new_qa.get('bones', 0) < target['min_bones']:
        errors.append('not_enough_skin_joints')
    if new_qa.get('triangles', 0) > target['triangle_budget']:
        errors.append('polygon_budget_exceeded')
    if abs(float(new['height']) - target['height_m']) > target['height_tolerance_m']:
        errors.append('height_not_within_blueprint')
    if float(new['head_height_ratio']) < target['head_to_height_min']:
        errors.append('head_is_still_too_small')
    if float(new['shoulder_height_ratio']) > target['shoulder_to_height_max']:
        errors.append('shoulders_are_still_too_wide')
    if float(new['shoulder_height_ratio']) >= float(old['shoulder_height_ratio']):
        errors.append('no_relative_shoulder_improvement')
    if float(new['head_height_ratio']) <= float(old['head_height_ratio']):
        errors.append('no_relative_head_improvement')
    if blueprint.get('art_status') != 'PENDING_HUMAN_REVIEW':
        errors.append('cannot_self_approve_art_quality')
    return {
        'technical_gate': 'PASS' if not errors else 'FAIL',
        'errors': errors,
        'art_gate': 'PENDING_HUMAN_REVIEW',
        'release_gate': 'BLOCKED_UNTIL_ART_AND_GAMEPLAY_ACCEPTANCE',
    }


def same_camera_bounds(baseline, candidate):
    a = np.asarray(trimesh.load(baseline, force='scene').bounds, dtype=float)
    b = np.asarray(trimesh.load(candidate, force='scene').bounds, dtype=float)
    bounds = np.stack([np.minimum(a[0], b[0]), np.maximum(a[1], b[1])])
    if bounds.shape != (2, 3) or not np.isfinite(bounds).all():
        raise ValueError('Invalid GLB reference bounds')
    return bounds


def tile_sheet(label, glb, bounds, out, *, cell=(450, 420)):
    """2x2 orthographic contact sheet, tied to the exported GLB sha256."""
    w, h = cell
    board = Image.new('RGB', (w*2+40, h*2+120), '#112b35')
    draw = ImageDraw.Draw(board)
    draw.text((24, 18), f'RAFTFORGE / {label}', font=font(28, True), fill='#f5dbb3')
    draw.text((24, 57), 'LOCKED FRAMING / TRUE GLB / FOUR CAMERA ANGLES',
              font=font(15), fill='#b7dadb')
    for i, (title, angle) in enumerate(ANGLES):
        x = 18 + (i%2)*w
        y = 91 + (i//2)*h
        image = render_glb(glb, angle=angle, size=(w-18,h-30),
                           framing_bounds=bounds)
        board.paste(image, (x,y))
        draw.text((x+10,y+h-25), title, font=font(18, True),fill='#e8d1ad')
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    board.save(out, optimize=True)
    return out


def matrix_sheet(before, after, out):
    """A/B progression matrix, same camera, no image generation."""
    a = Image.open(before).convert('RGB')
    b = Image.open(after).convert('RGB')
    board=Image.new('RGB',(a.width+b.width,max(a.height,b.height)+55),'#102a35')
    board.paste(a,(0,55))
    board.paste(b,(a.width,55))
    d=ImageDraw.Draw(board)
    d.text((22,14),'BEFORE: A14 HEROIC BODY',font=font(21,True),fill='#f3d5a9')
    d.text((a.width+22,14),'AFTER: COMPACT STYLIZED BODY',font=font(21,True),fill='#addfd3')
    out=Path(out)
    board.save(out,optimize=True)
    return out


def run(blueprint_path, baseline, candidate, proportion_path, outdir):
    blueprint=json.loads(Path(blueprint_path).read_text(encoding='utf-8'))
    proportions=json.loads(Path(proportion_path).read_text(encoding='utf-8'))
    a=audit(baseline, target_height=1.8)
    b=audit(candidate, target_height=blueprint['target']['height_m'])
    qa=validate_proportions(blueprint,proportions,a,b)
    if qa['technical_gate']!='PASS':
        raise ValueError('Locked blueprint rejected actual candidate: '+str(qa['errors']))
    bounds=same_camera_bounds(baseline,candidate)
    outdir=Path(outdir)
    outdir.mkdir(parents=True,exist_ok=True)
    before=tile_sheet('BASELINE',baseline,bounds,outdir/'reference_2x2_before.png')
    after=tile_sheet('CANDIDATE',candidate,bounds,outdir/'reference_2x2_after.png')
    matrix=matrix_sheet(before,after,outdir/'before_vs_after_matrix.png')
    # A real 120 px tall screenshot-scale thumbnail is intentional: this shows
    # whether the outfit silhouette reads at realistic third-person game size.
    full=render_glb(candidate,angle='hero',size=(360,440),framing_bounds=bounds)
    thumb=full.resize((100,120),Image.Resampling.LANCZOS)
    thumb.save(outdir/'candidate_gameplay_120px.png')
    report={
      'pipeline':'RAFTFORGE_BLENDER_BLUEPRINT_TO_4VIEW_TO_AB_GATE',
      'source_of_truth':str(blueprint_path),
      'blueprint_sha256':digest(blueprint_path),
      'baseline_sha256':digest(baseline),
      'candidate_sha256':digest(candidate),
      'measurement_sha256':digest(proportion_path),
      'baseline':a['file'],'candidate':b['file'],
      'camera_framing':bounds.round(5).tolist(),
      'triangle_before':a['triangles'],'triangle_after':b['triangles'],
      'bones_before':a['bones'],'bones_after':b['bones'],
      'dimensions_before_m':a['dimensions_m'],
      'dimensions_after_m':b['dimensions_m'],
      'proportion_measures':proportions,
      'review':qa,
      'artifacts':[x.name for x in [before,after,matrix]]+
        ['candidate_gameplay_120px.png'],
      'limitations':[
        'This is shape and material visual QA, not objective beauty scoring.',
        'Renderer is VTK, not the shipping WebGL2 game.',
        'A 120px crop is a visual aid, not a gameplay screenshot.',
        'No AI-generated reference image was used as evidence of actual GLB quality.',
        'No artist approval is inferred from mechanical proportion thresholds.'
      ]
    }
    (outdir/'review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser(description='Four real GLB camera tiles + before/after art gates')
    p.add_argument('--baseline',required=True)
    p.add_argument('--candidate',required=True)
    p.add_argument('--proportions',required=True)
    p.add_argument('--blueprint',required=True)
    p.add_argument('--out',required=True)
    args=p.parse_args()
    print(json.dumps(run(args.blueprint,args.baseline,args.candidate,args.proportions,args.out),
                     indent=2,ensure_ascii=False))


if __name__=='__main__':
    main()
