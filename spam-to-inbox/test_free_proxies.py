#!/usr/bin/env python3
"""
Utilitaire de test pour proxies gratuits
Permet de tester et valider les proxies avant utilisation
"""
import requests
import time
import json
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

# Ajout du chemin src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from free_proxy_manager import FreeProxyManager
from logger import setup_logging, get_logger

class FreeProxyTester:
    """Testeur de proxies gratuits avec utilitaires"""
    
    def __init__(self, log_level='INFO'):
        self.logger = setup_logging(log_level)
        self.test_urls = [
            'https://httpbin.org/ip',
            'https://api.ipify.org?format=json',
            'https://ifconfig.me/ip'
        ]
        
    def test_single_proxy(self, host: str, port: int, timeout: int = 10) -> Dict:
        """Test un proxy individuel avec détails"""
        proxy_url = f"http://{host}:{port}"
        result = {
            'host': host,
            'port': port,
            'working': False,
            'response_time': None,
            'detected_ip': None,
            'error': None,
            'test_url_used': None
        }
        
        for test_url in self.test_urls:
            try:
                start_time = time.time()
                response = requests.get(
                    test_url,
                    proxies={'http': proxy_url, 'https': proxy_url},
                    timeout=timeout,
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                )
                
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    result['working'] = True
                    result['response_time'] = response_time
                    result['test_url_used'] = test_url
                    
                    # Extraire IP détectée
                    if 'httpbin.org' in test_url:
                        data = response.json()
                        result['detected_ip'] = data.get('origin', 'Unknown')
                    elif 'ipify.org' in test_url:
                        data = response.json()
                        result['detected_ip'] = data.get('ip', 'Unknown')
                    else:
                        result['detected_ip'] = response.text.strip()
                    
                    break  # Succès, pas besoin de tester d'autres URLs
                    
            except Exception as e:
                result['error'] = str(e)
                continue  # Essayer URL suivante
        
        return result
    
    def test_proxy_list(self, proxy_list: List[Dict], max_workers: int = 10) -> List[Dict]:
        """Test une liste de proxies en parallèle"""
        results = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Soumission des tâches
            future_to_proxy = {
                executor.submit(
                    self.test_single_proxy, 
                    proxy['host'], 
                    proxy['port']
                ): proxy for proxy in proxy_list
            }
            
            # Collecte des résultats
            for future in as_completed(future_to_proxy):
                result = future.result()
                results.append(result)
                
                # Affichage en temps réel
                status = "✅" if result['working'] else "❌"
                response_time = f"({result['response_time']:.2f}s)" if result['response_time'] else ""
                print(f"{status} {result['host']}:{result['port']} {response_time}")
        
        return results
    
    def get_manual_proxy_list(self) -> List[Dict]:
        """Retourne une liste de proxies gratuits à tester manuellement"""
        return [
            {'host': '51.158.68.133', 'port': 8811, 'country': 'FR'},
            {'host': '144.217.7.124', 'port': 5566, 'country': 'CA'},
            {'host': '20.111.54.16', 'port': 8123, 'country': 'US'},
            {'host': '104.248.90.212', 'port': 8080, 'country': 'US'},
            {'host': '159.223.163.18', 'port': 80, 'country': 'US'},
            {'host': '165.227.81.188', 'port': 9999, 'country': 'US'},
            {'host': '185.162.230.55', 'port': 80, 'country': 'NL'},
            {'host': '103.216.207.15', 'port': 8080, 'country': 'IN'},
            {'host': '45.76.97.109', 'port': 3128, 'country': 'SG'},
            {'host': '194.5.193.183', 'port': 80, 'country': 'DE'}
        ]
    
    def fetch_and_test_free_proxies(self) -> Dict:
        """Récupère et teste automatiquement des proxies gratuits"""
        print("🌐 Récupération de proxies gratuits...")
        
        try:
            manager = FreeProxyManager('config/free_proxies.json')
            stats = manager.get_proxy_stats()
            
            print(f"📊 Statistiques manager: {stats}")
            
            working_proxies = [p for p in manager.working_proxies if p.get('working')]
            
            return {
                'total_found': len(manager.working_proxies),
                'working_count': len(working_proxies),
                'working_proxies': working_proxies,
                'sources': stats.get('sources', [])
            }
            
        except Exception as e:
            print(f"❌ Erreur récupération automatique: {e}")
            return {'error': str(e)}
    
    def create_working_proxy_config(self, results: List[Dict], output_file: str = 'config/working_proxies.json'):
        """Crée un fichier de configuration avec les proxies fonctionnels"""
        working_proxies = [r for r in results if r['working']]
        
        if not working_proxies:
            print("❌ Aucun proxy fonctionnel à sauvegarder")
            return False
        
        config = {
            "proxy_type": "free_tested",
            "created_at": time.strftime('%Y-%m-%d %H:%M:%S'),
            "tested_count": len(results),
            "working_count": len(working_proxies),
            "proxies": []
        }
        
        for proxy in working_proxies:
            config["proxies"].append({
                "host": proxy['host'],
                "port": proxy['port'],
                "response_time": proxy.get('response_time', 0),
                "detected_ip": proxy.get('detected_ip', 'Unknown'),
                "test_url": proxy.get('test_url_used', 'Unknown'),
                "status": "working"
            })
        
        # Tri par temps de réponse
        config["proxies"].sort(key=lambda x: x['response_time'] or 999)
        
        try:
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Configuration sauvegardée: {output_file}")
            print(f"📊 {len(working_proxies)} proxies fonctionnels sauvegardés")
            return True
            
        except Exception as e:
            print(f"❌ Erreur sauvegarde: {e}")
            return False

