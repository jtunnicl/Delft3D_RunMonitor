# Delft3D-FM Multi-Domain Result Analyzer

A Python-based tool for post-processing, aggregating, and visualizing multi-domain results from Delft3D-FM (Flexible Mesh) simulations. 
This script handles the reconstruction of partitioned map files into a single global domain for spatial analysis and animation.
It is used to derive a graphical picture of model run progress while Delft3D-FM is executing on REANNZ supercomputing infrastructure.

The repository also contains a frozen MATLAB workflow in `mddPlot.m`. That script usable, but new feature development should happen in Python.

## Installation

We recommend to create a Python virtual environment
```
python -m venv .venv
source .venv/bin/activate
```

To build the package:
```
pip install -e .
```
This will also install dependencies.

Run the interactive viewer from inside your output directory:

```bash
python examples/plot.py
```

This opens a PyVista windowteps through all time frames.
Glob patterns with `*` should be quoted to prevent shell expansion.

Limit the time range:

```bash
python examples/plot.py --mappattern 'FlowFM_*_map.nc' \
                        --start-time 2 --end-time 20 \
```

Add a cross-section overlay:

```bash
python examples/plot.py --xs-file XSects.txt
```

On headless nodes (e.g. Mahuika) use `xvfb-run` to suppress the OpenGL display requirement:

```bash
xfvb-run python examples/plot.py
```

Run `python examples/plot.py --help` to see all options.

## Testing

Install the test dependencies:

```bash
pip install -e ".[test]"
```


To run tests.

```bash
pytest tests/
```

## Features

- **Multi-Domain Aggregation:** Automatically identifies and merges results from multiple partition files (`FlowFM_0000_map.nc`, `FlowFM_0001_map.nc`, etc.).
- **Sediment Transport Analysis:** Converts cumulative bedload sediment transport (kg) into instantaneous volumetric flux ($m^3/m/s$). TO DO 
- **Morphological Change (DoD):** Calculates "Dem of Difference" (DoD) to visualize erosion and deposition patterns over time.
- **Automated Animation:** Generates high-quality synchronized videos of water depth and bed level changes. TO DO 
- **Spatial Binning:** Includes logic for longitudinal mass balance using GeoTIFF-based spatial bins.  TO DO 
- **3D Export:** Exports final bed geometry as an STL file (with coordinate offsets) for 3D modeling in Blender, Unity, or Rhino.  TO DO 

## MATLAB Workflow

The MATLAB entrypoint is intended as a stable handoff tool rather than an actively developed surface.

- Primary function: `mddPlot(caseFolder, Name=Value)`
- Example runner: `runmddPlot.m`
- Status and full usage notes: `MATLAB.md`

The current MATLAB workflow supports:

- automatic discovery of `*_his.nc`, `*_map.nc`, and `*_net.nc` files beneath a case folder
- water-depth and DoD map rendering
- discharge and bedload history panels
- optional AVI, PNG, and STL export

The current MATLAB workflow does not attempt to preserve incomplete prototype features such as raster-bin mass balance or cross-section overlays. Those are documented explicitly rather than left partially implemented.

## File Requirements

The script expects the standard Delft3D-FM output structure:
- **`*_his.nc`**: History file containing time-series data for cross-sections.
- **`*_map.nc`**: Map files (one per partition) containing spatial mesh data.
- **`*_net.nc`**: The master network file describing the global mesh connectivity.
- **`XSects.txt`** (Optional): A text file containing coordinates for cross-section overlays.

## Output formats

Pass `--output <filename>` to `examples/plot.py` to save instead of opening an interactive window. The file extension determines the format:

| Extension | Format | Notes |
|-----------|--------|-------|
| `.mp4` `.avi` `.mov` | Video | Recommended for sharing. Requires `ffmpeg`. |
| `.gif` | Animated GIF | Larger files — use `--step` to reduce frame count. |
| `.png` `.jpg` | Image | Single file, or numbered (`out_0000.png`, `out_0001.png`, …) if more than one frame. |
| `.vtp` `.vtk` | VTK mesh | Preserves scalar data (water depth, DoD). Open in [ParaView](https://www.paraview.org/). |
| `.stl` `.ply` `.obj` | 3D mesh | Geometry only. Suitable for CAD or 3D printing tools such as Blender, Rhino, or MeshLab. |

### Examples
```bash
# Interactive viewer (default)
python examples/plot.py "data/*_map.nc"

# Save MP4 of all frames
python examples/plot.py "data/*_map.nc" --output animation.mp4

# Save every 3rd frame as a GIF
python examples/plot.py "data/*_map.nc" --output animation.gif --step 3

# Export all frames as
python examples/plot.py "data/*_map.nc" --output images/frame.png

# Export each frame as a VTK mesh
python examples/plot.py "data/*_map.nc" --output mesh.stl
```

### Velocity quiver overlay

Overlay velocity vectors (arrows) on top of a water-depth plot using
`mesh2d_ucx` / `mesh2d_ucy`.

```bash
python examples/quiver_plot.py data/FlowFM_*_map.nc
```