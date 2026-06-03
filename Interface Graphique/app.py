import os
# Doit être défini AVANT tout import de tensorflow/keras/protobuf
os.environ.setdefault('PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION', 'python')
os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')

import dash
from dash import dcc, html, Input, Output, State
import yfinance as yf
import pandas as pd
from flask import jsonify, request as flask_request, Response, stream_with_context
import requests
from bs4 import BeautifulSoup
from services.database import init_db
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

# Charger les variables d'environnement depuis .env (chemin absolu)
import os as _os
try:
    from dotenv import load_dotenv
    _env_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), ".env")
    load_dotenv(dotenv_path=_env_path, override=True)
except ImportError:
    pass  # python-dotenv non installé, les env vars système seront utilisées

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

# Désactiver le cache navigateur pour les assets (force rechargement chatbot.js à chaque fois)
app.server.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

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
    dcc.Store(id="demo-seen-store", storage_type="session"),
    dcc.Interval(id="interval-component", interval=5*60*1000, n_intervals=0),

    # === TICKER EN HAUT (z-index: 3000) ===
    html.Div(id="ticker-container"),
    
    # === NAVBAR (z-index: 2000) ===
    html.Div(id="navbar-container"),
    
    # === PAGE CONTENT ===
    dash.page_container,

    # === CHATBOT WIDGET ===
    html.Button(
        html.I(className="fa-solid fa-robot"),
        id="chatbot-toggle",
        title="Assistant IA"
    ),
    html.Div(
        id="chatbot-panel",
        className="chatbot-hidden",
        children=[

            # ── Header ──────────────────────────────────────────
            html.Div(id="chatbot-header", children=[
                html.Div(className="chatbot-header-left", children=[
                    html.Div(className="chatbot-avatar", children=[
                        html.I(className="fa-solid fa-robot")
                    ]),
                    html.Div(className="chatbot-header-info", children=[
                        html.Span("Conseiller IA", className="chatbot-header-name"),
                        html.Div(className="chatbot-header-status", children=[
                            html.Span(className="chatbot-status-dot"),
                            html.Span("En ligne"),
                        ]),
                    ]),
                ]),
                html.Div(className="chatbot-header-actions", children=[
                    html.Button(
                        html.I(className="fa-solid fa-clock-rotate-left"),
                        id="chatbot-history-btn",
                        title="Historique des conversations"
                    ),
                    html.Button(
                        html.I(className="fa-solid fa-pen-to-square"),
                        id="chatbot-new-btn",
                        title="Nouvelle conversation"
                    ),
                    html.Button(
                        html.I(className="fa-solid fa-xmark"),
                        id="chatbot-close",
                        title="Fermer"
                    ),
                ]),
            ]),

            # ── Vue Chat (par défaut) ────────────────────────────
            html.Div(id="chatbot-chat-view", children=[
                html.Div(id="chatbot-messages", children=[
                    html.Div(
                        id="chatbot-welcome",
                        className="chatbot-msg chatbot-msg-bot",
                        children=[
                            html.Div(className="chatbot-bubble", children=[
                                html.Strong("Bonjour !"),
                                html.Br(),
                                "Je suis votre assistant IA. Posez-moi vos questions sur la plateforme, les modèles de prédiction ou les actions disponibles."
                            ])
                        ]
                    )
                ]),
                html.Div(id="chatbot-input-row", children=[
                    html.Button(
                        html.I(className="fa-solid fa-microphone"),
                        id="chatbot-mic",
                        title="Parler"
                    ),
                    html.Textarea(
                        id="chatbot-input",
                        placeholder="Posez votre question ou parlez…",
                        rows=1
                    ),
                    html.Button(
                        html.I(className="fa-solid fa-paper-plane"),
                        id="chatbot-send",
                        title="Envoyer"
                    ),
                ]),
            ]),

            # ── Vue Historique (cachée par défaut) ───────────────
            html.Div(id="chatbot-history-view", className="cb-view-hidden", children=[
                html.Div(id="chatbot-history-header", children=[
                    html.Span("Conversations", className="cb-hist-title"),
                    html.Button(
                        [html.I(className="fa-solid fa-plus"), " Nouvelle"],
                        id="chatbot-new-btn2",
                        className="cb-new-btn"
                    ),
                ]),
                html.Div(id="chatbot-history-list"),
            ]),

        ]
    ),
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
    def nav_cls(href):
        if href == "/":
            return "nav-link active" if pathname == "/" else "nav-link"
        return "nav-link active" if pathname.startswith(href) else "nav-link"

    nav_links = [
        dcc.Link("Accueil",     href="/",            className=nav_cls("/")),
        dcc.Link("Témoignages", href="/temoignages", className=nav_cls("/temoignages")),
    ]

    if not is_logged_in:
        nav_links.append(dcc.Link("Demo", href="/demo", className=nav_cls("/demo")))

    if is_logged_in:
        nav_links.extend([
            dcc.Link("Marchés",    href="/actions_page", className=nav_cls("/actions_page")),
            dcc.Link("Analyse",    href="/analysis",     className=nav_cls("/analysis")),
            dcc.Link("Mon Suivi",  href="/mon-suivi",    className=nav_cls("/mon-suivi")),
            dcc.Link("Mon Profil", href="/profil",       className=nav_cls("/profil")),
        ])

        if session and session.get("is_admin"):
            print(f"[ADMIN] Lien admin ajouté pour {session.get('email')}")
            nav_links.append(dcc.Link("Admin", href="/admin", className=nav_cls("/admin")))

        nav_links.append(html.Button("Déconnexion", id="logout-btn", className="nav-link"))

    else:
        nav_links.extend([
            dcc.Link("Connexion",   href="/login",  className=nav_cls("/login")),
            dcc.Link("Inscription", href="/signup", className=nav_cls("/signup")),
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
    Output("demo-seen-store", "data", allow_duplicate=True),
    Input("url", "pathname"),
    State("session-store", "data"),
    State("demo-seen-store", "data"),
    prevent_initial_call=True
)
def redirect_if_not_logged(pathname, session, demo_seen):
    # Pages protégées → login si non connecté
    if pathname in PROTECTED_PAGES and session is None:
        return "/login", dash.no_update
    # Première visite sur "/" sans compte → démo (une seule fois par session)
    if pathname == "/" and session is None and not demo_seen:
        return "/demo", True
    return dash.no_update, dash.no_update

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


# === API PREVIEW (Open Graph tags for article hover card) ===
_preview_cache = {}

@app.server.route('/api/preview')
def api_preview():
    url = flask_request.args.get('url', '')
    if not url or not url.startswith(('http://', 'https://')):
        return jsonify({'error': 'Invalid URL'}), 400

    if url in _preview_cache:
        return jsonify(_preview_cache[url])

    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resp = requests.get(url, timeout=5, headers=headers, allow_redirects=True)
        soup = BeautifulSoup(resp.text, 'html.parser')

        def og(prop):
            tag = soup.find('meta', property=f'og:{prop}')
            return tag['content'].strip() if tag and tag.get('content') else None

        def meta_name(name):
            tag = soup.find('meta', attrs={'name': name})
            return tag['content'].strip() if tag and tag.get('content') else None

        title = (og('title') or meta_name('title') or
                 (soup.title.string.strip() if soup.title else '') or '')
        image = og('image') or meta_name('twitter:image') or ''
        description = og('description') or meta_name('description') or ''
        site_name = og('site_name') or ''

        result = {
            'title':       title[:200],
            'image':       image,
            'description': description[:300],
            'site_name':   site_name,
        }
        if len(_preview_cache) < 500:
            _preview_cache[url] = result

        resp_json = jsonify(result)
        resp_json.headers['Cache-Control'] = 'max-age=3600'
        return resp_json
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === API PRICES (parallel fetch for all symbols) ===
def _fetch_price(sym):
    try:
        h = yf.Ticker(sym).history(period='5d', interval='1d')
        if h.empty:
            return sym, None
        try:
            h.index = pd.to_datetime(h.index).tz_localize(None)
        except Exception:
            h.index = pd.to_datetime(h.index).tz_convert(None)
        price = float(h['Close'].iloc[-1])
        prev  = float(h['Close'].iloc[-2]) if len(h) >= 2 else price
        return sym, {'price': round(price, 2), 'pct': round((price - prev) / prev * 100, 2)}
    except Exception:
        return sym, None

@app.server.route('/api/prices')
def api_prices():
    results = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(_fetch_price, sym): sym for sym in _ALLOWED}
        for future in as_completed(futures):
            sym, data = future.result()
            results[sym] = data
    return jsonify(results)


