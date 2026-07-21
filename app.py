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
# STACKED PRESETS
# =========================================================

STACK_PRESETS = {

    "Government Expenditure": [
        "General public services_percGDP",
        "Defence_percGDP",
        "Public order and safety_percGDP",
        "Economic affairs_percGDP",
        "Environmental protection_percGDP",
        "Housing and community amenities_percGDP",
        "Health_percGDP",
        "Recreation, culture and religion_percGDP",
        "Education_percGDP",
        "Social protection_percGDP",
        "Interest Payments on Debt_percGDP",
        "Public Pension Spending_percGDP"
    ],

    "Tax Revenue": [
        "Taxes on income, profits and capital gains_percGDP",
        "Taxes on payroll and workforce_percGDP",
        "Taxes on property_percGDP",
        "Taxes on goods and services_percGDP",
        "Taxes on international trade_percGDP",
        "Other taxes_percGDP",
        "Social security contributions_percGDP"
    ]

}


MASKS = ["Grouped", "Standard", "Detailed"]

dataset_types = {
    "Nominal": [
        ds for ds in datasets_dict
        if ("REAL" not in ds)
        and ("1990" not in ds)
        and ("2024" not in ds)
    ],

    "Real 2024": [
        ds for ds in datasets_dict
        if "2024" in ds
    ],

    "YoY % Change": sorted(datasets_dict.keys())
}

for k in dataset_types:
    dataset_types[k] = sorted(dataset_types[k])

eu28 = [
    "Austria","Belgium","Bulgaria","Cyprus","Czechia","Germany","Denmark",
    "Spain","Estonia","Finland","France","Greece","Croatia","Hungary",
    "Ireland","Italy","Lithuania","Luxembourg","Latvia","Malta",
    "Netherlands","Poland","Portugal","Romania","Slovakia",
    "Slovenia","Sweden","United Kingdom"
]

eu27 = eu28[:-1]

subnational_names = [
    # India
    "Andaman and Nicobar Islands","Andhra Pradesh","Arunachal Pradesh","Assam","Bihar",
    "Chandigarh","Chhattisgarh","Delhi","Goa","Gujarat","Haryana","Himachal Pradesh",
    "Jammu and Kashmir","Jharkhand","Karnataka","Kerala","Madhya Pradesh","Maharashtra",
    "Manipur","Meghalaya","Mizoram","Nagaland","Odisha","Puducherry","Punjab","Rajasthan",
    "Sikkim","Tamil Nadu","Telangana","Tripura","Uttar Pradesh","Uttarakhand","West Bengal",

    # China
    "Anhui","Beijing","Chongqing","Fujian","Gansu","Guangdong","Guangxi","Guizhou",
    "Hainan","Hebei","Heilongjiang","Henan","Hubei","Hunan","Inner Mongolia",
    "Jiangsu","Jiangxi","Jilin","Liaoning","Ningxia","Qinghai","Shaanxi",
    "Shandong","Shanghai","Shanxi","Sichuan","Tianjin","Tibet","Xinjiang",
    "Yunnan","Zhejiang",

    # Canada
    "Alberta","British Columbia","Manitoba","New Brunswick",
    "Newfoundland and Labrador","Northwest Territories","Nova Scotia",
    "Nunavut","Ontario","Prince Edward Island","Quebec",
    "Saskatchewan","Yukon",

    # USA
    "Alabama","Alaska","Arizona","Arkansas","California","Colorado",
    "Connecticut","Delaware","District of Columbia","Florida","Georgia",
    "Hawaii","Idaho","Illinois","Indiana","Iowa","Kansas","Kentucky",
    "Louisiana","Maine","Maryland","Massachusetts","Michigan",
    "Minnesota","Mississippi","Missouri","Montana","Nebraska",
    "Nevada","New Hampshire","New Jersey","New Mexico","New York",
    "North Carolina","North Dakota","Ohio","Oklahoma","Oregon",
    "Pennsylvania","Rhode Island","South Carolina","South Dakota",
    "Tennessee","Texas","Utah","Vermont","Virginia","Washington",
    "West Virginia","Wisconsin","Wyoming"
]

US_STATES = set(subnational_names[-50:])
CANADA_PROVINCES = set(subnational_names[-63:-50])
CHINA_PROVINCES = set(subnational_names[33:64])
INDIA_STATES = set(subnational_names[:33])


