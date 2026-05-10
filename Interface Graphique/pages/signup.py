import dash
from dash import html, dcc, Input, Output, State, callback, clientside_callback, no_update
from services.auth_service import create_user
import base64
import cv2
import numpy as np

dash.register_page(__name__, path="/signup")

# Style commun pour les champs
_icon_style = {"position": "static", "transform": "none", "pointerEvents": "none",
               "fontSize": "1rem", "color": "#00f7ff"}
_eye_btn_style = {
    "position": "absolute", "right": "14px", "top": "40%",
    "transform": "translateY(-50%)", "background": "none", "border": "none",
    "cursor": "pointer", "color": "#00f7ff", "padding": "4px", "zIndex": "3"
}
FR_PHONE_PREFIX = "+33 "


def _format_fr_phone(value):
    phone = (value or "").strip()
    if not phone:
        return None
    if phone.startswith("+33"):
        phone = phone[3:].strip()
    return f"{FR_PHONE_PREFIX}{phone}".strip() if phone else None

layout = html.Div(className="auth-page", style={"paddingTop": "100px"}, children=[
    html.Div(className="auth-container", children=[
        html.Div(className="auth-card", children=[
            html.H1("INSCRIPTION", className="auth-title"),
            html.Div(className="auth-neon-line"),

            # ── Prénom ──
            html.Div(className="auth-input-icon", children=[
                html.I(className="fas fa-user"),
                dcc.Input(id="signup-prenom", type="text", placeholder="Prénom",
                          className="auth-input")
            ]),

            # ── Nom ──
            html.Div(className="auth-input-icon", children=[
                html.I(className="fas fa-user-tie"),
                dcc.Input(id="signup-nom", type="text", placeholder="Nom",
                          className="auth-input")
            ]),

            # ── Email ──
            html.Div(className="auth-input-icon", children=[
                html.I(className="fas fa-envelope"),
                dcc.Input(id="signup-email", type="email", placeholder="Email",
                          className="auth-input")
            ]),

            # ── Téléphone (optionnel) ──
            html.Div(className="auth-input-icon auth-phone-field", children=[
                html.I(className="fas fa-phone"),
                html.Span(FR_PHONE_PREFIX.strip(), className="auth-phone-prefix"),
                dcc.Input(id="signup-telephone", type="tel",
                          placeholder="6 12 34 56 78",
                          autoComplete="tel",
                          className="auth-input auth-phone-input")
            ]),

            # ── Mot de passe + œil ──
            html.Div(className="auth-input-icon", style={"position": "relative"}, children=[
                html.I(className="fas fa-lock"),
                dcc.Input(id="signup-password", type="password",
                          placeholder="Mot de passe (min. 6 caractères)",
                          className="auth-input", style={"paddingRight": "50px"}),
                html.Button(
                    html.I(id="toggle-signup-pw-icon", className="fas fa-eye",
                           style=_icon_style),
                    id="toggle-signup-pw", n_clicks=0,
                    title="Afficher / masquer", style=_eye_btn_style
                )
            ]),

            # ── Reconnaissance faciale ──
            html.Div(className="auth-checkbox",
                     style={"margin": "20px 0", "textAlign": "center"}, children=[
                dcc.Checklist(
                    id="signup-use-face",
                    options=[{"label": " Activer la reconnaissance faciale (recommandé)",
                              "value": "use_face"}],
                    value=[],
                    labelStyle={"color": "var(--accent)", "fontWeight": "600"}
                )
            ]),

            # ── Zone caméra ──
            html.Div(id="camera-section", style={"display": "none"}, children=[
                html.Div(className="camera-container", children=[
                    html.Video(id="signup-camera", className="camera-video", autoPlay=True),
                    html.Div(id="signup-camera-status", className="camera-status no-face",
                             children="⏳ Initialisation caméra..."),
                    html.Div(className="camera-overlay")
                ]),
                dcc.Interval(id="signup-capture-interval", interval=2000, n_intervals=0)
            ]),

            # ── Consentement légal ──
            html.Div(className="signup-consent-box", children=[
                html.Div(className="signup-consent-header", children=[
                    html.I(className="fas fa-shield-halved", style={"color": "#00f0ff", "fontSize": "1.1rem"}),
                    html.Span("Données personnelles & Conditions d'utilisation",
                              style={"fontWeight": "700", "color": "#e2e8f0", "fontSize": "0.9rem"}),
                ]),
                html.Div(className="signup-consent-details", children=[
                    html.Div(className="signup-consent-item", children=[
                        html.I(className="fas fa-lock consent-icon"),
                        html.Span("Vos données sont chiffrées et stockées de manière sécurisée."),
                    ]),
                    html.Div(className="signup-consent-item", children=[
                        html.I(className="fas fa-eye-slash consent-icon"),
                        html.Span("Votre email est strictement confidentiel et n'est jamais partagé."),
                    ]),
                    html.Div(className="signup-consent-item", children=[
                        html.I(className="fas fa-face-smile consent-icon"),
                        html.Span("En cas d'activation, vos données biométriques (reconnaissance faciale) "
                                  "sont traitées localement et ne sont pas transmises à des tiers."),
                    ]),
                    html.Div(className="signup-consent-item", children=[
                        html.I(className="fas fa-chart-line consent-icon"),
                        html.Span("Vos statistiques de trading restent privées sauf activation explicite "
                                  "de la visibilité publique depuis votre profil."),
                    ]),
                    html.Div(className="signup-consent-item", children=[
                        html.I(className="fas fa-trash-alt consent-icon"),
                        html.Span("Vous pouvez demander la suppression de votre compte et de toutes vos données à tout moment."),
                    ]),
                ]),
                html.Label(className="signup-consent-check-label", children=[
                    dcc.Checklist(
                        id="signup-terms",
                        options=[{"label": "", "value": "accepted"}],
                        value=[],
                        className="signup-terms-check",
                    ),
                    html.Span([
                        "J'ai lu et j'accepte les ",
                        html.Strong("Conditions Générales d'Utilisation"),
                        " et la ",
                        html.Strong("Politique de Confidentialité"),
                        ". Je consens au traitement de mes données personnelles dans le cadre de cette plateforme.",
                    ]),
                ]),
            ]),

            html.Button("CRÉER MON COMPTE", id="signup-btn", className="auth-btn",
                        style={"opacity": "0.45", "cursor": "not-allowed", "pointerEvents": "none"},
                        disabled=True),

            html.Div(id="signup-output", className="auth-message"),

            html.Div(className="auth-footer", children=[
                "Déjà un compte ?",
                dcc.Link("Se connecter", href="/login")
            ]),

            dcc.Location(id="signup-redirect"),
            dcc.Store(id="signup-face-image"),
            dcc.Store(id="signup-face-captured"),
            html.Script(src="/assets/camera.js")
        ])
    ])
])

