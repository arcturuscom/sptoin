"""
Environment Configuration Manager
Supports DEV/PROD environments with build once, run everywhere
"""
import os
import json
from typing import Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass
from logger import get_logger

logger = get_logger(__name__)

class Environment(Enum):
    """Supported environments"""
    DEV = "dev"
    STAGING = "staging"  
    PROD = "prod"
    LOCAL = "local"

@dataclass
class ProxyConfig:
    """Proxy configuration for environment"""
    provider: str
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    sticky_sessions: bool = True
    session_duration: int = 30
    use_free_proxies: bool = False
    free_proxy_config: Optional[str] = None

@dataclass
class EmailConfig:
    """Email server configuration"""
    imap_host: str
    imap_port: int
    max_emails_per_account: int
    batch_size: int
    connection_timeout: int
    retry_attempts: int

@dataclass
class BehaviorConfig:
    """Anti-detection behavior configuration"""
    enable_human_behavior: bool
    fatigue_simulation: bool
    min_delay_seconds: float
    max_delay_seconds: float
    distraction_probability: float
    break_probability: float
    inter_account_delay_min: float
    inter_account_delay_max: float

@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str
    log_dir: str
    max_file_size: int
    backup_count: int
    enable_console: bool
    enable_file: bool
    colored_output: bool

@dataclass
class SecurityConfig:
    """Security and safety configuration"""
    dry_run_mode: bool
    enable_rate_limiting: bool
    max_concurrent_accounts: int
    require_confirmation: bool
    backup_emails_before_move: bool
    max_daily_emails: Optional[int]

