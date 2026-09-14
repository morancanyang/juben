"""Render cinematic NPC portrait cards with local Blender/Cycles."""
import argparse, json, math, random
from pathlib import Path
import bpy
from mathutils import Vector
from PIL import Image, ImageDraw, ImageFont

p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--work-dir',type=Path,required=True);p.add_argument('--out-dir',type=Path,required=True);p.add_argument('--samples',type=int,default=48);p.add_argument('--only',default='');a=p.parse_args();a.work_dir.mkdir(parents=True,exist_ok=True);a.out_dir.mkdir(parents=True,exist_ok=True)
FONT='C:/Windows/Fonts/msyh.ttc'; random.seed(8842)

def mat(name,c,rough=.5,metal=0):
 m=bpy.data.materials.new(name);m.diffuse_color=(*c,1);m.use_nodes=True;s=m.node_tree.nodes.get('Principled BSDF');s.inputs['Base Color'].default_value=(*c,1);s.inputs['Roughness'].default_value=rough;s.inputs['Metallic'].default_value=metal;return m
def box(name,loc,scale,ma,bevel=.03,rot=(0,0,0)):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc,rotation=rot);o=bpy.context.object;o.name=name;o.dimensions=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(ma)
 if bevel:b=o.modifiers.new('Soft portrait edge','BEVEL');b.width=bevel;b.segments=3;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL')
 return o
def sph(name,loc,scale,ma):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,radius=1,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;o.data.materials.append(ma)
 for f in o.data.polygons:f.use_smooth=True
 return o
def cyl(name,loc,r,d,ma,rot=(0,0,0)):
 bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=r,depth=d,location=loc,rotation=rot);o=bpy.context.object;o.name=name;o.data.materials.append(ma);o.modifiers.new('Weighted normals','WEIGHTED_NORMAL');return o
def curve(name,pts,r,ma):
 d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.bevel_depth=r;d.bevel_resolution=3;s=d.splines.new('BEZIER');s.bezier_points.add(len(pts)-1)
 for b,co in zip(s.bezier_points,pts):b.co=co;b.handle_left_type='AUTO';b.handle_right_type='AUTO'
 o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);d.materials.append(ma);return o
def aim(o,t):o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler()

