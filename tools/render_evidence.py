"""Cinematic evidence stills: local Blender/Cycles, no image API or external assets.

Run with a Python environment containing bpy, Pillow and NumPy. The manifest
contains only evidence descriptions visible at discovery, never case answers.
"""
import argparse
import json
import math
import random
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser()
parser.add_argument('--manifest', type=Path, required=True)
parser.add_argument('--work-dir', type=Path, required=True)
parser.add_argument('--out-dir', type=Path, required=True)
parser.add_argument('--only', default='')
parser.add_argument('--samples', type=int, default=64)
args = parser.parse_args()
args.work_dir.mkdir(parents=True, exist_ok=True)
args.out_dir.mkdir(parents=True, exist_ok=True)
FONT = 'C:/Windows/Fonts/simsun.ttc'
SANS = 'C:/Windows/Fonts/msyh.ttc'
random.seed(2709)


def material(name, color, rough=.5, metal=0, transmission=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    s = m.node_tree.nodes.get('Principled BSDF')
    s.inputs['Base Color'].default_value = (*color, 1)
    s.inputs['Roughness'].default_value = rough
    s.inputs['Metallic'].default_value = metal
    s.inputs['Transmission Weight'].default_value = transmission
    return m


def textured(name, color, scale=60, rough=.65, metal=0, stretch=(1, 1, 1)):
    m = material(name, color, rough, metal)
    n, links = m.node_tree.nodes, m.node_tree.links
    tex = n.new('ShaderNodeTexNoise'); tex.inputs['Scale'].default_value = scale
    tex.inputs['Detail'].default_value = 3
    coord = n.new('ShaderNodeTexCoord')
    mapping = n.new('ShaderNodeVectorMath'); mapping.operation = 'MULTIPLY'
    mapping.inputs[1].default_value = stretch
    links.new(coord.outputs['Generated'], mapping.inputs[0]); links.new(mapping.outputs[0], tex.inputs['Vector'])
    ramp = n.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (*[v*.45 for v in color], 1)
    ramp.color_ramp.elements[1].color = (*[min(v*1.5, 1) for v in color], 1)
    links.new(tex.outputs['Fac'], ramp.inputs[0])
    links.new(ramp.outputs[0], n.get('Principled BSDF').inputs['Base Color'])
    bump = n.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = .2; bump.inputs['Distance'].default_value = .02
    links.new(tex.outputs['Fac'], bump.inputs['Height']); links.new(bump.outputs[0], n.get('Principled BSDF').inputs['Normal'])
    return m


def box(name, pos, size, mat, bevel=.025, rot=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=pos, rotation=(0, 0, rot))
    o = bpy.context.object; o.name = name; o.dimensions = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.data.materials.append(mat)
    if bevel:
        b = o.modifiers.new('Machined edges', 'BEVEL'); b.width = bevel; b.segments = 3
        o.modifiers.new('Surface normals', 'WEIGHTED_NORMAL')
    return o


def cylinder(name, pos, radius, depth, mat, rot=(0, 0, 0), vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=pos, rotation=rot)
    o = bpy.context.object; o.name = name; o.data.materials.append(mat)
    b = o.modifiers.new('Rounded edge', 'BEVEL'); b.width = min(.015, depth/8); b.segments = 3
    o.modifiers.new('Normals', 'WEIGHTED_NORMAL')
    return o


def sphere(name, pos, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=28, ring_count=14, radius=1, location=pos)
    o = bpy.context.object; o.name=name; o.scale=scale; o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth=True
    return o


def curve(name, points, radius, mat, closed=False):
    data=bpy.data.curves.new(name, 'CURVE'); data.dimensions='3D'; data.bevel_depth=radius; data.bevel_resolution=3
    s=data.splines.new('POLY'); s.points.add(len(points)-1)
    for p, co in zip(s.points, points): p.co=(*co, 1)
    s.use_cyclic_u=closed
    obj=bpy.data.objects.new(name, data); bpy.context.collection.objects.link(obj); data.materials.append(mat)
    return obj


def ring(name, pos, radius, thickness, mat, ratio=1):
    return curve(name, [(pos[0]+radius*math.cos(t), pos[1]+radius*math.sin(t)*ratio, pos[2]) for t in np.linspace(0, math.tau, 100)], thickness, mat, True)


def lathe(name, pos, profile, mat):
    verts=[]; faces=[]; segments=80
    for r, z in profile:
        verts.extend([(pos[0]+r*math.cos(t*math.tau/segments), pos[1]+r*math.sin(t*math.tau/segments), pos[2]+z) for t in range(segments)])
    for j in range(len(profile)-1):
        for i in range(segments):
            a=j*segments+i; b=j*segments+(i+1)%segments
            faces.append((a,b,b+segments,a+segments))
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(verts,[],faces); mesh.materials.append(mat)
    obj=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(obj)
    for p in mesh.polygons:p.use_smooth=True
    return obj


def texture_image(name, title, lines=(), screen=False, chart=False, blue=False):
    w,h=1200,1500
    rng=np.random.default_rng(sum(map(ord,name)))
    base=np.array((18,35,36) if screen else (29,59,95) if blue else (195,182,151))
    noise=rng.normal(0,1.5,(h,w,1))
    arr=np.clip(np.broadcast_to(base,(h,w,3))+noise,0,255).astype('uint8')
    im=Image.fromarray(arr); d=ImageDraw.Draw(im)
    ink=(177,210,190) if screen else (220,225,220) if blue else (44,47,40)
    faint=(63,88,83) if screen else (96,125,158) if blue else (142,133,109)
    d.text((80,65),'CASEBOOK  /  EVIDENCE ARCHIVE',font=ImageFont.truetype('C:/Windows/Fonts/cour.ttf',26),fill=faint)
    d.line((80,135,1120,135),fill=faint,width=2)
    font=ImageFont.truetype(SANS,62 if len(title)<15 else 49)
    d.text((80,195),title,font=font,fill=ink)
    d.line((80,305,1120,305),fill=faint,width=2)
    y=370
    for text in lines:
        for start in range(0,len(text),23):
            d.text((85,y),text[start:start+23],font=ImageFont.truetype(FONT,42),fill=ink)
            y+=78
        y+=32
    if chart:
        top=max(y+20,670); bottom=1260
        for x in range(110,1120,125):d.line((x,top,x,bottom),fill=faint,width=1)
        for yy in range(top,bottom,90):d.line((110,yy,1080,yy),fill=faint,width=1)
        pts=[(120,top+20),(345,top+25),(430,bottom-160),(735,bottom-30),(850,top+40),(1080,top+35)]
        d.line(pts,fill=(158,189,173) if screen else (97,63,42),width=8)
        for x,text in [(275,'20:26'),(665,'20:34'),(895,'20:38')]:d.text((x,bottom+25),text,font=ImageFont.truetype('C:/Windows/Fonts/cour.ttf',34),fill=ink)
    else:
        for yy in range(min(y+70,1260),1360,65):d.line((85,yy,1110,yy),fill=faint,width=1)
    d.text((80,1435),'现场留存  ·  按原记录核对',font=ImageFont.truetype(FONT,26),fill=faint)
    path=args.work_dir/f'{name}.png'; im.save(path)
    return path


def image_mat(name, path, emission=0):
    m=material(name,(1,1,1),.68)
    n=m.node_tree.nodes; s=n.get('Principled BSDF'); tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(path),check_existing=True)
    m.node_tree.links.new(tex.outputs['Color'],s.inputs['Base Color'])
    if emission:
        m.node_tree.links.new(tex.outputs['Color'],s.inputs['Emission Color']);s.inputs['Emission Strength'].default_value=emission
    return m


