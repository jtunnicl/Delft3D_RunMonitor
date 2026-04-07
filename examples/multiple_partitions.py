from Delft3D_RunMonitor.multi_ugrid_mesh import MultiUGridMesh
import defopt
from glob import glob

def main(*, mappattern: str='FlowFM_*_map.nc'):
    """
    @param mappattern:glob pattern for the map files
    """
    mapnames = glob(mappattern)
    mesh = MultiUGridMesh(mapnames)
    mesh.plot()

if __name__ == '__main__':
    defopt.run(main)