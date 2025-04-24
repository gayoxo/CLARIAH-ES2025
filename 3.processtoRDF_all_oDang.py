# Requiere: pip install rdflib
import sqlite3
from rdflib import Graph, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, XSD, SKOS

DB_PATH = "gutenberg_all.db"

# Namespaces
TOX = Namespace("http://etsisi.upm.es/tox/")
BASE = Namespace("http://etsisi.upm.es/book/")
ODANG = Namespace("http://w3id.org/odang#")

g = Graph()
g.bind("tox", TOX)
g.bind("book", BASE)
g.bind("odang", ODANG)
g.bind("skos", SKOS)

# Clases y jerarquía
g.add((TOX.Document, RDF.type, RDFS.Class))
g.add((TOX.ToxicExpression, RDF.type, RDFS.Class))
g.add((TOX.ToxicityCategory, RDF.type, RDFS.Class))
g.add((TOX.LevelOfHate, RDF.type, RDFS.Class))

# Niveles del odio
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

# Categorías Detoxify y mapeo a niveles + equivalencias O-Dang!
categories = {
    "toxicity": ("BiasedAttitudes", ODANG.GeneralToxicity),
    "severe_toxicity": ("ActsOfBias", ODANG.ExtremeToxicity),
    "obscene": ("ActsOfBias", ODANG.ObsceneLanguage),
    "identity_attack": ("Discrimination", ODANG.IdentityAttack),
    "insult": ("ActsOfBias", ODANG.Insult),
    "threat": ("BiasMotivatedViolence", ODANG.Threat),
    "sexual_explicit": ("ActsOfBias", ODANG.SexualHarassment)
}

# Definir las categorías y relaciones semánticas
for cat, (level, odang_uri) in categories.items():
    cat_uri = TOX[cat]
    g.add((cat_uri, RDF.type, TOX.ToxicityCategory))
    g.add((cat_uri, RDFS.label, Literal(cat.replace("_", " ").capitalize(), lang="en")))
    g.add((cat_uri, TOX.belongsToLevel, levels[level]))
    g.add((cat_uri, SKOS.exactMatch, odang_uri))

# Conectar a la base de datos
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

# Guardar archivos RDF
g.serialize("export_toxicidad_all_odang.rdf", format="xml")
g.serialize("export_toxicidad_all_odang.ttl", format="turtle")
print("✅ RDF exportado con equivalencias O-Dang!")