def sheet(name,title,lines,pos=(0,0,.08),size=(2.25,2.8),rot=0,screen=False,chart=False,blue=False):
    path=texture_image(name,title,lines,screen,chart,blue)
    m=image_mat(name,path,.18 if screen else 0)
    width,height=size; verts=[];uvs=[];faces=[]; nx,ny=12,15
    for j in range(ny+1):
        for i in range(nx+1):
            x=(i/nx-.5)*width;y=(j/ny-.5)*height
            z=0 if screen else .015*math.sin(i*.5+j*.4)+.045*(abs(x)/(width/2))**12
            verts.append((pos[0]+x*math.cos(rot)-y*math.sin(rot),pos[1]+x*math.sin(rot)+y*math.cos(rot),pos[2]+z))
            uvs.append((i/nx,j/ny))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.materials.append(m)
    uv=mesh.uv_layers.new()
    for poly in mesh.polygons:
        for li in poly.loop_indices:uv.data[li].uv=uvs[mesh.loops[li].vertex_index]
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    if not screen:
        mod=obj.modifiers.new('Paper edge','SOLIDIFY');mod.thickness=.009
    return obj


def label(name,text,pos,size=(.85,.42),blue=False):
    path=args.work_dir/f'{name}-label.png'
    im=Image.new('RGB',(900,400),(24,53,89) if blue else (192,187,162));d=ImageDraw.Draw(im)
    lines=text.split('\n');font=ImageFont.truetype(SANS,75 if max(map(len,lines))<12 else 48)
    for i,line in enumerate(lines):d.text((45,50+i*100),line,font=font,fill=(208,220,222) if blue else (33,40,35))
    im.save(path)
    bpy.ops.mesh.primitive_plane_add(size=1,location=pos)
    o=bpy.context.object;o.name=name;o.scale=(size[0],size[1],1);o.data.materials.append(image_mat(name,path));return o


