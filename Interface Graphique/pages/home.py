from dash import html, dcc, Input, Output, State, callback, ctx
import dash
import pandas as pd
import requests
import yfinance as yf
from io import StringIO
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

dash.register_page(__name__, path="/")

_GITHUB_BASE = "https://raw.githubusercontent.com/adam-hassen/stock-auto-update/main/data/articles_sentiment"
_MASTER_URL  = f"{_GITHUB_BASE}/ALL_ARTICLES_MASTER.csv"

_COMPANIES = {
    'AAPL':  'Apple Inc.',
    'MSFT':  'Microsoft',
    'TSLA':  'Tesla',
    'NVDA':  'NVIDIA',
    'GOOGL': 'Alphabet',
    'AMZN':  'Amazon',
    'META':  'Meta',
}

# ==================== SENTIMENT DATA ====================

def _load_articles():
    try:
        resp = requests.get(_MASTER_URL, timeout=10)
        if resp.status_code == 200:
            df = pd.read_csv(StringIO(resp.text))
            df['date_publication'] = pd.to_datetime(df['date_publication'], errors='coerce')
            return df.dropna(subset=['date_publication', 'score_sentiment'])
    except Exception as e:
        print(f"[HOME] Articles indisponibles: {e}")
    return pd.DataFrame()


def _compute_signal(df, ticker):
    empty = {'rec': 'SURVEILLER', 'signal_valid_to': '—', 'horizon_label': '', 'latest_dt': None}
    if df.empty:
        return empty
    col = next((c for c in ['symbol', 'ticker', 'Ticker'] if c in df.columns), None)
    if not col:
        return empty
    df_co = df[df[col] == ticker].copy()
    if df_co.empty:
        return empty
    try:
        df_co['date_publication'] = (
            pd.to_datetime(df_co['date_publication'], errors='coerce', utc=True)
            .dt.tz_localize(None)
        )
        df_co = df_co.dropna(subset=['date_publication'])
        cutoff = datetime.now() - timedelta(days=2)
        recent = df_co[df_co['date_publication'] >= cutoff]
        df_co = recent if not recent.empty else df_co.tail(15)
    except Exception:
        df_co = df_co.tail(15)

    score = (
        float(df_co['score_pondere'].mean()) if 'score_pondere' in df_co.columns
        else float((df_co['score_sentiment'] * df_co['confiance']).mean()) if 'confiance' in df_co.columns
        else float(df_co['score_sentiment'].mean())
    )
    rec = 'ACHETER' if score > 0.15 else 'VENDRE' if score < -0.15 else 'SURVEILLER'
    latest_dt = None
    try:
        latest_dt  = df_co['date_publication'].max()
        oldest_dt  = df_co['date_publication'].min()
        expires_dt = latest_dt + timedelta(hours=48)
        window_h   = max(1, round((latest_dt - oldest_dt).total_seconds() / 3600))
        signal_valid_to = expires_dt.strftime('%d %b à %Hh')
        horizon_label   = f"~{window_h}h de données"
    except Exception:
        signal_valid_to = (datetime.now() + timedelta(days=2)).strftime('%d %b')
        horizon_label   = '~48h'
    return {
        'rec': rec, 'signal_valid_to': signal_valid_to, 'horizon_label': horizon_label,
        'latest_dt': latest_dt.isoformat() if latest_dt is not None else None,
    }


def _get_price(ticker, signal_date=None):
    try:
        hist = yf.Ticker(ticker).history(period="60d", interval="1d")
        if not hist.empty:
            try:
                hist.index = pd.to_datetime(hist.index).tz_localize(None)
            except Exception:
                hist.index = pd.to_datetime(hist.index).tz_convert(None)
            current      = round(float(hist['Close'].iloc[-1]), 2)
            current_date = hist.index[-1].strftime('%d %b').lstrip('0')
            if signal_date:
                target      = pd.Timestamp(signal_date)
                if target.tzinfo:
                    target  = target.tz_localize(None)
                closest_idx = int(abs(hist.index - target).argmin())
                entry       = round(float(hist['Close'].iloc[closest_idx]), 2)
                entry_date  = hist.index[closest_idx].strftime('%d %b').lstrip('0')
            else:
                idx        = -3 if len(hist) >= 3 else -2
                entry      = round(float(hist['Close'].iloc[idx]), 2)
                entry_date = hist.index[idx].strftime('%d %b').lstrip('0')
            return {'entry': entry, 'current': current, 'entry_date': entry_date, 'current_date': current_date}
    except Exception:
        pass
    return {'entry': 0.0, 'current': 0.0, 'entry_date': '', 'current_date': ''}

