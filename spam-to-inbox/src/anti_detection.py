"""
Module anti-détection pour comportement humain réaliste
Simule les patterns de lecture et d'interaction humains
"""
import time
import random
import math
from typing import Dict, List, Optional
from logger import get_logger

logger = get_logger(__name__)

class HumanBehaviorSimulator:
    """Simulateur de comportement humain pour éviter la détection"""
    
    def __init__(self, fatigue_enabled: bool = True):
        self.fatigue_enabled = fatigue_enabled
        self.session_start_time = time.time()
        self.actions_performed = 0
        self.current_fatigue_level = 0.0  # 0.0 = frais, 1.0 = très fatigué
        
        # Paramètres comportementaux de base
        self.base_read_speed = 1.0
        self.distraction_probability = 0.05  # 5% de chance de distraction
        self.break_probability = 0.02  # 2% de chance de pause
        
        logger.info("🧠 Simulateur comportement humain initialisé")
    
    def calculate_reading_delay(self, email_size: int, content_complexity: str = 'normal') -> float:
        """
        Calcule un délai de lecture réaliste basé sur la taille et complexité
        """
        # Délais de base par type de contenu
        base_delays = {
            'simple': 0.8,    # Newsletter simple
            'normal': 1.0,    # Email standard
            'complex': 1.5,   # Email avec pièces jointes/formatting
            'promotional': 0.6  # Spam/promo (lecture rapide)
        }
        
        base_delay = base_delays.get(content_complexity, 1.0)
        
        # Facteur basé sur la taille (approximation temps de lecture)
        # ~200 mots par minute de lecture
        size_factor = max(0.5, math.log10(max(100, email_size)) * 0.3)
        
        # Application fatigue
        fatigue_multiplier = 1.0 + (self.current_fatigue_level * 0.5)
        
        # Variation aléatoire humaine (±30%)
        random_factor = random.uniform(0.7, 1.3)
        
        total_delay = base_delay * size_factor * fatigue_multiplier * random_factor
        
        # Bornes réalistes (minimum 1 seconde, maximum 30 secondes)
        final_delay = max(1.0, min(30.0, total_delay))
        
        logger.debug(f"⏱️ Délai lecture: {final_delay:.2f}s (taille:{email_size}, complexité:{content_complexity})")
        return final_delay
    
    def should_take_break(self) -> bool:
        """Détermine s'il faut prendre une pause"""
        # Probabilité augmente avec la fatigue et le temps de session
        session_duration = time.time() - self.session_start_time
        
        # Facteur temps (plus longue session = plus de pauses)
        time_factor = min(1.0, session_duration / 3600)  # Max après 1h
        
        # Facteur fatigue
        fatigue_factor = self.current_fatigue_level
        
        # Facteur nombre d'actions
        action_factor = min(1.0, self.actions_performed / 100)
        
        total_probability = self.break_probability * (1 + time_factor + fatigue_factor + action_factor)
        
        should_break = random.random() < total_probability
        
        if should_break:
            logger.info("☕ Pause comportement humain déclenchée")
        
        return should_break
    
    def take_human_break(self) -> float:
        """Prend une pause réaliste"""
        # Types de pauses avec durées différentes
        break_types = [
            ('micro_pause', (2, 8)),        # Courte réflexion
            ('coffee_break', (10, 30)),     # Pause café
            ('distraction', (5, 15)),       # Distraction courte
            ('long_pause', (30, 120))       # Pause longue (rare)
        ]
        
        # Pondération selon fatigue
        if self.current_fatigue_level > 0.7:
            # Plus fatigué = pauses plus longues plus probables
            weights = [0.3, 0.3, 0.2, 0.2]
        elif self.current_fatigue_level > 0.4:
            weights = [0.4, 0.4, 0.15, 0.05]
        else:
            weights = [0.6, 0.3, 0.1, 0.0]
        
        break_type, duration_range = random.choices(break_types, weights=weights)[0]
        duration = random.uniform(*duration_range)
        
        logger.info(f"⏸️ {break_type}: {duration:.1f}s")
        
        # Les pauses réduisent légèrement la fatigue
        self.current_fatigue_level = max(0.0, self.current_fatigue_level - 0.1)
        
        return duration
    
    def should_show_distraction(self) -> bool:
        """Détermine si une distraction se produit"""
        return random.random() < self.distraction_probability
    
    def simulate_distraction(self) -> float:
        """Simule une distraction brève"""
        distraction_types = [
            'notification_check',    # Vérifier une notification
            'quick_scroll',         # Scroll rapide
            'window_switch',        # Changer de fenêtre
            'micro_task'           # Petite tâche rapide
        ]
        
        distraction = random.choice(distraction_types)
        duration = random.uniform(0.5, 3.0)
        
        logger.debug(f"😴 Distraction: {distraction} ({duration:.1f}s)")
        return duration
    
    def calculate_action_delay(self, action_type: str, context: Dict = None) -> float:
        """
        Calcule le délai pour une action spécifique
        """
        base_delays = {
            'connect': (2.0, 5.0),          # Temps de connexion/chargement
            'folder_select': (1.0, 2.5),   # Sélection dossier
            'email_scan': (0.8, 2.0),      # Scan liste emails
            'email_open': (0.5, 1.5),      # Ouverture email
            'email_move': (0.3, 1.0),      # Déplacement email
            'batch_process': (1.0, 3.0),   # Traitement par lot
            'disconnect': (0.5, 1.5)       # Déconnexion
        }
        
        min_delay, max_delay = base_delays.get(action_type, (1.0, 2.0))
        
        # Application fatigue
        if self.fatigue_enabled:
            fatigue_mult = 1.0 + (self.current_fatigue_level * 0.3)
            min_delay *= fatigue_mult
            max_delay *= fatigue_mult
        
        # Délai de base
        delay = random.uniform(min_delay, max_delay)
        
        # Ajout distractions occasionnelles
        if self.should_show_distraction():
            delay += self.simulate_distraction()
        
        return delay
    
    def update_fatigue(self, action_weight: float = 1.0):
        """Met à jour le niveau de fatigue après une action"""
        if not self.fatigue_enabled:
            return
        
        self.actions_performed += 1
        
        # Facteurs d'augmentation de fatigue
        time_factor = (time.time() - self.session_start_time) / 3600  # Fatigue par heure
        action_factor = self.actions_performed * 0.001  # Fatigue par action
        weight_factor = action_weight * 0.01  # Poids de l'action
        
        # Augmentation fatigue
        fatigue_increase = (time_factor + action_factor + weight_factor) * 0.05
        self.current_fatigue_level = min(1.0, self.current_fatigue_level + fatigue_increase)
        
        logger.debug(f"😴 Niveau fatigue: {self.current_fatigue_level:.2f}")
    
    def simulate_realistic_session(self, email_count: int) -> Dict:
        """
        Simule une session complète avec comportement réaliste
        """
        session_plan = {
            'total_emails': email_count,
            'estimated_duration': 0.0,
            'planned_breaks': [],
            'reading_pattern': self._determine_reading_pattern(),
            'batch_sizes': self._calculate_batch_sizes(email_count)
        }
        
        # Estimation durée totale
        avg_read_time = 3.0  # Temps moyen par email
        base_duration = email_count * avg_read_time
        
        # Ajout temps pauses et actions
        estimated_breaks = max(1, email_count // 20)  # Une pause toutes les 20 emails
        break_time = estimated_breaks * 15  # 15s moyenne par pause
        
        session_plan['estimated_duration'] = base_duration + break_time
        
        logger.info(f"📋 Plan session: {email_count} emails, ~{session_plan['estimated_duration']:.0f}s")
        
        return session_plan
    
    def _determine_reading_pattern(self) -> str:
        """Détermine le pattern de lecture pour la session"""
        patterns = [
            'thorough',      # Lecture attentive
            'scanning',      # Scan rapide
            'selective',     # Sélectif
            'batch_delete'   # Suppression en lot
        ]
        
        # Pondération selon l'heure (approximation)
        hour = time.localtime().tm_hour
        
        if 8 <= hour <= 10:  # Matin - plus attentif
            weights = [0.4, 0.3, 0.2, 0.1]
        elif 12 <= hour <= 14:  # Midi - scan rapide
            weights = [0.2, 0.5, 0.2, 0.1]
        elif 17 <= hour <= 19:  # Soir - nettoyage
            weights = [0.1, 0.2, 0.3, 0.4]
        else:  # Autres heures
            weights = [0.25, 0.25, 0.25, 0.25]
        
        pattern = random.choices(patterns, weights=weights)[0]
        logger.info(f"📖 Pattern lecture: {pattern}")
        
        return pattern
    
    def _calculate_batch_sizes(self, total_emails: int) -> List[int]:
        """Calcule les tailles de lot réalistes"""
        if total_emails <= 10:
            return [total_emails]
        
        batches = []
        remaining = total_emails
        
        while remaining > 0:
            # Taille de lot variable (5-25 emails)
            batch_size = min(remaining, random.randint(5, 25))
            batches.append(batch_size)
            remaining -= batch_size
        
        logger.debug(f"📦 Lots planifiés: {batches}")
        return batches
    
    def wait_with_progress(self, duration: float, description: str = "Attente"):
        """Attente avec indicateur de progression optionnel"""
        if duration < 1.0:
            time.sleep(duration)
            return
        
        logger.info(f"⏳ {description}: {duration:.1f}s")
        
        # Pour les longues attentes, découpage en segments
        if duration > 10.0:
            segments = int(duration / 5.0)
            segment_duration = duration / segments
            
            for i in range(segments):
                time.sleep(segment_duration)
                if i < segments - 1:  # Pas de log pour le dernier segment
                    remaining = duration - ((i + 1) * segment_duration)
                    logger.debug(f"⏳ Encore {remaining:.1f}s...")
        else:
            time.sleep(duration)
    
    def get_session_stats(self) -> Dict:
        """Retourne les statistiques de la session"""
        session_duration = time.time() - self.session_start_time
        
        return {
            'session_duration': session_duration,
            'actions_performed': self.actions_performed,
            'fatigue_level': self.current_fatigue_level,
            'actions_per_minute': self.actions_performed / max(1, session_duration / 60)
        }

def test_human_behavior():
    """Test simple du simulateur de comportement"""
    print("🧪 Test simulateur comportement humain...")
    
    simulator = HumanBehaviorSimulator()
    
    # Test calcul délai lecture
    delay = simulator.calculate_reading_delay(1500, 'normal')
    print(f"✅ Délai lecture calculé: {delay:.2f}s")
    
    # Test plan session
    plan = simulator.simulate_realistic_session(50)
    print(f"✅ Plan session: {plan['estimated_duration']:.0f}s pour {plan['total_emails']} emails")
    
    # Test fatigue
    simulator.update_fatigue(2.0)
    print(f"✅ Niveau fatigue: {simulator.current_fatigue_level:.2f}")
    
    print("✅ Tous les tests comportement humain passés!")

if __name__ == "__main__":
    test_human_behavior()