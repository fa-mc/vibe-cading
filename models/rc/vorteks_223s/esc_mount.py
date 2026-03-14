import cadquery as cq


class EscMount:
    """ESC mount plate for the Arrma Vorteks 223S.

    A flat rectangular plate with two corner notches cut from the bottom
    and a centred groove on the back face for cable routing / alignment.

    Parameters
    ----------
    length : float
        Overall plate length (X axis), mm. Default 57.
    width : float
        Overall plate width (Y axis), mm. Default 38.
    height : float
        Plate thickness (Z axis), mm. Default 4.
    left_notch_w : float
        Width (X) of the bottom-left corner notch, mm. Default 12.
    left_notch_h : float
        Height (Y) of the bottom-left corner notch, mm. Default 24
        (= width − 14 mm top lip).
    right_notch_w : float
        Width (X) of the bottom-right corner notch, mm. Default 10.
    right_notch_h : float
        Height (Y) of the bottom-right corner notch, mm. Default 12.
    fillet_r : float
        Fillet radius applied to all vertical edges (inner notch corners
        and outer plate corners), mm. Default 2.0.
    groove_w : float
        Width of the back-face centre groove, mm. Default 4.
    groove_depth : float
        Depth of the back-face centre groove, mm. Default 1.2.
    """

    # ── Reference dimensions ──────────────────────────────────────────────────
    LENGTH: float = 57.0
    WIDTH: float = 38.0
    HEIGHT: float = 4.0
    LEFT_NOTCH_W: float = 12.0
    LEFT_NOTCH_H: float = 24.0   # WIDTH − 14 mm top lip
    RIGHT_NOTCH_W: float = 12.0
    RIGHT_NOTCH_H: float = 10.0
    FILLET_R: float = 2.0
    GROOVE_W: float = 5.0
    GROOVE_DEPTH: float = 1.5

    def __init__(
        self,
        length: float = LENGTH,
        width: float = WIDTH,
        height: float = HEIGHT,
        left_notch_w: float = LEFT_NOTCH_W,
        left_notch_h: float = LEFT_NOTCH_H,
        right_notch_w: float = RIGHT_NOTCH_W,
        right_notch_h: float = RIGHT_NOTCH_H,
        fillet_r: float = FILLET_R,
        groove_w: float = GROOVE_W,
        groove_depth: float = GROOVE_DEPTH,
    ):
        self.length = length
        self.width = width
        self.height = height
        self.left_notch_w = left_notch_w
        self.left_notch_h = left_notch_h
        self.right_notch_w = right_notch_w
        self.right_notch_h = right_notch_h
        self.fillet_r = fillet_r
        self.groove_w = groove_w
        self.groove_depth = groove_depth

        self._solid = self._build()

    def _build(self) -> cq.Workplane:
        """Construct the ESC mount plate solid."""
        L, W, H = self.length, self.width, self.height

        # 1. Base plate — centred at the XY origin
        part = cq.Workplane("XY").box(L, W, H)

        # 2. Bottom-left corner notch — flush with left and bottom edges
        #    Cutter box is positioned in world space to avoid workplane-origin drift
        part = part.cut(
            cq.Workplane("XY")
            .box(self.left_notch_w, self.left_notch_h, H)
            .translate((
                -(L / 2 - self.left_notch_w / 2),
                -(W / 2 - self.left_notch_h / 2),
                0,
            ))
        )

        # 3. Right-edge centre notch — right edge of cut flush with plate right
        #    edge, vertically centred (Y = 0)
        part = part.cut(
            cq.Workplane("XY")
            .box(self.right_notch_w, self.right_notch_h, H)
            .translate((
                +(L / 2 - self.right_notch_w / 2),
                0,
                0,
            ))
        )

        # 4. Fillet all vertical edges (inner notch corners + outer plate corners)
        if self.fillet_r > 0:
            part = part.edges("|Z").fillet(self.fillet_r)

        # 5. Back-face centre groove — centred at X=0, runs the full width
        part = (
            part
            .faces("<Z").workplane()
            .rect(self.groove_w, W)
            .cutBlind(-self.groove_depth)
        )

        return part

    @property
    def solid(self) -> cq.Workplane:
        """The CadQuery solid."""
        return self._solid


if __name__ == "__main__":
    from ocp_vscode import show

    mount = EscMount()
    show(mount.solid)
