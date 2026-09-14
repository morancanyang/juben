"""Local Pillow compositor for the three cinematic case covers.

No API, network, stock art, or external textures are used. The output is a
layered, grainy matte-painting style bitmap suitable for the existing cover cards.
"""
from pathlib import Path
import math, random
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import numpy as np

random.seed(4021)
OUT = Path(__file__).resolve().parents[1] / 'web' / 'src' / 'media' / 'covers'
OUT.mkdir(parents=True, exist_ok=True)
W, H = 1600, 900

def gradient(top, bottom):
    y = np.linspace(0, 1, H)[:, None, None]
    a=np.array(top,dtype=float)[None,None,:]; b=np.array(bottom,dtype=float)[None,None,:]
    arr=np.repeat(a*(1-y)+b*y,W,axis=1)
    return Image.fromarray(np.uint8(np.clip(arr,0,255)),'RGB')

def add_vignette(im, strength=.70):
    a=np.asarray(im).astype(float); yy,xx=np.mgrid[0:H,0:W]
    r=((xx-W*.5)/(W*.7))**2+((yy-H*.5)/(H*.72))**2
    f=1-strength*np.clip(r,0,1)**1.25
    a=np.clip(a*f[...,None],0,255)
    return Image.fromarray(np.uint8(a))

def grain(im, amount=2.3):
    a=np.asarray(im).astype(np.int16)
    n=np.random.default_rng(104).normal(0,amount,(H,W,1))
    return Image.fromarray(np.uint8(np.clip(a+n,0,255))).filter(ImageFilter.GaussianBlur(.12))

def rain_layer():
    r=Image.new('RGBA',(W,H)); d=ImageDraw.Draw(r)
    for _ in range(620):
        x=random.randrange(W); y=random.randrange(H); ln=random.randrange(18,95)
        col=(150,185,176,random.randrange(14,48)); d.line((x,y,x-7,y+ln),fill=col,width=random.choice([1,1,2]))
    return r.filter(ImageFilter.GaussianBlur(.45))

