"""Procedural PBR-ready material recipes and seamless wood texture generation."""
from __future__ import annotations
from pathlib import Path
import numpy as np
from PIL import Image
from trimesh.visual.material import PBRMaterial

P = {
 'wood':('#b88856',.83,0), 'wood_light':('#d2a574',.82,0),
 'wood_dark':('#684733',.94,0), 'wood_end':('#986741',.91,0),
 'wood_crack':('#4d382d',.96,0),'rope':('#d5b98c',.95,0),
 'rope_shadow':('#917751',.98,0),'iron':('#45555b',.58,.68),
 'iron_light':('#879a9c',.41,.72),'brass':('#c59958',.43,.74),
 'rust':('#9d5539',.91,.15),'leather':('#77503a',.85,.05),
 'charcoal':('#282b2e',.99,.02),'ember':('#ed8547',.88,.03),
 'sea_glass':('#78cad0',.19,.04),'sea_blue':('#266e81',.43,.08),
 'leaf':('#729f60',.87,0),'soil':('#46352a',.98,0),
 'fabric':('#ded6b4',.92,0),
}

def rgba(hex_color):
    h=hex_color.lstrip('#')
    return [int(h[i:i+2],16) for i in (0,2,4)] + [255]


def material(name):
    h,rough,met=P[name]
    return PBRMaterial(name=name,baseColorFactor=rgba(h),metallicFactor=float(met),roughnessFactor=float(rough),doubleSided=True,
                       emissiveFactor=[0.26,0.07,0.01] if name=='ember' else [0.,0.,0.])


def wood_maps(output: Path,seed=48,size=512):
    """Create color, roughness, normal maps for optional use in Blender/Three.js."""
    output.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(seed)
    x=np.arange(size,dtype=np.float32)/size
    X,Y=np.meshgrid(x,x)
    phase=(Y*39 + .18*np.sin(X*2*np.pi*4)+.08*np.sin(X*2*np.pi*13))
    grain=.5*np.sin(2*np.pi*phase)+.16*np.sin(2*np.pi*phase*2)
    grain+=.11*np.sin(2*np.pi*(Y*83+X*3))+.09*np.sin(2*np.pi*(Y*109-X*2))
    grain+=rng.normal(0,.028,size=(size,size))
    shade=np.clip(grain,-1,1)
    base=np.array([178,127,77],float)
    albedo=np.clip(base[None,None,:]+shade[:,:,None]*np.array([33,31,24]),0,255).astype(np.uint8)
    rough=np.uint8(np.clip(.82+shade*.055,.55,.98)*255)
    du=np.gradient(shade,axis=1)*.6;dv=np.gradient(shade,axis=0)*.6
    normal=np.stack([-du,-dv,np.ones_like(du)],axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    normal=np.uint8(np.clip(normal*.5+.5,0,1)*255)
    names=['wood_albedo.png','wood_roughness.png','wood_normal.png']
    for fname,img,mode in zip(names,[albedo,rough,normal],['RGB','L','RGB']):
        Image.fromarray(img,mode).save(output/fname,optimize=True)
    return names
