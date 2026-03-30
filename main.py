"""
main.py
Point d'entrée du pipeline de résumé RDF orienté requêtes.

Usage :
    python main.py
    python main.py --schema data/sample_schema.ttl --queries data/sample_queries.txt --k 5
"""

import argparse
import os
import sys

# Ajouter le répertoire courant au path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.schema_graph import RDFSchemaGraph
from src.query_parser import SPARQLQueryParser, load_queries
from src.subgraph_builder import SubgraphBuilder
from src.importance import compute_importance_scores, print_scores
from src.summarizer import RDFSummarizer, select_top_k, connect_subgraphs
from src.evaluator import compute_coverage, compute_compactness, print_evaluation
from src.visualizer import draw_graph, compare_schema_vs_summary


def main():
    parser = argparse.ArgumentParser(
        description="Résumé RDF basé sur des sous-graphes orientés requêtes"
    )
    parser.add_argument(
        "--schema", default="data/sample_schema.ttl",
        help="Chemin vers le fichier RDF du schéma (Turtle)"
    )
    parser.add_argument(
        "--queries", default="data/sample_queries.txt",
        help="Chemin vers le fichier de requêtes SPARQL"
    )
    parser.add_argument(
        "--k", type=int, default=4,
        help="Nombre de sous-graphes à sélectionner (top-k)"
    )
    parser.add_argument(
        "--alpha", type=float, default=0.5,
        help="Poids de la fréquence d'usage (défaut: 0.5)"
    )
    parser.add_argument(
        "--beta", type=float, default=0.3,
        help="Poids de la connectivité externe (défaut: 0.3)"
    )
    parser.add_argument(
        "--gamma", type=float, default=0.2,
        help="Poids de la diversité des propriétés (défaut: 0.2)"
    )
    parser.add_argument(
        "--visualize", action="store_true",
        help="Générer des images PNG du schéma et du résumé"
    )
    parser.add_argument(
        "--output-dir", default="output",
        help="Répertoire de sortie pour les images"
    )
    args = parser.parse_args()

    # Validation des poids
    total_weights = args.alpha + args.beta + args.gamma
    if abs(total_weights - 1.0) > 1e-6:
        print(f"Erreur : α + β + γ = {total_weights:.3f} ≠ 1.0")
        print("Conseil : utilisez par exemple --alpha 0.5 --beta 0.3 --gamma 0.2")
        sys.exit(1)

    print("=" * 60)
    print("  Résumé RDF orienté requêtes — Pipeline complet")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Chargement du schéma RDF
    # ------------------------------------------------------------------
    print(f"\n[Schéma] Chargement depuis : {args.schema}")
    schema = RDFSchemaGraph(args.schema, fmt="turtle")
    print(f"         {schema.schema.number_of_nodes()} classe(s), "
          f"{schema.schema.number_of_edges()} propriété(s) dans le schéma")

    # ------------------------------------------------------------------
    # 2. Chargement des requêtes SPARQL
    # ------------------------------------------------------------------
    print(f"\n[Requêtes] Chargement depuis : {args.queries}")
    queries = load_queries(args.queries)
    print(f"           {len(queries)} requête(s) chargée(s)")

    # ------------------------------------------------------------------
    # 3. Exécution du pipeline
    # ------------------------------------------------------------------
    summarizer = RDFSummarizer(schema)
    summary = summarizer.run(
        queries=queries,
        k=args.k,
        alpha=args.alpha,
        beta=args.beta,
        gamma=args.gamma,
        verbose=True,
    )

    # ------------------------------------------------------------------
    # 4. Évaluation
    # ------------------------------------------------------------------
    print("\n[Évaluation]")
    # Reconstruire tous les sous-graphes pour l'évaluation
    parser_obj = SPARQLQueryParser(schema)
    builder = SubgraphBuilder(schema)
    bgps = [parser_obj.extract_bgp(q) for q in queries]
    all_subgraphs = builder.build_all(bgps)

    metrics = compute_coverage(summary, all_subgraphs)
    compactness = compute_compactness(summary, schema)
    print_evaluation(metrics, compactness)

    # ------------------------------------------------------------------
    # 5. Visualisation (optionnelle)
    # ------------------------------------------------------------------
    if args.visualize:
        os.makedirs(args.output_dir, exist_ok=True)
        print(f"\n[Visualisation] Génération des images dans '{args.output_dir}/'...")

        compare_schema_vs_summary(
            schema, summary,
            output_path=os.path.join(args.output_dir, "schema_vs_summary.png")
        )
        draw_graph(
            schema.schema,
            title="Schéma RDF complet",
            output_path=os.path.join(args.output_dir, "schema_full.png")
        )
        draw_graph(
            summary,
            title=f"Résumé RDF (top-{args.k} sous-graphes)",
            output_path=os.path.join(args.output_dir, "summary.png")
        )

    print("\nTerminé.")


if __name__ == "__main__":
    main()
