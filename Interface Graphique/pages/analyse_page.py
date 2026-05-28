"""
Page Analyse - ENSIM
Dashboard d'analyse de sentiment - Theme ENSIM (cyan neon glassmorphism)
"""

import dash
from dash import dcc, html, Input, Output, State, callback, no_update
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import datetime, timedelta
import requests
from io import StringIO

dash.register_page(__name__, path="/analysis", name="Analyse")

# ==================== CONFIG ====================
GITHUB_BASE = "https://raw.githubusercontent.com/adam-hassen/stock-auto-update/main/data/articles_sentiment"
MASTER_URL = f"{GITHUB_BASE}/ALL_ARTICLES_MASTER.csv"

COMPANIES = {
    'AAPL': {'name': 'Apple Inc.', 'sector': 'Technology'},
    'MSFT': {'name': 'Microsoft Corp.', 'sector': 'Technology'},
    'TSLA': {'name': 'Tesla Inc.', 'sector': 'Automotive'},
    'NVDA': {'name': 'NVIDIA Corp.', 'sector': 'Semiconductors'},
    'GOOGL': {'name': 'Alphabet Inc.', 'sector': 'Technology'},
    'AMZN': {'name': 'Amazon.com', 'sector': 'E-commerce'},
    'META': {'name': 'Meta Platforms', 'sector': 'Social Media'},
}

# ==================== DATA ====================
def load_master_data():
    print("=" * 60)
    print(f"[ANALYSE] Loading: {MASTER_URL}")
    
    try:
        response = requests.get(MASTER_URL, timeout=15)
        if response.status_code == 200:
            df = pd.read_csv(StringIO(response.text))
            df['date_publication'] = pd.to_datetime(df['date_publication'], errors='coerce')
            df = df.dropna(subset=['date_publication', 'score_sentiment'])
            print(f"[ANALYSE] Loaded {len(df)} articles")
            return df
    except Exception as e:
        print(f"[ANALYSE] Error: {e}")
    
    all_dfs = []
    for ticker in COMPANIES.keys():
        try:
            response = requests.get(f"{GITHUB_BASE}/{ticker}.csv", timeout=10)
            if response.status_code == 200:
                df = pd.read_csv(StringIO(response.text))
                if not df.empty:
                    all_dfs.append(df)
        except Exception:
            pass
    
    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        combined['date_publication'] = pd.to_datetime(combined['date_publication'], errors='coerce')
        combined = combined.dropna(subset=['date_publication', 'score_sentiment'])
        return combined
    
    return pd.DataFrame()

def get_price_data(ticker, days=30):
    try:
        stock = yf.Ticker(ticker)
        return stock.history(period=f"{days}d", interval="1d")
    except Exception:
        return pd.DataFrame()

