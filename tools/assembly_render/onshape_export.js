// Export the CAD data the render pipeline needs, straight from the Onshape web app.
//
// Usage: open the solarian-arm1 Onshape document while signed in, open the
// browser devtools console, paste this file and run:
//
//   await exportArm()
//
// It downloads solarian-arm1-onshape-export.zip containing:
//   assembly_arm1_v4.json            assembly definition of arm1_v4 (occurrence transforms, mates)
//   assembly_arm1_v4_gripper.json    arm1_v4 with solarian-gripper1 mounted (only used for the final shot)
//   meshes/<part>.stl                tessellation of every part of arm1_v4, in part-studio coordinates (mm)
//   solarian-arm1.step               STEP of the arm1_v4 assembly
// Unzip it into tools/assembly_render/cad/ and run ./build.sh.

const CFG = {
  doc: 'd60e2cd05d40533c485d06e9',
  ws: '361314ab0f218f78e02b4966',
  arm: 'cf4fff8f31934d4f2d96a1b1',      // arm1_v4 (what the URDF/MJCF is exported from)
  withGripper: 'cfc6e7e995d60d18c50feb65', // S106 with brackets v4 with gripper
  // parts we print: fine tessellation. Everything else (servos, horn) is coarser.
  printed: ['Base_08q', 'Rotation_Pitch_08i', 'SO_ARM100_08k_116_Square', 'SO_ARM100_08k_Mirror',
    'SO_ARM100_08k_Asym_Mirror_Clip', 'Part 1', 'horn spacer 2 mm', 'horn spacer 7 mm'],
};

const xsrf = () => decodeURIComponent((document.cookie.split(';').map(c => c.trim())
  .find(c => c.startsWith('XSRF-TOKEN=')) || '').split('=').slice(1).join('='));
const getJSON = async (u) => (await fetch(u, { headers: { Accept: 'application/json' } })).json();
const postJSON = async (u, body) => (await fetch(u, {
  method: 'POST', body: JSON.stringify(body),
  headers: { 'Content-Type': 'application/json', Accept: 'application/json', 'X-XSRF-TOKEN': xsrf() },
})).json();
const baseName = (n) => n.replace(/ <\d+>$/, '');
const cleanName = (n) => baseName(n).replace(/[^A-Za-z0-9_.-]+/g, '_');

function partBase(i) {
  const wvm = i.documentId === CFG.doc ? `w/${CFG.ws}`
    : (i.documentVersion ? `v/${i.documentVersion}` : `m/${i.documentMicroversion}`);
  return `/api/partstudios/d/${i.documentId}/${wvm}/e/${i.elementId}`;
}

async function tessellate(i, angle, chord) {
  const q = `partId=${encodeURIComponent(i.partId)}&angleTolerance=${angle}&chordTolerance=${chord}` +
    `&outputFacetNormals=true&outputVertexNormals=false&configuration=${encodeURIComponent(i.fullConfiguration || 'default')}`;
  const bodies = await getJSON(`${partBase(i)}/tessellatedfaces?${q}`);
  const tris = bodies.flatMap(b => (b.faces || []).flatMap(f => f.facets || []));
  const buf = new ArrayBuffer(84 + 50 * tris.length), dv = new DataView(buf);
  dv.setUint32(80, tris.length, true);
  let o = 84;
  for (const t of tris) {
    for (let k = 0; k < 3; k++) dv.setFloat32(o + 4 * k, (t.normal || [0, 0, 0])[k], true); o += 12;
    for (const v of t.vertices) { for (let k = 0; k < 3; k++) dv.setFloat32(o + 4 * k, v[k] * 1000, true); o += 12; }
    o += 2;
  }
  return new Uint8Array(buf);
}

async function translate(url, body) {
  let st = await postJSON(url, body);
  while (st.requestState === 'ACTIVE') { await new Promise(r => setTimeout(r, 1000)); st = await getJSON(`/api/translations/${st.id}`); }
  if (st.requestState !== 'DONE') throw new Error(st.failureReason);
  return new Uint8Array(await (await fetch(`/api/documents/d/${st.resultDocumentId}/externaldata/${st.resultExternalDataIds[0]}`)).arrayBuffer());
}

