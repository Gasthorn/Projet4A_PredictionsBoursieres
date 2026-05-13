import sqlite3
import bcrypt

DB_NAME = "users.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def init_db():
    """Initialise la base de données avec toutes les tables"""
    conn = get_connection()
    cursor = conn.cursor()

    # === TABLE USERS ===
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        print("🆕 Création de la table users...")
        cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password BLOB NOT NULL,
            face_image TEXT,
            is_admin INTEGER DEFAULT 0,
            prenom TEXT,
            nom TEXT,
            telephone TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
        print("✅ Table users créée avec succès")
        
        # Créer un admin par défaut
        create_default_admin(conn)
    else:
        # Vérifier les colonnes existantes
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'is_admin' not in columns:
            print("🔄 Migration: ajout de la colonne is_admin...")
            cursor.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0")
            conn.commit()
            print("✅ Migration is_admin réussie")
        
        if 'face_image' not in columns:
            print("🔄 Migration: ajout de la colonne face_image...")
            cursor.execute("ALTER TABLE users ADD COLUMN face_image TEXT")
            conn.commit()
            print("✅ Migration face_image réussie")
        
        if 'created_at' not in columns:
            print("🔄 Migration: ajout de la colonne created_at...")
            cursor.execute("ALTER TABLE users ADD COLUMN created_at DATETIME")
            conn.commit()
            cursor.execute("UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
            conn.commit()
            print("✅ Migration created_at réussie")

        if 'prenom' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN prenom TEXT")
            conn.commit()
            print("✅ Migration prenom réussie")

        if 'nom' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN nom TEXT")
            conn.commit()
            print("✅ Migration nom réussie")

        if 'telephone' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN telephone TEXT")
            conn.commit()
            print("✅ Migration telephone réussie")

        if 'public_stats' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN public_stats INTEGER DEFAULT 0")
            conn.commit()
            print("✅ Migration public_stats réussie")

        if 'is_online' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN is_online INTEGER DEFAULT 0")
            conn.commit()
            print("✅ Migration is_online réussie")

        print("📦 Table users déjà existante, conservation des données")
        ensure_admin_exists(conn)

    # === TABLE USER_TRADES ===
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT NOT NULL,
        symbol TEXT NOT NULL,
        entry_price REAL NOT NULL,
        exit_price REAL,
        entry_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        exit_date DATETIME,
        quantity REAL,
        prediction_direction TEXT,
        actual_direction TEXT,
        pnl REAL,
        pnl_percentage REAL,
        status TEXT DEFAULT 'open',
        model_type TEXT DEFAULT 'sentiment',
        FOREIGN KEY (user_email) REFERENCES users(email)
    )
    """)
    print("✅ Table user_trades vérifiée/créée")

    # Migration: model_type column (for existing databases)
    cursor.execute("PRAGMA table_info(user_trades)")
    trade_columns = [col[1] for col in cursor.fetchall()]
    if 'model_type' not in trade_columns:
        cursor.execute("ALTER TABLE user_trades ADD COLUMN model_type TEXT DEFAULT 'sentiment'")
        conn.commit()
        print("✅ Migration model_type réussie")

    # === TABLE PREDICTIONS_LOG ===
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        prediction_price REAL,
        prediction_direction TEXT,
        confidence REAL,
        model_version TEXT,
        predicted_date DATE,
        actual_price REAL,
        actual_direction TEXT,
        accuracy BOOLEAN,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    print("✅ Table predictions_log vérifiée/créée")

    # === TABLE TESTIMONIALS ===
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
    print("✅ Table testimonials vérifiée/créée")

    conn.commit()
    conn.close()
    print("🎯 Toutes les tables sont initialisées avec succès")

def create_default_admin(conn):
    """Crée un admin par défaut"""
    cursor = conn.cursor()
    
    default_email = "admin@ensim.com"
    default_password = "Admin123!"
    
    hashed = bcrypt.hashpw(default_password.encode(), bcrypt.gensalt())
    
    try:
        cursor.execute(
            "INSERT INTO users (email, password, is_admin) VALUES (?, ?, ?)",
            (default_email, hashed, 1)
        )
        conn.commit()
        print("👑 Admin par défaut créé: admin@ensim.com / Admin123!")
        print("⚠️  CHANGE CE MOT DE PASSE DÈS QUE POSSIBLE !")
    except sqlite3.IntegrityError:
        print("ℹ️ Admin par défaut déjà existant")
    except Exception as e:
        print(f"❌ Erreur création admin: {e}")

def ensure_admin_exists(conn):
    """S'assure qu'il y a au moins un admin"""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("⚠️ Aucun admin trouvé, création d'un admin par défaut...")
        create_default_admin(conn)
    else:
        print(f"👥 {count} administrateur(s) trouvé(s)")
