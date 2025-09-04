#!/usr/bin/env python3
"""
VERSION DE TEST avec proxies gratuits
Point d'entrée adapté pour utiliser des proxies gratuits au lieu de SmartProxy
"""
import argparse
import csv
import json
import time
import random
import os
import sys
from typing import List, Dict, Tuple
from datetime import datetime

# Imports modules locaux
from free_proxy_manager import FreeProxyManager  # Au lieu de ProxyManager
from client_simulator import ClientSimulator
from email_processor import EmailProcessor
from anti_detection import HumanBehaviorSimulator
from logger import (setup_logging, get_logger, log_session_start, 
                   log_session_end, log_error_with_context, 
                   create_session_summary, cleanup_old_logs)

class SpamToInboxFreeProxyProcessor:
    """Version de test avec proxies gratuits"""
    
    def __init__(self, config_dir: str = 'config', log_level: str = 'INFO'):
        self.config_dir = config_dir
        self.logger = setup_logging(log_level)
        
        # Composants principaux (version proxy gratuit)
        self.proxy_manager = None
        self.client_simulator = ClientSimulator()
        self.behavior_simulator = HumanBehaviorSimulator()
        
        # Statistiques session
        self.stats = {
            'accounts_processed': 0,
            'emails_moved': 0,
            'errors': 0,
            'unique_sessions': set(),
            'start_time': time.time(),
            'duration': 0,
            'success_rate': 0.0
        }
        
        self.logger.info("🆓 Spam-to-Inbox Processor (Proxy Gratuit) initialisé")
    
    def load_configuration(self, accounts_file: str = None, free_proxies: bool = True) -> bool:
        """Charge la configuration pour proxies gratuits"""
        try:
            # Fichier comptes par défaut
            if not accounts_file:
                accounts_file = os.path.join(self.config_dir, 'accounts.csv')
            
            # Vérification existence fichier comptes
            if not os.path.exists(accounts_file):
                self.logger.error(f"❌ Fichier comptes non trouvé: {accounts_file}")
                return False
            
            # Chargement comptes (même logique)
            self.accounts = self._load_accounts(accounts_file)
            if not self.accounts:
                self.logger.error("❌ Aucun compte valide chargé")
                return False
            
            # DIFFÉRENCE: Utilise FreeProxyManager au lieu de ProxyManager
            if free_proxies:
                free_proxy_config = os.path.join(self.config_dir, 'free_proxies.json')
                if os.path.exists(free_proxy_config):
                    self.proxy_manager = FreeProxyManager(free_proxy_config)
                    self.logger.info("🆓 Gestionnaire proxy gratuit configuré")
                else:
                    self.logger.warning("⚠️ Config proxy gratuit manquante, création instance test")
                    self.proxy_manager = FreeProxyManager.create_test_instance()
            else:
                self.logger.info("🔄 Mode sans proxy activé")
                self.proxy_manager = None
            
            self.logger.info(f"✅ Configuration chargée: {len(self.accounts)} comptes")
            return True
            
        except Exception as e:
            log_error_with_context('main_free_proxy', e, {'config_dir': self.config_dir})
            return False
    
    def _load_accounts(self, accounts_file: str) -> List[Dict]:
        """Charge les comptes (même logique que version principale)"""
        accounts = []
        
        try:
            with open(accounts_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row_num, row in enumerate(reader, 1):
                    # Validation des champs requis
                    if not row.get('email') or not row.get('password'):
                        self.logger.warning(f"⚠️ Ligne {row_num} incomplète, ignorée")
                        continue
                    
                    # Validation format email
                    email = row['email'].strip().lower()
                    if not self._is_valid_hotmail_email(email):
                        self.logger.warning(f"⚠️ Email non valide ignoré: {email}")
                        continue
                    
                    account = {
                        'email': email,
                        'password': row['password'].strip(),
                        'app_password': row.get('app_password', '').strip(),
                        'use_app_password': bool(row.get('app_password', '').strip())
                    }
                    
                    accounts.append(account)
            
            self.logger.info(f"📧 {len(accounts)} comptes valides chargés")
            return accounts
            
        except Exception as e:
            log_error_with_context('main_free_proxy', e, {'file': accounts_file})
            return []
    
    def _is_valid_hotmail_email(self, email: str) -> bool:
        """Vérifie si l'email est un compte Hotmail/Outlook valide"""
        valid_domains = [
            '@hotmail.com', '@hotmail.fr', '@hotmail.co.uk',
            '@outlook.com', '@outlook.fr', '@outlook.co.uk',
            '@live.com', '@live.fr', '@live.co.uk',
            '@msn.com'
        ]
        
        return any(email.endswith(domain) for domain in valid_domains)
    
    def test_proxy_connectivity(self) -> bool:
        """Test spécial pour proxies gratuits"""
        if not self.proxy_manager:
            self.logger.info("🔄 Mode sans proxy - pas de test proxy nécessaire")
            return True
        
        self.logger.info("🧪 Test de connectivité proxy gratuit...")
        
        try:
            # Obtenir statistiques des proxies
            stats = self.proxy_manager.get_proxy_stats()
            self.logger.info(f"📊 Proxies disponibles: {stats}")
            
            if stats['working_proxies'] == 0:
                self.logger.warning("⚠️ Aucun proxy gratuit fonctionnel")
                return False
            
            # Test d'obtention proxy
            test_proxy = self.proxy_manager.get_proxy_for_account("test@test.com")
            self.logger.info(f"✅ Test proxy obtenu: {test_proxy}")
            
            self.proxy_manager.end_session("test@test.com")
            
            return True
            
        except Exception as e:
            log_error_with_context('main_free_proxy', e, {'action': 'test_proxy'})
            return False
    
    def process_single_account_test(self, account: Dict, max_emails: int = 5, dry_run: bool = True) -> bool:
        """Version de test simplifiée pour un seul compte"""
        email = account['email']
        session_start_time = time.time()
        
        try:
            self.logger.info(f"🧪 TEST compte: {email}")
            
            # 1. Obtenir proxy (gratuit ou None)
            if self.proxy_manager:
                proxy_config = self.proxy_manager.get_proxy_for_account(email)
                self.stats['unique_sessions'].add(proxy_config.get('session_id', 'direct'))
                self.logger.info(f"🌐 Proxy assigné: {proxy_config}")
            else:
                proxy_config = None
                self.logger.info("🔄 Mode connexion directe")
            
            # 2. Sélectionner client aléatoire
            client = self.client_simulator.get_random_client()
            
            # 3. Log début session
            session_id = proxy_config.get('session_id', 'direct') if proxy_config else 'direct'
            log_session_start(email, client.name, session_id)
            
            # 4. Simulation connexion (sans vraie connexion IMAP en mode test)
            if dry_run:
                self.logger.info("🧪 DRY RUN: Simulation connexion IMAP...")
                
                # Délai de connexion réaliste
                connect_delay = self.behavior_simulator.calculate_action_delay('connect')
                self.behavior_simulator.wait_with_progress(connect_delay, "Simulation connexion")
                
                # Simulation récupération emails
                scan_delay = self.behavior_simulator.calculate_action_delay('email_scan')
                self.behavior_simulator.wait_with_progress(scan_delay, "Simulation scan spam")
                
                # Simulation traitement emails
                fake_email_count = random.randint(1, max_emails)
                self.logger.info(f"📧 Simulation: {fake_email_count} emails spam trouvés")
                
                # Simulation déplacement avec comportement humain
                for i in range(fake_email_count):
                    read_delay = self.behavior_simulator.calculate_reading_delay(
                        random.randint(500, 2000), 'promotional'
                    )
                    self.behavior_simulator.wait_with_progress(
                        read_delay, f"Simulation lecture email {i+1}"
                    )
                    
                    # Mise à jour fatigue
                    self.behavior_simulator.update_fatigue(1.0)
                    
                    # Pause potentielle
                    if self.behavior_simulator.should_take_break():
                        break_duration = self.behavior_simulator.take_human_break()
                        self.behavior_simulator.wait_with_progress(break_duration, "Pause humaine")
                
                self.stats['emails_moved'] += fake_email_count
                self.logger.info(f"✅ Simulation terminée: {fake_email_count} emails 'déplacés'")
                
            else:
                self.logger.warning("⚠️ Mode réel non implémenté dans cette version test")
                return False
            
            return True
            
        except Exception as e:
            log_error_with_context('main_free_proxy', e, {'account': email})
            return False
        
        finally:
            # Fin de session
            if self.proxy_manager:
                self.proxy_manager.end_session(email)
            
            # Log fin session
            session_duration = time.time() - session_start_time
            log_session_end(email, self.stats['emails_moved'], self.stats['errors'], session_duration)

def main():
    """Point d'entrée pour version test proxy gratuit"""
    parser = argparse.ArgumentParser(
        description="Spam to Inbox - VERSION TEST avec proxies gratuits",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Version de test utilisant des proxies gratuits:

Exemples d'utilisation:

  # Test avec proxies gratuits
  python main_free_proxy.py --test-free-proxies

  # Test d'un seul compte avec proxy gratuit
  python main_free_proxy.py --test-single-account user@hotmail.com

  # Test sans proxy (connexion directe)
  python main_free_proxy.py --no-proxy --test-single-account user@hotmail.com

  # Actualiser liste proxies gratuits
  python main_free_proxy.py --refresh-proxies

ATTENTION: Version de test uniquement - utilise des proxies gratuits publics
        """
    )
    
    # Arguments de test
    parser.add_argument('--test-free-proxies', action='store_true',
                       help='Test des proxies gratuits seulement')
    parser.add_argument('--test-single-account', type=str,
                       help='Test un seul compte spécifique')
    parser.add_argument('--no-proxy', action='store_true',
                       help='Mode sans proxy (connexion directe)')
    parser.add_argument('--refresh-proxies', action='store_true',
                       help='Actualise la liste des proxies gratuits')
    
    # Arguments standard
    parser.add_argument('--accounts', type=str,
                       help='Fichier CSV des comptes')
    parser.add_argument('--max-emails', type=int, default=5,
                       help='Nombre maximum d\'emails pour test (défaut: 5)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Niveau de logging')
    
    args = parser.parse_args()
    
    # Initialisation du processeur
    processor = SpamToInboxFreeProxyProcessor(log_level=args.log_level)
    
    try:
        # Test proxies gratuits seulement
        if args.test_free_proxies:
            processor.logger.info("🧪 TEST PROXIES GRATUITS UNIQUEMENT")
            
            if not processor.load_configuration(args.accounts, free_proxies=not args.no_proxy):
                sys.exit(1)
            
            if not args.no_proxy:
                if processor.test_proxy_connectivity():
                    print("✅ Proxies gratuits fonctionnels trouvés!")
                    
                    # Afficher statistiques
                    stats = processor.proxy_manager.get_proxy_stats()
                    print(f"📊 Statistiques: {stats}")
                    sys.exit(0)
                else:
                    print("❌ Aucun proxy gratuit fonctionnel!")
                    sys.exit(1)
            else:
                print("✅ Mode sans proxy configuré!")
                sys.exit(0)
        
        # Actualisation proxies
        if args.refresh_proxies:
            processor.logger.info("🔄 ACTUALISATION PROXIES GRATUITS")
            
            if processor.load_configuration(free_proxies=True):
                processor.proxy_manager.refresh_proxies()
                stats = processor.proxy_manager.get_proxy_stats()
                print(f"✅ Proxies actualisés: {stats}")
                sys.exit(0)
            else:
                print("❌ Erreur lors de l'actualisation!")
                sys.exit(1)
        
        # Test d'un seul compte
        if args.test_single_account:
            processor.logger.info(f"🧪 TEST COMPTE UNIQUE: {args.test_single_account}")
            
            if not processor.load_configuration(args.accounts, free_proxies=not args.no_proxy):
                sys.exit(1)
            
            # Trouver le compte dans la liste
            target_account = None
            for account in processor.accounts:
                if account['email'] == args.test_single_account:
                    target_account = account
                    break
            
            if not target_account:
                processor.logger.error(f"❌ Compte {args.test_single_account} non trouvé dans la configuration")
                sys.exit(1)
            
            # Test du compte
            success = processor.process_single_account_test(
                target_account, 
                args.max_emails, 
                dry_run=True
            )
            
            if success:
                print(f"✅ Test réussi pour {args.test_single_account}")
                sys.exit(0)
            else:
                print(f"❌ Test échoué pour {args.test_single_account}")
                sys.exit(1)
        
        # Si aucune option spéciale, afficher aide
        parser.print_help()
        
    except KeyboardInterrupt:
        processor.logger.info("🛑 Arrêt demandé par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        log_error_with_context('main_free_proxy', e)
        sys.exit(1)

if __name__ == "__main__":
    main()