def predict_impact(df_company):
    _empty = {
        'signal': 'NEUTRE', 'score': 0, 'confidence': 0, 'article_count': 0,
        'latest_article': '—', 'signal_valid_from': '—', 'signal_valid_to': '—',
        'horizon_label': '~48h',
    }
    if df_company.empty:
        return _empty

    try:
        df_recent = df_company.copy()
        df_recent['date_publication'] = pd.to_datetime(
            df_recent['date_publication'], errors='coerce', utc=True
        ).dt.tz_localize(None)
        df_recent = df_recent.dropna(subset=['date_publication'])
        cutoff = datetime.now() - timedelta(days=2)
        df_filtered = df_recent[df_recent['date_publication'] >= cutoff]
        df_recent = df_filtered if not df_filtered.empty else df_recent.tail(15)
    except Exception:
        df_recent = df_company.tail(15)

    if df_recent.empty:
        return _empty

    if 'score_pondere' in df_recent.columns:
        weighted_score = df_recent['score_pondere'].mean()
    elif 'confiance' in df_recent.columns:
        weighted_score = (df_recent['score_sentiment'] * df_recent['confiance']).mean()
    else:
        weighted_score = df_recent['score_sentiment'].mean()

    volume_factor = min(len(df_recent) / 10, 1.0)
    confidence = abs(weighted_score) * volume_factor * 100

    if weighted_score > 0.15:
        signal = 'HAUSSIER'
    elif weighted_score < -0.15:
        signal = 'BAISSIER'
    else:
        signal = 'NEUTRE'

    # Horizon dynamique basé sur la date du dernier article
    try:
        latest_dt = df_recent['date_publication'].max()
        oldest_dt = df_recent['date_publication'].min()
        # Le signal expire 48h après le dernier article analysé
        expires_dt = latest_dt + timedelta(hours=48)
        latest_str  = latest_dt.strftime('%d %b %H:%M')
        valid_from  = oldest_dt.strftime('%d %b')
        valid_to    = expires_dt.strftime('%d %b %Y à %Hh')
        # Durée réelle de la fenêtre d'articles
        window_h = max(1, round((latest_dt - oldest_dt).total_seconds() / 3600))
        horizon_label = f"~{window_h}h de données · signal valide ~48h"
    except Exception:
        latest_str  = '—'
        valid_from  = datetime.now().strftime('%d %b')
        valid_to    = (datetime.now() + timedelta(days=2)).strftime('%d %b %Y')
        horizon_label = '~48h'

    return {
        'signal': signal,
        'score': round(float(weighted_score), 3),
        'confidence': round(min(confidence, 95), 1),
        'article_count': len(df_recent),
        'latest_article': latest_str,
        'signal_valid_from': valid_from,
        'signal_valid_to': valid_to,
        'horizon_label': horizon_label,
    }

