# -*- coding: utf-8 -*-
"""
試合シミュレーター（打球物理演算版）
打球速度・角度・方向を計算し、各打球の結果を判定
作戦機能: 継投、代打、代走、バント、盗塁、敬遠
"""
import random
import math
from typing import Tuple, List, Optional, Dict
from enum import Enum
from dataclasses import dataclass, field
from models import Team, Player

# 物理演算エンジンをインポート
try:
    from physics_engine import get_at_bat_simulator, HitResult, get_physics_engine
    PHYSICS_ENABLED = True
except ImportError:
    PHYSICS_ENABLED = False

# 新しい打席エンジンをインポート
try:
    from at_bat_engine import (
        get_at_bat_simulator as get_new_at_bat_simulator,
        AtBatResult, DefenseData, AtBatContext
    )
    NEW_ENGINE_ENABLED = True
except ImportError:
    NEW_ENGINE_ENABLED = False


# ========================================
# 打球物理計算モジュール
# ========================================
@dataclass
class BattedBall:
    """打球データ"""
    exit_velocity: float    # 打球速度 (km/h)
    launch_angle: float     # 打球角度 (度) 上向きが正
    spray_angle: float      # 打球方向 (度) 中堅を0とし、左方向が負、右方向が正
    hang_time: float = 0.0  # 滞空時間 (秒)
    distance: float = 0.0   # 飛距離 (m)
    
    def __post_init__(self):
        """飛距離と滞空時間を計算"""
        # 空気抵抗を考慮した簡易飛距離計算
        v0 = self.exit_velocity / 3.6  # m/s に変換
        angle_rad = math.radians(self.launch_angle)
        
        # 重力加速度
        g = 9.8
        
        # 空気抵抗係数（野球ボール）
        drag_factor = 0.35
        
        # 初速成分
        vx = v0 * math.cos(angle_rad)
        vy = v0 * math.sin(angle_rad)
        
        # 空気抵抗を考慮した飛距離（簡易モデル）
        if self.launch_angle > 0:
            # 飛球
            t_flight = (2 * vy / g) * (1 - drag_factor * 0.3)
            self.hang_time = max(0.5, t_flight)
            self.distance = vx * self.hang_time * (1 - drag_factor)
        else:
            # ゴロ
            self.hang_time = 0.3 + abs(self.launch_angle) / 30  # ゴロの到達時間
            self.distance = vx * self.hang_time * 0.7  # 地面での減速


