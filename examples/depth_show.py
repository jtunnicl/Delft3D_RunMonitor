"""
Creates a plot from test files. Minimal viable product.
"""

from Delft3D_RunMonitor import *
from glob import glob

mesh = MultiUGridMesh(sorted(glob("data/*.nc")))
Viewer([PlotView(mesh, varname='mesh2d_waterdepth', clim=[0, 5])]).show()
