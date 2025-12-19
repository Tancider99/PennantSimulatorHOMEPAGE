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

        # 3. Starter Logic
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
                
            # (C) Inning Start Check (Avoid starting tired)
            if state.outs == 0:
                # Allow pushing for Quality Start (6IP, <3 ER) if doing well
                is_qs_pace = state.inning >= 6 and current_runs <= 3
                stamina_threshold = 10 if is_qs_pace else 18 # Further relaxed thresholds for more starter innings
                if current_stamina < stamina_threshold:
                     return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
                
                # Close Game (Lead/Deficit <= 2) and Inning >= 7 -> Go to bullpen if showing fatigue
                if state.inning >= 7 and abs(score_diff) <= 2:
                    if float(pitch_count) > 120 or current_stamina < 25: # Further relaxed for starter innings
                        return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
                        
            # (D) Crisis Management (Mid-Inning)
            # 6th Inning+, Close Game, Runners on base
            if state.inning >= 6 and abs(score_diff) <= 3 and (state.runner_1b or state.runner_2b):
                if current_stamina < 15: # Tired and in trouble (further relaxed)
                    return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
                if current_runs >= 6: # Giving up runs (further relaxed)
                    return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)

        # 4. Reliever Logic
        else:
            role = self._get_pitcher_role_in_game(team, current_pitcher)
            
            # (A) Closer special case
            is_save_situation = (score_diff > 0 and score_diff <= 3) or (score_diff > 0 and (state.runner_1b or state.runner_2b or state.runner_3b) and score_diff == 4) 
            if role == PitcherRole.CLOSER and is_save_situation and state.inning >= 9:
                return None # Ensure finish
                
            # (B) Fatigue / Limits
            if current_stamina < 10: return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
            if pitch_count > 40: return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
            
            # (C) Inning Straddle Prevention (Strict)
            # Start of new inning
            if state.outs == 0 and current_pitcher_ip > 0:
                 # Exceptions:
                 # 1. Closer in tie game (9th-10th) or save situation
                 # 2. Long relief in blowout
                 # 3. Setup A (8th) finishing 8th then maybe facing 1 batter in 9th? No, usually pull.
                 
                if role == PitcherRole.CLOSER and state.inning >= 9:
                     pass # Keep going
                elif role == PitcherRole.LONG and abs(score_diff) >= 4:
                     # Long reliever can throw multiple innings in blowout
                     if current_pitcher_ip < 2.0: pass
                     else: return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
                else:
                     # Setup/Middle -> Pull immediately at start of inning
                     return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)

            # (D) One Inning Limit (Mid-inning limit)
            # If IP >= 1.0, look for exit (unless Closer)
            if current_pitcher_ip >= 1.0:
                if role == PitcherRole.CLOSER and is_save_situation: pass
                elif role == PitcherRole.LONG and abs(score_diff) >= 4: 
                    if current_pitcher_ip >= 3.0: return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
                else:
                    return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)
            
            # (E) Crisis (Reliever blowing it)
            if current_runs >= 2 and score_diff <= 2:
                return self._select_reliever(team, state, score_diff, next_batter, current_pitcher)

        # 5. Situational Matchups (Lefty Specialist)
        # Winning pattern (7th+), Close game, Lefty batter coming up
        if state.inning >= 7 and score_diff > 0 and score_diff <= 3 and next_batter.bats == "左":
            if current_pitcher.throws == "右" and not (is_starter and current_stamina > 40):
                # Don't pull Closer/Setup A casually
                role = self._get_pitcher_role_in_game(team, current_pitcher)
                if role not in [PitcherRole.CLOSER, PitcherRole.SETUP_A]:
                    specialist = self._find_available_reliever(team, state, role_filter=[PitcherRole.SPECIALIST])
                    if specialist: return specialist

        return None

    def _select_reliever(self, team: Team, state: GameState, score_diff: int, next_batter: Player, current_pitcher: Player) -> Optional[Player]:
        """
        Select the best available reliever based on the game situation ("Winning Pattern" vs "Losing/Mop-up").
        """
        used_pitchers = state.home_pitchers_used if state.is_top else state.away_pitchers_used
        
        # 1. Determine Target Role Strategy
        target_roles = []
        is_winning = score_diff > 0
        is_close = abs(score_diff) <= 3
        is_blowout = abs(score_diff) >= 5
        
        # (A) Victory Formula (Winning & Close)
        if is_winning and is_close:
            if state.inning >= 9:
                target_roles = [PitcherRole.CLOSER, PitcherRole.SETUP_A]
            elif state.inning == 8:
                target_roles = [PitcherRole.SETUP_A, PitcherRole.SETUP_B, PitcherRole.MIDDLE]
            elif state.inning == 7:
                target_roles = [PitcherRole.SETUP_B, PitcherRole.MIDDLE]
            else:
                target_roles = [PitcherRole.MIDDLE, PitcherRole.LONG]
                
        # (B) Tie Game (High Leverage)
        elif score_diff == 0:
            if state.inning >= 8:
                target_roles = [PitcherRole.SETUP_A, PitcherRole.SETUP_B, PitcherRole.CLOSER] # Go for win
            else:
                target_roles = [PitcherRole.MIDDLE, PitcherRole.SETUP_B]
                
        # (C) Losing (Close)
        elif not is_winning and is_close:
            # Keep it close using good middle relievers
            target_roles = [PitcherRole.MIDDLE, PitcherRole.SETUP_B]
            
        # (D) Blowout (Win or Loss) -> Save high leverage arms
        else:
            target_roles = [PitcherRole.LONG, PitcherRole.MIDDLE]

        # 2. Find Candidates Matching Roles
        # Flatten priority list: Start searching for the first role, then second...
        candidate = None
        
        # Lefty Specialist check for High Leverage
        if is_close and next_batter.bats == "左":
            candidate = self._find_available_reliever(team, state, role_filter=[PitcherRole.SPECIALIST])
            if candidate: return candidate

        for role in target_roles:
            candidate = self._find_available_reliever(team, state, role_filter=[role])
            if candidate: return candidate
            
        # 3. Fallback: Any available arm (sorted by appropriate ability)
        # If we need a win, get best available. If blowout, get worst available.
        all_available = self._get_all_available_relievers(team, state)
        if not all_available: return None # No one left! (Should catch elsewhere)
        
        if is_winning and is_close:
            # Best available
            all_available.sort(key=lambda p: p.stats.overall_pitching(), reverse=True)
        else:
            # Save arms (worst first, or high stamina)
            all_available.sort(key=lambda p: p.stats.overall_pitching(), reverse=False)
            
        return all_available[0]
        
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
        rotation_p = [team.players[i] for i in team.rotation if 0 <= i < len(team.players)]
        
        avail = []
        for idx in team.active_roster:
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
    def __init__(self):
        # 投手管理は PitchingDirector で行うため、ここでは不要
        pass

    def decide_strategy(self, state: GameState, offense_team, defense_team, batter: Player) -> str:
        score_diff = state.away_score - state.home_score if state.is_top else state.home_score - state.away_score
        is_late = state.inning >= 7
        is_close = abs(score_diff) <= 2
        
        bunt_skill = get_effective_stat(batter, 'bunt_sac')
        if state.outs == 0 and (state.runner_1b) and not state.runner_3b:
            batting_ab = batter.stats.overall_batting()
            if batter.position == Position.PITCHER: return "BUNT"
            if (is_close and is_late) or (bunt_skill > 70 and batting_ab < 45) or (state.runner_2b and is_close):
                return "BUNT"
        
        # 二盗判定（1塁ランナーがいて2塁が空いている）
        if state.runner_1b and not state.runner_2b and not state.runner_3b and state.outs < 2:
            runner_spd = get_effective_stat(state.runner_1b, 'speed')
            runner_stl = get_effective_stat(state.runner_1b, 'steal')
            attempt_prob = 0.02 + (runner_spd - 50) * 0.003
            attempt_prob *= (0.7 + (runner_stl / 50.0) * 0.5)
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
            if is_close and is_late: attempt_prob *= 0.3  # 接戦終盤は特に慎重
            elif abs(score_diff) >= 4: attempt_prob *= 1.5  # 点差があれば積極的
            if random.random() < max(0.002, attempt_prob): return "STEAL"
        
        eff_power = get_effective_stat(batter, 'power', is_risp=state.is_risp())
        if state.balls >= 3 and state.strikes < 2 and eff_power > 65: return "POWER"
        
        eff_contact = get_effective_stat(batter, 'contact', is_risp=state.is_risp())
        eff_avoid_k = get_effective_stat(batter, 'avoid_k')
        if state.strikes == 2 and eff_contact > 50 and eff_avoid_k > 50: return "MEET"
            
        return "SWING"

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
                # 本当は出場済みフラグが見たい
                if hasattr(p, 'has_played') and p.has_played: continue 
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

        base_velo = velocity * fatigue
        if pitch_type != "ストレート":
            speed_ratio = base["base_speed"] / 145.0
            base_velo *= speed_ratio
        velo = random.gauss(base_velo, 1.5); velo = max(80, min(170, velo))

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
        # 修正: 変化球のペナルティを軽減 (0.25 -> 0.20)
        con_eff = contact + meet_bonus - (p_move - 50) * 0.20 - ball_penalty
        
        # --- 打球速度を先に計算し、それでHard/Mid/Softを判定 ---
        # ベース速度: パワー・コンタクト依存
        base_v = 145 + (power - 50) * 0.8 + (con_eff - 50) * 0.1
        if strategy == "POWER": base_v += 10
        elif strategy == "MEET": base_v -= 5
        
        # --- 芯を捉えた/外したの判定 ---
        # 芯を捉える確率: コンタクト能力依存 (平均で約15%)
        barrel_chance = 0.10 + con_eff * 0.001  # 8-18%
        barrel_chance = max(0.10, min(0.20, barrel_chance))
        
        # 芯を外す確率: コンタクトが低いほど高い (平均で約10%)
        mishit_chance = 0.40- con_eff * 0.002  # 10-20%
        mishit_chance = max(0.20, min(0.40, mishit_chance))
        
        contact_roll = random.random()
        if contact_roll < barrel_chance:
            # 芯を捉えた (バレル): 打球速度ボーナス
            base_v += 20
        elif contact_roll > (1.0 - mishit_chance):
            # 芯を外した: 打球速度デバフ
            base_v -= 50
        
        # ランダム要素を追加 (標準偏差12km/hでばらつき)
        velo = base_v + random.gauss(0, 12)
        velo = max(60, min(180, velo))  # 60-180km/hに制限
        
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
        
        traj_bias = 5 + (trajectory * 5)
        angle_center = traj_bias - (p_gb_tendency - 50) * 0.2
        # --- 修正: ポップフライ増加を抑制、ライナー性へ誘導 ---
        angle_center += 1.0  # +3.0 -> +1.0
        
        if pitch.location.z < 0.5: angle_center -= 5
        if pitch.location.z > 0.9: angle_center += 5
        if gap > 60 and quality != "soft" and random.random() < (gap/150): angle_center = 15
        
        if strategy == "BUNT":
            angle = -20; velo = 30 + random.uniform(-5, 5)
            bunt_skill = get_effective_stat(batter, 'bunt_sac')
            if random.uniform(0, 100) > bunt_skill:
                if random.random() < 0.5: angle = 30
                else: velo += 20
            quality = "soft"
        else:
            # --- BABIP個人差縮小: 打球角度のランダム性を上げる ---
            base_angle = 15 + (angle_center - 15) * 0.2
            angle = random.gauss(base_angle, 22)
            angle = max(-50, min(70, angle))
        
        # ハードヒットの最低速度保証
        if quality == "hard": velo = max(velo, 152)
        
        # --- ゴロ減少、フライ増加に調整 ---
        gb_limit = 15 + (140 - velo) * 0.06  # ゴロ判定を狭く (変更なし)
        ld_limit = 20 - (140 - velo) * 0.02  # ライナー判定を狭く (24→20)
        # FB% = FLYBALL + POPUP (全フライ)
        # IFFB% = POPUP / (FLYBALL + POPUP)
        
        if angle < gb_limit: htype = BattedBallType.GROUNDBALL
        elif angle < ld_limit: htype = BattedBallType.LINEDRIVE
        elif angle < 50: htype = BattedBallType.FLYBALL  # フライ判定を広く (変更なし)
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
        
        drag_base = 0.92 - (velo / 550.0) 
        drag_factor = max(0.2, drag_base)
        
        if angle > 45 or angle < 10: drag_factor *= 0.75 
        elif angle >= 20 and angle <= 45: 
             if velo > 150: drag_factor *= 0.85
             else: drag_factor *= 0.88 
             
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
        
        return BattedBallData(velo, angle, spray, htype, dist, hang_time, land_x, land_y, [], quality)

