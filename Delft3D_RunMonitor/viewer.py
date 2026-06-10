"""High-level viewer API.

Classes
-------
Overlay
    Abstract base class for PlotView overlays.
CrossSectionOverlay
    Static cross-section lines; derives from Overlay.
QuiverOverlay
    Time-varying velocity arrow glyphs; derives from Overlay.
PlotView
    Describe a single panel: which mesh, which field, and how to colour it.
Viewer
    Arrange PlotViews in a grid; drive keyboard interaction or export to
    video, GIF, images, or mesh files.

Module-level helpers
--------------------
add_cross_sections
    Load a cross-section file and add the overlay to a plotter in one call.
export_frames
    Low-level frame-export dispatcher (animation, images, or meshes).
"""

import time as _time
import warnings
from pathlib import Path

import numpy as np
import pyvista as pv


# Format sets                                                                  #

IMAGE_FORMATS     = {'.png', '.jpg', '.jpeg'}
MESH_FORMATS      = {'.stl', '.vtp', '.vtk', '.ply', '.obj'}
VIDEO_FORMATS     = {'.mp4', '.avi', '.mov'}
GIF_FORMATS       = {'.gif'}
ANIMATION_FORMATS = VIDEO_FORMATS | GIF_FORMATS

# position_x/y are panel-relative (0-1 within the subplot viewport).
DEFAULT_SCALAR_BAR = {
    'vertical':   True,
    'position_x': 0.82,
    'position_y': 0.05,
    'height':     0.90,
    'width':      0.05,
}


# Cross-section helpers

def _load_cross_sections(xs_file: str, z: float = 0.0) -> tuple:
    """Parse *xs_file* into a PyVista line mesh and a list of section names.

    File format: pairs of 'easting northing' rows.
    A ``#`` comment line immediately before a pair is used as the section name.
    """
    names = []
    coord_rows = []
    pending_name = None

    with open(xs_file) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith('#'):
                pending_name = line.lstrip('#').strip()
            else:
                coord_rows.append([float(x) for x in line.split()])
                if len(coord_rows) % 2 == 0:
                    names.append(pending_name)
                    pending_name = None

    coords = np.array(coord_rows).reshape(-1, 2, 2)
    points, lines, scalars = [], [], []
    offset = 0
    for i, pair in enumerate(coords):
        pts = np.column_stack([pair, np.full(2, z)])
        points.extend(pts)
        lines += [2, offset, offset + 1]
        scalars.extend([i, i])
        offset += 2

    mesh = pv.PolyData()
    mesh.points = np.array(points)
    mesh.lines = np.array(lines)
    mesh.point_data["xs_index"] = np.array(scalars, dtype=float)
    return mesh, names


def _draw_cross_sections(pl: pv.Plotter, xs_mesh: pv.PolyData, names: list) -> None:
    """Add a pre-loaded cross-section mesh to the active subplot of *pl*."""
    n = len(names)
    pl.add_mesh(
        xs_mesh,
        scalars="xs_index",
        cmap="tab10",
        clim=[-0.5, n - 0.5],
        line_width=3,
        render_lines_as_tubes=True,
        show_scalar_bar=False,
    )

    endpoints = xs_mesh.points[1::2]
    labelled = [(pt, name) for pt, name in zip(endpoints, names) if name]
    if labelled:
        mids, labels = zip(*labelled)
        pl.add_point_labels(
            list(mids),
            list(labels),
            font_size=8,
            always_visible=True,
            show_points=False,
            shape=None,
        )


def add_cross_sections(pl: pv.Plotter, xs_file: str, z: float = 0.0) -> None:
    """Load *xs_file* and add styled cross-section lines to the active subplot of *pl*.

    Parameters
    ----------
    pl:
        PyVista Plotter (the active subplot is used).
    xs_file:
        Path to the cross-section coordinate file.
    z:
        Elevation at which to draw the lines.
    """
    mesh, names = _load_cross_sections(xs_file, z)
    _draw_cross_sections(pl, mesh, names)


# Low-level export helper

