#!/usr/bin/env python3
"""RAFTBOUND Asset Kit A02 - procedural geometry with a Blender-compatible glTF output.
Run with Python + numpy + trimesh; Blender finishing project is in blender/build_scene.py.
World units: meter, Y up; foundation footprint 2 x 2m, centered at (0,0,0).
"""
from __future__ import annotations
import json, math, random
from pathlib import Path
from collections import defaultdict
import numpy as np
import trimesh
from trimesh.visual.material import PBRMaterial
from trimesh.visual import TextureVisuals

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'glb'; OUT.mkdir(exist_ok=True)
R = random.Random(8042)
PALETTE = {
    'wood_honey':('#BE8550',0.83,0.0),
    'wood_light':('#D4A46F',0.85,0.0),
    'wood_mid':('#A96D3B',0.86,0.0),
    'wood_bark':('#68452C',0.98,0.0),
    'wood_seam':('#8B5D3C',0.93,0.0),
    'wood_bleach':('#E2BB89',0.92,0.0),
    'rope':('#D5B27B',0.96,0.0),
    'rope_dark':('#8B6F4E',0.99,0.0),
    'metal':('#8C9B9D',0.48,0.72),
    'metal_edge':('#B7C8C4',0.43,0.67),
    'iron':('#465964',0.53,0.60),
    'rust':('#A86644',0.92,0.25),
    'bronze':('#D9AC5C',0.52,0.66),
    'plastic_aqua':('#73C7CF',0.39,0.03),
    'plastic_white':('#E4EFDC',0.54,0.02),
    'plastic_coral':('#E78E6B',0.56,0.02),
    'water':('#3DAFBF',0.27,0.02),
    'leaf_main':('#478D50',0.85,0.00),
    'leaf_light':('#83B660',0.84,0.00),
    'leaf_dark':('#2B7047',0.92,0.00),
    'soil':('#54402D',0.96,0.00),
    'pebble':('#817666',0.96,0.00),
    'ember':('#EB8148',0.92,0.00),
    'coal':('#393639',0.99,0.00),
    'canvas':('#E7D1AA',0.96,0.00),
}

def rgba(name):
    h = PALETTE[name][0].lstrip('#'); return [int(h[i:i+2],16) for i in (0,2,4)]+[255]

class Asset:
    def __init__(self,name):
        self.name=name; self.parts=[]
    def add(self, m, mat):
        if not isinstance(m, trimesh.Trimesh): raise TypeError(type(m))
        if len(m.faces): self.parts.append((mat,m))
        return self
    def box(self,cen,sz,mat,bevel=0):
        if bevel:
            m=chamfer_box(sz,bevel)
        else: m=trimesh.creation.box(extents=sz)
        m.apply_translation(cen);return self.add(m,mat)
    def rod(self,a,b,r,mat,sections=10,r1=None):
        self.add(rod_mesh(a,b,r,sections,r1),mat);return self
    def ball(self,cen,sz,mat,subdiv=1):
        m=trimesh.creation.icosphere(subdivisions=subdiv)
        m.apply_scale(sz);m.apply_translation(cen)
        return self.add(m,mat)
    def tube_loop(self,pts,r,mat,segments=8):
        for a,b in zip(pts,pts[1:]): self.rod(a,b,r,mat,segments)
        return self
    def export(self):
        grouped=defaultdict(list)
        for mat,geo in self.parts:grouped[mat].append(geo)
        scene=trimesh.Scene()
        for mat,meshes in grouped.items():
            big=trimesh.util.concatenate(meshes)
            pbr=PBRMaterial(name=mat,baseColorFactor=rgba(mat),metallicFactor=PALETTE[mat][2],roughnessFactor=PALETTE[mat][1],doubleSided=True)
            big.visual=TextureVisuals(material=pbr)
            scene.add_geometry(big,geom_name=f'{self.name}_{mat}',node_name=f'{self.name}_{mat}')
        path=OUT/f'{self.name}.glb';scene.export(path)
        total_tri=sum(len(g.faces) for g in scene.geometry.values())
        loaded=trimesh.load(path,force='scene')
        b=loaded.bounds
        return {'id':self.name,'file':f'glb/{self.name}.glb','triangles':total_tri,'materials':len(grouped),'parts_before_batch':len(self.parts),'bounds_m':[[round(float(v),3) for v in row] for row in b],'size_kb':round(path.stat().st_size/1024,1)}

