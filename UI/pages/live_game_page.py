# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Live Game Page
Premium Digital Stadium UI with AI & Management
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout, QGraphicsDropShadowEffect,
    QDialog, QSizePolicy, QGraphicsOpacityEffect, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QTimer, QPointF, QRectF, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QPainterPath, 
    QLinearGradient, QPolygonF
)

import sys
import os
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from UI.theme import get_theme
from live_game_engine import PitchType, PlayResult, PitchResult, BattedBallType, get_rank

# ========================================
# デザイン定数
# ========================================
COLORS = {
    "bg": QColor("#121212"),
    "field_fair": QColor("#1e1e1e"),
    "field_foul": QColor("#181818"),
    "line": QColor("#444444"),
    "text_main": QColor("#ffffff"),
    "text_sub": QColor("#888888"),
    "accent": QColor("#00e5ff"),   # Cyan
    "accent2": QColor("#ffd700"),  # Gold
    "btn_bg": QColor("#263238"),
    
    # Result Colors
    "strike": QColor("#ffd700"),   # Yellow
    "ball":   QColor("#00e676"),   # Green
    "hit":    QColor("#2979ff"),   # Blue
    "out":    QColor("#ff1744"),   # Red
}

FONTS = {
    "main": "Segoe UI",
    "digit": "Roboto Mono", 
    "impact": "Impact"
}

