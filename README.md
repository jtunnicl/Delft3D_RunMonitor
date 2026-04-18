# Delft3D-FM Multi-Domain Result Analyzer

A Python-based tool for post-processing, aggregating, and visualizing multi-domain results from Delft3D-FM (Flexible Mesh) simulations. 
This script handles the reconstruction of partitioned map files into a single global domain for spatial analysis and animation.
It is used to derive a graphical picture of model run progress while Delft3D-FM is executing on REANNZ supercomputing infrastructure.

The repository also contains a frozen MATLAB workflow in `mddPlot.m`. That script usable, but new feature development should happen in Python.

## Installation

We recommend to create a Python virtual environment
```
python -m venv venv
source venv/bin/activate
```

To build the package:
```
pip install -e .
```
This will also install dependencies.

Run some examples, for instance
```
python examples/multiple_partitions.py -m data/FlowFM_\*_map.nc \
                                       -v mesh2d_waterdepth \
                                       -t 3
```
This will display the water depth at time index 3. Note the backslash `\*`. Type 
```
python examples/multiple_partitions.py -h
```
to see the list of options.

To generate a movie
```
DISPLAY= python examples/multiple_partitions_movie.py \
                -m /nesi/project/nesi99999/app_examples/Delft3D/jon/DFM_OUTPUT_FlowFM/FlowFM_00\*_map.nc \
                -v mesh2d_waterdepth --cmin=0 --cmax=3 --t0=2 --t1=10
```
The setting of `DISPLAY=` to empty prevents an OpenGL error on mahuika.


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

## Outputs

- **Videos:** `.avi` files showing the temporal evolution of the reach.
- **STL Mesh:** A scaled/offset 3D mesh of the bed surface for CAD/CGI software.
- **Data Cubes:** Interpolated matrices (`bed_matrix`, `dep_matrix`) for further statistical analysis.
