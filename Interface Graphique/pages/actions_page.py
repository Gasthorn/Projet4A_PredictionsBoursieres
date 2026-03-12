from dash import html, dcc, Input, Output, State, callback, register_page,no_update,ctx,ALL
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from supabase import create_client

register_page(__name__, path="/actions_page", name="Actions")

url = "https://qeolwdccnegosrbldxqa.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFlb2x3ZGNjbmVnb3NyYmxkeHFhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc4NjIxOTIsImV4cCI6MjA4MzQzODE5Mn0.BHFV2ANfkC3RP-_R-cyjp-8yKtQhsZhVWUmnGnuU9b4"
supabase = create_client(url, key)
symbol_groups = {
    "BTC": ["BTC", "BTC-USD"],
    # Ajouter d'autres regroupements si nécessaire
}

def filter_period(df, period):
    days_map = {
        "1mo": 30, "2mo": 60, "3mo": 90, "6mo": 182,
        "9mo": 273, "1y": 365, "2y": 730, "3y": 1095, "5y": 1825
    }
    if period not in days_map:
        return df

    last_date = df["date"].iloc[0]
    cutoff = last_date - pd.Timedelta(days=days_map[period])

    return df[df["date"] >= cutoff]

stock_items = []

response = supabase.table("stocks") \
    .select("symbol,name") \
    .order("symbol") \
    .execute()

available_symbols_raw = []
symbol_to_name_raw = {}

for row in response.data:
    available_symbols_raw.append(row["symbol"])
    symbol_to_name_raw[row["symbol"]] = row["name"]

available_symbols = []
symbol_to_name = {}

for group_name, group_symbols in symbol_groups.items():
    present_symbols = [s for s in group_symbols if s in available_symbols_raw]
    if present_symbols:
        available_symbols.append(group_name)  
        symbol_to_name[group_name] = symbol_to_name_raw[present_symbols[0]]
        for s in present_symbols:
            available_symbols_raw.remove(s)

for s in available_symbols_raw:
    available_symbols.append(s)
    symbol_to_name[s] = symbol_to_name_raw[s]

for symbol in available_symbols:
    display_name = symbol_to_name.get(symbol, symbol) 
    stock_items.append(html.Div(
        display_name,
        id={'type': 'stock-item', 'index': symbol},  
        n_clicks=0,
        className="stock-item active" if symbol == "AAPL" else "stock-item"
    ))

