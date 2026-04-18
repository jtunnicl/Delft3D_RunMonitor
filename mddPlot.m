function result = mddPlot(caseFolder, options)
%MDDPLOT Summarize Delft3D-FM multi-domain output in MATLAB.
%   RESULT = MDDPLOT(CASEFOLDER) locates a history file, one or more map
%   files, and a single net file beneath CASEFOLDER, then generates a
%   summary figure showing water depth, bed-level change, and time-series
%   context for the run.
%
%   RESULT = MDDPLOT(..., Name=Value) overrides file patterns, export
%   options, and plotting parameters.
%
%   Supported outputs:
%     - AVI animation via 'exportVideo'
%     - PNG frame export via 'exportImages'
%     - STL export of the final bed surface via 'exportSTL'
%
%   Notes:
%     - CASEFOLDER defaults to the current working directory.
%     - 'xsFile' and 'rasterBin' are retained for backwards compatibility;
%       they are not required by the current plotting workflow.
%     - The net file must describe triangular elements.
    arguments
        caseFolder {mustBeFolder} = pwd
        options.rasterBin {mustBeText} = '*.tif'
        options.xsFile {mustBeText} = '*.txt'
        options.hisFile {mustBeText} = '*/*his.nc'   % Relative to 'caseFolder'
        options.mapFiles {mustBeText} = '*/*map.nc'  % Relative to 'caseFolder'
        options.netFiles {mustBeText} = '*net.nc'    % Relative to 'caseFolder'
        options.exportVideo logical = true
        options.exportImages logical = false
        options.exportSTL logical = false
        options.visible logical = true
        options.nameVideo {mustBeText} = 'Simulation_Summary.avi'
        options.nameImages {mustBeText} = 'images/step_%d.png'
        options.nameSTL {mustBeText} = 'Final_Bed_Surface.stl'
        options.rhoS double {mustBePositive} = 1600
        options.width double {mustBePositive} = 47.17
        options.gridRes double {mustBePositive} = 1.0
        options.timeRes double {mustBePositive, mustBeInteger} = 1
    end

    caseFolder = char(string(caseFolder));

    hisFile = singleFileGlob(caseFolder, options.hisFile, true);
    mapFiles = multiFileGlob(caseFolder, options.mapFiles);
    netFile = singleFileGlob(caseFolder, options.netFiles, true);
    xsFile = singleFileGlob(caseFolder, options.xsFile, false);

    fprintf('mddPlot case folder: %s\n', caseFolder);
    fprintf('  History file: %s\n', hisFile);
    fprintf('  Network file: %s\n', netFile);
    fprintf('  Map files: %d\n', numel(mapFiles));
    if ~isempty(xsFile)
        fprintf('  Cross-section file: %s\n', xsFile);
    else
        fprintf('  Cross-section file: not used\n');
    end

    result = struct();
    result.caseFolder = caseFolder;
    result.files = struct(...
        'history', hisFile, ...
        'network', netFile, ...
        'maps', {mapFiles}, ...
        'crossSections', xsFile, ...
        'rasterBin', char(string(options.rasterBin)));

    isHeadless = isempty(getenv('DISPLAY')) || ~usejava('desktop');
    defaultFigureVisible = get(groot, 'DefaultFigureVisible');
    cleanupFigureVisibility = onCleanup(@() set(groot, 'DefaultFigureVisible', defaultFigureVisible)); %#ok<NASGU>
    if isHeadless
        fprintf('No DISPLAY available: switching to headless plotting mode. Figures are invisible.\n');
        set(groot, 'DefaultFigureVisible', 'off');
        if options.exportVideo
            warning('No Display set. Video cannot be rendered. Try xvfb-run if video export is required.');
            options.exportVideo = false;
        end
    end

    fprintf('Loading history data...\n');
    t = ncread(hisFile, 'time');
    t = t(:);
    if numel(t) < 2
        error('History file %s must contain at least two time samples.', hisFile);
    end

    dt = t(2) - t(1);
    Qw = ncread(hisFile, 'cross_section_discharge');
    QsCum = ncread(hisFile, 'cross_section_bedload_sediment_transport');
    Qs = diff(QsCum, 1, 2) / dt / options.width / options.rhoS;

    QwPlot = prepareTimeSeriesMatrix(Qw, numel(t), 'cross_section_discharge');
    QsPlot = prepareTimeSeriesMatrix(Qs, numel(t) - 1, 'cross_section_bedload_sediment_transport');
    tHours = t / 3600;
    qsHours = tHours(2:end);

    fprintf('Parsing network and partition info...\n');
    numSteps = numel(ncread(mapFiles{1}, 'time'));
    if options.timeRes > numSteps
        warning('timeRes (%d) is greater than numSteps (%d); using 1.', options.timeRes, numSteps);
        options.timeRes = 1;
    end

    timeSteps = 1:options.timeRes:numSteps;
    numFrames = numel(timeSteps);
    fprintf('%d timesteps (%d frames after timeRes=%d).\n', numSteps, numFrames, options.timeRes);

    links = ncread(netFile, 'NetElemLink')';
    Xn = ncread(netFile, 'mesh2d_node_x');
    Yn = ncread(netFile, 'mesh2d_node_y');
    TRI = ncread(netFile, 'NetElemNode')';
    if size(TRI, 2) < 3
        error('Net file %s does not contain triangular element connectivity.', netFile);
    end
    if size(TRI, 2) > 3 && any(TRI(:, 4:end) > 0, 'all')
        error('mddPlot only supports triangular NetElemNode connectivity.');
    end
    TRI = TRI(:, 1:3);
    idomainSize = size(links, 1);

    X = nan(idomainSize, 1);
    Y = nan(idomainSize, 1);

    fprintf('Looping through partitions to collect static and initial data.\n');
    for q = 1:numel(mapFiles)
        try
            gIdx = int32(ncread(mapFiles{q}, 'mesh2d_flowelem_globalnr'));
            X(gIdx) = ncread(mapFiles{q}, 'mesh2d_face_x');
            Y(gIdx) = ncread(mapFiles{q}, 'mesh2d_face_y');
        catch ME
            warning('Could not read geometry from %s (%s).', mapFiles{q}, ME.message);
        end
    end

    faceMask = isfinite(X) & isfinite(Y);
    if ~any(faceMask)
        error('No valid face coordinates were recovered from the map files.');
    end

    [waterDepthStart, waterLevelStart] = readStepData(mapFiles, idomainSize, 1);
    zBedStart = waterLevelStart - waterDepthStart;

    fprintf('Interpolate to regular grid.\n');
    xVec = floor(min(X(faceMask))):options.gridRes:ceil(max(X(faceMask)));
    yVec = floor(min(Y(faceMask))):options.gridRes:ceil(max(Y(faceMask)));
    [XX, YY] = meshgrid(xVec, yVec);

    fprintf('Creating a mask for the active flow area using an alphaShape\n');
    shp = alphaShape(X(faceMask), Y(faceMask));
    inMask = inShape(shp, XX, YY);

    if options.exportVideo
        mkOutputDir(options.nameVideo);
        v = VideoWriter(options.nameVideo);
        v.FrameRate = 10;
        open(v);
    end

    m1 = 128;
    r = [linspace(0, 1, m1)'; ones(m1, 1)];
    g = [linspace(0, 1, m1)'; linspace(1, 0, m1)'];
    b = [ones(m1, 1); linspace(1, 0, m1)'];
    cmapDod = [r g b];

    hasXsFile = ~isempty(xsFile);
    if hasXsFile
        try
            load(xsFile); %#ok<LOAD>
        catch ME
            warning('Could not load cross-section file %s (%s). Continuing without it.', xsFile, ME.message);
            hasXsFile = false;
        end
    end

    fig = figure('Visible', 'off', 'Position', [10 370 1280 976], 'Color', 'w');
    tlo = tiledlayout(3, 4, 'TileSpacing', 'Compact');
    title(tlo, sprintf('Delft3D-FM run summary: %s', caseFolder), 'Interpreter', 'none');

    ax1 = nexttile(tlo, 1, [2, 2]);
    ax2 = nexttile(tlo, 3, [2, 2]);
    ax3 = nexttile(tlo, 9, [1, 2]);
    ax4 = nexttile(tlo, 11, [1, 2]);

    lastRenderedStep = timeSteps(1);
    lastBedSurface = [];

    for frameIndex = 1:numFrames
        timeIndex = timeSteps(frameIndex);
        lastRenderedStep = timeIndex;
        fprintf('Processing frame %d/%d (step %d).\n', frameIndex, numFrames, timeIndex);

        [waterDepth, waterLevel] = readStepData(mapFiles, idomainSize, timeIndex);
        zBed = waterLevel - waterDepth;
        lastBedSurface = zBed;
        dodInstant = zBed - zBedStart;

        bedInterpolant = buildInterpolant(X, Y, zBed);
        depthInterpolant = buildInterpolant(X, Y, waterDepth);
        dodInterpolant = buildInterpolant(X, Y, dodInstant);

        bedInterp = bedInterpolant(XX, YY);
        bedInterp(~inMask) = NaN;

        znNodes = bedInterpolant(Xn, Yn);
        depthNodes = depthInterpolant(Xn, Yn);
        dodNodes = dodInterpolant(Xn, Yn);

        cla(ax1);
        trisurf(ax1, TRI, Xn, Yn, znNodes, depthNodes, 'EdgeColor', 'none');
        view(ax1, 0, 90);
        axis(ax1, 'equal');
        colorbar(ax1);
        colormap(ax1, parula);
        clim(ax1, [0 2]);
        title(ax1, sprintf('Water Depth (h) | Time: %.2f h', tHours(timeIndex)));
        xlabel(ax1, 'Easting');
        ylabel(ax1, 'Northing');

        cla(ax2);
        trisurf(ax2, TRI, Xn, Yn, znNodes, dodNodes, 'EdgeColor', 'none');
        view(ax2, 0, 90);
        axis(ax2, 'equal');
        colorbar(ax2);
        colormap(ax2, cmapDod);
        clim(ax2, [-1 1]);
        title(ax2, 'Morphological Change (DoD) [m]');
        xlabel(ax2, 'Easting');
        ylabel(ax2, 'Northing');

        cla(ax3);
        plotHistoryPanel(ax3, tHours, QwPlot, tHours(timeIndex), 'Discharge history', 'Q_w [m^3 s^{-1}]');

        cla(ax4);
        qsMarker = qsHours(max(1, min(numel(qsHours), timeIndex - 1)));
        plotHistoryPanel(ax4, qsHours, QsPlot, qsMarker, 'Bedload transport history', 'Q_s [m^3 m^{-1} s^{-1}]');

        if hasXsFile
            subtitle(tlo, sprintf('Cross-section definition found: %s', xsFile), 'Interpreter', 'none');
        else
            subtitle(tlo, 'Cross-section overlay not used in the current MATLAB workflow.');
        end

        drawnow;
        if options.exportVideo
            writeVideo(v, getframe(fig));
        end
        if options.exportImages
            imageName = sprintf(options.nameImages, timeIndex);
            mkOutputDir(imageName);

            img = print(fig, '-RGBImage');
            imwrite(img, imageName);
            fprintf('Step %d written to %s.\n', timeIndex, imageName);
        end
    end

    if options.exportVideo
        close(v);
    end

    if options.visible && ~isHeadless
        fig.Visible = 'on';
        drawnow;
    end

    if options.exportSTL
        if isempty(lastBedSurface)
            error('STL export failed because no frame was rendered.');
        end

        mkOutputDir(options.nameSTL);
        offsetX = floor(min(Xn));
        offsetY = floor(min(Yn));
        finalBedInterpolant = buildInterpolant(X, Y, lastBedSurface);
        finalZnNodes = finalBedInterpolant(Xn, Yn);
        verts = [(Xn - offsetX), (Yn - offsetY), finalZnNodes];

        valid = all(isfinite(verts), 2);
        if any(~valid)
            warning('STL export: dropping %d invalid vertices containing NaN/Inf.', nnz(~valid));
            triMask = all(valid(TRI), 2);
            if ~any(triMask)
                error('STL export failed: no valid triangles remain after removing non-finite vertices.');
            end
            newIndex = zeros(size(valid));
            newIndex(valid) = 1:nnz(valid);
            cleanVerts = verts(valid, :);
            cleanTri = newIndex(TRI(triMask, :));
            TR = triangulation(cleanTri, cleanVerts);
        else
            TR = triangulation(TRI, verts);
        end

        stlwrite(TR, options.nameSTL);
        fprintf('Processing complete. STL exported.\n');
    end

    result.summary = struct(...
        'numPartitions', numel(mapFiles), ...
        'numTimeSteps', numSteps, ...
        'numFrames', numFrames, ...
        'lastRenderedStep', lastRenderedStep, ...
        'headless', isHeadless);
    result.outputs = struct(...
        'video', ternary(options.exportVideo, options.nameVideo, ''), ...
        'imagesPattern', ternary(options.exportImages, options.nameImages, ''), ...
        'stl', ternary(options.exportSTL, options.nameSTL, ''));
end

function path = singleFileGlob(baseFolder, pattern, required)
    candidates = unique(localDirMatches(baseFolder, pattern), 'stable');
    if isempty(candidates)
        if required
            error('No files found matching %s under %s.', pattern, baseFolder);
        end
        path = '';
        return;
    end

    path = candidates{1};
    if numel(candidates) > 1
        warning('Multiple files found matching %s; using %s', pattern, path);
    end
end

function paths = multiFileGlob(baseFolder, pattern)
    paths = unique(localDirMatches(baseFolder, pattern), 'stable');
    assert(~isempty(paths), 'No files found matching %s under %s.', pattern, baseFolder);
    paths = sort(paths);
end

function paths = localDirMatches(baseFolder, pattern)
    paths = {};
    patternText = char(string(pattern));
    if strlength(string(patternText)) == 0
        return;
    end

    patternList = {patternText};
    if isAbsolutePath(patternText)
        patternList = [patternList, {fullfile(baseFolder, patternText)}]; %#ok<AGROW>
    else
        patternList = [{fullfile(baseFolder, patternText)}, patternList]; %#ok<AGROW>
    end

    for idx = 1:numel(patternList)
        dirs = dir(patternList{idx});
        if isempty(dirs)
            continue;
        end

        dirs = dirs(~[dirs.isdir]);
        if isempty(dirs)
            continue;
        end

        paths = [paths, fullfile({dirs.folder}, {dirs.name})]; %#ok<AGROW>
    end
end

function tf = isAbsolutePath(pathText)
    tf = startsWith(pathText, filesep) || ~isempty(regexp(pathText, '^[A-Za-z]:[\\/]', 'once'));
end

function mkOutputDir(filePath)
    [folder, ~, ~] = fileparts(filePath);
    if ~isempty(folder) && exist(folder, 'dir') ~= 7
        fprintf('Creating directory %s\n', folder);
        mkdir(folder);
    end
end

function [waterDepth, waterLevel] = readStepData(mapFiles, idomainSize, timeIndex)
    waterDepth = nan(idomainSize, 1);
    waterLevel = nan(idomainSize, 1);

    for q = 1:numel(mapFiles)
        try
            gIdx = int32(ncread(mapFiles{q}, 'mesh2d_flowelem_globalnr'));
            waterDepth(gIdx) = ncread(mapFiles{q}, 'mesh2d_waterdepth', [1 timeIndex], [inf 1]);
            waterLevel(gIdx) = ncread(mapFiles{q}, 'mesh2d_s1', [1 timeIndex], [inf 1]);
        catch ME
            warning('Could not read timestep %d from %s (%s).', timeIndex, mapFiles{q}, ME.message);
        end
    end
end

function interpolant = buildInterpolant(xValues, yValues, zValues)
    valid = isfinite(xValues) & isfinite(yValues) & isfinite(zValues);
    if ~any(valid)
        error('Interpolation failed because no finite values were available.');
    end

    interpolant = scatteredInterpolant(xValues(valid), yValues(valid), zValues(valid), 'nearest', 'none');
end

function series = prepareTimeSeriesMatrix(data, expectedLength, variableName)
    data = squeeze(data);

    if isvector(data)
        series = reshape(data, [], 1);
    elseif size(data, 1) == expectedLength
        series = data;
    elseif size(data, 2) == expectedLength
        series = data.';
    else
        error('Variable %s does not contain a dimension of length %d.', variableName, expectedLength);
    end

    if size(series, 1) ~= expectedLength
        error('Variable %s could not be reshaped to %d timesteps.', variableName, expectedLength);
    end
end

function plotHistoryPanel(ax, timeHours, series, currentHour, panelTitle, yLabelText)
    if size(series, 2) == 1
        plot(ax, timeHours, series, 'LineWidth', 1.5, 'Color', [0.1 0.3 0.7]);
    else
        plot(ax, timeHours, series, 'Color', [0.75 0.75 0.75]);
        hold(ax, 'on');
        plot(ax, timeHours, mean(series, 2, 'omitnan'), 'LineWidth', 1.5, 'Color', [0.1 0.1 0.1]);
    end

    hold(ax, 'on');
    xline(ax, currentHour, '--', 'Color', [0.8 0.2 0.2], 'LineWidth', 1.2);
    grid(ax, 'on');
    title(ax, panelTitle);
    xlabel(ax, 'Time [h]');
    ylabel(ax, yLabelText);
    xlim(ax, [timeHours(1), timeHours(end)]);
end

function value = ternary(condition, trueValue, falseValue)
    if condition
        value = trueValue;
    else
        value = falseValue;
    end
end