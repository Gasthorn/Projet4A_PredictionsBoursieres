from dash import html, dcc, Input, Output, callback, register_page,no_update
import plotly.graph_objects as go
import pandas as pd

register_page(__name__, path="/actions_page", name="Actions")

df_report = pd.read_csv("Data/data_report.csv")
df = pd.read_csv("Data/ALL_FEATURES.csv", parse_dates=["date"])
available_symbols = sorted(df["symbol"].unique())

def filter_period(df, period):
    """Filtre df selon la période comme yfinance."""
    days_map = {
        "1mo": 30,
        "2mo": 60,
        "3mo": 90,
        "6mo": 182,
        "9mo": 273,
        "1y": 365,
        "2y": 730,
        "3y": 1095,
        "5y": 1825,
    }
    if period not in days_map:
        return df

    cutoff = pd.Timestamp.today() - pd.Timedelta(days=days_map[period])
    return df[df["date"] >= cutoff]

# === LAYOUT ===
dropdown_options = [
    {"label": symbol, "value": symbol}
    for symbol in available_symbols
]

layout = html.Div(className="actions-page", children=[
    # Titre animé
    html.Div(className="page-title", children=[
        html.H1("Analyse d'Actifs en Temps Réel", className="glow-title"),
        html.Div(className="neon-underline")
    ]),
    # Conteneur principal
    html.Div(className="actions-container", children=[
        # === PANNEAU DE CONTRÔLE ===
        html.Div(className="control-panel", children=[
            html.H3("Sélection d'Actif", className="panel-title"),
            dcc.Dropdown(
                id='stock-dropdown',
                options=dropdown_options,
                value='AAPL',
                multi = True,
                className="lux-dropdown scrollable-dropdown"
            ),
            html.H3("Période", className="panel-title mt-20"),
            dcc.Dropdown(
                id='period-dropdown',
                options=[
                    {'label': '1 mois', 'value': '1mo'},
                    {'label': '2 mois', 'value': '2mo'},
                    {'label': '3 mois', 'value': '3mo'},
                    {'label': '6 mois', 'value': '6mo'},
                    {'label': '9 mois', 'value': '9mo'},
                    {'label': '1 an', 'value': '1y'},
                    {'label': '2 ans', 'value': '2y'},
                    {'label': '3 ans', 'value': '3y'},
                    {'label': '5 ans', 'value': '5y'},

                ],
                value='6mo',
                className="lux-dropdown scrollable-dropdown"
            )
        ]),

        # === MÉTRIQUES EN TEMPS RÉEL ===
        html.Div(className="metrics-panel", children=[
            html.H3("Métriques Live", className="panel-title"),
            dcc.Loading(html.Div(id='live-metrics', className="metrics-grid"), type="cube")
        ]),

        # === GRAPHIQUE ===
        html.Div(className="graph-panel", children=[
            html.H3("Graphique des Prix", className="panel-title"),
            dcc.Loading(dcc.Graph(id='stock-graph', className="lux-graph"), type="dot"),
            # INTERVAL UNIQUE
            dcc.Interval(id='interval-graph-update', interval=60*1000, n_intervals=0)
        ]),

        # === DONNEES AVANCEES ===
        html.Div(className="advanced-control-panel",children=[
            html.H3("Données Avancées", className="panel-title"),
            dcc.Loading(html.Div(id="advanced-metrics-grid", className="metrics-grid"),
                        type="cube"
                        )
        ])
    ])
])
def get_interval(period):
    if "y" in period:
        return "5d"
    else:
        return "1d"
    
