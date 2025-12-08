# -*- coding: utf-8 -*-
"""
ライブ試合エンジン (修正版: ホームラン数微減調整 + バグ修正・機能維持)
"""
import random
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict
from enum import Enum
from models import Position, Player, Team, PlayerRecord, PitchType, TeamLevel, generate_best_lineup

# ========================================
# 定数・ユーティリティ
# ========================================

STRIKE_ZONE = {
    'width': 0.432, # 17インチ (約43cm)
    'height': 0.56, # 一般的なストライクゾーンの高さ
    'center_x': 0.0,
    'center_z': 0.75, # 地面から75cm中心
    'half_width': 0.216,
    'half_height': 0.28
}

def get_rank(value: int) -> str:
    """能力値をランクに変換"""
    if value >= 90: return "S"
    if value >= 80: return "A"
    if value >= 70: return "B"
    if value >= 60: return "C"
    if value >= 50: return "D"
    if value >= 40: return "E"
    if value >= 30: return "F"
    return "G"

def get_effective_stat(player: Player, stat_name: str, opponent: Optional[Player] = None, is_risp: bool = False, is_close_game: bool = False) -> float:
    """
    状況と調子を考慮した有効能力値を計算
    """
    # 1. 基本値の取得
    if not hasattr(player.stats, stat_name):
        return 50.0
    base_value = getattr(player.stats, stat_name)
    
    # 2. 調子による補正 (基準5, 1につき±2%)
    condition_diff = player.condition - 5
    condition_multiplier = 1.0 + (condition_diff * 0.02)
    
    value = base_value * condition_multiplier
    
    # 3. 特殊能力補正
    # --- 打者 ---
    if player.position != Position.PITCHER:
        # 対左投手
        if stat_name in ['contact', 'power'] and opponent and opponent.position == Position.PITCHER:
            vs_left = getattr(player.stats, 'vs_left_batter', 50)
            value += (vs_left - 50) * 0.2

        # チャンス
        if is_risp and stat_name in ['contact', 'power']:
            chance = getattr(player.stats, 'chance', 50)
            value += (chance - 50) * 0.5
            
        # メンタル (接戦時)
        if is_close_game:
            mental = getattr(player.stats, 'mental', 50)
            value += (mental - 50) * 0.3

    # --- 投手 ---
    else:
        # 対左打者
        if opponent and opponent.position != Position.PITCHER:
            vs_left = getattr(player.stats, 'vs_left_pitcher', 50)
            value += (vs_left - 50) * 0.2
            
        # 対ピンチ
        if is_risp:
            pinch = getattr(player.stats, 'vs_pinch', 50)
            if stat_name in ['stuff', 'movement', 'control']:
                value += (pinch - 50) * 0.5
                
        # 安定感
        if stat_name == 'control':
            stability = getattr(player.stats, 'stability', 50)
            if condition_diff < 0:
                mitigation = (stability - 50) * 0.2
                value += max(0, mitigation)

    return max(1.0, value)

# ========================================
# 列挙型
# ========================================

class PitchResult(Enum):
    BALL = "ボール"
    STRIKE_CALLED = "見逃し"
    STRIKE_SWINGING = "空振り"
    FOUL = "ファウル"
    IN_PLAY = "インプレー"
    HIT_BY_PITCH = "死球"

class BattedBallType(Enum):
    GROUNDBALL = "ゴロ"
    LINEDRIVE = "ライナー"
    FLYBALL = "フライ"
    POPUP = "内野フライ"

class PlayResult(Enum):
    SINGLE = "安打"
    DOUBLE = "二塁打"
    TRIPLE = "三塁打"
    HOME_RUN = "本塁打"
    INFIELD_HIT = "内野安打"
    STRIKEOUT = "三振"
    GROUNDOUT = "ゴロ"
    FLYOUT = "フライ"
    LINEOUT = "ライナー"
    POPUP_OUT = "内野フライ"
    DOUBLE_PLAY = "併殺打"
    WALK = "四球"
    HIT_BY_PITCH = "死球"
    SACRIFICE_FLY = "犠飛"
    SACRIFICE_BUNT = "犠打"
    STOLEN_BASE = "盗塁成功"
    CAUGHT_STEALING = "盗塁死"
    ERROR = "失策"
    
    # 内部処理用
    FOUL = "ファウル"
    BALL = "ボール"
    STRIKE = "ストライク"

# ========================================
# データクラス
# ========================================

