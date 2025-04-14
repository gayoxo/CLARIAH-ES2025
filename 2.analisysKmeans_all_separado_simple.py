import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

def crear_vista_rango_continuo_sqlite(conn, min_libros):
    df = pd.read_sql("""
        SELECT anio, COUNT(*) AS num_libros
        FROM procesados
        WHERE anio IS NOT NULL
        GROUP BY anio
        ORDER BY anio
    """, conn)

    anios_validos = df[df["num_libros"] >= min_libros]["anio"].tolist()

    if not anios_validos:
        raise ValueError("No hay años con suficientes libros para el análisis.")

    secuencias, temp = [], [anios_validos[0]]
    for i in range(1, len(anios_validos)):
        if anios_validos[i] == anios_validos[i-1] + 1:
            temp.append(anios_validos[i])
        else:
            secuencias.append(temp)
            temp = [anios_validos[i]]
    secuencias.append(temp)

    rango_max = max(secuencias, key=len)
    anio_ini, anio_fin = rango_max[0], rango_max[-1]
    print(f"\U0001F4C5 Rango continuo seleccionado: {anio_ini} - {anio_fin} ({len(rango_max)} años)")

    query = f"""
        CREATE VIEW IF NOT EXISTS libros_view AS
        SELECT * FROM procesados
        WHERE anio BETWEEN {anio_ini} AND {anio_fin}
          AND anio IN (
              SELECT anio FROM (
                  SELECT anio, COUNT(*) AS total
                  FROM procesados
                  GROUP BY anio
              ) WHERE total >= {min_libros}
          )
    """
    conn.execute(query)
    conn.commit()
    print("✅ Vista 'libros_view' creada.")

def exporttxt(df, nombre_archivo):
    with pd.option_context('display.max_rows', None, 'display.max_columns', None):
        contenido = df.to_string(index=True)
    with open(nombre_archivo, 'w', encoding='utf-8') as f:
        f.write(contenido)
    print(f"✅ DataFrame exportado a '{nombre_archivo}' correctamente.")

def main():
    MIN_LIBROS_POR_ANIO = 50
    DB_PATH = "gutenberg_all.db"
    conn = sqlite3.connect(DB_PATH)
    crear_vista_rango_continuo_sqlite(conn, MIN_LIBROS_POR_ANIO)

    df = pd.read_sql("""
        SELECT anio, lenguaje, toxicity, severe_toxicity, obscene,
               identity_attack, insult, threat
        FROM libros_view
    """, conn)

    features = ["toxicity", "severe_toxicity", "obscene", "identity_attack", "insult", "threat"]

    # Media anual por lenguaje
    medias = df.groupby(["anio", "lenguaje"])[features].mean().reset_index()
    exporttxt(medias, "medias_anuales_por_lenguaje.txt")

    # Gráfico 1: evolución media por idioma
    plt.figure(figsize=(16, 8))
    for lang in medias["lenguaje"].unique():
        medias_lang = medias[medias["lenguaje"] == lang]
        avg = medias_lang[features].mean(axis=1)
        plt.plot(medias_lang["anio"], avg, marker='o', label=lang)

    plt.title("Evolución anual de la toxicidad media por idioma")
    plt.xlabel("Año")
    plt.ylabel("Toxicidad media (promedio de índices)")
    plt.legend(title="Lenguaje", loc='upper center', bbox_to_anchor=(0.5, -0.2),
               ncol=9, fontsize='small')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    # Gráfico 2: barras para el año más reciente
    ultimo_anio = df["anio"].max()
    resumen_ultimo = df[df["anio"] == ultimo_anio].groupby("lenguaje")[features].mean()
    exporttxt(resumen_ultimo, f"resumen_toxicidad_{ultimo_anio}.txt")

    resumen_ultimo.plot(kind="bar", figsize=(14, 7))
    plt.title(f"Media de toxicidad por lenguaje en {ultimo_anio}")
    plt.ylabel("Media de índice")
    plt.xlabel("Lenguaje")
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.grid(axis='y')
    plt.show()

if __name__ == "__main__":
    main()
