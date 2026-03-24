import dash
from dash import html, dcc, Input, Output, State, callback, no_update, ALL
import plotly.graph_objects as go
import plotly.express as px
from services.admin_service import *
from services.auth_service import get_user_by_email
from services.tracking_service import get_pending_testimonials, approve_testimonial, reject_testimonial
import datetime
import json
import pandas as pd
import numpy as np

dash.register_page(__name__, path="/admin", name="Admin Dashboard")

layout = html.Div(className="admin-premium", children=[
    # Header avec stats rapides
    html.Div(className="admin-premium-header", children=[
        html.Div(className="header-left", children=[
            html.Div(className="header-title", children=[
                html.I(className="fas fa-crown header-icon"),
                html.H1("Administration", className="header-main-title"),
            ]),
            html.Div(className="header-badge", children=[
                html.I(className="fas fa-shield-alt"),
                "Super Admin"
            ]),
        ]),
        html.Div(className="header-right", children=[
            html.Div(className="header-datetime", id="admin-premium-datetime"),
            html.Button([
                html.I(className="fas fa-arrow-left"),
                html.Span("Retour au site")
            ], id="admin-premium-back", className="header-back-btn"),
        ]),
    ]),

    # Cartes de KPIs
    html.Div(className="admin-premium-kpi-grid", id="admin-premium-kpis"),

    # Navigation
    html.Div(className="admin-premium-nav", children=[
        html.Button([html.I(className="fas fa-users"), "Utilisateurs"], 
                   id="nav-users", className="nav-btn active"),
        html.Button([html.I(className="fas fa-chart-line"), "Statistiques"], 
                   id="nav-stats", className="nav-btn"),
        html.Button([html.I(className="fas fa-history"), "Logs"], 
                   id="nav-logs", className="nav-btn"),
        html.Button([html.I(className="fas fa-comment-dots"), "Témoignages"], 
                   id="nav-testimonials", className="nav-btn"),
        html.Button([html.I(className="fas fa-sliders-h"), "Configuration"], 
                   id="nav-config", className="nav-btn"),
    ]),

    # Contenu principal
    html.Div(id="admin-premium-content", className="admin-premium-content"),

    # Stores
    dcc.Store(id="admin-current-section", data="users"),
    dcc.Interval(id="admin-premium-interval", interval=10000, n_intervals=0),
])

# Callback pour la date
@callback(
    Output("admin-premium-datetime", "children"),
    Input("admin-premium-interval", "n_intervals")
)
def update_datetime(n):
    now = datetime.datetime.now()
    return [
        html.I(className="far fa-calendar-alt"),
        html.Span(now.strftime("%d %B %Y • %H:%M"))
    ]

# Callback pour les KPIs
@callback(
    Output("admin-premium-kpis", "children"),
    Input("admin-premium-interval", "n_intervals"),
    State("session-store", "data")
)
def update_kpis(n, session):
    if not session:
        return []
    
    users = get_all_users()
    testimonials = get_pending_testimonials()
    
    total_users = len(users)
    admins = sum(1 for u in users if u[2])
    with_faces = sum(1 for u in users if u[3] and u[3] != '')
    pending_testimonials = len(testimonials)
    
    return [
        html.Div(className="kpi-premium-card", children=[
            html.Div(className="kpi-premium-icon", children=html.I(className="fas fa-users")),
            html.Div(className="kpi-premium-content", children=[
                html.Span("Utilisateurs", className="kpi-premium-label"),
                html.Span(total_users, className="kpi-premium-value"),
                html.Span(f"+{total_users//10} cette semaine", className="kpi-premium-trend positive"),
            ]),
        ]),
        html.Div(className="kpi-premium-card", children=[
            html.Div(className="kpi-premium-icon", children=html.I(className="fas fa-crown")),
            html.Div(className="kpi-premium-content", children=[
                html.Span("Administrateurs", className="kpi-premium-label"),
                html.Span(admins, className="kpi-premium-value"),
                html.Span(f"{admins/total_users*100:.1f}% du total", className="kpi-premium-trend"),
            ]),
        ]),
        html.Div(className="kpi-premium-card", children=[
            html.Div(className="kpi-premium-icon", children=html.I(className="fas fa-face-smile")),
            html.Div(className="kpi-premium-content", children=[
                html.Span("Reconnaissance", className="kpi-premium-label"),
                html.Span(with_faces, className="kpi-premium-value"),
                html.Span(f"{with_faces/total_users*100:.1f}% des utilisateurs", className="kpi-premium-trend"),
            ]),
        ]),
        html.Div(className="kpi-premium-card", children=[
            html.Div(className="kpi-premium-icon", children=html.I(className="fas fa-clock")),
            html.Div(className="kpi-premium-content", children=[
                html.Span("En attente", className="kpi-premium-label"),
                html.Span(pending_testimonials, className="kpi-premium-value"),
                html.Span("témoignages à valider", className="kpi-premium-trend"),
            ]),
        ]),
    ]