@dataclass
class PitchLocation:
    x: float
    z: float
    is_strike: bool

@dataclass
class PitchData:
    pitch_type: str
    velocity: float
    spin_rate: int
    horizontal_break: float
    vertical_break: float
    location: PitchLocation
    release_point: Tuple[float, float, float]
    trajectory: List[Tuple[float, float, float]] = field(default_factory=list)

@dataclass
class BattedBallData:
    exit_velocity: float
    launch_angle: float
    spray_angle: float
    hit_type: BattedBallType
    distance: float
    hang_time: float
    landing_x: float
    landing_y: float
    trajectory: List[Tuple[float, float, float]] = field(default_factory=list)
    contact_quality: str = "medium"

@dataclass
class GameState:
    inning: int = 1
    is_top: bool = True
    outs: int = 0
    balls: int = 0
    strikes: int = 0
    
    runner_1b: Optional[Player] = None 
    runner_2b: Optional[Player] = None
    runner_3b: Optional[Player] = None
    
    home_score: int = 0
    away_score: int = 0
    
    home_batter_order: int = 0
    away_batter_order: int = 0
    
    home_pitcher_idx: int = 0
    away_pitcher_idx: int = 0
    
    # スタミナ (0-100)
    home_pitcher_stamina: float = 100.0
    away_pitcher_stamina: float = 100.0
    
    home_pitch_count: int = 0
    away_pitch_count: int = 0

    # 登板済み投手リスト
    home_pitchers_used: List[Player] = field(default_factory=list)
    away_pitchers_used: List[Player] = field(default_factory=list)

    def is_runner_on(self) -> bool:
        return any([self.runner_1b, self.runner_2b, self.runner_3b])

    def is_risp(self) -> bool:
        return (self.runner_2b is not None) or (self.runner_3b is not None)

    def current_pitcher_stamina(self) -> float:
        # 表（is_top=True）はホーム投手が投げている
        return self.home_pitcher_stamina if self.is_top else self.away_pitcher_stamina

# ========================================
# AI マネージャー
# ========================================

class AIManager:
    """AIによる采配決定"""
    
    def decide_strategy(self, state: GameState, offense_team, defense_team, batter: Player) -> str:
        score_diff = state.away_score - state.home_score if state.is_top else state.home_score - state.away_score
        is_late = state.inning >= 7
        is_close = abs(score_diff) <= 2
        
        # バント職人
        bunt_skill = get_effective_stat(batter, 'bunt_sac')
        
        if state.outs == 0 and (state.runner_1b or state.runner_2b) and not state.runner_3b:
            batting_ab = batter.stats.overall_batting()
            if (is_close and is_late) or (bunt_skill > 70 and batting_ab < 45):
                return "BUNT"
        
        # 盗塁
        if state.runner_1b and not state.runner_2b and not state.runner_3b and state.outs < 2:
            runner_spd = get_effective_stat(state.runner_1b, 'speed')
            runner_stl = get_effective_stat(state.runner_1b, 'steal')
            
            steal_threshold = 80
            if is_close and is_late: steal_threshold = 70
            
            if runner_spd >= steal_threshold and runner_stl >= 60:
                if random.random() < 0.25:
                    return "STEAL"
        
        # 強振
        eff_power = get_effective_stat(batter, 'power', is_risp=state.is_risp())
        if state.balls >= 3 and state.strikes < 2 and eff_power > 65: 
            return "POWER"
        
        # ミート打ち
        eff_contact = get_effective_stat(batter, 'contact', is_risp=state.is_risp())
        eff_avoid_k = get_effective_stat(batter, 'avoid_k')
        if state.strikes == 2 and eff_contact > 50 and eff_avoid_k > 50:
            return "MEET"
            
        return "SWING"

    def decide_pitch_strategy(self, state: GameState, pitcher: Player, batter: Player) -> str:
        eff_control = get_effective_stat(pitcher, 'control', opponent=batter, is_risp=state.is_risp())
        
        if state.balls >= 3:
            return "STRIKE" 
        
        if state.strikes == 2:
            has_breaking = len(pitcher.stats.pitches) > 0
            if has_breaking and eff_control > 40:
                return "BALL"
        
        eff_power = get_effective_stat(batter, 'power', is_risp=state.is_risp())
        if state.is_risp() and not state.runner_1b and eff_power > 85 and state.inning >= 8 and abs(state.home_score - state.away_score) <= 1:
            return "WALK"

        return "NORMAL"

# ========================================
# 投球・打球エンジン
# ========================================