# ==================== CARD BUILDERS ====================

_REC_CARD  = {'ACHETER': 'home-pred-buy',  'VENDRE': 'home-pred-sell',  'SURVEILLER': 'home-pred-watch'}
_REC_BADGE = {'ACHETER': 'home-pred-rec-buy', 'VENDRE': 'home-pred-rec-sell', 'SURVEILLER': 'home-pred-rec-watch'}
_REC_ICON  = {'ACHETER': 'fas fa-arrow-trend-up', 'VENDRE': 'fas fa-arrow-trend-down', 'SURVEILLER': 'fas fa-minus'}
_TIP_ICON  = {'ACHETER': 'fas fa-circle-up', 'VENDRE': 'fas fa-circle-down', 'SURVEILLER': 'fas fa-circle-pause'}
_TIP_COLOR = {'ACHETER': '#00f0a0', 'VENDRE': '#ff4d6d', 'SURVEILLER': '#f0c040'}
_TIP_TITLE = {
    'ACHETER':   "Bonne nouvelle — c'est le moment d'acheter",
    'VENDRE':    "Attention — signal négatif détecté",
    'SURVEILLER':"Pas encore — attendez un peu",
}


def _sentiment_card(ticker, company, df):
    sig      = _compute_signal(df, ticker)
    prices   = _get_price(ticker, signal_date=sig.get('latest_dt'))
    rec      = sig['rec']
    tip_color = _TIP_COLOR.get(rec, '#f0c040')

    tip_body = {
        'ACHETER':    f"Notre IA a analysé des dizaines d'articles récents sur {company}. Les nouvelles sont positives et les investisseurs réagissent bien. Si tu veux investir, c'est maintenant.",
        'VENDRE':     f"Les dernières actualités autour de {company} sont mauvaises. Notre IA a repéré des signaux inquiétants — le cours risque de baisser. Mieux vaut ne pas investir maintenant.",
        'SURVEILLER': f"Les signaux sont encore flous pour {company}. Notre IA n'est pas assez sûre pour te donner un conseil clair. Patiente encore un peu et reviens bientôt.",
    }.get(rec, '')

    return html.Div(className=f"home-pred-card {_REC_CARD.get(rec, 'home-pred-watch')}", children=[
        html.Div(className="home-pred-top", children=[
            html.Div([
                html.Div(ticker,  className="home-pred-ticker"),
                html.Div(company, className="home-pred-company"),
            ]),
            html.Span(
                [html.I(className=_REC_ICON.get(rec, '')), f"  {rec}"],
                className=f"home-pred-rec {_REC_BADGE.get(rec, 'home-pred-rec-watch')}",
            ),
        ]),
        html.Div(className="home-pred-validity", children=[
            html.I(className="fas fa-clock"),
            html.Span(f"Conseil valable jusqu'au {sig['signal_valid_to']}"),
            html.Span(sig['horizon_label'], className="home-pred-horizon"),
        ]),
        html.A(
            [html.I(className="fas fa-chart-line"), "  Calculer mon investissement"],
            href="/mon-suivi",
            className="home-pred-btn",
        ),
        html.Div(className="home-pred-tooltip", children=[
            html.Div(className="home-pred-tooltip-inner", children=[
                html.I(className=_TIP_ICON.get(rec, 'fas fa-circle-info'),
                       style={"fontSize": "2rem", "color": tip_color, "marginBottom": "10px"}),
                html.Div(_TIP_TITLE.get(rec, ''), className="home-pred-tooltip-title", style={"color": tip_color}),
                html.Div(f"{company} — {ticker}", className="home-pred-tooltip-company"),
                html.P(tip_body, className="home-pred-tooltip-body"),
                html.Div(className="home-pred-tooltip-prices", children=[
                    html.Span(
                        f"Le {prices['entry_date']} : ${prices['entry']:,.2f}" if prices['entry_date'] else f"Conseil : ${prices['entry']:,.2f}",
                        className="home-pred-tooltip-price-item"
                    ),
                    html.I(className="fas fa-arrow-right", style={"color": "#4a5c7a", "fontSize": "0.7rem"}),
                    html.Span(
                        f"Auj. ({prices['current_date']}) : ${prices['current']:,.2f}" if prices['current_date'] else f"Maintenant : ${prices['current']:,.2f}",
                        className="home-pred-tooltip-price-item"
                    ),
                ]),
                html.Div(className="home-pred-tooltip-footer", children=[
                    html.I(className="fas fa-clock"),
                    html.Span(f" Valable jusqu'au {sig['signal_valid_to']}"),
                ]),
            ]),
        ]),
    ])


