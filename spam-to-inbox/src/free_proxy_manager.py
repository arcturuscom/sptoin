"""
Gestionnaire de proxies gratuits pour tests locaux
Alternative au proxy manager payant avec rotation automatique
"""
import requests
import json
import time
import random
import threading
from typing import List, Dict, Optional
from logger import get_logger

logger = get_logger(__name__)

class FreeProxyManager:
    """Gestionnaire de proxies gratuits avec rotation et validation"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path or 'config/free_proxies.json')
        self.working_proxies = []
        self.current_proxy_index = 0
        self.proxy_stats = {}
        self.last_fetch_time = 0
        self.fetch_interval = 300  # 5 minutes
        self._lock = threading.Lock()
        
        logger.info("🆓 Gestionnaire proxy gratuit initialisé")
        self._initial_proxy_fetch()
    
    def _load_config(self, config_path: str) -> Dict:
        """Charge la configuration des proxies gratuits"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"✅ Configuration proxy gratuit chargée: {config_path}")
            return config
        except Exception as e:
            logger.error(f"❌ Erreur chargement config: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """Configuration par défaut si fichier absent"""
        return {
            "proxy_type": "free",
            "providers": [],
            "test_settings": {
                "test_url": "https://httpbin.org/ip",
                "timeout": 10,
                "max_retries": 3
            },
            "fallback": {
                "use_no_proxy": True
            }
        }
    
    def _initial_proxy_fetch(self):
        """Récupération initiale des proxies"""
        logger.info("🔄 Récupération initiale des proxies gratuits...")
        
        # Proxies manuels d'abord
        manual_proxies = self._get_manual_proxies()
        if manual_proxies:
            logger.info(f"📝 {len(manual_proxies)} proxies manuels trouvés")
            self.working_proxies.extend(manual_proxies)
        
        # Puis tentative de récupération automatique
        auto_proxies = self._fetch_auto_proxies()
        if auto_proxies:
            logger.info(f"🤖 {len(auto_proxies)} proxies automatiques récupérés")
            self.working_proxies.extend(auto_proxies)
        
        # Test initial des proxies
        if self.working_proxies:
            self._test_all_proxies()
        else:
            logger.warning("⚠️ Aucun proxy trouvé, mode sans proxy activé")
    
    def _get_manual_proxies(self) -> List[Dict]:
        """Récupère les proxies configurés manuellement"""
        proxies = []
        
        for provider in self.config.get('providers', []):
            if provider.get('name') == 'manual_proxies':
                for proxy_info in provider.get('proxies', []):
                    proxy = {
                        'host': proxy_info['host'],
                        'port': proxy_info['port'],
                        'type': proxy_info.get('type', 'http'),
                        'country': proxy_info.get('country', 'Unknown'),
                        'source': 'manual',
                        'working': None,
                        'response_time': None
                    }
                    proxies.append(proxy)
        
        return proxies
    
    def _fetch_auto_proxies(self) -> List[Dict]:
        """Récupère automatiquement des proxies depuis les APIs"""
        proxies = []
        
        for provider in self.config.get('providers', []):
            if not provider.get('auto_fetch', False):
                continue
            
            try:
                logger.info(f"🌐 Récupération depuis {provider['name']}...")
                
                if provider['name'] == 'proxylist.geonode.com':
                    proxies.extend(self._fetch_geonode_proxies(provider))
                elif provider['name'] == 'proxy-list.download':
                    proxies.extend(self._fetch_proxylist_proxies(provider))
                
                # Délai entre les APIs pour éviter les limits
                time.sleep(2)
                
            except Exception as e:
                logger.warning(f"⚠️ Erreur récupération {provider['name']}: {e}")
                continue
        
        return proxies
    
    def _fetch_geonode_proxies(self, provider: Dict) -> List[Dict]:
        """Récupère des proxies depuis l'API Geonode"""
        try:
            response = requests.get(
                provider['url'], 
                timeout=10,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            if response.status_code == 200:
                data = response.json()
                proxies = []
                
                for item in data.get('data', []):
                    proxy = {
                        'host': item.get('ip'),
                        'port': int(item.get('port')),
                        'type': 'http',
                        'country': item.get('country', 'Unknown'),
                        'source': 'geonode',
                        'working': None,
                        'response_time': None
                    }
                    proxies.append(proxy)
                
                logger.info(f"✅ {len(proxies)} proxies récupérés depuis Geonode")
                return proxies
            else:
                logger.warning(f"⚠️ Erreur API Geonode: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Erreur Geonode: {e}")
        
        return []
    
    def _fetch_proxylist_proxies(self, provider: Dict) -> List[Dict]:
        """Récupère des proxies depuis proxy-list.download"""
        try:
            response = requests.get(
                provider['url'], 
                timeout=10,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            if response.status_code == 200:
                proxy_lines = response.text.strip().split('\n')
                proxies = []
                
                for line in proxy_lines[:10]:  # Limite à 10 proxies
                    if ':' in line:
                        host, port = line.strip().split(':')
                        proxy = {
                            'host': host,
                            'port': int(port),
                            'type': 'http',
                            'country': 'Unknown',
                            'source': 'proxy-list.download',
                            'working': None,
                            'response_time': None
                        }
                        proxies.append(proxy)
                
                logger.info(f"✅ {len(proxies)} proxies récupérés depuis proxy-list.download")
                return proxies
            else:
                logger.warning(f"⚠️ Erreur API proxy-list.download: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Erreur proxy-list.download: {e}")
        
        return []
    
    def _test_proxy(self, proxy: Dict) -> bool:
        """Test un proxy individuel"""
        test_url = self.config['test_settings']['test_url']
        timeout = self.config['test_settings']['timeout']
        
        proxy_url = f"http://{proxy['host']}:{proxy['port']}"
        
        try:
            start_time = time.time()
            response = requests.get(
                test_url,
                proxies={'http': proxy_url, 'https': proxy_url},
                timeout=timeout,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                proxy['working'] = True
                proxy['response_time'] = response_time
                proxy['last_tested'] = time.time()
                
                # Vérifier l'anonymat si demandé
                if self.config['test_settings'].get('check_anonymity', False):
                    data = response.json()
                    proxy['detected_ip'] = data.get('origin', 'Unknown')
                
                logger.debug(f"✅ Proxy OK: {proxy['host']}:{proxy['port']} ({response_time:.2f}s)")
                return True
            else:
                proxy['working'] = False
                logger.debug(f"❌ Proxy échec: {proxy['host']}:{proxy['port']} (status: {response.status_code})")
                
        except Exception as e:
            proxy['working'] = False
            proxy['error'] = str(e)
            logger.debug(f"❌ Proxy erreur: {proxy['host']}:{proxy['port']} ({e})")
        
        return False
    
    def _test_all_proxies(self):
        """Test tous les proxies en parallèle (limité)"""
        logger.info("🧪 Test des proxies disponibles...")
        
        working_count = 0
        total_count = len(self.working_proxies)
        
        # Test séquentiel pour éviter de surcharger
        for i, proxy in enumerate(self.working_proxies):
            logger.info(f"🔍 Test proxy {i+1}/{total_count}: {proxy['host']}:{proxy['port']}")
            
            if self._test_proxy(proxy):
                working_count += 1
            
            # Délai entre tests
            time.sleep(0.5)
        
        # Filtrer les proxies fonctionnels
        self.working_proxies = [p for p in self.working_proxies if p.get('working', False)]
        
        logger.info(f"📊 Test terminé: {working_count}/{total_count} proxies fonctionnels")
        
        if working_count == 0:
            logger.warning("⚠️ Aucun proxy fonctionnel trouvé!")
    
    def get_proxy_for_account(self, email: str) -> Dict:
        """
        Récupère un proxy pour un compte (simulation sticky)
        Pour les tests, on fait une rotation simple
        """
        with self._lock:
            # Vérifier si on a des proxies fonctionnels
            if not self.working_proxies:
                if self.config['fallback'].get('use_no_proxy', True):
                    logger.info(f"🔄 Pas de proxy disponible pour {email}, mode direct")
                    return {
                        'host': None,
                        'port': None,
                        'user': None,
                        'pass': None,
                        'type': 'direct',
                        'session_id': f'direct-{hash(email)}',
                        'email': email
                    }
                else:
                    raise Exception("Aucun proxy disponible et mode direct désactivé")
            
            # Sélection du proxy (rotation simple)
            proxy = self.working_proxies[self.current_proxy_index % len(self.working_proxies)]
            self.current_proxy_index += 1
            
            # Simulation session sticky pour les tests
            session_id = f"free-{hash(email + str(time.time()))}_{self.current_proxy_index}"
            
            proxy_config = {
                'host': proxy['host'],
                'port': proxy['port'],
                'user': None,  # Pas d'auth pour proxies gratuits
                'pass': None,
                'type': proxy.get('type', 'http'),
                'session_id': session_id,
                'source': proxy.get('source', 'unknown'),
                'email': email,
                'response_time': proxy.get('response_time', 0)
            }
            
            logger.info(f"🌐 Proxy assigné à {email}: {proxy['host']}:{proxy['port']} (source: {proxy.get('source', 'unknown')})")
            
            return proxy_config
    
    def end_session(self, email: str):
        """Termine une session (pour compatibilité)"""
        logger.debug(f"🔚 Fin session proxy pour {email}")
    
    def get_proxy_stats(self) -> Dict:
        """Statistiques des proxies"""
        working_count = len([p for p in self.working_proxies if p.get('working', False)])
        
        return {
            'total_proxies': len(self.working_proxies),
            'working_proxies': working_count,
            'current_index': self.current_proxy_index,
            'sources': list(set([p.get('source', 'unknown') for p in self.working_proxies])),
            'avg_response_time': self._calculate_avg_response_time()
        }
    
    def _calculate_avg_response_time(self) -> float:
        """Calcule le temps de réponse moyen"""
        times = [p.get('response_time', 0) for p in self.working_proxies if p.get('response_time')]
        return sum(times) / len(times) if times else 0.0
    
    def refresh_proxies(self):
        """Force la actualisation des proxies"""
        logger.info("🔄 Actualisation forcée des proxies...")
        self.working_proxies.clear()
        self.current_proxy_index = 0
        self._initial_proxy_fetch()
    
    @classmethod
    def create_test_instance(cls) -> 'FreeProxyManager':
        """Crée une instance pour les tests"""
        instance = cls.__new__(cls)
        instance.config = instance._get_default_config()
        instance.working_proxies = [
            {
                'host': '127.0.0.1',
                'port': 8080,
                'type': 'http',
                'country': 'Local',
                'source': 'test',
                'working': True,
                'response_time': 0.1
            }
        ]
        instance.current_proxy_index = 0
        instance.proxy_stats = {}
        instance._lock = threading.Lock()
        
        return instance

def test_free_proxy_manager():
    """Test du gestionnaire de proxy gratuit"""
    print("🧪 Test gestionnaire proxy gratuit...")
    
    try:
        # Test avec instance de test
        manager = FreeProxyManager.create_test_instance()
        
        # Test obtention proxy
        proxy = manager.get_proxy_for_account("test@hotmail.com")
        print(f"✅ Proxy obtenu: {proxy}")
        
        # Test statistiques
        stats = manager.get_proxy_stats()
        print(f"✅ Statistiques: {stats}")
        
        # Test fin de session
        manager.end_session("test@hotmail.com")
        print("✅ Fin session OK")
        
        print("✅ Test gestionnaire proxy gratuit passé!")
        return True
        
    except Exception as e:
        print(f"❌ Test échoué: {e}")
        return False

if __name__ == "__main__":
    test_free_proxy_manager()