# ==================== LAYOUT ====================
layout = html.Div(className="analyse-lux-page", children=[
    
    dcc.Store(id="master-data-store"),
    dcc.Store(id="last-update-store"),
    dcc.Interval(id="initial-load", interval=100, n_intervals=0, max_intervals=1),
    dcc.Interval(id="analysis-refresh", interval=5*60*1000, n_intervals=0),
    dcc.Interval(id="clock-tick", interval=1000, n_intervals=0),
    
    html.Div(className="analyse-lux-container", children=[
        
        # ========== HERO ==========
        html.Div(className="analyse-hero", children=[
            html.Div(className="analyse-hero-badge", children=[
                html.Span(className="analyse-pulse-dot"),
                html.Span("ANALYSE EN DIRECT", className="analyse-badge-text")
            ]),
            html.H1("Sentiment Intelligence", className="analyse-hero-title"),
            html.Div(className="analyse-neon-line"),
            html.P("Analyse de marche pilotee par intelligence artificielle FinBERT - Surveillez l'humeur du marche en temps reel", 
                   className="analyse-hero-subtitle"),
            
            # Live clock
            html.Div(className="analyse-clock-block", children=[
                html.Div(id="analyse-live-clock", className="analyse-clock"),
                html.Div(id="analyse-last-update", className="analyse-last-update"),
            ]),
        ]),
        
        # ========== KPI BAR ==========
        html.Div(className="analyse-kpi-grid", children=[
            html.Div(id="analyse-kpi-articles", className="analyse-kpi-card"),
            html.Div(id="analyse-kpi-companies", className="analyse-kpi-card"),
            html.Div(id="analyse-kpi-sentiment", className="analyse-kpi-card"),
            html.Div(id="analyse-kpi-bullish", className="analyse-kpi-card"),
            html.Div(id="analyse-kpi-bearish", className="analyse-kpi-card"),
        ]),
        
        # ========== MARKET OVERVIEW ==========
        html.Div(className="analyse-overview-panel", children=[
            html.Div(className="analyse-overview-left", children=[
                html.Div("APERCU DU MARCHE", className="analyse-block-label"),
                html.H2(id="analyse-headline", className="analyse-headline"),
                html.P(id="analyse-detail", className="analyse-detail"),
            ]),
            html.Div(className="analyse-overview-right", children=[
                html.Div(id="analyse-leaders", className="analyse-leaders-wrap"),
            ])
        ]),
        
        # ========== LATEST NEWS ==========
        html.Div(className="analyse-section", children=[
            html.Div(className="analyse-section-header", children=[
                html.Div(children=[
                    html.Div("01", className="analyse-section-num"),
                    html.Div(children=[
                        html.H2("Dernieres actualites", className="analyse-section-title"),
                        html.Div("Flux d'actualites en temps reel analyse par IA", className="analyse-section-sub")
                    ])
                ]),
                html.Div(className="analyse-controls", children=[
                    dcc.Dropdown(
                        id="feed-filter-ticker",
                        options=[{'label': 'TOUTES LES ACTIONS', 'value': 'ALL'}] + 
                                [{'label': t, 'value': t} for t in COMPANIES.keys()],
                        value='ALL',
                        clearable=False,
                        className="analyse-dropdown"
                    ),
                    dcc.Dropdown(
                        id="feed-filter-sentiment",
                        options=[
                            {'label': 'TOUS SENTIMENTS', 'value': 'ALL'},
                            {'label': 'POSITIF', 'value': 'positive'},
                            {'label': 'NEGATIF', 'value': 'negative'},
                            {'label': 'NEUTRE', 'value': 'neutral'},
                        ],
                        value='ALL',
                        clearable=False,
                        className="analyse-dropdown"
                    ),
                ])
            ]),
            html.Div(id="news-feed", className="analyse-news-feed")
        ]),
        
        # ========== PREDICTIONS ==========
        html.Div(className="analyse-section", children=[
            html.Div(className="analyse-section-header", children=[
                html.Div(children=[
                    html.Div("02", className="analyse-section-num"),
                    html.Div(children=[
                        html.H2("Recommandations IA", className="analyse-section-title"),
                        html.Div("Signaux haussier/baissier bases sur l'analyse FinBERT ponderee (48h)", className="analyse-section-sub")
                    ])
                ]),
            ]),
            html.Div(id="predictions-grid", className="analyse-predictions-grid")
        ]),
        
        # ========== CORRELATION CHART ==========
        html.Div(className="analyse-section", children=[
            html.Div(className="analyse-section-header", children=[
                html.Div(children=[
                    html.Div("03", className="analyse-section-num"),
                    html.Div(children=[
                        html.H2("Correlation Prix / Sentiment", className="analyse-section-title"),
                        html.Div("Comparez l'evolution du cours avec le sentiment quotidien", className="analyse-section-sub")
                    ])
                ]),
                html.Div(className="analyse-controls", children=[
                    dcc.Dropdown(
                        id="correlation-ticker",
                        options=[{'label': f"{t} - {info['name']}", 'value': t} for t, info in COMPANIES.items()],
                        value='AAPL',
                        clearable=False,
                        className="analyse-dropdown"
                    )
                ])
            ]),
            html.Div(className="analyse-chart-panel", children=[
                dcc.Graph(id="correlation-chart", config={'displayModeBar': False})
            ])
        ]),
        
        # ========== HEATMAP ==========
        html.Div(className="analyse-section", children=[
            html.Div(className="analyse-section-header", children=[
                html.Div(children=[
                    html.Div("04", className="analyse-section-num"),
                    html.Div(children=[
                        html.H2("Matrice de Sentiment", className="analyse-section-title"),
                        html.Div("Heatmap du sentiment sur 14 jours pour toutes les actions suivies", className="analyse-section-sub")
                    ])
                ]),
            ]),
            html.Div(className="analyse-chart-panel", children=[
                dcc.Graph(id="sentiment-heatmap", config={'displayModeBar': False})
            ])
        ]),
        
        # ========== METHODOLOGY ==========
        html.Div(className="analyse-method", children=[
            html.Div("METHODOLOGIE", className="analyse-block-label"),
            html.H3("Comment notre IA analyse le marche", className="analyse-method-title"),
            html.Div(className="analyse-method-grid", children=[
                html.Div(className="analyse-method-step", children=[
                    html.Div("01", className="analyse-method-num"),
                    html.Div(children=[
                        html.Div("Collecte", className="analyse-method-stitle"),
                        html.P("Agregation des actualites financieres via NewsAPI et GNews sur 7 entreprises majeures, en continu.", className="analyse-method-desc")
                    ])
                ]),
                html.Div(className="analyse-method-step", children=[
                    html.Div("02", className="analyse-method-num"),
                    html.Div(children=[
                        html.Div("Analyse IA", className="analyse-method-stitle"),
                        html.P("FinBERT (ProsusAI), modele BERT specialise en finance, evalue le ton et la confiance de chaque article.", className="analyse-method-desc")
                    ])
                ]),
                html.Div(className="analyse-method-step", children=[
                    html.Div("03", className="analyse-method-num"),
                    html.Div(children=[
                        html.Div("Ponderation", className="analyse-method-stitle"),
                        html.P("Les sources tier-1 (Reuters, Bloomberg, FT) et les articles recents recoivent un poids superieur.", className="analyse-method-desc")
                    ])
                ]),
                html.Div(className="analyse-method-step", children=[
                    html.Div("04", className="analyse-method-num"),
                    html.Div(children=[
                        html.Div("Signal", className="analyse-method-stitle"),
                        html.P("Agregation sur fenetre glissante de 48h pour produire un signal HAUSSIER / BAISSIER / NEUTRE.", className="analyse-method-desc")
                    ])
                ]),
            ]),
        ]),
        
        # ========== FOOTER ==========
        html.Div(className="analyse-footer", children=[
            html.P([
                html.I(className="fas fa-shield-halved"),
                " Mise a jour automatique toutes les 5 minutes"
            ]),
            html.P([
                html.I(className="fas fa-triangle-exclamation"),
                " Cet outil est purement informatif et ne constitue pas un conseil en investissement."
            ], className="analyse-disclaimer")
        ])
    ])
])

