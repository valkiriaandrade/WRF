"""Colour scale of the 2 m temperature map.

The palette (``jet``, both ends extended) is the one of the original
``Scripts/2m_temperatura.py``. Instead of the original fixed −3…15 °C, the class
boundaries follow the data range of each map, so both winter and summer maps keep
their contrast; ``--vmin``/``--vmax`` fix either end explicitly (kept exactly as given).
"""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

CMAP = "jet"
EXTEND = "both"
#: Lower/upper percentiles used for the automatic range (robust to a few outliers;
#: values outside the range are still shown by the colorbar arrows).
PERCENTILES = (1.0, 99.0)
NICE_STEPS = (0.5, 1.0, 2.0, 5.0, 10.0)
MAX_CLASSES = 24


def nice_step(span: float, max_classes: int = MAX_CLASSES) -> float:
    """Smallest step in :data:`NICE_STEPS` that splits ``span`` into ≤ ``max_classes``.

    >>> nice_step(18), nice_step(30), nice_step(8)
    (1.0, 2.0, 0.5)
    """
    for step in NICE_STEPS:
        if span / step <= max_classes:
            return step
    return NICE_STEPS[-1] * math.ceil(span / (NICE_STEPS[-1] * max_classes))


def data_range(
    values: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
    extent: Sequence[float] | None = None,
) -> tuple[float, float]:
    """1st–99th percentile of the finite values inside ``extent`` (lon/lat box)."""
    values = np.asarray(values, dtype=float)
    inside = np.isfinite(values)
    if extent is not None:
        lon_min, lon_max, lat_min, lat_max = extent
        lon = (np.asarray(lon) + 180) % 360 - 180
        inside &= (lon >= lon_min) & (lon <= lon_max) & (lat >= lat_min) & (lat <= lat_max)
    if not inside.any():
        raise ValueError("No valid temperature inside the map area; check --region")
    low, high = np.percentile(values[inside], PERCENTILES)
    return float(low), float(high)


def temperature_levels(
    values: np.ndarray,
    lat: np.ndarray,
    lon: np.ndarray,
    *,
    extent: Sequence[float] | None = None,
    vmin: float | None = None,
    vmax: float | None = None,
) -> np.ndarray:
    """Class boundaries (°C) for one map.

    Missing ends are taken from :func:`data_range` and rounded outwards to a multiple of
    the step; ends given with ``vmin``/``vmax`` are kept exactly as given. The step is the
    smallest of :data:`NICE_STEPS` that gives at most :data:`MAX_CLASSES` classes after
    that rounding.

    >>> temperature_levels(None, None, None, vmin=-3, vmax=15)[[0, 1, -1]].tolist()
    [-3.0, -2.0, 15.0]
    >>> temperature_levels(None, None, None, vmin=0.3, vmax=4.2).tolist()[:3]
    [0.3, 0.5, 1.0]

    Raises:
        ValueError: if the lower end is not below the upper end.
    """
    auto_low, auto_high = vmin is None, vmax is None
    if auto_low or auto_high:
        low, high = data_range(values, lat, lon, extent)
        vmin = low if auto_low else vmin
        vmax = high if auto_high else vmax
    if not vmin < vmax:
        lower = f"automatic lower end {vmin:.1f}" if auto_low else f"--vmin {vmin:g}"
        upper = f"automatic upper end {vmax:.1f}" if auto_high else f"--vmax {vmax:g}"
        raise ValueError(f"The colour scale needs {lower} °C below {upper} °C")
    step = nice_step(vmax - vmin)
    while True:
        start = math.floor(vmin / step) * step if auto_low else vmin
        stop = math.ceil(vmax / step) * step if auto_high else vmax
        inner = np.arange(math.floor(start / step) + 1, math.ceil(stop / step)) * step
        levels = np.unique(np.round(np.concatenate([[start], inner, [stop]]), 6))
        if len(levels) - 1 <= MAX_CLASSES:
            return levels
        step = next((s for s in NICE_STEPS if s > step), step * 2)
