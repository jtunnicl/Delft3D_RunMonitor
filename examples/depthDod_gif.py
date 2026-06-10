"""
Plot waterdepth and DOD with crossection overlays, export to gif.
"""

from glob import glob
from Delft3D_RunMonitor import *

def _dod(mesh, ti):
    """Bed level change relative to t=0 (depth of difference)."""
    bed_t0 = mesh.readField("mesh2d_s1", 0) - mesh.readField("mesh2d_dg", 0)
    bed_ti = mesh.readField("mesh2d_s1", ti) - mesh.readField("mesh2d_dg", ti)
    return bed_ti - bed_t0


mesh = MultiUGridMesh(sorted(glob("data/*.nc")))
overlays = [CrossSectionOverlay("data/cross_sections.txt")]

Viewer([
    PlotView(mesh, "mesh2d_waterdepth", title="Water Depth (m)",
             overlays=overlays, clim=[0, 1]),
    PlotView(mesh, field_fn=_dod, title="Depth of Difference (m)",
                cmap="bwr", clim=[-2, 2], overlays=overlays),
]).export("dod.mp4")