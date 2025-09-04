"""
Simulation de 5 clients email différents pour anti-détection
Chaque client a ses propres headers, commandes IMAP et comportements
"""
import random
import re
from typing import Dict, List, Tuple
from logger import get_logger

logger = get_logger(__name__)

class EmailClient:
    """Représente un client email spécifique"""
    
    def __init__(self, name: str, user_agent: str, imap_id: Dict, 
                 headers: Dict, behaviors: Dict):
        self.name = name
        self.user_agent = user_agent
        self.imap_id = imap_id  # Pour commande IMAP ID
        self.headers = headers
        self.behaviors = behaviors
    
    def get_imap_commands(self) -> List[str]:
        """Retourne les commandes IMAP spécifiques au client"""
        commands = []
        
        # Commande ID (identification client)
        if self.imap_id:
            id_params = ' '.join([f'"{k}" "{v}"' for k, v in self.imap_id.items()])
            commands.append(f'ID ({id_params})')
        
        # Commandes spécifiques selon le client
        if 'initial_commands' in self.behaviors:
            commands.extend(self.behaviors['initial_commands'])
        
        return commands
    
    def get_folder_names(self) -> Dict[str, str]:
        """Noms de dossiers selon le client"""
        return self.behaviors.get('folder_names', {
            'spam': 'Junk',
            'inbox': 'INBOX',
            'sent': 'Sent',
            'drafts': 'Drafts'
        })
    
    def get_search_pattern(self) -> str:
        """Pattern de recherche spécifique au client"""
        return self.behaviors.get('search_pattern', 'ALL')

