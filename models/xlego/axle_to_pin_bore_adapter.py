import cadquery as cq
from models.lego.technic_axle import TechnicAxle

class AxleToPinBoreAdapter:
    """Special 2-stud adapter: bottom half is a cross axle, top half is a round rod
    designed to fit into the hollow inner bore of a standard Technic pin."""

    def __init__(self, axle_shrink: float = 0.02, rod_diameter: float = 3.40):
        self.axle_shrink = axle_shrink
        self.rod_diameter = rod_diameter
        self._solid = None
        self._build()

    def _build(self):
        # D1: Base Cross Axle (1 stud = 8.0 mm)
        # We disable lead_in to avoid a notch at Z=8.0 (the union seam).
        # We also disable corner_radius to prevent boolean sweeping errors when shrunk.
        # We pass `self.axle_shrink` to clearance to shrink the axle geometry.
        axle_obj = TechnicAxle(studs=1, clearance=self.axle_shrink, lead_in=0.0, corner_radius=0.0)
        axle_base = axle_obj.solid

        # Apply standard Lego lead-in chamfer only to the bottom insertion face (<Z)
        lead_in = TechnicAxle.DEFAULT_LEAD_IN
        self.axle = axle_base.faces("<Z").edges().chamfer(lead_in)

        # D2: Round Pin-Rod Extension
        # Extends from Z=8.0 to Z=15.0
        # Standard pin axle socket diameter is 3.2 mm. We apply a 0.1 mm reduction
        # clearance for a smooth insertion fit, resulting in a target rod OD.
        self.rod = (
            cq.Workplane("XY")
            .workplane(offset=8.0)
            .circle(self.rod_diameter / 2)
            .extrude(7.0)
            .faces(">Z")
            .edges()
            .chamfer(0.5)  # 0.5 mm chamfer for guiding the pin on
        )

        # Combine both sections and rotate the final assembly by 45 degrees around Z.
        # This optimizes the printing paths for horizontal FDM print orientation.
        self._solid = self.axle.union(self.rod).rotate((0, 0, 0), (0, 0, 1), 45)

        # Validation: check for contiguous single solid
        assert len(self._solid.solids().vals()) == 1, "Expected single solid."

    @property
    def solid(self) -> cq.Workplane:
        return self._solid

if __name__ == "__main__":
    from ocp_vscode import show

    adapter = AxleToPinBoreAdapter()
    show(adapter.solid)
