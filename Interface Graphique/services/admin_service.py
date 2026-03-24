import sqlite3
from services.database import get_connection
import datetime

def get_all_users():
    """Récupère tous les utilisateurs avec la bonne structure"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, email, is_admin, face_image FROM users ORDER BY id DESC")
        users = cursor.fetchall()
        # S'assurer que chaque tuple a 4 éléments
        result = []
        for user in users:
            if len(user) >= 4:
                result.append((user[0], user[1], user[2] if user[2] else 0, user[3]))
            else:
                print(f" Structure utilisateur incorrecte: {user}")
        return result
    except Exception as e:
        print(f" Erreur get_all_users: {e}")
        return []
    finally:
        conn.close()

def get_user_count():
    """Nombre total d'utilisateurs"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        return count
    except Exception as e:
        print(f" Erreur get_user_count: {e}")
        return 0
    finally:
        conn.close()

def get_users_with_faces():
    """Nombre d'utilisateurs avec reconnaissance faciale"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM users WHERE face_image IS NOT NULL AND face_image != ''")
        count = cursor.fetchone()[0]
        return count
    except Exception as e:
        print(f" Erreur get_users_with_faces: {e}")
        return 0
    finally:
        conn.close()

def get_users_without_faces():
    """Nombre d'utilisateurs sans reconnaissance faciale"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM users WHERE face_image IS NULL OR face_image = ''")
        count = cursor.fetchone()[0]
        return count
    except Exception as e:
        print(f" Erreur get_users_without_faces: {e}")
        return 0
    finally:
        conn.close()

def delete_user(user_id):
    """Supprime un utilisateur"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        return deleted
    except Exception as e:
        print(f" Erreur delete_user: {e}")
        return False
    finally:
        conn.close()

def init_login_logs_table():
    """Crée la table des logs si elle n'existe pas"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            success BOOLEAN,
            method TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        print(" Table login_logs vérifiée/créée")
    except Exception as e:
        print(f" Erreur création table logs: {e}")
    finally:
        conn.close()

def create_login_log(user_email, success, method="face"):
    """Crée un log de connexion"""
    # S'assurer que la table existe
    init_login_logs_table()
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO login_logs (user_email, success, method) VALUES (?, ?, ?)",
            (user_email, 1 if success else 0, method)
        )
        conn.commit()
        return True
    except Exception as e:
        print(f" Erreur create_login_log: {e}")
        return False
    finally:
        conn.close()

def get_login_logs(limit=100):
    """Récupère les derniers logs"""
    # S'assurer que la table existe
    init_login_logs_table()
    
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT id, user_email, success, method, timestamp 
        FROM login_logs 
        ORDER BY timestamp DESC 
        LIMIT ?
        """, (limit,))
        logs = cursor.fetchall()
        return logs
    except Exception as e:
        print(f" Erreur get_login_logs: {e}")
        return []
    finally:
        conn.close()