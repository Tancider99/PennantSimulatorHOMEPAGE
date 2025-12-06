# -*- coding: utf-8 -*-
"""
ライブ試合エンジン

一球単位で試合を進行させるエンジン
投球生成・打球生成・守備判定を統合し、
トラッキングデータを提供する
"""
import random
import math
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict, Any
from enum import Enum


# ========================================
# 定数
# ========================================

# NPB球場寸法
FIELD = {
    'mound_distance': 18.44,
    'base_distance': 27.431,
    'infield_depth': 28.0,
    'fence_center': 122.0,
    'fence_left_center': 116.0,
    'fence_right_center': 116.0,
    'fence_left': 100.0,
    'fence_right': 100.0,
    'fence_height': 4.2,
}

# ストライクゾーン（メートル）
STRIKE_ZONE = {
    'width': 0.432,  # 17インチ = 43.2cm
    'height': 0.56,  # 膝から胸まで約56cm
    'center_x': 0.0,
    'center_z': 0.85,  # 地上85cm（膝上）
}


# ========================================
# 列挙型
# ========================================

class PitchType(Enum):
    """球種"""
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
    """投球結果"""
    BALL = "ボール"
    STRIKE_CALLED = "見逃しストライク"
    STRIKE_SWINGING = "空振り"
    FOUL = "ファウル"
    IN_PLAY = "インプレー"
    HIT_BY_PITCH = "死球"


class BattedBallType(Enum):
    """打球タイプ"""
    GROUNDBALL = "ゴロ"
    LINEDRIVE = "ライナー"
    FLYBALL = "フライ"
    POPUP = "内野フライ"


class PlayResult(Enum):
    """プレー結果"""
    # 安打
    SINGLE = "シングルヒット"
    DOUBLE = "ツーベースヒット"
    TRIPLE = "スリーベースヒット"
    HOME_RUN = "ホームラン"
    INFIELD_HIT = "内野安打"

    # アウト
    STRIKEOUT = "三振"
    GROUNDOUT = "ゴロアウト"
    FLYOUT = "フライアウト"
    LINEOUT = "ライナーアウト"
    POPUP_OUT = "内野フライ"
    DOUBLE_PLAY = "ダブルプレー"

    # その他
    WALK = "四球"
    HIT_BY_PITCH = "死球"
    SACRIFICE_FLY = "犠牲フライ"
    SACRIFICE_BUNT = "犠打"
    ERROR = "エラー"

    # 継続
    FOUL = "ファウル"
    BALL = "ボール"
    STRIKE = "ストライク"


# ========================================
# データクラス
# ========================================

@dataclass
class PitchLocation:
    """投球位置（トラッキングデータ）"""
    x: float  # 横位置（キャッチャー視点で右が正）メートル
    z: float  # 高さ（地面からの高さ）メートル
    is_strike: bool  # ストライクゾーン内か

    def to_zone_coordinates(self) -> Tuple[float, float]:
        """ストライクゾーン座標系に変換（-1〜1の範囲）"""
        zone_x = (self.x - STRIKE_ZONE['center_x']) / (STRIKE_ZONE['width'] / 2)
        zone_z = (self.z - STRIKE_ZONE['center_z']) / (STRIKE_ZONE['height'] / 2)
        return zone_x, zone_z


@dataclass
class PitchData:
    """投球データ（トラッキング情報含む）"""
    pitch_type: str  # 球種名
    velocity: float  # 球速 (km/h)
    spin_rate: int  # 回転数 (rpm)
    horizontal_break: float  # 横変化 (cm)
    vertical_break: float  # 縦変化 (cm)
    location: PitchLocation  # 投球位置
    release_point: Tuple[float, float, float]  # リリースポイント (x, y, z)

    # 軌道データ（描画用）
    trajectory: List[Tuple[float, float, float]] = field(default_factory=list)


@dataclass
class BattedBallData:
    """打球データ（トラッキング情報含む）"""
    exit_velocity: float  # 打球速度 (km/h)
    launch_angle: float  # 打球角度 (度)
    spray_angle: float  # 打球方向 (度) 0=センター、正=ライト、負=レフト
    hit_type: BattedBallType  # 打球タイプ
    distance: float  # 飛距離 (m)
    hang_time: float  # 滞空時間 (s)
    landing_x: float  # 落下地点X (m)
    landing_y: float  # 落下地点Y (m)

    # 軌道データ（描画用）
    trajectory: List[Tuple[float, float, float]] = field(default_factory=list)

    # 打球質
    contact_quality: str = "medium"  # soft/medium/hard


