from pathlib import Path
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'web'/'src'/'media'/'scenes'; OUT.mkdir(parents=True,exist_ok=True)
W,H=1600,900
random.seed(90213)

def grad(a,b):
 y=np.linspace(0,1,H)[:,None,None]; arr=np.repeat(np.array(a)[None,None,:]*(1-y)+np.array(b)[None,None,:]*y,W,axis=1)
 return Image.fromarray(np.uint8(np.clip(arr,0,255))).convert('RGBA')
def glow(im,box,color,blur=60):
 l=Image.new('RGBA',(W,H));d=ImageDraw.Draw(l);d.ellipse(box,fill=color);return Image.alpha_composite(im,l.filter(ImageFilter.GaussianBlur(blur)))
def particles(im,count,color,seed):
 rr=random.Random(seed); p=Image.new('RGBA',(W,H));d=ImageDraw.Draw(p)
 for _ in range(count):
  x=rr.randrange(W); y=rr.randrange(H); r=rr.choice([1,1,1,2,2,3]); a=rr.randrange(22,100); d.ellipse((x-r,y-r,x+r,y+r),fill=(*color,a))
 return Image.alpha_composite(im,p.filter(ImageFilter.GaussianBlur(.45)))
def rain(im,seed,amount=380):
 rr=random.Random(seed);p=Image.new('RGBA',(W,H));d=ImageDraw.Draw(p)
 for _ in range(amount):
  x=rr.randrange(W);y=rr.randrange(H);ln=rr.randrange(18,75);d.line((x,y,x-7,y+ln),fill=(165,190,183,rr.randrange(16,50)),width=rr.choice([1,1,2]))
 return Image.alpha_composite(im,p.filter(ImageFilter.GaussianBlur(.5)))
def snow(im,seed):
 rr=random.Random(seed);p=Image.new('RGBA',(W,H));d=ImageDraw.Draw(p)
 for _ in range(300):
  x=rr.randrange(W);y=rr.randrange(H);r=rr.choice([1,1,2,3]);d.ellipse((x-r,y-r,x+r,y+r),fill=(210,231,225,rr.randrange(20,95)))
 return Image.alpha_composite(im,p.filter(ImageFilter.GaussianBlur(.6)))
def finish(im,seed=1):
 im=Image.alpha_composite(im,Image.new('RGBA',(W,H),(4,8,7,0)))
 # Filmic grade: pull the UI-green cast toward charcoal blue shadows and warm practical highlights.
 arr=np.asarray(im.convert('RGB')).astype(float)
 lum=arr.mean(axis=2,keepdims=True)
 arr[:,:,0]*=1.06; arr[:,:,1]*=.91; arr[:,:,2]*=1.07
 warm=np.clip((lum-92)/150,0,1)
 arr[:,:,0]+=warm[:,:,0]*10; arr[:,:,1]+=warm[:,:,0]*3
 # Gentle S-curve and cinematic vignette.
 arr=arr/255.; arr=np.clip((arr-.5)*1.12+.5,0,1)*255
 yy,xx=np.mgrid[0:H,0:W]; v=((xx-W/2)/(W*.72))**2+((yy-H/2)/(H*.72))**2; arr*=1-.48*np.clip(v,0,1)[...,None]**1.18
 # Fine optical grain and a restrained halation pass around highlights.
 base=Image.fromarray(np.uint8(np.clip(arr,0,255)))
 hi=np.asarray(base).mean(axis=2); bloom=Image.fromarray(np.uint8(np.clip((hi-150)*1.7,0,255))).filter(ImageFilter.GaussianBlur(12)).convert('RGBA')
 bloom.putalpha(bloom.getchannel('R').point(lambda x:int(x*.16)))
 base=Image.alpha_composite(base.convert('RGBA'),Image.merge('RGBA',(bloom.getchannel('R'),bloom.getchannel('R'),bloom.getchannel('R'),bloom.getchannel('A'))))
 arr=np.asarray(base.convert('RGB')).astype(float); rng=np.random.default_rng(seed); arr+=rng.normal(0,1.55,(H,W,1))
 return Image.fromarray(np.uint8(np.clip(arr,0,255))).filter(ImageFilter.GaussianBlur(.13)).convert('RGB')
