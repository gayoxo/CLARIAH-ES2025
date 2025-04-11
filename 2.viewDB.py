import sqlite3

DB_PATH = "gutenberg.db"

def crear_vista_descargados():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE VIEW IF NOT EXISTS descargados AS
    SELECT *
    FROM procesados
    WHERE estado = 'descargado' AND anio IS NOT NULL
    """)

    conn.commit()
    conn.close()
    print("✅ Vista 'descargados' creada (solo con año definido).")

if __name__ == "__main__":
    try:
        crear_vista_descargados()
    except Exception as e:
        print(f"⚠️ Error al crear la vista: {e}")
