# create_admin.py
import sqlite3
import bcrypt

# Connexion à la base
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Email et mot de passe de l'admin
email = input("Email de l'admin: ")
password = input("Mot de passe: ")

# Hasher le mot de passe
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

try:
    # Vérifier si l'utilisateur existe déjà
    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
    existing = cursor.fetchone()
    
    if existing:
        # Promouvoir en admin
        cursor.execute("UPDATE users SET is_admin = 1 WHERE email = ?", (email,))
        print(f"✅ {email} est maintenant admin !")
    else:
        # Créer un nouvel admin
        cursor.execute(
            "INSERT INTO users (email, password, is_admin) VALUES (?, ?, ?)",
            (email, hashed, 1)
        )
        print(f"✅ Admin créé: {email}")
    
    conn.commit()
    
except Exception as e:
    print(f"❌ Erreur: {e}")
finally:
    conn.close()