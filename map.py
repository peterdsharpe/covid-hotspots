# %% [md]
"""
# COVID-19 Hotspots
By Peter Sharpe
"""
# Imports:
# %%

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
import dash

sns.set(palette=sns.color_palette("husl"))
import cartopy.crs as ccrs
import pandas as pd
import requests
import io
import datetime

# %% [md]
# Assumptions and data scrape:
# %%

today = datetime.datetime.today()

# Get COVID data
raw_covid_data = pd.read_csv(
    "https://github.com/nytimes/covid-19-data/raw/master/us-counties.csv",
    # "https://github.com/nytimes/covid-19-data/raw/master/live/us-counties.csv",
    engine='python',
)

# Get population data
raw_population_data = pd.read_csv(
    "https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/counties/totals/co-est2019-alldata.csv",
    engine='python'
)

# %% [md]
# Clean data
# %%
important_columns = [
    "date",
    "county",
    "state",
    "fips",
    "cases",
    "deaths"
]
raw_covid_data = raw_covid_data[important_columns]
raw_covid_data = raw_covid_data.dropna()
raw_covid_data["fips"] = raw_covid_data["fips"].astype(int)

raw_population_data = raw_population_data.loc[raw_population_data["COUNTY"] != 0]

# %% [md]
# Make clean COVID data
# %%
covid_data = pd.DataFrame(columns=important_columns)

for fips in raw_covid_data["fips"].unique():
    all_county_covid_data = raw_covid_data.loc[raw_covid_data["fips"] == fips]

    county_covid_data = all_county_covid_data.iloc[-1].copy()

    # Add number of new cases in past week
    cases = all_county_covid_data["cases"].values
    try:
        county_covid_data["new cases in past week"] = cases[-1] - cases[-8]
    except IndexError:
        county_covid_data["new cases in past week"] = cases[-1]

    covid_data = covid_data.append(county_covid_data)

# %% [md]
# Add population and per-capita columns to the data:
# %%

county_populations = pd.DataFrame({
    "fips"      : 1000 * raw_population_data["STATE"] + raw_population_data["COUNTY"],
    "population": raw_population_data["POPESTIMATE2019"]
})

covid_data["population"] = [
    county_populations["population"].iloc[
        county_populations["fips"].searchsorted(fips)
    ]
    for fips in covid_data["fips"]
]

covid_data["cases per capita"] = covid_data["cases"] / covid_data["population"]
covid_data["deaths per capita"] = covid_data["deaths"] / covid_data["population"]
covid_data["new cases in past week per capita"] = covid_data["new cases in past week"] / covid_data["population"]
covid_data["new deaths in past week per capita"] = covid_data["new cases in past week"] / covid_data["population"]

# %% [md]
# Clean up some names before ready for use:
# %%

covid_data["name"] = covid_data["county"] + " County, " + covid_data["state"]
covid_data["fips_str"] = covid_data["fips"].apply(lambda x: str(x).zfill(5))

# %% [md]
# # Per-Capita New Cases:
# %%
from urllib.request import urlopen
import json

with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
    counties = json.load(response)

names = list(covid_data["name"])
locations = list(covid_data["fips_str"])
new_daily_cases_per_mil =  list(1e6 / 7 * covid_data['new cases in past week per capita'])
color_label = "Daily New Cases per 1M Pop.,<br>Avg. over Past Week"

# Fill in blank counties
county_ids = [
    feature["id"]
    for feature in counties["features"]
]
for id in county_ids:
    if id not in locations:
        locations.append(id)
        new_daily_cases_per_mil.append(0)
        names.append("No Data")

fig = px.choropleth(
    # covid_data,
    geojson=counties,
    locations=locations,
    color=new_daily_cases_per_mil,
    color_continuous_scale="viridis",
    range_color=(0, 250),
    scope="usa",
    hover_name=names,
    hover_data={color_label: new_daily_cases_per_mil},
    labels={"color": color_label},
)
fig.update_layout(
    margin={"r": 0, "l": 0, "b": 0},
    title=f"Current COVID-19 Infection Rates as of {datetime.datetime.date(today)}<br>By Peter Sharpe (Data Source: The New York Times)"
)
fig.show()
