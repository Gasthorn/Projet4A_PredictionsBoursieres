# check_db_structure.py
import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

print("📋 Structure de la table users:")
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

print("\n👥 Utilisateurs:")
cursor.execute("SELECT id, email, is_admin, face_image FROM users")
users = cursor.fetchall()
for user in users:
    print(f"  - ID: {user[0]}, Email: {user[1]}, Admin: {user[2]}, Face: {'Oui' if user[3] else 'Non'}")

# Vérifier/créer la table des logs
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

print("\n📊 Table login_logs vérifiée/créée")

conn.close()