"""Reusable, meter-scaled mesh building blocks for stylized survival props."""
from __future__ import annotations
import numpy as np
import trimesh
from scipy.spatial import ConvexHull


def chamfer_box(extents, bevel=0.02, center=(0, 0, 0)):
    ext = np.asarray(extents, float)
    if (ext <= 0).any():
        raise ValueError('Box extents must be positive')
    b = min(float(bevel), float(ext.min()) * 0.24)
    if b <= 0:
        m = trimesh.creation.box(extents=ext)
    else:
        h = ext / 2.0
        pts = []
        for a in (-1,1):
            for c in (-1,1):
                for d in (-1,1):
                    pts.extend([(a*(h[0]-b), c*h[1], d*h[2]),
                                (a*h[0], c*(h[1]-b), d*h[2]),
                                (a*h[0], c*h[1], d*(h[2]-b))])
        pts = np.asarray(pts)
        hull = ConvexHull(pts)
        m = trimesh.Trimesh(vertices=pts, faces=hull.simplices, process=True)
        m.fix_normals()
    m.apply_translation(np.asarray(center, float))
    return m


def rod(start, end, radius, sections=10, radius_end=None):
    start, end = np.asarray(start,float), np.asarray(end,float)
    axis = end - start
    length = float(np.linalg.norm(axis))
    if length < 1e-7:
        raise ValueError('Rod points must be distinct')
    r0=float(radius); r1=float(radius_end if radius_end is not None else radius)
    n=max(6,int(sections))
    dirs=np.linspace(0,2*np.pi,n,endpoint=False)
    v=np.concatenate((np.column_stack([r0*np.cos(dirs),r0*np.sin(dirs),np.zeros(n)]),
                      np.column_stack([r1*np.cos(dirs),r1*np.sin(dirs),np.full(n,length)]),
                      np.array([[0,0,0],[0,0,length]])))
    faces=[]
    for i in range(n):
        j=(i+1)%n
        faces.extend(((i,j,n+i),(j,n+j,n+i),(2*n,j,i),(2*n+1,n+i,n+j)))
    m=trimesh.Trimesh(vertices=v,faces=faces,process=False)
    align=trimesh.geometry.align_vectors([0,0,1],axis/length)
    m.apply_transform(align)
    m.apply_translation(start)
    return m


def ring(center, major, minor, normal=(0,1,0), n=40, sides=8):
    center=np.asarray(center,float)
    normal=np.asarray(normal,float);normal/=np.linalg.norm(normal)
    tangent=np.cross(normal,[1,0,0])
    if np.linalg.norm(tangent)<.1:tangent=np.cross(normal,[0,0,1])
    tangent/=np.linalg.norm(tangent);bitangent=np.cross(normal,tangent)
    vertices=[];faces=[]
    for i in range(n):
        theta=2*np.pi*i/n
        radial=np.cos(theta)*tangent+np.sin(theta)*bitangent
        for j in range(sides):
            phi=2*np.pi*j/sides
            vertices.append(center+radial*(major+minor*np.cos(phi))+normal*minor*np.sin(phi))
    for i in range(n):
        for j in range(sides):
            a=i*sides+j;b=((i+1)%n)*sides+j;c=((i+1)%n)*sides+(j+1)%sides;d=i*sides+(j+1)%sides
            faces.extend(((a,b,d),(b,c,d)))
    result=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    result.fix_normals()
    return result


def rope_line(points,radius=.014,sides=7):
    pts=list(points)
    return [rod(a,b,radius,sections=sides) for a,b in zip(pts,pts[1:]) if np.linalg.norm(np.array(b)-a)>1e-6]


def bowl(center=(0,0,0),bottom_radius=.37,top_radius=.52,height=.23,thick=.024,segments=48):
    """Open, solid-wall tapered bowl with visible inside and closed bottom."""
    cx,cy,cz=center
    angles=np.arange(segments)*2*np.pi/segments
    rings=[(bottom_radius,cy),(top_radius,cy+height),(top_radius-thick,cy+height),(bottom_radius-thick*.5,cy+thick)]
    verts=[]
    for r,y in rings:
        verts.extend(([cx+r*np.cos(a),y,cz+r*np.sin(a)] for a in angles))
    verts.extend([[cx,cy,cz],[cx,cy+thick,cz]])
    faces=[]
    for k in range(3):
        for i in range(segments):
            j=(i+1)%segments
            a=k*segments+i;b=k*segments+j;c=(k+1)*segments+j;d=(k+1)*segments+i
            faces.extend(((a,b,c),(a,c,d)))
    for i in range(segments):
        j=(i+1)%segments
        faces.extend(((4*segments,i,j),(4*segments+1,3*segments+j,3*segments+i)))
    m=trimesh.Trimesh(vertices=verts,faces=faces,process=False)
    m.fix_normals()
    return m


def leaf(center,length,width,normal_y=0.07):
    """Low-poly pointed organic sprout leaf."""
    x,y,z=center
    verts=[[x,y,z],[x+length*.35,y+normal_y,z-width*.32],
           [x+length,y+normal_y*1.6,z],[x+length*.35,y+normal_y,z+width*.32],
           [x+length*.4,y+normal_y*.5,z]]
    faces=[[0,1,4],[1,2,4],[2,3,4],[3,0,4]]
    return trimesh.Trimesh(vertices=verts,faces=faces,process=False)
