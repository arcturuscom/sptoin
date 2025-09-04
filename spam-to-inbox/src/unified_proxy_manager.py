"""
Unified Proxy Manager - Environment-aware proxy management
Supports SmartProxy, Free Proxies, and Direct connection based on environment
"""
from typing import Dict, Optional
from abc import ABC, abstractmethod
from environment_config import EnvironmentConfig, ProxyConfig
from proxy_manager import ProxyManager
from free_proxy_manager import FreeProxyManager
from logger import get_logger

logger = get_logger(__name__)

class BaseProxyManager(ABC):
    """Abstract base class for proxy managers"""
    
    @abstractmethod
    def get_proxy_for_account(self, email: str) -> Dict:
        """Get proxy configuration for account"""
        pass
    
    @abstractmethod
    def end_session(self, email: str):
        """End proxy session for account"""
        pass
    
    @abstractmethod
    def get_proxy_stats(self) -> Dict:
        """Get proxy manager statistics"""
        pass

class DirectConnectionManager(BaseProxyManager):
    """Direct connection manager (no proxy)"""
    
    def __init__(self):
        self.sessions = {}
        logger.info("🔄 Direct connection manager initialized")
    
    def get_proxy_for_account(self, email: str) -> Dict:
        """Return direct connection config"""
        session_id = f"direct-{hash(email)}"
        self.sessions[email] = session_id
        
        return {
            'host': None,
            'port': None,
            'user': None,
            'pass': None,
            'type': 'direct',
            'session_id': session_id,
            'provider': 'direct'
        }
    
    def end_session(self, email: str):
        """End direct session"""
        if email in self.sessions:
            del self.sessions[email]
            logger.debug(f"🔚 Direct session ended for {email}")
    
    def get_proxy_stats(self) -> Dict:
        """Get direct connection stats"""
        return {
            'provider': 'direct',
            'active_sessions': len(self.sessions),
            'connection_type': 'direct'
        }

