import dash
from dash import html, dcc, Input, Output, State, callback, no_update
import urllib.parse

# Importer les fonctions d'authentification
from services.auth_service import verify_user

dash.register_page(__name__, path="/login", name="Connexion")

layout = html.Div(className="auth-page login-page", children=[
    html.Div(className="auth-container", children=[
        html.Div(className="auth-card", children=[
            # Titre avec effet néon
            html.H1("CONNEXION", className="auth-title"),
            html.Div(className="auth-neon-line"),
            
            # Formulaire standard
           html.Div(className="auth-input-icon", style={"position":"relative"}, children=[
    html.I(className="fas fa-envelope", style={
        "position":"absolute",
        "left":"350px",
        "top":"38%",
        "transform":"translateY(-50%)",
        "color":"#00f7ff"
    }),
    dcc.Input(
        id="login-email",
        type="email",
        placeholder="Email",
        className="auth-input",
        style={"paddingLeft":"45px"}
    )
]),
            
          html.Div(className="auth-input-icon", style={"position":"relative"}, children=[
    html.I(className="fas fa-lock", style={
        "position":"absolute",
        "left":"350px",
        "top":"37%",
        "transform":"translateY(-50%)",
        "color":"#00f7ff"
    }),
    dcc.Input(
        id="login-password",
        type="password",
        placeholder="Mot de passe",
        className="auth-input",
        style={"paddingLeft":"45px"}
    )
]),
            
            html.Button("SE CONNECTER", id="login-btn", className="auth-btn"),
            
            # Séparateur
            html.Div(style={"text-align": "center", "margin": "20px 0", "color": "var(--muted)", 
                           "position": "relative", "display": "flex", "align-items": "center", 
                           "justify-content": "center", "gap": "10px"}, 
                    children=[
                        html.Hr(style={"flex": "1", "border": "none", "height": "1px", 
                                      "background": "linear-gradient(90deg, transparent, var(--accent), transparent)"}),
                        html.Span("OU", style={"color": "var(--accent)", "font-weight": "bold"}),
                        html.Hr(style={"flex": "1", "border": "none", "height": "1px", 
                                      "background": "linear-gradient(90deg, transparent, var(--accent), transparent)"})
                    ]),
            
            # Bouton de connexion faciale
            dcc.Link(
                html.Button(
                    [html.I(className="fas fa-camera", style={"margin-right": "10px"}), 
                     "CONNEXION FACIALE RAPIDE"],
                    className="auth-btn",
                    style={
                        "background": "linear-gradient(135deg, #8be9ff, #00f0ff)",
                        "margin-bottom": "10px",
                        "width": "100%"
                    }
                ),
                href="/face-login",
                style={"text-decoration": "none", "width": "100%"}
            ),
            
            # Message d'info
            html.Div(style={
                "font-size": "0.9rem", 
                "color": "var(--muted)", 
                "text-align": "center",
                "margin-top": "10px",
                "padding": "10px",
                "border-radius": "8px",
                "background": "rgba(0,240,255,0.05)",
                "border": "1px solid rgba(0,240,255,0.1)"
            }, children=[
                html.I(className="fas fa-info-circle", style={"margin-right": "5px", "color": "var(--accent)"}),
                " Pas besoin d'email ni de mot de passe ! Regarde simplement la caméra."
            ]),
            
            # Message de retour pour la connexion standard
            html.Div(id="login-output", className="auth-message"),
            
            # Lien vers inscription
            html.Div(className="auth-footer", children=[
                "Pas encore de compte ?",
                dcc.Link("S'inscrire", href="/signup")
            ]),
            
            dcc.Location(id="login-redirect")
        ])
    ])
])

# Callback UNIQUE pour la connexion standard
@callback(
    Output("session-store", "data", allow_duplicate=True),
    Output("login-output", "children", allow_duplicate=True),
    Output("login-output", "className", allow_duplicate=True),
    Output("login-redirect", "pathname", allow_duplicate=True),
    Input("login-btn", "n_clicks"),
    State("login-email", "value"),
    State("login-password", "value"),
    prevent_initial_call=True
)
def login(n_clicks, email, password):
    """Callback pour la connexion standard par email/mot de passe"""
    if not n_clicks:
        return no_update, no_update, no_update, no_update
    
    # Vérification des champs
    if not email or not password:
        return no_update, "❌ Email et mot de passe requis", "auth-message error", no_update
    
    # Vérification des identifiants - MAINTENANT RETOURNE UN DICT AVEC is_admin
    user = verify_user(email, password)
    
    if user:
        # user est maintenant un dict: {"email": email, "is_admin": is_admin}
        print(f"✅ Connexion réussie: {email} (admin: {user.get('is_admin', 0)})")
        
        # Créer la session avec les infos utilisateur
        session_data = {
            "email": user["email"],
            "is_admin": user.get("is_admin", 0)
        }
        
        return session_data, "✅ Connexion réussie !", "auth-message success", "/"
    
    # Échec de connexion
    return no_update, "❌ Email ou mot de passe incorrect", "auth-message error", no_update

# Callback pour pré-remplir l'email (output différent, donc pas de conflit)
@callback(
    Output("login-email", "value"),
    Input("url", "search"),
    prevent_initial_call=True
)
def prefill_email(search):
    """Pré-remplit l'email si on vient de l'inscription"""
    if search and "email=" in search:
        params = urllib.parse.parse_qs(search[1:])
        if "email" in params:
            return params["email"][0]
    return no_update