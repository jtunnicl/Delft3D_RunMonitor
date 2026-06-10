"""
Export water depth as a VTP mesh file for post-processing in ParaView.

Each exported time step produces a numbered file.
Use t0 and t1 to limit which time steps are written.
"""

from glob import glob
from Delft3D_RunMonitor import *

mesh = MultiUGridMesh(sorted(glob("data/*.nc")))

Viewer([
    PlotView(mesh, varname='mesh2d_waterdepth',
             clim=[0, 5], title='Water Depth (m)')
]).export("depth.vtp", t0=0, t1=1)
