# 📧 Spam-to-Inbox Automation

**Projet Python complet pour automatiser le déplacement d'emails spam vers inbox pour des comptes Hotmail/Outlook avec protection anti-détection maximale.**

## 🎯 Caractéristiques Critiques

### ✅ **Sticky Sessions (ESSENTIEL)**
- Chaque compte garde la **MÊME IP** pendant toute sa session
- Format SmartProxy : `username-session-{unique_session_id}`
- Jamais de changement d'IP entre connexion et déconnexion
- Sessions automatiquement gérées et nettoyées

### 🎭 **Anti-Détection Avancée**
- **5 clients email différents** simulés (Outlook Desktop, Web, Mobile, Thunderbird, Apple Mail)
- **Comportement humain réaliste** avec délais variables et pauses
- **Fatigue progressive** qui influence les temps de traitement
- **Distractions occasionnelles** (5% du temps)
- **Patterns de lecture** adaptatifs selon l'heure

### 🔒 **Sécurité et Fiabilité**
- Support mots de passe d'application (2FA)
- Connexions IMAP SSL sécurisées
- Gestion d'erreurs complète
- Logs détaillés avec rotation automatique
- Mode dry-run pour tests

## 📁 Structure du Projet

```
spam-to-inbox/
├── src/
│   ├── __init__.py              # Package principal
│   ├── main.py                  # Point d'entrée avec argparse
│   ├── proxy_manager.py         # 🔑 CRITIQUE: Sticky sessions
│   ├── email_processor.py       # Connexion IMAP et traitement
│   ├── client_simulator.py      # Simulation 5 clients email
│   ├── anti_detection.py        # Comportement humain
│   └── logger.py               # Système de logs
├── config/
│   ├── accounts.csv.example    # Exemple comptes
│   └── proxies.json.example    # Exemple configuration proxy
├── tests/
│   └── test_proxy.py           # Tests sticky sessions
├── requirements.txt            # Dépendances Python
├── .env.example               # Variables environnement
├── README.md                  # Documentation
└── run.sh                     # Script de lancement
```

## 🚀 Installation Rapide

1. **Cloner et installer**
```bash
cd spam-to-inbox
pip install -r requirements.txt
```

2. **Configuration**
```bash
# Copier les exemples
cp config/accounts.csv.example config/accounts.csv
cp config/proxies.json.example config/proxies.json
cp .env.example .env

# Éditer avec vos credentials
nano config/accounts.csv
nano config/proxies.json
```

3. **Configuration accounts.csv**
```csv
email,password,app_password
user1@hotmail.com,password123,
user2@outlook.com,password456,app_pwd_if_2fa
```

4. **Configuration proxies.json**
```json
{
  "provider": "smartproxy",
  "username": "sp_your_username",
  "password": "your_proxy_password",
  "sticky_sessions": true,
  "session_duration": 30
}
```

## 📋 Utilisation

### **Commandes Principales**

```bash
# Test de configuration
python src/main.py --test-config

# Traitement standard
python src/main.py

# Mode dry-run (test sans modifications)
python src/main.py --dry-run

# Limite d'emails et filtre
python src/main.py --max-emails 25 --filter "hotmail"

# Mode debug avec logs détaillés
python src/main.py --log-level DEBUG
```

### **Options Avancées**

```bash
python src/main.py \
    --accounts custom/accounts.csv \
    --proxies custom/proxies.json \
    --max-emails 100 \
    --log-level INFO \
    --cleanup-logs
```

## 🔧 Workflow Technique

### **1. Sticky Sessions (CRITIQUE)**
```python
# CHAQUE compte obtient sa propre session sticky
proxy = proxy_manager.get_proxy_for_account(email)
# Format: username-session-abc123def

# TOUTES les opérations utilisent CE MÊME proxy
imap = connect_imap(email, password, proxy)
emails = get_spam_emails(imap, proxy)      # MÊME proxy
move_emails(imap, emails, proxy)           # MÊME proxy
imap.logout()                              # MÊME proxy

# Fin de session libère l'IP
proxy_manager.end_session(email)
```

### **2. Simulation de Clients**
- **Outlook Desktop Windows** (35%) - Headers Microsoft spécifiques
- **Outlook Web** (25%) - User-agent navigateur
- **Outlook Mobile iOS** (20%) - Headers mobile
- **Thunderbird** (15%) - Client open source
- **Apple Mail** (5%) - Client Apple

