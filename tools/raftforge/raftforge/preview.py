"""Actual offscreen renderer evidence using free VTK (no image generation)."""
from __future__ import annotations
from pathlib import Path
import numpy as np
import trimesh
from PIL import Image,ImageDraw,ImageFont


def render_glb(glb,angle='hero',size=(760,620)):
    try:
        import vtk
        from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy
    except ImportError as e:
        raise ImportError('Install optional vtk package to render software evidence') from e
    scene=trimesh.load(glb,force='scene')
    renderer=vtk.vtkRenderer();renderer.SetBackground(.065,.125,.174)
    renderer.SetBackground2(.12,.21,.258);renderer.GradientBackgroundOn()
    renderer.AutomaticLightCreationOff()
    bounds=scene.bounds
    center=(bounds[0]+bounds[1])*.5
    radius=float(np.linalg.norm(bounds[1]-bounds[0]))*.52
    focus=center.copy();focus[1]+=.03*radius
    for geom in scene.geometry.values():
        vertices=np.asarray(geom.vertices, dtype=np.float32)
        faces=np.asarray(geom.faces,dtype=np.int64)
        pts=vtk.vtkPoints();pts.SetData(numpy_to_vtk(vertices,deep=True))
        cells=vtk.vtkCellArray()
        for tri in faces:
            t=vtk.vtkTriangle()
            for i,p in enumerate(tri):t.GetPointIds().SetId(i,int(p))
            cells.InsertNextCell(t)
        poly=vtk.vtkPolyData();poly.SetPoints(pts);poly.SetPolys(cells)
        vertex_color = getattr(geom.visual, 'kind', None) == 'vertex'
        if vertex_color:
            color_array = np.asarray(geom.visual.vertex_colors, dtype=np.uint8)
            if len(color_array) != len(vertices):
                raise ValueError('Invalid vertex-color count in GLB')
            scalars = numpy_to_vtk(np.ascontiguousarray(color_array[:, :3]), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
            scalars.SetName('COLOR_0')
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
        mat=getattr(geom.visual,'material',None)
        rgba=getattr(mat,'baseColorFactor',[174,154,140,255])
        color=[1.0,1.0,1.0] if vertex_color else [float(c)/255 for c in rgba[:3]]
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
