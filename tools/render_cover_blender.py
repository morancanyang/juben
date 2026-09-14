"""Render cinematic case cover art locally with Blender/Cycles-compatible geometry.
Usage: bpy-python tools/render_cover_blender.py --out-dir ... [--draft]
"""
import argparse, math, random
from pathlib import Path
import bpy
from mathutils import Vector

parser=argparse.ArgumentParser(); parser.add_argument('--out-dir',type=Path,required=True); parser.add_argument('--draft',action='store_true'); args=parser.parse_args(); args.out_dir.mkdir(parents=True,exist_ok=True)
random.seed(99)

def clear(): bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
def mat(name,color,rough=.5,metal=0,emit=None):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;nt=m.node_tree;bs=nt.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
 if name in {'mansion stone','wet grounds','tunnel concrete','wet rail bed','blue snow','station metal','slate roof','night train','steel','dark wood'}:
  tex=nt.nodes.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=4.5;tex.inputs['Detail'].default_value=3.2;tex.inputs['Roughness'].default_value=.72
  bump=nt.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.16;bump.inputs['Distance'].default_value=.14
  nt.links.new(tex.outputs['Fac'],bump.inputs['Height']);nt.links.new(bump.outputs['Normal'],bs.inputs['Normal'])
 if emit:
  bs.inputs['Emission Color'].default_value=(*emit[0],1);bs.inputs['Emission Strength'].default_value=emit[1]
 return m
def cube(name,loc,scale,material,bevel=.04,rot=(0,0,0)):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc,rotation=rot);o=bpy.context.object;o.name=name;o.dimensions=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material)
 if bevel:
  b=o.modifiers.new('soft edge','BEVEL');b.width=bevel;b.segments=3;o.modifiers.new('weighted normals','WEIGHTED_NORMAL')
 return o
def cyl(name,loc,r,depth,material,verts=48,rot=(0,0,0)):
 bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc,rotation=rot);o=bpy.context.object;o.name=name;o.data.materials.append(material);b=o.modifiers.new('weighted normals','WEIGHTED_NORMAL');return o
def sphere(name,loc,scale,material):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=40,ring_count=20,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;o.data.materials.append(material);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return o
def wedge(name,loc,scale,material,roof_pitch=.55):
 x,y,z=loc; sx,sy,sz=scale; h=sz*roof_pitch
 verts=[(-sx/2,-sy/2,-sz/2),(sx/2,-sy/2,-sz/2),(sx/2,sy/2,-sz/2),(-sx/2,sy/2,-sz/2),(-sx/2,-sy/2,sz/2),(sx/2,-sy/2,sz/2),(0,-sy/2,sz/2+h),(-sx/2,sy/2,sz/2),(sx/2,sy/2,sz/2),(0,sy/2,sz/2+h)]
 faces=[(0,1,2,3),(0,4,5,1),(1,5,6,2),(2,6,9,8),(3,2,8,7),(0,3,7,4),(4,7,9,6,5),(7,8,9)]
 me=bpy.data.meshes.new(name);me.from_pydata([(vx+x,vy+y,vz+z) for vx,vy,vz in verts],[],faces);me.materials.append(material);o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);be=o.modifiers.new('soft edge','BEVEL');be.width=.06;be.segments=2;return o
def curve(name,points,bevel,material):
 d=bpy.data.curves.new(name,'CURVE');d.dimensions='3D';d.bevel_depth=bevel;d.bevel_resolution=3;s=d.splines.new('BEZIER');s.bezier_points.add(len(points)-1)
 for p,co in zip(s.bezier_points,points):p.co=co;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
 o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);d.materials.append(material);return o
def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def area(name,loc,energy,color,size,target):
 d=bpy.data.lights.new(name,'AREA');d.energy=energy;d.color=color;d.shape='DISK';d.size=size;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=loc;aim(o,target);return o
def point(name,loc,energy,color):
 d=bpy.data.lights.new(name,'POINT');d.energy=energy;d.color=color;d.shadow_soft_size=1.2;o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.location=loc;return o
def setup(name):
 clear();s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1600;s.render.resolution_y=900;s.render.resolution_percentage=100;s.render.image_settings.file_format='WEBP';s.render.image_settings.color_mode='RGB';s.render.image_settings.quality=95
 s.render.film_transparent=False;s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.009,.018,.016,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.36;s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=.28
 cam_data=bpy.data.cameras.new('Cinematic camera');cam=bpy.data.objects.new('Cinematic camera',cam_data);bpy.context.collection.objects.link(cam)
 cam.location={'train':(3.8,-24,5.8),'manor':(8.5,-25,6.4),'station':(-7.5,-25,6.6)}.get(name,(0,-24,7.1));aim(cam,{'train':(0,1.5,2.1),'manor':(0,2.0,3.0),'station':(0,2.0,2.4)}.get(name,(0,0,2.7)));cam.data.lens=52;cam.data.dof.use_dof=True;cam.data.dof.focus_distance=22;cam.data.dof.aperture_fstop=4.2;s.camera=cam
 try:
  s.eevee.use_gtao=True;s.eevee.gtao_distance=3;s.eevee.gtao_factor=1.35;s.eevee.use_soft_shadows=True
 except Exception: pass
 # Keep the render path compatible with bundled bpy builds; highlight rolloff is handled by AgX.
 return s
