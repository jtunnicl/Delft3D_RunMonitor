import numpy as np
from netCDF4 import Dataset
import pyvista as pv


class UGridMesh:
    def __init__(self, filename):
        self.filename = filename

        # Data containers
        self.x = None
        self.y = None
        self.z = None
        self.face_nodes = None
        self.edge_nodes = None

        self._read()

    def _read(self):
        with Dataset(self.filename, "r") as nc:
            # --- Node coordinates ---
            self.x = nc.variables["mesh2d_node_x"][:]
            self.y = nc.variables["mesh2d_node_y"][:]

            if "mesh2d_node_z" in nc.variables:
                self.z = nc.variables["mesh2d_node_z"][:]
            else:
                self.z = None

            # --- Edge connectivity ---
            edge_var = nc.variables["mesh2d_edge_nodes"]
            self.edge_nodes = edge_var[:].astype(np.int64)

            # Convert to 0-based indexing if needed
            start_index = getattr(edge_var, "start_index", 0)
            if start_index != 0:
                self.edge_nodes -= start_index

            # --- Face connectivity ---
            face_var = nc.variables["mesh2d_face_nodes"]
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

    def __repr__(self):
        return (
            f"UGridMesh2D(\n"
            f"  nodes: {len(self.x)},\n"
            f"  edges: {len(self.edge_nodes)},\n"
            f"  faces: {len(self.face_nodes)}\n"
            f")"
        )
    
    def to_pyvista(self):
        """
        Convert mesh to a PyVista PolyData object.
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

        mesh = pv.PolyData(points, faces)
        return mesh

    
    def plot(self, show_edges=True):
        mesh = self.to_pyvista()
        plotter = pv.Plotter()
        plotter.add_mesh(mesh, show_edges=show_edges)
        plotter.show()
