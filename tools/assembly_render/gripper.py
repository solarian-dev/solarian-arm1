"""Pose solarian-gripper1 on the arm's flange (optional: only for the last steps and stills).

The gripper's own render pipeline (solarian-gripper1/tools/assembly_render) knows its parts, fasteners
and finger kinematics; this runs it in a subprocess and re-bases its parts onto the arm's wrist-roll horn
using the 'S106 with brackets v4 with gripper' assembly (both assemblies share feetech_back_holder_to_horn).
Set GRIPPER_RENDER to that folder; it defaults to the sibling plugin checkout.
"""
import json, os, subprocess, sys, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
GR = os.environ.get('GRIPPER_RENDER', os.path.join(HERE, '..', '..', '..', 'solarian-gripper1', 'tools', 'assembly_render'))
CAD = os.environ.get('ARM_CAD', os.path.join(HERE, 'cad'))

def available(): return os.path.exists(os.path.join(GR, 'anim.py'))

_cache = {}
def preload(qs):
    """Pose the gripper for many finger travels in one subprocess (the kinematics solve is slow to start)."""
    qs = sorted({round(float(q), 1) for q in qs} - set(_cache))
    if not qs: return
    code = ("import json,anim,sys;out={}\n"
            "for q in %r:\n M=anim.world(q);out[repr(q)]={k:[anim.MESH[k],[float(x) for x in M[k].ravel()],list(anim.COL[k])] for k in M if not k.startswith('iron_')}\n"
            "sys.stdout.write(json.dumps(out))") % (qs,)
    out = subprocess.run([sys.executable, '-c', code], cwd=GR, capture_output=True, text=True, check=True).stdout
    for q, d in json.loads(out[out.index('{'):]).items():
        _cache[float(q)] = {k: (m, np.array(T).reshape(4, 4), c) for k, (m, T, c) in d.items()}

def gripper_world(q=0.0):
    """Gripper part/fastener transforms in the gripper v5 frame: {key: (mesh, M 4x4, col)}."""
    q = round(float(q), 1)
    if q not in _cache: preload([q])
    return _cache[q]

def _occ(asm, name):
    A = json.load(open(asm)); ra = A['rootAssembly']
    inst = {i['id']: i for i in ra['instances'] + [x for s in A.get('subAssemblies', []) for x in s['instances']]}
    for o in ra['occurrences']:
        if inst[o['path'][-1]]['name'] == name:
            T = np.array(o['transform']).reshape(4, 4); T[:3, 3] *= 1000; return T
    raise KeyError(name)

def flange_from_gripper():
    """Transform taking gripper-v5 coordinates to the arm's 'Servo Horn <1>' frame (the flange)."""
    combo = os.path.join(CAD, 'assembly_arm1_v4_gripper.json')
    T_back_combo = _occ(combo, 'feetech_back_holder_to_horn <1>')
    T_horn_combo = _occ(combo, 'Servo Horn <1>')
    T_back_v5 = gripper_world(0.0)['feetech_back_holder_to_horn <1>'][1]
    return np.linalg.inv(T_horn_combo) @ T_back_combo @ np.linalg.inv(T_back_v5)