class BattedBallCalculator:
    """打球物理計算クラス"""
    
    # 野球場の定数（NPB平均的な球場）
    INFIELD_DEPTH = 27.4        # 内野手の守備位置 (m)
    OUTFIELD_START = 75.0       # 外野フェンス開始 (m)
    CENTER_FIELD_FENCE = 122.0  # センターフェンス距離 (m)
    CORNER_FENCE = 100.0        # 両翼フェンス距離 (m)
    
    @staticmethod
    def calculate_batted_ball(batter_stats, pitcher_stats, pitch_type: str = "fastball") -> BattedBall:
        """打球データを計算
        
        Args:
            batter_stats: 打者の能力値
            pitcher_stats: 投手の能力値
            pitch_type: 球種
        
        Returns:
            BattedBall: 打球データ
        """
        # 打者能力値の取得（内部値1-20を100スケールに変換）
        raw_contact = getattr(batter_stats, 'contact', 50)
        raw_power = getattr(batter_stats, 'power', 50)
        contact = batter_stats.to_100_scale(raw_contact) if hasattr(batter_stats, 'to_100_scale') else raw_contact * 5
        power = batter_stats.to_100_scale(raw_power) if hasattr(batter_stats, 'to_100_scale') else raw_power * 5
        
        # 投手能力値の取得（内部値1-20を100スケールに変換）
        raw_p_speed = getattr(pitcher_stats, 'speed', 50)
        raw_p_control = getattr(pitcher_stats, 'control', 50)
        raw_p_breaking = getattr(pitcher_stats, 'breaking', 50)
        p_speed = pitcher_stats.to_100_scale(raw_p_speed) if hasattr(pitcher_stats, 'to_100_scale') else raw_p_speed * 5
        p_control = pitcher_stats.to_100_scale(raw_p_control) if hasattr(pitcher_stats, 'to_100_scale') else raw_p_control * 5
        p_breaking = pitcher_stats.to_100_scale(raw_p_breaking) if hasattr(pitcher_stats, 'to_100_scale') else raw_p_breaking * 5
        
        # ===== 打球速度の計算 (km/h) =====
        # NPB平均: 約130km/h、強打で165km/h以上
        # パワーと投球速度が影響（投手の球が速いほど反発で速くなる）
        base_velocity = 95  # 基本打球速度
        power_bonus = (power - 40) * 0.8  # パワー40が基準（下げた）
        pitch_velocity_factor = p_speed * 0.2  # 投球速度の反発（弱める）
        
        # ランダム要素（芯に当たるか）
        sweet_spot = random.gauss(0, 18)  # 標準偏差18km/h
        
        exit_velocity = base_velocity + power_bonus + pitch_velocity_factor + sweet_spot
        exit_velocity = max(70, min(175, exit_velocity))  # 70-175 km/h
        
        # ===== 打球角度の計算 (度) =====
        # NPB平均: 約10-15度、フライ: 25-35度、ゴロ: -10~0度
        # ミートが高いほど角度のコントロールが良い
        
        # 基本角度（パワーヒッターは高め狙い）
        target_angle = 10 + (power - contact) * 0.12
        
        # ブレ（ミートが低いとブレる、投手の能力も影響）
        control_effect = (100 - contact) * 0.15 + p_breaking * 0.05
        angle_deviation = random.gauss(0, 15 + control_effect)
        
        launch_angle = target_angle + angle_deviation
        launch_angle = max(-20, min(60, launch_angle))  # -20~60度
        
        # ===== 打球方向の計算 (度) =====
        # 0度=センター、負=レフト方向、正=ライト方向
        # 右打者はレフト方向、左打者はライト方向が多い傾向
        
        # ランダムな打球方向（引っ張り/流し）
        spray_angle = random.gauss(0, 25)  # 標準偏差25度
        
        # ミートが高いと狙った方向に打てる
        if contact >= 70:
            spray_angle *= 0.8  # 方向のブレを抑制
        
        spray_angle = max(-45, min(45, spray_angle))  # -45~45度
        
        return BattedBall(exit_velocity, launch_angle, spray_angle)
    
    @staticmethod
    def judge_result(ball: BattedBall, fielding_stats: Dict = None) -> Tuple[str, str]:
        """打球の結果を判定
        
        Args:
            ball: 打球データ
            fielding_stats: 守備側の能力値（オプション）
        
        Returns:
            (結果, 説明)
        """
        ev = ball.exit_velocity
        la = ball.launch_angle
        dist = ball.distance
        spray = ball.spray_angle
        
        # 守備能力（平均50）
        avg_fielding = 50
        if fielding_stats:
            avg_fielding = fielding_stats.get('fielding', 50)
        
        # フェンス距離（方向による）
        fence_dist = BattedBallCalculator.CENTER_FIELD_FENCE - abs(spray) * 0.5
        
        # ===== ホームラン判定 =====
        if la >= 20 and la <= 40 and dist >= fence_dist:
            return "home_run", f"飛距離{dist:.0f}m、打球速度{ev:.0f}km/h"
        
        # ===== フライアウト/長打判定 =====
        if la >= 15:
            # 外野フライ
            if dist >= BattedBallCalculator.OUTFIELD_START:
                # 外野への飛球
                catch_difficulty = (dist - 75) / 50 + (ev - 120) / 100
                catch_chance = 0.85 - catch_difficulty * 0.2 + (avg_fielding - 50) * 0.005
                
                if random.random() > catch_chance:
                    # ヒット（二塁打/三塁打）
                    if dist >= 110:
                        return "triple", f"三塁打！{dist:.0f}m"
                    elif dist >= 90:
                        return "double", f"二塁打！{dist:.0f}m"
                    else:
                        return "single", f"外野ヒット {dist:.0f}m"
                else:
                    return "flyout", f"外野フライ {dist:.0f}m"
            else:
                # 内野フライ/ポップフライ
                return "flyout", f"内野フライ"
        
        # ===== ライナー判定 =====
        elif 5 <= la < 15:
            # ライナー（速度が重要）
            if ev >= 140:
                # 強烈なライナー
                catch_chance = 0.5 + (avg_fielding - 50) * 0.01
                if random.random() > catch_chance:
                    if dist >= 70:
                        return "double", f"強烈なライナー二塁打！{ev:.0f}km/h"
                    return "single", f"ライナーヒット {ev:.0f}km/h"
                return "lineout", f"好捕！ライナー {ev:.0f}km/h"
            else:
                # 普通のライナー
                catch_chance = 0.7 + (avg_fielding - 50) * 0.008
                if random.random() > catch_chance:
                    return "single", f"ライナーヒット"
                return "lineout", f"ライナーアウト"
        
        # ===== ゴロ判定 =====
        else:
            # ゴロ（速度と方向で判定）
            # 内野ゴロの処理時間
            reaction_time = 0.3  # 反応時間
            throw_time = 1.5 - avg_fielding * 0.01  # 送球時間
            
            # 一塁到達時間（打者の足）
            runner_speed = 50  # デフォルト
            first_base_time = 4.2 - runner_speed * 0.015  # 4.2秒基準
            
            # ゴロの処理
            if ev >= 130:
                # 強烈なゴロ
                if abs(spray) > 30:
                    # 三遊間/一二塁間を抜ける可能性
                    hit_chance = 0.4 + (ev - 130) * 0.01
                    if random.random() < hit_chance:
                        return "single", f"強襲ヒット！{ev:.0f}km/h"
                
                # 内野安打の可能性
                infield_hit_chance = 0.1 + (runner_speed - 50) * 0.005
                if random.random() < infield_hit_chance:
                    return "single", f"内野安打！"
                
                return "groundout", f"内野ゴロ {ev:.0f}km/h"
            else:
                # 普通のゴロ
                # 守備位置による捕球判定
                if abs(spray) > 35:
                    # 際どい当たり
                    if random.random() < 0.25:
                        return "single", f"三遊間（一二塁間）を抜けた！"
                
                return "groundout", f"内野ゴロ"
    
    @staticmethod
    def simulate_swing(batter_stats, pitcher_stats) -> Tuple[str, BattedBall, str]:
        """スイング結果をシミュレート
        
        Returns:
            (結果タイプ, 打球データまたはNone, 説明)
        """
        # 打者能力値の取得（内部値1-20を100スケールに変換）
        raw_contact = getattr(batter_stats, 'contact', 50)
        raw_eye = getattr(batter_stats, 'eye', 50)
        contact = batter_stats.to_100_scale(raw_contact) if hasattr(batter_stats, 'to_100_scale') else raw_contact * 5
        eye = batter_stats.to_100_scale(raw_eye) if hasattr(batter_stats, 'to_100_scale') else raw_eye * 5
        
        # 投手能力値の取得（内部値1-20を100スケールに変換）
        raw_p_speed = getattr(pitcher_stats, 'speed', 50)
        raw_p_control = getattr(pitcher_stats, 'control', 50)
        raw_p_breaking = getattr(pitcher_stats, 'breaking', 50)
        p_speed = pitcher_stats.to_100_scale(raw_p_speed) if hasattr(pitcher_stats, 'to_100_scale') else raw_p_speed * 5
        p_control = pitcher_stats.to_100_scale(raw_p_control) if hasattr(pitcher_stats, 'to_100_scale') else raw_p_control * 5
        p_breaking = pitcher_stats.to_100_scale(raw_p_breaking) if hasattr(pitcher_stats, 'to_100_scale') else raw_p_breaking * 5
        
        # ===== まずスイングするかどうか =====
        # ストライクゾーン判定（投手の制球力が高いほどストライク率上昇）
        strike_rate = 0.45 + p_control * 0.003
        is_strike = random.random() < strike_rate
        
        if is_strike:
            # ストライク
            # スイング判定（ミートが高いほど適切にスイング）
            swing_chance = 0.65 + (contact - 40) * 0.004
            will_swing = random.random() < swing_chance
            
            if will_swing:
                # コンタクト判定（投手能力が打者能力を抑える）
                pitcher_effectiveness = (p_speed + p_breaking) / 2
                contact_chance = 0.55 + (contact - 40) * 0.005 - (pitcher_effectiveness - 40) * 0.003
                contact_chance = max(0.25, min(0.85, contact_chance))
                
                if random.random() < contact_chance:
                    # 打球発生
                    ball = BattedBallCalculator.calculate_batted_ball(batter_stats, pitcher_stats)
                    result, desc = BattedBallCalculator.judge_result(ball)
                    return result, ball, desc
                else:
                    # 空振り
                    return "swing_miss", None, "空振り"
            else:
                # 見逃しストライク
                return "called_strike", None, "見逃しストライク"
        else:
            # ボール
            # 振るかどうか（選球眼が高いほどボール球を見逃す）
            chase_chance = 0.40 - eye * 0.004
            chase_chance = max(0.08, min(0.45, chase_chance))
            
            if random.random() < chase_chance:
                # ボール球をスイング
                contact_chance = 0.25 + (contact - 40) * 0.003
                if random.random() < contact_chance:
                    # ファウルか弱い打球
                    if random.random() < 0.65:
                        return "foul", None, "ファウル"
                    ball = BattedBallCalculator.calculate_batted_ball(batter_stats, pitcher_stats)
                    ball.exit_velocity *= 0.75  # ボール球なので弱い打球
                    result, desc = BattedBallCalculator.judge_result(ball)
                    return result, ball, desc
                else:
                    return "swing_miss", None, "ボール球空振り"
            else:
                # ボール見逃し
                return "ball", None, "ボール"


class TacticType(Enum):
    """作戦タイプ"""
    NONE = "なし"
    BUNT = "バント"
    SACRIFICE_BUNT = "犠牲バント"
    SQUEEZE = "スクイズ"
    HIT_AND_RUN = "ヒットエンドラン"
    STEAL = "盗塁"
    INTENTIONAL_WALK = "敬遠"
    PINCH_HIT = "代打"
    PINCH_RUN = "代走"
    PITCHING_CHANGE = "継投"


@dataclass
class GameState:
    """試合の状態"""
    inning: int = 1
    is_top: bool = True  # 表/裏
    outs: int = 0
    runners: List[bool] = field(default_factory=lambda: [False, False, False])  # 1塁,2塁,3塁
    home_score: int = 0
    away_score: int = 0
    pitch_count: int = 0  # 投球数
    
    def get_runner_situation(self) -> str:
        """走者状況の文字列"""
        if not any(self.runners):
            return "無走者"
        parts = []
        if self.runners[0]: parts.append("1塁")
        if self.runners[1]: parts.append("2塁")
        if self.runners[2]: parts.append("3塁")
        return ",".join(parts)


