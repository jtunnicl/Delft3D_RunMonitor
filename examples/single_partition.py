from Delft3D_RunMonitor import UGridMesh
import defopt

def main(*, mapname: str='FlowFM_0000_map.nc', varname: str="mesh2d_waterdepth", time_index: int=0):
    """
    mapname: name of the map NetCDF file
    varname: variable name
    time_index: time index
    """
    mesh = UGridMesh(mapname)
    mesh.plot(varname, time_index)

if __name__ == '__main__':
    defopt.run(main)