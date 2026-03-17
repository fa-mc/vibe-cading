"""Steep (Option C) slipper gear variant."""

from models.xlego.slipper_gear.directional.base import SlipperGearBase

class SlipperGearSteep(SlipperGearBase):
    """Option C (Hybrid/Steep): Variable ramps, dynamically matched short arms.

    The ramp is steep (default 12 ramps). The assembly base class auto-calculates
    the arm pitch to dynamically match the tooth pitch to act as a clean pawl.

    Parameters
    ----------
    teeth : int
        Number of gear teeth in the outer ring. Controls overall gear pitch radius.
    module : float
        Gear module size, combined with teeth to establish the pitch radius.
    face_width : float
        Overall external height (Z-thickness) of the completed assembly.
    spring_thickness : float
        Thickness (Z-axis) of the inner sliding spring component.
    hub_r : float
        Radius of the inner cross-axle bushing and spring core.
    bushing_clearance : float
        Gap leaving float tolerance between the inner bushing hub and the outer shell caps.
    ring_wall_thickness : float
        Minimum solid wall thickness separating the outer gear teeth root from the inner ratcheting pocket.
    ramp_count : int
        Number of hard ratcheting steep ramps profiled into the inner bore of the ring.
    ramp_height : float
        The radial depth of the ratcheting teeth. Lowering this decreases the required slip torque and prevents snapping stiff PLA arms.
    spring_count : int
        Number of flexible pawl lever arms cut into the inner spring disc.
    arm_pitch : float
        Rate of expansion for the pawls (spiral coefficient) reaching outward.
    arm_base_width : float
        Anchor thickness of the pawls strictly at origin.
    tip_gap : float
        Radial setback of the pawl tip from the deepest point of the ratcheting pocket.
    """
    def __init__(
        self,
        teeth: int = 24,
        module: float = 1.0,
        face_width: float = 7.95,
        spring_thickness: float = 5.15,
        hub_r: float = 4.0,
        bushing_clearance: float = 0.1,
        ramp_count: int = 12,
        ring_wall_thickness: float = 0.5,
        ramp_height: float = 0.5,
        spring_count: int = 3,
        arm_pitch: float = 2.4,
        arm_base_width: float = 2.0,
        tip_gap: float = 0.05,
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

        # Anchor strictly at origin (0 width) and use pure mathematical spiral to reach tip
        spring_p.setdefault("arm_base_width", arm_base_width)
        spring_p.setdefault("tip_gap", tip_gap)

        # Thinner Spring to guarantee it avoids pinching in the slightly smaller assembly gap
        spring_p.setdefault("plate_thickness", spring_thickness)

        # Allow the spring arms to be independent short pawls instead of perfectly matching
        # the ring's steep pitch (which causes them to over-extend and collide with the next tooth).
        # A very steep pitch (22.0) means it will reach r=9.75 in just ~25 degrees of sweep.
        spring_p.setdefault("arm_pitch", arm_pitch)

        plate_p.setdefault("bushing_r", spring_hub_r)
        plate_p.setdefault("bushing_clearance", bushing_clearance)
        plate_p.setdefault("plate_r", default_sag_r - 0.2)

        super().__init__(ring_params=ring_p, spring_params=spring_p, plate_params=plate_p, **kwargs)

if __name__ == "__main__":
    from ocp_vscode import show
    # Set to False to easily see inside the mechanism during interactive preview
    g_steep = SlipperGearSteep(show_top_plate=False, teeth=20)
    show(g_steep.solid, names=["Steep (Option C)"])
