"""Deterministic, art-directed procedural game assets. Right handed, Y-up, meters."""
from __future__ import annotations
from dataclasses import dataclass,field
from pathlib import Path
from collections import defaultdict
import numpy as np
import trimesh
from trimesh.visual import TextureVisuals
from .geometry import chamfer_box,rod,ring,rope_line,bowl,leaf
from .materials import material

@dataclass
class Builder:
    name: str
    parts: list = field(default_factory=list)
    def add(self,mat,mesh):
        if not isinstance(mesh,trimesh.Trimesh) or not len(mesh.faces): raise ValueError('Empty/nonmesh')
        self.parts.append((mat,mesh));return self
    def box(self,mat,center,size,bevel=.01):return self.add(mat,chamfer_box(size,bevel,center))
    def rod(self,mat,p,q,r=.018,segments=9,**kwargs):return self.add(mat,rod(p,q,r,segments,**kwargs))
    def loop(self,mat,center,r=.2,tube=.015,normal=(0,1,0),n=38):return self.add(mat,ring(center,r,tube,normal,n))
    def rope(self,points,rad=.013,mat='rope'):
        for m in rope_line(points,rad):self.add(mat,m)
        return self
    def scene(self):
        groups=defaultdict(list)
        for mat,geo in self.parts:groups[mat].append(geo)
        out=trimesh.Scene()
        for mat,geos in groups.items():
            combined=trimesh.util.concatenate(geos)
            combined.visual=TextureVisuals(material=material(mat))
            out.add_geometry(combined,geom_name=f'{self.name}_{mat}',node_name=f'{self.name}_{mat}')
        return out


def raft_tile(config):
    """Tile is 2x2 meters, raft walk surface near y=.08."""
    rng=np.random.default_rng(int(config.get('seed',42)))
    n=int(config.get('planks',7)); assert 4<=n<=12
    weather=float(config.get('weathering',.5));assert 0<=weather<=1
    detail=int(config.get('detail',2));assert 0<=detail<=3
    b=Builder('foundation_2m_art')
    # structural beams and realistic overhang below walking surface
    for z in [-.66,.66]:
        b.box('wood_dark',(0,-.18,z),(2.04,.24,.22),.038)
        b.box('wood_end',(0,-.325,z),(2.08,.035,.24),.008)
    widths=rng.uniform(.8,1.2,n);widths=widths/widths.sum()*1.98
    x=-.99
    for i,w in enumerate(widths):
        cx=x+w/2; x+=w
        shrink=rng.uniform(0,.045)*(weather+.15)
        dz=rng.uniform(-.045,.045)*(weather+.3)
        mat='wood_light' if i%4==0 else 'wood' if i%3!=0 else 'wood_end'
        b.box(mat,(cx,.004+dz/8,0),(w-.012,.145,2.04-shrink),min(.025,w/8))
        # endgrain plugs, grain dark streaks etched from both board edges
        if detail>0:
            for j in range(2):
                xx=cx+(j-.5)*w*.32
                z1=rng.uniform(-.85,-.2)
                z2=min(.96,z1+rng.uniform(.4,.9))
                b.rod('wood_end',(xx,.085,z1),(xx+.012,.085,z2),r=.0028,segments=6)
        if detail>1:
            for z in [-.69,.66]:
                b.add('iron',chamfer_box((.046,.012,.046),.008,(cx,.092,z)))
                b.add('wood_crack',chamfer_box((.012,.003,.012),.002,(cx,.099,z)))
        if weather>.35 and detail>1 and i%2==0:
            # short split near end (visual marking, not false cracks through the mesh)
            z=.95-rng.uniform(.02,.14)
            b.rod('wood_crack',(cx-w*.23,.087,z),(cx-w*.13,.087,z-.16*weather),.004,segments=6)
    for z in [-.68,.68]:
        for x in [-.8,.8]:
            # restrained thick rope wraps across beam, not bright diagonal lines across whole floor
            pts=[(x-.07,.105,z-.105),(x+.045,.108,z-.102),(x+.074,-.20,z-.10),(x+.015,-.298,z+.125),(x-.06,-.20,z+.122)]
            b.rope(pts,.016)
    return b


