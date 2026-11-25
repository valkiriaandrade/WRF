"""Map regions accepted by the command line, with Portuguese aliases."""

from __future__ import annotations

import argparse
from dataclasses import dataclass


@dataclass(frozen=True)
class Region:
    """A map domain: display name, extent (``None`` = whole model grid) and states."""

    name: str
    label: str
    extent: tuple[float, float, float, float] | None = None
    states: tuple[str, ...] | None = None


REGIONS: dict[str, Region] = {
    "domain": Region("domain", "Southern Brazil"),
    "south": Region("south", "PR, SC and RS", (-57.6, -48.0, -33.75, -22.5), ("PR", "SC", "RS")),
}

#: Portuguese names kept for consistency with the other projects of this portfolio.
ALIASES: dict[str, str] = {"sul": "south"}


def normalize_region(value: str) -> str:
    """Return the canonical region name for ``value``.

    Accepts ``domain`` (the whole WRF grid) and ``south`` (PR, SC, RS), plus the
    Portuguese alias ``sul``, case-insensitively.

    Raises:
        argparse.ArgumentTypeError: if the name is not a known region or alias.
    """
    key = value.strip().lower()
    key = ALIASES.get(key, key)
    if key not in REGIONS:
        accepted = ", ".join([*REGIONS, *ALIASES])
        raise argparse.ArgumentTypeError(f"unknown region {value!r}; choose one of: {accepted}")
    return key
