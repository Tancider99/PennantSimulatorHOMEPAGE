# -*- coding: utf-8 -*-
"""
NPB打席結果判定エンジン

投手と打者の能力を基に打球成分（打球速度・角度・方向）を生成し、
守備能力を考慮して結果を判定するリアルな野球シミュレーション

NPB 2023年実績ベース:
- リーグ打率: .254
- リーグOPS: .688
- リーグBABIP: .294
- 三振率: 21.5%
- 四球率: 7.8%
- HR率: 2.3%（打席比）
- ゴロ率: 45%, ライナー率: 10%, フライ率: 45%
"""
import random
import math
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict
from enum import Enum


# ========================================
# 定数定義
# ========================================

# NPB球場平均寸法
FIELD_CONSTANTS = {
    'mound_distance': 18.44,      # マウンドからホーム (m)
    'base_distance': 27.431,      # 塁間 (m)
    'infield_depth': 28.0,        # 内野手守備位置 (m)
    'infield_grass': 29.0,        # 内野芝生ライン (m)
    'outfield_start': 75.0,       # 外野開始位置 (m)
    'fence_center': 122.0,        # センターフェンス (m)
    'fence_left_center': 116.0,   # 左中間 (m)
    'fence_right_center': 116.0,  # 右中間 (m)
    'fence_left': 100.0,          # レフトポール (m)
    'fence_right': 100.0,         # ライトポール (m)
    'fence_height': 4.2,          # フェンス高さ (m)
}

# 打球タイプ目標分布（NPB実績）
HIT_TYPE_DISTRIBUTION = {
    'groundball': 0.45,    # ゴロ 45%
    'linedrive': 0.10,     # ライナー 10%
    'flyball': 0.35,       # フライ 35%
    'popup': 0.10,         # 内野フライ 10%
}

# 打球タイプ別安打率（NPB実績）
BABIP_BY_TYPE = {
    'groundball': 0.230,   # ゴロ安打率 23%
    'linedrive': 0.680,    # ライナー安打率 68%
    'flyball': 0.140,      # フライ安打率 14%（HR除く）
    'popup': 0.015,        # 内野フライ安打率 1.5%
}

# 打球質分布（NPB/MLB Statcast基準）
CONTACT_QUALITY = {
    'soft': {'threshold': 0.23, 'max_velo': 95},      # 23%: ～95km/h
    'medium': {'threshold': 0.42, 'max_velo': 135},   # 42%: 95-135km/h
    'hard': {'threshold': 0.35, 'max_velo': 193},     # 35%: 135km/h～
}

# 打球角度範囲
LAUNCH_ANGLE_RANGES = {
    'groundball': (-15, 10),     # ゴロ: -15～10度
    'linedrive': (10, 25),       # ライナー: 10-25度
    'flyball': (25, 50),         # フライ: 25-50度
    'popup': (50, 75),           # 内野フライ: 50-75度
}


# ========================================
# 列挙型
# ========================================

class AtBatResult(Enum):
    """打席結果"""
    # 安打
    SINGLE = "単打"
    DOUBLE = "二塁打"
    TRIPLE = "三塁打"
    HOME_RUN = "本塁打"
    INFIELD_HIT = "内野安打"

    # アウト
    STRIKEOUT = "三振"
    GROUNDOUT = "ゴロ"
    FLYOUT = "飛球"
    LINEOUT = "ライナー"
    POP_OUT = "邪飛"
    DOUBLE_PLAY = "併殺打"
    SACRIFICE_FLY = "犠飛"
    SACRIFICE_BUNT = "犠打"

    # その他
    WALK = "四球"
    HIT_BY_PITCH = "死球"
    INTENTIONAL_WALK = "敬遠"
    ERROR = "失策"


class PitchResult(Enum):
    """投球結果"""
    STRIKE_LOOKING = "見逃しストライク"
    STRIKE_SWINGING = "空振り"
    BALL = "ボール"
    FOUL = "ファウル"
    IN_PLAY = "打球"