# ==================== CALLBACKS ====================
@callback(
    [Output("master-data-store", "data"),
     Output("last-update-store", "data")],
    [Input("initial-load", "n_intervals"),
     Input("analysis-refresh", "n_intervals")],
)
def refresh_master_data(initial_n, refresh_n):
    df = load_master_data()
    update_time = datetime.now().isoformat()
    if df.empty:
        return [], update_time
    df['date_publication'] = df['date_publication'].astype(str)
    return df.to_dict('records'), update_time

@callback(
    Output("analyse-live-clock", "children"),
    Input("clock-tick", "n_intervals"),
)
def update_clock(n):
    now = datetime.now()
    return [
        html.Span(now.strftime("%H:%M:%S"), className="analyse-clock-time"),
        html.Span(now.strftime("%A %d %B %Y").upper(), className="analyse-clock-date"),
    ]

@callback(
    Output("analyse-last-update", "children"),
    [Input("last-update-store", "data"),
     Input("clock-tick", "n_intervals")],
)
def update_last_update(last_update, n):
    if not last_update:
        return ""
    try:
        last = datetime.fromisoformat(last_update)
        diff_sec = (datetime.now() - last).total_seconds()
        if diff_sec < 60:
            txt = f"il y a {int(diff_sec)} secondes"
        elif diff_sec < 3600:
            txt = f"il y a {int(diff_sec / 60)} minutes"
        else:
            txt = f"il y a {int(diff_sec / 3600)} heures"
        return [
            html.I(className="fas fa-sync analyse-update-icon"),
            html.Span(f"Donnees mises a jour {txt}")
        ]
    except:
        return ""

