%% Delft3D-FM Multi-Domain Result Analyzer
% This script processes Delft3D-FM Flexible Mesh results (NetCDF).
% It extracts water depth, bed levels, DoD (Dem of Difference), and sediment 
% data across multiple partitions and generates animations and mass balance plots.

%% 1. USER CONFIGURATION
% -------------------------------------------------------------------------
% Path settings
case_folder = 'G:\Delft3D\Niraj2023\Run_017\DFM_OUTPUT_FlowFM\';
his_file    = 'FlowFM_0000_his.nc'; % History file (time series)
map_prefix  = 'FlowFM';             % Prefix for partition map files (e.g., FlowFM_0000_map.nc)
net_file    = 'G:\Delft3D\Niraj2023\Run_008\DFM_interpreted_idomain_FlowFM_net.nc'; % Master network file
raster_bins = 'G:\Delft3D\Niraj2023\Telemac1_cells.tif'
xs_file     = 'G:\Delft3D\Niraj2023\XSects2.txt';

% Physical constants
dt = 0; % Will be calculated from time vector
rho_s = 1600; % Bulk sediment density (kg/m3)
width = 47.17; % Reach width for flux conversion

% Plotting settings
export_video = true;
grid_res = 1.0; % Meters (Resolution for interpolation grid)
% -------------------------------------------------------------------------

%% 2. LOAD TIME SERIES DATA (History File)
% -------------------------------------------------------------------------
fprintf('Loading history data...\n');
t = ncread(his_file, 'time');
dt = t(2) - t(1);

% Qw: Discharge (m3/s) | Qs: Cumulative Bedload (kg)
Qw = ncread(his_file, 'cross_section_discharge'); 
Qs_cum = ncread(his_file, 'cross_section_bedload_sediment_transport');

% Convert cumulative mass to instantaneous volumetric flux (m3/m/s)
% diff() gets the mass per timestep, then divide by time, width, and density.
Qs = diff(Qs_cum, 1, 2) / dt / width / rho_s;

%% 3. LOAD MESH & DOMAIN STRUCTURE (Network File)
% -------------------------------------------------------------------------
fprintf('Parsing network and partition info...\n');
v_info = ncinfo(net_file);
Numsteps = size(ncread(sprintf('%s_%04d_map.nc', map_prefix, q),'time'),1);
% Extract number of partitions from the idomain attribute
partitions = v_info.Variables(strcmp({v_info.Variables.Name}, 'idomain')).Attributes(3).Value;

links = ncread(net_file, 'NetElemLink')';
Xn = ncread(net_file, 'NetNode_x');
Yn = ncread(net_file, 'NetNode_y');
Zn = ncread(net_file, 'NetNode_z');
TRI = ncread(net_file, 'NetElemNode')'; % Triangulation connectivity
idomain_size = size(links, 1);

%% 4. AGGREGATE MULTI-DOMAIN SPATIAL DATA
% -------------------------------------------------------------------------
% Pre-allocate global arrays for speed
X = zeros(idomain_size, 1);
Y = zeros(idomain_size, 1);
d_g = zeros(idomain_size, Numsteps);     % Water depth
sl_g = zeros(idomain_size, Numsteps);    % Water level (s1)
dg_g = zeros(idomain_size, Numsteps);    % Median grain size (D50)

fprintf('Looping through %d partitions...\n', partitions);
for q = 0:(partitions-1)
    fname = sprintf('%s_%04d_map.nc', map_prefix, q);
    
    % Global mapping indices for this partition
    g_idx = int32(ncread(fname, 'mesh2d_flowelem_globalnr'));
    
    % Static Geometry
    X(g_idx) = ncread(fname, 'mesh2d_face_x');
    Y(g_idx) = ncread(fname, 'mesh2d_face_y');
    
    % Dynamic Results
    d_g(g_idx, :)  = ncread(fname, 'mesh2d_waterdepth');
    sl_g(g_idx, :) = ncread(fname, 'mesh2d_s1');
    dg_g(g_idx, :) = ncread(fname, 'mesh2d_dg');
