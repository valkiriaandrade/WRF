import subprocess
import sys


def test_import_has_no_output(tmp_path):
    # A fresh interpreter: in this test session the package is already imported.
    code = (
        "import wrf_maps.cli, wrf_maps.plotting, sys; sys.exit('matplotlib.pyplot' in sys.modules)"
    )
    subprocess.run([sys.executable, "-c", code], cwd=tmp_path, check=True)
    assert not list(tmp_path.iterdir())


def test_offline_map_and_figure_cleanup(tmp_path):
    import geopandas as gpd
    import matplotlib.pyplot as plt
    from shapely.geometry import box

    from wrf_maps.plotting import plot_map

    borders = tmp_path / "bounds.geojson"
    gpd.GeoDataFrame(geometry=[box(-2, -2, 2, 2)], crs=4326).to_file(borders)
    output = tmp_path / "maps" / "sample.png"
    plot_map(
        [[1, 2], [3, 4]],
        [-1, 1],
        [359, 1],
        output,
        title="Test",
        label="mm",
        levels=[0, 2, 5],
        cmap="BrBG",
        shapefile=borders,
    )
    assert output.read_bytes().startswith(b"\x89PNG")
    assert not plt.get_fignums()
