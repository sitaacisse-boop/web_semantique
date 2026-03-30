"""
evaluator.py
Évaluation du résumé RDF via la métrique de Coverage (Section 7.7).

Coverage = éléments couverts par le résumé / éléments apparaissant dans les requêtes

Un élément est "couvert" s'il figure dans le résumé ET dans les requêtes.
"""

from typing import List, Set, Tuple, Dict
import networkx as nx
try:
    from .subgraph_builder import Subgraph
except ImportError:
    import sys, os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.subgraph_builder import Subgraph


# ------------------------------------------------------------------
# Coverage
# ------------------------------------------------------------------

def compute_coverage(
    summary: nx.MultiDiGraph,
    query_subgraphs: List[Subgraph],
) -> Dict:
    """
    Calcule la métrique de Coverage du résumé.

    Paramètres :
        summary         : graphe résumé (MultiDiGraph)
        query_subgraphs : tous les sous-graphes S_q (avant sélection)

    Retourne un dictionnaire avec :
        - coverage_nodes : proportion de classes couvertes
        - coverage_edges : proportion de propriétés couvertes
        - coverage_global : coverage combinée (nœuds + arêtes)
        - details         : éléments couverts et manquants
    """
    # Éléments dans les requêtes (union de tous les S_q)
    query_nodes: Set[str] = set()
    query_edges: Set[Tuple[str, str, str]] = set()

    for sq in query_subgraphs:
        query_nodes.update(sq.nodes())
        for u, v, data in sq.edges():
            query_edges.add((u, v, data.get("property", "")))

    # Éléments dans le résumé
    summary_nodes = set(summary.nodes())
    summary_edges = set()
    for u, v, data in summary.edges(data=True):
        summary_edges.add((u, v, data.get("property", "")))

    # Intersection
    covered_nodes = query_nodes & summary_nodes
    covered_edges = query_edges & summary_edges

    cov_n = len(covered_nodes) / len(query_nodes) if query_nodes else 0.0
    cov_e = len(covered_edges) / len(query_edges) if query_edges else 0.0

    # Coverage globale = pondération égale nœuds + arêtes
    total_query = len(query_nodes) + len(query_edges)
    total_covered = len(covered_nodes) + len(covered_edges)
    cov_global = total_covered / total_query if total_query > 0 else 0.0

    return {
        "coverage_nodes": cov_n,
        "coverage_edges": cov_e,
        "coverage_global": cov_global,
        "n_query_nodes": len(query_nodes),
        "n_query_edges": len(query_edges),
        "n_covered_nodes": len(covered_nodes),
        "n_covered_edges": len(covered_edges),
        "missing_nodes": query_nodes - summary_nodes,
        "missing_edges": query_edges - summary_edges,
    }


# ------------------------------------------------------------------
# Compacité
# ------------------------------------------------------------------

def compute_compactness(
    summary: nx.MultiDiGraph,
    schema_graph,
) -> float:
    """
    Compacité = 1 - (taille du résumé / taille du schéma complet).
    Un résumé parfaitement compact vaut 1, un résumé = schéma complet vaut 0.
    """
    schema = schema_graph.schema
    total = schema.number_of_nodes() + schema.number_of_edges()
    if total == 0:
        return 1.0
    summary_size = summary.number_of_nodes() + summary.number_of_edges()
    return 1.0 - summary_size / total


# ------------------------------------------------------------------
# Affichage
# ------------------------------------------------------------------

def print_evaluation(metrics: dict, compactness: float = None):
    print("\n" + "=" * 50)
    print("ÉVALUATION DU RÉSUMÉ")
    print("=" * 50)
    print(f"Coverage nœuds  : {metrics['coverage_nodes']:.2%} "
          f"({metrics['n_covered_nodes']}/{metrics['n_query_nodes']})")
    print(f"Coverage arêtes : {metrics['coverage_edges']:.2%} "
          f"({metrics['n_covered_edges']}/{metrics['n_query_edges']})")
    print(f"Coverage globale: {metrics['coverage_global']:.2%}")
    if compactness is not None:
        print(f"Compacité       : {compactness:.2%}")
    if metrics["missing_nodes"]:
        print("\nClasses manquantes :")
        for n in sorted(metrics["missing_nodes"]):
            print(f"  - {n.split('/')[-1].split('#')[-1]}")
    if metrics["missing_edges"]:
        print("\nRelations manquantes :")
        for u, v, p in sorted(metrics["missing_edges"]):
            u_s = u.split("/")[-1].split("#")[-1]
            v_s = v.split("/")[-1].split("#")[-1]
            p_s = p.split("/")[-1].split("#")[-1]
            print(f"  - {u_s} --[{p_s}]--> {v_s}")
    print("=" * 50)
