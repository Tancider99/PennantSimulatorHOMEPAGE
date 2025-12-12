# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Live Game Page (Modern & Simple)
High-End Data Visualization & Broadcast UI
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout, QGraphicsDropShadowEffect,
    QDialog, QSizePolicy, QProgressBar, QSplitter
)
from PySide6.QtCore import Qt, Signal, QTimer, QPointF, QRectF, QSize, QEasingCurve
from PySide6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QPainterPath, 
    QLinearGradient, QPolygonF, QRadialGradient
)

import sys
import os
import math
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from UI.theme import get_theme
from live_game_engine import PitchType, PlayResult, PitchResult, BattedBallType, get_rank, PitchData, BattedBallData

# ========================================
# ユーティリティ & デザイン定数
# ========================================
THEME = get_theme()

class VisualStyle:
    # Modern Flat Dark Theme (Game Themed: Dark/Amber/Cyan)
    BG_MAIN = QColor("#101010")      # Matte Black (Primary Background)
    BG_PANEL = QColor("#1D1D1D")     # Dark Grey Card (Visual Elements Background)
    BG_ELEVATED = QColor("#282828")  # Elevated Elements (Data Cards, Buttons)
    
    TEXT_PRIMARY = QColor("#E0E0E0")  # Light Text
    TEXT_SECONDARY = QColor("#A0A0A0") # Secondary Info
    TEXT_TERTIARY = QColor("#606060") # Low-Emphasis

    # Result Colors (User Specified)
    COLOR_STRIKE = QColor("#FFC107")  # Amber (Strike, Foul, SO)
    COLOR_BALL = QColor("#4CAF50")    # Green (Ball)
    COLOR_HIT = QColor("#00BCD4")     # Cyan (Hit, HR)
    COLOR_OUT = QColor("#FF5722")     # Deep Orange/Red (Out)
    
    BORDER_COLOR = QColor("#383838")

    # Fonts
    FONT_NUM = "Roboto Mono"
    FONT_UI = "Segoe UI"
    
    # Generic Accents (Legacy for UI parts)
    ACCENT_CYAN = QColor("#00BCD4")
    ACCENT_MAGENTA = QColor("#FF4081")
    ACCENT_GOLD = QColor("#FFC107")
    ACCENT_RED = QColor("#FF5722")
    ACCENT_GREEN = QColor("#4CAF50")

    @staticmethod
    def get_result_color(result: str):
        """結果文字列に基づいて色を返す"""
        res = str(result)
        
        if any(x in res for x in ["安打", "本塁打", "二塁打", "三塁打"]):
            return VisualStyle.COLOR_HIT
            
        if any(x in res for x in ["アウト", "フライ", "ゴロ", "ライナー", "併殺", "失策", "犠"]):
            return VisualStyle.COLOR_OUT
            
        if "ボール" in res or "四球" in res or "死球" in res:
            return VisualStyle.COLOR_BALL
            
        return VisualStyle.COLOR_STRIKE

