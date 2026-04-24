import defopt
from glob import glob
from Delft3D_RunMonitor import MultiUGridMesh
import numpy as np

def main(*, mappattern: str='FlowFM_*_map.nc', varname: str='mesh2d_waterdepth'):
    """
    Compute time derivative of field

    mappattern: glob pattern for the map files
    varname: variable name
    """

    varname = 'mesh2d_waterdepth'
    dvarname = f'd{varname}_dt'

    # load the meshes
    filenames = glob('data/FlowFM_*_map.nc')
    if len(filenames) == 0:
        raise RuntimeError('ERROR: must have at least one map file!')

    mugm = MultiUGridMesh(filenames)

    # get the time axis from the first mesh
    time = mugm.meshes[0].time[:] # read the the time axis
    nt = len(time)
    # data at the current time 
    field0 = mugm.readField(varname=varname, time_index=0)

    # convert mesh to VTK
    polydata = mugm.to_pyvista()
    # allocate memory for the derivative
    df = np.empty_like(field0)
    polydata.cell_data[dvarname] = df

    # iterate over time and produce the time derivative
    for i0 in range(nt - 1):
        i1 = i0 + 1
        dt = time[i1] - time[i0]
        field1 = mugm.readField(varname='mesh2d_waterdepth', time_index=i1)
        df[:] = (field1 - field0)/dt
        # save the file
        polydata.save(f'{dvarname}_{i0:04}.vtp')

        field0 = field1


if __name__ == '__main__':
    defopt.run(main)

