# -*- coding: utf-8 -*-
"""
Game Systems Module
Weather, Injury, and AI Decision Systems
"""
import random
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game_state import GameStateManager
    from models import Player


# ============================================================================
# WEATHER SYSTEM (天候システム)
# ============================================================================

def check_weather(game_state: 'GameStateManager') -> dict:
    """
    Check weather conditions before a game.
    
    Returns:
        dict with keys:
            - can_play: bool - True if game can proceed
            - weather: str - Weather type ('晴れ', '曇り', '雨', '雷雨')
            - delay_minutes: int - Delay time if any
    """
    if not getattr(game_state, 'weather_enabled', True):
        return {'can_play': True, 'weather': '晴れ', 'delay_minutes': 0}
    
    # Weather probabilities (total = 100)
    weather_roll = random.random() * 100
    
    if weather_roll < 70:  # 70% - Clear/Cloudy (playable)
        weather = '晴れ' if weather_roll < 50 else '曇り'
        return {'can_play': True, 'weather': weather, 'delay_minutes': 0}
    
    elif weather_roll < 90:  # 20% - Rain (possible delay)
        weather = '雨'
        # 50% chance of rain delay
        if random.random() < 0.5:
            delay = random.randint(30, 120)  # 30min to 2hr delay
            return {'can_play': True, 'weather': weather, 'delay_minutes': delay}
        else:
            # Rain too heavy - game cancelled
            return {'can_play': False, 'weather': weather, 'delay_minutes': 0}
    
    else:  # 10% - Thunderstorm (cancelled)
        return {'can_play': False, 'weather': '雷雨', 'delay_minutes': 0}


def get_weather_display(weather_result: dict) -> str:
    """Get display string for weather result"""
    if not weather_result['can_play']:
        return f"⛈ {weather_result['weather']}のため試合中止"
    elif weather_result['delay_minutes'] > 0:
        return f"🌧 {weather_result['weather']} - {weather_result['delay_minutes']}分遅延"
    else:
        if weather_result['weather'] == '晴れ':
            return "☀ 晴れ"
        else:
            return f"☁ {weather_result['weather']}"


# ============================================================================
# INJURY SYSTEM (怪我発生システム)
# ============================================================================

INJURY_TYPES = [
    ('軽い打撲', 3, 7),        # Minor bruise: 3-7 days
    ('肉離れ', 7, 21),         # Muscle strain: 7-21 days
    ('捻挫', 7, 14),           # Sprain: 7-14 days
    ('骨折', 30, 60),          # Fracture: 30-60 days
    ('靭帯損傷', 60, 120),     # Ligament: 60-120 days
    ('疲労骨折', 21, 45),      # Stress fracture: 21-45 days
]


def check_injury(player: 'Player', game_state: 'GameStateManager', 
                 is_pitching: bool = False) -> Optional[dict]:
    """
    Check if a player gets injured during gameplay.
    
    Args:
        player: The player to check
        game_state: Current game state
        is_pitching: True if player is pitching (higher injury risk)
    
    Returns:
        None if no injury, or dict with injury details:
            - type: str - Injury type name
            - days: int - Recovery days
    """
    if not getattr(game_state, 'injuries_enabled', True):
        return None
    
    if getattr(player, 'is_injured', False):
        return None  # Already injured
    
    # Base injury rate per at-bat/pitch event
    base_rate = 0.001  # 0.1% base chance
    
    # Modifiers
    fatigue = getattr(player, 'fatigue', 0)
    fatigue_mult = 1.0 + (fatigue / 100) * 2.0  # 0-100 fatigue -> 1.0-3.0 mult
    
    age = getattr(player, 'age', 25)
    age_mult = 1.0 + max(0, age - 30) * 0.05  # +5% per year over 30
    
    pitch_mult = 1.5 if is_pitching else 1.0
    
    final_rate = base_rate * fatigue_mult * age_mult * pitch_mult
    
    if random.random() < final_rate:
        # Injury occurred - select type
        injury_weights = [50, 25, 15, 5, 3, 2]  # Weighted toward minor injuries
        injury_idx = random.choices(range(len(INJURY_TYPES)), weights=injury_weights)[0]
        injury_name, min_days, max_days = INJURY_TYPES[injury_idx]
        recovery_days = random.randint(min_days, max_days)
        
        return {
            'type': injury_name,
            'days': recovery_days
        }
    
    return None


