#!/bin/bash

# Script de lancement Spam-to-Inbox
# Automatise le démarrage avec vérifications préalables

set -e  # Arrêt sur erreur

# Couleurs pour output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variables
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src"
CONFIG_DIR="$SCRIPT_DIR/config"
LOGS_DIR="$SCRIPT_DIR/logs"

echo -e "${BLUE}🚀 Spam-to-Inbox Launcher${NC}"
echo "================================"

# Vérification Python
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo -e "${RED}❌ Python non trouvé. Installez Python 3.7+${NC}"
        exit 1
    fi
    PYTHON_CMD="python"
else
    PYTHON_CMD="python3"
fi

echo -e "${GREEN}✅ Python trouvé: $($PYTHON_CMD --version)${NC}"

# Vérification des dépendances
echo -e "${BLUE}📦 Vérification des dépendances...${NC}"
if ! $PYTHON_CMD -c "import imaplib, socks, colorlog" &> /dev/null; then
    echo -e "${YELLOW}⚠️  Installation des dépendances...${NC}"
    $PYTHON_CMD -m pip install -r "$SCRIPT_DIR/requirements.txt"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Échec installation dépendances${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Dépendances OK${NC}"

# Création des répertoires nécessaires
mkdir -p "$LOGS_DIR"
mkdir -p "$CONFIG_DIR"

# Vérification fichiers configuration
if [ ! -f "$CONFIG_DIR/accounts.csv" ]; then
    echo -e "${YELLOW}⚠️  Fichier accounts.csv manquant${NC}"
    if [ -f "$CONFIG_DIR/accounts.csv.example" ]; then
        echo -e "${BLUE}📄 Copie du fichier exemple...${NC}"
        cp "$CONFIG_DIR/accounts.csv.example" "$CONFIG_DIR/accounts.csv"
        echo -e "${RED}❗ IMPORTANT: Éditez config/accounts.csv avec vos vrais comptes${NC}"
        echo -e "${BLUE}   nano $CONFIG_DIR/accounts.csv${NC}"
    else
        echo -e "${RED}❌ Aucun exemple trouvé pour accounts.csv${NC}"
        exit 1
    fi
fi

if [ ! -f "$CONFIG_DIR/proxies.json" ]; then
    echo -e "${YELLOW}⚠️  Fichier proxies.json manquant${NC}"
    if [ -f "$CONFIG_DIR/proxies.json.example" ]; then
        echo -e "${BLUE}📄 Copie du fichier exemple...${NC}"
        cp "$CONFIG_DIR/proxies.json.example" "$CONFIG_DIR/proxies.json"
        echo -e "${RED}❗ IMPORTANT: Éditez config/proxies.json avec vos vrais identifiants${NC}"
        echo -e "${BLUE}   nano $CONFIG_DIR/proxies.json${NC}"
    else
        echo -e "${RED}❌ Aucun exemple trouvé pour proxies.json${NC}"
        exit 1
    fi
fi

# Vérification contenu configuration
if grep -q "sp_your_username" "$CONFIG_DIR/proxies.json" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Configuration proxy non modifiée (identifiants exemple détectés)${NC}"
    echo -e "${BLUE}   Éditez $CONFIG_DIR/proxies.json avant de continuer${NC}"
fi

if grep -q "password123" "$CONFIG_DIR/accounts.csv" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Configuration comptes non modifiée (mots de passe exemple détectés)${NC}"
    echo -e "${BLUE}   Éditez $CONFIG_DIR/accounts.csv avant de continuer${NC}"
fi

echo -e "${GREEN}✅ Configuration trouvée${NC}"

# Parse des arguments
DRY_RUN=""
MAX_EMAILS=""
LOG_LEVEL="INFO"
FILTER=""
EXTRA_ARGS=""

# Options de lancement
echo ""
echo -e "${BLUE}📋 Options de lancement disponibles:${NC}"
echo "1) Test de configuration seulement"
echo "2) Mode dry-run (test sans modifications)"
echo "3) Traitement standard"
echo "4) Traitement avec options personnalisées"
echo "5) Mode debug (logs détaillés)"

read -p "Choisissez une option (1-5): " choice

case $choice in
    1)
        echo -e "${BLUE}🧪 Test de configuration...${NC}"
        EXTRA_ARGS="--test-config"
        ;;
    2)
        echo -e "${BLUE}🧪 Mode dry-run activé${NC}"
        read -p "Nombre max d'emails par compte (défaut: 10): " max_emails
        max_emails=${max_emails:-10}
        EXTRA_ARGS="--dry-run --max-emails $max_emails"
        ;;
    3)
        echo -e "${BLUE}🚀 Traitement standard${NC}"
        read -p "Nombre max d'emails par compte (défaut: 50): " max_emails
        max_emails=${max_emails:-50}
        EXTRA_ARGS="--max-emails $max_emails"
        ;;
    4)
        echo -e "${BLUE}⚙️  Configuration personnalisée${NC}"
        read -p "Nombre max d'emails (défaut: 50): " max_emails
        read -p "Filtre comptes (optionnel): " filter
        read -p "Dry-run? (y/N): " dry_run
        
        max_emails=${max_emails:-50}
        EXTRA_ARGS="--max-emails $max_emails"
        
        if [ ! -z "$filter" ]; then
            EXTRA_ARGS="$EXTRA_ARGS --filter \"$filter\""
        fi
        
        if [[ $dry_run =~ ^[Yy]$ ]]; then
            EXTRA_ARGS="$EXTRA_ARGS --dry-run"
        fi
        ;;
    5)
        echo -e "${BLUE}🔧 Mode debug activé${NC}"
        EXTRA_ARGS="--log-level DEBUG --max-emails 5"
        ;;
    *)
        echo -e "${RED}❌ Option invalide${NC}"
        exit 1
        ;;
