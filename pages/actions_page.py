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
def get_interval(period):
    if "y" in period:
        return "5d"
    else:
        return "1d"
    
# === CALLBACKS ===
@callback(
    Output('stock-graph', 'figure'),
    Output('live-metrics', 'children'),
    Input('interval-graph-update', 'n_intervals'),
    Input('stock-dropdown', 'value'),
    Input('period-dropdown', 'value')
)

def update_graph_and_metrics(n, symbol, period):
    # Couleurs de remplissage des candelsticks
    color_palette = [
        ((0, 255, 0), (0, 100, 0)),         # vert vif / vert très foncé
        ((0, 120, 255), (0, 40, 120)),      # bleu vif / bleu très foncé
        ((255, 165, 0), (140, 70, 0)),      # orange vif / orange foncé marqué
        ((200, 0, 200), (100, 0, 100)),       # violet vif / violet très foncé
        ((255, 20, 147), (120, 0, 70)),     # rose vif / rose foncé marqué
        ((0, 206, 209), (0, 80, 80)),       # turquoise vif / turquoise foncé
        ((255, 255, 0), (150, 150, 0)),     # jaune vif / jaune foncé marqué
        ((255, 69, 0), (140, 35, 0)),       # orange rouge vif / orange rouge foncé
        ((75, 0, 130), (30, 0, 50)),        # indigo vif / indigo très foncé
        ((60, 179, 113), (20, 90, 50)),     # vert menthe vif / vert menthe foncé
    ]

    interval=get_interval(period)
    try:
        fig = go.Figure()
        metrics = [
            html.Div(className="metric-item metric-header", children=[
                html.Span("Ticker", className="metric-label"),
                html.Span("Prix Actuel", className="metric-label"),
                html.Span("Variation (1j)", className="metric-label"),
            ])
        ]

        if isinstance(symbol, str):
            symbols = [symbol]  #transformer la chaîne en liste
        elif isinstance(symbol, list):
            symbols = [s for s in symbol if s]  # filtrer les valeurs vides
        else:
            symbols = []

        if not symbols:
            fig.add_annotation(text="Aucune action sélectionnée", x=0.5, y=0.5, showarrow=False)
            return fig, [html.Div("Aucune action sélectionnée", className="metric-item error")]
        
        for i,ticker_symbol in enumerate(symbols):
            try :
                up_rgb, down_rgb = color_palette[i % len(color_palette)]
                # Couleurs différentes pour chaque action différente
                up_line = f"rgb({up_rgb[0]},{up_rgb[1]},{up_rgb[2]})"
                down_line = f"rgb({down_rgb[0]},{down_rgb[1]},{down_rgb[2]})"

                # Couleurs légèrement assombries pour le remplissage
                up_fill = f"rgba({up_rgb[0]},{up_rgb[1]},{up_rgb[2]},0.6)"
                down_fill = f"rgba({down_rgb[0]},{down_rgb[1]},{down_rgb[2]},0.6)"

                ticker = yf.Ticker(ticker_symbol)
                hist = ticker.history(period=period, interval=interval)
                
                if hist.empty:
                    continue 

                # Graphique
                fig.add_trace(go.Candlestick(
                    x=hist.index,
                    open=hist['Open'], high=hist['High'],
                    low=hist['Low'], close=hist['Close'],
                    name=ticker_symbol,
                    increasing_line_color=up_line,
                    decreasing_line_color=down_line,
                    increasing_fillcolor=up_fill,
                    decreasing_fillcolor=down_fill
                ))

                # Métriques
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2] if len(hist) > 1 else current
                change = (current - prev) / prev * 100 if prev != 0 else 0
                metrics.append(html.Div(className="metric-item", children=[
                    html.Span(ticker_symbol, className="metric-title"),
                    html.Span(f"${current:,.2f}", className="metric-value"),
                    html.Span(f"{'+' if change > 0 else ''}{change:.2f}%", 
                              className=f"metric-change {'up' if change > 0 else 'down'}")
                ]))
            except Exception:
                continue
        
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
        fig.update_xaxes(autorange=True)
        fig.update_yaxes(autorange=True)
        return fig, metrics

    except Exception as e:
        fig = go.Figure().add_annotation(text="Erreur de chargement", x=0.5, y=0.5, showarrow=False)
        metrics = [html.Div("Erreur API", className="metric-item error")]
        return fig, metrics