def frame(base, title, subtitle):
 d=ImageDraw.Draw(base); d.rectangle((0,0,W,8),fill=(151,170,124,45)); d.rectangle((0,H-7,W,H),fill=(0,0,0,80)); return base

def manor_study():
 im=grad((17,29,27),(37,42,32)); d=ImageDraw.Draw(im); im=glow(im,(770,180,1120,560),(207,183,108,38),80); d=ImageDraw.Draw(im)
 d.polygon([(0,0),(1120,0),(1040,690),(0,900)],fill=(22,31,27,255)); d.polygon([(1120,0),(1600,0),(1600,900),(1040,690)],fill=(13,22,21,255)); d.polygon([(0,900),(1040,690),(1600,900)],fill=(28,31,25,255))
 for x in range(120,1020,145): d.line((x,0,x+35,690),fill=(84,76,52,95),width=4)
 d.rectangle((1085,90,1525,590),outline=(9,15,14,255),width=22); d.line((1300,90,1300,590),fill=(8,14,13,255),width=16); d.line((1085,350,1525,330),fill=(8,14,13,255),width=14)
 d.rectangle((500,510,1210,660),fill=(39,25,18,255)); d.rectangle((560,465,720,540),fill=(30,20,16,255)); d.rectangle((745,492,820,575),fill=(215,205,169,220)); d.ellipse((770,515,804,548),fill=(75,35,19,240)); d.rectangle((960,466,1000,545),fill=(183,170,111,210)); d.line((980,465,980,420),fill=(183,170,111,180),width=4)
 d.rectangle((140,205,350,600),fill=(24,28,24,255));
 for y in range(240,590,70): d.line((160,y,330,y),fill=(77,62,42,100),width=3)
 return finish(rain(particles(im,210,(192,201,157),11),12),11)
def manor_hall():
 im=grad((11,21,21),(43,41,29));d=ImageDraw.Draw(im); im=glow(im,(840,220,1080,650),(177,155,91,35),75);d=ImageDraw.Draw(im)
 d.polygon([(0,0),(1060,0),(930,620),(0,900)],fill=(27,31,26,255));d.polygon([(1060,0),(1600,0),(1600,900),(930,620)],fill=(14,20,19,255));d.polygon([(0,900),(930,620),(1600,900)],fill=(35,33,25,255))
 for y in [120,270,420]: d.line((0,y,1600,y-70),fill=(82,77,54,70),width=3)
 d.rectangle((1070,160,1450,710),fill=(10,15,14,230));d.rectangle((1090,180,1430,710),outline=(89,75,48,150),width=8);d.rectangle((1130,430,1400,660),fill=(47,53,49,255));d.rectangle((1180,470,1350,620),fill=(89,104,96,150));
 d.rectangle((260,160,390,350),outline=(96,90,63,130),width=10);d.ellipse((294,194,356,256),outline=(186,163,91,170),width=6);d.line((325,225,325,208),fill=(220,190,105,180),width=4);d.line((325,225,346,237),fill=(220,190,105,180),width=4)
 d.rectangle((780,540,960,650),fill=(47,49,40,255));d.rectangle((820,470,920,560),fill=(19,22,19,255));d.rectangle((845,493,895,545),fill=(164,183,157,100));
 return finish(rain(particles(im,180,(188,194,150),21),22),22)
def manor_pantry():
 im=grad((19,29,26),(66,57,38));d=ImageDraw.Draw(im);im=glow(im,(550,80,1000,390),(223,193,126,40),90);d=ImageDraw.Draw(im)
 d.rectangle((0,0,W,H),fill=(30,34,28,255)); d.polygon([(0,0),(1600,0),(1300,900),(0,900)],fill=(49,48,38,255));d.polygon([(1600,0),(1600,900),(1300,900),(1300,0)],fill=(21,28,25,255));d.polygon([(0,900),(1300,900),(740,560)],fill=(68,55,39,255))
 for x in range(0,1300,105): d.line((x,0,x,900),fill=(105,97,72,70),width=2)
 d.rectangle((470,430,1190,590),fill=(107,94,69,255));d.rectangle((520,420,850,530),fill=(57,57,47,255));d.rectangle((885,410,1120,530),fill=(58,58,48,255));
 d.ellipse((625,370,770,515),fill=(142,121,84,255));d.ellipse((910,365,1055,510),fill=(142,121,84,255)); d.rectangle((652,414,744,448),fill=(219,209,179,180));d.rectangle((938,408,1028,444),fill=(219,209,179,180));
 d.rectangle((180,610,520,700),fill=(30,32,28,255));d.rectangle((230,540,380,630),fill=(75,77,67,220));d.rectangle((560,635,820,745),fill=(203,194,161,170));
 return finish(particles(im,260,(226,195,130),31),33)
