#!/usr/bin/env python3
"""Assemble a live-ready starter raft from production meshes, no duplicate authoring."""
from pathlib import Path
import trimesh, numpy as np
ROOT=Path(__file__).resolve().parents[1]
world=trimesh.Scene()

def put(name,x,y,z,rot=0):
    source=trimesh.load(ROOT/'glb'/f'{name}.glb',force='scene')
    T=trimesh.transformations.translation_matrix([x,y,z]) @ trimesh.transformations.rotation_matrix(rot,[0,1,0])
    for i,(gn,mesh) in enumerate(source.geometry.items()):
        world.add_geometry(mesh.copy(),geom_name=f'{name}_{len(world.geometry):03d}_{i}',node_name=f'{name}_{len(world.geometry):03d}_{i}',transform=T)

for x in (-2,0,2):
    for z in (-2,0,2):put('foundation_2m',x,0,z)
put('compact_grill',-2,.1,-2)
put('solar_purifier',0,.1,-2)
put('planter_box',2,.1,-2)
put('storage_chest',2,.1,2)
put('salvage_net_tool',-1,.1,1)
put('plank_bundle',1,.1,2)
put('salvage_barrel',5,-.12,-1,.4)
put('plastic_bottle',4,0,3,.6)
put('palm_leaf',-4,.02,2,.5)
put('buoy_marker',-3.7,0,-3.2)
path=ROOT/'starter_raft_scene.glb';world.export(path)
print('Built',path,round(path.stat().st_size/1024),'KB')
