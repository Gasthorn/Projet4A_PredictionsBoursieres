import dash
from dash import html, dcc, Input, Output, State, callback, ALL
import plotly.graph_objects as go
from services.tracking_service import get_global_stats, get_approved_testimonials, add_testimonial, get_user_testimonial
from services.auth_service import get_user_by_email
import pandas as pd
import numpy as np
from datetime import datetime

dash.register_page(__name__, path="/temoignages", name="Témoignages")

# Données statiques enrichies pour l'exemple
sample_testimonials = [
    {
        "name": "Thomas Martin",
        "initials": "TM",
        "role": "Investisseur particulier",
        "content": "Les prédictions m'ont permis de multiplier mon capital par 2 en 6 mois. Une précision incroyable !",
        "rating": 5,
        "gain": "+8 240 €",
        "country": "🇫🇷",
        "trades": 47,
        "win_rate": 81
    },
    {
        "name": "Sophie Lambert",
        "initials": "SL",
        "role": "Débutante",
        "content": "Je n'y connaissais rien au trading. Grâce aux analyses claires et précises, j'ai réalisé mes premiers bénéfices.",
        "rating": 5,
        "gain": "+3 350 €",
        "country": "🇫🇷",
        "trades": 23,
        "win_rate": 74
    },
    {
        "name": "Marc Dubois",
        "initials": "MD",
        "role": "Retraité",
        "content": "Un complément de revenu idéal. Les prédictions sont fiables et le suivi est excellent.",
        "rating": 5,
        "gain": "+6 450 €",
        "country": "🇫🇷",
        "trades": 38,
        "win_rate": 76
    },
    {
        "name": "Julie Petit",
        "initials": "JP",
        "role": "Trader occasionnel",
        "content": "La meilleure plateforme que j'ai testée. Les résultats sont au rendez-vous.",
        "rating": 5,
        "gain": "+12 300 €",
        "country": "🇫🇷",
        "trades": 52,
        "win_rate": 85
    },
    {
        "name": "Alexandre Richard",
        "initials": "AR",
        "role": "Investisseur pro",
        "content": "Utilisé en complément de mon analyse technique. Le taux de réussite est impressionnant.",
        "rating": 5,
        "gain": "+15 780 €",
        "country": "🇫🇷",
        "trades": 89,
        "win_rate": 79
    },
    {
        "name": "Claire Moreau",
        "initials": "CM",
        "role": "Cadre supérieur",
        "content": "Gain de temps et efficacité. Je recommande à tous ceux qui veulent investir sans stress.",
        "rating": 5,
        "gain": "+9 420 €",
        "country": "🇫🇷",
        "trades": 41,
        "win_rate": 73
    },
    {
        "name": "Hassen Ahmed",
        "initials": "HA",
        "role": "Trader actif",
        "content": "Une plateforme exceptionnelle avec des prédictions très précises. J'ai augmenté mon capital significativement.",
        "rating": 5,
        "gain": "+5 000 €",
        "country": "🇫🇷",
        "trades": 35,
        "win_rate": 77
    }
]

layout = html.Div(className="testimonials-premium-page", children=[
    # Hero Section
    html.Div(className="testimonials-premium-hero", children=[
        html.Div(className="hero-content", children=[
            html.H1("Ils nous font confiance", className="hero-premium-title"),
            html.P("Rejoignez une communauté de + de 1 200 traders", className="hero-premium-subtitle"),
            html.Div(className="hero-premium-stats", id="testimonials-premium-stats"),
        ]),
        html.Div(className="hero-premium-decoration"),
    ]),

    # Grille de témoignages
    html.Div(className="testimonials-premium-grid", id="testimonials-premium-grid"),

    # Formulaire d'ajout
    html.Div(id="testimonials-premium-form", className="testimonials-premium-form-wrapper"),
])

