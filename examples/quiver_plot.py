from Delft3D_RunMonitor import *
import sys

mesh = MultiUGridMesh(sorted(sys.argv[1:]))
view = PlotView(mesh, varname='mesh2d_waterdepth', clim=[0, 5],
                title='Water Depth + Velocity',
                overlays=[VelocityOverlay(mesh)])
Viewer([view]).show()