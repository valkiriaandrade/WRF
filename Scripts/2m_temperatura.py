"""Entrada compatível por nome; consulte --help para configurar os arquivos."""

import sys

from wrf_maps.cli import main

if __name__ == "__main__":
    main([] + sys.argv[1:])