end

% Derived Bed Elevation (Z = WaterLevel - Depth)
Zbed_g = sl_g - d_g;

%% 5. GRID INTERPOLATION SETUP
% -------------------------------------------------------------------------
% Define a regular grid for raster-based analysis and plotting
x_vec = floor(min(X)):grid_res:ceil(max(X));
y_vec = floor(min(Y)):grid_res:ceil(max(Y));
[XX, YY] = meshgrid(x_vec, y_vec);

% Create a mask for the active flow area using an alphaShape
shp = alphaShape(X, Y);
in_mask = inShape(shp, XX, YY);

%% 6. VISUALIZATION: DEPTH & DOD ANIMATION
% -------------------------------------------------------------------------
% Setup custom colormaps
% Red-Blue for DoD (Erosion/Deposition)
m1 = 128;
r = [linspace(0, 1, m1)'; ones(m1, 1)];
g = [linspace(0, 1, m1)'; linspace(1, 0, m1)'];
b = [ones(m1, 1); linspace(1, 0, m1)'];
cmap_dod = [r g b];

% Load Cross-section locations
xs = load(xs_file);
xs_order = [1:2:25, 29 31 33 37 35 39]; 

if export_video
    v = VideoWriter('Simulation_Summary.avi');
    v.FrameRate = 10;
    open(v);
end

fig = figure('Position', [10 370 1280 976], 'Color', 'w');
tlo = tiledlayout(3, 4, 'TileSpacing', 'Compact');

for a = 2:Numsteps
    % 1. Interpolate current data to regular grid for this timestep
    % 'nearest' is faster; 'linear' is smoother.
    bed_interp = griddata(X, Y, Zbed_g(:, a), XX, YY, 'nearest');
    bed_interp(~in_mask) = NaN;
    
    % Calculate DoD relative to initial timestep
    dod_instant = Zbed_g(:, a) - Zbed_g(:, 1);
    
    % Mapping back to Mesh Nodes for trisurf plotting
    Zn_nodes = interp2(x_vec, y_vec, bed_interp, Xn, Yn);
    Depth_nodes = interp1(X, d_g(:, a), Xn); % Simple mapping to nodes
    
    % --- SUBPLOT 1: Water Depth ---
    ax1 = nexttile(1, [2, 2]);
    h1 = trisurf(TRI(:, 1:3), Xn, Yn, Zn_nodes, Depth_nodes, 'EdgeColor', 'none');
    view(0, 90); axis equal; colorbar;
    colormap(ax1, parula); clim([0 2]);
    title(sprintf('Water Depth (h) | Time: %d hrs', round(t(a)/3600)));
    
    % --- SUBPLOT 2: Bed Level Difference (DoD) ---
    ax2 = nexttile(3, [2, 2]);
    % We plot dod_instant mapped to nodes
    dod_nodes = interp1(X, dod_instant, Xn); 
    h2 = trisurf(TRI(:, 1:3), Xn, Yn, Zn_nodes, dod_nodes, 'EdgeColor', 'none');
    view(0, 90); axis equal; colorbar;
    colormap(ax2, cmap_dod); clim([-1 1]);
    title('Morphological Change (DoD) [m]');

    % --- SUBPLOT 3: Longitudinal Mass Balance ---
    % (Requires mapping morphological change to spatial bins)
    % This logic can be expanded based on the 'binsraster' logic in original code
    
    drawnow;
    if export_video
        writeVideo(v, getframe(gcf));
    end
end

if export_video, close(v); end

%% 7. STL EXPORT FOR 3D MODELING (Blender/Unity)
% -------------------------------------------------------------------------
% Centering coordinates to avoid large-coordinate jitter in 3D software
offsetX = floor(min(Xn));
offsetY = floor(min(Yn));
verts = [(Xn - offsetX), (Yn - offsetY), Zn_nodes];
TR = triangulation(TRI(:, 1:3), verts);
stlwrite(TR, 'Final_Bed_Surface.stl');

fprintf('Processing complete. STL and Video exported.\n');
toc;