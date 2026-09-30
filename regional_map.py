"""Independent region, network and node layers for hydrogen potential."""

from pathlib import Path
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from shapely.geometry import shape
import streamlit as st
import xarray as xr


COLUMNS = ["region", "country", "latitude", "longitude", "potential_twh_per_year"]
DEFAULT_BASEMAP = "https://tiles.openfreemap.org/styles/positron"

# Energy palette from https://wasserstoffatlas.de/en (public app settings).
ATLAS_ENERGY_COLORS = ["#9ae2ef", "#6fccdc", "#65a5b8", "#316e87", "#0d4b63"]

POTENTIAL = "Hydrogen potential (TWh H₂/year)"
NETWORK_COLUMNS = ["bus0", "bus1", "carrier", "capacity_gw"]
MAP_VIEWPORT_WIDTH, MAP_VIEWPORT_HEIGHT = 1400, 815
COLORBAR_MARGIN = 90
MIN_MAP_VALUE = 0.01  # hide connections and nodes that would show as 0.00
HIDDEN_METRICS = {'hydrogen_storage', 'solar_potential', 'wind_potential'}  # prepared, but not offered in the app


def read_regions(source):
    """Read WGS84 polygons keyed by the PyPSA region name."""
    content = source.read() if hasattr(source, "read") else Path(source).read_text()
    geojson = json.loads(content)
    if not isinstance(geojson, dict) or geojson.get("type") != "FeatureCollection" or not geojson.get("features"):
        raise ValueError("Regions must be a non-empty GeoJSON FeatureCollection.")
    names = set()
    for feature in geojson["features"]:
        if not isinstance(feature, dict) or not isinstance(feature.get("properties"), dict):
            raise ValueError("Every GeoJSON feature needs a properties object.")
        name = feature.get("properties", {}).get("name")
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError("Every GeoJSON feature needs a unique properties.name matching the CSV region.")
        geometry = feature.get("geometry") or {}
        if not isinstance(geometry, dict) or geometry.get("type") not in ("Polygon", "MultiPolygon"):
            raise ValueError("Region geometries must be Polygon or MultiPolygon.")
        try:
            polygon = shape(geometry)
        except Exception as exc:
            raise ValueError(f"Cannot read polygon for region {name}.") from exc
        if polygon.is_empty or not polygon.is_valid:
            raise ValueError(f"Invalid polygon for region {name}.")
        west, south, east, north = polygon.bounds
        if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
            raise ValueError("GeoJSON coordinates must be WGS84 longitude/latitude.")
        names.add(name)
    return geojson


def read_network(source, data):
    edges = pd.read_csv(source, dtype={"bus0": str, "bus1": str})
    missing = set(NETWORK_COLUMNS) - set(edges.columns)
    if missing:
        raise ValueError("Missing network columns: " + ", ".join(sorted(missing)))
    edges = edges[NETWORK_COLUMNS].copy()
    if edges.empty:
        raise ValueError("The network CSV contains no connections.")
    for col in ("bus0", "bus1", "carrier"):
        edges[col] = edges[col].astype("string").str.strip()
        if edges[col].isna().any() or edges[col].eq("").any():
            raise ValueError(f"Network {col} must not be blank.")
    if not edges.carrier.isin(["H2", "AC", "DC"]).all():
        raise ValueError("Network carrier must be H2, AC, or DC.")
    edges.capacity_gw = pd.to_numeric(edges.capacity_gw, errors="coerce")
    if not np.isfinite(edges.capacity_gw).all() or edges.capacity_gw.lt(0).any():
        raise ValueError("Network capacity_gw must be finite and non-negative.")
    if data.region.duplicated().any():
        raise ValueError("Network overlays require globally unique region names.")
    unknown = (set(edges.bus0) | set(edges.bus1)) - set(data.region)
    if unknown:
        raise ValueError("Unknown network endpoints: " + ", ".join(sorted(unknown)))
    return edges


