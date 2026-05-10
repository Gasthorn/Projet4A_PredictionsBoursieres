import dash
from dash import html, dcc, Input, Output, State, callback
from services.tracking_service import get_global_stats, get_rich_testimonials, add_testimonial, get_user_testimonial, get_user_stats, get_user_trades
from services.auth_service import get_user_by_email, set_public_stats

dash.register_page(__name__, path="/temoignages", name="Témoignages")

def _parse_optional_number(value):
    if value in (None, ""):
        return None
    cleaned = str(value).replace(" ", "").replace(",", ".").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


layout = html.Div(className="testimonials-premium-page", children=[

    # ===== HERO =====
    html.Div(className="testimonials-premium-hero", children=[
        html.Div(className="hero-content", children=[
            html.H1("Ils nous font confiance", className="hero-premium-title"),
            html.P("Rejoignez notre communauté d'utilisateurs qui suivent leurs prédictions au quotidien",
                   className="hero-premium-subtitle"),
            html.Div(className="hero-premium-stats", id="testimonials-premium-stats"),
        ]),
        html.Div(className="hero-premium-decoration"),
    ]),

    # ===== GRILLE =====
    html.Div(className="testimonials-premium-grid", id="testimonials-premium-grid"),

    # ===== FORMULAIRE =====
    html.Div(id="testimonials-premium-form", className="testimonials-premium-form-wrapper"),
])


# ==================== CALLBACK PRINCIPAL ====================

@callback(
    Output("testimonials-premium-stats", "children"),
    Output("testimonials-premium-grid", "children"),
    Output("testimonials-premium-form", "children"),
    Input("url", "pathname"),
    State("session-store", "data"),
)
def load_testimonials_page(pathname, session):

    # ── STATS GLOBALES RÉELLES ──
    stats = get_global_stats()

    user_count = stats.get('user_count', 0)
    avg_rating = stats.get('avg_rating', 4.9)
    winning = stats.get('winning_trades', 0)
    win_rate = stats.get('win_rate', 0)
    total_pnl = stats.get('total_pnl', 0)

    stats_display = html.Div(className="premium-stats-grid", children=[
        html.Div(className="premium-stat-card", children=[
            html.Div(className="premium-stat-icon", children=html.I(className="fas fa-users")),
            html.Div(className="premium-stat-content", children=[
                html.Span("Utilisateurs inscrits", className="premium-stat-label"),
                html.Span(f"{user_count:,}", className="premium-stat-value"),
                html.Span("membres actifs", className="premium-stat-trend"),
            ]),
        ]),
        html.Div(className="premium-stat-card", children=[
            html.Div(className="premium-stat-icon", children=html.I(className="fas fa-star")),
            html.Div(className="premium-stat-content", children=[
                html.Span("Note moyenne", className="premium-stat-label"),
                html.Span(f"{avg_rating:.1f}", className="premium-stat-value"),
                html.Span("sur 5 étoiles", className="premium-stat-trend"),
            ]),
        ]),
        html.Div(className="premium-stat-card", children=[
            html.Div(className="premium-stat-icon", children=html.I(className="fas fa-trophy")),
            html.Div(className="premium-stat-content", children=[
                html.Span("Trades gagnants", className="premium-stat-label"),
                html.Span(f"{winning:,}", className="premium-stat-value"),
                html.Span(
                    f"{win_rate:.1f}% de réussite" if win_rate > 0 else "—",
                    className="premium-stat-trend positive",
                ),
            ]),
        ]),
        html.Div(className="premium-stat-card", children=[
            html.Div(className="premium-stat-icon", children=html.I(className="fas fa-euro-sign")),
            html.Div(className="premium-stat-content", children=[
                html.Span("Gains cumulés", className="premium-stat-label"),
                html.Span(
                    f"{total_pnl:+,.0f} €" if total_pnl != 0 else "—",
                    className="premium-stat-value",
                ),
                html.Span("depuis le lancement", className="premium-stat-trend positive"),
            ]),
        ]),
    ])

    # ── TÉMOIGNAGES RÉELS ──
    testimonials = get_rich_testimonials(12)

    if not testimonials:
        grid = html.Div(className="tem-empty-state", children=[
            html.I(className="fas fa-comments", style={"fontSize": "3rem", "color": "rgba(0,240,255,0.3)", "display": "block", "marginBottom": "16px"}),
            html.H3("Aucun témoignage approuvé pour le moment", style={"color": "#7a8aaa"}),
            html.P("Soyez le premier à partager votre expérience !", style={"color": "#555e7a"}),
        ])
    else:
        cards = [_build_testimonial_card(t) for t in testimonials]
        grid = html.Div(cards, className="premium-cards-grid")

    # ── FORMULAIRE / STATUT ──
    form = _build_form_section(session)

    return stats_display, grid, form