def chamfer_box(sz,b):
    w,h,d=sz;b=min(b,w*.13,h*.3,d*.13)
    def perimeter(x,z,c):
        return [(-x/2+c,-z/2), (x/2-c,-z/2),(x/2,-z/2+c),(x/2,z/2-c),
                (x/2-c,z/2),(-x/2+c,z/2),(-x/2,z/2-c),(-x/2,-z/2+c)]
    coords=[]
    for y,dd in ((-h/2,b),( -h/2+b,0),(h/2-b,0),(h/2,b)):
        for x,z in perimeter(w-2*dd,d-2*dd,b if dd==0 else max(.01,b*.25)):
            coords.append([x,y,z])
    coords.extend([[0,-h/2,0],[0,h/2,0]])
    faces=[]
    for j in range(3):
        for i in range(8):
            a=j*8+i; b1=j*8+(i+1)%8; c=(j+1)*8+i; d1=(j+1)*8+(i+1)%8
            faces.extend([[a,b1,c],[b1,d1,c]])
    for i in range(8):
        faces.append([32,(i+1)%8,i]); faces.append([33,24+i,24+(i+1)%8])
    m=trimesh.Trimesh(vertices=coords,faces=faces,process=True)
    trimesh.repair.fix_normals(m);return m

def rod_mesh(a,b,r,sections=10,r1=None):
    a=np.array(a,float);b=np.array(b,float); v=b-a;L=np.linalg.norm(v)
    if L<1e-7: return trimesh.creation.icosphere(radius=r)
    r1=r if r1 is None else r1
    if abs(r1-r)>1e-6:
        verts=[]
        for z,rad in ((0,r),(L,r1)):
            for i in range(sections):
                ang=2*math.pi*i/sections
                verts.append([math.cos(ang)*rad,math.sin(ang)*rad,z])
        faces=[]
        for i in range(sections):
            j=(i+1)%sections;faces.extend([[i,j,sections+j],[i,sections+j,sections+i]])
        verts += [[0,0,0],[0,0,L]]
        for i in range(sections):
            j=(i+1)%sections
            faces.extend([[sections*2,j,i],[sections*2+1,sections+i,sections+j]])
        m=trimesh.Trimesh(vertices=verts,faces=faces,process=True)
    else: m=trimesh.creation.cylinder(radius=r,height=L,sections=sections)
    # cylinder centered on its axis while tapered generator starts at z=0
    start = (r1==r)
    rot=trimesh.geometry.align_vectors([0,0,1],v/L)
    m.apply_transform(rot)
    m.apply_translation((a+b)*.5 if start else a)
    return m

def band(a,center,dims,axis,mat):
    # Decorative wrap/collar at beams, axis X or Z
    c=np.array(center)
    if axis=='z':
        a.box(c+[-dims[0]/2,0,0],(.035,dims[1],dims[2]),mat)
        a.box(c+[ dims[0]/2,0,0],(.035,dims[1],dims[2]),mat)
    else:
        a.box(c+[0,0,-dims[2]/2],(dims[0],dims[1],.035),mat)
        a.box(c+[0,0, dims[2]/2],(dims[0],dims[1],.035),mat)


