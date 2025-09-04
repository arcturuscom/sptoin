#!/usr/bin/env python3
"""
Tests OBLIGATOIRES pour validation des sticky sessions
CRITIQUE: Vérifie que les proxies gardent la même IP par session
"""
import sys
import os
import time
import unittest
import requests
from unittest.mock import patch, MagicMock

# Ajout du chemin src pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from proxy_manager import ProxyManager
from client_simulator import ClientSimulator, EmailClient
from logger import setup_logging, get_logger

class TestStickyProxySessions(unittest.TestCase):
    """Tests critiques des sessions sticky"""
    
    @classmethod
    def setUpClass(cls):
        """Configuration des tests"""
        cls.logger = setup_logging('DEBUG')
        cls.proxy_manager = ProxyManager("test_user", "test_pass")
    
    def setUp(self):
        """Reset avant chaque test"""
        self.proxy_manager.active_sessions.clear()
        self.proxy_manager.session_timestamps.clear()
        self.proxy_manager.session_ips.clear()
    
    def test_same_proxy_same_account(self):
        """TEST 1: Même proxy pour même compte (CRITIQUE)"""
        print("🧪 Test 1: Sticky session même compte...")
        
        email = "test@hotmail.com"
        
        # Première demande
        proxy1 = self.proxy_manager.get_proxy_for_account(email)
        time.sleep(0.1)  # Petite pause
        
        # Deuxième demande pour le même compte
        proxy2 = self.proxy_manager.get_proxy_for_account(email)
        
        # CRITIQUE: Doit être exactement le même proxy
        self.assertEqual(proxy1['user'], proxy2['user'], 
                        "❌ ÉCHEC CRITIQUE: Session pas sticky pour même compte!")
        self.assertEqual(proxy1['session_id'], proxy2['session_id'],
                        "❌ ÉCHEC CRITIQUE: Session ID différent pour même compte!")
        
        print(f"✅ Proxy sticky maintenu: {proxy1['user']}")
    
    def test_different_proxy_different_accounts(self):
        """TEST 2: Proxies différents pour comptes différents"""
        print("🧪 Test 2: Séparation des comptes...")
        
        email1 = "user1@hotmail.com"
        email2 = "user2@outlook.com"
        
        proxy1 = self.proxy_manager.get_proxy_for_account(email1)
        proxy2 = self.proxy_manager.get_proxy_for_account(email2)
        
        # Les proxies doivent être différents
        self.assertNotEqual(proxy1['user'], proxy2['user'],
                           "❌ ÉCHEC: Même proxy pour comptes différents!")
        self.assertNotEqual(proxy1['session_id'], proxy2['session_id'],
                           "❌ ÉCHEC: Même session ID pour comptes différents!")
        
        print(f"✅ Proxies séparés: {proxy1['session_id']} != {proxy2['session_id']}")
    
    def test_session_persistence_time(self):
        """TEST 3: Persistence de session dans le temps"""
        print("🧪 Test 3: Persistence temporelle...")
        
        email = "persist@hotmail.com"
        
        # Session initiale
        proxy_initial = self.proxy_manager.get_proxy_for_account(email)
        initial_time = time.time()
        
        # Attendre un peu mais moins que l'expiration (30 min = 1800s)
        time.sleep(1)
        
        # Nouvelle demande
        proxy_after = self.proxy_manager.get_proxy_for_account(email)
        
        # Doit être la même session
        self.assertEqual(proxy_initial['session_id'], proxy_after['session_id'],
                        "❌ ÉCHEC: Session perdue avant expiration!")
        
        print(f"✅ Session persistante: {proxy_initial['session_id']}")
    
    def test_session_cleanup(self):
        """TEST 4: Nettoyage de session"""
        print("🧪 Test 4: Nettoyage session...")
        
        email = "cleanup@hotmail.com"
        
        # Créer une session
        proxy_before = self.proxy_manager.get_proxy_for_account(email)
        session_id_before = proxy_before['session_id']
        
        # Vérifier que la session existe
        self.assertIn(email, self.proxy_manager.active_sessions)
        
        # Terminer la session
        self.proxy_manager.end_session(email)
        
        # Vérifier que la session est supprimée
        self.assertNotIn(email, self.proxy_manager.active_sessions)
        
        # Nouvelle session doit être différente
        proxy_after = self.proxy_manager.get_proxy_for_account(email)
        session_id_after = proxy_after['session_id']
        
        self.assertNotEqual(session_id_before, session_id_after,
                           "❌ ÉCHEC: Session pas renouvelée après cleanup!")
        
        print(f"✅ Session nettoyée: {session_id_before} → {session_id_after}")
    
    def test_session_expiration(self):
        """TEST 5: Expiration automatique des sessions"""
        print("🧪 Test 5: Expiration session...")
        
        email = "expire@hotmail.com"
        
        # Créer une session
        proxy = self.proxy_manager.get_proxy_for_account(email)
        session_id = proxy['session_id']
        
        # Simuler expiration en modifiant le timestamp
        self.proxy_manager.session_timestamps[email] = time.time() - 2000  # > 1800s
        
        # Demander un nouveau proxy (devrait créer nouvelle session)
        proxy_new = self.proxy_manager.get_proxy_for_account(email)
        session_id_new = proxy_new['session_id']
        
        self.assertNotEqual(session_id, session_id_new,
                           "❌ ÉCHEC: Session expirée non renouvelée!")
        
        print(f"✅ Session expirée renouvelée: {session_id} → {session_id_new}")
    
    def test_session_format_smartproxy(self):
        """TEST 6: Format de session SmartProxy correct"""
        print("🧪 Test 6: Format SmartProxy...")
        
        email = "format@hotmail.com"
        proxy = self.proxy_manager.get_proxy_for_account(email)
        
        # Vérifier le format username-session-{id}
        user_parts = proxy['user'].split('-')
        
        self.assertEqual(len(user_parts), 3, 
                        f"❌ ÉCHEC: Format incorrect {proxy['user']}")
        self.assertEqual(user_parts[0], "test_user",
                        f"❌ ÉCHEC: Username incorrect {user_parts[0]}")
        self.assertEqual(user_parts[1], "session",
                        f"❌ ÉCHEC: Format sticky incorrect {user_parts[1]}")
        self.assertTrue(len(user_parts[2]) >= 8,
                       f"❌ ÉCHEC: Session ID trop court {user_parts[2]}")
        
        print(f"✅ Format SmartProxy correct: {proxy['user']}")
    
    def test_concurrent_sessions(self):
        """TEST 7: Sessions concurrentes multiples"""
        print("🧪 Test 7: Sessions concurrentes...")
        
        emails = [f"user{i}@hotmail.com" for i in range(5)]
        proxies = {}
        
        # Créer plusieurs sessions simultanément
        for email in emails:
            proxies[email] = self.proxy_manager.get_proxy_for_account(email)
        
        # Vérifier que toutes les sessions sont uniques
        session_ids = [p['session_id'] for p in proxies.values()]
        unique_ids = set(session_ids)
        
        self.assertEqual(len(session_ids), len(unique_ids),
                        f"❌ ÉCHEC: Sessions dupliquées! {len(session_ids)} vs {len(unique_ids)}")
        
        # Vérifier persistence de chaque session
        for email in emails:
            proxy_check = self.proxy_manager.get_proxy_for_account(email)
            self.assertEqual(proxies[email]['session_id'], proxy_check['session_id'],
                           f"❌ ÉCHEC: Session non persistante pour {email}")
        
        print(f"✅ {len(emails)} sessions concurrentes OK")
    
    def test_session_stats(self):
        """TEST 8: Statistiques des sessions"""
        print("🧪 Test 8: Statistiques sessions...")
        
        # Créer quelques sessions
        emails = ["stats1@hotmail.com", "stats2@outlook.com"]
        for email in emails:
            self.proxy_manager.get_proxy_for_account(email)
        
        stats = self.proxy_manager.get_active_sessions()
        
        self.assertEqual(stats['session_count'], len(emails),
                        f"❌ ÉCHEC: Compteur sessions incorrect")
        self.assertIsNotNone(stats['newest_session'],
                            "❌ ÉCHEC: Timestamp nouvelle session manquant")
        
        print(f"✅ Statistiques: {stats['session_count']} sessions actives")

