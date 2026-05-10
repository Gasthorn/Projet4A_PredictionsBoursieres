import dash
from dash import html, dcc, Input, Output, State, callback, no_update, ALL
import plotly.graph_objects as go
from services.admin_service import (
    get_all_users, delete_user, get_login_logs, init_login_logs_table,
    get_registration_stats, get_platform_trade_stats, get_top_traders,
)
from services.auth_service import get_user_by_email, promote_to_admin, demote_from_admin
from services.tracking_service import get_pending_testimonials, approve_testimonial, reject_testimonial
import datetime
import json

dash.register_page(__name__, path="/admin", name="Admin Dashboard")

layout = html.Div(className="admin-premium", children=[

    # ── Stores & Interval ─────────────────────────────────────────────────────
    dcc.Store(id="admin-current-section", data="users"),
    dcc.Store(id="admin-pending-delete", data=None),
    dcc.Interval(id="admin-premium-interval", interval=5000, n_intervals=0),

    # ── Toast Notification ────────────────────────────────────────────────────
    html.Div(id="admin-toast", style={"display": "none"}),

    # ── Delete Confirmation Modal ─────────────────────────────────────────────
    html.Div(
        id="delete-confirm-panel",
        style={"display": "none"},
        className="delete-confirm-overlay",
        children=[
            html.Div(className="admin-modal", children=[
                html.Div(className="admin-modal-icon",
                         children=html.I(className="fas fa-exclamation-triangle")),
                html.H3("Confirmer la suppression"),
                html.P(id="delete-confirm-text",
                       children="Êtes-vous sûr de vouloir supprimer cet utilisateur ?"),
                html.Div(className="admin-modal-actions", children=[
                    html.Button("Annuler",
                                id="btn-cancel-delete",
                                className="modal-btn cancel"),
                    html.Button([html.I(className="fas fa-trash"), " Supprimer"],
                                id="btn-confirm-delete",
                                className="modal-btn confirm-delete"),
                ]),
            ]),
        ],
    ),

    # ── Header ────────────────────────────────────────────────────────────────
    html.Div(className="admin-premium-header", children=[
        html.Div(className="header-left", children=[
            html.Div(className="header-title", children=[
                html.I(className="fas fa-shield-halved header-icon"),
                html.H1("Administration", className="header-main-title"),
            ]),
        ]),
        html.Div(className="header-right", children=[
            html.Div(id="admin-premium-datetime", className="header-datetime"),
            html.Button(
                [html.I(className="fas fa-arrow-left"), html.Span(" Retour au site")],
                id="admin-premium-back",
                className="header-back-btn",
            ),
        ]),
    ]),

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    html.Div(className="admin-premium-kpi-grid", id="admin-premium-kpis"),

    # ── Navigation ────────────────────────────────────────────────────────────
    html.Div(className="admin-premium-nav", children=[
        html.Button([html.I(className="fas fa-users"), " Utilisateurs"],
                    id="nav-users", className="nav-btn active"),
        html.Button([html.I(className="fas fa-chart-line"), " Statistiques"],
                    id="nav-stats", className="nav-btn"),
        html.Button([html.I(className="fas fa-history"), " Logs"],
                    id="nav-logs", className="nav-btn"),
        html.Button([html.I(className="fas fa-comment-dots"), " Témoignages"],
                    id="nav-testimonials", className="nav-btn"),
        html.Button([html.I(className="fas fa-sliders-h"), " Configuration"],
                    id="nav-config", className="nav-btn"),
    ]),

    # ── Main Content ──────────────────────────────────────────────────────────
    html.Div(id="admin-premium-content", className="admin-premium-content"),
])


