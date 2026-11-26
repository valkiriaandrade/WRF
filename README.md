# WRF Weather Model Maps

**Turn CPTEC/INPE WRF regional model GRIB2 output into clean 2 m temperature maps of southern Brazil, with one Python command.**

[![CI](https://github.com/valkiriaandrade/wrf-weather-model-maps/actions/workflows/tests.yml/badge.svg)](https://github.com/valkiriaandrade/wrf-weather-model-maps/actions/workflows/tests.yml)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.12-blue)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## Gallery

<img src="figures/wrf_2m_temperature_2024-08-26_09utc.png" alt="WRF 2 m temperature over southern Brazil, 26 August 2024 09 UTC" width="560"/>

*WRF 7 km 2 m temperature over southern Brazil, valid 26 Aug 2024 09 UTC (06h local time),
from the 21 Aug 2024 12 UTC run: a cold early morning, with temperatures near or below
0 °C on the Santa Catarina highlands.*

## What it does

- Reads the **2 m temperature** field from a WRF GRIB2 file with ecCodes. A CPTEC file holds
  hundreds of fields (the sample has 305 GRIB messages); exactly one of them must be the 2 m
  temperature, in kelvin, otherwise the file is rejected.
- Converts kelvin to °C and draws a map (original `jet` palette, colour scale fitted to each map's data range) of the model domain or of the southern states
  (PR, SC, RS), with coastline, country and state borders, lat/lon labels, units and a
  source credit.
- Builds the title from the data: valid time (UTC) and, for CPTEC file names, the model run.

## Data source

[**WRF**](https://www.mmm.ucar.edu/models/wrf) (Weather Research and Forecasting model) is a
limited-area numerical weather prediction model. [CPTEC/INPE](https://www.cptec.inpe.br/) runs
it operationally over South America and distributes GRIB2 output; the sample file is the
**7 km southern Brazil (SU) domain**:

| File | Content |
|---|---|
| `data/WRF_cpt_07KM_SU_2024082112_2024082609.grib2` | Run 21 Aug 2024 12 UTC, valid 26 Aug 2024 09 UTC (243 × 214 grid, 305 fields) |

The provider name encodes `WRF_cpt_<resolution>_<domain>_<run YYYYMMDDHH>_<valid YYYYMMDDHH>`.

*Data: CPTEC/INPE – WRF 7 km, https://ftp.cptec.inpe.br/modelos/tempo/WRF/.*

## Get the data

The 2024 sample above is **committed**: CPTEC keeps only recent runs on its server (the archive
currently starts in 2025), so it can no longer be downloaded. The README examples and
`make figures` use it, so they work right after cloning.

To map a current forecast, download a run from the public CPTEC/INPE server
(`WRF/ams_07km/recortes/regioes/<YYYY>/<MM>/<DD>/<HH>/`):

```bash
make data                          # latest run, +24 h, southern Brazil (SU) domain
python scripts/download_data.py --run 2026112500 --leads 0 24 48   # a given run and lead times
python scripts/download_data.py --domain NE                         # another regional cut-out
python scripts/download_data.py --dry-run                           # only list the URLs
python scripts/download_data.py --list-runs                         # every run kept on the server
```

`--domain` selects the regional cut-out: `SU` (south, default), `SE`, `CO`, `NE` or `NT`.
`--list-runs` walks the whole server archive, one listing per run folder, so it takes a few
minutes; `make data` only looks for the newest run. Downloaded files are git-ignored, and existing
files are skipped (`--overwrite` fetches them again, `--data-dir` changes the folder). A run or
lead time that isn't on the server is reported by name.

## Install

Python 3.10 or later. GRIB2 is read with [ecCodes](https://github.com/ecmwf/eccodes-python),
which installs from pip with its binaries on Windows, Linux and macOS.

```bash
git clone https://github.com/valkiriaandrade/wrf-weather-model-maps.git
cd wrf-weather-model-maps
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"  # or: make install
```

## Quick start

```bash
# Whole model domain
wrf-maps --input data/WRF_cpt_07KM_SU_2024082112_2024082609.grib2 --output output/t2m.png

# Zoom on PR, SC and RS, at 300 dpi
wrf-maps --input data/WRF_cpt_07KM_SU_2024082112_2024082609.grib2 \
         --region south --dpi 300 --output output/t2m_south.png

# Latest forecast: download it, then map it (the colour scale adapts to the data)
make data
wrf-maps --input data/WRF_cpt_07KM_SU_<run>_<valid>.grib2 --output output/t2m_latest.png

# Rebuild every figure in figures/
make figures                       # or: python scripts/make_figures.py
```

## CLI options

`wrf-maps --help` prints the full list.

| Option | Default | Description |
|---|---|---|
| `--input FILE` | *required* | WRF GRIB2 file; exactly one of its fields must be the 2 m temperature |
| `--output FILE` | *required* | Output PNG (folders are created) |
| `--region {domain,south}` | `domain` | Whole model grid, or PR/SC/RS; the Portuguese alias `sul` is also accepted |
| `--shapefile FILE` | – | State boundaries with a CRS (`.shp` or zipped) to mask the field; `--region south` needs a `SIGLA_UF` column to select PR, SC and RS. By default Natural Earth borders are drawn |
| `--vmin`, `--vmax` | automatic | Colour-scale limits in °C. By default each map uses the 1st–99th percentile of its own area, rounded to a tidy step (0.5/1/2/5 °C), so winter and summer maps both keep their contrast |
| `--title TEXT` | built from the data | Custom map title |
| `--dpi N` | `200` | PNG resolution |
| `--verbose` | off | Debug logging and full tracebacks |

`scripts/wrf_2m_temperature.py` is a shortcut for the same command.

## Project structure

```
wrf-weather-model-maps/
├── data/                  # committed 2024 sample; `make data` adds recent runs
├── figures/               # published maps (rebuilt with `make figures`)
├── scripts/
│   ├── download_data.py   # downloads WRF runs from CPTEC/INPE (`make data`)
│   ├── make_figures.py    # regenerates every figure in figures/
│   └── wrf_2m_temperature.py
├── src/wrf_maps/
│   ├── cli.py             # command-line interface
│   ├── io.py              # GRIB2 reading with ecCodes
│   ├── plotting.py        # shared map style and rendering
│   ├── colour_scales.py   # palette and data-fitted class levels
│   ├── labels.py          # K → °C, titles and run metadata
│   └── regions.py         # map domains and region aliases
├── tests/                 # pytest suite (synthetic data + the real GRIB2 file)
├── docs/                  # validation notes and project history
├── Makefile
└── pyproject.toml
```

## Development

```bash
make install   # editable install with dev tools + pre-commit hooks (ruff)
make test      # pytest with coverage report
make lint      # ruff check + ruff format --check
make data      # download the latest WRF run (manual step, never run in CI)
make figures   # regenerate every figure in figures/ from data/
```

On Windows without `make`, run the commands from the [Makefile](Makefile) directly, e.g.
`python -m pytest -q --cov` or `python scripts/make_figures.py`. The first map run without a
shapefile downloads Natural Earth borders (cached afterwards).

Tests and CI never download anything: they use the committed sample, and a test fixture blocks
network access.

## License

Code: [MIT](LICENSE) © Valkiria Andrade.

The WRF sample in `data/` and any downloaded run are CPTEC/INPE model output; they are not
covered by the MIT licence. Cite CPTEC/INPE when you publish maps made from them, and ask
CPTEC/INPE (atende.cptec@inpe.br) about any other use. Without `--shapefile`, coastlines and
borders come from [Natural Earth](https://www.naturalearthdata.com/) (public domain).

---

Project history: [original README](docs/README-original.md).
