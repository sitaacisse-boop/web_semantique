# Résumé RDF orienté requêtes — Dataset SWDF

Projet de Web Sémantique — Implémentation de l'approche proposée en **Section 7** du rapport : résumé de schéma RDF basé sur des sous-graphes orientés requêtes.

---

## 1. Contexte général

Les graphes de connaissances RDF (*RDF Knowledge Graphs*) représentent des connaissances structurées sous forme de triplets *(sujet, prédicat, objet)*. Leur taille et complexité rendent leur compréhension difficile, en particulier pour la formulation de requêtes SPARQL.

Trois familles d'approches ont été étudiées dans le rapport :

1. Une approche **orientée requêtes** fondée sur des **propriétés logiques**
2. Une approche **structurelle** basée sur des **centralités** et l'**apprentissage automatique**
3. Une approche basée sur des **représentations vectorielles** (*embeddings*)

---

## 2. État de l'art — Articles étudiés

### Article 1 — Query-Oriented Summarization (Čebirić et al., 2015)

**Objectif** : définir un bon résumé RDF du point de vue des requêtes SPARQL — garantir que le résumé préserve correctement les capacités de réponse aux requêtes.

**Deux propriétés fondamentales** :
- **Représentativité** : toute requête ayant une réponse sur le graphe original doit en avoir une sur le résumé
- **Précision** : toute requête correspondant au résumé doit pouvoir l'être sur au moins un graphe original correspondant

**Deux types de résumés** :
- *Baseline summary* : basé sur les propriétés structurelles (règles DNT1-DNT4), complexité O(G²)
- *Refined summary* : plus précis mais complexité O(G⁵)

**Limite** : évaluation exclusivement théorique, pas de comparaison quantitative.

---

### Article 2 — SumMER : Structural Summarization (Troullinou et al., 2023)

**Objectif** : produire un résumé structurel lisible en sélectionnant les concepts les plus importants du schéma (top-k).

**Méthode** :
1. Extraction du schéma RDF
2. Calcul de **8 mesures de centralité** (PageRank, Degree, Betweenness, HITS...)
3. Ajout du **nombre d'instances** comme caractéristique
4. Apprentissage d'un **modèle de régression supervisée** à partir des logs SPARQL
5. Sélection des top-k classes les plus importantes
6. Connexion via une **approximation du Steiner Tree**

**Évaluation** : empirique et quantitative sur des graphes réels (DBpedia, SWDF), mesurée par la *coverage*.

**Caractéristiques** : approche structurelle, notion explicite d'importance, sélection node-centric, machine learning.

---

### Article 3 — Constructing Semantic Summaries Using Embeddings (Pappas et al., 2024)

**Objectif** : améliorer la scalabilité et la qualité sémantique des résumés RDF en exploitant des représentations vectorielles apprises automatiquement.

**Méthode** :
1. Génération d'**embeddings RDF2Vec** (marches aléatoires + Word2Vec Skip-gram)
2. Apprentissage supervisé de l'importance des nœuds et arêtes :
   - Pour les nœuds : `f_node : embedding(v) → I_node(v)` (Decision Tree Regressor)
   - Pour les arêtes : `f_edge : embedding(e) → I_edge(e)` (Support Vector Regressor)
3. Sélection des **top-k nœuds** les plus importants
4. Connexion via **SDIST** (Steiner Tree pondéré par les embeddings)

**Caractéristiques** : forte scalabilité, meilleure coverage, cohérence sémantique, mais interprétabilité plus limitée.

---

## 3. Analyse comparative des approches

| Critère | Query-Oriented | SumMER | Embeddings |
|---|---|---|---|
| Orientation | Usage | Structure | Sémantique + Usage |
| Importance explicite | Non | Oui (centralités) | Oui (apprise) |
| Pondération des arêtes | Non | Non | Oui |
| Scalabilité | Faible | Moyenne | Élevée |
| Coverage | Moyenne | Bonne | Meilleure |
| Interprétabilité | Élevée | Élevée | Plus limitée |

**Observation clé** (Section 6 du rapport) : ces approches sélectionnent principalement des éléments isolés (nœuds ou arêtes), alors que les requêtes SPARQL expriment des **motifs structuraux impliquant plusieurs éléments simultanément**. C'est le point de départ de notre approche.

---

## 4. Notre approche — Section 7

### Motivation

L'unité naturelle d'usage d'un graphe RDF n'est pas le nœud isolé, mais le **sous-graphe correspondant aux motifs de requêtes (BGP)**. Nous proposons donc une méthode centrée sur des **sous-graphes orientés requêtes**.

### Définitions

Soit un graphe RDF G = (V, E) :
- V : ensemble des nœuds (classes ou entités)
- E : ensemble des arêtes (propriétés RDF)