def export_frames(output, time_indices, update_frame, mesh, plotter):
    """Dispatch frame export based on *output* file extension.

    Parameters
    ----------
    output:
        Destination file path (string or Path).
    time_indices:
        Sequence of time indices to export.
    update_frame:
        ``Callable[[time_index], None]`` that updates the plotter state.
    mesh:
        PyVista mesh used when saving mesh-format files.
    plotter:
        Configured PyVista Plotter.
    """
    path = Path(output)
    ext = path.suffix.lower()
    multi = len(time_indices) > 1

    if ext in ANIMATION_FORMATS:
        if ext in GIF_FORMATS:
            plotter.open_gif(str(path))
        else:
            plotter.open_movie(str(path))
        for ti in time_indices:
            update_frame(ti)
            plotter.write_frame()
        plotter.close()
    elif multi:
        for i, ti in enumerate(time_indices):
            update_frame(ti)
            dest = path.parent / f"{path.stem}_{i:04d}{path.suffix}"
            if ext in IMAGE_FORMATS:
                plotter.screenshot(str(dest))
            elif ext in MESH_FORMATS:
                mesh.save(str(dest))
    else:
        update_frame(time_indices[0])
        if ext in IMAGE_FORMATS:
            plotter.screenshot(str(path))
        elif ext in MESH_FORMATS:
            mesh.save(str(path))

class Overlay:
    """Abstract base class for PlotView overlays.

    Subclasses must implement :meth:`add_to`.

    Parameters
    ----------
    is_dynamic:
        ``True`` if the overlay needs to update each frame.
    """

    is_dynamic: bool = False

    def add_to(self, plotter: pv.Plotter, time_index: int = None) -> None:
        raise NotImplementedError

class CrossSectionOverlay(Overlay):
    """Cross-section lines loaded once and reusable across any PlotView.

    Parameters
    ----------
    xs_file:
        Path to cross-section coordinate file (pairs of easting/northing rows).
    """

    def __init__(self, xs_file: str):
        self._mesh, self._names = _load_cross_sections(xs_file)

    def add_to(self, plotter: pv.Plotter, time_index: int = None) -> None:
        """Add the overlay to the *active* subplot of *plotter*."""
        _draw_cross_sections(plotter, self._mesh, self._names)

class VelocityOverlay(Overlay):
    """Velocity vector overlay rendered at face centres.

    Reads ``mesh2d_ucx`` / ``mesh2d_ucy`` (face-centred Cartesian components).
    Use *downsample* to keep the arrow count manageable.

    Parameters
    ----------
    mesh:
        A ``UGridMesh`` or ``MultiUGridMesh`` instance.
    scale:
        Arrow length multiplier (metres of arrow per m/s of flow).
    color:
        Color for plot quiver.
    downsample:
        Plot every *downsample*-th face.
    """

    is_dynamic: bool = True

    def __init__(self, mesh, scale: float = 10.0, 
                 color: str = 'white',
                 downsample: int = 100):
        self.mesh    = mesh
        self.scale   = scale
        self.color   = color
        self.downsample  = downsample

        meshes = mesh.meshes if hasattr(mesh, 'meshes') else [mesh]
        fc_x = np.concatenate([m.nc.variables['mesh2d_face_x'][:] for m in meshes])
        fc_y = np.concatenate([m.nc.variables['mesh2d_face_y'][:] for m in meshes])

        self._idx = np.arange(0, len(fc_x), downsample)
        n = len(self._idx)
        pts = np.column_stack([fc_x[self._idx], fc_y[self._idx], np.zeros(n)])
        self._polydata = pv.PolyData(pts)
        self._polydata.point_data['_vel'] = np.zeros((n, 3), dtype=float)

    def add_to(self, plotter: pv.Plotter, time_index: int = None) -> None:
        if time_index is not None:
            ux = self.mesh.readField('mesh2d_ucx', time_index)[self._idx]
            uy = self.mesh.readField('mesh2d_ucy', time_index)[self._idx]
            self._polydata.point_data['_vel'][:, 0] = ux
            self._polydata.point_data['_vel'][:, 1] = uy

        glyphs = self._polydata.glyph(orient='_vel', scale='_vel', factor=self.scale)
        plotter.add_mesh(glyphs, color=self.color, name=f'_quiver_{id(self)}')