@dataclass
class GameState:
    """試合状態"""
    inning: int = 1
    is_top: bool = True  # 表 = True
    outs: int = 0
    balls: int = 0
    strikes: int = 0

    # 走者 (player_idxとspeed)
    runner_1b: Optional[Tuple[int, int]] = None
    runner_2b: Optional[Tuple[int, int]] = None
    runner_3b: Optional[Tuple[int, int]] = None

    # スコア
    home_score: int = 0
    away_score: int = 0

    # 打順
    home_batter_order: int = 0  # 0-8
    away_batter_order: int = 0

    # 現在の投手インデックス
    home_pitcher_idx: int = -1
    away_pitcher_idx: int = -1

    # 投球数
    home_pitch_count: int = 0
    away_pitch_count: int = 0

    def get_count_string(self) -> str:
        return f"{self.balls}-{self.strikes}"

    def get_runner_string(self) -> str:
        runners = []
        if self.runner_1b:
            runners.append("1塁")
        if self.runner_2b:
            runners.append("2塁")
        if self.runner_3b:
            runners.append("3塁")
        return "・".join(runners) if runners else "無走者"

    def has_runner(self) -> bool:
        return self.runner_1b is not None or self.runner_2b is not None or self.runner_3b is not None

    def is_bases_loaded(self) -> bool:
        return all([self.runner_1b, self.runner_2b, self.runner_3b])

    def count_runners(self) -> int:
        return sum(1 for r in [self.runner_1b, self.runner_2b, self.runner_3b] if r is not None)


@dataclass
class AtBatResult:
    """打席結果"""
    result: PlayResult
    pitch_data: Optional[PitchData] = None
    batted_ball: Optional[BattedBallData] = None
    rbis: int = 0
    runs_scored: List[int] = field(default_factory=list)  # 得点した走者のplayer_idx


# ========================================
# 投球生成エンジン
# ========================================