class PitchLocation(Enum):
    """投球コース"""
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
    """打球データ"""
    exit_velocity: float        # 打球速度 (km/h)
    launch_angle: float         # 打球角度 (度) 正=上向き
    spray_angle: float          # 打球方向 (度) 0=センター、正=ライト、負=レフト
    hit_type: str               # 打球タイプ (groundball/linedrive/flyball/popup)
    contact_quality: str        # 打球質 (soft/medium/hard)
    distance: float = 0.0       # 飛距離 (m)
    hang_time: float = 0.0      # 滞空時間 (s)
    landing_x: float = 0.0      # 落下地点X (m)
    landing_y: float = 0.0      # 落下地点Y (m)

    def __post_init__(self):
        """飛距離と滞空時間を計算"""
        self._calculate_trajectory()

    def _calculate_trajectory(self):
        """打球の軌道を計算（空気抵抗・揚力考慮）"""
        # 初速 (km/h -> m/s)
        v0 = self.exit_velocity / 3.6
        angle_rad = math.radians(self.launch_angle)
        spray_rad = math.radians(self.spray_angle)

        # 初速成分
        vx = v0 * math.cos(angle_rad) * math.sin(spray_rad)  # 左右
        vy = v0 * math.cos(angle_rad) * math.cos(spray_rad)  # 前後
        vz = v0 * math.sin(angle_rad)                         # 上下

        # 物理定数
        g = 9.8          # 重力加速度
        rho = 1.2        # 空気密度
        Cd = 0.35        # 抗力係数
        Cl = 0.25        # 揚力係数（バックスピン）
        A = 0.0042       # ボール断面積
        m = 0.145        # ボール質量

        # 数値積分
        dt = 0.02
        x, y, z = 0, 0, 1.0  # バット高さ1m
        t = 0
        max_z = z

        while z >= 0 and t < 10:
            speed = math.sqrt(vx**2 + vy**2 + vz**2)

            if speed > 0:
                # 空気抵抗
                drag = 0.5 * rho * Cd * A * speed**2 / m
                # 揚力（打球角度が正の時のみ）
                lift = 0.5 * rho * Cl * A * speed**2 / m if self.launch_angle > 5 else 0

                # 加速度
                ax = -drag * vx / speed
                ay = -drag * vy / speed
                az = -g - drag * vz / speed + lift
            else:
                ax, ay, az = 0, 0, -g

            # 速度・位置更新
            vx += ax * dt
            vy += ay * dt
            vz += az * dt
            x += vx * dt
            y += vy * dt
            z += vz * dt

            max_z = max(max_z, z)
            t += dt

        self.distance = math.sqrt(x**2 + y**2)
        self.hang_time = t
        self.landing_x = x
        self.landing_y = y


@dataclass
class PitchData:
    """投球データ"""
    pitch_type: str             # 球種
    velocity: float             # 球速 (km/h)
    location: PitchLocation     # コース
    horizontal_break: float     # 横変化 (cm)
    vertical_break: float       # 縦変化 (cm)
    spin_rate: int             # 回転数 (rpm)
    is_strike_zone: bool       # ストライクゾーン内か


@dataclass
class DefenseData:
    """守備データ"""
    # 内野手能力 (1-99スケール)
    catcher_fielding: int = 50
    first_fielding: int = 50
    second_fielding: int = 50
    third_fielding: int = 50
    short_fielding: int = 50

    # 外野手能力
    left_fielding: int = 50
    center_fielding: int = 50
    right_fielding: int = 50
    left_speed: int = 50
    center_speed: int = 50
    right_speed: int = 50
    left_arm: int = 50
    center_arm: int = 50
    right_arm: int = 50

    def get_avg_infield(self) -> float:
        """内野守備平均"""
        return (self.first_fielding + self.second_fielding +
                self.third_fielding + self.short_fielding) / 4

    def get_avg_outfield(self) -> float:
        """外野守備平均"""
        return (self.left_fielding + self.center_fielding +
                self.right_fielding) / 3


@dataclass
class AtBatContext:
    """打席状況"""
    balls: int = 0
    strikes: int = 0
    outs: int = 0
    runners: List[bool] = field(default_factory=lambda: [False, False, False])
    inning: int = 1
    is_top: bool = True
    score_diff: int = 0  # 攻撃チームから見た点差


# ========================================
# 打球生成エンジン
# ========================================