def train_cabin():
 im=grad((11,20,22),(51,56,50));d=ImageDraw.Draw(im); im=glow(im,(1000,160,1500,630),(196,173,113,32),85);d=ImageDraw.Draw(im)
 d.polygon([(0,0),(1260,0),(1060,585),(0,900)],fill=(53,60,57,255));d.polygon([(1260,0),(1600,0),(1600,900),(1060,585)],fill=(25,33,34,255));d.polygon([(0,900),(1060,585),(1600,900)],fill=(46,48,43,255));
 d.rectangle((1100,90,1510,420),fill=(4,10,13,255));d.rectangle((1130,120,1480,390),fill=(3,8,11,255));d.line((1300,110,1300,410),fill=(74,83,79,180),width=12)
 d.rectangle((460,480,1040,610),fill=(81,75,64,255));d.rectangle((540,430,840,520),fill=(92,84,69,255));d.rectangle((700,385,830,450),fill=(65,60,52,255));d.ellipse((850,560,970,660),fill=(176,181,165,180));d.ellipse((880,585,930,635),fill=(20,39,51,180));d.rectangle((210,670,380,760),fill=(24,31,30,255));d.rectangle((290,630,350,690),fill=(65,129,151,180));d.rectangle((940,350,996,430),fill=(80,80,66,255));
 return finish(particles(im,170,(177,196,174),41),42)
def train_service():
 im=grad((19,29,29),(66,73,65));d=ImageDraw.Draw(im);d.polygon([(0,0),(1040,0),(920,650),(0,900)],fill=(46,54,51,255));d.polygon([(1040,0),(1600,0),(1600,900),(920,650)],fill=(22,32,33,255));d.polygon([(0,900),(920,650),(1600,900)],fill=(41,47,43,255));
 for y in range(170,670,110):d.line((0,y,1600,y-90),fill=(126,139,123,75),width=3)
 d.rectangle((570,420,1160,620),fill=(54,62,58,255));d.rectangle((625,360,940,450),fill=(80,91,79,255));d.rectangle((680,390,900,430),fill=(174,187,150,110));d.rectangle((1090,220,1440,440),fill=(12,22,23,255));d.rectangle((1130,260,1400,400),fill=(43,69,67,180));
 d.rectangle((300,690,380,760),fill=(26,37,42,255));d.polygon([(340,680),(375,650),(410,690),(385,740)],fill=(69,143,162,210));d.rectangle((980,530,1150,620),fill=(104,86,64,220));
 return finish(particles(im,210,(184,204,179),51),52)
def train_corridor():
 im=grad((10,20,22),(44,54,50));d=ImageDraw.Draw(im);d.polygon([(0,0),(480,0),(785,560),(0,900)],fill=(48,60,58,255));d.polygon([(1120,0),(1600,0),(1600,900),(815,560)],fill=(22,34,35,255));d.polygon([(0,900),(1600,900),(815,560)],fill=(40,47,43,255));d.polygon([(480,0),(1120,0),(815,560)],fill=(54,62,57,255));
 for x in [150,330,1270,1450]:d.line((x,0,815,560),fill=(116,133,124,100),width=5)
 for y in range(130,540,100):d.line((470+(y-130)*.65,y,1130-(y-130)*.65,y),fill=(112,127,118,60),width=3)
 d.rectangle((1350,220,1485,500),fill=(11,19,19,255));d.rectangle((1370,250,1465,420),fill=(99,125,112,100));d.rectangle((650,560,800,635),fill=(36,43,39,255));d.rectangle((690,530,760,570),fill=(112,169,123,180));d.line((540,670,1070,670),fill=(153,166,140,100),width=4)
 return finish(particles(im,220,(164,208,176),61),62)
