from dash import html, dcc, Input, Output, callback, register_page
import yfinance as yf
import plotly.graph_objects as go
import pandas as pd

register_page(__name__, path="/actions_page", name="Actions")

# === LAYOUT ===
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
                options=[
                    {'label': 'Apple (AAPL)', 'value': 'AAPL'},
                    {'label': 'Microsoft (MSFT)', 'value': 'MSFT'},
                    {'label': 'Tesla (TSLA)', 'value': 'TSLA'},
                    {'label': 'Amazon (AMZN)', 'value': 'AMZN'},
                    {'label': 'NVIDIA (NVDA)', 'value': 'NVDA'},
                    {'label': 'Bitcoin (BTC)', 'value': 'BTC-USD'},
                    {'label': 'Ethereum (ETH)', 'value': 'ETH-USD'},
                ],
                value='AAPL',
                className="lux-dropdown scrollable-dropdown"
            ),
            html.H3("Intervalle", className="panel-title mt-20"),
            dcc.Dropdown(
                id='interval-dropdown',
                options=[
                    {'label': '1 minute', 'value': '1m'},
                    {'label': '5 minutes', 'value': '5m'},
                    {'label': '15 minutes', 'value': '15m'},
                    {'label': '1 heure', 'value': '60m'},
                ],
                value='1m',
                className="lux-dropdown"
            ),
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
    ])
])

# === CALLBACKS ===
@callback(
    Output('stock-graph', 'figure'),
    Output('live-metrics', 'children'),
    Input('interval-graph-update', 'n_intervals'),
    Input('stock-dropdown', 'value'),
    Input('interval-dropdown', 'value')
)
def update_graph_and_metrics(n, symbol, interval):
    try:
        # Récupérer données
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d", interval=interval)
        
        if hist.empty:
            fig = go.Figure().add_annotation(text="Aucune donnée", x=0.5, y=0.5, showarrow=False)
            metrics = [html.Div("Données indisponibles", className="metric-item error")]
            return fig, metrics

        # Graphique
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist['Open'], high=hist['High'],
            low=hist['Low'], close=hist['Close'],
            name=symbol
        ))
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

        # Métriques
        current = hist['Close'].iloc[-1]
        prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
        change = (current - prev) / prev * 100 if prev != 0 else 0

        metrics = [
            html.Div(className="metric-item", children=[
                html.Span("Prix Actuel", className="metric-label"),
                html.Span(f"${current:,.2f}", className="metric-value")
            ]),
            html.Div(className="metric-item", children=[
                html.Span("Variation", className="metric-label"),
                html.Span(f"{'+' if change > 0 else ''}{change:.2f}%", 
                         className=f"metric-change {'up' if change > 0 else 'down'}")
            ]),
            html.Div(className="metric-item", children=[
                html.Span("Volume", className="metric-label"),
                html.Span(f"{hist['Volume'].iloc[-1]:,}", className="metric-value")
            ]),
        ]

        return fig, metrics

    except Exception as e:
        fig = go.Figure().add_annotation(text="Erreur de chargement", x=0.5, y=0.5, showarrow=False)
        metrics = [html.Div("Erreur API", className="metric-item error")]
        return fig, metrics