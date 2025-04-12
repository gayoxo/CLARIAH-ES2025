import pandas as pd
import os
import sqlite3
import pickle
import re
from tqdm import tqdm
from detoxify import Detoxify

# === CONFIGURACIÓN ===
BASE_PATH = r"E:\GutembergALL"
METADATA_CSV = os.path.join(BASE_PATH, "gutenberg_over_70000_metadata.csv")
BOOKS_FOLDER = os.path.join(BASE_PATH, "books")
DB_PATH = "gutenberg.db"

# Etiquetas de Detoxify
labels = [
    "toxicity", "severe_toxicity", "obscene",
    "identity_attack", "insult", "threat", "sexual_explicit"
]

# Cargar modelo Detoxify
detox_model = Detoxify("original")

# === CONEXIÓN A SQLITE ===
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# === CREAR TABLA SI NO EXISTE ===
cursor.execute("""
CREATE TABLE IF NOT EXISTS procesados (
    book_id INTEGER PRIMARY KEY,
    palabras INTEGER,
    lenguaje TEXT,
    anio INTEGER,
    toxicity REAL,
    severe_toxicity REAL,
    obscene REAL,
    identity_attack REAL,
    insult REAL,
    threat REAL,
    sexual_explicit REAL
)
""")
conn.commit()

# === FUNCIONES ===
def registrar(book_id, palabras, lenguaje, anio, scores):
    try:
        cursor.execute("""
            INSERT INTO procesados (
                book_id, palabras, lenguaje, anio,
                toxicity, severe_toxicity, obscene,
                identity_attack, insult, threat, sexual_explicit
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(book_id) DO UPDATE SET
                palabras = excluded.palabras,
                lenguaje = excluded.lenguaje,
                anio = excluded.anio,
                toxicity = excluded.toxicity,
                severe_toxicity = excluded.severe_toxicity,
                obscene = excluded.obscene,
                identity_attack = excluded.identity_attack,
                insult = excluded.insult,
                threat = excluded.threat,
                sexual_explicit = excluded.sexual_explicit
        """, (
            book_id,
            palabras,
            lenguaje,
            anio,
            float(scores.get("toxicity", 0.0)),
            float(scores.get("severe_toxicity", 0.0)),
            float(scores.get("obscene", 0.0)),
            float(scores.get("identity_attack", 0.0)),
            float(scores.get("insult", 0.0)),
            float(scores.get("threat", 0.0)),
            float(scores.get("sexual_explicit", 0.0))
        ))
        conn.commit()
    except Exception as e:
        print(f"⚠️ Error al registrar {book_id}: {e}")

def buscar_archivo_pkl(book_id):
    patron = f"{book_id}_"
    for root, _, files in os.walk(BOOKS_FOLDER):
        for file in files:
            if file.startswith(patron) and file.endswith(".pkl"):
                return os.path.join(root, file)
    return None

def dividir_en_parrafos(texto):
    texto = re.sub(r'\s+', ' ', texto).strip()
    return [p.strip() for p in texto.split('\n') if p.strip()]

def analizar_parrafos(parrafos):
    if not parrafos:
        return {label: 0.0 for label in labels}

    acumulado = {label: 0.0 for label in labels}
    n = 0

    for p in parrafos:
        try:
            resultados = detox_model.predict(p[:512])
            for label in labels:
                acumulado[label] += float(resultados.get(label, 0.0))
            n += 1
        except Exception as e:
            print(f"⚠️ Error al analizar párrafo: {e}")

    if n == 0:
        return {label: 0.0 for label in labels}

    media = {label: float(acumulado[label] / n) for label in labels}
    return media

# === CARGAR METADATOS ===
df = pd.read_csv(METADATA_CSV)
df = df[df['Language'] == 'English']
df = df.set_index('Book Num')
print(f"📄 Libros en inglés encontrados: {len(df)}")

# === PROCESAR LIBROS ===
for book_id in tqdm(df.index, desc="📖 Analizando libros"):
    file_path = buscar_archivo_pkl(book_id)
    if not file_path:
        continue

    try:
        with open(file_path, "rb") as f:
            texto = pickle.load(f)
        if not isinstance(texto, str):
            raise ValueError("Contenido no es texto")

        palabras = len(texto.split())
        lenguaje = df.loc[book_id, 'Language']

        published = df.loc[book_id, 'Published Date']
        anio = None
        if isinstance(published, str):
            match = re.search(r"(\d{4})", published)
            if match:
                anio = int(match.group(1))

        parrafos = dividir_en_parrafos(texto)
        scores = analizar_parrafos(parrafos)

        registrar(book_id, palabras, lenguaje, anio, scores)
        print(f"✅ Analizado {book_id}")

    except Exception as e:
        print(f"❌ [{book_id}] Error procesando: {e}")

conn.close()
print("✅ Finalizado.")
