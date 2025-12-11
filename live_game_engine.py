# -*- coding: utf-8 -*-
"""
ライブ試合エンジン (Ultimate Edition Ver.4: 物理演算完全補正・守備挙動リアル化・BABIP適正化版)
"""
import random
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict
from enum import Enum
from models import Position, Player, Team, PlayerRecord, PitchType, TeamLevel, generate_best_lineup, Stadium

# ========================================
# 物理定数・ユーティリティ
# ========================================

GRAVITY = 9.81          # 重力加速度 (m/s^2)
AIR_DENSITY = 1.20      # 空気密度 (kg/m^3)
BALL_MASS = 0.145       # ボール質量 (kg)
BALL_RADIUS = 0.037     # ボール半径 (m)
BALL_AREA = math.pi * (BALL_RADIUS ** 2)

# BABIP調整: 空気抵抗を強めて滞空時間を伸ばし、アウトを取りやすくする
DRAG_COEFF_BASE = 0.35  
MAGNUS_CONST = 0.0002   

STRIKE_ZONE = {
    'width': 0.432,
    'height': 0.56,
    'center_x': 0.0,
    'center_z': 0.75, # 地面からの高さ中心
    'half_width': 0.216,
    'half_height': 0.28
}

# 守備定数 (メートル単位)
FIELD_COORDS = {
    Position.PITCHER: (0, 18.0),
    Position.CATCHER: (0, -1.0),
    Position.FIRST: (19.3, 19.3), # 1塁ベース付近修正
    Position.SECOND: (10.0, 38.0),
    Position.THIRD: (-19.3, 19.3),
    Position.SHORTSTOP: (-10.0, 38.0),
    Position.LEFT: (-35.0, 85.0),
    Position.CENTER: (0.0, 92.0),
    Position.RIGHT: (35.0, 85.0),
}

# Linear Weights (得点価値)
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

# UZR算出用のスケーリング係数
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

    # 怪我している場合は大幅ダウン
    if hasattr(player, 'is_injured') and player.is_injured:
        return getattr(player.stats, stat_name) * 0.5

    base_value = getattr(player.stats, stat_name)
    
    # 調子補正
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
# 物理演算ユーティリティ
# ========================================

