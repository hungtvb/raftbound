"""unittest discover -s tests -v: real GLB export/import and deterministic QA."""
from __future__ import annotations
import hashlib,json,tempfile,unittest
from pathlib import Path
from raftforge.generators import build
from raftforge.geometry import chamfer_box,rod,ring
from raftforge.validation import validate
from raftforge.materials import wood_maps
import trimesh
import numpy as np

ROOT=Path(__file__).resolve().parents[1]

class FactoryTest(unittest.TestCase):
    def test_presets_generate_valid_glb(self):
        with tempfile.TemporaryDirectory() as tmp:
            for recipe_file in sorted((ROOT/'presets').glob('*.json')):
                recipe=json.loads(recipe_file.read_text())
                builder=build(recipe)
                glb=Path(tmp)/(builder.name+'.glb')
                builder.scene().export(glb)
                result=validate(glb,recipe['type'])
                self.assertTrue(result['static_pass'],result)
                self.assertEqual(glb.read_bytes()[:4],b'glTF')
                self.assertLess(glb.stat().st_size,800_000)

    def test_seed_reproducibility(self):
        r={'type':'raft_tile','seed':919,'weathering':.65,'planks':7,'detail':2}
        x=build(r).scene().export(file_type='glb')
        y=build(r).scene().export(file_type='glb')
        self.assertEqual(hashlib.sha256(x).hexdigest(),hashlib.sha256(y).hexdigest())
        self.assertNotEqual(x,build({**r,'seed':920}).scene().export(file_type='glb'))

    def test_detail_budget_and_validation(self):
        for kind in ['raft_tile','storage_chest','compact_grill']:
            simple=build({'type':kind,'detail':0}).scene()
            refined=build({'type':kind,'detail':3}).scene()
            self.assertLess(sum(len(m.faces) for m in simple.geometry.values()),
                            sum(len(m.faces) for m in refined.geometry.values()))

    def test_recipe_rejection(self):
        with self.assertRaises(ValueError):build({'type':'unsupported'})
        for recipe in ({'type':'raft_tile','planks':3},
                       {'type':'raft_tile','weathering':1.5},
                       {'type':'compact_grill','detail':10}):
            with self.assertRaises(AssertionError):build(recipe)

    def test_primitive_normals(self):
        b=chamfer_box((1,.5,.4),.025)
        self.assertTrue(b.is_watertight)
        self.assertTrue(b.is_winding_consistent)
        self.assertGreater(b.volume,0)
        rod_mesh=rod((0,0,0),(0,1,1),.02)
        self.assertTrue(np.isfinite(rod_mesh.vertices).all())
        self.assertGreater(len(ring((0,0,0),.5,.02).faces),200)

    def test_variants_have_real_distinct_geometry(self):
        a=build({'type':'raft_tile','seed':48}).scene().export(file_type='glb')
        b=build({'type':'raft_tile','seed':49}).scene().export(file_type='glb')
        self.assertNotEqual(a,b)

    def test_wood_maps_repeatable(self):
        with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
            for x,y in zip(wood_maps(Path(a)),wood_maps(Path(b))):
                self.assertEqual((Path(a)/x).read_bytes(),(Path(b)/y).read_bytes())

    def test_render_preview_optional(self):
        try:
            import vtk
        except ImportError:
            self.skipTest('VTK not installed in minimal CI')
        from raftforge.preview import render_glb
        with tempfile.TemporaryDirectory() as d:
            glb=Path(d)/'chest.glb';build({'type':'storage_chest'}).scene().export(glb)
            img=render_glb(glb,size=(320,256))
            self.assertEqual(img.size,(320,256))
            self.assertGreater(float(np.std(np.asarray(img))),12)


    def test_render_glb_vertex_colors_not_lost(self):
        try:
            import vtk
        except ImportError:
            self.skipTest('VTK not installed in minimal CI')
        from raftforge.preview import render_glb
        from trimesh.visual import ColorVisuals
        with tempfile.TemporaryDirectory() as d:
            mesh = trimesh.creation.box(extents=(1.,1.,1.))
            mesh.visual = ColorVisuals(mesh=mesh,vertex_colors=np.tile([238,42,18,255],(len(mesh.vertices),1)).astype('uint8'))
            path=Path(d)/'red.glb';mesh.export(path)
            image = np.asarray(render_glb(path,size=(320,256)))
            red_pixels=(image[:,:,0]>image[:,:,1]*1.4)&(image[:,:,0]>image[:,:,2]*1.4)
            self.assertGreater(float(np.mean(red_pixels)),.1)

if __name__=='__main__':unittest.main()