class PitchGenerator:
    PITCH_DATA = {
        "ストレート": {"base_speed": 148, "h_break": 0, "v_break": 10},
        "ツーシーム": {"base_speed": 145, "h_break": 12, "v_break": 2},
        "カットボール": {"base_speed": 140, "h_break": -8, "v_break": 3},
        "スライダー": {"base_speed": 132, "h_break": -20, "v_break": -3},
        "カーブ":     {"base_speed": 115, "h_break": -12, "v_break": -25},
        "フォーク":   {"base_speed": 136, "h_break": 0, "v_break": -30},
        "チェンジアップ": {"base_speed": 128, "h_break": 8, "v_break": -15},
        "シュート":   {"base_speed": 140, "h_break": 18, "v_break": -6},
        "シンカー":   {"base_speed": 142, "h_break": 15, "v_break": -10},
        "スプリット": {"base_speed": 140, "h_break": 3, "v_break": -28}
    }

    def generate_pitch(self, pitcher: Player, batter: Player, catcher: Player, state: GameState, strategy="NORMAL") -> PitchData:
        is_risp = state.is_risp()
        is_close = abs(state.home_score - state.away_score) <= 2
        
        velocity = get_effective_stat(pitcher, 'velocity', batter, is_risp, is_close)
        control = get_effective_stat(pitcher, 'control', batter, is_risp, is_close)
        movement = get_effective_stat(pitcher, 'movement', batter, is_risp, is_close)
        
        if catcher:
            lead = get_effective_stat(catcher, 'catcher_lead', is_close_game=is_close)
            control += (lead - 50) * 0.2
        
        current_stamina = state.current_pitcher_stamina()
        fatigue = 1.0
        if current_stamina < 30:
            fatigue = 0.9 + (current_stamina / 300.0)
        if current_stamina <= 0:
            fatigue = 0.8
        
        pitch_cost = 0.5
        if is_risp: pitch_cost *= 1.2
        
        # スタミナ減少対象を表裏で正しく切り替え
        if state.is_top: 
            state.home_pitcher_stamina = max(0, state.home_pitcher_stamina - pitch_cost)
        else: 
            state.away_pitcher_stamina = max(0, state.away_pitcher_stamina - pitch_cost)
        
        pitch_type = None
        breaking_balls = getattr(pitcher.stats, 'breaking_balls', [])
        
        if strategy == "WALK":
            pitch_type = "ストレート"
        elif not breaking_balls:
            pitch_type = "ストレート"
        else:
            straight_prob = max(0.4, 0.7 - len(breaking_balls) * 0.1)
            if state.strikes == 2: straight_prob *= 0.7
            
            if random.random() < straight_prob:
                pitch_type = "ストレート"
            else:
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
                else:
                    pitch_type = breaking_balls[0]
            
        base = self.PITCH_DATA.get(pitch_type, self.PITCH_DATA["ストレート"])
        
        base_velo = velocity * fatigue
        if pitch_type != "ストレート":
            speed_ratio = base["base_speed"] / 148.0
            base_velo *= speed_ratio
            
        velo = random.gauss(base_velo, 1.5)
        velo = max(80, min(170, velo))
        
        move_factor = 1.0 + (movement - 50) * 0.01
        h_brk = base["h_break"] * move_factor + random.gauss(0, 2)
        v_brk = base["v_break"] * move_factor + random.gauss(0, 2)
        
        loc = self._calc_location(control * fatigue, state, strategy)
        traj = self._calc_traj(velo, h_brk, v_brk, loc)
        
        return PitchData(pitch_type, round(velo,1), 2200, h_brk, v_brk, loc, (0,18.44,1.8), traj)

    def _calc_location(self, control, state, strategy):
        if strategy == "WALK":
            return PitchLocation(1.0, 1.5, False)

        sigma = max(0.05, 0.25 - (control * 0.002))
        tx, tz = 0, STRIKE_ZONE['center_z']
        
        if strategy == "STRIKE":
            sigma *= 0.8
        elif strategy == "BALL":
            if random.random() < 0.6: tz -= 0.25
            else: tx = 0.25 if random.random() < 0.5 else -0.25
        else:
            if random.random() < 0.7:
                tx = random.choice([-0.2, 0.2])
                tz += random.choice([-0.2, 0.2])
                
        ax = random.gauss(tx, sigma)
        az = random.gauss(tz, sigma)
        
        is_strike = (abs(ax) <= STRIKE_ZONE['half_width'] + 0.036 and
                     abs(az - STRIKE_ZONE['center_z']) <= STRIKE_ZONE['half_height'] + 0.036)
                     
        return PitchLocation(ax, az, is_strike)

    def _calc_traj(self, velo, hb, vb, loc):
        path = []
        start = (random.uniform(-0.05, 0.05), 18.44, 1.8)
        end = (loc.x, 0, loc.z)
        steps = 15
        for i in range(steps + 1):
            t = i/steps
            x = start[0] + (end[0]-start[0])*t + (hb/100 * 0.3)*math.sin(t*math.pi)
            y = start[1] * (1-t)
            z = start[2] + (end[2]-start[2])*t + (vb/100 * 0.3)*(t**2)
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
        
        p_movement = get_effective_stat(pitcher, 'movement', opponent=batter, is_risp=is_risp)
        p_gb_tendency = getattr(pitcher.stats, 'gb_tendency', 50)
        
        meet_bonus = 0
        if strategy == "MEET": meet_bonus = 15
        if strategy == "POWER": meet_bonus = -20 
        
        ball_penalty = 0 if pitch.location.is_strike else 20
        con_eff = contact + meet_bonus - (p_movement - 50) * 0.4 - ball_penalty
        
        quality_roll = random.uniform(0, 100)
        
        # ハードコンタクトの基準 (標準的)
        if quality_roll < con_eff * 0.35: quality = "hard"
        elif quality_roll < con_eff * 0.85: quality = "medium"
        else: quality = "soft"
        
        # 【再修正】打球速度の微調整 (103 + ... に戻しつつ係数調整)
        base_v = 101 + (power - 50) * 0.68
        
        if strategy == "POWER": base_v += 9
        
        # ハードコンタクトボーナス
        if quality == "hard": base_v += 18 + (power/12)
        if quality == "soft": base_v -= 30
        
        traj_bias = 5 + (trajectory * 5)
        gb_effect = (p_gb_tendency - 50) * 0.2
        angle_center = traj_bias - gb_effect
        
        if pitch.location.z < 0.5: angle_center -= 5
        if pitch.location.z > 0.9: angle_center += 5
        
        if gap > 60 and quality != "soft":
            if random.random() < (gap/150):
                angle_center = 15
        
        if strategy == "BUNT":
            angle = -20
            velo = 30 + random.uniform(-5, 5)
            bunt_skill = get_effective_stat(batter, 'bunt_sac')
            if random.uniform(0, 100) > bunt_skill:
                if random.random() < 0.5: angle = 30
                else: velo += 20
            quality = "soft"
        else:
            angle = random.gauss(angle_center, 12)
        
        velo = max(40, base_v + random.gauss(0, 5))
        if quality == "hard": velo = max(velo, 120)
        
        if angle < 7: htype = BattedBallType.GROUNDBALL
        elif angle < 20: htype = BattedBallType.LINEDRIVE
        elif angle < 50: htype = BattedBallType.FLYBALL
        else: htype = BattedBallType.POPUP
        
        v_ms = velo / 3.6
        dist = (v_ms**2 * math.sin(math.radians(2 * angle))) / 9.8
        
        if htype == BattedBallType.GROUNDBALL:
            dist *= 0.5
        elif htype == BattedBallType.POPUP:
            dist *= 0.3
        else:
            # 【再修正】飛距離減衰を 0.84 に微調整 (前回0.86, 前々回0.82の間)
            dist *= 0.84
            dist *= (1.0 + (power-50)*0.0022)
            
        dist = max(0, dist)
        spray = random.gauss(0, 25)
        
        rad = math.radians(spray)
        land_x = dist * math.sin(rad)
        land_y = dist * math.cos(rad)
        
        return BattedBallData(velo, angle, spray, htype, dist, 4.0, land_x, land_y, [], quality)

