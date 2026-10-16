#!/usr/bin/env python3
"""Deterministic tileable timber PBR texture maps, authored as production inputs for Blender.
Maps: sRGB albedo; linear roughness and tangent-space normal; 512x512 repeatable.
"""
import numpy as np
from PIL import Image
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'textures';P.mkdir(exist_ok=True)
N=512
u,v=np.meshgrid(np.arange(N,dtype=np.float32)/N,np.arange(N,dtype=np.float32)/N)
rng=np.random.default_rng(51231)
# Periodic ridged bands with hand-crafted curved variations (periodic on both axes).
wave=v*24+ .20*np.sin(2*np.pi*u*3)+.11*np.sin(2*np.pi*u*11)+.12*np.cos(2*np.pi*v*4)
ring=np.sin(2*np.pi*wave)+.34*np.sin(2*np.pi*wave*3)
long=np.sin(2*np.pi*u*2+np.sin(2*np.pi*v*3))
fractal=(np.sin(2*np.pi*v*83)*.17+np.sin(2*np.pi*v*147)*.08+np.sin(2*np.pi*u*27+2*np.pi*v*5)*.09)
height=.57+ring*.09+long*.045+fractal*.06
height=np.clip(height,0,1)
# Bleached warm timber; dark annual rings and lighter wear.
p=height-.54
color=np.empty((N,N,3),dtype=np.float32)
for k,(center,gain) in enumerate([(188,77),(135,65),(84,39)]):
 color[...,k]=center+gain*p+np.sin(2*np.pi*u*5+2*np.pi*v*9)*2.0
color=np.clip(color,0,255).astype('uint8')
rough=np.clip(0.79+ring*.045+.028*np.sin(2*np.pi*u*7)+fractal*.04,.58,.98)
# Periodic derivatives ensure smooth texture tiling.
hx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*5.2
hy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*5.2
normal=np.stack((-hx,-hy,np.ones_like(height)),axis=-1)
normal/=np.linalg.norm(normal,axis=2,keepdims=True)
normal=np.clip((normal*.5+.5)*255,0,255).astype('uint8')
Image.fromarray(color,'RGB').save(P/'wood_basecolor.png',optimize=True)
Image.fromarray((rough*255).astype('uint8'),'L').save(P/'wood_roughness.png',optimize=True)
Image.fromarray(normal,'RGB').save(P/'wood_normal.png',optimize=True)
Image.fromarray((height*255).astype('uint8'),'L').save(P/'wood_height.png',optimize=True)
print('Generated 4 tileable PBR map files:',P)
