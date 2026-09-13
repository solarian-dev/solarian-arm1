# solarian-so106

SO-106 6-DOF arm module for Solarian. Joints use Feetech STS servos
(`shoulder_pan`, `shoulder_lift`, `elbow_flex`, `wrist_flex`, `wrist_yaw`,
`wrist_roll`). The gripper is a separate module — typically
[`solarian-umi-slim`](https://github.com/solarian-dev/solarian-umi-slim),
mated flange-to-flange.

## Installation

```bash
pip install -e plugins/solarian-feetech
pip install -e plugins/solarian-so106
```

## Module

| Entry point | Class | Role |
|---|---|---|
| `so106-arm` | `So106ArmModule` | 6 joints + Mink IK (`x..rz`) |

Default YAML lives at `solarian_so106/conf_arm.yaml`. Copy it into a project's
`conf/` (for example `right_arm.yaml`) and set the serial port / servo ids.

```python
from solarian.core.robot import Robot
from solarian.sim import SceneConfig, ModuleAttachment
from solarian_so106 import ARM_MJCF_PATH
from solarian_so106.arm import So106ArmModule
from solarian_umi_slim import MJCF_FEETECH_PATH as UMI_SLIM_MJCF
from solarian_umi_slim.umi_slim_feetech import UmiSlimFeetechModule

class So106Robot(Robot):
    right_arm = So106ArmModule(ik_tcp=UmiSlimFeetechModule.tcp_from_flange)
    right_gripper = UmiSlimFeetechModule()
    scene = SceneConfig(
        attachments=[
            ModuleAttachment(
                module="right_arm",
                mjcf=ARM_MJCF_PATH,
                prefix="right/",
            ),
            ModuleAttachment(
                module="right_gripper",
                mjcf=UMI_SLIM_MJCF,
                parent_site="right/flange",
                child_site="flange",
                prefix="right_gripper/",
            ),
        ],
    )
```

The arm MJCF exports a `flange` site (CAD Frame). Attach a gripper by aligning
both models' `flange` frames. IK tracks `flange` plus the tool's
`tcp_from_flange` offset (CAD `tcp` in the gripper's mate frame). The scene
still attaches the gripper MJCF for physics and cameras.

## Onshape export

Re-export after a CAD change (needs Onshape API credentials):

```bash
solarian onshape-export plugins/solarian-so106/solarian_so106/assets/so106_description
solarian onshape-export plugins/solarian-so106/solarian_so106/assets/so106_description --clean-only
```

That writes `solarian_so106/assets/so106.xml`. Use `--update-yaml` to sync
joint limits into a project's arm config:

```bash
solarian onshape-export plugins/solarian-so106/solarian_so106/assets/so106_description \
    --update-yaml projects/so106/conf/right_arm.yaml
```

CAD mates should be named `shoulder_pan` … `wrist_roll`. Keep a Frame named
`flange` on the wrist for gripper attachment. Put the tool TCP Frame on the
gripper assembly (name it `tcp`), not on the arm.

`wrist_roll` is 0-centered (`±π`) in `so106.xml` / `config.json` even though
CAD exports `[-2π, 0]`. `solarian.prefer_config_limits` keeps that override
on re-export so home can roll both ways.
