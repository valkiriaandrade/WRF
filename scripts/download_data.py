"""Download WRF 7 km GRIB2 output from the public CPTEC/INPE server into ``data/``.

Source: https://ftp.cptec.inpe.br/modelos/tempo/WRF/ams_07km/recortes/regioes/ (CPTEC/INPE),
organised as ``<YYYY>/<MM>/<DD>/<HH>/WRF_cpt_07KM_<DOMAIN>_<run>_<valid>.grib2``.

The server keeps only recent runs (the archive starts in 2025), so the 2024 sample used by the
README and ``make figures`` is committed in ``data/`` and is not downloaded.

Usage::

    python scripts/download_data.py                        # latest run, +24 h, domain SU
    python scripts/download_data.py --run 2026112500 --leads 0 24 48
    python scripts/download_data.py --dry-run              # only list the URLs

Files that already exist are skipped (use ``--overwrite`` to fetch them again).
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

BASE_URL = "https://ftp.cptec.inpe.br/modelos/tempo/WRF/ams_07km/recortes/regioes"
ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "wrf-maps-data-download"
DEFAULT_DOMAIN = "SU"
DEFAULT_LEADS = [24]
#: The committed sample used by the README and `make figures` (no longer on the server).
SAMPLE = "WRF_cpt_07KM_SU_2024082112_2024082609.grib2"

logger = logging.getLogger("download_data")
_LINK = re.compile(r'href="([^"?/][^"]*)"')


class DownloadError(RuntimeError):
    """A file could not be downloaded."""


@dataclass(frozen=True)
class Item:
    """One file to download: source URL and destination relative to the data folder."""

    url: str
    path: Path


def parse_run(value: str) -> datetime:
    """Parse a run time ``YYYYMMDDHH`` (argparse type)."""
    try:
        return datetime.strptime(value, "%Y%m%d%H")
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"invalid run {value!r}; use YYYYMMDDHH") from error


def file_name(domain: str, run: datetime, lead: int) -> str:
    """CPTEC file name for one forecast step."""
    valid = run + timedelta(hours=lead)
    return f"WRF_cpt_07KM_{domain}_{run:%Y%m%d%H}_{valid:%Y%m%d%H}.grib2"


def run_url(run: datetime) -> str:
    """Folder of one model run on the server."""
    return f"{BASE_URL}/{run:%Y/%m/%d/%H}/"


def plan(run: datetime, leads: Iterable[int], domain: str = DEFAULT_DOMAIN) -> list[Item]:
    """GRIB2 files of ``run`` for each forecast hour in ``leads``."""
    return [
        Item(run_url(run) + file_name(domain, run, lead), Path(file_name(domain, run, lead)))
        for lead in leads
    ]


def read_text(url: str, opener: Callable = urllib.request.urlopen, timeout: float = 60) -> str:
    """Fetch a directory listing as text."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with opener(request, timeout=timeout) as response:
        return response.read().decode("utf-8", "replace")


def list_entries(url: str, read: Callable[[str], str] = read_text) -> list[str]:
    """Names linked from a server directory listing (folders keep their trailing slash)."""
    return sorted(set(_LINK.findall(read(url))))


def available_runs(
    domain: str = DEFAULT_DOMAIN, read: Callable[[str], str] = read_text, newest_only=False
) -> list[datetime]:
    """Runs on the server that contain files for ``domain``, oldest first.

    With ``newest_only`` the search stops at the most recent run, which needs only a
    handful of listing requests.
    """

    def folders(url: str) -> list[str]:
        return [name for name in list_entries(url, read) if re.fullmatch(r"\d+/", name)]

    runs: list[datetime] = []
    years = folders(f"{BASE_URL}/")
    for year in reversed(years) if newest_only else years:
        months = folders(f"{BASE_URL}/{year}")
        for month in reversed(months) if newest_only else months:
            days = folders(f"{BASE_URL}/{year}{month}")
            for day in reversed(days) if newest_only else days:
                hours = folders(f"{BASE_URL}/{year}{month}{day}")
                for hour in reversed(hours) if newest_only else hours:
                    url = f"{BASE_URL}/{year}{month}{day}{hour}"
                    if any(f"_{domain}_" in n for n in list_entries(url, read)):
                        run = datetime.strptime(f"{year}{month}{day}{hour}", "%Y/%m/%d/%H/")
                        if newest_only:
                            return [run]
                        runs.append(run)
    return runs


