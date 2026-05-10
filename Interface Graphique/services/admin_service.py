import sqlite3
from services.database import get_connection
import datetime


def get_all_users():
    """Récupère tous les utilisateurs avec infos complètes (8 colonnes)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, email, is_admin, face_image,
                   COALESCE(prenom, '') as prenom,
                   COALESCE(nom, '') as nom,
                   COALESCE(created_at, '') as created_at,
                   COALESCE(public_stats, 0) as public_stats
            FROM users ORDER BY id DESC
        """)
        return [(u[0], u[1], u[2] or 0, u[3], u[4], u[5], u[6], bool(u[7])) for u in cursor.fetchall()]
    except Exception as e:
        print(f" Erreur get_all_users: {e}")
        return []
    finally:
        conn.close()


def get_registration_stats(days=30):
    """Retourne les inscriptions par jour sur les N derniers jours"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT DATE(created_at) as day, COUNT(*) as cnt
            FROM users
            WHERE created_at >= DATE('now', ?)
            GROUP BY DATE(created_at)
            ORDER BY day
        """, (f'-{days} days',))
        return {row[0]: row[1] for row in cursor.fetchall()}
    except Exception as e:
        print(f" Erreur get_registration_stats: {e}")
        return {}
    finally:
        conn.close()


def get_platform_trade_stats():
    """Statistiques globales des trades pour le dashboard admin"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT COUNT(*),
                   SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END),
                   SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END),
                   COALESCE(SUM(pnl), 0),
                   COUNT(DISTINCT user_email)
            FROM user_trades
        """)
        total, closed, wins, total_pnl, active = cursor.fetchone()
        closed = closed or 0
        wins = wins or 0
        win_rate = round((wins / closed * 100) if closed > 0 else 0, 1)
        return {
            'total': total or 0,
            'closed': closed,
            'wins': wins,
            'win_rate': win_rate,
            'total_pnl': total_pnl or 0,
            'active_users': active or 0,
        }
    except Exception as e:
        print(f" Erreur get_platform_trade_stats: {e}")
        return {'total': 0, 'closed': 0, 'wins': 0, 'win_rate': 0, 'total_pnl': 0, 'active_users': 0}
    finally:
        conn.close()


def get_top_traders(limit=5):
    """Top traders par PnL total (trades fermés uniquement)"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT ut.user_email,
                   COALESCE(u.prenom, ''), COALESCE(u.nom, ''),
                   COUNT(*) as trades,
                   COALESCE(SUM(ut.pnl), 0) as total_pnl,
                   COALESCE(SUM(CASE WHEN ut.pnl > 0 THEN 1 ELSE 0 END), 0) as wins
            FROM user_trades ut
            LEFT JOIN users u ON u.email = ut.user_email
            WHERE ut.status = 'closed'
            GROUP BY ut.user_email
            ORDER BY total_pnl DESC
            LIMIT ?
        """, (limit,))
        result = []
        for email, prenom, nom, trades, pnl, wins in cursor.fetchall():
            name = " ".join(filter(None, [prenom, nom])).strip() or email.split('@')[0].capitalize()
            win_rate = round((wins / trades * 100) if trades > 0 else 0, 1)
            result.append({'email': email, 'name': name, 'trades': trades, 'pnl': pnl, 'win_rate': win_rate})
        return result
    except Exception as e:
        print(f" Erreur get_top_traders: {e}")
        return []
    finally:
        conn.close()


def get_user_count():
    """Nombre total d'utilisateurs"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0] or 0
    except Exception as e:
        print(f" Erreur get_user_count: {e}")
        return 0
    finally:
        conn.close()


def get_users_with_faces():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM users WHERE face_image IS NOT NULL AND face_image != ''")
        return cursor.fetchone()[0] or 0
    except Exception as e:
        print(f" Erreur get_users_with_faces: {e}")
        return 0
    finally:
        conn.close()


def get_users_without_faces():
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM users WHERE face_image IS NULL OR face_image = ''")
        return cursor.fetchone()[0] or 0
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
        return cursor.rowcount > 0
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
    except Exception as e:
        print(f" Erreur création table logs: {e}")
    finally:
        conn.close()


def create_login_log(user_email, success, method="face"):
    """Crée un log de connexion"""
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
        return cursor.fetchall()
    except Exception as e:
        print(f" Erreur get_login_logs: {e}")
        return []
    finally:
        conn.close()
