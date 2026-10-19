"""RAFTFORGE — independent stylized sailor/survivor clothes, no body-shell crop.

Blender builtin bpy/bmesh only, offline. Parametric lofted T-shirt with sleeves,
baggy cargo shorts, canvas shoes, visible short hair and one utility pouch.
Each garment is a NEW mesh; copy nearest four body skin influences by spatial
weighted interpolation onto original 65-bone armature. Do not use paid models.
"""
from __future__ import annotations
import json
import math
import statistics
import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree


def material(name, rgba, roughness=.9):
    mat=bpy.data.materials.new(name)
    mat.diffuse_color=(*rgba,1.)
    mat.use_nodes=True
    bsdf=mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value=(*rgba,1.)
        bsdf.inputs['Roughness'].default_value=roughness
        bsdf.inputs['Metallic'].default_value=0.
    return mat


def body_info(body,arm):
    world=[body.matrix_world@p.co for p in body.data.vertices]
    lo=min(p.z for p in world)
    hi=max(p.z for p in world)
    h=hi-lo
    core=[p for p in world if .52< (p.z-lo)/h <.7 and abs(p.x)<.30]
    if not core:raise RuntimeError('Cannot establish torso landmarks')
    center_y=statistics.median(p.y for p in core)
    bx=[arm.matrix_world@arm.data.bones[n].head_local for n in ('upperarm_l','upperarm_r')]
    return lo,hi,h,center_y,bx


def loft(rings,segments=24):
    """Closed-around circumference, OPEN at neck/hem to avoid a solid fake box."""
    verts=[];faces=[]
    for xc,yc,zc,rx,ry in rings:
        for j in range(segments):
            a=math.tau*j/segments
            verts.append((xc+rx*math.cos(a),yc+ry*math.sin(a),zc))
    for i in range(len(rings)-1):
        for j in range(segments):
            a=i*segments+j;b=i*segments+(j+1)%segments
            c=(i+1)*segments+(j+1)%segments;d=(i+1)*segments+j
            faces.append((a,b,c,d))
    return verts,faces


def sleeve(a,b,rings=(.107,.110,.101),segments=20):
    """Independent sleeve tube along artist-rigged upper arm."""
    a=Vector(a); b=Vector(b)
    axis=b-a
    if axis.length<.08:raise RuntimeError('Upper arm landmark degenerate')
    axis.normalize()
    u=axis.cross(Vector((0,0,1))).normalized()
    v=axis.cross(u).normalized()
    verts=[];faces=[]
    for f,r in zip((0,.12,.26),rings):
        pos=a+axis*f
        for j in range(segments):
            ang=j*math.tau/segments
            p=pos+u*math.cos(ang)*r+v*math.sin(ang)*r
            verts.append(tuple(p))
    for k in range(2):
        for j in range(segments):
            i=k*segments+j;ii=k*segments+(j+1)%segments
            faces.append((i,ii,(k+1)*segments+(j+1)%segments,(k+1)*segments+j))
    return verts,faces


def combine(*groups):
    vertices=[];faces=[]
    for xyz,polys in groups:
        shift=len(vertices);vertices+=xyz
        faces +=[tuple(shift+i for i in polygon) for polygon in polys]
    return vertices,faces


def interpolate_weights(source,output,source_tree):
    """Weighted nearest-surface vertex transfer (not copying source mesh geometry).

    Four-neighbor interpolation preserves enough shoulder/hip bends for the
    generated separate meshes. Animation pose/penetration QA remains mandatory.
    """
    groups={g.index:g.name for g in source.vertex_groups}
    dst={g.name:g for g in output.vertex_groups}
    world=output.matrix_world
    missing=set(groups.values())-set(dst)
    if missing:raise RuntimeError('Weight transfer lost groups '+repr(missing))
    assigned=0
    for vertex in output.data.vertices:
        nearby=source_tree.find_n(world@vertex.co,4)
        channels={}
        for _point,index,distance in nearby:
            scale=1./max(distance,.003)**2
            for g in source.data.vertices[index].groups:
                name=groups[g.group]
                channels[name]=channels.get(name,0.)+g.weight*scale
        if not channels:raise RuntimeError('Body mesh missing weights near garment')
        best=sorted(channels.items(),key=lambda item:item[1],reverse=True)[:4]
        total=sum(v for _,v in best)
        if total<=0:raise RuntimeError('Invalid weight sum')
        for name,value in best:
            dst[name].add([vertex.index],value/total,'REPLACE')
        assigned+=1
    return assigned


def make_mesh(body,tree,name,world_vertices,polys,mat):
    mesh=bpy.data.meshes.new(name+'_Topology')
    inv=body.matrix_world.inverted()
    mesh.from_pydata([tuple(inv@Vector(v)) for v in world_vertices],[],polys)
    mesh.update()
    if not mesh.polygons:raise RuntimeError(name+' has no polygons')
    obj=body.copy()
    obj.data=mesh
    obj.name=name
    bpy.context.collection.objects.link(obj)
    obj.matrix_world=body.matrix_world.copy()
    mesh.materials.clear();mesh.materials.append(mat)
    n=interpolate_weights(body,obj,tree)
    # Face-culling-safe normals for the separate garment topology.
    # No material-replacement trick or cosmetic overlay on the body.
    for poly in mesh.polygons:
        poly.use_smooth=True
    if not any(mod.type=='ARMATURE' for mod in obj.modifiers):
        raise RuntimeError(name+' is not deformable')
    return obj,{'name':name,'vertices':n,'faces':len(mesh.polygons),'skinned':True}