class PitchGenerator:
    """投球生成クラス"""

    # 球種データ
    PITCH_DATA = {
        "ストレート": {"base_speed": 145, "h_break": 0, "v_break": 12, "spin": 2200},
        "スライダー": {"base_speed": 132, "h_break": -20, "v_break": -3, "spin": 2400},
        "カーブ": {"base_speed": 118, "h_break": -10, "v_break": -28, "spin": 2600},
        "チェンジアップ": {"base_speed": 128, "h_break": 10, "v_break": -18, "spin": 1500},
        "フォーク": {"base_speed": 138, "h_break": 0, "v_break": -35, "spin": 1100},
        "シンカー": {"base_speed": 143, "h_break": 15, "v_break": -10, "spin": 1900},
        "カットボール": {"base_speed": 140, "h_break": -8, "v_break": 3, "spin": 2300},
        "ツーシーム": {"base_speed": 144, "h_break": 12, "v_break": 2, "spin": 2100},
        "シュート": {"base_speed": 138, "h_break": 18, "v_break": -6, "spin": 2000},
        "スプリット": {"base_speed": 140, "h_break": 3, "v_break": -28, "spin": 1300},
    }

    def __init__(self):
        pass

    def generate_pitch(self, pitcher_stats, pitch_type: str = None,
                       game_state: GameState = None) -> PitchData:
        """投球を生成

        Args:
            pitcher_stats: 投手の能力値
            pitch_type: 球種（Noneの場合はAI選択）
            game_state: 試合状況

        Returns:
            PitchData: 投球データ
        """
        # 能力値取得
        speed = getattr(pitcher_stats, 'speed', 50)
        control = getattr(pitcher_stats, 'control', 50)
        breaking = getattr(pitcher_stats, 'breaking', 50)

        # 球種選択
        if pitch_type is None:
            pitch_type = self._select_pitch_type(pitcher_stats, game_state)

        # 基本データ取得
        base = self.PITCH_DATA.get(pitch_type, self.PITCH_DATA["ストレート"])

        # 球速計算（能力50で基準、±15km/h程度の変動）
        velocity = base["base_speed"] + (speed - 50) * 0.3 + random.gauss(0, 1.5)
        velocity = max(100, min(165, velocity))

        # 変化量（変化球能力で補正）
        break_factor = 1 + (breaking - 50) * 0.01
        h_break = base["h_break"] * break_factor + random.gauss(0, 2)
        v_break = base["v_break"] * break_factor + random.gauss(0, 2)

        # 回転数
        spin_rate = base["spin"] + (speed - 50) * 5 + random.randint(-150, 150)

        # 投球位置計算
        location = self._calculate_location(control, game_state)

        # リリースポイント
        release_point = (
            random.gauss(0, 0.05),  # 左右のブレ
            18.44,  # マウンド距離
            1.8 + random.gauss(0, 0.05)  # リリース高さ
        )

        # 軌道計算
        trajectory = self._calculate_trajectory(
            velocity, h_break, v_break, location, release_point
        )

        return PitchData(
            pitch_type=pitch_type,
            velocity=round(velocity, 1),
            spin_rate=spin_rate,
            horizontal_break=round(h_break, 1),
            vertical_break=round(v_break, 1),
            location=location,
            release_point=release_point,
            trajectory=trajectory
        )

    def _select_pitch_type(self, pitcher_stats, game_state: GameState = None) -> str:
        """球種をAI選択"""
        # 投手の持ち球リスト
        breaking_balls = getattr(pitcher_stats, 'breaking_balls', [])
        if not breaking_balls:
            breaking_balls = ["スライダー"]

        all_pitches = ["ストレート"] + breaking_balls

        if game_state is None:
            return random.choice(all_pitches)

        # カウントに応じた球種選択
        if game_state.strikes == 2:
            # 追い込んだら決め球
            if random.random() < 0.65:
                return random.choice(breaking_balls) if breaking_balls else "ストレート"
        elif game_state.balls >= 2:
            # ボール先行ならストレート
            if random.random() < 0.55:
                return "ストレート"

        return random.choice(all_pitches)

    def _calculate_location(self, control: int, game_state: GameState = None) -> PitchLocation:
        """投球位置を計算"""
        # コントロールによる制球のばらつき
        # 能力50で標準偏差0.15m、80で0.08m程度
        std_dev = 0.20 - control * 0.0015

        # 基本的にストライクゾーン中心を狙う
        target_x = random.gauss(0, std_dev)
        target_z = random.gauss(STRIKE_ZONE['center_z'], std_dev * 0.8)

        # カウントによる調整
        if game_state:
            if game_state.balls >= 3:
                # ボール3つならストライク狙い
                target_x *= 0.7
                target_z = STRIKE_ZONE['center_z'] + random.gauss(0, std_dev * 0.6)
            elif game_state.strikes == 2:
                # 追い込んだらボール球で誘う
                if random.random() < 0.4:
                    # 低めのボール球
                    target_z = STRIKE_ZONE['center_z'] - STRIKE_ZONE['height'] * 0.8

        # ストライクゾーン判定
        half_width = STRIKE_ZONE['width'] / 2
        half_height = STRIKE_ZONE['height'] / 2
        is_strike = (
            abs(target_x) <= half_width and
            abs(target_z - STRIKE_ZONE['center_z']) <= half_height
        )

        return PitchLocation(x=target_x, z=target_z, is_strike=is_strike)

    def _calculate_trajectory(self, velocity: float, h_break: float, v_break: float,
                              location: PitchLocation, release: Tuple) -> List[Tuple]:
        """投球軌道を計算（描画用）"""
        trajectory = []
        steps = 20

        for i in range(steps + 1):
            t = i / steps
            # 簡易的な軌道計算（実際はより複雑）
            x = release[0] + (location.x - release[0]) * t + (h_break / 100) * t * (1 - t) * 4
            y = release[1] * (1 - t)
            z = release[2] + (location.z - release[2]) * t - 4.9 * (t * 0.4) ** 2 + (v_break / 100) * t

            trajectory.append((x, y, z))

        return trajectory


# ========================================
# 打球生成エンジン
# ========================================

