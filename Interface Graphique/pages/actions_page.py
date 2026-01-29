from dash import html, dcc, Input, Output, State, callback, register_page,no_update,ctx,ALL
import plotly.graph_objects as go
import pandas as pd

register_page(__name__, path="/actions_page", name="Actions")

df_report = pd.read_csv("Data/data_report.csv")
df_cleaned = pd.read_csv("Data/ALL_CLEANED.csv", parse_dates=["date"])
df_features = pd.read_csv("Data/ALL_FEATURES.csv", parse_dates=["date"])
available_symbols = sorted(df_cleaned["symbol"].unique())

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

symbol_to_name = {
    "AAPL": "Apple",
    "AMZN": "Amazon",
    "BTC-USD": "Bitcoin",
    "GOOGL": "Google",
    "META": "Meta",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "TSLA": "Tesla"
}

stock_items = []
for symbol in available_symbols:
    display_name = symbol_to_name.get(symbol, symbol)  # fallback au symbole si pas de nom
    stock_items.append(html.Div(
        display_name,
        id={'type': 'stock-item', 'index': symbol},  # on garde le symbol pour le callback
        n_clicks=0,
        className="stock-item active" if symbol == "AAPL" else "stock-item"
    ))

# === LAYOUT ===
dropdown_options = [
    {"label": symbol, "value": symbol}
    for symbol in available_symbols
]