Un **Basic Graph Pattern (BGP)** est un ensemble de triplets RDF exprimant un besoin informationnel utilisateur.

Un **sous-graphe orienté requête** S_q est le sous-graphe du schéma RDF induit par les classes et propriétés apparaissant dans un BGP donné q.

### Pipeline — 5 étapes

```
Requêtes SPARQL
      ↓
1. Extraction des BGP                              [src/query_parser.py]
      ↓
2. Construction des sous-graphes S_q               [src/subgraph_builder.py]
      ↓
3. Calcul des scores I(S)                          [src/importance.py]
      ↓
4. Sélection top-k                                 [src/summarizer.py]
      ↓
5. Connexion via Steiner Tree → Résumé final       [src/summarizer.py]
```

### Formule d'importance (Section 7.4)

```
I(S) = α · freq(S)  +  β · ExternalConnectivity(S)  +  γ · Diversité(S)
```

| Composante | Définition formelle | Normalisation |
|---|---|---|
| `freq(S)` | Nombre d'occurrences du motif dans Q | `freq / total_requêtes` → [0,1] |
| `ExternalConnectivity(S)` | `\|{(p,u) \| u ∉ V(S), ∃v ∈ V(S), (v,p,u) ∈ E}\|` | `EC / \|E(schéma)\|` → [0,1] |
| `Diversité(S)` | `\|{p \| (·,p,·) ∈ E(S)}\| / \|E(S)\|` | Déjà dans [0,1] |

Paramètres par défaut : **α = 0.5**, **β = 0.3**, **γ = 0.2** (avec α + β + γ = 1)

