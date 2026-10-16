#!/usr/bin/env python3
"""A07 acceptance of packed GLB, independent of builder and WebGL mock."""
import json,struct,collections
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parents[1]

def parse(b):
    assert len(b)>=32
    assert struct.unpack_from('<III',b,0)==(0x46546c67,2,len(b))
    n,t=struct.unpack_from('<II',b,12);assert t==0x4e4f534a
    j=json.loads(b[20:20+n]);q=20+n
    n2,t2=struct.unpack_from('<II',b,q);assert t2==0x004e4942
    return j,b[q+8:q+8+n2]
DT={5121:'u1',5123:'<u2',5125:'<u4',5126:'<f4'}
DIM={'SCALAR':1,'VEC3':3,'VEC4':4,'MAT4':16}
def read(doc,bin,acc_id):
    acc=doc['accessors'][acc_id];bv=doc['bufferViews'][acc['bufferView']]
    offset=bv.get('byteOffset',0)+acc.get('byteOffset',0)
    sz= np.dtype(DT[acc['componentType']]).itemsize*DIM[acc['type']]
    assert bv.get('byteStride',sz)==sz
    return np.frombuffer(bin,dtype=DT[acc['componentType']],count=acc['count']*DIM[acc['type']],offset=offset).reshape(acc['count'],DIM[acc['type']])

def colors(doc,bin):
    bucket=collections.Counter();triangleCount=0
    for desc in doc['meshes']:
        for prim in desc['primitives']:
            attrs=prim['attributes'];p=read(doc,bin,attrs['POSITION']);ind=read(doc,bin,prim['indices']).flatten()
            assert len(ind)%3==0 and np.max(ind)<len(p)
            if 'COLOR_0' in attrs:
                col=read(doc,bin,attrs['COLOR_0']);assert col.shape==(len(p),3)
                assert np.isfinite(col).all() and np.min(col)>=0 and np.max(col)<=1
                # Each source segment has constant palette color; require one per triangle.
                assert np.allclose(col[ind[0::3]],col[ind[1::3]],atol=1e-6)
                assert np.allclose(col[ind[0::3]],col[ind[2::3]],atol=1e-6)
                palette=col[ind[::3]]
            else:
                col=doc['materials'][prim['material']]['pbrMetallicRoughness']['baseColorFactor'][:3]
                palette=np.tile(np.array(col),(len(ind)//3,1))
            for rgb,count in zip(*np.unique(np.round(palette,5),axis=0,return_counts=True)):
                bucket[tuple(round(float(c),5) for c in rgb)]+=int(count)
            triangleCount+=len(ind)//3
    return bucket,triangleCount

new_json,new_bin=parse((P/'glb/survivor_sailor_skinned.glb').read_bytes())
assert len(new_json['skins'])==1 and len(new_json['skins'][0]['joints'])==17
assert len(new_json['meshes'])==2, 'expected two draw batches'
assert len(new_json['materials'])==2
assert all('COLOR_0' in p['attributes'] for m in new_json['meshes'] for p in m['primitives'])
newhist,newtri=colors(new_json,new_bin)
# Fixture records the per-color triangle counts from the immutable A06 release.
# Keeping this small reference with the asset kit makes QA reproducible offline.
fixture=json.loads((P/'tests/fixtures/A06_color_triangle_histogram.json').read_text())
oldtri=fixture['triangles'];oldbatches=fixture['material_primitives']
oldhist=collections.Counter({tuple(float(x) for x in row['rgb']):row['triangles'] for row in fixture['colors']})
assert oldtri==newtri==18628,(oldtri,newtri)
assert oldhist==newhist, f'Vertex color mismatch {oldhist-newhist} {newhist-oldhist}'
assert len(newhist)>=20,len(newhist)
print(f'PASS A07: {newtri} triangles, 17 bones, material batches {oldbatches} -> 2, {len(newhist)} colors preserved EXACTLY by triangle count')
