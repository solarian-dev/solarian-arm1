"""Vertex-clustering decimation of the heavy stock meshes, for the animations only (print files are untouched)."""
import sys, os, struct, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
def read(p):
    d = open(p, 'rb').read(); n = struct.unpack('<I', d[80:84])[0]
    return np.frombuffer(d[84:84 + n * 50], dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')]))['v'].astype(float)
def write(p, tri):
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    a = np.zeros(len(tri), dtype=np.dtype([('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')])); a['n'] = n; a['v'] = tri
    with open(p, 'wb') as f: f.write(b'decimated'.ljust(80, b' ')); f.write(struct.pack('<I', len(tri))); f.write(a.tobytes())
def decimate(tri, cell):
    v = tri.reshape(-1, 3); key = np.floor(v / cell).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.ravel()
    cnt = np.bincount(inv); rep = np.zeros((cnt.size, 3))
    for k in range(3): rep[:, k] = np.bincount(inv, v[:, k]) / cnt
    F = inv.reshape(-1, 3); ok = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])
    F = np.unique(np.sort(F[ok], axis=1), axis=0, return_index=True)[1]; Fo = inv.reshape(-1, 3)[ok][np.sort(F)]
    return rep[Fo]
src, dst, cell, minimum = sys.argv[1], sys.argv[2], float(sys.argv[3]), int(sys.argv[4])
os.makedirs(dst, exist_ok=True)
for f in sorted(os.listdir(src)):
    if not f.endswith('.stl'): continue
    t = read(os.path.join(src, f))
    out = decimate(t, cell) if len(t) > minimum else t
    write(os.path.join(dst, f), out); print(f, len(t), '->', len(out))