# Callback pour la navigation
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
    prevent_initial_call=True
)
def switch_section(users_clicks, stats_clicks, logs_clicks, testimonials_clicks, config_clicks, current):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, "nav-btn active", "nav-btn", "nav-btn", "nav-btn", "nav-btn", "users"
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    sections = {
        "nav-users": "users",
        "nav-stats": "stats",
        "nav-logs": "logs",
        "nav-testimonials": "testimonials",
        "nav-config": "config"
    }
    
    new_section = sections.get(button_id, current)
    
    # Classes pour les boutons
    classes = {
        "nav-users": "nav-btn active" if new_section == "users" else "nav-btn",
        "nav-stats": "nav-btn active" if new_section == "stats" else "nav-btn",
        "nav-logs": "nav-btn active" if new_section == "logs" else "nav-btn",
        "nav-testimonials": "nav-btn active" if new_section == "testimonials" else "nav-btn",
        "nav-config": "nav-btn active" if new_section == "config" else "nav-btn"
    }
    
    # Contenu selon la section
    if new_section == "users":
        content = users_section()
    elif new_section == "stats":
        content = stats_section()
    elif new_section == "logs":
        content = logs_section()
    elif new_section == "testimonials":
        content = testimonials_section()
    elif new_section == "config":
        content = config_section()
    else:
        content = html.Div()
    
    return (content, classes["nav-users"], classes["nav-stats"], classes["nav-logs"], 
            classes["nav-testimonials"], classes["nav-config"], new_section)

def users_section():
    """Section utilisateurs"""
    return html.Div(className="section-premium", children=[
        html.Div(className="section-premium-header", children=[
            html.H2([html.I(className="fas fa-users"), "Gestion des utilisateurs"], 
                   className="section-premium-title"),
            html.Div(className="section-premium-actions", children=[
                html.Div(className="search-premium", children=[
                    html.I(className="fas fa-search"),
                    dcc.Input(
                        id="users-search",
                        type="text",
                        placeholder="Rechercher un email...",
                        className="search-premium-input"
                    ),
                ]),
                html.Button([html.I(className="fas fa-sync-alt"), "Actualiser"], 
                           id="users-refresh", className="action-premium-btn"),
            ]),
        ]),
        html.Div(id="users-table-container", className="table-premium-container"),
    ])

def stats_section():
    """Section statistiques"""
    return html.Div(className="section-premium", children=[
        html.Div(className="section-premium-header", children=[
            html.H2([html.I(className="fas fa-chart-line"), "Statistiques"], 
                   className="section-premium-title"),
        ]),
        html.Div(className="stats-premium-grid", children=[
            html.Div(className="chart-premium-card", children=[
                html.H3("Évolution des inscriptions"),
                dcc.Graph(id="stats-growth-chart", config={'displayModeBar': False}),
            ]),
            html.Div(className="chart-premium-card", children=[
                html.H3("Répartition des utilisateurs"),
                dcc.Graph(id="stats-repartition-chart", config={'displayModeBar': False}),
            ]),
        ]),
    ])

def logs_section():
    """Section logs"""
    return html.Div(className="section-premium", children=[
        html.Div(className="section-premium-header", children=[
            html.H2([html.I(className="fas fa-history"), "Logs d'activité"], 
                   className="section-premium-title"),
        ]),
        html.Div(id="logs-premium-container", className="logs-premium-container"),
    ])