class DefenseEngine:
    # team_level引数を追加
    def judge(self, ball: BattedBallData, defense_team: Team, team_level: TeamLevel = TeamLevel.FIRST):
        abs_spray = abs(ball.spray_angle)
        fence_dist = 122 - (abs_spray / 45.0) * (122 - 100)
        
        if ball.hit_type == BattedBallType.FLYBALL and ball.distance > fence_dist and abs_spray < 45:
            return PlayResult.HOME_RUN
        
        if abs_spray > 45:
            return PlayResult.FOUL
            
        fielder, position_name = self._get_responsible_fielder(ball, defense_team, team_level)
        
        if fielder:
            defense_range = getattr(fielder.stats, 'defense_ranges', {}).get(position_name, 1)
            defense_range = defense_range * (1.0 + (fielder.condition - 5) * 0.02)
            error_rating = get_effective_stat(fielder, 'error')
        else:
            defense_range = 1
            error_rating = 1
            
        hit_prob = 0.0
        
        # ヒット確率 (打高傾向を維持)
        if ball.hit_type == BattedBallType.GROUNDBALL:
            hit_prob = 0.30
            if ball.distance < 45:
                 hit_prob -= (defense_range - 50) * 0.01
            else:
                 hit_prob = 0.62
                 
        elif ball.hit_type == BattedBallType.LINEDRIVE:
            hit_prob = 0.65
            hit_prob -= (defense_range - 50) * 0.005
            
        elif ball.hit_type == BattedBallType.FLYBALL:
            hit_prob = 0.18
            hit_prob -= (defense_range - 50) * 0.005
            
        elif ball.hit_type == BattedBallType.POPUP:
            hit_prob = 0.01
        
        if ball.contact_quality == "hard": hit_prob += 0.25
        if ball.contact_quality == "soft": hit_prob -= 0.1
        
        is_hit = random.random() < hit_prob
        
        if is_hit:
            if ball.distance > 100 or (ball.distance > 80 and ball.hit_type == BattedBallType.LINEDRIVE):
                if random.random() < 0.1: return PlayResult.TRIPLE
                return PlayResult.DOUBLE
            return PlayResult.SINGLE
        else:
            error_prob = max(0.001, 0.02 - (error_rating * 0.0002))
            if random.random() < error_prob:
                return PlayResult.ERROR
            
            if ball.hit_type == BattedBallType.GROUNDBALL: return PlayResult.GROUNDOUT
            if ball.hit_type == BattedBallType.LINEDRIVE: return PlayResult.LINEOUT
            if ball.hit_type == BattedBallType.POPUP: return PlayResult.POPUP_OUT
            return PlayResult.FLYOUT

    def _get_responsible_fielder(self, ball: BattedBallData, team: Team, team_level: TeamLevel) -> Tuple[Optional[Player], str]:
        angle = ball.spray_angle
        dist = ball.distance
        pos_enum = Position
        
        if dist < 45 or ball.hit_type == BattedBallType.GROUNDBALL:
            if angle < -20: return self._get_player_by_pos(team, pos_enum.THIRD, team_level), pos_enum.THIRD.value
            elif angle < -5: return self._get_player_by_pos(team, pos_enum.SHORTSTOP, team_level), pos_enum.SHORTSTOP.value
            elif angle < 15: return self._get_player_by_pos(team, pos_enum.SECOND, team_level), pos_enum.SECOND.value
            else: return self._get_player_by_pos(team, pos_enum.FIRST, team_level), pos_enum.FIRST.value
        else:
            lineup = self._get_lineup_by_level(team, team_level)
            outfielders = [team.players[i] for i in lineup if 0 <= i < len(team.players) and team.players[i].position == pos_enum.OUTFIELD]
            
            if not outfielders: return None, "外野手"
            
            idx = 0
            if angle < -15: idx = 0
            elif angle > 15: idx = min(2, len(outfielders)-1)
            else: idx = min(1, len(outfielders)-1)
            
            return outfielders[idx], pos_enum.OUTFIELD.value

    def _get_player_by_pos(self, team: Team, pos: Position, team_level: TeamLevel) -> Optional[Player]:
        lineup = self._get_lineup_by_level(team, team_level)
        for idx in lineup:
            if 0 <= idx < len(team.players):
                p = team.players[idx]
                if p.position == pos:
                    return p
        return None

    def _get_lineup_by_level(self, team: Team, level: TeamLevel) -> List[int]:
        if level == TeamLevel.SECOND:
            return team.farm_lineup
        elif level == TeamLevel.THIRD:
            return team.third_lineup
        else:
            return team.current_lineup

