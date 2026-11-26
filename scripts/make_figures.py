"""Regenerate every figure in ``figures/`` from the data in ``data/``.

Usage::

    python scripts/make_figures.py [--data-dir data] [--figures-dir figures] [--dpi 200]

Figures whose source data is not in the repository are skipped with a warning and
the existing image is kept. A figure that fails does not stop the others. The exit
status is 1 if any figure was skipped or failed.
"""

from __future__ import annotations

import argparse
import logging
import sys
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


def build(data_dir: Path, figures_dir: Path, dpi: int) -> tuple[list[str], list[str]]:
    """Rebuild all figures with available data; return the names skipped and failed."""
    skipped, failed = [], []
    for output, source in FIGURES:
        path = data_dir / source
        if not path.exists():
            logger.warning("Skipping %s (kept existing image): missing %s", output, path)
            skipped.append(output)
            continue
        logger.info("Building %s", output)
        argv = ["--input", str(path), "--dpi", str(dpi), "--output", str(figures_dir / output)]
        try:
            wrf_maps(argv)
        except SystemExit as error:  # the CLI reports expected errors with exit status 2
            if error.code:
                logger.error("Failed: %s", output)
                failed.append(output)
        except Exception:
            logger.exception("Failed: %s", output)
            failed.append(output)
    return skipped, failed


def main() -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--figures-dir", type=Path, default=ROOT / "figures")
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    skipped, failed = build(args.data_dir, args.figures_dir, args.dpi)
    built = len(FIGURES) - len(skipped) - len(failed)
    logger.info(
        "Done: %d figure(s) regenerated, %d skipped, %d failed", built, len(skipped), len(failed)
    )
    return 1 if skipped or failed else 0


if __name__ == "__main__":
    sys.exit(main())