class TacticManager:
    """作戦マネージャー - AI・自動判断用"""
    
    @staticmethod
    def should_bunt(batter: Player, game_state: GameState, is_player_team: bool = False) -> bool:
        """バントすべき状況か判断"""
        # 送りバント: 無死or1死で走者1塁、打者が非力
        if game_state.outs <= 1 and game_state.runners[0] and not game_state.runners[2]:
            if batter.stats.power < 50 and batter.stats.contact < 60:
                return random.random() < 0.6
        return False
    
    @staticmethod
    def should_squeeze(batter: Player, game_state: GameState) -> bool:
        """スクイズすべき状況か判断"""
        # 1死以下、3塁走者あり、1点が重要な場面
        if game_state.outs <= 1 and game_state.runners[2]:
            if game_state.is_top:
                score_diff = game_state.away_score - game_state.home_score
            else:
                score_diff = game_state.home_score - game_state.away_score
            if abs(score_diff) <= 2 and game_state.inning >= 7:
                return random.random() < 0.3
        return False
    
    @staticmethod
    def should_steal(runner: Player, game_state: GameState, pitcher: Player) -> bool:
        """盗塁すべき状況か判断"""
        # 走者の足が速く、投手の牽制が弱い場合
        if game_state.outs < 2 and game_state.runners[0] and not game_state.runners[1]:
            runner_speed = runner.stats.speed if runner else 50
            if runner_speed >= 70:
                return random.random() < 0.25
            elif runner_speed >= 60:
                return random.random() < 0.15
        return False
    
    @staticmethod
    def should_intentional_walk(batter: Player, game_state: GameState, next_batter: Player) -> bool:
        """敬遠すべき状況か判断"""
        # 強打者で1塁が空いている場合
        if not game_state.runners[0]:
            batter_overall = batter.stats.contact * 0.5 + batter.stats.power * 0.5
            next_overall = next_batter.stats.contact * 0.5 + next_batter.stats.power * 0.5 if next_batter else 50
            if batter_overall > 75 and batter_overall > next_overall + 10:
                if game_state.runners[1] or game_state.runners[2]:  # 得点圏走者
                    return random.random() < 0.4
        return False
    
    @staticmethod
    def should_change_pitcher(pitcher: Player, game_state: GameState, team: Team, 
                              pitcher_stats: Dict = None) -> Tuple[bool, str]:
        """継投すべきか判断（パワプロ風スタミナ制）
        
        スタミナに基づいて投球数上限が決まる:
        - スタミナS(90+): 130球前後
        - スタミナA(80-89): 120球前後
        - スタミナB(70-79): 110球前後
        - スタミナC(60-69): 100球前後
        - スタミナD(50-59): 90球前後
        - スタミナE(40-49): 80球前後
        - スタミナF以下: 70球前後
        """
        if pitcher_stats is None:
            pitcher_stats = {}
        
        pitch_count = pitcher_stats.get('pitch_count', 0)
        hits_allowed = pitcher_stats.get('hits', 0)
        walks_allowed = pitcher_stats.get('walks', 0)
        runs_allowed = pitcher_stats.get('runs', 0)
        innings_pitched = pitcher_stats.get('innings', 0)
        
        # 投手のスタミナ値を取得（1-99スケール）
        stamina = getattr(pitcher.stats, 'stamina', 50)
        
        # スタミナに基づく投球数上限を計算
        # 基準: スタミナ50で100球、スタミナ10ごとに±10球
        base_pitch_limit = 100
        stamina_bonus = (stamina - 50) * 0.6  # スタミナ50基準で±30球範囲
        pitch_limit = int(base_pitch_limit + stamina_bonus)
        pitch_limit = max(60, min(140, pitch_limit))  # 60-140球の範囲
        
        # 投手タイプによる調整
        from models import PitchType
        
        if pitcher.pitch_type == PitchType.STARTER:
            # 先発投手
            # スタミナ切れ判定（投球数が上限に達したら交代）
            if pitch_count >= pitch_limit:
                return True, f"球数制限({pitch_count}球)"
            
            # 上限の80%で疲労が見え始める
            fatigue_threshold = pitch_limit * 0.8
            if pitch_count >= fatigue_threshold:
                # 疲労状態での被打・失点が多い場合は交代
                if runs_allowed >= 3 and innings_pitched >= 5:
                    return True, "疲労+失点"
                if hits_allowed >= 10:
                    return True, "被安打多"
            
            # KO（大量失点）
            if runs_allowed >= 5 and innings_pitched < 5:
                return True, "KO"
            
            # 完投ペースかチェック（スタミナ高い投手のみ）
            if stamina >= 70 and pitch_count < pitch_limit * 0.7 and runs_allowed <= 2:
                # 完投の可能性があるので続投
                if innings_pitched >= 7:
                    pass  # 続投
        
        # 中継ぎ: スタミナに応じて1-2イニング
        elif pitcher.pitch_type == PitchType.RELIEVER:
            reliever_limit = 30 + (stamina - 50) * 0.3  # 中継ぎは30球基準
            reliever_limit = max(20, min(50, reliever_limit))
            
            if pitch_count >= reliever_limit:
                return True, "中継ぎ交代"
            if innings_pitched >= 2:
                return True, "中継ぎ交代"
            if hits_allowed >= 3 and innings_pitched < 2:
                return True, "炎上"
        
        # 抑え: 1イニング限定（スタミナ高い場合は2イニングも可）
        elif pitcher.pitch_type == PitchType.CLOSER:
            closer_limit = 25 + (stamina - 50) * 0.2
            closer_limit = max(20, min(40, closer_limit))
            
            if innings_pitched >= 1 and pitch_count >= closer_limit:
                return True, "抑え完了"
            if innings_pitched >= 2:
                return True, "抑え完了"
        
        return False, ""
    
    @staticmethod
    def get_pitch_limit_by_stamina(stamina: int) -> int:
        """スタミナ値から投球数上限を計算"""
        base_pitch_limit = 100
        stamina_bonus = (stamina - 50) * 0.6
        pitch_limit = int(base_pitch_limit + stamina_bonus)
        return max(60, min(140, pitch_limit))
    
    @staticmethod
    def should_pinch_hit(batter: Player, game_state: GameState, team: Team) -> Tuple[bool, Optional[Player]]:
        """代打を出すべきか判断"""
        # 終盤で投手の打席、または弱打者の重要な場面
        if game_state.inning >= 7:
            # 投手の打席
            from models import Position
            if batter.position == Position.PITCHER:
                bench = [p for p in team.players if p not in team.current_lineup and p.position != Position.PITCHER]
                if bench:
                    best_pinch = max(bench, key=lambda p: p.stats.contact * 0.5 + p.stats.power * 0.5)
                    return True, best_pinch
            
            # チャンスで弱打者
            if (game_state.runners[1] or game_state.runners[2]) and batter.stats.contact < 50:
                bench = [p for p in team.players if p not in team.current_lineup and p.position != Position.PITCHER]
                if bench:
                    better_hitters = [p for p in bench if p.stats.contact > batter.stats.contact + 15]
                    if better_hitters:
                        return True, max(better_hitters, key=lambda p: p.stats.contact)
        
        return False, None


