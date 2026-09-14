"""Original local Blender scene: no API, downloaded model, or remote texture.

Dependencies: Python 3.13 + bpy 5.2, numpy, Pillow.
Usage: python tools/render_casebook.py --work-dir PATH --out PATH [--draft]
The Windows SimSun font is rasterized into the paper; no font file is distributed.
"""
import argparse
import math
import random
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFont, ImageFilter

parser = argparse.ArgumentParser()
parser.add_argument('--work-dir', type=Path, required=True)
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--font', default='C:/Windows/Fonts/simsun.ttc')
parser.add_argument('--draft', action='store_true')
args = parser.parse_args()
args.work_dir = args.work_dir.resolve()
args.out = args.out.resolve()
args.work_dir.mkdir(parents=True, exist_ok=True)
args.out.parent.mkdir(parents=True, exist_ok=True)
random.seed(2317)
rng = np.random.default_rng(2317)


def paper_texture():
    w, h = 1800, 2300
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    coarse = Image.fromarray(rng.integers(45, 220, (70, 55), dtype=np.uint8)).resize((w, h), Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(30))
    clouds = (np.asarray(coarse, dtype=np.float32) - 128) / 25
    fine = rng.normal(0, 1.6, (h, w)).astype(np.float32)
    edge = np.minimum(np.minimum(xx, w - xx), np.minimum(yy, h - yy))
    ageing = np.exp(-edge / 56) * 29
    stains = np.zeros((h, w), np.float32)
    for _ in range(21):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        sx, sy = rng.uniform(20, 160), rng.uniform(20, 210)
        stains += np.exp(-((xx - x) / sx)**2 - ((yy - y) / sy)**2) * rng.uniform(2, 13)
    fold = np.exp(-((xx - 915 - np.sin(yy / 520) * 5) / 4)**2) * 16
    fold += np.exp(-((yy - 1510 + np.sin(xx / 390) * 2) / 3)**2) * 11
    values = clouds + fine - ageing - stains - fold
    arr = np.stack([np.clip(base + values, 0, 255) for base in (207, 188, 151)], axis=-1).astype('uint8')
    im = Image.fromarray(arr)
    overlay = Image.new('RGBA', (w, h)); d = ImageDraw.Draw(overlay)
    # Typeset the exact user-provided title, with enough room for the perspective.
    title_font = ImageFont.truetype(args.font, 335)
    title = '夜半卷宗'
    spacing = 32
    total = sum(d.textlength(c, font=title_font) for c in title) + spacing * 3
    x = (w - total) / 2
    for c in title:
        d.text((x, 575), c, font=title_font, fill=(37, 35, 29, 242), stroke_width=1)
        x += d.textlength(c, font=title_font) + spacing
    # Restrained archival rulework and non-spoiler case metadata.
    small = ImageFont.truetype(args.font, 37)
    tiny = ImageFont.truetype(args.font, 24)
    mono = ImageFont.truetype('C:/Windows/Fonts/cour.ttf', 24)
    d.text((165, 225), '证 据 留 存', font=small, fill=(58, 48, 34, 145))
    d.text((1270, 239), 'E-01 / 001', font=mono, fill=(61, 51, 37, 158))
    d.line([(155, 350), (1640, 350)], fill=(79, 60, 40, 115), width=2)
    d.line([(155, 362), (1640, 362)], fill=(79, 60, 40, 75), width=1)
    d.text((610, 1100), 'MIDNIGHT CASEBOOK', font=mono, fill=(54, 47, 35, 155))
    d.line([(520, 1185), (1280, 1185)], fill=(75, 58, 37, 92), width=1)
    for y in range(1420, 1930, 115):
        d.line([(170, y), (1620, y)], fill=(85, 67, 43, 49), width=1)
    d.text((168, 2010), '现场采集 / 待归档', font=tiny, fill=(52, 42, 32, 128))
    d.text((1370, 2010), '01 — 06', font=mono, fill=(52, 42, 32, 128))
    # A rubbed archival seal and a partial coffee ring.
    stamp = Image.new('RGBA', (340, 170)); sd = ImageDraw.Draw(stamp)
    sd.rectangle((12, 12, 328, 158), outline=(111, 39, 29, 111), width=8)
    sd.rectangle((23, 23, 317, 147), outline=(111, 39, 29, 100), width=2)
    sd.text((55, 49), '待核验', font=ImageFont.truetype(args.font, 66), fill=(111, 39, 29, 145))
    stamp = stamp.rotate(-11, resample=Image.Resampling.BICUBIC, expand=True)
    overlay.alpha_composite(stamp, (1140, 1660))
    for radius in (207, 211, 215):
        d.arc((1450-radius, 470-radius, 1450+radius, 470+radius), 85, 295, fill=(99, 65, 33, 32), width=3)
    # Random ink loss is deterministic and independent of Chinese character shape.
    overlay_arr = np.array(overlay)
    wear = rng.random((h, w))
    overlay_arr[:, :, 3][wear > .982] //= 3
    im = Image.alpha_composite(im.convert('RGBA'), Image.fromarray(overlay_arr))
    texture_path = args.work_dir / 'paper-letterpress.png'
    im.convert('RGB').save(texture_path)
    return texture_path