def main():
    """Interface en ligne de commande pour tester les proxies"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Testeur de proxies gratuits")
    parser.add_argument('--test-manual', action='store_true',
                       help='Teste une liste prédéfinie de proxies')
    parser.add_argument('--test-auto', action='store_true',
                       help='Teste les proxies récupérés automatiquement')
    parser.add_argument('--test-single', nargs=2, metavar=('HOST', 'PORT'),
                       help='Teste un proxy spécifique')
    parser.add_argument('--save-working', type=str, default='config/working_proxies.json',
                       help='Fichier où sauvegarder les proxies fonctionnels')
    parser.add_argument('--max-workers', type=int, default=10,
                       help='Nombre de threads pour tests parallèles')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       default='INFO', help='Niveau de logging')
    
    args = parser.parse_args()
    
    tester = FreeProxyTester(args.log_level)
    
    if args.test_single:
        host, port = args.test_single
        print(f"🧪 Test proxy unique: {host}:{port}")
        
        result = tester.test_single_proxy(host, int(port))
        
        if result['working']:
            print(f"✅ Proxy fonctionnel!")
            print(f"   Temps de réponse: {result['response_time']:.2f}s")
            print(f"   IP détectée: {result['detected_ip']}")
        else:
            print(f"❌ Proxy non fonctionnel")
            if result['error']:
                print(f"   Erreur: {result['error']}")
    
    elif args.test_manual:
        print("🧪 Test de la liste prédéfinie de proxies...")
        
        proxy_list = tester.get_manual_proxy_list()
        print(f"📋 {len(proxy_list)} proxies à tester")
        
        results = tester.test_proxy_list(proxy_list, args.max_workers)
        
        working_count = len([r for r in results if r['working']])
        print(f"\n📊 Résultats: {working_count}/{len(results)} proxies fonctionnels")
        
        if working_count > 0 and args.save_working:
            tester.create_working_proxy_config(results, args.save_working)
    
    elif args.test_auto:
        print("🤖 Test automatique des proxies récupérés...")
        
        result = tester.fetch_and_test_free_proxies()
        
        if 'error' in result:
            print(f"❌ Erreur: {result['error']}")
        else:
            print(f"📊 Résultats automatiques:")
            print(f"   Total trouvé: {result['total_found']}")
            print(f"   Fonctionnels: {result['working_count']}")
            print(f"   Sources: {result.get('sources', [])}")
            
            if result['working_count'] > 0:
                print("\n✅ Proxies fonctionnels trouvés:")
                for proxy in result['working_proxies'][:5]:  # Top 5
                    print(f"   {proxy['host']}:{proxy['port']} ({proxy.get('response_time', 0):.2f}s)")
    
    else:
        print("🆓 Testeur de Proxies Gratuits")
        print("===============================")
        print("Utilisez --help pour voir les options disponibles")
        print("\nExemples:")
        print("  python test_free_proxies.py --test-manual")
        print("  python test_free_proxies.py --test-single 51.158.68.133 8811")
        print("  python test_free_proxies.py --test-auto")

if __name__ == "__main__":
    main()