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
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumWidth(60)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        
        label_h = 20
        rank_h = 25
        val_h = 20
        bar_area_h = h - label_h - rank_h - val_h - 10
        bar_bottom_y = h - label_h - 5
        
        bar_w = 14
        bar_x = (w - bar_w) // 2
        
        painter.setBrush(QColor("#1e2126"))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bar_x, rank_h + val_h + 5, bar_w, bar_area_h, 6, 6)
        
        if self.label == "球速":
            ratio = min(1.0, max(0.0, (self.value - 120) / (170 - 120)))
        else:
            ratio = min(1.0, max(0.0, self.value / float(self.max_value)))
        fill_h = int(bar_area_h * ratio)
        fill_y = bar_bottom_y - fill_h
        
        stats = PlayerStats()
        
        is_trajectory = (self.label == "弾道")
        is_velocity = (self.label == "球速")
        
        if is_trajectory:
            if self.value == 1: color = QColor("#4488FF")
            elif self.value == 2: color = QColor("#88FF44")
            elif self.value == 3: color = QColor("#FF8800")
            else: color = QColor("#FF4444")
            rank_text = "" 
        else:
            color = QColor(stats.get_rank_color(self.value))
            rank_text = stats.get_rank(self.value)
        
        painter.setBrush(color)
        painter.drawRoundedRect(bar_x, fill_y, bar_w, fill_h, 6, 6)
        
        painter.setPen(QColor(self.theme.text_secondary))
        font_lbl = QFont("Yu Gothic UI", 9)
        painter.setFont(font_lbl)
        painter.drawText(QRect(0, h - label_h, w, label_h), Qt.AlignCenter, self.label)
        
        if not is_trajectory and not is_velocity:
            painter.setPen(color)
            font_rank = QFont("Segoe UI", 16, QFont.Black)
            painter.setFont(font_rank)
            painter.drawText(QRect(0, 0, w, rank_h), Qt.AlignCenter, rank_text)
        
        painter.setPen(Qt.white)
        font_size = 14 if is_trajectory else 11
        font_val = QFont("Consolas", font_size, QFont.Bold)
        painter.setFont(font_val)
        
        val_rect_y = 0 if (is_trajectory or is_velocity) else rank_h
        val_rect_h = rank_h + val_h if (is_trajectory or is_velocity) else val_h
        
        painter.drawText(QRect(0, val_rect_y, w, val_rect_h), Qt.AlignCenter, str(self.value))

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
        
        tabs.addTab(self._create_stats_grid(self.player.record, is_pitcher=(self.player.position.value=="投手")), "一軍")
        
        rec_farm = getattr(self.player, "record_farm", None)
        tabs.addTab(self._create_stats_grid(rec_farm, is_pitcher=(self.player.position.value=="投手")), "二軍")
        
        rec_third = getattr(self.player, "record_third", None) 
        tabs.addTab(self._create_stats_grid(rec_third, is_pitcher=(self.player.position.value=="投手")), "三軍")
        
        layout.addWidget(tabs)
        
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

        layout.addWidget(self._create_toolbar())

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

    def set_player(self, player, team_name=None):
        self.current_player = player
        self.current_team_name = team_name
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
        top_section = QWidget()
        top_layout = QHBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(30)
        
        radar = RadarChart() 
        is_pitcher = (player.position.value == "投手")
        radar.set_player_stats(player, is_pitcher)
        top_layout.addWidget(radar, 2)
        
        right_panel = QWidget()
        rp_layout = QVBoxLayout(right_panel)
        rp_layout.setContentsMargins(0, 10, 0, 0)
        
        header_h = QHBoxLayout()
        name_v = QVBoxLayout()
        name_lbl = QLabel(player.name.upper())
        name_lbl.setStyleSheet("font-size: 42px; font-weight: 900; color: #fff; font-family: 'Segoe UI';")
        
        t_str = f"[{self.current_team_name}] " if getattr(self, 'current_team_name', None) else ""
        sub_info = QLabel(f"{t_str}#{player.uniform_number} | {safe_enum_val(player.position)} | {player.bats}打{player.throws}投 | {player.age}歳")
        sub_info.setStyleSheet("font-size: 16px; color: #5fbcd3; font-weight: bold;")
        name_v.addWidget(name_lbl)
        name_v.addWidget(sub_info)
        header_h.addLayout(name_v)
        
        header_h.addStretch()
        
        ovr_v = QVBoxLayout()
        ovr_val = QLabel(f"★ {player.overall_rating}")
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
        
        stats_widget = SeasonStatsWidget(player)
        stats_widget.detail_requested.connect(self._on_detail_stats)
        rp_layout.addWidget(stats_widget)
        
        rp_layout.addStretch()
        top_layout.addWidget(right_panel, 3)
        
        self.content_layout.addWidget(top_section, 3)

        bottom_tabs = QTabWidget()
        bottom_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{ 
                background: transparent; color: #666; font-size: 14px; font-weight: bold; padding: 10px 20px;
            }}
            QTabBar::tab:selected {{ color: #fff; border-bottom: 2px solid #5fbcd3; }}
        """)
        
        self.content_layout.addWidget(bottom_tabs, 5)
        
        stats = player.stats
        
        if is_pitcher:
            pitch_basic = [
                ("球速", stats.velocity, 170), ("制球", stats.control, 99),
                ("スタミナ", stats.stamina, 99), ("球威", stats.stuff, 99),
                ("変化量", stats.movement, 99), ("安定度", stats.stability, 99)
            ]
            pitch_spec = [
                ("対左打者", stats.vs_left_pitcher, 99), ("対ピンチ", stats.vs_pinch, 99),
                ("クイック", stats.hold_runners, 99)
            ]
            pitch_fld = [
                ("守備力", stats.fielding, 99), ("肩力", stats.arm, 99),
                ("捕球", stats.error, 99), ("打球反応", stats.gb_tendency, 99), 
                ("バント", stats.bunt_sac, 99)
            ]
            pitch_mental = [
                ("メンタル", stats.mental, 99), ("野球脳", stats.intelligence, 99),
                ("回復", stats.recovery, 99), ("ケガ耐性", stats.durability, 99),
                ("練習態度", stats.work_ethic, 99)
            ]
            
            bottom_tabs.addTab(self._create_full_tab(pitch_basic), "PITCHING BASIC")
            
            # ★追加: 球種タブ (球種ごとのパラメータ表示)
            pitch_types_widget = QWidget()
            pt_layout = QHBoxLayout(pitch_types_widget)
            pt_layout.setContentsMargins(0, 10, 0, 0)
            pt_layout.setSpacing(10)
            
            if stats.pitches:
                for p_name in stats.pitches.keys():
                    qual = stats.get_pitch_quality(p_name)
                    stf = stats.get_pitch_stuff(p_name)
                    mov = stats.get_pitch_movement(p_name)
                    
                    # 1球種につき3本のバーを表示するためのコンテナ
                    p_box = QFrame()
                    p_box.setStyleSheet("background: #222; border-radius: 6px;")
                    vb = QVBoxLayout(p_box)
                    vb.setContentsMargins(5,5,5,5)
                    
                    lbl = QLabel(p_name)
                    lbl.setAlignment(Qt.AlignCenter)
                    lbl.setStyleSheet("color: #ccc; font-weight: bold; font-size: 11px;")
                    vb.addWidget(lbl)
                    
                    h_bars = QHBoxLayout()
                    h_bars.setSpacing(4)
                    h_bars.addWidget(VerticalStatBar("精度", qual, 99))
                    h_bars.addWidget(VerticalStatBar("球威", stf, 99))
                    h_bars.addWidget(VerticalStatBar("変化", mov, 99))
                    vb.addLayout(h_bars)
                    
                    pt_layout.addWidget(p_box)
                pt_layout.addStretch()
            else:
                pt_layout.addWidget(QLabel("変化球なし", styleSheet="color:#666;"))
                
            bottom_tabs.addTab(pitch_types_widget, "PITCHES")
            
            bottom_tabs.addTab(self._create_full_tab(pitch_spec), "SPECIAL")
            bottom_tabs.addTab(self._create_full_tab(pitch_fld), "FIELDING")
            bottom_tabs.addTab(self._create_full_tab(pitch_mental), "MENTAL / OTHER")
            
        else:
            bat_basic = [
                ("弾道", stats.trajectory, 4), 
                ("ミート", stats.contact, 99), ("パワー", stats.power, 99),
                ("ギャップ", stats.gap, 99), 
                ("選球眼", stats.eye, 99), ("三振回避", stats.avoid_k, 99)
            ]
            bat_spec = [
                ("対左投手", stats.vs_left_batter, 99), ("チャンス", stats.chance, 99),
                ("バント", stats.bunt_sac, 99), ("バント安打", stats.bunt_hit, 99),
                ("走力", stats.speed, 99), ("盗塁", stats.steal, 99),
                ("走塁技術", stats.baserunning, 99)
            ]
            fld_list = [
                ("捕球", stats.error, 99),
                ("肩力", stats.arm, 99), ("送球安定", getattr(stats, 'stability', 50), 99),
                ("併殺処理", stats.turn_dp, 99)
            ]
            if safe_enum_val(player.position) == "捕手":
                fld_list.append(("リード", stats.catcher_lead, 99))
            
            if hasattr(stats, 'defense_ranges'):
                for pos_name, val in stats.defense_ranges.items():
                    if val > 0:
                        fld_list.append((f"守備({pos_name})", val, 99))

            mental_list = [
                ("メンタル", stats.mental, 99), ("野球脳", stats.intelligence, 99),
                ("回復", stats.recovery, 99), ("ケガ耐性", stats.durability, 99),
                ("練習態度", stats.work_ethic, 99)
            ]
            
            bottom_tabs.addTab(self._create_full_tab(bat_basic), "BATTING")
            bottom_tabs.addTab(self._create_full_tab(bat_spec), "SPECIAL / RUNNING")
            bottom_tabs.addTab(self._create_full_tab(fld_list), "FIELDING")
            bottom_tabs.addTab(self._create_full_tab(mental_list), "MENTAL / OTHER")

    def _create_full_tab(self, items):
        tab_widget = QWidget()
        tab_layout = QHBoxLayout(tab_widget)
        tab_layout.setContentsMargins(0, 10, 0, 0)
        tab_layout.setSpacing(10)
        
        for lbl, val, max_v in items:
            bar = VerticalStatBar(lbl, val, max_v)
            tab_layout.addWidget(bar)
            
        return tab_widget

    def _on_back(self):
        self.back_requested.emit()

    def _on_detail_stats(self):
        if self.current_player:
            self.detail_stats_requested.emit(self.current_player)