class EnvironmentConfig:
    """Main environment configuration manager"""
    
    def __init__(self, environment: Environment = None, config_dir: str = "config"):
        self.config_dir = config_dir
        self.environment = environment or self._detect_environment()
        self._config_cache = {}
        
        logger.info(f"🌍 Environment: {self.environment.value.upper()}")
        self._load_environment_config()
    
    def _detect_environment(self) -> Environment:
        """Auto-detect environment from various sources"""
        
        # 1. Environment variable
        env_var = os.getenv('SPAM_TO_INBOX_ENV', '').lower()
        if env_var:
            try:
                return Environment(env_var)
            except ValueError:
                logger.warning(f"⚠️ Invalid environment variable: {env_var}")
        
        # 2. Config file marker
        env_marker_file = os.path.join(self.config_dir, '.env_marker')
        if os.path.exists(env_marker_file):
            try:
                with open(env_marker_file, 'r') as f:
                    env_from_file = f.read().strip().lower()
                    return Environment(env_from_file)
            except:
                pass
        
        # 3. Hostname-based detection
        hostname = os.getenv('HOSTNAME', '').lower()
        if 'prod' in hostname or 'production' in hostname:
            return Environment.PROD
        elif 'staging' in hostname or 'stage' in hostname:
            return Environment.STAGING
        elif 'dev' in hostname or 'development' in hostname:
            return Environment.DEV
        
        # 4. Default to LOCAL for development
        logger.info("🏠 No environment specified, defaulting to LOCAL")
        return Environment.LOCAL
    
    def _load_environment_config(self):
        """Load configuration for current environment"""
        config_file = os.path.join(self.config_dir, f'environment_{self.environment.value}.json')
        
        if not os.path.exists(config_file):
            logger.warning(f"⚠️ Config file not found: {config_file}")
            logger.info("🔧 Creating default configuration...")
            self._create_default_config(config_file)
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                self._config_cache = json.load(f)
            logger.info(f"✅ Configuration loaded: {config_file}")
        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            self._config_cache = self._get_default_config_dict()
    
    def _create_default_config(self, config_file: str):
        """Create default configuration file for environment"""
        default_config = self._get_default_config_dict()
        
        try:
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ Default config created: {config_file}")
        except Exception as e:
            logger.error(f"❌ Failed to create config: {e}")
    
    def _get_default_config_dict(self) -> Dict[str, Any]:
        """Get default configuration based on environment"""
        
        if self.environment == Environment.PROD:
            return self._get_prod_defaults()
        elif self.environment == Environment.STAGING:
            return self._get_staging_defaults()
        elif self.environment == Environment.DEV:
            return self._get_dev_defaults()
        else:  # LOCAL
            return self._get_local_defaults()
    
    def _get_prod_defaults(self) -> Dict[str, Any]:
        """Production environment defaults"""
        return {
            "environment": "prod",
            "proxy": {
                "provider": "smartproxy",
                "host": "gate.smartproxy.com",
                "port": 10000,
                "username": "${SMARTPROXY_USERNAME}",
                "password": "${SMARTPROXY_PASSWORD}",
                "sticky_sessions": True,
                "session_duration": 30,
                "use_free_proxies": False
            },
            "email": {
                "imap_host": "outlook.office365.com",
                "imap_port": 993,
                "max_emails_per_account": 100,
                "batch_size": 25,
                "connection_timeout": 30,
                "retry_attempts": 3
            },
            "behavior": {
                "enable_human_behavior": True,
                "fatigue_simulation": True,
                "min_delay_seconds": 3.0,
                "max_delay_seconds": 8.0,
                "distraction_probability": 0.05,
                "break_probability": 0.02,
                "inter_account_delay_min": 10.0,
                "inter_account_delay_max": 20.0
            },
            "logging": {
                "level": "INFO",
                "log_dir": "logs",
                "max_file_size": 52428800,
                "backup_count": 10,
                "enable_console": False,
                "enable_file": True,
                "colored_output": False
            },
            "security": {
                "dry_run_mode": False,
                "enable_rate_limiting": True,
                "max_concurrent_accounts": 1,
                "require_confirmation": True,
                "backup_emails_before_move": True,
                "max_daily_emails": 1000
            },
            "accounts": {
                "file": "config/accounts_prod.csv",
                "validate_domains": True,
                "require_app_passwords": True
            }
        }
    
    def _get_staging_defaults(self) -> Dict[str, Any]:
        """Staging environment defaults"""
        config = self._get_prod_defaults()
        config.update({
            "environment": "staging",
            "email": {**config["email"], "max_emails_per_account": 50},
            "logging": {**config["logging"], "level": "DEBUG", "enable_console": True},
            "security": {**config["security"], "dry_run_mode": True, "max_daily_emails": 500},
            "accounts": {"file": "config/accounts_staging.csv", "validate_domains": True, "require_app_passwords": False}
        })
        return config
    
    def _get_dev_defaults(self) -> Dict[str, Any]:
        """Development environment defaults"""
        return {
            "environment": "dev",
            "proxy": {
                "provider": "free",
                "use_free_proxies": True,
                "free_proxy_config": "config/free_proxies.json",
                "sticky_sessions": False,
                "fallback_direct": True
            },
            "email": {
                "imap_host": "outlook.office365.com",
                "imap_port": 993,
                "max_emails_per_account": 10,
                "batch_size": 5,
                "connection_timeout": 15,
                "retry_attempts": 2
            },
            "behavior": {
                "enable_human_behavior": True,
                "fatigue_simulation": False,
                "min_delay_seconds": 1.0,
                "max_delay_seconds": 3.0,
                "distraction_probability": 0.1,
                "break_probability": 0.05,
                "inter_account_delay_min": 2.0,
                "inter_account_delay_max": 5.0
            },
            "logging": {
                "level": "DEBUG",
                "log_dir": "logs",
                "max_file_size": 10485760,
                "backup_count": 3,
                "enable_console": True,
                "enable_file": True,
                "colored_output": True
            },
            "security": {
                "dry_run_mode": True,
                "enable_rate_limiting": False,
                "max_concurrent_accounts": 1,
                "require_confirmation": False,
                "backup_emails_before_move": False,
                "max_daily_emails": 50
            },
            "accounts": {
                "file": "config/accounts_dev.csv",
                "validate_domains": False,
                "require_app_passwords": False
            }
        }
    
    def _get_local_defaults(self) -> Dict[str, Any]:
        """Local development defaults (most permissive)"""
        return {
            "environment": "local",
            "proxy": {
                "provider": "none",
                "use_free_proxies": False,
                "direct_connection": True
            },
            "email": {
                "imap_host": "outlook.office365.com",
                "imap_port": 993,
                "max_emails_per_account": 5,
                "batch_size": 3,
                "connection_timeout": 10,
                "retry_attempts": 1
            },
            "behavior": {
                "enable_human_behavior": False,
                "fatigue_simulation": False,
                "min_delay_seconds": 0.5,
                "max_delay_seconds": 1.0,
                "distraction_probability": 0.0,
                "break_probability": 0.0,
                "inter_account_delay_min": 1.0,
                "inter_account_delay_max": 2.0
            },
            "logging": {
                "level": "DEBUG",
                "log_dir": "logs",
                "max_file_size": 5242880,
                "backup_count": 2,
                "enable_console": True,
                "enable_file": False,
                "colored_output": True
            },
            "security": {
                "dry_run_mode": True,
                "enable_rate_limiting": False,
                "max_concurrent_accounts": 1,
                "require_confirmation": False,
                "backup_emails_before_move": False,
                "max_daily_emails": 10
            },
            "accounts": {
                "file": "config/test_accounts.csv",
                "validate_domains": False,
                "require_app_passwords": False
            }
        }
    
    def get_proxy_config(self) -> ProxyConfig:
        """Get proxy configuration for current environment"""
        proxy_data = self._config_cache.get("proxy", {})
        
        return ProxyConfig(
            provider=proxy_data.get("provider", "none"),
            host=proxy_data.get("host", ""),
            port=proxy_data.get("port", 0),
            username=self._resolve_env_var(proxy_data.get("username")),
            password=self._resolve_env_var(proxy_data.get("password")),
            sticky_sessions=proxy_data.get("sticky_sessions", False),
            session_duration=proxy_data.get("session_duration", 30),
            use_free_proxies=proxy_data.get("use_free_proxies", False),
            free_proxy_config=proxy_data.get("free_proxy_config")
        )
    
    def get_email_config(self) -> EmailConfig:
        """Get email configuration for current environment"""
        email_data = self._config_cache.get("email", {})
        
        return EmailConfig(
            imap_host=email_data.get("imap_host", "outlook.office365.com"),
            imap_port=email_data.get("imap_port", 993),
            max_emails_per_account=email_data.get("max_emails_per_account", 10),
            batch_size=email_data.get("batch_size", 5),
            connection_timeout=email_data.get("connection_timeout", 10),
            retry_attempts=email_data.get("retry_attempts", 1)
        )
    
    def get_behavior_config(self) -> BehaviorConfig:
        """Get behavior configuration for current environment"""
        behavior_data = self._config_cache.get("behavior", {})
        
        return BehaviorConfig(
            enable_human_behavior=behavior_data.get("enable_human_behavior", False),
            fatigue_simulation=behavior_data.get("fatigue_simulation", False),
            min_delay_seconds=behavior_data.get("min_delay_seconds", 0.5),
            max_delay_seconds=behavior_data.get("max_delay_seconds", 1.0),
            distraction_probability=behavior_data.get("distraction_probability", 0.0),
            break_probability=behavior_data.get("break_probability", 0.0),
            inter_account_delay_min=behavior_data.get("inter_account_delay_min", 1.0),
            inter_account_delay_max=behavior_data.get("inter_account_delay_max", 2.0)
        )
    
    def get_logging_config(self) -> LoggingConfig:
        """Get logging configuration for current environment"""
        logging_data = self._config_cache.get("logging", {})
        
        return LoggingConfig(
            level=logging_data.get("level", "INFO"),
            log_dir=logging_data.get("log_dir", "logs"),
            max_file_size=logging_data.get("max_file_size", 10485760),
            backup_count=logging_data.get("backup_count", 3),
            enable_console=logging_data.get("enable_console", True),
            enable_file=logging_data.get("enable_file", True),
            colored_output=logging_data.get("colored_output", True)
        )
    
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration for current environment"""
        security_data = self._config_cache.get("security", {})
        
        return SecurityConfig(
            dry_run_mode=security_data.get("dry_run_mode", True),
            enable_rate_limiting=security_data.get("enable_rate_limiting", False),
            max_concurrent_accounts=security_data.get("max_concurrent_accounts", 1),
            require_confirmation=security_data.get("require_confirmation", False),
            backup_emails_before_move=security_data.get("backup_emails_before_move", False),
            max_daily_emails=security_data.get("max_daily_emails")
        )
    
    def get_accounts_file(self) -> str:
        """Get accounts file path for current environment"""
        accounts_data = self._config_cache.get("accounts", {})
        return accounts_data.get("file", "config/test_accounts.csv")
    
    def _resolve_env_var(self, value: str) -> Optional[str]:
        """Resolve environment variables in config values"""
        if not value or not isinstance(value, str):
            return value
        
        if value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.getenv(env_var)
        
        return value
    
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == Environment.PROD
    
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment in [Environment.DEV, Environment.LOCAL]
    
    def get_environment_info(self) -> Dict[str, Any]:
        """Get environment information"""
        return {
            "environment": self.environment.value,
            "config_file": os.path.join(self.config_dir, f'environment_{self.environment.value}.json'),
            "accounts_file": self.get_accounts_file(),
            "proxy_provider": self.get_proxy_config().provider,
            "dry_run_mode": self.get_security_config().dry_run_mode,
            "log_level": self.get_logging_config().level
        }
    
    def set_environment(self, environment: Environment):
        """Switch environment (useful for testing)"""
        self.environment = environment
        logger.info(f"🔄 Environment switched to: {environment.value.upper()}")
        self._load_environment_config()
    
    def validate_environment(self) -> bool:
        """Validate current environment configuration"""
        try:
            proxy_config = self.get_proxy_config()
            email_config = self.get_email_config()
            
            # Check accounts file exists
            accounts_file = self.get_accounts_file()
            if not os.path.exists(accounts_file):
                logger.error(f"❌ Accounts file not found: {accounts_file}")
                return False
            
            # Validate proxy config for production
            if self.is_production():
                if proxy_config.provider == "smartproxy" and (not proxy_config.username or not proxy_config.password):
                    logger.error("❌ Production requires valid SmartProxy credentials")
                    return False
            
            logger.info("✅ Environment configuration validated")
            return True
            
        except Exception as e:
            logger.error(f"❌ Environment validation failed: {e}")
            return False

def get_current_environment() -> EnvironmentConfig:
    """Get current environment configuration (singleton pattern)"""
    if not hasattr(get_current_environment, '_instance'):
        get_current_environment._instance = EnvironmentConfig()
    return get_current_environment._instance

def test_environment_config():
    """Test environment configuration system"""
    print("🧪 Test environment configuration...")
    
    # Test environment detection
    env_config = EnvironmentConfig()
    print(f"✅ Detected environment: {env_config.environment.value}")
    
    # Test configuration loading
    proxy_config = env_config.get_proxy_config()
    print(f"✅ Proxy config: {proxy_config.provider}")
    
    # Test environment switching
    env_config.set_environment(Environment.DEV)
    dev_config = env_config.get_security_config()
    print(f"✅ DEV dry_run: {dev_config.dry_run_mode}")
    
    # Test validation
    valid = env_config.validate_environment()
    print(f"✅ Validation: {valid}")
    
    print("✅ Environment configuration test passed!")

if __name__ == "__main__":
    test_environment_config()