def rain(count=450):
 rm=mat('rain silver',(0.3,.48,.45),.16,emit=((.35,.52,.48),.12))
 for _ in range(count):
  x=random.uniform(-10,10);y=random.uniform(-2,7);z=random.uniform(1,11);cyl('rain streak',(x,y,z),.008,random.uniform(.18,.5),rm,8,rot=(random.uniform(-.13,.13),random.uniform(-.13,.13),random.uniform(-.13,.13)))
def tunnel(s):
 black=mat('tunnel concrete',(.022,.032,.033),.84);steel=mat('steel',(.16,.20,.19),.28,.6);trainm=mat('night train',(.025,.075,.07),.3,.18);glass=mat('train windshield',(.015,.035,.038),.12,.25);window=mat('warm windows',(.62,.30,.08),.25,emit=((1,.34,.08),2.8));head=mat('headlight',(.9,.58,.2),.16,emit=((1,.23,.03),9));moon=mat('cold moon',(.62,.72,.68),.42,emit=((.65,.78,.72),1.8));ground=mat('wet rail bed',(.025,.045,.043),.64)
 cube('tunnel floor',(0,2,-.35),(24,28,.45),ground,0)
 cube('left tunnel wall',(-8,4,4),(1,28,10),black,0);cube('right tunnel wall',(8,4,4),(1,28,10),black,0);cube('tunnel ceiling',(0,6,10.5),(16,28,1),black,0)
 # receding arch ribs behind the locomotive
 for y in [4,7,10,13,16]:
  for x in [-6.8,6.8]: cube('tunnel rib',(x,y,4.8),(.18,.3,8.4),steel,.03,rot=(0,.18 if x<0 else -.18,0))
  cube('rib top',(0,y,8.75),(13.5,.3,.18),steel,.03)
 # locomotive front, framed in a pool of warm light
 cube('locomotive nose',(0,-1.7,2.35),(6.8,2.2,3.8),trainm,.28,rot=(0,.0,0))
 cube('sloped nose',(0,-2.78,2.55),(6.1,.28,3.0),trainm,.18,rot=(math.radians(-8),0,0))
 cube('windshield',(0,-2.96,3.15),(4.3,.08,1.15),glass,.08,rot=(math.radians(-8),0,0))
 for x in [-2.3,2.3]: cube('amber side window',(x,-2.93,2.8),(1.0,.07,.72),window,.06,rot=(math.radians(-8),0,0))
 sphere('train headlamp',(0,-3.0,1.45),(.42,.14,.42),head)
 cube('front grille',(0,-2.96,.82),(2.8,.10,.20),steel,.03)
 for x in [-1.1,-.55,0,.55,1.1]: cube('grille slot',(x,-3.04,.83),(.08,.05,.22),black,.01)
 # wet rails and sleepers lead into frame
 for x in [-1.25,1.25]: cube('rail',(x,-7,.03),(.13,25,.09),steel,.02,rot=(0,0,.012 if x<0 else -.012))
 for y in [-7,-5,-3,-1,1,3,5,7,9]: cube('sleeper',(0,y,-.01),(3.2,.16,.10),steel,.02)
 sphere('moon',(5.8,13,8.5),(1.15,1.15,1.15),moon);area('moonlight',(3,7,9),950,(.48,.66,.62),7,(0,3,2));area('headlight spill',(0,-5,2),620,(1,.28,.06),4,(0,4,0));area('carriage glow',(0,-4,4),850,(1,.30,.08),4,(0,0,2))
 rain(260);return s
