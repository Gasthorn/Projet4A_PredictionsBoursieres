"""
Module de reconnaissance faciale simplifiée pour ENSIM
Utilise OpenCV avec fallback console si GUI non disponible
"""

import os
import pickle
import hashlib
import time
from pathlib import Path

# Gestion d'import sécurisée pour OpenCV
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
    
    # Vérifier si la GUI est disponible (imshow fonctionne)
    try:
        # Test rapide pour voir si imshow est implémenté
        test_window = cv2.namedWindow("test", cv2.WINDOW_NORMAL)
        cv2.destroyWindow("test")
        GUI_AVAILABLE = True
        print("✅ OpenCV disponible (mode graphique)")
    except:
        GUI_AVAILABLE = False
        print("⚠️ Interface graphique OpenCV non disponible (mode console)")
        
except ImportError as e:
    print(f"⚠️ OpenCV non disponible: {e}")
    print("  Pour l'activer: pip install opencv-python")
    OPENCV_AVAILABLE = False
    GUI_AVAILABLE = False
    cv2 = None
    np = None

# Version simplifiée sans face_recognition
FACE_SIMPLIFIED = True

# Dossier pour stocker les données des visages
FACE_DATA_DIR = Path("face_data")
try:
    FACE_DATA_DIR.mkdir(exist_ok=True)
except:
    print(f"⚠️ Impossible de créer le dossier {FACE_DATA_DIR}")

def get_face_hash_from_image(frame):
    """
    Crée un hash simple d'un visage à partir d'une image
    Version simplifiée sans face_recognition
    """
    if not OPENCV_AVAILABLE:
        return None
    
    try:
        # Convertir en gris
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Redimensionner à une taille fixe
        resized = cv2.resize(gray, (100, 100))
        
        # Convertir en bytes et créer un hash
        img_bytes = resized.tobytes()
        face_hash = hashlib.sha256(img_bytes).hexdigest()
        
        return face_hash
    except Exception as e:
        print(f"❌ Erreur création hash: {e}")
        return None