@callback(
    Output("testimonials-premium-stats", "children"),
    Output("testimonials-premium-grid", "children"),
    Output("testimonials-premium-form", "children"),
    Input("url", "pathname"),
    State("session-store", "data")
)
def load_testimonials_page(pathname, session):
    # Statistiques globales
    stats = get_global_stats()
    
    # Stats élégantes
    stats_display = html.Div([
        html.Div(className="premium-stat-card", children=[
            html.Div(className="premium-stat-icon", children=html.I(className="fas fa-users")),
            html.Div(className="premium-stat-content", children=[
                html.Span("Utilisateurs actifs", className="premium-stat-label"),
                html.Span("1,247", className="premium-stat-value"),
                html.Span("+12% ce mois", className="premium-stat-trend positive"),
            ])
        ]),
        html.Div(className="premium-stat-card", children=[
            html.Div(className="premium-stat-icon", children=html.I(className="fas fa-star")),
            html.Div(className="premium-stat-content", children=[
                html.Span("Note moyenne", className="premium-stat-label"),
                html.Span("4.9", className="premium-stat-value"),
                html.Span("sur 5", className="premium-stat-trend"),
            ])
        ]),
        html.Div(className="premium-stat-card", children=[
            html.Div(className="premium-stat-icon", children=html.I(className="fas fa-trophy")),
            html.Div(className="premium-stat-content", children=[
                html.Span("Trades gagnants", className="premium-stat-label"),
                html.Span(f"{stats['winning_trades']:,}", className="premium-stat-value"),
                html.Span(f"{stats.get('win_rate', 78):.1f}% réussite", className="premium-stat-trend positive"),
            ])
        ]),
        html.Div(className="premium-stat-card", children=[
            html.Div(className="premium-stat-icon", children=html.I(className="fas fa-euro-sign")),
            html.Div(className="premium-stat-content", children=[
                html.Span("Gains cumulés", className="premium-stat-label"),
                html.Span(f"{stats['total_pnl']:,.0f}€", className="premium-stat-value"),
                html.Span("+235k€ ce mois", className="premium-stat-trend positive"),
            ])
        ]),
    ], className="premium-stats-grid")
    
    # Témoignages enrichis
    testimonials = get_approved_testimonials(8)
    display_testimonials = testimonials if testimonials else sample_testimonials
    
    cards = []
    for t in display_testimonials:
        if isinstance(t, tuple):  # Données de la BDD
            name, content, rating, investment, gain, period, date = t
            initials = name[:2].upper() if name else "U"
            role = "Utilisateur"
            gain_text = f"+{gain:,.0f} €" if gain else ""
            trades_count = np.random.randint(20, 100)
            win_rate = np.random.randint(65, 90)
            country = "🇫🇷"
        else:  # Données statiques
            name = t["name"]
            initials = t["initials"]
            role = t["role"]
            content = t["content"]
            rating = t["rating"]
            gain_text = t["gain"]
            trades_count = t.get("trades", np.random.randint(20, 100))
            win_rate = t.get("win_rate", np.random.randint(65, 90))
            country = t.get("country", "🇫🇷")
        
        card = html.Div(className="premium-testimonial-card", children=[
            # En-tête
            html.Div(className="premium-card-header", children=[
                html.Div(className="premium-card-avatar-wrapper", children=[
                    html.Div(className="premium-card-avatar", children=initials),
                    html.Div(className="premium-card-online", title="En ligne"),
                ]),
                html.Div(className="premium-card-info", children=[
                    html.Div(className="premium-card-name-wrapper", children=[
                        html.H3(name, className="premium-card-name"),
                        html.Span("✔️", className="premium-card-verified", title="Utilisateur vérifié"),
                    ]),
                    html.Div(className="premium-card-role", children=[
                        html.Span(role, className="premium-card-role-text"),
                        html.Span(country, className="premium-card-country"),
                    ]),
                ]),
                html.Div(className="premium-card-rating", children=[
                    html.Span("★" * rating, className="premium-card-stars"),
                ]),
            ]),
            
            # Contenu
            html.Div(className="premium-card-quote", children=[
                html.I(className="fas fa-quote-left premium-quote-icon"),
                html.P(content, className="premium-card-content"),
            ]),
            
            # Statistiques
            html.Div(className="premium-card-stats", children=[
                html.Div(className="premium-stat-item", children=[
                    html.Span("Trades", className="stat-item-label"),
                    html.Span(trades_count, className="stat-item-value"),
                ]),
                html.Div(className="premium-stat-item", children=[
                    html.Span("Win rate", className="stat-item-label"),
                    html.Span(f"{win_rate}%", className="stat-item-value positive"),
                ]),
                html.Div(className="premium-stat-item", children=[
                    html.Span("Gain", className="stat-item-label"),
                    html.Span(gain_text, className="stat-item-value gain"),
                ]),
            ]),
            
            # Footer
            html.Div(className="premium-card-footer", children=[
                html.Div(className="premium-footer-left", children=[
                    html.I(className="fas fa-calendar-alt"),
                    html.Span("Membre depuis 6 mois"),
                ]),
                html.Div(className="premium-footer-right", children=[
                    html.I(className="fas fa-chart-line"),
                    html.Span("Actif récemment"),
                ]),
            ]),
        ])
        cards.append(card)
    
    testimonials_grid = html.Div(cards, className="premium-cards-grid")
    
    # Formulaire
    if session and session.get("email"):
        user_email = session.get("email")
        user = get_user_by_email(user_email)
        existing = get_user_testimonial(user_email)
        
        if existing:
            status = existing[1]
            if status == 'pending':
                form = html.Div([
                    html.Div(className="premium-status-icon", children=html.I(className="fas fa-clock")),
                    html.H3("Témoignage en attente", className="premium-status-title"),
                    html.P("Votre témoignage sera visible après validation.", className="premium-status-text"),
                ], className="premium-status-card pending")
            elif status == 'approved':
                form = html.Div([
                    html.Div(className="premium-status-icon", children=html.I(className="fas fa-check-circle")),
                    html.H3("Merci pour votre témoignage !", className="premium-status-title"),
                    html.P("Il est déjà visible sur cette page.", className="premium-status-text"),
                ], className="premium-status-card approved")
            else:
                form = create_testimonial_form(user)
        else:
            form = create_testimonial_form(user)
    else:
        form = html.Div([
            html.H3("Partagez votre expérience", className="premium-cta-title"),
            html.P("Connectez-vous pour laisser un témoignage", className="premium-cta-text"),
            dcc.Link(
                html.Button("Se connecter", className="premium-cta-button"),
                href="/login"
            )
        ], className="premium-cta-card")
    
    return stats_display, testimonials_grid, form