def cup(pos=(0,0,0),scale=1):
    x,y,z=pos
    lathe('Porcelain saucer',(x,y,z),[(0,.04),(.55,.04),(.83,.11),(.87,.14),(.84,.16),(.52,.09),(0,.09)],M['ceramic'])
    lathe('Tea cup',(x,y,z),[(0,.11),(.34,.11),(.39,.18),(.46,.65),(.49,.71),(.48,.75),(.44,.74),(.42,.66),(.34,.2),(0,.2)],M['ceramic'])
    cylinder('Dark amber tea',(x,y,z+.285),.354,.009,M['tea'])
    curve('Cup handle',[(x+.45+.3*math.sin(t),y,z+.43+.22*math.cos(t)) for t in np.linspace(0,math.pi,50)],.055,M['ceramic'])
    for _ in range(15):
        a=random.random()*math.tau;r=random.uniform(.05,.31)
        box('White crystalline residue',(x+math.cos(a)*r,y+math.sin(a)*r,z+.30),(.021,.018,.012),M['white'],.003,random.random())


def syringe(pos=(0,0,0)):
    x,y,z=pos
    cylinder('Fine barrel',(x,y,z+.13),.115,1.0,M['glass'],(math.pi/2,0,0))
    cylinder('Clear remnant',(x,y-.18,z+.13),.08,.5,M['liquid'],(math.pi/2,0,0))
    cylinder('Plunger',(x,y+.67,z+.13),.055,.5,M['white'],(math.pi/2,0,0))
    box('Plunger cap',(x,y+.91,z+.13),(.32,.07,.16),M['white'])
    cylinder('Needle hub',(x,y-.61,z+.13),.065,.2,M['metal'],(math.pi/2,0,0))
    cylinder('Fine needle',(x,y-1.03,z+.13),.008,.68,M['metal'],(math.pi/2,0,0),24)
    for i in range(9):box('Graduation',(x+.012,y-.4+i*.09,z+.24),(.055 if i%3 else .1,.009,.003),M['black'],0)
    label('Barrel ID','Z-17',(x+.43,y+.06,z+.055),(.5,.28))


def jar(pos=(0,0,0)):
    x,y,z=pos
    lathe('Sweetener glass jar',(x,y,z),[(0,.04),(.47,.04),(.5,.12),(.5,.85),(.45,1.0),(.46,1.04),(.42,1.04),(.4,.9),(.44,.1),(0,.1)],M['glass'])
    cylinder('Sweetener crystals',(x,y,z+.39),.435,.5,M['white'])
    cylinder('Pierced foil seal',(x,y,z+1.045),.448,.012,M['foil'])
    cylinder('Tiny puncture',(x+.11,y-.07,z+1.054),.019,.002,M['black'])
    for i in range(6):curve('Torn foil edge',[(x+.11,y-.07,z+1.06),(x+.11+math.cos(i)*.045,y-.07+math.sin(i)*.04,z+1.074)],.004,M['metal'])
    label('Sweetener label','代糖 / SWEETENER',(x,y-.1,z+.7),( .78,.35)).rotation_euler[0]=math.radians(78)
    cylinder('Jar lid',(x+.9,y+.15,z+.055),.47,.1,M['brass'])


