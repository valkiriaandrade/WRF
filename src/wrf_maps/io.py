"""Leitura com fechamento de arquivos e validação explícita de grades."""

from pathlib import Path

import numpy as np
import xarray as xr


def files_in(directory, suffix):
    files = sorted(Path(directory).glob(f"*{suffix}"))
    if not files:
        raise ValueError(f"Nenhum arquivo {suffix} em {directory}")
    return files


def read_field(path, variable):
    # Objetos de arquivo evitam limitações Unicode do backend netCDF4 no Windows.
    with Path(path).open("rb") as stream:
        signature = stream.read(8)
        stream.seek(0)
        engine = "scipy" if signature.startswith(b"CDF") else "h5netcdf"
        with xr.open_dataset(stream, engine=engine, decode_times=False) as dataset:
            if variable not in dataset:
                raise ValueError(f"Variável {variable!r} ausente em {path}")
            field = dataset[variable].load()
    if not {"lat", "lon"}.issubset(field.dims):
        raise ValueError("A variável deve ter dimensões lat e lon")
    return field


def spatial(field):
    for dim in tuple(field.dims):
        if dim not in ("lat", "lon"):
            if field.sizes[dim] != 1:
                raise ValueError(f"Selecione explicitamente um índice para {dim}")
            field = field.isel({dim: 0}, drop=True)
    return field.transpose("lat", "lon")


def align_exact(*fields):
    if any(f.dims != fields[0].dims for f in fields[1:]):
        raise ValueError("Dimensões incompatíveis")
    return xr.align(*fields, join="exact")


def read_grib(path, name):
    """Leia uma mensagem em grade retangular, liberando cada handle ecCodes."""
    from datetime import datetime

    import eccodes as ec

    selected = None
    with Path(path).open("rb") as stream:
        while (message := ec.codes_grib_new_from_file(stream)) is not None:
            try:
                if ec.codes_get(message, "name") != name:
                    continue
                if name == "2 metre temperature" and ec.codes_get(message, "units") != "K":
                    raise ValueError("Temperatura WRF deve estar em Kelvin")
                if selected is not None:
                    raise ValueError(f"Mais de um campo {name!r}; separe a validade desejada")
                nx, ny = ec.codes_get(message, "Ni"), ec.codes_get(message, "Nj")
                values = ec.codes_get_values(message).astype(float)
                if nx * ny != values.size:
                    raise ValueError("Apenas grades retangulares são suportadas")
                if ec.codes_get(message, "bitmapPresent"):
                    values[ec.codes_get_array(message, "bitmap") == 0] = np.nan
                lat = ec.codes_get_array(message, "latitudes")
                lon = ec.codes_get_array(message, "longitudes")
                # Coordenadas e valores seguem a mesma ordem de varredura.
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
        raise ValueError(f"Campo {name!r} ausente em {path}")
    return selected


def save_netcdf(field, output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    field.to_netcdf(output, engine="h5netcdf")
