# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Live Game Page
一球速報風のリアルタイム試合シミュレーション
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout, QGraphicsDropShadowEffect,
    QDialog, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPainterPath

import sys
import os
import math
# パス設定 (必要に応じて調整)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.cards import Card

# ========================================
# 試合開始モード選択ダイアログ
# ========================================

class GameModeDialog(QDialog):
    """試合モード選択ダイアログ"""

    mode_selected = Signal(str)  # "skip" or "manage"

    def __init__(self, home_team, away_team, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.home_team = home_team
        self.away_team = away_team

        self.setWindowTitle("試合モード選択")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(500, 420)

        self._setup_ui()

    def _setup_ui(self):
        # コンテナ
        container = QFrame(self)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 10)
        container.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(container)

        content = QVBoxLayout(container)
        content.setContentsMargins(32, 32, 32, 32)
        content.setSpacing(24)

        # タイトル
        title = QLabel("GAME START")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 700;
            color: {self.theme.text_primary};
            letter-spacing: 3px;
        """)
        title.setAlignment(Qt.AlignCenter)
        content.addWidget(title)

        # 対戦カード
        matchup_frame = QFrame()
        matchup_frame.setStyleSheet(f"background: {self.theme.bg_input}; border-radius: 8px;")
        matchup_layout = QHBoxLayout(matchup_frame)
        
        away_lbl = QLabel(self.away_team.name)
        away_lbl.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {self.theme.text_primary};")
        
        vs_lbl = QLabel("VS")
        vs_lbl.setStyleSheet(f"font-size: 14px; color: {self.theme.text_muted}; font-weight: bold;")
        
        home_lbl = QLabel(self.home_team.name)
        home_lbl.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {self.theme.text_primary};")
        
        matchup_layout.addWidget(away_lbl, alignment=Qt.AlignCenter)
        matchup_layout.addWidget(vs_lbl, alignment=Qt.AlignCenter)
        matchup_layout.addWidget(home_lbl, alignment=Qt.AlignCenter)
        
        content.addWidget(matchup_frame)

        content.addSpacing(10)

        # モード選択ボタン
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(12)

        # 采配モード（Manage）
        manage_btn = self._create_mode_button(
            "一球速報モード (MANAGE)",
            "リアルタイムで試合を観戦・指揮します。\nトラッキングデータを確認できます。",
            "manage",
            self.theme.primary
        )
        buttons_layout.addWidget(manage_btn)

        # スキップ（Skip）
        skip_btn = self._create_mode_button(
            "結果のみ表示 (SKIP)",
            "試合を高速でシミュレートし、すぐに結果を表示します。",
            "skip",
            self.theme.bg_card_hover
        )
        buttons_layout.addWidget(skip_btn)

        content.addLayout(buttons_layout)
        content.addStretch()

        # キャンセル
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.theme.text_muted};
                border: none;
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: {self.theme.text_primary};
                text-decoration: underline;
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        content.addWidget(cancel_btn, alignment=Qt.AlignCenter)

    def _create_mode_button(self, title: str, description: str, mode: str, color: str) -> QPushButton:
        """モード選択ボタンを作成"""
        btn = QPushButton()
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(80)
        
        # 色の決定
        bg_color = self.theme.bg_input
        border_color = self.theme.border
        if mode == "manage":
            border_color = color
            
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 8px;
                text-align: left;
                padding: 12px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.bg_card_hover};
                border: 1px solid {self.theme.primary};
            }}
        """)
        
        layout = QVBoxLayout(btn)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {self.theme.text_primary}; bg: transparent;")
        title_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet(f"font-size: 11px; color: {self.theme.text_secondary}; bg: transparent;")
        desc_lbl.setWordWrap(True)
        desc_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        layout.addWidget(title_lbl)
        layout.addWidget(desc_lbl)
        
        btn.clicked.connect(lambda: self._on_mode_selected(mode))
        
        return btn

    def _on_mode_selected(self, mode: str):
        self.mode_selected.emit(mode)
        self.accept()


