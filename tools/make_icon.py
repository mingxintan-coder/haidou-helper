from PIL import Image, ImageDraw, ImageFilter
import math
S=1024
def hexpts(cx,cy,r,rot=-90):
    return [(cx+r*math.cos(math.radians(rot+60*i)), cy+r*math.sin(math.radians(rot+60*i))) for i in range(6)]
img=Image.new("RGBA",(S,S),(0,0,0,0))
# background: rounded square with vertical gradient
bg=Image.new("RGBA",(S,S))
top,bot=(28,40,66),(10,14,24)
for y in range(S):
    t=y/S; c=tuple(int(top[i]*(1-t)+bot[i]*t) for i in range(3))+(255,)
    ImageDraw.Draw(bg).line([(0,y),(S,y)],fill=c)
mask=Image.new("L",(S,S),0); ImageDraw.Draw(mask).rounded_rectangle([24,24,S-24,S-24],radius=210,fill=255)
img.paste(bg,(0,0),mask)
d=ImageDraw.Draw(img)
# glow behind hexagon
glow=Image.new("RGBA",(S,S),(0,0,0,0)); gd=ImageDraw.Draw(glow)
gd.polygon(hexpts(S/2,S/2+10,360),fill=(80,200,255,90))
glow=glow.filter(ImageFilter.GaussianBlur(60)); img=Image.alpha_composite(img,glow); d=ImageDraw.Draw(img)
# gold hexagon ring
outer=hexpts(S/2,S/2+10,370); inner=hexpts(S/2,S/2+10,300)
d.polygon(outer,fill=(214,178,104,255)); d.polygon(inner,fill=(16,24,40,255))
# inner subtle hex fill
d.polygon(hexpts(S/2,S/2+10,300),fill=(20,32,56,255))
# rising win-rate line (cyan) with glow
pts=[(300,650),(420,560),(500,610),(640,430),(720,470)]
line=Image.new("RGBA",(S,S),(0,0,0,0)); ld=ImageDraw.Draw(line)
ld.line(pts,fill=(90,220,255,255),width=58,joint="curve")
for p in pts[:-1]: ld.ellipse([p[0]-29,p[1]-29,p[0]+29,p[1]+29],fill=(90,220,255,255))
lg=line.filter(ImageFilter.GaussianBlur(18)); img=Image.alpha_composite(img,lg); img=Image.alpha_composite(img,line); d=ImageDraw.Draw(img)
# gold 4-point spark at the end
cx,cy=730,380; R,r=140,34
star=[]
for i in range(8):
    ang=math.radians(-90+45*i); rr=R if i%2==0 else r
    star.append((cx+rr*math.cos(ang),cy+rr*math.sin(ang)))
d.polygon(star,fill=(255,224,140,255))
d.ellipse([cx-26,cy-26,cx+26,cy+26],fill=(255,248,220,255))
img.save("icon_1024.png")
sizes=[16,24,32,48,64,128,256]
base=img.resize((256,256),Image.LANCZOS)
base.save("icon.ico",sizes=[(s,s) for s in sizes])
img.resize((256,256),Image.LANCZOS).save("icon.png")
prev=Image.new("RGBA",(16+24+32+48+64+128+256+80,270),(240,240,240,255))
x=10
for s in sizes:
    prev.alpha_composite(img.resize((s,s),Image.LANCZOS),(x,262-s)); x+=s+10
prev.save("icon_preview.png")
