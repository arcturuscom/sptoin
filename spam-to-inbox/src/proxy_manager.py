"""
Proxy Manager avec sticky sessions OBLIGATOIRES
CRITIQUE: Chaque compte garde la MÊME IP pendant TOUTE sa session
"""
import hashlib
import time
import json
from typing import Dict, Optional
from logger import get_logger

logger = get_logger(__name__)

class ProxyManager:
    """Gestionnaire de proxies avec sticky sessions OBLIGATOIRES"""
    
    def __init__(self, username: str, password: str):
        self.username = username
        self.password = password
        self.active_sessions = {}  # email -> session_id
        self.session_timestamps = {}  # email -> timestamp
        self.session_ips = {}  # session_id -> ip (pour tracking)
        
    def get_proxy_for_account(self, email: str) -> Dict:
        """
        CRITIQUE : Retourne TOUJOURS le même proxy pour un compte
        pendant toute sa session (sticky session)
        """
        # Vérifier si session existe et est valide (< 30 min)
        if email in self.active_sessions:
            age = time.time() - self.session_timestamps[email]
            if age < 1800:  # Session valide 30 minutes
                session_id = self.active_sessions[email]
                logger.info(f"♻️ Réutilisation session {session_id} pour {email}")
            else:
                # Session expirée, libérer l'ancienne et créer une nouvelle
                old_session = self.active_sessions[email]
                logger.info(f"🔄 Session {old_session} expirée pour {email}")
                self._cleanup_session(email)
                session_id = self._create_new_session(email)
        else:
            session_id = self._create_new_session(email)
            logger.info(f"🆕 Nouvelle session {session_id} pour {email}")
        
        # CRUCIAL : Le format avec -session- garde la même IP !
        proxy_config = {
            'host': 'gate.smartproxy.com',
            'port': 10000,
            'user': f'{self.username}-session-{session_id}',
            'pass': self.password,
            'session_id': session_id,
            'type': 'http'
        }
        
        logger.debug(f"🔗 Proxy config pour {email}: {proxy_config['user']}@{proxy_config['host']}:{proxy_config['port']}")
        return proxy_config
    
    def _create_new_session(self, email: str) -> str:
        """Crée une nouvelle session sticky unique"""
        # Utilise email + timestamp + hash pour unicité
        unique_data = f"{email}_{int(time.time() * 1000000)}_{hash(email + str(time.time()))}"
        session_id = hashlib.md5(unique_data.encode()).hexdigest()[:12]  # 12 chars pour plus d'unicité
        
        self.active_sessions[email] = session_id
        self.session_timestamps[email] = time.time()
        
        logger.info(f"✅ Session sticky créée: {session_id} pour {email}")
        return session_id
    
    def _cleanup_session(self, email: str):
        """Nettoie les données de session"""
        if email in self.active_sessions:
            session_id = self.active_sessions[email]
            if session_id in self.session_ips:
                del self.session_ips[session_id]
            del self.active_sessions[email]
            del self.session_timestamps[email]
    
    def end_session(self, email: str):
        """Termine la session pour libérer l'IP"""
        if email in self.active_sessions:
            session_id = self.active_sessions[email]
            logger.info(f"🔚 Fin de session {session_id} pour {email}")
            self._cleanup_session(email)
        else:
            logger.warning(f"⚠️ Tentative de fin de session inexistante pour {email}")
    
    def get_active_sessions(self) -> Dict:
        """Retourne les sessions actives (debug)"""
        return {
            'active_sessions': dict(self.active_sessions),
            'session_count': len(self.active_sessions),
            'oldest_session': min(self.session_timestamps.values()) if self.session_timestamps else None,
            'newest_session': max(self.session_timestamps.values()) if self.session_timestamps else None
        }
    
    def force_cleanup_expired_sessions(self, max_age: int = 1800):
        """Force le nettoyage des sessions expirées"""
        current_time = time.time()
        expired_emails = []
        
        for email, timestamp in self.session_timestamps.items():
            if current_time - timestamp > max_age:
                expired_emails.append(email)
        
        for email in expired_emails:
            logger.info(f"🧹 Nettoyage session expirée pour {email}")
            self.end_session(email)
        
        return len(expired_emails)

    @classmethod
    def from_config(cls, config_path: str) -> 'ProxyManager':
        """Crée un ProxyManager depuis un fichier config"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return cls(
                username=config['username'],
                password=config['password']
            )
        except Exception as e:
            logger.error(f"❌ Erreur chargement config proxy: {e}")
            raise

def test_sticky_sessions():
    """Test simple des sticky sessions"""
    print("🧪 Test des sticky sessions...")
    
    proxy_mgr = ProxyManager("test_user", "test_pass")
    
    # Test 1: Même proxy pour même compte
    email = "test@hotmail.com"
    proxy1 = proxy_mgr.get_proxy_for_account(email)
    proxy2 = proxy_mgr.get_proxy_for_account(email)
    
    assert proxy1['user'] == proxy2['user'], "❌ Session pas sticky!"
    print("✅ Test 1 OK: Session sticky maintenue")
    
    # Test 2: Proxies différents pour comptes différents
    proxy3 = proxy_mgr.get_proxy_for_account("autre@hotmail.com")
    assert proxy1['user'] != proxy3['user'], "❌ Sessions pas séparées!"
    print("✅ Test 2 OK: Sessions séparées par compte")
    
    # Test 3: Fin de session
    proxy_mgr.end_session(email)
    proxy4 = proxy_mgr.get_proxy_for_account(email)
    assert proxy1['user'] != proxy4['user'], "❌ Session pas terminée!"
    print("✅ Test 3 OK: Fin de session fonctionne")
    
    print("✅ Tous les tests sticky sessions passés!")

if __name__ == "__main__":
    test_sticky_sessions()