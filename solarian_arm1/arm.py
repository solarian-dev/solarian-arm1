from solarian.core.arm_module import ArmModule
from solarian.core.ik import CartesianIKActuator, MinkIK
from solarian_feetech.actuator import FeetechServo
from solarian_arm1 import ARM_MJCF_PATH


# Solarian Arm 1 is a full 6-DOF arm (the gripper is a separate module). IK
# controls all six joints, each mapped 1:1 onto the identically named joint of
# the arm's MuJoCo model. The TCP defaults to the wrist rail ``flange``; a project mates
# a tool by passing that tool's flange-relative pose as ``ik_tcp``.
IK_JOINT_ACTUATORS = [
    "shoulder_pan", "shoulder_lift", "elbow_flex", "wrist_flex", "wrist_yaw", "wrist_roll",
]
IK_JOINT_MODEL_NAMES = IK_JOINT_ACTUATORS
IK_MJCF = ARM_MJCF_PATH

# Named joint poses (``home``, ``ground``) belong to MoveSkill, in the
# project's conf/move.yaml: this module takes joint values, not pose names.
# They are in normalized joint space ([-100, 100]; 0 == mid-range), converted
# to radians via the IK joint limits for ArmModule.moveJ (SI API).

# Per-joint position PID. Gravity-loaded joints (lift, elbow, wrist_flex) get
# stiffer P/D so the arm holds against typical tool mass; distal yaw/roll
# stay closer to the soft SO-100 defaults (P=12/D=32).
#
# Gravity joints also get a small I (P-only cannot cancel constant gravity),
# zero dead zone, and relaxed overload so a legitimate hold does not trip the
# factory 80%/2s fuse and drop Protective_Torque to 20%. Over-temp / over-current
# stay at firmware defaults.
_GRAVITY_HOLD = {
    "I_Coefficient": 3,
    "CW_Dead_Zone": 0,
    "CCW_Dead_Zone": 0,
    "Overload_Torque": 95,
    "Protective_Torque": 50,
    "Protection_Time": 254,
}

SERVO_GAINS = {
    # shoulder_pan turns the whole arm's inertia with no gravity load to settle
    # it against, so it is the one joint that must be able to sit still: with
    # I > 0 and no dead zone the integrator winds up inside the gear backlash,
    # breaks free, overshoots, and limit-cycles as a visible shake. Hence no I,
    # a 1-tick dead zone (~0.09 deg at the joint), and less D than the gravity
    # joints -- D differentiates encoder quantization into torque chatter.
    "shoulder_pan":  {
        "P_Coefficient": 22,
        "D_Coefficient": 24,
        "I_Coefficient": 0,
        "CW_Dead_Zone": 1,
        "CCW_Dead_Zone": 1,
    },
    "shoulder_lift": {"P_Coefficient": 24, "D_Coefficient": 40, **_GRAVITY_HOLD},
    "elbow_flex":    {"P_Coefficient": 22, "D_Coefficient": 40, **_GRAVITY_HOLD},
    "wrist_flex":    {"P_Coefficient": 22, "D_Coefficient": 40, **_GRAVITY_HOLD},
    "wrist_yaw":  {
        "P_Coefficient": 22,
        "D_Coefficient": 24,
        "I_Coefficient": 0,
        "CW_Dead_Zone": 1,
        "CCW_Dead_Zone": 1,
    },
    "wrist_roll":    {"P_Coefficient": 22, "D_Coefficient": 40},
}


class Arm1Module(ArmModule):
    shoulder_pan = FeetechServo(model="sts3250")
    shoulder_lift = FeetechServo(model="sts3250")
    elbow_flex = FeetechServo(model="sts3250")
    wrist_flex = FeetechServo(model="sts3250", is_continuous=True)
    wrist_yaw = FeetechServo(model="sts3215", is_continuous=True)
    wrist_roll = FeetechServo(model="sts3215", is_continuous=True)

    # Cartesian-space actuators (end-effector pose). Present because this arm
    # implements IK; ``cfg.id`` 0..5 selects the pose component x,y,z,rx,ry,rz.
    x = CartesianIKActuator()
    y = CartesianIKActuator()
    z = CartesianIKActuator()
    rx = CartesianIKActuator()
    ry = CartesianIKActuator()
    rz = CartesianIKActuator()

    # Declarative IK backend: the core builds the mink (MuJoCo) backend from this
    # spec automatically when connecting -- no build method needed.
    # ``orientation_cost`` is raised to match ``position_cost`` (both 1.0) so the
    # 6-DOF arm holds the commanded end-effector orientation firmly during pure
    # translations (otherwise nudging x/y/z lets the tool visibly rotate).
    ik_backend = MinkIK(
        mjcf=IK_MJCF,
        joints=dict(zip(IK_JOINT_ACTUATORS, IK_JOINT_MODEL_NAMES)),
        frame="flange",
        position_cost=1.0,
        orientation_cost=1.0,
    )

    def initialize(self):
        super().initialize()

        self.disable_torque()

        self.configure_components(
            {
                "Return_Delay_Time": 0,
                "Maximum_Acceleration": 254,
                "Acceleration": 254,
                "Operating_Mode": 0,
                "I_Coefficient": 0,
            },
            component_names=IK_JOINT_ACTUATORS,
        )
        for name, gains in SERVO_GAINS.items():
            self.configure_components(gains, component_names=[name])

        # Servos keep the Goal_Position from the last session, so energising
        # without latching first snaps the arm to wherever it was commanded
        # before, from wherever it is now.
        self.enable_torque_holding()
