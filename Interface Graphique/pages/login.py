import dash
from dash import html, dcc, Input, Output, State, callback, clientside_callback, no_update
import urllib.parse

from services.auth_service import verify_user

dash.register_page(__name__, path="/login", name="Connexion")

layout = html.Div(className="auth-page login-page", children=[

    dcc.Store(id="remember-store", storage_type="local"),

    html.Div(className="auth-container", children=[
        html.Div(className="auth-card", children=[
            html.H1("CONNEXION", className="auth-title"),
            html.Div(className="auth-neon-line"),

            # ── Email : le CSS .auth-input-icon i gère left:22px automatiquement ──
            html.Div(className="auth-input-icon", children=[
                html.I(className="fas fa-envelope"),
                dcc.Input(
                    id="login-email",
                    type="email",
                    placeholder="Email",
                    className="auth-input"
                )
            ]),

            # ── Mot de passe + icône œil ──
            html.Div(className="auth-input-icon", style={"position": "relative"}, children=[
                html.I(className="fas fa-lock"),
                dcc.Input(
                    id="login-password",
                    type="password",
                    placeholder="Mot de passe",
                    className="auth-input",
                    style={"paddingRight": "50px"}
                ),
                # Bouton œil positionné à droite dans le champ
                html.Button(
                    html.I(
                        id="toggle-login-pw-icon",
                        className="fas fa-eye",
                        style={
                            "position": "static",
                            "transform": "none",
                            "pointerEvents": "none",
                            "fontSize": "1rem",
                            "color": "#00f7ff"
                        }
                    ),
                    id="toggle-login-pw",
                    n_clicks=0,
                    title="Afficher / masquer",
                    style={
                        "position": "absolute",
                        "right": "14px",
                        "top": "40%",
                        "transform": "translateY(-50%)",
                        "background": "none",
                        "border": "none",
                        "cursor": "pointer",
                        "color": "#00f7ff",
                        "padding": "4px",
                        "zIndex": "3"
                    }
                )
            ]),

            # ── Se souvenir de moi ──
            html.Div(style={"margin": "10px 0 15px", "paddingLeft": "4px"}, children=[
                dcc.Checklist(
                    id="remember-me",
                    options=[{"label": "  Se souvenir de moi", "value": "remember"}],
                    value=[],
                    labelStyle={
                        "color": "var(--muted)",
                        "fontSize": "0.9rem",
                        "cursor": "pointer",
                        "userSelect": "none"
                    },
                    inputStyle={
                        "accentColor": "#00f7ff",
                        "cursor": "pointer",
                        "width": "15px",
                        "height": "15px",
                        "marginRight": "6px"
                    }
                )
            ]),

            html.Button("SE CONNECTER", id="login-btn", className="auth-btn"),

            html.Div(style={
                "textAlign": "center", "margin": "20px 0",
                "display": "flex", "alignItems": "center",
                "justifyContent": "center", "gap": "10px"
            }, children=[
                html.Hr(style={"flex": "1", "border": "none", "height": "1px",
                               "background": "linear-gradient(90deg, transparent, var(--accent), transparent)"}),
                html.Span("OU", style={"color": "var(--accent)", "fontWeight": "bold"}),
                html.Hr(style={"flex": "1", "border": "none", "height": "1px",
                               "background": "linear-gradient(90deg, transparent, var(--accent), transparent)"})
            ]),

            dcc.Link(
                html.Button(
                    [html.I(className="fas fa-camera", style={"marginRight": "10px"}),
                     "CONNEXION FACIALE RAPIDE"],
                    className="auth-btn",
                    style={
                        "background": "linear-gradient(135deg, #8be9ff, #00f0ff)",
                        "marginBottom": "10px",
                        "width": "100%"
                    }
                ),
                href="/face-login",
                style={"textDecoration": "none", "width": "100%"}
            ),

            html.Div(style={
                "fontSize": "0.9rem", "color": "var(--muted)",
                "textAlign": "center", "marginTop": "10px", "padding": "10px",
                "borderRadius": "8px", "background": "rgba(0,240,255,0.05)",
                "border": "1px solid rgba(0,240,255,0.1)"
            }, children=[
                html.I(className="fas fa-info-circle",
                       style={"marginRight": "5px", "color": "var(--accent)"}),
                " Pas besoin d'email ni de mot de passe ! Regarde simplement la caméra."
            ]),

            html.Div(id="login-output", className="auth-message"),

            html.Div(className="auth-footer", children=[
                "Pas encore de compte ?",
                dcc.Link("S'inscrire", href="/signup")
            ]),

            html.A(
                [html.I(className="fas fa-flask", style={"marginRight": "8px"}),
                 "Voir nos performances sans s'inscrire"],
                href="/demo",
                style={
                    "display": "block",
                    "textAlign": "center",
                    "marginTop": "14px",
                    "fontSize": "0.82rem",
                    "color": "rgba(0,212,255,0.6)",
                    "textDecoration": "none",
                    "padding": "8px",
                    "borderRadius": "8px",
                    "border": "1px solid rgba(0,212,255,0.12)",
                    "background": "rgba(0,212,255,0.04)",
                    "transition": "all 0.15s",
                }
            ),

            dcc.Location(id="login-redirect")
        ])
    ])
])

