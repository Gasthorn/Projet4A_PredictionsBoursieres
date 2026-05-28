import dash
from dash import html, dcc, Input, Output, State, callback, clientside_callback, no_update
import base64
import cv2
import numpy as np
from services.database import get_connection
from services.face_comparator import compare_faces
import os

dash.register_page(__name__, path="/face-login", name="Connexion Faciale")

# === LAYOUT ===
layout = html.Div(className="auth-page login-page", children=[
    html.Div(className="auth-container", children=[
        html.Div(className="auth-card", children=[
            # Titre avec effet néon
            html.H1("CONNEXION FACIALE", className="auth-title"),
            html.Div(className="auth-neon-line"),
            
            # Message explicatif
            html.Div(style={"text-align": "center", "margin-bottom": "20px", "color": "var(--accent-2)"}, 
                    children="Regarde la caméra pour te connecter automatiquement"),
            
            # Zone caméra
            html.Div(className="camera-container", children=[
                html.Video(
                    id="face-login-camera",
                    className="camera-video",
                    autoPlay=True
                    
                ),
                html.Div(id="face-login-status", className="camera-status no-face", 
                        children="Initialisation..."),
                html.Div(className="camera-overlay")  # Guide ovale
            ]),
            
            # Bouton d'annulation
            html.Button(
                "RETOUR",
                id="face-login-back-btn",
                className="auth-btn",
                style={"margin-top": "20px", "background": "linear-gradient(135deg, #8be9ff, #00f0ff)"}
            ),
            
            # Message de statut
            html.Div(id="face-login-message", className="auth-message"),
            
            # Stores et intervalles
            dcc.Store(id="face-login-result"),
            dcc.Interval(id="face-login-interval", interval=2000, n_intervals=0),
            dcc.Interval(id="camera-start-interval", interval=500, n_intervals=0),
            dcc.Location(id="face-login-redirect"),
            
            # Script caméra
            html.Script(src="/assets/camera.js")
        ])
    ])
])

# === FONCTIONS UTILITAIRES ===
def get_all_users_with_faces():
    """Récupère tous les utilisateurs qui ont une image faciale"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email, face_image FROM users WHERE face_image IS NOT NULL AND face_image != ''")
    results = cursor.fetchall()
    conn.close()
    print(f"{len(results)} utilisateurs avec image faciale trouvés")
    for email, img in results:
        print(f"  - {email}: {len(img) if img else 0} caractères")
    return results

# === CALLBACKS ===
# Callback pour démarrer la caméra automatiquement
clientside_callback(
    """
    function(n_intervals) {
        if (window.videoStream) {
            return "Caméra déjà active";
        }

        var videoElement = document.getElementById('face-login-camera');
        if (videoElement && window.startCamera) {
            window.startCamera('face-login-camera');
            return "Caméra activée - Recherche de visage...";
        }
        return "Initialisation...";
    }
    """,
    Output("face-login-status", "children"),
    Input("camera-start-interval", "n_intervals"),
    prevent_initial_call=True
)

# Clientside callback pour la capture automatique
clientside_callback(
    """
    function(n_intervals) {
        if (window.captureImage) {
            return window.captureImage('face-login-camera', 'face-login-result');
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("face-login-result", "data"),
    Input("face-login-interval", "n_intervals"),
    prevent_initial_call=True
)

# Callback principal pour la connexion faciale
@callback(
    Output("session-store", "data", allow_duplicate=True),
    Output("face-login-message", "children"),
    Output("face-login-message", "className"),
    Output("face-login-status", "children", allow_duplicate=True),
    Output("face-login-status", "className"),
    Output("face-login-redirect", "pathname"),
    Input("face-login-result", "data"),
    prevent_initial_call=True
)
def process_face_login(face_data):
    if not face_data or not isinstance(face_data, str):
        return no_update, no_update, no_update, no_update, no_update, no_update
    
    try:
        print(f"Image capturée reçue ({len(face_data)} caractères)")
        
        # Récupérer tous les utilisateurs avec images
        users = get_all_users_with_faces()
        
        if len(users) == 0:
            return (no_update, no_update, no_update,
                   "Aucun visage enregistré", "camera-status no-face",
                   no_update)
        
        # Chercher le meilleur match
        best_match = None
        best_score = 0
        best_email = None
        SIMILARITY_THRESHOLD = 0.40  # 40% de similarité minimum
        
        for email, stored_image in users:
            if stored_image:
                # Comparer les images
                match, score = compare_faces(face_data, stored_image, threshold=SIMILARITY_THRESHOLD)
                
                print(f"Similarité avec {email}: {score:.2%}")
                
                if score > best_score:
                    best_score = score
                    best_email = email
                    
                    if match:
                        best_match = email
                        print(f"  MATCH TROUVÉ!")
        
        if best_match or best_score > SIMILARITY_THRESHOLD:
            email_to_use = best_match if best_match else best_email
            print(f"Connexion réussie pour {email_to_use} (score: {best_score:.2%})")
            
            return ({"email": email_to_use}, 
                   f"Bienvenue {email_to_use.split('@')[0]} !", "auth-message success",
                   f"Visage reconnu ({best_score:.0%})", "camera-status face-detected",
                   "/")
        else:
            print(f"Aucun match trouvé (meilleur score: {best_score:.2%})")
            return (no_update, no_update, no_update,
                   f"Visage non reconnu ({best_score:.0%})", "camera-status no-face",
                   no_update)
            
    except Exception as e:
        print(f"Erreur analyse faciale: {e}")
        import traceback
        traceback.print_exc()
        return (no_update, f"Erreur: {str(e)}", "auth-message error",
               "Erreur de scan", "camera-status no-face",
               no_update)

# Callback pour le bouton retour
@callback(
    Output("face-login-redirect", "pathname", allow_duplicate=True),
    Input("face-login-back-btn", "n_clicks"),
    prevent_initial_call=True
)
def go_back(n_clicks):
    if n_clicks:
        return "/login"
    return no_update