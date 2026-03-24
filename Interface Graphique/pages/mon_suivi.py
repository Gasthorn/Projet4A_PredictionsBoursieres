import dash
from dash import html, dcc, Input, Output, State, callback
import plotly.graph_objects as go
import plotly.express as px
from services.tracking_service import get_user_trades, get_user_stats
from services.auth_service import get_user_by_email
import pandas as pd
import numpy as np
from datetime import datetime

dash.register_page(__name__, path="/mon-suivi", name="Mon Suivi")

layout = html.Div(className="premium-dashboard", children=[
    # Header avec effet de bienvenue
    html.Div(className="premium-header", children=[
        html.Div(className="header-left", children=[
            html.H1("Tableau de bord", className="premium-title"),
            html.Div(className="premium-welcome", id="premium-welcome-message"),
        ]),
        html.Div(className="header-right", children=[
            html.Div(className="premium-date", id="premium-date"),
            html.Div(className="premium-avatar", children=[
                html.I(className="fas fa-user-circle", style={"fontSize": "2rem", "color": "#00f0ff"}),
            ]),
        ]),
    ]),

    # Cartes de performance (KPIs) avec icônes Font Awesome
    html.Div(className="premium-kpi-grid", id="premium-kpi-grid"),

    # Graphique principal
    html.Div(className="premium-chart-container", children=[
        html.Div(className="chart-header", children=[
            html.H2("Évolution du capital", className="chart-title"),
            html.Div(className="chart-legend", children=[
                html.Span([html.I(className="fas fa-chart-line", style={"marginRight": "5px"}), "Capital"], 
                         className="legend-item", style={"color": "#00f0ff"}),
            ]),
        ]),
        dcc.Graph(id="premium-chart", className="premium-chart", config={'displayModeBar': False}),
    ]),

    # Section Trades uniquement
    html.Div(className="premium-trades-section", children=[
        html.Div(className="section-header", children=[
            html.H2([html.I(className="fas fa-history", style={"marginRight": "10px"}), "Historique des trades"], 
                   className="section-title"),
            html.Div(id="trades-summary", className="trades-summary"),
        ]),
        html.Div(id="premium-trades-table", className="trades-table-container"),
    ]),

    # Interval de mise à jour
    dcc.Interval(id="premium-interval", interval=30000, n_intervals=0),
])

@callback(
    Output("premium-welcome-message", "children"),
    Input("premium-interval", "n_intervals"),
    State("session-store", "data")
)
def update_welcome(n, session):
    if not session:
        return ""
    email = session.get("email", "")
    name = email.split('@')[0].capitalize()
    return f"Bon retour parmi nous, {name}"

@callback(
    Output("premium-date", "children"),
    Input("premium-interval", "n_intervals")
)
def update_date(n):
    now = datetime.now()
    return now.strftime("%d %B %Y • %H:%M")

