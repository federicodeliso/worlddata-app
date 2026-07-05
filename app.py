import joblib
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
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
# HOME (PROFESSIONAL DASHBOARD STYLE)
# =========================================================
home = html.Div([

    html.Div([
        html.H1("Macro Data Analytics Dashboard",
                style={"marginBottom": "5px"}),

        html.P(
            "Explore global indicators across countries and time using interactive visual analytics.",
            style={"color": "#666", "fontSize": "16px"}
        )
    ], style={"textAlign": "center", "padding": "40px 20px"}),

    html.Div([

        html.Div([
            html.H3("📈 Trend Analysis"),
            html.P("Compare multiple indicators across countries over time."),
            dcc.Link("Open Line Chart →", href="/line")
        ], className="card"),

        html.Div([
            html.H3("🔵 Correlation Explorer"),
            html.P("Analyze relationships between economic indicators."),
            dcc.Link("Open Scatter Plot →", href="/scatter")
        ], className="card"),

        html.Div([
            html.H3("📊 Rankings"),
            html.P("View top and bottom countries by indicator."),
            dcc.Link("Open Bar Charts →", href="/bar")
        ], className="card"),

    ], style={
        "display": "grid",
        "gridTemplateColumns": "repeat(auto-fit, minmax(250px, 1fr))",
        "gap": "20px",
        "padding": "0 40px 60px"
    })

])


# =========================================================
# LINE PAGE
# =========================================================
line = html.Div([

    html.Div([
        dcc.Link("← Back to Home", href="/")
    ], style={"padding": "10px"}),

    html.H2("Multi-Country & Multi-Dataset Trends",
            style={"textAlign": "center"}),

    html.Div([
        dcc.Dropdown(
            id="line-ds",
            options=dataset_options,
            value=[dataset_options[0]["value"]],
            multi=True,
            placeholder="Select datasets"
        ),

        dcc.Dropdown(
            id="line-country",
            multi=True,
            placeholder="Select countries"
        ),
    ], style={"maxWidth": "900px", "margin": "0 auto"}),

    dcc.Graph(id="line-chart", style={"height": "75vh"})

])


# =========================================================
# SCATTER PAGE
# =========================================================
scatter = html.Div([

    html.Div([dcc.Link("← Back to Home", href="/")], style={"padding": "10px"}),

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

    html.Div([dcc.Link("← Back to Home", href="/")], style={"padding": "10px"}),

    html.H2("Country Rankings"),

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
        value=10
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
# LINE COUNTRY OPTIONS
# =========================================================
@app.callback(
    Output("line-country", "options"),
    Output("line-country", "value"),
    Input("line-ds", "value"),
    State("line-country", "value")
)
def update_countries(datasets, selected):

    if not datasets:
        return [], []

    df = get_dataset(datasets[0])

    countries = sorted(df["Country Name"].dropna().unique())

    options = [{"label": c, "value": c} for c in countries]

    # Keep previously selected countries if they still exist
    if selected:
        keep = [c for c in selected if c in countries]
        if keep:
            return options, keep

    # Default selection: Italy
    if "Italy" in countries:
        return options, ["Italy"]

    # Fallback
    if countries:
        return options, [countries[0]]

    return options, []


# =========================================================
# LINE CHART (FINAL VERSION)
# =========================================================
@app.callback(
    Output("line-chart", "figure"),
    Input("line-ds", "value"),
    Input("line-country", "value")
)
def line_fn(datasets, countries):

    fig = go.Figure()

    if not datasets or not countries:
        fig.update_layout(template="plotly_white")
        return fig

    colors = px.colors.qualitative.Set2

    i = 0

    for ds in datasets:
        df = get_dataset(ds)

        for c in countries:

            row = df[df["Country Name"] == c]
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
                    mode="lines",
                    name=f"{ds} — {c}",
                    line=dict(
                        width=2,
                        shape="spline",
                        smoothing=0.5,
                        color=colors[i % len(colors)]
                    )
                )
            )

            i += 1

    fig.update_layout(
        template="plotly_white",
        height=700,
        hovermode="x unified",
        legend=dict(
            orientation="h",
            y=1.1,
            x=0.5,
            xanchor="center"
        ),
        margin=dict(l=50, r=30, t=80, b=50)
    )

    return fig


# =========================================================
# SCATTER OPTIONS
# =========================================================
@app.callback(
    Output("scatter-country", "options"),
    Output("scatter-country", "value"),
    Input("scatter-ds", "value")
)
def scatter_countries(ds):

    if not ds:
        return [], []

    df = get_dataset(ds[0])
    c = sorted(df["Country Name"].dropna().unique())

    return [{"label": x, "value": x} for x in c], c[:3]


# =========================================================
# SCATTER
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

    fig.update_layout(template="plotly_white")

    return fig


# =========================================================
# BAR
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
