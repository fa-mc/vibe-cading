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

"""Regenerate the README sample-gallery assets under ``assets/``.

For each gallery model this renders a shaded PNG thumbnail (VTK offscreen, at the
canonical three-quarter view — ~30 deg azimuth, per-part elevation) and exports an
interactive STL (``cq.exporters``) that GitHub's native 3D viewer can rotate. The
README wraps each ``sample-<name>.png`` thumbnail in a link to ``sample-<name>.stl``.

**These assets are decorative and regenerate-on-demand.** VTK/OCCT tessellation is
host-dependent, so they are NOT byte-reproducible across machines (same class of
drift as ``cq.Workplane.text()`` glyphs). Do **not** register them in
``visual_contracts.toml`` / the CI visual-contract freshness gate — that gate is for
the byte-reproducible orthographic SVGs only; pointing it at these would false-fail.

The renderer uses VTK, which ships with CadQuery, so this tool adds no extra runtime
dependency. The optional content-crop uses Pillow if importable and is skipped
otherwise. The canonical ~30 deg view is research-backed: oblique three-quarter
views are recognised best, whereas a front-on view flattens rotationally-symmetric
parts (e.g. the gear).

Usage::

    python3 vibe_cading/tools/gen_gallery.py                  # overwrite assets/
    python3 vibe_cading/tools/gen_gallery.py --out-dir tmp/g  # render elsewhere
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # annotations only — cadquery is imported lazily in main()
    import cadquery as cq

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Shared canonical three-quarter azimuth for every thumbnail.
AZIMUTH = -30.0

# Per-piece RGB (0..1). Two-part models use a second colour for the second piece.
_BLUE = (0.26, 0.52, 0.96)
_RED = (0.86, 0.16, 0.14)
_GREEN = (0.30, 0.70, 0.42)
_ORANGE = (0.95, 0.55, 0.15)
_PURPLE = (0.56, 0.45, 0.88)
_AMBER = (0.96, 0.64, 0.20)


def _make_actor(workplane: "cq.Workplane", rgb: tuple[float, float, float]):
    """Build a Phong-shaded VTK actor from a CadQuery workplane's tessellation."""
    import vtk

    verts, tris = workplane.val().tessellate(0.02, 0.2)
    points = vtk.vtkPoints()
    points.SetNumberOfPoints(len(verts))
    for i, v in enumerate(verts):
        points.SetPoint(i, v.x, v.y, v.z)
    polys = vtk.vtkCellArray()
    for a, b, c in tris:
        polys.InsertNextCell(3)
        polys.InsertCellPoint(a)
        polys.InsertCellPoint(b)
        polys.InsertCellPoint(c)
    pd = vtk.vtkPolyData()
    pd.SetPoints(points)
    pd.SetPolys(polys)

    # Recompute consistent outward normals so concave parts (holed slabs) shade cleanly.
    nrm = vtk.vtkPolyDataNormals()
    nrm.SetInputData(pd)
    nrm.ConsistencyOn()
    nrm.AutoOrientNormalsOn()
    nrm.SetFeatureAngle(45)
    nrm.Update()

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(nrm.GetOutputPort())
    mapper.ScalarVisibilityOff()
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    prop.SetColor(*rgb)
    prop.SetAmbient(0.32)
    prop.SetDiffuse(0.74)
    prop.SetSpecular(0.12)
    prop.SetSpecularPower(20)
    prop.SetInterpolationToPhong()
    return actor


def _crop_to_content(png_path: Path, pad: int = 14) -> None:
    """Crop transparent margins to the content bbox (no-op if Pillow is absent)."""
    try:
        from PIL import Image
    except ImportError:
        return
    im = Image.open(png_path)
    bbox = im.getbbox()
    if bbox:
        left, top, right, bottom = bbox
        im.crop((
            max(0, left - pad), max(0, top - pad),
            min(im.width, right + pad), min(im.height, bottom + pad),
        )).save(png_path)