# ─────────────────────────────────────────────────────────────────────────────
# DATETIME
# ─────────────────────────────────────────────────────────────────────────────
@callback(
    Output("admin-premium-datetime", "children"),
    Input("admin-premium-interval", "n_intervals"),
)
def update_datetime(n):
    now = datetime.datetime.now()
    return [
        html.I(className="far fa-calendar-alt"),
        html.Span(" " + now.strftime("%d %B %Y  •  %H:%M")),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────────────────────────────────────
@callback(
    Output("admin-premium-kpis", "children"),
    Input("admin-premium-interval", "n_intervals"),
    State("session-store", "data"),
)
def update_kpis(n, session):
    if not session:
        return []

    users = get_all_users()
    testimonials = get_pending_testimonials()

    total = len(users)
    admins = sum(1 for u in users if u[2])
    with_faces = sum(1 for u in users if u[3] and u[3] != "")
    pending = len(testimonials)

    one_week_ago = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
    new_this_week = sum(1 for u in users if u[6] and str(u[6])[:10] >= one_week_ago)

    face_pct = f"{with_faces / total * 100:.0f}% des users" if total else "0%"
    admin_pct = f"{admins / total * 100:.1f}% du total" if total else "0%"
    week_trend = f"+{new_this_week} cette semaine" if new_this_week > 0 else "aucun cette semaine"

    cards = [
        ("fas fa-user-group", "Utilisateurs", total, week_trend, "positive" if new_this_week > 0 else ""),
        ("fas fa-shield-halved", "Administrateurs", admins, admin_pct, ""),
        ("fas fa-face-smile", "Reconnaissance faciale", with_faces, face_pct, ""),
        ("fas fa-comment-dots", "Témoignages en attente", pending, "à valider", "warning" if pending > 0 else ""),
    ]

    return [
        html.Div(className="kpi-premium-card", children=[
            html.Div(className="kpi-premium-icon", children=html.I(className=icon)),
            html.Div(className="kpi-premium-content", children=[
                html.Span(label, className="kpi-premium-label"),
                html.Span(value, className="kpi-premium-value"),
                html.Span(trend, className=f"kpi-premium-trend {trend_cls}"),
            ]),
        ])
        for icon, label, value, trend, trend_cls in cards
    ]


# ─────────────────────────────────────────────────────────────────────────────
# NAVIGATION
# ─────────────────────────────────────────────────────────────────────────────
@callback(
    Output("admin-premium-content", "children"),
    Output("nav-users", "className"),
    Output("nav-stats", "className"),
    Output("nav-logs", "className"),
    Output("nav-testimonials", "className"),
    Output("nav-config", "className"),
    Output("admin-current-section", "data"),
    Input("nav-users", "n_clicks"),
    Input("nav-stats", "n_clicks"),
    Input("nav-logs", "n_clicks"),
    Input("nav-testimonials", "n_clicks"),
    Input("nav-config", "n_clicks"),
    State("admin-current-section", "data"),
    prevent_initial_call=True,
)
def switch_section(*args):
    current = args[-1]
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, "nav-btn active", "nav-btn", "nav-btn", "nav-btn", "nav-btn", "users"

    btn_id = ctx.triggered[0]["prop_id"].split(".")[0]
    section_map = {
        "nav-users": "users",
        "nav-stats": "stats",
        "nav-logs": "logs",
        "nav-testimonials": "testimonials",
        "nav-config": "config",
    }
    new = section_map.get(btn_id, current)

    def cls(key):
        return "nav-btn active" if new == key else "nav-btn"

    builders = {
        "users": users_section,
        "stats": stats_section,
        "logs": logs_section,
        "testimonials": testimonials_section,
        "config": config_section,
    }
    content = builders.get(new, lambda: html.Div())()

    return (
        content,
        cls("users"), cls("stats"), cls("logs"), cls("testimonials"), cls("config"),
        new,
    )


# ─────────────────────────────────────────────────────────────────────────────
# INIT: charge la section utilisateurs au premier rendu de la page
# ─────────────────────────────────────────────────────────────────────────────
@callback(
    Output("admin-premium-content", "children", allow_duplicate=True),
    Input("admin-premium-interval", "n_intervals"),
    State("session-store", "data"),
    prevent_initial_call="initial_duplicate",
)
def init_admin_content(n_intervals, session):
    if n_intervals > 0:
        return no_update
    return users_section()


# ─────────────────────────────────────────────────────────────────────────────
# SECTION BUILDERS
# ─────────────────────────────────────────────────────────────────────────────
def users_section():
    return html.Div(className="section-premium", children=[
        html.Div(className="section-premium-header", children=[
            html.H2([html.I(className="fas fa-users"), " Gestion des utilisateurs"],
                    className="section-premium-title"),
            html.Div(className="section-premium-actions", children=[
                html.Div(className="search-premium", children=[
                    html.I(className="fas fa-search"),
                    dcc.Input(id="users-search", type="text",
                              placeholder="Rechercher un email…",
                              className="search-premium-input",
                              debounce=True),
                ]),
                html.Button([html.I(className="fas fa-sync-alt"), " Actualiser"],
                            id="users-refresh", className="action-premium-btn"),
            ]),
        ]),
        html.Div(id="users-table-container", className="table-premium-container"),
    ])


def stats_section():
    return html.Div(className="section-premium", children=[
        html.Div(className="section-premium-header", children=[
            html.H2([html.I(className="fas fa-chart-line"), " Statistiques plateforme"],
                    className="section-premium-title"),
        ]),
        html.Div(id="stats-trade-kpis"),
        html.Div(className="stats-premium-grid", children=[
            html.Div(className="chart-premium-card", children=[
                html.H3([html.I(className="fas fa-chart-area"), " Inscriptions (30 derniers jours)"]),
                dcc.Graph(id="stats-growth-chart", config={"displayModeBar": False}),
            ]),
            html.Div(className="chart-premium-card", children=[
                html.H3([html.I(className="fas fa-chart-pie"), " Reconnaissance faciale"]),
                dcc.Graph(id="stats-repartition-chart", config={"displayModeBar": False}),
            ]),
            html.Div(className="chart-premium-card", children=[
                html.H3([html.I(className="fas fa-euro-sign"), " PnL par trader"]),
                dcc.Graph(id="stats-pnl-chart", config={"displayModeBar": False}),
            ]),
            html.Div(className="chart-premium-card", children=[
                html.H3([html.I(className="fas fa-trophy"), " Top 5 traders"]),
                html.Div(id="stats-top-traders"),
            ]),
        ]),
    ])


def logs_section():
    return html.Div(className="section-premium", children=[
        html.Div(className="section-premium-header", children=[
            html.H2([html.I(className="fas fa-history"), " Logs d'activité"],
                    className="section-premium-title"),
            html.Button([html.I(className="fas fa-sync-alt"), " Actualiser"],
                        id="logs-refresh", className="action-premium-btn"),
        ]),
        html.Div(id="logs-premium-container", className="logs-premium-container"),
    ])


def testimonials_section():
    return html.Div(className="section-premium", children=[
        html.Div(className="section-premium-header", children=[
            html.H2([html.I(className="fas fa-comment-dots"), " Gestion des témoignages"],
                    className="section-premium-title"),
            html.Button([html.I(className="fas fa-sync-alt"), " Actualiser"],
                        id="testimonials-refresh", className="action-premium-btn"),
        ]),
        html.Div(id="testimonials-premium-list", className="testimonials-premium-grid"),
    ])


def config_section():
    return html.Div(className="section-premium", children=[
        html.Div(className="section-premium-header", children=[
            html.H2([html.I(className="fas fa-sliders-h"), " Configuration"],
                    className="section-premium-title"),
        ]),
        html.Div(className="config-premium-grid", children=[
            html.Div(className="config-premium-card", children=[
                html.H3([html.I(className="fas fa-tools"), " Paramètres généraux"]),
                html.Div(className="config-premium-item", children=[
                    html.Label("Mode maintenance"),
                    dcc.RadioItems(
                        options=[{"label": " Activé", "value": "on"},
                                 {"label": " Désactivé", "value": "off"}],
                        value="off",
                        className="config-premium-radio",
                        labelStyle={"display": "flex", "alignItems": "center",
                                    "gap": "6px", "color": "#94a3b8",
                                    "marginBottom": "6px", "cursor": "pointer"},
                    ),
                ]),
            ]),
            html.Div(className="config-premium-card", children=[
                html.H3([html.I(className="fas fa-shield-alt"), " Sécurité"]),
                html.Div(className="config-premium-item", children=[
                    html.Label("Tentatives de connexion max"),
                    dcc.Input(type="number", value=5, min=1, max=20,
                              className="config-premium-input"),
                ]),
                html.Div(className="config-premium-item", children=[
                    html.Label("Durée de session (minutes)"),
                    dcc.Input(type="number", value=60, min=5, max=1440,
                              className="config-premium-input"),
                ]),
            ]),
            html.Div(className="config-premium-card", children=[
                html.H3([html.I(className="fas fa-database"), " Base de données"]),
                html.Div(style={"display": "flex", "flexDirection": "column", "gap": "10px"},
                         children=[
                    html.Div(style={"display": "flex", "justifyContent": "space-between",
                                    "alignItems": "center",
                                    "padding": "10px 0",
                                    "borderBottom": "1px solid rgba(140,220,255,0.08)"},
                             children=[
                        html.Span("Statut", style={"color": "#64748b", "fontSize": "0.82rem"}),
                        html.Span([html.I(className="fas fa-circle",
                                          style={"color": "#10b981", "fontSize": "0.5rem",
                                                 "marginRight": "5px"}),
                                   "Opérationnel"],
                                  style={"color": "#10b981", "fontSize": "0.82rem",
                                         "fontWeight": "600"}),
                    ]),
                    html.Div(style={"display": "flex", "justifyContent": "space-between",
                                    "alignItems": "center", "padding": "10px 0"},
                             children=[
                        html.Span("Type", style={"color": "#64748b", "fontSize": "0.82rem"}),
                        html.Span("SQLite 3", style={"color": "#e2e8f0", "fontSize": "0.82rem"}),
                    ]),
                ]),
            ]),
        ]),
    ])


# ─────────────────────────────────────────────────────────────────────────────
# USERS TABLE
# ─────────────────────────────────────────────────────────────────────────────
def _build_users_table(search=None, session=None):
    if not session:
        return html.Div("Accès non autorisé", className="error-premium")

    users = get_all_users()
    if search:
        q = search.lower()
        users = [u for u in users if q in u[1].lower() or q in (u[4] + " " + u[5]).lower()]

    if not users:
        return html.Div([
            html.I(className="fas fa-users-slash"),
            html.H4("Aucun utilisateur trouvé"),
            html.P("Modifiez votre recherche ou actualisez la liste."),
        ], className="empty-premium")

    rows = []
    for user in users:
        user_id, email, is_admin_flag, face_image, prenom, nom, created_at, public_stats = user

        full_name = " ".join(filter(None, [prenom, nom])).strip() or "—"
        member_since = str(created_at)[:10] if created_at else "—"

        face_badge = html.Span(
            [html.I(className="fas fa-check-circle"), " Activé"],
            className="status-badge success",
        ) if (face_image and face_image != "") else html.Span(
            [html.I(className="fas fa-times-circle"), " Désactivé"],
            className="status-badge error",
        )

        role_badge = html.Span(
            [html.I(className="fas fa-crown"), " Admin"],
            className="role-badge admin",
        ) if is_admin_flag else html.Span(
            [html.I(className="fas fa-user"), " Utilisateur"],
            className="role-badge user",
        )

        toggle_icon = "fas fa-user-slash" if is_admin_flag else "fas fa-crown"
        toggle_cls = "table-action-btn demote" if is_admin_flag else "table-action-btn promote"
        toggle_title = "Rétrograder" if is_admin_flag else "Promouvoir admin"

        rows.append(html.Tr([
            html.Td(f"#{user_id}", style={"color": "#64748b", "fontSize": "0.8rem"}),
            html.Td([
                html.Div(full_name, className="user-full-name"),
                html.Div(email, className="user-email-sub"),
            ]),
            html.Td(member_since, style={"color": "#64748b", "fontSize": "0.82rem"}),
            html.Td(face_badge),
            html.Td(role_badge),
            html.Td([
                html.Button(
                    html.I(className=toggle_icon),
                    id={"type": "toggle-admin", "index": user_id},
                    className=toggle_cls,
                    title=toggle_title,
                ),
                html.Button(
                    html.I(className="fas fa-trash"),
                    id={"type": "delete-user", "index": user_id},
                    className="table-action-btn delete",
                    title="Supprimer",
                ),
            ]),
        ]))

    return html.Table([
        html.Thead(html.Tr([
            html.Th("ID"),
            html.Th("Utilisateur"),
            html.Th("Inscrit le"),
            html.Th("Reconnaissance"),
            html.Th("Rôle"),
            html.Th("Actions"),
        ])),
        html.Tbody(rows),
    ], className="table-premium")


@callback(
    Output("users-table-container", "children"),
    Input("users-refresh", "n_clicks"),
    Input("users-search", "value"),
    State("session-store", "data"),
    prevent_initial_call=False,
)
def update_users_table(n_clicks, search, session):
    return _build_users_table(search, session)


# ─────────────────────────────────────────────────────────────────────────────
# DELETE USER – show modal
# ─────────────────────────────────────────────────────────────────────────────
@callback(
    Output("delete-confirm-panel", "style"),
    Output("delete-confirm-text", "children"),
    Output("admin-pending-delete", "data"),
    Input({"type": "delete-user", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def show_delete_modal(n_clicks):
    if not any(n for n in (n_clicks or []) if n):
        return no_update, no_update, no_update

    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update

    try:
        info = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
        user_id = info["index"]
    except Exception:
        return no_update, no_update, no_update

    users = get_all_users()
    user = next((u for u in users if u[0] == user_id), None)
    email = user[1] if user else f"ID {user_id}"

    msg = [
        html.Span(f"Vous êtes sur le point de supprimer "),
        html.Strong(email, style={"color": "#ef4444"}),
        html.Span(". Cette action est irréversible."),
    ]
    return {"display": "flex"}, msg, user_id


# ─────────────────────────────────────────────────────────────────────────────
# DELETE USER – cancel
# ─────────────────────────────────────────────────────────────────────────────
@callback(
    Output("delete-confirm-panel", "style", allow_duplicate=True),
    Output("admin-pending-delete", "data", allow_duplicate=True),
    Input("btn-cancel-delete", "n_clicks"),
    prevent_initial_call=True,
)
def cancel_delete(n):
    if n:
        return {"display": "none"}, None
    return no_update, no_update


# ─────────────────────────────────────────────────────────────────────────────
# DELETE USER – confirm
# ─────────────────────────────────────────────────────────────────────────────
@callback(
    Output("delete-confirm-panel", "style", allow_duplicate=True),
    Output("admin-pending-delete", "data", allow_duplicate=True),
    Output("users-table-container", "children", allow_duplicate=True),
    Output("admin-toast", "children", allow_duplicate=True),
    Output("admin-toast", "style", allow_duplicate=True),
    Output("admin-toast", "className", allow_duplicate=True),
    Input("btn-confirm-delete", "n_clicks"),
    State("admin-pending-delete", "data"),
    State("session-store", "data"),
    prevent_initial_call=True,
)
def confirm_delete(n, user_id, session):
    if not n or user_id is None:
        return no_update, no_update, no_update, no_update, no_update, no_update

    success = delete_user(user_id)
    table = _build_users_table(None, session)

    if success:
        toast = [html.I(className="fas fa-check-circle"), f" Utilisateur #{user_id} supprimé avec succès"]
        toast_cls = "admin-toast success"
    else:
        toast = [html.I(className="fas fa-times-circle"), " Erreur lors de la suppression"]
        toast_cls = "admin-toast error"

    return (
        {"display": "none"},
        None,
        table,
        toast,
        {"display": "flex"},
        toast_cls,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PROMOTE / DEMOTE
# ─────────────────────────────────────────────────────────────────────────────
@callback(
    Output("users-table-container", "children", allow_duplicate=True),
    Output("admin-toast", "children", allow_duplicate=True),
    Output("admin-toast", "style", allow_duplicate=True),
    Output("admin-toast", "className", allow_duplicate=True),
    Input({"type": "toggle-admin", "index": ALL}, "n_clicks"),
    State("session-store", "data"),
    prevent_initial_call=True,
)
def toggle_admin_role(n_clicks, session):
    if not any(n for n in (n_clicks or []) if n):
        return no_update, no_update, no_update, no_update

    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update, no_update

    try:
        info = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
        user_id = info["index"]
    except Exception:
        return no_update, no_update, no_update, no_update

    users = get_all_users()
    user = next((u for u in users if u[0] == user_id), None)
    if not user:
        return no_update, \
               [html.I(className="fas fa-times-circle"), " Utilisateur introuvable"], \
               {"display": "flex"}, "admin-toast error"

    email, is_admin_flag = user[1], user[2]

    if is_admin_flag:
        ok = demote_from_admin(email)
        msg_ok = f" {email} a été rétrogradé"
        msg_fail = " Impossible de rétrograder le dernier administrateur"
    else:
        ok = promote_to_admin(email)
        msg_ok = f" {email} est maintenant administrateur"
        msg_fail = " Erreur lors de la promotion"

    icon_ok = "fas fa-check-circle"
    icon_fail = "fas fa-times-circle"
    toast = [html.I(className=icon_ok if ok else icon_fail),
             msg_ok if ok else msg_fail]
    cls = "admin-toast success" if ok else "admin-toast error"

    return _build_users_table(None, session), toast, {"display": "flex"}, cls


# ─────────────────────────────────────────────────────────────────────────────
# STATS CHARTS
# ─────────────────────────────────────────────────────────────────────────────
def _dark_layout(fig, bar=False, tick_format=None):
    xaxis = dict(showgrid=False, showline=False)
    if tick_format:
        xaxis["tickformat"] = tick_format
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", size=11),
        height=260,
        margin=dict(l=10, r=10, t=10, b=30),
        xaxis=xaxis,
        yaxis=dict(showgrid=True, gridcolor="rgba(99,179,237,0.08)", zeroline=False),
        showlegend=False,
        hovermode="x unified" if not bar else "closest",
    )


@callback(
    Output("stats-growth-chart", "figure"),
    Output("stats-repartition-chart", "figure"),
    Output("stats-pnl-chart", "figure"),
    Output("stats-trade-kpis", "children"),
    Output("stats-top-traders", "children"),
    Input("admin-premium-interval", "n_intervals"),
    State("session-store", "data"),
)
def update_charts(n, session):
    if not session:
        return go.Figure(), go.Figure(), go.Figure(), [], []

    # ── Chart 1: Inscriptions réelles (30j) ──────────────────────────────────
    reg_stats = get_registration_stats(30)
    today = datetime.date.today()
    dates = [today - datetime.timedelta(days=i) for i in range(29, -1, -1)]
    values = [reg_stats.get(str(d), 0) for d in dates]

    growth = go.Figure()
    growth.add_trace(go.Scatter(
        x=dates, y=values,
        mode="lines+markers",
        line=dict(color="#00f0ff", width=2.5),
        marker=dict(size=4, color="#00f0ff"),
        fill="tozeroy",
        fillcolor="rgba(0,240,255,0.07)",
        hovertemplate="%{x|%d %b}<br>%{y} inscription(s)<extra></extra>",
    ))
    _dark_layout(growth, tick_format="%d %b")

    # ── Chart 2: Reconnaissance faciale ──────────────────────────────────────
    users = get_all_users()
    with_f = sum(1 for u in users if u[3] and u[3] != "")
    without_f = max(0, len(users) - with_f)

    repart = go.Figure()
    repart.add_trace(go.Pie(
        labels=["Avec reconnaissance", "Sans reconnaissance"],
        values=[with_f or 1, without_f or 1],
        marker=dict(colors=["#00f0ff", "#7c3aed"], line=dict(color="rgba(0,0,0,0)", width=0)),
        textinfo="label+percent",
        textfont=dict(color="#e2e8f0", size=11),
        hole=0.5,
        hovertemplate="%{label}: %{value}<extra></extra>",
    ))
    repart.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", size=11),
        height=260,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
    )

    # ── Chart 3: PnL par trader (bar) ────────────────────────────────────────
    top8 = get_top_traders(8)
    pnl_fig = go.Figure()
    if top8:
        names = [t['name'] for t in top8]
        pnls = [t['pnl'] for t in top8]
        colors = ["#10b981" if p >= 0 else "#ef4444" for p in pnls]
        pnl_fig.add_trace(go.Bar(
            x=names, y=pnls,
            marker_color=colors,
            text=[f"{p:+,.0f} €" for p in pnls],
            textposition="outside",
            textfont=dict(size=9, color="#e2e8f0"),
            hovertemplate="%{x}<br>PnL: %{y:+,.0f} €<extra></extra>",
        ))
    _dark_layout(pnl_fig, bar=True)

    # ── Trade KPIs ────────────────────────────────────────────────────────────
    ts = get_platform_trade_stats()
    trade_kpis = html.Div(className="stats-trade-kpi-row", children=[
        html.Div(className="stats-trade-kpi-card", children=[
            html.Span("Trades totaux", className="stk-label"),
            html.Span(f"{ts['total']:,}", className="stk-value"),
        ]),
        html.Div(className="stats-trade-kpi-card", children=[
            html.Span("Trades fermés", className="stk-label"),
            html.Span(f"{ts['closed']:,}", className="stk-value"),
        ]),
        html.Div(className="stats-trade-kpi-card", children=[
            html.Span("Win rate", className="stk-label"),
            html.Span(
                f"{ts['win_rate']:.1f}%",
                className="stk-value positive" if ts['win_rate'] >= 50 else "stk-value",
            ),
        ]),
        html.Div(className="stats-trade-kpi-card", children=[
            html.Span("PnL total plateforme", className="stk-label"),
            html.Span(
                f"{ts['total_pnl']:+,.0f} €" if ts['total_pnl'] != 0 else "—",
                className="stk-value positive" if ts['total_pnl'] >= 0 else "stk-value negative",
            ),
        ]),
        html.Div(className="stats-trade-kpi-card", children=[
            html.Span("Traders actifs", className="stk-label"),
            html.Span(f"{ts['active_users']:,}", className="stk-value"),
        ]),
    ])

    # ── Top 5 traders table ───────────────────────────────────────────────────
    top5 = get_top_traders(5)
    if not top5:
        traders_el = html.P("Aucun trade enregistré pour le moment.",
                            style={"color": "#64748b", "padding": "20px 0", "fontSize": "0.88rem"})
    else:
        rows = []
        for i, t in enumerate(top5):
            pnl_cls = "tt-positive" if t['pnl'] >= 0 else "tt-negative"
            rows.append(html.Tr([
                html.Td(f"#{i+1}", className="tt-rank"),
                html.Td(t['name']),
                html.Td(f"{t['trades']}"),
                html.Td(f"{t['win_rate']:.0f}%", className=pnl_cls),
                html.Td(f"{t['pnl']:+,.0f} €", className=pnl_cls),
            ]))
        traders_el = html.Table([
            html.Thead(html.Tr([
                html.Th("Rang"), html.Th("Trader"), html.Th("Trades"),
                html.Th("Win Rate"), html.Th("PnL"),
            ])),
            html.Tbody(rows),
        ], className="top-traders-table")

    return growth, repart, pnl_fig, trade_kpis, traders_el


# ─────────────────────────────────────────────────────────────────────────────
# LOGS
# ─────────────────────────────────────────────────────────────────────────────
@callback(
    Output("logs-premium-container", "children"),
    Input("admin-premium-interval", "n_intervals"),
    Input("logs-refresh", "n_clicks"),
    State("session-store", "data"),
)
def update_logs(*args):
    session = args[-1]
    if not session:
        return html.Div("Accès non autorisé", className="error-premium")

    init_login_logs_table()
    logs = get_login_logs(limit=60)

    if not logs:
        return html.Div([
            html.I(className="fas fa-inbox"),
            html.H4("Aucun log disponible"),
            html.P("Les connexions apparaîtront ici."),
        ], className="empty-premium")

    rows = []
    for log_entry in logs:
        log_id, email, success, method, timestamp = log_entry

        status_el = html.Span(
            [html.I(className="fas fa-check-circle"), " Succès"],
            className="log-success",
        ) if success else html.Span(
            [html.I(className="fas fa-times-circle"), " Échec"],
            className="log-failed",
        )

        method_lower = (method or "inconnu").lower()
        method_cls = "log-method-badge face" if "face" in method_lower else "log-method-badge password"
        method_el = html.Span(method or "—", className=method_cls)

        ts = timestamp[:16] if timestamp else "—"
        rows.append(html.Tr([
            html.Td(f"#{log_id}", style={"color": "#64748b", "fontSize": "0.78rem"}),
            html.Td(email or "—"),
            html.Td(status_el),
            html.Td(method_el),
            html.Td(ts, style={"color": "#64748b", "fontSize": "0.82rem"}),
        ]))

    return html.Table([
        html.Thead(html.Tr([
            html.Th("ID"),
            html.Th("Email"),
            html.Th("Statut"),
            html.Th("Méthode"),
            html.Th("Date"),
        ])),
        html.Tbody(rows),
    ], className="logs-premium-table")


# ─────────────────────────────────────────────────────────────────────────────
# TESTIMONIALS – display
# ─────────────────────────────────────────────────────────────────────────────
@callback(
    Output("testimonials-premium-list", "children"),
    Input("testimonials-refresh", "n_clicks"),
    State("session-store", "data"),
)
def update_testimonials(n_clicks, session):
    if not session:
        return html.Div("Accès non autorisé", className="error-premium")

    items = get_pending_testimonials()

    if not items:
        return html.Div([
            html.I(className="fas fa-check-double"),
            html.H4("Aucun témoignage en attente"),
            html.P("Tous les témoignages ont été traités."),
        ], className="empty-premium")

    cards = []
    for t in items:
        t_id, email, name, content, rating, investment, gain, period, date = t

        meta = []
        if investment:
            meta.append(html.Span([html.I(className="fas fa-euro-sign"), f" {investment}€"]))
        if gain:
            meta.append(html.Span([html.I(className="fas fa-chart-line"), f" +{gain}€"]))
        if period:
            meta.append(html.Span([html.I(className="fas fa-clock"), f" {period}"]))
        if date:
            meta.append(html.Span([html.I(className="fas fa-calendar"), f" {date[:10]}"]))

        cards.append(html.Div(className="testimonial-premium-card", children=[
            html.Div(className="testimonial-premium-header", children=[
                html.Div(className="testimonial-premium-user", children=[
                    html.Div(className="user-avatar", children=(name or "?")[0].upper()),
                    html.Div(className="user-info", children=[
                        html.H4(name or "Anonyme"),
                        html.Span(email or ""),
                    ]),
                ]),
                html.Div("★" * (rating or 0), className="testimonial-premium-rating"),
            ]),
            html.P(content or "", className="testimonial-premium-content"),
            html.Div(meta, className="testimonial-premium-meta"),
            html.Div(className="testimonial-premium-actions", children=[
                html.Button(
                    [html.I(className="fas fa-check"), " Approuver"],
                    id={"type": "approve-premium", "index": t_id},
                    className="action-premium approve",
                ),
                html.Button(
                    [html.I(className="fas fa-times"), " Rejeter"],
                    id={"type": "reject-premium", "index": t_id},
                    className="action-premium reject",
                ),
            ]),
        ]))

    return cards


# ─────────────────────────────────────────────────────────────────────────────
# TESTIMONIALS – actions
# ─────────────────────────────────────────────────────────────────────────────
@callback(
    Output("testimonials-premium-list", "children", allow_duplicate=True),
    Output("admin-toast", "children", allow_duplicate=True),
    Output("admin-toast", "style", allow_duplicate=True),
    Output("admin-toast", "className", allow_duplicate=True),
    Input({"type": "approve-premium", "index": ALL}, "n_clicks"),
    Input({"type": "reject-premium", "index": ALL}, "n_clicks"),
    State("session-store", "data"),
    prevent_initial_call=True,
)
def handle_testimonial_actions(approve_clicks, reject_clicks, session):
    if not session:
        return no_update, no_update, no_update, no_update

    ctx = dash.callback_context
    if not ctx.triggered:
        return no_update, no_update, no_update, no_update

    if not any(n for n in (approve_clicks or []) + (reject_clicks or []) if n):
        return no_update, no_update, no_update, no_update

    try:
        info = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
        action = info["type"]
        t_id = info["index"]

        if "approve" in action:
            approve_testimonial(t_id)
            toast = [html.I(className="fas fa-check-circle"), " Témoignage approuvé"]
            cls = "admin-toast success"
        else:
            reject_testimonial(t_id)
            toast = [html.I(className="fas fa-times-circle"), " Témoignage rejeté"]
            cls = "admin-toast info"
    except Exception:
        toast = [html.I(className="fas fa-exclamation-circle"), " Une erreur est survenue"]
        cls = "admin-toast error"

    return update_testimonials(None, session), toast, {"display": "flex"}, cls


# ─────────────────────────────────────────────────────────────────────────────
# BACK BUTTON
# ─────────────────────────────────────────────────────────────────────────────
@callback(
    Output("url", "pathname"),
    Input("admin-premium-back", "n_clicks"),
    prevent_initial_call=True,
)
def go_back(n):
    return "/"
