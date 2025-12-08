# -*- coding: utf-8 -*-
"""
ライブ試合エンジン (修正版: 全能力反映)
"""
import random
import math
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict
from enum import Enum
from models import Position # modelsからインポート

# ========================================
# 定数・ユーティリティ
# ========================================

STRIKE_ZONE = {
    'width': 0.432,
    'height': 0.56,
    'center_x': 0.0,
    'center_z': 0.75, # 地面から75cm
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

# ========================================
# 列挙型
# ========================================

class PitchType(Enum):
    FASTBALL = "ストレート"
    SLIDER = "スライダー"
    CURVE = "カーブ"
    CHANGEUP = "チェンジアップ"
    FORK = "フォーク"
    SINKER = "シンカー"
    CUTTER = "カットボール"
    TWOSEAM = "ツーシーム"
    SHOOT = "シュート"
    SPLIT = "スプリット"

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
    
    # 走者 (Player Object)
    runner_1b: Optional[object] = None 
    runner_2b: Optional[object] = None
    runner_3b: Optional[object] = None
    
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

    def is_runner_on(self) -> bool:
        return any([self.runner_1b, self.runner_2b, self.runner_3b])

    def current_pitcher_stamina(self) -> float:
        return self.away_pitcher_stamina if self.is_top else self.home_pitcher_stamina

# ========================================
# AI マネージャー
# ========================================

class AIManager:
    """AIによる采配決定"""
    
    def decide_strategy(self, state: GameState, offense_team, defense_team) -> str:
        """攻撃側の作戦を決定"""
        score_diff = state.away_score - state.home_score if state.is_top else state.home_score - state.away_score
        is_late = state.inning >= 7
        is_close = abs(score_diff) <= 2
        
        # 盗塁: ランナー1塁、俊足、接戦
        if state.runner_1b and not state.runner_2b and state.outs < 2:
            # 安全にstatsにアクセス
            if hasattr(state.runner_1b, 'stats'):
                runner_spd = getattr(state.runner_1b.stats, 'run', 50)
                if runner_spd >= 80 and random.random() < 0.2:
                    return "STEAL"
        
        # バント: 無死1塁/2塁、接戦、終盤、打力低め
        if state.outs == 0 and (state.runner_1b or state.runner_2b) and not state.runner_3b:
            if is_close and is_late:
                return "BUNT"
                
        # 強振: 3-0, 3-1 カウントでパワーヒッター
        if state.balls >= 3 and state.strikes < 2:
            return "POWER"
            
        return "SWING"

    def decide_pitch_strategy(self, state: GameState) -> str:
        """守備側の配球方針"""
        if state.balls >= 3:
            return "STRIKE" # ストライクを取りに行く
        if state.strikes == 2:
            return "BALL" # 誘い球
        return "NORMAL"

# ========================================
# 投球・打球エンジン (能力値反映)
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

    def generate_pitch(self, p_stats, pitch_type, state, strategy="NORMAL") -> PitchData:
        # 能力値
        velocity = getattr(p_stats, 'velocity', 145)
        control = getattr(p_stats, 'control', 50)
        movement = getattr(p_stats, 'movement', 50)
        stamina = getattr(p_stats, 'stamina', 50)
        
        # スタミナ消費
        current_stamina = state.current_pitcher_stamina()
        fatigue = 1.0 if current_stamina > 30 else 0.9
        
        # スタミナ減少
        cost = 0.5 if pitch_type == "ストレート" else 0.7
        if state.is_top: state.away_pitcher_stamina = max(0, state.away_pitcher_stamina - cost)
        else: state.home_pitcher_stamina = max(0, state.home_pitcher_stamina - cost)
        
        # 球種
        if not pitch_type:
            breaking = getattr(p_stats, 'breaking_balls', ["スライダー"])
            if not breaking: breaking = ["スライダー"]
            pitch_type = "ストレート" if random.random() < 0.5 else random.choice(breaking)
            
        base = self.PITCH_DATA.get(pitch_type, self.PITCH_DATA["ストレート"])
        
        # 球速
        base_velo = velocity * fatigue
        velo = random.gauss(base_velo, 2.0)
        velo = max(80, min(168, velo))
        
        # 変化 (Movementが高いとキレが増す)
        move_factor = 1.0 + (movement - 50) * 0.005
        h_brk = base["h_break"] * move_factor + random.gauss(0, 2)
        v_brk = base["v_break"] * move_factor + random.gauss(0, 2)
        
        # ロケーション
        loc = self._calc_location(control * fatigue, state, strategy)
        
        # 軌道
        traj = self._calc_traj(velo, h_brk, v_brk, loc)
        
        return PitchData(pitch_type, round(velo,1), 2200, h_brk, v_brk, loc, (0,18.44,1.8), traj)

    def _calc_location(self, control, state, strategy):
        # 精度 (Control 50 -> 0.15m, 99 -> 0.05m)
        sigma = max(0.05, 0.25 - (control * 0.002))
        
        # ターゲット
        tx, tz = 0, STRIKE_ZONE['center_z']
        
        if strategy == "STRIKE":
            sigma *= 0.7
        elif strategy == "BALL":
            if random.random() < 0.5: tz -= 0.3
            else: tx = 0.25 if random.random() < 0.5 else -0.25
        else:
            if random.random() < 0.6:
                tx = random.choice([-0.2, 0.2])
                tz += random.choice([-0.25, 0.25])
                
        ax = random.gauss(tx, sigma)
        az = random.gauss(tz, sigma)
        
        is_strike = (abs(ax) <= 0.23 and abs(az - 0.75) <= 0.29)
        return PitchLocation(ax, az, is_strike)

    def _calc_traj(self, velo, hb, vb, loc):
        path = []
        start = (random.uniform(-0.05, 0.05), 18.44, 1.8)
        end = (loc.x, 0, loc.z)
        for i in range(16):
            t = i/15
            x = start[0] + (end[0]-start[0])*t + (hb/150)*math.sin(t*3.14)
            y = start[1] * (1-t)
            z = start[2] + (end[2]-start[2])*t + (vb/150)*(t**2)
            path.append((x,y,z))
        return path

class BattedBallGenerator:
    def generate(self, b_stats, p_stats, pitch: PitchData, strategy="SWING"):
        power = getattr(b_stats, 'power', 50)
        contact = getattr(b_stats, 'contact', 50)
        gap = getattr(b_stats, 'gap', 50)
        
        p_movement = getattr(p_stats, 'movement', 50)
        p_gb_tendency = getattr(p_stats, 'gb_tendency', 50)
        
        # ミート補正
        meet_bonus = 0
        if strategy == "MEET": meet_bonus = 15
        if strategy == "POWER": meet_bonus = -15
        
        # コンタクト品質
        con_eff = contact + meet_bonus - (p_movement - 50) * 0.3
        if not pitch.location.is_strike: con_eff -= 20
        
        quality_roll = random.uniform(0, 100)
        if quality_roll < con_eff * 0.4: quality = "hard"
        elif quality_roll < con_eff * 0.9: quality = "medium"
        else: quality = "soft"
        
        # 速度
        base_v = 110 + (power - 50)*0.9
        if strategy == "POWER": base_v += 10
        if quality == "hard": base_v += 20
        if quality == "soft": base_v -= 25
        
        velo = max(60, base_v + random.gauss(0, 6))
        
        # 角度
        angle_bias = 15 - (p_gb_tendency - 50) * 0.2
        if pitch.location.z < 0.6: angle_bias -= 10
        if pitch.location.z > 0.9: angle_bias += 15
        if strategy == "BUNT":
            angle = -15
            velo = 30
            quality = "soft"
        else:
            # Gapが高いとライナー性
            if gap > 60 and random.random() < (gap/200): angle_bias = 20
            angle = random.gauss(angle_bias, 15)
        
        # タイプ
        if angle < 8: htype = BattedBallType.GROUNDBALL
        elif angle < 23: htype = BattedBallType.LINEDRIVE
        elif angle < 50: htype = BattedBallType.FLYBALL
        else: htype = BattedBallType.POPUP
        
        # 飛距離
        v_ms = velo / 3.6
        dist = (v_ms**2 * math.sin(math.radians(2 * angle))) / 9.8
        dist *= (0.6 + random.random()*0.3)
        if htype == BattedBallType.GROUNDBALL: dist *= 0.4
        dist = max(0, dist)
        
        # 軌道生成
        traj = []
        spray = random.gauss(0, 20)
        steps = 20
        for i in range(steps+1):
            t = i/steps
            d = dist * t
            h = d * math.tan(math.radians(angle)) - (9.8 * d**2) / (2 * (v_ms * math.cos(math.radians(angle)))**2)
            if h < 0: h = 0
            
            rad = math.radians(spray)
            x = d * math.sin(rad)
            y = d * math.cos(rad)
            traj.append((x, y, h))
            
        return BattedBallData(velo, angle, spray, htype, dist, 4.0, x, y, traj, quality)

class DefenseEngine:
    def judge(self, ball: BattedBallData):
        if ball.hit_type == BattedBallType.FLYBALL and ball.distance > 115:
            return PlayResult.HOME_RUN
            
        # 守備乱数
        def_roll = random.uniform(0, 100)
        
        # 基本BABIP率 (ヒットになる確率)
        hit_prob = 0.3
        
        if ball.contact_quality == "hard": hit_prob += 0.4
        if ball.contact_quality == "soft": hit_prob -= 0.15
        if ball.hit_type == BattedBallType.LINEDRIVE: hit_prob += 0.3
        if ball.hit_type == BattedBallType.POPUP: hit_prob = 0.01
        
        if random.random() < hit_prob:
            # ヒット
            if ball.distance > 85: return PlayResult.DOUBLE
            if ball.distance > 100: return PlayResult.TRIPLE
            return PlayResult.SINGLE
        else:
            # アウト
            if ball.hit_type == BattedBallType.GROUNDBALL: return PlayResult.GROUNDOUT
            if ball.hit_type == BattedBallType.LINEDRIVE: return PlayResult.LINEOUT
            return PlayResult.FLYOUT

# ========================================
# 統合エンジン
# ========================================

class LiveGameEngine:
    def __init__(self, home, away):
        self.home_team = home
        self.away_team = away
        self.state = GameState()
        self.pitch_gen = PitchGenerator()
        self.bat_gen = BattedBallGenerator()
        self.def_eng = DefenseEngine()
        self.ai = AIManager()
        
        self._init_starters()

    def _init_starters(self):
        self.state.home_pitcher_idx = 0
        self.state.away_pitcher_idx = 0

    def get_current_batter(self):
        team = self.away_team if self.state.is_top else self.home_team
        order = self.state.away_batter_order if self.state.is_top else self.state.home_batter_order
        return team.players[order % 9], order % 9

    def get_current_pitcher(self):
        team = self.home_team if self.state.is_top else self.away_team
        idx = self.state.home_pitcher_idx if self.state.is_top else self.state.away_pitcher_idx
        return team.players[idx], idx

    def simulate_pitch(self, strategy="SWING"):
        batter, _ = self.get_current_batter()
        pitcher, _ = self.get_current_pitcher()
        
        # 守備側AI判断
        pitch_strategy = self.ai.decide_pitch_strategy(self.state)
        
        # 投球
        pitch = self.pitch_gen.generate_pitch(pitcher.stats, None, self.state, pitch_strategy)
        
        # バント処理
        if strategy == "BUNT":
            ball = self.bat_gen.generate(batter.stats, pitcher.stats, pitch, strategy)
            ball.exit_velocity = 30
            ball.distance = 5
            ball.hit_type = BattedBallType.GROUNDBALL
            return PitchResult.IN_PLAY, pitch, ball
            
        # 盗塁処理
        if strategy == "STEAL":
            runner = self.state.runner_1b
            if runner:
                spd = getattr(runner.stats, 'run', 50)
                if random.random() < (spd/100) * 0.8:
                    # 成功
                    self.state.runner_2b = self.state.runner_1b
                    self.state.runner_1b = None
                    return PitchResult.BALL, pitch, None # ボール扱い
                else:
                    # 失敗
                    self.state.runner_1b = None
                    self.state.outs += 1
                    if self.state.outs >= 3: self._change_inning()
                    return PitchResult.STRIKE_SWINGING, pitch, None

        # スイング判定
        swing_prob = 0.7 if pitch.location.is_strike else 0.25
        if strategy == "WAIT": swing_prob *= 0.2
        if self.state.strikes == 2: swing_prob += 0.2
        
        # Eyeによる選球眼補正
        eye = getattr(batter.stats, 'eye', 50)
        if not pitch.location.is_strike:
            swing_prob -= (eye - 50) * 0.005
        
        is_swing = random.random() < swing_prob
        
        if not is_swing:
            res = PitchResult.STRIKE_CALLED if pitch.location.is_strike else PitchResult.BALL
            return res, pitch, None
            
        # コンタクト判定
        con = getattr(batter.stats, 'contact', 50)
        hit_prob = 0.6 + (con-50)*0.005
        if not pitch.location.is_strike: hit_prob -= 0.3
        
        if random.random() > hit_prob:
            return PitchResult.STRIKE_SWINGING, pitch, None
            
        # ファウル
        if random.random() < 0.3:
            return PitchResult.FOUL, pitch, None
            
        # インプレー
        ball = self.bat_gen.generate(batter.stats, pitcher.stats, pitch, strategy)
        return PitchResult.IN_PLAY, pitch, ball

    def process_pitch_result(self, res, pitch, ball):
        if res == PitchResult.BALL:
            self.state.balls += 1
            if self.state.balls >= 4: return self._walk()
        elif res in [PitchResult.STRIKE_CALLED, PitchResult.STRIKE_SWINGING]:
            self.state.strikes += 1
            if self.state.strikes >= 3: return self._out(PlayResult.STRIKEOUT)
        elif res == PitchResult.FOUL:
            if self.state.strikes < 2: self.state.strikes += 1
        elif res == PitchResult.IN_PLAY:
            play = self.def_eng.judge(ball)
            return self._resolve_play(play)
        return None

    def _walk(self):
        batter, _ = self.get_current_batter()
        self._advance_runners(1, batter)
        self._reset_count()
        self._next_batter()
        return PlayResult.WALK

    def _out(self, kind=PlayResult.STRIKEOUT):
        self.state.outs += 1
        self._reset_count()
        self._next_batter()
        if self.state.outs >= 3: self._change_inning()
        return kind

    def _resolve_play(self, play):
        batter, _ = self.get_current_batter()
        
        self._reset_count()
        self._next_batter()
        
        if play == PlayResult.HOME_RUN:
            self._score(1 + (1 if self.state.runner_1b else 0) + (1 if self.state.runner_2b else 0) + (1 if self.state.runner_3b else 0))
            self.state.runner_1b = self.state.runner_2b = self.state.runner_3b = None
        elif play in [PlayResult.SINGLE, PlayResult.INFIELD_HIT]:
            self._advance_runners(1, batter)
        elif play == PlayResult.DOUBLE:
            self._advance_runners(2, batter)
        elif play == PlayResult.TRIPLE:
            self._advance_runners(3, batter)
        else: # OUT
            self.state.outs += 1
            if self.state.outs >= 3: self._change_inning()
            
        return play

    def _advance_runners(self, bases, batter=None):
        score = 0
        
        if bases == 1:
            if self.state.runner_3b: score += 1; self.state.runner_3b = None
            if self.state.runner_2b:
                # 50% chance to score from 2nd on single
                if random.random() < 0.5:
                    score += 1; self.state.runner_2b = None
                else:
                    self.state.runner_3b = self.state.runner_2b; self.state.runner_2b = None
                    
            if self.state.runner_1b: self.state.runner_2b = self.state.runner_1b
            
            self.state.runner_1b = batter
            
        elif bases == 2:
            if self.state.runner_3b: score += 1; self.state.runner_3b = None
            if self.state.runner_2b: score += 1; self.state.runner_2b = None
            if self.state.runner_1b: self.state.runner_3b = self.state.runner_1b; self.state.runner_1b = None
            
            self.state.runner_2b = batter
            
        elif bases == 3:
            if self.state.runner_3b: score += 1
            if self.state.runner_2b: score += 1
            if self.state.runner_1b: score += 1
            self.state.runner_1b = self.state.runner_2b = None
            self.state.runner_3b = batter
        
        self._score(score)

    def _score(self, pts):
        if self.state.is_top: self.state.away_score += pts
        else: self.state.home_score += pts

    def _reset_count(self):
        self.state.balls = 0
        self.state.strikes = 0

    def _next_batter(self):
        if self.state.is_top: self.state.away_batter_order = (self.state.away_batter_order + 1) % 9
        else: self.state.home_batter_order = (self.state.home_batter_order + 1) % 9

    def _change_inning(self):
        self.state.outs = 0
        self.state.runner_1b = None
        self.state.runner_2b = None
        self.state.runner_3b = None
        if not self.state.is_top: self.state.inning += 1
        self.state.is_top = not self.state.is_top

    def is_game_over(self):
        if self.state.inning > 9: return True
        if self.state.inning == 9 and not self.state.is_top and self.state.home_score > self.state.away_score: return True
        return False

    def get_winner(self):
        if self.state.home_score > self.state.away_score: return self.home_team.name
        if self.state.away_score > self.state.home_score: return self.away_team.name
        return "DRAW"