# -*- coding: utf-8 -*-
"""
打席結果判定エンジン（能力値完全反映版）

すべての選手能力（gap, eye, avoid_k, stuff, movement, defense_rangesなど）を
計算ロジックに組み込んだリアルな野球シミュレーション
"""
import random
import math
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict
from enum import Enum
from models import Position  # Position Enumが必要

# ========================================
# 列挙型
# ========================================

class AtBatResult(Enum):
    SINGLE = "単打"
    DOUBLE = "二塁打"
    TRIPLE = "三塁打"
    HOME_RUN = "本塁打"
    INFIELD_HIT = "内野安打"
    STRIKEOUT = "三振"
    GROUNDOUT = "ゴロ"
    FLYOUT = "飛球"
    LINEOUT = "ライナー"
    POP_OUT = "邪飛"
    DOUBLE_PLAY = "併殺打"
    SACRIFICE_FLY = "犠飛"
    SACRIFICE_BUNT = "犠打"
    WALK = "四球"
    HIT_BY_PITCH = "死球"
    ERROR = "失策"

class PitchResult(Enum):
    STRIKE_LOOKING = "見逃しストライク"
    STRIKE_SWINGING = "空振り"
    BALL = "ボール"
    FOUL = "ファウル"
    IN_PLAY = "打球"

class PitchLocation(Enum):
    HIGH_INSIDE = "高め内角"
    HIGH_MIDDLE = "高め中央"
    HIGH_OUTSIDE = "高め外角"
    MIDDLE_INSIDE = "真ん中内角"
    MIDDLE_MIDDLE = "真ん中中央"
    MIDDLE_OUTSIDE = "真ん中外角"
    LOW_INSIDE = "低め内角"
    LOW_MIDDLE = "低め中央"
    LOW_OUTSIDE = "低め外角"
    BALL_ZONE = "ボールゾーン"

# ========================================
# データクラス
# ========================================

@dataclass
class BattedBall:
    exit_velocity: float
    launch_angle: float
    spray_angle: float
    hit_type: str
    contact_quality: str
    distance: float = 0.0
    hang_time: float = 0.0
    landing_x: float = 0.0
    landing_y: float = 0.0

@dataclass
class PitchData:
    pitch_type: str
    velocity: float
    location: PitchLocation
    horizontal_break: float
    vertical_break: float
    spin_rate: int
    is_strike_zone: bool

@dataclass
class DefenseData:
    """守備データ（詳細版）"""
    # 各ポジションの守備範囲 (1-99)
    ranges: Dict[str, int] = field(default_factory=dict)
    # 各ポジションの肩力
    arms: Dict[str, int] = field(default_factory=dict)
    # 各ポジションのエラー回避
    errors: Dict[str, int] = field(default_factory=dict)
    # 捕手リード
    catcher_lead: int = 50
    # 内野連携（併殺等）
    turn_dp: int = 50

    def get_range(self, pos: Position) -> int:
        return self.ranges.get(pos.value, 1) # デフォルト1（適正なし）

    def get_arm(self, pos: Position) -> int:
        return self.arms.get(pos.value, 50)

    def get_error(self, pos: Position) -> int:
        return self.errors.get(pos.value, 50)

@dataclass
class AtBatContext:
    balls: int = 0
    strikes: int = 0
    outs: int = 0
    runners: List[bool] = field(default_factory=lambda: [False, False, False])
    inning: int = 1
    is_top: bool = True
    score_diff: int = 0

# ========================================
# 打球生成エンジン
# ========================================

