"""
subgraph_builder.py
Construction des sous-graphes S_q à partir des BGP extraits.
Chaque sous-graphe S_q correspond au sous-graphe du schéma RDF
induit par les classes et propriétés d'une requête q.
"""

from dataclasses import dataclass, field
from typing import Set, FrozenSet, List
import networkx as nx


@dataclass
class Subgraph:
    """
    Représente un sous-graphe orienté requête S_q.

    Attributs :
        query_id    : identifiant de la requête source
        classes     : ensemble des classes impliquées
        properties  : ensemble des propriétés impliquées
        graph       : sous-graphe du schéma (MultiDiGraph)
        freq        : nombre de requêtes avec ce même motif (fréquence)
    """
    query_id: int
    classes: FrozenSet[str]
    properties: FrozenSet[str]
    graph: nx.MultiDiGraph
    freq: int = 1

    def signature(self) -> FrozenSet:
        """Identifiant canonique du motif (classes + propriétés)."""
        return frozenset(self.classes) | frozenset(self.properties)

    def nodes(self) -> Set[str]:
        return set(self.graph.nodes())

    def edges(self) -> List:
        return list(self.graph.edges(data=True))

    def is_empty(self) -> bool:
        return self.graph.number_of_nodes() == 0


class SubgraphBuilder:
    """
    Construit les sous-graphes S_q pour un ensemble de requêtes Q.
    """

    def __init__(self, schema_graph):
        """
        schema_graph : instance de RDFSchemaGraph
        """
        self.schema = schema_graph

    def build(self, query_id: int, classes: Set[str], properties: Set[str]) -> Subgraph:
        """
        Construit S_q = sous-graphe du schéma induit par (classes, properties).

        Algorithme :
        1. Ajouter tous les nœuds (classes) présents dans le schéma.
        2. Ajouter toutes les arêtes (propriétés) reliant ces nœuds
           et dont la propriété figure dans l'ensemble extrait.
        """
        subg = nx.MultiDiGraph()

        # Filtrer les classes qui existent réellement dans le schéma
        valid_classes = {c for c in classes if c in self.schema.schema.nodes()}

        # Si une propriété est connue mais ses classes ne sont pas encore ajoutées,
        # on les ajoute via domain/range
        for prop in properties:
            domain, range_ = self.schema.get_domain_range(prop)
            if domain:
                valid_classes.add(domain)
            if range_:
                valid_classes.add(range_)

        # Ajouter les nœuds
        for cls in valid_classes:
            data = self.schema.schema.nodes.get(cls, {})
            subg.add_node(cls, **data)

        # Ajouter les arêtes (propriétés reliant les classes valides)
        for u, v, key, data in self.schema.schema.edges(keys=True, data=True):
            prop = data.get("property", "")
            if u in valid_classes and v in valid_classes:
                if prop in properties or not properties:
                    subg.add_edge(u, v, key=key, **data)

        return Subgraph(
            query_id=query_id,
            classes=frozenset(valid_classes),
            properties=frozenset(properties),
            graph=subg,
        )

    def build_all(self, extracted_bgps) -> List[Subgraph]:
        """
        Construit les sous-graphes pour une liste de BGPs.

        extracted_bgps : liste de (classes, properties) retournée par SPARQLQueryParser
        Retourne une liste de Subgraph, en regroupant les motifs identiques (même signature).
        """
        subgraphs = []
        signature_map = {}  # signature -> index dans subgraphs

        for qid, (classes, properties) in enumerate(extracted_bgps):
            sq = self.build(qid, classes, properties)
            if sq.is_empty():
                continue

            sig = sq.signature()
            if sig in signature_map:
                # Même motif : incrémenter la fréquence
                subgraphs[signature_map[sig]].freq += 1
            else:
                signature_map[sig] = len(subgraphs)
                subgraphs.append(sq)

        return subgraphs