def _render_png(pieces: list, elevation: float, out_png: Path, zoom: float = 1.02) -> None:
    """Render coloured (workplane, rgb) pieces to a transparent shaded PNG.

    Uses VTK offscreen rendering (a true z-buffer, unlike a 2D painter's algorithm),
    so concave parts with through-holes occlude correctly.
    """
    import vtk

    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    for workplane, rgb in pieces:
        ren.AddActor(_make_actor(workplane, rgb))

    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.SetAlphaBitPlanes(1)
    rw.SetMultiSamples(8)
    rw.AddRenderer(ren)
    rw.SetSize(1000, 1000)

    ren.ResetCamera()
    cam = ren.GetActiveCamera()
    cam.Azimuth(AZIMUTH)
    cam.Elevation(elevation)
    ren.ResetCamera()  # re-fit AFTER the rotation so nothing clips at the edges
    cam.Zoom(zoom)
    ren.ResetCameraClippingRange()

    ren.AutomaticLightCreationOff()
    for position, intensity in [((-1, 1, 2), 0.9), ((1, -0.5, 0.5), 0.4)]:
        light = vtk.vtkLight()
        light.SetPosition(*position)
        light.SetIntensity(intensity)
        light.SetLightTypeToCameraLight()
        ren.AddLight(light)
    rw.Render()

    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.SetInputBufferTypeToRGBA()
    w2i.ReadFrontBufferOff()
    w2i.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(out_png))
    writer.SetInputConnection(w2i.GetOutputPort())
    writer.Write()
    _crop_to_content(out_png)


def _gallery_jobs() -> list:
    """The gallery spec: ``(name, png_pieces, stl_solid, elevation)`` per sample.

    ``png_pieces`` is a list of ``(workplane, rgb)`` (two entries for the two-part
    servo and hinge); ``stl_solid`` is the single (possibly compound) solid exported
    for the interactive viewer.
    """
    from vibe_cading.mechanical.gears.helical import HelicalGear
    from vibe_cading.lego.technic_l_liftarm import LegoTechnicLLiftarm
    from vibe_cading.lego_adapters.servos.sg90.servo_mount import (
        ServoMountAssembly,
        ServoMountBase,
        ServoMountClamp,
    )
    from vibe_cading.mechanical.hinge import PrintInPlaceHinge

    # Herringbone (double-helical) gear — two opposite-hand helical halves
    # meeting at the mid-plane chevron.
    gear = HelicalGear(
        module=1.0, teeth=30, face_width=12.0, helix_angle=30,
        bore=6, double_helix=True,
    )
    lift = LegoTechnicLLiftarm()  # default 3x5
    base = ServoMountBase()
    clamp = ServoMountClamp(outer_x=base.outer_size / 2, arm_inner_x=base.arm_inner_x)
    servo_assembly = ServoMountAssembly()  # base + clamp compound, for the STL
    hinge = PrintInPlaceHinge(angle=35)  # shown open; screw_holes=True by default

    return [
        ("gear", [(gear.solid, _BLUE)], gear.solid, 25.0),
        ("lliftarm", [(lift.solid, _RED)], lift.solid, 27.0),
        ("servo", [(base.solid, _GREEN), (clamp.solid, _ORANGE)], servo_assembly.solid, 23.0),
        ("hinge", [(hinge.leaf_a, _PURPLE), (hinge.leaf_b, _AMBER)], hinge.solid, 35.0),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate the README sample-gallery assets (assets/sample-*.png + .stl).",
    )
    parser.add_argument(
        "--out-dir", type=Path, default=REPO_ROOT / "assets",
        help="Directory to write sample-<name>.png/.stl into (default: <repo>/assets).",
    )
    parser.add_argument(
        "--stl-tolerance", type=float, default=0.04,
        help="Linear deflection (mm) for STL tessellation (default: 0.04).",
    )
    args = parser.parse_args()

    import cadquery as cq  # lazy: keeps --help free of the CadQuery/VTK import cascade

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, png_pieces, stl_solid, elevation in _gallery_jobs():
        png = out_dir / f"sample-{name}.png"
        stl = out_dir / f"sample-{name}.stl"
        _render_png(png_pieces, elevation, png)
        cq.exporters.export(
            stl_solid, str(stl), tolerance=args.stl_tolerance, angularTolerance=0.2,
        )
        print(f"wrote {png.name} + {stl.name}")


if __name__ == "__main__":
    main()
