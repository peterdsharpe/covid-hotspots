# %% [md]
"""
# COVID-19 Hotspots
By Peter Sharpe
"""
# Imports:
# %%
import plotly.express as px
import pandas as pd
import datetime
from urllib.request import urlopen
import json
import numpy as np

# %% [md]
# Assumptions and data scrape:
# %%

today = datetime.datetime.today()
# today = datetime.datetime(year=2020, month=3, day=15) # Fix a date here, if desired

# Get COVID data
print("Downloading data...")
raw_covid_data = pd.read_csv(
    "https://github.com/nytimes/covid-19-data/raw/master/us-counties.csv",
    engine='python',
    encoding = "latin"
)

# Get population data
raw_population_data = pd.read_csv(
    "https://www2.census.gov/programs-surveys/popest/datasets/2010-2019/counties/totals/co-est2019-alldata.csv",
    engine='python',
    encoding = "latin"
)
print("Download complete.")

# %% [md]
# Clean data
# %%

# Grab important columns only
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

# Set some types
raw_covid_data["fips"] = raw_covid_data["fips"].astype(int)
raw_covid_data["date"] = pd.to_datetime(raw_covid_data["date"])

# Trim data to before today, in the case of backtesting
raw_covid_data = raw_covid_data[raw_covid_data["date"] <= today]

# Eliminate whole states from population data
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


def get_population(fips):
    index = county_populations["fips"].searchsorted(fips)
    if index == len(county_populations):  # no population data exists for this county
        return np.NaN
    return county_populations["population"].iloc[index]


covid_data["population"] = [
    get_population(fips)
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

with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
    counties = json.load(response)

names = list(covid_data["name"])
locations = list(covid_data["fips_str"])
new_daily_cases_per_100k = list(1e5 / 7 * covid_data['new cases in past week per capita'])
color_label = "Daily New Cases per 100k,<br>1-wk. moving avg."

# Fill in blank counties
county_ids = [
    feature["id"]
    for feature in counties["features"]
]
for id in county_ids:
    if id not in locations:
        locations.append(id)
        new_daily_cases_per_100k.append(0)
        names.append("No Data")

fig = px.choropleth(
    # covid_data,
    geojson=counties,
    locations=locations,
    color=new_daily_cases_per_100k,
    color_continuous_scale="viridis",
    range_color=(0, 100),
    scope="usa",
    hover_name=names,
    hover_data={color_label: new_daily_cases_per_100k},
    labels={"color": color_label},
)
fig.update_layout(
    margin={"r": 0, "l": 0, "b": 0},
    title=f'<b>Current COVID-19 Infection Rates Per Capita as of {datetime.datetime.date(today)}</b><br>'
          f'By <a href="https://peterdsharpe.github.io/">Peter Sharpe</a> | '
          f'Data Source: <a href="https://github.com/nytimes/covid-19-data">The New York Times</a> | '
          f'<a href="https://github.com/peterdsharpe/covid-hotspots">Source Code</a>'
)
fig.write_html(f"index.html")
# fig.show() # Uncomment this for a live display