@callback(
    Output("premium-kpi-grid", "children"),
    Output("premium-chart", "figure"),
    Output("premium-trades-table", "children"),
    Output("trades-summary", "children"),
    Input("premium-interval", "n_intervals"),
    State("session-store", "data")
)
def update_dashboard(n, session):
    if not session:
        return [], {}, html.Div("Veuillez vous connecter", className="error-premium"), ""
    
    user_email = session.get("email")
    stats = get_user_stats(user_email)
    trades = get_user_trades(user_email, 50)
    
    # --- KPIs avec icônes Font Awesome ---
    kpi_cards = [
        html.Div(className="kpi-card", children=[
            html.Div(className="kpi-icon", children=html.I(className="fas fa-wallet")),
            html.Div(className="kpi-content", children=[
                html.Span("Capital total", className="kpi-label"),
                html.Span("12 450 €", className="kpi-value"),
                html.Span([html.I(className="fas fa-arrow-up", style={"marginRight": "3px"}), "+2.3%"], 
                         className="kpi-change positive"),
            ]),
        ]),
        html.Div(className="kpi-card", children=[
            html.Div(className="kpi-icon", children=html.I(className="fas fa-chart-line")),
            html.Div(className="kpi-content", children=[
                html.Span("Gains totaux", className="kpi-label"),
                html.Span(f"{stats['total_pnl']:+,.0f} €", className=f"kpi-value {'positive' if stats['total_pnl'] > 0 else 'negative'}"),
                html.Span([html.I(className="fas fa-percent", style={"marginRight": "3px"}), f"{stats['win_rate']:.1f}% réussite"], 
                         className="kpi-detail"),
            ]),
        ]),
        html.Div(className="kpi-card", children=[
            html.Div(className="kpi-icon", children=html.I(className="fas fa-chart-pie")),
            html.Div(className="kpi-content", children=[
                html.Span("Trades", className="kpi-label"),
                html.Span(f"{stats['total_trades']}", className="kpi-value"),
                html.Span([
                    html.I(className="fas fa-check-circle", style={"color": "#7cffb2", "marginRight": "5px"}),
                    f"{stats['wins']} gagnants",
                    html.I(className="fas fa-times-circle", style={"color": "#ff7b7b", "marginLeft": "10px", "marginRight": "5px"}),
                    f"{stats['losses']} perdants"
                ], className="kpi-detail"),
            ]),
        ]),
        html.Div(className="kpi-card", children=[
            html.Div(className="kpi-icon", children=html.I(className="fas fa-bolt")),
            html.Div(className="kpi-content", children=[
                html.Span("Positions ouvertes", className="kpi-label"),
                html.Span(f"{stats['open_trades']}", className="kpi-value"),
                html.Span([html.I(className="fas fa-hourglass-half", style={"marginRight": "5px"}), "en cours"], 
                         className="kpi-detail"),
            ]),
        ]),
    ]
    
    # --- Graphique époustouflant ---
    dates = pd.date_range(end=datetime.now(), periods=30, freq="D")
    capital = [10000 + i*50 + (i*8 if i>15 else 0) + np.random.randint(-20, 20) for i in range(30)]
    
    fig = go.Figure()
    
    # Zone de remplissage avec dégradé
    fig.add_trace(go.Scatter(
        x=dates,
        y=capital,
        mode='lines',
        name='Capital',
        line=dict(color="#00f0ff", width=3),
        fill='tozeroy',
        fillcolor="rgba(0, 240, 255, 0.1)"
    ))
    
    # Points sur la courbe
    fig.add_trace(go.Scatter(
        x=dates[::3],
        y=[capital[i] for i in range(0, 30, 3)],
        mode='markers',
        name='Points',
        marker=dict(color="#00f0ff", size=8, line=dict(color="#0a0f1a", width=2)),
        showlegend=False
    ))
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0e0", family="Inter"),
        height=350,
        margin=dict(l=40, r=20, t=20, b=40),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            showline=False,
            tickformat="%d %b"
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            tickformat=",.0f",
            title=""
        ),
        hovermode="x unified",
        showlegend=False
    )
    
    # --- Résumé des trades ---
    closed_trades = len([t for t in trades if t[5]])  # trade avec exit_price
    win_trades = len([t for t in trades if t[10] and t[10] > 0])
    
    trades_summary = html.Div([
        html.Span([html.I(className="fas fa-list", style={"marginRight": "5px"}), f"{len(trades)} total"], 
                 className="summary-badge"),
        html.Span([html.I(className="fas fa-check", style={"marginRight": "5px"}), f"{closed_trades} fermés"], 
                 className="summary-badge"),
        html.Span([html.I(className="fas fa-trophy", style={"marginRight": "5px"}), f"{win_trades} gagnants"], 
                 className="summary-badge positive"),
        html.Span([html.I(className="fas fa-clock", style={"marginRight": "5px"}), f"{stats['open_trades']} ouverts"], 
                 className="summary-badge"),
    ])
    
    # --- Tableau des trades ---
    if not trades:
        trades_table = html.Div(
            [html.I(className="fas fa-inbox", style={"fontSize": "3rem", "marginBottom": "15px", "display": "block"}), 
             "Aucune activité pour le moment"],
            className="empty-premium"
        )
    else:
        rows = []
        for trade in trades[:20]:
            symbol = trade[3]
            entry = trade[4]
            exit_price = trade[5] if trade[5] else None
            pnl = trade[10] if trade[10] else 0
            date = trade[8][:10]
            
            pnl_class = "positive" if pnl > 0 else "negative" if pnl < 0 else ""
            status = "Ouvert" if not exit_price else "Fermé"
            
            rows.append(html.Tr([
                html.Td(html.Span(symbol, className="trade-symbol")),
                html.Td(f"{entry:,.2f} €"),
                html.Td(f"{exit_price:,.2f} €" if exit_price else "—"),
                html.Td(html.Span([
                    html.I(className="fas fa-arrow-up" if pnl > 0 else "fas fa-arrow-down" if pnl < 0 else "", 
                          style={"marginRight": "5px"}),
                    f"{pnl:+,.0f} €"
                ], className=f"trade-pnl {pnl_class}")),
                html.Td(date),
                html.Td(html.Span([
                    html.I(className="fas fa-lock-open" if status == "Ouvert" else "fas fa-lock", 
                          style={"marginRight": "5px"}),
                    status
                ], className=f"trade-status {status.lower()}")),
            ]))
        
        trades_table = html.Div([
            html.Table([
                html.Thead(html.Tr([
                    html.Th([html.I(className="fas fa-coins", style={"marginRight": "5px"}), "Actif"]),
                    html.Th([html.I(className="fas fa-arrow-right-to-bracket", style={"marginRight": "5px"}), "Entrée"]),
                    html.Th([html.I(className="fas fa-arrow-right-from-bracket", style={"marginRight": "5px"}), "Sortie"]),
                    html.Th([html.I(className="fas fa-chart-simple", style={"marginRight": "5px"}), "P&L"]),
                    html.Th([html.I(className="fas fa-calendar", style={"marginRight": "5px"}), "Date"]),
                    html.Th([html.I(className="fas fa-circle-info", style={"marginRight": "5px"}), "Statut"]),
                ])),
                html.Tbody(rows)
            ], className="premium-table")
        ])
    
    return kpi_cards, fig, trades_table, trades_summary