# === CALLBACKS ==
@callback(
    Output('stock-graph', 'figure'),
    Output('live-metrics', 'children'),
    Input('interval-graph-update', 'n_intervals'),
    Input('stock-dropdown', 'value'),
    Input('period-dropdown', 'value'),
)
def update_graph_and_metrics(n, symbol, period):

    color_palette = [
        ((0, 255, 0), (0, 100, 0)),
        ((0, 120, 255), (0, 40, 120)),
        ((255, 165, 0), (140, 70, 0)),
        ((200, 0, 200), (100, 0, 100)),
        ((255, 20, 147), (120, 0, 70)),
        ((0, 206, 209), (0, 80, 80)),
        ((255, 255, 0), (150, 150, 0)),
        ((255, 69, 0), (140, 35, 0)),
        ((75, 0, 130), (30, 0, 50)),
        ((60, 179, 113), (20, 90, 50)),
    ]

    fig = go.Figure()
    metrics = [
        html.Div(className="metric-item metric-header", children=[
            html.Span("Ticker"),
            html.Span("Prix Actuel"),
            html.Span("Variation (1j)")
        ])
    ]

    if isinstance(symbol, str):
        symbols = [symbol]
    elif isinstance(symbol, list):
        symbols = [s for s in symbol if s]
    else:
        symbols = []

    if not symbols:
        fig.add_annotation(text="Aucune action sélectionnée", x=0.5, y=0.5, showarrow=False)
        return fig, [html.Div("Aucune action sélectionnée", className="metric-item error")]

    for i, ticker_symbol in enumerate(symbols):

        # Filtrer les données pour ce ticker
        hist = df[df["symbol"] == ticker_symbol].sort_values("date").copy()

        if hist.empty:
            continue

        # Filtrage par période
        hist = filter_period(hist, period)

        if hist.empty:
            continue

        up_rgb, down_rgb = color_palette[i % len(color_palette)]
        up_line = f"rgb({up_rgb[0]},{up_rgb[1]},{up_rgb[2]})"
        down_line = f"rgb({down_rgb[0]},{down_rgb[1]},{down_rgb[2]})"
        up_fill = f"rgba({up_rgb[0]},{up_rgb[1]},{up_rgb[2]},0.6)"
        down_fill = f"rgba({down_rgb[0]},{down_rgb[1]},{down_rgb[2]},0.6)"

        # Ajout du graphique
        fig.add_trace(go.Candlestick(
            x=hist["date"],
            open=hist["Open"],
            high=hist["High"],
            low=hist["Low"],
            close=hist["Close"],
            name=ticker_symbol,
            increasing_line_color=up_line,
            decreasing_line_color=down_line,
            increasing_fillcolor=up_fill,
            decreasing_fillcolor=down_fill
        ))

        # Métriques
        current = hist["Close"].iloc[-1]
        prev = hist["Close"].iloc[-2] if len(hist) > 1 else current
        change = (current - prev) / prev * 100 if prev != 0 else 0

        metrics.append(html.Div(className="metric-item", children=[
            html.Span(ticker_symbol),
            html.Span(f"${current:,.2f}"),
            html.Span(f"{'+' if change > 0 else ''}{change:.2f}%",
                      className=f"metric-change {'up' if change > 0 else 'down'}")
        ]))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e6ffff"),
        xaxis=dict(showgrid=True, gridcolor="rgba(0,240,255,0.1)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(0,240,255,0.1)"),
        margin=dict(l=40, r=40, t=40, b=40),
        height=500
    )

    return fig, metrics

@callback(
    Output("advanced-metrics-grid", "children"),
    Input("stock-dropdown", "value"),
)
def update_advanced_metrics(symbols):
    if isinstance(symbols, str):
        symbols = [symbols]
    elif isinstance(symbols, list):
        symbols = [s for s in symbols if s]
    else:
        symbols = []

    if not symbols:
        return [html.Div("Aucun ticker sélectionné", className="metric-item error")]

    metrics = [
        html.Div(className="metric-item metric-header", children=[
            html.Span("Ticker"),
            html.Span("Volatilité 10j"),
            html.Span("Retour quotidien"),
            html.Span("Overnight Gap")
        ])
    ]

    for ticker in symbols:
        hist = df[df["symbol"] == ticker].sort_values("date")
        if hist.empty:
            continue

        last_row = hist.iloc[-1]

        # Forcer conversion float si jamais
        vol = float(last_row["volatility_10"])
        ret = float(last_row["daily_return"])
        gap = float(last_row["overnight_gap"])

        metrics.append(
            html.Div(className="metric-item", children=[
                html.Span(ticker, className="metric-title"),
                html.Span(f"{vol:.4f}", className=f"metric-change {'up' if vol > 0 else 'down'}"),
                html.Span(f"{ret:.4f}", className=f"metric-change {'up' if ret > 0 else 'down'}"),
                html.Span(f"{gap:.4f}", className=f"metric-change {'up' if gap > 0 else 'down'}"),
            ])
        )

    return metrics