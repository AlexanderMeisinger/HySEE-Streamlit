# This script visualize results from PyPSA-Eur via Streamlit
# Author: Alexander Meisinger
# Base: https://github.com/fneum/spatial-sector-dashboard and https://github.com/PyPSA/pypsa-eur

import streamlit as st
import pandas as pd
import numpy as np
import xarray as xr
import yaml
import plotly.graph_objects as go
from matplotlib.colors import to_rgba
from contextlib import suppress
import geopandas as gpd
import networkx as nx
import hvplot.networkx as hvnx
import holoviews as hv
import datetime
import hvplot.pandas
import plotly.express as px
from PIL import Image
from regional_map import model_countries, render_regional_map

from helpers import rename_techs_energy_balance, prepare_colors, rename_techs_h2_balance, rename_tech_capacity

CACHE_TTL = 24*3600 # seconds

### MAIN

with open("data/config.yaml", encoding='utf-8') as file:
    config = yaml.safe_load(file)

preferred_order_energy_balance = pd.Index(config['preferred_order_energy_balance'])

## DISPLAY

st.set_page_config(
    page_title='HySEE – Hydrogen in Southeast Europe',
    layout="wide"
)

style = '<style>div.block-container{padding-top:.5rem; padding-bottom:0rem; padding-right:1.2rem; padding-left:1.2rem} footer {display: none !important;} [data-testid="stMetricLabel"] p {font-size: 16px !important;}</style>'
st.write(style, unsafe_allow_html=True)

## SIDEBAR

with st.sidebar:
    image = Image.open("euki-logo.png")
    st.image(image, width=250)
    
    st.title("HySEE – Hydrogen in Southeast Europe")

    st.markdown("""
        **Institute for Energy Networks and Energy Storage, OTH Regensburg**
    """)

    spatial_countries = model_countries()
    pages = [
        # "Europe",
        # "Germany",
        *spatial_countries,
    ]
    display = st.selectbox("Region", pages, help="Choose your view on the system.")

    # Scenario sensitivities are set aside for now; all stay at the base scenario (0).
    show_scenario_settings = False
    sel = dict.fromkeys(["low_carbon", "high_carbon", "low_h2cost", "grid_freeze", "high_h2demand"], 0)

    if show_scenario_settings:
        choices = {0: "2 °C", 1: "1.5 °C"}
        sel["low_carbon"] = st.radio(
            ":thermometer: Temperature rise",
            choices,
            format_func=lambda x: choices[x],
            horizontal=True,
            help='**Scenario settings:**\n\n'
            '**2.0 °C:** Basis Scenario aligned with the European Green Deal. \n\n'
            '**1.5 °C:** Scenario disigned to analyse the impact of the 1.5 °C climate target.',
        )

        choices = {0: "yes", 1: "no"}
        sel["high_carbon"] = st.radio(
            ":factory: Climate goals",
            choices,
            format_func=lambda x: choices[x],
            horizontal=True,
            help='**Scenario settings:**\n\n'
            '**Yes:** Basis Scenario aligned with the European Green Deal. \n\n'
            '**No:** Scenario designed to analyse the impact of no further progress on climate actions after 2025.',
        )

        choices = {0: "No", 1: "Yes"}
        sel["low_h2cost"] = st.radio(
            "💰 Low H2 cost",
            choices,
            format_func=lambda x: choices[x],
            horizontal=True,
            help='**Scenario settings:**\n\n'
            '**No:** Basis Scenario aligned with the European Green Deal. \n\n'
            '**Yes:** Scenario designed to analyse the impact of a 25% reduction in electrolyser CAPEX costs.',
        )

        choices = {0: "no", 1: "yes"}
        sel["grid_freeze"] = st.radio(
            "🧊 Grid freeze",
            choices,
            format_func=lambda x: choices[x],
            horizontal=True,
            help='**Scenario settings:**\n\n'
            '**No:** Basis Scenario aligned with the European Green Deal. \n\n'
            '**Yes:** Scenario designed to analyse the impact of no additional network expansion.',
        )

        choices = {0: "no", 1: "yes"}
        sel["high_h2demand"] = st.radio(
            "💧 High H2 demand",
            choices,
            format_func=lambda x: choices[x],
            horizontal=True,
            help='**Scenario settings:**\n\n'
            '**No:** Basis Scenario aligned with the European Green Deal. \n\n'
            '**Yes:** Scenario designed to analyse the impact of a 20% increase in hydrogen demand in the HVC industry, aviation, and automotive sectors.',
        )

    number_sensitivities = sel["low_carbon"] + sel["low_h2cost"] + sel["grid_freeze"] + sel["high_h2demand"] + sel["high_carbon"]

    definitions_container = st.container()

    with st.expander("About"):
         st.write("""
             All results were created using the open energy system model PyPSA-Earth. The model covers all energy sectors including
             electricity, buildings, transport, agriculture and industry at high spatio-temporal resolution. The code for the energy model and for data preparation is available on
             [Github-Model](https://github.com/AlexanderMeisinger/pypsa-earth/tree/hysee) and [Github-Preparation](https://github.com/AlexanderMeisinger/HySEE-Preparation).

             We acknowledge funding from the European Climate Initiative (EUKI) and the German Federal Ministry for the Environment, Climate Action, Nature Conservation and Nuclear Safety.
             """)

