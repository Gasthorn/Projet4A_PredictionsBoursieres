import dash
from dash import html, dcc, Input, Output, State, callback, no_update, ctx, ALL
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor

dash.register_page(__name__, path="/demo")

_COMPANIES = {
    'AAPL':  'Apple',
    'MSFT':  'Microsoft',
    'TSLA':  'Tesla',
    'NVDA':  'NVIDIA',
    'GOOGL': 'Alphabet',
    'AMZN':  'Amazon',
    'META':  'Meta',
}

_MODEL_META = {
    'lstm':        {'label': 'LSTM',               'icon': 'fas fa-brain',     'color': '#00d4ff'},
    'transformer': {'label': 'Transformer Hybride', 'icon': 'fas fa-atom',      'color': '#3ef5a0'},
    'sentiment':   {'label': 'Actualités',          'icon': 'fas fa-newspaper', 'color': '#f0c040'},
}

_DEFAULT_TICKER = 'TSLA'


def _chip_class(k, selected):
    return "demo-chip demo-chip-active" if k == selected else "demo-chip"


layout = html.Div(className="demo-page", children=[

    # ── Popup "Faites-nous confiance" ─────────────────────────────────
    dcc.Store(id="demo-popup-closed", storage_type="session"),

    html.Div(id="demo-trust-overlay", className="demo-trust-overlay", children=[
        html.Div(className="demo-trust-modal", children=[

            html.Button(
                html.I(className="fas fa-times"),
                id="demo-trust-x",
                className="demo-trust-close",
                n_clicks=0,
            ),

            html.Div(className="demo-trust-badge", children=[
                html.I(className="fas fa-brain"),
                "  Prédictions IA — données réelles"
            ]),

            html.H2("Pourquoi nous faire confiance ?", className="demo-trust-title"),
            html.P(
                "Nous ne vous demandons pas de nous croire sur parole. "
                "Voici la preuve : nos 3 modèles IA, testés sur les 180 derniers jours.",
                className="demo-trust-sub"
            ),

            html.Div(className="demo-trust-intro", children=[
                html.I(className="fas fa-circle-info"),
                html.Span(
                    "La démo ci-dessous simule exactement ce qui se serait passé "
                    "si vous aviez suivi les conseils de chaque modèle IA depuis 6 mois. "
                    "Les résultats sont calculés sur des données de marché réelles — "
                    "y compris quand un modèle perd de l'argent."
                ),
            ]),

            html.Div(className="demo-trust-models", children=[
                html.Div(className="demo-trust-model", children=[
                    html.I(className="fas fa-brain", style={"color": "#00d4ff"}),
                    html.Div(children=[
                        html.Strong("LSTM"),
                        html.P("Analyse 30 jours de prix historiques via un réseau de neurones BiLSTM. "
                               "14 indicateurs techniques calculés en temps réel."),
                    ]),
                ]),
                html.Div(className="demo-trust-model", children=[
                    html.I(className="fas fa-atom", style={"color": "#3ef5a0"}),
                    html.Div(children=[
                        html.Strong("Transformer Hybride"),
                        html.P("Combine 60 jours de prix ET les actualités financières. "
                               "44 features analysées par un Transformer (même architecture que les LLMs)."),
                    ]),
                ]),
                html.Div(className="demo-trust-model", children=[
                    html.I(className="fas fa-newspaper", style={"color": "#f0c040"}),
                    html.Div(children=[
                        html.Strong("Actualités"),
                        html.P("Analyse le sentiment des articles de presse financière "
                               "des 48 dernières heures pour détecter les signaux HAUSSIER ou BAISSIER."),
                    ]),
                ]),
            ]),

            html.Div(className="demo-trust-actions", children=[
                html.Button(
                    [html.I(className="fas fa-play"), "  Voir la démonstration"],
                    id="demo-trust-close",
                    className="demo-trust-btn-primary",
                    n_clicks=0,
                ),
                html.A(
                    [html.I(className="fas fa-user-plus"), "  Créer un compte"],
                    href="/signup", className="demo-trust-btn-ghost"
                ),
            ]),

            html.P(
                [html.I(className="fas fa-right-to-bracket", style={"marginRight":"5px"}),
                 "Déjà inscrit ? ",
                 html.A("Se connecter", href="/login", style={"color":"rgba(0,212,255,0.6)", "textDecoration":"underline"})],
                className="demo-trust-login-hint",
                id="demo-trust-skip-link",
            ),
        ]),
    ]),

    # ── Hero ──────────────────────────────────────────────────────────
    html.Div(className="demo-hero", children=[
        html.Div(className="demo-hero-badge", children=[
            html.I(className="fas fa-flask"),
            "  Démonstration live"
        ]),
        html.H1("Et si vous aviez suivi nos conseils ?", className="demo-h1"),
        html.P(
            "Choisissez une action et un montant. "
            "Comparez les 3 modèles IA côte à côte sur les 180 derniers jours.",
            className="demo-subtitle"
        ),
    ]),

    # ── Contrôles ─────────────────────────────────────────────────────
    dcc.Store(id="demo-ticker-store", data=_DEFAULT_TICKER),

    html.Div(className="demo-controls-bar", children=[
        html.Label("Choisissez une action", className="demo-label"),
        html.Div(className="demo-controls-row", children=[
            # Chips
            html.Div(className="demo-chips-row", id="demo-chips-row", children=[
                html.Button(
                    children=[
                        html.Span(k, className="chip-sym"),
                        html.Span(v, className="chip-name"),
                    ],
                    id={"type": "demo-chip", "index": k},
                    className=_chip_class(k, _DEFAULT_TICKER),
                    n_clicks=0,
                ) for k, v in _COMPANIES.items()
            ]),
            # Séparateur
            html.Div(className="demo-ctrl-sep"),
            # Montant
            html.Div(className="demo-ctrl-inline", children=[
                html.Label("Montant (€)", className="demo-label"),
                dcc.Input(
                    id="demo-amount",
                    type="number",
                    value=500,
                    min=100,
                    max=100000,
                    step=100,
                    className="demo-input",
                ),
            ]),
            # Bouton
            html.Button(
                [html.I(className="fas fa-play"), "  Simuler"],
                id="demo-btn",
                className="demo-btn",
                n_clicks=0,
            ),
        ]),
    ]),

    # ── Résultats 3 colonnes ──────────────────────────────────────────
    dcc.Loading(
        id="demo-loading",
        type="circle",
        color="#00d4ff",
        children=html.Div(id="demo-result"),
    ),

    # ── CTA ───────────────────────────────────────────────────────────
    html.Div(className="demo-cta-section", children=[
        html.Div(className="demo-cta-inner", children=[
            html.Div(className="demo-cta-text", children=[
                html.H2("Passez aux prédictions en temps réel", className="demo-cta-title"),
                html.P(
                    "Créez un compte gratuit pour accéder aux signaux IA en direct, "
                    "enregistrer vos investissements et suivre votre performance.",
                    className="demo-cta-sub"
                ),
                html.Ul(className="demo-cta-features", children=[
                    html.Li([html.I(className="fas fa-check"), "  Prédictions en temps réel sur 8 actifs"]),
                    html.Li([html.I(className="fas fa-check"), "  Historique personnel de vos investissements"]),
                    html.Li([html.I(className="fas fa-check"), "  Assistant IA conversationnel"]),
                    html.Li([html.I(className="fas fa-check"), "  Comparaison des modèles sur vos actifs"]),
                ]),
            ]),
            html.Div(className="demo-cta-btns", children=[
                html.A(
                    [html.I(className="fas fa-user-plus"), "  Créer un compte gratuit"],
                    href="/signup", className="demo-cta-primary"
                ),
                html.A(
                    [html.I(className="fas fa-right-to-bracket"), "  Se connecter"],
                    href="/login", className="demo-cta-ghost"
                ),
            ]),
        ]),
    ]),
])


