# 🆓 Guide d'Utilisation avec Proxies Gratuits

**Configuration et tests avec des proxies gratuits pour vos tests locaux**

## 🎯 Pourquoi utiliser des proxies gratuits ?

✅ **Tests locaux** sans frais  
✅ **Validation du code** avant investissement proxy payant  
✅ **Apprentissage** du système de rotation  
✅ **Développement** et debugging  

## 🚀 Installation et Configuration Rapide

### 1. **Préparation des fichiers de test**

```bash
cd spam-to-inbox

# Copier la configuration de test
cp config/test_accounts.csv config/accounts.csv

# Éditer avec VOS VRAIS comptes email
nano config/accounts.csv
```

**IMPORTANT** : Remplacez par vos vrais identifiants Hotmail/Outlook :
```csv
email,password,app_password
votre_email@hotmail.com,votre_mot_de_passe,
autre@outlook.com,autre_password,mot_passe_app_si_2fa
```

### 2. **Test des proxies gratuits disponibles**

```bash
# Test des proxies prédéfinis
python test_free_proxies.py --test-manual

# Test d'un proxy specific
python test_free_proxies.py --test-single 51.158.68.133 8811

# Récupération automatique et test
python test_free_proxies.py --test-auto
```

Exemple de sortie :
```
🧪 Test de la liste prédéfinie de proxies...
📋 10 proxies à tester
✅ 51.158.68.133:8811 (2.34s)
❌ 144.217.7.124:5566
✅ 20.111.54.16:8123 (1.87s)
...
📊 Résultats: 3/10 proxies fonctionnels
✅ Configuration sauvegardée: config/working_proxies.json
```

### 3. **Tests avec la version proxy gratuit**

```bash
# Test des proxies gratuits seulement
python src/main_free_proxy.py --test-free-proxies

# Test d'un seul compte avec proxy gratuit
python src/main_free_proxy.py --test-single-account votre_email@hotmail.com

# Test sans proxy (connexion directe)
python src/main_free_proxy.py --no-proxy --test-single-account votre_email@hotmail.com
```

## 📋 Étapes de Test Recommandées

### **Phase 1 : Validation Proxies**
```bash
# 1. Tester les proxies disponibles
python test_free_proxies.py --test-manual --save-working config/working_proxies.json

# 2. Vérifier qu'au moins 1 proxy fonctionne
python src/main_free_proxy.py --test-free-proxies
```

### **Phase 2 : Test Sans Proxy** (Plus Sûr pour débuter)
```bash
# 1. Test connexion directe d'abord
python src/main_free_proxy.py --no-proxy --test-single-account votre_email@hotmail.com

# 2. Vérifier les logs
tail -f logs/spam-to-inbox.log
```

### **Phase 3 : Test Avec Proxy Gratuit**
```bash
# 1. Test avec proxy (simulation seulement)
python src/main_free_proxy.py --test-single-account votre_email@hotmail.com --max-emails 3

# 2. Si succès, actualiser les proxies
python src/main_free_proxy.py --refresh-proxies
```

## 🔧 Configuration des Proxies Gratuits

Le fichier `config/free_proxies.json` contient :

### **Sources Automatiques**
- **proxy-list.download** : Liste de proxies HTTP élite
- **proxylist.geonode.com** : API avec format JSON
- **Rotation automatique** : Changement après erreurs

### **Proxies Manuels Testés**
```json
{
  "name": "manual_proxies",
  "proxies": [
    {"host": "51.158.68.133", "port": 8811, "country": "FR"},
    {"host": "20.111.54.16", "port": 8123, "country": "US"},
    {"host": "144.217.7.124", "port": 5566, "country": "CA"}
  ]
}
```

### **Paramètres de Test**
- **Timeout** : 10 secondes
- **URL de test** : httpbin.org/ip
- **Vérification anonymat** : Activée
- **Fallback** : Connexion directe si aucun proxy

## 🚨 Limitations des Proxies Gratuits

### ⚠️ **Points d'Attention**
- **Fiabilité variable** : Proxies peuvent tomber
- **Vitesse limitée** : Plus lents que proxies payants  
- **Pas de sticky sessions** : Rotation simple
- **Anonymat partiel** : Moins sécurisé
- **Détection possible** : Par les serveurs email

### ✅ **Solutions de Contournement**
- **Mode sans proxy** pour tests initiaux
- **Rotation fréquente** des proxies
- **Fallback automatique** vers connexion directe
- **Tests préalables** de tous les proxies

## 📊 Exemple de Session de Test

```bash
# 1. Préparation
cd spam-to-inbox
cp config/test_accounts.csv config/accounts.csv
# Éditer config/accounts.csv avec vos vrais comptes

# 2. Test proxies
python test_free_proxies.py --test-manual
# ✅ 3/10 proxies fonctionnels trouvés

# 3. Test connectivité
python src/main_free_proxy.py --test-free-proxies
# ✅ Proxies gratuits fonctionnels trouvés!
# 📊 Statistiques: {'working_proxies': 3, 'sources': ['manual']}

# 4. Test d'un compte
python src/main_free_proxy.py --test-single-account votre@hotmail.com
# 🧪 TEST compte: votre@hotmail.com
# 🌐 Proxy assigné: {'host': '51.158.68.133', 'port': 8811}
# 📧 Simulation: 3 emails spam trouvés
# ✅ Simulation terminée: 3 emails 'déplacés'
```

## 🔄 Migration vers Proxies Payants

Une fois vos tests validés avec les proxies gratuits :

### **1. Obtenir SmartProxy (Recommandé)**
- Compte SmartProxy avec sticky sessions
- Format : `username-session-{id}`
- IPs stables et fiables

### **2. Configurer proxies.json**
```json
{
  "provider": "smartproxy",
  "username": "sp_votre_username",
  "password": "votre_password"
}
```

### **3. Utiliser la version principale**
```bash
# Au lieu de main_free_proxy.py
python src/main.py --test-config

# Puis traitement réel
python src/main.py --max-emails 25
```

## 🛠️ Dépannage Proxies Gratuits

### **Aucun proxy ne fonctionne**
```bash
# Test connexion directe
python src/main_free_proxy.py --no-proxy --test-single-account votre@hotmail.com

# Actualiser la liste
python src/main_free_proxy.py --refresh-proxies

# Test manuel d'un proxy spécifique  
python test_free_proxies.py --test-single 51.158.68.133 8811
```

### **Proxies lents**
```bash
# Logs debug pour diagnostic
python src/main_free_proxy.py --test-single-account votre@hotmail.com --log-level DEBUG

# Vérifier les temps de réponse
python test_free_proxies.py --test-manual
```

### **Erreurs de connexion email**
```bash
# Vérifier d'abord sans proxy
python src/main_free_proxy.py --no-proxy --test-single-account votre@hotmail.com

# Si OK sans proxy = problème de proxy
# Si KO sans proxy = problème credentials email
```

---

## 🎉 Prêt pour vos Tests !

Vous avez maintenant un système complet pour tester avec des proxies gratuits :

✅ **Outils de test** des proxies  
✅ **Version spécialisée** pour proxies gratuits  
✅ **Mode fallback** sans proxy  
✅ **Configuration flexible** et logs détaillés  

**Commencez par les tests sans proxy, puis intégrez progressivement les proxies gratuits !**