# ── Toggle œil : Output sur prop 'type' → React applique proprement ──
clientside_callback(
    """
    function(n_clicks, currentType) {
        if (!n_clicks) return [window.dash_clientside.no_update, window.dash_clientside.no_update];
        if (currentType === 'password') {
            return ['text', 'fas fa-eye-slash'];
        }
        return ['password', 'fas fa-eye'];
    }
    """,
    Output("login-password", "type"),
    Output("toggle-login-pw-icon", "className"),
    Input("toggle-login-pw", "n_clicks"),
    State("login-password", "type"),
)

# ── Charger les identifiants mémorisés dès que la page login monte ──
@callback(
    Output("login-email", "value", allow_duplicate=True),
    Output("login-password", "value", allow_duplicate=True),
    Output("remember-me", "value"),
    Input("remember-store", "data"),
    prevent_initial_call="initial_duplicate"
)
def load_remembered(data):
    if data and data.get("remember"):
        return data.get("email", ""), data.get("password", ""), ["remember"]
    return no_update, no_update, []

# ── Connexion standard ──
@callback(
    Output("session-store", "data", allow_duplicate=True),
    Output("login-output", "children", allow_duplicate=True),
    Output("login-output", "className", allow_duplicate=True),
    Output("login-redirect", "pathname", allow_duplicate=True),
    Output("remember-store", "data"),
    Input("login-btn", "n_clicks"),
    State("login-email", "value"),
    State("login-password", "value"),
    State("remember-me", "value"),
    prevent_initial_call=True
)
def login(n_clicks, email, password, remember):
    if not n_clicks:
        return no_update, no_update, no_update, no_update, no_update

    if not email or not password:
        return no_update, "Email et mot de passe requis", "auth-message error", no_update, no_update

    user = verify_user(email, password)

    if user:
        session_data = {"email": user["email"], "is_admin": user.get("is_admin", 0)}
        remember_data = (
            {"email": email, "password": password, "remember": True}
            if (remember and "remember" in remember)
            else {}
        )
        return session_data, "Connexion réussie !", "auth-message success", "/", remember_data

    return no_update, "Email ou mot de passe incorrect", "auth-message error", no_update, no_update

# ── Pré-remplir l'email si redirigé depuis le signup ──
@callback(
    Output("login-email", "value", allow_duplicate=True),
    Input("url", "search"),
    prevent_initial_call=True
)
def prefill_email(search):
    if search and "email=" in search:
        params = urllib.parse.parse_qs(search[1:])
        if "email" in params:
            return params["email"][0]
    return no_update
