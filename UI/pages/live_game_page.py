# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Live Game Page (Savant Style)
High-End Data Visualization & Broadcast UI
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout, QGraphicsDropShadowEffect,
    QDialog, QSizePolicy, QProgressBar, QSplitter
)
from PySide6.QtCore import Qt, Signal, QTimer, QPointF, QRectF, QSize
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
    # Colors derived from theme but specialized for data viz
    BG_MAIN = QColor("#0b0c10")
    BG_PANEL = QColor("#1e2126")
    ACCENT_CYAN = QColor("#00e5ff")
    ACCENT_MAGENTA = QColor("#d500f9")
    ACCENT_GOLD = QColor("#ffd700")
    ACCENT_RED = QColor("#ff1744")
    ACCENT_GREEN = QColor("#00e676")
    
    # Fonts
    FONT_NUM = "Roboto Mono"
    FONT_UI = "Segoe UI"

    @staticmethod
    def get_pitch_color(pitch_type: str):
        mapping = {
            "ストレート": QColor("#ff4081"),    # Pink (4-Seam)
            "ツーシーム": QColor("#e040fb"),    # Purple
            "カットボール": QColor("#7c4dff"),  # Deep Purple
            "スライダー": QColor("#ffd740"),    # Amber
            "カーブ": QColor("#00e5ff"),        # Cyan
            "フォーク": QColor("#69f0ae"),      # Green
            "チェンジアップ": QColor("#1de9b6"),# Teal
            "シュート": QColor("#ff6e40"),      # Deep Orange
            "シンカー": QColor("#40c4ff"),      # Light Blue
            "スプリット": QColor("#00b0ff"),    # Blue
        }
        return mapping.get(pitch_type, QColor("#999999"))

