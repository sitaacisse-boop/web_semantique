"""
visualizer.py
Visualisation du graphe schéma et du résumé produit.
"""

import matplotlib
matplotlib.use("Agg")  # backend non-interactif (fichier PNG)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
from typing import Optional, Set


def draw_graph(
    G: nx.MultiDiGraph,
    title: str = "Graphe",
    highlight_nodes: Optional[Set[str]] = None,
    output_path: Optional[str] = None,
    figsize: tuple = (12, 8),
):
    """
    Dessine un graphe RDF (schéma ou résumé).

    highlight_nodes : nœuds à colorer en orange (nœuds de connexion Steiner)
    output_path     : chemin du fichier PNG de sortie (None = affichage)
    """
    if G.number_of_nodes() == 0:
        print(f"[visualizer] Graphe '{title}' vide, rien à afficher.")
        return

    fig, ax = plt.subplots(figsize=figsize)

    # Layout
    try:
        pos = nx.spring_layout(G, seed=42, k=2.5)
    except Exception:
        pos = nx.circular_layout(G)

    # Couleurs des nœuds
    highlight_nodes = highlight_nodes or set()
    node_colors = []
    for n in G.nodes():
        if n in highlight_nodes:
            node_colors.append("#FFA500")   # orange = nœud de connexion
        else:
            node_colors.append("#4C9BE8")   # bleu = nœud principal

    # Labels courts (partie locale de l'URI)
    labels = {n: n.split("/")[-1].split("#")[-1] for n in G.nodes()}

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=800,
                           alpha=0.9, ax=ax)
    nx.draw_networkx_labels(G, pos, labels, font_size=8, font_color="white",
                            font_weight="bold", ax=ax)

    # Arêtes avec labels de propriétés
    edge_labels = {}
    for u, v, data in G.edges(data=True):
        prop = data.get("property", "")
        prop_short = prop.split("/")[-1].split("#")[-1]
        key = (u, v)
        if key not in edge_labels:
            edge_labels[key] = prop_short
        else:
            edge_labels[key] += f"\n{prop_short}"

    nx.draw_networkx_edges(G, pos, edge_color="#666666", arrows=True,
                           arrowsize=15, width=1.5,
                           connectionstyle="arc3,rad=0.1", ax=ax)
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=7,
                                 font_color="#333333", ax=ax)

    # Légende
    legend_patches = [
        mpatches.Patch(color="#4C9BE8", label="Nœud sélectionné"),
    ]
    if highlight_nodes:
        legend_patches.append(
            mpatches.Patch(color="#FFA500", label="Nœud de connexion (Steiner)")
        )
    ax.legend(handles=legend_patches, loc="upper left", fontsize=9)

    ax.set_title(title, fontsize=13, fontweight="bold", pad=15)
    ax.axis("off")
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"[visualizer] Image sauvegardée : {output_path}")
    else:
        plt.show()
    plt.close()


def compare_schema_vs_summary(schema_graph, summary, output_path=None):
    """Affiche le schéma complet et le résumé côte à côte."""
    fig, axes = plt.subplots(1, 2, figsize=(20, 8))

    def _draw(G, ax, title, color):
        if G.number_of_nodes() == 0:
            ax.text(0.5, 0.5, "Graphe vide", ha="center", va="center")
            ax.set_title(title)
            return
        try:
            pos = nx.spring_layout(G, seed=42, k=2.0)
        except Exception:
            pos = nx.circular_layout(G)
        labels = {n: n.split("/")[-1].split("#")[-1] for n in G.nodes()}
        nx.draw_networkx_nodes(G, pos, node_color=color, node_size=700,
                               alpha=0.85, ax=ax)
        nx.draw_networkx_labels(G, pos, labels, font_size=8,
                                font_color="white", font_weight="bold", ax=ax)
        nx.draw_networkx_edges(G, pos, edge_color="#888", arrows=True,
                               arrowsize=12, ax=ax,
                               connectionstyle="arc3,rad=0.1")
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.axis("off")

    _draw(schema_graph.schema, axes[0],
          f"Schéma complet\n({schema_graph.schema.number_of_nodes()} nœuds, "
          f"{schema_graph.schema.number_of_edges()} arêtes)",
          "#2196F3")
    _draw(summary, axes[1],
          f"Résumé\n({summary.number_of_nodes()} nœuds, "
          f"{summary.number_of_edges()} arêtes)",
          "#4CAF50")

    plt.suptitle("Schéma RDF vs Résumé orienté requêtes", fontsize=14,
                 fontweight="bold", y=1.02)
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"[visualizer] Comparaison sauvegardée : {output_path}")
    else:
        plt.show()
    plt.close()