class UnifiedProxyManager:
    """
    Unified proxy manager that selects appropriate proxy provider
    based on environment configuration
    """
    
    def __init__(self, env_config: EnvironmentConfig):
        self.env_config = env_config
        self.proxy_config = env_config.get_proxy_config()
        self.manager = None
        
        self._initialize_proxy_manager()
    
    def _initialize_proxy_manager(self):
        """Initialize appropriate proxy manager based on configuration"""
        provider = self.proxy_config.provider.lower()
        
        logger.info(f"🌐 Initializing proxy manager: {provider}")
        
        try:
            if provider == "smartproxy":
                self.manager = self._create_smartproxy_manager()
            elif provider == "free":
                self.manager = self._create_free_proxy_manager()
            elif provider in ["none", "direct"]:
                self.manager = DirectConnectionManager()
            else:
                logger.warning(f"⚠️ Unknown proxy provider: {provider}, falling back to direct")
                self.manager = DirectConnectionManager()
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize proxy manager: {e}")
            logger.info("🔄 Falling back to direct connection")
            self.manager = DirectConnectionManager()
    
    def _create_smartproxy_manager(self) -> ProxyManager:
        """Create SmartProxy manager with environment configuration"""
        if not self.proxy_config.username or not self.proxy_config.password:
            raise ValueError("SmartProxy requires username and password")
        
        manager = ProxyManager(
            username=self.proxy_config.username,
            password=self.proxy_config.password
        )
        
        logger.info(f"✅ SmartProxy manager initialized: {self.proxy_config.username}")
        return manager
    
    def _create_free_proxy_manager(self) -> FreeProxyManager:
        """Create free proxy manager with environment configuration"""
        if self.proxy_config.free_proxy_config:
            manager = FreeProxyManager(self.proxy_config.free_proxy_config)
        else:
            logger.warning("⚠️ No free proxy config specified, using test instance")
            manager = FreeProxyManager.create_test_instance()
        
        logger.info("✅ Free proxy manager initialized")
        return manager
    
    def get_proxy_for_account(self, email: str) -> Dict:
        """Get proxy for account using configured provider"""
        try:
            proxy = self.manager.get_proxy_for_account(email)
            
            # Add environment metadata
            proxy['environment'] = self.env_config.environment.value
            proxy['provider_type'] = self.proxy_config.provider
            
            logger.debug(f"🌐 Proxy assigned to {email}: {proxy.get('provider', 'unknown')}")
            return proxy
            
        except Exception as e:
            logger.error(f"❌ Failed to get proxy for {email}: {e}")
            
            # Fallback to direct connection
            logger.info("🔄 Falling back to direct connection")
            fallback_manager = DirectConnectionManager()
            return fallback_manager.get_proxy_for_account(email)
    
    def end_session(self, email: str):
        """End proxy session"""
        try:
            self.manager.end_session(email)
        except Exception as e:
            logger.error(f"❌ Error ending session for {email}: {e}")
    
    def get_proxy_stats(self) -> Dict:
        """Get comprehensive proxy statistics"""
        try:
            base_stats = self.manager.get_proxy_stats()
            
            # Add environment information
            base_stats.update({
                'environment': self.env_config.environment.value,
                'provider': self.proxy_config.provider,
                'sticky_sessions': self.proxy_config.sticky_sessions,
                'session_duration': self.proxy_config.session_duration
            })
            
            return base_stats
            
        except Exception as e:
            logger.error(f"❌ Error getting proxy stats: {e}")
            return {'error': str(e)}
    
    def test_connectivity(self) -> bool:
        """Test proxy connectivity"""
        try:
            # Test with a dummy email
            test_proxy = self.get_proxy_for_account("connectivity-test@test.com")
            
            if test_proxy.get('type') == 'direct':
                logger.info("✅ Direct connection test passed")
                result = True
            elif hasattr(self.manager, 'test_connectivity'):
                result = self.manager.test_connectivity()
            else:
                # Basic connectivity test
                result = test_proxy is not None
            
            # Clean up test session
            self.end_session("connectivity-test@test.com")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Connectivity test failed: {e}")
            return False
    
    def refresh_proxies(self):
        """Refresh proxy list (if supported by provider)"""
        if hasattr(self.manager, 'refresh_proxies'):
            logger.info("🔄 Refreshing proxy list...")
            self.manager.refresh_proxies()
        else:
            logger.info("ℹ️ Proxy refresh not supported by current provider")
    
    def switch_provider(self, new_provider: str):
        """Switch to different proxy provider (runtime switching)"""
        logger.info(f"🔄 Switching proxy provider to: {new_provider}")
        
        # Update configuration
        old_provider = self.proxy_config.provider
        self.proxy_config.provider = new_provider
        
        try:
            # Re-initialize with new provider
            self._initialize_proxy_manager()
            logger.info(f"✅ Switched from {old_provider} to {new_provider}")
            
        except Exception as e:
            logger.error(f"❌ Failed to switch provider: {e}")
            # Revert to old provider
            self.proxy_config.provider = old_provider
            self._initialize_proxy_manager()
            raise
    
    def get_provider_info(self) -> Dict:
        """Get detailed provider information"""
        return {
            'provider': self.proxy_config.provider,
            'environment': self.env_config.environment.value,
            'sticky_sessions': self.proxy_config.sticky_sessions,
            'host': getattr(self.proxy_config, 'host', None),
            'port': getattr(self.proxy_config, 'port', None),
            'use_free_proxies': self.proxy_config.use_free_proxies,
            'manager_type': type(self.manager).__name__
        }

def create_proxy_manager(env_config: EnvironmentConfig = None) -> UnifiedProxyManager:
    """Factory function to create unified proxy manager"""
    if env_config is None:
        from environment_config import get_current_environment
        env_config = get_current_environment()
    
    return UnifiedProxyManager(env_config)

def test_unified_proxy_manager():
    """Test unified proxy manager with different environments"""
    print("🧪 Test unified proxy manager...")
    
    from environment_config import EnvironmentConfig, Environment
    
    # Test with LOCAL environment (direct connection)
    print("\n📍 Testing LOCAL environment...")
    local_env = EnvironmentConfig(Environment.LOCAL)
    local_manager = UnifiedProxyManager(local_env)
    
    proxy = local_manager.get_proxy_for_account("test@local.com")
    print(f"✅ Local proxy: {proxy['type']}")
    
    stats = local_manager.get_proxy_stats()
    print(f"✅ Local stats: {stats}")
    
    # Test with DEV environment (free proxies)
    print("\n🛠️ Testing DEV environment...")
    dev_env = EnvironmentConfig(Environment.DEV)
    dev_manager = UnifiedProxyManager(dev_env)
    
    proxy = dev_manager.get_proxy_for_account("test@dev.com")
    print(f"✅ Dev proxy: {proxy.get('provider_type', 'unknown')}")
    
    # Test provider switching
    print("\n🔄 Testing provider switching...")
    dev_manager.switch_provider("direct")
    proxy = dev_manager.get_proxy_for_account("test@switched.com")
    print(f"✅ Switched proxy: {proxy['type']}")
    
    # Test connectivity
    print("\n🌐 Testing connectivity...")
    connectivity = dev_manager.test_connectivity()
    print(f"✅ Connectivity: {connectivity}")
    
    print("\n✅ Unified proxy manager test passed!")

if __name__ == "__main__":
    test_unified_proxy_manager()