"""The wrist build sequence: fasteners, steps, what moves in from where, joint poses and camera paths.

Edit this to change the guide. Offsets are in world millimetres (CAD pose, all joints at 0).
"""
import json, sys, numpy as np
sys.path.insert(0, '.')
from scene import parts, pose, JOINTS, rot
import gripper as GR

FPS = 30
P = parts()
STEEL = (0.32, 0.33, 0.36)

def place(seat, d):
    d = np.asarray(d, float); d /= np.linalg.norm(d); z = -d
    a = np.array([1., 0, 0]) if abs(z[0]) < 0.9 else np.array([0, 1., 0])
    x = np.cross(a, z); x /= np.linalg.norm(x); y = np.cross(z, x)
    M = np.eye(4); M[:3, 0] = x; M[:3, 1] = y; M[:3, 2] = z; M[:3, 3] = seat; return M
def trans(v): T = np.eye(4); T[:3, 3] = v; return T

# ---- fasteners (rest pose) -------------------------------------------------------------------
# group = the joint whose motion carries the fastener (None: fixed to the forearm)
F = {}
def addf(key, mesh, seat, d, group=None):
    F[key] = dict(mesh=mesh, M=place(seat, d), col=STEEL, group=group, dir=np.asarray(d, float) / np.linalg.norm(d))

# side bracket + 7 mm spacer -> wrist-flex horn: M3x12 from the outside of the bracket (x = -27.03), into the horn
for i, (y, z) in enumerate(((-197.58, 236.68), (-204.58, 229.68), (-211.58, 236.68), (-204.58, 243.68))):
    addf(f'flex_scr_{i}', 'scr_M3x12', [-27.03, y, z], [1, 0, 0], 'dof_wrist_flex')
# yaw servo -> side bracket flanges: 2x M2x6 per flange (bottom flange from below, top flange from above)
for i, y in enumerate((-192.4, -216.8)): addf(f'yawsrv_scr_b{i}', 'scr_M2x6', [-34.5, y, 218.5], [0, 0, 1], 'dof_wrist_flex')
for i, y in enumerate((-196.1, -216.8)): addf(f'yawsrv_scr_t{i}', 'scr_M2x6', [-34.5, y, 254.8], [0, 0, -1], 'dof_wrist_flex')
# end bracket + 2 mm spacer -> yaw horn: M3x6 from the inside of the bracket (z = 259.13), down into the horn
for i, (x, y) in enumerate(((-51.78, -225.15), (-44.78, -232.15), (-37.78, -225.15), (-44.78, -218.15))):
    addf(f'yaw_scr_{i}', 'scr_M3x6', [x, y, 259.13], [0, 0, -1], 'dof_wrist_yaw')
# roll servo -> end bracket tabs: one M2x6 per tab, from the outside
for i, x in enumerate((-55.0, -34.5)):
    addf(f'rollsrv_scr_f{i}', 'scr_M2x6', [x, -243.3, 270.4], [0, 1, 0], 'dof_wrist_yaw')
    addf(f'rollsrv_scr_r{i}', 'scr_M2x6', [x, -207.0, 270.4], [0, -1, 0], 'dof_wrist_yaw')

# ---- gripper on the flange (optional) ----------------------------------------------------------
HAVE_GRIPPER = GR.available()
G_ADAPTER = ['feetech_back_holder_to_horn <1>', 'horn spacer 3.5 mm <1>']
def gripper_parts(q=0.0):
    if not HAVE_GRIPPER: return {}
    W = GR.gripper_world(q); base = P['Servo Horn <1>']['M'] @ GR.flange_from_gripper()
    out = {}
    for k, (m, T, c) in W.items():
        mesh = m if (m.startswith(('scr_', 'csk_', 'nut_', 'nylock_', 'insert_', 'shoulder_'))) else 'g_' + m
        out['G/' + k] = dict(mesh=mesh, M=base @ T, col=tuple(c), group='dof_wrist_roll')
    return out
