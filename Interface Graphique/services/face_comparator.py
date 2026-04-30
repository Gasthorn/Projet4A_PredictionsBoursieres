import cv2
import numpy as np
import base64

def compare_faces(face1_base64, face2_base64, threshold=0.50):  # Seuil plus haut
    """
    Compare deux images de visages en base64
    Retourne (is_match, score)
    """
    try:
        # Décoder les images base64
        if ',' in face1_base64:
            face1_bytes = base64.b64decode(face1_base64.split(',')[1])
        else:
            face1_bytes = base64.b64decode(face1_base64)
            
        if ',' in face2_base64:
            face2_bytes = base64.b64decode(face2_base64.split(',')[1])
        else:
            face2_bytes = base64.b64decode(face2_base64)
        
        # Convertir en images OpenCV
        nparr1 = np.frombuffer(face1_bytes, np.uint8)
        nparr2 = np.frombuffer(face2_bytes, np.uint8)
        
        img1 = cv2.imdecode(nparr1, cv2.IMREAD_COLOR)
        img2 = cv2.imdecode(nparr2, cv2.IMREAD_COLOR)
        
        if img1 is None or img2 is None:
            print("❌ Impossible de décoder les images")
            return False, 0
        
        # Redimensionner
        img1 = cv2.resize(img1, (100, 100))
        img2 = cv2.resize(img2, (100, 100))
        
        # Convertir en gris
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
        
        # MÉTHODE 1: Corrélation croisée (POIDS FORT)
        try:
            result = cv2.matchTemplate(gray1, gray2, cv2.TM_CCOEFF_NORMED)
            corr_score = result[0][0]
        except:
            corr_score = 0.0
        
        # MÉTHODE 2: MSE (Mean Squared Error) - moins de poids
        mse = np.mean((gray1.astype(float) - gray2.astype(float)) ** 2)
        max_mse = 255**2
        mse_score = 1 - min(mse / max_mse, 1)
        
        # MÉTHODE 3: Différence structurelle (Sobel) - NOUVEAU
        sobel1 = cv2.Sobel(gray1, cv2.CV_64F, 1, 1, ksize=5)
        sobel2 = cv2.Sobel(gray2, cv2.CV_64F, 1, 1, ksize=5)
        sobel_diff = np.mean(np.abs(sobel1 - sobel2))
        sobel_score = 1 - min(sobel_diff / 1000, 1)
        
        # MÉTHODE 4: Histogrammes (poids FAIBLE car sensible aux couleurs)
        hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
        hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])
        hist_score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        hist_score = max(0, min(1, hist_score))
        
        # NOUVEAU: Détection de visage pour vérifier
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        faces1 = face_cascade.detectMultiScale(gray1, 1.1, 4)
        faces2 = face_cascade.detectMultiScale(gray2, 1.1, 4)
        
        is_face1 = len(faces1) > 0
        is_face2 = len(faces2) > 0
        
        # Score combiné avec NOUVEAUX POIDS
        # On donne plus de poids à la corrélation et à Sobel (forme)
        # Moins de poids aux histogrammes (couleur)
        final_score = (corr_score * 0.5 + mse_score * 0.1 + sobel_score * 0.3 + hist_score * 0.1)
        
        # Pénalité si ce n'est pas un visage
        if not is_face1 or not is_face2:
            final_score *= 0.5
            print("⚠️ Image non faciale détectée - score réduit")
        
        print(f"📊 Scores - Corr: {corr_score:.2%}, MSE: {mse_score:.2%}, Sobel: {sobel_score:.2%}, Hist: {hist_score:.2%}")
        print(f"📈 Score final: {final_score:.2%}")
        
        return final_score > threshold, final_score
        
    except Exception as e:
        print(f"❌ Erreur comparaison: {e}")
        import traceback
        traceback.print_exc()
        return False, 0