def build_spatial_map(data, geojson, edges, regions, network, nodes, metrics=None, basemap=DEFAULT_BASEMAP):
    """Compose region shading, capacity-scaled edges and potential-scaled nodes."""
    # Plotly <5.24 uses Mapbox trace names and the matching layout key.
    modern_maps = hasattr(go, "Choroplethmap") and hasattr(go, "Scattermap")
    choropleth = go.Choroplethmap if modern_maps else go.Choroplethmapbox
    scatter = go.Scattermap if modern_maps else go.Scattermapbox
    map_layout = "map" if modern_maps else "mapbox"
    fig = go.Figure()
    metrics = metrics or {POTENTIAL: ("potential_twh_per_year", POTENTIAL, "TWh H₂/year")}
    region_column, region_label, region_unit = metrics.get(regions, next(iter(metrics.values())))
    node_column, node_label, node_unit = metrics.get(nodes, next(iter(metrics.values())))
    node_name = node_label.removesuffix(f" ({node_unit})")
    maximum = max(data[region_column].max(), 1e-9)
    node_maximum = max(data[node_column].max(), 1e-9)
    if geojson is not None:
        features = [f for f in geojson["features"] if f["properties"]["name"] in set(data.region)]
        names = [f["properties"]["name"] for f in features]
        values = data.set_index("region")[region_column].reindex(names)
        if names:
            fig.add_trace(choropleth(
                geojson={"type": "FeatureCollection", "features": features},
                featureidkey="properties.name", locations=names,
                z=values if regions != "Nothing" else np.zeros(len(names)),
                colorscale=ATLAS_ENERGY_COLORS if regions != "Nothing" else [[0, "white"], [1, "white"]],
                zmin=0, zmax=maximum, showscale=regions != "Nothing",
                colorbar={"x": 1, "xanchor": "left", "tickfont": {"size": 16, "color": "#31333F"}},
                marker={"opacity": 0.65, "line": {"color": "#888", "width": 1}},
                hovertemplate=region_label.removesuffix(f" ({region_unit})") + ": %{z:.2f} " + region_unit + "<extra></extra>",
                hoverinfo="skip" if regions == "Nothing" else None,
                name="Regions",
            ))
    if network != "Nothing" and edges is not None:
        carriers = ["H2"] if network == "Hydrogen Network" else ["AC", "DC"]
        selected = edges[edges.carrier.isin(carriers) & edges.bus0.isin(data.region) & edges.bus1.isin(data.region) & edges.capacity_gw.ge(MIN_MAP_VALUE)]
        coords = data.set_index("region")
        scale = selected.capacity_gw.max()
        for i, edge in enumerate(selected.itertuples()):
            endpoints = coords.loc[[edge.bus0, edge.bus1]]
            fig.add_trace(scatter(
                lat=endpoints.latitude, lon=endpoints.longitude, mode="lines",
                line={"width": max(1, 10 * edge.capacity_gw / scale), "color": "#b64b9b" if edge.carrier == "H2" else "#d97706"},
                hoverinfo="skip", name=network, legendgroup="network", showlegend=i == 0,
            ))
        if not selected.empty:
            # Map lines are only hoverable at their vertices, which sit under the
            # nodes, so an invisible marker at each midpoint carries the value.
            start, end = coords.loc[selected.bus0], coords.loc[selected.bus1]
            fig.add_trace(scatter(
                lat=(start.latitude.values + end.latitude.values) / 2,
                lon=(start.longitude.values + end.longitude.values) / 2,
                mode="markers", marker={"size": 14, "opacity": 0},
                text=[f"Pipeline capacity: {capacity:.2f} GW H₂" if carrier == "H2" else f"Line capacity: {capacity:.2f} GWₑ"
                      for carrier, capacity in zip(selected.carrier, selected.capacity_gw)],
                hovertemplate="%{text}<extra></extra>", name=network, legendgroup="network", showlegend=False,
            ))
        if selected.empty:
            # Keep the legend entry when every connection is below the display threshold.
            fig.add_trace(scatter(
                lat=[None], lon=[None], mode="lines", hoverinfo="skip",
                line={"width": 3, "color": "#b64b9b" if network == "Hydrogen Network" else "#d97706"},
                name=network, legendgroup="network", showlegend=True,
            ))
    if nodes != "Nothing":
        shown = data[data[node_column].ge(MIN_MAP_VALUE)]
        fig.add_trace(scatter(
            lat=shown.latitude, lon=shown.longitude, mode="markers", text=shown.region,
            customdata=shown[["country", node_column]],
            marker={"size": np.maximum(6, 40 * np.sqrt(shown[node_column] / node_maximum)), "color": "#454545", "opacity": 0.75},
            hovertemplate=node_name + ": %{customdata[1]:.2f} " + node_unit + "<extra></extra>",
            name=node_name, showlegend=not shown.empty,
        ))
        if shown.empty:
            # Keep the legend entry when every node is below the display threshold.
            fig.add_trace(scatter(
                lat=[None], lon=[None], mode="markers", hoverinfo="skip",
                marker={"size": 12, "color": "#454545", "opacity": 0.75}, name=node_name,
            ))
    west, east = data.longitude.min(), data.longitude.max()
    south, north = data.latitude.min(), data.latitude.max()
    if geojson is not None:
        for feature in features:
            geometry = shape(feature['geometry'])
            if geometry.is_empty:
                continue
            xmin, ymin, xmax, ymax = geometry.bounds
            west, east = min(west, xmin), max(east, xmax)
            south, north = min(south, ymin), max(north, ymax)
    lon_padding = max((east - west) * 0.03, 0.05)
    lat_padding = max((north - south) * 0.03, 0.05)
    bounds = dict(west=west - lon_padding, east=east + lon_padding,
                  south=south - lat_padding, north=north + lat_padding)
    # Explicit camera values are updated on country changes; bounds alone can
    # leave Plotly's existing map camera unchanged.
    mercator_south, mercator_north = np.arcsinh(np.tan(np.radians(
        np.clip([bounds['south'], bounds['north']], -85, 85)
    )))
    center = dict(
        lon=(west + east) / 2,
        lat=float(np.degrees(np.arctan(np.sinh((mercator_south + mercator_north) / 2)))),
    )
    longitude_fraction = max((bounds['east'] - bounds['west']) / 360, 1e-6)
    latitude_fraction = max((mercator_north - mercator_south) / (2 * np.pi), 1e-6)
    # Usable viewport in pixels (world is 512 px wide at zoom 0): the width is a
    # conservative estimate of the wide-layout chart minus the colour scale,
    # the height is the figure height minus the bottom margin.
    zoom = float(np.clip(min(np.log2(MAP_VIEWPORT_WIDTH / (512 * longitude_fraction)),
                             np.log2(MAP_VIEWPORT_HEIGHT / (512 * latitude_fraction))), 0, 8))
    camera_revision = 'country-camera|' + '|'.join(data.region)
    # Plotly can only rotate colour bar titles counter-clockwise, so the title
    # is a clockwise-rotated annotation at the right edge of the figure.
    show_colorbar = geojson is not None and bool(names) and regions != "Nothing"
    if show_colorbar:
        fig.add_annotation(
            x=1, y=0.5, xref="paper", yref="paper", xanchor="right", yanchor="middle",
            xshift=COLORBAR_MARGIN, textangle=90, showarrow=False,
            text=region_label, font={"size": 16, "color": "#31333F"},
        )
    fig.update_layout(
        **{map_layout: {"style": basemap, "center": center, "zoom": zoom,
                       "uirevision": camera_revision}},
        height=850, margin={"l": 0, "r": COLORBAR_MARGIN if show_colorbar else 0, "t": 0, "b": 85},
        legend={"orientation": "h", "font": {"size": 16, "color": "#31333F"}, "x": 1, "xanchor": "right", "y": -0.015, "yanchor": "top"}, uirevision=camera_revision,
    )
    return fig


