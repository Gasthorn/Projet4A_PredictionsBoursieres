from dash import html, dcc, Input, Output, State, callback, register_page,no_update,ctx,ALL
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from tensorflow.keras.models import load_model

register_page(__name__, path="/actions_page", name="Actions")

df_report = pd.read_csv("Data/data_report.csv")
df_cleaned = pd.read_csv("Data/ALL_CLEANED.csv", parse_dates=["date"])
df_features = pd.read_csv("Data/ALL_FEATURES.csv", parse_dates=["date"])
available_symbols = sorted(df_cleaned["symbol"].unique())

lstm_model = load_model("Modèle IA/global_lstm_returns.keras")
symbol_to_id = {
    "AAPL": 0,
    "AMZN": 1,
    "BTC-USD": 2,
    "GOOGL": 3,
    "META": 4,
    "MSFT": 5,
    "NVDA": 6,
    "TSLA": 7,
}

def prepare_lstm_inputs(df_features, symbol, n_timesteps=60):
    """
    Prépare les deux entrées pour le LSTM :
    - Séquence temporelle (Close)
    - ID du symbol
    """
    seq_input = df_features["Close"].tail(n_timesteps).values.reshape(1, n_timesteps, 1)

    symbol_id = symbol_to_id[symbol]
    extra_input = np.array([[symbol_id]])  # forme (1,1)

    return [seq_input, extra_input]

def predict_lstm(df_features_symbol, symbol):
    """
    Retourne signal, confiance et backtest
    """
    inputs = prepare_lstm_inputs(df_features_symbol, symbol)
    if inputs is None:
        return "Pas assez de données", "N/A", "N/A"

    # Prédiction
    pred_price = lstm_model.predict(inputs)[0][0]

    # Signal simple
    signal = "Acheter" if pred_price > 0 else "Vendre"

    # Confiance relative (en %)
    confidence = abs(pred_price)*1000

    # Backtest statique (à adapter si tu as un vrai backtest)
    backtest = "Gain moyen 6 mois : +3%"

    return signal, f"{confidence:.1f}%", backtest, pred_price

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
                #Signal du modèle
                html.Div(className="text-panel", children=[
                    html.Table(
                        className="lux-table split-table",
                        children=[
                            html.Thead(
                                html.Tr([
                                    html.Th("Signal"),
                                    html.Th("Prédiction"),
                                    html.Th("Confiance"),
                                ])
                            ),
                            html.Tbody([
                                html.Tr([
                                    html.Td(id="ai-signal", className="metric-value up", children="Chargement..."),
                                    html.Td(id="ai-predict", className="metric-value up", children="Chargement..."),
                                    html.Td(id="ai-confidence", className="metric-value", children="Chargement..."),
                                ])
                            ])
                        ]
                    )

                ]),
                # Backtest / Performance passée
                html.Div(className="text-panel", children=[
                    html.H4("Performance passée", className="panel-title"),
                    html.Div(id="ai-backtest", className="metric-value", children="Chargement...")  
                ])
            ]),
            # === MÉTRIQUES EN TEMPS RÉEL ===
            html.Div(className="text-panel", children=[
                html.H3("Résumé rapide : Top Stats", className="panel-title"),
                dcc.Loading(html.Div(id='live-metrics', className="metrics-grid"), type="cube")  
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
    Output('ai-signal', 'children'),
    Output('ai-signal', 'className'),
    Output('ai-predict', 'children'),
    Output('ai-predict', 'className'),
    Output('ai-confidence', 'children'),
    Output('ai-backtest', 'children'),
    Input('interval-graph-update', 'n_intervals'),
    Input("selected-stock", "data"),
    Input('period-dropdown', 'value'),
)
def update_graph_and_metrics(n, symbol, period):

    fig = go.Figure()

    metrics = []
    ai_signal, ai_confidence, ai_backtest, ai_prediction = "N/A", "N/A", "N/A","N/A"

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

    ai_signal, ai_confidence, ai_backtest, ai_prediction = predict_lstm(hist_metric, symbol)

    signal_class = "metric-value up" if ai_signal == "Acheter" else "metric-value down"
    predict_class = "metric-value up" if ai_signal == "Acheter" else "metric-value down"


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

    return fig, metrics, ai_signal,signal_class, ai_prediction,predict_class, ai_confidence, ai_backtest