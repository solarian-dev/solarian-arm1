# solarian-arm1

solarian-arm1 is a 6-DOF arm module for Solarian. It is a modification of an
existing open-source arm, the [SO-100 by The Robot Studio](https://github.com/TheRobotStudio/SO-ARM100).
The mod adds one degree of freedom in the wrist, a yaw joint the original design
does not have. Joints use Feetech STS servos
(`shoulder_pan`, `shoulder_lift`, `elbow_flex`, `wrist_flex`, `wrist_yaw`,
`wrist_roll`). The gripper is a separate module — typically
[`solarian-gripper1`](https://github.com/solarian-dev/solarian-gripper1),
mated flange-to-flange.

## Installation

```bash
pip install -e plugins/solarian-feetech
pip install -e plugins/solarian-arm1
```

## Module

| Entry point | Class | Role |
|---|---|---|
| `arm-1` | `Arm1Module` | 6 joints + Mink IK (`x..rz`) |

Default YAML lives at `solarian_arm_1/conf_arm.yaml`. Copy it into a project's
`conf/` (for example `right_arm.yaml`) and set the serial port / servo ids.

```python
from solarian.core.robot import Robot
from solarian.sim import SceneConfig, ModuleAttachment
from solarian_arm_1 import ARM_MJCF_PATH
from solarian_arm_1.arm import Arm1Module
from solarian_gripper_1 import MJCF_FEETECH_PATH as GRIPPER_MJCF
from solarian_gripper_1.gripper_feetech import Gripper1FeetechModule

class Arm1Robot(Robot):
    right_arm = Arm1Module(ik_tcp=Gripper1FeetechModule.tcp_from_flange)
    right_gripper = Gripper1FeetechModule()
    scene = SceneConfig(
        attachments=[
            ModuleAttachment(
                module="right_arm",
                mjcf=ARM_MJCF_PATH,
                prefix="right/",
            ),
            ModuleAttachment(
                module="right_gripper",
                mjcf=GRIPPER_MJCF,
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
solarian onshape-export plugins/solarian-arm1/solarian_arm_1/assets/arm1_description
solarian onshape-export plugins/solarian-arm1/solarian_arm_1/assets/arm1_description --clean-only
```

That writes `solarian_arm_1/assets/arm1.xml`. Use `--update-yaml` to sync
joint limits into a project's arm config:

```bash
solarian onshape-export plugins/solarian-arm1/solarian_arm_1/assets/arm1_description \
    --update-yaml projects/arm1/conf/modules/right_arm.yaml
```

CAD mates should be named `shoulder_pan` … `wrist_roll`. Keep a Frame named
`flange` on the wrist for gripper attachment. Put the tool TCP Frame on the
gripper assembly (name it `tcp`), not on the arm.

`wrist_roll` is 0-centered (`±π`) in `arm1.xml` / `config.json` even though
CAD exports `[-2π, 0]`. `solarian.prefer_config_limits` keeps that override
on re-export so home can roll both ways.

## License

[Apache License 2.0](LICENSE). Copyright 2026 PrimaryKey Inc. The mechanical
design and meshes in `solarian_arm_1/assets/` are derived from the
[SO-ARM100](https://github.com/TheRobotStudio/SO-ARM100) by The Robot Studio
(Apache 2.0) and modified; see [NOTICE](NOTICE). solarian-arm1 is not
affiliated with, sponsored by, or endorsed by The Robot Studio or Hugging Face.

Solarian, Solarian Arm and the Solarian logo are trademarks of PrimaryKey Inc.
See the [trademark policy](https://github.com/solarian-dev/solarian/blob/main/TRADEMARKS.md).
