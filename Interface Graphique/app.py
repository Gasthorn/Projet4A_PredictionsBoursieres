import dash
from dash import dcc, html, Input, Output
import yfinance as yf

# === INITIALISATION ===
app = dash.Dash(__name__,use_pages=True, suppress_callback_exceptions=True, external_stylesheets=[  "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css" ])
app.title = "TradeLux - Plateforme de Trading"

# === TICKERS ===
TICKERS = {
    "BTC-USD": "BTC/USD",
    "ETH-USD": "ETH/USD",
    "^IXIC": "NASDAQ",
    "AAPL": "AAPL",
    "GOOGL": "GOOGL"
}

# === RÉCUPÉRATION DONNÉES ===
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
                data.append({"label": label, "value": f"{current:,.2f}", "change": change_str, "class": change_class})
            else:
                data.append({"label": label, "value": "N/A", "change": "down 0.0%", "class": "down"})
        except:
            data.append({"label": label, "value": "ERR", "change": "down 0.0%", "class": "down"})
    return data

# === LAYOUT COMPLET (TOUT DEDANS) ===
app.layout = html.Div([
    # Fond animé
    html.Div(className="trade-bg"),
    html.Div(className="grid-lines"),
    html.Div([html.Div(className="particle") for _ in range(40)]),

    # === OBLIGATOIRE : dcc.Interval + dcc.Location ===
    dcc.Location(id="url", refresh=False),
    dcc.Interval(id="interval-component", interval=5*60*1000, n_intervals=0, disabled=True),

    # Ticker
    html.Div(id="ticker-container"),

    # Navbar
    html.Div(id="navbar", className="navbar", children=[
        html.Div(className="navbar-left", children=[
            html.Img(src="/assets/logo.png", className="logo", alt="Logo")
        ]),
        html.Div(className="nav-links", children=[
            dcc.Link("Accueil", href="/", className="nav-link"),
            dcc.Link("Marchés", href="/actions_page", className="nav-link"),
            dcc.Link("Analyse", href="/analysis", className="nav-link"),
            html.A("Contact", href="#contact-section", className="nav-link", **{"data-scroll": ""}),
        ]),
    ]),

    # Contenu principal avec animation
    html.Div(id="page-content", className="page-content", children=[
        html.Div(id="page-transition", children=dash.page_container)
    ])
])

# === CALLBACK PRINCIPAL : TOUT CONTRÔLE ===
@app.callback(
    Output("ticker-container", "children"),
    Output("interval-component", "disabled"),
    Output("navbar", "className"),
    Output("page-content", "className"),
    Output("page-transition", "className"),
    Input("url", "pathname")
)
def control_layout(pathname):
    if pathname == "/":
        return (
            html.Div(className="ticker-wrap", children=[
                html.Div(id="ticker-inner", className="ticker-inner")
            ]),
            False,  # interval activé
            "navbar with-ticker",
            "page-content with-ticker",
            "page-fade-in"
        )
    else:
        return (
            "",  # pas de ticker
            True,  # interval désactivé
            "navbar no-ticker",
            "page-content no-ticker",
            "page-fade-in"
        )

# === CALLBACK TICKER : FLUIDE INFINI ===
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
        for symbol, d in zip(TICKERS.keys(), data)
    ]
    ticker_set = html.Div(className="ticker-set", children=items)
    return [ticker_set, ticker_set]  # 2x → boucle parfaite 

# === LANCEMENT ===
if __name__ == "__main__":
    app.run( port=7860, debug=True)