> **Choix de normalisation** : on divise chaque composante par son **maximum naturel absolu** (et non par le min-max de l'ensemble), pour éviter les instabilités quand toutes les valeurs sont égales.

### Métrique d'évaluation (Section 7.7)

```
Coverage = éléments couverts par le résumé / éléments apparaissant dans les requêtes
```

Un bon résumé doit : couvrir un maximum de requêtes, rester compact, et préserver la cohérence structurelle.

---

## 5. Dataset utilisé

| Fichier | Source | Description |
|---|---|---|
| `data/swdf_schema.ttl` | [LOV](https://lov.linkeddata.es) | Ontologie SWC 2009 — 18 classes, 13 propriétés |
| `data/swdf_queries.txt` | [LSQ](https://aksw.org/Projects/LSQ.html) | 15 requêtes SPARQL (3 réelles + 12 réalistes) |
| `data/swdf_queries.log` | LSQ / data.semanticweb.org | Logs Apache réels (Mai 2014) |
| `data/swc_ontology.n3` | LOV | Ontologie SWC complète originale |

---

## 6. Résultats (k=5, α=0.5, β=0.3, γ=0.2)

```
Rang  Score   freq_n   EC_n    Div_n   Classes
1     0.4179  0.0667  0.6154  1.0000  AcademicEvent, ConferenceEvent, Person
2     0.4179  0.0667  0.6154  1.0000  AcademicEvent, SessionEvent, TalkEvent
3     0.4179  0.0667  0.6154  1.0000  AcademicEvent, ConferenceEvent, PanelEvent
4     0.4179  0.0667  0.6154  1.0000  AcademicEvent, ConferenceEvent, TalkEvent
5     0.3949  0.0667  0.5385  1.0000  AcademicEvent, Programme

Résumé final : 7 nœuds, 5 arêtes
```

| Métrique | Valeur | Détail |
|---|---|---|
| Coverage nœuds | 58.3% | 7 classes sur 12 utilisées dans les requêtes |
| Coverage arêtes | 37.5% | 3 relations sur 8 utilisées dans les requêtes |
| Coverage globale | 50.0% | Moyenne nœuds + arêtes |
| Compacité | 61.3% | Le résumé fait 39% de la taille du schéma original |

---

## 7. Interface graphique

L'interface Streamlit permet de manipuler le pipeline en temps réel :

![Interface Streamlit](https://github.com/sitaacisse-boop/web_semantique/raw/main/docs/interface.png)

L'interface contient 4 onglets :

| Onglet | Contenu |
|---|---|
| 📊 Schéma | Graphe interactif du schéma SWDF complet (18 classes, 13 propriétés) |
| ⚙️ Pipeline | Scores I(S), tableau des sous-graphes, graphes schéma vs résumé |
| 📈 Évaluation | Jauges Coverage et Compacité, éléments manquants |
| 🔬 Analyse | Courbe Coverage vs k, impact des poids α β γ |

---

## 8. Structure du projet

```
web_semantique/
├── run.sh              ← Script de lancement (menu interactif)
├── app.py              ← Interface Streamlit interactive
├── main.py             ← Pipeline en ligne de commande
├── notebook.ipynb      ← Notebook Jupyter avec résultats et graphiques
├── requirements.txt    ← Dépendances Python
│
├── data/
│   ├── swdf_schema.ttl     ← Schéma RDF réel (SWC ontology)
│   ├── swdf_queries.txt    ← 15 requêtes SPARQL
│   ├── swdf_queries.log    ← Logs Apache réels (LSQ)
│   └── swc_ontology.n3     ← Ontologie SWC originale complète
│
└── src/
    ├── schema_graph.py     ← Chargement du schéma RDF dans NetworkX
    ├── query_parser.py     ← Extraction des BGP (Section 7.3)
    ├── subgraph_builder.py ← Construction des sous-graphes S_q
    ├── importance.py       ← Calcul des scores I(S) (Section 7.4)
    ├── summarizer.py       ← Sélection top-k + Steiner Tree (Sections 7.5-7.6)
    ├── evaluator.py        ← Métrique Coverage (Section 7.7)
    └── visualizer.py       ← Visualisation des graphes
```

---

## 9. Comment tester le projet

### Prérequis
- Python 3.9 ou supérieur
- Git installé

### Étape 1 — Cloner le dépôt

```bash
git clone https://github.com/sitaacisse-boop/web_semantique.git
cd web_semantique
```

### Étape 2 — Créer l'environnement et installer les dépendances

```bash
# Créer le venv
python3 -m venv .venv

# Activer le venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows

# Installer les packages
pip install -r requirements.txt
```

### Étape 3 — Lancer (choisir une option)

#### Option A — Script interactif (le plus simple)

```bash
bash run.sh
```

```
╔══════════════════════════════════════════╗
║   Résumé RDF orienté requêtes — SWDF    ║
╚══════════════════════════════════════════╝

  1 — Interface Streamlit   (recommandé)
  2 — Notebook Jupyter
  3 — Pipeline ligne de commande
  4 — Tout installer / vérifier
  0 — Quitter
```

#### Option B — Interface Streamlit

```bash
streamlit run app.py
```
→ Ouvre **http://localhost:8501** dans le navigateur

#### Option C — Notebook Jupyter

```bash
jupyter notebook notebook.ipynb
```
→ Ouvre **http://localhost:8888** — sélectionner **Python 3 (ipykernel)** puis **Kernel → Restart & Run All**

#### Option D — Pipeline ligne de commande

```bash
python main.py \
  --schema  data/swdf_schema.ttl \
  --queries data/swdf_queries.txt \
  --k 5 --alpha 0.5 --beta 0.3 --gamma 0.2 \
  --visualize
```

| Paramètre | Description | Défaut |
|---|---|---|
| `--k` | Nombre de sous-graphes à sélectionner | `5` |
| `--alpha` | Poids de la fréquence | `0.5` |
| `--beta` | Poids de la connectivité externe | `0.3` |
| `--gamma` | Poids de la diversité | `0.2` |
| `--visualize` | Générer les images dans `output/` | optionnel |

### Étape 4 — Vérifier les résultats attendus

```
[Schéma]   18 classe(s), 13 propriété(s)
[Requêtes] 15 requête(s) chargée(s)
[Parsing]  14 motif(s) distinct(s) identifié(s)

Rang  Score   Classes
1     0.4179  AcademicEvent, ConferenceEvent, Person
2     0.4179  AcademicEvent, SessionEvent, TalkEvent
3     0.4179  AcademicEvent, ConferenceEvent, PanelEvent
4     0.4179  AcademicEvent, ConferenceEvent, TalkEvent
5     0.3949  AcademicEvent, Programme

Résumé final : 7 nœud(s), 5 arête(s)

Coverage nœuds  : 58.33% (7/12)
Coverage arêtes : 37.50% (3/8)
Coverage globale: 50.00%
Compacité       : 61.29%
```

---

## 10. Dépendances

```
rdflib >= 6.0.0        # Manipulation des graphes RDF
networkx >= 3.0        # Algorithmes de graphes (Steiner Tree)
numpy >= 1.24          # Calculs numériques
matplotlib >= 3.6      # Visualisation (notebook)
scikit-learn >= 1.2    # Normalisation
streamlit >= 1.28      # Interface web interactive
plotly >= 5.0          # Graphes interactifs
sparqlwrapper >= 2.0   # Requêtes SPARQL
pyparsing >= 3.0       # Parsing SPARQL
```

---

## 11. Références

- Čebirić et al. (2015). *Query-Oriented Summarization of RDF Graphs*
- Troullinou et al. (2023). *SumMER: Structural Summarization for RDF/S Knowledge Graphs*
- Pappas et al. (2024). *Constructing Semantic Summaries Using Embeddings*
