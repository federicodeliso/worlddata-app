import joblib
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
from functools import lru_cache

# =========================================================
# DATA
# =========================================================
datasets_dict = joblib.load("datasets.joblib")

for ds, df in datasets_dict.items():
    datasets_dict[ds] = df.loc[:, ~df.columns.duplicated()]

dataset_types = {
    "Nominal": [ds for ds in datasets_dict if ("REAL" not in ds) and ("1990" not in ds) and ("2024" not in ds)],
    "Real 2024": [ds for ds in datasets_dict if "2024" in ds],
    "YoY % Change": list(datasets_dict.keys())
}

for k in dataset_types:
    dataset_types[k].sort()

@lru_cache(maxsize=50)
def get_dataset(ds_name):
    df = datasets_dict.get(ds_name)
    if df is None:
        return None
    df = df.copy()
    if "Country Name" not in df.columns:
        df = df.reset_index()
        df.columns = ["Country Name"] + list(df.columns[1:])
    return df

# =========================================================
# APP
# =========================================================
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# =========================================================
# HOME PAGE
# =========================================================
home_layout = html.Div([
    html.H1("📊 Dashboard Home", style={"textAlign": "center"}),

    html.Br(),

    dcc.Link("📈 Line Chart", href="/line"),
    html.Br(),
    dcc.Link("🔵 Scatter Comparison", href="/scatter"),
    html.Br(),
    dcc.Link("📊 Bar Ranking", href="/bar"),
])

# =========================================================
# LINE PAGE (YOUR EXISTING ONE SIMPLIFIED HERE)
# =========================================================
line_layout = html.Div([

    dcc.Link("⬅ Home", href="/"),
    html.H2("Line Chart"),

    dcc.Dropdown(
        id="type-dropdown",
        options=[{"label": t, "value": t} for t in dataset_types.keys()],
        value="Nominal",
        clearable=False
    ),

    dcc.Dropdown(id="dataset-dropdown", multi=True),
    dcc.Dropdown(id="country-dropdown", multi=True),

    dcc.Graph(id="line-chart")
])

# =========================================================
# SCATTER PAGE
# =========================================================
scatter_layout = html.Div([

    dcc.Link("⬅ Home", href="/"),
    html.H2("Scatter Comparison"),

    dcc.Dropdown(
        id="scatter-datasets",
        options=[{"label": d, "value": d} for d in datasets_dict.keys()],
        multi=True,
        placeholder="Select 2 datasets"
    ),

    dcc.Dropdown(
        id="scatter-countries",
        options=[],
        multi=True
    ),

    dcc.Slider(
        id="scatter-year",
        min=0,
        max=10,
        value=0,
        step=1
    ),

    dcc.Graph(id="scatter-graph")
])

# =========================================================
# BAR PAGE
# =========================================================
bar_layout = html.Div([

    dcc.Link("⬅ Home", href="/"),
    html.H2("Bar Ranking"),

    dcc.Dropdown(
        id="bar-dataset",
        options=[{"label": d, "value": d} for d in datasets_dict.keys()]
    ),

    dcc.Slider(
        id="bar-year",
        min=0,
        max=10,
        value=0,
        step=1
    ),

    dcc.Graph(id="bar-graph")
])

# =========================================================
# ROUTING
# =========================================================
app.layout = html.Div([
    dcc.Location(id="url"),
    html.Div(id="page-content")
])

@app.callback(Output("page-content", "children"),
              Input("url", "pathname"))
def display_page(path):
    if path == "/line":
        return line_layout
    elif path == "/scatter":
        return scatter_layout
    elif path == "/bar":
        return bar_layout
    return home_layout

# =========================================================
# LINE CHART CALLBACK (simplified version)
# =========================================================
@app.callback(
    Output("dataset-dropdown", "options"),
    Output("dataset-dropdown", "value"),
    Input("type-dropdown", "value")
)
def update_ds(t):
    ds = dataset_types[t]
    return [{"label": x, "value": x} for x in ds], ds[:1]

@app.callback(
    Output("country-dropdown", "options"),
    Output("country-dropdown", "value"),
    Input("dataset-dropdown", "value")
)
def update_country(ds):
    if not ds:
        return [], ["Italy"]

    countries = set()
    for d in ds:
        df = get_dataset(d)
        countries.update(df["Country Name"].astype(str).unique())

    countries = sorted(list(countries))
    return [{"label": c, "value": c} for c in countries], countries[:1]

@app.callback(
    Output("line-chart", "figure"),
    Input("dataset-dropdown", "value"),
    Input("country-dropdown", "value")
)
def line(ds_list, countries):

    fig = go.Figure()
    if not ds_list or not countries:
        return fig

    for ds in ds_list:
        df = get_dataset(ds)
        years = df.columns[1:]

        for c in countries:
            row = df[df["Country Name"] == c]
            if row.empty:
                continue

            fig.add_trace(go.Scatter(
                x=years,
                y=row.iloc[0, 1:],
                name=f"{c}-{ds}"
            ))

    return fig

# =========================================================
# SCATTER (basic structure)
# =========================================================
@app.callback(
    Output("scatter-graph", "figure"),
    Input("scatter-datasets", "value"),
    Input("scatter-countries", "value"),
    Input("scatter-year", "value")
)
def scatter(ds, countries, year_idx):

    fig = go.Figure()
    if not ds or len(ds) < 2 or not countries:
        return fig

    d1 = get_dataset(ds[0])
    d2 = get_dataset(ds[1])
    years = d1.columns[1:]

    year = years[year_idx]

    for c in countries:
        v1 = d1[d1["Country Name"] == c][year].values
        v2 = d2[d2["Country Name"] == c][year].values

        if len(v1) and len(v2):
            fig.add_trace(go.Scatter(
                x=[v1[0]],
                y=[v2[0]],
                mode="markers+text",
                text=[c],
                name=c
            ))

    return fig

# =========================================================
# BAR CHART
# =========================================================
@app.callback(
    Output("bar-graph", "figure"),
    Input("bar-dataset", "value"),
    Input("bar-year", "value")
)
def bar(ds, year_idx):

    fig = go.Figure()
    if not ds:
        return fig

    df = get_dataset(ds)
    year = df.columns[1:][year_idx]

    values = df[["Country Name", year]].dropna()
    values = values.sort_values(year, ascending=False)

    fig.add_trace(go.Bar(
        x=values["Country Name"],
        y=values[year]
    ))

    return fig

# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
