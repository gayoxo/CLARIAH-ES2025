import sqlite3
import pandas as pd
from sklearn.cluster import KMeans
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
    print("✅ Vista 'libros_view' creada con el rango continuo más largo.")

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

    df_total = pd.read_sql("""
        SELECT book_id, anio, palabras, lenguaje, toxicity, severe_toxicity, obscene,
               identity_attack, insult, threat, sexual_explicit
        FROM libros_view
    """, conn)

    features = ["toxicity", "severe_toxicity", "obscene", "identity_attack", "insult", "threat"]
    etiquetas = ["Toxicidad Bajo", "Toxicidad Medio", "Toxicidad Alto"]
    colores = {"Toxicidad Bajo": "#8BC34A", "Toxicidad Medio": "#FFC107", "Toxicidad Alto": "#F44336"}

    for lang, df in df_total.groupby("lenguaje"):
        if len(df) < 50:
            print(f"⏭️ Omitiendo '{lang}' por tener pocos libros ({len(df)}).")
            continue

        print(f"\n📚 Analizando lenguaje: {lang} ({len(df)} libros)")

        X = df[features]
        kmeans = KMeans(n_clusters=3, random_state=42)
        df["cluster"] = kmeans.fit_predict(X)

        cluster_mean = df.groupby("cluster")[features].mean()
        cluster_mean["avg"] = cluster_mean.mean(axis=1)
        cluster_mean = cluster_mean.sort_values("avg")
        cluster_to_label = {cluster: label for cluster, label in zip(cluster_mean.index, etiquetas)}
        df["toxicidad"] = df["cluster"].map(cluster_to_label)

        count_by_year = df.groupby(["anio", "toxicidad"]).size().unstack(fill_value=0)
        percentages = count_by_year.div(count_by_year.sum(axis=1), axis=0) * 100
        percentages = percentages[etiquetas]

        exporttxt(percentages, f"percentages_libros_{lang}.txt")

        plt.figure(figsize=(25, 6))
        percentages.plot(kind="bar", stacked=True, color=[colores[col] for col in percentages.columns])
        plt.title(f"Porcentaje de libros por grupo de toxicidad y año - {lang}")
        plt.xlabel("Año")
        plt.ylabel("Porcentaje (%)")
        plt.xticks(rotation=45)
        plt.legend(title="Nivel de toxicidad")
        plt.tight_layout()
        plt.show()

        medias_por_indice = df.groupby("anio")[features].mean()
        exporttxt(medias_por_indice, f"medias_por_indice_libros_{lang}.txt")

        plt.figure(figsize=(14, 7))
        for feature in features:
            plt.plot(medias_por_indice.index, medias_por_indice[feature], marker='o', label=feature)
        plt.title(f"Evolución anual de los índices de toxicidad - {lang}")
        plt.xlabel("Año")
        plt.ylabel("Media de toxicidad")
        plt.legend(title="Índice de toxicidad", bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.grid(True)
        plt.tight_layout()
        plt.show()

        df["total_toxicidad"] = df[features].sum(axis=1)
        suma_total_anual = df.groupby("anio")["total_toxicidad"].sum()

        plt.figure(figsize=(14, 6))
        plt.plot(suma_total_anual.index, suma_total_anual.values, marker='o', color='darkred')
        plt.title(f"Toxicidad total combinada por año - {lang}")
        plt.xlabel("Año")
        plt.ylabel("Suma total de toxicidad")
        plt.grid(True)
        plt.tight_layout()
        plt.show()

if __name__ == "__main__":
    main()
