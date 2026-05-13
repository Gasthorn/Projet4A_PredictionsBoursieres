import dash
from dash import dcc, html, Input, Output, State
import yfinance as yf
import pandas as pd
from flask import jsonify
from services.database import init_db
import logging

# Supprimer les logs trop bavards
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# === INIT DATABASE ===
init_db()

# === INIT DASH ===
app = dash.Dash(
    __name__,
    use_pages=True,
    suppress_callback_exceptions=True,
    external_stylesheets=[
        "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css"
    ]
)

app.title = "ENSIM - Predictions Boursieres"

# === TICKERS ===
TICKERS = {
    "BTC-USD": "BTC/USD",
    "ETH-USD": "ETH/USD",
    "^IXIC": "NASDAQ",
    "AAPL": "AAPL",
    "GOOGL": "GOOGL"
}

def fetch_ticker_data():
    data = []
    for symbol, label in TICKERS.items():
        try:
            stock = yf.Ticker(symbol)
            hist = stock.history(period="1d", interval="1m")
            if len(hist) >= 2:
                current = hist['Close'].iloc[-1]
                prev = hist['Close'].iloc[-2]
                change = (current - prev) / prev * 100
                change_str = f"up {change:.2f}%" if change > 0 else f"down {abs(change):.2f}%"
                change_class = "up" if change > 0 else "down"
                data.append({
                    "label": label,
                    "value": f"{current:,.2f}",
                    "change": change_str,
                    "class": change_class
                })
            else:
                data.append({
                    "label": label,
                    "value": "N/A",
                    "change": "down 0.0%",
                    "class": "down"
                })
        except Exception as e:
            print(f"Erreur ticker {symbol}: {e}")
            data.append({
                "label": label,
                "value": "ERR",
                "change": "down 0.0%",
                "class": "down"
            })
    return data

# === LAYOUT ===
app.layout = html.Div([

    # Background (z-index négatif)
    html.Div(className="trade-bg"),
    html.Div(className="grid-lines"),
    html.Div([html.Div(className="particle") for _ in range(40)]),

    # === COMPOSANTS CORE ===
    dcc.Location(id="url", refresh=False),
    dcc.Store(id="session-store", storage_type="session"),
    dcc.Interval(id="interval-component", interval=5*60*1000, n_intervals=0),

    # === TICKER EN HAUT (z-index: 3000) ===
    html.Div(id="ticker-container"),
    
    # === NAVBAR (z-index: 2000) ===
    html.Div(id="navbar-container"),
    
    # === PAGE CONTENT ===
    dash.page_container
])

# === LISTE DES PAGES PROTÉGÉES ===
PROTECTED_PAGES = ["/actions_page", "/analysis", "/admin", "/mon-suivi", "/profil"]

