"""``wrf-maps`` command: 2 m temperature map from a WRF GRIB2 file."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence

from .arguments import build_parser, execute
from .colour_scales import CMAP, EXTEND, temperature_levels
from .io import read_grib
from .labels import SOURCE_CREDIT, domain_from_name, format_title, kelvin_to_celsius
from .plotting import mask_to_borders, plot_map
from .regions import ALIASES, REGIONS, domain_label, normalize_region

__all__ = ["build_cli", "kelvin_to_celsius", "main", "run"]

logger = logging.getLogger(__name__)


def run(args: argparse.Namespace) -> None:
    """Read the 2 m temperature, convert it to °C and draw the map."""
    field = read_grib(args.input, "2 metre temperature")
    values, lat, lon = field.values, field.lat, field.lon
    logger.info("Read 2 m temperature valid at %s UTC from %s", field.valid_time, args.input)
    region = REGIONS[args.region]
    if args.region == "domain":
        # The whole grid of the file: name it after the CPTEC cut-out (SU, NE, ...).
        label = domain_label(domain_from_name(args.input))
    else:
        label = region.label
    celsius = kelvin_to_celsius(values)
    states = list(region.states) if region.states else None
    # The automatic colour range uses only what is drawn: with a shapefile, the points
    # inside its polygons (for --region south, inside PR, SC and RS).
    shown = (
        mask_to_borders(celsius, lat, lon, args.shapefile, states) if args.shapefile else celsius
    )
    levels = temperature_levels(
        shown, lat, lon, extent=region.extent, vmin=args.vmin, vmax=args.vmax
    )
    logger.info(
        "Colour scale %g to %g °C every %g °C", levels[0], levels[-1], levels[1] - levels[0]
    )
    title = args.title or format_title(field.valid_time, label, field.run_time)
    plot_map(
        celsius,
        lat,
        lon,
        args.output,
        title=title,
        label="Temperature (°C)",
        levels=levels,
        cmap=CMAP,
        extend=EXTEND,
        extend_colours=True,
        shapefile=args.shapefile,
        states=states,
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
    parser.add_argument(
        "--vmin",
        type=float,
        help="lowest colour-scale value in °C (default: 1st percentile of the map area, "
        "rounded down)",
    )
    parser.add_argument(
        "--vmax",
        type=float,
        help="highest colour-scale value in °C (default: 99th percentile of the map area, "
        "rounded up)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point of the ``wrf-maps`` command."""
    execute(build_cli(), run, argv)
