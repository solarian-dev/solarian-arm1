import numpy as np, struct, os, json, sys
HERE=os.path.dirname(os.path.abspath(__file__))
SRC=os.environ.get('ARM_MESHES', os.path.join(HERE,'cad','meshes'))
OUT=os.environ.get('ARM_STL_OUT', os.path.join(HERE,'..','..','STL','Individual')); os.makedirs(OUT, exist_ok=True)
def read(p):
    d=open(p,'rb').read(); n=struct.unpack('<I',d[80:84])[0]
    return np.frombuffer(d[84:84+n*50],dtype=np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')]))['v'].astype(float)
def write(p,tri,name):
    n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); l=np.linalg.norm(n,axis=1,keepdims=True); n=n/np.maximum(l,1e-12)
    a=np.zeros(len(tri),dtype=np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')])); a['n']=n; a['v']=tri
    with open(p,'wb') as f: f.write(name.encode()[:80].ljust(80,b' ')); f.write(struct.pack('<I',len(tri))); f.write(a.tobytes())
def rot_to(d):  # rotation taking unit vector d to -z
    t=np.array([0,0,-1.]); v=np.cross(d,t); c=d@t
    if np.linalg.norm(v)<1e-9: return np.eye(3) if c>0 else np.diag([1,-1,-1])
    vx=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]]); return np.eye(3)+vx+vx@vx/(1+c)
def analyze(tri,d):
    R=rot_to(d); t=tri@R.T; z=t[...,2]; zmin=z.min()
    n=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]); A=np.linalg.norm(n,axis=1)/2; nn=n/np.maximum(2*A[:,None],1e-12)
    onbed=(np.abs(z-zmin)<0.05).all(1)
    contact=A[onbed & (nn[:,2]<-0.99)].sum()
    over=A[(~onbed)&(nn[:,2]<-np.cos(np.radians(45)))].sum()
    return contact,over,(t.reshape(-1,3).max(0)-t.reshape(-1,3).min(0)),R
res={}
# the parts this mod adds; the stock SO-100 parts are printed from The Robot Studio's own STLs
DEFAULT=['horn_spacer_7_mm','horn_spacer_2_mm','STS3215_Side_bracket','STS3215_End_bracket']
for arg in (sys.argv[1:] or DEFAULT):
    name,_,force=arg.partition(':')
    tri=read(f'{SRC}/{name}.stl')
    n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); A=np.linalg.norm(n,axis=1)/2; nn=n/np.maximum(2*A[:,None],1e-12)
    # candidate directions: area-weighted clusters of normals
    q=np.round(nn,2); keys,inv=np.unique(q,axis=0,return_inverse=True); w=np.bincount(inv.ravel(),A)
    cands=[keys[i]/np.linalg.norm(keys[i]) for i in np.argsort(-w)[:12] if w[i]>20]
    best=None
    if force: cands=[np.array([float(x) for x in force.split(',')])]
    for d in cands:
        c,o,ext,R=analyze(tri,d)
        score=o-1.5*c+0.2*ext[2]*10
        if best is None or score<best[0]: best=(score,d,c,o,ext,R)
    score,d,c,o,ext,R=best
    t=tri@R.T
    # rotate about z to align the longest XY extent with x (min-area rect via PCA)
    xy=t.reshape(-1,3)[:,:2]; xy0=xy-xy.mean(0); ev,evec=np.linalg.eigh(np.cov(xy0.T)); ax=evec[:,1]; ang=-np.arctan2(ax[1],ax[0])
    Rz=np.array([[np.cos(ang),-np.sin(ang),0],[np.sin(ang),np.cos(ang),0],[0,0,1]]); t=t@Rz.T
    p=t.reshape(-1,3); lo,hi=p.min(0),p.max(0); t=t-np.array([(lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2]])
    write(f'{OUT}/{name}.stl',t.astype(np.float32),f'solarian-arm1 {name} (mm, print orientation)')
    res[name]=dict(down=np.round(d,3).tolist(),contact=round(c,1),overhang=round(o,1),size=np.round(hi-lo,1).tolist())
    print(name,res[name])
old=json.load(open(os.path.join(HERE,'orient.json'))) if os.path.exists(os.path.join(HERE,'orient.json')) else {}
old.update(res); json.dump(old,open(os.path.join(HERE,'orient.json'),'w'),indent=1)
