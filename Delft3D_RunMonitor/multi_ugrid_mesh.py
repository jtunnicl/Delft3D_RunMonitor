import numpy as np
import pyvista as pv

from .ugrid_mesh import UGridMesh
import time


class MultiUGridMesh(UGridMesh):
    """
    A class that combines data and grid stored in mutiple partitions
    """

    def __init__(self, filenames):
        """
        Constructor

        :param filenames: list of map filenames
        """
        self.meshes = [UGridMesh(fn) for fn in filenames]
        self.time = 0
        if len(self.meshes) > 0:
            self.time = self.meshes[0].time

    def readField(self, varname: str, time_index: int):
        """
        Read the field values at time time_index from the NetCDF file

        :param varname: variable name
        :param time_index: time index
        """
        data_list = [m.readField(varname=varname, time_index=time_index) for m in self.meshes]
        return np.concatenate(data_list)


    def to_pyvista(self, varname, time_index):
        """
        Convert mesh to a PyVista PolyData object

        :param varname: variable name
        :param time_index: time index
        """
        polydata = pv.merge([m.to_pyvista(varname, time_index) for m in self.meshes])
        return polydata

    def movie(self, varname, moviefile: str="animation.mp4", t0: int=0, t1: int=-1, clim=None):
        """
        Make movie
        
        :param varname: variable name
        :param moviefile: output file
        :param t0: first time index
        :param t1: one beyond last time index
        :param clim: (cmin, cmax) tuple. cmin and cmax are the min/max values of the color map
        """
        # We could just call movie from UGridMesh but this implementation is 2-3 times faster

        tic = time.time()
        pv.OFF_SCREEN = True

        # get the mesh, should have at least one time step. Assume the mesh does not change
        polydata = self.to_pyvista(varname=varname, time_index=0)

        # set the data_ptr to either point or cell data
        # try cell data first
        data_ptr = polydata.cell_data.get(varname, None)
        if data_ptr is None:
            # maybe point data?
            data_ptr = polydata.point_data.get(varname, None)
        if data_ptr is None:
            # could not find any acceptable staggering
            raise RuntimeError(f'ERROR could not find data {varname}')

        plotter = pv.Plotter(off_screen=True)
        plotter.open_movie(moviefile)
        nt = len(self.time)
        # allow t0 and t1 to be negative, -1 means last index
        if t1 < 0:
            t1 = nt + t1
        if t0 < 0:
            t0 = nt + t0
        t0 = min(nt, t0)
        t1 = min(nt, t1)
        print(f't0 = {t0} t1 = {t1}') 
        for time_index in range(t0, t1):
            print(f'time index {time_index}')
            plotter.clear()
            data_ptr[:] = self.readField(varname=varname, time_index=time_index)
            plotter.add_mesh(polydata, scalars=varname, clim=clim)
            plotter.write_frame()
        plotter.close()

        toc = time.time()
        print(f'time to create {t1 - t0} frames: {toc - tic:.2f} s ({(toc - tic)/(t1 - t0):.2f} s/frame)')

    

