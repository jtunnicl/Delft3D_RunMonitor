"""
Rate of depth change (dh/dt) exported as an MP4.

Useful for tracking the inundation front — large positive values show rising water,
large negative values show recession. The first frame returns zeros because there is
no prior step to difference against.
"""

import numpy as np
from glob import glob
from Delft3D_RunMonitor import *

mesh = MultiUGridMesh(sorted(glob("data/*.nc")))
time = mesh.meshes[0].time[:]

def dh_dt(mesh, ti):
    t_prev = max(ti - 1, 0)
    f0 = mesh.readField('mesh2d_waterdepth', t_prev)
    f1 = mesh.readField('mesh2d_waterdepth', ti)
    dt = time[ti] - time[t_prev]
    return (f1 - f0) / dt if dt else np.zeros_like(f1)

Viewer([PlotView(mesh, field_fn=dh_dt, clim=[-0.0001, 0.0001], cmap='bwr',
                 title='dh/dt (m/s)')]).export("timeDerivative.mp4")
