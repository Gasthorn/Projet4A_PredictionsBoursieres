import dash
from dash import html, dcc, Input, Output, State, callback, clientside_callback, no_update
from services.auth_service import create_user
import base64
import cv2
import numpy as np

dash.register_page(__name__, path="/signup")

layout = html.Div(className="auth-page", style={"paddingTop": "100px"}, children=[
    html.Div(className="auth-container", children=[
        html.Div(className="auth-card", children=[
            # Titre avec effet néon
            html.H1("INSCRIPTION", className="auth-title"),
            html.Div(className="auth-neon-line"),
            
            # Formulaire
              html.Div(className="auth-input-icon", style={"position":"relative"}, children=[
    html.I(className="fas fa-envelope", style={
        "position":"absolute",
        "left":"350px",
        "top":"38%",
        "transform":"translateY(-50%)",
        "color":"#00f7ff"
    }),
    dcc.Input(
        id="signup-email",
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
        id="signup-password",
        type="password",
        placeholder="Mot de passe",
        className="auth-input",
        style={"paddingLeft":"45px"}
    )
]),
            
            # Option reconnaissance faciale
            html.Div(className="auth-checkbox", style={"margin": "20px 0", "text-align": "center"}, children=[
                dcc.Checklist(
                    id="signup-use-face",
                    options=[{"label": " Activer la reconnaissance faciale (recommandé)", "value": "use_face"}],
                    value=[],
                    labelStyle={"color": "var(--accent)", "font-weight": "600"}
                )
            ]),
            
            # Zone caméra
            html.Div(id="camera-section", style={"display": "none"}, children=[
                html.Div(className="camera-container", children=[
                    html.Video(
                        id="signup-camera",
                        className="camera-video",
                        autoPlay=True
                   
                    ),
                    html.Div(id="signup-camera-status", className="camera-status no-face", 
                            children="⏳ Initialisation caméra..."),
                    html.Div(className="camera-overlay")
                ]),
                dcc.Interval(id="signup-capture-interval", interval=2000, n_intervals=0)
            ]),
            
            html.Button("CRÉER MON COMPTE", id="signup-btn", className="auth-btn"),
            
            # Message de retour
            html.Div(id="signup-output", className="auth-message"),
            
            # Lien vers connexion
            html.Div(className="auth-footer", children=[
                "Déjà un compte ?",
                dcc.Link("Se connecter", href="/login")
            ]),
            
            dcc.Location(id="signup-redirect"),
            dcc.Store(id="signup-face-image"),  # Store pour l'image du visage (base64)
            dcc.Store(id="signup-face-captured"),  # Indicateur si visage capturé
            html.Script(src="/assets/camera.js")
        ])
    ])
])

# Callback pour démarrer/arrêter la caméra
clientside_callback(
    """
    function(useFace) {
        if (useFace && useFace.indexOf('use_face') > -1) {
            setTimeout(function() {
                if (window.startCamera) {
                    window.startCamera('signup-camera');
                }
            }, 500);
            return {'display': 'block'};
        } else {
            if (window.stopCamera) {
                window.stopCamera();
            }
            return {'display': 'none'};
        }
    }
    """,
    Output("camera-section", "style"),
    Input("signup-use-face", "value")
)

# Callback pour capture automatique
clientside_callback(
    """
    function(n_intervals, useFace) {
        if (!useFace || useFace.indexOf('use_face') === -1) {
            return window.dash_clientside.no_update;
        }
        
        if (window.captureImage) {
            return window.captureImage('signup-camera', 'signup-face-image');
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("signup-face-image", "data"),
    Input("signup-capture-interval", "n_intervals"),
    State("signup-use-face", "value"),
    prevent_initial_call=True
)

# Callback pour traiter l'image capturée
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
            # Décoder l'image pour vérifier qu'elle est valide
            base64_data = face_data.split(',')[1]
            image_bytes = base64.b64decode(base64_data)
            
            # Convertir en image OpenCV pour détection
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            # Détecter le visage
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) > 0:
                # Visage détecté - on garde l'image complète en base64
                print(f"✅ Visage détecté, image: {len(face_data)} caractères")
                
                # On retourne l'image base64 complète pour stockage
                return face_data, "✅ Visage détecté !", "camera-status face-detected"
            else:
                return no_update, "❌ Aucun visage", "camera-status no-face"
                
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return no_update, f"❌ Erreur", "camera-status no-face"
    
    return no_update, no_update, no_update

# Callback principal d'inscription
@callback(
    Output("signup-output", "children"),
    Output("signup-output", "className"),
    Output("signup-redirect", "pathname"),
    Input("signup-btn", "n_clicks"),
    State("signup-email", "value"),
    State("signup-password", "value"),
    State("signup-use-face", "value"),
    State("signup-face-captured", "data"),  # Maintenant c'est l'image base64
    prevent_initial_call=True
)
def signup(n_clicks, email, password, use_face, face_image):
    if not n_clicks:
        return no_update, no_update, no_update
    
    # Vérifications
    if not email or not password:
        return "❌ Email et mot de passe requis", "auth-message error", no_update
    
    if len(password) < 6:
        return "❌ Mot de passe trop court (min 6 caractères)", "auth-message error", no_update
    
    # Si l'utilisateur a coché la case mais pas de visage capturé
    if use_face and "use_face" in use_face and not face_image:
        return "❌ Attends que ton visage soit détecté !", "auth-message error", no_update
    
    # Créer l'utilisateur avec l'image (pas le hash)
    print(f"📝 Création utilisateur: {email}, image: {len(face_image) if face_image else 'None'} caractères")
    success = create_user(email, password, face_image if (use_face and "use_face" in use_face) else None)
    
    if success:
        msg = "✅ Compte créé avec succès !"
        if face_image:
            msg += " (Reconnaissance faciale activée)"
        return msg, "auth-message success", "/login"
    else:
        return "❌ Cet email est déjà utilisé", "auth-message error", no_update