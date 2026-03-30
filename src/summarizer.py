"""
summarizer.py
Pipeline principal du résumé RDF basé sur des sous-graphes orientés requêtes.

Algorithme (Section 7) :
    1. Extraction des BGP depuis les requêtes SPARQL
    2. Construction des sous-graphes S_q
    3. Calcul des scores d'importance I(S)
    4. Sélection des top-k sous-graphes
    5. Connexion via approximation du Steiner Tree
    6. Retour du résumé final
"""

from typing import List, Tuple, Optional
import sys, os
import networkx as nx

try:
    from .subgraph_builder import Subgraph
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.subgraph_builder import Subgraph


# ------------------------------------------------------------------
# Sélection top-k
# ------------------------------------------------------------------

def select_top_k(
    ranked: List[Tuple[Subgraph, float]],
    k: int,
) -> List[Subgraph]:
    """
    Retourne les k sous-graphes avec les meilleurs scores.
    Si k > len(ranked), retourne tous les sous-graphes disponibles.
    """
    k = min(k, len(ranked))
    return [sq for sq, _ in ranked[:k]]


# ------------------------------------------------------------------
# Connexion via Steiner Tree (adaptation aux sous-graphes)
# ------------------------------------------------------------------

def connect_subgraphs(
    selected: List[Subgraph],
    schema_graph,
) -> nx.MultiDiGraph:
    """
    Connecte les sous-graphes sélectionnés pour former un résumé connexe.

    Adaptation du Steiner Tree aux sous-graphes :
    - Terminaux = tous les nœuds appartenant aux sous-graphes sélectionnés
    - On cherche un sous-graphe connexe minimal du schéma couvrant ces terminaux
    - Approximation : MST sur le graphe métrique des terminaux (2-approx classique)

    Retourne le graphe de résumé final (MultiDiGraph).
    """
    if not selected:
        return nx.MultiDiGraph()

    # Graphe non-dirigé du schéma (pour les chemins)
    undirected = schema_graph.as_undirected()

    # Ensemble des nœuds terminaux (union de tous les sous-graphes sélectionnés)
    terminals = set()
    for sq in selected:
        terminals.update(sq.nodes())

    terminals = {t for t in terminals if t in undirected.nodes()}

    if len(terminals) <= 1:
        return _build_final_summary(selected, set(), schema_graph)

    # --- Approximation 2-approx du Steiner Tree ---
    steiner_nodes = _steiner_tree_approx(undirected, terminals)

    return _build_final_summary(selected, steiner_nodes, schema_graph)


def _steiner_tree_approx(G: nx.Graph, terminals: set) -> set:
    """
    Approximation du Steiner Tree (ratio 2(1 - 1/|terminaux|)) :

    1. Construire le graphe de distance entre terminaux (closure métrique)
    2. Trouver l'MST de ce graphe
    3. Remplacer chaque arête abstraite par le chemin dans G
    4. Supprimer les feuilles non-terminales (élagage)
    """
    terminal_list = list(terminals)
    n = len(terminal_list)

    if n == 0:
        return set()
    if n == 1:
        return set(terminal_list)

    # Étape 1 : Plus courts chemins entre toutes les paires de terminaux
    paths = {}
    metric_graph = nx.Graph()
    metric_graph.add_nodes_from(terminal_list)

    for i in range(n):
        for j in range(i + 1, n):
            t1, t2 = terminal_list[i], terminal_list[j]
            try:
                length = nx.shortest_path_length(G, t1, t2)
                path = nx.shortest_path(G, t1, t2)
                paths[(t1, t2)] = path
                paths[(t2, t1)] = path[::-1]
                metric_graph.add_edge(t1, t2, weight=length)
            except nx.NetworkXNoPath:
                pass  # terminaux non connectés

    if metric_graph.number_of_edges() == 0:
        return terminals

    # Étape 2 : MST du graphe métrique
    mst = nx.minimum_spanning_tree(metric_graph, weight="weight")

    # Étape 3 : Reconstruction des chemins dans G
    steiner_nodes = set()
    for u, v in mst.edges():
        path = paths.get((u, v)) or paths.get((v, u))
        if path:
            steiner_nodes.update(path)

    # Étape 4 : Élagage des feuilles non-terminales
    steiner_nodes = _prune_non_terminal_leaves(steiner_nodes, terminals, G)

    return steiner_nodes