def manor(s):
 sky=mat('storm sky',(.012,.035,.038),.95);wall=mat('mansion stone',(.06,.085,.078),.78);roof=mat('slate roof',(.018,.028,.028),.64);wood=mat('dark wood',(.06,.035,.022),.58);window=mat('amber windows',(.62,.28,.07),.2,emit=((1,.25,.04),2.6));ground=mat('wet grounds',(.025,.06,.052),.72)
 cube('wet grounds',(0,2,-.28),(24,24,.5),ground,0)
 cube('main manor',(0,2,2.8),(7.2,4.4,5.2),wall,.1);cube('wing left',(-5.1,2,2.35),(3.1,3.8,4.1),wall,.08);cube('wing right',(5.1,2,2.35),(3.1,3.8,4.1),wall,.08)
 wedge('main gabled roof',(0,2,5.55),(8.3,5.3,1.15),roof,.9);wedge('left roof',(-5.1,2,4.55),(3.7,4.5,.95),roof,.8);wedge('right roof',(5.1,2,4.55),(3.7,4.5,.95),roof,.8)
 cyl('tower',(-5.1,2,5.0),.92,5.0,wall,48);cyl('tower cap',(-5.1,2,7.65),1.08,.38,roof,48)
 for x in [-5.1,-3.8,-1.75,1.75,3.8,5.1]:
  cube('rain-lit window',(x,-.28,2.75),(.72,.08,1.12),window,.04);cube('window mullion',(x,-.33,2.75),(.08,.05,1.06),wood,.01);cube('window mullion',(x,-.33,2.75),(.68,.05,.08),wood,.01)
 cube('front door',(0,-.30,1.45),(1.2,.12,2.2),wood,.05);cube('door glow',(0,-.38,1.55),(.75,.04,1.65),window,.02)
 for i in range(12):
  x=random.uniform(-10,10);y=random.uniform(-4,8);z=random.uniform(.1,1.2);cube('wet stone',(x,y,z),(.3,random.uniform(.2,.7),.12),wall,.03,rot=(0,0,random.random()*math.pi))
 rain(440);area('storm fill',(0,5,9),1050,(.34,.52,.50),11,(0,2,3));area('window warmth',(0,-5,4),760,(1,.28,.06),5,(0,0,2));point('lightning',(4,3,9),2600,(.7,.84,.82));return s
def station(s):
 snow=mat('blue snow',(.22,.34,.37),.9);stationm=mat('station metal',(.055,.12,.14),.42,.55);glass=mat('observation windows',(.12,.38,.42),.12,emit=((.1,.48,.52),1.5));white=mat('snow caps',(.62,.72,.72),.88);aur=mat('aurora',(.08,.42,.28),.32,emit=((.04,.46,.22),1.7));red=mat('beacon red',(.7,.08,.03),.25,emit=((1,.06,.01),3.2))
 cube('polar snow field',(0,1,-.35),(26,26,.55),snow,0)
 cube('station body',(0,2,2.0),(8.8,4.5,3.6),stationm,.22);cube('station roof',(0,2,4.05),(9.0,4.7,.32),white,.12)
 # rounded side modules and snow drifts
 cyl('left module',(-5.0,2,2.0),1.7,3.4,stationm,48,rot=(0,math.pi/2,0));cyl('right module',(5.0,2,2.0),1.7,3.4,stationm,48,rot=(0,math.pi/2,0))
 for x in [-3.1,0,3.1]: cube('cyan station window',(x,-.30,2.25),(1.7,.10,.86),glass,.12)
 for x in [-3.1,0,3.1]: cube('window divider',(x,-.37,2.25),(.06,.04,.8),stationm,.01)
 cyl('communications mast',(3.3,2,6.3),.10,5.8,white,24);sphere('mast beacon',(3.3,2,9.25),(.2,.2,.2),red);cyl('dish mast',(5.8,2,5.6),.08,4.3,white,24,rot=(0,.25,0))
 bpy.ops.mesh.primitive_torus_add(major_radius=1.15,minor_radius=.07,major_segments=48,location=(5.95,2,7.7),rotation=(0,.5,0));bpy.context.object.data.materials.append(white)
 pts=[(x,3.3+0.45*math.sin(x/1.5),9.0+0.22*math.sin(x/2.2)) for x in [i*.5-9 for i in range(37)]];curve('green aurora',pts,.16,aur);curve('blue aurora',[(x,y+.7,z-.35) for x,y,z in pts],.08,glass)
 star=mat('stars',(.6,.8,.74),.2,emit=((.6,.8,.74),3));
 for _ in range(230): sphere('polar star',(random.uniform(-11,11),random.uniform(5,13),random.uniform(7,13)),(.018,.018,.018),star)
 # windblown snow streaks
 rain(320);area('cold moon fill',(0,5,11),980,(.42,.62,.70),9,(0,1,2));area('station window light',(0,-5,4),820,(.20,.60,.66),5,(0,0,2));return s
for name,fn in [('train',tunnel),('manor',manor),('station',station)]:
 s=setup(name);fn(s);s.render.filepath=str((args.out_dir/f'{name}.webp').resolve());bpy.ops.render.render(write_still=True);print('saved',s.render.filepath)

