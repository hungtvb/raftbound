"""Run `python -m raftforge build --recipe presets/raft_tile.json` or `batch`."""
import argparse,json,sys
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
    img=sub.add_parser('image2mesh',help='Run a locally installed open-source image-to-3D backend')
    img.add_argument('--backend',required=True,choices=['triposr','instantmesh'])
    img.add_argument('--backend-dir',type=Path,required=True)
    img.add_argument('--image',type=Path,required=True)
    img.add_argument('--out',type=Path,default=Path('output/image3d'))
    img.add_argument('--python',dest='python_executable',default=sys.executable)
    img.add_argument('--source-up',choices=['y','z'],default='y')
    img.add_argument('--size-m',type=float,default=1.8)
    img.add_argument('--tri-budget',type=int,default=30000)
    img.add_argument('--config',default='configs/instant-mesh-large.yaml')
    img.add_argument('--steps',type=int,default=30)
    img.add_argument('--timeout',type=int,default=3600)
    img.add_argument('--allow-complex-bg',action='store_true')
    img.add_argument('--render',action='store_true')
    prep=sub.add_parser('image-prep',help='Generate model-ready isolated neutral-canvas image')
    prep.add_argument('--image',type=Path,required=True)
    prep.add_argument('--out',type=Path,required=True)
    prep.add_argument('--allow-complex-bg',action='store_true')
    args=p.parse_args()
    if args.cmd=='image-prep':
        from .image3d import preprocess_image
        info=preprocess_image(args.image,args.out,allow_complex_bg=args.allow_complex_bg)
        print(json.dumps(info,indent=2))
        return
    if args.cmd=='image2mesh':
        from .image3d import Image3DOptions,run_image3d
        opts=Image3DOptions(backend=args.backend,backend_dir=args.backend_dir,
              input_image=args.image,output_dir=args.out,
              target_max_dim_m=args.size_m,source_up=args.source_up,
              triangle_budget=args.tri_budget,python_executable=args.python_executable,
              timeout_sec=args.timeout,instantmesh_config=args.config,
              instantmesh_steps=args.steps,allow_complex_bg=args.allow_complex_bg,
              preview=args.render)
        outcome=run_image3d(opts)
        print(json.dumps(outcome,indent=2))
        if not outcome['qa']['static_pass']:raise SystemExit(2)
        return
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