@callback(
    [Output("analyse-kpi-articles", "children"),
     Output("analyse-kpi-companies", "children"),
     Output("analyse-kpi-sentiment", "children"),
     Output("analyse-kpi-bullish", "children"),
     Output("analyse-kpi-bearish", "children")],
    Input("master-data-store", "data"),
)
def update_kpi_bar(data):
    if not data:
        empty = [html.Div("---", className="analyse-kpi-value"), html.Div("CHARGEMENT", className="analyse-kpi-label")]
        return empty, empty, empty, empty, empty
    
    df = pd.DataFrame(data)
    total = len(df)
    companies = df['symbol'].nunique() if 'symbol' in df.columns else 0
    avg_sent = df['score_sentiment'].mean() if 'score_sentiment' in df.columns else 0
    
    sentiment_counts = df['sentiment'].value_counts() if 'sentiment' in df.columns else {}
    bullish_pct = (sentiment_counts.get('positive', 0) / total * 100) if total > 0 else 0
    bearish_pct = (sentiment_counts.get('negative', 0) / total * 100) if total > 0 else 0
    
    sent_class = "analyse-up" if avg_sent > 0.05 else "analyse-down" if avg_sent < -0.05 else ""
    
    return (
        [html.I(className="fas fa-newspaper analyse-kpi-icon"),
         html.Div(children=[
            html.Div(f"{total:,}", className="analyse-kpi-value"),
            html.Div("ARTICLES ANALYSES", className="analyse-kpi-label")
         ])],
        [html.I(className="fas fa-building analyse-kpi-icon"),
         html.Div(children=[
            html.Div(f"{companies}", className="analyse-kpi-value"),
            html.Div("ACTIONS SUIVIES", className="analyse-kpi-label")
         ])],
        [html.I(className="fas fa-chart-line analyse-kpi-icon"),
         html.Div(children=[
            html.Div(f"{avg_sent:+.3f}", className=f"analyse-kpi-value {sent_class}"),
            html.Div("SENTIMENT MOYEN", className="analyse-kpi-label")
         ])],
        [html.I(className="fas fa-arrow-trend-up analyse-kpi-icon analyse-up"),
         html.Div(children=[
            html.Div(f"{bullish_pct:.1f}%", className="analyse-kpi-value analyse-up"),
            html.Div("NEWS POSITIVES", className="analyse-kpi-label")
         ])],
        [html.I(className="fas fa-arrow-trend-down analyse-kpi-icon analyse-down"),
         html.Div(children=[
            html.Div(f"{bearish_pct:.1f}%", className="analyse-kpi-value analyse-down"),
            html.Div("NEWS NEGATIVES", className="analyse-kpi-label")
         ])],
    )

@callback(
    [Output("analyse-headline", "children"),
     Output("analyse-detail", "children"),
     Output("analyse-leaders", "children")],
    Input("master-data-store", "data"),
)
def update_market_summary(data):
    if not data:
        return "Chargement...", "", html.Div()
    
    df = pd.DataFrame(data)
    if 'symbol' not in df.columns:
        return "Donnees indisponibles", "", html.Div()
    
    try:
        df['date_publication'] = pd.to_datetime(df['date_publication'], errors='coerce', utc=True).dt.tz_localize(None)
        cutoff = datetime.now() - timedelta(days=3)
        df_recent = df[df['date_publication'] >= cutoff]
        if df_recent.empty:
            df_recent = df
    except Exception:
        df_recent = df
    
    overall = df_recent['score_sentiment'].mean()
    
    if overall > 0.05:
        headline = "Le marche affiche une tendance positive"
        detail = f"Le sentiment agrege sur l'ensemble des actions suivies s'etablit a {overall:+.3f}, indiquant un biais haussier dans la couverture mediatique recente."
    elif overall < -0.05:
        headline = "Le marche montre des signes de prudence"
        detail = f"Le sentiment agrege s'etablit a {overall:+.3f}, traduisant un biais baissier dans les actualites financieres recentes."
    else:
        headline = "Le marche reste en zone neutre"
        detail = f"Le sentiment agrege s'etablit a {overall:+.3f}, sans tendance directionnelle claire dans le flux d'actualites."
    
    by_company = df_recent.groupby('symbol').agg(
        avg_score=('score_sentiment', 'mean'),
        count=('score_sentiment', 'count')
    ).reset_index().sort_values('avg_score', ascending=False)
    
    top_3 = by_company.head(3)
    bottom_3 = by_company.tail(3).iloc[::-1]
    
    leaders = html.Div(className="analyse-leaders", children=[
        html.Div(className="analyse-leader-block", children=[
            html.Div([html.I(className="fas fa-arrow-up"), " HAUSSIERS"], className="analyse-leader-label analyse-up"),
            html.Div(className="analyse-leader-list", children=[
                html.Div(className="analyse-leader-row", children=[
                    html.Span(row['symbol'], className="analyse-leader-tick"),
                    html.Span(f"{row['avg_score']:+.3f}", className="analyse-leader-score analyse-up"),
                ]) for _, row in top_3.iterrows()
            ])
        ]),
        html.Div(className="analyse-leader-block", children=[
            html.Div([html.I(className="fas fa-arrow-down"), " BAISSIERS"], className="analyse-leader-label analyse-down"),
            html.Div(className="analyse-leader-list", children=[
                html.Div(className="analyse-leader-row", children=[
                    html.Span(row['symbol'], className="analyse-leader-tick"),
                    html.Span(f"{row['avg_score']:+.3f}", className="analyse-leader-score analyse-down"),
                ]) for _, row in bottom_3.iterrows()
            ])
        ]),
    ])
    
    return headline, detail, leaders

