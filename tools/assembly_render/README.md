# assembly_render

Scripts that turn the Onshape assembly into the build assets in this repo:

- `STL/Individual/*.stl`: the new wrist parts, rotated onto their best face for printing
- `STL/Plates/arm1_wrist_parts_plate_220x220.stl`: those parts on one 220 × 220 mm plate
- `STEP/solarian-arm1.step`: STEP of the `arm1_v4` assembly
- `docs/media/assembly/*.mp4|webp`: the step-by-step wrist assembly animations
- `docs/media/*.png`: hero, wrist, labelled exploded wrist and plate renders

Everything is rendered headless with WebGL in Chromium, so no Blender or GPU is
needed. It is the same renderer as
[solarian-gripper1's](https://github.com/solarian-dev/solarian-gripper1/tree/main/tools/assembly_render).

## 1. Export from Onshape

Open the `solarian-arm1` Onshape document while signed in, open the browser
devtools console, paste [`onshape_export.js`](onshape_export.js) and run
`await exportArm()`. It downloads `solarian-arm1-onshape-export.zip` with:

| File | What |
| --- | --- |
| `assembly_arm1_v4.json` | assembly definition of `arm1_v4` (occurrence transforms, mates, mate connectors) |
| `assembly_arm1_v4_gripper.json` | `arm1_v4` with solarian-gripper1 mounted (only used to place the gripper on the flange) |
| `meshes/*.stl` | each part tessellated in its part-studio frame (mm) |
| `solarian-arm1.step` | STEP of `arm1_v4` (copy it to `STEP/`) |

Unzip it into `cad/`, replacing what's there. Update the element IDs at the
top of `onshape_export.js` if the assemblies are renamed or recreated.

## 2. Build

```bash
cd tools/assembly_render
./build.sh
```

Requirements: Python 3 with `numpy`, `scipy` and `pillow`, Node with
`playwright` (Chrome or Chromium with WebGL via SwiftShader is fine), and
`ffmpeg` with `libx264` and `libwebp`.

The last two steps (gripper on the flange, finished arm) and the hero still
show solarian-gripper1. They use that plugin's own render pipeline, found at
`$GRIPPER_RENDER` (default: the sibling checkout
`../../../solarian-gripper1/tools/assembly_render`). Without it, the gripper
step is skipped.

## How it works

| File | Role |
| --- | --- |
| `decimate.py` | Vertex-clustering decimation of the heavy stock SO-100 meshes, for the animations only. |
| `prep.py` | Loads STLs, writes vertex/normal buffers (`data/*.tri`) and outline edges (`data/*.edg`, B-rep face boundaries + creases > 35°). |
| `scene.py` | Places every part from the Onshape occurrence transforms, reads each revolute mate's axis and poses the six joints (`pose(P, q)`). |
| `gripper.py` | Runs the gripper's pipeline in a subprocess and re-bases its parts onto the wrist-roll horn. |
| `fasteners.py` | Procedural socket-head and countersunk screws and nuts (the CAD has no fasteners). |
| `anim.py` | The build sequence: fastener positions, then per step which parts are already in, offset keyframes for what moves in (and from where), joint poses and the camera path. Edit this to change the guide. |
| `viewer.html` + `render.mjs` | Minimal WebGL renderer (shaded + outlines) driven by Playwright; renders a JSON list of shots to PNGs. |
| `encode.py` | Adds step titles and encodes per-step MP4s, a full MP4 and 640 px animated WebP previews. |
| `orient.py` | Picks a print orientation per part (max bed contact, min overhang) and writes `STL/Individual`. Force a direction with `name:x,y,z`. |
| `plates.py` | Shelf-packs the oriented parts into the plate STL. |
| `stills.py` + `labels.py` | Hero, wrist, exploded-wrist and plate renders; `labels.py` projects part centres with the viewer's camera and draws the callouts. |

## Fastener positions

The screw positions in `anim.py` come from the CAD: the horn screws sit on the
spacers' hole pattern (four holes on a 14 mm cross around each joint axis),
and the bracket-to-servo screws on the flange holes that line up with the
servo's Ø1.5 mm case holes. Lengths follow the stack-up along each axis:

| Joint | Stack on the horn | Screw |
| --- | --- | --- |
| wrist flex | 2 mm bracket + 7 mm spacer, into a 2.5 mm horn | M3×12 |
| wrist yaw | 2 mm bracket + 2 mm spacer, into a 2.5 mm horn | M3×6 |
| brackets → servo case | 2 mm flange | M2×6 |
