# -*- coding: utf-8 -*-
"""
ライブ試合エンジン (修正版: ボール球スイング増・コンタクト率低下・リーグ実データ対応)
"""
import random
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict, Any
from enum import Enum
from models import (
    Team, Player, GameStatus, Position, Stadium, 
    PitchType, TeamLevel, PitcherRole, PlayerRecord,
    generate_best_lineup
)
from pitching_system import PitchingDirector, create_pitching_context, PitcherRole as PSPitcherRole
from game_systems import AIDecisionMaker, check_injury, apply_injury

# ========================================
# 定数・ユーティリティ
# ========================================

STRIKE_ZONE = {
    'width': 0.432,
    'height': 0.56,
    'center_x': 0.0,
    'center_z': 0.75,
    'half_width': 0.216,
    'half_height': 0.28
}

FIELD_COORDS = {
    Position.PITCHER: (0, 18.0),
    Position.CATCHER: (0, -1.0),
    Position.FIRST: (18.0, 24.0),
    Position.SECOND: (10.0, 42.0),
    Position.THIRD: (-18.0, 24.0),
    Position.SHORTSTOP: (-10.0, 42.0),
    Position.LEFT: (-35.0, 88.0),
    Position.CENTER: (0.0, 95.0),
    Position.RIGHT: (35.0, 88.0),
}

RUN_VALUES = {
    "Out": -0.27,
    "Single": 0.90,
    "Double": 1.27,
    "Triple": 1.62,
    "HomeRun": 2.10,
    "Error": 0.50, 
    "SB": 0.20,
    "CS": -0.40,
    "DP": -0.80,
    "WildPitch": 0.30,
    "PassedBall": 0.30
}

# 守備指標のスケール係数 (年間換算での見栄えを調整)
UZR_SCALE = {
    "RngR": 0.70, # 範囲貢献
    "ErrR": 0.40, # 失策抑止
    "ARM": 0.60,  # 補殺貢献
    "DPR": 0.30,  # 併殺貢献
    "rSB": 0.90,  # 盗塁阻止
    "rBlk": 0.40   # ブロッキング
}

def get_rank(value: int) -> str:
    if value >= 90: return "S"
    if value >= 80: return "A"
    if value >= 70: return "B"
    if value >= 60: return "C"
    if value >= 50: return "D"
    if value >= 40: return "E"
    if value >= 30: return "F"
    return "G"

def calculate_double_play_success(fielder: Player, runner_speed: int = 50) -> float:
    """併殺成功率を計算（turn_dp能力使用）
    
    Returns: 0.0-1.0の成功確率
    """
    turn_dp = getattr(fielder.stats, 'turn_dp', 50)
    # 基本成功率60%、turn_dp99で80%、turn_dp1で40%
    base_rate = 0.60
    dp_bonus = (turn_dp - 50) / 250  # ±0.2
    runner_penalty = (runner_speed - 50) / 500  # 速いランナーで-0.1
    return max(0.3, min(0.9, base_rate + dp_bonus - runner_penalty))

def calculate_bunt_success(batter: Player, is_sacrifice: bool = True) -> float:
    """バント成功率を計算
    
    Returns: 0.0-1.0の成功確率
    """
    if is_sacrifice:
        bunt_stat = getattr(batter.stats, 'bunt_sac', 50)
        # 犠牲バント: 基本70%、bunt_sac99で95%、bunt_sac1で45%
        base_rate = 0.70
    else:
        bunt_stat = getattr(batter.stats, 'bunt_hit', 50)
        # セーフティ: 基本10%、bunt_hit99で45%、bunt_hit1で5%
        base_rate = 0.1
    
    bonus = (bunt_stat - 50) / 200  # ±0.25
    return max(0.1, min(0.95, base_rate + bonus))

def get_effective_stat(player: Player, stat_name: str, opponent: Optional[Player] = None, is_risp: bool = False, is_close_game: bool = False, aptitude_val: int = 4, catcher_lead: int = 50) -> float:
    if not hasattr(player.stats, stat_name):
        return 50.0

    if hasattr(player, 'is_injured') and player.is_injured:
        return getattr(player.stats, stat_name) * 0.5

    base_value = getattr(player.stats, stat_name)
    condition_diff = player.condition - 5
    condition_multiplier = 1.0 + (condition_diff * 0.015)
    
    value = base_value * condition_multiplier
    
    # 疲労ペナルティ: 疲労度50で-10%、100で-20%
    fatigue = getattr(player, 'fatigue', 0)
    fatigue_penalty = 1.0 - (fatigue / 500)  # 0-20%減少
    value *= fatigue_penalty
    
    # Aptitude Penalty
    if player.position == Position.PITCHER and aptitude_val < 4:
        if aptitude_val == 3: 
            pass # 〇: No penalty (Standard)
        elif aptitude_val == 2: 
            value *= 0.90 # △: Mild penalty (-10%)
        elif aptitude_val <= 1: 
            value *= 0.70 # ×: Severe penalty (-30%)

    if player.position != Position.PITCHER:
        if stat_name in ['contact', 'power'] and opponent and opponent.position == Position.PITCHER:
            vs_left = getattr(player.stats, 'vs_left_batter', 50)
            throws = getattr(opponent, 'throws', '右')
            if throws == '左':
                value += (vs_left - 50) * 0.4 
            else:
                value -= (vs_left - 50) * 0.1

        if is_risp and stat_name in ['contact', 'power']:
            chance = getattr(player.stats, 'chance', 50)
            value += (chance - 50) * 0.5
        if is_close_game:
            mental = getattr(player.stats, 'mental', 50)
            value += (mental - 50) * 0.3
        
        # 野球脳: 走塁・守備状況判断に影響
        if stat_name in ['speed', 'baserunning', 'steal']:
            intelligence = getattr(player.stats, 'intelligence', 50)
            value += (intelligence - 50) * 0.2
    else:
        # 捕手リード補正: 投手の球威・コントロールに影響
        if stat_name in ['stuff', 'control', 'movement']:
            lead_bonus = (catcher_lead - 50) * 0.1  # 最大+/-5
            value += lead_bonus
            
        if opponent and opponent.position != Position.PITCHER:
            vs_left = getattr(player.stats, 'vs_left_pitcher', 50)
            bats = getattr(opponent, 'bats', '右')
            if bats == '左' or bats == '両': 
                value += (vs_left - 50) * 0.4
            else:
                value -= (vs_left - 50) * 0.1

        if is_risp:
            pinch = getattr(player.stats, 'vs_pinch', 50)
            if stat_name in ['stuff', 'movement', 'control']:
                value += (pinch - 50) * 0.5
        
        # 投手もプレッシャー時にメンタル適用
        if is_close_game:
            mental = getattr(player.stats, 'mental', 50)
            value += (mental - 50) * 0.25
            
        if stat_name == 'control':
            stability = getattr(player.stats, 'stability', 50)
            if condition_diff < 0:
                mitigation = (stability - 50) * 0.2
                value += max(0, mitigation)

    # Special handling for velocity (measured in km/h, not 1-99 scale)
    if stat_name == 'velocity':
        return max(100.0, min(175.0, value))  # Realistic velocity range: 100-175 km/h
    
    return max(20.0, min(120.0, value))


# ========================================
# 列挙型
# ========================================

class PitchResult(Enum):
    BALL = "ボール"; STRIKE_CALLED = "見逃し"; STRIKE_SWINGING = "空振り"
    FOUL = "ファウル"; IN_PLAY = "インプレー"; HIT_BY_PITCH = "死球"

class BattedBallType(Enum):
    GROUNDBALL = "ゴロ"; LINEDRIVE = "ライナー"; FLYBALL = "フライ"; POPUP = "内野フライ"

class PlayResult(Enum):
    SINGLE = "安打"; DOUBLE = "二塁打"; TRIPLE = "三塁打"; HOME_RUN = "本塁打"
    STRIKEOUT = "三振"; GROUNDOUT = "ゴロ"; FLYOUT = "フライ"; LINEOUT = "ライナー"; POPUP_OUT = "内野フライ"
    ERROR = "失策"; SACRIFICE_FLY = "犠飛"; SACRIFICE_BUNT = "犠打"; DOUBLE_PLAY = "併殺打"
    FOUL = "ファウル"; FIELDERS_CHOICE = "野選"

# ========================================
# データクラス
# ========================================

@dataclass
class Substitution:
    player_in: Player
    player_out: Player
    position: Position
    order: int

@dataclass
class PitchLocation:
    x: float; z: float; is_strike: bool

@dataclass
class PitchData:
    pitch_type: str; velocity: float; spin_rate: int
    horizontal_break: float; vertical_break: float
    location: PitchLocation; release_point: Tuple[float, float, float]
    trajectory: List[Tuple[float, float, float]] = field(default_factory=list)

@dataclass
class BattedBallData:
    exit_velocity: float; launch_angle: float; spray_angle: float
    hit_type: BattedBallType; distance: float; hang_time: float
    landing_x: float; landing_y: float
    trajectory: List[Tuple[float, float, float]] = field(default_factory=list)
    contact_quality: str = "medium"

def create_default_inning_scores():
    return [0] * 9

@dataclass
class GameState:
    inning: int = 1; is_top: bool = True
    outs: int = 0; balls: int = 0; strikes: int = 0
    runner_1b: Optional[Player] = None; runner_2b: Optional[Player] = None; runner_3b: Optional[Player] = None
    home_score: int = 0; away_score: int = 0
    home_batter_order: int = 0; away_batter_order: int = 0
    home_pitcher_idx: int = 0; away_pitcher_idx: int = 0
    home_pitcher_stamina: float = 100.0; away_pitcher_stamina: float = 100.0
    pitch_count: int = 0 # Total pitches in the current at-bat
    home_pitch_count: int = 0; away_pitch_count: int = 0 # Total pitches for each team's current pitcher
    home_hits: int = 0; away_hits: int = 0
    home_errors: int = 0; away_errors: int = 0
    home_pitchers_used: List[Player] = field(default_factory=list)
    away_pitchers_used: List[Player] = field(default_factory=list)
    home_current_pitcher_runs: int = 0
    away_current_pitcher_runs: int = 0
    home_inning_scores: List[int] = field(default_factory=create_default_inning_scores)
    away_inning_scores: List[int] = field(default_factory=create_default_inning_scores)
    
    def is_runner_on(self) -> bool: return any([self.runner_1b, self.runner_2b, self.runner_3b])
    def is_risp(self) -> bool: return (self.runner_2b is not None) or (self.runner_3b is not None)
    def current_pitcher_stamina(self) -> float: return self.home_pitcher_stamina if self.is_top else self.away_pitcher_stamina
    
    def get_score_diff(self) -> int:
        if self.is_top: return self.away_score - self.home_score
        else: return self.home_score - self.away_score

# ========================================
# エンジンクラス群
# ========================================

class NPBPitcherManager:
    """
    NPB/Modern Baseball Style Pitcher Management Logic
    - Strict role enforcement (Starter, Setup A/B, Closer, Middle, Long, Specialist)
    - Winning/Losing patterns
    - Inning/Batter limitations
    """

    def check_pitcher_change(self, state: GameState, team: Team, opponent: Team, next_batter: Player, current_pitcher: Player, current_pitcher_ip: float = 0.0) -> Optional[Player]:
        """
        Determine if the current pitcher should be changed.
        Returns the replacement player, or None if no change is needed.
        """
        # 1. Basic Info
        is_starter = current_pitcher in [team.players[i] for i in team.rotation if 0 <= i < len(team.players)]
        current_stamina = state.home_pitcher_stamina if state.is_top else state.away_pitcher_stamina
        current_runs = state.home_current_pitcher_runs if state.is_top else state.away_current_pitcher_runs
        pitch_count = state.home_pitch_count if state.is_top else state.away_pitch_count
        
        score_diff = state.home_score - state.away_score
        if state.is_top: score_diff *= -1 # Positive means Team is Leading
        
        # 2. Injury Check (Handled elsewhere, but good as safeguard)
        if current_pitcher.is_injured:
            return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)

        # 3. Winning Formula Enforcement (Start of Inning)
        # 勝ちパターン継投の強制 (イニング頭)
        if state.outs == 0:
            # 9回以降: セーブシチュエーションなら守護神
            if state.inning >= 9:
                is_save_situation = (score_diff > 0 and score_diff <= 3) or (score_diff >= 4 and (state.runner_1b or state.runner_2b or state.runner_3b))
                # 同点の場合はHOMEなら守護神を出す (サヨナラ勝ち狙い)
                if score_diff == 0 and not state.is_top: is_save_situation = True
                
                if is_save_situation and role != PitcherRole.CLOSER:
                     closer = team.get_closer()
                     # If closer is available and not tired
                     if closer and closer != current_pitcher and closer.current_stamina > 20 and not closer.is_injured:
                         return closer

        # 4. Starter Logic
        if is_starter:
            # (A) Hard Fatigue Limits
            if current_stamina < 5: return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
            if pitch_count > 130: return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
            
            # (B) Performance / Blowout (Early Hook)
            # If 6+ runs allowed in first 3 innings -> Pull (relaxed from 5)
            if state.inning <= 3 and current_runs >= 6:
                return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
            # If 8+ runs allowed anytime -> Pull (relaxed from 6)
            if current_runs >= 8:
                return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
                
            # (C) Inning Start Check (Avoid starting tired or strict inning limits for modern SP)
            if state.outs == 0:
                is_qs_pace = state.inning >= 6 and current_runs <= 3
                stamina_threshold = 10 if is_qs_pace else 18 
                if current_stamina < stamina_threshold:
                     return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
                
                # Close Game check
                if state.inning >= 7 and abs(score_diff) <= 2:
                    if float(pitch_count) > 110 or current_stamina < 25: 
                        return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
                        
            # (D) Crisis Management (Mid-Inning)
            if state.inning >= 6 and abs(score_diff) <= 3 and (state.runner_1b or state.runner_2b):
                if current_stamina < 15: 
                    return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
                if current_runs >= 5: 
                    return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)

        # 5. Reliever Logic (Standard)
        else:
            # (A) Closer special case (Don't pull closer in save situation unless disaster)
            is_save_situation = (score_diff > 0 and score_diff <= 3) 
            if role == PitcherRole.CLOSER and is_save_situation and state.inning >= 9:
                 if current_runs >= 3: return self._select_reliever(team, state, score_diff, next_batter, current_pitcher) # Blowup
                 return None 
                
            # (B) Fatigue / Limits
            if current_stamina < 10: return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
            if pitch_count > 40: return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
            
            # (C) Inning Straddle / One Inning Limit
            if state.outs == 0 and current_pitcher_ip > 0:
                # Always look to refresh unless Closer or Long Relief
                if role == PitcherRole.CLOSER and state.inning >= 9: pass
                elif role == PitcherRole.LONG and abs(score_diff) >= 4:
                     if current_pitcher_ip < 2.0: pass
                     else: return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
                else:
                     return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)

            if current_pitcher_ip >= 1.0:
                if role == PitcherRole.CLOSER and is_save_situation: pass
                elif role == PitcherRole.LONG and abs(score_diff) >= 4: 
                    if current_pitcher_ip >= 3.0: return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
                else:
                    return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
            
            # (E) Crisis
            if current_runs >= 2 and score_diff <= 2:
                return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)

        # 6. Lefty Specialist (Specific case)
        if state.inning >= 7 and score_diff > 0 and score_diff <= 3 and next_batter.bats == "左":
            if current_pitcher.throws == "右" and not (is_starter and current_stamina > 40):
                role = self._get_pitcher_role_in_game(team, current_pitcher)
                if role not in [PitcherRole.CLOSER, PitcherRole.SETUP_A]:
                    specialist = self._find_available_reliever(team, state, role_filter=[PitcherRole.SPECIALIST])
                    if specialist: return specialist

        return None
    
    # ... (Keep existing methods) ...
    def _select_reliever(self, team: Team, state: GameState, score_diff: int, next_batter: Player, current_pitcher: Player) -> Optional[Player]:
        # ... logic as before but more robust ...
        used_pitchers = state.home_pitchers_used if state.is_top else state.away_pitchers_used
        is_winning = score_diff > 0
        is_close = abs(score_diff) <= 3
        is_tie = score_diff == 0
        
        target_roles = []
        
        if (is_winning and is_close) or is_tie:
            if state.inning >= 9: 
                # Winning or Tie in 9th+: Closer priority
                target_roles = [PitcherRole.CLOSER, PitcherRole.SETUP_A]
            elif state.inning == 8: 
                # 8th: Setup A priority, but allow Setup B/Middle
                target_roles = [PitcherRole.SETUP_A, PitcherRole.SETUP_B, PitcherRole.MIDDLE]
            elif state.inning == 7: 
                # 7th: Setup B priority, then Middle
                target_roles = [PitcherRole.SETUP_B, PitcherRole.MIDDLE]
            else: 
                target_roles = [PitcherRole.MIDDLE, PitcherRole.LONG]
        elif not is_winning and is_close:
            # Losing but close (1-3 runs): Use Middle/Long, avoid wasting Setup/Closer
            target_roles = [PitcherRole.MIDDLE, PitcherRole.LONG]
        else:
            # Blowout
            target_roles = [PitcherRole.LONG, PitcherRole.MIDDLE]
            
        for role in target_roles:
            candidate = self._find_available_reliever(team, state, role_filter=[role])
            if candidate: return candidate
            
        # Fallback
        all_avail = self._get_all_available_relievers(team, state)
        if all_avail:
             # ★修正: 勝ちパターン以外(負け試合や点差が開いた場面)では、セットアッパー/クローザーを極力出さない
             high_leverage_roles = [PitcherRole.CLOSER, PitcherRole.SETUP_A, PitcherRole.SETUP_B]
             
             if not ((is_winning and is_close) or is_tie):
                 # Filter out high leverage pitchers unless absolutely necessary (stamina management)
                 low_leverage_avail = []
                 for p in all_avail:
                     p_role = self._get_pitcher_role_in_game(team, p)
                     if p_role not in high_leverage_roles:
                         low_leverage_avail.append(p)
                 
                 # If we have low leverage specialists, use them
                 if low_leverage_avail:
                     all_avail = low_leverage_avail
             
             # Sort logic
             if is_winning and is_close: all_avail.sort(key=lambda p: p.stats.overall_pitching(), reverse=True)
             else: all_avail.sort(key=lambda p: p.stats.overall_pitching(), reverse=False) # Save best arms
             
             if all_avail:
                 return all_avail[0]
                 
        return None
        
    def _find_available_reliever(self, team: Team, state: GameState, role_filter: List[PitcherRole]) -> Optional[Player]:
        all_relievers = self._get_all_available_relievers(team, state)
        for role in role_filter:
            # Check specific assigned players first
            if role == PitcherRole.CLOSER:
                c = team.get_closer()
                if c and c in all_relievers: return c
            elif role == PitcherRole.SETUP_A:
                # Assuming index 0 is Primary
                if team.setup_pitchers:
                    idx = team.setup_pitchers[0]
                    if 0 <= idx < len(team.players):
                         p = team.players[idx]
                         if p in all_relievers: return p
            elif role == PitcherRole.SETUP_B:
                 # Assuming index 1+ is Secondary
                if len(team.setup_pitchers) > 1:
                    for idx in team.setup_pitchers[1:]:
                        if 0 <= idx < len(team.players):
                             p = team.players[idx]
                             if p in all_relievers: return p
            
            # Generic Role Search (for Middle, Long, or fallback Setup)
            # We need to correctly classify 'Middle' vs 'Long'
            candidates = []
            for p in all_relievers:
                p_role = self._get_pitcher_role_in_game(team, p)
                if p_role == role:
                    candidates.append(p)
            
            if candidates:
                # Sort by condition/ability
                candidates.sort(key=lambda x: (x.current_stamina, x.stats.overall_pitching()), reverse=True)
                return candidates[0]
                
        return None

    def _get_all_available_relievers(self, team: Team, state: GameState) -> List[Player]:
        used = state.home_pitchers_used if state.is_top else state.away_pitchers_used
        
        target_roster = team.active_roster
        target_rotation = team.rotation
        
        if self.team_level == TeamLevel.SECOND:
            target_roster = team.farm_roster
            target_rotation = team.farm_rotation
        elif self.team_level == TeamLevel.THIRD:
            target_roster = team.third_roster
            target_rotation = team.third_rotation
            
        rotation_p = [team.players[i] for i in target_rotation if 0 <= i < len(team.players)]
        
        avail = []
        for idx in target_roster:
            if not (0 <= idx < len(team.players)): continue
            p = team.players[idx]
            if p.position != Position.PITCHER: continue
            if p.is_injured: continue
            if p in used: continue
            if p in rotation_p: continue
            
            # Stamina Check (Absolute minimum)
            if p.current_stamina < 20: continue 
            
            avail.append(p)
        return avail

    def _get_pitcher_role_in_game(self, team: Team, player: Player) -> PitcherRole:
        """Helper to infer role from Team lists"""
        # Closer
        if team.closer_idx != -1 and team.players[team.closer_idx] == player:
            return PitcherRole.CLOSER
        
        # Setup (A=0, B=Rest)
        if team.setup_pitchers:
            if player in [team.players[i] for i in team.setup_pitchers if 0<=i<len(team.players)]:
                # Is it first setup?
                if team.setup_pitchers[0] < len(team.players) and team.players[team.setup_pitchers[0]] == player:
                    return PitcherRole.SETUP_A
                return PitcherRole.SETUP_B
        
        # Starter (Should be filtered out usually, but check)
        if player in [team.players[i] for i in team.rotation if 0<=i<len(team.players)]:
            return PitcherRole.STARTER
            
        # Specialist (Throws Left & High vsLeft)
        # Assuming we don't have detailed role stored, we infer
        if player.throws == "左":
            # Simplified: Lefties not in Setup/Closer are specialists if Stamina is low?
            # Or just treat as Middle for now?
            # Let's say if overall is low but vsLeft is high?
            if getattr(player.stats, 'vs_left_batter', 50) >= 60:
                return PitcherRole.SPECIALIST

        # Long Relief (High Stamina Middle)
        stats_stamina = player.stats.stamina if hasattr(player, 'stats') else 0
        if stats_stamina >= 60:
            return PitcherRole.LONG
            
        return PitcherRole.MIDDLE