# === LAYOUT ===
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
                value='3mo',
                className="lux-dropdown scrollable-dropdown"
            )
        ])
    ]),
    html.Div(className="actions-container", children=[
        html.Div(className="dual-panel-row",children=[
            # --- Recommandations (prédictions) ---
            html.Div(className="ai-panel", children=[
                #Signal du modèle
                html.Div(className="text-panel", children=[
                    html.H3("Prévisions de l'IA",className="panel-title", style={"padding-left": "36px"}),
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
                                    html.Td(id="ai-signal", className="metric-value", children="Chargement..."),
                                    html.Td(id="ai-predict", className="metric-value", children="Chargement..."),
                                    html.Td(id="ai-confidence", className="metric-value", children="Chargement..."),
                                ])
                            ])
                        ]
                    ),
                    # Backtest / Performance passée
                    html.H4("Performance passée", className="panel-title"),
                    html.Div(id="ai-backtest", className="metric-value", children="Chargement...", style={"margin-bottom": "24px"}) ,
                    html.H3("Attention : Les prédictions ne constituent pas un conseil financier", className="panel-title"),
                ]),
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
    ai_signal, ai_actual, ai_backtest, ai_prediction = "N/A", "N/A", "N/A","N/A"

    if not symbol:
        fig.add_annotation(
            text="Aucune action sélectionnée", x=0.5, y=0.5, showarrow=False
        )
        return (
            fig,
            [html.Div("Aucune donnée pour la période sélectionnée", className="metric-item error")],
            "N/A",
            "metric-value",
            "N/A",
            "metric-value",
            "N/A",
            "N/A"
        )

    ticker_symbol = symbol
    for group_name, group_symbols in symbol_groups.items():
        if symbol in group_symbols:
            ticker_group = group_symbols  
            break
    else:
        ticker_group = [symbol]  
    # Filtrer les données pour ce ticker
    all_data = []
    batch_size = 1000
    start = 0

    while True:
        response = supabase.table("historical_data") \
            .select("date, open, high, low, close, volume") \
            .in_("symbol", ticker_group) \
            .order("date", desc=True) \
            .range(start, start + batch_size - 1) \
            .execute()
        
        if not response.data:
            break
        
        all_data.extend(response.data)
        start += batch_size

    hist_graph = pd.DataFrame(all_data)
    hist_graph["date"] = pd.to_datetime(hist_graph["date"])
    hist_graph = hist_graph.drop_duplicates(subset=[ "date"], keep="first")

    if hist_graph.empty:
        fig.add_annotation(
            text=f"Aucune donnée pour {ticker_symbol}", x=0.5, y=0.5, showarrow=False
        )
        return (
            fig,
            [html.Div("Aucune donnée pour la période sélectionnée", className="metric-item error")],
            "N/A",
            "metric-value",
            "N/A",
            "metric-value",
            "N/A",
            "N/A"
        )

    # Filtrage par période
    hist_graph = filter_period(hist_graph, period)
    if hist_graph.empty:
        fig.add_annotation(
            text=f"Aucune donnée pour la période sélectionnée", x=0.5, y=0.5, showarrow=False
        )
        return (
            fig,
            [html.Div("Aucune donnée pour la période sélectionnée", className="metric-item error")],
            "N/A",
            "metric-value",
            "N/A",
            "metric-value",
            "N/A",
            "N/A"
        )
    # Couleurs simples : vert pour hausse, rouge pour baisse
    increasing_color = "green"
    decreasing_color = "red"

    # Ajout du graphique
    fig.add_trace(go.Candlestick(
        x=hist_graph["date"],
        open=hist_graph["open"],
        high=hist_graph["high"],
        low=hist_graph["low"],
        close=hist_graph["close"],
        name=ticker_symbol,
        increasing_line_color=increasing_color,
        decreasing_line_color=decreasing_color,
        increasing_fillcolor="rgba(0,255,0,0.6)",
        decreasing_fillcolor="rgba(255,0,0,0.6)"
    ))

    all_data = []
    start = 0
    while True:
        response = supabase.table("features") \
            .select("*") \
            .in_("symbol", ticker_group) \
            .order("date", desc=True) \
            .range(start, start + batch_size - 1) \
            .execute()

        if not response.data:
            break
        
        all_data.extend(response.data)
        start += batch_size

    hist_metric = pd.DataFrame(all_data)
    hist_metric["date"] = pd.to_datetime(hist_metric["date"])
    hist_metric = hist_metric.drop_duplicates(subset=[ "date"], keep="first")

    if hist_metric.empty:
        fig.add_annotation(
            text=f"Aucune donnée pour {ticker_symbol}", x=0.5, y=0.5, showarrow=False
        )
        return (
            fig,
            [html.Div("Aucune donnée pour la période sélectionnée", className="metric-item error")],
            "N/A",
            "metric-value",
            "N/A",
            "metric-value",
            "N/A",
            "N/A"
        )

    # Filtrage par période
    hist_metric = filter_period(hist_metric, period)
    if hist_metric.empty:
        fig.add_annotation(
            text=f"Aucune donnée pour la période sélectionnée", x=0.5, y=0.5, showarrow=False
        )
        return (
            fig,
            [html.Div("Aucune donnée pour la période sélectionnée", className="metric-item error")],
            "N/A",
            "metric-value",
            "N/A",
            "metric-value",
            "N/A",
            "N/A"
        )

    # Métriques
    price = hist_metric["close_lag1"].iloc[-1]
    high = hist_graph["high"].iloc[-1]
    low = hist_graph["low"].iloc[-1]
    volume = hist_graph["volume"].iloc[-1]
    if len(hist_graph) < 2:
        yesterday_price = hist_graph["close"].iloc[-1]
    else:
        yesterday_price = hist_graph["close"].iloc[-2]
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

    response = supabase.table("predictions") \
        .select("*") \
        .in_("symbol", ticker_group) \
        .order("date", desc=True) \
        .limit(1) \
        .execute()

    pred_df = pd.DataFrame(response.data)

    if not pred_df.empty:
        ai_signal = pred_df["signal"].iloc[0]
        ai_prediction = pred_df["predicted_close"].iloc[0]
        ai_actual = pred_df['actual_close'].iloc[0]
        ai_backtest = "Gain moyen 6 mois : +3%"

    signal_class = "metric-value"
    predict_class = "metric-value"

    if(ai_signal == "BUY"):
        signal_class = "metric-value up"
        predict_class = "metric-value up"
    elif(ai_signal == "SELL"):
        signal_class = "metric-value down"
        predict_class = "metric-value down"
    else:
        signal_class = "metric-value"
        predict_class = "metric-value"

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

    return fig, metrics, ai_signal,signal_class, ai_prediction,predict_class, ai_actual, ai_backtest