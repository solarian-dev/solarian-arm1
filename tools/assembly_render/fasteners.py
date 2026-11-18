"""Procedural fastener meshes (.tri/.edg) in local frame: screw head top at z=0, shaft along -z."""
import numpy as np, os
import os
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'data'); os.makedirs(OUT,exist_ok=True)
def cyl(r, z0, z1, n=24, cap0=True, cap1=True):
    a=np.linspace(0,2*np.pi,n,endpoint=False); c=np.c_[np.cos(a),np.sin(a)]
    T=[];E=[]
    for i in range(n):
        j=(i+1)%n
        p00=[r*c[i,0],r*c[i,1],z0];p01=[r*c[j,0],r*c[j,1],z0];p10=[r*c[i,0],r*c[i,1],z1];p11=[r*c[j,0],r*c[j,1],z1]
        T+= [[p00,p01,p11],[p00,p11,p10]]
        if cap0: T.append([[0,0,z0],p01,p00])
        if cap1: T.append([[0,0,z1],p10,p11])
        E+= [[p00,p01],[p10,p11]]
    return T,E
def hexprism(af, z0, z1, hole=None):
    rc=af/2/np.cos(np.pi/6); a=np.arange(6)*np.pi/3+np.pi/6; c=np.c_[np.cos(a),np.sin(a)]*rc
    T=[];E=[]
    for i in range(6):
        j=(i+1)%6; p00=[*c[i],z0];p01=[*c[j],z0];p10=[*c[i],z1];p11=[*c[j],z1]
        T+=[[p00,p01,p11],[p00,p11,p10],[[0,0,z0],p01,p00],[[0,0,z1],p10,p11]]
        E+=[[p00,p01],[p10,p11],[p00,p10]]
    return T,E
def save(name,parts):
    T=[];E=[]
    for t,e in parts: T+=t;E+=e
    T=np.array(T,float);E=np.array(E,float)
    n=np.cross(T[:,1]-T[:,0],T[:,2]-T[:,0]); n/=np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-9)
    np.concatenate([T.reshape(-1,3),np.repeat(n,3,axis=0)],1).astype('<f4').tofile(f'{OUT}/{name}.tri')
    E.reshape(-1,3).astype('<f4').tofile(f'{OUT}/{name}.edg')
def cone(r0,z0,r1,z1,n=24):
    a=np.linspace(0,2*np.pi,n,endpoint=False); c=np.c_[np.cos(a),np.sin(a)]; T=[];E=[]
    for i in range(n):
        j=(i+1)%n; p00=[r0*c[i,0],r0*c[i,1],z0];p01=[r0*c[j,0],r0*c[j,1],z0];p10=[r1*c[i,0],r1*c[i,1],z1];p11=[r1*c[j,0],r1*c[j,1],z1]
        T+=[[p00,p01,p11],[p00,p11,p10],[[0,0,z1],p10,p11]]; E+=[[p10,p11]]
    return T,E
def csk(d,L,dk,name):
    # ISO 10642 countersunk: head top flush at z=0, 90 deg cone down to the shank; L includes the head
    h=(dk-d)/2
    save(name,[cone(d/2*0.95,-h,dk/2,0),cyl(d/2*0.95,-L,-h,16,cap1=False)])
def shcs(d,L,dk,k,name):
    save(name,[cyl(dk/2,0,k),cyl(d/2*0.95,-L,0,16)])   # head z in [0,k]; shaft below
for L in (5,6,8): shcs(2,L,3.8,2,f'scr_M2x{L}')
for L in (6,): shcs(3,L,5.5,3,f'scr_M3x{L}')
for L in (14,): shcs(3,L,5.5,3,f'scr_M3x{L}')
for L in (8,10,12,25): shcs(3,L,5.5,3,f'scr_M3x{L}')
shcs(5,20,8.5,5,'scr_M5x20')
for L in (10,14): csk(3,L,6.0,f'csk_M3x{L}')
# soldering iron for the heat-set inserts: tip at the origin, body along +z
save('iron',[cone(0.6,0,2.4,10),cyl(2.4,10,70),cyl(7,70,170)])
save('nut_M3',[hexprism(5.5,-2.4,0)]); save('nut_M5',[hexprism(8,-4,0)])
save('nylock_M3',[hexprism(5.5,-2.4,0),cyl(2.6,-4,-2.4)])
# shoulder screws: head 7x3, shoulder d4 length Ls, thread M3 x 4
for Ls in (6,10): save(f'shoulder_4x{Ls}',[cyl(3.5,0,3),cyl(2,-Ls,0),cyl(1.45,-Ls-4,-Ls,16)])
save('insert_M3',[cyl(2.35,-4,0,20)])
print('ok')

# 220x220 bed plate used for print previews
s=110; z=-0.3
v=np.array([[-s,-s,z],[s,-s,z],[s,s,z],[-s,-s,z],[s,s,z],[-s,s,z]],dtype='<f4'); n=np.tile([0,0,1],(6,1)).astype('<f4')
np.concatenate([v,n],1).tofile(f'{OUT}/bedplate.tri')
L=[]
for x in range(-110,111,20): L+=[[x,-s,z+0.05],[x,s,z+0.05],[-s,x,z+0.05],[s,x,z+0.05]]
np.array(L,dtype='<f4').tofile(f'{OUT}/bedplate.edg')