def timber_plank(a,cx,cy,cz,length=1.88,width=.3,thick=.12,orientation='z',style=0):
    palette=['wood_honey','wood_light','wood_mid','wood_bleach']
    x,z=(width,length) if orientation=='z' else (length,width)
    a.box((cx,cy,cz),(x,thick,z),palette[style%4],bevel=.025)
    # Grain seams and nail marks are geometry rather than texture to keep them visible at prototype distance.
    for side in (-1,1):
        if orientation=='z':
            xx=cx+side*(width*.32)
            for p in (-.62,.58):
                a.rod((xx,cy+thick/2+.003,cz+p),(xx+.025,cy+thick/2+.003,cz+p+.14),.008,'wood_seam',6)
        else:
            zz=cz+side*(width*.32)
            for p in (-.62,.58):
                a.rod((cx+p,cy+thick/2+.003,zz),(cx+p+.14,cy+thick/2+.003,zz+.02),.008,'wood_seam',6)

def raft_tile():
    """A02 - weathered six-board raft module, authored around 2 m grid pivot."""
    a=Asset('foundation_2m')
    # Staggered, hefty cross beams visible underneath the silhouette.
    for z in (-.65,.64):
        a.box((0,-.17,z),(1.97,.20,.23),'wood_bark',.037)
        a.box((0,-.065,z),(1.89,.025,.19),'wood_seam',.009)
    # Individual planks vary in height, taper and patina; readable from gameplay height.
    for i in range(6):
        x=(i-2.5)*.327
        height=(-.013,.004,-.008,.014,-.017,.008)[i]
        variation=(.009,-.020,.007,.015,-.018,.013)[i]
        timber_plank(a,x,height,variation,1.91,.301,.135,'z',i+1)
        # Weathered grain scars along the top of selected boards.
        for j in range(2):
            z=(-.47,.38)[j]+((i%3)-1)*.12
            a.rod((x-.075,height+.074,z-.21),(x-.062,height+.075,z+.17),.006,'wood_seam',6)
        # Two discrete iron nail heads at both beam intersections.
        for z in (-.62,.61):
            for dx in (-.09,.09):
                a.ball((x+dx,height+.071,z),(.017,.007,.018),'iron',1)
    # Exterior chafing ropes tie the planks to submerged beams.
    for x in (-.825,.825):
        for z in (-.67,.65):
            a.rod((x,-.255,z-.15),(x,-.17,z+.15),.032,'rope',8)
            a.rod((x-.09,-.06,z),(x+.085,-.04,z),.023,'rope_dark',8)
            a.ball((x,-.038,z),(.038,.026,.041),'rope',1)
    # Dark caps on timber ends improve outline in the moving sea.
    for z in (-.962,.959):
        for i in (0,2,4):
            x=(i-2.5)*.327
            a.box((x,-.008,z),(.278,.045,.015),'wood_bark',.004)
    return a

def driftwood():
    a=Asset('driftwood_plank')
    timber_plank(a,0,.01,0,1.35,.34,.145,'z',2)
    for i in (-1,1):a.rod((-.14,.093,i*.5),(.13,.093,i*.42),.012,'wood_seam',7)
    return a

def plastic_bottle():
    a=Asset('plastic_bottle')
    # Bottle lies on its side (X axis), somewhat dimpled shoulder + bands.
    a.rod((-.40,0,0),(.28,0,0),.165,'plastic_aqua',14)
    a.ball((-.36,0,0),(.08,.155,.155),'plastic_aqua',1)
    a.rod((.27,0,0),(.41,0,0),.084,'plastic_aqua',12)
    a.rod((.41,0,0),(.51,0,0),.102,'plastic_coral',12)
    for x in (-.19,-.13,-.07):a.rod((x,0,0),(x+.015,0,0),.17,'plastic_white',14)
    for x in (-.34,.23):a.rod((x,0,0),(x+.016,0,0),.17,'plastic_white',14)
    return a

