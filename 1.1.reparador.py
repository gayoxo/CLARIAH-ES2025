import sqlite3
import pandas as pd

DB_PATH = "gutenberg_all.db"  # o "gutenberg_all.db"
CSV_PATH = "gutenberg_over_70000_metadata.csv"

# Cargar CSV con títulos
df = pd.read_csv(CSV_PATH)
df = df.set_index("Book Num")

# Conectar a la base de datos
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Asegurarse de que la columna exista
cursor.execute("PRAGMA table_info(procesados)")
columnas = [col[1] for col in cursor.fetchall()]
if 'titulo' not in columnas:
    cursor.execute("ALTER TABLE procesados ADD COLUMN titulo TEXT")

# Buscar IDs sin título
cursor.execute("SELECT book_id FROM procesados WHERE titulo IS NULL OR titulo = ''")
ids_faltantes = [r[0] for r in cursor.fetchall()]

for book_id in ids_faltantes:
    try:
        titulo = df.loc[book_id, 'Book Title']
        cursor.execute("UPDATE procesados SET titulo = ? WHERE book_id = ?", (titulo, book_id))
        print(f"✅ Actualizado título para {book_id}")
    except Exception as e:
        print(f"⚠️ No se pudo actualizar {book_id}: {e}")

conn.commit()
conn.close()
print("🎉 Reparación completada.")