def latest_run(domain: str = DEFAULT_DOMAIN, read: Callable[[str], str] = read_text) -> datetime:
    """Most recent run on the server with files for ``domain``.

    Raises:
        DownloadError: if the server lists no run for the domain.
    """
    runs = available_runs(domain, read, newest_only=True)
    if not runs:
        raise DownloadError(f"No WRF run with domain {domain!r} found under {BASE_URL}/")
    return runs[0]


def fetch(
    url: str,
    dest: Path,
    *,
    overwrite: bool = False,
    retries: int = 3,
    timeout: float = 300,
    opener: Callable = urllib.request.urlopen,
) -> bool:
    """Download ``url`` to ``dest``; return False if it was skipped because it exists.

    The file is written to ``<dest>.part`` first and renamed when complete.

    Raises:
        DownloadError: if the file does not exist on the server or every attempt fails.
    """
    if dest.exists() and dest.stat().st_size > 0 and not overwrite:
        logger.debug("Already present: %s", dest)
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_name(dest.name + ".part")
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with opener(request, timeout=timeout) as response, partial.open("wb") as out:
                shutil.copyfileobj(response, out)
            partial.replace(dest)
            return True
        except urllib.error.HTTPError as error:
            partial.unlink(missing_ok=True)
            if error.code == 404:
                raise DownloadError(
                    f"Not found on the server: {url} (the server keeps only recent runs; "
                    "list them with --list-runs)"
                ) from error
            last_error = error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            partial.unlink(missing_ok=True)
            last_error = error
        if attempt < retries:
            time.sleep(2 * attempt)
    raise DownloadError(f"Could not download {url} after {retries} attempts: {last_error}")


def download(items: Iterable[Item], data_dir: Path, *, overwrite: bool = False) -> list[str]:
    """Download every item; return the error messages of the ones that failed."""
    errors, fetched, skipped = [], 0, 0
    for item in items:
        try:
            if fetch(item.url, data_dir / item.path, overwrite=overwrite):
                fetched += 1
                logger.info("Downloaded %s", item.path)
            else:
                skipped += 1
        except DownloadError as error:
            errors.append(str(error))
            logger.error("%s", error)
    logger.info("%d downloaded, %d already present, %d failed", fetched, skipped, len(errors))
    return errors


def build_parser() -> argparse.ArgumentParser:
    """Command-line options."""
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--run", default="latest", help="model run YYYYMMDDHH, or 'latest' available on the server"
    )
    parser.add_argument(
        "--leads", nargs="+", type=int, default=DEFAULT_LEADS, help="forecast hours to download"
    )
    parser.add_argument("--domain", default=DEFAULT_DOMAIN, help="regional cut-out, e.g. SU")
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--overwrite", action="store_true", help="download existing files again")
    parser.add_argument("--dry-run", action="store_true", help="only list the URLs")
    parser.add_argument(
        "--list-runs", action="store_true", help="print the runs kept on the server and exit"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point; returns the process exit status."""
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    if (args.data_dir / SAMPLE).exists():
        logger.info("Sample used by the README and make figures is present: %s", SAMPLE)
    else:
        logger.warning(
            "Committed sample %s is missing and is no longer on the server; restore it "
            "with `git checkout -- data/%s`",
            SAMPLE,
            SAMPLE,
        )
    try:
        if args.list_runs:
            runs = available_runs(args.domain)
            print("\n".join(f"{r:%Y%m%d%H}" for r in runs) or "no runs found")
            return 0
        run = latest_run(args.domain) if args.run == "latest" else parse_run(args.run)
    except (DownloadError, argparse.ArgumentTypeError, urllib.error.URLError) as error:
        logger.error("%s", error)
        return 1
    logger.info("Run %s, domain %s, forecast hours %s", f"{run:%Y%m%d%H}", args.domain, args.leads)
    items = plan(run, args.leads, args.domain)
    if args.dry_run:
        for item in items:
            print(f"{item.url} -> {args.data_dir / item.path}")
        return 0
    errors = download(items, args.data_dir, overwrite=args.overwrite)
    if errors:
        logger.error("%d file(s) could not be downloaded:\n  %s", len(errors), "\n  ".join(errors))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
