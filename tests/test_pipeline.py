"""The command behind the published map, run offline on the committed sample."""

import logging
import sys
from datetime import datetime
from types import SimpleNamespace

import numpy as np
import pytest
from conftest import ROOT, load_script

from wrf_maps import cli
from wrf_maps.io import read_grib

pytest.importorskip("eccodes")
SAMPLE = ROOT / "data" / "WRF_cpt_07KM_SU_2024082112_2024082609.grib2"


@pytest.fixture
def states(tmp_path):
    """Three boxes standing in for PR, SC and RS, plus one for the rest of the domain."""
    import geopandas as gpd
    from shapely.geometry import box

    path = tmp_path / "states.geojson"
    gpd.GeoDataFrame(
        {"SIGLA_UF": ["PR", "SC", "RS", "XX"]},
        geometry=[
            box(-54.6, -26.7, -48.0, -22.5),
            box(-53.8, -29.4, -48.3, -26.7),
            box(-57.6, -33.75, -49.7, -29.4),
            box(-60.0, -37.0, -45.0, -20.0),
        ],
        crs=4326,
    ).to_file(path)
    return path


@pytest.fixture
def drawn(monkeypatch):
    """Keep what the CLI passes to plot_map, and still draw the PNG."""
    calls = []
    real = cli.plot_map

    def spy(values, lat, lon, output, **kwargs):
        calls.append(SimpleNamespace(values=values, **kwargs))
        real(values, lat, lon, output, **kwargs)

    monkeypatch.setattr(cli, "plot_map", spy)
    return calls


def test_sample_is_geolocated_and_oriented():
    field = read_grib(SAMPLE, "2 metre temperature")
    lat, lon = field.lat, field.lon
    assert lat[0, 0] == pytest.approx(-36.97, abs=0.01) and lon[0, 0] == pytest.approx(
        -59.94, abs=0.01
    )
    assert lat[-1, -1] == pytest.approx(-20.03, abs=0.01) and lon[-1, -1] == pytest.approx(
        -45.03, abs=0.01
    )
    assert np.all(np.diff(lat[:, 0]) > 0) and np.all(np.diff(lon[0]) > 0)
    # That cold morning the minimum (−4.6 °C) is on the Santa Catarina highlands, at São Joaquim.
    coldest = np.unravel_index(np.nanargmin(field.values), field.values.shape)
    assert lat[coldest] == pytest.approx(-28.29, abs=0.1) and lon[coldest] == pytest.approx(
        -49.93, abs=0.1
    )
    assert field.values[coldest] - 273.15 == pytest.approx(-4.57, abs=0.01)


def test_published_map_command(tmp_path, states, drawn):
    output = tmp_path / "t2m.png"
    cli.main(["--input", str(SAMPLE), "--shapefile", str(states), "--output", str(output)])
    assert output.read_bytes().startswith(b"\x89PNG")
    [call] = drawn
    assert call.title == (
        "WRF 2 m temperature (°C) – Southern Brazil\n"
        "Valid 26 Aug 2024 09 UTC · run 21 Aug 2024 12 UTC"
    )
    assert call.levels[0] == -1 and call.levels[-1] == 17 and call.levels[1] - call.levels[0] == 1
    assert call.cmap == "jet" and call.extend == "both" and call.extend_colours is True
    assert call.extent is None and call.states is None


def test_south_region_scale_comes_from_the_three_states_only(tmp_path, states, drawn):
    cli.main(
        ["--input", str(SAMPLE), "--region", "sul", "--shapefile", str(states)]
        + ["--output", str(tmp_path / "south.png")]
    )
    [call] = drawn
    assert call.title.startswith("WRF 2 m temperature (°C) – PR, SC and RS\n")
    assert call.states == ["PR", "SC", "RS"] and call.extent == [-57.6, -48.0, -33.75, -22.5]
    field = read_grib(SAMPLE, "2 metre temperature")
    inside = np.zeros(field.values.shape, bool)
    for x0, y0, x1, y1 in [(-54.6, -26.7, -48.0, -22.5), (-53.8, -29.4, -48.3, -26.7)] + [
        (-57.6, -33.75, -49.7, -29.4)
    ]:
        inside |= (field.lon >= x0) & (field.lon <= x1) & (field.lat >= y0) & (field.lat <= y1)
    low, high = np.percentile(field.values[inside] - 273.15, [1, 99])
    assert call.levels[0] == np.floor(low) and call.levels[-1] == np.ceil(high)