# ========================================
# 試合モード選択ダイアログ
# ========================================
class GameModeDialog(QDialog):
    mode_selected = Signal(str)

    def __init__(self, home_team, away_team, parent=None):
        super().__init__(parent)
        self.selected_mode = None
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(500, 320)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a1a;
                border: 1px solid #333;
                border-radius: 4px;
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 150))
        frame.setGraphicsEffect(shadow)
        
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(40, 30, 40, 30)
        fl.setSpacing(20)
        
        # Title
        title = QLabel("GAME START")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white; letter-spacing: 4px;")
        fl.addWidget(title)
        
        # Matchup
        m_layout = QHBoxLayout()
        def t_lbl(t): return QLabel(t, styleSheet="font-size: 16px; color: #ccc; font-weight: bold;")
        m_layout.addWidget(t_lbl(away_team.name), alignment=Qt.AlignCenter)
        m_layout.addWidget(QLabel("vs", styleSheet="color: #666; margin: 0 15px; font-style: italic;"), alignment=Qt.AlignCenter)
        m_layout.addWidget(t_lbl(home_team.name), alignment=Qt.AlignCenter)
        fl.addLayout(m_layout)
        
        fl.addSpacing(10)
        
        # Buttons
        b_layout = QHBoxLayout()
        b_layout.setSpacing(15)
        
        def mkbtn(txt, mode, col):
            b = QPushButton(txt)
            b.setCursor(Qt.PointingHandCursor)
            b.setFixedHeight(45)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; border: 1px solid #555; color: #eee; font-weight: bold; font-size: 12px;
                }}
                QPushButton:hover {{
                    background: {col}; border-color: {col}; color: #111;
                }}
            """)
            b.clicked.connect(lambda: self._sel(mode))
            return b
            
        b_layout.addWidget(mkbtn("RESULT ONLY", "skip", "#90caf9"))
        b_layout.addWidget(mkbtn("MANAGE MODE", "manage", "#ffd700"))
        fl.addLayout(b_layout)
        
        layout.addWidget(frame)

    def _sel(self, m):
        self.selected_mode = m
        self.mode_selected.emit(m)
        self.accept()


# ========================================
# ストライクゾーン
# ========================================
class StrikeZoneWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.pitches = [] 
        self.current_pitch = None

    def add_pitch(self, pitch_data, result_type: str, is_hit: bool, is_out: bool, is_strikeout: bool, pitcher_hand: str = "Right"):
        if not pitch_data: return
        
        # 色決定
        if is_hit: color = COLORS["hit"]
        elif is_strikeout: color = COLORS["strike"] 
        elif is_out: color = COLORS["out"]    
        elif pitch_data.location.is_strike: color = COLORS["strike"]
        else: color = COLORS["ball"]
            
        self.pitches.append((pitch_data, color, pitcher_hand))
        if len(self.pitches) > 15: self.pitches.pop(0)
        self.current_pitch = (pitch_data, color, pitcher_hand)
        self.update()

    def clear_pitches(self):
        self.pitches.clear()
        self.current_pitch = None
        self.update()

    def _get_shape_type(self, ptype, hand):
        straight = ["ストレート", "ツーシーム", "カットボール"]
        breaking = ["スライダー", "カーブ"]
        reverse = ["シュート", "シンカー"]
        drop = ["フォーク", "スプリット", "チェンジアップ"]
        
        if ptype in straight: return 0
        if ptype in drop: return 3
        
        is_lefty = (hand == "Left")
        if ptype in breaking: return 2 if is_lefty else 1
        if ptype in reverse: return 1 if is_lefty else 2
        return 0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        
        zone_w = min(w * 0.8, h * 0.6)
        zone_h = zone_w * 1.35
        cx, cy = w / 2, h / 2
        zone_rect = QRectF(cx - zone_w/2, cy - zone_h/2, zone_w, zone_h)
        
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        cw, ch = zone_w/3, zone_h/3
        for i in range(1, 3):
            painter.drawLine(zone_rect.left()+cw*i, zone_rect.top(), zone_rect.left()+cw*i, zone_rect.bottom())
            painter.drawLine(zone_rect.left(), zone_rect.top()+ch*i, zone_rect.right(), zone_rect.top()+ch*i)
            
        painter.setPen(QPen(QColor(255, 255, 255, 150), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(zone_rect)
        
        def draw_mark(data_tuple, is_latest):
            pitch, color, hand = data_tuple
            if not pitch or not pitch.location: return
            
            nx = pitch.location.x / 0.216
            ny = (pitch.location.z - 0.75) / 0.28
            px = cx + nx * (zone_w / 2)
            py = cy - ny * (zone_h / 2)
            
            px = max(zone_rect.left()-30, min(zone_rect.right()+30, px))
            py = max(zone_rect.top()-30, min(zone_rect.bottom()+30, py))
            
            shape_id = self._get_shape_type(pitch.pitch_type, hand)
            size = 14 if is_latest else 10
            h_sz = size / 2
            
            painter.setPen(Qt.NoPen)
            painter.setBrush(color)
            center = QPointF(px, py)
            
            if shape_id == 0: painter.drawEllipse(center, h_sz, h_sz)
            elif shape_id == 1: # Left Tri
                painter.drawPolygon(QPolygonF([QPointF(px-h_sz, py), QPointF(px+h_sz, py-h_sz), QPointF(px+h_sz, py+h_sz)]))
            elif shape_id == 2: # Right Tri
                painter.drawPolygon(QPolygonF([QPointF(px+h_sz, py), QPointF(px-h_sz, py-h_sz), QPointF(px-h_sz, py+h_sz)]))
            elif shape_id == 3: # Down Tri
                painter.drawPolygon(QPolygonF([QPointF(px, py+h_sz), QPointF(px-h_sz, py-h_sz), QPointF(px+h_sz, py-h_sz)]))
            
            if is_latest:
                painter.setBrush(Qt.NoBrush)
                painter.setPen(QPen(Qt.white, 2))
                painter.drawEllipse(center, h_sz+4, h_sz+4)
                
                painter.setPen(Qt.white)
                painter.setFont(QFont(FONTS["digit"], 11, QFont.Bold))
                painter.drawText(QRectF(px+15, py-10, 60, 20), Qt.AlignLeft|Qt.AlignVCenter, f"{int(pitch.velocity)}")

        painter.setOpacity(0.6)
        for d in self.pitches:
            if d == self.current_pitch: continue
            draw_mark(d, False)
            
        painter.setOpacity(1.0)
        if self.current_pitch:
            draw_mark(self.current_pitch, True)


# ========================================
# フィールド (スタイリッシュ・全体表示)
# ========================================
class StylishFieldWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.batted_ball = None
        self.runners = [False, False, False]

    def set_batted_ball(self, ball_data):
        self.batted_ball = ball_data
        self.update()

    def set_runners(self, runners):
        self.runners = runners
        self.update()

    def clear(self):
        self.batted_ball = None
        self.update()

    def project(self, x, y, z=0, width=100, height=100):
        cam_h = 90.0
        cam_d = -80.0
        scale = min(width, height) * 2.8
        depth = (y - cam_d)
        if depth < 1: depth = 1
        persp = 150.0 / (depth + 100.0)
        cx = width / 2
        cy = height * 0.9
        sx = cx + (x * persp * scale * 0.005)
        gy = cy - (y * persp * scale * 0.004)
        sy = gy - (z * persp * scale * 0.01)
        return QPointF(sx, sy)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        
        painter.fillRect(self.rect(), COLORS["bg"])
        
        radius = 122.0
        poly = QPolygonF()
        steps = 40
        for i in range(steps + 1):
            deg = -45 + (90 * i / steps)
            rad = math.radians(deg)
            poly.append(self.project(radius * math.sin(rad), radius * math.cos(rad), 0, w, h))
        poly.append(self.project(0, 0, 0, w, h))
        
        painter.setPen(Qt.NoPen)
        painter.setBrush(COLORS["field_fair"])
        painter.drawPolygon(poly)
        
        painter.setPen(QPen(COLORS["line"], 2))
        home = self.project(0, 0, 0, w, h)
        pole_l = self.project(-86, 86, 0, w, h)
        pole_r = self.project(86, 86, 0, w, h)
        painter.drawLine(home, pole_l)
        painter.drawLine(home, pole_r)
        
        wall_h = 3.5
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#263238"))
        for i in range(steps):
            deg1 = -45 + (90 * i / steps)
            deg2 = -45 + (90 * (i+1) / steps)
            r1, r2 = math.radians(deg1), math.radians(deg2)
            p1 = self.project(radius*math.sin(r1), radius*math.cos(r1), 0, w, h)
            p2 = self.project(radius*math.sin(r2), radius*math.cos(r2), 0, w, h)
            p3 = self.project(radius*math.sin(r2), radius*math.cos(r2), wall_h, w, h)
            p4 = self.project(radius*math.sin(r1), radius*math.cos(r1), wall_h, w, h)
            painter.drawPolygon(QPolygonF([p1, p2, p3, p4]))

        painter.setPen(QPen(COLORS["line"], 1))
        first = self.project(19.3, 19.3, 0, w, h)
        second = self.project(0, 38.7, 0, w, h)
        third = self.project(-19.3, 19.3, 0, w, h)
        painter.drawLine(home, first)
        painter.drawLine(first, second)
        painter.drawLine(second, third)
        painter.drawLine(third, home)
        
        mound = self.project(0, 18.44, 0, w, h)
        painter.setBrush(COLORS["line"])
        painter.setPen(Qt.NoPen)
        mw = w * 0.04
        painter.drawEllipse(mound, mw/2, mw*0.3)

        def draw_base(pt, occ):
            col = COLORS["accent2"] if occ else QColor("#666")
            painter.setBrush(col)
            sz = w * 0.008
            painter.drawPolygon(QPolygonF([
                QPointF(pt.x(), pt.y()-sz*0.6),
                QPointF(pt.x()+sz, pt.y()),
                QPointF(pt.x(), pt.y()+sz*0.6),
                QPointF(pt.x()-sz, pt.y())
            ]))
            
        draw_base(first, self.runners[0])
        draw_base(second, self.runners[1])
        draw_base(third, self.runners[2])

        if self.batted_ball and self.batted_ball.trajectory:
            traj = self.batted_ball.trajectory
            path = QPainterPath()
            start = self.project(traj[0][0], traj[0][1], traj[0][2], w, h)
            path.moveTo(start)
            shadow_path = QPainterPath()
            shadow_path.moveTo(self.project(traj[0][0], traj[0][1], 0, w, h))
            
            for p in traj:
                pt = self.project(p[0], p[1], p[2], w, h)
                path.lineTo(pt)
                spt = self.project(p[0], p[1], 0, w, h)
                shadow_path.lineTo(spt)
            
            painter.setPen(QPen(QColor(0,0,0,100), 2))
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(shadow_path)
            
            lc = COLORS["accent"]
            if "HOME_RUN" in str(self.batted_ball.hit_type): lc = COLORS["out"]
            painter.setPen(QPen(lc, 3))
            painter.drawPath(path)
            
            last = traj[-1]
            ball_pt = self.project(last[0], last[1], last[2], w, h)
            painter.setBrush(Qt.white)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(ball_pt, 3, 3)


# ========================================
# メイン画面 (HUDレイアウト)
# ========================================

class LiveGamePage(QWidget):
    game_finished = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.live_engine = None
        self.is_simulating = False
        self.selected_strategy = "SWING"
        
        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. 3D Field (Background)
        self.field_widget = StylishFieldWidget()
        layout.addWidget(self.field_widget, 0, 0)
        
        # 2. UI Overlay
        ui_container = QWidget()
        ui_container.setAttribute(Qt.WA_TranslucentBackground)
        ui_container.setStyleSheet("background: transparent;")
        
        ui_grid = QGridLayout(ui_container)
        ui_grid.setContentsMargins(20, 20, 20, 20)
        ui_grid.setSpacing(15)
        
        # Top: Scoreboard
        self.scoreboard = self._create_scoreboard()
        ui_grid.addWidget(self.scoreboard, 0, 0, 1, 3, Qt.AlignTop | Qt.AlignHCenter)
        
        # Spacer
        ui_grid.setRowStretch(1, 1)
        
        # Bottom Left: Controls & Logs
        control_panel = self._create_controls_panel()
        ui_grid.addWidget(control_panel, 2, 0, Qt.AlignBottom | Qt.AlignLeft)
        
        # Bottom Right: Info & Zone
        right_area = QWidget()
        r_layout = QVBoxLayout(right_area)
        r_layout.setContentsMargins(0,0,0,0)
        r_layout.setSpacing(10)
        
        # Tracking Info (Top of Right Area)
        self.track_info = self._create_track_info()
        r_layout.addWidget(self.track_info)
        
        # Player Info & Zone
        player_zone = QHBoxLayout()
        self.matchup_panel = self._create_matchup()
        self.zone_panel = self._create_zone_panel()
        player_zone.addWidget(self.matchup_panel)
        player_zone.addWidget(self.zone_panel)
        r_layout.addLayout(player_zone)
        
        ui_grid.addWidget(right_area, 2, 2, Qt.AlignBottom | Qt.AlignRight)
        
        layout.addWidget(ui_container, 0, 0)

    def _hud_style(self):
        return """
            background-color: rgba(10, 10, 12, 240);
            border: 1px solid #333;
            border-radius: 0px;
        """

    def _create_scoreboard(self):
        f = QFrame()
        f.setFixedSize(800, 70)
        f.setStyleSheet(self._hud_style())
        l = QHBoxLayout(f)
        l.setContentsMargins(20, 0, 20, 0)
        
        l.addWidget(QLabel("AWAY", styleSheet="color:#888; font-weight:bold; font-size:14px;"))
        self.lbl_away = QLabel("TEAM A", styleSheet="color:white; font-weight:bold; font-size:20px;")
        l.addWidget(self.lbl_away)
        self.lbl_away_score = QLabel("0", styleSheet=f"color:{COLORS['accent2'].name()}; font-weight:900; font-size:36px;")
        l.addWidget(self.lbl_away_score)
        
        l.addStretch()
        
        self.lbl_inning = QLabel("1st TOP", styleSheet="color:#00e5ff; font-weight:bold; font-size:16px;")
        l.addWidget(self.lbl_inning)
        
        # 修正: アウトカウントをリストで保持
        self.lbl_outs = [QLabel("●"), QLabel("●")]
        for lbl in self.lbl_outs:
            lbl.setStyleSheet("color:#444; font-size:14px; margin-left:5px;")
            l.addWidget(lbl)
        
        l.addStretch()
        
        self.lbl_home_score = QLabel("0", styleSheet=f"color:{COLORS['accent2'].name()}; font-weight:900; font-size:36px;")
        l.addWidget(self.lbl_home_score)
        self.lbl_home = QLabel("TEAM B", styleSheet="color:white; font-weight:bold; font-size:20px;")
        l.addWidget(self.lbl_home)
        l.addWidget(QLabel("HOME", styleSheet="color:#888; font-weight:bold; font-size:14px;"))
        
        return f

    def _create_track_info(self):
        f = QFrame()
        f.setFixedSize(280, 60)
        f.setStyleSheet("background: rgba(0,0,0,0.5); border: 1px solid #00e5ff;")
        l = QGridLayout(f)
        l.setContentsMargins(10,5,10,5)
        
        def lbl(t, v):
            return QLabel(f"{t}: {v}", styleSheet="color:white; font-family:Roboto Mono; font-size:12px;")
            
        self.lbl_tv = lbl("VELO", "-")
        self.lbl_ta = lbl("ANG", "-")
        self.lbl_td = lbl("DIST", "-")
        
        l.addWidget(self.lbl_tv, 0, 0)
        l.addWidget(self.lbl_ta, 0, 1)
        l.addWidget(self.lbl_td, 1, 0, 1, 2)
        return f

    def _create_matchup(self):
        f = QFrame()
        f.setFixedSize(280, 180)
        f.setStyleSheet(self._hud_style())
        l = QVBoxLayout(f)
        l.setContentsMargins(15, 10, 15, 10)
        
        # Batter
        l.addWidget(QLabel("AT BAT", styleSheet="color:#00e5ff; font-size:10px; font-weight:bold;"))
        self.lbl_batter = QLabel("---", styleSheet="color:white; font-size:20px; font-weight:bold;")
        l.addWidget(self.lbl_batter)
        self.lbl_b_stat = QLabel("Pow: - Con: -", styleSheet="color:#aaa; font-size:12px;")
        l.addWidget(self.lbl_b_stat)
        
        l.addSpacing(5)
        l.addWidget(QFrame(styleSheet="background:#333; max-height:1px;"))
        l.addSpacing(5)
        
        # Pitcher
        l.addWidget(QLabel("PITCHER", styleSheet="color:#ffd700; font-size:10px; font-weight:bold;"))
        self.lbl_pitcher = QLabel("---", styleSheet="color:#ddd; font-size:16px; font-weight:bold;")
        l.addWidget(self.lbl_pitcher)
        self.lbl_p_stat = QLabel("Stamina", styleSheet="color:#aaa; font-size:12px;")
        l.addWidget(self.lbl_p_stat)
        self.p_stamina = QProgressBar()
        self.p_stamina.setFixedHeight(6)
        self.p_stamina.setStyleSheet("QProgressBar{background:#333; border:none;} QProgressBar::chunk{background:#ffd700;}")
        l.addWidget(self.p_stamina)
        
        l.addStretch()
        return f

    def _create_zone_panel(self):
        f = QFrame()
        f.setFixedSize(200, 250)
        f.setStyleSheet(self._hud_style())
        l = QVBoxLayout(f)
        l.setContentsMargins(0,0,0,0)
        
        cbox = QFrame()
        cbox.setStyleSheet("border-bottom: 1px solid #333; padding: 5px;")
        cl = QHBoxLayout(cbox)
        self.lbl_count = QLabel("0 - 0")
        self.lbl_count.setStyleSheet("font-size: 28px; font-weight: 900; color: white;")
        cl.addWidget(self.lbl_count, alignment=Qt.AlignCenter)
        l.addWidget(cbox)
        
        self.zone = StrikeZoneWidget()
        l.addWidget(self.zone)
        return f

    def _create_controls_panel(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(10)
        
        # Log
        scroll = QScrollArea()
        scroll.setFixedSize(350, 120)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: rgba(0,0,0,0.6); border: 1px solid #333;")
        self.log_con = QWidget()
        self.log_con.setStyleSheet("background: transparent;")
        self.log_layout = QVBoxLayout(self.log_con)
        self.log_layout.setAlignment(Qt.AlignTop)
        self.log_layout.setContentsMargins(10, 5, 10, 5)
        scroll.setWidget(self.log_con)
        l.addWidget(scroll)
        
        # Strategy Buttons
        strat_layout = QGridLayout()
        strategies = ["SWING", "MEET", "POWER", "BUNT", "WAIT", "STEAL"]
        self.strat_btns = {}
        for i, s in enumerate(strategies):
            b = QPushButton(s)
            b.setCheckable(True)
            b.setFixedSize(80, 30)
            b.setStyleSheet("""
                QPushButton { background: #333; color: #ccc; border: 1px solid #555; font-weight: bold; }
                QPushButton:checked { background: #00e5ff; color: black; border-color: #00e5ff; }
            """)
            b.clicked.connect(lambda c, x=s: self._set_strategy(x))
            strat_layout.addWidget(b, i//3, i%3)
            self.strat_btns[s] = b
        self.strat_btns["SWING"].setChecked(True)
        l.addLayout(strat_layout)
        
        # Main Actions
        act_layout = QHBoxLayout()
        
        self.btn_pitch = QPushButton("PITCH")
        self.btn_pitch.setFixedSize(100, 40)
        self.btn_pitch.setStyleSheet("background:#0091ea; color:white; border:none; font-weight:bold; font-size:14px;")
        self.btn_pitch.clicked.connect(self._on_pitch)
        
        self.btn_skip = QPushButton("SKIP TO END")
        self.btn_skip.setFixedSize(120, 40)
        self.btn_skip.setStyleSheet("background:#ff1744; color:white; border:none; font-weight:bold;")
        self.btn_skip.clicked.connect(self._on_skip)
        
        act_layout.addWidget(self.btn_pitch)
        act_layout.addWidget(self.btn_skip)
        l.addLayout(act_layout)
        
        return w

    def _set_strategy(self, s):
        for k, b in self.strat_btns.items():
            if k != s: b.setChecked(False)
        self.strat_btns[s].setChecked(True)
        self.selected_strategy = s

    def _setup_timer(self):
        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self._on_pitch)

    # --- Logic ---

    def start_game(self, home, away):
        dlg = GameModeDialog(home, away, self)
        if dlg.exec() == QDialog.Accepted:
            self._init_engine(home, away)
            if dlg.selected_mode == "skip":
                self._run_full_simulation()
            else:
                self._update_display()
                self._log("=== PLAY BALL ===", True)

    def _init_engine(self, home, away):
        from live_game_engine import LiveGameEngine
        self.live_engine = LiveGameEngine(home, away)
        
        self.lbl_home.setText(home.name[:3].upper())
        self.lbl_away.setText(away.name[:3].upper())
        self.zone.clear_pitches()
        self.field_widget.clear()
        
        # Reset logs
        while self.log_layout.count():
            item = self.log_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def _on_pitch(self):
        if self.live_engine.is_game_over(): return
        
        # Decide strategy via AI if CPU turn (simplified for demo)
        strat = self.selected_strategy
        if not self.live_engine.state.is_top: # Home (Player) is batting
             pass 
        else: # CPU batting
             strat = self.live_engine.ai.decide_strategy(self.live_engine.state, None, None)

        res, pitch, ball = self.live_engine.simulate_pitch(strat)
        play_res = self.live_engine.process_pitch_result(res, pitch, ball)
        
        # Logic for visual feedback
        is_hit, is_out = False, False
        is_strikeout = (play_res == PlayResult.STRIKEOUT)
        if play_res:
            name = play_res.name
            if "HIT" in name or play_res in [PlayResult.SINGLE, PlayResult.DOUBLE, PlayResult.TRIPLE, PlayResult.HOME_RUN]: is_hit = True
            elif "OUT" in name or play_res in [PlayResult.STRIKEOUT, PlayResult.GROUNDOUT, PlayResult.FLYOUT, PlayResult.LINEOUT, PlayResult.POPUP_OUT]: is_out = True
        
        pitcher, _ = self.live_engine.get_current_pitcher()
        hand = getattr(pitcher, 'throw_hand', 'Right')
        
        if pitch:
            r_str = play_res.value if play_res else res.value
            self.zone.add_pitch(pitch, r_str, is_hit, is_out, is_strikeout, hand)
            
            info = f"{pitch.pitch_type} {int(pitch.velocity)}km"
            if play_res:
                self._log(f"{info} -> {play_res.value}", True)
                if is_hit or is_out:
                    # Longer delay for hit/out (6s)
                    QTimer.singleShot(6000, self.zone.clear_pitches)
                    QTimer.singleShot(6000, self.field_widget.clear)
            else:
                self._log(f"{info} -> {res.value}")

        if ball:
            self.field_widget.set_batted_ball(ball)
            # Update Tracking Info
            self.lbl_tv.setText(f"VELO: {int(ball.exit_velocity)}km")
            self.lbl_ta.setText(f"ANG: {int(ball.launch_angle)}dg")
            self.lbl_td.setText(f"DIST: {int(ball.distance)}m")

        self._update_display()
        if self.live_engine.is_game_over(): self._finish()

    def _on_skip(self):
        self._run_full_simulation()

    def _run_full_simulation(self):
        # AI vs AI simulation loop
        while not self.live_engine.is_game_over():
            # AI decisions
            strat = self.live_engine.ai.decide_strategy(self.live_engine.state, None, None)
            r, p, b = self.live_engine.simulate_pitch(strat)
            self.live_engine.process_pitch_result(r, p, b)
        self._finish()

    def _update_display(self):
        st = self.live_engine.state
        self.lbl_home_score.setText(str(st.home_score))
        self.lbl_away_score.setText(str(st.away_score))
        self.lbl_inning.setText(f"{st.inning} {'TOP' if st.is_top else 'BOT'}")
        
        col_on, col_off = "#ff1744", "#333"
        self.lbl_outs[0].setStyleSheet(f"color: {col_on if st.outs >= 1 else col_off}; font-size:14px; margin-left:5px;")
        self.lbl_outs[1].setStyleSheet(f"color: {col_on if st.outs >= 2 else col_off}; font-size:14px; margin-left:5px;")
        self.lbl_count.setText(f"{st.balls} - {st.strikes}")
        
        b, _ = self.live_engine.get_current_batter()
        p, _ = self.live_engine.get_current_pitcher()
        
        if b:
            self.lbl_batter.setText(b.name)
            p_rank = get_rank(getattr(b.stats, 'power', 50))
            c_rank = get_rank(getattr(b.stats, 'contact', 50))
            r_rank = get_rank(getattr(b.stats, 'run', 50))
            self.lbl_b_stat.setText(f"Pow:{p_rank} Con:{c_rank} Run:{r_rank}")
        if p:
            self.lbl_pitcher.setText(p.name)
            stam = st.current_pitcher_stamina()
            self.p_stamina.setValue(int(stam))
            
        runners = [st.runner_1b is not None, st.runner_2b is not None, st.runner_3b is not None]
        self.field_widget.set_runners(runners)

    def _log(self, txt, hl=False):
        l = QLabel(txt)
        c = "#ffd700" if hl else "#ccc"
        l.setStyleSheet(f"color:{c}; font-family:'{FONTS['digit']}'; font-size:11px;")
        self.log_layout.insertWidget(0, l)

    def _finish(self):
        self.sim_timer.stop()
        self._log("=== GAME SET ===", True)
        res = {
            "home_team": self.live_engine.home_team,
            "away_team": self.live_engine.away_team,
            "home_score": self.live_engine.state.home_score,
            "away_score": self.live_engine.state.away_score,
            "winner": self.live_engine.get_winner()
        }
        self.game_finished.emit(res)