def create_testimonial_form(user):
    """Formulaire avec étoiles dynamiques"""
    name = user['email'].split('@')[0].capitalize() if user else "Utilisateur"
    
    return html.Div(className="premium-form-simple", children=[
        html.H3("Partagez votre expérience", className="simple-form-title"),
        html.P("Votre avis compte pour notre communauté", className="simple-form-subtitle"),
        
        html.Div(className="simple-form-group", children=[
            html.Label("Nom affiché"),
            dcc.Input(
                id="testimonial-name",
                type="text",
                value=name,
                className="simple-form-input"
            ),
        ]),
        
        # Système d'étoiles dynamique
        html.Div(className="simple-form-group", children=[
            html.Label("Votre note"),
            html.Div(className="stars-container", id="stars-container", children=[
                html.Span("☆", className="star active", id="star-1", n_clicks=0),
                html.Span("☆", className="star active", id="star-2", n_clicks=0),
                html.Span("☆", className="star active", id="star-3", n_clicks=0),
                html.Span("☆", className="star active", id="star-4", n_clicks=0),
                html.Span("☆", className="star active", id="star-5", n_clicks=0),
            ]),
            dcc.Store(id="selected-rating", data=5),
        ]),
        
        html.Div(className="simple-form-group", children=[
            html.Label("Votre message"),
            dcc.Textarea(
                id="testimonial-content",
                placeholder="Racontez votre expérience...",
                className="simple-form-textarea"
            ),
        ]),
        
        html.Div(className="simple-form-row", children=[
            html.Div(className="simple-form-group", children=[
                html.Label("Gain (€) - optionnel"),
                dcc.Input(
                    id="testimonial-gain",
                    type="number",
                    placeholder="ex: 5000",
                    className="simple-form-input"
                ),
            ]),
            html.Div(className="simple-form-group", children=[
                html.Label("Période - optionnel"),
                dcc.Input(
                    id="testimonial-period",
                    type="text",
                    placeholder="ex: 6 mois",
                    className="simple-form-input"
                ),
            ]),
        ]),
        
        html.Button(
            "Envoyer mon témoignage",
            id="testimonial-submit",
            className="simple-form-button"
        ),
        
        html.Div(id="testimonial-message", className="simple-form-message"),
    ])

# Callback pour les étoiles
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
    prevent_initial_call=True
)
def update_stars(star1, star2, star3, star4, star5):
    ctx = dash.callback_context
    if not ctx.triggered:
        # Par défaut, 5 étoiles
        return "star active", "star active", "star active", "star active", "star active", 5
    
    # Récupérer l'ID de l'étoile cliquée
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    rating = int(button_id.split("-")[1])
    
    # Générer les classes pour chaque étoile
    classes = []
    for i in range(1, 6):
        if i <= rating:
            classes.append("star active")
        else:
            classes.append("star")
    
    return classes[0], classes[1], classes[2], classes[3], classes[4], rating

# Callback pour l'envoi du témoignage
@callback(
    Output("testimonial-message", "children"),
    Input("testimonial-submit", "n_clicks"),
    State("session-store", "data"),
    State("testimonial-name", "value"),
    State("testimonial-content", "value"),
    State("selected-rating", "data"),
    State("testimonial-gain", "value"),
    State("testimonial-period", "value"),
    prevent_initial_call=True
)
def submit_testimonial(n_clicks, session, name, content, rating, gain, period):
    if not session:
        return html.Div([
            html.I(className="fas fa-exclamation-circle"),
            html.Span("Veuillez vous connecter")
        ], className="simple-message error")
    
    if not content or len(content) < 10:
        return html.Div([
            html.I(className="fas fa-exclamation-circle"),
            html.Span("Le message doit contenir au moins 10 caractères")
        ], className="simple-message error")
    
    user_email = session.get("email")
    success = add_testimonial(
        user_email=user_email,
        user_name=name,
        content=content,
        rating=rating,
        gain=gain,
        period=period
    )
    
    if success:
        return html.Div([
            html.I(className="fas fa-check-circle"),
            html.Span("Témoignage envoyé ! En attente de validation.")
        ], className="simple-message success")
    else:
        return html.Div([
            html.I(className="fas fa-times-circle"),
            html.Span("Une erreur est survenue")
        ], className="simple-message error")