@callback(
    Output("news-feed", "children"),
    [Input("master-data-store", "data"),
     Input("feed-filter-ticker", "value"),
     Input("feed-filter-sentiment", "value")],
)
def update_news_feed(data, filter_ticker, filter_sentiment):
    if not data:
        return html.Div("Chargement du flux d'actualites...", className="analyse-empty")
    
    df = pd.DataFrame(data)
    
    try:
        df['date_publication'] = pd.to_datetime(df['date_publication'], errors='coerce', utc=True).dt.tz_localize(None)
        df = df.sort_values('date_publication', ascending=False)
    except Exception:
        pass
    
    if filter_ticker and filter_ticker != 'ALL':
        df = df[df['symbol'] == filter_ticker]
    if filter_sentiment and filter_sentiment != 'ALL':
        df = df[df['sentiment'] == filter_sentiment]
    
    df = df.head(15)
    
    if df.empty:
        return html.Div("Aucun article ne correspond aux filtres", className="analyse-empty")
    
    items = []
    for _, row in df.iterrows():
        sentiment = row.get('sentiment', 'neutral')
        ticker = row.get('symbol', '?')
        title = str(row.get('titre', ''))[:200]
        source = str(row.get('source', 'Unknown'))
        url = row.get('url', '#')
        
        try:
            pub_date = pd.to_datetime(row['date_publication'])
            time_ago = datetime.now() - pub_date
            if time_ago.days > 0:
                time_str = f"il y a {time_ago.days}j"
            elif time_ago.seconds > 3600:
                time_str = f"il y a {time_ago.seconds // 3600}h"
            else:
                time_str = f"il y a {max(time_ago.seconds // 60, 1)}min"
            full_date = pub_date.strftime("%H:%M")
        except:
            time_str = "recent"
            full_date = ""
        
        sent_class = f"analyse-news-{sentiment}"
        sent_label_map = {'positive': 'POSITIF', 'negative': 'NEGATIF', 'neutral': 'NEUTRE'}
        sent_label = sent_label_map.get(sentiment, 'NEUTRE')
        
        items.append(
            html.A(href=url, target="_blank", className="analyse-news-link",
                   **{'data-preview-url': url, 'data-title': title, 'data-source': source},
                   children=[
                html.Div(className=f"analyse-news-row {sent_class}", children=[
                    html.Div(className="analyse-news-time-col", children=[
                        html.Div(full_date, className="analyse-news-time"),
                        html.Div(time_str, className="analyse-news-rel"),
                    ]),
                    html.Div(className="analyse-news-tick-col", children=[
                        html.Div(ticker, className="analyse-news-tick"),
                    ]),
                    html.Div(className="analyse-news-content-col", children=[
                        html.Div(title, className="analyse-news-title"),
                        html.Div(className="analyse-news-source-row", children=[
                            html.Span(source, className="analyse-news-source"),
                        ])
                    ]),
                    html.Div(className="analyse-news-badge-col", children=[
                        html.Div(sent_label, className=f"analyse-news-badge {sent_class}"),
                    ]),
                ])
            ])
        )
    
    return items

