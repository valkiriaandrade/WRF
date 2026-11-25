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