# ========================================
# 統合エンジン
# ========================================

class LiveGameEngine:
    def __init__(self, home: Team, away: Team, team_level: TeamLevel = TeamLevel.FIRST):
        self.home_team = home
        self.away_team = away
        self.team_level = team_level
        self.state = GameState()
        self.pitch_gen = PitchGenerator()
        self.bat_gen = BattedBallGenerator()
        self.def_eng = DefenseEngine()
        self.ai = AIManager()
        
        self.game_stats = defaultdict(lambda: defaultdict(int))
        self._init_starters()

        # オーダーが守備適正を考慮していない（CPU生成など）場合は自動修正する
        if self.team_level == TeamLevel.FIRST:
            self._ensure_valid_lineup(self.home_team)
            self._ensure_valid_lineup(self.away_team)

    def _ensure_valid_lineup(self, team: Team):
        """オーダーをチェックし、不整合（特に捕手がいない等）があれば最適化する"""
        if not team.current_lineup or len(team.current_lineup) < 9:
            players = team.get_active_roster_players()
            new_lineup = generate_best_lineup(team, players)
            team.current_lineup = new_lineup
            return

        has_valid_catcher = False
        catcher_idx = -1
        if hasattr(team, 'lineup_positions') and len(team.lineup_positions) == 9:
            for i, pos_str in enumerate(team.lineup_positions):
                if pos_str in ["捕", "捕手"]:
                    catcher_idx = team.current_lineup[i]
                    break
        
        if catcher_idx == -1:
            for idx in team.current_lineup:
                if 0 <= idx < len(team.players):
                    p = team.players[idx]
                    if p.position == Position.CATCHER:
                        has_valid_catcher = True
                        break
        else:
            if 0 <= catcher_idx < len(team.players):
                p = team.players[catcher_idx]
                if p.stats.get_defense_range(Position.CATCHER) >= 20:
                    has_valid_catcher = True

        if not has_valid_catcher:
            players = team.get_active_roster_players()
            batters = [p for p in players if p.position != Position.PITCHER]
            new_lineup = generate_best_lineup(team, batters)
            team.current_lineup = new_lineup

    def _init_starters(self):
        hp = self.home_team.get_today_starter() or self.home_team.players[0]
        ap = self.away_team.get_today_starter() or self.away_team.players[0]
        
        try:
            self.state.home_pitcher_idx = self.home_team.players.index(hp)
        except ValueError:
            self.state.home_pitcher_idx = 0
            hp = self.home_team.players[0]
            
        try:
            self.state.away_pitcher_idx = self.away_team.players.index(ap)
        except ValueError:
            self.state.away_pitcher_idx = 0
            ap = self.away_team.players[0]

        self.state.home_pitchers_used.append(hp)
        self.state.away_pitchers_used.append(ap)
        
        self.game_stats[hp]['games_pitched'] = 1
        self.game_stats[ap]['games_pitched'] = 1
        self.game_stats[hp]['games_started'] = 1
        self.game_stats[ap]['games_started'] = 1

    def get_current_batter(self) -> Tuple[Player, int]:
        team = self.away_team if self.state.is_top else self.home_team
        order_idx = self.state.away_batter_order if self.state.is_top else self.state.home_batter_order
        
        lineup = team.current_lineup
        if self.team_level == TeamLevel.SECOND: lineup = team.farm_lineup
        elif self.team_level == TeamLevel.THIRD: lineup = team.third_lineup
        
        if not lineup: 
            return team.players[0], 0
        
        p_idx = lineup[order_idx % len(lineup)]
        return team.players[p_idx], order_idx

    def get_current_pitcher(self) -> Tuple[Player, int]:
        team = self.home_team if self.state.is_top else self.away_team
        idx = self.state.home_pitcher_idx if self.state.is_top else self.state.away_pitcher_idx
        return team.players[idx], idx

    def get_current_catcher(self) -> Optional[Player]:
        team = self.home_team if self.state.is_top else self.away_team
        lineup = team.current_lineup
        if self.team_level == TeamLevel.SECOND: lineup = team.farm_lineup
        elif self.team_level == TeamLevel.THIRD: lineup = team.third_lineup
        
        if not lineup: return None
        for p_idx in lineup:
            if 0 <= p_idx < len(team.players) and team.players[p_idx].position == Position.CATCHER:
                return team.players[p_idx]
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

        pitch = self.pitch_gen.generate_pitch(pitcher, batter, catcher, self.state, pitch_strategy)
        
        if self.state.is_top: self.state.away_pitch_count += 1
        else: self.state.home_pitch_count += 1
        
        res, ball = self._resolve_contact(batter, pitcher, pitch, strategy)
        self.process_pitch_result(res, pitch, ball)
        
        return res, pitch, ball

    def _resolve_contact(self, batter, pitcher, pitch, strategy):
        if strategy == "BUNT":
            bunt_skill = get_effective_stat(batter, 'bunt_sac')
            difficulty = 20 if not pitch.location.is_strike else 0
            if random.uniform(0, 100) > (bunt_skill - difficulty):
                return PitchResult.FOUL if random.random() < 0.8 else PitchResult.STRIKE_SWINGING, None
            else:
                ball = self.bat_gen.generate(batter, pitcher, pitch, self.state, strategy)
                return PitchResult.IN_PLAY, ball

        eye = get_effective_stat(batter, 'eye')
        swing_prob = 0.75 if pitch.location.is_strike else (0.40 - (eye - 50) * 0.01)
        if self.state.strikes == 2: swing_prob += 0.3
        
        if random.random() >= swing_prob:
            return PitchResult.STRIKE_CALLED if pitch.location.is_strike else PitchResult.BALL, None
            
        contact = get_effective_stat(batter, 'contact', opponent=pitcher)
        hit_prob = 0.78 + (contact - 50)*0.005
        if not pitch.location.is_strike: hit_prob -= 0.2
        
        if random.random() > hit_prob:
            return PitchResult.STRIKE_SWINGING, None
            
        if random.random() < 0.35:
             return PitchResult.FOUL, None
             
        ball = self.bat_gen.generate(batter, pitcher, pitch, self.state, strategy)
        return PitchResult.IN_PLAY, ball

    def _attempt_steal(self, catcher):
        runner = self.state.runner_1b
        if not runner: return False
        
        runner_spd = get_effective_stat(runner, 'speed')
        catcher_arm = get_effective_stat(catcher, 'arm') if catcher else 50
        
        success_prob = 0.70 + (runner_spd - 50)*0.01 - (catcher_arm - 50)*0.01
        
        if random.random() < success_prob:
            self.state.runner_2b = runner; self.state.runner_1b = None
            self.game_stats[runner]['stolen_bases'] += 1
            return True
        else:
            self.state.runner_1b = None; self.state.outs += 1
            self.game_stats[runner]['caught_stealing'] += 1
            return True

    def process_pitch_result(self, res, pitch, ball):
        pitcher, _ = self.get_current_pitcher()
        
        if res == PitchResult.BALL:
            self.state.balls += 1
            if self.state.balls >= 4: self._walk()
        elif res in [PitchResult.STRIKE_CALLED, PitchResult.STRIKE_SWINGING]:
            self.state.strikes += 1
            if self.state.strikes >= 3: 
                self.game_stats[pitcher]['strikeouts_pitched'] += 1
                self._out(PlayResult.STRIKEOUT)
        elif res == PitchResult.FOUL:
            if self.state.strikes < 2: self.state.strikes += 1
        elif res == PitchResult.IN_PLAY:
            defense_team = self.home_team if self.state.is_top else self.away_team
            play = self.def_eng.judge(ball, defense_team, self.team_level)
            if play == PlayResult.FOUL:
                if self.state.strikes < 2: self.state.strikes += 1
            else:
                self._resolve_play(play)
        
        if res == PitchResult.IN_PLAY:
            defense_team = self.home_team if self.state.is_top else self.away_team
            return self.def_eng.judge(ball, defense_team, self.team_level)
        return res

    def _walk(self):
        batter, _ = self.get_current_batter()
        pitcher, _ = self.get_current_pitcher()
        self.game_stats[batter]['plate_appearances'] += 1
        self.game_stats[batter]['walks'] += 1
        self.game_stats[pitcher]['walks_allowed'] += 1
        
        self._advance_runners(1, batter, is_walk=True)
        self._reset_count()
        self._next_batter()

    def _out(self, kind=PlayResult.STRIKEOUT):
        batter, _ = self.get_current_batter()
        pitcher, _ = self.get_current_pitcher()
        self.game_stats[batter]['plate_appearances'] += 1
        self.game_stats[batter]['at_bats'] += 1
        if kind == PlayResult.STRIKEOUT:
            self.game_stats[batter]['strikeouts'] += 1
        
        self.state.outs += 1
        self.game_stats[pitcher]['innings_pitched'] += 0.333
        
        self._reset_count()
        self._next_batter()
        if self.state.outs >= 3: self._change_inning()

    def _resolve_play(self, play):
        batter, _ = self.get_current_batter()
        pitcher, _ = self.get_current_pitcher()
        
        self.game_stats[batter]['plate_appearances'] += 1
        self.game_stats[batter]['at_bats'] += 1
        
        if play in [PlayResult.SINGLE, PlayResult.DOUBLE, PlayResult.TRIPLE, PlayResult.HOME_RUN]:
            self.game_stats[batter]['hits'] += 1
            self.game_stats[pitcher]['hits_allowed'] += 1
            if play == PlayResult.DOUBLE: self.game_stats[batter]['doubles'] += 1
            if play == PlayResult.TRIPLE: self.game_stats[batter]['triples'] += 1
            if play == PlayResult.HOME_RUN: 
                self.game_stats[batter]['home_runs'] += 1
                self.game_stats[pitcher]['home_runs_allowed'] += 1

        self._reset_count()
        self._next_batter()
        
        scored = 0
        if play == PlayResult.HOME_RUN:
            scored = 1 + (1 if self.state.runner_1b else 0) + (1 if self.state.runner_2b else 0) + (1 if self.state.runner_3b else 0)
            self.state.runner_1b = self.state.runner_2b = self.state.runner_3b = None
        elif play == PlayResult.SINGLE:
            scored = self._advance_runners(1, batter)
        elif play == PlayResult.DOUBLE:
            scored = self._advance_runners(2, batter)
        elif play == PlayResult.TRIPLE:
            scored = self._advance_runners(3, batter)
        elif play == PlayResult.ERROR:
            scored = self._advance_runners(1, batter)
        else: # アウト
            self.state.outs += 1
            self.game_stats[pitcher]['innings_pitched'] += 0.333
            if self.state.outs >= 3: self._change_inning()
            return play

        if scored > 0:
            self.game_stats[batter]['rbis'] += scored
            if play != PlayResult.ERROR:
                self.game_stats[pitcher]['runs_allowed'] += scored
                self.game_stats[pitcher]['earned_runs'] += scored
            self._score(scored)
            
        return play

    def _advance_runners(self, bases, batter, is_walk=False):
        score = 0
        if is_walk:
            if self.state.runner_1b:
                if self.state.runner_2b:
                    if self.state.runner_3b: score += 1
                    self.state.runner_3b = self.state.runner_3b if self.state.runner_3b else self.state.runner_2b
                self.state.runner_2b = self.state.runner_2b if self.state.runner_2b else self.state.runner_1b
            self.state.runner_1b = batter
        else:
            if bases == 4: pass
            elif bases == 3:
                if self.state.runner_3b: score += 1
                if self.state.runner_2b: score += 1
                if self.state.runner_1b: score += 1
                self.state.runner_1b = self.state.runner_2b = None
                self.state.runner_3b = batter
            elif bases == 2:
                if self.state.runner_3b: score += 1; self.state.runner_3b = None
                if self.state.runner_2b: score += 1; self.state.runner_2b = None
                if self.state.runner_1b:
                    if random.random() < 0.4: score += 1; self.state.runner_1b = None
                    else: self.state.runner_3b = self.state.runner_1b; self.state.runner_1b = None
                self.state.runner_2b = batter
            elif bases == 1:
                if self.state.runner_3b: score += 1; self.state.runner_3b = None
                if self.state.runner_2b:
                    if random.random() < 0.6: score += 1; self.state.runner_2b = None
                    else: self.state.runner_3b = self.state.runner_2b; self.state.runner_2b = None
                if self.state.runner_1b: self.state.runner_2b = self.state.runner_1b
                self.state.runner_1b = batter
        return score

    def _score(self, pts):
        if self.state.is_top: self.state.away_score += pts
        else: self.state.home_score += pts

    def _reset_count(self):
        self.state.balls = 0
        self.state.strikes = 0

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

        if self.state.is_top:
            self.state.away_batter_order = (self.state.away_batter_order + 1) % n
        else:
            self.state.home_batter_order = (self.state.home_batter_order + 1) % n

    def _change_inning(self):
        self.state.outs = 0
        self.state.runner_1b = None
        self.state.runner_2b = None
        self.state.runner_3b = None
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
        """試合結果を確定し、選手成績とチーム成績に反映"""
        win_p, loss_p = None, None
        
        # 投手がいない場合のガード
        if not self.state.home_pitchers_used or not self.state.away_pitchers_used:
            return

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
            # チームレベルに応じたレコードを使用
            record = player.get_record_by_level(self.team_level)
            
            for key, val in stats.items():
                if hasattr(record, key):
                    current = getattr(record, key)
                    setattr(record, key, current + val)
            
            record.games += 1

    def get_winner(self):
        if self.state.home_score > self.state.away_score: return self.home_team.name
        if self.state.away_score > self.state.home_score: return self.away_team.name
        return "DRAW"