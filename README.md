# Résumé RDF orienté requêtes — Dataset SWDF

Projet de Web Sémantique — Implémentation d'une approche de résumé de schéma RDF basée sur les logs de requêtes SPARQL.

## 🌐 Interface interactive en ligne

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://web-semantique-swdf.streamlit.app)

> Cliquez sur le badge ci-dessus pour accéder à l'interface sans aucune installation.

---

## 📋 Description du projet

Ce projet implémente une approche de **résumé de schéma RDF orienté requêtes** :

- Au lieu de résumer le schéma de façon statique, on analyse les **logs de requêtes SPARQL réelles**
- On identifie les parties du schéma les plus utilisées via les **BGP (Basic Graph Patterns)**
- On produit un résumé compact et représentatif via un **Steiner Tree**

### Dataset utilisé
- **Schéma** : Ontologie SWC (Semantic Web Conference) — téléchargée depuis [LOV](https://lov.linkeddata.es)
- **Requêtes** : Logs réels du serveur `data.semanticweb.org` (Mai 2014) via le projet [LSQ](https://aksw.org/Projects/LSQ.html)

---

## ⚙️ Pipeline — 5 étapes

```
Requêtes SPARQL
      ↓
1. Extraction des BGP (Basic Graph Patterns)
      ↓
2. Construction des sous-graphes S_q
      ↓
3. Calcul des scores I(S) = α·freq_n + β·EC_n + γ·Div_n
      ↓
4. Sélection top-k
      ↓
5. Connexion via Steiner Tree → Résumé final
```

### Formule d'importance

$$I(S) = \alpha \cdot \text{freq\_n}(S) + \beta \cdot \text{EC\_n}(S) + \gamma \cdot \text{Div\_n}(S)$$

| Composante | Calcul | Description |
|---|---|---|
| freq_n | freq / total_requêtes | Fréquence d'usage normalisée |
| EC_n | EC / \|E(schéma)\| | Connectivité externe normalisée |
| Div_n | props_distinctes / \|E(S)\| | Diversité des propriétés |

---

## 📊 Résultats (k=5, α=0.5, β=0.3, γ=0.2)

| Métrique | Valeur |
|---|---|
| Coverage nœuds | 58.3% (7/12) |
| Coverage arêtes | 37.5% (3/8) |
| Coverage globale | 50.0% |
| Compacité | 61.3% |

---

## 🗂️ Structure du projet

```
websemantique/
├── app.py              ← Interface Streamlit interactive
├── main.py             ← Pipeline en ligne de commande
├── notebook.ipynb      ← Notebook Jupyter avec résultats complets
├── requirements.txt    ← Dépendances Python
│
├── data/
│   ├── swdf_schema.ttl     ← Schéma RDF réel (SWC ontology)
│   ├── swdf_queries.txt    ← 15 requêtes SPARQL
│   └── swdf_queries.log    ← Logs Apache réels (LSQ)
│
└── src/
    ├── schema_graph.py     ← Chargement du schéma RDF
    ├── query_parser.py     ← Extraction des BGP
    ├── subgraph_builder.py ← Construction des S_q
    ├── importance.py       ← Calcul I(S)
    ├── summarizer.py       ← Sélection top-k + Steiner Tree
    ├── evaluator.py        ← Coverage + Compacité
    └── visualizer.py       ← Visualisation
```

---

## 🚀 Lancer localement

```bash
# Cloner le dépôt
git clone https://github.com/amiraben09/web_semantique-.git
cd web_semantique-

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'interface Streamlit
streamlit run app.py

# Ou lancer le pipeline en ligne de commande
python main.py --schema data/swdf_schema.ttl --queries data/swdf_queries.txt --k 5

# Ou ouvrir le notebook
jupyter notebook notebook.ipynb
```

---

## 📦 Dépendances

```
rdflib
networkx
numpy
matplotlib
scikit-learn
streamlit
plotly
sparqlwrapper
```