def accessory_box(body,tree,name,center,size,mat,bevel=.015):
    """A tiny low-poly cargo pouch, never a substitute for actual clothing."""
    cx,cy,cz=center;dx,dy,dz=size
    v=[(cx+x*dx/2,cy+y*dy/2,cz+z*dz/2)
       for x,y,z in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                      (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    f=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
    return make_mesh(body,tree,name,v,f,mat)


def produce(body,arm,other_meshes):
    lo,hi,h,cy,shoulders=body_info(body,arm)
    x0=(shoulders[0].x+shoulders[1].x)/2.
    points=[body.matrix_world@v.co for v in body.data.vertices]
    tree=KDTree(len(points))
    for i,p in enumerate(points):tree.insert(p,i)
    tree.balance()
    palette={
        'skin':material('RB_SunlitSkin',(.68,.47,.35)),
        'shirt':material('RB_FadedOceanTshirt',(.17,.55,.62)),
        'shorts':material('RB_SandCargoShorts',(.53,.40,.28)),
        'shoes':material('RB_CanvasDeckShoes',(.21,.25,.25)),
        'hair':material('RB_ShortDarkHair',(.14,.10,.08)),
        'pouch':material('RB_SmallLeatherPouch',(.32,.20,.11)),
        'eyes':material('RB_EyesNatural',(.79,.76,.68))
    }
    body.data.materials.clear()
    body.data.materials.append(palette['skin'])
    for obj in other_meshes:
        if obj==body:continue
        if 'eye' in obj.name.lower() and 'brow' not in obj.name.lower():
            obj.data.materials.clear();obj.data.materials.append(palette['eyes'])
    results=[]
    def add(name,geometry,material_name):
        verts,faces=geometry
        obj,info=make_mesh(body,tree,name,verts,faces,palette[material_name])
        results.append(info)
        return obj

    # Bloused T-shirt: distinct body loft + attached short sleeves. The top
    # is continuous up to a neat crew neck; no bare-shoulder tube top.
    # All heights are fractions of the artist's measured 1.8m figure.
    rings=[
        (x0,cy,lo+.487*h,.180,.143),
        (x0,cy,lo+.53*h,.191,.147),
        (x0,cy,lo+.60*h,.204,.157),
        (x0,cy,lo+.70*h,.209,.159),
        (x0,cy,lo+.775*h,.215,.153),
        (x0,cy,lo+.811*h,.185,.142),
        (x0,cy,lo+.841*h,.084,.092),
    ]
    torso=loft(rings,32)
    sleeve_parts=[]
    for name in ('upperarm_l','upperarm_r'):
        bone=arm.data.bones[name]
        start=arm.matrix_world@bone.head_local
        end=arm.matrix_world@bone.tail_local
        sleeve_parts.append(sleeve(start,end))
    add('RB_TShirt',combine(torso,*sleeve_parts),'shirt')

    # Slightly roomy shorts with a distinct waist shell and TWO separate
    # cloth leg barrels to the knees. Not a duplicate of body vertices.
    waist=loft([
        (x0,cy,lo+.505*h,.164,.122),
        (x0,cy,lo+.470*h,.184,.145),
        (x0,cy,lo+.421*h,.204,.146),
        (x0,cy,lo+.380*h,.207,.142),
    ],28)
    thigh_groups=[]
    for side in (-1,1):
        cx=x0+side*.105
        thigh_groups.append(loft([
            (cx,cy,lo+.405*h,.119,.130),
            (cx,cy,lo+.352*h,.122,.131),
            (cx,cy,lo+.292*h,.121,.129),
            (cx,cy,lo+.246*h,.113,.120)
        ],20))
    add('RB_CargoShorts',combine(waist,*thigh_groups),'shorts')

    # Pair of low canvas shoes with flared sole, independent meshes. Feet
    # remain on the ground and no longer resemble bulky boots.
    for side,tag in [(-1,'L'),(1,'R')]:
        cx=x0+side*.122
        sample=[p for p in points if lo+.035*h<p.z<lo+.13*h and abs(p.x-cx)<.105]
        fy=statistics.median(p.y for p in sample) if sample else cy
        shoe=loft([
            (cx,fy-.024,lo+.012*h,.106,.157),
            (cx,fy-.022,lo+.040*h,.108,.159),
            (cx,fy-.004,lo+.085*h,.091,.122),
            (cx,fy+.005,lo+.115*h,.079,.095),
        ],24)
        add('RB_CanvasShoes_'+tag,shoe,'shoes')

    # Short side-parted hair above the eyebrows: face and eyes unobstructed.
    head_samples=[p for p in points if lo+.89*h<p.z<lo+.96*h and abs(p.x)<.24]
    hy=statistics.median(p.y for p in head_samples) if head_samples else cy
    hair=loft([
        (x0,hy,lo+.947*h,.095,.097),
        (x0,hy,lo+.967*h,.099,.100),
        (x0,hy,lo+.992*h,.086,.083),
        (x0,hy,lo+1.010*h,.045,.052),
        (x0,hy,lo+1.018*h,.008,.011),
    ],28)
    add('RB_ShortHair',hair,'hair')

    pouch_center=(x0+.190,cy+.010,lo+.445*h)
    add('RB_SmallCargoPouch',accessory_box_geometry(pouch_center,(.095,.082,.129)),'pouch')
    return results


def accessory_box_geometry(center,size):
    cx,cy,cz=center;dx,dy,dz=size
    verts=[(cx+dx*x/2,cy+dy*y/2,cz+dz*z/2) for x,y,z in
        [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
         (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    faces=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
    return verts,faces
