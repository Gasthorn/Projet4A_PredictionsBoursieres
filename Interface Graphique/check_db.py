# check_db.py
import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Voir la structure de la table
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()
print(" Structure de la table users:")
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

# Voir tous les utilisateurs
cursor.execute("SELECT id, email, face_hash FROM users")
users = cursor.fetchall()
print(f"\n👥 {len(users)} utilisateurs trouvés:")
for user in users:
    print(f"  - ID: {user[0]}, Email: {user[1]}, Face hash: {user[2] if user[2] else ' AUCUN'}")

conn.close()