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


import cadquery as cq

from vibe_cading.lego.constants import (
    BLOCK_PLAY,
    BLOCK_ROOF,
    BLOCK_WALL,
    CLUTCH_TUBE_OD,
    PLATE_HEIGHT,
    STUD_DIAMETER,
    STUD_HEIGHT,
    STUD_PITCH,
)
from vibe_cading.print_settings import ToleranceProfile, get_profile

# Entry overcut for the clutch bore: extend the bore below the Z=0 rim so its
# entry face is not coincident with the body bottom face. Coincident boolean
# faces are an OCCT reliability hazard (see Known Modelling Pitfalls). The bore
# stays blind at the top (terminates at the roof underside, no overcut there).
_BORE_ENTRY_OVERCUT: float = 0.1


class LegoBlock:
    """Parametric studded Lego System block — brick / plate / tile generator.

    One class spans the whole studded-System family on the 8 mm stud grid; the
    member you want is a *parameter set*, not a subclass.  Use the convenience
    factories for the common members:

        LegoBlock(2, 3)            # 2x3 brick (the default: plates=3, studded)
        LegoBlock.brick(2, 4)      # 3-plate-tall studded brick
        LegoBlock.plate(2, 4)      # 1-plate-tall studded plate
        LegoBlock.tile(2, 4)       # 1-plate-tall smooth tile (no studs)
        LegoBlock(2, 4, plates=6)  # double-height brick

    Geometry
    --------
    * **Footprint** ``studs_x x studs_y`` studs; outer edge along each axis is
      ``n * STUD_PITCH - BLOCK_PLAY`` (the real-Lego 0.2 mm pack gap).
    * **Height** ``plates * PLATE_HEIGHT`` (plate = 1, brick = 3, double = 6).
    * **Top** studs (``studded=True``) or smooth (``studded=False`` → tile).
    * **Underside** hollowed to ``BLOCK_WALL`` walls + ``BLOCK_ROOF`` top plate,
      with clutch tubes auto-placed **only where a 2x2 stud cluster exists**
      (both dims >= 2).  A 1xN or 1x1 block has no tubes — it relies on wall
      friction (this model omits the small anti-stud ribs that real 1xN Lego
      bricks add; proper clutch tubes need a 2x2 stud cluster).

    Origin convention
    -----------------
    The block is **centred in XY** about ``(0, 0)`` and its **bottom clutch rim
    sits at Z = 0** — that bottom face is the primary mating interface (it grips
    the studs of the block below), so it lands on the project zero-datum plane.
    The body roof is at ``Z = plates * PLATE_HEIGHT``; stud tops are
    ``STUD_HEIGHT`` above that.  Studs point **+Z**.

    Parameters
    ----------
    studs_x, studs_y:
        Footprint in studs along X and Y.  Both must be >= 1.
    plates:
        Height in plate units (1 plate = ``PLATE_HEIGHT`` = 3.2 mm).  Must be
        >= 1.  Integer plate-units keep every block on the System stacking grid.
    studded:
        Whether the top face carries studs.  ``False`` yields a smooth tile.
    profile:
        Manufacturing tolerance profile that sizes the underside clutch bore.
        Defaults to the active profile from
        ``vibe_cading.print_settings.get_profile()`` (env ``PRINT_PROFILE`` →
        ``fdm_standard``).  The clutch bore is the part's only fit-sensitive
        feature; everything else is nominal real-Lego geometry.
    """

    PLATES_PER_BRICK: int = 3  # 9.6 mm brick / 3.2 mm plate

    def __init__(
        self,
        studs_x: int,
        studs_y: int,
        plates: int = PLATES_PER_BRICK,
        studded: bool = True,
        profile: ToleranceProfile | None = None,
    ) -> None:
        if studs_x < 1 or studs_y < 1:
            raise ValueError(
                f"studs_x and studs_y must be >= 1, got {studs_x}x{studs_y}"
            )
        if plates < 1:
            raise ValueError(f"plates must be >= 1, got {plates}")

        self.studs_x: int = studs_x
        self.studs_y: int = studs_y
        self.plates: int = plates
        self.studded: bool = studded

        # Derived dimensions (all from fundamentals — no magic numbers).
        self.footprint_x: float = studs_x * STUD_PITCH - BLOCK_PLAY
        self.footprint_y: float = studs_y * STUD_PITCH - BLOCK_PLAY
        self.height: float = plates * PLATE_HEIGHT

        # Clutch fit: the underside tube receives a stud from below.  Size its
        # bore off the active profile's *slip* grade (snug, removable) — not the
        # raw nominal: FDM holes print undersized, so a zero-clearance bore would
        # seize on a real stud.  Sourced from STUD_DIAMETER + 2*slip.radial but
        # held as its own attribute so tuning the clutch never resizes the studs.
        # Mirrors LegoTechnicBeam / TechnicPinHole, the codebase's mating-bore idiom.
        self._profile: ToleranceProfile = profile or get_profile()
        self.clutch_bore_diameter: float = (
            STUD_DIAMETER + 2 * self._profile.slip.radial
        )

        self._solid: cq.Workplane = self._build()

    # ── Convenience factories (the common family members) ─────────────────────
    @classmethod
    def brick(cls, studs_x: int, studs_y: int,
              profile: ToleranceProfile | None = None) -> "LegoBlock":
        """A standard 3-plate-tall studded brick (9.6 mm body)."""
        return cls(studs_x, studs_y, plates=cls.PLATES_PER_BRICK,
                   studded=True, profile=profile)

    @classmethod
    def plate(cls, studs_x: int, studs_y: int,
              profile: ToleranceProfile | None = None) -> "LegoBlock":
        """A 1-plate-tall studded plate (3.2 mm body)."""
        return cls(studs_x, studs_y, plates=1, studded=True, profile=profile)

    @classmethod
    def tile(cls, studs_x: int, studs_y: int,
             profile: ToleranceProfile | None = None) -> "LegoBlock":
        """A 1-plate-tall smooth tile (3.2 mm body, no studs)."""
        return cls(studs_x, studs_y, plates=1, studded=False, profile=profile)

    # ── Geometry ──────────────────────────────────────────────────────────────
    def _grid_centres(self, n: int) -> list[float]:
        """Stud centres for ``n`` studs along one axis, centred about the origin."""
        return [(i - (n - 1) / 2.0) * STUD_PITCH for i in range(n)]

    def _underside_features(
        self, body: cq.Workplane, cavity_h: float
    ) -> cq.Workplane:
        """Add the underside clutch tubes (hollow cylinders) where they belong.

        Clutch tubes sit at the *interior* grid vertices — the midpoints between
        adjacent studs in both axes — so a tube exists only when the footprint
        has a 2x2 stud cluster (``studs_x >= 2 and studs_y >= 2``).  For a 1xN or
        1x1 block both interior-vertex lists are empty, so no tube is added and
        the block relies on wall friction (this model omits the small anti-stud
        ribs real 1xN Lego bricks use).

        Tubes span the full cavity height so their tops fuse into the roof
        underside, keeping the result a single contiguous solid.
        """
        xs = self._grid_centres(self.studs_x)
        ys = self._grid_centres(self.studs_y)
        tube_xs = [(a + b) / 2 for a, b in zip(xs, xs[1:])]
        tube_ys = [(a + b) / 2 for a, b in zip(ys, ys[1:])]
        tube_pts = [(tx, ty) for tx in tube_xs for ty in tube_ys]
        if not tube_pts:
            return body

        tubes = (
            cq.Workplane("XY")
            .pushPoints(tube_pts)
            .circle(CLUTCH_TUBE_OD / 2)
            .extrude(cavity_h)
        )
        # Profile-driven clutch bore (see __init__): grips a stud from below.
        # Extend the entry below Z=0 by _BORE_ENTRY_OVERCUT so the bore mouth is
        # not coincident with the body bottom face; the terminal stays at cavity_h
        # (blind, closed by the roof — never overcut into the roof). The extra
        # cutter volume sits in empty space below Z=0, so the solid is unchanged.
        bores = (
            cq.Workplane("XY")
            .workplane(offset=-_BORE_ENTRY_OVERCUT)
            .pushPoints(tube_pts)
            .circle(self.clutch_bore_diameter / 2)
            .extrude(cavity_h + _BORE_ENTRY_OVERCUT)
        )
        return body.union(tubes).cut(bores)

    def _build(self) -> cq.Workplane:
        """Body box → hollow underside → clutch tubes → optional studs."""
        cavity_h = self.height - BLOCK_ROOF  # always > 0 (min height 3.2 > roof 1.0)

        # Outer body: bottom rim at Z=0, centred in XY.
        body = cq.Workplane("XY").box(
            self.footprint_x, self.footprint_y, self.height,
            centered=(True, True, False),
        )
        # Hollow the underside, leaving BLOCK_WALL walls and a BLOCK_ROOF top.
        cavity = cq.Workplane("XY").box(
            self.footprint_x - 2 * BLOCK_WALL,
            self.footprint_y - 2 * BLOCK_WALL,
            cavity_h,
            centered=(True, True, False),
        )
        body = body.cut(cavity)

        body = self._underside_features(body, cavity_h)

        if self.studded:
            stud_pts = [
                (x, y)
                for x in self._grid_centres(self.studs_x)
                for y in self._grid_centres(self.studs_y)
            ]
            studs = (
                cq.Workplane("XY")
                .workplane(offset=self.height)
                .pushPoints(stud_pts)
                .circle(STUD_DIAMETER / 2)
                .extrude(STUD_HEIGHT)
            )
            body = body.union(studs)

        # Single-solid topological guard (project invariant).
        solid_count = len(body.solids().vals())
        assert solid_count == 1, (
            f"Expected single solid, got {solid_count} for "
            f"{self.studs_x}x{self.studs_y} plates={self.plates} "
            f"studded={self.studded}."
        )
        return body

    @property
    def solid(self) -> cq.Workplane:
        """The finished block body as a CadQuery Workplane."""
        return self._solid

    @classmethod
    def demo(cls, **kwargs) -> list[tuple[cq.Workplane, str, str]]:
        """One generator, four parameter sets: brick / plate / tile / 1xN.

        Shows the three height/top variants at a shared 2x3 footprint plus a
        1x4 brick (the no-interior-tubes case), laid out along +X with gaps.
        """
        members = [
            (cls.brick(2, 3), "brick(2x3)", "royalblue"),
            (cls.plate(2, 3), "plate(2x3)", "gold"),
            (cls.tile(2, 3), "tile(2x3)", "tomato"),
            (cls.brick(1, 4), "brick(1x4)", "seagreen"),
        ]
        placed: list[tuple[cq.Workplane, str, str]] = []
        cursor = 0.0
        for block, name, color in members:
            bb = block.solid.val().BoundingBox()
            dx = cursor + bb.xlen / 2 + 4.0  # 4 mm clear gap between members
            placed.append((block.solid.translate((dx, 0, 0)), name, color))
            cursor = dx + bb.xlen / 2
        return placed