class PlotView:
    """A single panel in a Viewer.

    Provide either *varname* (a NetCDF variable read directly from the mesh) or
    *field_fn* (a callable for derived fields).  Not both.

    Parameters
    ----------
    mesh:
        A ``UGridMesh`` or ``MultiUGridMesh`` instance.
    varname:
        NetCDF variable name.  Mutually exclusive with *field_fn*.
    field_fn:
        ``Callable[[mesh, time_index], np.ndarray]`` for derived fields.
    clim:
        ``[cmin, cmax]`` plot limits.
    cmap:
        Matplotlib colormap name.
    title:
        Label shown below the scalar bar.  Defaults to *varname* when given,
        or empty for derived fields.
    overlays:
        List of overlay objects (e.g. ``CrossSectionOverlay``).
    scalar_bar_args:
        Dict of keyword arguments forwarded to PyVista's scalar bar.
        Defaults to :data:`DEFAULT_SCALAR_BAR`.  All position values are
        panel-relative (0–1 within the subplot).
    **mesh_kwargs:
        Any additional keyword arguments accepted by ``pyvista.Plotter.add_mesh``
        (e.g. ``show_edges=True``, ``opacity=0.8``, ``nan_color='grey'``).
        The ``scalars`` key is reserved and must not be used here.
    """

    def __init__(self, mesh, varname: str = None, field_fn=None,
                 clim=None, cmap: str = 'plasma', title: str = None,
                 overlays: list = None, scalar_bar_args: dict = None,
                 **mesh_kwargs):

        if varname is None and field_fn is None:
            raise ValueError("Provide either varname or field_fn.")
        if varname is not None and field_fn is not None:
            raise ValueError("Provide varname or field_fn, not both.")
        if 'scalars' in mesh_kwargs:
            raise ValueError("'scalars' is managed internally; do not pass it via mesh_kwargs.")

        self.mesh = mesh
        self.varname = varname
        self.field_fn = field_fn
        self.clim = clim
        self.cmap = cmap
        self.title = title if title is not None else (varname or '')
        self.overlays = overlays or []
        self.scalar_bar_args = dict(DEFAULT_SCALAR_BAR) if scalar_bar_args is None else scalar_bar_args
        self.mesh_kwargs = mesh_kwargs

        # Infer data staggering from NetCDF metadata when varname is given.
        self.location = 'face'
        if varname is not None:
            first = mesh.meshes[0] if hasattr(mesh, 'meshes') else mesh
            v = first.nc.variables.get(varname)
            if v is not None:
                self.location = getattr(v, 'location', 'face')

        # Key used in PyVista's cell_data / point_data dict.
        self._scalar_name = varname if varname else '_field'

        # Set by _init_polydata(); None until then.
        self._polydata = None
        self._data_ptr = None

    # ------------------------------------------------------------------ #

    def get_field(self, time_index: int):
        """Return the scalar array for the given time step."""
        if self.field_fn is not None:
            return self.field_fn(self.mesh, time_index)
        return self.mesh.readField(self.varname, time_index)

    def _init_polydata(self):
        """Build the PyVista mesh and pre-allocate the scalar array at t=0."""
        self._polydata = self.mesh.to_pyvista()
        field0 = self.get_field(0)
        store = (self._polydata.cell_data if self.location == 'face'
                 else self._polydata.point_data)
        store[self._scalar_name] = field0.copy()
        # Keep a reference so we can update in-place without rebuilding.
        self._data_ptr = store[self._scalar_name]

    def _update(self, time_index: int):
        """Overwrite scalar values in-place; no PyVista mesh rebuild."""
        self._data_ptr[:] = self.get_field(time_index)