class ClientSimulator:
    """Simulateur de différents clients email"""
    
    def __init__(self):
        self.clients = self._initialize_clients()
        logger.info(f"📱 {len(self.clients)} clients email initialisés")
    
    def _initialize_clients(self) -> List[EmailClient]:
        """Initialise les 5 clients email différents"""
        
        clients = []
        
        # 1. OUTLOOK DESKTOP WINDOWS
        outlook_desktop = EmailClient(
            name="Outlook Desktop Windows",
            user_agent="Microsoft Outlook 16.0",
            imap_id={
                "name": "Microsoft Outlook",
                "version": "16.0.14326.20404",
                "os": "Windows",
                "os-version": "10.0.19042"
            },
            headers={
                "User-Agent": "Microsoft-MacOutlook/16.54.21101001",
                "X-Mailer": "Microsoft Outlook 16.0"
            },
            behaviors={
                'folder_names': {
                    'spam': 'Junk E-mail',  # Outlook spécifique
                    'inbox': 'Inbox',
                    'sent': 'Sent Items',
                    'drafts': 'Drafts'
                },
                'initial_commands': ['CAPABILITY', 'NAMESPACE'],
                'read_delay_base': 3.0,
                'batch_size': 50,
                'uses_idle': True
            }
        )
        clients.append(outlook_desktop)
        
        # 2. OUTLOOK WEB
        outlook_web = EmailClient(
            name="Outlook Web",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Outlook Web",
            imap_id={
                "name": "Outlook Web App",
                "version": "16.0.14326",
                "vendor": "Microsoft"
            },
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "X-MS-Exchange-Organization-OriginalArrivalTime": "true"
            },
            behaviors={
                'folder_names': {
                    'spam': 'Junk',
                    'inbox': 'Inbox',
                    'sent': 'SentItems',
                    'drafts': 'Drafts'
                },
                'initial_commands': ['ID NIL'],
                'read_delay_base': 2.5,
                'batch_size': 25,
                'uses_idle': False
            }
        )
        clients.append(outlook_web)
        
        # 3. OUTLOOK MOBILE iOS
        outlook_mobile = EmailClient(
            name="Outlook Mobile iOS",
            user_agent="Outlook-iOS/4.2148.0",
            imap_id={
                "name": "Outlook",
                "version": "4.2148.0",
                "os": "iOS",
                "os-version": "15.6",
                "device": "iPhone"
            },
            headers={
                "User-Agent": "Outlook-iOS/4.2148.0",
                "X-MS-Exchange-Organization-Mobile": "iPhone"
            },
            behaviors={
                'folder_names': {
                    'spam': 'Junk',
                    'inbox': 'Inbox',
                    'sent': 'Sent',
                    'drafts': 'Drafts'
                },
                'initial_commands': ['CAPABILITY'],
                'read_delay_base': 4.0,  # Mobile plus lent
                'batch_size': 10,  # Petits batches mobile
                'uses_idle': True,
                'mobile_optimized': True
            }
        )
        clients.append(outlook_mobile)
        
        # 4. THUNDERBIRD
        thunderbird = EmailClient(
            name="Mozilla Thunderbird",
            user_agent="Thunderbird/91.13.0",
            imap_id={
                "name": "Thunderbird",
                "version": "91.13.0",
                "vendor": "Mozilla",
                "support-url": "https://support.mozilla.org/kb/thunderbird"
            },
            headers={
                "User-Agent": "Mozilla Thunderbird 91.13.0",
                "X-Mailer": "Mozilla Thunderbird"
            },
            behaviors={
                'folder_names': {
                    'spam': 'Junk',
                    'inbox': 'INBOX',
                    'sent': 'Sent',
                    'drafts': 'Drafts'
                },
                'initial_commands': ['CAPABILITY', 'NAMESPACE', 'LIST "" "*"'],
                'read_delay_base': 2.0,
                'batch_size': 100,  # Thunderbird plus efficace
                'uses_idle': True,
                'supports_condstore': True
            }
        )
        clients.append(thunderbird)
        
        # 5. APPLE MAIL
        apple_mail = EmailClient(
            name="Apple Mail",
            user_agent="Mail/3654.120.0.1.13",
            imap_id={
                "name": "Mail",
                "version": "16.0",
                "vendor": "Apple Inc.",
                "os": "Mac OS X",
                "os-version": "12.6"
            },
            headers={
                "User-Agent": "Mail/3654.120.0.1.13 CFNetwork/1333.0.4 Darwin/21.6.0",
                "X-Mailer": "Apple Mail (2.3654.120.0.1.13)"
            },
            behaviors={
                'folder_names': {
                    'spam': 'Junk',
                    'inbox': 'INBOX',
                    'sent': 'Sent Messages',
                    'drafts': 'Drafts'
                },
                'initial_commands': ['CAPABILITY', 'ID NIL'],
                'read_delay_base': 2.8,
                'batch_size': 30,
                'uses_idle': True,
                'apple_extensions': True
            }
        )
        clients.append(apple_mail)
        
        return clients
    
    def get_random_client(self) -> EmailClient:
        """Sélectionne un client aléatoire avec pondération réaliste"""
        # Pondération basée sur l'usage réel
        weights = {
            "Outlook Desktop Windows": 0.35,  # Plus utilisé en entreprise
            "Outlook Web": 0.25,              # Très populaire
            "Outlook Mobile iOS": 0.20,       # Usage mobile
            "Mozilla Thunderbird": 0.15,      # Utilisateurs avancés
            "Apple Mail": 0.05               # Moins courant pour Outlook/Hotmail
        }
        
        client_names = list(weights.keys())
        client_weights = list(weights.values())
        
        selected_name = random.choices(client_names, weights=client_weights)[0]
        selected_client = next(c for c in self.clients if c.name == selected_name)
        
        logger.info(f"📱 Client sélectionné: {selected_client.name}")
        return selected_client
    
    def get_client_by_name(self, name: str) -> EmailClient:
        """Récupère un client spécifique par nom"""
        for client in self.clients:
            if client.name.lower() == name.lower():
                return client
        
        logger.warning(f"⚠️ Client '{name}' non trouvé, retour client aléatoire")
        return self.get_random_client()
    
    def simulate_client_behavior(self, client: EmailClient, action: str) -> Dict:
        """Simule le comportement spécifique d'un client"""
        behavior = {
            'client_name': client.name,
            'action': action,
            'base_delay': client.behaviors.get('read_delay_base', 3.0)
        }
        
        if action == 'connect':
            behavior['commands'] = client.get_imap_commands()
            behavior['delay'] = random.uniform(1.0, 3.0)
            
        elif action == 'read_email':
            base_delay = client.behaviors.get('read_delay_base', 3.0)
            # Délai aléatoire basé sur le client
            behavior['delay'] = random.uniform(base_delay * 0.8, base_delay * 1.5)
            behavior['batch_size'] = client.behaviors.get('batch_size', 25)
            
        elif action == 'move_email':
            behavior['delay'] = random.uniform(0.5, 2.0)
            behavior['folder_names'] = client.get_folder_names()
            
        elif action == 'disconnect':
            behavior['delay'] = random.uniform(0.5, 1.5)
            behavior['graceful'] = True
        
        return behavior
    
    def get_realistic_usage_pattern(self) -> Dict:
        """Retourne un pattern d'usage réaliste pour la session"""
        patterns = [
            {
                'name': 'morning_check',
                'description': 'Vérification matinale rapide',
                'read_speed': 1.2,
                'thorough': False,
                'batch_processing': True
            },
            {
                'name': 'lunch_break',
                'description': 'Consultation pause déjeuner',
                'read_speed': 0.8,
                'thorough': True,
                'batch_processing': False
            },
            {
                'name': 'end_of_day',
                'description': 'Nettoyage fin de journée',
                'read_speed': 1.5,
                'thorough': False,
                'batch_processing': True
            },
            {
                'name': 'weekend_cleanup',
                'description': 'Grand nettoyage weekend',
                'read_speed': 0.6,
                'thorough': True,
                'batch_processing': False
            }
        ]
        
        pattern = random.choice(patterns)
        logger.debug(f"📋 Pattern d'usage: {pattern['description']}")
        return pattern

def test_client_simulation():
    """Test simple de la simulation de clients"""
    print("🧪 Test simulation clients...")
    
    simulator = ClientSimulator()
    
    # Test sélection client
    client = simulator.get_random_client()
    print(f"✅ Client sélectionné: {client.name}")
    
    # Test comportement
    behavior = simulator.simulate_client_behavior(client, 'read_email')
    print(f"✅ Comportement simulé: {behavior}")
    
    # Test pattern usage
    pattern = simulator.get_realistic_usage_pattern()
    print(f"✅ Pattern usage: {pattern['description']}")
    
    print("✅ Tous les tests client simulation passés!")

if __name__ == "__main__":
    test_client_simulation()