GP = gripper_parts(0.0)

COL = {k: p['col'] for k, p in P.items()}; COL.update({k: f['col'] for k, f in F.items()}); COL.update({k: g['col'] for k, g in GP.items()})
MESH = {k: p['mesh'] for k, p in P.items()}; MESH.update({k: f['mesh'] for k, f in F.items()}); MESH.update({k: g['mesh'] for k, g in GP.items()})
DIR = {k: f['dir'] for k, f in F.items()}
GROUP = {k: f['group'] for k, f in F.items()}

def world(q=None, fingers=0.0):
    """All part, fastener and gripper transforms for joint angles q (dict, rad) and gripper closing travel (mm)."""
    q = q or {}
    M, G = pose(P, q)
    for k, f in F.items(): M[k] = (G[f['group']] if f['group'] else np.eye(4)) @ f['M']
    if HAVE_GRIPPER:
        gp = gripper_parts(round(float(fingers), 1))
        for k, g in gp.items(): M[k] = G['dof_wrist_roll'] @ g['M']
    return M

def ease(t): t = min(max(t, 0), 1); return t * t * (3 - 2 * t)
def lerp(a, b, t): return np.asarray(a) * (1 - t) + np.asarray(b) * t
def sel(prefix): return [k for k in list(P) + list(F) + list(GP) if k.startswith(prefix)]
def ev(key, kf, hide=None): return dict(key=key, kf=[(float(t), list(map(float, o))) for t, o in kf], hide=hide)
def parts_in(keys, t0, t1, off): return [ev(k, [(t0, off), (t1, [0, 0, 0])]) for k in keys]
def fast_in(keys, t0, dt=0.5, stagger=0.12, dist=25, base=(0, 0, 0)):
    b = np.asarray(base, float)
    return [ev(k, [(t0 + i * stagger, b - DIR[k] * dist), (t0 + i * stagger + dt, b)]) for i, k in enumerate(keys)]

# ---- part groups ---------------------------------------------------------------------------------
STOCK_ORDER = ['Base_08q <2>', 'Base_08q <1>', 'STS3215_03a <5>', 'Rotation_Pitch_08i <1>', 'STS3215_03a <4>',
               'SO_ARM100_08k_Asym_Mirror_Clip <2>', 'SO_ARM100_08k_116_Square <1>', 'STS3215_03a <3>',
               'SO_ARM100_08k_Mirror <2>', 'SO_ARM100_08k_Asym_Mirror_Clip <1>', 'STS3215_03a <2>']
FLEX = ['horn spacer 7 mm <1>', 'STS3215_Side_bracket <1>'] + sel('flex_scr')
YAW_SERVO = ['STS3215_03a_Wrist_Roll <1>'] + sel('yawsrv_scr')
YAW = ['horn spacer 2 mm <1>', 'STS3215_End_bracket <1>'] + sel('yaw_scr')
ROLL = ['STS3215_03a_Wrist_Roll <2>', 'Servo Horn <1>'] + sel('rollsrv_scr')
ARM = STOCK_ORDER + FLEX + YAW_SERVO + YAW + ROLL
GADAPT = [k for k in GP if k[2:] in G_ADAPTER or k.startswith('G/arm_scr')]
GBODY = [k for k in GP if k not in GADAPT]

# ---- steps ------------------------------------------------------------------------------------
STEPS = []
def step(name, title, dur, base, events, cam0, cam1, q=None, qfn=None, camfn=None, fingers=0.0, ffn=None):
    STEPS.append(dict(name=name, title=title, dur=dur, base=base, events=events, cam0=cam0, cam1=cam1,
                      q=q or {}, qfn=qfn, camfn=camfn, fingers=fingers, ffn=ffn))
cam = lambda tgt, yaw, pitch, dist: dict(target=tgt, yaw=yaw, pitch=pitch, dist=dist, fov=30)
WRIST = [-38, -212, 252]