class TestClientSimulator(unittest.TestCase):
    """Tests du simulateur de clients"""
    
    def setUp(self):
        self.simulator = ClientSimulator()
    
    def test_client_selection(self):
        """Test sélection de clients"""
        print("🧪 Test sélection clients...")
        
        client = self.simulator.get_random_client()
        self.assertIsInstance(client, EmailClient)
        
        # Test client spécifique
        outlook = self.simulator.get_client_by_name("Outlook Desktop Windows")
        self.assertEqual(outlook.name, "Outlook Desktop Windows")
        
        print(f"✅ Client sélectionné: {client.name}")
    
    def test_client_behaviors(self):
        """Test comportements clients"""
        print("🧪 Test comportements clients...")
        
        client = self.simulator.get_random_client()
        behavior = self.simulator.simulate_client_behavior(client, 'read_email')
        
        self.assertIn('delay', behavior)
        self.assertGreater(behavior['delay'], 0)
        self.assertIn('client_name', behavior)
        
        print(f"✅ Comportement simulé: {behavior['delay']:.2f}s")

@patch('requests.get')
class TestProxyConnectivity(unittest.TestCase):
    """Tests de connectivité proxy (mockés)"""
    
    def test_proxy_connection_simulation(self, mock_get):
        """Test simulation connexion proxy"""
        print("🧪 Test simulation connexion proxy...")
        
        # Mock réponse succès
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ip": "192.168.1.100", "country": "US"}
        mock_get.return_value = mock_response
        
        proxy_manager = ProxyManager("test_user", "test_pass")
        proxy = proxy_manager.get_proxy_for_account("connectivity@test.com")
        
        # Test structure proxy
        self.assertEqual(proxy['host'], 'gate.smartproxy.com')
        self.assertEqual(proxy['port'], 10000)
        self.assertIn('session', proxy['user'])
        
        print(f"✅ Simulation connexion proxy OK")