def material(name, color, roughness=.5, metallic=0):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    shader = mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = metallic
    return mat, shader


def add_noise(mat, scale, detail=3):
    n = mat.node_tree.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail
    return n


def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def cube(name, location, scale, mat, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object; obj.name = name; obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new('Worn rounded edges', 'BEVEL'); modifier.width = bevel; modifier.segments = 3
        obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return obj


def lathe(name, profile, mat, location=(0,0,0), segments=128):
    vertices = [(r * math.cos(i / segments * math.tau), r * math.sin(i / segments * math.tau), z)
                for r,z in profile for i in range(segments)]
    faces=[]
    for ring in range(len(profile)-1):
        for i in range(segments):
            a=ring*segments+i; b=ring*segments+(i+1)%segments
            faces.append((a,b,b+segments,a+segments))
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(vertices,[],faces); mesh.update()
    obj=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(obj)
    obj.location=location; obj.data.materials.append(mat)
    for f in mesh.polygons:f.use_smooth=True
    return obj


def curve(name, points, bevel, mat):
    data=bpy.data.curves.new(name,'CURVE'); data.dimensions='3D'; data.resolution_u=16
    data.bevel_depth=bevel; data.bevel_resolution=5
    spline=data.splines.new('BEZIER'); spline.bezier_points.add(len(points)-1)
    for b,p in zip(spline.bezier_points,points):
        b.co=p; b.handle_left_type='AUTO'; b.handle_right_type='AUTO'
    obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj); data.materials.append(mat)
    return obj


def light(name, loc, energy, color, size, target, shape='DISK', size_y=None):
    data=bpy.data.lights.new(name,'AREA'); data.energy=energy; data.color=color; data.shape=shape; data.size=size
    if size_y is not None:data.size_y=size_y
    obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj); obj.location=loc; aim(obj,target)
    return obj


def paper(name, mat, x, y, z, rotation, w=3.06, h=4.02, curl=True):
    nx,ny=60,80; verts=[]; uvs=[]
    for j in range(ny+1):
        v=j/ny
        for i in range(nx+1):
            u=i/nx; px=(u-.5)*w; py=(v-.5)*h
            if i in (0,nx):px+=random.uniform(-.013,.013)
            if j in (0,ny):py+=random.uniform(-.013,.013)
            edge=min(u,1-u,v,1-v)
            pz=.006*math.sin(u*20+v*13)
            if curl:
                pz+=.064*math.exp(-edge*42)*(1+math.sin(v*11+u*14))
                pz+=.016*math.exp(-((u-.51)/.012)**2)
            verts.append((px,py,pz)); uvs.append((u,v))
    faces=[]
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i; faces.append((a,a+1,a+nx+2,a+nx+1))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
    uv=mesh.uv_layers.new(name='Paper UV')
    for poly in mesh.polygons:
        for loop in poly.loop_indices:uv.data[loop].uv=uvs[mesh.loops[loop].vertex_index]
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    obj.location=(x,y,z);obj.rotation_euler[2]=rotation;obj.data.materials.append(mat)
    mod=obj.modifiers.new('Paper thickness','SOLIDIFY');mod.thickness=.005
    return obj


