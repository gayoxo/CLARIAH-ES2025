import pandas as pd
import os
import sqlite3
import pickle
import re
from tqdm import tqdm

# === CONFIGURACIÓN ===
BASE_PATH = r"E:\GutembergALL"
METADATA_CSV = os.path.join(BASE_PATH, "gutenberg_over_70000_metadata.csv")
BOOKS_FOLDER = os.path.join(BASE_PATH, "books")
DB_PATH = "gutenberg.db"
LOCAL_TXT_FOLDER = "libros_ingles"
os.makedirs(LOCAL_TXT_FOLDER, exist_ok=True)

# 💡 Si usas Git, añade esto a tu .gitignore para excluir los textos locales:
# libros_ingles/

# === CONEXIÓN A SQLITE ===
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
SELECT * FROM procesados WHERE estado = 'descargado' AND anio IS NOT NULL
""")

cursor.execute("""
CREATE VIEW IF NOT EXISTS errores AS
SELECT * FROM procesados WHERE estado = 'error'
""")

conn.commit()

# === FUNCIÓN DE INSERCIÓN ROBUSTA ===
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

# === BUSCAR ARCHIVO PKL CORRESPONDIENTE A UN ID ===
def buscar_archivo_pkl(book_id):
    patron = f"{book_id}_"
    for root, _, files in os.walk(BOOKS_FOLDER):
        for file in files:
            if file.startswith(patron) and file.endswith(".pkl"):
                return os.path.join(root, file)
    return None

# === CARGAR METADATOS CSV ===
df = pd.read_csv(METADATA_CSV)
df = df[df['Language'] == 'English']
df = df.set_index('Book Num')

print(f"📄 Libros en inglés encontrados: {len(df)}")

# === PROCESAR LIBROS ===
for book_id in tqdm(df.index, desc="📥 Importando libros"):
    file_path = buscar_archivo_pkl(book_id)
    if not file_path:
        continue

    local_copy_path = os.path.join(LOCAL_TXT_FOLDER, f"{book_id}.txt")

    try:
        with open(file_path, "rb") as f:
            texto = pickle.load(f)

        if not isinstance(texto, str):
            raise ValueError("Contenido no es texto")

        palabras = len(texto.split())
        lenguaje = df.loc[book_id, 'Language']

        # ⏳ Extraer año desde Published Date
        published = df.loc[book_id, 'Published Date']
        anio = None
        if isinstance(published, str):
            match = re.search(r"(\d{4})", published)
            if match:
                anio = int(match.group(1))

        registrar(book_id, "descargado", palabras, lenguaje, anio)

        if not os.path.exists(local_copy_path):
            with open(local_copy_path, "w", encoding="utf-8") as f:
                f.write(texto)
            print(f"📁 Copiado local: {book_id}.txt")

    except Exception as e:
        print(f"⚠️ [{book_id}] Error leyendo archivo: {e}")
        registrar(book_id, "error")

# === FINALIZAR ===
conn.close()
print("✅ Finalizado.")
