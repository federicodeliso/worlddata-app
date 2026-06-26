import joblib
import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
from functools import lru_cache

# =========================================================
# 1. LOAD DATA ONCE
# =========================================================
datasets_dict = joblib.load("/storage/emulated/0/Download/datasets.joblib")

# Clean duplicate columns once
for ds, df in datasets_dict.items():
    datasets_dict[ds] = df.loc[:, ~df.columns.duplicated()]

# =========================================================
# 2. DATASET TYPES
# =========================================================
dataset_types = {
    "Nominal": [ds for ds in datasets_dict if ("REAL" not in ds) and ("1990" not in ds) and ("2024" not in ds)],
    "Real 2024": [ds for ds in datasets_dict if "2024" in ds],
    "YoY % Change": list(datasets_dict.keys())
}

for key in dataset_types:
    dataset_types[key].sort()

# =========================================================
# 3. CACHE (IMPORTANT PERFORMANCE FIX)
# =========================================================
@lru_cache(maxsize=50)
def get_dataset(ds_name):
    df = datasets_dict.get(ds_name)
    if df is None:
        return None

    df = df.copy()

    if "Country Name" in df.columns:
        return df

    df = df.reset_index()
    df.columns = ["Country Name"] + list(df.columns[1:])
    return df

# =========================================================
# 4. APP INIT
# =========================================================
app = dash.Dash(__name__)
app.title = "Stable Mobile Dashboard"

# =========================================================
# 5. LAYOUT (MOBILE + FILTER TOGGLE)
# =========================================================
app.layout = html.Div([

    html.H2("📊 Macro Dashboard", style={"textAlign": "center"}),

    html.Button(
        "Filters ▼",
        id="toggle-filters",
        n_clicks=0,
        style={
            "width": "100%",
            "padding": "12px",
            "fontSize": "16px",
            "marginBottom": "10px"
        }
    ),

    html.Div(
        id="filters-panel",
        children=[

            html.Div([
                html.Label("Dataset Type"),
                dcc.Dropdown(
                    id="type-dropdown",
                    options=[{"label": t, "value": t} for t in dataset_types.keys()],
                    value="Nominal",
                    clearable=False
                ),
            ], style={"padding": "8px"}),

            html.Div([
                html.Label("Datasets"),
                dcc.Dropdown(
                    id="dataset-dropdown",
                    options=[],
                    value=[],
                    multi=True
                ),
            ], style={"padding": "8px"}),

            html.Div([
                html.Label("Countries"),
                dcc.Dropdown(
                    id="country-dropdown",
                    options=[],
                    value=[],
                    multi=True
                ),
            ], style={"padding": "8px"}),

        ],
        style={"display": "block"}
    ),

    dcc.Graph(
        id="line-chart",
        style={"height": "65vh"}
    )
])

# =========================================================
# 6. TOGGLE FILTERS
# =========================================================
@app.callback(
    Output("filters-panel", "style"),
    Output("toggle-filters", "children"),
    Input("toggle-filters", "n_clicks"),
    State("filters-panel", "style")
)
def toggle_filters(n, style):
    if n % 2 == 1:
        return {"display": "none"}, "Filters ▶"
    return {"display": "block"}, "Filters ▼"

# =========================================================
# 7. DATASET DROPDOWN
# =========================================================
@app.callback(
    Output("dataset-dropdown", "options"),
    Output("dataset-dropdown", "value"),
    Input("type-dropdown", "value")
)
def update_dataset_options(selected_type):

    datasets = dataset_types.get(selected_type, [])
    options = [{"label": ds, "value": ds} for ds in datasets]

    default_map = {
        "Nominal": datasets[0] if datasets else None,
        "Real 2024": datasets[0] if datasets else None,
        "YoY % Change": datasets[0] if datasets else None
    }

    default_value = default_map.get(selected_type)

    value = [default_value] if default_value else []

    return options, value

# =========================================================
# 8. COUNTRY DROPDOWN (FAST + SAFE)
# =========================================================
@app.callback(
    Output("country-dropdown", "options"),
    Output("country-dropdown", "value"),
    Input("dataset-dropdown", "value"),
    State("country-dropdown", "value")
)
def update_country_options(selected_datasets, selected_countries):

    if not selected_datasets:
        return [], ["Italy"]

    countries = set()

    for ds in selected_datasets:
        df = get_dataset(ds)
        if df is None:
            continue

        col = "Country Name"

        for c in df[col].dropna().astype(str).unique():
            countries.add(c.strip())

    countries = sorted(list(countries))

    options = [{"label": c, "value": c} for c in countries]

    if not countries:
        return [], ["Italy"]

    value = selected_countries or (["Italy"] if "Italy" in countries else [countries[0]])

    return options, value

# =========================================================
# 9. CHART (OPTIMIZED - NO HEAVY REBUILDING)
# =========================================================
@app.callback(
    Output("line-chart", "figure"),
    Input("dataset-dropdown", "value"),
    Input("country-dropdown", "value"),
    Input("type-dropdown", "value")
)
def update_line_chart(selected_datasets, selected_countries, selected_type):

    fig = go.Figure()

    if not selected_datasets or not selected_countries:
        fig.update_layout(title="Select dataset and country")
        return fig

    yaxis_title = "Value"

    for ds in selected_datasets:

        df = get_dataset(ds)
        if df is None:
            continue

        country_col = "Country Name"
        year_cols = df.columns[1:]

        for country in selected_countries:

            row = df[df[country_col] == country]
            if row.empty:
                continue

            values = row.iloc[0, 1:]

            # safe numeric conversion
            values = values.apply(
                lambda x: float(x)
                if str(x).replace('.', '', 1).replace('-', '', 1).isdigit()
                else None
            )

            if selected_type == "YoY % Change":
                values = values.pct_change() * 100
                yaxis_title = "YoY % Change (%)"

            fig.add_trace(go.Scatter(
                x=year_cols,
                y=values,
                mode="lines+markers",
                name=f"{country} - {ds}"
            ))

    fig.update_layout(
        title="Macro Time Series",
        xaxis_title="Year",
        yaxis_title=yaxis_title,
        template="plotly_white",
        hovermode="x unified",

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )

    return fig

# =========================================================
# 10. RUN APP
# =========================================================

server = app.server