### **3. Comportement Humain**
```python
# Délais basés sur taille email
delay = calculate_reading_delay(email_size, complexity)

# Pauses aléatoires
if should_take_break():
    duration = take_human_break()  # 2-120 secondes

# Fatigue progressive
fatigue_level += action_weight
delay *= (1 + fatigue_level * 0.5)
```

## 📊 Logs et Monitoring

### **Structure des Logs**
```
logs/
├── spam-to-inbox.log          # Log principal
├── proxy.log                  # Sessions sticky
├── email.log                  # Opérations IMAP
├── behavior.log               # Comportement humain
└── client.log                 # Simulation clients
```

### **Exemples de Logs**
```
🚀 SESSION START | Email: user@hotmail.com | Client: Outlook Desktop | Proxy: session-abc123
📧 MOVE | 15 emails | Junk → Inbox
🧠 read_email | Délai: 3.2s
🔚 Fin de session session-abc123 pour user@hotmail.com
📊 RÉSUMÉ SESSION: 15 emails déplacés, 0 erreurs, 95.2s
```

## ⚙️ Configuration Serveurs IMAP

### **Hotmail/Outlook/Live**
- **Serveur**: `outlook.office365.com`
- **Port**: `993` (SSL)
- **Dossier spam**: `Junk` (ou `Junk E-mail` selon client)
- **Support**: @hotmail.com, @outlook.com, @live.com, @msn.com

## 🧪 Tests et Validation

### **Test Sticky Sessions**
```bash
python src/proxy_manager.py
# ✅ Test 1 OK: Session sticky maintenue
# ✅ Test 2 OK: Sessions séparées par compte  
# ✅ Test 3 OK: Fin de session fonctionne
```

### **Test Configuration Complète**
```bash
python src/main.py --test-config
# ✅ Proxy test: sp_user-session-abc123@gate.smartproxy.com
# ✅ Client test: Outlook Desktop Windows
# ✅ Comportement test: délai 2.34s
```

## 🔒 Sécurité et Bonnes Pratiques

### **Mots de Passe d'Application**
Pour les comptes avec 2FA activé :
1. Générer un mot de passe d'application dans les paramètres Outlook
2. Utiliser ce mot de passe dans la colonne `app_password`
3. Le script détectera automatiquement et utilisera ce mot de passe

### **Gestion des Erreurs**
- Authentification échouée → Suggère mot de passe d'application
- Connexion proxy échouée → Retry automatique
- Session expirée → Renouvellement automatique
- Dossier introuvable → Adaptation selon le client

### **Limitations de Taux**
- Délais minimums entre emails (0.2s)
- Pauses entre comptes (8-15s)
- Sessions limitées à 30 minutes
- Nettoyage automatique des sessions expirées

## 🚨 Points Critiques

### ❌ **À NE JAMAIS FAIRE**
- Changer de proxy pendant une session
- Ignorer les délais anti-détection
- Traiter trop d'emails simultanément
- Utiliser des délais fixes (non aléatoires)

### ✅ **Bonnes Pratiques**
- Toujours tester avec `--dry-run` d'abord
- Surveiller les logs pour détecter les problèmes
- Utiliser `--max-emails` raisonnable (50 max)
- Nettoyer les logs régulièrement avec `--cleanup-logs`

## 📈 Statistiques et Monitoring

Le script fournit des statistiques détaillées :
- Comptes traités avec succès
- Nombre total d'emails déplacés
- Taux de réussite par compte
- Sessions proxy uniques utilisées
- Durée totale de traitement
- Erreurs rencontrées

## 🔧 Dépannage

### **Proxy ne fonctionne pas**
1. Vérifier credentials dans `proxies.json`
2. Tester connectivité : `ping gate.smartproxy.com`
3. Vérifier format sticky : `username-session-xxxx`

### **Authentification échouée**
1. Vérifier mot de passe dans `accounts.csv`
2. Générer mot de passe d'application si 2FA
3. Vérifier domaine email supporté

### **Emails non trouvés**
1. Vérifier nom dossier spam selon le client
2. Tester avec `--log-level DEBUG`
3. Vérifier permissions IMAP du compte

---

**🔑 RAPPEL CRITIQUE** : Les sticky sessions sont ESSENTIELLES pour éviter la détection. Ne jamais modifier le format `username-session-{id}` qui garantit la même IP pour toute la session d'un compte.