def station_lab():
 im=grad((7,18,27),(39,56,60));d=ImageDraw.Draw(im); im=glow(im,(180,100,650,470),(161,211,220,32),90);d=ImageDraw.Draw(im);d.rectangle((0,0,W,H),fill=(22,38,44,255));d.polygon([(0,0),(1220,0),(1030,650),(0,900)],fill=(32,51,57,255));d.polygon([(1220,0),(1600,0),(1600,900),(1030,650)],fill=(12,27,34,255));d.polygon([(0,900),(1030,650),(1600,900)],fill=(39,54,55,255));
 d.rectangle((650,145,1130,610),fill=(9,22,28,255));d.rectangle((680,170,1100,585),outline=(118,151,151,150),width=13);d.rectangle((760,270,1020,480),fill=(44,73,78,180));d.line((710,220,1070,220),fill=(178,216,205,120),width=5);d.rectangle((250,530,520,650),fill=(56,74,74,220));d.rectangle((310,475,455,555),fill=(102,151,150,150));d.rectangle((1180,340,1320,440),fill=(42,60,62,255));d.ellipse((1220,370,1265,415),fill=(218,88,71,180));
 return finish(snow(particles(im,230,(191,228,227),71),72),72)
def station_control():
 im=grad((5,15,24),(33,52,60));d=ImageDraw.Draw(im); im=glow(im,(260,20,1120,340),(85,183,160,34),100);d=ImageDraw.Draw(im);d.rectangle((0,0,W,H),fill=(17,33,40,255));d.polygon([(0,0),(1150,0),(1020,610),(0,900)],fill=(24,46,52,255));d.polygon([(1150,0),(1600,0),(1600,900),(1020,610)],fill=(10,25,33,255));d.polygon([(0,900),(1020,610),(1600,900)],fill=(31,43,43,255));
 d.rectangle((180,110,680,390),fill=(6,20,28,255));d.rectangle((205,135,655,365),fill=(36,91,91,180));d.line((430,135,430,365),fill=(10,30,35,220),width=8);d.line((205,250,655,250),fill=(10,30,35,220),width=8);d.rectangle((760,350,1420,590),fill=(13,24,27,255));
 for i in range(4):d.rectangle((810+i*135,395,920+i*135,500),fill=(39,76,74,220));d.line((825+i*135,430,900+i*135,430),fill=(145,209,176,160),width=4);d.line((825+i*135,460,890+i*135,460),fill=(119,187,170,130),width=3)
 d.rectangle((520,650,900,735),fill=(30,39,38,255));d.ellipse((650,620,760,690),fill=(56,42,33,220));
 return finish(snow(particles(im,180,(142,223,181),81),82),82)
def station_comms():
 im=grad((7,18,24),(42,54,50));d=ImageDraw.Draw(im); im=glow(im,(840,180,1250,520),(217,169,91,36),90);d=ImageDraw.Draw(im);d.rectangle((0,0,W,H),fill=(22,33,34,255));d.polygon([(0,0),(1070,0),(980,640),(0,900)],fill=(35,51,50,255));d.polygon([(1070,0),(1600,0),(1600,900),(980,640)],fill=(16,27,29,255));d.polygon([(0,900),(980,640),(1600,900)],fill=(44,48,41,255));
 d.rectangle((180,230,700,580),fill=(17,26,27,255));d.rectangle((230,285,490,460),fill=(34,74,69,230));d.line((260,390,450,390),fill=(120,220,163,180),width=5);d.rectangle((810,180,980,700),fill=(47,57,52,255));
 for y in range(240,650,80):d.line((835,y,955,y),fill=(119,128,104,150),width=4)
 for x in [870,930,1010,1080,1160]:d.line((x,220,x,600),fill=(143,139,107,110),width=6)
 d.rectangle((1110,560,1300,665),fill=(87,72,49,255));d.rectangle((1160,520,1255,590),fill=(94,77,52,255));d.line((1240,530,1275,500),fill=(203,171,104,170),width=4)
 return finish(particles(im,260,(183,218,177),91),92)

items=[('rain-manor-study',manor_study),('rain-manor-hall',manor_hall),('rain-manor-pantry',manor_pantry),('last-train-cabin',train_cabin),('last-train-service',train_service),('last-train-corridor',train_corridor),('silent-station-lab',station_lab),('silent-station-control',station_control),('silent-station-comms',station_comms)]
for i,(name,fn) in enumerate(items):
 out=OUT/(name+'.webp'); fn().save(out,quality=93,method=6); print(out)
