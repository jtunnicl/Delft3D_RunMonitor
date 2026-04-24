from Delft3D_RunMonitor import MultiUGridMesh
import defopt
from glob import glob

def main(*, mappattern: str='FlowFM_*_map.nc', varname: str="mesh2d_waterdepth", 
            cmin: float=None, cmax: float=None,
            t0: int=0, t1: int=-1):
    """
    mappattern: glob pattern for the map files
    varname: variable name
    cmin: min float colourmap value
    cmax: max float colourmap value
    t0: min time index
    t1: one beyond last time index
    """
    mapnames = glob(mappattern)
    mesh = MultiUGridMesh(mapnames)
    clim = None
    if type(cmin) is float and type(cmax) is float:
        clim = [float(cmin), float(cmax)]
    mesh.movie(varname, clim=clim, t0=t0, t1=t1)

if __name__ == '__main__':
    defopt.run(main)