def mask_grouped(df, year):

    df = df.copy()

    cols = df.columns.drop("Country Name")

    df.loc[df["Country Name"].isin(subnational_names), cols] = np.nan
    df.loc[df["Country Name"].isin(eu27), cols] = np.nan

    if int(year) <= 2018:

        df.loc[df["Country Name"] == "United Kingdom", cols] = np.nan
        df.loc[df["Country Name"] == "EU27", cols] = np.nan

    else:

        df.loc[df["Country Name"] == "EU28", cols] = np.nan

    return df


def mask_standard(df, year):

    df = df.copy()

    cols = df.columns.drop("Country Name")

    df.loc[df["Country Name"].isin(["EU27","EU28"]), cols] = np.nan

    df.loc[df["Country Name"].isin(subnational_names), cols] = np.nan

    return df


def mask_detailed(df, year):

    df = df.copy()

    cols = df.columns.drop("Country Name")

    df.loc[df["Country Name"].isin(["EU27","EU28"]), cols] = np.nan

    for country in [
        "United States",
        "China",
        "Canada",
        "India"
    ]:

        df.loc[df["Country Name"] == country, cols] = np.nan

    return df


def apply_mask(df, mask_name, year):

    if mask_name == "Grouped":
        return mask_grouped(df, year)

    if mask_name == "Standard":
        return mask_standard(df, year)

    if mask_name == "Detailed":
        return mask_detailed(df, year)

    return df

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

        html.Div([
            html.H3("🌍 Global Map"),
            html.P("Visualize indicators geographically."),
            dcc.Link("Open Map →", href="/map")
        ], className="card"),

        html.Div([
            html.H3("🟦 Composition"),
            html.P("Stacked area charts for expenditure, taxes and custom datasets."),
            dcc.Link("Open Composition →", href="/stack")
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
# MAP PAGE
# =========================================================

map_page = html.Div(

    style={
        "backgroundColor": "#f4f6f9",
        "padding": "20px",
        "fontFamily": "Arial"
    },

    children=[

        html.Div([
            dcc.Link("← Back to Home", href="/")
        ], style={"paddingBottom": "15px"}),

        html.H2(
            "Global Indicator Map",
            style={
                "textAlign": "center",
                "color": "#1f3b5c",
                "marginBottom": "25px"
            }
        ),

        html.Div(

            style={
                "display": "flex",
                "gap": "20px",
                "marginBottom": "20px",
                "flexWrap": "wrap"
            },

            children=[

                html.Div([

                    html.Label("Dataset"),

                    dcc.Dropdown(
                        id="map-dataset"
                    )

                ], style={"flex": "2"}),

                html.Div([

                    html.Label("Year"),

                    dcc.Dropdown(
                        id="map-year"
                    )

                ], style={"width": "150px"})

            ]

        ),

        dcc.Graph(
            id="map-graph",
            style={"height": "80vh"}
        )

    ]
)


# =========================================================
# STACK PAGE
# =========================================================

stack_page = html.Div([

    html.Div([
        dcc.Link("← Back to Home", href="/")
    ]),

    html.H2("Composition Explorer"),

    html.Div([

        dcc.Dropdown(
            id="stack-country",
            placeholder="Country"
        ),

        dcc.Dropdown(
            id="stack-preset",
            options=[
                {"label":k,"value":k}
                for k in STACK_PRESETS
            ],
            value="Government Expenditure"
        ),

        dcc.Dropdown(
            id="stack-extra",
            options=dataset_options,
            multi=True,
            placeholder="Extra datasets (optional)"
        ),

        dcc.Dropdown(
            id="stack-value",
            options=[
                {"label":"Current","value":"_curr"},
                {"label":"Per Capita","value":"_curr_pc"},
                {"label":"% GDP","value":"_percGDP"}
            ],
            value="_percGDP"
        )

    ],
    style={
        "display":"grid",
        "gridTemplateColumns":"repeat(4,1fr)",
        "gap":"15px"
    }),

    dcc.Graph(
        id="stack-chart",
        style={"height":"80vh"}
    )

])

# =========================================================
# BAR PAGE
# =========================================================

bar = html.Div(

    style={
        "backgroundColor": "#f4f6f9",
        "padding": "20px",
        "fontFamily": "Arial"
    },

    children=[

        html.Div([
            dcc.Link("← Back to Home", href="/")
        ], style={"paddingBottom": "15px"}),

        html.H2(
            "Country Rankings",
            style={
                "textAlign": "center",
                "color": "#1f3b5c",
                "marginBottom": "25px"
            }
        ),

        html.Div(

            style={
                "display": "flex",
                "gap": "15px",
                "flexWrap": "wrap",
                "alignItems": "flex-end",
                "marginBottom": "25px"
            },

            children=[

                html.Div([
                    html.Label("Dataset Type"),

                    dcc.Dropdown(
                        id="type-dropdown",
                        options=[
                            {"label": k, "value": k}
                            for k in dataset_types
                        ],
                        value="Nominal",
                        clearable=False
                    )

                ], style={"width": "180px"}),

                html.Div([

                    html.Label("Dataset"),

                    dcc.Dropdown(
                        id="dataset-dropdown"
                    )

                ], style={"flex": "2"}),

                html.Div([

                    html.Label("Year"),

                    dcc.Dropdown(
                        id="year-dropdown"
                    )

                ], style={"width": "120px"}),

                html.Div([

                    html.Label("Mask"),

                    dcc.Dropdown(
                        id="mask-dropdown",
                        options=[
                            {"label": m, "value": m}
                            for m in MASKS
                        ],
                        value="Grouped",
                        clearable=False
                    )

                ], style={"width": "170px"}),

                html.Div([

                    html.Label("Top / Bottom"),

                    dcc.Input(
                        id="top-x",
                        type="number",
                        value=10,
                        min=1,
                        step=1,
                        style={"width": "70px"}
                    ),

                    dcc.RadioItems(
                        id="top-bottom",
                        options=[
                            {"label": "Top", "value": "top"},
                            {"label": "Bottom", "value": "bottom"}
                        ],
                        value="top",
                        inline=True
                    )

                ], style={"width": "220px"})
            ]
        ),

        dcc.Graph(
            id="bar-graph",
            style={
                "height": "700px",
                "backgroundColor": "white",
                "borderRadius": "10px"
            }
        )
    ]
)

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
    if p == "/map":
        return map_page
    if p == "/stack":
        return stack_page
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

@app.callback(
    Output("dataset-dropdown", "options"),
    Output("dataset-dropdown", "value"),
    Input("type-dropdown", "value")
)
def update_dataset_dropdown(selected_type):

    datasets = dataset_types[selected_type]

    options = [
        {"label": d, "value": d}
        for d in datasets
    ]

    default_map = {
        "Nominal": "GDPCAP_COM_NOMINAL",
        "Real 2024": "REALGDPCAP_COM_2024",
        "YoY % Change": "GDPCAP_COM_NOMINAL"
    }

    default_value = default_map.get(selected_type)

    if default_value in datasets:
        value = default_value
    elif datasets:
        value = datasets[0]
    else:
        value = None

    return options, value

@app.callback(
    Output("year-dropdown", "options"),
    Output("year-dropdown", "value"),
    Input("dataset-dropdown", "value")
)
def update_year_dropdown(dataset_name):

    if dataset_name is None:
        return [], None

    df = get_dataset(dataset_name)

    if df is None:
        return [], None

    year_cols = sorted(
        [c for c in df.columns if c != "Country Name"],
        key=int
    )

    options = [
        {"label": y, "value": y}
        for y in year_cols
    ]

    return options, year_cols[-1]


# =========================================================
# BAR
# =========================================================
@app.callback(
    Output("bar-graph", "figure"),
    Input("dataset-dropdown", "value"),
    Input("mask-dropdown", "value"),
    Input("top-x", "value"),
    Input("top-bottom", "value"),
    Input("year-dropdown", "value"),
    Input("type-dropdown", "value")
)
def update_chart(
    dataset_name,
    mask_name,
    top_x,
    top_bottom,
    selected_year,
    selected_type
):

    if dataset_name is None:
        return go.Figure()

    top_x = top_x or 10

    df = get_dataset(dataset_name).copy()

    year_cols = sorted(
        [c for c in df.columns if c != "Country Name"],
        key=int
    )

    year = (
        selected_year
        if selected_year in year_cols
        else year_cols[-1]
    )

    # -----------------------------
    # YoY Transformation
    # -----------------------------
    if selected_type == "YoY % Change":

        df = (
            df.set_index("Country Name")
              .pct_change(axis=1)
              .mul(100)
              .reset_index()
        )

    # -----------------------------
    # Apply Mask
    # -----------------------------
    df = apply_mask(df, mask_name, year)

    # -----------------------------
    # Keep selected year
    # -----------------------------
    df = df[["Country Name", year]].copy()

    df = df.dropna(subset=[year])

    ascending = (top_bottom == "bottom")

    df = (
        df.sort_values(year, ascending=ascending)
          .head(top_x)
    )

    # Largest displayed at the top
    df = df.iloc[::-1]

    if selected_type == "YoY % Change":
        labels = [f"{v:,.1f}%" for v in df[year]]
    else:
        labels = [f"{v:,.2f}" for v in df[year]]

    colors = [
        "#2f5aa6" if v >= 0 else "#d9534f"
        for v in df[year]
    ]

    fig = go.Figure()

    fig.add_trace(

        go.Bar(

            y=df["Country Name"],
            x=df[year],

            orientation="h",

            marker=dict(
                color=colors,
                line=dict(
                    color="white",
                    width=1
                )
            ),

            text=labels,

            textposition="auto",

            hovertemplate=(
                "<b>%{y}</b><br>"
                + year
                + ": %{x:,.2f}"
                + "<extra></extra>"
            )

        )

    )

    fig.update_layout(

        template="plotly_white",

        title=dict(
            text=f"{dataset_name} ({mask_name}) - {selected_type}",
            x=0.5
        ),

        height=max(650, top_x * 40),

        xaxis_title=year,

        yaxis_title="",

        margin=dict(
            l=180,
            r=40,
            t=70,
            b=40
        ),

        bargap=0.25

    )

    return fig

@app.callback(
    Output("map-dataset","options"),
    Output("map-dataset","value"),
    Input("url","pathname")
)
def map_dataset(_):

    options = [
        {"label":k,"value":k}
        for k in sorted(datasets_dict.keys())
    ]

    default = (
        "GDP_COM_NOMINAL"
        if "GDP_COM_NOMINAL" in datasets_dict
        else options[0]["value"]
    )

    return options, default

@app.callback(
    Output("map-year","options"),
    Output("map-year","value"),
    Input("map-dataset","value")
)
def map_years(ds):

    if ds is None:
        return [],None

    df = get_dataset(ds)

    years = sorted(
        [c for c in df.columns if c!="Country Name"],
        key=int
    )

    return (
        [{"label":y,"value":y} for y in years],
        years[-1]
    )

@app.callback(
    Output("map-graph","figure"),
    Input("map-dataset","value"),
    Input("map-year","value")
)
def update_map(ds,year):

    if ds is None or year is None:
        return go.Figure()

    df = get_dataset(ds)

    df = df[["Country Name",year]].dropna()

    fig = px.choropleth(

        df,

        locations="Country Name",

        locationmode="country names",

        color=year,

        color_continuous_scale="Viridis",

        projection="natural earth",

        hover_name="Country Name",

        hover_data={
            year:":,.2f"
        }

    )

    fig.update_layout(

        template="plotly_white",

        title={
            "text":f"{ds} ({year})",
            "x":0.5
        },

        geo=dict(
            showframe=False,
            showcoastlines=True,
            coastlinecolor="gray",
            projection_type="natural earth",
            bgcolor="rgba(0,0,0,0)"
        ),

        margin=dict(
            l=0,
            r=0,
            t=60,
            b=0
        ),

        coloraxis_colorbar=dict(
            title=ds
        )

    )

    return fig


@app.callback(
    Output("stack-chart", "figure"),
    Input("stack-country", "value"),
    Input("stack-preset", "value"),
    Input("stack-extra", "value"),
    Input("stack-value", "value")
)
def update_stack(country, preset, extra, value_suffix):

    fig = go.Figure()

    if country is None:
        return fig

    datasets = []

    # ------------------------------------
    # Preset datasets
    # ------------------------------------
    for ds in STACK_PRESETS[preset]:

        name = ds.replace("_percGDP", value_suffix)

        if name in datasets_dict:
            datasets.append(name)

    # ------------------------------------
    # Additional datasets selected manually
    # ------------------------------------
    if extra:

        for ds in extra:

            if ds not in datasets:
                datasets.append(ds)

    colors = px.colors.qualitative.Set3

    # ------------------------------------
    # Plot
    # ------------------------------------
    for i, ds in enumerate(datasets):

        df = get_dataset(ds)

        if df is None:
            continue

        row = df[df["Country Name"] == country]

        if row.empty:
            continue

        years = []
        values = []

        for y in YEARS:

            if y not in row.columns:
                continue

            value = row.iloc[0][y]

            if pd.notna(value):

                years.append(int(y))
                values.append(float(value))

        fig.add_trace(

            go.Scatter(

                x=years,
                y=values,

                mode="lines",

                stackgroup="one",

                name=ds.replace(value_suffix, ""),

                line=dict(
                    width=1,
                    color=colors[i % len(colors)]
                )

            )

        )

    fig.update_layout(

        template="plotly_white",

        title=f"{preset} — {country}",

        hovermode="x unified",

        legend=dict(
            orientation="v",
            x=1.02,
            y=1
        ),

        margin=dict(
            l=50,
            r=170,
            t=70,
            b=40
        )

    )

    return fig


# =========================================================
# RUN
# =========================================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8050, debug=False)