# ── Callback : fermer le popup confiance ─────────────────────────
@callback(
    Output("demo-trust-overlay", "className"),
    Output("demo-popup-closed",  "data"),
    Input("demo-trust-close",    "n_clicks"),
    Input("demo-trust-x",        "n_clicks"),
    prevent_initial_call=True,
)
def close_trust_popup(n1, n2):
    return "demo-trust-overlay demo-trust-hidden", True


# ── Callback : sélection d'un chip ticker ─────────────────────────
@callback(
    Output({"type": "demo-chip", "index": ALL}, "className"),
    Output("demo-ticker-store", "data"),
    Input({"type": "demo-chip", "index": ALL},  "n_clicks"),
    prevent_initial_call=True,
)
def select_ticker(n_clicks_list):
    triggered = ctx.triggered_id
    if not triggered:
        return no_update, no_update
    selected = triggered["index"]
    classes  = [_chip_class(k, selected) for k in _COMPANIES.keys()]
    return classes, selected


# ── Callback : simulation ─────────────────────────────────────────
# Se déclenche au chargement (initial), au clic sur un chip ET au clic "Simuler"
@callback(
    Output("demo-result",      "children"),
    Input("demo-ticker-store", "data"),   # chip sélectionné (+ chargement initial)
    Input("demo-btn",          "n_clicks"),
    State("demo-amount",       "value"),
    prevent_initial_call=False,
)
def run_demo(ticker, n_clicks, amount):
    if not ticker:
        return no_update

    try:
        amount = float(amount) if amount and float(amount) >= 100 else 500.0
    except (TypeError, ValueError):
        amount = 500.0

    company = _COMPANIES.get(ticker, ticker)

    def _run(key):
        try:
            if key == 'lstm':
                from pages.mon_suivi import _run_backtest_lstm
                return key, _run_backtest_lstm(ticker, start_amount=amount, days=180)
            elif key == 'transformer':
                from services.transformer_service import predict_backtest
                return key, predict_backtest(ticker, start_amount=amount, days=180)
            else:
                from pages.mon_suivi import _run_backtest
                return key, _run_backtest(ticker, start_amount=amount, days=180)
        except Exception as e:
            print(f"[DEMO] {key}/{ticker}: {e}")
            return key, None

    results = {}
    with ThreadPoolExecutor(max_workers=3) as ex:
        for key, bt in ex.map(_run, _MODEL_META.keys()):
            results[key] = bt

    best_key, best_ret = None, None
    for k, bt in results.items():
        if bt and (best_ret is None or bt['total_return'] > best_ret):
            best_ret = bt['total_return']
            best_key = k

    cards = [_make_model_card(k, results.get(k), amount, ticker)
             for k in _MODEL_META.keys()]

    best_label = _MODEL_META[best_key]['label']  if best_key else "—"
    best_color = _MODEL_META[best_key]['color']   if best_key else "#00d4ff"

    return html.Div(className="demo-results", children=[
        html.Div(className="demo-results-header", children=[
            html.Span(f"{ticker} — {company}", className="demo-results-ticker"),
            html.Span([
                "Meilleur modèle sur cette période : ",
                html.Strong(best_label, style={"color": best_color}),
            ], className="demo-results-best"),
        ]),
        html.Div(className="demo-cards-grid", children=cards),
        html.P(
            "Simulation rolling 180 jours · données réelles · "
            "les performances passées ne garantissent pas les résultats futurs.",
            className="demo-result-disclaimer"
        ),
    ])


