import dash
from dash import html, dcc, Input, Output, State, callback, clientside_callback, no_update
from services.auth_service import create_user
import base64
import cv2
import numpy as np

dash.register_page(__name__, path="/signup")

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
        html.Div(className="auth-card signup-card", children=[

            # ── En-tête ──
            html.H1("Créer un compte", className="auth-title"),
            html.P("Rejoignez notre plateforme de prédictions boursières IA",
                   className="signup-subtitle"),
            html.Div(className="auth-neon-line"),

            # ── Section : Identité ──
            html.Div(className="signup-section-label", children=[
                html.I(className="fas fa-user-circle"),
                html.Span(" Identité"),
            ]),
            html.Div(className="signup-fields-row", children=[
                html.Div(className="auth-input-icon", children=[
                    html.I(className="fas fa-user"),
                    dcc.Input(id="signup-prenom", type="text", placeholder="Prénom",
                              className="auth-input"),
                ]),
                html.Div(className="auth-input-icon", children=[
                    html.I(className="fas fa-user-tie"),
                    dcc.Input(id="signup-nom", type="text", placeholder="Nom",
                              className="auth-input"),
                ]),
            ]),
            html.Div(className="auth-input-icon", children=[
                html.I(className="fas fa-envelope"),
                dcc.Input(id="signup-email", type="email", placeholder="Adresse email",
                          className="auth-input"),
            ]),
            html.Div(className="auth-input-icon auth-phone-field", children=[
                html.I(className="fas fa-phone"),
                html.Span(FR_PHONE_PREFIX.strip(), className="auth-phone-prefix"),
                dcc.Input(id="signup-telephone", type="tel",
                          placeholder="6 12 34 56 78",
                          autoComplete="tel",
                          className="auth-input auth-phone-input"),
            ]),

            # ── Section : Sécurité ──
            html.Div(className="signup-section-label", children=[
                html.I(className="fas fa-shield-halved"),
                html.Span(" Sécurité"),
            ]),
            html.Div(className="auth-input-icon", style={"position": "relative"}, children=[
                html.I(className="fas fa-lock"),
                dcc.Input(id="signup-password", type="password",
                          placeholder="Mot de passe (min. 6 caractères)",
                          className="auth-input", style={"paddingRight": "50px"}),
                html.Button(
                    html.I(id="toggle-signup-pw-icon", className="fas fa-eye"),
                    id="toggle-signup-pw", n_clicks=0,
                    title="Afficher / masquer", style=_eye_btn_style,
                ),
            ]),
            html.Div(id="pw-strength-bar", className="pw-strength-wrap", style={"display": "none"}, children=[
                html.Div(className="pw-strength-track", children=[
                    html.Div(id="pw-strength-fill", className="pw-strength-fill"),
                ]),
                html.Span(id="pw-strength-label", className="pw-strength-label"),
            ]),
            html.Div(className="pw-rules", children=[
                html.Div(id="rule-len",    className="pw-rule", children=[html.I(className="fas fa-circle-xmark"), " Min. 8 caractères"]),
                html.Div(id="rule-upper",  className="pw-rule", children=[html.I(className="fas fa-circle-xmark"), " Une majuscule"]),
                html.Div(id="rule-digit",  className="pw-rule", children=[html.I(className="fas fa-circle-xmark"), " Un chiffre"]),
                html.Div(id="rule-symbol", className="pw-rule", children=[html.I(className="fas fa-circle-xmark"), " Un caractère spécial (!@#...)"]),
            ]),
            html.Div(className="auth-input-icon", style={"position": "relative"}, children=[
                html.I(id="confirm-pw-icon", className="fas fa-lock-open",
                       style={"color": "rgba(120,150,180,0.5)"}),
                dcc.Input(id="signup-password-confirm", type="password",
                          placeholder="Confirmer le mot de passe",
                          className="auth-input", style={"paddingRight": "50px"}),
                html.Button(
                    html.I(id="toggle-signup-pw2-icon", className="fas fa-eye"),
                    id="toggle-signup-pw2", n_clicks=0,
                    title="Afficher / masquer", style=_eye_btn_style,
                ),
            ]),
            html.Div(id="pw-match-feedback", className="signup-pw-feedback"),

            # ── Carte Reconnaissance faciale ──
            html.Div(className="signup-face-card", children=[
                html.Div(className="signup-face-card-icon", children=[
                    html.I(className="fas fa-face-smile"),
                ]),
                html.Div(className="signup-face-card-content", children=[
                    html.Div(className="signup-face-card-header", children=[
                        html.Strong("Reconnaissance faciale"),
                        html.Span("Recommandé", className="signup-badge-rec"),
                    ]),
                    html.P("Connexion instantanée sans mot de passe",
                           className="signup-face-card-desc"),
                ]),
                html.Label(className="signup-face-toggle-wrap", children=[
                    dcc.Checklist(
                        id="signup-use-face",
                        options=[{"label": "", "value": "use_face"}],
                        value=[],
                        className="signup-face-check",
                    ),
                    html.Span(className="signup-toggle-slider"),
                ]),
            ]),

            # ── Zone caméra ──
            html.Div(id="camera-section", style={"display": "none"}, children=[
                html.Div(className="camera-container", children=[
                    html.Video(id="signup-camera", className="camera-video", autoPlay=True),
                    html.Div(id="signup-camera-status", className="camera-status no-face",
                             children="Initialisation caméra..."),
                    html.Div(className="camera-overlay"),
                ]),
                dcc.Interval(id="signup-capture-interval", interval=2000, n_intervals=0),
            ]),

            # ── Section CGU (collapsible) ──
            html.Div(className="signup-consent-box", children=[
                html.Button(
                    id="consent-toggle-btn", n_clicks=0,
                    className="signup-consent-toggle",
                    children=[
                        html.Div(style={"display": "flex", "gap": "8px", "alignItems": "center"}, children=[
                            html.I(className="fas fa-file-contract"),
                            html.Span("Lire les conditions d'utilisation"),
                        ]),
                        html.I(id="consent-chevron", className="fas fa-chevron-down"),
                    ],
                ),
                html.Div(id="consent-details", style={"display": "none"},
                         className="signup-consent-details", children=[
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
                        html.Span("Vos données biométriques (reconnaissance faciale) "
                                  "sont traitées localement et ne sont pas transmises à des tiers."),
                    ]),
                    html.Div(className="signup-consent-item", children=[
                        html.I(className="fas fa-chart-line consent-icon"),
                        html.Span("Vos statistiques de trading restent privées sauf activation "
                                  "explicite depuis votre profil."),
                    ]),
                    html.Div(className="signup-consent-item", children=[
                        html.I(className="fas fa-trash-alt consent-icon"),
                        html.Span("Vous pouvez demander la suppression de votre compte "
                                  "et de toutes vos données à tout moment."),
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
                        ".",
                    ]),
                ]),
            ]),

            html.Button("CRÉER MON COMPTE", id="signup-btn", className="auth-btn",
                        style={"opacity": "0.45", "cursor": "not-allowed", "pointerEvents": "none"},
                        disabled=True),

            html.Div(id="signup-output", className="auth-message"),

            html.Div(className="auth-footer", children=[
                "Déjà un compte ?",
                dcc.Link("Se connecter", href="/login"),
            ]),

            dcc.Location(id="signup-redirect"),
            dcc.Store(id="signup-face-image"),
            dcc.Store(id="signup-face-captured"),
            html.Script(src="/assets/camera.js"),
        ])
    ])
])