# ========================================
# 3D 投球軌道 & ストライクゾーン (Gameday Style)
# ========================================
class GamedayStrikeZone(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(300, 350)
        self.pitches = []  # (PitchData, result_str, color)
        self.last_pitch = None

    def add_pitch(self, pitch: PitchData, result: str):
        color = VisualStyle.get_pitch_color(pitch.pitch_type)
        self.pitches.append((pitch, result, color))
        if len(self.pitches) > 10:  # 最新10球のみ表示
            self.pitches.pop(0)
        self.last_pitch = pitch
        self.update()

    def clear(self):
        self.pitches = []
        self.last_pitch = None
        self.update()

    def project_3d(self, x, y, z, width, height):
        """
        簡易パースペクティブ投影
        x: 横 (Home plate center=0)
        y: 奥行き (Home plate=0, Pitcher mound=18.44)
        z: 高さ (Ground=0)
        """
        scale = min(width, height) * 0.85
        
        # 視点設定 (捕手後方上空からの視点)
        cam_dist = 4.0  # カメラ距離
        
        # 奥行きによるスケール補正
        # y=0 (ホームベース) が最大、y=18.44 (マウンド) が最小
        depth_factor = cam_dist / (cam_dist + y/12.0) 
        
        screen_x = width/2 + (x * scale * 0.6 * depth_factor)
        # z=0が画面下部に来るように調整
        screen_y = height * 0.90 - (z * scale * 0.6 * depth_factor)
        
        return QPointF(screen_x, screen_y), depth_factor

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        # 背景 (ダーク)
        painter.fillRect(self.rect(), VisualStyle.BG_PANEL)
        
        # --- ホームベース周辺 ---
        hb_center, _ = self.project_3d(0, 0, 0, w, h)
        
        # ホームプレート (五角形)
        hp_scale = 0.43 # 幅43cm
        hp_pts = [
            self.project_3d(0, 0, 0, w, h)[0], # 先端
            self.project_3d(hp_scale/2, 0.2, 0, w, h)[0],
            self.project_3d(hp_scale/2, 0.4, 0, w, h)[0],
            self.project_3d(-hp_scale/2, 0.4, 0, w, h)[0],
            self.project_3d(-hp_scale/2, 0.2, 0, w, h)[0],
        ]
        painter.setBrush(QColor(220, 220, 220))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(QPolygonF(hp_pts))

        # バッターボックス (簡易ライン)
        painter.setPen(QPen(QColor(255, 255, 255, 50), 2))
        l_box_tl, _ = self.project_3d(-1.2, 0, 0, w, h)
        l_box_bl, _ = self.project_3d(-1.2, 1.5, 0, w, h)
        painter.drawLine(l_box_tl, l_box_bl)
        
        r_box_tl, _ = self.project_3d(1.2, 0, 0, w, h)
        r_box_bl, _ = self.project_3d(1.2, 1.5, 0, w, h)
        painter.drawLine(r_box_tl, r_box_bl)

        # --- 3D ストライクゾーン枠 (透明ボックス) ---
        zone_top = 1.05  # 一般的な上限 (m)
        zone_btm = 0.45  # 一般的な下限 (m)
        zone_w = 0.216   # 幅の半分 (m)
        
        # 前面 (ホームベース上)
        tl_f, _ = self.project_3d(-zone_w, 0, zone_top, w, h)
        tr_f, _ = self.project_3d(zone_w, 0, zone_top, w, h)
        bl_f, _ = self.project_3d(-zone_w, 0, zone_btm, w, h)
        br_f, _ = self.project_3d(zone_w, 0, zone_btm, w, h)
        
        # 背面 (少し奥) - 立体感を出すためのダミー深度
        back_depth = 0.5
        tl_b, _ = self.project_3d(-zone_w, back_depth, zone_top, w, h)
        tr_b, _ = self.project_3d(zone_w, back_depth, zone_top, w, h)
        bl_b, _ = self.project_3d(-zone_w, back_depth, zone_btm, w, h)
        br_b, _ = self.project_3d(zone_w, back_depth, zone_btm, w, h)
        
        # ワイヤーフレーム
        painter.setPen(QPen(QColor(255, 255, 255, 40), 1, Qt.DotLine))
        painter.drawLine(tl_f, tl_b); painter.drawLine(tr_f, tr_b)
        painter.drawLine(bl_f, bl_b); painter.drawLine(br_f, br_b)
        painter.drawLine(tl_b, tr_b); painter.drawLine(tr_b, br_b)
        painter.drawLine(br_b, bl_b); painter.drawLine(bl_b, tl_b)

        # 前面枠 (実線・強調・ストライクゾーン本体)
        painter.setPen(QPen(QColor(255, 255, 255, 180), 2))
        painter.drawRect(QRectF(tl_f, br_f))

        # --- 投球の描画 ---
        # 過去の投球 (薄く、点のみ)
        for i, (pitch, result, color) in enumerate(self.pitches):
            if pitch == self.last_pitch: continue
            
            # 通過点
            pt, _ = self.project_3d(pitch.location.x, 0, pitch.location.z, w, h)
            
            # 透過円
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(color.red(), color.green(), color.blue(), 100))
            painter.drawEllipse(pt, 6, 6)
            
            # 球順番号
            painter.setPen(QColor(255,255,255,180))
            painter.setFont(QFont(VisualStyle.FONT_NUM, 8))
            painter.drawText(QRectF(pt.x()-10, pt.y()-10, 20, 20), Qt.AlignCenter, str(i+1))

        # 最新の投球 (軌道付きで強調)
        if self.last_pitch:
            pitch = self.last_pitch
            color = VisualStyle.get_pitch_color(pitch.pitch_type)
            
            # 軌道 (Trajectory)
            path = QPainterPath()
            if pitch.trajectory:
                # 始点
                start_pt, _ = self.project_3d(pitch.trajectory[0][0], pitch.trajectory[0][1], pitch.trajectory[0][2], w, h)
                path.moveTo(start_pt)
                
                # パス生成
                for pos in pitch.trajectory[1:]:
                     # マウンド(y=18.44)からホーム(y=0)へ
                     pt, df = self.project_3d(pos[0], pos[1], pos[2], w, h)
                     path.lineTo(pt)
            
            # 軌道の影 (床面投影) - 深さを感じる要素
            shadow_path = QPainterPath()
            if pitch.trajectory:
                s_start, _ = self.project_3d(pitch.trajectory[0][0], pitch.trajectory[0][1], 0, w, h)
                shadow_path.moveTo(s_start)
                for pos in pitch.trajectory[1:]:
                     pt, _ = self.project_3d(pos[0], pos[1], 0, w, h)
                     shadow_path.lineTo(pt)
            
            # 影の描画
            painter.setPen(QPen(QColor(0,0,0,80), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(shadow_path)

            # 軌道の描画 (グラデーションをつけるとより良いが、単色で視認性重視)
            painter.setPen(QPen(color, 4))
            painter.drawPath(path)
            
            # 到達点 (ボール)
            final_pt, _ = self.project_3d(pitch.location.x, 0, pitch.location.z, w, h)
            
            # ボール本体
            painter.setPen(QPen(Qt.white, 1))
            painter.setBrush(color)
            painter.drawEllipse(final_pt, 10, 10)
            
            # 詳細テキスト (球速・球種)
            info_rect = QRectF(final_pt.x() + 15, final_pt.y() - 25, 120, 50)
            
            # 背景ボックス
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, 150))
            painter.drawRoundedRect(info_rect, 4, 4)
            
            painter.setPen(Qt.white)
            painter.setFont(QFont(VisualStyle.FONT_NUM, 10, QFont.Bold))
            painter.drawText(info_rect.adjusted(5,0,0,0), Qt.AlignLeft|Qt.AlignVCenter, f"{int(pitch.velocity)}km\n{pitch.pitch_type}")