# === CALLBACK PRINCIPAL : NAVBAR + TICKER + PROTECTION ===
@app.callback(
    Output("navbar-container", "children"),
    Output("ticker-container", "children"),
    Output("interval-component", "disabled"),
    Input("url", "pathname"),
    Input("session-store", "data"),
)
def update_layout(pathname, session):
    is_logged_in = session is not None
    is_home = pathname == "/"
    
    # === 1. CONSTRUCTION DE LA NAVBAR ===
    # TOUJOURS visibles : Accueil, Témoignages
    nav_links = [
        dcc.Link("Accueil", href="/", className="nav-link"),
        dcc.Link("Témoignages", href="/temoignages", className="nav-link"),
    ]
    
    if is_logged_in:
        # === CONNECTÉ ===
        nav_links.extend([
            dcc.Link("Marchés", href="/actions_page", className="nav-link"),
            dcc.Link("Analyse", href="/analysis", className="nav-link"),
            dcc.Link("Mon Suivi", href="/mon-suivi", className="nav-link"),
            dcc.Link("Mon Profil", href="/profil", className="nav-link"),
        ])
        
        # Ajouter Admin si l'utilisateur est admin
        if session and session.get("is_admin"):
            print(f" Lien admin ajouté pour {session.get('email')}")
            nav_links.append(dcc.Link("Admin", href="/admin", className="nav-link"))
        
        # Ajouter le bouton Déconnexion
        nav_links.append(html.Button("Déconnexion", id="logout-btn", className="nav-link"))
        
    else:
        # === NON CONNECTÉ ===
        nav_links.extend([
            dcc.Link("Connexion", href="/login", className="nav-link"),
            dcc.Link("Inscription", href="/signup", className="nav-link"),
        ])
    
    # Détermine la classe CSS de la navbar
    navbar_class = "navbar with-ticker" if is_home and is_logged_in else "navbar no-ticker"
    
    navbar = html.Div(className=navbar_class, children=[
        html.Div(className="navbar-left", children=[
            html.Img(src="/assets/logo.png", className="logo", alt="Logo")
        ]),
        html.Div(className="nav-links", children=nav_links)
    ])
    
    # === 2. TICKER (seulement sur home ET connecté) ===
    if is_home and is_logged_in:
        ticker = html.Div(className="ticker-wrap", children=[
            html.Div(id="ticker-inner", className="ticker-inner")
        ])
        interval_disabled = False
    else:
        ticker = ""
        interval_disabled = True
    
    return navbar, ticker, interval_disabled

# === CALLBACK TICKER ===
@app.callback(
    Output("ticker-inner", "children"),
    Input("interval-component", "n_intervals")
)
def update_ticker(n):
    data = fetch_ticker_data()
    items = [
        html.Div(className="ticker-item", children=[
            html.Span(d["label"]),
            html.Span(className="ticker-value", children=d["value"]),
            html.Span(className=f"ticker-change {d['class']}", children=d["change"])
        ])
        for d in data
    ]
    ticker_set = html.Div(className="ticker-set", children=items)
    return [ticker_set, ticker_set]

# === CALLBACK LOGOUT ===
# On retourne null → Dash écrit null dans sessionStorage lui-même
# Puis setTimeout donne le temps à Dash de finir avant de recharger la page
app.clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks && n_clicks > 0) {
            setTimeout(function() { window.location.href = '/'; }, 300);
            return null;
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("session-store", "data", allow_duplicate=True),
    Input("logout-btn", "n_clicks"),
    prevent_initial_call=True
)

# === CALLBACK REDIRECTION PAGES PROTÉGÉES ===
@app.callback(
    Output("url", "pathname", allow_duplicate=True),
    Input("url", "pathname"),
    State("session-store", "data"),
    prevent_initial_call=True
)
def redirect_if_not_logged(pathname, session):
    # Pages qui nécessitent une connexion
    if pathname in PROTECTED_PAGES and session is None:
        return "/login"
    
    return dash.no_update

# === API OHLCV (yfinance → lightweight-charts) ===
_ALLOWED = {'AAPL', 'AMZN', 'BTC-USD', 'GOOGL', 'META', 'MSFT', 'NVDA', 'TSLA'}

@app.server.route('/api/ohlcv/<symbol>')
def api_ohlcv(symbol):
    if symbol not in _ALLOWED:
        return jsonify({'error': 'Symbol not allowed'}), 400
    try:
        h = yf.Ticker(symbol).history(period='2y', interval='1d')
        if h.empty:
            return jsonify({'error': 'No data'}), 404
        try:
            h.index = pd.to_datetime(h.index).tz_localize(None)
        except Exception:
            h.index = pd.to_datetime(h.index).tz_convert(None)
        candles = [
            {
                'time':  str(idx.date()),
                'open':  round(float(row['Open']),  4),
                'high':  round(float(row['High']),  4),
                'low':   round(float(row['Low']),   4),
                'close': round(float(row['Close']), 4),
                'vol':   int(row['Volume']),
            }
            for idx, row in h.iterrows()
        ]
        return jsonify({'symbol': symbol, 'candles': candles})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === LANCEMENT ===
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
