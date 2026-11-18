#!/usr/bin/env bash
# Regenerate everything derived from the Onshape export in ./cad:
#   STL/Individual (print-oriented parts), STL/Plates, docs/media stills and the wrist assembly videos.
# Needs: python3 + numpy + scipy + pillow, node + playwright (Chromium/Chrome with WebGL), ffmpeg.
# The gripper shown in the last steps comes from solarian-gripper1's own pipeline (GRIPPER_RENDER, default:
# the sibling plugin checkout); without it those steps are skipped.
set -euo pipefail
cd "$(dirname "$0")"
# animations use decimated copies of the heavy stock SO-100 meshes; stills use the full meshes
python3 decimate.py cad/meshes data_dec 0.6 20000
python3 prep.py data_dec data
if [ -d "${GRIPPER_RENDER:-../../../solarian-gripper1/tools/assembly_render}/cad/meshes" ]; then
  python3 prep.py "${GRIPPER_RENDER:-../../../solarian-gripper1/tools/assembly_render}/cad/meshes" data_g
  for f in data_g/*; do mv "$f" "data/g_$(basename "$f")"; done; rmdir data_g
fi
python3 fasteners.py
python3 orient.py
python3 plates.py ../../STL/Plates
python3 anim.py
for s in $(python3 -c "import json;print(' '.join(x['name'] for x in json.load(open('steps.json'))))"); do
  node render.mjs "shots_$s.json" "frames/$s" 1280 720
done
python3 encode.py frames ../../docs/media/assembly
python3 prep.py cad/meshes data
python3 prep.py ../../STL/Plates data_plate && mv data_plate/arm1_wrist_parts_plate_220x220.tri data/plate_wrist.tri && mv data_plate/arm1_wrist_parts_plate_220x220.edg data/plate_wrist.edg
python3 stills.py && node render.mjs stills.json stills 1600 1000
python3 labels.py stills/exploded_wrist.png stills/exploded_wrist.png
cp stills/*.png ../../docs/media/
