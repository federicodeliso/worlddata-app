import joblib
import dash
from dash import dcc, html, Input, Output
import plotly.graph_objs as go
from functools import lru_cache

# =========================================================
# LOAD DATA
# =========================================================
datasets_dict = joblib.load("datasets.joblib")

for ds, df in datasets_dict.items():
    datasets_dict[ds] = df.loc[:, ~df.columns.duplicated()]

# =========================================================
# YEAR RANGE (REAL FIX)
# =========================================================
YEARS = [str(y) for y in range(1960, 2025)]

# =========================================================
# CACHE
# =========================================================
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
# HOME (CLEAN)
# =========================================================
home = html.Div([
    html.H1("📊 Macro Dashboard",
            style={"textAlign": "center", "marginTop": "20px"}),

    html.Div([
        dcc.Link("📈 Line Chart", href="/line"),
        html.Br(),
        dcc.Link("🔵 Scatter", href="/scatter"),
        html.Br(),
        dcc.Link("📊 Bar Ranking", href="/bar"),
    ], style={"textAlign": "center", "fontSize": "20px"})
])

# =========================================================
# LINE PAGE (IMPROVED LOOK)
# =========================================================
line_page = html.Div([

    dcc.Link("⬅ Home", href="/"),

    html.H2("Line Chart", style={"textAlign": "center"}),

    dcc.Dropdown(
        id="ds-type",
        options=[{"label": k, "value": k} for k in datasets_dict.keys()],
        value=list(datasets_dict.keys())[0],
        clearable=False
    ),

    dcc.Dropdown(id="country", multi=True),

    dcc.Graph(
        id="line",
        style={"height": "75vh"}
    )
])

# =========================================================
# SCATTER PAGE
# =========================================================
scatter_page = html.Div([

    dcc.Link("⬅ Home", href="/"),
    html.H2("Scatter Comparison"),

    dcc.Dropdown(
        id="scatter-ds",
        options=[{"label": k, "value": k} for k in datasets_dict.keys()],
        multi=True
    ),

    dcc.Dropdown(id="scatter-country", multi=True),

    dcc.Slider(
        id="year-slider",
        min=1960,
        max=2024,
        value=2000,
        marks={y: str(y) for y in range(1960, 2025, 10)}
    ),

    dcc.Graph(id="scatter", style={"height": "70vh"})
])

# =========================================================
# BAR PAGE
# =========================================================
bar_page = html.Div([

    dcc.Link("⬅ Home", href="/"),

    html.H2("Bar Ranking"),

    dcc.Dropdown(
        id="bar-ds",
        options=[{"label": k, "value": k} for k in datasets_dict.keys()],
        value=list(datasets_dict.keys())[0]
    ),

    dcc.Slider(
        id="bar-year",
        min=1960,
        max=2024,
        value=2000,
        marks={y: str(y) for y in range(1960, 2025, 10)}
    ),

    dcc.Graph(id="bar", style={"height": "70vh"})
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
        return line_page
    if path == "/scatter":
        return scatter_page
    if path == "/bar":
        return bar_page
    return home

# =========================================================
# LINE (FIXED COUNTRY LINK)
# =========================================================
@app.callback(
    Output("country", "options"),
    Output("country", "value"),
    Input("ds-type", "value")
)
def load_countries(ds):
    df = get_dataset(ds)
    countries = df["Country Name"].dropna().astype(str).unique()
    return [{"label": c, "value": c} for c in countries], [countries[0]] if len(countries) else []

@app.callback(
    Output("line", "figure"),
    Input("ds-type", "value"),
    Input("country", "value")
)
def line_chart(ds, countries):

    fig = go.Figure()
    df = get_dataset(ds)

    for c in countries or []:
        row = df[df["Country Name"] == c]

        if row.empty:
            continue

        fig.add_trace(go.Scatter(
            x=YEARS,
            y=row.iloc[0][YEARS],
            mode="lines",
            name=c
        ))

    fig.update_layout(
        template="plotly_white",
        height=700,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", y=1.1)
    )

    return fig

# =========================================================
# SCATTER (REAL DATA LINK)
# =========================================================
@app.callback(
    Output("scatter-country", "options"),
    Output("scatter-country", "value"),
    Input("scatter-ds", "value")
)
def scatter_countries(ds_list):

    if not ds_list:
        return [], []

    df = get_dataset(ds_list[0])
    countries = df["Country Name"].dropna().unique()

    return [{"label": c, "value": c} for c in countries], list(countries[:3])

@app.callback(
    Output("scatter", "figure"),
    Input("scatter-ds", "value"),
    Input("scatter-country", "value"),
    Input("year-slider", "value")
)
def scatter(ds_list, countries, year):

    fig = go.Figure()

    if not ds_list or len(ds_list) < 2:
        return fig

    y = str(year)

    d1 = get_dataset(ds_list[0])
    d2 = get_dataset(ds_list[1])

    for c in countries or []:
        v1 = d1[d1["Country Name"] == c][y].values
        v2 = d2[d2["Country Name"] == c][y].values

        if len(v1) and len(v2):
            fig.add_trace(go.Scatter(
                x=[v1[0]],
                y=[v2[0]],
                mode="markers+text",
                text=[c]
            ))

    fig.update_layout(template="plotly_white")

    return fig

# =========================================================
# BAR (REAL CONNECTION)
# =========================================================
@app.callback(
    Output("bar", "figure"),
    Input("bar-ds", "value"),
    Input("bar-year", "value")
)
def bar(ds, year):

    fig = go.Figure()

    df = get_dataset(ds)
    y = str(year)

    if y not in df.columns:
        return fig

    data = df[["Country Name", y]].dropna()
    data = data.sort_values(y, ascending=False).head(15)

    fig.add_trace(go.Bar(
        x=data["Country Name"],
        y=data[y]
    ))

    fig.update_layout(template="plotly_white")

    return fig

# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
