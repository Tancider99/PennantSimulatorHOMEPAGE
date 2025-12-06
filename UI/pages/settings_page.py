# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Settings Page
OOTP-Style Professional Settings Interface with Premium Design
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QSlider, QPushButton, QFrame, QSpinBox,
    QTabWidget, QScrollArea, QMessageBox, QFileDialog,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme, ThemeManager
from UI.widgets.cards import Card, PremiumCard
from UI.widgets.panels import ContentPanel
from UI.widgets.buttons import ActionButton


class SettingRow(QFrame):
    """A premium setting row with label and control"""

    def __init__(self, label: str, description: str = "", parent=None):
        super().__init__(parent)
        self.theme = get_theme()

        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated}, stop:1 {self.theme.bg_card});
                border: 1px solid {self.theme.border_muted};
                border-radius: 0px;
                margin: 2px 0px;
            }}
            QFrame:hover {{
                border-color: {self.theme.primary};
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_hover}, stop:1 {self.theme.bg_card_elevated});
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        # Label and description
        label_widget = QWidget()
        label_layout = QVBoxLayout(label_widget)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(4)

        self.label = QLabel(label)
        self.label.setStyleSheet(f"""
            color: {self.theme.text_primary};
            font-size: 14px;
            font-weight: 600;
            background: transparent;
            border: none;
        """)
        label_layout.addWidget(self.label)

        if description:
            self.desc = QLabel(description)
            self.desc.setStyleSheet(f"""
                color: {self.theme.text_muted};
                font-size: 12px;
                background: transparent;
                border: none;
            """)
            self.desc.setWordWrap(True)
            label_layout.addWidget(self.desc)

        layout.addWidget(label_widget, stretch=1)

        # Control widget placeholder
        self.control_layout = QHBoxLayout()
        layout.addLayout(self.control_layout)

    def set_control(self, widget):
        """Set the control widget"""
        self.control_layout.addWidget(widget)