class AIManager:
    def __init__(self, game_state_manager=None):
        # 投手管理は PitchingDirector で行うため、ここでは不要
        self.game_state_manager = game_state_manager
        
        # Get AI tendencies from settings (default 50 = normal)
        if game_state_manager:
            self.bunt_tendency = getattr(game_state_manager, 'ai_bunt_tendency', 50) / 50.0
            self.steal_tendency = getattr(game_state_manager, 'ai_steal_tendency', 50) / 50.0
            self.pitching_change_tendency = getattr(game_state_manager, 'ai_pitching_change_tendency', 50) / 50.0
            self.use_defensive_shift = getattr(game_state_manager, 'ai_defensive_shift', True)
        else:
            self.bunt_tendency = 1.0
            self.steal_tendency = 1.0
            self.pitching_change_tendency = 1.0
            self.use_defensive_shift = True

    def decide_strategy(self, state: GameState, offense_team, defense_team, batter: Player) -> str:
        score_diff = state.away_score - state.home_score if state.is_top else state.home_score - state.away_score
        is_late = state.inning >= 7
        is_close = abs(score_diff) <= 2
        
        bunt_skill = get_effective_stat(batter, 'bunt_sac')
        if state.outs == 0 and (state.runner_1b) and not state.runner_3b:
            batting_ab = batter.stats.overall_batting()
            if batter.position == Position.PITCHER and random.random() < self.bunt_tendency: return "BUNT"
            if ((is_close and is_late) or (bunt_skill > 70 and batting_ab < 45) or (state.runner_2b and is_close)) and random.random() < self.bunt_tendency:
                return "BUNT"
        
        # 二盗判定（1塁ランナーがいて2塁が空いている）
        if state.runner_1b and not state.runner_2b and not state.runner_3b and state.outs < 2:
            runner_spd = get_effective_stat(state.runner_1b, 'speed')
            runner_stl = get_effective_stat(state.runner_1b, 'steal')
            attempt_prob = 0.02 + (runner_spd - 50) * 0.003
            attempt_prob *= (0.7 + (runner_stl / 50.0) * 0.5)
            attempt_prob *= self.steal_tendency  # Apply AI steal tendency
            if is_close and is_late: attempt_prob *= 0.5 
            elif abs(score_diff) >= 4: attempt_prob *= 1.2 
            if random.random() < max(0.005, attempt_prob): return "STEAL"
        
        # 三盗判定（2塁ランナーがいて3塁が空いている）
        if state.runner_2b and not state.runner_3b and state.outs < 2:
            runner_spd = get_effective_stat(state.runner_2b, 'speed')
            runner_stl = get_effective_stat(state.runner_2b, 'steal')
            # 三盗は二盗より慎重に（確率を低めに）
            attempt_prob = 0.01 + (runner_spd - 60) * 0.002  # 足が速くないと試みない
            attempt_prob *= (0.5 + (runner_stl / 50.0) * 0.4)
            attempt_prob *= self.steal_tendency  # Apply AI steal tendency
            if is_close and is_late: attempt_prob *= 0.3  # 接戦終盤は特に慎重
            elif abs(score_diff) >= 4: attempt_prob *= 1.5  # 点差があれば積極的
            if random.random() < max(0.002, attempt_prob): return "STEAL"
        
        # スクイズ (0-1アウト、3塁ランナーあり、接戦)
        if state.runner_3b and state.outs < 2 and is_close:
            # 投手が打席 or 打撃力が低い(ミート<40) or 接戦で1点が欲しい
            if batter.position == Position.PITCHER: return "SQUEEZE"
            eff_contact = get_effective_stat(batter, 'contact', is_risp=True)
            if eff_contact < 40: return "SQUEEZE"
            # 終盤の同点・1点ビハインドなら強打者以外はスクイズ検討
            if is_late and score_diff <= 0 and get_effective_stat(batter, 'power') < 70:
                if random.random() < 0.4: return "SQUEEZE"

        # ヒットエンドラン (1アウト、1塁ランナー、ミートが高い、足がある)
        if state.outs == 1 and state.runner_1b and not state.runner_2b and not state.runner_3b:
            eff_contact = get_effective_stat(batter, 'contact')
            runner_spd = get_effective_stat(state.runner_1b, 'speed')
            if eff_contact > 65 and runner_spd > 65 and not is_late:
                 if random.random() < 0.3: return "HIT_AND_RUN"

        # 流し打ち (ランナー1塁で右打者が右方向へ打って進塁を助けるなど)
        # Shift破りとしてのAI判断は難しいが、状況打撃として導入
        if state.runner_1b and not state.runner_2b and state.outs < 2:
            # 右打者ならライト方向(流し)へ打つと1塁ランナーが3塁に行きやすい
            # 単純に「ミート重視かつ併殺回避」として流しを選択
            eff_contact = get_effective_stat(batter, 'contact')
            if eff_contact > 55:
                if random.random() < 0.25: return "NAGASHI"

        eff_power = get_effective_stat(batter, 'power', is_risp=state.is_risp())
        if state.balls >= 3 and state.strikes < 2 and eff_power > 65: return "POWER"
        
        eff_contact = get_effective_stat(batter, 'contact', is_risp=state.is_risp())
        eff_avoid_k = get_effective_stat(batter, 'avoid_k')
        if state.strikes == 2 and eff_contact > 50 and eff_avoid_k > 50: return "MEET"
            
        return "SWING"

    def decide_defensive_shifts(self, state: GameState, offense_team: Team, defense_team: Team, batter: Player, pitcher: Player) -> Dict[str, str]:
        """AIによる守備シフトの決定"""
        shifts = {"infield": "内野通常", "outfield": "外野通常"}
        
        # If defensive shift is disabled in settings, return default shifts
        if not self.use_defensive_shift:
            return shifts
        
        score_diff = state.home_score - state.away_score
        if not state.is_top: score_diff *= -1 # 守備側から見た点差
        
        is_close = abs(score_diff) <= 3  # 3点差以内 (拡大: 2→3)
        is_late = state.inning >= 6  # 6回以降 (拡大: 7→6)
        is_winning = score_diff > 0
        
        # --- 内野シフト ---
        # 前進守備: 3塁ランナーあり、0-1アウト、同点または僅差負け、または終盤の僅差勝ち
        if state.runner_3b and state.outs < 2:
            should_forward = False
            if score_diff == 0: should_forward = True # 同点なら絶対防ぐ
            elif score_diff <= -1 and score_diff >= -2: should_forward = True # 2点負けまで防ぐ
            elif is_late and score_diff >= 1 and score_diff <= 2: should_forward = True # 終盤2点リードまで守る
            
            if should_forward:
                shifts['infield'] = "前進守備"
        
        # ゲッツーシフト: 1塁ランナーあり、0-1アウト、2塁・3塁なし
        elif state.runner_1b and not state.runner_2b and not state.runner_3b and state.outs < 2:
            # 打者が鈍足またはゴロPなら積極的に敷く (閾値拡大: 60→70)
            batter_spd = get_effective_stat(batter, 'speed')
            if batter_spd < 70:
                shifts['infield'] = "ゲッツーシフト"
        
        # バントシフト: 投手またはバントの名手、かつ無死1塁/2塁
        elif (state.runner_1b or state.runner_2b) and state.outs == 0:
            bunt_skill = get_effective_stat(batter, 'bunt_sac')
            if batter.position == Position.PITCHER or bunt_skill > 65:  # 閾値緩和: 70→65
                shifts['infield'] = "バントシフト"

        # --- 外野シフト ---
        batter_pow = get_effective_stat(batter, 'power')
        
        # 長打力がある打者には深めシフト (閾値緩和: 75→65)
        if batter_pow > 65:
            shifts['outfield'] = "外野深め"
        # 長打力が低い打者には浅めシフト (閾値緩和: 35→50)
        elif batter_pow < 50:
            shifts['outfield'] = "外野浅め"
            
        # 2塁ランナーがいて、ワンヒットでの生還を阻止したい場合（前進）
        if state.runner_2b and is_close and shifts['outfield'] == "外野通常":
             # ただし長打警戒なら深め優先 (閾値緩和: 65→70)
             if batter_pow < 70:
                 shifts['outfield'] = "外野浅め"
                 
        # ピンチ時により積極的にシフトを適用
        if state.is_risp() and is_late:
            if shifts['infield'] == "内野通常" and state.outs < 2:
                # ピンチ時は3塁にランナーがいなくても前進気味に
                if is_close and (score_diff <= 0 or score_diff == 1):
                    shifts['infield'] = "前進守備"

        return shifts

    def decide_pitch_strategy(self, state: GameState, pitcher: Player, batter: Player) -> str:
        eff_control = get_effective_stat(pitcher, 'control', opponent=batter, is_risp=state.is_risp())
        if state.balls >= 3: return "STRIKE"
        if state.strikes == 2:
            has_breaking = len(pitcher.stats.pitches) > 0
            if has_breaking and eff_control > 40: return "BALL" 
        eff_power = get_effective_stat(batter, 'power', is_risp=state.is_risp())
        if state.is_risp() and not state.runner_1b and eff_power > 85 and state.inning >= 8 and abs(state.home_score - state.away_score) <= 1:
            return "WALK"
        return "NORMAL"

    def check_pinch_hitter(self, state: GameState, offense_team: Team, defense_team: Team, current_batter: Player, current_pitcher: Player) -> Optional[Player]:
        """ピンチヒッター起用判定"""
        score_diff = state.home_score - state.away_score
        if state.is_top: score_diff *= -1 # 攻撃側から見た点差
        
        is_risp = state.is_risp()
        is_late = state.inning >= 7
        is_close = abs(score_diff) <= 3
        is_losing = score_diff < 0
        
        # 1. 投手の打席: 終盤、接戦、または負けているなら代打
        if current_batter.position == Position.PITCHER:
            # 例外: 完封ペースや好投中の先発はそのまま打たせる可能性があるが、
            # 基本的に僅差の終盤は代打を送る
            
            # 自分が好投している（失点2以下）かつ勝っている場合
            pitcher_doing_well = False
            cur_p_runs = state.away_current_pitcher_runs if state.is_top else state.home_current_pitcher_runs
            # 注意: ここでのcurrent_pitcherは相手投手。自分の投手成績はGameStateから取る必要があるが、
            # current_batterが投手＝自分が投げている。
            # 簡易的に、7回以降で接戦なら代打を優先する
            
            should_sub = False
            if state.inning >= 7 and is_close: should_sub = True
            elif state.inning >= 6 and is_losing and is_risp: should_sub = True
            elif state.inning >= 8: should_sub = True # 8回以降は投手には代打
            
            if should_sub:
                return self._select_best_pinch_hitter(offense_team, current_pitcher)
            return None

        # 2. 野手の打席: スタメン野手への代打
        # 条件: 終盤の勝負所 (得点圏 or 接戦ビハインド) かつ 相手投手の左右相性が悪い/打撃能力が低い
        if (is_late and is_close) or (state.inning >= 8 and is_losing and score_diff >= -4):
            # チャンス時の代打
            if is_risp:
                eff_contact = get_effective_stat(current_batter, 'contact', opponent=current_pitcher, is_risp=True)
                eff_power = get_effective_stat(current_batter, 'power', opponent=current_pitcher, is_risp=True)
                
                # 現在の打者が平均以下なら代打検討
                if eff_contact < 50 or (score_diff < 0 and eff_power < 50):
                    candidate = self._select_best_pinch_hitter(offense_team, current_pitcher)
                    if candidate:
                        cand_contact = get_effective_stat(candidate, 'contact', opponent=current_pitcher, is_risp=True)
                        # 代打の方が明らかに打てるなら交代 (+10以上)
                        if cand_contact > eff_contact + 10:
                            return candidate
        
        return None

    def _select_best_pinch_hitter(self, team: Team, opponent_pitcher: Player) -> Optional[Player]:
        """ベンチから最適な代打を選出"""
        candidates = []
        used_players = set()
        # スタメンは除外
        used_players.update([team.players[i] for i in team.current_lineup if 0 <= i < len(team.players)])
        # 交代済み選手も本来除外すべきだが、game_stateで管理されている必要がある。
        # ここでは簡易的に「現在スタメンに入っていない選手」をベンチとみなす。
        # ただし既に出場した選手を除外するロジックが必要。
        # LiveGameEngine側で管理している出場済みリストが必要だが、ここではTeamオブジェクトのactive_rosterから
        # lineupに含まれていない選手を探す。
        
        bench = []
        for pid in team.active_roster:
            if 0 <= pid < len(team.players):
                p = team.players[pid]
                # 投手は代打の対象外(大谷ルール考慮なし)
                if p.position == Position.PITCHER: continue 
                if p in used_players: continue
                # 既に今日出場した選手は出場不可
                if getattr(p, 'has_played_today', False): continue 
                if p.is_injured: continue
                
                bench.append(p)
                
        if not bench: return None
        
        # 評価関数: 対投手能力重視
        best_p = None
        best_score = -1
        
        for p in bench:
            # チャンス×左右相性を加味した能力
            con = get_effective_stat(p, 'contact', opponent=opponent_pitcher, is_risp=True)
            pwr = get_effective_stat(p, 'power', opponent=opponent_pitcher, is_risp=True)
            
            # 代打○のスキルがあれば... (未実装ならconditionでボーナスでも)
            score = con * 0.6 + pwr * 0.4
            
            # ミート/パワーが高い順
            if score > best_score:
                best_score = score
                best_p = p
                
        return best_p

class PitchGenerator:
    PITCH_DATA = {
        "ストレート":     {"base_speed": 145, "h_break": 0,   "v_break": 10,  "spin_ratio": 1.0},
        "ツーシーム":     {"base_speed": 145, "h_break": 12,  "v_break": 2,   "spin_ratio": 0.95},
        "カットボール":   {"base_speed": 140, "h_break": -8,  "v_break": 3,   "spin_ratio": 1.05},
        "スライダー":     {"base_speed": 132, "h_break": -20, "v_break": -3,  "spin_ratio": 1.15},
        "カーブ":         {"base_speed": 115, "h_break": -12, "v_break": -25, "spin_ratio": 1.20},
        "フォーク":       {"base_speed": 136, "h_break": 0,   "v_break": -30, "spin_ratio": 0.60},
        "チェンジアップ": {"base_speed": 128, "h_break": 8,   "v_break": -15, "spin_ratio": 0.85},
        "シュート":       {"base_speed": 140, "h_break": 18,  "v_break": -6,  "spin_ratio": 0.98},
        "シンカー":       {"base_speed": 142, "h_break": 15,  "v_break": -10, "spin_ratio": 0.90},
        "スプリット":     {"base_speed": 140, "h_break": 3,   "v_break": -28, "spin_ratio": 0.55},
        "ナックル":       {"base_speed": 105, "h_break": 0,   "v_break": -20, "spin_ratio": 0.10}
    }

    def generate_pitch(self, pitcher: Player, batter: Player, catcher: Player, state: GameState, strategy="NORMAL", stadium: Stadium = None, aptitude_val: int = 4) -> PitchData:
        is_risp = state.is_risp()
        is_close = abs(state.home_score - state.away_score) <= 2
        
        velocity = get_effective_stat(pitcher, 'velocity', batter, is_risp, is_close, aptitude_val=aptitude_val)
        control = get_effective_stat(pitcher, 'control', batter, is_risp, is_close, aptitude_val=aptitude_val)
        
        if stadium: control = control / max(0.5, stadium.pf_bb)
        if catcher:
            lead = get_effective_stat(catcher, 'catcher_lead', is_close_game=is_close)
            control += (lead - 50) * 0.2
        
        # スタミナはPlayer.current_stamina（球数ベース）を使用
        current_stamina = pitcher.current_stamina
        fatigue = 1.0
        if current_stamina < 20: fatigue = 0.9 + (current_stamina / 200.0)
        if current_stamina <= 0: fatigue = 0.8
        
        # 投球ごとに1球消費（RISPでは1.2球）
        pitch_cost = 1.0
        if is_risp: pitch_cost = 1.2
        pitcher.current_stamina = max(0, pitcher.current_stamina - pitch_cost)
        
        base_straight_prob = 0.35 + (velocity - 145) * 0.01
        base_straight_prob = max(0.3, min(0.7, base_straight_prob))
        if getattr(pitcher.stats, 'movement', 50) > 70: base_straight_prob -= 0.1
        if strategy == "STRIKE": base_straight_prob += 0.2 
        elif strategy == "BALL": base_straight_prob -= 0.2 
        elif state.strikes == 2: base_straight_prob -= 0.15 
        
        pitch_type = "ストレート"
        breaking_balls = getattr(pitcher.stats, 'breaking_balls', [])
        
        if strategy != "WALK" and breaking_balls:
            if random.random() >= base_straight_prob:
                pitches = pitcher.stats.pitches
                if pitches:
                    total_val = 0
                    pitch_candidates = []
                    for p_name in pitches.keys():
                        qual = pitcher.stats.get_pitch_quality(p_name)
                        total_val += qual
                        pitch_candidates.append((p_name, qual))
                    r = random.uniform(0, total_val)
                    curr = 0
                    for p_name, qual in pitch_candidates:
                        curr += qual
                        if r <= curr:
                            pitch_type = p_name
                            break
                else: pitch_type = breaking_balls[0]
            
        base = self.PITCH_DATA.get(pitch_type, self.PITCH_DATA["ストレート"])
        
        p_stuff = pitcher.stats.get_pitch_stuff(pitch_type)
        p_move = pitcher.stats.get_pitch_movement(pitch_type)
        
        condition_diff = pitcher.condition - 5
        cond_mult = 1.0 + (condition_diff * 0.01)
        p_stuff = max(1, p_stuff * cond_mult)
        p_move = max(1, p_move * cond_mult)

        # Random variation, but never exceed pitcher's base velocity
        # Generate velocity between 97% and 100% of max ability
        max_velo = pitcher.stats.velocity  # Original ability is the max
        min_velo = max_velo * 0.97  # 97% of max
        base_velo = random.uniform(min_velo, max_velo) * fatigue
        
        if pitch_type != "ストレート":
            speed_ratio = base["base_speed"] / 145.0
            base_velo *= speed_ratio
        
        velo = max(80, min(max_velo, base_velo))  # Cap at pitcher's actual ability



        base_spin = velo * 15.5
        spin_ratio = base.get("spin_ratio", 1.0)
        calculated_spin = base_spin * spin_ratio
        is_low_spin_pitch = spin_ratio < 0.8
        stuff_mod = (p_stuff - 50) * 8.0 
        movement_mod = (p_move - 50) * 4.0 
        
        if is_low_spin_pitch: calculated_spin -= (stuff_mod + movement_mod)
        else: calculated_spin += (stuff_mod + movement_mod)
            
        calculated_spin += random.gauss(0, 50)
        spin_rate = int(max(100, calculated_spin))

        move_factor = 1.0 + (p_move - 50) * 0.01
        if is_low_spin_pitch:
            low_spin_bonus = max(0, (1500 - spin_rate) / 1000.0)
            spin_move_factor = 1.0 + low_spin_bonus
        else:
            spin_move_factor = spin_rate / 2200.0
        
        h_brk = base["h_break"] * move_factor * spin_move_factor + random.gauss(0, 2)
        v_brk = base["v_break"] * move_factor * spin_move_factor + random.gauss(0, 2)

        loc = self._calc_location(control * fatigue, state, strategy)
        traj = self._calc_traj(velo, h_brk, v_brk, loc, spin_rate, pitch_type)
        
        return PitchData(pitch_type, round(velo,1), spin_rate, h_brk, v_brk, loc, (0,18.44,1.8), traj)

    def _calc_location(self, control, state, strategy):
        if strategy == "WALK": return PitchLocation(1.0, 1.5, False)
        
        zone_target_prob = 0.54 + (control - 50) * 0.003
        if strategy == "STRIKE": zone_target_prob += 0.25 
        elif strategy == "BALL": zone_target_prob -= 0.3
        if state.balls == 3: zone_target_prob += 0.25
        if state.strikes == 0 and state.balls == 0: zone_target_prob += 0.1
        zone_target_prob = max(0.1, min(0.98, zone_target_prob))
        
        tx, tz = 0, STRIKE_ZONE['center_z']
        sigma = max(0.05, 0.22 - (control * 0.002))
        
        if random.random() < zone_target_prob:
            if random.random() < 0.35: tx = 0; tz = STRIKE_ZONE['center_z']
            else:
                tx = random.choice([-0.2, 0.2])
                tz = STRIKE_ZONE['center_z'] + random.choice([-0.25, 0.25])
        else:
            tx = random.choice([-0.28, 0.28]) 
            tz = STRIKE_ZONE['center_z'] + random.choice([-0.30, 0.30]) 

        ax = random.gauss(tx, sigma); az = random.gauss(tz, sigma)
        is_strike = (abs(ax) <= STRIKE_ZONE['half_width'] + 0.036 and abs(az - STRIKE_ZONE['center_z']) <= STRIKE_ZONE['half_height'] + 0.036)
        return PitchLocation(ax, az, is_strike)

    def _calc_traj(self, velo, hb, vb, loc, spin_rate, pitch_type):
        path = []; start = (random.uniform(-0.05, 0.05), 18.44, 1.8); end = (loc.x, 0, loc.z)
        steps = 15
        for i in range(steps + 1):
            t = i/steps
            break_t = t ** 1.5
            x = start[0] + (end[0]-start[0])*t + (hb/100 * 0.3) * math.sin(break_t * math.pi)
            y = start[1] * (1-t)
            z = start[2] + (end[2]-start[2])*t + (vb/100 * 0.3) * (t**2) 
            path.append((x,y,z))
        return path

