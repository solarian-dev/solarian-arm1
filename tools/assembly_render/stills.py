"""Hero, wrist and exploded-wrist renders (stills.json) plus label anchors for the exploded view (labels.json)."""
import sys, json, numpy as np; sys.path.insert(0, '.')
import anim
from anim import world, MESH, COL, P, F, GP, trans
M = world({}, 0.0)
def parts(Mx, keys, offsets=None):
    out = []
    for k in keys:
        T = Mx[k] if offsets is None else trans(offsets.get(k, [0, 0, 0])) @ Mx[k]
        out.append(dict(mesh=MESH[k], M=[float(x) for x in T.ravel()], col=list(COL[k])))
    return out
ALL = anim.ARM + list(GP)
shots = []
pose_q = {'dof_shoulder_pan': 0.25, 'dof_wrist_flex': 0.35, 'dof_wrist_yaw': 0.45, 'dof_wrist_roll': 0.3}
Mh = world(pose_q, 25.0)
shots.append(dict(file='hero.png', cam=dict(target=[-45, -205, 215], yaw=-60, pitch=18, dist=800, fov=30), parts=parts(Mh, ALL), bg=[1, 1, 1]))
shots.append(dict(file='wrist.png', cam=dict(target=[-40, -218, 262], yaw=-140, pitch=20, dist=300, fov=30), parts=parts(M, anim.ARM), bg=[1, 1, 1]))
# exploded wrist: every wrist part pulled out along its own joint axis
off = {}
for k in ['horn spacer 7 mm <1>']: off[k] = [-18, 0, 0]
for k in ['STS3215_Side_bracket <1>'] + anim.sel('flex_scr'): off[k] = [-40, 0, 0]
for k in ['STS3215_03a_Wrist_Roll <1>']: off[k] = [-75, 0, 0]
for k in anim.sel('yawsrv_scr_b'): off[k] = [-75, 0, -22]
for k in anim.sel('yawsrv_scr_t'): off[k] = [-75, 0, 14]
for k in ['horn spacer 2 mm <1>']: off[k] = [-75, 0, 32]
for k in ['STS3215_End_bracket <1>'] + anim.sel('yaw_scr'): off[k] = [-75, 0, 62]
for k in ['STS3215_03a_Wrist_Roll <2>', 'Servo Horn <1>']: off[k] = [-75, 0, 104]
for k in anim.sel('rollsrv_scr_f'): off[k] = [-75, -22, 62]
for k in anim.sel('rollsrv_scr_r'): off[k] = [-75, 22, 62]
EXP = dict(target=[-70, -200, 290], yaw=-112, pitch=12, dist=520, fov=30)
FORE = ['SO_ARM100_08k_Mirror <2>', 'SO_ARM100_08k_Asym_Mirror_Clip <1>', 'STS3215_03a <2>']
keys = FORE + anim.FLEX + anim.YAW_SERVO + anim.YAW + anim.ROLL
shots.append(dict(file='exploded_wrist.png', cam=EXP, parts=parts(M, keys, off), bg=[1, 1, 1]))
I4 = [float(x) for x in np.eye(4).ravel()]
shots.append(dict(file='plate_wrist.png', cam=dict(target=[0, 0, 0], yaw=-60, pitch=50, dist=330, fov=30),
                  parts=[dict(mesh='bedplate', M=I4, col=[0.85, 0.86, 0.88]), dict(mesh='plate_wrist', M=I4, col=[0.98, 0.6, 0.2])], bg=[1, 1, 1]))
json.dump(shots, open('stills.json', 'w'))
# label anchors: part centre (bbox of its mesh in world), in the exploded pose
import struct
def centre(k):
    d = open(f"data/{MESH[k]}.tri", 'rb').read(); v = np.frombuffer(d, '<f4').reshape(-1, 6)[:, :3]
    c = (v.min(0) + v.max(0)) / 2; T = trans(off.get(k, [0, 0, 0])) @ M[k]; return (T @ np.r_[c, 1])[:3].tolist()
LAB = [('STS3215_03a <2>', 'wrist flex servo (ID 4)'),
       ('horn spacer 7 mm <1>', 'horn spacer 7 mm (new)'),
       ('STS3215_Side_bracket <1>', 'side bracket (new)'),
       ('STS3215_03a_Wrist_Roll <1>', 'wrist yaw servo (ID 5, new)'),
       ('horn spacer 2 mm <1>', 'horn spacer 2 mm (new)'),
       ('STS3215_End_bracket <1>', 'end bracket (new)'),
       ('STS3215_03a_Wrist_Roll <2>', 'wrist roll servo (ID 6)'),
       ('SO_ARM100_08k_Mirror <2>', 'SO-100 forearm')]
json.dump(dict(cam=EXP, labels=[dict(text=t, p=centre(k)) for k, t in LAB]), open('labels.json', 'w'))
