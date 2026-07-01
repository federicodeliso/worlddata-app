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
# LINE PAGE (RESTORED BEAUTIFUL STYLE)
# =========================================================
line = html.Div([

    dcc.Link("⬅ Home", href="/"),

    html.H2("Line Chart", style={"textAlign": "center"}),

    dcc.Dropdown(
        id="line-ds",
        options=[{"label": k, "value": k} for k in datasets_dict.keys()],
        value=list(datasets_dict.keys())[0],
        clearable=False
    ),

    dcc.Dropdown(id="line-country", multi=True),

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
        options=[{"label": k, "value": k} for k in datasets_dict.keys()],
        multi=True
    ),

    dcc.Dropdown(id="scatter-country", multi=True),

    dcc.Slider(
        id="scatter-year",
        min=1960,
        max=2024,
        value=2000,
        marks={1960:"1960", 1980:"1980", 2000:"2000", 2024:"2024"}
    ),

    dcc.Graph(id="scatter-graph", style={"height": "70vh"})
])

# =========================================================
# BAR PAGE (TOP/BOTTOM + COUNT)
# =========================================================
bar = html.Div([

    dcc.Link("⬅ Home", href="/"),

    html.H2("Bar Ranking"),

    dcc.Dropdown(
        id="bar-ds",
        options=[{"label": k, "value": k} for k in datasets_dict.keys()],
        value=list(datasets_dict.keys())[0]
    ),

    html.Div([
        dcc.Slider(
            id="bar-year",
            min=1960,
            max=2024,
            value=2000,
            marks={1960:"1960", 1980:"1980", 2000:"2000", 2024:"2024"}
        )
    ]),

    html.Div([
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
            marks={5:"5", 10:"10", 20:"20", 30:"30"}
        )
    ]),

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
# LINE (RESTORED BEAUTY)
# =========================================================
@app.callback(
    Output("line-country", "options"),
    Output("line-country", "value"),
    Input("line-ds", "value")
)
def line_countries(ds):
    df = get_dataset(ds)
    c = df["Country Name"].astype(str).unique()
    return [{"label":x,"value":x} for x in c], list(c[:1])

@app.callback(
    Output("line-chart", "figure"),
    Input("line-ds", "value"),
    Input("line-country", "value")
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
        height=750,
        margin=dict(l=20,r=20,t=40,b=20),
        legend=dict(orientation="h", y=1.05)
    )

    return fig

# =========================================================
# SCATTER + REGRESSION LINE
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
    c = df["Country Name"].unique()
    return [{"label":x,"value":x} for x in c], list(c[:3])

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

    xs = []
    ys = []

    for c in countries or []:
        v1 = d1[d1["Country Name"] == c][y].values
        v2 = d2[d2["Country Name"] == c][y].values

        if len(v1) and len(v2):
            x = float(v1[0])
            yv = float(v2[0])

            xs.append(x)
            ys.append(yv)

            fig.add_trace(go.Scatter(
                x=[x],
                y=[yv],
                mode="markers",
                text=[c],
                hovertemplate=c
            ))

    # regression line
    if len(xs) > 2:
        m, b = np.polyfit(xs, ys, 1)
        x_line = np.linspace(min(xs), max(xs), 50)
        y_line = m * x_line + b

        fig.add_trace(go.Scatter(
            x=x_line,
            y=y_line,
            mode="lines",
            name="Trend",
            line=dict(dash="dash")
        ))

    fig.update_layout(
        template="plotly_white",
        hovermode="closest"
    )

    return fig

# =========================================================
# BAR (TOP/BOTTOM + COUNT)
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

    data = data.sort_values(y, ascending=(mode == "bottom"))

    data = data.head(count)

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
