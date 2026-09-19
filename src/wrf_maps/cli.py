import numpy as np

from .arguments import execute, parser
from .io import read_grib
from .plotting import plot_map


def kelvin_to_celsius(values):
    return np.asanyarray(values, dtype=float) - 273.15


def run(args):
    values, lat, lon, valid_time = read_grib(args.input, "2 metre temperature")
    plot_map(
        kelvin_to_celsius(values),
        lat,
        lon,
        args.output,
        title=args.title or f"Temperatura a 2 m — {valid_time} UTC",
        label="Temperatura (°C)",
        levels=np.arange(-10, 46, 2),
        cmap="coolwarm",
        shapefile=args.shapefile,
    )


def main(argv=None):
    p = parser("Temperatura WRF a 2 metros")
    p.add_argument("--input", required=True, help="GRIB2 com um campo de temperatura a 2 m")
    execute(p, run, argv)