def floating_barrel():
    a=Asset('salvage_barrel')
    a.rod((0,-.46,0),(0,.46,0),.335,'wood_mid',16)
    for ang in np.linspace(0,2*math.pi,12,endpoint=False):
        x,z=.34*math.cos(ang),.34*math.sin(ang)
        a.rod((x,-.425,z),(x,.425,z),.04,'wood_honey',6)
    for y in (-.33,.32):
        ring=[(.36*math.cos(t),y,.36*math.sin(t)) for t in np.linspace(0,2*math.pi,25)]
        a.tube_loop(ring,.035,'iron',8)
    a.rod((0,.465,0),(0,.485,0),.288,'wood_bark',14)
    a.ball((0,.50,0),(.065,.013,.065),'bronze',1)
    return a

def plank_rope_bundle():
    a=Asset('plank_bundle')
    for i in range(3):timber_plank(a,(i-1)*.09,i*.075-.12,0,1.32,.28,.1,'z',i)
    for z in (-.39,.39):
        a.box((0, .086, z),(.52,.075,.075),'rope',.015)
    return a

def palm_leaf():
    a=Asset('palm_leaf')
    a.rod((0,-.03,-.86),(0,.08,.87),.026,'leaf_dark',8,r1=.008)
    for i in range(12):
        t=i/12
        zz=-.72+i*.13
        width=.49*math.sin(math.pi*(t*.86+.09))
        for side in (-1,1):
            points=[]
            for u in (0,.30,.67,1):
                xx=side*width*u
                yy=.07+.10*math.sin(u*math.pi)-.05*u
                zc=zz+.15*u
                hw=.075*math.sin(u*math.pi)**.7*(1-.45*t)
                points.extend([[xx,yy,zc-hw],[xx,yy,zc+hw]])
            faces=[]
            for j in range(3):
                base=2*j;faces.extend([[base,base+1,base+2],[base+1,base+3,base+2]])
            mesh=trimesh.Trimesh(vertices=points,faces=faces,process=False)
            a.add(mesh,'leaf_main' if (i+side)%3 else 'leaf_light')
            a.rod((0,.07,zz),(side*width*.9,.04,zz+.14),.008,'leaf_dark',6)
    return a

def net_tool():
    """A02 - reinforced salvaging scoop with braided grip and diamond mesh."""
    a=Asset('salvage_net_tool')
    # Ergonomic tapered hardwood shaft, darker wrapped grip, bronze ferrule.
    a.rod((0,.025,0),(0,1.29,0),.047,'wood_honey',12,r1=.034)
    for y in np.arange(.11,.35,.05):
        # Lightweight binding stripes remain legible during animation.
        a.rod((0,y,0),(0,y+.024,0),.054,'rope_dark',9)
    a.rod((0,1.19,0),(0,1.43,0),.052,'iron',12)
    a.rod((0,1.27,0),(0,1.30,0),.063,'bronze',10)
    # Oval hoop with reinforcement at neck and pronounced side rim.
    center=np.array([0,1.45,.24]); radius=.375
    hoop=[center+np.array([radius*math.cos(t),0,radius*math.sin(t)]) for t in np.linspace(0,2*math.pi,41)]
    a.tube_loop(hoop,.029,'metal_edge',10)
    for side in (-1,1):
        a.rod((0,1.39,0),(side*.15,1.45,.10),.025,'iron',8)
    a.ball((0,1.46,.23),(.055,.026,.050),'bronze',1)
    # Sixteen tapered cords with lateral rings: recognisable net rather than plain hoop.
    for i in range(16):
        theta=i*math.tau/16
        ux,uz=math.cos(theta),math.sin(theta)
        ringpoint=(radius*ux,1.45,center[2]+radius*uz)
        middle=(.245*ux,1.19,center[2]+.245*uz)
        tip=(.075*ux,1.005,center[2]+.075*uz)
        a.rod(ringpoint,middle,.0085,'rope',6)
        a.rod(middle,tip,.0075,'rope',6)
    # Weft ties, offset for a diamond weave illusion; keep tiny alpha-free meshes.
    for y,r,offset in ((1.35,.325,0),(1.25,.277,.06),(1.14,.200,0),(1.065,.133,.05)):
        points=[[r*math.cos(i*math.tau/20+offset),y,center[2]+r*math.sin(i*math.tau/20+offset)] for i in range(21)]
        a.tube_loop(points,.0075,'rope_dark' if y==1.35 else 'rope',6)
    a.ball((0,.988,center[2]),(.052,.034,.052),'rope',1)
    return a

