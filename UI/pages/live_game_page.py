# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Live Game Page
一球速報風のリアルタイム試合シミュレーション
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout, QGraphicsDropShadowEffect,
    QDialog, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QPointF, QRectF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QPainterPath, QLinearGradient

import sys
import os
import math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.cards import Card
from UI.widgets.panels import ContentPanel
from UI.widgets.buttons import SimButton


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
        self.setFixedSize(500, 400)

        self._setup_ui()

    def _setup_ui(self):
        # Container
        container = QFrame(self)
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 0px;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 10)
        container.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        content = QVBoxLayout(container)
        content.setContentsMargins(32, 32, 32, 32)
        content.setSpacing(24)

        # タイトル
        title = QLabel("GAME MODE")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 700;
            color: {self.theme.text_primary};
            letter-spacing: 3px;
        """)
        title.setAlignment(Qt.AlignCenter)
        content.addWidget(title)

        # チーム名表示
        matchup = QLabel(f"{self.away_team.name}  VS  {self.home_team.name}")
        matchup.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 500;
            color: {self.theme.text_secondary};
        """)
        matchup.setAlignment(Qt.AlignCenter)
        content.addWidget(matchup)

        content.addSpacing(20)

        # モード選択ボタン
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(16)

        # スキップボタン
        skip_btn = self._create_mode_button(
            "SKIP",
            "試合結果だけを確認",
            "skip"
        )
        buttons_layout.addWidget(skip_btn)

        # 采配モードボタン
        manage_btn = self._create_mode_button(
            "MANAGE",
            "一球速報で試合を観戦・采配",
            "manage"
        )
        buttons_layout.addWidget(manage_btn)

        content.addLayout(buttons_layout)

        content.addStretch()

        # キャンセルボタン
        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.theme.text_muted};
                border: 1px solid {self.theme.border};
                border-radius: 0px;
                padding: 12px;
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 2px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.bg_card_hover};
                color: {self.theme.text_primary};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        content.addWidget(cancel_btn)

    def _create_mode_button(self, title: str, description: str, mode: str) -> QFrame:
        """モード選択ボタンを作成"""
        frame = QFrame()
        frame.setCursor(Qt.PointingHandCursor)
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_input};
                border: 1px solid {self.theme.border};
                border-radius: 0px;
            }}
            QFrame:hover {{
                background-color: {self.theme.bg_card_hover};
                border-color: {self.theme.primary};
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {self.theme.text_primary};
            letter-spacing: 2px;
        """)
        layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"""
            font-size: 13px;
            color: {self.theme.text_secondary};
        """)
        layout.addWidget(desc_label)

        # クリックイベント
        frame.mousePressEvent = lambda e: self._on_mode_selected(mode)

        return frame

    def _on_mode_selected(self, mode: str):
        self.mode_selected.emit(mode)
        self.accept()


# ========================================
# ストライクゾーンウィジェット
# ========================================

class StrikeZoneWidget(QWidget):
    """ストライクゾーン表示（投球トラッキング）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.setMinimumSize(200, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.pitches = []  # PitchDataのリスト
        self.current_pitch = None

    def add_pitch(self, pitch_data, result: str = ""):
        """投球を追加"""
        self.pitches.append((pitch_data, result))
        if len(self.pitches) > 20:
            self.pitches.pop(0)
        self.update()

    def set_current_pitch(self, pitch_data):
        """現在の投球を設定"""
        self.current_pitch = pitch_data
        self.update()

    def clear_pitches(self):
        """投球履歴をクリア"""
        self.pitches.clear()
        self.current_pitch = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景
        painter.fillRect(self.rect(), QColor(self.theme.bg_darkest))

        # サイズ計算
        w = self.width()
        h = self.height()
        margin = 30
        zone_w = w - margin * 2
        zone_h = zone_w * 1.3  # 縦長
        zone_x = margin
        zone_y = (h - zone_h) / 2

        # ストライクゾーン枠
        painter.setPen(QPen(QColor(self.theme.border_light), 2))
        painter.drawRect(QRectF(zone_x, zone_y, zone_w, zone_h))

        # グリッド（9分割）
        painter.setPen(QPen(QColor(self.theme.border_muted), 1))
        for i in range(1, 3):
            # 縦線
            x = zone_x + zone_w * i / 3
            painter.drawLine(QPointF(x, zone_y), QPointF(x, zone_y + zone_h))
            # 横線
            y = zone_y + zone_h * i / 3
            painter.drawLine(QPointF(zone_x, y), QPointF(zone_x + zone_w, y))

        # 過去の投球
        for pitch_data, result in self.pitches:
            if pitch_data and pitch_data.location:
                self._draw_pitch(painter, pitch_data, result, zone_x, zone_y, zone_w, zone_h, is_current=False)

        # 現在の投球
        if self.current_pitch and self.current_pitch.location:
            self._draw_pitch(painter, self.current_pitch, "", zone_x, zone_y, zone_w, zone_h, is_current=True)

        # ラベル
        painter.setPen(QColor(self.theme.text_muted))
        font = QFont("Yu Gothic UI", 10)
        painter.setFont(font)
        painter.drawText(QRectF(0, h - 20, w, 20), Qt.AlignCenter, "STRIKE ZONE")

    def _draw_pitch(self, painter, pitch_data, result: str, zone_x, zone_y, zone_w, zone_h, is_current: bool):
        """投球を描画"""
        loc = pitch_data.location

        # 座標変換（-1〜1の範囲をゾーン座標に）
        # ゾーン幅0.432m、高さ0.56mとして
        norm_x = loc.x / 0.3  # -1〜1に正規化
        norm_z = (loc.z - 0.85) / 0.35  # -1〜1に正規化

        # ピクセル座標に変換
        px = zone_x + zone_w / 2 + norm_x * (zone_w / 2) * 1.5
        py = zone_y + zone_h / 2 - norm_z * (zone_h / 2) * 1.2

        # 範囲制限
        px = max(5, min(self.width() - 5, px))
        py = max(5, min(self.height() - 5, py))

        # 色選択
        if is_current:
            color = QColor(self.theme.warning)
            size = 14
        elif loc.is_strike:
            color = QColor(self.theme.danger)
            size = 8
        else:
            color = QColor(self.theme.info)
            size = 8

        # 描画
        painter.setPen(QPen(color, 2))
        painter.setBrush(QBrush(color))
        painter.drawEllipse(QPointF(px, py), size / 2, size / 2)


# ========================================
# フィールドウィジェット
# ========================================

class FieldWidget(QWidget):
    """フィールド表示（打球トラッキング）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.batted_ball = None
        self.runners = [False, False, False]  # 1塁、2塁、3塁

    def set_batted_ball(self, ball_data):
        """打球データを設定"""
        self.batted_ball = ball_data
        self.update()

    def set_runners(self, runners: list):
        """走者を設定"""
        self.runners = runners[:3] if runners else [False, False, False]
        self.update()

    def clear(self):
        """クリア"""
        self.batted_ball = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 背景
        painter.fillRect(self.rect(), QColor("#1a3d1a"))  # 芝生色

        w = self.width()
        h = self.height()

        # ホームベース位置
        home_x = w / 2
        home_y = h - 40

        # スケール（フィールドを画面に収める）
        scale = min(w, h) / 300

        # 外野フェンス（扇形）
        fence_path = QPainterPath()
        fence_center = 122 * scale
        fence_angle = 45  # 左右各45度

        painter.setPen(QPen(QColor(self.theme.warning), 3))
        painter.setBrush(Qt.NoBrush)

        # 扇形を描画
        rect = QRectF(home_x - fence_center, home_y - fence_center,
                      fence_center * 2, fence_center * 2)
        painter.drawArc(rect, (90 - fence_angle) * 16, fence_angle * 2 * 16)

        # ファウルライン
        painter.setPen(QPen(QColor("white"), 2))
        line_length = fence_center
        # レフト線
        lx = home_x - line_length * math.sin(math.radians(45))
        ly = home_y - line_length * math.cos(math.radians(45))
        painter.drawLine(QPointF(home_x, home_y), QPointF(lx, ly))
        # ライト線
        rx = home_x + line_length * math.sin(math.radians(45))
        ry = home_y - line_length * math.cos(math.radians(45))
        painter.drawLine(QPointF(home_x, home_y), QPointF(rx, ry))

        # 内野ダイヤモンド
        base_dist = 27.431 * scale
        diamond_size = base_dist * 1.414  # 対角線長

        # 塁の位置
        base_positions = [
            (home_x + base_dist * 0.707, home_y - base_dist * 0.707),  # 1塁
            (home_x, home_y - diamond_size),                            # 2塁
            (home_x - base_dist * 0.707, home_y - base_dist * 0.707),  # 3塁
        ]

        # ダイヤモンドを描画
        painter.setPen(QPen(QColor("white"), 1))
        painter.drawLine(QPointF(home_x, home_y), QPointF(*base_positions[0]))
        painter.drawLine(QPointF(*base_positions[0]), QPointF(*base_positions[1]))
        painter.drawLine(QPointF(*base_positions[1]), QPointF(*base_positions[2]))
        painter.drawLine(QPointF(*base_positions[2]), QPointF(home_x, home_y))

        # 塁を描画
        base_size = 8
        for i, (bx, by) in enumerate(base_positions):
            if self.runners[i]:
                painter.setBrush(QBrush(QColor(self.theme.warning)))
            else:
                painter.setBrush(QBrush(QColor("white")))
            painter.setPen(Qt.NoPen)
            # 菱形
            path = QPainterPath()
            path.moveTo(bx, by - base_size)
            path.lineTo(bx + base_size, by)
            path.lineTo(bx, by + base_size)
            path.lineTo(bx - base_size, by)
            path.closeSubpath()
            painter.drawPath(path)

        # ホームベース
        painter.setBrush(QBrush(QColor("white")))
        home_path = QPainterPath()
        home_path.moveTo(home_x, home_y + 6)
        home_path.lineTo(home_x + 6, home_y)
        home_path.lineTo(home_x + 6, home_y - 4)
        home_path.lineTo(home_x - 6, home_y - 4)
        home_path.lineTo(home_x - 6, home_y)
        home_path.closeSubpath()
        painter.drawPath(home_path)

        # 打球軌道を描画
        if self.batted_ball and self.batted_ball.trajectory:
            self._draw_trajectory(painter, home_x, home_y, scale)

    def _draw_trajectory(self, painter, home_x, home_y, scale):
        """打球軌道を描画"""
        ball = self.batted_ball

        # 軌道の色（打球質で変える）
        if ball.contact_quality == "hard":
            color = QColor(self.theme.danger)
        elif ball.contact_quality == "medium":
            color = QColor(self.theme.warning)
        else:
            color = QColor(self.theme.info)

        painter.setPen(QPen(color, 2, Qt.DashLine))

        # 軌道を描画
        points = []
        for x, y, z in ball.trajectory:
            # 座標変換（メートル→ピクセル）
            px = home_x + x * scale
            py = home_y - y * scale
            points.append(QPointF(px, py))

        if len(points) > 1:
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])

        # 落下地点
        if points:
            landing = points[-1]
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(landing, 6, 6)

            # 飛距離表示
            painter.setPen(QColor("white"))
            font = QFont("Yu Gothic UI", 10, QFont.Bold)
            painter.setFont(font)
            painter.drawText(QPointF(landing.x() + 10, landing.y()), f"{ball.distance:.0f}m")


# ========================================
# ライブゲームページ
# ========================================

class LiveGamePage(QWidget):
    """一球速報風ライブゲームページ"""

    game_finished = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()

        self.live_engine = None
        self.is_simulating = False
        self.auto_advance = False
        self.sim_speed = 1

        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        self.setStyleSheet(f"background: {self.theme.bg_dark};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ヘッダー（スコアボード）
        self.scoreboard = self._create_scoreboard()
        layout.addWidget(self.scoreboard)

        # メインコンテンツ
        content = QHBoxLayout()
        content.setSpacing(12)

        # 左側：フィールドビュー
        left_panel = self._create_field_panel()
        content.addWidget(left_panel, stretch=2)

        # 中央：情報パネル
        center_panel = self._create_info_panel()
        content.addWidget(center_panel, stretch=1)

        # 右側：ストライクゾーン＆コントロール
        right_panel = self._create_control_panel()
        content.addWidget(right_panel, stretch=1)

        layout.addLayout(content)

        # プレイログ
        self.log_panel = self._create_log_panel()
        layout.addWidget(self.log_panel)

    def _create_scoreboard(self) -> QFrame:
        """スコアボードを作成"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 0px;
            }}
        """)

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(32)

        # アウェイチーム
        away_layout = QVBoxLayout()
        self.away_name = QLabel("AWAY")
        self.away_name.setStyleSheet(f"font-size: 14px; color: {self.theme.text_secondary}; letter-spacing: 2px;")
        self.away_score = QLabel("0")
        self.away_score.setStyleSheet(f"font-size: 48px; font-weight: 700; color: {self.theme.text_primary};")
        away_layout.addWidget(self.away_name, alignment=Qt.AlignCenter)
        away_layout.addWidget(self.away_score, alignment=Qt.AlignCenter)
        layout.addLayout(away_layout)

        # イニング情報
        inning_layout = QVBoxLayout()
        self.inning_label = QLabel("1回表")
        self.inning_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {self.theme.text_primary};
            padding: 8px 24px;
            background: {self.theme.bg_input};
            border-radius: 0px;
        """)
        self.outs_label = QLabel("0 OUT")
        self.outs_label.setStyleSheet(f"font-size: 14px; color: {self.theme.text_secondary};")
        inning_layout.addWidget(self.inning_label, alignment=Qt.AlignCenter)
        inning_layout.addWidget(self.outs_label, alignment=Qt.AlignCenter)
        layout.addLayout(inning_layout)

        # ホームチーム
        home_layout = QVBoxLayout()
        self.home_name = QLabel("HOME")
        self.home_name.setStyleSheet(f"font-size: 14px; color: {self.theme.text_secondary}; letter-spacing: 2px;")
        self.home_score = QLabel("0")
        self.home_score.setStyleSheet(f"font-size: 48px; font-weight: 700; color: {self.theme.text_primary};")
        home_layout.addWidget(self.home_name, alignment=Qt.AlignCenter)
        home_layout.addWidget(self.home_score, alignment=Qt.AlignCenter)
        layout.addLayout(home_layout)

        return frame

    def _create_field_panel(self) -> QFrame:
        """フィールドパネルを作成"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 0px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)

        # タイトル
        title = QLabel("FIELD VIEW")
        title.setStyleSheet(f"font-size: 12px; color: {self.theme.text_muted}; letter-spacing: 2px;")
        layout.addWidget(title)

        # フィールドウィジェット
        self.field_widget = FieldWidget()
        layout.addWidget(self.field_widget)

        return frame

    def _create_info_panel(self) -> QFrame:
        """情報パネルを作成"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 0px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        # カウント表示
        count_frame = QFrame()
        count_frame.setStyleSheet(f"background: {self.theme.bg_input}; border-radius: 0px;")
        count_layout = QVBoxLayout(count_frame)
        count_layout.setContentsMargins(12, 12, 12, 12)

        count_title = QLabel("COUNT")
        count_title.setStyleSheet(f"font-size: 11px; color: {self.theme.text_muted}; letter-spacing: 2px;")
        count_layout.addWidget(count_title)

        self.count_label = QLabel("0 - 0")
        self.count_label.setStyleSheet(f"font-size: 32px; font-weight: 700; color: {self.theme.text_primary};")
        self.count_label.setAlignment(Qt.AlignCenter)
        count_layout.addWidget(self.count_label)

        # B-S-O インジケーター
        bso_layout = QHBoxLayout()
        bso_layout.setSpacing(16)

        self.ball_indicators = self._create_bso_indicator("B", 4, self.theme.success)
        self.strike_indicators = self._create_bso_indicator("S", 3, self.theme.danger)
        self.out_indicators = self._create_bso_indicator("O", 3, self.theme.warning)

        bso_layout.addWidget(self.ball_indicators)
        bso_layout.addWidget(self.strike_indicators)
        bso_layout.addWidget(self.out_indicators)
        count_layout.addLayout(bso_layout)

        layout.addWidget(count_frame)

        # 対戦カード
        matchup_frame = QFrame()
        matchup_frame.setStyleSheet(f"background: {self.theme.bg_input}; border-radius: 0px;")
        matchup_layout = QVBoxLayout(matchup_frame)
        matchup_layout.setContentsMargins(12, 12, 12, 12)
        matchup_layout.setSpacing(8)

        self.pitcher_label = QLabel("投手: -")
        self.pitcher_label.setStyleSheet(f"font-size: 13px; color: {self.theme.text_secondary};")
        self.batter_label = QLabel("打者: -")
        self.batter_label.setStyleSheet(f"font-size: 13px; color: {self.theme.text_primary}; font-weight: 600;")

        matchup_layout.addWidget(self.pitcher_label)
        matchup_layout.addWidget(self.batter_label)
        layout.addWidget(matchup_frame)

        # 投球情報
        pitch_frame = QFrame()
        pitch_frame.setStyleSheet(f"background: {self.theme.bg_input}; border-radius: 0px;")
        pitch_layout = QVBoxLayout(pitch_frame)
        pitch_layout.setContentsMargins(12, 12, 12, 12)
        pitch_layout.setSpacing(4)

        pitch_title = QLabel("LAST PITCH")
        pitch_title.setStyleSheet(f"font-size: 11px; color: {self.theme.text_muted}; letter-spacing: 2px;")
        pitch_layout.addWidget(pitch_title)

        self.pitch_type_label = QLabel("-")
        self.pitch_type_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {self.theme.text_primary};")
        pitch_layout.addWidget(self.pitch_type_label)

        self.pitch_speed_label = QLabel("- km/h")
        self.pitch_speed_label.setStyleSheet(f"font-size: 24px; font-weight: 700; color: {self.theme.accent_blue};")
        pitch_layout.addWidget(self.pitch_speed_label)

        self.pitch_result_label = QLabel("-")
        self.pitch_result_label.setStyleSheet(f"font-size: 14px; color: {self.theme.text_secondary};")
        pitch_layout.addWidget(self.pitch_result_label)

        layout.addWidget(pitch_frame)

        layout.addStretch()

        return frame

    def _create_bso_indicator(self, label: str, count: int, color: str) -> QWidget:
        """B-S-O インジケーターを作成"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.theme.text_muted};")
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)

        dots_layout = QHBoxLayout()
        dots_layout.setSpacing(4)

        widget._dots = []
        for i in range(count):
            dot = QLabel()
            dot.setFixedSize(12, 12)
            dot.setStyleSheet(f"background: {self.theme.border}; border-radius: 6px;")
            dots_layout.addWidget(dot)
            widget._dots.append((dot, color))

        layout.addLayout(dots_layout)
        return widget

    def _update_bso(self, balls: int, strikes: int, outs: int):
        """B-S-Oインジケーターを更新"""
        for i, (dot, color) in enumerate(self.ball_indicators._dots):
            if i < balls:
                dot.setStyleSheet(f"background: {color}; border-radius: 6px;")
            else:
                dot.setStyleSheet(f"background: {self.theme.border}; border-radius: 6px;")

        for i, (dot, color) in enumerate(self.strike_indicators._dots):
            if i < strikes:
                dot.setStyleSheet(f"background: {color}; border-radius: 6px;")
            else:
                dot.setStyleSheet(f"background: {self.theme.border}; border-radius: 6px;")

        for i, (dot, color) in enumerate(self.out_indicators._dots):
            if i < outs:
                dot.setStyleSheet(f"background: {color}; border-radius: 6px;")
            else:
                dot.setStyleSheet(f"background: {self.theme.border}; border-radius: 6px;")

    def _create_control_panel(self) -> QFrame:
        """コントロールパネルを作成"""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 0px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # ストライクゾーン
        zone_title = QLabel("PITCH TRACKING")
        zone_title.setStyleSheet(f"font-size: 12px; color: {self.theme.text_muted}; letter-spacing: 2px;")
        layout.addWidget(zone_title)

        self.strike_zone = StrikeZoneWidget()
        layout.addWidget(self.strike_zone)

        # コントロールボタン
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.pitch_btn = QPushButton("PITCH")
        self.pitch_btn.setCursor(Qt.PointingHandCursor)
        self.pitch_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.primary};
                color: {self.theme.text_highlight};
                border: none;
                border-radius: 0px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 2px;
            }}
            QPushButton:hover {{
                background: {self.theme.primary_hover};
            }}
        """)
        self.pitch_btn.clicked.connect(self._on_pitch_clicked)
        btn_layout.addWidget(self.pitch_btn)

        self.auto_btn = QPushButton("AUTO")
        self.auto_btn.setCursor(Qt.PointingHandCursor)
        self.auto_btn.setCheckable(True)
        self.auto_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.bg_input};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 0px;
                padding: 12px 16px;
                font-size: 13px;
                font-weight: 600;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {self.theme.bg_card_hover};
            }}
            QPushButton:checked {{
                background: {self.theme.success};
                color: white;
                border-color: {self.theme.success};
            }}
        """)
        self.auto_btn.clicked.connect(self._on_auto_clicked)
        btn_layout.addWidget(self.auto_btn)

        layout.addLayout(btn_layout)

        # 作戦ボタン（将来拡張用）
        strategy_title = QLabel("STRATEGY")
        strategy_title.setStyleSheet(f"font-size: 12px; color: {self.theme.text_muted}; letter-spacing: 2px; margin-top: 8px;")
        layout.addWidget(strategy_title)

        strategy_layout = QGridLayout()
        strategy_layout.setSpacing(4)

        strategies = ["SWING", "BUNT", "STEAL", "HIT&RUN"]
        for i, s in enumerate(strategies):
            btn = QPushButton(s)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {self.theme.bg_input};
                    color: {self.theme.text_secondary};
                    border: 1px solid {self.theme.border_muted};
                    border-radius: 0px;
                    padding: 8px;
                    font-size: 11px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {self.theme.bg_card_hover};
                    color: {self.theme.text_primary};
                }}
            """)
            strategy_layout.addWidget(btn, i // 2, i % 2)

        layout.addLayout(strategy_layout)

        layout.addStretch()

        return frame

    def _create_log_panel(self) -> QFrame:
        """プレイログパネルを作成"""
        frame = QFrame()
        frame.setFixedHeight(100)
        frame.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 0px;
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        title = QLabel("PLAY LOG")
        title.setStyleSheet(f"font-size: 11px; color: {self.theme.text_muted}; letter-spacing: 2px;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        self.log_container = QWidget()
        self.log_layout = QVBoxLayout(self.log_container)
        self.log_layout.setContentsMargins(0, 0, 0, 0)
        self.log_layout.setSpacing(2)
        self.log_layout.setAlignment(Qt.AlignTop)

        scroll.setWidget(self.log_container)
        layout.addWidget(scroll)

        return frame

    def _setup_timer(self):
        """タイマーセットアップ"""
        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self._auto_pitch)

    def start_game(self, home_team, away_team, mode: str = "manage"):
        """試合開始"""
        from live_game_engine import LiveGameEngine

        self.live_engine = LiveGameEngine(home_team, away_team)

        # 表示更新
        self.home_name.setText(home_team.name[:6].upper())
        self.away_name.setText(away_team.name[:6].upper())
        self.home_score.setText("0")
        self.away_score.setText("0")

        self._clear_log()
        self.strike_zone.clear_pitches()
        self.field_widget.clear()

        self._update_display()
        self._add_log(f"プレイボール！ {away_team.name} vs {home_team.name}")

        if mode == "skip":
            self._run_full_game()

    def _run_full_game(self):
        """試合をスキップ（全て計算）"""
        if not self.live_engine:
            return

        while not self.live_engine.is_game_over():
            result, pitch, ball = self.live_engine.simulate_pitch()
            play_result = self.live_engine.process_pitch_result(result, pitch, ball)

        self._update_display()
        self._on_game_finished()

    def _on_pitch_clicked(self):
        """投球ボタンクリック"""
        self._simulate_one_pitch()

    def _on_auto_clicked(self):
        """オート切替"""
        self.auto_advance = self.auto_btn.isChecked()
        if self.auto_advance:
            self.sim_timer.start(800)
        else:
            self.sim_timer.stop()

    def _auto_pitch(self):
        """自動投球"""
        if self.live_engine and not self.live_engine.is_game_over():
            self._simulate_one_pitch()
        else:
            self.sim_timer.stop()
            self.auto_btn.setChecked(False)

    def _simulate_one_pitch(self):
        """一球シミュレート"""
        if not self.live_engine or self.live_engine.is_game_over():
            return

        # 投球シミュレート
        result, pitch, ball = self.live_engine.simulate_pitch()

        # 表示更新
        if pitch:
            self.strike_zone.set_current_pitch(pitch)
            self.pitch_type_label.setText(pitch.pitch_type)
            self.pitch_speed_label.setText(f"{pitch.velocity:.0f} km/h")

            result_text = result.value if result else "-"
            self.pitch_result_label.setText(result_text)

            # ログ追加
            self._add_log(f"{pitch.pitch_type} {pitch.velocity:.0f}km/h → {result_text}")

        # 結果処理
        play_result = self.live_engine.process_pitch_result(result, pitch, ball)

        if play_result:
            self._add_log(f"【{play_result.value}】", highlight=True)

            # 打球表示
            if ball:
                self.field_widget.set_batted_ball(ball)

            # 投球履歴に追加してクリア
            if pitch:
                self.strike_zone.add_pitch(pitch, result.value if result else "")
            self.strike_zone.set_current_pitch(None)

        # 表示更新
        self._update_display()

        # 試合終了チェック
        if self.live_engine.is_game_over():
            self._on_game_finished()

    def _update_display(self):
        """表示更新"""
        if not self.live_engine:
            return

        state = self.live_engine.state

        # スコア
        self.home_score.setText(str(state.home_score))
        self.away_score.setText(str(state.away_score))

        # イニング
        half = "表" if state.is_top else "裏"
        self.inning_label.setText(f"{state.inning}回{half}")
        self.outs_label.setText(f"{state.outs} OUT")

        # カウント
        self.count_label.setText(f"{state.balls} - {state.strikes}")
        self._update_bso(state.balls, state.strikes, state.outs)

        # 走者
        runners = [
            state.runner_1b is not None,
            state.runner_2b is not None,
            state.runner_3b is not None
        ]
        self.field_widget.set_runners(runners)

        # 打者・投手
        batter, _ = self.live_engine.get_current_batter()
        pitcher, _ = self.live_engine.get_current_pitcher()

        if batter:
            self.batter_label.setText(f"打者: {batter.name}")
        if pitcher:
            self.pitcher_label.setText(f"投手: {pitcher.name}")

    def _add_log(self, text: str, highlight: bool = False):
        """ログ追加"""
        label = QLabel(text)
        if highlight:
            label.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.theme.warning};")
        else:
            label.setStyleSheet(f"font-size: 11px; color: {self.theme.text_secondary};")

        self.log_layout.insertWidget(0, label)

        # 古いログを削除
        while self.log_layout.count() > 20:
            item = self.log_layout.takeAt(self.log_layout.count() - 1)
            if item.widget():
                item.widget().deleteLater()

    def _clear_log(self):
        """ログクリア"""
        while self.log_layout.count():
            item = self.log_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _on_game_finished(self):
        """試合終了"""
        self.sim_timer.stop()
        self.auto_btn.setChecked(False)

        winner = self.live_engine.get_winner()
        self._add_log(f"試合終了！ 勝者: {winner}", highlight=True)

        self.game_finished.emit({
            'home_score': self.live_engine.state.home_score,
            'away_score': self.live_engine.state.away_score,
            'home_team': self.live_engine.home_team,
            'away_team': self.live_engine.away_team,
            'winner': winner
        })
