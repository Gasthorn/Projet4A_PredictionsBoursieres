import sqlite3
from services.database import get_connection

import datetime

def init_testimonials_table():
    """Crée la table des témoignages"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS testimonials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        user_name TEXT NOT NULL,
        content TEXT NOT NULL,
        rating INTEGER DEFAULT 5,
        investment REAL,
        gain REAL,
        period TEXT,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        approved_at DATETIME,
        FOREIGN KEY (user_email) REFERENCES users(email)
    )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Table testimonials initialisée")

def add_testimonial(user_email, user_name, content, rating=5, investment=None, gain=None, period=None):
    """Ajoute un témoignage en attente de validation"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        print(f"📝 Ajout témoignage pour {user_email} avec statut 'pending'")
        
        cursor.execute("""
        INSERT INTO testimonials 
        (user_email, user_name, content, rating, investment, gain, period, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (user_email, user_name, content, rating, investment, gain, period))
        
        conn.commit()
        
        # Vérification immédiate
        cursor.execute("SELECT id, status FROM testimonials WHERE user_email = ? ORDER BY created_at DESC LIMIT 1", (user_email,))
        result = cursor.fetchone()
        print(f"✅ Témoignage ajouté: ID {result[0]}, statut: {result[1]}")
        
        return True
    except Exception as e:
        print(f"❌ Erreur ajout témoignage: {e}")
        return False
    finally:
        conn.close()

def get_approved_testimonials(limit=10):
    """Récupère les témoignages approuvés"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        SELECT user_name, content, rating, investment, gain, period, created_at
        FROM testimonials 
        WHERE status = 'approved'
        ORDER BY created_at DESC
        LIMIT ?
        """, (limit,))
        
        results = cursor.fetchall()
        return results
    except Exception as e:
        print(f"⚠️ Erreur get_approved_testimonials: {e}")
        return []
    finally:
        conn.close()

def get_pending_testimonials():
    """Récupère les témoignages en attente (pour admin)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        print("🔍 Recherche des témoignages en attente...")
        
        cursor.execute("""
        SELECT id, user_email, user_name, content, rating, investment, gain, period, created_at
        FROM testimonials 
        WHERE status = 'pending'
        ORDER BY created_at DESC
        """)
        
        results = cursor.fetchall()
        print(f"📊 {len(results)} témoignage(s) en attente trouvé(s)")
        
        # Affiche les IDs pour debug
        for r in results:
            print(f"   - ID: {r[0]}, Utilisateur: {r[2]}, Statut: en attente")
            
        return results
    except Exception as e:
        print(f"⚠️ Erreur get_pending_testimonials: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        conn.close()

def approve_testimonial(testimonial_id):
    """Approuve un témoignage"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        UPDATE testimonials 
        SET status = 'approved', approved_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (testimonial_id,))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Erreur approve_testimonial: {e}")
        return False
    finally:
        conn.close()

def reject_testimonial(testimonial_id):
    """Rejette un témoignage"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        UPDATE testimonials 
        SET status = 'rejected'
        WHERE id = ?
        """, (testimonial_id,))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Erreur reject_testimonial: {e}")
        return False
    finally:
        conn.close()

def get_user_testimonial(user_email):
    """Vérifie si l'utilisateur a déjà un témoignage"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        SELECT id, status FROM testimonials 
        WHERE user_email = ?
        ORDER BY created_at DESC
        LIMIT 1
        """, (user_email,))
        
        result = cursor.fetchone()
        return result
    except Exception as e:
        print(f"⚠️ Erreur get_user_testimonial: {e}")
        return None
    finally:
        conn.close()

def get_global_stats():
    """Statistiques globales pour la page témoignages"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Stats globales des trades
        cursor.execute("""
        SELECT 
            COUNT(*) as total_trades,
            SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_trades,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
            COALESCE(SUM(pnl), 0) as total_pnl,
            COALESCE(AVG(pnl_percentage), 0) as avg_return
        FROM user_trades
        """)
        
        trade_stats = cursor.fetchone()
        
        # Top performers
        cursor.execute("""
        SELECT user_email, COALESCE(SUM(pnl), 0) as total_pnl
        FROM user_trades
        WHERE status = 'closed'
        GROUP BY user_email
        ORDER BY total_pnl DESC
        LIMIT 5
        """)
        
        top_users = cursor.fetchall()
        
        # Précision des prédictions
        cursor.execute("""
        SELECT COALESCE(AVG(CASE WHEN accuracy = 1 THEN 100.0 ELSE 0 END), 0) as accuracy_rate
        FROM predictions_log
        WHERE accuracy IS NOT NULL
        """)
        
        accuracy = cursor.fetchone()[0] or 0
        
        # Nombre de témoignages approuvés
        cursor.execute("""
        SELECT COUNT(*) FROM testimonials WHERE status = 'approved'
        """)
        
        testimonials_count = cursor.fetchone()[0] or 0
        
        return {
            'total_trades': trade_stats[0] or 0,
            'closed_trades': trade_stats[1] or 0,
            'winning_trades': trade_stats[2] or 0,
            'total_pnl': trade_stats[3] or 0,
            'avg_return': trade_stats[4] or 0,
            'accuracy': accuracy,
            'top_users': top_users or [],
            'testimonials_count': testimonials_count
        }
    except Exception as e:
        print(f"⚠️ Erreur get_global_stats: {e}")
        return {
            'total_trades': 0,
            'closed_trades': 0,
            'winning_trades': 0,
            'total_pnl': 0,
            'avg_return': 0,
            'accuracy': 0,
            'top_users': [],
            'testimonials_count': 0
        }
    finally:
        conn.close()

def get_user_stats(user_email):
    """Calcule les statistiques d'un utilisateur"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Trades fermés
        cursor.execute("""
        SELECT 
            COUNT(*),
            COALESCE(SUM(pnl), 0),
            COALESCE(AVG(pnl_percentage), 0),
            COALESCE(SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END), 0) as wins,
            COALESCE(SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END), 0) as losses
        FROM user_trades 
        WHERE user_email = ? AND status = 'closed'
        """, (user_email,))
        
        stats = cursor.fetchone()
        
        # Trade en cours
        cursor.execute("""
        SELECT COUNT(*) FROM user_trades 
        WHERE user_email = ? AND status = 'open'
        """, (user_email,))
        
        open_trades = cursor.fetchone()[0]
        
        total_trades = stats[0] if stats[0] else 0
        total_pnl = stats[1] if stats[1] else 0
        avg_pnl = stats[2] if stats[2] else 0
        wins = stats[3] if stats[3] else 0
        losses = stats[4] if stats[4] else 0
        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'total_pnl': total_pnl,
            'avg_pnl': avg_pnl,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'open_trades': open_trades
        }
    except Exception as e:
        print(f"⚠️ Erreur get_user_stats: {e}")
        return {
            'total_trades': 0,
            'total_pnl': 0,
            'avg_pnl': 0,
            'wins': 0,
            'losses': 0,
            'win_rate': 0,
            'open_trades': 0
        }
    finally:
        conn.close()

def get_user_trades(user_email, limit=50):
    """Récupère les trades d'un utilisateur"""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
        SELECT * FROM user_trades 
        WHERE user_email = ? 
        ORDER BY entry_date DESC 
        LIMIT ?
        """, (user_email, limit))
        
        return cursor.fetchall()
    except Exception as e:
        print(f"⚠️ Erreur get_user_trades: {e}")
        return []
    finally:
        conn.close()