@callback(
    Output("predictions-grid", "children"),
    Input("master-data-store", "data"),
)
def update_predictions(data):
    if not data:
        return html.Div("Chargement des recommandations...", className="analyse-empty")
    
    df = pd.DataFrame(data)
    if 'symbol' not in df.columns:
        return html.Div("Donnees indisponibles", className="analyse-empty")
    
    cards = []
    for ticker, info in COMPANIES.items():
        df_company = df[df['symbol'] == ticker]
        prediction = predict_impact(df_company)
        
        signal = prediction['signal']
        score = prediction['score']
        articles = prediction['article_count']

        signal_class = {
            'HAUSSIER': 'analyse-pred-up',
            'BAISSIER': 'analyse-pred-down',
            'NEUTRE': 'analyse-pred-neutral'
        }.get(signal, 'analyse-pred-neutral')

        rec_label = {'HAUSSIER': 'ACHETER', 'BAISSIER': 'VENDRE', 'NEUTRE': 'SURVEILLER'}.get(signal, signal)
        rec_icon  = {'HAUSSIER': 'fas fa-arrow-trend-up', 'BAISSIER': 'fas fa-arrow-trend-down', 'NEUTRE': 'fas fa-minus'}.get(signal, 'fas fa-minus')

        if signal == 'HAUSSIER':
            if abs(score) > 0.4:
                desc = f"Notre modèle prédit que le prix de {info['name']} va monter prochainement. Les actualités récentes sont très positives. C'est le bon moment d'acheter avant que ça monte."
            else:
                desc = f"Notre modèle prédit une légère hausse du prix de {info['name']}. Les nouvelles sont globalement bonnes. Tu peux acheter, mais le signal reste modéré."
        elif signal == 'BAISSIER':
            if abs(score) > 0.4:
                desc = f"Notre modèle prédit que le prix de {info['name']} va baisser. Si tu as cette action, c'est le moment de vendre avant qu'elle perde de la valeur."
            else:
                desc = f"Notre modèle prédit une légère baisse du prix de {info['name']}. Mieux vaut ne pas investir maintenant et attendre que la situation se stabilise."
        else:
            desc = f"Notre modèle ne sait pas encore si le prix de {info['name']} va monter ou baisser. Attends un signal plus clair avant d'agir."

        cards.append(
            html.Div(className=f"analyse-pred-card {signal_class}", children=[
                html.Div(className="analyse-pred-header", children=[
                    html.Div(children=[
                        html.Div(ticker, className="analyse-pred-tick"),
                        html.Div(info['name'], className="analyse-pred-comp"),
                        html.Div(info.get('sector', ''), className="analyse-pred-sector"),
                    ]),
                    html.Span(className=f"analyse-pred-signal {signal_class}", children=[
                        html.I(className=rec_icon), f"  {rec_label}",
                    ]),
                ]),
                html.Div(className="analyse-pred-divider"),
                html.P(desc, className="analyse-pred-desc"),
                html.Div(className="analyse-pred-footer", children=[
                    html.Span([html.I(className="fas fa-newspaper"), f"  {articles} articles analysés"],
                              className="analyse-pred-articles"),
                    html.Span([html.I(className="fas fa-clock"), f"  Valable jusqu'au {prediction['signal_valid_to']}"],
                              className="analyse-pred-valid-to"),
                ]),
            ])
        )

    return cards

@callback(
    Output("sentiment-heatmap", "figure"),
    Input("master-data-store", "data"),
)
def update_heatmap(data):
    if not data:
        return go.Figure().update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=400)
    
    df = pd.DataFrame(data)
    
    try:
        df['date_publication'] = pd.to_datetime(df['date_publication'], errors='coerce', utc=True).dt.tz_localize(None)
        df = df.dropna(subset=['date_publication'])
    except Exception:
        return go.Figure()
    
    if df.empty:
        return go.Figure()
    
    df['date'] = df['date_publication'].dt.date
    pivot = df.pivot_table(values='score_sentiment', index='symbol', columns='date', aggfunc='mean')
    pivot = pivot.iloc[:, -14:] if pivot.shape[1] > 14 else pivot
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[d.strftime('%d/%m') for d in pivot.columns],
        y=pivot.index,
        colorscale=[
            [0, '#ff7b7b'],
            [0.5, '#0a1530'],
            [1, '#7cffb2'],
        ],
        zmid=0,
        zmin=-1,
        zmax=1,
        hovertemplate='<b>%{y}</b> | %{x}<br>Score: %{z:.3f}<extra></extra>',
        colorbar=dict(
            title=dict(text="SCORE", font=dict(color='#8be9ff', size=10, family='Inter')),
            tickfont=dict(color='#b8dff0', size=10),
            outlinewidth=0,
            thickness=10,
        ),
        xgap=3,
        ygap=3,
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#eaf6ff', family='Inter, sans-serif'),
        height=400,
        margin=dict(l=70, r=20, t=20, b=40),
        xaxis=dict(
            tickfont=dict(color='#b8dff0', size=11),
            gridcolor='rgba(0,240,255,0.05)',
        ),
        yaxis=dict(
            tickfont=dict(color='#eaf6ff', size=13, family='Inter'),
            gridcolor='rgba(0,240,255,0.05)',
        ),
    )
    
    return fig

