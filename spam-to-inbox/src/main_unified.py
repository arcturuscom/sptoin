#!/usr/bin/env python3
"""
UNIFIED MAIN ENTRY POINT - Environment-aware spam to inbox processor
Build once, run everywhere - supports LOCAL/DEV/STAGING/PROD environments
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

# Environment-aware imports
from environment_config import EnvironmentConfig, Environment, get_current_environment
from unified_proxy_manager import create_proxy_manager
from client_simulator import ClientSimulator
from email_processor import EmailProcessor
from anti_detection import HumanBehaviorSimulator
from logger import (setup_logging, get_logger, log_session_start, 
                   log_session_end, log_error_with_context, 
                   create_session_summary, cleanup_old_logs)

class UnifiedSpamProcessor:
    """
    Environment-aware spam processor
    Automatically adapts behavior based on environment configuration
    """
    
    def __init__(self, environment: Environment = None):
        # Initialize environment configuration
        self.env_config = EnvironmentConfig(environment) if environment else get_current_environment()
        
        # Setup logging based on environment
        logging_config = self.env_config.get_logging_config()
        self.logger = setup_logging(
            log_level=logging_config.level,
            log_dir=logging_config.log_dir,
            enable_console=logging_config.enable_console,
            enable_file=logging_config.enable_file,
            max_file_size=logging_config.max_file_size,
            backup_count=logging_config.backup_count
        )
        
        # Initialize components based on environment
        self.proxy_manager = create_proxy_manager(self.env_config)
        self.client_simulator = ClientSimulator()
        
        # Configure behavior simulator based on environment
        behavior_config = self.env_config.get_behavior_config()
        self.behavior_simulator = HumanBehaviorSimulator(
            fatigue_enabled=behavior_config.fatigue_simulation
        )
        
        # Override behavior settings from config
        self.behavior_simulator.base_read_speed = (behavior_config.min_delay_seconds + behavior_config.max_delay_seconds) / 2
        self.behavior_simulator.distraction_probability = behavior_config.distraction_probability
        self.behavior_simulator.break_probability = behavior_config.break_probability
        
        # Statistics tracking
        self.stats = {
            'environment': self.env_config.environment.value,
            'accounts_processed': 0,
            'emails_moved': 0,
            'errors': 0,
            'unique_sessions': set(),
            'start_time': time.time(),
            'duration': 0,
            'success_rate': 0.0
        }
        
        self.logger.info(f"🌍 Unified Spam Processor initialized - Environment: {self.env_config.environment.value.upper()}")
        self._log_environment_info()
    
    def _log_environment_info(self):
        """Log current environment configuration"""
        env_info = self.env_config.get_environment_info()
        security_config = self.env_config.get_security_config()
        
        self.logger.info("=" * 50)
        self.logger.info("🌍 ENVIRONMENT CONFIGURATION")
        self.logger.info("=" * 50)
        self.logger.info(f"Environment: {env_info['environment'].upper()}")
        self.logger.info(f"Proxy Provider: {env_info['proxy_provider']}")
        self.logger.info(f"Accounts File: {env_info['accounts_file']}")
        self.logger.info(f"Dry Run Mode: {env_info['dry_run_mode']}")
        self.logger.info(f"Log Level: {env_info['log_level']}")
        if security_config.max_daily_emails:
            self.logger.info(f"Daily Limit: {security_config.max_daily_emails} emails")
        self.logger.info("=" * 50)
    
    def validate_environment(self) -> bool:
        """Validate environment configuration and readiness"""
        self.logger.info("🔍 Validating environment configuration...")
        
        try:
            # Validate environment config
            if not self.env_config.validate_environment():
                return False
            
            # Test proxy connectivity
            if not self.proxy_manager.test_connectivity():
                self.logger.error("❌ Proxy connectivity test failed")
                return False
            
            # Check accounts file
            accounts_file = self.env_config.get_accounts_file()
            if not os.path.exists(accounts_file):
                self.logger.error(f"❌ Accounts file not found: {accounts_file}")
                return False
            
            # Production-specific validations
            if self.env_config.is_production():
                proxy_config = self.env_config.get_proxy_config()
                if proxy_config.provider == "smartproxy" and (not proxy_config.username or not proxy_config.password):
                    self.logger.error("❌ Production requires valid SmartProxy credentials")
                    return False
            
            self.logger.info("✅ Environment validation passed")
            return True
            
        except Exception as e:
            log_error_with_context('main_unified', e, {'action': 'validate_environment'})
            return False
    
    def load_accounts(self) -> bool:
        """Load accounts based on environment configuration"""
        accounts_file = self.env_config.get_accounts_file()
        security_config = self.env_config.get_security_config()
        
        try:
            self.accounts = []
            
            with open(accounts_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row_num, row in enumerate(reader, 1):
                    # Validation des champs requis
                    if not row.get('email') or not row.get('password'):
                        self.logger.warning(f"⚠️ Ligne {row_num} incomplète, ignorée")
                        continue
                    
                    # Validation format email
                    email = row['email'].strip().lower()
                    if not self._is_valid_email(email):
                        self.logger.warning(f"⚠️ Email non valide ignoré: {email}")
                        continue
                    
                    # Check app password requirement for production
                    accounts_config = self.env_config._config_cache.get("accounts", {})
                    if accounts_config.get("require_app_passwords", False):
                        if not row.get('app_password', '').strip():
                            self.logger.warning(f"⚠️ Mot de passe d'application requis pour {email}")
                            continue
                    
                    account = {
                        'email': email,
                        'password': row['password'].strip(),
                        'app_password': row.get('app_password', '').strip(),
                        'use_app_password': bool(row.get('app_password', '').strip())
                    }
                    
                    self.accounts.append(account)
            
            self.logger.info(f"📧 {len(self.accounts)} comptes valides chargés depuis {accounts_file}")
            return len(self.accounts) > 0
            
        except Exception as e:
            log_error_with_context('main_unified', e, {'file': accounts_file})
            return False
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email address"""
        valid_domains = [
            '@hotmail.com', '@hotmail.fr', '@hotmail.co.uk',
            '@outlook.com', '@outlook.fr', '@outlook.co.uk',
            '@live.com', '@live.fr', '@live.co.uk',
            '@msn.com'
        ]
        
        return any(email.endswith(domain) for domain in valid_domains)
    
    def process_all_accounts(self, account_filter: str = None, override_limits: Dict = None) -> bool:
        """Process all accounts with environment-aware behavior"""
        if not self.accounts:
            self.logger.error("❌ No accounts loaded")
            return False
        
        # Apply account filter
        accounts_to_process = self.accounts
        if account_filter:
            accounts_to_process = [acc for acc in self.accounts 
                                 if account_filter.lower() in acc['email'].lower()]
            self.logger.info(f"🔍 Filter applied: {len(accounts_to_process)} accounts selected")
        
        # Get environment-specific limits
        email_config = self.env_config.get_email_config()
        security_config = self.env_config.get_security_config()
        
        max_emails = override_limits.get('max_emails', email_config.max_emails_per_account) if override_limits else email_config.max_emails_per_account
        
        # Environment-specific warnings
        if security_config.dry_run_mode:
            self.logger.info("🧪 DRY RUN MODE - No actual email modifications")
        else:
            self.logger.warning("🚨 LIVE MODE - Emails will be actually moved!")
            if security_config.require_confirmation:
                response = input("Continue with live processing? (yes/no): ")
                if response.lower() not in ['yes', 'y']:
                    self.logger.info("🛑 Processing cancelled by user")
                    return False
        
        # Process accounts
        try:
            for i, account in enumerate(accounts_to_process, 1):
                self.logger.info(f"🔄 Processing account {i}/{len(accounts_to_process)}: {account['email']}")
                
                success = self._process_single_account(
                    account, 
                    max_emails, 
                    security_config.dry_run_mode
                )
                
                if success:
                    self.stats['accounts_processed'] += 1
                else:
                    self.stats['errors'] += 1
                
                # Inter-account delay from environment config
                if i < len(accounts_to_process):  # Not the last account
                    behavior_config = self.env_config.get_behavior_config()
                    inter_delay = random.uniform(
                        behavior_config.inter_account_delay_min,
                        behavior_config.inter_account_delay_max
                    )
                    self.logger.info(f"⏸️ Inter-account delay: {inter_delay:.1f}s")
                    self.behavior_simulator.wait_with_progress(inter_delay, "Inter-account pause")
                
                # Check daily limits
                if security_config.max_daily_emails and self.stats['emails_moved'] >= security_config.max_daily_emails:
                    self.logger.warning(f"⚠️ Daily limit reached: {security_config.max_daily_emails} emails")
                    break
        
        except KeyboardInterrupt:
            self.logger.info("🛑 Processing interrupted by user")
        except Exception as e:
            log_error_with_context('main_unified', e, {'action': 'process_all_accounts'})
        
        # Finalize statistics
        self._finalize_stats()
        
        # Generate summary
        summary = create_session_summary(self.stats)
        self.logger.info(summary)
        
        return self.stats['errors'] == 0
    
    def _process_single_account(self, account: Dict, max_emails: int, dry_run: bool) -> bool:
        """Process single account with environment-aware configuration"""
        email = account['email']
        session_start_time = time.time()
        
        try:
            # Get proxy from unified manager
            proxy_config = self.proxy_manager.get_proxy_for_account(email)
            session_id = proxy_config.get('session_id', 'unknown')
            self.stats['unique_sessions'].add(session_id)
            
            # Select client
            client = self.client_simulator.get_random_client()
            
            # Log session start
            log_session_start(email, client.name, session_id)
            
            # Get email configuration
            email_config = self.env_config.get_email_config()
            
            # Create processor with environment-aware config
            processor = EmailProcessor(proxy_config, client)
            
            # Connection with environment-specific timeout
            connect_delay = self.behavior_simulator.calculate_action_delay('connect')
            self.behavior_simulator.wait_with_progress(connect_delay, "Connecting to IMAP")
            
            connected = processor.connect(
                email,
                account['app_password'] if account['use_app_password'] else account['password'],
                account['use_app_password']
            )
            
            if not connected:
                self.logger.error(f"❌ Connection failed for {email}")
                return False
            
            try:
                # Get spam emails
                scan_delay = self.behavior_simulator.calculate_action_delay('email_scan')
                self.behavior_simulator.wait_with_progress(scan_delay, "Scanning spam folder")
                
                if dry_run:
                    # Simulation for dry run
                    fake_count = random.randint(1, min(10, max_emails))
                    self.logger.info(f"🧪 DRY RUN: Simulating {fake_count} spam emails")
                    spam_emails = [{'id': f'fake_{i}', 'size': random.randint(500, 3000)} for i in range(fake_count)]
                else:
                    spam_emails = processor.get_spam_emails(max_emails)
                
                if not spam_emails:
                    self.logger.info(f"📭 No spam emails found for {email}")
                    return True
                
                self.logger.info(f"📧 {len(spam_emails)} spam emails found for {email}")
                
                # Process emails with environment-aware behavior
                moved_count = self._process_emails_with_behavior(
                    processor, spam_emails, dry_run, email_config.batch_size
                )
                
                self.stats['emails_moved'] += moved_count
                return True
                
            finally:
                processor.disconnect()
        
        except Exception as e:
            log_error_with_context('main_unified', e, {'account': email})
            return False
        
        finally:
            # End session
            self.proxy_manager.end_session(email)
            
            # Log session end
            session_duration = time.time() - session_start_time
            log_session_end(email, self.stats['emails_moved'], self.stats['errors'], session_duration)
    
    def _process_emails_with_behavior(self, processor: EmailProcessor, emails: List[Dict], 
                                    dry_run: bool, batch_size: int) -> int:
        """Process emails with environment-aware behavior"""
        behavior_config = self.env_config.get_behavior_config()
        moved_count = 0
        
        # Process in environment-configured batches
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(emails) + batch_size - 1) // batch_size
            
            self.logger.info(f"📦 Processing batch {batch_num}/{total_batches}: {len(batch)} emails")
            
            for j, email_data in enumerate(batch):
                # Environment-aware reading delay
                if behavior_config.enable_human_behavior:
                    read_delay = self.behavior_simulator.calculate_reading_delay(
                        email_data.get('size', 1000),
                        'promotional'
                    )
                    # Apply environment min/max constraints
                    read_delay = max(behavior_config.min_delay_seconds,
                                   min(behavior_config.max_delay_seconds, read_delay))
                else:
                    read_delay = random.uniform(behavior_config.min_delay_seconds,
                                              behavior_config.max_delay_seconds)
                
                self.behavior_simulator.wait_with_progress(read_delay, f"Reading email {j+1}")
                
                # Update fatigue if enabled
                if behavior_config.fatigue_simulation:
                    self.behavior_simulator.update_fatigue(1.0)
                
                # Environment-aware breaks
                if (behavior_config.enable_human_behavior and 
                    random.random() < behavior_config.break_probability):
                    break_duration = self.behavior_simulator.take_human_break()
                    self.behavior_simulator.wait_with_progress(break_duration, "Human break")
            
            # Move emails
            if dry_run:
                moved_count += len(batch)
                self.logger.info(f"🧪 DRY RUN: {len(batch)} emails 'moved'")
            else:
                success, fails = processor.move_emails_to_inbox(batch)
                moved_count += success
                if fails > 0:
                    self.logger.warning(f"⚠️ {fails} failures in batch {batch_num}")
        
        return moved_count
    
    def _finalize_stats(self):
        """Finalize processing statistics"""
        self.stats['duration'] = time.time() - self.stats['start_time']
        self.stats['unique_sessions'] = len(self.stats['unique_sessions'])
        
        if self.stats['accounts_processed'] > 0:
            self.stats['success_rate'] = (
                (self.stats['accounts_processed'] - self.stats['errors']) / 
                self.stats['accounts_processed']
            ) * 100