def read_potential(source):
    data = pd.read_csv(source, dtype={"region": str, "country": str})
    missing = set(COLUMNS) - set(data.columns)
    if missing:
        raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
    data = data[COLUMNS].copy()
    if data.empty:
        raise ValueError("The CSV contains no regional observations.")
    for column in COLUMNS[:2]:
        if data[column].isna().any():
            raise ValueError(f"{column} must be supplied for every row.")
        data[column] = data[column].astype(str).str.strip()
        if data[column].eq("").any():
            raise ValueError(f"{column} must not be blank.")
    for column in COLUMNS[2:]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
        if not np.isfinite(data[column]).all():
            raise ValueError(f"{column} must contain finite numeric values in every row.")
    if not data.latitude.between(-90, 90).all() or not data.longitude.between(-180, 180).all():
        raise ValueError("Coordinates must be WGS84 latitude (-90 to 90) and longitude (-180 to 180).")
    if data.potential_twh_per_year.lt(0).any():
        raise ValueError("Hydrogen potential must be non-negative.")
    if data.duplicated(["country", "region"]).any():
        raise ValueError("Supply one row per country and region; select a single scenario and year before importing.")
    return data


def model_countries():
    bundles = (Path(__file__).parent / "data" / "spatial").glob("*/*/*/metadata.json")
    return sorted({p.parent.parent.parent.name for p in bundles})