class BattedBallGenerator:
    """打球成分生成クラス"""

    def __init__(self):
        # 球種データ
        self.pitch_data = {
            "ストレート": {"base_speed": 145, "h_break": 0, "v_break": 12},
            "スライダー": {"base_speed": 130, "h_break": -18, "v_break": -2},
            "カーブ": {"base_speed": 115, "h_break": -8, "v_break": -25},
            "チェンジアップ": {"base_speed": 128, "h_break": 8, "v_break": -15},
            "フォーク": {"base_speed": 135, "h_break": 0, "v_break": -30},
            "シンカー": {"base_speed": 142, "h_break": 12, "v_break": -8},
            "カットボール": {"base_speed": 138, "h_break": -6, "v_break": 5},
            "ツーシーム": {"base_speed": 143, "h_break": 10, "v_break": 3},
            "シュート": {"base_speed": 135, "h_break": 15, "v_break": -5},
            "スプリット": {"base_speed": 137, "h_break": 2, "v_break": -22},
        }

    def generate_pitch(self, pitcher_stats, pitch_type: str = None) -> PitchData:
        """投球を生成"""
        if pitch_type is None or pitch_type not in self.pitch_data:
            pitch_type = "ストレート"

        base = self.pitch_data[pitch_type]

        # 投手能力による補正（1-99スケール）
        speed = getattr(pitcher_stats, 'speed', 50)
        control = getattr(pitcher_stats, 'control', 50)
        breaking = getattr(pitcher_stats, 'breaking', 50)

        # 球速計算（能力50で基準値、10ポイントで約2km/h変動）
        velocity = base["base_speed"] + (speed - 50) * 0.2 + random.gauss(0, 1.5)
        velocity = max(90, min(165, velocity))

        # 変化量
        h_break = base["h_break"] * (1 + (breaking - 50) * 0.01) + random.gauss(0, 2)
        v_break = base["v_break"] * (1 + (breaking - 50) * 0.01) + random.gauss(0, 2)

        # コース制球（コントロールが高いほどストライクゾーンに投げやすい）
        # NPB平均ストライク率は約60%程度、四球率7.8%を実現するため調整
        strike_rate = 0.30 + control * 0.004  # 50で50%、80で62%
        is_strike = random.random() < strike_rate

        # コース決定
        if is_strike:
            locations = [loc for loc in PitchLocation if loc != PitchLocation.BALL_ZONE]
            # コントロールが高いと低め中心に投げられる
            if control >= 70 and random.random() < 0.4:
                locations = [PitchLocation.LOW_INSIDE, PitchLocation.LOW_MIDDLE,
                           PitchLocation.LOW_OUTSIDE]
        else:
            # ボールゾーンだが、際どいコースも
            if random.random() < 0.3:
                locations = [PitchLocation.HIGH_INSIDE, PitchLocation.HIGH_OUTSIDE,
                           PitchLocation.LOW_INSIDE, PitchLocation.LOW_OUTSIDE]
            else:
                locations = [PitchLocation.BALL_ZONE]

        location = random.choice(locations)

        return PitchData(
            pitch_type=pitch_type,
            velocity=velocity,
            location=location,
            horizontal_break=h_break,
            vertical_break=v_break,
            spin_rate=2200 + random.randint(-200, 200),
            is_strike_zone=(location != PitchLocation.BALL_ZONE)
        )

    def calculate_swing_decision(self, batter_stats, pitch: PitchData,
                                  context: AtBatContext) -> bool:
        """スイング判定

        NPB目標: 三振率21.5%、四球率7.8%
        """
        contact = getattr(batter_stats, 'contact', 50)
        eye = getattr(batter_stats, 'eye', contact)  # 選球眼

        # 選球眼に基づく判断
        eye_factor = eye / 100

        if pitch.is_strike_zone:
            # ストライクを見逃す確率（見逃し三振の可能性を上げる）
            # 追い込まれているほど振る
            strike_looking_prob = 0.22 - eye_factor * 0.10  # 0.15→0.22
            if context.strikes == 2:
                strike_looking_prob *= 0.4  # 2ストライクでは見逃しにくいが、一定確率で見逃し三振
            return random.random() > strike_looking_prob
        else:
            # ボール球に手を出す確率（ボール球を見逃して四球を増やす）
            # NPB四球率7.8%を目標にさらに調整
            chase_prob = 0.18 - eye_factor * 0.10  # より低く

            # 追い込まれるとボール球に手を出しやすい
            if context.strikes == 2:
                chase_prob += 0.15

            # 際どいコースは手を出しやすい
            if pitch.location in [PitchLocation.LOW_OUTSIDE, PitchLocation.LOW_INSIDE]:
                chase_prob += 0.05

            return random.random() < chase_prob

    def calculate_contact(self, batter_stats, pitcher_stats, pitch: PitchData,
                          is_swing: bool) -> Tuple[bool, bool]:
        """コンタクト判定

        NPB目標: 空振り三振を含む全体三振率21.5%

        Returns:
            (コンタクト成功, ファウルか)
        """
        if not is_swing:
            return False, False

        contact = getattr(batter_stats, 'contact', 50)
        p_speed = getattr(pitcher_stats, 'speed', 50)
        p_control = getattr(pitcher_stats, 'control', 50)
        p_breaking = getattr(pitcher_stats, 'breaking', 50)

        # 基本コンタクト率（空振りを増やすため下げる）
        # 能力50で約70%
        base_rate = 0.55 + contact * 0.003  # 50で70%、80で79%

        # 投手能力によるペナルティ（強化）
        pitcher_factor = (p_speed + p_breaking) / 2
        penalty = (pitcher_factor - 50) * 0.004  # 0.003→0.004

        # 球速によるペナルティ
        if pitch.velocity > 150:
            penalty += (pitch.velocity - 150) * 0.008  # 0.006→0.008
        elif pitch.velocity > 145:
            penalty += (pitch.velocity - 145) * 0.003

        # 変化球によるペナルティ（強化）
        total_break = abs(pitch.horizontal_break) + abs(pitch.vertical_break)
        if total_break > 20:
            penalty += (total_break - 20) * 0.004  # 0.003→0.004
        elif total_break > 10:
            penalty += (total_break - 10) * 0.002

        # ボールゾーンはコンタクトしにくい
        if not pitch.is_strike_zone:
            penalty += 0.15

        contact_rate = max(0.30, min(0.95, base_rate - penalty))

        if random.random() > contact_rate:
            return False, False  # 空振り

        # コンタクト成功時、ファウルか判定
        # ストライクゾーン外はファウルになりやすい
        foul_rate = 0.35
        if not pitch.is_strike_zone:
            foul_rate += 0.20

        is_foul = random.random() < foul_rate
        return True, is_foul

    def generate_batted_ball(self, batter_stats, pitcher_stats, pitch: PitchData,
                             context: AtBatContext = None) -> BattedBall:
        """打球データを生成

        投手と打者の能力を基に、現実的な打球成分を計算
        """
        # 打者能力（1-99スケール）
        contact = getattr(batter_stats, 'contact', 50)
        power = getattr(batter_stats, 'power', 50)
        trajectory = getattr(batter_stats, 'trajectory', 2)  # 弾道 1-4

        # 投手能力
        p_speed = getattr(pitcher_stats, 'speed', 50)
        p_breaking = getattr(pitcher_stats, 'breaking', 50)

        # ===== 1. 打球タイプ決定 =====
        hit_type = self._determine_hit_type(contact, power, trajectory, pitch)

        # ===== 2. 打球質決定 =====
        contact_quality = self._determine_contact_quality(contact, power, pitch)

        # ===== 3. 打球速度計算 =====
        exit_velocity = self._calculate_exit_velocity(
            power, contact_quality, pitch.velocity, hit_type
        )

        # ===== 4. 打球角度計算 =====
        launch_angle = self._calculate_launch_angle(
            hit_type, contact, power, trajectory
        )

        # ===== 5. 打球方向計算 =====
        spray_angle = self._calculate_spray_angle(contact, power)

        return BattedBall(
            exit_velocity=exit_velocity,
            launch_angle=launch_angle,
            spray_angle=spray_angle,
            hit_type=hit_type,
            contact_quality=contact_quality
        )

    def _determine_hit_type(self, contact: int, power: int, trajectory: int,
                            pitch: PitchData) -> str:
        """打球タイプを決定（目標: GB45%, LD10%, FB35%, IFFB10%）"""
        # 弾道による補正
        # trajectory: 1=ゴロ打ち, 2=ライナー, 3=普通, 4=フライ打ち
        gb_mod = {1: 0.12, 2: 0.02, 3: 0.0, 4: -0.12}.get(trajectory, 0)
        ld_mod = {1: -0.02, 2: 0.04, 3: 0.02, 4: -0.02}.get(trajectory, 0)
        fb_mod = {1: -0.10, 2: -0.03, 3: 0.0, 4: 0.12}.get(trajectory, 0)

        # パワーによる補正（パワーが高いとフライが増える）
        power_fb_mod = (power - 50) * 0.002

        # 投球コースによる補正
        if pitch.location in [PitchLocation.LOW_INSIDE, PitchLocation.LOW_MIDDLE,
                             PitchLocation.LOW_OUTSIDE]:
            gb_mod += 0.05  # 低めはゴロになりやすい
        elif pitch.location in [PitchLocation.HIGH_INSIDE, PitchLocation.HIGH_MIDDLE,
                               PitchLocation.HIGH_OUTSIDE]:
            fb_mod += 0.05  # 高めはフライになりやすい

        # 確率計算
        gb_prob = HIT_TYPE_DISTRIBUTION['groundball'] + gb_mod
        ld_prob = HIT_TYPE_DISTRIBUTION['linedrive'] + ld_mod
        fb_prob = HIT_TYPE_DISTRIBUTION['flyball'] + fb_mod + power_fb_mod
        popup_prob = HIT_TYPE_DISTRIBUTION['popup']

        # 正規化
        total = gb_prob + ld_prob + fb_prob + popup_prob
        gb_prob /= total
        ld_prob /= total
        fb_prob /= total
        popup_prob /= total

        # 乱数で決定
        roll = random.random()
        if roll < gb_prob:
            return 'groundball'
        elif roll < gb_prob + ld_prob:
            return 'linedrive'
        elif roll < gb_prob + ld_prob + fb_prob:
            return 'flyball'
        else:
            return 'popup'

    def _determine_contact_quality(self, contact: int, power: int,
                                   pitch: PitchData) -> str:
        """打球質を決定（目標: Soft23%, Medium42%, Hard35%）"""
        # 打者能力による補正
        ability_factor = (contact + power) / 100  # 0.5-1.0程度

        # ボールゾーンは弱い打球になりやすい
        zone_penalty = 0.15 if not pitch.is_strike_zone else 0

        # 確率計算
        soft_prob = CONTACT_QUALITY['soft']['threshold'] + zone_penalty - ability_factor * 0.05
        hard_prob = CONTACT_QUALITY['hard']['threshold'] + ability_factor * 0.08 - zone_penalty
        medium_prob = 1.0 - soft_prob - hard_prob

        roll = random.random()
        if roll < soft_prob:
            return 'soft'
        elif roll < soft_prob + medium_prob:
            return 'medium'
        else:
            return 'hard'

    def _calculate_exit_velocity(self, power: int, contact_quality: str,
                                 pitch_velocity: float, hit_type: str) -> float:
        """打球速度を計算"""
        # 基準速度（打球質に基づく）
        if contact_quality == 'soft':
            base_velo = random.gauss(82, 8)
            max_velo = CONTACT_QUALITY['soft']['max_velo']
        elif contact_quality == 'medium':
            base_velo = random.gauss(115, 10)
            max_velo = CONTACT_QUALITY['medium']['max_velo']
        else:  # hard
            base_velo = random.gauss(148, 10)
            max_velo = CONTACT_QUALITY['hard']['max_velo']

        # パワーによる補正（能力50で基準、10ポイントで約3km/h）
        power_bonus = (power - 50) * 0.3

        # 投球速度の反発（速い球ほど飛ぶ）
        pitch_bonus = (pitch_velocity - 140) * 0.15

        # 打球タイプによる補正
        type_factor = {
            'groundball': 0.95,
            'linedrive': 1.02,
            'flyball': 0.92,
            'popup': 0.70
        }.get(hit_type, 1.0)

        velocity = (base_velo + power_bonus + pitch_bonus) * type_factor
        return max(60, min(max_velo, velocity))

    def _calculate_launch_angle(self, hit_type: str, contact: int,
                                power: int, trajectory: int) -> float:
        """打球角度を計算"""
        angle_range = LAUNCH_ANGLE_RANGES[hit_type]

        # 各タイプに応じた平均角度
        mean_angles = {
            'groundball': 0,
            'linedrive': 17,
            'flyball': 35,
            'popup': 60
        }

        # 標準偏差
        std_devs = {
            'groundball': 6,
            'linedrive': 4,
            'flyball': 6,
            'popup': 5
        }

        mean = mean_angles[hit_type]
        std = std_devs[hit_type]

        # コンタクト能力による安定性
        std *= (1.2 - contact * 0.004)  # 高いcontactほど安定

        angle = random.gauss(mean, std)
        return max(angle_range[0], min(angle_range[1], angle))

    def _calculate_spray_angle(self, contact: int, power: int) -> float:
        """打球方向を計算（センター=0、ライト=正、レフト=負）"""
        # 基本は中央狙い
        mean = 0

        # パワーヒッターは引っ張り傾向
        if power > 70:
            mean += random.choice([-8, 8])  # 引っ張り方向

        # コンタクト能力が高いと方向が安定
        std = 22 - contact * 0.08

        angle = random.gauss(mean, std)
        return max(-45, min(45, angle))