def test_cli_reports_bad_input_in_one_line(tmp_path, capsys):
    damaged = tmp_path / "damaged.grib2"
    damaged.write_bytes(SAMPLE.read_bytes()[:5000])
    with pytest.raises(SystemExit) as stop:
        cli.main(["--input", str(damaged), "--output", str(tmp_path / "x.png")])
    assert stop.value.code == 2
    assert "Error:" in capsys.readouterr().err and not (tmp_path / "x.png").exists()


def test_verbose_debug_only_for_this_package(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "run", lambda args: None)
    root, package = logging.getLogger(), logging.getLogger("wrf_maps")
    monkeypatch.setattr(root, "level", root.level)
    monkeypatch.setattr(package, "level", package.level)
    cli.main(["--input", "x", "--output", str(tmp_path / "x.png"), "--verbose"])
    assert package.getEffectiveLevel() == logging.DEBUG
    assert logging.getLogger("matplotlib").getEffectiveLevel() > logging.DEBUG


# ---------------------------------------------------------------- read_grib checks
class FakeGrib:
    """Stand-in for the ecCodes module: messages are dicts of keys."""

    GribInternalError = type("GribInternalError", (Exception,), {})

    def __init__(self, *messages):
        self.messages, self.released = list(messages), []

    def codes_grib_new_from_file(self, stream):
        return self.messages.pop(0) if self.messages else None

    def codes_get(self, message, key):
        return message[key]

    def codes_get_values(self, message):
        return np.asarray(message["values"], dtype=float)

    def codes_get_array(self, message, key):
        return np.asarray(message[key])

    def codes_release(self, message):
        self.released.append(message)


def _t2m(**changes):
    message = {
        "name": "2 metre temperature",
        "units": "K",
        "Ni": 2,
        "Nj": 2,
        "values": [270.0, 271.0, 272.0, 273.0],
        "bitmapPresent": 0,
        "latitudes": [-30.0, -30.0, -29.0, -29.0],
        "longitudes": [300.0, 301.0, 300.0, 301.0],
        "jPointsAreConsecutive": 0,
        "validityDate": 20240826,
        "validityTime": 900,
        "dataDate": 20240821,
        "dataTime": 1200,
    }
    return {**message, **changes}


@pytest.fixture
def grib(monkeypatch, tmp_path):
    path = tmp_path / "fake.grib2"
    path.touch()

    def install(*messages):
        fake = FakeGrib(*messages)
        monkeypatch.setitem(sys.modules, "eccodes", fake)
        return fake

    return path, install


def test_read_grib_fields_times_bitmap_and_longitudes(grib):
    path, install = grib
    fake = install({"name": "10 metre wind"}, _t2m(bitmapPresent=1, bitmap=[1, 1, 0, 1]))
    field = read_grib(path, "2 metre temperature")
    assert field.valid_time == datetime(2024, 8, 26, 9) and field.run_time == datetime(
        2024, 8, 21, 12
    )
    np.testing.assert_array_equal(field.lon, [[-60, -59], [-60, -59]])
    assert np.isnan(field.values[1, 0]) and field.values[1, 1] == 273.0
    assert len(fake.released) == 2


@pytest.mark.parametrize(
    ("messages", "error"),
    [
        ([_t2m(units="C")], "must be in kelvin"),
        ([_t2m(), _t2m()], "More than one"),
        ([_t2m(Ni=3)], "regular rectangular grids"),
        ([{"name": "10 metre wind"}], "not found"),
    ],
)
def test_read_grib_rejects_ambiguous_or_wrong_fields(grib, messages, error):
    path, install = grib
    fake = install(*messages)
    with pytest.raises(ValueError, match=error):
        read_grib(path, "2 metre temperature")
    assert len(fake.released) == len(messages)  # every handle released


# ---------------------------------------------------------------- make figures
def test_make_figures_reports_skipped_and_failed(tmp_path, monkeypatch):
    make_figures = load_script("make_figures")
    monkeypatch.setattr(sys, "argv", ["make_figures", "--data-dir", str(tmp_path)])
    assert make_figures.main() == 1  # sample missing: skipped
    source = make_figures.FIGURES[0][1]
    (tmp_path / source).write_bytes(b"not a grib file")
    monkeypatch.setattr(
        make_figures, "FIGURES", [("a.png", source), ("b.png", "missing.grib2"), ("c.png", source)]
    )
    skipped, failed = make_figures.build(tmp_path, tmp_path / "figures", 50)
    assert skipped == ["b.png"] and failed == [
        "a.png",
        "c.png",
    ]  # one failure does not stop the rest
