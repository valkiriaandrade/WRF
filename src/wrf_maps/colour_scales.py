"""Colour scale of the 2 m temperature map.

The palette (``jet``, both ends extended) is the one of the original
``Scripts/2m_temperatura.py``. Instead of the original fixed −3…15 °C, the class
boundaries follow the data range of each map, so both winter and summer maps keep
their contrast; ``--vmin``/``--vmax`` fix either end explicitly.
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

    Missing ends are taken from :func:`data_range`; both ends are then rounded outwards
    to a multiple of :func:`nice_step`.

    Raises:
        ValueError: if ``vmin`` is not below ``vmax``.
    """
    if vmin is None or vmax is None:
        low, high = data_range(values, lat, lon, extent)
        vmin = low if vmin is None else vmin
        vmax = high if vmax is None else vmax
    if not vmin < vmax:
        raise ValueError(f"--vmin ({vmin}) must be lower than --vmax ({vmax})")
    step = nice_step(vmax - vmin)
    start = math.floor(vmin / step) * step
    stop = math.ceil(vmax / step) * step
    return np.round(np.arange(start, stop + step / 2, step), 6)
