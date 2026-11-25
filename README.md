# WRF

Weather data processing and visualisation project by Valkiria Andrade.
The code is organised as a Python package with a command-line interface,
regression tests and automated checks on GitHub Actions.

<img src="Figuras/2m_temperatura.png" alt="WRF 2 m temperature map for southern Brazil" width="480"/>

## Installation

Python 3.10 or later. From this repository's folder:

```bash
python -m venv .venv
# Windows PowerShell: .venv/Scripts/Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

WRF and MERGE also need ecCodes: `python -m pip install -e ".[grib]"`.
The ecCodes package ships binaries for Windows, Linux and macOS. NetCDF, calculations and
maps do not depend on this extra. GRIB files are read directly with ecCodes, replacing pygrib.

## Usage

Example (check your files' names and metadata):

```bash
wrf-maps --input Dados/WRF_cpt_07KM_SU_2024082112_2024082609.grib2 --output output/temperature.png
wrf-maps --help
```

The GRIB file must contain exactly one 2 m temperature message. Ambiguous fields are rejected. The title uses the data's UTC valid time. The Kelvin → Celsius conversion is applied to the WRF field.

`--shapefile path/BR_UF_2022.shp` applies a mask and local boundaries; the file
must come with its auxiliary files and CRS. ZIP files must be extracted first.
Without a shapefile, Cartopy may download Natural Earth cartography on first use.
`--title` sets the title and `--verbose` shows error details.
Maps are saved without opening windows. The output folder is created automatically.

## Architecture and maintenance

- `src/wrf_maps/io.py`: reading, resource cleanup and grid validation.
- `src/wrf_maps/cli.py`: arguments and processing coordination.
- `src/wrf_maps/plotting.py`: rendering and geographic masking.
- `Scripts/`: entry points with the historical names, using the installed package.
- `tests/`: synthetic data and regression tests independent of external services.
- `Dados/` and `Figuras/`: original data and figures, preserved.

The historical entry points now require the same arguments as the CLI. Paths,
dates and files that used to be hard-coded must be passed explicitly.
Palettes and resolution were standardised; figures are not pixel-perfect copies
of the old versions. Missing values are not converted to zero.

```bash
pytest -q
ruff check src Scripts tests
```

CI runs the tests on Python 3.10 and 3.12. Tests use small synthetic data
and local cartography; scientific interpretation and period coverage should be
checked against operational data.

History, scientific background and images: [original README](docs/README-original.md).