def build():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.samples=24 if args.draft else 160
    scene.cycles.use_denoising=True;scene.cycles.adaptive_threshold=.06 if args.draft else .018
    scene.cycles.max_bounces=8
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type='OPTIX';prefs.get_devices()
        for device in prefs.devices:device.use=device.type=='OPTIX'
        if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
        print('Render devices:',[(d.name,d.type,d.use) for d in prefs.devices],flush=True)
    except Exception as error:print('CPU rendering:',str(error),flush=True)
    scene.render.resolution_x=960 if args.draft else 1920
    scene.render.resolution_y=844 if args.draft else 1688
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
    scene.render.film_transparent=False
    scene.world.use_nodes=True
    scene.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.065,.085,.072,1)
    scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.20
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=-.25

    wood,bs=material('Dark walnut with long open grain',(.08,.04,.021),.36)
    nodes=wood.node_tree.nodes;links=wood.node_tree.links
    coord=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY'
    mapping.inputs[1].default_value=(.55,32,8);links.new(coord.outputs['Generated'],mapping.inputs[0])
    noise=add_noise(wood,5,5);noise.inputs['Roughness'].default_value=.78;links.new(mapping.outputs[0],noise.inputs['Vector'])
    ramp=nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.20;ramp.color_ramp.elements[0].color=(.013,.009,.005,1)
    ramp.color_ramp.elements[1].position=.8;ramp.color_ramp.elements[1].color=(.125,.067,.029,1)
    links.new(noise.outputs['Fac'],ramp.inputs[0]);links.new(ramp.outputs['Color'],bs.inputs['Base Color'])
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.24;bump.inputs['Distance'].default_value=.042
    links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
    # Micro pores break up the broad grain and specular reflection.
    micro=add_noise(wood,235,2)
    micro_bump=nodes.new('ShaderNodeBump');micro_bump.inputs['Strength'].default_value=.23;micro_bump.inputs['Distance'].default_value=.015
    links.new(micro.outputs['Fac'],micro_bump.inputs['Height']);links.new(bump.outputs['Normal'],micro_bump.inputs['Normal'])
    links.new(micro_bump.outputs['Normal'],bs.inputs['Normal'])
    rough=nodes.new('ShaderNodeMapRange');rough.inputs['To Min'].default_value=.29;rough.inputs['To Max'].default_value=.52
    links.new(micro.outputs['Fac'],rough.inputs['Value']);links.new(rough.outputs[0],bs.inputs['Roughness'])
    cube('Old investigation desktop',(0,0,-.20),(13,11,.38),wood,.06)
    dark,_=material('Deep desk seams',(.009,.011,.008),.9)
    for y in [-3.35,-1.7,0,1.7,3.4]:cube('Join between walnut boards',(0,y,-.003),(13,.013,.013),dark)

    paper_mat,pbs=material('Aged evidence document',(.65,.56,.4),.84)
    tex=paper_mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(paper_texture()))
    paper_mat.node_tree.links.new(tex.outputs['Color'],pbs.inputs['Base Color'])
    pn=add_noise(paper_mat,190,2)
    bump=paper_mat.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.18;bump.inputs['Distance'].default_value=.011
    paper_mat.node_tree.links.new(pn.outputs['Fac'],bump.inputs['Height']);paper_mat.node_tree.links.new(bump.outputs['Normal'],pbs.inputs['Normal'])
    backing,_=material('Old second leaf',(.48,.39,.25),.9)
    paper('Lower archive page',backing,-.88,.08,.018,math.radians(3),curl=False)
    paper('Evidence with exact title',paper_mat,-.93,-.04,.044,math.radians(-7))

    ceramic,cbs=material('Ivory ceramic glaze',(.73,.69,.56),.20)
    cbs.inputs['Coat Weight'].default_value=.27;cbs.inputs['Coat Roughness'].default_value=.17
    cn=add_noise(ceramic,145,3);cb=ceramic.node_tree.nodes.new('ShaderNodeBump')
    cb.inputs['Strength'].default_value=.10;cb.inputs['Distance'].default_value=.007
    ceramic.node_tree.links.new(cn.outputs['Fac'],cb.inputs['Height']);ceramic.node_tree.links.new(cb.outputs['Normal'],cbs.inputs['Normal'])
    cup=(1.64,.58,.085)
    lathe('Porcelain cup',[(.005,.06),(.26,.06),(.31,.07),(.355,.10),(.40,.17),(.45,.29),(.50,.50),(.535,.76),(.55,.86),(.552,.89),(.542,.91),(.522,.912),(.506,.895),(.505,.86),(.49,.74),(.46,.49),(.414,.29),(.36,.19),(.29,.16),(.005,.16)],ceramic,cup)
    lathe('Porcelain saucer',[(.002,.028),(.24,.028),(.34,.018),(.42,.018),(.44,.032),(.77,.06),(.90,.095),(.92,.12),(.91,.14),(.87,.15),(.75,.128),(.54,.091),(.45,.067),(.29,.064),(.002,.064)],ceramic,(cup[0],cup[1],.004))
    # Open C-shaped ceramic handle, oriented away from the page.
    curve('Coffee cup handle',[(cup[0]+.50,cup[1],.86),(cup[0]+.83,cup[1],.88),(cup[0]+1.00,cup[1],.66),(cup[0]+.91,cup[1],.36),(cup[0]+.46,cup[1],.33)],.085,ceramic)
    coffee,cfs=material('Dark coffee',(.026,.009,.0028),.16)
    cfs.inputs['IOR'].default_value=1.333;cfs.inputs['Specular IOR Level'].default_value=.48
    lathe('Coffee surface with meniscus',[(.001,.0),(.474,.0),(.488,.009),(.493,.016)],coffee,(cup[0],cup[1],.85))
    crema,_=material('Minute coffee bubbles',(.17,.065,.016),.31)
    for i in range(42):
        a=random.uniform(0,math.tau);r=random.uniform(.462,.482);rad=random.uniform(.003,.011)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=10,ring_count=6,radius=rad,location=(cup[0]+r*math.cos(a),cup[1]+r*math.sin(a),.855))
        ob=bpy.context.object;ob.name='Coffee edge bubble';ob.scale.z=.24;ob.data.materials.append(crema)

    brass,bbs=material('Aged dark brass',(.17,.094,.033),.29,.82)
    bn=add_noise(brass,6,4);br=brass.node_tree.nodes.new('ShaderNodeValToRGB')
    br.color_ramp.elements[0].color=(.022,.027,.017,1);br.color_ramp.elements[1].color=(.25,.125,.035,1)
    brass.node_tree.links.new(bn.outputs['Fac'],br.inputs[0]);brass.node_tree.links.new(br.outputs['Color'],bbs.inputs['Base Color'])
    lamp_x,lamp_y=-3.12,2.20
    lathe('Tungsten lamp foot',[(.001,.015),(.41,.015),(.48,.06),(.46,.13),(.39,.19),(.27,.21),(.12,.22),(.001,.22)],brass,(lamp_x,lamp_y,0))
    curve('Lamp curved neck',[(lamp_x,lamp_y,.20),(lamp_x,lamp_y,.95),(lamp_x+.05,lamp_y,1.85),(lamp_x+.66,lamp_y,2.03)],.051,brass)
    shade,_=material('Black green enamel',(.016,.033,.023),.26,.48)
    shade_obj=lathe('Lamp shade',[(.58,0),(.59,.04),(.53,.16),(.40,.29),(.22,.41),(.105,.44),(.09,.48)],shade,(lamp_x+.65,lamp_y,1.60))
    shade_obj.rotation_euler[1]=math.radians(-12)
    light('Warm tungsten practical',(-2.44,1.95,1.56),95,(1,.70,.38),.48,(-.6,-.2,0))
    light('Soft warm key',(-3,-2,4.8),330,(1,.80,.57),3.1,(-.5,0,0))
    light('Rain window fill',(3.6,3.6,4.4),180,(.52,.69,.68),3.6,(.4,.2,0),'RECTANGLE',1.8)
    light('Narrow reflection in cup',(1.1,2.8,3.5),85,(1,.87,.68),.35,(1.5,.5,.5),'RECTANGLE',2.2)

    bpy.ops.object.camera_add(location=(.12,-6.8,9.6))
    camera=bpy.context.object;aim(camera,(-.05,.18,.0));camera.data.lens=51
    camera.data.dof.use_dof=True;camera.data.dof.focus_distance=(camera.location-Vector((-.2,0,.1))).length
    camera.data.dof.aperture_fstop=7.5
    scene.camera=camera
    scene.render.filepath=str(args.out)
    if not args.draft:
        bpy.ops.wm.save_as_mainfile(filepath=str(args.work_dir/'casebook-desk.blend'))
    print('Rendering',scene.render.resolution_x,scene.render.resolution_y,flush=True)
    bpy.ops.render.render(write_still=True)
    # Bake subtle grain and vignette into the asset itself so sampled pixels and
    # the static image share exactly the same colour when the animation starts.
    im=Image.open(args.out).convert('RGB')
    pix=np.asarray(im,dtype=np.float32)
    yy,xx=np.mgrid[0:im.height,0:im.width].astype(np.float32)
    radius=((xx/im.width-.50)/.68)**2+((yy/im.height-.51)/.69)**2
    vignette=1-.85*np.clip(radius,0,1)**1.6
    grain=rng.normal(0,.62,(im.height,im.width,1))
    pix=np.clip(pix*vignette[:,:,None]+grain,0,255).astype('uint8')
    Image.fromarray(pix).save(args.out)
    if not args.draft:
        web=Image.fromarray(pix).resize((1600,1408),Image.Resampling.LANCZOS).convert('RGBA')
        wy,wx=np.mgrid[0:1408,0:1600].astype(np.float32)
        border=np.minimum(np.minimum(wx,1599-wx)/75,np.minimum(wy,1407-wy)/66)
        alpha=np.clip(border,0,1);alpha=alpha*alpha*(3-2*alpha)
        web.putalpha(Image.fromarray(np.uint8(alpha*255)))
        web.save(args.out.with_suffix('.webp'),quality=91,method=6)
    print('Saved local 3D render:',str(args.out),flush=True)


build()
