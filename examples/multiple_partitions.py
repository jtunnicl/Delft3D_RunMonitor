from Delft3D_RunMonitor import MultiUGridMesh
import defopt
from glob import glob

def main(*, mappattern: str='FlowFM_*_map.nc', varname: str="mesh2d_waterdepth", time_index: int=0, cmin: float=None, cmax: float=None):
    """
    mappattern: glob pattern for the map files
    varname: variable name
    time_index: time index
    """
    mapnames = glob(mappattern)
    mesh = MultiUGridMesh(mapnames)
    clim = None
    if type(cmin) is float and type(cmax) is float:
        clim = [float(cmin), float(cmax)]
    mesh.plot(varname, time_index, clim=clim)

if __name__ == '__main__':
    defopt.run(main)