function zip(files) { // store-only zip
  const T = new Uint32Array(256).map((_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
  const crc = (u) => { let c = 0xFFFFFFFF; for (const b of u) c = T[(c ^ b) & 0xFF] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };
  const enc = new TextEncoder(), parts = [], central = []; let off = 0;
  for (const [name, data] of files) {
    const nb = enc.encode(name), c = crc(data);
    const lh = new DataView(new ArrayBuffer(30));
    lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint32(14, c, true);
    lh.setUint32(18, data.length, true); lh.setUint32(22, data.length, true); lh.setUint16(26, nb.length, true);
    parts.push(new Uint8Array(lh.buffer), nb, data);
    const ch = new DataView(new ArrayBuffer(46));
    ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true); ch.setUint32(16, c, true);
    ch.setUint32(20, data.length, true); ch.setUint32(24, data.length, true); ch.setUint16(28, nb.length, true); ch.setUint32(42, off, true);
    central.push(new Uint8Array(ch.buffer), nb);
    off += 30 + nb.length + data.length;
  }
  const size = central.reduce((s, x) => s + x.length, 0), end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
  end.setUint32(12, size, true); end.setUint32(16, off, true);
  return new Blob([...parts, ...central, new Uint8Array(end.buffer)], { type: 'application/zip' });
}

// Both STEP-imported brackets are called "Part 1" in their part studios; name the meshes after the studio.
const STUDIO_NAMES = { '3b73df5e4b808747df8a2d0e': 'STS3215_Side_bracket', 'f6fb1923d6f9874f4fb0d953': 'STS3215_End_bracket' };
const meshName = (i) => STUDIO_NAMES[i.elementId] || cleanName(i.name);

async function exportArm({ step = true } = {}) {
  const enc = new TextEncoder(), files = [];
  const asmUrl = (e) => `/api/assemblies/d/${CFG.doc}/w/${CFG.ws}/e/${e}?includeMateFeatures=true&includeMateConnectors=true`;
  const arm = await getJSON(asmUrl(CFG.arm)), withG = await getJSON(asmUrl(CFG.withGripper));
  files.push(['assembly_arm1_v4.json', enc.encode(JSON.stringify(arm))]);
  files.push(['assembly_arm1_v4_gripper.json', enc.encode(JSON.stringify(withG))]);
  // Base_08q <1> and <2> are two different parts with the same name: the second distinct part
  // of a name gets a "__2" suffix (instance order), so the base is Base_08q + Base_08q__2.
  const parts = new Map(), seen = new Map();
  for (const i of arm.rootAssembly.instances) {
    if (i.type !== 'Part') continue;
    const n = meshName(i), ids = seen.get(n) || [];
    if (!ids.includes(i.partId)) ids.push(i.partId); seen.set(n, ids);
    const k = ids.indexOf(i.partId); parts.set(k ? `${n}__${k + 1}` : n, i);
  }
  for (const [name, i] of parts) {
    const fine = CFG.printed.includes(baseName(i.name));
    files.push([`meshes/${name}.stl`, await tessellate(i, fine ? 0.05 : 0.12, fine ? 0.00001 : 0.00004)]);
    console.log('tessellated', name);
  }
  if (step) files.push(['solarian-arm1.step', await translate(`/api/assemblies/d/${CFG.doc}/w/${CFG.ws}/e/${CFG.arm}/translations`,
    { formatName: 'STEP', storeInDocument: false, destinationName: 'solarian-arm1' })]);
  const a = document.createElement('a');
  a.href = URL.createObjectURL(zip(files)); a.download = 'solarian-arm1-onshape-export.zip';
  a.textContent = 'Download solarian-arm1-onshape-export.zip';
  Object.assign(a.style, { position: 'fixed', top: '80px', left: '50%', zIndex: 999999, background: '#d9480f', color: '#fff', padding: '12px 18px', borderRadius: '8px' });
  document.body.appendChild(a); a.click();
  return files.map(([n, d]) => `${n} ${d.length}`);
}
