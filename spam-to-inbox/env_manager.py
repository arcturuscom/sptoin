#!/usr/bin/env python3
"""
Environment Manager - CLI tool for environment management and validation
Helps switch between environments and validate configurations
"""
import os
import sys
import json
import argparse
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from environment_config import EnvironmentConfig, Environment
from unified_proxy_manager import create_proxy_manager
from logger import setup_logging, get_logger

class EnvironmentManager:
    """Environment management and validation tool"""
    
    def __init__(self):
        self.config_dir = "config"
        self.logger = setup_logging('INFO')
    
    def list_environments(self) -> Dict[str, Any]:
        """List all available environments and their status"""
        environments = {}
        
        for env in Environment:
            try:
                env_config = EnvironmentConfig(env, self.config_dir)
                config_file = os.path.join(self.config_dir, f'environment_{env.value}.json')
                accounts_file = env_config.get_accounts_file()
                
                environments[env.value] = {
                    'environment': env.value,
                    'config_exists': os.path.exists(config_file),
                    'accounts_exists': os.path.exists(accounts_file),
                    'proxy_provider': env_config.get_proxy_config().provider,
                    'dry_run': env_config.get_security_config().dry_run_mode,
                    'max_emails': env_config.get_email_config().max_emails_per_account,
                    'log_level': env_config.get_logging_config().level,
                    'description': self._get_env_description(env.value)
                }
            except Exception as e:
                environments[env.value] = {
                    'environment': env.value,
                    'error': str(e),
                    'status': 'ERROR'
                }
        
        return environments
    
    def _get_env_description(self, env: str) -> str:
        """Get environment description"""
        descriptions = {
            'local': 'Local development - direct connection, minimal settings',
            'dev': 'Development - free proxies, debug logging, safe testing',
            'staging': 'Staging - production-like with safety measures',
            'prod': 'Production - full security, SmartProxy, live processing'
        }
        return descriptions.get(env, 'Unknown environment')
    
    def validate_environment(self, env_name: str) -> bool:
        """Validate specific environment configuration"""
        try:
            environment = Environment(env_name)
            env_config = EnvironmentConfig(environment, self.config_dir)
            
            self.logger.info(f"🔍 Validating {env_name.upper()} environment...")
            
            # Basic validation
            if not env_config.validate_environment():
                return False
            
            # Test proxy manager creation
            self.logger.info("🌐 Testing proxy manager...")
            proxy_manager = create_proxy_manager(env_config)
            
            # Test connectivity
            if not proxy_manager.test_connectivity():
                self.logger.warning("⚠️ Proxy connectivity test failed")
                if env_name == 'prod':
                    return False
            
            # Environment-specific validations
            if env_name == 'prod':
                if not self._validate_production(env_config):
                    return False
            
            self.logger.info(f"✅ {env_name.upper()} environment validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Validation failed for {env_name}: {e}")
            return False
    
    def _validate_production(self, env_config: EnvironmentConfig) -> bool:
        """Production-specific validations"""
        proxy_config = env_config.get_proxy_config()
        
        # Check SmartProxy credentials
        if proxy_config.provider == "smartproxy":
            if not proxy_config.username or not proxy_config.password:
                self.logger.error("❌ Production requires SmartProxy credentials")
                self.logger.info("   Set SMARTPROXY_USERNAME and SMARTPROXY_PASSWORD environment variables")
                return False
        
        # Check accounts file
        accounts_file = env_config.get_accounts_file()
        if 'prod' in accounts_file and not os.path.exists(accounts_file):
            self.logger.error(f"❌ Production accounts file missing: {accounts_file}")
            return False
        
        return True
    
    def set_environment_marker(self, env_name: str) -> bool:
        """Set environment marker file"""
        try:
            marker_file = os.path.join(self.config_dir, '.env_marker')
            
            os.makedirs(self.config_dir, exist_ok=True)
            with open(marker_file, 'w') as f:
                f.write(env_name)
            
            self.logger.info(f"✅ Environment marker set to: {env_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to set environment marker: {e}")
            return False
    
    def get_current_environment(self) -> str:
        """Get currently configured environment"""
        try:
            env_config = EnvironmentConfig(config_dir=self.config_dir)
            return env_config.environment.value
        except:
            return 'unknown'
    
    def create_missing_configs(self, env_name: str) -> bool:
        """Create missing configuration files for environment"""
        try:
            environment = Environment(env_name)
            env_config = EnvironmentConfig(environment, self.config_dir)
            
            config_file = os.path.join(self.config_dir, f'environment_{env_name}.json')
            if not os.path.exists(config_file):
                self.logger.info(f"📝 Creating config file: {config_file}")
                env_config._create_default_config(config_file)
            
            accounts_file = env_config.get_accounts_file()
            if not os.path.exists(accounts_file):
                self.logger.info(f"📝 Creating accounts file: {accounts_file}")
                self._create_sample_accounts_file(accounts_file, env_name)
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to create configs: {e}")
            return False
    
    def _create_sample_accounts_file(self, accounts_file: str, env_name: str):
        """Create sample accounts file"""
        os.makedirs(os.path.dirname(accounts_file), exist_ok=True)
        
        if env_name == 'prod':
            content = "email,password,app_password\n# REPLACE WITH REAL PRODUCTION ACCOUNTS\n# user@hotmail.com,secure_password,app_password_16_chars\n"
        else:
            content = f"email,password,app_password\n{env_name}_user@hotmail.com,{env_name}_password_123,\n{env_name}_test@outlook.com,{env_name}_password_456,{env_name}_app_pass\n"
        
        with open(accounts_file, 'w') as f:
            f.write(content)
    
    def show_environment_info(self, env_name: str = None) -> Dict:
        """Show detailed environment information"""
        if env_name:
            environments = {env_name: self.list_environments()[env_name]}
        else:
            environments = self.list_environments()
        
        return environments
    
    def test_proxy_providers(self) -> Dict[str, Any]:
        """Test all proxy providers across environments"""
        results = {}
        
        for env in Environment:
            try:
                env_config = EnvironmentConfig(env, self.config_dir)
                proxy_manager = create_proxy_manager(env_config)
                
                results[env.value] = {
                    'provider': env_config.get_proxy_config().provider,
                    'connectivity': proxy_manager.test_connectivity(),
                    'stats': proxy_manager.get_proxy_stats()
                }
                
            except Exception as e:
                results[env.value] = {
                    'error': str(e),
                    'status': 'FAILED'
                }
        
        return results

