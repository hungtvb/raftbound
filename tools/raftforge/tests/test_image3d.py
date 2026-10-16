"""Hermetic local adapter tests: no model weights, paid API, GPU or network."""
from __future__ import annotations
import json
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageDraw
import trimesh

from raftforge.image3d import (
    BACKENDS, Image3DOptions, backend_command, normalize_to_glb,
    inspect_mesh, preprocess_image, probe_gpu, run_image3d
)


class ImageTo3DTest(unittest.TestCase):
    def _image(self, path,alpha=True):
        im=Image.new('RGBA',(240,180),(230,230,230,0 if alpha else 255))
        ImageDraw.Draw(im).ellipse((62,18,178,163),fill=(215,130,45,255))
        im.save(path)
        return path

    def test_preprocessor_alpha_centered_and_repeatable(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            original=self._image(tmp/'original.png')
            a,b=tmp/'a.png',tmp/'b.png'
            x=preprocess_image(original,a)
            y=preprocess_image(original,b)
            self.assertEqual(x['preprocessor'],'provided_alpha')
            self.assertEqual(x['normalized_sha256'],y['normalized_sha256'])
            with Image.open(a) as verified:
                self.assertEqual(verified.size,(512,512))
                self.assertEqual(verified.getpixel((0,0)),(128,128,128))

    def test_preprocessor_flat_background(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            src=self._image(tmp/'flat.png',alpha=False)
            meta=preprocess_image(src,tmp/'clean.png')
            self.assertEqual(meta['preprocessor'],'flat_bg_corner_flood')
            self.assertGreater(meta['cropped_bounds_px'][0],5)
            self.assertLess(meta['cropped_bounds_px'][2],240)

    def test_preprocessor_rejects_complex_background(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            im=Image.new('RGB',(200,180))
            im.putpixel((0,0),(255,0,0));im.putpixel((199,0),(0,255,0));im.putpixel((0,179),(0,0,255));im.putpixel((199,179),(255,255,255))
            src=tmp/'complex.png';im.save(src)
            with self.assertRaisesRegex(ValueError,'Complex background'):
                preprocess_image(src,tmp/'clean.png')

    def test_real_glb_normalization_and_static_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp)
            mesh=trimesh.creation.icosphere(subdivisions=2)
            mesh.apply_scale([.7,.5,1.1])
            src=tmp/'raw.obj';mesh.export(src)
            target=tmp/'model.glb'
            transform=normalize_to_glb(src,target,1.8,'z')
            self.assertGreater(transform['scale_factor'],0)
            report=inspect_mesh(target,30000)
            self.assertTrue(report['static_pass'])
            self.assertAlmostEqual(max(report['dimensions_m']),1.8,places=2)
            self.assertAlmostEqual(report['bounds_m'][0][1],0,places=3)
            self.assertFalse(report['visual_approved'])
            self.assertEqual(target.read_bytes()[:4],b'glTF')

    def test_triangle_budget_is_not_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            mesh=trimesh.creation.icosphere(subdivisions=3)
            dest=Path(tmp)/'large.glb';mesh.export(dest)
            qa=inspect_mesh(dest,budget=300)
            self.assertFalse(qa['static_pass'])
            self.assertFalse(qa['budget_ok'])

    def test_triposr_command_and_successful_stub_e2e(self):
        # The stub writes a REAL GLB, letting us test path conventions, process
        # isolation, preprocessing, normalization, SHA-256, and QA end-to-end.
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            src=self._image(base/'input-ref.png')
            repo=base/'fake-triposr';repo.mkdir()
            (repo/'run.py').write_text('''import argparse,os,pathlib,sys,trimesh
p=argparse.ArgumentParser();p.add_argument('image');p.add_argument('--no-remove-bg',action='store_true');p.add_argument('--model-save-format');p.add_argument('--output-dir');p.add_argument('--device');args=p.parse_args()
assert os.environ.get('HF_HUB_OFFLINE')=='1'
assert os.environ.get('TRANSFORMERS_OFFLINE')=='1'
out=pathlib.Path(args.output_dir)/'0';out.mkdir(parents=True,exist_ok=True)
trimesh.creation.icosphere(subdivisions=2).export(out/'mesh.glb')
''',encoding='utf-8')
            opts=Image3DOptions(backend='triposr',backend_dir=repo,input_image=src,output_dir=base/'final')
            report=run_image3d(opts)
            self.assertEqual(report['status'],'static_pass')
            self.assertEqual(report['visual_status'],'NOT_VALIDATED')
            self.assertTrue((base/'final/model.glb').is_file())
            self.assertTrue((base/'final/evidence.json').is_file())
            self.assertFalse(report['network_isolation_enforced'])
            self.assertEqual(report['backend'],'triposr')

    def test_textured_obj_to_glb_preserves_uv_texture(self):
        from trimesh.visual.material import PBRMaterial
        from trimesh.visual.texture import TextureVisuals
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            im=Image.new('RGB',(16,16),(210,115,76))
            mesh=trimesh.creation.box(extents=(1,1,1))
            uv=np.zeros((len(mesh.vertices),2),dtype=np.float32)
            uv[:,0]=np.clip(mesh.vertices[:,0]+.5,0,1)
            uv[:,1]=np.clip(mesh.vertices[:,1]+.5,0,1)
            mesh.visual=TextureVisuals(uv=uv,material=PBRMaterial(name='wood',baseColorTexture=im))
            # Stub real OBJ/MTL sidecars as generated by texture-capable tools.
            payload=trimesh.exchange.obj.export_obj(mesh,include_texture=True,return_texture=True)
            src=base/'sample.obj';src.write_text(payload[0])
            for name,data in payload[1].items():
                (base/name).write_bytes(data)
            dst=base/'out.glb'
            normalize_to_glb(src,dst)
            qa=inspect_mesh(dst)
            self.assertTrue(qa['static_pass'])
            self.assertGreater(qa['uv_geometry_count'],0)
            self.assertGreater(qa['albedo_texture_geometry_count'],0)

    def test_backend_missing_and_instantmesh_command(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);repo=base/'instantmesh';repo.mkdir()
            (repo/'run.py').write_text('')
            (repo/'configs').mkdir();(repo/'configs/instant-mesh-large.yaml').write_text('{}')
            clean=base/'input.png';clean.write_bytes(b'PNG')
            opts=Image3DOptions(backend='instantmesh',backend_dir=repo,input_image=clean,output_dir=base/'out')
            cmd,expected=backend_command(opts,clean,base/'raw')
            self.assertIn('--export_texmap',cmd)
            self.assertIn('--no_rembg',cmd)
            self.assertTrue(str(expected).endswith('instant-mesh-large/meshes/input.obj'))
            (repo/'run.py').unlink()
            with self.assertRaises(FileNotFoundError):backend_command(opts,clean,base/'raw')

    def test_reject_nonlocal_and_unsupported_backend(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);im=self._image(path/'one.png')
            opts=Image3DOptions('unsupported',path,im,path/'out')
            with self.assertRaises(ValueError):run_image3d(opts)
            no_gpu=probe_gpu()
            self.assertIn('cuda_available',no_gpu)

if __name__=='__main__':unittest.main()