# ========================================
# 守備判定エンジン
# ========================================

class DefenseEngine:
    """守備判定クラス"""

    def __init__(self):
        # 内野手守備位置（ホームからの距離、左右位置）
        self.infield_positions = {
            'first': (28, 15),    # 一塁手
            'second': (32, 8),    # 二塁手
            'short': (35, -8),    # 遊撃手
            'third': (28, -15),   # 三塁手
        }

        # 外野手守備位置
        self.outfield_positions = {
            'left': (85, -25),
            'center': (90, 0),
            'right': (85, 25),
        }

    def judge_result(self, ball: BattedBall, defense: DefenseData,
                     runner_speed: int = 50) -> AtBatResult:
        """打球の結果を判定"""

        # ===== 1. 本塁打判定 =====
        hr_result = self._check_home_run(ball)
        if hr_result:
            return AtBatResult.HOME_RUN

        # ===== 2. 打球タイプ別判定 =====
        if ball.hit_type == 'popup':
            return self._judge_popup(ball, defense)
        elif ball.hit_type == 'groundball':
            return self._judge_groundball(ball, defense, runner_speed)
        elif ball.hit_type == 'linedrive':
            return self._judge_linedrive(ball, defense)
        else:  # flyball
            return self._judge_flyball(ball, defense)

    def _check_home_run(self, ball: BattedBall) -> bool:
        """本塁打判定"""
        # フェンス距離を方向から計算
        fence_dist = self._get_fence_distance(ball.spray_angle)

        # 飛距離がフェンスを超え、かつ適切な角度
        if ball.distance >= fence_dist:
            # 角度が低すぎると直撃（フェンス高さを超える必要）
            min_angle = 15
            if ball.launch_angle >= min_angle:
                return True
            # ギリギリの場合は確率判定
            elif ball.launch_angle >= 10 and random.random() < 0.5:
                return True

        # フェンス際の判定
        if fence_dist - 3 <= ball.distance < fence_dist:
            if ball.launch_angle >= 25 and random.random() < 0.3:
                return True

        return False

    def _get_fence_distance(self, spray_angle: float) -> float:
        """方向に応じたフェンス距離"""
        abs_angle = abs(spray_angle)

        if abs_angle < 15:
            return FIELD_CONSTANTS['fence_center']
        elif abs_angle < 30:
            t = (abs_angle - 15) / 15
            return FIELD_CONSTANTS['fence_center'] - \
                   (FIELD_CONSTANTS['fence_center'] - FIELD_CONSTANTS['fence_left_center']) * t
        else:
            t = (abs_angle - 30) / 15
            return FIELD_CONSTANTS['fence_left_center'] - \
                   (FIELD_CONSTANTS['fence_left_center'] - FIELD_CONSTANTS['fence_left']) * min(1, t)

    def _judge_popup(self, ball: BattedBall, defense: DefenseData) -> AtBatResult:
        """内野フライ判定（目標安打率: 1.5%）"""
        # 内野フライはほぼ確実にアウト
        catch_rate = 0.985 + defense.get_avg_infield() * 0.0003

        if random.random() < catch_rate:
            return AtBatResult.POP_OUT
        return AtBatResult.SINGLE

    def _judge_groundball(self, ball: BattedBall, defense: DefenseData,
                          runner_speed: int) -> AtBatResult:
        """ゴロ判定（目標安打率: 23%）"""

        # 基本アウト率
        base_out_rate = 0.77

        # 守備力による補正
        infield_avg = defense.get_avg_infield()
        defense_bonus = (infield_avg - 50) * 0.003

        # 打球速度による補正
        # 速い打球は抜けやすい、遅い打球は内野安打の可能性
        if ball.exit_velocity > 145:
            speed_bonus = (ball.exit_velocity - 145) * 0.005  # 抜ける確率UP
            base_out_rate -= speed_bonus
        elif ball.exit_velocity < 95:
            # 弱いゴロは足次第
            infield_hit_bonus = (95 - ball.exit_velocity) * 0.003
            runner_bonus = (runner_speed - 50) * 0.004
            if random.random() < infield_hit_bonus + runner_bonus:
                return AtBatResult.INFIELD_HIT

        # 打球方向による補正（三遊間・一二塁間は抜けやすい）
        if abs(ball.spray_angle) > 25:
            gap_bonus = 0.08
            base_out_rate -= gap_bonus

        # 走者速度による内野安打
        infield_hit_rate = 0.05 + (runner_speed - 50) * 0.002

        out_rate = base_out_rate + defense_bonus

        roll = random.random()
        if roll < out_rate:
            return AtBatResult.GROUNDOUT
        elif roll < out_rate + infield_hit_rate:
            return AtBatResult.INFIELD_HIT
        else:
            return AtBatResult.SINGLE

    def _judge_linedrive(self, ball: BattedBall, defense: DefenseData) -> AtBatResult:
        """ライナー判定（目標安打率: 68%）"""

        # ライナーは安打になりやすい
        base_hit_rate = 0.68

        # 守備力による補正
        if ball.distance < 40:
            # 内野ライナー
            defense_val = defense.get_avg_infield()
        else:
            # 外野ライナー
            defense_val = defense.get_avg_outfield()

        defense_penalty = (defense_val - 50) * 0.004

        # 打球速度による補正
        if ball.exit_velocity > 155:
            speed_bonus = 0.08  # 速いライナーは捕りにくい
            base_hit_rate += speed_bonus

        hit_rate = max(0.50, min(0.85, base_hit_rate - defense_penalty))

        if random.random() < hit_rate:
            # 長打判定
            if ball.distance > 85:
                if random.random() < 0.20:
                    return AtBatResult.TRIPLE
                return AtBatResult.DOUBLE
            elif ball.distance > 65 and ball.exit_velocity > 145:
                if random.random() < 0.40:
                    return AtBatResult.DOUBLE
            return AtBatResult.SINGLE
        else:
            return AtBatResult.LINEOUT

    def _judge_flyball(self, ball: BattedBall, defense: DefenseData) -> AtBatResult:
        """フライ判定（目標安打率: 14%、HR除く）"""

        # 基本的にアウト
        base_out_rate = 0.86

        # 外野守備力
        outfield_avg = defense.get_avg_outfield()
        defense_bonus = (outfield_avg - 50) * 0.003

        # 距離による補正（深いフライは捕りにくい）
        if ball.distance > 95:
            distance_penalty = (ball.distance - 95) * 0.008
            base_out_rate -= distance_penalty
        elif ball.distance < 70:
            # 浅いフライは捕りやすい
            base_out_rate += 0.05

        # 滞空時間による補正（長いほど捕りやすい）
        if ball.hang_time > 5.0:
            base_out_rate += 0.03
        elif ball.hang_time < 3.5:
            base_out_rate -= 0.05

        out_rate = max(0.70, min(0.95, base_out_rate + defense_bonus))

        if random.random() < out_rate:
            return AtBatResult.FLYOUT
        else:
            # 安打時の長打判定
            if ball.distance > 100:
                if random.random() < 0.30:
                    return AtBatResult.TRIPLE
                return AtBatResult.DOUBLE
            elif ball.distance > 80:
                if random.random() < 0.50:
                    return AtBatResult.DOUBLE
            return AtBatResult.SINGLE


