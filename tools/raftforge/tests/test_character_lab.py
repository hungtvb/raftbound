import json
import tempfile
from types import SimpleNamespace
import numpy as np
import unittest
from pathlib import Path
from character_lab.quality import audit,fit_rigged_glb,art_gate,read_glb,create_visual_review

ROOT=Path(__file__).resolve().parents[1]
GLB=(ROOT/'input/survivor_sailor_skinned_A07.glb') if (ROOT/'input/survivor_sailor_skinned_A07.glb').exists() else (ROOT.parents[1]/'assets/glb/survivor_sailor_skinned.glb')

class TestCharacterLab(unittest.TestCase):
 def test_actual_a07_skin_audit(self):
  a=audit(GLB)
  self.assertTrue(a['technical_pass'],a['technical_errors'])
  self.assertEqual(a['bones'],17)
  self.assertGreater(a['triangles'],15000)
  self.assertFalse(a['production_ready'])
 def test_fit_preserves_original_nodes_skin_and_binary(self):
  with tempfile.TemporaryDirectory() as d:
   out=Path(d)/'fit.glb'
   original,chunks=read_glb(GLB)
   data=fit_rigged_glb(GLB,out,1.8,180)
   fitted,new_chunks=read_glb(out)
   self.assertEqual(data['preserved_skins'],1)
   self.assertEqual(data['yaw_degrees'],180)
   self.assertEqual(fitted['skins'],original['skins'])
   self.assertEqual(chunks[1:],new_chunks[1:])
   self.assertEqual(original['nodes'],fitted['nodes'][:len(original['nodes'])])
   self.assertAlmostEqual(audit(out)['dimensions_m'][1],1.8,places=2)
 def test_reviews_reject_incomplete_and_unconvincing_art(self):
  tech=audit(GLB)
  with self.assertRaises(ValueError):art_gate({'face':5},tech)
  scores=dict.fromkeys(['silhouette','face','hands','clothing','in_game_readability','animation_deformation'],5)
  scores['hands']=2;scores['reviewer_notes']='Hands need real sculpted anatomy'
  result=art_gate(scores,tech)
  self.assertEqual(result['decision'],'NEEDS_ART_REWORK')
  self.assertFalse(result['production_ready'])
 def test_reviews_only_approve_reviewed_asset(self):
  s={k:4 for k in ['silhouette','face','hands','clothing','in_game_readability','animation_deformation']}
  s['reviewer_notes']='Reviewed front, side, back, gameplay, animation'
  self.assertTrue(art_gate(s,audit(GLB))['production_ready'])
  self.assertFalse(art_gate(s,{'technical_pass':False})['production_ready'])
 def test_character_actual_vertex_colors_are_visible(self):
  try:import vtk
  except ImportError:self.skipTest('Optional VTK')
  import numpy as np
  from character_lab.preview import render_glb
  image=np.asarray(render_glb(GLB,angle='front',size=(320,350)))
  spread=image.max(axis=2).astype(float)-image.min(axis=2).astype(float)
  self.assertGreater(float((spread>60).mean()),.04,'QA renderer lost A07 vertex colors')
 def test_pbr_material_tints_vertex_colors(self):
  from character_lab.preview import _compose_vertex_material_color
  white_vertices=np.array([[255,255,255],[128,255,128]],dtype=np.uint8)
  mat=SimpleNamespace(baseColorFactor=[.08,.32,.40,1.])
  result=_compose_vertex_material_color(white_vertices,mat)
  np.testing.assert_array_equal(result[0],[20,82,102])
  self.assertLess(int(result[1,0]),int(result[1,1]))
  self.assertGreater(int(result[1,2]),int(result[1,0]))
  np.testing.assert_array_equal(
      _compose_vertex_material_color(white_vertices,None),white_vertices)

 def test_glb_rejects_bad_magic(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'bad.glb';p.write_bytes(b'not glTF');
   with self.assertRaises(ValueError):read_glb(p)
 def test_render_board_is_real_3d_if_vtk(self):
  try:import vtk
  except ImportError:self.skipTest('Optional free VTK missing')
  with tempfile.TemporaryDirectory() as d:
   p=create_visual_review(GLB,Path(d)/'review.png')
   self.assertGreater(p.stat().st_size,10000)

if __name__=='__main__':unittest.main()