# ========================================
# フィールドビュー (打球・守備)
# ========================================
class BroadcastField(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(300, 300)
        self.batted_ball = None
        self.runners = [False, False, False] # 1B, 2B, 3B

    def set_data(self, ball: BattedBallData, runners):
        self.batted_ball = ball
        self.runners = runners
        self.update()

    def clear(self):
        self.batted_ball = None
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h * 0.85 # ホームベース位置
        
        # 背景
        painter.fillRect(self.rect(), VisualStyle.BG_PANEL)
        
        # --- フィールド描画 (スケーリング) ---
        scale = min(w, h) / 130.0 # 130mスケール
        
        # フェアグラウンド (扇形)
        field_path = QPainterPath()
        field_path.moveTo(cx, cy)
        field_path.arcTo(cx - 122*scale, cy - 122*scale, 244*scale, 244*scale, 45, 90) # センター122m
        field_path.closeSubpath()
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#263238")) # 芝生色 (ダーク)
        painter.drawPath(field_path)
        
        # 内野 (ダイヤモンド)
        base_dist = 27.43 * scale # 約30m
        diamond = QPolygonF()
        diamond.append(QPointF(cx, cy)) # 本塁
        diamond.append(QPointF(cx + base_dist, cy - base_dist)) # 1塁
        diamond.append(QPointF(cx, cy - base_dist*2)) # 2塁
        diamond.append(QPointF(cx - base_dist, cy - base_dist)) # 3塁
        
        painter.setBrush(QColor("#3e2723")) # 土色
        painter.setPen(QPen(QColor(255,255,255,50), 1))
        painter.drawPolygon(diamond)
        
        # ベース & ランナー
        base_size = 7
        bases = [
            (cx + base_dist, cy - base_dist), # 1st
            (cx, cy - base_dist*2),           # 2nd
            (cx - base_dist, cy - base_dist)  # 3rd
        ]
        
        for i, (bx, by) in enumerate(bases):
            is_occ = self.runners[i]
            col = VisualStyle.ACCENT_GOLD if is_occ else QColor("#555")
            painter.setBrush(col)
            painter.setPen(Qt.white if is_occ else Qt.NoPen)
            painter.drawPolygon(QPolygonF([
                QPointF(bx, by-base_size), QPointF(bx+base_size, by),
                QPointF(bx, by+base_size), QPointF(bx-base_size, by)
            ]))

        # --- 打球描画 ---
        if self.batted_ball:
            # 極座標 -> 直交座標
            dist_px = self.batted_ball.distance * scale
            angle_rad = math.radians(self.batted_ball.spray_angle)
            
            # 画面上の座標 (y軸は上向き負、x軸は右向き正)
            # spray_angle: 0=Center, Positive=Right, Negative=Left
            lx = cx + dist_px * math.sin(angle_rad)
            ly = cy - dist_px * math.cos(angle_rad)
            
            # 軌道線 (放物線の射影)
            traj_path = QPainterPath()
            traj_path.moveTo(cx, cy)
            
            # 制御点 (頂点) を簡易計算してベジェ曲線にする
            mid_x = (cx + lx) / 2
            mid_y = (cy + ly) / 2
            # 滞空時間が長いほど頂点を高くする
            h_factor = self.batted_ball.hang_time * 20 * scale
            ctrl_pt = QPointF(mid_x, mid_y - h_factor)
            
            traj_path.quadTo(ctrl_pt, QPointF(lx, ly))
            
            # 描画
            color = VisualStyle.ACCENT_CYAN
            if "HOME_RUN" in str(self.batted_ball.hit_type): color = VisualStyle.ACCENT_MAGENTA
            elif "OUT" in str(self.batted_ball.hit_type): color = VisualStyle.ACCENT_RED
            
            painter.setPen(QPen(color, 2, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(traj_path)
            
            # 落下点
            painter.setBrush(color)
            painter.setPen(Qt.white)
            painter.drawEllipse(QPointF(lx, ly), 5, 5)
            
            # テキスト表示 (飛距離)
            painter.setFont(QFont(VisualStyle.FONT_NUM, 9))
            painter.setPen(Qt.white)
            label = f"{int(self.batted_ball.distance)}m"
            painter.drawText(lx + 8, ly, label)

# ========================================
# データカード (各種スタッツ表示用)
# ========================================
class DataCard(QFrame):
    def __init__(self, title, value="-", parent=None, color=VisualStyle.ACCENT_CYAN):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(30, 33, 38, 200);
                border-left: 3px solid {color.name()};
                border-radius: 2px;
            }}
        """)
        l = QVBoxLayout(self)
        l.setContentsMargins(8, 5, 8, 5)
        l.setSpacing(2)
        
        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("color: #888; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        
        self.lbl_value = QLabel(str(value))
        self.lbl_value.setStyleSheet(f"color: white; font-family: '{VisualStyle.FONT_NUM}'; font-size: 16px; font-weight: bold;")
        
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
        self.date_str = "2027-01-01"
        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        # メインレイアウト
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. ヘッダー (スコアボード)
        self.scoreboard_widget = self._create_scoreboard()
        main_layout.addWidget(self.scoreboard_widget)

        # 2. メインコンテンツ (左右分割)
        content_area = QWidget()
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)
        
        # --- LEFT: Matchup & Strike Zone ---
        left_panel = QWidget()
        lp_layout = QVBoxLayout(left_panel)
        lp_layout.setContentsMargins(0,0,0,0)
        lp_layout.setSpacing(10)
        
        # Matchup Card (Batter vs Pitcher)
        self.matchup_card = self._create_matchup_card()
        lp_layout.addWidget(self.matchup_card)
        
        # 3D Strike Zone
        self.zone_widget = GamedayStrikeZone()
        lp_layout.addWidget(self.zone_widget, stretch=1)
        
        # Pitch Stats Grid
        self.pitch_stats_grid = self._create_pitch_stats_grid()
        lp_layout.addWidget(self.pitch_stats_grid)
        
        content_layout.addWidget(left_panel, stretch=5)
        
        # --- RIGHT: Field & Log ---
        right_panel = QWidget()
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(0,0,0,0)
        rp_layout.setSpacing(10)
        
        # Field View
        self.field_widget = BroadcastField()
        rp_layout.addWidget(self.field_widget, stretch=4)
        
        # Hit Stats Grid
        self.hit_stats_grid = self._create_hit_stats_grid()
        rp_layout.addWidget(self.hit_stats_grid)
        
        # Game Log
        self.log_widget = self._create_log_area()
        rp_layout.addWidget(self.log_widget, stretch=3)

        # Controls
        self.controls_widget = self._create_controls()
        rp_layout.addWidget(self.controls_widget)
        
        content_layout.addWidget(right_panel, stretch=4)
        
        main_layout.addWidget(content_area)

    def _create_scoreboard(self):
        w = QFrame()
        w.setFixedHeight(70)
        w.setStyleSheet(f"background-color: {VisualStyle.BG_MAIN.name()}; border-bottom: 1px solid #333;")
        
        l = QHBoxLayout(w)
        l.setContentsMargins(20, 0, 20, 0)
        
        # Away Team
        self.lbl_away = QLabel("AWAY")
        self.lbl_away.setStyleSheet("font-size: 20px; font-weight: 900; color: #ccc;")
        self.lbl_away_score = QLabel("0")
        self.lbl_away_score.setStyleSheet(f"font-size: 36px; font-weight: 900; color: {VisualStyle.ACCENT_GOLD.name()};")
        
        # Inning Info
        self.lbl_inning = QLabel("1st TOP")
        self.lbl_inning.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {VisualStyle.ACCENT_CYAN.name()}; margin: 0 20px;")
        
        # BSO
        bso_frame = QFrame()
        bl = QVBoxLayout(bso_frame)
        bl.setSpacing(2); bl.setContentsMargins(0,15,0,15)
        
        def mk_dots(label, col):
            r = QHBoxLayout()
            r.setSpacing(4)
            r.addWidget(QLabel(label, styleSheet="font-weight:bold; font-size:10px; color:#666; width:10px;"))
            dots = []
            for _ in range(3 if label=="B" else 2):
                d = QLabel("●")
                d.setStyleSheet("color: #333; font-size: 8px;")
                r.addWidget(d)
                dots.append(d)
            r.addStretch()
            bl.addLayout(r)
            return dots

        self.dots_b = mk_dots("B", VisualStyle.ACCENT_GREEN)
        self.dots_s = mk_dots("S", VisualStyle.ACCENT_GOLD)
        self.dots_o = mk_dots("O", VisualStyle.ACCENT_RED)
        
        # Home Team
        self.lbl_home_score = QLabel("0")
        self.lbl_home_score.setStyleSheet(f"font-size: 36px; font-weight: 900; color: {VisualStyle.ACCENT_GOLD.name()};")
        self.lbl_home = QLabel("HOME")
        self.lbl_home.setStyleSheet("font-size: 20px; font-weight: 900; color: white;")
        
        l.addWidget(self.lbl_away)
        l.addWidget(self.lbl_away_score)
        l.addStretch()
        l.addWidget(self.lbl_inning)
        l.addWidget(bso_frame)
        l.addStretch()
        l.addWidget(self.lbl_home_score)
        l.addWidget(self.lbl_home)
        
        return w

    def _create_matchup_card(self):
        f = QFrame()
        f.setStyleSheet("background: transparent;")
        l = QHBoxLayout(f)
        l.setContentsMargins(0,0,0,0)
        
        # Pitcher Info
        p_box = QFrame()
        p_box.setStyleSheet(f"background: {VisualStyle.BG_PANEL.name()}; border-radius: 2px; border-left: 4px solid {VisualStyle.ACCENT_RED.name()};")
        pl = QGridLayout(p_box)
        pl.addWidget(QLabel("PITCHER", styleSheet="color:#888; font-size:9px; letter-spacing:1px;"), 0, 0)
        self.lbl_p_name = QLabel("---", styleSheet="color:white; font-weight:bold; font-size:14px;")
        pl.addWidget(self.lbl_p_name, 1, 0)
        self.pb_stamina = QProgressBar()
        self.pb_stamina.setFixedHeight(4)
        self.pb_stamina.setStyleSheet(f"QProgressBar{{background:#333; border:none;}} QProgressBar::chunk{{background:{VisualStyle.ACCENT_RED.name()};}}")
        pl.addWidget(self.pb_stamina, 2, 0)
        self.lbl_p_stats = QLabel("ERA: -.--", styleSheet=f"color:#aaa; font-size:10px; font-family:'{VisualStyle.FONT_NUM}';")
        pl.addWidget(self.lbl_p_stats, 3, 0)
        l.addWidget(p_box, stretch=1)
        
        # VS
        l.addWidget(QLabel("VS", styleSheet="color:#555; font-style:italic; font-weight:bold;"), alignment=Qt.AlignCenter)
        
        # Batter Info
        b_box = QFrame()
        b_box.setStyleSheet(f"background: {VisualStyle.BG_PANEL.name()}; border-radius: 2px; border-left: 4px solid {VisualStyle.ACCENT_CYAN.name()};")
        bl = QGridLayout(b_box)
        bl.addWidget(QLabel("BATTER", styleSheet="color:#888; font-size:9px; letter-spacing:1px;"), 0, 0)
        self.lbl_b_name = QLabel("---", styleSheet="color:white; font-weight:bold; font-size:14px;")
        bl.addWidget(self.lbl_b_name, 1, 0)
        self.lbl_b_detail = QLabel("L / R", styleSheet="color:#aaa; font-size:10px;")
        bl.addWidget(self.lbl_b_detail, 2, 0)
        self.lbl_b_stats = QLabel("AVG: .--- HR: -", styleSheet=f"color:#aaa; font-size:10px; font-family:'{VisualStyle.FONT_NUM}';")
        bl.addWidget(self.lbl_b_stats, 3, 0)
        l.addWidget(b_box, stretch=1)
        
        return f

    def _create_pitch_stats_grid(self):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0,5,0,5)
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
            QScrollArea {{ border: 1px solid #333; background: {VisualStyle.BG_PANEL.name()}; }}
            QScrollBar:vertical {{ width: 8px; background: #111; }}
            QScrollBar::handle:vertical {{ background: #444; border-radius: 4px; }}
        """)
        self.log_container = QWidget()
        self.log_container.setStyleSheet("background: transparent;")
        self.log_layout = QVBoxLayout(self.log_container)
        self.log_layout.setAlignment(Qt.AlignTop)
        self.log_layout.setContentsMargins(10,5,10,5)
        scroll.setWidget(self.log_container)
        return scroll

    def _create_controls(self):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(0,5,0,0)
        
        self.btn_pitch = QPushButton("NEXT PITCH")
        self.btn_pitch.setFixedHeight(45)
        self.btn_pitch.setStyleSheet(f"""
            QPushButton {{
                background: {VisualStyle.ACCENT_CYAN.name()};
                color: #000;
                font-weight: bold;
                font-size: 14px;
                border: none;
                border-radius: 2px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{ background: #4dd0e1; }}
        """)
        self.btn_pitch.clicked.connect(self._on_pitch)
        
        self.btn_skip = QPushButton("SKIP")
        self.btn_skip.setFixedHeight(45)
        self.btn_skip.setStyleSheet("""
            QPushButton {
                background: #333; color: #fff; font-weight: bold; border: 1px solid #555;
            }
            QPushButton:hover { background: #444; }
        """)
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
        
        # Clear logs
        while self.log_layout.count():
            item = self.log_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _on_pitch(self):
        if not self.live_engine or self.live_engine.is_game_over(): return

        # Simulation
        play_res, pitch, ball = self.live_engine.simulate_pitch()
        
        # 1. Update Strike Zone
        if pitch:
            res_str = play_res.value if hasattr(play_res, 'value') else str(play_res)
            self.zone_widget.add_pitch(pitch, res_str)
            
            # Update Pitch Stats
            self.card_velo.set_value(f"{int(pitch.velocity)} km/h")
            self.card_spin.set_value(f"{pitch.spin_rate} rpm")
            self.card_type.set_value(pitch.pitch_type)
            
            self._log(f"{pitch.pitch_type} ({int(pitch.velocity)}km) -> {res_str}")

        # 2. Update Field & Hit Stats
        if ball:
            runners = [
                self.live_engine.state.runner_1b is not None,
                self.live_engine.state.runner_2b is not None,
                self.live_engine.state.runner_3b is not None
            ]
            self.field_widget.set_data(ball, runners)
            
            self.card_exit.set_value(f"{int(ball.exit_velocity)} km/h")
            self.card_angle.set_value(f"{int(ball.launch_angle)}°")
            self.card_dist.set_value(f"{int(ball.distance)} m")
            
            # ヒットやアウトなら少し待ってクリア
            if "安打" in str(play_res) or "本塁打" in str(play_res):
                 self._log(f"!!! {play_res.value} !!!", True)
        else:
            # 打球がない場合はヒットスタッツをリセット
            self.card_exit.set_value("-")
            self.card_angle.set_value("-")
            self.card_dist.set_value("-")

        # 3. Update Scoreboard & Matchup
        self._update_display()

        if self.live_engine.is_game_over():
            self._finish()

    def _on_skip(self):
        # 高速進行
        if not self.live_engine: return
        while not self.live_engine.is_game_over():
            self.live_engine.simulate_pitch()
        self._update_display()
        self._finish()

    def _update_display(self):
        st = self.live_engine.state
        self.lbl_home_score.setText(str(st.home_score))
        self.lbl_away_score.setText(str(st.away_score))
        self.lbl_inning.setText(f"{st.inning} {'TOP' if st.is_top else 'BOT'}")
        
        # Update BSO
        for i, d in enumerate(self.dots_b):
            d.setStyleSheet(f"color: {VisualStyle.ACCENT_GREEN.name() if st.balls > i else '#333'}; font-size: 8px;")
        for i, d in enumerate(self.dots_s):
            d.setStyleSheet(f"color: {VisualStyle.ACCENT_GOLD.name() if st.strikes > i else '#333'}; font-size: 8px;")
        for i, d in enumerate(self.dots_o):
            d.setStyleSheet(f"color: {VisualStyle.ACCENT_RED.name() if st.outs > i else '#333'}; font-size: 8px;")

        # Update Matchup
        b, _ = self.live_engine.get_current_batter()
        p, _ = self.live_engine.get_current_pitcher()
        
        if b:
            self.lbl_b_name.setText(b.name)
            self.lbl_b_detail.setText(f"{b.bats}投{b.throws}打")
            
            rank_p = get_rank(getattr(b.stats, 'power', 50))
            rank_c = get_rank(getattr(b.stats, 'contact', 50))
            self.lbl_b_stats.setText(f"Pow:{rank_p} Con:{rank_c}")
            
        if p:
            self.lbl_p_name.setText(p.name)
            stam = st.current_pitcher_stamina()
            self.pb_stamina.setValue(int(stam))
            self.lbl_p_stats.setText(f"Stamina: {int(stam)}%")

        # Runners (Update even if no hit, e.g. steal/walk)
        runners = [
            st.runner_1b is not None,
            st.runner_2b is not None,
            st.runner_3b is not None
        ]
        if not self.field_widget.batted_ball: # 打球表示中でなければランナーだけ更新
            self.field_widget.runners = runners
            self.field_widget.update()

    def _log(self, txt, highlight=False):
        l = QLabel(txt)
        col = VisualStyle.ACCENT_GOLD.name() if highlight else "#ccc"
        l.setStyleSheet(f"color: {col}; font-family: '{VisualStyle.FONT_NUM}'; font-size: 11px;")
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