# ── Activer le bouton : CGU acceptées + mot de passe valide ──
@callback(
    Output("signup-btn", "disabled"),
    Output("signup-btn", "style"),
    Input("signup-terms", "value"),
    Input("signup-password", "value"),
)
def toggle_signup_btn(terms, pw):
    rules = _pw_rules(pw)
    pw_ok = rules["len"] and rules["upper"] and rules["digit"]
    accepted = bool(terms and "accepted" in terms)
    if accepted and pw_ok:
        return False, {}
    return True, {"opacity": "0.45", "cursor": "not-allowed", "pointerEvents": "none"}


# ── Toggle œil mot de passe ──
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

# ── Toggle œil confirmation ──
clientside_callback(
    """
    function(n_clicks, currentType) {
        if (!n_clicks) return [window.dash_clientside.no_update, window.dash_clientside.no_update];
        if (currentType === 'password') return ['text', 'fas fa-eye-slash'];
        return ['password', 'fas fa-eye'];
    }
    """,
    Output("signup-password-confirm", "type"),
    Output("toggle-signup-pw2-icon", "className"),
    Input("toggle-signup-pw2", "n_clicks"),
    State("signup-password-confirm", "type"),
)

# ── Indicateur de force du mot de passe ──
def _pw_rules(pw):
    pw = pw or ""
    return {
        "len":    len(pw) >= 8,
        "upper":  any(c.isupper() for c in pw),
        "digit":  any(c.isdigit() for c in pw),
        "symbol": any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in pw),
    }