def starfield():
    s=Image.new('RGBA',(W,H)); d=ImageDraw.Draw(s)
    for _ in range(240):
        x=random.randrange(W); y=random.randrange(H//2); a=random.randrange(30,130); r=random.choice([1,1,2]);d.ellipse((x-r,y-r,x+r,y+r),fill=(185,213,212,a))
    return s.filter(ImageFilter.GaussianBlur(.35))

def train():
    im=gradient((8,14,18),(19,29,31)).convert('RGBA'); d=ImageDraw.Draw(im)
    # Moon and distant night beyond the tunnel mouth.
    d.ellipse((1130,-130,1510,250),fill=(212,218,194,225)); d.ellipse((1195,-125,1510,190),fill=(8,15,18,255))
    # Tunnel arch, perspective ribs and wet rails.
    d.polygon([(220,900),(255,390),(390,205),(800,90),(1210,205),(1350,390),(1380,900)],fill=(9,13,15,255))
    for i in range(10):
        t=i/9; x=255+(1130*t); d.line((x,390-270*math.sin(t*math.pi),x-45,900),fill=(44,59,59,120),width=5)
    d.line((800,110,800,900),fill=(108,122,112,100),width=7)
    # Train body entering darkness, warm windows repeating.
    d.polygon([(0,495),(1010,460),(1310,570),(1600,690),(1600,900),(0,900)],fill=(27,39,39,255))
    d.line((0,505,1195,476),fill=(119,132,122,165),width=9);d.line((0,700,1600,745),fill=(8,15,17,240),width=13)
    for i in range(9):
        x=105+i*137; d.rounded_rectangle((x,548-i*3,x+92,635-i*2),radius=7,fill=(174,165,110,135))
        d.rectangle((x+10,558-i*3,x+82,625-i*2),fill=(213,192,130,53))
    d.ellipse((1010,520,1090,600),fill=(214,197,130,160))
    # Track glints.
    d.line((0,840,1600,825),fill=(165,158,132,105),width=4); d.line((0,865,1600,848),fill=(64,91,84,160),width=3)
    im=im.filter(ImageFilter.GaussianBlur(.35)); im=Image.alpha_composite(im,rain_layer().putalpha(0) if False else Image.new('RGBA',(W,H)))
    im=add_vignette(im.convert('RGB'),.78).convert('RGBA'); im=grain(im,2.4).convert('RGB')
    return im

def manor():
    im=gradient((10,24,27),(26,38,31)).convert('RGBA'); d=ImageDraw.Draw(im)
    # Storm sky, moon glow through clouds and mountain layers.
    glow=Image.new('RGBA',(W,H));gd=ImageDraw.Draw(glow);gd.ellipse((250,-190,1080,620),fill=(183,196,164,42));glow=glow.filter(ImageFilter.GaussianBlur(95));im=Image.alpha_composite(im,glow);d=ImageDraw.Draw(im)
    d.polygon([(0,510),(250,430),(480,500),(780,360),(1030,470),(1330,330),(1600,450),(1600,900),(0,900)],fill=(16,30,28,220))
    # Mansion silhouette and lit windows.
    d.polygon([(480,650),(480,420),(645,300),(760,370),(870,266),(1110,420),(1110,650)],fill=(11,22,21,255))
    d.polygon([(430,430),(650,250),(790,360),(925,230),(1160,430)],fill=(10,20,20,255))
    d.rectangle((690,465,780,650),fill=(36,44,35,255));d.rectangle((860,424,940,650),fill=(25,34,31,255))
    for x,y in [(545,470),(620,540),(835,470),(1005,480),(1010,555)]: d.rectangle((x,y,x+32,y+50),fill=(194,165,91,135))
    d.ellipse((740,525,783,568),fill=(220,185,96,160))
    # Lightning slit and rain curtains.
    d.line((1020,20,920,230,980,190,900,375),fill=(212,224,198,115),width=4)
    im=Image.alpha_composite(im,rain_layer()); im=add_vignette(im.convert('RGB'),.73).convert('RGBA'); return grain(im,2.8).convert('RGB')

def station():
    im=gradient((5,14,22),(32,50,56)).convert('RGBA'); im=Image.alpha_composite(im,starfield()); d=ImageDraw.Draw(im)
    # Aurora ribbons.
    aur=Image.new('RGBA',(W,H));ad=ImageDraw.Draw(aur)
    pts=[]
    for x in range(-100,1700,20): pts.append((x,185+55*math.sin(x/170)+28*math.sin(x/63)))
    ad.line(pts,fill=(105,202,174,115),width=56);ad.line([(x,y+75) for x,y in pts],fill=(78,130,168,76),width=42);aur=aur.filter(ImageFilter.GaussianBlur(24));im=Image.alpha_composite(im,aur);d=ImageDraw.Draw(im)
    # Snow plain and station module.
    d.polygon([(0,595),(400,530),(780,580),(1120,515),(1600,565),(1600,900),(0,900)],fill=(183,204,199,95))
    d.polygon([(410,650),(410,435),(800,320),(1190,435),(1190,650)],fill=(20,42,49,245));d.polygon([(800,320),(1190,435),(1190,650),(800,615)],fill=(12,28,34,255))
    d.rectangle((530,485,690,575),fill=(119,167,161,120));d.rectangle((730,452,870,560),fill=(180,203,180,145));d.rectangle((910,486,1080,578),fill=(89,145,157,115))
    for x in [560,755,940]: d.line((x,490,x+30,570),fill=(218,228,193,120),width=4)
    # Antenna and dish under polar wind.
    d.line((1025,450,1090,145),fill=(131,157,159,210),width=8);d.ellipse((1040,130,1160,185),outline=(155,185,176,185),width=6);d.line((1100,157,1200,118),fill=(160,183,174,180),width=4)
    d.line((800,350,800,185),fill=(153,181,178,180),width=7);d.ellipse((785,165,815,195),fill=(203,224,202,170))
    im=Image.alpha_composite(im,rain_layer().rotate(90,expand=False)); im=add_vignette(im.convert('RGB'),.64).convert('RGBA'); return grain(im,2.1).convert('RGB')

for name,fn in [('train',train),('manor',manor),('station',station)]:
    out=OUT/f'{name}.webp'; fn().save(out,quality=93,method=6); print(out)
