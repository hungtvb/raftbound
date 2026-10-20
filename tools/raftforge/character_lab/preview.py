"""Actual offscreen renderer evidence using free VTK (no image generation)."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image,ImageDraw,ImageFont


def _pbr_color_multiplier(material):
    """glTF baseColorFactor is linearized RGB 0..1, unlike 8-bit COLOR_0."""
    base = getattr(material, 'baseColorFactor', None)
    if base is None:
        return np.array([1.0, 1.0, 1.0], dtype=np.float32)
    value = np.asarray(base, dtype=np.float32)[:3]
    if not np.isfinite(value).all() or len(value) != 3:
        raise ValueError('Invalid PBR baseColorFactor')
    # Defensive tolerance for nonstandard trimesh materials storing 8-bit RGB.
    if np.max(value) > 1.0:
        value /= 255.0
    return np.clip(value, 0.0, 1.0)


def _compose_vertex_material_color(vertex_rgb, material):
    """glTF PBR: baseColor = baseColorFactor * COLOR_0 (texture if present).

    The VTK QA renderer has no GLTF shader. Bake the factor into per-vertex
    RGB instead of discarding it when COLOR_0 is present.
    """
    rgb = np.asarray(vertex_rgb, dtype=np.float32)
    if rgb.ndim != 2 or rgb.shape[1] < 3:
        raise ValueError('Invalid per-vertex RGB')
    return np.rint(np.clip(rgb[:, :3] * _pbr_color_multiplier(material), 0.0, 255.0)).astype(np.uint8)


def render_glb(glb,angle='hero',size=(760,620),framing_bounds=None):
    try:
        import vtk
        from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy
    except ImportError as e:
        raise ImportError('Install optional vtk package to render software evidence') from e
    scene=trimesh.load(glb,force='scene')
    # trimesh may classify a GLB mesh with COLOR_0 + PBR material as
    # TextureVisuals and silently hide its vertex RGB. Read glTF accessors
    # directly when available, matching geometry by glTF mesh name.
    direct_colors={}
    try:
        from .quality import read_glb
        document,chunks=read_glb(glb)
        binary=next((v for k,v in chunks if k==0x004E4942),b'')
        for mesh in document.get('meshes',[]):
            prims=mesh.get('primitives',[])
            if len(prims)!=1 or 'COLOR_0' not in prims[0].get('attributes',{}):continue
            a=document['accessors'][prims[0]['attributes']['COLOR_0']]
            view=document['bufferViews'][a['bufferView']]
            fields={'VEC3':3,'VEC4':4}; comps={5121:np.uint8,5123:np.uint16,5126:np.float32}
            width=fields.get(a['type']);dtype=comps.get(a['componentType'])
            if not width or dtype is None:continue
            start=view.get('byteOffset',0)+a.get('byteOffset',0)
            stride=view.get('byteStride',np.dtype(dtype).itemsize*width)
            if stride!=np.dtype(dtype).itemsize*width:
                color=np.stack([np.frombuffer(binary,dtype=dtype,count=width,offset=start+i*stride) for i in range(a['count'])])
            else:
                color=np.frombuffer(binary,dtype=dtype,count=a['count']*width,offset=start).reshape(-1,width)
            if a['componentType']==5126:color=np.rint(np.clip(color[:,:3],0,1)*255).astype(np.uint8)
            elif a.get('normalized'):color=np.rint(color[:,:3].astype(float)/np.iinfo(dtype).max*255).astype(np.uint8)
            else:color=np.clip(color[:,:3],0,255).astype(np.uint8)
            direct_colors[mesh['name']]=color
    except (KeyError,ValueError,TypeError,IndexError):
        direct_colors={}

    renderer=vtk.vtkRenderer();renderer.SetBackground(.065,.125,.174)
    renderer.SetBackground2(.12,.21,.258);renderer.GradientBackgroundOn()
    renderer.AutomaticLightCreationOff()
    # Matching camera framing is required for valid before-vs-after evidence:
    # auto-framing each GLB separately can visually conceal body height changes.
    bounds=np.asarray(framing_bounds,dtype=float) if framing_bounds is not None else scene.bounds
    if bounds.shape!=(2,3) or not np.isfinite(bounds).all() or np.any(bounds[1]<=bounds[0]):
        raise ValueError('Invalid shared camera framing bounds')
    center=(bounds[0]+bounds[1])*.5
    radius=float(np.linalg.norm(bounds[1]-bounds[0]))*.52
    focus=center.copy();focus[1]+=.03*radius
    # Scene graph matrices must be applied; otherwise the rig-safe fitting root
    # changes glTF placement but the QA image still draws the unfitted mesh.
    for node in scene.graph.nodes_geometry:
        transform, geom_name=scene.graph[node]
        geom=scene.geometry[geom_name].copy()
        geom.apply_transform(transform)
        vertices=np.asarray(geom.vertices, dtype=np.float32)
        faces=np.asarray(geom.faces,dtype=np.int64)
        pts=vtk.vtkPoints();pts.SetData(numpy_to_vtk(vertices,deep=True))
        cells=vtk.vtkCellArray()
        for tri in faces:
            t=vtk.vtkTriangle()
            for i,p in enumerate(tri):t.GetPointIds().SetId(i,int(p))
            cells.InsertNextCell(t)
        poly=vtk.vtkPolyData();poly.SetPoints(pts);poly.SetPolys(cells)
        mat=getattr(geom.visual,'material',None)
        vertex_color = geom_name in direct_colors or getattr(geom.visual, 'kind', None) == 'vertex'
        if vertex_color:
            color_array = direct_colors.get(geom_name) if geom_name in direct_colors else np.asarray(geom.visual.vertex_colors, dtype=np.uint8)
            if len(color_array) != len(vertices):
                raise ValueError('Invalid vertex-color count in GLB')
            # Previously COLOR_0 whitened the costume because PBR material
            # colors were ignored. Multiply both as specified by glTF.
            display_rgb = _compose_vertex_material_color(color_array, mat)
            scalars = numpy_to_vtk(np.ascontiguousarray(display_rgb), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
            scalars.SetName('PBR_x_COLOR_0')
            poly.GetPointData().SetScalars(scalars)
        normals=vtk.vtkPolyDataNormals();normals.SetInputData(poly)
        normals.SetSplitting(True);normals.SetFeatureAngle(48);normals.ConsistencyOn();normals.AutoOrientNormalsOn();normals.Update()
        mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(normals.GetOutputPort())
        if vertex_color:
            mapper.ScalarVisibilityOn()
            mapper.SetScalarModeToUsePointData()
            mapper.SetColorModeToDirectScalars()
        else:
            mapper.ScalarVisibilityOff()
        actor=vtk.vtkActor();actor.SetMapper(mapper)
        color=[1.0,1.0,1.0] if vertex_color else _pbr_color_multiplier(mat).tolist()
        met=float(getattr(mat,'metallicFactor',0.) or 0.)
        prop=actor.GetProperty();prop.SetColor(*color);prop.SetInterpolationToPhong()
        prop.SetAmbient(.21);prop.SetDiffuse(.73);prop.SetSpecular(.25+met*.35)
        prop.SetSpecularPower(20+met*25)
        renderer.AddActor(actor)
    # Soft circular tabletop: stays visually behind the prop
    disc=vtk.vtkCylinderSource();disc.SetRadius(max(radius*.68,.45));disc.SetHeight(.015);disc.SetResolution(64)
    disc_mapper=vtk.vtkPolyDataMapper();disc_mapper.SetInputConnection(disc.GetOutputPort())
    disc_actor=vtk.vtkActor();disc_actor.SetMapper(disc_mapper)
    disc_actor.SetPosition(float(center[0]),float(bounds[0][1]-.09),float(center[2]))
    disc_actor.GetProperty().SetColor(.10,.18,.205);disc_actor.GetProperty().SetOpacity(.7)
    renderer.AddActor(disc_actor)
    for pos,intensity,color in [((3,8,-5),1.,(.97,.92,.81)),((-6,3,2),.52,(.57,.80,.97)),((2,4,6),.8,(.96,.83,.58))]:
        lamp=vtk.vtkLight();lamp.SetLightTypeToSceneLight();lamp.SetPosition(*(center+np.asarray(pos)*radius*.75));lamp.SetFocalPoint(*center)
        lamp.SetColor(*color);lamp.SetIntensity(intensity);renderer.AddLight(lamp)
    cams={'hero':np.array([1.8,1.52,-2.2]),'rear':np.array([-1.8,1.30,2.3]),'top':np.array([1.2,3.2,-1.3]),'front':np.array([0,1.15,-2.8])}
    view=cams[angle]
    camera=renderer.GetActiveCamera();camera.SetFocalPoint(*focus)
    camera.SetPosition(*(focus+view*radius*1.6));camera.SetViewUp(0,1,0)
    camera.SetClippingRange(.01,50);camera.ParallelProjectionOn();camera.SetParallelScale(max(radius*.97,.75))
    w=vtk.vtkRenderWindow();w.SetOffScreenRendering(True);w.SetSize(*size);w.SetMultiSamples(4);w.AddRenderer(renderer)
    w.Render()
    filt=vtk.vtkWindowToImageFilter();filt.SetInput(w);filt.SetInputBufferTypeToRGB();filt.ReadFrontBufferOff();filt.Update()
    data=filt.GetOutput();arr=vtk_to_numpy(data.GetPointData().GetScalars()).reshape((size[1],size[0],3))
    im=Image.fromarray(np.flipud(arr.copy()),'RGB')
    w.Finalize()
    return im


def font(sz,bold=False):
    candidates=[f'/usr/share/fonts/truetype/dejavu/DejaVuSans{"-Bold" if bold else ""}.ttf',
                '/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf']
    for path in candidates:
        try:return ImageFont.truetype(path,sz)
        except OSError:continue
    return ImageFont.load_default()


def contact_sheet(glbs,out):
    angles=['hero','rear','top']
    glbs=[Path(x) for x in glbs]
    cw,ch=520,420
    pad=16;header=116
    img=Image.new('RGB',(len(angles)*cw+pad*2,len(glbs)*(ch+50)+header+pad*2),(13,32,43))
    draw=ImageDraw.Draw(img)
    draw.text((35,23),'RAFTFORGE / A11',font=font(30,True),fill='#f2d9ac')
    draw.text((35,65),'Procedural GLB • real offscreen model renders • free / offline',font=font(16),fill='#bbd2d4')
    for i,glb in enumerate(glbs):
        for j,angle in enumerate(angles):
            piece=render_glb(glb,angle=angle,size=(cw-12,ch-12))
            x=pad+j*cw+6;y=header+pad+i*(ch+50)
            img.paste(piece,(x,y))
            draw.text((x+12,y+ch-2),glb.stem.replace('_art','').replace('_',' ').upper()+' / '+angle.upper(),font=font(14,True),fill='#f3d6a5')
    out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);img.save(out,optimize=True)
    return out