def recorder(pos=(0,0,0)):
    x,y,z=pos
    box('Recorder aluminium body',(x,y,z+.19),(.91,2.02,.32),M['metal'],.1)
    box('Recorder black face',(x,y,z+.365),(.79,1.88,.035),M['black'],.06)
    for row in range(5):
        for col in range(7):cylinder('Microphone aperture',(x-.28+col*.09,y+.58+row*.062,z+.39),.02,.009,M['dark'])
    box('LCD bezel',(x,y+.12,z+.4),(.65,.55,.025),M['brass'])
    label('Recording timestamp','00:29\nLAST RECORDING',(x,y+.12,z+.42),(.59,.49))
    cylinder('Playback wheel',(x,y-.51,z+.43),.23,.07,M['metal'])
    cylinder('Play key',(x,y-.51,z+.475),.12,.025,M['black'])
    for dx in [-.24,.24]:cylinder('Transport key',(x+dx,y-.85,z+.405),.07,.03,M['metal'])
    cylinder('Unlit recording LED',(x+.25,y+.49,z+.408),.017,.01,M['black'])


def clipboard(name,title,lines,chart=False):
    box('Archive board',(0,0,.055),(2.65,3.2,.1),M['leather'],.06)
    sheet(name+'under','现场记录',[],pos=(.04,.04,.13),rot=.025)
    sheet(name,title,lines,pos=(-.035,-.02,.165),rot=-.018,chart=chart)
    box('Clip',(0,1.4,.215),(1.08,.33,.06),M['metal'])
    for x in [-.41,.41]:cylinder('Clip rivet',(x,1.4,.26),.045,.035,M['metal'])


def terminal(name,title,lines,chart=False):
    box('Industrial recorder',(0,.05,.17),(2.9,3.27,.34),M['metal'],.09)
    box('Recessed screen',(0,.18,.36),(2.53,2.76,.035),M['black'])
    sheet(name,title,lines,pos=(0,.18,.388),size=(2.35,2.64),screen=True,chart=chart)
    for x in [-1.28,1.28]:
        for y in [-1.42,1.5]:cylinder('Corner screw',(x,y,.362),.055,.015,M['metal'])
    for x in [-.38,0,.38]:box('Terminal key',(x,-1.43,.37),(.22,.12,.05),M['black'])
    curve('Recorder cable',[(.9,1.5,.15),(1.15,1.9,.12),(1.8,2.15,.1),(2.4,2.2,.08)],.036,M['black'])


def access_card(name='card',pos=(0,0,0),broken=False,back=False,token=False):
    x,y,z=pos
    if broken:
        points=[(-.85,-.49),(.57,-.49),(.3,-.16),(.61,.07),(.41,.2),(.83,.53),(-.85,.53)]
        mesh=bpy.data.meshes.new('Broken blue card');mesh.from_pydata([(x+a,y+b,z+.06) for a,b in points],[],[tuple(range(len(points)))]);mesh.materials.append(M['blue'])
        o=bpy.data.objects.new('Jagged card fragment',mesh);bpy.context.collection.objects.link(o);o.modifiers.new('Card thickness','SOLIDIFY').thickness=.045
        label(name,'墨衡数据',(x-.3,y+.08,z+.068),(.9,.38),blue=True)
        for j in range(10):curve('Attached coat fibre',[(x+.48,y-.15+j*.03,z+.08),(x+.66+random.random()*.15,y-.28+j*.028,z+.09)],.004,M['fabric'])
    else:
        box('Maintenance token' if token else 'Access card',(x,y,z+.055),(1.82,1.15,.09),M['blue'],.055)
        label(name,'S-02\n维护令牌' if token else '墨衡数据\n门禁授权 / 背面编号' if back else '墨衡数据',(x,y+.06,z+.11),(1.6,.86),blue=True)
        if back:
            for i in range(26):box('Printed code stripe',(x-.65+i*.05,y-.4,z+.114),(.018+random.random()*.018,.14,.003),M['white'],0)
        if token:
            for i in range(6):curve('Fresh reader scratches',[(x-.75+i*.065,y+.4,z+.117),(x-.57+i*.067,y+.27,z+.118)],.0035,M['metal'])


def wire():
    curve('Coiled thin steel wire',[(.78*math.cos(t),.51*math.sin(t),.055+.018*t/math.tau) for t in np.linspace(0,math.tau*2.8,230)],.012,M['metal'])
    curve('Wire end',[(.25,-.5,.08),(.5,-.9,.06),(1.12,-1.12,.05)],.012,M['metal'])
    for i in range(16):curve('Grey glove fibres',[(1.03,-1.08,.065),(1.1+random.uniform(-.15,.2),-1.1+random.uniform(-.18,.12),.075)],.004,M['fabric'])