class BattedBallGenerator:
    """打球生成クラス"""

    def __init__(self):
        pass

    def generate_batted_ball(self, batter_stats, pitcher_stats,
                             pitch: PitchData) -> Optional[BattedBallData]:
        """打球を生成

        Args:
            batter_stats: 打者能力
            pitcher_stats: 投手能力
            pitch: 投球データ

        Returns:
            BattedBallData or None（空振り/見逃しの場合）
        """
        contact = getattr(batter_stats, 'contact', 50)
        power = getattr(batter_stats, 'power', 50)
        trajectory_type = getattr(batter_stats, 'trajectory', 2)

        # 打球タイプ決定
        hit_type = self._determine_hit_type(contact, power, trajectory_type, pitch)

        # 打球質決定
        contact_quality = self._determine_contact_quality(contact, power, pitch)

        # 打球速度
        exit_velocity = self._calculate_exit_velocity(power, contact_quality, pitch)

        # 打球角度
        launch_angle = self._calculate_launch_angle(hit_type, contact, trajectory_type)

        # 打球方向
        spray_angle = self._calculate_spray_angle(contact, pitch)

        # 飛距離と軌道を計算
        distance, hang_time, landing_x, landing_y, trajectory = self._calculate_trajectory(
            exit_velocity, launch_angle, spray_angle
        )

        return BattedBallData(
            exit_velocity=round(exit_velocity, 1),
            launch_angle=round(launch_angle, 1),
            spray_angle=round(spray_angle, 1),
            hit_type=hit_type,
            distance=round(distance, 1),
            hang_time=round(hang_time, 2),
            landing_x=round(landing_x, 1),
            landing_y=round(landing_y, 1),
            trajectory=trajectory,
            contact_quality=contact_quality
        )

    def _determine_hit_type(self, contact: int, power: int, trajectory: int,
                           pitch: PitchData) -> BattedBallType:
        """打球タイプを決定"""
        # 弾道による補正
        gb_mod = {1: 0.12, 2: 0.02, 3: 0.0, 4: -0.12}.get(trajectory, 0)
        fb_mod = {1: -0.10, 2: -0.03, 3: 0.0, 4: 0.12}.get(trajectory, 0)

        # 投球位置による補正
        if pitch.location.z < STRIKE_ZONE['center_z'] - 0.15:
            gb_mod += 0.08  # 低めはゴロ
        elif pitch.location.z > STRIKE_ZONE['center_z'] + 0.15:
            fb_mod += 0.08  # 高めはフライ

        # 確率計算（目標: GB45%, LD10%, FB35%, IFFB10%）
        gb_prob = 0.45 + gb_mod
        ld_prob = 0.10
        fb_prob = 0.35 + fb_mod
        popup_prob = 0.10

        total = gb_prob + ld_prob + fb_prob + popup_prob
        roll = random.random() * total

        if roll < gb_prob:
            return BattedBallType.GROUNDBALL
        elif roll < gb_prob + ld_prob:
            return BattedBallType.LINEDRIVE
        elif roll < gb_prob + ld_prob + fb_prob:
            return BattedBallType.FLYBALL
        else:
            return BattedBallType.POPUP

    def _determine_contact_quality(self, contact: int, power: int,
                                   pitch: PitchData) -> str:
        """打球質を決定"""
        # ボール球は弱い打球になりやすい
        zone_penalty = 0.12 if not pitch.location.is_strike else 0

        # 確率計算（目標: Soft23%, Medium42%, Hard35%）
        soft_prob = 0.23 + zone_penalty
        hard_prob = 0.35 - zone_penalty + (power - 50) * 0.003
        medium_prob = 1.0 - soft_prob - hard_prob

        roll = random.random()
        if roll < soft_prob:
            return "soft"
        elif roll < soft_prob + medium_prob:
            return "medium"
        else:
            return "hard"

    def _calculate_exit_velocity(self, power: int, contact_quality: str,
                                 pitch: PitchData) -> float:
        """打球速度を計算"""
        if contact_quality == "soft":
            base = random.gauss(82, 8)
            max_velo = 95
        elif contact_quality == "medium":
            base = random.gauss(115, 10)
            max_velo = 135
        else:  # hard
            base = random.gauss(148, 10)
            max_velo = 185

        power_bonus = (power - 50) * 0.3
        pitch_bonus = (pitch.velocity - 140) * 0.12

        velocity = base + power_bonus + pitch_bonus
        return max(60, min(max_velo, velocity))

    def _calculate_launch_angle(self, hit_type: BattedBallType, contact: int,
                                trajectory: int) -> float:
        """打球角度を計算"""
        ranges = {
            BattedBallType.GROUNDBALL: (-10, 10, 0, 5),
            BattedBallType.LINEDRIVE: (10, 25, 17, 4),
            BattedBallType.FLYBALL: (25, 50, 35, 6),
            BattedBallType.POPUP: (50, 75, 60, 5),
        }
        min_a, max_a, mean, std = ranges[hit_type]
        angle = random.gauss(mean, std)
        return max(min_a, min(max_a, angle))

    def _calculate_spray_angle(self, contact: int, pitch: PitchData) -> float:
        """打球方向を計算"""
        std = 22 - contact * 0.08
        angle = random.gauss(0, std)
        return max(-45, min(45, angle))

    def _calculate_trajectory(self, exit_velocity: float, launch_angle: float,
                              spray_angle: float) -> Tuple:
        """打球軌道を計算"""
        v0 = exit_velocity / 3.6
        angle_rad = math.radians(launch_angle)
        spray_rad = math.radians(spray_angle)

        vx = v0 * math.cos(angle_rad) * math.sin(spray_rad)
        vy = v0 * math.cos(angle_rad) * math.cos(spray_rad)
        vz = v0 * math.sin(angle_rad)

        g = 9.8
        drag = 0.35
        dt = 0.05

        x, y, z = 0, 0, 1.0
        t = 0
        trajectory = [(x, y, z)]

        while z >= 0 and t < 10:
            speed = math.sqrt(vx**2 + vy**2 + vz**2)
            if speed > 0:
                d = 0.5 * 1.2 * 0.0042 * drag * speed**2 / 0.145
                vx -= d * vx / speed * dt
                vy -= d * vy / speed * dt
                vz -= (g + d * vz / speed) * dt

            x += vx * dt
            y += vy * dt
            z += vz * dt
            t += dt

            if len(trajectory) < 100:
                trajectory.append((x, y, max(0, z)))

        distance = math.sqrt(x**2 + y**2)
        return distance, t, x, y, trajectory