class BattedBallGenerator:
    """打球生成・判定クラス"""

    def generate_pitch(self, pitcher_stats, pitch_type: str = None) -> PitchData:
        """投球生成"""
        # 能力値取得
        velocity_stat = getattr(pitcher_stats, 'velocity', 145)
        control = getattr(pitcher_stats, 'control', 50)
        movement = getattr(pitcher_stats, 'movement', 50)
        
        # 球速 (km/h)
        base_velo = velocity_stat
        velo = random.gauss(base_velo, 2.0)
        
        # コントロール判定
        # Control 50 -> ストライク率 55%
        strike_prob = 0.40 + (control * 0.003)
        is_strike = random.random() < strike_prob
        
        # コース決定
        if is_strike:
            locations = [l for l in PitchLocation if l != PitchLocation.BALL_ZONE]
            location = random.choice(locations)
        else:
            location = PitchLocation.BALL_ZONE
            
        return PitchData(
            pitch_type=pitch_type or "ストレート",
            velocity=velo,
            location=location,
            horizontal_break=0, # 簡易化
            vertical_break=0,
            spin_rate=2200,
            is_strike_zone=is_strike
        )

    def calculate_swing_decision(self, batter_stats, pitch: PitchData, context: AtBatContext) -> bool:
        """スイング判定 (Eye, Control)"""
        eye = getattr(batter_stats, 'eye', 50)
        
        # 選球眼補正
        eye_factor = (eye - 50) * 0.005
        
        if pitch.is_strike_zone:
            # ストライクゾーン
            swing_prob = 0.75 + eye_factor # 目が良いとストライクを振りやすい
            if context.strikes == 2: swing_prob += 0.15 # 追い込まれると振る
        else:
            # ボールゾーン
            swing_prob = 0.30 - eye_factor # 目が良いと見極める
            if context.strikes == 2: swing_prob += 0.15 # 追い込まれると手を出す
            
        return random.random() < max(0.05, min(0.98, swing_prob))

    def calculate_contact(self, batter_stats, pitcher_stats, pitch: PitchData) -> Tuple[bool, bool]:
        """コンタクト判定 (Contact, Avoid K vs Stuff, Velocity)"""
        contact = getattr(batter_stats, 'contact', 50)
        avoid_k = getattr(batter_stats, 'avoid_k', 50)
        
        stuff = getattr(pitcher_stats, 'stuff', 50) # 奪三振力
        velocity = getattr(pitcher_stats, 'velocity', 145)
        
        # 基本コンタクト率
        base_rate = 0.80
        
        # 能力補正
        batter_skill = (contact * 0.6 + avoid_k * 0.4)
        pitcher_skill = (stuff * 0.6 + (velocity - 130) * 0.5)
        
        rate = base_rate + (batter_skill - pitcher_skill) * 0.004
        
        # ゾーン外補正
        if not pitch.is_strike_zone: rate -= 0.15
        
        contact_success = random.random() < max(0.40, min(0.95, rate))
        
        # ファウル判定
        is_foul = False
        if contact_success:
            foul_prob = 0.3
            if not pitch.is_strike_zone: foul_prob += 0.2
            # Stuffが良いとファウルになりやすい
            foul_prob += (stuff - 50) * 0.002
            is_foul = random.random() < foul_prob
            
        return contact_success, is_foul

    def generate_batted_ball(self, batter_stats, pitcher_stats, pitch: PitchData) -> BattedBall:
        """打球生成 (Power, Gap, Movement, GB Tendency)"""
        power = getattr(batter_stats, 'power', 50)
        gap = getattr(batter_stats, 'gap', 50)
        contact = getattr(batter_stats, 'contact', 50)
        
        movement = getattr(pitcher_stats, 'movement', 50) # 被本塁打抑制・芯を外す
        gb_tendency = getattr(pitcher_stats, 'gb_tendency', 50) # ゴロ傾向
        
        # 打球速度
        base_exit_velo = 130 + (power - 50) * 0.8
        # Movementが高いと芯を外して速度低下
        base_exit_velo -= (movement - 50) * 0.3
        exit_velocity = random.gauss(base_exit_velo, 10)
        
        # 打球角度
        # GB Tendencyが高いと角度が下がる
        base_angle = 15 - (gb_tendency - 50) * 0.3
        # Gapが高いとライナー性（10-25度）が増える
        if gap > 60 and random.random() < (gap/200):
            base_angle = 18 # ライナー狙い
            
        launch_angle = random.gauss(base_angle, 15)
        
        # 打球方向 (Pull/Push) - 簡易的にランダム
        spray_angle = random.gauss(0, 25)
        
        # タイプ判定
        if launch_angle < 10: hit_type = "groundball"
        elif launch_angle < 25: hit_type = "linedrive"
        elif launch_angle < 50: hit_type = "flyball"
        else: hit_type = "popup"
        
        # 飛距離概算 (簡易物理)
        v0 = exit_velocity / 3.6
        angle_rad = math.radians(launch_angle)
        g = 9.8
        distance = (v0**2 * math.sin(2 * angle_rad)) / g
        distance *= 0.8 # 空気抵抗簡易補正
        
        # コンタクト品質
        quality = "medium"
        if exit_velocity > 150: quality = "hard"
        elif exit_velocity < 110: quality = "soft"
        
        return BattedBall(exit_velocity, launch_angle, spray_angle, hit_type, quality, distance)

# ========================================
# 守備判定エンジン
# ========================================

