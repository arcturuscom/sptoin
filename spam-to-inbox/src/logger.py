"""
Système de logging avancé avec rotation et multiple niveaux
Logs détaillés pour debugging et monitoring des opérations
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional
import colorlog

class CustomFormatter(colorlog.ColoredFormatter):
    """Formateur personnalisé avec couleurs et émojis"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Mapping émojis par niveau
        self.emoji_mapping = {
            'DEBUG': '🔧',
            'INFO': '📄',
            'WARNING': '⚠️',
            'ERROR': '❌',
            'CRITICAL': '🚨'
        }
    
    def format(self, record):
        # Ajouter émoji selon le niveau
        if hasattr(record, 'levelname'):
            emoji = self.emoji_mapping.get(record.levelname, '📄')
            record.emoji = emoji
        
        # Format de base avec couleurs
        formatted = super().format(record)
        
        return formatted

def setup_logging(log_level: str = 'INFO', 
                  log_dir: str = 'logs',
                  enable_console: bool = True,
                  enable_file: bool = True,
                  max_file_size: int = 10 * 1024 * 1024,  # 10MB
                  backup_count: int = 5) -> logging.Logger:
    """
    Configure le système de logging complet
    """
    
    # Créer le répertoire logs si nécessaire
    if enable_file and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    
    # Configuration du logger principal
    logger = logging.getLogger('spam-to-inbox')
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Éviter la duplication des handlers
    if logger.handlers:
        logger.handlers.clear()
    
    # Formateur pour console (avec couleurs et émojis)
    console_formatter = CustomFormatter(
        fmt='%(emoji)s %(log_color)s%(levelname)-8s%(reset)s | %(cyan)s%(asctime)s%(reset)s | %(name)s:%(lineno)d | %(message)s',
        datefmt='%H:%M:%S',
        log_colors={
            'DEBUG': 'blue',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )
    
    # Formateur pour fichier (sans couleurs)
    file_formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler console
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # Handler fichier avec rotation
    if enable_file:
        log_filename = os.path.join(log_dir, 'spam-to-inbox.log')
        file_handler = logging.handlers.RotatingFileHandler(
            log_filename,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Log spécialisés par module
        _setup_specialized_logs(log_dir, file_formatter, max_file_size, backup_count)
    
    return logger

def _setup_specialized_logs(log_dir: str, formatter: logging.Formatter,
                           max_size: int, backup_count: int):
    """Configure des logs spécialisés par composant"""
    
    specialized_logs = [
        ('proxy_manager', 'proxy.log'),
        ('email_processor', 'email.log'),
        ('anti_detection', 'behavior.log'),
        ('client_simulator', 'client.log')
    ]
    
    for logger_name, filename in specialized_logs:
        spec_logger = logging.getLogger(logger_name)
        
        if not spec_logger.handlers:  # Éviter duplication
            file_path = os.path.join(log_dir, filename)
            handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=max_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            handler.setFormatter(formatter)
            spec_logger.addHandler(handler)
            spec_logger.setLevel(logging.DEBUG)

def get_logger(name: str) -> logging.Logger:
    """
    Récupère un logger configuré pour un module
    """
    # Si c'est un nom de module complet, extraire le nom court
    if '.' in name:
        name = name.split('.')[-1]
    
    return logging.getLogger(name)

def log_session_start(email: str, client_name: str, proxy_session: str):
    """Log spécial pour début de session"""
    logger = get_logger('session')
    logger.info(f"🚀 SESSION START | Email: {email} | Client: {client_name} | Proxy: {proxy_session}")

def log_session_end(email: str, success_count: int, fail_count: int, duration: float):
    """Log spécial pour fin de session"""
    logger = get_logger('session')
    logger.info(f"🏁 SESSION END | Email: {email} | Réussis: {success_count} | Échecs: {fail_count} | Durée: {duration:.1f}s")

def log_proxy_sticky_session(email: str, session_id: str, action: str):
    """Log spécial pour suivi des sessions sticky"""
    logger = get_logger('proxy_manager')
    logger.info(f"🔗 STICKY SESSION | {action} | Email: {email} | Session: {session_id}")

def log_email_operation(operation: str, email_count: int, folder_from: str = None, folder_to: str = None):
    """Log spécial pour opérations email"""
    logger = get_logger('email_processor')
    if folder_from and folder_to:
        logger.info(f"📧 {operation} | {email_count} emails | {folder_from} → {folder_to}")
    else:
        logger.info(f"📧 {operation} | {email_count} emails")

def log_behavior_action(action: str, delay: float, context: dict = None):
    """Log spécial pour actions comportementales"""
    logger = get_logger('anti_detection')
    context_str = f" | Context: {context}" if context else ""
    logger.debug(f"🧠 {action} | Délai: {delay:.2f}s{context_str}")

def log_error_with_context(module: str, error: Exception, context: dict = None):
    """Log d'erreur enrichi avec contexte"""
    logger = get_logger(module)
    context_str = f" | Context: {context}" if context else ""
    logger.error(f"❌ {type(error).__name__}: {str(error)}{context_str}", exc_info=True)

def create_session_summary(stats: dict) -> str:
    """Crée un résumé de session pour les logs"""
    summary = f"""
📊 RÉSUMÉ SESSION
===============
• Durée totale: {stats.get('duration', 0):.1f}s
• Comptes traités: {stats.get('accounts_processed', 0)}
• Emails déplacés: {stats.get('emails_moved', 0)}
• Erreurs: {stats.get('errors', 0)}
• Proxies utilisés: {stats.get('unique_sessions', 0)}
• Efficacité: {stats.get('success_rate', 0):.1f}%
==============="""
    return summary

def setup_debug_logging():
    """Configuration logging pour debugging intensif"""
    logger = setup_logging(
        log_level='DEBUG',
        enable_console=True,
        enable_file=True
    )
    
    # Ajout handler pour logs très détaillés
    debug_logger = logging.getLogger('debug')
    debug_handler = logging.FileHandler('logs/debug_detailed.log', encoding='utf-8')
    debug_formatter = logging.Formatter(
        '%(asctime)s.%(msecs)03d | %(levelname)s | %(name)s:%(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    debug_handler.setFormatter(debug_formatter)
    debug_logger.addHandler(debug_handler)
    debug_logger.setLevel(logging.DEBUG)
    
    logger.info("🔧 Mode debug détaillé activé")
    return logger

def cleanup_old_logs(log_dir: str = 'logs', max_age_days: int = 30):
    """Nettoie les anciens fichiers de log"""
    if not os.path.exists(log_dir):
        return
    
    import time
    current_time = time.time()
    max_age_seconds = max_age_days * 24 * 3600
    
    cleaned_count = 0
    
    for filename in os.listdir(log_dir):
        if filename.endswith('.log') or filename.endswith('.log.1'):
            file_path = os.path.join(log_dir, filename)
            try:
                file_age = current_time - os.path.getctime(file_path)
                if file_age > max_age_seconds:
                    os.remove(file_path)
                    cleaned_count += 1
            except Exception as e:
                logger = get_logger('cleanup')
                logger.warning(f"Erreur nettoyage {filename}: {e}")
    
    if cleaned_count > 0:
        logger = get_logger('cleanup')
        logger.info(f"🧹 {cleaned_count} anciens fichiers log supprimés")

# Configuration par défaut au chargement du module
default_logger = setup_logging()

def test_logging():
    """Test du système de logging"""
    print("🧪 Test système de logging...")
    
    # Test différents niveaux
    logger = get_logger('test')
    
    logger.debug("Test message DEBUG")
    logger.info("Test message INFO")
    logger.warning("Test message WARNING")
    logger.error("Test message ERROR")
    
    # Test logs spécialisés
    log_session_start("test@hotmail.com", "Outlook Desktop", "session-abc123")
    log_email_operation("MOVE", 5, "Junk", "Inbox")
    log_behavior_action("read_email", 2.5, {"size": 1500})
    log_session_end("test@hotmail.com", 5, 0, 45.2)
    
    print("✅ Test logging complet passé!")

if __name__ == "__main__":
    test_logging()