# ========================================
# スイング判定エンジン
# ========================================

class SwingDecisionEngine:
    """スイング判定クラス"""

    def decide_swing(self, batter_stats, pitch: PitchData,
                     game_state: GameState) -> bool:
        """スイングするかを判定"""
        contact = getattr(batter_stats, 'contact', 50)
        eye = getattr(batter_stats, 'eye', contact)
        eye_factor = eye / 100

        if pitch.location.is_strike:
            # ストライクを見逃す確率
            looking_prob = 0.20 - eye_factor * 0.10
            if game_state.strikes == 2:
                looking_prob *= 0.3
            return random.random() > looking_prob
        else:
            # ボール球を振る確率
            chase_prob = 0.20 - eye_factor * 0.10
            if game_state.strikes == 2:
                chase_prob += 0.15
            return random.random() < chase_prob

    def decide_contact(self, batter_stats, pitcher_stats,
                       pitch: PitchData) -> Tuple[bool, bool]:
        """コンタクト判定

        Returns:
            (コンタクト成功, ファウルか)
        """
        contact = getattr(batter_stats, 'contact', 50)
        p_speed = getattr(pitcher_stats, 'speed', 50)
        p_breaking = getattr(pitcher_stats, 'breaking', 50)

        # 基本コンタクト率
        base_rate = 0.55 + contact * 0.003

        # 投手能力ペナルティ
        penalty = ((p_speed + p_breaking) / 2 - 50) * 0.004

        # 球速ペナルティ
        if pitch.velocity > 150:
            penalty += (pitch.velocity - 150) * 0.008
        elif pitch.velocity > 145:
            penalty += (pitch.velocity - 145) * 0.003

        # 変化量ペナルティ
        total_break = abs(pitch.horizontal_break) + abs(pitch.vertical_break)
        if total_break > 20:
            penalty += (total_break - 20) * 0.004

        # ボール球ペナルティ
        if not pitch.location.is_strike:
            penalty += 0.15

        contact_rate = max(0.30, min(0.92, base_rate - penalty))

        if random.random() > contact_rate:
            return False, False

        # ファウル判定
        foul_rate = 0.35 if pitch.location.is_strike else 0.50
        is_foul = random.random() < foul_rate

        return True, is_foul


# ========================================
# 守備判定エンジン
# ========================================

