function mddPlot(caseFolder, options)
    arguments
        caseFolder {mustBeFolder} = '' 
        options.rasterBin  {mustBeText} = '*.tif'
        options.xsFile     {mustBeText} = '*.txt'
        options.hisFile    {mustBeText} = '*/*his.nc'  % Relative to 'caseFolder'
        options.mapFiles   {mustBeText} = '*/*map.nc'  % Relative to 'caseFolder'
        options.netFiles   {mustBeText} = '*net.nc'    % Relative to 'caseFolder'
        options.exportVideo logical = true
        options.exportImages logical = false
        options.exportSTL logical = false
        options.visible logical = true % whether to display plot window.
        options.nameVideo {mustBeText} = 'Simulation_Summary.avi'
        options.nameImages {mustBeText} = 'images/step_%d.png'
        options.nameSTL {mustBeText} = 'Final_Bed_Surface.stl'
        options.rhoS double {mustBePositive} = 1600
        options.width double {mustBePositive} = 47.17
        options.gridRes double {mustBePositive} = 1.0
        options.timeRes double {mustBePositive, mustBeInteger} = 1
    end

% Validate inputs
rasterBin = singleFileGlob(options.rasterBin);
xsFile = singleFileGlob(options.xsFile);
hisFile = singleFileGlob(caseFolder, options.hisFile);
mapFiles = multiFileGlob(caseFolder, options.mapFiles);
netFiles = multiFileGlob(caseFolder, options.netFiles);

% maybe print some stuff here.
% fprintf('  History File: %s', hisFile);
% fprintf('%d Network Files\n', numel(netFiles));
% fprintf('%d Map Files\n', numel(mapFiles));

if numel(mapFiles) ~= numel(netFiles)
    warning("Mismatch in output files %d net, %d map", numel(netFiles), numel(mapFiles))
end

% Non-interactive detection
isHeadless = isempty(getenv('DISPLAY')) || ~usejava('desktop');
if isHeadless
    info('No DISPLAY available: switching to headless plotting mode. Figures are invisible.');
    set(0, 'DefaultFigureVisible', 'off');
    if options.exportVideo
        warning('No Display set. Video cannot be rendered. (try using `xvfb-run`).');
        options.exportVideo = false
    end
end

%% 2. LOAD TIME SERIES DATA (History File)
% -------------------------------------------------------------------------
fprintf('Loading history data...\n');
t = ncread(hisFile, 'time');
dt = t(2) - t(1);

% Qw: Discharge (m3/s) | Qs: Cumulative Bedload (kg)
Qw = ncread(hisFile, 'cross_section_discharge'); 
QsCum = ncread(hisFile, 'cross_section_bedload_sediment_transport');

% Convert cumulative mass to instantaneous volumetric flux (m3/m/s)
% diff() gets the mass per timestep, then divide by time, width, and density.
Qs = diff(QsCum, 1, 2) / dt / options.width / options.rhoS;

%% 3. LOAD MESH & DOMAIN STRUCTURE (Network File)
% -------------------------------------------------------------------------
fprintf('Parsing network and partition info...\n');
vInfo = ncinfo(netFiles{1});
numSteps = size(ncread(mapFiles{1}, 'time'), 1);
if options.timeRes > numSteps
    warning('timeRes (%d) is greater than numSteps (%d); using 1.', options.timeRes, numSteps);
    options.timeRes = 1;
end

timeSteps = 1:options.timeRes:numSteps;
numFrames = numel(timeSteps);
fprintf('%d timesteps (%d frames after timeRes=%d).\n', numSteps, numFrames, options.timeRes);

% Extract number of partitions from the idomain attribute

% Could add check to confirm number files same as in partition info.
% partitions = vInfo.Variables.mesh2d_netelem_domain

% Newer delft outputs use this updated schema. % possibly add test for old format.
links = ncread(netFiles{1}, 'NetElemLink')';
Xn = ncread(netFiles{1}, 'mesh2d_node_x');
Yn = ncread(netFiles{1}, 'mesh2d_node_y');
Zn = ncread(netFiles{1}, 'mesh2d_node_z');
TRI = ncread(netFiles{1}, 'NetElemNode')'; % Triangulation connectivity
idomainSize = size(links, 1);

