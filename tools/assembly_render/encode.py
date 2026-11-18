"""Overlay step titles on rendered frames and encode MP4 (per step + full) and animated WebP previews."""
import json, os, subprocess, sys, shutil
from PIL import Image, ImageDraw, ImageFont
HERE=os.path.dirname(os.path.abspath(__file__))
FRAMES=sys.argv[1] if len(sys.argv)>1 else os.path.join(HERE,'frames')
OUT=sys.argv[2] if len(sys.argv)>2 else os.path.join(HERE,'..','..','docs','media','assembly')
os.makedirs(OUT,exist_ok=True)
steps=json.load(open(os.path.join(HERE,'steps.json')))
def font(sz,bold=False):
    for p in (['/usr/share/fonts/opentype/inter/Inter-SemiBold.otf'] if bold else ['/usr/share/fonts/opentype/inter/Inter-Regular.otf'])+['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']:
        if os.path.exists(p): return ImageFont.truetype(p,sz)
    return ImageFont.load_default()
F1,F2=font(30,True),font(20)
tmp=os.path.join(HERE,'_titled'); shutil.rmtree(tmp,ignore_errors=True)
lst=[]
for i,s in enumerate(steps,1):
    src=os.path.join(FRAMES,s['name']); dst=os.path.join(tmp,s['name']); os.makedirs(dst)
    for f in sorted(os.listdir(src)):
        im=Image.open(os.path.join(src,f)).convert('RGB'); d=ImageDraw.Draw(im)
        d.text((40,32),f"Step {i}" if i<len(steps) else "Done",font=F2,fill=(120,120,128))
        d.text((40,58),s['title'],font=F1,fill=(25,25,30))
        d.text((im.width-40,im.height-40),"solarian-arm1",font=F2,fill=(170,170,176),anchor='rs')
        im.save(os.path.join(dst,f))
    mp4=os.path.join(OUT,f"{s['name']}.mp4")
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','30','-i',os.path.join(dst,'%04d.png'),'-c:v','libx264','-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',mp4],check=True)
    webp=os.path.join(OUT,f"{s['name']}.webp")
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','30','-i',os.path.join(src,'%04d.png'),'-vf','fps=15,scale=640:-1:flags=lanczos','-c:v','libwebp_anim','-lossless','0','-q:v','60','-loop','0',webp],check=True)
    lst.append(mp4); print(s['name'],os.path.getsize(mp4)//1024,'KB mp4',os.path.getsize(webp)//1024,'KB webp')
with open(os.path.join(tmp,'list.txt'),'w') as f:
    for m in lst: f.write(f"file '{os.path.abspath(m)}'\n")
full=os.path.join(OUT,'assembly_full.mp4')
subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',os.path.join(tmp,'list.txt'),'-c','copy','-movflags','+faststart',full],check=True)
print('full',os.path.getsize(full)//1024,'KB')
shutil.rmtree(tmp)