def render_regional_map(country, definitions_container=None):
    # The Streamlit Cloud toolbar overlaps the top of the page, so the title is pushed below it.
    st.markdown('<div style="height:2.5rem"></div>', unsafe_allow_html=True)
    st.title(f"H2Atlas {country}")
    bundles = sorted((Path(__file__).parent / "data" / "spatial").glob("*/*/*/metadata.json"))
    render_model_results(bundles, country, definitions_container=definitions_container)


@st.cache_data
def load_model_bundle(directory, modified):
    """Only small prepared files are loaded here; PyPSA stays in preprocessing."""
    directory = Path(directory)
    with xr.open_dataset(directory / 'report.nc') as source:
        report = source.load()
    data = report.to_dataframe().reset_index()
    geojson = read_regions(directory / 'regions.geojson')
    edges = pd.read_csv(directory / 'network.csv', dtype={'bus0': str, 'bus1': str})
    metrics = {key: (key, f"{value.attrs['label']} ({value.attrs['units']})", value.attrs['units'])
               for key, value in report.data_vars.items()}
    return data, geojson, edges, metrics, report.attrs


def render_model_results(bundles, country, basemap=DEFAULT_BASEMAP, definitions_container=None):
    if not bundles:
        st.info('No preprocessed model data found. Run the spatial preparation step first.')
        st.code('python HySEE-Preparation/workflow/notebooks/streamlit-data.py --spatial --project-dir Bulgaria/pypsa-earth', language='bash')
        return
    available = [p for p in bundles if p.parent.parent.parent.name == country]
    if country == 'Bulgaria':
        available = [p for p in available if p.parent.name.endswith('_0export')]
        if not available:
            st.info('No prepared 0export result found for Bulgaria.')
            return
    if not available:
        st.info(f'No prepared model data found for {country}.')
        return
    bundle = sorted(available)[0]
    try:
        data, geojson, edges, metrics, attributes = load_model_bundle(str(bundle.parent), max(f.stat().st_mtime_ns for f in bundle.parent.iterdir()))
    except (ValueError, OSError, KeyError) as exc:
        st.error(f'Cannot load prepared model data: {exc}')
        return
    # Energy quantities (TWh, GWh) shade the regions, power capacities (GW) size the nodes.
    energy_options = ['Nothing', *[key for key, (_, _, unit) in metrics.items() if 'Wh' in unit and key not in HIDDEN_METRICS]]
    capacity_options = ['Nothing', *[key for key, (_, _, unit) in metrics.items() if 'Wh' not in unit and key not in HIDDEN_METRICS]]
    format_metric = lambda key: metrics[key][1].removesuffix(f" ({metrics[key][2]})") if key in metrics else key
    col1, col2, col3 = st.columns(3)
    regions = col1.selectbox('Energy', energy_options, index=min(1, len(energy_options) - 1), format_func=format_metric)
    network = col2.selectbox('Network', ['Nothing', 'Hydrogen Network', 'Electricity Network'], index=1)
    # The list heading already says "Capacity", so the word is dropped from its entries.
    nodes = col3.selectbox('Capacity', capacity_options, format_func=lambda key: format_metric(key).replace(' capacity', ''),
                           index=capacity_options.index('electrolyser_capacity') if 'electrolyser_capacity' in capacity_options else min(1, len(capacity_options) - 1))
    fig = build_spatial_map(data, geojson, edges, regions, network, nodes, metrics, basemap=basemap)
    summaries = []
    for selection in (regions, nodes):
        if selection == 'Nothing':
            continue
        key, label, unit = metrics[selection]
        label = label.removesuffix(f' ({unit})')
        summaries.append(f'{label}: <b>{data[key].sum():,.0f} {unit}</b>')
    if summaries:
        fig.add_annotation(
            x=0, y=-0.015, xref='paper', yref='paper',
            xanchor='left', yanchor='top', showarrow=False,
            font={"size": 16, "color": "#31333F"},
            text=' &nbsp; · &nbsp; '.join(summaries),
        )
    st.plotly_chart(fig, use_container_width=True, key=f"regional_map_{country}")
    definitions_container = definitions_container if definitions_container is not None else st.sidebar
    with definitions_container.expander('Definitions'):
        with xr.open_dataset(bundle.parent / 'report.nc') as report:
            for key, value in report.data_vars.items():
                if key in HIDDEN_METRICS:
                    continue
                st.write(f"**{value.attrs['label']}:** {value.attrs['definition']}")
