# Architecture

`Delft3D_RunMonitor` implements a few classes that are decribed below. This document gives an overview of the 
code architecture and shows how to extend the current functionality.

Each functionality is captured in a class, e. g. `UGridMesh`. Type, for instance,
```
pydoc Delft3D_RunMonitor.ugrid_mesh.UGridMesh
```
to see the `UGridMesh` documentation. (You must have the code installed with `pip install -e .` to access the documentation.)

## Class UGridMesh

This class reads single partition data stored in the `UGRID` format, mesh and, if requested, fields. Only the mesh is internally stored, data are read for a single time value on request and returned to the caller. This reduces the memory footprint. 

The mesh data can be converted to VTK/pyvista format for visualization using the `to_pyvista` method. The user can then add fields to the mesh. Examples of plotting and movie making methods are provided. However, the user can also use their own, custom plotting if desired.

## Class MultiUGridMesh

Class `MultiUGridMesh` extends `UGridMesh` by supporting multiple partitions. 

## Example of computing a derived field

Let's assume we want to compute the time derivative of `mesh2d_waterdepth`. Following would be a possible implementation:

```python
import Delft3D_RunMonitor as dr
from glob import glob
import numpy as np

varname = 'mesh2d_waterdepth'
dvarname = f'd{varname}_dt'

# load the meshes
filenames = glob('data/FlowFM_*_map.nc')
if len(filenames) == 0:
    raise RuntimeError('ERROR: must have at least one map file!')

# read the multi-partition geometry
mugm = MultiUGridMesh(filenames)

# read the time axis from the first mesh
time = mugm.meshes[0].time[:]
nt = len(time)

# read the data at the first time step
field0 = mugm.readField(varname=varname, time_index=0)

# convert the mesh to VTK
polydata = mugm.to_pyvista()

# allocate memory for the derivative
df = np.empty_like(field0)
polydata.cell_data[dvarname] = df

# iterate over time and produce the time derivative
for i0 in range(nt - 1):

    # next time step
    i1 = i0 + 1

    # time interval
    dt = time[i1] - time[i0]

    # read the field at the next time step
    field1 = mugm.readField(varname='mesh2d_waterdepth', time_index=i1)

    # set the time derivative values
    df[:] = (field1 - field0)/dt

    # save the file at the i0 time step
    polydata.save(f'{dvarname}_{i0:04}.vtp')

    # update the field
    field0 = field1
```
The saved fiels can then be visualized with `Paraview`.
