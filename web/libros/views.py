import pandas as pd
import sqlite3
from django.shortcuts import render
from django.http import JsonResponse
from sklearn.cluster import KMeans

def dashboard(request):
    conn = sqlite3.connect('../gutenberg_all.db')  # Ajusta ruta si es necesario
    df = pd.read_sql("""
        SELECT anio, toxicity, severe_toxicity, obscene,
               identity_attack, insult, threat
        FROM libros_view
    """, conn)

    medios = df.groupby("anio").mean().reset_index()
    data = medios.to_dict(orient="list")

    context = {
        "labels": data["anio"],
        "toxicity": data["toxicity"],
        "severe_toxicity": data["severe_toxicity"],
        "obscene": data["obscene"],
        "identity_attack": data["identity_attack"],
        "insult": data["insult"],
        "threat": data["threat"],
    }
    return render(request, "libros/dashboard.html", context)

def grafo_html(request):
    return render(request, "libros/grafo.html")

def grafo_parametrico_html(request, param):
    return render(request, "libros/grafo_parametrico.html", {"param": param})




def grafo_libros(request):
    conn = sqlite3.connect('../gutenberg_all.db')

    df = pd.read_sql("""
        SELECT book_id, anio, lenguaje, titulo,
               toxicity, severe_toxicity, obscene,
               identity_attack, insult, threat
        FROM libros_view
        WHERE anio IS NOT NULL
    """, conn)

    ultimos_10 = sorted(df["anio"].dropna().unique())[-10:]
    df = df[df["anio"].isin(ultimos_10)]

    features = ["toxicity", "severe_toxicity", "obscene", "identity_attack", "insult", "threat"]
    df = df.dropna(subset=features)

    if df.empty:
        return JsonResponse({"error": "Not enough books to display."}, status=400)

    X = df[features]
    kmeans = KMeans(n_clusters=3, random_state=42, n_init='auto')
    df["cluster"] = kmeans.fit_predict(X)

    centros = pd.DataFrame(kmeans.cluster_centers_, columns=features)
    centros["mean"] = centros.mean(axis=1)
    ordenados = centros.sort_values("mean").index.tolist()
    etiquetas = ["Low Toxicity", "Medium Toxicity", "High Toxicity"]
    mapa = {cluster: etiquetas[i] for i, cluster in enumerate(ordenados)}
    df["nivel_toxicidad"] = df["cluster"].map(mapa)

    df = (
        df.groupby(["anio", "nivel_toxicidad"])
        .apply(lambda g: g.sample(n=min(len(g), 30), random_state=42))
        .reset_index(drop=True)
    )

    nodes, edges, seen = [], [], set()
    for _, row in df.iterrows():
        book_id = str(row["book_id"])
        title = row["titulo"] or f"Book {book_id}"
        year = str(row["anio"])
        toxicidad = row["nivel_toxicidad"]
        tox_id = f"tox_{toxicidad.lower().replace(' ', '_')}"

        year_node_id = f"y{year}"
        if year_node_id not in seen:
            nodes.append({"id": year_node_id, "label": year, "group": "anio"})
            seen.add(year_node_id)

        if tox_id not in seen:
            nodes.append({"id": tox_id, "label": toxicidad, "group": "toxicidad"})
            seen.add(tox_id)

        edge_year_to_tox = {"from": year_node_id, "to": tox_id}
        if edge_year_to_tox not in edges:
            edges.append(edge_year_to_tox)

        book_node_id = f"b{book_id}"
        if book_node_id not in seen:
            tooltip = (
                f"Title: {title}\n"
                f"Language: {row['lenguaje']}\n"
                + "\n".join(f"{col}: {row[col]:.4f}" for col in features) + "\n"
                f"Gutenberg: https://www.gutenberg.org/ebooks/{book_id}"
            )
            nodes.append({
                "id": book_node_id,
                "label": title[:40],
                "title": tooltip,
                "group": "libro"
            })
            seen.add(book_node_id)

        edges.append({"from": tox_id, "to": book_node_id})

    return JsonResponse({"nodes": nodes, "edges": edges})



def grafo_parametrico_data(request, param):
    conn = sqlite3.connect('../gutenberg_all.db')

    if param not in ["toxicity", "severe_toxicity", "obscene", "identity_attack", "insult", "threat"]:
        return JsonResponse({"error": "Invalid parameter."}, status=400)

    df = pd.read_sql(f"""
        SELECT book_id, anio, lenguaje, titulo, {param}
        FROM libros_view
        WHERE anio IS NOT NULL AND {param} IS NOT NULL
    """, conn)

    ultimos_10 = sorted(df["anio"].dropna().unique())[-10:]
    df = df[df["anio"].isin(ultimos_10)]

    if df.empty:
        return JsonResponse({"error": "Not enough books to analyze."}, status=400)

    X = df[[param]]
    kmeans = KMeans(n_clusters=3, random_state=42, n_init='auto')
    df["cluster"] = kmeans.fit_predict(X)

    centros = pd.DataFrame(kmeans.cluster_centers_, columns=[param])
    centros["mean"] = centros[param]
    ordenados = centros.sort_values("mean").index.tolist()
    etiquetas = ["Low", "Medium", "High"]
    mapa = {cluster: etiquetas[i] for i, cluster in enumerate(ordenados)}
    df["nivel_toxicidad"] = df["cluster"].map(mapa)

    df = (
        df.groupby(["anio", "nivel_toxicidad"])
        .apply(lambda g: g.sample(n=min(len(g), 30), random_state=42))
        .reset_index(drop=True)
    )

    nodes, edges, seen = [], [], set()
    for _, row in df.iterrows():
        book_id = str(row["book_id"])
        title = row["titulo"] or f"Book {book_id}"
        year = str(row["anio"])
        nivel = row["nivel_toxicidad"]
        tox_id = f"{param}_{nivel.lower()}"

        year_node_id = f"y{year}"
        if year_node_id not in seen:
            nodes.append({"id": year_node_id, "label": year, "group": "anio"})
            seen.add(year_node_id)

        if tox_id not in seen:
            nodes.append({"id": tox_id, "label": f"{nivel} ({param})", "group": "toxicidad"})
            seen.add(tox_id)

        edge_year_to_tox = {"from": year_node_id, "to": tox_id}
        if edge_year_to_tox not in edges:
            edges.append(edge_year_to_tox)

        book_node_id = f"b{book_id}"
        if book_node_id not in seen:
            tooltip = (
                f"Title: {title}\n"
                f"Language: {row['lenguaje']}\n"
                f"{param}: {row[param]:.4f}\n"
                f"Gutenberg: https://www.gutenberg.org/ebooks/{book_id}"
            )
            nodes.append({
                "id": book_node_id,
                "label": title[:40],
                "title": tooltip,
                "group": "libro"
            })
            seen.add(book_node_id)

        edges.append({"from": tox_id, "to": book_node_id})

    return JsonResponse({"nodes": nodes, "edges": edges})