class SettingsPage(ContentPanel):
    """Settings page with premium game configuration"""

    settings_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.settings = {}

        self._setup_ui()
        self._load_defaults()

    def _setup_ui(self):
        """Create the premium settings page layout"""
        # Header with gradient
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.bg_card}, stop:1 {self.theme.bg_card_elevated});
                border: 1px solid {self.theme.border};
                border-radius: 16px;
            }}
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(24, 20, 24, 20)

        # Title with icon
        title_layout = QVBoxLayout()
        title = QLabel("設定")
        title.setStyleSheet(f"""
            font-size: 28px;
            font-weight: 700;
            color: {self.theme.text_primary};
        """)
        subtitle = QLabel("ゲームとUIの設定をカスタマイズ")
        subtitle.setStyleSheet(f"""
            font-size: 14px;
            color: {self.theme.text_secondary};
        """)
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        # Reset button with premium style
        reset_btn = QPushButton("デフォルトに戻す")
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_hover}, stop:1 {self.theme.bg_card});
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.danger_light}, stop:1 {self.theme.danger});
                border-color: {self.theme.danger};
                color: white;
            }}
        """)
        reset_btn.clicked.connect(self._reset_settings)
        header_layout.addWidget(reset_btn)

        self.add_widget(header_frame)

        # Tabs with premium styling
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: transparent;
                border: none;
            }}
            QTabBar::tab {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card}, stop:1 {self.theme.bg_dark});
                color: {self.theme.text_secondary};
                border: 1px solid {self.theme.border};
                border-bottom: none;
                padding: 14px 28px;
                margin-right: 4px;
                border-radius: 0px;
                font-size: 14px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.primary}, stop:1 {self.theme.primary_dark});
                color: white;
                border-color: {self.theme.primary};
            }}
            QTabBar::tab:hover:!selected {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_hover}, stop:1 {self.theme.bg_card});
                color: {self.theme.text_primary};
            }}
        """)

        # Create tabs
        tabs.addTab(self._create_display_tab(), "画面表示")
        tabs.addTab(self._create_game_tab(), "ゲーム")
        tabs.addTab(self._create_sim_tab(), "シミュレーション")
        tabs.addTab(self._create_audio_tab(), "サウンド")
        tabs.addTab(self._create_save_tab(), "セーブ/ロード")

        self.add_widget(tabs)

        # Apply button at bottom
        apply_layout = QHBoxLayout()
        apply_layout.addStretch()

        self.apply_btn = QPushButton("設定を適用")
        self.apply_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.success_light}, stop:1 {self.theme.success});
                color: white;
                border: none;
                border-radius: 10px;
                padding: 14px 40px;
                font-size: 16px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.success_hover}, stop:1 {self.theme.success_light});
            }}
        """)
        self.apply_btn.clicked.connect(self._apply_settings)
        apply_layout.addWidget(self.apply_btn)

        self.add_layout(apply_layout)

    def _create_display_tab(self) -> QWidget:
        """Create display/window settings tab - FIRST TAB"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(8, 16, 8, 16)

        # Window Size Card
        window_card = PremiumCard("ウィンドウサイズ", "")

        # Window size preset
        row = SettingRow("ウィンドウサイズ", "ウィンドウの大きさを選択")
        self.window_size_combo = QComboBox()
        self.window_size_combo.addItems([
            "1280 x 720 (HD)",
            "1366 x 768",
            "1600 x 900",
            "1920 x 1080 (Full HD)",
            "2560 x 1440 (QHD)",
            "3840 x 2160 (4K)"
        ])
        self.window_size_combo.setCurrentIndex(3)
        self.window_size_combo.setMinimumWidth(200)
        row.set_control(self.window_size_combo)
        window_card.add_widget(row)

        # Fullscreen
        row = SettingRow("フルスクリーン", "F11キーでも切替可能")
        self.fullscreen_check = QCheckBox()
        row.set_control(self.fullscreen_check)
        window_card.add_widget(row)

        # Start maximized
        row = SettingRow("起動時に最大化", "ゲーム起動時にウィンドウを最大化")
        self.start_maximized_check = QCheckBox()
        row.set_control(self.start_maximized_check)
        window_card.add_widget(row)

        layout.addWidget(window_card)

        # UI Scale Card
        scale_card = PremiumCard("UIスケール", "")

        # UI Scale
        row = SettingRow("UIサイズ", "文字やボタンの大きさを調整")
        scale_layout = QHBoxLayout()
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(80, 150)
        self.scale_slider.setValue(100)
        self.scale_slider.setFixedWidth(180)
        self.scale_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {self.theme.bg_input};
                height: 8px;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.primary_light}, stop:1 {self.theme.primary});
                width: 20px;
                height: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.primary_dark}, stop:1 {self.theme.primary});
                border-radius: 4px;
            }}
        """)
        scale_layout.addWidget(self.scale_slider)
        self.scale_label = QLabel("100%")
        self.scale_label.setStyleSheet(f"""
            font-weight: 700;
            font-size: 14px;
            color: {self.theme.primary_light};
            min-width: 50px;
            background: transparent;
            border: none;
        """)
        scale_layout.addWidget(self.scale_label)
        self.scale_slider.valueChanged.connect(
            lambda v: self.scale_label.setText(f"{v}%")
        )
        row.control_layout.addLayout(scale_layout)
        scale_card.add_widget(row)

        layout.addWidget(scale_card)

        # Theme Card
        theme_card = PremiumCard("テーマ設定", "")

        # Theme
        row = SettingRow("テーマ", "UIの外観を変更")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["ダーク（OOTP風）", "ダークブルー", "ミッドナイト", "クラシック"])
        self.theme_combo.setCurrentIndex(0)
        self.theme_combo.setMinimumWidth(180)
        row.set_control(self.theme_combo)
        theme_card.add_widget(row)

        # Language
        row = SettingRow("言語", "表示言語を変更")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["日本語", "English"])
        self.lang_combo.setCurrentIndex(0)
        self.lang_combo.setMinimumWidth(180)
        row.set_control(self.lang_combo)
        theme_card.add_widget(row)

        # Font size
        row = SettingRow("フォントサイズ", "テキストの大きさ")
        self.font_combo = QComboBox()
        self.font_combo.addItems(["小", "中", "大", "特大"])
        self.font_combo.setCurrentIndex(1)
        self.font_combo.setMinimumWidth(180)
        row.set_control(self.font_combo)
        theme_card.add_widget(row)

        layout.addWidget(theme_card)

        # Stats Display Card
        stats_card = PremiumCard("統計表示", "")

        # Show advanced stats
        row = SettingRow("高度な統計", "WAR、OPS+などの詳細統計を表示")
        self.adv_stats_check = QCheckBox()
        self.adv_stats_check.setChecked(True)
        row.set_control(self.adv_stats_check)
        stats_card.add_widget(row)

        # Rating system
        row = SettingRow("能力表示", "選手能力の表示方法")
        self.rating_combo = QComboBox()
        self.rating_combo.addItems(["数値 (1-99)", "ランク (S-G)", "星", "グラフ"])
        self.rating_combo.setCurrentIndex(0)
        self.rating_combo.setMinimumWidth(180)
        row.set_control(self.rating_combo)
        stats_card.add_widget(row)

        layout.addWidget(stats_card)
        layout.addStretch()

        scroll.setWidget(widget)
        return scroll

    def _create_game_tab(self) -> QWidget:
        """Create game settings tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(8, 16, 8, 16)

        # Difficulty card
        diff_card = PremiumCard("難易度", "")

        # Difficulty level
        row = SettingRow("ゲーム難易度", "AI球団の強さを調整")
        self.difficulty_combo = QComboBox()
        self.difficulty_combo.addItems(["ルーキー", "レギュラー", "ベテラン", "オールスター", "殿堂入り"])
        self.difficulty_combo.setCurrentIndex(2)
        self.difficulty_combo.setMinimumWidth(180)
        row.set_control(self.difficulty_combo)
        diff_card.add_widget(row)

        # Trade difficulty
        row = SettingRow("トレード難易度", "相手球団がトレードに応じやすさ")
        self.trade_diff_combo = QComboBox()
        self.trade_diff_combo.addItems(["簡単", "普通", "難しい", "リアル"])
        self.trade_diff_combo.setCurrentIndex(1)
        self.trade_diff_combo.setMinimumWidth(180)
        row.set_control(self.trade_diff_combo)
        diff_card.add_widget(row)

        # FA difficulty
        row = SettingRow("FA獲得難易度", "FA選手の獲得しやすさ")
        self.fa_diff_combo = QComboBox()
        self.fa_diff_combo.addItems(["簡単", "普通", "難しい", "リアル"])
        self.fa_diff_combo.setCurrentIndex(1)
        self.fa_diff_combo.setMinimumWidth(180)
        row.set_control(self.fa_diff_combo)
        diff_card.add_widget(row)

        layout.addWidget(diff_card)

        # Season settings card
        season_card = PremiumCard("シーズン設定", "")

        # Games per season
        row = SettingRow("試合数", "1シーズンあたりの試合数")
        self.games_spin = QSpinBox()
        self.games_spin.setRange(30, 143)
        self.games_spin.setValue(143)
        self.games_spin.setMinimumWidth(100)
        row.set_control(self.games_spin)
        season_card.add_widget(row)

        # DH rule
        row = SettingRow("DH制", "指名打者ルールを使用")
        self.dh_check = QCheckBox()
        self.dh_check.setChecked(True)
        row.set_control(self.dh_check)
        season_card.add_widget(row)

        # Interleague
        row = SettingRow("交流戦", "セ・パ交流戦を開催")
        self.interleague_check = QCheckBox()
        self.interleague_check.setChecked(True)
        row.set_control(self.interleague_check)
        season_card.add_widget(row)

        layout.addWidget(season_card)

        # Roster settings card
        roster_card = PremiumCard("ロスター設定", "")

        # Roster limit
        row = SettingRow("1軍登録人数", "1軍に登録できる選手の上限")
        self.roster_limit_spin = QSpinBox()
        self.roster_limit_spin.setRange(25, 40)
        self.roster_limit_spin.setValue(28)
        self.roster_limit_spin.setMinimumWidth(100)
        row.set_control(self.roster_limit_spin)
        roster_card.add_widget(row)

        # Injuries
        row = SettingRow("故障発生", "選手の故障が発生")
        self.injuries_check = QCheckBox()
        self.injuries_check.setChecked(True)
        row.set_control(self.injuries_check)
        roster_card.add_widget(row)

        layout.addWidget(roster_card)
        layout.addStretch()

        scroll.setWidget(widget)
        return scroll

    def _create_sim_tab(self) -> QWidget:
        """Create simulation settings tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(8, 16, 8, 16)

        # Simulation card
        sim_card = PremiumCard("シミュレーション設定", "")

        # Simulation speed
        row = SettingRow("シミュレーション速度", "自動進行時の速度")
        speed_layout = QHBoxLayout()
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 10)
        self.speed_slider.setValue(5)
        self.speed_slider.setFixedWidth(150)
        speed_layout.addWidget(self.speed_slider)
        self.speed_label = QLabel("5x")
        self.speed_label.setStyleSheet(f"""
            font-weight: 700;
            color: {self.theme.primary_light};
            min-width: 40px;
            background: transparent;
            border: none;
        """)
        speed_layout.addWidget(self.speed_label)
        self.speed_slider.valueChanged.connect(
            lambda v: self.speed_label.setText(f"{v}x")
        )
        row.control_layout.addLayout(speed_layout)
        sim_card.add_widget(row)

        # Auto-advance
        row = SettingRow("自動進行", "試合を自動的に進行")
        self.auto_advance_check = QCheckBox()
        self.auto_advance_check.setChecked(True)
        row.set_control(self.auto_advance_check)
        sim_card.add_widget(row)

        # Show play-by-play
        row = SettingRow("プレイバイプレイ表示", "打席ごとの詳細を表示")
        self.pbp_check = QCheckBox()
        self.pbp_check.setChecked(True)
        row.set_control(self.pbp_check)
        sim_card.add_widget(row)

        layout.addWidget(sim_card)

        # Physics card
        physics_card = PremiumCard("物理演算", "")

        # Realistic physics
        row = SettingRow("リアル物理演算", "打球の軌道を物理的に計算")
        self.physics_check = QCheckBox()
        self.physics_check.setChecked(True)
        row.set_control(self.physics_check)
        physics_card.add_widget(row)

        # Wind effect
        row = SettingRow("風の影響", "風がボールに影響を与える")
        self.wind_check = QCheckBox()
        self.wind_check.setChecked(True)
        row.set_control(self.wind_check)
        physics_card.add_widget(row)

        layout.addWidget(physics_card)

        # AI settings card
        ai_card = PremiumCard("AI設定", "")

        # AI aggressiveness
        row = SettingRow("AI積極性", "AIの采配の積極性")
        self.ai_aggr_combo = QComboBox()
        self.ai_aggr_combo.addItems(["消極的", "普通", "積極的", "非常に積極的"])
        self.ai_aggr_combo.setCurrentIndex(1)
        self.ai_aggr_combo.setMinimumWidth(180)
        row.set_control(self.ai_aggr_combo)
        ai_card.add_widget(row)

        layout.addWidget(ai_card)
        layout.addStretch()

        scroll.setWidget(widget)
        return scroll

    def _create_audio_tab(self) -> QWidget:
        """Create audio settings tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(8, 16, 8, 16)

        # Audio card
        audio_card = PremiumCard("サウンド設定", "")

        # Master volume
        row = SettingRow("マスター音量", "全体の音量")
        volume_layout = QHBoxLayout()
        self.master_slider = QSlider(Qt.Horizontal)
        self.master_slider.setRange(0, 100)
        self.master_slider.setValue(80)
        self.master_slider.setFixedWidth(150)
        volume_layout.addWidget(self.master_slider)
        self.master_label = QLabel("80%")
        self.master_label.setStyleSheet(f"""
            font-weight: 700;
            color: {self.theme.primary_light};
            min-width: 50px;
            background: transparent;
            border: none;
        """)
        volume_layout.addWidget(self.master_label)
        self.master_slider.valueChanged.connect(
            lambda v: self.master_label.setText(f"{v}%")
        )
        row.control_layout.addLayout(volume_layout)
        audio_card.add_widget(row)

        # BGM volume
        row = SettingRow("BGM音量", "背景音楽の音量")
        bgm_layout = QHBoxLayout()
        self.bgm_slider = QSlider(Qt.Horizontal)
        self.bgm_slider.setRange(0, 100)
        self.bgm_slider.setValue(70)
        self.bgm_slider.setFixedWidth(150)
        bgm_layout.addWidget(self.bgm_slider)
        self.bgm_label = QLabel("70%")
        self.bgm_label.setStyleSheet(f"""
            font-weight: 700;
            color: {self.theme.primary_light};
            min-width: 50px;
            background: transparent;
            border: none;
        """)
        bgm_layout.addWidget(self.bgm_label)
        self.bgm_slider.valueChanged.connect(
            lambda v: self.bgm_label.setText(f"{v}%")
        )
        row.control_layout.addLayout(bgm_layout)
        audio_card.add_widget(row)

        # SFX volume
        row = SettingRow("効果音", "効果音の音量")
        sfx_layout = QHBoxLayout()
        self.sfx_slider = QSlider(Qt.Horizontal)
        self.sfx_slider.setRange(0, 100)
        self.sfx_slider.setValue(90)
        self.sfx_slider.setFixedWidth(150)
        sfx_layout.addWidget(self.sfx_slider)
        self.sfx_label = QLabel("90%")
        self.sfx_label.setStyleSheet(f"""
            font-weight: 700;
            color: {self.theme.primary_light};
            min-width: 50px;
            background: transparent;
            border: none;
        """)
        sfx_layout.addWidget(self.sfx_label)
        self.sfx_slider.valueChanged.connect(
            lambda v: self.sfx_label.setText(f"{v}%")
        )
        row.control_layout.addLayout(sfx_layout)
        audio_card.add_widget(row)

        # Crowd noise
        row = SettingRow("観客音", "試合中の観客の音")
        self.crowd_check = QCheckBox()
        self.crowd_check.setChecked(True)
        row.set_control(self.crowd_check)
        audio_card.add_widget(row)

        layout.addWidget(audio_card)
        layout.addStretch()

        scroll.setWidget(widget)
        return scroll

    def _create_save_tab(self) -> QWidget:
        """Create save/load settings tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(8, 16, 8, 16)

        # Save card
        save_card = PremiumCard("セーブデータ", "")

        # Auto-save
        row = SettingRow("オートセーブ", "自動的にゲームを保存")
        self.autosave_check = QCheckBox()
        self.autosave_check.setChecked(True)
        row.set_control(self.autosave_check)
        save_card.add_widget(row)

        # Auto-save interval
        row = SettingRow("オートセーブ間隔", "自動保存の頻度（試合数）")
        self.autosave_spin = QSpinBox()
        self.autosave_spin.setRange(1, 30)
        self.autosave_spin.setValue(5)
        self.autosave_spin.setMinimumWidth(100)
        row.set_control(self.autosave_spin)
        save_card.add_widget(row)

        # Save slots
        row = SettingRow("セーブスロット数", "保持するセーブデータの数")
        self.slots_spin = QSpinBox()
        self.slots_spin.setRange(1, 10)
        self.slots_spin.setValue(3)
        self.slots_spin.setMinimumWidth(100)
        row.set_control(self.slots_spin)
        save_card.add_widget(row)

        layout.addWidget(save_card)

        # Backup card
        backup_card = PremiumCard("バックアップ", "")

        # Backup location
        backup_row = QFrame()
        backup_row.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: 1px solid {self.theme.border_muted};
                border-radius: 10px;
            }}
        """)
        backup_layout = QHBoxLayout(backup_row)
        backup_layout.setContentsMargins(16, 12, 16, 12)

        backup_label = QLabel("バックアップ先:")
        backup_label.setStyleSheet(f"""
            color: {self.theme.text_secondary};
            font-weight: 600;
            background: transparent;
            border: none;
        """)
        backup_layout.addWidget(backup_label)

        self.backup_path = QLabel("./backups")
        self.backup_path.setStyleSheet(f"""
            color: {self.theme.text_primary};
            padding: 8px 12px;
            background: {self.theme.bg_input};
            border-radius: 6px;
        """)
        backup_layout.addWidget(self.backup_path, stretch=1)

        browse_btn = QPushButton("参照...")
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.bg_card_hover};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 6px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background: {self.theme.primary};
                border-color: {self.theme.primary};
            }}
        """)
        browse_btn.clicked.connect(self._browse_backup)
        backup_layout.addWidget(browse_btn)

        backup_card.add_widget(backup_row)

        # Export/Import buttons
        export_layout = QHBoxLayout()

        export_btn = QPushButton("エクスポート")
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_hover}, stop:1 {self.theme.bg_card});
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.primary_light}, stop:1 {self.theme.primary});
                border-color: {self.theme.primary};
            }}
        """)
        export_btn.clicked.connect(self._export_save)
        export_layout.addWidget(export_btn)

        import_btn = QPushButton("インポート")
        import_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_hover}, stop:1 {self.theme.bg_card});
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.primary_light}, stop:1 {self.theme.primary});
                border-color: {self.theme.primary};
            }}
        """)
        import_btn.clicked.connect(self._import_save)
        export_layout.addWidget(import_btn)

        backup_card.add_layout(export_layout)

        layout.addWidget(backup_card)
        layout.addStretch()

        scroll.setWidget(widget)
        return scroll

    def _load_defaults(self):
        """Load default settings"""
        self.settings = {
            "window_size": "1920 x 1080 (Full HD)",
            "fullscreen": False,
            "start_maximized": False,
            "ui_scale": 100,
            "difficulty": "ベテラン",
            "trade_difficulty": "普通",
            "fa_difficulty": "普通",
            "games_per_season": 143,
            "dh_rule": True,
            "interleague": True,
            "roster_limit": 28,
            "injuries": True,
            "sim_speed": 5,
            "auto_advance": True,
            "show_pbp": True,
            "physics": True,
            "wind": True,
            "ai_aggression": "普通",
            "theme": "ダーク（OOTP風）",
            "language": "日本語",
            "font_size": "中",
            "advanced_stats": True,
            "rating_display": "数値 (1-99)",
            "master_volume": 80,
            "bgm_volume": 70,
            "sfx_volume": 90,
            "crowd_noise": True,
            "autosave": True,
            "autosave_interval": 5,
            "save_slots": 3,
        }

    def _reset_settings(self):
        """Reset to default settings"""
        result = QMessageBox.question(
            self, "設定リセット",
            "すべての設定をデフォルトに戻しますか？",
            QMessageBox.Yes | QMessageBox.No
        )

        if result == QMessageBox.Yes:
            self._load_defaults()
            self._apply_settings_to_ui()
            QMessageBox.information(self, "完了", "設定をリセットしました。")

    def _apply_settings_to_ui(self):
        """Apply loaded settings to UI controls"""
        # Display settings
        self.window_size_combo.setCurrentText(self.settings.get("window_size", "1920 x 1080 (Full HD)"))
        self.fullscreen_check.setChecked(self.settings.get("fullscreen", False))
        self.start_maximized_check.setChecked(self.settings.get("start_maximized", False))
        self.scale_slider.setValue(self.settings.get("ui_scale", 100))
        self.theme_combo.setCurrentText(self.settings.get("theme", "ダーク（OOTP風）"))
        self.lang_combo.setCurrentText(self.settings.get("language", "日本語"))
        self.font_combo.setCurrentText(self.settings.get("font_size", "中"))
        self.adv_stats_check.setChecked(self.settings.get("advanced_stats", True))
        self.rating_combo.setCurrentText(self.settings.get("rating_display", "数値 (1-99)"))

        # Game settings
        self.difficulty_combo.setCurrentText(self.settings.get("difficulty", "ベテラン"))
        self.trade_diff_combo.setCurrentText(self.settings.get("trade_difficulty", "普通"))
        self.fa_diff_combo.setCurrentText(self.settings.get("fa_difficulty", "普通"))
        self.games_spin.setValue(self.settings.get("games_per_season", 143))
        self.dh_check.setChecked(self.settings.get("dh_rule", True))
        self.interleague_check.setChecked(self.settings.get("interleague", True))
        self.roster_limit_spin.setValue(self.settings.get("roster_limit", 28))
        self.injuries_check.setChecked(self.settings.get("injuries", True))

        # Simulation settings
        self.speed_slider.setValue(self.settings.get("sim_speed", 5))
        self.auto_advance_check.setChecked(self.settings.get("auto_advance", True))
        self.pbp_check.setChecked(self.settings.get("show_pbp", True))
        self.physics_check.setChecked(self.settings.get("physics", True))
        self.wind_check.setChecked(self.settings.get("wind", True))
        self.ai_aggr_combo.setCurrentText(self.settings.get("ai_aggression", "普通"))

        # Audio settings
        self.master_slider.setValue(self.settings.get("master_volume", 80))
        self.bgm_slider.setValue(self.settings.get("bgm_volume", 70))
        self.sfx_slider.setValue(self.settings.get("sfx_volume", 90))
        self.crowd_check.setChecked(self.settings.get("crowd_noise", True))

        # Save settings
        self.autosave_check.setChecked(self.settings.get("autosave", True))
        self.autosave_spin.setValue(self.settings.get("autosave_interval", 5))
        self.slots_spin.setValue(self.settings.get("save_slots", 3))

    def _apply_settings(self):
        """Apply current settings"""
        self.settings = {
            # Display
            "window_size": self.window_size_combo.currentText(),
            "fullscreen": self.fullscreen_check.isChecked(),
            "start_maximized": self.start_maximized_check.isChecked(),
            "ui_scale": self.scale_slider.value() / 100.0,
            "theme": self.theme_combo.currentText(),
            "language": self.lang_combo.currentText(),
            "font_size": self.font_combo.currentText(),
            "advanced_stats": self.adv_stats_check.isChecked(),
            "rating_display": self.rating_combo.currentText(),
            # Game
            "difficulty": self.difficulty_combo.currentText(),
            "trade_difficulty": self.trade_diff_combo.currentText(),
            "fa_difficulty": self.fa_diff_combo.currentText(),
            "games_per_season": self.games_spin.value(),
            "dh_rule": self.dh_check.isChecked(),
            "interleague": self.interleague_check.isChecked(),
            "roster_limit": self.roster_limit_spin.value(),
            "injuries": self.injuries_check.isChecked(),
            # Simulation
            "sim_speed": self.speed_slider.value(),
            "auto_advance": self.auto_advance_check.isChecked(),
            "show_pbp": self.pbp_check.isChecked(),
            "physics": self.physics_check.isChecked(),
            "wind": self.wind_check.isChecked(),
            "ai_aggression": self.ai_aggr_combo.currentText(),
            # Audio
            "master_volume": self.master_slider.value(),
            "bgm_volume": self.bgm_slider.value(),
            "sfx_volume": self.sfx_slider.value(),
            "crowd_noise": self.crowd_check.isChecked(),
            # Save
            "autosave": self.autosave_check.isChecked(),
            "autosave_interval": self.autosave_spin.value(),
            "save_slots": self.slots_spin.value(),
        }

        self.settings_changed.emit(self.settings)
        QMessageBox.information(self, "完了", "設定を適用しました。")

    def _browse_backup(self):
        """Browse for backup folder"""
        folder = QFileDialog.getExistingDirectory(
            self, "バックアップ先を選択",
            self.backup_path.text()
        )
        if folder:
            self.backup_path.setText(folder)

    def _export_save(self):
        """Export save data"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "セーブデータをエクスポート",
            "", "NPB Save Files (*.npbs)"
        )
        if file_path:
            QMessageBox.information(
                self, "エクスポート完了",
                f"セーブデータを {file_path} に書き出しました。"
            )

    def _import_save(self):
        """Import save data"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "セーブデータをインポート",
            "", "NPB Save Files (*.npbs)"
        )
        if file_path:
            result = QMessageBox.question(
                self, "インポート確認",
                "現在のデータを上書きしますか？",
                QMessageBox.Yes | QMessageBox.No
            )
            if result == QMessageBox.Yes:
                QMessageBox.information(
                    self, "インポート完了",
                    "セーブデータを読み込みました。"
                )

    def get_settings(self) -> dict:
        """Get current settings"""
        return self.settings
