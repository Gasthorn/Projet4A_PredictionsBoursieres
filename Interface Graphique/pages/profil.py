import dash
from dash import html, dcc, Input, Output, State, callback, no_update
from datetime import datetime

from services.auth_service import get_user_by_email, update_user_profile, set_public_stats, set_online_status
from services.tracking_service import get_user_stats, get_user_trades

dash.register_page(__name__, path="/profil", name="Mon Profil")

FR_PHONE_PREFIX = "+33 "


def _split_fr_phone(value):
    phone = (value or "").strip()
    if phone.startswith("+33"):
        return phone[3:].strip()
    return phone


def _format_fr_phone(value):
    phone = _split_fr_phone(value)
    return f"{FR_PHONE_PREFIX}{phone}".strip() if phone else ""

layout = html.Div(className="profil-page", children=[
    dcc.Location(id="profil-url"),
    dcc.Store(id="profil-edit-mode", data=False),
    dcc.Interval(id="profil-init", interval=300, n_intervals=0, max_intervals=1),

    # ===== HERO =====
    html.Div(className="profil-hero", children=[
        html.Div(className="profil-hero-badge", children=[
            html.Span(className="profil-pulse-dot"),
            html.Span("MON ESPACE PERSONNEL"),
        ]),
        html.H1("Mon Profil", className="profil-hero-title"),
        html.Div(className="profil-neon-line"),
    ]),

    html.Div(className="profil-layout", children=[

        # ══════════════ SIDEBAR GAUCHE ══════════════
        html.Div(className="profil-sidebar", children=[

            # Carte avatar + identité
            html.Div(className="profil-id-card", children=[
                html.Div(className="profil-avatar-wrap", children=[
                    html.Div(id="profil-avatar", className="profil-avatar"),
                    html.Div(id="profil-avatar-ring", className="profil-avatar-ring"),
                ]),
                html.H2(id="profil-full-name", className="profil-full-name"),
                html.P(id="profil-email-display", className="profil-email"),
                html.Div(id="profil-badges", className="profil-badges"),
                html.Div(id="profil-member-label", className="profil-member-label"),
            ]),

            # Bouton modifier
            html.Button(
                [html.I(className="fas fa-pen"), "  Modifier le profil"],
                id="profil-edit-toggle-btn",
                className="profil-edit-toggle-btn",
                n_clicks=0,
            ),
        ]),

        # ══════════════ MAIN DROITE ══════════════
        html.Div(className="profil-main", children=[

            # ── KPIs trading ──
            html.Div(id="profil-kpis", className="profil-kpi-row"),

            # ── Informations personnelles ──
            html.Div(className="profil-card", id="profil-info-card", children=[
                html.Div(className="profil-card-hdr", children=[
                    html.Div([
                        html.I(className="fas fa-id-card"),
                        html.Span("  Informations personnelles"),
                    ], className="profil-card-title"),
                    html.Span(id="profil-edit-badge", className="profil-mode-badge profil-mode-read",
                              children="Lecture"),
                ]),
                html.Div(id="profil-info-body"),
                html.Div(id="profil-save-feedback"),
            ]),

            # ── Visibilité publique ──
            html.Div(className="profil-card", children=[
                html.Div(className="profil-card-hdr", children=[
                    html.Div([
                        html.I(className="fas fa-globe"),
                        html.Span("  Visibilité publique"),
                    ], className="profil-card-title"),
                ]),
                html.Div(className="profil-visibility-body", children=[
                    html.Div(className="profil-toggle-row", children=[
                        html.Div(className="profil-toggle-text", children=[
                            html.P("Partager mes performances", className="profil-toggle-title"),
                            html.P(
                                "Vos gains réels, trades et win rate seront visibles dans la page Témoignages. "
                                "Votre email reste toujours masqué.",
                                className="profil-toggle-desc",
                            ),
                        ]),
                        html.Label(className="profil-toggle-switch", children=[
                            dcc.Checklist(
                                id="profil-public-toggle",
                                options=[{"label": "", "value": "on"}],
                                value=[],
                                className="profil-toggle-check",
                                inputClassName="profil-toggle-input",
                                labelClassName="profil-toggle-label",
                            ),
                            html.Span(className="profil-toggle-slider"),
                        ]),
                    ]),
                    html.Div(id="profil-public-hint", className="profil-public-hint"),
                    html.Div(className="profil-toggle-row", style={"marginTop": "16px"}, children=[
                        html.Div(className="profil-toggle-text", children=[
                            html.P("Apparaître en ligne", className="profil-toggle-title"),
                            html.P(
                                "Affiche un point vert sur votre carte témoignage pour indiquer que vous êtes connecté.",
                                className="profil-toggle-desc",
                            ),
                        ]),
                        html.Label(className="profil-toggle-switch", children=[
                            dcc.Checklist(
                                id="profil-online-toggle",
                                options=[{"label": "", "value": "on"}],
                                value=[],
                                className="profil-toggle-check",
                                inputClassName="profil-toggle-input",
                                labelClassName="profil-toggle-label",
                            ),
                            html.Span(className="profil-toggle-slider"),
                        ]),
                    ]),
                    html.Div(id="profil-online-hint", className="profil-public-hint"),
                ]),
            ]),

            # ── Activité récente ──
            html.Div(className="profil-card", children=[
                html.Div(className="profil-card-hdr", children=[
                    html.Div([
                        html.I(className="fas fa-clock-rotate-left"),
                        html.Span("  Activité récente"),
                    ], className="profil-card-title"),
                    dcc.Link(
                        [html.I(className="fas fa-arrow-right"), "  Voir tout"],
                        href="/mon-suivi",
                        className="profil-card-link",
                    ),
                ]),
                html.Div(id="profil-recent-trades"),
            ]),

            # ── Sécurité & Compte ──
            html.Div(className="profil-card", children=[
                html.Div(className="profil-card-hdr", children=[
                    html.Div([
                        html.I(className="fas fa-shield-halved"),
                        html.Span("  Sécurité & Compte"),
                    ], className="profil-card-title"),
                ]),
                html.Div(id="profil-security"),
            ]),
        ]),
    ]),
])


