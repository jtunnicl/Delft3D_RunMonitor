% Example how to call function.
%profile on -memory
mddPlot('/home/cwal219/app_examples/Delft3D/jon', 'exportVideo', true, 'exportSTL', true, 'exportImages', true, 'nameVideo', 'video.avi', 'nameImages', 'pngs/%d.png', 'nameSTL', 'model.stl', 'gridRes', 10, 'timeRes', 50);
%profsave(profile('info'), 'my_profile_results');