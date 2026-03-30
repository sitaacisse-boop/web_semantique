#!/bin/bash
# ─────────────────────────────────────────────
#  run.sh — Lancer le projet Web Sémantique
#  Usage : bash run.sh
# ─────────────────────────────────────────────

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$PROJECT_DIR/.venv/bin/python"
PIP="$PROJECT_DIR/.venv/bin/pip"
STREAMLIT="$PROJECT_DIR/.venv/bin/streamlit"
JUPYTER="$PROJECT_DIR/.venv/bin/jupyter"

cd "$PROJECT_DIR"

# Couleurs
RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'
YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

echo ""
echo -e "${BLUE}╔══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Résumé RDF orienté requêtes — SWDF    ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Vérifier le venv ──
if [ ! -f "$VENV" ]; then
    echo -e "${RED}✗ Environnement Python non trouvé.${NC}"
    echo -e "${YELLOW}→ Création du venv et installation des packages...${NC}"
    python3 -m venv .venv
    $PIP install -q -r requirements.txt
    echo -e "${GREEN}✓ Packages installés.${NC}"
fi

# ── Menu ──
echo -e "${CYAN}Que voulez-vous lancer ?${NC}"
echo ""
echo -e "  ${GREEN}1${NC} — Interface Streamlit   (recommandé)"
echo -e "  ${GREEN}2${NC} — Notebook Jupyter"
echo -e "  ${GREEN}3${NC} — Pipeline ligne de commande"
echo -e "  ${GREEN}4${NC} — Tout installer / vérifier"
echo -e "  ${GREEN}0${NC} — Quitter"
echo ""
read -p "Votre choix : " CHOIX

case $CHOIX in

  1)
    echo ""
    echo -e "${GREEN}▶ Lancement de l'interface Streamlit...${NC}"
    echo -e "${CYAN}→ Ouvre ton navigateur sur : http://localhost:8501${NC}"
    echo -e "${YELLOW}   (Ctrl+C pour arrêter)${NC}"
    echo ""
    $STREAMLIT run app.py
    ;;

  2)
    echo ""
    echo -e "${GREEN}▶ Lancement de Jupyter Notebook...${NC}"
    echo -e "${CYAN}→ Ouvre ton navigateur sur : http://localhost:8888${NC}"
    echo -e "${YELLOW}   (Ctrl+C pour arrêter)${NC}"
    echo ""
    $JUPYTER notebook notebook.ipynb
    ;;

  3)
    echo ""
    echo -e "${GREEN}▶ Exécution du pipeline...${NC}"
    echo ""
    read -p "  Valeur de k (défaut: 5) : " K
    K=${K:-5}
    read -p "  α (défaut: 0.5) : " ALPHA
    ALPHA=${ALPHA:-0.5}
    read -p "  β (défaut: 0.3) : " BETA
    BETA=${BETA:-0.3}
    GAMMA=$(echo "1 - $ALPHA - $BETA" | bc)
    echo ""
    echo -e "${CYAN}  Paramètres : k=$K  α=$ALPHA  β=$BETA  γ=$GAMMA${NC}"
    echo ""
    $VENV main.py \
      --schema  data/swdf_schema.ttl \
      --queries data/swdf_queries.txt \
      --k       $K \
      --alpha   $ALPHA \
      --beta    $BETA \
      --gamma   $GAMMA \
      --visualize
    ;;

  4)
    echo ""
    echo -e "${YELLOW}▶ Vérification et installation des packages...${NC}"
    $PIP install -q -r requirements.txt
    echo ""
    $VENV -c "
import rdflib, networkx, numpy, matplotlib, sklearn, streamlit, plotly
print('✓ rdflib      :', rdflib.__version__)
print('✓ networkx    :', networkx.__version__)
print('✓ numpy       :', numpy.__version__)
print('✓ matplotlib  :', matplotlib.__version__)
print('✓ sklearn     :', sklearn.__version__)
print('✓ streamlit   :', streamlit.__version__)
print('✓ plotly      :', plotly.__version__)
print()
print('Tout est OK ✓')
"
    ;;

  0)
    echo -e "${YELLOW}Au revoir.${NC}"
    exit 0
    ;;

  *)
    echo -e "${RED}Choix invalide.${NC}"
    exit 1
    ;;

esac
