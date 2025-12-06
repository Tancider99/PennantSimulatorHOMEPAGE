# -*- coding: utf-8 -*-
"""
Pennant Simulator 2027（ペナントシミュレーター2027） - メインファイル（プロフェッショナル版）
洗練されたUIと安定したゲームプレイを実現
"""
import pygame
import sys
import random
import math

from constants import *
from models import Team, League, GameStatus, Player
from team_generator import create_team
from ui_pro import fonts, Colors, Button, ToastManager
from screens import ScreenRenderer
from game_simulator import GameSimulator
from player_generator import create_draft_prospect, create_foreign_free_agent
from models import Position, PitchType, PlayerStatus
from game_state import GameStateManager, GameState, DifficultyLevel
from schedule_manager import ScheduleManager
from settings_manager import settings
from pennant_mode import PennantManager, PennantPhase
from pennant_screens import PennantScreens
from save_manager import SaveManager


# ========================================
# 打球物理計算システム
# ========================================
class BallPhysics:
    """打球の物理計算クラス - NPB実データに基づくリアルなシミュレーション"""
    
    # フィールド定義（メートル単位）
    FIELD_DEPTH = 120  # センターまでの距離
    FIELD_WIDTH = 100  # レフト/ライト方向の幅
    FENCE_DISTANCE = 122  # フェンスまでの距離（センター）
    FENCE_DISTANCE_CORNER = 100  # フェンスまでの距離（両翼）
    
    # NPB実績に基づく結果確率（2023年シーズン参考）
    # 平均打率.250、長打率.380、三振率20%、四球率8%
    NPB_STATS = {
        'avg_batting_avg': 0.250,  # リーグ平均打率
        'avg_obp': 0.320,  # リーグ平均出塁率
        'avg_slg': 0.380,  # リーグ平均長打率
        'avg_strikeout_rate': 0.200,  # 三振率
        'avg_walk_rate': 0.080,  # 四球率
        'avg_hr_rate': 0.025,  # 本塁打率（打席あたり）
        'pitch_strike_rate': 0.62,  # ストライク率
        'contact_rate': 0.75,  # コンタクト率（スイング時）
        'foul_rate': 0.35,  # ファウル率（コンタクト時）
        'ball_in_play_rate': 0.65,  # インプレー率
    }
    
    # 守備位置（ホームベースを原点、メートル単位）
    # x = 左右（正がライト方向）、y = 前方（正がセンター方向）
    FIELDER_POSITIONS = {
        'pitcher': (0, 18.44),
        'catcher': (0, -1),
        'first': (15, 20),
        'second': (8, 28),
        'shortstop': (-8, 28),
        'third': (-15, 20),
        'left': (-28, 60),
        'center': (0, 70),
        'right': (28, 60),
    }
    
    # 守備範囲（メートル）- この距離内なら基本的に捕球可能（広めに設定）
    POSITION_RANGE = {
        'pitcher': 6,
        'catcher': 5,
        'first': 14,
        'second': 18,
        'shortstop': 20,
        'third': 12,
        'left': 35,
        'center': 45,
        'right': 35,
    }
    
    # 打球パラメータ定数（physics_engine.pyと統一）
    SOFT_CONTACT_MAX_VELO = 95   # Soft contact: 95km/h以下
    MID_CONTACT_MAX_VELO = 135   # Mid contact: 95-135km/h
    MIN_EXIT_VELOCITY = 60.0    # 最低打球速度
    MAX_EXIT_VELOCITY = 193.0   # 最高打球速度
    GROUNDBALL_MAX_ANGLE = 10   # ゴロ: 10度以下
    LINEDRIVE_MIN_ANGLE = 10    # ライナー: 10-25度
    LINEDRIVE_MAX_ANGLE = 25
    FLYBALL_MIN_ANGLE = 25      # フライ: 25-50度
    POPUP_MIN_ANGLE = 50        # ポップアップ: 50度以上
    
    @staticmethod
    def generate_batted_ball(batter, pitcher):
        """打球データを生成（physics_engine.pyと同じ計算ロジック）
        
        目標統計:
        - GB%=45%, LD%=10%, FB%=35%, IFFB%=10%
        - Soft%=23%, Mid%=42%, Hard%=35%
        """
        # 打者能力
        contact = getattr(batter.stats, 'contact', 50)
        power = getattr(batter.stats, 'power', 50)
        trajectory_type = getattr(batter.stats, 'trajectory', 2)  # 弾道: 1=ゴロ, 2=普通, 3=ライナー, 4=フライ
        
        # 投手能力
        p_stuff = getattr(pitcher.stats, 'speed', 50)
        p_control = getattr(pitcher.stats, 'control', 50)
        
        # 空振り判定（既存ロジック維持）
        miss_chance = 0.22 - (contact - 50) * 0.0025 + (p_stuff - 50) * 0.002
        if random.random() < miss_chance:
            return None
        
        # ===== 打球の質（Soft/Mid/Hard）の決定 =====
        # 目標: Soft%=23%, Mid%=42%, Hard%=35%
        quality_roll = random.random()
        
        # Soft/Mid/Hard の閾値（physics_engine.pyと同じ）
        soft_threshold = 0.23
        hard_threshold = 0.35
        mid_threshold = 1.0 - soft_threshold - hard_threshold  # 0.42
        
        if quality_roll < soft_threshold:
            contact_quality = random.uniform(0.0, 0.35)  # Soft contact
        elif quality_roll < soft_threshold + mid_threshold:
            contact_quality = random.uniform(0.35, 0.70)  # Mid contact
        else:
            contact_quality = random.uniform(0.70, 1.0)  # Hard contact
        
        # ===== 打球速度の計算（Soft/Mid/Hardに基づく） =====
        if contact_quality < 0.35:
            # Soft contact: 60-95 km/h
            base_exit_velo = 60 + power * 0.8
            exit_velocity = base_exit_velo + contact_quality * 80
            exit_velocity = min(BallPhysics.SOFT_CONTACT_MAX_VELO, exit_velocity)
        elif contact_quality < 0.70:
            # Mid contact: 95-135 km/h
            normalized_q = (contact_quality - 0.35) / 0.35
            base_exit_velo = BallPhysics.SOFT_CONTACT_MAX_VELO + power * 0.5
            exit_velocity = base_exit_velo + normalized_q * (BallPhysics.MID_CONTACT_MAX_VELO - BallPhysics.SOFT_CONTACT_MAX_VELO)
        else:
            # Hard contact: 135-193 km/h
            normalized_q = (contact_quality - 0.70) / 0.30
            base_exit_velo = BallPhysics.MID_CONTACT_MAX_VELO + power * 1.5
            exit_velocity = base_exit_velo + normalized_q * (BallPhysics.MAX_EXIT_VELOCITY - BallPhysics.MID_CONTACT_MAX_VELO) * 0.6
        
        # ランダム変動と投手能力補正
        stuff_penalty = (p_stuff - 50) * 0.15
        exit_velocity += random.gauss(0, 4) - stuff_penalty
        exit_velocity = max(BallPhysics.MIN_EXIT_VELOCITY, min(BallPhysics.MAX_EXIT_VELOCITY, exit_velocity))
        
        # ===== 打球角度の計算（目標: GB%=45%, LD%=10%, FB%=35%, IFFB%=10%） =====
        type_roll = random.random()
        
        # 弾道タイプによる補正
        # trajectory: 1=ゴロ打ち(GB+10%), 2=普通, 3=ライナー(LD+5%), 4=フライ打ち(FB+10%)
        gb_boost = {1: 0.12, 2: 0.00, 3: -0.05, 4: -0.10}.get(trajectory_type, 0)
        ld_boost = {1: -0.03, 2: 0, 3: 0.05, 4: -0.02}.get(trajectory_type, 0)
        
        # 基本確率 (GB=43%, LD=10%, FB=37%, IFFB=10%)
        gb_chance = 0.43 + gb_boost
        ld_chance = 0.10 + ld_boost
        fb_chance = 0.37 - gb_boost * 0.4
        iffb_chance = 0.10
        
        # コンタクトの質による補正
        if contact_quality < 0.35:
            # Soft contactはゴロかポップアップになりやすい
            gb_chance += 0.05
            ld_chance -= 0.01
            fb_chance -= 0.05
            iffb_chance += 0.01
        elif contact_quality > 0.70:
            # Hard contactはライナーやフライになりやすい
            gb_chance -= 0.04
            ld_chance += 0.01
            fb_chance += 0.03
            iffb_chance -= 0.01
        
        # 正規化
        total = gb_chance + ld_chance + fb_chance + iffb_chance
        gb_chance /= total
        ld_chance /= total
        fb_chance /= total
        iffb_chance /= total
        
        # 打球タイプと角度を決定
        if type_roll < gb_chance:
            # ゴロ: -15度 〜 10度
            launch_angle = random.gauss(2, 5)
            launch_angle = max(-15, min(BallPhysics.GROUNDBALL_MAX_ANGLE, launch_angle))
            hit_type = 'grounder'
        elif type_roll < gb_chance + ld_chance:
            # ライナー: 10度 〜 25度
            launch_angle = random.gauss(17, 4)
            launch_angle = max(BallPhysics.LINEDRIVE_MIN_ANGLE, min(BallPhysics.LINEDRIVE_MAX_ANGLE, launch_angle))
            hit_type = 'liner'
        elif type_roll < gb_chance + ld_chance + fb_chance:
            # 通常フライ: 25度 〜 50度
            launch_angle = random.gauss(38, 6)
            launch_angle = max(BallPhysics.FLYBALL_MIN_ANGLE, min(BallPhysics.POPUP_MIN_ANGLE - 1, launch_angle))
            hit_type = 'fly'
        else:
            # 内野フライ（ポップアップ）: 50度 〜 65度
            launch_angle = random.gauss(55, 5)
            launch_angle = max(BallPhysics.POPUP_MIN_ANGLE, min(65, launch_angle))
            hit_type = 'popup'
        
        launch_angle = max(-15, min(65, launch_angle))
        
        # フライとポップアップは打球速度を調整（飛距離抑制）
        final_exit_velocity = exit_velocity
        if hit_type == 'fly':
            final_exit_velocity *= 0.88
        elif hit_type == 'popup':
            final_exit_velocity *= 0.70
        
        # 打球方向（センター基準、正=ライト方向）
        pull_tendency = (power - 50) * 0.06  # 既存のロジック維持
        direction = random.gauss(pull_tendency, 22)
        direction = max(-45, min(45, direction))
        
        return {
            'exit_velocity': final_exit_velocity,
            'launch_angle': launch_angle,
            'direction': direction,
            'quality': contact_quality,
            'hit_type': hit_type,
            'contact_quality': contact_quality
        }
    
    @staticmethod
    def calculate_trajectory(ball_data):
        """打球軌道を計算（座標リスト）- フェンス跳ね返り対応
        
        Returns:
            list: 軌道データのリスト。各要素は (x, y, z, bounced) のタプル
                  bounced: その時点でバウンドしているかどうか
        """
        if ball_data is None:
            return []
        
        # 初速（m/s）
        ev_ms = ball_data['exit_velocity'] / 3.6
        angle_rad = math.radians(ball_data['launch_angle'])
        dir_rad = math.radians(ball_data['direction'])
        
        # 速度成分
        vx = ev_ms * math.cos(angle_rad) * math.sin(dir_rad)  # 左右
        vy = ev_ms * math.cos(angle_rad) * math.cos(dir_rad)  # 前方
        vz = ev_ms * math.sin(angle_rad)  # 上方
        
        # 物理定数
        gravity = 9.8
        drag = 0.003  # 空気抵抗
        bounce_coef = 0.4  # 地面反発係数
        fence_bounce_coef = 0.35  # フェンス反発係数
        friction = 0.88  # 地面摩擦
        
        # フェンス定義
        FENCE_CENTER = 122.0  # センター
        FENCE_ALLEY = 116.0   # 左中間・右中間
        FENCE_CORNER = 100.0  # 両翼
        FENCE_HEIGHT = 4.2    # フェンス高さ
        
        def get_fence_distance(x, y):
            """打球位置からフェンスまでの距離を計算"""
            if y <= 0:
                return 1000  # バックネット方向
            angle = math.degrees(math.atan2(abs(x), y))
            if angle < 15:
                return FENCE_CENTER
            elif angle < 30:
                t = (angle - 15) / 15
                return FENCE_CENTER - t * (FENCE_CENTER - FENCE_ALLEY)
            else:
                t = min(1.0, (angle - 30) / 15)
                return FENCE_ALLEY - t * (FENCE_ALLEY - FENCE_CORNER)
        
        trajectory = []
        x, y, z = 0, 0, 1.0  # 初期位置（高さ1m）
        dt = 0.05  # 時間刻み
        bounces = 0
        max_bounces = 8
        fence_hit = False
        has_bounced = False  # バウンドしたかどうかのフラグ
        
        for _ in range(400):  # 最大20秒
            trajectory.append((x, y, max(0, z), has_bounced))
            
            # 空気抵抗
            speed = math.sqrt(vx**2 + vy**2 + vz**2)
            if speed > 0:
                drag_factor = 1 - drag * speed * dt
                vx *= drag_factor
                vy *= drag_factor
                vz *= drag_factor
            
            # 重力
            vz -= gravity * dt
            
            # 位置更新
            new_x = x + vx * dt
            new_y = y + vy * dt
            new_z = z + vz * dt
            
            # フェンスとの衝突判定
            dist_from_home = math.sqrt(new_x**2 + new_y**2)
            fence_dist = get_fence_distance(new_x, new_y)
            
            if dist_from_home >= fence_dist and new_z <= FENCE_HEIGHT and new_z > 0:
                # フェンスに当たった！
                fence_hit = True
                
                # フェンスへの法線ベクトルを計算（ホーム方向）
                norm_len = math.sqrt(new_x**2 + new_y**2)
                if norm_len > 0:
                    nx = -new_x / norm_len
                    ny = -new_y / norm_len
                else:
                    nx, ny = 0, -1
                
                # 速度の法線成分を反転（跳ね返り）
                dot = vx * nx + vy * ny
                vx = (vx - 2 * dot * nx) * fence_bounce_coef
                vy = (vy - 2 * dot * ny) * fence_bounce_coef
                vz *= 0.7  # 高さ方向も減衰
                
                # フェンスの内側に戻す
                new_x = (fence_dist - 1) * (-nx)
                new_y = (fence_dist - 1) * (-ny)
                
                # 跳ね返りポイントを追加
                trajectory.append((new_x, new_y, new_z, has_bounced))
            
            x, y, z = new_x, new_y, new_z
            
            # 地面との接触
            if z <= 0:
                z = 0.05
                has_bounced = True  # バウンドフラグを立てる
                if bounces < max_bounces and abs(vz) > 0.5:
                    # バウンド
                    vz = -vz * bounce_coef
                    vx *= friction
                    vy *= friction
                    bounces += 1
                else:
                    # 転がり
                    roll_friction = 0.94
                    for _ in range(30):
                        vx *= roll_friction
                        vy *= roll_friction
                        x += vx * dt
                        y += vy * dt
                        trajectory.append((x, y, 0.1, True))
                        if abs(vx) < 0.2 and abs(vy) < 0.2:
                            break
                    break
            
            # 十分遠くに飛んだら終了（ホームラン）
            if dist_from_home > fence_dist and z > FENCE_HEIGHT:
                # フェンス越え
                for _ in range(10):  # 着地まで追加
                    vz -= gravity * dt
                    x += vx * dt
                    y += vy * dt
                    z += vz * dt
                    trajectory.append((x, y, max(0, z), has_bounced))
                    if z <= 0:
                        break
                break
            
            # バックネット方向に戻りすぎたら終了
            if y < -5:
                break
        
        return trajectory
    
    @staticmethod
    def get_landing_point(trajectory):
        """軌道の終点を取得"""
        if not trajectory:
            return (0, 5, 0)
        point = trajectory[-1]
        # バウンド情報付き(4要素)と従来(3要素)の両方に対応
        if len(point) >= 3:
            return (point[0], point[1], point[2])
        return (0, 5, 0)
    
    @staticmethod
    def has_ball_bounced(trajectory):
        """軌道データから打球がバウンドしたかどうかを判定"""
        if not trajectory:
            return False
        # 最後の要素をチェック
        point = trajectory[-1]
        if len(point) >= 4:
            return point[3]  # バウンドフラグ
        return False
    
    @staticmethod
    def get_first_bounce_frame(trajectory):
        """最初にバウンドしたフレームを取得"""
        for i, point in enumerate(trajectory):
            if len(point) >= 4 and point[3]:
                return i
        return -1  # バウンドしていない
    
    @staticmethod
    def classify_ball_type(ball_data):
        """打球種類を判定（physics_engine.pyと同じ角度閾値）"""
        if ball_data is None:
            return 'none'
        
        # generate_batted_ballで既にhit_typeが設定されている場合はそれを返す
        if 'hit_type' in ball_data:
            return ball_data['hit_type']
        
        # 角度ベースの判定（フォールバック）
        angle = ball_data['launch_angle']
        if angle <= BallPhysics.GROUNDBALL_MAX_ANGLE:  # 10度以下
            return 'grounder'
        elif angle <= BallPhysics.LINEDRIVE_MAX_ANGLE:  # 10-25度
            return 'liner'
        elif angle < BallPhysics.POPUP_MIN_ANGLE:  # 25-50度
            return 'fly'
        else:  # 50度以上
            return 'popup'
    
    @staticmethod
    def check_foul(trajectory, ball_data):
        """ファウル判定（シンプル版）"""
        if not trajectory or len(trajectory) < 2:
            return False, None
        
        # 着地点でファウル判定
        landing = trajectory[-1]
        lx, ly = landing[0], landing[1]
        
        # ファウルライン角度（45度）
        if ly > 0:
            angle = math.degrees(math.atan2(abs(lx), ly))
            if angle > 45:
                # ファウルフライの捕球判定
                if ball_data and ball_data['launch_angle'] > 15:
                    height = max(p[2] for p in trajectory)
                    if height > 8:
                        dist = math.sqrt(lx**2 + ly**2)
                        catch_prob = max(0.1, 0.8 - dist * 0.008)
                        if random.random() < catch_prob:
                            fielder = 'right' if lx > 0 else 'left'
                            if ly < 25:
                                fielder = 'first' if lx > 0 else 'third'
                            if ly < 5:
                                fielder = 'catcher'
                            return True, fielder  # ファウルフライアウト
                return True, None  # ただのファウル
        
        # 内野でファウルゾーンに最初に落ちた場合
        for point in trajectory:
            px, py, pz = point
            if pz < 1.0 and py > 0 and py < 27:
                if py > 0:
                    point_angle = math.degrees(math.atan2(abs(px), py))
                    if point_angle > 45:
                        return True, None
                break
        
        return False, None
    
    @staticmethod
    def check_homerun(trajectory, ball_data, park_factor=1.0):
        """ホームラン判定（ノーバウンドでフェンス越え）
        
        Args:
            trajectory: 打球軌道データ
            ball_data: 打球データ（速度、角度など）
            park_factor: パークファクター（1.0が基準、高いほどHRが出やすい）
                - 1.2: HR出やすい（東京ドームなど）
                - 1.0: 標準
                - 0.8: HR出にくい（広い球場）
        
        Returns: (is_homerun: bool, is_entitled_double: bool)
        - ノーバウンドでフェンス越え → ホームラン
        - ワンバウンド以上でフェンス越え → エンタイトルツーベース
        """
        if not trajectory or not ball_data:
            return False, False
        
        # パークファクターによるフェンス距離調整
        # park_factor高い → フェンス近い → HR出やすい
        # 基準: 両翼100m、センター122m
        base_pole = 100
        base_center = 122
        # パークファクター1.2で約5%短く、0.8で約5%長く
        fence_adjustment = 1.0 - (park_factor - 1.0) * 0.25
        
        def get_fence_distance(x, y):
            if y <= 0:
                return 1000  # バックネット方向はフェンスなし
            angle = abs(math.degrees(math.atan2(x, y)))
            if angle > 45:
                return 1000  # ファウルゾーン
            # 両翼から中堅への放物線補間
            pole_dist = base_pole * fence_adjustment
            center_dist = base_center * fence_adjustment
            return pole_dist + (center_dist - pole_dist) * (1 - (angle / 45) ** 1.5)
        
        # フェンスの高さ（約3-4m）、パークファクターで微調整
        # HR出やすい球場はフェンスも低め
        FENCE_HEIGHT = 3.5 * fence_adjustment
        
        # 軌道を追って、フェンス到達時の状態を確認
        bounced = False
        for i, point in enumerate(trajectory):
            x, y, z = point
            
            # バウンド検出（高さが0に近づいて反発）
            if i > 0 and z < 0.5:
                prev_z = trajectory[i-1][2]
                if prev_z > z and z < 1.0:
                    bounced = True
            
            # フェンス距離を計算
            dist = math.sqrt(x**2 + y**2)
            fence_dist = get_fence_distance(x, y)
            
            # フェンス到達判定
            if dist >= fence_dist:
                # フェンス越え時の高さ
                if z > FENCE_HEIGHT:
                    if bounced:
                        # ワンバウンド後にフェンス越え → エンタイトルツーベース
                        return False, True
                    else:
                        # ノーバウンドでフェンス越え → ホームラン
                        # 追加条件: 打球速度と角度
                        if (ball_data['exit_velocity'] > 120 and 
                            ball_data['launch_angle'] > 12 and
                            ball_data['launch_angle'] < 50):
                            return True, False
                elif z > 0 and not bounced:
                    # フェンス直撃（高さが足りない）→ ヒット扱い
                    return False, False
        
        # 軌道がフェンスに届かない場合
        return False, False
    
    @staticmethod
    def check_ground_rule_double(trajectory, ball_data, park_factor=1.0):
        """エンタイトルツーベース判定（ワンバウンドでスタンドイン）"""
        _, is_entitled = BallPhysics.check_homerun(trajectory, ball_data, park_factor)
        return is_entitled

    @staticmethod
    def find_closest_fielder(landing, ball_type):
        """最も近い野手を特定"""
        lx, ly = landing[0], landing[1]
        
        min_dist = float('inf')
        closest = None
        
        for pos, (fx, fy) in BallPhysics.FIELDER_POSITIONS.items():
            if pos in ['pitcher', 'catcher']:
                continue
            
            # ゴロで内野に落ちた場合、外野手は対象外
            if ball_type == 'grounder' and pos in ['left', 'center', 'right'] and ly < 55:
                continue
            
            d = math.sqrt((lx - fx)**2 + (ly - fy)**2)
            if d < min_dist:
                min_dist = d
                closest = pos
        
        return closest, min_dist
    
    @staticmethod
    def get_effective_range(fielder, fielding_ability, run_ability=50):
        """守備能力に応じた有効守備範囲を計算
        
        Args:
            fielder: 守備位置
            fielding_ability: 守備力（反応速度、判断力）
            run_ability: 走力（移動速度）
        
        Returns:
            有効守備範囲（メートル）
        """
        base_range = BallPhysics.POSITION_RANGE.get(fielder, 10)
        
        # 守備力と走力の影響（各能力50基準で±30%変動）
        # 守備力: 反応・判断・ポジショニング（60%の影響）
        # 走力: 移動速度（40%の影響）
        fielding_mod = (fielding_ability - 50) / 50 * 0.18  # ±18%
        run_mod = (run_ability - 50) / 50 * 0.12  # ±12%
        
        total_mod = 1.0 + fielding_mod + run_mod
        return base_range * total_mod
    
    @staticmethod
    def calculate_catch_probability(fielder, distance, ball_type, exit_velo, fielder_ability, catching_ability=50, run_ability=50):
        """捕球確率を計算（BABIP .300目標）"""
        # 守備範囲（守備力と走力で変動）
        effective_range = BallPhysics.get_effective_range(fielder, fielder_ability, run_ability)
        
        # 外野フライの場合、飛距離に応じた追加の難易度
        is_outfield = fielder in ['left', 'center', 'right']
        
        # 距離による基本確率
        if distance <= effective_range * 0.3:
            base_prob = 0.995  # 正面はほぼ確実
        elif distance <= effective_range * 0.6:
            base_prob = 0.96
        elif distance <= effective_range * 0.85:
            base_prob = 0.88
        elif distance <= effective_range:
            base_prob = 0.75
        else:
            over = distance - effective_range
            # 守備範囲外は急激に確率低下
            base_prob = max(0.02, 0.50 - over * 0.08)
        
        # 打球種別補正
        if ball_type == 'popup':
            modifier = 1.02  # ポップフライはほぼ捕球
        elif ball_type == 'fly':
            # 外野フライは打球速度と飛距離で難易度変化
            if is_outfield:
                # 速い打球ほど難しい（打球速度150km以上は難易度UP）
                speed_penalty = max(0, (exit_velo - 140) * 0.004)
                modifier = 0.92 - speed_penalty
            else:
                modifier = 0.95  # 内野フライ
        elif ball_type == 'liner':
            # ライナーは非常に難しい（速度依存）
            modifier = 0.55 - (exit_velo - 120) * 0.003
        else:  # grounder
            modifier = 1.00  # ゴロ
        
        # 守備力補正（守備範囲は既に計算済みなので、ここでは捕球技術のみ）
        ability_mod = 1 + (catching_ability - 50) * 0.003
        
        prob = base_prob * modifier * ability_mod
        return max(0.02, min(0.995, prob))
    
    @staticmethod
    def calculate_error(fielder, ball_type, exit_velo, catching_ability, fielding_ability, arm_ability, is_throwing=False):
        """エラー判定を計算
        
        Args:
            fielder: 守備位置
            ball_type: 打球の種類（grounder, liner, fly, popup）
            exit_velo: 打球速度（km/h）
            catching_ability: 捕球能力（1-99）
            fielding_ability: 守備力（1-99）
            arm_ability: 肩力（1-99）
            is_throwing: 送球エラー判定かどうか
        
        Returns:
            (is_error, error_type): エラーかどうかと種類
        """
        import random
        
        if is_throwing:
            # 送球エラー判定
            # 基本エラー率: 1.5%（肩力50基準）
            base_error_rate = 0.015
            
            # 肩力による補正（肩力が低いほどエラー増加）
            arm_mod = (50 - arm_ability) / 50 * 0.02  # ±2%
            
            # 守備力による補正（判断力、送球体勢）
            fielding_mod = (50 - fielding_ability) / 50 * 0.01  # ±1%
            
            # 難しい打球は送球も難しい
            if ball_type == 'liner':
                difficulty_mod = 0.01  # ライナーは難しい体勢
            elif ball_type == 'grounder' and exit_velo > 140:
                difficulty_mod = 0.008  # 強いゴロ
            else:
                difficulty_mod = 0
            
            error_rate = base_error_rate + arm_mod + fielding_mod + difficulty_mod
            error_rate = max(0.001, min(0.08, error_rate))
            
            if random.random() < error_rate:
                return True, 'throwing'  # 送球エラー
            return False, None
        
        else:
            # 捕球エラー判定
            # 基本エラー率: 1%（捕球50基準）
            base_error_rate = 0.01
            
            # 捕球能力による補正
            catching_mod = (50 - catching_ability) / 50 * 0.02  # ±2%
            
            # 守備力による補正（ポジショニング、グラブさばき）
            fielding_mod = (50 - fielding_ability) / 50 * 0.01  # ±1%
            
            # 打球種別による難易度補正
            if ball_type == 'liner':
                difficulty_mod = 0.03  # ライナーは非常に難しい
            elif ball_type == 'grounder' and exit_velo > 150:
                difficulty_mod = 0.02  # 強烈なゴロ
            elif ball_type == 'grounder' and exit_velo > 130:
                difficulty_mod = 0.01  # 速いゴロ
            elif ball_type == 'fly' and exit_velo > 150:
                difficulty_mod = 0.01  # 強い打球のフライ
            else:
                difficulty_mod = 0
            
            error_rate = base_error_rate + catching_mod + fielding_mod + difficulty_mod
            error_rate = max(0.001, min(0.10, error_rate))
            
            if random.random() < error_rate:
                return True, 'fielding'  # 捕球エラー
            return False, None
    
    @staticmethod
    def determine_hit_type(ball_type, distance, exit_velo, quality):
        """ヒットの種類を判定"""
        if ball_type == 'grounder':
            # ゴロヒットは基本シングル
            if distance > 55 and exit_velo > 140 and random.random() < 0.12:
                return 'double'
            return 'single'
        
        elif ball_type == 'liner':
            if distance > 85 and quality > 0.7:
                if random.random() < 0.25:
                    return 'triple'
                return 'double'
            elif distance > 55:
                return 'double'
            return 'single'
        
        else:  # fly
            if distance > 90:
                if random.random() < 0.20:
                    return 'triple'
                return 'double'
            elif distance > 65:
                return 'double'
            return 'single'
    
    @staticmethod
    def determine_result(ball_data, trajectory, fielders_ability, park_factor=1.0):
        """打球結果を総合判定"""
        if ball_data is None:
            return 'no_contact', None
        
        if not trajectory:
            return 'foul', None
        
        # 0. バウンドしたかどうかを確認
        has_bounced = BallPhysics.has_ball_bounced(trajectory)
        first_bounce_frame = BallPhysics.get_first_bounce_frame(trajectory)
        
        # 1. ファウル判定
        is_foul, foul_fielder = BallPhysics.check_foul(trajectory, ball_data)
        if is_foul:
            if foul_fielder:
                return 'foul_flyout', {'fielder': foul_fielder}
            return 'foul', None
        
        # 2. ホームラン/エンタイトルツーベース判定（パークファクター考慮）
        is_hr, is_entitled_double = BallPhysics.check_homerun(trajectory, ball_data, park_factor)
        if is_hr:
            landing = BallPhysics.get_landing_point(trajectory)
            dist = math.sqrt(landing[0]**2 + landing[1]**2)
            return 'homerun', {'distance': dist, 'direction': ball_data['direction']}
        elif is_entitled_double:
            landing = BallPhysics.get_landing_point(trajectory)
            dist = math.sqrt(landing[0]**2 + landing[1]**2)
            return 'entitled_double', {'distance': dist, 'direction': ball_data['direction']}
        
        # 3. 打球種類
        ball_type = BallPhysics.classify_ball_type(ball_data)
        
        # 4. 最寄り野手
        landing = BallPhysics.get_landing_point(trajectory)
        fielder, dist_to_fielder = BallPhysics.find_closest_fielder(landing, ball_type)
        
        if fielder is None:
            # 野手が見つからない場合（あり得ないが念のため）
            return 'single', {'distance': math.sqrt(landing[0]**2 + landing[1]**2)}
        
        # 5. 守備能力取得（辞書形式で詳細な能力も取得可能に）
        if isinstance(fielders_ability.get(fielder), dict):
            # 詳細な能力辞書形式
            ability_dict = fielders_ability.get(fielder, {})
            fielding = ability_dict.get('fielding', 50)
            catching = ability_dict.get('catching', 50)
            arm = ability_dict.get('arm', 50)
            run = ability_dict.get('run', 50)
        else:
            # 単一値形式（互換性維持）
            fielding = fielders_ability.get(fielder, 50)
            catching = fielding
            arm = 50
            run = 50
        
        # 6. 捕球判定（守備範囲は守備力と走力で変動）
        catch_prob = BallPhysics.calculate_catch_probability(
            fielder, dist_to_fielder, ball_type, 
            ball_data['exit_velocity'], fielding, catching, run
        )
        
        # バウンド後のフライ・ライナーは直接捕球できない（ゴロと同じ扱い）
        if has_bounced and ball_type in ['fly', 'liner', 'popup']:
            # バウンド後は全てヒット扱い（外野手が処理）
            total_dist = math.sqrt(landing[0]**2 + landing[1]**2)
            hit_type = BallPhysics.determine_hit_type(
                'grounder', total_dist,  # バウンド後はゴロ扱いでヒット判定
                ball_data['exit_velocity'], 
                ball_data.get('quality', 0.5)
            )
            return hit_type, {'distance': total_dist, 'direction': ball_data['direction']}
        
        if random.random() < catch_prob:
            # 捕球成功 - エラー判定
            is_error, error_type = BallPhysics.calculate_error(
                fielder, ball_type, ball_data['exit_velocity'],
                catching, fielding, arm, is_throwing=False
            )
            
            if is_error:
                # 捕球エラー
                return 'single', {'fielder': fielder, 'error': 'fielding'}
            
            # 内野ゴロの場合、送球判定
            if ball_type == 'grounder' and fielder in ['first', 'second', 'shortstop', 'third']:
                is_throw_error, _ = BallPhysics.calculate_error(
                    fielder, ball_type, ball_data['exit_velocity'],
                    catching, fielding, arm, is_throwing=True
                )
                if is_throw_error:
                    return 'single', {'fielder': fielder, 'error': 'throwing'}
                return 'groundout', {'fielder': fielder}
            
            if ball_type == 'liner':
                return 'lineout', {'fielder': fielder}
            return 'flyout', {'fielder': fielder}
        
        else:
            # ヒット
            total_dist = math.sqrt(landing[0]**2 + landing[1]**2)
            hit_type = BallPhysics.determine_hit_type(
                ball_type, total_dist, 
                ball_data['exit_velocity'], 
                ball_data.get('quality', 0.5)
            )
            return hit_type, {'distance': total_dist, 'direction': ball_data['direction']}
    
    # 旧メソッド名との互換性
    @staticmethod
    def calculate_batted_ball(batter, pitcher):
        """旧メソッド名（互換用）"""
        return BallPhysics.generate_batted_ball(batter, pitcher)
    
    @staticmethod
    def calculate_landing_point(trajectory):
        """旧メソッド名（互換用）"""
        return BallPhysics.get_landing_point(trajectory)
    
    @staticmethod
    def calculate_catch_frame(trajectory, fielder_name):
        """捕球されるフレームを計算（トラッキング表示用）"""
        if not trajectory or not fielder_name:
            return len(trajectory) if trajectory else 0
        
        # 野手の初期位置
        fielder_pos = BallPhysics.FIELDER_POSITIONS.get(fielder_name)
        if not fielder_pos:
            return len(trajectory)
        
        fx, fz = fielder_pos
        
        # 野手の移動速度（約8m/s = 0.4m/frame at 20fps相当）
        fielder_speed = 0.4
        
        # 落下点を先に見つける
        landing_frame = len(trajectory) - 1
        for i in range(len(trajectory) - 1, 0, -1):
            point = trajectory[i]
            if isinstance(point, dict):
                height = point.get('z', 0)
            else:
                height = point[2]
            if height <= 2.0:
                landing_frame = i
                break
        
        # 各フレームでボール位置と野手位置の距離を計算
        for i, point in enumerate(trajectory):
            if isinstance(point, dict):
                bx = point.get('x', 0)
                by = point.get('y', 0)  # 前方距離
                bz = point.get('z', 0)  # 高さ
            else:
                bx, by, bz = point[0], point[1], point[2]
            
            # 野手がボールに向かって移動した距離
            fielder_reach = 3.0 + fielder_speed * i
            
            # ボールまでの2D距離（x, y平面）
            dist_to_ball = math.sqrt((bx - fx)**2 + (by - fz)**2)
            
            # ゴロの場合（高さ2.5m以下）
            if bz <= 2.5:
                if dist_to_ball < fielder_reach:
                    return min(i + 5, len(trajectory))  # 捕球後少し余裕
            
            # フライの場合（落下中で野手が追いつける）
            elif i > 0 and i >= landing_frame - 10:
                if isinstance(trajectory[i-1], dict):
                    prev_z = trajectory[i-1].get('z', 0)
                else:
                    prev_z = trajectory[i-1][2]
                
                # 落下中かつ捕球可能な高さ
                if bz < prev_z and bz < 5.0:
                    if dist_to_ball < fielder_reach:
                        return min(i + 3, len(trajectory))
        
        # 落下点で捕球（外野フライの場合）
        return min(landing_frame + 5, len(trajectory))
    
    @staticmethod
    def get_fielders_ability(team):
        """チームの守備能力を取得"""
        abilities = {}
        position_map = {
            'first': Position.FIRST,
            'second': Position.SECOND,
            'shortstop': Position.SHORTSTOP,
            'third': Position.THIRD,
            'left': Position.OUTFIELD,
            'center': Position.OUTFIELD,
            'right': Position.OUTFIELD,
        }
        
        for pos_name, pos_enum in position_map.items():
            for player in team.players:
                if player.position == pos_enum:
                    fielding = getattr(player.stats, 'fielding', 50)
                    speed = getattr(player.stats, 'speed', 50)
                    abilities[pos_name] = (fielding * 0.7 + speed * 0.3)
                    break
            if pos_name not in abilities:
                abilities[pos_name] = 50
        
        return abilities


class NPBGame:
    """NPBゲームメインクラス"""
    
    def __init__(self):
        pygame.init()
        
        # 画面設定
        self.settings = settings  # 設定オブジェクトへの参照
        screen_width, screen_height = settings.get_resolution()
        set_screen_size(screen_width, screen_height)
        
        if settings.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
            actual_size = self.screen.get_size()
            set_screen_size(actual_size[0], actual_size[1])
        else:
            self.screen = pygame.display.set_mode((screen_width, screen_height), pygame.RESIZABLE)
        
        pygame.display.set_caption("NPB プロ野球ペナントシミュレーター 2026")
        
        # レンダラーと状態管理
        self.renderer = ScreenRenderer(self.screen)
        self.state_manager = GameStateManager()
        self.schedule_manager = None
        self.game_simulator = None
        
        # ペナントモード
        self.pennant_manager = None
        self.pennant_screens = PennantScreens(self.screen)
        self.pennant_draft_picks = []  # ドラフト指名リスト
        self.pennant_camp_results = None  # キャンプ結果
        self.camp_daily_result = None  # キャンプ1日の結果
        self.camp_training_menu = None  # トレーニングメニュー設定
        
        # 秋季キャンプ用
        self.fall_camp_results = None  # 秋季キャンプ結果
        self.fall_camp_daily_result = None  # 秋季キャンプ1日の結果
        self.fall_camp_training_menu = None  # 秋季トレーニングメニュー設定
        self.fall_camp_players = []  # 秋季キャンプ参加選手
        
        # UI状態
        self.buttons = {}
        self.scroll_offset = 0
        self.result_scroll = 0
        self.show_title_start_menu = False  # タイトル画面のスタートメニュー表示
        
        # 各画面のスクロール位置
        self.lineup_scroll = 0
        self.lineup_roster_tab = "all"
        self.draft_scroll = 0
        self.ikusei_draft_scroll = 0
        self.fa_scroll = 0
        self.standings_scroll = 0
        self.player_detail_scroll = 0
        
        # ロースター画面の個別スクロール
        self.roster_scroll_left = 0     # 左パネル（野手一覧等）
        self.roster_scroll_right = 0    # 右パネル（投手等）
        self.farm_scroll_first = 0      # 一軍スクロール
        self.farm_scroll_second = 0     # 二軍スクロール
        self.farm_scroll_third = 0      # 三軍スクロール
        self.order_scroll_batters = 0   # 野手一覧スクロール
        self.order_scroll_pitchers = 0  # 投手一覧スクロール
        
        # チーム名編集用
        self.custom_team_names = {}  # {元の名前: カスタム名}
        self._load_team_name_presets()  # プリセットを読み込み
        self.editing_team_idx = -1
        self.team_name_input = ""
        
        # チーム選択画面用
        self.preview_team_name = None  # 選択中（プレビュー中）のチーム名
        self.team_preview_scroll = 0  # チーム詳細プレビューのスクロール
        
        # スケジュール選択用
        self.selected_game_idx = -1  # 選択した日程のインデックス
        
        # 育成システム用
        self.selected_training_player_idx = -1
        self.training_points = 100  # 初期育成ポイント
        
        # 設定タブとスクロール
        self.settings_tab = "display"
        self.settings_scroll = 0  # 設定画面のスクロール位置
        
        # ドラフト/FA用
        self.hover_draft_index = -1
        self.selected_fa_idx = -1  # 外国人FA選択
        
        # 育成ドラフト用
        self.developmental_prospects = []  # 育成ドラフト候補
        self.developmental_draft_round = 1
        self.developmental_draft_messages = []
        self.selected_developmental_idx = -1
        self.ikusei_draft_prospects = []  # 育成ドラフト候補（別名）
        self.selected_ikusei_draft_idx = -1
        
        # 選手詳細画面用
        self.detail_player = None  # 詳細表示中の選手
        self.selected_detail_player = None  # 詳細表示中の選手（別名）
        
        # ダブルクリック検出用
        self._last_click_time = 0
        self._last_click_pos = (0, 0)
        
        # オーダー画面用（クリック選択方式）
        self.dragging_player_idx = -1
        self.drag_pos = None
        self.lineup_tab = "batters"  # "batters", "pitchers", "bench"
        self.drop_zones = {}  # ドロップゾーン情報
        self.selected_lineup_slot = -1  # 選択中のラインアップスロット
        self.order_sub_tab = "batter"  # "batter" or "pitcher" - オーダータブのサブタブ
        
        # クリック選択方式用（新）
        self.lineup_selected_player_idx = -1  # 選択中の選手インデックス
        self.lineup_swap_mode = False  # 入れ替えモード
        self.lineup_selected_slot = -1  # 選択中のスロット（打順/ローテなど）
        self.lineup_selected_source = ""  # 選択元（"roster", "lineup", "rotation"など）
        
        # ポジションクリック選択用（新）
        self.position_selected_slot = -1  # 選択中のポジションスロット
        self.position_swap_mode = False  # ポジション入れ替えモード
        
        # ROSTER_MANAGEMENT画面用のポジション選択
        self.roster_position_selected_slot = -1
        self.roster_swap_mode = False
        
        # 打順クリック選択用（新）
        self.batting_order_selected_slot = -1  # 選択中の打順スロット
        self.batting_order_swap_mode = False  # 打順入れ替えモード
        
        # ポジションドラッグ&ドロップ用
        self.dragging_position_slot = -1  # ドラッグ中の打順スロット（ポジション用）
        self.position_drag_pos = None  # ポジションドラッグの現在位置
        self.lineup_edit_mode = "player"  # "player" or "position" - 編集モード
        
        # 投手オーダー・ベンチ設定用
        self.pitcher_order_tab = "rotation"  # "rotation", "relief", "closer"
        self.selected_rotation_slot = -1  # 選択中のローテーションスロット
        self.selected_relief_slot = -1  # 選択中の中継ぎスロット
        self.bench_setting_tab = "batters"  # "batters" or "pitchers"
        self.pitcher_scroll = 0  # 投手リストスクロール
        self.bench_scroll = 0  # ベンチ設定スクロール
        
        # 経営画面用
        self.management_tab = "overview"
        
        # 記録画面用
        self.standings_tab = "standings"  # "standings", "batting", "pitching"
        
        # 新規ゲーム設定用
        self.new_game_setup_state = {"difficulty": "normal"}
        
        # ニュースリスト（メイン画面表示用）
        self.news_list = []  # 最近のニュース [{"date": "4/1", "text": "開幕戦勝利！"}, ...]
        
        # セーブ状態管理
        self.has_unsaved_changes = False  # 未保存の変更があるか
        self.show_confirm_dialog = False  # 確認ダイアログ表示中
        self.confirm_action = None  # 確認後に実行するアクション
        self._pending_pennant_start = False  # 設定画面後にペナント開始するかどうか
        # 春季キャンプ用の選択マップ（選手インデックス -> トレーニングインデックス）
        self.spring_selected_menus = {}
        
        # ポジション重複警告
        self.show_lineup_conflict_warning = False
        self.lineup_conflict_message = ""
        
        # エラーメッセージ表示用
        self.error_message = ""
        self.error_message_timer = 0  # エラーメッセージ表示時間
        
        # 試合中の戦略操作
        self.game_strategy_mode = None  # "pinch_hit", "pinch_run", "pitching_change" など
        self.strategy_candidates = []  # 交代候補選手リスト
        self.selected_strategy_idx = -1
        
        # チーム作成用
        self.new_team_name = ""  # 新規チーム名入力
        self.new_team_league = "central"  # "central" or "pacific"
        self.new_team_color_idx = 0  # 選択した色のインデックス
        self.new_team_gen_mode = "random"  # "random" or "template"
    
    def _apply_game_preset(self, preset: str):
        """ゲームプリセットを適用"""
        rules = self.settings.game_rules
        
        if preset == "real_2024":
            # 2027年NPB公式ルール（セリーグDH導入）
            rules.central_dh = True
            rules.pacific_dh = True
            rules.interleague_dh = True
            rules.regular_season_games = 143
            rules.enable_interleague = True
            rules.enable_climax_series = True
            rules.enable_spring_camp = True
            rules.enable_allstar = True
            ToastManager.show("2027年NPB公式ルールを適用", "success")
        
        elif preset == "classic":
            # 従来ルール（セDHなし）
            rules.central_dh = False
            rules.pacific_dh = True
            rules.interleague_dh = True
            rules.regular_season_games = 143
            rules.enable_interleague = True
            rules.enable_climax_series = True
            rules.enable_spring_camp = True
            rules.enable_allstar = True
            ToastManager.show("クラシックルールを適用（セDHなし）", "success")
        
        elif preset == "short":
            # ショートシーズン
            rules.central_dh = True
            rules.pacific_dh = True
            rules.regular_season_games = 120
            rules.enable_interleague = False
            rules.enable_climax_series = False
            rules.enable_spring_camp = False
            rules.enable_allstar = False
            ToastManager.show("ショートシーズンを適用", "success")
        
        elif preset == "full":
            # フルシーズン
            rules.central_dh = True
            rules.pacific_dh = True
            rules.interleague_dh = True
            rules.regular_season_games = 143
            rules.enable_interleague = True
            rules.enable_climax_series = True
            rules.enable_spring_camp = True
            rules.enable_allstar = True
            ToastManager.show("フルシーズンを適用", "success")
    
    def add_news(self, text: str, date: str = None):
        """ニュースを追加（最大10件保持）"""
        if date is None:
            # 次の試合の日付または完了した試合の日付から取得
            if self.schedule_manager and self.state_manager.player_team:
                try:
                    next_game = self.schedule_manager.get_next_game_for_team(self.state_manager.player_team.name)
                    if next_game and next_game.date:
                        if hasattr(next_game.date, 'month'):
                            date = f"{next_game.date.month}/{next_game.date.day}"
                        else:
                            date = str(next_game.date)
                    else:
                        # 完了した試合から最新の日付を探す
                        team_schedule = self.schedule_manager.get_team_schedule(self.state_manager.player_team.name)
                        completed = [g for g in team_schedule if g.is_completed]
                        if completed and completed[-1].date:
                            last_date = completed[-1].date
                            if hasattr(last_date, 'month'):
                                date = f"{last_date.month}/{last_date.day}"
                            else:
                                date = str(last_date)
                        else:
                            date = "--"
                except Exception:
                    date = "--"
            else:
                date = "--"
        
        self.news_list.insert(0, {"date": date, "text": text})
        # 最大10件に制限
        if len(self.news_list) > 10:
            self.news_list = self.news_list[:10]
    
    def reset_game_state(self):
        """ゲーム状態をリセット（新規ゲーム開始時に呼び出す）"""
        # state_manager のリセット
        self.state_manager.current_year = 2026
        self.state_manager.current_game_number = 0
        self.state_manager.current_opponent = None
        self.state_manager.player_team = None
        self.state_manager.draft_prospects = []
        self.state_manager.foreign_free_agents = []
        self.state_manager.selected_draft_pick = None
        self.state_manager.playoff_stage = None
        self.state_manager.playoff_teams = []
        
        # キャンプ関連
        self.spring_camp_day = 1
        self.spring_camp_max_days = 30
        self.spring_selected_menus = {}
        self.selected_spring_player_idx = -1
        self.selected_spring_training_idx = -1
        self.spring_filter_pos = None
        self.spring_player_scroll = 0
        
        self.fall_camp_day = 1
        self.fall_camp_max_days = 14
        self.fall_selected_menus = {}
        self.selected_fall_player_idx = -1
        self.selected_fall_training_idx = -1
        self.fall_filter_pos = None
        self.fall_player_scroll = 0
        self.fall_camp_players = []
        self.fall_camp_results = None
        self.fall_camp_daily_result = None
        self.fall_camp_training_menu = None
        
        # 育成関連
        self.selected_training_player_idx = -1
        self.training_selected_menus = {}
        self.training_filter_pos = None
        self.training_scroll = 0
        self.selected_training_idx = -1
        
        # ドラフト関連
        self.draft_round = 1
        self.draft_picks = {}
        self.draft_order = []
        self.draft_lottery_results = {}
        self.draft_waiting_for_other_teams = False
        self.current_picking_team_idx = 0
        self.draft_messages = []
        self.developmental_prospects = []
        self.developmental_draft_round = 1
        self.developmental_draft_messages = []
        self.selected_developmental_idx = -1
        self.draft_scroll = 0
        self.ikusei_draft_scroll = 0
        
        # FA関連
        self.selected_fa_idx = -1
        self.fa_scroll = 0
        
        # オーダー関連
        self.lineup_scroll = 0
        self.lineup_roster_tab = "all"
        self.lineup_selected_player_idx = -1
        self.lineup_swap_mode = False
        self.lineup_selected_slot = -1
        self.lineup_selected_source = ""
        self.lineup_tab = "batters"
        self.order_sub_tab = "batter"
        
        # 投手オーダー・ベンチ
        self.pitcher_order_tab = "rotation"
        self.selected_rotation_slot = -1
        self.selected_relief_slot = -1
        self.bench_setting_tab = "batters"
        self.pitcher_scroll = 0
        self.bench_scroll = 0
        
        # ニュース
        self.news_list = []
        
        # セーブ状態
        self.has_unsaved_changes = False
        self.show_confirm_dialog = False
        self.confirm_action = None
        
        # ペナント
        self.pennant_manager = None
        self.pennant_camp_results = None
        self.camp_daily_result = None
        self.camp_training_menu = None
        
        # その他のスクロール
        self.result_scroll = 0
        self.standings_scroll = 0
        self.player_detail_scroll = 0
        self.roster_scroll_left = 0
        self.roster_scroll_right = 0
        self.farm_scroll_first = 0
        self.farm_scroll_second = 0
        self.farm_scroll_third = 0
        self.order_scroll_batters = 0
        self.order_scroll_pitchers = 0

    def _apply_training_after_game(self):
        """試合後に育成メニューの経験値を付与（メニュー未設定時は自動選択）"""
        from player_development import PlayerDevelopment, TrainingType
        import random
        
        team = self.state_manager.player_team
        if not team:
            return
        
        all_players = team.players
        if not hasattr(self, 'training_selected_menus'):
            self.training_selected_menus = {}
        
        # 育成メニューと一致するTrainingType配列（screens.pyのUI順序と一致）
        # 投手: 投球(PITCHING), 制球(CONTROL), 変化球(BREAKING), スタミナ(STAMINA)
        # 野手: 打撃(BATTING), 筋力(POWER), 走塁(RUNNING), 守備(FIELDING), スタミナ(STAMINA)
        trainings_pitcher = [TrainingType.PITCHING, TrainingType.CONTROL, TrainingType.BREAKING,
                             TrainingType.STAMINA]
        trainings_batter = [TrainingType.BATTING, TrainingType.POWER, TrainingType.RUNNING,
                            TrainingType.FIELDING, TrainingType.STAMINA]
        
        trained_count = 0
        stat_up_count = 0
        
        for p_idx, player in enumerate(all_players):
            # メニューが設定されている場合はそれを使用
            if p_idx in self.training_selected_menus:
                t_idx = self.training_selected_menus[p_idx]
            else:
                # メニュー未設定：選手の弱点ステータスを自動選択
                t_idx = self._auto_select_training_for_player(player)
            
            if player.position.name == 'PITCHER':
                tlist = trainings_pitcher
            else:
                tlist = trainings_batter
            
            if 0 <= t_idx < len(tlist):
                ttype = tlist[t_idx]
                # 試合後育成は確実に経験値付与（guaranteed=True）、倍率0.5
                result = PlayerDevelopment.train_player(player, ttype, xp_multiplier=0.5, guaranteed=True)
                if result.get('success'):
                    trained_count += 1
                if result.get('stat_gains'):
                    stat_up_count += len(result['stat_gains'])
        
        # 経験値付与結果をトーストで表示
        if trained_count > 0:
            from ui_pro import ToastManager
            if stat_up_count > 0:
                ToastManager.show(f"試合後練習: {trained_count}人経験値獲得 ({stat_up_count}人成長)", "success")
            else:
                ToastManager.show(f"試合後練習: {trained_count}人経験値獲得", "info")

    def _auto_select_training_for_player(self, player) -> int:
        """選手の弱点を分析して自動で練習メニューを選択（AIシステム使用）"""
        from ai_system import ai_manager, AITrainingStrategy
        return ai_manager.get_smart_training_menu(player, AITrainingStrategy.WEAKNESS)

    def init_teams(self):
        """チームを初期化（固定選手データを使用）"""
        from team_generator import load_or_create_teams
        
        # 固定選手データを読み込み（なければ生成して保存）
        central_teams, pacific_teams = load_or_create_teams(
            NPB_CENTRAL_TEAMS, 
            NPB_PACIFIC_TEAMS
        )
        
        self.state_manager.central_teams = central_teams
        self.state_manager.pacific_teams = pacific_teams
        self.state_manager.all_teams = self.state_manager.central_teams + self.state_manager.pacific_teams
    
    def _create_new_team(self):
        """新規チームを作成してリーグに追加"""
        from team_generator import create_team
        from models import League
        
        # チーム名チェック
        if not self.new_team_name or len(self.new_team_name.strip()) == 0:
            ToastManager.show("チーム名を入力してください", "warning")
            return
        
        team_name = self.new_team_name.strip()
        
        # 既存のチーム名と重複チェック
        existing_names = [t.name for t in self.state_manager.all_teams]
        if team_name in existing_names:
            ToastManager.show("同じ名前のチームが既に存在します", "warning")
            return
        
        # チームカラー
        team_colors = [
            (220, 50, 50),    # 赤
            (50, 100, 220),   # 青
            (50, 180, 50),    # 緑
            (255, 180, 0),    # オレンジ
            (180, 50, 220),   # 紫
            (50, 180, 180),   # シアン
            (255, 220, 50),   # 黄
            (255, 100, 150),  # ピンク
            (100, 100, 100),  # グレー
        ]
        color = team_colors[self.new_team_color_idx % len(team_colors)]
        
        # リーグを決定
        league = League.CENTRAL if self.new_team_league == "central" else League.PACIFIC
        
        # 新規チームを作成
        new_team = create_team(team_name, league)
        new_team.color = color
        
        # リーグに追加
        if self.new_team_league == "central":
            self.state_manager.central_teams.append(new_team)
        else:
            self.state_manager.pacific_teams.append(new_team)
        
        # all_teams を更新
        self.state_manager.all_teams = self.state_manager.central_teams + self.state_manager.pacific_teams
        
        ToastManager.show(f"チーム「{team_name}」を作成しました", "success")
        
        # チーム選択画面に戻る
        self.state_manager.change_state(GameState.TEAM_SELECT)
        self.new_team_name = ""
    
    def init_schedule(self):
        """スケジュールを初期化"""
        self.schedule_manager = ScheduleManager(self.state_manager.current_year)
        self.schedule_manager.generate_season_schedule(
            self.state_manager.central_teams,
            self.state_manager.pacific_teams
        )
    
    def check_lineup_position_conflicts(self) -> str:
        """ラインナップのポジション重複をチェックし、エラーメッセージを返す"""
        team = self.state_manager.player_team
        if not team or not team.current_lineup:
            return ""
        
        from models import Position
        
        # 各ポジションの選手カウント
        position_counts = {}
        lineup = team.current_lineup
        
        # lineup_positions を取得（独立したポジション管理）
        if hasattr(team, 'lineup_positions') and team.lineup_positions:
            lineup_positions = team.lineup_positions
        else:
            lineup_positions = None
        
        # ポジション別にカウント
        for i, player_idx in enumerate(lineup):
            if player_idx < 0 or player_idx >= len(team.players):
                continue
            
            # lineup_positions がある場合はそれを使用
            if lineup_positions and i < len(lineup_positions):
                pos = lineup_positions[i]
                # 短縮名を正式名に変換
                pos_map = {"捕": "捕手", "一": "一塁手", "二": "二塁手", "三": "三塁手",
                          "遊": "遊撃手", "左": "左翼手", "中": "中堅手", "右": "右翼手", "DH": "DH", "投": "投手"}
                pos = pos_map.get(pos, pos)
            else:
                # 選手の本来のポジションを使用
                player = team.players[player_idx]
                pos = player.position.value
            
            if pos == "DH":
                continue  # DHは重複OK
            if pos == "投手":
                continue  # 投手は打順に入らない（DH制）
            
            # 外野手は左中右を合計3人まで
            if pos in ["左翼手", "中堅手", "右翼手", "外野手"]:
                pos = "外野"
            
            if pos not in position_counts:
                position_counts[pos] = 0
            position_counts[pos] += 1
        
        # 重複チェック
        errors = []
        for pos, count in position_counts.items():
            if pos == "外野":
                if count > 3:
                    errors.append(f"外野手が{count}人います（最大3人）")
            else:
                if count > 1:
                    errors.append(f"{pos}が{count}人います")
        
        if errors:
            return "ポジション重複: " + ", ".join(errors)
        
        # 必須ポジションのチェック
        rules = self.settings.game_rules
        team_league = getattr(team, 'league', None)
        from models import League
        
        use_dh = True
        if team_league == League.CENTRAL:
            use_dh = rules.central_dh
        elif team_league == League.PACIFIC:
            use_dh = rules.pacific_dh
        
        required_positions = ["捕手", "一塁手", "二塁手", "三塁手", "遊撃手"]
        missing = []
        for pos in required_positions:
            if pos not in position_counts or position_counts[pos] == 0:
                missing.append(pos)
        
        if "外野" not in position_counts or position_counts.get("外野", 0) < 3:
            outfield_count = position_counts.get("外野", 0)
            missing.append(f"外野手（あと{3 - outfield_count}人必要）")
        
        if missing:
            return "守備位置が不足: " + ", ".join(missing)
        
        return ""
    
    def auto_set_lineup(self):
        """自動でオーダーを設定"""
        self.auto_set_lineup_for_team(self.state_manager.player_team)
    
    def auto_set_lineup_for_team(self, team: Team):
        """指定チームの自動オーダー設定（ポジション考慮・DH対応）"""
        if not team:
            return
        
        from models import Position
        from settings_manager import settings
        
        # DH制の判定（リーグに応じて）
        is_pacific = hasattr(team, 'league') and team.league.value == "パシフィック"
        use_dh = (is_pacific and settings.game_rules.pacific_dh) or (not is_pacific and settings.game_rules.central_dh)
        
        # 支配下選手のみ（野手）
        batters = [p for p in team.players if not getattr(p, 'is_developmental', False) 
                   and p.position != Position.PITCHER]
        
        if len(batters) < 9:
            # 選手不足時は単純に上位9人
            batters.sort(key=lambda p: p.stats.overall_batting(), reverse=True)
            team.current_lineup = [team.players.index(b) for b in batters[:9]]
            return
        
        # ポジション別に最適選手を選ぶ
        lineup = []
        position_assignments = {}
        used_players = set()
        
        # DH制の場合は8ポジション + DH、そうでなければ8ポジション + 投手
        if use_dh:
            # 各ポジションに配置（捕手→内野→外野→DH）
            positions_order = [
                ("捕手", Position.CATCHER, 1),
                ("一塁手", Position.FIRST, 1),
                ("二塁手", Position.SECOND, 1),
                ("三塁手", Position.THIRD, 1),
                ("遊撃手", Position.SHORTSTOP, 1),
                ("外野手", Position.OUTFIELD, 3),
            ]
        else:
            # DH無しの場合は8ポジション（投手は9番）
            positions_order = [
                ("捕手", Position.CATCHER, 1),
                ("一塁手", Position.FIRST, 1),
                ("二塁手", Position.SECOND, 1),
                ("三塁手", Position.THIRD, 1),
                ("遊撃手", Position.SHORTSTOP, 1),
                ("外野手", Position.OUTFIELD, 3),
            ]
        
        # まず各本職ポジションに配置
        for pos_name, pos_enum, count in positions_order:
            candidates = [p for p in batters if p.position == pos_enum and team.players.index(p) not in used_players]
            candidates.sort(key=lambda p: p.stats.overall_batting(), reverse=True)
            
            for i in range(min(count, len(candidates))):
                player = candidates[i]
                player_idx = team.players.index(player)
                lineup.append(player_idx)
                used_players.add(player_idx)
                
                if pos_enum == Position.OUTFIELD:
                    outfield_pos = ["左翼手", "中堅手", "右翼手"][i % 3]
                    position_assignments[outfield_pos] = player_idx
                else:
                    position_assignments[pos_name] = player_idx
        
        # 8人に満たない場合、サブポジション対応選手を追加
        needed_positions = [pos for pos, _, _ in positions_order if pos not in position_assignments]
        
        # 不足ポジションを埋める（サブポジション考慮）
        while len(lineup) < 8 and len(used_players) < len(batters):
            remaining = [p for p in batters if team.players.index(p) not in used_players]
            if not remaining:
                break
            remaining.sort(key=lambda p: p.stats.overall_batting(), reverse=True)
            player = remaining[0]
            player_idx = team.players.index(player)
            lineup.append(player_idx)
            used_players.add(player_idx)
        
        # DHまたは9番目の野手を追加
        if use_dh:
            # DH: 打撃力が最も高い未使用選手
            dh_candidates = [p for p in batters if team.players.index(p) not in used_players]
            if dh_candidates:
                dh_candidates.sort(key=lambda p: p.stats.overall_batting(), reverse=True)
                dh_player = dh_candidates[0]
                dh_idx = team.players.index(dh_player)
                lineup.append(dh_idx)
                used_players.add(dh_idx)
                position_assignments["指名打者"] = dh_idx
        
        # 9人に満たない場合はさらに補充
        while len(lineup) < 9:
            remaining = [p for p in batters if team.players.index(p) not in used_players]
            if not remaining:
                break
            remaining.sort(key=lambda p: p.stats.overall_batting(), reverse=True)
            player = remaining[0]
            player_idx = team.players.index(player)
            lineup.append(player_idx)
            used_players.add(player_idx)
        
        # 打順を能力と役割で最適化
        if len(lineup) >= 9:
            lineup_players = [(idx, team.players[idx]) for idx in lineup]
            
            def get_batting_score(p, role):
                stats = p.stats
                if role == 1:  # 1番: 走力・ミート
                    return stats.contact * 1.5 + stats.run * 2 + stats.speed
                elif role == 2:  # 2番: ミート・繋ぎ
                    return stats.contact * 2 + stats.run + getattr(stats, 'clutch', 50)
                elif role == 3:  # 3番: 打率・長打
                    return stats.contact * 1.5 + stats.power * 1.5 + getattr(stats, 'clutch', 50)
                elif role == 4:  # 4番: 最強打者
                    return stats.power * 2 + stats.contact + getattr(stats, 'clutch', 50) * 1.5
                elif role == 5:  # 5番: 長打
                    return stats.power * 1.8 + stats.contact + getattr(stats, 'clutch', 50)
                else:  # 6-8番
                    return stats.overall_batting()
            
            final_lineup = [None] * 9
            remaining_players = list(lineup_players)
            
            # 4番から決定（最強打者）
            for role in [4, 3, 5, 1, 2, 6, 7, 8, 9]:
                if not remaining_players:
                    break
                best = max(remaining_players, key=lambda x: get_batting_score(x[1], role))
                final_lineup[role - 1] = best[0]
                remaining_players.remove(best)
            
            team.current_lineup = final_lineup
        else:
            team.current_lineup = lineup[:9]
        
        # position_assignmentsを設定
        if not hasattr(team, 'position_assignments'):
            team.position_assignments = {}
        team.position_assignments = position_assignments
        
        # lineup_positionsを設定（オーダー画面用）
        lineup_positions = []
        pos_short = {"捕手": "捕", "一塁手": "一", "二塁手": "二", "三塁手": "三", 
                     "遊撃手": "遊", "左翼手": "左", "中堅手": "中", "右翼手": "右", 
                     "指名打者": "DH", "外野手": "外"}
        
        for idx in team.current_lineup:
            if idx is None:
                lineup_positions.append("DH" if use_dh else "投")
                continue
            player = team.players[idx]
            # position_assignmentsから検索
            assigned_pos = None
            for pos_name, p_idx in position_assignments.items():
                if p_idx == idx:
                    assigned_pos = pos_short.get(pos_name, pos_name[:1])
                    break
            if assigned_pos:
                lineup_positions.append(assigned_pos)
            else:
                # ポジションから推測
                pos_val = player.position.value
                if pos_val == "外野手":
                    lineup_positions.append("外")
                else:
                    lineup_positions.append(pos_short.get(pos_val, pos_val[:1]))
        
        team.lineup_positions = lineup_positions
        
        # 先発投手を設定（先発適性順）
        pitchers = [p for p in team.players if not getattr(p, 'is_developmental', False) 
                    and p.position == Position.PITCHER]
        
        # 投手を適性順でソート
        starters = sorted(pitchers, key=lambda p: (p.starter_aptitude, p.stats.overall_pitching()), reverse=True)
        relievers = sorted(pitchers, key=lambda p: (p.middle_aptitude, p.stats.overall_pitching()), reverse=True)
        closers = sorted(pitchers, key=lambda p: (p.closer_aptitude, p.stats.overall_pitching()), reverse=True)
        
        # 先発ローテーション（6人）
        team.rotation = []
        used_pitchers = set()
        for p in starters[:6]:
            idx = team.players.index(p)
            team.rotation.append(idx)
            used_pitchers.add(idx)
        
        if team.rotation:
            team.starting_pitcher_idx = team.rotation[0]
        
        # 抑え（1人）
        for p in closers:
            idx = team.players.index(p)
            if idx not in used_pitchers:
                team.closer_idx = idx
                used_pitchers.add(idx)
                break
        
        # 中継ぎ（4人）
        team.setup_pitchers = []
        for p in relievers:
            if len(team.setup_pitchers) >= 4:
                break
            idx = team.players.index(p)
            if idx not in used_pitchers:
                team.setup_pitchers.append(idx)
                used_pitchers.add(idx)
    
    def _auto_set_pitcher_order(self, team: 'Team'):
        """投手オーダーをAI自動設定（先発ローテ・中継ぎ・抑え）"""
        if not team:
            return
        
        from ai_system import ai_manager
        from models import Position
        
        # AIによる最適化
        result = ai_manager.optimize_pitcher_rotation(team)
        
        # 先発ローテーション
        team.rotation = []
        for p in result['rotation'][:6]:
            idx = team.players.index(p)
            team.rotation.append(idx)
        
        # 足りない分は-1で埋める
        while len(team.rotation) < 6:
            team.rotation.append(-1)
        
        if team.rotation and team.rotation[0] >= 0:
            team.starting_pitcher_idx = team.rotation[0]
        
        # 抑え
        if result['closer']:
            team.closer_idx = team.players.index(result['closer'])
        else:
            team.closer_idx = -1
        
        # セットアップ
        team.setup_pitchers = []
        for p in result['setup']:
            team.setup_pitchers.append(team.players.index(p))

    def save_current_game(self):
        """現在のゲームをセーブ"""
        if not self.state_manager.player_team:
            ToastManager.show("セーブするデータがありません", "error")
            return
        
        try:
            from save_manager import SaveManager, create_save_data
            
            # SaveManagerインスタンスを作成
            save_mgr = SaveManager()
            
            # セーブデータを作成
            save_data = create_save_data(self)
            
            # スロット1に保存（自動セーブ）
            success = save_mgr.save_game(1, save_data)
            
            if success:
                ToastManager.show("ゲームをセーブしました", "success")
                self.has_unsaved_changes = False  # 未保存フラグをリセット
            else:
                ToastManager.show("セーブに失敗しました", "error")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Save error: {e}")
            ToastManager.show(f"セーブエラー: {str(e)[:30]}", "error")
    
    def load_saved_game(self):
        """セーブデータをロード"""
        try:
            from save_manager import SaveManager, load_save_data
            
            save_mgr = SaveManager()
            slots = save_mgr.get_save_slots()
            
            # スロット1にデータがあるか確認
            slot1 = slots[0] if slots else None
            if slot1 and slot1.get("exists"):
                save_data = save_mgr.load_game(1)
                if save_data:
                    success = load_save_data(self, save_data)
                    if success:
                        ToastManager.show("ゲームをロードしました", "success")
                        self.state_manager.change_state(GameState.MENU)
                    else:
                        ToastManager.show("ロードに失敗しました", "error")
                        self._show_error("セーブデータの読み込みに失敗しました")
                else:
                    ToastManager.show("セーブデータがありません", "warning")
                    self._show_error("セーブデータが見つかりません。新規ゲームを始めてください。")
            else:
                ToastManager.show("セーブデータがありません", "warning")
                self._show_error("セーブデータが見つかりません。新規ゲームを始めてください。")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Load error: {e}")
            ToastManager.show(f"ロードエラー: {str(e)[:30]}", "error")
            self._show_error(f"ロードエラー: {str(e)[:50]}")
    
    def start_game(self):
        """試合開始"""
        if not self.state_manager.player_team:
            return
        
        # ポジション重複チェック
        position_error = self.check_lineup_position_conflicts()
        if position_error:
            self.show_lineup_conflict_warning = True
            self.lineup_conflict_message = position_error
            ToastManager.show(position_error, "error")
            return  # 試合開始をブロック
        
        next_game = self.schedule_manager.get_next_game_for_team(self.state_manager.player_team.name)
        if not next_game:
            # シーズン終了 -> 秋季キャンプへ
            self.start_fall_camp()
            return
        
        # オーダー未設定なら自動設定
        if len(self.state_manager.player_team.current_lineup) < 9 or self.state_manager.player_team.starting_pitcher_idx < 0:
            self.auto_set_lineup()
        
        # DHなしの場合、投手を9番に入れる
        self._ensure_pitcher_in_lineup_if_no_dh(self.state_manager.player_team)
        
        # 対戦相手を決定
        is_home = next_game.home_team_name == self.state_manager.player_team.name
        opponent_name = next_game.away_team_name if is_home else next_game.home_team_name
        self.state_manager.current_opponent = next((t for t in self.state_manager.all_teams if t.name == opponent_name), None)
        
        if self.state_manager.current_opponent:
            self.auto_set_lineup_for_team(self.state_manager.current_opponent)
        
        # 試合方法選択画面に遷移
        self.state_manager.change_state(GameState.GAME_CHOICE)
    
    # ===========================
    # 采配モード
    # ===========================
    
    def start_game_manage_mode(self):
        """采配モードで試合開始（自分のチームを操作）"""
        next_game = self.schedule_manager.get_next_game_for_team(self.state_manager.player_team.name)
        if not next_game:
            return
        
        is_home = next_game.home_team_name == self.state_manager.player_team.name
        
        if is_home:
            self.game_simulator = GameSimulator(self.state_manager.player_team, self.state_manager.current_opponent)
        else:
            self.game_simulator = GameSimulator(self.state_manager.current_opponent, self.state_manager.player_team)
        
        # 采配状態を初期化
        self.game_manage_state = {
            'inning': 1,
            'is_top': True,
            'outs': 0,
            'strikes': 0,
            'balls': 0,
            'runners': [None, None, None],  # ランナー（選手オブジェクト）
            'home_score': 0,
            'away_score': 0,
            'current_batter': None,
            'current_pitcher': None,
            'play_log': [],
            'current_play': "",
            'game_finished': False,
            'pitch_count': {'player': 0, 'opponent': 0},  # チームごとの投球数
            'pitcher_pitch_count': {},  # 投手ごとの投球数
            'batter_idx_home': 0,
            'batter_idx_away': 0,
            'next_game': next_game,
            'is_home': is_home,
            'pitch_history': [],
            'at_bat_pitch_count': 0,
            # 采配関連
            'tactic': None,  # 現在の戦術指示
            'waiting_for_tactic': False,  # 戦術入力待ち
            'player_is_batting': False,  # プレイヤーが攻撃中
            'player_is_pitching': False,  # プレイヤーが守備中
            'selected_tactic': 'normal',  # 選択中の打撃戦術（UI表示用）
            'selected_pitcher_tactic': 'normal',  # 選択中の投手戦術（UI表示用）
            # 選手交代
            'substitution_mode': None,  # None, 'pinch_hit', 'pinch_run', 'defensive', 'pitcher'
            'substitution_target': None,  # 交代対象選手
            'used_players': {'home': set(), 'away': set()},  # 使用済み選手
            # 統計
            'batting_stats': {},  # 打者成績
            'pitching_stats': {},  # 投手成績
            # 投手スタミナ
            'pitcher_stamina': {},
            # 守備位置
            'defensive_positions': {'home': {}, 'away': {}},
            # 打球トラッキング
            'ball_tracking': None,
            'trajectory': [],
            'animation_frame': 0,
            'animation_active': False,
            # アニメーション待機用
            'waiting_for_animation': False,  # アニメーション終了待ち
            'pending_action': None,  # アニメーション後の処理 ('next_batter', 'record_out', etc.)
            'pending_action_args': {},  # 処理の引数
            'result_display_timer': 0,  # 結果表示タイマー
            # 球場情報
            'park_factor': 1.0,  # パークファクター（HR出やすさ）
            # 確認ダイアログ
            'confirm_skip_game': False,  # 試合スキップ確認ダイアログ表示フラグ
            # 守備シフト
            'defensive_shift': 'normal',  # 守備シフト
        }
        
        # どちらのチームをプレイヤーが操作するか設定
        state = self.game_manage_state
        if is_home:
            state['player_team'] = self.game_simulator.home_team
            state['opponent_team'] = self.game_simulator.away_team
        else:
            state['player_team'] = self.game_simulator.away_team
            state['opponent_team'] = self.game_simulator.home_team
        
        # 初期打順設定
        self._setup_manage_at_bat()
        
        self.state_manager.change_state(GameState.GAME_MANAGE)
    
    def _setup_manage_at_bat(self):
        """采配モード：次の打席の打者・投手を設定"""
        state = self.game_manage_state
        
        if state['is_top']:
            batting_team = self.game_simulator.away_team
            pitching_team = self.game_simulator.home_team
            batter_idx = state['batter_idx_away'] % 9
        else:
            batting_team = self.game_simulator.home_team
            pitching_team = self.game_simulator.away_team
            batter_idx = state['batter_idx_home'] % 9
        
        # プレイヤーの攻守状態を更新
        is_player_batting = (state['is_top'] and not state['is_home']) or (not state['is_top'] and state['is_home'])
        state['player_is_batting'] = is_player_batting
        state['player_is_pitching'] = not is_player_batting
        
        # 打者設定
        if batting_team.current_lineup and len(batting_team.current_lineup) > batter_idx:
            player_idx = batting_team.current_lineup[batter_idx]
            if player_idx < len(batting_team.players):
                state['current_batter'] = batting_team.players[player_idx]
        
        # 投手設定（現在の投手を使用）
        current_pitcher = getattr(pitching_team, 'current_pitcher', None)
        if current_pitcher is None:
            if pitching_team.starting_pitcher_idx >= 0 and pitching_team.starting_pitcher_idx < len(pitching_team.players):
                current_pitcher = pitching_team.players[pitching_team.starting_pitcher_idx]
                pitching_team.current_pitcher = current_pitcher
        state['current_pitcher'] = current_pitcher
        
        # カウントリセット
        state['strikes'] = 0
        state['balls'] = 0
        state['pitch_history'] = []
        state['at_bat_pitch_count'] = 0
        state['tactic'] = None
        state['selected_tactic'] = 'normal'  # 作戦選択状態をリセット
        state['selected_pitcher_tactic'] = 'normal'  # 投手作戦もリセット
        state['determined_result'] = None  # 前回結果をクリア
        state['result_details'] = None
        
        # 守備側チームの選手能力を守備AIに反映
        self._update_fielder_abilities(pitching_team)
        
        # プレイヤーが攻撃中なら戦術入力待ち
        if state['player_is_batting']:
            state['waiting_for_tactic'] = True
    
    def _update_fielder_abilities(self, pitching_team):
        """守備チームの選手能力を守備AIに反映"""
        if not hasattr(self, 'renderer') or not hasattr(self.renderer, 'cyber_field'):
            return
        
        cyber_field = self.renderer.cyber_field
        
        # ポジション名変換
        position_map = {
            'P': 'P', '投手': 'P',
            'C': 'C', '捕手': 'C',
            '1B': '1B', '一塁手': '1B',
            '2B': '2B', '二塁手': '2B', 
            '3B': '3B', '三塁手': '3B',
            'SS': 'SS', '遊撃手': 'SS',
            'LF': 'LF', '左翼手': 'LF',
            'CF': 'CF', '中堅手': 'CF',
            'RF': 'RF', '右翼手': 'RF',
        }
        
        # 先発オーダーから守備位置を特定
        lineup = getattr(pitching_team, 'current_lineup', [])
        defensive_positions = getattr(pitching_team, 'defensive_positions', {})
        
        for player in pitching_team.players:
            pos_name = getattr(player, 'position', 'P')
            field_pos = position_map.get(pos_name, None)
            
            if field_pos:
                # 選手の能力を取得
                stats = getattr(player, 'stats', None)
                if stats:
                    speed = getattr(stats, 'speed', 50)
                    fielding = getattr(stats, 'fielding', 50)
                    arm = getattr(stats, 'arm', 60)
                else:
                    speed, fielding, arm = 50, 50, 60
                
                # 守備AIに能力を設定
                cyber_field.fielder_abilities[field_pos] = {
                    'speed': speed,
                    'fielding': fielding,
                    'arm': arm
                }
        
        # 野手をリセット
        cyber_field.reset_fielders()
    
    def set_manage_tactic(self, tactic: str):
        """采配モード：戦術を設定"""
        state = self.game_manage_state
        state['tactic'] = tactic
        # UIの選択状態も更新（打撃戦術の場合）
        if tactic in ['normal', 'power_swing', 'contact_swing', 'take', 'bunt', 'steal']:
            state['selected_tactic'] = tactic
        state['waiting_for_tactic'] = False
    
    def set_manage_pitcher_tactic(self, tactic: str):
        """采配モード：投手戦術を設定"""
        state = self.game_manage_state
        state['pitcher_tactic'] = tactic
        # UIの選択状態も更新
        if tactic in ['normal', 'ball_first', 'strike_first']:
            state['selected_pitcher_tactic'] = tactic
    
    def set_manage_defensive_shift(self, shift_type: str):
        """采配モード：守備シフトを設定"""
        state = self.game_manage_state
        state['defensive_shift'] = shift_type
        # ミニマップの守備位置を更新
        if hasattr(self, 'renderer') and hasattr(self.renderer, 'cyber_field'):
            self.renderer.cyber_field.set_defensive_shift(shift_type)
        from ui_pro import ToastManager
        shift_names = {
            'normal': '通常', 'pull': 'プルシフト', 'opposite': '逆方向シフト',
            'infield_in': '前進守備', 'no_doubles': '二塁打阻止', 'bunt_defense': 'バント守備'
        }
        ToastManager.show(f"守備シフト: {shift_names.get(shift_type, shift_type)}", "info")
    
    def advance_game_manage(self):
        """采配モード：1プレイ進める"""
        import random
        
        state = self.game_manage_state
        if state['game_finished']:
            return
        
        # 戦術入力待ちならスキップ
        if state['waiting_for_tactic']:
            return
        
        batter = state['current_batter']
        pitcher = state['current_pitcher']
        
        if not batter or not pitcher:
            self._finish_game_manage()
            return
        
        # 投球数を更新（チームごと）
        if state.get('player_is_pitching'):
            state['pitch_count']['player'] = state['pitch_count'].get('player', 0) + 1
        else:
            state['pitch_count']['opponent'] = state['pitch_count'].get('opponent', 0) + 1
        state['at_bat_pitch_count'] = state.get('at_bat_pitch_count', 0) + 1
        
        # 投手の投球数を記録
        pitcher_id = id(pitcher)
        if pitcher_id not in state['pitcher_pitch_count']:
            state['pitcher_pitch_count'][pitcher_id] = 0
        state['pitcher_pitch_count'][pitcher_id] += 1
        
        # 投手のAIに基づいて球種を選択
        # 投手の持ち球と能力から球種と確率を決定
        pitcher_pitches = getattr(pitcher, 'pitches', {})
        if not pitcher_pitches:
            # デフォルトの球種セット
            pitcher_pitches = {'ストレート': 5, 'スライダー': 3, 'カーブ': 2}
        
        # 球種の重み付け選択（変化球レベルが高いほど選択されやすい）
        weighted_pitches = []
        for pitch_name, level in pitcher_pitches.items():
            weight = level * 2 + 1  # レベル1=3, レベル5=11
            weighted_pitches.extend([pitch_name] * weight)
        
        pitch_type = random.choice(weighted_pitches) if weighted_pitches else 'ストレート'
        
        # 投球トラッキングデータを生成
        # 球速（投手の球速能力と球種に基づく）
        base_velocity = getattr(pitcher, 'velocity', 140)  # km/h
        velocity_by_type = {
            'ストレート': 0, 'ツーシーム': -3, 'カットボール': -5,
            'スライダー': -10, 'カーブ': -20, 'フォーク': -8,
            'チェンジアップ': -15, 'シュート': -5, 'シンカー': -8,
            'スプリット': -7
        }
        velocity_mod = velocity_by_type.get(pitch_type, -5)
        pitch_velocity = base_velocity + velocity_mod + random.uniform(-3, 3)
        
        # 回転数（球種と変化球能力に基づく）
        breaking_ball = getattr(pitcher, 'breaking_ball', 50)  # 変化球能力
        base_spin = {
            'ストレート': 2200, 'ツーシーム': 2000, 'カットボール': 2400,
            'スライダー': 2500, 'カーブ': 2700, 'フォーク': 1500,
            'チェンジアップ': 1800, 'シュート': 2100, 'シンカー': 1900,
            'スプリット': 1600
        }
        spin_rate = base_spin.get(pitch_type, 2200) + int((breaking_ball - 50) * 10) + random.randint(-100, 100)
        
        # 投球位置（投手のコントロール能力に基づく）
        control = getattr(pitcher, 'control', 50)
        control_accuracy = control / 100.0  # 0.0-1.0
        # 狙った位置からのズレ（コントロールが高いほど小さい）
        max_deviation = 0.5 * (1.0 - control_accuracy * 0.8)
        target_x = random.uniform(-0.6, 0.6)  # 狙い位置
        target_y = random.uniform(0.2, 0.8)
        location_x = target_x + random.uniform(-max_deviation, max_deviation)
        location_y = target_y + random.uniform(-max_deviation * 0.7, max_deviation * 0.7)
        # 範囲を制限
        location_x = max(-1.0, min(1.0, location_x))
        location_y = max(0.0, min(1.0, location_y))
        
        # トラッキングデータを保存
        state['last_pitch_data'] = {
            'velocity': round(pitch_velocity, 1),
            'spin_rate': spin_rate,
            'location_x': round(location_x, 2),
            'location_y': round(location_y, 2),
            'pitch_type': pitch_type
        }
        
        # 戦術による結果修正
        tactic = state.get('tactic')
        
        # 投球結果をシミュレート
        pitch_result = self._simulate_manage_pitch(batter, pitcher, tactic)
        
        pitch_history_entry = {
            'type': pitch_type, 
            'result': '',
            'location_x': round(location_x, 2),
            'location_y': round(location_y, 2),
            'swing': False  # スイングしたかどうか
        }
        
        # 結果処理
        if pitch_result == 'strike':
            state['strikes'] += 1
            pitch_history_entry['result'] = '見逃し'
            pitch_history_entry['swing'] = False
            if state['strikes'] >= 3:
                state['current_play'] = f"{batter.name} 見逃し三振"
                state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
                pitch_history_entry['result'] = '見逃し三振'
                self._record_manage_player_stats(batter, pitcher, 'strikeout')
                self._record_manage_out()
            else:
                state['current_play'] = f"見逃しストライク ({state['balls']}-{state['strikes']})"
        
        elif pitch_result == 'swing_strike':
            state['strikes'] += 1
            pitch_history_entry['result'] = 'ストライク'
            pitch_history_entry['swing'] = True
            if state['strikes'] >= 3:
                state['current_play'] = f"{batter.name} 空振り三振"
                state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
                pitch_history_entry['result'] = '空振り三振'
                self._record_manage_player_stats(batter, pitcher, 'strikeout')
                self._record_manage_out()
            else:
                state['current_play'] = f"空振り ({state['balls']}-{state['strikes']})"
        
        elif pitch_result == 'ball':
            state['balls'] += 1
            pitch_history_entry['result'] = 'ボール'
            if state['balls'] >= 4:
                state['current_play'] = f"{batter.name} 四球"
                state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
                pitch_history_entry['result'] = '四球'
                rbi = 1 if all(state['runners']) else 0
                self._record_manage_player_stats(batter, pitcher, 'walk', rbi)
                self._advance_manage_runners_walk(batter)
                self._queue_next_batter()
            else:
                state['current_play'] = f"ボール ({state['balls']}-{state['strikes']})"
        
        elif pitch_result == 'foul':
            if state['strikes'] < 2:
                state['strikes'] += 1
            pitch_history_entry['result'] = 'ファウル'
            pitch_history_entry['swing'] = True  # ファウルはスイングした結果
            state['current_play'] = f"ファウル ({state['balls']}-{state['strikes']})"
        
        elif pitch_result == 'bunt_success':
            # バント成功
            state['current_play'] = f"{batter.name} 犠打成功"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            pitch_history_entry['result'] = '犠打'
            self._record_manage_player_stats(batter, pitcher, 'bunt')
            self._advance_manage_runners_bunt()
            self._record_manage_out()
        
        elif pitch_result == 'bunt_fail':
            state['strikes'] += 1
            pitch_history_entry['result'] = 'バント失敗'
            if state['strikes'] >= 3:
                state['current_play'] = f"{batter.name} バント失敗 三振"
                state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
                self._record_manage_out()
            else:
                state['current_play'] = f"バント失敗 ({state['balls']}-{state['strikes']})"
        
        elif pitch_result == 'squeeze_success':
            # スクイズ成功
            if state['runners'][2]:
                state['current_play'] = f"{batter.name} スクイズ成功！得点"
                state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
                pitch_history_entry['result'] = 'スクイズ'
                self._add_manage_run()
                state['runners'][2] = None
                self._record_manage_out()
            else:
                state['current_play'] = f"{batter.name} スクイズ失敗"
                self._record_manage_out()
        
        elif pitch_result == 'hit_and_run_success':
            # エンドラン成功
            state['current_play'] = f"{batter.name} ヒットエンドラン成功"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            pitch_history_entry['result'] = 'エンドラン'
            self._advance_manage_runners_hit(1)
            state['runners'][0] = batter
            self._queue_next_batter()
        
        elif pitch_result == 'hit_and_run_fail':
            # エンドラン失敗（併殺）
            state['current_play'] = f"{batter.name} エンドラン失敗 併殺"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            pitch_history_entry['result'] = '併殺'
            self._record_manage_out()
            self._record_manage_out()
        
        elif pitch_result == 'steal_success':
            # 盗塁成功
            stolen_base = self._execute_steal()
            if stolen_base:
                state['current_play'] = f"盗塁成功！"
                state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
                pitch_history_entry['result'] = '盗塁'
            state['balls'] += 1
            if state['balls'] >= 4:
                self._advance_manage_runners_walk(batter)
                self._queue_next_batter()
        
        elif pitch_result == 'steal_fail':
            # 盗塁失敗
            state['current_play'] = f"盗塁失敗！アウト"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            pitch_history_entry['result'] = '盗塁死'
            self._fail_steal()
        
        elif pitch_result == 'single':
            rbi = sum(1 for i, r in enumerate(state['runners']) if r and i >= 1)
            state['current_play'] = f"{batter.name} ヒット"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            pitch_history_entry['result'] = '安打'
            self._record_manage_player_stats(batter, pitcher, 'single', rbi)
            # ランナー進塁はアニメーション後に実行
            self._queue_hit_result(1, batter)
        
        elif pitch_result == 'double':
            rbi = sum(1 for r in state['runners'] if r)
            state['current_play'] = f"{batter.name} 二塁打"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            pitch_history_entry['result'] = '二塁打'
            self._record_manage_player_stats(batter, pitcher, 'double', rbi)
            # ランナー進塁はアニメーション後に実行
            self._queue_hit_result(2, batter)
        
        elif pitch_result == 'triple':
            rbi = sum(1 for r in state['runners'] if r)
            state['current_play'] = f"{batter.name} 三塁打"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            pitch_history_entry['result'] = '三塁打'
            self._record_manage_player_stats(batter, pitcher, 'triple', rbi)
            # ランナー進塁はアニメーション後に実行
            self._queue_hit_result(3, batter)
        
        elif pitch_result == 'homerun':
            rbi = sum(1 for r in state['runners'] if r) + 1
            state['current_play'] = f"{batter.name} ホームラン！"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            pitch_history_entry['result'] = '本塁打'
            self._record_manage_player_stats(batter, pitcher, 'homerun', rbi)
            # ホームラン処理はアニメーション後に実行
            self._queue_homerun_result()
        
        elif pitch_result == 'entitled_double':
            # エンタイトルツーベース（ワンバウンドでフェンス越え）
            rbi = sum(1 for r in state['runners'] if r)
            state['current_play'] = f"{batter.name} エンタイトルツーベース"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            pitch_history_entry['result'] = 'エンタイトル二塁打'
            self._record_manage_player_stats(batter, pitcher, 'double', rbi)
            # ランナー進塁（二塁打扱い）
            self._queue_hit_result(2, batter)
        
        elif pitch_result in ['out', 'groundout', 'flyout', 'lineout']:
            # トラッキングデータからアウトの種類を取得
            determined = state.get('determined_result', pitch_result)
            details = state.get('result_details', {})
            fielder = details.get('fielder', '')
            
            # 日本語の野手名変換
            fielder_jp = {
                'first': '一塁手', 'second': '二塁手', 'shortstop': '遊撃手', 
                'third': '三塁手', 'pitcher': '投手', 'catcher': '捕手',
                'left': '左翼手', 'center': '中堅手', 'right': '右翼手'
            }.get(fielder, '')
            
            # 結果に基づいてアウト種類を決定
            if determined == 'groundout' or pitch_result == 'groundout':
                out_type = 'ゴロ'
            elif determined == 'flyout' or pitch_result == 'flyout':
                out_type = 'フライ'
            elif determined == 'lineout' or pitch_result == 'lineout':
                out_type = 'ライナー'
            else:
                out_type = 'アウト'
            
            # 犠牲フライ判定（外野フライで3塁ランナーあり、2アウト未満）
            rbi = 0
            is_sac_fly = False
            if (determined == 'flyout' or pitch_result == 'flyout') and state['runners'][2] and state['outs'] < 2:
                if fielder in ['left', 'center', 'right']:
                    rbi = 1
                    is_sac_fly = True
            
            # 野手名があれば表示
            if fielder_jp:
                state['current_play'] = f"{batter.name} {fielder_jp}{out_type}"
            else:
                state['current_play'] = f"{batter.name} {out_type}アウト"
            
            if is_sac_fly:
                state['current_play'] += "（犠飛）"
            
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            pitch_history_entry['result'] = out_type
            self._record_manage_player_stats(batter, pitcher, 'sacrifice_fly' if is_sac_fly else 'out', rbi)
            
            # 犠牲フライでの得点処理
            if is_sac_fly and state['runners'][2]:
                self._add_manage_run()
                state['runners'][2] = None
            
            # 物理計算で結果が決定済みなので即座にアウト処理
            self._record_manage_out()
        
        elif pitch_result == 'double_play':
            state['current_play'] = f"{batter.name} 併殺打"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            pitch_history_entry['result'] = '併殺'
            self._record_manage_player_stats(batter, pitcher, 'double_play')
            state['runners'][0] = None
            self._record_manage_out()
            self._record_manage_out()
        
        elif pitch_result == 'sacrifice_fly':
            state['current_play'] = f"{batter.name} 犠牲フライ"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            pitch_history_entry['result'] = '犠飛'
            rbi = 1 if state['runners'][2] else 0
            self._record_manage_player_stats(batter, pitcher, 'sacrifice_fly', rbi)
            if state['runners'][2]:
                self._add_manage_run()
                state['runners'][2] = None
            self._record_manage_out()
        
        elif pitch_result == 'intentional_walk':
            state['current_play'] = f"{batter.name} 敬遠"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            pitch_history_entry['result'] = '敬遠'
            rbi = 1 if all(state['runners']) else 0
            self._record_manage_player_stats(batter, pitcher, 'intentional_walk', rbi)
            self._advance_manage_runners_walk(batter)
            self._queue_next_batter()
        
        # 投球履歴に追加
        if 'pitch_history' not in state:
            state['pitch_history'] = []
        state['pitch_history'].append(pitch_history_entry)
    
    def _simulate_manage_pitch(self, batter, pitcher, tactic):
        """采配モード：投球結果をシミュレート（戦術考慮）"""
        import random
        
        state = self.game_manage_state
        
        # 打者・投手能力
        batter_contact = getattr(batter.stats, 'contact', 50)
        batter_power = getattr(batter.stats, 'power', 50)
        batter_speed = getattr(batter.stats, 'speed', 50)
        pitcher_control = getattr(pitcher.stats, 'control', 50)
        pitcher_speed = getattr(pitcher.stats, 'speed', 50)
        
        # 戦術による処理
        if tactic == 'bunt':
            # バント
            success_rate = 50 + (batter_contact - 50) * 0.3
            if random.random() * 100 < success_rate:
                return 'bunt_success'
            else:
                return 'bunt_fail'
        
        elif tactic == 'squeeze':
            # スクイズ（3塁ランナーがいる場合のみ有効）
            if state['runners'][2]:
                success_rate = 40 + (batter_contact - 50) * 0.3
                if random.random() * 100 < success_rate:
                    return 'squeeze_success'
            return 'bunt_fail'
        
        elif tactic == 'hit_and_run':
            # ヒットエンドラン（1塁ランナーがいる場合のみ有効）
            if state['runners'][0]:
                success_rate = 35 + (batter_contact - 50) * 0.4
                if random.random() * 100 < success_rate:
                    return 'hit_and_run_success'
                else:
                    return 'hit_and_run_fail'
            return self._simulate_normal_pitch(batter, pitcher)
        
        elif tactic == 'steal':
            # 盗塁
            if state['runners'][0] or state['runners'][1]:
                runner = state['runners'][0] or state['runners'][1]
                runner_speed = getattr(runner.stats, 'speed', 50) if runner else 50
                success_rate = 40 + (runner_speed - 50) * 0.5
                if random.random() * 100 < success_rate:
                    return 'steal_success'
                else:
                    return 'steal_fail'
            return self._simulate_normal_pitch(batter, pitcher)
        
        elif tactic == 'intentional_walk':
            # 敬遠（守備側の戦術）
            return 'intentional_walk'
        
        elif tactic == 'power_swing':
            # 強振
            return self._simulate_normal_pitch(batter, pitcher, power_bonus=15)
        
        elif tactic == 'contact_swing':
            # ミート重視
            return self._simulate_normal_pitch(batter, pitcher, contact_bonus=15)
        
        elif tactic == 'take':
            # 見逃し（ボールを待つ）
            roll = random.random() * 100
            if roll < 50:
                return 'ball'
            else:
                return 'strike'
        
        else:
            return self._simulate_normal_pitch(batter, pitcher)
    
    def _simulate_normal_pitch(self, batter, pitcher, contact_bonus=0, power_bonus=0):
        """通常の投球シミュレーション（NPB統計に基づくリアルな結果）"""
        import random
        
        state = self.game_manage_state
        
        # 能力値取得
        batter_contact = getattr(batter.stats, 'contact', 50) + contact_bonus
        batter_power = getattr(batter.stats, 'power', 50) + power_bonus
        batter_eye = getattr(batter.stats, 'eye', batter_contact)
        pitcher_control = getattr(pitcher.stats, 'control', 50)
        pitcher_speed = getattr(pitcher.stats, 'speed', 50)
        pitcher_breaking = getattr(pitcher.stats, 'breaking_ball', 50)
        
        # 投手の疲労計算
        pitcher_id = id(pitcher)
        pitch_count = state['pitcher_pitch_count'].get(pitcher_id, 0)
        fatigue = min(30, pitch_count // 8)  # 8球ごとに疲労蓄積
        pitcher_control = max(20, pitcher_control - fatigue * 0.5)
        pitcher_speed = max(30, pitcher_speed - fatigue * 0.3)
        
        # カウント状況による補正
        balls = state['balls']
        strikes = state['strikes']
        
        # 投手有利カウント vs 打者有利カウント
        if strikes >= 2 and balls <= 1:
            count_advantage = 'pitcher'  # 追い込まれ
            strike_tendency = 0.70
            swing_rate = 0.55  # 追い込まれたら振りやすい
        elif balls >= 3 and strikes <= 1:
            count_advantage = 'batter'  # 打者有利
            strike_tendency = 0.55  # ストライク入れにくる
            swing_rate = 0.35  # 選べる
        else:
            count_advantage = 'neutral'
            strike_tendency = 0.62
            swing_rate = 0.45
        
        # ストライク/ボール判定（実際の投球位置で判定）
        # コントロールと状況に応じて狙う位置を決定
        control_accuracy = pitcher_control / 100.0
        
        if strike_tendency > 0.6:  # ストライクを取りに行く状況
            target_x = random.uniform(-0.35, 0.35)  # ゾーン内を狙う
            target_y = random.uniform(0.25, 0.75)
        else:
            target_x = random.uniform(-0.6, 0.6)  # 広めに
            target_y = random.uniform(0.1, 0.9)
        
        # コントロールによるブレ
        max_deviation = 0.4 * (1.0 - control_accuracy * 0.8)
        location_x = target_x + random.uniform(-max_deviation, max_deviation)
        location_y = target_y + random.uniform(-max_deviation * 0.8, max_deviation * 0.8)
        location_x = max(-1.0, min(1.0, location_x))
        location_y = max(0.0, min(1.0, location_y))
        
        # last_pitch_dataを更新
        if 'last_pitch_data' in state:
            state['last_pitch_data']['location_x'] = round(location_x, 2)
            state['last_pitch_data']['location_y'] = round(location_y, 2)
        
        # 実際の位置でストライク/ボール判定
        is_strike_zone = (-0.45 <= location_x <= 0.45) and (0.15 <= location_y <= 0.85)
        
        # 選球眼による判断
        eye_factor = (batter_eye - 50) * 0.003
        
        # スイング判定
        base_swing_rate = swing_rate
        if is_strike_zone:
            # ストライクゾーンは振る確率が高い
            swing_chance = base_swing_rate + 0.35 + (batter_contact - 50) * 0.003
        else:
            # ボールゾーンは選球眼が重要
            swing_chance = base_swing_rate - eye_factor * 10
        
        will_swing = random.random() < min(0.90, max(0.15, swing_chance))
        
        if not will_swing:
            # 見逃し
            if is_strike_zone:
                return 'strike'  # 見逃しストライク
            else:
                return 'ball'  # 見逃しボール
        
        # スイングした場合のコンタクト判定
        contact_rate = BallPhysics.NPB_STATS['contact_rate']
        contact_modifier = (batter_contact - 50) * 0.006 - (pitcher_speed + pitcher_breaking - 100) * 0.003
        final_contact_rate = contact_rate + contact_modifier
        
        if random.random() > final_contact_rate:
            # 空振り
            state['ball_tracking'] = None
            state['trajectory'] = []
            return 'swing_strike'  # 空振りストライク
        
        # コンタクトした - ファウル or インプレー判定
        foul_rate = BallPhysics.NPB_STATS['foul_rate']
        if not is_strike_zone:
            foul_rate += 0.15  # ボール球はファウルになりやすい
        
        if random.random() < foul_rate:
            # ファウル
            state['ball_tracking'] = {
                'exit_velocity': 40 + random.random() * 50,
                'launch_angle': random.uniform(-30, 70),
                'direction': random.choice([-60, -55, 55, 60]),
                'distance': 10 + random.random() * 40,
                'is_foul': True
            }
            state['trajectory'] = []
            return 'foul'
        
        # インプレー - 物理演算を使用
        ball_data = BallPhysics.calculate_batted_ball(batter, pitcher)
        
        if ball_data is None:
            # まれにフェアゾーンに飛ばない
            state['ball_tracking'] = None
            state['trajectory'] = []
            return 'strike'
        
        # パワーボーナスを適用
        if power_bonus > 0:
            ball_data['exit_velocity'] *= (1 + power_bonus / 150)
        
        trajectory = BallPhysics.calculate_trajectory(ball_data)
        
        # 飛距離を計算
        landing = BallPhysics.calculate_landing_point(trajectory)
        distance = math.sqrt(landing[0]**2 + landing[1]**2)
        ball_data['distance'] = distance
        ball_data['landing'] = landing
        
        # 打球タイプを判定して保存
        ball_type = BallPhysics.classify_ball_type(ball_data)
        state['ball_type'] = ball_type
        
        # 守備側のチームを取得
        if state['is_top']:
            fielding_team = self.game_simulator.home_team
        else:
            fielding_team = self.game_simulator.away_team
        
        # 守備能力を取得
        fielders_ability = BallPhysics.get_fielders_ability(fielding_team)
        
        # パークファクターを取得
        park_factor = state.get('park_factor', 1.0)
        
        # 結果を判定（パークファクター考慮）
        result, details = BallPhysics.determine_result(ball_data, trajectory, fielders_ability, park_factor)
        
        # アウトの場合、捕球フレームでトラッキングを切り詰め
        fielder_name = details.get('fielder', '') if details else ''
        if result in ['groundout', 'flyout', 'lineout', 'foul_flyout']:
            catch_frame = BallPhysics.calculate_catch_frame(trajectory, fielder_name)
            trajectory = trajectory[:catch_frame]
        
        # トラッキングデータを保存（捕球地点まで）
        state['ball_tracking'] = ball_data
        state['trajectory'] = [{'x': t[0], 'y': t[1], 'z': t[2]} for t in trajectory]
        state['animation_frame'] = 0
        state['animation_active'] = False
        
        # 犠牲フライの可能性（2アウト未満、3塁ランナーあり、外野フライ）
        if result == 'flyout' and state['outs'] < 2 and state['runners'][2]:
            if details and details.get('fielder', '') in ['left', 'center', 'right']:
                if distance > 55:
                    return 'sacrifice_fly'
        
        # ダブルプレーの可能性
        if result == 'groundout' and state['runners'][0] and state['outs'] < 2:
            if details and details.get('fielder', '') in ['shortstop', 'second', 'third', 'first']:
                dp_chance = 0.25 + (fielders_ability.get(details['fielder'], 50) - 50) * 0.005
                if random.random() < dp_chance:
                    state['determined_result'] = 'double_play'
                    return 'double_play'
        
        # 判定結果を保存（トラッキングと同期用）
        state['determined_result'] = result
        if details:
            state['result_details'] = details
        
        return result
    
    def _advance_manage_runners_walk(self, batter):
        """采配モード：四球時のランナー進塁"""
        state = self.game_manage_state
        
        # 押し出し
        if state['runners'][2] and state['runners'][1] and state['runners'][0]:
            self._add_manage_run()
        
        if state['runners'][1] and state['runners'][0]:
            state['runners'][2] = state['runners'][1]
        if state['runners'][0]:
            state['runners'][1] = state['runners'][0]
        state['runners'][0] = batter
    
    def _advance_manage_runners_hit(self, bases):
        """采配モード：ヒット時のランナー進塁"""
        state = self.game_manage_state
        
        for i in range(2, -1, -1):
            if state['runners'][i]:
                new_base = i + bases
                if new_base >= 3:
                    self._add_manage_run()
                    state['runners'][i] = None
                else:
                    state['runners'][new_base] = state['runners'][i]
                    state['runners'][i] = None
    
    def _advance_manage_runners_bunt(self):
        """采配モード：バント時のランナー進塁"""
        state = self.game_manage_state
        
        if state['runners'][2]:
            self._add_manage_run()
            state['runners'][2] = None
        if state['runners'][1]:
            state['runners'][2] = state['runners'][1]
            state['runners'][1] = None
        if state['runners'][0]:
            state['runners'][1] = state['runners'][0]
            state['runners'][0] = None
    
    def _execute_steal(self):
        """盗塁実行"""
        state = self.game_manage_state
        
        if state['runners'][1]:
            state['runners'][2] = state['runners'][1]
            state['runners'][1] = None
            return '3塁'
        elif state['runners'][0]:
            state['runners'][1] = state['runners'][0]
            state['runners'][0] = None
            return '2塁'
        return None
    
    def _fail_steal(self):
        """盗塁失敗"""
        state = self.game_manage_state
        
        if state['runners'][1]:
            state['runners'][1] = None
            self._record_manage_out(is_steal_out=True)
        elif state['runners'][0]:
            state['runners'][0] = None
            self._record_manage_out(is_steal_out=True)
    
    def _score_manage_homerun(self):
        """采配モード：ホームラン処理"""
        state = self.game_manage_state
        
        for i in range(3):
            if state['runners'][i]:
                self._add_manage_run()
                state['runners'][i] = None
        self._add_manage_run()
    
    def _record_manage_player_stats(self, batter, pitcher, result: str, rbi: int = 0):
        """采配モード：個人成績を記録"""
        if not batter or not pitcher:
            return
        
        # 打者成績
        if result in ['single', 'double', 'triple', 'homerun']:
            batter.record.at_bats += 1
            batter.record.hits += 1
            pitcher.record.hits_allowed += 1
            if result == 'double':
                batter.record.doubles += 1
            elif result == 'triple':
                batter.record.triples += 1
            elif result == 'homerun':
                batter.record.home_runs += 1
                batter.record.runs += 1
                pitcher.record.home_runs_allowed += 1
        elif result in ['out', 'strikeout', 'flyout', 'groundout', 'lineout', 'foul_flyout', 'double_play', 'sacrifice_fly']:
            if result != 'sacrifice_fly':
                batter.record.at_bats += 1
            if result == 'strikeout':
                batter.record.strikeouts += 1
                pitcher.record.strikeouts_pitched += 1
            if result == 'double_play':
                batter.record.grounded_into_dp += 1
            if result == 'sacrifice_fly':
                batter.record.sacrifice_flies += 1
        elif result in ['walk', 'intentional_walk', 'hit_by_pitch']:
            batter.record.walks += 1
            pitcher.record.walks_allowed += 1
        elif result in ['bunt', 'bunt_success']:
            batter.record.sacrifice_hits += 1
        elif result == 'stolen_base':
            batter.record.stolen_bases += 1
        elif result == 'caught_stealing':
            batter.record.caught_stealing += 1
        
        # 打点と失点
        if rbi > 0:
            batter.record.rbis += rbi
            pitcher.record.runs_allowed += rbi
            pitcher.record.earned_runs += rbi
    
    def _add_manage_run(self):
        """采配モード：得点追加"""
        state = self.game_manage_state
        if state['is_top']:
            state['away_score'] += 1
        else:
            state['home_score'] += 1
    
    def _record_manage_out(self, is_steal_out=False):
        """采配モード：アウト記録"""
        state = self.game_manage_state
        state['outs'] += 1
        
        if state['outs'] >= 3:
            state['outs'] = 0
            state['runners'] = [None, None, None]
            
            if state['is_top']:
                state['is_top'] = False
            else:
                state['is_top'] = True
                state['inning'] += 1
                
                # 9回終了チェック
                if state['inning'] > 9:
                    if state['home_score'] != state['away_score']:
                        self._finish_game_manage()
                        return
                    # 延長戦へ
            
            # アニメーション中なら待機設定
            if state.get('animation_active'):
                state['waiting_for_animation'] = True
                state['pending_action'] = 'setup_at_bat'
                state['result_display_timer'] = 60  # 1秒待機
            else:
                self._setup_manage_at_bat()
        elif not is_steal_out:
            # アニメーション中なら待機設定
            if state.get('animation_active'):
                state['waiting_for_animation'] = True
                state['pending_action'] = 'next_batter'
                state['result_display_timer'] = 60
            else:
                self._next_manage_batter()
    
    def _next_manage_batter(self):
        """采配モード：次の打者へ"""
        state = self.game_manage_state
        
        if state['is_top']:
            state['batter_idx_away'] += 1
        else:
            state['batter_idx_home'] += 1
        
        self._setup_manage_at_bat()
    
    def _queue_next_batter(self):
        """アニメーション待機後に次の打者へ進む"""
        state = self.game_manage_state
        if state.get('animation_active') or state.get('trajectory'):
            state['waiting_for_animation'] = True
            state['pending_action'] = 'next_batter'
            state['result_display_timer'] = 90  # アニメーション後1.5秒待機
        else:
            self._next_manage_batter()
    
    def _queue_hit_result(self, bases: int, batter):
        """アニメーション終了後にランナー進塁を実行"""
        state = self.game_manage_state
        if state.get('animation_active') or state.get('trajectory'):
            state['waiting_for_animation'] = True
            state['pending_action'] = 'hit_result'
            state['pending_action_args'] = {'bases': bases, 'batter': batter}
            state['result_display_timer'] = 90
        else:
            self._advance_manage_runners_hit(bases)
            if bases == 1:
                state['runners'][0] = batter
            elif bases == 2:
                state['runners'][1] = batter
            elif bases == 3:
                state['runners'][2] = batter
            self._next_manage_batter()
    
    def _queue_homerun_result(self):
        """アニメーション終了後にホームラン処理を実行"""
        state = self.game_manage_state
        if state.get('animation_active') or state.get('trajectory'):
            state['waiting_for_animation'] = True
            state['pending_action'] = 'homerun_result'
            state['result_display_timer'] = 90
        else:
            self._score_manage_homerun()
            self._next_manage_batter()
    
    def _execute_pending_action(self, state):
        """保留中のアクションを実行してアニメーション状態をクリア"""
        pending_action = state.get('pending_action')
        args = state.get('pending_action_args', {})
        
        # 状態をクリア
        state['waiting_for_animation'] = False
        state['pending_action'] = None
        state['pending_action_args'] = {}
        state['animation_complete'] = False
        state['trajectory'] = []
        state['ball_tracking'] = None
        state['animation_frame'] = 0
        state['anim_counter'] = 0
        
        # アクションを実行
        if pending_action == 'next_batter':
            self._next_manage_batter()
        elif pending_action == 'setup_at_bat':
            self._setup_manage_at_bat()
        elif pending_action == 'hit_result':
            bases = args.get('bases', 1)
            batter = args.get('batter')
            self._advance_manage_runners_hit(bases)
            if batter:
                if bases == 1:
                    state['runners'][0] = batter
                elif bases == 2:
                    state['runners'][1] = batter
                elif bases == 3:
                    state['runners'][2] = batter
            self._next_manage_batter()
        elif pending_action == 'homerun_result':
            self._score_manage_homerun()
            self._next_manage_batter()
    
    # 選手交代処理
    def execute_pinch_hitter(self, new_player):
        """代打"""
        state = self.game_manage_state
        
        if state['is_top']:
            batting_team = self.game_simulator.away_team if state['is_home'] else self.game_simulator.home_team
            batter_idx = state['batter_idx_away'] % 9
        else:
            batting_team = self.game_simulator.home_team if state['is_home'] else self.game_simulator.away_team
            batter_idx = state['batter_idx_home'] % 9
        
        # ラインナップを更新
        if batting_team.current_lineup and len(batting_team.current_lineup) > batter_idx:
            old_idx = batting_team.current_lineup[batter_idx]
            new_idx = batting_team.players.index(new_player)
            batting_team.current_lineup[batter_idx] = new_idx
            
            # 使用済みマーク
            team_key = 'home' if batting_team == self.game_simulator.home_team else 'away'
            state['used_players'][team_key].add(old_idx)
        
        state['current_batter'] = new_player
        state['substitution_mode'] = None
    
    def execute_pinch_runner(self, base_idx, new_player):
        """代走"""
        state = self.game_manage_state
        
        if state['runners'][base_idx]:
            old_runner = state['runners'][base_idx]
            state['runners'][base_idx] = new_player
            
            # 使用済みマーク
            if state['is_top']:
                batting_team = self.game_simulator.away_team if state['is_home'] else self.game_simulator.home_team
            else:
                batting_team = self.game_simulator.home_team if state['is_home'] else self.game_simulator.away_team
            
            team_key = 'home' if batting_team == self.game_simulator.home_team else 'away'
            if old_runner in batting_team.players:
                state['used_players'][team_key].add(batting_team.players.index(old_runner))
        
        state['substitution_mode'] = None
    
    def execute_pitcher_change(self, new_pitcher):
        """投手交代"""
        state = self.game_manage_state
        
        if state['is_top']:
            pitching_team = self.game_simulator.home_team if state['is_home'] else self.game_simulator.away_team
        else:
            pitching_team = self.game_simulator.away_team if state['is_home'] else self.game_simulator.home_team
        
        old_pitcher = pitching_team.current_pitcher
        pitching_team.current_pitcher = new_pitcher
        state['current_pitcher'] = new_pitcher
        
        # 使用済みマーク
        team_key = 'home' if pitching_team == self.game_simulator.home_team else 'away'
        if old_pitcher and old_pitcher in pitching_team.players:
            state['used_players'][team_key].add(pitching_team.players.index(old_pitcher))
        
        state['substitution_mode'] = None
    
    def execute_defensive_substitution(self, position, new_player):
        """守備固め"""
        state = self.game_manage_state
        
        if state['is_top']:
            fielding_team = self.game_simulator.home_team if state['is_home'] else self.game_simulator.away_team
        else:
            fielding_team = self.game_simulator.away_team if state['is_home'] else self.game_simulator.home_team
        
        # ラインナップで該当ポジションを探して交代
        team_key = 'home' if fielding_team == self.game_simulator.home_team else 'away'
        
        # 守備位置をマップ
        if team_key not in state['defensive_positions']:
            state['defensive_positions'][team_key] = {}
        state['defensive_positions'][team_key][position] = new_player
        
        state['substitution_mode'] = None
    
    def _finish_game_manage(self):
        """采配モード：試合終了"""
        state = self.game_manage_state
        state['game_finished'] = True
        
        # game_simulatorに結果を反映
        self.game_simulator.home_score = state['home_score']
        self.game_simulator.away_score = state['away_score']
        self.game_simulator.inning = state['inning']
    
    def end_game_manage(self):
        """采配モード終了、結果画面へ遷移"""
        state = self.game_manage_state
        
        # 試合が終わっていなければ残りをシミュレート
        if not state['game_finished']:
            for _ in range(500):
                if state['game_finished']:
                    break
                state['waiting_for_tactic'] = False  # 自動進行
                state['tactic'] = None
                self.advance_game_manage()
        
        # ===== 個人成績を各選手に反映 =====
        self._apply_manage_game_stats()
        
        # 試合結果を記録
        next_game = state['next_game']
        self.schedule_manager.complete_game(next_game, state['home_score'], state['away_score'])
        
        # チームの勝敗を更新（重要：これがないと順位に反映されない）
        is_home = state['is_home']
        player_team = self.state_manager.player_team
        opponent = self.state_manager.current_opponent
        
        if is_home:
            if state['home_score'] > state['away_score']:
                player_team.wins += 1
                opponent.losses += 1
            elif state['home_score'] < state['away_score']:
                player_team.losses += 1
                opponent.wins += 1
            else:
                player_team.draws = getattr(player_team, 'draws', 0) + 1
                opponent.draws = getattr(opponent, 'draws', 0) + 1
        else:
            if state['away_score'] > state['home_score']:
                player_team.wins += 1
                opponent.losses += 1
            elif state['away_score'] < state['home_score']:
                player_team.losses += 1
                opponent.wins += 1
            else:
                player_team.draws = getattr(player_team, 'draws', 0) + 1
                opponent.draws = getattr(opponent, 'draws', 0) + 1
        
        # 育成メニューによる経験値付与
        self._apply_training_after_game()
        
        # ニュースに追加
        is_home = state['is_home']
        if is_home:
            opponent_name = self.state_manager.current_opponent.name
            if state['home_score'] > state['away_score']:
                self.add_news(f"vs {opponent_name} {state['home_score']}-{state['away_score']} 勝利！")
            elif state['home_score'] < state['away_score']:
                self.add_news(f"vs {opponent_name} {state['home_score']}-{state['away_score']} 敗戦")
            else:
                self.add_news(f"vs {opponent_name} {state['home_score']}-{state['away_score']} 引き分け")
        else:
            opponent_name = self.state_manager.current_opponent.name
            if state['away_score'] > state['home_score']:
                self.add_news(f"@ {opponent_name} {state['away_score']}-{state['home_score']} 勝利！")
            elif state['away_score'] < state['home_score']:
                self.add_news(f"@ {opponent_name} {state['away_score']}-{state['home_score']} 敗戦")
            else:
                self.add_news(f"@ {opponent_name} {state['away_score']}-{state['home_score']} 引き分け")
        
        self.has_unsaved_changes = True
        self.state_manager.change_state(GameState.RESULT)
    
    def skip_manage_to_inning_end(self):
        """采配モード：イニング終了までスキップ"""
        state = self.game_manage_state
        if state['game_finished']:
            return
        
        current_inning = state['inning']
        current_is_top = state['is_top']
        
        for _ in range(100):
            if state['game_finished']:
                break
            if state['inning'] != current_inning or state['is_top'] != current_is_top:
                break
            state['waiting_for_tactic'] = False
            state['tactic'] = None
            self.advance_game_manage()
    
    def skip_manage_to_game_end(self):
        """采配モード：試合終了までスキップし、結果画面へ遷移"""
        state = self.game_manage_state
        if state['game_finished']:
            # 既に終了している場合は結果画面へ
            self.end_game_manage()
            return
        
        # 現在のスコアを保存
        current_home_score = state['home_score']
        current_away_score = state['away_score']
        current_inning = state['inning']
        
        # game_simulatorを使って残りの試合をシミュレート
        # 現在のスコアから開始
        self.game_simulator.home_score = current_home_score
        self.game_simulator.away_score = current_away_score
        self.game_simulator.inning = current_inning
        
        # シミュレートを実行（現在のイニングから続行）
        home_score, away_score = self.game_simulator.simulate_game()
        
        # シミュレート結果をstateに反映
        state['home_score'] = home_score
        state['away_score'] = away_score
        state['game_finished'] = True
        state['inning'] = self.game_simulator.inning
        
        # 結果画面へ遷移
        self.end_game_manage()
    
    def _apply_manage_game_stats(self):
        """采配モード：試合の個人成績を各選手に反映"""
        state = self.game_manage_state
        batting_stats = state.get('batting_stats', {})
        pitching_stats = state.get('pitching_stats', {})
        
        # 打撃成績を反映
        for player_key, stats in batting_stats.items():
            # player_keyは "team_name:player_name" または player オブジェクト参照
            if isinstance(player_key, str) and ':' in player_key:
                team_name, player_name = player_key.split(':', 1)
                # チームと選手を探す
                for team in [self.game_simulator.home_team, self.game_simulator.away_team]:
                    if team.name == team_name:
                        for player in team.players:
                            if player.name == player_name:
                                self._add_batting_stats_to_player(player, stats)
                                break
            elif hasattr(player_key, 'name'):
                # 直接playerオブジェクトの場合
                self._add_batting_stats_to_player(player_key, stats)
        
        # 投手成績を反映
        for player_key, stats in pitching_stats.items():
            if isinstance(player_key, str) and ':' in player_key:
                team_name, player_name = player_key.split(':', 1)
                for team in [self.game_simulator.home_team, self.game_simulator.away_team]:
                    if team.name == team_name:
                        for player in team.players:
                            if player.name == player_name:
                                self._add_pitching_stats_to_player(player, stats)
                                break
            elif hasattr(player_key, 'name'):
                self._add_pitching_stats_to_player(player_key, stats)
    
    def _add_batting_stats_to_player(self, player, stats):
        """打撃成績を選手に加算"""
        if not hasattr(player, 'season_stats'):
            player.season_stats = {}
        
        ss = player.season_stats
        ss['games'] = ss.get('games', 0) + 1
        ss['at_bats'] = ss.get('at_bats', 0) + stats.get('at_bats', 0)
        ss['hits'] = ss.get('hits', 0) + stats.get('hits', 0)
        ss['doubles'] = ss.get('doubles', 0) + stats.get('doubles', 0)
        ss['triples'] = ss.get('triples', 0) + stats.get('triples', 0)
        ss['home_runs'] = ss.get('home_runs', 0) + stats.get('home_runs', 0)
        ss['rbis'] = ss.get('rbis', 0) + stats.get('rbis', 0)
        ss['runs'] = ss.get('runs', 0) + stats.get('runs', 0)
        ss['walks'] = ss.get('walks', 0) + stats.get('walks', 0)
        ss['strikeouts'] = ss.get('strikeouts', 0) + stats.get('strikeouts', 0)
        ss['stolen_bases'] = ss.get('stolen_bases', 0) + stats.get('stolen_bases', 0)
    
    def _add_pitching_stats_to_player(self, player, stats):
        """投手成績を選手に加算"""
        if not hasattr(player, 'season_stats'):
            player.season_stats = {}
        
        ss = player.season_stats
        ss['games_pitched'] = ss.get('games_pitched', 0) + 1
        ss['innings_pitched'] = ss.get('innings_pitched', 0) + stats.get('innings', 0)
        ss['hits_allowed'] = ss.get('hits_allowed', 0) + stats.get('hits', 0)
        ss['runs_allowed'] = ss.get('runs_allowed', 0) + stats.get('runs', 0)
        ss['earned_runs'] = ss.get('earned_runs', 0) + stats.get('earned_runs', stats.get('runs', 0))
        ss['walks_allowed'] = ss.get('walks_allowed', 0) + stats.get('walks', 0)
        ss['strikeouts_pitched'] = ss.get('strikeouts_pitched', 0) + stats.get('strikeouts', 0)
        ss['wins'] = ss.get('wins', 0) + stats.get('wins', 0)
        ss['losses'] = ss.get('losses', 0) + stats.get('losses', 0)
        ss['saves'] = ss.get('saves', 0) + stats.get('saves', 0)

    def _show_manage_substitution_dialog(self, mode: str):
        """采配モード：選手交代ダイアログを表示"""
        state = self.game_manage_state
        state['substitution_mode'] = mode
        
        # 交代可能な選手をリストアップ
        player_team = state['player_team']
        used = state['used_players']
        team_key = 'home' if player_team == self.game_simulator.home_team else 'away'
        used_set = used.get(team_key, set())
        
        available = []
        if mode == 'pinch_hit':
            # 代打：野手（現在ラインナップにいない選手）
            lineup_set = set(player_team.current_lineup) if player_team.current_lineup else set()
            for i, p in enumerate(player_team.players):
                if i not in used_set and i not in lineup_set:
                    if p.position.name != 'PITCHER':
                        available.append(p)
        elif mode == 'pinch_run':
            # 代走：足の速い選手
            lineup_set = set(player_team.current_lineup) if player_team.current_lineup else set()
            for i, p in enumerate(player_team.players):
                if i not in used_set and i not in lineup_set:
                    available.append(p)
            # 足の速い順にソート
            available.sort(key=lambda x: getattr(x.stats, 'speed', 50), reverse=True)
        elif mode == 'pitcher':
            # 投手交代
            current_pitcher = state['current_pitcher']
            for i, p in enumerate(player_team.players):
                if i not in used_set and p.position.name == 'PITCHER':
                    if p != current_pitcher:
                        available.append(p)
        elif mode == 'defensive':
            # 守備固め
            lineup_set = set(player_team.current_lineup) if player_team.current_lineup else set()
            for i, p in enumerate(player_team.players):
                if i not in used_set and i not in lineup_set:
                    available.append(p)
        
        self.substitution_available_players = available
    
    def _execute_manage_substitution(self, idx: int):
        """采配モード：選手交代を実行"""
        state = self.game_manage_state
        mode = state.get('substitution_mode')
        available = getattr(self, 'substitution_available_players', [])
        
        if idx >= len(available):
            return
        
        new_player = available[idx]
        
        if mode == 'pinch_hit':
            self.execute_pinch_hitter(new_player)
            ToastManager.show(f"代打: {new_player.name}", "info")
        elif mode == 'pinch_run':
            # 最も進んでいる塁のランナーを交代
            for i in range(2, -1, -1):
                if state['runners'][i]:
                    self.execute_pinch_runner(i, new_player)
                    ToastManager.show(f"代走: {new_player.name}", "info")
                    break
        elif mode == 'pitcher':
            self.execute_pitcher_change(new_player)
            ToastManager.show(f"投手交代: {new_player.name}", "info")
        elif mode == 'defensive':
            # 守備固め（とりあえずポジションを引き継ぐ）
            self.execute_defensive_substitution(new_player.position.name, new_player)
            ToastManager.show(f"守備固め: {new_player.name}", "info")
        
        self.substitution_available_players = []

    def start_game_watch_mode(self):
        """観戦モードで試合開始（自動進行、ユーザー入力なし）"""
        next_game = self.schedule_manager.get_next_game_for_team(self.state_manager.player_team.name)
        if not next_game:
            return
        
        is_home = next_game.home_team_name == self.state_manager.player_team.name
        
        if is_home:
            self.state_manager.current_opponent = next((t for t in self.state_manager.all_teams if t.name == next_game.away_team_name), None)
            self.game_simulator.home_team = self.state_manager.player_team
            self.game_simulator.away_team = self.state_manager.current_opponent
        else:
            self.state_manager.current_opponent = next((t for t in self.state_manager.all_teams if t.name == next_game.home_team_name), None)
            self.game_simulator.home_team = self.state_manager.current_opponent
            self.game_simulator.away_team = self.state_manager.player_team
        
        # 観戦状態を初期化（采配モードとほぼ同じ構造）
        self.game_watch_state = {
            'inning': 1,
            'is_top': True,
            'outs': 0,
            'strikes': 0,
            'balls': 0,
            'runners': [None, None, None],
            'home_score': 0,
            'away_score': 0,
            'current_batter': None,
            'current_pitcher': None,
            'play_log': [],
            'current_play': "",
            'game_finished': False,
            'pitch_count': {'player': 0, 'opponent': 0},
            'pitcher_pitch_count': {},
            'batter_idx_home': 0,
            'batter_idx_away': 0,
            'next_game': next_game,
            'is_home': is_home,
            'pitch_history': [],
            'at_bat_pitch_count': 0,
            # 観戦モードは自動進行
            'auto_play': True,
            # トラッキング
            'ball_tracking': None,
            'trajectory': [],
            'animation_frame': 0,
            'animation_active': False,
            'waiting_for_animation': False,
            'pending_action': None,
            'pending_action_args': {},
            'result_display_timer': 0,
        }
        
        # 先頭打者と投手を設定
        state = self.game_watch_state
        state['current_batter'] = self._get_watch_lineup_batter(0, True)
        state['current_pitcher'] = self._get_watch_starting_pitcher(False)
        
        self.state_manager.change_state(GameState.GAME_WATCH)
    
    def _get_watch_lineup_batter(self, idx: int, is_top: bool):
        """観戦モード：打順から打者を取得"""
        team = self.game_simulator.away_team if is_top else self.game_simulator.home_team
        lineup = getattr(team, 'lineup', team.players[:9])
        return lineup[idx % len(lineup)] if lineup else team.players[idx % len(team.players)]
    
    def _get_watch_starting_pitcher(self, is_top: bool):
        """観戦モード：先発投手を取得"""
        team = self.game_simulator.home_team if is_top else self.game_simulator.away_team
        for player in team.players:
            if hasattr(player, 'position') and player.position.name == 'PITCHER':
                if hasattr(player, 'pitch_type') and player.pitch_type and player.pitch_type.name == 'STARTER':
                    return player
        # 先発が見つからない場合は最初の投手
        for player in team.players:
            if hasattr(player, 'position') and player.position.name == 'PITCHER':
                return player
        return team.players[0]
    
    def advance_game_watch(self):
        """観戦モード：1プレイ進める（自動処理）"""
        import random
        
        state = self.game_watch_state
        if state['game_finished']:
            return
        
        batter = state['current_batter']
        pitcher = state['current_pitcher']
        
        if not batter or not pitcher:
            self._finish_game_watch()
            return
        
        # 投球結果をシミュレート（采配モードと同じロジック）
        pitch_result = self._simulate_watch_pitch(batter, pitcher)
        
        # 結果処理
        if pitch_result == 'strike':
            state['strikes'] += 1
            if state['strikes'] >= 3:
                state['current_play'] = f"{batter.name} 三振"
                state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
                self._record_watch_player_stats(batter, pitcher, 'strikeout')
                self._record_watch_out()
            else:
                state['current_play'] = f"ストライク ({state['balls']}-{state['strikes']})"
        
        elif pitch_result == 'ball':
            state['balls'] += 1
            if state['balls'] >= 4:
                state['current_play'] = f"{batter.name} 四球"
                state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
                rbi = 1 if all(state['runners']) else 0
                self._record_watch_player_stats(batter, pitcher, 'walk', rbi)
                self._advance_watch_runners_walk(batter)
                self._next_watch_batter()
            else:
                state['current_play'] = f"ボール ({state['balls']}-{state['strikes']})"
        
        elif pitch_result == 'foul':
            if state['strikes'] < 2:
                state['strikes'] += 1
            state['current_play'] = f"ファウル ({state['balls']}-{state['strikes']})"
        
        elif pitch_result == 'single':
            rbi = sum(1 for i, r in enumerate(state['runners']) if r and i >= 1)
            state['current_play'] = f"{batter.name} ヒット"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            self._record_watch_player_stats(batter, pitcher, 'single', rbi)
            self._advance_watch_runners_hit(1, batter)
            self._next_watch_batter()
        
        elif pitch_result == 'double':
            rbi = sum(1 for r in state['runners'] if r)
            state['current_play'] = f"{batter.name} 二塁打"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            self._record_watch_player_stats(batter, pitcher, 'double', rbi)
            self._advance_watch_runners_hit(2, batter)
            self._next_watch_batter()
        
        elif pitch_result == 'triple':
            rbi = sum(1 for r in state['runners'] if r)
            state['current_play'] = f"{batter.name} 三塁打"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            self._record_watch_player_stats(batter, pitcher, 'triple', rbi)
            self._advance_watch_runners_hit(3, batter)
            self._next_watch_batter()
        
        elif pitch_result == 'homerun':
            rbi = sum(1 for r in state['runners'] if r) + 1
            state['current_play'] = f"{batter.name} ホームラン！"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            self._record_watch_player_stats(batter, pitcher, 'homerun', rbi)
            self._score_watch_runs(rbi)
            state['runners'] = [None, None, None]
            self._next_watch_batter()
        
        elif pitch_result in ['out', 'groundout', 'flyout']:
            state['current_play'] = f"{batter.name} アウト"
            state['play_log'].append(f"{state['inning']}回{'表' if state['is_top'] else '裏'}: {state['current_play']}")
            self._record_watch_player_stats(batter, pitcher, 'out')
            self._record_watch_out()
    
    def _simulate_watch_pitch(self, batter, pitcher):
        """観戦モード：投球結果をシミュレート"""
        import random
        
        # 打者と投手の能力から結果を決定
        bat_contact = getattr(batter.stats, 'contact', 50)
        bat_power = getattr(batter.stats, 'power', 50)
        pitch_control = getattr(pitcher.stats, 'control', 50)
        pitch_stuff = getattr(pitcher.stats, 'stuff', 50)
        
        # 基本確率
        strike_chance = 0.35 + (pitch_control - 50) / 200
        ball_chance = 0.30 - (pitch_control - 50) / 200
        contact_chance = 0.35 * (bat_contact / 50)
        
        roll = random.random()
        
        if roll < strike_chance:
            # スイングするかどうか
            if random.random() < 0.4:
                return 'strike'
            else:
                # スイングした
                if random.random() < 0.25:
                    return 'foul'
                else:
                    return 'strike'
        elif roll < strike_chance + ball_chance:
            return 'ball'
        else:
            # 打球
            hit_quality = (bat_contact + bat_power) / 2 - (pitch_control + pitch_stuff) / 2
            hit_roll = random.random() * 100
            
            if hit_roll < 5 + hit_quality / 10:
                return 'homerun'
            elif hit_roll < 8 + hit_quality / 8:
                return 'triple'
            elif hit_roll < 15 + hit_quality / 5:
                return 'double'
            elif hit_roll < 35 + hit_quality / 3:
                return 'single'
            elif hit_roll < 50:
                return 'foul'
            else:
                return random.choice(['groundout', 'flyout', 'out'])
    
    def _record_watch_player_stats(self, batter, pitcher, result: str, rbi: int = 0):
        """観戦モード：個人成績を記録"""
        if not batter or not pitcher:
            return
        
        # 打者成績
        if result in ['single', 'double', 'triple', 'homerun']:
            batter.record.at_bats += 1
            batter.record.hits += 1
            pitcher.record.hits_allowed += 1
            if result == 'double':
                batter.record.doubles += 1
            elif result == 'triple':
                batter.record.triples += 1
            elif result == 'homerun':
                batter.record.home_runs += 1
                batter.record.runs += 1
                pitcher.record.home_runs_allowed += 1
        elif result in ['out', 'strikeout', 'flyout', 'groundout']:
            batter.record.at_bats += 1
            if result == 'strikeout':
                batter.record.strikeouts += 1
                pitcher.record.strikeouts_pitched += 1
        elif result in ['walk']:
            batter.record.walks += 1
            pitcher.record.walks_allowed += 1
        
        # 打点と失点
        if rbi > 0:
            batter.record.rbis += rbi
            pitcher.record.runs_allowed += rbi
            pitcher.record.earned_runs += rbi
    
    def _record_watch_out(self):
        """観戦モード：アウトを記録"""
        state = self.game_watch_state
        state['outs'] += 1
        
        if state['outs'] >= 3:
            # チェンジ
            state['outs'] = 0
            state['runners'] = [None, None, None]
            
            if state['is_top']:
                state['is_top'] = False
            else:
                state['is_top'] = True
                state['inning'] += 1
                
                # 9回裏終了または勝ち越し判定
                if state['inning'] > 9:
                    if state['home_score'] != state['away_score']:
                        self._finish_game_watch()
                        return
            
            # 投手交代（簡易）
            state['current_pitcher'] = self._get_watch_starting_pitcher(state['is_top'])
        
        self._next_watch_batter()
    
    def _next_watch_batter(self):
        """観戦モード：次の打者"""
        state = self.game_watch_state
        if state['is_top']:
            state['batter_idx_away'] = (state['batter_idx_away'] + 1) % 9
            state['current_batter'] = self._get_watch_lineup_batter(state['batter_idx_away'], True)
        else:
            state['batter_idx_home'] = (state['batter_idx_home'] + 1) % 9
            state['current_batter'] = self._get_watch_lineup_batter(state['batter_idx_home'], False)
        state['balls'] = 0
        state['strikes'] = 0
    
    def _advance_watch_runners_walk(self, batter):
        """観戦モード：四球でランナー進塁"""
        state = self.game_watch_state
        # 押し出し判定
        if all(state['runners']):
            self._score_watch_runs(1)
        # ランナー進塁
        if state['runners'][1]:
            state['runners'][2] = state['runners'][1]
        if state['runners'][0]:
            state['runners'][1] = state['runners'][0]
        state['runners'][0] = batter
    
    def _advance_watch_runners_hit(self, bases: int, batter):
        """観戦モード：ヒットでランナー進塁"""
        state = self.game_watch_state
        runs = 0
        
        # 三塁打以上は全員ホーム
        if bases >= 3:
            for i in range(3):
                if state['runners'][i]:
                    runs += 1
                    state['runners'][i] = None
        elif bases == 2:
            # 二塁打：2塁3塁ランナーホーム
            for i in range(1, 3):
                if state['runners'][i]:
                    runs += 1
                    state['runners'][i] = None
            if state['runners'][0]:
                state['runners'][2] = state['runners'][0]
                state['runners'][0] = None
        else:
            # 単打
            if state['runners'][2]:
                runs += 1
                state['runners'][2] = None
            if state['runners'][1]:
                state['runners'][2] = state['runners'][1]
                state['runners'][1] = None
            if state['runners'][0]:
                state['runners'][1] = state['runners'][0]
        
        if runs > 0:
            self._score_watch_runs(runs)
        
        # 打者を塁に
        if bases == 1:
            state['runners'][0] = batter
        elif bases == 2:
            state['runners'][1] = batter
        elif bases == 3:
            state['runners'][2] = batter
    
    def _score_watch_runs(self, runs: int):
        """観戦モード：得点追加"""
        state = self.game_watch_state
        if state['is_top']:
            state['away_score'] += runs
        else:
            state['home_score'] += runs

    def start_draft(self):
        """ドラフト画面に遷移"""
        self.generate_draft_prospects()
        self.state_manager.change_state(GameState.DRAFT)
    
    # end_game_watchの残骸削除済み

    def generate_draft_prospects(self):
        """NPB式ドラフト候補を生成"""
        self.state_manager.draft_prospects = []
        
        # ドラフト状態を初期化
        self.draft_round = 1  # 現在の指名順位（1巡目、2巡目...）
        self.max_draft_rounds = 8  # 最大8巡
        self.draft_picks = {}  # チーム名 -> 獲得選手リスト
        self.draft_order = []  # 指名順（ウェーバー方式）
        self.draft_lottery_results = {}  # 1巡目のくじ引き結果
        self.draft_waiting_for_other_teams = False  # 他チームの指名待ち
        self.current_picking_team_idx = 0  # 現在指名中のチームインデックス
        self.draft_messages = []  # ドラフト中のメッセージログ
        
        # 投手候補（40人）
        for i in range(40):
            pitch_type = random.choice([PitchType.STARTER, PitchType.RELIEVER, PitchType.CLOSER])
            potential = random.choices([9, 8, 7, 6, 5, 4], weights=[2, 5, 10, 20, 30, 33])[0]
            prospect = create_draft_prospect(Position.PITCHER, pitch_type, potential)
            self.state_manager.draft_prospects.append(prospect)
        
        # 野手候補（60人）
        positions = [Position.CATCHER, Position.FIRST, Position.SECOND, Position.THIRD,
                    Position.SHORTSTOP, Position.OUTFIELD, Position.OUTFIELD]
        for i in range(60):
            position = random.choice(positions)
            potential = random.choices([9, 8, 7, 6, 5, 4], weights=[2, 5, 10, 20, 30, 33])[0]
            prospect = create_draft_prospect(position, None, potential)
            self.state_manager.draft_prospects.append(prospect)
        
        # ポテンシャル順にソート
        self.state_manager.draft_prospects.sort(key=lambda p: p.potential, reverse=True)
        
        # 指名順を設定（前シーズン下位チームから）
        all_teams = self.state_manager.all_teams[:]
        all_teams.sort(key=lambda t: t.winning_percentage)  # 勝率低い順
        
        # 1巡目はくじ引き（後で実装）
        self.draft_order = [team.name for team in all_teams]
    
    def auto_pick_for_team(self, team_name):
        """AIチームの自動指名"""
        # 残っている最高ポテンシャル選手を選択
        available = [p for p in self.state_manager.draft_prospects if not p.drafted]
        if not available:
            return None
        
        # 最初の1人（最高ポテンシャル）を選択
        pick = available[0]
        pick.drafted = True
        
        # チームに追加
        for team in self.state_manager.all_teams:
            if team.name == team_name:
                team.players.append(pick)
                if team_name not in self.draft_picks:
                    self.draft_picks[team_name] = []
                self.draft_picks[team_name].append(pick)
                self.draft_messages.append(f"{team_name}が{pick.name}を指名！")
                break
        
        return pick

    def execute_player_draft_pick(self, prospect):
        """プレイヤーチームの指名を実行"""
        if not prospect or prospect.drafted:
            return False
        
        prospect.drafted = True
        team_name = self.state_manager.player_team.name
        
        self.state_manager.player_team.players.append(prospect)
        if team_name not in self.draft_picks:
            self.draft_picks[team_name] = []
        self.draft_picks[team_name].append(prospect)
        self.draft_messages.append(f"あなたのチームが{prospect.name}を指名！")
        
        return True

    def advance_draft_round(self):
        """ドラフトの次のラウンドへ進める"""
        self.draft_round += 1
        if self.draft_round > self.max_draft_rounds:
            # ドラフト終了
            return False
        self.current_picking_team_idx = 0
        return True

    def skip_to_game_end(self):
        """試合終了までスキップし、結果画面へ遷移"""
        state = self.game_watch_state
        if state['game_finished']:
            # 既に終了している場合は結果画面へ
            self.end_game_watch()
            return
        
        # 現在のスコアを保存
        current_home_score = state['home_score']
        current_away_score = state['away_score']
        current_inning = state['inning']
        
        # game_simulatorを使って残りの試合をシミュレート
        # 現在のスコアから開始
        self.game_simulator.home_score = current_home_score
        self.game_simulator.away_score = current_away_score
        self.game_simulator.inning = current_inning
        
        # シミュレートを実行（現在のイニングから続行）
        home_score, away_score = self.game_simulator.simulate_game()
        
        # シミュレート結果をstateに反映
        state['home_score'] = home_score
        state['away_score'] = away_score
        state['game_finished'] = True
        state['inning'] = self.game_simulator.inning
        
        # 結果画面へ遷移
        self.end_game_watch()
    
    def _finish_game_watch(self):
        """試合観戦を終了"""
        state = self.game_watch_state
        state['game_finished'] = True
        
        # game_simulatorに結果を反映
        self.game_simulator.home_score = state['home_score']
        self.game_simulator.away_score = state['away_score']
        self.game_simulator.inning = state['inning']
    
    def end_game_watch(self):
        """観戦終了、結果画面へ遷移"""
        state = self.game_watch_state
        
        # 試合が終わっていなければ残りをシミュレート
        if not state['game_finished']:
            # 残りを高速シミュレート
            for _ in range(500):
                if state['game_finished']:
                    break
                self.advance_game_watch()
        
        # 試合結果を記録
        next_game = state['next_game']
        self.schedule_manager.complete_game(next_game, state['home_score'], state['away_score'])
        
        # チームの勝敗を更新（重要：これがないと順位に反映されない）
        is_home = state['is_home']
        player_team = self.state_manager.player_team
        opponent = self.state_manager.current_opponent
        
        if is_home:
            if state['home_score'] > state['away_score']:
                player_team.wins += 1
                opponent.losses += 1
            elif state['home_score'] < state['away_score']:
                player_team.losses += 1
                opponent.wins += 1
            else:
                player_team.draws = getattr(player_team, 'draws', 0) + 1
                opponent.draws = getattr(opponent, 'draws', 0) + 1
        else:
            if state['away_score'] > state['home_score']:
                player_team.wins += 1
                opponent.losses += 1
            elif state['away_score'] < state['home_score']:
                player_team.losses += 1
                opponent.wins += 1
            else:
                player_team.draws = getattr(player_team, 'draws', 0) + 1
                opponent.draws = getattr(opponent, 'draws', 0) + 1
        
        # 育成メニューによる経験値付与（試合ごとに実行）
        self._apply_training_after_game()
        
        # ニュースに追加
        if is_home:
            opponent_name = self.state_manager.current_opponent.name
            if state['home_score'] > state['away_score']:
                self.add_news(f"vs {opponent_name} {state['home_score']}-{state['away_score']} 勝利！")
            elif state['home_score'] < state['away_score']:
                self.add_news(f"vs {opponent_name} {state['home_score']}-{state['away_score']} 敗戦")
            else:
                self.add_news(f"vs {opponent_name} {state['home_score']}-{state['away_score']} 引き分け")
        else:
            opponent_name = self.state_manager.current_opponent.name
            if state['away_score'] > state['home_score']:
                self.add_news(f"@ {opponent_name} {state['away_score']}-{state['home_score']} 勝利！")
            elif state['away_score'] < state['home_score']:
                self.add_news(f"@ {opponent_name} {state['away_score']}-{state['home_score']} 敗戦")
            else:
                self.add_news(f"@ {opponent_name} {state['away_score']}-{state['home_score']} 引き分け")
        
        self.has_unsaved_changes = True
        self.state_manager.change_state(GameState.RESULT)
    
    def generate_draft_prospects(self):
        """NPB式ドラフト候補を生成"""
        self.state_manager.draft_prospects = []
        
        # ドラフト状態を初期化
        self.draft_round = 1  # 現在の指名順位（1巡目、2巡目...）
        self.max_draft_rounds = 8  # 最大8巡
        self.draft_picks = {}  # チーム名 -> 獲得選手リスト
        self.draft_order = []  # 指名順（ウェーバー方式）
        self.draft_lottery_results = {}  # 1巡目のくじ引き結果
        self.draft_waiting_for_other_teams = False  # 他チームの指名待ち
        self.current_picking_team_idx = 0  # 現在指名中のチームインデックス
        self.draft_messages = []  # ドラフト中のメッセージログ
        
        # 投手候補（40人）
        for i in range(40):
            pitch_type = random.choice([PitchType.STARTER, PitchType.RELIEVER, PitchType.CLOSER])
            potential = random.choices([9, 8, 7, 6, 5, 4], weights=[2, 5, 10, 20, 30, 33])[0]
            prospect = create_draft_prospect(Position.PITCHER, pitch_type, potential)
            self.state_manager.draft_prospects.append(prospect)
        
        # 野手候補（60人）
        positions = [Position.CATCHER, Position.FIRST, Position.SECOND, Position.THIRD,
                    Position.SHORTSTOP, Position.OUTFIELD, Position.OUTFIELD]
        for i in range(60):
            position = random.choice(positions)
            potential = random.choices([9, 8, 7, 6, 5, 4], weights=[2, 5, 10, 20, 30, 33])[0]
            prospect = create_draft_prospect(position, None, potential)
            self.state_manager.draft_prospects.append(prospect)
        
        # ポテンシャル順にソート
        self.state_manager.draft_prospects.sort(key=lambda p: p.potential, reverse=True)
        
        # 指名順を設定（前シーズン下位チームから）
        all_teams = self.state_manager.all_teams[:]
        all_teams.sort(key=lambda t: t.winning_percentage)  # 勝率低い順
        self.draft_order = [t.name for t in all_teams]
        
        # 各チームの指名リストを初期化
        for team in self.state_manager.all_teams:
            self.draft_picks[team.name] = []
        
        # プレイヤーチームの指名順を探す
        player_team_name = self.state_manager.player_team.name
        self.player_draft_order_idx = self.draft_order.index(player_team_name)
        
        # プレイヤーの番までCPUチームが指名
        self._process_cpu_draft_picks()
    
    def _process_cpu_draft_picks(self):
        """CPUチームのドラフト指名を処理"""
        if not self.state_manager.draft_prospects:
            return
        
        player_team_name = self.state_manager.player_team.name
        
        # 現在の巡でプレイヤーの番が来るまでCPUが指名
        while True:
            if self.draft_round > self.max_draft_rounds:
                break
            
            current_team_name = self.draft_order[self.current_picking_team_idx]
            
            # プレイヤーチームの番が来たら終了
            if current_team_name == player_team_name:
                break
            
            # CPUチームが指名
            cpu_team = next((t for t in self.state_manager.all_teams if t.name == current_team_name), None)
            if cpu_team:
                self._cpu_draft_pick(cpu_team)
            
            # 次のチームへ
            self._advance_draft_turn()
    
    def _cpu_draft_pick(self, team):
        """CPUチームがドラフト指名"""
        if not self.state_manager.draft_prospects:
            return
        
        # チーム状況に応じて候補を選ぶ
        pitchers = [p for p in team.players if p.position == Position.PITCHER]
        catchers = [p for p in team.players if p.position == Position.CATCHER]
        
        need_pitcher = len(pitchers) < 15
        need_catcher = len(catchers) < 3
        
        best_prospect = None
        
        # 優先順位: ポテンシャルトップ10 → ポジション補強 → ベスト残り
        top_prospects = self.state_manager.draft_prospects[:10]
        
        if self.draft_round <= 2:
            # 上位巡は基本的にベスト候補
            best_prospect = self.state_manager.draft_prospects[0]
        else:
            # 下位巡はチーム状況考慮
            if need_pitcher:
                pitcher_prospects = [p for p in self.state_manager.draft_prospects if p.position == Position.PITCHER]
                if pitcher_prospects:
                    best_prospect = max(pitcher_prospects, key=lambda p: p.potential)
            elif need_catcher:
                catcher_prospects = [p for p in self.state_manager.draft_prospects if p.position == Position.CATCHER]
                if catcher_prospects:
                    best_prospect = max(catcher_prospects, key=lambda p: p.potential)
            
            if not best_prospect:
                best_prospect = self.state_manager.draft_prospects[0]
        
        # 指名完了
        self._complete_draft_pick_for_team(best_prospect, team)
        
        # メッセージ記録
        msg = f"【{self.draft_round}巡目】{team.name}: {best_prospect.name} ({best_prospect.position.value})"
        self.draft_messages.append(msg)
    
    def _advance_draft_turn(self):
        """ドラフト指名順を進める"""
        self.current_picking_team_idx += 1
        
        # 全チーム指名完了 → 次巡へ
        if self.current_picking_team_idx >= len(self.draft_order):
            self.draft_round += 1
            self.current_picking_team_idx = 0
            
            # 偶数巡は逆順（ウェーバー方式）
            if self.draft_round % 2 == 0:
                self.draft_order = self.draft_order[::-1]
    
    def draft_player(self):
        """NPB式ドラフト指名（1巡目はくじ引き対応）"""
        if self.state_manager.selected_draft_pick is None or self.state_manager.selected_draft_pick < 0:
            ToastManager.show("選手を選択してください", "warning")
            return
        
        if self.state_manager.selected_draft_pick >= len(self.state_manager.draft_prospects):
            return
        
        prospect = self.state_manager.draft_prospects[self.state_manager.selected_draft_pick]
        team = self.state_manager.player_team
        
        # 1巡目は競合の可能性（他チームも指名するか判定）
        if self.draft_round == 1:
            # 上位候補は競合しやすい
            competing_teams = []
            for other_team in self.state_manager.all_teams:
                if other_team.name == team.name:
                    continue
                # ポテンシャル高い選手は競合率高い
                compete_chance = prospect.potential * 8  # 最大72%
                if random.randint(1, 100) <= compete_chance:
                    competing_teams.append(other_team.name)
            
            if competing_teams:
                # くじ引き
                all_bidders = [team.name] + competing_teams
                winner = random.choice(all_bidders)
                
                if winner == team.name:
                    ToastManager.show(f"{len(competing_teams)}球団競合を制しました", "success")
                    self._complete_draft_pick(prospect, team)
                    msg = f"【{self.draft_round}巡目】{team.name}: {prospect.name} ({len(competing_teams)}球団競合制す)"
                else:
                    ToastManager.show(f"{len(competing_teams)}球団競合、{winner}が獲得", "warning")
                    # 他チームが獲得
                    winner_team = next((t for t in self.state_manager.all_teams if t.name == winner), None)
                    if winner_team:
                        self._complete_draft_pick_for_team(prospect, winner_team)
                    msg = f"【{self.draft_round}巡目】{winner}: {prospect.name} (競合制す)"
                    # プレイヤーは再選択が必要
                    self.draft_messages.append(msg)
                    ToastManager.show("再度指名してください", "info")
                    self.state_manager.selected_draft_pick = None
                    return
            else:
                # 単独指名
                self._complete_draft_pick(prospect, team)
                msg = f"【{self.draft_round}巡目】{team.name}: {prospect.name} ({prospect.position.value})"
        else:
            # 2巡目以降は単独指名
            self._complete_draft_pick(prospect, team)
            msg = f"【{self.draft_round}巡目】{team.name}: {prospect.name} ({prospect.position.value})"
        
        self.draft_messages.append(msg)
        self.state_manager.selected_draft_pick = None
        
        # 指名順を進める
        self._advance_draft_turn()
        
        # ドラフト終了判定
        if self.draft_round > self.max_draft_rounds or not self.state_manager.draft_prospects:
            self._finish_draft()
            return
        
        # 次のプレイヤーの番までCPU処理
        self._process_cpu_draft_picks()
        
        # ドラフト終了判定（CPU処理後）
        if self.draft_round > self.max_draft_rounds or not self.state_manager.draft_prospects:
            self._finish_draft()
    
    def _finish_draft(self):
        """ドラフト終了処理 → 育成ドラフトへ"""
        # プレイヤーチームの獲得選手を表示
        acquired = self.draft_picks.get(self.state_manager.player_team.name, [])
        if acquired:
            ToastManager.show(f"支配下ドラフト終了！ {len(acquired)}選手を獲得", "success")
        
        # 育成ドラフト候補を生成
        self.generate_developmental_prospects()
        self.state_manager.change_state(GameState.DEVELOPMENTAL_DRAFT)
    
    def generate_developmental_prospects(self):
        """育成ドラフト候補を生成"""
        self.developmental_prospects = []
        self.developmental_draft_round = 1
        self.developmental_draft_messages = []
        self.selected_developmental_idx = -1
        
        # 育成候補は支配下より能力は低いがポテンシャル高い選手も
        # 投手候補（30人）
        for i in range(30):
            pitch_type = random.choice([PitchType.STARTER, PitchType.RELIEVER, PitchType.CLOSER])
            # 育成はポテンシャル低めの選手が多い
            potential = random.choices([7, 6, 5, 4, 3, 2], weights=[5, 10, 20, 30, 25, 10])[0]
            prospect = create_draft_prospect(Position.PITCHER, pitch_type, potential)
            prospect.is_developmental = True
            self.developmental_prospects.append(prospect)
        
        # 野手候補（40人）
        positions = [Position.CATCHER, Position.FIRST, Position.SECOND, Position.THIRD,
                    Position.SHORTSTOP, Position.OUTFIELD, Position.OUTFIELD]
        for i in range(40):
            position = random.choice(positions)
            potential = random.choices([7, 6, 5, 4, 3, 2], weights=[5, 10, 20, 30, 25, 10])[0]
            prospect = create_draft_prospect(position, None, potential)
            prospect.is_developmental = True
            self.developmental_prospects.append(prospect)
        
        # ポテンシャル順にソート
        self.developmental_prospects.sort(key=lambda p: p.potential, reverse=True)
    
    def draft_developmental_player(self):
        """育成ドラフト指名"""
        if self.selected_developmental_idx < 0 or self.selected_developmental_idx >= len(self.developmental_prospects):
            ToastManager.show("選手を選択してください", "warning")
            return
        
        prospect = self.developmental_prospects[self.selected_developmental_idx]
        team = self.state_manager.player_team
        
        # 育成選手として登録
        player = Player(
            name=prospect.name,
            position=prospect.position,
            pitch_type=prospect.pitch_type,
            stats=prospect.stats,
            age=prospect.age,
            status=PlayerStatus.FARM,
            uniform_number=0,
            is_developmental=True,
            draft_round=100 + self.developmental_draft_round  # 育成は100+
        )
        
        # 背番号（育成は3桁）
        used_numbers = [p.uniform_number for p in team.players]
        for num in range(101, 200):
            if num not in used_numbers:
                player.uniform_number = num
                break
        
        team.players.append(player)
        
        # メッセージ
        msg = f"【育成{self.developmental_draft_round}位】{team.name}: {prospect.name}"
        self.developmental_draft_messages.append(msg)
        ToastManager.show(f" 育成{self.developmental_draft_round}位 {prospect.name} を獲得！", "success")
        
        # リストから削除
        self.developmental_prospects.pop(self.selected_developmental_idx)
        self.selected_developmental_idx = -1
        self.developmental_draft_round += 1
        
        # 最大5人まで
        if self.developmental_draft_round > 5 or not self.developmental_prospects:
            self._finish_developmental_draft()
    
    def _finish_developmental_draft(self):
        """育成ドラフト終了処理"""
        dev_count = len([p for p in self.state_manager.player_team.players if p.is_developmental and p.draft_round >= 100])
        ToastManager.show(f"育成ドラフト終了！", "success")
        
        # 外国人FA画面へ
        self.generate_foreign_free_agents()
        self.state_manager.change_state(GameState.FREE_AGENT)
    
    def _complete_draft_pick(self, prospect, team):
        """ドラフト指名完了（プレイヤーチーム）"""
        self._complete_draft_pick_for_team(prospect, team)
        ToastManager.show(f"{prospect.name} を獲得", "success")
    
    def _complete_draft_pick_for_team(self, prospect, team):
        """ドラフト指名完了（任意チーム）"""
        player = Player(
            name=prospect.name,
            position=prospect.position,
            pitch_type=prospect.pitch_type,
            stats=prospect.stats,
            age=prospect.age,
            status=PlayerStatus.ACTIVE,
            uniform_number=0,
            draft_round=self.draft_round
        )
        
        # 空き背番号を探す
        used_numbers = [p.uniform_number for p in team.players]
        for num in range(1, 100):
            if num not in used_numbers:
                player.uniform_number = num
                break
        
        team.players.append(player)
        
        # ドラフトリストから削除
        if prospect in self.state_manager.draft_prospects:
            self.state_manager.draft_prospects.remove(prospect)
        
        # 指名記録
        if hasattr(self, 'draft_picks'):
            self.draft_picks[team.name].append(prospect.name)
    
    def generate_foreign_free_agents(self):
        """外国人FA選手を生成"""
        self.state_manager.foreign_free_agents = []
        self.selected_fa_idx = -1  # FA選択リセット
        
        for _ in range(5):
            pitch_type = random.choice([PitchType.STARTER, PitchType.RELIEVER, PitchType.CLOSER])
            player = create_foreign_free_agent(Position.PITCHER, pitch_type)
            self.state_manager.foreign_free_agents.append(player)
        
        positions = [Position.FIRST, Position.THIRD, Position.OUTFIELD]
        for _ in range(5):
            position = random.choice(positions)
            player = create_foreign_free_agent(position)
            self.state_manager.foreign_free_agents.append(player)
    
    def handle_events(self):
        """イベント処理"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            # ウィンドウリサイズ
            if event.type == pygame.VIDEORESIZE:
                if not settings.fullscreen:
                    self.screen = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
                    set_screen_size(event.w, event.h)
                    self.renderer.screen = self.screen
            
            # キー入力
            if event.type == pygame.KEYDOWN:
                # チーム名編集中のテキスト入力
                if self.state_manager.current_state == GameState.TEAM_EDIT and self.editing_team_idx >= 0:
                    if event.key == pygame.K_BACKSPACE:
                        self.team_name_input = self.team_name_input[:-1]
                    elif event.key == pygame.K_RETURN:
                        self._confirm_team_name_edit()
                    elif event.key == pygame.K_ESCAPE:
                        self._cancel_team_name_edit()
                    elif event.unicode and len(self.team_name_input) < 20:
                        self.team_name_input += event.unicode
                    continue  # テキスト入力中は他のキー処理をスキップ
                
                # チーム作成画面でのテキスト入力
                if self.state_manager.current_state == GameState.TEAM_CREATE:
                    if event.key == pygame.K_BACKSPACE:
                        self.new_team_name = self.new_team_name[:-1]
                    elif event.key == pygame.K_RETURN:
                        self._create_new_team()
                    elif event.key == pygame.K_ESCAPE:
                        self.state_manager.change_state(GameState.TEAM_SELECT)
                    elif event.unicode and len(self.new_team_name) < 20:
                        self.new_team_name += event.unicode
                    continue  # テキスト入力中は他のキー処理をスキップ
                
                if event.key == pygame.K_F11:
                    settings.toggle_fullscreen()
                    if settings.fullscreen:
                        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                        actual_size = self.screen.get_size()
                        set_screen_size(actual_size[0], actual_size[1])
                    else:
                        width, height = settings.get_resolution()
                        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
                    self.renderer.screen = self.screen
                
                if event.key == pygame.K_ESCAPE:
                    if self.state_manager.current_state != GameState.TITLE:
                        self.state_manager.change_state(GameState.MENU)
                
                # スクロール
                if self.state_manager.current_state in [GameState.LINEUP, GameState.SCHEDULE_VIEW, GameState.DRAFT]:
                    if event.key == pygame.K_UP:
                        self.scroll_offset = max(0, self.scroll_offset - 1)
                    elif event.key == pygame.K_DOWN:
                        self.scroll_offset += 1
                
                # 選手詳細画面でのスクロール
                if self.state_manager.current_state == GameState.PLAYER_DETAIL:
                    if event.key == pygame.K_UP:
                        self.player_detail_scroll = max(0, self.player_detail_scroll - 30)
                    elif event.key == pygame.K_DOWN:
                        self.player_detail_scroll += 30
                    elif event.key == pygame.K_ESCAPE:
                        # 前の画面に戻る
                        self.selected_detail_player = None
                        self.player_detail_scroll = 0
                        self.state_manager.change_state(GameState.LINEUP)
                
                # 采配モードでのスペースキー（次の球）
                if self.state_manager.current_state == GameState.GAME_MANAGE:
                    game_manage_state = getattr(self, 'game_manage_state', {})
                    if event.key == pygame.K_SPACE:
                        if not game_manage_state.get('waiting_for_tactic') or not game_manage_state.get('player_is_batting'):
                            self.advance_game_manage()
                    elif event.key == pygame.K_1:
                        self.set_manage_tactic('normal')
                    elif event.key == pygame.K_2:
                        self.set_manage_tactic('power_swing')
                    elif event.key == pygame.K_3:
                        self.set_manage_tactic('contact_swing')
                    elif event.key == pygame.K_4:
                        self.set_manage_tactic('take')
                    elif event.key == pygame.K_5:
                        self.set_manage_tactic('bunt')
                    elif event.key == pygame.K_6:
                        self.set_manage_tactic('squeeze')
                    elif event.key == pygame.K_7:
                        self.set_manage_tactic('hit_and_run')
                    elif event.key == pygame.K_8:
                        self.set_manage_tactic('steal')
            
            # マウスホイール
            if event.type == pygame.MOUSEWHEEL:
                current_state = self.state_manager.current_state
                mouse_pos = pygame.mouse.get_pos()
                
                # 観戦/采配画面でのズーム
                if current_state in [GameState.GAME_WATCH, GameState.GAME_MANAGE]:
                    self.renderer.cyber_field.handle_scroll(event.y)
                    continue  # 他のスクロール処理をスキップ
                
                # 各画面ごとのスクロール処理（上限・下限を設定）
                if current_state == GameState.LINEUP:
                    # オーダー画面：二軍選手リストのマウスホイールスクロール
                    # 現在のタブによって有効なリストを判断
                    order_sub_tab = getattr(self, 'order_sub_tab', 'batter')
                    
                    if order_sub_tab == 'batter':
                        second_batter_rect = getattr(self.renderer, '_second_batter_list_rect', None)
                        if second_batter_rect and second_batter_rect.collidepoint(mouse_pos):
                            # 二軍野手リスト上でのスクロール
                            current = getattr(self.renderer, '_second_batter_scroll', 0)
                            max_scroll = getattr(self.renderer, '_second_batter_max_scroll', None)
                            if max_scroll is None:
                                # fallback: estimate visible rows from screen height and approximate row height
                                sw, sh = self.screen.get_size()
                                fallback_height = max(100, sh - 260)
                                row_h = 34
                                visible = max(4, (fallback_height - 120) // row_h)
                                if self.state_manager.player_team:
                                    try:
                                        count = len(self.state_manager.player_team.get_second_team_batters())
                                    except Exception:
                                        count = 0
                                else:
                                    count = 0
                                max_scroll = max(0, count - visible)
                            self.renderer._second_batter_scroll = max(0, min(max_scroll, current - event.y))
                        else:
                            # 通常のスクロール
                            self.scroll_offset = max(0, self.scroll_offset - event.y)
                    elif order_sub_tab == 'pitcher':
                        # Try to use renderer-provided list rect; fall back to a reasonable area if missing
                        second_pitcher_rect = getattr(self.renderer, '_second_pitcher_list_rect', None)
                        if not second_pitcher_rect:
                            # approximate right-half list area as fallback using same layout math as screens.py
                            sw, sh = self.screen.get_size()
                            left_half = (sw - 50) // 2
                            right_x = 20 + left_half + 10
                            right_w = left_half
                            # content vertical position approximated similarly to screens (content_y + 5)
                            fallback_y = 140
                            fallback_h = max(100, sh - 260)
                            second_pitcher_rect = pygame.Rect(right_x, fallback_y, right_w, fallback_h)

                        # If mouse is on the left half (starter/relief/closer area), do not treat as second-team list
                        if second_pitcher_rect:
                            try:
                                mouse_x = mouse_pos[0]
                                if mouse_x < second_pitcher_rect.x:
                                    # cursor is over left side slots; fall back to normal scroll
                                    self.scroll_offset = max(0, self.scroll_offset - event.y)
                                    continue
                            except Exception:
                                pass

                        if second_pitcher_rect and second_pitcher_rect.collidepoint(mouse_pos):
                            # 二軍投手リスト上でのスクロール
                            current = getattr(self.renderer, '_second_pitcher_scroll', 0)
                            max_scroll = getattr(self.renderer, '_second_pitcher_max_scroll', None)
                            if max_scroll is None:
                                # compute fallback visible rows from fallback rect height and row size
                                fh = second_pitcher_rect.height
                                row_h = 32
                                visible = max(4, (fh - 120) // row_h)
                                if self.state_manager.player_team:
                                    try:
                                        count = len(self.state_manager.player_team.get_second_team_pitchers())
                                    except Exception:
                                        count = 0
                                else:
                                    count = 0
                                max_scroll = max(0, count - visible)
                            # ensure current is numeric and clamp properly
                            try:
                                new_scroll = max(0, min(max_scroll, current - event.y))
                            except Exception:
                                new_scroll = max(0, current - event.y)
                            self.renderer._second_pitcher_scroll = new_scroll
                        else:
                            # 通常のスクロール
                            self.scroll_offset = max(0, self.scroll_offset - event.y)
                    else:
                        # 通常のスクロール
                        if self.state_manager.player_team:
                            if self.lineup_tab == "pitchers":
                                players = self.state_manager.player_team.get_active_pitchers()
                            elif self.lineup_tab == "batters":
                                players = self.state_manager.player_team.get_active_batters()
                            else:
                                players = [p for p in self.state_manager.player_team.players if not getattr(p, 'is_developmental', False)]
                            visible_count = 12  # 表示可能な行数
                            max_scroll = max(0, len(players) - visible_count)
                            self.scroll_offset = max(0, min(max_scroll, self.scroll_offset - event.y))
                        else:
                            self.scroll_offset = max(0, self.scroll_offset - event.y)
                elif current_state == GameState.SCHEDULE_VIEW:
                    # スケジュール画面：試合数に基づく上限
                    if self.schedule_manager and self.state_manager.player_team:
                        games = self.schedule_manager.get_team_schedule(self.state_manager.player_team.name)
                        max_scroll = max(0, len(games) - 10)
                        self.scroll_offset = max(0, min(max_scroll, self.scroll_offset - event.y * 3))
                    else:
                        self.scroll_offset = max(0, self.scroll_offset - event.y * 3)
                elif current_state == GameState.DRAFT:
                    max_scroll = max(0, len(self.state_manager.draft_prospects) - 12)
                    self.draft_scroll = max(0, min(max_scroll, self.draft_scroll - event.y))
                elif current_state in [GameState.IKUSEI_DRAFT, GameState.DEVELOPMENTAL_DRAFT]:
                    max_scroll = max(0, len(getattr(self, 'developmental_prospects', [])) - 12)
                    self.ikusei_draft_scroll = getattr(self, 'ikusei_draft_scroll', 0)
                    self.ikusei_draft_scroll = max(0, min(max_scroll, self.ikusei_draft_scroll - event.y))
                elif current_state == GameState.FREE_AGENT:
                    # FA画面：外国人FA選手数に基づく上限
                    fa_count = len(self.state_manager.foreign_free_agents) if self.state_manager.foreign_free_agents else 0
                    max_scroll = max(0, (fa_count - 8) * 30)
                    self.fa_scroll = max(0, min(max_scroll, self.fa_scroll - event.y * 30))
                elif current_state == GameState.STANDINGS:
                    # 記録画面：コンテンツの高さに基づいて動的計算
                    screen_height = self.screen.get_height()
                    content_height = 800  # 記録画面のおおよそのコンテンツ高さ
                    max_scroll = max(0, content_height - screen_height + 150)
                    self.standings_scroll = max(0, min(max_scroll, self.standings_scroll - event.y * 30))
                elif current_state == GameState.RESULT:
                    # 試合結果画面のスクロール（投手/打者成績）
                    self.result_scroll = max(0, self.result_scroll - event.y * 2)
                elif current_state == GameState.PLAYER_DETAIL:
                    # 選手詳細画面：コンテンツの高さに基づいて動的計算
                    screen_height = self.screen.get_height()
                    content_height = 650  # 選手詳細のおおよそのコンテンツ高さ
                    max_scroll = max(0, content_height - screen_height + 200)
                    self.player_detail_scroll = max(0, min(max_scroll, self.player_detail_scroll - event.y * 30))
                elif current_state == GameState.TEAM_SELECT:
                    # チーム選択画面のプレビュースクロール：選手リストの長さに基づく
                    screen_height = self.screen.get_height()
                    preview_name = getattr(self, 'preview_team_name', None)
                    all_teams = getattr(self.state_manager, 'all_teams', []) or []
                    preview_team = None
                    if preview_name:
                        for t in all_teams:
                            if t.name == preview_name:
                                preview_team = t
                                break
                    if preview_team:
                        # Match the renderer's layout sizes used in screens.py
                        # sections: analysis (100) + top batters (160) + top pitchers (160) + stadium (90)
                        total_content_height = 100 + 160 + 160 + 90
                        # visible area inside the preview panel in screens.py uses panel_height - 165
                        # panel_height = screen_height - header_h - 50; header_h is ~120 in the renderer
                        header_h_est = 120
                        panel_height = max(200, self.screen.get_height() - header_h_est - 50)
                        visible_height = max(100, panel_height - 165)
                        max_scroll = max(0, total_content_height - visible_height)
                    else:
                        max_scroll = 0
                    # ensure attribute exists and is in pixel units
                    self.team_preview_scroll = getattr(self, 'team_preview_scroll', 0)
                    self.team_preview_scroll = max(0, min(max_scroll, self.team_preview_scroll - event.y * 30))
                elif current_state == GameState.SETTINGS:
                    # 設定画面のスクロール（ゲームルールタブのみ）
                    if self.settings_tab == "game_rules":
                        screen_height = self.screen.get_height()
                        content_height = 700  # ゲームルール設定のおおよそのコンテンツ高さ
                        max_scroll = max(0, content_height - screen_height + 200)
                        self.settings_scroll = max(0, min(max_scroll, self.settings_scroll - event.y * 30))
                elif current_state == GameState.PENNANT_CAMP:
                    # 春季キャンプ画面の選手リストスクロール
                    max_scroll = getattr(self.renderer, '_spring_camp_max_scroll', 0)
                    self.spring_player_scroll = getattr(self, 'spring_player_scroll', 0)
                    self.spring_player_scroll = max(0, min(max_scroll, self.spring_player_scroll - event.y))
                elif current_state == GameState.TRAINING:
                    # 育成画面の選手リストスクロール
                    max_scroll = getattr(self.renderer, '_training_max_scroll', 0)
                    current = getattr(self, 'training_player_scroll', 0)
                    try:
                        new_scroll = max(0, min(max_scroll, current - event.y))
                    except Exception:
                        new_scroll = max(0, current - event.y)
                    self.training_player_scroll = new_scroll
                elif current_state == GameState.PENNANT_FALL_CAMP:
                    # 秋季キャンプ画面の選手リストスクロール
                    max_scroll = getattr(self.renderer, '_fall_camp_max_scroll', 0)
                    self.fall_player_scroll = getattr(self, 'fall_player_scroll', 0)
                    self.fall_player_scroll = max(0, min(max_scroll, self.fall_player_scroll - event.y))
                elif current_state == GameState.ROSTER_MANAGEMENT:
                    # 登録管理画面のスクロール - マウス位置に応じて個別パネルをスクロール
                    roster_tab = getattr(self, 'roster_tab', 'order')
                    mouse_x = pygame.mouse.get_pos()[0]
                    screen_width = self.screen.get_width()
                    
                    if roster_tab == 'farm':
                        # 軍入れ替えタブ: 3列の個別スクロール
                        col_width = (screen_width - 80) // 3
                        if mouse_x < 30 + col_width:
                            # 一軍パネル
                            self.farm_scroll_first = max(0, self.farm_scroll_first - event.y)
                        elif mouse_x < 30 + col_width * 2 + 10:
                            # 二軍パネル
                            self.farm_scroll_second = max(0, self.farm_scroll_second - event.y)
                        else:
                            # 三軍パネル
                            self.farm_scroll_third = max(0, self.farm_scroll_third - event.y)
                    elif roster_tab == 'order':
                        # オーダータブ: サブタブに応じてスクロール
                        order_sub_tab = getattr(self, 'order_sub_tab', 'batter')
                        if order_sub_tab == 'pitcher':
                            # 投手オーダー: 二軍投手リストのスクロール
                            second_pitcher_rect = getattr(self.renderer, '_second_pitcher_list_rect', None)
                            if not second_pitcher_rect:
                                sw, sh = self.screen.get_size()
                                left_half = (sw - 50) // 2
                                right_x = 20 + left_half + 10
                                right_w = left_half
                                fallback_y = 140
                                fallback_h = max(100, sh - 260)
                                second_pitcher_rect = pygame.Rect(right_x, fallback_y, right_w, fallback_h)

                            # If mouse is on the left half (starter/relief/closer area), do not scroll second-team list
                            if second_pitcher_rect and mouse_pos[0] < second_pitcher_rect.x:
                                # cursor is over left side slots; do not scroll
                                pass
                            elif second_pitcher_rect and second_pitcher_rect.collidepoint(mouse_pos):
                                current = getattr(self.renderer, '_second_pitcher_scroll', 0)
                                max_scroll = getattr(self.renderer, '_second_pitcher_max_scroll', None)
                                if max_scroll is None:
                                    fh = second_pitcher_rect.height
                                    row_h = 32
                                    visible = max(4, (fh - 120) // row_h)
                                    if self.state_manager.player_team:
                                        try:
                                            count = len(self.state_manager.player_team.get_second_team_pitchers())
                                        except Exception:
                                            count = 0
                                    else:
                                        count = 0
                                    max_scroll = max(0, count - visible)
                                self.renderer._second_pitcher_scroll = max(0, min(max_scroll, current - event.y))
                            else:
                                self.pitcher_scroll = max(0, self.pitcher_scroll - event.y)
                        else:
                            # 野手オーダー: 二軍野手リストのスクロール
                            second_batter_rect = getattr(self.renderer, '_second_batter_list_rect', None)
                            if second_batter_rect and second_batter_rect.collidepoint(mouse_pos):
                                current = getattr(self.renderer, '_second_batter_scroll', 0)
                                max_scroll = getattr(self.renderer, '_second_batter_max_scroll', 0)
                                self.renderer._second_batter_scroll = max(0, min(max_scroll, current - event.y))
                            else:
                                self.order_scroll_batters = max(0, self.order_scroll_batters - event.y)
                    else:
                        # その他のタブ
                        self.scroll_offset = max(0, self.scroll_offset - event.y)
            
            # マウスクリック
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                
                # 観戦/采配画面での視点ドラッグ開始
                if self.state_manager.current_state in [GameState.GAME_WATCH, GameState.GAME_MANAGE]:
                    self._camera_drag_start = mouse_pos
                    self._camera_dragging = True
                    self._camera_drag_button = 1  # 左ボタン
                
                # オーダー画面でのドラッグ開始または選手詳細表示
                if self.state_manager.current_state in [GameState.LINEUP, GameState.ROSTER_MANAGEMENT]:
                    # 編集モードに応じた処理
                    if self.lineup_edit_mode == "position":
                        # ポジション編集モード：守備位置の入れ替え
                        if not self.handle_position_click(mouse_pos):
                            # ポジションボタンをクリックしていなければ通常処理
                            self.handle_lineup_drag_start(mouse_pos)
                    elif self.lineup_edit_mode == "batting_order":
                        # 打順編集モード：打順の入れ替え
                        if not self.handle_batting_order_swap(mouse_pos):
                            self.handle_lineup_drag_start(mouse_pos)
                    else:
                        # 選手編集モード（デフォルト）
                        self.handle_lineup_drag_start(mouse_pos)
                
                # ドラフト画面での選手選択
                if self.state_manager.current_state == GameState.DRAFT:
                    self.handle_draft_click(mouse_pos)
                
                # 育成ドラフト画面での選手選択
                if self.state_manager.current_state in [GameState.IKUSEI_DRAFT, GameState.DEVELOPMENTAL_DRAFT]:
                    self.handle_ikusei_draft_click(mouse_pos)
                
                # FA画面での選手選択
                if self.state_manager.current_state == GameState.FREE_AGENT:
                    self.handle_fa_click(mouse_pos)
                
                # チーム選択画面
                if self.state_manager.current_state == GameState.TEAM_SELECT:
                    self.handle_team_select_click(mouse_pos)
                
                # 難易度選択画面
                if self.state_manager.current_state == GameState.DIFFICULTY_SELECT:
                    self.handle_difficulty_click(mouse_pos)
            
            # ダブルクリックで選手詳細画面へ
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if hasattr(self, '_last_click_time') and hasattr(self, '_last_click_pos'):
                    import time
                    current_time = time.time()
                    if current_time - self._last_click_time < 0.3:  # 300ms以内
                        dist = ((event.pos[0] - self._last_click_pos[0])**2 + 
                               (event.pos[1] - self._last_click_pos[1])**2)**0.5
                        if dist < 20:  # 近い位置
                            self.handle_double_click(event.pos)
                self._last_click_time = time.time() if 'time' in dir() else __import__('time').time()
                self._last_click_pos = event.pos
            
            # 右クリックドラッグ（視点移動用）
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
                if self.state_manager.current_state in [GameState.GAME_WATCH, GameState.GAME_MANAGE]:
                    self._camera_drag_start = pygame.mouse.get_pos()
                    self._camera_dragging = True
                    self._camera_drag_button = 3  # 右ボタン
            
            if event.type == pygame.MOUSEBUTTONUP and event.button == 3:
                if self.state_manager.current_state in [GameState.GAME_WATCH, GameState.GAME_MANAGE]:
                    self._camera_dragging = False
            
            # マウスドラッグ（移動）
            if event.type == pygame.MOUSEMOTION:
                # 観戦/采配画面での視点ドラッグ
                if self.state_manager.current_state in [GameState.GAME_WATCH, GameState.GAME_MANAGE]:
                    if getattr(self, '_camera_dragging', False) and hasattr(self, '_camera_drag_start'):
                        current_pos = pygame.mouse.get_pos()
                        dx = current_pos[0] - self._camera_drag_start[0]
                        dy = current_pos[1] - self._camera_drag_start[1]
                        # 保存されたボタン状態を使用
                        drag_button = getattr(self, '_camera_drag_button', 1)
                        self.renderer.cyber_field.handle_drag(dx, dy, drag_button)
                        self._camera_drag_start = current_pos
                
                if self.dragging_player_idx >= 0:
                    self.drag_pos = pygame.mouse.get_pos()
                if self.dragging_position_slot >= 0:
                    self.position_drag_pos = pygame.mouse.get_pos()
            
            # マウスリリース（ドロップ）
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                # 観戦/采配画面での視点ドラッグ終了
                if self.state_manager.current_state in [GameState.GAME_WATCH, GameState.GAME_MANAGE]:
                    self._camera_dragging = False
                
                if self.dragging_player_idx >= 0:
                    self.handle_lineup_drop(pygame.mouse.get_pos())
                if self.dragging_position_slot >= 0:
                    self.handle_position_drop(pygame.mouse.get_pos())
            
            # ボタンイベント
            for button_name, button in self.buttons.items():
                # Buttonオブジェクトの場合のみ処理（Rectなどは無視）
                if hasattr(button, 'handle_event') and button.handle_event(event):
                    self.handle_button_click(button_name)
        
        return True
    
    def _load_team_name_presets(self):
        """チーム名プリセットをファイルから読み込み"""
        import json
        import os
        preset_path = os.path.join(os.path.dirname(__file__), "team_name_presets.json")
        try:
            if os.path.exists(preset_path):
                with open(preset_path, 'r', encoding='utf-8') as f:
                    self.custom_team_names = json.load(f)
        except Exception as e:
            print(f"チーム名プリセット読み込みエラー: {e}")
            self.custom_team_names = {}
    
    def _save_team_name_presets(self):
        """チーム名プリセットをファイルに保存"""
        import json
        import os
        preset_path = os.path.join(os.path.dirname(__file__), "team_name_presets.json")
        try:
            with open(preset_path, 'w', encoding='utf-8') as f:
                json.dump(self.custom_team_names, f, ensure_ascii=False, indent=2)
            ToastManager.show("チーム名プリセットを保存しました", "success")
        except Exception as e:
            print(f"チーム名プリセット保存エラー: {e}")
            ToastManager.show("プリセット保存に失敗しました", "error")
    
    def _confirm_team_name_edit(self):
        """チーム名編集を確定"""
        if self.editing_team_idx >= 0 and self.team_name_input.strip():
            team = self.state_manager.all_teams[self.editing_team_idx]
            self.custom_team_names[team.name] = self.team_name_input.strip()
            self._save_team_name_presets()  # プリセットを保存
            ToastManager.show(f"チーム名を変更: {self.team_name_input}", "success")
        self.editing_team_idx = -1
        self.team_name_input = ""
    
    def _cancel_team_name_edit(self):
        """チーム名編集をキャンセル"""
        self.editing_team_idx = -1
        self.team_name_input = ""
    
    def handle_draft_click(self, mouse_pos):
        """ドラフト画面のクリック処理（スクロール対応）"""
        # 選手リストの領域を計算（簡易版）
        header_h = 120
        card_y = header_h + 20 + 65  # カード上部 + ヘッダー行
        draft_scroll = getattr(self, 'draft_scroll', 0)
        
        for i in range(min(12, len(self.state_manager.draft_prospects) - draft_scroll)):
            actual_idx = i + draft_scroll
            row_y = card_y + i * 38
            row_rect = pygame.Rect(45, row_y - 5, self.screen.get_width() - 90, 34)
            
            if row_rect.collidepoint(mouse_pos):
                self.state_manager.selected_draft_pick = actual_idx
                return
    
    def handle_fa_click(self, mouse_pos):
        """FA画面のクリック処理"""
        # rendererのfa_row_rectsを使用
        if hasattr(self.renderer, 'fa_row_rects'):
            for i, rect in enumerate(self.renderer.fa_row_rects):
                if rect.collidepoint(mouse_pos):
                    self.selected_fa_idx = i
                    return
    
    def handle_double_click(self, mouse_pos):
        """ダブルクリックで選手詳細画面を開く"""
        current_state = self.state_manager.current_state
        
        if current_state == GameState.LINEUP:
            # オーダー画面の選手をクリック
            team = self.state_manager.player_team
            if team and team.players:
                # 行の高さとヘッダーからどの選手か計算
                header_h = 120
                row_h = 45
                y_offset = mouse_pos[1] - header_h - 70 + self.lineup_scroll
                if y_offset >= 0:
                    idx = int(y_offset / row_h)
                    if 0 <= idx < len(team.players):
                        self.selected_detail_player = team.players[idx]
                        self.player_detail_scroll = 0
                        self.state_manager.change_state(GameState.PLAYER_DETAIL)
                        return
        
        elif current_state == GameState.DRAFT:
            # ドラフト画面の候補選手をクリック
            if self.state_manager.draft_prospects:
                header_h = 120
                row_h = 42
                y_offset = mouse_pos[1] - header_h - 85 + self.draft_scroll
                if y_offset >= 0:
                    idx = int(y_offset / row_h)
                    if 0 <= idx < len(self.state_manager.draft_prospects):
                        prospect = self.state_manager.draft_prospects[idx]
                        # DraftProspectからPlayerを作成して表示
                        temp_player = Player(
                            name=prospect.name,
                            position=prospect.position,
                            age=prospect.age,
                            stats=prospect.potential_stats
                        )
                        self.selected_detail_player = temp_player
                        self.player_detail_scroll = 0
                        # 状態は変えずに詳細を表示（モーダル風）
                        ToastManager.show(f"{prospect.name}の詳細", "info")
                        return
    
    def handle_ikusei_draft_click(self, mouse_pos):
        """育成ドラフト画面のクリック処理（スクロール対応）"""
        header_h = 120
        row_h = 38  # draw_ikusei_draft_screenと一致
        card_y = header_h + 70 + 20 + 25 + 8  # カード開始位置 + パディング + ヘッダー + 区切り線
        ikusei_scroll = getattr(self, 'ikusei_draft_scroll', 0)
        
        for i in range(min(12, len(self.developmental_prospects) - ikusei_scroll)):
            actual_idx = i + ikusei_scroll
            row_y = card_y + i * row_h
            row_rect = pygame.Rect(40, row_y - 3, self.screen.get_width() - 400, 34)
            
            if row_rect.collidepoint(mouse_pos):
                self.selected_developmental_idx = actual_idx
                return
    
    def sign_fa_player(self):
        """外国人FA選手を獲得"""
        if self.selected_fa_idx < 0 or self.selected_fa_idx >= len(self.state_manager.foreign_free_agents):
            ToastManager.show("選手を選択してください", "warning")
            return
        
        player = self.state_manager.foreign_free_agents[self.selected_fa_idx]
        team = self.state_manager.player_team
        
        # 空き背番号を探す
        used_numbers = [p.uniform_number for p in team.players]
        for num in range(1, 100):
            if num not in used_numbers:
                player.uniform_number = num
                break
        
        # チームに追加
        team.players.append(player)
        
        # FAリストから削除
        self.state_manager.foreign_free_agents.pop(self.selected_fa_idx)
        self.selected_fa_idx = -1
        
        ToastManager.show(f"{player.name} と契約", "success")
    
    def start_new_season(self):
        """新シーズンを開始"""
        # シーズン番号を進める
        self.state_manager.current_year += 1
        
        # 全選手の年齢を+1、引退処理
        for team in self.state_manager.all_teams:
            retired_players = []
            for player in team.players:
                player.age += 1
                
                # 引退判定（38歳以上で確率）
                if player.age >= 38:
                    retire_chance = (player.age - 37) * 15  # 38歳15%, 39歳30%...
                    if random.randint(1, 100) <= retire_chance:
                        retired_players.append(player)
            
            # 引退選手を除外
            for retired in retired_players:
                if retired in team.players:
                    team.players.remove(retired)
            
            # チーム成績リセット
            team.wins = 0
            team.losses = 0
            team.draws = 0
        
        # スケジュール再生成
        self.init_schedule()
        
        # オーダーをリセット
        for team in self.state_manager.all_teams:
            team.current_lineup = []
            team.starting_pitcher_idx = -1
        
        # メニューへ
        ToastManager.show(f"{self.state_manager.current_year}年シーズン開幕", "success")
        self.state_manager.change_state(GameState.MENU)
    
    def handle_team_select_click(self, mouse_pos):
        """チーム選択画面のクリック処理"""
        # 戻るボタンを明示的にチェックして処理
        if "team_select_back" in self.buttons:
            btn = self.buttons["team_select_back"]
            if hasattr(btn, 'rect') and btn.rect.collidepoint(mouse_pos):
                # 明示的にタイトルに戻る処理
                self.preview_team_name = None
                self.team_preview_scroll = 0
                self.state_manager.change_state(GameState.TITLE)
                self.show_title_start_menu = False
                return
    
    def handle_difficulty_click(self, mouse_pos):
        """難易度選択画面のクリック処理"""
        # カードクリックで難易度選択
        header_h = 120
        card_y = header_h + 60
        card_width = 220
        card_height = 200
        total_width = card_width * 4 + 30 * 3
        start_x = (self.screen.get_width() - total_width) // 2
        
        difficulties = [DifficultyLevel.EASY, DifficultyLevel.NORMAL, DifficultyLevel.HARD, DifficultyLevel.VERY_HARD]
        
        for i, level in enumerate(difficulties):
            x = start_x + i * (card_width + 30)
            card_rect = pygame.Rect(x, card_y, card_width, card_height)
            
            if card_rect.collidepoint(mouse_pos):
                self.state_manager.difficulty = level
                ToastManager.show(f"難易度: {level.value} を選択", "info")
                return
    
    def handle_button_click(self, button_name: str):
        """ボタンクリック処理"""
        # タイトル画面
        if button_name == "start":
            # スタートメニューを表示
            self.show_title_start_menu = True
        
        elif button_name == "back_to_title":
            # スタートメニューを閉じる
            self.show_title_start_menu = False
        
        elif button_name == "new_game":
            # 新規ゲーム - まずチーム選択へ（設定はチーム選択後）
            self.show_title_start_menu = False
            self.new_game_setup_state = {"difficulty": "normal"}
            self.reset_game_state()  # ゲーム状態をリセット
            self.init_teams()  # チームを初期化
            self.state_manager.change_state(GameState.TEAM_SELECT)
            ToastManager.show("チームを選択してください！", "info")
        
        elif button_name == "load_game":
            # ロード画面へ遷移（将来実装）
            self.show_title_start_menu = False
            self.load_saved_game()
        
        elif button_name == "return_to_title":
            # セーブしていない場合は確認ダイアログを表示
            if self.has_unsaved_changes:
                self.show_confirm_dialog = True
                self.confirm_action = "return_to_title"
            else:
                self.state_manager.change_state(GameState.TITLE)
                self.show_title_start_menu = False
        
        elif button_name == "confirm_yes":
            # 確認ダイアログでYES
            self.show_confirm_dialog = False
            if self.confirm_action == "return_to_title":
                self.state_manager.change_state(GameState.TITLE)
                self.show_title_start_menu = False
                self.has_unsaved_changes = False
            elif self.confirm_action == "spring_auto_finish":
                # Auto-run remaining camp days
                from player_development import PlayerDevelopment, TrainingType
                team = self.state_manager.player_team
                all_players = team.players if team else []
                max_days = getattr(self, 'spring_camp_max_days', 30)
                cur_day = getattr(self, 'spring_camp_day', 1)
                remaining = max_days - cur_day + 1
                
                trained = 0
                stat_ups = 0
                for _ in range(remaining):
                    for player in all_players:
                        # Get player fatigue
                        fatigue = getattr(player.player_status, 'fatigue', 0) if hasattr(player, 'player_status') and player.player_status else 0
                        
                        # Pick training based on position and fatigue
                        if fatigue > 80:
                            ttype = TrainingType.REST
                        elif fatigue > 50:
                            if player.position.name == 'PITCHER':
                                ttype = random.choice([TrainingType.PITCHING, TrainingType.CONTROL, TrainingType.STAMINA, 
                                                       TrainingType.REST, TrainingType.REST, TrainingType.REST])
                            else:
                                ttype = random.choice([TrainingType.BATTING, TrainingType.POWER, TrainingType.RUNNING, 
                                                       TrainingType.FIELDING, TrainingType.REST, TrainingType.REST])
                        else:
                            if player.position.name == 'PITCHER':
                                ttype = random.choice([TrainingType.PITCHING, TrainingType.CONTROL, TrainingType.STAMINA])
                            else:
                                ttype = random.choice([TrainingType.BATTING, TrainingType.POWER, TrainingType.RUNNING, TrainingType.FIELDING])
                        res = PlayerDevelopment.train_player(player, ttype, xp_multiplier=0.6)
                        if res.get('success'):
                            trained += 1
                        if res.get('stat_gains'):
                            stat_ups += len(res['stat_gains'])
                
                self.spring_camp_day = max_days + 1
                self.spring_selected_menus = {}
                ToastManager.show(f"残り{remaining}日を自動実行 ({stat_ups}回成長)", "success")
                self.state_manager.change_state(GameState.MENU)
            elif self.confirm_action == "spring_batch_with_log":
                # 春季キャンプ一括実行（ログ表示あり）
                self._run_camp_batch(is_fall=False, show_log=True)
            elif self.confirm_action == "fall_batch_with_log":
                # 秋季キャンプ一括実行（ログ表示あり）
                self._run_camp_batch(is_fall=True, show_log=True)
            elif self.confirm_action == "fall_auto_finish":
                # 秋季キャンプ残り日数を自動実行
                from player_development import PlayerDevelopment, TrainingType
                fall_players = self.fall_camp_players if self.fall_camp_players else []
                max_days = getattr(self, 'fall_camp_max_days', 14)
                cur_day = getattr(self, 'fall_camp_day', 1)
                remaining = max_days - cur_day + 1
                
                trained = 0
                stat_ups = 0
                for _ in range(remaining):
                    for player in fall_players:
                        # Get player fatigue
                        fatigue = getattr(player.player_status, 'fatigue', 0) if hasattr(player, 'player_status') and player.player_status else 0
                        
                        # Pick training based on position and fatigue
                        if fatigue > 80:
                            ttype = TrainingType.REST
                        elif fatigue > 50:
                            if player.position.name == 'PITCHER':
                                ttype = random.choice([TrainingType.PITCHING, TrainingType.CONTROL, TrainingType.STAMINA,
                                                       TrainingType.REST, TrainingType.REST, TrainingType.REST])
                            else:
                                ttype = random.choice([TrainingType.BATTING, TrainingType.POWER, TrainingType.RUNNING,
                                                       TrainingType.FIELDING, TrainingType.REST, TrainingType.REST])
                        else:
                            if player.position.name == 'PITCHER':
                                ttype = random.choice([TrainingType.PITCHING, TrainingType.CONTROL, TrainingType.STAMINA])
                            else:
                                ttype = random.choice([TrainingType.BATTING, TrainingType.POWER, TrainingType.RUNNING, TrainingType.FIELDING])
                        res = PlayerDevelopment.train_player(player, ttype, xp_multiplier=0.6)
                        if res.get('success'):
                            trained += 1
                        if res.get('stat_gains'):
                            stat_ups += len(res['stat_gains'])
                
                self.fall_camp_day = max_days + 1
                self.fall_selected_menus = {}
                ToastManager.show(f"秋季キャンプ終了 ({stat_ups}回成長) ドラフトへ", "success")
                self.generate_draft_prospects()
                self.state_manager.change_state(GameState.DRAFT)
            self.confirm_action = None
            self.confirm_message = None
        
        elif button_name == "confirm_no":
            # 確認ダイアログでNO（キャンセル）- 一括実行ではログなしで実行
            self.show_confirm_dialog = False
            if self.confirm_action == "spring_batch_with_log":
                self._run_camp_batch(is_fall=False, show_log=False)
            elif self.confirm_action == "fall_batch_with_log":
                self._run_camp_batch(is_fall=True, show_log=False)
            self.confirm_action = None
            self.confirm_message = None
        
        elif button_name == "settings":
            self.state_manager.change_state(GameState.SETTINGS)
        
        elif button_name == "quit":
            pygame.quit()
            sys.exit()
        
        # === 新規ゲーム設定画面 ===
        elif button_name.startswith("setup_toggle_"):
            # シーズンイベント切り替え
            key = button_name.replace("setup_toggle_", "")
            rules = self.settings.game_rules
            if hasattr(rules, key):
                current = getattr(rules, key)
                setattr(rules, key, not current)
                status = "ON" if not current else "OFF"
                ToastManager.show(f"{key} を {status} に変更", "info")
        
        elif button_name.startswith("setup_games_"):
            # 試合数設定
            games = int(button_name.replace("setup_games_", ""))
            self.settings.game_rules.regular_season_games = games
            ToastManager.show(f"シーズン {games}試合 に設定", "info")
        
        elif button_name.startswith("setup_innings_"):
            # 延長上限設定
            innings = int(button_name.replace("setup_innings_", ""))
            self.settings.game_rules.extra_innings_limit = innings
            if innings == 0:
                ToastManager.show("延長戦を無制限に設定", "info")
            else:
                ToastManager.show(f"延長戦上限を {innings}回 に設定", "info")
        
        elif button_name.startswith("setup_foreign_limit_"):
            # 外国人支配下枠設定
            limit = int(button_name.replace("setup_foreign_limit_", ""))
            self.settings.game_rules.foreign_player_limit = limit
            ToastManager.show(f"外国人支配下枠を {limit}人 に設定", "info")
        
        elif button_name == "confirm_start":
            # ゲーム開始確定（チーム選択後に設定画面から来た場合のみ有効）
            if getattr(self, '_pending_pennant_start', False):
                self._pending_pennant_start = False
                self.start_pennant_mode()
            else:
                # チームが選択されていなければ警告
                if not self.state_manager.player_team:
                    ToastManager.show("先にチームを選択してください", "warning")
                else:
                    self.start_pennant_mode()
        
        # 難易度選択（互換性のため残す）
        elif button_name == "confirm" and self.state_manager.current_state == GameState.DIFFICULTY_SELECT:
            self.init_teams()
            self.state_manager.change_state(GameState.TEAM_SELECT)
        
        elif button_name == "back_title":
            # 新規ゲーム設定画面から戻る
            if getattr(self, '_pending_pennant_start', False):
                # チーム選択後に設定画面にいる場合はチーム選択へ戻る
                self._pending_pennant_start = False
                self.state_manager.change_state(GameState.TEAM_SELECT)
            else:
                self.state_manager.change_state(GameState.TITLE)
        
        # ===== 選手エディタ画面 =====
        elif button_name == "editor_back":
            self.state_manager.change_state(GameState.TITLE)
            self.show_title_start_menu = False
        
        elif button_name == "editor_save":
            self._save_editor_data()
        
        elif button_name == "editor_regenerate":
            self._regenerate_all_players()
        
        elif button_name.startswith("editor_team_"):
            # チーム選択タブ
            idx = int(button_name.replace("editor_team_", ""))
            self.editor_selected_team_idx = idx
            self.editor_selected_player_idx = -1
            self.editor_scroll = 0
        
        elif button_name == "editor_tab_batters":
            self.editor_tab = "batters"
            self.editor_scroll = 0
            self.editor_selected_player_idx = -1
        
        elif button_name == "editor_tab_pitchers":
            self.editor_tab = "pitchers"
            self.editor_scroll = 0
            self.editor_selected_player_idx = -1
        
        elif button_name.startswith("editor_player_"):
            # 選手選択
            idx = int(button_name.replace("editor_player_", ""))
            self.editor_selected_player_idx = idx
            self.editor_editing_field = None
            self.editor_edit_value = ""
        
        elif button_name == "editor_scroll_up":
            self.editor_scroll = max(0, self.editor_scroll - 1)
        
        elif button_name == "editor_scroll_down":
            self.editor_scroll += 1
        
        elif button_name == "edit_name":
            # 名前編集開始
            if self.editor_selected_player_idx >= 0 and self.editor_teams:
                team = self.editor_teams[self.editor_selected_team_idx]
                player = team.players[self.editor_selected_player_idx]
                self.editor_editing_field = "name"
                self.editor_edit_value = player.name
        
        elif button_name.startswith("edit_") and self.editor_selected_player_idx >= 0:
            # 能力値編集開始
            key = button_name.replace("edit_", "")
            if self.editor_teams and key not in ["name", "team_names"]:
                team = self.editor_teams[self.editor_selected_team_idx]
                player = team.players[self.editor_selected_player_idx]
                if hasattr(player.stats, key):
                    self.editor_editing_field = key
                    self.editor_edit_value = str(getattr(player.stats, key))
        
        # チーム名編集画面への遷移
        elif button_name == "edit_team_names":
            self.state_manager.change_state(GameState.TEAM_EDIT)
            self.editing_team_idx = -1
            self.team_name_input = ""
        
        # チーム編集画面のボタン
        elif button_name.startswith("edit_team_"):
            idx = int(button_name.replace("edit_team_", ""))
            self.editing_team_idx = idx
            team = self.state_manager.all_teams[idx]
            self.team_name_input = self.custom_team_names.get(team.name, "")
        
        elif button_name.startswith("confirm_edit_"):
            self._confirm_team_name_edit()
        
        elif button_name.startswith("cancel_edit_"):
            self._cancel_team_name_edit()
        
        elif button_name.startswith("reset_team_"):
            idx = int(button_name.replace("reset_team_", ""))
            team = self.state_manager.all_teams[idx]
            if team.name in self.custom_team_names:
                del self.custom_team_names[team.name]
                self._save_team_name_presets()  # プリセットを保存
                ToastManager.show("チーム名をリセットしました", "info")
        
        elif button_name == "back_to_select":
            self.state_manager.change_state(GameState.TEAM_SELECT)
            self.editing_team_idx = -1
            self.team_name_input = ""
        
        elif button_name == "apply_names":
            self.state_manager.change_state(GameState.TEAM_SELECT)
            ToastManager.show("チーム名を適用しました", "success")
        
        # チーム選択（プレビュー）
        elif button_name.startswith("team_"):
            team_name = button_name.replace("team_", "")
            # プレビュー用にチーム名を保持
            self.preview_team_name = team_name
            self.team_preview_scroll = 0  # スクロールリセット
            display_name = self.custom_team_names.get(team_name, team_name)
            ToastManager.show(f"{display_name} を選択中", "info")
        
        # チーム確定
        elif button_name == "confirm_team":
            if self.preview_team_name:
                for team in self.state_manager.all_teams:
                    if team.name == self.preview_team_name:
                        self.state_manager.player_team = team
                        self.init_schedule()
                        display_name = self.custom_team_names.get(self.preview_team_name, self.preview_team_name)
                        ToastManager.show(f"{display_name} を選択しました。設定を確認してください", "success")
                        self.preview_team_name = None
                        self.team_preview_scroll = 0
                        # 新規ゲーム設定画面へ遷移（チーム選択前の設定画面をチーム選択後に表示）
                        self.new_game_setup_state = {"difficulty": self.new_game_setup_state.get("difficulty", "normal")}
                        self._pending_pennant_start = True  # 設定後にペナント開始
                        self.state_manager.change_state(GameState.NEW_GAME_SETUP)
                        return
            else:
                ToastManager.show("チームを選択してください", "warning")
        
        # チーム選択画面からタイトルに戻る
        elif button_name == "team_select_back":
            self.preview_team_name = None
            self.team_preview_scroll = 0
            self.state_manager.change_state(GameState.TITLE)
            self.show_title_start_menu = False
        
        # チーム追加ボタン
        elif button_name == "add_team":
            self.new_team_name = ""
            self.new_team_league = "central"
            self.new_team_color_idx = 0
            self.new_team_gen_mode = "random"
            self.state_manager.change_state(GameState.TEAM_CREATE)
        
        # チーム作成画面のボタン
        elif button_name == "team_league_central":
            self.new_team_league = "central"
        elif button_name == "team_league_pacific":
            self.new_team_league = "pacific"
        elif button_name.startswith("team_color_"):
            idx = int(button_name.replace("team_color_", ""))
            self.new_team_color_idx = idx
        elif button_name == "team_gen_random":
            self.new_team_gen_mode = "random"
        elif button_name == "team_gen_template":
            self.new_team_gen_mode = "template"
        elif button_name == "create_team_confirm":
            self._create_new_team()
        elif button_name == "create_team_cancel":
            self.state_manager.change_state(GameState.TEAM_SELECT)
        
        # ========================================
        # メインメニュー（新項目）
        # ========================================
        # 試合メニュー
        elif button_name == "game_menu":
            self.start_game()
        
        # スケジュール
        elif button_name == "schedule":
            self.state_manager.change_state(GameState.SCHEDULE_VIEW)
            self.selected_game_idx = -1  # 選択リセット
            # 次の試合位置へスクロール
            if self.schedule_manager and self.state_manager.player_team:
                games = self.schedule_manager.get_team_schedule(self.state_manager.player_team.name)
                next_idx = next((i for i, g in enumerate(games) if not g.is_completed), 0)
                self.scroll_offset = max(0, next_idx - 3)
                self.selected_game_idx = next_idx  # デフォルトで次の試合を選択
            else:
                self.scroll_offset = 0
        
        # 日程選択
        elif button_name.startswith("select_game_"):
            idx = int(button_name.replace("select_game_", ""))
            self.selected_game_idx = idx
            ToastManager.show(f"第{idx + 1}戦を選択しました", "info")
        
        # 選択した日程までスキップ
        elif button_name == "skip_to_date":
            if self.selected_game_idx >= 0:
                self.simulate_all_games_until(self.selected_game_idx)
        
        # 育成画面
        elif button_name == "training":
            self.state_manager.change_state(GameState.TRAINING)
            self.selected_training_player_idx = -1
            self.selected_training_idx = -1
            self.training_filter_pos = None
            self.training_player_scroll = 0
        
        # 育成: 選手選択
        elif button_name.startswith("training_select_player_"):
            idx = int(button_name.replace("training_select_player_", ""))
            self.selected_training_player_idx = idx
            # Load existing menu selection for this player
            if not hasattr(self, 'training_selected_menus'):
                self.training_selected_menus = {}
            team = self.state_manager.player_team
            all_players = team.players if team else []
            filtered_players = getattr(self.renderer, '_training_filtered_players', all_players)
            if 0 <= idx < len(filtered_players):
                actual_player = filtered_players[idx]
                try:
                    actual_idx = all_players.index(actual_player)
                except ValueError:
                    actual_idx = idx
                self.selected_training_idx = self.training_selected_menus.get(actual_idx, -1)
        
        # 育成: ポジションフィルタ
        elif button_name.startswith("training_filter_pos_"):
            pos = button_name.replace("training_filter_pos_", "")
            self.training_filter_pos = pos if pos != "ALL" else None
            self.training_player_scroll = 0
            self.selected_training_player_idx = -1
        
        # 育成: メニュー選択
        elif button_name.startswith("training_option_"):
            idx = int(button_name.replace("training_option_", ""))
            self.selected_training_idx = idx
            # If a player is selected, immediately assign this menu to that player
            p_idx = getattr(self, 'selected_training_player_idx', -1)
            if p_idx >= 0:
                if not hasattr(self, 'training_selected_menus'):
                    self.training_selected_menus = {}
                team = self.state_manager.player_team
                all_players = team.players if team else []
                filtered_players = getattr(self.renderer, '_training_filtered_players', all_players)
                if 0 <= p_idx < len(filtered_players):
                    actual_player = filtered_players[p_idx]
                    try:
                        actual_idx = all_players.index(actual_player)
                    except ValueError:
                        actual_idx = p_idx
                    self.training_selected_menus[actual_idx] = idx
                    ToastManager.show(f"{actual_player.name} のメニューを設定しました", "info")

                    # Menu assigned for this player; keep selection stable (no auto-advance)
        
        # 育成: メニュー設定
        elif button_name == "training_set_menu":
            if not hasattr(self, 'training_selected_menus'):
                self.training_selected_menus = {}
            team = self.state_manager.player_team
            all_players = team.players if team else []
            filtered_players = getattr(self.renderer, '_training_filtered_players', all_players)
            
            p_idx = getattr(self, 'selected_training_player_idx', -1)
            t_idx = getattr(self, 'selected_training_idx', -1)
            
            if 0 <= p_idx < len(filtered_players) and t_idx >= 0:
                actual_player = filtered_players[p_idx]
                try:
                    actual_idx = all_players.index(actual_player)
                except ValueError:
                    actual_idx = p_idx
                self.training_selected_menus[actual_idx] = t_idx
                ToastManager.show(f"{actual_player.name} のメニューを設定しました", "info")
                
                # Menu assigned for this player; keep selection stable (no auto-advance)
            else:
                ToastManager.show("選手とメニューを選択してください", "warning")
        
        # 育成: AI自動メニュー設定
        elif button_name == "training_auto_menu":
            from ai_system import ai_manager, AITrainingStrategy
            
            team = self.state_manager.player_team
            if team:
                if not hasattr(self, 'training_selected_menus'):
                    self.training_selected_menus = {}
                
                auto_set_count = 0
                for i, player in enumerate(team.players):
                    if i not in self.training_selected_menus:
                        # AIによる最適メニュー選択（弱点強化戦略）
                        t_idx = ai_manager.get_smart_training_menu(player, AITrainingStrategy.WEAKNESS)
                        self.training_selected_menus[i] = t_idx
                        auto_set_count += 1
                
                ToastManager.show(f"AI: {auto_set_count}人の弱点を分析してメニュー設定", "success")
        
        # 育成: メニュー全クリア
        elif button_name == "training_clear_menu":
            if hasattr(self, 'training_selected_menus'):
                cleared_count = len(self.training_selected_menus)
                self.training_selected_menus = {}
                self.selected_training_player_idx = -1
                self.selected_training_idx = -1
                ToastManager.show(f"{cleared_count}人のメニューをクリアしました", "info")
        
        # 育成: 日を進める（全員練習）
        elif button_name == "training_advance_day":
            from player_development import PlayerDevelopment, TrainingType
            
            if not hasattr(self, 'training_selected_menus'):
                self.training_selected_menus = {}
            
            team = self.state_manager.player_team
            all_players = team.players if team else []
            
            # Define training types - must match screens.py UI order
            # 投手: 投球(PITCHING), 制球(CONTROL), 変化球(BREAKING), スタミナ(STAMINA)
            # 野手: 打撃(BATTING), 筋力(POWER), 走塁(RUNNING), 守備(FIELDING), スタミナ(STAMINA)
            trainings_pitcher = [TrainingType.PITCHING, TrainingType.CONTROL, TrainingType.BREAKING,
                                 TrainingType.STAMINA]
            trainings_batter = [TrainingType.BATTING, TrainingType.POWER, TrainingType.RUNNING,
                                TrainingType.FIELDING, TrainingType.STAMINA]
            
            trained_count = 0
            stat_ups = 0
            for p_idx, t_idx in self.training_selected_menus.items():
                if 0 <= p_idx < len(all_players):
                    player = all_players[p_idx]
                    if player.position.name == 'PITCHER':
                        tlist = trainings_pitcher
                    else:
                        tlist = trainings_batter
                    if 0 <= t_idx < len(tlist):
                        ttype = tlist[t_idx]
                        res = PlayerDevelopment.train_player(player, ttype)
                        if res.get('success'):
                            trained_count += 1
                        if res.get('stat_gains'):
                            stat_ups += len(res['stat_gains'])
            
            # Clear menus after training
            self.training_selected_menus = {}
            self.selected_training_player_idx = -1
            self.selected_training_idx = -1
            
            ToastManager.show(f"練習完了 ({trained_count}人練習, {stat_ups}回成長)", "success")

        # 春季キャンプ画面: 選手選択
        elif button_name.startswith("spring_select_player_"):
            idx = int(button_name.replace("spring_select_player_", ""))
            self.selected_spring_player_idx = idx

        # 春季キャンプ: ポジションフィルタ
        elif button_name.startswith("spring_filter_pos_"):
            pos = button_name.replace("spring_filter_pos_", "")
            self.spring_filter_pos = pos if pos != "ALL" else None
            self.spring_player_scroll = 0  # フィルタ変更時はスクロールリセット
            self.selected_spring_player_idx = -1  # 選択もリセット

        # 春季キャンプ: トレーニング選択
        elif button_name.startswith("spring_training_"):
            idx = int(button_name.replace("spring_training_", ""))
            # If a player is selected, save the training as that player's chosen menu
            p_idx = getattr(self, 'selected_spring_player_idx', -1)
            if p_idx is not None and p_idx >= 0:
                # Get the actual player from filtered list
                team = self.state_manager.player_team
                all_players = team.players if team else []
                filtered_players = getattr(self.renderer, '_spring_camp_filtered_players', all_players)
                
                if 0 <= p_idx < len(filtered_players):
                    player = filtered_players[p_idx]
                    fatigue = getattr(player.player_status, 'fatigue', 0) if hasattr(player, 'player_status') and player.player_status else 0
                    
                    # Check if fatigue > 80 and non-REST selected
                    # REST is index 4 for pitchers, 5 for batters
                    is_pitcher = player.position.name == 'PITCHER'
                    rest_idx = 4 if is_pitcher else 5
                    
                    if fatigue > 80 and idx != rest_idx:
                        ToastManager.show(f"疲労度が{fatigue}%のため休養しか選べません", "warning")
                        idx = rest_idx  # Force REST
                
                if not hasattr(self, 'spring_selected_menus'):
                    self.spring_selected_menus = {}
                self.spring_selected_menus[p_idx] = idx
            # Also store globally for fallback/renderer
            self.selected_spring_training_idx = idx

        # 春季キャンプ: 練習実行 → メニュー設定 or 日を進める
        elif button_name == "spring_confirm_train":
            from player_development import PlayerDevelopment, TrainingType
            
            if not hasattr(self, 'spring_selected_menus'):
                self.spring_selected_menus = {}
            
            team = self.state_manager.player_team
            all_players = team.players if team else []
            
            # Check if all players have menus set
            all_menus_set = len(self.spring_selected_menus) >= len(all_players) and len(all_players) > 0
            
            if all_menus_set:
                # ADVANCE DAY: Execute training for all players
                # Must match screens.py UI order exactly
                trainings_pitcher = [TrainingType.PITCHING, TrainingType.CONTROL, TrainingType.BREAKING,
                                     TrainingType.STAMINA, TrainingType.REST]
                trainings_batter = [TrainingType.BATTING, TrainingType.POWER, TrainingType.RUNNING,
                                    TrainingType.FIELDING, TrainingType.STAMINA, TrainingType.REST]
                
                trained_count = 0
                stat_ups = 0
                for p_idx, t_idx in self.spring_selected_menus.items():
                    if 0 <= p_idx < len(all_players):
                        player = all_players[p_idx]
                        if player.position.name == 'PITCHER':
                            tlist = trainings_pitcher
                        else:
                            tlist = trainings_batter
                        if 0 <= t_idx < len(tlist):
                            ttype = tlist[t_idx]
                            res = PlayerDevelopment.train_player(player, ttype, xp_multiplier=0.6)
                            if res.get('success'):
                                trained_count += 1
                            if res.get('stat_gains'):
                                stat_ups += len(res['stat_gains'])
                
                # Clear menus after day advance
                self.spring_selected_menus = {}
                
                # Advance camp day
                self.spring_camp_day = getattr(self, 'spring_camp_day', 1) + 1
                max_days = getattr(self, 'spring_camp_max_days', 30)
                
                ToastManager.show(f"Day {self.spring_camp_day - 1} 完了 ({trained_count}人練習, {stat_ups}回成長)", "success")
                
                if self.spring_camp_day > max_days:
                    ToastManager.show("キャンプ終了 開幕に向けて準備完了", "success")
                    self.state_manager.change_state(GameState.MENU)
            else:
                # SET MENU for selected player
                p_idx = getattr(self, 'selected_spring_player_idx', -1)
                t_idx = getattr(self, 'selected_spring_training_idx', -1)
                
                # Get actual player index in all_players (not filtered)
                filtered_players = getattr(self.renderer, '_spring_camp_filtered_players', all_players)
                if 0 <= p_idx < len(filtered_players):
                    actual_player = filtered_players[p_idx]
                    actual_idx = all_players.index(actual_player) if actual_player in all_players else p_idx
                    
                    if t_idx >= 0:
                        self.spring_selected_menus[actual_idx] = t_idx
                        ToastManager.show(f"{actual_player.name} のメニューを設定しました", "info")
                        # Keep selection on this player (do not auto-advance)
                    else:
                        ToastManager.show("練習メニューを選択してください", "warning")
                else:
                    ToastManager.show("選手を選択してください", "warning")

        # 春季キャンプ: 戻る
        elif button_name == "spring_back":
            self.state_manager.change_state(GameState.MENU)

        # 春季キャンプ: メニュー自動設定（日を進めない）
        elif button_name == "spring_auto_train":
            from ai_system import ai_manager, AITrainingStrategy
            
            team = self.state_manager.player_team
            if team:
                if not hasattr(self, 'spring_selected_menus'):
                    self.spring_selected_menus = {}
                
                # AI自動設定
                auto_set_count = 0
                for i, player in enumerate(team.players):
                    if i not in self.spring_selected_menus:
                        # 疲労度チェック
                        fatigue = getattr(player.player_status, 'fatigue', 0) if hasattr(player, 'player_status') and player.player_status else 0
                        
                        if fatigue > 80:
                            # 疲労度が高い場合は休養
                            if player.position.name == 'PITCHER':
                                t_idx = 4  # REST for pitcher
                            else:
                                t_idx = 5  # REST for batter
                        elif fatigue > 50:
                            # 疲労度中程度は50%休養
                            if player.position.name == 'PITCHER':
                                t_idx = random.choice([ai_manager.get_smart_training_menu(player, AITrainingStrategy.WEAKNESS), 4, 4])
                            else:
                                t_idx = random.choice([ai_manager.get_smart_training_menu(player, AITrainingStrategy.WEAKNESS), 5, 5])
                        else:
                            # AIによる最適メニュー選択
                            t_idx = ai_manager.get_smart_training_menu(player, AITrainingStrategy.WEAKNESS)
                        
                        self.spring_selected_menus[i] = t_idx
                        auto_set_count += 1
                
                ToastManager.show(f"AI: {auto_set_count}人の弱点を分析してメニュー設定", "success")
        
        # 春季キャンプ: 一括実行（残り日数を一気に実行）
        elif button_name == "spring_batch_run":
            team = self.state_manager.player_team
            all_players = team.players if team else []
            
            # First auto-set menus if not set (with fatigue consideration)
            if not hasattr(self, 'spring_selected_menus'):
                self.spring_selected_menus = {}
            
            for i, player in enumerate(all_players):
                if i not in self.spring_selected_menus:
                    fatigue = getattr(player.player_status, 'fatigue', 0) if hasattr(player, 'player_status') and player.player_status else 0
                    if fatigue > 80:
                        t_idx = 4 if player.position.name == 'PITCHER' else 5
                    elif fatigue > 50:
                        if player.position.name == 'PITCHER':
                            t_idx = random.choice([0, 1, 2, 4, 4, 4])
                        else:
                            t_idx = random.choice([0, 1, 2, 3, 5, 5])
                    else:
                        if player.position.name == 'PITCHER':
                            t_idx = random.choice([0, 1, 2])
                        else:
                            t_idx = random.choice([0, 1, 2, 3])
                    self.spring_selected_menus[i] = t_idx
            
            # Show dialog asking if user wants to see growth log
            self.show_confirm_dialog = True
            self.confirm_action = "spring_batch_with_log"
            self.confirm_message = "キャンプ一括実行\n\nメニューを自動設定し、残り日数を\n一気に実行します。\n\n成長ログを表示しますか？"

        # 春季キャンプ: キャンプ終了
        elif button_name == "spring_end_camp":
            # If days remain, confirm auto-run of remaining days
            max_days = getattr(self, 'spring_camp_max_days', 30)
            cur_day = getattr(self, 'spring_camp_day', 1)
            remaining = max_days - cur_day + 1
            if remaining > 0:
                self.show_confirm_dialog = True
                self.confirm_action = "spring_auto_finish"
                self.confirm_message = f"残り{remaining}日あります。\n残りの日数は自動でトレーニングを行います。\n\nキャンプを終了しますか？"
            else:
                ToastManager.show("春季キャンプ終了！シーズン開幕へ！", "success")
                self.spring_selected_menus = {}
                self.state_manager.change_state(GameState.MENU)
        
        # ========================================
        # 秋季キャンプ画面
        # ========================================
        # 秋季キャンプ: 選手選択
        elif button_name.startswith("fall_select_player_"):
            idx = int(button_name.replace("fall_select_player_", ""))
            self.selected_fall_player_idx = idx

        # 秋季キャンプ: ポジションフィルタ
        elif button_name.startswith("fall_filter_pos_"):
            pos = button_name.replace("fall_filter_pos_", "")
            self.fall_filter_pos = pos if pos != "ALL" else None
            self.fall_player_scroll = 0
            self.selected_fall_player_idx = -1

        # 秋季キャンプ: トレーニング選択
        elif button_name.startswith("fall_training_"):
            idx = int(button_name.replace("fall_training_", ""))
            p_idx = getattr(self, 'selected_fall_player_idx', -1)
            if p_idx is not None and p_idx >= 0:
                # Get the actual player from filtered list
                fall_players = self.fall_camp_players if self.fall_camp_players else []
                filtered_players = getattr(self.renderer, '_fall_camp_filtered_players', fall_players)
                
                if 0 <= p_idx < len(filtered_players):
                    player = filtered_players[p_idx]
                    fatigue = getattr(player.player_status, 'fatigue', 0) if hasattr(player, 'player_status') and player.player_status else 0
                    
                    # Check if fatigue > 80 and non-REST selected
                    is_pitcher = player.position.name == 'PITCHER'
                    rest_idx = 4 if is_pitcher else 5
                    
                    if fatigue > 80 and idx != rest_idx:
                        ToastManager.show(f"疲労度が{fatigue}%のため休養しか選べません", "warning")
                        idx = rest_idx  # Force REST
                
                if not hasattr(self, 'fall_selected_menus'):
                    self.fall_selected_menus = {}
                self.fall_selected_menus[p_idx] = idx
            self.selected_fall_training_idx = idx

        # 秋季キャンプ: 練習実行
        elif button_name == "fall_confirm_train":
            from player_development import PlayerDevelopment, TrainingType
            
            if not hasattr(self, 'fall_selected_menus'):
                self.fall_selected_menus = {}
            
            team = self.state_manager.player_team
            # 秋季キャンプは総合力の低い選手のみ参加
            fall_players = self.fall_camp_players if self.fall_camp_players else []
            
            all_menus_set = len(self.fall_selected_menus) >= len(fall_players) and len(fall_players) > 0
            
            if all_menus_set:
                # Must match screens.py UI order exactly
                trainings_pitcher = [TrainingType.PITCHING, TrainingType.CONTROL, TrainingType.BREAKING,
                                     TrainingType.STAMINA, TrainingType.POWER, TrainingType.REST]
                trainings_batter = [TrainingType.BATTING, TrainingType.POWER, TrainingType.RUNNING,
                                    TrainingType.FIELDING, TrainingType.STAMINA, TrainingType.REST]
                
                trained_count = 0
                stat_ups = 0
                for p_idx, t_idx in self.fall_selected_menus.items():
                    if 0 <= p_idx < len(fall_players):
                        player = fall_players[p_idx]
                        if player.position.name == 'PITCHER':
                            tlist = trainings_pitcher
                        else:
                            tlist = trainings_batter
                        if 0 <= t_idx < len(tlist):
                            ttype = tlist[t_idx]
                            res = PlayerDevelopment.train_player(player, ttype, xp_multiplier=0.6)
                            if res.get('success'):
                                trained_count += 1
                            if res.get('stat_gains'):
                                stat_ups += len(res['stat_gains'])
                
                self.fall_selected_menus = {}
                self.fall_camp_day = getattr(self, 'fall_camp_day', 1) + 1
                max_days = getattr(self, 'fall_camp_max_days', 14)
                
                ToastManager.show(f"Day {self.fall_camp_day - 1} 完了 ({trained_count}人練習, {stat_ups}回成長)", "success")
                
                if self.fall_camp_day > max_days:
                    ToastManager.show("秋季キャンプ終了 ドラフトへ", "success")
                    self.generate_draft_prospects()
                    self.state_manager.change_state(GameState.DRAFT)
            else:
                p_idx = getattr(self, 'selected_fall_player_idx', -1)
                t_idx = getattr(self, 'selected_fall_training_idx', -1)
                
                filtered_players = getattr(self.renderer, '_fall_camp_filtered_players', fall_players)
                if 0 <= p_idx < len(filtered_players):
                    actual_player = filtered_players[p_idx]
                    actual_idx = fall_players.index(actual_player) if actual_player in fall_players else p_idx
                    
                    if t_idx >= 0:
                        self.fall_selected_menus[actual_idx] = t_idx
                        ToastManager.show(f"{actual_player.name} のメニューを設定しました", "info")
                        # Keep selection on this player (do not auto-advance)
                    else:
                        ToastManager.show("練習メニューを選択してください", "warning")
                else:
                    ToastManager.show("選手を選択してください", "warning")

        # 秋季キャンプ: 戻る
        elif button_name == "fall_back":
            self.state_manager.change_state(GameState.MENU)

        # 秋季キャンプ: メニュー自動設定
        elif button_name == "fall_auto_train":
            from ai_system import ai_manager, AITrainingStrategy
            
            fall_players = self.fall_camp_players if self.fall_camp_players else []
            if fall_players:
                if not hasattr(self, 'fall_selected_menus'):
                    self.fall_selected_menus = {}
                
                auto_set_count = 0
                for i, player in enumerate(fall_players):
                    if i not in self.fall_selected_menus:
                        # 疲労度チェック
                        fatigue = getattr(player.player_status, 'fatigue', 0) if hasattr(player, 'player_status') and player.player_status else 0
                        
                        if fatigue > 80:
                            if player.position.name == 'PITCHER':
                                t_idx = 4
                            else:
                                t_idx = 5
                        elif fatigue > 50:
                            if player.position.name == 'PITCHER':
                                t_idx = random.choice([ai_manager.get_smart_training_menu(player, AITrainingStrategy.WEAKNESS), 4, 4])
                            else:
                                t_idx = random.choice([ai_manager.get_smart_training_menu(player, AITrainingStrategy.WEAKNESS), 5, 5])
                        else:
                            # AIによる最適メニュー選択
                            t_idx = ai_manager.get_smart_training_menu(player, AITrainingStrategy.WEAKNESS)
                        
                        self.fall_selected_menus[i] = t_idx
                        auto_set_count += 1
                
                ToastManager.show(f"AI: {auto_set_count}人の弱点を分析してメニュー設定", "success")
        
        # 秋季キャンプ: 一括実行
        elif button_name == "fall_batch_run":
            fall_players = self.fall_camp_players if self.fall_camp_players else []
            
            # First auto-set menus if not set (with fatigue consideration)
            if not hasattr(self, 'fall_selected_menus'):
                self.fall_selected_menus = {}
            
            for i, player in enumerate(fall_players):
                if i not in self.fall_selected_menus:
                    fatigue = getattr(player.player_status, 'fatigue', 0) if hasattr(player, 'player_status') and player.player_status else 0
                    if fatigue > 80:
                        t_idx = 4 if player.position.name == 'PITCHER' else 5
                    elif fatigue > 50:
                        if player.position.name == 'PITCHER':
                            t_idx = random.choice([0, 1, 2, 4, 4, 4])
                        else:
                            t_idx = random.choice([0, 1, 2, 3, 5, 5])
                    else:
                        if player.position.name == 'PITCHER':
                            t_idx = random.choice([0, 1, 2])
                        else:
                            t_idx = random.choice([0, 1, 2, 3])
                    self.fall_selected_menus[i] = t_idx
            
            # Show dialog asking if user wants to see growth log
            self.show_confirm_dialog = True
            self.confirm_action = "fall_batch_with_log"
            self.confirm_message = "キャンプ一括実行\n\nメニューを自動設定し、残り日数を\n一気に実行します。\n\n成長ログを表示しますか？"

        # 秋季キャンプ: キャンプ終了
        elif button_name == "fall_end_camp":
            max_days = getattr(self, 'fall_camp_max_days', 14)
            cur_day = getattr(self, 'fall_camp_day', 1)
            remaining = max_days - cur_day + 1
            if remaining > 0:
                self.show_confirm_dialog = True
                self.confirm_action = "fall_auto_finish"
                self.confirm_message = f"残り{remaining}日あります。\n残りの日数は自動でトレーニングを行います。\n\nキャンプを終了しますか？"
            else:
                ToastManager.show("秋季キャンプ終了 ドラフトへ", "success")
                self.fall_selected_menus = {}
                self.generate_draft_prospects()
                self.state_manager.change_state(GameState.DRAFT)
        
        # 育成: トレーニング実行
        elif button_name.startswith("train_"):
            self.execute_training(button_name)
        
        # 編成（新しい編成画面へ）
        elif button_name == "roster":
            self.roster_tab = "order"  # デフォルトをオーダータブに
            self.selected_roster_player_idx = -1
            self.scroll_offset = 0
            self.state_manager.change_state(GameState.ROSTER_MANAGEMENT)
        
        # 編成画面から選手詳細を表示
        elif button_name.startswith("player_detail_"):
            player_idx = int(button_name.replace("player_detail_", ""))
            if player_idx < len(self.state_manager.player_team.players):
                self.selected_detail_player = self.state_manager.player_team.players[player_idx]
                self.player_detail_scroll = 0
                self._previous_state = self.state_manager.current_state  # 戻り先を記憶
                self.state_manager.change_state(GameState.PLAYER_DETAIL)
        
        # オーダー画面から選手詳細を表示
        elif button_name.startswith("order_player_detail_"):
            player_idx = int(button_name.replace("order_player_detail_", ""))
            if player_idx < len(self.state_manager.player_team.players):
                self.selected_detail_player = self.state_manager.player_team.players[player_idx]
                self.player_detail_scroll = 0
                self._previous_state = self.state_manager.current_state  # 戻り先を記憶
                self.state_manager.change_state(GameState.PLAYER_DETAIL)
        
        # 選手登録管理（旧ルートからも対応）
        elif button_name == "roster_management":
            self.roster_tab = "order"  # デフォルトをオーダータブに
            self.selected_roster_player_idx = -1
            self.scroll_offset = 0
            self.state_manager.change_state(GameState.ROSTER_MANAGEMENT)
        
        # オーダータブのサブタブ切り替え（野手オーダー/投手オーダー）
        elif button_name == "tab_batter_order":
            self.order_sub_tab = "batter"
            self.scroll_offset = 0
        elif button_name == "tab_pitcher_order":
            self.order_sub_tab = "pitcher"
            self.scroll_offset = 0
            self.pitcher_scroll = 0
        
        # 野手一覧から詳細画面へ
        elif button_name.startswith("detail_batter_"):
            player_idx = int(button_name.replace("detail_batter_", ""))
            if player_idx < len(self.state_manager.player_team.players):
                self.selected_detail_player = self.state_manager.player_team.players[player_idx]
                self.player_detail_scroll = 0
                self._previous_state = self.state_manager.current_state
                self.state_manager.change_state(GameState.PLAYER_DETAIL)
        
        # 投手一覧から詳細画面へ
        elif button_name.startswith("detail_pitcher_"):
            player_idx = int(button_name.replace("detail_pitcher_", ""))
            if player_idx < len(self.state_manager.player_team.players):
                self.selected_detail_player = self.state_manager.player_team.players[player_idx]
                self.player_detail_scroll = 0
                self._previous_state = self.state_manager.current_state
                self.state_manager.change_state(GameState.PLAYER_DETAIL)
        
        # 選手登録管理タブ切り替え（tab_batter_order, tab_pitcher_order より後に処理）
        elif button_name.startswith("tab_") and button_name not in ["tab_batter_order", "tab_pitcher_order"]:
            tab_name = button_name.replace("tab_", "")
            if tab_name in ["order", "farm", "players", "promote", "release", "trade"]:
                self.roster_tab = tab_name
                # 各スクロールをリセット
                self.scroll_offset = 0
                self.farm_scroll_first = 0
                self.farm_scroll_second = 0
                self.farm_scroll_third = 0
                self.order_scroll_batters = 0
                self.order_scroll_pitchers = 0
        
        # ラインナップ画面のロースタータブ
        elif button_name == "tab_all":
            self.lineup_roster_tab = "all"
        elif button_name == "tab_batters":
            self.lineup_roster_tab = "batters"
        elif button_name == "tab_pitchers":
            self.lineup_roster_tab = "pitcher"
        
        # オーダー画面からの一軍昇格（二軍→一軍）
        elif button_name.startswith("promote_first_"):
            # 二軍野手のプレイヤーインデックス
            player_idx = int(button_name.replace("promote_first_", ""))
            self._promote_player_farm(player_idx)
        
        # 二軍野手クリック選択（入れ替え用）
        elif button_name.startswith("second_batter_"):
            player_idx = int(button_name.replace("second_batter_", ""))
            self._handle_second_batter_click(player_idx)
        
        # 投手オーダー画面からの一軍昇格（二軍→一軍）
        elif button_name.startswith("promote_pitcher_first_"):
            player_idx = int(button_name.replace("promote_pitcher_first_", ""))
            self._promote_player_farm(player_idx)
        
        # 二軍投手クリック選択（入れ替え用）
        elif button_name.startswith("second_pitcher_"):
            player_idx = int(button_name.replace("second_pitcher_", ""))
            self._handle_second_pitcher_click(player_idx)
        
        # 投手オーダー画面からの一軍降格（一軍→二軍）
        elif button_name.startswith("demote_pitcher_first_"):
            player_idx = int(button_name.replace("demote_pitcher_first_", ""))
            self._demote_player_farm(player_idx)
        
        # 野手並び替えボタン（昇順/降順トグル）
        elif button_name == "batter_sort_overall":
            current_mode = getattr(self.renderer, '_batter_sort_mode', 'default')
            current_asc = getattr(self.renderer, '_batter_sort_asc', False)
            if current_mode == 'overall':
                self.renderer._batter_sort_asc = not current_asc
            else:
                self.renderer._batter_sort_mode = 'overall'
                self.renderer._batter_sort_asc = False
        elif button_name == "batter_sort_age":
            current_mode = getattr(self.renderer, '_batter_sort_mode', 'default')
            current_asc = getattr(self.renderer, '_batter_sort_asc', True)
            if current_mode == 'age':
                self.renderer._batter_sort_asc = not current_asc
            else:
                self.renderer._batter_sort_mode = 'age'
                self.renderer._batter_sort_asc = True
        
        # 投手並び替えボタン（昇順/降順トグル）
        elif button_name == "pitcher_sort_overall":
            current_mode = getattr(self.renderer, '_pitcher_sort_mode', 'default')
            current_asc = getattr(self.renderer, '_pitcher_sort_asc', False)
            if current_mode == 'overall':
                self.renderer._pitcher_sort_asc = not current_asc
            else:
                self.renderer._pitcher_sort_mode = 'overall'
                self.renderer._pitcher_sort_asc = False
        elif button_name == "pitcher_sort_age":
            current_mode = getattr(self.renderer, '_pitcher_sort_mode', 'default')
            current_asc = getattr(self.renderer, '_pitcher_sort_asc', True)
            if current_mode == 'age':
                self.renderer._pitcher_sort_asc = not current_asc
            else:
                self.renderer._pitcher_sort_mode = 'age'
                self.renderer._pitcher_sort_asc = True
        
        # 一軍/二軍/三軍入れ替え - 昇格（二軍→一軍）
        elif button_name.startswith("promote_farm_"):
            player_idx = int(button_name.replace("promote_farm_", ""))
            self._promote_player_farm(player_idx)
        
        # 三軍→二軍への昇格
        elif button_name.startswith("promote_third_"):
            player_idx = int(button_name.replace("promote_third_", ""))
            self._promote_player_from_third(player_idx)
        
        # 一軍/二軍/三軍入れ替え - 降格 (demote_bench_* は別処理なので除外)
        elif button_name.startswith("demote_") and not button_name.startswith("demote_bench_"):
            player_idx = int(button_name.replace("demote_", ""))
            self._demote_player_farm(player_idx)
        
        # ロースター画面並び替えボタン（昇順/降順トグル）
        elif button_name == "roster_sort_overall":
            current_mode = getattr(self.renderer, '_roster_sort_mode', 'default')
            current_asc = getattr(self.renderer, '_roster_sort_asc', False)
            if current_mode == 'overall':
                # 同じボタン再クリックで昇順/降順切り替え
                self.renderer._roster_sort_asc = not current_asc
            else:
                self.renderer._roster_sort_mode = 'overall'
                self.renderer._roster_sort_asc = False  # デフォルト: 降順（高い順）
        elif button_name == "roster_sort_age":
            current_mode = getattr(self.renderer, '_roster_sort_mode', 'default')
            current_asc = getattr(self.renderer, '_roster_sort_asc', True)
            if current_mode == 'age':
                self.renderer._roster_sort_asc = not current_asc
            else:
                self.renderer._roster_sort_mode = 'age'
                self.renderer._roster_sort_asc = True  # デフォルト: 昇順（若い順）
        
        # 選手一覧タブ並び替えボタン（昇順/降順トグル）
        elif button_name == "players_sort_overall":
            current_mode = getattr(self.renderer, '_players_sort_mode', 'default')
            current_asc = getattr(self.renderer, '_players_sort_asc', False)
            if current_mode == 'overall':
                self.renderer._players_sort_asc = not current_asc
            else:
                self.renderer._players_sort_mode = 'overall'
                self.renderer._players_sort_asc = False
        elif button_name == "players_sort_age":
            current_mode = getattr(self.renderer, '_players_sort_mode', 'default')
            current_asc = getattr(self.renderer, '_players_sort_asc', True)
            if current_mode == 'age':
                self.renderer._players_sort_asc = not current_asc
            else:
                self.renderer._players_sort_mode = 'age'
                self.renderer._players_sort_asc = True
        
        # 二軍タブ並び替えボタン（昇順/降順トグル）
        elif button_name == "second_sort_overall":
            current_mode = getattr(self.renderer, '_second_sort_mode', 'default')
            current_asc = getattr(self.renderer, '_second_sort_asc', False)
            if current_mode == 'overall':
                self.renderer._second_sort_asc = not current_asc
            else:
                self.renderer._second_sort_mode = 'overall'
                self.renderer._second_sort_asc = False
        elif button_name == "second_sort_age":
            current_mode = getattr(self.renderer, '_second_sort_mode', 'default')
            current_asc = getattr(self.renderer, '_second_sort_asc', True)
            if current_mode == 'age':
                self.renderer._second_sort_asc = not current_asc
            else:
                self.renderer._second_sort_mode = 'age'
                self.renderer._second_sort_asc = True
        
        # 三軍タブ並び替えボタン（昇順/降順トグル）
        elif button_name == "third_sort_overall":
            current_mode = getattr(self.renderer, '_third_sort_mode', 'default')
            current_asc = getattr(self.renderer, '_third_sort_asc', False)
            if current_mode == 'overall':
                self.renderer._third_sort_asc = not current_asc
            else:
                self.renderer._third_sort_mode = 'overall'
                self.renderer._third_sort_asc = False
        elif button_name == "third_sort_age":
            current_mode = getattr(self.renderer, '_third_sort_mode', 'default')
            current_asc = getattr(self.renderer, '_third_sort_asc', True)
            if current_mode == 'age':
                self.renderer._third_sort_asc = not current_asc
            else:
                self.renderer._third_sort_mode = 'age'
                self.renderer._third_sort_asc = True

        # 自由契約タブ並び替えボタン
        elif button_name == "release_sort_overall":
            current = getattr(self.renderer, '_release_sort_mode', 'default')
            self.renderer._release_sort_mode = 'overall' if current != 'overall' else 'default'
        elif button_name == "release_sort_age":
            current = getattr(self.renderer, '_release_sort_mode', 'default')
            self.renderer._release_sort_mode = 'age' if current != 'age' else 'default'

        # 助っ人外国人タブ並び替えボタン（昇順/降順トグル）
        elif button_name == "foreign_sort_overall":
            current_mode = getattr(self.renderer, '_foreign_sort_mode', 'default')
            current_asc = getattr(self.renderer, '_foreign_sort_asc', False)
            if current_mode == 'overall':
                self.renderer._foreign_sort_asc = not current_asc
            else:
                self.renderer._foreign_sort_mode = 'overall'
                self.renderer._foreign_sort_asc = False
        elif button_name == "foreign_sort_age":
            current_mode = getattr(self.renderer, '_foreign_sort_mode', 'default')
            current_asc = getattr(self.renderer, '_foreign_sort_asc', True)
            if current_mode == 'age':
                self.renderer._foreign_sort_asc = not current_asc
            else:
                self.renderer._foreign_sort_mode = 'age'
                self.renderer._foreign_sort_asc = True
        
        # 外国人選手解雇
        elif button_name.startswith("release_foreign_"):
            player_idx = int(button_name.replace("release_foreign_", ""))
            team = self.state_manager.player_team
            if team and player_idx < len(team.players):
                player = team.players[player_idx]
                # 確認なしで即座に解雇
                team.players.remove(player)
                self.has_unsaved_changes = True
                ToastManager.show(f"{player.name}を解雇しました", "info")
        
        # ラインアップに選手追加
        elif button_name.startswith("add_lineup_"):
            player_idx = int(button_name.replace("add_lineup_", ""))
            self.add_player_to_lineup(player_idx)
        
        # ラインアップから選手削除
        elif button_name.startswith("remove_lineup_"):
            slot = int(button_name.replace("remove_lineup_", ""))
            self.remove_player_from_lineup(slot)
        
        # 守備位置クリック選択（選択入れ替え方式に統一）
        # change_pos_ と quick_pos_ は廃止、position_slot_に統合
        
        # 編集モード切り替え（選手 / ポジション / 打順）- Toast不要、UIで判断
        elif button_name == "edit_mode_player":
            self.lineup_edit_mode = "player"
            self.reset_lineup_selection()
        
        elif button_name == "edit_mode_position":
            self.lineup_edit_mode = "position"
            self.reset_lineup_selection()
        
        elif button_name == "edit_mode_batting_order":
            self.lineup_edit_mode = "batting_order"
            self.reset_lineup_selection()
        
        # 野手/投手オーダー タブ切り替え
        elif button_name == "tab_batter_order":
            self.lineup_tab = "batters"
            self.lineup_edit_mode = "player"
            self.reset_lineup_selection()
            self.roster_position_selected_slot = -1
            self.roster_swap_mode = False
            self.scroll_offset = 0
        
        elif button_name == "tab_pitcher_order":
            self.lineup_tab = "pitchers"
            self.lineup_edit_mode = "player"
            self.reset_lineup_selection()
            self.roster_position_selected_slot = -1
            self.roster_swap_mode = False
            self.pitcher_scroll = 0
        
        # ベンチスロット処理
        elif button_name.startswith("bench_slot_"):
            slot = int(button_name.replace("bench_slot_", ""))
            team = self.state_manager.player_team
            if team:
                if self.lineup_swap_mode:
                    # 選手をベンチスロットに配置
                    self._add_to_bench_slot(slot, self.lineup_selected_player_idx)
                    self.reset_lineup_selection()
                else:
                    # ベンチスロットの選手を選択
                    bench = team.bench_lineup or []
                    if slot < len(bench) and bench[slot] >= 0:
                        self.lineup_selected_player_idx = bench[slot]
                        self.lineup_selected_slot = slot
                        self.lineup_selected_source = "bench"
                        self.lineup_swap_mode = True
                        player = team.players[bench[slot]]
                        ToastManager.show(f"ベンチ {player.name}を選択中", "info")
                    else:
                        self.lineup_selected_slot = slot
                        self.lineup_selected_source = "bench_empty"
                        self.lineup_swap_mode = True
                        ToastManager.show(f"ベンチ{slot + 1}番に入れる選手をクリック", "info")
        
        # ベンチから選手削除
        elif button_name.startswith("bench_remove_"):
            slot = int(button_name.replace("bench_remove_", ""))
            self._remove_from_bench(slot)
        
        # ポジションスロットクリック（守備位置の入れ替え専用）
        elif button_name.startswith("position_slot_"):
            slot = int(button_name.replace("position_slot_", ""))
            # 守備位置編集モードのときのみ処理、それ以外は無視
            if self.lineup_edit_mode == "position":
                self.handle_position_slot_click(slot)
            # position_slot_は選手選択には使わない（lineup_slot_を使う）
            return
        
        # ポジション変更ボタン（ROSTER_MANAGEMENT画面用 - 選手選択と同じ入れ替え方式）
        elif button_name.startswith("change_pos_"):
            slot = int(button_name.replace("change_pos_", ""))
            self._handle_position_swap_click(slot)
            return
        
        # 打順スロットクリック（打順の入れ替え専用）
        elif button_name.startswith("batting_order_"):
            slot = int(button_name.replace("batting_order_", ""))
            # 打順編集モードのときのみ処理
            if self.lineup_edit_mode == "batting_order":
                self.handle_batting_order_slot_click(slot)
            return
        
        # ポジションドラッグ開始
        elif button_name.startswith("drag_position_"):
            slot = int(button_name.replace("drag_position_", ""))
            self.dragging_position_slot = slot
            self.position_drag_pos = pygame.mouse.get_pos()
        
        # オーダー最適化（能力順でソート）
        elif button_name == "optimize_lineup":
            self.optimize_lineup_by_stats()
        
        # ラインナップ全入れ替え（シャッフル）
        elif button_name == "shuffle_lineup":
            self.shuffle_lineup()
        
        # ラインナップ保存
        elif button_name == "save_lineup_preset":
            self.save_lineup_preset()
        
        # ラインナップ読み込み
        elif button_name == "load_lineup_preset":
            self.load_lineup_preset()
        
        # ========================================
        # 投手オーダー画面
        # ========================================
        elif button_name == "to_pitcher_order":
            self.pitcher_order_tab = "rotation"
            self.selected_rotation_slot = -1
            self.selected_relief_slot = -1
            self.pitcher_scroll = 0
            self.state_manager.change_state(GameState.PITCHER_ORDER)
        
        elif button_name == "tab_rotation":
            self.pitcher_order_tab = "rotation"
            self.pitcher_scroll = 0
        
        elif button_name == "tab_relief":
            self.pitcher_order_tab = "relief"
            self.pitcher_scroll = 0
        
        elif button_name == "tab_closer":
            self.pitcher_order_tab = "closer"
            self.pitcher_scroll = 0
        
        # ローテーション削除ボタン
        elif button_name.startswith("remove_rotation_"):
            slot = int(button_name.replace("remove_rotation_", ""))
            team = self.state_manager.player_team
            if team and hasattr(team, 'rotation') and slot < len(team.rotation):
                removed_idx = team.rotation[slot]
                if removed_idx >= 0:
                    # 先発が1人以下になる場合は削除不可
                    current_starters = sum(1 for r in team.rotation if r >= 0)
                    if current_starters <= 1:
                        ToastManager.show("先発は最低1人必要です", "warning")
                        return
                    
                    player = team.players[removed_idx] if removed_idx < len(team.players) else None
                    team.rotation[slot] = -1
                    if player:
                        ToastManager.show(f"{player.name}をローテーションから外しました", "info")
                    self.selected_rotation_slot = -1
        
        # 中継ぎ削除ボタン
        elif button_name.startswith("remove_relief_"):
            slot = int(button_name.replace("remove_relief_", ""))
            team = self.state_manager.player_team
            if team and hasattr(team, 'setup_pitchers') and slot < len(team.setup_pitchers):
                removed_idx = team.setup_pitchers[slot]
                if removed_idx >= 0:
                    player = team.players[removed_idx] if removed_idx < len(team.players) else None
                    team.setup_pitchers.pop(slot)
                    if player:
                        ToastManager.show(f"{player.name}を中継ぎから外しました", "info")
                    self.selected_relief_slot = -1
        
        # 抑え削除ボタン
        elif button_name == "remove_closer":
            team = self.state_manager.player_team
            if team:
                removed_idx = getattr(team, 'closer_idx', -1)
                if removed_idx >= 0:
                    player = team.players[removed_idx] if removed_idx < len(team.players) else None
                    team.closer_idx = -1
                    if player:
                        ToastManager.show(f"{player.name}を抑えから外しました", "info")
                    self.selected_rotation_slot = -1
        
        elif button_name.startswith("rotation_slot_"):
            slot = int(button_name.replace("rotation_slot_", ""))
            self.selected_rotation_slot = slot
            self.selected_relief_slot = -1
        
        elif button_name.startswith("relief_slot_"):
            slot = int(button_name.replace("relief_slot_", ""))
            self.selected_relief_slot = slot
            self.selected_rotation_slot = -1
        
        elif button_name == "closer_slot":
            # 抑えスロットを選択（-99で識別）
            self.selected_rotation_slot = -99  # 抑え選択を示す特別な値
            self.selected_relief_slot = -1
            ToastManager.show("抑え投手を設定：右の投手リストから選択", "info")
        
        elif button_name.startswith("pitcher_") and not button_name.startswith("pitcher_scroll"):
            # 投手を選択してスロットに配置
            player_idx = int(button_name.replace("pitcher_", ""))
            team = self.state_manager.player_team
            if team:
                player = team.players[player_idx] if player_idx < len(team.players) else None
                player_name = player.name if player else "選手"
                
                # オーダーサブタブが投手の場合、またはピッチャーオーダータブの場合
                is_pitcher_order_tab = getattr(self, 'order_sub_tab', 'batter') == "pitcher"
                
                # 抑え選択中（-99）
                if self.selected_rotation_slot == -99:
                    old_closer = getattr(team, 'closer_idx', -1)
                    team.closer_idx = player_idx
                    if old_closer >= 0 and old_closer != player_idx:
                        if old_closer not in getattr(team, 'setup_pitchers', []):
                            if not hasattr(team, 'setup_pitchers'):
                                team.setup_pitchers = []
                            team.setup_pitchers.append(old_closer)
                    ToastManager.show(f"{player_name}を抑え投手に設定", "success")
                    self.selected_rotation_slot = -1
                    return
                
                if (is_pitcher_order_tab or self.pitcher_order_tab == "rotation") and self.selected_rotation_slot >= 0:
                    # ローテーションに追加/入れ替え
                    while len(team.rotation) <= self.selected_rotation_slot:
                        team.rotation.append(-1)
                    
                    # 既存選手がいる場合は入れ替え（古い選手をベンチへ）
                    old_pitcher_idx = team.rotation[self.selected_rotation_slot] if self.selected_rotation_slot < len(team.rotation) else -1
                    if old_pitcher_idx >= 0 and old_pitcher_idx != player_idx:
                        # 古い選手をベンチに追加
                        if old_pitcher_idx not in team.bench_pitchers:
                            team.add_to_bench_pitchers(old_pitcher_idx)
                    
                    # 新しい選手をローテに配置
                    team.rotation[self.selected_rotation_slot] = player_idx
                    # ベンチから削除
                    if hasattr(team, 'bench_pitchers') and player_idx in team.bench_pitchers:
                        team.remove_from_bench_pitchers(player_idx)
                    
                    ToastManager.show(f"{player_name}を先発{self.selected_rotation_slot + 1}番手に設定", "success")
                    self.selected_rotation_slot = -1
                    
                elif (is_pitcher_order_tab or self.pitcher_order_tab == "relief") and self.selected_relief_slot >= 0:
                    # 中継ぎに追加
                    if not hasattr(team, 'setup_pitchers'):
                        team.setup_pitchers = []
                    
                    # スロット位置に配置（既存があれば入れ替え）
                    while len(team.setup_pitchers) <= self.selected_relief_slot:
                        team.setup_pitchers.append(-1)
                    
                    old_idx = team.setup_pitchers[self.selected_relief_slot] if self.selected_relief_slot < len(team.setup_pitchers) else -1
                    team.setup_pitchers[self.selected_relief_slot] = player_idx
                    
                    # 既存の投手を他の空きスロットへ
                    if old_idx >= 0 and old_idx != player_idx:
                        for i, s in enumerate(team.setup_pitchers):
                            if s == -1:
                                team.setup_pitchers[i] = old_idx
                                break
                    
                    ToastManager.show(f"{player_name}を中継ぎ{self.selected_relief_slot + 1}に追加", "success")
                    self.selected_relief_slot = -1
                    
                elif self.pitcher_order_tab == "closer":
                    # 抑えに設定
                    old_closer = getattr(team, 'closer_idx', -1)
                    team.closer_idx = player_idx
                    # 古い抑えをベンチに追加
                    if old_closer >= 0 and old_closer != player_idx:
                        if hasattr(team, 'bench_pitchers') and old_closer not in team.bench_pitchers:
                            team.add_to_bench_pitchers(old_closer)
                    ToastManager.show(f"{player_name}を抑え投手に設定", "success")
        
        elif button_name == "pitcher_scroll_up":
            self.pitcher_scroll = max(0, self.pitcher_scroll - 1)
        
        elif button_name == "pitcher_scroll_down":
            self.pitcher_scroll += 1
        
        elif button_name == "pitcher_auto_set" or button_name == "auto_pitcher_order":
            team = self.state_manager.player_team
            if team:
                self._auto_set_pitcher_order(team)
                ToastManager.show("投手陣を自動設定しました", "success")
        
        elif button_name == "pitcher_back":
            self.state_manager.change_state(GameState.LINEUP)
        
        elif button_name == "to_bench_setting":
            self.bench_setting_tab = "batters"
            self.bench_scroll = 0
            self.state_manager.change_state(GameState.BENCH_SETTING)
        
        # ========================================
        # ベンチ設定画面
        # ========================================
        elif button_name == "bench_tab_batters":
            self.bench_setting_tab = "batters"
            self.bench_scroll = 0
        
        elif button_name == "bench_tab_pitchers":
            self.bench_setting_tab = "pitchers"
            self.bench_scroll = 0
        
        elif button_name.startswith("add_bench_"):
            player_idx = int(button_name.replace("add_bench_", ""))
            team = self.state_manager.player_team
            if team:
                if self.bench_setting_tab == "batters":
                    if team.add_to_bench_batters(player_idx):
                        ToastManager.show("野手をベンチに追加", "success")
                    else:
                        ToastManager.show("ベンチが満員です", "warning")
                else:
                    if team.add_to_bench_pitchers(player_idx):
                        ToastManager.show("投手をベンチに追加", "success")
                    else:
                        ToastManager.show("ベンチが満員です", "warning")
        
        # 野手オーダー画面からベンチ野手を追加
        elif button_name.startswith("add_bench_batter_"):
            player_idx = int(button_name.replace("add_bench_batter_", ""))
            team = self.state_manager.player_team
            if team:
                if team.add_to_bench_batters(player_idx):
                    ToastManager.show("野手をベンチに追加", "success")
                else:
                    ToastManager.show("ベンチが満員です", "warning")
        
        elif button_name.startswith("remove_bench_batter_"):
            player_idx = int(button_name.replace("remove_bench_batter_", ""))
            team = self.state_manager.player_team
            if team:
                team.remove_from_bench_batters(player_idx)
                ToastManager.show("ベンチから外しました", "info")
        
        # 控えから外して二軍に降格
        elif button_name.startswith("demote_bench_batter_"):
            player_idx = int(button_name.replace("demote_bench_batter_", ""))
            team = self.state_manager.player_team
            if team:
                team.remove_from_bench_batters(player_idx)
                # 二軍に降格
                from models import TeamLevel
                if player_idx < len(team.players):
                    team.players[player_idx].team_level = TeamLevel.SECOND
                ToastManager.show("二軍に降格しました", "info")
        
        # 控え選手をクリック（選択して入れ替え）
        elif button_name.startswith("bench_batter_"):
            player_idx = int(button_name.replace("bench_batter_", ""))
            team = self.state_manager.player_team
            if team:
                # 二軍野手が選択されていたら入れ替え
                second_batter_idx = getattr(self.renderer, '_second_batter_selected_idx', -1)
                if second_batter_idx >= 0:
                    self._swap_second_batter_with_first(player_idx, "bench")
                else:
                    # 控え選手の選択/選択解除
                    bench_selected = getattr(self.renderer, '_bench_batter_selected_idx', -1)
                    if bench_selected == player_idx:
                        # 同じ選手を再クリックで解除
                        self.renderer._bench_batter_selected_idx = -1
                    else:
                        # 別の控え選手が選択されていたら入れ替え
                        if bench_selected >= 0:
                            self._swap_bench_batters(bench_selected, player_idx)
                            self.renderer._bench_batter_selected_idx = -1
                        else:
                            # 新規選択
                            self.renderer._bench_batter_selected_idx = player_idx
                            if player_idx < len(team.players):
                                player = team.players[player_idx]
                                ToastManager.show(f"{player.name}を選択中。スタメン/控えをクリックで入れ替え", "info")
        
        elif button_name.startswith("remove_bench_pitcher_"):
            idx = int(button_name.replace("remove_bench_pitcher_", ""))
            team = self.state_manager.player_team
            if team and idx < len(team.bench_pitchers):
                player_idx = team.bench_pitchers[idx]
                team.remove_from_bench_pitchers(player_idx)
                ToastManager.show("ベンチから外しました", "info")
        
        elif button_name == "bench_scroll_up":
            self.bench_scroll = max(0, self.bench_scroll - 1)
        
        elif button_name == "bench_scroll_down":
            self.bench_scroll += 1
        
        elif button_name == "bench_auto_set":
            team = self.state_manager.player_team
            if team:
                team.auto_set_bench()
                ToastManager.show("ベンチを自動設定しました", "success")
        
        elif button_name == "bench_back":
            self.state_manager.change_state(GameState.PITCHER_ORDER)
        
        elif button_name == "to_lineup":
            self.state_manager.change_state(GameState.LINEUP)
        
        # 選手解雇（選手一覧タブから）
        elif button_name.startswith("release_player_"):
            player_idx = int(button_name.replace("release_player_", ""))
            self.release_player(player_idx)
        
        # 選手解雇（旧形式）
        elif button_name.startswith("release_") and not button_name.startswith("release_player_"):
            player_idx = int(button_name.replace("release_", ""))
            self.release_player(player_idx)
        
        # 外国人FA市場を開く
        elif button_name == "open_foreign_fa":
            if len(self.state_manager.foreign_free_agents) == 0:
                self.generate_foreign_free_agents()
            self.state_manager.change_state(GameState.FREE_AGENT)
        
        # トレード市場を開く（未実装なのでToast）
        elif button_name == "open_trade_market":
            ToastManager.show("トレード機能は現在開発中です", "info")
        
        # 育成選手を支配下昇格（選手一覧タブから）
        elif button_name.startswith("promote_roster_"):
            player_idx = int(button_name.replace("promote_roster_", ""))
            self.promote_player_to_roster(player_idx)
        
        # 育成選手を支配下昇格（旧形式）
        elif button_name.startswith("promote_") and not button_name.startswith("promote_roster_") and not button_name.startswith("promote_first_") and not button_name.startswith("promote_farm_") and not button_name.startswith("promote_third_") and not button_name.startswith("promote_pitcher_"):
            player_idx = int(button_name.replace("promote_", ""))
            self.promote_player_to_roster(player_idx)
        
        # 経営
        elif button_name == "management":
            self.management_tab = "overview"
            self.state_manager.change_state(GameState.MANAGEMENT)
        
        # 経営タブ切り替え
        elif button_name.startswith("mgmt_tab_"):
            self.management_tab = button_name.replace("mgmt_tab_", "")
        
        # 記録
        elif button_name == "records":
            self.standings_tab = "standings"
            self.state_manager.change_state(GameState.STANDINGS)
        
        # 記録画面タブ切り替え
        elif button_name.startswith("standings_tab_"):
            self.standings_tab = button_name.replace("standings_tab_", "")
        
        # 成績画面の軍別フィルタ切り替え
        elif button_name.startswith("stats_filter_"):
            self.stats_team_level_filter = button_name.replace("stats_filter_", "")
        
        # 設定メニュー
        elif button_name == "settings_menu":
            self.state_manager.change_state(GameState.SETTINGS)
        
        # セーブ機能
        elif button_name == "save_game":
            self.save_current_game()
        
        # ========================================
        # 旧メニュー項目（互換性維持）
        # ========================================
        elif button_name == "lineup":
            self.state_manager.change_state(GameState.LINEUP)
            self.scroll_offset = 0
        
        elif button_name == "jump_next":
            # 次の試合へジャンプ
            if self.schedule_manager and self.state_manager.player_team:
                games = self.schedule_manager.get_team_schedule(self.state_manager.player_team.name)
                next_idx = next((i for i, g in enumerate(games) if not g.is_completed), 0)
                self.scroll_offset = max(0, next_idx - 3)
        
        elif button_name == "start_game":
            self.start_game()
        
        elif button_name == "standings":
            self.state_manager.change_state(GameState.STANDINGS)
        
        elif button_name == "free_agent":
            if len(self.state_manager.foreign_free_agents) == 0:
                self.generate_foreign_free_agents()
            self.state_manager.change_state(GameState.FREE_AGENT)
        
        elif button_name == "team_stats":
            self.state_manager.change_state(GameState.TEAM_STATS)
        
        # ========================================
        # ペナントモード
        # ========================================
        # 春季キャンプ
        elif button_name == "advance_day":
            self.advance_camp_day()
        
        elif button_name == "auto_camp":
            self.auto_camp()
        
        elif button_name == "intrasquad":
            self.execute_intrasquad_game()
        
        elif button_name == "practice_game":
            self.execute_practice_game()
        
        elif button_name.startswith("menu_"):
            # トレーニングメニュー変更 (menu_batting_3 など)
            parts = button_name.split("_")
            if len(parts) == 3:
                key = parts[1]
                value = int(parts[2])
                if self.camp_training_menu is None:
                    self.camp_training_menu = {"batting": 3, "pitching": 3, "fielding": 3, "physical": 3, "rest": 3}
                self.camp_training_menu[key] = value
        
        elif button_name == "camp_training" or button_name == "camp_skip":
            self.process_pennant_camp()
        
        elif button_name == "end_camp":
            # 春季キャンプ終了 → メニューに戻る（自動で試合開始しない）
            self.end_pennant_camp()
        
        elif button_name == "draft_start":
            self.pennant_manager.generate_draft_pool()
            self.pennant_draft_picks = []
            self.state_manager.change_state(GameState.PENNANT_DRAFT)
        
        elif button_name == "confirm_draft":
            self.complete_pennant_draft()
        
        elif button_name == "next_phase":
            self.pennant_manager.advance_phase()
            self.update_pennant_phase()
        
        elif button_name == "play_game":
            self.start_game()
        
        elif button_name == "sim_week":
            self.simulate_games(7)
        
        elif button_name == "sim_month":
            self.simulate_games(30)
        
        # 試合方法選択
        elif button_name == "manage_game":
            # 采配モードで試合開始
            self.start_game_manage_mode()
        
        elif button_name == "watch_game":
            # 観戦モードで試合開始
            self.start_game_watch_mode()
        
        elif button_name == "skip_to_result":
            # 結果までスキップ（従来のGAMEモードへ）
            self.state_manager.change_state(GameState.GAME)
        
        elif button_name == "back_from_game_choice":
            # 試合方法選択から戻る
            self.state_manager.change_state(GameState.MENU)
        
        # 采配モード処理
        elif button_name == "next_manage_play":
            # 次のプレイへ（采配モード）
            self.advance_game_manage()
        
        elif button_name == "skip_manage_inning":
            # イニング終了までスキップ（采配モード）
            self.skip_manage_to_inning_end()
        
        elif button_name == "skip_manage_game":
            # 試合スキップ確認ダイアログを表示
            if hasattr(self, 'game_manage_state'):
                self.game_manage_state['confirm_skip_game'] = True
        
        elif button_name == "confirm_skip_yes":
            # スキップ確認：はい
            if hasattr(self, 'game_manage_state'):
                self.game_manage_state['confirm_skip_game'] = False
                self.skip_manage_to_game_end()
        
        elif button_name == "confirm_skip_no":
            # スキップ確認：いいえ
            if hasattr(self, 'game_manage_state'):
                self.game_manage_state['confirm_skip_game'] = False
        
        elif button_name == "end_manage":
            # 采配終了、結果画面へ
            self.end_game_manage()
        
        # 采配モード：攻撃戦術
        elif button_name.startswith("tactic_pitcher_"):
            # 投手戦術（ボール先行、ストライク先行など）
            pitcher_tactic = button_name.replace("tactic_pitcher_", "")
            self.set_manage_pitcher_tactic(pitcher_tactic)
        elif button_name.startswith("tactic_"):
            tactic = button_name.replace("tactic_", "")
            self.set_manage_tactic(tactic)
            # 戦術を選択するだけで、「次の球」ボタンで進む
        
        # 采配モード：守備シフト
        elif button_name.startswith("shift_"):
            shift_type = button_name.replace("shift_", "")
            self.set_manage_defensive_shift(shift_type)
        
        # 采配モード：選手交代
        elif button_name == "substitution_pinch_hit":
            self._show_manage_substitution_dialog('pinch_hit')
        
        elif button_name == "substitution_pinch_run":
            self._show_manage_substitution_dialog('pinch_run')
        
        elif button_name == "substitution_pitcher":
            self._show_manage_substitution_dialog('pitcher')
        
        elif button_name == "substitution_defensive":
            self._show_manage_substitution_dialog('defensive')
        
        elif button_name.startswith("select_sub_"):
            # 選手交代確定
            idx = int(button_name.replace("select_sub_", ""))
            self._execute_manage_substitution(idx)
        
        elif button_name == "cancel_substitution":
            # 選手交代キャンセル
            if hasattr(self, 'game_manage_state'):
                self.game_manage_state['substitution_mode'] = None
                self.substitution_available_players = []
        
        # 試合観戦画面
        elif button_name == "next_play":
            # 次のプレイへ進む
            self.advance_game_watch()
        
        elif button_name == "skip_inning":
            # イニング終了までスキップ
            self.skip_to_inning_end()
        
        elif button_name == "skip_game":
            # 試合終了までスキップ
            self.skip_to_game_end()
        
        elif button_name == "end_watch":
            # 観戦終了、結果画面へ
            self.end_game_watch()
        
        # 視点切り替え
        elif button_name == "view_prev":
            view_name = self.renderer.cyber_field.cycle_view(-1)
            ToastManager.show(f"視点: {view_name}", "info", duration=1000)
        
        elif button_name == "view_next":
            view_name = self.renderer.cyber_field.cycle_view(1)
            ToastManager.show(f"視点: {view_name}", "info", duration=1000)
        
        # 投手交代ボタン（観戦画面）
        elif button_name == "change_pitcher":
            self._show_pitcher_change_dialog()
        
        # プレイログのスクロール
        elif button_name == "log_scroll_up":
            current = getattr(self, 'game_watch_log_scroll', 0)
            self.game_watch_log_scroll = max(0, current - 1)
        
        elif button_name == "log_scroll_down":
            game_watch_state = getattr(self, 'game_watch_state', {})
            play_log = game_watch_state.get('play_log', [])
            visible_lines = 10
            max_scroll = max(0, len(play_log) - visible_lines)
            current = getattr(self, 'game_watch_log_scroll', 0)
            self.game_watch_log_scroll = min(max_scroll, current + 1)
        
        elif button_name == "menu":
            self.state_manager.change_state(GameState.MENU)
        
        # オーダー設定
        elif button_name == "auto_lineup":
            self.auto_set_lineup()
            ToastManager.show("オーダーを自動設定しました", "success")
        
        elif button_name == "clear_lineup":
            self.clear_lineup()
        
        # タブ切り替え（オーダー画面）
        elif button_name == "tab_all":
            self.lineup_tab = "all"
            self.scroll_offset = 0
        
        elif button_name == "tab_batters":
            self.lineup_tab = "batters"
            self.scroll_offset = 0
        
        elif button_name == "tab_pitchers":
            self.lineup_tab = "pitchers"
            self.scroll_offset = 0
        
        # ドラフト
        elif button_name == "draft_player":
            self.draft_player()
        
        # 育成ドラフト
        elif button_name == "draft_ikusei_player":
            self.draft_developmental_player()  # 既存の関数を使用
        
        elif button_name == "skip_ikusei":
            # この巡をパス
            ToastManager.show("この巡をパスしました", "info")
            self.developmental_draft_round += 1
            if self.developmental_draft_round > 5:
                self._finish_developmental_draft()
        
        elif button_name == "finish_ikusei_draft":
            # 育成ドラフト終了 → FAへ
            self._finish_developmental_draft()
        
        # 選手詳細画面の軍別成績切り替え
        elif button_name.startswith("stats_level_") and self.state_manager.current_state == GameState.PLAYER_DETAIL:
            level = button_name.replace("stats_level_", "")
            self.player_detail_stats_level = level
        
        # 選手詳細画面の戻るボタン
        elif button_name == "back" and self.state_manager.current_state == GameState.PLAYER_DETAIL:
            self.selected_detail_player = None
            self.player_detail_scroll = 0
            self.player_detail_stats_level = 'first'  # リセット
            # 前の画面に戻る
            previous = getattr(self, '_previous_state', GameState.LINEUP)
            self.state_manager.change_state(previous)
        
        # FA
        elif button_name == "sign_fa":
            self.sign_fa_player()
        
        elif button_name == "next_season":
            self.start_new_season()
        
        # 試合結果
        elif button_name == "next_game":
            self.result_scroll = 0  # スクロールリセット
            self.state_manager.change_state(GameState.MENU)
        
        # 試合結果画面スクロール
        elif button_name == "result_scroll_up":
            self.result_scroll = max(0, self.result_scroll - 3)
        
        elif button_name == "result_scroll_down":
            self.result_scroll += 3
        
        # 設定
        elif button_name.startswith("resolution_"):
            res_str = button_name.split("_")[1]
            width, height = map(int, res_str.split("x"))
            settings.set_resolution(width, height)
            set_screen_size(width, height)
            
            if not settings.fullscreen:
                self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
                self.renderer.screen = self.screen
            
            ToastManager.show(f"解像度を {width}x{height} に変更", "info")
        
        elif button_name == "toggle_fullscreen":
            settings.toggle_fullscreen()
            if settings.fullscreen:
                self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                actual_size = self.screen.get_size()
                set_screen_size(actual_size[0], actual_size[1])
            else:
                width, height = settings.get_resolution()
                self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
            self.renderer.screen = self.screen
        
        elif button_name == "toggle_sound":
            settings.toggle_sound()
            status = "ON" if settings.sound_enabled else "OFF"
            ToastManager.show(f"サウンド: {status}", "info")
        
        # 画質設定
        elif button_name.startswith("quality_"):
            quality = button_name.replace("quality_", "")
            settings.graphics_quality = quality
            quality_names = {"low": "低", "medium": "中", "high": "高"}
            ToastManager.show(f"画質を {quality_names.get(quality, quality)} に変更", "info")
        
        # ========================================
        # 試合中の戦略操作
        # ========================================
        elif button_name == "strategy_bunt":
            ToastManager.show("バント指示", "info")
            if self.game_simulator:
                self.game_simulator.next_tactic = "bunt"
        
        elif button_name == "strategy_squeeze":
            ToastManager.show("スクイズ指示", "info")
            if self.game_simulator:
                self.game_simulator.next_tactic = "squeeze"
        
        elif button_name == "strategy_steal":
            ToastManager.show("盗塁指示", "info")
            if self.game_simulator:
                self.game_simulator.next_tactic = "steal"
        
        elif button_name == "strategy_hit_run":
            ToastManager.show("エンドラン指示", "info")
            if self.game_simulator:
                self.game_simulator.next_tactic = "hit_and_run"
        
        elif button_name == "strategy_pinch_hit":
            # 代打選手候補を表示
            self.game_strategy_mode = "pinch_hit"
            self.strategy_candidates = self._get_pinch_hit_candidates()
            if not self.strategy_candidates:
                ToastManager.show("代打候補がいません", "warning")
                self.game_strategy_mode = None
        
        elif button_name == "strategy_pinch_run":
            # 代走選手候補を表示
            self.game_strategy_mode = "pinch_run"
            self.strategy_candidates = self._get_pinch_run_candidates()
            if not self.strategy_candidates:
                ToastManager.show("代走候補がいません", "warning")
                self.game_strategy_mode = None
        
        elif button_name == "strategy_intentional_walk":
            ToastManager.show("敬遠指示", "info")
            if self.game_simulator:
                self.game_simulator.next_tactic = "intentional_walk"
        
        elif button_name == "strategy_pitch_out":
            ToastManager.show("ピッチアウト指示", "info")
            if self.game_simulator:
                self.game_simulator.next_tactic = "pitch_out"
        
        elif button_name == "strategy_infield_in":
            ToastManager.show("前進守備指示", "info")
            if self.game_simulator:
                self.game_simulator.defensive_shift = "infield_in"
        
        elif button_name == "strategy_pitching_change":
            # 継投候補を表示
            self.game_strategy_mode = "pitching_change"
            self.strategy_candidates = self._get_relief_pitcher_candidates()
            if not self.strategy_candidates:
                ToastManager.show("継投候補がいません", "warning")
                self.game_strategy_mode = None
        
        elif button_name == "strategy_mound_visit":
            ToastManager.show("マウンド訪問（投手の疲労回復）", "info")
            if self.game_simulator:
                # 簡易的に球数リセット
                self.game_simulator.home_pitcher_stats['pitch_count'] = max(0, 
                    self.game_simulator.home_pitcher_stats.get('pitch_count', 0) - 10)
        
        elif button_name == "cancel_strategy":
            self.game_strategy_mode = None
            self.strategy_candidates = []
        
        elif button_name.startswith("select_candidate_"):
            idx = int(button_name.replace("select_candidate_", ""))
            if self.strategy_candidates and idx < len(self.strategy_candidates):
                self._execute_strategy_substitution(idx)
        
        elif button_name == "game_auto_play":
            # 自動再生（試合を高速進行）
            if self.game_simulator:
                self._run_game_simulation()
        
        elif button_name == "game_next_play":
            # 1プレイ進める
            ToastManager.show("次のプレイへ", "info")
            # 実際の実装では1打席分のシミュレーションを実行
        
        elif button_name in ["speed_slow", "speed_normal", "speed_fast"]:
            speed_map = {"speed_slow": 1, "speed_normal": 2, "speed_fast": 5}
            self.game_speed = speed_map.get(button_name, 1)
            ToastManager.show(f"速度: {self.game_speed}x", "info")
        
        # 設定タブ切り替え
        elif button_name.startswith("settings_tab_"):
            self.settings_tab = button_name.replace("settings_tab_", "")
            self.settings_scroll = 0  # タブ切り替え時にスクロールリセット
        
        # ゲームルール設定のトグル
        elif button_name.startswith("toggle_"):
            rule_key = button_name.replace("toggle_", "")
            if hasattr(settings.game_rules, rule_key):
                current_value = getattr(settings.game_rules, rule_key)
                setattr(settings.game_rules, rule_key, not current_value)
                settings.save_settings()
                status = "ON" if not current_value else "OFF"
                rule_names = {
                    "central_dh": "セリーグDH制",
                    "pacific_dh": "パリーグDH制",
                    "interleague_dh": "交流戦DH（ホームルール）",
                    "enable_interleague": "交流戦",
                    "enable_climax_series": "クライマックスシリーズ",
                    "enable_allstar": "オールスター",
                    "enable_spring_camp": "春季キャンプ",
                    "enable_tiebreaker": "タイブレーク制度",
                    "unlimited_foreign": "外国人枠無制限",
                }
                rule_name = rule_names.get(rule_key, rule_key)
                ToastManager.show(f"{rule_name}: {status}", "info")
        
        # ゲームルール設定の数値変更
        elif button_name.startswith("set_"):
            parts = button_name.split("_")
            # set_rule_key_value 形式
            value = int(parts[-1])
            key = "_".join(parts[1:-1])
            if hasattr(settings.game_rules, key):
                setattr(settings.game_rules, key, value)
                settings.save_settings()
                key_names = {
                    "regular_season_games": "レギュラーシーズン試合数",
                    "interleague_games": "交流戦試合数",
                    "extra_innings_limit": "延長上限",
                    "foreign_player_limit": "外国人枠",
                    "roster_limit": "一軍登録枠",
                    "farm_roster_limit": "育成枠上限",
                    "spring_camp_days": "キャンプ日数",
                }
                key_name = key_names.get(key, key)
                if value == 0:
                    if "foreign" in key or "farm" in key or "innings" in key:
                        display_value = "無制限"
                    else:
                        display_value = str(value)
                else:
                    display_value = str(value)
                ToastManager.show(f"{key_name}: {display_value}", "info")
        
        # 戻る
        elif button_name == "back":
            if self.state_manager.current_state == GameState.SETTINGS:
                # 設定画面からは前の画面に戻る（メニューかタイトル）
                # ゲーム開始時の設定画面からはペナント開始
                if getattr(self, '_pending_pennant_start', False):
                    self._pending_pennant_start = False
                    self.start_pennant_mode()
                elif self.state_manager.previous_state and self.state_manager.previous_state != GameState.SETTINGS:
                    self.state_manager.change_state(self.state_manager.previous_state)
                elif self.state_manager.player_team:
                    self.state_manager.change_state(GameState.MENU)
                else:
                    self.state_manager.change_state(GameState.TITLE)
            elif self.state_manager.current_state == GameState.STANDINGS:
                self.state_manager.change_state(GameState.MENU)
            elif self.state_manager.current_state == GameState.DRAFT:
                # ドラフトを終了して育成ドラフトへ
                ToastManager.show("支配下ドラフト終了", "info")
                self.generate_developmental_prospects()
                self.state_manager.change_state(GameState.DEVELOPMENTAL_DRAFT)
            elif self.state_manager.current_state in [GameState.DEVELOPMENTAL_DRAFT, GameState.IKUSEI_DRAFT]:
                # 育成ドラフト終了 → FA画面へ
                ToastManager.show("育成ドラフト終了", "info")
                self.generate_foreign_free_agents()
                self.state_manager.change_state(GameState.FREE_AGENT)
            elif self.state_manager.current_state == GameState.ROSTER_MANAGEMENT:
                self.state_manager.change_state(GameState.MENU)
            else:
                self.state_manager.change_state(GameState.MENU)
        
        # オーダー画面から選手詳細を表示
        elif button_name.startswith("order_detail_"):
            player_idx = int(button_name.replace("order_detail_", ""))
            if player_idx < len(self.state_manager.player_team.players):
                self.selected_detail_player = self.state_manager.player_team.players[player_idx]
                self.player_detail_scroll = 0
                self._previous_state = self.state_manager.current_state
                self.state_manager.change_state(GameState.PLAYER_DETAIL)
        
        # 登録管理画面から選手詳細を表示
        elif button_name.startswith("roster_detail_"):
            player_idx = int(button_name.replace("roster_detail_", ""))
            if player_idx < len(self.state_manager.player_team.players):
                self.selected_detail_player = self.state_manager.player_team.players[player_idx]
                self.player_detail_scroll = 0
                self._previous_state = self.state_manager.current_state
                self.state_manager.change_state(GameState.PLAYER_DETAIL)
        
        # ドラフト画面から選手詳細を表示
        elif button_name.startswith("draft_detail_"):
            player_idx = int(button_name.replace("draft_detail_", ""))
            if player_idx < len(self.state_manager.draft_prospects):
                self.selected_detail_player = self.state_manager.draft_prospects[player_idx]
                self.player_detail_scroll = 0
                self._previous_state = self.state_manager.current_state
                self.state_manager.change_state(GameState.PLAYER_DETAIL)
        
        # 育成ドラフト画面から選手詳細を表示
        elif button_name.startswith("ikusei_detail_"):
            player_idx = int(button_name.replace("ikusei_detail_", ""))
            dev_prospects = getattr(self, 'developmental_prospects', [])
            if player_idx < len(dev_prospects):
                self.selected_detail_player = dev_prospects[player_idx]
                self.player_detail_scroll = 0
                self._previous_state = self.state_manager.current_state
                self.state_manager.change_state(GameState.PLAYER_DETAIL)
    
    def update(self):
        """ゲーム状態更新"""
        # エラーメッセージタイマーを減らす
        if self.error_message_timer > 0:
            self.error_message_timer -= 1
            if self.error_message_timer <= 0:
                self.error_message = ""
        
        # 打球トラッキング表示更新（采配モード）- 守備アニメーションなし
        if self.state_manager.current_state == GameState.GAME_MANAGE:
            state = getattr(self, 'game_manage_state', {})
            # トラッキングデータの表示フレーム更新（表示用のみ）
            if state.get('trajectory'):
                trajectory_len = len(state['trajectory'])
                current_frame = state.get('animation_frame', 0)
                
                # すでに最後のフレームに達している場合
                if current_frame >= trajectory_len - 1:
                    # アニメーション完了処理
                    if not state.get('animation_complete'):
                        state['animation_complete'] = True
                        state['animation_frame'] = trajectory_len - 1
                    
                    # 結果表示タイマーを減らす
                    if state.get('result_display_timer', 0) > 0:
                        state['result_display_timer'] -= 1
                    elif state.get('waiting_for_animation'):
                        # タイマー終了後、保留中のアクションを実行
                        self._execute_pending_action(state)
                else:
                    # フレームを進める
                    state['anim_counter'] = state.get('anim_counter', 0) + 1
                    if state['anim_counter'] >= 3:
                        state['anim_counter'] = 0
                        state['animation_frame'] = current_frame + 1
        
        # 打球トラッキング表示更新（観戦モード）
        if self.state_manager.current_state == GameState.GAME_WATCH:
            state = getattr(self, 'game_watch_state', {})
            if state.get('trajectory'):
                trajectory_len = len(state['trajectory'])
                current_frame = state.get('animation_frame', 0)
                
                # すでに最後のフレームに達している場合
                if current_frame >= trajectory_len - 1:
                    if not state.get('animation_complete'):
                        state['animation_complete'] = True
                        state['animation_frame'] = trajectory_len - 1
                    
                    # 結果表示タイマーを減らす
                    if state.get('result_display_timer', 0) > 0:
                        state['result_display_timer'] -= 1
                    elif state.get('waiting_for_animation'):
                        # タイマー終了後、状態をクリア
                        state['waiting_for_animation'] = False
                        state['animation_complete'] = False
                        state['trajectory'] = []
                        state['ball_tracking'] = None
                        state['animation_frame'] = 0
                        state['anim_counter'] = 0
                else:
                    # フレームを進める
                    state['anim_counter'] = state.get('anim_counter', 0) + 1
                    if state['anim_counter'] >= 3:
                        state['anim_counter'] = 0
                        state['animation_frame'] = current_frame + 1
        
        if self.state_manager.current_state == GameState.GAME and self.state_manager.current_opponent:
            # 試合シミュレーション
            pygame.time.wait(1500)
            
            next_game = self.schedule_manager.get_next_game_for_team(self.state_manager.player_team.name)
            if next_game:
                is_home = next_game.home_team_name == self.state_manager.player_team.name
                
                if is_home:
                    self.game_simulator = GameSimulator(self.state_manager.player_team, self.state_manager.current_opponent)
                else:
                    self.game_simulator = GameSimulator(self.state_manager.current_opponent, self.state_manager.player_team)
                
                self.game_simulator.simulate_game()
                
                self.schedule_manager.complete_game(next_game, self.game_simulator.home_score, self.game_simulator.away_score)
                
                # 育成メニューによる経験値付与（試合ごとに実行）
                self._apply_training_after_game()
                
                # ニュースに試合結果を追加
                player_team = self.state_manager.player_team
                home_score = self.game_simulator.home_score
                away_score = self.game_simulator.away_score
                
                if is_home:
                    opponent_name = self.state_manager.current_opponent.name
                    if home_score > away_score:
                        self.add_news(f"vs {opponent_name} {home_score}-{away_score} 勝利！")
                    elif home_score < away_score:
                        self.add_news(f"vs {opponent_name} {home_score}-{away_score} 敗戦")
                    else:
                        self.add_news(f"vs {opponent_name} {home_score}-{away_score} 引き分け")
                else:
                    opponent_name = self.state_manager.current_opponent.name
                    if away_score > home_score:
                        self.add_news(f"@ {opponent_name} {away_score}-{home_score} 勝利！")
                    elif away_score < home_score:
                        self.add_news(f"@ {opponent_name} {away_score}-{home_score} 敗戦")
                    else:
                        self.add_news(f"@ {opponent_name} {away_score}-{home_score} 引き分け")
                
                # 未保存の変更フラグを立てる
                self.has_unsaved_changes = True
                
                self.state_manager.change_state(GameState.RESULT)
    
    def draw(self):
        """描画"""
        state = self.state_manager.current_state
        
        if state == GameState.TITLE:
            self.buttons = self.renderer.draw_title_screen(self.show_title_start_menu)
        
        elif state == GameState.NEW_GAME_SETUP:
            self.buttons = self.renderer.draw_new_game_setup_screen(
                self.settings,
                self.new_game_setup_state
            )
        
        elif state == GameState.SETTINGS:
            self.buttons = self.renderer.draw_settings_screen(settings, self.settings_tab, self.settings_scroll)
        
        elif state == GameState.DIFFICULTY_SELECT:
            self.buttons = self.renderer.draw_difficulty_screen(self.state_manager.difficulty)
        
        elif state == GameState.TEAM_SELECT:
            self.buttons = self.renderer.draw_team_select_screen(
                self.state_manager.central_teams,
                self.state_manager.pacific_teams,
                self.custom_team_names,
                self.preview_team_name,
                self.team_preview_scroll
            )
        
        elif state == GameState.TEAM_EDIT:
            self.buttons = self.renderer.draw_team_edit_screen(
                self.state_manager.all_teams,
                self.editing_team_idx,
                self.team_name_input,
                self.custom_team_names
            )
        
        elif state == GameState.TEAM_CREATE:
            self.buttons = self.renderer.draw_team_create_screen(
                self.new_team_name,
                self.new_team_league,
                self.new_team_color_idx,
                self.new_team_gen_mode
            )
        
        elif state == GameState.MENU:
            self.buttons = self.renderer.draw_menu_screen(
                self.state_manager.player_team,
                self.state_manager.current_year,
                self.schedule_manager,
                self.news_list,
                self.state_manager.central_teams,
                self.state_manager.pacific_teams
            )
        
        elif state == GameState.LINEUP:
            # タブに応じたフィルタ指定
            if self.lineup_tab == "pitchers":
                selected_position = "pitcher"
            elif self.lineup_tab == "batters":
                selected_position = "batters"
            else:
                selected_position = "all"
            
            self.buttons = self.renderer.draw_lineup_screen(
                self.state_manager.player_team,
                self.scroll_offset,
                self.dragging_player_idx,
                self.drag_pos,
                self.lineup_roster_tab,
                self.dragging_position_slot,
                self.position_drag_pos,
                self.lineup_edit_mode,
                self.lineup_selected_player_idx,
                self.lineup_selected_slot,
                self.lineup_selected_source,
                self.lineup_swap_mode,
                self.position_selected_slot,
                self.batting_order_selected_slot,
                self.roster_position_selected_slot
            )
            # ドロップゾーン情報を保存
            if "_drop_zones" in self.buttons:
                self.drop_zones = self.buttons.pop("_drop_zones")
        
        elif state == GameState.PITCHER_ORDER:
            self.buttons = self.renderer.draw_pitcher_order_screen(
                self.state_manager.player_team,
                self.pitcher_order_tab,
                self.selected_rotation_slot,
                self.selected_relief_slot,
                self.pitcher_scroll
            )
        
        elif state == GameState.BENCH_SETTING:
            self.buttons = self.renderer.draw_bench_setting_screen(
                self.state_manager.player_team,
                self.bench_setting_tab,
                self.bench_scroll
            )
        
        elif state == GameState.SCHEDULE_VIEW:
            self.buttons = self.renderer.draw_schedule_screen(
                self.schedule_manager,
                self.state_manager.player_team,
                self.scroll_offset,
                self.selected_game_idx
            )
        
        elif state == GameState.GAME:
            # 試合状態を構築
            game_state = {}
            if self.game_simulator:
                game_state = {
                    'inning': self.game_simulator.inning,
                    'is_top': getattr(self.game_simulator, 'is_top_inning', True),
                    'outs': getattr(self.game_simulator, 'current_outs', 0),
                    'runners': getattr(self.game_simulator, 'current_runners', [False, False, False]),
                    'home_score': self.game_simulator.home_score,
                    'away_score': self.game_simulator.away_score,
                    'pitch_count': getattr(self.game_simulator, 'home_pitcher_stats', {}).get('pitch_count', 0),
                }
                # 現在の打者・投手
                if hasattr(self.game_simulator, 'current_batter_idx'):
                    batting_team = self.game_simulator.away_team if game_state['is_top'] else self.game_simulator.home_team
                    batter_idx = self.game_simulator.current_batter_idx
                    if 0 <= batter_idx < len(batting_team.current_lineup):
                        player_idx = batting_team.current_lineup[batter_idx]
                        if 0 <= player_idx < len(batting_team.players):
                            game_state['current_batter'] = batting_team.players[player_idx]
                
                if hasattr(self.game_simulator, 'current_pitcher_idx'):
                    pitching_team = self.game_simulator.home_team if game_state['is_top'] else self.game_simulator.away_team
                    pitcher_idx = self.game_simulator.current_pitcher_idx
                    if 0 <= pitcher_idx < len(pitching_team.players):
                        game_state['current_pitcher'] = pitching_team.players[pitcher_idx]
            
            self.buttons = self.renderer.draw_game_screen(
                self.state_manager.player_team,
                self.state_manager.current_opponent,
                game_state,
                self.game_strategy_mode,
                self.strategy_candidates
            )
        
        elif state == GameState.GAME_CHOICE:
            # 試合方法選択画面
            self.buttons = self.renderer.draw_game_choice_screen(
                self.state_manager.player_team,
                self.state_manager.current_opponent
            )
        
        elif state == GameState.GAME_MANAGE:
            # 采配モード画面
            game_manage_state = getattr(self, 'game_manage_state', {})
            substitution_mode = game_manage_state.get('substitution_mode')
            
            if substitution_mode:
                # 選手交代ダイアログを表示
                available = getattr(self, 'substitution_available_players', [])
                self.buttons = self.renderer.draw_game_manage_screen(
                    self.state_manager.player_team,
                    self.state_manager.current_opponent,
                    game_manage_state
                )
                sub_buttons = self.renderer.draw_substitution_dialog(
                    substitution_mode,
                    available,
                    game_manage_state
                )
                self.buttons.update(sub_buttons)
            else:
                self.buttons = self.renderer.draw_game_manage_screen(
                    self.state_manager.player_team,
                    self.state_manager.current_opponent,
                    game_manage_state
                )
        
        elif state == GameState.RESULT:
            self.buttons = self.renderer.draw_result_screen(
                self.game_simulator,
                self.result_scroll
            )
        
        elif state == GameState.STANDINGS:
            self.buttons = self.renderer.draw_standings_screen(
                self.state_manager.central_teams,
                self.state_manager.pacific_teams,
                self.state_manager.player_team,
                self.standings_tab,
                self.scroll_offset,
                getattr(self, 'stats_team_level_filter', 'first')  # デフォルトは一軍
            )
        
        elif state == GameState.DRAFT:
            draft_msgs = getattr(self, 'draft_messages', [])
            draft_rnd = getattr(self, 'draft_round', 1)
            draft_scroll = getattr(self, 'draft_scroll', 0)
            self.buttons = self.renderer.draw_draft_screen(
                self.state_manager.draft_prospects,
                self.state_manager.selected_draft_pick if self.state_manager.selected_draft_pick is not None else -1,
                draft_rnd,
                draft_msgs,
                draft_scroll
            )
        
        elif state == GameState.IKUSEI_DRAFT or state == GameState.DEVELOPMENTAL_DRAFT:
            # 育成ドラフト画面（2つのステート名を統一）
            dev_msgs = getattr(self, 'developmental_draft_messages', [])
            dev_rnd = getattr(self, 'developmental_draft_round', 1)
            ikusei_scroll = getattr(self, 'ikusei_draft_scroll', 0)
            self.buttons = self.renderer.draw_ikusei_draft_screen(
                self.developmental_prospects,
                self.selected_developmental_idx,
                dev_rnd,
                dev_msgs,
                ikusei_scroll
            )
        
        elif state == GameState.PLAYER_DETAIL:
            # 選手詳細画面
            player = self.selected_detail_player
            if player:
                self.buttons = self.renderer.draw_player_detail_screen(
                    player,
                    self.player_detail_scroll,
                    stats_level=getattr(self, 'player_detail_stats_level', 'first')
                )
        
        elif state == GameState.FREE_AGENT:
            self.buttons = self.renderer.draw_free_agent_screen(
                self.state_manager.player_team,
                self.state_manager.foreign_free_agents,
                self.selected_fa_idx
            )
        
        elif state == GameState.TEAM_STATS:
            self.buttons = self.renderer.draw_team_stats_screen(
                self.state_manager.player_team,
                self.state_manager.current_year
            )
        
        elif state == GameState.TRAINING:
            # Initialize training menus dict if not present
            if not hasattr(self, 'training_selected_menus'):
                self.training_selected_menus = {}
            self.buttons = self.renderer.draw_training_screen(
                self.state_manager.player_team,
                self.selected_training_player_idx,
                0,  # training_points is no longer used
                getattr(self, 'selected_training_idx', -1),
                getattr(self, 'training_player_scroll', 0),
                getattr(self, 'training_filter_pos', None),
                self.training_selected_menus,
                0  # training_days_remaining
            )
        
        elif state == GameState.PENNANT_CAMP:
            # Spring camp screen - improved version with more state
            self.selected_spring_player_idx = getattr(self, 'selected_spring_player_idx', -1)
            self.spring_filter_pos = getattr(self, 'spring_filter_pos', None)
            # Initialize selected menus dict if not present
            if not hasattr(self, 'spring_selected_menus'):
                self.spring_selected_menus = {}
            spring_selected_menus = self.spring_selected_menus
            # Determine selected training for UI: prefer per-player selection if present
            self.selected_spring_training_idx = getattr(self, 'selected_spring_training_idx', -1)
            if self.selected_spring_player_idx is not None and self.selected_spring_player_idx >= 0:
                per_player_idx = spring_selected_menus.get(self.selected_spring_player_idx, None)
                if per_player_idx is not None:
                    self.selected_spring_training_idx = per_player_idx
            self.spring_player_scroll = getattr(self, 'spring_player_scroll', 0)
            self.spring_hovered_training = getattr(self, 'spring_hovered_training', -1)
            self.spring_camp_day = getattr(self, 'spring_camp_day', 1)
            self.spring_camp_max_days = getattr(self, 'spring_camp_max_days', 30)
            self.buttons = self.renderer.draw_spring_camp_screen(
                self.state_manager.player_team,
                self.selected_spring_player_idx,
                self.spring_filter_pos,
                self.selected_spring_training_idx,
                self.spring_player_scroll,
                self.spring_hovered_training,
                self.spring_camp_day,
                self.spring_camp_max_days,
                spring_selected_menus
            )
        
        elif state == GameState.MANAGEMENT:
            # 財務情報を取得
            finances = None
            if self.pennant_manager and self.state_manager.player_team:
                finances = self.pennant_manager.team_finances.get(self.state_manager.player_team.name)
            self.buttons = self.renderer.draw_management_screen(
                self.state_manager.player_team,
                finances,
                self.management_tab
            )
        
        elif state == GameState.ROSTER_MANAGEMENT:
            roster_tab = getattr(self, 'roster_tab', 'order')
            
            # タブに応じたスクロールオフセットを設定
            if roster_tab == 'farm':
                scroll_data = {
                    'first': self.farm_scroll_first,
                    'second': self.farm_scroll_second,
                    'third': self.farm_scroll_third
                }
            elif roster_tab == 'order':
                scroll_data = self.order_scroll_batters
            else:
                scroll_data = self.scroll_offset
            
            self.buttons = self.renderer.draw_roster_management_screen(
                self.state_manager.player_team,
                roster_tab,
                self.lineup_selected_player_idx,  # 選択中の選手インデックス
                scroll_data,
                self.dragging_player_idx,
                self.drag_pos,
                getattr(self, 'order_sub_tab', 'batter'),  # 野手/投手サブタブ
                getattr(self.renderer, '_second_pitcher_scroll', getattr(self, 'pitcher_scroll', 0)),  # 投手リストスクロール（rendererが管理している場合は優先）
                getattr(self, 'selected_rotation_slot', -1),  # 選択中のローテスロット
                getattr(self, 'selected_relief_slot', -1),  # 選択中の中継ぎスロット
                getattr(self, 'roster_position_selected_slot', -1)  # 選択中のポジションスロット
            )
            # ドロップゾーン情報を保存
            if "_drop_zones" in self.buttons:
                self.drop_zones = self.buttons.pop("_drop_zones")
        
        # ペナントモード画面
        elif state == GameState.PENNANT_HOME:
            self.buttons = self.pennant_screens.draw_pennant_home(
                self.pennant_manager,
                self.state_manager.player_team
            )
        
        elif state == GameState.PENNANT_DRAFT:
            self.buttons = self.pennant_screens.draw_draft_screen(
                self.pennant_manager,
                self.state_manager.player_team,
                self.pennant_draft_picks,
                self.scroll_offset
            )
        
        elif state == GameState.PENNANT_CAMP:
            self.buttons = self.pennant_screens.draw_spring_camp(
                self.pennant_manager,
                self.state_manager.player_team,
                self.pennant_camp_results,
                self.camp_daily_result,
                self.camp_training_menu
            )
        
        elif state == GameState.PENNANT_FALL_CAMP:
            # 秋季キャンプ画面 - 状態変数を初期化
            self.selected_fall_player_idx = getattr(self, 'selected_fall_player_idx', -1)
            self.fall_filter_pos = getattr(self, 'fall_filter_pos', None)
            if not hasattr(self, 'fall_selected_menus'):
                self.fall_selected_menus = {}
            self.selected_fall_training_idx = getattr(self, 'selected_fall_training_idx', -1)
            if self.selected_fall_player_idx is not None and self.selected_fall_player_idx >= 0:
                per_player_idx = self.fall_selected_menus.get(self.selected_fall_player_idx, None)
                if per_player_idx is not None:
                    self.selected_fall_training_idx = per_player_idx
            self.fall_player_scroll = getattr(self, 'fall_player_scroll', 0)
            self.fall_hovered_training = getattr(self, 'fall_hovered_training', -1)
            self.fall_camp_day = getattr(self, 'fall_camp_day', 1)
            self.fall_camp_max_days = getattr(self, 'fall_camp_max_days', 14)
            
            # 秋季キャンプ参加選手をフィルタ（総合力250以下）
            if not self.fall_camp_players and self.state_manager.player_team:
                all_players = self.state_manager.player_team.players
                self.fall_camp_players = [p for p in all_players if p.overall_rating <= 250]
            
            self.buttons = self.renderer.draw_fall_camp_screen(
                self.state_manager.player_team,
                self.selected_fall_player_idx,
                self.fall_filter_pos,
                self.selected_fall_training_idx,
                self.fall_player_scroll,
                self.fall_hovered_training,
                self.fall_camp_day,
                self.fall_camp_max_days,
                self.fall_selected_menus,
                250  # overall_threshold
            )
        
        elif state == GameState.PENNANT_CS:
            central_sorted = sorted(self.state_manager.central_teams, key=lambda t: (-t.win_rate, -t.wins))
            pacific_sorted = sorted(self.state_manager.pacific_teams, key=lambda t: (-t.win_rate, -t.wins))
            self.buttons = self.pennant_screens.draw_climax_series(
                self.pennant_manager,
                central_sorted,
                pacific_sorted
            )
        
        # エラーメッセージを右下に表示
        if self.error_message and self.error_message_timer > 0:
            self._draw_error_message()
        
        # 確認ダイアログを表示（セーブ確認など）
        if self.show_confirm_dialog:
            self._draw_confirm_dialog()
    
    def _draw_confirm_dialog(self):
        """確認ダイアログを描画"""
        width = self.screen.get_width()
        height = self.screen.get_height()
        
        # 半透明オーバーレイ
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # Get custom message if set
        custom_msg = getattr(self, 'confirm_message', None)
        
        # ダイアログボックス
        dialog_w = 450
        # If there's a custom message, allow the dialog height to grow based on lines
        if custom_msg:
            lines = custom_msg.split('\n')
            # Count only non-empty lines for spacing calculation
            non_empty = [ln for ln in lines if ln.strip()]
            # Start area (title + top padding) + per-line height + bottom area for buttons
            needed_h = 55 + len(non_empty) * 25 + 80
            dialog_h = max(220, needed_h)
        else:
            dialog_h = 180

        dialog_x = (width - dialog_w) // 2
        dialog_y = (height - dialog_h) // 2
        
        from ui_pro import Colors, fonts, Button
        
        # ダイアログ背景
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
        pygame.draw.rect(self.screen, Colors.BG_CARD, dialog_rect, border_radius=12)
        pygame.draw.rect(self.screen, Colors.WARNING, dialog_rect, 2, border_radius=12)
        
        # タイトル
        title_surf = fonts.h2.render("確認", True, Colors.WARNING)
        title_rect = title_surf.get_rect(centerx=width // 2, top=dialog_y + 20)
        self.screen.blit(title_surf, title_rect)
        
        # メッセージ
        if custom_msg:
            # Split custom message by newlines and render each line
            lines = custom_msg.split('\n')
            y = dialog_y + 55
            for line in lines:
                if line.strip():
                    msg_surf = fonts.small.render(line, True, Colors.TEXT_PRIMARY)
                    msg_rect = msg_surf.get_rect(centerx=width // 2, top=y)
                    self.screen.blit(msg_surf, msg_rect)
                    y += 25
                else:
                    # add a blank line spacing
                    y += 20
            # place buttons below the rendered text with padding
            btn_y = y + 15
        else:
            msg_text = "セーブしていないデータがあります。"
            msg_surf = fonts.body.render(msg_text, True, Colors.TEXT_PRIMARY)
            msg_rect = msg_surf.get_rect(centerx=width // 2, top=dialog_y + 60)
            self.screen.blit(msg_surf, msg_rect)
            
            msg2_text = "タイトルに戻りますか？"
            msg2_surf = fonts.body.render(msg2_text, True, Colors.TEXT_SECONDARY)
            msg2_rect = msg2_surf.get_rect(centerx=width // 2, top=dialog_y + 85)
            self.screen.blit(msg2_surf, msg2_rect)
            btn_y = dialog_y + 125
        
        # ボタン（ダイアログ幅に合わせて中央配置）
        btn_spacing = 20
        btn_width = 120
        btn_height = 40
        total_btn_width = btn_width * 2 + btn_spacing
        btn_start_x = dialog_x + (dialog_w - total_btn_width) // 2
        
        # ボタンがダイアログ内に収まるように調整
        max_btn_y = dialog_y + dialog_h - btn_height - 15
        btn_y = min(btn_y, max_btn_y)
        
        yes_btn = Button(btn_start_x, btn_y, btn_width, btn_height, "はい", "danger", font=fonts.body)
        yes_btn.draw(self.screen)
        self.buttons["confirm_yes"] = yes_btn
        
        no_btn = Button(btn_start_x + btn_width + btn_spacing, btn_y, btn_width, btn_height, "いいえ", "outline", font=fonts.body)
        no_btn.draw(self.screen)
        self.buttons["confirm_no"] = no_btn
    
    def _show_error(self, message: str):
        """エラーメッセージを表示"""
        self.error_message = message
        self.error_message_timer = 180  # 約3秒（60FPS想定）
    
    def _draw_error_message(self):
        """エラーメッセージを右下に描画"""
        from ui_pro import Colors, fonts
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        
        # メッセージボックス
        padding = 15
        msg_surf = fonts.body.render(self.error_message, True, Colors.TEXT_PRIMARY)
        box_w = msg_surf.get_width() + padding * 2
        box_h = msg_surf.get_height() + padding * 2
        box_x = width - box_w - 20
        box_y = height - box_h - 20
        
        # 背景（半透明の赤）
        box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
        pygame.draw.rect(self.screen, (60, 20, 20), box_rect, border_radius=8)
        pygame.draw.rect(self.screen, Colors.DANGER, box_rect, 2, border_radius=8)
        
        # テキスト
        self.screen.blit(msg_surf, (box_x + padding, box_y + padding))
    
    # ========================================
    # ペナントモード メソッド
    # ========================================
    def start_pennant_mode(self):
        """ペナントモード開始（春季キャンプから）"""
        from settings_manager import settings
        
        self.pennant_manager = PennantManager(max_years=30)
        self.pennant_manager.initialize_pennant(
            self.state_manager.all_teams,
            self.state_manager.player_team
        )
        
        # 全チームのオーダーを自動設定（野手打順・投手ローテ・ベンチ）
        for team in self.state_manager.all_teams:
            # 野手オーダーを自動設定（空白打順を作らない）
            self.auto_set_lineup_for_team(team)
            # 投手陣を自動設定
            team.auto_set_pitching_staff()
            # ベンチを自動設定
            if hasattr(team, 'auto_set_bench'):
                team.auto_set_bench()
        
        # キャンプ設定を確認
        if settings.game_rules.enable_spring_camp:
            # 春季キャンプフェーズから開始
            self.pennant_manager.current_phase = PennantPhase.SPRING_CAMP
            
            # キャンプを開始（設定から日数取得、チーム情報も渡す）
            camp_days = settings.game_rules.spring_camp_days
            self.pennant_manager.start_spring_camp(
                total_days=camp_days,
                team=self.state_manager.player_team
            )
            
            # キャンプ関連変数を初期化
            self.pennant_camp_results = None
            self.camp_daily_result = None
            self.camp_training_menu = {
                "batting": 3, "pitching": 3, "fielding": 3, "physical": 3, "rest": 3, "mental": 3
            }
            
            # 参加選手のgrowthとplayer_statusを初期化（キャンプ開始時）
            from player_development import PlayerGrowth, PlayerStatus
            for player in self.state_manager.player_team.players:
                if not hasattr(player, 'growth') or player.growth is None:
                    player.growth = PlayerGrowth(potential=getattr(player, 'potential', 5))
                if not hasattr(player, 'player_status') or player.player_status is None:
                    player.player_status = PlayerStatus()
                # キャンプ開始時に疲労をリセット
                player.player_status.fatigue = 0
                player.player_status.motivation = 70
            
            self.state_manager.change_state(GameState.PENNANT_CAMP)
            
            # キャンプ地情報を表示
            camp_state = self.pennant_manager.spring_camp_state
            camp_loc = camp_state.camp_location if camp_state else "沖縄"
            ToastManager.show(f"{self.state_manager.current_year}年 春季キャンプ開始！（{camp_loc}・{camp_days}日間）", "success")
        else:
            # キャンプをスキップしてメニューへ
            self.pennant_manager.current_phase = PennantPhase.REGULAR_SEASON
            self.state_manager.change_state(GameState.MENU)
            ToastManager.show(f"{self.state_manager.current_year}年 シーズン開始！", "success")
    
    def advance_camp_day(self):
        """キャンプを1日進める"""
        if not self.pennant_manager or not self.pennant_manager.spring_camp_state:
            return
        
        # トレーニングメニューを設定
        if self.camp_training_menu:
            self.pennant_manager.set_camp_training_menu(
                batting=self.camp_training_menu.get("batting", 3),
                pitching=self.camp_training_menu.get("pitching", 3),
                fielding=self.camp_training_menu.get("fielding", 3),
                physical=self.camp_training_menu.get("physical", 3),
                rest=self.camp_training_menu.get("rest", 3)
            )
        
        # 1日進める
        self.camp_daily_result = self.pennant_manager.advance_camp_day(
            self.state_manager.player_team
        )
        
        day = self.camp_daily_result.get("day", 0)
        growth_count = len(self.camp_daily_result.get("growth", {}))
        
        if growth_count > 0:
            ToastManager.show(f"Day{day}: {growth_count}人が成長！", "success")
        else:
            ToastManager.show(f"Day{day}: 練習終了", "info")
        
        # キャンプ終了判定
        camp = self.pennant_manager.spring_camp_state
        if camp and camp.current_day > camp.total_days:
            self.end_pennant_camp()
    
    def auto_camp(self):
        """キャンプを一括で進める"""
        if not self.pennant_manager or not self.pennant_manager.spring_camp_state:
            return
        
        camp = self.pennant_manager.spring_camp_state
        remaining = camp.total_days - camp.current_day + 1
        
        # トレーニングメニューを設定
        if self.camp_training_menu:
            self.pennant_manager.set_camp_training_menu(
                batting=self.camp_training_menu.get("batting", 3),
                pitching=self.camp_training_menu.get("pitching", 3),
                fielding=self.camp_training_menu.get("fielding", 3),
                physical=self.camp_training_menu.get("physical", 3),
                rest=self.camp_training_menu.get("rest", 3)
            )
        
        # 残りの日数を一括処理
        for _ in range(remaining):
            self.pennant_manager.advance_camp_day(self.state_manager.player_team)
        
        self.camp_daily_result = None  # 一括の場合は日次結果をクリア
        self.end_pennant_camp()
    
    def execute_intrasquad_game(self):
        """紅白戦を実行"""
        if not self.pennant_manager:
            return
        
        result = self.pennant_manager.execute_intrasquad_game(self.state_manager.player_team)
        mvp = result.get("mvp", "")
        ToastManager.show(f"紅白戦終了！ MVP: {mvp}", "success")
    
    def execute_practice_game(self):
        """オープン戦を実行"""
        if not self.pennant_manager:
            return
        
        # ランダムに対戦相手を選ぶ
        opponents = [t for t in self.state_manager.all_teams if t != self.state_manager.player_team]
        opponent = opponents[0] if opponents else None
        
        if opponent:
            result = self.pennant_manager.execute_practice_game(
                self.state_manager.player_team, opponent.name
            )
            score = result.get("score", "0-0")
            win_text = "勝利！" if result.get("win") else "敗北..."
            ToastManager.show(f"オープン戦 vs {opponent.name}: {score} {win_text}", "info")
    
    def end_pennant_camp(self):
        """キャンプを終了してシーズンへ"""
        if not self.pennant_manager:
            return
        
        summary = self.pennant_manager.end_spring_camp()
        self.pennant_camp_results = summary
        
        growth_count = len(summary.get("growth_results", {}))
        ToastManager.show(f"キャンプ終了！{growth_count}人が成長しました", "success")
        
        # フェーズを進める
        self.pennant_manager.advance_phase()
        self.state_manager.change_state(GameState.MENU)
    
    def start_fall_camp(self):
        """秋季キャンプを開始"""
        if not self.state_manager.player_team:
            return
        
        # 総合力が250以下の選手のみ参加（若手・控え中心）
        OVERALL_THRESHOLD = 250
        all_players = self.state_manager.player_team.players
        self.fall_camp_players = [p for p in all_players if p.overall_rating <= OVERALL_THRESHOLD]
        
        if not self.fall_camp_players:
            ToastManager.show("参加対象の選手がいません（総合力250以下）", "warning")
            # ドラフトへ移行
            self.generate_draft_prospects()
            self.state_manager.change_state(GameState.DRAFT)
            return
        
        # 参加選手のgrowthとplayer_statusを初期化（キャンプ開始時）
        from player_development import PlayerGrowth, PlayerStatus
        for player in self.fall_camp_players:
            if not hasattr(player, 'growth') or player.growth is None:
                player.growth = PlayerGrowth(potential=getattr(player, 'potential', 5))
            if not hasattr(player, 'player_status') or player.player_status is None:
                player.player_status = PlayerStatus()
            # キャンプ開始時に疲労をリセット
            player.player_status.fatigue = 0
            player.player_status.motivation = 70
        
        # 秋季キャンプ状態を初期化
        self.fall_camp_results = None
        self.fall_camp_daily_result = None
        self.fall_camp_training_menu = {
            "batting": 3, "pitching": 3, "fielding": 3, "physical": 3, "rest": 3, "mental": 3
        }
        self.fall_camp_day = 1
        self.fall_camp_max_days = 14  # 秋季キャンプは2週間
        self.fall_selected_menus = {}
        self.selected_fall_player_idx = -1
        self.fall_filter_pos = None
        self.fall_player_scroll = 0
        
        ToastManager.show(f"秋季キャンプ開始！（{len(self.fall_camp_players)}人参加・14日間）", "success")
        self.state_manager.change_state(GameState.PENNANT_FALL_CAMP)

    def process_pennant_camp(self):
        """春季キャンプ処理（簡易版 - 互換性のため残す）"""
        if not self.pennant_manager:
            return
        
        self.pennant_camp_results = self.pennant_manager.process_spring_camp(
            self.state_manager.player_team
        )
        self.state_manager.change_state(GameState.PENNANT_CAMP)
        
        # 成長した選手数をトースト表示
        growth_count = len(self.pennant_camp_results.get("growth", {}))
        ToastManager.show(f"キャンプ完了！{growth_count}人が成長", "success")
    
    def _run_camp_batch(self, is_fall: bool = False, show_log: bool = False):
        """キャンプを一括実行する
        
        Args:
            is_fall: Trueなら秋季キャンプ、Falseなら春季キャンプ
            show_log: 成長ログを表示するかどうか
        """
        from player_development import PlayerDevelopment, TrainingType
        
        if is_fall:
            players = self.fall_camp_players if self.fall_camp_players else []
            max_days = getattr(self, 'fall_camp_max_days', 14)
            cur_day = getattr(self, 'fall_camp_day', 1)
            selected_menus = getattr(self, 'fall_selected_menus', {})
            camp_name = "秋季"
        else:
            team = self.state_manager.player_team
            players = team.players if team else []
            max_days = getattr(self, 'spring_camp_max_days', 30)
            cur_day = getattr(self, 'spring_camp_day', 1)
            selected_menus = getattr(self, 'spring_selected_menus', {})
            camp_name = "春季"
        
        remaining = max_days - cur_day + 1
        
        # Define training types for each position - must match screens.py UI order
        trainings_pitcher = [TrainingType.PITCHING, TrainingType.CONTROL, TrainingType.BREAKING,
                             TrainingType.STAMINA, TrainingType.REST]
        trainings_batter = [TrainingType.BATTING, TrainingType.POWER, TrainingType.RUNNING,
                            TrainingType.FIELDING, TrainingType.STAMINA, TrainingType.REST]
        
        # Collect growth log
        growth_log = []  # List of (player_name, stat_name, old_val, new_val)
        trained = 0
        stat_ups = 0
        
        for day in range(remaining):
            for i, player in enumerate(players):
                # Get menu from selection or pick random
                t_idx = selected_menus.get(i, -1)
                if t_idx < 0:
                    if player.position.name == 'PITCHER':
                        t_idx = random.choice([0, 1, 2])
                    else:
                        t_idx = random.choice([0, 1, 2, 3])
                
                if player.position.name == 'PITCHER':
                    tlist = trainings_pitcher
                else:
                    tlist = trainings_batter
                
                if 0 <= t_idx < len(tlist):
                    ttype = tlist[t_idx]
                    
                    # Store old values for logging
                    old_vals = {}
                    if show_log:
                        for stat in ['speed', 'control', 'stamina', 'breaking', 
                                    'contact', 'power', 'run', 'fielding', 'arm', 'mental']:
                            old_vals[stat] = getattr(player.stats, stat, 0)
                    
                    res = PlayerDevelopment.train_player(player, ttype, xp_multiplier=0.6)
                    if res.get('success'):
                        trained += 1
                    if res.get('stat_gains'):
                        stat_ups += len(res['stat_gains'])
                        
                        # Record growth for log
                        if show_log:
                            for stat_name, gain in res['stat_gains'].items():
                                new_val = getattr(player.stats, stat_name, 0)
                                growth_log.append((player.name, stat_name, old_vals.get(stat_name, 0), new_val))
        
        # Store growth log for display
        if show_log and growth_log:
            self.camp_growth_log = growth_log
            self.show_camp_log = True
        
        # Finish camp
        if is_fall:
            self.fall_camp_day = max_days + 1
            self.fall_selected_menus = {}
            ToastManager.show(f"{camp_name}キャンプ終了 ({stat_ups}回成長)", "success")
            self.generate_draft_prospects()
            self.state_manager.change_state(GameState.DRAFT)
        else:
            self.spring_camp_day = max_days + 1
            self.spring_selected_menus = {}
            ToastManager.show(f"{camp_name}キャンプ終了 ({stat_ups}回成長)", "success")
            self.state_manager.change_state(GameState.MENU)
    
    def execute_training(self, training_type: str):
        """育成トレーニングを実行"""
        if not self.state_manager.player_team:
            return
        
        if self.selected_training_player_idx < 0:
            ToastManager.show("選手を選択してください", "warning")
            return
        
        players = self.state_manager.player_team.players
        if self.selected_training_player_idx >= len(players):
            return
        
        player = players[self.selected_training_player_idx]
        
        # トレーニングコストと効果を定義
        training_costs = {
            "train_velocity": 50,
            "train_control": 40,
            "train_breaking": 45,
            "train_stamina": 35,
            "train_contact": 40,
            "train_power": 50,
            "train_speed": 35,
            "train_defense": 40,
        }
        
        cost = training_costs.get(training_type, 50)
        
        if self.training_points < cost:
            ToastManager.show("育成ポイントが足りません", "warning")
            return
        
        # 能力値を上昇
        stat_name = ""
        if training_type == "train_velocity":
            player.stats.speed = min(20, player.stats.speed + 1)
            stat_name = "球速"
        elif training_type == "train_control":
            player.stats.control = min(20, player.stats.control + 1)
            stat_name = "制球"
        elif training_type == "train_breaking":
            player.stats.breaking = min(20, player.stats.breaking + 1)
            stat_name = "変化"
        elif training_type == "train_stamina":
            player.stats.stamina = min(20, player.stats.stamina + 1)
            stat_name = "スタミナ"
        elif training_type == "train_contact":
            player.stats.contact = min(20, player.stats.contact + 1)
            stat_name = "ミート"
        elif training_type == "train_power":
            player.stats.power = min(20, player.stats.power + 1)
            stat_name = "パワー"
        elif training_type == "train_speed":
            player.stats.run = min(20, player.stats.run + 1)
            stat_name = "走力"
        elif training_type == "train_defense":
            player.stats.fielding = min(20, player.stats.fielding + 1)
            stat_name = "守備"
        
        self.training_points -= cost
        ToastManager.show(f"{player.name}の{stat_name}が上昇！", "success")
    
    def reset_lineup_selection(self):
        """オーダー画面の選択状態をリセット"""
        self.lineup_selected_player_idx = -1
        self.lineup_swap_mode = False
        self.lineup_selected_slot = -1
        self.lineup_selected_source = ""
        self.dragging_player_idx = -1
        self.drag_pos = None
        # ポジション選択もリセット
        self.position_selected_slot = -1
        self.position_swap_mode = False
        # 打順選択もリセット
        self.batting_order_selected_slot = -1
        self.batting_order_swap_mode = False
    
    def _cycle_position(self, slot: int):
        """守備位置を循環（ROSTER_MANAGEMENT画面用）"""
        team = self.state_manager.player_team
        if not team:
            return
        
        # DH制の判定
        from settings_manager import settings
        is_pacific = hasattr(team, 'league') and team.league.value == "パシフィック"
        use_dh = (is_pacific and settings.game_rules.pacific_dh) or (not is_pacific and settings.game_rules.central_dh)
        
        # 守備位置リスト
        positions = ["捕", "一", "二", "三", "遊", "左", "中", "右"]
        if use_dh:
            positions.append("DH")
        
        # lineup_positionsを取得・初期化
        if not hasattr(team, 'lineup_positions') or team.lineup_positions is None:
            team.lineup_positions = ["捕", "一", "二", "三", "遊", "左", "中", "右", "DH" if use_dh else "投"]
        
        while len(team.lineup_positions) <= slot:
            team.lineup_positions.append("DH" if use_dh else "投")
        
        # 現在の位置を取得
        current_pos = team.lineup_positions[slot]
        
        # 次の位置を計算
        try:
            current_idx = positions.index(current_pos)
            next_idx = (current_idx + 1) % len(positions)
        except ValueError:
            next_idx = 0
        
        team.lineup_positions[slot] = positions[next_idx]

    def _handle_position_swap_click(self, slot: int):
        """ポジションをクリックして入れ替え（2回クリック方式）"""
        team = self.state_manager.player_team
        if not team:
            return
        
        # lineup_positions を確保
        if not hasattr(team, 'lineup_positions') or team.lineup_positions is None:
            team.lineup_positions = ["捕", "一", "二", "三", "遊", "左", "中", "右", "DH"]
        while len(team.lineup_positions) <= slot:
            team.lineup_positions.append("DH")
        
        # renderer に選択状態を保存
        if not hasattr(self.renderer, '_order_pos_selected_slot'):
            self.renderer._order_pos_selected_slot = -1
        
        if self.renderer._order_pos_selected_slot >= 0 and self.renderer._order_pos_selected_slot != slot:
            # 入れ替え実行
            src = self.renderer._order_pos_selected_slot
            team.lineup_positions[src], team.lineup_positions[slot] = team.lineup_positions[slot], team.lineup_positions[src]
            
            from ui_pro import ToastManager
            ToastManager.show(f"守備位置を入れ替えました", "success")
            self.renderer._order_pos_selected_slot = -1
        elif self.renderer._order_pos_selected_slot == slot:
            # 同じスロットをクリックで解除
            self.renderer._order_pos_selected_slot = -1
        else:
            # 選択開始
            self.renderer._order_pos_selected_slot = slot
            current_pos = team.lineup_positions[slot]
            from ui_pro import ToastManager
            ToastManager.show(f"{slot + 1}番 [{current_pos}] を選択中", "info")

    def _handle_second_pitcher_click(self, player_idx: int):
        """二軍投手をクリックして選択→一軍投手と入れ替え可能"""
        team = self.state_manager.player_team
        if not team:
            return
        
        from ui_pro import ToastManager
        from models import TeamLevel
        
        # 空きスロットが選択されていたらそこに配置
        if self.lineup_swap_mode and self.lineup_selected_source in ["rotation_empty", "relief_empty", "closer_empty"]:
            slot_idx = self.lineup_selected_slot
            player = team.players[player_idx]
            
            if self.lineup_selected_source == "rotation_empty":
                rotation = team.rotation or []
                while len(rotation) <= slot_idx:
                    rotation.append(-1)
                rotation[slot_idx] = player_idx
                team.rotation = rotation
                player.team_level = TeamLevel.FIRST
                ToastManager.show(f"{player.name}を先発{slot_idx+1}番に配置", "success")
            elif self.lineup_selected_source == "relief_empty":
                setup = team.setup_pitchers or []
                while len(setup) <= slot_idx:
                    setup.append(-1)
                setup[slot_idx] = player_idx
                team.setup_pitchers = setup
                player.team_level = TeamLevel.FIRST
                ToastManager.show(f"{player.name}を中継ぎ{slot_idx+1}番に配置", "success")
            elif self.lineup_selected_source == "closer_empty":
                team.closer_idx = player_idx
                player.team_level = TeamLevel.FIRST
                ToastManager.show(f"{player.name}を抑えに配置", "success")
            
            self.reset_lineup_selection()
            return
        
        # renderer に選択状態を保存
        if not hasattr(self.renderer, '_second_pitcher_selected_idx'):
            self.renderer._second_pitcher_selected_idx = -1
        
        if self.renderer._second_pitcher_selected_idx == player_idx:
            # 同じ選手をクリックで解除
            self.renderer._second_pitcher_selected_idx = -1
        else:
            # 選択開始（一軍投手との入れ替え待ち）
            self.renderer._second_pitcher_selected_idx = player_idx
            if player_idx < len(team.players):
                player = team.players[player_idx]
                ToastManager.show(f"{player.name} を選択中。先発/中継ぎ/抑えをクリックで入れ替え", "info")
    
    def _swap_second_pitcher_with_first(self, first_player_idx: int, slot_type: str, slot_idx: int = -1):
        """二軍投手と一軍投手を入れ替え"""
        team = self.state_manager.player_team
        if not team:
            return
        
        from ui_pro import ToastManager
        from models import TeamLevel
        
        second_idx = getattr(self.renderer, '_second_pitcher_selected_idx', -1)
        if second_idx < 0:
            return
        
        second_player = team.players[second_idx]
        first_player = team.players[first_player_idx] if first_player_idx >= 0 else None
        
        # 入れ替え実行
        if slot_type == "rotation" and slot_idx >= 0:
            # 先発ローテーションとの入れ替え
            rotation = team.rotation or []
            while len(rotation) <= slot_idx:
                rotation.append(-1)
            old_idx = rotation[slot_idx] if slot_idx < len(rotation) else -1
            rotation[slot_idx] = second_idx
            team.rotation = rotation
            second_player.team_level = TeamLevel.FIRST
            if old_idx >= 0 and old_idx < len(team.players):
                team.players[old_idx].team_level = TeamLevel.SECOND
            ToastManager.show(f"{second_player.name}を先発{slot_idx+1}番に昇格", "success")
        elif slot_type == "setup" and slot_idx >= 0:
            # 中継ぎとの入れ替え
            setup = team.setup_pitchers or []
            while len(setup) <= slot_idx:
                setup.append(-1)
            old_idx = setup[slot_idx] if slot_idx < len(setup) else -1
            setup[slot_idx] = second_idx
            team.setup_pitchers = setup
            second_player.team_level = TeamLevel.FIRST
            if old_idx >= 0 and old_idx < len(team.players):
                team.players[old_idx].team_level = TeamLevel.SECOND
            ToastManager.show(f"{second_player.name}を中継ぎ{slot_idx+1}番に昇格", "success")
        elif slot_type == "closer":
            # 抑えとの入れ替え
            old_closer = getattr(team, 'closer_idx', -1)
            team.closer_idx = second_idx
            second_player.team_level = TeamLevel.FIRST
            if old_closer >= 0 and old_closer < len(team.players):
                team.players[old_closer].team_level = TeamLevel.SECOND
            ToastManager.show(f"{second_player.name}を抑えに昇格", "success")
        
        self.renderer._second_pitcher_selected_idx = -1

    def _handle_second_batter_click(self, player_idx: int):
        """二軍野手をクリックして選択→一軍選手と入れ替え可能"""
        team = self.state_manager.player_team
        if not team:
            return
        
        from ui_pro import ToastManager
        from models import TeamLevel
        
        # 控え選手が選択されていたら入れ替え
        bench_selected = getattr(self.renderer, '_bench_batter_selected_idx', -1)
        if bench_selected >= 0:
            self._swap_bench_with_second(bench_selected, player_idx)
            self.renderer._bench_batter_selected_idx = -1
            return
        
        # 空きスロットが選択されていたらそこに配置
        if self.lineup_swap_mode and self.lineup_selected_source == "lineup_empty":
            slot_idx = self.lineup_selected_slot
            player = team.players[player_idx]
            lineup = team.current_lineup or []
            while len(lineup) <= slot_idx:
                lineup.append(-1)
            lineup[slot_idx] = player_idx
            team.current_lineup = lineup
            player.team_level = TeamLevel.FIRST
            ToastManager.show(f"{player.name}を{slot_idx+1}番に配置", "success")
            self.reset_lineup_selection()
            return
        
        # renderer に選択状態を保存
        if not hasattr(self.renderer, '_second_batter_selected_idx'):
            self.renderer._second_batter_selected_idx = -1
        
        if self.renderer._second_batter_selected_idx == player_idx:
            # 同じ選手をクリックで解除
            self.renderer._second_batter_selected_idx = -1
        else:
            # 選択開始（一軍選手との入れ替え待ち）
            self.renderer._second_batter_selected_idx = player_idx
            if player_idx < len(team.players):
                player = team.players[player_idx]
                ToastManager.show(f"{player.name} を選択中。スタメン/控えをクリックで入れ替え", "info")
    
    def _swap_second_batter_with_first(self, first_player_idx: int, slot_type: str, slot_idx: int = -1):
        """二軍野手と一軍野手を入れ替え"""
        team = self.state_manager.player_team
        if not team:
            return
        
        from ui_pro import ToastManager
        from models import TeamLevel
        
        second_idx = getattr(self.renderer, '_second_batter_selected_idx', -1)
        if second_idx < 0:
            return
        
        second_player = team.players[second_idx]
        first_player = team.players[first_player_idx] if first_player_idx >= 0 else None
        
        # 入れ替え実行
        if slot_type == "lineup" and slot_idx >= 0:
            # スタメンとの入れ替え
            team.current_lineup[slot_idx] = second_idx
            second_player.team_level = TeamLevel.FIRST
            if first_player:
                first_player.team_level = TeamLevel.SECOND
            ToastManager.show(f"{second_player.name}をスタメンに昇格", "success")
        elif slot_type == "bench":
            # ベンチとの入れ替え
            bench = team.bench_batters or []
            if first_player_idx in bench:
                # 既存のベンチ選手と入れ替え
                idx = bench.index(first_player_idx)
                bench[idx] = second_idx
                team.bench_batters = bench
                second_player.team_level = TeamLevel.FIRST
                if first_player:
                    first_player.team_level = TeamLevel.SECOND
                ToastManager.show(f"{second_player.name}と{first_player.name}を入れ替え", "success")
            else:
                # ベンチに追加
                bench.append(second_idx)
                team.bench_batters = bench
                second_player.team_level = TeamLevel.FIRST
                ToastManager.show(f"{second_player.name}を控えに昇格", "success")
        
        self.renderer._second_batter_selected_idx = -1

    def _swap_bench_batters(self, idx1: int, idx2: int):
        """控え野手同士を入れ替え"""
        team = self.state_manager.player_team
        if not team:
            return
        
        from ui_pro import ToastManager
        
        bench = team.bench_batters or []
        if idx1 in bench and idx2 in bench:
            # 両方ベンチにいる場合は位置を入れ替え
            pos1 = bench.index(idx1)
            pos2 = bench.index(idx2)
            bench[pos1], bench[pos2] = bench[pos2], bench[pos1]
            team.bench_batters = bench
            p1 = team.players[idx1]
            p2 = team.players[idx2]
            ToastManager.show(f"{p1.name}と{p2.name}の順番を入れ替え", "success")

    def _swap_bench_with_lineup(self, bench_idx: int, lineup_slot: int):
        """控え選手とスタメンを入れ替え"""
        team = self.state_manager.player_team
        if not team:
            return
        
        from ui_pro import ToastManager
        from models import TeamLevel
        
        lineup = team.current_lineup or []
        bench = team.bench_batters or []
        
        if bench_idx not in bench:
            return
        
        if lineup_slot < 0 or lineup_slot >= len(lineup):
            return
        
        lineup_player_idx = lineup[lineup_slot]
        bench_player = team.players[bench_idx]
        
        # 入れ替え実行
        # ベンチから削除してスタメンに
        bench.remove(bench_idx)
        
        # 元のスタメン選手をベンチに
        if lineup_player_idx >= 0:
            lineup_player = team.players[lineup_player_idx]
            bench.append(lineup_player_idx)
        
        # 控え選手をスタメンに
        lineup[lineup_slot] = bench_idx
        
        team.current_lineup = lineup
        team.bench_batters = bench
        
        ToastManager.show(f"{bench_player.name}をスタメンに", "success")
        self.renderer._bench_batter_selected_idx = -1

    def _swap_bench_with_second(self, bench_idx: int, second_idx: int):
        """控え選手と二軍選手を入れ替え"""
        team = self.state_manager.player_team
        if not team:
            return
        
        from ui_pro import ToastManager
        from models import TeamLevel
        
        bench = team.bench_batters or []
        
        if bench_idx not in bench:
            return
        
        if second_idx < 0 or second_idx >= len(team.players):
            return
        
        bench_player = team.players[bench_idx]
        second_player = team.players[second_idx]
        
        # 入れ替え実行
        # ベンチから削除して二軍へ
        bench_pos = bench.index(bench_idx)
        bench[bench_pos] = second_idx
        
        # 元の控え選手を二軍に
        bench_player.team_level = TeamLevel.SECOND
        
        # 二軍選手を一軍に
        second_player.team_level = TeamLevel.FIRST
        
        team.bench_batters = bench
        
        ToastManager.show(f"{bench_player.name}と{second_player.name}を入れ替え", "success")

    def handle_position_slot_click(self, slot: int):
        """ポジションスロットのクリック処理（守備位置入れ替え）"""
        team = self.state_manager.player_team
        if not team:
            return
        
        lineup = team.current_lineup or []
        
        if self.position_swap_mode and self.position_selected_slot >= 0:
            # 入れ替え実行
            src_slot = self.position_selected_slot
            if src_slot != slot:
                # _execute_position_swapを利用
                old_selected = self.position_selected_slot
                self.position_selected_slot = src_slot  # 元の選択を維持
                self._execute_position_swap(slot)
            else:
                self.position_selected_slot = -1
                self.position_swap_mode = False
        else:
            # スロット選択
            if slot < len(lineup) and lineup[slot] >= 0:
                self.position_selected_slot = slot
                self.position_swap_mode = True
                player = team.players[lineup[slot]]
                # Toastではなく視覚効果で選択状態を表示（画面側で実装済み）
            else:
                pass  # 空スロットは無視
    
    def _add_to_bench_slot(self, slot: int, player_idx: int):
        """選手をベンチスロットに追加"""
        team = self.state_manager.player_team
        if not team or player_idx < 0:
            return
        
        # ベンチリストを初期化
        if not hasattr(team, 'bench_lineup') or team.bench_lineup is None:
            team.bench_lineup = []
        
        # スロット数を確保
        while len(team.bench_lineup) <= slot:
            team.bench_lineup.append(-1)
        
        # 既にスタメンにいる場合は警告
        if team.current_lineup and player_idx in team.current_lineup:
            ToastManager.show("既にスタメンの選手です", "warning")
            return
        
        # 既にベンチにいる場合は位置を入れ替え
        if player_idx in team.bench_lineup:
            old_slot = team.bench_lineup.index(player_idx)
            team.bench_lineup[old_slot] = team.bench_lineup[slot]
            team.bench_lineup[slot] = player_idx
            player = team.players[player_idx]
            ToastManager.show(f"{player.name}をベンチ{slot + 1}番に移動", "success")
        else:
            team.bench_lineup[slot] = player_idx
            player = team.players[player_idx]
            ToastManager.show(f"{player.name}をベンチ{slot + 1}番に配置", "success")
    
    def _remove_from_bench(self, slot: int):
        """ベンチスロットから選手を外す"""
        team = self.state_manager.player_team
        if not team or not hasattr(team, 'bench_lineup'):
            return
        
        if slot < len(team.bench_lineup) and team.bench_lineup[slot] >= 0:
            player = team.players[team.bench_lineup[slot]]
            team.bench_lineup[slot] = -1
            ToastManager.show(f"{player.name}をベンチから外しました", "info")
    
    def handle_position_click(self, mouse_pos):
        """ポジション（守備位置）のクリック選択処理 - 選手とは別"""
        if not self.state_manager.player_team:
            return
        
        team = self.state_manager.player_team
        lineup = team.current_lineup or []
        
        # ポジションボタンをチェック（position_slot_N形式）
        for button_name, button in self.buttons.items():
            if button_name.startswith("position_slot_"):
                if hasattr(button, 'rect') and button.rect.collidepoint(mouse_pos):
                    slot_idx = int(button_name.replace("position_slot_", ""))
                    
                    if self.position_swap_mode:
                        # ポジションスワップ実行
                        self._execute_position_swap(slot_idx)
                    else:
                        # ポジション選択開始
                        if slot_idx < len(lineup) and lineup[slot_idx] >= 0:
                            self.position_selected_slot = slot_idx
                            self.position_swap_mode = True
                            player = team.players[lineup[slot_idx]]
                            ToastManager.show(f"{player.name}の守備位置を選択中。入れ替え先をクリック", "info")
                        else:
                            ToastManager.show("空きスロットは選択できません", "warning")
                    return True
        
        # 何もクリックしていなければ選択解除
        if self.position_swap_mode:
            self.position_selected_slot = -1
            self.position_swap_mode = False
            ToastManager.show("ポジション選択を解除しました", "info")
        
        return False
    
    def _execute_position_swap(self, target_slot: int):
        """守備位置の入れ替えを実行（打順は維持、ポジションのみスワップ）"""
        team = self.state_manager.player_team
        lineup = team.current_lineup or []
        
        src_slot = self.position_selected_slot
        
        if src_slot == target_slot:
            # 同じスロットは無視
            self.position_selected_slot = -1
            self.position_swap_mode = False
            return
        
        # 両スロットに選手がいることを確認
        if src_slot >= len(lineup) or target_slot >= len(lineup):
            # 空スロットは入れ替え不可
            self.position_selected_slot = -1
            self.position_swap_mode = False
            return
        
        src_player_idx = lineup[src_slot]
        tgt_player_idx = lineup[target_slot]
        
        if src_player_idx < 0 or tgt_player_idx < 0:
            # 空スロットは入れ替え不可
            self.position_selected_slot = -1
            self.position_swap_mode = False
            return
        
        # lineup_positions（守備位置リスト）を入れ替え
        if hasattr(team, 'lineup_positions') and team.lineup_positions:
            lineup_positions = team.lineup_positions
        else:
            lineup_positions = ["捕", "一", "二", "三", "遊", "左", "中", "右", "DH"]
            while len(lineup_positions) < 9:
                lineup_positions.append("DH")
        
        # 守備位置を入れ替え
        while len(lineup_positions) <= max(src_slot, target_slot):
            lineup_positions.append("DH")
        
        lineup_positions[src_slot], lineup_positions[target_slot] = lineup_positions[target_slot], lineup_positions[src_slot]
        team.lineup_positions = lineup_positions
        
        # Toastなし、視覚効果で判断
        
        self.position_selected_slot = -1
        self.position_swap_mode = False
    
    def handle_batting_order_slot_click(self, slot: int):
        """打順スロットのクリック処理（打順入れ替え）"""
        team = self.state_manager.player_team
        if not team:
            return
        
        lineup = team.current_lineup or []
        
        if self.batting_order_swap_mode and self.batting_order_selected_slot >= 0:
            # 入れ替え実行
            src_slot = self.batting_order_selected_slot
            if src_slot != slot and src_slot < len(lineup) and slot < len(lineup):
                # 打順（選手）を入れ替え
                lineup[src_slot], lineup[slot] = lineup[slot], lineup[src_slot]
                team.current_lineup = lineup
            self.batting_order_selected_slot = -1
            self.batting_order_swap_mode = False
        else:
            # スロット選択
            if slot < len(lineup) and lineup[slot] >= 0:
                self.batting_order_selected_slot = slot
                self.batting_order_swap_mode = True
            else:
                pass  # 空スロットは無視
    
    def handle_batting_order_swap(self, mouse_pos):
        """打順スロットのクリック選択処理 - 打順の入れ替え専用"""
        if not self.state_manager.player_team:
            return False
        
        team = self.state_manager.player_team
        lineup = team.current_lineup or []
        
        # 打順ボタンをチェック（batting_order_N形式）
        for button_name, button in self.buttons.items():
            if button_name.startswith("batting_order_"):
                if hasattr(button, 'rect') and button.rect.collidepoint(mouse_pos):
                    slot_idx = int(button_name.replace("batting_order_", ""))
                    
                    if self.lineup_swap_mode and self.lineup_selected_source == "batting_order":
                        # 打順スワップ実行
                        src_slot = self.lineup_selected_slot
                        if src_slot != slot_idx:
                            # 選手を入れ替え
                            while len(lineup) <= max(src_slot, slot_idx):
                                lineup.append(-1)
                            
                            lineup[src_slot], lineup[slot_idx] = lineup[slot_idx], lineup[src_slot]
                            team.current_lineup = lineup
                            # Toastなしで入れ替え完了（視覚効果で判断）
                        self.reset_lineup_selection()
                    else:
                        # 打順選択開始
                        if slot_idx < len(lineup) and lineup[slot_idx] >= 0:
                            self.lineup_selected_slot = slot_idx
                            self.lineup_selected_source = "batting_order"
                            self.lineup_swap_mode = True
                            # Toastなし、視覚効果のみ
                        else:
                            pass  # 空きスロットは無視
                    return True
        
        return False
    
    def handle_lineup_click(self, mouse_pos):
        """オーダー画面でのクリック選択処理（ドラッグ&ドロップの代替）"""
        if not self.state_manager.player_team:
            return
        
        team = self.state_manager.player_team
        
        # ポジション変更ボタン(change_pos_)がクリックされている場合はスキップ
        # これはhandle_button_clickで別途処理される
        for button_name, button in self.buttons.items():
            if button_name.startswith("change_pos_"):
                if hasattr(button, 'rect') and button.rect.collidepoint(mouse_pos):
                    return  # change_pos_はhandle_button_clickで処理
        
        # ドロップゾーン情報を取得
        if "_drop_zones" in self.buttons:
            drop_zones = self.buttons["_drop_zones"]
        else:
            drop_zones = self.drop_zones
        
        clicked_something = False
        
        # 選手一覧のボタンをチェック（ロースター）
        for button_name, button in self.buttons.items():
            if button_name.startswith("drag_player_") or button_name.startswith("add_lineup_"):
                if hasattr(button, 'rect') and button.rect.collidepoint(mouse_pos):
                    if button_name.startswith("drag_player_"):
                        player_idx = int(button_name.replace("drag_player_", ""))
                    else:
                        player_idx = int(button_name.replace("add_lineup_", ""))
                    
                    if self.lineup_swap_mode:
                        # 入れ替えモード中なら入れ替え実行
                        self._execute_lineup_swap(player_idx, "roster")
                    else:
                        # 選択モード開始
                        self.lineup_selected_player_idx = player_idx
                        self.lineup_selected_source = "roster"
                        self.lineup_swap_mode = True
                        player = team.players[player_idx]
                        ToastManager.show(f"{player.name}を選択中。入れ替え先をクリック", "info")
                    clicked_something = True
                    return
            
            # スタメンスロットのクリック
            elif button_name.startswith("lineup_slot_"):
                if hasattr(button, 'rect') and button.rect.collidepoint(mouse_pos):
                    # ポジション入れ替えモード中は選手選択をスキップ
                    if getattr(self, 'roster_swap_mode', False):
                        clicked_something = True
                        return
                    
                    slot_idx = int(button_name.replace("lineup_slot_", ""))
                    lineup = team.current_lineup or []
                    first_player_idx = lineup[slot_idx] if slot_idx < len(lineup) else -1
                    
                    # 二軍野手が選択されていたら入れ替え
                    second_batter_idx = getattr(self.renderer, '_second_batter_selected_idx', -1)
                    if second_batter_idx >= 0:
                        self._swap_second_batter_with_first(first_player_idx, "lineup", slot_idx)
                        clicked_something = True
                        return
                    
                    # 控え選手が選択されていたら入れ替え
                    bench_batter_idx = getattr(self.renderer, '_bench_batter_selected_idx', -1)
                    if bench_batter_idx >= 0:
                        self._swap_bench_with_lineup(bench_batter_idx, slot_idx)
                        clicked_something = True
                        return
                    
                    if self.lineup_swap_mode:
                        # 入れ替え実行
                        self._execute_lineup_swap_to_slot(slot_idx)
                    else:
                        # このスロットの選手を選択
                        if slot_idx < len(lineup) and lineup[slot_idx] >= 0:
                            self.lineup_selected_player_idx = lineup[slot_idx]
                            self.lineup_selected_slot = slot_idx
                            self.lineup_selected_source = "lineup"
                            self.lineup_swap_mode = True
                            # Toastなし、視覚効果のみ
                        else:
                            # 空きスロットをクリック
                            self.lineup_selected_slot = slot_idx
                            self.lineup_selected_source = "lineup_empty"
                            self.lineup_swap_mode = True
                            ToastManager.show(f"{slot_idx+1}番の空き枠を選択中。二軍選手をクリックで配置", "info")
                    clicked_something = True
                    return
            
            # ローテーションスロット
            elif button_name.startswith("rotation_slot_"):
                if hasattr(button, 'rect') and button.rect.collidepoint(mouse_pos):
                    slot_idx = int(button_name.replace("rotation_slot_", ""))
                    rotation = team.rotation or []
                    first_pitcher_idx = rotation[slot_idx] if slot_idx < len(rotation) else -1
                    
                    # 二軍投手が選択されていたら入れ替え
                    second_pitcher_idx = getattr(self.renderer, '_second_pitcher_selected_idx', -1)
                    if second_pitcher_idx >= 0:
                        self._swap_second_pitcher_with_first(first_pitcher_idx, "rotation", slot_idx)
                        clicked_something = True
                        return
                    
                    if self.lineup_swap_mode:
                        self._execute_pitcher_swap_to_slot(slot_idx, "rotation")
                    else:
                        if slot_idx < len(rotation) and rotation[slot_idx] >= 0:
                            self.lineup_selected_player_idx = rotation[slot_idx]
                            self.lineup_selected_slot = slot_idx
                            self.lineup_selected_source = "rotation"
                            self.lineup_swap_mode = True
                            # Toastなし
                        else:
                            self.lineup_selected_slot = slot_idx
                            self.lineup_selected_source = "rotation_empty"
                            self.lineup_swap_mode = True
                            ToastManager.show(f"先発{slot_idx+1}番の空き枠を選択中。二軍投手をクリックで配置", "info")
                    clicked_something = True
                    return
            
            # 中継ぎスロット
            elif button_name.startswith("relief_slot_"):
                if hasattr(button, 'rect') and button.rect.collidepoint(mouse_pos):
                    slot_idx = int(button_name.replace("relief_slot_", ""))
                    setup = team.setup_pitchers or []
                    first_pitcher_idx = setup[slot_idx] if slot_idx < len(setup) else -1
                    
                    # 二軍投手が選択されていたら入れ替え
                    second_pitcher_idx = getattr(self.renderer, '_second_pitcher_selected_idx', -1)
                    if second_pitcher_idx >= 0:
                        self._swap_second_pitcher_with_first(first_pitcher_idx, "setup", slot_idx)
                        clicked_something = True
                        return
                    
                    if self.lineup_swap_mode:
                        self._execute_pitcher_swap_to_slot(slot_idx, "relief")
                    else:
                        if slot_idx < len(setup) and setup[slot_idx] >= 0:
                            self.lineup_selected_player_idx = setup[slot_idx]
                            self.lineup_selected_slot = slot_idx
                            self.lineup_selected_source = "relief"
                            self.lineup_swap_mode = True
                            # Toastなし
                        else:
                            self.lineup_selected_slot = slot_idx
                            self.lineup_selected_source = "relief_empty"
                            self.lineup_swap_mode = True
                            ToastManager.show(f"中継ぎ{slot_idx+1}番の空き枠を選択中。二軍投手をクリックで配置", "info")
                    clicked_something = True
                    return
            
            # 抑えスロット
            elif button_name == "closer_slot":
                if hasattr(button, 'rect') and button.rect.collidepoint(mouse_pos):
                    # 二軍投手が選択されていたら入れ替え
                    second_pitcher_idx = getattr(self.renderer, '_second_pitcher_selected_idx', -1)
                    if second_pitcher_idx >= 0:
                        closer_idx = getattr(team, 'closer_idx', -1)
                        self._swap_second_pitcher_with_first(closer_idx, "closer")
                        clicked_something = True
                        return
                    
                    if self.lineup_swap_mode:
                        self._execute_pitcher_swap_to_slot(0, "closer")
                    else:
                        if team.closer_idx >= 0:
                            self.lineup_selected_player_idx = team.closer_idx
                            self.lineup_selected_slot = 0
                            self.lineup_selected_source = "closer"
                            self.lineup_swap_mode = True
                            # Toastなし
                        else:
                            self.lineup_selected_slot = 0
                            self.lineup_selected_source = "closer_empty"
                            self.lineup_swap_mode = True
                            ToastManager.show("抑えの空き枠を選択中。二軍投手をクリックで配置", "info")
                    clicked_something = True
                    return
        
        # 打順ドロップゾーン（order_N）のチェック
        for key, rect in drop_zones.items():
            if isinstance(rect, pygame.Rect) and rect.collidepoint(mouse_pos):
                if key.startswith("order_"):
                    order_idx = int(key.replace("order_", ""))
                    
                    if self.lineup_swap_mode:
                        self._execute_lineup_swap_to_slot(order_idx)
                    else:
                        lineup = team.current_lineup or []
                        if order_idx < len(lineup) and lineup[order_idx] >= 0:
                            self.lineup_selected_player_idx = lineup[order_idx]
                            self.lineup_selected_slot = order_idx
                            self.lineup_selected_source = "lineup"
                            self.lineup_swap_mode = True
                            player = team.players[lineup[order_idx]]
                            ToastManager.show(f"{player.name}を選択中。入れ替え先をクリック", "info")
                        else:
                            self.lineup_selected_slot = order_idx
                            self.lineup_selected_source = "lineup_empty"
                            self.lineup_swap_mode = True
                            ToastManager.show(f"{order_idx + 1}番に入れる選手をクリック", "info")
                    clicked_something = True
                    return
        
        # 何もクリックしていなければ選択解除
        if not clicked_something:
            # 二軍投手/二軍野手/控え野手の選択解除
            second_pitcher_selected = getattr(self.renderer, '_second_pitcher_selected_idx', -1)
            second_batter_selected = getattr(self.renderer, '_second_batter_selected_idx', -1)
            bench_batter_selected = getattr(self.renderer, '_bench_batter_selected_idx', -1)
            rotation_slot_selected = getattr(self, 'selected_rotation_slot', -1)
            relief_slot_selected = getattr(self, 'selected_relief_slot', -1)
            
            if second_pitcher_selected >= 0:
                self.renderer._second_pitcher_selected_idx = -1
                ToastManager.show("選択を解除しました", "info")
            elif second_batter_selected >= 0:
                self.renderer._second_batter_selected_idx = -1
                ToastManager.show("選択を解除しました", "info")
            elif bench_batter_selected >= 0:
                self.renderer._bench_batter_selected_idx = -1
                ToastManager.show("選択を解除しました", "info")
            elif rotation_slot_selected >= 0 or rotation_slot_selected == -99:
                # ローテーション/抑えスロット選択解除
                self.selected_rotation_slot = -1
                ToastManager.show("選択を解除しました", "info")
            elif relief_slot_selected >= 0:
                # 中継ぎスロット選択解除
                self.selected_relief_slot = -1
                ToastManager.show("選択を解除しました", "info")
            elif self.lineup_swap_mode:
                self.reset_lineup_selection()
                ToastManager.show("選択を解除しました", "info")
    
    def _execute_lineup_swap(self, target_player_idx: int, target_source: str):
        """打順の入れ替えを実行"""
        team = self.state_manager.player_team
        
        if self.lineup_selected_source in ["lineup", "lineup_empty"]:
            # 打順スロットから選手への入れ替え
            slot_idx = self.lineup_selected_slot
            lineup = team.current_lineup or []
            while len(lineup) <= slot_idx:
                lineup.append(-1)
            
            old_player_idx = lineup[slot_idx] if slot_idx < len(lineup) else -1
            lineup[slot_idx] = target_player_idx
            
            # 元の選手が既にラインナップにいた場合は削除
            if target_player_idx in lineup:
                other_idx = lineup.index(target_player_idx)
                if other_idx != slot_idx:
                    lineup[other_idx] = old_player_idx if old_player_idx >= 0 else -1
            
            team.current_lineup = lineup
            ToastManager.show(f"{team.players[target_player_idx].name}を{slot_idx + 1}番に配置", "success")
        
        elif self.lineup_selected_source == "roster":
            # ロースター同士の入れ替え（打順に影響なし）
            pass
        
        self.reset_lineup_selection()
    
    def _execute_lineup_swap_to_slot(self, target_slot: int):
        """選択中の選手を打順スロットに配置"""
        team = self.state_manager.player_team
        lineup = team.current_lineup or []
        while len(lineup) <= target_slot:
            lineup.append(-1)
        
        if self.lineup_selected_source == "roster":
            # ロースターから打順へ
            player_idx = self.lineup_selected_player_idx
            player = team.players[player_idx]
            
            # 投手チェック
            if player.position.value == "投手":
                is_dh = self._is_dh_enabled_for_team(team)
                if is_dh or target_slot != 8:
                    ToastManager.show("投手は打順に入れません", "warning")
                    self.reset_lineup_selection()
                    return
            
            # 既に打順にいる場合は削除
            if player_idx in lineup:
                old_slot = lineup.index(player_idx)
                lineup[old_slot] = -1
            
            # 入れ替え
            old_player = lineup[target_slot]
            lineup[target_slot] = player_idx
            
            team.current_lineup = lineup
            ToastManager.show(f"{player.name}を{target_slot + 1}番に配置", "success")
        
        elif self.lineup_selected_source in ["lineup", "lineup_empty"]:
            # 打順同士の入れ替え
            src_slot = self.lineup_selected_slot
            if src_slot != target_slot:
                # スワップ
                src_player = lineup[src_slot] if src_slot < len(lineup) else -1
                tgt_player = lineup[target_slot] if target_slot < len(lineup) else -1
                
                while len(lineup) <= max(src_slot, target_slot):
                    lineup.append(-1)
                
                lineup[src_slot] = tgt_player
                lineup[target_slot] = src_player
                
                team.current_lineup = lineup
                ToastManager.show(f"{src_slot + 1}番と{target_slot + 1}番を入れ替え", "success")
        
        self.reset_lineup_selection()
    
    def _execute_pitcher_swap_to_slot(self, target_slot: int, target_type: str):
        """選択中の投手を投手スロットに配置"""
        team = self.state_manager.player_team
        
        if self.lineup_selected_source == "roster":
            player_idx = self.lineup_selected_player_idx
            player = team.players[player_idx]
            
            # 投手のみ配置可能
            if player.position.value != "投手":
                ToastManager.show("投手のみ配置できます", "warning")
                self.reset_lineup_selection()
                return
            
            if target_type == "rotation":
                rotation = team.rotation or []
                while len(rotation) <= target_slot:
                    rotation.append(-1)
                
                # 既に配置されていたら削除
                if player_idx in rotation:
                    old_slot = rotation.index(player_idx)
                    rotation[old_slot] = -1
                if player_idx in (team.setup_pitchers or []):
                    team.setup_pitchers.remove(player_idx)
                if player_idx == team.closer_idx:
                    team.closer_idx = -1
                
                rotation[target_slot] = player_idx
                team.rotation = rotation
                ToastManager.show(f"{player.name}を先発{target_slot + 1}番手に配置", "success")
            
            elif target_type == "relief":
                setup = team.setup_pitchers or []
                while len(setup) <= target_slot:
                    setup.append(-1)
                
                # 既に配置されていたら削除
                if player_idx in (team.rotation or []):
                    idx = team.rotation.index(player_idx)
                    team.rotation[idx] = -1
                if player_idx in setup:
                    old_slot = setup.index(player_idx)
                    setup[old_slot] = -1
                if player_idx == team.closer_idx:
                    team.closer_idx = -1
                
                setup[target_slot] = player_idx
                team.setup_pitchers = setup
                ToastManager.show(f"{player.name}を中継ぎ{target_slot + 1}番手に配置", "success")
            
            elif target_type == "closer":
                # 既に配置されていたら削除
                if player_idx in (team.rotation or []):
                    idx = team.rotation.index(player_idx)
                    team.rotation[idx] = -1
                if player_idx in (team.setup_pitchers or []):
                    team.setup_pitchers.remove(player_idx)
                
                team.closer_idx = player_idx
                ToastManager.show(f"{player.name}を抑えに配置", "success")
        
        elif self.lineup_selected_source in ["rotation", "rotation_empty"]:
            # ローテーション同士の入れ替え
            if target_type == "rotation":
                src_slot = self.lineup_selected_slot
                rotation = team.rotation or []
                while len(rotation) <= max(src_slot, target_slot):
                    rotation.append(-1)
                
                rotation[src_slot], rotation[target_slot] = rotation[target_slot], rotation[src_slot]
                team.rotation = rotation
                ToastManager.show(f"先発{src_slot + 1}番手と{target_slot + 1}番手を入れ替え", "success")
        
        elif self.lineup_selected_source in ["relief", "relief_empty"]:
            # 中継ぎ同士の入れ替え
            if target_type == "relief":
                src_slot = self.lineup_selected_slot
                setup = team.setup_pitchers or []
                while len(setup) <= max(src_slot, target_slot):
                    setup.append(-1)
                
                setup[src_slot], setup[target_slot] = setup[target_slot], setup[src_slot]
                team.setup_pitchers = setup
                ToastManager.show(f"中継ぎ{src_slot + 1}番手と{target_slot + 1}番手を入れ替え", "success")
        
        self.reset_lineup_selection()
    
    def handle_lineup_drag_start(self, mouse_pos):
        """オーダー画面でのクリック処理（クリック選択方式）"""
        self.handle_lineup_click(mouse_pos)
    
    def handle_lineup_drop(self, mouse_pos):
        """オーダー画面でのドロップ処理"""
        if self.dragging_player_idx < 0 or not self.state_manager.player_team:
            self.dragging_player_idx = -1
            self.drag_pos = None
            return
        
        team = self.state_manager.player_team
        player = team.players[self.dragging_player_idx]
        
        # ドロップゾーンを取得
        if "_drop_zones" in self.buttons:
            drop_zones = self.buttons["_drop_zones"]
        else:
            drop_zones = self.drop_zones
        
        # ラインナップの初期化
        if not team.current_lineup:
            team.current_lineup = []
        
        # どのドロップゾーンに落としたか判定
        dropped = False
        
        for key, rect in drop_zones.items():
            if not isinstance(rect, pygame.Rect):
                continue
            if not rect.collidepoint(mouse_pos):
                continue
            
            # 打順スロットへのドロップ
            if key.startswith("order_"):
                order_idx = int(key.replace("order_", ""))
                
                # 投手は打順に入れられない（DH制でない場合の9番を除く）
                if player.position.value == "投手":
                    # DH制確認（リーグによって異なる）
                    is_dh_enabled = self._is_dh_enabled_for_team(team)
                    if is_dh_enabled or order_idx != 8:  # DH制ありなら投手不可、DH制なしでも9番以外は不可
                        ToastManager.show("投手は打順に入れません", "warning")
                        break
                
                # 守備位置の重複チェック（position_assignmentsを使用）
                if not hasattr(team, 'position_assignments'):
                    team.position_assignments = {}
                
                # この選手がどの守備位置で出場するか確認
                assigned_pos = None
                for pos_name, assigned_idx in team.position_assignments.items():
                    if assigned_idx == self.dragging_player_idx:
                        assigned_pos = pos_name
                        break
                
                # まだ守備位置が割り当てられていない場合、自動で割り当てを試みる
                if assigned_pos is None and player.position.value != "投手":
                    assigned_pos = self._try_auto_assign_position(team, player, self.dragging_player_idx)
                    if assigned_pos:
                        team.position_assignments[assigned_pos] = self.dragging_player_idx
                        ToastManager.show(f"{player.name}を{assigned_pos}に自動配置", "info")
                
                # 同一ポジションの選手が既に打順にいるかチェック
                position_conflict = self._check_position_conflict(team, self.dragging_player_idx, order_idx)
                if position_conflict:
                    ToastManager.show(position_conflict, "warning")
                    # 警告は出すが配置は許可（ユーザーが手動で調整）
                
                # 既存のラインナップでの元の位置を記録（まだ消さない）
                old_idx = None
                if self.dragging_player_idx in team.current_lineup:
                    old_idx = team.current_lineup.index(self.dragging_player_idx)

                # 指定位置に配置（リスト長を確保）
                while len(team.current_lineup) <= order_idx:
                    team.current_lineup.append(-1)

                # 既にその位置に誰かいる場合は入れ替えを行う
                if team.current_lineup[order_idx] >= 0:
                    old_player_idx = team.current_lineup[order_idx]
                    # もし元のスロットがあれば、そこにold_playerを戻す（入れ替え）
                    if old_idx is not None:
                        team.current_lineup[old_idx] = old_player_idx
                    else:
                        # 元の位置が存在しない（外部から追加された選手）なら、探して置換
                        for i, idx in enumerate(team.current_lineup):
                            if idx == self.dragging_player_idx:
                                team.current_lineup[i] = old_player_idx
                                break
                else:
                    # その位置が空だった場合、元のスロットは空にする
                    if old_idx is not None:
                        team.current_lineup[old_idx] = -1

                # 最後に指定位置へ配置
                team.current_lineup[order_idx] = self.dragging_player_idx
                ToastManager.show(f"{player.name}を{order_idx + 1}番に配置", "success")
                dropped = True
                break
            
            # 守備位置スロットへのドロップ
            elif key.startswith("pos_"):
                pos_name = key.replace("pos_", "")
                
                # サブポジション対応の守備位置チェック
                from models import Position
                
                # 守備位置名からPositionへの変換
                pos_name_to_position = {
                    "捕手": Position.CATCHER,
                    "一塁手": Position.FIRST,
                    "二塁手": Position.SECOND,
                    "三塁手": Position.THIRD,
                    "遊撃手": Position.SHORTSTOP,
                    "左翼手": Position.OUTFIELD,
                    "中堅手": Position.OUTFIELD,
                    "右翼手": Position.OUTFIELD,
                    "DH": None,  # DHは特別
                }
                
                target_position = pos_name_to_position.get(pos_name)
                player_pos = player.position
                
                # DHでない場合、適切なポジションかチェック
                if target_position is not None:
                    # 投手はフィールドに配置できない
                    if player_pos == Position.PITCHER:
                        ToastManager.show("投手はフィールドに配置できません", "warning")
                        break
                    
                    # メインポジションまたはサブポジションで守れるかチェック
                    can_play = player.can_play_position(target_position)
                    
                    # 外野手の特別処理（左翼・中堅・右翼は同じOUTFIELDポジション）
                    if pos_name in ["左翼手", "中堅手", "右翼手"]:
                        can_play = (player_pos == Position.OUTFIELD or 
                                   Position.OUTFIELD in getattr(player, 'sub_positions', []))
                    
                    if not can_play:
                        if hasattr(player, 'sub_positions') and player.sub_positions:
                            sub_pos_names = [p.value for p in player.sub_positions]
                            ToastManager.show(f"{player.name}は{pos_name}を守れません（サブ: {', '.join(sub_pos_names)}）", "warning")
                        else:
                            ToastManager.show(f"{player.name}は{pos_name}を守れません", "warning")
                        break
                else:
                    # DH: 投手以外なら誰でも可
                    if player_pos == Position.PITCHER:
                        ToastManager.show("投手はDHに配置できません", "warning")
                        break
                
                # position_assignmentsの初期化
                if not hasattr(team, 'position_assignments'):
                    team.position_assignments = {}
                
                # 既にこの選手がどこかに配置されていたら削除
                for p_key in list(team.position_assignments.keys()):
                    if team.position_assignments[p_key] == self.dragging_player_idx:
                        del team.position_assignments[p_key]
                
                # 既にこの位置に誰かがいたら削除
                if pos_name in team.position_assignments:
                    old_idx = team.position_assignments[pos_name]
                    if old_idx != self.dragging_player_idx:
                        old_player = team.players[old_idx]
                        ToastManager.show(f"{old_player.name}の配置を解除", "info")
                
                team.position_assignments[pos_name] = self.dragging_player_idx
                
                # サブポジションで守る場合は適性値も表示
                rating = player.get_position_rating(target_position) if target_position else 1.0
                if rating < 1.0:
                    ToastManager.show(f"{player.name}を{pos_name}に配置（適性{int(rating*100)}%）", "success")
                else:
                    ToastManager.show(f"{player.name}を{pos_name}に配置", "success")
                dropped = True
                break
            
            # 先発投手スロットへのドロップ
            elif key == "starting_pitcher":
                if player.position.value != "投手":
                    ToastManager.show("投手以外は先発に設定できません", "warning")
                    break
                
                team.starting_pitcher_idx = self.dragging_player_idx
                ToastManager.show(f"{player.name}を先発投手に設定", "success")
                dropped = True
                break
        
        # ドラッグ状態リセット
        self.dragging_player_idx = -1
        self.drag_pos = None
    
    def handle_position_drop(self, mouse_pos):
        """ポジションのドラッグ&ドロップ処理"""
        if self.dragging_position_slot < 0 or not self.state_manager.player_team:
            self.dragging_position_slot = -1
            self.position_drag_pos = None
            return
        
        team = self.state_manager.player_team
        from_slot = self.dragging_position_slot
        
        # lineup_positionsの初期化
        if not hasattr(team, 'lineup_positions') or team.lineup_positions is None:
            team.lineup_positions = ["捕", "一", "二", "三", "遊", "左", "中", "右", "DH"]
        while len(team.lineup_positions) < 9:
            team.lineup_positions.append("DH")
        
        # ドロップゾーンを取得
        if "_drop_zones" in self.buttons:
            drop_zones = self.buttons["_drop_zones"]
        else:
            drop_zones = self.drop_zones
        
        # どのスロットにドロップしたかを判定
        for key, rect in drop_zones.items():
            if not isinstance(rect, pygame.Rect):
                continue
            if not rect.collidepoint(mouse_pos):
                continue
            
            # 打順スロットへのポジションドロップ
            if key.startswith("order_") or key.startswith("position_slot_"):
                if key.startswith("order_"):
                    to_slot = int(key.replace("order_", ""))
                else:
                    to_slot = int(key.replace("position_slot_", ""))
                
                if to_slot != from_slot and 0 <= to_slot < 9:
                    # ポジションを入れ替え
                    team.lineup_positions[from_slot], team.lineup_positions[to_slot] = \
                        team.lineup_positions[to_slot], team.lineup_positions[from_slot]
                    ToastManager.show(f"{from_slot+1}番と{to_slot+1}番のポジションを入れ替え", "success")
                break
        
        # ドラッグ状態リセット
        self.dragging_position_slot = -1
        self.position_drag_pos = None
    
    def optimize_lineup_by_stats(self):
        """ラインナップをAI最適化"""
        from ai_system import ai_manager, AILineupStrategy
        
        team = self.state_manager.player_team
        if not team:
            ToastManager.show("チームが選択されていません", "warning")
            return
        
        # AIによる最適化
        optimized, desc = ai_manager.optimize_lineup_advanced(team, AILineupStrategy.STANDARD)
        
        if not optimized:
            ToastManager.show("最適化できませんでした", "warning")
            return
        
        # インデックスに変換
        new_lineup = []
        for player in optimized:
            idx = team.players.index(player)
            new_lineup.append(idx)
        
        # 9人に満たない場合は-1で埋める
        while len(new_lineup) < 9:
            new_lineup.append(-1)
        
        team.current_lineup = new_lineup
        ToastManager.show(f"AI: {desc}", "success")
    
    def shuffle_lineup(self):
        """ラインナップをシャッフル"""
        team = self.state_manager.player_team
        if not team or not team.current_lineup:
            ToastManager.show("オーダーが設定されていません", "warning")
            return
        
        import random
        valid_players = [idx for idx in team.current_lineup if idx >= 0]
        random.shuffle(valid_players)
        
        new_lineup = [-1] * 9
        for i, player_idx in enumerate(valid_players):
            if i < 9:
                new_lineup[i] = player_idx
        
        team.current_lineup = new_lineup
        ToastManager.show("ラインナップをシャッフルしました", "info")
    
    def save_lineup_preset(self):
        """現在のラインナップをプリセットとして保存"""
        team = self.state_manager.player_team
        if not team or not team.current_lineup:
            ToastManager.show("保存するオーダーがありません", "warning")
            return
        
        if not hasattr(team, 'lineup_presets'):
            team.lineup_presets = []
        
        preset = {
            'lineup': list(team.current_lineup),
            'positions': list(getattr(team, 'lineup_positions', [])),
            'pitcher': team.starting_pitcher_idx
        }
        team.lineup_presets.append(preset)
        
        # 最大5件まで保持
        if len(team.lineup_presets) > 5:
            team.lineup_presets = team.lineup_presets[-5:]
        
        ToastManager.show(f"オーダープリセット{len(team.lineup_presets)}を保存", "success")
    
    def load_lineup_preset(self):
        """最後に保存したラインナッププリセットを読み込み"""
        team = self.state_manager.player_team
        if not team:
            return
        
        if not hasattr(team, 'lineup_presets') or not team.lineup_presets:
            ToastManager.show("保存されたプリセットがありません", "warning")
            return
        
        # 最後のプリセットを読み込み
        preset = team.lineup_presets[-1]
        team.current_lineup = list(preset.get('lineup', []))
        if 'positions' in preset and preset['positions']:
            team.lineup_positions = list(preset['positions'])
        if 'pitcher' in preset:
            team.starting_pitcher_idx = preset['pitcher']
        
        ToastManager.show("オーダープリセットを読み込みました", "success")
    
    def _is_dh_enabled_for_team(self, team: Team) -> bool:
        """チームのリーグに応じてDH制が有効かどうかを返す"""
        rules = self.settings.game_rules
        
        # チームのリーグを確認
        from models import League
        if team.league == League.CENTRAL:
            return rules.central_dh
        elif team.league == League.PACIFIC:
            return rules.pacific_dh
        else:
            # 不明な場合はDHありとする
            return True
    
    def _try_auto_assign_position(self, team: Team, player, player_idx: int) -> str:
        """打順配置時に守備位置を自動割り当て"""
        from models import Position
        
        # 既に割り当て済みのポジションを取得
        assigned_positions = set(team.position_assignments.keys()) if hasattr(team, 'position_assignments') else set()
        
        # 選手のメインポジションに基づいて割り当て
        pos_map = {
            Position.CATCHER: "捕手",
            Position.FIRST: "一塁手",
            Position.SECOND: "二塁手",
            Position.THIRD: "三塁手",
            Position.SHORTSTOP: "遊撃手",
        }
        
        main_pos = player.position
        
        # メインポジションが空いていれば割り当て
        if main_pos in pos_map:
            pos_name = pos_map[main_pos]
            if pos_name not in assigned_positions:
                return pos_name
        
        # 外野手の場合は左中右を順に試す
        if main_pos == Position.OUTFIELD:
            for outfield_pos in ["左翼手", "中堅手", "右翼手"]:
                if outfield_pos not in assigned_positions:
                    return outfield_pos
        
        # メインポジションが埋まっている場合、サブポジションを試す
        if hasattr(player, 'sub_positions'):
            for sub_pos in player.sub_positions:
                if sub_pos in pos_map:
                    sub_pos_name = pos_map[sub_pos]
                    if sub_pos_name not in assigned_positions:
                        return sub_pos_name
                elif sub_pos == Position.OUTFIELD:
                    for outfield_pos in ["左翼手", "中堅手", "右翼手"]:
                        if outfield_pos not in assigned_positions:
                            return outfield_pos
        
        # DH制が有効で、DHが空いていればDHに配置
        if self._is_dh_enabled_for_team(team) and "DH" not in assigned_positions:
            return "DH"
        
        return None
    
    def _check_position_conflict(self, team: Team, player_idx: int, target_order: int) -> str:
        """ポジション重複をチェックし、問題があればメッセージを返す"""
        from models import Position
        
        if not hasattr(team, 'position_assignments'):
            return None
        
        player = team.players[player_idx]
        
        # この選手の守備位置を取得
        player_pos = None
        for pos_name, assigned_idx in team.position_assignments.items():
            if assigned_idx == player_idx:
                player_pos = pos_name
                break
        
        if player_pos is None:
            # 守備位置未割り当て
            return None
        
        # 同じ守備位置の選手が既にラインナップにいるか
        for i, lineup_idx in enumerate(team.current_lineup):
            if lineup_idx < 0 or lineup_idx == player_idx:
                continue
            
            # この選手の守備位置を取得
            for pos_name, assigned_idx in team.position_assignments.items():
                if assigned_idx == lineup_idx:
                    if pos_name == player_pos and pos_name != "DH":
                        other_player = team.players[lineup_idx]
                        return f"注意: {other_player.name}と同じ守備位置（{pos_name}）です"
        
        # 外野の特別処理（左中右は別々にカウント）
        if player_pos in ["左翼手", "中堅手", "右翼手"]:
            outfield_count = 0
            for pos_name in team.position_assignments.keys():
                if pos_name in ["左翼手", "中堅手", "右翼手"]:
                    assigned_idx = team.position_assignments[pos_name]
                    if assigned_idx in team.current_lineup:
                        outfield_count += 1
            
            if outfield_count >= 3 and player_idx not in team.current_lineup:
                return "外野手が既に3人います"
        
        return None
    
    def promote_player_to_roster(self, player_idx: int):
        """育成選手を支配下登録に昇格"""
        team = self.state_manager.player_team
        if not team or player_idx < 0 or player_idx >= len(team.players):
            return
        
        player = team.players[player_idx]
        if not player.is_developmental:
            ToastManager.show(f"{player.name}は既に支配下登録です", "warning")
            return
        
        if team.promote_to_roster(player):
            ToastManager.show(f"{player.name}を支配下登録しました！", "success")
            # 背番号を変更（3桁から2桁へ）
            used_numbers = {p.uniform_number for p in team.players if not p.is_developmental and p != player}
            for num in range(1, 100):
                if num not in used_numbers:
                    player.uniform_number = num
                    break
        else:
            ToastManager.show("支配下枠が一杯です", "error")
    
    def add_player_to_lineup(self, player_idx: int):
        """選手をラインアップに追加"""
        team = self.state_manager.player_team
        if not team or player_idx < 0 or player_idx >= len(team.players):
            return
        
        player = team.players[player_idx]
        
        # 既にラインアップに入っているか確認
        if player_idx in team.current_lineup:
            ToastManager.show(f"{player.name}は既にスタメンです", "warning")
            return
        
        # 9人未満なら追加
        if len(team.current_lineup) < 9:
            team.current_lineup.append(player_idx)
            ToastManager.show(f"{player.name}をスタメンに追加", "success")
        else:
            ToastManager.show("スタメンは9人までです", "warning")
    
    def remove_player_from_lineup(self, slot: int):
        """ラインアップから選手を削除"""
        team = self.state_manager.player_team
        if not team:
            return
        
        if 0 <= slot < len(team.current_lineup):
            player_idx = team.current_lineup[slot]
            if player_idx is not None and 0 <= player_idx < len(team.players):
                player_name = team.players[player_idx].name
                team.current_lineup[slot] = None
                # Noneを詰める
                team.current_lineup = [p for p in team.current_lineup if p is not None]
                ToastManager.show(f"{player_name}をスタメンから外しました", "info")
    
    def cycle_lineup_position(self, slot: int):
        """守備位置をサイクル（次のポジションへ変更）"""
        team = self.state_manager.player_team
        if not team:
            return
        
        from settings_manager import settings
        
        # DH制の判定
        is_pacific = hasattr(team, 'league') and team.league.value == "パシフィック"
        use_dh = (is_pacific and settings.game_rules.pacific_dh) or (not is_pacific and settings.game_rules.central_dh)
        
        # 利用可能なポジション
        positions = ["捕", "一", "二", "三", "遊", "左", "中", "右"]
        if use_dh:
            positions.append("DH")
        
        # lineup_positionsを初期化
        if not hasattr(team, 'lineup_positions') or team.lineup_positions is None:
            team.lineup_positions = positions[:9] if use_dh else ["捕", "一", "二", "三", "遊", "左", "中", "右", "投"]
        
        # 9スロット分確保
        while len(team.lineup_positions) < 9:
            team.lineup_positions.append("DH" if use_dh else "投")
        
        if slot < 0 or slot >= 9:
            return
        
        current_pos = team.lineup_positions[slot]
        try:
            current_idx = positions.index(current_pos)
            next_idx = (current_idx + 1) % len(positions)
        except ValueError:
            next_idx = 0
        
        team.lineup_positions[slot] = positions[next_idx]
        ToastManager.show(f"{slot+1}番の守備を{positions[next_idx]}に変更", "info")
    
    def swap_lineup_order(self, from_slot: int, to_slot: int):
        """打順を入れ替える（選手のみ、ポジションは維持）"""
        team = self.state_manager.player_team
        if not team:
            return
        
        lineup = team.current_lineup
        if not lineup:
            return
        
        # lineupの長さが足りない場合は拡張
        while len(lineup) < 9:
            lineup.append(-1)
        
        # インデックスチェック
        if from_slot < 0 or from_slot >= 9 or to_slot < 0 or to_slot >= 9:
            return
        
        # 選手のみを入れ替え（ポジションは維持）
        from_player = lineup[from_slot] if from_slot < len(lineup) else -1
        to_player = lineup[to_slot] if to_slot < len(lineup) else -1
        
        lineup[from_slot] = to_player
        lineup[to_slot] = from_player
        
        ToastManager.show(f"{from_slot+1}番と{to_slot+1}番を入れ替え", "info")
    
    def swap_lineup_position(self, from_slot: int, to_slot: int):
        """ポジションのみを入れ替える"""
        team = self.state_manager.player_team
        if not team:
            return
        
        # lineup_positionsの初期化
        if not hasattr(team, 'lineup_positions') or team.lineup_positions is None:
            team.lineup_positions = ["捕", "一", "二", "三", "遊", "左", "中", "右", "DH"]
        
        while len(team.lineup_positions) < 9:
            team.lineup_positions.append("DH")
        
        # インデックスチェック
        if from_slot < 0 or from_slot >= 9 or to_slot < 0 or to_slot >= 9:
            return
        
        # ポジションのみを入れ替え
        team.lineup_positions[from_slot], team.lineup_positions[to_slot] = \
            team.lineup_positions[to_slot], team.lineup_positions[from_slot]
        
        ToastManager.show(f"{from_slot+1}番と{to_slot+1}番の守備位置を入れ替え", "info")
    
    def set_lineup_position_direct(self, position: str):
        """選択中のスロットに直接ポジションを設定"""
        team = self.state_manager.player_team
        if not team:
            return
        
        # 選択中のスロットがなければ、最後に選択したスロットか最初の空きスロットを使用
        slot = self.selected_lineup_slot
        if slot < 0 or slot >= 9:
            # 空きスロットを探す
            slot = 0
        
        # lineup_positionsを初期化
        if not hasattr(team, 'lineup_positions') or team.lineup_positions is None:
            team.lineup_positions = ["捕", "一", "二", "三", "遊", "左", "中", "右", "DH"]
        
        while len(team.lineup_positions) < 9:
            team.lineup_positions.append("DH")
        
        team.lineup_positions[slot] = position
        ToastManager.show(f"{slot+1}番を{position}に変更", "info")
    
    def _get_pinch_hit_candidates(self) -> list:
        """代打候補選手を取得"""
        team = self.state_manager.player_team
        if not team:
            return []
        
        from models import Position
        
        # 現在のラインナップに入っていない野手
        lineup_set = set(team.current_lineup or [])
        candidates = []
        
        for i, player in enumerate(team.players):
            if i in lineup_set:
                continue
            if player.position == Position.PITCHER:
                continue
            if getattr(player, 'is_developmental', False):
                continue
            candidates.append(player)
        
        # ミートとパワーの合計でソート
        candidates.sort(key=lambda p: p.stats.contact + p.stats.power, reverse=True)
        return candidates[:10]
    
    def _get_pinch_run_candidates(self) -> list:
        """代走候補選手を取得"""
        team = self.state_manager.player_team
        if not team:
            return []
        
        from models import Position
        
        lineup_set = set(team.current_lineup or [])
        candidates = []
        
        for i, player in enumerate(team.players):
            if i in lineup_set:
                continue
            if player.position == Position.PITCHER:
                continue
            if getattr(player, 'is_developmental', False):
                continue
            candidates.append(player)
        
        # 走力でソート
        candidates.sort(key=lambda p: p.stats.speed, reverse=True)
        return candidates[:10]
    
    def _get_relief_pitcher_candidates(self) -> list:
        """継投候補投手を取得"""
        team = self.state_manager.player_team
        if not team:
            return []
        
        from models import Position, PitchType
        
        candidates = []
        current_pitcher_idx = team.starting_pitcher_idx
        
        for i, player in enumerate(team.players):
            if player.position != Position.PITCHER:
                continue
            if i == current_pitcher_idx:
                continue
            if getattr(player, 'is_developmental', False):
                continue
            # 先発投手は中継ぎに使わない（オプション）
            if getattr(player, 'pitch_type', None) == PitchType.STARTER:
                continue
            candidates.append(player)
        
        # 能力でソート（球速 + 制球）
        candidates.sort(key=lambda p: p.stats.speed + p.stats.control, reverse=True)
        return candidates[:8]
    
    def _show_pitcher_change_dialog(self):
        """投手交代ダイアログを表示"""
        candidates = self._get_relief_pitcher_candidates()
        if not candidates:
            ToastManager.show("継投候補がいません", "warning")
            return
        
        self.game_strategy_mode = "pitching_change"
        self.strategy_candidates = candidates
        ToastManager.show("継投する投手を選択してください", "info")
    
    def _execute_pitcher_change(self, new_pitcher):
        """投手交代を実行"""
        team = self.state_manager.player_team
        if not team or not self.game_simulator:
            return
        
        new_pitcher_idx = team.players.index(new_pitcher)
        
        # game_simulatorに投手交代を通知
        if self.game_simulator.home_team == team:
            old_idx = self.game_simulator.current_home_pitcher_idx
            self.game_simulator.current_home_pitcher_idx = new_pitcher_idx
            self.game_simulator.home_pitcher_stats = {'pitch_count': 0, 'innings': 0, 'hits': 0, 'runs': 0, 'walks': 0}
        else:
            old_idx = self.game_simulator.current_away_pitcher_idx
            self.game_simulator.current_away_pitcher_idx = new_pitcher_idx
            self.game_simulator.away_pitcher_stats = {'pitch_count': 0, 'innings': 0, 'hits': 0, 'runs': 0, 'walks': 0}
        
        # ログに追加
        if hasattr(self.game_simulator, 'log'):
            self.game_simulator.log.append(f"投手交代: {new_pitcher.name} がマウンドへ")
        
        # game_watch_stateを更新
        if hasattr(self, 'game_watch_state') and self.game_watch_state:
            self.game_watch_state['current_pitcher'] = new_pitcher
            play_log = self.game_watch_state.get('play_log', [])
            play_log.append(f"投手交代: {new_pitcher.name}")
            self.game_watch_state['play_log'] = play_log
        
        ToastManager.show(f"{new_pitcher.name} がマウンドへ", "success")
        self.game_strategy_mode = None
        self.strategy_candidates = []
    
    def _execute_strategy_substitution(self, candidate_idx: int):
        """戦略的選手交代を実行"""
        if not self.strategy_candidates or candidate_idx >= len(self.strategy_candidates):
            return
        
        new_player = self.strategy_candidates[candidate_idx]
        team = self.state_manager.player_team
        
        if not team:
            return
        
        new_player_idx = team.players.index(new_player)
        
        if self.game_strategy_mode == "pinch_hit":
            # 代打: 現在の打者と交代
            ToastManager.show(f"代打: {new_player.name}", "success")
            # 実際のゲームシミュレータに交代を通知
            if self.game_simulator and hasattr(self.game_simulator, 'substitute_batter'):
                self.game_simulator.substitute_batter(new_player_idx)
        
        elif self.game_strategy_mode == "pinch_run":
            # 代走: 走者と交代
            ToastManager.show(f"代走: {new_player.name}", "success")
            if self.game_simulator and hasattr(self.game_simulator, 'substitute_runner'):
                self.game_simulator.substitute_runner(new_player_idx)
        
        elif self.game_strategy_mode == "pitching_change":
            # 継投（新しい関数を使用）
            self._execute_pitcher_change(new_player)
        
        # ダイアログを閉じる
        self.game_strategy_mode = None
        self.strategy_candidates = []
    
    def _run_game_simulation(self):
        """試合をシミュレーションして結果画面へ"""
        if not self.game_simulator:
            return
        
        # 試合をシミュレート
        self.game_simulator.simulate()
        self.result_scroll = 0
        self.state_manager.change_state(GameState.RESULT)
    
    def release_player(self, player_idx: int):
        """選手を解雇（自由契約）"""
        team = self.state_manager.player_team
        if not team or player_idx < 0 or player_idx >= len(team.players):
            return
        
        player = team.players[player_idx]
        player_name = player.name
        
        # ラインアップから削除
        if player_idx in team.current_lineup:
            team.current_lineup.remove(player_idx)
        
        # 選手リストから削除
        team.players.remove(player)
        
        # ラインアップのインデックスを調整
        team.current_lineup = [i if i < player_idx else i - 1 for i in team.current_lineup if i != player_idx]
        
        if team.starting_pitcher_idx == player_idx:
            team.starting_pitcher_idx = -1
        elif team.starting_pitcher_idx > player_idx:
            team.starting_pitcher_idx -= 1
        
        ToastManager.show(f"{player_name}を自由契約にしました", "warning")
    
    def clear_lineup(self):
        """ラインナップをクリア"""
        if self.state_manager.player_team:
            self.state_manager.player_team.current_lineup = []
            self.state_manager.player_team.starting_pitcher_idx = -1
            if hasattr(self.state_manager.player_team, 'position_assignments'):
                self.state_manager.player_team.position_assignments = {}
            ToastManager.show("オーダーをクリアしました", "info")
    
    def complete_pennant_draft(self):
        """ペナントドラフト確定"""
        if not self.pennant_manager or not self.pennant_draft_picks:
            return
        
        for idx in self.pennant_draft_picks:
            if idx < len(self.pennant_manager.draft_pool):
                draft_player = self.pennant_manager.draft_pool[idx]
                new_player = self.pennant_manager.convert_draft_to_player(draft_player)
                
                # 空き背番号を探す
                used = [p.uniform_number for p in self.state_manager.player_team.players]
                for num in range(1, 100):
                    if num not in used:
                        new_player.uniform_number = num
                        break
                
                self.state_manager.player_team.players.append(new_player)
        
        count = len(self.pennant_draft_picks)
        ToastManager.show(f"{count}人を指名しました！", "success")
        
        self.pennant_draft_picks = []
        self.pennant_manager.advance_phase()
        self.state_manager.change_state(GameState.PENNANT_HOME)
    
    def update_pennant_phase(self):
        """ペナントフェーズに応じて画面遷移"""
        if not self.pennant_manager:
            return
        
        phase = self.pennant_manager.current_phase
        
        if phase == PennantPhase.SPRING_CAMP:
            self.state_manager.change_state(GameState.PENNANT_HOME)
        elif phase == PennantPhase.DRAFT:
            self.state_manager.change_state(GameState.PENNANT_HOME)
        elif phase == PennantPhase.CLIMAX_SERIES:
            self.state_manager.change_state(GameState.PENNANT_CS)
        else:
            self.state_manager.change_state(GameState.PENNANT_HOME)
    
    def simulate_games(self, days: int):
        """指定日数分の試合をシミュレート"""
        if not self.schedule_manager or not self.state_manager.player_team:
            return
        
        simulated = 0
        for _ in range(days):
            # 全球団の試合をシミュレート
            simulated += self.simulate_all_teams_one_day()
            
            # プレイヤーチームの試合がなくなったら終了
            next_game = self.schedule_manager.get_next_game_for_team(self.state_manager.player_team.name)
            if not next_game:
                break
        
        ToastManager.show(f"{simulated}試合をシミュレートしました", "info")
    
    def simulate_all_teams_one_day(self) -> int:
        """全チームの1日分の試合をシミュレート"""
        if not self.schedule_manager:
            return 0
        
        simulated = 0
        
        # 未完了の試合を日付順に取得
        pending_games = [g for g in self.schedule_manager.schedule.games if not g.is_completed]
        if not pending_games:
            return 0
        
        # 最も早い日付の試合を取得
        min_date = min(pending_games, key=lambda g: (g.month, g.day))
        today_games = [g for g in pending_games if g.month == min_date.month and g.day == min_date.day]
        
        for game in today_games:
            home_team = next((t for t in self.state_manager.all_teams if t.name == game.home_team_name), None)
            away_team = next((t for t in self.state_manager.all_teams if t.name == game.away_team_name), None)
            
            if home_team and away_team:
                # 両チームのオーダーを自動設定
                self.auto_set_lineup_for_team(home_team)
                self.auto_set_lineup_for_team(away_team)
                
                # 試合シミュレーション
                sim = GameSimulator(home_team, away_team)
                sim.simulate_game()
                self.schedule_manager.complete_game(game, sim.home_score, sim.away_score)
                simulated += 1
                
                # プレイヤーチームの試合後は育成経験値付与
                player_team_name = self.state_manager.player_team.name if self.state_manager.player_team else None
                if player_team_name and (home_team.name == player_team_name or away_team.name == player_team_name):
                    self._apply_training_after_game()
                
                # ペナントモード時は疲労加算
                if self.pennant_manager:
                    for player in home_team.players:
                        self.pennant_manager.add_fatigue(player, random.randint(2, 5))
                    for player in away_team.players:
                        self.pennant_manager.add_fatigue(player, random.randint(2, 5))
        
        return simulated
    
    def simulate_all_games_until(self, target_game_idx: int):
        """指定した試合インデックスまで全球団の試合をシミュレート"""
        if not self.schedule_manager or not self.state_manager.player_team:
            return
        
        games = self.schedule_manager.get_team_schedule(self.state_manager.player_team.name)
        if target_game_idx >= len(games):
            return
        
        target_game = games[target_game_idx]
        simulated_total = 0
        
        # 選択した試合の直前まで全チームの試合をシミュレート
        while True:
            # 次の試合を確認
            next_idx = next((i for i, g in enumerate(games) if not g.is_completed), len(games))
            
            # 目標の試合に到達したら終了
            if next_idx >= target_game_idx:
                break
            
            # 1日分の全試合をシミュレート
            simulated = self.simulate_all_teams_one_day()
            if simulated == 0:
                break
            simulated_total += simulated
        
        if simulated_total > 0:
            ToastManager.show(f"{simulated_total}試合をシミュレートしました", "success")
        
        # 選択をリセットして次の試合に移動
        self.selected_game_idx = target_game_idx
        
        # スクロール位置を更新
        self.scroll_offset = max(0, target_game_idx - 3)
    
    def _get_effective_team_level(self, player_idx: int):
        """選手の実効的な所属軍を判定（None時は画面表示と同じロジックで判定）"""
        from models import TeamLevel
        from settings_manager import settings
        
        if player_idx >= len(self.state_manager.player_team.players):
            return None
        
        player = self.state_manager.player_team.players[player_idx]
        current_level = getattr(player, 'team_level', None)
        
        # 明示的に設定されている場合はそのまま返す
        if current_level is not None:
            return current_level
        
        # 育成選手は三軍
        if player.is_developmental:
            return TeamLevel.THIRD
        
        # Noneの場合：screens.pyと同じロジックで判定
        first_limit = getattr(settings.game_rules, 'first_team_limit', 31)
        first_count = 0
        
        for i, p in enumerate(self.state_manager.player_team.players):
            if p.is_developmental:
                continue
            level = getattr(p, 'team_level', None)
            if level == TeamLevel.FIRST:
                first_count += 1
            elif level is None:
                # Noneは順番に一軍として数える
                if first_count < first_limit:
                    first_count += 1
                    if i == player_idx:
                        return TeamLevel.FIRST
                else:
                    if i == player_idx:
                        return TeamLevel.SECOND
        
        return TeamLevel.SECOND  # デフォルトは二軍
    
    def _promote_player_farm(self, player_idx: int):
        """選手を上の軍に昇格（二軍→一軍、三軍→二軍）"""
        from models import TeamLevel
        from settings_manager import settings
        
        if player_idx >= len(self.state_manager.player_team.players):
            return
        
        player = self.state_manager.player_team.players[player_idx]
        
        # 育成選手は昇格不可（別途「支配下昇格」を使う）
        if player.is_developmental:
            self._show_error("育成選手は支配下昇格が必要です")
            return
        
        # 現在の所属軍を取得
        current_level = getattr(player, 'team_level', None)
        first_limit = getattr(settings.game_rules, 'first_team_limit', 31)
        
        # 現在の一軍人数をカウント
        first_count = self._count_first_team_players()
        
        if current_level == TeamLevel.SECOND:
            # 二軍→一軍
            if first_count >= first_limit:
                self._show_error(f"一軍枠が満員です ({first_count}/{first_limit})")
                return
            player.team_level = TeamLevel.FIRST
            
            # ベンチに追加（野手はベンチ野手、投手はベンチ投手）
            from models import Position
            if player.position != Position.PITCHER:
                bench_batters = getattr(self.state_manager.player_team, 'bench_batters', []) or []
                if player_idx not in bench_batters:
                    bench_batters.append(player_idx)
                    self.state_manager.player_team.bench_batters = bench_batters
            else:
                bench_pitchers = getattr(self.state_manager.player_team, 'bench_pitchers', []) or []
                if player_idx not in bench_pitchers:
                    bench_pitchers.append(player_idx)
                    self.state_manager.player_team.bench_pitchers = bench_pitchers
        elif current_level == TeamLevel.THIRD:
            # 三軍→二軍
            player.team_level = TeamLevel.SECOND
        elif current_level == TeamLevel.FIRST:
            self._show_error("すでに一軍に登録されています")
        elif current_level is None:
            # Noneの場合：一軍枠に空きがあれば一軍へ
            if first_count < first_limit:
                player.team_level = TeamLevel.FIRST
            else:
                self._show_error(f"一軍枠が満員です ({first_count}/{first_limit})")
    
    def _promote_player_from_third(self, player_idx: int):
        """選手を三軍から二軍に昇格"""
        from models import TeamLevel
        
        if player_idx >= len(self.state_manager.player_team.players):
            return
        
        player = self.state_manager.player_team.players[player_idx]
        
        # 実効的な所属軍を判定
        effective_level = self._get_effective_team_level(player_idx)
        
        if effective_level == TeamLevel.THIRD:
            # 三軍→二軍
            player.team_level = TeamLevel.SECOND
        elif effective_level == TeamLevel.SECOND:
            pass  # すでに二軍
        elif effective_level == TeamLevel.FIRST:
            pass  # すでに一軍
        else:
            pass  # 昇格先がない
    
    def _demote_player_farm(self, player_idx: int):
        """選手を下の軍に降格（一軍→二軍、二軍→三軍）"""
        from models import TeamLevel
        from settings_manager import settings
        
        if player_idx >= len(self.state_manager.player_team.players):
            return
        
        player = self.state_manager.player_team.players[player_idx]
        team = self.state_manager.player_team
        
        # 実効的な所属軍を判定
        effective_level = self._get_effective_team_level(player_idx)
        enable_third = getattr(settings.game_rules, 'enable_third_team', False)
        
        if effective_level == TeamLevel.FIRST:
            # 一軍→二軍
            # 一軍スロットから選手を削除
            self._remove_player_from_first_team_slots(player_idx)
            player.team_level = TeamLevel.SECOND
        elif effective_level == TeamLevel.SECOND:
            # 二軍→三軍（三軍制が有効な場合のみ）
            if enable_third:
                player.team_level = TeamLevel.THIRD
        elif effective_level == TeamLevel.THIRD:
            pass  # すでに三軍
        else:
            pass  # 降格先がない
    
    def _remove_player_from_first_team_slots(self, player_idx: int):
        """選手を一軍のすべてのスロットから削除"""
        team = self.state_manager.player_team
        
        # スタメンから削除
        if team.current_lineup:
            for i in range(len(team.current_lineup)):
                if team.current_lineup[i] == player_idx:
                    team.current_lineup[i] = None
        
        # ベンチ野手から削除
        bench_batters = getattr(team, 'bench_batters', None)
        if bench_batters and player_idx in bench_batters:
            team.bench_batters = [b for b in bench_batters if b != player_idx]
        
        # ベンチ投手から削除
        bench_pitchers = getattr(team, 'bench_pitchers', None)
        if bench_pitchers and player_idx in bench_pitchers:
            team.bench_pitchers = [b for b in bench_pitchers if b != player_idx]
        
        # 先発ローテーションから削除
        rotation = getattr(team, 'rotation', None)
        if rotation:
            for i in range(len(rotation)):
                if rotation[i] == player_idx:
                    team.rotation[i] = -1
        
        # 中継ぎから削除
        setup_pitchers = getattr(team, 'setup_pitchers', None)
        if setup_pitchers:
            for i in range(len(setup_pitchers)):
                if setup_pitchers[i] == player_idx:
                    team.setup_pitchers[i] = -1
        
        # 抑えから削除
        if getattr(team, 'closer_idx', -1) == player_idx:
            team.closer_idx = -1
        
        # 先発投手から削除
        if getattr(team, 'starting_pitcher_idx', -1) == player_idx:
            team.starting_pitcher_idx = -1
    
    def _count_first_team_players(self) -> int:
        """一軍の選手数をカウント"""
        from models import TeamLevel
        team = self.state_manager.player_team
        first_team_set = set()
        
        # スタメン
        lineup = team.current_lineup or []
        first_team_set.update(p_idx for p_idx in lineup if p_idx is not None and p_idx >= 0)
        
        # ベンチ野手
        bench_batters = getattr(team, 'bench_batters', []) or []
        first_team_set.update(b_idx for b_idx in bench_batters if b_idx >= 0)
        
        # 先発ローテーション
        rotation = getattr(team, 'rotation', []) or []
        first_team_set.update(r_idx for r_idx in rotation if r_idx >= 0)
        
        # 中継ぎ
        setup_pitchers = getattr(team, 'setup_pitchers', []) or []
        first_team_set.update(s_idx for s_idx in setup_pitchers if s_idx >= 0)
        
        # 抑え
        closer = getattr(team, 'closer', -1)
        if closer >= 0:
            first_team_set.add(closer)
        
        return len(first_team_set)
    
    def _ensure_pitcher_in_lineup_if_no_dh(self, team):
        """DHなしの場合、投手を9番に入れる"""
        from settings_manager import settings
        
        if not team:
            return
        
        # DHルールを判定
        is_pacific = hasattr(team, 'league') and team.league.value == "パシフィック"
        use_dh = (is_pacific and settings.game_rules.pacific_dh) or (not is_pacific and settings.game_rules.central_dh)
        
        if use_dh:
            return  # DHありなら何もしない
        
        # DHなしの場合、9番に投手を入れる
        if team.starting_pitcher_idx < 0:
            return  # 投手が設定されていない
        
        lineup = team.current_lineup or []
        if len(lineup) < 9:
            lineup = lineup + [None] * (9 - len(lineup))
            team.current_lineup = lineup
        
        pitcher_idx = team.starting_pitcher_idx
        
        # 投手が既にラインナップにいる場合はその位置を確認
        if pitcher_idx in lineup:
            return  # 既にいるので何もしない
        
        # 9番に投手を入れる
        lineup[8] = pitcher_idx
        team.current_lineup = lineup
        
        # lineup_positionsの9番を「投」に設定
        if hasattr(team, 'lineup_positions') and team.lineup_positions:
            while len(team.lineup_positions) < 9:
                team.lineup_positions.append("投")
            team.lineup_positions[8] = "投"

    def run(self):
        """メインループ"""
        clock = pygame.time.Clock()
        running = True
        
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            
            pygame.display.flip()
            clock.tick(60)
        
        pygame.quit()
        sys.exit()


def main():
    """エントリーポイント"""
    game = NPBGame()
    game.run()


if __name__ == "__main__":
    main()