def _make_model_card(key, bt, amount, ticker):
    meta = _MODEL_META[key]

    if not bt:
        return html.Div(className="demo-model-card demo-model-error", children=[
            html.Div(className="demo-mc-head", children=[
                html.I(className=meta['icon'], style={"color": meta['color']}),
                html.Span(meta['label'], className="demo-mc-name"),
            ]),
            html.Div(className="demo-mc-nodata", children=[
                html.I(className="fas fa-circle-exclamation"),
                html.P("Données insuffisantes pour ce modèle."),
            ]),
        ])

    final    = bt['final_value']
    gain     = final - amount
    ret      = bt['total_return']
    bh_final = bt['buy_hold'][-1] if bt.get('buy_hold') else amount
    bh_ret   = bt['buy_hold_return']
    win_rate = bt['win_rate']
    start_dt = bt['start_date']
    dates    = bt['dates']
    port     = bt['portfolio']
    bh       = bt['buy_hold']

    is_pos    = gain >= 0
    gain_sign = "+" if is_pos else ""
    line_col  = "#3ef5a0" if is_pos else "#ff6060"
    fill_col  = "rgba(0,255,135,0.07)" if is_pos else "rgba(255,60,60,0.07)"
    gain_cls  = "demo-mc-pos" if is_pos else "demo-mc-neg"
    vs_bh     = final - bh_final
    vs_sign   = "+" if vs_bh >= 0 else ""

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=bh, name="Sans IA",
        line=dict(color="rgba(255,255,255,0.22)", width=1.2, dash="dot"),
        hovertemplate="%{y:.2f}€<extra>Sans IA</extra>",
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=port, name="Modèle IA",
        line=dict(color=line_col, width=2.2),
        fill="tonexty", fillcolor=fill_col,
        hovertemplate="%{y:.2f}€<extra>Modèle IA</extra>",
    ))
    fig.add_hline(y=amount, line_dash="dot", line_color="rgba(255,255,255,0.1)")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(3,8,25,0.6)",
        font=dict(color="#8ab4cc", size=10, family="system-ui"),
        margin=dict(l=40, r=8, t=30, b=36),
        height=200,
        legend=dict(orientation="h", y=1.08, x=0, bgcolor="rgba(0,0,0,0)", font=dict(size=10)),
        xaxis=dict(gridcolor="rgba(255,255,255,0.04)", showgrid=True, zeroline=False, tickfont=dict(size=9)),
        yaxis=dict(gridcolor="rgba(255,255,255,0.04)", showgrid=True, zeroline=False,
                   ticksuffix="€", tickfont=dict(size=9)),
        hovermode="x unified",
    )

    return html.Div(className=f"demo-model-card {'demo-mc-winner' if is_pos else ''}", children=[
        html.Div(className="demo-mc-head", children=[
            html.I(className=meta['icon'], style={"color": meta['color']}),
            html.Span(meta['label'], className="demo-mc-name"),
        ]),
        html.Div(className="demo-mc-summary", children=[
            f"{amount:,.0f}€ depuis {start_dt} → ",
            html.Strong(f"{final:,.2f}€", className=gain_cls),
        ]),
        html.Div(className=f"demo-mc-gain {gain_cls}", children=[
            html.Span(f"{gain_sign}{gain:,.2f}€", className="demo-mc-gain-eur"),
            html.Span(f"  {gain_sign}{ret:.1f}%", className="demo-mc-gain-pct"),
        ]),
        html.Div(className="demo-mc-chart", children=[
            dcc.Graph(figure=fig, config={"displayModeBar": False, "responsive": True}),
        ]),
        html.Div(className="demo-mc-stats", children=[
            html.Div(className="demo-mc-stat", children=[
                html.Div(className="demo-mc-stat-lbl-wrap", children=[
                    html.Span("Sans IA", className="demo-mc-stat-lbl"),
                    html.Span("achat jour 0, conservé 180j", className="demo-mc-stat-hint"),
                ]),
                html.Span(f"{bh_final:,.2f}€ ({'+' if bh_ret>=0 else ''}{bh_ret:.1f}%)",
                          className="demo-mc-stat-val"),
            ]),
            html.Div(className="demo-mc-stat", children=[
                html.Span("Avantage IA vs sans IA", className="demo-mc-stat-lbl"),
                html.Span(f"{vs_sign}{vs_bh:,.2f}€",
                          className=f"demo-mc-stat-val {'demo-mc-pos' if vs_bh>=0 else 'demo-mc-neg'}"),
            ]),
            html.Div(className="demo-mc-stat", children=[
                html.Span("Taux réussite des signaux", className="demo-mc-stat-lbl"),
                html.Span(f"{win_rate}%", className="demo-mc-stat-val"),
            ]),
        ]),
    ])
