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
        # Nombre d'utilisateurs non-admin
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 0")
        user_count = cursor.fetchone()[0] or 0

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
        closed = trade_stats[1] or 0
        winning = trade_stats[2] or 0
        win_rate = round((winning / closed * 100) if closed > 0 else 0, 1)

        # Note moyenne des témoignages approuvés
        cursor.execute("SELECT COALESCE(AVG(rating), 4.9) FROM testimonials WHERE status = 'approved'")
        avg_rating = round(cursor.fetchone()[0] or 4.9, 1)

        # Nombre de témoignages approuvés
        cursor.execute("SELECT COUNT(*) FROM testimonials WHERE status = 'approved'")
        testimonials_count = cursor.fetchone()[0] or 0

        return {
            'user_count': user_count,
            'total_trades': trade_stats[0] or 0,
            'closed_trades': closed,
            'winning_trades': winning,
            'total_pnl': trade_stats[3] or 0,
            'avg_return': trade_stats[4] or 0,
            'win_rate': win_rate,
            'avg_rating': avg_rating,
            'testimonials_count': testimonials_count,
        }
    except Exception as e:
        print(f"⚠️ Erreur get_global_stats: {e}")
        return {
            'user_count': 0, 'total_trades': 0, 'closed_trades': 0,
            'winning_trades': 0, 'total_pnl': 0, 'avg_return': 0,
            'win_rate': 0, 'avg_rating': 4.9, 'testimonials_count': 0,
        }
    finally:
        conn.close()


def get_rich_testimonials(limit=10):
    """Témoignages approuvés avec vraies stats utilisateurs (trades, gains, win rate)"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        SELECT t.user_email, t.user_name, t.content, t.rating,
               t.investment, t.gain, t.period, t.created_at,
               u.prenom, u.nom, u.created_at AS member_since,
               COALESCE(u.public_stats, 0) AS public_stats,
               COALESCE(u.is_online, 0) AS is_online
        FROM testimonials t
        LEFT JOIN users u ON u.email = t.user_email
        WHERE t.status = 'approved'
        ORDER BY t.created_at DESC
        LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()

        result = []
        for row in rows:
            email, user_name, content, rating, investment, gain, period, created_at, prenom, nom, member_since, public_stats, is_online = row

            # Stats réelles uniquement si l'utilisateur a activé la visibilité publique
            trades, wins, real_pnl, win_rate = 0, 0, 0.0, 0.0
            if public_stats:
                cursor.execute("""
                SELECT COUNT(*),
                       COALESCE(SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END), 0),
                       COALESCE(SUM(pnl), 0)
                FROM user_trades
                WHERE user_email = ? AND status = 'closed'
                """, (email,))
                ts = cursor.fetchone()
                trades = ts[0] or 0
                wins = ts[1] or 0
                real_pnl = ts[2] or 0.0
                win_rate = round((wins / trades * 100) if trades > 0 else 0.0, 1)

            recent_trades = []
            if public_stats:
                cursor.execute("""
                SELECT symbol, prediction_direction, quantity, pnl, pnl_percentage, entry_date
                FROM user_trades
                WHERE user_email = ? AND status = 'closed'
                ORDER BY entry_date DESC
                LIMIT 3
                """, (email,))
                recent_trades = [
                    {
                        'symbol': r[0],
                        'signal': r[1],
                        'amount': r[2] or 0,
                        'pnl': r[3] or 0,
                        'pnl_pct': r[4] or 0,
                        'date': str(r[5])[:10] if r[5] else '',
                    }
                    for r in cursor.fetchall()
                ]

            # Nom affiché : prénom + nom > user_name > email prefix
            full = " ".join(filter(None, [prenom, nom])).strip()
            display_name = full or user_name or email.split('@')[0].capitalize()
            parts = display_name.split()
            initials = (parts[0][0] + (parts[-1][0] if len(parts) > 1 else parts[0][-1])).upper()

            # Gain affiché : PnL réel si public (même si 0), sinon champ du formulaire
            if public_stats:
                display_gain = real_pnl
            else:
                display_gain = float(gain) if gain else 0.0

            # Ancienneté en mois (0 = moins d'un mois)
            member_months = 0
            if member_since:
                try:
                    from datetime import datetime as _dt
                    since = _dt.fromisoformat(str(member_since).split('.')[0])
                    member_months = max(0, (_dt.now() - since).days // 30)
                except Exception:
                    pass

            result.append({
                'email': email,
                'name': display_name,
                'initials': initials,
                'content': content or '',
                'rating': int(rating or 5),
                'gain': display_gain,
                'trades': trades if public_stats else None,
                'win_rate': win_rate if public_stats else None,
                'period': period or '',
                'member_months': member_months,
                'public_stats': bool(public_stats),
                'is_online': bool(is_online),
            })

        return result
    except Exception as e:
        print(f"⚠️ Erreur get_rich_testimonials: {e}")
        return []
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


def save_followed_trade(user_email, symbol, signal, entry_price, current_price, amount, action='ACHAT', model_type='sentiment'):
    """Sauvegarde un trade que l'utilisateur confirme avoir suivi.
    action : 'ACHAT' (position longue) ou 'VENTE' (position courte/vente à découvert)
    model_type : 'sentiment' | 'lstm'
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        sig_to_dir = {'HAUSSIER': 'up', 'BAISSIER': 'down', 'NEUTRE': 'neutral'}
        pred_dir = sig_to_dir.get(signal, 'neutral')

        if action == 'ACHAT':
            pnl = (current_price - entry_price) / entry_price * amount
            actual_dir = 'up'
        elif action == 'VENTE':
            pnl = (entry_price - current_price) / entry_price * amount
            actual_dir = 'down'
        else:
            pnl = 0.0
            actual_dir = 'neutral'

        pnl_pct = (pnl / amount * 100) if amount > 0 else 0.0
        model_type = model_type or 'sentiment'

        cursor.execute("""
        INSERT INTO user_trades
        (user_email, symbol, entry_price, exit_price, quantity, prediction_direction, actual_direction, pnl, pnl_percentage, status, model_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'closed', ?)
        """, (user_email, symbol, round(entry_price, 2), round(current_price, 2),
              round(amount, 2), pred_dir, actual_dir, round(pnl, 2), round(pnl_pct, 2), model_type))

        conn.commit()
        print(f"✅ Trade sauvegardé: {symbol} | {signal} | PnL: {pnl:+.2f}€")
        return True
    except Exception as e:
        print(f"❌ Erreur save_followed_trade: {e}")
        return False
    finally:
        conn.close()
