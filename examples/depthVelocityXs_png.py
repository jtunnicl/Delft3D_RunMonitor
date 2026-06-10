"""
Water depth with both velocity arrows and cross-section lines stacked as overlays.

Demonstrates combining multiple overlays on a single PlotView. VelocityOverlay updates
each frame (is_dynamic=True) while CrossSectionOverlay is drawn once and reused,
so the two overlay types compose without conflict.
"""

from glob import glob
from Delft3D_RunMonitor import *

mesh = MultiUGridMesh(sorted(glob("data/*.nc")))
xs = CrossSectionOverlay("data/cross_sections.txt")
velocity = VelocityOverlay(mesh, scale=10.0, color='white', downsample=100)

Viewer([
    PlotView(mesh, varname='mesh2d_waterdepth',
             clim=[0, 5], title='Water Depth + Velocity + Cross-sections',
             overlays=[velocity, xs])
]).export("pngs/depthVelocityXs.png")