class AdvancedDefenseEngine:
    def judge(self, ball: BattedBallData, defense_team: Team, team_level: TeamLevel = TeamLevel.FIRST, stadium: Stadium = None, current_pitcher: Player = None, league_stats: Dict[str, float] = None, batter: Player = None):
        abs_spray = abs(ball.spray_angle)
        self.league_stats = league_stats or {}
        
        base_fence = 122 - (abs_spray / 45.0) * (122 - 100)
        pf_hr = stadium.pf_hr if stadium else 1.0
        fence_dist = base_fence / math.sqrt(pf_hr) 
        
        if ball.hit_type == BattedBallType.FLYBALL and ball.distance > fence_dist and abs_spray < 45:
            return PlayResult.HOME_RUN
        
        target_pos = (ball.landing_x, ball.landing_y)
        best_fielder, fielder_type, initial_pos = self._find_nearest_fielder(target_pos, defense_team, team_level, current_pitcher)
        
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
            if ball.hit_type == BattedBallType.POPUP: return PlayResult.POPUP_OUT
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
        
        # ===== 捕球確率計算（BABIP .290-.310 目標） =====
        # 内野フライ(POPUP)は滞空時間が長くほぼ確実にアウト
        if ball.hit_type == BattedBallType.POPUP:
            catch_prob = 0.99  # 99% → 98%
        # 外野定位置のフライ（85-100m、移動距離少ない）
        elif ball.hit_type == BattedBallType.FLYBALL and 75 < ball.distance < 105 and dist_to_ball < 15:
            catch_prob = 0.97  # 97% → 93%
        # 外野定位置付近のフライ（移動距離中程度）
        elif ball.hit_type == BattedBallType.FLYBALL and dist_to_ball < 25:
            catch_prob = 0.92  # 92% → 88%
        else:
            # 通常の計算（タイム差に基づく）- BABIP向上のため調整
            if time_diff >= 1.0:
                catch_prob = 0.80  # 85% → 78%
            elif time_diff >= 0.5:
                catch_prob = 0.65 + (time_diff - 0.5) * 0.26  # 0.65-0.78
            elif time_diff >= 0.0:
                catch_prob = 0.45 + (time_diff / 0.5) * 0.20  # 0.45-0.65
            elif time_diff > -0.3:
                ratio = (time_diff + 0.3) / 0.3
                catch_prob = ratio * 0.35  # 0-0.35（難しい打球）
            elif time_diff > -0.6:
                ratio = (time_diff + 0.6) / 0.3
                catch_prob = ratio * 0.05  # 0-0.05（非常に難しい）
            else:
                catch_prob = 0.0  # 届かない
        
        # --- BABIP能力依存を最小化: 全員.300前後を目指す ---
        # ハードコンタクトのボーナスをほぼなくす
        if ball.contact_quality == "hard": 
            catch_prob *= 0.95  # 0.82 -> 0.92 (わずか8%減少のみ)
        
        # ライナーのボーナスも最小限に
        if ball.hit_type == BattedBallType.LINEDRIVE: 
            catch_prob *= 0.83  # 0.70 -> 0.80 (20%減少に縮小)
        
        # --- ソフトコンタクトのペナルティも最小限に ---
        if ball.contact_quality == "soft" and ball.hit_type in [BattedBallType.FLYBALL, BattedBallType.POPUP]:
            catch_prob = max(catch_prob, 0.72)  # 0.68 -> 0.72 (28%ヒット)
        
        # キャッチャー前のぼてぼてゴロも平均化
        if ball.hit_type == BattedBallType.GROUNDBALL and ball.distance < 15 and ball.contact_quality == "soft":
            catch_prob = 0.72  # 0.70 -> 0.72
        elif ball.hit_type == BattedBallType.GROUNDBALL and ball.distance < 25 and ball.contact_quality == "soft":
            catch_prob = 0.70  # 0.68 -> 0.70
        
        if stadium: catch_prob /= stadium.pf_1b
        return max(0.0, min(0.99, catch_prob))

    def _find_nearest_fielder(self, ball_pos, team, team_level, current_pitcher):
        min_dist = 999.0; best_f = None; best_type = ""; best_init = (0,0)
        lineup = team.current_lineup
        if team_level == TeamLevel.SECOND: lineup = team.farm_lineup
        elif team_level == TeamLevel.THIRD: lineup = team.third_lineup
        
        pos_map = {}
        for idx in lineup:
            if 0 <= idx < len(team.players):
                p = team.players[idx]
                if p.position != Position.DH and p.position != Position.PITCHER: pos_map[p.position] = p
        
        if current_pitcher:
             pos_map[Position.PITCHER] = current_pitcher

        for pos_enum, coords in FIELD_COORDS.items():
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

        # --- 修正: 内野安打の機会を増やす (マージン縮小) ---
        if throw_time < (runner_time + 0.2):  # 0.2 → 0.08秒に縮小
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
        
        # ----- スリーベース判定（非常に厳しい条件） -----
        # 条件: フェンス際(100m以上) + ライン際/ギャップ + 足が速い
        is_fence_area = dist > 100
        is_gap_or_line = abs_spray > 20
        is_fast_runner = speed_stat > 55
        
        if is_fence_area and is_gap_or_line and is_fast_runner:
            if margin_3b + random_factor > 1.5:
                return PlayResult.TRIPLE
            elif margin_3b + random_factor > 0.5:
                triple_prob = 0.15 + (margin_3b * 0.1)
                if random.random() < min(0.3, triple_prob):
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
            elif is_gap_or_line and ball.contact_quality == "hard":
                # ギャップ/ライン際の強い打球
                if margin_2b + random_factor > 0.3:
                    return PlayResult.DOUBLE
                elif margin_2b + random_factor > -0.5:
                    double_prob = 0.25 + (margin_2b * 0.15)
                    if random.random() < max(0.1, min(0.5, double_prob)):
                        return PlayResult.DOUBLE
        
        return PlayResult.SINGLE

    def _update_defensive_metrics(self, fielder, team_level, avg_catch_prob, is_caught, play_value):
        """UZR (RngR) の計算: 平均的な選手との差分を積み上げる"""
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
                rec.uzr_arm += val; rec.def_drs_raw += val
                return True # Out
            else:
                # 補殺失敗 (Safe)
                val = (0.0 - avg_kill_prob) * abs(run_val_safe) # マイナス
                val *= UZR_SCALE["ARM"]
                rec.uzr_arm += val; rec.def_drs_raw += val
                return False # Safe
        else:
            # ランナー自重 (Hold)
            # 肩が強いことによる抑止効果（本来走られる確率 - 実際に走られた確率）
            # 簡易的に、平均より肩が強ければプラスを与える
            avg_attempt_threshold = 0.3
            deterrence_val = (avg_attempt_threshold - attempt_threshold) * 0.5 # 係数は調整
            if deterrence_val > 0:
                 rec.uzr_arm += deterrence_val * UZR_SCALE["ARM"]
                 rec.def_drs_raw += deterrence_val * UZR_SCALE["ARM"]
            return False

