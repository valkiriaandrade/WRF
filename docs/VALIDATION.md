# Refactoring validation

- Python 3.11 on Windows: tests for unit conversion, reading, selection errors and
  offline map rendering.
- Original GRIB file read with ecCodes: 243 × 214 grid, valid 26/08/2024 09:00 UTC.
- Map produced in `output/temperature.png` from the real data with local state boundaries.
- Editable install of the package and Ruff checks executed.

Exactly one of the GRIB messages in a file must be the 2 m temperature (the sample holds 305). Reduced grids are not
supported. The shapefile mask is optional; by default the map keeps the GRIB area.
Rendering was standardised and does not reproduce the historical palette pixel by pixel.

## English translation and figure regeneration (v0.2.0)

- Folders and files renamed to English; code, CLI help, messages, titles and labels
  translated. The kelvin → °C conversion is unchanged.
- Colour scale: the original `jet` palette, both ends extended, as in
  `Scripts/2m_temperatura.py`. The original fixed −3 to 15 °C range was replaced by levels
  fitted to each map: the 1st–99th percentile of the map area, rounded outward to a tidy step
  (0.5, 1, 2, 5 or 10 °C, at most 24 classes). `--vmin`/`--vmax` fix either end. The sample map
  uses −1 to 17 °C every 1 °C. The first English version used `coolwarm` with fixed −10 to 44 °C
  levels; commit 95868ab ("Restore the jet palette with data-fitted levels") replaced it, because
  the winter sample used only a few of those colours.
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

## Code review fixes (v0.3.0, 2026-11-26)

- Titles name the CPTEC cut-out of the file (SU Southern Brazil, SE, CO, NE, NT) instead of
  "Southern Brazil" for every file; the model run time now comes from the GRIB (`dataDate`,
  `dataTime`) like the valid time. Checked on a downloaded NE file (run 2026112600, +24 h):
  "WRF 2 m temperature (°C) – Northeast Brazil".
- Colour range: `--vmin`/`--vmax` are used exactly as given (before, they were rounded outward
  to the step), and the step is chosen after rounding, so a map never has more than 24 classes
  (a −0.9…23.1 °C range used to give 25). With `--shapefile`, the automatic range comes from
  the points inside the polygons only (for `--region south`, PR/SC/RS instead of the whole
  box). The published figure does not use either option and is byte-identical.
- Unused NetCDF helpers removed, with their dependencies (xarray, h5netcdf, h5py, scipy).
- A damaged GRIB file gives a one-line error instead of a traceback.
- New tests run the published map command offline on the sample (title, levels, palette),
  check its geolocation (corners, and the −4.6 °C minimum at São Joaquim, SC), the PR/SC/RS
  colour range, every `read_grib` rejection, truncated downloads and `make figures` failures.
  Coverage, now including `scripts/` and branches: 72% → 87%.