class GameSimulator:
    """試合シミュレーター"""

    def __init__(self, home_team: Team, away_team: Team, use_physics: bool = False,
                 fast_mode: bool = True, use_new_engine: bool = True):
        """
        Args:
            home_team: ホームチーム
            away_team: アウェイチーム
            use_physics: 物理演算を使用するか
            fast_mode: 高速モード（軽量計算）
            use_new_engine: 新しい打席エンジン(at_bat_engine)を使用するか
        """
        self.home_team = home_team
        self.away_team = away_team
        self.home_score = 0
        self.away_score = 0
        self.inning = 1
        self.max_innings = 9
        self.log = []
        self.detailed_log = []  # 詳細ログ（物理データ含む）

        # 作戦・継投管理
        self.tactic_manager = TacticManager()
        self.home_pitcher_stats = {'pitch_count': 0, 'hits': 0, 'walks': 0, 'runs': 0, 'innings': 0}
        self.away_pitcher_stats = {'pitch_count': 0, 'hits': 0, 'walks': 0, 'runs': 0, 'innings': 0}
        self.current_home_pitcher_idx = home_team.starting_pitcher_idx
        self.current_away_pitcher_idx = away_team.starting_pitcher_idx

        # プレイヤーからの戦略指示
        self.next_tactic = None  # "bunt", "squeeze", "steal", "hit_and_run", "intentional_walk", "pitch_out"
        self.defensive_shift = None  # "infield_in", "no_doubles", etc.

        # 試合進行状態（UI表示用）
        self.is_top_inning = True
        self.current_outs = 0
        self.current_runners = [False, False, False]
        self.current_batter_idx = 0
        self.current_pitcher_idx = 0

        # 高速モード（デフォルトでON）- 物理演算をスキップして軽量計算
        self.fast_mode = fast_mode

        # イニングスコア（NPB公式風表示用）
        self.inning_scores_home = []  # ホームチームの各回得点
        self.inning_scores_away = []  # アウェイチームの各回得点

        # 選手別成績（試合中）
        self.batting_results = {}  # {player_idx: {'ab': 0, 'hits': 0, 'rbi': 0, 'hr': 0, 'bb': 0, 'so': 0}}
        self.pitching_results = {}  # {player_idx: {'ip': 0.0, 'h': 0, 'r': 0, 'er': 0, 'bb': 0, 'so': 0, 'np': 0}}

        # 投手リレー記録
        self.home_pitchers_used = []  # [(player_idx, innings_pitched, runs_allowed)]
        self.away_pitchers_used = []

        # 新しい打席エンジンを使用するかどうか
        self.use_new_engine = use_new_engine and NEW_ENGINE_ENABLED and not fast_mode
        if self.use_new_engine:
            self.new_at_bat_sim = get_new_at_bat_simulator()

        # 物理演算を使用するかどうか（高速モードでは無効）
        self.use_physics = use_physics and PHYSICS_ENABLED and not fast_mode and not use_new_engine
        if self.use_physics:
            self.at_bat_sim = get_at_bat_simulator()
            self.physics = get_physics_engine()
            # 球場の気象条件を設定（ランダム）
            self.physics.set_weather(
                wind_x=random.uniform(-5, 5),
                wind_y=random.uniform(-3, 3),
                temp=random.uniform(15, 30),
                humidity=random.uniform(40, 70)
            )
    
    def _init_batter_stats(self, team: Team, player_idx: int):
        """打者成績を初期化"""
        key = (team.name, player_idx)
        if key not in self.batting_results:
            self.batting_results[key] = {
                'ab': 0, 'hits': 0, 'rbi': 0, 'hr': 0, 'bb': 0, 'so': 0, 'runs': 0
            }
    
    def _init_pitcher_stats(self, team: Team, player_idx: int):
        """投手成績を初期化"""
        key = (team.name, player_idx)
        if key not in self.pitching_results:
            self.pitching_results[key] = {
                'ip': 0.0, 'h': 0, 'r': 0, 'er': 0, 'bb': 0, 'so': 0, 'np': 0
            }
    
    def _record_at_bat(self, batting_team: Team, batter_idx: int, result: str, rbi: int = 0):
        """打席結果を記録"""
        self._init_batter_stats(batting_team, batter_idx)
        key = (batting_team.name, batter_idx)
        stats = self.batting_results[key]
        
        if result in ['single', 'double', 'triple', 'homerun']:
            stats['ab'] += 1
            stats['hits'] += 1
            if result == 'homerun':
                stats['hr'] += 1
        elif result in ['out', 'strikeout', 'flyout', 'groundout', 'double_play']:
            stats['ab'] += 1
            if result == 'strikeout':
                stats['so'] += 1
        elif result in ['walk', 'hit_by_pitch']:
            stats['bb'] += 1
        
        stats['rbi'] += rbi
    
    def _record_pitcher_result(self, pitching_team: Team, pitcher_idx: int, result: str):
        """投手の被打席結果を記録"""
        self._init_pitcher_stats(pitching_team, pitcher_idx)
        key = (pitching_team.name, pitcher_idx)
        stats = self.pitching_results[key]
        stats['np'] += 1  # 球数（簡易的に打席ごとにカウント）
        
        if result in ['single', 'double', 'triple', 'homerun']:
            stats['h'] += 1
        elif result == 'strikeout':
            stats['so'] += 1
        elif result in ['walk', 'hit_by_pitch']:
            stats['bb'] += 1
    
    def execute_bunt(self, batter: Player, runners: List[bool]) -> Tuple[str, List[bool]]:
        """バント実行"""
        success_rate = 0.7 + batter.stats.contact * 0.002  # ミートが高いほど成功率UP
        
        if random.random() < success_rate:
            # 成功: 走者進塁、打者アウト
            new_runners = [False, runners[0], runners[1]]
            self.log.append(f"  {batter.name} 送りバント成功")
            return "bunt_out", new_runners
        else:
            # 失敗: ファウルか小フライ
            if random.random() < 0.5:
                self.log.append(f"  {batter.name} バント失敗（ファウル）")
                return "foul", runners
            else:
                self.log.append(f"  {batter.name} バント失敗（小フライ）")
                return "out", runners
    
    def execute_squeeze(self, batter: Player, runners: List[bool]) -> Tuple[str, int, List[bool]]:
        """スクイズ実行"""
        success_rate = 0.6 + batter.stats.contact * 0.002
        
        if runners[2] and random.random() < success_rate:
            # 成功: 3塁走者生還
            new_runners = [False, runners[0], runners[1]]
            self.log.append(f"  {batter.name} スクイズ成功！1点追加")
            return "squeeze_success", 1, new_runners
        else:
            # 失敗
            self.log.append(f"  {batter.name} スクイズ失敗")
            return "out", 0, runners
    
    def execute_steal(self, runner: Player, catcher: Player) -> bool:
        """盗塁実行"""
        # 成功率 = 走者の足 vs 捕手の肩
        runner_speed = runner.stats.speed if runner else 50
        catcher_arm = catcher.stats.arm if catcher else 60
        
        success_rate = 0.6 + (runner_speed - catcher_arm) * 0.005
        success_rate = max(0.3, min(0.9, success_rate))
        
        if random.random() < success_rate:
            self.log.append(f"  {runner.name} 盗塁成功！")
            return True
        else:
            self.log.append(f"  {runner.name} 盗塁失敗！アウト")
            return False
    
    def execute_intentional_walk(self, batter: Player) -> Tuple[str, List[bool]]:
        """敬遠実行"""
        self.log.append(f"  {batter.name} 敬遠四球")
        batter.record.walks += 1
        return "intentional_walk", [True, False, False]  # 走者状況は呼び出し側で処理
    
    def check_pitching_change(self, is_home_pitching: bool) -> bool:
        """継投チェックと実行（AI支援）"""
        from ai_system import ai_manager
        
        if is_home_pitching:
            pitcher_idx = self.current_home_pitcher_idx
            team = self.home_team
            stats = self.home_pitcher_stats
        else:
            pitcher_idx = self.current_away_pitcher_idx
            team = self.away_team
            stats = self.away_pitcher_stats
        
        if pitcher_idx < 0 or pitcher_idx >= len(team.players):
            return False
        
        pitcher = team.players[pitcher_idx]
        
        # AI継投判断
        score_diff = self.home_score - self.away_score if is_home_pitching else self.away_score - self.home_score
        game_state_dict = {
            'inning': self.inning,
            'score_diff': score_diff,
            'pitch_count': stats.get('pitch_count', 0),
            'hits_allowed': stats.get('hits', 0),
            'is_defending': True
        }
        
        suggestion = ai_manager.suggest_pitching_change(team, pitcher_idx, stats.get('pitch_count', 0), game_state_dict)
        
        if suggestion:
            new_idx, reason = suggestion
            if new_idx >= 0 and new_idx < len(team.players):
                new_pitcher = team.players[new_idx]
                if is_home_pitching:
                    self.current_home_pitcher_idx = new_idx
                    self.home_pitcher_stats = {'pitch_count': 0, 'hits': 0, 'walks': 0, 'runs': 0, 'innings': 0}
                else:
                    self.current_away_pitcher_idx = new_idx
                    self.away_pitcher_stats = {'pitch_count': 0, 'hits': 0, 'walks': 0, 'runs': 0, 'innings': 0}
                
                self.log.append(f"  継投: {pitcher.name} -> {new_pitcher.name} ({reason})")
                return True
        
        # 従来ロジックでもチェック
        game_state = GameState(
            inning=self.inning,
            home_score=self.home_score,
            away_score=self.away_score
        )
        
        should_change, reason = self.tactic_manager.should_change_pitcher(pitcher, game_state, team, stats)
        
        if should_change:
            # 継投実行
            new_pitcher = None
            
            # 9回僅差リードなら抑え
            score_diff = self.home_score - self.away_score if is_home_pitching else self.away_score - self.home_score
            if self.inning >= 9 and 0 < score_diff <= 3:
                new_pitcher = team.get_closer()
            
            # それ以外は中継ぎ
            if not new_pitcher:
                new_pitcher = team.get_setup_pitcher()
            
            if new_pitcher:
                new_idx = team.players.index(new_pitcher)
                if is_home_pitching:
                    self.current_home_pitcher_idx = new_idx
                    self.home_pitcher_stats = {'pitch_count': 0, 'hits': 0, 'walks': 0, 'runs': 0, 'innings': 0}
                else:
                    self.current_away_pitcher_idx = new_idx
                    self.away_pitcher_stats = {'pitch_count': 0, 'hits': 0, 'walks': 0, 'runs': 0, 'innings': 0}
                
                self.log.append(f"  継投: {pitcher.name} → {new_pitcher.name} ({reason})")
                return True
        
        return False
    
    def simulate_at_bat_physics(self, batter: Player, pitcher: Player) -> Tuple[str, int, dict]:
        """物理演算を使った打席シミュレーション"""
        b_stats = batter.stats
        p_stats = pitcher.stats
        
        # 投手の持ち球リストを取得
        pitch_list = getattr(p_stats, 'breaking_balls', [])
        if not pitch_list:
            pitch_list = ["ストレート", "スライダー"]
        else:
            pitch_list = ["ストレート"] + pitch_list
        
        # 打席シミュレーション
        result, details = self.at_bat_sim.simulate_at_bat(b_stats, p_stats, pitch_list)
        
        # 結果を文字列に変換
        result_map = {
            HitResult.HOME_RUN: "home_run",
            HitResult.TRIPLE: "triple",
            HitResult.DOUBLE: "double",
            HitResult.SINGLE: "single",
            HitResult.INFIELD_HIT: "single",
            HitResult.FLYOUT: "out",
            HitResult.GROUNDOUT: "out",
            HitResult.LINEOUT: "out",
            HitResult.STRIKEOUT: "strikeout",
            HitResult.WALK: "walk",
            HitResult.HIT_BY_PITCH: "walk",
            HitResult.ERROR: "single",
        }
        
        result_str = result_map.get(result, "out")
        direct_runs = 1 if result == HitResult.HOME_RUN else 0
        
        # 成績記録
        if result_str == "home_run":
            batter.record.home_runs += 1
            batter.record.hits += 1
            batter.record.at_bats += 1
            batter.record.runs += 1
            pitcher.record.hits_allowed += 1
        elif result_str == "triple":
            batter.record.hits += 1
            batter.record.at_bats += 1
            batter.record.triples += 1
            pitcher.record.hits_allowed += 1
        elif result_str == "double":
            batter.record.hits += 1
            batter.record.at_bats += 1
            batter.record.doubles += 1
            pitcher.record.hits_allowed += 1
        elif result_str == "single":
            batter.record.hits += 1
            batter.record.at_bats += 1
            pitcher.record.hits_allowed += 1
        elif result_str == "walk":
            batter.record.walks += 1
            pitcher.record.walks_allowed += 1
        elif result_str == "strikeout":
            batter.record.strikeouts += 1
            batter.record.at_bats += 1
            pitcher.record.strikeouts_pitched += 1
        else:
            batter.record.at_bats += 1
        
        return result_str, direct_runs, details
    
    def simulate_at_bat(self, batter: Player, pitcher: Player) -> Tuple[str, int]:
        """打席をシミュレート（打球物理計算版）

        打球速度、角度、方向を計算し、各打球の結果を判定
        投手と野手の能力値に基づいて試合結果を計算
        """
        # 新しい打席エンジンを使用する場合
        if self.use_new_engine:
            return self._simulate_at_bat_new_engine(batter, pitcher)

        b_stats = batter.stats
        p_stats = pitcher.stats

        # 打者の能力値（内部値1-20を100スケールに変換）
        raw_contact = getattr(b_stats, 'contact', 50)
        raw_power = getattr(b_stats, 'power', 50)
        raw_speed = getattr(b_stats, 'run', 50)  # 走力
        raw_eye = getattr(b_stats, 'eye', raw_contact)  # eyeがない場合はcontactで代用
        
        contact = b_stats.to_100_scale(raw_contact) if hasattr(b_stats, 'to_100_scale') else raw_contact * 5
        power = b_stats.to_100_scale(raw_power) if hasattr(b_stats, 'to_100_scale') else raw_power * 5
        speed = b_stats.to_100_scale(raw_speed) if hasattr(b_stats, 'to_100_scale') else raw_speed * 5
        eye = b_stats.to_100_scale(raw_eye) if hasattr(b_stats, 'to_100_scale') else raw_eye * 5
        
        # 投手の能力値（内部値1-20を100スケールに変換）
        raw_p_speed = getattr(p_stats, 'speed', 50)
        raw_p_control = getattr(p_stats, 'control', 50)
        raw_p_breaking = getattr(p_stats, 'breaking', 50)
        
        p_speed = p_stats.to_100_scale(raw_p_speed) if hasattr(p_stats, 'to_100_scale') else raw_p_speed * 5
        p_control = p_stats.to_100_scale(raw_p_control) if hasattr(p_stats, 'to_100_scale') else raw_p_control * 5
        p_breaking = p_stats.to_100_scale(raw_p_breaking) if hasattr(p_stats, 'to_100_scale') else raw_p_breaking * 5
        
        # ===== 打席のシミュレーション（球数カウント）=====
        balls = 0
        strikes = 0
        foul_count = 0
        
        while balls < 4 and strikes < 3:
            # 1球ごとのシミュレーション
            result_type, batted_ball, desc = BattedBallCalculator.simulate_swing(b_stats, p_stats)
            
            if result_type == "ball":
                balls += 1
            elif result_type == "called_strike":
                strikes += 1
            elif result_type == "swing_miss":
                strikes += 1
            elif result_type == "foul":
                if strikes < 2:
                    strikes += 1
                foul_count += 1
                # ファウルが続きすぎたら打球が出る
                if foul_count >= 5 and random.random() < 0.3:
                    batted_ball = BattedBallCalculator.calculate_batted_ball(b_stats, p_stats)
                    result_type, desc = BattedBallCalculator.judge_result(batted_ball)
                    break
            else:
                # 打球が発生した
                break
        
        # ===== 結果の判定 =====
        if balls >= 4:
            # 四球
            batter.record.walks += 1
            pitcher.record.walks_allowed += 1
            return "walk", 0
        
        if strikes >= 3 and result_type in ["swing_miss", "called_strike"]:
            # 三振
            batter.record.strikeouts += 1
            batter.record.at_bats += 1
            pitcher.record.strikeouts_pitched += 1
            return "strikeout", 0
        
        # 打球が発生した場合の結果処理
        if batted_ball:
            result = result_type
            
            # 成績記録
            if result == "home_run":
                batter.record.home_runs += 1
                batter.record.hits += 1
                batter.record.at_bats += 1
                batter.record.runs += 1
                batter.record.rbis += 1
                pitcher.record.hits_allowed += 1
                return "home_run", 1
            elif result == "triple":
                batter.record.hits += 1
                batter.record.at_bats += 1
                batter.record.triples += 1
                pitcher.record.hits_allowed += 1
                return "triple", 0
            elif result == "double":
                batter.record.hits += 1
                batter.record.at_bats += 1
                batter.record.doubles += 1
                pitcher.record.hits_allowed += 1
                return "double", 0
            elif result == "single":
                batter.record.hits += 1
                batter.record.at_bats += 1
                pitcher.record.hits_allowed += 1
                return "single", 0
            elif result in ["flyout", "lineout"]:
                batter.record.at_bats += 1
                return "out", 0
            elif result == "groundout":
                batter.record.at_bats += 1
                # 内野安打の可能性（足の速い選手 - 100スケールの能力値を使用）
                infield_hit_chance = 0.03 + (speed - 40) * 0.003
                infield_hit_chance = max(0.01, min(0.20, infield_hit_chance))
                if random.random() < infield_hit_chance:
                    batter.record.hits += 1
                    pitcher.record.hits_allowed += 1
                    return "single", 0
                return "out", 0
            else:
                batter.record.at_bats += 1
                return "out", 0
        
        # 予期しない結果
        batter.record.at_bats += 1
        return "out", 0

    def _simulate_at_bat_new_engine(self, batter: Player, pitcher: Player) -> Tuple[str, int]:
        """新しい打席エンジン(at_bat_engine)を使用した打席シミュレーション

        NPBの実績データに基づいた精密なシミュレーション:
        - 打率: .254
        - 三振率: 21.5%
        - 四球率: 7.8%
        - ゴロ率: 45%, ライナー率: 10%, フライ率: 45%
        """
        b_stats = batter.stats
        p_stats = pitcher.stats
        speed = getattr(b_stats, 'run', 50)

        # 守備データを作成
        defense = DefenseData()

        # 投手の持ち球
        pitch_list = ["ストレート"]
        if hasattr(p_stats, 'breaking_balls') and p_stats.breaking_balls:
            pitch_list.extend(p_stats.breaking_balls)

        # 打席状況
        context = AtBatContext(
            balls=0,
            strikes=0,
            outs=self.current_outs,
            runners=self.current_runners.copy(),
            inning=self.inning,
            is_top=self.is_top_inning,
            score_diff=self.away_score - self.home_score if self.is_top_inning else self.home_score - self.away_score
        )

        # 打席シミュレーション
        result, data = self.new_at_bat_sim.simulate_at_bat(
            b_stats, p_stats, defense, context, pitch_list
        )

        # 結果を文字列に変換して成績を記録
        if result == AtBatResult.HOME_RUN:
            batter.record.home_runs += 1
            batter.record.hits += 1
            batter.record.at_bats += 1
            batter.record.runs += 1
            batter.record.rbis += 1
            pitcher.record.hits_allowed += 1
            pitcher.record.home_runs_allowed += 1
            return "home_run", 1

        elif result == AtBatResult.TRIPLE:
            batter.record.hits += 1
            batter.record.at_bats += 1
            batter.record.triples += 1
            pitcher.record.hits_allowed += 1
            return "triple", 0

        elif result == AtBatResult.DOUBLE:
            batter.record.hits += 1
            batter.record.at_bats += 1
            batter.record.doubles += 1
            pitcher.record.hits_allowed += 1
            return "double", 0

        elif result in [AtBatResult.SINGLE, AtBatResult.INFIELD_HIT]:
            batter.record.hits += 1
            batter.record.at_bats += 1
            pitcher.record.hits_allowed += 1
            return "single", 0

        elif result == AtBatResult.WALK:
            batter.record.walks += 1
            pitcher.record.walks_allowed += 1
            return "walk", 0

        elif result == AtBatResult.STRIKEOUT:
            batter.record.strikeouts += 1
            batter.record.at_bats += 1
            pitcher.record.strikeouts_pitched += 1
            return "strikeout", 0

        elif result == AtBatResult.GROUNDOUT:
            batter.record.at_bats += 1
            # 内野安打の可能性（新エンジンでは既に判定済みなのでここでは基本アウト）
            return "out", 0

        elif result in [AtBatResult.FLYOUT, AtBatResult.LINEOUT, AtBatResult.POP_OUT]:
            batter.record.at_bats += 1
            return "out", 0

        elif result == AtBatResult.DOUBLE_PLAY:
            batter.record.at_bats += 1
            return "double_play", 0

        elif result == AtBatResult.SACRIFICE_FLY:
            # 犠飛は打数にカウントしない
            return "sacrifice_fly", 1

        else:
            batter.record.at_bats += 1
            return "out", 0

    def simulate_inning(self, batting_team: Team, pitching_team: Team, batter_idx: int) -> Tuple[int, int]:
        """イニングをシミュレート
        
        Args:
            batting_team: 攻撃チーム
            pitching_team: 守備チーム
            batter_idx: 先頭打者の打順インデックス
        
        Returns:
            (得点, 次回先頭打者インデックス)
        """
        runs = 0
        outs = 0
        runners = [False, False, False]  # 1塁, 2塁, 3塁
        
        if len(batting_team.current_lineup) == 0:
            return 0, batter_idx
        
        # 現在の投手を取得（継投対応）
        is_home_pitching = (pitching_team == self.home_team)
        if is_home_pitching:
            pitcher_idx = self.current_home_pitcher_idx if self.current_home_pitcher_idx >= 0 else pitching_team.starting_pitcher_idx
        else:
            pitcher_idx = self.current_away_pitcher_idx if self.current_away_pitcher_idx >= 0 else pitching_team.starting_pitcher_idx
        
        if pitcher_idx == -1 or pitcher_idx >= len(pitching_team.players):
            return 0, batter_idx
        
        pitcher = pitching_team.players[pitcher_idx]
        
        # 投手成績を初期化
        self._init_pitcher_stats(pitching_team, pitcher_idx)
        
        # 投手のスタミナ情報を取得
        if is_home_pitching:
            pitcher_stats = self.home_pitcher_stats
        else:
            pitcher_stats = self.away_pitcher_stats
        
        while outs < 3:
            lineup_idx = batter_idx % len(batting_team.current_lineup)
            player_idx = batting_team.current_lineup[lineup_idx]
            
            if player_idx >= len(batting_team.players):
                batter_idx += 1
                continue
            
            batter = batting_team.players[player_idx]
            
            # 打者成績を初期化
            self._init_batter_stats(batting_team, player_idx)
            
            # 継投チェック（打席前）
            if self.check_pitching_change(is_home_pitching):
                # 投手が交代した場合、新投手を取得
                if is_home_pitching:
                    pitcher_idx = self.current_home_pitcher_idx
                    pitcher_stats = self.home_pitcher_stats
                else:
                    pitcher_idx = self.current_away_pitcher_idx
                    pitcher_stats = self.away_pitcher_stats
                pitcher = pitching_team.players[pitcher_idx]
                self._init_pitcher_stats(pitching_team, pitcher_idx)
            
            result, direct_runs = self.simulate_at_bat(batter, pitcher)
            
            # 球数カウント（打席ごとに平均4球として計算）
            pitch_in_ab = random.randint(3, 7)
            pitcher_stats['pitch_count'] = pitcher_stats.get('pitch_count', 0) + pitch_in_ab
            
            # 成績記録
            rbi = 0
            
            if result == "home_run":
                rbi = direct_runs + sum(1 for r in runners if r)
                runs += rbi
                batter.record.rbis += sum(1 for r in runners if r)  # 追加RBI
                runners = [False, False, False]
                self.log.append(f"  {batter.name} ホームラン！")
                self._record_at_bat(batting_team, player_idx, "homerun", rbi)
                self._record_pitcher_result(pitching_team, pitcher_idx, "homerun")
                pitcher_stats['hits'] = pitcher_stats.get('hits', 0) + 1
                pitcher_stats['runs'] = pitcher_stats.get('runs', 0) + rbi
            elif result == "triple":
                rbi = sum(1 for r in runners if r)
                runs += rbi
                batter.record.rbis += rbi
                runners = [False, False, True]
                self.log.append(f"  {batter.name} 三塁打")
                self._record_at_bat(batting_team, player_idx, "triple", rbi)
                self._record_pitcher_result(pitching_team, pitcher_idx, "triple")
                pitcher_stats['hits'] = pitcher_stats.get('hits', 0) + 1
                pitcher_stats['runs'] = pitcher_stats.get('runs', 0) + rbi
            elif result == "double":
                rbi = 0
                if runners[2]: 
                    runs += 1
                    rbi += 1
                if runners[1]: 
                    runs += 1
                    rbi += 1
                batter.record.rbis += rbi
                runners = [False, True, runners[0]]
                self.log.append(f"  {batter.name} 二塁打")
                self._record_at_bat(batting_team, player_idx, "double", rbi)
                self._record_pitcher_result(pitching_team, pitcher_idx, "double")
                pitcher_stats['hits'] = pitcher_stats.get('hits', 0) + 1
                pitcher_stats['runs'] = pitcher_stats.get('runs', 0) + rbi
            elif result == "single":
                rbi = 0
                if runners[2]: 
                    runs += 1
                    rbi += 1
                if runners[1]:
                    if random.random() < 0.5:  # 2塁走者が生還する確率
                        runs += 1
                        rbi += 1
                        runners[2] = runners[0]
                    else:
                        runners[2] = True
                else:
                    runners[2] = runners[0]
                runners[0] = True
                runners[1] = False
                batter.record.rbis += rbi
                self.log.append(f"  {batter.name} ヒット")
                self._record_at_bat(batting_team, player_idx, "single", rbi)
                self._record_pitcher_result(pitching_team, pitcher_idx, "single")
                pitcher_stats['hits'] = pitcher_stats.get('hits', 0) + 1
                pitcher_stats['runs'] = pitcher_stats.get('runs', 0) + rbi
            elif result == "walk":
                rbi = 0
                if runners[0] and runners[1] and runners[2]: 
                    runs += 1
                    rbi += 1
                if runners[0] and runners[1]: runners[2] = True
                if runners[0]: runners[1] = True
                runners[0] = True
                batter.record.rbis += rbi
                self.log.append(f"  {batter.name} 四球")
                self._record_at_bat(batting_team, player_idx, "walk", rbi)
                self._record_pitcher_result(pitching_team, pitcher_idx, "walk")
                pitcher_stats['walks'] = pitcher_stats.get('walks', 0) + 1
                pitcher_stats['runs'] = pitcher_stats.get('runs', 0) + rbi
            elif result == "strikeout":
                outs += 1
                self.log.append(f"  {batter.name} 三振 ({outs}アウト)")
                self._record_at_bat(batting_team, player_idx, "strikeout", 0)
                self._record_pitcher_result(pitching_team, pitcher_idx, "strikeout")
            else:
                outs += 1
                # 犠牲フライ判定
                if outs < 3 and random.random() < 0.35 and runners[2]:
                    runs += 1
                    batter.record.rbis += 1
                    runners[2] = False
                    self.log.append(f"  {batter.name} 犠牲フライ、得点 ({outs}アウト)")
                    self._record_at_bat(batting_team, player_idx, "out", 1)
                    pitcher_stats['runs'] = pitcher_stats.get('runs', 0) + 1
                else:
                    self.log.append(f"  {batter.name} アウト ({outs}アウト)")
                    self._record_at_bat(batting_team, player_idx, "out", 0)
                self._record_pitcher_result(pitching_team, pitcher_idx, "out")
            
            batter_idx += 1
        
        # イニング終了時の投手成績更新
        pitcher_stats['innings'] = pitcher_stats.get('innings', 0) + 1
        
        # 投手の投球回を更新
        pitcher_key = (pitching_team.name, pitcher_idx)
        if pitcher_key in self.pitching_results:
            self.pitching_results[pitcher_key]['ip'] += 1.0
        
        pitcher.record.innings_pitched += 1
        pitcher.record.earned_runs += runs
        pitcher.record.games_pitched += 1
        
        return runs, batter_idx
    
    def simulate_game(self) -> Tuple[int, int]:
        """試合をシミュレート"""
        self.log = [f"=== {self.away_team.name} vs {self.home_team.name} ===\n"]
        
        # 両チームの打順を追跡
        away_batter_idx = 0
        home_batter_idx = 0
        
        for inning in range(1, self.max_innings + 1):
            self.inning = inning
            self.log.append(f"\n--- {inning}回表 ---")
            runs, away_batter_idx = self.simulate_inning(self.away_team, self.home_team, away_batter_idx)
            self.away_score += runs
            self.inning_scores_away.append(runs)  # イニングスコア記録
            
            # 9回裏、ホームチームがリードしていれば終了
            if inning == self.max_innings and self.home_score > self.away_score:
                self.inning_scores_home.append('X')  # 試合終了マーク
                break
            
            self.log.append(f"\n--- {inning}回裏 ---")
            runs, home_batter_idx = self.simulate_inning(self.home_team, self.away_team, home_batter_idx)
            self.home_score += runs
            self.inning_scores_home.append(runs)  # イニングスコア記録
            
            # サヨナラ判定
            if inning >= self.max_innings and self.home_score > self.away_score:
                self.log.append("\nサヨナラ勝ち！")
                break
        
        # 延長戦
        while self.home_score == self.away_score and self.inning < 12:
            self.inning += 1
            self.log.append(f"\n--- {self.inning}回表（延長）---")
            runs, away_batter_idx = self.simulate_inning(self.away_team, self.home_team, away_batter_idx)
            self.away_score += runs
            self.inning_scores_away.append(runs)
            
            self.log.append(f"\n--- {self.inning}回裏（延長）---")
            runs, home_batter_idx = self.simulate_inning(self.home_team, self.away_team, home_batter_idx)
            self.home_score += runs
            self.inning_scores_home.append(runs)
            
            if self.home_score != self.away_score:
                if self.home_score > self.away_score:
                    self.log.append("\nサヨナラ勝ち！")
                break
        
        # 勝敗記録
        if self.home_score > self.away_score:
            self.home_team.wins += 1
            self.away_team.losses += 1
            # 勝利投手
            if self.home_team.starting_pitcher_idx >= 0:
                pitcher = self.home_team.players[self.home_team.starting_pitcher_idx]
                pitcher.record.wins += 1
            result = f"{self.home_team.name} 勝利"
        elif self.away_score > self.home_score:
            self.away_team.wins += 1
            self.home_team.losses += 1
            # 勝利投手
            if self.away_team.starting_pitcher_idx >= 0:
                pitcher = self.away_team.players[self.away_team.starting_pitcher_idx]
                pitcher.record.wins += 1
            result = f"{self.away_team.name} 勝利"
        else:
            self.home_team.draws += 1
            self.away_team.draws += 1
            result = "引き分け"
        
        self.log.append(f"\n最終スコア: {self.away_team.name} {self.away_score} - {self.home_score} {self.home_team.name}")
        self.log.append(f"試合結果: {result}")
        
        return self.home_score, self.away_score