# ==================== HELPERS ====================

def _avatar_style(win_rate, trades):
    """Couleur de l'avatar selon la performance réelle (None = stats privées)"""
    wr = win_rate or 0
    tr = trades or 0
    if tr == 0:
        return {"background": "linear-gradient(135deg, #0a4a6a, #00f0ff22)"}
    if wr >= 60:
        return {"background": "linear-gradient(135deg, #004d2a, #00ff8744)"}
    if wr >= 45:
        return {"background": "linear-gradient(135deg, #0a3060, #00f0ff33)"}
    return {"background": "linear-gradient(135deg, #4d0014, #ff4d6d33)"}


def _build_testimonial_card(t):
    name = t['name']
    initials = t['initials']
    content = t['content']
    rating = t['rating']
    gain = t['gain']
    trades = t['trades']          # None si stats privées
    win_rate = t['win_rate']      # None si stats privées
    member_months = t['member_months']
    is_public = t.get('public_stats', False)
    is_online = t.get('is_online', False)

    stars = "★" * rating + "☆" * (5 - rating)

    if is_public and gain != 0:
        gain_text = f"{gain:+,.0f} €"
        gain_cls = "stat-item-value gain" if gain > 0 else "stat-item-value negative"
    else:
        gain_text = "—"
        gain_cls = "stat-item-value"

    if member_months >= 12:
        member_label = f"{member_months // 12} an{'s' if member_months // 12 > 1 else ''}"
    elif member_months > 0:
        member_label = f"{member_months} mois"
    else:
        member_label = "< 1 mois"

    win_cls = "stat-item-value positive" if (win_rate or 0) >= 50 else "stat-item-value"

    return html.Div(className="premium-testimonial-card", children=[

        # En-tête
        html.Div(className="premium-card-header", children=[
            html.Div(className="premium-card-avatar-wrapper", children=[
                html.Div(
                    className="premium-card-avatar",
                    children=initials,
                    style=_avatar_style(win_rate, trades),
                ),
                html.Div(
                    className="premium-card-online" if is_online else "premium-card-offline",
                    title="En ligne" if is_online else "Hors ligne",
                ),
            ]),
            html.Div(className="premium-card-info", children=[
                html.Div(className="premium-card-name-wrapper", children=[
                    html.H3(name, className="premium-card-name"),
                    html.Span("✔", className="premium-card-verified", title="Compte vérifié"),
                ]),
                html.Div(className="premium-card-role", children=[
                    html.Span(
                        "Trader actif" if (trades or 0) >= 10 else ("Investisseur" if (trades or 0) > 0 else "Membre"),
                        className="premium-card-role-text",
                    ),
                ]),
            ]),
            html.Div(className="premium-card-rating", children=[
                html.Span(stars, className="premium-card-stars"),
            ]),
        ]),

        # Citation
        html.Div(className="premium-card-quote", children=[
            html.I(className="fas fa-quote-left premium-quote-icon"),
            html.P(content, className="premium-card-content"),
        ]),

        # Statistiques (réelles si public, sinon masquées)
        html.Div(className="premium-card-stats", children=[
            html.Div(className="premium-stat-item", children=[
                html.Span("Trades", className="stat-item-label"),
                html.Span(str(trades) if trades is not None else "—", className="stat-item-value"),
            ]),
            html.Div(className="premium-stat-item", children=[
                html.Span("Win rate", className="stat-item-label"),
                html.Span(f"{win_rate:.0f}%" if win_rate is not None else "—", className=win_cls),
            ]),
            html.Div(className="premium-stat-item", children=[
                html.Span("Gain net", className="stat-item-label"),
                html.Span(gain_text, className=gain_cls),
            ]),
        ]),

        # Footer
        html.Div(className="premium-card-footer", children=[
            html.Div(className="premium-footer-left", children=[
                html.I(className="fas fa-calendar-alt"),
                html.Span(f"  Membre depuis {member_label}"),
            ]),
            html.Div(className="premium-footer-right", children=[
                html.I(className="fas fa-shield-halved"),
                html.Span("  Données vérifiées"),
            ]),
        ]),
    ])


