"""
solarian-so106

SO-106 6-DOF arm module for the Solarian robotics framework. Joints are
Feetech STS servos; the gripper is a separate module (typically
``solarian-umi-slim``).
"""

from pathlib import Path

__version__ = "0.1.0"

#: Directory holding this plugin's simulation assets (MJCF + onshape config).
ASSETS_DIR = Path(__file__).resolve().parent / "assets"

#: Absolute path to the arm MJCF used by MinkIK and scene attachments.
ARM_MJCF_PATH = str(ASSETS_DIR / "so106.xml")

__all__ = [
    "ASSETS_DIR",
    "ARM_MJCF_PATH",
    "__version__",
]
