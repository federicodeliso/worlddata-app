import joblib
import dash
from dash import dcc, html, Input, Output
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
# HOME (NEW PRETTY UI)
# =========================================================
home_layout = html.Div([

    html.Div([
        html.H1("📊 Macro Analytics Dashboard",
                style={"textAlign": "center", "color": "#2c3e50"}),

        html.P("Select a module below",
               style={"textAlign": "center", "color": "#7f8c8d"})
    ]),

    html.Div([

        dcc.Link(
            html.Div([
                html.H3("📈 Line Chart"),
                html.P("Trends over time by country & dataset")
            ], style={
                "padding": "20px",
                "margin": "10px",
                "borderRadius": "12px",
                "backgroundColor": "#ecf0f1",
                "textAlign": "center"
            }),
            href="/line"
        ),

        dcc.Link(
            html.Div([
                html.H3("🔵 Scatter Analysis"),
                html.P("Compare datasets across countries & time")
            ], style={
                "padding": "20px",
                "margin": "10px",
                "borderRadius": "12px",
                "backgroundColor": "#ecf0f1",
                "textAlign": "center"
            }),
            href="/scatter"
        ),

        dcc.Link(
            html.Div([
                html.H3("📊 Ranking Bar Chart"),
                html.P("Top / bottom countries comparison")
            ], style={
                "padding": "20px",
                "margin": "10px",
                "borderRadius": "12px",
                "backgroundColor": "#ecf0f1",
                "textAlign": "center"
            }),
            href="/bar"
        ),

    ], style={"maxWidth": "600px", "margin": "auto"})
])

# =========================================================
# LINE (YOUR LOGIC KEPT)
# =========================================================
line_layout = html.Div([
    dcc.Link("⬅ Home", href="/"),
    html.H2("Line Chart"),

    dcc.Dropdown(
        id="type-dropdown",
        options=[{"label": t, "value": t} for t in dataset_types.keys()],
        value="Nominal"
    ),

    dcc.Dropdown(id="dataset-dropdown", multi=True),
    dcc.Dropdown(id="country-dropdown", multi=True),

    dcc.Graph(id="line-chart")
])

# =========================================================
# SCATTER (FIXED SIMPLE)
# =========================================================
scatter_layout = html.Div([
    dcc.Link("⬅ Home", href="/"),
    html.H2("Scatter Analysis"),

    dcc.Dropdown(
        id="scatter-ds",
        options=[{"label": d, "value": d} for d in datasets_dict.keys()],
        multi=True,
        placeholder="Select 2 datasets"
    ),

    dcc.Dropdown(
        id="scatter-country",
        options=[],
        multi=True
    ),

    dcc.Slider(id="scatter-year", min=0, max=10, step=1, value=0),

    dcc.Graph(id="scatter-graph")
])

# =========================================================
# BAR (FIXED CLEAN)
# =========================================================
bar_layout = html.Div([
    dcc.Link("⬅ Home", href="/"),
    html.H2("Ranking Chart"),

    dcc.Dropdown(
        id="bar-ds",
        options=[{"label": d, "value": d} for d in datasets_dict.keys()]
    ),

    dcc.Slider(id="bar-year", min=0, max=10, step=1, value=0),

    dcc.Graph(id="bar-graph")
])

# =========================================================
# ROUTING
# =========================================================
app.layout = html.Div([
    dcc.Location(id="url"),
    html.Div(id="page")
])

@app.callback(Output("page", "children"),
              Input("url", "pathname"))
def router(path):
    if path == "/line":
        return line_layout
    if path == "/scatter":
        return scatter_layout
    if path == "/bar":
        return bar_layout
    return home_layout

# =========================================================
# LINE (UNCHANGED CORE LOGIC)
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

    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1)
    )

    return fig

# =========================================================
# SCATTER FIXED
# =========================================================
@app.callback(
    Output("scatter-graph", "figure"),
    Input("scatter-ds", "value"),
    Input("scatter-country", "value"),
    Input("scatter-year", "value")
)
def scatter(ds, countries, year_idx):

    fig = go.Figure()
    if not ds or len(ds) < 2 or not countries:
        return fig

    d1 = get_dataset(ds[0])
    d2 = get_dataset(ds[1])

    years = d1.columns[1:]
    year = years[min(year_idx, len(years)-1)]

    for c in countries:
        v1 = d1[d1["Country Name"] == c][year].values
        v2 = d2[d2["Country Name"] == c][year].values

        if len(v1) and len(v2):
            fig.add_trace(go.Scatter(
                x=[v1[0]],
                y=[v2[0]],
                mode="markers+text",
                text=[c]
            ))

    return fig

# =========================================================
# BAR FIXED
# =========================================================
@app.callback(
    Output("bar-graph", "figure"),
    Input("bar-ds", "value"),
    Input("bar-year", "value")
)
def bar(ds, year_idx):

    fig = go.Figure()
    if not ds:
        return fig

    df = get_dataset(ds)
    years = df.columns[1:]
    year = years[min(year_idx, len(years)-1)]

    data = df[["Country Name", year]].dropna()
    data = data.sort_values(year, ascending=False).head(15)

    fig.add_trace(go.Bar(
        x=data["Country Name"],
        y=data[year]
    ))

    return fig

# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
