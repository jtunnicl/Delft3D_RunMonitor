"""
Four-panel diagnostic dashboard in a 2x2 grid.

Combines four derived and direct fields in one window:
  top-left     Water depth           — where the water is
  top-right    Velocity magnitude    — how fast it is moving
  bottom-left  Depth of difference   — net bed-level change since t=0
  bottom-right dh/dt                 — rate of depth change (inundation front)

Use shape=(2, 2) in Viewer to arrange PlotViews row-by-row.
"""

import numpy as np
from glob import glob
from Delft3D_RunMonitor import *

mesh = MultiUGridMesh(sorted(glob("data/*.nc")))
time = mesh.meshes[0].time[:]

def velocity_magnitude(mesh, ti):
    ucx = mesh.readField('mesh2d_ucx', ti)
    ucy = mesh.readField('mesh2d_ucy', ti)
    return np.sqrt(ucx**2 + ucy**2)

def dod(mesh, ti):
    bed_t0 = mesh.readField('mesh2d_s1', 0) - mesh.readField('mesh2d_dg', 0)
    bed_ti = mesh.readField('mesh2d_s1', ti) - mesh.readField('mesh2d_dg', ti)
    return bed_ti - bed_t0

def dh_dt(mesh, ti):
    t_prev = max(ti - 1, 0)
    f0 = mesh.readField('mesh2d_waterdepth', t_prev)
    f1 = mesh.readField('mesh2d_waterdepth', ti)
    dt = time[ti] - time[t_prev]
    return (f1 - f0) / dt if dt else np.zeros_like(f1)

Viewer([
    PlotView(mesh, varname='mesh2d_waterdepth',
             clim=[0, 5], title='Water Depth (m)'),
    PlotView(mesh, field_fn=velocity_magnitude,
             clim=[0, 2], cmap='YlOrRd', title='Velocity Magnitude (m/s)'),
    PlotView(mesh, field_fn=dod,
             clim=[-2, 2], cmap='bwr', title='Depth of Difference (m)'),
    PlotView(mesh, field_fn=dh_dt,
             clim=[-0.0001, 0.0001], cmap='bwr', title='dh/dt (m/s)'),
], shape=(2, 2)).show()