def testimonials_section():
    """Section témoignages"""
    return html.Div(className="section-premium", children=[
        html.Div(className="section-premium-header", children=[
            html.H2([html.I(className="fas fa-comment-dots"), "Gestion des témoignages"], 
                   className="section-premium-title"),
            html.Button([html.I(className="fas fa-sync-alt"), "Actualiser"], 
                       id="testimonials-refresh", className="action-premium-btn"),
        ]),
        html.Div(id="testimonials-premium-list", className="testimonials-premium-grid"),
    ])

def config_section():
    """Section configuration"""
    return html.Div(className="section-premium", children=[
        html.Div(className="section-premium-header", children=[
            html.H2([html.I(className="fas fa-sliders-h"), "Configuration"], 
                   className="section-premium-title"),
        ]),
        html.Div(className="config-premium-grid", children=[
            html.Div(className="config-premium-card", children=[
                html.H3("Paramètres généraux"),
                html.Div(className="config-premium-item", children=[
                    html.Label("Mode maintenance"),
                    dcc.RadioItems(
                        options=[
                            {"label": "Activé", "value": "on"},
                            {"label": "Désactivé", "value": "off"},
                        ],
                        value="off",
                        className="config-premium-radio"
                    ),
                ]),
            ]),
            html.Div(className="config-premium-card", children=[
                html.H3("Sécurité"),
                html.Div(className="config-premium-item", children=[
                    html.Label("Tentatives max"),
                    dcc.Input(type="number", value=5, className="config-premium-input"),
                ]),
            ]),
        ]),
    ])

# Callback pour la table des utilisateurs
@callback(
    Output("users-table-container", "children"),
    Input("users-refresh", "n_clicks"),
    Input("users-search", "value"),
    State("session-store", "data"),
    prevent_initial_call=False
)
def update_users_table(n_clicks, search, session):
    if not session:
        return html.Div("Accès non autorisé", className="error-premium")
    
    users = get_all_users()
    
    if search:
        users = [u for u in users if search.lower() in u[1].lower()]
    
    if not users:
        return html.Div([
            html.I(className="fas fa-users-slash"),
            html.H4("Aucun utilisateur trouvé"),
        ], className="empty-premium")
    
    rows = []
    for user in users:
        user_id, email, is_admin, face_image = user
        
        # Statut visage
        face_status = html.Span([
            html.I(className="fas fa-check-circle"),
            "Activé"
        ], className="status-badge success") if face_image else html.Span([
            html.I(className="fas fa-times-circle"),
            "Désactivé"
        ], className="status-badge error")
        
        # Badge admin
        role_badge = html.Span([
            html.I(className="fas fa-crown"),
            "Admin"
        ], className="role-badge admin") if is_admin else html.Span([
            html.I(className="fas fa-user"),
            "User"
        ], className="role-badge user")
        
        rows.append(html.Tr([
            html.Td(f"#{user_id}"),
            html.Td(email),
            html.Td(face_status),
            html.Td(role_badge),
            html.Td([
                html.Button(html.I(className="fas fa-edit"), 
                           id={"type": "edit-user", "index": user_id},
                           className="table-action-btn edit"),
                html.Button(html.I(className="fas fa-trash"), 
                           id={"type": "delete-user", "index": user_id},
                           className="table-action-btn delete"),
            ]),
        ]))
    
    return html.Table([
        html.Thead(html.Tr([
            html.Th("ID"),
            html.Th("Email"),
            html.Th("Reconnaissance"),
            html.Th("Rôle"),
            html.Th("Actions"),
        ])),
        html.Tbody(rows)
    ], className="table-premium")

