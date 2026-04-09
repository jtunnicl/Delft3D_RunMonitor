# Delft3D-FM Multi-Domain Result Analyzer

A Python-based tool for post-processing, aggregating, and visualizing multi-domain results from Delft3D-FM (Flexible Mesh) simulations. 
This script handles the reconstruction of partitioned map files into a single global domain for spatial analysis and animation.
It is used to derive a graphical picture of model run progress while Delft3D-FM is executing on REANNZ supercomputing infrastructure.

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

The software relies on libGL. On mahuika: `module load Mesa`.

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


## Features

- **Multi-Domain Aggregation:** Automatically identifies and merges results from multiple partition files (`FlowFM_0000_map.nc`, `FlowFM_0001_map.nc`, etc.).
- **Sediment Transport Analysis:** Converts cumulative bedload sediment transport (kg) into instantaneous volumetric flux ($m^3/m/s$). TO DO 
- **Morphological Change (DoD):** Calculates "Dem of Difference" (DoD) to visualize erosion and deposition patterns over time.
- **Automated Animation:** Generates high-quality synchronized videos of water depth and bed level changes. TO DO 
- **Spatial Binning:** Includes logic for longitudinal mass balance using GeoTIFF-based spatial bins.  TO DO 
- **3D Export:** Exports final bed geometry as an STL file (with coordinate offsets) for 3D modeling in Blender, Unity, or Rhino.  TO DO 

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