# ========================================
# 打席シミュレーター
# ========================================

class AtBatSimulator:
    """打席シミュレータークラス"""

    def __init__(self):
        self.ball_generator = BattedBallGenerator()
        self.defense_engine = DefenseEngine()

    def simulate_pitch(self, batter_stats, pitcher_stats,
                       context: AtBatContext, pitch_type: str = None
                       ) -> Tuple[PitchResult, Optional[BattedBall]]:
        """1球をシミュレート

        Returns:
            (投球結果, 打球データ or None)
        """
        # 投球生成
        if pitch_type is None:
            pitch_type = self._select_pitch_type(pitcher_stats, context)

        pitch = self.ball_generator.generate_pitch(pitcher_stats, pitch_type)

        # スイング判定
        will_swing = self.ball_generator.calculate_swing_decision(
            batter_stats, pitch, context
        )

        if not will_swing:
            # 見逃し
            if pitch.is_strike_zone:
                return PitchResult.STRIKE_LOOKING, None
            else:
                return PitchResult.BALL, None

        # コンタクト判定
        contact_success, is_foul = self.ball_generator.calculate_contact(
            batter_stats, pitcher_stats, pitch, True
        )

        if not contact_success:
            return PitchResult.STRIKE_SWINGING, None

        if is_foul:
            return PitchResult.FOUL, None

        # 打球生成
        batted_ball = self.ball_generator.generate_batted_ball(
            batter_stats, pitcher_stats, pitch, context
        )

        return PitchResult.IN_PLAY, batted_ball

    def simulate_at_bat(self, batter_stats, pitcher_stats,
                        defense: DefenseData = None,
                        context: AtBatContext = None,
                        pitch_list: List[str] = None
                        ) -> Tuple[AtBatResult, Dict]:
        """1打席をシミュレート

        Returns:
            (打席結果, 詳細データ)
        """
        if context is None:
            context = AtBatContext()

        if defense is None:
            defense = DefenseData()

        if pitch_list is None:
            pitch_list = self._get_pitcher_repertoire(pitcher_stats)

        # 打者の走力
        runner_speed = getattr(batter_stats, 'run', 50)

        pitch_count = 0
        pitch_log = []

        while True:
            pitch_count += 1

            # 球種選択
            pitch_type = self._select_pitch_type_from_list(
                pitcher_stats, context, pitch_list
            )

            # 投球シミュレーション
            pitch_result, batted_ball = self.simulate_pitch(
                batter_stats, pitcher_stats, context, pitch_type
            )

            # ログ記録
            pitch_log.append({
                'pitch_type': pitch_type,
                'result': pitch_result.value,
                'count': f"{context.balls}-{context.strikes}"
            })

            # 結果処理
            if pitch_result == PitchResult.BALL:
                context.balls += 1
                if context.balls >= 4:
                    return AtBatResult.WALK, self._create_result_data(pitch_log, pitch_count)

            elif pitch_result in [PitchResult.STRIKE_LOOKING, PitchResult.STRIKE_SWINGING]:
                context.strikes += 1
                if context.strikes >= 3:
                    return AtBatResult.STRIKEOUT, self._create_result_data(pitch_log, pitch_count)

            elif pitch_result == PitchResult.FOUL:
                if context.strikes < 2:
                    context.strikes += 1

            elif pitch_result == PitchResult.IN_PLAY:
                # 打球結果判定
                result = self.defense_engine.judge_result(
                    batted_ball, defense, runner_speed
                )

                result_data = self._create_result_data(pitch_log, pitch_count)
                result_data.update({
                    'batted_ball': {
                        'exit_velocity': batted_ball.exit_velocity,
                        'launch_angle': batted_ball.launch_angle,
                        'spray_angle': batted_ball.spray_angle,
                        'distance': batted_ball.distance,
                        'hang_time': batted_ball.hang_time,
                        'hit_type': batted_ball.hit_type,
                        'contact_quality': batted_ball.contact_quality
                    }
                })

                return result, result_data

            # 無限ループ防止
            if pitch_count > 30:
                return AtBatResult.WALK, self._create_result_data(pitch_log, pitch_count)

    def _select_pitch_type(self, pitcher_stats, context: AtBatContext) -> str:
        """球種を選択"""
        breaking_balls = getattr(pitcher_stats, 'breaking_balls', [])

        # 追い込んでいたら変化球
        if context.strikes == 2:
            if breaking_balls and random.random() < 0.7:
                return random.choice(breaking_balls)

        # ボール先行ならストレート
        if context.balls >= 2:
            if random.random() < 0.6:
                return "ストレート"

        # それ以外はランダム
        all_pitches = ["ストレート"] + breaking_balls
        return random.choice(all_pitches) if all_pitches else "ストレート"

    def _select_pitch_type_from_list(self, pitcher_stats, context: AtBatContext,
                                     pitch_list: List[str]) -> str:
        """球種リストから選択"""
        if not pitch_list:
            return "ストレート"

        # 追い込み時は決め球
        if context.strikes == 2 and len(pitch_list) > 1:
            # 変化球優先
            non_fastball = [p for p in pitch_list if p != "ストレート"]
            if non_fastball and random.random() < 0.65:
                return random.choice(non_fastball)

        # ボール先行時はストレート
        if context.balls >= 2:
            if "ストレート" in pitch_list and random.random() < 0.55:
                return "ストレート"

        return random.choice(pitch_list)

    def _get_pitcher_repertoire(self, pitcher_stats) -> List[str]:
        """投手の持ち球リストを取得"""
        breaking_balls = getattr(pitcher_stats, 'breaking_balls', [])
        return ["ストレート"] + breaking_balls if breaking_balls else ["ストレート"]

    def _create_result_data(self, pitch_log: List, pitch_count: int) -> Dict:
        """結果データを作成"""
        return {
            'pitch_count': pitch_count,
            'pitch_log': pitch_log
        }


