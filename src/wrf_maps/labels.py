"""Human-readable labels, unit conversion and run metadata for WRF maps."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import numpy as np

SOURCE_CREDIT = "Data: CPTEC/INPE WRF 7 km"
ABSOLUTE_ZERO_CELSIUS = 273.15

#: CPTEC WRF file names: ``WRF_cpt_07KM_SU_<run YYYYMMDDHH>_<valid YYYYMMDDHH>.grib2``.
_PROVIDER_NAME = re.compile(r"WRF_cpt_(\d+)KM_([A-Z]+)_(\d{10})_(\d{10})")


def kelvin_to_celsius(values):
    """Convert temperatures from kelvin to degrees Celsius (NaN preserved).

    >>> float(kelvin_to_celsius(273.15))
    0.0
    """
    return np.asanyarray(values, dtype=float) - ABSOLUTE_ZERO_CELSIUS


def run_time_from_name(path: str | Path) -> datetime | None:
    """Model initialisation time from a CPTEC WRF file name, if it follows the pattern."""
    match = _PROVIDER_NAME.search(Path(path).name)
    if not match:
        return None
    return datetime.strptime(match.group(3), "%Y%m%d%H")


def format_time(stamp: datetime) -> str:
    """``2024-08-26 09:00`` -> ``"26 Aug 2024 09 UTC"``."""
    return f"{stamp:%d %b %Y %H} UTC"


def format_title(
    valid: datetime, region: str | None = None, run: datetime | None = None, units: str = "°C"
) -> str:
    """Build a two-line map title: product, units and region, then valid time and model run.

    >>> print(format_title(datetime(2024, 8, 26, 9), "Southern Brazil", datetime(2024, 8, 21, 12)))
    WRF 2 m temperature (°C) – Southern Brazil
    Valid 26 Aug 2024 09 UTC · run 21 Aug 2024 12 UTC
    """
    title = "WRF 2 m temperature"
    if units:
        title += f" ({units})"
    if region:
        title += f" – {region}"
    when = f"Valid {format_time(valid)}"
    if run:
        when += f" · run {format_time(run)}"
    return f"{title}\n{when}"
