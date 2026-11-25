"""WRF 2 m temperature map.

Shortcut for ``wrf-maps``; run with ``--help`` for all options.
"""

import sys

from wrf_maps.cli import main

if __name__ == "__main__":
    main(sys.argv[1:])