def detect_face(frame):
    """
    Détecte un visage dans l'image en utilisant le classificateur Haar Cascade d'OpenCV
    """
    if not OPENCV_AVAILABLE:
        return None
    
    try:
        # Charger le classificateur Haar Cascade pour la détection de visages
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Convertir en gris
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Détecter les visages
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) == 0:
            return None
        
        # Prendre le premier visage
        (x, y, w, h) = faces[0]
        face_roi = frame[y:y+h, x:x+w]
        
        return face_roi
    except Exception as e:
        print(f"❌ Erreur détection visage: {e}")
        return None

    """
    Capture un visage depuis la webcam (version avec fallback console)
    """
    if not OPENCV_AVAILABLE:
        print("❌ OpenCV non disponible")
        return None
    
    try:
        # Initialiser la webcam
        video_capture = cv2.VideoCapture(0)
        if not video_capture.isOpened():
            print("❌ Impossible d'ouvrir la webcam")
            return None
        
        print("\n" + "="*50)
        print("🔵 CAPTURE FACIALE - ENSIM")
        print("="*50)
        
        if GUI_AVAILABLE:
            print("📸 Fenêtre de capture va s'ouvrir...")
            print("   [ESPACE] pour capturer")
            print("   [Q] pour annuler")
        else:
            print("📸 Mode console - regarde la caméra")
            print("   Capture automatique dans 3 secondes...")
            time.sleep(1)
            print("   3...")
            time.sleep(1)
            print("   2...")
            time.sleep(1)
            print("   1...")
            time.sleep(1)
        
        face_image = None
        face_hash = None
        captured = False
        
        # Variables pour le mode console
        console_attempts = 0
        max_console_attempts = 5
        
        while not captured:
            ret, frame = video_capture.read()
            if not ret:
                break
            
            # Détecter le visage
            face_roi = detect_face(frame)
            
            # Préparer l'image d'affichage
            display_frame = frame.copy()
            if face_roi is not None:
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                for (x, y, w, h) in faces:
                    cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    cv2.putText(display_frame, "VISAGE", (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            # Mode GUI
            if GUI_AVAILABLE:
                cv2.putText(display_frame, "ESPACE: capturer | Q: quitter", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                if face_roi is None:
                    cv2.putText(display_frame, "⚠️ AUCUN VISAGE DETECTE", 
                               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                cv2.imshow('Capture Visage - ENSIM', display_frame)
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord(' '):
                    if face_roi is not None:
                        face_hash = get_face_hash_from_image(face_roi)
                        face_image = face_roi
                        captured = True
                        print("\n✅ Visage capturé avec succès!")
                    else:
                        print("\n❌ Aucun visage détecté, réessaie")
                        
                elif key == ord('q'):
                    print("\n❌ Capture annulée")
                    break
            
            # Mode console (sans GUI)
            else:
                console_attempts += 1
                print(f"\r📸 Tentative {console_attempts}/{max_console_attempts}... ", end="", flush=True)
                
                if face_roi is not None:
                    face_hash = get_face_hash_from_image(face_roi)
                    face_image = face_roi
                    captured = True
                    print("\n✅ Visage capturé avec succès!")
                elif console_attempts >= max_console_attempts:
                    print("\n❌ Échec capture - aucun visage détecté")
                    break
                else:
                    time.sleep(0.5)  # Pause entre les tentatives
        
        # Nettoyer
        video_capture.release()
        if GUI_AVAILABLE:
            cv2.destroyAllWindows()
        
        if face_hash:
            print("✅ Données faciales enregistrées")
            return {"hash": face_hash, "image": face_image}
        
        print("❌ Aucune donnée faciale capturée")
        return None
        
    except Exception as e:
        print(f"\n❌ Erreur capture: {e}")
        return None
def capture_face_from_webcam():
    """
    Capture un visage depuis la webcam (version avec fallback console)
    """
    if not OPENCV_AVAILABLE:
        print("❌ OpenCV non disponible")
        return None
    
    try:
        # Essayer différents backends sur Windows
        video_capture = None
        
        # Liste des backends à essayer
        backends = []
        if hasattr(cv2, 'CAP_DSHOW'):
            backends.append(cv2.CAP_DSHOW)  # DirectShow (meilleur sur Windows)
        if hasattr(cv2, 'CAP_MSMF'):
            backends.append(cv2.CAP_MSMF)   # Media Foundation (défaut)
        backends.append(0)  # Backend par défaut
        
        for backend in backends:
            try:
                print(f"🔄 Tentative avec backend: {backend}")
                if backend != 0:
                    video_capture = cv2.VideoCapture(0, backend)
                else:
                    video_capture = cv2.VideoCapture(0)
                    
                if video_capture.isOpened():
                    print(f"✅ Webcam ouverte avec backend: {backend}")
                    break
                else:
                    video_capture.release()
            except:
                continue
        
        if not video_capture or not video_capture.isOpened():
            print("❌ Impossible d'ouvrir la webcam avec aucun backend")
            return None
        
        # Configurer la résolution pour de meilleures performances
        video_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        video_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        video_capture.set(cv2.CAP_PROP_FPS, 30)
        
        print("\n" + "="*50)
        print("🔵 CAPTURE FACIALE - ENSIM")
        print("="*50)
        
        if GUI_AVAILABLE:
            print("📸 Fenêtre de capture va s'ouvrir...")
            print("   [ESPACE] pour capturer")
            print("   [Q] pour annuler")
            print("   Appuie sur ESPACE quand ton visage est dans le cadre vert")
        
        face_image = None
        face_hash = None
        captured = False
        
        # Variables pour le mode console
        console_attempts = 0
        max_console_attempts = 5
        
        # Créer une fenêtre
        window_name = 'Capture Visage - ENSIM'
        if GUI_AVAILABLE:
            cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(window_name, 800, 600)
        
        while not captured:
            ret, frame = video_capture.read()
            if not ret:
                print("❌ Erreur lecture frame")
                break
            
            # Détecter le visage
            face_roi = detect_face(frame)
            
            # Préparer l'image d'affichage
            display_frame = frame.copy()
            
            # Dessiner les rectangles et instructions
            if face_roi is not None:
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                for (x, y, w, h) in faces:
                    # Rectangle vert pour le visage
                    cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 3)
                    cv2.putText(display_frame, "VISAGE DETECTE", (x, y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    # Ajouter un effet de glow
                    cv2.rectangle(display_frame, (x-2, y-2), (x+w+2, y+h+2), (0, 255, 0), 1)
            
            # Mode GUI
            if GUI_AVAILABLE:
                # Instructions en haut
                cv2.putText(display_frame, "ESPACE: capturer | Q: quitter", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                if face_roi is None:
                    cv2.putText(display_frame, "⚠️ AUCUN VISAGE DETECTE - Regarde la camera", 
                               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                else:
                    cv2.putText(display_frame, "✅ VISAGE DETECTE - Appuie sur ESPACE", 
                               (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Ajouter un guide au centre
                h, w = display_frame.shape[:2]
                center_x, center_y = w//2, h//2
                cv2.circle(display_frame, (center_x, center_y), 5, (0, 255, 255), -1)
                cv2.rectangle(display_frame, 
                             (center_x-150, center_y-150), 
                             (center_x+150, center_y+150), 
                             (255, 255, 0), 2)
                cv2.putText(display_frame, "Place ton visage ici", 
                           (center_x-120, center_y-160), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                
                cv2.imshow(window_name, display_frame)
                key = cv2.waitKey(1) & 0xFF
                
                if key == ord(' '):
                    if face_roi is not None:
                        face_hash = get_face_hash_from_image(face_roi)
                        face_image = face_roi
                        captured = True
                        print("\n✅ Visage capturé avec succès!")
                        
                        # Afficher un message de confirmation
                        cv2.putText(display_frame, "CAPTURE REUSSIE !", 
                                   (center_x-150, center_y), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                        cv2.imshow(window_name, display_frame)
                        cv2.waitKey(1000)  # Afficher 1 seconde
                        
                    else:
                        print("\n❌ Aucun visage détecté, réessaie")
                        
                elif key == ord('q'):
                    print("\n❌ Capture annulée")
                    break
            
            # Mode console (sans GUI)
            else:
                console_attempts += 1
                print(f"\r📸 Tentative {console_attempts}/{max_console_attempts}... ", end="", flush=True)
                
                if face_roi is not None:
                    face_hash = get_face_hash_from_image(face_roi)
                    face_image = face_roi
                    captured = True
                    print("\n✅ Visage capturé avec succès!")
                elif console_attempts >= max_console_attempts:
                    print("\n❌ Échec capture - aucun visage détecté")
                    break
                else:
                    time.sleep(0.5)  # Pause entre les tentatives
        
        # Nettoyer
        video_capture.release()
        if GUI_AVAILABLE:
            cv2.destroyAllWindows()
            cv2.waitKey(1)  # Petit délai pour que les fenêtres se ferment
        
        if face_hash:
            print("✅ Données faciales enregistrées")
            return {"hash": face_hash, "image": face_image}
        
        print("❌ Aucune donnée faciale capturée")
        return None
        
    except Exception as e:
        print(f"\n❌ Erreur capture: {e}")
        import traceback
        traceback.print_exc()
        return None
def save_face_encoding(email, face_data):
    """Sauvegarde les données du visage"""
    if not OPENCV_AVAILABLE or face_data is None:
        return False
    
    try:
        # Nettoyer l'email pour en faire un nom de fichier valide
        safe_email = email.replace('@', '_at_').replace('.', '_')
        filename = FACE_DATA_DIR / f"{safe_email}.pkl"
        
        with open(filename, 'wb') as f:
            pickle.dump(face_data, f)
        print(f"✅ Visage sauvegardé pour {email}")
        return True
    except Exception as e:
        print(f"❌ Erreur sauvegarde: {e}")
        return False

def load_face_encoding(email):
    """Charge les données du visage"""
    if not OPENCV_AVAILABLE:
        return None
    
    try:
        safe_email = email.replace('@', '_at_').replace('.', '_')
        filename = FACE_DATA_DIR / f"{safe_email}.pkl"
        
        if not filename.exists():
            return None
        
        with open(filename, 'rb') as f:
            return pickle.load(f)
    except Exception as e:
        print(f"❌ Erreur chargement: {e}")
        return None

def verify_face(email, tolerance=0.7):
    """Vérifie le visage (version avec fallback console)"""
    if not OPENCV_AVAILABLE:
        return False, "OpenCV non disponible"
    
    try:
        # Charger les données sauvegardées
        saved_data = load_face_encoding(email)
        if saved_data is None:
            return False, "Aucun visage enregistré pour cet email"
        
        saved_hash = saved_data.get("hash")
        
        # Initialiser la webcam
        video_capture = cv2.VideoCapture(0)
        if not video_capture.isOpened():
            return False, "Webcam non disponible"
        
        print("\n" + "="*50)
        print("🔵 VÉRIFICATION FACIALE - ENSIM")
        print("="*50)
        
        if GUI_AVAILABLE:
            print("📸 Regarde la caméra...")
        else:
            print("📸 Mode console - regarde la caméra")
            print("   Vérification automatique dans 3 secondes...")
            time.sleep(1)
            print("   3...")
            time.sleep(1)
            print("   2...")
            time.sleep(1)
            print("   1...")
            time.sleep(1)
        
        result = False
        message = "Vérification échouée"
        max_frames = 45  # ~1.5 secondes
        frame_count = 0
        matched = False
        
        while frame_count < max_frames and not matched:
            ret, frame = video_capture.read()
            if not ret:
                break
            
            # Détecter le visage
            face_roi = detect_face(frame)
            
            # Préparer l'image d'affichage
            display_frame = frame.copy()
            
            if face_roi is not None:
                # Dessiner un rectangle
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.1, 4)
                for (x, y, w, h) in faces:
                    cv2.rectangle(display_frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Calculer le hash du visage actuel
                current_hash = get_face_hash_from_image(face_roi)
                
                # Comparer les hash
                if current_hash and current_hash == saved_hash:
                    result = True
                    message = "✅ Visage reconnu !"
                    matched = True
                    
                    if GUI_AVAILABLE:
                        cv2.putText(display_frame, "RECONNU !", (50, 100), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                        cv2.putText(display_frame, message, (50, 150), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Mode GUI
            if GUI_AVAILABLE:
                # Afficher le compteur
                progress = f"Scan... {frame_count+1}/{max_frames}"
                cv2.putText(display_frame, progress, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                if face_roi is None:
                    cv2.putText(display_frame, "⚠️ AUCUN VISAGE", (10, 60), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                cv2.imshow('Verification Faciale - ENSIM', display_frame)
                cv2.waitKey(1)
            
            # Mode console
            else:
                if face_roi is not None:
                    print(f"\r📸 Visage détecté - analyse... {frame_count+1}/{max_frames}", end="", flush=True)
                else:
                    print(f"\r📸 Aucun visage détecté - {frame_count+1}/{max_frames}", end="", flush=True)
                time.sleep(0.1)
            
            frame_count += 1
        
        # Nettoyer
        print()  # Nouvelle ligne
        video_capture.release()
        if GUI_AVAILABLE:
            cv2.destroyAllWindows()
        
        if matched:
            print(" Vérification réussie !")
        else:
            print(" Échec de la vérification")
        
        return result, message
        
    except Exception as e:
        print(f"\n Erreur vérification: {e}")
        return False, f"Erreur: {str(e)}"

def delete_face_encoding(email):
    """Supprime le visage"""
    try:
        safe_email = email.replace('@', '_at_').replace('.', '_')
        filename = FACE_DATA_DIR / f"{safe_email}.pkl"
        if filename.exists():
            filename.unlink()
            print(f" Visage supprimé pour {email}")
            return True
        else:
            print(f" Aucun visage trouvé pour {email}")
    except Exception as e:
        print(f" Erreur suppression: {e}")
    return False

def user_has_face(email):
    """Vérifie si l'utilisateur a un visage"""
    return load_face_encoding(email) is not None

def list_all_users_with_faces():
    """Liste tous les utilisateurs ayant un visage enregistré"""
    try:
        files = list(FACE_DATA_DIR.glob("*.pkl"))
        users = []
        for f in files:
            # Convertir le nom de fichier en email approximatif
            name = f.stem.replace('_at_', '@').replace('_', '.')
            users.append(name)
        return users
    except:
        return []
