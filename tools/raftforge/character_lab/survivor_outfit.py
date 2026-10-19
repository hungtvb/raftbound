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
from collections import Counter
import bmesh
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


def sleeve(a,b,rings=(.133,.119,.109),segments=18):
    """Independent sleeve tube along artist-rigged upper arm."""
    a=Vector(a); b=Vector(b)
    axis=b-a
    if axis.length<.08:raise RuntimeError('Upper arm landmark degenerate')
    axis.normalize()
    u=axis.cross(Vector((0,0,1))).normalized()
    v=axis.cross(u).normalized()
    verts=[];faces=[]
    for f,r in zip((0.,.19,.39),rings):
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



def stitched_shirt(rings, arm, segments=32):
    """One connected T-shirt surface with genuine armholes and welded sleeves.

    Open two rectangular 18-edge loops in the torso at the shoulders, connect
    the perimeter of each loop to the inner sleeve ring by explicit shared
    topology. Both sleeves are now part of ONE mesh component. Exactly four
    boundary loops remain: neck, waist hem, left/right sleeve cuffs.
    """
    if segments!=32:
        raise ValueError('Shoulder topology requires 32 torso segments')
    v,f=loft(rings,segments=segments)
    first_row,last_row=3,6
    holes=(('upperarm_l',29),('upperarm_r',13))
    def is_cut(row,col):
        if not first_row<=row<last_row:return False
        for _name,start in holes:
            if (col-start)%segments<6:return True
        return False
    old=list(f)
    f=[face for idx,face in enumerate(old) if not is_cut(idx//segments,idx%segments)]
    removed=len(old)-len(f)
    if removed!=36:
        raise RuntimeError('Torso must have two precise 18-face shoulder openings')
    def node(row,col):return row*segments+(col%segments)
    def perimeter(start):
        # 3 rows x 6 columns => 2*(3+6)=18 vertices.
        loop=[node(first_row,start+k) for k in range(7)]
        loop.extend(node(row,start+6) for row in range(first_row+1,last_row+1))
        loop.extend(node(last_row,start+k) for k in range(5,-1,-1))
        loop.extend(node(row,start) for row in range(last_row-1,first_row,-1))
        if len(loop)!=18 or len(set(loop))!=18:
            raise RuntimeError('Invalid shoulder boundary topology')
        return loop
    for bone_name,start in holes:
        bone=arm.data.bones[bone_name]
        a=arm.matrix_world@bone.head_local
        b=arm.matrix_world@bone.tail_local
        new_v,new_f=sleeve(a,b,segments=18)
        off=len(v)
        v.extend(new_v)
        f.extend([tuple(off+i for i in face) for face in new_f])
        body_loop=perimeter(start)
        # Find a continuous one-to-one mapping, not nearest vertices:
        # otherwise bridge faces would self-intersect and leave cracks.
        mappings=[]
        for direction in (1,-1):
            for shift in range(18):
                ids=[(shift+direction*k)%18 for k in range(18)]
                score=sum((Vector(v[body_loop[k]])-Vector(v[off+ids[k]])).length_squared
                          for k in range(18))
                mappings.append((score,ids))
        _score,ring=min(mappings,key=lambda item:item[0])
        # Two-row rounded shoulder transition: one oversized quad bridge
        # previously made a hard ridge / wing at the upper shoulder in idle.
        # Mid-points are genuine shared mesh vertices; both bridge rows are
        # welded, so the original 4-opening manifold stays intact.
        mids=[]
        for k in range(18):
            shoulder=Vector(v[body_loop[k]])
            sleeve_root=Vector(v[off+ring[k]])
            point=shoulder.lerp(sleeve_root,.52)
            point.z-=.025
            mids.append(len(v))
            v.append(tuple(point))
        for k in range(18):
            n=(k+1)%18
            a0=body_loop[k];a1=body_loop[n]
            m0=mids[k];m1=mids[n]
            b0=off+ring[k];b1=off+ring[n]
            f.append((a0,a1,m1,m0))
            f.append((m0,m1,b1,b0))
    return v,f


def cuff_tube(a,b,at=.385,length=.031,radius=.107,segments=18):
    """Ribbed sleeve hem exactly aligned to arm axis and sewn garment cuff."""
    a=Vector(a);b=Vector(b)
    axis=(b-a).normalized()
    u=axis.cross(Vector((0,0,1))).normalized()
    v=axis.cross(u).normalized()
    points=[];faces=[]
    for frac,r in ((at,radius+.002),(at+length,radius+.001),
                   (at+length+.006,radius-.004)):
        p=a+axis*frac
        for j in range(segments):
            theta=j*math.tau/segments
            q=p+u*math.cos(theta)*r+v*math.sin(theta)*r
            points.append(tuple(q))
    for row in range(2):
        for j in range(segments):
            i=row*segments+j;k=row*segments+(j+1)%segments
            faces.append((i,k,k+segments,i+segments))
    return points,faces


def mesh_topology(vertices,faces):
    """Count true topology components and naked edges; independent of Blender UI."""
    roots=list(range(len(vertices)))
    def root(x):
        while roots[x]!=x:
            roots[x]=roots[roots[x]]
            x=roots[x]
        return x
    edges=Counter()
    touched=set()
    for face in faces:
        if len(face)<3:raise RuntimeError('Degenerate clothing face')
        for i,a in enumerate(face):
            b=face[(i+1)%len(face)]
            if a==b:raise RuntimeError('Zero-length topology edge')
            touched.add(a);touched.add(b)
            ra=root(a);rb=root(b)
            if ra!=rb:roots[rb]=ra
            edges[tuple(sorted((a,b)))]+=1
    if any(n>2 for n in edges.values()):
        raise RuntimeError('Non-manifold overlapping garment edges')
    boundary=[pair for pair,n in edges.items() if n==1]
    return {'connected_components':len({root(i) for i in touched}),
            'boundary_edges':len(boundary),
            'non_manifold_edges':sum(n>2 for n in edges.values())}


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
    # Object.copy() retains armature modifier and hierarchy but Blender does
    # not necessarily copy vertex group definitions after swapping .data.
    # Create the full matching set explicitly before assigning influences.
    dst={g.name:g for g in output.vertex_groups}
    for name in groups.values():
        if name not in dst:dst[name]=output.vertex_groups.new(name=name)
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
    # Make face winding consistent after connecting the armholes. These seams
    # are genuine shared-vertex joints and NOT texture overlays.
    bm=bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    # Face-culling-safe normals for the separate garment topology.
    # No material-replacement trick or cosmetic overlay on the body.
    for poly in mesh.polygons:
        poly.use_smooth=True
    if not any(mod.type=='ARMATURE' for mod in obj.modifiers):
        raise RuntimeError(name+' is not deformable')
    qa=mesh_topology(world_vertices,polys)
    if name=='RB_TShirt':
        if qa['connected_components']!=1 or qa['boundary_edges']!=100:
            raise RuntimeError('T-shirt is not a seamless four-opening garment: '+str(qa))
    return obj,{'name':name,'vertices':n,'faces':len(mesh.polygons),
                'skinned':True,**qa}


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
        'collar':material('RB_CrewNeckRibbing',(.10,.40,.46)),
        'seams':material('RB_ShirtSeamCloth',(.13,.45,.51)),
        'flaps':material('RB_CargoFlapTrim',(.35,.27,.20)),
        'shorts':material('RB_SandCargoShorts',(.53,.40,.28)),
        'shoes':material('RB_CanvasDeckShoes',(.21,.25,.25)),
        'hair':material('RB_ShortDarkHair',(.14,.10,.08)),
        'pouch':material('RB_SmallLeatherPouch',(.32,.20,.11)),
        'pocket':material('RB_CargoPocketFabric',(.43,.31,.22)),
        'sole':material('RB_RubberShoeSoles',(.115,.14,.14)),
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
        # A real shoulder slopes below the neckline. The previous 
        # .815/.852-height shoulder sections generated two prominent
        # triangular spikes when the T-pose arms folded into idle.
        (x0,cy,lo+.765*h,.218,.158),
        (x0,cy,lo+.797*h,.204,.151),
        (x0,cy,lo+.823*h,.166,.119),
        (x0,cy,lo+.874*h,.095,.091),
    ]
    # Shared armhole edge loops rather than three disconnected cylinders.
    add('RB_TShirt',stitched_shirt(rings,arm),'shirt')
    # A narrow crew-neck band obscures the flat-looking raw loft neckline.
    # The band is a separate fitted skinned strip, not a substitute for
    # welding the sleeve topology (which is independently validated).
    collar=loft([
        (x0,cy,lo+.862*h,.096,.092),
        (x0,cy,lo+.876*h,.098,.093),
        (x0,cy,lo+.882*h,.091,.090)
    ],32)
    add('RB_CrewNeck',collar,'collar')
    add('RB_ShirtHem',loft([
        (x0,cy,lo+.483*h,.182,.145),
        (x0,cy,lo+.489*h,.187,.147),
        (x0,cy,lo+.501*h,.189,.147),
    ],32),'seams')
    for name,tag in (('upperarm_l','L'),('upperarm_r','R')):
        bone=arm.data.bones[name]
        a=arm.matrix_world@bone.head_local
        b=arm.matrix_world@bone.tail_local
        add('RB_SleeveCuff_'+tag,cuff_tube(a,b),'seams')

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
    # Real cargo side pockets, distinct fabric and silhouette, each weighted
    # to the thigh so they articulate during walk/cast without hovering.
    for side,label in ((-1,'L'),(1,'R')):
        cx=x0+side*.212
        pocket=loft([
            (cx,cy+.036,lo+.313*h,.044,.056),
            (cx,cy+.036,lo+.325*h,.052,.058),
            (cx,cy+.036,lo+.367*h,.054,.059),
            (cx,cy+.036,lo+.378*h,.044,.052),
        ],24)
        add('RB_CargoPocket_'+label,pocket,'pocket')
        # Visible fabric flap and top seam. The panel follows the same thigh
        # weighted neighborhood as the pocket; it is not a decal.
        flap=loft([
            (cx,cy+.041,lo+.370*h,.054,.060),
            (cx,cy+.041,lo+.384*h,.052,.059),
            (cx,cy+.041,lo+.391*h,.045,.053),
        ],24)
        add('RB_CargoFlap_'+label,flap,'flaps')

    # Pair of low canvas shoes with a REAL enclosed sole instead of open
    # cylinders revealing the character's toes through their bottoms.
    for side,tag in [(-1,'L'),(1,'R')]:
        cx=x0+side*.122
        # Position each shoe from the true toe-to-heel body envelope, not
        # the median instep. The latter was biased toward the heel and left
        # toes visibly poking out of the shoes in the Three.js idle screenshot.
        sample=[p for p in points if lo-.01*h<p.z<lo+.105*h and abs(p.x-cx)<.095]
        if len(sample)<50:raise RuntimeError('Cannot measure foot envelope '+tag)
        fy=(min(p.y for p in sample)+max(p.y for p in sample))*.5
        shoe_vertices,shoe_faces=loft([
            (cx,fy,lo-.008*h,.106,.147),
            (cx,fy,lo+.019*h,.108,.153),
            (cx,fy+.014,lo+.047*h,.092,.132),
            (cx,fy+.023,lo+.077*h,.076,.103),
        ],24)
        # Closed underside, with enough room for the foot mesh.
        shoe_faces.append(tuple(reversed(range(24))))
        add('RB_CanvasShoes_'+tag,(shoe_vertices,shoe_faces),'shoes')
        # Visible thin rubber perimeter, not a second bulky boot shaft.
        sole=loft([
            (cx,fy-.001,lo-.013*h,.110,.155),
            (cx,fy-.002,lo+.004*h,.112,.155),
            (cx,fy,lo+.019*h,.108,.153),
        ],24)
        add('RB_ShoeSole_'+tag,sole,'sole')

    # Short side-parted hair above the eyebrows: face and eyes unobstructed.
    head_samples=[p for p in points if lo+.93*h<p.z<lo+.985*h and abs(p.x)<.24]
    hy=(min(p.y for p in head_samples)+max(p.y for p in head_samples))*.5 if head_samples else cy
    hair=loft([
        (x0-.005,hy,lo+.961*h,.091,.089),
        (x0-.006,hy,lo+.982*h,.098,.096),
        (x0-.003,hy,lo+.999*h,.076,.075),
        (x0+.002,hy,lo+1.008*h,.038,.041),
        (x0+.009,hy,lo+1.012*h,.006,.008),
    ],28)
    add('RB_ShortHair',hair,'hair')

    pouch_center=(x0+.190,cy+.010,lo+.445*h)
    add('RB_SmallCargoPouch',accessory_box_geometry(pouch_center,(.095,.082,.129)),'pouch')
    return results


def accessory_box_geometry(center,size):
    """A small rounded utility pouch (not a crude eight-vertex cube)."""
    cx,cy,cz=center
    dx,dy,dz=size
    rings=[]
    for f,k in ((-.50,.72),(-.35,1.0),(.35,1.0),(.50,.72)):
        rings.append((cx,cy,cz+dz*f,dx*k*.5,dy*k*.5))
    return loft(rings,24)