## PAGES

if display in spatial_countries:
    render_regional_map(display, definitions_container=definitions_container)

if (display == "Europe") and (number_sensitivities <= 1):

    st.markdown("<br>", unsafe_allow_html=True)
    st.title("Europe")

    choices = config["EU_scenarios"]
    idx = st.selectbox("View", choices, format_func=lambda x: choices[x], label_visibility='hidden')

    ds = xr.open_dataset("data/EU_scenarios_streamlit.nc")

    accessors = {k: v for k, v in sel.items() if k not in ['power_grid', 'hydrogen_grid']}
    df = ds[idx].sel(**accessors, drop=True).to_dataframe().squeeze().unstack(level=0).dropna(axis=1)

    df.index = ["".join(str(col)).strip() for col in df.index.values]

    if idx == "energy":
        df.columns = df.columns.map(rename_techs_energy_balance)
        df = df.T.groupby(level=0).sum().T
        
        to_drop = df.columns[(df.abs() < 50).all(axis=0)] # ToDo: Outsource energy threshold
        df.drop(columns=to_drop, inplace=True)
        
        missing = df.columns.difference(preferred_order_energy_balance)
        order = preferred_order_energy_balance.intersection(df.columns).append(missing)
        df = df.loc[:, order]
    elif idx == "hydrogen": 
        df.columns = df.columns.map(rename_techs_h2_balance)
        df = df.T.groupby(level=0).sum().T
        
        to_drop = df.columns[(df.abs() < 50).all(axis=0)] # ToDo: Outsource energy threshold
        df.drop(columns=to_drop, inplace=True)
    elif idx == "storage" or idx == "generation" or idx == "conversion":
        df.columns = df.columns.map(rename_tech_capacity)
        df = df.T.groupby(level=0).sum().T
        
        to_drop = df.columns[(df.abs() < 1).all(axis=0)] # ToDo: Outsource energy threshold
        df.drop(columns=to_drop, inplace=True)
    else:
        df.columns = df.columns.map(rename_techs_energy_balance)
        df = df.T.groupby(level=0).sum().T
        
        to_drop = df.columns[(df.abs() < 1).all(axis=0)] # ToDo: Outsource energy threshold
        df.drop(columns=to_drop, inplace=True)
        
        missing = df.columns.difference(preferred_order_energy_balance)
        order = preferred_order_energy_balance.intersection(df.columns).append(missing)
        df = df.loc[:, order]

    if idx == 'storage':
         df.drop("co2", axis=1, inplace=True, errors="ignore")
         df.drop("co2 sequestered", axis=1, inplace=True, errors="ignore")
         df.drop("electricity distribution grid", axis=1, inplace=True, errors="ignore")
         df.drop("oil", axis=1, inplace=True, errors="ignore")
         df.drop("oil refining", axis=1, inplace=True, errors="ignore")
         df.drop("methanol", axis=1, inplace=True, errors="ignore")
         df.drop("methane", axis=1, inplace=True, errors="ignore")
         df.drop("ammonia store", axis=1, inplace=True, errors="ignore")
         df.drop("solar rooftop", axis=1, inplace=True, errors="ignore")
         df.drop("solid biomass", axis=1, inplace=True, errors="ignore")
         df.drop("unsustainable biogas", axis=1, inplace=True, errors="ignore")
         df.drop("unsustainable bioliquids", axis=1, inplace=True, errors="ignore")
         df.drop("unsustainable solid biomass", axis=1, inplace=True, errors="ignore")
         df.drop("Solar", axis=1, inplace=True, errors="ignore")
         df.drop("biogas", axis=1, inplace=True, errors="ignore")
         df.drop("gas", axis=1, inplace=True, errors="ignore")
         df.drop("solid biomass transport", axis=1, inplace=True, errors="ignore")
         df.drop("solar PV", axis=1, inplace=True, errors="ignore")
         df.drop("others", axis=1, inplace=True, errors="ignore")
         df.drop("hydrogen", axis=1, inplace=True, errors="ignore")
         df.drop("coal", axis=1, inplace=True, errors="ignore")
         df.drop("co2 stored", axis=1, inplace=True, errors="ignore")
         df.drop("lignite", axis=1, inplace=True, errors="ignore")
         df.drop("solar-hsat", axis=1, inplace=True, errors="ignore")
         df.drop("onshore wind", axis=1, inplace=True, errors="ignore")

    if idx == 'generation':
        df.drop("coal", axis=1, inplace=True, errors="ignore")
        df.drop("gas", axis=1, inplace=True, errors="ignore")
        df.drop("lignite", axis=1, inplace=True, errors="ignore")
        df.drop("nuclear", axis=1, inplace=True, errors="ignore")
        df.drop("oil", axis=1, inplace=True, errors="ignore")
        df.drop("biogas", axis=1, inplace=True, errors="ignore")
        df.drop("solid biomass", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable biogas", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable bioliquids", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable solid biomass", axis=1, inplace=True, errors="ignore")

    colors = prepare_colors(config)
    color = [colors[c] for c in df.columns]

    unit = choices[idx].split(" (")[1][:-1]

    ylim = config["ylim"][idx]

    plot = px.bar(
    df,
    x=df.index,  # Assuming the DataFrame index represents the x-axis
    y=df.columns,  # Stack the bars using the columns of the DataFrame
    color_discrete_sequence=color,  # Apply the color sequence
    labels={"value": f"{choices[idx]}", "index": ""},
    height=720,
    )

    # Update layout for font scaling and legend
    plot.update_layout(
        font=dict(size=18),  # Global font size, analogous to hvplot's fontscale
        xaxis=dict(
            title=dict(font=dict(size=18)),  # X-axis title font size
            tickfont=dict(size=16),  # X-axis tick labels font size
        ),
        yaxis=dict(
            title=dict(font=dict(size=18)),  # Y-axis title font size
            tickfont=dict(size=16),  # Y-axis tick labels font size
            tickformat=".0f"
        ),
        legend=dict(
            title=dict(text=""),  # Remove the legend title
            font=dict(size=16),  # Legend font size
        ),
    )

    # Add hover tooltips
    plot.update_traces(
        hovertemplate="Technology: %{x}<br>Value: %{y:.2f}<br>"
    )

    # Display the Plotly chart in Streamlit
    st.plotly_chart(plot, use_container_width=True)

if (display == "Germany") and (number_sensitivities <= 1):

    st.markdown("<br>", unsafe_allow_html=True)
    st.title("Germany")

    choices = config["DE_scenarios"]
    idx = st.selectbox("View", choices, format_func=lambda x: choices[x], label_visibility='hidden')

    ds = xr.open_dataset("data/DE_scenarios_streamlit.nc")

    accessors = {k: v for k, v in sel.items() if k not in ['power_grid', 'hydrogen_grid']}
    df = ds[idx].sel(**accessors, drop=True).to_dataframe().squeeze().unstack(level=0).dropna(axis=1)

    df.index = ["".join(str(col)).strip() for col in df.index.values]

    if idx == "energy":
        df.columns = df.columns.map(rename_techs_energy_balance)
        df = df.T.groupby(level=0).sum().T
        
        to_drop = df.columns[(df.abs() < 1).all(axis=0)] # ToDo: Outsource energy threshold
        df.drop(columns=to_drop, inplace=True)
        
        missing = df.columns.difference(preferred_order_energy_balance)
        order = preferred_order_energy_balance.intersection(df.columns).append(missing)
        df = df.loc[:, order]
    elif idx == "hydrogen": 
        df.columns = df.columns.map(rename_techs_h2_balance)
        df = df.T.groupby(level=0).sum().T
        
        to_drop = df.columns[(df.abs() < 1).all(axis=0)] # ToDo: Outsource energy threshold
        df.drop(columns=to_drop, inplace=True)
    elif idx == "storage" or idx == "generation" or idx == "conversion":
        df.columns = df.columns.map(rename_tech_capacity)
        df = df.T.groupby(level=0).sum().T
        
        to_drop = df.columns[(df.abs() < 1).all(axis=0)] # ToDo: Outsource energy threshold
        df.drop(columns=to_drop, inplace=True)
    else:
        df.columns = df.columns.map(rename_techs_energy_balance)
        df = df.T.groupby(level=0).sum().T
        
        to_drop = df.columns[(df.abs() < 1).all(axis=0)] # ToDo: Outsource energy threshold
        df.drop(columns=to_drop, inplace=True)
        
        missing = df.columns.difference(preferred_order_energy_balance)
        order = preferred_order_energy_balance.intersection(df.columns).append(missing)
        df = df.loc[:, order]

    if idx == 'storage':
        df.drop("co2", axis=1, inplace=True, errors="ignore")
        df.drop("co2 sequestered", axis=1, inplace=True, errors="ignore")
        df.drop("electricity distribution grid", axis=1, inplace=True, errors="ignore")
        df.drop("oil", axis=1, inplace=True, errors="ignore")
        df.drop("oil refining", axis=1, inplace=True, errors="ignore")
        df.drop("methanol", axis=1, inplace=True, errors="ignore")
        df.drop("methane", axis=1, inplace=True, errors="ignore")
        df.drop("ammonia store", axis=1, inplace=True, errors="ignore")
        df.drop("solar rooftop", axis=1, inplace=True, errors="ignore")
        df.drop("solid biomass", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable biogas", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable bioliquids", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable solid biomass", axis=1, inplace=True, errors="ignore")
        df.drop("Solar", axis=1, inplace=True, errors="ignore")
        df.drop("biogas", axis=1, inplace=True, errors="ignore")
        df.drop("gas", axis=1, inplace=True, errors="ignore")
        df.drop("solid biomass transport", axis=1, inplace=True, errors="ignore")
        df.drop("solar PV", axis=1, inplace=True, errors="ignore")
        df.drop("others", axis=1, inplace=True, errors="ignore")
        df.drop("hydrogen", axis=1, inplace=True, errors="ignore")   

    if idx == 'generation':
        df.drop("coal", axis=1, inplace=True, errors="ignore")
        df.drop("gas", axis=1, inplace=True, errors="ignore")
        df.drop("lignite", axis=1, inplace=True, errors="ignore")
        df.drop("nuclear", axis=1, inplace=True, errors="ignore")
        df.drop("oil", axis=1, inplace=True, errors="ignore")
        df.drop("biogas", axis=1, inplace=True, errors="ignore")
        df.drop("solid biomass", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable biogas", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable bioliquids", axis=1, inplace=True, errors="ignore")
        df.drop("unsustainable solid biomass", axis=1, inplace=True, errors="ignore")

    colors = prepare_colors(config)
    color = [colors[c] for c in df.columns]

    unit = choices[idx].split(" (")[1][:-1]

    ylim = config["ylim"][idx]

    plot = px.bar(
    df,
    x=df.index,  # Assuming the DataFrame index represents the x-axis
    y=df.columns,  # Stack the bars using the columns of the DataFrame
    color_discrete_sequence=color,  # Apply the color sequence
    labels={"value": f"{choices[idx]}", "index": ""},
    height=720,
    )

    # Update layout for font scaling and legend
    plot.update_layout(
        font=dict(size=18),  # Global font size, analogous to hvplot's fontscale
        xaxis=dict(
            title=dict(font=dict(size=18)),  # X-axis title font size
            tickfont=dict(size=16),  # X-axis tick labels font size
        ),
        yaxis=dict(
            title=dict(font=dict(size=18)),  # Y-axis title font size
            tickfont=dict(size=16),  # Y-axis tick labels font size
            tickformat=".1f" if idx =="storage" else ".0f"
        ),
        legend=dict(
            title=dict(text=""),  # Remove the legend title
            font=dict(size=16),  # Legend font size
        ),
    )

    # Add hover tooltips
    plot.update_traces(
        hovertemplate="Technology: %{x}<br>Value: %{y:.2f}<br>"
    )

    # Display the Plotly chart in Streamlit
    st.plotly_chart(plot, use_container_width=True)


if number_sensitivities > 1 and display in ("Europe", "Germany"):
    
    st.write("")
    st.write("")

    message = "Sorry, you can only choose one additional sensitivity in the lower block of the left panel!"
    st.error(message, icon="🚨")