%% 4. AGGREGATE MULTI-DOMAIN SPATIAL DATA
% -------------------------------------------------------------------------
% Pre-allocate global arrays for speed
X = zeros(idomainSize, 1);
Y = zeros(idomainSize, 1);
waterDepthStart = zeros(idomainSize, 1);     % Water depth
waterLevelStart = zeros(idomainSize, 1);    % Water level (s1)
% medianGrainSize = zeros(idomainSize, 1);    % Median grain size (D50)

fprintf('Looping through partitions to collect static and initial data.\n');
for q = 1:numel(mapFiles)
    try
        %fname = sprintf('%s_%04d_map.nc', map_prefix, q);'
        %fprintf('\r    %s\n\r', mapFiles{q})
        % Global mapping indices for this partition
        gIdx = int32(ncread(mapFiles{q}, 'mesh2d_flowelem_globalnr'));
        
        % Static Geometry
        X(gIdx) = ncread(mapFiles{q}, 'mesh2d_face_x');
        Y(gIdx) = ncread(mapFiles{q}, 'mesh2d_face_y');
    catch ME
        warning('Could not read %s', mapFiles{q})
    end
end

% Read initial dynamic data
[waterDepthStart, waterLevelStart, ~] = readStepData(mapFiles, idomainSize, 1);
zBedStart = waterLevelStart - waterDepthStart;

fprintf('Interpolate to regular grid.\n');

% Derived Bed Elevation (zBed = waterLevel - waterDepth)

%% 5. GRID INTERPOLATION SETUP
% -------------------------------------------------------------------------
% Define a regular grid for raster-based analysis and plotting
xVec = floor(min(X)):options.gridRes:ceil(max(X));
yVec = floor(min(Y)):options.gridRes:ceil(max(Y));
[XX, YY] = meshgrid(xVec, yVec);

fprintf('Creating a mask for the active flow area using an alphaShape\n')
shp = alphaShape(X, Y);
inMask = inShape(shp, XX, YY);

%% 6. VISUALIZATION: DEPTH & DOD ANIMATION
% -------------------------------------------------------------------------

if options.exportVideo
    mkOutputDir(options.nameVideo);
    v = VideoWriter(options.nameVideo);
    v.FrameRate = 10;
    open(v);
end