def storage_chest(config):
    rng=np.random.default_rng(int(config.get('seed',42)))
    detail=int(config.get('detail',2));assert 0<=detail<=3
    b=Builder('storage_chest_art')
    # sturdy raised footing, 1.05m long x .62m deep x .78m high
    for x in (-.42,.42):
        for z in (-.23,.23):b.box('wood_dark',(x,.06,z),(.13,.13,.14),.019)
    b.box('wood_dark',(0,.34,0),(1.04,.49,.62),.035)
    for side in (-1,1):
        for idx in range(3):
            b.box('wood' if idx!=1 else 'wood_light',(0,.185+idx*.146,side*.323),(.99,.133,.055),.019)
            b.box('wood_end',(side*.53,.185+idx*.146,0),(.055,.133,.61),.018)
    for x in (-.35,.35):
        b.box('wood_end',(x,.34,-.337),(.024,.52,.014),.004)
        b.box('wood_end',(x,.34,.337),(.024,.52,.014),.004)
    # arched lid, wood slats are individually pitched on a gentle circular arc
    n=9
    for i in range(n):
        z=-.31+(i+.5)*.62/n
        y=.607+.12*(1-(z/.31)**2)
        mat='wood_light' if i in (1,6) else 'wood'
        b.box(mat,(0,y,z),(1.06,.09,.62/n+.007),.012)
    # metal bands wrap the arched lid on two x coordinates
    for x in (-.365,.365):
        for i in range(9):
            z=-.32+(i+.5)*.64/9
            y=.668+.12*(1-(z/.32)**2)
            b.box('iron',(x,y,z),(.06,.014,.076),.004)
        for z in (-.333,.333):b.box('iron',(x,.36,z),(.068,.47,.02),.008)
        for y in (.22,.43,.55):
            for z in (-.352,.352):b.add('brass',chamfer_box((.032,.032,.01),.004,(x,y,z)))
    # central front lock, latch, rivet pattern
    b.box('iron',(0,.47,-.37),(.20,.23,.037),.019)
    b.box('brass',(0,.474,-.391),(.135,.14,.013),.012)
    b.loop('iron',(0,.486,-.404),.033,.008,normal=(0,0,1),n=22)
    b.box('charcoal',(0,.474,-.417),(.020,.055,.006),.005)
    # sturdy side handles
    for s in (-1,1):
        b.loop('iron',(s*.557,.35,0),.095,.014,normal=(1,0,0),n=24)
        b.box('brass',(s*.541,.42,0),(.035,.045,.2),.01)
    if detail>1:
        for s in (-1,1):
            for z in (-.27,.27):
                for y in (.2,.35,.49):
                    b.add('brass',chamfer_box((.014,.028,.028),.006,(s*.552,y,z)))
        for x in (-.47,.47):
            for z in (-.21,.21):b.add('iron',chamfer_box((.07,.024,.08),.012,(x,.743,z)))
    if detail>2:
        for i in range(5):
            x=rng.uniform(-.38,.38)
            b.rod('wood_end',(x,.185,-.355),(x+.03,.30,-.355),.0035)
    return b


def compact_grill(config):
    rng=np.random.default_rng(int(config.get('seed',42)))
    detail=int(config.get('detail',2));assert 0<=detail<=3
    b=Builder('compact_grill_art')
    # 4 tapered angled iron legs plus reinforcing shelf
    for x in (-.34,.34):
        for z in (-.30,.30):
            b.rod('iron',(x, .57,z),(x*1.18,.04,z*1.17),.039,segments=10,radius_end=.032)
            b.box('iron_light',(x*1.18,.03,z*1.17),(.135,.056,.13),.013)
    b.box('iron',(0,.265,0),(.65,.037,.59),.025)
    for x in (-.25,.25):b.box('iron_light',(x,.285,0),(.022,.018,.55),.005)
    # open brazier basin (not a sealed opaque cylinder)
    b.add('iron',bowl((0,.55,0),bottom_radius=.32,top_radius=.45,height=.24,thick=.025,segments=40))
    b.loop('iron_light',(0,.795,0),.445,.022,(0,1,0),40)
    # charcoal visible below grill grate
    for i in range(17):
        x,z=rng.uniform(-.25,.25,size=2)
        if x*x+z*z>.07:continue
        y=.62+rng.uniform(.01,.07)
        b.add('ember' if i%4==0 else 'charcoal',chamfer_box((rng.uniform(.07,.13),rng.uniform(.045,.09),rng.uniform(.05,.1)),.012,(x,y,z)))
    # grill rods sit just above rim
    for z in np.arange(-.33,.335,.083):
        xx=float(np.sqrt(max(.05,.405*.405-z*z)))
        b.rod('iron_light',(-xx,.834,float(z)),(xx,.834,float(z)),.012,segments=9)
    for x in (-.32,.32):b.rod('iron_light',(x,.845,-.26),(x,.845,.26),.012,segments=8)
    # handles mounted in side hooks
    for s in (-1,1):
        b.rod('iron_light',(s*.433,.735,-.13),(s*.55,.775,-.13),.017)
        b.rod('iron_light',(s*.433,.735,.13),(s*.55,.775,.13),.017)
        b.rod('wood_dark',(s*.55,.78,-.13),(s*.55,.78,.13),.036,segments=12)
    # bolts, air vents and decorative straps
    if detail>0:
        for ang in np.linspace(0,2*np.pi,12,endpoint=False):
            x,z=.405*np.cos(ang),.405*np.sin(ang)
            b.add('rust',chamfer_box((.034,.027,.034),.007,(x,.63,z)))
        for z in (-.2,.2):
            b.add('brass',chamfer_box((.065,.055,.015),.007,(0,.38,z)))
    if detail>1:
        for x in (-.25,.25):
            for z in (-.21,.21):
                b.add('brass',chamfer_box((.028,.029,.015),.006,(x,.30,z)))
    return b

BUILDERS={'raft_tile':raft_tile,'storage_chest':storage_chest,'compact_grill':compact_grill}

def build(recipe:dict):
    kind=recipe.get('type')
    if kind not in BUILDERS:raise ValueError(f'Unknown model type: {kind!r}. Valid: {list(BUILDERS)}')
    return BUILDERS[kind](recipe)