def _lstm_card(ticker, company, pred):
    if pred is None:
        rec = 'SURVEILLER'
        return_pct      = None
        current_price   = None
        predicted_price = None
    else:
        rec             = pred['signal']
        return_pct      = pred['return_pct']
        current_price   = pred['current_price']
        predicted_price = pred['predicted_price']

    tip_color  = _TIP_COLOR.get(rec, '#f0c040')
    ret_str    = f"{return_pct:+.3f}%" if return_pct is not None else "N/A"
    direction  = "monter" if rec == 'ACHETER' else "baisser"
    tip_body   = (
        f"Notre modèle BiLSTM a analysé les 60 derniers jours de variation de prix de {company}. "
        f"Il prédit que le cours va {direction} de {abs(return_pct):.3f}% dans les prochains jours. "
        f"Ce signal est basé uniquement sur l'historique des prix, sans tenir compte des actualités."
    ) if return_pct is not None else f"Données insuffisantes pour {company} — le modèle n'a pas pu produire de signal."

    return html.Div(className=f"home-pred-card {_REC_CARD.get(rec, 'home-pred-watch')}", children=[
        html.Div(className="home-pred-top", children=[
            html.Div([
                html.Div(ticker,  className="home-pred-ticker"),
                html.Div(company, className="home-pred-company"),
            ]),
            html.Span(
                [html.I(className=_REC_ICON.get(rec, '')), f"  {rec}"],
                className=f"home-pred-rec {_REC_BADGE.get(rec, 'home-pred-rec-watch')}",
            ),
        ]),
        # Validity line — shows predicted return instead of date
        html.Div(className="home-pred-validity", children=[
            html.I(className="fas fa-brain"),
            html.Span("Rendement prédit par le modèle LSTM"),
            html.Span(ret_str, className="home-pred-horizon"),
        ]),
        html.A(
            [html.I(className="fas fa-chart-line"), "  Calculer mon investissement"],
            href="/mon-suivi",
            className="home-pred-btn",
        ),
        html.Div(className="home-pred-tooltip", children=[
            html.Div(className="home-pred-tooltip-inner", children=[
                html.I(className=_TIP_ICON.get(rec, 'fas fa-circle-info'),
                       style={"fontSize": "2rem", "color": tip_color, "marginBottom": "10px"}),
                html.Div(_TIP_TITLE.get(rec, ''), className="home-pred-tooltip-title", style={"color": tip_color}),
                html.Div(f"{company} — {ticker}", className="home-pred-tooltip-company"),
                html.P(tip_body, className="home-pred-tooltip-body"),
                html.Div(className="home-pred-tooltip-prices", children=[
                    html.Span(
                        f"Prix actuel : ${current_price:,.2f}" if current_price else "Prix actuel : N/A",
                        className="home-pred-tooltip-price-item"
                    ),
                    html.I(className="fas fa-arrow-right", style={"color": "#4a5c7a", "fontSize": "0.7rem"}),
                    html.Span(
                        f"Prédit : ${predicted_price:,.2f}" if predicted_price else "Prédit : N/A",
                        className="home-pred-tooltip-price-item"
                    ),
                ]),
                html.Div(className="home-pred-tooltip-footer", children=[
                    html.I(className="fas fa-microchip"),
                    html.Span(f" Basé sur 60 jours d'historique · {ret_str}"),
                ]),
            ]),
        ]),
    ])