class Viewer:
    """Arrange PlotViews in a subplot grid and drive the interactive loop.

    Parameters
    ----------
    views:
        List of ``PlotView`` objects.
    shape:
        ``(rows, cols)`` subplot grid.  
        Default to ``(1, len(views))``.
    t0:
        First time index to display.
        Default ``0``.
    t1:
        Last time index to display.
        Default ``-1``.
    step:
        Default ``1``.

    Keyboard controls (interactive mode)
    -------------------------------------
    t     Step forward by *step* frames.
    r     Run continuous animation.
    space Stop animation.
    s     Jump to first frame.
    e     Jump to last frame.
    """

    def __init__(self, views: list, shape: tuple = None,
                 t0: int = 0, t1: int = -1, step: int = 1):
        self.views  = views
        self.shape  = shape or (1, len(views))
        self.time   = views[0].mesh.time
        self.nt     = len(self.time)
        self.t0     = t0
        self.t1     = t1
        self.step   = step

    def _init_views(self):
        for view in self.views:
            view._init_polydata()

    def _add_view_to_subplot(self, pl: pv.Plotter, idx: int, view,
                             time_index: int = 0) -> None:
        """Activate subplot *idx*, add *view*'s mesh, overlays, and title label."""
        row, col = divmod(idx, self.shape[1])
        pl.subplot(row, col)

        # Use a unique internal title so PyVista keys each panel's bar separately.
        sb_args = dict(view.scalar_bar_args)
        sb_args.setdefault('title', f'_view_{idx}')
        pl.add_mesh(
            view._polydata,
            scalars=view._scalar_name,
            clim=view.clim,
            cmap=view.cmap,
            scalar_bar_args=sb_args,
            **view.mesh_kwargs,
        )

        pl.scalar_bars[sb_args['title']].SetTitle('')

        for overlay in view.overlays:
            overlay.add_to(pl, time_index)

        if view.title:
            pl.add_text(view.title, position='lower_right',
                        font_size=9, name=f'_bar_title_{idx}')

    def _populate_plotter(self, pl: pv.Plotter, time_index: int = 0):
        """Add each view's mesh and overlays to the appropriate subplot."""
        for idx, view in enumerate(self.views):
            self._add_view_to_subplot(pl, idx, view, time_index)
        pl.link_views()
        self._setup_camera(pl)

    def _setup_camera(self, pl: pv.Plotter) -> None:
        """Set top-down orthographic projection."""
        pl.view_xy()
        pl.camera.parallel_projection = True

    def _update_frame(self, pl: pv.Plotter, ti: int) -> None:
        """Update all views and dynamic overlays in-place at time index *ti*."""
        for idx, view in enumerate(self.views):
            view._update(ti)
            dynamic = [o for o in view.overlays if o.is_dynamic]
            if dynamic:
                row, col = divmod(idx, self.shape[1])
                pl.subplot(row, col)
                for overlay in dynamic:
                    overlay.add_to(pl, ti)

    def _clamp_time_range(self, t0: int, t1: int) -> tuple:
        """Resolve negative indices and clamp to valid range.

        Both t0 and t1 are inclusive time indices.
        """
        if t1 < 0:
            t1 = self.nt + t1
        return max(0, t0), min(self.nt - 1, t1)

    def show(self):
        """Open an interactive viewer alongside a slider window for time navigation.

        Uses the *t0*, *t1*, and *step* values set on the Viewer.

        Keyboard controls (in the viewer window)
        -----------------------------------------
        Right / Left    Step forward / backward by *step* frames.
        Home / End      Jump to first / last frame.
        Space           Toggle play / pause.
        """
        import tkinter as tk

        t0, t1 = self._clamp_time_range(self.t0, self.t1)
        step = self.step

        self._init_views()
        for view in self.views:
            view._update(t0)

        pl = pv.Plotter(shape=self.shape)
        self._populate_plotter(pl, t0)

        ti = t0
        running = False

        root = tk.Tk()
        root.title(f'{t0} / {t1}')
        root.resizable(True, False)
        slider_var = tk.IntVar(value=t0)

        def _go(new_ti):
            nonlocal ti
            clamped = max(t0, min(t1, new_ti))
            if clamped == ti:
                return
            ti = clamped
            self._update_frame(pl, ti)
            slider_var.set(ti)
            root.title(f'{ti} / {t1}')
            pl.render()

        def _toggle():
            nonlocal running
            if running:
                running = False
            else:
                running = True
                while running and ti < t1:
                    _go(ti + step)
                    pl.update(100)
                running = False

        tk.Scale(root, from_=t0, to=t1, orient='horizontal',
                 variable=slider_var, resolution=1,
                 command=lambda v: _go(int(v))).pack(fill='x', padx=8, pady=4)

        pl.add_key_event('Right', lambda: _go(ti + step))
        pl.add_key_event('Left',  lambda: _go(ti - step))
        pl.add_key_event('Home',  lambda: _go(t0))
        pl.add_key_event('End',   lambda: _go(t1))
        pl.add_key_event('space', _toggle)

        def _close():
            try:
                pl.close()
            except Exception:
                pass

        root.protocol('WM_DELETE_WINDOW', _close)
        pl.add_key_event('q', _close)

        # Drive tkinter event processing from a VTK repeating timer so the
        # slider window stays responsive even when the viewer has focus.
        iren = pl.iren.interactor
        iren.AddObserver('TimerEvent', lambda obj, event: root.update())
        iren.CreateRepeatingTimer(50)

        root.update()  # render the tkinter window before the viewer opens
        pl.show()
        try:
            root.destroy()
        except Exception:
            pass

    def export(self, outfile: str = 'animation.mp4',
               t0: int = None, t1: int = None, step: int = None):
        """Export frames to *outfile*.

        The output format is inferred from the file extension:

        - ``.mp4`` / ``.avi`` / ``.mov`` — video animation
        - ``.gif`` — animated GIF
        - ``.png`` / ``.jpg`` / ``.jpeg`` — screenshot(s); files are numbered
          automatically when more than one frame is exported
        - ``.stl`` / ``.vtp`` / ``.vtk`` / ``.ply`` / ``.obj`` — merged mesh
          file(s); numbered automatically when more than one frame is exported

        Parameters
        ----------
        outfile:
            Output file path.
        t0:
            First time index (inclusive).  Defaults to the value set on the
            Viewer.  Negative values count from the end.
        t1:
            Last time index (inclusive).  Defaults to the value set on the
            Viewer.  ``-1`` means the final time step.
        step:
            Frame stride.  Defaults to the value set on the Viewer.
        """
        path = Path(outfile)
        ext = path.suffix.lower()
        path.parent.mkdir(parents=True, exist_ok=True)

        if ext not in ANIMATION_FORMATS | IMAGE_FORMATS | MESH_FORMATS:
            raise ValueError(
                f"Unsupported output format: {ext!r}. "
                f"Supported: {sorted(ANIMATION_FORMATS | IMAGE_FORMATS | MESH_FORMATS)}"
            )

        t0   = self.t0   if t0   is None else t0
        t1   = self.t1   if t1   is None else t1
        step = self.step if step is None else step

        t0, t1 = self._clamp_time_range(t0, t1)
        nframes = len(range(t0, t1 + 1, step))

        self._init_views()
        tic = _time.time()

        pl = pv.Plotter(shape=self.shape, off_screen=True)
        for view in self.views:
            view._update(t0)
        self._populate_plotter(pl, t0)

        if ext in ANIMATION_FORMATS:
            if ext in GIF_FORMATS:
                pl.open_gif(str(path))
            else:
                pl.open_movie(str(path))

            for ti in range(t0, t1 + 1, step):
                self._update_frame(pl, ti)
                pl.write_frame()

        else:  # IMAGE_FORMATS or MESH_FORMATS
            for i, ti in enumerate(range(t0, t1 + 1, step)):
                dest = (path if nframes == 1
                        else path.parent / f"{path.stem}_{i:04d}{ext}")
                self._update_frame(pl, ti)
                if ext in IMAGE_FORMATS:
                    pl.screenshot(str(dest))
                else:
                    pv.merge([v._polydata for v in self.views]).save(str(dest))

        pl.close()

        elapsed = _time.time() - tic
        print(f"Wrote {nframes} frame(s) to {outfile} "
              f"in {elapsed:.1f}s ({elapsed / max(nframes, 1):.2f}s/frame)")