class PhysicsEngine:
    """
    高精度物理演算エンジン
    ルンゲ・クッタ法(RK4)を用いた弾道シミュレーション
    """
    @staticmethod
    def simulate_trajectory(
        v0: Tuple[float, float, float], 
        spin_rate: float, 
        spin_axis: Tuple[float, float, float],
        start_pos: Tuple[float, float, float],
        dt: float = 0.01,
        max_time: float = 10.0,
        stop_on_ground: bool = True
    ) -> List[Tuple[float, float, float]]:
        
        trajectory = [start_pos]
        pos = list(start_pos)
        vel = list(v0)
        
        # マグヌス力の係数計算 (簡易近似)
        cl = spin_rate * 0.00005 

        # スピン軸ベクトル (正規化)
        spin_len = math.sqrt(spin_axis[0]**2 + spin_axis[1]**2 + spin_axis[2]**2)
        if spin_len > 0:
            spin_axis = (spin_axis[0]/spin_len, spin_axis[1]/spin_len, spin_axis[2]/spin_len)
        else:
            spin_axis = (0, 0, 0)

        t = 0
        while t < max_time:
            v_mag = math.sqrt(vel[0]**2 + vel[1]**2 + vel[2]**2)
            if v_mag == 0: break

            # 4次のルンゲ・クッタ法で積分
            
            def acceleration(v):
                v_curr = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
                
                # 抗力 (Drag)
                # 高速域ではCdが下がる現象を簡易モデル化
                cd = DRAG_COEFF_BASE * (1.0 - (v_curr / 400.0)) 
                fd_mag = 0.5 * AIR_DENSITY * (v_curr**2) * cd * BALL_AREA
                
                fd = [
                    -fd_mag * (v[0] / v_curr),
                    -fd_mag * (v[1] / v_curr),
                    -fd_mag * (v[2] / v_curr)
                ]
                
                # マグヌス力 (Magnus)
                cross_x = spin_axis[1]*v[2] - spin_axis[2]*v[1]
                cross_y = spin_axis[2]*v[0] - spin_axis[0]*v[2]
                cross_z = spin_axis[0]*v[1] - spin_axis[1]*v[0]
                
                fm_mag = 0.5 * AIR_DENSITY * (v_curr**2) * cl * BALL_AREA
                
                fm = [fm_mag * cross_x, fm_mag * cross_y, fm_mag * cross_z]

                # 加速度
                ax = (fd[0] + fm[0]) / BALL_MASS
                ay = (fd[1] + fm[1]) / BALL_MASS
                az = (fd[2] + fm[2]) / BALL_MASS - GRAVITY
                
                return (ax, ay, az)

            k1_v = acceleration(vel)
            k1_p = vel
            
            v2 = [vel[i] + k1_v[i] * dt * 0.5 for i in range(3)]
            k2_v = acceleration(v2)
            k2_p = v2
            
            v3 = [vel[i] + k2_v[i] * dt * 0.5 for i in range(3)]
            k3_v = acceleration(v3)
            k3_p = v3
            
            v4 = [vel[i] + k3_v[i] * dt for i in range(3)]
            k4_v = acceleration(v4)
            k4_p = v4
            
            # 更新
            for i in range(3):
                pos[i] += (dt / 6.0) * (k1_p[i] + 2*k2_p[i] + 2*k3_p[i] + k4_p[i])
                vel[i] += (dt / 6.0) * (k1_v[i] + 2*k2_v[i] + 2*k3_v[i] + k4_v[i])
            
            trajectory.append(tuple(pos))
            t += dt
            
            if stop_on_ground and pos[2] <= 0:
                pos[2] = 0
                trajectory[-1] = tuple(pos)
                break
                
        return trajectory

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
    """NPB準拠の継投ロジック"""
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

        if abs(score_diff) <= 2 and state.is_risp() and next_batter.bats == "左":
             eff_vs_left = getattr(current_pitcher.stats, 'vs_left_batter', 50)
             if current_pitcher.throws == "右" and eff_vs_left < 45:
                 lefty_specialist = self._find_lefty_specialist(team, current_pitcher)
                 if lefty_specialist: return lefty_specialist

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
            if (is_close and is_late) or (bunt_skill > 70 and batting_ab < 45) or (state.runner_2b and is_close): return "BUNT"
        
        if state.runner_1b and not state.runner_2b and not state.runner_3b and state.outs < 2:
            runner_spd = get_effective_stat(state.runner_1b, 'speed')
            runner_stl = get_effective_stat(state.runner_1b, 'steal')
            attempt_prob = 0.02 + (runner_spd - 50) * 0.003
            attempt_prob *= (0.7 + (runner_stl / 50.0) * 0.5)
            if is_close and is_late: attempt_prob *= 0.5
            elif abs(score_diff) >= 4: attempt_prob *= 1.2
            attempt_prob = max(0.005, attempt_prob)
            if random.random() < attempt_prob: return "STEAL"
        
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
    # 物理パラメータ (速度km/h, スピンrpm, 縦変化, 横変化)
    # spin_axis: (x, y, z)
    PITCH_SPECS = {
        "ストレート": {"velo": 148, "spin": 2300, "axis": (-0.1, 0, 1.0)}, 
        "ツーシーム": {"velo": 145, "spin": 2100, "axis": (0.3, 0, 0.8)},
        "カットボール": {"velo": 140, "spin": 2400, "axis": (-0.4, 0, 0.5)},
        "スライダー": {"velo": 132, "spin": 2500, "axis": (-0.8, 0, 0.2)}, 
        "カーブ":     {"velo": 115, "spin": 2600, "axis": (-0.6, 0, -0.6)}, 
        "フォーク":   {"velo": 136, "spin": 1200, "axis": (0, 0, 1.0)},     
        "チェンジアップ": {"velo": 128, "spin": 1800, "axis": (0.2, 0, 0.8)},
        "シュート":   {"velo": 140, "spin": 2200, "axis": (0.8, 0, 0.6)},
        "シンカー":   {"velo": 142, "spin": 2000, "axis": (0.7, 0, -0.3)},
        "スプリット": {"velo": 140, "spin": 1400, "axis": (0, 0, 0.9)}
    }

    def generate_pitch(self, pitcher: Player, batter: Player, catcher: Player, state: GameState, strategy="NORMAL", stadium: Stadium = None) -> PitchData:
        is_risp = state.is_risp()
        is_close = abs(state.home_score - state.away_score) <= 2
        
        velocity_st = get_effective_stat(pitcher, 'velocity', batter, is_risp, is_close)
        control_st = get_effective_stat(pitcher, 'control', batter, is_risp, is_close)
        movement_st = get_effective_stat(pitcher, 'movement', batter, is_risp, is_close)
        
        if stadium: control_st = control_st / max(0.5, stadium.pf_bb)
        if catcher:
            lead = get_effective_stat(catcher, 'catcher_lead', is_close_game=is_close)
            control_st += (lead - 50) * 0.2
        
        current_stamina = state.current_pitcher_stamina()
        fatigue = 1.0
        if current_stamina < 30: fatigue = 0.9 + (current_stamina / 300.0)
        
        pitch_cost = 0.5 * (1.2 if is_risp else 1.0)
        if state.is_top: state.home_pitcher_stamina = max(0, state.home_pitcher_stamina - pitch_cost)
        else: state.away_pitcher_stamina = max(0, state.away_pitcher_stamina - pitch_cost)
        
        pitch_type = "ストレート"
        breaking_balls = getattr(pitcher.stats, 'breaking_balls', [])
        
        if strategy != "WALK" and breaking_balls:
            straight_prob = max(0.4, 0.7 - len(breaking_balls) * 0.1)
            if state.strikes == 2: straight_prob *= 0.7
            if random.random() >= straight_prob:
                pitches = pitcher.stats.pitches
                if pitches:
                    total_val = sum(pitches.values())
                    r = random.uniform(0, total_val)
                    curr = 0
                    for p, v in pitches.items():
                        curr += v
                        if r <= curr:
                            pitch_type = p
                            break
                else: pitch_type = breaking_balls[0]
            
        spec = self.PITCH_SPECS.get(pitch_type, self.PITCH_SPECS["ストレート"])
        
        # 速度計算
        base_v_kmh = velocity_st * fatigue * (spec["velo"] / 148.0)
        v_kmh = random.gauss(base_v_kmh, 1.5)
        v_ms = v_kmh / 3.6
        
        # スピンと変化量
        move_factor = 1.0 + (movement_st - 50) * 0.01
        spin_rate = spec["spin"] * move_factor * random.uniform(0.95, 1.05)
        
        axis = list(spec["axis"])
        if pitcher.throws == "左":
            axis[0] *= -1 
        
        # ターゲット座標
        target_x, target_z = self._calc_target(control_st * fatigue, state, strategy)
        
        # 反復補正: 物理シミュレーションを回して、ターゲットに到達する初速ベクトルを見つける
        # 3回のイテレーションで誤差を修正
        dist = 18.44
        release_point = (random.uniform(-0.1, 0.1), 18.44, 1.8) 
        
        # 初期推定 (直線 + 重力分補正)
        flight_time_est = dist / v_ms
        v_x = (target_x - release_point[0]) / flight_time_est
        v_y = -v_ms # マウンドからホームへはY軸マイナス方向
        v_z = (target_z - release_point[2]) / flight_time_est + (0.5 * 9.81 * flight_time_est)
        
        v0 = [v_x, v_y, v_z]
        
        # 反復修正ループ
        for _ in range(2):
            traj = PhysicsEngine.simulate_trajectory(v0, spin_rate, axis, release_point)
            actual_end = traj[-1]
            
            # 誤差
            err_x = target_x - actual_end[0]
            err_z = target_z - actual_end[2]
            
            # 補正
            v0[0] += err_x / flight_time_est
            v0[2] += err_z / flight_time_est
        
        # 最終シミュレーション
        final_traj = PhysicsEngine.simulate_trajectory(v0, spin_rate, axis, release_point)
        final_end = final_traj[-1]
        
        h_break = (final_end[0] - target_x) * 100 
        v_break = (final_end[2] - target_z) * 100 

        loc = PitchLocation(final_end[0], final_end[2], self._is_strike(final_end[0], final_end[2]))
        
        return PitchData(
            pitch_type, round(v_kmh, 1), int(spin_rate), 
            h_break, v_break, loc, release_point, final_traj
        )

    def _calc_target(self, control, state, strategy):
        if strategy == "WALK": return (1.0, 1.5)
        
        tx, tz = 0, STRIKE_ZONE['center_z']
        
        # コントロールのブレ幅
        sigma = max(0.035, 0.18 - (control * 0.0018))
        
        # ストライクゾーン狙撃率 (高めに設定してカウントを整える)
        zone_prob = 0.68 + (control - 50)*0.004
        
        if strategy == "STRIKE" or state.balls == 3: zone_prob += 0.25
        elif strategy == "BALL" or state.strikes == 2: zone_prob -= 0.25
        
        if random.random() < zone_prob:
            corner_prob = 0.6 if control > 60 else 0.2
            if random.random() < corner_prob:
                tx = random.choice([-0.2, 0.2])
                tz = STRIKE_ZONE['center_z'] + random.choice([-0.25, 0.25])
        else:
            tx = random.choice([-0.35, 0.35])
            tz = STRIKE_ZONE['center_z'] + random.choice([-0.35, 0.35])

        ax = random.gauss(tx, sigma)
        az = random.gauss(tz, sigma)
        return ax, az

    def _is_strike(self, x, z):
        return (abs(x) <= STRIKE_ZONE['half_width'] + 0.036 and 
                abs(z - STRIKE_ZONE['center_z']) <= STRIKE_ZONE['half_height'] + 0.036)