def grill():
    a=Asset('compact_grill')
    for x in (-.49,.49):
        for z in (-.42,.42):
            a.rod((x,.03,z),(x,.72,z),.074,'wood_mid',9)
            a.rod((x,.13,z),(x,.25,z),.08,'rope',8)
    for z in (-.42,.42):a.box((0,.36,z),(1.05,.10,.11),'wood_bark',.018)
    a.box((0,.71,0),(1.21,.18,1.05),'iron',.04)
    a.box((0,.825,0),(1.00,.032,.83),'coal')
    for x in np.linspace(-.45,.45,8):a.rod((x,.96,-.45),(x,.96,.45),.022,'metal_edge',8)
    for z in (-.48,.48):a.rod((-.57,.96,z),(.57,.96,z),.038,'metal',8)
    for x,z in ((-.24,-.20),(.15,.06),(.1,-.27)):
        a.ball((x,.86,z),(.11,.06,.09),'ember',1)
    # folded grate handles, dark wooden grip at the end
    a.rod((.58,.92,0),(.79,.95,0),.055,'iron',10)
    a.rod((.75,.95,0),(.92,.95,0),.073,'wood_honey',10)
    return a

def purifier():
    a=Asset('solar_purifier')
    for x in (-.52,.52):
        for z in (-.4,.4):a.rod((x,.03,z),(x,.82,z),.07,'wood_honey',10)
    a.box((0,.56,0),(1.20,.115,1.04),'wood_bark',.026)
    for x in (-.45,.45):a.box((x,.92,0),(.12,.23,.95),'wood_mid',.018)
    a.box((0,.78,0),(.96,.18,.80),'metal',.06)
    a.box((0,.893,0),(.72,.022,.55),'water',.010)
    # angled shade canopy on two legs
    a.rod((-.54,1.01,-.42),(-.54,1.62,-.42),.035,'iron',8)
    a.rod(( .54,1.01,-.42),( .54,1.62,-.42),.035,'iron',8)
    top=trimesh.creation.box(extents=(1.37,.075,.95))
    top.apply_transform(trimesh.transformations.rotation_matrix(math.radians(18),[1,0,0]))
    top.apply_translation([0,1.60,-.06]);a.add(top,'canvas')
    # pipe water to collecting jug
    a.rod((.48,.8,.1),(.85,.7,.1),.027,'metal_edge',10)
    a.rod((.85,.70,.1),(.85,.47,.1),.027,'metal_edge',10)
    a.rod((.85,.10,.15),(.85,.48,.15),.17,'plastic_aqua',12)
    a.rod((.85,.45,.15),(.85,.53,.15),.078,'plastic_white',10)
    return a

def sprout(a,x,z,y=.88,variant=0):
    top=np.array([x+.04,.0,z]);root=np.array([x, y,z]);
    a.rod(root,root+[.04,.36,0],.023,'leaf_dark',8,r1=.013)
    for side in (-1,1):
        start=root+np.array([.025,.18,0]);tip=start+np.array([side*.25,.13,0.07*variant-.05])
        mid=(start+tip)*.5+np.array([0,.055,0])
        a.rod(start,mid,.053,'leaf_main' if side==1 else 'leaf_light',8,r1=.027)
        a.rod(mid,tip,.038,'leaf_main' if side==1 else 'leaf_light',8,r1=.004)