def simulate_game_fast(home_team: Team, away_team: Team) -> Tuple[int, int, str]:
    """高速試合シミュレーション（バッチ処理用）
    
    NPB 2023年実績ベースの計算ロジック:
    - リーグ平均得点: 3.68点/試合
    - ホームアドバンテージ: +3.5%程度
    - 引き分け率: 約2.5%
    
    Returns:
        (home_score, away_score, winner_name)
    """
    # チームの平均能力を計算（NPB実績ベース）
    def calc_team_batting(team):
        # 現在のラインナップを優先
        if team.current_lineup:
            batters = [team.players[i] for i in team.current_lineup 
                      if 0 <= i < len(team.players) and team.players[i].position.value != "投手"]
        else:
            batters = [p for p in team.players if p.position.value != "投手"]
        
        if not batters:
            return 50
        
        # NPB実績: ミートは打率、パワーは長打力、走力は得点効率に影響
        total = sum(p.stats.contact * 0.45 + p.stats.power * 0.35 + p.stats.speed * 0.20 
                   for p in batters[:9])  # スタメン9人まで
        return total / min(9, len(batters))
    
    def calc_team_pitching(team):
        # 先発投手を重視
        if team.starting_pitcher_idx >= 0 and team.starting_pitcher_idx < len(team.players):
            starter = team.players[team.starting_pitcher_idx]
            starter_rating = starter.stats.control * 0.40 + starter.stats.breaking * 0.30 + starter.stats.speed * 0.20 + starter.stats.stamina * 0.10
        else:
            starter_rating = 50
        
        # 他の投手陣
        relievers = [p for p in team.players if p.position.value == "投手" 
                    and team.players.index(p) != team.starting_pitcher_idx]
        if relievers:
            bullpen_rating = sum(p.stats.control * 0.35 + p.stats.breaking * 0.35 + p.stats.speed * 0.30 
                               for p in relievers[:5]) / min(5, len(relievers))
        else:
            bullpen_rating = 50
        
        # 先発70%、リリーフ30%の重み
        return starter_rating * 0.70 + bullpen_rating * 0.30
    
    home_bat = calc_team_batting(home_team)
    away_bat = calc_team_batting(away_team)
    home_pitch = calc_team_pitching(home_team)
    away_pitch = calc_team_pitching(away_team)
    
    # 期待得点を計算（NPB 2023年平均3.68点/試合ベース）
    base_runs = 3.68
    
    # 打撃力と投手力の差から期待得点を計算
    # 能力値50が基準、差1ポイントで約±1.5%の影響
    home_bat_factor = 1 + (home_bat - 50) * 0.015
    away_bat_factor = 1 + (away_bat - 50) * 0.015
    home_pitch_factor = 1 - (away_pitch - 50) * 0.012
    away_pitch_factor = 1 - (home_pitch - 50) * 0.012
    
    home_exp = base_runs * home_bat_factor * home_pitch_factor
    away_exp = base_runs * away_bat_factor * away_pitch_factor
    
    # ホームアドバンテージ（NPB実績: 約53.5%のホーム勝率 ≒ +3.5%）
    home_exp *= 1.035
    
    # 得点の分散を加味（NPB標準偏差約2.5）
    home_score = max(0, int(home_exp + random.gauss(0, 2.2)))
    away_score = max(0, int(away_exp + random.gauss(0, 2.2)))
    
    # 極端な点差を抑制（現実的な範囲に）
    home_score = min(home_score, 15)
    away_score = min(away_score, 15)
    
    # 引き分けの場合は延長戦（NPB引き分け率約2.5%）
    if home_score == away_score:
        if random.random() < 0.70:  # 70%で延長で決着
            # 延長は1点差決着が多い
            if random.random() < 0.535:  # ホーム有利
                home_score += 1
            else:
                away_score += 1
    
    # 勝敗記録
    if home_score > away_score:
        home_team.wins += 1
        away_team.losses += 1
        winner = home_team.name
    elif away_score > home_score:
        away_team.wins += 1
        home_team.losses += 1
        winner = away_team.name
    else:
        home_team.draws += 1
        away_team.draws += 1
        winner = ""
    
    return home_score, away_score, winner


