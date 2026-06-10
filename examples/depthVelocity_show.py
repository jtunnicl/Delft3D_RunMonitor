from Delft3D_RunMonitor import *
import sys
from glob import glob


mesh = MultiUGridMesh(sorted(glob("data/*.nc")))
view = PlotView(mesh, varname='mesh2d_waterdepth', clim=[0, 5],
                title='Water Depth + Velocity',
                overlays=[VelocityOverlay(mesh)])
Viewer([view]).show()