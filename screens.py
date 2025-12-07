# -*- coding: utf-8 -*-
"""
NPBペナントシミュレーター - 画面描画モジュール
すべての画面をプロフェッショナルなデザインで統一
"""
import pygame
import math
import time
import random
from typing import Dict, List, Optional, Tuple

from ui_pro import (
    Colors, fonts, FontManager,
    Button, Card, ProgressBar, Table, RadarChart,
    Toast, ToastManager,
    draw_background, draw_header, draw_rounded_rect, draw_shadow,
    draw_selection_effect, lerp_color
)
from constants import (
    TEAM_COLORS, NPB_CENTRAL_TEAMS, NPB_PACIFIC_TEAMS,
    NPB_STADIUMS, TEAM_ABBREVIATIONS, NPB_BATTING_TITLES, NPB_PITCHING_TITLES
)
from game_state import DifficultyLevel
from models import Team, Player


# ========================================
# 3D投影システム（サイバーパンク風トラッキング用）
# ========================================
class Vector3:
    """3Dベクトルクラス"""
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z
    
    def copy(self):
        return Vector3(self.x, self.y, self.z)


class CyberField3D:
    """サイバーパンク風3D野球場レンダラー（Ursina風）"""
    
    # 物理定数
    GRAVITY = -9.8 * 2  # ゲーム用に重力を強めに
    DRAG = 0.005        # 空気抵抗
    FIELD_SCALE = 1.0   # 全体のスケール
    
    # デフォルトカメラ設定（見やすい位置に固定）
    DEFAULT_CAMERA_HEIGHT = 30.0
    DEFAULT_CAMERA_DIST = -25.0
    DEFAULT_CAMERA_ANGLE = 8.0
    DEFAULT_FOV = 550
    
    # 野球定数（デフォルト）- NPB標準値
    BASE_FENCE_DIST = 122  # センターまでの基準距離（メートル）
    BASE_FENCE_DIST_CORNER = 100  # 両翼の基準距離（メートル）
    BASE_FENCE_DIST_ALLEY = 116   # 左中間・右中間の基準距離（メートル）
    FENCE_HEIGHT = 4.2    # フェンスの高さ（メートル）
    
    # 色定義（サイバーパンク風）
    COLOR_BG = (5, 10, 20)
    COLOR_GRID = (0, 255, 255, 50)
    COLOR_GRID_LINE = (0, 80, 80)
    COLOR_GRID_FAR = (0, 40, 40)  # 遠くのグリッド線
    COLOR_BALL = (255, 200, 100)
    COLOR_BALL_GLOW = (255, 150, 50)
    COLOR_TRAIL = (255, 150, 50)
    COLOR_FENCE = (255, 0, 255)
    COLOR_POLE = (255, 255, 0)
    COLOR_TEXT = (0, 255, 255)
    COLOR_FOUL_LINE = (0, 255, 255)
    COLOR_BASE = (255, 255, 255)
    COLOR_RUNNER = (255, 180, 50)
    COLOR_FIELDER = (0, 255, 100)
    COLOR_FIELDER_CHASE = (255, 255, 0)
    
    # 守備位置データ (x, z) - メートル単位
    # x = 左右（正がライト）、z = 前方（正がセンター）
    FIELDER_POSITIONS = {
        'P': (0, 18.44),      # マウンド
        'C': (0, -1),         # キャッチャー
        '1B': (15, 20),       # 一塁手
        '2B': (8, 28),        # 二塁手
        '3B': (-15, 20),      # 三塁手
        'SS': (-8, 28),       # 遊撃手
        'LF': (-32, 85),      # レフト（NPB標準守備位置）
        'CF': (0, 85),        # センター（NPB標準守備位置）
        'RF': (32, 85),       # ライト（NPB標準守備位置）
    }
    
    # フェンス境界（角度に応じた距離）- NPB標準
    FENCE_DISTANCES = {
        'left_pole': 100,     # レフトポール（両翼）
        'left_center': 116,   # 左中間
        'center': 122,        # センター
        'right_center': 116,  # 右中間
        'right_pole': 100,    # ライトポール（両翼）
    }
    
    # 視点プリセット
    VIEW_PRESETS = {
        'broadcast': {'height': 8.0, 'dist': -15.0, 'angle': 15.0, 'fov': 600, 'name': '放送席'},
        'backstop': {'height': 4.0, 'dist': -8.0, 'angle': 10.0, 'fov': 700, 'name': 'バックネット'},
        'blimp': {'height': 80.0, 'dist': 30.0, 'angle': 60.0, 'fov': 500, 'name': '俯瞰'},
        'tracking': {'height': 5.0, 'dist': -10.0, 'angle': 12.0, 'fov': 650, 'name': 'トラッキング'},
        'centerfield': {'height': 10.0, 'dist': 80.0, 'angle': -5.0, 'fov': 600, 'name': 'センター'},
        'firstbase': {'height': 8.0, 'dist': 10.0, 'angle': 15.0, 'fov': 600, 'name': '一塁側', 'offset_x': 30},
    }
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.width = screen.get_width()
        self.height = screen.get_height()
        self.vanishing_point_x = self.width / 2
        self.vanishing_point_y = self.height * 0.0
        
        # カメラ設定（可変）
        self.camera_height = self.DEFAULT_CAMERA_HEIGHT
        self.camera_dist = self.DEFAULT_CAMERA_DIST
        self.camera_angle = self.DEFAULT_CAMERA_ANGLE
        self.camera_offset_x = 0.0
        self.fov = self.DEFAULT_FOV
        self.current_view = 'broadcast'
        
        # ボール追跡カメラモード
        self.tracking_mode = False
        self.camera_target = None  # カメラが追跡する対象位置
        
        # 球場設定（NPB標準）
        self.fence_dist_center = self.BASE_FENCE_DIST  # 122m
        self.fence_dist_left = self.BASE_FENCE_DIST_CORNER  # 100m
        self.fence_dist_right = self.BASE_FENCE_DIST_CORNER  # 100m
        self.fence_dist_left_center = self.BASE_FENCE_DIST_ALLEY  # 116m
        self.fence_dist_right_center = self.BASE_FENCE_DIST_ALLEY  # 116m
        self.park_factor = 1.0
        self.stadium_name = ""
        
        # 守備者の現在位置（追跡AI用）
        self.fielder_current_pos = {pos: list(coord) for pos, coord in self.FIELDER_POSITIONS.items()}
        self.chasing_fielder = None  # 現在追跡中の野手
        self.fielder_reaction_time = {}  # 各野手の反応時間追跡
        self.ball_trajectory_cache = []  # 軌道データキャッシュ
        self.estimated_landing_point = None  # 予測落下点
        self.ball_direction = None  # 打球方向ベクトル
        self.ball_caught = False  # 捕球フラグ
        self.bounce_position = None  # バウンド後の位置
        
        # 守備能力（ポジション別、0-100）
        self.fielder_abilities = {
            'P': {'speed': 50, 'fielding': 50, 'arm': 60},
            'C': {'speed': 40, 'fielding': 70, 'arm': 80},
            '1B': {'speed': 45, 'fielding': 60, 'arm': 60},
            '2B': {'speed': 65, 'fielding': 70, 'arm': 65},
            '3B': {'speed': 55, 'fielding': 65, 'arm': 75},
            'SS': {'speed': 70, 'fielding': 75, 'arm': 75},
            'LF': {'speed': 65, 'fielding': 60, 'arm': 70},
            'CF': {'speed': 75, 'fielding': 70, 'arm': 75},
            'RF': {'speed': 60, 'fielding': 60, 'arm': 80},
        }
        
        # アニメーション用
        self.ball_position = [0, 1, 0]  # x, y(高さ), z
        self.ball_velocity = [0, 0, 0]
        self.ball_trail = []  # 軌跡ポイント
        self.is_ball_flying = False
        self.ball_landed = False
        
        # 走者AIシステム
        self.runner_positions = {}  # {base: (x, z, progress)} progress=0-1で塁間進捗
        self.runner_states = {}     # {base: 'waiting'|'running'|'returning'|'stopped'}
        self.runner_speeds = {}     # {base: speed_value}
        self.batter_runner = None   # 打者走者の状態
        self.batter_runner_pos = [0, 0]  # 打者走者の位置
        self.batter_runner_progress = 0  # 打者走者の進捗
        
        # 送球システム
        self.throw_state = None     # {'from': pos, 'to': base, 'ball_pos': [x,y,z], 'progress': 0-1}
        self.throw_target_base = None  # 送球先塁
        self.play_result = None     # {'outs': [], 'safe': [], 'runs': 0}
        self.fielder_with_ball = None  # ボールを持っている野手
        
        # 超進化版守備AIシステム（NPB完全再現）
        self.fielder_momentum = {}      # 野手の移動momentum（慣性）
        self.fielder_acceleration = {}   # 野手の加速度
        self.fielder_facing_dir = {}     # 野手の向き（送球時重要）
        self.diving_state = {}           # ダイビングキャッチ状態
        self.catch_animation = None      # 捕球アニメーション
        self.defensive_play_type = None  # 'routine'|'hard'|'spectacular'
        self.ball_spin_effect = 0        # 打球のスピンによる曲がり
        self.wind_effect = (0, 0)        # 風の影響(x, z)
        
        # NPBリアル守備能力詳細
        self.fielder_details = {
            'P': {'range': 6, 'first_step': 0.25, 'glove_size': 11.5, 'dive_ability': 40},
            'C': {'range': 4, 'first_step': 0.30, 'glove_size': 33.0, 'dive_ability': 50},
            '1B': {'range': 8, 'first_step': 0.22, 'glove_size': 12.5, 'dive_ability': 60},
            '2B': {'range': 12, 'first_step': 0.18, 'glove_size': 11.25, 'dive_ability': 75},
            '3B': {'range': 10, 'first_step': 0.20, 'glove_size': 11.75, 'dive_ability': 70},
            'SS': {'range': 14, 'first_step': 0.17, 'glove_size': 11.5, 'dive_ability': 80},
            'LF': {'range': 20, 'first_step': 0.20, 'glove_size': 12.75, 'dive_ability': 65},
            'CF': {'range': 25, 'first_step': 0.18, 'glove_size': 12.75, 'dive_ability': 85},
            'RF': {'range': 18, 'first_step': 0.22, 'glove_size': 12.75, 'dive_ability': 60},
        }
        
        # 結果表示システム（画面上部用）
        self.result_display = {
            'text': '',
            'sub_text': '',
            'color': (255, 255, 255),
            'animation_time': 0,
            'show_duration': 3.0,
            'fielder_credit': '',  # "CF 好捕！" など
        }
        
    def set_stadium(self, home_run_factor: float = 1.0, stadium_name: str = ""):
        """球場のパークファクターに基づいてフェンス距離を設定"""
        self.park_factor = home_run_factor
        self.stadium_name = stadium_name
        # パークファクターによる調整（1.0が標準、1.1は狭い球場、0.9は広い球場）
        factor_adjustment = (1.0 - home_run_factor) * 10  # 調整幅を抑える
        self.fence_dist_center = int(self.BASE_FENCE_DIST + factor_adjustment)
        self.fence_dist_left = int(self.BASE_FENCE_DIST_CORNER + factor_adjustment * 0.5)
        self.fence_dist_right = int(self.BASE_FENCE_DIST_CORNER + factor_adjustment * 0.5)
        self.fence_dist_left_center = int(self.BASE_FENCE_DIST_ALLEY + factor_adjustment * 0.7)
        self.fence_dist_right_center = int(self.BASE_FENCE_DIST_ALLEY + factor_adjustment * 0.7)
    
    def set_view(self, view_name: str):
        """視点プリセットを設定"""
        if view_name in self.VIEW_PRESETS:
            preset = self.VIEW_PRESETS[view_name]
            self.camera_height = preset['height']
            self.camera_dist = preset['dist']
            self.camera_angle = preset['angle']
            self.fov = preset['fov']
            self.camera_offset_x = preset.get('offset_x', 0.0)
            self.current_view = view_name
            self.tracking_mode = (view_name == 'tracking')
    
    def cycle_view(self, direction: int = 1):
        """視点を切り替え"""
        view_names = list(self.VIEW_PRESETS.keys())
        current_idx = view_names.index(self.current_view) if self.current_view in view_names else 0
        new_idx = (current_idx + direction) % len(view_names)
        self.set_view(view_names[new_idx])
        return self.VIEW_PRESETS[view_names[new_idx]]['name']
    
    def handle_drag(self, dx: int, dy: int, button: int = 1):
        """ドラッグによる視点操作"""
        if button == 1:
            self.camera_offset_x = max(-60.0, min(60.0, self.camera_offset_x - dx * 0.2))
            self.camera_angle = max(-20.0, min(80.0, self.camera_angle + dy * 0.15))
        elif button == 3:
            self.camera_dist = max(-30.0, min(120.0, self.camera_dist + dy * 0.3))
            self.camera_height = max(3.0, min(100.0, self.camera_height - dx * 0.15))
        self.current_view = 'custom'
        self.tracking_mode = False
    
    def handle_scroll(self, scroll_y: int):
        """マウスホイールでズーム"""
        self.fov = max(300, min(1000, self.fov + scroll_y * 25))
        self.current_view = 'custom'
    
    def reset_fielders(self):
        """守備位置をリセット"""
        self.fielder_current_pos = {pos: list(coord) for pos, coord in self.FIELDER_POSITIONS.items()}
        self.chasing_fielder = None
        self.fielder_reaction_time = {}  # 反応時間もリセット
        self.ball_trajectory_cache = []  # 軌道キャッシュもリセット
        self.estimated_landing_point = None  # 予測落下点
        self.ball_direction = None  # 打球方向ベクトル
        self.ball_caught = False  # 捕球フラグ
        self.bounce_position = None  # バウンド後の位置
        # 走者AIもリセット
        self.runner_positions = {}
        self.runner_states = {}
        # 送球システムリセット
        self.throw_state = None
        self.throw_target_base = None
        self.play_result = {'outs': [], 'safe': [], 'runs': 0}
        self.fielder_with_ball = None
        self.runner_speeds = {}
        self.batter_runner = None
        self.batter_runner_pos = [0, 0]
        self.batter_runner_progress = 0
        # 超進化版守備AIリセット
        self.fielder_momentum = {pos: [0, 0] for pos in self.FIELDER_POSITIONS}
        self.fielder_acceleration = {pos: 0 for pos in self.FIELDER_POSITIONS}
        self.fielder_facing_dir = {pos: [0, 1] for pos in self.FIELDER_POSITIONS}
        self.diving_state = {}
    
    def set_defensive_shift(self, shift_type: str = 'normal'):
        """守備シフトを設定
        
        shift_type:
            'normal' - 通常の守備位置
            'pull' - プルシフト（引っ張り打者対策、内野を一塁側へ）
            'opposite' - 逆方向シフト（流し打ち打者対策、内野を三塁側へ）
            'no_doubles' - 二塁打阻止シフト（外野深め）
            'infield_in' - 内野前進守備（ホームゲッツー狙い）
            'bunt_defense' - バント守備
        """
        # 通常位置を基準にする
        base = self.FIELDER_POSITIONS
        
        if shift_type == 'normal':
            self.fielder_current_pos = {pos: list(coord) for pos, coord in base.items()}
        
        elif shift_type == 'pull':
            # プルシフト：内野を一塁側（x+方向）へシフト
            self.fielder_current_pos = {
                'P': list(base['P']),
                'C': list(base['C']),
                '1B': [base['1B'][0] + 3, base['1B'][1]],
                '2B': [base['2B'][0] + 10, base['2B'][1] + 3],  # 二遊間寄り
                'SS': [base['SS'][0] + 12, base['SS'][1]],  # 二塁ベース付近
                '3B': [base['3B'][0] + 5, base['3B'][1]],
                'LF': [base['LF'][0] + 8, base['LF'][1]],
                'CF': [base['CF'][0] + 10, base['CF'][1]],
                'RF': [base['RF'][0] - 5, base['RF'][1]],
            }
        
        elif shift_type == 'opposite':
            # 逆方向シフト：内野を三塁側（x-方向）へシフト
            self.fielder_current_pos = {
                'P': list(base['P']),
                'C': list(base['C']),
                '1B': [base['1B'][0] - 5, base['1B'][1]],
                '2B': [base['2B'][0] - 10, base['2B'][1]],
                'SS': [base['SS'][0] - 8, base['SS'][1] + 3],
                '3B': [base['3B'][0] - 3, base['3B'][1]],
                'LF': [base['LF'][0] + 5, base['LF'][1]],
                'CF': [base['CF'][0] - 10, base['CF'][1]],
                'RF': [base['RF'][0] - 8, base['RF'][1]],
            }
        
        elif shift_type == 'no_doubles':
            # 二塁打阻止シフト：外野深め
            self.fielder_current_pos = {
                'P': list(base['P']),
                'C': list(base['C']),
                '1B': list(base['1B']),
                '2B': [base['2B'][0], base['2B'][1] + 5],
                'SS': [base['SS'][0], base['SS'][1] + 5],
                '3B': list(base['3B']),
                'LF': [base['LF'][0] - 5, base['LF'][1] + 15],
                'CF': [base['CF'][0], base['CF'][1] + 15],
                'RF': [base['RF'][0] + 5, base['RF'][1] + 15],
            }
        
        elif shift_type == 'infield_in':
            # 内野前進守備
            self.fielder_current_pos = {
                'P': list(base['P']),
                'C': list(base['C']),
                '1B': [base['1B'][0], base['1B'][1] - 8],
                '2B': [base['2B'][0], base['2B'][1] - 10],
                'SS': [base['SS'][0], base['SS'][1] - 10],
                '3B': [base['3B'][0], base['3B'][1] - 8],
                'LF': list(base['LF']),
                'CF': list(base['CF']),
                'RF': list(base['RF']),
            }
        
        elif shift_type == 'bunt_defense':
            # バント守備
            self.fielder_current_pos = {
                'P': list(base['P']),
                'C': list(base['C']),
                '1B': [base['1B'][0] - 3, base['1B'][1] - 12],  # 前進
                '2B': [base['2B'][0] + 5, base['2B'][1]],  # 一塁カバー
                'SS': list(base['SS']),
                '3B': [base['3B'][0] + 3, base['3B'][1] - 12],  # 前進
                'LF': list(base['LF']),
                'CF': list(base['CF']),
                'RF': list(base['RF']),
            }
        self.catch_animation = None
        self.defensive_play_type = None
    
    def set_result_display(self, text: str, sub_text: str = '', color: tuple = None, fielder_credit: str = ''):
        """結果表示を設定（画面上部用）"""
        if color is None:
            # テキストに応じた色を自動設定
            if 'ホームラン' in text:
                color = (255, 100, 100)
            elif 'ヒット' in text or '二塁打' in text or '三塁打' in text:
                color = (0, 255, 150)
            elif 'アウト' in text or '三振' in text:
                color = (150, 150, 180)
            elif '四球' in text:
                color = (100, 200, 255)
            elif '好捕' in text or 'ファインプレー' in text:
                color = (255, 215, 0)
            else:
                color = (255, 255, 255)
        
        self.result_display = {
            'text': text,
            'sub_text': sub_text,
            'color': color,
            'animation_time': 0,
            'show_duration': 3.0,
            'fielder_credit': fielder_credit
        }
    
    # ========================================
    # 走者AIシステム
    # ========================================
    
    # 塁の座標（メートル）
    BASE_COORDS = {
        'home': (0, 0),
        '1B': (19.4, 19.4),    # 約27.43m/√2
        '2B': (0, 38.8),      # 約27.43m*√2
        '3B': (-19.4, 19.4),
    }
    
    def init_runners(self, runners_on_base, runner_speeds=None):
        """走者を初期化（打球発生時に呼び出す）
        runners_on_base: [1塁, 2塁, 3塁] のboolean or Player
        runner_speeds: {base: speed_value}
        """
        self.runner_positions = {}
        self.runner_states = {}
        self.runner_speeds = runner_speeds or {}
        
        base_names = ['1B', '2B', '3B']
        for i, has_runner in enumerate(runners_on_base):
            if has_runner:
                base = base_names[i]
                self.runner_positions[base] = list(self.BASE_COORDS[base]) + [0.0]  # x, z, progress
                self.runner_states[base] = 'waiting'  # 初期状態
                if base not in self.runner_speeds:
                    self.runner_speeds[base] = 60  # デフォルト走力
        
        # 打者走者を初期化
        self.batter_runner = True
        self.batter_runner_pos = [0, 0]  # ホームから開始
        self.batter_runner_progress = 0
        self.batter_runner_speed = 60  # デフォルト
    
    def set_batter_runner_speed(self, speed):
        """打者走者の走力を設定"""
        self.batter_runner_speed = speed
    
    def update_runners_ai(self, dt, ball_state, is_fly=False, is_caught=False):
        """走者AIを更新
        ball_state: {'position': (x, y, z), 'landed': bool, 'fielder_has_ball': bool}
        """
        if not (self.runner_positions or self.batter_runner):
            return
        
        # 打球状態から走塁判断
        ball_pos = ball_state.get('position', (0, 0, 0))
        ball_landed = ball_state.get('landed', False)
        fielder_has_ball = ball_state.get('fielder_has_ball', False) or self.ball_caught
        ball_distance = math.sqrt(ball_pos[0]**2 + ball_pos[2]**2) if ball_pos else 0
        
        # 各走者のAI更新
        for base in list(self.runner_positions.keys()):
            state = self.runner_states.get(base, 'waiting')
            speed = self.runner_speeds.get(base, 60)
            
            # 走者AI判断
            if state == 'waiting':
                if is_fly and not ball_landed:
                    # フライの場合、タッチアップ準備
                    self.runner_states[base] = 'tagging'
                elif not is_fly or ball_landed:
                    # ゴロ/ライナーまたはフライ落下後 - 走塁開始
                    self.runner_states[base] = 'running'
            
            elif state == 'tagging':
                # タッチアップ待機中
                if is_caught:
                    # 捕球された - タッチアップスタート（走力に応じて判断）
                    if base == '3B' and speed >= 50:
                        self.runner_states[base] = 'running'  # 3塁走者はホーム狙い
                    elif ball_distance > 80 and speed >= 70:
                        self.runner_states[base] = 'running'  # 深いフライなら進塁
                    else:
                        self.runner_states[base] = 'stopped'
                elif not is_fly or ball_landed:
                    # フライが落ちた - 走塁開始
                    self.runner_states[base] = 'running'
            
            elif state == 'running':
                # 走塁中
                if fielder_has_ball:
                    # 野手がボールを持っている - 帰塁判断
                    progress = self.runner_positions[base][2] if len(self.runner_positions[base]) > 2 else 0
                    if progress < 0.5:
                        self.runner_states[base] = 'returning'
                    else:
                        # 次の塁に向かう（走力に応じて）
                        pass
            
            # 実際の移動処理
            self._move_runner(base, dt)
        
        # 打者走者のAI更新
        if self.batter_runner:
            self._update_batter_runner_ai(dt, ball_state, is_fly, is_caught)
    
    def _move_runner(self, base, dt):
        """走者を移動させる"""
        state = self.runner_states.get(base, 'stopped')
        if state == 'stopped' or state == 'tagging':
            return
        
        speed = self.runner_speeds.get(base, 60)
        # NPB選手の走力: speed 50=約6.5m/s, 100=約9.5m/s
        run_speed = 6.0 + (speed / 100) * 3.5
        
        if len(self.runner_positions[base]) < 3:
            self.runner_positions[base].append(0.0)
        
        pos = self.runner_positions[base]
        progress = pos[2]
        
        # 目標塁を決定
        next_base_map = {'1B': '2B', '2B': '3B', '3B': 'home'}
        prev_base_map = {'1B': 'home', '2B': '1B', '3B': '2B'}
        
        if state == 'running':
            next_base = next_base_map.get(base)
            if next_base:
                target = self.BASE_COORDS[next_base]
                current = self.BASE_COORDS[base]
                # 進塁方向に移動
                dist_total = math.sqrt((target[0] - current[0])**2 + (target[1] - current[1])**2)
                progress_add = (run_speed * dt) / dist_total if dist_total > 0 else 0
                new_progress = min(1.0, progress + progress_add)
                
                # 座標更新
                pos[0] = current[0] + (target[0] - current[0]) * new_progress
                pos[1] = current[1] + (target[1] - current[1]) * new_progress
                pos[2] = new_progress
                
                # 次の塁に到達
                if new_progress >= 1.0:
                    if next_base == 'home':
                        # ホームイン - 走者削除
                        del self.runner_positions[base]
                        del self.runner_states[base]
                    else:
                        # 次の塁に移動
                        del self.runner_positions[base]
                        del self.runner_states[base]
                        self.runner_positions[next_base] = [target[0], target[1], 0.0]
                        self.runner_states[next_base] = 'running'
                        self.runner_speeds[next_base] = speed
        
        elif state == 'returning':
            prev_base = prev_base_map.get(base, base)
            target = self.BASE_COORDS[prev_base] if prev_base != 'home' else self.BASE_COORDS[base]
            current_x, current_z = pos[0], pos[1]
            # 帰塁方向に移動
            dist = math.sqrt((target[0] - current_x)**2 + (target[1] - current_z)**2)
            if dist > 0.5:
                dx = (target[0] - current_x) / dist
                dz = (target[1] - current_z) / dist
                pos[0] += dx * run_speed * dt
                pos[1] += dz * run_speed * dt
                pos[2] = max(0, pos[2] - (run_speed * dt) / 27.43)
            else:
                self.runner_states[base] = 'stopped'
                pos[2] = 0
    
    def _update_batter_runner_ai(self, dt, ball_state, is_fly, is_caught):
        """打者走者のAI"""
        if not self.batter_runner:
            return
        
        # フライが捕球されたらアウト
        if is_caught and is_fly:
            self.batter_runner = None
            return
        
        speed = getattr(self, 'batter_runner_speed', 60)
        run_speed = 6.0 + (speed / 100) * 3.5
        
        # 一塁に向かって走る
        target = self.BASE_COORDS['1B']
        current = self.batter_runner_pos
        
        dist = math.sqrt((target[0] - current[0])**2 + (target[1] - current[1])**2)
        if dist > 0.5:
            dx = (target[0] - current[0]) / dist
            dz = (target[1] - current[1]) / dist
            self.batter_runner_pos[0] += dx * run_speed * dt
            self.batter_runner_pos[1] += dz * run_speed * dt
            self.batter_runner_progress = 1.0 - (dist / 27.43)
        else:
            # 一塁到達
            self.batter_runner = None
            # 一塁走者として登録
            if '1B' not in self.runner_positions:
                self.runner_positions['1B'] = [target[0], target[1], 0.0]
                self.runner_states['1B'] = 'stopped'
                self.runner_speeds['1B'] = speed
    
    def get_runner_draw_positions(self):
        """描画用の走者位置を取得"""
        positions = {}
        for base, pos in self.runner_positions.items():
            positions[base] = (pos[0], pos[1])
        if self.batter_runner:
            positions['batter'] = tuple(self.batter_runner_pos)
        return positions
    
    # ===== NPB完全再現 送球システム =====
    def start_throw(self, from_fielder, to_base):
        """送球を開始（NPB完全再現版）"""
        if from_fielder not in self.fielder_current_pos:
            return
        
        from_pos = self.fielder_current_pos[from_fielder]
        to_coord = self.BASE_COORDS.get(to_base, (0, 0))
        
        # 送球者の肩力と守備力を取得
        ability = self.fielder_abilities.get(from_fielder, {})
        arm_strength = ability.get('arm', 60)
        fielding = ability.get('fielding', 50)
        
        # NPBリアル送球速度（肩力依存: 32-50 m/s = 115-180 km/h）
        base_throw_speed = 32 + (arm_strength / 100) * 18
        
        # 守備力によるスムーズな送球（高守備力は素早くリリース）
        transfer_time = 0.4 - (fielding / 200)  # 0.15-0.4秒の送球準備
        
        # 送球距離
        dist = math.sqrt((to_coord[0] - from_pos[0])**2 + (to_coord[1] - from_pos[1])**2)
        
        # 遠投時の速度低下
        if dist > 40:
            base_throw_speed *= 0.92
        elif dist > 60:
            base_throw_speed *= 0.85
        
        throw_time = dist / base_throw_speed if base_throw_speed > 0 else 1.0
        
        # 野手の向きによる送球精度
        facing = self.fielder_facing_dir.get(from_fielder, [0, 1])
        to_dir = [to_coord[0] - from_pos[0], to_coord[1] - from_pos[1]]
        dir_len = math.sqrt(to_dir[0]**2 + to_dir[1]**2)
        if dir_len > 0:
            to_dir = [to_dir[0]/dir_len, to_dir[1]/dir_len]
        
        # 向きと送球方向のずれで送球時間が増加
        dot = facing[0] * to_dir[0] + facing[1] * to_dir[1]
        turn_penalty = max(0, 0.15 * (1 - dot))  # 後ろ向きだと最大0.15秒追加
        
        self.throw_state = {
            'from': from_fielder,
            'to': to_base,
            'from_pos': list(from_pos),
            'to_pos': list(to_coord),
            'ball_pos': [from_pos[0], 2.0, from_pos[1]],  # x, height, z
            'progress': 0.0,
            'throw_time': throw_time + transfer_time + turn_penalty,
            'throw_speed': base_throw_speed,
            'distance': dist,
            'arm_strength': arm_strength,
            'is_double_play': to_base == '2B' and self.batter_runner is not None,
        }
        self.throw_target_base = to_base
        self.fielder_with_ball = None  # 送球中はボールを持っていない
        
        # 送球時の向きを更新
        self.fielder_facing_dir[from_fielder] = to_dir
    
    def update_throw(self, dt):
        """送球を更新（NPB完全再現版）"""
        if not self.throw_state:
            return None
        
        state = self.throw_state
        state['progress'] += dt / state['throw_time']
        
        # 送球中のボール位置を補間
        p = state['progress']
        fx, fz = state['from_pos']
        tx, tz = state['to_pos']
        
        # NPBリアル送球軌道
        # 短距離はライナー、長距離は放物線
        dist = state['distance']
        if dist < 20:
            arc_height = dist * 0.05  # ライナー
        elif dist < 40:
            arc_height = dist * 0.07  # 中距離
        else:
            arc_height = min(dist * 0.1, 5.0)  # 長距離の山なり
        
        height = 1.8 + arc_height * 4 * p * (1 - p)  # 放物線
        
        state['ball_pos'] = [
            fx + (tx - fx) * p,
            height,
            fz + (tz - fz) * p
        ]
        
        # 送球完了
        if state['progress'] >= 1.0:
            target_base = state['to']
            is_dp = state.get('is_double_play', False)
            self.throw_state = None
            self.fielder_with_ball = self._get_fielder_at_base(target_base)
            
            result = self._check_out_at_base(target_base)
            
            # ダブルプレー判定
            if is_dp and result.get('out') and target_base == '2B':
                # 二塁でアウト後、一塁へ転送
                dp_fielder = self.fielder_with_ball or '2B'
                self.start_throw(dp_fielder, '1B')
                result['double_play_attempt'] = True
            
            return result
        
        return None
        return None
    
    def _get_fielder_at_base(self, base):
        """塁をカバーしている野手を取得（NPBリアル）"""
        # 実際にベースカバーに入っている野手を確認
        base_coords = self.BASE_COORDS.get(base, (0, 0))
        
        default_fielders = {
            'home': 'C',
            '1B': '1B',
            '2B': 'SS',  # デフォルトはSS
            '3B': '3B'
        }
        
        # ベース付近の野手を探す
        min_dist = float('inf')
        nearest_fielder = default_fielders.get(base)
        
        for pos, (fx, fz) in self.fielder_current_pos.items():
            dist = math.sqrt((fx - base_coords[0])**2 + (fz - base_coords[1])**2)
            if dist < 3.0 and dist < min_dist:  # 3m以内でベースカバー
                min_dist = dist
                nearest_fielder = pos
        
        return nearest_fielder
    
    def _check_out_at_base(self, base):
        """塁でのアウト判定（NPB完全再現版）"""
        result = {'out': False, 'safe': False, 'runner': None, 'base': base, 'play_type': 'force'}
        
        # 打者走者の一塁到達チェック
        if base == '1B' and self.batter_runner:
            # 打者走者の一塁までの残り距離から到達時間を推定
            runner_dist = math.sqrt(
                (self.batter_runner_pos[0] - self.BASE_COORDS['1B'][0])**2 +
                (self.batter_runner_pos[1] - self.BASE_COORDS['1B'][1])**2
            )
            
            # 走者速度から残り時間を計算
            runner_speed = self.runner_speeds.get('batter', 7.0)
            runner_remaining_time = runner_dist / runner_speed if runner_speed > 0 else 1.0
            
            # ギリギリの判定（0.1秒以内は5分5分）
            if runner_remaining_time > 0.15:
                result['out'] = True
                result['runner'] = 'batter'
                self.batter_runner = None
                if self.play_result:
                    self.play_result['outs'].append('batter@1B')
                self.set_result_display('アウト！', 'ゴロアウト', (150, 150, 180))
            elif runner_remaining_time > 0.05:
                # きわどいタイミング（ランダム要素）
                if random.random() < 0.5:
                    result['out'] = True
                    result['runner'] = 'batter'
                    self.batter_runner = None
                    if self.play_result:
                        self.play_result['outs'].append('batter@1B')
                    self.set_result_display('アウト！', 'きわどいタイミング', (150, 150, 180))
                else:
                    result['safe'] = True
                    result['runner'] = 'batter'
                    self.set_result_display('セーフ！', 'きわどいタイミング', (0, 255, 150))
            else:
                result['safe'] = True
                result['runner'] = 'batter'
                self.set_result_display('セーフ！', '内野安打', (0, 255, 150))
            return result
        
        # 各塁の走者チェック
        # フォースアウトの塁を判定
        prev_base_map = {'2B': '1B', '3B': '2B', 'home': '3B'}
        prev_base = prev_base_map.get(base)
        
        if prev_base and prev_base in self.runner_positions:
            runner_pos = self.runner_positions[prev_base]
            runner_progress = runner_pos[2] if len(runner_pos) > 2 else 0
            
            # NPBリアル判定（進捗度ベース）
            if runner_progress < 0.90:
                result['out'] = True
                result['runner'] = prev_base
                del self.runner_positions[prev_base]
                if prev_base in self.runner_states:
                    del self.runner_states[prev_base]
                if self.play_result:
                    self.play_result['outs'].append(f'{prev_base}@{base}')
                self.set_result_display('アウト！', f'{prev_base}走者フォースアウト', (150, 150, 180))
            elif runner_progress < 0.98:
                # きわどいタイミング
                if random.random() < 0.4:
                    result['out'] = True
                    result['runner'] = prev_base
                    del self.runner_positions[prev_base]
                    if prev_base in self.runner_states:
                        del self.runner_states[prev_base]
                    if self.play_result:
                        self.play_result['outs'].append(f'{prev_base}@{base}')
                    self.set_result_display('アウト！', 'きわどいタイミング', (150, 150, 180))
                else:
                    result['safe'] = True
                    result['runner'] = prev_base
                    self.set_result_display('セーフ！', '', (0, 255, 150))
            else:
                result['safe'] = True
                result['runner'] = prev_base
        
        return result
    
    def decide_throw_target(self, fielder_pos, ball_type):
        """最適な送球先を決定（守備AI）"""
        # 走者状況を確認
        has_batter_runner = self.batter_runner is not None
        runners = list(self.runner_positions.keys())
        
        # フォースアウトの塁を優先
        force_bases = []
        if has_batter_runner:
            force_bases.append('1B')
            if '1B' in runners:
                force_bases.append('2B')
                if '2B' in runners:
                    force_bases.append('3B')
                    if '3B' in runners:
                        force_bases.append('home')
        
        # 最も近い走者への送球を選択
        best_base = '1B'  # デフォルト
        
        if force_bases:
            # 一番アウトにしやすい塁を選択
            # ダブルプレー狙い: 2塁→1塁
            if '2B' in force_bases and ball_type == 'infield_grounder':
                best_base = '2B'  # ダブルプレー狙い
            elif 'home' in force_bases and '3B' in runners:
                # 3塁走者がいてホームフォースなら本塁
                best_base = 'home'
            else:
                best_base = force_bases[0]
        elif runners:
            # タッチプレーが必要な場合
            # 最も進んでいる走者を狙う
            if '3B' in runners:
                best_base = 'home'
            elif '2B' in runners:
                best_base = '3B'
            else:
                best_base = '1B'
        
        return best_base
    
    def get_throw_ball_position(self):
        """送球中のボール位置を取得"""
        if self.throw_state:
            return self.throw_state['ball_pos']
        return None

    def predict_landing_point(self, trajectory, current_frame):
        """打球の軌道から落下点を予測する
        軌道座標: (x=左右, y=前方距離, z=高さ)
        フィールド座標: (x=左右, z=前方距離) - 高さは無視
        """
        if not trajectory or len(trajectory) < 2:
            return None
        
        # 軌道から地面に近い点を探す
        for point in trajectory:
            if isinstance(point, dict):
                x, y, z = point.get('x', 0), point.get('y', 0), point.get('z', 0)
            elif isinstance(point, (list, tuple)) and len(point) >= 3:
                x, y, z = point[0], point[1], point[2]
            else:
                continue
            # z(高さ)が低い点 = 着地点
            if z <= 0.5:
                return (x, y)  # フィールド座標 (x=左右, z=前方距離としてyを使用)
        
        # 最後のポイントを返す
        last_point = trajectory[-1]
        if isinstance(last_point, dict):
            return (last_point.get('x', 0), last_point.get('y', 0))
        elif isinstance(last_point, (list, tuple)) and len(last_point) >= 3:
            return (last_point[0], last_point[1])
        return None
    
    def calculate_ball_line(self, trajectory):
        """打球の移動直線（方向ベクトル）を計算
        軌道座標: (x=左右, y=前方距離, z=高さ)
        """
        if not trajectory or len(trajectory) < 2:
            return None
        
        first = trajectory[0]
        last = trajectory[-1]
        
        if isinstance(first, dict):
            x1, y1 = first.get('x', 0), first.get('y', 0)
        else:
            x1, y1 = first[0], first[1]
        
        if isinstance(last, dict):
            x2, y2 = last.get('x', 0), last.get('y', 0)
        else:
            x2, y2 = last[0], last[1]
        
        # 方向ベクトル（正規化）- フィールド座標系
        dx, dy = x2 - x1, y2 - y1
        length = math.sqrt(dx*dx + dy*dy)
        if length > 0:
            return {'dx': dx/length, 'dy': dy/length, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'length': length}
        return None
    
    def point_to_line_distance(self, px, py, line):
        """点から打球直線への最短距離と最近点を計算"""
        if not line:
            return float('inf'), px, py
        
        x1, y1 = line['x1'], line['y1']
        x2, y2 = line['x2'], line['y2']
        
        dx = x2 - x1
        dy = y2 - y1
        line_len_sq = dx*dx + dy*dy
        
        if line_len_sq == 0:
            return math.sqrt((px - x1)**2 + (py - y1)**2), x1, y1
        
        # 点から直線への射影点を計算（直線上のみ、延長しない）
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / line_len_sq))
        
        nearest_x = x1 + t * dx
        nearest_y = y1 + t * dy
        
        dist = math.sqrt((px - nearest_x)**2 + (py - nearest_y)**2)
        
        return dist, nearest_x, nearest_y
    
    def set_trajectory_for_fielders(self, trajectory):
        """守備AI用に軌道データをセット"""
        self.ball_trajectory_cache = trajectory if trajectory else []
        self.ball_caught = False
        self.bounce_position = None
        if trajectory:
            self.estimated_landing_point = self.predict_landing_point(trajectory, 0)
            self.ball_direction = self.calculate_ball_line(trajectory)
        else:
            self.estimated_landing_point = None
            self.ball_direction = None
    
    def get_fence_distance_at_angle(self, angle_deg):
        """角度に応じたフェンス距離を取得（放物線補間）"""
        # angle_deg: 0=センター、-45=レフト、+45=ライト
        abs_angle = abs(angle_deg)
        if abs_angle <= 20:
            # センター付近
            return 122 - (abs_angle / 20) * 12  # 122m -> 110m
        elif abs_angle <= 45:
            # 中間からポールへ
            return 110 - ((abs_angle - 20) / 25) * 10  # 110m -> 100m
        else:
            return 100  # ファウルゾーン
    
    def is_within_field(self, x, z):
        """座標がフィールド内かチェック"""
        if z < -5:  # バックネット後方
            return False
        
        # フェンス境界チェック
        if z > 10:  # 内野より奥
            angle_rad = math.atan2(x, z)
            angle_deg = math.degrees(angle_rad)
            fence_dist = self.get_fence_distance_at_angle(angle_deg)
            distance = math.sqrt(x**2 + z**2)
            if distance > fence_dist - 2:  # フェンス手前2mまで
                return False
        
        # ファウルライン外（大きく外れた場合）
        if abs(x) > 80:
            return False
        
        return True
    
    def clamp_to_field(self, x, z, pos):
        """座標をフィールド内に制限"""
        # バックネット
        z = max(-3, z)
        
        # フェンス境界
        if z > 10:
            angle_rad = math.atan2(x, z)
            angle_deg = math.degrees(angle_rad)
            fence_dist = self.get_fence_distance_at_angle(angle_deg)
            distance = math.sqrt(x**2 + z**2)
            max_dist = fence_dist - 3  # フェンス手前3m
            
            if distance > max_dist:
                # フェンス方向に制限
                scale = max_dist / distance
                x = x * scale
                z = z * scale
        
        # 左右制限（ファウルゾーン考慮）
        max_x = 70 if z < 50 else 60
        x = max(-max_x, min(max_x, x))
        
        return x, z
    
    def update_fielders_for_ball(self, ball_pos, trajectory=None):
        """打球位置に応じて野手を移動させる（超現実的版）
        
        軌道座標系: (x=左右, y=前方距離, z=高さ)
        フィールド座標系: (x=左右, z=前方距離) ※守備位置用
        """
        # フレームタイム（30FPS想定）
        dt = 0.033
        
        # 送球中の場合は送球を更新（ただし野手の動きは継続）
        if self.throw_state:
            throw_result = self.update_throw(dt)
            if throw_result:
                # 送球完了後のアウト判定結果を保存
                if throw_result.get('out'):
                    self.play_result = self.play_result or {'outs': []}
                    # 結果表示は_check_out_at_base内で設定済み
            # 送球中でも野手はカバー位置へ移動を継続
        
        if not ball_pos:
            return
        
        # 捕球後は野手の動きを継続（カバーリング）
        # ball_caughtでreturnしない
        
        # 軌道データが渡されたらキャッシュ
        if trajectory:
            self.ball_trajectory_cache = trajectory
            self.estimated_landing_point = self.predict_landing_point(trajectory, 0)
            self.ball_direction = self.calculate_ball_line(trajectory)
        
        # ball_pos解析（軌道座標系: x=左右, y=前方, z=高さ）
        try:
            if isinstance(ball_pos, dict):
                bx = ball_pos.get('x', 0)      # 左右
                by = ball_pos.get('y', 0)      # 前方距離
                bz = ball_pos.get('z', 0)      # 高さ
            elif isinstance(ball_pos, (list, tuple)) and len(ball_pos) >= 3:
                bx, by, bz = ball_pos[0], ball_pos[1], ball_pos[2]
            else:
                return
        except (KeyError, IndexError, TypeError):
            return
        
        # フィールド座標での打球位置
        ball_x = bx       # 左右位置
        ball_z = by       # 前方距離（奥行き）
        ball_y = bz       # 高さ
        
        # フレームタイム
        dt = 0.033
        
        # 打球の種類を判定
        ball_type = self._classify_ball_type(ball_x, ball_y, ball_z)
        
        # 全野手の動きを更新（実際の守備を完全再現）
        self._update_all_fielders_realistic(ball_x, ball_y, ball_z, ball_type, dt)
        
        # ボール位置を更新
        self.ball_position = [ball_x, ball_y, ball_z]
    
    def _update_all_fielders_realistic(self, ball_x, ball_y, ball_z, ball_type, dt):
        """全野手の動きを実際の守備のように更新"""
        
        # 1. 打球の目標地点を計算（落下点 or 現在位置）
        if ball_y > 3.0 and self.estimated_landing_point:
            target_x, target_z = self.estimated_landing_point
        else:
            target_x, target_z = ball_x, ball_z
        
        # 2. 捕球済みの場合は送球者以外がカバー移動のみ
        if self.ball_caught:
            for pos in list(self.fielder_current_pos.keys()):
                if pos == self.fielder_with_ball:
                    continue  # ボールを持っている野手は動かない
                fx, fz = self.fielder_current_pos[pos]
                ability = self.fielder_abilities.get(pos, {})
                speed = ability.get('speed', 50)
                # カバー位置へ移動
                new_x, new_z = self._fielder_cover_position(pos, fx, fz, ball_x, ball_z, self.fielder_with_ball, ball_type, speed, dt)
                new_x, new_z = self.clamp_to_field(new_x, new_z, pos)
                self.fielder_current_pos[pos] = [new_x, new_z]
            return
        
        # 3. 最適な守備者を選択
        chaser = self._select_primary_fielder(ball_x, ball_y, ball_z, target_x, target_z, ball_type)
        self.chasing_fielder = chaser
        
        # 4. 全野手を役割別に動かす
        for pos in list(self.fielder_current_pos.keys()):
            fx, fz = self.fielder_current_pos[pos]
            ability = self.fielder_abilities.get(pos, {})
            speed = ability.get('speed', 50)
            fielding = ability.get('fielding', 50)
            
            if pos == chaser:
                # 主守備者：ボールを追う
                new_x, new_z = self._fielder_chase_ball(pos, fx, fz, target_x, target_z, ball_x, ball_y, ball_z, speed, fielding, dt)
            else:
                # その他：カバーリング/バックアップ
                new_x, new_z = self._fielder_cover_position(pos, fx, fz, ball_x, ball_z, chaser, ball_type, speed, dt)
            
            # フィールド境界チェック
            new_x, new_z = self.clamp_to_field(new_x, new_z, pos)
            self.fielder_current_pos[pos] = [new_x, new_z]
    
    def _select_primary_fielder(self, ball_x, ball_y, ball_z, target_x, target_z, ball_type):
        """打球に対する主守備者を選択（実際の守備判断を再現）"""
        
        # 打球方向の角度
        angle = math.degrees(math.atan2(ball_x, ball_z)) if ball_z > 0 else 0
        
        # 打球の種類と位置による優先順位
        candidates = []
        
        for pos, (fx, fz) in self.fielder_current_pos.items():
            # 距離計算
            dist = math.sqrt((fx - target_x)**2 + (fz - target_z)**2)
            
            # ポジション別の適性判定
            score = dist  # 基本は距離（小さいほど良い）
            
            # 打球種別による適性
            if ball_type == 'infield_grounder':
                # 内野ゴロ：内野手優先
                if pos in ['1B', '2B', 'SS', '3B']:
                    score *= 0.6
                elif pos == 'P' and ball_z < 20 and abs(ball_x) < 8:
                    score *= 0.7
                elif pos in ['LF', 'CF', 'RF']:
                    continue  # 外野手は対象外
            
            elif ball_type in ['fly', 'high_fly']:
                # 外野フライ：外野手優先
                if pos in ['LF', 'CF', 'RF']:
                    score *= 0.5
                elif pos in ['1B', '2B', 'SS', '3B'] and ball_z < 50:
                    score *= 0.8  # 浅いフライは内野も対応
                else:
                    continue
            
            elif ball_type == 'infield_fly':
                # 内野フライ：内野手優先
                if pos in ['1B', '2B', 'SS', '3B', 'C']:
                    score *= 0.6
                elif pos == 'P' and ball_z < 15:
                    score *= 0.7
            
            elif ball_type in ['liner', 'liner_infield', 'line_drive']:
                # ライナー：反応勝負
                if ball_z < 40:
                    if pos in ['1B', '2B', 'SS', '3B', 'P']:
                        score *= 0.65
                else:
                    if pos in ['LF', 'CF', 'RF']:
                        score *= 0.6
            
            elif ball_type in ['through_grounder', 'outfield_grounder']:
                # 外野への抜けるゴロ
                if pos in ['LF', 'CF', 'RF']:
                    score *= 0.5
            
            # 打球方向による補正
            if angle > 20 and pos in ['1B', '2B', 'RF']:
                score *= 0.85
            elif angle < -20 and pos in ['3B', 'SS', 'LF']:
                score *= 0.85
            elif abs(angle) < 15 and pos in ['CF', 'P', 'SS', '2B']:
                score *= 0.85
            
            # 守備力による補正
            ability = self.fielder_abilities.get(pos, {})
            fielding = ability.get('fielding', 50)
            score *= (1.0 - fielding / 500)
            
            candidates.append((pos, score, dist))
        
        # 最適な守備者を選択
        if candidates:
            candidates.sort(key=lambda x: x[1])
            return candidates[0][0]
        
        # フォールバック：最も近い野手
        min_dist = float('inf')
        nearest = 'SS'
        for pos, (fx, fz) in self.fielder_current_pos.items():
            dist = math.sqrt((fx - target_x)**2 + (fz - target_z)**2)
            if dist < min_dist:
                min_dist = dist
                nearest = pos
        return nearest
    
    def _fielder_chase_ball(self, pos, fx, fz, target_x, target_z, ball_x, ball_y, ball_z, speed, fielding, dt):
        """守備者がボールを追う動き（実際の動きを再現）"""
        
        # 反応時間チェック
        reaction_time = self.fielder_reaction_time.get(pos, 0)
        self.fielder_reaction_time[pos] = reaction_time + dt
        
        # プロ野手の反応時間（0.10-0.25秒）
        base_reaction = 0.18 - (fielding - 50) * 0.001
        base_reaction = max(0.10, min(0.25, base_reaction))
        
        if reaction_time < base_reaction:
            return fx, fz  # 反応待ち
        
        # 目標地点への距離
        dist_to_target = math.sqrt((target_x - fx)**2 + (target_z - fz)**2)
        dist_to_ball = math.sqrt((ball_x - fx)**2 + (ball_z - fz)**2)
        
        # 捕球判定
        details = self.fielder_details.get(pos, {})
        catch_range = 3.0 + (fielding / 100) * 3.0  # 3.0m〜6.0m
        
        # ゴロは範囲広め
        if ball_y <= 2.0:
            catch_range *= 1.3
        
        # 捕球可能かチェック
        can_catch = False
        if ball_y <= 2.5:
            # ゴロ/低い打球
            can_catch = dist_to_ball < catch_range
        elif ball_y <= 10.0:
            # ライナー
            can_catch = dist_to_ball < catch_range * 0.9
        else:
            # フライ（落下点で待機）
            can_catch = dist_to_target < catch_range * 0.7
        
        if can_catch:
            # 捕球成功
            self.ball_caught = True
            self.fielder_with_ball = pos
            self.defensive_play_type = 'routine' if dist_to_ball < catch_range * 0.5 else 'hard'
            
            # 送球開始
            ball_type = self._classify_ball_type(ball_x, ball_y, ball_z)
            throw_target = self.decide_throw_target(pos, ball_type)
            if throw_target and (self.batter_runner or self.runner_positions):
                self.start_throw(pos, throw_target)
            return fx, fz
        
        # ボールを追う
        if dist_to_target < 0.3:
            return fx, fz
        
        # === NPB超現実的な走り方 ===
        # プロ野手のスプリント速度: 7.5-9.5 m/s (菊池涼介 9.2m/s、源田壮亮 9.0m/s)
        base_speed = 7.5 + (speed / 100) * 2.0  # 7.5-9.5 m/s
        
        # 加速度曲線（0-100%への加速）
        # プロ野手は約0.4秒で最高速の80%に達する
        accel_time = reaction_time - base_reaction
        if accel_time < 0.2:
            accel = accel_time / 0.2 * 0.6  # 最初の0.2秒で60%
        elif accel_time < 0.4:
            accel = 0.6 + (accel_time - 0.2) / 0.2 * 0.3  # 次の0.2秒で90%
        else:
            accel = min(1.0, 0.9 + (accel_time - 0.4) / 0.3 * 0.1)  # その後で100%
        
        actual_speed = base_speed * accel
        
        # 方向転換のペナルティ（急な方向転換は速度低下）
        dx_raw = (target_x - fx)
        dz_raw = (target_z - fz)
        
        # 前フレームの移動方向を取得
        prev_dir = self.fielder_facing_dir.get(pos, [0, 1])
        new_dir = [dx_raw / dist_to_target, dz_raw / dist_to_target]
        
        # 方向の変化量
        dot = prev_dir[0] * new_dir[0] + prev_dir[1] * new_dir[1]
        turn_factor = max(0.5, (1 + dot) / 2)  # 後ろ向きだと50%速度低下
        actual_speed *= turn_factor
        
        # 向きを更新
        self.fielder_facing_dir[pos] = new_dir
        
        # ダイビング/スライディングキャッチの判定
        if dist_to_ball < catch_range * 1.5 and dist_to_ball > catch_range * 0.8:
            # ギリギリの範囲ならダイブ
            if ball_y <= 3.0 and fielding > 60:
                actual_speed *= 1.2  # ダイビング補正
        
        return fx + new_dir[0] * actual_speed * dt, fz + new_dir[1] * actual_speed * dt
    
    def _fielder_cover_position(self, pos, fx, fz, ball_x, ball_z, chaser, ball_type, speed, dt):
        """カバーリング位置への移動（NPB完全再現版）
        
        実際のプロ野球における守備連携を忠実に再現
        - ベースカバー
        - 中継プレー
        - バックアップ
        - カットオフ位置
        """
        
        # ベース座標
        BASES = {
            'home': (0, 0),
            '1B': (19.4, 19.4),
            '2B': (0, 27.43),
            '3B': (-19.4, 19.4)
        }
        
        # ランナー状況を確認
        has_runners = bool(self.runner_positions)
        has_batter_runner = self.batter_runner is not None
        
        # 打球方向（-45°=レフト方向、+45°=ライト方向）
        angle = math.degrees(math.atan2(ball_x, ball_z)) if ball_z > 0 else 0
        ball_dist = math.sqrt(ball_x**2 + ball_z**2)
        
        # 目標位置を決定
        target_x, target_z = fx, fz
        
        # ========== 投手 P ==========
        if pos == 'P':
            if ball_type == 'infield_grounder':
                if chaser in ['1B', '2B'] and angle >= 0:
                    # 一塁方向のゴロ：一塁ベースカバー
                    target_x, target_z = 18, 18
                elif chaser in ['3B', 'SS'] and angle < 0:
                    # 三塁方向のゴロ：本塁カバー補助
                    target_x, target_z = 3, 5
                else:
                    # 投手前のゴロなど：一塁ベースカバー
                    target_x, target_z = 16, 16
            elif ball_type in ['fly', 'high_fly', 'liner'] and ball_dist > 50:
                # 外野への打球：バックアップ位置
                target_x, target_z = 0, 20
            else:
                # 一塁ベースカバーがデフォルト
                target_x, target_z = 17, 17
        
        # ========== 捕手 C ==========
        elif pos == 'C':
            # 捕手は常にホームベース付近
            if chaser in ['LF', 'CF', 'RF'] and ball_dist > 60:
                # 外野への長打：ホーム前で中継の構え
                target_x, target_z = 0, 3
            else:
                target_x, target_z = 0, 0
        
        # ========== 一塁手 1B ==========
        elif pos == '1B':
            if chaser == '1B':
                pass  # 自分が追いかけ中
            elif has_batter_runner or has_runners:
                # ランナーがいる場合は一塁ベース
                target_x, target_z = 19.4, 19.4
            elif ball_type in ['fly', 'high_fly'] and angle > 20:
                # ライト方向のフライ：ファウルゾーンカバー
                target_x, target_z = 25, 15
            else:
                target_x, target_z = 19.4, 19.4
        
        # ========== 二塁手 2B ==========
        elif pos == '2B':
            if chaser == '2B':
                pass
            elif chaser in ['RF', 'CF'] and ball_dist > 55:
                # 右中間・中堅への打球：中継位置
                cutoff_x = ball_x * 0.35 + 8
                cutoff_z = max(35, ball_z * 0.4)
                target_x, target_z = cutoff_x, cutoff_z
            elif chaser == 'LF' and ball_dist > 55:
                # レフトへの打球：二塁ベースカバー
                target_x, target_z = 0, 27.43
            elif angle >= 5:
                # 右方向のゴロ：一塁ベース付近でカバー
                if chaser == '1B':
                    target_x, target_z = 19.4, 19.4
                else:
                    target_x, target_z = 12, 22
            else:
                # 左方向のゴロ：二塁ベースカバー
                target_x, target_z = 0, 27.43
        
        # ========== 遊撃手 SS ==========
        elif pos == 'SS':
            if chaser == 'SS':
                pass
            elif chaser in ['LF', 'CF'] and ball_dist > 55:
                # 左中間・レフトへの打球：中継位置
                cutoff_x = ball_x * 0.35 - 8
                cutoff_z = max(35, ball_z * 0.4)
                target_x, target_z = cutoff_x, cutoff_z
            elif chaser == 'RF' and ball_dist > 55:
                # ライトへの打球：二塁ベースカバー
                target_x, target_z = 0, 27.43
            elif angle < -5:
                # 左方向のゴロ：三塁ベースカバー補助
                if chaser == '3B':
                    target_x, target_z = -15, 22
                else:
                    target_x, target_z = -10, 25
            else:
                # 右方向のゴロ：二塁ベースカバー
                target_x, target_z = 0, 27.43
        
        # ========== 三塁手 3B ==========
        elif pos == '3B':
            if chaser == '3B':
                pass
            elif has_runners and '2B' in self.runner_positions:
                # 二塁走者がいる場合は三塁ベース
                target_x, target_z = -19.4, 19.4
            elif ball_type in ['fly', 'high_fly'] and angle < -20:
                # レフト方向のフライ：ファウルゾーンカバー
                target_x, target_z = -25, 15
            else:
                target_x, target_z = -19.4, 19.4
        
        # ========== 左翼手 LF ==========
        elif pos == 'LF':
            if chaser == 'LF':
                pass
            elif chaser == 'CF':
                # センターが追いかけ中：左中間バックアップ
                chaser_pos = self.fielder_current_pos.get(chaser, [-20, 70])
                target_x = chaser_pos[0] - 15
                target_z = chaser_pos[1] + 12
            elif chaser == 'RF':
                # ライトが追いかけ中：センター方向カバー
                target_x = -10
                target_z = 60
            elif ball_type in ['fly', 'high_fly', 'liner']:
                # フライ系：打球方向に備える
                target_x = max(-50, ball_x - 12)
                target_z = max(55, min(90, ball_z * 0.85))
            else:
                # ゴロ系：前進守備
                target_x = max(-45, ball_x - 8)
                target_z = 50
        
        # ========== 中堅手 CF ==========
        elif pos == 'CF':
            if chaser == 'CF':
                pass
            elif chaser == 'LF':
                # レフトが追いかけ中：左中間バックアップ
                chaser_pos = self.fielder_current_pos.get(chaser, [-20, 70])
                target_x = chaser_pos[0] + 12
                target_z = chaser_pos[1] + 15
            elif chaser == 'RF':
                # ライトが追いかけ中：右中間バックアップ
                chaser_pos = self.fielder_current_pos.get(chaser, [20, 70])
                target_x = chaser_pos[0] - 12
                target_z = chaser_pos[1] + 15
            elif ball_type in ['fly', 'high_fly', 'liner']:
                # フライ系：打球方向をカバー
                target_x = ball_x * 0.6
                target_z = max(60, min(95, ball_z * 0.9))
            else:
                # ゴロ系：適度に前進
                target_x = ball_x * 0.5
                target_z = 55
        
        # ========== 右翼手 RF ==========
        elif pos == 'RF':
            if chaser == 'RF':
                pass
            elif chaser == 'CF':
                # センターが追いかけ中：右中間バックアップ
                chaser_pos = self.fielder_current_pos.get(chaser, [20, 70])
                target_x = chaser_pos[0] + 15
                target_z = chaser_pos[1] + 12
            elif chaser == 'LF':
                # レフトが追いかけ中：センター方向カバー
                target_x = 10
                target_z = 60
            elif ball_type in ['fly', 'high_fly', 'liner']:
                # フライ系：打球方向に備える
                target_x = min(50, ball_x + 12)
                target_z = max(55, min(90, ball_z * 0.85))
            else:
                # ゴロ系：前進守備
                target_x = min(45, ball_x + 8)
                target_z = 50
        
        # 目標に向かって移動（カバーリングは少しゆっくり）
        dist = math.sqrt((target_x - fx)**2 + (target_z - fz)**2)
        if dist > 0.5:
            # カバーリング速度：5.5-7.5 m/s
            move_speed = 5.5 + (speed / 100) * 2.0
            dx = (target_x - fx) / dist
            dz = (target_z - fz) / dist
            
            # 向きを更新
            self.fielder_facing_dir[pos] = [dx, dz]
            
            return fx + dx * move_speed * dt, fz + dz * move_speed * dt
        
        return fx, fz
    
    def _classify_ball_type(self, ball_x, ball_y, ball_z):
        """打球の種類を分類
        ball_x=左右, ball_y=高さ, ball_z=前方距離
        """
        distance = math.sqrt(ball_x**2 + ball_z**2)
        
        if ball_y > 25:
            return 'high_fly'
        elif ball_y > 12:
            if distance > 60:
                return 'fly'
            else:
                return 'infield_fly'
        elif ball_y > 5:
            if distance > 50:
                return 'liner'
            else:
                return 'liner_infield'
        elif ball_y > 1.5:
            return 'line_drive'
        elif distance < 30:
            return 'infield_grounder'
        elif distance < 50:
            return 'through_grounder'
        else:
            return 'outfield_grounder'
    
    def start_ball_flight(self, ball_data: dict):
        """打球の飛行を開始"""
        if ball_data is None:
            return
        
        self.reset_fielders()
        self.ball_position = [0, 1, 0]
        self.ball_trail = []
        self.is_ball_flying = True
        self.ball_landed = False
        
        # 物理ベクトル計算
        ev_km = ball_data.get('exit_velocity', 140)
        la_deg = ball_data.get('launch_angle', 25)
        spray = ball_data.get('direction', 0)
        
        ev_ms = ev_km * 1000 / 3600
        rad_la = math.radians(la_deg)
        rad_spray = math.radians(spray)
        
        self.ball_velocity = [
            ev_ms * math.cos(rad_la) * math.sin(rad_spray),
            ev_ms * math.sin(rad_la),
            ev_ms * math.cos(rad_la) * math.cos(rad_spray)
        ]
        
        # トラッキングモードに切り替え
        if self.current_view == 'broadcast':
            self.tracking_mode = True
    
    def update_ball_physics(self, dt: float = 0.016):
        """ボールの物理更新（毎フレーム呼び出し）"""
        if not self.is_ball_flying or self.ball_landed:
            return None
        
        game_dt = dt * 2.5  # ゲーム速度
        
        # 重力
        self.ball_velocity[1] += self.GRAVITY * game_dt
        # 空気抵抗
        drag_factor = 1 - self.DRAG * game_dt
        self.ball_velocity = [v * drag_factor for v in self.ball_velocity]
        
        # 移動
        self.ball_position[0] += self.ball_velocity[0] * game_dt
        self.ball_position[1] += self.ball_velocity[1] * game_dt
        self.ball_position[2] += self.ball_velocity[2] * game_dt
        
        # 軌跡に追加
        self.ball_trail.append(tuple(self.ball_position))
        if len(self.ball_trail) > 60:
            self.ball_trail.pop(0)
        
        # 守備AI更新
        self._update_fielder_ai(game_dt)
        
        # トラッキングカメラ更新
        if self.tracking_mode:
            self._update_tracking_camera(game_dt)
        
        # 地面判定
        if self.ball_position[1] <= 0.5:
            self.ball_position[1] = 0.5
            self.ball_landed = True
            self.is_ball_flying = False
            
            # 結果を返す
            dist = math.sqrt(self.ball_position[0]**2 + self.ball_position[2]**2)
            return {
                'landed': True,
                'distance': dist,
                'position': tuple(self.ball_position),
                'chasing_fielder': self.chasing_fielder
            }
        
        return {'landed': False, 'distance': math.sqrt(self.ball_position[0]**2 + self.ball_position[2]**2)}
    
    def set_fielder_abilities(self, fielding_team):
        """守備チームの能力を設定"""
        if not fielding_team or not hasattr(fielding_team, 'players'):
            return
        
        # ポジションに応じた選手の能力を取得
        position_map = {
            'P': ['投手', 'ピッチャー', 'P'],
            'C': ['捕手', 'キャッチャー', 'C'],
            '1B': ['一塁手', 'ファースト', '1B'],
            '2B': ['二塁手', 'セカンド', '2B'],
            '3B': ['三塁手', 'サード', '3B'],
            'SS': ['遊撃手', 'ショート', 'SS'],
            'LF': ['左翼手', 'レフト', 'LF'],
            'CF': ['中堅手', 'センター', 'CF'],
            'RF': ['右翼手', 'ライト', 'RF'],
        }
        
        for pos, pos_names in position_map.items():
            for player in fielding_team.players:
                player_pos = getattr(player, 'position', None)
                if player_pos:
                    pos_str = player_pos.value if hasattr(player_pos, 'value') else str(player_pos)
                    if any(pn in pos_str for pn in pos_names):
                        stats = getattr(player, 'stats', None)
                        if stats:
                            self.fielder_abilities[pos] = {
                                'speed': getattr(stats, 'speed', 50),
                                'fielding': getattr(stats, 'fielding', 50),
                                'arm': getattr(stats, 'arm', 50),
                            }
                        break
    
    def _update_fielder_ai(self, dt: float):
        """守備AIの更新（守備能力に基づく）"""
        # 最も近い野手を探す（守備能力を考慮）
        min_weighted_dist = float('inf')
        nearest = None
        
        for pos, (fx, fz) in self.fielder_current_pos.items():
            if pos in ['P', 'C']:
                continue
            
            # 実際の距離
            d = math.sqrt((self.ball_position[0] - fx)**2 + (self.ball_position[2] - fz)**2)
            
            # 守備能力で重み付け（能力が高いほど距離が短く見える）
            ability = self.fielder_abilities.get(pos, {})
            speed = ability.get('speed', 50)
            fielding = ability.get('fielding', 50)
            
            # 能力係数: 高能力だと係数が低い → 到達しやすい
            ability_factor = 1.0 - (speed * 0.3 + fielding * 0.2) / 100
            weighted_dist = d * (0.5 + ability_factor * 0.5)
            
            if weighted_dist < min_weighted_dist:
                min_weighted_dist = weighted_dist
                nearest = pos
        
        self.chasing_fielder = nearest
        
        # 追跡（守備能力に基づく速度）
        if nearest:
            fx, fz = self.fielder_current_pos[nearest]
            bx, bz = self.ball_position[0], self.ball_position[2]
            
            dist_xz = math.sqrt((bx - fx)**2 + (bz - fz)**2)
            if dist_xz > 1.0:
                # 守備能力に基づく速度（speed 50 = 12m/s, speed 100 = 20m/s）
                ability = self.fielder_abilities.get(nearest, {})
                speed_stat = ability.get('speed', 50)
                base_speed = 10.0 + (speed_stat / 100) * 10.0  # 10-20 m/s
                
                # 守備能力でルート効率を調整
                fielding_stat = ability.get('fielding', 50)
                efficiency = 0.8 + (fielding_stat / 100) * 0.2  # 0.8-1.0
                
                actual_speed = base_speed * efficiency
                
                dx = (bx - fx) / dist_xz
                dz = (bz - fz) / dist_xz
                new_x = self.fielder_current_pos[nearest][0] + dx * actual_speed * dt
                new_z = self.fielder_current_pos[nearest][1] + dz * actual_speed * dt
                
                # フェンス外に出ないように制限
                # フェンス距離を計算（方向に応じた距離）
                angle_from_center = math.atan2(new_x, new_z) if new_z != 0 else 0
                angle_deg = abs(math.degrees(angle_from_center))
                
                # 角度に応じてフェンス距離を補間
                if angle_deg < 45:
                    t = angle_deg / 45
                    max_dist = self.fence_dist_center * (1 - t * 0.15)  # センターから両翼へ
                else:
                    max_dist = self.fence_dist_center * 0.85  # 両翼
                
                # 距離がフェンス-5mを超えたら制限
                dist_from_home = math.sqrt(new_x**2 + new_z**2)
                fence_limit = max_dist - 5
                
                if dist_from_home > fence_limit:
                    # フェンスの内側に制限
                    scale = fence_limit / dist_from_home
                    new_x *= scale
                    new_z *= scale
                
                # ファウルラインの外に出ないよう制限（角度±45度以内）
                if new_z > 0:  # 前方の場合のみ
                    max_angle = math.radians(44)
                    current_angle = math.atan2(abs(new_x), new_z)
                    if current_angle > max_angle:
                        # 角度を制限
                        new_x = math.copysign(new_z * math.tan(max_angle), new_x)
                
                self.fielder_current_pos[nearest][0] = new_x
                self.fielder_current_pos[nearest][1] = new_z
    
    def _update_tracking_camera(self, dt: float):
        """ボール追跡カメラの更新"""
        if not self.is_ball_flying:
            return
        
        # ボールの後ろから追う
        vel_len = math.sqrt(sum(v**2 for v in self.ball_velocity))
        if vel_len > 0.1:
            # ボールの進行方向の後ろに配置
            offset_x = -self.ball_velocity[0] / vel_len * 8
            offset_z = -self.ball_velocity[2] / vel_len * 8
            
            target_x = self.ball_position[0] + offset_x
            target_dist = self.ball_position[2] + offset_z
            target_height = max(self.ball_position[1] + 3, 5)
            
            # スムーズに追従
            lerp_speed = dt * 3
            self.camera_offset_x += (target_x - self.camera_offset_x) * lerp_speed
            self.camera_dist += (target_dist - 20 - self.camera_dist) * lerp_speed
            self.camera_height += (target_height - self.camera_height) * lerp_speed
    
    def project(self, v: Vector3) -> Optional[Tuple[int, int, float]]:
        """3D座標を2D画面座標に投影"""
        rel_x = v.x - self.camera_offset_x
        rel_y = v.y
        rel_z = v.z - self.camera_dist
        
        angle_rad = math.radians(self.camera_angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        
        rotated_y = rel_y * cos_a - rel_z * sin_a
        rotated_z = rel_y * sin_a + rel_z * cos_a
        
        rotated_y -= self.camera_height * cos_a
        rotated_z += self.camera_height * sin_a
        
        if rotated_z <= 0.1:
            return None
        
        scale = self.fov / rotated_z
        sx = int(self.vanishing_point_x + rel_x * scale)
        sy = int(self.vanishing_point_y - rotated_y * scale)
        
        return (sx, sy, scale)
    
    def draw_background(self):
        """サイバー風背景を描画"""
        self.screen.fill(self.COLOR_BG)
    
    def draw_result_display_top(self, dt: float = 0.016):
        """結果表示を画面上部に描画（NPB風演出）"""
        if not hasattr(self, 'result_display') or not self.result_display.get('text'):
            return
        
        rd = self.result_display
        rd['animation_time'] = rd.get('animation_time', 0) + dt
        
        # 表示時間チェック
        if rd['animation_time'] > rd.get('show_duration', 3.0):
            return
        
        center_x = self.width // 2
        
        # アニメーション進行度
        progress = rd['animation_time']
        
        # 登場アニメーション（0.3秒で表示）
        if progress < 0.3:
            alpha = int(255 * (progress / 0.3))
            scale = 0.8 + 0.2 * (progress / 0.3)
        # 消失アニメーション（最後0.3秒）
        elif progress > rd.get('show_duration', 3.0) - 0.3:
            remaining = rd.get('show_duration', 3.0) - progress
            alpha = int(255 * (remaining / 0.3))
            scale = 1.0
        else:
            alpha = 255
            scale = 1.0
        
        color = rd.get('color', (255, 255, 255))
        text = rd.get('text', '')
        sub_text = rd.get('sub_text', '')
        fielder_credit = rd.get('fielder_credit', '')
        
        # 背景バー（画面上部）
        bar_height = 60 if sub_text or fielder_credit else 45
        bar_y = 85  # スコアボードの下
        
        bar_surface = pygame.Surface((self.width, bar_height), pygame.SRCALPHA)
        bar_surface.fill((0, 0, 0, min(200, alpha // 2)))
        self.screen.blit(bar_surface, (0, bar_y))
        
        # グロー効果付きメインテキスト
        if text:
            # グロー
            glow_color = (color[0] // 3, color[1] // 3, color[2] // 3, alpha // 2)
            glow_surf = pygame.Surface((400, 50), pygame.SRCALPHA)
            try:
                main_text = fonts.h2.render(text, True, color)
                glow_text = fonts.h2.render(text, True, glow_color[:3])
            except:
                main_text = fonts.h3.render(text, True, color)
                glow_text = fonts.h3.render(text, True, glow_color[:3])
            
            text_x = center_x - main_text.get_width() // 2
            text_y = bar_y + 8
            
            # グロー（オフセットで描画）
            for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                self.screen.blit(glow_text, (text_x + ox, text_y + oy))
            
            # メインテキスト
            self.screen.blit(main_text, (text_x, text_y))
        
        # サブテキスト（守備者クレジットなど）
        y_offset = bar_y + 35
        if sub_text:
            sub_surf = fonts.small.render(sub_text, True, (200, 220, 240))
            self.screen.blit(sub_surf, (center_x - sub_surf.get_width() // 2, y_offset))
            y_offset += 18
        
        if fielder_credit:
            credit_surf = fonts.tiny.render(fielder_credit, True, (255, 215, 0))
            self.screen.blit(credit_surf, (center_x - credit_surf.get_width() // 2, y_offset))
        
        # 上下のアクセントライン
        accent_color = (*color, alpha)
        pygame.draw.line(self.screen, color, (0, bar_y), (self.width, bar_y), 2)
        pygame.draw.line(self.screen, (color[0]//2, color[1]//2, color[2]//2), 
                        (0, bar_y + bar_height), (self.width, bar_y + bar_height), 1)
    
    def draw_grid(self):
        """3Dグリッドを描画"""
        # Z方向の線
        for x in range(-60, 61, 15):
            p1 = self.project(Vector3(x, 0, 0))
            p2 = self.project(Vector3(x, 0, 150))
            if p1 and p2:
                pygame.draw.line(self.screen, self.COLOR_GRID_FAR, (p1[0], p1[1]), (p2[0], p2[1]), 1)
        
        # X方向の線
        for z in range(0, 151, 15):
            p1 = self.project(Vector3(-60, 0, z))
            p2 = self.project(Vector3(60, 0, z))
            if p1 and p2:
                pygame.draw.line(self.screen, self.COLOR_GRID_FAR, (p1[0], p1[1]), (p2[0], p2[1]), 1)
    
    def draw_foul_lines(self):
        """ファウルラインを描画"""
        home = self.project(Vector3(0, 0.1, 0))
        left_pole = self.project(Vector3(
            self.fence_dist_left * math.sin(math.radians(45)), 0.1,
            self.fence_dist_left * math.cos(math.radians(45))
        ))
        right_pole = self.project(Vector3(
            self.fence_dist_right * math.sin(math.radians(-45)), 0.1,
            self.fence_dist_right * math.cos(math.radians(-45))
        ))
        
        if home and left_pole:
            pygame.draw.line(self.screen, self.COLOR_FOUL_LINE, (home[0], home[1]), (left_pole[0], left_pole[1]), 2)
        if home and right_pole:
            pygame.draw.line(self.screen, self.COLOR_FOUL_LINE, (home[0], home[1]), (right_pole[0], right_pole[1]), 2)
    
    def draw_fence(self):
        """外野フェンスを描画（パークファクターに基づく距離）- NPB標準"""
        fence_points = []
        steps = 25
        
        for i in range(steps + 1):
            angle = math.radians(-45 + (90 * i / steps))
            angle_deg = -45 + (90 * i / steps)
            
            # 角度に応じてフェンス距離を補間（両翼-左中間/右中間-センター）
            abs_angle = abs(angle_deg)
            if abs_angle < 15:
                # センター方向（15度以内）
                fence_dist = self.fence_dist_center
            elif abs_angle < 30:
                # 左中間・右中間方向（15-30度）
                t = (abs_angle - 15) / 15
                if angle_deg > 0:  # 左翼側
                    fence_dist = self.fence_dist_center - t * (self.fence_dist_center - self.fence_dist_left_center)
                else:  # 右翼側
                    fence_dist = self.fence_dist_center - t * (self.fence_dist_center - self.fence_dist_right_center)
            else:
                # 両翼方向（30-45度）
                t = (abs_angle - 30) / 15
                if angle_deg > 0:  # 左翼側
                    fence_dist = self.fence_dist_left_center - t * (self.fence_dist_left_center - self.fence_dist_left)
                else:  # 右翼側
                    fence_dist = self.fence_dist_right_center - t * (self.fence_dist_right_center - self.fence_dist_right)
            
            x = fence_dist * math.sin(angle)
            z = fence_dist * math.cos(angle)
            p_btm = self.project(Vector3(x, 0, z))
            p_top = self.project(Vector3(x, self.FENCE_HEIGHT, z))
            
            if p_btm and p_top:
                fence_points.append((p_btm, p_top))
                pygame.draw.line(self.screen, (100, 0, 100), (p_btm[0], p_btm[1]), (p_top[0], p_top[1]), 1)
        
        # フェンス上端と下端を結ぶ
        if len(fence_points) > 1:
            points_top = [(p[1][0], p[1][1]) for p in fence_points]
            points_btm = [(p[0][0], p[0][1]) for p in fence_points]
            pygame.draw.lines(self.screen, self.COLOR_FENCE, False, points_top, 3)
            pygame.draw.lines(self.screen, (60, 0, 60), False, points_btm, 1)
        
        # ファウルポール
        if len(fence_points) > 0:
            # 左ポール
            top_lp = self.project(Vector3(
                self.fence_dist_left * math.sin(math.radians(45)), 25,
                self.fence_dist_left * math.cos(math.radians(45))
            ))
            if top_lp:
                pygame.draw.line(self.screen, self.COLOR_POLE, 
                               (fence_points[-1][0][0], fence_points[-1][0][1]), 
                               (top_lp[0], top_lp[1]), 3)
            
            # 右ポール
            top_rp = self.project(Vector3(
                self.fence_dist_right * math.sin(math.radians(-45)), 25,
                self.fence_dist_right * math.cos(math.radians(-45))
            ))
            if top_rp:
                pygame.draw.line(self.screen, self.COLOR_POLE,
                               (fence_points[0][0][0], fence_points[0][0][1]),
                               (top_rp[0], top_rp[1]), 3)
        
        # 距離表示
        dist_text = f"{self.fence_dist_center}m"
        dist_surf = fonts.tiny.render(dist_text, True, self.COLOR_TEXT)
        center_fence = self.project(Vector3(0, self.FENCE_HEIGHT + 2, self.fence_dist_center))
        if center_fence:
            self.screen.blit(dist_surf, (center_fence[0] - dist_surf.get_width() // 2, center_fence[1]))
    
    def draw_bases(self, runners: List[bool]):
        """ベースとランナーを描画"""
        # ベース位置（メートル単位、地面に設置）
        base_coords = [
            Vector3(0, 0.05, 0),        # ホーム
            Vector3(19, 0.05, 19),      # 1塁
            Vector3(0, 0.05, 38),       # 2塁
            Vector3(-19, 0.05, 19),     # 3塁
        ]
        
        for i, base in enumerate(base_coords):
            p = self.project(base)
            if p:
                if i == 0:
                    # ホームベース（五角形）
                    size = max(2, int(2 * p[2]))
                    pts = [
                        (p[0], p[1] - size),
                        (p[0] + size, p[1]),
                        (p[0] + size//2, p[1] + size),
                        (p[0] - size//2, p[1] + size),
                        (p[0] - size, p[1])
                    ]
                    pygame.draw.polygon(self.screen, self.COLOR_BASE, pts, 2)
                else:
                    # 塁ベース（小さく）
                    size = max(2, int(2 * p[2]))
                    if runners[i - 1]:
                        # ランナーあり（小さく）
                        pygame.draw.rect(self.screen, self.COLOR_RUNNER,
                                       (p[0] - size, p[1] - size, size * 2, size * 2))
                        # ランナーマーカー（小さく）
                        pygame.draw.circle(self.screen, (255, 220, 100), (p[0], p[1] - size), max(2, int(size * 0.7)))
                    else:
                        pygame.draw.rect(self.screen, self.COLOR_BASE,
                                       (p[0] - size, p[1] - size, size * 2, size * 2), 2)
        
        # ベースライン
        line_color = (0, 150, 150)
        for i in range(4):
            p1 = self.project(base_coords[i])
            p2 = self.project(base_coords[(i + 1) % 4])
            if p1 and p2:
                pygame.draw.line(self.screen, line_color, (p1[0], p1[1]), (p2[0], p2[1]), 2)
        
        # ピッチャーマウンド（地面に設置）
        mound = self.project(Vector3(0, 0.05, 18.44))
        if mound:
            pygame.draw.circle(self.screen, (80, 60, 50), (mound[0], mound[1]), max(2, int(2 * mound[2])))
            pygame.draw.circle(self.screen, self.COLOR_TEXT, (mound[0], mound[1]), max(2, int(2 * mound[2])), 1)
    
    def draw_runners_ai(self):
        """AIで動く走者を描画"""
        runner_positions = self.get_runner_draw_positions()
        
        for base, (rx, rz) in runner_positions.items():
            # 走者の3D座標
            v = Vector3(rx, 0.5, rz)  # 高さ0.5m（地面上）
            p = self.project(v)
            
            if p:
                # 走者の大きさ（遠近に応じて）
                size = max(4, min(10, int(4 * p[2])))
                
                # 打者走者は別色
                if base == 'batter':
                    color = (255, 255, 100)  # 黄色
                    outline = (255, 200, 0)
                else:
                    color = self.COLOR_RUNNER
                    outline = (255, 220, 100)
                
                # 走者本体（楕円風）
                pygame.draw.circle(self.screen, color, (p[0], p[1]), size)
                pygame.draw.circle(self.screen, outline, (p[0], p[1]), size, 2)
                
                # 走者の状態に応じたエフェクト
                state = self.runner_states.get(base, '')
                if state == 'running':
                    # 走塁中 - 動きのエフェクト
                    pygame.draw.circle(self.screen, (255, 255, 200), (p[0] - 2, p[1]), size // 2)
                elif state == 'tagging':
                    # タッチアップ待機中 - T表示
                    tag_label = fonts.tiny.render("T", True, (255, 100, 100))
                    self.screen.blit(tag_label, (p[0] - 3, p[1] - size - 8))
    
    def draw_fielders(self):
        """守備位置を描画"""
        positions = {
            'P': Vector3(0, 0.1, 18.44),
            'C': Vector3(0, 0.1, -1),
            '1B': Vector3(15, 0.1, 20),
            '2B': Vector3(8, 0.1, 28),
            'SS': Vector3(-8, 0.1, 28),
            '3B': Vector3(-15, 0.1, 20),
            'LF': Vector3(-28, 0.1, 60),
            'CF': Vector3(0, 0.1, 70),
            'RF': Vector3(28, 0.1, 60),
        }
        
        for pos, coord in positions.items():
            p = self.project(coord)
            if p:
                # 守備者マーカー（小さめに調整）
                size = max(3, min(6, int(2.5 * p[2])))
                color = (255, 100, 100) if pos == 'P' else self.COLOR_FIELDER
                pygame.draw.circle(self.screen, color, (p[0], p[1]), size)
                pygame.draw.circle(self.screen, (255, 255, 255), (p[0], p[1]), size, 1)
                
                # ポジションラベル（スケールに応じて表示）
                if p[2] > 1.5:
                    label = fonts.tiny.render(pos, True, (200, 200, 200))
                    self.screen.blit(label, (p[0] - label.get_width() // 2, p[1] + size + 1))
    
    def draw_ball_trajectory(self, trajectory: List[dict], ball_pos: Optional[Vector3] = None):
        """打球の軌跡とボールを描画"""
        if not trajectory or len(trajectory) == 0:
            return
        
        # 軌跡を描画
        trail_points = []
        last_point_data = None
        
        for i, point in enumerate(trajectory):
            if isinstance(point, dict):
                # dict形式: x=横方向, y=奥行き（フィールド上の距離）, z=高さ
                px = point.get('x', 0)
                py = point.get('y', 0)  # 奥行き方向
                pz = point.get('z', 0)  # 高さ
                p = self.project(Vector3(px, pz, py))
                last_point_data = (px, pz, py)
            else:
                # タプル形式: (x, y, z) = (横, 奥行き, 高さ)
                p = self.project(Vector3(point[0], point[2], point[1]))
                last_point_data = (point[0], point[2], point[1])
            
            if p and 0 <= p[0] <= self.width and 0 <= p[1] <= self.height:
                trail_points.append((p[0], p[1]))
        
        # 軌跡線を描画
        if len(trail_points) > 1:
            # グロー効果（シアンの軌跡）
            for offset in [4, 2]:
                alpha_base = 100 if offset == 4 else 200
                for i in range(len(trail_points) - 1):
                    progress = i / max(1, len(trail_points) - 1)
                    alpha = int(alpha_base * (0.3 + 0.7 * progress))
                    color = (0, alpha, alpha)
                    pygame.draw.line(self.screen, color, trail_points[i], trail_points[i + 1], offset)
            
            # メインライン（明るいシアン）
            pygame.draw.lines(self.screen, self.COLOR_TRAIL, False, trail_points, 2)
        
        # ボール位置（軌跡の最後の点）
        if trail_points:
            ball_screen_pos = trail_points[-1]
            # グロー
            pygame.draw.circle(self.screen, (0, 200, 200), ball_screen_pos, 8)
            pygame.draw.circle(self.screen, self.COLOR_BALL_GLOW, ball_screen_pos, 5)
            # ボール本体
            pygame.draw.circle(self.screen, self.COLOR_BALL, ball_screen_pos, 3)
        elif last_point_data:
            # 軌跡が1点だけの場合もボールを表示
            p = self.project(Vector3(last_point_data[0], last_point_data[1], last_point_data[2]))
            if p:
                pygame.draw.circle(self.screen, (0, 200, 200), (p[0], p[1]), 8)
                pygame.draw.circle(self.screen, self.COLOR_BALL_GLOW, (p[0], p[1]), 5)
                pygame.draw.circle(self.screen, self.COLOR_BALL, (p[0], p[1]), 3)
    
    def draw_tracking_data_panel(self, ball_data: dict, x: int, y: int):
        """トラッキングデータパネルを描画"""
        if not ball_data:
            return
        
        panel_w = 180
        panel_h = 120
        
        # パネル背景
        panel_surface = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surface.fill((0, 20, 40, 220))
        self.screen.blit(panel_surface, (x, y))
        pygame.draw.rect(self.screen, self.COLOR_TEXT, (x, y, panel_w, panel_h), 2, border_radius=5)
        
        # タイトル
        title = fonts.small.render("TRACKING DATA", True, self.COLOR_TEXT)
        self.screen.blit(title, (x + 10, y + 5))
        
        # データ
        exit_velo = ball_data.get('exit_velocity', 0)
        launch_angle = ball_data.get('launch_angle', 0)
        direction = ball_data.get('direction', 0)
        distance = ball_data.get('distance', 0)
        
        data_lines = [
            f"EXIT VELO : {exit_velo:.1f} km/h",
            f"LAUNCH ANG: {launch_angle:.1f} deg",
            f"DIRECTION : {direction:.1f} deg",
            f"DISTANCE  : {distance:.1f} m"
        ]
        
        for i, line in enumerate(data_lines):
            text = fonts.tiny.render(line, True, (200, 220, 240))
            self.screen.blit(text, (x + 10, y + 30 + i * 22))
    
    def draw_strike_zone_panel(self, pitch_history: list, x: int, y: int, last_pitch_data: dict = None):
        """ストライクゾーントラッキングパネルを描画（投球データ表示付き）"""
        panel_w = 130
        panel_h = 200
        
        # パネル背景
        panel_surface = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surface.fill((0, 20, 40, 220))
        self.screen.blit(panel_surface, (x, y))
        pygame.draw.rect(self.screen, self.COLOR_TEXT, (x, y, panel_w, panel_h), 2, border_radius=5)
        
        # タイトル
        title = fonts.tiny.render("PITCH TRACKING", True, self.COLOR_TEXT)
        self.screen.blit(title, (x + 8, y + 5))
        
        # 最新の投球データ表示
        if last_pitch_data:
            pitch_type = last_pitch_data.get('pitch_type', 'ストレート')
            speed = last_pitch_data.get('speed', 140)
            spin = last_pitch_data.get('spin', 2200)
            
            type_surf = fonts.small.render(pitch_type, True, (255, 200, 100))
            self.screen.blit(type_surf, (x + 8, y + 22))
            
            speed_text = f"{speed:.0f} km/h"
            speed_surf = fonts.tiny.render(speed_text, True, (200, 220, 240))
            self.screen.blit(speed_surf, (x + 8, y + 42))
            
            spin_text = f"{spin:.0f} rpm"
            spin_surf = fonts.tiny.render(spin_text, True, (180, 200, 220))
            self.screen.blit(spin_surf, (x + 70, y + 42))
        else:
            # 投球履歴から最新を取得
            if pitch_history:
                last_pitch = pitch_history[-1]
                pitch_type = last_pitch.get('type', 'ストレート')
                type_surf = fonts.small.render(pitch_type, True, (255, 200, 100))
                self.screen.blit(type_surf, (x + 8, y + 22))
        
        # ストライクゾーン描画エリア
        zone_x = x + 25
        zone_y = y + 62
        zone_w = 80
        zone_h = 100
        
        # ゾーン背景
        pygame.draw.rect(self.screen, (20, 40, 60), (zone_x, zone_y, zone_w, zone_h))
        
        # 9分割グリッド
        cell_w = zone_w // 3
        cell_h = zone_h // 3
        for i in range(1, 3):
            pygame.draw.line(self.screen, (60, 80, 100), 
                           (zone_x + i * cell_w, zone_y), 
                           (zone_x + i * cell_w, zone_y + zone_h), 1)
            pygame.draw.line(self.screen, (60, 80, 100),
                           (zone_x, zone_y + i * cell_h),
                           (zone_x + zone_w, zone_y + i * cell_h), 1)
        
        # ゾーン枠
        pygame.draw.rect(self.screen, self.COLOR_TEXT, (zone_x, zone_y, zone_w, zone_h), 2)
        
        # 投球履歴をプロット（固定位置を使用）
        if pitch_history:
            for i, pitch in enumerate(pitch_history[-10:]):  # 最新10球
                result = pitch.get('result', '')
                is_swing = pitch.get('swing', False)  # 空振りフラグ
                
                # 保存された位置データを使用（ランダムではなく固定）
                px_offset = pitch.get('location_x', 0.0)
                py_offset = pitch.get('location_y', 0.0)
                
                # 位置に基づくストライク/ボール判定（-0.45〜0.45がストライクゾーン）
                is_in_zone = abs(px_offset) <= 0.45 and 0.15 <= py_offset <= 0.85
                
                # 結果と位置によって色を設定
                if result in ['ボール', '四球']:
                    color = (100, 180, 100)  # 緑（ボール）
                elif result == '空振り三振' or (result == 'ストライク' and is_swing):
                    color = (255, 150, 50)  # オレンジ（空振り）
                elif result in ['見逃し', 'ストライク']:
                    color = (255, 100, 100)  # 赤（見逃しストライク）
                elif result == 'ファウル':
                    color = (200, 200, 100)  # 黄（ファウル）
                else:
                    color = (100, 150, 255)  # 青（打球）
                
                # 位置計算
                px = zone_x + zone_w / 2 + px_offset * zone_w
                py = zone_y + zone_h / 2 + py_offset * zone_h
                
                # 範囲制限
                px = max(zone_x - 15, min(zone_x + zone_w + 15, px))
                py = max(zone_y - 10, min(zone_y + zone_h + 10, py))
                
                # プロット
                size = 4 if i == len(pitch_history[-10:]) - 1 else 2
                pygame.draw.circle(self.screen, color, (int(px), int(py)), size)
                if i == len(pitch_history[-10:]) - 1:
                    # 最新の投球は枠をつける
                    pygame.draw.circle(self.screen, (255, 255, 255), (int(px), int(py)), size + 2, 1)
    
    def draw_minimap(self, x: int = 10, y: int = 10, size: int = 120):
        """フィールドのミニマップを描画"""
        # ミニマップの背景
        map_surface = pygame.Surface((size, size), pygame.SRCALPHA)
        map_surface.fill((10, 20, 30, 200))
        
        center_x = size // 2
        center_y = size - 10  # ホームベースは下部
        scale = size / 280  # フルフィールドを収める
        
        # フィールド範囲（扇形）
        points = [(center_x, center_y)]
        for i in range(21):
            angle = math.radians(-45 + i * 4.5)
            r = int(self.fence_dist_center * scale)
            px = center_x + int(r * math.sin(angle))
            py = center_y - int(r * math.cos(angle))
            points.append((px, py))
        if len(points) > 2:
            pygame.draw.polygon(map_surface, (30, 60, 30), points)
        
        # 内野
        infield_r = int(40 * scale)
        pygame.draw.arc(map_surface, (50, 80, 50), 
                       (center_x - infield_r, center_y - infield_r, 
                        infield_r * 2, infield_r * 2),
                       math.radians(225), math.radians(315), 2)
        
        # ベースを描画
        base_positions = [
            (0, 0),       # ホーム
            (19, 19),     # 1塁
            (0, 38),      # 2塁
            (-19, 19),    # 3塁
        ]
        for bx, bz in base_positions:
            mx = center_x + int(bx * scale)
            my = center_y - int(bz * scale)
            pygame.draw.rect(map_surface, (255, 255, 255), (mx - 2, my - 2, 4, 4))
        
        # 野手の位置
        for pos, (fx, fz) in self.fielder_current_pos.items():
            mx = center_x + int(fx * scale)
            my = center_y - int(fz * scale)
            color = (0, 200, 255) if pos == self.chasing_fielder else (100, 150, 255)
            pygame.draw.circle(map_surface, color, (mx, my), 3)
        
        # ボールの位置
        if self.ball_position:
            bx = self.ball_position[0]
            bz = self.ball_position[2]
            mx = center_x + int(bx * scale)
            my = center_y - int(bz * scale)
            # ミニマップ範囲内のみ描画
            if 0 <= mx < size and 0 <= my < size:
                pygame.draw.circle(map_surface, (255, 255, 0), (mx, my), 4)
                # ボールの影（地面位置）
                pygame.draw.circle(map_surface, (100, 100, 100), (mx, my), 2)
        
        # 軌跡
        if len(self.ball_trail) > 1:
            trail_pts = []
            for bx, by, bz in self.ball_trail[-30:]:
                mx = center_x + int(bx * scale)
                my = center_y - int(bz * scale)
                if 0 <= mx < size and 0 <= my < size:
                    trail_pts.append((mx, my))
            if len(trail_pts) > 1:
                pygame.draw.lines(map_surface, (0, 255, 255), False, trail_pts, 1)
        
        # 枠
        pygame.draw.rect(map_surface, (0, 200, 200), (0, 0, size, size), 2)
        
        # メイン画面に描画
        self.screen.blit(map_surface, (x, y))
        
        # ラベル
        label = fonts.tiny.render("MINI MAP", True, (0, 200, 200))
        self.screen.blit(label, (x + 5, y + size + 2))
    
    def draw_dynamic_fielders(self):
        """動的な野手位置を描画（追跡時）"""
        for pos, (fx, fz) in self.fielder_current_pos.items():
            # 野手の3D座標（地面に設置）
            coord = Vector3(fx, 0.1, fz)
            p = self.project(coord)
            if p:
                # 追跡中の野手は強調
                if pos == self.chasing_fielder:
                    # グロー効果
                    pygame.draw.circle(self.screen, (0, 100, 200), (p[0], p[1]), 12)
                    pygame.draw.circle(self.screen, (0, 200, 255), (p[0], p[1]), 8)
                    pygame.draw.circle(self.screen, (200, 255, 255), (p[0], p[1]), 5)
                    
                    # 野手名
                    label = fonts.small.render(pos, True, (255, 255, 100))
                    self.screen.blit(label, (p[0] - label.get_width() // 2, p[1] + 12))
                else:
                    # 通常の野手
                    size = max(3, min(6, int(2.5 * p[2])))
                    color = (255, 100, 100) if pos == 'P' else self.COLOR_FIELDER
                    pygame.draw.circle(self.screen, color, (p[0], p[1]), size)
                    pygame.draw.circle(self.screen, (255, 255, 255), (p[0], p[1]), size, 1)
                    
                    if p[2] > 1.5:
                        label = fonts.tiny.render(pos, True, (200, 200, 200))
                        self.screen.blit(label, (p[0] - label.get_width() // 2, p[1] + size + 1))
    
    def draw_ball_with_shadow(self, ball_pos: List[float] = None):
        """ボールと影を描画（送球中も対応）"""
        # 送球中のボール位置を優先
        throw_ball_pos = self.get_throw_ball_position()
        pos = throw_ball_pos if throw_ball_pos else (ball_pos if ball_pos else self.ball_position)
        if not pos or len(pos) < 3:
            return
        
        # 送球中かどうか判定
        is_throwing = throw_ball_pos is not None
        
        # 影（地面に投影）
        shadow_coord = Vector3(pos[0], 0.1, pos[2])
        shadow_p = self.project(shadow_coord)
        if shadow_p:
            shadow_size = max(2, min(8, int(4 / (1 + pos[1] * 0.1))))
            shadow_surf = pygame.Surface((shadow_size * 4, shadow_size * 2), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, 100), 
                              (0, 0, shadow_size * 4, shadow_size * 2))
            self.screen.blit(shadow_surf, 
                           (shadow_p[0] - shadow_size * 2, shadow_p[1] - shadow_size))
        
        # ボール本体
        ball_coord = Vector3(pos[0], pos[1], pos[2])
        ball_p = self.project(ball_coord)
        if ball_p:
            if is_throwing:
                # 送球中は別色（オレンジ系）
                pygame.draw.circle(self.screen, (200, 100, 0), (ball_p[0], ball_p[1]), 6)
                pygame.draw.circle(self.screen, (255, 180, 100), (ball_p[0], ball_p[1]), 4)
                pygame.draw.circle(self.screen, (255, 255, 200), (ball_p[0], ball_p[1]), 2)
            else:
                # グロー効果
                pygame.draw.circle(self.screen, (0, 150, 150), (ball_p[0], ball_p[1]), 6)
                pygame.draw.circle(self.screen, self.COLOR_BALL_GLOW, (ball_p[0], ball_p[1]), 4)
                # ボール
                pygame.draw.circle(self.screen, self.COLOR_BALL, (ball_p[0], ball_p[1]), 2)
            
            # 高度表示
            if pos[1] > 2:
                height_text = f"{pos[1]:.1f}m"
                text_surf = fonts.tiny.render(height_text, True, (200, 200, 200))
                self.screen.blit(text_surf, (ball_p[0] + 8, ball_p[1] - 6))


class ScreenRenderer:
    """すべての画面を描画するレンダラー"""
    
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        fonts.init()  # フォント初期化
        self.title_animation_time = 0
        self.baseball_particles = []
        self.cyber_field = CyberField3D(screen)  # 3Dフィールドレンダラー
    
    def get_team_color(self, team_name: str) -> tuple:
        """チームカラーを取得"""
        colors = TEAM_COLORS.get(team_name, (Colors.PRIMARY, Colors.TEXT_PRIMARY))
        if isinstance(colors, tuple) and len(colors) == 2 and isinstance(colors[0], tuple):
            return colors[0]  # プライマリカラーを返す
        return colors if isinstance(colors, tuple) else Colors.PRIMARY
    
    def _to_rank(self, value: int) -> str:
        """能力値をパワプロ風ランクに変換（1-99スケール → S/A/B/C/D/E/F/G）"""
        if value >= 90:
            return "S"
        elif value >= 80:
            return "A"
        elif value >= 70:
            return "B"
        elif value >= 60:
            return "C"
        elif value >= 50:
            return "D"
        elif value >= 40:
            return "E"
        elif value >= 30:
            return "F"
        else:
            return "G"
    
    def get_team_abbr(self, team_name: str) -> str:
        """チーム略称を取得"""
        return TEAM_ABBREVIATIONS.get(team_name, team_name[:4])
    
    def get_stadium_name(self, team_name: str) -> str:
        """本拠地球場名を取得"""
        stadium = NPB_STADIUMS.get(team_name, {})
        return stadium.get("name", "球場")
    
    def _draw_gradient_background(self, team_color=None, style="default"):
        """共通のグラデーション背景を描画"""
        width = self.screen.get_width()
        height = self.screen.get_height()
        
        # 基本グラデーション
        for y in range(height):
            ratio = y / height
            if style == "dark":
                r = int(15 + 12 * ratio)
                g = int(17 + 13 * ratio)
                b = int(22 + 16 * ratio)
            else:
                r = int(18 + 10 * ratio)
                g = int(20 + 12 * ratio)
                b = int(28 + 14 * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (width, y))
        
        # チームカラーがある場合、装飾を追加
        if team_color:
            # 斜めのアクセントライン
            for i in range(3):
                start_x = width - 350 + i * 100
                line_alpha = 15 - i * 3
                line_color = (team_color[0] // 5, team_color[1] // 5, team_color[2] // 5)
                pygame.draw.line(self.screen, line_color, (start_x, 0), (start_x - 200, height), 2)
            
            # 上部アクセントライン
            pygame.draw.rect(self.screen, team_color, (0, 0, width, 3))
    
    # ========================================
    # タイトル画面
    # ========================================
    def draw_title_screen(self, show_start_menu: bool = False) -> Dict[str, Button]:
        """タイトル画面を描画（シンプル＆スタイリッシュ版）"""
        # シンプルな暗いグラデーション背景
        self._draw_gradient_background(style="dark")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        center_x = width // 2
        
        self.title_animation_time += 0.02
        
        # 中央に縦のアクセントライン（チームカラーのグラデーション）
        line_surf = pygame.Surface((4, height), pygame.SRCALPHA)
        for y in range(height):
            alpha = int(80 * (1 - abs(y - height/2) / (height/2)))
            line_surf.set_at((0, y), (*Colors.PRIMARY[:3], alpha))
            line_surf.set_at((1, y), (*Colors.PRIMARY[:3], alpha))
            line_surf.set_at((2, y), (*Colors.PRIMARY[:3], alpha))
            line_surf.set_at((3, y), (*Colors.PRIMARY[:3], alpha))
        self.screen.blit(line_surf, (center_x - 2, 0))
        
        # ロゴエリア
        logo_y = height // 3
        
        # メインタイトル（シンプルに）
        title_text = "PENNANT"
        title = fonts.title.render(title_text, True, Colors.TEXT_PRIMARY)
        title_rect = title.get_rect(center=(center_x, logo_y - 30))
        self.screen.blit(title, title_rect)
        
        # サブタイトル
        subtitle_text = "SIMULATOR"
        subtitle = fonts.h2.render(subtitle_text, True, Colors.TEXT_SECONDARY)
        subtitle_rect = subtitle.get_rect(center=(center_x, logo_y + 30))
        self.screen.blit(subtitle, subtitle_rect)
        
        # 年度表示
        year_text = "2025"
        year_surf = fonts.tiny.render(year_text, True, Colors.PRIMARY)
        year_rect = year_surf.get_rect(center=(center_x, logo_y + 70))
        self.screen.blit(year_surf, year_rect)
        
        # ボタンエリア（シンプルに）
        btn_width = 250
        btn_height = 55
        btn_x = center_x - btn_width // 2
        btn_y = height // 2 + 50
        btn_spacing = 70
        
        buttons = {}
        
        if show_start_menu:
            # スタートメニュー表示中（ニューゲーム/ロード選択）
            # 半透明のオーバーレイ
            overlay = pygame.Surface((width, height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))
            
            # メニューボックス
            menu_w, menu_h = 320, 280
            menu_rect = pygame.Rect(center_x - menu_w // 2, height // 2 - menu_h // 2, menu_w, menu_h)
            draw_rounded_rect(self.screen, menu_rect, Colors.BG_CARD, 16)
            
            # タイトル
            menu_title = fonts.h2.render("GAME START", True, Colors.TEXT_PRIMARY)
            menu_title_rect = menu_title.get_rect(centerx=center_x, top=menu_rect.y + 25)
            self.screen.blit(menu_title, menu_title_rect)
            
            # ボタン
            menu_btn_y = menu_rect.y + 80
            menu_btn_spacing = 60
            
            buttons["new_game"] = Button(
                center_x - btn_width // 2, menu_btn_y, btn_width, btn_height,
                "NEW GAME", "primary", font=fonts.h3
            )
            
            buttons["load_game"] = Button(
                center_x - btn_width // 2, menu_btn_y + menu_btn_spacing, btn_width, btn_height,
                "LOAD GAME", "outline", font=fonts.body
            )
            
            buttons["back_to_title"] = Button(
                center_x - btn_width // 2, menu_btn_y + menu_btn_spacing * 2, btn_width, btn_height,
                "BACK", "ghost", font=fonts.body
            )
            
            for btn in buttons.values():
                btn.draw(self.screen)
        else:
            # 通常のタイトル画面
            # スタートボタン（プライマリ）
            buttons["start"] = Button(
                btn_x, btn_y, btn_width, btn_height,
                "START", "primary", font=fonts.h3
            )
            
            # 設定ボタン（ゴースト）
            buttons["settings"] = Button(
                btn_x, btn_y + btn_spacing, btn_width, btn_height,
                "SETTINGS", "ghost", font=fonts.body
            )
            
            # 終了ボタン（アウトライン）
            buttons["quit"] = Button(
                btn_x, btn_y + btn_spacing * 2, btn_width, btn_height,
                "QUIT", "outline", font=fonts.body
            )
            
            for btn in buttons.values():
                btn.draw(self.screen)
            
            # フッター
            footer = fonts.tiny.render("Press START to begin your journey", True, Colors.TEXT_MUTED)
            footer_rect = footer.get_rect(center=(center_x, height - 40))
            
            # 点滅エフェクト
            alpha = int(128 + 127 * math.sin(self.title_animation_time * 3))
            footer.set_alpha(alpha)
            self.screen.blit(footer, footer_rect)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    def draw_new_game_setup_screen(self, settings_obj, setup_state: dict = None) -> Dict[str, Button]:
        """新規ゲーム開始設定画面を描画（詳細設定統合版）
        
        Args:
            settings_obj: 設定オブジェクト（game_rulesを含む）
            setup_state: 設定状態を保持する辞書
        """
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        center_x = width // 2
        
        # デフォルト状態
        if setup_state is None:
            setup_state = {}
        
        # ヘッダー
        header_h = draw_header(self.screen, "NEW GAME")
        
        # サブヘッダー
        subtitle = fonts.body.render("ゲーム設定を確認してスタート", True, Colors.TEXT_SECONDARY)
        self.screen.blit(subtitle, (center_x - subtitle.get_width() // 2, header_h + 10))
        
        buttons = {}
        rules = settings_obj.game_rules
        
        # カードエリア開始位置
        card_top = header_h + 50
        card_spacing = 15
        available_width = width - 60  # 左右30pxマージン
        
        # 2列レイアウト
        card_width = min(450, (available_width - card_spacing) // 2)
        card_height = 280
        col1_x = center_x - card_width - card_spacing // 2
        col2_x = center_x + card_spacing // 2
        
        # === 左カード: 試合設定 ===
        left_card = Card(col1_x, card_top, card_width, card_height, "試合設定")
        left_rect = left_card.draw(self.screen)
        
        y = left_rect.y + 50
        
        # シーズン試合数
        label_surf = fonts.small.render("シーズン試合数", True, Colors.TEXT_PRIMARY)
        self.screen.blit(label_surf, (left_rect.x + 20, y))
        y += 28
        
        game_options = [120, 130, 143]
        btn_x = left_rect.x + 20
        btn_w = 90
        for games in game_options:
            is_selected = rules.regular_season_games == games
            style = "primary" if is_selected else "outline"
            btn = Button(btn_x, y, btn_w, 32, f"{games}試合", style, font=fonts.small)
            btn.draw(self.screen)
            buttons[f"setup_games_{games}"] = btn
            btn_x += btn_w + 10
        
        y += 50
        
        # 延長戦設定
        label_surf = fonts.small.render("延長上限", True, Colors.TEXT_PRIMARY)
        self.screen.blit(label_surf, (left_rect.x + 20, y))
        y += 28
        
        ext_options = [9, 12, 0]
        btn_x = left_rect.x + 20
        for ext in ext_options:
            display = "無制限" if ext == 0 else f"{ext}回"
            is_selected = rules.extra_innings_limit == ext
            style = "primary" if is_selected else "outline"
            btn = Button(btn_x, y, btn_w, 32, display, style, font=fonts.small)
            btn.draw(self.screen)
            buttons[f"setup_innings_{ext}"] = btn
            btn_x += btn_w + 10
        
        y += 50
        
        # DH制（常にオン）
        dh_label = fonts.small.render("DH制", True, Colors.TEXT_PRIMARY)
        self.screen.blit(dh_label, (left_rect.x + 20, y + 8))
        dh_status = fonts.small.render("常時ON", True, Colors.SUCCESS)
        self.screen.blit(dh_status, (left_rect.x + 200, y + 8))
        
        # === 右カード: シーズン設定 ===
        right_card = Card(col2_x, card_top, card_width, card_height, "シーズン設定")
        right_rect = right_card.draw(self.screen)
        
        y = right_rect.y + 50
        
        # シーズンイベント切り替え
        event_settings = [
            ("春季キャンプ", "enable_spring_camp", rules.enable_spring_camp),
            ("交流戦", "enable_interleague", rules.enable_interleague),
            ("オールスター", "enable_allstar", rules.enable_allstar),
            ("クライマックスシリーズ", "enable_climax_series", rules.enable_climax_series),
            ("タイブレーク制度", "enable_tiebreaker", rules.enable_tiebreaker),
        ]
        
        for label, key, value in event_settings:
            label_surf = fonts.small.render(label, True, Colors.TEXT_PRIMARY)
            self.screen.blit(label_surf, (right_rect.x + 20, y + 6))
            
            status = "ON" if value else "OFF"
            style = "success" if value else "ghost"
            btn = Button(right_rect.x + card_width - 100, y, 70, 30, status, style, font=fonts.small)
            btn.draw(self.screen)
            buttons[f"setup_toggle_{key}"] = btn
            y += 40
        
        # === 下部カード: 外国人枠設定 ===
        bottom_y = card_top + card_height + card_spacing
        bottom_card = Card(col1_x, bottom_y, card_width * 2 + card_spacing, 100, "外国人枠設定")
        bottom_rect = bottom_card.draw(self.screen)
        
        y = bottom_rect.y + 50
        
        # 外国人枠無制限
        label_surf = fonts.small.render("外国人枠無制限", True, Colors.TEXT_PRIMARY)
        self.screen.blit(label_surf, (bottom_rect.x + 20, y + 6))
        status = "ON" if rules.unlimited_foreign else "OFF"
        style = "success" if rules.unlimited_foreign else "ghost"
        btn = Button(bottom_rect.x + 180, y, 70, 30, status, style, font=fonts.small)
        btn.draw(self.screen)
        buttons["setup_toggle_unlimited_foreign"] = btn
        
        # 外国人支配下枠
        label_surf = fonts.small.render("支配下枠", True, Colors.TEXT_PRIMARY)
        self.screen.blit(label_surf, (bottom_rect.x + 300, y + 6))
        
        btn_x = bottom_rect.x + 400
        for opt in [3, 4, 5]:
            is_selected = rules.foreign_player_limit == opt
            style = "primary" if is_selected else "outline"
            btn = Button(btn_x, y, 50, 30, str(opt), style, font=fonts.small)
            btn.draw(self.screen)
            buttons[f"setup_foreign_limit_{opt}"] = btn
            btn_x += 60
        
        # === フッター: ボタンエリア ===
        footer_y = height - 80
        
        # 戻るボタン
        buttons["back_title"] = Button(
            30, footer_y, 140, 50,
            "← 戻る", "ghost", font=fonts.body
        )
        buttons["back_title"].draw(self.screen)
        
        # ゲームスタートボタン
        buttons["confirm_start"] = Button(
            width - 200, footer_y, 170, 50,
            "ゲーム開始", "primary", font=fonts.h3
        )
        buttons["confirm_start"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    def _draw_baseball(self, x: int, y: int, radius: int):
        """野球ボールを描画"""
        # 白い円
        pygame.draw.circle(self.screen, (255, 255, 255), (x, y), radius)
        pygame.draw.circle(self.screen, (200, 200, 200), (x, y), radius, 2)
        
        # 縫い目（簡略版）
        seam_color = (200, 50, 50)
        # 左側の縫い目
        pygame.draw.arc(self.screen, seam_color, 
                       (x - radius - 5, y - radius//2, radius, radius), 
                       -0.5, 0.5, 2)
        # 右側の縫い目
        pygame.draw.arc(self.screen, seam_color,
                       (x + 5, y - radius//2, radius, radius),
                       2.6, 3.6, 2)
    
    def _draw_title_decorations(self, width: int, height: int):
        """タイトル画面の装飾を描画"""
        # チームカラーの斜めストライプ（非常に薄く）
        team_colors = [
            (255, 102, 0),   # 巨人
            (255, 215, 0),   # 阪神
            (0, 90, 180),    # DeNA
            (200, 0, 0),     # 広島
            (0, 60, 125),    # ヤクルト
            (0, 80, 165),    # 中日
        ]
        
        stripe_width = 150
        for i, color in enumerate(team_colors):
            x = (i * stripe_width + int(self.title_animation_time * 20)) % (width + stripe_width * 2) - stripe_width
            stripe_surf = pygame.Surface((stripe_width, height), pygame.SRCALPHA)
            pygame.draw.polygon(stripe_surf, (*color, 8), [
                (0, 0), (stripe_width, 0), 
                (stripe_width - 50, height), (-50, height)
            ])
            self.screen.blit(stripe_surf, (x, 0))
    
    def _draw_team_ticker(self, height: int):
        """画面下部にチーム名をスクロール表示"""
        all_teams = NPB_CENTRAL_TEAMS + NPB_PACIFIC_TEAMS
        
        ticker_y = height - 80
        ticker_text = "  |  ".join(all_teams)
        ticker_text = ticker_text + "  |  " + ticker_text  # 繰り返し
        
        # スクロールオフセット
        offset = int(self.title_animation_time * 50) % (len(all_teams) * 200)
        
        ticker_surf = fonts.small.render(ticker_text, True, Colors.TEXT_MUTED)
        self.screen.blit(ticker_surf, (-offset, ticker_y))

    # ========================================
    # 難易度選択画面
    # ========================================
    def draw_difficulty_screen(self, current_difficulty: DifficultyLevel) -> Dict[str, Button]:
        """難易度選択画面を描画"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        center_x = width // 2
        
        # ヘッダー
        header_h = draw_header(self.screen, "難易度選択", "ゲームの難しさを選択してください")
        
        # 難易度カード
        difficulties = [
            (DifficultyLevel.EASY, "イージー", "初心者向け", Colors.SUCCESS, "選手能力UP、相手弱体化"),
            (DifficultyLevel.NORMAL, "ノーマル", "標準的な難易度", Colors.PRIMARY, "バランスの取れた設定"),
            (DifficultyLevel.HARD, "ハード", "上級者向け", Colors.WARNING, "相手の能力強化"),
            (DifficultyLevel.VERY_HARD, "ベリーハード", "最高難度", Colors.DANGER, "極限の挑戦"),
        ]
        
        card_width = 220
        card_height = 200
        total_width = card_width * 4 + 30 * 3
        start_x = (width - total_width) // 2
        card_y = header_h + 60
        
        buttons = {}
        
        for i, (level, name, desc, color, detail) in enumerate(difficulties):
            x = start_x + i * (card_width + 30)
            
            # 選択中かどうか
            is_selected = current_difficulty == level
            
            # カード背景
            card_rect = pygame.Rect(x, card_y, card_width, card_height)
            
            if is_selected:
                draw_shadow(self.screen, card_rect, 4, 10, 50)
                bg_color = lerp_color(Colors.BG_CARD, color, 0.15)
                draw_rounded_rect(self.screen, card_rect, bg_color, 16)
                pygame.draw.rect(self.screen, color, card_rect, 3, border_radius=16)
            else:
                draw_shadow(self.screen, card_rect, 2, 6, 25)
                draw_rounded_rect(self.screen, card_rect, Colors.BG_CARD, 16)
                draw_rounded_rect(self.screen, card_rect, Colors.BG_CARD, 16, 1, Colors.BORDER)
            
            # アイコン（色付き円）
            pygame.draw.circle(self.screen, color, (x + card_width // 2, card_y + 45), 25)
            icon_text = fonts.h2.render(str(i + 1), True, Colors.TEXT_PRIMARY)
            icon_rect = icon_text.get_rect(center=(x + card_width // 2, card_y + 45))
            self.screen.blit(icon_text, icon_rect)
            
            # 難易度名
            name_surf = fonts.h3.render(name, True, Colors.TEXT_PRIMARY)
            name_rect = name_surf.get_rect(center=(x + card_width // 2, card_y + 95))
            self.screen.blit(name_surf, name_rect)
            
            # 説明
            desc_surf = fonts.small.render(desc, True, Colors.TEXT_SECONDARY)
            desc_rect = desc_surf.get_rect(center=(x + card_width // 2, card_y + 125))
            self.screen.blit(desc_surf, desc_rect)
            
            # 詳細
            detail_surf = fonts.tiny.render(detail, True, Colors.TEXT_MUTED)
            detail_rect = detail_surf.get_rect(center=(x + card_width // 2, card_y + 155))
            self.screen.blit(detail_surf, detail_rect)
            
            # ボタン（カード全体）
            btn = Button(x, card_y, card_width, card_height, "", "ghost")
            btn.callback = None  # 視覚的なボタン
            buttons[f"difficulty_{level.name}"] = btn
        
        # 決定ボタン
        btn_y = card_y + card_height + 60
        buttons["confirm"] = Button(
            center_x - 150, btn_y, 300, 60,
            "決定して次へ →", "success", font=fonts.h3
        )
        buttons["confirm"].draw(self.screen)
        
        # 戻るボタン
        buttons["back_title"] = Button(
            50, height - 80, 150, 50,
            "← 戻る", "ghost", font=fonts.body
        )
        buttons["back_title"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    # ========================================
    # チーム選択画面（強化版）
    # ========================================
    def draw_team_select_screen(self, central_teams: List, pacific_teams: List, 
                                   custom_names: Dict = None, selected_team_name: str = None,
                                   preview_scroll: int = 0) -> Dict[str, Button]:
        """チーム選択画面を描画"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        custom_names = custom_names or {}
        
        # ヘッダー
        header_h = draw_header(self.screen, "TEAM SELECT", "監督としてチームを率いる球団を選んでください")
        
        buttons = {}
        
        # チーム追加ボタン
        add_team_btn = Button(
            width - 380, header_h - 45, 160, 36,
            "+ チーム追加", "primary", font=fonts.small
        )
        add_team_btn.draw(self.screen)
        buttons["add_team"] = add_team_btn
        
        # チーム名編集ボタン
        edit_names_btn = Button(
            width - 200, header_h - 45, 160, 36,
            "チーム名編集", "ghost", font=fonts.small
        )
        edit_names_btn.draw(self.screen)
        buttons["edit_team_names"] = edit_names_btn
        
        # 左側: チームリスト（2リーグ）
        list_width = 440
        panel_height = height - header_h - 50
        
        # 選択されたチームを見つける
        all_teams = central_teams + pacific_teams
        selected_team = None
        if selected_team_name:
            for team in all_teams:
                if team.name == selected_team_name:
                    selected_team = team
                    break
        
        mouse_pos = pygame.mouse.get_pos()
        hovered_team = None
        hovered_team_obj = None
        
        # リーグパネル（左側）
        leagues = [
            ("NORTH LEAGUE", north_teams, 25, Colors.PRIMARY),
            ("SOUTH LEAGUE", south_teams, 25 + list_width // 2 + 10, (180, 90, 60)),
        ]
        
        for league_name, teams, panel_x, accent_color in leagues:
            # パネル背景
            panel_w = list_width // 2 - 5
            panel_rect = pygame.Rect(panel_x, header_h + 15, panel_w, panel_height)
            draw_rounded_rect(self.screen, panel_rect, Colors.BG_CARD, 3)
            draw_rounded_rect(self.screen, panel_rect, Colors.BG_CARD, 3, 1, Colors.BORDER)
            
            # リーグ名
            league_surf = fonts.small.render(league_name, True, accent_color)
            league_rect = league_surf.get_rect(center=(panel_x + panel_w // 2, header_h + 38))
            self.screen.blit(league_surf, league_rect)
            
            # アクセントライン
            line_width = 60
            pygame.draw.line(self.screen, accent_color,
                           (panel_x + panel_w // 2 - line_width, header_h + 55),
                           (panel_x + panel_w // 2 + line_width, header_h + 55), 2)
            
            # チームボタン
            btn_width = panel_w - 20
            btn_height = 52  # 星評価削除によりコンパクトに
            btn_x = panel_x + 10
            btn_y = header_h + 70
            btn_spacing = 58
            
            for i, team in enumerate(teams):
                team_color = self.get_team_color(team.name)
                btn_rect = pygame.Rect(btn_x, btn_y + i * btn_spacing, btn_width, btn_height)
                
                # ホバー・選択検出
                is_hovered = btn_rect.collidepoint(mouse_pos)
                is_selected = selected_team_name == team.name
                
                if is_hovered:
                    hovered_team = team.name
                    hovered_team_obj = team
                
                # ボタン背景
                if is_selected:
                    bg_color = lerp_color(Colors.BG_CARD, team_color, 0.35)
                    border_color = team_color
                elif is_hovered:
                    bg_color = lerp_color(Colors.BG_CARD, team_color, 0.2)
                    border_color = Colors.BORDER_LIGHT
                else:
                    bg_color = lerp_color(Colors.BG_CARD, team_color, 0.06)
                    border_color = Colors.BORDER
                
                draw_rounded_rect(self.screen, btn_rect, bg_color, 3)
                draw_rounded_rect(self.screen, btn_rect, bg_color, 3, 2 if is_selected else 1, border_color)
                
                # チームカラーのアクセント（左側のバー）
                color_rect = pygame.Rect(btn_x, btn_y + i * btn_spacing, 4, btn_height)
                pygame.draw.rect(self.screen, team_color, color_rect)
                
                # チーム名（中央配置）
                display_name = custom_names.get(team.name, team.name)
                team_name_surf = fonts.body.render(display_name, True, Colors.TEXT_PRIMARY)
                team_name_rect = team_name_surf.get_rect(midleft=(btn_x + 14, btn_y + i * btn_spacing + btn_height // 2))
                self.screen.blit(team_name_surf, team_name_rect)
                
                # 選択インジケーター
                if is_selected:
                    indicator_surf = fonts.small.render("▶", True, team_color)
                    self.screen.blit(indicator_surf, (btn_x + btn_width - 25, btn_y + i * btn_spacing + btn_height // 2 - 8))
                
                # 登録ボタン（選択用）
                btn = Button(
                    btn_x, btn_y + i * btn_spacing, btn_width, btn_height,
                    "", "ghost", font=fonts.body
                )
                btn.is_hovered = is_hovered
                buttons[f"team_{team.name}"] = btn
        
        # 右側: 選択したチームの詳細プレビュー
        preview_x = 25 + list_width + 20
        preview_width = width - preview_x - 25
        
        # プレビューチーム（選択優先）
        preview_team = selected_team or hovered_team_obj
        
        if preview_team:
            self._draw_team_preview_panel_enhanced(preview_team, preview_x, header_h + 15, 
                                          preview_width, panel_height, custom_names, buttons, preview_scroll, 0)
        else:
            # 未選択時のガイド
            self._draw_team_select_guide_enhanced(preview_x, header_h + 15, preview_width, panel_height, 0)
        
        # 左下に戻るボタン（確実にクリック可能な位置に配置）
        back_btn = Button(
            25, height - 75, 140, 50,
            "← 戻る", "warning", font=fonts.body
        )
        back_btn.draw(self.screen)
        buttons["team_select_back"] = back_btn
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    def _calculate_team_power(self, team) -> int:
        """チームの総合戦力を5段階で計算"""
        if not team.players:
            return 3
        
        total_overall = sum(
            p.stats.overall_batting() if p.position.value != "P" else p.stats.overall_pitching()
            for p in team.players[:25]
        )
        avg_overall = total_overall / min(25, len(team.players))
        
        # thresholds updated for 1-99 scale (approx scaling factor 99/20 ≈ 5)
        if avg_overall >= 70:
            return 5
        elif avg_overall >= 60:
            return 4
        elif avg_overall >= 50:
            return 3
        elif avg_overall >= 40:
            return 2
        else:
            return 1
    
    def _draw_team_preview_panel(self, team, x: int, y: int, width: int, height: int, 
                                  custom_names: Dict, buttons: Dict):
        """チーム詳細プレビューパネル（レガシー互換）"""
        import time
        self._draw_team_preview_panel_enhanced(team, x, y, width, height, custom_names, buttons, 0, time.time())
    
    def _draw_team_preview_panel_scrollable(self, team, x: int, y: int, width: int, height: int, 
                                  custom_names: Dict, buttons: Dict, scroll_offset: int = 0):
        """チーム詳細プレビューパネル（スクロール対応・レガシー互換）"""
        import time
        self._draw_team_preview_panel_enhanced(team, x, y, width, height, custom_names, buttons, scroll_offset, time.time())
    
    def _draw_team_preview_panel_enhanced(self, team, x: int, y: int, width: int, height: int, 
                                  custom_names: Dict, buttons: Dict, scroll_offset: int = 0, anim_time: float = 0):
        """チーム詳細プレビューパネル"""
        team_color = self.get_team_color(team.name)
        
        # メインパネル背景（シャープ）
        panel_rect = pygame.Rect(x, y, width, height)
        draw_shadow(self.screen, panel_rect, 2, 5, 40)
        draw_rounded_rect(self.screen, panel_rect, Colors.BG_CARD, 3)
        
        # クリッピング領域を設定
        clip_rect = pygame.Rect(x, y, width, height - 75)
        
        # チームカラーのヘッダー（グラデーション効果）
        header_rect = pygame.Rect(x, y, width, 80)
        for hy in range(80):
            ratio = hy / 80
            line_color = lerp_color(lerp_color(Colors.BG_CARD, team_color, 0.35), Colors.BG_CARD, ratio * 0.7)
            pygame.draw.line(self.screen, line_color, (x, y + hy), (x + width, y + hy))
        
        # チームカラーのアクセントライン
        pygame.draw.rect(self.screen, team_color, pygame.Rect(x, y, 5, 80))
        
        # チーム名（大きく表示）
        display_name = custom_names.get(team.name, team.name)
        team_name_surf = fonts.h2.render(display_name, True, Colors.TEXT_PRIMARY)
        self.screen.blit(team_name_surf, (x + 20, y + 15))
        
        # 球場情報（チーム名の下に余裕を持って配置）
        stadium = NPB_STADIUMS.get(team.name, {})
        if stadium:
            stadium_name = stadium.get('name', '')
            location = stadium.get('location', '')
            stadium_text = f"{location} / {stadium_name}"
            stadium_surf = fonts.small.render(stadium_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(stadium_surf, (x + 20, y + 52))
        
        # スクロール可能なコンテンツエリア
        content_y = y + 90 - scroll_offset
        content_start_y = y + 90
        content_end_y = y + height - 85
        
        # クリッピング
        self.screen.set_clip(pygame.Rect(x, content_start_y, width, content_end_y - content_start_y))
        
        # 野手と投手を分類
        batters = [p for p in team.players if p.position.value != "投手"]
        pitchers = [p for p in team.players if p.position.value == "投手"]
        
        # ===== 戦力分析（改良版）=====
        section_height = 100
        if content_y + section_height > content_start_y and content_y < content_end_y:
            analysis_rect = pygame.Rect(x + 12, content_y, width - 24, section_height - 10)
            draw_rounded_rect(self.screen, analysis_rect, Colors.BG_INPUT, 3)
            
            # セクションヘッダー
            header_surf = fonts.small.render("■ POWER ANALYSIS", True, Colors.TEXT_ACCENT if hasattr(Colors, 'TEXT_ACCENT') else Colors.PRIMARY)
            self.screen.blit(header_surf, (x + 22, content_y + 10))
            
            # 攻撃力・守備力・投手力を計算
            offense_power = sum(p.stats.contact + p.stats.power for p in batters[:9]) / max(1, len(batters[:9])) / 2 if batters else 0
            defense_power = sum(p.stats.fielding + p.stats.arm for p in batters[:9]) / max(1, len(batters[:9])) / 2 if batters else 0
            pitching_power = sum(p.stats.speed + p.stats.control for p in pitchers[:6]) / max(1, len(pitchers[:6])) / 2 if pitchers else 0
            
            # 3つのバー（横並び・改良版）
            bar_items = [
                ("OFFENSE", offense_power / 99, (180, 80, 80)),
                ("DEFENSE", defense_power / 99, (80, 150, 100)),
                ("PITCHING", pitching_power / 99, (80, 120, 180)),
            ]
            
            bar_width = (width - 70) // 3
            for i, (label, value, color) in enumerate(bar_items):
                bx = x + 22 + i * (bar_width + 8)
                by = content_y + 38
                
                # ラベル
                label_surf = fonts.tiny.render(label, True, Colors.TEXT_MUTED)
                self.screen.blit(label_surf, (bx, by))
                
                # バー背景
                bar_rect = pygame.Rect(bx, by + 18, bar_width - 15, 16)
                pygame.draw.rect(self.screen, Colors.BG_DARKER if hasattr(Colors, 'BG_DARKER') else (15, 17, 22), bar_rect, border_radius=2)
                
                # バー本体
                fill_width = int((bar_width - 15) * min(1.0, value))
                if fill_width > 0:
                    fill_rect = pygame.Rect(bx, by + 18, fill_width, 16)
                    pygame.draw.rect(self.screen, color, fill_rect, border_radius=2)
                
                # 数値
                value_text = f"{int(value * 100)}"
                value_surf = fonts.tiny.render(value_text, True, Colors.TEXT_PRIMARY)
                self.screen.blit(value_surf, (bx + bar_width - 35, by))
        
        content_y += section_height
        
        # ===== 主力野手（改良版）=====
        section_height = 160
        if content_y + section_height > content_start_y and content_y < content_end_y:
            batter_rect = pygame.Rect(x + 12, content_y, width - 24, section_height - 10)
            draw_rounded_rect(self.screen, batter_rect, Colors.BG_INPUT, 3)
            
            header_surf = fonts.small.render("■ TOP BATTERS", True, Colors.TEXT_ACCENT if hasattr(Colors, 'TEXT_ACCENT') else Colors.PRIMARY)
            self.screen.blit(header_surf, (x + 22, content_y + 10))
            
            top_batters = sorted(batters, key=lambda p: p.stats.overall_batting(), reverse=True)[:5]
            for i, player in enumerate(top_batters):
                py = content_y + 35 + i * 24
                
                # ポジション（固定幅）
                pos_text = player.position.value[:2] if len(player.position.value) > 2 else player.position.value
                pos_surf = fonts.tiny.render(pos_text, True, Colors.TEXT_MUTED)
                self.screen.blit(pos_surf, (x + 22, py + 2))
                
                # 名前（固定幅エリア）
                name_surf = fonts.small.render(player.name[:10], True, Colors.TEXT_PRIMARY)
                self.screen.blit(name_surf, (x + 55, py))
                
                # 能力値バッジ（右端に固定）：総合を★数値表記に変更（1-999スケール）
                overall = player.overall_rating
                badge_color = self._get_overall_color(overall / 10)  # color based on 1-99 equivalent
                badge_text = f"★{overall}"
                badge_surf = fonts.tiny.render(badge_text, True, badge_color)
                badge_x = x + width - 70
                self.screen.blit(badge_surf, (badge_x, py + 2))
        
        content_y += section_height
        
        # ===== 主力投手（改良版）=====
        section_height = 160
        if content_y + section_height > content_start_y and content_y < content_end_y:
            pitcher_rect = pygame.Rect(x + 12, content_y, width - 24, section_height - 10)
            draw_rounded_rect(self.screen, pitcher_rect, Colors.BG_INPUT, 3)
            
            header_surf = fonts.small.render("■ TOP PITCHERS", True, Colors.TEXT_ACCENT if hasattr(Colors, 'TEXT_ACCENT') else Colors.PRIMARY)
            self.screen.blit(header_surf, (x + 22, content_y + 10))
            
            top_pitchers = sorted(pitchers, key=lambda p: p.stats.overall_pitching(), reverse=True)[:5]
            for i, player in enumerate(top_pitchers):
                py = content_y + 35 + i * 24
                
                # 役割（先発/中継/抑え）
                if hasattr(player, 'starter_aptitude') and player.starter_aptitude >= 70:
                    role = "先発"
                elif hasattr(player, 'closer_aptitude') and player.closer_aptitude >= 70:
                    role = "抑え"
                else:
                    role = "中継"
                pos_surf = fonts.tiny.render(role, True, Colors.TEXT_MUTED)
                self.screen.blit(pos_surf, (x + 22, py + 2))
                
                # 名前
                name_surf = fonts.small.render(player.name[:10], True, Colors.TEXT_PRIMARY)
                self.screen.blit(name_surf, (x + 55, py))
                
                # 能力値バッジ：総合を★数値表記に変更（1-999スケール）
                overall = player.overall_rating
                badge_color = self._get_overall_color(overall / 10)  # color based on 1-99 equivalent
                badge_text = f"★{overall}"
                badge_surf = fonts.tiny.render(badge_text, True, badge_color)
                badge_x = x + width - 70
                self.screen.blit(badge_surf, (badge_x, py + 2))
        
        content_y += section_height
        
        # ===== 球場情報（改良版）=====
        section_height = 90
        if content_y + section_height > content_start_y and content_y < content_end_y:
            stadium_rect = pygame.Rect(x + 12, content_y, width - 24, section_height - 10)
            draw_rounded_rect(self.screen, stadium_rect, Colors.BG_INPUT, 3)
            
            header_surf = fonts.small.render("■ STADIUM", True, Colors.TEXT_ACCENT if hasattr(Colors, 'TEXT_ACCENT') else Colors.PRIMARY)
            self.screen.blit(header_surf, (x + 22, content_y + 10))
            
            if stadium:
                sy = content_y + 38
                
                # 収容人数
                cap_text = f"収容: {stadium.get('capacity', 0):,}人"
                cap_surf = fonts.small.render(cap_text, True, Colors.TEXT_SECONDARY)
                self.screen.blit(cap_surf, (x + 22, sy))
                
                # HR係数
                hr_factor = stadium.get("home_run_factor", 1.0)
                if hr_factor > 1.05:
                    hr_text = f"HR係数: {hr_factor:.2f} (打者有利)"
                    hr_color = (180, 100, 100)
                elif hr_factor < 0.95:
                    hr_text = f"HR係数: {hr_factor:.2f} (投手有利)"
                    hr_color = (100, 150, 100)
                else:
                    hr_text = f"HR係数: {hr_factor:.2f} (標準)"
                    hr_color = Colors.TEXT_SECONDARY
                hr_surf = fonts.small.render(hr_text, True, hr_color)
                self.screen.blit(hr_surf, (x + 22, sy + 22))
        
        # クリッピング解除
        self.screen.set_clip(None)
        
        # 下部に固定ボタンエリア（グラデーション背景）
        btn_area_rect = pygame.Rect(x, y + height - 75, width, 75)
        for by_offset in range(75):
            ratio = by_offset / 75
            line_color = lerp_color(Colors.BG_CARD, (20, 23, 28), ratio * 0.3)
            pygame.draw.line(self.screen, line_color, (x, y + height - 75 + by_offset), (x + width, y + height - 75 + by_offset))
        
        # セパレーター
        pygame.draw.line(self.screen, Colors.BORDER, (x + 15, y + height - 74), (x + width - 15, y + height - 74))
        
        # 決定ボタン（チームカラー付き）
        confirm_btn = Button(
            x + 15, y + height - 60, width - 30, 48,
            f"{display_name} で始める", "success", font=fonts.h3
        )
        confirm_btn.draw(self.screen)
        buttons["confirm_team"] = confirm_btn
        
        # スクロールインジケーター
        total_content_height = 100 + 160 + 160 + 90
        visible_height = height - 165
        
        if total_content_height > visible_height:
            scrollbar_height = max(30, int(visible_height * visible_height / total_content_height))
            max_scroll = max(1, total_content_height - visible_height)
            scrollbar_y = y + 90 + int((visible_height - scrollbar_height) * scroll_offset / max_scroll)
            scrollbar_rect = pygame.Rect(x + width - 6, scrollbar_y, 3, scrollbar_height)
            pygame.draw.rect(self.screen, Colors.BORDER_LIGHT, scrollbar_rect, border_radius=1)
    
    def _draw_team_select_guide(self, x: int, y: int, width: int, height: int):
        """チーム未選択時のガイド（レガシー互換）"""
        import time
        self._draw_team_select_guide_enhanced(x, y, width, height, time.time())
    
    def _draw_team_select_guide_enhanced(self, x: int, y: int, width: int, height: int, anim_time: float = 0):
        """チーム未選択時のガイド"""
        panel_rect = pygame.Rect(x, y, width, height)
        draw_rounded_rect(self.screen, panel_rect, Colors.BG_CARD, 3)
        draw_rounded_rect(self.screen, panel_rect, Colors.BG_CARD, 3, 1, Colors.BORDER)
        
        # 中央にガイドテキスト
        center_x = x + width // 2
        center_y = y + height // 2
        
        # アイコン
        icon_surf = fonts.title.render("NPB", True, Colors.TEXT_MUTED)
        icon_rect = icon_surf.get_rect(center=(center_x, center_y - 80))
        self.screen.blit(icon_surf, icon_rect)
        
        # メインテキスト
        text1 = "SELECT YOUR TEAM"
        text1_surf = fonts.h2.render(text1, True, Colors.TEXT_PRIMARY)
        text1_rect = text1_surf.get_rect(center=(center_x, center_y - 10))
        self.screen.blit(text1_surf, text1_rect)
        
        # サブテキスト
        text2 = "左のリストからチームを選択"
        text3 = "クリックで詳細情報を表示"
        text2_surf = fonts.body.render(text2, True, Colors.TEXT_SECONDARY)
        text3_surf = fonts.body.render(text3, True, Colors.TEXT_MUTED)
        text2_rect = text2_surf.get_rect(center=(center_x, center_y + 30))
        text3_rect = text3_surf.get_rect(center=(center_x, center_y + 58))
        self.screen.blit(text2_surf, text2_rect)
        self.screen.blit(text3_surf, text3_rect)
        
        # 矢印インジケーター（左を指す）
        arrow_x = center_x - 100
        arrow_y = center_y + 100
        
        # 矢印を描画
        arrow_color = Colors.TEXT_MUTED
        pygame.draw.polygon(self.screen, arrow_color, [
            (arrow_x, arrow_y),
            (arrow_x + 20, arrow_y - 12),
            (arrow_x + 20, arrow_y + 12)
        ])
        pygame.draw.rect(self.screen, arrow_color, pygame.Rect(arrow_x + 18, arrow_y - 5, 40, 10))
        
        hint_surf = fonts.small.render("チームを選択", True, Colors.TEXT_MUTED)
        hint_rect = hint_surf.get_rect(midleft=(arrow_x + 65, arrow_y))
        self.screen.blit(hint_surf, hint_rect)
    
    def _get_overall_color(self, overall: float) -> tuple:
        """総合力に応じた色を返す（1-99スケール用）"""
        if overall >= 80:
            return Colors.GOLD
        elif overall >= 70:
            return Colors.SUCCESS
        elif overall >= 60:
            return Colors.PRIMARY
        elif overall >= 50:
            return Colors.TEXT_PRIMARY
        else:
            return Colors.TEXT_MUTED
    
    def _draw_team_info_tooltip(self, team_name: str, mouse_pos: tuple):
        """チーム情報のツールチップを描画（レガシー互換用）"""
        stadium = NPB_STADIUMS.get(team_name, {})
        if not stadium:
            return
        
        # ツールチップの内容
        lines = [
            f"{stadium.get('location', '')}",
            f"{stadium.get('name', '')}",
            f"収容: {stadium.get('capacity', 0):,}人",
            f"HR係数: {stadium.get('home_run_factor', 1.0):.2f}",
        ]
        
        # サイズ計算
        max_width = max(fonts.small.size(line)[0] for line in lines) + 30
        tooltip_height = len(lines) * 25 + 20
        
        # 位置調整（画面外に出ないように）
        x = min(mouse_pos[0] + 20, self.screen.get_width() - max_width - 10)
        y = min(mouse_pos[1] + 20, self.screen.get_height() - tooltip_height - 10)
        
        # 背景
        tooltip_rect = pygame.Rect(x, y, max_width, tooltip_height)
        draw_shadow(self.screen, tooltip_rect, 3, 6, 40)
        draw_rounded_rect(self.screen, tooltip_rect, Colors.BG_CARD, 8)
        draw_rounded_rect(self.screen, tooltip_rect, Colors.BG_CARD, 8, 1, Colors.BORDER_LIGHT)
        
        # テキスト
        text_y = y + 10
        for line in lines:
            line_surf = fonts.small.render(line, True, Colors.TEXT_PRIMARY)
            self.screen.blit(line_surf, (x + 15, text_y))
            text_y += 25

    # ========================================
    # メインメニュー画面（スタイリッシュ版）
    # ========================================
    def draw_menu_screen(self, player_team, current_year: int, schedule_manager, news_list: list = None, central_teams: list = None, pacific_teams: list = None) -> Dict[str, Button]:
        """メインメニュー画面を描画（洗練されたスポーツデザイン）"""
        width = self.screen.get_width()
        height = self.screen.get_height()
        
        # グラデーション背景
        for y in range(height):
            ratio = y / height
            r = int(18 + 8 * ratio)
            g = int(20 + 10 * ratio)
            b = int(28 + 12 * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (width, y))
        
        team_color = self.get_team_color(player_team.name) if player_team else Colors.PRIMARY
        
        # 装飾ライン（斜めのアクセント）
        line_color = (*team_color[:3], 30) if len(team_color) == 3 else team_color
        for i in range(3):
            start_x = width - 300 + i * 80
            pygame.draw.line(self.screen, (team_color[0]//4, team_color[1]//4, team_color[2]//4), 
                           (start_x, 0), (start_x - 150, height), 2)
        
        # 上部アクセントライン
        pygame.draw.rect(self.screen, team_color, (0, 0, width, 3))
        
        buttons = {}
        
        # ========================================
        # 左上: チーム情報
        # ========================================
        if player_team:
            # チーム略称
            abbr = self.get_team_abbr(player_team.name)
            abbr_surf = fonts.title.render(abbr, True, team_color)
            self.screen.blit(abbr_surf, (30, 20))
            
            # チーム名
            team_name_surf = fonts.body.render(player_team.name, True, Colors.TEXT_SECONDARY)
            self.screen.blit(team_name_surf, (30, 75))
            
            # シーズン
            year_surf = fonts.small.render(f"{current_year}年シーズン", True, Colors.TEXT_MUTED)
            self.screen.blit(year_surf, (30, 100))
            
            # 成績
            record_y = 135
            record_surf = fonts.h2.render(f"{player_team.wins} - {player_team.losses} - {player_team.draws}", True, Colors.TEXT_PRIMARY)
            self.screen.blit(record_surf, (30, record_y))
            
            # 勝率
            rate = player_team.win_rate if player_team.games_played > 0 else 0
            rate_text = f"勝率 .{int(rate * 1000):03d}"
            rate_surf = fonts.body.render(rate_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(rate_surf, (30, record_y + 40))
            
            # 試合進行
            progress_text = f"{player_team.games_played} / 143 試合"
            progress_surf = fonts.small.render(progress_text, True, Colors.TEXT_MUTED)
            self.screen.blit(progress_surf, (30, record_y + 65))
        
        # ========================================
        # 左側: 次の試合情報
        # ========================================
        next_game = None
        if schedule_manager and player_team:
            next_game = schedule_manager.get_next_game_for_team(player_team.name)
        
        game_y = 245
        next_label = fonts.small.render("NEXT GAME", True, Colors.TEXT_MUTED)
        self.screen.blit(next_label, (30, game_y))
        
        if next_game:
            is_home = next_game.home_team_name == player_team.name
            opponent = next_game.away_team_name if is_home else next_game.home_team_name
            opp_abbr = self.get_team_abbr(opponent)
            
            # 対戦カード
            my_abbr = self.get_team_abbr(player_team.name)
            vs_text = f"{my_abbr}  vs  {opp_abbr}"
            vs_surf = fonts.h3.render(vs_text, True, Colors.TEXT_PRIMARY)
            self.screen.blit(vs_surf, (30, game_y + 25))
            
            # HOME/AWAY
            location = "（ホーム）" if is_home else "（アウェイ）"
            loc_surf = fonts.small.render(location, True, Colors.TEXT_MUTED)
            self.screen.blit(loc_surf, (30, game_y + 55))
        else:
            end_surf = fonts.h3.render("シーズン終了", True, Colors.GOLD)
            self.screen.blit(end_surf, (30, game_y + 25))
        
        # ========================================
        # 左側: ニュース（最新5件）
        # ========================================
        news_y = 340
        news_label = fonts.small.render("NEWS", True, Colors.TEXT_MUTED)
        self.screen.blit(news_label, (30, news_y))
        
        if news_list and len(news_list) > 0:
            for i, news_item in enumerate(news_list[:5]):
                # news_itemはdict形式 {"date": "...", "text": "..."} または文字列
                if isinstance(news_item, dict):
                    date_str = news_item.get("date", "")
                    text_str = news_item.get("text", "")
                    news_text = f"[{date_str}] {text_str}"
                else:
                    news_text = str(news_item)
                
                # 長すぎる場合は省略
                if len(news_text) > 35:
                    news_text = news_text[:35] + "..."
                
                news_surf = fonts.tiny.render(news_text, True, Colors.TEXT_SECONDARY)
                self.screen.blit(news_surf, (30, news_y + 22 + i * 20))
        else:
            no_news = fonts.tiny.render("ニュースはありません", True, Colors.TEXT_MUTED)
            self.screen.blit(no_news, (30, news_y + 22))
        
        # ========================================
        # 中央下部: 両リーグ順位表
        # ========================================
        standings_y = height - 220
        standings_width = 200
        
        # セ・リーグ
        cl_x = 30
        cl_label = fonts.small.render("セ・リーグ", True, Colors.TEXT_MUTED)
        self.screen.blit(cl_label, (cl_x, standings_y))
        
        if central_teams:
            c_teams = sorted(central_teams, key=lambda t: (t.wins - t.losses, t.wins), reverse=True)
            for i, team in enumerate(c_teams[:6]):
                is_player = player_team and team.name == player_team.name
                t_abbr = self.get_team_abbr(team.name)
                t_color = self.get_team_color(team.name)
                
                y = standings_y + 22 + i * 22
                
                # 順位
                rank_surf = fonts.tiny.render(f"{i+1}", True, Colors.TEXT_MUTED)
                self.screen.blit(rank_surf, (cl_x, y))
                
                # チーム名
                name_color = t_color if is_player else Colors.TEXT_SECONDARY
                name_surf = fonts.tiny.render(t_abbr, True, name_color)
                self.screen.blit(name_surf, (cl_x + 25, y))
                
                # 勝敗
                record_text = f"{team.wins}-{team.losses}"
                record_surf = fonts.tiny.render(record_text, True, Colors.TEXT_MUTED)
                self.screen.blit(record_surf, (cl_x + 85, y))
                
                # 勝率
                rate = team.win_rate if team.games_played > 0 else 0
                rate_text = f".{int(rate * 1000):03d}"
                rate_surf = fonts.tiny.render(rate_text, True, Colors.TEXT_MUTED)
                self.screen.blit(rate_surf, (cl_x + 140, y))
        
        # パ・リーグ
        pl_x = cl_x + standings_width + 30
        pl_label = fonts.small.render("パ・リーグ", True, Colors.TEXT_MUTED)
        self.screen.blit(pl_label, (pl_x, standings_y))
        
        if pacific_teams:
            p_teams = sorted(pacific_teams, key=lambda t: (t.wins - t.losses, t.wins), reverse=True)
            for i, team in enumerate(p_teams[:6]):
                is_player = player_team and team.name == player_team.name
                t_abbr = self.get_team_abbr(team.name)
                t_color = self.get_team_color(team.name)
                
                y = standings_y + 22 + i * 22
                
                # 順位
                rank_surf = fonts.tiny.render(f"{i+1}", True, Colors.TEXT_MUTED)
                self.screen.blit(rank_surf, (pl_x, y))
                
                # チーム名
                name_color = t_color if is_player else Colors.TEXT_SECONDARY
                name_surf = fonts.tiny.render(t_abbr, True, name_color)
                self.screen.blit(name_surf, (pl_x + 25, y))
                
                # 勝敗
                record_text = f"{team.wins}-{team.losses}"
                record_surf = fonts.tiny.render(record_text, True, Colors.TEXT_MUTED)
                self.screen.blit(record_surf, (pl_x + 85, y))
                
                # 勝率
                rate = team.win_rate if team.games_played > 0 else 0
                rate_text = f".{int(rate * 1000):03d}"
                rate_surf = fonts.tiny.render(rate_text, True, Colors.TEXT_MUTED)
                self.screen.blit(rate_surf, (pl_x + 140, y))
        
        # ========================================
        # 右下: メニューボタン（小型・英語+日本語）
        # ========================================
        btn_w = 120
        btn_h = 50
        btn_gap = 8
        # 右下に配置（3行2列 + システムボタン1行）
        total_btn_height = (btn_h + btn_gap) * 3 + 15 + 32  # メニュー3行 + gap + システム1行
        btn_area_x = width - 275
        btn_area_y = height - total_btn_height - 25  # 下から配置
        
        menu_buttons = [
            ("start_game", "PLAY", "試合"),
            ("roster", "ROSTER", "編成"),
            ("schedule", "SCHEDULE", "日程"),
            ("training", "TRAINING", "育成"),
            ("management", "FINANCE", "経営"),
            ("records", "RECORDS", "記録"),
        ]
        
        for i, (name, en_label, jp_label) in enumerate(menu_buttons):
            col = i % 2
            row = i // 2
            bx = btn_area_x + col * (btn_w + btn_gap)
            by = btn_area_y + row * (btn_h + btn_gap)
            
            # ボタン背景
            btn_rect = pygame.Rect(bx, by, btn_w, btn_h)
            
            # PLAYボタンは特別な色
            if name == "start_game":
                pygame.draw.rect(self.screen, (40, 45, 55), btn_rect, border_radius=8)
                pygame.draw.rect(self.screen, team_color, btn_rect, 2, border_radius=8)
            else:
                pygame.draw.rect(self.screen, (35, 38, 48), btn_rect, border_radius=8)
                pygame.draw.rect(self.screen, (60, 65, 75), btn_rect, 1, border_radius=8)
            
            # 英語ラベル
            en_surf = fonts.small.render(en_label, True, Colors.TEXT_PRIMARY)
            en_rect = en_surf.get_rect(centerx=bx + btn_w // 2, top=by + 8)
            self.screen.blit(en_surf, en_rect)
            
            # 日本語ラベル
            jp_surf = fonts.tiny.render(jp_label, True, Colors.TEXT_MUTED)
            jp_rect = jp_surf.get_rect(centerx=bx + btn_w // 2, top=by + 28)
            self.screen.blit(jp_surf, jp_rect)
            
            btn = Button(bx, by, btn_w, btn_h, "", "ghost")
            buttons[name] = btn
        
        # システムボタン（右下最下部）
        sys_y = btn_area_y + (btn_h + btn_gap) * 3 + 15
        sys_btn_w = 75
        sys_btn_h = 32
        
        sys_buttons = [
            ("save_game", "SAVE", "保存"),
            ("settings_menu", "CONFIG", "設定"),
            ("return_to_title", "TITLE", "戻る"),
        ]
        
        for i, (name, en_label, jp_label) in enumerate(sys_buttons):
            bx = btn_area_x + i * (sys_btn_w + 8)
            
            btn_rect = pygame.Rect(bx, sys_y, sys_btn_w, sys_btn_h)
            pygame.draw.rect(self.screen, (30, 32, 40), btn_rect, border_radius=6)
            pygame.draw.rect(self.screen, (50, 55, 65), btn_rect, 1, border_radius=6)
            
            # ラベル
            label_surf = fonts.tiny.render(en_label, True, Colors.TEXT_SECONDARY)
            label_rect = label_surf.get_rect(center=(bx + sys_btn_w // 2, sys_y + sys_btn_h // 2))
            self.screen.blit(label_surf, label_rect)
            
            btn = Button(bx, sys_y, sys_btn_w, sys_btn_h, "", "ghost")
            buttons[name] = btn
        
        # 区切り線
        pygame.draw.line(self.screen, (40, 45, 55), (btn_area_x - 25, 30), (btn_area_x - 25, height - 30), 1)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    def _draw_league_standings_modern(self, x: int, y: int, width: int, height: int,
                                       player_team, schedule_manager, team_color):
        """モダンなリーグ順位パネル"""
        # パネル背景
        panel_rect = pygame.Rect(x, y, width, height)
        draw_rounded_rect(self.screen, panel_rect, Colors.BG_CARD, 16)
        
        if not player_team:
            return
        
        # プレイヤーのリーグ
        is_central = player_team.league.value == "セントラル"
        league_name = "CENTRAL" if is_central else "PACIFIC"
        accent_color = team_color
        
        # タイトル
        title_surf = fonts.small.render(league_name, True, accent_color)
        self.screen.blit(title_surf, (x + 20, y + 15))
        
        league_label = fonts.tiny.render("LEAGUE", True, Colors.TEXT_MUTED)
        self.screen.blit(league_label, (x + 20, y + 35))
        
        # 区切り線
        pygame.draw.line(self.screen, Colors.BORDER, (x + 15, y + 60), (x + width - 15, y + 60), 1)
        
        # 順位データ
        if schedule_manager:
            if is_central and hasattr(schedule_manager, 'central_teams'):
                teams = schedule_manager.central_teams
            elif hasattr(schedule_manager, 'pacific_teams'):
                teams = schedule_manager.pacific_teams
            else:
                teams = []
            
            sorted_teams = sorted(teams, key=lambda t: (-t.win_rate, -t.wins))
            
            row_y = y + 75
            row_height = 52
            
            for rank, team in enumerate(sorted_teams, 1):
                t_color = self.get_team_color(team.name)
                is_player_team = player_team and team.name == player_team.name
                
                # プレイヤーチームをハイライト
                if is_player_team:
                    highlight_rect = pygame.Rect(x + 10, row_y - 5, width - 20, row_height - 2)
                    draw_rounded_rect(self.screen, highlight_rect, lerp_color(Colors.BG_CARD, accent_color, 0.15), 8)
                
                # 順位バッジ
                rank_colors = {1: Colors.GOLD, 2: (192, 192, 192), 3: (205, 127, 50)}
                rank_color = rank_colors.get(rank, Colors.TEXT_MUTED)
                rank_surf = fonts.body.render(str(rank), True, rank_color)
                self.screen.blit(rank_surf, (x + 20, row_y + 10))
                
                # チーム略称
                abbr = self.get_team_abbr(team.name)
                name_color = Colors.TEXT_PRIMARY if is_player_team else Colors.TEXT_SECONDARY
                name_surf = fonts.body.render(abbr, True, t_color)
                self.screen.blit(name_surf, (x + 50, row_y + 10))
                
                # 勝敗
                record = f"{team.wins}-{team.losses}"
                record_surf = fonts.small.render(record, True, Colors.TEXT_SECONDARY)
                record_rect = record_surf.get_rect(right=x + width - 70, centery=row_y + 18)
                self.screen.blit(record_surf, record_rect)
                
                # 勝率
                rate = f".{int(team.win_rate * 1000):03d}" if team.games_played > 0 else ".000"
                rate_surf = fonts.small.render(rate, True, Colors.TEXT_PRIMARY)
                rate_rect = rate_surf.get_rect(right=x + width - 20, centery=row_y + 18)
                self.screen.blit(rate_surf, rate_rect)
                
                row_y += row_height
    
    def _draw_league_standings_compact(self, x: int, y: int, width: int, height: int,
                                        player_team, schedule_manager):
        """リーグ順位パネル（コンパクト版）- 後方互換用"""
        self._draw_league_standings_modern(x, y, width, height, player_team, schedule_manager,
                                           self.get_team_color(player_team.name) if player_team else Colors.PRIMARY)

    # 旧メソッド保持（後方互換）
    def _draw_league_standings_compact_old(self, x: int, y: int, width: int, height: int,
                                        player_team, schedule_manager):
        """リーグ順位パネル（コンパクト版）"""
        # パネル背景
        panel_rect = pygame.Rect(x, y, width, height)
        draw_rounded_rect(self.screen, panel_rect, Colors.BG_CARD, 12)
        
        # プレイヤーのリーグ
        is_central = player_team.league.value == "セントラル" if player_team else True
        league_name = "セ・リーグ" if is_central else "パ・リーグ"
        accent_color = Colors.PRIMARY if is_central else Colors.DANGER
        
        # タイトル
        title_surf = fonts.body.render(f"{league_name} 順位", True, accent_color)
        self.screen.blit(title_surf, (x + 15, y + 12))
        
        # 区切り線
        pygame.draw.line(self.screen, Colors.BORDER, (x + 12, y + 40), (x + width - 12, y + 40), 1)
        
        # 順位データ
        if schedule_manager:
            if is_central and hasattr(schedule_manager, 'central_teams'):
                teams = schedule_manager.central_teams
            elif hasattr(schedule_manager, 'pacific_teams'):
                teams = schedule_manager.pacific_teams
            else:
                teams = []
            
            sorted_teams = sorted(teams, key=lambda t: (-t.win_rate, -t.wins))
            
            row_y = y + 50
            row_height = 36
            
            for rank, team in enumerate(sorted_teams, 1):
                # プレイヤーチームをハイライト
                if player_team and team.name == player_team.name:
                    highlight_rect = pygame.Rect(x + 8, row_y - 2, width - 16, row_height - 4)
                    pygame.draw.rect(self.screen, lerp_color(Colors.BG_CARD, accent_color, 0.2), highlight_rect, border_radius=6)
                
                team_color = self.get_team_color(team.name)
                
                # 順位バッジ
                rank_colors = {1: Colors.GOLD, 2: (192, 192, 192), 3: (205, 127, 50)}
                rank_color = rank_colors.get(rank, Colors.TEXT_MUTED)
                rank_surf = fonts.body.render(str(rank), True, rank_color)
                self.screen.blit(rank_surf, (x + 15, row_y + 6))
                
                # チーム略称
                abbr = self.get_team_abbr(team.name)
                name_surf = fonts.body.render(abbr, True, team_color)
                self.screen.blit(name_surf, (x + 40, row_y + 6))
                
                # 勝敗（コンパクト）
                record = f"{team.wins}-{team.losses}"
                record_surf = fonts.small.render(record, True, Colors.TEXT_SECONDARY)
                self.screen.blit(record_surf, (x + 115, row_y + 8))
                
                # 勝率
                rate = f".{int(team.win_rate * 1000):03d}" if team.games_played > 0 else ".000"
                rate_surf = fonts.small.render(rate, True, Colors.TEXT_PRIMARY)
                self.screen.blit(rate_surf, (x + 175, row_y + 8))
                
                row_y += row_height
        
        # もう一方のリーグへの切り替えボタン（小さく）
        other_league = "パ・リーグ" if is_central else "セ・リーグ"
        switch_text = f"→ {other_league}"
        switch_surf = fonts.tiny.render(switch_text, True, Colors.TEXT_MUTED)
        self.screen.blit(switch_surf, (x + width - 80, y + 12))
    
    # ========================================
    # オーダー設定画面（ドラッグ&ドロップ対応）
    # ========================================
    def draw_lineup_screen(self, player_team, scroll_offset: int = 0,
                           dragging_player_idx: int = -1,
                           drag_pos: tuple = None,
                           selected_position: str = None,
                           dragging_position_slot: int = -1,
                           position_drag_pos: tuple = None,
                           lineup_edit_mode: str = "player",
                           lineup_selected_player_idx: int = -1,
                           lineup_selected_slot: int = -1,
                           lineup_selected_source: str = "",
                           lineup_swap_mode: bool = False,
                           position_selected_slot: int = -1,
                           batting_order_selected_slot: int = -1,
                           roster_position_selected_slot: int = -1) -> Dict[str, Button]:
        """オーダー設定画面を描画（ドラッグ&ドロップ対応）"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        
        team_color = self.get_team_color(player_team.name) if player_team else Colors.PRIMARY
        header_h = draw_header(self.screen, "オーダー設定", 
                               "選手をドラッグして打順に配置", team_color)
        
        buttons = {}
        drop_zones = {}  # ドロップゾーン情報
        
        if not player_team:
            return buttons
        
        # ========================================
        # 左パネル: 野球場型のポジション配置
        # ========================================
        field_card = Card(30, header_h + 20, 480, 420, "POSITION")
        field_rect = field_card.draw(self.screen)
        
        # フィールドの中心
        field_cx = field_rect.x + field_rect.width // 2
        field_cy = field_rect.y + 220
        
        # 守備位置の座標（野球場型配置 - 位置調整）
        position_coords = {
            "捕手": (field_cx, field_cy + 100),
            "一塁手": (field_cx + 100, field_cy + 20),
            "二塁手": (field_cx + 45, field_cy - 50),
            "三塁手": (field_cx - 100, field_cy + 20),
            "遊撃手": (field_cx - 45, field_cy - 50),
            "左翼手": (field_cx - 110, field_cy - 130),
            "中堅手": (field_cx, field_cy - 160),
            "右翼手": (field_cx + 110, field_cy - 130),
        }
        
        # DHスロットの位置（フィールド下部）
        dh_position = (field_cx, field_cy + 165)
        
        # グラウンドを簡易的に描画
        # 外野の扇形
        pygame.draw.arc(self.screen, Colors.SUCCESS, 
                       (field_cx - 160, field_cy - 220, 320, 320),
                       3.14 * 0.75, 3.14 * 0.25, 2)
        
        # 内野ダイヤモンド
        diamond = [
            (field_cx, field_cy - 40),   # 2塁
            (field_cx + 60, field_cy + 30),  # 1塁
            (field_cx, field_cy + 100),  # ホーム
            (field_cx - 60, field_cy + 30),  # 3塁
        ]
        pygame.draw.polygon(self.screen, Colors.BORDER, diamond, 2)
        
        # 投手マウンド
        pygame.draw.circle(self.screen, Colors.BORDER, (field_cx, field_cy + 30), 8, 2)
        
        # 守備配置を取得（チームのposition_assignmentsを優先）
        lineup = player_team.current_lineup if player_team.current_lineup else []
        
        # チームに保存された守備位置情報を使用
        if hasattr(player_team, 'position_assignments') and player_team.position_assignments:
            position_assignments = dict(player_team.position_assignments)
        else:
            position_assignments = {}
            # 現在のラインナップから守備位置を自動割り当て
            for order_idx, player_idx in enumerate(lineup):
                if player_idx >= 0 and player_idx < len(player_team.players):
                    player = player_team.players[player_idx]
                    pos = player.position.value
                    
                    # 外野手は順番に配置
                    if pos == "外野手":
                        for field_pos in ["左翼手", "中堅手", "右翼手"]:
                            if field_pos not in position_assignments:
                                position_assignments[field_pos] = player_idx
                                break
                    elif pos in position_coords:
                        if pos not in position_assignments:
                            position_assignments[pos] = player_idx
        
        # 各守備位置を描画
        for pos_name, (px, py) in position_coords.items():
            # 短縮名
            short_names = {
                "捕手": "捕", "一塁手": "一", "二塁手": "二", "三塁手": "三",
                "遊撃手": "遊", "左翼手": "左", "中堅手": "中", "右翼手": "右"
            }
            display_name = short_names.get(pos_name, pos_name[:1])
            
            # スロット背景（小さめ）
            slot_rect = pygame.Rect(px - 38, py - 20, 76, 40)
            
            # ドロップゾーンとして登録
            drop_zones[f"pos_{pos_name}"] = slot_rect
            
            # ドラッグ中のハイライト
            if dragging_player_idx >= 0 and slot_rect.collidepoint(drag_pos or (0, 0)):
                pygame.draw.rect(self.screen, (*Colors.PRIMARY[:3], 100), slot_rect, border_radius=6)
                pygame.draw.rect(self.screen, Colors.PRIMARY, slot_rect, 2, border_radius=6)
            else:
                pygame.draw.rect(self.screen, Colors.BG_CARD_HOVER, slot_rect, border_radius=6)
                pygame.draw.rect(self.screen, Colors.BORDER, slot_rect, 1, border_radius=6)
            
            # 配置済み選手
            if pos_name in position_assignments:
                player_idx = position_assignments[pos_name]
                player = player_team.players[player_idx]
                name = player.name[:3]
                name_surf = fonts.tiny.render(name, True, Colors.TEXT_PRIMARY)
                name_rect = name_surf.get_rect(center=(px, py - 3))
                self.screen.blit(name_surf, name_rect)
                
                pos_surf = fonts.tiny.render(display_name, True, Colors.TEXT_SECONDARY)
                pos_rect = pos_surf.get_rect(center=(px, py + 12))
                self.screen.blit(pos_surf, pos_rect)
            else:
                # 空きスロット
                empty_surf = fonts.small.render(display_name, True, Colors.TEXT_MUTED)
                empty_rect = empty_surf.get_rect(center=(px, py))
                self.screen.blit(empty_surf, empty_rect)
        
        # DHスロット描画
        dh_x, dh_y = dh_position
        dh_rect = pygame.Rect(dh_x - 38, dh_y - 20, 76, 40)
        drop_zones["pos_DH"] = dh_rect
        
        # ドラッグ中のハイライト
        if dragging_player_idx >= 0 and dh_rect.collidepoint(drag_pos or (0, 0)):
            pygame.draw.rect(self.screen, (*Colors.PRIMARY[:3], 100), dh_rect, border_radius=6)
            pygame.draw.rect(self.screen, Colors.PRIMARY, dh_rect, 2, border_radius=6)
        else:
            pygame.draw.rect(self.screen, Colors.BG_CARD_HOVER, dh_rect, border_radius=6)
            pygame.draw.rect(self.screen, Colors.WARNING, dh_rect, 1, border_radius=6)  # DHは特別色
        
        # DHスロット内容
        if "DH" in position_assignments:
            dh_player_idx = position_assignments["DH"]
            dh_player = player_team.players[dh_player_idx]
            dh_name_surf = fonts.tiny.render(dh_player.name[:3], True, Colors.TEXT_PRIMARY)
            dh_name_rect = dh_name_surf.get_rect(center=(dh_x, dh_y - 3))
            self.screen.blit(dh_name_surf, dh_name_rect)
            
            dh_label = fonts.tiny.render("DH", True, Colors.WARNING)
            dh_label_rect = dh_label.get_rect(center=(dh_x, dh_y + 12))
            self.screen.blit(dh_label, dh_label_rect)
        else:
            dh_empty = fonts.small.render("DH", True, Colors.TEXT_MUTED)
            dh_empty_rect = dh_empty.get_rect(center=(dh_x, dh_y))
            self.screen.blit(dh_empty, dh_empty_rect)
        
        # ========================================
        # 中央パネル: 打順
        # ========================================
        order_card = Card(520, header_h + 20, 280, 480, "LINEUP")
        order_rect = order_card.draw(self.screen)
        
        # 編集モード切り替えボタン
        player_mode_style = "primary" if lineup_edit_mode == "player" else "ghost"
        pos_mode_style = "primary" if lineup_edit_mode == "position" else "ghost"
        
        mode_btn_y = order_rect.y + 45
        buttons["edit_mode_player"] = Button(order_rect.x + 10, mode_btn_y, 60, 24, "選手", player_mode_style, font=fonts.tiny)
        buttons["edit_mode_player"].draw(self.screen)
        buttons["edit_mode_position"] = Button(order_rect.x + 75, mode_btn_y, 60, 24, "守備", pos_mode_style, font=fonts.tiny)
        buttons["edit_mode_position"].draw(self.screen)
        
        # 最適化・シャッフルボタン
        buttons["optimize_lineup"] = Button(order_rect.x + 145, mode_btn_y, 50, 24, "最適", "secondary", font=fonts.tiny)
        buttons["optimize_lineup"].draw(self.screen)
        buttons["shuffle_lineup"] = Button(order_rect.x + 200, mode_btn_y, 50, 24, "🔀", "ghost", font=fonts.tiny)
        buttons["shuffle_lineup"].draw(self.screen)
        
        # ポジション重複チェック
        position_counts = {}
        position_conflicts = []
        if hasattr(player_team, 'position_assignments'):
            for pos_name, player_idx in player_team.position_assignments.items():
                if player_idx in lineup and pos_name != "DH":
                    # 外野は左中右をまとめてカウント
                    if pos_name in ["左翼手", "中堅手", "右翼手"]:
                        count_key = "外野手"
                    else:
                        count_key = pos_name
                    
                    if count_key not in position_counts:
                        position_counts[count_key] = []
                    position_counts[count_key].append(player_idx)
            
            # 重複を検出
            for pos_name, players in position_counts.items():
                if pos_name == "外野手" and len(players) > 3:
                    position_conflicts.append(f"外野手が{len(players)}人います")
                elif pos_name != "外野手" and len(players) > 1:
                    position_conflicts.append(f"{pos_name}が{len(players)}人います")
        
        # lineup_positionsを取得（独立したポジション管理）
        if hasattr(player_team, 'lineup_positions') and player_team.lineup_positions:
            lineup_positions = player_team.lineup_positions
        else:
            lineup_positions = ["捕", "一", "二", "三", "遊", "左", "中", "右", "DH"]
        while len(lineup_positions) < 9:
            lineup_positions.append("DH")
        
        y = order_rect.y + 78
        for i in range(9):
            # スロット全体の矩形（より広め）
            slot_rect = pygame.Rect(order_rect.x + 10, y, order_rect.width - 20, 40)
            drop_zones[f"order_{i}"] = slot_rect
            
            # ポジションスロット（独立してドラッグ可能）
            pos_slot_rect = pygame.Rect(order_rect.x + 10, y, 40, 38)
            drop_zones[f"position_slot_{i}"] = pos_slot_rect
            
            # ドラッグ中のハイライト（選手）
            is_player_drag_target = dragging_player_idx >= 0 and slot_rect.collidepoint(drag_pos or (0, 0))
            # ドラッグ中のハイライト（ポジション）
            is_pos_drag_target = dragging_position_slot >= 0 and pos_slot_rect.collidepoint(position_drag_pos or (0, 0))
            is_pos_dragging = dragging_position_slot == i

            # ★選択エフェクト判定
            is_batting_order_selected = lineup_edit_mode == "batting_order" and batting_order_selected_slot == i
            is_lineup_slot_selected = lineup_edit_mode == "player" and lineup_swap_mode and lineup_selected_source == "lineup" and lineup_selected_slot == i

            if is_batting_order_selected or is_lineup_slot_selected:
                draw_selection_effect(self.screen, slot_rect, color=Colors.PRIMARY, intensity=1.0)
            elif is_player_drag_target:
                pygame.draw.rect(self.screen, (*Colors.PRIMARY[:3], 100), slot_rect, border_radius=5)
                pygame.draw.rect(self.screen, Colors.PRIMARY, slot_rect, 2, border_radius=5)
            elif is_pos_drag_target:
                pygame.draw.rect(self.screen, (*Colors.WARNING[:3], 100), slot_rect, border_radius=5)
                pygame.draw.rect(self.screen, Colors.WARNING, slot_rect, 2, border_radius=5)
            else:
                pygame.draw.rect(self.screen, Colors.BG_INPUT, slot_rect, border_radius=5)
            
            # ポジションスロット（左側、独立）
            # ★選択エフェクト判定
            is_pos_slot_selected = lineup_edit_mode == "position" and position_selected_slot == i
            
            # 背景色の描画（選択時も含む）
            if is_pos_slot_selected:
                pos_bg_color = (*Colors.SUCCESS[:3], 100)  # 選択時は緑系の背景
            elif is_pos_dragging:
                pos_bg_color = (*Colors.WARNING[:3], 80)
            else:
                pos_bg_color = Colors.BG_CARD_HOVER
            pygame.draw.rect(self.screen, pos_bg_color, pos_slot_rect, border_radius=4)

            # ★選択エフェクト描画（選択時は固定の強調枠）
            if is_pos_slot_selected:
                draw_selection_effect(self.screen, pos_slot_rect, color=Colors.SUCCESS, intensity=0.8)
                pygame.draw.rect(self.screen, Colors.SUCCESS, pos_slot_rect, 2, border_radius=4)
            else:
                pygame.draw.rect(self.screen, Colors.WARNING if lineup_edit_mode == "position" else Colors.BORDER, pos_slot_rect, 1, border_radius=4)
            
            # ポジション表示
            pos_text = lineup_positions[i] if i < len(lineup_positions) else "DH"
            text_color = Colors.TEXT_PRIMARY if is_pos_slot_selected else Colors.WARNING
            pos_surf = fonts.small.render(pos_text, True, text_color)
            pos_text_rect = pos_surf.get_rect(center=(pos_slot_rect.centerx, pos_slot_rect.centery))
            self.screen.blit(pos_surf, pos_text_rect)
            
            # ポジションドラッグ用ボタン
            buttons[f"drag_position_{i}"] = Button(pos_slot_rect.x, pos_slot_rect.y, pos_slot_rect.width, pos_slot_rect.height, "", "ghost")
            
            # 打順番号
            num_surf = fonts.small.render(f"{i + 1}", True, Colors.PRIMARY)
            self.screen.blit(num_surf, (slot_rect.x + 48, slot_rect.y + 11))
            
            # 配置済み選手
            if i < len(lineup) and lineup[i] >= 0 and lineup[i] < len(player_team.players):
                player = player_team.players[lineup[i]]
                name_surf = fonts.tiny.render(player.name[:5], True, Colors.TEXT_PRIMARY)
                self.screen.blit(name_surf, (slot_rect.x + 68, slot_rect.y + 12))
                
                # 選手の本来のポジション（小さく表示）
                player_pos_short = player.position.value[:2]
                player_pos_surf = fonts.tiny.render(f"({player_pos_short})", True, Colors.TEXT_MUTED)
                self.screen.blit(player_pos_surf, (slot_rect.x + 130, slot_rect.y + 12))
                
                # 入れ替えボタン（上下）を各スロットに追加
                btn_x = slot_rect.right - 70
                if i > 0:
                    swap_up = Button(btn_x, slot_rect.y + 4, 22, 16, "↑", "ghost", font=fonts.tiny)
                    swap_up.draw(self.screen)
                    buttons[f"lineup_swap_up_{i}"] = swap_up
                if i < 8:
                    swap_down = Button(btn_x + 24, slot_rect.y + 4, 22, 16, "↓", "ghost", font=fonts.tiny)
                    swap_down.draw(self.screen)
                    buttons[f"lineup_swap_down_{i}"] = swap_down
                
                # ポジション入れ替えボタン
                if lineup_edit_mode == "position":
                    if i > 0:
                        pos_up = Button(slot_rect.x + 52, slot_rect.y + 22, 18, 14, "◀", "warning", font=fonts.tiny)
                        pos_up.draw(self.screen)
                        buttons[f"pos_swap_up_{i}"] = pos_up
                    if i < 8:
                        pos_down = Button(slot_rect.x + 72, slot_rect.y + 22, 18, 14, "▶", "warning", font=fonts.tiny)
                        pos_down.draw(self.screen)
                        buttons[f"pos_swap_down_{i}"] = pos_down
                
                # 削除ボタン（スロットから外す）
                remove_btn = Button(slot_rect.right - 22, slot_rect.y + 12, 18, 16, "×", "danger", font=fonts.tiny)
                remove_btn.draw(self.screen)
                buttons[f"lineup_remove_{i}"] = remove_btn
            else:
                # 空スロット
                empty_surf = fonts.tiny.render("- 空 -", True, Colors.TEXT_MUTED)
                self.screen.blit(empty_surf, (slot_rect.x + 50, slot_rect.y + 10))
            
            y += 42
        
        # ポジション重複警告表示
        if position_conflicts:
            warning_y = y + 2
            for conflict in position_conflicts[:2]:  # 最大2件表示
                warning_surf = fonts.tiny.render(f"! {conflict}", True, Colors.ERROR)
                self.screen.blit(warning_surf, (order_rect.x + 10, warning_y))
                warning_y += 16
        
        # プリセット保存/読込ボタン
        preset_y = order_rect.bottom - 35
        buttons["save_lineup_preset"] = Button(order_rect.x + 10, preset_y, 80, 28, "SAVE", "ghost", font=fonts.tiny)
        buttons["save_lineup_preset"].draw(self.screen)
        buttons["load_lineup_preset"] = Button(order_rect.x + 95, preset_y, 80, 28, "LOAD", "ghost", font=fonts.tiny)
        buttons["load_lineup_preset"].draw(self.screen)
        
        # ポジションドラッグ中の表示
        if dragging_position_slot >= 0 and position_drag_pos:
            pos_text = lineup_positions[dragging_position_slot] if dragging_position_slot < len(lineup_positions) else "?"
            drag_pos_surf = fonts.body.render(pos_text, True, Colors.WARNING)
            drag_rect = pygame.Rect(position_drag_pos[0] - 20, position_drag_pos[1] - 15, 40, 30)
            pygame.draw.rect(self.screen, Colors.BG_CARD, drag_rect, border_radius=6)
            pygame.draw.rect(self.screen, Colors.WARNING, drag_rect, 2, border_radius=6)
            self.screen.blit(drag_pos_surf, (position_drag_pos[0] - 10, position_drag_pos[1] - 10))
        
        # ========================================
        # 右パネル: 選手一覧（ドラッグ元）
        # ========================================
        roster_card = Card(820, header_h + 20, width - 850, height - header_h - 100, "ROSTER")
        roster_rect = roster_card.draw(self.screen)
        
        # タブ: 全員 / 野手 / 投手
        tab_y = roster_rect.y + 45
        all_style = "primary" if selected_position == "all" or selected_position is None else "ghost"
        batter_style = "primary" if selected_position == "batters" else "ghost"
        pitcher_style = "primary" if selected_position == "pitcher" else "ghost"
        
        buttons["tab_all"] = Button(roster_rect.x + 10, tab_y, 55, 28, "全員", all_style, font=fonts.tiny)
        buttons["tab_all"].draw(self.screen)
        
        buttons["tab_batters"] = Button(roster_rect.x + 70, tab_y, 55, 28, "野手", batter_style, font=fonts.tiny)
        buttons["tab_batters"].draw(self.screen)
        
        buttons["tab_pitchers"] = Button(roster_rect.x + 130, tab_y, 55, 28, "投手", pitcher_style, font=fonts.tiny)
        buttons["tab_pitchers"].draw(self.screen)
        
        # 選手リスト取得（タブに応じて）
        if selected_position == "pitcher":
            players = player_team.get_active_pitchers()
            count_text = f"{len(players)}人"
        elif selected_position == "batters":
            players = player_team.get_active_batters()
            count_text = f"{len(players)}人"
        else:
            # 全員表示
            players = [p for p in player_team.players if not getattr(p, 'is_developmental', False)]
            count_text = f"{len(players)}人"
        count_surf = fonts.tiny.render(count_text, True, Colors.TEXT_MUTED)
        self.screen.blit(count_surf, (roster_rect.x + 190, tab_y + 8))
        
        # 選手リスト（コンパクト表示）
        y = tab_y + 36
        row_height = 30  # コンパクト化
        visible_count = (roster_rect.height - 100) // row_height
        
        # ヘッダー
        header_surf = fonts.tiny.render("名前", True, Colors.TEXT_MUTED)
        self.screen.blit(header_surf, (roster_rect.x + 22, y))
        stat_header = fonts.tiny.render("能力", True, Colors.TEXT_MUTED)
        self.screen.blit(stat_header, (roster_rect.x + 100, y))
        y += 18
        
        for i in range(scroll_offset, min(len(players), scroll_offset + visible_count)):
            player = players[i]
            player_idx = player_team.players.index(player)
            
            row_rect = pygame.Rect(roster_rect.x + 8, y, roster_rect.width - 30, row_height - 2)
            
            # 選択済みマーキング
            is_in_lineup = player_idx in lineup
            
            is_player_selected = lineup_swap_mode and lineup_selected_player_idx == player_idx

            if is_player_selected:
                draw_selection_effect(self.screen, row_rect)
            elif dragging_player_idx == player_idx:
                # ドラッグ中は半透明
                pygame.draw.rect(self.screen, (*Colors.PRIMARY[:3], 30), row_rect, border_radius=4)
            elif is_in_lineup:
                pygame.draw.rect(self.screen, (*Colors.SUCCESS[:3], 40), row_rect, border_radius=4)
                pygame.draw.rect(self.screen, Colors.SUCCESS, row_rect, 1, border_radius=4)
            else:
                pygame.draw.rect(self.screen, Colors.BG_INPUT, row_rect, border_radius=4)
            
            # ドラッグ可能インジケータ（コンパクト）
            grip_x = row_rect.x + 5
            for dot_y in [row_rect.y + 8, row_rect.y + 14, row_rect.y + 20]:
                pygame.draw.circle(self.screen, Colors.TEXT_MUTED, (grip_x, dot_y), 1)
                pygame.draw.circle(self.screen, Colors.TEXT_MUTED, (grip_x + 4, dot_y), 1)
            
            # 選手情報（レイアウト調整して被り防止）
            name_surf = fonts.tiny.render(player.name[:4], True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_surf, (row_rect.x + 14, row_rect.y + 7))
            
            pos_surf = fonts.tiny.render(player.position.value[:2], True, Colors.TEXT_SECONDARY)
            self.screen.blit(pos_surf, (row_rect.x + 58, row_rect.y + 7))
            
            # 能力値プレビュー（位置調整）
            if player.position.value == "投手":
                stat_text = f"{player.stats.speed_to_kmh()}km 制{player.stats.control}"
            else:
                stat_text = f"ミ{player.stats.contact} パ{player.stats.power}"
            stat_preview = fonts.tiny.render(stat_text, True, Colors.TEXT_MUTED)
            self.screen.blit(stat_preview, (row_rect.x + 88, row_rect.y + 7))
            
            # 詳細ボタン（小さめ）
            detail_btn = Button(
                row_rect.right - 32, row_rect.y + 3, 28, row_height - 8,
                "詳", "outline", font=fonts.tiny
            )
            detail_btn.draw(self.screen)
            buttons[f"player_detail_{player_idx}"] = detail_btn
            
            # ドラッグ用ボタンとして登録（詳細ボタン以外の領域）
            buttons[f"drag_player_{player_idx}"] = Button(
                row_rect.x, row_rect.y, row_rect.width - 35, row_rect.height, "", "ghost"
            )
            
            y += row_height
        
        # スクロールバー表示
        if len(players) > visible_count:
            scroll_track_h = roster_rect.height - 120
            scroll_h = max(20, int(scroll_track_h * visible_count / len(players)))
            max_scroll = len(players) - visible_count
            scroll_y_pos = roster_rect.y + 100 + int((scroll_offset / max(1, max_scroll)) * (scroll_track_h - scroll_h))
            pygame.draw.rect(self.screen, Colors.BG_INPUT, 
                            (roster_rect.right - 10, roster_rect.y + 100, 5, scroll_track_h), border_radius=2)
            pygame.draw.rect(self.screen, Colors.PRIMARY, 
                            (roster_rect.right - 10, scroll_y_pos, 5, scroll_h), border_radius=2)
        
        # ドラッグ中の選手を描画
        if dragging_player_idx >= 0 and drag_pos and dragging_player_idx < len(player_team.players):
            player = player_team.players[dragging_player_idx]
            drag_surf = fonts.small.render(player.name[:6], True, Colors.PRIMARY)
            drag_rect = pygame.Rect(drag_pos[0] - 40, drag_pos[1] - 12, 80, 24)
            pygame.draw.rect(self.screen, Colors.BG_CARD, drag_rect, border_radius=4)
            pygame.draw.rect(self.screen, Colors.PRIMARY, drag_rect, 2, border_radius=4)
            self.screen.blit(drag_surf, (drag_pos[0] - 35, drag_pos[1] - 8))
        
        # ========================================
        # 先発投手選択
        # ========================================
        pitcher_card = Card(30, header_h + 470, 480, 90, "STARTER")
        pitcher_rect = pitcher_card.draw(self.screen)
        
        # 現在の先発投手
        if player_team.starting_pitcher_idx >= 0 and player_team.starting_pitcher_idx < len(player_team.players):
            pitcher = player_team.players[player_team.starting_pitcher_idx]
            pitcher_surf = fonts.body.render(pitcher.name, True, team_color)
            self.screen.blit(pitcher_surf, (pitcher_rect.x + 25, pitcher_rect.y + 50))
            
            stat_text = f"{pitcher.stats.speed_to_kmh()}km 制球{pitcher.stats.control}"
            stat_surf = fonts.tiny.render(stat_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(stat_surf, (pitcher_rect.x + 180, pitcher_rect.y + 55))
        else:
            empty_surf = fonts.small.render("投手タブから先発を選んでください", True, Colors.TEXT_MUTED)
            self.screen.blit(empty_surf, (pitcher_rect.x + 25, pitcher_rect.y + 50))
        
        # ドロップゾーンとして登録
        drop_zones["starting_pitcher"] = pitcher_rect
        
        # ========================================
        # 下部ボタン
        # ========================================
        # ヘルプテキスト（編集モードに応じて変更）
        if lineup_edit_mode == "position":
            help_text = "ポジション編集モード: 左のポジションをドラッグして入れ替え | ◀▶ボタンでも移動可能"
        else:
            help_text = "選手編集モード: 選手をドラッグして打順に配置 | ↑↓ボタンで順序入れ替え"
        help_surf = fonts.tiny.render(help_text, True, Colors.TEXT_MUTED)
        self.screen.blit(help_surf, (width // 2 - help_surf.get_width() // 2, height - 95))
        
        buttons["roster_management"] = Button(
            200, height - 65, 150, 45,
            "登録管理", "ghost", font=fonts.small
        )
        buttons["roster_management"].draw(self.screen)
        
        buttons["auto_lineup"] = Button(
            width - 340, height - 65, 130, 45,
            "AUTO", "secondary", font=fonts.small
        )
        buttons["auto_lineup"].draw(self.screen)
        
        buttons["clear_lineup"] = Button(
            width - 200, height - 65, 130, 45,
            "CLEAR", "ghost", font=fonts.small
        )
        buttons["clear_lineup"].draw(self.screen)
        
        buttons["to_pitcher_order"] = Button(
            360, height - 65, 150, 45,
            "投手設定", "warning", font=fonts.small
        )
        buttons["to_pitcher_order"].draw(self.screen)
        
        buttons["back"] = Button(
            50, height - 65, 130, 45,
            "← 戻る", "ghost", font=fonts.small
        )
        buttons["back"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        # ドロップゾーン情報を返す
        buttons["_drop_zones"] = drop_zones
        
        return buttons
    
    # ========================================
    # 試合進行画面（戦略オプション付き）
    # ========================================
    def draw_game_screen(self, player_team, opponent_team, game_state: dict = None,
                         strategy_mode: str = None, strategy_candidates: list = None) -> Dict[str, Button]:
        """試合進行画面を描画（戦略オプション付き）"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        center_x = width // 2
        
        buttons = {}
        
        if game_state is None:
            game_state = {}
        
        inning = game_state.get('inning', 1)
        is_top = game_state.get('is_top', True)
        outs = game_state.get('outs', 0)
        runners = game_state.get('runners', [False, False, False])
        home_score = game_state.get('home_score', 0)
        away_score = game_state.get('away_score', 0)
        current_batter = game_state.get('current_batter', None)
        current_pitcher = game_state.get('current_pitcher', None)
        pitch_count = game_state.get('pitch_count', 0)
        
        # ヘッダー部分
        team1_color = self.get_team_color(player_team.name) if player_team else Colors.PRIMARY
        team2_color = self.get_team_color(opponent_team.name) if opponent_team else Colors.DANGER
        
        # イニング表示
        inning_text = f"{inning}回{'表' if is_top else '裏'}"
        inning_surf = fonts.h2.render(inning_text, True, Colors.TEXT_PRIMARY)
        inning_rect = inning_surf.get_rect(center=(center_x, 40))
        self.screen.blit(inning_surf, inning_rect)
        
        # スコアボード
        score_y = 80
        # アウェイチーム
        away_name = opponent_team.name[:4] if is_top else player_team.name[:4]
        home_name = player_team.name[:4] if is_top else opponent_team.name[:4]
        
        away_surf = fonts.h3.render(away_name, True, team2_color if is_top else team1_color)
        self.screen.blit(away_surf, (center_x - 180, score_y))
        
        away_score_surf = fonts.h1.render(str(away_score), True, Colors.TEXT_PRIMARY)
        away_score_rect = away_score_surf.get_rect(center=(center_x - 50, score_y + 15))
        self.screen.blit(away_score_surf, away_score_rect)
        
        vs_surf = fonts.body.render("-", True, Colors.TEXT_MUTED)
        self.screen.blit(vs_surf, (center_x - 8, score_y + 5))
        
        home_score_surf = fonts.h1.render(str(home_score), True, Colors.TEXT_PRIMARY)
        home_score_rect = home_score_surf.get_rect(center=(center_x + 50, score_y + 15))
        self.screen.blit(home_score_surf, home_score_rect)
        
        home_surf = fonts.h3.render(home_name, True, team1_color if is_top else team2_color)
        self.screen.blit(home_surf, (center_x + 100, score_y))
        
        # アウトカウント表示
        out_y = 130
        out_text = f"アウト: {'●' * outs}{'○' * (3 - outs)}"
        out_surf = fonts.body.render(out_text, True, Colors.TEXT_SECONDARY)
        out_rect = out_surf.get_rect(center=(center_x, out_y))
        self.screen.blit(out_surf, out_rect)
        
        # ダイヤモンド（走塁図）
        diamond_y = 220
        diamond_size = 80
        
        # ベースの位置
        bases = [
            (center_x, diamond_y + diamond_size),      # ホーム
            (center_x + diamond_size, diamond_y),      # 1塁
            (center_x, diamond_y - diamond_size),      # 2塁
            (center_x - diamond_size, diamond_y),      # 3塁
        ]
        
        # ダイヤモンド線
        for i in range(4):
            pygame.draw.line(self.screen, Colors.BORDER, bases[i], bases[(i+1)%4], 2)
        
        # ベースと走者
        base_colors = [Colors.BG_CARD, Colors.BG_CARD, Colors.BG_CARD]
        for i, has_runner in enumerate(runners):
            if has_runner:
                base_colors[i] = Colors.WARNING
        
        # 1塁
        pygame.draw.rect(self.screen, base_colors[0], 
                        (bases[1][0] - 12, bases[1][1] - 12, 24, 24), border_radius=3)
        if runners[0]:
            pygame.draw.rect(self.screen, Colors.WARNING, 
                            (bases[1][0] - 12, bases[1][1] - 12, 24, 24), 2, border_radius=3)
        # 2塁
        pygame.draw.rect(self.screen, base_colors[1], 
                        (bases[2][0] - 12, bases[2][1] - 12, 24, 24), border_radius=3)
        if runners[1]:
            pygame.draw.rect(self.screen, Colors.WARNING, 
                            (bases[2][0] - 12, bases[2][1] - 12, 24, 24), 2, border_radius=3)
        # 3塁
        pygame.draw.rect(self.screen, base_colors[2], 
                        (bases[3][0] - 12, bases[3][1] - 12, 24, 24), border_radius=3)
        if runners[2]:
            pygame.draw.rect(self.screen, Colors.WARNING, 
                            (bases[3][0] - 12, bases[3][1] - 12, 24, 24), 2, border_radius=3)
        # ホーム
        pygame.draw.polygon(self.screen, Colors.BG_CARD, 
                          [(bases[0][0], bases[0][1] - 10),
                           (bases[0][0] + 10, bases[0][1]),
                           (bases[0][0] + 10, bases[0][1] + 8),
                           (bases[0][0] - 10, bases[0][1] + 8),
                           (bases[0][0] - 10, bases[0][1])])
        
        # 現在の打者・投手情報
        info_y = 320
        if current_batter:
            batter_text = f"打者: {current_batter.name} ({current_batter.position.value[:2]})"
            batter_surf = fonts.body.render(batter_text, True, Colors.TEXT_PRIMARY)
            self.screen.blit(batter_surf, (50, info_y))
            
            # 打者成績
            avg = current_batter.record.batting_average
            stats_text = f"打率.{int(avg*1000):03d} {current_batter.record.home_runs}本 {current_batter.record.rbis}点"
            stats_surf = fonts.small.render(stats_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(stats_surf, (50, info_y + 25))
        
        if current_pitcher:
            pitcher_text = f"投手: {current_pitcher.name}"
            pitcher_surf = fonts.body.render(pitcher_text, True, Colors.TEXT_PRIMARY)
            self.screen.blit(pitcher_surf, (width - 280, info_y))
            
            # 投手成績
            era = current_pitcher.record.era
            p_stats = f"防{era:.2f} {pitch_count}球"
            p_stats_surf = fonts.small.render(p_stats, True, Colors.TEXT_SECONDARY)
            self.screen.blit(p_stats_surf, (width - 280, info_y + 25))
        
        # ========================================
        # 戦略パネル
        # ========================================
        strategy_panel_y = 400
        strategy_card = Card(30, strategy_panel_y, width - 60, 200, "作戦")
        strategy_rect = strategy_card.draw(self.screen)
        
        # 戦略ボタン群
        btn_y = strategy_rect.y + 50
        btn_h = 45
        btn_gap = 10
        
        # 攻撃時の戦略
        if is_top == (player_team == opponent_team):  # プレイヤーチームが攻撃中
            # 打撃戦略
            attack_x = strategy_rect.x + 20
            
            buttons["strategy_bunt"] = Button(attack_x, btn_y, 100, btn_h, "バント", "secondary", font=fonts.small)
            buttons["strategy_bunt"].draw(self.screen)
            
            buttons["strategy_squeeze"] = Button(attack_x + 110, btn_y, 110, btn_h, "スクイズ", "secondary", font=fonts.small)
            buttons["strategy_squeeze"].draw(self.screen)
            
            buttons["strategy_steal"] = Button(attack_x + 230, btn_y, 90, btn_h, "盗塁", "secondary", font=fonts.small)
            buttons["strategy_steal"].draw(self.screen)
            
            buttons["strategy_hit_run"] = Button(attack_x + 330, btn_y, 120, btn_h, "エンドラン", "secondary", font=fonts.small)
            buttons["strategy_hit_run"].draw(self.screen)
            
            # 選手交代
            btn_y2 = btn_y + btn_h + btn_gap
            buttons["strategy_pinch_hit"] = Button(attack_x, btn_y2, 100, btn_h, "代打", "warning", font=fonts.small)
            buttons["strategy_pinch_hit"].draw(self.screen)
            
            buttons["strategy_pinch_run"] = Button(attack_x + 110, btn_y2, 100, btn_h, "代走", "warning", font=fonts.small)
            buttons["strategy_pinch_run"].draw(self.screen)
        
        else:  # プレイヤーチームが守備中
            # 守備戦略
            defense_x = strategy_rect.x + 20
            
            buttons["strategy_intentional_walk"] = Button(defense_x, btn_y, 110, btn_h, "敬遠", "secondary", font=fonts.small)
            buttons["strategy_intentional_walk"].draw(self.screen)
            
            buttons["strategy_pitch_out"] = Button(defense_x + 120, btn_y, 120, btn_h, "ピッチアウト", "secondary", font=fonts.small)
            buttons["strategy_pitch_out"].draw(self.screen)
            
            buttons["strategy_infield_in"] = Button(defense_x + 250, btn_y, 130, btn_h, "前進守備", "secondary", font=fonts.small)
            buttons["strategy_infield_in"].draw(self.screen)
            
            # 投手交代
            btn_y2 = btn_y + btn_h + btn_gap
            buttons["strategy_pitching_change"] = Button(defense_x, btn_y2, 120, btn_h, "継投", "warning", font=fonts.small)
            buttons["strategy_pitching_change"].draw(self.screen)
            
            buttons["strategy_mound_visit"] = Button(defense_x + 130, btn_y2, 130, btn_h, "マウンド訪問", "ghost", font=fonts.small)
            buttons["strategy_mound_visit"].draw(self.screen)
        
        # クイック再生/一時停止
        control_x = strategy_rect.right - 200
        buttons["game_auto_play"] = Button(control_x, btn_y, 80, btn_h, "自動", "primary", font=fonts.small)
        buttons["game_auto_play"].draw(self.screen)
        
        buttons["game_next_play"] = Button(control_x + 90, btn_y, 80, btn_h, "次へ", "outline", font=fonts.small)
        buttons["game_next_play"].draw(self.screen)
        
        # 速度調整
        btn_y2 = btn_y + btn_h + btn_gap
        speed_label = fonts.tiny.render("速度:", True, Colors.TEXT_MUTED)
        self.screen.blit(speed_label, (control_x, btn_y2 + 12))
        
        buttons["speed_slow"] = Button(control_x + 40, btn_y2, 40, 35, "1x", "ghost", font=fonts.tiny)
        buttons["speed_slow"].draw(self.screen)
        buttons["speed_normal"] = Button(control_x + 85, btn_y2, 40, 35, "2x", "ghost", font=fonts.tiny)
        buttons["speed_normal"].draw(self.screen)
        buttons["speed_fast"] = Button(control_x + 130, btn_y2, 40, 35, "5x", "ghost", font=fonts.tiny)
        buttons["speed_fast"].draw(self.screen)
        
        # ========================================
        # 戦略選択ダイアログ（候補者選択）
        # ========================================
        if strategy_mode and strategy_candidates:
            # オーバーレイ
            overlay = pygame.Surface((width, height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))
            
            # ダイアログ
            dialog_w, dialog_h = 500, 400
            dialog_x = center_x - dialog_w // 2
            dialog_y = height // 2 - dialog_h // 2
            
            pygame.draw.rect(self.screen, Colors.BG_CARD, 
                           (dialog_x, dialog_y, dialog_w, dialog_h), border_radius=16)
            pygame.draw.rect(self.screen, Colors.PRIMARY, 
                           (dialog_x, dialog_y, dialog_w, dialog_h), 2, border_radius=16)
            
            # タイトル
            mode_titles = {
                "pinch_hit": "代打選手を選択",
                "pinch_run": "代走選手を選択",
                "pitching_change": "交代投手を選択",
            }
            title_text = mode_titles.get(strategy_mode, "選手を選択")
            title_surf = fonts.h3.render(title_text, True, Colors.TEXT_PRIMARY)
            title_rect = title_surf.get_rect(center=(center_x, dialog_y + 35))
            self.screen.blit(title_surf, title_rect)
            
            # 候補リスト
            list_y = dialog_y + 70
            for i, player in enumerate(strategy_candidates[:8]):  # 最大8人表示
                row_rect = pygame.Rect(dialog_x + 20, list_y, dialog_w - 40, 35)
                
                # ホバー効果用ボタン
                btn = Button(row_rect.x, row_rect.y, row_rect.width, row_rect.height, "", "ghost")
                btn.draw(self.screen)
                buttons[f"select_candidate_{i}"] = btn
                
                pygame.draw.rect(self.screen, Colors.BG_INPUT, row_rect, border_radius=6)
                
                # 選手名
                name_surf = fonts.body.render(player.name, True, Colors.TEXT_PRIMARY)
                self.screen.blit(name_surf, (row_rect.x + 10, row_rect.y + 8))
                
                # ポジション
                pos_surf = fonts.small.render(player.position.value[:3], True, Colors.TEXT_SECONDARY)
                self.screen.blit(pos_surf, (row_rect.x + 150, row_rect.y + 10))
                
                # 能力値
                if strategy_mode == "pitching_change":
                    stat_text = f"{player.stats.speed_to_kmh()}km 制{player.stats.control}"
                else:
                    stat_text = f"ミ{player.stats.contact} パ{player.stats.power}"
                stat_surf = fonts.small.render(stat_text, True, Colors.TEXT_MUTED)
                self.screen.blit(stat_surf, (row_rect.x + 250, row_rect.y + 10))
                
                list_y += 38
            
            # キャンセルボタン
            buttons["cancel_strategy"] = Button(center_x - 60, dialog_y + dialog_h - 55, 120, 40, "キャンセル", "ghost", font=fonts.body)
            buttons["cancel_strategy"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    # ========================================
    # 試合方法選択画面
    # ========================================
    def draw_game_choice_screen(self, player_team, opponent_team) -> Dict[str, Button]:
        """試合方法選択画面を描画"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        center_x = width // 2
        center_y = height // 2
        
        buttons = {}
        
        # ヘッダー
        header_h = draw_header(self.screen, "PLAY BALL", "試合の進め方を選んでください")
        
        # チーム対戦カード
        team1_color = self.get_team_color(player_team.name) if player_team else Colors.PRIMARY
        team2_color = self.get_team_color(opponent_team.name) if opponent_team else Colors.DANGER
        
        matchup_y = header_h + 40
        
        # プレイヤーチーム
        team1_surf = fonts.h2.render(player_team.name if player_team else "---", True, team1_color)
        team1_rect = team1_surf.get_rect(center=(center_x - 120, matchup_y))
        self.screen.blit(team1_surf, team1_rect)
        
        # VS
        vs_surf = fonts.h3.render("VS", True, Colors.TEXT_MUTED)
        vs_rect = vs_surf.get_rect(center=(center_x, matchup_y))
        self.screen.blit(vs_surf, vs_rect)
        
        # 対戦相手
        team2_surf = fonts.h2.render(opponent_team.name if opponent_team else "---", True, team2_color)
        team2_rect = team2_surf.get_rect(center=(center_x + 120, matchup_y))
        self.screen.blit(team2_surf, team2_rect)
        
        # 選択ボタン（3列に変更）
        button_y = center_y - 30
        card_width = 250
        card_spacing = 20
        total_width = card_width * 3 + card_spacing * 2
        start_x = center_x - total_width // 2
        
        # 采配モードボタン（新規追加）
        manage_card = Card(start_x, button_y, card_width, 200, "采配モード")
        manage_rect = manage_card.draw(self.screen)
        
        manage_desc1 = fonts.body.render("自分で采配を振る", True, Colors.TEXT_PRIMARY)
        manage_desc2 = fonts.small.render("継投・代打・バントなど", True, Colors.TEXT_SECONDARY)
        manage_desc3 = fonts.small.render("戦術を自由に指示", True, Colors.TEXT_SECONDARY)
        
        self.screen.blit(manage_desc1, (manage_rect.x + 25, manage_rect.y + 60))
        self.screen.blit(manage_desc2, (manage_rect.x + 25, manage_rect.y + 95))
        self.screen.blit(manage_desc3, (manage_rect.x + 25, manage_rect.y + 120))
        
        manage_btn = Button(manage_rect.x + 50, manage_rect.y + 145, 150, 40, "采配する", "warning", font=fonts.body)
        manage_btn.draw(self.screen)
        buttons["manage_game"] = manage_btn
        
        # 観戦ボタン
        watch_card = Card(start_x + card_width + card_spacing, button_y, card_width, 200, "試合を観戦")
        watch_rect = watch_card.draw(self.screen)
        
        watch_desc1 = fonts.body.render("一球速報風に観戦", True, Colors.TEXT_PRIMARY)
        watch_desc2 = fonts.small.render("投球ごとに結果を確認", True, Colors.TEXT_SECONDARY)
        watch_desc3 = fonts.small.render("試合を楽しめます", True, Colors.TEXT_SECONDARY)
        
        self.screen.blit(watch_desc1, (watch_rect.x + 25, watch_rect.y + 60))
        self.screen.blit(watch_desc2, (watch_rect.x + 25, watch_rect.y + 95))
        self.screen.blit(watch_desc3, (watch_rect.x + 25, watch_rect.y + 120))
        
        watch_btn = Button(watch_rect.x + 50, watch_rect.y + 145, 150, 40, "観戦する", "primary", font=fonts.body)
        watch_btn.draw(self.screen)
        buttons["watch_game"] = watch_btn
        
        # スキップボタン
        skip_card = Card(start_x + (card_width + card_spacing) * 2, button_y, card_width, 200, "結果までスキップ")
        skip_rect = skip_card.draw(self.screen)
        
        skip_desc1 = fonts.body.render("試合をシミュレート", True, Colors.TEXT_PRIMARY)
        skip_desc2 = fonts.small.render("すぐに結果画面へ進む", True, Colors.TEXT_SECONDARY)
        skip_desc3 = fonts.small.render("時間を節約したい場合に", True, Colors.TEXT_SECONDARY)
        
        self.screen.blit(skip_desc1, (skip_rect.x + 25, skip_rect.y + 60))
        self.screen.blit(skip_desc2, (skip_rect.x + 25, skip_rect.y + 95))
        self.screen.blit(skip_desc3, (skip_rect.x + 25, skip_rect.y + 120))
        
        skip_btn = Button(skip_rect.x + 50, skip_rect.y + 145, 150, 40, "スキップ", "ghost", font=fonts.body)
        skip_btn.draw(self.screen)
        buttons["skip_to_result"] = skip_btn
        
        # 戻るボタン
        back_btn = Button(50, height - 70, 150, 50, "← 戻る", "ghost", font=fonts.body)
        back_btn.draw(self.screen)
        buttons["back_from_game_choice"] = back_btn
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    # ========================================
    # 采配モード画面（野球場デザイン）
    # ========================================
    def draw_game_manage_screen(self, player_team, opponent_team, game_state: dict) -> Dict[str, Button]:
        """采配モード画面を描画（サイバーパンク風3D野球場）"""
        width = self.screen.get_width()
        height = self.screen.get_height()
        center_x = width // 2
        
        buttons = {}
        
        if game_state is None:
            game_state = {}
        
        inning = game_state.get('inning', 1)
        is_top = game_state.get('is_top', True)
        outs = game_state.get('outs', 0)
        strikes = game_state.get('strikes', 0)
        balls = game_state.get('balls', 0)
        runners = game_state.get('runners', [None, None, None])
        home_score = game_state.get('home_score', 0)
        away_score = game_state.get('away_score', 0)
        current_batter = game_state.get('current_batter')
        current_pitcher = game_state.get('current_pitcher')
        current_play = game_state.get('current_play', "")
        play_log = game_state.get('play_log', [])
        game_finished = game_state.get('game_finished', False)
        pitch_count = game_state.get('pitch_count', 0)
        waiting_for_tactic = game_state.get('waiting_for_tactic', False)
        player_is_batting = game_state.get('player_is_batting', False)
        player_is_pitching = game_state.get('player_is_pitching', False)
        is_home = game_state.get('is_home', True)
        ball_tracking = game_state.get('ball_tracking', None)
        trajectory = game_state.get('trajectory', [])
        animation_frame = game_state.get('animation_frame', 0)
        
        # チームカラー
        team1_color = self.get_team_color(player_team.name) if player_team else Colors.PRIMARY
        team2_color = self.get_team_color(opponent_team.name) if opponent_team else Colors.DANGER
        
        # ランナー情報を変換
        runners_bool = [r is not None for r in runners]
        
        # アニメーション状態
        animation_active = game_state.get('animation_active', False)
        waiting_for_animation = game_state.get('waiting_for_animation', False)
        pitch_history = game_state.get('pitch_history', [])
        
        # アニメーション中はランナーを非表示（進塁前の状態）
        display_runners = [False, False, False] if (animation_active or waiting_for_animation) else runners_bool
        
        # 打球追跡時のボール位置を更新
        if trajectory and ball_tracking and animation_frame < len(trajectory):
            frame_data = trajectory[animation_frame]
            if isinstance(frame_data, dict):
                self.cyber_field.ball_position = [
                    frame_data.get('x', 0),
                    frame_data.get('z', 0),  # 高さ
                    frame_data.get('y', 0)   # 奥行き
                ]
            else:
                self.cyber_field.ball_position = [frame_data[0], frame_data[2], frame_data[1]]
            self.cyber_field.is_ball_flying = True
        else:
            self.cyber_field.is_ball_flying = False
        
        # ========== 球場設定（パークファクターに基づく） ==========
        # ホームチームの球場を使用
        home_team = player_team if is_home else opponent_team
        if home_team:
            stadium_info = NPB_STADIUMS.get(home_team.name, {})
            park_factor = stadium_info.get('home_run_factor', 1.0)
            stadium_name = stadium_info.get('name', '')
            self.cyber_field.set_stadium(park_factor, stadium_name)
            # ゲーム状態にもパークファクターを反映（HR判定に使用）
            game_state['park_factor'] = park_factor
        
        # 守備チームの能力を設定
        fielding_team = opponent_team if player_is_batting else player_team
        self.cyber_field.set_fielder_abilities(fielding_team)
        
        # ========== サイバー3Dフィールド描画 ==========
        self.cyber_field.width = width
        self.cyber_field.height = height
        self.cyber_field.vanishing_point_x = width / 2
        self.cyber_field.vanishing_point_y = height * 0.15  # 消失点を少し下げる
        
        # カメラ設定（後方からの視点）
        self.cyber_field.camera_height = 20.0  # 高めにして視点を上げる
        self.cyber_field.camera_dist = -25.0  # 後ろに下がる
        self.cyber_field.camera_angle = 8.0  # 緩やかな俯瞰
        self.cyber_field.fov = CyberField3D.DEFAULT_FOV + 100  # 広角
        self.cyber_field.camera_offset_x = 0
        
        self.cyber_field.draw_background()
        self.cyber_field.draw_grid()
        self.cyber_field.draw_foul_lines()
        self.cyber_field.draw_fence()
        self.cyber_field.draw_bases(display_runners)
        
        # 打球トラッキング中は動的野手を表示
        if trajectory and ball_tracking:
            # アニメーションフレームまでの軌跡のみ表示
            display_trajectory = trajectory[:animation_frame + 1] if animation_frame < len(trajectory) else trajectory
            # 守備は表示しない（物理計算で結果決定済み）
            self.cyber_field.draw_ball_trajectory(display_trajectory)
            self.cyber_field.draw_ball_with_shadow()
            # ミニマップを左下に表示（パネルと被らないように上に配置）
            self.cyber_field.draw_minimap(10, height - 260, 130)
        # 守備配置は表示しない
        
        # ========== モードインジケーター（左上） ==========
        if player_is_batting:
            mode_text = "BATTING"
            mode_bg = (80, 60, 0)
            mode_border = (255, 200, 60)
        elif player_is_pitching:
            mode_text = "PITCHING"
            mode_bg = (0, 40, 80)
            mode_border = (100, 180, 255)
        else:
            mode_text = "OPPONENT"
            mode_bg = (40, 40, 50)
            mode_border = (100, 100, 120)
        
        mode_panel = pygame.Surface((110, 30), pygame.SRCALPHA)
        mode_panel.fill((*mode_bg, 230))
        self.screen.blit(mode_panel, (10, 10))
        pygame.draw.rect(self.screen, mode_border, (10, 10, 110, 30), 2, border_radius=6)
        mode_surf = fonts.small.render(mode_text, True, mode_border)
        self.screen.blit(mode_surf, (15 + (100 - mode_surf.get_width()) // 2, 15))
        
        # ========== スコアボード（中央上・洗練されたデザイン） ==========
        score_x = center_x - 120
        score_y = 8
        score_w = 240
        score_h = 75
        
        # グラデーション風の背景
        score_bg = pygame.Surface((score_w, score_h), pygame.SRCALPHA)
        for i in range(score_h):
            alpha = 230 - i // 3
            score_bg.fill((0, 20 + i // 5, 45 + i // 4, alpha), (0, i, score_w, 1))
        self.screen.blit(score_bg, (score_x, score_y))
        
        # メタリックな枠線
        pygame.draw.rect(self.screen, (80, 150, 200), (score_x, score_y, score_w, score_h), 2, border_radius=8)
        pygame.draw.rect(self.screen, (40, 80, 120, 100), (score_x + 2, score_y + 2, score_w - 4, score_h - 4), 1, border_radius=6)
        
        # イニング（トップバナー風）
        inning_bg = pygame.Surface((score_w - 16, 20), pygame.SRCALPHA)
        if game_finished:
            inning_bg.fill((200, 50, 80, 180))
            inning_text = "FINAL"
            inning_color = (255, 220, 220)
        else:
            inning_bg.fill((50, 100, 150, 150))
            inning_text = f"{inning}回{'表' if is_top else '裏'}"
            inning_color = (180, 220, 255)
        self.screen.blit(inning_bg, (score_x + 8, score_y + 4))
        inning_surf = fonts.small.render(inning_text, True, inning_color)
        self.screen.blit(inning_surf, (score_x + (score_w - inning_surf.get_width()) // 2, score_y + 5))
        
        # チーム名とスコア
        away_team = opponent_team if is_home else player_team
        home_team = player_team if is_home else opponent_team
        away_color = team2_color if is_home else team1_color
        home_color = team1_color if is_home else team2_color
        
        # アウェイチーム
        team_y = score_y + 28
        pygame.draw.rect(self.screen, away_color, (score_x + 12, team_y, 5, 16), border_radius=2)
        away_name = away_team.name[:6] if away_team else "AWAY"
        away_surf = fonts.small.render(away_name, True, Colors.TEXT_PRIMARY)
        self.screen.blit(away_surf, (score_x + 22, team_y))
        # スコア表示（大きめ・ハイライト）
        away_score_bg = pygame.Surface((40, 20), pygame.SRCALPHA)
        away_score_bg.fill((0, 50, 80, 150) if not is_top else (80, 150, 200, 100))
        self.screen.blit(away_score_bg, (score_x + 170, team_y - 2))
        away_score_surf = fonts.h3.render(str(away_score), True, (255, 255, 255))
        self.screen.blit(away_score_surf, (score_x + 180, team_y - 2))
        
        # ホームチーム
        home_y_pos = team_y + 22
        pygame.draw.rect(self.screen, home_color, (score_x + 12, home_y_pos, 5, 16), border_radius=2)
        home_name = home_team.name[:6] if home_team else "HOME"
        home_surf = fonts.small.render(home_name, True, Colors.TEXT_PRIMARY)
        self.screen.blit(home_surf, (score_x + 22, home_y_pos))
        # スコア表示
        home_score_bg = pygame.Surface((40, 20), pygame.SRCALPHA)
        home_score_bg.fill((80, 150, 200, 100) if not is_top else (0, 50, 80, 150))
        self.screen.blit(home_score_bg, (score_x + 170, home_y_pos - 2))
        home_score_surf = fonts.h3.render(str(home_score), True, (255, 255, 255))
        self.screen.blit(home_score_surf, (score_x + 180, home_y_pos - 2))
        
        # 攻撃マーカー（アニメーション風）
        marker_pulse = 0.7 + 0.3 * math.sin(pygame.time.get_ticks() / 300)
        marker_color = tuple(int(c * marker_pulse) for c in (100, 255, 200))
        if is_top:
            pygame.draw.polygon(self.screen, marker_color, [
                (score_x + 5, team_y + 8), (score_x + 10, team_y + 4), (score_x + 10, team_y + 12)])
        else:
            pygame.draw.polygon(self.screen, marker_color, [
                (score_x + 5, home_y_pos + 8), (score_x + 10, home_y_pos + 4), (score_x + 10, home_y_pos + 12)])
        
        # ========== BSO（右上・洗練されたデザイン） ==========
        bso_x = width - 100
        bso_y = 8
        bso_w = 90
        bso_h = 70
        
        # グラデーション背景
        bso_bg = pygame.Surface((bso_w, bso_h), pygame.SRCALPHA)
        for i in range(bso_h):
            alpha = 220 - i // 3
            bso_bg.fill((15 + i // 5, 25 + i // 4, 45 + i // 3, alpha), (0, i, bso_w, 1))
        self.screen.blit(bso_bg, (bso_x, bso_y))
        pygame.draw.rect(self.screen, (80, 150, 200), (bso_x, bso_y, bso_w, bso_h), 2, border_radius=8)
        
        bso_data = [
            ("B", balls, 4, (76, 200, 100), (30, 60, 40)),
            ("S", strikes, 3, (255, 210, 80), (60, 50, 30)),
            ("O", outs, 3, (255, 90, 90), (60, 30, 30))
        ]
        for i, (label, count, max_c, active_color, inactive_color) in enumerate(bso_data):
            by = bso_y + 10 + i * 20
            # ラベル
            label_surf = fonts.small.render(label, True, (150, 180, 200))
            self.screen.blit(label_surf, (bso_x + 8, by))
            # ドット（グロー効果付き）
            for j in range(max_c):
                cx = bso_x + 32 + j * 16
                cy = by + 8
                if j < count:
                    # アクティブ：グロー効果
                    glow_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
                    pygame.draw.circle(glow_surf, (*active_color[:3], 100), (8, 8), 7)
                    self.screen.blit(glow_surf, (cx - 8, cy - 8))
                    pygame.draw.circle(self.screen, active_color, (cx, cy), 5)
                    pygame.draw.circle(self.screen, (255, 255, 255, 180), (cx - 1, cy - 1), 2)
                else:
                    pygame.draw.circle(self.screen, inactive_color, (cx, cy), 5)
                    pygame.draw.circle(self.screen, (60, 70, 90), (cx, cy), 5, 1)
        
        # ========== 試合スキップボタン（右上BSOの左） ==========
        if not game_finished:
            skip_btn_x = bso_x - 85
            skip_btn_y = bso_y + 25
            skip_btn = Button(skip_btn_x, skip_btn_y, 80, 26, "試合Skip", "warning", font=fonts.tiny)
            skip_btn.draw(self.screen)
            buttons["skip_manage_game"] = skip_btn
        
        # ========== ストライクゾーンパネル（左側に配置） ==========
        last_pitch = game_state.get('last_pitch_data', None)
        self.cyber_field.draw_strike_zone_panel(pitch_history, 10, 120, last_pitch)
        
        # ========== 打球トラッキングデータ（右側・打球時のみ） ==========
        if ball_tracking and not ball_tracking.get('is_foul', False):
            self.cyber_field.draw_tracking_data_panel(ball_tracking, width - 195, 120)
        
        # ========== プレイ結果（画面上部に表示） ==========
        if current_play or game_finished:
            result_text = "GAME SET !!" if game_finished else current_play
            if "三振" in result_text or "アウト" in result_text:
                result_color = (150, 150, 180)
            elif "ヒット" in result_text or "二塁打" in result_text or "三塁打" in result_text:
                result_color = (0, 255, 150)
            elif "ホームラン" in result_text:
                result_color = CyberField3D.COLOR_FENCE
            elif "四球" in result_text:
                result_color = (100, 200, 255)
            elif game_finished:
                result_color = CyberField3D.COLOR_FENCE
            else:
                result_color = CyberField3D.COLOR_TEXT
            
            # 画面上部に結果バーを表示（スコアボードの下）
            result_bar_y = 88
            result_bar_h = 40
            result_bar_w = 400  # 短いバー
            result_bar_x = center_x - result_bar_w // 2
            
            # 背景バー
            result_bar = pygame.Surface((result_bar_w, result_bar_h), pygame.SRCALPHA)
            result_bar.fill((0, 0, 0, 180))
            self.screen.blit(result_bar, (result_bar_x, result_bar_y))
            
            # 上下のアクセントライン
            pygame.draw.line(self.screen, result_color, (result_bar_x, result_bar_y), (result_bar_x + result_bar_w, result_bar_y), 2)
            pygame.draw.line(self.screen, (result_color[0]//2, result_color[1]//2, result_color[2]//2), 
                            (result_bar_x, result_bar_y + result_bar_h), (result_bar_x + result_bar_w, result_bar_y + result_bar_h), 1)
            
            # グロー効果付きテキスト
            glow_color = (result_color[0]//3, result_color[1]//3, result_color[2]//3)
            result_surf = fonts.h3.render(result_text, True, result_color)
            glow_surf = fonts.h3.render(result_text, True, glow_color)
            
            text_x = center_x - result_surf.get_width() // 2
            text_y = result_bar_y + (result_bar_h - result_surf.get_height()) // 2
            
            # グロー
            for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                self.screen.blit(glow_surf, (text_x + ox, text_y + oy))
            
            # メインテキスト
            shadow_surf = fonts.h3.render(result_text, True, (0, 0, 0))
            self.screen.blit(shadow_surf, (text_x + 2, text_y + 2))
            self.screen.blit(result_surf, (text_x, text_y))
        
        # ========== 下部パネル（左：打者＋戦術、右：投手＋戦術） ==========
        panel_h = 120
        panel_y = height - panel_h
        
        # 能力値からランクに変換する関数
        def _to_rank(val):
            if val >= 90: return "S"
            elif val >= 80: return "A"
            elif val >= 70: return "B"
            elif val >= 60: return "C"
            elif val >= 50: return "D"
            elif val >= 40: return "E"
            else: return "F"
        
        def _rank_color(rank):
            colors = {"S": (255, 215, 0), "A": (255, 100, 100), "B": (255, 150, 80),
                      "C": (100, 200, 255), "D": (150, 180, 200), "E": (120, 120, 140), "F": (100, 100, 100)}
            return colors.get(rank, (180, 180, 180))
        
        # ========== 左側：打者パネル ==========
        batter_panel_w = 220
        # 半透明背景
        batter_bg = pygame.Surface((batter_panel_w, panel_h), pygame.SRCALPHA)
        batter_bg.fill((15, 25, 45, 200))
        self.screen.blit(batter_bg, (0, panel_y))
        pygame.draw.rect(self.screen, (80, 180, 255), (0, panel_y, 3, panel_h))
        
        # 打者ヘッダー
        batter_label = fonts.tiny.render("BATTER", True, (100, 180, 255))
        self.screen.blit(batter_label, (10, panel_y + 4))
        
        if current_batter:
            batter_name = f"#{current_batter.uniform_number} {current_batter.name}"
            batter_surf = fonts.small.render(batter_name, True, Colors.TEXT_PRIMARY)
            self.screen.blit(batter_surf, (10, panel_y + 18))
            
            # 能力ランク表示（ミート・パワー・走力のみ）
            stats = current_batter.stats
            contact = getattr(stats, 'contact', 50)
            power = getattr(stats, 'power', 50)
            speed = getattr(stats, 'speed', 50)
            
            rank_y = panel_y + 38
            rank_items = [("ミート", contact), ("パワー", power), ("走力", speed)]
            for i, (label, val) in enumerate(rank_items):
                sx = 10 + i * 70
                lbl_surf = fonts.tiny.render(label, True, (120, 140, 160))
                self.screen.blit(lbl_surf, (sx, rank_y))
                rank = _to_rank(val)
                rank_surf = fonts.small.render(rank, True, _rank_color(rank))
                self.screen.blit(rank_surf, (sx + 36, rank_y - 2))
        
        # 打撃戦術ボタン（左下）
        if player_is_batting and not game_finished:
            btn_w = 52
            btn_h = 22
            selected_tactic = game_state.get('selected_tactic', 'normal')
            tactics = [
                ("通常", "normal"), ("強振", "power_swing"),
                ("ミート", "contact_swing"), ("待て", "take"),
            ]
            tactic_y = panel_y + 58
            for i, (label, tactic_id) in enumerate(tactics):
                bx = 8 + i * (btn_w + 2)
                # 選択中の戦術はハイライト
                if selected_tactic == tactic_id:
                    style = "primary"
                else:
                    style = "ghost"
                btn = Button(bx, tactic_y, btn_w, btn_h, label, style, font=fonts.tiny)
                btn.draw(self.screen)
                buttons[f"tactic_{tactic_id}"] = btn
            
            # 特殊戦術（バント・盗塁など）
            special_y = panel_y + 82
            special_tactics = [
                ("バント", "bunt"), ("盗塁", "steal"),
            ]
            for i, (label, tactic_id) in enumerate(special_tactics):
                bx = 8 + i * (btn_w + 2)
                # 選択中の戦術はハイライト
                if selected_tactic == tactic_id:
                    style = "primary"
                else:
                    style = "ghost"
                btn = Button(bx, special_y, btn_w, btn_h, label, style, font=fonts.tiny)
                btn.draw(self.screen)
                buttons[f"tactic_{tactic_id}"] = btn
            
            # 代打・代走ボタン（選択方式ではない）
            sub_btn_x = 8 + 2 * (btn_w + 2)
            pinch_hit_btn = Button(sub_btn_x, special_y, btn_w, btn_h, "代打", "warning", font=fonts.tiny)
            pinch_hit_btn.draw(self.screen)
            buttons["substitution_pinch_hit"] = pinch_hit_btn
            
            pinch_run_btn = Button(sub_btn_x + btn_w + 2, special_y, btn_w, btn_h, "代走", "warning", font=fonts.tiny)
            pinch_run_btn.draw(self.screen)
            if any(runners_bool):
                buttons["substitution_pinch_run"] = pinch_run_btn
        
        # ========== 右側：投手パネル ==========
        pitcher_panel_w = 220
        pitcher_panel_x = width - pitcher_panel_w
        # 半透明背景
        pitcher_bg = pygame.Surface((pitcher_panel_w, panel_h), pygame.SRCALPHA)
        pitcher_bg.fill((45, 20, 35, 200))
        self.screen.blit(pitcher_bg, (pitcher_panel_x, panel_y))
        pygame.draw.rect(self.screen, (255, 100, 150), (width - 3, panel_y, 3, panel_h))
        
        # 投手ヘッダー
        pitcher_label = fonts.tiny.render("PITCHER", True, (255, 150, 180))
        self.screen.blit(pitcher_label, (pitcher_panel_x + 10, panel_y + 4))
        
        if current_pitcher:
            pitcher_name = f"#{current_pitcher.uniform_number} {current_pitcher.name}"
            pitcher_surf = fonts.small.render(pitcher_name, True, Colors.TEXT_PRIMARY)
            self.screen.blit(pitcher_surf, (pitcher_panel_x + 10, panel_y + 18))
            
            # 能力ランク表示（球速・制球・変化球）＋スタミナバー
            stats = current_pitcher.stats
            spd = getattr(stats, 'speed', 50)
            ctrl = getattr(stats, 'control', 50)
            brk = getattr(stats, 'breaking_ball', 50)
            stam = getattr(stats, 'stamina', 50)
            
            rank_y = panel_y + 38
            rank_items = [("球速", spd), ("制球", ctrl), ("変化", brk)]
            for i, (label, val) in enumerate(rank_items):
                sx = pitcher_panel_x + 8 + i * 50
                lbl_surf = fonts.tiny.render(label, True, (140, 120, 140))
                self.screen.blit(lbl_surf, (sx, rank_y))
                rank = _to_rank(val)
                rank_surf = fonts.small.render(rank, True, _rank_color(rank))
                self.screen.blit(rank_surf, (sx + 28, rank_y - 2))
            
            # スタミナバー表示（ランクの右側に配置）
            pitch_count = game_state.get('pitch_count', {})
            if player_is_pitching:
                current_pitches = pitch_count.get('opponent', 0)
            else:
                current_pitches = pitch_count.get('player', 0)
            
            # スタミナに基づく最大投球数（スタミナ50で約100球、80で約140球、30で約70球）
            max_pitches = int(60 + stam * 1.5)
            remaining_ratio = max(0, min(1, (max_pitches - current_pitches) / max_pitches))
            
            stam_x = pitcher_panel_x + 158
            stam_lbl = fonts.tiny.render("残", True, (140, 120, 140))
            self.screen.blit(stam_lbl, (stam_x, rank_y))
            
            # スタミナバー（残ラベルの右横に配置）
            bar_w = 45
            bar_h = 12
            bar_x = stam_x + 18
            bar_y = rank_y
            pygame.draw.rect(self.screen, (60, 50, 60), (bar_x, bar_y, bar_w, bar_h), border_radius=2)
            
            # 残りスタミナに応じた色
            if remaining_ratio > 0.5:
                bar_color = (100, 200, 100)
            elif remaining_ratio > 0.25:
                bar_color = (200, 180, 80)
            else:
                bar_color = (200, 80, 80)
            
            if remaining_ratio > 0:
                fill_w = int(bar_w * remaining_ratio)
                pygame.draw.rect(self.screen, bar_color, (bar_x, bar_y, fill_w, bar_h), border_radius=2)
        
        # 投手戦術ボタン（右下）
        if player_is_pitching and not game_finished:
            btn_w = 50
            btn_h = 22
            tactic_y = panel_y + 58
            
            selected_pitcher_tactic = game_state.get('selected_pitcher_tactic', 'normal')
            
            # 投球戦術（選択式）: 通常、ボール先行、ストライク先行
            pitcher_tactics = [
                ("通常", "normal"), ("B先行", "ball_first"), ("S先行", "strike_first"),
            ]
            for i, (label, tactic_id) in enumerate(pitcher_tactics):
                bx = pitcher_panel_x + 8 + i * (btn_w + 2)
                style = "primary" if selected_pitcher_tactic == tactic_id else "ghost"
                btn = Button(bx, tactic_y, btn_w, btn_h, label, style, font=fonts.tiny)
                btn.draw(self.screen)
                buttons[f"tactic_pitcher_{tactic_id}"] = btn
            
            # 交代ボタン（選択式ではない）
            sub_y = panel_y + 82
            pitcher_btn = Button(pitcher_panel_x + 8, sub_y, 65, btn_h, "投手交代", "warning", font=fonts.tiny)
            pitcher_btn.draw(self.screen)
            buttons["substitution_pitcher"] = pitcher_btn
            
            defense_btn = Button(pitcher_panel_x + 77, sub_y, 65, btn_h, "守備固め", "warning", font=fonts.tiny)
            defense_btn.draw(self.screen)
            buttons["substitution_defensive"] = defense_btn
            
            # 敬遠は選択式ではなく即実行
            walk_btn = Button(pitcher_panel_x + 146, sub_y, 65, btn_h, "敬遠", "danger", font=fonts.tiny)
            walk_btn.draw(self.screen)
            buttons["tactic_intentional_walk"] = walk_btn
            
            # ========== 守備シフト選択ボタン ==========
            shift_y = panel_y + 108
            selected_shift = game_state.get('defensive_shift', 'normal')
            shift_label = fonts.tiny.render("守備シフト:", True, Colors.TEXT_SECONDARY)
            self.screen.blit(shift_label, (pitcher_panel_x + 8, shift_y))
            
            # シフト選択ボタン（2行で表示）
            shift_options = [
                ("通常", "normal"), ("プル", "pull"), ("逆シフト", "opposite"),
            ]
            shift_options2 = [
                ("前進", "infield_in"), ("深め", "no_doubles"), ("バント", "bunt_defense"),
            ]
            
            shift_btn_w = 45
            shift_btn_h = 20
            for i, (label, shift_id) in enumerate(shift_options):
                bx = pitcher_panel_x + 8 + i * (shift_btn_w + 2)
                style = "primary" if selected_shift == shift_id else "ghost"
                btn = Button(bx, shift_y + 16, shift_btn_w, shift_btn_h, label, style, font=fonts.tiny)
                btn.draw(self.screen)
                buttons[f"shift_{shift_id}"] = btn
            
            for i, (label, shift_id) in enumerate(shift_options2):
                bx = pitcher_panel_x + 8 + i * (shift_btn_w + 2)
                style = "primary" if selected_shift == shift_id else "ghost"
                btn = Button(bx, shift_y + 38, shift_btn_w, shift_btn_h, label, style, font=fonts.tiny)
                btn.draw(self.screen)
                buttons[f"shift_{shift_id}"] = btn
        
        # ========== 下部：操作ボタン ==========
        btn_y = height - 36
        btn_h = 30
        
        # アニメーション関連の状態
        animation_active = game_state.get('animation_active', False)
        waiting_for_animation = game_state.get('waiting_for_animation', False)
        
        if game_finished:
            # 結果ボタンは中央に
            result_btn = Button(center_x - 90, btn_y, 180, btn_h, "結果を見る", "primary", font=fonts.small)
            result_btn.draw(self.screen)
            buttons["end_manage"] = result_btn
        else:
            # 次の球ボタン（再生中以外は表示）
            if not animation_active and not waiting_for_animation:
                # 投手作戦中は右側、打者作戦中は左側に表示
                if player_is_pitching:
                    # 右側（投手パネルの左）
                    next_btn_x = pitcher_panel_x - 100
                else:
                    # 左側（打者パネルの右）
                    next_btn_x = batter_panel_w + 10
                
                if not waiting_for_tactic or not player_is_batting:
                    next_btn = Button(next_btn_x, btn_y, 90, btn_h, "次の球", "primary", font=fonts.small)
                    next_btn.draw(self.screen)
                    buttons["next_manage_play"] = next_btn
            else:
                # 再生中表示
                pulse_color = (100 + int(50 * math.sin(pygame.time.get_ticks() / 200)), 200, 255)
                anim_label = fonts.small.render("再生中...", True, pulse_color)
                self.screen.blit(anim_label, (center_x - 30, btn_y + 6))
        
        # ========== 試合スキップ確認ダイアログ ==========
        if game_state.get('confirm_skip_game', False):
            # 半透明オーバーレイ
            overlay = pygame.Surface((width, height), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            self.screen.blit(overlay, (0, 0))
            
            # ダイアログ
            dialog_w = 300
            dialog_h = 120
            dialog_x = (width - dialog_w) // 2
            dialog_y = (height - dialog_h) // 2
            
            pygame.draw.rect(self.screen, (30, 35, 50), (dialog_x, dialog_y, dialog_w, dialog_h), border_radius=10)
            pygame.draw.rect(self.screen, (80, 150, 200), (dialog_x, dialog_y, dialog_w, dialog_h), 2, border_radius=10)
            
            # メッセージ
            msg = fonts.small.render("試合をスキップしますか？", True, Colors.TEXT_PRIMARY)
            self.screen.blit(msg, (dialog_x + (dialog_w - msg.get_width()) // 2, dialog_y + 25))
            
            # ボタン
            yes_btn = Button(dialog_x + 40, dialog_y + 70, 90, 35, "はい", "danger", font=fonts.small)
            yes_btn.draw(self.screen)
            buttons["confirm_skip_yes"] = yes_btn
            
            no_btn = Button(dialog_x + 170, dialog_y + 70, 90, 35, "いいえ", "ghost", font=fonts.small)
            no_btn.draw(self.screen)
            buttons["confirm_skip_no"] = no_btn
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    # ========================================
    # 選手交代ダイアログ
    # ========================================
    def draw_substitution_dialog(self, mode: str, available_players: list, game_state: dict) -> Dict[str, Button]:
        """選手交代ダイアログを描画"""
        width = self.screen.get_width()
        height = self.screen.get_height()
        
        buttons = {}
        
        # 半透明オーバーレイ
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))
        
        # ダイアログ
        dialog_w = 500
        dialog_h = 450
        dialog_x = (width - dialog_w) // 2
        dialog_y = (height - dialog_h) // 2
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
        pygame.draw.rect(self.screen, Colors.BG_CARD, dialog_rect, border_radius=12)
        pygame.draw.rect(self.screen, Colors.BORDER, dialog_rect, 2, border_radius=12)
        
        # タイトル
        titles = {
            'pinch_hit': '代打選手を選択',
            'pinch_run': '代走選手を選択',
            'pitcher': '交代投手を選択',
            'defensive': '守備固め選手を選択',
        }
        title_text = titles.get(mode, '選手を選択')
        title_surf = fonts.h3.render(title_text, True, Colors.TEXT_PRIMARY)
        self.screen.blit(title_surf, (dialog_x + 20, dialog_y + 15))
        
        # 選手リスト
        list_y = dialog_y + 55
        list_height = 320
        row_height = 35
        
        for i, player in enumerate(available_players[:9]):
            row_y = list_y + i * row_height
            row_rect = pygame.Rect(dialog_x + 15, row_y, dialog_w - 30, row_height - 3)
            
            # 背景
            bg_color = (50, 50, 60) if i % 2 == 0 else (45, 45, 55)
            pygame.draw.rect(self.screen, bg_color, row_rect, border_radius=4)
            
            # 選手情報
            name_text = f"#{player.uniform_number} {player.name}"
            name_surf = fonts.small.render(name_text, True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_surf, (row_rect.x + 10, row_rect.y + 8))
            
            # ポジション
            pos_text = player.position.value if hasattr(player.position, 'value') else str(player.position)
            pos_surf = fonts.tiny.render(pos_text[:6], True, Colors.TEXT_SECONDARY)
            self.screen.blit(pos_surf, (row_rect.x + 200, row_rect.y + 10))
            
            # 能力
            if mode == 'pitcher':
                stat_text = f"球速{self._to_rank(getattr(player.stats, 'speed', 50))} 制球{self._to_rank(getattr(player.stats, 'control', 50))}"
            else:
                stat_text = f"ミ{self._to_rank(getattr(player.stats, 'contact', 50))} パ{self._to_rank(getattr(player.stats, 'power', 50))}"
            stat_surf = fonts.tiny.render(stat_text, True, Colors.TEXT_MUTED)
            self.screen.blit(stat_surf, (row_rect.x + 280, row_rect.y + 10))
            
            # 選択ボタン
            select_btn = Button(row_rect.right - 70, row_rect.y + 3, 60, row_height - 9, "選択", "primary", font=fonts.tiny)
            select_btn.draw(self.screen)
            buttons[f"select_sub_{i}"] = select_btn
        
        # キャンセルボタン
        cancel_btn = Button(dialog_x + dialog_w // 2 - 60, dialog_y + dialog_h - 50, 120, 40, "キャンセル", "ghost", font=fonts.body)
        cancel_btn.draw(self.screen)
        buttons["cancel_substitution"] = cancel_btn
        
        return buttons
    
    # ========================================
    # 試合観戦画面（采配モードベース・采配ボタンなし）
    # ========================================
    def draw_game_watch_screen(self, player_team, opponent_team, game_state: dict, log_scroll: int = 0) -> Dict[str, Button]:
        """試合観戦画面を描画（采配モードと同じUI、采配ボタンなし）"""
        width = self.screen.get_width()
        height = self.screen.get_height()
        center_x = width // 2
        
        buttons = {}
        
        if game_state is None:
            game_state = {}
        
        inning = game_state.get('inning', 1)
        is_top = game_state.get('is_top', True)
        outs = game_state.get('outs', 0)
        strikes = game_state.get('strikes', 0)
        balls = game_state.get('balls', 0)
        runners = game_state.get('runners', [False, False, False])
        home_score = game_state.get('home_score', 0)
        away_score = game_state.get('away_score', 0)
        current_batter = game_state.get('current_batter', None)
        current_pitcher = game_state.get('current_pitcher', None)
        current_play = game_state.get('current_play', "")
        play_log = game_state.get('play_log', [])
        game_finished = game_state.get('game_finished', False)
        pitch_count = game_state.get('pitch_count', 0)
        ball_tracking = game_state.get('ball_tracking', None)
        trajectory = game_state.get('trajectory', [])
        animation_frame = game_state.get('animation_frame', 0)
        
        # チームカラー
        team1_color = self.get_team_color(player_team.name) if player_team else Colors.PRIMARY
        team2_color = self.get_team_color(opponent_team.name) if opponent_team else Colors.DANGER
        
        # 打球追跡時のボール位置を更新
        if trajectory and ball_tracking and animation_frame < len(trajectory):
            frame_data = trajectory[animation_frame]
            if isinstance(frame_data, dict):
                self.cyber_field.ball_position = [
                    frame_data.get('x', 0),
                    frame_data.get('z', 0),  # 高さ
                    frame_data.get('y', 0)   # 奥行き
                ]
            else:
                self.cyber_field.ball_position = [frame_data[0], frame_data[2], frame_data[1]]
            self.cyber_field.is_ball_flying = True
        else:
            self.cyber_field.is_ball_flying = False
        
        # ========== 球場設定（パークファクターに基づく） ==========
        # ホームチームの球場を使用
        home_team = player_team if not is_top else opponent_team
        if home_team:
            stadium_info = NPB_STADIUMS.get(home_team.name, {})
            park_factor = stadium_info.get('home_run_factor', 1.0)
            stadium_name = stadium_info.get('name', '')
            self.cyber_field.set_stadium(park_factor, stadium_name)
            # ゲーム状態にもパークファクターを反映
            game_state['park_factor'] = park_factor
        
        # 守備チームの能力を設定（表の攻撃＝ホームチームが守備、裏の攻撃＝アウェイチームが守備）
        fielding_team = opponent_team if is_top else player_team
        self.cyber_field.set_fielder_abilities(fielding_team)
        
        # ========== サイバー3Dフィールド描画 ==========
        self.cyber_field.width = width
        self.cyber_field.height = height
        self.cyber_field.vanishing_point_x = width / 2
        self.cyber_field.vanishing_point_y = height * 0.35
        
        # カメラ設定を固定
        self.cyber_field.camera_height = CyberField3D.DEFAULT_CAMERA_HEIGHT
        self.cyber_field.camera_dist = CyberField3D.DEFAULT_CAMERA_DIST
        self.cyber_field.camera_angle = CyberField3D.DEFAULT_CAMERA_ANGLE
        self.cyber_field.fov = CyberField3D.DEFAULT_FOV
        self.cyber_field.camera_offset_x = 0
        
        self.cyber_field.draw_background()
        self.cyber_field.draw_grid()
        self.cyber_field.draw_foul_lines()
        self.cyber_field.draw_fence()
        self.cyber_field.draw_bases(runners)
        
        # 打球トラッキング中は動的野手を表示
        if trajectory and ball_tracking:
            # アニメーションフレームまでの軌跡のみ表示
            display_trajectory = trajectory[:animation_frame + 1] if animation_frame < len(trajectory) else trajectory
            # 守備は表示しない（物理計算で結果決定済み）
            self.cyber_field.draw_ball_trajectory(display_trajectory)
            self.cyber_field.draw_ball_with_shadow()
            # ミニマップを右下に表示（パネルと被らないように上に配置）
            self.cyber_field.draw_minimap(width - 140, height - 260, 130)
        # 守備配置は表示しない
        
        # ========== スコアボード（左上、洗練されたデザイン） ==========
        score_board_x = 10
        score_board_y = 10
        score_board_w = 220
        score_board_h = 95
        
        # グラデーション背景
        score_bg = pygame.Surface((score_board_w, score_board_h), pygame.SRCALPHA)
        for i in range(score_board_h):
            alpha = 230 - i // 3
            score_bg.fill((0, 20 + i // 5, 45 + i // 4, alpha), (0, i, score_board_w, 1))
        self.screen.blit(score_bg, (score_board_x, score_board_y))
        pygame.draw.rect(self.screen, (80, 150, 200), (score_board_x, score_board_y, score_board_w, score_board_h), 2, border_radius=8)
        
        # イニングヘッダー
        inning_bg = pygame.Surface((score_board_w - 16, 22), pygame.SRCALPHA)
        if game_finished:
            inning_bg.fill((200, 50, 80, 180))
            inning_text = "FINAL"
            inning_color = (255, 220, 220)
        else:
            inning_bg.fill((50, 100, 150, 150))
            inning_text = f"{inning}回{'表' if is_top else '裏'}"
            inning_color = (180, 220, 255)
        self.screen.blit(inning_bg, (score_board_x + 8, score_board_y + 4))
        inning_surf = fonts.small.render(inning_text, True, inning_color)
        self.screen.blit(inning_surf, (score_board_x + 15, score_board_y + 7))
        
        # ライブインジケーター
        if not game_finished:
            pulse = (math.sin(time.time() * 4) + 1) / 2
            color = (255, int(80 * pulse), int(80 * pulse))
            pygame.draw.circle(self.screen, color, (score_board_x + score_board_w - 20, score_board_y + 15), 6)
            pygame.draw.circle(self.screen, (255, 255, 255, 180), (score_board_x + score_board_w - 21, score_board_y + 14), 2)
        
        # チーム名とスコア
        team_y = score_board_y + 32
        # アウェイ
        pygame.draw.rect(self.screen, team2_color, (score_board_x + 12, team_y, 5, 16), border_radius=2)
        away_name = opponent_team.name[:7] if opponent_team else "AWAY"
        away_surf = fonts.small.render(away_name, True, Colors.TEXT_PRIMARY)
        self.screen.blit(away_surf, (score_board_x + 22, team_y))
        away_score_bg = pygame.Surface((40, 20), pygame.SRCALPHA)
        away_score_bg.fill((0, 50, 80, 150) if not is_top else (80, 150, 200, 100))
        self.screen.blit(away_score_bg, (score_board_x + 155, team_y - 2))
        away_score_surf = fonts.h3.render(str(away_score), True, (255, 255, 255))
        self.screen.blit(away_score_surf, (score_board_x + 165, team_y - 2))
        
        # ホーム
        home_y = team_y + 24
        pygame.draw.rect(self.screen, team1_color, (score_board_x + 12, home_y, 5, 16), border_radius=2)
        home_name = player_team.name[:7] if player_team else "HOME"
        home_surf = fonts.small.render(home_name, True, Colors.TEXT_PRIMARY)
        self.screen.blit(home_surf, (score_board_x + 22, home_y))
        home_score_bg = pygame.Surface((40, 20), pygame.SRCALPHA)
        home_score_bg.fill((80, 150, 200, 100) if not is_top else (0, 50, 80, 150))
        self.screen.blit(home_score_bg, (score_board_x + 155, home_y - 2))
        home_score_surf = fonts.h3.render(str(home_score), True, (255, 255, 255))
        self.screen.blit(home_score_surf, (score_board_x + 165, home_y - 2))
        
        # 攻撃中マーカー（アニメーション）
        marker_pulse = 0.7 + 0.3 * math.sin(pygame.time.get_ticks() / 300)
        marker_color = tuple(int(c * marker_pulse) for c in (100, 255, 200))
        if is_top:
            pygame.draw.polygon(self.screen, marker_color, [
                (score_board_x + 5, team_y + 8), (score_board_x + 10, team_y + 4), (score_board_x + 10, team_y + 12)])
        else:
            pygame.draw.polygon(self.screen, marker_color, [
                (score_board_x + 5, home_y + 8), (score_board_x + 10, home_y + 4), (score_board_x + 10, home_y + 12)])
        
        # ========== BSO表示（右上・洗練されたデザイン） ==========
        bso_x = width - 105
        bso_y = 10
        bso_w = 95
        bso_h = 75
        
        bso_bg = pygame.Surface((bso_w, bso_h), pygame.SRCALPHA)
        for i in range(bso_h):
            alpha = 220 - i // 3
            bso_bg.fill((15 + i // 5, 25 + i // 4, 45 + i // 3, alpha), (0, i, bso_w, 1))
        self.screen.blit(bso_bg, (bso_x, bso_y))
        pygame.draw.rect(self.screen, (80, 150, 200), (bso_x, bso_y, bso_w, bso_h), 2, border_radius=8)
        
        bso_data = [
            ("B", balls, 4, (76, 200, 100), (30, 60, 40)),
            ("S", strikes, 3, (255, 210, 80), (60, 50, 30)),
            ("O", outs, 3, (255, 90, 90), (60, 30, 30))
        ]
        for i, (label, count, max_c, active_color, inactive_color) in enumerate(bso_data):
            by = bso_y + 10 + i * 21
            label_surf = fonts.small.render(label, True, (150, 180, 200))
            self.screen.blit(label_surf, (bso_x + 10, by))
            for j in range(max_c):
                cx = bso_x + 35 + j * 16
                cy = by + 8
                if j < count:
                    glow_surf = pygame.Surface((16, 16), pygame.SRCALPHA)
                    pygame.draw.circle(glow_surf, (*active_color[:3], 100), (8, 8), 7)
                    self.screen.blit(glow_surf, (cx - 8, cy - 8))
                    pygame.draw.circle(self.screen, active_color, (cx, cy), 5)
                    pygame.draw.circle(self.screen, (255, 255, 255, 180), (cx - 1, cy - 1), 2)
                else:
                    pygame.draw.circle(self.screen, inactive_color, (cx, cy), 5)
                    pygame.draw.circle(self.screen, (60, 70, 90), (cx, cy), 5, 1)
        
        # ========== トラッキングデータパネル ==========
        if ball_tracking:
            self.cyber_field.draw_tracking_data_panel(ball_tracking, width - 190, 100)
        
        # ========== プレイ結果（画面上部に表示） ==========
        if current_play or game_finished:
            result_text = "GAME SET !!" if game_finished else current_play
            if "三振" in result_text or "アウト" in result_text:
                result_color = (150, 150, 180)
            elif "ヒット" in result_text or "二塁打" in result_text or "三塁打" in result_text:
                result_color = (0, 255, 150)
            elif "ホームラン" in result_text:
                result_color = CyberField3D.COLOR_FENCE
            elif "四球" in result_text:
                result_color = (100, 200, 255)
            elif game_finished:
                result_color = CyberField3D.COLOR_FENCE
            else:
                result_color = CyberField3D.COLOR_TEXT
            
            # 画面上部に結果バーを表示（スコアボードの下）
            result_bar_y = 90
            result_bar_h = 45
            result_bar_w = 400  # 短いバー
            result_bar_x = center_x - result_bar_w // 2
            
            # 背景バー
            result_bar = pygame.Surface((result_bar_w, result_bar_h), pygame.SRCALPHA)
            result_bar.fill((0, 0, 0, 180))
            self.screen.blit(result_bar, (result_bar_x, result_bar_y))
            
            # 上下のアクセントライン
            pygame.draw.line(self.screen, result_color, (result_bar_x, result_bar_y), (result_bar_x + result_bar_w, result_bar_y), 2)
            pygame.draw.line(self.screen, (result_color[0]//2, result_color[1]//2, result_color[2]//2), 
                            (result_bar_x, result_bar_y + result_bar_h), (result_bar_x + result_bar_w, result_bar_y + result_bar_h), 1)
            
            # グロー効果付きテキスト
            glow_color = (result_color[0]//3, result_color[1]//3, result_color[2]//3)
            result_surf = fonts.h2.render(result_text, True, result_color)
            glow_surf = fonts.h2.render(result_text, True, glow_color)
            
            text_x = center_x - result_surf.get_width() // 2
            text_y = result_bar_y + (result_bar_h - result_surf.get_height()) // 2
            
            # グロー
            for ox, oy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
                self.screen.blit(glow_surf, (text_x + ox, text_y + oy))
            
            # メインテキスト
            shadow_surf = fonts.h2.render(result_text, True, (0, 0, 0))
            self.screen.blit(shadow_surf, (text_x + 2, text_y + 2))
            self.screen.blit(result_surf, (text_x, text_y))
        
        # ========== 下部パネル（左：打者、右：投手）采配モードスタイル ==========
        panel_h = 100
        panel_y = height - panel_h
        
        # 能力値からランクに変換する関数
        def _to_rank(val):
            if val >= 90: return "S"
            elif val >= 80: return "A"
            elif val >= 70: return "B"
            elif val >= 60: return "C"
            elif val >= 50: return "D"
            elif val >= 40: return "E"
            else: return "F"
        
        def _rank_color(rank):
            colors = {"S": (255, 215, 0), "A": (255, 100, 100), "B": (255, 150, 80),
                      "C": (100, 200, 255), "D": (150, 180, 200), "E": (120, 120, 140), "F": (100, 100, 100)}
            return colors.get(rank, (180, 180, 180))
        
        # ========== 左側：打者パネル ==========
        batter_panel_w = 220
        # 半透明背景
        batter_bg = pygame.Surface((batter_panel_w, panel_h), pygame.SRCALPHA)
        batter_bg.fill((15, 25, 45, 200))
        self.screen.blit(batter_bg, (0, panel_y))
        pygame.draw.rect(self.screen, (80, 180, 255), (0, panel_y, 3, panel_h))
        
        # 打者ヘッダー
        batter_label = fonts.tiny.render("BATTER", True, (100, 180, 255))
        self.screen.blit(batter_label, (10, panel_y + 4))
        
        if current_batter:
            batter_name = f"#{current_batter.uniform_number} {current_batter.name}"
            batter_surf = fonts.small.render(batter_name, True, Colors.TEXT_PRIMARY)
            self.screen.blit(batter_surf, (10, panel_y + 18))
            
            # 能力ランク表示（ミート・パワー・走力のみ）
            stats = current_batter.stats
            contact = getattr(stats, 'contact', 50)
            power = getattr(stats, 'power', 50)
            speed = getattr(stats, 'speed', 50)
            
            rank_y = panel_y + 40
            rank_items = [("ミート", contact), ("パワー", power), ("走力", speed)]
            for i, (label, val) in enumerate(rank_items):
                sx = 10 + i * 70
                lbl_surf = fonts.tiny.render(label, True, (120, 140, 160))
                self.screen.blit(lbl_surf, (sx, rank_y))
                rank = _to_rank(val)
                rank_surf = fonts.small.render(rank, True, _rank_color(rank))
                self.screen.blit(rank_surf, (sx + 36, rank_y - 2))
            
            # 打率表示
            avg = current_batter.record.batting_average if hasattr(current_batter.record, 'batting_average') else 0
            avg_text = f".{int(avg * 1000):03d}" if avg > 0 else ".---"
            avg_surf = fonts.small.render(avg_text, True, (200, 220, 255))
            self.screen.blit(avg_surf, (10, panel_y + 65))
        
        # ========== 右側：投手パネル ==========
        pitcher_panel_w = 220
        pitcher_panel_x = width - pitcher_panel_w
        # 半透明背景
        pitcher_bg = pygame.Surface((pitcher_panel_w, panel_h), pygame.SRCALPHA)
        pitcher_bg.fill((45, 20, 35, 200))
        self.screen.blit(pitcher_bg, (pitcher_panel_x, panel_y))
        pygame.draw.rect(self.screen, (255, 100, 150), (width - 3, panel_y, 3, panel_h))
        
        # 投手ヘッダー
        pitcher_label = fonts.tiny.render("PITCHER", True, (255, 150, 180))
        self.screen.blit(pitcher_label, (pitcher_panel_x + 10, panel_y + 4))
        
        if current_pitcher:
            pitcher_name = f"#{current_pitcher.uniform_number} {current_pitcher.name}"
            pitcher_surf = fonts.small.render(pitcher_name, True, Colors.TEXT_PRIMARY)
            self.screen.blit(pitcher_surf, (pitcher_panel_x + 10, panel_y + 18))
            
            # 能力ランク表示（球速・制球・変化球）
            stats = current_pitcher.stats
            spd = getattr(stats, 'speed', 50)
            ctrl = getattr(stats, 'control', 50)
            brk = getattr(stats, 'breaking_ball', 50)
            
            rank_y = panel_y + 40
            rank_items = [("球速", spd), ("制球", ctrl), ("変化", brk)]
            for i, (label, val) in enumerate(rank_items):
                sx = pitcher_panel_x + 8 + i * 55
                lbl_surf = fonts.tiny.render(label, True, (140, 120, 140))
                self.screen.blit(lbl_surf, (sx, rank_y))
                rank = _to_rank(val)
                rank_surf = fonts.small.render(rank, True, _rank_color(rank))
                self.screen.blit(rank_surf, (sx + 28, rank_y - 2))
            
            # 投球数表示
            pitch_surf = fonts.small.render(f"📊 {pitch_count}球", True, (200, 180, 220))
            self.screen.blit(pitch_surf, (pitcher_panel_x + 10, panel_y + 65))
        
        # ========== ボタンエリア（下部中央） ==========
        btn_y = panel_y + 35
        btn_h = 30
        
        if game_finished:
            result_btn = Button(center_x - 90, btn_y, 180, btn_h, "結果を見る", "primary", font=fonts.small)
            result_btn.draw(self.screen)
            buttons["end_watch"] = result_btn
        else:
            # 次の球ボタン（中央左）
            next_btn = Button(batter_panel_w + 15, btn_y, 100, btn_h, "次の球", "primary", font=fonts.small)
            next_btn.draw(self.screen)
            buttons["next_play"] = next_btn
            
            # イニングスキップ
            skip_inning_btn = Button(batter_panel_w + 125, btn_y, 110, btn_h, "イニング終了", "ghost", font=fonts.small)
            skip_inning_btn.draw(self.screen)
            buttons["skip_inning"] = skip_inning_btn
            
            # 試合スキップ
            skip_game_btn = Button(batter_panel_w + 245, btn_y, 100, btn_h, "試合終了", "ghost", font=fonts.small)
            skip_game_btn.draw(self.screen)
            buttons["skip_game"] = skip_game_btn
            
            # 終了ボタン
            end_btn = Button(pitcher_panel_x - 85, btn_y, 75, btn_h, "終了", "warning", font=fonts.small)
            end_btn.draw(self.screen)
            buttons["end_watch"] = end_btn
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    def _draw_stadium_background(self, width, height):
        """3D野球場背景を描画（フェンスが上、ホームベースが下）"""
        # ダークグリーン背景
        self.screen.fill((8, 20, 12))
        
        # 芝生パターン（3D遠近感）
        cx = width // 2
        home_y = height - 80  # ホームベースの位置（下部）
        fence_y = 60  # フェンスの位置（上部）
        
        # 外野芝生（濃淡でストライプ）
        for i in range(20):
            stripe_color = (20, 60, 30) if i % 2 == 0 else (25, 70, 35)
            y1 = fence_y + i * (home_y - fence_y - 100) // 20
            y2 = fence_y + (i + 1) * (home_y - fence_y - 100) // 20
            # 遠近感のある台形
            top_w = int(width * 0.3 + (width * 0.5) * i / 20)
            bot_w = int(width * 0.3 + (width * 0.5) * (i + 1) / 20)
            pts = [
                (cx - top_w // 2, y1),
                (cx + top_w // 2, y1),
                (cx + bot_w // 2, y2),
                (cx - bot_w // 2, y2)
            ]
            pygame.draw.polygon(self.screen, stripe_color, pts)
        
        # 内野土部分
        infield_color = (60, 45, 30)
        infield_y = home_y - 180
        infield_pts = [
            (cx, infield_y),
            (cx + 150, home_y - 90),
            (cx, home_y),
            (cx - 150, home_y - 90)
        ]
        pygame.draw.polygon(self.screen, infield_color, infield_pts)
        
        # 内野芝（緑の菱形）
        inner_grass_color = (30, 75, 40)
        grass_pts = [
            (cx, infield_y + 40),
            (cx + 80, home_y - 110),
            (cx, home_y - 60),
            (cx - 80, home_y - 110)
        ]
        pygame.draw.polygon(self.screen, inner_grass_color, grass_pts)
        
        # 外野フェンス
        fence_color = (20, 50, 80)
        fence_pts = [
            (cx - int(width * 0.4), fence_y),
            (cx - int(width * 0.35), fence_y - 15),
            (cx, fence_y - 25),
            (cx + int(width * 0.35), fence_y - 15),
            (cx + int(width * 0.4), fence_y),
            (cx + int(width * 0.4), fence_y + 20),
            (cx - int(width * 0.4), fence_y + 20),
        ]
        pygame.draw.polygon(self.screen, fence_color, fence_pts)
        # フェンス上部のライン
        pygame.draw.line(self.screen, (255, 220, 50), 
                        (cx - int(width * 0.4), fence_y), 
                        (cx + int(width * 0.4), fence_y), 3)
        
        # ファールライン
        foul_color = (200, 200, 200)
        pygame.draw.line(self.screen, foul_color, (cx, home_y), (cx - int(width * 0.4), fence_y + 20), 2)
        pygame.draw.line(self.screen, foul_color, (cx, home_y), (cx + int(width * 0.4), fence_y + 20), 2)
        
        # 距離表示（フェンス）
        dist_surf = fonts.tiny.render("122m", True, (150, 200, 255))
        self.screen.blit(dist_surf, (cx - 20, fence_y + 5))
    
    def _draw_3d_diamond(self, width, height, runners, is_top):
        """3D視点のダイヤモンドを描画"""
        cx = width // 2
        home_y = height - 80
        
        # 塁の位置（3D遠近感）
        base_positions = [
            (cx, home_y),           # ホーム
            (cx + 110, home_y - 70),  # 1塁
            (cx, home_y - 150),       # 2塁
            (cx - 110, home_y - 70),  # 3塁
        ]
        
        # ベースライン
        line_color = (200, 200, 200)
        for i in range(4):
            pygame.draw.line(self.screen, line_color, 
                           base_positions[i], base_positions[(i + 1) % 4], 2)
        
        # 各塁ベース
        base_size = 12
        for i, (bx, by) in enumerate(base_positions):
            if i == 0:  # ホームベース
                pts = [(bx, by - 8), (bx + 10, by), (bx + 6, by + 8), 
                       (bx - 6, by + 8), (bx - 10, by)]
                pygame.draw.polygon(self.screen, (200, 200, 200), pts)
            else:
                # ランナーがいる場合はオレンジ
                if runners[i - 1]:
                    pygame.draw.rect(self.screen, (255, 150, 50), 
                                   (bx - base_size // 2, by - base_size // 2, base_size, base_size))
                    # ランナーマーカー
                    pygame.draw.circle(self.screen, (255, 200, 100), (bx, by - 15), 6)
                else:
                    pygame.draw.rect(self.screen, (200, 200, 200), 
                                   (bx - base_size // 2, by - base_size // 2, base_size, base_size))
        
        # ピッチャーマウンド
        mound_x, mound_y = cx, home_y - 75
        pygame.draw.ellipse(self.screen, (70, 55, 40), (mound_x - 20, mound_y - 8, 40, 16))
        pygame.draw.rect(self.screen, (200, 200, 200), (mound_x - 6, mound_y - 2, 12, 4))
        
        # バッターボックス
        pygame.draw.rect(self.screen, (200, 200, 200), (cx - 30, home_y - 15, 20, 35), 1)
        pygame.draw.rect(self.screen, (200, 200, 200), (cx + 10, home_y - 15, 20, 35), 1)
        
        return base_positions
    
    def _draw_fielder_positions(self, width, height, fielder_tracking=None):
        """守備位置を描画"""
        cx = width // 2
        home_y = height - 80
        
        # 基本守備位置（3D遠近感）
        default_positions = {
            'P': (cx, home_y - 75),
            'C': (cx, home_y + 20),
            '1B': (cx + 130, home_y - 60),
            '2B': (cx + 50, home_y - 110),
            'SS': (cx - 50, home_y - 110),
            '3B': (cx - 130, home_y - 60),
            'LF': (cx - 180, home_y - 200),
            'CF': (cx, home_y - 250),
            'RF': (cx + 180, home_y - 200),
        }
        
        # 守備者を描画
        for pos, (px, py) in default_positions.items():
            # 守備者のマーカー
            color = (50, 150, 255) if pos != 'P' else (255, 100, 100)
            pygame.draw.circle(self.screen, color, (px, py), 8)
            pygame.draw.circle(self.screen, (255, 255, 255), (px, py), 8, 2)
            
            # ポジションラベル
            label = fonts.tiny.render(pos, True, (200, 200, 200))
            self.screen.blit(label, (px - label.get_width() // 2, py + 12))
        
        # 守備者の動き（トラッキングがある場合）
        if fielder_tracking and fielder_tracking.get('fielder_position'):
            target_pos = fielder_tracking['fielder_position']
            fielder = fielder_tracking.get('fielder_name', '')
            
            # 守備者が捕球に向かう線
            for pos, (px, py) in default_positions.items():
                if pos not in ['P', 'C']:
                    # 移動経路を点線で表示
                    pygame.draw.line(self.screen, (100, 200, 255), 
                                   (px, py), target_pos, 1)
    
    def _draw_large_diamond(self, cx, cy, runners, is_top):
        """互換性のため残す（3Dダイヤモンドを使用）"""
        width = self.screen.get_width()
        height = self.screen.get_height()
        self._draw_3d_diamond(width, height, runners, is_top)
    
    def _draw_ball_tracking(self, cx, cy, play_result: str, ball_tracking=None, trajectory=None):
        """打球トラッキングを描画（物理計算ベース）"""
        width = self.screen.get_width()
        height = self.screen.get_height()
        field_cx = width // 2
        home_y = height - 80
        
        # 打球データがない場合は従来のランダム表示
        if not ball_tracking:
            self._draw_ball_tracking_legacy(cx, cy, play_result)
            return
        
        # 物理データから描画
        exit_velocity = ball_tracking.get('exit_velocity', 100)
        launch_angle = ball_tracking.get('launch_angle', 20)
        direction = ball_tracking.get('direction', 0)
        
        # 方向と飛距離から終点を計算（3D視点変換）
        distance = ball_tracking.get('distance', 50)
        
        # 方向角度からX位置を計算（-45〜+45度）
        import math
        dir_rad = math.radians(direction)
        end_x = field_cx + int(distance * 2 * math.sin(dir_rad))
        
        # 飛距離からY位置を計算（遠近感）
        # 100m = フェンス付近、0m = ホーム付近
        normalized_dist = min(distance / 130, 1.0)  # 130mを最大とする
        end_y = home_y - int((home_y - 80) * normalized_dist)
        
        # 打球タイプによる色
        if launch_angle > 25 and distance > 100:  # ホームラン級
            ball_color = (255, 200, 50)
            trail_color = (255, 150, 0)
        elif launch_angle > 15:  # フライ
            ball_color = (100, 200, 255)
            trail_color = (50, 150, 200)
        elif launch_angle < 0:  # ゴロ
            ball_color = (150, 180, 150)
            trail_color = (100, 130, 100)
        else:  # ライナー
            ball_color = (100, 255, 150)
            trail_color = (50, 200, 100)
        
        # 軌道を描画（複数点）
        if trajectory:
            prev_point = None
            for i, point in enumerate(trajectory[::3]):  # 3点ごとに表示
                # 3D座標を2D画面座標に変換
                tx = field_cx + int(point['x'] * 2)
                # Y座標は飛距離に応じて
                ty = home_y - int(point['y'] * 2) - int(point['z'] * 0.5)
                
                if prev_point:
                    pygame.draw.line(self.screen, trail_color, prev_point, (tx, ty), 2)
                prev_point = (tx, ty)
        else:
            # 軌道データがない場合は直線
            pygame.draw.line(self.screen, trail_color, (field_cx, home_y), (end_x, end_y), 3)
        
        # ボール位置
        pygame.draw.circle(self.screen, (255, 255, 255), (end_x, end_y), 10)
        pygame.draw.circle(self.screen, ball_color, (end_x, end_y), 7)
        
        # 打球データパネル（右上に配置）
        panel_x = width - 160
        panel_y = 100
        panel_w = 150
        panel_h = 100
        
        # パネル背景
        panel_surface = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surface.fill((10, 20, 30, 220))
        self.screen.blit(panel_surface, (panel_x, panel_y))
        pygame.draw.rect(self.screen, ball_color, (panel_x, panel_y, panel_w, panel_h), 2, border_radius=5)
        
        # データ表示
        title_surf = fonts.small.render("TRACKING DATA", True, ball_color)
        self.screen.blit(title_surf, (panel_x + 10, panel_y + 5))
        
        data_texts = [
            f"Exit Velo: {exit_velocity:.1f} km/h",
            f"Launch: {launch_angle:.1f} deg",
            f"Direction: {direction:.1f} deg",
            f"Distance: {distance:.1f} m"
        ]
        
        for i, text in enumerate(data_texts):
            text_surf = fonts.tiny.render(text, True, (200, 220, 240))
            self.screen.blit(text_surf, (panel_x + 10, panel_y + 25 + i * 18))
    
    def _draw_ball_tracking_legacy(self, cx, cy, play_result: str):
        """打球トラッキングを描画（レガシー版）"""
        ds = 70
        home_x, home_y = cx, cy + ds
        
        # 打球の種類に応じた軌道を決定
        if "ホームラン" in play_result:
            # ホームラン：センター方向に大きく飛ぶ
            end_x, end_y = cx + random.randint(-40, 40), cy - 150
            ball_color = (255, 200, 50)
            trail_color = (255, 150, 0)
            speed_text = f"{random.randint(145, 165)} km/h"
            angle_text = f"{random.randint(28, 38)}°"
            dist_text = f"{random.randint(120, 150)}m"
        elif "三塁打" in play_result:
            # 三塁打：ライト方向
            end_x, end_y = cx + random.randint(80, 120), cy - 80
            ball_color = (100, 255, 150)
            trail_color = (50, 200, 100)
            speed_text = f"{random.randint(130, 145)} km/h"
            angle_text = f"{random.randint(15, 25)}°"
            dist_text = f"{random.randint(90, 110)}m"
        elif "二塁打" in play_result:
            # 二塁打：レフト方向
            end_x, end_y = cx + random.randint(-100, -60), cy - 60
            ball_color = (100, 255, 150)
            trail_color = (50, 200, 100)
            speed_text = f"{random.randint(125, 140)} km/h"
            angle_text = f"{random.randint(12, 22)}°"
            dist_text = f"{random.randint(70, 95)}m"
        elif "ヒット" in play_result or "シングル" in play_result:
            # シングルヒット：内野を抜ける
            direction = random.choice([-1, 1])
            end_x, end_y = cx + direction * random.randint(40, 80), cy - random.randint(20, 50)
            ball_color = (100, 255, 150)
            trail_color = (50, 200, 100)
            speed_text = f"{random.randint(110, 130)} km/h"
            angle_text = f"{random.randint(5, 15)}°"
            dist_text = f"{random.randint(40, 70)}m"
        elif "フライ" in play_result or "アウト" in play_result:
            # フライアウト
            direction = random.choice([-1, 0, 1])
            end_x, end_y = cx + direction * random.randint(30, 60), cy - random.randint(30, 60)
            ball_color = (150, 150, 180)
            trail_color = (80, 80, 120)
            speed_text = f"{random.randint(95, 115)} km/h"
            angle_text = f"{random.randint(35, 55)}°"
            dist_text = f"{random.randint(50, 80)}m"
        elif "ゴロ" in play_result:
            # ゴロ
            direction = random.choice([-1, 0, 1])
            end_x, end_y = cx + direction * random.randint(20, 50), cy + random.randint(-20, 20)
            ball_color = (150, 150, 180)
            trail_color = (80, 80, 120)
            speed_text = f"{random.randint(100, 120)} km/h"
            angle_text = f"-{random.randint(5, 15)}°"
            dist_text = f"{random.randint(20, 40)}m"
        elif "三振" in play_result or "四球" in play_result:
            # 打球なし
            return
        else:
            # その他
            return
        
        # 軌道ライン（グロー効果）
        for offset in [4, 3, 2]:
            pygame.draw.line(self.screen, trail_color, (home_x, home_y), (end_x, end_y), offset)
        pygame.draw.line(self.screen, ball_color, (home_x, home_y), (end_x, end_y), 2)
        
        # ボール位置（終点）
        pygame.draw.circle(self.screen, (255, 255, 255), (end_x, end_y), 8)
        pygame.draw.circle(self.screen, ball_color, (end_x, end_y), 6)
        
        # 打球データ表示
        data_x = end_x + 15
        data_y = end_y - 30
        
        # データパネル背景
        panel_w, panel_h = 85, 50
        data_panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        data_panel.fill((10, 15, 25, 200))
        self.screen.blit(data_panel, (data_x, data_y))
        pygame.draw.rect(self.screen, ball_color, (data_x, data_y, panel_w, panel_h), 1, border_radius=3)
        
        # データテキスト
        speed_surf = fonts.tiny.render(speed_text, True, ball_color)
        angle_surf = fonts.tiny.render(angle_text, True, (150, 180, 200))
        dist_surf = fonts.tiny.render(dist_text, True, (200, 200, 220))
        
        self.screen.blit(speed_surf, (data_x + 5, data_y + 4))
        self.screen.blit(angle_surf, (data_x + 5, data_y + 18))
        self.screen.blit(dist_surf, (data_x + 5, data_y + 32))
    
    def _draw_batter_icon(self, x, y, size):
        """バッターアイコンを描画（サイバー風）"""
        # 体（アウトライン）
        pygame.draw.circle(self.screen, (80, 150, 200), (x + size // 2, y - size // 4), size // 4, 2)
        pygame.draw.rect(self.screen, (80, 150, 200), (x + size // 3, y, size // 3, size // 2), 2, border_radius=3)
        # バット
        pygame.draw.line(self.screen, (200, 180, 100), (x + size // 2, y - size // 4), (x + size, y - size // 2), 2)
    
    def _draw_pitcher_icon(self, x, y, size):
        """ピッチャーアイコンを描画（サイバー風）"""
        # 体（アウトライン）
        pygame.draw.circle(self.screen, (200, 100, 100), (x + size // 2, y - size // 4), size // 4, 2)
        pygame.draw.rect(self.screen, (200, 100, 100), (x + size // 3, y, size // 3, size // 2), 2, border_radius=3)
        # 腕
        pygame.draw.line(self.screen, (200, 100, 100), (x + size // 2, y + size // 6), (x + size, y - size // 4), 2)
    
    def _draw_mini_stat_bar(self, x, y, label, value, color):
        """ミニ能力バーを描画"""
        label_surf = fonts.tiny.render(label, True, (100, 105, 120))
        self.screen.blit(label_surf, (x, y))
        
        bar_x = x + 45
        bar_y = y + 4
        bar_w = 70
        bar_h = 6
        
        # 背景
        pygame.draw.rect(self.screen, (40, 43, 53), (bar_x, bar_y, bar_w, bar_h), border_radius=3)
        # 値
        fill_w = int(bar_w * min(value, 100) / 100)
        if fill_w > 0:
            pygame.draw.rect(self.screen, color, (bar_x, bar_y, fill_w, bar_h), border_radius=3)
    
    # ========================================
    # 試合結果画面
    # ========================================
    def draw_result_screen(self, game_simulator, scroll_offset: int = 0) -> Dict[str, Button]:
        """試合結果画面を描画（投手・打者成績スクロール対応）"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        center_x = width // 2
        
        buttons = {}
        
        if not game_simulator:
            return buttons
        
        # ヘッダー
        header_h = draw_header(self.screen, "試合結果")
        
        home_team = game_simulator.home_team
        away_team = game_simulator.away_team
        home_color = self.get_team_color(home_team.name)
        away_color = self.get_team_color(away_team.name)
        
        # === スコアボード（イニングスコア付き）===
        score_card_w = min(800, width - 40)
        score_card = Card(center_x - score_card_w // 2, header_h + 10, score_card_w, 120)
        score_rect = score_card.draw(self.screen)
        
        # イニング数を取得
        innings_away = game_simulator.inning_scores_away if hasattr(game_simulator, 'inning_scores_away') else []
        innings_home = game_simulator.inning_scores_home if hasattr(game_simulator, 'inning_scores_home') else []
        num_innings = max(9, len(innings_away), len(innings_home))
        
        # イニングスコア表示
        table_y = score_rect.y + 20
        team_col_w = 80
        inning_col_w = 26
        total_col_w = 32
        
        # ヘッダー行（イニング番号）
        x = score_rect.x + team_col_w + 8
        for i in range(1, min(num_innings + 1, 13)):  # 最大12回まで表示
            inn_surf = fonts.tiny.render(str(i), True, Colors.TEXT_MUTED)
            inn_rect = inn_surf.get_rect(center=(x + inning_col_w // 2, table_y))
            self.screen.blit(inn_surf, inn_rect)
            x += inning_col_w
        
        # R/H/E ヘッダー
        for label in ["R", "H", "E"]:
            label_surf = fonts.tiny.render(label, True, Colors.TEXT_MUTED)
            label_rect = label_surf.get_rect(center=(x + total_col_w // 2, table_y))
            self.screen.blit(label_surf, label_rect)
            x += total_col_w
        
        # アウェイチーム行
        table_y += 22
        away_name_short = away_team.name[:4]
        away_surf = fonts.small.render(away_name_short, True, away_color)
        self.screen.blit(away_surf, (score_rect.x + 8, table_y))
        
        x = score_rect.x + team_col_w + 8
        for i in range(min(num_innings, 12)):
            if i < len(innings_away):
                score_val = innings_away[i]
                score_text = str(score_val) if score_val != 'X' else 'X'
                score_color = Colors.WARNING if score_val not in [0, 'X'] else Colors.TEXT_SECONDARY
            else:
                score_text = "-"
                score_color = Colors.TEXT_MUTED
            score_surf = fonts.small.render(score_text, True, score_color)
            score_r = score_surf.get_rect(center=(x + inning_col_w // 2, table_y + 6))
            self.screen.blit(score_surf, score_r)
            x += inning_col_w
        
        # アウェイ R/H/E - batting_resultsから集計
        away_hits = 0
        if hasattr(game_simulator, 'batting_results'):
            for key, stats in game_simulator.batting_results.items():
                if key[0] == away_team.name:
                    away_hits += stats.get('hits', 0)
        away_errors = 0
        for val, color in [(game_simulator.away_score, Colors.TEXT_PRIMARY), (away_hits, Colors.TEXT_SECONDARY), (away_errors, Colors.TEXT_SECONDARY)]:
            val_surf = fonts.body.render(str(val), True, color)
            val_rect = val_surf.get_rect(center=(x + total_col_w // 2, table_y + 6))
            self.screen.blit(val_surf, val_rect)
            x += total_col_w
        
        # ホームチーム行
        table_y += 30
        home_name_short = home_team.name[:4]
        home_surf = fonts.small.render(home_name_short, True, home_color)
        self.screen.blit(home_surf, (score_rect.x + 8, table_y))
        
        x = score_rect.x + team_col_w + 8
        for i in range(min(num_innings, 12)):
            if i < len(innings_home):
                score_val = innings_home[i]
                score_text = str(score_val) if score_val != 'X' else 'X'
                score_color = Colors.WARNING if score_val not in [0, 'X'] else Colors.TEXT_SECONDARY
            else:
                score_text = "-"
                score_color = Colors.TEXT_MUTED
            score_surf = fonts.small.render(score_text, True, score_color)
            score_r = score_surf.get_rect(center=(x + inning_col_w // 2, table_y + 6))
            self.screen.blit(score_surf, score_r)
            x += inning_col_w
        
        # ホーム R/H/E - batting_resultsから集計
        home_hits = 0
        if hasattr(game_simulator, 'batting_results'):
            for key, stats in game_simulator.batting_results.items():
                if key[0] == home_team.name:
                    home_hits += stats.get('hits', 0)
        home_errors = 0
        for val, color in [(game_simulator.home_score, Colors.TEXT_PRIMARY), (home_hits, Colors.TEXT_SECONDARY), (home_errors, Colors.TEXT_SECONDARY)]:
            val_surf = fonts.body.render(str(val), True, color)
            val_rect = val_surf.get_rect(center=(x + total_col_w // 2, table_y + 6))
            self.screen.blit(val_surf, val_rect)
            x += total_col_w
        
        # === 勝敗結果 ===
        result_y = score_rect.bottom + 5
        if game_simulator.home_score > game_simulator.away_score:
            winner_text = f"◯ {home_team.name} WIN"
            winner_color = home_color
        elif game_simulator.away_score > game_simulator.home_score:
            winner_text = f"◯ {away_team.name} WIN"
            winner_color = away_color
        else:
            winner_text = "△ DRAW"
            winner_color = Colors.WARNING
        
        winner_surf = fonts.h3.render(winner_text, True, winner_color)
        winner_rect = winner_surf.get_rect(center=(center_x, result_y + 12))
        self.screen.blit(winner_surf, winner_rect)
        
        # === 投手成績（左側）・打撃成績（右側）===
        content_y = result_y + 35
        panel_h = height - content_y - 80
        panel_w = (width - 50) // 2
        
        # 投手成績パネル（スクロール対応）
        pitcher_card = Card(20, content_y, panel_w - 5, panel_h, "投手成績")
        pitcher_rect = pitcher_card.draw(self.screen)
        
        py = pitcher_rect.y + 42
        # ヘッダー
        pitcher_headers = [("投手", 90), ("結", 28), ("回", 32), ("安", 28), ("失", 28), ("自", 28), ("四", 28), ("振", 28), ("球", 32)]
        px = pitcher_rect.x + 8
        for hdr, w in pitcher_headers:
            h_surf = fonts.tiny.render(hdr, True, Colors.TEXT_MUTED)
            self.screen.blit(h_surf, (px, py))
            px += w
        py += 18
        
        # 投手データ（両チーム・pitching_resultsから取得）
        all_pitchers = []
        if hasattr(game_simulator, 'pitching_results'):
            for key, stats in game_simulator.pitching_results.items():
                team_name, pitcher_idx = key
                team = home_team if team_name == home_team.name else away_team
                if pitcher_idx < len(team.players):
                    pitcher = team.players[pitcher_idx]
                    all_pitchers.append((team, pitcher_idx, pitcher, stats))
        
        # 投手成績表示
        row_height = 22
        visible_pitcher_rows = (pitcher_rect.height - 80) // row_height
        for idx, (team, pitcher_idx, pitcher, pstats) in enumerate(all_pitchers[:visible_pitcher_rows]):
            px = pitcher_rect.x + 8
            # チーム色バー
            pygame.draw.rect(self.screen, self.get_team_color(team.name), 
                           (px, py + 2, 3, 16), border_radius=1)
            
            # 投手名
            p_name = f"{pitcher.name[:5]}"
            name_surf = fonts.small.render(p_name, True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_surf, (px + 6, py))
            px += 90
            
            # 勝敗判定
            result_mark = ""
            if hasattr(game_simulator, 'winning_pitcher') and game_simulator.winning_pitcher == pitcher_idx:
                result_mark = "○"
            elif hasattr(game_simulator, 'losing_pitcher') and game_simulator.losing_pitcher == pitcher_idx:
                result_mark = "●"
            elif hasattr(game_simulator, 'save_pitcher') and game_simulator.save_pitcher == pitcher_idx:
                result_mark = "S"
            
            ip = f"{pstats.get('ip', 0):.1f}"
            h = pstats.get('h', 0)
            r = pstats.get('r', 0)
            er = pstats.get('er', r)  # 自責点がなければ失点と同じ
            bb = pstats.get('bb', 0)
            so = pstats.get('so', 0)
            np = pstats.get('np', 0)
            
            for val, w in [(result_mark, 28), (ip, 32), (h, 28), (r, 28), (er, 28), (bb, 28), (so, 28), (np, 32)]:
                v_surf = fonts.small.render(str(val), True, Colors.TEXT_SECONDARY)
                self.screen.blit(v_surf, (px, py))
                px += w
            py += row_height
            
            if py > pitcher_rect.bottom - 30:
                break
        
        # 打撃成績パネル（スクロール対応）
        batting_card = Card(panel_w + 30, content_y, panel_w - 5, panel_h, "打撃成績")
        batting_rect = batting_card.draw(self.screen)
        
        by = batting_rect.y + 42
        # ヘッダー
        batting_headers = [("選手", 85), ("打", 28), ("安", 28), ("点", 28), ("本", 28), ("四", 28), ("三", 28)]
        bx = batting_rect.x + 8
        for hdr, w in batting_headers:
            h_surf = fonts.tiny.render(hdr, True, Colors.TEXT_MUTED)
            self.screen.blit(h_surf, (bx, by))
            bx += w
        by += 18
        
        # 全打撃データを収集（batting_resultsから取得）
        all_batters = []
        for team in [away_team, home_team]:
            lineup = team.current_lineup or []
            for i, player_idx in enumerate(lineup):
                if player_idx is None or player_idx < 0 or player_idx >= len(team.players):
                    continue
                player = team.players[player_idx]
                key = (team.name, player_idx)
                if hasattr(game_simulator, 'batting_results') and key in game_simulator.batting_results:
                    stats = game_simulator.batting_results[key]
                else:
                    stats = {'ab': 0, 'hits': 0, 'rbi': 0, 'hr': 0, 'bb': 0, 'so': 0}
                all_batters.append((team, player, i + 1, stats))
        
        # スクロール対応
        visible_rows = (batting_rect.height - 80) // row_height
        max_scroll = max(0, len(all_batters) - visible_rows)
        actual_scroll = min(scroll_offset, max_scroll)
        
        # クリッピング設定
        clip_rect = pygame.Rect(batting_rect.x, batting_rect.y + 60, batting_rect.width, batting_rect.height - 70)
        self.screen.set_clip(clip_rect)
        
        # 打撃データ表示
        for idx, (team, player, order, bstats) in enumerate(all_batters[actual_scroll:actual_scroll + visible_rows + 2]):
            if by > batting_rect.bottom - 20:
                break
            
            bx = batting_rect.x + 8
            
            # チーム色バー
            pygame.draw.rect(self.screen, self.get_team_color(team.name), 
                           (bx, by + 2, 3, 14), border_radius=1)
            
            # 選手名（打順付き）
            b_name = f"{order}.{player.name[:4]}"
            name_surf = fonts.small.render(b_name, True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_surf, (bx + 6, by))
            bx += 85
            
            ab = bstats.get('ab', 0)
            h = bstats.get('hits', 0)
            rbi = bstats.get('rbi', 0)
            hr = bstats.get('hr', 0)
            bb = bstats.get('bb', 0)
            so = bstats.get('so', 0)
            
            for i, (val, w) in enumerate([(ab, 28), (h, 28), (rbi, 28), (hr, 28), (bb, 28), (so, 28)]):
                # ヒット・打点・HRがある場合は強調
                if i in [1, 2, 3] and val > 0:
                    v_color = Colors.SUCCESS
                else:
                    v_color = Colors.TEXT_SECONDARY
                v_surf = fonts.small.render(str(val), True, v_color)
                self.screen.blit(v_surf, (bx, by))
                bx += w
            by += row_height
        
        self.screen.set_clip(None)
        
        # スクロールバー
        if len(all_batters) > visible_rows:
            scroll_track_h = batting_rect.height - 80
            scroll_h = max(20, int(scroll_track_h * visible_rows / len(all_batters)))
            scroll_y_pos = batting_rect.y + 60 + int((actual_scroll / max(1, max_scroll)) * (scroll_track_h - scroll_h))
            pygame.draw.rect(self.screen, Colors.BG_INPUT, 
                            (batting_rect.right - 12, batting_rect.y + 60, 6, scroll_track_h), border_radius=3)
            pygame.draw.rect(self.screen, Colors.PRIMARY, 
                            (batting_rect.right - 12, scroll_y_pos, 6, scroll_h), border_radius=3)
            
            # スクロールボタン
            if actual_scroll > 0:
                scroll_up_btn = Button(batting_rect.right - 35, batting_rect.y + 45, 25, 20, "▲", "ghost", font=fonts.tiny)
                scroll_up_btn.draw(self.screen)
                buttons["result_scroll_up"] = scroll_up_btn
            if actual_scroll < max_scroll:
                scroll_down_btn = Button(batting_rect.right - 35, batting_rect.bottom - 35, 25, 20, "▼", "ghost", font=fonts.tiny)
                scroll_down_btn.draw(self.screen)
                buttons["result_scroll_down"] = scroll_down_btn
        
        # ボタン
        buttons["next_game"] = Button(
            center_x - 80, height - 70, 160, 50,
            "次へ", "primary", font=fonts.h3
        )
        buttons["next_game"].draw(self.screen)
        
        buttons["back"] = Button(
            50, height - 65, 120, 45,
            "戻る", "ghost", font=fonts.body
        )
        buttons["back"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    # ========================================
    # 順位表画面（個人成績タブ付き）
    # ========================================
    def draw_standings_screen(self, central_teams: List, pacific_teams: List, player_team,
                              tab: str = "standings", scroll_offset: int = 0,
                              team_level_filter: str = "all") -> Dict[str, Button]:
        """順位表・個人成績画面を描画"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        
        header_h = draw_header(self.screen, "RECORDS")
        
        buttons = {}
        
        # タブ
        tabs = [
            ("standings", "順位表"),
            ("batting", "打撃成績"),
            ("pitching", "投手成績"),
        ]
        
        tab_y = header_h + 15
        tab_x = 30
        
        for tab_id, tab_name in tabs:
            style = "primary" if tab == tab_id else "ghost"
            btn = Button(tab_x, tab_y, 120, 38, tab_name, style, font=fonts.small)
            btn.draw(self.screen)
            buttons[f"standings_tab_{tab_id}"] = btn
            tab_x += 130
        
        # 軍別フィルタ（打撃成績・投手成績タブのみ - 全員削除、一軍/二軍/三軍のみ）
        if tab in ["batting", "pitching"]:
            filter_x = width - 240
            filters = [("first", "一軍"), ("second", "二軍"), ("third", "三軍")]
            for fid, fname in filters:
                style = "primary" if team_level_filter == fid else "outline"
                fbtn = Button(filter_x, tab_y, 70, 38, fname, style, font=fonts.tiny)
                fbtn.draw(self.screen)
                buttons[f"stats_filter_{fid}"] = fbtn
                filter_x += 75
        
        content_y = header_h + 65
        
        if tab == "standings":
            # 順位表タブ
            panel_width = (width - 80) // 2
            
            leagues = [
                ("セントラル・リーグ", central_teams, 30, Colors.PRIMARY),
                ("パシフィック・リーグ", pacific_teams, 30 + panel_width + 20, Colors.DANGER),
            ]
            
            for league_name, teams, panel_x, accent_color in leagues:
                sorted_teams = sorted(teams, key=lambda t: (-t.win_rate, -t.wins))
                
                panel_rect = pygame.Rect(panel_x, content_y, panel_width, height - content_y - 80)
                draw_rounded_rect(self.screen, panel_rect, Colors.BG_CARD, 16)
                draw_rounded_rect(self.screen, panel_rect, Colors.BG_CARD, 16, 1, Colors.BORDER)
                
                league_surf = fonts.h3.render(league_name, True, accent_color)
                league_rect = league_surf.get_rect(center=(panel_x + panel_width // 2, content_y + 30))
                self.screen.blit(league_surf, league_rect)
                
                headers = ["順", "チーム", "勝", "敗", "分", "率"]
                header_x = [15, 50, 200, 245, 290, 335]
                y = content_y + 55
                
                for i, header in enumerate(headers):
                    h_surf = fonts.tiny.render(header, True, Colors.TEXT_SECONDARY)
                    self.screen.blit(h_surf, (panel_x + header_x[i], y))
                
                y += 22
                pygame.draw.line(self.screen, Colors.BORDER,
                               (panel_x + 10, y), (panel_x + panel_width - 10, y), 1)
                y += 8
                
                for rank, team in enumerate(sorted_teams, 1):
                    row_rect = pygame.Rect(panel_x + 8, y - 3, panel_width - 16, 40)
                    
                    if player_team and team.name == player_team.name:
                        pygame.draw.rect(self.screen, (*accent_color[:3], 30), row_rect, border_radius=4)
                    
                    team_color = self.get_team_color(team.name)
                    
                    rank_color = Colors.GOLD if rank <= 3 else Colors.TEXT_SECONDARY
                    rank_surf = fonts.body.render(str(rank), True, rank_color)
                    self.screen.blit(rank_surf, (panel_x + header_x[0], y + 6))
                    
                    # チーム名を短縮
                    short_name = team.name[:6] if len(team.name) > 6 else team.name
                    name_surf = fonts.small.render(short_name, True, team_color)
                    self.screen.blit(name_surf, (panel_x + header_x[1], y + 8))
                    
                    wins_surf = fonts.small.render(str(team.wins), True, Colors.TEXT_PRIMARY)
                    self.screen.blit(wins_surf, (panel_x + header_x[2], y + 8))
                    
                    losses_surf = fonts.small.render(str(team.losses), True, Colors.TEXT_PRIMARY)
                    self.screen.blit(losses_surf, (panel_x + header_x[3], y + 8))
                    
                    ties_surf = fonts.small.render(str(team.draws), True, Colors.TEXT_PRIMARY)
                    self.screen.blit(ties_surf, (panel_x + header_x[4], y + 8))
                    
                    rate = f".{int(team.win_rate * 1000):03d}" if team.games_played > 0 else ".000"
                    rate_surf = fonts.small.render(rate, True, Colors.TEXT_PRIMARY)
                    self.screen.blit(rate_surf, (panel_x + header_x[5], y + 8))
                    
                    y += 42
        
        elif tab == "batting":
            # 打撃成績タブ
            self._draw_batting_leaders(central_teams + pacific_teams, player_team, 
                                       content_y, width, height, scroll_offset, buttons, team_level_filter)
        
        elif tab == "pitching":
            # 投手成績タブ
            self._draw_pitching_leaders(central_teams + pacific_teams, player_team,
                                        content_y, width, height, scroll_offset, buttons, team_level_filter)
        
        # 戻るボタン
        buttons["back"] = Button(
            50, height - 70, 150, 50,
            "← 戻る", "ghost", font=fonts.body
        )
        buttons["back"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    def _draw_batting_leaders(self, all_teams: List, player_team, content_y: int, 
                              width: int, height: int, scroll_offset: int, buttons: Dict,
                              team_level_filter: str = "first"):
        """打撃成績ランキングを描画（実績ベース）"""
        from models import TeamLevel
        
        # 軍別フィルタを適用（全員オプションを削除）
        def matches_filter(player):
            level = getattr(player, 'team_level', None)
            if team_level_filter == "first":
                return level == TeamLevel.FIRST or (level is None and not player.is_developmental)
            elif team_level_filter == "second":
                return level == TeamLevel.SECOND
            elif team_level_filter == "third":
                return level == TeamLevel.THIRD or player.is_developmental
            return level == TeamLevel.FIRST or (level is None and not player.is_developmental)  # デフォルトは一軍
        
        # 全選手を収集（野手のみ、規定打席以上、軍別フィルタ適用）
        all_batters = []
        for team in all_teams:
            for player in team.players:
                if player.position.value != "投手" and player.record.at_bats >= 10 and matches_filter(player):
                    all_batters.append((player, team.name))
        
        # 打撃タイトル別カード
        card_width = (width - 90) // 3
        
        titles = [
            ("打率ランキング", "avg", "打率"),
            ("本塁打ランキング", "hr", "本塁打"),
            ("打点ランキング", "rbi", "打点"),
        ]
        
        for i, (title, stat_type, stat_label) in enumerate(titles):
            card_x = 30 + i * (card_width + 15)
            card = Card(card_x, content_y, card_width, height - content_y - 80, title)
            card_rect = card.draw(self.screen)
            
            # 実績ベースでソート
            if stat_type == "avg":
                sorted_batters = sorted(all_batters, key=lambda x: -x[0].record.batting_average)
            elif stat_type == "hr":
                sorted_batters = sorted(all_batters, key=lambda x: -x[0].record.home_runs)
            else:
                sorted_batters = sorted(all_batters, key=lambda x: -x[0].record.rbis)
            
            y = card_rect.y + 50
            
            for rank, (player, team_name) in enumerate(sorted_batters[:10], 1):
                row_rect = pygame.Rect(card_rect.x + 10, y, card_rect.width - 20, 35)
                
                # 自チームハイライト
                if player_team and team_name == player_team.name:
                    pygame.draw.rect(self.screen, (*Colors.PRIMARY[:3], 30), row_rect, border_radius=4)
                
                # 順位
                rank_color = Colors.GOLD if rank <= 3 else Colors.TEXT_MUTED
                rank_surf = fonts.small.render(f"{rank}", True, rank_color)
                self.screen.blit(rank_surf, (row_rect.x + 5, y + 8))
                
                # 選手名
                name_surf = fonts.small.render(player.name[:5], True, Colors.TEXT_PRIMARY)
                self.screen.blit(name_surf, (row_rect.x + 30, y + 8))
                
                # チーム略称
                abbr = self.get_team_abbr(team_name)
                team_surf = fonts.tiny.render(abbr, True, Colors.TEXT_MUTED)
                self.screen.blit(team_surf, (row_rect.x + 100, y + 10))
                
                # 実績値表示
                if stat_type == "avg":
                    avg = player.record.batting_average
                    display_val = f".{int(avg * 1000):03d}" if avg > 0 else ".000"
                elif stat_type == "hr":
                    display_val = str(player.record.home_runs)
                else:
                    display_val = str(player.record.rbis)
                stat_surf = fonts.body.render(display_val, True, Colors.SUCCESS)
                stat_rect = stat_surf.get_rect(right=row_rect.right - 10, centery=y + 17)
                self.screen.blit(stat_surf, stat_rect)
                
                y += 38
    
    def _draw_pitching_leaders(self, all_teams: List, player_team, content_y: int,
                               width: int, height: int, scroll_offset: int, buttons: Dict,
                               team_level_filter: str = "first"):
        """投手成績ランキングを描画（実績ベース）"""
        from models import TeamLevel
        
        # 軍別フィルタを適用（全員オプションを削除）
        def matches_filter(player):
            level = getattr(player, 'team_level', None)
            if team_level_filter == "first":
                return level == TeamLevel.FIRST or (level is None and not player.is_developmental)
            elif team_level_filter == "second":
                return level == TeamLevel.SECOND
            elif team_level_filter == "third":
                return level == TeamLevel.THIRD or player.is_developmental
            return level == TeamLevel.FIRST or (level is None and not player.is_developmental)  # デフォルトは一軍
        
        # 全投手を収集（登板数1以上、軍別フィルタ適用）
        all_pitchers = []
        for team in all_teams:
            for player in team.players:
                if player.position.value == "投手" and player.record.innings_pitched >= 1 and matches_filter(player):
                    all_pitchers.append((player, team.name))
        
        card_width = (width - 90) // 3
        
        titles = [
            ("防御率ランキング", "era", "防御率"),
            ("奪三振ランキング", "k", "奪三振"),
            ("勝利数ランキング", "wins", "勝利"),
        ]
        
        for i, (title, stat_type, stat_label) in enumerate(titles):
            card_x = 30 + i * (card_width + 15)
            card = Card(card_x, content_y, card_width, height - content_y - 80, title)
            card_rect = card.draw(self.screen)
            
            # 実績ベースでソート
            if stat_type == "era":
                # 防御率は低い順、投球回5以上で
                qualified = [p for p in all_pitchers if p[0].record.innings_pitched >= 5]
                sorted_pitchers = sorted(qualified, key=lambda x: x[0].record.era if x[0].record.era > 0 else 99)
            elif stat_type == "k":
                sorted_pitchers = sorted(all_pitchers, key=lambda x: -x[0].record.strikeouts_pitched)
            else:
                sorted_pitchers = sorted(all_pitchers, key=lambda x: -x[0].record.wins)
            
            y = card_rect.y + 50
            
            for rank, (player, team_name) in enumerate(sorted_pitchers[:10], 1):
                row_rect = pygame.Rect(card_rect.x + 10, y, card_rect.width - 20, 35)
                
                if player_team and team_name == player_team.name:
                    pygame.draw.rect(self.screen, (*Colors.PRIMARY[:3], 30), row_rect, border_radius=4)
                
                rank_color = Colors.GOLD if rank <= 3 else Colors.TEXT_MUTED
                rank_surf = fonts.small.render(f"{rank}", True, rank_color)
                self.screen.blit(rank_surf, (row_rect.x + 5, y + 8))
                
                name_surf = fonts.small.render(player.name[:5], True, Colors.TEXT_PRIMARY)
                self.screen.blit(name_surf, (row_rect.x + 30, y + 8))
                
                abbr = self.get_team_abbr(team_name)
                team_surf = fonts.tiny.render(abbr, True, Colors.TEXT_MUTED)
                self.screen.blit(team_surf, (row_rect.x + 100, y + 10))
                
                # 実績値表示
                if stat_type == "era":
                    era = player.record.era
                    display_val = f"{era:.2f}" if era > 0 else "0.00"
                elif stat_type == "k":
                    display_val = str(player.record.strikeouts_pitched)
                else:
                    display_val = str(player.record.wins)
                stat_surf = fonts.body.render(display_val, True, Colors.SUCCESS)
                stat_rect = stat_surf.get_rect(right=row_rect.right - 10, centery=y + 17)
                self.screen.blit(stat_surf, stat_rect)
                
                y += 38

    # ========================================
    # スケジュール画面
    # ========================================
    def draw_schedule_screen(self, schedule_manager, player_team, scroll_offset: int = 0,
                               selected_game_idx: int = -1) -> Dict[str, Button]:
        """スケジュール画面を描画（NPB完全版）"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        
        team_color = self.get_team_color(player_team.name) if player_team else Colors.PRIMARY
        header_h = draw_header(self.screen, "SCHEDULE", player_team.name if player_team else "", team_color)
        
        buttons = {}
        
        if schedule_manager and player_team:
            games = schedule_manager.get_team_schedule(player_team.name)
            
            # 統計情報を計算
            completed_games = [g for g in games if g.is_completed]
            wins = sum(1 for g in completed_games if g.get_winner() == player_team.name)
            losses = sum(1 for g in completed_games if g.get_winner() and g.get_winner() != player_team.name)
            draws = sum(1 for g in completed_games if g.is_draw())
            
            # 左パネル: シーズン概要
            summary_card = Card(30, header_h + 20, 280, 200, "シーズン概要")
            summary_rect = summary_card.draw(self.screen)
            
            y = summary_rect.y + 55
            summary_items = [
                ("総試合数", f"{len(games)}試合"),
                ("消化試合", f"{len(completed_games)}試合"),
                ("残り試合", f"{len(games) - len(completed_games)}試合"),
                ("", ""),
                ("成績", f"{wins}勝 {losses}敗 {draws}分"),
            ]
            
            for label, value in summary_items:
                if label == "":
                    y += 10
                    continue
                label_surf = fonts.small.render(label, True, Colors.TEXT_SECONDARY)
                value_surf = fonts.small.render(value, True, Colors.TEXT_PRIMARY)
                self.screen.blit(label_surf, (summary_rect.x + 20, y))
                self.screen.blit(value_surf, (summary_rect.x + 130, y))
                y += 28
            
            # 左パネル: 直近の成績
            recent_card = Card(30, header_h + 235, 280, 200, "直近5試合")
            recent_rect = recent_card.draw(self.screen)
            
            recent_games = completed_games[-5:] if len(completed_games) >= 5 else completed_games
            y = recent_rect.y + 55
            
            if recent_games:
                for game in reversed(recent_games):
                    is_home = game.home_team_name == player_team.name
                    opponent = game.away_team_name if is_home else game.home_team_name
                    opponent_abbr = self.get_team_abbr(opponent)
                    
                    my_score = game.home_score if is_home else game.away_score
                    opp_score = game.away_score if is_home else game.home_score
                    
                    # 勝敗マーク
                    if my_score > opp_score:
                        result_mark = "○"
                        result_color = Colors.SUCCESS
                    elif my_score < opp_score:
                        result_mark = "●"
                        result_color = Colors.DANGER
                    else:
                        result_mark = "△"
                        result_color = Colors.WARNING
                    
                    mark_surf = fonts.body.render(result_mark, True, result_color)
                    self.screen.blit(mark_surf, (recent_rect.x + 20, y))
                    
                    vs_text = f"vs {opponent_abbr}"
                    vs_surf = fonts.small.render(vs_text, True, Colors.TEXT_SECONDARY)
                    self.screen.blit(vs_surf, (recent_rect.x + 50, y))
                    
                    score_text = f"{my_score}-{opp_score}"
                    score_surf = fonts.small.render(score_text, True, Colors.TEXT_PRIMARY)
                    self.screen.blit(score_surf, (recent_rect.x + 180, y))
                    
                    y += 28
            else:
                no_game_surf = fonts.small.render("まだ試合がありません", True, Colors.TEXT_MUTED)
                self.screen.blit(no_game_surf, (recent_rect.x + 20, y))
            
            # 右パネル: 全試合日程
            schedule_card = Card(330, header_h + 20, width - 360, height - header_h - 100, "試合日程一覧")
            schedule_rect = schedule_card.draw(self.screen)
            
            # ヘッダー
            headers = [("#", 40), ("日付", 90), ("対戦相手", 160), ("場所", 80), ("スコア", 100), ("結果", 60)]
            x = schedule_rect.x + 20
            y = schedule_rect.y + 50
            
            for header_text, w in headers:
                h_surf = fonts.tiny.render(header_text, True, Colors.TEXT_MUTED)
                self.screen.blit(h_surf, (x, y))
                x += w
            
            y += 25
            pygame.draw.line(self.screen, Colors.BORDER,
                           (schedule_rect.x + 15, y), (schedule_rect.right - 15, y), 1)
            y += 8
            
            # 試合一覧
            row_height = 32
            visible_count = (schedule_rect.height - 100) // row_height
            
            # 次の試合を探す
            next_game_idx = next((i for i, g in enumerate(games) if not g.is_completed), len(games))
            
            for i in range(scroll_offset, min(len(games), scroll_offset + visible_count)):
                game = games[i]
                
                row_rect = pygame.Rect(schedule_rect.x + 10, y - 3, schedule_rect.width - 20, row_height - 2)
                
                # 選択された日程をハイライト
                if i == selected_game_idx and not game.is_completed:
                    pygame.draw.rect(self.screen, (*Colors.GOLD[:3], 60), row_rect, border_radius=4)
                    pygame.draw.rect(self.screen, Colors.GOLD, row_rect, 2, border_radius=4)
                # 次の試合をハイライト
                elif i == next_game_idx:
                    pygame.draw.rect(self.screen, (*team_color[:3], 40), row_rect, border_radius=4)
                    pygame.draw.rect(self.screen, team_color, row_rect, 2, border_radius=4)
                elif i % 2 == 0:
                    pygame.draw.rect(self.screen, Colors.BG_INPUT, row_rect, border_radius=2)
                
                # 未完了の試合はクリック可能なボタンとして登録
                if not game.is_completed:
                    row_btn = Button(row_rect.x, row_rect.y, row_rect.width, row_rect.height, "", "ghost")
                    row_btn.color_normal = (0, 0, 0, 0)  # 透明
                    row_btn.color_hover = (*team_color[:3], 30)
                    buttons[f"select_game_{i}"] = row_btn
                
                x = schedule_rect.x + 20
                
                # 試合番号
                num_color = Colors.TEXT_PRIMARY if not game.is_completed else Colors.TEXT_MUTED
                num_surf = fonts.small.render(str(i + 1), True, num_color)
                self.screen.blit(num_surf, (x, y))
                x += 40
                
                # 日付
                date_str = f"{game.month}/{game.day}"
                date_color = Colors.TEXT_PRIMARY if not game.is_completed else Colors.TEXT_MUTED
                date_surf = fonts.small.render(date_str, True, date_color)
                self.screen.blit(date_surf, (x, y))
                x += 90
                
                # 対戦相手
                is_home = game.home_team_name == player_team.name
                opponent = game.away_team_name if is_home else game.home_team_name
                opp_color = self.get_team_color(opponent)
                opp_abbr = self.get_team_abbr(opponent)
                opp_surf = fonts.small.render(opp_abbr, True, opp_color if not game.is_completed else Colors.TEXT_MUTED)
                self.screen.blit(opp_surf, (x, y))
                x += 160
                
                # 場所
                if is_home:
                    loc_text = "HOME"
                    loc_color = Colors.SUCCESS
                else:
                    loc_text = "AWAY"
                    loc_color = Colors.WARNING
                if game.is_completed:
                    loc_color = Colors.TEXT_MUTED
                loc_surf = fonts.tiny.render(loc_text, True, loc_color)
                self.screen.blit(loc_surf, (x, y + 2))
                x += 80
                
                # スコア
                if game.is_completed:
                    my_score = game.home_score if is_home else game.away_score
                    opp_score = game.away_score if is_home else game.home_score
                    score_text = f"{my_score} - {opp_score}"
                    score_surf = fonts.small.render(score_text, True, Colors.TEXT_SECONDARY)
                    self.screen.blit(score_surf, (x, y))
                else:
                    if i == next_game_idx:
                        next_surf = fonts.tiny.render("NEXT", True, team_color)
                        self.screen.blit(next_surf, (x + 10, y + 2))
                    else:
                        pending_surf = fonts.small.render("- - -", True, Colors.TEXT_MUTED)
                        self.screen.blit(pending_surf, (x, y))
                x += 100
                
                # 結果
                if game.is_completed:
                    winner = game.get_winner()
                    if winner == player_team.name:
                        result_text = "勝ち"
                        result_color = Colors.SUCCESS
                    elif winner is None:
                        result_text = "引分"
                        result_color = Colors.WARNING
                    else:
                        result_text = "負け"
                        result_color = Colors.DANGER
                    result_surf = fonts.small.render(result_text, True, result_color)
                    self.screen.blit(result_surf, (x, y))
                
                y += row_height
                
                if y > schedule_rect.bottom - 20:
                    break
            
            # スクロールインジケーター
            if len(games) > visible_count:
                total_pages = (len(games) + visible_count - 1) // visible_count
                current_page = scroll_offset // visible_count + 1
                page_text = f"{current_page}/{total_pages} ページ (スクロールで移動)"
                page_surf = fonts.tiny.render(page_text, True, Colors.TEXT_MUTED)
                self.screen.blit(page_surf, (schedule_rect.x + 20, schedule_rect.bottom - 25))
        
        # ボタン
        buttons["back"] = Button(
            50, height - 70, 150, 50,
            "← 戻る", "ghost", font=fonts.body
        )
        buttons["back"].draw(self.screen)
        
        # 次の試合へジャンプボタン
        if schedule_manager and player_team:
            games = schedule_manager.get_team_schedule(player_team.name)
            next_idx = next((i for i, g in enumerate(games) if not g.is_completed), -1)
            if next_idx >= 0:
                buttons["jump_next"] = Button(
                    220, height - 70, 150, 50,
                    "NEXT GAME", "ghost", font=fonts.body
                )
                buttons["jump_next"].draw(self.screen)
                
                # 選択した日程までスキップボタン
                buttons["skip_to_date"] = Button(
                    390, height - 70, 200, 50,
                    "この日程まで進む", "primary", font=fonts.body
                )
                buttons["skip_to_date"].draw(self.screen)
                
                # ヒント
                hint_text = "日程をクリックして選択→「この日程まで進む」で試合をシミュレート"
                hint_surf = fonts.tiny.render(hint_text, True, Colors.TEXT_MUTED)
                self.screen.blit(hint_surf, (620, height - 55))
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    # ========================================
    # ドラフト画面
    # ========================================
    def draw_draft_screen(self, prospects: List, selected_idx: int = -1, 
                          draft_round: int = 1, draft_messages: List[str] = None,
                          scroll_offset: int = 0) -> Dict[str, Button]:
        """ドラフト画面を描画（スクロール対応）"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        center_x = width // 2
        
        # ヘッダーにラウンド表示
        round_text = f"第{draft_round}巡目"
        header_h = draw_header(self.screen, f"DRAFT - {round_text}", "有望な新人選手を獲得しよう")
        
        buttons = {}
        
        # 左側: 選手リストカード（高さを調整してはみ出し防止）
        card_width = width - 350 if draft_messages else width - 60
        card_height = height - header_h - 140  # ボタン用の余白を確保
        card = Card(30, header_h + 20, card_width - 30, card_height)
        card_rect = card.draw(self.screen)
        
        # ヘッダー
        headers = [("名前", 150), ("ポジション", 100), ("年齢", 60), ("ポテンシャル", 100), ("総合力", 80), ("", 50)]
        x = card_rect.x + 20
        y = card_rect.y + 20
        
        for header_text, w in headers:
            h_surf = fonts.small.render(header_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(h_surf, (x, y))
            x += w
        
        y += 25
        pygame.draw.line(self.screen, Colors.BORDER,
                       (card_rect.x + 15, y), (card_rect.right - 15, y), 1)
        y += 8
        
        # 表示可能な行数を動的に計算（はみ出し防止）
        row_height = 36
        available_height = card_rect.bottom - y - 20  # 余白を確保
        max_visible = available_height // row_height
        visible_count = min(max_visible, len(prospects) - scroll_offset)
        
        for i in range(scroll_offset, min(scroll_offset + visible_count, len(prospects))):
            prospect = prospects[i]
            display_i = i - scroll_offset  # 表示上のインデックス
            
            row_rect = pygame.Rect(card_rect.x + 10, y - 3, card_rect.width - 20, 34)
            
            # 選択中
            if i == selected_idx:
                pygame.draw.rect(self.screen, (*Colors.PRIMARY[:3], 50), row_rect, border_radius=5)
                pygame.draw.rect(self.screen, Colors.PRIMARY, row_rect, 2, border_radius=5)
            elif display_i % 2 == 0:
                pygame.draw.rect(self.screen, Colors.BG_INPUT, row_rect, border_radius=4)
            
            x = card_rect.x + 20
            
            # 名前
            name_surf = fonts.body.render(prospect.name[:10], True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_surf, (x, y + 3))
            x += 150
            
            # ポジション
            pos_text = prospect.position.value
            if prospect.pitch_type:
                pos_text += f" ({prospect.pitch_type.value[:2]})"
            pos_surf = fonts.small.render(pos_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(pos_surf, (x, y + 5))
            x += 100
            
            # 年齢
            age_surf = fonts.body.render(f"{prospect.age}歳", True, Colors.TEXT_PRIMARY)
            self.screen.blit(age_surf, (x, y + 3))
            x += 60
            
            # ポテンシャル
            pot_color = Colors.GOLD if prospect.potential >= 8 else (
                Colors.SUCCESS if prospect.potential >= 6 else Colors.TEXT_PRIMARY
            )
            pot_surf = fonts.body.render(f"{'★' * min(prospect.potential, 5)}", True, pot_color)
            self.screen.blit(pot_surf, (x, y + 3))
            x += 100
            
            # 総合力
            overall = prospect.stats.overall_batting() if prospect.position.value != "投手" else prospect.stats.overall_pitching()
            overall_surf = fonts.body.render(f"{overall:.0f}", True, Colors.TEXT_PRIMARY)
            self.screen.blit(overall_surf, (x, y + 3))
            x += 80
            
            # 詳細ボタン
            detail_btn = Button(x, y, 40, 28, "詳細", "outline", font=fonts.tiny)
            detail_btn.draw(self.screen)
            buttons[f"draft_detail_{i}"] = detail_btn
            
            y += 36  # 行高さを調整してはみ出し防止
        
        # スクロールバー
        if len(prospects) > 12:
            scroll_track_h = card_rect.height - 80
            scroll_h = max(30, int(scroll_track_h * 12 / len(prospects)))
            scroll_y = card_rect.y + 50 + int((scroll_offset / max(1, len(prospects) - 12)) * (scroll_track_h - scroll_h))
            pygame.draw.rect(self.screen, Colors.BG_INPUT, 
                           (card_rect.right - 15, card_rect.y + 50, 8, scroll_track_h), border_radius=4)
            pygame.draw.rect(self.screen, Colors.PRIMARY,
                           (card_rect.right - 15, scroll_y, 8, scroll_h), border_radius=4)
        
        # 右側: ドラフトログ（メッセージがある場合）
        if draft_messages:
            log_card = Card(width - 310, header_h + 20, 280, height - header_h - 130, "PICK LOG")
            log_rect = log_card.draw(self.screen)
            
            log_y = log_rect.y + 45
            # 最新10件を表示
            recent_msgs = draft_messages[-10:] if len(draft_messages) > 10 else draft_messages
            for msg in recent_msgs:
                msg_surf = fonts.small.render(msg[:35], True, Colors.TEXT_SECONDARY)
                self.screen.blit(msg_surf, (log_rect.x + 10, log_y))
                log_y += 22
        
        # ボタン
        btn_y = height - 90
        
        buttons["draft_player"] = Button(
            center_x + 50, btn_y, 200, 55,
            "この選手を指名", "success", font=fonts.body
        )
        buttons["draft_player"].enabled = selected_idx >= 0
        buttons["draft_player"].draw(self.screen)
        
        buttons["back"] = Button(
            50, btn_y, 150, 50,
            "ドラフト終了", "ghost", font=fonts.body
        )
        buttons["back"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    # ========================================
    # 育成ドラフト画面
    # ========================================
    def draw_ikusei_draft_screen(self, prospects: List, selected_idx: int = -1,
                                   draft_round: int = 1, draft_messages: List[str] = None,
                                   scroll_offset: int = 0) -> Dict[str, Button]:
        """育成ドラフト画面を描画（スクロール対応）"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        center_x = width // 2
        
        # ヘッダー
        round_text = f"第{draft_round}巡目"
        header_h = draw_header(self.screen, f"DEVELOPMENT DRAFT - {round_text}", "将来性のある選手を育成枠で獲得")
        
        buttons = {}
        
        # 説明カード
        info_card = Card(30, header_h + 10, 350, 50)
        info_rect = info_card.draw(self.screen)
        info_text = fonts.small.render("育成選手は背番号3桁で支配下登録枠外です", True, Colors.INFO)
        self.screen.blit(info_text, (info_rect.x + 15, info_rect.y + 15))
        
        # 選手リストカード
        card_width = width - 350 if draft_messages else width - 60
        card = Card(30, header_h + 70, card_width - 30, height - header_h - 180)
        card_rect = card.draw(self.screen)
        
        # ヘッダー
        headers = [("名前", 150), ("ポジション", 100), ("年齢", 60), ("伸びしろ", 100), ("総合力", 80), ("", 50)]
        x = card_rect.x + 20
        y = card_rect.y + 20
        
        for header_text, w in headers:
            h_surf = fonts.small.render(header_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(h_surf, (x, y))
            x += w
        
        y += 25
        pygame.draw.line(self.screen, Colors.BORDER,
                       (card_rect.x + 15, y), (card_rect.right - 15, y), 1)
        y += 8
        
        # 選手一覧（育成選手は少し能力が低め、スクロール対応）
        visible_count = min(12, len(prospects) - scroll_offset)
        
        for i in range(scroll_offset, min(scroll_offset + visible_count, len(prospects))):
            prospect = prospects[i]
            display_i = i - scroll_offset
            
            row_rect = pygame.Rect(card_rect.x + 10, y - 3, card_rect.width - 20, 34)
            
            # 選択中
            if i == selected_idx:
                pygame.draw.rect(self.screen, (*Colors.SUCCESS[:3], 50), row_rect, border_radius=5)
                pygame.draw.rect(self.screen, Colors.SUCCESS, row_rect, 2, border_radius=5)
            elif display_i % 2 == 0:
                pygame.draw.rect(self.screen, Colors.BG_INPUT, row_rect, border_radius=4)
            
            x = card_rect.x + 20
            
            # 名前（育成マーク）
            name_text = f"*{prospect.name[:9]}"
            name_surf = fonts.body.render(name_text, True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_surf, (x, y + 3))
            x += 150
            
            # ポジション
            pos_text = prospect.position.value
            if hasattr(prospect, 'pitch_type') and prospect.pitch_type:
                pos_text += f" ({prospect.pitch_type.value[:2]})"
            pos_surf = fonts.small.render(pos_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(pos_surf, (x, y + 5))
            x += 100
            
            # 年齢
            age_surf = fonts.body.render(f"{prospect.age}歳", True, Colors.TEXT_PRIMARY)
            self.screen.blit(age_surf, (x, y + 3))
            x += 60
            
            # 伸びしろ（潜在能力）
            growth = getattr(prospect, 'growth_potential', prospect.potential)
            growth_color = Colors.SUCCESS if growth >= 7 else (
                Colors.PRIMARY if growth >= 5 else Colors.TEXT_SECONDARY
            )
            growth_bar = "▰" * growth + "▱" * (10 - growth)
            growth_surf = fonts.small.render(growth_bar, True, growth_color)
            self.screen.blit(growth_surf, (x, y + 5))
            x += 100
            
            # 総合力（育成なので低め）
            if hasattr(prospect, 'potential_stats'):
                overall = prospect.potential_stats.overall_batting() if prospect.position.value != "投手" else prospect.potential_stats.overall_pitching()
            else:
                overall = 30  # デフォルト値
            overall_surf = fonts.body.render(f"{overall:.0f}", True, Colors.TEXT_SECONDARY)
            self.screen.blit(overall_surf, (x, y + 3))
            x += 80
            
            # 詳細ボタン
            detail_btn = Button(x, y, 40, 28, "詳細", "outline", font=fonts.tiny)
            detail_btn.draw(self.screen)
            buttons[f"ikusei_detail_{i}"] = detail_btn
            
            y += 38
        
        # スクロールバー
        if len(prospects) > 12:
            scroll_track_h = card_rect.height - 80
            scroll_h = max(30, int(scroll_track_h * 12 / len(prospects)))
            scroll_y = card_rect.y + 50 + int((scroll_offset / max(1, len(prospects) - 12)) * (scroll_track_h - scroll_h))
            pygame.draw.rect(self.screen, Colors.BG_INPUT, 
                           (card_rect.right - 15, card_rect.y + 50, 8, scroll_track_h), border_radius=4)
            pygame.draw.rect(self.screen, Colors.SUCCESS,
                           (card_rect.right - 15, scroll_y, 8, scroll_h), border_radius=4)
        
        # 右側: ドラフトログ
        if draft_messages:
            log_card = Card(width - 310, header_h + 70, 280, height - header_h - 180, "PICK LOG")
            log_rect = log_card.draw(self.screen)
            
            log_y = log_rect.y + 45
            recent_msgs = draft_messages[-10:] if len(draft_messages) > 10 else draft_messages
            for msg in recent_msgs:
                msg_surf = fonts.small.render(msg[:35], True, Colors.TEXT_SECONDARY)
                self.screen.blit(msg_surf, (log_rect.x + 10, log_y))
                log_y += 22
        
        # ボタン
        btn_y = height - 90
        
        buttons["draft_ikusei_player"] = Button(
            center_x + 50, btn_y, 200, 55,
            "この選手を指名", "success", font=fonts.body
        )
        buttons["draft_ikusei_player"].enabled = selected_idx >= 0
        buttons["draft_ikusei_player"].draw(self.screen)
        
        buttons["skip_ikusei"] = Button(
            center_x - 180, btn_y, 180, 50,
            "この巡はパス", "outline", font=fonts.body
        )
        buttons["skip_ikusei"].draw(self.screen)
        
        buttons["finish_ikusei_draft"] = Button(
            50, btn_y, 150, 50,
            "育成終了 →FA", "ghost", font=fonts.body
        )
        buttons["finish_ikusei_draft"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    # ========================================
    # 選手詳細画面（パワプロ風）
    # ========================================
    def draw_player_detail_screen(self, player, scroll_y: int = 0) -> Dict[str, Button]:
        """選手詳細画面を描画（パワプロ風の能力表示）"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        center_x = width // 2
        
        # ヘッダー
        header_h = draw_header(self.screen, f"{player.name}", f"{player.position.value} / {player.age}歳")
        
        buttons = {}
        
        # スクロール対応の描画領域を設定
        content_y = header_h + 20 - scroll_y
        
        # ========== 基本情報カード ==========
        info_card = Card(30, content_y, 400, 200, "基本情報")
        info_rect = info_card.draw(self.screen)
        
        # 総合力を計算
        overall = player.overall_rating
        overall_color = Colors.GOLD if overall >= 700 else Colors.SUCCESS if overall >= 500 else Colors.WARNING if overall >= 300 else Colors.TEXT_MUTED
        
        info_items = [
            ("背番号", f"#{player.uniform_number}", Colors.TEXT_PRIMARY),
            ("ポジション", player.position.value, Colors.TEXT_PRIMARY),
            ("年齢", f"{player.age}歳", Colors.TEXT_PRIMARY),
            ("投打", f"{getattr(player.stats, 'throwing_hand', '右')}投{getattr(player.stats, 'batting_hand', '右')}打", Colors.TEXT_PRIMARY),
            ("総合力", f"★{overall}", overall_color),
        ]
        
        y = info_rect.y + 45
        for label, value, color in info_items:
            label_surf = fonts.small.render(f"{label}:", True, Colors.TEXT_SECONDARY)
            value_surf = fonts.body.render(str(value), True, color)
            self.screen.blit(label_surf, (info_rect.x + 20, y))
            self.screen.blit(value_surf, (info_rect.x + 120, y))
            y += 32
        
        # ========== 打撃能力カード ==========
        if player.position.value != "投手":
            batting_card = Card(450, content_y, 400, 250, "BATTING")
            batting_rect = batting_card.draw(self.screen)
            
            # 能力値を100スケールに変換
            batting_stats = [
                ("ミート", player.stats.to_100_scale(player.stats.contact), Colors.INFO),
                ("パワー", player.stats.to_100_scale(player.stats.power), Colors.DANGER),
                ("走力", player.stats.to_100_scale(player.stats.run), Colors.SUCCESS),
                ("肩力", player.stats.to_100_scale(player.stats.throwing if hasattr(player.stats, 'throwing') else player.stats.arm), Colors.WARNING),
                ("守備", player.stats.to_100_scale(player.stats.fielding), Colors.PRIMARY),
                ("捕球", player.stats.to_100_scale(getattr(player.stats, 'catching', player.stats.fielding)), Colors.GOLD),
            ]
            
            y = batting_rect.y + 45
            for stat_name, value, color in batting_stats:
                # ラベル
                label_surf = fonts.small.render(stat_name, True, Colors.TEXT_SECONDARY)
                self.screen.blit(label_surf, (batting_rect.x + 20, y + 3))
                
                # バー
                bar_x = batting_rect.x + 80
                bar_width = 200
                bar_height = 18
                
                # 背景バー
                pygame.draw.rect(self.screen, Colors.BG_INPUT, 
                               (bar_x, y, bar_width, bar_height), border_radius=3)
                
                # 値バー
                filled_width = int(bar_width * value / 100)
                if filled_width > 0:
                    pygame.draw.rect(self.screen, color,
                                   (bar_x, y, filled_width, bar_height), border_radius=3)
                
                # ランク表示（数値なし）
                rank = player.stats.get_rank(value)
                rank_color = player.stats.get_rank_color(value)
                rank_surf = fonts.body.render(rank, True, rank_color)
                self.screen.blit(rank_surf, (batting_rect.right - 40, y))
                
                y += 30
        
        # ========== 投球能力カード（投手の場合）==========
        if player.position.value == "投手":
            pitching_card = Card(450, content_y, 400, 250, "PITCHING")
            pitching_rect = pitching_card.draw(self.screen)
            
            # 能力値を0-99スケールで表示、球速はkm/hで表示
            speed_kmh = player.stats.speed_to_kmh()
            pitching_stats = [
                (f"球速 ({speed_kmh}km)", player.stats.speed, Colors.DANGER),
                ("コントロール", player.stats.control, Colors.INFO),
                ("スタミナ", player.stats.stamina, Colors.SUCCESS),
                ("変化球", player.stats.breaking, Colors.PRIMARY),
                ("キレ", getattr(player.stats, 'movement', player.stats.breaking), Colors.WARNING),
            ]
            
            y = pitching_rect.y + 45
            for stat_name, value, color in pitching_stats:
                label_surf = fonts.small.render(stat_name, True, Colors.TEXT_SECONDARY)
                self.screen.blit(label_surf, (pitching_rect.x + 20, y + 3))
                
                bar_x = pitching_rect.x + 100
                bar_width = 180
                bar_height = 18
                
                pygame.draw.rect(self.screen, Colors.BG_INPUT,
                               (bar_x, y, bar_width, bar_height), border_radius=3)
                
                filled_width = int(bar_width * value / 100)
                if filled_width > 0:
                    pygame.draw.rect(self.screen, color,
                                   (bar_x, y, filled_width, bar_height), border_radius=3)
                
                # ランク表示（数値なし）
                rank = player.stats.get_rank(value)
                rank_color = player.stats.get_rank_color(value)
                rank_surf = fonts.body.render(rank, True, rank_color)
                self.screen.blit(rank_surf, (pitching_rect.right - 40, y))
                
                y += 35
        
        # ========== 守備適正カード（野手のみ） ==========
        if player.position.value != "投手":
            fielding_y = content_y + 260
            from models import Position
            fielding_card = Card(30, fielding_y, 400, 200, "守備適正")
            fielding_rect = fielding_card.draw(self.screen)
            
            # 守備位置リスト
            positions = [
                (Position.CATCHER, "捕手"),
                (Position.FIRST, "一塁"),
                (Position.SECOND, "二塁"),
                (Position.THIRD, "三塁"),
                (Position.SHORTSTOP, "遊撃"),
                (Position.OUTFIELD, "外野"),
            ]
            
            y = fielding_rect.y + 40
            for pos, pos_name in positions:
                # 適正値を取得（メインポジション=99、サブは保存された値から、それ以外は0）
                if player.position == pos:
                    apt_value = 99
                elif pos in getattr(player, 'sub_positions', []):
                    # 0.0-1.0を1-99に変換
                    rating = player.sub_position_ratings.get(pos.value, 0.7)
                    apt_value = int(rating * 99)
                else:
                    apt_value = 0
                
                # ランクを計算
                rank = self._get_ability_rank(apt_value) if apt_value > 0 else "-"
                rank_color = self._get_rank_color(rank) if apt_value > 0 else Colors.TEXT_MUTED
                
                # ポジション名
                pos_surf = fonts.small.render(pos_name, True, Colors.TEXT_SECONDARY)
                self.screen.blit(pos_surf, (fielding_rect.x + 20, y))
                
                # 適正値
                if apt_value > 0:
                    value_surf = fonts.small.render(str(apt_value), True, Colors.TEXT_PRIMARY)
                    self.screen.blit(value_surf, (fielding_rect.x + 100, y))
                else:
                    value_surf = fonts.small.render("-", True, Colors.TEXT_MUTED)
                    self.screen.blit(value_surf, (fielding_rect.x + 100, y))
                
                # ランク
                rank_surf = fonts.body.render(rank, True, rank_color)
                self.screen.blit(rank_surf, (fielding_rect.x + 150, y))
                
                y += 26
            
            abilities_y = content_y + 470  # 特殊能力カードを下に
        else:
            abilities_y = content_y + 260
        
        # ========== 特殊能力カード（パワプロ式） ==========
        from special_abilities import SpecialAbility, SpecialAbilityType
        special_card = Card(30, abilities_y, width - 60, 180, "✨ 特殊能力")
        special_rect = special_card.draw(self.screen)
        
        # 選手の特殊能力を取得
        player_abilities = getattr(player, 'special_abilities', None)
        ability_list = player_abilities.abilities if player_abilities else []
        
        # パワプロ風表示（青能力と赤能力を分けて表示）
        positive_abilities = [a for a in ability_list if a.effect_value > 0]
        negative_abilities = [a for a in ability_list if a.effect_value < 0]
        
        x = special_rect.x + 20
        y = special_rect.y + 40
        
        # 青能力（プラス）
        if positive_abilities:
            for ability in positive_abilities:
                # パワプロ風の青いバッジ
                text_surf = fonts.small.render(ability.display_name, True, Colors.WHITE)
                text_w = text_surf.get_width()
                badge_rect = pygame.Rect(x, y, text_w + 20, 26)
                pygame.draw.rect(self.screen, Colors.INFO, badge_rect, border_radius=4)
                self.screen.blit(text_surf, (x + 10, y + 5))
                x += text_w + 28
                
                if x > special_rect.right - 100:
                    x = special_rect.x + 20
                    y += 32
        
        # 赤能力（マイナス）
        if negative_abilities:
            if positive_abilities and x != special_rect.x + 20:
                x = special_rect.x + 20
                y += 32
            for ability in negative_abilities:
                # パワプロ風の赤いバッジ
                text_surf = fonts.small.render(ability.display_name, True, Colors.WHITE)
                text_w = text_surf.get_width()
                badge_rect = pygame.Rect(x, y, text_w + 20, 26)
                pygame.draw.rect(self.screen, Colors.DANGER, badge_rect, border_radius=4)
                self.screen.blit(text_surf, (x + 10, y + 5))
                x += text_w + 28
                
                if x > special_rect.right - 100:
                    x = special_rect.x + 20
                    y += 32
        
        # 特殊能力がない場合
        if not positive_abilities and not negative_abilities:
            no_ability = fonts.small.render("特殊能力なし", True, Colors.TEXT_SECONDARY)
            self.screen.blit(no_ability, (special_rect.x + 20, special_rect.y + 55))
        
        # 戻るボタン
        buttons["back"] = Button(
            50, height - 80, 150, 50,
            "← 戻る", "ghost", font=fonts.body
        )
        buttons["back"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    def _get_ability_rank(self, value: int) -> str:
        """能力値をランクに変換"""
        if value >= 90:
            return "S"
        elif value >= 80:
            return "A"
        elif value >= 70:
            return "B"
        elif value >= 60:
            return "C"
        elif value >= 50:
            return "D"
        elif value >= 40:
            return "E"
        elif value >= 30:
            return "F"
        else:
            return "G"
    
    def _get_rank_color(self, rank: str):
        """ランクに応じた色を返す"""
        colors = {
            "S": Colors.GOLD,
            "A": Colors.DANGER,
            "B": Colors.WARNING,
            "C": Colors.SUCCESS,
            "D": Colors.INFO,
            "E": Colors.TEXT_SECONDARY,
            "F": Colors.TEXT_SECONDARY,
            "G": Colors.TEXT_SECONDARY,
        }
        return colors.get(rank, Colors.TEXT_PRIMARY)
    
    # ========================================
    # 外国人FA画面
    # ========================================
    def draw_free_agent_screen(self, player_team, free_agents: List, selected_idx: int = -1) -> Dict[str, Button]:
        """外国人FA画面を描画"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        center_x = width // 2
        
        team_color = self.get_team_color(player_team.name) if player_team else Colors.PRIMARY
        header_h = draw_header(self.screen, "外国人選手市場", 
                               f"予算: {player_team.budget if player_team else 0}億円", team_color)
        
        buttons = {}
        
        # 選手リストカード
        card = Card(30, header_h + 20, width - 60, height - header_h - 130)
        card_rect = card.draw(self.screen)
        
        # ヘッダー
        headers = [("名前", 180), ("ポジション", 120), ("年俸", 100), ("総合力", 100)]
        x = card_rect.x + 25
        y = card_rect.y + 25
        
        for header_text, w in headers:
            h_surf = fonts.small.render(header_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(h_surf, (x, y))
            x += w
        
        y += 30
        pygame.draw.line(self.screen, Colors.BORDER,
                       (card_rect.x + 20, y), (card_rect.right - 20, y), 1)
        y += 10
        
        # 選手一覧（行をクリック可能にするためrect情報を保存）
        self.fa_row_rects = []
        for i, player in enumerate(free_agents[:10]):
            row_rect = pygame.Rect(card_rect.x + 15, y - 5, card_rect.width - 30, 38)
            self.fa_row_rects.append(row_rect)
            
            # 選択中の行はハイライト
            if i == selected_idx:
                pygame.draw.rect(self.screen, (*Colors.PRIMARY[:3], 60), row_rect, border_radius=4)
                pygame.draw.rect(self.screen, Colors.PRIMARY, row_rect, 2, border_radius=4)
            elif i % 2 == 0:
                pygame.draw.rect(self.screen, Colors.BG_INPUT, row_rect, border_radius=4)
            
            x = card_rect.x + 25
            
            # 名前
            name_surf = fonts.body.render(player.name[:12], True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_surf, (x, y + 5))
            x += 180
            
            # ポジション
            pos_text = player.position.value
            if player.pitch_type:
                pos_text += f" ({player.pitch_type.value[:2]})"
            pos_surf = fonts.body.render(pos_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(pos_surf, (x, y + 5))
            x += 120
            
            # 年俸
            salary_surf = fonts.body.render(f"{player.salary}億", True, Colors.WARNING)
            self.screen.blit(salary_surf, (x, y + 5))
            x += 100
            
            # 総合力
            overall = player.stats.overall_batting() if player.position.value != "投手" else player.stats.overall_pitching()
            overall_surf = fonts.body.render(f"{overall:.0f}", True, Colors.TEXT_PRIMARY)
            self.screen.blit(overall_surf, (x, y + 5))
            
            y += 42
        
        # ボタン行
        btn_y = height - 90
        
        # 獲得ボタン
        sign_style = "primary" if selected_idx >= 0 else "ghost"
        buttons["sign_fa"] = Button(
            center_x - 200, btn_y, 180, 50,
            "SIGN", sign_style, font=fonts.body
        )
        buttons["sign_fa"].draw(self.screen)
        
        # 次へボタン（新シーズン開始）
        buttons["next_season"] = Button(
            center_x + 20, btn_y, 180, 50,
            "NEW SEASON", "success", font=fonts.body
        )
        buttons["next_season"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    # ========================================
    # 設定画面
    # ========================================
    def draw_settings_screen(self, settings_obj, settings_tab: str = "display", scroll_offset: int = 0) -> Dict[str, Button]:
        """設定画面を描画
        
        Args:
            settings_obj: 設定オブジェクト
            settings_tab: 表示するタブ ("display", "game_rules")
            scroll_offset: スクロールオフセット
        """
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        center_x = width // 2
        
        header_h = draw_header(self.screen, "SETTINGS")
        
        buttons = {}
        
        card_top = header_h + 30
        content_height = height - card_top - 100  # 利用可能な高さ
        
        # 表示設定カード（タブなしで直接表示）
        card = Card(center_x - 400, card_top, 800, 450, "画面設定")
        card_rect = card.draw(self.screen)
        
        y = card_rect.y + 55
        
        # 画面サイズ設定
        res_label = fonts.h3.render("画面サイズ", True, Colors.TEXT_PRIMARY)
        self.screen.blit(res_label, (card_rect.x + 30, y))
        y += 45
        
        resolutions = [(1280, 720), (1600, 900), (1920, 1080)]
        for i, (w, h) in enumerate(resolutions):
            btn_x = card_rect.x + 30 + i * 200
            is_current = (settings_obj.screen_width, settings_obj.screen_height) == (w, h)
            style = "primary" if is_current else "ghost"
            
            btn = Button(btn_x, y, 180, 45, f"{w}x{h}", style, font=fonts.body)
            btn.draw(self.screen)
            buttons[f"resolution_{w}x{h}"] = btn
        
        y += 75
        
        # 画質設定
        quality_label = fonts.h3.render("画質", True, Colors.TEXT_PRIMARY)
        self.screen.blit(quality_label, (card_rect.x + 30, y))
        y += 45
        
        current_quality = getattr(settings_obj, 'graphics_quality', 'medium')
        quality_options = [("low", "低"), ("medium", "中"), ("high", "高")]
        for i, (qkey, qlabel) in enumerate(quality_options):
            btn_x = card_rect.x + 30 + i * 150
            is_current = current_quality == qkey
            style = "primary" if is_current else "ghost"
            
            btn = Button(btn_x, y, 130, 45, qlabel, style, font=fonts.body)
            btn.draw(self.screen)
            buttons[f"quality_{qkey}"] = btn
        
        y += 75
        
        # フルスクリーン
        fullscreen_label = fonts.h3.render("フルスクリーン", True, Colors.TEXT_PRIMARY)
        self.screen.blit(fullscreen_label, (card_rect.x + 30, y))
        
        fullscreen_status = "ON" if settings_obj.fullscreen else "OFF"
        fullscreen_style = "success" if settings_obj.fullscreen else "ghost"
        buttons["toggle_fullscreen"] = Button(
            card_rect.x + 350, y - 5, 120, 45,
            fullscreen_status, fullscreen_style, font=fonts.body
        )
        buttons["toggle_fullscreen"].draw(self.screen)
        
        y += 70
        
        # サウンド
        sound_label = fonts.h3.render("サウンド", True, Colors.TEXT_PRIMARY)
        self.screen.blit(sound_label, (card_rect.x + 30, y))
        
        sound_status = "ON" if settings_obj.sound_enabled else "OFF"
        sound_style = "success" if settings_obj.sound_enabled else "ghost"
        buttons["toggle_sound"] = Button(
            card_rect.x + 350, y - 5, 120, 45,
            sound_status, sound_style, font=fonts.body
        )
        buttons["toggle_sound"].draw(self.screen)
        
        # 戻るボタン
        buttons["back"] = Button(
            50, height - 70, 150, 50,
            "← 戻る", "ghost", font=fonts.body
        )
        buttons["back"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons

    # ========================================
    # チーム成績画面
    # ========================================
    def draw_team_stats_screen(self, player_team, current_year: int) -> Dict[str, Button]:
        """チーム成績詳細画面を描画"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        
        team_color = self.get_team_color(player_team.name) if player_team else Colors.PRIMARY
        
        header_h = draw_header(self.screen, f"{player_team.name} 成績",
                               f"{current_year}年シーズン", team_color)
        
        buttons = {}
        
        if player_team:
            # 左パネル: チーム基本情報
            basic_card = Card(30, header_h + 20, 350, 450, "シーズン成績")
            basic_rect = basic_card.draw(self.screen)
            
            y = basic_rect.y + 55
            
            # 本拠地球場
            stadium = NPB_STADIUMS.get(player_team.name, {})
            stadium_name = stadium.get("name", "不明")
            stadium_capacity = stadium.get("capacity", 0)
            
            # チーム基本情報
            info_items = [
                ("本拠地", stadium_name),
                ("収容人数", f"{stadium_capacity:,}人" if stadium_capacity > 0 else "不明"),
                ("", ""),  # 空行
                ("勝利", f"{player_team.wins}"),
                ("敗北", f"{player_team.losses}"),
                ("引分", f"{player_team.draws}"),
                ("", ""),  # 空行
                ("勝率", f".{int(player_team.win_rate * 1000):03d}" if player_team.games_played > 0 else ".000"),
                ("消化試合", f"{player_team.games_played}/143"),
                ("残り試合", f"{143 - player_team.games_played}"),
            ]
            
            for label, value in info_items:
                if label == "":
                    y += 15
                    continue
                label_surf = fonts.body.render(label, True, Colors.TEXT_SECONDARY)
                value_surf = fonts.body.render(value, True, Colors.TEXT_PRIMARY)
                self.screen.blit(label_surf, (basic_rect.x + 25, y))
                self.screen.blit(value_surf, (basic_rect.x + 160, y))
                y += 32
            
            # シーズン進行バー
            y += 10
            progress = player_team.games_played / 143 if player_team.games_played > 0 else 0
            bar = ProgressBar(basic_rect.x + 25, y, 300, 18, progress, team_color)
            bar.draw(self.screen)
            
            # 中央パネル: 打撃成績上位
            batting_card = Card(400, header_h + 20, 360, 320, "🏏 打撃成績上位")
            bat_rect = batting_card.draw(self.screen)
            
            # 打者をフィルタ
            batters = [p for p in player_team.players if p.position.value != "投手"]
            # 打率でソート（仮の計算）
            sorted_batters = sorted(batters, 
                                   key=lambda p: p.stats.contact + p.stats.power + p.stats.speed, 
                                   reverse=True)[:6]
            
            y = bat_rect.y + 55
            headers = ["選手", "打率", "本", "打点"]
            header_x = [25, 150, 230, 280]
            
            for i, h in enumerate(headers):
                h_surf = fonts.tiny.render(h, True, Colors.TEXT_MUTED)
                self.screen.blit(h_surf, (bat_rect.x + header_x[i], y))
            
            y += 28
            
            for player in sorted_batters:
                # 選手名
                name_surf = fonts.small.render(player.name[:10], True, Colors.TEXT_PRIMARY)
                self.screen.blit(name_surf, (bat_rect.x + header_x[0], y))
                
                # 仮のシーズン成績（実際のゲームでは累積する）
                avg = 0.220 + (player.stats.contact / 1000)
                hr = int(player.stats.power / 5)
                rbi = int((player.stats.power + player.stats.contact) / 4)
                
                avg_surf = fonts.small.render(f".{int(avg * 1000):03d}", True, Colors.TEXT_SECONDARY)
                self.screen.blit(avg_surf, (bat_rect.x + header_x[1], y))
                
                hr_surf = fonts.small.render(str(hr), True, Colors.TEXT_SECONDARY)
                self.screen.blit(hr_surf, (bat_rect.x + header_x[2], y))
                
                rbi_surf = fonts.small.render(str(rbi), True, Colors.TEXT_SECONDARY)
                self.screen.blit(rbi_surf, (bat_rect.x + header_x[3], y))
                
                y += 32
            
            # 投手成績
            pitching_card = Card(400, header_h + 360, 360, 180, "PITCHING TOP")
            pitch_rect = pitching_card.draw(self.screen)
            
            pitchers = [p for p in player_team.players if p.position.value == "投手"]
            sorted_pitchers = sorted(pitchers,
                                    key=lambda p: p.stats.overall_pitching(),
                                    reverse=True)[:3]
            
            y = pitch_rect.y + 55
            p_headers = ["選手", "防御率", "勝", "負", "S"]
            p_header_x = [25, 130, 205, 245, 285]
            
            for i, h in enumerate(p_headers):
                h_surf = fonts.tiny.render(h, True, Colors.TEXT_MUTED)
                self.screen.blit(h_surf, (pitch_rect.x + p_header_x[i], y))
            
            y += 28
            
            for player in sorted_pitchers:
                name_surf = fonts.small.render(player.name[:8], True, Colors.TEXT_PRIMARY)
                self.screen.blit(name_surf, (pitch_rect.x + p_header_x[0], y))
                
                # 仮のシーズン成績
                era = 5.00 - (player.stats.control / 50) - (player.stats.stamina / 100)
                era = max(1.50, min(6.00, era))
                wins = int(player.stats.control / 10)
                losses = max(0, 10 - wins)
                saves = 0 if player.pitch_type and player.pitch_type.value != "クローザー" else int(player.stats.control / 5)
                
                era_surf = fonts.small.render(f"{era:.2f}", True, Colors.TEXT_SECONDARY)
                self.screen.blit(era_surf, (pitch_rect.x + p_header_x[1], y))
                
                w_surf = fonts.small.render(str(wins), True, Colors.TEXT_SECONDARY)
                self.screen.blit(w_surf, (pitch_rect.x + p_header_x[2], y))
                
                l_surf = fonts.small.render(str(losses), True, Colors.TEXT_SECONDARY)
                self.screen.blit(l_surf, (pitch_rect.x + p_header_x[3], y))
                
                s_surf = fonts.small.render(str(saves), True, Colors.TEXT_SECONDARY)
                self.screen.blit(s_surf, (pitch_rect.x + p_header_x[4], y))
                
                y += 28
            
            # 右パネル: タイトル候補
            title_card = Card(780, header_h + 20, 330, 520, "TITLE RACE")
            title_rect = title_card.draw(self.screen)
            
            y = title_rect.y + 55
            
            # 打撃タイトル
            bat_title_label = fonts.small.render("【打撃部門】", True, Colors.GOLD)
            self.screen.blit(bat_title_label, (title_rect.x + 20, y))
            y += 30
            
            for title_key, title_name in list(NPB_BATTING_TITLES.items())[:4]:
                title_surf = fonts.tiny.render(f"・{title_name}", True, Colors.TEXT_SECONDARY)
                self.screen.blit(title_surf, (title_rect.x + 30, y))
                
                # 最有力候補（チーム内）
                if sorted_batters:
                    candidate = sorted_batters[0]
                    cand_surf = fonts.tiny.render(f"→ {candidate.name[:6]}", True, Colors.TEXT_MUTED)
                    self.screen.blit(cand_surf, (title_rect.x + 170, y))
                y += 25
            
            y += 20
            
            # 投手タイトル
            pitch_title_label = fonts.small.render("【投手部門】", True, Colors.SECONDARY)
            self.screen.blit(pitch_title_label, (title_rect.x + 20, y))
            y += 30
            
            for title_key, title_name in list(NPB_PITCHING_TITLES.items())[:4]:
                title_surf = fonts.tiny.render(f"・{title_name}", True, Colors.TEXT_SECONDARY)
                self.screen.blit(title_surf, (title_rect.x + 30, y))
                
                if sorted_pitchers:
                    candidate = sorted_pitchers[0]
                    cand_surf = fonts.tiny.render(f"→ {candidate.name[:6]}", True, Colors.TEXT_MUTED)
                    self.screen.blit(cand_surf, (title_rect.x + 170, y))
                y += 25
        
        # 戻るボタン
        buttons["back"] = Button(
            50, height - 70, 150, 50,
            "← 戻る", "ghost", font=fonts.body
        )
        buttons["back"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons

    # ========================================
    # チーム作成画面
    # ========================================
    def draw_team_create_screen(self, team_name: str = "", league: str = "central", 
                                  color_idx: int = 0, gen_mode: str = "random") -> Dict[str, Button]:
        """新規チーム作成画面を描画"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        
        header_h = draw_header(self.screen, "チーム作成", 
                               "新しいチームを作成します")
        
        buttons = {}
        
        # メインカード
        card_width = min(700, width - 60)
        card_x = (width - card_width) // 2
        main_card = Card(card_x, header_h + 20, card_width, height - header_h - 100, "チーム情報")
        card_rect = main_card.draw(self.screen)
        
        y = card_rect.y + 55
        
        # チーム名入力
        name_label = fonts.body.render("チーム名:", True, Colors.TEXT_PRIMARY)
        self.screen.blit(name_label, (card_rect.x + 30, y))
        
        name_rect = pygame.Rect(card_rect.x + 150, y - 5, 400, 35)
        pygame.draw.rect(self.screen, Colors.BG_INPUT, name_rect, border_radius=4)
        pygame.draw.rect(self.screen, Colors.BORDER, name_rect, 1, border_radius=4)
        
        name_surf = fonts.body.render(team_name if team_name else "チーム名を入力", 
                                      True, Colors.TEXT_PRIMARY if team_name else Colors.TEXT_MUTED)
        self.screen.blit(name_surf, (name_rect.x + 10, name_rect.y + 8))
        
        y += 60
        
        # リーグ選択
        league_label = fonts.body.render("所属リーグ:", True, Colors.TEXT_PRIMARY)
        self.screen.blit(league_label, (card_rect.x + 30, y))
        
        central_style = "primary" if league == 'central' else "ghost"
        central_btn = Button(card_rect.x + 150, y - 5, 150, 35, "セ・リーグ", central_style, font=fonts.body)
        central_btn.draw(self.screen)
        buttons["team_league_central"] = central_btn
        
        pacific_style = "primary" if league == 'pacific' else "ghost"
        pacific_btn = Button(card_rect.x + 320, y - 5, 150, 35, "パ・リーグ", pacific_style, font=fonts.body)
        pacific_btn.draw(self.screen)
        buttons["team_league_pacific"] = pacific_btn
        
        y += 60
        
        # チームカラー選択
        color_label = fonts.body.render("チームカラー:", True, Colors.TEXT_PRIMARY)
        self.screen.blit(color_label, (card_rect.x + 30, y))
        
        colors_list = [
            ("赤", (220, 50, 50)),
            ("青", (50, 100, 220)),
            ("緑", (50, 180, 50)),
            ("黄", (255, 220, 50)),
            ("紫", (180, 50, 220)),
            ("橙", (255, 180, 0)),
            ("シアン", (50, 180, 180)),
            ("ピンク", (255, 100, 150)),
            ("灰", (100, 100, 100)),
        ]
        
        for i, (color_name, color_value) in enumerate(colors_list):
            btn_x = card_rect.x + 150 + (i % 5) * 70
            btn_y = y - 2 + (i // 5) * 40
            color_rect = pygame.Rect(btn_x, btn_y, 55, 30)
            
            is_selected = (i == color_idx)
            pygame.draw.rect(self.screen, color_value, color_rect, border_radius=4)
            if is_selected:
                pygame.draw.rect(self.screen, Colors.TEXT_PRIMARY, color_rect, 3, border_radius=4)
            
            color_btn = Button(btn_x, btn_y, 55, 30, "", "ghost", font=fonts.tiny)
            buttons[f"team_color_{i}"] = color_btn
        
        y += 90
        
        # 生成モード選択
        gen_label = fonts.body.render("生成モード:", True, Colors.TEXT_PRIMARY)
        self.screen.blit(gen_label, (card_rect.x + 30, y))
        
        random_style = "primary" if gen_mode == 'random' else "ghost"
        random_btn = Button(card_rect.x + 150, y - 5, 150, 35, "ランダム生成", random_style, font=fonts.body)
        random_btn.draw(self.screen)
        buttons["team_gen_random"] = random_btn
        random_btn.draw(self.screen)
        buttons["team_gen_random"] = random_btn
        
        y += 60
        
        # 説明テキスト
        desc_text = "※ チームを作成すると、指定したリーグに追加されます"
        desc_surf = fonts.small.render(desc_text, True, Colors.TEXT_MUTED)
        self.screen.blit(desc_surf, (card_rect.x + 30, y))
        
        y += 25
        desc_text2 = "※ 選手は自動で生成されます"
        desc_surf2 = fonts.small.render(desc_text2, True, Colors.TEXT_MUTED)
        self.screen.blit(desc_surf2, (card_rect.x + 30, y))
        
        # 下部ボタン
        btn_y = height - 70
        
        # 戻るボタン
        back_btn = Button(50, btn_y, 150, 50, "← 戻る", "ghost", font=fonts.body)
        back_btn.draw(self.screen)
        buttons["create_team_cancel"] = back_btn
        
        # 作成ボタン
        create_btn = Button(width - 200, btn_y, 150, 50, "作成", "primary", font=fonts.body)
        create_btn.draw(self.screen)
        buttons["create_team_confirm"] = create_btn
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons

    # ========================================
    # チーム編集画面
    # ========================================
    def draw_team_edit_screen(self, all_teams: List, editing_team_idx: int = -1, 
                               input_text: str = "", custom_names: Dict = None) -> Dict[str, Button]:
        """チーム名編集画面を描画"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        
        header_h = draw_header(self.screen, "チーム名編集", 
                               "各チームの名前をカスタマイズできます")
        
        buttons = {}
        custom_names = custom_names or {}
        
        # メインカード
        card_width = min(900, width - 60)
        card_x = (width - card_width) // 2
        main_card = Card(card_x, header_h + 20, card_width, height - header_h - 100, "チーム一覧")
        card_rect = main_card.draw(self.screen)
        
        # ヘッダー行
        y = card_rect.y + 55
        headers = [("リーグ", 80), ("デフォルト名", 220), ("カスタム名", 250), ("操作", 120)]
        x = card_rect.x + 25
        
        for header_text, col_width in headers:
            header_surf = fonts.small.render(header_text, True, Colors.TEXT_MUTED)
            self.screen.blit(header_surf, (x, y))
            x += col_width
        
        y += 35
        pygame.draw.line(self.screen, Colors.BORDER,
                        (card_rect.x + 20, y - 5),
                        (card_rect.x + card_width - 40, y - 5), 1)
        
        # チーム一覧
        for idx, team in enumerate(all_teams):
            row_y = y + idx * 45
            if row_y > card_rect.y + card_rect.height - 50:
                break
            
            # 編集中のチームをハイライト
            if idx == editing_team_idx:
                highlight_rect = pygame.Rect(card_rect.x + 15, row_y - 5, card_width - 50, 40)
                pygame.draw.rect(self.screen, (*Colors.PRIMARY[:3], 30), highlight_rect, border_radius=4)
            
            x = card_rect.x + 25
            
            # リーグ
            league_text = "セ" if idx < 6 else "パ"
            league_color = Colors.PRIMARY if idx < 6 else Colors.DANGER
            league_surf = fonts.body.render(league_text, True, league_color)
            self.screen.blit(league_surf, (x + 20, row_y))
            x += 80
            
            # デフォルト名
            team_color = self.get_team_color(team.name)
            default_name_surf = fonts.body.render(team.name[:12], True, team_color)
            self.screen.blit(default_name_surf, (x, row_y))
            x += 220
            
            # カスタム名（入力中 or 設定済み）
            if idx == editing_team_idx:
                # 入力ボックス
                input_rect = pygame.Rect(x, row_y - 3, 200, 32)
                pygame.draw.rect(self.screen, Colors.BG_INPUT, input_rect, border_radius=4)
                pygame.draw.rect(self.screen, Colors.PRIMARY, input_rect, 2, border_radius=4)
                
                display_text = input_text if input_text else "入力してください..."
                text_color = Colors.TEXT_PRIMARY if input_text else Colors.TEXT_MUTED
                input_surf = fonts.body.render(display_text[:14], True, text_color)
                self.screen.blit(input_surf, (x + 8, row_y + 2))
                
                # カーソル（点滅）
                if int(time.time() * 2) % 2 == 0:
                    cursor_x = x + 8 + fonts.body.size(input_text[:14])[0]
                    pygame.draw.line(self.screen, Colors.TEXT_PRIMARY,
                                   (cursor_x, row_y), (cursor_x, row_y + 24), 2)
            else:
                custom_name = custom_names.get(team.name, "")
                if custom_name:
                    custom_surf = fonts.body.render(custom_name[:14], True, Colors.SUCCESS)
                    self.screen.blit(custom_surf, (x, row_y))
                else:
                    no_custom_surf = fonts.body.render("---", True, Colors.TEXT_MUTED)
                    self.screen.blit(no_custom_surf, (x, row_y))
            
            x += 250
            
            # 編集ボタン
            if idx == editing_team_idx:
                # 確定・キャンセルボタン
                confirm_btn = Button(x, row_y - 5, 50, 32, "OK", "success", font=fonts.small)
                confirm_btn.draw(self.screen)
                buttons[f"confirm_edit_{idx}"] = confirm_btn
                
                cancel_btn = Button(x + 55, row_y - 5, 50, 32, "✖", "danger", font=fonts.small)
                cancel_btn.draw(self.screen)
                buttons[f"cancel_edit_{idx}"] = cancel_btn
            else:
                edit_btn = Button(x, row_y - 5, 70, 32, "編集", "ghost", font=fonts.small)
                edit_btn.draw(self.screen)
                buttons[f"edit_team_{idx}"] = edit_btn
                
                # リセットボタン（カスタム名がある場合）
                if team.name in custom_names:
                    reset_btn = Button(x + 75, row_y - 5, 45, 32, "X", "ghost", font=fonts.small)
                    reset_btn.draw(self.screen)
                    buttons[f"reset_team_{idx}"] = reset_btn
        
        # 下部ボタン
        buttons["back_to_select"] = Button(
            50, height - 70, 150, 50,
            "← 戻る", "ghost", font=fonts.body
        )
        buttons["back_to_select"].draw(self.screen)
        
        buttons["apply_names"] = Button(
            width - 200, height - 70, 150, 50,
            "適用して選択へ", "primary", font=fonts.body
        )
        buttons["apply_names"].draw(self.screen)
        
        # ヒント
        hint_text = "チーム名を変更すると、ゲーム内のすべての表示に反映されます"
        hint_surf = fonts.tiny.render(hint_text, True, Colors.TEXT_MUTED)
        self.screen.blit(hint_surf, ((width - hint_surf.get_width()) // 2, height - 25))
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons

    # ========================================
    # 育成画面
    # ========================================
    def draw_training_screen(self, player_team, selected_player_idx: int = -1,
                              training_points: int = 0,
                              selected_training_idx: int = -1,
                              player_scroll: int = 0,
                              filter_position: Optional[str] = None,
                              training_menus: dict = None,
                              training_days_remaining: int = 0) -> Dict[str, Button]:
        """育成画面を描画（日数経過でXP獲得システム）
        
        XPシステムを使った本格的な育成機能。
        日数経過で経験値が入り、メニュー未設定時は自動設定。
        """
        if training_menus is None:
            training_menus = {}
        
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        
        team_color = self.get_team_color(player_team.name) if player_team else Colors.PRIMARY
        menus_set = len(training_menus)
        total_players = len(player_team.players) if player_team else 0
        header_h = draw_header(self.screen, "育成", f"メニュー設定: {menus_set}/{total_players}人 - 日を進めて選手を鍛えよう！", team_color)
        
        buttons = {}
        
        if not player_team:
            return buttons
        
        # レイアウト
        gutter = 15
        left_w = min(340, int(width * 0.28))
        right_w = min(380, int(width * 0.30))
        mid_w = width - left_w - right_w - gutter * 4

        left_x = gutter
        mid_x = left_x + left_w + gutter
        right_x = mid_x + mid_w + gutter

        content_h = height - header_h - 80

        # ========== 左パネル: 選手一覧 ==========
        left_card = Card(left_x, header_h + 15, left_w, content_h, "選手一覧")
        left_rect = left_card.draw(self.screen)
        self._training_player_list_rect = left_rect

        # ポジションフィルターボタン
        pos_y = left_rect.y + 45
        positions = [("全員", "ALL"), ("投", "P"), ("捕", "C"), ("内", "INF"), ("外", "OF")]
        pos_btn_w = (left_rect.width - 30) // len(positions)
        for i, (label, key) in enumerate(positions):
            bx = left_rect.x + 10 + i * pos_btn_w
            style = "primary" if filter_position == key or (filter_position is None and key == "ALL") else "ghost"
            btn = Button(bx, pos_y, pos_btn_w - 4, 28, label, style, font=fonts.tiny)
            btn.draw(self.screen)
            buttons[f"training_filter_pos_{key}"] = btn

        # ポジションでフィルタリング
        all_players = player_team.players if player_team else []
        def pos_filter(ply, flt):
            if not flt or flt == "ALL":
                return True
            if flt == "P":
                return ply.position.name == 'PITCHER'
            if flt == "C":
                return ply.position.name == 'CATCHER'
            if flt == "INF":
                return ply.position.name in ['FIRST', 'SECOND', 'THIRD', 'SHORTSTOP']
            if flt == "OF":
                return ply.position.name == 'OUTFIELD'
            return True

        filtered_players = [p for p in all_players if pos_filter(p, filter_position)]
        self._training_filtered_players = filtered_players

        # Helper: return training option definitions for a given player (used to show assigned menu labels)
        def training_options_for(ply):
            if ply is None:
                return []
            if ply.position.name == 'PITCHER':
                return [
                    ("投球練習", "PITCHING", "球速", "speed", (4, 9), 50, Colors.DANGER),
                    ("制球練習", "CONTROL", "制球", "control", (4, 9), 40, Colors.PRIMARY),
                    ("変化球", "BREAKING", "変化球", "breaking", (4, 9), 45, Colors.WARNING),
                    ("スタミナ", "STAMINA", "スタミナ", "stamina", (4, 9), 35, Colors.SUCCESS),
                ]
            else:
                return [
                    ("打撃練習", "BATTING", "ミート", "contact", (4, 9), 40, Colors.PRIMARY),
                    ("筋力トレ", "POWER", "パワー", "power", (4, 9), 50, Colors.DANGER),
                    ("走塁練習", "RUNNING", "走力", "run", (3, 7), 35, Colors.SUCCESS),
                    ("守備練習", "FIELDING", "守備", "fielding", (3, 7), 40, Colors.WARNING),
                    ("スタミナ", "STAMINA", "スタミナ", "stamina", (4, 9), 35, Colors.SUCCESS),
                ]

        # 選手リストヘッダー
        list_header_y = pos_y + 38
        pygame.draw.line(self.screen, Colors.BORDER, 
                        (left_rect.x + 10, list_header_y), 
                        (left_rect.right - 10, list_header_y), 1)
        
        headers = [("名前", 0), ("Pos", 100), ("年", 145), ("総合", 175)]
        for h_text, h_x in headers:
            h_surf = fonts.tiny.render(h_text, True, Colors.TEXT_MUTED)
            self.screen.blit(h_surf, (left_rect.x + 15 + h_x, list_header_y + 5))

        # 選手リスト
        list_y = list_header_y + 28
        row_h = 36
        visible_count = max(5, (left_rect.bottom - list_y - 10) // row_h)
        self._training_visible_players = visible_count
        self._training_max_scroll = max(0, len(filtered_players) - visible_count)

        for i in range(visible_count):
            idx = i + player_scroll
            if idx >= len(filtered_players):
                break
            player = filtered_players[idx]
            ry = list_y + i * row_h
            row_rect = pygame.Rect(left_rect.x + 8, ry, left_rect.width - 16, row_h - 4)

            # 選択ハイライト
            if idx == selected_player_idx:
                pygame.draw.rect(self.screen, (*team_color[:3], 60), row_rect, border_radius=6)
                pygame.draw.rect(self.screen, team_color, row_rect, 2, border_radius=6)
            elif i % 2 == 0:
                pygame.draw.rect(self.screen, Colors.BG_INPUT, row_rect, border_radius=4)

            row_btn = Button(row_rect.x, row_rect.y, row_rect.width, row_rect.height, "", "ghost")
            buttons[f"training_select_player_{idx}"] = row_btn

            # 選手情報
            name_color = Colors.TEXT_PRIMARY if idx == selected_player_idx else Colors.TEXT_SECONDARY
            name_s = fonts.small.render(player.name[:7], True, name_color)
            self.screen.blit(name_s, (row_rect.x + 8, row_rect.y + 8))

            pos_s = fonts.tiny.render(player.position.value[:2], True, Colors.TEXT_MUTED)
            self.screen.blit(pos_s, (row_rect.x + 105, row_rect.y + 10))

            age_s = fonts.tiny.render(str(player.age), True, Colors.TEXT_MUTED)
            self.screen.blit(age_s, (row_rect.x + 148, row_rect.y + 10))

            # 総合力
            try:
                overall_val = int(getattr(player, 'overall_rating', 0))
            except Exception:
                overall_val = 0
            overall_s = fonts.tiny.render(f"★{overall_val}", True, Colors.TEXT_MUTED)
            # place overall to the left of menu label area to avoid overlap
            self.screen.blit(overall_s, (row_rect.right - 100, row_rect.y + 10))

            # Show assigned menu label for this player (if any)
            try:
                actual_player_idx = all_players.index(player) if player in all_players else -1
            except Exception:
                actual_player_idx = -1
            if actual_player_idx in training_menus:
                m_idx = training_menus.get(actual_player_idx, -1)
                opts = training_options_for(player)
                if 0 <= m_idx < len(opts):
                    menu_label = opts[m_idx][2]
                else:
                    menu_label = "設定済"
                menu_s = fonts.tiny.render(menu_label, True, Colors.TEXT_MUTED)
                # align menu label at the far right
                self.screen.blit(menu_s, (row_rect.right - 18 - menu_s.get_width(), row_rect.y + 10))

        # ========== 中央パネル: 育成メニュー ==========
        mid_card = Card(mid_x, header_h + 15, mid_w, content_h, "育成メニュー")
        mid_rect = mid_card.draw(self.screen)
        self._training_menu_rect = mid_rect

        # 育成オプション（選手のポジションで分岐）- キャンプと同じ構成
        if 0 <= selected_player_idx < len(filtered_players):
            sel_p = filtered_players[selected_player_idx]
            if sel_p.position.name == 'PITCHER':
                training_options = [
                    ("投球練習", "PITCHING", "球速", "speed", (4, 9), 50, Colors.DANGER),
                    ("制球練習", "CONTROL", "制球", "control", (4, 9), 40, Colors.PRIMARY),
                    ("変化球", "BREAKING", "変化球", "breaking", (4, 9), 45, Colors.WARNING),
                    ("スタミナ", "STAMINA", "スタミナ", "stamina", (4, 9), 35, Colors.SUCCESS),
                ]
            else:
                training_options = [
                    ("打撃練習", "BATTING", "ミート", "contact", (4, 9), 40, Colors.PRIMARY),
                    ("筋力トレ", "POWER", "パワー", "power", (4, 9), 50, Colors.DANGER),
                    ("走塁練習", "RUNNING", "走力", "run", (3, 7), 35, Colors.SUCCESS),
                    ("守備練習", "FIELDING", "守備", "fielding", (3, 7), 40, Colors.WARNING),
                    ("スタミナ", "STAMINA", "スタミナ", "stamina", (4, 9), 35, Colors.SUCCESS),
                ]
        else:
            training_options = [
                ("打撃練習", "BATTING", "ミート", "contact", (4, 9), 40, Colors.PRIMARY),
                ("筋力トレ", "POWER", "パワー", "power", (4, 9), 50, Colors.DANGER),
                ("走塁練習", "RUNNING", "走力", "run", (3, 7), 35, Colors.SUCCESS),
                ("守備練習", "FIELDING", "守備", "fielding", (3, 7), 40, Colors.WARNING),
            ]

        btn_w = (mid_rect.width - 40) // 2
        btn_h = 55
        t_y = mid_rect.y + 50

        # Get actual player index in all_players for checking training_menus
        actual_player_idx = -1
        if 0 <= selected_player_idx < len(filtered_players):
            sel_p = filtered_players[selected_player_idx]
            try:
                actual_player_idx = all_players.index(sel_p)
            except ValueError:
                actual_player_idx = selected_player_idx
            # Check if this player already has a menu set
            player_has_menu = actual_player_idx in training_menus
            current_menu_idx = training_menus.get(actual_player_idx, -1)
        else:
            player_has_menu = False
            current_menu_idx = -1

        for i, (label, key, effect, stat_key, xp_range, cost, color) in enumerate(training_options):
            col = i % 2
            row = i // 2
            tx = mid_rect.x + 15 + col * (btn_w + 10)
            ty = t_y + row * (btn_h + 8)

            is_selected = (i == selected_training_idx) or (i == current_menu_idx)
            style = "primary" if is_selected else "ghost"
            
            tbtn = Button(tx, ty, btn_w, btn_h, "", style)
            tbtn.draw(self.screen)
            buttons[f"training_option_{i}"] = tbtn

            label_color = Colors.TEXT_PRIMARY if is_selected else color
            label_s = fonts.body.render(label, True, label_color)
            self.screen.blit(label_s, (tx + 12, ty + 8))

            effect_text = f"{effect} +XP({xp_range[0]}~{xp_range[1]})"
            effect_s = fonts.tiny.render(effect_text, True, Colors.TEXT_MUTED)
            self.screen.blit(effect_s, (tx + 12, ty + 30))
            
            # Show checkmark if this menu is set for current player
            if i == current_menu_idx:
                check_s = fonts.tiny.render("✓設定済", True, Colors.SUCCESS)
                self.screen.blit(check_s, (tx + btn_w - 55, ty + 8))

        # プレビューパネル
        preview_y = t_y + 3 * (btn_h + 8) + 20
        pygame.draw.line(self.screen, Colors.BORDER,
                        (mid_rect.x + 15, preview_y - 10),
                        (mid_rect.right - 15, preview_y - 10), 1)

        preview_title = fonts.small.render("効果プレビュー", True, Colors.TEXT_PRIMARY)
        self.screen.blit(preview_title, (mid_rect.x + 15, preview_y))

        if 0 <= selected_training_idx < len(training_options) and 0 <= selected_player_idx < len(filtered_players):
            sel_training = training_options[selected_training_idx]
            sel_player = filtered_players[selected_player_idx]
            
            preview_lines = []
            stat_key = sel_training[3]
            xp_range = sel_training[4]
            cost = sel_training[5]
            
            if stat_key and sel_player.growth:
                cur_val = getattr(sel_player.stats, stat_key, 50)
                cur_xp = sel_player.growth.xp.get(stat_key, 0)
                req_xp = sel_player.growth.xp_required_for(cur_val)
                avg_gain = (xp_range[0] + xp_range[1]) // 2
                
                preview_lines.append(f"対象: {sel_training[2]} (現在値: {cur_val})")
                preview_lines.append(f"獲得XP: {xp_range[0]}～{xp_range[1]} (平均{avg_gain})")
                preview_lines.append(f"現在XP: {cur_xp} / 必要XP: {req_xp}")
                
                if cur_xp + avg_gain >= req_xp:
                    preview_lines.append(f"→ 能力UP期待大！ ({sel_training[2]}+1)")

            py = preview_y + 25
            for line in preview_lines:
                line_s = fonts.tiny.render(line, True, Colors.TEXT_SECONDARY)
                self.screen.blit(line_s, (mid_rect.x + 20, py))
                py += 20
        else:
            hint_s = fonts.tiny.render("選手と育成メニューを選択してください", True, Colors.TEXT_MUTED)
            self.screen.blit(hint_s, (mid_rect.x + 20, preview_y + 30))

        # ヒント: プレイヤーをクリックしてから育成メニューをクリックすると、
        # その選手のメニューを即座に設定します（従来の「メニューを設定」/「日を進める」ボタンは廃止）。
        hint_text = "プレイヤーを選択→メニューをクリックで即設定されます。"
        hint_s = fonts.tiny.render(hint_text, True, Colors.TEXT_MUTED)
        self.screen.blit(hint_s, (mid_rect.x + 20, mid_rect.bottom - 140))

        # AI Auto-set menu button
        auto_btn = Button(
            mid_rect.x + 15, mid_rect.bottom - 100,
            mid_rect.width - 30, 40,
            " 自動メニュー設定",
            "ghost",
            font=fonts.body
        )
        auto_btn.draw(self.screen)
        buttons["training_auto_menu"] = auto_btn
        
        # メニュークリアボタン
        clear_btn = Button(
            mid_rect.x + 15, mid_rect.bottom - 55,
            mid_rect.width - 30, 40,
            "メニュー全クリア",
            "ghost",
            font=fonts.body
        )
        clear_btn.draw(self.screen)
        buttons["training_clear_menu"] = clear_btn

        # ========== 右パネル: 選手詳細 ==========
        detail_card = Card(right_x, header_h + 15, right_w, content_h, "選手詳細")
        detail_rect = detail_card.draw(self.screen)
        self._training_detail_rect = detail_rect

        if 0 <= selected_player_idx < len(filtered_players):
            sel = filtered_players[selected_player_idx]
            sx = detail_rect.x + 15
            sy = detail_rect.y + 45

            name_s = fonts.h2.render(sel.name, True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_s, (sx, sy))
            sy += 32

            # ポテンシャル表示
            potential = sel.growth.potential if sel.growth else 5
            pot_stars = "★" * (potential // 2) + "☆" * (5 - potential // 2)
            pos_text = f"{sel.position.value} / {sel.age}歳 / {pot_stars}"
            pos_s = fonts.small.render(pos_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(pos_s, (sx, sy))
            sy += 30

            pygame.draw.line(self.screen, Colors.BORDER,
                            (sx, sy), (detail_rect.right - 15, sy), 1)
            sy += 12

            # 能力値とXPバー
            if sel.position.name == 'PITCHER':
                stat_items = [
                    ("球速", "speed", Colors.DANGER),
                    ("制球", "control", Colors.PRIMARY),
                    ("変化球", "breaking", Colors.WARNING),
                    ("スタミナ", "stamina", Colors.SUCCESS),
                ]
            else:
                stat_items = [
                    ("ミート", "contact", Colors.PRIMARY),
                    ("パワー", "power", Colors.DANGER),
                    ("走力", "run", Colors.SUCCESS),
                    ("守備", "fielding", Colors.WARNING),
                    ("スタミナ", "stamina", Colors.SUCCESS),
                ]

            bar_w = detail_rect.width - 100

            for stat_name, stat_key, stat_color in stat_items:
                val = getattr(sel.stats, stat_key, 50)
                xp = sel.growth.xp.get(stat_key, 0) if sel.growth else 0
                req = sel.growth.xp_required_for(val) if sel.growth else 100

                # 球速は km/h 表示
                if stat_key == "speed" and sel.position.name == 'PITCHER':
                    display_name = f"球速 ({sel.stats.speed_to_kmh()}km)"
                else:
                    display_name = stat_name

                label_s = fonts.small.render(display_name, True, Colors.TEXT_SECONDARY)
                self.screen.blit(label_s, (sx, sy))
                
                val_s = fonts.small.render(str(val), True, stat_color)
                self.screen.blit(val_s, (sx + 120, sy))

                bar_rect = pygame.Rect(sx, sy + 22, bar_w, 10)
                pygame.draw.rect(self.screen, Colors.BG_INPUT, bar_rect, border_radius=5)
                fill_w = int(bar_w * min(val, 99) / 99)
                fill_rect = pygame.Rect(sx, sy + 22, fill_w, 10)
                pygame.draw.rect(self.screen, stat_color, fill_rect, border_radius=5)

                xp_bar_rect = pygame.Rect(sx, sy + 34, bar_w, 6)
                pygame.draw.rect(self.screen, Colors.BG_INPUT, xp_bar_rect, border_radius=3)
                xp_fill_w = int(bar_w * min(xp, req) / max(1, req))
                xp_fill_rect = pygame.Rect(sx, sy + 34, xp_fill_w, 6)
                pygame.draw.rect(self.screen, Colors.GOLD, xp_fill_rect, border_radius=3)

                xp_text = f"XP: {xp}/{req}"
                xp_s = fonts.tiny.render(xp_text, True, Colors.TEXT_MUTED)
                self.screen.blit(xp_s, (sx + bar_w + 5, sy + 28))

                sy += 48
        else:
            hint_y = detail_rect.y + detail_rect.height // 2 - 30
            hint_s = fonts.body.render("← 選手を選択", True, Colors.TEXT_MUTED)
            hint_rect = hint_s.get_rect(center=(detail_rect.centerx, hint_y))
            self.screen.blit(hint_s, hint_rect)

            hint2_s = fonts.small.render("してください", True, Colors.TEXT_MUTED)
            hint2_rect = hint2_s.get_rect(center=(detail_rect.centerx, hint_y + 30))
            self.screen.blit(hint2_s, hint2_rect)

        # ========== 下部ボタン ==========
        buttons["back"] = Button(
            gutter, height - 60, 140, 45,
            "← 戻る", "ghost", font=fonts.body
        )
        buttons["back"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons

    def draw_spring_camp_screen(self, player_team, selected_player_idx: int = -1,
                                filter_position: Optional[str] = None,
                                selected_training_idx: int = -1,
                                player_scroll: int = 0,
                                hovered_training_idx: int = -1,
                                camp_day: int = 1,
                                max_camp_days: int = 30,
                                selected_menus: dict = None) -> Dict[str, Button]:
        """春季キャンプ画面：3分割レイアウト（改善版）

        左: 選手一覧（ポジションで絞り込み＋スクロール＋メニュー設定状態表示）
        中央: 練習メニュー（ホバーで効果プレビュー）＋日にちを進めるボタン
        右: 選択中選手の詳細（能力＋XPバー＋状態）
        
        Args:
            selected_menus: dict mapping player index -> training menu index
        """
        if selected_menus is None:
            selected_menus = {}
        
        draw_background(self.screen, "gradient")

        width = self.screen.get_width()
        height = self.screen.get_height()
        team_color = self.get_team_color(player_team.name) if player_team else Colors.PRIMARY
        
        # Count how many players have menus set
        all_players_count = len(player_team.players) if player_team else 0
        menus_set_count = len(selected_menus)
        header_h = draw_header(self.screen, "春季キャンプ", f"Day {camp_day}/{max_camp_days} - メニュー設定: {menus_set_count}/{all_players_count}人", team_color)

        buttons: Dict[str, Button] = {}

        # Layout columns - responsive
        gutter = 15
        left_w = min(320, int(width * 0.25))
        right_w = min(380, int(width * 0.30))
        mid_w = width - left_w - right_w - gutter * 4

        left_x = gutter
        mid_x = left_x + left_w + gutter
        right_x = mid_x + mid_w + gutter

        content_h = height - header_h - 80

        # ========== 左パネル: 選手一覧 ==========
        left_card = Card(left_x, header_h + 15, left_w, content_h, "選手一覧")
        left_rect = left_card.draw(self.screen)
        self._spring_camp_player_list_rect = left_rect

        # Position filter buttons (horizontal)
        pos_y = left_rect.y + 45
        positions = [("全員", "ALL"), ("投", "P"), ("捕", "C"), ("内", "INF"), ("外", "OF")]
        pos_btn_w = (left_rect.width - 30) // len(positions)
        for i, (label, key) in enumerate(positions):
            bx = left_rect.x + 10 + i * pos_btn_w
            style = "primary" if filter_position == key or (filter_position is None and key == "ALL") else "ghost"
            btn = Button(bx, pos_y, pos_btn_w - 4, 28, label, style, font=fonts.tiny)
            btn.draw(self.screen)
            buttons[f"spring_filter_pos_{key}"] = btn

        # Filter players
        all_players = player_team.players if player_team else []
        def pos_filter(ply, flt):
            if not flt or flt == "ALL":
                return True
            if flt == "P":
                return ply.position.name == 'PITCHER'
            if flt == "C":
                return ply.position.name == 'CATCHER'
            if flt == "INF":
                return ply.position.name in ['FIRST', 'SECOND', 'THIRD', 'SHORTSTOP']
            if flt == "OF":
                return ply.position.name == 'OUTFIELD'
            return True

        filtered_players = [p for p in all_players if pos_filter(p, filter_position)]
        self._spring_camp_filtered_players = filtered_players  # store for main to use

        # Player list header
        list_header_y = pos_y + 38
        pygame.draw.line(self.screen, Colors.BORDER, 
                        (left_rect.x + 10, list_header_y), 
                        (left_rect.right - 10, list_header_y), 1)
        
        headers = [("名前", 0), ("Pos", 90), ("年", 130)]
        for h_text, h_x in headers:
            h_surf = fonts.tiny.render(h_text, True, Colors.TEXT_MUTED)
            self.screen.blit(h_surf, (left_rect.x + 15 + h_x, list_header_y + 5))

        # Player rows
        list_y = list_header_y + 28
        row_h = 36
        visible_count = max(5, (left_rect.bottom - list_y - 10) // row_h)
        self._spring_camp_visible_players = visible_count
        self._spring_camp_max_scroll = max(0, len(filtered_players) - visible_count)

        for i in range(visible_count):
            idx = i + player_scroll
            if idx >= len(filtered_players):
                break
            ply = filtered_players[idx]
            ry = list_y + i * row_h
            row_rect = pygame.Rect(left_rect.x + 8, ry, left_rect.width - 16, row_h - 4)

            # Selection highlight
            if idx == selected_player_idx:
                pygame.draw.rect(self.screen, (*team_color[:3], 60), row_rect, border_radius=6)
                pygame.draw.rect(self.screen, team_color, row_rect, 2, border_radius=6)
            elif i % 2 == 0:
                pygame.draw.rect(self.screen, Colors.BG_INPUT, row_rect, border_radius=4)

            # Clickable button
            row_btn = Button(row_rect.x, row_rect.y, row_rect.width, row_rect.height, "", "ghost")
            buttons[f"spring_select_player_{idx}"] = row_btn

            # Player info
            name_color = Colors.TEXT_PRIMARY if idx == selected_player_idx else Colors.TEXT_SECONDARY
            name_s = fonts.small.render(ply.name[:7], True, name_color)
            self.screen.blit(name_s, (row_rect.x + 8, row_rect.y + 8))

            pos_s = fonts.tiny.render(ply.position.value[:2], True, Colors.TEXT_MUTED)
            self.screen.blit(pos_s, (row_rect.x + 95, row_rect.y + 10))

            age_s = fonts.tiny.render(str(ply.age), True, Colors.TEXT_MUTED)
            self.screen.blit(age_s, (row_rect.x + 130, row_rect.y + 10))

            # Overall rating (star-prefixed numeric)
            try:
                overall_val = int(getattr(ply, 'overall_rating', 0))
            except Exception:
                overall_val = 0
            overall_s = fonts.tiny.render(f"★{overall_val}", True, Colors.TEXT_MUTED)
            # move overall further left to avoid colliding with menu label on the right
            self.screen.blit(overall_s, (row_rect.right - 110, row_rect.y + 10))

            # Fatigue indicator and menu set indicator
            fatigue = getattr(ply.player_status, 'fatigue', 0) if ply.player_status else 0
            if fatigue >= 60:
                fatigue_color = Colors.DANGER
            elif fatigue >= 30:
                fatigue_color = Colors.WARNING
            else:
                fatigue_color = Colors.SUCCESS
            fatigue_s = fonts.tiny.render(f"{fatigue}%", True, fatigue_color)
            self.screen.blit(fatigue_s, (row_rect.x + 160, row_rect.y + 10))
            
            # Show assigned menu label for this player (if any)
            try:
                actual_player_idx = all_players.index(ply) if ply in all_players else -1
            except Exception:
                actual_player_idx = -1
            if actual_player_idx in selected_menus:
                m_idx = selected_menus.get(actual_player_idx, -1)
                # Build training options for this player to resolve label
                if ply.position.name == 'PITCHER':
                    opts = [
                        ("投球練習", "PITCHING", "球速", "speed", (8, 18), Colors.DANGER),
                        ("制球練習", "CONTROL", "制球", "control", (8, 18), Colors.PRIMARY),
                        ("変化球", "BREAKING", "変化球", "breaking", (8, 18), Colors.WARNING),
                        ("スタミナ", "STAMINA", "スタミナ", "stamina", (8, 18), Colors.SUCCESS),
                        ("休養", "REST", "疲労回復", None, (0, 0), Colors.TEXT_MUTED),
                    ]
                else:
                    opts = [
                        ("打撃練習", "BATTING", "ミート", "contact", (8, 18), Colors.PRIMARY),
                        ("筋力トレ", "POWER", "パワー", "power", (8, 18), Colors.DANGER),
                        ("走塁練習", "RUNNING", "走力", "run", (6, 14), Colors.SUCCESS),
                        ("守備練習", "FIELDING", "守備", "fielding", (6, 14), Colors.WARNING),
                        ("スタミナ", "STAMINA", "スタミナ", "stamina", (8, 18), Colors.SUCCESS),
                        ("休養", "REST", "疲労回復", None, (0, 0), Colors.TEXT_MUTED),
                    ]
                if 0 <= m_idx < len(opts):
                    menu_label = opts[m_idx][2]
                else:
                    menu_label = "設定済"
                menu_s = fonts.tiny.render(menu_label, True, Colors.TEXT_MUTED)
                # align menu label at the far right
                self.screen.blit(menu_s, (row_rect.right - 18 - menu_s.get_width(), row_rect.y + 10))

        # ========== 中央パネル: 練習メニュー ==========
        mid_card = Card(mid_x, header_h + 15, mid_w, content_h, "練習メニュー")
        mid_rect = mid_card.draw(self.screen)
        self._spring_camp_training_menu_rect = mid_rect

        # Training options with descriptions — vary by selected player's position
        if 0 <= selected_player_idx < len(filtered_players):
            sel_p = filtered_players[selected_player_idx]
            if sel_p.position.name == 'PITCHER':
                trainings = [
                    ("投球練習", "PITCHING", "球速", "speed", (8, 18), Colors.DANGER),
                    ("制球練習", "CONTROL", "制球", "control", (8, 18), Colors.PRIMARY),
                    ("変化球", "BREAKING", "変化球", "breaking", (8, 18), Colors.WARNING),
                    ("スタミナ", "STAMINA", "スタミナ", "stamina", (8, 18), Colors.SUCCESS),
                    ("休養", "REST", "疲労回復", None, (0, 0), Colors.TEXT_MUTED),
                ]
            else:
                trainings = [
                    ("打撃練習", "BATTING", "ミート", "contact", (8, 18), Colors.PRIMARY),
                    ("筋力トレ", "POWER", "パワー", "power", (8, 18), Colors.DANGER),
                    ("走塁練習", "RUNNING", "走力", "run", (6, 14), Colors.SUCCESS),
                    ("守備練習", "FIELDING", "守備", "fielding", (6, 14), Colors.WARNING),
                    ("スタミナ", "STAMINA", "スタミナ", "stamina", (8, 18), Colors.SUCCESS),
                    ("休養", "REST", "疲労回復", None, (0, 0), Colors.TEXT_MUTED),
                ]
        else:
            trainings = [
                ("打撃練習", "BATTING", "ミート", "contact", (8, 18), Colors.PRIMARY),
                ("筋力トレ", "POWER", "パワー", "power", (8, 18), Colors.DANGER),
                ("走塁練習", "RUNNING", "走力", "run", (6, 14), Colors.SUCCESS),
                ("守備練習", "FIELDING", "守備", "fielding", (6, 14), Colors.WARNING),
                ("投球練習", "PITCHING", "球速", "speed", (8, 18), Colors.DANGER),
                ("スタミナ", "STAMINA", "スタミナ", "stamina", (8, 18), Colors.SUCCESS),
                ("制球練習", "CONTROL", "制球", "control", (8, 18), Colors.PRIMARY),
                ("休養", "REST", "疲労回復", None, (0, 0), Colors.TEXT_MUTED),
            ]

        btn_w = (mid_rect.width - 40) // 2
        btn_h = 52
        t_y = mid_rect.y + 50

        for i, (label, key, effect, stat_key, xp_range, color) in enumerate(trainings):
            col = i % 2
            row = i // 2
            tx = mid_rect.x + 15 + col * (btn_w + 10)
            ty = t_y + row * (btn_h + 8)

            # Button style based on selection
            is_selected = (i == selected_training_idx)
            is_hovered = (i == hovered_training_idx)
            style = "primary" if is_selected else ("outline" if is_hovered else "ghost")
            
            tbtn = Button(tx, ty, btn_w, btn_h, "", style)
            tbtn.draw(self.screen)
            buttons[f"spring_training_{i}"] = tbtn

            # Training label
            label_color = Colors.TEXT_PRIMARY if is_selected else color
            label_s = fonts.body.render(label, True, label_color)
            self.screen.blit(label_s, (tx + 12, ty + 8))

            # Effect description
            if xp_range[0] > 0:
                effect_text = f"{effect} +XP({xp_range[0]}~{xp_range[1]})"
            else:
                effect_text = effect
            effect_s = fonts.tiny.render(effect_text, True, Colors.TEXT_MUTED)
            self.screen.blit(effect_s, (tx + 12, ty + 30))

        # Preview panel (shows expected result when training is selected)
        preview_y = t_y + 5 * (btn_h + 8) + 15
        pygame.draw.line(self.screen, Colors.BORDER,
                        (mid_rect.x + 15, preview_y - 10),
                        (mid_rect.right - 15, preview_y - 10), 1)

        preview_title = fonts.small.render("効果プレビュー", True, Colors.TEXT_PRIMARY)
        self.screen.blit(preview_title, (mid_rect.x + 15, preview_y))

        if 0 <= selected_training_idx < len(trainings) and 0 <= selected_player_idx < len(filtered_players):
            sel_training = trainings[selected_training_idx]
            sel_player = filtered_players[selected_player_idx]
            
            preview_lines = []
            stat_key = sel_training[3]
            xp_range = sel_training[4]
            
            if stat_key and sel_player.growth:
                cur_val = getattr(sel_player.stats, stat_key, 50)
                cur_xp = sel_player.growth.xp.get(stat_key, 0)
                req_xp = sel_player.growth.xp_required_for(cur_val)
                avg_gain = (xp_range[0] + xp_range[1]) // 2
                
                preview_lines.append(f"対象: {sel_training[2]} (現在値: {cur_val})")
                preview_lines.append(f"獲得XP: {xp_range[0]}～{xp_range[1]} (平均{avg_gain})")
                preview_lines.append(f"現在XP: {cur_xp} / 必要XP: {req_xp}")
                
                # Estimate if level up will occur
                if cur_xp + avg_gain >= req_xp:
                    preview_lines.append(f"→ 能力UP期待大！ ({sel_training[2]}+1)")
            elif sel_training[1] == "REST":
                fatigue = getattr(sel_player.player_status, 'fatigue', 0) if sel_player.player_status else 0
                preview_lines.append(f"現在疲労: {fatigue}%")
                preview_lines.append("→ 疲労-30")

            py = preview_y + 25
            for line in preview_lines:
                line_s = fonts.tiny.render(line, True, Colors.TEXT_SECONDARY)
                self.screen.blit(line_s, (mid_rect.x + 20, py))
                py += 20
        else:
            hint_s = fonts.tiny.render("選手と練習を選択してください", True, Colors.TEXT_MUTED)
            self.screen.blit(hint_s, (mid_rect.x + 20, preview_y + 30))

        # Execute button - now shows "Advance Day" when all menus set, or "Set menu" when selecting player
        # can_execute: whether a single player's menu selection is valid
        can_execute = (0 <= selected_player_idx < len(filtered_players) and 
                   0 <= selected_training_idx < len(trainings))
        all_menus_set = len(selected_menus) >= len(all_players) and len(all_players) > 0
        if all_menus_set:
            exec_btn = Button(
                mid_rect.x + 15, mid_rect.bottom - 60,
                mid_rect.width - 30, 45,
                "▶ 日を進める (全員練習)",
                "success",
                font=fonts.h3
            )
        elif can_execute:
            exec_btn = Button(
                mid_rect.x + 15, mid_rect.bottom - 60,
                mid_rect.width - 30, 45,
                "✓ メニューを設定",
                "primary",
                font=fonts.h3
            )
        else:
            exec_btn = Button(
                mid_rect.x + 15, mid_rect.bottom - 60,
                mid_rect.width - 30, 45,
                "選手と練習を選択",
                "outline",
                font=fonts.h3
            )
        exec_btn.draw(self.screen)
        buttons["spring_confirm_train"] = exec_btn

        # ========== 右パネル: 選手詳細 ==========
        detail_card = Card(right_x, header_h + 15, right_w, content_h, "選手詳細")
        detail_rect = detail_card.draw(self.screen)
        self._spring_camp_detail_rect = detail_rect

        if 0 <= selected_player_idx < len(filtered_players):
            sel = filtered_players[selected_player_idx]
            sx = detail_rect.x + 15
            sy = detail_rect.y + 45

            # Player name and basic info
            name_s = fonts.h2.render(sel.name, True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_s, (sx, sy))
            sy += 32

            # Position, Age (潜在力は内部の隠しステータスのため表示しない)
            pos_text = f"{sel.position.value} / {sel.age}歳"
            pos_s = fonts.small.render(pos_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(pos_s, (sx, sy))
            sy += 34

            # Fatigue status
            if sel.player_status:
                fatigue = sel.player_status.fatigue
                
                status_text = f"疲労: {fatigue}%"
                status_s = fonts.tiny.render(status_text, True, Colors.TEXT_MUTED)
                self.screen.blit(status_s, (sx, sy))
                sy += 25

            pygame.draw.line(self.screen, Colors.BORDER,
                            (sx, sy), (detail_rect.right - 15, sy), 1)
            sy += 12

            # Stats with XP bars
            if sel.position.name == 'PITCHER':
                stat_items = [
                    ("球速", "speed", Colors.DANGER),
                    ("制球", "control", Colors.PRIMARY),
                    ("スタミナ", "stamina", Colors.SUCCESS),
                    ("変化球", "breaking", Colors.WARNING),
                ]
            else:
                stat_items = [
                    ("ミート", "contact", Colors.PRIMARY),
                    ("パワー", "power", Colors.DANGER),
                    ("走力", "run", Colors.SUCCESS),
                    ("守備", "fielding", Colors.WARNING),
                    ("肩力", "arm", Colors.PRIMARY),
                ]

            bar_w = detail_rect.width - 100

            for stat_name, stat_key, stat_color in stat_items:
                val = getattr(sel.stats, stat_key, 50)
                xp = sel.growth.xp.get(stat_key, 0) if sel.growth else 0
                req = sel.growth.xp_required_for(val) if sel.growth else 100

                # Stat label and value
                label_s = fonts.small.render(stat_name, True, Colors.TEXT_SECONDARY)
                self.screen.blit(label_s, (sx, sy))
                
                val_s = fonts.small.render(str(val), True, stat_color)
                self.screen.blit(val_s, (sx + 70, sy))

                # Stat bar (0-99)
                bar_rect = pygame.Rect(sx, sy + 22, bar_w, 10)
                pygame.draw.rect(self.screen, Colors.BG_INPUT, bar_rect, border_radius=5)
                fill_w = int(bar_w * min(val, 99) / 99)
                fill_rect = pygame.Rect(sx, sy + 22, fill_w, 10)
                pygame.draw.rect(self.screen, stat_color, fill_rect, border_radius=5)

                # XP progress bar (smaller, below stat bar)
                xp_bar_rect = pygame.Rect(sx, sy + 34, bar_w, 6)
                pygame.draw.rect(self.screen, Colors.BG_INPUT, xp_bar_rect, border_radius=3)
                xp_fill_w = int(bar_w * min(xp, req) / max(1, req))
                xp_fill_rect = pygame.Rect(sx, sy + 34, xp_fill_w, 6)
                pygame.draw.rect(self.screen, Colors.GOLD, xp_fill_rect, border_radius=3)

                # XP text
                xp_text = f"XP: {xp}/{req}"
                xp_s = fonts.tiny.render(xp_text, True, Colors.TEXT_MUTED)
                self.screen.blit(xp_s, (sx + bar_w + 5, sy + 28))

                sy += 52
        else:
            # No player selected
            hint_y = detail_rect.y + detail_rect.height // 2 - 30
            hint_s = fonts.body.render("← 選手を選択", True, Colors.TEXT_MUTED)
            hint_rect = hint_s.get_rect(center=(detail_rect.centerx, hint_y))
            self.screen.blit(hint_s, hint_rect)

            hint2_s = fonts.small.render("してください", True, Colors.TEXT_MUTED)
            hint2_rect = hint2_s.get_rect(center=(detail_rect.centerx, hint_y + 30))
            self.screen.blit(hint2_s, hint2_rect)

        # ========== 下部ボタン ==========
        buttons["spring_back"] = Button(
            gutter, height - 60, 140, 45,
            "← 戻る", "ghost", font=fonts.body
        )
        buttons["spring_back"].draw(self.screen)

        buttons["spring_auto_train"] = Button(
            gutter + 160, height - 60, 180, 45,
            "メニュー自動設定", "outline", font=fonts.small
        )
        buttons["spring_auto_train"].draw(self.screen)

        buttons["spring_end_camp"] = Button(
            width - gutter - 160, height - 60, 150, 45,
            "キャンプ終了 →", "primary", font=fonts.body
        )
        buttons["spring_end_camp"].draw(self.screen)

        ToastManager.update_and_draw(self.screen)
        return buttons

    def draw_fall_camp_screen(self, player_team, selected_player_idx: int = -1,
                              filter_position: Optional[str] = None,
                              selected_training_idx: int = -1,
                              player_scroll: int = 0,
                              hovered_training_idx: int = -1,
                              camp_day: int = 1,
                              max_camp_days: int = 14,
                              selected_menus: dict = None,
                              overall_threshold: int = 250) -> Dict[str, Button]:
        """秋季キャンプ画面：総合力が一定以下の選手のみ参加
        
        春季キャンプと同じUIだが、参加選手が限定される。
        overall_threshold: この値以下の総合力の選手のみ参加可能
        """
        if selected_menus is None:
            selected_menus = {}
        
        draw_background(self.screen, "gradient")

        width = self.screen.get_width()
        height = self.screen.get_height()
        team_color = self.get_team_color(player_team.name) if player_team else Colors.PRIMARY
        
        # 総合力フィルター: 参加可能な選手のみ
        all_players = player_team.players if player_team else []
        eligible_players = [p for p in all_players if getattr(p, 'overall_rating', 999) <= overall_threshold]
        
        menus_set_count = len(selected_menus)
        header_h = draw_header(self.screen, "🍂 秋季キャンプ", 
                              f"Day {camp_day}/{max_camp_days} - 参加: {len(eligible_players)}人 (総合{overall_threshold}以下)", 
                              team_color)

        buttons: Dict[str, Button] = {}

        # レイアウト
        gutter = 15
        left_w = min(320, int(width * 0.25))
        right_w = min(380, int(width * 0.30))
        mid_w = width - left_w - right_w - gutter * 4

        left_x = gutter
        mid_x = left_x + left_w + gutter
        right_x = mid_x + mid_w + gutter

        content_h = height - header_h - 80

        # ========== 左パネル: 選手一覧（参加可能選手のみ）==========
        left_card = Card(left_x, header_h + 15, left_w, content_h, "📋 参加選手")
        left_rect = left_card.draw(self.screen)
        self._fall_camp_player_list_rect = left_rect

        # ポジションフィルターボタン
        pos_y = left_rect.y + 45
        positions = [("全員", "ALL"), ("投", "P"), ("捕", "C"), ("内", "INF"), ("外", "OF")]
        pos_btn_w = (left_rect.width - 30) // len(positions)
        for i, (label, key) in enumerate(positions):
            bx = left_rect.x + 10 + i * pos_btn_w
            style = "primary" if filter_position == key or (filter_position is None and key == "ALL") else "ghost"
            btn = Button(bx, pos_y, pos_btn_w - 4, 28, label, style, font=fonts.tiny)
            btn.draw(self.screen)
            buttons[f"fall_filter_pos_{key}"] = btn

        # ポジションでフィルタリング
        def pos_filter(ply, flt):
            if not flt or flt == "ALL":
                return True
            if flt == "P":
                return ply.position.name == 'PITCHER'
            if flt == "C":
                return ply.position.name == 'CATCHER'
            if flt == "INF":
                return ply.position.name in ['FIRST', 'SECOND', 'THIRD', 'SHORTSTOP']
            if flt == "OF":
                return ply.position.name == 'OUTFIELD'
            return True

        filtered_players = [p for p in eligible_players if pos_filter(p, filter_position)]
        self._fall_camp_filtered_players = filtered_players

        # 選手リストヘッダー
        list_header_y = pos_y + 38
        pygame.draw.line(self.screen, Colors.BORDER, 
                        (left_rect.x + 10, list_header_y), 
                        (left_rect.right - 10, list_header_y), 1)
        
        headers = [("名前", 0), ("Pos", 90), ("年", 130), ("総合", 170)]
        for h_text, h_x in headers:
            h_surf = fonts.tiny.render(h_text, True, Colors.TEXT_MUTED)
            self.screen.blit(h_surf, (left_rect.x + 15 + h_x, list_header_y + 5))

        # 選手リスト
        list_y = list_header_y + 28
        row_h = 36
        visible_count = max(5, (left_rect.bottom - list_y - 10) // row_h)
        self._fall_camp_visible_players = visible_count
        self._fall_camp_max_scroll = max(0, len(filtered_players) - visible_count)

        for i in range(visible_count):
            idx = i + player_scroll
            if idx >= len(filtered_players):
                break
            ply = filtered_players[idx]
            ry = list_y + i * row_h
            row_rect = pygame.Rect(left_rect.x + 8, ry, left_rect.width - 16, row_h - 4)

            # 選択ハイライト
            if idx == selected_player_idx:
                pygame.draw.rect(self.screen, (*team_color[:3], 60), row_rect, border_radius=6)
                pygame.draw.rect(self.screen, team_color, row_rect, 2, border_radius=6)
            elif i % 2 == 0:
                pygame.draw.rect(self.screen, Colors.BG_INPUT, row_rect, border_radius=4)

            row_btn = Button(row_rect.x, row_rect.y, row_rect.width, row_rect.height, "", "ghost")
            buttons[f"fall_select_player_{idx}"] = row_btn

            # 選手情報
            name_color = Colors.TEXT_PRIMARY if idx == selected_player_idx else Colors.TEXT_SECONDARY
            name_s = fonts.small.render(ply.name[:7], True, name_color)
            self.screen.blit(name_s, (row_rect.x + 8, row_rect.y + 8))

            pos_s = fonts.tiny.render(ply.position.value[:2], True, Colors.TEXT_MUTED)
            self.screen.blit(pos_s, (row_rect.x + 95, row_rect.y + 10))

            age_s = fonts.tiny.render(str(ply.age), True, Colors.TEXT_MUTED)
            self.screen.blit(age_s, (row_rect.x + 130, row_rect.y + 10))

            # 総合力（秋季キャンプ参加者は低め）
            try:
                overall_val = int(getattr(ply, 'overall_rating', 0))
            except Exception:
                overall_val = 0
            overall_color = Colors.WARNING if overall_val < 200 else Colors.TEXT_MUTED
            overall_s = fonts.tiny.render(f"★{overall_val}", True, overall_color)
            # move overall further left to avoid colliding with menu label on the right
            self.screen.blit(overall_s, (row_rect.right - 110, row_rect.y + 10))

            # Fatigue indicator
            fatigue = getattr(ply.player_status, 'fatigue', 0) if ply.player_status else 0
            if fatigue >= 60:
                fatigue_color = Colors.DANGER
            elif fatigue >= 30:
                fatigue_color = Colors.WARNING
            else:
                fatigue_color = Colors.SUCCESS
            fatigue_s = fonts.tiny.render(f"{fatigue}%", True, fatigue_color)
            self.screen.blit(fatigue_s, (row_rect.x + 160, row_rect.y + 10))

            # メニュー設定済みインジケーター（表示: メニュー名）
            actual_player_idx = all_players.index(ply) if ply in all_players else -1
            if actual_player_idx in selected_menus:
                m_idx = selected_menus.get(actual_player_idx, -1)
                # Build trainings list for this player to resolve label
                if ply.position.name == 'PITCHER':
                    opts = [
                        ("投球練習", "PITCHING", "球速", "speed", (10, 22), Colors.DANGER),
                        ("制球練習", "CONTROL", "制球", "control", (10, 22), Colors.PRIMARY),
                        ("変化球", "BREAKING", "変化球", "breaking", (10, 22), Colors.WARNING),
                        ("スタミナ", "STAMINA", "スタミナ", "stamina", (10, 22), Colors.SUCCESS),
                        ("休養", "REST", "疲労回復", None, (0, 0), Colors.TEXT_MUTED),
                    ]
                else:
                    opts = [
                        ("打撃練習", "BATTING", "ミート", "contact", (10, 22), Colors.PRIMARY),
                        ("筋力トレ", "POWER", "パワー", "power", (10, 22), Colors.DANGER),
                        ("走塁練習", "RUNNING", "走力", "run", (8, 18), Colors.SUCCESS),
                        ("守備練習", "FIELDING", "守備", "fielding", (8, 18), Colors.WARNING),
                        ("スタミナ", "STAMINA", "スタミナ", "stamina", (10, 22), Colors.SUCCESS),
                        ("休養", "REST", "疲労回復", None, (0, 0), Colors.TEXT_MUTED),
                    ]
                if 0 <= m_idx < len(opts):
                    menu_label = opts[m_idx][2]
                else:
                    menu_label = "設定済"
                menu_s = fonts.tiny.render(menu_label, True, Colors.SUCCESS)
                self.screen.blit(menu_s, (row_rect.right - 18 - menu_s.get_width(), row_rect.y + 10))

        # ========== 中央パネル: 練習メニュー（春季と同じ）==========
        mid_card = Card(mid_x, header_h + 15, mid_w, content_h, "練習メニュー")
        mid_rect = mid_card.draw(self.screen)
        self._fall_camp_training_menu_rect = mid_rect

        # 練習メニュー（選手のポジションで分岐）
        if 0 <= selected_player_idx < len(filtered_players):
            sel_p = filtered_players[selected_player_idx]
            if sel_p.position.name == 'PITCHER':
                trainings = [
                    ("投球練習", "PITCHING", "球速", "speed", (10, 22), Colors.DANGER),
                    ("制球練習", "CONTROL", "制球", "control", (10, 22), Colors.PRIMARY),
                    ("変化球", "BREAKING", "変化球", "breaking", (10, 22), Colors.WARNING),
                    ("スタミナ", "STAMINA", "スタミナ", "stamina", (10, 22), Colors.SUCCESS),
                    ("休養", "REST", "疲労回復", None, (0, 0), Colors.TEXT_MUTED),
                ]
            else:
                trainings = [
                    ("打撃練習", "BATTING", "ミート", "contact", (10, 22), Colors.PRIMARY),
                    ("筋力トレ", "POWER", "パワー", "power", (10, 22), Colors.DANGER),
                    ("走塁練習", "RUNNING", "走力", "run", (8, 18), Colors.SUCCESS),
                    ("守備練習", "FIELDING", "守備", "fielding", (8, 18), Colors.WARNING),
                    ("スタミナ", "STAMINA", "スタミナ", "stamina", (10, 22), Colors.SUCCESS),
                    ("休養", "REST", "疲労回復", None, (0, 0), Colors.TEXT_MUTED),
                ]
        else:
            trainings = [
                ("打撃練習", "BATTING", "ミート", "contact", (10, 22), Colors.PRIMARY),
                ("筋力トレ", "POWER", "パワー", "power", (10, 22), Colors.DANGER),
                ("走塁練習", "RUNNING", "走力", "run", (8, 18), Colors.SUCCESS),
                ("守備練習", "FIELDING", "守備", "fielding", (8, 18), Colors.WARNING),
                ("休養", "REST", "疲労回復", None, (0, 0), Colors.TEXT_MUTED),
            ]

        btn_w = (mid_rect.width - 40) // 2
        btn_h = 52
        t_y = mid_rect.y + 50

        for i, (label, key, effect, stat_key, xp_range, color) in enumerate(trainings):
            col = i % 2
            row = i // 2
            tx = mid_rect.x + 15 + col * (btn_w + 10)
            ty = t_y + row * (btn_h + 8)

            is_selected = (i == selected_training_idx)
            is_hovered = (i == hovered_training_idx)
            style = "primary" if is_selected else ("outline" if is_hovered else "ghost")
            
            tbtn = Button(tx, ty, btn_w, btn_h, "", style)
            tbtn.draw(self.screen)
            buttons[f"fall_training_{i}"] = tbtn

            label_color = Colors.TEXT_PRIMARY if is_selected else color
            label_s = fonts.body.render(label, True, label_color)
            self.screen.blit(label_s, (tx + 12, ty + 8))

            if xp_range[0] > 0:
                effect_text = f"{effect} +XP({xp_range[0]}~{xp_range[1]})"
            else:
                effect_text = effect
            effect_s = fonts.tiny.render(effect_text, True, Colors.TEXT_MUTED)
            self.screen.blit(effect_s, (tx + 12, ty + 30))

        # プレビュー
        preview_y = t_y + 4 * (btn_h + 8) + 15
        pygame.draw.line(self.screen, Colors.BORDER,
                        (mid_rect.x + 15, preview_y - 10),
                        (mid_rect.right - 15, preview_y - 10), 1)

        preview_title = fonts.small.render("効果プレビュー", True, Colors.TEXT_PRIMARY)
        self.screen.blit(preview_title, (mid_rect.x + 15, preview_y))

        if 0 <= selected_training_idx < len(trainings) and 0 <= selected_player_idx < len(filtered_players):
            sel_training = trainings[selected_training_idx]
            sel_player = filtered_players[selected_player_idx]
            
            preview_lines = []
            stat_key = sel_training[3]
            xp_range = sel_training[4]
            
            if stat_key and sel_player.growth:
                cur_val = getattr(sel_player.stats, stat_key, 50)
                cur_xp = sel_player.growth.xp.get(stat_key, 0)
                req_xp = sel_player.growth.xp_required_for(cur_val)
                avg_gain = (xp_range[0] + xp_range[1]) // 2
                
                preview_lines.append(f"対象: {sel_training[2]} (現在値: {cur_val})")
                preview_lines.append(f"獲得XP: {xp_range[0]}～{xp_range[1]} (平均{avg_gain})")
                preview_lines.append(f"現在XP: {cur_xp} / 必要XP: {req_xp}")
                
                if cur_xp + avg_gain >= req_xp:
                    preview_lines.append(f"→ 能力UP期待大！ ({sel_training[2]}+1)")
            elif sel_training[1] == "REST":
                fatigue = getattr(sel_player.player_status, 'fatigue', 0) if sel_player.player_status else 0
                preview_lines.append(f"現在疲労: {fatigue}%")
                preview_lines.append("→ 疲労-30")

            py = preview_y + 25
            for line in preview_lines:
                line_s = fonts.tiny.render(line, True, Colors.TEXT_SECONDARY)
                self.screen.blit(line_s, (mid_rect.x + 20, py))
                py += 20
        else:
            hint_s = fonts.tiny.render("選手と練習を選択してください", True, Colors.TEXT_MUTED)
            self.screen.blit(hint_s, (mid_rect.x + 20, preview_y + 30))

        # 実行ボタン
        can_execute = (0 <= selected_player_idx < len(filtered_players) and 
                   0 <= selected_training_idx < len(trainings))
        all_menus_set = len(selected_menus) >= len(eligible_players) and len(eligible_players) > 0
        if all_menus_set:
            exec_btn = Button(
                mid_rect.x + 15, mid_rect.bottom - 60,
                mid_rect.width - 30, 45,
                "▶ 日を進める (全員練習)",
                "success",
                font=fonts.h3
            )
        elif can_execute:
            exec_btn = Button(
                mid_rect.x + 15, mid_rect.bottom - 60,
                mid_rect.width - 30, 45,
                "✓ メニューを設定",
                "primary",
                font=fonts.h3
            )
        else:
            exec_btn = Button(
                mid_rect.x + 15, mid_rect.bottom - 60,
                mid_rect.width - 30, 45,
                "選手と練習を選択",
                "outline",
                font=fonts.h3
            )
        exec_btn.draw(self.screen)
        buttons["fall_confirm_train"] = exec_btn

        # ========== 右パネル: 選手詳細 ==========
        detail_card = Card(right_x, header_h + 15, right_w, content_h, "選手詳細")
        detail_rect = detail_card.draw(self.screen)
        self._fall_camp_detail_rect = detail_rect

        if 0 <= selected_player_idx < len(filtered_players):
            sel = filtered_players[selected_player_idx]
            sx = detail_rect.x + 15
            sy = detail_rect.y + 45

            name_s = fonts.h2.render(sel.name, True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_s, (sx, sy))
            sy += 32

            pos_text = f"{sel.position.value} / {sel.age}歳"
            pos_s = fonts.small.render(pos_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(pos_s, (sx, sy))
            sy += 34

            if sel.player_status:
                fatigue = sel.player_status.fatigue
                
                status_text = f"疲労: {fatigue}%"
                status_s = fonts.tiny.render(status_text, True, Colors.TEXT_MUTED)
                self.screen.blit(status_s, (sx, sy))
                sy += 25

            pygame.draw.line(self.screen, Colors.BORDER,
                            (sx, sy), (detail_rect.right - 15, sy), 1)
            sy += 12

            # 能力値とXPバー
            if sel.position.name == 'PITCHER':
                stat_items = [
                    ("球速", "speed", Colors.DANGER),
                    ("制球", "control", Colors.PRIMARY),
                    ("スタミナ", "stamina", Colors.SUCCESS),
                    ("変化球", "breaking", Colors.WARNING),
                ]
            else:
                stat_items = [
                    ("ミート", "contact", Colors.PRIMARY),
                    ("パワー", "power", Colors.DANGER),
                    ("走力", "run", Colors.SUCCESS),
                    ("守備", "fielding", Colors.WARNING),
                    ("肩力", "arm", Colors.PRIMARY),
                ]

            bar_w = detail_rect.width - 100

            for stat_name, stat_key, stat_color in stat_items:
                val = getattr(sel.stats, stat_key, 50)
                xp = sel.growth.xp.get(stat_key, 0) if sel.growth else 0
                req = sel.growth.xp_required_for(val) if sel.growth else 100

                label_s = fonts.small.render(stat_name, True, Colors.TEXT_SECONDARY)
                self.screen.blit(label_s, (sx, sy))
                
                val_s = fonts.small.render(str(val), True, stat_color)
                self.screen.blit(val_s, (sx + 70, sy))

                bar_rect = pygame.Rect(sx, sy + 22, bar_w, 10)
                pygame.draw.rect(self.screen, Colors.BG_INPUT, bar_rect, border_radius=5)
                fill_w = int(bar_w * min(val, 99) / 99)
                fill_rect = pygame.Rect(sx, sy + 22, fill_w, 10)
                pygame.draw.rect(self.screen, stat_color, fill_rect, border_radius=5)

                xp_bar_rect = pygame.Rect(sx, sy + 34, bar_w, 6)
                pygame.draw.rect(self.screen, Colors.BG_INPUT, xp_bar_rect, border_radius=3)
                xp_fill_w = int(bar_w * min(xp, req) / max(1, req))
                xp_fill_rect = pygame.Rect(sx, sy + 34, xp_fill_w, 6)
                pygame.draw.rect(self.screen, Colors.GOLD, xp_fill_rect, border_radius=3)

                xp_text = f"XP: {xp}/{req}"
                xp_s = fonts.tiny.render(xp_text, True, Colors.TEXT_MUTED)
                self.screen.blit(xp_s, (sx + bar_w + 5, sy + 28))

                sy += 52
        else:
            hint_y = detail_rect.y + detail_rect.height // 2 - 30
            hint_s = fonts.body.render("← 選手を選択", True, Colors.TEXT_MUTED)
            hint_rect = hint_s.get_rect(center=(detail_rect.centerx, hint_y))
            self.screen.blit(hint_s, hint_rect)

            hint2_s = fonts.small.render("してください", True, Colors.TEXT_MUTED)
            hint2_rect = hint2_s.get_rect(center=(detail_rect.centerx, hint_y + 30))
            self.screen.blit(hint2_s, hint2_rect)

        # ========== 下部ボタン ==========
        buttons["fall_back"] = Button(
            gutter, height - 60, 140, 45,
            "← 戻る", "ghost", font=fonts.body
        )
        buttons["fall_back"].draw(self.screen)

        buttons["fall_auto_train"] = Button(
            gutter + 160, height - 60, 180, 45,
            "メニュー自動設定", "outline", font=fonts.small
        )
        buttons["fall_auto_train"].draw(self.screen)

        buttons["fall_end_camp"] = Button(
            width - gutter - 160, height - 60, 150, 45,
            "キャンプ終了 →", "primary", font=fonts.body
        )
        buttons["fall_end_camp"].draw(self.screen)

        ToastManager.update_and_draw(self.screen)
        return buttons

    # ========================================
    # 経営画面
    # ========================================
    def draw_management_screen(self, player_team: Team, finances, tab: str = "overview") -> Dict[str, Button]:
        """経営画面を描画"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        buttons = {}
        
        # ヘッダー
        header_h = 80
        team_info = player_team.name if player_team else None
        draw_header(self.screen, "MANAGEMENT", team_info)
        
        # タブ
        tabs = [
            ("overview", "概要"),
            ("finances", "財務"),
            ("facilities", "施設"),
            ("sponsors", "スポンサー"),
            ("staff", "スタッフ"),
        ]
        
        tab_y = header_h + 15
        tab_x = 30
        
        for tab_id, tab_name in tabs:
            style = "primary" if tab == tab_id else "ghost"
            btn = Button(tab_x, tab_y, 130, 40, tab_name, style, font=fonts.small)
            btn.draw(self.screen)
            buttons[f"mgmt_tab_{tab_id}"] = btn
            tab_x += 140
        
        # 財務データの取得（デフォルト値）
        if finances:
            budget = finances.budget if hasattr(finances, 'budget') else 50.0
            payroll = finances.payroll if hasattr(finances, 'payroll') else 30.0
            revenue = finances.revenue if hasattr(finances, 'revenue') else 25.0
            sponsorship = finances.sponsorship if hasattr(finances, 'sponsorship') else 10.0
            ticket_sales = finances.ticket_sales if hasattr(finances, 'ticket_sales') else 5.0
            merchandise = finances.merchandise if hasattr(finances, 'merchandise') else 3.0
        else:
            budget = 50.0
            payroll = 30.0
            revenue = 25.0
            sponsorship = 10.0
            ticket_sales = 5.0
            merchandise = 3.0
        
        available = budget - payroll
        
        content_y = header_h + 70
        
        if tab == "overview":
            # 概要タブ
            # 左カード: 収支サマリー
            summary_card = Card(30, content_y, 380, 250, "SUMMARY")
            summary_rect = summary_card.draw(self.screen)
            
            y = summary_rect.y + 55
            summary_items = [
                ("総予算", f"{budget:.1f}億円", Colors.PRIMARY),
                ("年俸総額", f"{payroll:.1f}億円", Colors.DANGER),
                ("利用可能", f"{available:.1f}億円", Colors.SUCCESS if available > 0 else Colors.DANGER),
                ("年間収入", f"{revenue:.1f}億円", Colors.TEXT_PRIMARY),
            ]
            
            for label, value, color in summary_items:
                label_surf = fonts.body.render(label, True, Colors.TEXT_SECONDARY)
                value_surf = fonts.h3.render(value, True, color)
                self.screen.blit(label_surf, (summary_rect.x + 25, y))
                self.screen.blit(value_surf, (summary_rect.x + 200, y))
                y += 45
            
            # 右カード: 収入内訳
            income_card = Card(430, content_y, 350, 250, "INCOME")
            income_rect = income_card.draw(self.screen)
            
            y = income_rect.y + 55
            income_items = [
                ("スポンサー", sponsorship),
                ("チケット売上", ticket_sales),
                ("グッズ売上", merchandise),
            ]
            
            total_income = sponsorship + ticket_sales + merchandise
            
            for label, value in income_items:
                label_surf = fonts.body.render(label, True, Colors.TEXT_SECONDARY)
                self.screen.blit(label_surf, (income_rect.x + 20, y))
                
                # 棒グラフ
                bar_width = 150
                bar_rect = pygame.Rect(income_rect.x + 120, y + 3, bar_width, 20)
                pygame.draw.rect(self.screen, Colors.BG_INPUT, bar_rect, border_radius=10)
                
                if total_income > 0:
                    fill_ratio = value / total_income
                    fill_rect = pygame.Rect(bar_rect.x, bar_rect.y, int(bar_width * fill_ratio), 20)
                    pygame.draw.rect(self.screen, Colors.SUCCESS, fill_rect, border_radius=10)
                
                value_surf = fonts.small.render(f"{value:.1f}億", True, Colors.TEXT_PRIMARY)
                self.screen.blit(value_surf, (bar_rect.right + 10, y + 2))
                
                y += 40
            
            # 下カード: 今後の予定
            schedule_card = Card(30, content_y + 270, 750, 180, "SCHEDULE")
            schedule_rect = schedule_card.draw(self.screen)
            
            y = schedule_rect.y + 55
            schedule_items = [
                ("ドラフト契約金", "約5.0億円", "10月"),
                ("FA補強", "予算10.0億円", "11-12月"),
                ("施設維持費", "年間3.0億円", "通年"),
            ]
            
            for i, (item, amount, period) in enumerate(schedule_items):
                x_offset = schedule_rect.x + 25 + i * 240
                item_surf = fonts.body.render(item, True, Colors.TEXT_PRIMARY)
                amount_surf = fonts.small.render(amount, True, Colors.WARNING)
                period_surf = fonts.tiny.render(period, True, Colors.TEXT_MUTED)
                self.screen.blit(item_surf, (x_offset, y))
                self.screen.blit(amount_surf, (x_offset, y + 28))
                self.screen.blit(period_surf, (x_offset, y + 50))
        
        elif tab == "finances":
            # 財務タブ
            # 年俸一覧
            payroll_card = Card(30, content_y, 500, height - content_y - 100, "💵 選手年俸一覧")
            payroll_rect = payroll_card.draw(self.screen)
            
            y = payroll_rect.y + 55
            
            if player_team:
                # 年俸順にソート
                sorted_players = sorted(player_team.players, 
                    key=lambda p: p.salary if hasattr(p, 'salary') else 1000, reverse=True)
                
                for i, player in enumerate(sorted_players[:12]):
                    salary = player.salary if hasattr(player, 'salary') else 1000
                    salary_oku = salary / 10000  # 万円→億円
                    
                    # 行背景
                    row_rect = pygame.Rect(payroll_rect.x + 15, y, payroll_rect.width - 30, 35)
                    if i % 2 == 0:
                        pygame.draw.rect(self.screen, (*Colors.BG_CARD[:3], 100), row_rect, border_radius=4)
                    
                    name_surf = fonts.body.render(player.name[:8], True, Colors.TEXT_PRIMARY)
                    self.screen.blit(name_surf, (row_rect.x + 10, y + 7))
                    
                    pos_surf = fonts.tiny.render(player.position.value, True, Colors.TEXT_MUTED)
                    self.screen.blit(pos_surf, (row_rect.x + 150, y + 10))
                    
                    salary_color = Colors.DANGER if salary_oku > 3 else Colors.TEXT_PRIMARY
                    salary_surf = fonts.body.render(f"{salary_oku:.2f}億円", True, salary_color)
                    self.screen.blit(salary_surf, (row_rect.x + 250, y + 7))
                    
                    y += 38
            
            # 年俸ランキング（リーグ）
            rank_card = Card(550, content_y, 250, 200, "SALARY RANK")
            rank_rect = rank_card.draw(self.screen)
            
            rank_text = fonts.h2.render("3位", True, Colors.PRIMARY)
            rank_info = fonts.small.render("セ・リーグ", True, Colors.TEXT_MUTED)
            self.screen.blit(rank_text, (rank_rect.x + 90, rank_rect.y + 80))
            self.screen.blit(rank_info, (rank_rect.x + 85, rank_rect.y + 120))
        
        elif tab == "facilities":
            # 施設タブ
            facility_card = Card(30, content_y, 750, height - content_y - 100, "FACILITIES")
            facility_rect = facility_card.draw(self.screen)
            
            y = facility_rect.y + 55
            
            facilities = [
                ("本拠地球場", "レベル5", "収容: 40,000人", "良好", 95),
                ("室内練習場", "レベル3", "バッティング・ブルペン", "普通", 70),
                ("トレーニング施設", "レベル4", "筋力・走力強化", "良好", 85),
                ("リハビリ施設", "レベル2", "怪我からの復帰支援", "普通", 60),
                ("寮", "レベル3", "若手選手向け", "普通", 75),
                ("スカウティング設備", "レベル3", "ドラフト・FAの情報収集", "普通", 70),
            ]
            
            for name, level, desc, condition, rating in facilities:
                # 施設行
                row_rect = pygame.Rect(facility_rect.x + 20, y, facility_rect.width - 40, 60)
                pygame.draw.rect(self.screen, Colors.BG_INPUT, row_rect, border_radius=8)
                
                name_surf = fonts.body.render(name, True, Colors.TEXT_PRIMARY)
                self.screen.blit(name_surf, (row_rect.x + 15, y + 8))
                
                level_surf = fonts.small.render(level, True, Colors.PRIMARY)
                self.screen.blit(level_surf, (row_rect.x + 180, y + 10))
                
                desc_surf = fonts.tiny.render(desc, True, Colors.TEXT_MUTED)
                self.screen.blit(desc_surf, (row_rect.x + 15, y + 35))
                
                # レーティングバー
                bar_x = row_rect.x + 400
                bar_rect = pygame.Rect(bar_x, y + 20, 150, 16)
                pygame.draw.rect(self.screen, Colors.BORDER, bar_rect, border_radius=8)
                
                fill_width = int(150 * rating / 100)
                if rating >= 80:
                    fill_color = Colors.SUCCESS
                elif rating >= 50:
                    fill_color = Colors.WARNING
                else:
                    fill_color = Colors.DANGER
                fill_rect = pygame.Rect(bar_x, y + 20, fill_width, 16)
                pygame.draw.rect(self.screen, fill_color, fill_rect, border_radius=8)
                
                # 投資ボタン
                buttons[f"upgrade_{name}"] = Button(
                    row_rect.right - 100, y + 15, 80, 35,
                    "投資", "ghost", font=fonts.tiny
                )
                buttons[f"upgrade_{name}"].draw(self.screen)
                
                y += 68
        
        elif tab == "sponsors":
            # スポンサータブ
            sponsor_card = Card(30, content_y, 500, height - content_y - 100, "スポンサー契約")
            sponsor_rect = sponsor_card.draw(self.screen)
            
            y = sponsor_rect.y + 55
            
            sponsors = [
                ("メインスポンサー", "AA自動車", "10.0億円/年", 3, "契約中"),
                ("ユニフォームスポンサー", "BB銀行", "5.0億円/年", 2, "契約中"),
                ("球場看板", "CC飲料", "2.0億円/年", 1, "更新可"),
                ("公式パートナー", "DD電機", "1.5億円/年", 5, "契約中"),
            ]
            
            for name, company, amount, years, status in sponsors:
                row_rect = pygame.Rect(sponsor_rect.x + 15, y, sponsor_rect.width - 30, 55)
                pygame.draw.rect(self.screen, Colors.BG_INPUT, row_rect, border_radius=8)
                
                name_surf = fonts.body.render(name, True, Colors.TEXT_SECONDARY)
                self.screen.blit(name_surf, (row_rect.x + 10, y + 5))
                
                company_surf = fonts.body.render(company, True, Colors.TEXT_PRIMARY)
                self.screen.blit(company_surf, (row_rect.x + 10, y + 28))
                
                amount_surf = fonts.small.render(amount, True, Colors.SUCCESS)
                self.screen.blit(amount_surf, (row_rect.x + 200, y + 15))
                
                years_surf = fonts.tiny.render(f"残{years}年", True, Colors.TEXT_MUTED)
                self.screen.blit(years_surf, (row_rect.x + 320, y + 18))
                
                status_color = Colors.SUCCESS if status == "契約中" else Colors.WARNING
                status_surf = fonts.small.render(status, True, status_color)
                self.screen.blit(status_surf, (row_rect.x + 400, y + 15))
                
                y += 62
            
            # 新規スポンサー獲得
            new_card = Card(550, content_y, 250, 150, "📢 新規獲得")
            new_rect = new_card.draw(self.screen)
            
            buttons["find_sponsors"] = Button(
                new_rect.x + 40, new_rect.y + 70, 170, 45,
                "🔍 営業活動", "secondary", font=fonts.body
            )
            buttons["find_sponsors"].draw(self.screen)
        
        elif tab == "staff":
            # スタッフタブ
            staff_card = Card(30, content_y, 750, height - content_y - 100, "👔 コーチングスタッフ")
            staff_rect = staff_card.draw(self.screen)
            
            y = staff_rect.y + 55
            
            staff_list = [
                ("監督", "山田一郎", "A", "チーム士気向上"),
                ("ヘッドコーチ", "佐藤二郎", "B", "総合指導"),
                ("打撃コーチ", "鈴木三郎", "A", "打撃能力向上"),
                ("投手コーチ", "高橋四郎", "B", "投球能力向上"),
                ("守備・走塁コーチ", "田中五郎", "C", "守備・走塁向上"),
                ("バッテリーコーチ", "伊藤六郎", "B", "捕手育成"),
                ("育成コーチ", "渡辺七郎", "A", "若手成長支援"),
            ]
            
            for role, name, rank, effect in staff_list:
                row_rect = pygame.Rect(staff_rect.x + 15, y, staff_rect.width - 30, 45)
                pygame.draw.rect(self.screen, Colors.BG_INPUT, row_rect, border_radius=6)
                
                role_surf = fonts.small.render(role, True, Colors.TEXT_MUTED)
                self.screen.blit(role_surf, (row_rect.x + 10, y + 13))
                
                name_surf = fonts.body.render(name, True, Colors.TEXT_PRIMARY)
                self.screen.blit(name_surf, (row_rect.x + 160, y + 10))
                
                # ランク
                rank_colors = {"S": Colors.WARNING, "A": Colors.SUCCESS, "B": Colors.PRIMARY, "C": Colors.TEXT_MUTED}
                rank_color = rank_colors.get(rank, Colors.TEXT_MUTED)
                rank_surf = fonts.h3.render(rank, True, rank_color)
                self.screen.blit(rank_surf, (row_rect.x + 340, y + 8))
                
                effect_surf = fonts.tiny.render(effect, True, Colors.TEXT_SECONDARY)
                self.screen.blit(effect_surf, (row_rect.x + 400, y + 15))
                
                # 変更ボタン
                buttons[f"change_staff_{role}"] = Button(
                    row_rect.right - 90, y + 5, 70, 35,
                    "変更", "ghost", font=fonts.tiny
                )
                buttons[f"change_staff_{role}"].draw(self.screen)
                
                y += 52
        
        # 戻るボタン
        buttons["back"] = Button(
            50, height - 70, 150, 50,
            "← 戻る", "ghost", font=fonts.body
        )
        buttons["back"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    def draw_roster_management_screen(self, player_team: 'Team', selected_tab: str = "roster",
                                       selected_player_idx: int = -1, scroll_offset: int = 0,
                                       dragging_player_idx: int = -1, drag_pos: tuple = None,
                                       order_sub_tab: str = "batter", pitcher_scroll: int = 0,
                                       selected_rotation_slot: int = -1, selected_relief_slot: int = -1,
                                       roster_position_selected_slot: int = -1) -> dict:
        """選手登録管理画面（支配下・育成管理）- 改良版"""
        buttons = {}
        width, height = self.screen.get_size()
        header_h = 70
        
        # 背景
        draw_background(self.screen, "gradient")
        
        # ヘッダー
        header_rect = pygame.Rect(0, 0, width, header_h)
        pygame.draw.rect(self.screen, Colors.BG_CARD, header_rect)
        
        title_surf = fonts.h2.render("ROSTER MANAGEMENT", True, Colors.TEXT_PRIMARY)
        self.screen.blit(title_surf, (30, 20))
        
        # 登録状況サマリー
        roster_count = player_team.get_roster_count()
        dev_count = player_team.get_developmental_count()
        
        summary_text = f"支配下: {roster_count}/70  育成: {dev_count}/30"
        summary_surf = fonts.body.render(summary_text, True, Colors.TEXT_SECONDARY)
        self.screen.blit(summary_surf, (width - summary_surf.get_width() - 30, 25))
        
        # タブ
        tab_y = header_h + 8
        tabs = [
            ("order", "オーダー"),
            ("farm", "軍入れ替え"),
            ("players", "選手一覧"),
            ("foreign", "助っ人外国人"),
            ("trade", "トレード"),
        ]
        
        tab_x = 30
        tab_width = 100
        for tab_id, tab_name in tabs:
            is_active = tab_id == selected_tab
            btn = Button(
                tab_x, tab_y, tab_width, 36,
                tab_name, "primary" if is_active else "ghost", font=fonts.small
            )
            btn.draw(self.screen)
            buttons[f"tab_{tab_id}"] = btn
            tab_x += tab_width + 8
        
        content_y = tab_y + 48
        content_height = height - content_y - 70
        
        if selected_tab == "order":
            self._draw_order_tab(player_team, content_y, content_height, scroll_offset, selected_player_idx, buttons,
                                order_sub_tab, pitcher_scroll, selected_rotation_slot, selected_relief_slot,
                                roster_position_selected_slot)
        elif selected_tab == "farm":
            self._draw_farm_tab(player_team, content_y, content_height, scroll_offset, buttons)
        elif selected_tab == "players":
            self._draw_players_tab(player_team, content_y, content_height, scroll_offset, selected_player_idx, buttons)
        elif selected_tab == "foreign":
            self._draw_foreign_players_tab(player_team, content_y, content_height, scroll_offset, buttons)
        elif selected_tab == "trade":
            self._draw_trade_tab(player_team, content_y, content_height, scroll_offset, buttons)
        
        # ドラッグ中の選手表示
        if dragging_player_idx >= 0 and drag_pos and dragging_player_idx < len(player_team.players):
            player = player_team.players[dragging_player_idx]
            drag_rect = pygame.Rect(drag_pos[0] - 50, drag_pos[1] - 15, 100, 30)
            pygame.draw.rect(self.screen, Colors.PRIMARY, drag_rect, border_radius=6)
            drag_surf = fonts.small.render(player.name[:6], True, Colors.TEXT_PRIMARY)
            self.screen.blit(drag_surf, (drag_pos[0] - 40, drag_pos[1] - 8))
        
        # 戻るボタン
        buttons["back"] = Button(
            30, height - 60, 130, 45,
            "戻る", "ghost", font=fonts.body
        )
        buttons["back"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    def _draw_roster_tab(self, player_team, content_y, content_height, scroll_offset, selected_player_idx, buttons):
        """支配下選手タブを描画（改良版：コンパクトで一覧性向上）"""
        width = self.screen.get_width()
        
        # 並び替え状態を取得
        roster_sort_mode = getattr(self, '_roster_sort_mode', 'default')
        roster_sort_asc = getattr(self, '_roster_sort_asc', True)
        
        # 選手を投手/野手で分類
        pitchers = [(i, p) for i, p in enumerate(player_team.players) 
                   if not p.is_developmental and p.position.value == "投手"]
        batters = [(i, p) for i, p in enumerate(player_team.players) 
                  if not p.is_developmental and p.position.value != "投手"]
        
        # 並び替え（昇順/降順対応）
        if roster_sort_mode == 'overall':
            pitchers.sort(key=lambda x: x[1].overall_rating, reverse=not roster_sort_asc)
            batters.sort(key=lambda x: x[1].overall_rating, reverse=not roster_sort_asc)
        elif roster_sort_mode == 'age':
            pitchers.sort(key=lambda x: x[1].age, reverse=not roster_sort_asc)
            batters.sort(key=lambda x: x[1].age, reverse=not roster_sort_asc)
        
        # 左パネル: 投手一覧
        left_width = (width - 80) // 2
        left_card = Card(30, content_y, left_width, content_height, f"投手 {len(pitchers)}人")
        left_rect = left_card.draw(self.screen)
        
        # 右パネル: 野手一覧
        right_card = Card(50 + left_width, content_y, left_width, content_height, f"野手 {len(batters)}人")
        right_rect = right_card.draw(self.screen)
        
        # 並び替えボタン（左パネル上部）
        sort_btn_y = left_rect.y + 36
        overall_label = "総合↑" if roster_sort_mode == 'overall' and roster_sort_asc else "総合↓" if roster_sort_mode == 'overall' else "総合順"
        sort_btn_overall = Button(left_rect.x + 8, sort_btn_y, 50, 20, overall_label, "primary" if roster_sort_mode == 'overall' else "ghost", font=fonts.tiny)
        sort_btn_overall.draw(self.screen)
        buttons["roster_sort_overall"] = sort_btn_overall
        
        age_label = "年齢↑" if roster_sort_mode == 'age' and roster_sort_asc else "年齢↓" if roster_sort_mode == 'age' else "年齢順"
        sort_btn_age = Button(left_rect.x + 62, sort_btn_y, 50, 20, age_label, "primary" if roster_sort_mode == 'age' else "ghost", font=fonts.tiny)
        sort_btn_age.draw(self.screen)
        buttons["roster_sort_age"] = sort_btn_age
        
        row_height = 32
        header_height = 22
        
        # 投手リスト
        self._draw_player_list_compact(
            left_rect, pitchers, scroll_offset, selected_player_idx, 
            row_height, header_height, buttons, "pitcher",
            ["#", "名前", "タイプ", "球速", "制球", "スタミナ"]
        )
        
        # 野手リスト
        self._draw_player_list_compact(
            right_rect, batters, scroll_offset, selected_player_idx,
            row_height, header_height, buttons, "batter",
            ["#", "名前", "守備", "ミート", "パワー", "走力"]
        )
    
    def _draw_player_list_compact(self, card_rect, players, scroll_offset, selected_idx, 
                                   row_height, header_height, buttons, player_type, headers):
        """コンパクトな選手リストを描画"""
        y = card_rect.y + 45
        max_visible = (card_rect.height - 60) // row_height
        
        # ヘッダー
        col_widths = [35, 75, 55, 45, 45, 45] if player_type == "pitcher" else [35, 75, 55, 45, 45, 45]
        x = card_rect.x + 10
        for i, hdr in enumerate(headers):
            hdr_surf = fonts.tiny.render(hdr, True, Colors.TEXT_MUTED)
            self.screen.blit(hdr_surf, (x, y))
            x += col_widths[i]
        y += header_height
        
        # 選手行
        for i in range(scroll_offset, min(scroll_offset + max_visible, len(players))):
            idx, player = players[i]
            row_rect = pygame.Rect(card_rect.x + 5, y, card_rect.width - 25, row_height - 2)
            
            is_selected = idx == selected_idx
            bg_color = (*Colors.PRIMARY[:3], 60) if is_selected else Colors.BG_INPUT
            pygame.draw.rect(self.screen, bg_color, row_rect, border_radius=3)
            
            x = card_rect.x + 10
            
            # 背番号
            num_surf = fonts.tiny.render(str(player.uniform_number), True, Colors.TEXT_PRIMARY)
            self.screen.blit(num_surf, (x, y + 7))
            x += col_widths[0]
            
            # 名前
            name_surf = fonts.tiny.render(player.name[:5], True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_surf, (x, y + 7))
            x += col_widths[1]
            
            if player_type == "pitcher":
                # タイプ
                type_text = player.pitch_type.value[:2] if player.pitch_type else "-"
                type_surf = fonts.tiny.render(type_text, True, Colors.TEXT_SECONDARY)
                self.screen.blit(type_surf, (x, y + 7))
                x += col_widths[2]
                
                # 球速 (100スケール)
                speed_val = player.stats.to_100_scale(player.stats.speed)
                speed_color = self._get_stat_color(speed_val)
                speed_surf = fonts.tiny.render(str(speed_val), True, speed_color)
                self.screen.blit(speed_surf, (x, y + 7))
                x += col_widths[3]
                
                # 制球 (100スケール)
                ctrl_val = player.stats.to_100_scale(player.stats.control)
                ctrl_color = self._get_stat_color(ctrl_val)
                ctrl_surf = fonts.tiny.render(str(ctrl_val), True, ctrl_color)
                self.screen.blit(ctrl_surf, (x, y + 7))
                x += col_widths[4]
                
                # スタミナ (100スケール)
                stam_val = player.stats.to_100_scale(player.stats.stamina)
                stam_color = self._get_stat_color(stam_val)
                stam_surf = fonts.tiny.render(str(stam_val), True, stam_color)
                self.screen.blit(stam_surf, (x, y + 7))
            else:
                # 守備
                pos_text = player.position.value[:2]
                pos_surf = fonts.tiny.render(pos_text, True, Colors.TEXT_SECONDARY)
                self.screen.blit(pos_surf, (x, y + 7))
                x += col_widths[2]
                
                # ミート (100スケール)
                contact_val = player.stats.to_100_scale(player.stats.contact)
                contact_color = self._get_stat_color(contact_val)
                contact_surf = fonts.tiny.render(str(contact_val), True, contact_color)
                self.screen.blit(contact_surf, (x, y + 7))
                x += col_widths[3]
                
                # パワー (100スケール)
                power_val = player.stats.to_100_scale(player.stats.power)
                power_color = self._get_stat_color(power_val)
                power_surf = fonts.tiny.render(str(power_val), True, power_color)
                self.screen.blit(power_surf, (x, y + 7))
                x += col_widths[4]
                
                # 走力 (100スケール)
                run_val = player.stats.to_100_scale(player.stats.run)
                run_color = self._get_stat_color(run_val)
                run_surf = fonts.tiny.render(str(run_val), True, run_color)
                self.screen.blit(run_surf, (x, y + 7))
            
            # 詳細ボタン
            detail_btn = Button(row_rect.right - 40, y + 3, 35, row_height - 8, "詳", "outline", font=fonts.tiny)
            detail_btn.draw(self.screen)
            buttons[f"roster_detail_{idx}"] = detail_btn
            
            buttons[f"player_{idx}"] = row_rect
            y += row_height
        
        # スクロールバー
        if len(players) > max_visible:
            self._draw_scrollbar(card_rect, scroll_offset, len(players), max_visible)
    
    def _get_stat_color(self, value):
        """能力値に応じた色を返す"""
        if value >= 80:
            return Colors.WARNING  # 金
        elif value >= 70:
            return Colors.SUCCESS  # 緑
        elif value >= 50:
            return Colors.TEXT_PRIMARY  # 白
        else:
            return Colors.TEXT_MUTED  # グレー
    
    def _get_player_field_positions(self, player) -> str:
        """選手の守備適正を短縮表記で取得"""
        from models import Position
        
        # ポジション略称マップ
        pos_abbrev = {
            Position.CATCHER: "捕",
            Position.FIRST: "一",
            Position.SECOND: "二",
            Position.THIRD: "三",
            Position.SHORTSTOP: "遊",
            Position.OUTFIELD: "外",
            Position.PITCHER: "投"
        }
        
        positions = []
        # メインポジション
        main_abbrev = pos_abbrev.get(player.position, "?")
        positions.append(main_abbrev)
        
        # サブポジション
        sub_positions = getattr(player, 'sub_positions', []) or []
        for sub_pos in sub_positions[:2]:  # 最大2つまで表示
            abbrev = pos_abbrev.get(sub_pos, "")
            if abbrev and abbrev not in positions:
                positions.append(abbrev)
        
        return "".join(positions)
    
    def _draw_scrollbar(self, card_rect, scroll_offset, total_items, visible_items):
        """スクロールバーを描画"""
        scroll_track_h = card_rect.height - 60
        scroll_h = max(20, int(scroll_track_h * visible_items / total_items))
        max_scroll = total_items - visible_items
        scroll_y = card_rect.y + 45 + int((scroll_offset / max(1, max_scroll)) * (scroll_track_h - scroll_h))
        pygame.draw.rect(self.screen, Colors.BG_INPUT, 
                        (card_rect.right - 12, card_rect.y + 45, 6, scroll_track_h), border_radius=3)
        pygame.draw.rect(self.screen, Colors.PRIMARY, 
                        (card_rect.right - 12, scroll_y, 6, scroll_h), border_radius=3)

    def _draw_developmental_tab(self, player_team, content_y, content_height, scroll_offset, selected_player_idx, buttons):
        """育成選手タブを描画"""
        width = self.screen.get_width()
        
        card = Card(30, content_y, width - 60, content_height, "育成選手一覧")
        card_rect = card.draw(self.screen)
        
        dev_players = [(i, p) for i, p in enumerate(player_team.players) if p.is_developmental]
        
        row_height = 32
        y = card_rect.y + 45
        max_visible = (card_rect.height - 60) // row_height
        
        # ヘッダー
        headers = ["#", "名前", "位置", "年齢", "Pot", "能力"]
        col_widths = [35, 65, 50, 40, 60, 120]
        hx = card_rect.x + 15
        for i, hdr in enumerate(headers):
            hdr_surf = fonts.tiny.render(hdr, True, Colors.TEXT_MUTED)
            self.screen.blit(hdr_surf, (hx, y))
            hx += col_widths[i]
        y += 22
        
        for i in range(scroll_offset, min(scroll_offset + max_visible, len(dev_players))):
            idx, player = dev_players[i]
            row_rect = pygame.Rect(card_rect.x + 10, y, card_rect.width - 60, row_height - 2)
            
            is_selected = idx == selected_player_idx
            bg_color = (*Colors.PRIMARY[:3], 60) if is_selected else Colors.BG_INPUT
            pygame.draw.rect(self.screen, bg_color, row_rect, border_radius=4)
            
            x = card_rect.x + 15
            
            # 背番号
            num_surf = fonts.tiny.render(str(player.uniform_number), True, Colors.TEXT_PRIMARY)
            self.screen.blit(num_surf, (x, y + 7))
            x += col_widths[0]
            
            # 名前
            name_surf = fonts.tiny.render(player.name[:5], True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_surf, (x, y + 7))
            x += col_widths[1]
            
            # ポジション
            pos_text = player.position.value[:2]
            pos_surf = fonts.tiny.render(pos_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(pos_surf, (x, y + 7))
            x += col_widths[2]
            
            # 年齢
            age_surf = fonts.tiny.render(f"{player.age}", True, Colors.TEXT_SECONDARY)
            self.screen.blit(age_surf, (x, y + 7))
            x += col_widths[3]
            
            # ポテンシャル
            if hasattr(player, 'growth') and player.growth:
                pot = player.growth.potential
                pot_color = Colors.WARNING if pot >= 7 else Colors.SUCCESS if pot >= 5 else Colors.TEXT_MUTED
                pot_surf = fonts.tiny.render("★" * min(pot, 5), True, pot_color)
                self.screen.blit(pot_surf, (x, y + 7))
            x += col_widths[4]
            
            # 主要能力
            if player.position.value == "投手":
                stat_text = f"{player.stats.speed_to_kmh()}km 制{player.stats.control}"
            else:
                stat_text = f"ミ{player.stats.contact} パ{player.stats.power}"
            stat_surf = fonts.tiny.render(stat_text, True, Colors.TEXT_MUTED)
            self.screen.blit(stat_surf, (x, y + 7))
            
            # 詳細ボタン
            detail_btn = Button(row_rect.right - 40, y + 3, 35, row_height - 8, "詳", "outline", font=fonts.tiny)
            detail_btn.draw(self.screen)
            buttons[f"roster_detail_{idx}"] = detail_btn
            
            buttons[f"player_{idx}"] = row_rect
            y += row_height
        
        # スクロールバー
        if len(dev_players) > max_visible:
            self._draw_scrollbar(card_rect, scroll_offset, len(dev_players), max_visible)

    def _draw_promote_tab(self, player_team, content_y, content_height, scroll_offset, buttons, roster_count):
        """支配下昇格タブを描画"""
        width = self.screen.get_width()
        
        card = Card(30, content_y, width - 60, content_height, "育成 → 支配下 昇格")
        card_rect = card.draw(self.screen)
        
        # 説明と枠状況
        can_promote = player_team.can_add_roster_player()
        status_color = Colors.SUCCESS if can_promote else Colors.DANGER
        
        desc_surf = fonts.small.render("育成選手を支配下登録に昇格させます", True, Colors.TEXT_SECONDARY)
        self.screen.blit(desc_surf, (card_rect.x + 20, card_rect.y + 45))
        
        status_text = f"支配下枠: {roster_count}/70 {'(空きあり)' if can_promote else '(満員)'}"
        status_surf = fonts.body.render(status_text, True, status_color)
        self.screen.blit(status_surf, (card_rect.x + 20, card_rect.y + 70))
        
        dev_players = [(i, p) for i, p in enumerate(player_team.players) if p.is_developmental]
        
        row_height = 60  # 少し高くして詳細ボタンを収める
        y = card_rect.y + 110
        max_visible = (card_rect.height - 130) // row_height
        
        for i in range(scroll_offset, min(scroll_offset + max_visible, len(dev_players))):
            idx, player = dev_players[i]
            row_rect = pygame.Rect(card_rect.x + 15, y, card_rect.width - 180, row_height - 5)
            pygame.draw.rect(self.screen, Colors.BG_INPUT, row_rect, border_radius=6)
            
            # 選手情報（詳細表示）
            info_line1 = f"#{player.uniform_number} {player.name} ({player.position.value}) {player.age}歳"
            info_surf1 = fonts.small.render(info_line1, True, Colors.TEXT_PRIMARY)
            self.screen.blit(info_surf1, (row_rect.x + 15, y + 6))
            
            # 能力値と総合ランク
            if player.position.value == "投手":
                stat_text = f"{player.stats.speed_to_kmh()}km 制球:{player.stats.control} スタミナ:{player.stats.stamina}"
                overall = player.stats.overall_pitching()
            else:
                stat_text = f"ミート:{player.stats.contact} パワー:{player.stats.power} 走力:{player.stats.run}"
                overall = player.stats.overall_batting()
            
            # 総合ランク
            rank = player.stats.get_rank(overall)
            rank_color = player.stats.get_rank_color(overall)
            rank_text = f"  総合:{rank}"
            
            info_surf2 = fonts.tiny.render(stat_text, True, Colors.TEXT_MUTED)
            self.screen.blit(info_surf2, (row_rect.x + 15, y + 28))
            rank_surf = fonts.tiny.render(rank_text, True, rank_color)
            self.screen.blit(rank_surf, (row_rect.x + 260, y + 28))
            
            # 詳細ボタン（能力詳細を見るため）
            detail_btn = Button(row_rect.x + row_rect.width - 50, y + 35, 45, 20, "詳細", "outline", font=fonts.tiny)
            detail_btn.draw(self.screen)
            buttons[f"roster_detail_{idx}"] = detail_btn
            
            # 昇格ボタン
            if can_promote:
                promote_btn = Button(row_rect.right + 15, y + 8, 100, 34, "昇格", "primary", font=fonts.small)
                promote_btn.draw(self.screen)
                buttons[f"promote_{idx}"] = promote_btn
            else:
                # 枠なしの場合はグレーアウト
                disabled_surf = fonts.small.render("枠なし", True, Colors.TEXT_MUTED)
                self.screen.blit(disabled_surf, (row_rect.right + 35, y + 15))
            
            y += row_height
        
        # スクロールバー
        if len(dev_players) > max_visible:
            self._draw_scrollbar(card_rect, scroll_offset, len(dev_players), max_visible)
        
        # ホバー中の選手の能力プレビュー
        hovered_player = None
        mouse_pos = pygame.mouse.get_pos()
        check_y = card_rect.y + 110
        for i in range(scroll_offset, min(scroll_offset + max_visible, len(dev_players))):
            idx, player = dev_players[i]
            row_rect = pygame.Rect(card_rect.x + 15, check_y, card_rect.width - 180, row_height - 5)
            if row_rect.collidepoint(mouse_pos):
                hovered_player = player
                break
            check_y += row_height
        
        if hovered_player:
            self._draw_player_ability_preview(hovered_player)

    def _draw_order_tab(self, player_team, content_y, content_height, scroll_offset, selected_player_idx, buttons, 
                        order_sub_tab: str = "batter", pitcher_scroll: int = 0, 
                        selected_rotation_slot: int = -1, selected_relief_slot: int = -1,
                        roster_position_selected_slot: int = -1):
        """オーダー編成タブを描画"""
        width = self.screen.get_width()
        from settings_manager import settings
        from models import Position, TeamLevel
        
        # サブタブ描画
        sub_tab_y = content_y
        sub_tabs = [("batter", "野手オーダー"), ("pitcher", "投手オーダー")]
        sub_tab_x = 30
        for tab_id, tab_name in sub_tabs:
            is_active = tab_id == order_sub_tab
            btn = Button(sub_tab_x, sub_tab_y, 110, 30, tab_name, "primary" if is_active else "outline", font=fonts.small)
            btn.draw(self.screen)
            buttons[f"tab_{tab_id}_order"] = btn
            sub_tab_x += 118
        
        content_y += 40
        content_height -= 40
        
        if order_sub_tab == "pitcher":
            self._draw_pitcher_order_content(player_team, content_y, content_height, pitcher_scroll, 
                                            selected_rotation_slot, selected_relief_slot, buttons)
            return
        
        # ========== 野手オーダー画面（3分割） ==========
        drop_zones = {}
        
        # DH制の判定
        is_pacific = hasattr(player_team, 'league') and player_team.league.value == "パシフィック"
        use_dh = (is_pacific and settings.game_rules.pacific_dh) or (not is_pacific and settings.game_rules.central_dh)
        
        # 3分割のカラム幅
        col_width = (width - 80) // 3
        col_spacing = 10
        row_height = 32
        
        # ========================================
        # 左パネル: スタメン9人
        # ========================================
        starter_card = Card(20, content_y, col_width, content_height - 55, "スタメン")
        starter_rect = starter_card.draw(self.screen)
        
        if not hasattr(player_team, 'lineup_positions') or player_team.lineup_positions is None:
            player_team.lineup_positions = ["捕", "一", "二", "三", "遊", "左", "中", "右", "DH" if use_dh else "投"]
        
        # DHなしの場合、9番が「DH」なら「投」に修正
        if not use_dh and len(player_team.lineup_positions) >= 9:
            if player_team.lineup_positions[8] == "DH":
                player_team.lineup_positions[8] = "投"
        
        # ポジション選択状態を取得
        pos_selected_slot = getattr(self, '_order_pos_selected_slot', -1)
        
        y = starter_rect.y + 40
        for i in range(9):
            row_rect = pygame.Rect(starter_rect.x + 4, y, col_width - 12, row_height - 2)
            drop_zones[f"order_{i}"] = row_rect
            row_hovered = row_rect.collidepoint(pygame.mouse.get_pos())
            
            if i < len(player_team.current_lineup) and player_team.current_lineup[i] is not None:
                player_idx = player_team.current_lineup[i]
                if 0 <= player_idx < len(player_team.players):
                    player = player_team.players[player_idx]
                    is_selected = player_idx == selected_player_idx
                    
                    bg_color = (*Colors.PRIMARY[:3], 80) if is_selected else Colors.BG_HOVER if row_hovered else Colors.BG_INPUT
                    pygame.draw.rect(self.screen, bg_color, row_rect, border_radius=4)
                    if is_selected:
                        draw_selection_effect(self.screen, row_rect, Colors.PRIMARY, 0.7)
                    
                    x = starter_rect.x + 6
                    # 打順
                    num_surf = fonts.tiny.render(f"{i+1}", True, Colors.PRIMARY)
                    self.screen.blit(num_surf, (x, y + 7))
                    x += 16
                    
                    # 守備（クリックで入れ替え可能）
                    current_pos = player_team.lineup_positions[i] if i < len(player_team.lineup_positions) else "DH"
                    pos_btn_rect = pygame.Rect(x, y + 2, 26, row_height - 6)
                    pos_hovered = pos_btn_rect.collidepoint(pygame.mouse.get_pos())
                    is_pos_selected = pos_selected_slot == i
                    
                    if is_pos_selected:
                        pos_bg = (*Colors.WARNING[:3], 120)
                        pygame.draw.rect(self.screen, pos_bg, pos_btn_rect, border_radius=3)
                        pygame.draw.rect(self.screen, Colors.WARNING, pos_btn_rect, 2, border_radius=3)
                    else:
                        pos_bg = Colors.BG_HOVER if pos_hovered else Colors.BG_CARD
                        pygame.draw.rect(self.screen, pos_bg, pos_btn_rect, border_radius=3)
                        pygame.draw.rect(self.screen, Colors.SUCCESS, pos_btn_rect, 1, border_radius=3)
                    
                    pos_surf = fonts.tiny.render(current_pos, True, Colors.WARNING if is_pos_selected else Colors.SUCCESS)
                    pos_rect = pos_surf.get_rect(center=pos_btn_rect.center)
                    self.screen.blit(pos_surf, pos_rect)
                    buttons[f"change_pos_{i}"] = Button(pos_btn_rect.x, pos_btn_rect.y, pos_btn_rect.width, pos_btn_rect.height, "", "ghost")
                    x += 30
                    
                    # 総合力
                    overall = player.overall_rating
                    overall_color = Colors.GOLD if overall >= 700 else Colors.SUCCESS if overall >= 500 else Colors.TEXT_MUTED
                    overall_surf = fonts.tiny.render(f"★{overall}", True, overall_color)
                    self.screen.blit(overall_surf, (x, y + 7))
                    x += 45
                    
                    # 選手名
                    name_surf = fonts.tiny.render(f"#{player.uniform_number} {player.name[:3]}", True, Colors.TEXT_PRIMARY)
                    self.screen.blit(name_surf, (x, y + 7))
                    
                    # 守備適正（年齢の左）
                    field_positions = self._get_player_field_positions(player)
                    fp_surf = fonts.tiny.render(field_positions, True, Colors.TEXT_MUTED)
                    self.screen.blit(fp_surf, (row_rect.right - 90, y + 7))
                    
                    # 年齢
                    age_surf = fonts.tiny.render(f"{player.age}", True, Colors.TEXT_MUTED)
                    self.screen.blit(age_surf, (row_rect.right - 50, y + 7))
                    
                    # 詳細ボタン
                    detail_btn = Button(row_rect.right - 28, y + 4, 24, row_height - 8, "詳", "outline", font=fonts.tiny)
                    detail_btn.draw(self.screen)
                    buttons[f"order_detail_{player_idx}"] = detail_btn
                    
                    # スロットクリックで入れ替え
                    slot_btn = Button(row_rect.x + 50, row_rect.y, row_rect.width - 80, row_rect.height, "", "ghost")
                    buttons[f"lineup_slot_{i}"] = slot_btn
            else:
                pygame.draw.rect(self.screen, Colors.BG_CARD, row_rect, border_radius=4)
                pygame.draw.rect(self.screen, Colors.BORDER, row_rect, 1, border_radius=4)
                num_surf = fonts.tiny.render(f"{i+1}", True, Colors.TEXT_MUTED)
                self.screen.blit(num_surf, (starter_rect.x + 6, y + 7))
                empty_surf = fonts.tiny.render("空き", True, Colors.TEXT_MUTED)
                self.screen.blit(empty_surf, (starter_rect.x + 50, y + 7))
            
            y += row_height
        
        # ========================================
        # 中央パネル: 控え野手
        # ========================================
        bench_x = 20 + col_width + col_spacing
        bench_card = Card(bench_x, content_y, col_width, content_height - 55, "控え野手")
        bench_rect = bench_card.draw(self.screen)
        
        bench_batters = getattr(player_team, 'bench_batters', []) or []
        bench_batter_selected_idx = getattr(self, '_bench_batter_selected_idx', -1)
        y = bench_rect.y + 40
        
        for bi, b_idx in enumerate(bench_batters):
            if y >= bench_rect.bottom - 35:
                break
            if b_idx >= 0 and b_idx < len(player_team.players):
                bp = player_team.players[b_idx]
                bench_row = pygame.Rect(bench_rect.x + 4, y, col_width - 12, row_height - 2)
                
                is_hovered = bench_row.collidepoint(pygame.mouse.get_pos())
                is_selected = bench_batter_selected_idx == b_idx
                
                if is_selected:
                    bg_color = (*Colors.PRIMARY[:3], 100)
                elif is_hovered:
                    bg_color = Colors.BG_HOVER
                else:
                    bg_color = Colors.BG_INPUT
                pygame.draw.rect(self.screen, bg_color, bench_row, border_radius=3)
                
                if is_selected:
                    draw_selection_effect(self.screen, bench_row, Colors.PRIMARY, 0.7)
                
                # 総合力
                overall = bp.overall_rating
                overall_color = Colors.GOLD if overall >= 700 else Colors.SUCCESS if overall >= 500 else Colors.TEXT_MUTED
                overall_surf = fonts.tiny.render(f"★{overall}", True, overall_color)
                self.screen.blit(overall_surf, (bench_row.x + 4, y + 7))
                
                name_surf = fonts.tiny.render(f"#{bp.uniform_number} {bp.name[:3]}", True, Colors.TEXT_PRIMARY)
                self.screen.blit(name_surf, (bench_row.x + 38, y + 7))
                
                # 守備適正（年齢の左）
                field_positions = self._get_player_field_positions(bp)
                fp_surf = fonts.tiny.render(field_positions, True, Colors.TEXT_MUTED)
                self.screen.blit(fp_surf, (bench_row.right - 115, y + 7))
                
                # 年齢
                age_surf = fonts.tiny.render(f"{bp.age}", True, Colors.TEXT_MUTED)
                self.screen.blit(age_surf, (bench_row.right - 78, y + 7))
                
                # 詳細ボタン
                detail_btn = Button(bench_row.right - 56, y + 4, 24, 22, "詳", "outline", font=fonts.tiny)
                detail_btn.draw(self.screen)
                buttons[f"order_detail_{b_idx}"] = detail_btn
                
                # 降格ボタン
                remove_btn = Button(bench_row.right - 28, y + 4, 24, 22, "↓", "warning", font=fonts.tiny)
                remove_btn.draw(self.screen)
                buttons[f"demote_bench_batter_{b_idx}"] = remove_btn
                
                # クリック可能エリア（二軍選手との入れ替え用）
                btn = Button(bench_row.x, bench_row.y, bench_row.width - 60, bench_row.height, "", "ghost")
                buttons[f"bench_batter_{b_idx}"] = btn
                
                y += row_height
        
        # ========================================
        # 右パネル: 二軍野手一覧
        # ========================================
        right_x = bench_x + col_width + col_spacing
        
        # スタメン・控えにいる選手を除外
        used_players = set(player_team.current_lineup or [])
        used_players.update(bench_batters)
        
        # 二軍野手を取得（team_level=SECOND、またはteam_level未設定で一軍オーダーに入っていない選手）
        second_batters = []
        for i, p in enumerate(player_team.players):
            if p.is_developmental or p.position == Position.PITCHER:
                continue
            if i in used_players:
                continue
            level = getattr(p, 'team_level', None)
            # 明示的にSECOND、または未設定で一軍オーダー外
            if level == TeamLevel.SECOND or level is None:
                second_batters.append((i, p))
        
        # 並び替え状態を取得
        batter_sort_mode = getattr(self, '_batter_sort_mode', 'default')
        batter_sort_asc = getattr(self, '_batter_sort_asc', True)
        if batter_sort_mode == 'overall':
            second_batters.sort(key=lambda x: x[1].overall_rating, reverse=not batter_sort_asc)
        elif batter_sort_mode == 'age':
            second_batters.sort(key=lambda x: x[1].age, reverse=not batter_sort_asc)
        
        # 一軍人数をカウント（昇格ボタン表示判定用）
        # 一軍=スタメン+ベンチ野手+ローテーション+中継ぎ+抑え
        from settings_manager import settings
        first_limit = getattr(settings.game_rules, 'first_team_limit', 31)
        first_team_set = set(used_players)  # スタメン+ベンチ野手
        
        # 先発ローテーションを追加
        rotation = getattr(player_team, 'rotation', []) or []
        first_team_set.update(r_idx for r_idx in rotation if r_idx >= 0)
        
        # 中継ぎを追加
        setup_pitchers = getattr(player_team, 'setup_pitchers', []) or []
        first_team_set.update(s_idx for s_idx in setup_pitchers if s_idx >= 0)
        
        # 抑えを追加
        closer = getattr(player_team, 'closer_idx', -1)
        if closer >= 0:
            first_team_set.add(closer)
        
        first_count = len(first_team_set)
        has_first_vacancy = first_count < first_limit
        
        right_card = Card(right_x, content_y, col_width, content_height - 55, f"二軍野手 {len(second_batters)}人")
        right_rect = right_card.draw(self.screen)
        
        # 並び替えボタン
        sort_y = right_rect.y + 38
        overall_label = "総合↑" if batter_sort_mode == 'overall' and batter_sort_asc else "総合↓" if batter_sort_mode == 'overall' else "総合"
        sort_btn_overall = Button(right_rect.x + 4, sort_y, 40, 18, overall_label, "primary" if batter_sort_mode == 'overall' else "ghost", font=fonts.tiny)
        sort_btn_overall.draw(self.screen)
        buttons["batter_sort_overall"] = sort_btn_overall
        
        age_label = "年齢↑" if batter_sort_mode == 'age' and batter_sort_asc else "年齢↓" if batter_sort_mode == 'age' else "年齢"
        sort_btn_age = Button(right_rect.x + 48, sort_y, 40, 18, age_label, "primary" if batter_sort_mode == 'age' else "ghost", font=fonts.tiny)
        sort_btn_age.draw(self.screen)
        buttons["batter_sort_age"] = sort_btn_age
        
        # スクロールオフセットを取得
        batter_scroll = getattr(self, '_second_batter_scroll', 0)
        
        # 二軍野手選択状態を取得
        second_batter_selected_idx = getattr(self, '_second_batter_selected_idx', -1)
        
        y = right_rect.y + 60
        list_row_height = 28
        max_visible = (right_rect.height - 100) // list_row_height
        
        for si in range(batter_scroll, min(batter_scroll + max_visible, len(second_batters))):
            sidx, sp = second_batters[si]
            row = pygame.Rect(right_rect.x + 4, y, col_width - 12, list_row_height - 2)
            is_hovered = row.collidepoint(pygame.mouse.get_pos())
            is_selected = second_batter_selected_idx == sidx
            
            if is_selected:
                bg_color = (*Colors.PRIMARY[:3], 100)
            elif is_hovered:
                bg_color = Colors.BG_HOVER
            else:
                bg_color = Colors.BG_INPUT
            pygame.draw.rect(self.screen, bg_color, row, border_radius=3)
            
            if is_selected:
                draw_selection_effect(self.screen, row, Colors.PRIMARY, 0.7)
            
            # 総合力
            overall = sp.overall_rating
            overall_color = Colors.GOLD if overall >= 700 else Colors.SUCCESS if overall >= 500 else Colors.TEXT_MUTED
            overall_surf = fonts.tiny.render(f"★{overall}", True, overall_color)
            self.screen.blit(overall_surf, (row.x + 4, y + 5))
            
            name_surf = fonts.tiny.render(f"{sp.name[:3]}", True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_surf, (row.x + 38, y + 5))
            
            # 守備適正（年齢の左）
            field_positions = self._get_player_field_positions(sp)
            fp_surf = fonts.tiny.render(field_positions, True, Colors.TEXT_MUTED)
            self.screen.blit(fp_surf, (row.right - 115, y + 5))
            
            # 年齢
            age_surf = fonts.tiny.render(f"{sp.age}", True, Colors.TEXT_MUTED)
            self.screen.blit(age_surf, (row.right - 78, y + 5))
            
            # 詳細ボタン
            detail_btn = Button(row.right - 56, y + 2, 22, 22, "詳", "outline", font=fonts.tiny)
            detail_btn.draw(self.screen)
            buttons[f"order_detail_{sidx}"] = detail_btn
            
            # 一軍昇格ボタン（一軍枠に空きがある時のみ表示）
            if has_first_vacancy:
                promote_btn = Button(row.right - 30, y + 2, 26, 22, "↑", "success", font=fonts.tiny)
                promote_btn.draw(self.screen)
                buttons[f"promote_first_{sidx}"] = promote_btn
            
            # クリック可能エリア（選択用）- 一軍選手と入れ替え可能
            btn = Button(row.x, row.y, row.width - 60, row.height, "", "ghost")
            buttons[f"second_batter_{sidx}"] = btn
            
            y += list_row_height
        
        # スクロールバー表示（マウスホイールで操作）
        max_scroll = max(0, len(second_batters) - max_visible)
        if len(second_batters) > max_visible:
            self._draw_scrollbar(right_rect, batter_scroll, len(second_batters), max_visible)
        
        # 二軍野手リストエリアを保存（マウスホイール判定用）
        self._second_batter_list_rect = right_rect
        self._second_batter_max_scroll = max_scroll
        
        # ホバー中の選手プレビュー
        hovered_player = None
        mouse_pos = pygame.mouse.get_pos()
        
        # スタメンからホバー検出
        check_y = starter_rect.y + 40
        for i in range(9):
            row_rect = pygame.Rect(starter_rect.x + 4, check_y, col_width - 12, row_height - 2)
            if row_rect.collidepoint(mouse_pos):
                if i < len(player_team.current_lineup) and player_team.current_lineup[i] is not None:
                    player_idx = player_team.current_lineup[i]
                    if 0 <= player_idx < len(player_team.players):
                        hovered_player = player_team.players[player_idx]
                break
            check_y += row_height
        
        # 控えからホバー検出
        if not hovered_player:
            check_y = bench_rect.y + 40
            for b_idx in bench_batters:
                if check_y >= bench_rect.bottom - 35:
                    break
                if b_idx >= 0 and b_idx < len(player_team.players):
                    bench_row = pygame.Rect(bench_rect.x + 4, check_y, col_width - 12, row_height - 2)
                    if bench_row.collidepoint(mouse_pos):
                        hovered_player = player_team.players[b_idx]
                        break
                    check_y += row_height
        
        # 二軍一覧からホバー検出
        if not hovered_player:
            check_y = right_rect.y + 40
            for sidx, sp in second_batters:
                if check_y >= right_rect.bottom - 35:
                    break
                row = pygame.Rect(right_rect.x + 4, check_y, col_width - 12, list_row_height - 2)
                if row.collidepoint(mouse_pos):
                    hovered_player = sp
                    break
                check_y += list_row_height
        
        if hovered_player:
            self._draw_player_ability_preview(hovered_player)
        
        # 下部ボタン
        btn_y = content_y + content_height - 45
        auto_btn = Button(20, btn_y, 120, 38, "自動編成", "primary", font=fonts.small)
        auto_btn.draw(self.screen)
        buttons["auto_lineup"] = auto_btn
        
        buttons["_drop_zones"] = drop_zones

    def _draw_pitcher_order_content(self, player_team, content_y, content_height, pitcher_scroll, 
                                     selected_rotation_slot, selected_relief_slot, buttons):
        """投手オーダータブのコンテンツを描画（先発ローテ・中継ぎ・抑え・投手一覧）"""
        width = self.screen.get_width()
        from models import Position, TeamLevel
        
        # ローテーション、中継ぎ、抑えに設定されている投手を取得
        rotation = getattr(player_team, 'rotation', []) or []
        while len(rotation) < 8:
            rotation.append(-1)
        player_team.rotation = rotation[:8]
        
        setup_pitchers = getattr(player_team, 'setup_pitchers', []) or []
        while len(setup_pitchers) < 8:
            setup_pitchers.append(-1)
        player_team.setup_pitchers = setup_pitchers[:8]
        
        closer_idx = getattr(player_team, 'closer_idx', -1)
        
        # 使用中の投手を取得（先発・中継ぎ・抑え）
        used_pitchers = set()
        for r in rotation:
            if r >= 0:
                used_pitchers.add(r)
        for s in setup_pitchers:
            if s >= 0:
                used_pitchers.add(s)
        if closer_idx >= 0:
            used_pitchers.add(closer_idx)
        
        # 一軍人数をカウント（昇格ボタン表示判定用）
        from settings_manager import settings
        first_limit = getattr(settings.game_rules, 'first_team_limit', 31)
        # 一軍=スタメン+ベンチ野手+ローテーション+中継ぎ+抑え
        first_team_set = set(used_pitchers)  # ローテーション+中継ぎ+抑え
        
        # スタメン野手を追加
        lineup = getattr(player_team, 'current_lineup', []) or []
        first_team_set.update(p_idx for p_idx in lineup if p_idx is not None and p_idx >= 0)
        
        # ベンチ野手を追加
        bench_batters = getattr(player_team, 'bench_batters', []) or []
        first_team_set.update(b_idx for b_idx in bench_batters if b_idx >= 0)
        
        first_count = len(first_team_set)
        has_first_vacancy = first_count < first_limit
        
        # 二軍投手を取得（オーダーに入っていない投手を自動的に二軍に設定）
        second_team_pitchers = []
        for i, p in enumerate(player_team.players):
            if p.position != Position.PITCHER or p.is_developmental:
                continue
            
            # オーダーに入っていない投手は自動的に二軍に設定
            if i not in used_pitchers:
                p.team_level = TeamLevel.SECOND
                second_team_pitchers.append((i, p))
            else:
                # オーダーに入っている投手は一軍に設定
                p.team_level = TeamLevel.FIRST
        
        # レイアウト計算（左半分：オーダー、右半分：投手一覧）
        left_half_width = (width - 50) // 2
        right_half_width = left_half_width
        slot_panel_width = (left_half_width - 10) // 2  # 先発と中継ぎ用
        row_height = 36  # 行の高さを広げる
        
        # ========================================
        # 左上: 先発ローテーション
        # ========================================
        starter_height = row_height * 8 + 50
        starter_card = Card(20, content_y + 5, slot_panel_width, starter_height, "先発")
        starter_rect = starter_card.draw(self.screen)
        y = starter_rect.y + 30
        for i in range(8):
            row_rect = pygame.Rect(starter_rect.x + 4, y, slot_panel_width - 12, row_height - 2)
            is_selected = i == selected_rotation_slot
            is_hovered = row_rect.collidepoint(pygame.mouse.get_pos())
            
            if is_selected:
                bg_color = (*Colors.PRIMARY[:3], 80)
            elif is_hovered:
                bg_color = Colors.BG_HOVER
            else:
                bg_color = Colors.BG_INPUT
            pygame.draw.rect(self.screen, bg_color, row_rect, border_radius=3)
            
            if is_selected:
                draw_selection_effect(self.screen, row_rect, Colors.PRIMARY, 0.7)
            
            num_surf = fonts.small.render(f"{i + 1}.", True, Colors.INFO)
            self.screen.blit(num_surf, (row_rect.x + 6, y + 8))
            
            pitcher_idx = rotation[i] if i < len(rotation) else -1
            if pitcher_idx >= 0 and pitcher_idx < len(player_team.players):
                pitcher = player_team.players[pitcher_idx]
                apt = getattr(pitcher, 'starter_aptitude', 50)
                apt_mark = "◎" if apt >= 70 else "○" if apt >= 40 else "-"
                apt_color = Colors.SUCCESS if apt >= 70 else Colors.WARNING if apt >= 40 else Colors.TEXT_MUTED
                apt_surf = fonts.small.render(apt_mark, True, apt_color)
                self.screen.blit(apt_surf, (row_rect.x + 28, y + 8))
                
                # 総合力
                overall = pitcher.overall_rating
                overall_color = Colors.GOLD if overall >= 700 else Colors.SUCCESS if overall >= 500 else Colors.TEXT_MUTED
                overall_surf = fonts.tiny.render(f"★{overall}", True, overall_color)
                self.screen.blit(overall_surf, (row_rect.x + 46, y + 10))
                
                name_surf = fonts.tiny.render(f"#{pitcher.uniform_number} {pitcher.name[:3]}", True, Colors.TEXT_PRIMARY)
                self.screen.blit(name_surf, (row_rect.x + 80, y + 10))
                
                # 年齢
                age_surf = fonts.tiny.render(f"{pitcher.age}", True, Colors.TEXT_MUTED)
                self.screen.blit(age_surf, (row_rect.right - 70, y + 10))
                
                # 詳細ボタン
                detail_btn = Button(row_rect.right - 48, y + 4, 22, 26, "詳", "outline", font=fonts.tiny)
                detail_btn.draw(self.screen)
                buttons[f"order_detail_{pitcher_idx}"] = detail_btn
                
                remove_btn = Button(row_rect.right - 22, y + 4, 18, 26, "×", "danger", font=fonts.small)
                remove_btn.draw(self.screen)
                buttons[f"remove_rotation_{i}"] = remove_btn
            else:
                empty_surf = fonts.small.render("空き", True, Colors.TEXT_MUTED)
                self.screen.blit(empty_surf, (row_rect.x + 50, y + 8))
            
            btn = Button(row_rect.x, row_rect.y, row_rect.width - 54, row_rect.height, "", "ghost")
            buttons[f"rotation_slot_{i}"] = btn
            y += row_height
        
        # ========================================
        # 右上: 中継ぎ
        # ========================================
        relief_x = 20 + slot_panel_width + 5
        relief_card = Card(relief_x, content_y + 5, slot_panel_width, starter_height, "中継ぎ")
        relief_rect = relief_card.draw(self.screen)
        
        y = relief_rect.y + 36
        for i in range(8):
            row_rect = pygame.Rect(relief_rect.x + 4, y, slot_panel_width - 12, row_height - 2)
            is_selected = i == selected_relief_slot
            is_hovered = row_rect.collidepoint(pygame.mouse.get_pos())
            
            if is_selected:
                bg_color = (*Colors.SUCCESS[:3], 80)
            elif is_hovered:
                bg_color = Colors.BG_HOVER
            else:
                bg_color = Colors.BG_INPUT
            pygame.draw.rect(self.screen, bg_color, row_rect, border_radius=3)
            
            if is_selected:
                draw_selection_effect(self.screen, row_rect, Colors.SUCCESS, 0.7)
            
            num_surf = fonts.small.render(f"{i + 1}.", True, Colors.SUCCESS)
            self.screen.blit(num_surf, (row_rect.x + 6, y + 8))
            
            if i < len(setup_pitchers) and setup_pitchers[i] >= 0:
                pitcher_idx = setup_pitchers[i]
                if pitcher_idx < len(player_team.players):
                    pitcher = player_team.players[pitcher_idx]
                    apt = getattr(pitcher, 'middle_aptitude', 50)
                    apt_mark = "◎" if apt >= 70 else "○" if apt >= 40 else "-"
                    apt_color = Colors.SUCCESS if apt >= 70 else Colors.WARNING if apt >= 40 else Colors.TEXT_MUTED
                    apt_surf = fonts.small.render(apt_mark, True, apt_color)
                    self.screen.blit(apt_surf, (row_rect.x + 28, y + 8))
                    
                    # 総合力
                    overall = pitcher.overall_rating
                    overall_color = Colors.GOLD if overall >= 700 else Colors.SUCCESS if overall >= 500 else Colors.TEXT_MUTED
                    overall_surf = fonts.tiny.render(f"★{overall}", True, overall_color)
                    self.screen.blit(overall_surf, (row_rect.x + 46, y + 10))
                    
                    name_surf = fonts.tiny.render(f"#{pitcher.uniform_number} {pitcher.name[:3]}", True, Colors.TEXT_PRIMARY)
                    self.screen.blit(name_surf, (row_rect.x + 80, y + 10))
                    
                    # 年齢
                    age_surf = fonts.tiny.render(f"{pitcher.age}", True, Colors.TEXT_MUTED)
                    self.screen.blit(age_surf, (row_rect.right - 70, y + 10))
                    
                    # 詳細ボタン
                    detail_btn = Button(row_rect.right - 48, y + 4, 22, 26, "詳", "outline", font=fonts.tiny)
                    detail_btn.draw(self.screen)
                    buttons[f"order_detail_{pitcher_idx}"] = detail_btn
                    
                    remove_btn = Button(row_rect.right - 22, y + 4, 18, 26, "×", "danger", font=fonts.small)
                    remove_btn.draw(self.screen)
                    buttons[f"remove_relief_{i}"] = remove_btn
            else:
                empty_surf = fonts.small.render("空き", True, Colors.TEXT_MUTED)
                self.screen.blit(empty_surf, (row_rect.x + 50, y + 8))
            
            btn = Button(row_rect.x, row_rect.y, row_rect.width - 54, row_rect.height, "", "ghost")
            buttons[f"relief_slot_{i}"] = btn
            y += row_height
        
        # ========================================
        # 下: 抑え
        # ========================================
        closer_y = content_y + 5 + starter_height + 5
        closer_card = Card(20, closer_y, left_half_width, row_height + 42, "抑え")
        closer_rect = closer_card.draw(self.screen)
        
        y = closer_rect.y + 36
        row_rect = pygame.Rect(closer_rect.x + 4, y, left_half_width - 12, row_height - 2)
        is_closer_selected = selected_rotation_slot == -99
        is_hovered = row_rect.collidepoint(pygame.mouse.get_pos())
        
        if is_closer_selected:
            bg_color = (*Colors.DANGER[:3], 80)
        elif is_hovered:
            bg_color = Colors.BG_HOVER
        else:
            bg_color = Colors.BG_INPUT
        pygame.draw.rect(self.screen, bg_color, row_rect, border_radius=3)
        
        if is_closer_selected:
            draw_selection_effect(self.screen, row_rect, Colors.DANGER, 0.7)
        
        guardian_text = fonts.small.render("守", True, Colors.DANGER)
        self.screen.blit(guardian_text, (row_rect.x + 8, y + 8))
        
        if closer_idx >= 0 and closer_idx < len(player_team.players):
            closer = player_team.players[closer_idx]
            apt = getattr(closer, 'closer_aptitude', 50)
            apt_mark = "◎" if apt >= 70 else "○" if apt >= 40 else "-"
            apt_color = Colors.SUCCESS if apt >= 70 else Colors.WARNING if apt >= 40 else Colors.TEXT_MUTED
            apt_surf = fonts.small.render(apt_mark, True, apt_color)
            self.screen.blit(apt_surf, (row_rect.x + 32, y + 8))
            
            # 総合力
            overall = closer.overall_rating
            overall_color = Colors.GOLD if overall >= 700 else Colors.SUCCESS if overall >= 500 else Colors.TEXT_MUTED
            overall_surf = fonts.tiny.render(f"★{overall}", True, overall_color)
            self.screen.blit(overall_surf, (row_rect.x + 52, y + 10))
            
            name_surf = fonts.tiny.render(f"#{closer.uniform_number} {closer.name[:3]}", True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_surf, (row_rect.x + 86, y + 10))
            
            # 年齢
            age_surf = fonts.tiny.render(f"{closer.age}", True, Colors.TEXT_MUTED)
            self.screen.blit(age_surf, (row_rect.right - 70, y + 10))
            
            # 詳細ボタン
            detail_btn = Button(row_rect.right - 48, y + 4, 22, 26, "詳", "outline", font=fonts.tiny)
            detail_btn.draw(self.screen)
            buttons[f"order_detail_{closer_idx}"] = detail_btn
            
            remove_btn = Button(row_rect.right - 22, y + 4, 18, 26, "×", "danger", font=fonts.small)
            remove_btn.draw(self.screen)
            buttons["remove_closer"] = remove_btn
        else:
            empty_surf = fonts.small.render("空き", True, Colors.TEXT_MUTED)
            self.screen.blit(empty_surf, (row_rect.x + 56, y + 8))
        
        btn = Button(row_rect.x, row_rect.y, row_rect.width - 54, row_rect.height, "", "ghost")
        buttons["closer_slot"] = btn
        
        # 自動編成ボタン
        auto_btn = Button(20 + left_half_width - 100, closer_y + row_height + 42 + 8, 90, 32, "自動編成", "primary", font=fonts.tiny)
        auto_btn.draw(self.screen)
        buttons["auto_pitcher_order"] = auto_btn
        
        # ========================================
        # 右半分: 二軍投手一覧
        # ========================================
        right_x = 20 + left_half_width + 10
        list_card = Card(right_x, content_y + 5, right_half_width, content_height - 10, "二軍投手一覧")
        list_rect = list_card.draw(self.screen)
        
        # 並び替え状態を取得
        pitcher_sort_mode = getattr(self, '_pitcher_sort_mode', 'default')
        pitcher_sort_asc = getattr(self, '_pitcher_sort_asc', True)
        if pitcher_sort_mode == 'overall':
            second_team_pitchers.sort(key=lambda x: x[1].overall_rating, reverse=not pitcher_sort_asc)
        elif pitcher_sort_mode == 'age':
            second_team_pitchers.sort(key=lambda x: x[1].age, reverse=not pitcher_sort_asc)
        
        # 並び替えボタン
        sort_btn_y = list_rect.y + 34
        overall_label = "総合↑" if pitcher_sort_mode == 'overall' and pitcher_sort_asc else "総合↓" if pitcher_sort_mode == 'overall' else "総合"
        sort_btn_overall_p = Button(list_rect.right - 90, sort_btn_y, 40, 18, overall_label, "primary" if pitcher_sort_mode == 'overall' else "ghost", font=fonts.tiny)
        sort_btn_overall_p.draw(self.screen)
        buttons["pitcher_sort_overall"] = sort_btn_overall_p
        
        age_label = "年齢↑" if pitcher_sort_mode == 'age' and pitcher_sort_asc else "年齢↓" if pitcher_sort_mode == 'age' else "年齢"
        sort_btn_age_p = Button(list_rect.right - 46, sort_btn_y, 40, 18, age_label, "primary" if pitcher_sort_mode == 'age' else "ghost", font=fonts.tiny)
        sort_btn_age_p.draw(self.screen)
        buttons["pitcher_sort_age"] = sort_btn_age_p
        
        # 選択中のスロット表示
        slot_info_y = list_rect.y + 55
        if selected_rotation_slot >= 0:
            slot_text = f"▼ 先発 {selected_rotation_slot + 1}番 に追加"
            slot_color = Colors.INFO
        elif selected_relief_slot >= 0:
            slot_text = f"▼ 中継ぎ {selected_relief_slot + 1}番 に追加"
            slot_color = Colors.SUCCESS
        elif selected_rotation_slot == -99:
            slot_text = "▼ 抑え に追加"
            slot_color = Colors.DANGER
        else:
            slot_text = "← スロットを選択"
            slot_color = Colors.TEXT_MUTED
        
        slot_info_surf = fonts.tiny.render(slot_text, True, slot_color)
        self.screen.blit(slot_info_surf, (list_rect.x + 8, slot_info_y))
        
        # 使用中の投手を取得
        # 二軍投手選択状態を取得
        second_pitcher_selected_idx = getattr(self, '_second_pitcher_selected_idx', -1)
        
        # ヘッダー
        list_row_height = 32
        list_y = slot_info_y + 18
        hdr_x = list_rect.x + 8
        for hdr, w in [("総合", 38), ("選手名", 85), ("先", 22), ("中", 22), ("抑", 22), ("", 40)]:
            hdr_surf = fonts.tiny.render(hdr, True, Colors.TEXT_MUTED)
            self.screen.blit(hdr_surf, (hdr_x, list_y))
            hdr_x += w
        list_y += 18
        
        max_visible = (list_rect.height - 120) // list_row_height
        
        # 二軍投手を表示
        for si in range(pitcher_scroll, min(pitcher_scroll + max_visible, len(second_team_pitchers))):
            sidx, sp = second_team_pitchers[si]
            row_rect = pygame.Rect(list_rect.x + 4, list_y, list_rect.width - 12, list_row_height - 2)
            is_hovered = row_rect.collidepoint(pygame.mouse.get_pos())
            is_selected = second_pitcher_selected_idx == sidx
            
            if is_selected:
                bg_color = (*Colors.PRIMARY[:3], 100)
            elif is_hovered:
                bg_color = (*Colors.SUCCESS[:3], 80) if (selected_rotation_slot >= 0 or selected_relief_slot >= 0 or selected_rotation_slot == -99) else Colors.BG_HOVER
            else:
                bg_color = Colors.BG_INPUT
            pygame.draw.rect(self.screen, bg_color, row_rect, border_radius=3)
            
            if is_selected:
                draw_selection_effect(self.screen, row_rect, Colors.PRIMARY, 0.7)
            elif is_hovered:
                draw_selection_effect(self.screen, row_rect, Colors.SUCCESS, 0.5)
            
            text_color = Colors.TEXT_PRIMARY
            x = list_rect.x + 8
            
            # 総合力
            overall = sp.overall_rating
            overall_color = Colors.GOLD if overall >= 700 else Colors.SUCCESS if overall >= 500 else Colors.TEXT_MUTED
            overall_surf = fonts.tiny.render(str(overall), True, overall_color)
            self.screen.blit(overall_surf, (x, list_y + 8))
            x += 38
            
            # 選手名
            name_surf = fonts.tiny.render(f"{sp.name[:4]}", True, text_color)
            self.screen.blit(name_surf, (x, list_y + 8))
            x += 70
            
            # 年齢
            age_surf = fonts.tiny.render(f"{sp.age}", True, Colors.TEXT_MUTED)
            self.screen.blit(age_surf, (x, list_y + 8))
            x += 25
            
            # 適性（先発）
            starter_apt = getattr(sp, 'starter_aptitude', 50)
            starter_mark = "◎" if starter_apt >= 70 else "○" if starter_apt >= 40 else "-"
            starter_color = Colors.SUCCESS if starter_apt >= 70 else Colors.WARNING if starter_apt >= 40 else Colors.TEXT_MUTED
            self.screen.blit(fonts.tiny.render(starter_mark, True, starter_color), (x, list_y + 8))
            x += 18
            
            # 適性（中継ぎ）
            middle_apt = getattr(sp, 'middle_aptitude', 50)
            middle_mark = "◎" if middle_apt >= 70 else "○" if middle_apt >= 40 else "-"
            middle_color = Colors.SUCCESS if middle_apt >= 70 else Colors.WARNING if middle_apt >= 40 else Colors.TEXT_MUTED
            self.screen.blit(fonts.tiny.render(middle_mark, True, middle_color), (x, list_y + 8))
            x += 18
            
            # 適性（抑え）
            closer_apt = getattr(sp, 'closer_aptitude', 50)
            closer_mark = "◎" if closer_apt >= 70 else "○" if closer_apt >= 40 else "-"
            closer_color = Colors.SUCCESS if closer_apt >= 70 else Colors.WARNING if closer_apt >= 40 else Colors.TEXT_MUTED
            self.screen.blit(fonts.tiny.render(closer_mark, True, closer_color), (x, list_y + 8))
            
            # 詳細ボタン
            detail_btn = Button(row_rect.right - 26, list_y + 4, 22, 22, "詳", "outline", font=fonts.tiny)
            detail_btn.draw(self.screen)
            buttons[f"order_detail_{sidx}"] = detail_btn
            
            # クリック可能エリア（選択用）
            btn = Button(row_rect.x, row_rect.y, row_rect.width - 30, row_rect.height, "", "ghost")
            buttons[f"second_pitcher_{sidx}"] = btn
            
            list_y += list_row_height
        
        # スクロールバー表示（ボタンなし、マウスホイールで操作）
        if len(second_team_pitchers) > max_visible:
            self._draw_scrollbar(list_rect, pitcher_scroll, len(second_team_pitchers), max_visible)
        
        # 二軍投手リストエリアを保存（マウスホイール判定用）
        self._second_pitcher_list_rect = list_rect
        self._second_pitcher_max_scroll = max(0, len(second_team_pitchers) - max_visible)
        
        # ホバー中の投手プレビュー（先発/中継ぎ/抑え + 二軍投手）
        hovered_player = None
        mouse_pos = pygame.mouse.get_pos()
        
        # 先発ローテーションのホバーチェック
        starter_check_y = starter_rect.y + 30
        for i in range(8):
            row_rect = pygame.Rect(starter_rect.x + 4, starter_check_y, slot_panel_width - 12, row_height - 2)
            if row_rect.collidepoint(mouse_pos):
                pitcher_idx = rotation[i] if i < len(rotation) else -1
                if pitcher_idx >= 0 and pitcher_idx < len(player_team.players):
                    hovered_player = player_team.players[pitcher_idx]
                break
            starter_check_y += row_height
        
        # 中継ぎのホバーチェック
        if not hovered_player:
            relief_check_y = relief_rect.y + 30
            for i in range(8):
                row_rect = pygame.Rect(relief_rect.x + 4, relief_check_y, slot_panel_width - 12, row_height - 2)
                if row_rect.collidepoint(mouse_pos):
                    if i < len(setup_pitchers) and setup_pitchers[i] >= 0:
                        pitcher_idx = setup_pitchers[i]
                        if pitcher_idx < len(player_team.players):
                            hovered_player = player_team.players[pitcher_idx]
                    break
                relief_check_y += row_height
        
        # 抑えのホバーチェック
        if not hovered_player:
            closer_row_rect = pygame.Rect(closer_rect.x + 4, closer_rect.y + 36, left_half_width - 12, row_height - 2)
            if closer_row_rect.collidepoint(mouse_pos):
                if closer_idx >= 0 and closer_idx < len(player_team.players):
                    hovered_player = player_team.players[closer_idx]
        
        # 二軍投手リストのホバーチェック
        if not hovered_player:
            check_y = slot_info_y + 52
            for si in range(pitcher_scroll, min(pitcher_scroll + max_visible, len(second_team_pitchers))):
                sidx, sp = second_team_pitchers[si]
                row_rect = pygame.Rect(list_rect.x + 4, check_y, list_rect.width - 12, list_row_height - 2)
                if row_rect.collidepoint(mouse_pos):
                    hovered_player = sp
                    break
                check_y += list_row_height
        
        if hovered_player:
            self._draw_player_ability_preview(hovered_player)

    def _draw_release_tab(self, player_team, content_y, content_height, scroll_offset, buttons):
        """自由契約タブを描画"""
        width = self.screen.get_width()
        
        card = Card(30, content_y, width - 60, content_height, "自由契約（選手解雇）")
        card_rect = card.draw(self.screen)
        
        desc_surf = fonts.small.render("選手を自由契約にして登録枠を空けます。解雇した選手は戻ってきません。", True, Colors.TEXT_SECONDARY)
        self.screen.blit(desc_surf, (card_rect.x + 20, card_rect.y + 45))
        
        # 並び替えボタン
        release_sort_mode = getattr(self, '_release_sort_mode', 'default')
        sort_y = card_rect.y + 42
        sort_btn_overall = Button(card_rect.right - 150, sort_y, 50, 22, "総合順", "primary" if release_sort_mode == 'overall' else "ghost", font=fonts.tiny)
        sort_btn_overall.draw(self.screen)
        buttons["release_sort_overall"] = sort_btn_overall
        
        sort_btn_age = Button(card_rect.right - 95, sort_y, 50, 22, "年齢順", "primary" if release_sort_mode == 'age' else "ghost", font=fonts.tiny)
        sort_btn_age.draw(self.screen)
        buttons["release_sort_age"] = sort_btn_age
        
        # 支配下選手のみ
        players = [(i, p) for i, p in enumerate(player_team.players) if not p.is_developmental]
        
        # 並び替え
        if release_sort_mode == 'overall':
            players.sort(key=lambda x: x[1].overall_rating, reverse=True)
        elif release_sort_mode == 'age':
            players.sort(key=lambda x: x[1].age)
        
        row_height = 36
        y = card_rect.y + 80
        max_visible = (card_rect.height - 100) // row_height
        
        for i in range(scroll_offset, min(scroll_offset + max_visible, len(players))):
            idx, player = players[i]
            row_rect = pygame.Rect(card_rect.x + 15, y, card_rect.width - 150, row_height - 4)
            
            # ホバーエフェクト
            is_hovered = row_rect.collidepoint(pygame.mouse.get_pos())
            bg_color = Colors.BG_HOVER if is_hovered else Colors.BG_INPUT
            pygame.draw.rect(self.screen, bg_color, row_rect, border_radius=4)
            if is_hovered:
                draw_selection_effect(self.screen, row_rect, Colors.DANGER, 0.4)
            
            # 総合力
            overall = player.overall_rating
            overall_color = Colors.GOLD if overall >= 700 else Colors.SUCCESS if overall >= 500 else Colors.TEXT_MUTED
            overall_surf = fonts.tiny.render(str(overall), True, overall_color)
            self.screen.blit(overall_surf, (row_rect.x + 10, y + 10))
            
            # ポジション
            pos_text = player.position.value[:2] if player.position.value != "外野手" else "外"
            pos_surf = fonts.tiny.render(pos_text, True, Colors.SUCCESS)
            self.screen.blit(pos_surf, (row_rect.x + 50, y + 10))
            
            # 選手名
            name_surf = fonts.small.render(f"#{player.uniform_number} {player.name}", True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_surf, (row_rect.x + 75, y + 8))
            
            # 年齢
            age_surf = fonts.tiny.render(f"{player.age}歳", True, Colors.TEXT_MUTED)
            self.screen.blit(age_surf, (row_rect.right - 140, y + 10))
            
            # 年俸
            if player.salary >= 100000000:
                salary_text = f"{player.salary // 100000000}億"
            else:
                salary_text = f"{player.salary // 10000}万"
            salary_surf = fonts.tiny.render(salary_text, True, Colors.WARNING)
            self.screen.blit(salary_surf, (row_rect.right - 80, y + 10))
            
            # 詳細ボタン
            detail_btn = Button(row_rect.right - 35, y + 4, 30, 26, "詳", "outline", font=fonts.tiny)
            detail_btn.draw(self.screen)
            buttons[f"roster_detail_{idx}"] = detail_btn
            
            # 解雇ボタン
            release_btn = Button(row_rect.right + 15, y + 2, 80, 28, "解雇", "danger", font=fonts.small)
            release_btn.draw(self.screen)
            buttons[f"release_{idx}"] = release_btn
            
            y += row_height
        
        if len(players) > max_visible:
            self._draw_scrollbar(card_rect, scroll_offset, len(players), max_visible)
        
        # ホバー中の選手の能力プレビュー
        hovered_player = None
        mouse_pos = pygame.mouse.get_pos()
        check_y = card_rect.y + 80
        for i in range(scroll_offset, min(scroll_offset + max_visible, len(players))):
            idx, player = players[i]
            row_rect = pygame.Rect(card_rect.x + 15, check_y, card_rect.width - 150, row_height - 4)
            if row_rect.collidepoint(mouse_pos):
                hovered_player = player
                break
            check_y += row_height
        
        if hovered_player:
            self._draw_player_ability_preview(hovered_player)

    def _draw_foreign_players_tab(self, player_team, content_y, content_height, scroll_offset, buttons):
        """助っ人外国人タブを描画（チーム内の外国人選手一覧 + 補強）"""
        width = self.screen.get_width()
        from models import Position
        
        # 外国人選手を抽出
        foreign_players = [(i, p) for i, p in enumerate(player_team.players) 
                          if getattr(p, 'is_foreign', False)]
        
        # 左側: チーム内外国人選手
        left_width = (width - 70) // 2
        left_card = Card(30, content_y, left_width, content_height - 60, f"外国人選手 {len(foreign_players)}/5")
        left_rect = left_card.draw(self.screen)
        
        # ソートボタン
        foreign_sort_mode = getattr(self, '_foreign_sort_mode', 'default')
        foreign_sort_asc = getattr(self, '_foreign_sort_asc', True)
        
        sort_btn_y = left_rect.y + 36
        overall_label = "総合↑" if foreign_sort_mode == 'overall' and foreign_sort_asc else "総合↓" if foreign_sort_mode == 'overall' else "総合順"
        sort_btn_overall = Button(left_rect.x + 8, sort_btn_y, 50, 20, overall_label, "primary" if foreign_sort_mode == 'overall' else "ghost", font=fonts.tiny)
        sort_btn_overall.draw(self.screen)
        buttons["foreign_sort_overall"] = sort_btn_overall
        
        age_label = "年齢↑" if foreign_sort_mode == 'age' and foreign_sort_asc else "年齢↓" if foreign_sort_mode == 'age' else "年齢順"
        sort_btn_age = Button(left_rect.x + 62, sort_btn_y, 50, 20, age_label, "primary" if foreign_sort_mode == 'age' else "ghost", font=fonts.tiny)
        sort_btn_age.draw(self.screen)
        buttons["foreign_sort_age"] = sort_btn_age
        
        # ソート適用
        if foreign_sort_mode == 'overall':
            foreign_players.sort(key=lambda x: x[1].overall_rating, reverse=not foreign_sort_asc)
        elif foreign_sort_mode == 'age':
            foreign_players.sort(key=lambda x: x[1].age, reverse=not foreign_sort_asc)
        
        # 選手リスト
        row_height = 36
        y = left_rect.y + 62
        max_visible = (left_rect.height - 100) // row_height
        
        # ヘッダー
        hdr_x = left_rect.x + 10
        for hdr, w in [("守備", 40), ("名前", 100), ("総合", 45), ("年齢", 40)]:
            hdr_surf = fonts.tiny.render(hdr, True, Colors.TEXT_MUTED)
            self.screen.blit(hdr_surf, (hdr_x, y))
            hdr_x += w
        y += 22
        
        for i in range(scroll_offset, min(scroll_offset + max_visible, len(foreign_players))):
            idx, player = foreign_players[i]
            row_rect = pygame.Rect(left_rect.x + 5, y, left_rect.width - 80, row_height - 2)
            is_hovered = row_rect.collidepoint(pygame.mouse.get_pos())
            
            bg_color = Colors.BG_HOVER if is_hovered else Colors.BG_INPUT
            pygame.draw.rect(self.screen, bg_color, row_rect, border_radius=3)
            
            x = left_rect.x + 10
            
            # ポジション
            pos_text = player.position.value[:2] if player.position else "?"
            pos_surf = fonts.tiny.render(pos_text, True, Colors.TEXT_PRIMARY)
            self.screen.blit(pos_surf, (x, y + 10))
            x += 40
            
            # 名前
            name_surf = fonts.small.render(f"#{player.uniform_number} {player.name[:5]}", True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_surf, (x, y + 8))
            x += 100
            
            # 総合力
            overall = player.overall_rating
            overall_color = Colors.GOLD if overall >= 700 else Colors.SUCCESS if overall >= 500 else Colors.TEXT_MUTED
            overall_surf = fonts.small.render(str(overall), True, overall_color)
            self.screen.blit(overall_surf, (x, y + 8))
            x += 45
            
            # 年齢
            age_surf = fonts.small.render(f"{player.age}歳", True, Colors.TEXT_MUTED)
            self.screen.blit(age_surf, (x, y + 8))
            
            # 詳細ボタン
            detail_btn = Button(row_rect.right + 5, y + 4, 30, 28, "詳", "outline", font=fonts.tiny)
            detail_btn.draw(self.screen)
            buttons[f"order_detail_{idx}"] = detail_btn
            
            # 解雇ボタン
            release_btn = Button(row_rect.right + 40, y + 4, 30, 28, "解", "danger", font=fonts.tiny)
            release_btn.draw(self.screen)
            buttons[f"release_foreign_{idx}"] = release_btn
            
            y += row_height
        
        # 右側: 外国人補強
        right_x = 40 + left_width
        right_card = Card(right_x, content_y, left_width, content_height - 60, "外国人選手補強")
        right_rect = right_card.draw(self.screen)
        
        desc_surf = fonts.small.render("外国人選手を獲得します。", True, Colors.TEXT_SECONDARY)
        self.screen.blit(desc_surf, (right_rect.x + 20, right_rect.y + 45))
        
        # 現在の外国人数
        foreign_count = len(foreign_players)
        status_text = f"枠: {foreign_count}/5 （残り{5 - foreign_count}枠）"
        status_color = Colors.SUCCESS if foreign_count < 5 else Colors.DANGER
        status_surf = fonts.body.render(status_text, True, status_color)
        self.screen.blit(status_surf, (right_rect.x + 20, right_rect.y + 75))
        
        # 外国人FA市場へのリンク
        can_sign = foreign_count < 5
        fa_btn = Button(right_rect.x + 20, right_rect.y + 120, 200, 45, 
                       "外国人FA市場を開く" if can_sign else "枠がありません", 
                       "primary" if can_sign else "ghost", font=fonts.body)
        fa_btn.draw(self.screen)
        if can_sign:
            buttons["open_foreign_fa"] = fa_btn
        
        info_text = "※ 外国人FA市場では世界各国の選手と契約できます"
        info_surf = fonts.tiny.render(info_text, True, Colors.TEXT_MUTED)
        self.screen.blit(info_surf, (right_rect.x + 20, right_rect.y + 180))
        
        # ホバープレビュー
        hovered_player = None
        mouse_pos = pygame.mouse.get_pos()
        check_y = left_rect.y + 84
        for i in range(scroll_offset, min(scroll_offset + max_visible, len(foreign_players))):
            idx, player = foreign_players[i]
            row_rect = pygame.Rect(left_rect.x + 5, check_y, left_rect.width - 80, row_height - 2)
            if row_rect.collidepoint(mouse_pos):
                hovered_player = player
                break
            check_y += row_height
        
        if hovered_player:
            self._draw_player_ability_preview(hovered_player)

    def _draw_foreign_tab(self, player_team, content_y, content_height, scroll_offset, buttons):
        """新外国人補強タブを描画"""
        width = self.screen.get_width()
        
        card = Card(30, content_y, width - 60, content_height, "外国人選手補強")
        card_rect = card.draw(self.screen)
        
        desc_surf = fonts.small.render("外国人選手を獲得します。外国人枠は5名までです。", True, Colors.TEXT_SECONDARY)
        self.screen.blit(desc_surf, (card_rect.x + 20, card_rect.y + 45))
        
        # 現在の外国人数を計算
        foreign_count = sum(1 for p in player_team.players if hasattr(p, 'is_foreign') and p.is_foreign)
        status_text = f"現在の外国人選手: {foreign_count}/5"
        status_color = Colors.SUCCESS if foreign_count < 5 else Colors.DANGER
        status_surf = fonts.body.render(status_text, True, status_color)
        self.screen.blit(status_surf, (card_rect.x + 20, card_rect.y + 70))
        
        # 外国人FA市場へのリンク
        fa_btn = Button(card_rect.x + 20, card_rect.y + 110, 200, 45, "外国人FA市場を開く", "primary", font=fonts.body)
        fa_btn.draw(self.screen)
        buttons["open_foreign_fa"] = fa_btn
        
        info_text = "※ 外国人FA市場では世界各国のフリーエージェント選手と契約できます"
        info_surf = fonts.tiny.render(info_text, True, Colors.TEXT_MUTED)
        self.screen.blit(info_surf, (card_rect.x + 20, card_rect.y + 170))

    def _draw_trade_tab(self, player_team, content_y, content_height, scroll_offset, buttons):
        """トレードタブを描画"""
        width = self.screen.get_width()
        
        card = Card(30, content_y, width - 60, content_height, "トレード")
        card_rect = card.draw(self.screen)
        
        desc_surf = fonts.small.render("他球団と選手をトレードします。", True, Colors.TEXT_SECONDARY)
        self.screen.blit(desc_surf, (card_rect.x + 20, card_rect.y + 45))
        
        # トレード市場へのリンク
        trade_btn = Button(card_rect.x + 20, card_rect.y + 90, 200, 45, "トレード市場を開く", "primary", font=fonts.body)
        trade_btn.draw(self.screen)
        buttons["open_trade_market"] = trade_btn
        
        info_text = "※ トレードでは他球団の選手と交換できます。金銭トレードも可能です。"
        info_surf = fonts.tiny.render(info_text, True, Colors.TEXT_MUTED)
        self.screen.blit(info_surf, (card_rect.x + 20, card_rect.y + 150))

    def _draw_farm_tab(self, player_team, content_y, content_height, scroll_offsets, buttons):
        """一軍/二軍/三軍入れ替えタブを描画
        
        Args:
            scroll_offsets: dict with 'first', 'second', 'third' keys
        """
        width = self.screen.get_width()
        from models import Position, TeamLevel
        from settings_manager import settings
        
        # 並び替え状態を取得（二軍と三軍で独立）
        second_sort_mode = getattr(self, '_second_sort_mode', 'default')
        second_sort_asc = getattr(self, '_second_sort_asc', True)
        third_sort_mode = getattr(self, '_third_sort_mode', 'default')
        third_sort_asc = getattr(self, '_third_sort_asc', True)
        
        # 三軍制の有効/無効を確認
        enable_third = getattr(settings.game_rules, 'enable_third_team', False)
        first_limit = getattr(settings.game_rules, 'first_team_limit', 31)
        
        # スクロールオフセットを取得（辞書または整数に対応）
        if isinstance(scroll_offsets, dict):
            scroll_first = scroll_offsets.get('first', 0)
            scroll_second = scroll_offsets.get('second', 0)
            scroll_third = scroll_offsets.get('third', 0)
        else:
            scroll_first = scroll_second = scroll_third = scroll_offsets
        
        # 選手を軍別に分類（team_levelを優先、設定がない場合は自動判定）
        first_team = []
        second_team = []
        third_team = []
        
        for i, p in enumerate(player_team.players):
            level = getattr(p, 'team_level', None)
            
            if level is not None:
                # team_levelが明示的に設定されている場合はそれを優先
                if level == TeamLevel.FIRST:
                    first_team.append((i, p))
                elif level == TeamLevel.SECOND:
                    second_team.append((i, p))
                elif level == TeamLevel.THIRD:
                    third_team.append((i, p))
            elif p.is_developmental:
                # 育成選手でteam_level未設定の場合は三軍
                third_team.append((i, p))
            else:
                # 自動判定: 一軍28人まで、それ以上は二軍（制限なし）
                if len(first_team) < first_limit:
                    first_team.append((i, p))
                else:
                    second_team.append((i, p))
        
        # 二軍の並び替え（昇順/降順対応）
        if second_sort_mode == 'overall':
            second_team.sort(key=lambda x: x[1].overall_rating, reverse=not second_sort_asc)
        elif second_sort_mode == 'age':
            second_team.sort(key=lambda x: x[1].age, reverse=not second_sort_asc)
        
        # 三軍の並び替え（昇順/降順対応）
        if third_sort_mode == 'overall':
            third_team.sort(key=lambda x: x[1].overall_rating, reverse=not third_sort_asc)
        elif third_sort_mode == 'age':
            third_team.sort(key=lambda x: x[1].age, reverse=not third_sort_asc)
        
        # 二軍と三軍のみ表示（一軍はオーダー画面で管理）
        if enable_third:
            col_width = (width - 60) // 2
        else:
            col_width = width - 60
        col_spacing = 10
        
        # 二軍カード
        second_card = Card(30, content_y, col_width, content_height - 60, f"二軍 {len(second_team)}人")
        second_rect = second_card.draw(self.screen)
        
        # 二軍用並び替えボタン
        sort_btn_y = second_rect.y + 36
        overall_label = "総合↑" if second_sort_mode == 'overall' and second_sort_asc else "総合↓" if second_sort_mode == 'overall' else "総合順"
        sort_btn_overall = Button(second_rect.x + 8, sort_btn_y, 50, 20, overall_label, "primary" if second_sort_mode == 'overall' else "ghost", font=fonts.tiny)
        sort_btn_overall.draw(self.screen)
        buttons["second_sort_overall"] = sort_btn_overall
        
        age_label = "年齢↑" if second_sort_mode == 'age' and second_sort_asc else "年齢↓" if second_sort_mode == 'age' else "年齢順"
        sort_btn_age = Button(second_rect.x + 62, sort_btn_y, 50, 20, age_label, "primary" if second_sort_mode == 'age' else "ghost", font=fonts.tiny)
        sort_btn_age.draw(self.screen)
        buttons["second_sort_age"] = sort_btn_age
        
        self._draw_farm_player_list(second_rect, second_team, scroll_second, buttons, "second", TeamLevel.SECOND, show_promote_first=False, header_offset=30)
        
        # 三軍カード（有効な場合のみ、人数制限なし）
        if enable_third:
            third_x = 30 + col_width + col_spacing
            third_card = Card(third_x, content_y, col_width, content_height - 60, f"三軍 {len(third_team)}人")
            third_rect = third_card.draw(self.screen)
            
            # 三軍用並び替えボタン（独立）
            sort_btn_y3 = third_rect.y + 36
            overall_label3 = "総合↑" if third_sort_mode == 'overall' and third_sort_asc else "総合↓" if third_sort_mode == 'overall' else "総合順"
            sort_btn_overall3 = Button(third_rect.x + 8, sort_btn_y3, 50, 20, overall_label3, "primary" if third_sort_mode == 'overall' else "ghost", font=fonts.tiny)
            sort_btn_overall3.draw(self.screen)
            buttons["third_sort_overall"] = sort_btn_overall3
            
            age_label3 = "年齢↑" if third_sort_mode == 'age' and third_sort_asc else "年齢↓" if third_sort_mode == 'age' else "年齢順"
            sort_btn_age3 = Button(third_rect.x + 62, sort_btn_y3, 50, 20, age_label3, "primary" if third_sort_mode == 'age' else "ghost", font=fonts.tiny)
            sort_btn_age3.draw(self.screen)
            buttons["third_sort_age"] = sort_btn_age3
            
            self._draw_farm_player_list(third_rect, third_team, scroll_third, buttons, "third", TeamLevel.THIRD, show_promote_first=False, header_offset=30)
        
        # ホバー中の選手を取得して能力プレビュー表示
        hovered_player = self._get_hovered_player_from_lists(
            [(second_team, second_rect, scroll_second)] + 
            ([(third_team, third_rect, scroll_third)] if enable_third else []),
            0  # 個別スクロールを使うので0
        )
        if hovered_player:
            self._draw_player_ability_preview(hovered_player)
        
        # 操作説明
        help_y = content_y + content_height - 45
        help_text = "二軍⇔三軍の入れ替え | 一軍への昇格はオーダー画面で行ってください"
        help_surf = fonts.small.render(help_text, True, Colors.TEXT_MUTED)
        self.screen.blit(help_surf, (30, help_y))
    
    def _get_hovered_player_from_lists(self, team_rect_pairs, scroll_offset):
        """複数のチームリストからホバー中の選手を取得
        
        Args:
            team_rect_pairs: List of (players, card_rect) or (players, card_rect, individual_scroll)
        """
        from models import Position
        row_height = 32
        mouse_pos = pygame.mouse.get_pos()
        
        for item in team_rect_pairs:
            if len(item) == 3:
                players, card_rect, individual_scroll = item
            else:
                players, card_rect = item
                individual_scroll = scroll_offset
            
            y = card_rect.y + 65  # ヘッダー分オフセット
            max_visible = (card_rect.height - 60) // row_height
            
            for i in range(individual_scroll, min(individual_scroll + max_visible, len(players))):
                idx, player = players[i]
                row_rect = pygame.Rect(card_rect.x + 5, y, card_rect.width - 55, row_height - 2)
                if row_rect.collidepoint(mouse_pos):
                    return player
                y += row_height
        return None
    
    def _draw_player_ability_preview(self, player):
        """選手能力プレビューをツールチップ形式で表示"""
        from models import Position
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        
        # プレビューボックスのサイズと位置
        preview_w = 280
        preview_h = 180
        preview_x = width - preview_w - 20
        preview_y = height - preview_h - 80
        
        # 背景
        preview_rect = pygame.Rect(preview_x, preview_y, preview_w, preview_h)
        pygame.draw.rect(self.screen, (*Colors.BG_CARD[:3], 240), preview_rect, border_radius=12)
        pygame.draw.rect(self.screen, Colors.PRIMARY, preview_rect, 2, border_radius=12)
        
        # ヘッダー（選手名）
        y = preview_y + 12
        name_surf = fonts.body.render(f"#{player.uniform_number} {player.name}", True, Colors.TEXT_PRIMARY)
        self.screen.blit(name_surf, (preview_x + 15, y))
        y += 28
        
        # ポジション・年齢
        pos_text = f"{player.position.value} / {player.age}歳"
        pos_surf = fonts.small.render(pos_text, True, Colors.TEXT_SECONDARY)
        self.screen.blit(pos_surf, (preview_x + 15, y))
        y += 25
        
        # 区切り線
        pygame.draw.line(self.screen, Colors.BORDER, (preview_x + 10, y), (preview_x + preview_w - 10, y), 1)
        y += 10
        
        # 能力値（100スケールに変換）
        if player.position == Position.PITCHER:
            stats = [
                ("球速", player.stats.to_100_scale(player.stats.speed)),
                ("制球", player.stats.to_100_scale(player.stats.control)),
                ("変化", player.stats.to_100_scale(player.stats.breaking)),
                ("スタミナ", player.stats.to_100_scale(player.stats.stamina)),
            ]
        else:
            stats = [
                ("ミート", player.stats.to_100_scale(player.stats.contact)),
                ("パワー", player.stats.to_100_scale(player.stats.power)),
                ("走力", player.stats.to_100_scale(player.stats.run)),
                ("守備", player.stats.to_100_scale(player.stats.fielding)),
            ]
        
        for stat_name, stat_value in stats:
            # ラベル
            label_surf = fonts.small.render(stat_name, True, Colors.TEXT_SECONDARY)
            self.screen.blit(label_surf, (preview_x + 15, y))
            
            # バー
            bar_x = preview_x + 85
            bar_w = 120
            bar_h = 12
            bar_rect = pygame.Rect(bar_x, y + 3, bar_w, bar_h)
            pygame.draw.rect(self.screen, Colors.BG_INPUT, bar_rect, border_radius=3)
            
            fill_w = int(bar_w * stat_value / 100)
            fill_color = self._get_stat_color(stat_value)
            fill_rect = pygame.Rect(bar_x, y + 3, fill_w, bar_h)
            pygame.draw.rect(self.screen, fill_color, fill_rect, border_radius=3)
            
            # ランク表示（数値ではなくG~S）
            stat_rank = player.stats.get_rank(stat_value)
            stat_rank_color = player.stats.get_rank_color(stat_value)
            rank_surf = fonts.body.render(stat_rank, True, stat_rank_color)
            self.screen.blit(rank_surf, (preview_x + preview_w - 35, y - 2))
            
            y += 22

    def _draw_farm_player_list(self, card_rect, players, scroll_offset, buttons, prefix, team_level, show_promote_first=True, header_offset=0):
        """軍別選手リストを描画"""
        from models import Position, TeamLevel
        
        row_height = 32
        y = card_rect.y + 45 + header_offset
        max_visible = (card_rect.height - 60 - header_offset) // row_height
        
        # ボタン列の幅を調整
        if team_level == TeamLevel.SECOND and show_promote_first:
            row_width = card_rect.width - 75  # 横2列ボタン用
        elif team_level == TeamLevel.SECOND:
            row_width = card_rect.width - 50  # 降格ボタンのみ
        else:
            row_width = card_rect.width - 50  # 1ボタン用
        
        # ヘッダー
        hdr_x = card_rect.x + 10
        for hdr, w in [("守備", 35), ("選手名", 85), ("総合", 40)]:
            hdr_surf = fonts.tiny.render(hdr, True, Colors.TEXT_MUTED)
            self.screen.blit(hdr_surf, (hdr_x, y))
            hdr_x += w
        y += 20
        
        for i in range(scroll_offset, min(scroll_offset + max_visible, len(players))):
            idx, player = players[i]
            row_rect = pygame.Rect(card_rect.x + 5, y, row_width, row_height - 2)
            
            is_hovered = row_rect.collidepoint(pygame.mouse.get_pos())
            bg_color = Colors.BG_HOVER if is_hovered else Colors.BG_INPUT
            pygame.draw.rect(self.screen, bg_color, row_rect, border_radius=4)
            
            # ホバーエフェクト
            if is_hovered:
                draw_selection_effect(self.screen, row_rect, Colors.PRIMARY, 0.4)
            
            x = card_rect.x + 10
            
            # 守備
            pos_text = player.position.value[:2] if player.position.value != "外野手" else "外"
            pos_surf = fonts.tiny.render(pos_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(pos_surf, (x, y + 8))
            x += 35
            
            # 選手名
            name_color = Colors.WARNING if player.is_developmental else Colors.TEXT_PRIMARY
            name_surf = fonts.tiny.render(player.name[:5], True, name_color)
            self.screen.blit(name_surf, (x, y + 8))
            x += 80
            
            # 総合力（1-999）
            overall = player.overall_rating
            overall_color = Colors.GOLD if overall >= 700 else Colors.SUCCESS if overall >= 500 else Colors.TEXT_MUTED
            overall_surf = fonts.tiny.render(f"★{overall}", True, overall_color)
            self.screen.blit(overall_surf, (x, y + 8))
            
            # 昇格/降格ボタン
            btn_x = row_rect.right + 3
            btn_w = 22
            btn_h = 24
            if team_level == TeamLevel.FIRST:
                # 一軍 → 二軍への降格ボタン
                down_btn = Button(btn_x, y + 3, btn_w, btn_h, "↓", "warning", font=fonts.small)
                down_btn.draw(self.screen)
                buttons[f"demote_{idx}"] = down_btn
            elif team_level == TeamLevel.SECOND:
                if show_promote_first:
                    # 二軍 → 一軍への昇格ボタン（横配置）
                    up_btn = Button(btn_x, y + 3, btn_w, btn_h, "↑", "success", font=fonts.small)
                    up_btn.draw(self.screen)
                    buttons[f"promote_farm_{idx}"] = up_btn
                    btn_x += btn_w + 2
                # 二軍 → 三軍への降格ボタン
                down_btn = Button(btn_x, y + 3, btn_w, btn_h, "↓", "warning", font=fonts.small)
                down_btn.draw(self.screen)
                buttons[f"demote_{idx}"] = down_btn
            elif team_level == TeamLevel.THIRD:
                # 三軍 → 二軍への昇格ボタン（育成選手も含む）
                up_btn = Button(btn_x, y + 3, btn_w, btn_h, "↑", "success", font=fonts.small)
                up_btn.draw(self.screen)
                buttons[f"promote_third_{idx}"] = up_btn
            
            y += row_height
        
        # スクロールバー
        if len(players) > max_visible:
            self._draw_scrollbar(card_rect, scroll_offset, len(players), max_visible)

    def _draw_players_tab(self, player_team, content_y, content_height, scroll_offset, selected_player_idx, buttons):
        """選手一覧タブを描画"""
        width = self.screen.get_width()
        from models import Position
        
        # 投手/野手のフィルタボタン
        filter_y = content_y
        pitcher_btn = Button(30, filter_y, 100, 32, "投手", "outline", font=fonts.small)
        pitcher_btn.draw(self.screen)
        buttons["filter_pitcher"] = pitcher_btn
        
        batter_btn = Button(140, filter_y, 100, 32, "野手", "outline", font=fonts.small)
        batter_btn.draw(self.screen)
        buttons["filter_batter"] = batter_btn
        
        all_btn = Button(250, filter_y, 100, 32, "全員", "primary", font=fonts.small)
        all_btn.draw(self.screen)
        buttons["filter_all"] = all_btn
        
        # 並び替えボタン
        players_sort_mode = getattr(self, '_players_sort_mode', 'default')
        players_sort_asc = getattr(self, '_players_sort_asc', True)
        overall_label = "総合力↑" if players_sort_mode == 'overall' and players_sort_asc else "総合力↓" if players_sort_mode == 'overall' else "総合力順"
        sort_overall_btn = Button(380, filter_y, 80, 32, overall_label, "primary" if players_sort_mode == 'overall' else "ghost", font=fonts.small)
        sort_overall_btn.draw(self.screen)
        buttons["players_sort_overall"] = sort_overall_btn
        
        age_label = "年齢↑" if players_sort_mode == 'age' and players_sort_asc else "年齢↓" if players_sort_mode == 'age' else "年齢順"
        sort_age_btn = Button(465, filter_y, 80, 32, age_label, "primary" if players_sort_mode == 'age' else "ghost", font=fonts.small)
        sort_age_btn.draw(self.screen)
        buttons["players_sort_age"] = sort_age_btn
        
        # 選手リスト
        list_y = filter_y + 45
        list_height = content_height - 55
        
        card = Card(30, list_y, width - 60, list_height, "選手一覧")
        card_rect = card.draw(self.screen)
        
        # 全選手（支配下・育成含む）
        all_players = [(i, p) for i, p in enumerate(player_team.players)]
        
        # 並び替え（昇順/降順対応）
        if players_sort_mode == 'overall':
            all_players.sort(key=lambda x: x[1].overall_rating, reverse=not players_sort_asc)
        elif players_sort_mode == 'age':
            all_players.sort(key=lambda x: x[1].age, reverse=not players_sort_asc)
        
        row_height = 34
        y = card_rect.y + 45
        max_visible = (card_rect.height - 60) // row_height
        
        # ヘッダー
        headers = ["#", "名前", "ポジ", "年齢", "契約", "能力"]
        header_x = [15, 50, 200, 280, 330, 400]
        for h, hx in zip(headers, header_x):
            h_surf = fonts.tiny.render(h, True, Colors.TEXT_MUTED)
            self.screen.blit(h_surf, (card_rect.x + hx, card_rect.y + 45))
        
        y += 25
        
        for i in range(scroll_offset, min(scroll_offset + max_visible, len(all_players))):
            idx, player = all_players[i]
            row_rect = pygame.Rect(card_rect.x + 10, y, card_rect.width - 20, row_height - 4)
            
            is_selected = idx == selected_player_idx
            is_hovered = row_rect.collidepoint(pygame.mouse.get_pos())
            
            if is_selected:
                bg_color = lerp_color(Colors.BG_CARD, Colors.PRIMARY, 0.3)
                # 選択エフェクト
                draw_selection_effect(self.screen, row_rect, Colors.PRIMARY, 1.0)
            elif is_hovered:
                bg_color = Colors.BG_HOVER
                # ホバーエフェクト（弱め）
                draw_selection_effect(self.screen, row_rect, Colors.PRIMARY, 0.3)
            else:
                bg_color = Colors.BG_INPUT if i % 2 == 0 else Colors.BG_CARD
            
            pygame.draw.rect(self.screen, bg_color, row_rect, border_radius=4)
            
            # 背番号
            num_surf = fonts.small.render(str(player.uniform_number), True, Colors.TEXT_SECONDARY)
            self.screen.blit(num_surf, (card_rect.x + 20, y + 7))
            
            # 名前
            name_color = Colors.WARNING if player.is_developmental else Colors.TEXT_PRIMARY
            name_surf = fonts.small.render(player.name[:8], True, name_color)
            self.screen.blit(name_surf, (card_rect.x + 55, y + 7))
            
            # ポジション
            pos_surf = fonts.small.render(player.position.value[:3], True, Colors.TEXT_SECONDARY)
            self.screen.blit(pos_surf, (card_rect.x + 205, y + 7))
            
            # 年齢
            age_surf = fonts.small.render(str(player.age), True, Colors.TEXT_SECONDARY)
            self.screen.blit(age_surf, (card_rect.x + 285, y + 7))
            
            # 契約
            contract_text = "育成" if player.is_developmental else "支配下"
            contract_surf = fonts.tiny.render(contract_text, True, Colors.WARNING if player.is_developmental else Colors.SUCCESS)
            self.screen.blit(contract_surf, (card_rect.x + 335, y + 9))
            
            # 総合能力（ランクのみ表示）
            overall = player.stats.overall_pitching() if player.position == Position.PITCHER else player.stats.overall_batting()
            rank = player.stats.get_rank(overall)
            rank_color = player.stats.get_rank_color(overall)
            overall_surf = fonts.small.render(f"{rank}", True, rank_color)
            self.screen.blit(overall_surf, (card_rect.x + 405, y + 7))
            
            # ボタン群（右寄せ）
            btn_x = row_rect.right - 55
            
            # 育成選手なら支配下昇格ボタンを表示
            if player.is_developmental:
                promote_btn = Button(btn_x - 50, y + 3, 45, 26, "昇格", "success", font=fonts.tiny)
                promote_btn.draw(self.screen)
                buttons[f"promote_roster_{idx}"] = promote_btn
            
            # 自由契約ボタン
            release_btn = Button(btn_x - 100, y + 3, 45, 26, "解雇", "warning", font=fonts.tiny)
            release_btn.draw(self.screen)
            buttons[f"release_player_{idx}"] = release_btn
            
            # 詳細ボタン
            detail_btn = Button(btn_x, y + 3, 50, 26, "詳細", "outline", font=fonts.tiny)
            detail_btn.draw(self.screen)
            buttons[f"player_detail_{idx}"] = detail_btn
            
            y += row_height
        
        if len(all_players) > max_visible:
            self._draw_scrollbar(card_rect, scroll_offset, len(all_players), max_visible)
        
        # ホバー中の選手の能力プレビュー
        hovered_player = None
        mouse_pos = pygame.mouse.get_pos()
        check_y = card_rect.y + 70
        for i in range(scroll_offset, min(scroll_offset + max_visible, len(all_players))):
            idx, player = all_players[i]
            row_rect = pygame.Rect(card_rect.x + 10, check_y, card_rect.width - 20, row_height - 4)
            if row_rect.collidepoint(mouse_pos):
                hovered_player = player
                break
            check_y += row_height
        
        if hovered_player:
            self._draw_player_ability_preview(hovered_player)

    # ========================================
    # 選手詳細画面（パワプロ風）
    # ========================================
    def draw_player_detail_screen(self, player, scroll_offset: int = 0, team_color=None, 
                                   stats_level: str = "first") -> Dict[str, Button]:
        """選手詳細画面を描画（パワプロ風能力表示・強化版）
        
        Args:
            stats_level: 成績表示の軍 ('first', 'second', 'third')
        """
        from models import Position
        
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        center_x = width // 2
        
        if team_color is None:
            team_color = Colors.PRIMARY
        
        # ヘッダー（選手情報をコンパクトに）
        pos_text = player.position.value
        if player.pitch_type:
            pos_text += f" ({player.pitch_type.value})"
        
        # カスタムヘッダー（より詳細な情報付き）
        header_h = 100
        pygame.draw.rect(self.screen, Colors.BG_CARD, (0, 0, width, header_h))
        
        # 背番号を大きく表示
        number_surf = fonts.h1.render(f"#{player.uniform_number}", True, team_color)
        self.screen.blit(number_surf, (30, 20))
        
        # 名前
        name_surf = fonts.h2.render(player.name, True, Colors.TEXT_PRIMARY)
        self.screen.blit(name_surf, (120, 25))
        
        # ポジション・年齢・契約タイプを横に
        contract_text = "育成" if player.is_developmental else "支配下"
        info_line = f"{pos_text}  |  {player.age}歳  |  {contract_text}  |  プロ{player.years_pro}年目"
        info_surf = fonts.body.render(info_line, True, Colors.TEXT_SECONDARY)
        self.screen.blit(info_surf, (120, 60))
        
        # 総合力を表示（右上大きく）
        overall = player.overall_rating
        overall_color = Colors.GOLD if overall >= 700 else Colors.SUCCESS if overall >= 500 else Colors.WARNING if overall >= 300 else Colors.TEXT_MUTED
        
        overall_label_surf = fonts.small.render("総合力", True, Colors.TEXT_MUTED)
        self.screen.blit(overall_label_surf, (width - 130, 15))
        
        overall_value_surf = fonts.h1.render(str(overall), True, overall_color)
        self.screen.blit(overall_value_surf, (width - 130, 35))
        
        # 年俸表示（その下）
        if player.salary >= 100000000:
            salary_text = f"{player.salary // 100000000}億{(player.salary % 100000000) // 10000000}千万"
        else:
            salary_text = f"{player.salary // 10000}万円"
        salary_surf = fonts.tiny.render(salary_text, True, Colors.WARNING)
        self.screen.blit(salary_surf, (width - salary_surf.get_width() - 30, 75))
        
        buttons = {}
        stats = player.stats
        
        # ===== 能力値表示エリア =====
        content_y = header_h + 10
        
        if player.position == Position.PITCHER:
            # 投手能力カード（左側）
            ability_card = Card(20, content_y, 400, 260, "PITCHER")
            ability_rect = ability_card.draw(self.screen)
            
            # 基本能力（2x2グリッド）- 球速はkm/h表示
            speed_kmh = stats.speed_to_kmh()
            abilities = [
                (f"球速 ({speed_kmh}km)", stats.speed, "", ""),
                ("コントロール", stats.control, "", ""),
                ("スタミナ", stats.stamina, "", ""),
                ("変化球", stats.breaking, "", ""),
            ]
            
            y = ability_rect.y + 45
            for i, (name, value, icon, extra) in enumerate(abilities):
                col = i % 2
                x = ability_rect.x + 20 + col * 185
                if i == 2:
                    y += 55
                
                # 名前
                name_surf = fonts.small.render(f"{icon} {name}", True, Colors.TEXT_SECONDARY)
                self.screen.blit(name_surf, (x, y))
                
                # ランク（大きく）
                rank = stats.get_rank(value)
                rank_color = stats.get_rank_color(value)
                rank_surf = fonts.h2.render(rank, True, rank_color)
                self.screen.blit(rank_surf, (x, y + 18))
                
                # 補足情報のみ（数値なし）
                if extra:
                    val_surf = fonts.tiny.render(extra, True, Colors.TEXT_MUTED)
                    self.screen.blit(val_surf, (x + 35, y + 28))
                
                # バー
                bar_x = x + 80
                bar_y = y + 30
                pygame.draw.rect(self.screen, Colors.BG_INPUT, (bar_x, bar_y, 80, 6), border_radius=3)
                fill_w = int(80 * value / 100)
                pygame.draw.rect(self.screen, rank_color, (bar_x, bar_y, fill_w, 6), border_radius=3)
            
            # 球種カード（右側）
            pitch_card = Card(430, content_y, width - 450, 260, "持ち球")
            pitch_rect = pitch_card.draw(self.screen)
            
            y = pitch_rect.y + 45
            if hasattr(stats, 'pitch_repertoire') and stats.pitch_repertoire:
                for pitch_name, break_value in list(stats.pitch_repertoire.items())[:8]:
                    # 球種名
                    pitch_surf = fonts.body.render(pitch_name, True, Colors.TEXT_PRIMARY)
                    self.screen.blit(pitch_surf, (pitch_rect.x + 20, y))
                    # 変化量バー
                    bar_x = pitch_rect.x + 150
                    pygame.draw.rect(self.screen, Colors.BG_INPUT, (bar_x, y + 5, 80, 8), border_radius=4)
                    fill_w = int(80 * min(break_value / 7, 1.0))
                    pygame.draw.rect(self.screen, Colors.INFO, (bar_x, y + 5, fill_w, 8), border_radius=4)
                    # 変化量
                    val_surf = fonts.small.render(f"{break_value}", True, Colors.TEXT_SECONDARY)
                    self.screen.blit(val_surf, (bar_x + 85, y + 2))
                    y += 26
            elif stats.breaking_balls:
                for pitch_name in stats.breaking_balls[:8]:
                    pitch_surf = fonts.body.render(f"• {pitch_name}", True, Colors.TEXT_PRIMARY)
                    self.screen.blit(pitch_surf, (pitch_rect.x + 20, y))
                    y += 26
            
        else:
            # 野手能力カード（左側）
            ability_card = Card(20, content_y, 400, 260, "🏏 野手能力")
            ability_rect = ability_card.draw(self.screen)
            
            # 弾道表示（上部に大きく）
            trajectory = getattr(stats, 'trajectory', 2)
            traj_names = {1: "グラウンダー", 2: "ライナー", 3: "普通", 4: "パワー"}
            
            traj_label = fonts.small.render("弾道", True, Colors.TEXT_SECONDARY)
            self.screen.blit(traj_label, (ability_rect.x + 20, ability_rect.y + 42))
            
            # 弾道アイコン（丸で表示）
            for i in range(4):
                color = Colors.WARNING if i < trajectory else Colors.BG_INPUT
                pygame.draw.circle(self.screen, color, (ability_rect.x + 80 + i * 25, ability_rect.y + 52), 8)
            traj_name_surf = fonts.small.render(traj_names.get(trajectory, '普通'), True, Colors.TEXT_MUTED)
            self.screen.blit(traj_name_surf, (ability_rect.x + 190, ability_rect.y + 45))
            
            # 基本能力（3列×2行）- 100スケールに変換
            abilities = [
                ("ミート", stats.to_100_scale(stats.contact), ""),
                ("パワー", stats.to_100_scale(stats.power), ""),
                ("走力", stats.to_100_scale(stats.run), ""),
                ("肩力", stats.to_100_scale(stats.arm), ""),
                ("守備", stats.to_100_scale(stats.fielding), ""),
                ("捕球", stats.to_100_scale(getattr(stats, 'catching', stats.fielding)), ""),
            ]
            
            y = ability_rect.y + 75
            for i, (name, value, icon) in enumerate(abilities):
                col = i % 3
                x = ability_rect.x + 15 + col * 125
                if i == 3:
                    y += 55
                
                # 名前
                name_surf = fonts.tiny.render(f"{icon}{name}", True, Colors.TEXT_SECONDARY)
                self.screen.blit(name_surf, (x, y))
                
                # ランク（大きく）
                rank = stats.get_rank(value)
                rank_color = stats.get_rank_color(value)
                rank_surf = fonts.h3.render(rank, True, rank_color)
                self.screen.blit(rank_surf, (x, y + 15))
                
                # バー
                bar_x = x + 30
                bar_y = y + 25
                pygame.draw.rect(self.screen, Colors.BG_INPUT, (bar_x, bar_y, 80, 5), border_radius=2)
                fill_w = int(80 * value / 100)
                pygame.draw.rect(self.screen, rank_color, (bar_x, bar_y, fill_w, 5), border_radius=2)
            
            # 守備適性カード（右側）
            pos_card = Card(430, content_y, width - 450, 260, "POSITION")
            pos_rect = pos_card.draw(self.screen)
            
            # メインポジション
            main_pos_surf = fonts.body.render(f"メイン: {player.position.value}", True, Colors.PRIMARY)
            self.screen.blit(main_pos_surf, (pos_rect.x + 20, pos_rect.y + 45))
            
            # サブポジション
            y = pos_rect.y + 75
            sub_label = fonts.small.render("サブポジション:", True, Colors.TEXT_SECONDARY)
            self.screen.blit(sub_label, (pos_rect.x + 20, y))
            y += 25
            
            if hasattr(player, 'sub_positions') and player.sub_positions:
                for sub_pos in player.sub_positions[:4]:
                    pos_surf = fonts.body.render(f"• {sub_pos.value}", True, Colors.TEXT_PRIMARY)
                    self.screen.blit(pos_surf, (pos_rect.x + 30, y))
                    y += 24
            else:
                none_surf = fonts.small.render("なし", True, Colors.TEXT_MUTED)
                self.screen.blit(none_surf, (pos_rect.x + 30, y))
        
        # 特殊能力カード（下部左）
        special_card = Card(20, content_y + 270, 400, 155, "SKILLS")
        special_rect = special_card.draw(self.screen)
        
        if player.position == Position.PITCHER:
            special_abilities = [
                ("対ピンチ", stats.clutch, ""),
                ("対左打者", getattr(stats, 'vs_left', 50), ""),
                ("メンタル", stats.mental, ""),
                ("安定感", stats.consistency, ""),
                ("クイック", getattr(stats, 'quick', 50), ""),
                ("牽制", getattr(stats, 'pickoff', 50), ""),
            ]
        else:
            special_abilities = [
                ("チャンス", stats.clutch, ""),
                ("対左投手", getattr(stats, 'vs_left', 50), ""),
                ("メンタル", stats.mental, ""),
                ("安定感", stats.consistency, ""),
                ("盗塁", getattr(stats, 'stealing', stats.run), ""),
                ("送球", getattr(stats, 'throwing', stats.arm), ""),
            ]
        
        y = special_rect.y + 42
        for i, (name, value, icon) in enumerate(special_abilities):
            col = i % 3
            x = special_rect.x + 15 + col * 125
            if i == 3:
                y += 38
            
            rank = stats.get_rank(value)
            rank_color = stats.get_rank_color(value)
            
            name_surf = fonts.tiny.render(f"{icon}{name}", True, Colors.TEXT_SECONDARY)
            rank_surf = fonts.body.render(rank, True, rank_color)
            
            self.screen.blit(name_surf, (x, y))
            self.screen.blit(rank_surf, (x, y + 16))
            
            # ミニバー
            bar_x = x + 30
            pygame.draw.rect(self.screen, Colors.BG_INPUT, (bar_x, y + 22, 50, 4), border_radius=2)
            fill = int(50 * min(value / 100, 1.0))
            pygame.draw.rect(self.screen, rank_color, (bar_x, y + 22, fill, 4), border_radius=2)
        
        # 成績カード（下部右）- 軍別成績切り替え機能付き
        record = player.record
        
        # 軍別成績の選択に応じて表示する成績を決定
        stats_level_display = {"first": "一軍", "second": "二軍", "third": "三軍"}.get(stats_level, "一軍")
        record_card = Card(430, content_y + 270, width - 450, 185, "成績")
        record_rect = record_card.draw(self.screen)
        
        # 軍切り替えボタン（タイトル右横に配置）
        btn_y = record_rect.y + 8
        btn_x = record_rect.x + 70
        for level_id, level_name in [("first", "一軍"), ("second", "二軍"), ("third", "三軍")]:
            style = "primary" if stats_level == level_id else "outline"
            level_btn = Button(btn_x, btn_y, 50, 22, level_name, style, font=fonts.tiny)
            level_btn.draw(self.screen)
            buttons[f"stats_level_{level_id}"] = level_btn
            btn_x += 55
        
        if player.position == Position.PITCHER:
            stats_items = [
                ("登板", f"{record.games_pitched}", Colors.TEXT_PRIMARY),
                ("勝", f"{record.wins}", Colors.SUCCESS),
                ("敗", f"{record.losses}", Colors.DANGER),
                ("S", f"{record.saves}", Colors.INFO),
                ("防御率", f"{record.era:.2f}", Colors.WARNING if record.era < 3.0 else Colors.TEXT_PRIMARY),
                ("K", f"{record.strikeouts_pitched}", Colors.PRIMARY),
            ]
        else:
            avg = record.batting_average
            avg_color = Colors.WARNING if avg >= 0.300 else Colors.SUCCESS if avg >= 0.280 else Colors.TEXT_PRIMARY
            stats_items = [
                ("打率", f".{int(avg * 1000):03d}" if avg > 0 else ".000", avg_color),
                ("安打", f"{record.hits}", Colors.TEXT_PRIMARY),
                ("HR", f"{record.home_runs}", Colors.DANGER if record.home_runs >= 20 else Colors.TEXT_PRIMARY),
                ("打点", f"{record.rbis}", Colors.SUCCESS),
                ("盗塁", f"{record.stolen_bases}", Colors.INFO),
                ("OPS", f"{record.ops:.3f}" if hasattr(record, 'ops') else "-", Colors.WARNING),
            ]
        
        x = record_rect.x + 15
        y = record_rect.y + 65  # 軍切り替えボタン分だけ下に移動
        item_width = (record_rect.width - 30) // len(stats_items)
        for label, value, color in stats_items:
            label_surf = fonts.tiny.render(label, True, Colors.TEXT_SECONDARY)
            value_surf = fonts.h3.render(value, True, color)
            self.screen.blit(label_surf, (x, y))
            self.screen.blit(value_surf, (x, y + 18))
            x += item_width
        
        # 戻るボタン
        buttons["back"] = Button(
            50, height - 70, 150, 50,
            "← 戻る", "ghost", font=fonts.body
        )
        buttons["back"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons
    
    # ========================================
    # 育成ドラフト画面
    # ========================================
    def draw_developmental_draft_screen(self, prospects: List, selected_idx: int = -1,
                                        draft_round: int = 1, draft_messages: List[str] = None) -> Dict[str, Button]:
        """育成ドラフト画面を描画"""
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        center_x = width // 2
        
        # ヘッダー（育成は別色）
        round_text = f"育成第{draft_round}巡目"
        header_h = draw_header(self.screen, f"DEV DRAFT - {round_text}", "将来性のある選手を発掘", Colors.SUCCESS)
        
        buttons = {}
        
        # 左側: 候補者リスト
        card_width = width - 320 if draft_messages else width - 60
        card = Card(30, header_h + 15, card_width - 30, height - header_h - 120)
        card_rect = card.draw(self.screen)
        
        # ヘッダー行
        headers = [("名前", 140), ("ポジション", 90), ("年齢", 50), ("ポテンシャル", 90), ("総合", 70)]
        x = card_rect.x + 15
        y = card_rect.y + 18
        
        for header_text, w in headers:
            h_surf = fonts.tiny.render(header_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(h_surf, (x, y))
            x += w
        
        y += 22
        pygame.draw.line(self.screen, Colors.BORDER, (card_rect.x + 10, y), (card_rect.right - 10, y), 1)
        y += 8
        
        # 候補者一覧
        visible_count = min(12, len(prospects))
        
        for i in range(visible_count):
            prospect = prospects[i]
            row_rect = pygame.Rect(card_rect.x + 8, y - 2, card_rect.width - 16, 32)
            
            # 選択中
            if i == selected_idx:
                pygame.draw.rect(self.screen, (*Colors.SUCCESS[:3], 50), row_rect, border_radius=4)
                pygame.draw.rect(self.screen, Colors.SUCCESS, row_rect, 2, border_radius=4)
            elif i % 2 == 0:
                pygame.draw.rect(self.screen, Colors.BG_INPUT, row_rect, border_radius=3)
            
            x = card_rect.x + 15
            
            # 名前
            name_surf = fonts.small.render(prospect.name[:8], True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_surf, (x, y + 4))
            x += 140
            
            # ポジション
            pos_text = prospect.position.value[:2]
            if prospect.pitch_type:
                pos_text += f"({prospect.pitch_type.value[0]})"
            pos_surf = fonts.tiny.render(pos_text, True, Colors.TEXT_SECONDARY)
            self.screen.blit(pos_surf, (x, y + 6))
            x += 90
            
            # 年齢
            age_surf = fonts.small.render(f"{prospect.age}", True, Colors.TEXT_PRIMARY)
            self.screen.blit(age_surf, (x, y + 4))
            x += 50
            
            # ポテンシャル（星表示、育成は最大3つ）
            pot_stars = min(prospect.potential // 3, 3)
            pot_color = Colors.SUCCESS if pot_stars >= 2 else Colors.TEXT_SECONDARY
            pot_surf = fonts.small.render("★" * pot_stars, True, pot_color)
            self.screen.blit(pot_surf, (x, y + 4))
            x += 90
            
            # 総合力
            overall = prospect.stats.overall_batting() if prospect.position.value != "投手" else prospect.stats.overall_pitching()
            overall_surf = fonts.small.render(f"{overall:.0f}", True, Colors.TEXT_PRIMARY)
            self.screen.blit(overall_surf, (x, y + 4))
            
            y += 35
        
        # 右側: 指名履歴
        if draft_messages:
            log_card = Card(width - 280, header_h + 15, 250, height - header_h - 120, "PICK LOG")
            log_rect = log_card.draw(self.screen)
            
            log_y = log_rect.y + 42
            recent_msgs = draft_messages[-8:] if len(draft_messages) > 8 else draft_messages
            for msg in recent_msgs:
                msg_surf = fonts.tiny.render(msg[:28], True, Colors.TEXT_SECONDARY)
                self.screen.blit(msg_surf, (log_rect.x + 8, log_y))
                log_y += 20
        
        # ボタン
        btn_y = height - 85
        
        buttons["draft_developmental"] = Button(
            center_x + 30, btn_y, 180, 50,
            "この選手を指名", "success", font=fonts.body
        )
        buttons["draft_developmental"].enabled = selected_idx >= 0
        buttons["draft_developmental"].draw(self.screen)
        
        buttons["skip_developmental"] = Button(
            center_x - 210, btn_y, 180, 50,
            "育成ドラフト終了", "ghost", font=fonts.body
        )
        buttons["skip_developmental"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons

    def draw_pitcher_order_screen(self, player_team, pitcher_order_tab: str = "rotation",
                                  selected_rotation_slot: int = -1,
                                  selected_relief_slot: int = -1,
                                  scroll_offset: int = 0) -> Dict[str, Button]:
        """投手オーダー画面を描画（ローテーション・中継ぎ・抑え設定）"""
        from models import Position, PitchType
        
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        
        team_color = self.get_team_color(player_team.name) if player_team else Colors.PRIMARY
        header_h = draw_header(self.screen, "投手起用設定", 
                               "先発ローテーション・中継ぎ・抑えを設定", team_color)
        
        buttons = {}
        
        if not player_team:
            return buttons
        
        # タブボタン
        tab_y = header_h + 15
        tab_items = [
            ("rotation", "先発ローテ"),
            ("relief", "中継ぎ"),
            ("closer", "抑え"),
        ]
        
        tab_x = 50
        for tab_id, tab_name in tab_items:
            is_active = pitcher_order_tab == tab_id
            btn_style = "primary" if is_active else "ghost"
            buttons[f"tab_{tab_id}"] = Button(tab_x, tab_y, 130, 40, tab_name, btn_style, font=fonts.body)
            buttons[f"tab_{tab_id}"].draw(self.screen)
            tab_x += 140
        
        content_y = tab_y + 55
        
        # ====================
        # 左パネル: 設定済み投手陣
        # ====================
        left_card = Card(30, content_y, 400, height - content_y - 90, "CURRENT STAFF")
        left_rect = left_card.draw(self.screen)
        
        staff_y = left_rect.y + 45
        
        if pitcher_order_tab == "rotation":
            # 先発ローテーション（6人）
            title_surf = fonts.body_bold.render("先発ローテーション", True, Colors.PRIMARY)
            self.screen.blit(title_surf, (left_rect.x + 15, staff_y))
            staff_y += 35
            
            rotation = player_team.rotation if player_team.rotation else []
            for i in range(6):
                slot_rect = pygame.Rect(left_rect.x + 10, staff_y, left_rect.width - 20, 45)
                is_selected = selected_rotation_slot == i
                
                bg_color = Colors.SECONDARY if is_selected else (Colors.BG_CARD if i % 2 == 0 else Colors.BG_INPUT)
                pygame.draw.rect(self.screen, bg_color, slot_rect, border_radius=6)
                
                # スロット番号（曜日表示）
                weekdays = ["月", "火", "水", "木", "金", "土"]
                day_surf = fonts.body_bold.render(f"{weekdays[i]}", True, Colors.PRIMARY)
                self.screen.blit(day_surf, (slot_rect.x + 10, slot_rect.y + 12))
                
                if i < len(rotation) and 0 <= rotation[i] < len(player_team.players):
                    pitcher = player_team.players[rotation[i]]
                    name_surf = fonts.body.render(pitcher.name, True, Colors.TEXT_PRIMARY)
                    self.screen.blit(name_surf, (slot_rect.x + 50, slot_rect.y + 12))
                    
                    # 能力表示
                    stats = pitcher.stats
                    ability_text = f"{stats.speed_to_kmh()}km 制球{stats.control} 変化{stats.breaking}"
                    ability_surf = fonts.tiny.render(ability_text, True, Colors.TEXT_SECONDARY)
                    self.screen.blit(ability_surf, (slot_rect.x + 200, slot_rect.y + 15))
                else:
                    empty_surf = fonts.body.render("- 未設定 -", True, Colors.TEXT_MUTED)
                    self.screen.blit(empty_surf, (slot_rect.x + 50, slot_rect.y + 12))
                
                buttons[f"rotation_slot_{i}"] = Button(slot_rect.x, slot_rect.y, slot_rect.width, slot_rect.height, "", "ghost")
                staff_y += 50
        
        elif pitcher_order_tab == "relief":
            # 中継ぎ投手
            title_surf = fonts.body_bold.render("中継ぎ投手", True, Colors.WARNING)
            self.screen.blit(title_surf, (left_rect.x + 15, staff_y))
            staff_y += 35
            
            bench_pitchers = player_team.bench_pitchers if hasattr(player_team, 'bench_pitchers') else []
            setup_pitchers = player_team.setup_pitchers if player_team.setup_pitchers else []
            
            # bench_pitchersとsetup_pitchersを統合
            relief_pitchers = list(set(bench_pitchers) | set(setup_pitchers))
            
            for i in range(8):
                slot_rect = pygame.Rect(left_rect.x + 10, staff_y, left_rect.width - 20, 45)
                is_selected = selected_relief_slot == i
                
                bg_color = Colors.SECONDARY if is_selected else (Colors.BG_CARD if i % 2 == 0 else Colors.BG_INPUT)
                pygame.draw.rect(self.screen, bg_color, slot_rect, border_radius=6)
                
                slot_surf = fonts.body_bold.render(f"{i+1}", True, Colors.WARNING)
                self.screen.blit(slot_surf, (slot_rect.x + 10, slot_rect.y + 12))
                
                if i < len(relief_pitchers) and 0 <= relief_pitchers[i] < len(player_team.players):
                    pitcher = player_team.players[relief_pitchers[i]]
                    name_surf = fonts.body.render(pitcher.name, True, Colors.TEXT_PRIMARY)
                    self.screen.blit(name_surf, (slot_rect.x + 50, slot_rect.y + 12))
                    
                    stats = pitcher.stats
                    ability_text = f"{stats.speed_to_kmh()}km 制球{stats.control}"
                    ability_surf = fonts.tiny.render(ability_text, True, Colors.TEXT_SECONDARY)
                    self.screen.blit(ability_surf, (slot_rect.x + 220, slot_rect.y + 15))
                else:
                    empty_surf = fonts.body.render("- 未設定 -", True, Colors.TEXT_MUTED)
                    self.screen.blit(empty_surf, (slot_rect.x + 50, slot_rect.y + 12))
                
                buttons[f"relief_slot_{i}"] = Button(slot_rect.x, slot_rect.y, slot_rect.width, slot_rect.height, "", "ghost")
                staff_y += 50
        
        elif pitcher_order_tab == "closer":
            # 抑え投手（1人）
            title_surf = fonts.body_bold.render("守護神（クローザー）", True, Colors.DANGER)
            self.screen.blit(title_surf, (left_rect.x + 15, staff_y))
            staff_y += 40
            
            closer_rect = pygame.Rect(left_rect.x + 10, staff_y, left_rect.width - 20, 80)
            pygame.draw.rect(self.screen, Colors.BG_CARD, closer_rect, border_radius=10)
            pygame.draw.rect(self.screen, Colors.DANGER, closer_rect, 2, border_radius=10)
            
            if player_team.closer_idx >= 0 and player_team.closer_idx < len(player_team.players):
                closer = player_team.players[player_team.closer_idx]
                
                # 大きめの名前表示
                name_surf = fonts.h2.render(closer.name, True, Colors.DANGER)
                self.screen.blit(name_surf, (closer_rect.x + 20, closer_rect.y + 10))
                
                # 能力表示
                stats = closer.stats
                ability_text = f"{stats.speed_to_kmh()}km  制球{stats.control}  変化{stats.breaking}  スタミナ{stats.stamina}"
                ability_surf = fonts.body.render(ability_text, True, Colors.TEXT_SECONDARY)
                self.screen.blit(ability_surf, (closer_rect.x + 20, closer_rect.y + 48))
            else:
                empty_surf = fonts.h3.render("- 未設定 -", True, Colors.TEXT_MUTED)
                self.screen.blit(empty_surf, (closer_rect.x + 100, closer_rect.y + 28))
            
            buttons["closer_slot"] = Button(closer_rect.x, closer_rect.y, closer_rect.width, closer_rect.height, "", "ghost")
        
        # ====================
        # 右パネル: 投手一覧
        # ====================
        right_card = Card(450, content_y, width - 480, height - content_y - 90, "PITCHERS")
        right_rect = right_card.draw(self.screen)
        
        # フィルター（タイプ別）
        pitchers = [p for p in player_team.players if p.position == Position.PITCHER and not p.is_developmental]
        
        # タブに応じたフィルタ
        if pitcher_order_tab == "rotation":
            # 先発投手を優先表示
            pitchers.sort(key=lambda p: (0 if p.pitch_type == PitchType.STARTER else 1, -p.stats.overall_pitching()))
        elif pitcher_order_tab == "relief":
            # 中継ぎを優先表示
            pitchers.sort(key=lambda p: (0 if p.pitch_type == PitchType.RELIEVER else 1, -p.stats.overall_pitching()))
        elif pitcher_order_tab == "closer":
            # 抑えを優先表示
            pitchers.sort(key=lambda p: (0 if p.pitch_type == PitchType.CLOSER else 1, -p.stats.overall_pitching()))
        
        list_y = right_rect.y + 45
        
        # ヘッダー
        headers = [("名前", 150), ("タイプ", 70), ("球速", 50), ("制球", 50), ("変化", 50), ("スタ", 50)]
        hx = right_rect.x + 15
        for h_name, h_width in headers:
            h_surf = fonts.small.render(h_name, True, Colors.TEXT_MUTED)
            self.screen.blit(h_surf, (hx, list_y))
            hx += h_width
        list_y += 28
        
        pygame.draw.line(self.screen, Colors.BORDER, (right_rect.x + 10, list_y), (right_rect.right - 10, list_y))
        list_y += 8
        
        # 表示範囲を計算
        visible_count = (right_rect.bottom - list_y - 20) // 38
        start_idx = scroll_offset
        end_idx = min(start_idx + visible_count, len(pitchers))
        
        for i, pitcher in enumerate(pitchers[start_idx:end_idx], start_idx):
            row_rect = pygame.Rect(right_rect.x + 10, list_y, right_rect.width - 20, 35)
            
            bg_color = Colors.BG_CARD if i % 2 == 0 else Colors.BG_INPUT
            pygame.draw.rect(self.screen, bg_color, row_rect, border_radius=4)
            
            rx = right_rect.x + 15
            
            # 名前
            name_surf = fonts.body.render(pitcher.name[:8], True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_surf, (rx, list_y + 8))
            rx += 150
            
            # タイプ
            type_text = pitcher.pitch_type.value[:2] if pitcher.pitch_type else "-"
            type_color = Colors.PRIMARY if pitcher.pitch_type == PitchType.STARTER else (
                Colors.WARNING if pitcher.pitch_type == PitchType.RELIEVER else Colors.DANGER)
            type_surf = fonts.small.render(type_text, True, type_color)
            self.screen.blit(type_surf, (rx, list_y + 10))
            rx += 70
            
            # 能力値
            stats = pitcher.stats
            for val in [stats.speed, stats.control, stats.breaking, stats.stamina]:
                val_color = Colors.SUCCESS if val >= 70 else (Colors.WARNING if val >= 50 else Colors.TEXT_SECONDARY)
                val_surf = fonts.small.render(str(val), True, val_color)
                self.screen.blit(val_surf, (rx, list_y + 10))
                rx += 50
            
            # 選択ボタン
            player_idx = player_team.players.index(pitcher)
            buttons[f"pitcher_{player_idx}"] = Button(row_rect.x, row_rect.y, row_rect.width, row_rect.height, "", "ghost")
            
            list_y += 38
        
        # スクロールボタン
        if scroll_offset > 0:
            buttons["pitcher_scroll_up"] = Button(right_rect.right - 50, right_rect.y + 45, 40, 30, "▲", "secondary")
            buttons["pitcher_scroll_up"].draw(self.screen)
        
        if end_idx < len(pitchers):
            buttons["pitcher_scroll_down"] = Button(right_rect.right - 50, right_rect.bottom - 40, 40, 30, "▼", "secondary")
            buttons["pitcher_scroll_down"].draw(self.screen)
        
        # ====================
        # 下部ボタン
        # ====================
        btn_y = height - 75
        
        buttons["pitcher_auto_set"] = Button(50, btn_y, 150, 50, "自動設定", "warning", font=fonts.body)
        buttons["pitcher_auto_set"].draw(self.screen)
        
        buttons["pitcher_back"] = Button(220, btn_y, 150, 50, "戻る", "ghost", font=fonts.body)
        buttons["pitcher_back"].draw(self.screen)
        
        buttons["to_bench_setting"] = Button(width - 220, btn_y, 180, 50, "ベンチ設定へ", "primary", font=fonts.body)
        buttons["to_bench_setting"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons

    def draw_bench_setting_screen(self, player_team, bench_tab: str = "batters",
                                  scroll_offset: int = 0) -> Dict[str, Button]:
        """ベンチ入りメンバー設定画面を描画"""
        from models import Position, PitchType
        
        draw_background(self.screen, "gradient")
        
        width = self.screen.get_width()
        height = self.screen.get_height()
        
        team_color = self.get_team_color(player_team.name) if player_team else Colors.PRIMARY
        header_h = draw_header(self.screen, "ベンチ入りメンバー設定", 
                               "試合に出場する控え選手を選択", team_color)
        
        buttons = {}
        
        if not player_team:
            return buttons
        
        # タブボタン
        tab_y = header_h + 15
        buttons["bench_tab_batters"] = Button(50, tab_y, 150, 40, "野手ベンチ", 
                                               "primary" if bench_tab == "batters" else "ghost", font=fonts.body)
        buttons["bench_tab_batters"].draw(self.screen)
        
        buttons["bench_tab_pitchers"] = Button(210, tab_y, 150, 40, "投手ベンチ",
                                                "primary" if bench_tab == "pitchers" else "ghost", font=fonts.body)
        buttons["bench_tab_pitchers"].draw(self.screen)
        
        # 登録情報表示
        info_text = f"一軍登録: {len(player_team.active_roster)}/{player_team.MAX_ACTIVE_ROSTER}人"
        info_surf = fonts.body.render(info_text, True, Colors.TEXT_SECONDARY)
        self.screen.blit(info_surf, (width - 250, tab_y + 10))
        
        content_y = tab_y + 55
        
        # ====================
        # 左パネル: 現在のベンチ
        # ====================
        left_card = Card(30, content_y, 380, height - content_y - 90, "CURRENT BENCH")
        left_rect = left_card.draw(self.screen)
        
        bench_y = left_rect.y + 45
        
        if bench_tab == "batters":
            title_surf = fonts.body_bold.render(f"ベンチ野手 ({len(player_team.bench_batters)}/{player_team.MAX_BENCH_BATTERS})", True, Colors.PRIMARY)
            self.screen.blit(title_surf, (left_rect.x + 15, bench_y))
            bench_y += 35
            
            for i, player_idx in enumerate(player_team.bench_batters):
                if 0 <= player_idx < len(player_team.players):
                    player = player_team.players[player_idx]
                    
                    row_rect = pygame.Rect(left_rect.x + 10, bench_y, left_rect.width - 20, 40)
                    pygame.draw.rect(self.screen, Colors.BG_CARD if i % 2 == 0 else Colors.BG_INPUT, row_rect, border_radius=4)
                    
                    # 名前とポジション
                    name_surf = fonts.body.render(player.name, True, Colors.TEXT_PRIMARY)
                    self.screen.blit(name_surf, (row_rect.x + 10, row_rect.y + 10))
                    
                    pos_surf = fonts.small.render(player.position.value[:2], True, Colors.TEXT_SECONDARY)
                    self.screen.blit(pos_surf, (row_rect.x + 180, row_rect.y + 12))
                    
                    # 総合力
                    overall = player.stats.overall_batting()
                    ov_surf = fonts.small.render(f"総合{overall:.0f}", True, Colors.TEXT_MUTED)
                    self.screen.blit(ov_surf, (row_rect.x + 230, row_rect.y + 12))
                    
                    # 外すボタン
                    buttons[f"remove_bench_batter_{i}"] = Button(row_rect.right - 60, row_rect.y + 5, 50, 30, "外す", "danger")
                    buttons[f"remove_bench_batter_{i}"].draw(self.screen)
                    
                    bench_y += 45
        
        else:  # pitchers
            title_surf = fonts.body_bold.render(f"ベンチ投手 ({len(player_team.bench_pitchers)}/{player_team.MAX_BENCH_PITCHERS})", True, Colors.WARNING)
            self.screen.blit(title_surf, (left_rect.x + 15, bench_y))
            bench_y += 35
            
            for i, player_idx in enumerate(player_team.bench_pitchers):
                if 0 <= player_idx < len(player_team.players):
                    pitcher = player_team.players[player_idx]
                    
                    row_rect = pygame.Rect(left_rect.x + 10, bench_y, left_rect.width - 20, 40)
                    pygame.draw.rect(self.screen, Colors.BG_CARD if i % 2 == 0 else Colors.BG_INPUT, row_rect, border_radius=4)
                    
                    # 名前とタイプ
                    name_surf = fonts.body.render(pitcher.name, True, Colors.TEXT_PRIMARY)
                    self.screen.blit(name_surf, (row_rect.x + 10, row_rect.y + 10))
                    
                    type_text = pitcher.pitch_type.value[:2] if pitcher.pitch_type else "-"
                    type_surf = fonts.small.render(type_text, True, Colors.TEXT_SECONDARY)
                    self.screen.blit(type_surf, (row_rect.x + 180, row_rect.y + 12))
                    
                    # 総合力
                    overall = pitcher.stats.overall_pitching()
                    ov_surf = fonts.small.render(f"総合{overall:.0f}", True, Colors.TEXT_MUTED)
                    self.screen.blit(ov_surf, (row_rect.x + 230, row_rect.y + 12))
                    
                    # 外すボタン
                    buttons[f"remove_bench_pitcher_{i}"] = Button(row_rect.right - 60, row_rect.y + 5, 50, 30, "外す", "danger")
                    buttons[f"remove_bench_pitcher_{i}"].draw(self.screen)
                    
                    bench_y += 45
        
        # ====================
        # 右パネル: 選手一覧（追加可能な選手）
        # ====================
        right_card = Card(430, content_y, width - 460, height - content_y - 90, "AVAILABLE")
        right_rect = right_card.draw(self.screen)
        
        list_y = right_rect.y + 45
        
        if bench_tab == "batters":
            # スタメン・ベンチ以外の野手
            lineup_set = set(player_team.current_lineup) if player_team.current_lineup else set()
            bench_set = set(player_team.bench_batters)
            
            available = [p for p in player_team.players 
                        if p.position != Position.PITCHER 
                        and not p.is_developmental
                        and player_team.players.index(p) not in lineup_set
                        and player_team.players.index(p) not in bench_set]
            available.sort(key=lambda p: -p.stats.overall_batting())
        else:
            # ローテ・ベンチ以外の投手
            rotation_set = set(player_team.rotation) if player_team.rotation else set()
            bench_set = set(player_team.bench_pitchers)
            
            available = [p for p in player_team.players 
                        if p.position == Position.PITCHER 
                        and not p.is_developmental
                        and player_team.players.index(p) not in rotation_set
                        and player_team.players.index(p) not in bench_set]
            available.sort(key=lambda p: -p.stats.overall_pitching())
        
        # ヘッダー
        if bench_tab == "batters":
            headers = [("名前", 130), ("守備", 50), ("ミート", 55), ("パワー", 55), ("走力", 50)]
        else:
            headers = [("名前", 130), ("タイプ", 60), ("球速", 50), ("制球", 50), ("変化", 50)]
        
        hx = right_rect.x + 15
        for h_name, h_width in headers:
            h_surf = fonts.small.render(h_name, True, Colors.TEXT_MUTED)
            self.screen.blit(h_surf, (hx, list_y))
            hx += h_width
        list_y += 28
        
        pygame.draw.line(self.screen, Colors.BORDER, (right_rect.x + 10, list_y), (right_rect.right - 10, list_y))
        list_y += 8
        
        # 表示範囲
        visible_count = (right_rect.bottom - list_y - 20) // 40
        start_idx = scroll_offset
        end_idx = min(start_idx + visible_count, len(available))
        
        for i, player in enumerate(available[start_idx:end_idx], start_idx):
            row_rect = pygame.Rect(right_rect.x + 10, list_y, right_rect.width - 20, 38)
            
            bg_color = Colors.BG_CARD if i % 2 == 0 else Colors.BG_INPUT
            pygame.draw.rect(self.screen, bg_color, row_rect, border_radius=4)
            
            rx = right_rect.x + 15
            
            # 名前
            name_surf = fonts.body.render(player.name[:7], True, Colors.TEXT_PRIMARY)
            self.screen.blit(name_surf, (rx, list_y + 9))
            rx += 130
            
            if bench_tab == "batters":
                # 守備
                pos_surf = fonts.small.render(player.position.value[:2], True, Colors.TEXT_SECONDARY)
                self.screen.blit(pos_surf, (rx, list_y + 11))
                rx += 50
                
                # 能力値
                stats = player.stats
                for val in [stats.contact, stats.power, stats.speed]:
                    val_color = Colors.SUCCESS if val >= 70 else (Colors.WARNING if val >= 50 else Colors.TEXT_SECONDARY)
                    val_surf = fonts.small.render(str(val), True, val_color)
                    self.screen.blit(val_surf, (rx, list_y + 11))
                    rx += 55
            else:
                # タイプ
                type_text = player.pitch_type.value[:2] if player.pitch_type else "-"
                type_surf = fonts.small.render(type_text, True, Colors.TEXT_SECONDARY)
                self.screen.blit(type_surf, (rx, list_y + 11))
                rx += 60
                
                # 能力値
                stats = player.stats
                for val in [stats.speed, stats.control, stats.breaking]:
                    val_color = Colors.SUCCESS if val >= 70 else (Colors.WARNING if val >= 50 else Colors.TEXT_SECONDARY)
                    val_surf = fonts.small.render(str(val), True, val_color)
                    self.screen.blit(val_surf, (rx, list_y + 11))
                    rx += 50
            
            # 追加ボタン
            player_idx = player_team.players.index(player)
            buttons[f"add_bench_{player_idx}"] = Button(row_rect.right - 60, row_rect.y + 4, 50, 30, "追加", "success")
            buttons[f"add_bench_{player_idx}"].draw(self.screen)
            
            list_y += 40
        
        # スクロールボタン
        if scroll_offset > 0:
            buttons["bench_scroll_up"] = Button(right_rect.right - 50, right_rect.y + 45, 40, 30, "▲", "secondary")
            buttons["bench_scroll_up"].draw(self.screen)
        
        if end_idx < len(available):
            buttons["bench_scroll_down"] = Button(right_rect.right - 50, right_rect.bottom - 40, 40, 30, "▼", "secondary")
            buttons["bench_scroll_down"].draw(self.screen)
        
        # ====================
        # 下部ボタン
        # ====================
        btn_y = height - 75
        
        buttons["bench_auto_set"] = Button(50, btn_y, 150, 50, "自動設定", "warning", font=fonts.body)
        buttons["bench_auto_set"].draw(self.screen)
        
        buttons["bench_back"] = Button(220, btn_y, 150, 50, "戻る", "ghost", font=fonts.body)
        buttons["bench_back"].draw(self.screen)
        
        buttons["to_lineup"] = Button(width - 220, btn_y, 180, 50, "オーダーへ", "primary", font=fonts.body)
        buttons["to_lineup"].draw(self.screen)
        
        ToastManager.update_and_draw(self.screen)
        
        return buttons