class BattedBallGenerator:
    def generate(self, batter: Player, pitcher: Player, pitch: PitchData, state: GameState, strategy="SWING", aptitude_val: int = 4):
        is_risp = state.is_risp()
        is_close = abs(state.home_score - state.away_score) <= 2

        power = get_effective_stat(batter, 'power', opponent=pitcher, is_risp=is_risp, is_close_game=is_close)
        contact = get_effective_stat(batter, 'contact', opponent=pitcher, is_risp=is_risp, is_close_game=is_close)
        gap = get_effective_stat(batter, 'gap', opponent=pitcher, is_risp=is_risp)
        trajectory = getattr(batter.stats, 'trajectory', 2)
        
        p_stuff = pitcher.stats.get_pitch_stuff(pitch.pitch_type)
        p_move = pitcher.stats.get_pitch_movement(pitch.pitch_type)
        p_gb_tendency = getattr(pitcher.stats, 'gb_tendency', 50)
        
        meet_bonus = 15 if strategy == "MEET" else (-20 if strategy == "POWER" else 0)
        ball_penalty = 0 if pitch.location.is_strike else 20
        # 修正: contact能力差を圧縮 (50からの偏差を50%に圧縮してBABIP差を縮める)
        # 30→40, 50→50, 70→60, 90→70 に圧縮
        base_con_eff = 50 + (contact - 50) * 0.5
        con_eff = base_con_eff + meet_bonus - (p_move - 50) * 0.20 - ball_penalty
        
        # --- 打球速度を先に計算し、それでHard/Mid/Softを判定 ---
        # ベース速度: パワー・コンタクト依存
        base_v = 140 + (power - 50) * 0.3
        if strategy == "POWER": base_v += 5
        elif strategy == "MEET": base_v -= 5
        elif strategy == "NAGASHI": 
            base_v -= 8 # Slight power penalty
            con_eff += 8 # Contact bonus
        
        # --- 芯を捉えた/外したの判定 ---
        # 芯を捉える確率: コンタクト能力依存を軽減 (10-15%に範囲を狭める)
        barrel_chance = 0.15 + con_eff * 0.0005  # 能力依存を半減
        barrel_chance = max(0.15, min(0.20, barrel_chance))
        
        # 芯を外す確率: コンタクトが低いほど高い (30-35%に範囲を狭める)
        mishit_chance = 0.50 - con_eff * 0.001  # 能力依存を軽減
        mishit_chance = max(0.40, min(0.50, mishit_chance))
        
        contact_roll = random.random()
        if contact_roll < barrel_chance:
            # 芯を捉えた (バレル): 打球速度ボーナス
            base_v += 20 + power * 0.1
        elif contact_roll < mishit_chance:
            # 芯を外した: 打球速度デバフ
            base_v -= 50
        
        # ランダム要素を追加 (標準偏差15km/hでばらつき)
        velo = base_v + random.gauss(0, 10)
        velo = max(80, min(200, velo))  # 80-200km/hに制限
        
        # --- 打球速度でHard/Mid/Softを判定 (MLB基準) ---
        # Hard: 152km/h (95mph) 以上
        # Medium: 128km/h (80mph) ~ 152km/h
        # Soft: 128km/h 未満
        if velo >= 152:
            quality = "hard"
        elif velo >= 128:
            quality = "medium"
        else:
            quality = "soft"
        
        # 弾道による打球角度の影響 (画像の分布を再現)
        # 弾道1: 10°を頂上、対称的な広い分布
        # 弾道2: 17°を頂上、やや狭い分布
        # 弾道3: 23°を頂上、さらに狭く右に偏った分布
        # 弾道4: 30°を頂上、最も狭く右に偏った分布
        traj_peaks = {1: 10, 2: 17, 3: 23, 4: 30}
        traj_peak = traj_peaks.get(trajectory, 17)
        
        # 弾道が高いほど分散が小さくなる（打球が安定）
        # 弾道1→25°, 弾道2→20°, 弾道3→16°, 弾道4→13° の標準偏差
        traj_variances = {1: 40, 2: 33, 3: 27, 4: 20}
        base_variance = traj_variances.get(trajectory, 20)
        
        # 弾道3,4は右に偏った分布（高角度側に裾野が伸びる）
        # 左右で異なる標準偏差を使用して非対称分布を実現
        traj_skew = {1: 0, 2: 0.1, 3: 0.25, 4: 0.4}  # 右への偏り係数
        skew = traj_skew.get(trajectory, 0)
        
        # 投手のゴロ傾向による影響（GB投手は角度が下がる）
        angle_center = traj_peak - (p_gb_tendency - 50) * 0.15
        
        # 投球位置による微調整
        if pitch.location.z < 0.5: angle_center -= 4  # 低め→ゴロ傾向
        if pitch.location.z > 0.9: angle_center += 4  # 高め→フライ傾向
        
        # ギャップヒッターはライナー性の打球（15°付近）が出やすい
        if gap > 60 and quality != "soft" and random.random() < (gap / 180):
            angle_center = 15
        
        if strategy == "BUNT":
            angle = -20; velo = 30 + random.uniform(-5, 5)
            bunt_skill = get_effective_stat(batter, 'bunt_sac')
            if random.uniform(0, 100) > bunt_skill:
                if random.random() < 0.5: angle = 30
                else: velo += 20
            quality = "soft"
        else:
            # 弾道に応じた非対称分布で打球角度を生成
            # まず正規分布で基本値を生成
            base_angle = random.gauss(0, 1)  # 標準正規分布
            
            # 弾道3,4は右に偏った分布（高角度側に裾野）
            if base_angle > 0:
                # 正の方向（高角度側）は分散を広げる
                angle = angle_center + base_angle * base_variance * (1 + skew)
            else:
                # 負の方向（低角度側）は分散を狭める
                angle = angle_center + base_angle * base_variance * (1 - skew * 0.5)
            
            # -50°～70°の範囲に制限
            angle = max(-50, min(70, angle))
        
        # ハードヒットの最低速度保証
        if quality == "hard": velo = max(velo, 152)
        
        # --- ゴロ減少、フライ増加に調整 ---
        gb_limit = 15 + (140 - velo) * 0.06  # ゴロ判定を狭く (変更なし)
        ld_limit = 24 - (140 - velo) * 0.02  # ライナー判定 (28→24: LD%下げ)
        # FB% = FLYBALL + POPUP (全フライ)
        # IFFB% = POPUP / (FLYBALL + POPUP)
        
        if angle < gb_limit: htype = BattedBallType.GROUNDBALL
        elif angle < ld_limit: htype = BattedBallType.LINEDRIVE
        elif angle < 60: htype = BattedBallType.FLYBALL  # フライ判定を広く (55→60: IFFB%下げ)
        else: htype = BattedBallType.POPUP  # 内野フライ (IFFB計算用)
        
        v_ms = velo / 3.6
        
        # --- 修正: マイナス角度の打球も正しく計算 ---
        if angle < 0:
            # マイナス角度の場合、ゴロとして地面を転がる距離を計算
            # 打球速度に基づく飛距離（角度の絶対値が大きいほど短い）
            angle_factor = 1.0 - (abs(angle) / 90.0)  # -50度で約0.44
            vacuum_dist = (v_ms**2 / 9.8) * angle_factor * 0.5
        else:
            vacuum_dist = (v_ms**2 * math.sin(math.radians(2 * angle))) / 9.8
        
        # 無段階式: 速度と角度で減衰を計算
        # 速度減衰: 速いほど空気抵抗が大きい（真空飛距離がv^2なので、減衰しても速いほど飛ぶ）
        speed_factor = 0.96 - (velo - 60) / 380.0  # 60km/h→0.96, 180km/h→0.64
        speed_factor = max(0.58, min(0.96, speed_factor))
        
        # 角度減衰: 高いほど減衰（0度で0%減衰、45度以上で最大減衰）
        if angle > 0:
            angle_penalty = 1.0 - (angle / 68.0) * 0.34  # 45度で22%減衰、68度で34%減衰
            angle_penalty = max(0.62, min(1.0, angle_penalty))
        else:
            # マイナス角度（ゴロ）は別処理
            angle_penalty = 0.89
        
        drag_factor = speed_factor * angle_penalty
             
        dist = max(5, abs(vacuum_dist * drag_factor))  # 最低5mは飛ぶようにする
        
        if htype == BattedBallType.GROUNDBALL: dist *= 0.5
        elif htype == BattedBallType.POPUP: dist *= 0.3
        
        # --- 修正: ゴロのスプレー角度を内野方向に調整 ---
        if htype == BattedBallType.GROUNDBALL:
            # キャッチャー/ピッチャー方向(0度付近)を減らし、内野方向に広げる
            # 左右に振れた角度で生成（平均±20度、標準偏差18度）
            base_spray = random.choice([-1, 1]) * random.uniform(8, 35)
            spray = base_spray + random.gauss(0, 8)
        else:
            spray = random.gauss(0, 25)
        rad = math.radians(spray)
        land_x = dist * math.sin(rad)
        land_y = dist * math.cos(rad)
        
        # --- 修正: マイナス角度でも滞空時間を正の値に ---
        if angle < 0:
            # ゴロとして処理（地面を転がる時間）
            hang_time = max(0.3, dist / (v_ms * 0.8))
        else:
            v_y = v_ms * math.sin(math.radians(angle))
            hang_time = max(0.3, (2 * v_y) / 9.8)
            
        if htype == BattedBallType.GROUNDBALL:
            hang_time = max(0.3, dist / (v_ms * 0.8))

        # --- Nagashi (Opposite) Handling ---
        if strategy == "NAGASHI":
            # Force opposite field
            # RHB (Right bat) -> Right Field (Positive spray)
            # LHB (Left bat) -> Left Field (Negative spray)
            # Switch hitter -> Assume batting vs opposite hand pitcher? 
            # BattedBallGenerator doesn't strictly know current stance, but we can assume normal platoon split or just check stats
            # Ideally passed in, but 'batter.bats' is static. 
            # Let's check pitcher hand? No, batter orientation matters.
            # Assuming batter.bats is reliable.
            target_spray_center = 0
            bats = getattr(batter, 'bats', '右')
            if bats == '右': target_spray_center = 25 # Right field
            elif bats == '左': target_spray_center = -25 # Left field
            else: 
                # Switch: opposite of pitcher throws
                p_throws = getattr(pitcher, 'throws', '右')
                if p_throws == '右': target_spray_center = -25 # Batting Left -> Left Field
                else: target_spray_center = 25 # Batting Right -> Right Field
            
            # Override spray
            spray = random.gauss(target_spray_center, 15)
            # Re-calculate landing
            rad = math.radians(spray)
            land_x = dist * math.sin(rad)
            land_y = dist * math.cos(rad)
            return BattedBallData(velo, angle, spray, htype, dist, hang_time, land_x, land_y, [], quality)
        
        return BattedBallData(velo, angle, spray, htype, dist, hang_time, land_x, land_y, [], quality)

