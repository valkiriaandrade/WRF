"""NetCDF reading with explicit file closing and strict grid checks."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import xarray as xr


def files_in(directory: str | Path, suffix: str) -> list[Path]:
    """Return the files in ``directory`` ending with ``suffix``, sorted by name.

    Raises:
        ValueError: if no file matches.
    """
    directory = Path(directory)
    if not directory.is_dir():
        raise ValueError(f"Input directory not found: {directory}")
    files = sorted(directory.glob(f"*{suffix}"))
    if not files:
        raise ValueError(f"No {suffix} files found in {directory}; check the --input directory")
    return files


def read_field(path: str | Path, variable: str) -> xr.DataArray:
    """Load ``variable`` from a NetCDF file into memory and close the file.

    Raises:
        ValueError: if the variable is missing or has no ``lat``/``lon`` dimensions.
    """
    # File objects avoid Unicode path limitations of the netCDF4 backend on Windows.
    with Path(path).open("rb") as stream:
        signature = stream.read(8)
        stream.seek(0)
        engine = "scipy" if signature.startswith(b"CDF") else "h5netcdf"
        with xr.open_dataset(stream, engine=engine, decode_times=False) as dataset:
            if variable not in dataset:
                available = ", ".join(map(str, dataset.data_vars)) or "none"
                raise ValueError(
                    f"Variable {variable!r} is missing from {path} (available: {available}); "
                    "check --variable"
                )
            field = dataset[variable].load()
    if not {"lat", "lon"}.issubset(field.dims):
        raise ValueError(f"Variable {variable!r} in {path} must have lat and lon dimensions")
    return field


def spatial(field: xr.DataArray) -> xr.DataArray:
    """Drop singleton non-spatial dimensions and return a ``(lat, lon)`` array.

    Raises:
        ValueError: if a non-spatial dimension has more than one element.
    """
    for dim in tuple(field.dims):
        if dim not in ("lat", "lon"):
            if field.sizes[dim] != 1:
                raise ValueError(
                    f"Dimension {dim!r} has {field.sizes[dim]} elements; "
                    "select a single index explicitly"
                )
            field = field.isel({dim: 0}, drop=True)
    return field.transpose("lat", "lon")


def align_exact(*fields: xr.DataArray) -> tuple[xr.DataArray, ...]:
    """Check that all fields share exactly the same grid.

    Raises:
        ValueError: if dimensions or coordinates differ.
    """
    if any(f.dims != fields[0].dims for f in fields[1:]):
        raise ValueError("Incompatible dimensions between files; grids must match exactly")
    return xr.align(*fields, join="exact")


def read_grib(path: str | Path, name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, str]:
    """Read one field on a rectangular grid from a GRIB2 file with ecCodes.

    Every ecCodes handle is released. ``"2 metre temperature"`` must be in kelvin.

    Returns:
        ``(values, lat, lon, valid_time)`` with 2D arrays and longitudes in −180–180.

    Raises:
        ImportError: if ecCodes is not installed.
        ValueError: if the field is missing, repeated, in the wrong units, or not on a regular grid.
    """
    try:
        import eccodes as ec
    except ImportError as error:  # pragma: no cover - depends on the environment
        raise ImportError(
            "Reading GRIB2 needs ecCodes; install it with: python -m pip install eccodes"
        ) from error

    selected = None
    with Path(path).open("rb") as stream:
        while (message := ec.codes_grib_new_from_file(stream)) is not None:
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
                valid_date = ec.codes_get(message, "validityDate")
                valid_time = ec.codes_get(message, "validityTime")
                stamp = datetime.strptime(f"{valid_date}{valid_time:04d}", "%Y%m%d%H%M")
                selected = (
                    values.reshape(shape),
                    lat.reshape(shape),
                    ((lon + 180) % 360 - 180).reshape(shape),
                    str(stamp),
                )
            finally:
                ec.codes_release(message)
    if selected is None:
        raise ValueError(f"Field {name!r} not found in {path}")
    return selected


def save_netcdf(field: xr.DataArray, output: str | Path) -> None:
    """Write ``field`` to ``output``, creating parent folders as needed."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    field.to_netcdf(output, engine="h5netcdf")
