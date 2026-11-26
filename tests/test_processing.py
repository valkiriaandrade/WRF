import sys
from datetime import datetime
from types import SimpleNamespace

import numpy as np
import pytest

from wrf_maps.cli import kelvin_to_celsius
from wrf_maps.io import read_grib


def test_kelvin_and_missing_values():
    np.testing.assert_allclose(kelvin_to_celsius([273.15, 300, np.nan]), [0, 26.85, np.nan])


def test_grib_closed_on_selection_failure(monkeypatch, tmp_path):
    closed = []
    messages = iter([1, None])
    path = tmp_path / "sample.grib2"
    path.touch()
    fake = SimpleNamespace(
        GribInternalError=type("GribInternalError", (Exception,), {}),
        codes_grib_new_from_file=lambda stream: next(messages),
        codes_get=lambda message, key: "other",
        codes_release=lambda message: closed.append(message),
    )
    monkeypatch.setitem(sys.modules, "eccodes", fake)
    with pytest.raises(ValueError):
        read_grib(path, "2 metre temperature")
    assert closed == [1]
    path.unlink()


def test_repository_grib():
    from pathlib import Path

    pytest.importorskip("eccodes")
    path = Path(__file__).parents[1] / "data/WRF_cpt_07KM_SU_2024082112_2024082609.grib2"
    field = read_grib(path, "2 metre temperature")
    values, lat, lon = field.values, field.lat, field.lon
    assert values.shape == lat.shape == lon.shape == (243, 214)
    assert field.valid_time == datetime(2024, 8, 26, 9)
    assert field.run_time == datetime(2024, 8, 21, 12)  # from the GRIB, matches the file name
    assert np.nanmin(values) > 200
    assert np.nanmax(values) < 350
