import numpy as np
from netCDF4 import Dataset
import pyvista as pv
import time


class UGridMesh:
    """
    A class to read a single partition of data stored on a UGrid mesh
    """

    def __init__(self, filename):

        """
        Constructor

        :param filename: NetCDF file name storing the mesh and data (map file)
        """

        # Data containers
        self.time = None
        self.x = None
        self.y = None
        self.z = None
        self.face_nodes = None
        self.edge_nodes = None
        self.nc = Dataset(filename, "r")
        self._readMesh()

    def _readMesh(self):
        """
        Read the UGrid mesh (points and connectivity)
        """
        # --- Time ---
        self.time = self.nc.variables["time"]

        # --- Node coordinates ---
        self.x = self.nc.variables["mesh2d_node_x"][:]
        self.y = self.nc.variables["mesh2d_node_y"][:]

        if "mesh2d_node_z" in self.nc.variables:
            self.z = self.nc.variables["mesh2d_node_z"][:]
        else:
            self.z = None

        # --- Edge connectivity ---
        edge_var = self.nc.variables["mesh2d_edge_nodes"]
        self.edge_nodes = edge_var[:].astype(np.int64)

        # Convert to 0-based indexing if needed
        start_index = getattr(edge_var, "start_index", 0)
        if start_index != 0:
            self.edge_nodes -= start_index

        # --- Face connectivity ---
        face_var = self.nc.variables["mesh2d_face_nodes"]
        self.face_nodes = face_var[:].astype(np.int64)

        # Handle fill values (ragged faces)
        fill_value = getattr(face_var, "_FillValue", None)
        if fill_value is not None:
            self.face_nodes = np.where(
                self.face_nodes == fill_value, -1, self.face_nodes
            )

        # Convert to 0-based indexing
        start_index = getattr(face_var, "start_index", 0)
        if start_index != 0:
            self.face_nodes = np.where(
                self.face_nodes >= 0,
                self.face_nodes - start_index,
                self.face_nodes
            )

    def readField(self, varname: str, time_index: int):
        """
        Read the field values at time time_index from the NetCDF file

        :param varname: variable name
        :param time_index: time index
        """
        return self.nc.variables[varname][time_index, :]
    
    def _buildVTKPolyData(self):
        """
        Build the VTK PolyData object
        """
        # Points (N, 3)
        points = np.column_stack((self.x, self.y, self.z))

        # Build faces in VTK format:
        # [npts, p0, p1, ..., npts, ...]
        faces_list = []
        for face in self.face_nodes:
            valid = face[face >= 0]  # remove fill values
            if len(valid) < 3:
                continue
            faces_list.append(np.concatenate(([len(valid)], valid)))

        if len(faces_list) == 0:
            raise ValueError("No valid faces found")

        faces = np.hstack(faces_list)

        return pv.PolyData(points, faces)
    
    def to_pyvista(self, varname=None, time_index=None):
        """
        Convert mesh to a PyVista PolyData object

        :param varname: variable name
        :param time_index: time index
        """

        polydata = self._buildVTKPolyData()

        if varname:
            # Read and add the fields
            v = self.nc.variables[varname]
            data = self.readField(varname, time_index)
            location = getattr(v, 'location', 'node')
            if location == 'node':
                polydata.point_data[varname] = data
            elif location == 'face':
                polydata.cell_data[varname] = data
            else:
                raise ValueError(f"ERROR: location {v['location']} is not supported")

        return polydata
    
    def plot(self, varname: str, time_index: int, cmap: str='plasma', clim=None, show_edges: bool=False):
        """
        Plot field at time index

        :param varname: variable name
        :param time_index: time index
        :param cmap: color map name
        :param clim: (cmin, cmax) tuple. cmin and cmax are the min/max values of the color map
        :param show_edges: True if the edges of the triangular mesh should be shown
        """
        polydata = self.to_pyvista(varname, time_index)
        plotter = pv.Plotter()
        plotter.add_mesh(polydata, show_edges=show_edges, clim=clim, cmap=cmap)
        plotter.show()

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
            # read and set the field values
            data_ptr[:] = self.readField(varname=varname, time_index=time_index)
            plotter.add_mesh(polydata, scalars=varname, clim=clim)
            plotter.write_frame()
        plotter.close()

        toc = time.time()
        print(f'time to create {t1 - t0} frames: {toc - tic:.2f} s ({(toc - tic)/(t1 - t0):.2f} s/frame)')
