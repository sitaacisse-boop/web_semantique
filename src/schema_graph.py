"""
schema_graph.py
Extraction du schéma RDF et construction du graphe de schéma.
"""

from rdflib import Graph, URIRef, RDF, RDFS, OWL
import networkx as nx


class RDFSchemaGraph:
    """
    Extrait le schéma (classes + propriétés) d'un graphe RDF
    et le représente comme un MultiDiGraph NetworkX.

    Nœuds  : classes  (attribut node_type='class')
    Arêtes : propriétés entre classes  (attribut 'property' = URI de la propriété)
    """

    RDF_TYPE = str(RDF.type)

    def __init__(self, rdf_path: str, fmt: str = "turtle"):
        self.raw = Graph()
        self.raw.parse(rdf_path, format=fmt)
        self.schema: nx.MultiDiGraph = nx.MultiDiGraph()
        self._build()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def _build(self):
        for cls in self._classes():
            self.schema.add_node(str(cls), node_type="class")

        for prop, domain, range_ in self._properties():
            d, r = str(domain), str(range_)
            for n in (d, r):
                if n not in self.schema:
                    self.schema.add_node(n, node_type="class")
            self.schema.add_edge(d, r, key=str(prop), property=str(prop))

    def _classes(self):
        classes = set()
        for vocab_class in (OWL.Class, RDFS.Class):
            for s in self.raw.subjects(RDF.type, vocab_class):
                classes.add(s)
        # Classes inférées via domain/range
        for pred in (RDFS.domain, RDFS.range):
            for o in self.raw.objects(None, pred):
                if isinstance(o, URIRef):
                    classes.add(o)
        return classes

    def _properties(self):
        props = []
        for vocab_prop in (OWL.ObjectProperty, OWL.DatatypeProperty, RDF.Property):
            for p in self.raw.subjects(RDF.type, vocab_prop):
                domain = self.raw.value(p, RDFS.domain)
                range_ = self.raw.value(p, RDFS.range)
                if domain and range_:
                    props.append((p, domain, range_))
        # Propriétés avec domain/range sans déclaration de type explicite
        for p in self.raw.subjects(RDFS.domain, None):
            domain = self.raw.value(p, RDFS.domain)
            range_ = self.raw.value(p, RDFS.range)
            if domain and range_ and (p, domain, range_) not in props:
                props.append((p, domain, range_))
        return props

    # ------------------------------------------------------------------
    # Accesseurs
    # ------------------------------------------------------------------

    def get_domain_range(self, prop_uri: str):
        """Retourne (domain, range) d'une propriété, ou (None, None)."""
        p = URIRef(prop_uri)
        domain = self.raw.value(p, RDFS.domain)
        range_ = self.raw.value(p, RDFS.range)
        return (str(domain) if domain else None,
                str(range_) if range_ else None)

    def classes(self):
        return list(self.schema.nodes())

    def properties(self):
        return list({d["property"] for _, _, d in self.schema.edges(data=True)})

    def as_undirected(self) -> nx.Graph:
        """Version non-dirigée (utile pour Steiner Tree)."""
        G = nx.Graph()
        for n, data in self.schema.nodes(data=True):
            G.add_node(n, **data)
        for u, v, data in self.schema.edges(data=True):
            if G.has_edge(u, v):
                G[u][v]["properties"].append(data["property"])
            else:
                G.add_edge(u, v, properties=[data["property"]], weight=1.0)
        return G