def _rule_cls(ok): return "pw-rule pw-rule-ok" if ok else "pw-rule"
def _rule_icon(ok): return "fas fa-circle-check" if ok else "fas fa-circle-xmark"


@callback(
    Output("pw-strength-bar", "style"),
    Output("pw-strength-fill", "style"),
    Output("pw-strength-fill", "className"),
    Output("pw-strength-label", "children"),
    Output("pw-strength-label", "style"),
    Output("rule-len",    "className"), Output("rule-len",    "children"),
    Output("rule-upper",  "className"), Output("rule-upper",  "children"),
    Output("rule-digit",  "className"), Output("rule-digit",  "children"),
    Output("rule-symbol", "className"), Output("rule-symbol", "children"),
    Input("signup-password", "value"),
)
def pw_strength(pw):
    rules = _pw_rules(pw)
    ok_len, ok_up, ok_dig, ok_sym = rules["len"], rules["upper"], rules["digit"], rules["symbol"]

    def rule_out(ok, text):
        return _rule_cls(ok), [html.I(className=_rule_icon(ok)), f" {text}"]

    if not pw:
        empty = {"display": "none"}, {}, "pw-strength-fill", "", {}
        r_len   = rule_out(False, "Min. 8 caractères")
        r_upper = rule_out(False, "Une majuscule")
        r_digit = rule_out(False, "Un chiffre")
        r_sym   = rule_out(False, "Un caractère spécial (!@#...)")
        return (*empty, *r_len, *r_upper, *r_digit, *r_sym)

    score = sum([ok_len, len(pw) >= 12, ok_up, ok_dig, ok_sym])
    levels = {
        0: ("15%",  "pw-strength-fill pw-weak",   "Trop faible", "#ff4d6d"),
        1: ("30%",  "pw-strength-fill pw-weak",   "Trop court",  "#ff4d6d"),
        2: ("55%",  "pw-strength-fill pw-fair",   "Moyen",       "#ffb347"),
        3: ("75%",  "pw-strength-fill pw-good",   "Bon",         "#f0e040"),
        4: ("88%",  "pw-strength-fill pw-strong", "Fort",        "#00f0a0"),
        5: ("100%", "pw-strength-fill pw-strong", "Très fort",   "#00f0a0"),
    }
    width, cls, label, color = levels.get(min(score, 5), levels[0])
    bar = {"display": "block"}, {"width": width}, cls, label, {"color": color}
    return (
        *bar,
        *rule_out(ok_len,  "Min. 8 caractères"),
        *rule_out(ok_up,   "Une majuscule"),
        *rule_out(ok_dig,  "Un chiffre"),
        *rule_out(ok_sym,  "Un caractère spécial (!@#...)"),
    )


# ── Feedback correspondance mots de passe ──
@callback(
    Output("pw-match-feedback", "children"),
    Output("pw-match-feedback", "className"),
    Output("confirm-pw-icon", "className"),
    Output("confirm-pw-icon", "style"),
    Input("signup-password", "value"),
    Input("signup-password-confirm", "value"),
)
def check_pw_match(pw, pw2):
    if not pw2:
        return "", "signup-pw-feedback", "fas fa-lock-open", {"color": "rgba(120,150,180,0.5)"}
    if pw == pw2:
        return [html.I(className="fas fa-check"), " Les mots de passe correspondent"], \
               "signup-pw-feedback pw-match", \
               "fas fa-lock", {"color": "#00f0a0"}
    return [html.I(className="fas fa-xmark"), " Les mots de passe ne correspondent pas"], \
           "signup-pw-feedback pw-mismatch", \
           "fas fa-lock-open", {"color": "#ff4d6d"}