class DefenseEngine:
    """守備結果判定クラス"""
    
    def judge_result(self, ball: BattedBall, defense: DefenseData, runner_speed: int) -> AtBatResult:
        
        # 1. ホームラン判定
        if ball.hit_type == "flyball" and ball.distance > 115: # 簡易フェンス距離
            return AtBatResult.HOME_RUN
            
        # 守備位置の特定（簡易）
        position = self._determine_fielder(ball.spray_angle, ball.distance)
        
        # 2. エラー判定
        error_stat = defense.get_error(position)
        # 難しい打球ほどエラーしやすい
        difficulty = 0
        if ball.contact_quality == "hard": difficulty += 10
        if position in [Position.SHORTSTOP, Position.SECOND, Position.THIRD]: difficulty += 5
        
        error_prob = max(0.005, (100 - error_stat + difficulty) * 0.0005)
        if random.random() < error_prob:
            return AtBatResult.ERROR
            
        # 3. アウト/ヒット判定
        range_stat = defense.get_range(position)
        
        # 基本ヒット率 (BABIP)
        hit_prob = 0.30
        
        # 打球タイプ補正
        if ball.hit_type == "groundball": hit_prob = 0.24
        elif ball.hit_type == "linedrive": hit_prob = 0.70
        elif ball.hit_type == "flyball": hit_prob = 0.15 # HR除く
        elif ball.hit_type == "popup": hit_prob = 0.01
        
        # 守備範囲補正 (守備が良いとヒット率下がる)
        hit_prob -= (range_stat - 50) * 0.004
        
        # 打球強さ補正
        if ball.contact_quality == "hard": hit_prob += 0.15
        if ball.contact_quality == "soft": hit_prob -= 0.10
        
        # 内野安打判定 (ゴロのみ)
        if ball.hit_type == "groundball":
            # 走力 vs 守備範囲・肩
            # 肩力は深いゴロで影響
            arm_stat = defense.get_arm(position)
            infield_hit_prob = (runner_speed * 0.003) - (arm_stat * 0.001) - (range_stat * 0.001)
            infield_hit_prob = max(0.02, infield_hit_prob)
            
            if random.random() < hit_prob:
                return AtBatResult.SINGLE # 抜けた
            elif random.random() < infield_hit_prob: # 追いついたが間に合わない
                return AtBatResult.INFIELD_HIT
            else:
                return AtBatResult.GROUNDOUT
        
        # フライ/ライナー
        if random.random() < hit_prob:
            # 長打判定 (Gap, Power, Distance)
            if ball.distance > 90 or (ball.hit_type == "linedrive" and ball.distance > 70):
                # ギャップを抜くか
                if random.random() < 0.3: return AtBatResult.DOUBLE
                if random.random() < 0.03: return AtBatResult.TRIPLE
            return AtBatResult.SINGLE
        else:
            if ball.hit_type == "linedrive": return AtBatResult.LINEOUT
            if ball.hit_type == "popup": return AtBatResult.POP_OUT
            return AtBatResult.FLYOUT

    def _determine_fielder(self, angle, distance) -> Position:
        """打球方向と距離から担当野手を決定"""
        if distance < 45: # 内野
            if -45 <= angle < -15: return Position.THIRD
            elif -15 <= angle < 0: return Position.SHORTSTOP
            elif 0 <= angle < 15: return Position.SECOND
            else: return Position.FIRST
        else: # 外野
            if angle < -15: return Position.OUTFIELD # LEFT
            elif angle > 15: return Position.OUTFIELD # RIGHT
            else: return Position.OUTFIELD # CENTER

# ========================================
# シミュレーター本体
# ========================================

class AtBatSimulator:
    def __init__(self):
        self.ball_gen = BattedBallGenerator()
        self.defense = DefenseEngine()

    def simulate_at_bat(self, batter_stats, pitcher_stats, defense_data: DefenseData, 
                       context: AtBatContext, pitch_list: List[str] = None) -> Tuple[AtBatResult, Dict]:
        """打席シミュレーション実行"""
        
        pitch_count = 0
        pitch_log = []
        
        while True:
            pitch_count += 1
            
            # 1. 投球
            pitch = self.ball_gen.generate_pitch(pitcher_stats)
            
            # 2. スイング判定
            swing = self.ball_gen.calculate_swing_decision(batter_stats, pitch, context)
            
            if not swing:
                if pitch.is_strike_zone:
                    context.strikes += 1
                else:
                    context.balls += 1
            else:
                # 3. コンタクト判定
                contact, is_foul = self.ball_gen.calculate_contact(batter_stats, pitcher_stats, pitch)
                
                if not contact:
                    context.strikes += 1
                elif is_foul:
                    if context.strikes < 2: context.strikes += 1
                else:
                    # 4. インプレー - 打球生成
                    batted_ball = self.ball_gen.generate_batted_ball(batter_stats, pitcher_stats, pitch)
                    
                    # 5. 守備判定
                    runner_speed = getattr(batter_stats, 'speed', 50)
                    result = self.defense.judge_result(batted_ball, defense_data, runner_speed)
                    
                    # 併殺判定 (ゴロアウトかつ走者あり)
                    if result == AtBatResult.GROUNDOUT and context.runners[0] and context.outs < 2:
                        # 守備側の併殺能力 vs 打者の走力
                        dp_prob = 0.15 + (defense_data.turn_dp - 50) * 0.003 - (runner_speed - 50) * 0.002
                        if random.random() < dp_prob:
                            result = AtBatResult.DOUBLE_PLAY
                            
                    return result, {'pitch_count': pitch_count}

            # カウント判定
            if context.balls >= 4:
                return AtBatResult.WALK, {'pitch_count': pitch_count}
            if context.strikes >= 3:
                return AtBatResult.STRIKEOUT, {'pitch_count': pitch_count}

_at_bat_simulator = AtBatSimulator()
def get_at_bat_simulator():
    return _at_bat_simulator