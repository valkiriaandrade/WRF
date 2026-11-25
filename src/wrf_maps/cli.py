"""``wrf-maps`` command: 2 m temperature map from a WRF GRIB2 file."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from datetime import datetime

import numpy as np

from .arguments import build_parser, execute
from .io import read_grib
from .labels import SOURCE_CREDIT, format_title, kelvin_to_celsius, run_time_from_name
from .plotting import plot_map
from .regions import ALIASES, REGIONS, normalize_region

__all__ = ["build_cli", "kelvin_to_celsius", "main", "run"]

logger = logging.getLogger(__name__)

LEVELS = np.arange(-10, 46, 2)
CMAP = "coolwarm"


def run(args: argparse.Namespace) -> None:
    """Read the 2 m temperature, convert it to °C and draw the map."""
    values, lat, lon, valid_time = read_grib(args.input, "2 metre temperature")
    logger.info("Read 2 m temperature valid at %s UTC from %s", valid_time, args.input)
    region = REGIONS[args.region]
    title = args.title or format_title(
        datetime.fromisoformat(valid_time), region.label, run_time_from_name(args.input)
    )
    plot_map(
        kelvin_to_celsius(values),
        lat,
        lon,
        args.output,
        title=title,
        label="Temperature (°C)",
        levels=LEVELS,
        cmap=CMAP,
        shapefile=args.shapefile,
        states=list(region.states) if region.states else None,
        extent=list(region.extent) if region.extent else None,
        credit=SOURCE_CREDIT,
        dpi=args.dpi,
    )


def build_cli() -> argparse.ArgumentParser:
    """Return the parser for the ``wrf-maps`` command."""
    parser = build_parser("WRF 2 m temperature map (kelvin in the file, °C on the map)")
    parser.add_argument(
        "--input", required=True, help="GRIB2 file with exactly one 2 m temperature field"
    )
    parser.add_argument(
        "--region",
        type=normalize_region,
        choices=list(REGIONS),
        default="domain",
        help=f"map domain (Portuguese aliases accepted: {', '.join(ALIASES)})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point of the ``wrf-maps`` command."""
    execute(build_cli(), run, argv)
