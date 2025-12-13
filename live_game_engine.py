# -*- coding: utf-8 -*-
"""
ライブ試合エンジン (修正版: 投手守備参加修正・フリーズ対策・ポテンヒット抑制)
"""
import random
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict
from enum import Enum
from models import Position, Player, Team, PlayerRecord, PitchType, TeamLevel, generate_best_lineup, Stadium

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
    "DP": -0.80
}

UZR_SCALE = {
    "RngR": 0.50,
    "ErrR": 0.50,
    "ARM": 0.25,
    "DPR": 0.25,
    "rSB": 0.15,
    "rBlk": 0.50
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

def get_effective_stat(player: Player, stat_name: str, opponent: Optional[Player] = None, is_risp: bool = False, is_close_game: bool = False) -> float:
    if not hasattr(player.stats, stat_name):
        return 50.0

    if hasattr(player, 'is_injured') and player.is_injured:
        return getattr(player.stats, stat_name) * 0.5

    base_value = getattr(player.stats, stat_name)
    condition_diff = player.condition - 5
    condition_multiplier = 1.0 + (condition_diff * 0.015)
    
    value = base_value * condition_multiplier
    
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
    else:
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
    home_pitch_count: int = 0; away_pitch_count: int = 0
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
    def check_pitcher_change(self, state: GameState, team: Team, opponent: Team, next_batter: Player, current_pitcher: Player) -> Optional[Player]:
        is_starter = current_pitcher in [team.players[i] for i in team.rotation if 0 <= i < len(team.players)]
        current_stamina = state.home_pitcher_stamina if not state.is_top else state.away_pitcher_stamina
        current_runs = state.home_current_pitcher_runs if not state.is_top else state.away_current_pitcher_runs
        pitch_count = state.home_pitch_count if not state.is_top else state.away_pitch_count
        
        score_diff = state.home_score - state.away_score
        if state.is_top: score_diff *= -1 
        
        if current_stamina <= 0 or pitch_count > 140:
            return self._select_reliever(team, state, score_diff, next_batter)
            
        if is_starter:
            if current_runs >= 6 and state.inning <= 6:
                return self._select_reliever(team, state, score_diff, next_batter)
            if pitch_count > 120:
                if score_diff > 0 and state.outs == 2 and pitch_count < 130: pass
                else: return self._select_reliever(team, state, score_diff, next_batter)
            if state.inning == 5 and score_diff > 0 and current_stamina > 10 and current_runs < 5:
                return None 
            if state.inning >= 7:
                if pitch_count > 110 or current_stamina < 15:
                     if score_diff >= -2: return self._select_reliever(team, state, score_diff, next_batter)
            if state.inning >= 7 and state.is_risp() and score_diff in range(-1, 2):
                if current_stamina > 20: pass
                else: return self._select_reliever(team, state, score_diff, next_batter)
        else:
            if state.outs == 0 and pitch_count > 25: 
                is_closer = team.closer_idx != -1 and team.players[team.closer_idx] == current_pitcher
                if not is_closer: return self._select_reliever(team, state, score_diff, next_batter)
            if current_runs >= 3: return self._select_reliever(team, state, score_diff, next_batter)
            if current_stamina < 5: return self._select_reliever(team, state, score_diff, next_batter)
        
        if score_diff > 0 and score_diff <= 3:
            if state.inning == 9: 
                closer = team.get_closer()
                if closer and closer != current_pitcher and not closer.is_injured: return closer
            elif state.inning == 8: 
                setup = team.get_setup_pitcher()
                if setup and setup != current_pitcher and not setup.is_injured:
                    if is_starter and current_stamina > 30 and pitch_count < 110: pass
                    else: return setup
        return None

    def _select_reliever(self, team: Team, state: GameState, score_diff: int, next_batter: Player) -> Optional[Player]:
        used_pitchers = state.home_pitchers_used if not state.is_top else state.away_pitchers_used
        available_pitchers = []
        rotation_players = [team.players[i] for i in team.rotation if 0 <= i < len(team.players)]
        
        for p_idx in team.active_roster:
            if 0 <= p_idx < len(team.players):
                p = team.players[p_idx]
                if p.position == Position.PITCHER and p not in used_pitchers and p not in rotation_players and not p.is_injured:
                    available_pitchers.append(p)
        
        if not available_pitchers: return None

        if state.inning >= 9 and (0 < score_diff <= 3 or (score_diff == 0 and not state.is_top)):
            closer = team.get_closer()
            if closer and closer in available_pitchers: return closer

        if state.inning >= 8 and (0 <= score_diff <= 3):
            setup = team.get_setup_pitcher()
            if setup and setup in available_pitchers: return setup

        if abs(score_diff) <= 3:
            if next_batter.bats == "左":
                lefties = [p for p in available_pitchers if p.throws == "左"]
                lefties.sort(key=lambda x: x.stats.overall_pitching(), reverse=True)
                if lefties: return lefties[0]
            best_reliever = max(available_pitchers, key=lambda p: p.stats.overall_pitching())
            return best_reliever

        available_pitchers.sort(key=lambda p: p.stats.overall_pitching())
        return available_pitchers[0]

    def _find_lefty_specialist(self, team: Team, current_pitcher: Player) -> Optional[Player]:
        return None 

class AIManager:
    def __init__(self):
        self.pitcher_manager = NPBPitcherManager()

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
        
        if state.runner_1b and not state.runner_2b and not state.runner_3b and state.outs < 2:
            runner_spd = get_effective_stat(state.runner_1b, 'speed')
            runner_stl = get_effective_stat(state.runner_1b, 'steal')
            attempt_prob = 0.02 + (runner_spd - 50) * 0.003
            attempt_prob *= (0.7 + (runner_stl / 50.0) * 0.5)
            if is_close and is_late: attempt_prob *= 0.5 
            elif abs(score_diff) >= 4: attempt_prob *= 1.2 
            if random.random() < max(0.005, attempt_prob): return "STEAL"
        
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

class PitchGenerator:
    PITCH_DATA = {
        "ストレート":     {"base_speed": 148, "h_break": 0,   "v_break": 10,  "spin_ratio": 1.0},
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

    def generate_pitch(self, pitcher: Player, batter: Player, catcher: Player, state: GameState, strategy="NORMAL", stadium: Stadium = None) -> PitchData:
        is_risp = state.is_risp()
        is_close = abs(state.home_score - state.away_score) <= 2
        
        velocity = get_effective_stat(pitcher, 'velocity', batter, is_risp, is_close)
        control = get_effective_stat(pitcher, 'control', batter, is_risp, is_close)
        
        if stadium: control = control / max(0.5, stadium.pf_bb)
        if catcher:
            lead = get_effective_stat(catcher, 'catcher_lead', is_close_game=is_close)
            control += (lead - 50) * 0.2
        
        current_stamina = state.current_pitcher_stamina()
        fatigue = 1.0
        if current_stamina < 30: fatigue = 0.9 + (current_stamina / 300.0)
        if current_stamina <= 0: fatigue = 0.8
        
        pitch_cost = 0.5
        if is_risp: pitch_cost *= 1.2
        if state.is_top: state.home_pitcher_stamina = max(0, state.home_pitcher_stamina - pitch_cost)
        else: state.away_pitcher_stamina = max(0, state.away_pitcher_stamina - pitch_cost)
        
        base_straight_prob = 0.35 + (velocity - 130) * 0.01
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
            speed_ratio = base["base_speed"] / 148.0
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
    def generate(self, batter: Player, pitcher: Player, pitch: PitchData, state: GameState, strategy="SWING"):
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
        con_eff = contact + meet_bonus - (p_move - 50) * 0.25 - ball_penalty
        
        power_bonus_factor = (power - 50) * 0.1
        hard_chance = max(1.0, (con_eff * 0.5) + power_bonus_factor)
        medium_limit = max(hard_chance + 10, con_eff * 0.85)
        
        quality_roll = random.uniform(0, 100)
        quality = "hard" if quality_roll < hard_chance else ("medium" if quality_roll < medium_limit else "soft")
        
        base_v = 145 + (power - 50) * 0.18
        if strategy == "POWER": base_v += 8
        if quality == "hard": base_v += 18 + (power / 12) 
        if quality == "soft": base_v -= 35 
        
        traj_bias = 5 + (trajectory * 5)
        angle_center = traj_bias - (p_gb_tendency - 50) * 0.2
        angle_center -= 3.0
        
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
            angle = random.gauss(angle_center, 12)
        
        velo = max(40, base_v + random.gauss(0, 5))
        if quality == "hard": velo = max(velo, 138)
        
        gb_limit = 16 + (140 - velo) * 0.08
        ld_limit = 22 - (140 - velo) * 0.05
        
        if angle < gb_limit: htype = BattedBallType.GROUNDBALL
        elif angle < ld_limit: htype = BattedBallType.LINEDRIVE
        elif angle < 50: htype = BattedBallType.FLYBALL
        else: htype = BattedBallType.POPUP
        
        v_ms = velo / 3.6
        vacuum_dist = (v_ms**2 * math.sin(math.radians(2 * angle))) / 9.8
        
        drag_base = 0.92 - (velo / 550.0) 
        drag_factor = max(0.2, drag_base)
        
        if angle > 45 or angle < 10: drag_factor *= 0.75 
        elif angle >= 20 and angle <= 45: 
             if velo > 150: drag_factor *= 0.85
             else: drag_factor *= 0.88 
             
        dist = max(0, vacuum_dist * drag_factor)
        
        if htype == BattedBallType.GROUNDBALL: dist *= 0.5
        elif htype == BattedBallType.POPUP: dist *= 0.3
        
        spray = random.gauss(0, 25)
        rad = math.radians(spray)
        land_x = dist * math.sin(rad)
        land_y = dist * math.cos(rad)
        
        v_y = v_ms * math.sin(math.radians(angle))
        hang_time = (2 * v_y) / 9.8
        if htype == BattedBallType.GROUNDBALL:
            hang_time = dist / (v_ms * 0.8)
        
        return BattedBallData(velo, angle, spray, htype, dist, hang_time, land_x, land_y, [], quality)

class AdvancedDefenseEngine:
    def judge(self, ball: BattedBallData, defense_team: Team, team_level: TeamLevel = TeamLevel.FIRST, stadium: Stadium = None, current_pitcher: Player = None):
        abs_spray = abs(ball.spray_angle)
        
        base_fence = 122 - (abs_spray / 45.0) * (122 - 100)
        pf_hr = stadium.pf_hr if stadium else 1.0
        fence_dist = base_fence / math.sqrt(pf_hr) 
        
        if ball.hit_type == BattedBallType.FLYBALL and ball.distance > fence_dist and abs_spray < 45:
            return PlayResult.HOME_RUN
        
        # 守備判定
        target_pos = (ball.landing_x, ball.landing_y)
        # ★修正: 現在の投手を渡す
        best_fielder, fielder_type, initial_pos = self._find_nearest_fielder(target_pos, defense_team, team_level, current_pitcher)
        
        if not best_fielder: 
            if abs_spray > 45: return PlayResult.FOUL
            return PlayResult.SINGLE 

        dist_to_ball = math.sqrt((target_pos[0] - initial_pos[0])**2 + (target_pos[1] - initial_pos[1])**2)
        
        range_stat = best_fielder.stats.get_defense_range(getattr(Position, fielder_type))
        adjusted_range = 50 + (range_stat - 50) * 0.1 
        adjusted_range = adjusted_range * (1.0 + (best_fielder.condition - 5) * 0.005)

        speed_stat = get_effective_stat(best_fielder, 'speed')
        max_speed = 7.8 + (speed_stat - 50) * 0.01
        
        reaction_delay = 0.45 - (adjusted_range / 1500.0) 
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
        catch_prob = 0.0
        
        if time_diff >= 0.5: catch_prob = 0.90 
        elif time_diff >= 0.0: catch_prob = 0.65 + (time_diff / 0.5) * 0.29
        elif time_diff > -0.3:
             ratio = (time_diff + 0.3) / 0.3
             catch_prob = ratio * 0.63
        else: catch_prob = 0.0
        
        luck_factor = 0.50; base_prob = 0.25
        if catch_prob > 0.89: luck_factor = 0.05 
        catch_prob = catch_prob * (1 - luck_factor) + base_prob * luck_factor
        
        if ball.contact_quality == "hard": catch_prob *= 0.85 
        if ball.hit_type == BattedBallType.LINEDRIVE: catch_prob *= 0.80
        
        if ball.contact_quality == "soft" and ball.hit_type in [BattedBallType.FLYBALL, BattedBallType.LINEDRIVE]:
            catch_prob = 0.5 + (catch_prob * 0.5) 

        if stadium: catch_prob /= stadium.pf_1b
        catch_prob = max(0.0, min(0.99, catch_prob))
        
        is_caught = random.random() < catch_prob
        
        if abs_spray > 45:
            if is_caught and ball.hit_type in [BattedBallType.FLYBALL, BattedBallType.POPUP]: return PlayResult.FLYOUT
            else: return PlayResult.FOUL

        potential_hit_result = self._judge_hit_type_potential(ball, target_pos, stadium)
        play_value = 0 
        
        if best_fielder.position != Position.CATCHER:
            self._update_defensive_metrics(best_fielder, team_level, catch_prob, is_caught, play_value)

        if is_caught:
            rec = best_fielder.get_record_by_level(team_level)
            pos_err_rate = 0.015 if best_fielder.position in [Position.FIRST, Position.LEFT, Position.RIGHT] else 0.025
            error_rating = get_effective_stat(best_fielder, 'error')
            error_prob = max(0.001, (pos_err_rate * 2.0) - (error_rating * 0.0005))
            
            if random.random() < error_prob:
                rec.uzr_errr -= (RUN_VALUES["Error"] * UZR_SCALE["ErrR"])
                rec.def_drs_raw -= (RUN_VALUES["Error"] * UZR_SCALE["ErrR"])
                return PlayResult.ERROR
            
            if ball.hit_type == BattedBallType.FLYBALL: return PlayResult.FLYOUT
            if ball.hit_type == BattedBallType.POPUP: return PlayResult.POPUP_OUT
            if ball.hit_type == BattedBallType.LINEDRIVE: return PlayResult.LINEOUT
            
            return self._judge_grounder_throw(best_fielder, ball, team_level)
        else:
            return potential_hit_result

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
        
        # ★修正: 現在の投手を守備位置にセット (先発投手インデックスは使わない)
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
        throw_speed = 30 + (arm / 100.0) * 15
        transfer_time = 0.8 - (get_effective_stat(fielder, 'error') / 200.0)
        throw_time = transfer_time + (dist_to_1b / throw_speed)
        
        throw_time *= 0.95
        runner_time = 4.1 
        time_margin = runner_time - throw_time
        rec = fielder.get_record_by_level(team_level)
        
        if throw_time < runner_time:
            if 0 < time_margin < 0.3:
                 val = 0.2 * UZR_SCALE["ARM"]
                 rec.def_drs_raw += val; rec.uzr_arm += val
            return PlayResult.GROUNDOUT
        else:
            if -0.3 < time_margin < 0:
                 val = -0.1 * UZR_SCALE["ARM"]
                 rec.def_drs_raw += val; rec.uzr_arm += val
            return PlayResult.SINGLE 

    def _judge_hit_type_potential(self, ball, ball_pos, stadium):
        abs_spray = abs(ball.spray_angle)
        if ball.contact_quality == "soft":
            if abs_spray < 35: return PlayResult.SINGLE

        dist = ball.distance
        pf_2b = stadium.pf_2b if stadium else 1.0
        pf_3b = stadium.pf_3b if stadium else 1.0
        
        base_double_threshold = 78.0 
        double_threshold = base_double_threshold / math.sqrt(pf_2b)
        triple_threshold = 105.0 / math.sqrt(pf_3b)
        
        is_behind_fielder = ball_pos[1] > 80 
        
        if dist > triple_threshold and is_behind_fielder:
             if random.random() < 0.3: return PlayResult.TRIPLE
             return PlayResult.DOUBLE
        
        if dist > double_threshold:
            is_down_the_line = abs_spray > 25
            is_gap = 15 < abs_spray < 35
            
            if ball.hit_type == BattedBallType.LINEDRIVE:
                if is_down_the_line or is_gap: return PlayResult.DOUBLE
                if dist > 85: return PlayResult.DOUBLE 
                
            if is_behind_fielder:
                 return PlayResult.DOUBLE
        
        return PlayResult.SINGLE

    def _update_defensive_metrics(self, fielder, team_level, catch_prob, is_caught, play_value):
        rec = fielder.get_record_by_level(team_level)
        rec.def_opportunities += 1
        rec.def_difficulty_sum += (1.0 - catch_prob)
        rng_r = 0.0
        if is_caught:
            rng_r = (1.0 - catch_prob) * play_value
            rec.def_plays_made += 1
        else:
            rng_r = (0.0 - catch_prob) * play_value
        rng_r *= UZR_SCALE["RngR"]
        rec.def_drs_raw += rng_r; rec.uzr_rngr += rng_r

    def judge_arm_opportunity(self, ball: BattedBallData, fielder: Player, runner: Player, base_from: int, team_level):
        arm = get_effective_stat(fielder, 'arm')
        runner_speed = get_effective_stat(runner, 'speed')
        kill_prob = 0.3 + (arm - 50) * 0.01 - (runner_speed - 50) * 0.01
        kill_prob = max(0.05, min(0.8, kill_prob))
        rec = fielder.get_record_by_level(team_level)
        if random.random() < 0.3: 
            if random.random() < kill_prob:
                val = 0.8 * UZR_SCALE["ARM"]; rec.uzr_arm += val; rec.def_drs_raw += val
                return True
            else:
                val = -0.4 * UZR_SCALE["ARM"]; rec.uzr_arm += val; rec.def_drs_raw += val
                return False
        else:
            hold_bonus = 0.02 * (arm / 100.0) * UZR_SCALE["ARM"]
            rec.uzr_arm += hold_bonus; rec.def_drs_raw += hold_bonus
            return False

class LiveGameEngine:
    def __init__(self, home: Team, away: Team, team_level: TeamLevel = TeamLevel.FIRST):
        self.home_team = home; self.away_team = away
        self.team_level = team_level; self.state = GameState()
        self.pitch_gen = PitchGenerator(); self.bat_gen = BattedBallGenerator()
        self.def_eng = AdvancedDefenseEngine(); self.ai = AIManager()
        self.game_stats = defaultdict(lambda: defaultdict(int))
        self.stadium = getattr(self.home_team, 'stadium', None)
        if not self.stadium: self.stadium = Stadium(name=f"{home.name} Stadium")
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
        try: self.state.home_pitcher_idx = self.home_team.players.index(hp)
        except: self.state.home_pitcher_idx = 0; hp = self.home_team.players[0]
        try: self.state.away_pitcher_idx = self.away_team.players.index(ap)
        except: self.state.away_pitcher_idx = 0; ap = self.away_team.players[0]
        self.state.home_pitchers_used.append(hp); self.state.away_pitchers_used.append(ap)
        self.game_stats[hp]['games_pitched'] = 1; self.game_stats[ap]['games_pitched'] = 1
        self.game_stats[hp]['games_started'] = 1; self.game_stats[ap]['games_started'] = 1

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
        try:
            new_idx = team.players.index(new_pitcher)
            if self.state.is_top:
                self.state.home_pitcher_idx = new_idx; self.state.home_pitchers_used.append(new_pitcher)
                self.state.home_pitcher_stamina = new_pitcher.stats.stamina; self.state.home_pitch_count = 0
                self.state.home_current_pitcher_runs = 0
            else:
                self.state.away_pitcher_idx = new_idx; self.state.away_pitchers_used.append(new_pitcher)
                self.state.away_pitcher_stamina = new_pitcher.stats.stamina; self.state.away_pitch_count = 0
                self.state.away_current_pitcher_runs = 0
            self.game_stats[new_pitcher]['games_pitched'] = 1
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
        base_rate = 0.0005
        rate = base_rate * (100 - durability) / 50.0 * fatigue_factor
        if random.random() < rate:
            days = random.randint(3, 30) 
            name = f"患部の{random.choice(['違和感', '捻挫', '肉離れ', '炎症'])}"
            if hasattr(player, 'inflict_injury'): player.inflict_injury(days, name)
            return True
        return False

    def simulate_pitch(self, manual_strategy=None):
        batter, _ = self.get_current_batter()
        pitcher, _ = self.get_current_pitcher()
        defense_team = self.home_team if self.state.is_top else self.away_team
        
        new_pitcher = self.ai.pitcher_manager.check_pitcher_change(self.state, defense_team, self.away_team if self.state.is_top else self.home_team, batter, pitcher)
        if new_pitcher:
            self.change_pitcher(new_pitcher); pitcher = new_pitcher
            
        catcher = self.get_current_catcher()
        offense_team = self.away_team if self.state.is_top else self.home_team
        strategy = manual_strategy or self.ai.decide_strategy(self.state, offense_team, defense_team, batter)
        pitch_strategy = self.ai.decide_pitch_strategy(self.state, pitcher, batter)
        
        if strategy == "STEAL":
            res = self._attempt_steal(catcher)
            if res: return PitchResult.BALL, None, None

        pitch = self.pitch_gen.generate_pitch(pitcher, batter, catcher, self.state, pitch_strategy, self.stadium)
        if self.state.is_top: self.state.home_pitch_count += 1
        else: self.state.away_pitch_count += 1
        self._check_injury_occurrence(pitcher, "PITCH")
        
        res, ball = self._resolve_contact(batter, pitcher, pitch, strategy)
        final_res = self.process_pitch_result(res, pitch, ball, strategy)
        return final_res, pitch, ball

    def _resolve_contact(self, batter, pitcher, pitch, strategy):
        if not pitch.location.is_strike:
            control = get_effective_stat(pitcher, 'control')
            if random.random() < (0.002 + max(0, (50-control)*0.0002)): return PitchResult.HIT_BY_PITCH, None

        if strategy == "BUNT":
            bunt_skill = get_effective_stat(batter, 'bunt_sac')
            difficulty = 20 if not pitch.location.is_strike else 0
            if random.uniform(0, 100) > (bunt_skill - difficulty):
                return PitchResult.FOUL if random.random() < 0.8 else PitchResult.STRIKE_SWINGING, None
            else:
                ball = self.bat_gen.generate(batter, pitcher, pitch, self.state, strategy)
                return PitchResult.IN_PLAY, ball

        eye = get_effective_stat(batter, 'eye')
        dist_from_center = math.sqrt(pitch.location.x**2 + (pitch.location.z - 0.75)**2)
        is_obvious_ball = dist_from_center > 0.45 
        
        if pitch.location.is_strike:
            swing_prob = 0.78 + (eye-50)*0.001
        else:
            if is_obvious_ball: swing_prob = 0.005 
            else: swing_prob = 0.30 - (eye-50)*0.004 

        if self.state.strikes == 2: swing_prob += 0.18
        if strategy == "POWER": swing_prob += 0.1 
        if strategy == "MEET": swing_prob -= 0.1
        swing_prob = max(0.001, min(0.99, swing_prob))
        
        if random.random() >= swing_prob: return PitchResult.STRIKE_CALLED if pitch.location.is_strike else PitchResult.BALL, None
            
        contact = get_effective_stat(batter, 'contact', opponent=pitcher)
        stuff = pitcher.stats.get_pitch_stuff(pitch.pitch_type)
        base_contact = 0.63
        hit_prob = base_contact + ((contact - stuff) * 0.0035)
        
        if pitch.location.is_strike: hit_prob += 0.08
        else: hit_prob -= 0.12
        if self.stadium: hit_prob /= max(0.5, self.stadium.pf_so)
        hit_prob = max(0.40, min(0.88, hit_prob))

        if self.state.strikes == 2:
            avoid_k = get_effective_stat(batter, 'avoid_k')
            hit_prob += (avoid_k - 50) * 0.002

        if random.random() > hit_prob: 
             self._check_injury_occurrence(batter, "SWING")
             return PitchResult.STRIKE_SWINGING, None
             
        if random.random() < 0.32: return PitchResult.FOUL, None
             
        ball = self.bat_gen.generate(batter, pitcher, pitch, self.state, strategy)
        self._check_injury_occurrence(batter, "RUN")
        return PitchResult.IN_PLAY, ball

    def _attempt_steal(self, catcher):
        runner = self.state.runner_1b
        if not runner: return False
        runner_spd = get_effective_stat(runner, 'speed')
        catcher_arm = get_effective_stat(catcher, 'arm') if catcher else 50
        success_prob = 0.70 + (runner_spd - 50)*0.01 - (catcher_arm - 50)*0.01
        self._check_injury_occurrence(runner, "RUN")
        if random.random() < success_prob:
            self.state.runner_2b = runner; self.state.runner_1b = None
            self.game_stats[runner]['stolen_bases'] += 1
            if catcher: self.game_stats[catcher]['uzr_rsb'] -= (0.15 * UZR_SCALE["rSB"])
            return True
        else:
            self.state.runner_1b = None; self.state.outs += 1
            self.game_stats[runner]['caught_stealing'] += 1
            if catcher: self.game_stats[catcher]['uzr_rsb'] += (0.45 * UZR_SCALE["rSB"])
            return True

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
                self._out() 
        elif res == PitchResult.FOUL:
            if self.state.strikes < 2: self.state.strikes += 1
        elif res == PitchResult.IN_PLAY:
            defense_team = self.home_team if self.state.is_top else self.away_team
            # ★修正: judgeに現在の投手を渡す
            play = self.def_eng.judge(ball, defense_team, self.team_level, self.stadium, current_pitcher=pitcher)
            
            if ball.contact_quality == "hard": self.game_stats[batter]['hard_hit_balls'] += 1; self.game_stats[pitcher]['hard_hit_balls'] += 1
            elif ball.contact_quality == "medium": self.game_stats[batter]['medium_hit_balls'] += 1; self.game_stats[pitcher]['medium_hit_balls'] += 1
            else: self.game_stats[batter]['soft_hit_balls'] += 1; self.game_stats[pitcher]['soft_hit_balls'] += 1
            
            batter_hand = getattr(batter, 'bats', "右")
            if batter_hand == "両": batter_hand = "左" if getattr(pitcher, 'throws', "右") == "右" else "右"
            angle = ball.spray_angle
            if abs(angle) <= 15: self.game_stats[batter]['center_balls'] += 1
            elif (batter_hand == "右" and angle < -15) or (batter_hand == "左" and angle > 15): self.game_stats[batter]['pull_balls'] += 1
            else: self.game_stats[batter]['oppo_balls'] += 1

            if ball.hit_type == BattedBallType.GROUNDBALL: self.game_stats[pitcher]['ground_balls'] += 1; self.game_stats[batter]['ground_balls'] += 1
            elif ball.hit_type == BattedBallType.FLYBALL: self.game_stats[pitcher]['fly_balls'] += 1; self.game_stats[batter]['fly_balls'] += 1
            elif ball.hit_type == BattedBallType.LINEDRIVE: self.game_stats[pitcher]['line_drives'] += 1; self.game_stats[batter]['line_drives'] += 1
            else: self.game_stats[pitcher]['popups'] += 1; self.game_stats[batter]['popups'] += 1
            
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
        self.game_stats[batter]['plate_appearances'] += 1
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
        self.game_stats[batter]['plate_appearances'] += 1
        scored_players = []
        
        if play in [PlayResult.SINGLE, PlayResult.DOUBLE, PlayResult.TRIPLE, PlayResult.HOME_RUN]:
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
            dp_prob = 0.4 + (dp_skill - 50) * 0.01; dp_prob = max(0.1, min(0.9, dp_prob))
            if random.random() < dp_prob:
                is_double_play = True
                dpr_val = 0.32 * UZR_SCALE["DPR"] 
                for pid in defense_team.current_lineup:
                    p = defense_team.players[pid]
                    if p.position in [Position.SECOND, Position.SHORTSTOP]: self.game_stats[p]['uzr_dpr'] += (dpr_val / 2)
                self.state.runner_1b = None
            else:
                dpr_val = -0.48 * UZR_SCALE["DPR"]
                for pid in defense_team.current_lineup:
                    p = defense_team.players[pid]
                    if p.position in [Position.SECOND, Position.SHORTSTOP]: self.game_stats[p]['uzr_dpr'] += (dpr_val / 2)
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
            if last_pitcher != win_p:
                score_diff = abs(self.state.home_score - self.state.away_score)
                if score_diff <= 3 and self.game_stats[last_pitcher]['innings_pitched'] >= 1.0: save_p = last_pitcher
                elif score_diff > 3 and self.game_stats[last_pitcher]['innings_pitched'] >= 3.0: save_p = last_pitcher

        if win_p: self.game_stats[win_p]['wins'] = 1
        if loss_p: self.game_stats[loss_p]['losses'] = 1
        if save_p: self.game_stats[save_p]['saves'] = 1

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

    def get_winner(self):
        if self.state.home_score > self.state.away_score: return self.home_team.name
        if self.state.away_score > self.state.home_score: return self.away_team.name
        return "DRAW"