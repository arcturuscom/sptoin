#!/usr/bin/env python3
"""
SPAM TO INBOX - Point d'entrée principal
Automatise le déplacement d'emails spam vers inbox pour Hotmail/Outlook
Avec protection anti-détection maximale et sticky sessions
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
from proxy_manager import ProxyManager
from client_simulator import ClientSimulator
from email_processor import EmailProcessor
from anti_detection import HumanBehaviorSimulator
from logger import (setup_logging, get_logger, log_session_start, 
                   log_session_end, log_error_with_context, 
                   create_session_summary, cleanup_old_logs)

class SpamToInboxProcessor:
    """Processeur principal pour le déplacement spam vers inbox"""
    
    def __init__(self, config_dir: str = 'config', log_level: str = 'INFO'):
        self.config_dir = config_dir
        self.logger = setup_logging(log_level)
        
        # Composants principaux
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
        
        self.logger.info("🚀 Spam-to-Inbox Processor initialisé")
    
    def load_configuration(self, accounts_file: str = None, proxies_file: str = None) -> bool:
        """Charge la configuration depuis les fichiers"""
        try:
            # Fichiers par défaut si non spécifiés
            if not accounts_file:
                accounts_file = os.path.join(self.config_dir, 'accounts.csv')
            if not proxies_file:
                proxies_file = os.path.join(self.config_dir, 'proxies.json')
            
            # Vérification existence fichiers
            if not os.path.exists(accounts_file):
                self.logger.error(f"❌ Fichier comptes non trouvé: {accounts_file}")
                return False
            
            if not os.path.exists(proxies_file):
                self.logger.error(f"❌ Fichier proxies non trouvé: {proxies_file}")
                return False
            
            # Chargement comptes
            self.accounts = self._load_accounts(accounts_file)
            if not self.accounts:
                self.logger.error("❌ Aucun compte valide chargé")
                return False
            
            # Chargement configuration proxy
            self.proxy_manager = ProxyManager.from_config(proxies_file)
            
            self.logger.info(f"✅ Configuration chargée: {len(self.accounts)} comptes")
            return True
            
        except Exception as e:
            log_error_with_context('main', e, {'config_dir': self.config_dir})
            return False
    
    def _load_accounts(self, accounts_file: str) -> List[Dict]:
        """Charge les comptes depuis le fichier CSV"""
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
            log_error_with_context('main', e, {'file': accounts_file})
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
    
    def process_all_accounts(self, max_emails_per_account: int = 50, 
                           dry_run: bool = False, 
                           account_filter: str = None) -> bool:
        """
        Traite tous les comptes configurés
        WORKFLOW CORRECT avec sticky sessions
        """
        if not self.accounts or not self.proxy_manager:
            self.logger.error("❌ Configuration non chargée")
            return False
        
        # Filtrage des comptes si nécessaire
        accounts_to_process = self.accounts
        if account_filter:
            accounts_to_process = [acc for acc in self.accounts 
                                 if account_filter.lower() in acc['email'].lower()]
            self.logger.info(f"🔍 Filtre appliqué: {len(accounts_to_process)} comptes sélectionnés")
        
        if dry_run:
            self.logger.info("🧪 MODE DRY RUN - Aucune modification ne sera effectuée")
        
        # Nettoyage préventif des sessions expirées
        expired_count = self.proxy_manager.force_cleanup_expired_sessions()
        if expired_count > 0:
            self.logger.info(f"🧹 {expired_count} sessions expirées nettoyées")
        
        # Traitement de chaque compte
        for account in accounts_to_process:
            try:
                success = self._process_single_account(
                    account, max_emails_per_account, dry_run
                )
                
                if success:
                    self.stats['accounts_processed'] += 1
                else:
                    self.stats['errors'] += 1
                
                # Pause entre comptes (comportement humain)
                if account != accounts_to_process[-1]:  # Pas de pause après le dernier
                    inter_account_delay = random.uniform(8.0, 15.0)
                    self.logger.info(f"⏸️ Pause entre comptes: {inter_account_delay:.1f}s")
                    self.behavior_simulator.wait_with_progress(
                        inter_account_delay, "Pause inter-comptes"
                    )
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Interruption utilisateur détectée")
                break
            except Exception as e:
                self.stats['errors'] += 1
                log_error_with_context('main', e, {'account': account['email']})
        
        # Calcul statistiques finales
        self._finalize_stats()
        
        # Résumé final
        summary = create_session_summary(self.stats)
        self.logger.info(summary)
        
        return self.stats['errors'] == 0
    
    def _process_single_account(self, account: Dict, max_emails: int, dry_run: bool) -> bool:
        """
        Traite un seul compte avec sticky session
        CRITIQUE: Même proxy pour TOUTE la session
        """
        email = account['email']
        session_start_time = time.time()
        
        try:
            # 1. Obtenir proxy sticky pour CE compte
            proxy_config = self.proxy_manager.get_proxy_for_account(email)
            self.stats['unique_sessions'].add(proxy_config['session_id'])
            
            # 2. Sélectionner client aléatoire
            client = self.client_simulator.get_random_client()
            
            # 3. Pattern de comportement pour cette session
            usage_pattern = self.client_simulator.get_realistic_usage_pattern()
            
            # Log début session
            log_session_start(email, client.name, proxy_config['session_id'])
            
            # 4. Connexion avec CE proxy (sticky)
            processor = EmailProcessor(proxy_config, client)
            
            # Délai de connexion réaliste
            connect_delay = self.behavior_simulator.calculate_action_delay('connect')
            self.behavior_simulator.wait_with_progress(connect_delay, "Connexion IMAP")
            
            # Tentative connexion
            connected = processor.connect(
                email, 
                account['app_password'] if account['use_app_password'] else account['password'],
                account['use_app_password']
            )
            
            if not connected:
                self.logger.error(f"❌ Échec connexion pour {email}")
                return False
            
            try:
                # 5. Récupération emails spam (MÊME proxy)
                self.logger.info(f"📂 Recherche emails spam pour {email}")
                
                scan_delay = self.behavior_simulator.calculate_action_delay('email_scan')
                self.behavior_simulator.wait_with_progress(scan_delay, "Scan dossier spam")
                
                spam_emails = processor.get_spam_emails(max_emails)
                
                if not spam_emails:
                    self.logger.info(f"📭 Aucun spam trouvé pour {email}")
                    return True
                
                self.logger.info(f"📧 {len(spam_emails)} emails spam trouvés pour {email}")
                
                # 6. Traitement avec comportement humain
                moved_count = 0
                if not dry_run:
                    moved_count = self._process_emails_with_behavior(
                        processor, spam_emails, usage_pattern
                    )
                else:
                    self.logger.info("🧪 DRY RUN: Emails non déplacés")
                    moved_count = len(spam_emails)
                
                self.stats['emails_moved'] += moved_count
                
                # Pause finale réaliste
                final_delay = self.behavior_simulator.calculate_action_delay('disconnect')
                self.behavior_simulator.wait_with_progress(final_delay, "Finalisation")
                
                return True
                
            finally:
                # 7. Déconnexion propre (MÊME proxy)
                processor.disconnect()
                
        except Exception as e:
            log_error_with_context('main', e, {'account': email})
            return False
        
        finally:
            # 8. CRITIQUE: Fin de session sticky
            self.proxy_manager.end_session(email)
            
            # Log fin session
            session_duration = time.time() - session_start_time
            success_count = self.stats['emails_moved']
            fail_count = self.stats['errors']
            log_session_end(email, success_count, fail_count, session_duration)
    
    def _process_emails_with_behavior(self, processor: EmailProcessor, 
                                    emails: List[Dict], pattern: Dict) -> int:
        """Traite les emails avec simulation comportement humain"""
        batch_sizes = self.behavior_simulator._calculate_batch_sizes(len(emails))
        moved_count = 0
        
        email_index = 0
        
        for batch_num, batch_size in enumerate(batch_sizes, 1):
            # Extraction du batch
            batch_emails = emails[email_index:email_index + batch_size]
            email_index += batch_size
            
            self.logger.info(f"📦 Traitement lot {batch_num}/{len(batch_sizes)} : {len(batch_emails)} emails")
            
            # Traitement du batch avec délais réalistes
            for i, email_data in enumerate(batch_emails):
                # Délai lecture basé sur taille email
                read_delay = self.behavior_simulator.calculate_reading_delay(
                    email_data.get('size', 1000),
                    'promotional'  # Spam = lecture rapide
                )
                
                # Simulation lecture
                self.behavior_simulator.wait_with_progress(read_delay, f"Lecture email {i+1}")
                
                # Mise à jour fatigue
                self.behavior_simulator.update_fatigue(1.0)
                
                # Pause potentielle
                if self.behavior_simulator.should_take_break():
                    break_duration = self.behavior_simulator.take_human_break()
                    self.behavior_simulator.wait_with_progress(break_duration, "Pause humaine")
            
            # Déplacement du batch
            success, fails = processor.move_emails_to_inbox(batch_emails)
            moved_count += success
            
            if fails > 0:
                self.logger.warning(f"⚠️ {fails} échecs dans le lot {batch_num}")
            
            # Pause entre lots
            if batch_num < len(batch_sizes):
                batch_delay = random.uniform(2.0, 5.0)
                self.behavior_simulator.wait_with_progress(batch_delay, "Pause inter-lots")
        
        return moved_count
    
    def _finalize_stats(self):
        """Finalise les statistiques de session"""
        self.stats['duration'] = time.time() - self.stats['start_time']
        
        if self.stats['accounts_processed'] > 0:
            self.stats['success_rate'] = (
                (self.stats['accounts_processed'] - self.stats['errors']) / 
                self.stats['accounts_processed']
            ) * 100
        
        self.stats['unique_sessions'] = len(self.stats['unique_sessions'])
    
    def test_configuration(self) -> bool:
        """Test de la configuration sans traitement réel"""
        self.logger.info("🧪 Test de configuration...")
        
        if not self.load_configuration():
            return False
        
        # Test proxy manager
        test_email = "test@hotmail.com"
        proxy = self.proxy_manager.get_proxy_for_account(test_email)
        self.logger.info(f"✅ Proxy test: {proxy['user']}@{proxy['host']}")
        self.proxy_manager.end_session(test_email)
        
        # Test client simulator
        client = self.client_simulator.get_random_client()
        self.logger.info(f"✅ Client test: {client.name}")
        
        # Test behavior simulator
        delay = self.behavior_simulator.calculate_reading_delay(1500)
        self.logger.info(f"✅ Comportement test: délai {delay:.2f}s")
        
        self.logger.info("✅ Configuration valide!")
        return True

def main():
    """Point d'entrée principal avec argparse"""
    parser = argparse.ArgumentParser(
        description="Spam to Inbox - Déplacement automatisé d'emails spam avec anti-détection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:

  # Traitement standard avec configuration par défaut
  python main.py

  # Traitement avec limite d'emails et mode dry-run
  python main.py --max-emails 25 --dry-run

  # Test de configuration seulement
  python main.py --test-config

  # Traitement avec filtre de comptes et logs debug
  python main.py --filter "hotmail" --log-level DEBUG

  # Configuration personnalisée
  python main.py --accounts custom/accounts.csv --proxies custom/proxies.json

IMPORTANT:
- Assurez-vous que les fichiers config/accounts.csv et config/proxies.json existent
- Les sticky sessions maintiennent la même IP par compte pour éviter la détection
- Le comportement humain est simulé avec délais et pauses réalistes
        """
    )
    
    # Arguments principaux
    parser.add_argument('--accounts', type=str, 
                       help='Fichier CSV des comptes (défaut: config/accounts.csv)')
    parser.add_argument('--proxies', type=str,
                       help='Fichier JSON des proxies (défaut: config/proxies.json)')
    parser.add_argument('--max-emails', type=int, default=50,
                       help='Nombre maximum d\'emails par compte (défaut: 50)')
    
    # Options de comportement
    parser.add_argument('--dry-run', action='store_true',
                       help='Mode test sans modifications réelles')
    parser.add_argument('--filter', type=str,
                       help='Filtre sur les adresses email (ex: "hotmail")')
    
    # Configuration logging
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Niveau de logging (défaut: INFO)')
    parser.add_argument('--cleanup-logs', action='store_true',
                       help='Nettoie les anciens logs avant démarrage')
    
    # Opérations spéciales
    parser.add_argument('--test-config', action='store_true',
                       help='Test de configuration seulement')
    parser.add_argument('--version', action='version', version='Spam-to-Inbox 1.0.0')
    
    args = parser.parse_args()
    
    # Nettoyage logs si demandé
    if args.cleanup_logs:
        cleanup_old_logs()
    
    # Initialisation du processeur
    processor = SpamToInboxProcessor(log_level=args.log_level)
    
    try:
        # Chargement configuration
        if not processor.load_configuration(args.accounts, args.proxies):
            sys.exit(1)
        
        # Mode test configuration
        if args.test_config:
            if processor.test_configuration():
                print("✅ Configuration valide!")
                sys.exit(0)
            else:
                print("❌ Erreurs dans la configuration!")
                sys.exit(1)
        
        # Traitement principal
        processor.logger.info("=" * 50)
        processor.logger.info("🚀 DÉMARRAGE SPAM-TO-INBOX")
        processor.logger.info("=" * 50)
        
        success = processor.process_all_accounts(
            max_emails_per_account=args.max_emails,
            dry_run=args.dry_run,
            account_filter=args.filter
        )
        
        if success:
            processor.logger.info("✅ Traitement terminé avec succès!")
            sys.exit(0)
        else:
            processor.logger.error("❌ Traitement terminé avec erreurs!")
            sys.exit(1)
    
    except KeyboardInterrupt:
        processor.logger.info("🛑 Arrêt demandé par l'utilisateur")
        sys.exit(130)
    except Exception as e:
        log_error_with_context('main', e)
        sys.exit(1)

if __name__ == "__main__":
    main()