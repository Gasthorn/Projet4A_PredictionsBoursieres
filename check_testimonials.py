import sqlite3

conn = sqlite3.connect("users.db")
cursor = conn.cursor()

print("📋 VÉRIFICATION DE LA BASE DE DONNÉES")
print("="*50)

# Liste toutes les tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
print("\n📊 Tables existantes:")
for table in tables:
    print(f"   - {table[0]}")

# Vérifie spécifiquement testimonials
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='testimonials'")
if cursor.fetchone():
    print("\n✅ Table 'testimonials' existe")
    
    # Structure
    cursor.execute("PRAGMA table_info(testimonials)")
    columns = cursor.fetchall()
    print("\n📋 Structure:")
    for col in columns:
        print(f"   - {col[1]} ({col[2]})")
    
    # Nombre de témoignages
    cursor.execute("SELECT COUNT(*) FROM testimonials")
    count = cursor.fetchone()[0]
    print(f"\n📈 Total témoignages: {count}")
    
    # Répartition par statut
    cursor.execute("SELECT status, COUNT(*) FROM testimonials GROUP BY status")
    stats = cursor.fetchall()
    if stats:
        print("\n📊 Répartition:")
        for stat in stats:
            print(f"   - {stat[0]}: {stat[1]}")
    
    # Derniers témoignages
    cursor.execute("""
    SELECT id, user_name, status, created_at 
    FROM testimonials 
    ORDER BY created_at DESC 
    LIMIT 5
    """)
    recent = cursor.fetchall()
    if recent:
        print("\n🆕 5 derniers:")
        for r in recent:
            print(f"   - ID:{r[0]}, {r[1]}, {r[2]}, {r[3]}")
else:
    print("\n❌ Table 'testimonials' n'existe PAS")

conn.close()