# 1 the stock SO-100, base to forearm (wrist-flex servo in the forearm)
e = []
for i, k in enumerate(STOCK_ORDER):
    t0 = 0.2 + i * 0.5
    e += parts_in([k], t0, t0 + 0.6, [0, 0, 70] if 'STS' not in k else [60, 0, 0])
step('01_so100', 'Build the SO-100 up to the forearm, wrist-flex servo included', 7.5, [], e,
     cam([0, -100, 145], -35, 20, 470), cam([0, -100, 145], -60, 20, 450))
# 2 7 mm spacer + side bracket onto the wrist-flex horn
e = parts_in(['horn spacer 7 mm <1>'], 0.2, 1.1, [-45, 0, 0]) + parts_in(['STS3215_Side_bracket <1>'], 1.2, 2.2, [-70, 0, 0]) \
    + fast_in(sel('flex_scr'), 2.6, stagger=0.2, dist=30)
step('02_flex_bracket', 'Fasten the 7 mm spacer and the side bracket to the wrist-flex horn (4× M3×12)', 5.5, STOCK_ORDER, e,
     cam(WRIST, -150, 18, 270), cam(WRIST, -168, 12, 240))
# 3 yaw servo into the side bracket
e = parts_in(['STS3215_03a_Wrist_Roll <1>'], 0.2, 1.6, [-80, 0, 0]) + fast_in(sel('yawsrv_scr_b'), 2.0, stagger=0.2) + fast_in(sel('yawsrv_scr_t'), 2.6, stagger=0.2)
step('03_yaw_servo', 'Slide the yaw servo into the side bracket and screw it down (4× M2×6)', 5.0, STOCK_ORDER + FLEX, e,
     cam(WRIST, -125, 12, 280), cam(WRIST, -110, 28, 270))
# 4 2 mm spacer + end bracket onto the yaw horn
e = parts_in(['horn spacer 2 mm <1>'], 0.2, 1.1, [0, 0, 40]) + parts_in(['STS3215_End_bracket <1>'], 1.2, 2.2, [0, 0, 70]) \
    + fast_in(sel('yaw_scr'), 2.6, stagger=0.2, dist=30)
step('04_yaw_bracket', 'Fasten the 2 mm spacer and the end bracket to the yaw horn (4× M3×6)', 5.5, STOCK_ORDER + FLEX + YAW_SERVO, e,
     cam([-45, -222, 262], -120, 40, 250), cam([-45, -222, 262], -100, 48, 235))
# 5 roll servo into the end bracket
e = parts_in(['STS3215_03a_Wrist_Roll <2>', 'Servo Horn <1>'], 0.2, 1.6, [0, 0, 80]) + fast_in(sel('rollsrv_scr_f'), 2.0, stagger=0.2) + fast_in(sel('rollsrv_scr_r'), 2.6, stagger=0.2)
step('05_roll_servo', 'Lower the roll servo into the end bracket and screw it down (4× M2×6)', 5.0, STOCK_ORDER + FLEX + YAW_SERVO + YAW, e,
     cam([-45, -225, 278], -140, 20, 290), cam([-45, -225, 278], -120, 25, 280))
# 6 check the three wrist joints by hand
def sweep(t):
    s = np.sin
    return {'dof_wrist_flex': 0.7 * s(2 * np.pi * min(t, 2.5) / 2.5) if t < 2.5 else 0.0,
            'dof_wrist_yaw': 0.9 * s(2 * np.pi * (t - 2.5) / 2.5) if 2.5 <= t < 5.0 else 0.0,
            'dof_wrist_roll': 1.6 * s(2 * np.pi * (t - 5.0) / 2.5) if 5.0 <= t < 7.5 else 0.0}
step('06_check', 'Check the wrist by hand: flex, then yaw, then roll', 7.5, ARM, [],
     cam([-40, -220, 262], -140, 22, 380), cam([-40, -220, 262], -120, 22, 380), qfn=sweep)