# ── Toggle CGU collapsible ──
clientside_callback(
    """
    function(n_clicks) {
        if (!n_clicks) return [{'display': 'none'}, 'fas fa-chevron-down'];
        if (n_clicks % 2 === 1) return [{'display': 'block'}, 'fas fa-chevron-up'];
        return [{'display': 'none'}, 'fas fa-chevron-down'];
    }
    """,
    Output("consent-details", "style"),
    Output("consent-chevron", "className"),
    Input("consent-toggle-btn", "n_clicks"),
)

# ── Caméra on/off + toggle slider visuel ──
clientside_callback(
    """
    function(useFace) {
        var active = useFace && useFace.indexOf('use_face') > -1;
        // Mise à jour visuelle du slider toggle
        var slider = document.querySelector('.signup-toggle-slider');
        if (slider) {
            if (active) {
                slider.style.background = 'rgba(0,240,255,0.3)';
                slider.style.borderColor = 'rgba(0,240,255,0.6)';
                slider.style.setProperty('--tw', '20px');
            } else {
                slider.style.background = 'rgba(255,255,255,0.1)';
                slider.style.borderColor = 'rgba(255,255,255,0.15)';
            }
        }
        // Pseudo-élément non gérable en JS → on ajoute/retire une classe
        var wrap = document.querySelector('.signup-face-toggle-wrap');
        if (wrap) wrap.classList.toggle('face-active', !!active);
        if (active) {
            setTimeout(function() { if (window.startCamera) window.startCamera('signup-camera'); }, 500);
            return {'display': 'block'};
        } else {
            if (window.stopCamera) window.stopCamera();
            return {'display': 'none'};
        }
    }
    """,
    Output("camera-section", "style"),
    Input("signup-use-face", "value"),
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
    prevent_initial_call=True,
)


# ── Traitement image visage ──
@callback(
    Output("signup-face-captured", "data"),
    Output("signup-camera-status", "children"),
    Output("signup-camera-status", "className"),
    Input("signup-face-image", "data"),
    prevent_initial_call=True,
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
                return face_data, "Visage détecté !", "camera-status face-detected"
            return no_update, "Aucun visage détecté", "camera-status no-face"
    except Exception as e:
        print(f"Erreur: {e}")
        return no_update, "Erreur", "camera-status no-face"
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
    State("signup-password-confirm", "value"),
    State("signup-use-face", "value"),
    State("signup-face-captured", "data"),
    State("signup-terms", "value"),
    prevent_initial_call=True,
)
def signup(n_clicks, prenom, nom, email, telephone, password, password_confirm, use_face, face_image, terms):
    if not n_clicks:
        return no_update, no_update, no_update

    if not terms or "accepted" not in terms:
        return "Vous devez accepter les conditions d'utilisation", "auth-message error", no_update

    if not prenom or not nom:
        return "Prénom et nom requis", "auth-message error", no_update

    if not email or not password:
        return "Email et mot de passe requis", "auth-message error", no_update

    rules = _pw_rules(password)
    if not rules["len"]:
        return "Mot de passe trop court (min. 8 caractères)", "auth-message error", no_update
    if not rules["upper"]:
        return "Ajoutez au moins une majuscule", "auth-message error", no_update
    if not rules["digit"]:
        return "Ajoutez au moins un chiffre", "auth-message error", no_update

    if password != password_confirm:
        return "Les mots de passe ne correspondent pas", "auth-message error", no_update

    if use_face and "use_face" in use_face and not face_image:
        return "Attends que ton visage soit détecté avant de continuer !", "auth-message error", no_update

    face = face_image if (use_face and "use_face" in use_face) else None
    telephone = _format_fr_phone(telephone)

    success = create_user(
        email=email, password=password, face_image=face,
        prenom=prenom.strip(), nom=nom.strip(),
        telephone=telephone,
    )

    if success:
        msg = "Compte créé avec succès !"
        if face:
            msg += " (Reconnaissance faciale activée)"
        return msg, "auth-message success", "/login"

    return "Cet email est déjà utilisé", "auth-message error", no_update