# Callback pour les graphiques
@callback(
    Output("stats-growth-chart", "figure"),
    Output("stats-repartition-chart", "figure"),
    Input("admin-premium-interval", "n_intervals"),
    State("session-store", "data")
)
def update_charts(n, session):
    if not session:
        return go.Figure(), go.Figure()
    
    # Données simulées
    dates = pd.date_range(end=datetime.datetime.now(), periods=30, freq="D")
    values = [10 + i + np.random.randint(-2, 3) for i in range(30)]
    
    # Graphique d'évolution
    growth_fig = go.Figure()
    growth_fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode='lines',
        line=dict(color="#00f0ff", width=3),
        fill='tozeroy',
        fillcolor="rgba(0, 240, 255, 0.1)"
    ))
    growth_fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0e0"),
        height=300,
        margin=dict(l=20, r=20, t=10, b=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#2a2a2a"),
        showlegend=False
    )
    
    # Graphique de répartition
    users = get_all_users()
    with_faces = sum(1 for u in users if u[3] and u[3] != '')
    without_faces = len(users) - with_faces
    admins = sum(1 for u in users if u[2])
    normals = len(users) - admins
    
    repart_fig = go.Figure()
    repart_fig.add_trace(go.Pie(
        labels=['Avec visage', 'Sans visage'],
        values=[with_faces, without_faces],
        marker=dict(colors=['#7cffb2', '#ff7b7b']),
        textinfo='label+percent',
        textfont=dict(color='#010214'),
        hole=0.4
    ))
    repart_fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0e0"),
        height=300,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False
    )
    
    return growth_fig, repart_fig

# Callback pour les témoignages
@callback(
    Output("testimonials-premium-list", "children"),
    Input("testimonials-refresh", "n_clicks"),
    State("session-store", "data")
)
def update_testimonials(n_clicks, session):
    if not session:
        return html.Div("Accès non autorisé", className="error-premium")
    
    testimonials = get_pending_testimonials()
    
    if not testimonials:
        return html.Div([
            html.I(className="fas fa-check-circle"),
            html.H3("Aucun témoignage en attente"),
            html.P("Tous les témoignages ont été traités.")
        ], className="empty-premium")
    
    cards = []
    for t in testimonials:
        t_id, email, name, content, rating, investment, gain, period, date = t
        
        card = html.Div(className="testimonial-premium-card", children=[
            html.Div(className="testimonial-premium-header", children=[
                html.Div(className="testimonial-premium-user", children=[
                    html.Div(className="user-avatar", children=name[0].upper()),
                    html.Div(className="user-info", children=[
                        html.H4(name),
                        html.Span(email),
                    ]),
                ]),
                html.Div(className="testimonial-premium-rating", children=[
                    "★" * rating,
                ]),
            ]),
            html.P(content, className="testimonial-premium-content"),
            html.Div(className="testimonial-premium-meta", children=[
                html.Span([html.I(className="fas fa-euro-sign"), f" {investment}€"]) if investment else None,
                html.Span([html.I(className="fas fa-chart-line"), f"+{gain}€"]) if gain else None,
                html.Span([html.I(className="fas fa-clock"), period]) if period else None,
                html.Span([html.I(className="fas fa-calendar"), date[:10]]) if date else None,
            ]),
            html.Div(className="testimonial-premium-actions", children=[
                html.Button([html.I(className="fas fa-check"), "Approuver"], 
                           id={"type": "approve-premium", "index": t_id},
                           className="action-premium approve"),
                html.Button([html.I(className="fas fa-times"), "Rejeter"], 
                           id={"type": "reject-premium", "index": t_id},
                           className="action-premium reject"),
            ]),
        ])
        cards.append(card)
    
    return cards

# Callback pour les actions sur les témoignages
@callback(
    Output("testimonials-premium-list", "children", allow_duplicate=True),
    Input({"type": "approve-premium", "index": ALL}, "n_clicks"),
    Input({"type": "reject-premium", "index": ALL}, "n_clicks"),
    State("session-store", "data"),
    prevent_initial_call=True
)
def handle_testimonial_actions(approve_clicks, reject_clicks, session):
    if not session:
        return dash.no_update
    
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
    
    trigger = ctx.triggered[0]
    prop_id = trigger["prop_id"]
    
    try:
        button_info = json.loads(prop_id.split(".")[0])
        action = button_info["type"]
        t_id = button_info["index"]
        
        if "approve" in action:
            approve_testimonial(t_id)
        else:
            reject_testimonial(t_id)
    except:
        pass
    
    # Rafraîchir
    return update_testimonials(None, session)

# Callback retour
@callback(
    Output("url", "pathname"),
    Input("admin-premium-back", "n_clicks"),
    prevent_initial_call=True
)
def go_back(n):
    return "/"