def main():
    """Unified entry point with environment awareness"""
    parser = argparse.ArgumentParser(
        description="Unified Spam-to-Inbox Processor - Build Once, Run Everywhere",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Support:
  LOCAL     - Direct connection, minimal delays, dry-run enforced
  DEV       - Free proxies, debug logging, dry-run enforced  
  STAGING   - SmartProxy, production-like, dry-run enforced
  PROD      - SmartProxy, full security, live processing

Environment Detection (in order):
  1. --env parameter
  2. SPAM_TO_INBOX_ENV environment variable
  3. config/.env_marker file
  4. Hostname analysis
  5. Default to LOCAL

Examples:
  python main_unified.py --env local --validate
  python main_unified.py --env dev --max-emails 10
  python main_unified.py --env staging --test-account user@hotmail.com
  python main_unified.py --env prod --accounts config/accounts_prod.csv

Production Usage:
  export SPAM_TO_INBOX_ENV=prod
  export SMARTPROXY_USERNAME=your_username
  export SMARTPROXY_PASSWORD=your_password
  python main_unified.py
        """
    )
    
    # Environment selection
    parser.add_argument('--env', type=str, choices=['local', 'dev', 'staging', 'prod'],
                       help='Force specific environment')
    
    # Processing options
    parser.add_argument('--max-emails', type=int,
                       help='Override max emails per account')
    parser.add_argument('--filter', type=str,
                       help='Filter accounts by email pattern')
    parser.add_argument('--test-account', type=str,
                       help='Process only specified account')
    
    # Operations
    parser.add_argument('--validate', action='store_true',
                       help='Validate environment configuration only')
    parser.add_argument('--info', action='store_true',
                       help='Show environment information')
    parser.add_argument('--force-live', action='store_true',
                       help='Force live mode (override dry-run)')
    
    # Overrides
    parser.add_argument('--accounts', type=str,
                       help='Override accounts file')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Override log level')
    
    args = parser.parse_args()
    
    try:
        # Determine environment
        environment = None
        if args.env:
            environment = Environment(args.env)
        
        # Initialize processor
        processor = UnifiedSpamProcessor(environment)
        
        # Show environment info
        if args.info:
            env_info = processor.env_config.get_environment_info()
            proxy_info = processor.proxy_manager.get_provider_info()
            
            print("\n" + "=" * 50)
            print("🌍 ENVIRONMENT INFORMATION")
            print("=" * 50)
            for key, value in env_info.items():
                print(f"{key:20}: {value}")
            print("\n🌐 PROXY INFORMATION")
            print("-" * 30)
            for key, value in proxy_info.items():
                print(f"{key:20}: {value}")
            print("=" * 50)
            return
        
        # Validate environment
        if not processor.validate_environment():
            sys.exit(1)
        
        if args.validate:
            print("✅ Environment validation passed!")
            return
        
        # Load accounts
        if not processor.load_accounts():
            sys.exit(1)
        
        # Handle single account test
        if args.test_account:
            target_account = None
            for account in processor.accounts:
                if account['email'] == args.test_account:
                    target_account = account
                    break
            
            if not target_account:
                processor.logger.error(f"❌ Account {args.test_account} not found")
                sys.exit(1)
            
            # Process single account
            success = processor._process_single_account(
                target_account,
                args.max_emails or processor.env_config.get_email_config().max_emails_per_account,
                processor.env_config.get_security_config().dry_run_mode and not args.force_live
            )
            
            sys.exit(0 if success else 1)
        
        # Process all accounts
        override_limits = {}
        if args.max_emails:
            override_limits['max_emails'] = args.max_emails
        
        success = processor.process_all_accounts(
            account_filter=args.filter,
            override_limits=override_limits
        )
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()