def planter():
    a=Asset('planter_box')
    for x in (-.59,.59):
        for z in (-.38,.38):a.rod((x,.03,z),(x,.63,z),.061,'wood_bark',8)
    a.box((0,.56,0),(1.44,.37,.98),'wood_mid',.045)
    a.box((0,.78,0),(1.23,.026,.79),'soil',.015)
    for z in (-.5,.5):a.box((0,.79,z),(1.50,.11,.12),'wood_light',.02)
    for x in (-.70,.70):a.box((x,.79,0),(.12,.11,.99),'wood_light',.02)
    for x in (-.4,0,.4):sprout(a,x,R.uniform(-.12,.12),.8,int((x+.4)*10))
    for x,z in ((-.35,.15),(.33,-.22),(.07,.15)):
        a.ball((x,.805,z),(.038,.019,.036),'pebble',1)
    return a

def chest():
    a=Asset('storage_chest')
    a.box((0,.49,0),(1.25,.74,.83),'wood_mid',.065)
    for z in (-.41,.41):a.box((0,.5,z),(1.28,.73,.062),'wood_honey',.023)
    a.box((0,.91,0),(1.33,.17,.91),'wood_honey',.045)
    for x in (-.46,.46):
        a.box((x,.54,.438),(.09,.80,.040),'iron',.014)
        a.box((x,.54,-.438),(.09,.80,.040),'iron',.014)
    a.box((0,.78,.47),(.16,.22,.06),'bronze',.018)
    a.ball((0,.77,.51),(.033,.03,.02),'iron',1)
    for x in (-.54,.54):
        for z in (-.38,.38):a.ball((x,.95,z),(.021,.02,.02),'iron',1)
    return a

def buoy():
    a=Asset('buoy_marker')
    a.rod((0,-.25,0),(0,.35,0),.20,'plastic_coral',12)
    a.rod((0,-.02,0),(0,.085,0),.215,'plastic_white',12)
    a.rod((0,.35,0),(0,.48,0),.10,'metal_edge',10)
    loop=[[.14*math.cos(t),.52,.14*math.sin(t)] for t in np.linspace(0,math.tau,17)]
    a.tube_loop(loop,.022,'rope',8)
    return a

ASSETS=[raft_tile,net_tool,driftwood,plastic_bottle,palm_leaf,plank_rope_bundle,floating_barrel,grill,purifier,planter,chest,buoy]
DESCRIPTIONS={
 'foundation_2m':('building','Sàn bè tiêu chuẩn, snap ô lưới 2 m; pivot tại tâm bề mặt'),
 'salvage_net_tool':('equipment','Vợt cán gỗ, vành kim loại và lưới dây'),
 'driftwood_plank':('resource','Tấm gỗ trôi đơn'),
 'plastic_bottle':('resource','Chai nhựa rỗng trôi nổi'),
 'palm_leaf':('resource','Lá cọ trôi nổi'),
 'plank_bundle':('resource','Bó gỗ buộc dây'),
 'salvage_barrel':('resource','Thùng gỗ tài nguyên hiếm'),
 'compact_grill':('craft_station','Bếp nướng có vỉ sắt và than'),
 'solar_purifier':('craft_station','Máy lọc nước cơ bản có tấm che, khay và bình hứng'),
 'planter_box':('craft_station','Khay trồng cây với cây non'),
 'storage_chest':('storage','Rương chứa đồ'),
 'buoy_marker':('decoration','Phao đánh dấu'),
}

def run():
    results=[]
    for fun in ASSETS:
        asset=fun(); rec=asset.export();rec['category'],rec['description_vi']=DESCRIPTIONS[asset.name]
        rec['unit']='meter';rec['up']='Y';rec['authoring']='procedural mesh + Blender finishing script'
        results.append(rec)
        print(rec['id'],f"{rec['triangles']} tris, {rec['size_kb']} KB")
    data={'pack':'RAFTBOUND Ocean Survival A02','version':'0.2.0','tile_size_m':2.0,'unit':'meter','up_axis':'Y','forward_axis':'-Z','style':'stylized semi-realistic with warm timber and saturated ocean colors','assets':results}
    (BASE/'asset_manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    return results
if __name__=='__main__':run()
