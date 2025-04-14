# Requiere: pip install rdflib
import sqlite3
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, XSD

DB_PATH = "gutenberg.db"

# Namespaces
TOX = Namespace("http://etsisi.upm.es/tox/")
BASE = Namespace("http://etsisi.upm.es/book/")

g = Graph()
g.bind("tox", TOX)
g.bind("book", BASE)

# Clases y jerarquía
g.add((TOX.Document, RDF.type, RDFS.Class))
g.add((TOX.ToxicExpression, RDF.type, RDFS.Class))
g.add((TOX.ToxicityCategory, RDF.type, RDFS.Class))
g.add((TOX.LevelOfHate, RDF.type, RDFS.Class))

# Niveles del odio (en inglés)
levels = {
    "BiasedAttitudes": TOX.BiasedAttitudes,
    "ActsOfBias": TOX.ActsOfBias,
    "Discrimination": TOX.Discrimination,
    "BiasMotivatedViolence": TOX.BiasMotivatedViolence,
    "Genocide": TOX.Genocide
}
for label, uri in levels.items():
    g.add((uri, RDF.type, TOX.LevelOfHate))
    g.add((uri, RDFS.label, Literal(label, lang="en")))

# Propiedades
g.add((TOX.hasToxicityScore, RDF.type, RDF.Property))
g.add((TOX.hasCategory, RDF.type, RDF.Property))
g.add((TOX.hasScore, RDF.type, RDF.Property))
g.add((TOX.hasLanguage, RDF.type, RDF.Property))
g.add((TOX.hasYear, RDF.type, RDF.Property))
g.add((TOX.hasTitle, RDF.type, RDF.Property))
g.add((TOX.belongsToLevel, RDF.type, RDF.Property))

# Categorías Detoxify y mapeo a niveles
categories = {
    "toxicity": "BiasedAttitudes",
    "severe_toxicity": "ActsOfBias",
    "obscene": "ActsOfBias",
    "identity_attack": "Discrimination",
    "insult": "ActsOfBias",
    "threat": "BiasMotivatedViolence",
    "sexual_explicit": "ActsOfBias"
}

# Definir las categorías
for cat, level in categories.items():
    uri = TOX[cat]
    g.add((uri, RDF.type, TOX.ToxicityCategory))
    g.add((uri, RDFS.label, Literal(cat.replace("_", " ").capitalize(), lang="en")))
    g.add((uri, TOX.belongsToLevel, levels[level]))

# Leer desde la base de datos
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.execute("SELECT * FROM procesados")
columns = [desc[0] for desc in cur.description]

for row in cur.fetchall():
    data = dict(zip(columns, row))
    doc_uri = BASE[f"book_{data['book_id']}"]
    g.add((doc_uri, RDF.type, TOX.Document))

    if data.get("titulo"):
        g.add((doc_uri, TOX.hasTitle, Literal(data["titulo"])))
    if data.get("lenguaje"):
        g.add((doc_uri, TOX.hasLanguage, Literal(data["lenguaje"])))
    if data.get("anio"):
        g.add((doc_uri, TOX.hasYear, Literal(data["anio"])))

    for cat in categories.keys():
        score = data.get(cat)
        if score is not None:
            node = BNode()
            g.add((node, RDF.type, TOX.ToxicExpression))
            g.add((node, TOX.hasCategory, TOX[cat]))
            g.add((node, TOX.hasScore, Literal(round(score, 5), datatype=XSD.float)))
            g.add((doc_uri, TOX.hasToxicityScore, node))

conn.close()

# Guardar los RDF
g.serialize("export_toxicidad_en.rdf", format="xml")
g.serialize("export_toxicidad_en.ttl", format="turtle")
print("✅ RDF exportado con título incluido.")