layout = html.Div(className="actions-page", children=[
    #Store permettant la valeur par défaut du graph
    dcc.Store(id="selected-stock", data="AAPL"),

    # Titre animé
    html.Div(className="page-title", children=[
        html.H1("Analyse d'Actifs en Temps Réel", className="glow-title"),
        html.Div(className="neon-underline")
    ]),
    # Conteneur principal
    html.Div(className="actions-navbar",children=[
        html.Div(className="actions-navbar-inner",children=[
            html.Div(
                className="stock-bar",
                children=stock_items
            ),
            dcc.Dropdown(
                searchable=False,
                maxHeight=100,
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
        ])
    ]),
    html.Div(className="actions-container", children=[
        html.Div(className="dual-panel-row",children=[
            # --- Recommandations (prédictions) ---
            html.Div(className="ai-panel", children=[
                html.H3("Prévisions de l'IA",className="panel-title", style={"padding-left": "36px"}),
                html.Div(className="text-panel", children=[
                    html.H3("Recommandations", className="panel-title"),
                    #Signal principal / valeur previsionnelle / confiance
                ]),
                html.Div(className="text-panel",children=[
                    html.H3("Performances Passée du Modèle",className="panel-title"),
                    #Précision / Métrique clé / graphique baktesting (gains si on suit les conseils)
                ])
            ]),
            # === MÉTRIQUES EN TEMPS RÉEL ===
            html.Div(className="text-panel", children=[
                html.H3("Résumé rapide : Top Stats", className="panel-title"),
                #High / Low (du jour) / volume / volume moyen récent / 
                dcc.Loading(html.Div(id='live-metrics', className="metrics-grid"), type="cube")  #modifier les stats 
            ])
        ]),
        # --- GRAPHIQUE ---
        html.Div(className="graph-panel", children=[
            html.H3("Graphique des Prix", className="panel-title"),
            dcc.Loading(
                dcc.Graph(id='stock-graph', className="lux-graph"),
                type="dot"
            ),
            dcc.Interval(
                id='interval-graph-update',
                interval=60*1000,
                n_intervals=0
            )
        ]),
        html.Div(className="text-panel", children=[
            html.H3("Indicateurs Techniques", className="panel-title"),
            #Moyenne Mobile / RSI / Volatilité /
        ]),
        # --- Footer ---
        html.Div(className="text-panel", children=[
            html.H3("Attention : Les prédictions ne constituent pas un conseil financier", className="panel-title"),
        ]),
    ])
])
def get_interval(period):
    if "y" in period:
        return "5d"
    else:
        return "1d"
    
# === CALLBACKS ==
@callback(
    Output("selected-stock", "data"),
    Output({"type": "stock-item", "index": ALL}, "className"),
    Input({"type": "stock-item", "index": ALL}, "n_clicks"),
    State({"type": "stock-item", "index": ALL}, "id"),
    prevent_initial_call=True
)
def select_single_stock(n_clicks, ids):
    if not ctx.triggered:
        return no_update, no_update

    selected = ctx.triggered_id["index"]

    classes = [
        "stock-item active" if item["index"] == selected else "stock-item"
        for item in ids
    ]

    return selected, classes
@callback(
    Output('stock-graph', 'figure'),
    Output('live-metrics', 'children'),
    Input('interval-graph-update', 'n_intervals'),
    Input("selected-stock", "data"),
    Input('period-dropdown', 'value'),
)
def update_graph_and_metrics(n, symbol, period):

    fig = go.Figure()

    if not symbol:
        fig.add_annotation(
            text="Aucune action sélectionnée", x=0.5, y=0.5, showarrow=False
        )
        return fig, [html.Div("Aucune action sélectionnée", className="metric-item error")]

    ticker_symbol = symbol
    # Filtrer les données pour ce ticker
    hist_graph = df_cleaned[df_cleaned["symbol"] == ticker_symbol].sort_values("date").copy()
    if hist_graph.empty:
        fig.add_annotation(
            text=f"Aucune donnée pour {ticker_symbol}", x=0.5, y=0.5, showarrow=False
        )
        return fig, [html.Div(f"Aucune donnée pour {ticker_symbol}", className="metric-item error")]

    # Filtrage par période
    hist_graph = filter_period(hist_graph, period)
    if hist_graph.empty:
        fig.add_annotation(
            text=f"Aucune donnée pour la période sélectionnée", x=0.5, y=0.5, showarrow=False
        )
        return fig, [html.Div("Aucune donnée pour la période sélectionnée", className="metric-item error")]

    # Couleurs simples : vert pour hausse, rouge pour baisse
    increasing_color = "green"
    decreasing_color = "red"

    # Ajout du graphique
    fig.add_trace(go.Candlestick(
        x=hist_graph["date"],
        open=hist_graph["Open"],
        high=hist_graph["High"],
        low=hist_graph["Low"],
        close=hist_graph["Close"],
        name=ticker_symbol,
        increasing_line_color=increasing_color,
        decreasing_line_color=decreasing_color,
        increasing_fillcolor="rgba(0,255,0,0.6)",
        decreasing_fillcolor="rgba(255,0,0,0.6)"
    ))

    hist_metric = df_features[df_features["symbol"] == ticker_symbol].sort_values("date").copy()
    if hist_metric.empty:
        fig.add_annotation(
            text=f"Aucune donnée pour {ticker_symbol}", x=0.5, y=0.5, showarrow=False
        )
        return fig, [html.Div(f"Aucune donnée pour {ticker_symbol}", className="metric-item error")]

    # Filtrage par période
    hist_metric = filter_period(hist_metric, period)
    if hist_metric.empty:
        fig.add_annotation(
            text=f"Aucune donnée pour la période sélectionnée", x=0.5, y=0.5, showarrow=False
        )
        return fig, [html.Div("Aucune donnée pour la période sélectionnée", className="metric-item error")]

    # Métriques
    price = hist_metric["Close"].iloc[-1]
    high = hist_metric["High"].iloc[-1]
    low = hist_metric["Low"].iloc[-1]
    volume = hist_metric["Volume"].iloc[-1]
    yesterday_price = hist_metric["Close"].iloc[-2]
    change_pct = (price - yesterday_price) / yesterday_price * 100

    change_class = "up" if change_pct >= 0 else "down"

    company = symbol_to_name.get(ticker_symbol, ticker_symbol)

    metrics = html.Div(className="text-panel", children=[
        html.Table(
            className="lux-table split-table",
            children=[
                html.Thead(
                    html.Tr([
                        html.Th("Entreprise"),
                        html.Th("Prix actuel"),
                        html.Th("Var. vs hier"),
                        html.Th(""),
                    ])
                ),
                html.Tbody([
                    # Ligne 1
                    html.Tr([
                        html.Td(company),
                        html.Td(f"${price:,.2f}"),
                        html.Td(
                            f"{change_pct:+.2f}%",
                            className=change_class
                        ),
                        html.Td(""),
                    ]),
                    # Ligne 2
                    html.Tr([
                        html.Td(f"High : {high:,.2f}"),
                        html.Td(f"Low : {low:,.2f}"),
                        html.Td(f"Volume : {volume:,.0f}"),
                    ]),
                ])
            ]
        )
    ])


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