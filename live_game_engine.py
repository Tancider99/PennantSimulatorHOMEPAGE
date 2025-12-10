# -*- coding: utf-8 -*-
"""
ライブ試合エンジン (完全版: NPB準拠・全軍統一ロジック・超現実的バランス調整)
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

# 守備定数 (メートル単位)
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

# Linear Weights (得点価値) - NPB環境に合わせて微調整
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

def get_effective_stat(player: Player, stat_name: str, opponent: Optional[Player] = None, is_risp: bool = False, is_close_game: bool = False) -> float:
    """能力値の実効値を計算 (コンディション、対左右、特殊能力などを加味)"""
    if not hasattr(player.stats, stat_name):
        return 50.0
    base_value = getattr(player.stats, stat_name)
    
    # コンディション補正 (1-9, 5が普通)
    # 調子の影響をやや強める (±10%程度)
    condition_diff = player.condition - 5
    condition_multiplier = 1.0 + (condition_diff * 0.025)
    
    value = base_value * condition_multiplier
    
    if player.position != Position.PITCHER:
        # 打者
        if stat_name in ['contact', 'power'] and opponent and opponent.position == Position.PITCHER:
            # 対左投手
            if getattr(opponent, 'throws', '右') == '左':
                vs_left = getattr(player.stats, 'vs_left_batter', 50)
                value += (vs_left - 50) * 0.3 # 影響度アップ
        
        if is_risp and stat_name in ['contact', 'power']:
            chance = getattr(player.stats, 'chance', 50)
            value += (chance - 50) * 0.4
            
        if is_close_game:
            mental = getattr(player.stats, 'mental', 50)
            value += (mental - 50) * 0.2
    else:
        # 投手
        if opponent and opponent.position != Position.PITCHER:
            # 対左打者
            if getattr(opponent, 'bats', '右') == '左': # 簡易判定
                vs_left = getattr(player.stats, 'vs_left_pitcher', 50)
                value += (vs_left - 50) * 0.3
                
        if is_risp:
            pinch = getattr(player.stats, 'vs_pinch', 50)
            if stat_name in ['stuff', 'movement', 'control']:
                value += (pinch - 50) * 0.4
                
        if stat_name == 'control':
            stability = getattr(player.stats, 'stability', 50)
            if condition_diff < 0: # 調子が悪い時
                mitigation = (stability - 50) * 0.3
                value += max(0, mitigation) # 安定度が高いと調子が悪くても能力が下がりにくい

    return max(1.0, min(120.0, value)) # 上限下限を設定

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

    def is_runner_on(self) -> bool: return any([self.runner_1b, self.runner_2b, self.runner_3b])
    def is_risp(self) -> bool: return (self.runner_2b is not None) or (self.runner_3b is not None)
    def current_pitcher_stamina(self) -> float: return self.home_pitcher_stamina if self.is_top else self.away_pitcher_stamina

# ========================================
# エンジンクラス群
# ========================================

class AIManager:
    """AI戦略決定ロジック"""
    def decide_strategy(self, state: GameState, offense_team, defense_team, batter: Player) -> str:
        score_diff = state.away_score - state.home_score if state.is_top else state.home_score - state.away_score
        is_late = state.inning >= 7
        is_close = abs(score_diff) <= 2
        
        # バント判断 (NPBはバント多め)
        bunt_skill = get_effective_stat(batter, 'bunt_sac')
        batting_ab = batter.stats.overall_batting()
        
        # 無死一塁、または無死二塁での送りバント
        if state.outs == 0:
            if state.runner_1b and not state.runner_2b and not state.runner_3b:
                # 投手が打者の場合、または打撃が弱く接戦の場合
                if batter.position == Position.PITCHER: return "BUNT"
                if is_close and (batting_ab < 45 or bunt_skill > 70): return "BUNT"
            elif state.runner_2b and not state.runner_3b:
                if is_close and (batting_ab < 40 or bunt_skill > 80): return "BUNT"
        
        # 盗塁判断
        if state.runner_1b and not state.runner_2b and not state.runner_3b and state.outs < 2:
            runner_spd = get_effective_stat(state.runner_1b, 'speed')
            runner_stl = get_effective_stat(state.runner_1b, 'steal')
            
            # 成功率目安70%以上で企図
            base_prob = 0.05 + (runner_spd - 50) * 0.005 + (runner_stl - 50) * 0.005
            
            # 接戦終盤は慎重に、大量リード/ビハインドは走らない
            if is_close and is_late: base_prob *= 0.8
            if abs(score_diff) >= 5: base_prob *= 0.1
            
            if random.random() < max(0, base_prob): return "STEAL"
        
        eff_power = get_effective_stat(batter, 'power', is_risp=state.is_risp())
        eff_contact = get_effective_stat(batter, 'contact', is_risp=state.is_risp())
        
        # カウント別アプローチ
        if state.balls >= 3 and state.strikes < 2 and eff_power > 60: return "POWER"
        if state.strikes == 2 and eff_contact > 50: return "MEET" # 追い込まれたらミート中心
            
        return "SWING"

    def decide_pitch_strategy(self, state: GameState, pitcher: Player, batter: Player) -> str:
        eff_control = get_effective_stat(pitcher, 'control', opponent=batter, is_risp=state.is_risp())
        
        # 3ボールからはストライクを取りに行く
        if state.balls >= 3: return "STRIKE" 
        
        # 2ストライクからはボール球で誘う
        if state.strikes == 2:
            has_breaking = len(pitcher.stats.pitches) > 0
            if has_breaking and eff_control > 45: return "BALL"
            
        # 敬遠判断: 接戦終盤、一塁空き、強打者
        eff_power = get_effective_stat(batter, 'power', is_risp=state.is_risp())
        score_diff = abs(state.home_score - state.away_score)
        if state.is_risp() and not state.runner_1b and eff_power > 80 and state.inning >= 8 and score_diff <= 1:
            return "WALK"
            
        return "NORMAL"

class PitchGenerator:
    """投球生成ロジック: NPB準拠の配球と精度"""
    PITCH_DATA = {
        "ストレート": {"base_speed": 146, "h_break": 0, "v_break": 10}, # NPB平均球速は146km/h前後
        "ツーシーム": {"base_speed": 143, "h_break": 12, "v_break": 2},
        "カットボール": {"base_speed": 138, "h_break": -8, "v_break": 3},
        "スライダー": {"base_speed": 130, "h_break": -20, "v_break": -3},
        "カーブ":     {"base_speed": 115, "h_break": -12, "v_break": -25},
        "フォーク":   {"base_speed": 134, "h_break": 0, "v_break": -30},
        "チェンジアップ": {"base_speed": 128, "h_break": 8, "v_break": -15},
        "シュート":   {"base_speed": 140, "h_break": 18, "v_break": -6},
        "シンカー":   {"base_speed": 138, "h_break": 15, "v_break": -10},
        "スプリット": {"base_speed": 138, "h_break": 3, "v_break": -28}
    }

    def generate_pitch(self, pitcher: Player, batter: Player, catcher: Player, state: GameState, strategy="NORMAL", stadium: Stadium = None) -> PitchData:
        is_risp = state.is_risp()
        is_close = abs(state.home_score - state.away_score) <= 2
        
        velocity = get_effective_stat(pitcher, 'velocity', batter, is_risp, is_close)
        control = get_effective_stat(pitcher, 'control', batter, is_risp, is_close)
        movement = get_effective_stat(pitcher, 'movement', batter, is_risp, is_close)
        
        # スタジアム補正 (PF)
        if stadium: control = control / max(0.5, stadium.pf_bb)
        
        # キャッチャーリード補正
        if catcher:
            lead = get_effective_stat(catcher, 'catcher_lead', is_close_game=is_close)
            control += (lead - 50) * 0.15
        
        # スタミナ疲労計算
        current_stamina = state.current_pitcher_stamina()
        fatigue = 1.0
        if current_stamina < 30: fatigue = 0.9 + (current_stamina / 300.0)
        if current_stamina <= 0: fatigue = 0.85
        
        # スタミナ消費
        pitch_cost = 0.7 # 球数制限意識
        if is_risp: pitch_cost *= 1.3
        if state.is_top: state.home_pitcher_stamina = max(0, state.home_pitcher_stamina - pitch_cost)
        else: state.away_pitcher_stamina = max(0, state.away_pitcher_stamina - pitch_cost)
        
        # 球種決定
        pitch_type = "ストレート"
        breaking_balls = getattr(pitcher.stats, 'breaking_balls', [])
        
        if strategy != "WALK" and breaking_balls:
            # ストレート率: 平均45-50%
            straight_prob = max(0.40, 0.65 - len(breaking_balls) * 0.08)
            
            # 追い込んだら変化球率アップ
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
            
        base = self.PITCH_DATA.get(pitch_type, self.PITCH_DATA["ストレート"])
        
        # 球速計算 (疲労とランダム性)
        base_velo = velocity * fatigue
        if pitch_type != "ストレート":
            speed_ratio = base["base_speed"] / 146.0
            base_velo *= speed_ratio
            
        velo = random.gauss(base_velo, 1.2); velo = max(80, min(165, velo))
        
        # 変化量計算
        move_factor = 1.0 + (movement - 50) * 0.015
        h_brk = base["h_break"] * move_factor + random.gauss(0, 2)
        v_brk = base["v_break"] * move_factor + random.gauss(0, 2)
        
        # ロケーション計算
        loc = self._calc_location(control * fatigue, state, strategy)
        
        # 軌道計算 (簡易)
        traj = self._calc_traj(velo, h_brk, v_brk, loc)
        
        return PitchData(pitch_type, round(velo,1), 2200, h_brk, v_brk, loc, (0,18.44,1.8), traj)

    def _calc_location(self, control, state, strategy):
        if strategy == "WALK": return PitchLocation(1.0, 1.5, False)
        
        # ストライクゾーン投球率 (Zone%)
        # NPB平均: 47-49%程度
        # コントロール50で48%を目指す
        zone_target_prob = 0.48 + (control - 50) * 0.004
        
        # 戦略補正
        if strategy == "STRIKE": zone_target_prob += 0.25
        elif strategy == "BALL": zone_target_prob -= 0.25
        
        # カウント補正 (3ボールならストライク取りに来る)
        if state.balls == 3: zone_target_prob += 0.30
        if state.strikes == 0 and state.balls == 0: zone_target_prob += 0.05
        
        zone_target_prob = max(0.1, min(0.95, zone_target_prob))
        
        tx, tz = 0, STRIKE_ZONE['center_z']
        
        # 精度 (Sigma): コントロールが高いほどバラつきが小さい
        sigma = max(0.06, 0.25 - (control * 0.0025))
        
        is_target_zone = random.random() < zone_target_prob
        
        if is_target_zone:
            # ゾーン内狙い
            # 四隅を突くか真ん中か
            if random.random() < 0.3 + (control/200): # コントロールが良いほど四隅
                tx = random.choice([-0.2, 0.2])
                tz = STRIKE_ZONE['center_z'] + random.choice([-0.25, 0.25])
            else:
                tx = 0
                tz = STRIKE_ZONE['center_z']
        else:
            # ゾーン外（ボール球）狙い
            tx = random.choice([-0.35, 0.35])
            tz = STRIKE_ZONE['center_z'] + random.choice([-0.35, 0.35])

        # 実際の着弾点 (狙い + ブレ)
        ax = random.gauss(tx, sigma)
        az = random.gauss(tz, sigma)
        
        # ストライク判定
        is_strike = (abs(ax) <= STRIKE_ZONE['half_width'] + 0.036 and abs(az - STRIKE_ZONE['center_z']) <= STRIKE_ZONE['half_height'] + 0.036)
        return PitchLocation(ax, az, is_strike)

    def _calc_traj(self, velo, hb, vb, loc):
        path = []; start = (random.uniform(-0.05, 0.05), 18.44, 1.8); end = (loc.x, 0, loc.z)
        steps = 10
        for i in range(steps + 1):
            t = i/steps
            x = start[0] + (end[0]-start[0])*t + (hb/100 * 0.3)*math.sin(t*math.pi)
            y = start[1] * (1-t)
            z = start[2] + (end[2]-start[2])*t + (vb/100 * 0.3)*(t**2)
            path.append((x,y,z))
        return path

class BattedBallGenerator:
    """打球生成ロジック: NPBの打球傾向を再現"""
    def generate(self, batter: Player, pitcher: Player, pitch: PitchData, state: GameState, strategy="SWING"):
        is_risp = state.is_risp()
        is_close = abs(state.home_score - state.away_score) <= 2

        power = get_effective_stat(batter, 'power', opponent=pitcher, is_risp=is_risp, is_close_game=is_close)
        contact = get_effective_stat(batter, 'contact', opponent=pitcher, is_risp=is_risp, is_close_game=is_close)
        gap = get_effective_stat(batter, 'gap', opponent=pitcher, is_risp=is_risp)
        trajectory = getattr(batter.stats, 'trajectory', 2) # 1:ゴロ, 2:中, 3:高, 4:アーチ
        
        p_movement = get_effective_stat(pitcher, 'movement', opponent=batter, is_risp=is_risp)
        p_gb_tendency = getattr(pitcher.stats, 'gb_tendency', 50) # ゴロピッチャー傾向
        
        # コンタクト品質の決定
        # strategy補正
        meet_bonus = 15 if strategy == "MEET" else (-15 if strategy == "POWER" else 0)
        
        # ボール球ペナルティ
        ball_penalty = 0 if pitch.location.is_strike else 25
        
        # 有効コンタクト値
        con_eff = contact + meet_bonus - (p_movement - 50) * 0.3 - ball_penalty
        
        # 打球の質 (Hard/Medium/Soft)
        # PowerもHardHit率に影響する
        hard_threshold = (con_eff * 0.4) + (power * 0.3)
        medium_threshold = hard_threshold + 40
        
        quality_roll = random.uniform(0, 100)
        if quality_roll < hard_threshold: quality = "hard"
        elif quality_roll < medium_threshold: quality = "medium"
        else: quality = "soft"
        
        # 打球速度 (Exit Velocity)
        # NPB平均: 138-140km/h程度 (MLBは142km/h程度)
        base_v = 138.0 + (power - 50) * 0.15
        
        if strategy == "POWER": base_v += 8
        
        if quality == "hard": base_v += 12 + (power / 6.0) 
        elif quality == "soft": base_v -= 30 
        
        # ランダム分散
        velo = max(50, base_v + random.gauss(0, 6))
        
        # 打球角度 (Launch Angle)
        # 弾道(1-4)とゴロ傾向で中心角度が決まる
        # 1: 0度, 2: 10度, 3: 18度, 4: 25度
        traj_angles = {1: 0, 2: 10, 3: 18, 4: 25}
        angle_center = traj_angles.get(trajectory, 10)
        
        # 投手のゴロ傾向補正
        angle_center -= (p_gb_tendency - 50) * 0.2
        
        # 高め・低め補正
        if pitch.location.z < 0.4: angle_center -= 4 # 低めはゴロになりやすい
        if pitch.location.z > 0.8: angle_center += 4 # 高めはフライになりやすい
        
        # バント処理
        if strategy == "BUNT":
            angle = -25; velo = 35 + random.uniform(-5, 5)
            quality = "soft"
        else:
            # 角度の分散 (標準偏差)
            angle_sigma = 14
            # ギャップ狙い (ラインドライブ傾向)
            if gap > 60 and quality == "hard":
                # 理想的な角度(10-25度)に収束しやすい
                angle_sigma = 10
                angle_center = (angle_center + 18) / 2
                
            angle = random.gauss(angle_center, angle_sigma)
        
        # 打球タイプ判定
        if angle < 10: htype = BattedBallType.GROUNDBALL
        elif angle < 25: htype = BattedBallType.LINEDRIVE
        elif angle < 50: htype = BattedBallType.FLYBALL
        else: htype = BattedBallType.POPUP
        
        # 飛距離計算 (物理モデル簡易版)
        v_ms = velo / 3.6
        vacuum_dist = (v_ms**2 * math.sin(math.radians(2 * angle))) / 9.8
        
        # 空気抵抗係数 (速度が速いほど、角度が高いほど影響大)
        drag_base = 0.96 - (velo / 800.0) 
        drag_factor = max(0.3, drag_base)
        
        # フライ/ライナーの伸び
        if 20 <= angle <= 35: drag_factor *= 1.05 # スイートスポット
        if htype == BattedBallType.POPUP: drag_factor *= 0.6
        
        dist = max(0, vacuum_dist * drag_factor)
        
        # ゴロの距離は転がり係数で調整
        if htype == BattedBallType.GROUNDBALL:
            # 内野を抜けるかどうかは守備判定で決まるが、ここでは「到達地点」としての距離
            dist = min(dist, 50) + (velo * 0.2) 

        # 方向 (Spray Angle)
        # 引っ張り傾向などを考慮しても良いが、ここでは正規分布
        spray = random.gauss(0, 28)
        
        rad = math.radians(spray)
        land_x = dist * math.sin(rad)
        land_y = dist * math.cos(rad)
        
        # 滞空時間
        v_y = v_ms * math.sin(math.radians(angle))
        hang_time = (2 * v_y) / 9.8
        if htype == BattedBallType.GROUNDBALL:
            hang_time = dist / (v_ms * 0.9) # 転がり速度
        
        return BattedBallData(velo, angle, spray, htype, dist, hang_time, land_x, land_y, [], quality)

class AdvancedDefenseEngine:
    """
    守備エンジン: 選手の守備能力に基づいて安打/アウトを判定
    BABIP .300 前後、守備率 .985 前後を目指す
    """
    def judge(self, ball: BattedBallData, defense_team: Team, team_level: TeamLevel = TeamLevel.FIRST, stadium: Stadium = None):
        abs_spray = abs(ball.spray_angle)
        
        # HR判定 (フェンス距離)
        # NPB球場は両翼100m, 中堅122m程度が標準
        base_fence = 122 - (abs_spray / 45.0) * (122 - 100)
        pf_hr = stadium.pf_hr if stadium else 1.0
        
        # 弾道による補正（ライナー性のHRなど）
        fence_height_margin = 0
        if ball.hit_type == BattedBallType.LINEDRIVE: fence_height_margin = 5
        
        if ball.hit_type in [BattedBallType.FLYBALL, BattedBallType.LINEDRIVE] and ball.distance > (base_fence / math.sqrt(pf_hr) + fence_height_margin) and abs_spray < 45:
            return PlayResult.HOME_RUN
        
        if abs_spray > 45: return PlayResult.FOUL

        # 落点と一番近い野手を計算
        target_pos = (ball.landing_x, ball.landing_y)
        best_fielder, fielder_type, initial_pos = self._find_nearest_fielder(target_pos, defense_team, team_level)
        
        if not best_fielder: return PlayResult.SINGLE 

        dist_to_ball = math.sqrt((target_pos[0] - initial_pos[0])**2 + (target_pos[1] - initial_pos[1])**2)
        
        # 守備パラメータ取得
        range_stat = best_fielder.stats.get_defense_range(getattr(Position, fielder_type))
        range_stat = range_stat * (1.0 + (best_fielder.condition - 5) * 0.02)
        speed_stat = get_effective_stat(best_fielder, 'speed')
        
        # 到達可能時間の計算
        # 初速反応 (Reaction) + 移動速度 (Speed/Range)
        
        # 最高速度 (m/s): 選手により 6.0 ~ 8.5 m/s 程度
        max_speed = 6.0 + (speed_stat / 100.0) * 2.5 
        if fielder_type in ["LEFT", "CENTER", "RIGHT"]: max_speed += 0.5 # 外野手は加速できる
        
        # 反応時間 (秒): 打球判断にかかる時間
        # 守備範囲値が高いほど反応が良い
        reaction_delay = 0.45 - (range_stat / 200.0) 
        
        time_needed = reaction_delay + (dist_to_ball / max_speed)
        
        # 打球の到達時間 (Time Available)
        if ball.hit_type in [BattedBallType.FLYBALL, BattedBallType.POPUP, BattedBallType.LINEDRIVE]:
            time_available = ball.hang_time
            # ライナーは滞空時間が短くても近くなら捕れる
            if ball.hit_type == BattedBallType.LINEDRIVE:
                 if dist_to_ball < 4.0: time_needed = 0.1 
        else:
            # ゴロ: 内野を抜けるまでの時間
            # 平均的なゴロ速度: 100km/h (27.7m/s) -> 減速考慮して平均 20m/s
            ball_speed_ms = (ball.exit_velocity / 3.6) * 0.7 
            time_available = dist_to_ball / max(5.0, ball_speed_ms)
            
            # 極端に近いゴロ
            if ball.hit_type == BattedBallType.GROUNDBALL and ball.distance < 25:
                 time_available = 10.0 # 基本追いつける

        time_diff = time_available - time_needed
        catch_prob = 0.0
        
        # 捕球確率 (Catch Probability)
        if time_diff >= 0.5:
             catch_prob = 0.98 # 余裕で追いつく
        elif time_diff >= 0.0:
             # ギリギリ追いつく (0.0 ~ 0.5秒の余裕) -> 70% ~ 98%
             catch_prob = 0.70 + (time_diff / 0.5) * 0.28
        elif time_diff > -0.3:
             # ダイビングキャッチの範囲
             ratio = (time_diff + 0.3) / 0.3
             catch_prob = ratio * 0.60 
        else:
             catch_prob = 0.0 # 追いつけない
        
        # 打球強度による補正 (Hard Hitは捕りにくい)
        if ball.contact_quality == "hard": catch_prob *= 0.88
        if ball.hit_type == BattedBallType.LINEDRIVE: catch_prob *= 0.90
        
        # パークファクター補正
        if stadium: catch_prob /= stadium.pf_1b
        
        catch_prob = max(0.0, min(0.999, catch_prob))
        
        is_caught = random.random() < catch_prob
        
        # ヒットの場合の種類判定 (単打/二塁打/三塁打)
        potential_hit_result = self._judge_hit_type_potential(ball, target_pos, stadium)
        play_value = RUN_VALUES["Out"] * -1 # アウトの価値（負の逆）
        
        # 記録更新
        if best_fielder.position != Position.CATCHER:
            self._update_defensive_metrics(best_fielder, team_level, catch_prob, is_caught, play_value)

        # 結果返却
        if is_caught:
            # エラー判定
            rec = best_fielder.get_record_by_level(team_level)
            
            # ポジション別エラー率基礎値
            pos_err_base = 0.015
            if best_fielder.position in [Position.SHORTSTOP, Position.THIRD]: pos_err_base = 0.025
            
            error_rating = get_effective_stat(best_fielder, 'error')
            
            # エラー率: 0.5% ~ 3.0% 程度
            error_prob = max(0.005, (pos_err_base * 2.0) - (error_rating * 0.0003))
            
            if random.random() < error_prob:
                # エラー発生
                rec.uzr_errr -= (RUN_VALUES["Error"] * UZR_SCALE["ErrR"])
                rec.def_drs_raw -= (RUN_VALUES["Error"] * UZR_SCALE["ErrR"])
                return PlayResult.ERROR
            
            if ball.hit_type == BattedBallType.FLYBALL: return PlayResult.FLYOUT
            if ball.hit_type == BattedBallType.POPUP: return PlayResult.POPUP_OUT
            if ball.hit_type == BattedBallType.LINEDRIVE: return PlayResult.LINEOUT
            
            # ゴロの場合は送球判定へ
            return self._judge_grounder_throw(best_fielder, ball, team_level)
            
        else:
            return potential_hit_result

    def _find_nearest_fielder(self, ball_pos, team, team_level):
        min_dist = 999.0; best_f = None; best_type = ""; best_init = (0,0)
        
        # ロジック統一: どのレベルでも current_lineup (あるいはレベルに応じたラインナップ) を使う
        # LiveGameEngine側で適切に lineup をセットしている前提だが、
        # ここでは念のためレベルに応じて取得する
        if team_level == TeamLevel.SECOND: lineup = team.farm_lineup
        elif team_level == TeamLevel.THIRD: lineup = team.third_lineup
        else: lineup = team.current_lineup
        
        pos_map = {}
        for idx in lineup:
            if 0 <= idx < len(team.players):
                p = team.players[idx]
                if p.position != Position.DH and p.position != Position.PITCHER: pos_map[p.position] = p
        
        pitcher = team.players[team.starting_pitcher_idx] if 0 <= team.starting_pitcher_idx < len(team.players) else team.players[0]
        pos_map[Position.PITCHER] = pitcher

        for pos_enum, coords in FIELD_COORDS.items():
            if pos_enum in pos_map:
                dist = math.sqrt((ball_pos[0] - coords[0])**2 + (ball_pos[1] - coords[1])**2)
                if dist < min_dist:
                    min_dist = dist; best_f = pos_map[pos_enum]; best_type = pos_enum.name; best_init = coords
        return best_f, best_type, best_init

    def _judge_grounder_throw(self, fielder, ball, team_level):
        # 一塁への送球判定
        base_1b_pos = (19.0, 19.0) # 一塁ベース位置
        ball_x = ball.landing_x; ball_y = ball.landing_y
        dist_to_1b = math.sqrt((ball_x - base_1b_pos[0])**2 + (ball_y - base_1b_pos[1])**2)
        
        arm = get_effective_stat(fielder, 'arm')
        
        # 送球速度
        throw_speed = 32 + (arm / 100.0) * 12 # m/s
        
        # 握り替え時間
        transfer_time = 0.7 - (get_effective_stat(fielder, 'error') / 300.0)
        
        throw_time = transfer_time + (dist_to_1b / throw_speed)
        
        # 打者走者の到達時間 (4.0 ~ 4.5秒)
        runner_time = 4.2 # 平均
        
        # 余裕時間
        time_margin = runner_time - throw_time
        rec = fielder.get_record_by_level(team_level)
        
        if throw_time < runner_time:
            # アウト
            if 0 < time_margin < 0.2: # 際どいプレー
                 val = 0.2 * UZR_SCALE["ARM"]
                 rec.def_drs_raw += val; rec.uzr_arm += val
            return PlayResult.GROUNDOUT
        else:
            # 内野安打
            if -0.2 < time_margin < 0:
                 val = -0.1 * UZR_SCALE["ARM"]
                 rec.def_drs_raw += val; rec.uzr_arm += val
            return PlayResult.SINGLE 

    def _judge_hit_type_potential(self, ball, ball_pos, stadium):
        dist = ball.distance
        pf_2b = stadium.pf_2b if stadium else 1.0
        pf_3b = stadium.pf_3b if stadium else 1.0
        
        # 二塁打・三塁打の閾値
        double_threshold = 60.0 / math.sqrt(pf_2b)
        triple_threshold = 100.0 / math.sqrt(pf_3b)
        is_behind_fielder = ball_pos[1] > 80 # 外野深部
        
        if dist > triple_threshold and is_behind_fielder:
             # 三塁打確率 (スピードに依存させるべきだが簡易的に)
             if random.random() < 0.2: return PlayResult.TRIPLE
             return PlayResult.DOUBLE
        if dist > double_threshold:
            if ball.hit_type == BattedBallType.LINEDRIVE: return PlayResult.DOUBLE
            if is_behind_fielder: return PlayResult.DOUBLE
        return PlayResult.SINGLE

    def _update_defensive_metrics(self, fielder, team_level, catch_prob, is_caught, play_value):
        rec = fielder.get_record_by_level(team_level)
        rec.def_opportunities += 1
        rec.def_difficulty_sum += (1.0 - catch_prob)
        
        # UZR (RngR) 簡易計算
        rng_r = 0.0
        if is_caught:
            # 捕った: 難易度が高いほどプラス
            rng_r = (1.0 - catch_prob) * 0.8
            rec.def_plays_made += 1
        else:
            # 捕れなかった: 易しいほどマイナス
            rng_r = (0.0 - catch_prob) * 0.8
            
        rng_r *= UZR_SCALE["RngR"]
        
        rec.def_drs_raw += rng_r
        rec.uzr_rngr += rng_r

    def judge_arm_opportunity(self, ball: BattedBallData, fielder: Player, runner: Player, base_from: int, team_level):
        arm = get_effective_stat(fielder, 'arm')
        runner_speed = get_effective_stat(runner, 'speed')
        
        # 補殺確率
        kill_prob = 0.30 + (arm - 50) * 0.015 - (runner_speed - 50) * 0.01
        kill_prob = max(0.05, min(0.7, kill_prob))
        
        rec = fielder.get_record_by_level(team_level)
        
        if random.random() < 0.25: # クロスプレイ発生率
            if random.random() < kill_prob:
                val = 1.0 * UZR_SCALE["ARM"]
                rec.uzr_arm += val; rec.def_drs_raw += val
                return True # アウト
            else:
                val = -0.5 * UZR_SCALE["ARM"]
                rec.uzr_arm += val; rec.def_drs_raw += val
                return False
        else:
            # 抑止点
            hold_bonus = 0.05 * (arm / 100.0) * UZR_SCALE["ARM"]
            rec.uzr_arm += hold_bonus; rec.def_drs_raw += hold_bonus
            return False

class LiveGameEngine:
    """試合進行エンジン"""
    def __init__(self, home: Team, away: Team, team_level: TeamLevel = TeamLevel.FIRST):
        self.home_team = home; self.away_team = away
        self.team_level = team_level; self.state = GameState()
        self.pitch_gen = PitchGenerator(); self.bat_gen = BattedBallGenerator()
        self.def_eng = AdvancedDefenseEngine(); self.ai = AIManager()
        self.game_stats = defaultdict(lambda: defaultdict(int))
        self.stadium = getattr(self.home_team, 'stadium', None)
        if not self.stadium: self.stadium = Stadium(name=f"{home.name} Stadium")
        self._init_starters()
        
        # 全軍共通でラインナップチェックを行う
        self._ensure_valid_lineup(self.home_team)
        self._ensure_valid_lineup(self.away_team)

    def _ensure_valid_lineup(self, team: Team):
        """ラインナップの不整合を修正 (全軍対応)"""
        # レベルに応じたラインナップ取得
        if self.team_level == TeamLevel.SECOND:
            get_lineup = lambda: team.farm_lineup
            set_lineup = lambda l: setattr(team, 'farm_lineup', l)
            get_roster = team.get_farm_roster_players
        elif self.team_level == TeamLevel.THIRD:
            get_lineup = lambda: team.third_lineup
            set_lineup = lambda l: setattr(team, 'third_lineup', l)
            get_roster = team.get_third_roster_players
        else:
            get_lineup = lambda: team.current_lineup
            set_lineup = lambda l: setattr(team, 'current_lineup', l)
            get_roster = team.get_active_roster_players

        current_lineup = get_lineup()

        # ラインナップ生成が必要な場合
        if not current_lineup or len(current_lineup) < 9:
            players = get_roster()
            # ロースター不足時の救済
            if len(players) < 9:
                 players = [p for p in team.players if p.team_level == self.team_level or p.team_level == TeamLevel.SECOND]
            if len(players) < 9: players = team.players # 最終手段
            
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

    def get_current_catcher(self) -> Optional[Player]:
        team = self.home_team if self.state.is_top else self.away_team
        if self.team_level == TeamLevel.SECOND: lineup = team.farm_lineup
        elif self.team_level == TeamLevel.THIRD: lineup = team.third_lineup
        else: lineup = team.current_lineup
        
        if not lineup: return None
        for p_idx in lineup:
            if team.players[p_idx].position == Position.CATCHER: return team.players[p_idx]
        return None

    def simulate_pitch(self, manual_strategy=None):
        batter, _ = self.get_current_batter()
        pitcher, _ = self.get_current_pitcher()
        catcher = self.get_current_catcher()
        
        defense_team = self.home_team if self.state.is_top else self.away_team
        offense_team = self.away_team if self.state.is_top else self.home_team
        
        strategy = manual_strategy or self.ai.decide_strategy(self.state, offense_team, defense_team, batter)
        pitch_strategy = self.ai.decide_pitch_strategy(self.state, pitcher, batter)
        
        if strategy == "STEAL":
            res = self._attempt_steal(catcher)
            if res: return PitchResult.BALL, None, None

        pitch = self.pitch_gen.generate_pitch(pitcher, batter, catcher, self.state, pitch_strategy, self.stadium)
        if self.state.is_top: self.state.away_pitch_count += 1
        else: self.state.home_pitch_count += 1
        
        # キャッチャーのフレーミング
        if not pitch.location.is_strike and pitch.location.z < 0.15 and catcher:
            catch_err = get_effective_stat(catcher, 'error')
            block_prob = 0.90 + (catch_err - 50) * 0.005
            if random.random() < 0.03: # パスボール発生率
                if random.random() <= block_prob:
                    val = 0.1 * UZR_SCALE["rBlk"]
                    self.game_stats[catcher]['uzr_rblk'] += val; self.game_stats[catcher]['def_drs_raw'] += val
                else:
                    val = -0.5 * UZR_SCALE["rBlk"]
                    self.game_stats[catcher]['uzr_rblk'] += val; self.game_stats[catcher]['def_drs_raw'] += val

        res, ball = self._resolve_contact(batter, pitcher, pitch, strategy)
        self.process_pitch_result(res, pitch, ball, strategy)
        return res, pitch, ball

    def _resolve_contact(self, batter, pitcher, pitch, strategy):
        # 死球判定
        if not pitch.location.is_strike:
            control = get_effective_stat(pitcher, 'control')
            # 死球率: 約0.3%
            if random.random() < (0.003 + max(0, (50-control)*0.0001)): return PitchResult.HIT_BY_PITCH, None

        # バント処理
        if strategy == "BUNT":
            bunt_skill = get_effective_stat(batter, 'bunt_sac')
            difficulty = 20 if not pitch.location.is_strike else 0
            if random.uniform(0, 100) > (bunt_skill - difficulty):
                return PitchResult.FOUL if random.random() < 0.8 else PitchResult.STRIKE_SWINGING, None
            else:
                ball = self.bat_gen.generate(batter, pitcher, pitch, self.state, strategy)
                return PitchResult.IN_PLAY, ball

        # スイング判定
        eye = get_effective_stat(batter, 'eye')
        if pitch.location.is_strike:
            # ゾーン内スイング率: 65-75%
            swing_prob = 0.70 + (eye-50)*0.002
        else:
            # ゾーン外スイング率 (O-Swing%): 25-35%
            swing_prob = 0.30 - (eye-50)*0.004

        if self.state.strikes == 2: swing_prob += 0.15 # 追い込まれると手を出しやすい
        if strategy == "POWER": swing_prob += 0.1 
        if strategy == "MEET": swing_prob -= 0.1
        
        swing_prob = max(0.01, min(0.99, swing_prob))
        
        if random.random() >= swing_prob: return PitchResult.STRIKE_CALLED if pitch.location.is_strike else PitchResult.BALL, None
            
        # コンタクト判定 (空振り or ファウル or インプレー)
        contact = get_effective_stat(batter, 'contact', opponent=pitcher)
        
        # 基礎コンタクト率 (空振りしない確率)
        # NPB平均空振り率: 9-10% -> コンタクト率 90%
        # ゾーン内: 90%, ゾーン外: 60%
        if pitch.location.is_strike:
            hit_prob = 0.88 + (contact - 50)*0.004
        else:
            hit_prob = 0.60 + (contact - 50)*0.005

        if self.stadium: hit_prob /= max(0.5, self.stadium.pf_so)

        if random.random() > hit_prob: return PitchResult.STRIKE_SWINGING, None
        
        # ファウル判定 (インプレーにならなかったもの)
        # コンタクトしたうち、約40-50%はファウル
        foul_prob = 0.45
        if strategy == "MEET": foul_prob += 0.1
        
        if random.random() < foul_prob: return PitchResult.FOUL, None
             
        # インプレー
        ball = self.bat_gen.generate(batter, pitcher, pitch, self.state, strategy)
        return PitchResult.IN_PLAY, ball

    def _attempt_steal(self, catcher):
        runner = self.state.runner_1b
        if not runner: return False
        
        runner_spd = get_effective_stat(runner, 'speed')
        catcher_arm = get_effective_stat(catcher, 'arm') if catcher else 50
        
        # 盗塁成功率目安: 70%
        success_prob = 0.70 + (runner_spd - 50)*0.01 - (catcher_arm - 50)*0.008
        
        catcher_rec = None
        if catcher: catcher_rec = self.game_stats[catcher]

        if random.random() < success_prob:
            self.state.runner_2b = runner; self.state.runner_1b = None
            self.game_stats[runner]['stolen_bases'] += 1
            if catcher_rec: catcher_rec['uzr_rsb'] -= (0.15 * UZR_SCALE["rSB"])
            return True
        else:
            self.state.runner_1b = None; self.state.outs += 1
            self.game_stats[runner]['caught_stealing'] += 1
            if catcher_rec: catcher_rec['uzr_rsb'] += (0.45 * UZR_SCALE["rSB"])
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
            else:
                self._resolve_play(play, strategy, ball)
        return res

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
        for p in scored_players:
            self.game_stats[p]['runs'] += 1
            
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
            
            if play == PlayResult.HOME_RUN:
                scored_players = self._advance_runners(4, batter)
            elif play == PlayResult.SINGLE: scored_players = self._advance_runners(1, batter)
            elif play == PlayResult.DOUBLE: scored_players = self._advance_runners(2, batter)
            elif play == PlayResult.TRIPLE: scored_players = self._advance_runners(3, batter)
            
            for p in scored_players:
                self.game_stats[p]['runs'] += 1
                
            scored = len(scored_players)
            if scored > 0:
                self.game_stats[batter]['rbis'] += scored
                self.game_stats[pitcher]['runs_allowed'] += scored; self.game_stats[pitcher]['earned_runs'] += scored
                self._score(scored)
            return play

        if play == PlayResult.ERROR:
            self.game_stats[batter]['at_bats'] += 1; self.game_stats[batter]['reach_on_error'] += 1
            self._record_pf(batter, pitcher); self._reset_count(); self._next_batter()
            
            scored_players = self._advance_runners(1, batter)
            for p in scored_players:
                self.game_stats[p]['runs'] += 1
            scored = len(scored_players)
            
            if scored > 0:
                self.game_stats[batter]['rbis'] += scored
                self.game_stats[pitcher]['runs_allowed'] += scored
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
             if self.state.is_runner_on(): 
                 is_sac_bunt = True; scored = self._advance_runners_bunt()
        
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
            if sac_scored_runner: self.game_stats[sac_scored_runner]['runs'] += 1
            self._score(scored)
        elif is_sac_bunt:
            self.game_stats[batter]['sacrifice_hits'] += 1
            if scored > 0:
                self.game_stats[batter]['rbis'] += scored
                self.game_stats[pitcher]['runs_allowed'] += scored; self.game_stats[pitcher]['earned_runs'] += scored
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
        """
        走者を進塁させ、得点した選手のリストを返す。
        同時にUBRの計算も行う（プラス・マイナス評価）。
        """
        scored_players = []
        
        # UBR設定
        UBR_SUCCESS_1B3B = 0.18
        UBR_FAIL_1B3B = -0.80
        UBR_HOLD_1B2B = -0.06  
        
        UBR_SUCCESS_2BH = 0.22
        UBR_FAIL_2BH = -1.00
        UBR_HOLD_2B3B = -0.08
        
        UBR_SUCCESS_1BH = 0.35 
        UBR_FAIL_1BH = -1.20
        UBR_HOLD_1B3B = -0.07

        if is_walk:
            if self.state.runner_1b:
                if self.state.runner_2b:
                    if self.state.runner_3b: 
                        scored_players.append(self.state.runner_3b) # 押し出し
                    self.state.runner_3b = self.state.runner_3b if self.state.runner_3b else self.state.runner_2b
                self.state.runner_2b = self.state.runner_2b if self.state.runner_2b else self.state.runner_1b
            self.state.runner_1b = batter
        else:
            # 3塁ランナー
            if self.state.runner_3b:
                scored_players.append(self.state.runner_3b)
                self.state.runner_3b = None
            
            # 2塁ランナー
            if self.state.runner_2b:
                if bases >= 2: # 二塁打以上で生還
                    scored_players.append(self.state.runner_2b)
                    self.state.runner_2b = None
                elif bases == 1: # 単打
                    # 生還判定 (UBR)
                    spd = get_effective_stat(self.state.runner_2b, 'speed')
                    br = get_effective_stat(self.state.runner_2b, 'baserunning')
                    
                    attempt_prob = 0.40 + (spd - 50) * 0.015 + (br - 50) * 0.005
                    
                    if random.random() < attempt_prob:
                        if random.random() < 0.05: # アウト！
                            self.game_stats[self.state.runner_2b]['ubr_val'] += UBR_FAIL_2BH
                            self.state.runner_2b = None
                            self.state.outs += 1 
                        else:
                            scored_players.append(self.state.runner_2b)
                            self.game_stats[self.state.runner_2b]['ubr_val'] += UBR_SUCCESS_2BH
                            self.state.runner_2b = None
                    else:
                        # 自重 (3塁止まり)
                        self.state.runner_3b = self.state.runner_2b
                        self.game_stats[self.state.runner_2b]['ubr_val'] += UBR_HOLD_2B3B
                        self.state.runner_2b = None

            # 1塁ランナー
            if self.state.runner_1b:
                if bases >= 3: # 三塁打以上
                    scored_players.append(self.state.runner_1b)
                    self.state.runner_1b = None
                elif bases == 2: # 二塁打
                    # 生還判定 (UBR)
                    spd = get_effective_stat(self.state.runner_1b, 'speed')
                    br = get_effective_stat(self.state.runner_1b, 'baserunning')
                    
                    attempt_prob = 0.35 + (spd - 50) * 0.015 + (br - 50) * 0.005
                    
                    if random.random() < attempt_prob:
                        if random.random() < 0.05: # アウト
                            self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_FAIL_1BH
                            self.state.runner_1b = None
                            self.state.outs += 1
                        else:
                            scored_players.append(self.state.runner_1b)
                            self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_SUCCESS_1BH
                            self.state.runner_1b = None
                    else:
                        # 自重 (3塁止まり)
                        self.state.runner_3b = self.state.runner_1b
                        self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_HOLD_1B3B
                        self.state.runner_1b = None
                elif bases == 1: # 単打
                    # 3塁進塁判定 (UBR)
                    spd = get_effective_stat(self.state.runner_1b, 'speed')
                    br = get_effective_stat(self.state.runner_1b, 'baserunning')
                    
                    attempt_prob = 0.25 + (spd - 50) * 0.015 + (br - 50) * 0.005
                    
                    # 前のランナーが3塁に止まっていないことが前提
                    if self.state.runner_3b is None and random.random() < attempt_prob:
                        if random.random() < 0.05: # アウト
                            self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_FAIL_1B3B
                            self.state.runner_1b = None
                            self.state.outs += 1
                        else:
                            self.state.runner_3b = self.state.runner_1b
                            self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_SUCCESS_1B3B
                            self.state.runner_1b = None
                    else:
                        # 自重 (2塁止まり)
                        self.state.runner_2b = self.state.runner_1b
                        self.game_stats[self.state.runner_1b]['ubr_val'] += UBR_HOLD_1B2B
                        self.state.runner_1b = None

            # 打者走者
            if bases == 4: # HR
                scored_players.append(batter)
            elif bases == 3:
                self.state.runner_3b = batter
            elif bases == 2:
                self.state.runner_2b = batter
            elif bases == 1:
                self.state.runner_1b = batter
                
        return scored_players
    
    # ... (score, reset_count, next_batter, change_inning, is_game_over, finalize_game_stats, get_winner) ...
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
        win_p, loss_p = None, None
        if not self.state.home_pitchers_used or not self.state.away_pitchers_used: return

        if self.state.home_score > self.state.away_score:
            starter = self.state.home_pitchers_used[0]
            if self.game_stats[starter]['innings_pitched'] >= 5: win_p = starter
            else: win_p = self.state.home_pitchers_used[-1]
            loss_p = self.state.away_pitchers_used[0]
        elif self.state.away_score > self.state.home_score:
            starter = self.state.away_pitchers_used[0]
            if self.game_stats[starter]['innings_pitched'] >= 5: win_p = starter
            else: win_p = self.state.away_pitchers_used[-1]
            loss_p = self.state.home_pitchers_used[0]

        if win_p: self.game_stats[win_p]['wins'] = 1
        if loss_p: self.game_stats[loss_p]['losses'] = 1

        for player, stats in self.game_stats.items():
            record = player.get_record_by_level(self.team_level)
            for key, val in stats.items():
                if hasattr(record, key):
                    current = getattr(record, key)
                    setattr(record, key, current + val)
            record.games += 1
            
            is_home_player = player in self.home_team.players
            if is_home_player:
                if player.position == Position.PITCHER:
                    record.home_games_pitched += 1
                else:
                    record.home_games += 1

    def get_winner(self):
        if self.state.home_score > self.state.away_score: return self.home_team.name
        if self.state.away_score > self.state.home_score: return self.away_team.name
        return "DRAW"