if HAVE_GRIPPER:
    # 7 gripper: adapter onto the roll horn first, then the gripper onto the adapter
    AW = [0, -70, 0]
    e = []
    for k in GADAPT:
        e.append(ev(k, [(0.2, np.add(AW, [0, -40, 0])), (1.0, AW), (2.6, AW), (3.6, [0, 0, 0])]))
    e += parts_in(GBODY, 3.4, 4.8, [0, -150, 0])
    step('07_gripper', 'Mount solarian-gripper1 on the roll horn (see the gripper guide)', 6.0, ARM, e,
         cam([-45, -260, 285], -150, 18, 520), cam([-45, -275, 285], -135, 20, 560))
    ALL = ARM + list(GP)
else:
    ALL = ARM
def done_q(t):
    w = 2 * np.pi * t / 8.0
    return {'dof_shoulder_pan': 0.35 * np.sin(w), 'dof_wrist_flex': 0.5 * np.sin(2 * w), 'dof_wrist_yaw': 0.6 * np.sin(w + 1),
            'dof_wrist_roll': 1.0 * np.sin(w)}
step('08_done' if HAVE_GRIPPER else '07_done', 'Done: the wrist flexes, yaws and rolls', 8.0, ALL, [],
     cam([-25, -165, 185], -40, 18, 860), cam([-25, -165, 185], -140, 18, 860), qfn=done_q,
     ffn=lambda t: 40 * 0.5 * (1 - np.cos(2 * np.pi * t / 4.0)))

def kf_offset(kf, t):
    if t <= kf[0][0]: return np.asarray(kf[0][1])
    for (t0, o0), (t1, o1) in zip(kf, kf[1:]):
        if t <= t1: return lerp(o0, o1, ease((t - t0) / max(t1 - t0, 1e-6)))
    return np.asarray(kf[-1][1])

def frames(st, every=1):
    n = int(st['dur'] * FPS); shots = []
    idx = list(range(0, n, every))
    if HAVE_GRIPPER and st['ffn']: GR.preload([st['ffn'](i / FPS) for i in idx])
    for i in idx:
        t = i / FPS; u = ease(i / (n - 1)); uc = float(st['camfn'](t)) if st['camfn'] else u
        q = st['qfn'](t) if st['qfn'] else st['q']
        fq = st['ffn'](t) if st['ffn'] else st['fingers']
        M = world(q, fq); ps = []
        for k in st['base']: ps.append(dict(mesh=MESH[k], M=[float(x) for x in M[k].ravel()], col=list(COL[k])))
        for e in st['events']:
            k = e['key']; t0 = e['kf'][0][0]
            if t < t0 or (e['hide'] is not None and t > e['hide']): continue
            T = trans(kf_offset(e['kf'], t)) @ M[k]; fade = min(1.0, (t - t0) / 0.25)
            ps.append(dict(mesh=MESH[k], M=[float(x) for x in T.ravel()], col=list(COL[k]), alpha=fade if fade < 1 else 1))
        c0, c1 = st['cam0'], st['cam1']
        c = dict(target=[float(x) for x in lerp(c0['target'], c1['target'], uc)], yaw=float(lerp(c0['yaw'], c1['yaw'], uc)),
                 pitch=float(lerp(c0['pitch'], c1['pitch'], uc)), dist=float(lerp(c0['dist'], c1['dist'], uc)), fov=30)
        shots.append(dict(file=f'{i:04d}.png', cam=c, parts=ps, bg=[1, 1, 1]))
    return shots

if __name__ == '__main__':
    only = [a for a in sys.argv[1:] if not a.startswith('--')]
    every = 1
    for a in sys.argv[1:]:
        if a.startswith('--every='): every = int(a.split('=')[1])
    for st in STEPS:
        if only and st['name'] not in only: continue
        fr = frames(st, every)
        json.dump(fr, open(f'shots_{st["name"]}.json', 'w')); print(st['name'], len(fr))
    json.dump([dict(name=s['name'], title=s['title'], dur=s['dur']) for s in STEPS], open('steps.json', 'w'), indent=1)