class AdvancedDefenseEngine:
    def __init__(self, is_postseason: bool = False):
        self.is_postseason = is_postseason

    def judge(self, ball: BattedBallData, defense_team: Team, team_level: TeamLevel = TeamLevel.FIRST, stadium: Stadium = None, current_pitcher: Player = None, league_stats: Dict[str, float] = None, batter: Player = None, shifts: Dict[str, str] = None):
        abs_spray = abs(ball.spray_angle)
        self.league_stats = league_stats or {}
        
        base_fence = 122 - (abs_spray / 45.0) * (122 - 100)
        pf_hr = stadium.pf_hr if stadium else 1.0
        # パークファクター効果を緩和 (変化量を15%に減衰)
        fence_adjustment = 1.0 + (pf_hr - 1.0) * 0.15
        fence_dist = base_fence / fence_adjustment 
        
        # フライとライナーの両方でHR判定（飛距離がフェンスを超えれば）
        if ball.hit_type in [BattedBallType.FLYBALL, BattedBallType.LINEDRIVE] and ball.distance > fence_dist and abs_spray < 45:
            return PlayResult.HOME_RUN
        
        target_pos = (ball.landing_x, ball.landing_y)
        best_fielder, fielder_type, initial_pos = self._find_nearest_fielder(target_pos, defense_team, team_level, current_pitcher, shifts)
        
        if not best_fielder: 
            if abs_spray > 45: return PlayResult.FOUL
            return PlayResult.SINGLE 

        # --- 捕球確率計算 ---
        # 実際の捕球確率（選手能力あり）
        actual_catch_prob = self._calculate_catch_prob(ball, target_pos, initial_pos, best_fielder, stadium, is_average=False)
        # 平均的な野手（リーグ平均データ使用）の捕球確率（UZR基準用）
        avg_catch_prob = self._calculate_catch_prob(ball, target_pos, initial_pos, best_fielder, stadium, is_average=True)
        
        is_caught = random.random() < actual_catch_prob
        
        if abs_spray > 45:
            if is_caught and ball.hit_type in [BattedBallType.FLYBALL, BattedBallType.POPUP]: return PlayResult.FLYOUT
            else: return PlayResult.FOUL

        potential_hit_result = self._judge_hit_type_potential(ball, target_pos, stadium, fielder=best_fielder, batter=batter)
        
        # --- UZR計算用の得点価値設定 ---
        # 捕ればアウト、落とせばヒット。この価値の差分がプレーの価値。
        run_value_out = RUN_VALUES["Out"]
        run_value_hit = RUN_VALUES["Single"]
        if potential_hit_result == PlayResult.DOUBLE: run_value_hit = RUN_VALUES["Double"]
        elif potential_hit_result == PlayResult.TRIPLE: run_value_hit = RUN_VALUES["Triple"]
        
        # プレー価値 = ヒット時の得点期待値 - アウト時の得点期待値 (約1.2点前後)
        play_value = run_value_hit - run_value_out

        if best_fielder.position != Position.CATCHER:
            self._update_defensive_metrics(best_fielder, team_level, avg_catch_prob, is_caught, play_value)

        if is_caught:
            # エラー判定 (ErrR)
            rec = best_fielder.get_record_by_level(team_level)
            pos_err_rate = 0.015 if best_fielder.position in [Position.FIRST, Position.LEFT, Position.RIGHT] else 0.025
            error_rating = get_effective_stat(best_fielder, 'error')
            
            # エラー発生確率
            error_prob = max(0.001, (pos_err_rate * 2.0) - (error_rating * 0.0005))
            
            # 平均的なエラー率 (リーグ実績データを使用)
            # 例: league_stats['error_rate_SHORTSTOP']
            pos_name = best_fielder.position.name
            avg_error_prob = self.league_stats.get(f'error_rate_{pos_name}', max(0.001, (pos_err_rate * 2.0) - (50.0 * 0.0005)))

            # ErrRの価値基準: エラー1つにつき約0.8点相当の損失とする
            error_run_value = 0.8 

            if random.random() < error_prob:
                # エラー発生: 平均的な選手ならエラーしない確率 * 損失
                loss = (1.0 - avg_error_prob) * error_run_value
                rec.uzr_errr -= (loss * UZR_SCALE["ErrR"])
                rec.def_drs_raw -= (loss * UZR_SCALE["ErrR"])
                return PlayResult.ERROR
            else:
                # エラー回避: 平均的な選手がエラーする確率 * 利得 (ごくわずかだが積み重なる)
                gain = avg_error_prob * error_run_value
                rec.uzr_errr += (gain * UZR_SCALE["ErrR"])
                rec.def_drs_raw += (gain * UZR_SCALE["ErrR"])
            
            if ball.hit_type == BattedBallType.FLYBALL: return PlayResult.FLYOUT
            if ball.hit_type == BattedBallType.POPUP:
                # 内野フライは内野手が捕球した場合のみPOPUP_OUTとして記録
                infield_positions = [Position.PITCHER, Position.CATCHER, Position.FIRST, 
                                     Position.SECOND, Position.THIRD, Position.SHORTSTOP]
                if best_fielder.position in infield_positions:
                    return PlayResult.POPUP_OUT
                else:
                    # 外野手が捕球した高いフライはFLYOUTとして記録
                    return PlayResult.FLYOUT
            if ball.hit_type == BattedBallType.LINEDRIVE: return PlayResult.LINEOUT
            
            return self._judge_grounder_throw(best_fielder, ball, team_level)
        else:
            return potential_hit_result

    def _calculate_catch_prob(self, ball, target_pos, initial_pos, fielder, stadium, is_average=False):
        """捕球確率を計算する共通メソッド"""
        dist_to_ball = math.sqrt((target_pos[0] - initial_pos[0])**2 + (target_pos[1] - initial_pos[1])**2)
        
        if is_average:
            avg_def = self.league_stats.get('avg_defense', 50.0)
            avg_spd = self.league_stats.get('avg_speed', 50.0)
            adjusted_range = avg_def  # 守備範囲をそのまま使用（能力値を反映）
            max_speed = 7.8 + (avg_spd - 50) * 0.01
        else:
            range_stat = fielder.stats.get_defense_range(getattr(Position, fielder.position.name, Position.DH))
            adjusted_range = range_stat  # 守備範囲をそのまま使用（能力値を反映）
            adjusted_range = adjusted_range * (1.0 + (fielder.condition - 5) * 0.005)
            speed_stat = get_effective_stat(fielder, 'speed')
            max_speed = 7.8 + (speed_stat - 50) * 0.01

        reaction_delay = 0.40 - (adjusted_range / 1500.0) 
        time_needed = reaction_delay + (dist_to_ball / max_speed)
        
        if ball.hit_type in [BattedBallType.FLYBALL, BattedBallType.POPUP, BattedBallType.LINEDRIVE]:
            time_available = ball.hang_time
            if ball.hit_type == BattedBallType.LINEDRIVE:
                 if dist_to_ball < 2.5: time_needed = 0 
        else:
            ball_speed_ms = (ball.exit_velocity / 3.6) * 0.6 
            time_available = dist_to_ball / max(1.0, ball_speed_ms)
            if ball.hit_type == BattedBallType.GROUNDBALL and ball.distance < 30:
                 time_available = 10.0 

        time_diff = time_available - time_needed
        
        # ===== 捕球確率計算（BABIP .300-.320 目標・大幅緩和版） =====
        # 内野フライ(POPUP)は滞空時間が長くほぼ確実にアウト
        if ball.hit_type == BattedBallType.POPUP:
            catch_prob = 0.97  # 内野フライでも若干のヒット可能性 (99→97%)
        # 外野定位置のフライ（85-100m、移動距離少ない）→ 守備位置付近は高確率アウト
        elif ball.hit_type == BattedBallType.FLYBALL and 75 < ball.distance < 105 and dist_to_ball < 15:
            catch_prob = 0.94  # 守備位置付近 (92→94%)
        # 外野定位置付近のフライ（移動距離中程度）
        elif ball.hit_type == BattedBallType.FLYBALL and dist_to_ball < 25:
            catch_prob = 0.88  # 定位置付近 (85→88%)
        else:
            # 通常の計算（タイム差に基づく）- BABIP大幅向上
            if time_diff >= 1.0:
                catch_prob = 0.78  # 余裕のあるプレー (75→78%)
            elif time_diff >= 0.5:
                catch_prob = 0.55 + (time_diff - 0.5) * 0.46  # 0.55-0.78
            elif time_diff >= 0.0:
                catch_prob = 0.35 + (time_diff / 0.5) * 0.20  # 0.35-0.55（際どいプレー）
            elif time_diff > -0.3:
                ratio = (time_diff + 0.3) / 0.3
                catch_prob = ratio * 0.18  # 0-0.18（難しい打球）
            elif time_diff > -0.6:
                ratio = (time_diff + 0.6) / 0.3
                catch_prob = ratio * 0.01  # 0-0.01（非常に難しい）→ ほぼヒット
            else:
                catch_prob = 0.0  # 届かない
        
        # --- 内野ゴロの守備位置付近も緩和 ---
        if ball.hit_type == BattedBallType.GROUNDBALL and dist_to_ball < 8:
            catch_prob = max(catch_prob, 0.85)  # 守備位置正面 (80→85%)
        elif ball.hit_type == BattedBallType.GROUNDBALL and dist_to_ball < 15:
            catch_prob = max(catch_prob, 0.70)  # 守備範囲内 (65→70%)
        
        # --- BABIP能力依存を最小化: 全員.300前後を目指す ---
        # ハードコンタクトのボーナス (緩和: 22%→12%減少)
        if ball.contact_quality == "hard": 
            catch_prob *= 0.95  # ハードヒットは12%減少
        
        # ライナーのボーナス (緩和: 45%→30%減少)
        if ball.hit_type == BattedBallType.LINEDRIVE: 
            catch_prob *= 0.90  # ライナーは30%減少
        
        # --- ソフトコンタクトのペナルティも最小限に ---
        if ball.contact_quality == "soft" and ball.hit_type in [BattedBallType.FLYBALL, BattedBallType.POPUP]:
            catch_prob = max(catch_prob, 0.60)  # ソフトフライでも40%ヒット (68→60%)
        
        # キャッチャー前のぼてぼてゴロ（内野安打増加）
        if ball.hit_type == BattedBallType.GROUNDBALL and ball.distance < 15 and ball.contact_quality == "soft":
            catch_prob = min(catch_prob, 0.68)  # ぼてぼては意外とヒット (78→68%)
        elif ball.hit_type == BattedBallType.GROUNDBALL and ball.distance < 25 and ball.contact_quality == "soft":
            catch_prob = min(catch_prob, 0.62)  # (75→62%)
        
        if stadium: catch_prob /= stadium.pf_1b
        return max(0.0, min(0.99, catch_prob))


    def _find_nearest_fielder(self, ball_pos, team, team_level, current_pitcher, shifts=None):
        min_dist = 999.0; best_f = None; best_type = ""; best_init = (0,0)
        lineup = team.current_lineup
        if team_level == TeamLevel.SECOND: lineup = team.farm_lineup
        elif team_level == TeamLevel.THIRD: lineup = team.third_lineup
        
        # Handle empty lineup - use roster directly
        if not lineup:
            lineup = []
            roster_indices = team.farm_roster if team_level == TeamLevel.SECOND else (team.third_roster if team_level == TeamLevel.THIRD else team.active_roster)
            if roster_indices:
                lineup = roster_indices[:9]
        
        pos_map = {}
        for idx in lineup:
            if 0 <= idx < len(team.players):
                p = team.players[idx]
                # Skip players whose level doesn't match game level (stale lineup index issue)
                if team_level != TeamLevel.FIRST and p.team_level != team_level:
                    continue
                if p.position != Position.DH and p.position != Position.PITCHER: pos_map[p.position] = p
        
        # If not enough fielders due to level mismatch, get from roster
        if len(pos_map) < 7 and team_level != TeamLevel.FIRST:
            roster_indices = team.farm_roster if team_level == TeamLevel.SECOND else team.third_roster
            for idx in roster_indices:
                if 0 <= idx < len(team.players):
                    p = team.players[idx]
                    if (p.team_level == team_level 
                        and p.position != Position.DH 
                        and p.position != Position.PITCHER
                        and p.position not in pos_map
                        and not p.is_injured):
                        pos_map[p.position] = p
        
        if current_pitcher:
             pos_map[Position.PITCHER] = current_pitcher

        # --- Shift Logic ---
        temp_coords = FIELD_COORDS.copy()
        infield_shift = shifts.get('infield', "内野通常") if shifts else "内野通常"
        outfield_shift = shifts.get('outfield', "外野通常") if shifts else "外野通常"

        if infield_shift == "前進守備":
            for pos in [Position.FIRST, Position.SECOND, Position.THIRD, Position.SHORTSTOP]:
                if pos in temp_coords:
                    orig = temp_coords[pos]
                    temp_coords[pos] = (orig[0], orig[1] - 9.0)
        elif infield_shift == "ゲッツーシフト":
            if Position.SHORTSTOP in temp_coords: temp_coords[Position.SHORTSTOP] = (-6.0, 36.0)
            if Position.SECOND in temp_coords: temp_coords[Position.SECOND] = (6.0, 36.0)
        elif infield_shift == "バントシフト":
             if Position.FIRST in temp_coords: temp_coords[Position.FIRST] = (14.0, 16.0)
             if Position.THIRD in temp_coords: temp_coords[Position.THIRD] = (-14.0, 16.0)

        if outfield_shift == "外野浅め":
            for pos in [Position.LEFT, Position.CENTER, Position.RIGHT]:
                if pos in temp_coords:
                    orig = temp_coords[pos]
                    temp_coords[pos] = (orig[0], orig[1] - 12.0)
        elif outfield_shift == "外野深め":
            for pos in [Position.LEFT, Position.CENTER, Position.RIGHT]:
                if pos in temp_coords:
                    orig = temp_coords[pos]
                    temp_coords[pos] = (orig[0], orig[1] + 10.0)

        for pos_enum, coords in temp_coords.items():
            if pos_enum in pos_map:
                dist = math.sqrt((ball_pos[0] - coords[0])**2 + (ball_pos[1] - coords[1])**2)
                if dist < min_dist:
                    min_dist = dist; best_f = pos_map[pos_enum]; best_type = pos_enum.name; best_init = coords
        return best_f, best_type, best_init

    def _judge_grounder_throw(self, fielder, ball, team_level):
        base_1b_pos = (20.0, 20.0) 
        ball_x = ball.landing_x; ball_y = ball.landing_y
        dist_to_1b = math.sqrt((ball_x - base_1b_pos[0])**2 + (ball_y - base_1b_pos[1])**2)
        
        arm = get_effective_stat(fielder, 'arm')
        # --- 修正: 送球速度アップ (内野安打抑制) ---
        throw_speed = 38 + (arm / 100.0) * 16
        
        # --- 修正: 握り替え時間短縮 ---
        transfer_time = 0.65 - (get_effective_stat(fielder, 'error') / 250.0)
        throw_time = transfer_time + (dist_to_1b / throw_speed)
        
        throw_time *= 0.95
        runner_time = 4.1 
        time_margin = runner_time - throw_time
        rec = fielder.get_record_by_level(team_level)
        
        # 内野安打阻止のARM貢献計算 (平均的なタイムとの差分で評価)
        # リーグ平均データを使用 (なければ50相当)
        avg_arm = self.league_stats.get('avg_arm', 50.0)
        avg_speed = 38 + (avg_arm / 100.0) * 16
        # エラー耐性の平均も考慮
        avg_error = self.league_stats.get('avg_error', 50.0)
        avg_transfer = 0.65 - (avg_error / 250.0)
        
        avg_throw_time = (avg_transfer + (dist_to_1b / avg_speed)) * 0.95
        
        # マージンが際どい場合のみ評価対象
        is_close_play = abs(runner_time - avg_throw_time) < 0.5
        
        if is_close_play:
             # タイム短縮秒数 * 価値 (0.1秒あたり約0.1点と仮定)
             time_saved = avg_throw_time - throw_time
             arm_val = time_saved * 1.0 * UZR_SCALE["ARM"]
             rec.def_drs_raw += arm_val
             rec.uzr_arm += arm_val

        # --- 修正: 内野安打の機会を大幅増加 (マージン拡大でBABIP向上) ---
        if throw_time < (runner_time + 0.50):  # 0.35 → 0.50秒に拡大（内野安打大幅増加）
            return PlayResult.GROUNDOUT
        else:
            return PlayResult.SINGLE 

    def _judge_hit_type_potential(self, ball, ball_pos, stadium, fielder=None, batter=None):
        """
        超現実的な長打判定：外野手の捕球〜送球タイミング vs 打者走者の走塁タイミング
        MLB/NPBの実データに基づく: シングル約70%, ダブル約20%, トリプル約2%
        """
        abs_spray = abs(ball.spray_angle)
        dist = ball.distance
        
        # ソフトコンタクトは確実にシングル
        if ball.contact_quality == "soft":
            return PlayResult.SINGLE
        
        # 距離が短い打球（80m未満）はほぼシングル
        if dist < 80:
            return PlayResult.SINGLE
        
        # ===== 外野手の処理時間計算 =====
        if fielder:
            arm_stat = get_effective_stat(fielder, 'arm')
            fielder_speed = get_effective_stat(fielder, 'speed')
        else:
            arm_stat = 50.0
            fielder_speed = 50.0
        
        # 打球到達時間（フライなら滞空時間、ゴロなら転がる時間）
        ball_travel_time = ball.hang_time
        
        # 外野手が打球位置に到達する追加時間
        fielder_run_time = max(0, (dist - 85) * 0.03) - (fielder_speed - 50) * 0.015
        
        # 捕球してから送球までの時間（クロウホップ含む）
        transfer_time = 1.2 - (arm_stat - 50) * 0.006  # 0.9〜1.5秒
        
        # 送球速度: 外野手は約35m/s(126km/h)〜42m/s(151km/h)
        throw_velocity = 35.0 + (arm_stat - 50) * 0.14
        
        # 送球距離（打球落下地点から各塁）
        dist_to_2b = math.sqrt((ball_pos[0])**2 + (ball_pos[1] - 38.6)**2)
        dist_to_3b = math.sqrt((ball_pos[0] + 19.3)**2 + (ball_pos[1] - 19.3)**2)
        
        # 送球時間
        throw_time_to_2b = dist_to_2b / throw_velocity
        throw_time_to_3b = dist_to_3b / throw_velocity
        
        # 外野手の合計処理時間（打球がフィールドに落ちてから塁に送球到達まで）
        defense_time_to_2b = ball_travel_time + fielder_run_time + transfer_time + throw_time_to_2b
        defense_time_to_3b = ball_travel_time + fielder_run_time + transfer_time + throw_time_to_3b
        
        # ===== 打者走者の走塁時間計算 =====
        if batter:
            speed_stat = get_effective_stat(batter, 'speed')
            baserunning_stat = get_effective_stat(batter, 'steal')
        else:
            speed_stat = 50.0
            baserunning_stat = 50.0
        
        # MLB平均: 1B到達4.3秒, 2B到達8.0秒, 3B到達12.0秒
        # ベーススピード: 50で平均的な4.3秒/塁間
        base_time = 4.3 - (speed_stat - 50) * 0.016  # 50で4.3秒, 100で3.5秒
        
        # 走塁センスボーナス（コーナリング、判断力）
        baserunning_bonus = (baserunning_stat - 50) * 0.02
        
        # ホームから各塁への到達時間
        time_to_1b = base_time + 0.3  # スタート遅延
        time_to_2b = time_to_1b + base_time - baserunning_bonus
        time_to_3b = time_to_2b + base_time - baserunning_bonus
        
        # ===== 現実的な長打判定 =====
        margin_2b = time_to_2b - defense_time_to_2b
        margin_3b = time_to_3b - defense_time_to_3b
        
        random_factor = random.gauss(0, 0.4)
        
        # ----- スリーベース判定（条件緩和） -----
        # 条件: フェンス際(95m以上) + ライン際/ギャップ + 足が平均以上
        is_fence_area = dist > 95  # 100→95に緩和
        is_gap_or_line = abs_spray > 20
        is_fast_runner = speed_stat > 20  # 55→50に緩和
        
        if is_fence_area and is_gap_or_line and is_fast_runner:
            if margin_3b + random_factor > 1.2:  # 1.5→1.2に緩和
                return PlayResult.TRIPLE
            elif margin_3b + random_factor > 0.3:  # 0.5→0.3に緩和
                triple_prob = 0.20 + (margin_3b * 0.12)  # 確率上昇
                if random.random() < min(0.40, triple_prob):  # 上限0.3→0.4
                    return PlayResult.TRIPLE
                return PlayResult.DOUBLE
        
        # ----- ツーベース判定 -----
        # 条件: 飛距離85m以上 + ギャップ/ライン際 または フェンス際
        is_extra_base_territory = dist > 85
        
        if is_extra_base_territory:
            if is_fence_area:
                # フェンス際はツーベース確率高い
                if margin_2b + random_factor > 0.5:
                    return PlayResult.DOUBLE
                elif margin_2b + random_factor > -0.5:
                    double_prob = 0.4 + (margin_2b * 0.2)
                    if random.random() < max(0.2, min(0.7, double_prob)):
                        return PlayResult.DOUBLE
            elif is_gap_or_line and ball.contact_quality in ["hard", "medium"]:
                # ギャップ/ライン際の強い・中程度の打球（案2: mediumも対象に）
                if margin_2b + random_factor > 0.3:
                    return PlayResult.DOUBLE
                elif margin_2b + random_factor > -0.5:
                    double_prob = 0.25 + (margin_2b * 0.15)
                    if random.random() < max(0.1, min(0.5, double_prob)):
                        return PlayResult.DOUBLE
        
        # ----- ライン際の打球は長打になりやすい（案3） -----
        # スプレー角度が大きい(ライン際)打球で飛距離70m以上は長打確率UP
        if abs_spray > 30 and dist > 70:
            if random.random() < 0.25:
                return PlayResult.DOUBLE
        
        # ----- 三塁線・一塁線を抜けたハードゴロも二塁打 -----
        # ライン際(abs_spray > 35)の速いゴロ(dist > 50m)は長打になりやすい
        if ball.hit_type == BattedBallType.GROUNDBALL and abs_spray > 35 and dist > 50:
            if ball.contact_quality == "hard":
                if random.random() < 0.50:  # ハードゴロは50%で二塁打
                    return PlayResult.DOUBLE
            elif ball.contact_quality == "medium":
                if random.random() < 0.25:  # ミディアムゴロは25%で二塁打
                    return PlayResult.DOUBLE
        
        return PlayResult.SINGLE

    def _update_defensive_metrics(self, fielder, team_level, avg_catch_prob, is_caught, play_value):
        """UZR (RngR) の計算: 平均的な選手との差分を積み上げる"""
        if self.is_postseason: return
        rec = fielder.get_record_by_level(team_level)
        rec.def_opportunities += 1
        
        # 難易度（平均的な選手が捕れない確率）を加算
        rec.def_difficulty_sum += (1.0 - avg_catch_prob)
        
        rng_r = 0.0
        
        # UZRの基本原理: (実際に捕ったか[1or0] - 平均的な選手が捕る確率) * プレーの価値
        # これにより、平均的な選手なら期待値通りの結果になり、プラスマイナス0に収束する
        
        if is_caught:
            # 捕った場合: (1 - 平均確率) * 価値 = プラス評価
            # 例: 確率30%の球を捕ったら 0.7 * 価値 のプラス
            rec.def_plays_made += 1
            rng_r = (1.0 - avg_catch_prob) * play_value
        else:
            # 落とした(ヒットになった)場合: (0 - 平均確率) * 価値 = マイナス評価
            # 例: 確率90%の球を落としたら -0.9 * 価値 のマイナス
            rng_r = (0.0 - avg_catch_prob) * play_value
            
        rng_r *= UZR_SCALE["RngR"]
        rec.def_drs_raw += rng_r; rec.uzr_rngr += rng_r

    def judge_arm_opportunity(self, ball: BattedBallData, fielder: Player, runner: Player, base_from: int, team_level):
        """外野手の補殺・進塁抑止評価"""
        arm = get_effective_stat(fielder, 'arm')
        runner_speed = get_effective_stat(runner, 'speed')
        
        # 刺せる確率 (平均50vs50なら30%)
        kill_prob = 0.3 + (arm - 50) * 0.01 - (runner_speed - 50) * 0.01
        kill_prob = max(0.05, min(0.8, kill_prob))
        
        # 平均的な野手の刺せる確率 (リーグ平均能力を使用)
        avg_arm = self.league_stats.get('avg_arm', 50.0)
        avg_kill_prob = 0.3 + (avg_arm - 50) * 0.01 - (runner_speed - 50) * 0.01
        avg_kill_prob = max(0.05, min(0.8, avg_kill_prob))
        
        # もしリーグの実績データがあればそちらを優先 (kill_rate)
        if 'kill_rate' in self.league_stats:
             avg_kill_prob = self.league_stats['kill_rate']

        rec = fielder.get_record_by_level(team_level)
        
        # ランナーが突っ込むかどうか (肩が強いと突っ込みにくい)
        attempt_threshold = 0.3 - (arm - 50) * 0.005
        is_attempt = random.random() < attempt_threshold
        
        # 価値定義
        run_val_out = 0.8 # 補殺の価値 (アウト増 + 進塁阻止)
        run_val_safe = -0.4 # 進塁許容の損失
        
        if is_attempt:
            # ランナーが走った
            if random.random() < kill_prob:
                # 補殺成功 (Kill)
                # 平均的な選手よりどれだけ確率が高かったか？というよりは、
                # 結果責任として (1 - 平均成功率) * 価値 を与えるのがUZR的
                val = (1.0 - avg_kill_prob) * run_val_out
                val *= UZR_SCALE["ARM"]
                if not self.is_postseason:
                    rec.uzr_arm += val; rec.def_drs_raw += val
                return True # Out
            else:
                # 補殺失敗 (Safe)
                val = (0.0 - avg_kill_prob) * abs(run_val_safe) # マイナス
                val *= UZR_SCALE["ARM"]
                if not self.is_postseason:
                    rec.uzr_arm += val; rec.def_drs_raw += val
                return False # Safe
        else:
            # ランナー自重 (Hold)
            # 肩が強いことによる抑止効果（本来走られる確率 - 実際に走られた確率）
            # 簡易的に、平均より肩が強ければプラスを与える
            avg_attempt_threshold = 0.3
            deterrence_val = (avg_attempt_threshold - attempt_threshold) * 0.5 # 係数は調整
            if deterrence_val > 0 and not self.is_postseason:
                 rec.uzr_arm += deterrence_val * UZR_SCALE["ARM"]
                 rec.def_drs_raw += deterrence_val * UZR_SCALE["ARM"]
            return False

def create_nested_defaultdict():
    return defaultdict(int)