def _prune_non_terminal_leaves(
    nodes: set, terminals: set, G: nx.Graph
) -> set:
    """
    Supprime itérativement les feuilles du Steiner Tree qui ne sont pas des terminaux.
    """
    result = set(nodes)
    changed = True
    while changed:
        changed = False
        subg = G.subgraph(result)
        leaves = {n for n in subg.nodes() if subg.degree(n) == 1}
        non_terminal_leaves = leaves - terminals
        if non_terminal_leaves:
            result -= non_terminal_leaves
            changed = True
    return result


# ------------------------------------------------------------------
# Construction du graphe résumé final
# ------------------------------------------------------------------

def _build_final_summary(
    selected: List[Subgraph],
    steiner_nodes: set,
    schema_graph,
) -> nx.MultiDiGraph:
    """
    Construit le MultiDiGraph final = union(sous-graphes sélectionnés)
    augmenté des nœuds et arêtes de connexion (Steiner Tree).
    """
    summary = nx.MultiDiGraph()
    schema = schema_graph.schema

    # Ajouter les nœuds et arêtes des sous-graphes sélectionnés
    for sq in selected:
        for n, data in sq.graph.nodes(data=True):
            summary.add_node(n, **data)
        for u, v, key, data in sq.graph.edges(keys=True, data=True):
            summary.add_edge(u, v, key=key, **data)

    # Ajouter les nœuds/arêtes de connexion du Steiner Tree
    all_nodes = set(summary.nodes()) | steiner_nodes
    for n in steiner_nodes:
        if n not in summary and n in schema.nodes():
            summary.add_node(n, **schema.nodes[n])

    # Ajouter les arêtes du schéma entre les nœuds du résumé
    for u, v, key, data in schema.edges(keys=True, data=True):
        if u in all_nodes and v in all_nodes and not summary.has_edge(u, v, key):
            summary.add_edge(u, v, key=key, **data)

    return summary


# ------------------------------------------------------------------
# Pipeline complet
# ------------------------------------------------------------------

class RDFSummarizer:
    """
    Orchestre le pipeline complet de résumé RDF orienté requêtes.

    Usage :
        summarizer = RDFSummarizer(schema_graph)
        summary = summarizer.run(queries, k=5, alpha=0.5, beta=0.3, gamma=0.2)
    """

    def __init__(self, schema_graph):
        try:
            from .query_parser import SPARQLQueryParser
            from .subgraph_builder import SubgraphBuilder
            from .importance import compute_importance_scores
        except ImportError:
            from src.query_parser import SPARQLQueryParser
            from src.subgraph_builder import SubgraphBuilder
            from src.importance import compute_importance_scores

        self.schema = schema_graph
        self.parser = SPARQLQueryParser(schema_graph)
        self.builder = SubgraphBuilder(schema_graph)
        self._compute_scores = compute_importance_scores

    def run(
        self,
        queries: List[str],
        k: int = 5,
        alpha: float = 0.5,
        beta: float = 0.3,
        gamma: float = 0.2,
        verbose: bool = True,
    ) -> nx.MultiDiGraph:
        """
        Exécute le pipeline complet.

        Retourne le graphe de résumé final.
        """
        total = len(queries)
        if verbose:
            print(f"[1/5] Parsing de {total} requête(s)...")

        # Étape 1 : Extraction des BGP
        bgps = [self.parser.extract_bgp(q) for q in queries]

        if verbose:
            print(f"[2/5] Construction des sous-graphes S_q...")

        # Étape 2 : Construction des sous-graphes
        subgraphs = self.builder.build_all(bgps)
        if verbose:
            print(f"       → {len(subgraphs)} motif(s) distinct(s) identifié(s)")

        if not subgraphs:
            print("Aucun sous-graphe valide. Vérifiez les requêtes et le schéma.")
            return nx.MultiDiGraph()

        if verbose:
            print(f"[3/5] Calcul des scores d'importance (α={alpha}, β={beta}, γ={gamma})...")

        # Étape 3 : Scores d'importance
        ranked = self._compute_scores(
            subgraphs, self.schema, total, alpha, beta, gamma
        )

        if verbose:
            try:
                from .importance import print_scores
            except ImportError:
                from src.importance import print_scores
            print_scores(ranked)

        # Étape 4 : Sélection top-k
        k_eff = min(k, len(ranked))
        if verbose:
            print(f"[4/5] Sélection des top-{k_eff} sous-graphes...")
        selected = select_top_k(ranked, k_eff)

        if verbose:
            print(f"[5/5] Connexion via approximation du Steiner Tree...")

        # Étape 5 : Connexion
        summary = connect_subgraphs(selected, self.schema)

        if verbose:
            print(f"\nRésumé final : {summary.number_of_nodes()} nœud(s), "
                  f"{summary.number_of_edges()} arête(s)")

        return summary
