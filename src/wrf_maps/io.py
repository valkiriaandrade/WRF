"""GRIB2 reading with ecCodes, with every handle released and strict field checks."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import NamedTuple

import numpy as np


class GribField(NamedTuple):
    """One field on a regular grid, with the model run and validity time from the GRIB."""

    values: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    valid_time: datetime
    run_time: datetime


def _stamp(date: int, time: int) -> datetime:
    return datetime.strptime(f"{date}{time:04d}", "%Y%m%d%H%M")


def read_grib(path: str | Path, name: str) -> GribField:
    """Read one field on a rectangular grid from a GRIB2 file with ecCodes.

    Every ecCodes handle is released. ``"2 metre temperature"`` must be in kelvin.

    Returns:
        :class:`GribField` with 2D arrays, longitudes in −180–180, and the validity and
        model run (``dataDate``/``dataTime``) times stored in the GRIB message.

    Raises:
        ImportError: if ecCodes is not installed.
        ValueError: if the file is not valid GRIB, or the field is missing, repeated, in the
            wrong units, or not on a regular grid.
    """
    try:
        import eccodes as ec
    except ImportError as error:  # pragma: no cover - depends on the environment
        raise ImportError(
            "Reading GRIB2 needs ecCodes; install it with: python -m pip install eccodes"
        ) from error

    selected = None
    with Path(path).open("rb") as stream:
        while True:
            try:
                message = ec.codes_grib_new_from_file(stream)
            except ec.GribInternalError as error:
                raise ValueError(f"{path} is not a readable GRIB file ({error})") from error
            if message is None:
                break
            try:
                if ec.codes_get(message, "name") != name:
                    continue
                if name == "2 metre temperature" and ec.codes_get(message, "units") != "K":
                    raise ValueError(f"WRF 2 m temperature in {path} must be in kelvin (K)")
                if selected is not None:
                    raise ValueError(
                        f"More than one {name!r} field in {path}; keep one validity time per file"
                    )
                nx, ny = ec.codes_get(message, "Ni"), ec.codes_get(message, "Nj")
                values = ec.codes_get_values(message).astype(float)
                if nx * ny != values.size:
                    raise ValueError(f"{path}: only regular rectangular grids are supported")
                if ec.codes_get(message, "bitmapPresent"):
                    values[ec.codes_get_array(message, "bitmap") == 0] = np.nan
                lat = ec.codes_get_array(message, "latitudes")
                lon = ec.codes_get_array(message, "longitudes")
                # Coordinates and values follow the same scanning order.
                shape = (nx, ny) if ec.codes_get(message, "jPointsAreConsecutive") else (ny, nx)
                selected = GribField(
                    values.reshape(shape),
                    lat.reshape(shape),
                    ((lon + 180) % 360 - 180).reshape(shape),
                    _stamp(
                        ec.codes_get(message, "validityDate"), ec.codes_get(message, "validityTime")
                    ),
                    _stamp(ec.codes_get(message, "dataDate"), ec.codes_get(message, "dataTime")),
                )
            except ec.GribInternalError as error:
                raise ValueError(f"{path}: damaged GRIB message ({error})") from error
            finally:
                ec.codes_release(message)
    if selected is None:
        raise ValueError(f"Field {name!r} not found in {path}")
    return selected
