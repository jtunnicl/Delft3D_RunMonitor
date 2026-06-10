# Delft3D RunMonitor

A Python package for visualising and exporting Delft3D-FM (Flexible Mesh) simulation results. It reads partitioned map files, merges them into a single domain, and provides an interactive viewer and batch export API built on [PyVista](https://docs.pyvista.org/).

Used to inspect model run progress on REANNZ supercomputing infrastructure.

---

## Setup

### Local

```sh
git clone <repo>
cd Delft3D_RunMonitor
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Mahuika HPC

```sh
cd /nesi/project/<project_code>
git clone <repo>
cd Delft3D_RunMonitor
module -q purge
module load Python/3.14.4-foss-2026
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

To view plots interactively (`.show()`) you need a functioning [X11 setup](https://docs.nesi.org.nz/Getting_Started/Accessing_the_HPCs/X11/).

`.export()` does not require X11 — prepend with `xvfb-run`:

```sh
xvfb-run python examples/depth_show.py
```

### Subsequent logins (Mahuika)

```sh
cd /nesi/project/<project_code>/Delft3D_RunMonitor
module -q purge
module load Python/3.14.4-foss-2026
source .venv/bin/activate
```

---

## Quick start

```python
from glob import glob
from Delft3D_RunMonitor import MultiUGridMesh, PlotView, Viewer

mesh = MultiUGridMesh(sorted(glob("data/FlowFM_*_map.nc")))

Viewer([
    PlotView(mesh, varname='mesh2d_waterdepth', clim=[0, 5], title='Water depth (m)'),
]).show()
```

---

## API reference

### Mesh classes

#### `UGridMesh(filename)`

Reads a single Delft3D-FM partition (`*_map.nc`). Used directly when there is only one partition file.

```python
from Delft3D_RunMonitor import UGridMesh
mesh = UGridMesh("FlowFM_map.nc")
```

#### `MultiUGridMesh(filenames)`

Merges multiple partition files into a single unified mesh. This is the normal entry point for Delft3D-FM runs that were decomposed across multiple cores.
Works in cases of one file.

```python
from glob import glob
from Delft3D_RunMonitor import MultiUGridMesh
mesh = MultiUGridMesh(sorted(glob("data/FlowFM_*_map.nc")))
```

---

### `PlotView`

Describes a single panel: which mesh, which field, and how to format it.

```python
PlotView(
    mesh,                        # UGridMesh or MultiUGridMesh
    varname='mesh2d_waterdepth', # NetCDF variable name — or use field_fn
    field_fn=None,               # Callable[[mesh, ti], np.ndarray] for derived fields
    clim=[0, 5],                 # [cmin, cmax] colour limits
    cmap='plasma',               # Matplotlib colormap
    title='Water depth (m)',     # Label below the colour bar
    overlays=[],                 # List of Overlay objects
    **mesh_kwargs,               # Passed to pyvista Plotter.add_mesh()
)
```

Use `field_fn` for fields not stored directly in the NetCDF — for example depth-of-difference or dh/dt:

```python
def dod(mesh, ti):
    bed0 = mesh.readField('mesh2d_s1', 0) - mesh.readField('mesh2d_dg', 0)
    bed  = mesh.readField('mesh2d_s1', ti) - mesh.readField('mesh2d_dg', ti)
    return bed - bed0

PlotView(mesh, field_fn=dod, clim=[-2, 2], cmap='bwr', title='DoD (m)')
```

---

### `Viewer`

Arranges one or more `PlotView` panels in a grid and drives interactive display or batch export.

```python
Viewer(
    views,          # List of PlotView objects
    shape=None,     # (rows, cols) — defaults to (1, len(views))
    t0=0,           # First time index (inclusive)
    t1=-1,          # Last time index (inclusive, negative counts from end)
    step=1,         # Frame step
)
```

#### `.show()`

Opens an interactive PyVista viewer alongside a slider window for time navigation.

| Key | Action |
|-----|--------|
| Right / Left | Step forward / backward one frame |
| Home / End | Jump to first / last frame |
| Space | Toggle play / pause |

#### `.export(outfile, t0=None, t1=None, step=None)`

Export frames to a file. The format is inferred from the extension:

| Extension | Format |
|-----------|--------|
| `.mp4` `.avi` `.mov` | Video (requires `ffmpeg`) |
| `.gif` | Animated GIF |
| `.png` `.jpg` | Image — numbered automatically when `t1 > t0` |
| `.vtp` `.vtk` | VTK mesh with scalar data (open in ParaView) |
| `.stl` `.ply` `.obj` | Geometry-only 3D mesh (Blender, Rhino, MeshLab) |

```python
Viewer([PlotView(mesh, varname='mesh2d_waterdepth', clim=[0, 5])]).export("depth.mp4")
```

---

### Overlays

Overlays are added to a `PlotView` via its `overlays=` parameter.
An overlay is anything that can be added to a plot that does not redraw the underlying mesh data. Make your own overlays extending the `Overlay` abstract.

#### `CrossSectionOverlay(xs_file)`

Draws static cross-section lines from a coordinate file. Lines are coloured by section index using `tab10`.

File format: pairs of `easting northing` rows; a `#` comment immediately before a pair sets its label.

```python
from Delft3D_RunMonitor import CrossSectionOverlay

xs = CrossSectionOverlay("data/cross_sections.txt")
PlotView(mesh, varname='mesh2d_waterdepth', clim=[0, 5], overlays=[xs])
```

#### `VelocityOverlay(mesh, scale=10.0, color='white', downsample=100)`

Draws time-varying velocity arrows at face centres using `mesh2d_ucx` / `mesh2d_ucy`.

- `scale` — arrow length multiplier (metres per m/s)
- `downsample` — plot every *n*-th face to keep rendering fast

```python
from Delft3D_RunMonitor import VelocityOverlay

vel = VelocityOverlay(mesh, scale=20, downsample=50)
PlotView(mesh, varname='mesh2d_waterdepth', clim=[0, 5], overlays=[vel])
```

---

## Example scripts

All examples use the included test dataset (`data/FlowFM_000[1-4]_map.nc`). Run from the repo root:

```sh
python examples/depth_show.py
```

| Script | Description |
|--------|-------------|
| `depth_show.py` | Single-panel water depth, interactive |
| `depthVelocity_show.py` | Water depth with velocity overlay |
| `depthVelocityXs_show.py` | Water depth, velocity, and cross-sections |
| `depthVelocityMagnitudeDodDhdt_show.py` | 2×2 dashboard: depth, velocity magnitude, DoD, dh/dt |
| `depthDod_gif.py` | Two-panel depth + DoD exported as animated GIF |
| `timeDerivative_mp4.py` | dh/dt exported as MP4 |
| `depth_vtp.py` | Water depth exported as VTP mesh files |

---

## Example data

`data/` contains a stripped, downsampled mesh of the Waiapu5 domain split across four partitions (`FlowFM_000[1-4]_map.nc`) and a cross-section file `cross_sections.txt`. All example scripts use this data.

---

## Testing

```sh
pip install -e ".[test]"
pytest tests/
```

---

## MATLAB workflow

A frozen MATLAB workflow is in `mddPlot.m`. It is stable but not actively developed — new features should be added in Python.

- Primary function: `mddPlot(caseFolder, Name=Value)`
- Example runner: `runmddPlot.m`
- Full usage notes: `MATLAB.md`

Supports automatic discovery of `*_his.nc`, `*_map.nc`, and `*_net.nc` files; water-depth and DoD map rendering; discharge and bedload history panels; and optional AVI, PNG, and STL export.

---

## Troubleshooting

### `X Error of failed request: GLXBadContext` (or similar)

PyVista requires an OpenGL context. On headless nodes, prefix your command with `xvfb-run`:

```sh
xvfb-run python examples/depth_show.py
```
