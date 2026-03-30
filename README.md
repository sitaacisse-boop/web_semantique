# Résumé RDF orienté requêtes — Dataset SWDF

Projet de Web Sémantique — Implémentation d'une approche de résumé de schéma RDF basée sur les logs de requêtes SPARQL.

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
1. Extraction des BGP (Basic Graph Patterns)       [src/query_parser.py]
      ↓
2. Construction des sous-graphes S_q               [src/subgraph_builder.py]
      ↓
3. Calcul des scores I(S) = α·freq_n + β·EC_n + γ·Div_n   [src/importance.py]
      ↓
4. Sélection top-k                                 [src/summarizer.py]
      ↓
5. Connexion via Steiner Tree → Résumé final       [src/summarizer.py]
```

### Formule d'importance

```
I(S) = α × freq_n(S)  +  β × EC_n(S)  +  γ × Div_n(S)
```

| Composante | Calcul | Description |
|---|---|---|
| `freq_n` | `freq(S) / total_requêtes` | Fréquence d'usage normalisée — dans [0,1] |
| `EC_n` | `EC(S) / \|E(schéma)\|` | Connectivité externe normalisée — dans [0,1] |
| `Div_n` | `props_distinctes / \|E(S)\|` | Diversité des propriétés — déjà dans [0,1] |

Paramètres par défaut : **α = 0.5**, **β = 0.3**, **γ = 0.2** (avec α + β + γ = 1)

---

## 📊 Résultats (k=5, α=0.5, β=0.3, γ=0.2)

| Métrique | Valeur | Détail |
|---|---|---|
| Coverage nœuds | 58.3% | 7 classes sur 12 utilisées dans les requêtes |
| Coverage arêtes | 37.5% | 3 relations sur 8 utilisées dans les requêtes |
| Coverage globale | 50.0% | Moyenne nœuds + arêtes |
| Compacité | 61.3% | Le résumé fait 39% de la taille du schéma original |

---

## 🗂️ Structure du projet

```
web_semantique/
├── run.sh              ← Script de lancement (interface menu)
├── app.py              ← Interface Streamlit interactive
├── main.py             ← Pipeline en ligne de commande
├── notebook.ipynb      ← Notebook Jupyter avec résultats complets
├── requirements.txt    ← Dépendances Python
│
├── data/
│   ├── swdf_schema.ttl     ← Schéma RDF réel (SWC ontology)
│   ├── swdf_queries.txt    ← 15 requêtes SPARQL (3 réelles LSQ + 12 réalistes)
│   ├── swdf_queries.log    ← Logs Apache réels (LSQ / data.semanticweb.org)
│   └── swc_ontology.n3     ← Ontologie SWC originale complète
│
└── src/
    ├── schema_graph.py     ← Chargement du schéma RDF dans NetworkX
    ├── query_parser.py     ← Extraction des BGP depuis les requêtes SPARQL
    ├── subgraph_builder.py ← Construction des sous-graphes S_q
    ├── importance.py       ← Calcul des scores I(S)
    ├── summarizer.py       ← Sélection top-k + connexion Steiner Tree
    ├── evaluator.py        ← Métriques Coverage + Compacité
    └── visualizer.py       ← Visualisation des graphes
```

---

## 🚀 Comment tester le projet — Guide complet

### Prérequis

- Python 3.9 ou supérieur
- Git installé

---

### Étape 1 — Cloner le dépôt

```bash
git clone https://github.com/sitaacisse-boop/web_semantique.git
cd web_semantique
```

---

### Étape 2 — Créer l'environnement virtuel et installer les dépendances

```bash
# Créer le venv
python3 -m venv .venv

# Activer le venv
source .venv/bin/activate        # macOS / Linux
# OU
.venv\Scripts\activate           # Windows

# Installer les packages
pip install -r requirements.txt
```

---

### Étape 3 — Choisir comment tester

Il y a **3 façons** de tester le projet :

---

#### Option A — Script interactif (le plus simple)

```bash
bash run.sh
```

Un menu s'affiche :

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

Tapez le chiffre correspondant et appuyez sur Entrée.

---

#### Option B — Interface Streamlit (interface graphique)

```bash
streamlit run app.py
```

Ouvre automatiquement le navigateur sur **http://localhost:8501**

L'interface contient 4 onglets :

| Onglet | Contenu |
|---|---|
| 📊 Schéma | Visualisation du schéma RDF complet avec graphe interactif |
| ⚙️ Pipeline | Lancer le pipeline, voir les scores et les graphes résumés |
| 📈 Évaluation | Métriques Coverage et Compacité avec jauges visuelles |
| 🔬 Analyse | Courbe Coverage vs k, impact des poids α β γ |

**Utilisation :**
1. Dans la barre latérale, ajuster **k** (nombre de sous-graphes) et les **poids α, β**
2. Cliquer **▶ Lancer le pipeline**
3. Explorer les résultats dans les onglets

---

#### Option C — Notebook Jupyter (résultats détaillés)

```bash
jupyter notebook notebook.ipynb
```

Ouvre sur **http://localhost:8888**

- Sélectionner le kernel **Python 3 (ipykernel)**
- Cliquer **Kernel → Restart & Run All**
- Toutes les cellules s'exécutent et affichent les résultats avec graphiques

---

#### Option D — Pipeline ligne de commande

```bash
python main.py \
  --schema  data/swdf_schema.ttl \
  --queries data/swdf_queries.txt \
  --k 5 \
  --alpha 0.5 \
  --beta  0.3 \
  --gamma 0.2 \
  --visualize
```

**Paramètres disponibles :**

| Paramètre | Description | Défaut |
|---|---|---|
| `--schema` | Chemin vers le schéma RDF (.ttl) | `data/swdf_schema.ttl` |
| `--queries` | Chemin vers les requêtes SPARQL (.txt) | `data/swdf_queries.txt` |
| `--k` | Nombre de sous-graphes à sélectionner | `5` |
| `--alpha` | Poids de la fréquence | `0.5` |
| `--beta` | Poids de la connectivité externe | `0.3` |
| `--gamma` | Poids de la diversité | `0.2` |
| `--visualize` | Générer les images dans `output/` | optionnel |

---

### Étape 4 — Vérifier les résultats attendus

Après exécution avec les paramètres par défaut (k=5), vous devez obtenir :

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

## 📦 Dépendances

```
rdflib >= 6.0.0
networkx >= 3.0
numpy >= 1.24
matplotlib >= 3.6
scikit-learn >= 1.2
streamlit >= 1.28
plotly >= 5.0
sparqlwrapper >= 2.0
pyparsing >= 3.0
```