def apply_injury(player: 'Player', injury: dict):
    """Apply injury to a player"""
    player.is_injured = True
    player.injury_days = injury['days']
    player.injury_type = injury['type']


def heal_injuries(team, days: int = 1):
    """Process injury healing for a team after days pass"""
    for player in team.players:
        if getattr(player, 'is_injured', False):
            player.injury_days = max(0, player.injury_days - days)
            if player.injury_days <= 0:
                player.is_injured = False
                player.injury_type = None


# ============================================================================
# AI DECISION SYSTEM (AI采配ロジック)
# ============================================================================

class AIDecisionMaker:
    """AI decision maker for non-player teams"""
    
    def __init__(self, game_state: 'GameStateManager'):
        self.game_state = game_state
        
        # Get tendencies from settings (0-100 scale)
        self.bunt_tendency = getattr(game_state, 'ai_bunt_tendency', 50) / 100.0
        self.steal_tendency = getattr(game_state, 'ai_steal_tendency', 50) / 100.0
        self.pitching_change_tendency = getattr(game_state, 'ai_pitching_change_tendency', 50) / 100.0
        self.use_defensive_shift = getattr(game_state, 'ai_defensive_shift', True)
        
        # Pinch hitter settings
        self.pinch_hitter_inning = getattr(game_state, 'pinch_hitter_inning', 7)
        self.substitute_stamina_threshold = getattr(game_state, 'substitute_stamina_threshold', 30)
    
    def should_use_pinch_hitter(self, inning: int, batter_stamina: float, 
                                 batter_ability: int, score_diff: int) -> bool:
        """
        Decide if AI should use a pinch hitter.
        
        Args:
            inning: Current inning
            batter_stamina: Current batter's stamina (0-100)
            batter_ability: Batter's overall ability
            score_diff: Score difference (positive = winning)
        
        Returns True if pinch hitter should be used.
        """
        # Don't use pinch hitters before configured inning
        if inning < self.pinch_hitter_inning:
            return False
        
        # Low stamina triggers consideration
        if batter_stamina <= self.substitute_stamina_threshold:
            return True
        
        # Late game, weak hitter, close game - consider pinch hit
        if inning >= 8 and batter_ability < 40 and abs(score_diff) <= 2:
            return random.random() < 0.5
        
        # 9th inning, need runs, weak hitter
        if inning >= 9 and score_diff <= 0 and batter_ability < 50:
            return random.random() < 0.6
        
        return False
    
    def should_bunt(self, inning: int, outs: int, score_diff: int, 
                    runner_on_first: bool, runner_on_second: bool,
                    batter_power: int) -> bool:
        """
        Decide if AI should call for a bunt.
        
        Returns True if bunt should be attempted.
        """
        # Base bunt situations
        base_rate = 0.0
        
        # Sacrifice bunt situations
        if outs < 2 and runner_on_first and not runner_on_second:
            if abs(score_diff) <= 2:  # Close game
                base_rate = 0.4
            else:
                base_rate = 0.2
        
        # Late game, need to move runner
        if inning >= 7 and runner_on_second and outs == 0:
            base_rate = 0.5
        
        # Weak hitter more likely to bunt
        if batter_power < 40:
            base_rate *= 1.3
        elif batter_power > 60:
            base_rate *= 0.5
        
        # Apply tendency modifier
        final_rate = base_rate * self.bunt_tendency * 2  # 0-100% -> 0-2x
        
        return random.random() < min(0.8, final_rate)
    
    def should_steal(self, runner_speed: int, catcher_arm: int, 
                     pitcher_control: int, outs: int, score_diff: int) -> bool:
        """
        Decide if AI should attempt a steal.
        
        Returns True if steal should be attempted.
        """
        if outs >= 2:
            # Don't steal with 2 outs usually
            return False
        
        # Base steal rate based on matchup
        speed_advantage = (runner_speed - 50) / 50.0  # -1 to +1
        catcher_disadvantage = (50 - catcher_arm) / 50.0  # -1 to +1
        
        base_rate = 0.1 + speed_advantage * 0.15 + catcher_disadvantage * 0.1
        
        # Adjust for game situation
        if score_diff < -3:
            base_rate *= 1.5  # More aggressive when behind
        elif score_diff > 3:
            base_rate *= 0.3  # Conservative when ahead
        
        # Apply tendency modifier
        final_rate = base_rate * self.steal_tendency * 2
        
        return random.random() < min(0.5, max(0, final_rate))
    
    def should_change_pitcher(self, current_stamina: float, runs_allowed: int,
                               inning: int, score_diff: int, 
                               pitch_count: int, is_starter: bool) -> float:
        """
        Get probability that AI should change the pitcher.
        
        Returns probability (0.0 to 1.0).
        """
        base_rate = 0.0
        
        # Stamina based
        if current_stamina < 20:
            base_rate = 0.8
        elif current_stamina < 40:
            base_rate = 0.4
        elif current_stamina < 60:
            base_rate = 0.15
        
        # Pitch count for starters
        if is_starter:
            if pitch_count > 110:
                base_rate += 0.4
            elif pitch_count > 90:
                base_rate += 0.2
        
        # Runs allowed this game
        if runs_allowed >= 5:
            base_rate += 0.3
        elif runs_allowed >= 3:
            base_rate += 0.15
        
        # Late innings, protecting lead
        if inning >= 8 and score_diff > 0 and score_diff <= 3:
            base_rate += 0.2
        
        # Apply tendency modifier
        final_rate = base_rate * self.pitching_change_tendency / 50.0
        
        return min(1.0, final_rate)
    
    def get_defensive_shift(self, batter_pull_tendency: float, 
                            batter_ground_ball_rate: float) -> str:
        """
        Decide defensive alignment.
        
        Returns: 'normal', 'shift_left', 'shift_right', 'infield_in', 'deep'
        """
        if not self.use_defensive_shift:
            return 'normal'
        
        # Pull hitter -> shift opposite field
        if batter_pull_tendency > 0.6:
            return 'shift_left' if random.random() < 0.7 else 'normal'
        elif batter_pull_tendency < 0.4:
            return 'shift_right' if random.random() < 0.5 else 'normal'
        
        # Ground ball hitter -> infield depth
        if batter_ground_ball_rate > 0.6:
            return 'infield_in' if random.random() < 0.3 else 'normal'
        
        return 'normal'


# ============================================================================
# AUTOSAVE SYSTEM (オートセーブ)
# ============================================================================

class AutosaveManager:
    """Manages automatic game saving"""
    
    def __init__(self, game_state: 'GameStateManager', save_callback):
        """
        Args:
            game_state: Current game state
            save_callback: Function to call to save the game
        """
        self.game_state = game_state
        self.save_callback = save_callback
        self.games_since_save = 0
    
    def on_game_complete(self) -> bool:
        """
        Called after each game completes.
        
        Returns True if autosave was triggered.
        """
        if not getattr(self.game_state, 'autosave_enabled', True):
            return False
        
        self.games_since_save += 1
        interval = getattr(self.game_state, 'autosave_interval', 5)
        
        if self.games_since_save >= interval:
            self.trigger_autosave()
            return True
        
        return False
    
    def trigger_autosave(self):
        """Execute autosave"""
        try:
            self.save_callback()
            self.games_since_save = 0
            print(f"[Autosave] Game saved automatically")
        except Exception as e:
            print(f"[Autosave] Failed to save: {e}")
    
    def reset(self):
        """Reset counter (e.g., after manual save)"""
        self.games_since_save = 0