# ========================================
# 3D 投球軌道 & ストライクゾーン (Simple & Clean)
# ========================================
class GamedayStrikeZone(QWidget):
    animation_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(350, 400)
        self.pitches = []  # (PitchData, result_str, color)
        self.last_pitch = None
        
        # アニメーション用
        self.anim_timer = QTimer(self)
        self.anim_timer.interval = 16 # ~60fps
        self.anim_timer.timeout.connect(self._update_anim)
        self.anim_progress = 0.0
        self.is_animating = False

    def animate_pitch(self, pitch: PitchData, result: str):
        """投球アニメーション開始"""
        self.last_pitch = pitch
        self.last_result = result
        self.last_color = VisualStyle.get_result_color(result)
        
        self.anim_progress = 0.0
        self.is_animating = True
        self.anim_timer.start()

    def add_to_history(self):
        """アニメーション完了後に履歴に追加"""
        if self.last_pitch:
            self.pitches.append((self.last_pitch, self.last_result, self.last_color))
            if len(self.pitches) > 10:
                self.pitches.pop(0)

    def clear(self):
        self.pitches = []
        self.last_pitch = None
        self.is_animating = False
        self.update()

    def _update_anim(self):
        speed_factor = 0.025
        if self.last_pitch:
            speed_factor = 0.02 + (self.last_pitch.velocity / 3000.0)
            
        self.anim_progress += speed_factor
        if self.anim_progress >= 1.0:
            self.anim_progress = 1.0
            self.is_animating = False
            self.anim_timer.stop()
            self.add_to_history()
            self.animation_finished.emit()
            
        self.update()

    def project_3d(self, x, y, z, width, height):
        """
        簡易パースペクティブ投影
        """
        scale = min(width, height) * 1.3 
        cam_dist = 4.0
        depth_factor = cam_dist / (cam_dist + y/12.0) 
        
        screen_x = width/2 + (x * scale * 0.6 * depth_factor)
        # ゾーン位置調整 
        screen_y = height * 1.00 - (z * scale * 0.6 * depth_factor)
        
        return QPointF(screen_x, screen_y), depth_factor

    def draw_pitch_symbol(self, painter, center: QPointF, size: float, pitch_type: str, color: QColor):
        """球種に応じた形状を描画"""
        painter.setBrush(color)
        painter.setPen(Qt.NoPen)
        
        pt = pitch_type
        
        if pt in ["ストレート", "ツーシーム"]:
            # 円
            painter.drawEllipse(center, size, size)
            
        elif pt in ["フォーク", "スプリット", "チェンジアップ", "ナックル"]:
            # 四角 (落ちる系)
            rect = QRectF(center.x()-size, center.y()-size, size*2, size*2)
            painter.drawRect(rect)
            
        elif pt in ["スライダー", "カットボール", "カーブ"]:
            # 三角 (曲がる系)
            # 上向き三角
            poly = QPolygonF([
                QPointF(center.x(), center.y() - size),
                QPointF(center.x() + size, center.y() + size),
                QPointF(center.x() - size, center.y() + size)
            ])
            painter.drawPolygon(poly)
            
        else: # シュート, シンカー等
            # ダイヤ (菱形)
            poly = QPolygonF([
                QPointF(center.x(), center.y() - size*1.2),
                QPointF(center.x() + size*1.2, center.y()),
                QPointF(center.x(), center.y() + size*1.2),
                QPointF(center.x() - size*1.2, center.y())
            ])
            painter.drawPolygon(poly)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # 背景 (単色・シンプル)
        painter.fillRect(self.rect(), VisualStyle.BG_PANEL)
        
        # --- ホームベース周辺 ---
        hp_scale = 0.43 # 幅43cm
        hp_pts = [
            self.project_3d(0, 0, 0, w, h)[0], # 先端
            self.project_3d(hp_scale/2, 0.2, 0, w, h)[0],
            self.project_3d(hp_scale/2, 0.4, 0, w, h)[0],
            self.project_3d(-hp_scale/2, 0.4, 0, w, h)[0],
            self.project_3d(-hp_scale/2, 0.2, 0, w, h)[0],
        ]
        painter.setBrush(QColor("#E0E0E0"))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(QPolygonF(hp_pts))

        # バッターボックス
        painter.setPen(QPen(QColor(255, 255, 255, 50), 2))
        l_box_tl, _ = self.project_3d(-1.2, 0, 0, w, h)
        l_box_bl, _ = self.project_3d(-1.2, 1.5, 0, w, h)
        painter.drawLine(l_box_tl, l_box_bl)
        
        r_box_tl, _ = self.project_3d(1.2, 0, 0, w, h)
        r_box_bl, _ = self.project_3d(1.2, 1.5, 0, w, h)
        painter.drawLine(r_box_tl, r_box_bl)

        # --- ストライクゾーン枠 ---
        zone_top = 1.05
        zone_btm = 0.45
        zone_w = 0.216
        
        tl_f, _ = self.project_3d(-zone_w, 0, zone_top, w, h)
        br_f, _ = self.project_3d(zone_w, 0, zone_btm, w, h)
        
        # 背面 (立体感)
        back_depth = 0.5
        tl_b, _ = self.project_3d(-zone_w, back_depth, zone_top, w, h)
        tr_b, _ = self.project_3d(zone_w, back_depth, zone_top, w, h)
        bl_b, _ = self.project_3d(-zone_w, back_depth, zone_btm, w, h)
        br_b, _ = self.project_3d(zone_w, back_depth, zone_btm, w, h)
        
        # 枠線
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1, Qt.DotLine))
        painter.drawLine(tl_b, tr_b); painter.drawLine(tr_b, br_b)
        painter.drawLine(br_b, bl_b); painter.drawLine(bl_b, tl_b)
        painter.drawLine(tl_f, tl_b); painter.drawLine(self.project_3d(zone_w, 0, zone_top, w, h)[0], tr_b)
        
        # メインゾーン
        painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
        painter.setBrush(QColor(255, 255, 255, 10))
        painter.drawRect(QRectF(tl_f, br_f))

        # --- 投球履歴 ---
        for i, (pitch, result, color) in enumerate(self.pitches):
            pt, _ = self.project_3d(pitch.location.x, 0, pitch.location.z, w, h)
            
            # 形状描画
            self.draw_pitch_symbol(painter, pt, 7, pitch.pitch_type, color)
            
            painter.setPen(QColor(0,0,0,200)) # 文字は見やすく黒系で
            painter.setFont(QFont(VisualStyle.FONT_NUM, 8, QFont.Bold))
            painter.drawText(QRectF(pt.x()-10, pt.y()-10, 20, 20), Qt.AlignCenter, str(i+1))

        # --- 最新投球アニメーション ---
        if self.last_pitch:
            pitch = self.last_pitch
            color = self.last_color # 結果色
            
            path = QPainterPath()
            shadow_path = QPainterPath()
            
            if pitch.trajectory:
                start_pt, _ = self.project_3d(pitch.trajectory[0][0], pitch.trajectory[0][1], pitch.trajectory[0][2], w, h)
                path.moveTo(start_pt)
                
                s_start, _ = self.project_3d(pitch.trajectory[0][0], pitch.trajectory[0][1], 0, w, h)
                shadow_path.moveTo(s_start)
                
                total_steps = len(pitch.trajectory)
                current_steps = int(total_steps * self.anim_progress)
                if current_steps < 1: current_steps = 1
                
                current_pos_3d = pitch.trajectory[0]

                for i in range(1, current_steps):
                     pos = pitch.trajectory[i]
                     current_pos_3d = pos
                     pt, df = self.project_3d(pos[0], pos[1], pos[2], w, h)
                     path.lineTo(pt)
                     s_pt, _ = self.project_3d(pos[0], pos[1], 0, w, h)
                     shadow_path.lineTo(s_pt)

                # 影
                painter.setPen(QPen(QColor(0,0,0,80), 3))
                painter.setBrush(Qt.NoBrush)
                painter.drawPath(shadow_path)

                # 軌道
                pen = QPen(color, 4)
                pen.setCapStyle(Qt.RoundCap)
                painter.setPen(pen)
                painter.drawPath(path)
                
                # ボール本体（形状で描画）
                # ★修正: アニメーションが完了したら、履歴点と同じ座標 (pitch.location, y=0) を使用
                if not self.is_animating and self.anim_progress >= 1.0:
                    ball_pt, _ = self.project_3d(pitch.location.x, 0, pitch.location.z, w, h)
                else:
                    # アニメーション中は、current_pos_3d (trajectoryの点) を使用
                    ball_pt, _ = self.project_3d(current_pos_3d[0], current_pos_3d[1], current_pos_3d[2], w, h)
                    
                self.draw_pitch_symbol(painter, ball_pt, 9, pitch.pitch_type, color)

                # 情報表示
                if not self.is_animating:
                    final_pt, _ = self.project_3d(pitch.location.x, 0, pitch.location.z, w, h)
                    
                    info_rect = QRectF(final_pt.x() + 15, final_pt.y() - 25, 130, 45)
                    
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(30, 30, 30, 220))
                    painter.drawRoundedRect(info_rect, 4, 4)
                    
                    painter.setPen(color)
                    painter.setFont(QFont(VisualStyle.FONT_NUM, 10, QFont.Bold))
                    painter.drawText(info_rect.adjusted(8,0,0,0), Qt.AlignLeft|Qt.AlignVCenter, f"{int(pitch.velocity)}km\n{pitch.pitch_type}")
                    
