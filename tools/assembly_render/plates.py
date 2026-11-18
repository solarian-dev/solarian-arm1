"""Lay out print-oriented parts on a bed (simple shelf packing) and write one combined STL per plate."""
import numpy as np, struct, sys, os, json
HERE=os.path.dirname(os.path.abspath(__file__))
STL=os.environ.get('ARM_STL_OUT', os.path.join(HERE,'..','..','STL','Individual'))
def read(p):
    d=open(p,'rb').read(); n=struct.unpack('<I',d[80:84])[0]
    return np.frombuffer(d[84:84+n*50],dtype=np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')]))['v'].astype(float)
def write(p,tri,name):
    n=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]); n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
    a=np.zeros(len(tri),dtype=np.dtype([('n','<f4',3),('v','<f4',(3,3)),('a','<u2')])); a['n']=n; a['v']=tri
    with open(p,'wb') as f: f.write(name.encode()[:80].ljust(80,b' ')); f.write(struct.pack('<I',len(tri))); f.write(a.tobytes())
def pack(items, bed, gap=6):
    # items: list of (name, tri); rotate 90deg if it helps fit; shelf packing by decreasing height(y-extent)
    placed=[]; meshes=[]
    for nm,t in items:
        p=t.reshape(-1,3); ext=p.max(0)-p.min(0)
        if ext[1]>ext[0]: t=t[...,[1,0,2]]*np.array([-1,1,1]); 
        meshes.append((nm,t))
    meshes.sort(key=lambda m: -(np.ptp(m[1].reshape(-1,3)[:,1])))
    x=y=0; shelf=0; out=[]
    for nm,t in meshes:
        p=t.reshape(-1,3); lo,hi=p.min(0),p.max(0); w,h=hi[0]-lo[0],hi[1]-lo[1]
        if x+w>bed: x=0; y+=shelf+gap; shelf=0
        if y+h>bed: raise SystemExit(f'does not fit: {nm}')
        out.append(t-np.array([lo[0]-x,lo[1]-y,lo[2]])); placed.append((nm,round(x,1),round(y,1))); x+=w+gap; shelf=max(shelf,h)
    allt=np.concatenate(out); p=allt.reshape(-1,3); c=(p.min(0)+p.max(0))/2; allt=allt-np.array([c[0],c[1],0])
    return allt, placed
if __name__=='__main__':
    out=sys.argv[1]; os.makedirs(out,exist_ok=True)
    pla=[('horn_spacer_7_mm',1),('horn_spacer_2_mm',1),('STS3215_Side_bracket',1),('STS3215_End_bracket',1)]
    items=[(f'{n}#{i}',read(f'{STL}/{n}.stl')) for n,q in pla for i in range(q)]
    t,pl=pack(items,215); write(f'{out}/arm1_wrist_parts_plate_220x220.stl',t.astype(np.float32),'solarian-arm1 wrist parts (220x220 bed)')
    print('wrist plate', np.round(np.ptp(t.reshape(-1,3),0),1), pl)
