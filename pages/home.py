from dash import html
import dash

dash.register_page(__name__, path="/")

layout = html.Div([
    # ====================== HERO ======================
    html.Div(className="hero", children=[
        html.H1("Bienvenue dans la Galaxie des Marchés Futuristes"),
    ]),

    # ====================== À PROPOS DE NOUS ======================
    html.Div(className="about-section", children=[
        html.Div(className="about-container", children=[

            # Titre avec effet néon
            html.Div(className="about-header", children=[
                html.H2("À propos de nous", className="about-title"),
                html.Div(className="neon-underline")
            ]),

            # Texte principal
            html.P("""
                Notre plateforme boursière futuriste combine innovation, intelligence artificielle et visualisation avancée 
                pour offrir une expérience unique d’analyse financière. Inspirée par la précision et l’esthétique du monde spatial, 
                notre mission est de guider les investisseurs vers une compréhension plus claire et plus intuitive des marchés.
            """, className="about-text"),

            # Cartes de valeurs
            html.Div(className="values-grid", children=[
                html.Div(className="value-card", children=[
                    html.I(className="fas fa-rocket", style={"fontSize": "2.2rem", "marginBottom": "12px", "color": "var(--accent)"}),
                    html.H4("Innovation"),
                    html.P("Technologies de pointe pour demain.")
                ]),
                html.Div(className="value-card", children=[
                    html.I(className="fas fa-brain", style={"fontSize": "2.2rem", "marginBottom": "12px", "color": "var(--accent-2)"}),
                    html.H4("Intelligence Artificielle"),
                    html.P("Prédictions précises, analyses automatisées.")
                ]),
                html.Div(className="value-card", children=[
                    html.I(className="fas fa-shield-alt", style={"fontSize": "2.2rem", "marginBottom": "12px", "color": "#00f0ff"}),
                    html.H4("Sécurité"),
                    html.P("Données chiffrées, confiance absolue.")
                ]),
                html.Div(className="value-card", children=[
                    html.I(className="fas fa-eye", style={"fontSize": "2.2rem", "marginBottom": "12px", "color": "#8be9ff"}),
                    html.H4("Vision Futuriste"),
                    html.P("Une interface inspirée de l’espace.")
                ]),
            ])
        ])
    ]),

    # ====================== CONTACT SECTION ======================
    html.Div(id="contact-section", className="contact-section", children=[
        html.Div(className="contact-container", children=[

            # --- CARTE CONTACT ---
            html.Div(className="contact-card", children=[
                html.Div(className="contact-header", children=[
                    html.H2("Contact & Réseaux", className="contact-title"),
                    html.Div(className="neon-line")
                ]),

                html.Div(className="contact-body", children=[
                    html.Div(className="info-line", children=[
                        html.I(className="fas fa-envelope"),
                        html.Span("contact.ETU@univ-lemans.fr")
                    ]),
                    html.Div(className="info-line", children=[
                        html.I(className="fas fa-phone"),
                        html.Span("+33 7 56 32 98 10")
                    ]),
                    html.Div(className="info-line", children=[
                        html.I(className="fas fa-location-dot"),
                        html.Span("ENSIM, Le Mans, France")
                    ]),

                    html.Div(className="social-icons", children=[
                        html.A(html.I(className="fab fa-instagram"), href="https://instagram.com", target="_blank", title="Instagram"),
                        html.A(html.I(className="fab fa-facebook-f"), href="https://facebook.com", target="_blank", title="Facebook"),
                        html.A(html.I(className="fab fa-linkedin-in"), href="https://linkedin.com", target="_blank", title="LinkedIn"),
                        html.A(html.I(className="fab fa-x-twitter"), href="https://x.com", target="_blank", title="X (Twitter)"),
                    ])
                ])
            ]),

            # --- CARTE GOOGLE MAPS ---
            html.Div(className="map-container", children=[
                html.Iframe(
                    src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2671.877541649405!2d0.16224861564635194!3d48.00942597921493!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x47e2886a4fa0b1ad%3A0xf8aeb2cc9cd5f2e!2sENSIM%20Le%20Mans!5e0!3m2!1sfr!2sfr!4v1715610936412!5m2!1sfr!2sfr",
                    width="100%",
                    height="100%",
                    style={"border": "0", "borderRadius": "16px"}
                ),
                html.Div(className="map-overlay", children=[
                    html.Div(className="pulse-ring"),
                    html.I(className="fas fa-map-marker-alt map-pin")
                ])
            ])
        ])
    ])
])