# ========================================
# フィールドビュー (Simple & Clean)
# ========================================
class BroadcastField(QWidget):
    animation_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(300, 300)
        self.batted_ball = None
        self.result_str = "" # 結果文字列保持用
        self.runners = [False, False, False]
        
        self.anim_timer = QTimer(self)
        self.anim_timer.interval = 16
        self.anim_timer.timeout.connect(self._update_anim)
        self.anim_progress = 0.0
        self.is_animating = False

    def animate_ball(self, ball: BattedBallData, runners, result_str: str):
        self.batted_ball = ball
        self.runners = runners
        self.result_str = result_str
        self.anim_progress = 0.0
        self.is_animating = True
        self.anim_timer.start()

    def set_runners_only(self, runners):
        self.runners = runners
        self.update()

    def clear(self):
        self.batted_ball = None
        self.result_str = ""
        self.is_animating = False
        self.update()

    def _update_anim(self):
        self.anim_progress += 0.02
        if self.anim_progress >= 1.0:
            self.anim_progress = 1.0
            self.is_animating = False
            self.anim_timer.stop()
            self.animation_finished.emit()
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        
        # 背景 (単色)
        painter.fillRect(self.rect(), VisualStyle.BG_PANEL)

        # 拡大表示
        cx, cy = w / 2, h * 0.9
        max_r = min(w/2, h * 0.85)
        scale = max_r / 122.0
        
        # フェアグラウンド (扇形)
        field_path = QPainterPath()
        field_path.moveTo(cx, cy)
        field_path.arcTo(cx - 122*scale, cy - 122*scale, 244*scale, 244*scale, 45, 90) 
        field_path.closeSubpath()
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#263238")) # Dark Green
        painter.drawPath(field_path)
        
        # 内野 (ダイヤモンド)
        base_dist = 27.43 * scale
        diamond = QPolygonF()
        diamond.append(QPointF(cx, cy))
        diamond.append(QPointF(cx + base_dist, cy - base_dist))
        diamond.append(QPointF(cx, cy - base_dist*2))
        diamond.append(QPointF(cx - base_dist, cy - base_dist))
        
        painter.setBrush(QColor("#4E342E")) # Dark Brown
        painter.setPen(QPen(QColor(255,255,255,30), 1))
        painter.drawPolygon(diamond)
        
        # ベース & ランナー
        base_size = 8
        bases = [
            (cx + base_dist, cy - base_dist),
            (cx, cy - base_dist*2),
            (cx - base_dist, cy - base_dist)
        ]
        
        for i, (bx, by) in enumerate(bases):
            is_occ = self.runners[i]
            col = VisualStyle.COLOR_STRIKE if is_occ else QColor(255,255,255,30) # ランナーは黄色で見やすく
            
            painter.setBrush(col)
            painter.setPen(Qt.white if is_occ else Qt.NoPen)
            
            # 菱形ベース
            poly = QPolygonF([
                QPointF(bx, by-base_size), QPointF(bx+base_size, by),
                QPointF(bx, by+base_size), QPointF(bx-base_size, by)
            ])
            painter.drawPolygon(poly)
            
            if is_occ:
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(QColor(255, 215, 0, 100), 4))
                painter.drawPolygon(poly)

        # --- 打球アニメーション ---
        if self.batted_ball:
            dist_px = self.batted_ball.distance * scale
            angle_rad = math.radians(self.batted_ball.spray_angle)
            
            target_lx = dist_px * math.sin(angle_rad)
            target_ly = -dist_px * math.cos(angle_rad)
            
            t = self.anim_progress
            
            h_factor = self.batted_ball.hang_time * 25 * scale 
            ctrl_x = target_lx / 2
            ctrl_y = target_ly / 2 - h_factor
            
            curr_x = 2 * (1-t) * t * ctrl_x + t*t * target_lx
            curr_y = 2 * (1-t) * t * ctrl_y + t*t * target_ly
            
            draw_x = cx + curr_x
            draw_y = cy + curr_y

            # 軌跡
            traj_path = QPainterPath()
            traj_path.moveTo(cx, cy)
            
            steps = int(30 * t)
            for i in range(1, steps + 1):
                sub_t = i / 30.0
                sx = 2 * (1-sub_t) * sub_t * ctrl_x + sub_t*sub_t * target_lx
                sy = 2 * (1-sub_t) * sub_t * ctrl_y + sub_t*sub_t * target_ly
                traj_path.lineTo(cx + sx, cy + sy)
            traj_path.lineTo(draw_x, draw_y)

            # 色決定（結果文字列を使用）
            color = VisualStyle.get_result_color(self.result_str)

            painter.setPen(QPen(color, 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(traj_path)
            
            # ボール
            painter.setBrush(color)
            painter.setPen(Qt.white)
            painter.drawEllipse(QPointF(draw_x, draw_y), 6, 6)
            
            if not self.is_animating:
                painter.setFont(QFont(VisualStyle.FONT_NUM, 10, QFont.Bold))
                painter.setPen(Qt.white)
                label = f"{int(self.batted_ball.distance)}m"
                painter.drawText(draw_x + 10, draw_y, label)

# ========================================
# データカード (Modern Flat)
# ========================================
class DataCard(QFrame):
    def __init__(self, title, value="-", parent=None, color=VisualStyle.ACCENT_CYAN):
        super().__init__(parent)
        self.setFixedHeight(70)
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {VisualStyle.BG_ELEVATED.name()};
                border-radius: 4px;
            }}
        """)
        
        l = QVBoxLayout(self)
        l.setContentsMargins(15, 10, 15, 10)
        l.setSpacing(2)
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet(f"color: {color.name()}; font-size: 10px; font-weight: 800; letter-spacing: 1px; border:none; background:transparent;")
        
        self.lbl_value = QLabel(str(value))
        self.lbl_value.setStyleSheet(f"color: {VisualStyle.TEXT_PRIMARY.name()}; font-family: '{VisualStyle.FONT_NUM}'; font-size: 18px; font-weight: bold; border:none; background:transparent;")
        
        l.addWidget(self.lbl_title)
        l.addWidget(self.lbl_value)

    def set_value(self, val):
        self.lbl_value.setText(str(val))

# ========================================
# メイン画面クラス
# ========================================
class LiveGamePage(QWidget):
    game_finished = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.live_engine = None
        self.is_simulating = False
        self.is_animating = False 
        self.need_zone_reset = False 
        self.date_str = "2027-01-01"
        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. ヘッダー
        self.scoreboard_widget = self._create_scoreboard()
        main_layout.addWidget(self.scoreboard_widget)

        # 2. メインコンテンツ
        content_area = QWidget()
        content_area.setStyleSheet(f"background: {VisualStyle.BG_MAIN.name()};")
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(15)
        
        # --- LEFT PANEL ---
        left_panel = QWidget()
        lp_layout = QVBoxLayout(left_panel)
        lp_layout.setContentsMargins(0,0,0,0)
        lp_layout.setSpacing(15)
        
        self.matchup_card = self._create_matchup_card()
        lp_layout.addWidget(self.matchup_card)
        
        # 3D Strike Zone
        self.zone_widget = GamedayStrikeZone()
        self.zone_widget.animation_finished.connect(self._on_animation_step_finished)
        lp_layout.addWidget(self.zone_widget, stretch=1)
        
        # ★追加: ピッチ結果表示
        self.lbl_pitch_result = QLabel("PITCH RESULT: ---")
        self.lbl_pitch_result.setAlignment(Qt.AlignCenter)
        self.lbl_pitch_result.setStyleSheet(f"color: {VisualStyle.TEXT_PRIMARY.name()}; font-size: 14px; font-weight: bold; padding: 5px; background: {VisualStyle.BG_ELEVATED.name()}; border-radius: 4px;")
        lp_layout.addWidget(self.lbl_pitch_result)
        
        # Pitch Stats Grid
        self.pitch_stats_grid = self._create_pitch_stats_grid()
        lp_layout.addWidget(self.pitch_stats_grid)
        
        content_layout.addWidget(left_panel, stretch=5)
        
        # --- RIGHT PANEL ---
        right_panel = QWidget()
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(0,0,0,0)
        rp_layout.setSpacing(15)
        
        self.field_widget = BroadcastField()
        self.field_widget.animation_finished.connect(self._on_animation_step_finished)
        rp_layout.addWidget(self.field_widget, stretch=4)
        
        self.hit_stats_grid = self._create_hit_stats_grid()
        rp_layout.addWidget(self.hit_stats_grid)
        
        self.log_widget = self._create_log_area()
        rp_layout.addWidget(self.log_widget, stretch=3)

        self.controls_widget = self._create_controls()
        rp_layout.addWidget(self.controls_widget)
        
        content_layout.addWidget(right_panel, stretch=4)
        main_layout.addWidget(content_area)

    def _create_scoreboard(self):
        w = QFrame()
        w.setFixedHeight(80)
        w.setStyleSheet(f"""
            QFrame {{
                background-color: {VisualStyle.BG_PANEL.name()};
                border-bottom: 1px solid {VisualStyle.BORDER_COLOR.name()};
            }}
        """)
        l = QHBoxLayout(w)
        l.setContentsMargins(30, 0, 30, 0)
        
        # Away
        self.lbl_away = QLabel("AWAY")
        self.lbl_away.setStyleSheet(f"font-size: 24px; font-weight: 900; color: {VisualStyle.TEXT_SECONDARY.name()}; font-family: 'Segoe UI Black';")
        self.lbl_away_score = QLabel("0")
        self.lbl_away_score.setStyleSheet(f"font-size: 48px; font-weight: 900; color: {VisualStyle.COLOR_STRIKE.name()}; font-family: '{VisualStyle.FONT_NUM}';")
        
        # Inning
        self.lbl_inning = QLabel("1st TOP")
        self.lbl_inning.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {VisualStyle.ACCENT_CYAN.name()}; margin: 0 30px;")
        
        # BSO
        bso_frame = QFrame()
        bl = QVBoxLayout(bso_frame)
        bl.setSpacing(3); bl.setContentsMargins(0,20,0,20)
        
        def mk_dots(label, col):
            r = QHBoxLayout()
            r.setSpacing(5)
            r.addWidget(QLabel(label, styleSheet=f"font-weight:bold; font-size:12px; color:{VisualStyle.TEXT_TERTIARY.name()}; width:15px;"))
            dots = []
            for _ in range(3 if label=="B" else 2):
                d = QLabel("●")
                d.setStyleSheet(f"color: {VisualStyle.BG_ELEVATED.name()}; font-size: 10px;")
                r.addWidget(d)
                dots.append(d)
            r.addStretch()
            bl.addLayout(r)
            return dots

        self.dots_b = mk_dots("B", VisualStyle.COLOR_BALL)
        self.dots_s = mk_dots("S", VisualStyle.COLOR_STRIKE)
        self.dots_o = mk_dots("O", VisualStyle.COLOR_OUT)
        
        # Home
        self.lbl_home_score = QLabel("0")
        self.lbl_home_score.setStyleSheet(f"font-size: 48px; font-weight: 900; color: {VisualStyle.COLOR_STRIKE.name()}; font-family: '{VisualStyle.FONT_NUM}';")
        self.lbl_home = QLabel("HOME")
        self.lbl_home.setStyleSheet(f"font-size: 24px; font-weight: 900; color: {VisualStyle.TEXT_PRIMARY.name()}; font-family: 'Segoe UI Black';")
        
        l.addWidget(self.lbl_away)
        l.addSpacing(15)
        l.addWidget(self.lbl_away_score)
        l.addStretch()
        l.addWidget(self.lbl_inning)
        l.addWidget(bso_frame)
        l.addStretch()
        l.addWidget(self.lbl_home_score)
        l.addSpacing(15)
        l.addWidget(self.lbl_home)
        
        return w

    def _create_matchup_card(self):
        f = QFrame()
        f.setStyleSheet("background: transparent;")
        l = QHBoxLayout(f)
        l.setContentsMargins(0,0,0,0)
        l.setSpacing(15)
        
        def create_box(title, col):
            b = QFrame()
            b.setStyleSheet(f"""
                QFrame {{
                    background-color: {VisualStyle.BG_ELEVATED.name()};
                    border-radius: 4px;
                    border-top: 3px solid {col.name()};
                }}
            """)
            gl = QGridLayout(b)
            gl.setContentsMargins(12, 10, 12, 10)
            gl.setSpacing(5)
            gl.addWidget(QLabel(title, styleSheet=f"color:{VisualStyle.TEXT_TERTIARY.name()}; font-size:10px; font-weight:bold; border:none; background:transparent;"), 0, 0, 1, 2)
            return b, gl

        # --- Pitcher Box ---
        p_box, pl = create_box("PITCHER", VisualStyle.ACCENT_RED)
        self.lbl_p_name = QLabel("---", styleSheet=f"color:{VisualStyle.TEXT_PRIMARY.name()}; font-weight:bold; font-size:16px; border:none; background:transparent;")
        pl.addWidget(self.lbl_p_name, 1, 0, 1, 2)
        
        self.pb_stamina = QProgressBar()
        self.pb_stamina.setFixedHeight(4)
        self.pb_stamina.setTextVisible(False)
        self.pb_stamina.setStyleSheet(f"QProgressBar{{background:{VisualStyle.BG_MAIN.name()}; border-radius:2px; border:none;}} QProgressBar::chunk{{background:{VisualStyle.ACCENT_RED.name()}; border-radius:2px;}}")
        pl.addWidget(self.pb_stamina, 2, 0, 1, 2)
        
        self.lbl_p_era = QLabel("ERA: -.--", styleSheet=f"color:{VisualStyle.TEXT_SECONDARY.name()}; font-size:11px; font-family:'{VisualStyle.FONT_NUM}'; border:none;")
        self.lbl_p_wl = QLabel("0W-0L", styleSheet=f"color:{VisualStyle.TEXT_SECONDARY.name()}; font-size:11px; font-family:'{VisualStyle.FONT_NUM}'; border:none;")
        self.lbl_p_so = QLabel("SO: 0", styleSheet=f"color:{VisualStyle.TEXT_SECONDARY.name()}; font-size:11px; font-family:'{VisualStyle.FONT_NUM}'; border:none;")
        
        pl.addWidget(self.lbl_p_era, 3, 0)
        pl.addWidget(self.lbl_p_wl, 3, 1)
        pl.addWidget(self.lbl_p_so, 4, 0)
        
        self.lbl_p_abil = QLabel("Stf:- Ctl:- Sta:-", styleSheet=f"color:{VisualStyle.TEXT_TERTIARY.name()}; font-size:10px; border:none;")
        pl.addWidget(self.lbl_p_abil, 5, 0, 1, 2)
        
        l.addWidget(p_box, stretch=1)
        
        # --- Batter Box ---
        b_box, bl = create_box("BATTER", VisualStyle.ACCENT_CYAN)
        self.lbl_b_name = QLabel("---", styleSheet=f"color:{VisualStyle.TEXT_PRIMARY.name()}; font-weight:bold; font-size:16px; border:none; background:transparent;")
        bl.addWidget(self.lbl_b_name, 1, 0, 1, 2)
        
        self.lbl_b_hand = QLabel("L / R", styleSheet=f"color:{VisualStyle.TEXT_TERTIARY.name()}; font-size:10px; border:none;")
        bl.addWidget(self.lbl_b_hand, 2, 0, 1, 2)
        
        self.lbl_b_avg = QLabel("AVG: .---", styleSheet=f"color:{VisualStyle.TEXT_SECONDARY.name()}; font-size:11px; font-family:'{VisualStyle.FONT_NUM}'; border:none;")
        self.lbl_b_ops = QLabel("OPS: .---", styleSheet=f"color:{VisualStyle.TEXT_SECONDARY.name()}; font-size:11px; font-family:'{VisualStyle.FONT_NUM}'; border:none;")
        self.lbl_b_hr_rbi = QLabel("HR: 0  RBI: 0", styleSheet=f"color:{VisualStyle.TEXT_SECONDARY.name()}; font-size:11px; font-family:'{VisualStyle.FONT_NUM}'; border:none;")
        
        bl.addWidget(self.lbl_b_avg, 3, 0)
        bl.addWidget(self.lbl_b_ops, 3, 1)
        bl.addWidget(self.lbl_b_hr_rbi, 4, 0, 1, 2)

        self.lbl_b_abil = QLabel("Con:- Pow:- Spd:-", styleSheet=f"color:{VisualStyle.TEXT_TERTIARY.name()}; font-size:10px; border:none;")
        bl.addWidget(self.lbl_b_abil, 5, 0, 1, 2)
        
        l.addWidget(b_box, stretch=1)
        
        return f

    def _create_pitch_stats_grid(self):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0,5,0,5)
        l.setSpacing(10)
        self.card_type = DataCard("PITCH TYPE", "-", color=VisualStyle.ACCENT_GOLD)
        self.card_velo = DataCard("VELOCITY", "-", color=VisualStyle.ACCENT_RED)
        self.card_spin = DataCard("SPIN RATE", "-", color=VisualStyle.ACCENT_MAGENTA)
        l.addWidget(self.card_type)
        l.addWidget(self.card_velo)
        l.addWidget(self.card_spin)
        return w

    def _create_hit_stats_grid(self):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0,5,0,5)
        l.setSpacing(10)
        self.card_exit = DataCard("EXIT VELO", "-", color=VisualStyle.ACCENT_CYAN)
        self.card_angle = DataCard("ANGLE", "-", color=VisualStyle.ACCENT_GREEN)
        self.card_dist = DataCard("DISTANCE", "-", color=VisualStyle.ACCENT_GOLD)
        l.addWidget(self.card_exit)
        l.addWidget(self.card_angle)
        l.addWidget(self.card_dist)
        return w
        
    def _create_log_area(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{ border: 1px solid {VisualStyle.BORDER_COLOR.name()}; background: {VisualStyle.BG_PANEL.name()}; border-radius: 4px; }}
            QScrollBar:vertical {{ width: 8px; background: {VisualStyle.BG_MAIN.name()}; }}
            QScrollBar::handle:vertical {{ background: #444; border-radius: 4px; }}
        """)
        self.log_container = QWidget()
        self.log_container.setStyleSheet("background: transparent;")
        self.log_layout = QVBoxLayout(self.log_container)
        self.log_layout.setAlignment(Qt.AlignTop)
        self.log_layout.setContentsMargins(15,10,15,10)
        scroll.setWidget(self.log_container)
        return scroll

    def _create_controls(self):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0,10,0,0)
        l.setSpacing(10)
        
        def style_btn(btn, bg_col, txt_col=QColor("#000")):
            btn.setFixedHeight(50)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_col.name()};
                    color: {txt_col.name()};
                    font-weight: 900;
                    font-size: 14px;
                    border: none;
                    border-radius: 4px;
                    letter-spacing: 1px;
                }}
                QPushButton:hover {{ background-color: {bg_col.lighter(110).name()}; }}
                QPushButton:disabled {{ background-color: {VisualStyle.BG_ELEVATED.name()}; color: {VisualStyle.TEXT_TERTIARY.name()}; }}
            """)

        self.btn_pitch = QPushButton("NEXT PITCH")
        style_btn(self.btn_pitch, VisualStyle.ACCENT_CYAN)
        self.btn_pitch.clicked.connect(self._on_pitch)
        
        self.btn_skip = QPushButton("SKIP")
        style_btn(self.btn_skip, VisualStyle.BG_ELEVATED, VisualStyle.TEXT_PRIMARY)
        self.btn_skip.clicked.connect(self._on_skip)
        
        l.addWidget(self.btn_pitch, stretch=2)
        l.addWidget(self.btn_skip, stretch=1)
        
        return w

    def _setup_timer(self):
        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self._on_pitch)

    # --- Logic Methods ---

    def start_game(self, home, away, date_str="2027-01-01"):
        self.date_str = date_str
        self._init_engine(home, away)
        self._update_display()
        self._log("=== PLAY BALL ===", True)

    def _init_engine(self, home, away):
        from live_game_engine import LiveGameEngine
        self.live_engine = LiveGameEngine(home, away)
        
        self.lbl_home.setText(home.name[:3].upper())
        self.lbl_away.setText(away.name[:3].upper())
        self.zone_widget.clear()
        self.field_widget.clear()
        self.need_zone_reset = False
        self.lbl_pitch_result.setText("PITCH RESULT: ---")
        self.lbl_pitch_result.setStyleSheet(f"color: {VisualStyle.TEXT_PRIMARY.name()}; font-size: 14px; font-weight: bold; padding: 5px; background: {VisualStyle.BG_ELEVATED.name()}; border-radius: 4px;")
        
        while self.log_layout.count():
            item = self.log_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _on_pitch(self):
        if self.is_animating or not self.live_engine or self.live_engine.is_game_over(): 
            return

        if self.need_zone_reset:
            self.zone_widget.clear()
            self.need_zone_reset = False

        # 現在の打者と打順を取得 (ログ用)
        current_batter, order_idx = self.live_engine.get_current_batter()
        current_inning = self.live_engine.state.inning
        is_top = self.live_engine.state.is_top
        team = self.live_engine.away_team if is_top else self.live_engine.home_team
        team_abbr = getattr(team, 'abbr', team.name[:3].upper())
        
        play_res, pitch, ball = self.live_engine.simulate_pitch()
        
        self.is_animating = True
        self.btn_pitch.setEnabled(False)
        self.btn_skip.setEnabled(False)
        
        # 判定用文字列
        res_val = play_res.value if hasattr(play_res, 'value') else str(play_res)
        
        if pitch:
            self.zone_widget.animate_pitch(pitch, res_val)
            self.card_velo.set_value(f"{int(pitch.velocity)} km/h")
            self.card_spin.set_value(f"{pitch.spin_rate} rpm")
            self.card_type.set_value(pitch.pitch_type)

            # ★追加: ピッチ結果ラベルを更新
            color = VisualStyle.get_result_color(res_val)
            self.lbl_pitch_result.setText(f"PITCH RESULT: {res_val.upper()}")
            self.lbl_pitch_result.setStyleSheet(f"color: {color.name()}; font-size: 14px; font-weight: bold; padding: 5px; background: {VisualStyle.BG_ELEVATED.name()}; border-radius: 4px;")
            
        if ball:
            runners = [
                self.live_engine.state.runner_1b is not None,
                self.live_engine.state.runner_2b is not None,
                self.live_engine.state.runner_3b is not None
            ]
            self.field_widget.animate_ball(ball, runners, res_val)
            self.card_exit.set_value(f"{int(ball.exit_velocity)} km/h")
            self.card_angle.set_value(f"{int(ball.launch_angle)}°")
            self.card_dist.set_value(f"{int(ball.distance)} m")
        else:
            self.card_exit.set_value("-")
            self.card_angle.set_value("-")
            self.card_dist.set_value("-")

        # ★修正: 打席終了のロジック (PitchResultが返ったが、カウントがリセットされている場合も含む)
        st = self.live_engine.state # 最新のステートを取得
        is_at_bat_end = False
        
        # 1. PlayResult (安打、アウト、犠打など) が返された場合
        if hasattr(play_res, 'name') and play_res.name in [
            'SINGLE', 'DOUBLE', 'TRIPLE', 'HOME_RUN', 'ERROR', 'SACRIFICE_FLY', 
            'SACRIFICE_BUNT', 'DOUBLE_PLAY', 'GROUNDOUT', 'FLYOUT', 'LINEOUT', 'POPUP_OUT', 'FIELDERS_CHOICE'
        ]:
            is_at_bat_end = True

        # 2. PitchResult であったが、LiveGameEngine側で打席が完了し、カウントがリセットされた場合 (四球、死球、三振)
        if not is_at_bat_end and st.balls == 0 and st.strikes == 0:
            if hasattr(play_res, 'name') and play_res.name in ['BALL', 'HIT_BY_PITCH', 'STRIKE_CALLED', 'STRIKE_SWINGING']:
                is_at_bat_end = True

        if is_at_bat_end:
            # 打者名と打順のフォールバック処理を追加
            batter_name = getattr(current_batter, 'name', 'UNKNOWN')
            batter_order = str(order_idx + 1)
            
            # ログ出力用の結果文字列調整
            if play_res.name == 'BALL' and hasattr(current_batter, 'runner_1b') and current_batter.runner_1b: res_val = "四球" # 四球で出塁
            elif play_res.name == 'HIT_BY_PITCH': res_val = "死球"
            elif play_res.name in ['STRIKE_CALLED', 'STRIKE_SWINGING'] and is_at_bat_end: res_val = "三振" # カウントリセットされたストライクは三振
            
            log_prefix = f"[{current_inning}回{'表' if is_top else '裏'} | {batter_order}番 {team_abbr} {batter_name}] "
            self._log(log_prefix + f"【{res_val}】", True)
            self.need_zone_reset = True

    def _on_animation_step_finished(self):
        if self.zone_widget.is_animating or self.field_widget.is_animating:
            return

        self.is_animating = False
        self.btn_pitch.setEnabled(True)
        self.btn_skip.setEnabled(True)
        
        self._update_display()
        
        if self.live_engine.is_game_over():
            self._finish()

    def _on_skip(self):
        if not self.live_engine or self.is_animating: return
        while not self.live_engine.is_game_over():
            self.live_engine.simulate_pitch()
        
        self.zone_widget.clear()
        self.field_widget.clear()
        self._update_display()
        self._finish()

    def _update_display(self):
        st = self.live_engine.state
        self.lbl_home_score.setText(str(st.home_score))
        self.lbl_away_score.setText(str(st.away_score))
        self.lbl_inning.setText(f"{st.inning} {'TOP' if st.is_top else 'BOT'}")
        
        for i, d in enumerate(self.dots_b):
            d.setStyleSheet(f"color: {VisualStyle.COLOR_BALL.name() if st.balls > i else VisualStyle.BG_ELEVATED.name()}; font-size: 10px;")
        for i, d in enumerate(self.dots_s):
            d.setStyleSheet(f"color: {VisualStyle.COLOR_STRIKE.name() if st.strikes > i else VisualStyle.BG_ELEVATED.name()}; font-size: 10px;")
        for i, d in enumerate(self.dots_o):
            d.setStyleSheet(f"color: {VisualStyle.COLOR_OUT.name() if st.outs > i else VisualStyle.BG_ELEVATED.name()}; font-size: 10px;")

        b, _ = self.live_engine.get_current_batter()
        p, _ = self.live_engine.get_current_pitcher()
        
        if b:
            self.lbl_b_name.setText(b.name)
            self.lbl_b_hand.setText(f"{b.bats}投{b.throws}打")
            avg = b.record.batting_average
            ops = b.record.ops
            self.lbl_b_avg.setText(f"AVG: {avg:.3f}")
            self.lbl_b_ops.setText(f"OPS: {ops:.3f}")
            self.lbl_b_hr_rbi.setText(f"HR: {b.record.home_runs}  RBI: {b.record.rbis}")
            
            con = get_rank(b.stats.contact)
            pow_ = get_rank(b.stats.power)
            spd = get_rank(b.stats.speed)
            self.lbl_b_abil.setText(f"Con:{con} Pow:{pow_} Spd:{spd}")
            
        if p:
            self.lbl_p_name.setText(p.name)
            stam = st.current_pitcher_stamina()
            self.pb_stamina.setValue(int(stam))
            era = p.record.era
            self.lbl_p_era.setText(f"ERA: {era:.2f}")
            self.lbl_p_wl.setText(f"{p.record.wins}W-{p.record.losses}L")
            self.lbl_p_so.setText(f"SO: {p.record.strikeouts_pitched}")
            
            stf = get_rank(p.stats.stuff)
            ctl = get_rank(p.stats.control)
            sta = get_rank(p.stats.stamina)
            self.lbl_p_abil.setText(f"Stf:{stf} Ctl:{ctl} Sta:{sta}")

        runners = [
            st.runner_1b is not None,
            st.runner_2b is not None,
            st.runner_3b is not None
        ]
        if not self.is_animating:
            self.field_widget.set_runners_only(runners)

    def _log(self, txt, highlight=False):
        l = QLabel(txt)
        col = VisualStyle.COLOR_STRIKE.name() if highlight else VisualStyle.TEXT_SECONDARY.name()
        l.setStyleSheet(f"color: {col}; font-family: '{VisualStyle.FONT_UI}'; font-size: 12px; font-weight: bold;")
        self.log_layout.insertWidget(0, l)

    def _finish(self):
        self.sim_timer.stop()
        if self.live_engine:
            self.live_engine.finalize_game_stats(self.date_str)
            
        self._log("=== GAME SET ===", True)
        res = {
            "home_team": self.live_engine.home_team,
            "away_team": self.live_engine.away_team,
            "home_score": self.live_engine.state.home_score,
            "away_score": self.live_engine.state.away_score,
            "winner": self.live_engine.get_winner()
        }
        self.game_finished.emit(res)