# ========================================
# グローバルインスタンス
# ========================================

_at_bat_simulator = None


def get_at_bat_simulator() -> AtBatSimulator:
    """シングルトンのシミュレーターを取得"""
    global _at_bat_simulator
    if _at_bat_simulator is None:
        _at_bat_simulator = AtBatSimulator()
    return _at_bat_simulator


# ========================================
# テスト用関数
# ========================================

def test_simulation(num_at_bats: int = 1000):
    """シミュレーションテスト"""
    from dataclasses import dataclass

    @dataclass
    class MockStats:
        contact: int = 50
        power: int = 50
        run: int = 50
        eye: int = 50
        trajectory: int = 2
        speed: int = 50
        control: int = 50
        breaking: int = 50
        stamina: int = 50
        breaking_balls: List[str] = field(default_factory=lambda: ["スライダー", "フォーク"])

    sim = get_at_bat_simulator()

    results = {}
    hit_types = {'groundball': 0, 'linedrive': 0, 'flyball': 0, 'popup': 0}
    contact_qualities = {'soft': 0, 'medium': 0, 'hard': 0}
    total_exit_velo = 0
    batted_balls = 0

    batter = MockStats(contact=55, power=55, run=55, trajectory=2)
    pitcher = MockStats(speed=55, control=55, breaking=55)

    for _ in range(num_at_bats):
        result, data = sim.simulate_at_bat(batter, pitcher)

        results[result] = results.get(result, 0) + 1

        if 'batted_ball' in data:
            bb = data['batted_ball']
            hit_types[bb['hit_type']] += 1
            contact_qualities[bb['contact_quality']] += 1
            total_exit_velo += bb['exit_velocity']
            batted_balls += 1

    print("=== 打席結果分布 ===")
    for result, count in sorted(results.items(), key=lambda x: -x[1]):
        print(f"{result.value}: {count} ({count/num_at_bats*100:.1f}%)")

    print("\n=== 打球タイプ分布 ===")
    for ht, count in hit_types.items():
        pct = count / batted_balls * 100 if batted_balls > 0 else 0
        print(f"{ht}: {count} ({pct:.1f}%)")

    print("\n=== 打球質分布 ===")
    for cq, count in contact_qualities.items():
        pct = count / batted_balls * 100 if batted_balls > 0 else 0
        print(f"{cq}: {count} ({pct:.1f}%)")

    if batted_balls > 0:
        print(f"\n平均打球速度: {total_exit_velo/batted_balls:.1f} km/h")

    # 打率計算
    hits = sum(results.get(r, 0) for r in [
        AtBatResult.SINGLE, AtBatResult.DOUBLE, AtBatResult.TRIPLE,
        AtBatResult.HOME_RUN, AtBatResult.INFIELD_HIT
    ])
    at_bats = num_at_bats - results.get(AtBatResult.WALK, 0) - results.get(AtBatResult.HIT_BY_PITCH, 0)

    if at_bats > 0:
        ba = hits / at_bats
        print(f"\n打率: {ba:.3f}")

    k_rate = results.get(AtBatResult.STRIKEOUT, 0) / num_at_bats
    bb_rate = results.get(AtBatResult.WALK, 0) / num_at_bats
    print(f"三振率: {k_rate*100:.1f}%")
    print(f"四球率: {bb_rate*100:.1f}%")


if __name__ == "__main__":
    test_simulation(1000)