def _build_form_section(session):
    if not (session and session.get("email")):
        return html.Div(className="premium-cta-card", children=[
            html.H3("Partagez votre expérience", className="premium-cta-title"),
            html.P("Connectez-vous pour laisser un témoignage", className="premium-cta-text"),
            dcc.Link(html.Button("Se connecter", className="premium-cta-button"), href="/login"),
        ])

    user_email = session.get("email")
    existing = get_user_testimonial(user_email)

    if existing:
        status = existing[1]
        if status == 'pending':
            return html.Div(className="premium-status-card pending", children=[
                html.Div(className="premium-status-icon", children=html.I(className="fas fa-clock")),
                html.H3("Témoignage en attente", className="premium-status-title"),
                html.P("Votre témoignage sera visible après validation par un administrateur.",
                       className="premium-status-text"),
            ])
        elif status == 'approved':
            return html.Div(className="premium-status-card approved", children=[
                html.Div(className="premium-status-icon", children=html.I(className="fas fa-check-circle")),
                html.H3("Merci pour votre témoignage !", className="premium-status-title"),
                html.P("Il est déjà visible sur cette page.", className="premium-status-text"),
            ])

    user = get_user_by_email(user_email)
    user_stats = get_user_stats(user_email)
    return _create_testimonial_form(user, user_stats)


def _create_testimonial_form(user, user_stats=None):
    # Nom pré-rempli avec vrai prénom + nom
    prenom = (user or {}).get('prenom', '')
    nom = (user or {}).get('nom', '')
    full_name = " ".join(filter(None, [prenom, nom])).strip()
    if not full_name:
        full_name = (user or {}).get('email', '').split('@')[0].capitalize()

    # Gain pré-rempli avec le vrai PnL de l'utilisateur
    real_pnl = (user_stats or {}).get('total_pnl', None)
    gain_default = round(real_pnl, 0) if real_pnl and real_pnl != 0 else None

    return html.Div(className="premium-form-simple", children=[
        html.H3("Partagez votre expérience", className="simple-form-title"),
        html.P("Votre avis compte pour notre communauté", className="simple-form-subtitle"),

        html.Div(className="simple-form-group", children=[
            html.Label("Nom affiché"),
            dcc.Input(id="testimonial-name", type="text", value=full_name, className="simple-form-input"),
        ]),

        html.Div(className="simple-form-group", children=[
            html.Label("Votre note"),
            html.Div(className="stars-container", id="stars-container", children=[
                html.Span("★", className="star active", id="star-1", n_clicks=0),
                html.Span("★", className="star active", id="star-2", n_clicks=0),
                html.Span("★", className="star active", id="star-3", n_clicks=0),
                html.Span("★", className="star active", id="star-4", n_clicks=0),
                html.Span("★", className="star active", id="star-5", n_clicks=0),
            ]),
            dcc.Store(id="selected-rating", data=5),
        ]),

        html.Div(className="simple-form-group", children=[
            html.Label("Votre message"),
            dcc.Textarea(
                id="testimonial-content",
                placeholder="Partagez votre expérience avec la plateforme...",
                className="simple-form-textarea",
            ),
        ]),

        html.Div(className="simple-form-row", children=[
            html.Div(className="simple-form-group", children=[
                html.Label([
                    "Gain net (€)",
                    html.Span(
                        " — pré-rempli depuis vos trades" if gain_default is not None else " — optionnel",
                        style={"fontSize": "0.72rem", "color": "#00f0ff", "marginLeft": "6px"},
                    ),
                ]),
                dcc.Input(
                    id="testimonial-gain",
                    type="text",
                    inputMode="numeric",
                    value=gain_default,
                    placeholder="ex: 5000",
                    className="simple-form-input",
                ),
            ]),
            html.Div(className="simple-form-group", children=[
                html.Label("Période — optionnel"),
                dcc.Input(
                    id="testimonial-period",
                    type="text",
                    placeholder="ex: 6 mois",
                    className="simple-form-input",
                ),
            ]),
        ]),

        html.Div(className="simple-anonymous-row", children=[
            dcc.Checklist(
                id="testimonial-anonymous",
                options=[{"label": " Publier en anonyme", "value": "anonymous"}],
                value=[],
                className="simple-anonymous-check",
                inputClassName="simple-anonymous-input",
                labelClassName="simple-anonymous-label",
            ),
        ]),

        html.Button("Envoyer mon témoignage", id="testimonial-submit", className="simple-form-button"),
        html.Div(id="testimonial-message", className="simple-form-message"),
    ])