# === API TRANSCRIPTION VOCALE (Groq Whisper) ===
@app.server.route('/api/transcribe', methods=['POST'])
def api_transcribe():
    from groq import Groq

    audio_file = flask_request.files.get('audio')
    if not audio_file:
        return jsonify({'error': 'Aucun fichier audio'}), 400

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return jsonify({'error': 'Clé API non configurée'}), 500

    try:
        client = Groq(api_key=api_key)
        audio_bytes = audio_file.read()
        transcription = client.audio.transcriptions.create(
            file=("audio.webm", audio_bytes),
            model="whisper-large-v3-turbo",
            language="fr",
            response_format="text",
        )
        return jsonify({'text': str(transcription).strip()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# === API INVESTISSEMENT CHATBOT ===
@app.server.route('/api/chat-invest', methods=['POST'])
def api_chat_invest():
    from services.database import get_connection

    data    = flask_request.get_json(force=True, silent=True) or {}
    email   = data.get('email', '').strip()
    symbol  = data.get('symbol', '').strip().upper()
    model   = data.get('model', 'sentiment').strip().lower()
    action  = data.get('action', 'ACHETER').strip().upper()
    amount  = float(data.get('amount', 0) or 0)

    print(f"[chat-invest] REÇU → email={email!r} symbol={symbol!r} model={model!r} action={action!r} amount={amount}")

    ALLOWED_SYMBOLS = {'AAPL','MSFT','TSLA','NVDA','GOOGL','AMZN','META','BTC-USD'}
    ALLOWED_MODELS  = {'sentiment','lstm','transformer'}

    if not email or symbol not in ALLOWED_SYMBOLS or model not in ALLOWED_MODELS or amount <= 0:
        print(f"[chat-invest] VALIDATION ÉCHOUÉE — email={email!r} symbol={symbol!r} model={model!r} amount={amount}")
        return jsonify({'error': 'Données invalides', 'debug': {'email': email, 'symbol': symbol, 'model': model, 'amount': amount}}), 400

    try:
        # Prix actuel
        h = yf.Ticker(symbol).history(period='2d', interval='1d')
        price = float(h['Close'].iloc[-1]) if not h.empty else 0.0

        # Mapper action → directions compatibles avec Mon Suivi
        pred_dir   = 'up'   if action == 'ACHETER' else 'down'
        actual_dir = 'up'   if action == 'ACHETER' else 'down'

        conn = get_connection()
        conn.execute("""
            INSERT INTO user_trades
                (user_email, symbol, entry_price, quantity,
                 prediction_direction, actual_direction, pnl, pnl_percentage,
                 model_type, status)
            VALUES (?, ?, ?, ?, ?, ?, 0, 0, ?, 'open')
        """, (email, symbol, price, amount, pred_dir, actual_dir, model))
        conn.commit()
        conn.close()

        print(f"[chat-invest] Trade sauvegardé: {email} | {symbol} | {model} | {action} | {amount}€ à {price}$")

        return jsonify({
            'success': True,
            'symbol':  symbol,
            'price':   round(price, 2),
            'amount':  amount,
            'action':  action,
            'model':   model,
        })
    except Exception as e:
        print(f"[chat-invest] Erreur: {e}")
        return jsonify({'error': str(e)}), 500


# === API COMPARAISON MODÈLES PAR ACTION ===
@app.server.route('/api/model-compare', methods=['GET'])
def api_model_compare():
    from services.database import get_connection

    email  = flask_request.args.get('email', '').strip()
    symbol = flask_request.args.get('symbol', '').strip().upper()

    if not email or not symbol:
        return jsonify({'error': 'Missing params'}), 400

    MODEL_LABELS = {'lstm': 'LSTM', 'transformer': 'Transformer', 'sentiment': 'Actualités'}

    try:
        conn = get_connection()
        # Résumé par modèle
        rows = conn.execute("""
            SELECT model_type,
                   COUNT(*) as trades,
                   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                   COALESCE(SUM(pnl), 0) as total_pnl,
                   COALESCE(AVG(pnl_percentage), 0) as avg_pct
            FROM user_trades
            WHERE user_email = ? AND symbol = ? AND status = 'closed'
            GROUP BY model_type
        """, (email, symbol)).fetchall()

        models = {}
        for model_type, trades, wins, total_pnl, avg_pct in rows:
            # Derniers trades de ce modèle
            recent = conn.execute("""
                SELECT entry_date, prediction_direction, quantity, pnl, pnl_percentage
                FROM user_trades
                WHERE user_email = ? AND symbol = ? AND model_type = ? AND status = 'closed'
                ORDER BY entry_date DESC LIMIT 5
            """, (email, symbol, model_type)).fetchall()

            models[model_type] = {
                'label':     MODEL_LABELS.get(model_type, model_type),
                'trades':    trades,
                'wins':      wins,
                'losses':    trades - wins,
                'win_rate':  round(wins / trades * 100, 1) if trades > 0 else 0.0,
                'total_pnl': round(total_pnl, 2),
                'avg_pct':   round(avg_pct, 2),
                'recent':    [
                    {
                        'date':    str(r[0])[:10],
                        'signal':  r[1],
                        'amount':  r[2] or 0,
                        'pnl':     round(r[3] or 0, 2),
                        'pnl_pct': round(r[4] or 0, 2),
                    }
                    for r in recent
                ],
            }
        conn.close()

        best_model = None
        if models:
            best_model = max(models.items(), key=lambda x: x[1]['total_pnl'])[0]

        return jsonify({'symbol': symbol, 'models': models, 'best_model': best_model})
    except Exception as e:
        print(f"[model-compare] Erreur: {e}")
        return jsonify({'error': str(e)}), 500


# === API COMPARAISON MODÈLES — SIMULATION BACKTESTS ===
@app.server.route('/api/backtest-compare', methods=['GET'])
def api_backtest_compare():
    symbol = flask_request.args.get('symbol', '').strip().upper()
    if not symbol:
        return jsonify({'error': 'Missing symbol'}), 400

    START = 500.0
    DAYS  = 180

    def _run_lstm():
        try:
            from pages.mon_suivi import _run_backtest_lstm
            return 'lstm', _run_backtest_lstm(symbol, start_amount=START, days=DAYS)
        except Exception as e:
            print(f"[backtest-compare] lstm {symbol}: {e}")
            return 'lstm', None

    def _run_transformer():
        try:
            from services.transformer_service import predict_backtest as _bt
            return 'transformer', _bt(symbol, start_amount=START, days=DAYS)
        except Exception as e:
            print(f"[backtest-compare] transformer {symbol}: {e}")
            return 'transformer', None

    def _run_sentiment():
        try:
            from pages.mon_suivi import _run_backtest
            return 'sentiment', _run_backtest(symbol, start_amount=START, days=DAYS)
        except Exception as e:
            print(f"[backtest-compare] sentiment {symbol}: {e}")
            return 'sentiment', None

    def _ds(arr, n=30):
        if not arr or len(arr) <= n:
            return [round(v, 2) for v in arr]
        step = len(arr) / n
        pts = [arr[int(i * step)] for i in range(n)] + [arr[-1]]
        return [round(v, 2) for v in pts]

    results = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = [ex.submit(_run_lstm), ex.submit(_run_transformer), ex.submit(_run_sentiment)]
        for f in as_completed(futures):
            key, bt = f.result()
            if bt:
                results[key] = {
                    'label':      {'lstm': 'LSTM', 'transformer': 'Transformer', 'sentiment': 'Actualités'}[key],
                    'start':      START,
                    'final':      bt['final_value'],
                    'return_pct': bt['total_return'],
                    'bh_final':   round(bt['buy_hold'][-1], 2) if bt.get('buy_hold') else START,
                    'bh_return':  bt['buy_hold_return'],
                    'n_trades':   bt['n_trades'],
                    'wins':       bt['wins'],
                    'losses':     bt['losses'],
                    'win_rate':   bt['win_rate'],
                    'start_date': bt['start_date'],
                    'series':     _ds(bt.get('portfolio', [])),
                    'bh_series':  _ds(bt.get('buy_hold', [])),
                }

    if not results:
        return jsonify({'error': f'Données insuffisantes pour {symbol}'}), 404

    best = max(results.items(), key=lambda x: x[1]['return_pct'])[0]
    return jsonify({'symbol': symbol, 'models': results, 'best_model': best, 'start': START})


# === API DÉTECTION INVESTISSEMENT (post-streaming, fiable) ===
@app.server.route('/api/chat-detect-invest', methods=['POST'])
def api_chat_detect_invest():
    """
    Après le streaming, vérifie si la conversation contient un investissement à enregistrer.
    Retourne {"invest": {...}} ou {"invest": null}.
    Utilise un prompt dédié à l'extraction JSON — beaucoup plus fiable que le marqueur inline.
    """
    import json as _json
    from groq import Groq

    data       = flask_request.get_json(force=True, silent=True) or {}
    messages   = data.get('messages', [])[-6:]   # derniers messages seulement

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return jsonify({'invest': None})

    EXTRACT_PROMPT = """Tu es un extracteur JSON. Analyse le dernier message de l'utilisateur et extrait les données d'un investissement à enregistrer.

MAPPINGS OBLIGATOIRES — noms d'entreprises → symboles boursiers :
Apple / AAPL → "AAPL"
Microsoft / MSFT → "MSFT"
Tesla / TSLA → "TSLA"
Nvidia / NVDA → "NVDA"
Google / Alphabet / GOOGL → "GOOGL"
Amazon / AMZN → "AMZN"
Meta / Facebook / META → "META"
Bitcoin / BTC / crypto → "BTC-USD"

MAPPINGS MODÈLES :
LSTM / LST / lstm / réseau de neurones / prix → "lstm"
Transformer / transformeur / hybride → "transformer"
Sentiment / actualités / actualites / news → "sentiment"

Si l'utilisateur dit qu'il a investi / mis de l'argent / suivi un conseil / acheté / vendu, extrais :
{"symbol":"AAPL","model":"lstm","action":"ACHETER","amount":500}

RÈGLES :
- action = "ACHETER" si l'utilisateur a acheté ou suivi un conseil haussier, "VENDRE" sinon
- amount = le montant en euros (nombre seul, ex: 500)
- Réponds UNIQUEMENT avec le JSON brut, rien d'autre
- Si une info manque ou si ce n'est PAS une intention d'enregistrement : réponds null"""

    try:
        client = Groq(api_key=api_key)
        resp   = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": EXTRACT_PROMPT}] + messages,
            max_tokens=80,
            stream=False,
            temperature=0,
        )
        raw = (resp.choices[0].message.content or "").strip()
        print(f"[detect-invest] raw='{raw}'")
        if raw == "null" or not raw.startswith("{"):
            return jsonify({"invest": None})
        invest = _json.loads(raw)
        # Validation
        ALLOWED_SYMBOLS = {"AAPL","MSFT","TSLA","NVDA","GOOGL","AMZN","META","BTC-USD"}
        ALLOWED_MODELS  = {"sentiment","lstm","transformer"}
        if (invest.get("symbol") in ALLOWED_SYMBOLS
                and invest.get("model","").lower() in ALLOWED_MODELS
                and invest.get("action") in {"ACHETER","VENDRE"}
                and float(invest.get("amount", 0) or 0) > 0):
            invest["model"] = invest["model"].lower()
            return jsonify({"invest": invest})
        return jsonify({"invest": None})
    except Exception as e:
        print(f"[detect-invest] erreur: {e}")
        return jsonify({"invest": None})


# === API CHATBOT (SSE streaming) ===
@app.server.route('/api/chat', methods=['POST'])
def api_chat():
    from services.chat_service import stream_chat
    import json

    data = flask_request.get_json(force=True, silent=True) or {}
    messages = data.get('messages', [])

    # Validation basique
    if not isinstance(messages, list):
        return jsonify({'error': 'Invalid payload'}), 400

    def generate():
        try:
            for chunk in stream_chat(messages):
                payload = json.dumps({'text': chunk}, ensure_ascii=False)
                yield f"data: {payload}\n\n"
        except Exception as e:
            payload = json.dumps({'error': str(e)}, ensure_ascii=False)
            yield f"data: {payload}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        content_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )


# === LANCEMENT ===
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8050))
    debug = os.environ.get("DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
