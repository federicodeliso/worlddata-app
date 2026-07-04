import joblib
import dash
from dash import dcc, html, Input, Output
import plotly.graph_objs as go
import numpy as np
from functools import lru_cache

# =========================================================
# DATA
# =========================================================
datasets_dict = joblib.load("datasets.joblib")

for ds, df in datasets_dict.items():
    datasets_dict[ds] = df.loc[:, ~df.columns.duplicated()]

YEARS = [str(y) for y in range(1960, 2025)]

dataset_options = [
    {"label": k, "value": k}
    for k in sorted(datasets_dict.keys())
]

# =========================================================
# CACHE
# =========================================================
@lru_cache(maxsize=50)
def get_dataset(ds):
    df = datasets_dict.get(ds)
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
# HOME
# =========================================================
home = html.Div([
    html.H1("📊 Macro Dashboard", style={"textAlign": "center"}),

    html.Div([
        dcc.Link("📈 Line Chart", href="/line"), html.Br(),
        dcc.Link("🔵 Scatter + Regression", href="/scatter"), html.Br(),
        dcc.Link("📊 Bar Ranking", href="/bar")
    ], style={"textAlign": "center", "fontSize": "20px"})
])

# =========================================================
# LINE PAGE
# =========================================================
line = html.Div([

    dcc.Link("⬅ Home", href="/"),

    html.H2("Line Chart", style={"textAlign": "center"}),

    dcc.Dropdown(
        id="line-ds",
        options=dataset_options,
        value=[dataset_options[0]["value"]],
        multi=True,
        clearable=False
    ),

    html.Br(),

    dcc.Dropdown(
        id="line-country",
        placeholder="Select a country"
    ),

    dcc.Graph(id="line-chart", style={"height": "75vh"})
])

# =========================================================
# SCATTER PAGE
# =========================================================
scatter = html.Div([

    dcc.Link("⬅ Home", href="/"),

    html.H2("Scatter + Regression"),

    dcc.Dropdown(
        id="scatter-ds",
        options=dataset_options,
        multi=True
    ),

    dcc.Dropdown(id="scatter-country", multi=True),

    dcc.Slider(
        id="scatter-year",
        min=1960,
        max=2024,
        value=2000,
        marks={1960: "1960", 1980: "1980", 2000: "2000", 2024: "2024"}
    ),

    dcc.Graph(id="scatter-graph", style={"height": "70vh"})
])

