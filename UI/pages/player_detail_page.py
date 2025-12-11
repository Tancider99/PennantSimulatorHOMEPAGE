# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Player Detail Page
Ultimate Dashboard: Hero Radar, Tabbed Season Stats, Full-Width Ability Bars
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout, QSizePolicy, QTabWidget,
    QGraphicsDropShadowEffect, QStyle, QSpacerItem
)
from PySide6.QtCore import Qt, Signal, QRect, QPointF
from PySide6.QtGui import (
    QFont, QColor, QPainter, QBrush, QPen, 
    QLinearGradient, QRadialGradient, QPolygonF, QPainterPath
)

import sys
import os
import math

# パス設定
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.panels import ToolbarPanel
from UI.widgets.charts import RadarChart
from models import PlayerStats

def safe_enum_val(obj):
    return obj.value if hasattr(obj, "value") else str(obj)

class VerticalStatBar(QWidget):
    """
    Full-width adaptable vertical stat bar
    """
    def __init__(self, label, value, max_value=99, parent=None):
        super().__init__(parent)
        self.label = label
        self.value = value
        self.max_value = max_value
        self.theme = get_theme()
        # サイズポリシーをExpandingにして横幅いっぱいに広がるようにする
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumWidth(60) # 最小幅

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        
        # エリア定義
        label_h = 20
        rank_h = 25
        val_h = 20
        bar_area_h = h - label_h - rank_h - val_h - 10
        bar_bottom_y = h - label_h - 5
        
        # バーの描画位置（ウィジェットの中央に描画）
        bar_w = 14
        bar_x = (w - bar_w) // 2
        
        # 背景バー
        painter.setBrush(QColor("#1e2126"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bar_x, rank_h + val_h + 5, bar_w, bar_area_h, 6, 6)
        
        # 値バー
        ratio = min(1.0, max(0.0, self.value / float(self.max_value)))
        fill_h = int(bar_area_h * ratio)
        fill_y = bar_bottom_y - fill_h
        
        stats = PlayerStats()
        color = QColor(stats.get_rank_color(self.value))
        
        painter.setBrush(color)
        painter.drawRoundedRect(bar_x, fill_y, bar_w, fill_h, 6, 6)
        
        # ラベル
        painter.setPen(QColor(self.theme.text_secondary))
        font_lbl = QFont("Yu Gothic UI", 9)
        painter.setFont(font_lbl)
        painter.drawText(QRect(0, h - label_h, w, label_h), Qt.AlignCenter, self.label)
        
        # ランク
        rank = stats.get_rank(self.value)
        painter.setPen(color)
        font_rank = QFont("Segoe UI", 16, QFont.Black)
        painter.setFont(font_rank)
        painter.drawText(QRect(0, 0, w, rank_h), Qt.AlignCenter, rank)
        
        # 数値
        painter.setPen(Qt.white)
        font_val = QFont("Consolas", 11, QFont.Bold)
        painter.setFont(font_val)
        painter.drawText(QRect(0, rank_h, w, val_h), Qt.AlignCenter, str(self.value))

class SeasonStatsWidget(QWidget):
    """
    Tabbed Season Stats Panel (1st, 2nd, 3rd)
    """
    detail_requested = Signal()

    def __init__(self, player, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.player = player
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # タブ作成
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {self.theme.border_muted}; background: transparent; }}
            QTabBar::tab {{ 
                background: {self.theme.bg_card}; 
                color: {self.theme.text_muted};
                padding: 6px 12px;
                min-width: 60px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{ 
                background: {self.theme.bg_card_elevated}; 
                color: {self.theme.primary};
                border-bottom: 2px solid {self.theme.primary};
            }}
        """)
        
        # 1軍成績
        tabs.addTab(self._create_stats_grid(self.player.record, is_pitcher=(self.player.position.value=="投手")), "一軍")
        
        # 2軍成績
        rec_farm = getattr(self.player, "record_farm", None)
        tabs.addTab(self._create_stats_grid(rec_farm, is_pitcher=(self.player.position.value=="投手")), "二軍")
        
        # 3軍成績
        rec_third = getattr(self.player, "record_third", None) 
        tabs.addTab(self._create_stats_grid(rec_third, is_pitcher=(self.player.position.value=="投手")), "三軍")
        
        layout.addWidget(tabs)
        
        # 詳細ボタン
        btn = QPushButton("詳細統計を見る")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.theme.accent_blue};
                border: 1px solid {self.theme.accent_blue};
                padding: 6px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {self.theme.accent_blue}; color: white; }}
        """)
        btn.clicked.connect(self.detail_requested.emit)
        layout.addWidget(btn)

    def _create_stats_grid(self, record, is_pitcher):
        container = QWidget()
        if record is None:
            l = QVBoxLayout(container)
            l.addWidget(QLabel("データなし", alignment=Qt.AlignCenter, styleSheet="color: #666;"))
            return container

        layout = QGridLayout(container)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        if is_pitcher:
            data = [
                ("防御率", f"{record.era:.2f}"), ("登板", record.games_pitched),
                ("勝利", record.wins), ("敗戦", record.losses),
                ("セーブ", record.saves), ("奪三振", record.strikeouts_pitched)
            ]
        else:
            data = [
                ("打率", f".{int(record.batting_average*1000):03d}"), ("試合", record.games),
                ("本塁打", record.home_runs), ("打点", record.rbis),
                ("盗塁", record.stolen_bases), ("OPS", f"{record.ops:.3f}")
            ]
            
        for i, (k, v) in enumerate(data):
            lbl_k = QLabel(k)
            lbl_k.setStyleSheet("font-size: 10px; color: #888;")
            lbl_v = QLabel(str(v))
            lbl_v.setStyleSheet("font-size: 14px; font-weight: bold; color: #fff; font-family: 'Consolas';")
            
            layout.addWidget(lbl_k, i//2 * 2, i%2)
            layout.addWidget(lbl_v, i//2 * 2 + 1, i%2)
            
        return container

# --- Main Page Class ---

class PlayerDetailPage(QWidget):
    """
    Refined Layout: 
    - Global Radar Chart (No vertex dots, No Center OVR)
    - OVR in Top-Right
    - All Abilities Displayed
    """
    back_requested = Signal()
    detail_stats_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.current_player = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setStyleSheet(f"background-color: {self.theme.bg_dark}; color: #ffffff;")

        # Toolbar
        layout.addWidget(self._create_toolbar())

        # Main Content
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(30, 20, 30, 30)
        self.content_layout.setSpacing(20)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)
        
        self.placeholder = QLabel("SELECT A PLAYER")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet("font-size: 24px; color: #555; font-weight: bold;")
        self.content_layout.addWidget(self.placeholder)

    def set_player(self, player):
        self.current_player = player
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        if not player:
            self.content_layout.addWidget(self.placeholder)
            return

        self._build_dashboard(player)

    def _create_toolbar(self) -> ToolbarPanel:
        toolbar = ToolbarPanel()
        toolbar.setFixedHeight(50)
        toolbar.setStyleSheet(f"background-color: {self.theme.bg_header}; border-bottom: 1px solid #333;")
        
        back_btn = QPushButton(" BACK")
        back_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowBack))
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setStyleSheet("QPushButton { background: transparent; color: #aaa; font-weight: bold; border: none; } QPushButton:hover { color: #fff; }")
        back_btn.clicked.connect(self._on_back)
        toolbar.add_widget(back_btn)
        
        toolbar.add_separator()
        toolbar.add_widget(QLabel("PLAYER PROFILE", styleSheet="font-weight: bold; color: #fff;"))
        toolbar.add_stretch()
        return toolbar

    def _build_dashboard(self, player):
        # === TOP SECTION (Radar + Info/Stats) ===
        top_section = QWidget()
        top_layout = QHBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(30)
        
        # 1. Left: Unified Radar Chart
        radar = RadarChart() # from UI.widgets.charts
        is_pitcher = (player.position.value == "投手")
        radar.set_player_stats(player, is_pitcher)
        top_layout.addWidget(radar, 2)
        
        # 2. Right: Info & OVR & Stats
        right_panel = QWidget()
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(0, 10, 0, 0)
        
        # Header (Name + OVR)
        header_h = QHBoxLayout()
        name_v = QVBoxLayout()
        name_lbl = QLabel(player.name.upper())
        name_lbl.setStyleSheet("font-size: 42px; font-weight: 900; color: #fff; font-family: 'Segoe UI';")
        sub_info = QLabel(f"#{player.uniform_number} | {safe_enum_val(player.position)} | {player.bats}打{player.throws}投 | {player.age}歳")
        sub_info.setStyleSheet("font-size: 16px; color: #5fbcd3; font-weight: bold;")
        name_v.addWidget(name_lbl)
        name_v.addWidget(sub_info)
        header_h.addLayout(name_v)
        
        header_h.addStretch()
        
        # OVR Display (Top Right)
        ovr_v = QVBoxLayout()
        ovr_val = QLabel(f"{player.overall_rating}")
        stats_util = PlayerStats()
        ovr_color = stats_util.get_rank_color(player.overall_rating)
        ovr_val.setStyleSheet(f"font-size: 48px; font-weight: 900; color: {ovr_color}; font-family: 'Segoe UI';")
        ovr_lbl = QLabel("OVR")
        ovr_lbl.setStyleSheet("font-size: 12px; font-weight: bold; color: #888;")
        ovr_lbl.setAlignment(Qt.AlignCenter)
        ovr_v.addWidget(ovr_val, alignment=Qt.AlignCenter)
        ovr_v.addWidget(ovr_lbl, alignment=Qt.AlignCenter)
        header_h.addLayout(ovr_v)
        
        rp_layout.addLayout(header_h)
        rp_layout.addSpacing(15)
        
        # Stats Widget (Tabbed)
        stats_widget = SeasonStatsWidget(player)
        stats_widget.detail_requested.connect(self._on_detail_stats)
        rp_layout.addWidget(stats_widget)
        
        rp_layout.addStretch()
        top_layout.addWidget(right_panel, 3)
        
        self.content_layout.addWidget(top_section, 4)

        # === BOTTOM SECTION (Tabbed Abilities - Full Width & All Stats) ===
        bottom_tabs = QTabWidget()
        bottom_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{ 
                background: transparent; color: #666; font-size: 14px; font-weight: bold; padding: 10px 20px;
            }}
            QTabBar::tab:selected {{ color: #fff; border-bottom: 2px solid #5fbcd3; }}
        """)
        
        self.content_layout.addWidget(bottom_tabs, 3)
        
        stats = player.stats
        
        # タブごとのデータ定義 (全能力網羅)
        if is_pitcher:
            # 投手: 基礎
            pitch_basic = [
                ("球速", stats.velocity, 165), ("制球", stats.control, 99),
                ("スタミナ", stats.stamina, 99), ("球威", stats.stuff, 99),
                ("変化量", stats.movement, 99), ("安定度", stats.stability, 99)
            ]
            # 投手: 特殊・メンタル
            pitch_spec = [
                ("対左打者", stats.vs_left_pitcher, 99), ("対ピンチ", stats.vs_pinch, 99),
                ("打球反応", stats.gb_tendency, 99), ("クイック", stats.hold_runners, 99),
                ("メンタル", stats.mental, 99), ("野球脳", stats.intelligence, 99),
                ("回復", stats.recovery, 99), ("ケガ耐性", stats.durability, 99),
                ("練習態度", stats.work_ethic, 99)
            ]
            # 投手: 守備・その他
            pitch_fld = [
                ("守備力", stats.fielding, 99), ("肩力", stats.arm, 99), # 投手も守備あり
                ("捕球", stats.error, 99), ("バント", stats.bunt_sac, 99)
            ]
            
            bottom_tabs.addTab(self._create_full_tab(pitch_basic), "PITCHING BASIC")
            bottom_tabs.addTab(self._create_full_tab(pitch_spec), "SPECIAL / MENTAL")
            bottom_tabs.addTab(self._create_full_tab(pitch_fld), "FIELDING / OTHER")
            
        else:
            # 野手: 打撃
            bat_basic = [
                ("ミート", stats.contact, 99), ("パワー", stats.power, 99),
                ("ギャップ", stats.gap, 99), ("弾道", stats.trajectory, 4),
                ("選球眼", stats.eye, 99), ("三振回避", stats.avoid_k, 99)
            ]
            # 野手: 特殊打撃・走塁
            bat_spec = [
                ("対左投手", stats.vs_left_batter, 99), ("チャンス", stats.chance, 99),
                ("バント", stats.bunt_sac, 99), ("バント安打", stats.bunt_hit, 99),
                ("走力", stats.speed, 99), ("盗塁", stats.steal, 99),
                ("走塁技術", stats.baserunning, 99)
            ]
            # 野手: 守備・メンタル・その他
            fld_men = [
                ("守備力", stats.fielding, 99), ("捕球", stats.error, 99),
                ("肩力", stats.arm, 99), ("送球安定", getattr(stats, 'stability', 50), 99),
                ("併殺処理", stats.turn_dp, 99), ("リード", stats.catcher_lead, 99), # 捕手用だが全表示
                ("メンタル", stats.mental, 99), ("野球脳", stats.intelligence, 99),
                ("回復", stats.recovery, 99), ("ケガ耐性", stats.durability, 99),
                ("練習態度", stats.work_ethic, 99)
            ]
            
            bottom_tabs.addTab(self._create_full_tab(bat_basic), "BATTING")
            bottom_tabs.addTab(self._create_full_tab(bat_spec), "SPECIAL / RUNNING")
            bottom_tabs.addTab(self._create_full_tab(fld_men), "FIELDING / MENTAL")

    def _create_full_tab(self, items):
        tab_widget = QWidget()
        tab_layout = QHBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 10, 0, 0)
        tab_layout.setSpacing(10)
        
        for lbl, val, max_v in items:
            # 弾道の特殊処理
            disp_val = val
            if lbl == "弾道":
                # 見た目はそのまま、ランクなどはVerticalStatBar内で処理
                pass
            
            bar = VerticalStatBar(lbl, disp_val, max_v)
            tab_layout.addWidget(bar)
            
        return tab_widget

    def _on_back(self):
        self.back_requested.emit()

    def _on_detail_stats(self):
        if self.current_player:
            self.detail_stats_requested.emit(self.current_player)