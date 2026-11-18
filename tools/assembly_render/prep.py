"""Pre-process STL meshes: weld vertices, compute smooth/flat normals and feature edges."""
import json, struct, sys, os, numpy as np
src = sys.argv[1]; out = sys.argv[2]
os.makedirs(out, exist_ok=True)
def read_stl(p):
    d = open(p,'rb').read(); n = struct.unpack('<I', d[80:84])[0]
    a = np.frombuffer(d[84:84+n*50], dtype=np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')]))
    return a['v'].astype(np.float64)
info = {}
for f in sorted(os.listdir(src)):
    if not f.endswith('.stl'): continue
    name = f[:-4]
    tri = read_stl(os.path.join(src,f))            # (n,3,3) mm
    # weld
    flat = tri.reshape(-1,3)
    q = np.round(flat/1e-4).astype(np.int64)
    uniq, inv = np.unique(q, axis=0, return_inverse=True)
    inv = inv.reshape(-1); F = inv.reshape(-1,3)
    V = np.zeros((len(uniq),3)); V[inv] = flat
    fn = np.cross(tri[:,1]-tri[:,0], tri[:,2]-tri[:,0]); ln = np.linalg.norm(fn,axis=1); keep = ln>1e-12
    fn[keep] /= ln[keep,None]
    # edges -> faces
    e = np.concatenate([F[:,[0,1]],F[:,[1,2]],F[:,[2,0]]]); fi = np.tile(np.arange(len(F)),3)
    es = np.sort(e,axis=1); key = es[:,0]*len(V)+es[:,1]
    order = np.argsort(key); key=key[order]; es=es[order]; fi=fi[order]
    segs=[]
    i=0; n=len(key)
    starts = np.r_[0, np.nonzero(np.diff(key))[0]+1, n]
    for s,t in zip(starts[:-1],starts[1:]):
        fs = fi[s:t]
        if len(fs)==1: segs.append(es[s]); continue
        if len(fs)==2:
            c = np.dot(fn[fs[0]],fn[fs[1]])
            if c < np.cos(np.radians(35)): segs.append(es[s])
        else: segs.append(es[s])
    segs = np.array(segs, dtype=np.int64).reshape(-1,2)
    lines = V[segs].reshape(-1,3).astype(np.float32)
    # smooth-ish normals: per-face normal but averaged across vertices where angle small (crease 35deg)
    tri_n = np.repeat(fn[:,None,:],3,axis=1).astype(np.float32)
    pos = tri.astype(np.float32).reshape(-1,3)
    np.concatenate([pos, tri_n.reshape(-1,3)],axis=1).astype('<f4').tofile(os.path.join(out,name+'.tri'))
    lines.astype('<f4').tofile(os.path.join(out,name+'.edg'))
    lo, hi = tri.reshape(-1,3).min(0), tri.reshape(-1,3).max(0)
    info[name] = dict(ntri=len(tri), nseg=len(segs), lo=lo.round(3).tolist(), hi=hi.round(3).tolist())
    print(name, len(tri), len(segs), np.round(hi-lo,1))
json.dump(info, open(os.path.join(out,'meshes.json'),'w'), indent=1)