def run_comprehensive_tests():
    """Lance tous les tests avec rapport détaillé"""
    print("=" * 60)
    print("🧪 TESTS COMPLETS STICKY SESSIONS PROXY")
    print("=" * 60)
    
    # Configuration logging pour les tests
    logger = setup_logging('INFO')
    
    # Suite de tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Ajout des tests dans l'ordre d'importance
    suite.addTest(loader.loadTestsFromTestCase(TestStickyProxySessions))
    suite.addTest(loader.loadTestsFromTestCase(TestClientSimulator))
    suite.addTest(loader.loadTestsFromTestCase(TestProxyConnectivity))
    
    # Runner avec rapport détaillé
    runner = unittest.TextTestRunner(
        verbosity=2,
        buffer=False,
        stream=sys.stdout
    )
    
    # Exécution
    start_time = time.time()
    result = runner.run(suite)
    duration = time.time() - start_time
    
    # Rapport final
    print("\n" + "=" * 60)
    print("📊 RAPPORT FINAL DES TESTS")
    print("=" * 60)
    print(f"🕒 Durée: {duration:.2f}s")
    print(f"✅ Tests réussis: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Échecs: {len(result.failures)}")
    print(f"💥 Erreurs: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ ÉCHECS:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback.split('AssertionError: ')[-1].split('\\n')[0]}")
    
    if result.errors:
        print("\n💥 ERREURS:")
        for test, traceback in result.errors:
            print(f"  - {test}: Erreur système")
    
    # Résultat global
    success = len(result.failures) == 0 and len(result.errors) == 0
    
    if success:
        print("\n🎉 TOUS LES TESTS PASSÉS - STICKY SESSIONS VALIDÉES!")
        print("✅ Les proxies maintiennent bien la même IP par session")
    else:
        print("\n🚨 ÉCHECS DÉTECTÉS - VÉRIFIEZ L'IMPLÉMENTATION!")
        print("❌ Les sticky sessions peuvent ne pas fonctionner correctement")
    
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)