@callback(
    Output("correlation-chart", "figure"),
    [Input("correlation-ticker", "value"),
     Input("master-data-store", "data")],
)
def update_correlation(ticker, data):
    if not data or not ticker:
        return go.Figure().update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=440)
    
    df = pd.DataFrame(data)
    
    try:
        df['date_publication'] = pd.to_datetime(df['date_publication'], errors='coerce', utc=True).dt.tz_localize(None)
    except Exception:
        pass
    
    df_ticker = df[df['symbol'] == ticker].copy() if 'symbol' in df.columns else pd.DataFrame()
    
    if df_ticker.empty:
        fig = go.Figure()
        fig.add_annotation(text=f"Aucune donnee pour {ticker}", 
                          xref="paper", yref="paper", x=0.5, y=0.5,
                          showarrow=False, font=dict(color='#8be9ff', size=14, family='Inter'))
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=440)
        return fig
    
    df_ticker['date'] = df_ticker['date_publication'].dt.date
    daily_sentiment = df_ticker.groupby('date').agg(
        score=('score_sentiment', 'mean'),
        count=('score_sentiment', 'count')
    ).reset_index()
    daily_sentiment['date'] = pd.to_datetime(daily_sentiment['date'])
    
    price_data = get_price_data(ticker, days=30)
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    if not price_data.empty:
        fig.add_trace(
            go.Scatter(
                x=price_data.index,
                y=price_data['Close'],
                name=f'PRIX {ticker}',
                line=dict(color='#00f0ff', width=2.5),
                hovertemplate='<b>$%{y:.2f}</b><br>%{x|%d/%m/%Y}<extra></extra>'
            ),
            secondary_y=False
        )
    
    colors = ['#7cffb2' if s > 0 else '#ff7b7b' for s in daily_sentiment['score']]
    fig.add_trace(
        go.Bar(
            x=daily_sentiment['date'],
            y=daily_sentiment['score'],
            name='SENTIMENT',
            marker=dict(color=colors, opacity=0.75, line=dict(width=0)),
            hovertemplate='<b>Sentiment %{y:.3f}</b><br>%{x|%d/%m/%Y}<br>%{customdata} articles<extra></extra>',
            customdata=daily_sentiment['count']
        ),
        secondary_y=True
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#eaf6ff', family='Inter, sans-serif', size=11),
        height=440,
        margin=dict(l=60, r=60, t=30, b=40),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1,
            bgcolor='rgba(0,0,0,0)',
            font=dict(color='#8be9ff', size=11, family='Inter')
        ),
        hovermode='x unified',
        xaxis=dict(
            gridcolor='rgba(0,240,255,0.05)',
            tickfont=dict(color='#b8dff0', size=11),
            showline=True,
            linecolor='rgba(0,240,255,0.15)',
        ),
        bargap=0.2,
    )
    
    fig.update_yaxes(
        title_text="PRIX (USD)",
        secondary_y=False,
        gridcolor='rgba(0,240,255,0.05)',
        tickfont=dict(color='#b8dff0', size=11),
        title_font=dict(color='#8be9ff', size=11, family='Inter'),
        showline=True,
        linecolor='rgba(0,240,255,0.15)',
    )
    fig.update_yaxes(
        title_text="SENTIMENT",
        secondary_y=True,
        gridcolor='rgba(0,240,255,0)',
        tickfont=dict(color='#b8dff0', size=11),
        title_font=dict(color='#8be9ff', size=11, family='Inter'),
        range=[-1, 1]
    )
    
    return fig