class DefenseEngine:
    """守備判定クラス"""

    def judge_result(self, batted_ball: BattedBallData,
                     defense_stats: Dict = None,
                     runner_speed: int = 50) -> PlayResult:
        """打球結果を判定"""
        # 本塁打判定
        if self._is_home_run(batted_ball):
            return PlayResult.HOME_RUN

        # 打球タイプ別判定
        if batted_ball.hit_type == BattedBallType.POPUP:
            return self._judge_popup(batted_ball)
        elif batted_ball.hit_type == BattedBallType.GROUNDBALL:
            return self._judge_groundball(batted_ball, runner_speed)
        elif batted_ball.hit_type == BattedBallType.LINEDRIVE:
            return self._judge_linedrive(batted_ball)
        else:
            return self._judge_flyball(batted_ball)

    def _is_home_run(self, ball: BattedBallData) -> bool:
        """本塁打判定"""
        fence = self._get_fence_distance(ball.spray_angle)
        return ball.distance >= fence and ball.launch_angle >= 15

    def _get_fence_distance(self, spray_angle: float) -> float:
        """フェンス距離を取得"""
        abs_angle = abs(spray_angle)
        if abs_angle < 15:
            return FIELD['fence_center']
        elif abs_angle < 30:
            t = (abs_angle - 15) / 15
            return FIELD['fence_center'] - (FIELD['fence_center'] - FIELD['fence_left_center']) * t
        else:
            t = (abs_angle - 30) / 15
            return FIELD['fence_left_center'] - (FIELD['fence_left_center'] - FIELD['fence_left']) * min(1, t)

    def _judge_popup(self, ball: BattedBallData) -> PlayResult:
        """内野フライ判定"""
        if random.random() < 0.985:
            return PlayResult.POPUP_OUT
        return PlayResult.SINGLE

    def _judge_groundball(self, ball: BattedBallData, runner_speed: int) -> PlayResult:
        """ゴロ判定"""
        out_rate = 0.77

        if ball.exit_velocity > 145:
            out_rate -= (ball.exit_velocity - 145) * 0.005
        elif ball.exit_velocity < 95:
            if random.random() < 0.12 + (runner_speed - 50) * 0.003:
                return PlayResult.INFIELD_HIT

        if abs(ball.spray_angle) > 25:
            out_rate -= 0.08

        if random.random() < out_rate:
            return PlayResult.GROUNDOUT
        return PlayResult.SINGLE

    def _judge_linedrive(self, ball: BattedBallData) -> PlayResult:
        """ライナー判定"""
        hit_rate = 0.68

        if ball.exit_velocity > 155:
            hit_rate += 0.08

        if random.random() < hit_rate:
            if ball.distance > 85:
                return PlayResult.TRIPLE if random.random() < 0.20 else PlayResult.DOUBLE
            elif ball.distance > 65:
                return PlayResult.DOUBLE if random.random() < 0.40 else PlayResult.SINGLE
            return PlayResult.SINGLE
        return PlayResult.LINEOUT

    def _judge_flyball(self, ball: BattedBallData) -> PlayResult:
        """フライ判定"""
        out_rate = 0.86

        if ball.distance > 95:
            out_rate -= (ball.distance - 95) * 0.008
        elif ball.distance < 70:
            out_rate += 0.05

        if random.random() < out_rate:
            return PlayResult.FLYOUT

        if ball.distance > 100:
            return PlayResult.TRIPLE if random.random() < 0.30 else PlayResult.DOUBLE
        elif ball.distance > 80:
            return PlayResult.DOUBLE if random.random() < 0.50 else PlayResult.SINGLE
        return PlayResult.SINGLE


# ========================================
# ライブ試合エンジン
# ========================================

