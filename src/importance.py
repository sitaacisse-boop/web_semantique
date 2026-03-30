"""
importance.py
Calcul du score d'importance I(S) pour chaque sous-graphe S.

Formule (Section 7.4 du document) :
    I(S) = α · freq(S) + β · ExternalConnectivity(S) + γ · Diversité(S)

avec α + β + γ = 1 et α, β, γ ≥ 0.

Les trois composantes sont normalisées dans [0, 1] avant combinaison.
"""

from typing import List, Tuple
import numpy as np
try:
    from .subgraph_builder import Subgraph
except ImportError:
    import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.subgraph_builder import Subgraph


# ------------------------------------------------------------------
# Composantes individuelles
# ------------------------------------------------------------------

def compute_frequency(sq: Subgraph, total_queries: int) -> float:
    """
    freq(S) = nombre d'occurrences du motif / nombre total de requêtes.
    Valeur dans [0, 1].
    """
    if total_queries == 0:
        return 0.0
    return sq.freq / total_queries


def compute_external_connectivity(sq: Subgraph, schema_graph) -> int:
    """
    ExternalConnectivity(S) = nombre de relations distinctes (p, u) telles que :
        - u ∉ V(S)  (nœud externe au sous-graphe)
        - ∃ v ∈ V(S) : (v, p, u) ∈ E  ou  (u, p, v) ∈ E

    Si plusieurs nœuds internes sont reliés au même nœud externe via la même
    propriété, on ne compte qu'une seule relation (conformément à la définition).
    """
    internal = sq.nodes()
    external_relations = set()

    schema = schema_graph.schema
    for u, v, data in schema.edges(data=True):
        prop = data.get("property", "")
        # Arête sortante d'un nœud interne vers un nœud externe
        if u in internal and v not in internal:
            external_relations.add((prop, v))
        # Arête entrante depuis un nœud externe
        if v in internal and u not in internal:
            external_relations.add((prop, u))

    return len(external_relations)


def compute_diversity(sq: Subgraph) -> float:
    """
    Diversité(S) = |{p | (·, p, ·) ∈ E(S)}| / |E(S)|

    Mesure la richesse relationnelle du motif.
    Retourne 0 si le sous-graphe n'a pas d'arêtes (cas dégénéré).
    """
    edges = sq.edges()
    if not edges:
        return 0.0
    distinct_props = {data.get("property", "") for _, _, data in edges}
    return len(distinct_props) / len(edges)


# ------------------------------------------------------------------
# Score global avec normalisation
# ------------------------------------------------------------------

def compute_importance_scores(
    subgraphs: List[Subgraph],
    schema_graph,
    total_queries: int,
    alpha: float = 0.5,
    beta: float = 0.3,
    gamma: float = 0.2,
) -> List[Tuple[Subgraph, float]]:
    """
    Calcule I(S) pour chaque sous-graphe et retourne une liste triée
    par ordre décroissant de score.

    Normalisation par maximum naturel de chaque composante :
        freq_n  = freq(S) / total_queries          → déjà dans [0, 1]
        ec_n    = EC(S)   / |E(schéma)|            → divisé par le nb total d'arêtes
        div_n   = Div(S)                           → déjà dans [0, 1]

    Paramètres :
        alpha : poids de la fréquence d'usage
        beta  : poids de la connectivité externe
        gamma : poids de la diversité des propriétés
    """
    # Validation des poids
    total = alpha + beta + gamma
    if abs(total - 1.0) > 1e-6:
        raise ValueError(
            f"α + β + γ doit être égal à 1 (reçu : {total:.4f}). "
            "Normalisez vos poids."
        )

    # Maximum naturel pour EC = nombre total d'arêtes dans le schéma
    total_schema_edges = max(schema_graph.schema.number_of_edges(), 1)

    # Normalisation par maximum naturel
    freqs_n   = np.array([compute_frequency(s, total_queries) for s in subgraphs])
    extconns_n = np.array([
        compute_external_connectivity(s, schema_graph) / total_schema_edges
        for s in subgraphs
    ])
    divs_n    = np.array([compute_diversity(s) for s in subgraphs])

    # Score combiné
    scores = alpha * freqs_n + beta * extconns_n + gamma * divs_n

    # Associer score à chaque sous-graphe et trier
    ranked = sorted(
        zip(subgraphs, scores.tolist()),
        key=lambda x: x[1],
        reverse=True,
    )
    return ranked


def print_scores(ranked: List[Tuple[Subgraph, float]]):
    """Affiche les scores de manière lisible."""
    print(f"\n{'='*60}")
    print(f"{'Rang':<5} {'Score':>8}  {'Freq':>5}  Classes / Propriétés")
    print(f"{'='*60}")
    for i, (sq, score) in enumerate(ranked, 1):
        classes_str = ", ".join(
            c.split("/")[-1].split("#")[-1] for c in sorted(sq.classes)
        )
        props_str = ", ".join(
            p.split("/")[-1].split("#")[-1] for p in sorted(sq.properties)
        )
        print(f"{i:<5} {score:>8.4f}  {sq.freq:>5}  [{classes_str}] -- [{props_str}]")
    print(f"{'='*60}\n")