# ==================== LAYOUT ====================

layout = html.Div([
    dcc.Store(id="home-pred-mode", data="sentiment"),
    dcc.Interval(id="home-init", interval=300, n_intervals=0, max_intervals=1),

    # ── Hero ──
    html.Div(className="hero", children=[
        html.H1("Bienvenue dans la Galaxie des Marchés Futuristes"),
    ]),

    # ── Recommandations IA ──
    html.Div(className="home-pred-section", children=[
        html.Div(className="home-pred-header", children=[
            html.Div(className="home-pred-live-badge", children=[
                html.Span(className="home-pred-pulse"),
                "CONSEILS IA EN DIRECT",
            ]),
            html.H2("Que faire aujourd'hui ?", className="home-pred-title"),
            html.P(
                "Notre IA lit les actualités financières pour vous dire clairement si vous devriez acheter ou vendre — sans jargon.",
                className="home-pred-subtitle",
            ),
        ]),

        # ── Mode toggle ──
        html.Div(className="home-mode-bar", children=[
            html.Button(
                [html.I(className="fas fa-newspaper"), "  Analyse des actualités"],
                id="home-btn-sentiment",
                className="home-mode-btn home-mode-active",
                n_clicks=0,
            ),
            html.Button(
                [html.I(className="fas fa-brain"), "  Modèle LSTM (prix)"],
                id="home-btn-lstm",
                className="home-mode-btn",
                n_clicks=0,
            ),
        ]),

        dcc.Loading(
            type="dot",
            color="#00f0ff",
            children=html.Div(
                id="home-pred-grid",
                className="home-pred-grid",
                children=html.Div(
                    [html.I(className="fas fa-circle-notch fa-spin"), "  Chargement des conseils..."],
                    className="home-pred-loading",
                ),
            ),
        ),
    ]),

    # ── À propos ──
    html.Div(className="about-section", children=[
        html.Div(className="about-container", children=[
            html.Div(className="about-header", children=[
                html.H2("À propos de nous", className="about-title"),
                html.Div(className="neon-underline"),
            ]),
            html.P(
                "Notre plateforme boursière futuriste combine innovation, intelligence artificielle et visualisation avancée "
                "pour offrir une expérience unique d'analyse financière. Inspirée par la précision et l'esthétique du monde spatial, "
                "notre mission est de guider les investisseurs vers une compréhension plus claire et plus intuitive des marchés.",
                className="about-text",
            ),
            html.Div(className="values-grid", children=[
                html.Div(className="value-card", children=[
                    html.I(className="fas fa-rocket", style={"fontSize": "2.2rem", "marginBottom": "12px", "color": "var(--accent)"}),
                    html.H4("Innovation"),
                    html.P("Technologies de pointe pour demain."),
                ]),
                html.Div(className="value-card", children=[
                    html.I(className="fas fa-brain", style={"fontSize": "2.2rem", "marginBottom": "12px", "color": "var(--accent-2)"}),
                    html.H4("Intelligence Artificielle"),
                    html.P("Prédictions précises, analyses automatisées."),
                ]),
                html.Div(className="value-card", children=[
                    html.I(className="fas fa-shield-alt", style={"fontSize": "2.2rem", "marginBottom": "12px", "color": "#00f0ff"}),
                    html.H4("Sécurité"),
                    html.P("Données chiffrées, confiance absolue."),
                ]),
                html.Div(className="value-card", children=[
                    html.I(className="fas fa-eye", style={"fontSize": "2.2rem", "marginBottom": "12px", "color": "#8be9ff"}),
                    html.H4("Vision Futuriste"),
                    html.P("Une interface inspirée de l'espace."),
                ]),
            ]),
        ]),
    ]),

    # ── Contact ──
    html.Div(id="contact-section", className="contact-section", children=[
        html.Div(className="contact-container", children=[
            html.Div(className="contact-card", children=[
                html.Div(className="contact-header", children=[
                    html.H2("Contact & Réseaux", className="contact-title"),
                    html.Div(className="neon-line"),
                ]),
                html.Div(className="contact-body", children=[
                    html.Div(className="info-line", children=[html.I(className="fas fa-envelope"), html.Span("contact.ETU@univ-lemans.fr")]),
                    html.Div(className="info-line", children=[html.I(className="fas fa-phone"),    html.Span("+33 7 56 32 98 10")]),
                    html.Div(className="info-line", children=[
                        html.I(className="fas fa-location-dot"),
                        html.Span(["ENSIM, 1 Rue Aristote", html.Br(), "72000 Le Mans, France"]),
                    ]),
                    html.Div(className="social-icons", children=[
                        html.A(html.I(className="fab fa-instagram"),  href="https://instagram.com", target="_blank"),
                        html.A(html.I(className="fab fa-facebook-f"), href="https://facebook.com",  target="_blank"),
                        html.A(html.I(className="fab fa-linkedin-in"),href="https://linkedin.com",  target="_blank"),
                        html.A(html.I(className="fab fa-x-twitter"),  href="https://x.com",         target="_blank"),
                    ]),
                ]),
            ]),
            html.Div(className="map-container", children=[
                html.Iframe(
                    src="https://maps.google.com/maps?q=ENSIM+Ecole+Nationale+Superieure+Ingenieurs+Le+Mans+1+Rue+Aristote+72000&z=17&output=embed",
                    width="100%", height="100%",
                    style={"border": "0", "borderRadius": "16px"},
                    referrerPolicy="no-referrer-when-downgrade",
                ),
            ]),
        ]),
    ]),
])

