"""Regenerate every figure in ``figures/`` from the data in ``data/``.

Usage::

    python scripts/make_figures.py [--data-dir data] [--figures-dir figures] [--dpi 200]

Figures whose source data is not in the repository are skipped with a warning and
the existing image is kept.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from wrf_maps.cli import main as wrf_maps

ROOT = Path(__file__).resolve().parents[1]
logger = logging.getLogger("make_figures")

#: (output figure, input GRIB2 file)
FIGURES = [
    (
        "wrf_2m_temperature_2024-08-26_09utc.png",
        "WRF_cpt_07KM_SU_2024082112_2024082609.grib2",
    ),
]


def build(data_dir: Path, figures_dir: Path, dpi: int) -> list[str]:
    """Rebuild all figures with available data; return the names that were skipped."""
    skipped = []
    for output, source in FIGURES:
        path = data_dir / source
        if not path.exists():
            logger.warning("Skipping %s (kept existing image): missing %s", output, path)
            skipped.append(output)
            continue
        logger.info("Building %s", output)
        wrf_maps(["--input", str(path), "--dpi", str(dpi), "--output", str(figures_dir / output)])
    return skipped


def main() -> None:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--figures-dir", type=Path, default=ROOT / "figures")
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    skipped = build(args.data_dir, args.figures_dir, args.dpi)
    built = len(FIGURES) - len(skipped)
    logger.info("Done: %d figure(s) regenerated, %d kept as-is", built, len(skipped))


if __name__ == "__main__":
    main()