def setup(npc):
 bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=720;scene.render.resolution_y=900;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
 scene.world=bpy.data.worlds.new('Portrait room');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.018,.027,.027,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.22
 scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=-.15
 case=npc['case']; accent=tuple(int(npc['color'][i:i+2],16)/255 for i in (1,3,5))
 skin=mat('Skin',(0.47,.28,.2),.72); skin2=mat('Skin highlight',(.62,.39,.28),.66); hair=mat('Hair',(.025,.018,.014),.7); dark=mat('Dark',(.012,.018,.017),.46); ivory=mat('Eye white',(.72,.69,.59),.33); iris=mat('Iris',(.08,.055,.035),.32); outfit=mat('Tailored fabric',tuple(max(.03,min(.45,x*.65+.04)) for x in accent),.84); metal=mat('Profession metal',(.28,.32,.29),.3,.7); warm=mat('Warm accent',(.56,.22,.11),.46); blue=mat('Cold accent',(.07,.22,.3),.42)
 floor=mat('Backdrop',(.025,.043,.036),.8);box('Portrait backdrop',(0,.7,2.3),(5,.35,5.2),floor,.08)
 # shoulders, neck, head; role-specific silhouette is carried by hair and prop
 box('Shoulders',(0,0,1.04),(2.45,.72,1.18),outfit,.25,rot=(0,0,random.uniform(-.04,.04)));cyl('Neck',(0,-.02,1.7),.3,.45,skin)
 sph('Face',(0,-.03,2.35),(.72,.57,.84),skin2)
 # ears, nose, eyes and brows
 for x in (-.6,.6):sph('Ear',(x,-.02,2.38),(.13,.08,.2),skin)
 sph('Nose',(0,-.58,2.33),(.12,.13,.21),skin2)
 for x in (-.25,.25):
  sph('Eye',(x,-.535,2.51),(.105,.045,.09),ivory);sph('Iris',(x,-.58,2.51),(.045,.02,.045),iris)
  curve('Brow',[(x-.15,-.57,2.67),(x,-.6,2.7),(x+.15,-.57,2.67)],.025,hair)
 # hair cap and locks
 sph('Hair cap',(0,.02,2.94),(.77,.61,.48),hair)
 for x in [-.62,-.44,-.26,.26,.44,.62]:sph('Hair lock',(x,-.04,2.76+random.random()*.12),(.12,.1,.34+random.random()*.2),hair)
 role=npc['role'];rid=npc['id'];
 if '医生' in role or '站医' in role:
  box('Medical coat',(0,-.39,1.45),(1.95,.08,1.3),ivory,.08);curve('Stethoscope',[(-.35,-.47,1.88),(-.12,-.52,1.25),(.35,-.47,1.82)],.028,metal);cyl('Stethoscope chest',(0,-.52,1.22),.12,.035,metal,rot=(math.pi/2,0,0))
 elif '工程师' in role or '数据' in role:
  box('Tech collar',(0,-.46,1.65),(1.65,.12,.22),dark,.04);box('ID badge',(.45,-.55,1.42),(.32,.04,.48),blue,.02);curve('Earpiece',[(.62,-.5,2.52),(.78,-.5,2.28),(.58,-.52,2.16)],.018,metal)
 elif '学生' in role:
  box('Student knit',(0,-.44,1.52),(1.8,.12,.7),outfit,.03);box('Music book',(.82,-.58,1.4),(.48,.08,.72),ivory,.02,rot=(0,.18,-.08));curve('Headphone band',[(-.48,-.5,2.77),(0,-.58,3.24),(.48,-.5,2.77)],.025,metal)
 elif '修复师' in role:
  box('Apron',(0,-.47,1.48),(1.72,.09,.92),warm,.04);cyl('Brush handle',(.72,-.61,1.42),.035,.78,metal,rot=(0,.45,0));sph('Brush tip',(.9,-.77,1.73),(.12,.08,.1),warm)
 elif '乘务长' in role:
  box('Uniform front',(0,-.47,1.55),(1.8,.1,1.18),dark,.06);box('Rail badge',(.4,-.54,1.9),(.42,.05,.28),warm,.02);curve('Cap brim',[(-.35,-.53,3.1),(.35,-.53,3.1)],.035,warm)
 elif '收藏家' in role or '管理员' in role:
  box('Archive vest',(0,-.47,1.5),(1.72,.1,1.05),outfit,.04);box('Key ring',(.62,-.59,1.4),(.12,.05,.12),metal);curve('Key loop',[(.57,-.6,1.4),(.81,-.59,1.26),(.95,-.57,1.42)],.018,metal)
 else:
  box('Work jacket',(0,-.47,1.52),(1.78,.1,1.1),outfit,.06);box('Pocket',(.4,-.54,1.35),(.48,.03,.3),dark,.02)
 # age/expression cues: subtle cheek contour and role-specific facial details
 if rid in ('zhou','shen','lu','chen'):curve('Jaw shadow',[(-.42,-.53,2.08),(0,-.59,1.95),(.42,-.53,2.08)],.026,dark)
 if rid in ('lin','he','su','bai','an'):curve('Loose strand',[(-.64,-.1,2.94),(-.83,-.25,2.52),(-.68,-.31,2.18)],.045,hair)
 if rid=='xu':box('Repair glasses bridge',(0,-.64,2.53),(.52,.025,.04),metal,.01);curve('Glasses left',[(-.5,-.62,2.53),(-.16,-.65,2.53)],.018,metal);curve('Glasses right',[(.16,-.65,2.53),(.5,-.62,2.53)],.018,metal)
 area=lambda name,pos,pow,col,size: None
 for name,pos,pow,col,size in [('Key',( -2.4,-2.4,4.8),500,(1,.48,.25),2.5),('Rim',(2.2,1.5,4.2),650,(*accent,),2.1),('Fill',(0,-3,3.0),65,(.65,.82,.74),3.0)]:
  data=bpy.data.lights.new(name,'AREA');data.energy=pow;data.color=col;data.shape='DISK';data.size=size;o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.location=pos;aim(o,(0,0,2))
 bpy.ops.object.camera_add(location=(0,-7.1,2.4));cam=bpy.context.object;aim(cam,(0,0,2.05));cam.data.lens=58;scene.camera=cam
 return scene,accent

def finish(src,dst,npc,accent):
 im=Image.open(src).convert('RGB');w,h=im.size;d=ImageDraw.Draw(im);gold=tuple(int(x*255) for x in accent)
 d.rectangle((19,19,w-20,h-20),outline=gold,width=4);d.rectangle((31,31,w-32,h-32),outline=tuple(min(255,int(x*.55+60)) for x in gold),width=1)
 d.rectangle((0,h-150,w,h),fill=(5,10,8,220));font=ImageFont.truetype(FONT,34);small=ImageFont.truetype(FONT,22)
 d.text((46,h-126),npc['name'],font=font,fill=(233,227,204));d.text((48,h-78),npc['role'],font=small,fill=(174,190,163));d.text((w-180,h-78),'NPC / 01',font=small,fill=(155,157,132))
 im.save(dst,'WEBP',quality=90,method=6)

items=json.loads(a.manifest.read_text(encoding='utf-8'))
for npc in items:
 key=npc['case']+'-'+npc['id']
 if a.only and key not in a.only.split(','):continue
 print('RENDER',key,flush=True);scene,accent=setup(npc);raw=a.work_dir/f'{key}.png';scene.render.filepath=str(raw.resolve());bpy.ops.render.render(write_still=True);finish(raw,a.out_dir/f'{key}.webp',npc,accent);print('SAVED',key,flush=True)