esac

# Message de sécurité
if [[ ! $EXTRA_ARGS =~ --dry-run ]] && [[ ! $EXTRA_ARGS =~ --test-config ]]; then
    echo ""
    echo -e "${YELLOW}⚠️  ATTENTION: Mode de traitement réel sélectionné${NC}"
    echo -e "${YELLOW}   Les emails seront réellement déplacés de spam vers inbox${NC}"
    read -p "Continuer? (y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        echo -e "${BLUE}🛑 Annulé par l'utilisateur${NC}"
        exit 0
    fi
fi

# Lancement du script principal
echo ""
echo -e "${GREEN}🚀 Lancement du processeur...${NC}"
echo -e "${BLUE}Command: $PYTHON_CMD $SRC_DIR/main.py $EXTRA_ARGS${NC}"
echo ""

cd "$SCRIPT_DIR"

# Fonction de nettoyage en cas d'interruption
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 Interruption détectée, nettoyage...${NC}"
    # Ici on pourrait ajouter du nettoyage spécifique
    exit 130
}

# Trap pour nettoyage propre
trap cleanup INT TERM

# Lancement avec gestion d'erreur
eval "$PYTHON_CMD $SRC_DIR/main.py $EXTRA_ARGS"
exit_code=$?

# Message de fin
echo ""
if [ $exit_code -eq 0 ]; then
    echo -e "${GREEN}✅ Traitement terminé avec succès!${NC}"
else
    echo -e "${RED}❌ Traitement terminé avec erreurs (code: $exit_code)${NC}"
    echo -e "${BLUE}💡 Consultez les logs dans $LOGS_DIR/${NC}"
fi

# Affichage des logs récents si erreur
if [ $exit_code -ne 0 ] && [ -f "$LOGS_DIR/spam-to-inbox.log" ]; then
    echo ""
    echo -e "${BLUE}📋 Dernières lignes de log:${NC}"
    echo "------------------------"
    tail -10 "$LOGS_DIR/spam-to-inbox.log"
fi

exit $exit_code