% Setup custom colormaps
% Red-Blue for DoD (Erosion/Deposition)
m1 = 128;
r = [linspace(0, 1, m1)'; ones(m1, 1)];
g = [linspace(0, 1, m1)'; linspace(1, 0, m1)'];
b = [ones(m1, 1); linspace(1, 0, m1)'];
cmapDod = [r g b];

% Load Cross-section locations
xs = load(xsFile);
xsOrder = [1:2:25, 29 31 33 37 35 39]; 

fig = figure('Visible', 'off', 'Position', [10 370 1280 976], 'Color', 'w');

tlo = tiledlayout(3, 4, 'TileSpacing', 'Compact');

for frameIndex = 1:numFrames
    a = timeSteps(frameIndex);
    fprintf('Processing frame %d/%d (step %d).\n', frameIndex, numFrames, a);
    % Read data for this step
    [waterDepth, waterLevel, medianGrainSize] = readStepData(mapFiles, idomainSize, a);
    
    % Compute derived bed for this step
    zBed = waterLevel - waterDepth;
    
    % Interpolate to grid
    bedInterp = griddata(X, Y, zBed, XX, YY, 'nearest');
    bedInterp(~inMask) = NaN;
    
    % Compute DoD
    dodInstant = zBed - zBedStart;
    
    % Mapping to nodes for plotting
    ZnNodes = interp2(xVec, yVec, bedInterp, Xn, Yn);
    depthNodes = interp1(X, waterDepth, Xn);
    dodNodes = interp1(X, dodInstant, Xn);
    ax1 = nexttile(1, [2, 2]);
    h1 = trisurf(TRI(:, 1:3), Xn, Yn, ZnNodes, depthNodes, 'EdgeColor', 'none');
    view(0, 90); axis equal; colorbar;
    colormap(ax1, parula); clim([0 2]);
    title(sprintf('Water Depth (h) | Time: %d hrs', round(t(a)/3600)));
    
    % --- SUBPLOT 2: Bed Level Difference (DoD) ---
    ax2 = nexttile(3, [2, 2]);
    % We plot dodInstant mapped to nodes
    dodNodes = interp1(X, dodInstant, Xn); 
    h2 = trisurf(TRI(:, 1:3), Xn, Yn, ZnNodes, dodNodes, 'EdgeColor', 'none');
    view(0, 90); axis equal; colorbar;
    colormap(ax2, cmapDod); clim([-1 1]);
    title('Morphological Change (DoD) [m]');

    % --- SUBPLOT 3: Longitudinal Mass Balance ---
    % (Requires mapping morphological change to spatial bins)
    % This logic can be expanded based on the 'binsraster' logic in original code
    
    % Export frame
    drawnow;
    if options.exportVideo
        writeVideo(v, getframe(fig));
    end
    if options.exportImages
        imageName = sprintf(options.nameImages, a);
        mkOutputDir(imageName);
        
        img = print(fig, '-RGBImage');
        imwrite(img, imageName);
        fprintf('Step %d written to %s.\n', a, imageName );
    end
end

if options.exportVideo
    close(v);
end

% Show plot window after all processing if requested
if options.visible && ~isHeadless
    fig.Visible = 'on';
    drawnow;
end

%% 7. STL EXPORT FOR 3D MODELING (Blender/Unity)
% -------------------------------------------------------------------------
% Centering coordinates to avoid large-coordinate jitter in 3D software
if options.exportSTL
    mkOutputDir(options.nameSTL);
    offsetX = floor(min(Xn));
    offsetY = floor(min(Yn));
    verts = [(Xn - offsetX), (Yn - offsetY), ZnNodes];

    valid = all(isfinite(verts), 2);
    if any(~valid)
        warning('STL export: dropping %d invalid vertices containing NaN/Inf.', nnz(~valid));
        triMask = all(valid(TRI(:, 1:3)), 2);
        if ~any(triMask)
            error('STL export failed: no valid triangles remain after removing non-finite vertices.');
        end
        newIndex = zeros(size(valid));
        newIndex(valid) = 1:nnz(valid);
        cleanVerts = verts(valid, :);
        cleanTri = newIndex(TRI(triMask, 1:3));
        TR = triangulation(cleanTri, cleanVerts);
    else
        TR = triangulation(TRI(:, 1:3), verts);
    end

    stlwrite(TR, options.nameSTL);

    fprintf('Processing complete. STL exported.\n');
end

% matlab doesn't natively expand globs.
function [path] = singleFileGlob(varargin)
    pattern = fullfile(varargin{:});
    dirs = dir(pattern);
    path = fullfile(dirs(1).folder, dirs(1).name);
    if numel(dirs) > 1
        warning('Multiple files found matching %s; using %s', pattern, path);
    end
end

function [paths] = multiFileGlob(varargin)

    pattern = fullfile(varargin{:});
    dirs = dir(pattern);
    assert(~isempty(dirs), 'No files found matching %s', pattern);

    paths = sort(fullfile({dirs.folder}, {dirs.name}));
end

function mkOutputDir(filePath)
    [folder, ~, ~] = fileparts(filePath);
    if ~isempty(folder) && exist(fullfile(pwd, folder), 'dir') ~= 7
        fprintf('Creating directory %s\n', folder);
        mkdir(folder);
    end
end

function [waterDepth, waterLevel, medianGrainSize] = readStepData(mapFiles, idomainSize, a)
    waterDepth = zeros(idomainSize, 1);
    waterLevel = zeros(idomainSize, 1);
    medianGrainSize = zeros(idomainSize, 1);
    
    for q = 1:numel(mapFiles)
        try
            %fprintf('\r    %s\n', mapFiles{q})
            gIdx = int32(ncread(mapFiles{q}, 'mesh2d_flowelem_globalnr'));
            waterDepth(gIdx) = ncread(mapFiles{q}, 'mesh2d_waterdepth', [1 a], [inf 1]);
            waterLevel(gIdx) = ncread(mapFiles{q}, 'mesh2d_s1', [1 a], [inf 1]);
            medianGrainSize(gIdx) = ncread(mapFiles{q}, 'mesh2d_dg', [1 a], [inf 1]);
        catch ME
            warning('Could not read %s', mapFiles{q})
        end
    end
end
end