def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()


def area(name,pos,power,color,size,target=(0,0,0)):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.color=color;data.shape='DISK';data.size=size
    o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.location=pos;aim(o,target)


def setup(e):
    global M
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=args.samples;scene.cycles.use_denoising=True
    scene.cycles.max_bounces=7;scene.cycles.transparent_max_bounces=6
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        for d in prefs.devices:d.use=d.type=='OPTIX'
        if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
    except Exception:pass
    scene.render.resolution_x=1600;scene.render.resolution_y=1000;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
    scene.world=bpy.data.worlds.new('Night ambience');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.065,.095,.095,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.12
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.2
    M={
        'black':material('Bakelite',(.018,.026,.027),.38), 'dark':material('Recesses',(.003,.005,.005)),
        'metal':textured('Brushed steel',(.37,.43,.44),140,.28,.85,stretch=(1,10,1)),
        'brass':textured('Aged brass',(.34,.21,.075),13,.35,.75),
        'ceramic':material('Warm ivory glaze',(.72,.72,.63),.16),
        'white':textured('Crystalline white',(.8,.82,.76),140,.55),
        'tea':material('Amber tea',(.055,.012,.003),.12,.05),
        'glass':material('Glass',(.83,.9,.86),.12,0,.86),
        'liquid':material('Clear remnant',(.74,.87,.83),.09,0,.9),
        'foil':textured('Creased foil',(.58,.61,.57),85,.3,.82),
        'fabric':textured('Grey woven fibre',(.12,.15,.15),180,.91),
        'leather':textured('Worn green leather',(.048,.076,.053),105,.85),
        'blue':textured('Dark blue polycarbonate',(.017,.08,.19),140,.3),
    }
    case=e['case']
    surface=textured('Dark desk timber',(.075,.035,.012),18,.66,stretch=(.15,12,2)) if case=='rain-manor' or case=='museum-example' else textured('Cold brushed tabletop',(.032,.052,.05),65,.52,.38,stretch=(.18,4,1))
    box('Investigation surface',(0,0,-.13),(14,14,.25),surface,.025)
    if case in ['rain-manor','museum-example']:
        for y in [-3,-1.65,1.65,3]:box('Desk plank seam',(0,y,.002),(14,.017,.008),M['dark'],0)
    else:
        box('Dark raised window edge',(0,3.8,.7),(12,.2,1.4),M['black'])
        for x in [-3,3]:box('Window frame',(x,3.6,1.7),(.13,.15,2.4),M['metal'])
    area('Warm practical key',(-3.5,-2,5.5),420,(1,.69,.36),2.0)
    area('Cold night window',(2.8,3.3,4.2),450 if case!='rain-manor' else 260,(.28,.58,.7),2.8)
    area('Soft readable fill',(0,-3,3.5),45,(.78,.88,.8),4.5)
    bpy.ops.object.camera_add(location=(.25,-5.7,6.8))
    cam=bpy.context.object;aim(cam,(0,0,.22));cam.data.type='PERSP';cam.data.lens=46
    cam.data.dof.use_dof=True;cam.data.dof.focus_distance=(cam.location-Vector((0,0,.2))).length;cam.data.dof.aperture_fstop=7.1
    scene.camera=cam
    return scene


