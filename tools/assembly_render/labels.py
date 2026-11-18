"""Draw leader-line labels on the exploded wrist render, projecting the anchors with the viewer's camera."""
import json, sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
img_path, out_path = sys.argv[1], sys.argv[2]
L = json.load(open('labels.json')); c = L['cam']
im = Image.open(img_path).convert('RGB'); W, H = im.size; d = ImageDraw.Draw(im)
def font(sz):
    for p in ('/usr/share/fonts/opentype/inter/Inter-Medium.otf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        try: return ImageFont.truetype(p, sz)
        except OSError: pass
    return ImageFont.load_default()
F = font(22)
y, p = np.radians(c['yaw']), np.radians(c['pitch']); t = np.array(c['target'], float)
eye = t + c['dist'] * np.array([np.cos(p) * np.cos(y), np.cos(p) * np.sin(y), np.sin(p)])
z = (eye - t) / np.linalg.norm(eye - t); x = np.cross([0, 0, 1], z); x /= np.linalg.norm(x); yv = np.cross(z, x)
f = 1 / np.tan(np.radians(c.get('fov', 30)) / 2)
def proj(P):
    v = np.asarray(P) - eye; cx, cy, cz = v @ x, v @ yv, v @ z
    return W / 2 + (f / (W / H) * cx / -cz) * W / 2, H / 2 - (f * cy / -cz) * H / 2
pts = [(proj(l['p']), l['text']) for l in L['labels']]
left = sorted([q for q in pts if q[0][0] < W * 0.5], key=lambda q: q[0][1])
right = sorted([q for q in pts if q[0][0] >= W * 0.5], key=lambda q: q[0][1])
for side, items in (('L', left), ('R', right)):
    n = len(items)
    for i, ((px, py), text) in enumerate(items):
        ty = max(60, min(H - 60, py))
        if i and ty < prev + 48: ty = prev + 48
        prev = ty
        tx = 40 if side == 'L' else W - 40
        tw = d.textlength(text, font=F)
        lx = tx + tw + 12 if side == 'L' else tx - tw - 12
        d.line([(px, py), (lx, ty)], fill=(150, 150, 158), width=2)
        d.ellipse([px - 5, py - 5, px + 5, py + 5], fill=(217, 72, 15))
        d.text((tx if side == 'L' else tx - tw, ty - 13), text, font=F, fill=(30, 30, 36))
im.save(out_path)
