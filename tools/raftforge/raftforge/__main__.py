"""Run `python -m raftforge build --recipe presets/raft_tile.json` or `batch`."""
import argparse,json
from pathlib import Path
from .generators import build
from .validation import validate
from .materials import wood_maps


def main():
    p=argparse.ArgumentParser(description='RAFTFORGE: free local 3D asset factory for RAFTBOUND')
    sub=p.add_subparsers(dest='cmd',required=True)
    one=sub.add_parser('build');one.add_argument('--recipe',required=True);one.add_argument('--out',default='output')
    batch=sub.add_parser('batch');batch.add_argument('--presets',default='presets');batch.add_argument('--out',default='output');batch.add_argument('--render',action='store_true')
    variants=sub.add_parser('variants');variants.add_argument('--recipe',required=True);variants.add_argument('--count',type=int,default=4);variants.add_argument('--out',default='output/variants')
    v=sub.add_parser('validate');v.add_argument('glb');v.add_argument('--type',required=True,choices=['raft_tile','storage_chest','compact_grill'])
    args=p.parse_args()
    if args.cmd=='validate':
        r=validate(Path(args.glb),args.type);print(json.dumps(r,indent=2));raise SystemExit(0 if r['static_pass'] else 1)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    if args.cmd=='variants':
        if not 1<=args.count<=12: raise ValueError('--count must be between 1 and 12')
        initial=json.loads(Path(args.recipe).read_text(encoding='utf-8'))
        for i in range(args.count):
            recipe={**initial,'seed':int(initial.get('seed',42))+i}
            b=build(recipe);glb=out/f'{b.name}_v{i:02d}.glb'
            b.scene().export(glb)
            result=validate(glb,recipe['type'])
            if not result['static_pass']:raise ValueError(f'Invalid variant {i}: {result}')
            print(f'variant {i:02d} seed={recipe["seed"]}: {glb.name} {result["triangles"]} triangles')
        return
    configs=[Path(args.recipe)] if args.cmd=='build' else sorted(Path(args.presets).glob('*.json'))
    reports=[]
    for file in configs:
        recipe=json.loads(file.read_text(encoding='utf-8'))
        b=build(recipe);glb=out/f'{b.name}.glb'
        b.scene().export(glb)
        report=validate(glb,recipe['type']);reports.append(report)
        print(f"{'PASS' if report['static_pass'] else 'FAIL'} {glb.name}: {report['triangles']} tris, {report['draw_batches']} batches, {glb.stat().st_size:,} bytes")
    wood_maps(out/'textures')
    (out/'qa.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
    if args.cmd=='batch' and args.render:
        try:
            from .preview import contact_sheet
            contact_sheet([out/f'{build(json.loads(file.read_text())).name}.glb' for file in configs],out/'contact-sheet.png')
        except ImportError as e:
            print('Preview not available (optional VTK required):',e)
    if not all(r['static_pass'] for r in reports):raise SystemExit('One or more static quality gates failed')

if __name__=='__main__':main()
