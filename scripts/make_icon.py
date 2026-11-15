"""Render the approved D3 vector icon and theme-aware toolbar assets."""
from pathlib import Path
from math import cos, sin, radians
from xml.etree import ElementTree
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
out = root / "assets"
out.mkdir(exist_ok=True)
raw = Image.new('RGBA',(1024,1024),(0,0,0,0))
d=ImageDraw.Draw(raw)
svg=(root/'scripts'/'app_icon.svg').read_text(encoding='utf-8')
for element in ElementTree.fromstring(svg):
    tag=element.tag.rsplit('}',1)[-1];a=element.attrib
    if tag=='rect':
        x,y,w,h=(float(a[k])*4 for k in ('x','y','width','height'))
        d.rounded_rectangle((x,y,x+w,y+h),radius=float(a.get('rx',0))*4,
            fill=a['fill'],outline=a.get('stroke'),width=round(float(a.get('stroke-width',1))*4))
    else:
        points=[tuple(float(v)*4 for v in pair.split(',')) for pair in a['points'].split()]
        if tag=='polygon':
            d.polygon(points,fill=a['fill'])
        elif tag=='polyline':
            width=float(a['stroke-width'])*4
            d.line(points,fill=a['stroke'],width=round(width),joint='curve')
            for x,y in points:
                d.ellipse((x-width/2,y-width/2,x+width/2,y+width/2),fill=a['stroke'])
image = raw.resize((256,256), Image.Resampling.LANCZOS)
image.save(out / "app-icon.png")
image.save(out / "app-icon.ico", sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
(out / "icon-choice.txt").write_text("D3 — Outline folder; ivory background, navy folder/download arrow, red video symbol.\n",encoding="utf-8")
(out / 'app-icon.svg').write_text(svg,encoding='utf-8')
icons=out/'toolbar';icons.mkdir(exist_ok=True)


def toolbar(name, color):
    im=Image.new('RGBA',(96,96),(0,0,0,0));d=ImageDraw.Draw(im)
    def line(points,w=9):
        d.line(points,fill=color,width=w,joint='curve')
    if name=='home':
        line([(10,45),(48,12),(86,45)]);line([(22,39),(22,82),(40,82),(40,58),(57,58),(57,82),(75,82),(75,39)])
    elif name in ('back','up'):
        if name=='back':line([(78,48),(18,48)]);line([(40,22),(14,48),(40,74)])
        else:line([(48,80),(48,18)]);line([(22,40),(48,14),(74,40)])
    elif name=='refresh':
        end=radians(270)
        points=[(48+30*cos(radians(a)),50+30*sin(radians(a))) for a in range(35,271,2)]
        # End the arc exactly on its tangent-aligned arrowhead axis.
        p=(48+30*cos(end),50+30*sin(end));points.append(p)
        line(points,9)
        x,y=points[0];d.ellipse((x-4.5,y-4.5,x+4.5,y+4.5),fill=color)
        tx,ty=-sin(end),cos(end);nx,ny=-ty,tx
        tip=(p[0]+22*tx,p[1]+22*ty)
        base=(p[0]-4*tx,p[1]-4*ty)
        d.polygon([tip,(base[0]+14*nx,base[1]+14*ny),(base[0]-14*nx,base[1]-14*ny)],fill=color)
    elif name=='settings':
        d.ellipse((22,22,74,74),outline=color,width=9);d.ellipse((38,38,58,58),outline=color,width=7)
        for x1,y1,x2,y2 in [(48,8,48,24),(48,72,48,88),(8,48,24,48),(72,48,88,48),(18,18,30,30),(66,66,78,78),(18,78,30,66),(66,30,78,18)]:line([(x1,y1),(x2,y2)])
    elif name=='help':
        d.ellipse((9,9,87,87),outline=color,width=8)
        font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',66);d.text((29,5),'?',font=font,fill=color)
    elif name=='folder':
        line([(10,78),(10,24),(38,24),(46,34),(85,34),(85,78),(10,78)],7);line([(11,43),(85,43)],7)
    elif name=='download':
        line([(48,10),(48,64)]);line([(26,44),(48,66),(70,44)]);line([(14,66),(14,84),(82,84),(82,66)],7)
    elif name=='pause':
        d.rounded_rectangle((23,14,35,82),radius=3,fill=color);d.rounded_rectangle((60,14,72,82),radius=3,fill=color)
    elif name=='resume':
        d.polygon([(29,12),(79,48),(29,84)],fill=color)
    elif name=='open':
        line([(47,15),(82,15),(82,50)],8);line([(79,18),(36,61)],8);line([(50,27),(17,27),(17,81),(70,81),(70,56)],7)
    return im.resize((22,22),Image.Resampling.LANCZOS)


for name in ('home','back','up','refresh','settings','help','folder','download','pause','resume','open'):
    toolbar(name,'#60665f').save(icons/(name+'.png'))
    toolbar(name,'#bdc5c4').save(icons/(name+'-dark.png'))
    if name in ('download','pause','resume'):
        toolbar(name,'#ffffff').save(icons/(name+'-white.png'))

# Native Treeview images sit immediately after the expansion arrow.
for state in ('unchecked','checked','partial'):
    im=Image.new('RGBA',(64,64),(0,0,0,0));d=ImageDraw.Draw(im)
    d.rounded_rectangle((8,8,55,55),radius=7,outline='#9B8066',width=5,fill='#B96A37' if state!='unchecked' else None)
    if state=='checked':d.line([(19,31),(28,40),(46,21)],fill='#FFF4DE',width=6,joint='curve')
    if state=='partial':d.line([(20,32),(44,32)],fill='#FFF4DE',width=6)
    im.resize((16,16),Image.Resampling.LANCZOS).save(icons/f'check-{state}.png')
for i in range(8):
    im=Image.new('RGBA',(64,64),(0,0,0,0));d=ImageDraw.Draw(im)
    d.arc((8,8,55,55),i*45,i*45+265,fill='#BD713C',width=7)
    im.resize((16,16),Image.Resampling.LANCZOS).save(icons/f'spinner-{i}.png')
