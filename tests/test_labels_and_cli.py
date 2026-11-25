import argparse
from datetime import datetime

import numpy as np
import pytest

from wrf_maps.arguments import positive_int
from wrf_maps.cli import build_cli
from wrf_maps.labels import (
    format_time,
    format_title,
    kelvin_to_celsius,
    run_time_from_name,
)
from wrf_maps.regions import REGIONS, normalize_region

NAME = "WRF_cpt_07KM_SU_2024082112_2024082609.grib2"


@pytest.mark.parametrize(
    ("value", "expected"),
    [("domain", "domain"), ("south", "south"), ("sul", "south"), ("SUL", "south")],
)
def test_region_names_and_portuguese_alias(value, expected):
    assert normalize_region(value) == expected


def test_unknown_region():
    with pytest.raises(argparse.ArgumentTypeError, match="domain, south, sul"):
        normalize_region("north")


def test_cli_defaults_alias_and_dpi():
    args = build_cli().parse_args(["--input", NAME, "--output", "o.png", "--region", "sul"])
    assert args.region == "south"
    assert REGIONS[args.region].states == ("PR", "SC", "RS")
    assert args.dpi == 200
    assert build_cli().parse_args(["--input", NAME, "--output", "o.png"]).region == "domain"
    with pytest.raises(argparse.ArgumentTypeError):
        positive_int("0")


@pytest.mark.parametrize(
    ("kelvin", "celsius"), [(273.15, 0.0), (233.15, -40.0), (310.15, 37.0), (0.0, -273.15)]
)
def test_kelvin_to_celsius(kelvin, celsius):
    assert float(kelvin_to_celsius(kelvin)) == pytest.approx(celsius)


def test_kelvin_to_celsius_keeps_shape_and_nan():
    result = kelvin_to_celsius(np.array([[273.15, np.nan]]))
    assert result.shape == (1, 2)
    assert np.isnan(result[0, 1])


def test_run_time_from_provider_name():
    assert run_time_from_name(f"data/{NAME}") == datetime(2024, 8, 21, 12)
    assert run_time_from_name("my_output.grib2") is None


def test_title_formatting():
    valid = datetime(2024, 8, 26, 9)
    assert format_time(valid) == "26 Aug 2024 09 UTC"
    assert format_title(valid, "Southern Brazil", datetime(2024, 8, 21, 12)) == (
        "WRF 2 m temperature (°C) – Southern Brazil\n"
        "Valid 26 Aug 2024 09 UTC · run 21 Aug 2024 12 UTC"
    )
    assert format_title(valid) == "WRF 2 m temperature (°C)\nValid 26 Aug 2024 09 UTC"