# =========================================================
# BAR PAGE
# =========================================================
bar = html.Div([

    dcc.Link("⬅ Home", href="/"),

    html.H2("Bar Ranking"),

    dcc.Dropdown(
        id="bar-ds",
        options=dataset_options,
        value=dataset_options[0]["value"]
    ),

    dcc.Slider(
        id="bar-year",
        min=1960,
        max=2024,
        value=2000,
        marks={1960: "1960", 1980: "1980", 2000: "2000", 2024: "2024"}
    ),

    html.Br(),

    dcc.RadioItems(
        id="bar-mode",
        options=[
            {"label": "Top", "value": "top"},
            {"label": "Bottom", "value": "bottom"}
        ],
        value="top",
        inline=True
    ),

    dcc.Slider(
        id="bar-count",
        min=5,
        max=30,
        step=5,
        value=10,
        marks={5: "5", 10: "10", 20: "20", 30: "30"}
    ),

    dcc.Graph(id="bar-graph", style={"height": "70vh"})
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
def router(p):
    if p == "/line":
        return line
    if p == "/scatter":
        return scatter
    if p == "/bar":
        return bar
    return home

# =========================================================
# LINE COUNTRY LOADER
# =========================================================
@app.callback(
    Output("line-country", "options"),
    Output("line-country", "value"),
    Input("line-ds", "value")
)
def update_country(ds):

    if not ds:
        return [], None

    df = get_dataset(ds[0])

    countries = sorted(df["Country Name"].dropna().unique())

    return (
        [{"label": c, "value": c} for c in countries],
        countries[0]
    )

# =========================================================
# LINE GRAPH
# =========================================================
@app.callback(
    Output("line-chart", "figure"),
    Input("line-ds", "value"),
    Input("line-country", "value")
)
def line_fn(datasets, country):

    fig = go.Figure()

    if not datasets or not country:
        fig.update_layout(template="plotly_white")
        return fig

    colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
        "#bcbd22", "#17becf"
    ]

    for i, ds in enumerate(datasets):

        df = get_dataset(ds)
        row = df[df["Country Name"] == country]

        if row.empty:
            continue

        years = []
        values = []

        for y in YEARS:
            if y in row.columns:
                v = row.iloc[0][y]
                if v is not None and str(v) != "nan":
                    years.append(int(y))
                    values.append(float(v))

        fig.add_trace(
            go.Scatter(
                x=years,
                y=values,
                mode="lines+markers",
                name=ds,
                line=dict(
                    width=3,
                    shape="spline",
                    smoothing=0.5,
                    color=colors[i % len(colors)]
                ),
                marker=dict(size=6),
                hovertemplate="<b>%{fullData.name}</b><br>Year: %{x}<br>Value: %{y:,.2f}<extra></extra>"
            )
        )

    fig.update_layout(
        title=f"{country}",
        template="plotly_white",
        height=650,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=1.1,
            x=0.5,
            xanchor="center"
        ),
        xaxis=dict(
            title="Year",
            rangeslider=dict(visible=True),
            showgrid=True
        ),
        yaxis=dict(
            title="Value",
            showgrid=True,
            zeroline=False
        ),
        margin=dict(l=50, r=30, t=80, b=50)
    )

    return fig

# =========================================================
# SCATTER COUNTRY OPTIONS
# =========================================================
@app.callback(
    Output("scatter-country", "options"),
    Output("scatter-country", "value"),
    Input("scatter-ds", "value")
)
def sc_countries(ds):
    if not ds:
        return [], []
    df = get_dataset(ds[0])
    c = sorted(df["Country Name"].unique())
    return [{"label": x, "value": x} for x in c], c[:3]

# =========================================================
# SCATTER GRAPH
# =========================================================
@app.callback(
    Output("scatter-graph", "figure"),
    Input("scatter-ds", "value"),
    Input("scatter-country", "value"),
    Input("scatter-year", "value")
)
def scatter_fn(ds, countries, year):

    fig = go.Figure()

    if not ds or len(ds) < 2:
        return fig

    d1 = get_dataset(ds[0])
    d2 = get_dataset(ds[1])

    y = str(year)

    xs, ys = [], []

    for c in countries or []:
        v1 = d1[d1["Country Name"] == c][y].values
        v2 = d2[d2["Country Name"] == c][y].values

        if len(v1) and len(v2):
            xs.append(float(v1[0]))
            ys.append(float(v2[0]))

            fig.add_trace(go.Scatter(
                x=[float(v1[0])],
                y=[float(v2[0])],
                mode="markers",
                text=[c],
                hovertemplate=c
            ))

    if len(xs) > 2:
        m, b = np.polyfit(xs, ys, 1)
        x_line = np.linspace(min(xs), max(xs), 50)

        fig.add_trace(go.Scatter(
            x=x_line,
            y=m * x_line + b,
            mode="lines",
            name="Trend",
            line=dict(dash="dash")
        ))

    fig.update_layout(template="plotly_white", hovermode="closest")

    return fig

# =========================================================
# BAR GRAPH
# =========================================================
@app.callback(
    Output("bar-graph", "figure"),
    Input("bar-ds", "value"),
    Input("bar-year", "value"),
    Input("bar-mode", "value"),
    Input("bar-count", "value")
)
def bar_fn(ds, year, mode, count):

    fig = go.Figure()
    df = get_dataset(ds)
    y = str(year)

    data = df[["Country Name", y]].dropna()
    data = data.sort_values(y, ascending=(mode == "bottom")).head(count)

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