# ==================== CALLBACKS ====================

@callback(
    Output("home-btn-sentiment", "className"),
    Output("home-btn-lstm",      "className"),
    Output("home-pred-mode",     "data"),
    Input("home-btn-sentiment",  "n_clicks"),
    Input("home-btn-lstm",       "n_clicks"),
    prevent_initial_call=True,
)
def toggle_mode(n_sent, n_lstm):
    active = "home-mode-btn home-mode-active"
    normal = "home-mode-btn"
    if ctx.triggered_id == "home-btn-lstm":
        return normal, active, "lstm"
    return active, normal, "sentiment"


@callback(
    Output("home-pred-grid", "children"),
    Input("home-init",       "n_intervals"),
    Input("home-pred-mode",  "data"),
    State("session-store",   "data"),
)
def render_home_predictions(_, mode, session):
    if not session or not session.get("email"):
        return html.Div(className="home-pred-login-wall", children=[
            html.Div(className="home-pred-login-icon", children=html.I(className="fas fa-lock")),
            html.H3("Connectez-vous pour voir les conseils IA", className="home-pred-login-title"),
            html.P(
                "Nos recommandations en temps réel sont réservées aux membres. "
                "Créez un compte gratuitement pour y accéder.",
                className="home-pred-login-sub",
            ),
            html.Div(className="home-pred-login-btns", children=[
                html.A([html.I(className="fas fa-right-to-bracket"), "  Se connecter"],
                       href="/login", className="home-pred-login-btn-primary"),
                html.A([html.I(className="fas fa-user-plus"), "  Créer un compte"],
                       href="/signup", className="home-pred-login-btn-ghost"),
            ]),
        ])

    mode = mode or "sentiment"

    if mode == "lstm":
        from services.lstm_service import predict as lstm_predict

        def _fetch(ticker):
            return ticker, lstm_predict(ticker)

        with ThreadPoolExecutor(max_workers=7) as ex:
            futures  = {ex.submit(_fetch, t): t for t in _COMPANIES}
            preds    = {}
            for f in as_completed(futures):
                ticker, result = f.result()
                preds[ticker] = result

        return [_lstm_card(ticker, company, preds.get(ticker))
                for ticker, company in _COMPANIES.items()]

    # ── Sentiment mode (défaut) ──
    df = _load_articles()
    return [_sentiment_card(ticker, company, df)
            for ticker, company in _COMPANIES.items()]
