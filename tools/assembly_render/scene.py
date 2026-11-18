"""Place every arm1_v4 part from the Onshape occurrence transforms, and pose the joints."""
import json, os, re, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
CAD = os.environ.get('ARM_CAD', os.path.join(HERE, 'cad'))
A = json.load(open(os.path.join(CAD, 'assembly_arm1_v4.json')))
RA = A['rootAssembly']
INST = {i['id']: i for i in RA['instances']}
# both STEP-imported brackets are called "Part 1" in their part studios
STUDIO = {'3b73df5e4b808747df8a2d0e': 'STS3215_Side_bracket', 'f6fb1923d6f9874f4fb0d953': 'STS3215_End_bracket'}
NICE = {'3b73df5e4b808747df8a2d0e': 'STS3215_Side_bracket <1>', 'f6fb1923d6f9874f4fb0d953': 'STS3215_End_bracket <1>'}

def clean(n): return re.sub(r'[^A-Za-z0-9_.-]+', '_', re.sub(r' <\d+>$', '', n))
def mesh_names():
    out, seen = {}, {}
    for i in RA['instances']:
        if i['type'] != 'Part': continue
        n = STUDIO.get(i['elementId']) or clean(i['name'])
        ids = seen.setdefault(n, [])
        if i['partId'] not in ids: ids.append(i['partId'])
        k = ids.index(i['partId']); out[i['id']] = n if k == 0 else f'{n}__{k + 1}'
    return out
MESH_OF = mesh_names()

PLA = (0.93, 0.93, 0.92)          # stock SO-100 printed parts
NEW = (0.98, 0.60, 0.20)          # the parts this mod adds (highlighted in the guide)
SERVO = (0.13, 0.13, 0.15)
COL = {'STS3215_03a': SERVO, 'STS3215_03a_Wrist_Roll': SERVO, 'Servo_Horn': (0.20, 0.20, 0.22),
       'STS3215_Side_bracket': (0.70, 0.72, 0.76), 'STS3215_End_bracket': (0.70, 0.72, 0.76),
       'horn_spacer_7_mm': NEW, 'horn_spacer_2_mm': NEW}

def key_of(i): return NICE.get(i['elementId'], i['name'])

def parts():
    """name -> dict(mesh, M (4x4, mm), col) in the CAD pose (all joints at 0)."""
    out = {}
    for o in RA['occurrences']:
        i = INST[o['path'][-1]]
        if i['type'] != 'Part': continue
        T = np.array(o['transform']).reshape(4, 4); T[:3, 3] *= 1000
        m = MESH_OF[i['id']]
        out[key_of(i)] = dict(mesh=m, M=T, col=COL.get(m, PLA), id=i['id'])
    return out

# --- joints ------------------------------------------------------------------------------------
# Each revolute mate gives an axis in world (CAD pose). The kinematic chain, base to flange:
CHAIN = ['dof_shoulder_pan', 'dof_shoulder_lift', 'dof_elbow_flex', 'dof_wrist_flex', 'dof_wrist_yaw', 'dof_wrist_roll']
# parts that move with each joint (everything downstream of it)
DOWN = {
 'dof_shoulder_pan':  ['Rotation_Pitch_08i <1>', 'STS3215_03a <4>', 'SO_ARM100_08k_Asym_Mirror_Clip <2>'],
 'dof_shoulder_lift': ['SO_ARM100_08k_116_Square <1>', 'STS3215_03a <3>'],
 'dof_elbow_flex':    ['SO_ARM100_08k_Mirror <2>', 'STS3215_03a <2>', 'SO_ARM100_08k_Asym_Mirror_Clip <1>', 'horn spacer 7 mm <1>'],
 'dof_wrist_flex':    ['STS3215_Side_bracket <1>', 'STS3215_03a_Wrist_Roll <1>', 'horn spacer 2 mm <1>'],
 'dof_wrist_yaw':     ['STS3215_End_bracket <1>', 'STS3215_03a_Wrist_Roll <2>'],
 'dof_wrist_roll':    ['Servo Horn <1>'],
}
def _cs(o, p):
    """Mate connector frame of occurrence path p (world, mm)."""
    T = None
    for oc in RA['occurrences']:
        if oc['path'] == p: T = np.array(oc['transform']).reshape(4, 4); T[:3, 3] *= 1000
    cs = o['mateConnectorCS']; M = np.eye(4)
    M[:3, 0] = cs['xAxis']; M[:3, 2] = cs['zAxis']; M[:3, 1] = np.cross(cs['zAxis'], cs['xAxis']); M[:3, 3] = np.array(cs['origin']) * 1000
    return T @ M
def joint_axes():
    J = {}
    for f in RA['features']:
        d = f['featureData']
        if d.get('mateType') != 'REVOLUTE': continue
        F = _cs(d['matedEntities'][0], d['matedEntities'][0]['matedOccurrence'])
        J[d['name']] = dict(origin=F[:3, 3], axis=F[:3, 2])
    return J
JOINTS = joint_axes()

def rot(axis, origin, a):
    k = np.asarray(axis, float); k /= np.linalg.norm(k); K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    R = np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = origin - R @ origin; return T

def pose(P, q):
    """q: dict joint -> angle (rad). Returns name -> world transform, and joint name -> world transform."""
    out = {k: p['M'].copy() for k, p in P.items()}; G = {}
    acc = np.eye(4)
    for j in CHAIN:
        a = q.get(j, 0.0); ax = JOINTS[j]
        o = (acc @ np.r_[ax['origin'], 1])[:3]; d = acc[:3, :3] @ ax['axis']
        acc = rot(d, o, a) @ acc; G[j] = acc.copy()
        for k in sum((DOWN[jj] for jj in CHAIN[CHAIN.index(j):]), []):
            pass
    # apply: a part's transform is the accumulated transform of the last joint upstream of it
    for idx, j in enumerate(CHAIN):
        for k in DOWN[j]:
            out[k] = G[j] @ P[k]['M']
    return out, G

if __name__ == '__main__':
    P = parts()
    for k, p in P.items(): print(f'{k:40s} {p["mesh"]:32s} {np.round(p["M"][:3, 3], 1)}')
    for j, v in JOINTS.items(): print(j, np.round(v['origin'], 1), np.round(v['axis'], 3))