class BattedBallGenerator:
    def generate(self, batter: Player, pitcher: Player, pitch: PitchData, state: GameState, strategy="SWING"):
        is_risp = state.is_risp()
        is_close = abs(state.home_score - state.away_score) <= 2

        power = get_effective_stat(batter, 'power', opponent=pitcher, is_risp=is_risp, is_close_game=is_close)
        contact = get_effective_stat(batter, 'contact', opponent=pitcher, is_risp=is_risp, is_close_game=is_close)
        
        # ミート確率
        sweet_spot_prob = (contact / 120.0) 
        if pitch.location.is_strike: sweet_spot_prob += 0.1
        else: sweet_spot_prob -= 0.2
        
        if strategy == "MEET": sweet_spot_prob += 0.15
        elif strategy == "POWER": sweet_spot_prob -= 0.15
        
        # BABIP調整: 芯で捉える確率を抑制
        is_sweet = random.random() < max(0.05, min(0.85, sweet_spot_prob * 0.9))
        quality = "hard" if is_sweet else ("medium" if random.random() < 0.6 else "soft")
        
        base_exit_v_kmh = 130 + (power - 50) * 1.2
        if quality == "hard": base_exit_v_kmh += 20
        elif quality == "soft": base_exit_v_kmh -= 40
        
        base_exit_v_kmh += (pitch.velocity - 140) * 0.15
        exit_v_kmh = max(60, random.gauss(base_exit_v_kmh, 5))
        exit_v = exit_v_kmh / 3.6 
        
        traj_tendency = getattr(batter.stats, 'trajectory', 2) 
        base_angle = 10 + (traj_tendency - 2) * 8
        if strategy == "BUNT":
            angle = random.gauss(-15, 5)
            exit_v = random.uniform(5, 15)
            quality = "soft"
        else:
            angle = random.gauss(base_angle, 15)
            if quality == "soft":
                if random.random() < 0.5: angle = random.uniform(-40, 5) 
                else: angle = random.uniform(50, 85) 
        
        timing_bias = random.gauss(0, 10 - (contact/20.0))
        bats = getattr(batter, 'bats', '右')
        if bats == '左': spray = -timing_bias * 2 
        else: spray = timing_bias * 2            
        
        rad_launch = math.radians(angle)
        rad_spray = math.radians(spray)
        
        vx = exit_v * math.cos(rad_launch) * math.sin(rad_spray)
        vy = exit_v * math.cos(rad_launch) * math.cos(rad_spray)
        vz = exit_v * math.sin(rad_launch)
        
        v0 = (vx, vy, vz)
        start_pos = (0, 0, 1.0) 
        
        if angle > 10:
            spin_rate = 1500 + (angle * 30) + (power * 10)
            spin_axis = (-1, 0, 0) 
        else:
            spin_rate = 1000 + abs(angle * 20)
            spin_axis = (1, 0, 0) 
            
        spin_axis = (spin_axis[0], 0, -math.sin(rad_spray)*0.5)

        trajectory = PhysicsEngine.simulate_trajectory(v0, spin_rate, spin_axis, start_pos, max_time=8.0)
        
        land_pos = trajectory[-1]
        dist = math.sqrt(land_pos[0]**2 + land_pos[1]**2)
        hang_time = len(trajectory) * 0.01
        
        if angle < 10: htype = BattedBallType.GROUNDBALL
        elif angle < 25: htype = BattedBallType.LINEDRIVE
        elif angle < 50: htype = BattedBallType.FLYBALL
        else: htype = BattedBallType.POPUP
        
        return BattedBallData(
            exit_v_kmh, angle, spray, htype, dist, hang_time, 
            land_pos[0], land_pos[1], trajectory, quality
        )

