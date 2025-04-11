import pandas as pd
import os
import sqlite3
from tqdm import tqdm
import shutil

# Ruta base del pendrive
PENDRIVE_PATH = "E:/gutenberg"  # ← ajusta esta línea según tu sistema

METADATA_CSV = os.path.join(PENDRIVE_PATH, "metadata.csv")
BOOKS_FOLDER = os.path.join(PENDRIVE_PATH, "books")
DB_PATH = "gutenberg.db"
LOCAL_TXT_FOLDER = "libros_ingles"

os.makedirs(LOCAL_TXT_FOLDER, exist_ok=True)

# Conexión a SQLite y creación de tabla y vista
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS procesados (
    book_id INTEGER PRIMARY KEY,
    estado TEXT,
    palabras INTEGER,
    lenguaje TEXT,
    anio INTEGER
)
""")

cursor.execute("""
CREATE VIEW IF NOT EXISTS descargados AS
SELECT * FROM procesados
WHERE estado = 'descargado' AND anio IS NOT NULL
""")

conn.commit()

# Función de inserción
def registrar(book_id, estado, palabras=None, lenguaje=None, anio=None):
    try:
        cursor.execute("""
            INSERT INTO procesados (book_id, estado, palabras, lenguaje, anio)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(book_id) DO UPDATE SET
                estado = excluded.estado,
                palabras = COALESCE(excluded.palabras, procesados.palabras),
                lenguaje = COALESCE(excluded.lenguaje, procesados.lenguaje),
                anio = COALESCE(excluded.anio, procesados.anio)
        """, (
            int(book_id),
            str(estado),
            int(palabras) if palabras and str(palabras).isdigit() else None,
            str(lenguaje) if lenguaje else None,
            int(anio) if anio and str(anio).isdigit() else None
        ))
        conn.commit()
    except Exception as e:
        print(f"⚠️ Error al registrar {book_id}: {e}")

# Cargar metadatos
df = pd.read_csv(METADATA_CSV)
df = df[df['language'] == 'en']

print(f"📄 Libros en inglés encontrados: {len(df)}")

# Insertar y copiar libros
for _, row in tqdm(df.iterrows(), total=len(df), desc="📥 Importando libros"):
    book_id = row['gutenberg_id']
    file_path = os.path.join(BOOKS_FOLDER, f"{book_id}.txt")
    local_copy_path = os.path.join(LOCAL_TXT_FOLDER, f"{book_id}.txt")

    if not os.path.exists(file_path):
        continue

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            texto = f.read()
        palabras = len(texto.split())
        anio = row.get('publication_date', None)
        lenguaje = row.get('language', 'en')

        registrar(book_id, "descargado", palabras, lenguaje, anio)

        # Copiar a carpeta local si es inglés y no existe
        if lenguaje == "en" and not os.path.exists(local_copy_path):
            shutil.copyfile(file_path, local_copy_path)
            print(f"📁 Copiado local: {book_id}.txt")

    except Exception as e:
        print(f"⚠️ [{book_id}] Error leyendo archivo: {e}")
        registrar(book_id, "error")

conn.close()
print("✅ Finalizado.")