# ── Activer le bouton quand les CGU sont acceptées ──
@callback(
    Output("signup-btn", "disabled"),
    Output("signup-btn", "style"),
    Input("signup-terms", "value"),
)
def toggle_signup_btn(terms):
    accepted = terms and "accepted" in terms
    if accepted:
        return False, {}
    return True, {"opacity": "0.45", "cursor": "not-allowed", "pointerEvents": "none"}


# ── Toggle œil ──
clientside_callback(
    """
    function(n_clicks, currentType) {
        if (!n_clicks) return [window.dash_clientside.no_update, window.dash_clientside.no_update];
        if (currentType === 'password') return ['text', 'fas fa-eye-slash'];
        return ['password', 'fas fa-eye'];
    }
    """,
    Output("signup-password", "type"),
    Output("toggle-signup-pw-icon", "className"),
    Input("toggle-signup-pw", "n_clicks"),
    State("signup-password", "type"),
)

# ── Caméra on/off ──
clientside_callback(
    """
    function(useFace) {
        if (useFace && useFace.indexOf('use_face') > -1) {
            setTimeout(function() { if (window.startCamera) window.startCamera('signup-camera'); }, 500);
            return {'display': 'block'};
        } else {
            if (window.stopCamera) window.stopCamera();
            return {'display': 'none'};
        }
    }
    """,
    Output("camera-section", "style"),
    Input("signup-use-face", "value")
)

# ── Capture automatique ──
clientside_callback(
    """
    function(n_intervals, useFace) {
        if (!useFace || useFace.indexOf('use_face') === -1) return window.dash_clientside.no_update;
        if (window.captureImage) return window.captureImage('signup-camera', 'signup-face-image');
        return window.dash_clientside.no_update;
    }
    """,
    Output("signup-face-image", "data"),
    Input("signup-capture-interval", "n_intervals"),
    State("signup-use-face", "value"),
    prevent_initial_call=True
)

# ── Traitement image visage ──
@callback(
    Output("signup-face-captured", "data"),
    Output("signup-camera-status", "children"),
    Output("signup-camera-status", "className"),
    Input("signup-face-image", "data"),
    prevent_initial_call=True
)
def process_face_image(face_data):
    if not face_data or not isinstance(face_data, str):
        return no_update, no_update, no_update
    try:
        if face_data.startswith('data:image'):
            base64_data = face_data.split(',')[1]
            image_bytes = base64.b64decode(base64_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            if len(faces) > 0:
                return face_data, "✅ Visage détecté !", "camera-status face-detected"
            return no_update, "❌ Aucun visage", "camera-status no-face"
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return no_update, "❌ Erreur", "camera-status no-face"
    return no_update, no_update, no_update

# ── Inscription ──
@callback(
    Output("signup-output", "children"),
    Output("signup-output", "className"),
    Output("signup-redirect", "pathname"),
    Input("signup-btn", "n_clicks"),
    State("signup-prenom", "value"),
    State("signup-nom", "value"),
    State("signup-email", "value"),
    State("signup-telephone", "value"),
    State("signup-password", "value"),
    State("signup-use-face", "value"),
    State("signup-face-captured", "data"),
    State("signup-terms", "value"),
    prevent_initial_call=True
)
def signup(n_clicks, prenom, nom, email, telephone, password, use_face, face_image, terms):
    if not n_clicks:
        return no_update, no_update, no_update

    if not terms or "accepted" not in terms:
        return "❌ Vous devez accepter les conditions d'utilisation", "auth-message error", no_update

    if not prenom or not nom:
        return "❌ Prénom et nom requis", "auth-message error", no_update

    if not email or not password:
        return "❌ Email et mot de passe requis", "auth-message error", no_update

    if len(password) < 6:
        return "❌ Mot de passe trop court (min 6 caractères)", "auth-message error", no_update

    if use_face and "use_face" in use_face and not face_image:
        return "❌ Attends que ton visage soit détecté !", "auth-message error", no_update

    face = face_image if (use_face and "use_face" in use_face) else None
    telephone = _format_fr_phone(telephone)

    success = create_user(
        email=email, password=password, face_image=face,
        prenom=prenom.strip(), nom=nom.strip(),
        telephone=telephone
    )

    if success:
        msg = "✅ Compte créé avec succès !"
        if face:
            msg += " (Reconnaissance faciale activée)"
        return msg, "auth-message success", "/login"

    return "❌ Cet email est déjà utilisé", "auth-message error", no_update