class LiveGameEngine:
    def __init__(self, home: Team, away: Team, team_level: TeamLevel = TeamLevel.FIRST, league_stats: Dict[str, float] = None):
        self.home_team = home; self.away_team = away
        self.team_level = team_level; self.state = GameState()
        self.pitch_gen = PitchGenerator(); self.bat_gen = BattedBallGenerator()
        self.def_eng = AdvancedDefenseEngine(); self.ai = AIManager()
        self.game_stats = defaultdict(lambda: defaultdict(int))
        self.stadium = getattr(self.home_team, 'stadium', None)
        if not self.stadium: self.stadium = Stadium(name=f"{home.name} Stadium")
        self.league_stats = league_stats or {}
        
        # 新しい投手管理システム
        self.home_pitching_director = PitchingDirector(home)
        self.away_pitching_director = PitchingDirector(away)
        
        self._init_starters()
        self._ensure_valid_lineup(self.home_team); self._ensure_valid_lineup(self.away_team)

    def _ensure_valid_lineup(self, team: Team):
        if self.team_level == TeamLevel.SECOND: get_lineup = lambda: team.farm_lineup; set_lineup = lambda l: setattr(team, 'farm_lineup', l); get_roster = team.get_farm_roster_players
        elif self.team_level == TeamLevel.THIRD: get_lineup = lambda: team.third_lineup; set_lineup = lambda l: setattr(team, 'third_lineup', l); get_roster = team.get_third_roster_players
        else: get_lineup = lambda: team.current_lineup; set_lineup = lambda l: setattr(team, 'current_lineup', l); get_roster = team.get_active_roster_players

        def is_valid_player(p):
            if p.is_injured: return False
            if self.team_level == TeamLevel.FIRST and hasattr(p, 'days_until_promotion') and p.days_until_promotion > 0: return False
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
            if len(valid_candidates) < 9: valid_candidates = [p for p in team.players if is_valid_player(p)]
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

    def _init_starters(self):
        hp = self.home_team.get_today_starter() or self.home_team.players[0]
        ap = self.away_team.get_today_starter() or self.away_team.players[0]
        
        # Store initial starters for later reference (aptitude checks)
        self.home_start_p = hp
        self.away_start_p = ap

        try: self.state.home_pitcher_idx = self.home_team.players.index(hp)
        except: self.state.home_pitcher_idx = 0; hp = self.home_team.players[0]
        try: self.state.away_pitcher_idx = self.away_team.players.index(ap)
        except: self.state.away_pitcher_idx = 0; ap = self.away_team.players[0]
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
        if not lineup: return team.players[0], 0
        return team.players[lineup[order_idx % len(lineup)]], order_idx

    def get_current_pitcher(self) -> Tuple[Player, int]:
        team = self.home_team if self.state.is_top else self.away_team
        idx = self.state.home_pitcher_idx if self.state.is_top else self.state.away_pitcher_idx
        return team.players[idx], idx

    def change_pitcher(self, new_pitcher: Player):
        team = self.home_team if self.state.is_top else self.away_team
        
        # 点差記録 (ホールド判定用)
        # 登板時点でのリード状況: (自チーム得点 - 相手チーム得点)
        score_diff = self.state.away_score - self.state.home_score if self.state.is_top else self.state.home_score - self.state.away_score
        self.game_stats[new_pitcher]['entry_score_diff'] = score_diff

        try:
            new_idx = team.players.index(new_pitcher)
            if self.state.is_top:
                self.state.home_pitcher_idx = new_idx; self.state.home_pitchers_used.append(new_pitcher)
                self.state.home_pitcher_stamina = new_pitcher.stats.stamina * 2.0 * (new_pitcher.current_stamina / 100.0)
                self.state.home_pitch_count = 0
                self.state.home_current_pitcher_runs = 0
            else:
                self.state.away_pitcher_idx = new_idx; self.state.away_pitchers_used.append(new_pitcher)
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
        for p_idx in lineup:
            if team.players[p_idx].position == Position.CATCHER: return team.players[p_idx]
        return None

    def _check_injury_occurrence(self, player: Player, action_type: str):
        if hasattr(player, 'is_injured') and player.is_injured: return 
        durability = getattr(player.stats, 'durability', 50)
        fatigue_factor = 1.0
        if player.position == Position.PITCHER and player.stats.stamina < 30: fatigue_factor = 3.0
        base_rate = 0.00005  # Reduced from 0.0005
        rate = base_rate * (100 - durability) / 50.0 * fatigue_factor
        if random.random() < rate:
            days = random.randint(3, 30) 
            name = f"患部の{random.choice(['違和感', '捻挫', '肉離れ', '炎症'])}"
            if hasattr(player, 'inflict_injury'): player.inflict_injury(days, name)
            return True
        return False

    def simulate_pitch(self, manual_strategy=None, shifts=None):
        if shifts:
            self.state.infield_shift = shifts.get('infield', "内野通常")
            self.state.outfield_shift = shifts.get('outfield', "外野通常")

        batter, _ = self.get_current_batter()
        pitcher, _ = self.get_current_pitcher()
        defense_team = self.home_team if self.state.is_top else self.away_team
        
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
        
        new_pitcher = pitching_director.check_pitcher_change(ctx, pitcher, used_pitchers, batter)
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
        catcher_arm = get_effective_stat(catcher, 'arm') if catcher else 50
        
        # 三盗は二盗より成功率が低い（距離が近く守備に有利）
        if steal_type == "3B":
            success_prob = 0.60 + (runner_spd - 50)*0.01 - (catcher_arm - 50)*0.012
        else:
            success_prob = 0.70 + (runner_spd - 50)*0.01 - (catcher_arm - 50)*0.01
        
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
            # ★修正: judgeに現在の投手を渡す
            play = self.def_eng.judge(ball, defense_team, self.team_level, self.stadium, current_pitcher=pitcher, league_stats=self.league_stats, batter=batter)
            
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
        defense_team = self.home_team if self.state.is_top else self.away_team
        for pid in defense_team.current_lineup:
            if 0 <= pid < len(defense_team.players) and defense_team.players[pid].position != Position.DH:
                self.game_stats[defense_team.players[pid]]['defensive_innings'] += (1.0 / 3.0)
        
        batter, _ = self.get_current_batter()
        self._record_pf(batter, pitcher)
        self._reset_count(); self._next_batter()
        if self.state.outs >= 3: self._change_inning()

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
            if random.random() < 0.85: 
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
        if self.state.outs >= 3: self._change_inning()
        return play

    def _advance_runners_bunt(self) -> int:
        score = 0
        if self.state.runner_3b: score += 1; self.state.runner_3b = None
        if self.state.runner_2b: self.state.runner_3b = self.state.runner_2b; self.state.runner_2b = None
        if self.state.runner_1b: self.state.runner_2b = self.state.runner_1b; self.state.runner_1b = None
        return score

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
    
    def _score(self, pts):
        if self.state.is_top: self.state.away_score += pts
        else: self.state.home_score += pts

    def _reset_count(self): self.state.balls = 0; self.state.strikes = 0

    def _next_batter(self):
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
        if self.state.inning >= 9 and not self.state.is_top and self.state.home_score > self.state.away_score: return True
        if self.state.inning >= 13: return True
        if self.state.inning >= 10 and self.state.is_top:
            if self.state.home_score != self.state.away_score: return True
        return False

    def finalize_game_stats(self, date_str: str = "2027-01-01"):
        win_p, loss_p, save_p, hold_ps = None, None, None, []
        if not self.state.home_pitchers_used or not self.state.away_pitchers_used: return

        home_win = self.state.home_score > self.state.away_score
        away_win = self.state.away_score > self.state.home_score
        
        if home_win:
            win_team_pitchers = self.state.home_pitchers_used
            loss_team_pitchers = self.state.away_pitchers_used
            starter = win_team_pitchers[0]
            if self.game_stats[starter]['innings_pitched'] >= 5: win_p = starter
            else:
                if len(win_team_pitchers) > 1: win_p = win_team_pitchers[1]
                else: win_p = starter
            loss_p = loss_team_pitchers[0]
        elif away_win:
            win_team_pitchers = self.state.away_pitchers_used
            loss_team_pitchers = self.state.home_pitchers_used
            starter = win_team_pitchers[0]
            if self.game_stats[starter]['innings_pitched'] >= 5: win_p = starter
            else:
                if len(win_team_pitchers) > 1: win_p = win_team_pitchers[1]
                else: win_p = starter
            loss_p = loss_team_pitchers[0]

        if win_p:
            win_team = self.home_team if home_win else self.away_team
            last_pitcher = self.state.home_pitchers_used[-1] if home_win else self.state.away_pitchers_used[-1]
            
            # --- セーブ判定 ---
            if last_pitcher != win_p:
                score_diff = abs(self.state.home_score - self.state.away_score)
                # 3点差以内かつ1イニング以上 OR 3イニング以上
                is_save_situation = (score_diff <= 3 and self.game_stats[last_pitcher]['innings_pitched'] >= 0.99) or \
                                    (self.game_stats[last_pitcher]['innings_pitched'] >= 3.0)
                if is_save_situation:
                    save_p = last_pitcher

            # --- ホールド判定 ---
            # 勝利チームの中継ぎ投手で、勝利・敗戦・セーブがつかない場合
            # 条件: 
            # 1. リード時または同点で登板
            # 2. 1アウト以上取得
            # 3. 降板時にリードまたは同点を維持 (かつ登板時より悪化していない?) -> NPB規定に準拠
            # 簡易判定: 
            # - リード時登板(点差<=3) -> リード維持で降板
            # - 同点時登板 -> 失点せず降板(同点維持 or 勝ち越し) -> 勝ち越しなら勝利投手の可能性
            
            check_pitchers = win_team_pitchers if home_win else self.state.away_pitchers_used # win_team_pitchers is safe? No, define above
            if home_win: check_pitchers = self.state.home_pitchers_used
            elif away_win: check_pitchers = self.state.away_pitchers_used
            else: check_pitchers = self.state.home_pitchers_used + self.state.away_pitchers_used # Draw

            for p in check_pitchers:
                if p == win_p or p == loss_p or p == save_p: continue
                if self.game_stats[p]['innings_pitched'] < 0.1: continue # 0/3回 = 0アウトならホールドつかない
                
                entry_diff = self.game_stats[p].get('entry_score_diff', -999)
                if entry_diff == -999: continue # 先発などは記録ないかも
                
                # 登板時条件: リード(3点以内) or 同点
                # entry_diffは「自チームリード」が正
                
                # NPBホールド条件簡略化:
                # 1. 登板時リード保って降板 (登板時リード <= 3点)
                # 2. 同点時登板で、失点せず降板 (勝ち越し時は勝利投手になるのでここは対象外)
                
                if 0 < entry_diff <= 3:
                    # リード時登板: 最終的にチームが勝っているので、恐らくリード維持した?
                    # 厳密には「降板時にリードしていたか」が必要だが、記録していない。
                    # しかし「勝利チームの中継ぎ」なら、逆転されずに勝った可能性が高い。
                    # 簡易的に、この条件を満たす中継ぎにはホールドをつける
                    hold_ps.append(p)
                elif entry_diff == 0:
                    # 同点時登板: 失点していなければ貢献
                    if self.game_stats[p]['runs_allowed'] == 0:
                        hold_ps.append(p)

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
        for player, stats in self.game_stats.items():
            record = player.get_record_by_level(self.team_level)
            for key, val in stats.items():
                if hasattr(record, key):
                    current = getattr(record, key)
                    setattr(record, key, current + val)
            record.games += 1
            
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
                    player.add_game_fatigue(at_bats=at_bats, defensive_innings=defensive_innings)
            
        # Highlight Analysis
        highlights = self._analyze_highlights(win_p, loss_p, save_p, home_win, away_win)

        return {
            "win": win_p,
            "loss": loss_p,
            "save": save_p,
            "game_stats": self.game_stats,
            "highlights": highlights
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