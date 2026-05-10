import sqlite3
import bcrypt
from services.database import get_connection

def create_user(email, password, face_image=None, prenom=None, nom=None, telephone=None, is_admin=0):
    """Crée un utilisateur normal (admin=0 par défaut)"""
    conn = get_connection()
    cursor = conn.cursor()

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    try:
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            print(f" Email déjà existant: {email}")
            conn.close()
            return False

        cursor.execute(
            "INSERT INTO users (email, password, face_image, prenom, nom, telephone, is_admin) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (email, hashed, face_image, prenom, nom, telephone, is_admin)
        )
        conn.commit()

        print(f" Utilisateur créé: {email} (admin: {is_admin})")
        conn.close()
        return True

    except Exception as e:
        print(f" Erreur création: {e}")
        conn.close()
        return False

def verify_user(email, password):
    """Vérifie les identifiants et retourne les infos utilisateur"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT password, is_admin FROM users WHERE email=?", (email,))
    result = cursor.fetchone()
    conn.close()

    if result and bcrypt.checkpw(password.encode(), result[0]):
        return {"email": email, "is_admin": result[1]}
    
    return None

def get_user_by_email(email):
    """Récupère les infos d'un utilisateur"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, email, is_admin, face_image, prenom, nom, telephone, created_at, public_stats, COALESCE(is_online, 0) FROM users WHERE email=?",
        (email,)
    )
    result = cursor.fetchone()
    conn.close()

    if result:
        return {
            "id": result[0],
            "email": result[1],
            "is_admin": result[2],
            "face_image": result[3],
            "prenom": result[4] or "",
            "nom": result[5] or "",
            "telephone": result[6] or "",
            "created_at": result[7] or "",
            "public_stats": bool(result[8]),
            "is_online": bool(result[9]),
        }
    return None


def set_online_status(email, value: bool):
    """Active ou désactive le statut en ligne de l'utilisateur"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET is_online = ? WHERE email = ?", (1 if value else 0, email))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erreur set_online_status: {e}")
        return False
    finally:
        conn.close()


def set_public_stats(email, value: bool):
    """Active ou désactive la visibilité publique des stats de l'utilisateur"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET public_stats = ? WHERE email = ?", (1 if value else 0, email))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erreur set_public_stats: {e}")
        return False
    finally:
        conn.close()

def update_user_profile(email, prenom, nom, telephone):
    """Met à jour les informations de profil d'un utilisateur"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET prenom=?, nom=?, telephone=? WHERE email=?",
            (prenom, nom, telephone, email)
        )
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f" Erreur mise à jour profil: {e}")
        return False
    finally:
        conn.close()

def is_admin(email):
    """Vérifie si un utilisateur est admin"""
    user = get_user_by_email(email)
    return user and user["is_admin"] == 1

def promote_to_admin(email):
    """Promouvoir un utilisateur en admin"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_admin = 1 WHERE email = ?", (email,))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    if success:
        print(f" {email} est maintenant admin")
    return success

def demote_from_admin(email):
    """Rétrograder un admin en utilisateur normal"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Vérifier que ce n'est pas le dernier admin
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
    admin_count = cursor.fetchone()[0]
    
    if admin_count <= 1:
        print(" Impossible de rétrograder le dernier admin")
        conn.close()
        return False
    
    cursor.execute("UPDATE users SET is_admin = 0 WHERE email = ?", (email,))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def get_all_users():
    """Récupère tous les utilisateurs (pour admin)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, email, is_admin, face_image FROM users ORDER BY id DESC")
    users = cursor.fetchall()
    conn.close()
    return users
# Ajoute ces fonctions à la fin du fichier auth_service.py

def promote_to_admin(email):
    """Promouvoir un utilisateur en admin"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET is_admin = 1 WHERE email = ?", (email,))
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            print(f" {email} promu admin")
        return success
    except Exception as e:
        print(f" Erreur promotion: {e}")
        return False
    finally:
        conn.close()

def demote_from_admin(email):
    """Rétrograder un admin en utilisateur normal"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Vérifier que ce n'est pas le dernier admin
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        admin_count = cursor.fetchone()[0]
        
        if admin_count <= 1:
            print(" Impossible de rétrograder le dernier admin")
            return False
        
        cursor.execute("UPDATE users SET is_admin = 0 WHERE email = ?", (email,))
        conn.commit()
        success = cursor.rowcount > 0
        if success:
            print(f" {email} rétrogradé")
        return success
    except Exception as e:
        print(f" Erreur rétrogradation: {e}")
        return False
    finally:
        conn.close()

def delete_user(user_id):
    """Supprimer un utilisateur par son ID"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Vérifier que ce n'est pas le dernier admin
        cursor.execute("SELECT email, is_admin FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        
        if user and user[1] == 1:  # C'est un admin
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
            admin_count = cursor.fetchone()[0]
            if admin_count <= 1:
                print(" Impossible de supprimer le dernier admin")
                return False
        
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        if deleted:
            print(f" Utilisateur {user_id} supprimé")
        return deleted
    except Exception as e:
        print(f" Erreur suppression: {e}")
        return False
    finally:
        conn.close()
# ... (garde les autres fonctions comme get_users_with_faces, etc.)