# ========================================
# トラッキング＆フィールド表示ウィジェット
# ========================================

class StrikeZoneWidget(QWidget):
    """ストライクゾーン表示（投球トラッキング）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.setMinimumSize(200, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.pitches = []  # (PitchData, result_str)
        self.current_pitch = None

    def add_pitch(self, pitch_data, result: str = ""):
        self.pitches.append((pitch_data, result))
        if len(self.pitches) > 10: # 直近10球
            self.pitches.pop(0)
        self.update()

    def set_current_pitch(self, pitch_data):
        self.current_pitch = pitch_data
        self.update()

    def clear_pitches(self):
        self.pitches.clear()
        self.current_pitch = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景
        painter.fillRect(self.rect(), QColor(self.theme.bg_darkest))

        w = self.width()
        h = self.height()
        
        # ゾーン描画領域
        margin = 40
        zone_w = w - margin * 2
        zone_h = zone_w * 1.3
        zone_x = margin
        zone_y = (h - zone_h) / 2

        # ストライクゾーン枠
        painter.setPen(QPen(QColor(self.theme.border_light), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(QRectF(zone_x, zone_y, zone_w, zone_h))

        # 9分割グリッド
        painter.setPen(QPen(QColor(self.theme.border_muted), 1, Qt.DotLine))
        for i in range(1, 3):
            x = zone_x + zone_w * i / 3
            painter.drawLine(QPointF(x, zone_y), QPointF(x, zone_y + zone_h))
            y = zone_y + zone_h * i / 3
            painter.drawLine(QPointF(zone_x, y), QPointF(zone_x + zone_w, y))

        # 過去の投球を描画（薄く）
        for pitch_data, result in self.pitches:
            if pitch_data and pitch_data.location:
                self._draw_pitch(painter, pitch_data, result, zone_x, zone_y, zone_w, zone_h, alpha=100)

        # 現在の投球を描画（強調）
        if self.current_pitch and self.current_pitch.location:
            self._draw_pitch(painter, self.current_pitch, "", zone_x, zone_y, zone_w, zone_h, alpha=255, is_current=True)

        # テキスト
        painter.setPen(QColor(self.theme.text_muted))
        painter.setFont(QFont("Segoe UI", 8))
        painter.drawText(QRectF(0, h - 20, w, 20), Qt.AlignCenter, "CATCHER VIEW")

    def _draw_pitch(self, painter, pitch_data, result, zx, zy, zw, zh, alpha=255, is_current=False):
        loc = pitch_data.location
        
        # 座標変換: x(-0.5~0.5 m) -> 画面, z(0.5~1.1 m) -> 画面
        # ストライクゾーン中心: x=0, z=0.85 (live_game_engine定義)
        # ゾーン幅 0.432m, 高さ 0.56m
        
        # 正規化座標 (-1 ~ 1)
        nx = loc.x / (0.432 / 2)
        nz = (loc.z - 0.85) / (0.56 / 2)
        
        # 画面座標
        px = zx + zw/2 + nx * (zw/2)
        py = zy + zh/2 - nz * (zh/2)
        
        # 色決定
        if is_current:
            color = QColor(self.theme.warning) # 最新は黄色
        elif loc.is_strike:
            color = QColor(self.theme.danger) # ストライクは赤
        else:
            color = QColor(self.theme.success) # ボールは緑/青
            
        color.setAlpha(alpha)
        
        # 描画
        radius = 8 if is_current else 6
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QPointF(px, py), radius, radius)
        
        # 球種・球速表示（最新のみ）
        if is_current:
            painter.setPen(QColor(self.theme.text_primary))
            painter.setFont(QFont("Segoe UI", 9, QFont.Bold))
            text = f"{pitch_data.pitch_type}\n{int(pitch_data.velocity)}km/h"
            
            # テキスト位置調整
            tx = px + 12 if px < zx + zw/2 else px - 60
            ty = py - 10
            painter.drawText(QRectF(tx, ty, 60, 40), Qt.AlignLeft, text)


class FieldWidget(QWidget):
    """フィールド表示（打球トラッキング）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.batted_ball = None
        self.runners = [False, False, False]

    def set_batted_ball(self, ball_data):
        self.batted_ball = ball_data
        self.update()

    def set_runners(self, runners: list):
        self.runners = runners
        self.update()

    def clear(self):
        self.batted_ball = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 芝生
        painter.fillRect(self.rect(), QColor("#2E7D32")) # 濃い緑

        w = self.width()
        h = self.height()
        
        # フィールド設定
        scale = min(w, h) / 280  # スケール調整
        home_x = w / 2
        home_y = h - 40 * scale

        # フェンス描画
        painter.setPen(QPen(QColor("#FFD54F"), 3))
        painter.setBrush(Qt.NoBrush)
        center_dist = 122 * scale
        rect = QRectF(home_x - center_dist, home_y - center_dist, center_dist*2, center_dist*2)
        painter.drawArc(rect, 45 * 16, 90 * 16) # 45度〜135度

        # ファウルライン
        painter.setPen(QPen(QColor("white"), 2))
        line_len = center_dist
        # レフト
        painter.drawLine(QPointF(home_x, home_y), 
                         QPointF(home_x - line_len * 0.707, home_y - line_len * 0.707))
        # ライト
        painter.drawLine(QPointF(home_x, home_y), 
                         QPointF(home_x + line_len * 0.707, home_y - line_len * 0.707))

        # 内野ダイヤモンド
        base_dist = 27.4 * scale
        
        # 塁座標
        p_home = QPointF(home_x, home_y)
        p_1b = QPointF(home_x + base_dist*0.707, home_y - base_dist*0.707)
        p_2b = QPointF(home_x, home_y - base_dist*1.414)
        p_3b = QPointF(home_x - base_dist*0.707, home_y - base_dist*0.707)

        # ランナー状況描画
        base_size = 8 * scale
        bases = [p_1b, p_2b, p_3b]
        
        painter.setPen(QPen(QColor("white"), 1))
        painter.drawLine(p_home, p_1b)
        painter.drawLine(p_1b, p_2b)
        painter.drawLine(p_2b, p_3b)
        painter.drawLine(p_3b, p_home)

        # ベース
        for i, pos in enumerate(bases):
            color = QColor(self.theme.warning) if self.runners[i] else QColor("white")
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor("black"), 1))
            painter.drawPolygon([
                QPointF(pos.x(), pos.y() - base_size),
                QPointF(pos.x() + base_size, pos.y()),
                QPointF(pos.x(), pos.y() + base_size),
                QPointF(pos.x() - base_size, pos.y())
            ])

        # ホームベース
        painter.setBrush(QBrush(QColor("white")))
        painter.drawPolygon([
            QPointF(home_x, home_y + base_size),
            QPointF(home_x + base_size, home_y),
            QPointF(home_x + base_size, home_y - base_size),
            QPointF(home_x - base_size, home_y - base_size),
            QPointF(home_x - base_size, home_y)
        ])

        # 打球軌跡の描画
        if self.batted_ball and self.batted_ball.trajectory:
            self._draw_ball_path(painter, home_x, home_y, scale)

    def _draw_ball_path(self, painter, hx, hy, scale):
        path = QPainterPath()
        traj = self.batted_ball.trajectory
        
        if not traj: return

        # 軌道を描画
        start_pt = QPointF(hx + traj[0][0]*scale, hy - traj[0][1]*scale)
        path.moveTo(start_pt)
        
        for pt in traj[1:]:
            # x:左右, y:前後
            x, y = pt[0], pt[1]
            path.lineTo(hx + x*scale, hy - y*scale)
            
        # 打球タイプによる色分け
        if self.batted_ball.hit_type.name == "HOME_RUN":
            color = QColor("#E91E63") # ピンク
            width = 3
        elif self.batted_ball.contact_quality == "hard":
            color = QColor("#FF5722") # オレンジ
            width = 2
        else:
            color = QColor("#4FC3F7") # 水色
            width = 2
            
        painter.setPen(QPen(color, width))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        
        # 落下点
        last = traj[-1]
        end_pt = QPointF(hx + last[0]*scale, hy - last[1]*scale)
        painter.setBrush(QBrush(color))
        painter.drawEllipse(end_pt, 4, 4)