def build(e):
    scene=setup(e); key=e['case']+'-'+e['id']; cid=e['case']; eid=e['id']
    if cid=='rain-manor':
        if eid=='e1':
            cup();sheet(key+'tag','茶杯现场留存',['白色结晶 / 杯底残留'],pos=(-1.45,.7,.05),size=(1.2,1.5),rot=.16)
        elif eid=='e2':
            wood=textured('Door oak',(.15,.073,.026),5,.65,stretch=(4,.1,1));box('Inner door section',(0,0,.045),(3.45,3.3,.09),wood)
            box('Intact brass escutcheon',(0,0,.14),(1.05,2.1,.13),M['brass'],.09)
            for y in [-.87,.87]:cylinder('Intact fastening',(0,y,.225),.095,.035,M['metal'])
            cylinder('Keyhole',(0,-.36,.225),.10,.014,M['black'])
            box('Keyhole throat',(0,-.49,.225),(.08,.22,.016),M['black'])
            cylinder('Key stem',(0,-.36,.47),.055,.49,M['brass'])
            ring('Key bow',(0,-.36,.75),.27,.054,M['brass'],.7)
            sphere('Door knob',(.04,.47,.43),(.32,.32,.23),M['brass'])
        elif eid=='e3':
            box('Medical case insert',(0,0,.07),(2.55,3.2,.14),M['metal'],.12)
            box('Sterile cotton',(0,0,.165),(2.3,2.95,.1),M['white'],.06);syringe((-.2,0,.22))
        elif eid=='e4':clipboard(key,'诊疗付款记录',['收款方：周砚管理的诊所','多笔诊疗款项转入','明日交警方核查'])
        elif eid=='e5':jar();sheet(key+'tag','代糖罐取样',['密封膜针孔 / 结晶留存'],pos=(-1.45,.6,.045),size=(1.15,1.5),rot=.14)
        elif eid=='e6':clipboard(key,'客房门禁记录',['21:48  周砚离开','22:06  周砚返回','22:24  林晚进入档案室','21:30 起  许知远在走廊'])
        elif eid=='e7':
            cup((-1.1,-.3,0));jar((.95,.5,0));syringe((0,-.15,.025));scene.camera.data.lens=40
        else:sheet(key,'收据背面的便笺',['不再替他遮掩。','账目和那年的事故','一起说清。'],rot=-.09);box('Receipt underneath',(.14,.1,.027),(2.45,3,.04),M['white'],.01,.035)
    elif cid=='last-train':
        if eid=='e1':
            recorder();curve('Wrist strap',[(.3,1,.12),(.92,1.3,.06),(1.24,.82,.05),(.53,.48,.08)],.022,M['black']);scene.camera.data.lens=56
        elif eid=='e2':
            curve('Grey neck pillow',[(.15+1.05*math.cos(t),.48+.8*math.sin(t),.27) for t in np.linspace(-.3,math.pi+1.5,70)],.26,M['fabric'])
            cylinder('Torn charcoal coat button',(-.45,-.6,.075),.36,.11,M['black'])
            ring('Button rim',(-.45,-.6,.132),.285,.018,M['metal'])
            for dx in [-.075,.075]:
                for dy in [-.075,.075]:cylinder('Button thread hole',(-.45+dx,-.6+dy,.138),.032,.008,M['dark'])
            for j in range(7):curve('Torn button threads',[(-.45,-.6,.145),(-.15+random.random()*.18,-.95-random.random()*.27,.04)],.006,M['fabric'])
            curve('Narrow deep pillow groove',[(.3+math.cos(t)*1.04,.48+math.sin(t)*.8,.522) for t in np.linspace(.1,1.4,45)],.026,M['black'])
        elif eid=='e3':access_card(key,broken=True);scene.camera.data.lens=56
        elif eid=='e4':
            box('Open document envelope',(.12,.18,.03),(2.85,3.6,.055),M['leather'],.01,.07)
            sheet(key,'匿名举报材料',['墨衡数据 / 乘客隐私','附：转账记录','记者署名：唐序'],rot=-.08)
        elif eid=='e5':terminal(key,'应急供电日志',['卫星授时 / 独立时钟','00:20  主电源断开','00:24  后端4号隔间门打开','00:29  主电源恢复'])
        elif eid=='e6':wire();box('Handrail seam',(.1,1.13,.22),(3.5,.27,.44),M['metal'],.04);scene.camera.data.lens=54
        elif eid=='e7':
            recorder((-1.2,0,0));sheet(key,'独立日志 · 时间核对',['录音报时  00:29','独立日志  00:24','时间误差  05:00'],pos=(.65,.1,.07),size=(1.8,2.45),rot=-.035);scene.camera.data.lens=41
        else:access_card(key,back=True);sheet(key+'record','授权记录',['门禁卡背面编号','与授权记录逐项核对'],pos=(-.38,.34,.018),size=(2.7,2.75),rot=.07)
    elif cid=='silent-station':
        if eid=='e1':terminal(key,'独立温度记录',['20:26 急降 / 20:34 危险低温','20:38 恢复'],chart=True)
        elif eid=='e2':
            box('Interlock control panel',(0,0,.12),(2.75,2.6,.23),M['metal'],.07)
            label(key,'联锁控制 / 维护旁路',(0,.73,.246),(2.25,.45))
            cylinder('Toggle socket',(0,-.1,.3),.33,.17,M['black'])
            cylinder('Toggle shaft',(0,.03,.6),.09,.6,M['metal'],(.35,0,0));sphere('Toggle tip',(0,.13,.87),(.14,.14,.2),M['black'])
            label(key+'seal','封签 / 联锁',(0,-.87,.257),(1.76,.31))
            for x in [-1.18,1.18]:
                for y in [-1.08,1.08]:cylinder('Panel screw',(x,y,.253),.07,.016,M['metal'])
        elif eid=='e3':terminal(key,'签名权限日志',['20:25  S-02 开启联锁旁路','20:26  S-02 启动强冷','本地签名 / 原始时间留存'])
        elif eid=='e4':
            sheet(key+'original','原始观测数据',['原始版本 / 待审查'],pos=(-.4,.25,.06),rot=.14)
            sheet(key,'系统维护补正',['对照版本','手工修改部分已标注'],pos=(.42,-.22,.11),size=(1.95,2.45),rot=-.12)
        elif eid=='e5':terminal(key,'定时消息任务',['消息：实验正常','20:22  创建 / 令牌 S-02','20:55  计划发送','发送身份：站长账号'])
        elif eid=='e6':
            box('Open tool pouch',(0,0,.09),(3,2.45,.16),M['fabric'],.16)
            access_card(key,token=True,pos=(0,-.1,.18))
            for i in range(30):box('Tool pouch zip tooth',(-1.32+i*.09,.94,.25),(.045,.07,.02),M['metal'],.005)
        elif eid=='e7':
            sheet(key+'temperature','独立温度记录',['20:34 危险低温'],pos=(-.76,.14,.07),size=(1.7,2.55),rot=.035,chart=True)
            sheet(key,'定时消息记录',['20:22  任务创建','20:55  计划发送'],pos=(.99,-.12,.085),size=(1.7,2.55),rot=-.04);scene.camera.data.lens=42
        else:terminal(key,'撤销请求 · 未上传',['20:39  苏遥提交撤销请求','对象：定时消息任务','网络断链 / 尚未处理'])
    else:
        if eid=='log':terminal(key,'展柜控制器',['19:12  展柜打开','使用维护卡：C-04'])
        elif eid=='glove':
            sphere('Work glove palm',(0,-.28,.17),(.48,.63,.16),M['fabric'])
            for i,x in enumerate([-.36,-.13,.12,.34]):
                curve('Glove finger',[(x,.05,.16),(x,.52+(1-abs(x))*.35,.16)],.115,M['fabric'])
            curve('Glove thumb',[(-.32,-.35,.16),(-.7,-.08,.13)],.15,M['fabric'])
            for _ in range(180):
                x=random.uniform(-.34,.34);y=random.uniform(-.68,.23)
                sphere('Silver powder',(x,y,.335),(.006,.007,.003),M['metal'])
        else:sheet(key,'收藏商收购便笺',['约定当晚收购一枚银徽章。','编号与待收购徽章一致。'],rot=-.06)
    return scene


def finish_image(path,out):
    im=Image.open(path).convert('RGB');arr=np.asarray(im).astype(np.float32)
    h,w=arr.shape[:2];yy,xx=np.mgrid[:h,:w];r=((xx-w*.5)/(w*.72))**2+((yy-h*.48)/(h*.8))**2
    vignette=1-np.clip(r*.3,0,.35)
    rng=np.random.default_rng(1909);grain=rng.normal(0,.75,(h,w,1))
    arr=np.clip(arr*vignette[:,:,None]+grain,0,255).astype('uint8')
    Image.fromarray(arr).save(out,'WEBP',quality=92,method=6)


for evidence in json.loads(args.manifest.read_text(encoding='utf-8')):
    key=evidence['case']+'-'+evidence['id']
    if args.only and key not in args.only.split(','):continue
    random.seed(sum(map(ord,key)))
    print('RENDER',key,flush=True)
    scene=build(evidence);path=args.work_dir/f'{key}.png';scene.render.filepath=str(path.resolve())
    bpy.ops.render.render(write_still=True)
    finish_image(path,args.out_dir/f'{key}.webp')
    print('SAVED',key,flush=True)