class LiveGameEngine:
    """ライブ試合エンジン - 一球単位で進行"""

    def __init__(self, home_team, away_team):
        self.home_team = home_team
        self.away_team = away_team

        # エンジン初期化
        self.pitch_generator = PitchGenerator()
        self.batted_ball_generator = BattedBallGenerator()
        self.swing_engine = SwingDecisionEngine()
        self.defense_engine = DefenseEngine()

        # 試合状態
        self.state = GameState()
        self._init_game()

        # 履歴
        self.pitch_history: List[PitchData] = []
        self.play_log: List[str] = []

        # イニングスコア
        self.inning_scores_home: List[int] = []
        self.inning_scores_away: List[int] = []
        self.current_inning_runs: int = 0

    def _init_game(self):
        """試合初期化"""
        # 先発投手設定
        if self.home_team.starting_pitcher_idx >= 0:
            self.state.home_pitcher_idx = self.home_team.starting_pitcher_idx
        elif self.home_team.rotation:
            self.state.home_pitcher_idx = self.home_team.rotation[0]

        if self.away_team.starting_pitcher_idx >= 0:
            self.state.away_pitcher_idx = self.away_team.starting_pitcher_idx
        elif self.away_team.rotation:
            self.state.away_pitcher_idx = self.away_team.rotation[0]

    def get_current_batter(self):
        """現在の打者を取得"""
        if self.state.is_top:
            team = self.away_team
            order = self.state.away_batter_order % 9
        else:
            team = self.home_team
            order = self.state.home_batter_order % 9

        if team.current_lineup and len(team.current_lineup) > order:
            idx = team.current_lineup[order]
            if 0 <= idx < len(team.players):
                return team.players[idx], idx

        return team.players[order] if order < len(team.players) else None, order

    def get_current_pitcher(self):
        """現在の投手を取得"""
        if self.state.is_top:
            team = self.home_team
            idx = self.state.home_pitcher_idx
        else:
            team = self.away_team
            idx = self.state.away_pitcher_idx

        if 0 <= idx < len(team.players):
            return team.players[idx], idx
        return None, -1

    def simulate_pitch(self, pitch_type: str = None) -> Tuple[PitchResult, PitchData, Optional[BattedBallData]]:
        """一球をシミュレート

        Returns:
            (投球結果, 投球データ, 打球データ or None)
        """
        batter, batter_idx = self.get_current_batter()
        pitcher, pitcher_idx = self.get_current_pitcher()

        if batter is None or pitcher is None:
            return PitchResult.BALL, None, None

        # 投球生成
        pitch = self.pitch_generator.generate_pitch(
            pitcher.stats, pitch_type, self.state
        )
        self.pitch_history.append(pitch)

        # 投球数カウント
        if self.state.is_top:
            self.state.home_pitch_count += 1
        else:
            self.state.away_pitch_count += 1

        # スイング判定
        will_swing = self.swing_engine.decide_swing(batter.stats, pitch, self.state)

        if not will_swing:
            if pitch.location.is_strike:
                return PitchResult.STRIKE_CALLED, pitch, None
            else:
                return PitchResult.BALL, pitch, None

        # コンタクト判定
        contact_success, is_foul = self.swing_engine.decide_contact(
            batter.stats, pitcher.stats, pitch
        )

        if not contact_success:
            return PitchResult.STRIKE_SWINGING, pitch, None

        if is_foul:
            return PitchResult.FOUL, pitch, None

        # 打球生成
        batted_ball = self.batted_ball_generator.generate_batted_ball(
            batter.stats, pitcher.stats, pitch
        )

        return PitchResult.IN_PLAY, pitch, batted_ball

    def process_pitch_result(self, pitch_result: PitchResult, pitch: PitchData,
                             batted_ball: BattedBallData = None) -> Optional[PlayResult]:
        """投球結果を処理してプレー結果を返す

        Returns:
            PlayResult or None（打席継続の場合）
        """
        if pitch_result == PitchResult.BALL:
            self.state.balls += 1
            if self.state.balls >= 4:
                return self._process_walk()
            return None

        elif pitch_result in [PitchResult.STRIKE_CALLED, PitchResult.STRIKE_SWINGING]:
            self.state.strikes += 1
            if self.state.strikes >= 3:
                return self._process_strikeout()
            return None

        elif pitch_result == PitchResult.FOUL:
            if self.state.strikes < 2:
                self.state.strikes += 1
            return None

        elif pitch_result == PitchResult.IN_PLAY:
            batter, _ = self.get_current_batter()
            runner_speed = getattr(batter.stats, 'run', 50) if batter else 50

            play_result = self.defense_engine.judge_result(batted_ball, None, runner_speed)
            return self._process_play_result(play_result, batted_ball)

        return None

    def _process_walk(self) -> PlayResult:
        """四球処理"""
        batter, batter_idx = self.get_current_batter()
        batter_speed = getattr(batter.stats, 'run', 50) if batter else 50

        # 押し出し判定
        rbis = 0
        if self.state.is_bases_loaded():
            rbis = 1
            if self.state.is_top:
                self.state.away_score += 1
            else:
                self.state.home_score += 1
            self.current_inning_runs += 1
            self.state.runner_3b = None

        # 走者進塁
        if self.state.runner_1b and self.state.runner_2b:
            self.state.runner_3b = self.state.runner_2b
        if self.state.runner_1b:
            self.state.runner_2b = self.state.runner_1b
        self.state.runner_1b = (batter_idx, batter_speed)

        self._advance_batter()
        self._reset_count()

        return PlayResult.WALK

    def _process_strikeout(self) -> PlayResult:
        """三振処理"""
        self.state.outs += 1
        self._advance_batter()
        self._reset_count()

        if self.state.outs >= 3:
            self._end_half_inning()

        return PlayResult.STRIKEOUT

    def _process_play_result(self, result: PlayResult, batted_ball: BattedBallData) -> PlayResult:
        """打球結果を処理"""
        batter, batter_idx = self.get_current_batter()
        batter_speed = getattr(batter.stats, 'run', 50) if batter else 50

        if result == PlayResult.HOME_RUN:
            runs = 1 + self.state.count_runners()
            if self.state.is_top:
                self.state.away_score += runs
            else:
                self.state.home_score += runs
            self.current_inning_runs += runs
            self.state.runner_1b = None
            self.state.runner_2b = None
            self.state.runner_3b = None

        elif result == PlayResult.TRIPLE:
            runs = self._score_all_runners()
            self.state.runner_3b = (batter_idx, batter_speed)

        elif result == PlayResult.DOUBLE:
            runs = self._process_double(batter_idx, batter_speed)

        elif result in [PlayResult.SINGLE, PlayResult.INFIELD_HIT]:
            runs = self._process_single(batter_idx, batter_speed)

        elif result in [PlayResult.GROUNDOUT, PlayResult.FLYOUT, PlayResult.LINEOUT, PlayResult.POPUP_OUT]:
            self.state.outs += 1
            if result == PlayResult.FLYOUT and self.state.outs < 3 and self.state.runner_3b:
                # 犠牲フライ判定
                if random.random() < 0.65:
                    self._score_runner_3b()
                    result = PlayResult.SACRIFICE_FLY

        self._advance_batter()
        self._reset_count()

        if self.state.outs >= 3:
            self._end_half_inning()

        return result

    def _process_single(self, batter_idx: int, batter_speed: int) -> int:
        """単打時の走者処理"""
        runs = 0

        if self.state.runner_3b:
            runs += 1
            if self.state.is_top:
                self.state.away_score += 1
            else:
                self.state.home_score += 1
            self.current_inning_runs += 1
            self.state.runner_3b = None

        if self.state.runner_2b:
            speed = self.state.runner_2b[1]
            if speed >= 55 and random.random() < 0.55:
                runs += 1
                if self.state.is_top:
                    self.state.away_score += 1
                else:
                    self.state.home_score += 1
                self.current_inning_runs += 1
            else:
                self.state.runner_3b = self.state.runner_2b
            self.state.runner_2b = None

        if self.state.runner_1b:
            speed = self.state.runner_1b[1]
            if speed >= 70 and random.random() < 0.25:
                self.state.runner_3b = self.state.runner_1b
            else:
                self.state.runner_2b = self.state.runner_1b
            self.state.runner_1b = None

        self.state.runner_1b = (batter_idx, batter_speed)
        return runs

    def _process_double(self, batter_idx: int, batter_speed: int) -> int:
        """二塁打時の走者処理"""
        runs = 0

        if self.state.runner_3b:
            runs += 1
            if self.state.is_top:
                self.state.away_score += 1
            else:
                self.state.home_score += 1
            self.current_inning_runs += 1
            self.state.runner_3b = None

        if self.state.runner_2b:
            runs += 1
            if self.state.is_top:
                self.state.away_score += 1
            else:
                self.state.home_score += 1
            self.current_inning_runs += 1
            self.state.runner_2b = None

        if self.state.runner_1b:
            speed = self.state.runner_1b[1]
            if speed >= 65 and random.random() < 0.40:
                runs += 1
                if self.state.is_top:
                    self.state.away_score += 1
                else:
                    self.state.home_score += 1
                self.current_inning_runs += 1
            else:
                self.state.runner_3b = self.state.runner_1b
            self.state.runner_1b = None

        self.state.runner_2b = (batter_idx, batter_speed)
        return runs

    def _score_all_runners(self) -> int:
        """全走者を生還"""
        runs = self.state.count_runners()
        if runs > 0:
            if self.state.is_top:
                self.state.away_score += runs
            else:
                self.state.home_score += runs
            self.current_inning_runs += runs

        self.state.runner_1b = None
        self.state.runner_2b = None
        self.state.runner_3b = None
        return runs

    def _score_runner_3b(self):
        """三塁走者を生還"""
        if self.state.runner_3b:
            if self.state.is_top:
                self.state.away_score += 1
            else:
                self.state.home_score += 1
            self.current_inning_runs += 1
            self.state.runner_3b = None

    def _advance_batter(self):
        """打順を進める"""
        if self.state.is_top:
            self.state.away_batter_order = (self.state.away_batter_order + 1) % 9
        else:
            self.state.home_batter_order = (self.state.home_batter_order + 1) % 9

    def _reset_count(self):
        """カウントリセット"""
        self.state.balls = 0
        self.state.strikes = 0
        self.pitch_history.clear()

    def _end_half_inning(self):
        """半イニング終了"""
        # イニングスコア記録
        if self.state.is_top:
            self.inning_scores_away.append(self.current_inning_runs)
        else:
            self.inning_scores_home.append(self.current_inning_runs)

        self.current_inning_runs = 0

        # 状態リセット
        self.state.outs = 0
        self.state.runner_1b = None
        self.state.runner_2b = None
        self.state.runner_3b = None
        self._reset_count()

        if self.state.is_top:
            self.state.is_top = False
        else:
            self.state.is_top = True
            self.state.inning += 1

    def is_game_over(self) -> bool:
        """試合終了判定"""
        # 9回裏終了
        if self.state.inning > 9:
            return True

        # 9回裏、ホームがリード
        if self.state.inning == 9 and not self.state.is_top:
            if self.state.home_score > self.state.away_score:
                return True

        # サヨナラ
        if self.state.inning >= 9 and not self.state.is_top:
            if self.state.home_score > self.state.away_score and self.state.outs >= 3:
                return True

        return False

    def get_winner(self) -> Optional[str]:
        """勝者を取得"""
        if self.state.home_score > self.state.away_score:
            return self.home_team.name
        elif self.state.away_score > self.state.home_score:
            return self.away_team.name
        return None


# ========================================
# 便利関数
# ========================================

def create_live_game(home_team, away_team) -> LiveGameEngine:
    """ライブゲームを作成"""
    return LiveGameEngine(home_team, away_team)