def main():
    """Environment manager CLI"""
    parser = argparse.ArgumentParser(
        description="Environment Manager - Build Once, Run Everywhere",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python env_manager.py --list
  python env_manager.py --validate dev
  python env_manager.py --set-env staging
  python env_manager.py --info prod
  python env_manager.py --create-configs local
  python env_manager.py --test-proxies
        """
    )
    
    parser.add_argument('--list', action='store_true',
                       help='List all environments and their status')
    parser.add_argument('--validate', type=str, choices=['local', 'dev', 'staging', 'prod'],
                       help='Validate specific environment')
    parser.add_argument('--set-env', type=str, choices=['local', 'dev', 'staging', 'prod'],
                       help='Set environment marker')
    parser.add_argument('--info', type=str, choices=['local', 'dev', 'staging', 'prod'],
                       help='Show detailed environment information')
    parser.add_argument('--create-configs', type=str, choices=['local', 'dev', 'staging', 'prod'],
                       help='Create missing configuration files')
    parser.add_argument('--test-proxies', action='store_true',
                       help='Test proxy providers across all environments')
    parser.add_argument('--current', action='store_true',
                       help='Show current environment')
    
    args = parser.parse_args()
    
    manager = EnvironmentManager()
    
    try:
        if args.list:
            print("\n🌍 AVAILABLE ENVIRONMENTS")
            print("=" * 50)
            
            environments = manager.list_environments()
            for env_name, info in environments.items():
                if 'error' in info:
                    print(f"{env_name:10} ❌ ERROR: {info['error']}")
                else:
                    status = "✅" if info['config_exists'] and info['accounts_exists'] else "⚠️"
                    proxy = info['proxy_provider']
                    dry_run = "DRY" if info['dry_run'] else "LIVE"
                    print(f"{env_name:10} {status} {proxy:10} {dry_run:4} - {info['description']}")
            
            print("\n🔍 Legend:")
            print("✅ = Fully configured    ⚠️ = Missing files")
            print("DRY = Dry run mode      LIVE = Live processing")
        
        elif args.validate:
            success = manager.validate_environment(args.validate)
            if success:
                print(f"✅ {args.validate.upper()} environment is valid")
            else:
                print(f"❌ {args.validate.upper()} environment validation failed")
                sys.exit(1)
        
        elif args.set_env:
            success = manager.set_environment_marker(args.set_env)
            if success:
                print(f"✅ Environment set to: {args.set_env.upper()}")
            else:
                sys.exit(1)
        
        elif args.info:
            info = manager.show_environment_info(args.info)[args.info]
            
            print(f"\n🌍 {args.info.upper()} ENVIRONMENT")
            print("=" * 30)
            
            if 'error' in info:
                print(f"❌ ERROR: {info['error']}")
            else:
                print(f"Description:    {info['description']}")
                print(f"Config file:    {'✅' if info['config_exists'] else '❌'}")
                print(f"Accounts file:  {'✅' if info['accounts_exists'] else '❌'}")
                print(f"Proxy provider: {info['proxy_provider']}")
                print(f"Mode:          {'DRY RUN' if info['dry_run'] else 'LIVE'}")
                print(f"Max emails:    {info['max_emails']}")
                print(f"Log level:     {info['log_level']}")
        
        elif args.create_configs:
            success = manager.create_missing_configs(args.create_configs)
            if success:
                print(f"✅ Configuration files created for {args.create_configs.upper()}")
            else:
                sys.exit(1)
        
        elif args.test_proxies:
            print("\n🌐 TESTING PROXY PROVIDERS")
            print("=" * 40)
            
            results = manager.test_proxy_providers()
            for env_name, result in results.items():
                if 'error' in result:
                    print(f"{env_name:10} ❌ {result['error']}")
                else:
                    status = "✅" if result['connectivity'] else "❌"
                    provider = result['provider']
                    print(f"{env_name:10} {status} {provider}")
        
        elif args.current:
            current = manager.get_current_environment()
            print(f"Current environment: {current.upper()}")
        
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()