# ==================== CALLBACKS ÉTOILES + ENVOI ====================

@callback(
    Output("star-1", "className"),
    Output("star-2", "className"),
    Output("star-3", "className"),
    Output("star-4", "className"),
    Output("star-5", "className"),
    Output("selected-rating", "data"),
    Input("star-1", "n_clicks"),
    Input("star-2", "n_clicks"),
    Input("star-3", "n_clicks"),
    Input("star-4", "n_clicks"),
    Input("star-5", "n_clicks"),
    prevent_initial_call=True,
)
def update_stars(s1, s2, s3, s4, s5):
    triggered = dash.callback_context.triggered
    if not triggered:
        return ("star active",) * 5 + (5,)
    star_id = triggered[0]["prop_id"].split(".")[0]
    rating = int(star_id.split("-")[1])
    classes = tuple("star active" if i <= rating else "star" for i in range(1, 6))
    return *classes, rating


@callback(
    Output("testimonial-message", "children"),
    Input("testimonial-submit", "n_clicks"),
    State("session-store", "data"),
    State("testimonial-name", "value"),
    State("testimonial-content", "value"),
    State("selected-rating", "data"),
    State("testimonial-gain", "value"),
    State("testimonial-period", "value"),
    State("testimonial-anonymous", "value"),
    prevent_initial_call=True,
)
def submit_testimonial(n_clicks, session, name, content, rating, gain, period, anonymous):
    if not session:
        return html.Div([html.I(className="fas fa-exclamation-circle"), " Veuillez vous connecter"],
                        className="simple-message error")

    if not content or len(content.strip()) < 10:
        return html.Div([html.I(className="fas fa-exclamation-circle"),
                         " Le message doit contenir au moins 10 caractères"],
                        className="simple-message error")

    gain = _parse_optional_number(gain)
    display_name = "Anonyme" if "anonymous" in (anonymous or []) else (name or "Anonyme").strip()

    ok = add_testimonial(
        user_email=session.get("email"),
        user_name=display_name,
        content=content.strip(),
        rating=rating or 5,
        gain=gain,
        period=period,
    )

    if ok:
        return html.Div([html.I(className="fas fa-check-circle"),
                         " Témoignage envoyé ! Il sera visible après validation."],
                        className="simple-message success")
    return html.Div([html.I(className="fas fa-times-circle"), " Une erreur est survenue"],
                    className="simple-message error")
