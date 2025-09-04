"""
Processeur d'emails avec connexion IMAP et gestion proxy
Gère la connexion sécurisée et le déplacement des emails spam
"""
import imaplib
import socket
import socks
import email
import time
import ssl
from typing import List, Dict, Optional, Tuple
import re
from logger import get_logger
from client_simulator import EmailClient

logger = get_logger(__name__)

class EmailProcessor:
    """Processeur principal pour les opérations IMAP"""
    
    def __init__(self, proxy_config: Dict, client: EmailClient):
        self.proxy_config = proxy_config
        self.client = client
        self.imap_conn = None
        self.connected = False
        
    def connect(self, email_addr: str, password: str, use_app_password: bool = False) -> bool:
        """
        Connexion IMAP avec proxy sticky et simulation client
        CRITIQUE: Utilise le même proxy pour toute la session
        """
        try:
            logger.info(f"🔌 Connexion IMAP pour {email_addr} via {self.client.name}")
            
            # Configuration proxy SOCKS5
            if self.proxy_config:
                self._setup_proxy_connection()
            
            # Connexion IMAP SSL
            self.imap_conn = imaplib.IMAP4_SSL(
                host='outlook.office365.com',
                port=993,
                ssl_context=self._get_ssl_context()
            )
            
            # Authentification
            auth_result = self._authenticate(email_addr, password, use_app_password)
            if not auth_result:
                return False
            
            # Commandes d'initialisation spécifiques au client
            self._execute_client_init_commands()
            
            self.connected = True
            logger.info(f"✅ Connexion IMAP réussie pour {email_addr}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur connexion IMAP {email_addr}: {e}")
            self.connected = False
            return False
    
    def _setup_proxy_connection(self):
        """Configure la connexion proxy SOCKS5 avec sticky session"""
        try:
            # Configuration SOCKS5 pour imaplib
            socks.set_default_proxy(
                socks.SOCKS5,
                self.proxy_config['host'],
                self.proxy_config['port'],
                username=self.proxy_config['user'],
                password=self.proxy_config['pass']
            )
            
            # Monkey patch socket pour utiliser SOCKS
            socket.socket = socks.socksocket
            
            logger.debug(f"🌐 Proxy configuré: {self.proxy_config['user']}@{self.proxy_config['host']}")
            
        except Exception as e:
            logger.error(f"❌ Erreur configuration proxy: {e}")
            raise
    
    def _get_ssl_context(self) -> ssl.SSLContext:
        """Crée un contexte SSL sécurisé"""
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        return context
    
    def _authenticate(self, email_addr: str, password: str, use_app_password: bool) -> bool:
        """Authentification IMAP avec gestion des mots de passe d'application"""
        try:
            if use_app_password:
                logger.info(f"🔐 Authentification avec mot de passe d'application")
            
            # Tentative de connexion
            result = self.imap_conn.login(email_addr, password)
            
            if result[0] == 'OK':
                logger.info(f"✅ Authentification réussie pour {email_addr}")
                return True
            else:
                logger.error(f"❌ Échec authentification: {result[1]}")
                return False
                
        except imaplib.IMAP4.error as e:
            error_msg = str(e).lower()
            if 'authentication failed' in error_msg:
                logger.error(f"❌ Échec authentification pour {email_addr}")
                if not use_app_password:
                    logger.info("💡 Tentez avec un mot de passe d'application si 2FA activé")
            else:
                logger.error(f"❌ Erreur IMAP: {e}")
            return False
    
    def _execute_client_init_commands(self):
        """Exécute les commandes d'initialisation spécifiques au client"""
        commands = self.client.get_imap_commands()
        
        for cmd in commands:
            try:
                if cmd.startswith('ID'):
                    # Commande ID spéciale
                    result = self.imap_conn._simple_command('ID', cmd[3:])
                    logger.debug(f"📝 Commande ID exécutée: {result}")
                else:
                    # Autres commandes
                    result = self.imap_conn._simple_command(cmd)
                    logger.debug(f"📝 Commande {cmd} exécutée: {result}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Commande {cmd} échouée: {e}")
                # Continue même si certaines commandes échouent
    
    def get_spam_emails(self, limit: int = 50) -> List[Dict]:
        """
        Récupère les emails du dossier spam
        Retourne une liste de dictionnaires avec métadonnées
        """
        if not self.connected or not self.imap_conn:
            logger.error("❌ Pas de connexion IMAP active")
            return []
        
        try:
            # Sélection du dossier spam (nom selon le client)
            spam_folder = self.client.get_folder_names()['spam']
            logger.info(f"📂 Sélection dossier spam: {spam_folder}")
            
            result = self.imap_conn.select(spam_folder, readonly=False)
            if result[0] != 'OK':
                logger.error(f"❌ Impossible de sélectionner {spam_folder}: {result[1]}")
                return []
            
            # Recherche emails
            search_pattern = self.client.get_search_pattern()
            result = self.imap_conn.search(None, search_pattern)
            
            if result[0] != 'OK':
                logger.error(f"❌ Erreur recherche emails: {result[1]}")
                return []
            
            email_ids = result[1][0].decode().split()
            
            if not email_ids or email_ids == ['']:
                logger.info("📭 Aucun email dans le dossier spam")
                return []
            
            # Limiter le nombre d'emails
            if len(email_ids) > limit:
                logger.info(f"📊 Limitation à {limit} emails sur {len(email_ids)} trouvés")
                email_ids = email_ids[-limit:]  # Prendre les plus récents
            
            logger.info(f"📧 {len(email_ids)} emails spam trouvés")
            
            # Récupération métadonnées
            emails = self._fetch_email_metadata(email_ids)
            
            return emails
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération spam: {e}")
            return []
    
    def _fetch_email_metadata(self, email_ids: List[str]) -> List[Dict]:
        """Récupère les métadonnées des emails"""
        emails = []
        
        for email_id in email_ids:
            try:
                # Récupération headers principaux
                result = self.imap_conn.fetch(email_id, '(ENVELOPE INTERNALDATE RFC822.SIZE FLAGS)')
                
                if result[0] != 'OK':
                    logger.warning(f"⚠️ Impossible de récupérer email {email_id}")
                    continue
                
                # Parse des données
                email_data = {
                    'id': email_id,
                    'raw_data': result[1][0],
                    'size': self._extract_size_from_response(result[1][0]),
                    'flags': self._extract_flags_from_response(result[1][0])
                }
                
                emails.append(email_data)
                
                # Délai anti-détection
                time.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"⚠️ Erreur récupération email {email_id}: {e}")
                continue
        
        logger.info(f"📊 {len(emails)} emails métadonnées récupérées")
        return emails
    
    def _extract_size_from_response(self, response) -> int:
        """Extrait la taille d'un email depuis la réponse IMAP"""
        try:
            response_str = str(response)
            size_match = re.search(r'RFC822\.SIZE (\d+)', response_str)
            return int(size_match.group(1)) if size_match else 0
        except:
            return 0
    
    def _extract_flags_from_response(self, response) -> List[str]:
        """Extrait les flags d'un email depuis la réponse IMAP"""
        try:
            response_str = str(response)
            flags_match = re.search(r'FLAGS \(([^)]+)\)', response_str)
            if flags_match:
                return flags_match.group(1).split()
            return []
        except:
            return []
    
    def move_emails_to_inbox(self, emails: List[Dict]) -> Tuple[int, int]:
        """
        Déplace les emails vers la boîte de réception
        Retourne (succès, échecs)
        """
        if not self.connected or not self.imap_conn:
            logger.error("❌ Pas de connexion IMAP active")
            return 0, len(emails)
        
        if not emails:
            logger.info("📭 Aucun email à déplacer")
            return 0, 0
        
        try:
            inbox_folder = self.client.get_folder_names()['inbox']
            success_count = 0
            fail_count = 0
            
            logger.info(f"📤 Déplacement de {len(emails)} emails vers {inbox_folder}")
            
            for email_data in emails:
                try:
                    email_id = email_data['id']
                    
                    # Copie vers inbox
                    copy_result = self.imap_conn.copy(email_id, inbox_folder)
                    
                    if copy_result[0] == 'OK':
                        # Marquer comme supprimé du spam
                        self.imap_conn.store(email_id, '+FLAGS', '\\Deleted')
                        success_count += 1
                        logger.debug(f"✅ Email {email_id} déplacé vers inbox")
                    else:
                        fail_count += 1
                        logger.warning(f"⚠️ Échec déplacement email {email_id}: {copy_result[1]}")
                    
                    # Délai anti-détection entre chaque email
                    time.sleep(0.2)
                    
                except Exception as e:
                    fail_count += 1
                    logger.error(f"❌ Erreur déplacement email {email_data.get('id', '?')}: {e}")
            
            # Expunge pour finaliser les suppressions
            if success_count > 0:
                self.imap_conn.expunge()
                logger.info(f"🗑️ Nettoyage effectué - {success_count} emails supprimés du spam")
            
            logger.info(f"📊 Résultat: {success_count} déplacés, {fail_count} échecs")
            return success_count, fail_count
            
        except Exception as e:
            logger.error(f"❌ Erreur générale déplacement: {e}")
            return 0, len(emails)
    
    def get_folder_list(self) -> List[str]:
        """Liste les dossiers disponibles"""
        if not self.connected or not self.imap_conn:
            return []
        
        try:
            result = self.imap_conn.list()
            if result[0] == 'OK':
                folders = []
                for folder_info in result[1]:
                    folder_name = folder_info.decode().split('"')[-2]
                    folders.append(folder_name)
                return folders
            return []
        except Exception as e:
            logger.error(f"❌ Erreur liste dossiers: {e}")
            return []
    
    def disconnect(self):
        """Ferme la connexion IMAP proprement"""
        try:
            if self.imap_conn:
                self.imap_conn.close()
                self.imap_conn.logout()
                logger.info("🔌 Déconnexion IMAP propre")
            self.connected = False
        except Exception as e:
            logger.warning(f"⚠️ Erreur lors de la déconnexion: {e}")
        finally:
            self.imap_conn = None
            self.connected = False
    
    def __enter__(self):
        """Support context manager"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Support context manager"""
        self.disconnect()

def test_email_processor():
    """Test simple du processeur email"""
    print("🧪 Test processeur email...")
    
    from client_simulator import ClientSimulator
    
    simulator = ClientSimulator()
    client = simulator.get_client_by_name("Outlook Desktop Windows")
    
    proxy_config = {
        'host': 'test.proxy.com',
        'port': 1080,
        'user': 'test-session-abc123',
        'pass': 'testpass'
    }
    
    processor = EmailProcessor(proxy_config, client)
    
    print(f"✅ Processeur créé avec client: {client.name}")
    print("⚠️ Test connexion nécessite vraies credentials")
    print("✅ Test processeur email basique passé!")

if __name__ == "__main__":
    test_email_processor()