# ================================================================
# CALLBACK CHARGEMENT INITIAL
# ================================================================

@callback(
    # Sidebar
    Output("profil-avatar", "children"),
    Output("profil-avatar", "style"),
    Output("profil-full-name", "children"),
    Output("profil-email-display", "children"),
    Output("profil-badges", "children"),
    Output("profil-member-label", "children"),
    # KPIs
    Output("profil-kpis", "children"),
    # Public toggle
    Output("profil-public-toggle", "value"),
    # Online toggle
    Output("profil-online-toggle", "value"),
    # Activité
    Output("profil-recent-trades", "children"),
    # Sécurité
    Output("profil-security", "children"),
    # Info body (mode lecture par défaut)
    Output("profil-info-body", "children"),
    Input("profil-init", "n_intervals"),
    Input("profil-url", "pathname"),
    State("session-store", "data"),
)
def load_profil(_init, pathname, session):
    empty = [no_update] * 13
    if not session:
        return empty

    email = session.get("email", "")
    user = get_user_by_email(email)
    if not user:
        return empty

    prenom = user.get("prenom") or ""
    nom = user.get("nom") or ""
    telephone = user.get("telephone") or ""
    is_admin = user.get("is_admin", 0)
    face = bool(user.get("face_image"))
    public = user.get("public_stats", False)
    online = user.get("is_online", False)
    created_raw = user.get("created_at", "") or ""

    # Nom complet & initiales
    full_name = f"{prenom} {nom}".strip() or email.split("@")[0].capitalize()
    initials = (prenom[:1] + nom[:1]).upper() if (prenom or nom) else email[:2].upper()

    # Ancienneté
    member_since = "—"
    member_months = 0
    if created_raw:
        try:
            dt = datetime.fromisoformat(created_raw.split(".")[0])
            member_months = max(0, (datetime.now() - dt).days // 30)
            member_since = dt.strftime("%d %B %Y")
            if member_months >= 12:
                duration = f"{member_months // 12} an{'s' if member_months // 12 > 1 else ''}"
            else:
                duration = f"{member_months} mois" if member_months > 0 else "< 1 mois"
        except Exception:
            duration = "—"
    else:
        duration = "—"

    # Couleur avatar selon win_rate
    stats = get_user_stats(email)
    wr = stats.get("win_rate", 0)
    if stats.get("total_trades", 0) == 0:
        av_color = "linear-gradient(135deg, #0a3060, #00f0ff55)"
    elif wr >= 60:
        av_color = "linear-gradient(135deg, #00331a, #00ff8766)"
    elif wr >= 45:
        av_color = "linear-gradient(135deg, #0a3060, #00f0ff66)"
    else:
        av_color = "linear-gradient(135deg, #330011, #ff4d6d55)"

    avatar_style = {"background": av_color}

    # Badges
    badges = []
    if is_admin:
        badges.append(html.Span([html.I(className="fas fa-crown"), "  Admin"], className="profil-badge profil-badge-gold"))
    badges.append(html.Span(
        [html.I(className="fas fa-camera"), "  Face ID actif"] if face else [html.I(className="fas fa-camera-slash"), "  Face ID inactif"],
        className="profil-badge profil-badge-cyan" if face else "profil-badge profil-badge-muted",
    ))
    if public:
        badges.append(html.Span([html.I(className="fas fa-globe"), "  Stats publiques"], className="profil-badge profil-badge-green"))

    member_label = html.Div(className="profil-member-info", children=[
        html.I(className="fas fa-calendar-check"),
        html.Span(f"  Membre depuis {duration}"),
    ])

    # KPIs réels
    total_pnl = stats.get("total_pnl", 0)
    kpis = [
        {"icon": "fas fa-chart-line", "label": "Gains / Pertes", "val": f"{total_pnl:+,.2f} €",
         "cls": "profil-kpi-pos" if total_pnl >= 0 else "profil-kpi-neg"},
        {"icon": "fas fa-list-check", "label": "Trades suivis", "val": str(stats.get("total_trades", 0)), "cls": ""},
        {"icon": "fas fa-trophy", "label": "Win rate", "val": f"{wr:.1f}%",
         "cls": "profil-kpi-pos" if wr >= 50 else "profil-kpi-neg"},
        {"icon": "fas fa-bolt", "label": "Positions ouvertes", "val": str(stats.get("open_trades", 0)), "cls": ""},
    ]
    kpi_cards = [
        html.Div(className="profil-kpi-card", children=[
            html.Div(className="profil-kpi-icon", children=html.I(className=k["icon"])),
            html.Div(className="profil-kpi-body", children=[
                html.Span(k["label"], className="profil-kpi-lbl"),
                html.Span(k["val"], className=f"profil-kpi-val {k['cls']}"),
            ]),
        ])
        for k in kpis
    ]

    # Activité récente
    trades = get_user_trades(email, 5)
    if not trades:
        recent = html.Div(className="profil-no-activity", children=[
            html.I(className="fas fa-inbox"),
            html.Span("  Aucune activité — commencez par simuler une prédiction"),
        ])
    else:
        sig_map = {"up": "HAUSSIER", "down": "BAISSIER", "neutral": "NEUTRE"}
        sig_cls = {"HAUSSIER": "profil-sig-bull", "BAISSIER": "profil-sig-bear", "NEUTRE": "profil-sig-neutral"}
        rows = []
        for t in trades:
            symbol = t[2]
            entry = t[3] or 0
            qty = t[7] or 0
            pred_dir = t[8] or "neutral"
            pnl = t[10] or 0
            pnl_pct = t[11] or 0
            date_str = str(t[5])[:10] if t[5] else "—"
            sig = sig_map.get(pred_dir, pred_dir.upper())
            pnl_cls = "profil-pnl-pos" if pnl > 0 else "profil-pnl-neg" if pnl < 0 else ""
            rows.append(html.Div(className="profil-trade-row", children=[
                html.Span(symbol, className="profil-trade-symbol"),
                html.Span(sig, className=f"profil-sig-badge {sig_cls.get(sig, '')}"),
                html.Span(f"{qty:,.0f} €" if qty else "—", className="profil-trade-qty"),
                html.Span(f"{pnl:+,.2f} €", className=f"profil-trade-pnl {pnl_cls}"),
                html.Span(f"({pnl_pct:+.1f}%)", className=f"profil-trade-pct {pnl_cls}"),
                html.Span(date_str, className="profil-trade-date"),
            ]))
        recent = html.Div(rows, className="profil-trades-list")

    # Sécurité
    security = html.Div(className="profil-security-grid", children=[
        _sec_item("fas fa-envelope", "Adresse email", email, note=None),
        _sec_item("fas fa-calendar-plus", "Membre depuis", member_since, note=None),
        _sec_item(
            "fas fa-camera" if face else "fas fa-camera-slash",
            "Connexion faciale",
            "Activée ✓" if face else "Non configurée",
            color="#00ff87" if face else None,
        ),
        _sec_item("fas fa-lock", "Mot de passe", "••••••••", note="Modifiable depuis la page de connexion"),
    ])

    # Infos personnelles en mode lecture
    info_read = _info_read_mode(prenom, nom, telephone)

    return (
        initials, avatar_style, full_name, email, badges, member_label,
        kpi_cards,
        ["on"] if public else [],
        ["on"] if online else [],
        recent, security, info_read,
    )


# ================================================================
# TOGGLE EDIT / LECTURE
# ================================================================

@callback(
    Output("profil-edit-mode", "data"),
    Output("profil-edit-toggle-btn", "children"),
    Input("profil-edit-toggle-btn", "n_clicks"),
    State("profil-edit-mode", "data"),
    prevent_initial_call=True,
)
def toggle_edit_mode(n_clicks, is_edit):
    new_mode = not is_edit
    if new_mode:
        btn = [html.I(className="fas fa-xmark"), "  Annuler"]
    else:
        btn = [html.I(className="fas fa-pen"), "  Modifier le profil"]
    return new_mode, btn


@callback(
    Output("profil-info-body", "children", allow_duplicate=True),
    Output("profil-edit-badge", "children"),
    Output("profil-edit-badge", "className"),
    Output("profil-save-feedback", "children"),
    Input("profil-edit-mode", "data"),
    State("session-store", "data"),
    prevent_initial_call=True,
)
def switch_info_mode(is_edit, session):
    if not session:
        return no_update, no_update, no_update, no_update

    user = get_user_by_email(session.get("email", ""))
    prenom = (user or {}).get("prenom", "")
    nom = (user or {}).get("nom", "")
    telephone = (user or {}).get("telephone", "")

    if is_edit:
        return _info_edit_mode(prenom, nom, telephone), "Édition", "profil-mode-badge profil-mode-edit", ""
    return _info_read_mode(prenom, nom, telephone), "Lecture", "profil-mode-badge profil-mode-read", ""


# ================================================================
# SAUVEGARDE PROFIL
# ================================================================

@callback(
    Output("profil-save-feedback", "children", allow_duplicate=True),
    Output("profil-edit-mode", "data", allow_duplicate=True),
    Output("profil-full-name", "children", allow_duplicate=True),
    Output("profil-avatar", "children", allow_duplicate=True),
    Input("profil-save-btn", "n_clicks"),
    State("profil-input-prenom", "value"),
    State("profil-input-nom", "value"),
    State("profil-input-tel", "value"),
    State("session-store", "data"),
    prevent_initial_call=True,
)
def save_profil(n_clicks, prenom, nom, telephone, session):
    if not n_clicks or not session:
        return no_update, no_update, no_update, no_update

    prenom = (prenom or "").strip()
    nom = (nom or "").strip()
    telephone = _format_fr_phone(telephone)

    if not prenom or not nom:
        return (
            html.Div([html.I(className="fas fa-circle-exclamation"), "  Prénom et nom sont requis"],
                     className="profil-feedback-err"),
            True, no_update, no_update,
        )

    ok = update_user_profile(session.get("email", ""), prenom, nom, telephone)
    if ok:
        full = f"{prenom} {nom}".strip()
        initials = (prenom[:1] + nom[:1]).upper()
        return (
            html.Div([html.I(className="fas fa-circle-check"), "  Profil mis à jour !"],
                     className="profil-feedback-ok"),
            False, full, initials,
        )
    return (
        html.Div([html.I(className="fas fa-circle-xmark"), "  Erreur lors de la mise à jour"],
                 className="profil-feedback-err"),
        True, no_update, no_update,
    )


# ================================================================
# TOGGLE VISIBILITÉ PUBLIQUE
# ================================================================

@callback(
    Output("profil-public-hint", "children"),
    Output("profil-badges", "children", allow_duplicate=True),
    Input("profil-public-toggle", "value"),
    State("session-store", "data"),
    prevent_initial_call=True,
)
def toggle_public(value, session):
    if not session:
        return no_update, no_update

    is_public = "on" in (value or [])
    email = session.get("email", "")
    set_public_stats(email, is_public)

    user = get_user_by_email(email)
    is_admin = (user or {}).get("is_admin", 0)
    face = bool((user or {}).get("face_image"))

    badges = []
    if is_admin:
        badges.append(html.Span([html.I(className="fas fa-crown"), "  Admin"], className="profil-badge profil-badge-gold"))
    badges.append(html.Span(
        [html.I(className="fas fa-camera"), "  Face ID actif"] if face else [html.I(className="fas fa-camera-slash"), "  Face ID inactif"],
        className="profil-badge profil-badge-cyan" if face else "profil-badge profil-badge-muted",
    ))
    if is_public:
        badges.append(html.Span([html.I(className="fas fa-globe"), "  Stats publiques"], className="profil-badge profil-badge-green"))

    if is_public:
        hint = html.Div(className="profil-hint-on", children=[
            html.I(className="fas fa-circle-check"),
            "  Vos gains et statistiques sont maintenant visibles dans la page Témoignages.",
        ])
    else:
        hint = html.Div(className="profil-hint-off", children=[
            html.I(className="fas fa-eye-slash"),
            "  Vos statistiques sont masquées — seul votre témoignage texte reste visible.",
        ])

    return hint, badges


# ================================================================
# TOGGLE STATUT EN LIGNE
# ================================================================

@callback(
    Output("profil-online-hint", "children"),
    Input("profil-online-toggle", "value"),
    State("session-store", "data"),
    prevent_initial_call=True,
)
def toggle_online(value, session):
    if not session:
        return no_update

    is_online = "on" in (value or [])
    set_online_status(session.get("email", ""), is_online)

    if is_online:
        return html.Div(className="profil-hint-on", children=[
            html.I(className="fas fa-circle-check"),
            "  Vous apparaissez en ligne sur vos témoignages.",
        ])
    return html.Div(className="profil-hint-off", children=[
        html.I(className="fas fa-eye-slash"),
        "  Vous apparaissez hors ligne — le point vert est masqué.",
    ])


# ================================================================
# HELPERS
# ================================================================

def _info_read_mode(prenom, nom, telephone):
    telephone = _format_fr_phone(telephone) if telephone else ""
    fields = [
        ("fas fa-user", "Prénom", prenom or "—"),
        ("fas fa-user-tie", "Nom", nom or "—"),
        ("fas fa-phone", "Téléphone", telephone or "Non renseigné"),
    ]
    return html.Div(className="profil-info-read", children=[
        html.Div(className="profil-info-field", children=[
            html.Div(className="profil-field-icon", children=html.I(className=icon)),
            html.Div(className="profil-field-body", children=[
                html.Span(label, className="profil-field-lbl"),
                html.Span(value, className="profil-field-val"),
            ]),
        ])
        for icon, label, value in fields
    ])


def _info_edit_mode(prenom, nom, telephone):
    telephone = _split_fr_phone(telephone)
    return html.Div(className="profil-info-edit", children=[
        html.Div(className="profil-input-row", children=[
            html.Div(className="profil-input-grp", children=[
                html.Label("Prénom *", className="profil-input-lbl"),
                html.Div(className="profil-input-wrap", children=[
                    html.I(className="fas fa-user profil-input-icon"),
                    dcc.Input(id="profil-input-prenom", type="text", value=prenom,
                              placeholder="Votre prénom", className="profil-input"),
                ]),
            ]),
            html.Div(className="profil-input-grp", children=[
                html.Label("Nom *", className="profil-input-lbl"),
                html.Div(className="profil-input-wrap", children=[
                    html.I(className="fas fa-user-tie profil-input-icon"),
                    dcc.Input(id="profil-input-nom", type="text", value=nom,
                              placeholder="Votre nom", className="profil-input"),
                ]),
            ]),
        ]),
        html.Div(className="profil-input-grp", children=[
            html.Label("Téléphone", className="profil-input-lbl"),
            html.Div(className="profil-input-wrap profil-phone-field", children=[
                html.I(className="fas fa-phone profil-input-icon"),
                html.Span(FR_PHONE_PREFIX.strip(), className="profil-phone-prefix"),
                dcc.Input(id="profil-input-tel", type="tel", value=telephone,
                          placeholder="6 12 34 56 78", className="profil-input profil-phone-input"),
            ]),
        ]),
        html.Button(
            [html.I(className="fas fa-floppy-disk"), "  Enregistrer les modifications"],
            id="profil-save-btn",
            className="profil-save-btn",
            n_clicks=0,
        ),
    ])


def _sec_item(icon, label, value, color=None, note=None):
    val_style = {"color": color} if color else {}
    return html.Div(className="profil-sec-item", children=[
        html.Div(className="profil-sec-icon", children=html.I(className=icon)),
        html.Div(className="profil-sec-body", children=[
            html.Span(label, className="profil-sec-lbl"),
            html.Span(value, className="profil-sec-val", style=val_style),
            html.Span(note, className="profil-sec-note") if note else None,
        ]),
    ])