def execute_substitution(team: Team, out_player_idx: int, in_player_idx: int, sub_type: str = "pinch_hit") -> bool:
    """選手交代を実行
    
    Args:
        team: チーム
        out_player_idx: 退場する選手のインデックス
        in_player_idx: 出場する選手のインデックス
        sub_type: 交代タイプ ("pinch_hit", "pinch_run", "pitching_change", "defensive")
    
    Returns:
        bool: 交代成功かどうか
    """
    if out_player_idx < 0 or out_player_idx >= len(team.players):
        return False
    if in_player_idx < 0 or in_player_idx >= len(team.players):
        return False
    
    out_player = team.players[out_player_idx]
    in_player = team.players[in_player_idx]
    
    # スターティングラインナップ内の位置を入れ替え
    if hasattr(team, 'starting_lineup') and team.starting_lineup:
        if out_player_idx in team.starting_lineup:
            slot_idx = team.starting_lineup.index(out_player_idx)
            team.starting_lineup[slot_idx] = in_player_idx
    
    # 投手交代の場合
    if sub_type == "pitching_change":
        if hasattr(team, 'current_pitcher_idx'):
            team.current_pitcher_idx = in_player_idx
    
    return True


# GameSimulatorクラスに追加するメソッド用のヘルパー関数
def add_substitute_methods_to_simulator():
    """GameSimulatorクラスに交代メソッドを追加（動的メソッド追加用）"""
    
    def substitute_batter(self, new_batter_idx: int):
        """代打を出す"""
        if hasattr(self, 'current_batter_idx'):
            old_idx = self.current_batter_idx
            self.current_batter_idx = new_batter_idx
            self.log.append(f"  代打: {self.home_team.players[new_batter_idx].name}")
    
    def substitute_runner(self, new_runner_idx: int, base: int = 1):
        """代走を出す
        
        Args:
            new_runner_idx: 代走選手のインデックス
            base: 何塁か (1, 2, 3)
        """
        self.log.append(f"  代走: {self.home_team.players[new_runner_idx].name} ({base}塁)")
    
    def change_pitcher(self, new_pitcher_idx: int, is_home: bool = True):
        """投手交代
        
        Args:
            new_pitcher_idx: 新投手のインデックス
            is_home: ホームチームの投手か
        """
        if is_home:
            old_idx = self.current_home_pitcher_idx
            self.current_home_pitcher_idx = new_pitcher_idx
            self.home_pitcher_stats = {'pitch_count': 0, 'hits': 0, 'walks': 0, 'runs': 0, 'innings': 0}
            team = self.home_team
        else:
            old_idx = self.current_away_pitcher_idx
            self.current_away_pitcher_idx = new_pitcher_idx
            self.away_pitcher_stats = {'pitch_count': 0, 'hits': 0, 'walks': 0, 'runs': 0, 'innings': 0}
            team = self.away_team
        
        if 0 <= new_pitcher_idx < len(team.players):
            self.log.append(f"  継投: {team.players[new_pitcher_idx].name}")
    
    # GameSimulatorクラスにメソッドを追加
    GameSimulator.substitute_batter = substitute_batter
    GameSimulator.substitute_runner = substitute_runner
    GameSimulator.change_pitcher = change_pitcher


# モジュール読み込み時に自動で追加
try:
    add_substitute_methods_to_simulator()
except:
    pass