class LiveGameEngine:
    def __init__(self, home: Team, away: Team, team_level: TeamLevel = TeamLevel.FIRST, league_stats: Dict[str, float] = None, is_all_star: bool = False, is_postseason: bool = False, debug_mode: bool = False, max_innings: int = 12, game_state_manager=None):
        self.home_team = home; self.away_team = away
        self.team_level = team_level; self.state = GameState()
        self.pitch_gen = PitchGenerator(); self.bat_gen = BattedBallGenerator()
        self.def_eng = AdvancedDefenseEngine(is_postseason=is_postseason); self.ai = AIManager(game_state_manager)
        self.game_stats = defaultdict(create_nested_defaultdict)
        self.stadium = getattr(self.home_team, 'stadium', None)
        self.stadium = getattr(self.home_team, 'stadium', None)
        if not self.stadium: self.stadium = Stadium(name=f"{home.name} Stadium")
        self.league_stats = league_stats or {}
        
        # Game state manager for settings access
        self.game_state_manager = game_state_manager
        
        # AI Decision Maker for non-player teams
        if game_state_manager:
            self.ai_decision = AIDecisionMaker(game_state_manager)
        else:
            self.ai_decision = None
        
        # Debug mode (only output debug prints when True)
        self.debug_mode = debug_mode
        
        # Check All-Star
        self.is_all_star = is_all_star or (home.name in ["ALL-NORTH", "ALL-SOUTH"] or away.name in ["ALL-NORTH", "ALL-SOUTH"])
        self.is_postseason = is_postseason
        self.max_innings = max_innings
        
        # Tracking for winning pitcher eligibility (NPB 9.17)
        # Records the pitcher who was on the mound when the go-ahead run was scored
        self.home_goahead_pitcher = None  # Pitcher on mound when home took lead
        self.away_goahead_pitcher = None  # Pitcher on mound when away took lead

        
        # 新しい投手管理システム - チームレベルを渡す
        self.home_pitching_director = PitchingDirector(home, self.team_level)
        self.away_pitching_director = PitchingDirector(away, self.team_level)
        
        self._init_starters()
        self._ensure_valid_lineup(self.home_team); self._ensure_valid_lineup(self.away_team)

        # Mark all initial players as has_played_today
        self._mark_starters_played(self.home_team)
        self._mark_starters_played(self.away_team)

    def _mark_starters_played(self, team: Team):
        # Lineup
        lineup = None
        if self.team_level == TeamLevel.SECOND: lineup = team.farm_lineup
        elif self.team_level == TeamLevel.THIRD: lineup = team.third_lineup
        else: lineup = team.current_lineup
        
        # DEBUG: Log when first team players are marked
        if self.team_level == TeamLevel.FIRST and lineup:
            marked_players = []
            for idx in lineup:
                if 0 <= idx < len(team.players):
                    marked_players.append(team.players[idx].name)
        
        if lineup:
             for idx in lineup:
                 if 0 <= idx < len(team.players):
                     p = team.players[idx]
                     p.has_played_today = True
        
        # Starter
        sp = None
        if self.state.is_top: # Wait, logic inside init_starters already decided starter idx
             if team == self.home_team: sp = self.home_start_p
        else:
             if team == self.away_team: sp = self.away_start_p
        
        # Actually just use self.home_start_p and self.away_start_p set in _init_starters using correct logic
        if team == self.home_team and hasattr(self, 'home_start_p'): 
            self.home_start_p.has_played_today = True
        if team == self.away_team and hasattr(self, 'away_start_p'): 
            self.away_start_p.has_played_today = True

    def _ensure_valid_lineup(self, team: Team):
        if self.team_level == TeamLevel.SECOND: get_lineup = lambda: team.farm_lineup; set_lineup = lambda l: setattr(team, 'farm_lineup', l); get_roster = team.get_farm_roster_players
        elif self.team_level == TeamLevel.THIRD: get_lineup = lambda: team.third_lineup; set_lineup = lambda l: setattr(team, 'third_lineup', l); get_roster = team.get_third_roster_players
        else: get_lineup = lambda: team.current_lineup; set_lineup = lambda l: setattr(team, 'current_lineup', l); get_roster = team.get_active_roster_players

        def is_valid_player(p):
            if p.is_injured: return False
            if self.team_level == TeamLevel.FIRST and hasattr(p, 'days_until_promotion') and p.days_until_promotion > 0: return False
            # 登録軍チェック: 選手の登録軍と試合の軍レベルが一致しない場合は無効
            if p.team_level != self.team_level: return False
            # 既に今日出場した選手は出場不可（複数軍出場防止）
            if getattr(p, 'has_played_today', False): return False
            return True

        current_lineup = get_lineup()
        has_invalid = False
        if current_lineup and len(current_lineup) >= 9:
            for idx in current_lineup:
                if 0 <= idx < len(team.players):
                    p = team.players[idx]
                    if not is_valid_player(p): has_invalid = True; break
                else: has_invalid = True; break
        
        if not current_lineup or len(current_lineup) < 9 or has_invalid:
            candidates = get_roster()
            valid_candidates = [p for p in candidates if is_valid_player(p)]
            # フォールバック: レベル適切なロスターから選手を緩和条件で探す
            if len(valid_candidates) < 9:
                # has_played_todayチェックを除外して再試行
                relaxed_candidates = [p for p in candidates 
                                      if p.position != Position.PITCHER 
                                      and not p.is_injured 
                                      and p.team_level == self.team_level]
                valid_candidates = relaxed_candidates
            # それでも足りない場合は現在の候補で続行（一軍選手を使わない）
            new_lineup = generate_best_lineup(team, valid_candidates)
            
            set_lineup(new_lineup); current_lineup = new_lineup

        has_valid_catcher = False
        for idx in current_lineup:
            if 0 <= idx < len(team.players):
                p = team.players[idx]
                if (p.position == Position.CATCHER or p.stats.get_defense_range(Position.CATCHER) >= 20) and is_valid_player(p): has_valid_catcher = True; break
        
        if not has_valid_catcher:
            candidates = get_roster()
            valid_candidates = [p for p in candidates if is_valid_player(p)]
            new_lineup = generate_best_lineup(team, valid_candidates)
            set_lineup(new_lineup)

    def run_pitcher_change_check(self):
        """投手交代の判定と実行 (イニング間/打者交代時)"""
        # Home (Defending) - Home pitches when is_top=True (top of inning, away batting)
        if hasattr(self, 'home_pitching_director') and self.state.is_top:
             # ホームが守備 (表) -> Home is Pitching
            # Use level-checked getter instead of direct index access
            current_pitcher, _ = self.get_current_pitcher()
            ctx = create_pitching_context(self.state, current_pitcher, 
                                          self.game_stats[current_pitcher]['innings_pitched'], True)
            
            # Next Batter (Away)
            next_batter, _ = self.get_current_batter()
            ctx.next_batter_hand = getattr(next_batter, 'bats', '右')
                    
            new_pitcher = self.home_pitching_director.check_pitcher_change(
                ctx, current_pitcher, 
                self.state.home_pitchers_used, next_batter, is_all_star=self.is_all_star
            )
            if new_pitcher: self._change_pitcher(self.home_team, new_pitcher)

        # Away (Defending) - Away pitches when is_top=False (bottom of inning, home batting)
        elif hasattr(self, 'away_pitching_director') and not self.state.is_top:
            # アウェイが守備 (裏) -> Away is Pitching
            # Use level-checked getter instead of direct index access
            current_pitcher, _ = self.get_current_pitcher()
            ctx = create_pitching_context(self.state, current_pitcher,
                                          self.game_stats[current_pitcher]['innings_pitched'], False)
            
            # Next Batter (Home)
            next_batter, _ = self.get_current_batter()
            ctx.next_batter_hand = getattr(next_batter, 'bats', '右')

            new_pitcher = self.away_pitching_director.check_pitcher_change(
                ctx, current_pitcher, 
                self.state.away_pitchers_used, next_batter, is_all_star=self.is_all_star
            )
            if new_pitcher: self._change_pitcher(self.away_team, new_pitcher)

    def _change_pitcher(self, team: Team, new_pitcher: Player):
        """投手を交代する"""
        if new_pitcher not in team.players: return # Safety
        new_pid = team.players.index(new_pitcher)
        
        is_home = (team == self.home_team)
        
        if is_home:
            old_pid = self.state.home_pitcher_idx
            self.state.home_pitcher_idx = new_pid
            if new_pitcher not in self.state.home_pitchers_used:
                self.state.home_pitchers_used.append(new_pitcher)
            self.state.home_pitcher_stamina = new_pitcher.current_stamina
            self.state.home_pitch_count = 0 
            self.state.home_current_pitcher_runs = 0
            # 登板時点差を記録（ホールド判定用）: 自チームリード正
            diff = self.state.home_score - self.state.away_score
            self.game_stats[new_pitcher]['entry_score_diff'] = diff
            new_pitcher.has_played_today = True
        else:
            old_pid = self.state.away_pitcher_idx
            self.state.away_pitcher_idx = new_pid
            if new_pitcher not in self.state.away_pitchers_used:
                self.state.away_pitchers_used.append(new_pitcher)
            self.state.away_pitcher_stamina = new_pitcher.current_stamina
            self.state.away_pitch_count = 0
            self.state.away_current_pitcher_runs = 0
            # 登板時点差: 自チームリード正
            diff = self.state.away_score - self.state.home_score
            self.game_stats[new_pitcher]['entry_score_diff'] = diff
            new_pitcher.has_played_today = True

    def _init_starters(self):
        # Helper to get fallback pitcher from correct roster
        def get_fallback_pitcher(team, level):
            if level == TeamLevel.SECOND:
                roster_indices = team.farm_roster
            elif level == TeamLevel.THIRD:
                roster_indices = team.third_roster
            else:
                roster_indices = team.active_roster
            
            # Find first pitcher in roster WITH CORRECT LEVEL
            for idx in roster_indices:
                if 0 <= idx < len(team.players):
                    p = team.players[idx]
                    if p.position == Position.PITCHER and not p.is_injured and p.team_level == level:
                        return p
            
            # Second pass: any pitcher with correct level from roster
            for idx in roster_indices:
                if 0 <= idx < len(team.players):
                    p = team.players[idx]
                    if p.position == Position.PITCHER and p.team_level == level:
                        return p
            
            # Last resort: first player from roster with correct level
            for idx in roster_indices:
                if 0 <= idx < len(team.players):
                    p = team.players[idx]
                    if p.team_level == level:
                        return p
            
            # Absolute fallback - should not happen in normal operation
            if roster_indices and len(roster_indices) > 0:
                idx = roster_indices[0]
                if 0 <= idx < len(team.players):
                    return team.players[idx]
            return team.players[0]
        
        hp = self.home_team.get_today_starter(self.team_level) or get_fallback_pitcher(self.home_team, self.team_level)
        ap = self.away_team.get_today_starter(self.team_level) or get_fallback_pitcher(self.away_team, self.team_level)
        
        # Store initial starters for later reference (aptitude checks)
        self.home_start_p = hp
        self.away_start_p = ap
        
        # Fallback: If no starter assigned (or reliever assigned), try to force a rotation pitcher
        if not hp or hp.position != Position.PITCHER:
            rot = self.home_team.rotation
            if self.team_level == TeamLevel.SECOND: rot = self.home_team.farm_rotation
            elif self.team_level == TeamLevel.THIRD: rot = self.home_team.third_rotation
            
            if rot:
                hp_idx = rot[self.home_team.rotation_index % len(rot)]
                if 0 <= hp_idx < len(self.home_team.players):
                    hp = self.home_team.players[hp_idx]
                    self.home_start_p = hp

        if not ap or ap.position != Position.PITCHER:
            rot = self.away_team.rotation
            if self.team_level == TeamLevel.SECOND: rot = self.away_team.farm_rotation
            elif self.team_level == TeamLevel.THIRD: rot = self.away_team.third_rotation

            if rot:
                ap_idx = rot[self.away_team.rotation_index % len(rot)]
                if 0 <= ap_idx < len(self.away_team.players):
                    ap = self.away_team.players[ap_idx]
                    self.away_start_p = ap


        try: self.state.home_pitcher_idx = self.home_team.players.index(hp)
        except: 
            # Fallback to level-appropriate roster
            fallback = get_fallback_pitcher(self.home_team, self.team_level)
            self.state.home_pitcher_idx = self.home_team.players.index(fallback)
            hp = fallback
        try: self.state.away_pitcher_idx = self.away_team.players.index(ap)
        except:
            fallback = get_fallback_pitcher(self.away_team, self.team_level)
            self.state.away_pitcher_idx = self.away_team.players.index(fallback)
            ap = fallback
        
        # Level validation: If starter's level doesn't match game level, find replacement
        if self.team_level != TeamLevel.FIRST:
            if hp.team_level != self.team_level:
                replacement = get_fallback_pitcher(self.home_team, self.team_level)
                if replacement and replacement.team_level == self.team_level:
                    hp = replacement
                    self.home_start_p = hp
                    self.state.home_pitcher_idx = self.home_team.players.index(hp)
            if ap.team_level != self.team_level:
                replacement = get_fallback_pitcher(self.away_team, self.team_level)
                if replacement and replacement.team_level == self.team_level:
                    ap = replacement
                    self.away_start_p = ap
                    self.state.away_pitcher_idx = self.away_team.players.index(ap)
        
        self.state.home_pitchers_used.append(hp); self.state.away_pitchers_used.append(ap)
        self.game_stats[hp]['games_pitched'] = 1; self.game_stats[ap]['games_pitched'] = 1
        self.game_stats[hp]['games_started'] = 1; self.game_stats[ap]['games_started'] = 1
        
        # 先発投手のスタミナを先発用最大値に初期化（70〜170球）
        hp.current_stamina = hp.calc_max_pitches(is_starting=True)
        ap.current_stamina = ap.calc_max_pitches(is_starting=True)

    def get_current_batter(self) -> Tuple[Player, int]:
        team = self.away_team if self.state.is_top else self.home_team
        order_idx = self.state.away_batter_order if self.state.is_top else self.state.home_batter_order
        if self.team_level == TeamLevel.SECOND: lineup = team.farm_lineup
        elif self.team_level == TeamLevel.THIRD: lineup = team.third_lineup
        else: lineup = team.current_lineup
        if not lineup:
            # Fallback to level-appropriate roster
            if self.team_level == TeamLevel.SECOND and team.farm_roster:
                return team.players[team.farm_roster[0]], 0
            elif self.team_level == TeamLevel.THIRD and team.third_roster:
                return team.players[team.third_roster[0]], 0
            return team.players[0], 0  # Absolute fallback
        
        player_idx = lineup[order_idx % len(lineup)]
        batter = team.players[player_idx]
        
        # Runtime level check: If batter's level doesn't match game level, find replacement
        if self.team_level != TeamLevel.FIRST and batter.team_level != self.team_level:
            # Get appropriate roster
            roster_indices = team.farm_roster if self.team_level == TeamLevel.SECOND else team.third_roster
            # Find a valid batter from roster
            for idx in roster_indices:
                if 0 <= idx < len(team.players):
                    p = team.players[idx]
                    if (p.team_level == self.team_level 
                        and p.position != Position.PITCHER 
                        and not p.is_injured):
                        return p, order_idx
            # Last resort: return first player from roster
            if roster_indices:
                return team.players[roster_indices[0]], order_idx
        
        return batter, order_idx

    def get_current_pitcher(self) -> Tuple[Player, int]:
        team = self.home_team if self.state.is_top else self.away_team
        idx = self.state.home_pitcher_idx if self.state.is_top else self.state.away_pitcher_idx
        pitcher = team.players[idx]
        
        # Runtime level check: If pitcher's level doesn't match game level, find replacement
        if self.team_level != TeamLevel.FIRST and pitcher.team_level != self.team_level:
            # Get appropriate roster
            roster_indices = team.farm_roster if self.team_level == TeamLevel.SECOND else team.third_roster
            # Find a valid pitcher from roster
            for roster_idx in roster_indices:
                if 0 <= roster_idx < len(team.players):
                    p = team.players[roster_idx]
                    if (p.team_level == self.team_level 
                        and p.position == Position.PITCHER 
                        and not p.is_injured):
                        # Update the pitcher index in state
                        if self.state.is_top:
                            self.state.home_pitcher_idx = roster_idx
                        else:
                            self.state.away_pitcher_idx = roster_idx
                        return p, roster_idx
        
        return pitcher, idx

    def change_pitcher(self, new_pitcher: Player):
        team = self.home_team if self.state.is_top else self.away_team
        
        # 点差記録 (ホールド判定用)
        # 登板時点でのリード状況: (自チーム得点 - 相手チーム得点)
        score_diff = self.state.away_score - self.state.home_score if self.state.is_top else self.state.home_score - self.state.away_score
        self.game_stats[new_pitcher]['entry_score_diff'] = score_diff
        
        new_pitcher.has_played_today = True

        try:
            new_idx = team.players.index(new_pitcher)
            if self.state.is_top:
                self.state.home_pitcher_idx = new_idx
                if new_pitcher not in self.state.home_pitchers_used:
                    self.state.home_pitchers_used.append(new_pitcher)
                self.state.home_pitcher_stamina = new_pitcher.stats.stamina * 2.0 * (new_pitcher.current_stamina / 100.0)
                self.state.home_pitch_count = 0
                self.state.home_current_pitcher_runs = 0
            else:
                self.state.away_pitcher_idx = new_idx
                if new_pitcher not in self.state.away_pitchers_used:
                    self.state.away_pitchers_used.append(new_pitcher)
                self.state.away_pitcher_stamina = new_pitcher.stats.stamina * 2.0 * (new_pitcher.current_stamina / 100.0)
                self.state.away_pitch_count = 0
                self.state.away_current_pitcher_runs = 0
            self.game_stats[new_pitcher]['games_pitched'] = 1
        except ValueError: pass


    def change_batter(self, new_batter: Player):
        """代打処理"""
        team = self.away_team if self.state.is_top else self.home_team
        order_idx = self.state.away_batter_order if self.state.is_top else self.state.home_batter_order
        lineup = team.current_lineup
        if self.team_level == TeamLevel.SECOND: lineup = team.farm_lineup
        elif self.team_level == TeamLevel.THIRD: lineup = team.third_lineup
        
        # 現在の打者ID
        current_pid = lineup[order_idx % len(lineup)]
        current_batter = team.players[current_pid]
        
        # 新しい打者のIDを見つける
        try:
            new_pid = team.players.index(new_batter)
            # ラインナップ書き換え
            lineup[order_idx % len(lineup)] = new_pid
            
            # 出場記録
            # finalize_game_statsで一律 +1 されるため、ここではキー作成のみ行う
            self.game_stats[new_batter]['participation'] = 1
            new_batter.has_played_today = True
            
            if new_batter not in [self.home_team.get_today_starter(), self.away_team.get_today_starter()]:
                 # スタメンでなければ途中出場
                 pass 
                 
            # 守備位置の変更が必要だが、代打時は一時的にDH扱いまたは前の守備位置を引き継ぐ?
            # 守備交代ダイアログを出せないので、前のポジションをそのまま引き継ぐか、
            # 後の守備イニングで交代が必要になる。
            # AIシミュレーションのみなら、ポジション不一致のまま進んでもエラーにはならないが、守備力が落ちる。
            # ここでは「代打」としてセットし、ポジションは仮に元の選手のものを引き継ぐ
            # (ただしnew_batter.positionは変えない)
            
        except ValueError: pass

    def get_current_catcher(self) -> Optional[Player]:
        team = self.home_team if self.state.is_top else self.away_team
        if self.team_level == TeamLevel.SECOND: lineup = team.farm_lineup
        elif self.team_level == TeamLevel.THIRD: lineup = team.third_lineup
        else: lineup = team.current_lineup
        if not lineup: return None
        
        # Try to find catcher from lineup with correct level
        for p_idx in lineup:
            if 0 <= p_idx < len(team.players):
                p = team.players[p_idx]
                if p.position == Position.CATCHER:
                    # Level check
                    if self.team_level != TeamLevel.FIRST and p.team_level != self.team_level:
                        continue  # Skip wrong-level catcher
                    return p
        
        # Fallback: Find catcher from roster
        if self.team_level != TeamLevel.FIRST:
            roster_indices = team.farm_roster if self.team_level == TeamLevel.SECOND else team.third_roster
            for idx in roster_indices:
                if 0 <= idx < len(team.players):
                    p = team.players[idx]
                    if p.team_level == self.team_level and p.position == Position.CATCHER and not p.is_injured:
                        return p
        
        return None

    def _check_injury_occurrence(self, player: Player, action_type: str):
        # Check if injuries are enabled in settings
        if self.game_state_manager and not getattr(self.game_state_manager, 'injuries_enabled', True):
            return False
        
        if hasattr(player, 'is_injured') and player.is_injured: return 
        durability = getattr(player.stats, 'durability', 50)
        fatigue_factor = 1.0
        if player.position == Position.PITCHER and player.stats.stamina < 30: fatigue_factor = 3.0
        
        # Reduced base rate from 0.00005 to 0.00001 (0.001%)
        base_rate = 0.00001  
        
        # Further reduce for farm games to minimize "off-day injury" complaints
        if self.team_level != TeamLevel.FIRST:
            base_rate *= 0.2  # 1/5th rate for farm
            
        rate = base_rate * (100 - durability) / 50.0 * fatigue_factor
        if random.random() < rate:
            days = random.randint(3, 30) 
            name = f"患部の{random.choice(['違和感', '捻挫', '肉離れ', '炎症'])}"
            if hasattr(player, 'inflict_injury'): player.inflict_injury(days, name)
            return True
        return False

    def simulate_pitch(self, manual_strategy=None, shifts=None):
        # === 超強力試合終了チェック ===
        # 8回以降、次の攻撃が始まる前に必ず試合終了判定を行う
        # 試合終了時は絶対に処理を終了する
        if self.is_game_over():
            return None  # 試合終了、これ以上の処理なし
        
        defense_team = self.home_team if self.state.is_top else self.away_team
        offense_team = self.away_team if self.state.is_top else self.home_team
        batter, _ = self.get_current_batter()
        pitcher, _ = self.get_current_pitcher()
        
        # DEBUG: Catch first team player usage in farm games
        if self.team_level != TeamLevel.FIRST:
            if batter.team_level == TeamLevel.FIRST and not hasattr(self, '_debug_first_batter_warned'):
                print(f"[PITCH DEBUG] {self.team_level}: FIRST team BATTER {batter.name} from {offense_team.name}")
                self._debug_first_batter_warned = True
            if pitcher.team_level == TeamLevel.FIRST and not hasattr(self, '_debug_first_pitcher_warned'):
                print(f"[PITCH DEBUG] {self.team_level}: FIRST team PITCHER {pitcher.name} from {defense_team.name}")
                self._debug_first_pitcher_warned = True


        # --- AI Shift Logic ---
        # If user didn't specify shifts (e.g. AI vs AI, or User is batting), let AI decide
        # Even if User is Pitching, if they didn't manually set shift (shifts=None), AI suggests?
        # Typically UI passes existing shift state if User is managing.
        # But if shifts is None, it means "Auto" or "No override".
        # We should check if the defense team is AI controlled.
        # For simplicity, if shifts is None, we run AI logic. 
        # (Assuming UI passes manual shifts if set)
        if shifts is None:
             shifts = self.ai.decide_defensive_shifts(self.state, offense_team, defense_team, batter, pitcher)

        if shifts:
            self.state.infield_shift = shifts.get('infield', "内野通常")
            self.state.outfield_shift = shifts.get('outfield', "外野通常")

        current_pitcher_ip = self.game_stats[pitcher]['innings_pitched']
        # 注意: game_statsのinnings_pitchedは累積だが、この試合の登板回数としては正しい。
        # ただし、リリーフが回またぎする場合、前の回 + 今回のアウト数になる。
        # 現在のイニングのアウト数だけ見たいわけではなく、この試合での総投球回で判断でOK。
        
        # 新しい投手管理システムを使用
        is_defending_home = self.state.is_top  # 表の攻撃中 = ホームが守備
        pitching_director = self.home_pitching_director if is_defending_home else self.away_pitching_director
        used_pitchers = self.state.home_pitchers_used if is_defending_home else self.state.away_pitchers_used
        
        ctx = create_pitching_context(self.state, pitcher, current_pitcher_ip, is_defending_home)
        ctx.next_batter_hand = batter.bats
        
        new_pitcher = pitching_director.check_pitcher_change(ctx, pitcher, used_pitchers, batter, is_all_star=self.is_all_star)
        if new_pitcher:
            self.change_pitcher(new_pitcher); pitcher = new_pitcher
        
        # --- 代打策判定 (Smart AI) ---
        offense_team = self.away_team if self.state.is_top else self.home_team
        new_batter = self.ai.check_pinch_hitter(self.state, offense_team, defense_team, batter, pitcher)
        if new_batter:
            self.change_batter(new_batter)
            batter = new_batter
            # コンソール出力などで確認できるようにしてもよい
            # print(f"PH: {new_batter.name} for {offense_team.name}")
            
        catcher = self.get_current_catcher()
        offense_team = self.away_team if self.state.is_top else self.home_team
        strategy = manual_strategy or self.ai.decide_strategy(self.state, offense_team, defense_team, batter)
        pitch_strategy = self.ai.decide_pitch_strategy(self.state, pitcher, batter)
        
        # 盗塁情報を初期化
        steal_info = None
        
        if strategy == "STEAL":
            # 盗塁対象のランナーを特定
            if self.state.runner_2b and not self.state.runner_3b:
                runner = self.state.runner_2b
            elif self.state.runner_1b and not self.state.runner_2b:
                runner = self.state.runner_1b
            else:
                runner = None
            
            runner_name = runner.name if runner else "ランナー"
            result = self._attempt_steal(catcher)
            if result is not None:
                steal_info = {
                    'success': result['success'], 
                    'runner_name': runner_name,
                    'steal_type': result['steal_type']
                }
                return PitchResult.BALL, None, None, steal_info
        
        # ヒットエンドラン: ランナーがスタートを切り、打者は必ずスイング
        if strategy == "HIT_AND_RUN" and self.state.runner_1b:
            # ランナーは1塁進塁（成功時）を前提に走る
            strategy = "SWING"  # 打者はスイング
        
        # スクイズ: 3塁ランナーがいて0-1アウト時にバント
        if strategy == "SQUEEZE" and self.state.runner_3b and self.state.outs < 2:
            strategy = "BUNT"

        # Correct Aptitude Calculation
        aptitude_val = 4 # Default to Max
        
        # Identify Role
        # Check if Starter
        is_starter = False
        if self.state.is_top:
            if pitcher == self.home_start_p: is_starter = True
        else:
            if pitcher == self.away_start_p: is_starter = True
            
        if is_starter:
            aptitude_val = getattr(pitcher, 'starter_aptitude', 4)
        else:
            # Check for Closer Situation
            # Save Situation: 9th inning+, Lead <= 3 or Tying/Winning run on base/deck
            # Simplified: Inning >= 9 and score_diff <= 3 (if leading)
            # Or just check if they are the designated closer in the roster?
            # User wants behavior based on context.
            # But the 'closer' aptitude should apply when acting as closer.
            # Usually setups pitch 8th.
            # Let's use the designated role in Team if possible?
            # Team object has `closers` list.
            
            team_obj = self.home_team if self.state.is_top else self.away_team # Defensive team
            # Wait, defense team is home if top.
            
            is_closer_role = False
            if hasattr(team_obj, 'closers') and team_obj.closers:
                # check if pitcher index matches closer index
                # But pitcher object identity is safer
                if pitcher in [team_obj.players[i] for i in team_obj.closers if 0 <= i < len(team_obj.players)]:
                    is_closer_role = True
            
            if is_closer_role:
                 aptitude_val = getattr(pitcher, 'closer_aptitude', 4)
            else:
                 aptitude_val = getattr(pitcher, 'middle_aptitude', 4)

        # Pass aptitude_val to generators
        pitch = self.pitch_gen.generate_pitch(pitcher, batter, catcher, self.state, pitch_strategy, self.stadium, aptitude_val=aptitude_val)
        if self.state.is_top: 
            self.state.home_pitch_count += 1
            self.state.home_pitcher_stamina -= 0.7 # スタミナ消費 (1.0 -> 0.7)
        else: 
            self.state.away_pitch_count += 1
            self.state.away_pitcher_stamina -= 0.7 # スタミナ消費 (1.0 -> 0.7)
        self._check_injury_occurrence(pitcher, "PITCH")
        
        res, ball = self._resolve_contact(batter, pitcher, pitch, strategy, aptitude_val=aptitude_val)
        final_res = self.process_pitch_result(res, pitch, ball, strategy)
        
        # --- rBlk (ブロッキング指標) の判定 ---
        if final_res in [PitchResult.BALL, PitchResult.STRIKE_SWINGING]:
             self._check_blocking(pitcher, catcher, pitch)

        return final_res, pitch, ball, steal_info

    def _check_blocking(self, pitcher, catcher, pitch):
        """ワイルドピッチ/パスボール判定とrBlk計算"""
        if not self.state.is_runner_on(): return
        
        # 低めの変化球やワンバウンド性の球 (z < 0.2 または 縦変化が大きい)
        # --- 修正: 判定基準を少し緩める (機会を増やす) ---
        is_difficult = pitch.location.z < 0.25 or abs(pitch.vertical_break) > 20
        if not is_difficult: return

        # 平均的な逸逸率 (難球の場合) - リーグ平均があれば使用
        # --- 修正: 平均阻止率を少し上げて、成功時のプラスを増やす ---
        avg_pass_prob = self.league_stats.get('pass_rate', 0.12)
        
        # 捕手の能力 (errorが高いほど捕逸しにくいと仮定)
        block_skill = get_effective_stat(catcher, 'error') if catcher else 50
        pass_prob = avg_pass_prob * (1.0 - (block_skill - 50) * 0.02)
        pass_prob = max(0.01, pass_prob)
        
        # 逸らしたか？
        is_passed = random.random() < pass_prob
        
        # UZR (rBlk) 計算
        run_val_advance = 0.25 # 進塁の価値（適当）
        
        if is_passed:
            # 逸らした: マイナス評価 (0 - (1-avg)) = -(1-avg)
            val = (0.0 - (1.0 - avg_pass_prob)) * run_val_advance * UZR_SCALE["rBlk"]
            if catcher:
                self.game_stats[catcher]['uzr_rblk'] += val
                self.game_stats[catcher]['def_drs_raw'] += val
            # 進塁処理
            self._advance_runners(1, None, is_walk=False) # ワイルドピッチ/パスボール進塁
        else:
            # 止めた: プラス評価 (1 - (1-avg)) = avg
            val = avg_pass_prob * run_val_advance * UZR_SCALE["rBlk"]
            if catcher:
                self.game_stats[catcher]['uzr_rblk'] += val
                self.game_stats[catcher]['def_drs_raw'] += val

    def _resolve_contact(self, batter, pitcher, pitch, strategy, aptitude_val: int = 4):
        if not pitch.location.is_strike:
            control = get_effective_stat(pitcher, 'control', aptitude_val=aptitude_val)
            if random.random() < (0.002 + max(0, (50-control)*0.0002)): return PitchResult.HIT_BY_PITCH, None

        if strategy == "BUNT":
            bunt_skill = get_effective_stat(batter, 'bunt_sac')
            difficulty = 20 if not pitch.location.is_strike else 0
            if random.uniform(0, 100) > (bunt_skill - difficulty):
                return PitchResult.FOUL if random.random() < 0.8 else PitchResult.STRIKE_SWINGING, None
            else:
                ball = self.bat_gen.generate(batter, pitcher, pitch, self.state, strategy, aptitude_val=aptitude_val)
                return PitchResult.IN_PLAY, ball

        eye = get_effective_stat(batter, 'eye')
        dist_from_center = math.sqrt(pitch.location.x**2 + (pitch.location.z - 0.75)**2)
        is_obvious_ball = dist_from_center > 0.45 
        
        if pitch.location.is_strike:
            swing_prob = 0.80 + (eye-50)*0.001
        else:
            if is_obvious_ball: swing_prob = 0.005 
            else: swing_prob = 0.35 - (eye-50)*0.005 # 0.30 -> 0.40 (ボール球スイング率UP)

        if self.state.strikes == 2: swing_prob += 0.18
        if strategy == "POWER": swing_prob += 0.1 
        if strategy == "MEET": swing_prob -= 0.1
        swing_prob = max(0.001, min(0.99, swing_prob))
        
        if random.random() >= swing_prob: return PitchResult.STRIKE_CALLED if pitch.location.is_strike else PitchResult.BALL, None
            
        contact = get_effective_stat(batter, 'contact', opponent=pitcher)
        stuff = pitcher.stats.get_pitch_stuff(pitch.pitch_type)
        base_contact = 0.60 # 0.63 -> 0.60 (コンタクト率DOWN: 三振増加)
        hit_prob = base_contact + ((contact - stuff) * 0.004)
        
        if pitch.location.is_strike: hit_prob += 0.08
        else: hit_prob -= 0.20 # ボール球コンタクト率DOWN
        if self.stadium: hit_prob /= max(0.5, self.stadium.pf_so)
        hit_prob = max(0.35, min(0.96, hit_prob)) 

        if self.state.strikes == 2:
            avoid_k = get_effective_stat(batter, 'avoid_k')
            hit_prob += 0.03 # 0.05 -> 0.03 (2ストライク時の粘りを少し抜く)
            hit_prob += (avoid_k - 50) * 0.003

        if random.random() > hit_prob: 
             self._check_injury_occurrence(batter, "SWING")
             return PitchResult.STRIKE_SWINGING, None
             
        if random.random() < 0.40: return PitchResult.FOUL, None # 0.32 -> 0.40 (ファウル率UP)
             
        ball = self.bat_gen.generate(batter, pitcher, pitch, self.state, strategy)
        self._check_injury_occurrence(batter, "RUN")
        return PitchResult.IN_PLAY, ball

    def _attempt_steal(self, catcher):
        """盗塁を試みる（二盗・三盗対応）"""
        # 三盗優先（2塁ランナーがいて3塁が空いている場合）
        if self.state.runner_2b and not self.state.runner_3b:
            runner = self.state.runner_2b
            steal_type = "3B"
        elif self.state.runner_1b and not self.state.runner_2b:
            runner = self.state.runner_1b
            steal_type = "2B"
        else:
            return None  # 盗塁不可
        
        runner_spd = get_effective_stat(runner, 'speed')
        raw_catcher_arm = get_effective_stat(catcher, 'arm') if catcher else 50
        # キャッチャー肩の影響を50%に圧縮（個人差縮小）
        catcher_arm = 50 + (raw_catcher_arm - 50) * 0.5
        
        # 盗塁成功率を下げる（盗塁死増加）
        # 三盗は二盗より成功率が低い（距離が近く守備に有利）
        if steal_type == "3B":
            success_prob = 0.55 + (runner_spd - 50)*0.008 - (catcher_arm - 50)*0.008  # 60→55%
        else:
            success_prob = 0.65 + (runner_spd - 50)*0.008 - (catcher_arm - 50)*0.008  # 70→65%
        
        self._check_injury_occurrence(runner, "RUN")
        
        is_success = random.random() < success_prob
        
        # --- rSB (盗塁阻止) UZR計算 (平均差分方式) ---
        avg_stop_prob = self.league_stats.get('cs_rate', 0.25)
        run_value_diff = 0.75
        
        if is_success:
            if steal_type == "3B":
                self.state.runner_3b = runner; self.state.runner_2b = None
            else:
                self.state.runner_2b = runner; self.state.runner_1b = None
            self.game_stats[runner]['stolen_bases'] += 1
            if catcher:
                val = (0.0 - avg_stop_prob) * run_value_diff * UZR_SCALE["rSB"]
                self.game_stats[catcher]['uzr_rsb'] += val
                self.game_stats[catcher]['def_drs_raw'] += val
            return {'success': True, 'steal_type': steal_type}
        else:
            if steal_type == "3B":
                self.state.runner_2b = None
            else:
                self.state.runner_1b = None
            self.state.outs += 1
            self.game_stats[runner]['caught_stealing'] += 1
            # ★修正: 盗塁死でもIPを記録
            pitcher, _ = self.get_current_pitcher()
            self.game_stats[pitcher]['innings_pitched'] += (1.0/3.0)

            if catcher:
                val = (1.0 - avg_stop_prob) * run_value_diff * UZR_SCALE["rSB"]
                self.game_stats[catcher]['uzr_rsb'] += val
                self.game_stats[catcher]['def_drs_raw'] += val
            if self.state.outs >= 3:
                self._change_inning()
            return {'success': False, 'steal_type': steal_type}


    def process_pitch_result(self, res, pitch, ball, strategy="NORMAL"):
        pitcher, _ = self.get_current_pitcher(); batter, _ = self.get_current_batter()
        is_in_zone = pitch.location.is_strike
        is_swing = res in [PitchResult.STRIKE_SWINGING, PitchResult.FOUL, PitchResult.IN_PLAY]
        is_contact = res in [PitchResult.FOUL, PitchResult.IN_PLAY]
        
        self.game_stats[pitcher]['pitches_thrown'] += 1; self.game_stats[batter]['pitches_seen'] += 1
        if is_in_zone:
            self.game_stats[pitcher]['zone_pitches'] += 1; self.game_stats[batter]['zone_pitches'] += 1
        else:
            self.game_stats[pitcher]['chase_pitches'] += 1; self.game_stats[batter]['chase_pitches'] += 1

        if is_swing:
            self.game_stats[pitcher]['swings'] += 1; self.game_stats[batter]['swings'] += 1
            if is_in_zone:
                self.game_stats[pitcher]['zone_swings'] += 1; self.game_stats[batter]['zone_swings'] += 1
                if is_contact: self.game_stats[pitcher]['zone_contact'] += 1; self.game_stats[batter]['zone_contact'] += 1
            else:
                self.game_stats[pitcher]['chase_swings'] += 1; self.game_stats[batter]['chase_swings'] += 1
                if is_contact: self.game_stats[pitcher]['chase_contact'] += 1; self.game_stats[batter]['chase_contact'] += 1
            if res == PitchResult.STRIKE_SWINGING:
                self.game_stats[pitcher]['whiffs'] += 1; self.game_stats[batter]['whiffs'] += 1

        if res in [PitchResult.STRIKE_CALLED, PitchResult.STRIKE_SWINGING, PitchResult.FOUL, PitchResult.IN_PLAY]:
            self.game_stats[pitcher]['strikes_thrown'] += 1
            if self.state.balls == 0 and self.state.strikes == 0:
                self.game_stats[pitcher]['first_pitch_strikes'] += 1; self.game_stats[batter]['first_pitch_strikes'] += 1
        else:
            self.game_stats[pitcher]['balls_thrown'] += 1

        final_result = res

        if res == PitchResult.BALL:
            self.state.balls += 1
            if self.state.balls >= 4: self._walk()
        elif res == PitchResult.HIT_BY_PITCH: self._walk(is_hbp=True)
        elif res in [PitchResult.STRIKE_CALLED, PitchResult.STRIKE_SWINGING]:
            self.state.strikes += 1
            if self.state.strikes >= 3: 
                self.game_stats[pitcher]['strikeouts_pitched'] += 1; self.game_stats[batter]['strikeouts'] += 1
                self.game_stats[batter]['plate_appearances'] += 1; self.game_stats[batter]['at_bats'] += 1
                self.game_stats[pitcher]['batters_faced'] += 1
                self._out() 
        elif res == PitchResult.FOUL:
            if self.state.strikes < 2: self.state.strikes += 1
        elif res == PitchResult.IN_PLAY:
            defense_team = self.home_team if self.state.is_top else self.away_team
            # ★修正: judgeに現在の投手とシフト情報を渡す
            shifts = {'infield': self.state.infield_shift, 'outfield': self.state.outfield_shift}
            play = self.def_eng.judge(ball, defense_team, self.team_level, self.stadium, current_pitcher=pitcher, league_stats=self.league_stats, batter=batter, shifts=shifts)
            
            if ball.contact_quality == "hard": self.game_stats[batter]['hard_hit_balls'] += 1; self.game_stats[pitcher]['hard_hit_balls'] += 1
            elif ball.contact_quality == "medium": self.game_stats[batter]['medium_hit_balls'] += 1; self.game_stats[pitcher]['medium_hit_balls'] += 1
            else: self.game_stats[batter]['soft_hit_balls'] += 1; self.game_stats[pitcher]['soft_hit_balls'] += 1
            
            batter_hand = getattr(batter, 'bats', "右")
            if batter_hand == "両": batter_hand = "左" if getattr(pitcher, 'throws', "右") == "右" else "右"
            angle = ball.spray_angle
            if abs(angle) <= 15: self.game_stats[batter]['center_balls'] += 1
            elif (batter_hand == "右" and angle < -15) or (batter_hand == "左" and angle > 15): self.game_stats[batter]['pull_balls'] += 1
            else: self.game_stats[batter]['oppo_balls'] += 1

            # GB%+FB%+LD%=100となるよう、POPUPはfly_ballsにカウント
            if ball.hit_type == BattedBallType.GROUNDBALL: self.game_stats[pitcher]['ground_balls'] += 1; self.game_stats[batter]['ground_balls'] += 1
            elif ball.hit_type in [BattedBallType.FLYBALL, BattedBallType.POPUP]: self.game_stats[pitcher]['fly_balls'] += 1; self.game_stats[batter]['fly_balls'] += 1
            elif ball.hit_type == BattedBallType.LINEDRIVE: self.game_stats[pitcher]['line_drives'] += 1; self.game_stats[batter]['line_drives'] += 1
            # POPUPは別途IFFB%計算用にもカウント
            if ball.hit_type == BattedBallType.POPUP: self.game_stats[pitcher]['popups'] += 1; self.game_stats[batter]['popups'] += 1
            
            self.game_stats[pitcher]['balls_in_play'] += 1; self.game_stats[batter]['balls_in_play'] += 1

            if play == PlayResult.FOUL:
                if self.state.strikes < 2: self.state.strikes += 1
            else:
                final_result = self._resolve_play(play, strategy, ball)
        
        return final_result

    def _record_pf(self, batter: Player, pitcher: Player):
        pf = self.stadium.pf_runs if self.stadium else 1.0
        self.game_stats[batter]['sum_pf_runs'] += pf
        self.game_stats[pitcher]['sum_pf_runs'] += pf

    def _walk(self, is_hbp=False):
        batter, _ = self.get_current_batter(); pitcher, _ = self.get_current_pitcher()
        self.game_stats[batter]['plate_appearances'] += 1; self.game_stats[pitcher]['batters_faced'] += 1
        if is_hbp: self.game_stats[batter]['hit_by_pitch'] += 1; self.game_stats[pitcher]['hit_batters'] += 1
        else: self.game_stats[batter]['walks'] += 1; self.game_stats[pitcher]['walks_allowed'] += 1
        self._record_pf(batter, pitcher)
        scored_players = self._advance_runners(1, batter, is_walk=True)
        for p in scored_players: self.game_stats[p]['runs'] += 1
        self._reset_count(); self._next_batter()

    def _out(self):
        pitcher, _ = self.get_current_pitcher()
        self.state.outs += 1
        self.game_stats[pitcher]['innings_pitched'] += (1.0 / 3.0)
        
        # DEBUG: Track IP recording

        
        defense_team = self.home_team if self.state.is_top else self.away_team
        for pid in defense_team.current_lineup:
            if 0 <= pid < len(defense_team.players) and defense_team.players[pid].position != Position.DH:
                self.game_stats[defense_team.players[pid]]['defensive_innings'] += (1.0 / 3.0)
        
        batter, _ = self.get_current_batter()
        self._record_pf(batter, pitcher)
        self._reset_count(); self._next_batter()
        
        # Only advance inning if game is not over
        if self.state.outs >= 3:
            game_over = self.is_game_over()

            if not game_over:
                self._change_inning()



    def _resolve_play(self, play, strategy, ball=None):
        batter, _ = self.get_current_batter(); pitcher, _ = self.get_current_pitcher()
        defense_team = self.home_team if self.state.is_top else self.away_team
        self.game_stats[batter]['plate_appearances'] += 1; self.game_stats[pitcher]['batters_faced'] += 1
        scored_players = []
        
        if play in [PlayResult.SINGLE, PlayResult.DOUBLE, PlayResult.TRIPLE, PlayResult.HOME_RUN]:
            # Team Stats Aggregation
            if self.state.is_top: self.state.away_hits += 1
            else: self.state.home_hits += 1

            self.game_stats[batter]['at_bats'] += 1; self.game_stats[batter]['hits'] += 1
            self.game_stats[pitcher]['hits_allowed'] += 1
            if play == PlayResult.DOUBLE: self.game_stats[batter]['doubles'] += 1
            if play == PlayResult.TRIPLE: self.game_stats[batter]['triples'] += 1
            if play == PlayResult.HOME_RUN: self.game_stats[batter]['home_runs'] += 1; self.game_stats[pitcher]['home_runs_allowed'] += 1
            
            if ball and (play == PlayResult.SINGLE or play == PlayResult.DOUBLE) and self.state.is_runner_on():
                # ★修正: 投手を考慮してフィールダーを探す
                best_fielder, _, _ = self.def_eng._find_nearest_fielder((ball.landing_x, ball.landing_y), defense_team, self.team_level, current_pitcher=pitcher)
                if best_fielder and best_fielder.position in [Position.LEFT, Position.CENTER, Position.RIGHT]:
                    if self.state.runner_1b: self.def_eng.judge_arm_opportunity(ball, best_fielder, self.state.runner_1b, 1, self.team_level)
                    if self.state.runner_2b: self.def_eng.judge_arm_opportunity(ball, best_fielder, self.state.runner_2b, 2, self.team_level)

            self._record_pf(batter, pitcher)
            self._reset_count(); self._next_batter()
            
            bases = 4 if play == PlayResult.HOME_RUN else (3 if play == PlayResult.TRIPLE else (2 if play == PlayResult.DOUBLE else 1))
            scored_players = self._advance_runners(bases, batter)
            
            for p in scored_players: self.game_stats[p]['runs'] += 1
            scored = len(scored_players)
            if scored > 0:
                self.game_stats[batter]['rbis'] += scored
                self.game_stats[pitcher]['runs_allowed'] += scored; self.game_stats[pitcher]['earned_runs'] += scored
                if self.state.is_top: self.state.home_current_pitcher_runs += scored
                else: self.state.away_current_pitcher_runs += scored
                self._score(scored)
            return play

        if play == PlayResult.ERROR:
            # Team Stats Aggregation (Defense makes error)
            if self.state.is_top: self.state.home_errors += 1
            else: self.state.away_errors += 1

            self.game_stats[batter]['at_bats'] += 1; self.game_stats[batter]['reach_on_error'] += 1
            self._record_pf(batter, pitcher); self._reset_count(); self._next_batter()
            scored_players = self._advance_runners(1, batter)
            for p in scored_players: self.game_stats[p]['runs'] += 1
            scored = len(scored_players)
            if scored > 0:
                self.game_stats[batter]['rbis'] += scored
                self.game_stats[pitcher]['runs_allowed'] += scored 
                if self.state.is_top: self.state.home_current_pitcher_runs += scored
                else: self.state.away_current_pitcher_runs += scored
                self._score(scored)
            return play

        is_sac_fly = False; is_sac_bunt = False; is_double_play = False; scored = 0
        sac_scored_runner = None
        
        if play == PlayResult.FLYOUT and self.state.runner_3b and self.state.outs < 2:
            # 内野フライ（POPUP）または浅い外野フライではタッチアップ不可
            is_popup_or_shallow = False
            if ball:
                from live_game_engine import BattedBallType
                if ball.hit_type == BattedBallType.POPUP:
                    is_popup_or_shallow = True  # 内野フライはタッチアップ不可
                elif ball.distance < 60:
                    is_popup_or_shallow = True  # 60m未満の浅いフライもタッチアップ不可
            
            if not is_popup_or_shallow and random.random() < 0.85: 
                is_sac_fly = True; scored = 1; sac_scored_runner = self.state.runner_3b
                self.state.runner_3b = None
        elif play == PlayResult.GROUNDOUT and self.state.runner_1b and self.state.outs < 2 and strategy != "BUNT":
            dp_skill = 50; count = 0
            for pid in defense_team.current_lineup:
                p = defense_team.players[pid]
                if p.position in [Position.SECOND, Position.SHORTSTOP]: dp_skill += get_effective_stat(p, 'turn_dp'); count += 1
            if count > 0: dp_skill /= count
            
            # 平均的な野手(50)の併殺確率
            # 実際のリーグデータがあればそれを使用 (デフォルトを少し上げて、失敗のマイナスを出しやすくする)
            avg_dp_prob = self.league_stats.get('dp_rate', 0.60)
            
            # 実際の併殺確率
            dp_prob = 0.4 + (dp_skill - 50) * 0.01; dp_prob = max(0.1, min(0.9, dp_prob))
            
            # DPR評価: 成功時は(1-平均確率)*価値、失敗時は(0-平均確率)*価値
            dpr_value = 0.8 # 併殺の価値 (アウト1つ追加 + ランナー消滅)
            
            if random.random() < dp_prob:
                is_double_play = True
                val = (1.0 - avg_dp_prob) * dpr_value * UZR_SCALE["DPR"]
                for pid in defense_team.current_lineup:
                    p = defense_team.players[pid]
                    if p.position in [Position.SECOND, Position.SHORTSTOP]: self.game_stats[p]['uzr_dpr'] += (val / 2)
                self.state.runner_1b = None
            else:
                val = (0.0 - avg_dp_prob) * dpr_value * UZR_SCALE["DPR"] # マイナス
                for pid in defense_team.current_lineup:
                    p = defense_team.players[pid]
                    if p.position in [Position.SECOND, Position.SHORTSTOP]: self.game_stats[p]['uzr_dpr'] += (val / 2)
        elif strategy == "BUNT" and play == PlayResult.GROUNDOUT:
             if self.state.is_runner_on(): is_sac_bunt = True; scored = self._advance_runners_bunt()
        
        self._record_pf(batter, pitcher)
        self.game_stats[pitcher]['innings_pitched'] += (1.0/3.0)
        self.state.outs += 1
        
        # DEBUG: Track IP recording in _resolve_play

        
        for pid in defense_team.current_lineup:
            if 0 <= pid < len(defense_team.players) and defense_team.players[pid].position != Position.DH:
                self.game_stats[defense_team.players[pid]]['defensive_innings'] += (1.0/3.0)

        if is_sac_fly:
            self.game_stats[batter]['sacrifice_flies'] += 1; self.game_stats[batter]['rbis'] += scored
            self.game_stats[pitcher]['runs_allowed'] += scored; self.game_stats[pitcher]['earned_runs'] += scored
            if self.state.is_top: self.state.home_current_pitcher_runs += scored
            else: self.state.away_current_pitcher_runs += scored
            if sac_scored_runner: self.game_stats[sac_scored_runner]['runs'] += 1
            self._score(scored)
        elif is_sac_bunt:
            self.game_stats[batter]['sacrifice_hits'] += 1
            if scored > 0:
                self.game_stats[batter]['rbis'] += scored
                self.game_stats[pitcher]['runs_allowed'] += scored; self.game_stats[pitcher]['earned_runs'] += scored
                if self.state.is_top: self.state.home_current_pitcher_runs += scored
                else: self.state.away_current_pitcher_runs += scored
                self._score(scored)
        elif is_double_play:
            self.game_stats[batter]['at_bats'] += 1; self.game_stats[batter]['grounded_into_dp'] += 1
            self.state.outs += 1; self.game_stats[pitcher]['innings_pitched'] += (1.0/3.0)
            # DEBUG: Track double play second out

            for pid in defense_team.current_lineup:
                if 0 <= pid < len(defense_team.players) and defense_team.players[pid].position != Position.DH:
                    self.game_stats[defense_team.players[pid]]['defensive_innings'] += (1.0/3.0)

        else:
            self.game_stats[batter]['at_bats'] += 1
            if scored > 0: 
                self.game_stats[batter]['rbis'] += scored
                self.game_stats[pitcher]['runs_allowed'] += scored; self.game_stats[pitcher]['earned_runs'] += scored
                if self.state.is_top: self.state.home_current_pitcher_runs += scored
                else: self.state.away_current_pitcher_runs += scored
                self._score(scored)

        self._reset_count(); self._next_batter()
        
        # Check for Walk-off immediately after play completion (if not already returned via score check)
        if self.is_game_over():
            return play

        if self.state.outs >= 3: 
            # Check if game is over (X-Game, Draw, etc.) BEFORE changing inning
            if self.is_game_over():
                return play
            
            self._change_inning()
        return play

    def _advance_runners_bunt(self) -> int:
        score = 0
        if self.state.runner_3b: score += 1; self.state.runner_3b = None
        if self.state.runner_2b: self.state.runner_3b = self.state.runner_2b; self.state.runner_2b = None
        if self.state.runner_1b: self.state.runner_2b = self.state.runner_1b; self.state.runner_1b = None
        return score

    def get_realtime_stats(self, player: Player) -> Dict[str, Any]:
        """リアルタイム成績（シーズン成績 + 今日の成績）を取得"""
        rec = player.record
        g_stats = self.game_stats[player]
        
        # Batting
        total_ab = rec.at_bats + g_stats['at_bats']
        total_h = rec.hits + g_stats['hits']
        total_hr = rec.home_runs + g_stats['home_runs']
        total_rbi = rec.rbis + g_stats['rbis']
        avg = total_h / total_ab if total_ab > 0 else 0.0
        
        # Pitching
        total_ip = rec.innings_pitched + g_stats['innings_pitched']
        total_er = rec.earned_runs + g_stats['earned_runs']
        era = (total_er * 9) / total_ip if total_ip > 0 else 0.0
        total_so = rec.strikeouts_pitched + g_stats['strikeouts_pitched']
        
        return {
            "avg": avg, "hr": total_hr, "rbi": total_rbi,
            "era": era, "so": total_so,
            "ip": total_ip
        }

    def _advance_runners(self, bases, batter, is_walk=False):
        scored_players = []
        UBR_SUCCESS_1B3B = 0.18; UBR_FAIL_1B3B = -0.80; UBR_HOLD_1B2B = -0.06  
        UBR_SUCCESS_2BH = 0.22; UBR_FAIL_2BH = -1.00; UBR_HOLD_2B3B = -0.08
        UBR_SUCCESS_1BH = 0.35; UBR_FAIL_1BH = -1.20; UBR_HOLD_1B3B = -0.07

        if is_walk:
            if self.state.runner_1b:
                if self.state.runner_2b:
                    if self.state.runner_3b: scored_players.append(self.state.runner_3b)
                    self.state.runner_3b = self.state.runner_3b if self.state.runner_3b else self.state.runner_2b
                self.state.runner_2b = self.state.runner_2b if self.state.runner_2b else self.state.runner_1b
            self.state.runner_1b = batter
        else:
            if self.state.runner_3b: scored_players.append(self.state.runner_3b); self.state.runner_3b = None
            if self.state.runner_2b:
                if bases >= 2: scored_players.append(self.state.runner_2b); self.state.runner_2b = None
                elif bases == 1:
                    spd = get_effective_stat(self.state.runner_2b, 'speed'); br = get_effective_stat(self.state.runner_2b, 'baserunning')
                    if random.random() < 0.40 + (spd - 50) * 0.015:
                        if random.random() < 0.05:
                            self.game_stats[self.state.runner_2b]['ubr_val'] += UBR_FAIL_2BH
                            self.state.runner_2b = None; self.state.outs += 1
                            # ★修正: 走塁死でもIPを記録
                            pitcher, _ = self.get_current_pitcher()
                            self.game_stats[pitcher]['innings_pitched'] += (1.0/3.0)

                            # ★修正: 走塁死で3アウトになった場合はイニングチェンジ
                            if self.state.outs >= 3:
                                self._change_inning()
                                return scored_players
                        else:
                            scored_players.append(self.state.runner_2b); self.game_stats[self.state.runner_2b]['ubr_val'] += UBR_SUCCESS_2BH
                            self.state.runner_2b = None
                    else:
                        self.state.runner_3b = self.state.runner_2b; self.game_stats[self.state.runner_2b]['ubr_val'] += UBR_HOLD_2B3B
                        self.state.runner_2b = None
            if self.state.runner_1b:
                if bases >= 3: scored_players.append(self.state.runner_1b); self.state.runner_1b = None
                elif bases == 2:
                    spd = get_effective_stat(self.state.runner_1b, 'speed'); br = get_effective_stat(self.state.runner_1b, 'baserunning')
                    if random.random() < 0.35 + (spd - 50) * 0.015:
                        if random.random() < 0.05:
                            self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_FAIL_1BH
                            self.state.runner_1b = None; self.state.outs += 1
                            # ★修正: 走塁死でもIPを記録
                            pitcher, _ = self.get_current_pitcher()
                            self.game_stats[pitcher]['innings_pitched'] += (1.0/3.0)

                            # ★修正: 走塁死で3アウトになった場合はイニングチェンジ
                            if self.state.outs >= 3:
                                self._change_inning()
                                return scored_players
                        else:
                            scored_players.append(self.state.runner_1b); self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_SUCCESS_1BH
                            self.state.runner_1b = None
                    else:
                        self.state.runner_3b = self.state.runner_1b; self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_HOLD_1B3B
                        self.state.runner_1b = None
                elif bases == 1:
                    spd = get_effective_stat(self.state.runner_1b, 'speed'); br = get_effective_stat(self.state.runner_1b, 'baserunning')
                    if self.state.runner_3b is None and random.random() < 0.25 + (spd - 50) * 0.015:
                        if random.random() < 0.05:
                            self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_FAIL_1B3B
                            self.state.runner_1b = None; self.state.outs += 1
                            # ★修正: 走塁死でもIPを記録
                            pitcher, _ = self.get_current_pitcher()
                            self.game_stats[pitcher]['innings_pitched'] += (1.0/3.0)

                            # ★修正: 走塁死で3アウトになった場合はイニングチェンジ
                            if self.state.outs >= 3:
                                self._change_inning()
                                return scored_players

                        else:
                            self.state.runner_3b = self.state.runner_1b; self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_SUCCESS_1B3B
                            self.state.runner_1b = None
                    else:
                        self.state.runner_2b = self.state.runner_1b; self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_HOLD_1B2B
                        self.state.runner_1b = None

            if bases == 4: scored_players.append(batter)
            elif bases == 3: self.state.runner_3b = batter
            elif bases == 2: self.state.runner_2b = batter
            elif bases == 1: self.state.runner_1b = batter
                
        return scored_players
    
    def _score(self, runs: int):
        # Track score before adding runs
        old_home = self.state.home_score
        old_away = self.state.away_score
        
        if self.state.is_top:
            self.state.away_score += runs
            # Ensure list is long enough
            while len(self.state.away_inning_scores) < self.state.inning:
                self.state.away_inning_scores.append(0)
            self.state.away_inning_scores[self.state.inning - 1] += runs
            
            # Track go-ahead: If away team just took the lead
            # Away team went from behind/tied to leading
            if old_away <= old_home and self.state.away_score > self.state.home_score:
                # Away team took the lead - record the AWAY team's last pitcher
                # This is the pitcher who was on the mound for AWAY before this at-bat started
                # (i.e., the last pitcher who completed their work for away team)
                if self.state.away_pitchers_used:
                    self.away_goahead_pitcher = self.state.away_pitchers_used[-1]
        else:
            self.state.home_score += runs
            while len(self.state.home_inning_scores) < self.state.inning:
                self.state.home_inning_scores.append(0)
            self.state.home_inning_scores[self.state.inning - 1] += runs
            
            # Track go-ahead: If home team just took the lead
            if old_home <= old_away and self.state.home_score > self.state.away_score:
                # Home team took the lead - record the HOME team's last pitcher
                if self.state.home_pitchers_used:
                    self.home_goahead_pitcher = self.state.home_pitchers_used[-1]

    def _reset_count(self): self.state.balls = 0; self.state.strikes = 0

    def _next_batter(self):
        self.run_pitcher_change_check()
        
        team = self.away_team if self.state.is_top else self.home_team
        lineup = team.current_lineup
        if self.team_level == TeamLevel.SECOND: lineup = team.farm_lineup
        elif self.team_level == TeamLevel.THIRD: lineup = team.third_lineup
        n = len(lineup)
        if n == 0:
            if self.state.is_top: self.state.away_batter_order = 0
            else: self.state.home_batter_order = 0
            return
        if self.state.is_top: self.state.away_batter_order = (self.state.away_batter_order + 1) % n
        else: self.state.home_batter_order = (self.state.home_batter_order + 1) % n

    def _change_inning(self):
        self.state.outs = 0
        self.state.runner_1b = self.state.runner_2b = self.state.runner_3b = None
        if not self.state.is_top: self.state.inning += 1
        self.state.is_top = not self.state.is_top

    def is_game_over(self):
        """
        NPB公式規則に基づく試合終了判定
        
        終了条件:
        1. 9回表終了時点でホーム得点＞ビジター得点 → 試合終了（Xゲーム）
        2. 9回裏途中でホーム得点＞ビジター得点 → 試合終了（サヨナラ）
        3. 9回裏終了時点でホーム得点＜ビジター得点 → 試合終了（ビジター勝利）
        4. 9回裏終了時点でホーム得点＝ビジター得点 → 延長
        5. 延長のあるイニングの裏終了時点でホーム＜ビジター → 試合終了
        6. 延長のあるイニングの裏途中でホーム＞ビジター → 試合終了（サヨナラ）
        7. 延長12回裏終了 → 試合終了（引き分け）
        """
        inning = self.state.inning
        is_top = self.state.is_top
        outs = self.state.outs
        home = self.state.home_score
        away = self.state.away_score
        
        # [規則1] 9回以降の表、3アウト時点でホームがリード → Xゲーム終了
        if inning >= 9 and is_top and outs >= 3:
            if home > away:
                return True
        
        # [規則2+6] 9回以降の裏、途中でホームがリード → サヨナラ勝ち
        # Note: これはイニング中のどのタイミングでも判定（得点した瞬間）
        if inning >= 9 and not is_top and outs < 3:
            if home > away:
                return True
        
        # [規則3+5] 9回以降の裏、3アウト時点で勝敗が決した場合
        if inning >= 9 and not is_top and outs >= 3:
            # ビジターがリード → ビジター勝利
            if away > home:
                return True
            # ホームがリード → ホーム勝利（サヨナラ、念のため）
            if home > away:
                return True
            # 同点の場合:
            # - 12回以降なら引き分け終了
            # - それ未満なら延長継続（False）
            if home == away:
                # 無制限設定（max_innings is None）なら続行
                if self.max_innings is None:
                    return False
                # 上限到達なら引き分け終了
                elif inning >= self.max_innings:
                    return True  # [規則7] 規定回終了で引き分け
                else:
                    return False  # 延長継続
        
        # ハードリミット (max_innings指定時のみ)
        if self.max_innings is not None and inning > self.max_innings:
            return True

        return False



    def finalize_game_stats(self, date_str: str = "2027-01-01"):
        """
        NPB公式規則に基づく責任投手判定
        - 勝利投手: 先発は5回以上投球必要、それ以外は最も効果的な救援投手
        - 敗戦投手: 決勝点を許した投手
        - セーブ: 勝利投手以外、最終投手、1/3イニング以上、リード維持
                  かつ(3点差以内で1回以上 OR 次打者2人HRで同点 OR 3回以上投球)
        - ホールド: 先発/勝利/敗戦/セーブ以外、最終投手以外、1アウト以上
                    自責点でリード失わない、かつ(3点差以内で1回以上 OR 次打者2人HRで同点 OR 3回以上)
        """
        win_p, loss_p, save_p, hold_ps = None, None, None, []
        if not self.state.home_pitchers_used or not self.state.away_pitchers_used:
            return None

        home_win = self.state.home_score > self.state.away_score
        away_win = self.state.away_score > self.state.home_score
        is_draw = not home_win and not away_win
        
        # Ensure inning scores cover all innings played (for extra innings with no runs)
        while len(self.state.away_inning_scores) < self.state.inning:
            self.state.away_inning_scores.append(0)
        while len(self.state.home_inning_scores) < self.state.inning:
            self.state.home_inning_scores.append(0)
        
        # DEBUG: Show pitchers used in order and their IP



        
        if is_draw:
            # 引き分けの場合も成績と疲労を反映する
            if not self.is_all_star and not self.is_postseason:
                for player, stats in self.game_stats.items():
                    record = player.get_record_by_level(self.team_level)
                    for key, val in stats.items():
                        if hasattr(record, key):
                            current = getattr(record, key)
                            setattr(record, key, current + val)
                    record.games += 1
                    
                    # 疲労蓄積
                    if player.position == Position.PITCHER:
                        pitches = stats.get('pitches_thrown', 0)
                        if pitches > 0:
                            player.add_game_fatigue(pitches_thrown=pitches)
                            player.days_rest = 0
                    else:
                        at_bats = stats.get('at_bats', 0) + stats.get('walks', 0) + stats.get('hit_by_pitch', 0)
                        defensive_innings = 9.0 if at_bats > 0 else 0
                        if at_bats > 0 or defensive_innings > 0:
                            player.add_game_fatigue(at_bats=at_bats, defensive_innings=defensive_innings)
                    
                    # 日別記録追加
                    temp_rec = PlayerRecord()
                    for key, val in stats.items():
                        if hasattr(temp_rec, key): setattr(temp_rec, key, val)
                    player.add_game_record(date_str, temp_rec)
            
            highlights = self._analyze_highlights(None, None, None, False, False)
            return {
                "win": None, "loss": None, "save": None,
                "game_stats": self.game_stats, "highlights": highlights,
                "is_draw": True
            }

        # 勝利/敗戦チーム判定
        if home_win:
            win_team_pitchers = list(self.state.home_pitchers_used)
            loss_team_pitchers = list(self.state.away_pitchers_used)
            win_team = self.home_team
        else:
            win_team_pitchers = list(self.state.away_pitchers_used)
            loss_team_pitchers = list(self.state.home_pitchers_used)
            win_team = self.away_team

        # === ゲーム出場記録補正 (バグ回避用) ===
        # 登板した全投手について、実際に投球した場合のみgames_pitchedを記録
        for p in win_team_pitchers + loss_team_pitchers:
            pitches = self.game_stats[p].get('pitches_thrown', 0)
            # Only count as "pitched in game" if actually threw at least 1 pitch
            if pitches > 0:
                if 'games_pitched' not in self.game_stats[p] or self.game_stats[p]['games_pitched'] == 0:
                    self.game_stats[p]['games_pitched'] = 1

        # === 勝利投手判定 (NPB規則9.17準拠) ===
        # 9.17(a): 投手登板中(または交代時の回)にチームがリードを奪い、それを維持した場合、その投手が勝利投手
        # 9.17(b): 先発投手は5回以上投球が必要 (コールドで6回未満の場合は4回)
        # 9.17(c): 救援投手が少しの間投げただけで効果的でなかった場合、最も効果的な救援投手に勝利が与えられる
        
        starter = win_team_pitchers[0]
        starter_ip = self.game_stats[starter]['innings_pitched']
        total_innings = self.state.inning  # 試合の総イニング数
        
        # 先発の必要投球回数 (通常は5回、6回未満のコールドは4回)
        required_starter_ip = 4.0 if total_innings < 6 else 5.0
        
        # 勝ち越し点を許した相手投手を取得 (= 勝利チームが勝ち越した時にマウンドにいた相手投手)
        # これは勝利チームにいた投手ではなく、敗北チームにいた投手
        # 勝利チームが勝ち越した時の投手を逆引きする必要がある
        if home_win:
            # ホームが勝った → ホームが勝ち越した時にマウンドにいたのは home_goahead_pitcher (=アウェイ投手)
            # 勝利投手は、その時に「ホームチームがリードを奪った」時の最後のホーム投手
            # home_goahead_pitcher は「アウェイ投手」なので、逆に考える必要がある
            # ホームがリードを奪った時、打っていたのはホームチーム
            # その時マウンドにいた「アウェイ投手」が home_goahead_pitcher
            # 勝利チーム(ホーム)の投手で、その時点で最後に投げていた投手を特定する必要がある
            pass  # 下のロジックで処理
        
        # サヨナラ勝利の場合: 最終回表に登板していた最後の投手が勝利投手
        is_walkoff = home_win and self.state.is_top == False  # ホームがサヨナラ勝ち
        
        if is_walkoff:
            # サヨナラゲーム: 勝利チーム(ホーム)の最後の投手が勝利投手
            win_p = win_team_pitchers[-1]
        elif starter_ip >= required_starter_ip:
            # 先発が規定投球回を満たした → 先発が勝利投手
            win_p = starter
        elif len(win_team_pitchers) == 1:
            # 先発1人のみ(規定回に達していなくても) → 先発が勝利投手
            win_p = starter
        else:
            # 救援投手から勝利投手を選ぶ (9.17(b)後段, 9.17(c))
            relievers = win_team_pitchers[1:]
            
            # 9.17(a)に基づき、勝ち越し点が入った時にマウンドにいた(または直前に降板した)投手を優先
            goahead_p = self.home_goahead_pitcher if home_win else self.away_goahead_pitcher
            
            if len(relievers) == 1:
                # 救援1人なら自動的にその投手
                win_p = relievers[0]
            elif goahead_p and goahead_p in relievers:
                # 勝ち越し点が入った時の投手がリリーバーにいる場合
                goahead_ip = self.game_stats[goahead_p]['innings_pitched']
                goahead_runs = self.game_stats[goahead_p].get('runs_allowed', 0)
                
                # 9.17(c): 少しの間投げただけで効果的でない場合は対象外
                # 1イニング未満かつ2失点以上なら効果的でないとみなす
                if goahead_ip < 1.0 and goahead_runs >= 2:
                    # 効果的でない → 他の最も効果的な投手を選ぶ
                    other_relievers = [p for p in relievers if p != goahead_p]
                    if other_relievers:
                        best = max(other_relievers, 
                            key=lambda p: (self.game_stats[p]['innings_pitched'], 
                                          -self.game_stats[p].get('runs_allowed', 0)))
                        win_p = best
                    else:
                        win_p = goahead_p
                else:
                    # 効果的だった → 勝ち越し時の投手が勝利投手
                    win_p = goahead_p
            else:
                # 勝ち越し時の投手がリリーバーにいない場合 → 従来のロジック
                # 複数救援: 9.17(b)後段ルール
                # 1. 投球回が他の投手より1回以上多い投手がいればその投手
                # 2. 投球回が同等(差1回未満)なら最も効果的な投手
                # 3. 同程度に効果的なら先に登板した投手
                
                reliever_stats = [(p, self.game_stats[p]['innings_pitched'], 
                                   self.game_stats[p].get('runs_allowed', 0)) 
                                  for p in relievers]
                
                # 投球回が多い順にソート
                reliever_stats.sort(key=lambda x: x[1], reverse=True)
                
                # 最多投球回とその投手
                max_ip = reliever_stats[0][1]
                
                # 1回以上多く投げた投手がいるかチェック
                candidates_1inning = [p for p, ip, _ in reliever_stats if max_ip - ip < 1.0]
                
                if len(candidates_1inning) == 1:
                    # 1回以上多く投げた投手が1人だけ
                    win_p = candidates_1inning[0]
                else:
                    # 同程度の投球回の投手から選ぶ
                    # 効果性: 失点が少ない投手を優先、同等なら登板順が早い投手
                    candidate_stats = [(p, ip, runs) for p, ip, runs in reliever_stats 
                                       if max_ip - ip < 1.0]
                    # 失点が少ない順、登板順(relieversリストの順)でソート
                    candidate_stats.sort(key=lambda x: (x[2], relievers.index(x[0])))
                    win_p = candidate_stats[0][0]

        # === 敗戦投手判定 (NPB規則) ===
        # 決勝点を許した投手 = 最初にリードを許した時に投げていた投手
        # 簡易実装: 敗戦チームの先発投手(通常最も失点が多い)
        loss_p = loss_team_pitchers[0]
        # より正確には、登板時スコア差と失点を追跡して判定すべき
        # 最も失点が多い投手を敗戦投手とする簡易ルール
        if len(loss_team_pitchers) > 1:
            runs_map = {p: self.game_stats[p].get('runs_allowed', 0) for p in loss_team_pitchers}
            max_runs = max(runs_map.values())
            # 失点が多い投手の中で、登板順が早い投手を優先（先発など）
            candidates = [p for p in loss_team_pitchers if runs_map[p] == max_runs]
            loss_p = candidates[0]

        # === セーブ判定 (NPB規則) ===
        final_pitcher = win_team_pitchers[-1]
        if final_pitcher != win_p:
            final_ip = self.game_stats[final_pitcher]['innings_pitched']
            score_diff = abs(self.state.home_score - self.state.away_score)
            entry_diff = self.game_stats[final_pitcher].get('entry_score_diff', score_diff)
            
            # セーブ必須条件:
            # 1. 勝利投手ではない ✓ (上でチェック済み)
            # 2. 最終投手 ✓ (final_pitcher)
            # 3. 1/3イニング(1アウト)以上
            # 4. リードを維持して試合終了
            if final_ip >= 1/3:
                # 特定条件のいずれか:
                # a) 登板時3点差以内で1イニング以上
                # b) 登板時、次2打者HRで同点(走者+2点差以下) 
                # c) 3イニング以上投球
                
                # 登板時差が3点以内
                cond_a = (entry_diff <= 3 and final_ip >= 1.0)
                # 3イニング以上
                cond_c = (final_ip >= 3.0)
                # 2打者本塁打で同点/逆転 (簡易判定: 2点差以内ならOK、ただしIP<1の場合でもOK)
                cond_b = (entry_diff <= 2) 

                is_save_situation = (cond_a or cond_b or cond_c)
                
                # 先発投手はセーブ対象外
                is_starter = (final_pitcher == win_team_pitchers[0])
                
                if is_save_situation and not is_starter:
                    save_p = final_pitcher

        # === ホールド判定 (NPB規則) ===
        # 条件:
        # 1. 勝利・敗戦・セーブ以外
        # 2. 1アウト(1/3回)以上
        # 3. リード維持 または 同点維持
        #    - リード時: セーブと同じシチュエーション条件 (3点差以内1回、2者連発圏内、3回以上)
        #    - 同点時: 失点せず同点のまま降板 (勝ち越した場合は勝利投手になるためここには来ないが、同点のままならホールド)
        
        # ホールドは両チーム対象（先発は対象外）
        all_pitchers_for_hold = []
        all_pitchers_for_hold.extend(win_team_pitchers)
        all_pitchers_for_hold.extend(loss_team_pitchers)
        
        # 先発投手を除外（先発はホールド対象外）
        home_starter = self.state.home_pitchers_used[0] if self.state.home_pitchers_used else None
        away_starter = self.state.away_pitchers_used[0] if self.state.away_pitchers_used else None

        for p in all_pitchers_for_hold:
            if p == win_p or p == loss_p or p == save_p: continue
            if p == home_starter or p == away_starter: continue  # 先発は除外
            if 'innings_pitched' not in self.game_stats[p]: continue
            
            ip = self.game_stats[p]['innings_pitched']
            runs = self.game_stats[p].get('runs_allowed', 0)
            entry_diff = self.game_stats[p].get('entry_score_diff', 0) 
            
            if ip >= 1/3:
                # 登板時リード (entry_diff > 0)
                if entry_diff > 0:
                    # 降板時もリード (簡易: 逆転許さず)
                    lead_kept = (entry_diff - runs > 0)
                    if lead_kept:
                        # 条件判定
                        is_hold = False
                        if entry_diff <= 3 and ip >= 1.0: is_hold = True
                        elif entry_diff <= 2: is_hold = True # 2点差以内なら1アウトでOK
                        elif ip >= 3.0: is_hold = True
                        
                        if is_hold: hold_ps.append(p)
                
                # 登板時同点 (entry_diff == 0)
                elif entry_diff == 0:
                    # 失点0なら「同点を維持」
                    if runs == 0:
                        hold_ps.append(p)

        # 記録を反映
        if win_p: self.game_stats[win_p]['wins'] += 1
        if loss_p: self.game_stats[loss_p]['losses'] += 1
        if save_p: self.game_stats[save_p]['saves'] += 1
        for hp in hold_ps: self.game_stats[hp]['holds'] += 1

        # 疲労更新 (days_restリセット & スタミナ消費)
        for p in self.state.home_pitchers_used + self.state.away_pitchers_used:
            p.days_rest = 0
            pitches = self.game_stats[p]['pitches_thrown']
            p.current_stamina = max(0, p.current_stamina - pitches)

        # Update stats
        if not self.is_all_star and not self.is_postseason: # オールスター・ポストシーズン（別途実装）はレギュラー成績に加算しない(要望)
            # TODO: Postseason check if needed
            
            # DEBUG: Show players getting stats in farm games
            for player, stats in self.game_stats.items():
                # Skip players whose level doesn't match game level
                if self.team_level != TeamLevel.FIRST and player.team_level != self.team_level:
                    continue  # Don't add stats for wrong-level players
                
                record = player.get_record_by_level(self.team_level)
                for key, val in stats.items():
                    if hasattr(record, key):
                        current = getattr(record, key)
                        setattr(record, key, current + val)
                record.games += 1
                
                # CG/SHO check - Complete game is when starter was the ONLY pitcher used
                ip = stats.get('innings_pitched', 0.0)
                gs = stats.get('games_started', 0)
                runs = stats.get('runs_allowed', 0)
                
                # Check if this pitcher was the only one used for their team
                is_home_pitcher = player in self.home_team.players
                if is_home_pitcher:
                    is_only_pitcher = len(self.state.home_pitchers_used) == 1 and self.state.home_pitchers_used[0] == player
                else:
                    is_only_pitcher = len(self.state.away_pitchers_used) == 1 and self.state.away_pitchers_used[0] == player
                
                # Complete game: started AND was the only pitcher AND pitched at least 9 full innings
                # Use >= 8.9 to avoid floating point issues with 9.0
                if gs == 1 and is_only_pitcher and ip >= 8.9:
                    record.complete_games += 1
                    stats['complete_games'] = 1 # for daily record
                    if runs == 0:
                        record.shutouts += 1
                        stats['shutouts'] = 1 # for daily record

                is_home_player = player in self.home_team.players
                if is_home_player:
                    if player.position == Position.PITCHER: record.home_games_pitched += 1
                    else: record.home_games += 1
                
                temp_rec = PlayerRecord()
                for key, val in stats.items():
                    if hasattr(temp_rec, key): setattr(temp_rec, key, val)
                player.add_game_record(date_str, temp_rec)
                
                # 疲労蓄積: 打者は打席+守備イニング、投手は投球数ベース
                if player.position == Position.PITCHER:
                    pitches = stats.get('pitches_thrown', 0)
                    if pitches > 0:
                        player.add_game_fatigue(pitches_thrown=pitches)
                else:
                    at_bats = stats.get('at_bats', 0) + stats.get('walks', 0) + stats.get('hit_by_pitch', 0)
                    # 守備イニング（スタメン野手は約9イニング想定）
                    defensive_innings = 9.0 if at_bats > 0 else 0
                    if at_bats > 0 or defensive_innings > 0:
                        # print(f"[FATIGUE DEBUG] Engine applying fatigue to Batter: {player.name} (ID: {id(player)}) - AB: {at_bats}")
                        player.add_game_fatigue(at_bats=at_bats, defensive_innings=defensive_innings)
            
        # Highlight Analysis
        highlights = self._analyze_highlights(win_p, loss_p, save_p, home_win, away_win)

        # Trim score lists to actual game length
        # Calculate actual completed innings based on game state
        final_inning = self.state.inning
        
        # For X-game (home wins without batting in bottom half), 
        # home_inning_scores should be 1 shorter than away_inning_scores
        # For normal games ending in bottom half, both are same length
        
        # Determine actual completed innings with improved logic for Draw and X-games
        
        # 1. Draw Game Correction
        # If inning > 12 (NPB rules), game ended after 12th bottom.
        # State would be inning=13, is_top=True.
        MAX_INNINGS = 12
        if self.state.inning > MAX_INNINGS:
            away_completed_innings = MAX_INNINGS
            home_completed_innings = MAX_INNINGS
        else:
            final_inning = self.state.inning
            away_completed_innings = final_inning
            
            # 2. X-Game / Called Game Logic
            # If it's bottom of inning but 0 outs and Home leads -> X-game (Home didn't bat)
            if not self.state.is_top and self.state.outs == 0 and self.state.home_score > self.state.away_score:
                home_completed_innings = final_inning - 1
            elif self.state.is_top:
                # Game ended during top half (should be rare/called game) or after top half
                home_completed_innings = final_inning - 1
            else:
                # Game ended during or after bottom half
                home_completed_innings = final_inning
        
        # Strict trimming: only keep actually played innings
        # Minimum 9 innings unless game was shorter (impossible in normal play)
        away_completed_innings = max(9, away_completed_innings)
        home_completed_innings = max(8, home_completed_innings)  # X-game in 9th = 8 batting innings for home
        
        # Extend arrays to match completed innings (fill with 0 for scoreless innings)
        # This ensures that scoreless innings (especially in extra innings) are recorded
        while len(self.state.home_inning_scores) < home_completed_innings:
            self.state.home_inning_scores.append(0)
        while len(self.state.away_inning_scores) < away_completed_innings:
            self.state.away_inning_scores.append(0)

        # Trim arrays (if longer than needed)
        if len(self.state.home_inning_scores) > home_completed_innings:
            self.state.home_inning_scores = self.state.home_inning_scores[:home_completed_innings]
        if len(self.state.away_inning_scores) > away_completed_innings:
            self.state.away_inning_scores = self.state.away_inning_scores[:away_completed_innings]
        


        return {
            "win": win_p,
            "loss": loss_p,
            "save": save_p,
            "game_stats": self.game_stats,
            "highlights": highlights,
            "home_pitchers_used": list(self.state.home_pitchers_used),
            "away_pitchers_used": list(self.state.away_pitchers_used)
        }


    def _analyze_highlights(self, win_p, loss_p, save_p, home_win, away_win):
        """Analyze game stats for highlight news"""
        highlights = []
        
        # Win Team & Lose Team
        win_team = self.home_team if home_win else self.away_team
        loss_team = self.home_team if home_win else self.away_team
        
        # 1. Pitching Highlights
        for p in self.state.home_pitchers_used + self.state.away_pitchers_used:
            stats = self.game_stats[p]
            ip = stats.get('innings_pitched', 0)
            so = stats.get('strikeouts_pitched', 0)
            runs = stats.get('runs_allowed', 0)
            
            p_team = self.home_team if p in self.home_team.players else self.away_team
            
            # Shutout (Kanpu) - Must be complete game (9+ IP) and 0 runs
            if ip >= 9.0 and runs == 0 and stats.get('games_started', 0) == 1:
                highlights.append({
                    "category": "PERFORMANCE",
                    "message": f"{p.name}投手（{p_team.name}）が完封勝利！",
                    "team": p_team.name,
                    "score": 100
                })
            # Complete Game (Kantou) - Must be complete game (9+ IP)
            elif ip >= 9.0 and stats.get('games_started', 0) == 1:
                highlights.append({
                    "category": "PERFORMANCE",
                    "message": f"{p.name}投手（{p_team.name}）が完投勝利！" if p == win_p else f"{p.name}投手（{p_team.name}）が完投！",
                    "team": p_team.name,
                    "score": 90
                })
            
            # 10+ Strikeouts
            if so >= 10:
                highlights.append({
                    "category": "PERFORMANCE",
                    "message": f"{p.name}投手（{p_team.name}）が{so}奪三振の快投！",
                    "team": p_team.name,
                    "score": 85
                })

        # 2. Batting Highlights
        for p, stats in self.game_stats.items():
            if p.position == Position.PITCHER and stats.get('at_bats', 0) == 0: continue
            
            p_team = self.home_team if p in self.home_team.players else self.away_team
            
            hr = stats.get('home_runs', 0)
            hits = stats.get('hits', 0)
            rbi = stats.get('rbis', 0)
            
            # Multi-HR
            if hr >= 3:
                highlights.append({
                    "category": "PERFORMANCE",
                    "message": f"{p.name}選手（{p_team.name}）が1試合3本塁打の大爆発！",
                    "team": p_team.name,
                    "score": 120
                })
            elif hr == 2:
                highlights.append({
                    "category": "PERFORMANCE",
                    "message": f"{p.name}選手（{p_team.name}）が2打席連続本塁打！", # Simplified text
                    "team": p_team.name,
                    "score": 95
                })
            elif hr == 1:
                 # Check for Walk-off (Sayonara)
                 # Difficult to detect strictly without play-by-play history, 
                 # but if home team won, game ended in 9+ inning bottom, and this player hit a HR...
                 # We need more context for walk-off. Skipping for now unless added to state.
                 pass

            # Cycle Hit (Requires keeping track of hit types per player more granularly OR checking stat dict)
            # Checking stats dict keys? 'hits' is total.
            # We don't track singles/doubles separately in game_stats dict by default?
            # Let's check structure.
            # game_stats[p] keys: at_bats, hits, doubles, triples, home_runs... usually.
            # We assume standard keys exist.
            
            # 3+ Hits (Mouda)
            if hits >= 4:
                highlights.append({
                    "category": "PERFORMANCE",
                    "message": f"{p.name}選手（{p_team.name}）が固め打ち、4安打の大活躍！",
                    "team": p_team.name,
                    "score": 80
                })
            elif hits == 3:
                 # Common, maybe too noisy? Log only if significant?
                 # Highlights should be special. 3 hits is good but happens often.
                 pass

            # 4+ RBIs
            if rbi >= 4:
                highlights.append({
                    "category": "PERFORMANCE",
                    "message": f"{p.name}選手（{p_team.name}）が勝負強さを発揮、{rbi}打点！",
                    "team": p_team.name,
                    "score": 85
                })
        
        # Sort by score (importance)
        highlights.sort(key=lambda x: x['score'], reverse=True)
        return highlights

    def get_winner(self):
        if self.state.home_score > self.state.away_score: return self.home_team.name
        if self.state.away_score > self.state.home_score: return self.away_team.name
        return "DRAW"