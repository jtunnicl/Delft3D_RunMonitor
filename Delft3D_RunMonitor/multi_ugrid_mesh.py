import numpy as np
import pyvista as pv
from .ugrid_mesh import UGridMesh


class MultiUGridMesh(UGridMesh):
    def __init__(self, filenames):
        """
        Parameters
        ----------
        filenames : list of map filenames
        """
        self.meshes = [UGridMesh(fn) for fn in filenames]

        # Output
        self.x = None
        self.y = None
        self.z = None
        self.face_nodes = None
        self.edge_nodes = None

        self._merge()

    def _merge(self):
        # --- Step 1: concatenate nodes ---
        xs, ys, zs = [], [], []
        offsets = []

        offset = 0
        for mesh in self.meshes:
            xs.append(mesh.x)
            ys.append(mesh.y)
            zs.append(mesh.z if mesh.z is not None else np.zeros_like(mesh.x))

            offsets.append(offset)
            offset += len(mesh.x)

        x = np.concatenate(xs)
        y = np.concatenate(ys)
        z = np.concatenate(zs)

        # --- Step 2: reindex connectivity ---
        face_list = []
        edge_list = []

        for mesh, offset in zip(self.meshes, offsets):
            # Faces
            if mesh.face_nodes is not None:
                fn = mesh.face_nodes.copy()
                mask = fn >= 0
                fn[mask] += offset
                face_list.append(fn)

            # Edges
            if mesh.edge_nodes is not None:
                en = mesh.edge_nodes + offset
                edge_list.append(en)

        face_nodes = np.vstack(face_list) if face_list else None
        edge_nodes = np.vstack(edge_list) if edge_list else None

        self.x = x
        self.y = y
        self.z = z
        self.face_nodes = face_nodes
        self.edge_nodes = edge_nodes

