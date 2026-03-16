"""Servo-saver shaft — combined re-export module.

This module provides the assembled parts for a two-piece compliant servo-saver.
It consists of two parts designed with the following rigid constraints:

1. **Total assembled height = 12.0 mm**:
   The offset base Z is set to 2.0 mm for nesting. The ShaftBody sits exactly 10.0 mm tall.
   Together they reach exactly 12.0 mm.

2. **Lego Axle cross-hole depth = 8.0 mm**:
   The Lego cross-bore is exactly 8.0 mm deep (1 Lego stud depth) into the top of the body shaft.

3. **Shaft neck extension = 5.0 mm**:
   The top of the cam to the top of the shaft maintains a strict 5.0 mm structural
   clearance so the outer spring can be compressed firmly against the servo shell.

4. **SG90 Spline insertion depth = 2.75 mm**:
   The bottom of the ShaftCrown press-fit bore is 2.75 mm deep to firmly grip the servo output gear.

Printed parts and files:

- ``ShaftCrown``: Fixed bottom gear driving the sinusoidal cam ramp.
- ``ShaftBody``: Outer body tracking the sine wave and transmitting it to a Lego axle.

For individual part previews (recommended for OCP Viewer):

    python3 shaft_crown.py
    python3 shaft_body.py

For the assembled preview:

    python3 shaft_with_saver.py
"""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from models.xlego.servos.shaft_crown import ShaftCrown  # noqa: F401
from models.xlego.servos.cam_utils import (  # noqa: F401
    SPRING_OD, SPRING_ID, SPRING_FREE_HEIGHT, SPRING_PRELOAD, SPRING_GAP,
    CAM_LIFT, CAM_R_INNER, CAM_R_OUTER, CAM_STEPS,
)
from models.xlego.servos.shaft_body import ShaftBody  # noqa: F401

__all__ = ["ShaftCrown", "ShaftBody"]

if __name__ == "__main__":
    from ocp_vscode import show

    crown = ShaftCrown()
    body  = ShaftBody()

    # ShaftBody Z=0 aligns with ShaftCrown top of disc (Z=2.0)
    # The crown cam ramp (Z 2.0→4.5) engages the body valley (underside of flange)
    offset = ShaftCrown.DISC_HEIGHT  # 2.0 mm

    show(
        crown.solid,
        body.solid.translate((0, 0, offset)),
        names=["ShaftCrown", "ShaftBody"],
        colors=["gold", "royalblue"],
    )
