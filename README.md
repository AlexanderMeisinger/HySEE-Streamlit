# HySEE - Hydrogen in Southeast Europe"

Base: [![DOI](https://zenodo.org/badge/451538981.svg)](https://zenodo.org/badge/latestdoi/451538981) & [![GitHub](https://github.com/AlexanderMeisinger/Demand-Europe-Streamlit)](https://github.com/AlexanderMeisinger/Demand-Europe-Streamlit)

Branch: [HySEE-Energy-Model](https://github.com/AlexanderMeisinger/HySEE-Energy-Model)

Preparation: [HySEE-Preparation](https://github.com/AlexanderMeisinger/HySEE-Preparation)

## Code for interactive dashboard for results exploration.

See live version at: https://hysee.streamlit.app/

## Local Installation and Usage

Install dependencies:

```sh
pip install -r requirements.txt
```

Start interactive dashboard:

```sh
streamlit run streamlit_app.py
```

## Spatial configurations

The default input is **preprocessed model results**, following the spatial view in
[fneum/spatial-sector-dashboard](https://github.com/fneum/spatial-sector-dashboard/blob/master/streamlit_app.py).
The app reads small exports from `data/spatial/`; it does not load full PyPSA
networks or run calculations on every Streamlit interaction.

From the workspace root, activate your PyPSA-Earth environment and run:

```sh
python HySEE-Preparation/workflow/notebooks/streamlit-data.py --spatial --project-dir Bulgaria/pypsa-earth --run 1h-sec
```

The preparation step reads:

- `Bulgaria/pypsa-earth/results/1h-sec/postnetworks/*.nc`: solved networks,
  optimised capacities, link flows, snapshot weights and bus coordinates.
- `Bulgaria/pypsa-earth/resources/1h-sec/bus_regions/regions_onshore_elec_s_10.geojson`:
  matching regional boundaries. The resolution token is inferred from each network
  filename; `--regions` can explicitly select a different file.

Each result produces `report.nc`, `regions.geojson`, `network.csv`, and
`metadata.json` under `HySEE-Streamlit/data/spatial/<country>/<run>/<network>/`.
Bulgaria's two available results have already been exported. To process Romania,
change `--project-dir` to `Romania/pypsa-earth`. Use `--network /path/to/result.nc`
for one result or `--output-dir /path/to/data/spatial` for another dashboard.

Select **Spatial configurations**, then the model country and result. The three
independent layer controls are:

- **Regions**: colour regions by a selected regional metric.
- **Network**: hydrogen or electricity connections, with width scaled by capacity.
- **Nodes**: size nodes by a separately selected regional metric.

Available metrics are hydrogen production and exports, electrolyser and hydrogen
storage capacity, installed solar/onshore wind capacity, and solar/onshore wind
capacity potential. Each metric includes its unit and definition in the exported
NetCDF and the dashboard's data expander.

Production includes all electricity-to-H₂ links, including alkaline, PEM and SOEC.
Energy totals use negative output-port flows clipped to positive delivery and
weighted by generator snapshot hours. Totals cover the model period (8,760 hours
for these Bulgaria results). Production and exports are **model results**, not
technical hydrogen potential. Renewable `p_nom_max` values describe electricity
capacity limits and are not converted into hypothetical H₂ output.

The selected result controls the spatial data. The legacy Europe/Germany sidebar
sensitivities do not apply. The two Bulgaria filenames currently yield the same
hydrogen totals; they remain separately selectable to preserve source provenance.
Network connections use regional endpoints, not actual pipeline routes. The map
supports Plotly >=5.15 and requires internet access for basemap tiles.
The map always uses the light **OpenFreeMap Positron** background. Its muted
colours keep regional overlays prominent. [OpenFreeMap](https://openfreemap.org/) provides
its public maps without registration or an API key.
Plotly versions before 5.24 automatically use the compatible Mapbox traces; newer
versions use MapLibre traces. No map API token is required.

### Optional custom data

Choose **Custom CSV** to use manually prepared data instead. Required columns are
`region,country,latitude,longitude,potential_twh_per_year`, with one observation
per region, WGS84 coordinates, non-negative potential and a consistent scenario,
year and H₂ energy basis. Optional boundary GeoJSON uses unique `properties.name`
values matching `region`. Optional network CSV uses `bus0,bus1,carrier,capacity_gw`
with carrier `H2`, `AC` or `DC` and endpoints matching globally unique region IDs.
Templates are available in the app. The earlier automatic filenames
`data/regional_hydrogen_potential.csv`, `data/regions.geojson` and
`data/spatial_network.csv` remain supported in this mode.

### Checks

```sh
python -m unittest discover -s tests
```

## License

[MIT](LICENSE)

Regional fills and their colour bar use the Wasserstoffatlas energy palette:
`#9ae2ef`, `#6fccdc`, `#65a5b8`, `#316e87`, `#0d4b63`
([original palette definition](https://wasserstoffatlas.de/_app/immutable/chunks/app.CELyt09p.js)).
The dashboard retains continuous scaling from zero to the displayed metric's
maximum; it does not copy the Atlas's quantile classification thresholds.