class AdvancedDefenseEngine:
    """
    超本格守備エンジン: 加速・最大速度・反応時間を考慮した物理的交差判定
    """
    def judge(self, ball: BattedBallData, defense_team: Team, team_level: TeamLevel = TeamLevel.FIRST, stadium: Stadium = None):
        pf_hr = stadium.pf_hr if stadium else 1.0
        fence_dist = 122.0 / math.sqrt(pf_hr) 
        fence_h = 3.0
        
        for i, pos in enumerate(ball.trajectory):
            d = math.sqrt(pos[0]**2 + pos[1]**2)
            if d >= fence_dist:
                if pos[2] > fence_h and abs(ball.spray_angle) < 45:
                    return PlayResult.HOME_RUN
                elif pos[2] <= fence_h and abs(ball.spray_angle) < 45:
                    pass # フェンス直撃
                break
                
        if abs(ball.spray_angle) > 45: return PlayResult.FOUL

        target_pos = (ball.landing_x, ball.landing_y)
        best_fielder, fielder_type, initial_pos = self._find_nearest_fielder(target_pos, defense_team, team_level)
        
        if not best_fielder: return PlayResult.SINGLE 

        # 守備パラメータ取得
        speed_stat = get_effective_stat(best_fielder, 'speed')
        range_stat = best_fielder.stats.get_defense_range(getattr(Position, fielder_type))
        
        # 物理パラメータ設定
        # 加速度 (m/s^2): 爆発力
        accel = 4.0 + (speed_stat / 100.0) * 2.0
        # 最大速度 (m/s): スピード
        max_v = 7.5 + (speed_stat / 100.0) * 4.5 
        # 反応時間 (s): 守備範囲・判断力
        reaction_time = max(0.1, 0.45 - (range_stat / 250.0))
        
        # 捕球可能性判定ループ
        can_catch = False
        
        # ボールの軌道を時間ステップごとにチェック
        for t_idx, b_pos in enumerate(ball.trajectory):
            t = t_idx * 0.01
            
            # まだ反応していない
            if t < reaction_time: continue
            
            # ボールの高さチェック (ジャンプ到達圏内 2.5m, ダイビング 0.5m)
            # フライならある程度の高さでも取れるが、今回はシンプルに3m以下とする
            if b_pos[2] > 3.0: continue
            
            # 必要な移動距離
            dist_to_ball = math.sqrt((b_pos[0] - initial_pos[0])**2 + (b_pos[1] - initial_pos[1])**2)
            
            # 野手が時間 t で到達できる距離を計算 (等加速度運動 -> 等速運動)
            run_time = t - reaction_time
            
            # 加速にかかる時間
            t_accel = max_v / accel
            
            if run_time <= t_accel:
                # 加速中: d = 1/2 * a * t^2
                reach_dist = 0.5 * accel * (run_time ** 2)
            else:
                # 等速中: d = (加速中の距離) + v_max * (残り時間)
                dist_accel = 0.5 * accel * (t_accel ** 2)
                reach_dist = dist_accel + max_v * (run_time - t_accel)
            
            # 捕球半径 (0.5m 〜 1.5m)
            catch_radius = 1.0 + (range_stat / 200.0)
            
            if reach_dist + catch_radius >= dist_to_ball:
                # 追いついた
                error_rate = 1.0 - (get_effective_stat(best_fielder, 'error') / 120.0)
                catch_prob = 0.98 * error_rate
                
                # ギリギリの場合確率ダウン
                margin = (reach_dist + catch_radius) - dist_to_ball
                if margin < 1.0:
                    catch_prob *= (0.5 + margin * 0.4)
                
                if random.random() < catch_prob:
                    can_catch = True
                    break

        if can_catch:
            self._update_defensive_metrics(best_fielder, team_level, 1.0, True, 1.0)
            if ball.hit_type == BattedBallType.FLYBALL: return PlayResult.FLYOUT
            if ball.hit_type == BattedBallType.POPUP: return PlayResult.POPUP_OUT
            if ball.hit_type == BattedBallType.LINEDRIVE: return PlayResult.LINEOUT
            return self._judge_grounder_throw(best_fielder, ball, team_level)
        else:
            self._update_defensive_metrics(best_fielder, team_level, 0.0, False, -0.5)
            return self._judge_hit_type_potential(ball, target_pos, stadium)

    def _find_nearest_fielder(self, ball_pos, team, team_level):
        min_dist = 999.0; best_f = None; best_type = ""; best_init = (0,0)
        lineup = team.current_lineup
        if team_level == TeamLevel.SECOND: lineup = team.farm_lineup
        elif team_level == TeamLevel.THIRD: lineup = team.third_lineup
        
        pos_map = {}
        for idx in lineup:
            if 0 <= idx < len(team.players):
                p = team.players[idx]
                if p.position != Position.DH: pos_map[p.position] = p
        
        pitcher = team.players[team.starting_pitcher_idx]
        pos_map[Position.PITCHER] = pitcher

        for pos_enum, coords in FIELD_COORDS.items():
            if pos_enum in pos_map:
                dist = math.sqrt((ball_pos[0] - coords[0])**2 + (ball_pos[1] - coords[1])**2)
                if dist < min_dist:
                    min_dist = dist; best_f = pos_map[pos_enum]; best_type = pos_enum.name; best_init = coords
        return best_f, best_type, best_init

    def _judge_grounder_throw(self, fielder, ball, team_level):
        base_1b_pos = (19.3, 19.3) 
        ball_x = ball.landing_x; ball_y = ball.landing_y
        dist_to_1b = math.sqrt((ball_x - base_1b_pos[0])**2 + (ball_y - base_1b_pos[1])**2)
        
        arm = get_effective_stat(fielder, 'arm')
        throw_speed = 30 + (arm / 100.0) * 15 
        transfer_time = 0.8 - (get_effective_stat(fielder, 'error') / 200.0)
        throw_time = transfer_time + (dist_to_1b / throw_speed)
        
        runner_speed_stat = 50 
        runner_time = 4.3 - ((runner_speed_stat - 50) * 0.01)
        
        if throw_time < runner_time:
            return PlayResult.GROUNDOUT
        else:
            return PlayResult.SINGLE 

    def _judge_hit_type_potential(self, ball, ball_pos, stadium):
        dist = ball.distance
        if dist > 85: return PlayResult.DOUBLE
        if dist > 105: return PlayResult.TRIPLE if random.random() < 0.2 else PlayResult.DOUBLE
        return PlayResult.SINGLE

    def _update_defensive_metrics(self, fielder, team_level, catch_prob, is_caught, play_value):
        rec = fielder.get_record_by_level(team_level)
        rec.def_opportunities += 1
        
        rng_r = 0.0
        if is_caught:
            rng_r = (1.0 - catch_prob) * play_value
            rec.def_plays_made += 1
        else:
            rng_r = (0.0 - catch_prob) * play_value
            
        rng_r *= UZR_SCALE["RngR"]
        rec.def_drs_raw += rng_r
        rec.uzr_rngr += rng_r
    
    def judge_arm_opportunity(self, ball, fielder, runner, base_from, team_level):
        pass

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
        self._ensure_valid_lineup(self.home_team)
        self._ensure_valid_lineup(self.away_team)

    def _ensure_valid_lineup(self, team: Team):
        if self.team_level == TeamLevel.SECOND:
            get_lineup = lambda: team.farm_lineup; set_lineup = lambda l: setattr(team, 'farm_lineup', l); get_roster = team.get_farm_roster_players
        elif self.team_level == TeamLevel.THIRD:
            get_lineup = lambda: team.third_lineup; set_lineup = lambda l: setattr(team, 'third_lineup', l); get_roster = team.get_third_roster_players
        else:
            get_lineup = lambda: team.current_lineup; set_lineup = lambda l: setattr(team, 'current_lineup', l); get_roster = team.get_active_roster_players

        current_lineup = get_lineup()
        has_injured_player = False
        if current_lineup and len(current_lineup) >= 9:
            for idx in current_lineup:
                if 0 <= idx < len(team.players):
                    if team.players[idx].is_injured:
                        has_injured_player = True; break
        if not current_lineup or len(current_lineup) < 9 or has_injured_player:
            players = get_roster()
            if len(players) < 9 and self.team_level != TeamLevel.FIRST:
                players = [p for p in team.players if p.team_level != TeamLevel.FIRST]
            if len(players) < 9: players = team.players
            new_lineup = generate_best_lineup(team, players)
            set_lineup(new_lineup); current_lineup = new_lineup

        has_valid_catcher = False
        if self.team_level == TeamLevel.FIRST and hasattr(team, 'lineup_positions') and len(team.lineup_positions) == 9:
            for i, pos_str in enumerate(team.lineup_positions):
                if pos_str in ["捕", "捕手"] and i < len(current_lineup): has_valid_catcher = True; break
        if not has_valid_catcher:
            for idx in current_lineup:
                if 0 <= idx < len(team.players):
                    p = team.players[idx]
                    if p.position == Position.CATCHER or p.stats.get_defense_range(Position.CATCHER) >= 20: has_valid_catcher = True; break
        if not has_valid_catcher:
            players = get_roster()
            if len(players) < 9 and self.team_level != TeamLevel.FIRST:
                players = [p for p in team.players if p.team_level != TeamLevel.FIRST]
            new_lineup = generate_best_lineup(team, players)
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
                self.state.home_pitcher_idx = new_idx
                self.state.home_pitchers_used.append(new_pitcher)
                self.state.home_pitcher_stamina = new_pitcher.stats.stamina
                self.state.home_pitch_count = 0
                self.state.home_current_pitcher_runs = 0
            else:
                self.state.away_pitcher_idx = new_idx
                self.state.away_pitchers_used.append(new_pitcher)
                self.state.away_pitcher_stamina = new_pitcher.stats.stamina
                self.state.away_pitch_count = 0
                self.state.away_current_pitcher_runs = 0
            self.game_stats[new_pitcher]['games_pitched'] = 1
        except ValueError:
            pass

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
            injury_names = ["違和感", "捻挫", "肉離れ", "炎症"]
            name = f"患部の{random.choice(injury_names)}"
            if hasattr(player, 'inflict_injury'):
                player.inflict_injury(days, name)
            return True
        return False

    def simulate_pitch(self, manual_strategy=None):
        batter, _ = self.get_current_batter()
        pitcher, _ = self.get_current_pitcher()
        defense_team = self.home_team if self.state.is_top else self.away_team
        
        new_pitcher = self.ai.pitcher_manager.check_pitcher_change(self.state, defense_team, self.away_team if self.state.is_top else self.home_team, batter, pitcher)
        if new_pitcher:
            self.change_pitcher(new_pitcher)
            pitcher = new_pitcher
            
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
        
        if not pitch.location.is_strike and pitch.location.z < 0.15 and catcher:
            catch_err = get_effective_stat(catcher, 'error')
            block_prob = 0.85 + (catch_err - 50) * 0.005
            if random.random() < 0.05:
                val = 0.1 * UZR_SCALE["rBlk"] if random.random() <= block_prob else -0.5 * UZR_SCALE["rBlk"]
                self.game_stats[catcher]['uzr_rblk'] += val; self.game_stats[catcher]['def_drs_raw'] += val

        res, ball = self._resolve_contact(batter, pitcher, pitch, strategy)
        
        # 修正: simulate_pitch内で処理を完結させる
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
        # スイング率調整
        swing_prob = (0.85 + (eye-50)*0.001) if pitch.location.is_strike else (0.38 - (eye-50)*0.004)
        if self.state.strikes == 2: swing_prob += 0.15
        if strategy == "POWER": swing_prob += 0.1 
        if strategy == "MEET": swing_prob -= 0.1
        swing_prob = max(0.01, min(0.99, swing_prob))
        
        if random.random() >= swing_prob: return PitchResult.STRIKE_CALLED if pitch.location.is_strike else PitchResult.BALL, None
            
        contact = get_effective_stat(batter, 'contact', opponent=pitcher)
        stuff = get_effective_stat(pitcher, 'stuff', opponent=batter)
        base_contact = 0.76
        diff = contact - stuff
        hit_prob = base_contact + (diff * 0.0035)
        
        if pitch.location.is_strike: hit_prob += 0.08
        else: hit_prob -= 0.12
            
        if self.stadium: hit_prob /= max(0.5, self.stadium.pf_so)
        hit_prob = max(0.45, min(0.96, hit_prob))

        if self.state.strikes == 2:
            avoid_k = get_effective_stat(batter, 'avoid_k')
            hit_prob += (avoid_k - 50) * 0.002

        if random.random() > hit_prob: 
             if hasattr(self, '_check_injury_occurrence'): self._check_injury_occurrence(batter, "SWING")
             return PitchResult.STRIKE_SWINGING, None
             
        if random.random() < 0.32: return PitchResult.FOUL, None
             
        ball = self.bat_gen.generate(batter, pitcher, pitch, self.state, strategy)
        if hasattr(self, '_check_injury_occurrence'): self._check_injury_occurrence(batter, "RUN")
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
        
        # 修正: pitchがNoneの場合の安全策
        is_in_zone = False
        if pitch:
            is_in_zone = pitch.location.is_strike
            self.game_stats[pitcher]['pitches_thrown'] += 1; self.game_stats[batter]['pitches_seen'] += 1
            if is_in_zone:
                self.game_stats[pitcher]['zone_pitches'] += 1; self.game_stats[batter]['zone_pitches'] += 1
            else:
                self.game_stats[pitcher]['chase_pitches'] += 1; self.game_stats[batter]['chase_pitches'] += 1

        is_swing = res in [PitchResult.STRIKE_SWINGING, PitchResult.FOUL, PitchResult.IN_PLAY]
        is_contact = res in [PitchResult.FOUL, PitchResult.IN_PLAY]

        if is_swing and pitch:
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
                final_result = PlayResult.STRIKEOUT
        elif res == PitchResult.FOUL:
            if self.state.strikes < 2: self.state.strikes += 1
            final_result = PitchResult.FOUL
        elif res == PitchResult.IN_PLAY:
            defense_team = self.home_team if self.state.is_top else self.away_team
            play = self.def_eng.judge(ball, defense_team, self.team_level, self.stadium)
            
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
                final_result = PitchResult.FOUL
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
        lineup = defense_team.current_lineup
        if self.team_level == TeamLevel.SECOND: lineup = defense_team.farm_lineup
        elif self.team_level == TeamLevel.THIRD: lineup = defense_team.third_lineup
        for p_idx in lineup:
            if 0 <= p_idx < len(defense_team.players):
                p = defense_team.players[p_idx]
                if p.position != Position.DH: self.game_stats[p]['defensive_innings'] += (1.0 / 3.0)
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
                best_fielder, _, _ = self.def_eng._find_nearest_fielder((ball.landing_x, ball.landing_y), defense_team, self.team_level)
                if best_fielder and best_fielder.position in [Position.LEFT, Position.CENTER, Position.RIGHT]:
                    if self.state.runner_1b: self.def_eng.judge_arm_opportunity(ball, best_fielder, self.state.runner_1b, 1, self.team_level)
                    if self.state.runner_2b: self.def_eng.judge_arm_opportunity(ball, best_fielder, self.state.runner_2b, 2, self.team_level)

            self._record_pf(batter, pitcher)
            self._reset_count(); self._next_batter()
            
            if play == PlayResult.HOME_RUN: scored_players = self._advance_runners(4, batter)
            elif play == PlayResult.SINGLE: scored_players = self._advance_runners(1, batter)
            elif play == PlayResult.DOUBLE: scored_players = self._advance_runners(2, batter)
            elif play == PlayResult.TRIPLE: scored_players = self._advance_runners(3, batter)
            
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
                if p.position in [Position.SECOND, Position.SHORTSTOP]:
                    dp_skill += get_effective_stat(p, 'turn_dp'); count += 1
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
        lineup = defense_team.current_lineup
        if self.team_level == TeamLevel.SECOND: lineup = defense_team.farm_lineup
        elif self.team_level == TeamLevel.THIRD: lineup = defense_team.third_lineup
        for p_idx in lineup:
            if 0 <= p_idx < len(defense_team.players):
                player = defense_team.players[p_idx]
                if player.position != Position.DH: self.game_stats[player]['defensive_innings'] += (1.0/3.0)

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
            for p_idx in lineup:
                if 0 <= p_idx < len(defense_team.players):
                    p = defense_team.players[p_idx]
                    if p.position != Position.DH: self.game_stats[player]['defensive_innings'] += (1.0/3.0)
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
        UBR_SUCCESS_1B3B = 0.18; UBR_FAIL_1B3B = -0.80
        UBR_HOLD_1B2B = -0.06; UBR_SUCCESS_2BH = 0.22
        UBR_FAIL_2BH = -1.00; UBR_HOLD_2B3B = -0.08
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
                    spd = get_effective_stat(self.state.runner_2b, 'speed')
                    br = get_effective_stat(self.state.runner_2b, 'baserunning')
                    if random.random() < (0.40 + (spd-50)*0.015 + (br-50)*0.005):
                        if random.random() < 0.05:
                            self.game_stats[self.state.runner_2b]['ubr_val'] += UBR_FAIL_2BH; self.state.runner_2b = None; self.state.outs += 1
                        else:
                            scored_players.append(self.state.runner_2b); self.game_stats[self.state.runner_2b]['ubr_val'] += UBR_SUCCESS_2BH; self.state.runner_2b = None
                    else:
                        self.state.runner_3b = self.state.runner_2b; self.game_stats[self.state.runner_2b]['ubr_val'] += UBR_HOLD_2B3B; self.state.runner_2b = None
            if self.state.runner_1b:
                if bases >= 3: scored_players.append(self.state.runner_1b); self.state.runner_1b = None
                elif bases == 2:
                    spd = get_effective_stat(self.state.runner_1b, 'speed')
                    br = get_effective_stat(self.state.runner_1b, 'baserunning')
                    if random.random() < (0.35 + (spd-50)*0.015 + (br-50)*0.005):
                        if random.random() < 0.05:
                            self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_FAIL_1BH; self.state.runner_1b = None; self.state.outs += 1
                        else:
                            scored_players.append(self.state.runner_1b); self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_SUCCESS_1BH; self.state.runner_1b = None
                    else:
                        self.state.runner_3b = self.state.runner_1b; self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_HOLD_1B3B; self.state.runner_1b = None
                elif bases == 1:
                    spd = get_effective_stat(self.state.runner_1b, 'speed')
                    br = get_effective_stat(self.state.runner_1b, 'baserunning')
                    if self.state.runner_3b is None and random.random() < (0.25 + (spd-50)*0.015 + (br-50)*0.005):
                        if random.random() < 0.05:
                            self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_FAIL_1B3B; self.state.runner_1b = None; self.state.outs += 1
                        else:
                            self.state.runner_3b = self.state.runner_1b; self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_SUCCESS_1B3B; self.state.runner_1b = None
                    else:
                        self.state.runner_2b = self.state.runner_1b; self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_HOLD_1B2B; self.state.runner_1b = None
            
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
        if self.state.inning > 9:
             if self.state.is_top: return False
             if self.state.home_score != self.state.away_score: return True
             if self.state.inning >= 12 and self.state.outs >= 3: return True
        if self.state.inning >= 9 and not self.state.is_top and self.state.home_score > self.state.away_score: return True
        return False

    def finalize_game_stats(self):
        win_p, loss_p, save_p = None, None, None
        if not self.state.home_pitchers_used or not self.state.away_pitchers_used: return

        home_win = self.state.home_score > self.state.away_score
        away_win = self.state.away_score > self.state.home_score
        
        if home_win:
            win_team_pitchers = self.state.home_pitchers_used
            loss_team_pitchers = self.state.away_pitchers_used
            starter = win_team_pitchers[0]
            if self.game_stats[starter]['innings_pitched'] >= 5: win_p = starter
            else: win_p = win_team_pitchers[1] if len(win_team_pitchers) > 1 else starter
            loss_p = loss_team_pitchers[0]
        elif away_win:
            win_team_pitchers = self.state.away_pitchers_used
            loss_team_pitchers = self.state.home_pitchers_used
            starter = win_team_pitchers[0]
            if self.game_stats[starter]['innings_pitched'] >= 5: win_p = starter
            else: win_p = win_team_pitchers[1] if len(win_team_pitchers) > 1 else starter
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
            if player in self.home_team.players:
                if player.position == Position.PITCHER: record.home_games_pitched += 1
                else: record.home_games += 1

    def get_winner(self):
        if self.state.home_score > self.state.away_score: return self.home_team.name
        if self.state.away_score > self.state.home_score: return self.away_team.name
        return "DRAW"