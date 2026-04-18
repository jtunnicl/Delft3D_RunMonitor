# MATLAB Workflow Status

The MATLAB workflow is now considered frozen. The repository's active feature work should happen in the Python package.

## What `mddPlot` does

- Finds one history file, one network file, and one or more partitioned map files beneath a case directory.
- Reconstructs the partitioned results into a single plotted domain.
- Produces a four-panel summary view for each timestep:
  - water depth map
  - DoD (bed elevation change relative to the first timestep)
  - discharge history
  - bedload transport history
- Optionally exports an AVI, PNG frames, and an STL of the final rendered bed surface.

## Supported inputs

The script expects standard Delft3D-FM NetCDF outputs:

- `*_his.nc` for time-series data.
- `*_map.nc` for partitioned spatial results.
- `*_net.nc` for the mesh topology.

The current MATLAB workflow assumes the net file contains triangular elements. If higher-order polygons are present, the function now errors explicitly instead of silently plotting the wrong geometry.

## Usage

```matlab
result = mddPlot('/path/to/case', ...
    'exportVideo', true, ...
    'exportImages', false, ...
    'exportSTL', false, ...
    'gridRes', 5, ...
    'timeRes', 10);
```

The returned `result` struct contains:

- `result.files` with the resolved input files.
- `result.summary` with partition and timestep counts.
- `result.outputs` with the enabled export targets.

## Name-value options

| Option | Meaning | Default |
| --- | --- | --- |
| `hisFile` | Glob for the history file relative to `caseFolder` | `*/*his.nc` |
| `mapFiles` | Glob for partition map files relative to `caseFolder` | `*/*map.nc` |
| `netFiles` | Glob for the mesh topology file relative to `caseFolder` | `*net.nc` |
| `exportVideo` | Write an AVI movie | `true` |
| `exportImages` | Write PNG frames | `false` |
| `exportSTL` | Export the final bed surface to STL | `false` |
| `nameVideo` | Output AVI path | `Simulation_Summary.avi` |
| `nameImages` | Output PNG filename pattern | `images/step_%d.png` |
| `nameSTL` | Output STL path | `Final_Bed_Surface.stl` |
| `rhoS` | Sediment bulk density used for bedload conversion | `1600` |
| `width` | Channel width used for bedload conversion | `47.17` |
| `gridRes` | Interpolation grid resolution in model units | `1.0` |
| `timeRes` | Frame stride through the simulation | `1` |
| `visible` | Show the figure after processing | `true` |

## Deliberate scope limits

These are intentionally documented instead of being left ambiguous:

- `rasterBin` is retained only for backwards compatibility and is not used by the current script.
- `xsFile` is optional metadata only; cross-section overlays are not rendered by the frozen MATLAB workflow.
- Headless runs disable video export unless a virtual display is provided, for example with `xvfb-run`.
- The script is a reporting/export tool, not a general MATLAB package API.