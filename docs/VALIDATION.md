# Refactoring validation

- Python 3.11 on Windows: tests for unit conversion, reading, selection errors and
  offline map rendering.
- Original GRIB file read with ecCodes: 243 × 214 grid, valid 26/08/2024 09:00 UTC.
- Map produced in `output/temperature.png` from the real data with local state boundaries.
- Editable install of the package and Ruff checks executed.

The API requires exactly one 2 m temperature field per file. Reduced grids are not
supported. The shapefile mask is optional; by default the map keeps the GRIB area.
Rendering was standardised and does not reproduce the historical palette pixel by pixel.

## English translation and figure regeneration (v0.2.0)

- Folders and files renamed to English; code, CLI help, messages, titles and labels
  translated. The kelvin → °C conversion, palette (`coolwarm`) and class levels
  (−10 to 44 °C every 2 °C) are unchanged.
- `figures/wrf_2m_temperature_2024-08-26_09utc.png` regenerated with `make figures`.
- The original figure was titled "6h" (local time, UTC−3); the regenerated title uses
  the GRIB valid time in UTC (09 UTC), plus the model run time taken from the file name.

## Data download and smooth contours (v0.3.0)

- `scripts/download_data.py` (`make data`) downloads WRF 7 km GRIB2 files from the public
  CPTEC/INPE server (https://ftp.cptec.inpe.br/modelos/tempo/WRF/ams_07km/recortes/regioes/).
  Default: latest run with the SU domain, +24 h; `--run`, `--leads`, `--domain` and
  `--list-runs` select others. Downloaded files are git-ignored.
- The server archive starts in 2025, so the 2024 sample cannot be downloaded any more; it
  stays committed and is what the README examples, `make figures` and the tests use.
- Checked end to end on 2026-11-25: latest run 2026112500, file
  `WRF_cpt_07KM_SU_2026112500_2026112600.grib2` downloaded and mapped with the CLI
  (automatic scale 14–28 °C).
- Maps are drawn with filled contours (`contourf`) as in the original script.
