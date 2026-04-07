from Delft3D_RunMonitor.ugrid_mesh import UGridMesh
import defopt

def main(*, mapname: str='FlowFM_0000_map.nc'):
    """
    @param mapname: name of the map NetCDF file
    """
    mesh = UGridMesh(mapname)
    mesh.plot()

if __name__ == '__main__':
    defopt.run(main)