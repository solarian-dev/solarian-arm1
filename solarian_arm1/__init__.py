"""
solarian-arm1

A 6-DOF arm module for Solarian: a mod of The Robot Studio SO-100 that adds
one degree of freedom in the wrist. Joints are Feetech STS servos. A gripper
is a separate module; the project passes that tool's flange-relative TCP as
``Arm1Module(ik_tcp=...)``.
"""

from pathlib import Path

__version__ = "0.2.0"

#: Directory holding this plugin's simulation assets (MJCF + onshape config).
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

#: Absolute path to the arm MJCF used by MinkIK and scene attachments.
ARM_MJCF_PATH = str(ASSETS_DIR / "arm1.xml")

__all__ = [
    "ASSETS_DIR",
    "ARM_MJCF_PATH",
    "__version__",
]