# ========================================
# ライブゲームページ (メイン)
# ========================================

class LiveGamePage(QWidget):
    """一球速報風ライブゲームページ"""

    game_finished = Signal(object) # 結果辞書をemit

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()

        self.live_engine = None
        self.is_simulating = False
        self.sim_speed = 800 # ms
        
        self.home_team = None
        self.away_team = None

        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        self.setStyleSheet(f"background: {self.theme.bg_dark};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # --- ヘッダー（スコアボード） ---
        self.scoreboard = self._create_scoreboard()
        layout.addWidget(self.scoreboard)

        # --- メインコンテンツ ---
        content = QHBoxLayout()
        content.setSpacing(12)

        # 左：フィールド
        field_frame = self._create_panel("FIELD VIEW", FieldWidget())
        self.field_widget = field_frame.findChild(FieldWidget)
        content.addWidget(field_frame, stretch=4)

        # 右：情報＆コントロール
        right_layout = QVBoxLayout()
        right_layout.setSpacing(12)

        # 対戦情報パネル
        self.matchup_panel = self._create_matchup_panel()
        right_layout.addWidget(self.matchup_panel)
        
        # ストライクゾーン
        zone_frame = self._create_panel("PITCH TRACKING", StrikeZoneWidget())
        self.strike_zone = zone_frame.findChild(StrikeZoneWidget)
        right_layout.addWidget(zone_frame)
        
        # コントロール
        self.control_panel = self._create_control_panel()
        right_layout.addWidget(self.control_panel)

        content.addLayout(right_layout, stretch=3)
        layout.addLayout(content)

        # --- ログ ---
        self.log_panel = self._create_log_panel()
        layout.addWidget(self.log_panel)

    def _create_scoreboard(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"background: {self.theme.bg_card}; border: 1px solid {self.theme.border}; border-radius: 8px;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(24, 12, 24, 12)

        # Away
        self.away_name = QLabel("AWAY")
        self.away_score = QLabel("0")
        self.away_score.setStyleSheet(f"font-size: 36px; font-weight: 800; color: {self.theme.text_primary};")
        
        # Home
        self.home_name = QLabel("HOME")
        self.home_score = QLabel("0")
        self.home_score.setStyleSheet(f"font-size: 36px; font-weight: 800; color: {self.theme.text_primary};")

        # Inning
        self.inning_label = QLabel("1回表")
        self.inning_label.setStyleSheet(f"font-size: 18px; font-weight: 700; color: {self.theme.primary}; background: {self.theme.bg_input}; padding: 4px 12px; border-radius: 4px;")
        
        # Count
        self.count_label = QLabel("0-0")
        self.count_label.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {self.theme.text_primary};")
        self.outs_label = QLabel("●●") # アウトカウント
        self.outs_label.setStyleSheet(f"font-size: 16px; color: {self.theme.text_muted};")

        layout.addWidget(self.away_name)
        layout.addWidget(self.away_score)
        layout.addStretch()
        layout.addWidget(self.inning_label)
        layout.addSpacing(20)
        layout.addWidget(self.count_label)
        layout.addWidget(self.outs_label)
        layout.addStretch()
        layout.addWidget(self.home_score)
        layout.addWidget(self.home_name)
        
        return frame

    def _create_panel(self, title, widget) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"background: {self.theme.bg_card}; border: 1px solid {self.theme.border}; border-radius: 8px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 12)
        layout.setSpacing(4)
        
        lbl = QLabel(title)
        lbl.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {self.theme.text_muted}; letter-spacing: 1px;")
        layout.addWidget(lbl)
        layout.addWidget(widget)
        return frame

    def _create_matchup_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"background: {self.theme.bg_input}; border: 1px solid {self.theme.border}; border-radius: 8px;")
        layout = QGridLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        
        self.pitcher_name = QLabel("投手: -")
        self.pitcher_info = QLabel("ERA: -")
        self.batter_name = QLabel("打者: -")
        self.batter_info = QLabel("AVG: -")
        
        for l in [self.pitcher_name, self.batter_name]:
            l.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {self.theme.text_primary};")
        for l in [self.pitcher_info, self.batter_info]:
            l.setStyleSheet(f"font-size: 12px; color: {self.theme.text_secondary};")

        layout.addWidget(self.pitcher_name, 0, 0)
        layout.addWidget(self.pitcher_info, 0, 1)
        layout.addWidget(self.batter_name, 1, 0)
        layout.addWidget(self.batter_info, 1, 1)
        
        return frame

    def _create_control_panel(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(f"background: {self.theme.bg_card}; border: 1px solid {self.theme.border}; border-radius: 8px;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # メインボタン
        self.pitch_btn = QPushButton("PITCH (投球)")
        self.pitch_btn.setStyleSheet(f"""
            QPushButton {{ background: {self.theme.primary}; color: white; border-radius: 4px; padding: 12px; font-weight: bold; font-size: 14px; }}
            QPushButton:hover {{ background: {self.theme.primary_hover}; }}
        """)
        self.pitch_btn.clicked.connect(self._on_pitch_clicked)
        
        self.auto_btn = QPushButton("AUTO (自動進行)")
        self.auto_btn.setCheckable(True)
        self.auto_btn.setStyleSheet(f"""
            QPushButton {{ background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; border-radius: 4px; padding: 8px; }}
            QPushButton:checked {{ background: {self.theme.success}; color: white; border: none; }}
        """)
        self.auto_btn.clicked.connect(self._on_auto_clicked)
        
        layout.addWidget(self.pitch_btn)
        layout.addWidget(self.auto_btn)
        
        return frame

    def _create_log_panel(self) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(120)
        frame.setStyleSheet(f"background: {self.theme.bg_card}; border: 1px solid {self.theme.border}; border-radius: 8px;")
        layout = QVBoxLayout(frame)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        self.log_container = QWidget()
        self.log_layout = QVBoxLayout(self.log_container)
        self.log_layout.setAlignment(Qt.AlignTop)
        
        scroll.setWidget(self.log_container)
        layout.addWidget(scroll)
        
        return frame

    def _setup_timer(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._auto_step)

    # --- ゲーム制御ロジック ---

    def confirm_and_start(self, home_team, away_team):
        """モード選択ダイアログを表示して試合開始"""
        self.home_team = home_team
        self.away_team = away_team
        
        dialog = GameModeDialog(home_team, away_team, self)
        dialog.mode_selected.connect(self._handle_mode_selection)
        dialog.exec()

    def _handle_mode_selection(self, mode):
        """選択されたモードで開始"""
        # エンジン初期化 (パスが通っている前提)
        from live_game_engine import LiveGameEngine
        self.live_engine = LiveGameEngine(self.home_team, self.away_team)
        
        if mode == "skip":
            self._start_skip_mode()
        else:
            self._start_manage_mode()

    def _start_skip_mode(self):
        """スキップモード：即座に計算"""
        # UIをロード中表示などに変更してもよいが、ここでは瞬時に計算
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            while not self.live_engine.is_game_over():
                res, pitch, ball = self.live_engine.simulate_pitch()
                self.live_engine.process_pitch_result(res, pitch, ball)
            
            self._emit_finished()
        finally:
            QApplication.restoreOverrideCursor()

    def _start_manage_mode(self):
        """采配モード：UI初期化して待機"""
        self.away_name.setText(self.away_team.name)
        self.home_name.setText(self.home_team.name)
        self._update_display()
        self._add_log("=== 試合開始 ===", highlight=True)

    def _on_pitch_clicked(self):
        self._simulate_step()

    def _on_auto_clicked(self, checked):
        if checked:
            self.timer.start(self.sim_speed)
        else:
            self.timer.stop()

    def _auto_step(self):
        if not self.live_engine.is_game_over():
            self._simulate_step()
        else:
            self.timer.stop()
            self.auto_btn.setChecked(False)

    def _simulate_step(self):
        """1球シミュレーション"""
        if self.live_engine.is_game_over():
            self._emit_finished()
            return

        # エンジン実行
        result, pitch, ball = self.live_engine.simulate_pitch()
        
        # UI更新（トラッキング）
        if pitch:
            res_str = result.value if result else ""
            self.strike_zone.set_current_pitch(pitch)
            self.strike_zone.add_pitch(pitch, res_str)
            
            # ログ
            velo = f"{int(pitch.velocity)}km/h"
            log_text = f"【{pitch.pitch_type}】 {velo} -> {res_str}"
            self._add_log(log_text)

        # 結果反映
        play_result = self.live_engine.process_pitch_result(result, pitch, ball)
        
        # 打球更新
        if ball:
            self.field_widget.set_batted_ball(ball)
        elif play_result: # ボール・ストライク以外で打球がない（四球・三振）
            pass # 前の打球を残すかクリアするか。ここでは更新しない

        if play_result:
            self._add_log(f"■ {play_result.value}", highlight=True)
            self.strike_zone.clear_pitches() # 打席終了でクリア
            if not ball:
                self.field_widget.clear()

        # スコアボード更新
        self._update_display()
        
        if self.live_engine.is_game_over():
            self._emit_finished()
            self.timer.stop()
            self.auto_btn.setChecked(False)
            self.pitch_btn.setDisabled(True)

    def _update_display(self):
        state = self.live_engine.state
        
        # スコア
        self.away_score.setText(str(state.away_score))
        self.home_score.setText(str(state.home_score))
        
        # イニング
        top_btm = "表" if state.is_top else "裏"
        self.inning_label.setText(f"{state.inning}回{top_btm}")
        
        # カウント
        self.count_label.setText(f"{state.balls}-{state.strikes}")
        # アウトカウント（●で表示）
        out_text = "●" * state.outs + "○" * (3 - state.outs)
        self.outs_label.setText(out_text)
        
        # ランナー
        runners = [
            state.runner_1b is not None,
            state.runner_2b is not None,
            state.runner_3b is not None
        ]
        self.field_widget.set_runners(runners)
        
        # マッチアップ
        batter, _ = self.live_engine.get_current_batter()
        pitcher, _ = self.live_engine.get_current_pitcher()
        
        if batter:
            self.batter_name.setText(f"打: {batter.name}")
            # statsあれば表示
        if pitcher:
            self.pitcher_name.setText(f"投: {pitcher.name}")

    def _add_log(self, text, highlight=False):
        lbl = QLabel(text)
        style = f"font-size: 12px; color: {self.theme.text_secondary};"
        if highlight:
            style = f"font-size: 13px; font-weight: bold; color: {self.theme.warning}; margin-top: 4px;"
        lbl.setStyleSheet(style)
        self.log_layout.insertWidget(0, lbl)
        
        # ログあふれ防止
        if self.log_layout.count() > 50:
            item = self.log_layout.takeAt(50)
            if item.widget(): item.widget().deleteLater()

    def _emit_finished(self):
        winner = self.live_engine.get_winner()
        self._add_log(f"試合終了 勝者: {winner}", highlight=True)
        
        result_data = {
            'home_score': self.live_engine.state.home_score,
            'away_score': self.live_engine.state.away_score,
            'winner': winner,
            'home_team': self.home_team,
            'away_team': self.away_team
        }
        self.game_finished.emit(result_data)