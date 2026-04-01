# This file is part of vibe-cading.
#
# vibe-cading is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# vibe-cading is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Matched (Option A) slipper gear variant."""

from models.xlego.slipper_gear.directional.base import SlipperGearBase

class SlipperGearMatched(SlipperGearBase):
    """Option A (Matched Pitch): 3-ramps, 3-arms, perfectly matched spiral pitches.

    The spring will lay flush against the entire length of the ramp for maximum
    contact area and high torque, but engages only 3 times per revolution.
    """
    def __init__(
        self,
        teeth: int = 24,
        module: float = 1.0,
        face_width: float = 7.9,
        spring_thickness: float = 5.1,
        hub_r: float = 4.0,
        bushing_clearance: float = 0.1,
        ramp_count: int = 3,
        ring_wall_thickness: float = 0.8,
        ramp_height: float = 1.0,
        spring_count: int = 3,
        arm_pitch: float = 2.0,
        arm_base_width: float = 4.0,
        tip_gap: float = 0.1,
        **kwargs
    ):
        ring_p = kwargs.pop("ring_params", {})
        spring_p = kwargs.pop("spring_params", {})
        plate_p = kwargs.pop("plate_params", {})

        # Merge local arguments with kwargs if passed in dict
        actual_teeth = ring_p.get("teeth", teeth)
        actual_module = ring_p.get("module", module)
        pitch_r = (actual_teeth * actual_module) / 2.0

        # Max radius that doesn't bite into the teeth root (dedendum ~1.25)
        default_sag_r = pitch_r - 1.5

        ring_p.setdefault("teeth", actual_teeth)
        ring_p.setdefault("module", actual_module)
        ring_p.setdefault("sag_r", default_sag_r)

        ramp_outer_r = default_sag_r - ring_wall_thickness

        ring_p.setdefault("ramp_count", ramp_count)
        ring_p.setdefault("ramp_end_r", ramp_outer_r)
        ring_p.setdefault("ramp_start_r", ramp_outer_r - ramp_height)
        ring_p.setdefault("face_width", face_width)

        spring_hub_r = spring_p.setdefault("hub_r", hub_r)
        spring_p.setdefault("spring_count", spring_count)

        # Anchor strictly at coordinate center to decouple inner math from hub width
        spring_p.setdefault("arm_base_width", arm_base_width)
        spring_p.setdefault("tip_gap", tip_gap)

        # Thinner Spring to guarantee it avoids pinching in the assembly gap
        spring_p.setdefault("plate_thickness", spring_thickness)

        # Slower long pitch means the arm spirals tightly along the ring's 120-degree long hooks.
        spring_p.setdefault("arm_pitch", arm_pitch)

        plate_p.setdefault("bushing_r", spring_hub_r)
        plate_p.setdefault("bushing_clearance", bushing_clearance)
        plate_p.setdefault("plate_r", default_sag_r - 0.2)

        super().__init__(ring_params=ring_p, spring_params=spring_p, plate_params=plate_p, **kwargs)

if __name__ == "__main__":
    from ocp_vscode import show
    # Set to False to easily see inside the mechanism during interactive preview
    g_matched = SlipperGearMatched(show_top_plate=False, teeth=20)
    show(g_matched.solid, names=["Matched (Option A)"])
