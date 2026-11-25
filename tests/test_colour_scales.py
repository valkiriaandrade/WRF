import numpy as np
import pytest

from wrf_maps.cli import build_cli
from wrf_maps.colour_scales import data_range, nice_step, temperature_levels

LAT, LON = np.meshgrid(np.linspace(-35, -20, 20), np.linspace(-60, -45, 20), indexing="ij")


def field(low, high):
    return np.linspace(low, high, LAT.size).reshape(LAT.shape)


@pytest.mark.parametrize(("span", "step"), [(5, 0.5), (18, 1.0), (40, 2.0), (100, 5.0)])
def test_nice_step(span, step):
    assert nice_step(span) == step


def test_winter_map_keeps_contrast():
    levels = temperature_levels(field(-2.3, 17.6), LAT, LON)
    assert levels[0] <= -2 and levels[-1] >= 17
    assert levels[1] - levels[0] == 1.0
    assert len(levels) - 1 <= 24


def test_summer_map_uses_its_own_range():
    levels = temperature_levels(field(18.0, 41.0), LAT, LON)
    assert levels[0] >= 18 and levels[-1] <= 42


def test_explicit_vmin_vmax_and_partial_override():
    levels = temperature_levels(field(0, 30), LAT, LON, vmin=-3, vmax=15)
    np.testing.assert_allclose(levels, np.arange(-3, 16, 1))
    assert temperature_levels(field(0, 30), LAT, LON, vmin=10)[0] == 10
    with pytest.raises(ValueError, match="lower than"):
        temperature_levels(field(0, 30), LAT, LON, vmin=5, vmax=5)


def test_range_ignores_nan_and_points_outside_extent():
    values = field(0, 10)
    values[0, 0] = np.nan
    values[LON > -50] = 100.0
    low, high = data_range(values, LAT, LON, extent=(-60, -50, -35, -20))
    assert high < 100
    with pytest.raises(ValueError, match="No valid"):
        data_range(values, LAT, LON, extent=(0, 1, 0, 1))


def test_cli_vmin_vmax_options():
    args = build_cli().parse_args(["--input", "x", "--output", "o.png", "--vmin", "-5"])
    assert args.vmin == -5.0 and args.vmax is None
