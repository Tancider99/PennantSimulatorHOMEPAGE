# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Settings Page
Angular Industrial Design with Functional Settings
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QSlider, QPushButton, QFrame, QSpinBox,
    QScrollArea, QSizePolicy, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme, ThemeManager


class SettingSection(QFrame):
    """Angular settings section with accent bar"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.title = title
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
                border-radius: 0px;
            }}
        """)
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Header with accent bar
        header = QWidget()
        header.setStyleSheet(f"background: {self.theme.bg_card_elevated};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        
        # Accent bar
        accent = QFrame()
        accent.setFixedSize(4, 40)
        accent.setStyleSheet(f"background: {self.theme.primary}; border-radius: 0px;")
        header_layout.addWidget(accent)
        
        # Title
        title_label = QLabel(self.title)
        title_label.setStyleSheet(f"""
            font-size: 12px;
            font-weight: 700;
            color: {self.theme.text_primary};
            letter-spacing: 2px;
            padding: 12px 16px;
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        self.main_layout.addWidget(header)
        
        # Content area
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(16, 8, 16, 16)
        self.content_layout.setSpacing(4)
        
        self.main_layout.addWidget(self.content_widget)
    
    def add_widget(self, widget):
        self.content_layout.addWidget(widget)


class SettingRow(QFrame):
    """Angular setting row with label and control"""
    
    def __init__(self, label: str, description: str = "", parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_input};
                border: none;
                border-radius: 0px;
            }}
            QFrame:hover {{
                background: {self.theme.bg_card_hover};
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(12)
        
        # Label section
        label_widget = QWidget()
        label_widget.setStyleSheet("background: transparent;")
        label_layout = QVBoxLayout(label_widget)
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(2)
        
        self.label = QLabel(label)
        self.label.setStyleSheet(f"""
            font-size: 12px;
            font-weight: 600;
            color: {self.theme.text_primary};
            background: transparent;
        """)
        label_layout.addWidget(self.label)
        
        if description:
            desc = QLabel(description)
            desc.setStyleSheet(f"""
                font-size: 10px;
                color: {self.theme.text_muted};
                background: transparent;
            """)
            desc.setWordWrap(True)
            label_layout.addWidget(desc)
        
        layout.addWidget(label_widget, stretch=1)
        
        # Control placeholder
        self.control_layout = QHBoxLayout()
        self.control_layout.setSpacing(8)
        layout.addLayout(self.control_layout)
    
    def set_control(self, widget):
        self.control_layout.addWidget(widget)


class SettingsPage(QWidget):
    """Settings page with functional game settings - QWidget based"""
    
    settings_changed = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.settings = {}
        
        self._setup_ui()
    
    def set_game_state(self, game_state):
        """Set game state and sync settings"""
        self.game_state = game_state
        self._sync_from_game_state()
    
    def _sync_from_game_state(self):
        """Sync UI controls from game state"""
        if not self.game_state:
            return
        
        # Weather toggle
        if hasattr(self.game_state, 'weather_enabled'):
            self.weather_check.setChecked(self.game_state.weather_enabled)
        
        # Auto order priority
        if hasattr(self.game_state, 'auto_order_priority'):
            priority = self.game_state.auto_order_priority
            if priority == "ability":
                self.order_priority_combo.setCurrentIndex(0)
            elif priority == "condition":
                self.order_priority_combo.setCurrentIndex(1)
            else:
                self.order_priority_combo.setCurrentIndex(2)
        
        # Auto order enabled for player team
        if hasattr(self.game_state, 'auto_order_enabled'):
            self.auto_order_check.setChecked(self.game_state.auto_order_enabled)
        
        # Pitcher stamina weight
        if hasattr(self.game_state, 'pitcher_stamina_weight'):
            self.stamina_weight_slider.setValue(int(self.game_state.pitcher_stamina_weight * 100))
        
        # AI settings
        if hasattr(self.game_state, 'ai_bunt_tendency'):
            self.ai_bunt_slider.setValue(self.game_state.ai_bunt_tendency)
        if hasattr(self.game_state, 'ai_steal_tendency'):
            self.ai_steal_slider.setValue(self.game_state.ai_steal_tendency)
        if hasattr(self.game_state, 'ai_pitching_change_tendency'):
            self.ai_pitch_change_slider.setValue(self.game_state.ai_pitching_change_tendency)
        
        # Injuries
        if hasattr(self.game_state, 'injuries_enabled'):
            self.injuries_check.setChecked(self.game_state.injuries_enabled)
        
        # Autosave
        if hasattr(self.game_state, 'autosave_enabled'):
            self.autosave_check.setChecked(self.game_state.autosave_enabled)
        if hasattr(self.game_state, 'autosave_interval'):
            self.autosave_spin.setValue(self.game_state.autosave_interval)
        
        # Auto demotion frequency
        if hasattr(self.game_state, 'auto_demotion_frequency'):
            freq = self.game_state.auto_demotion_frequency
            if freq == "strict":
                self.demotion_frequency_combo.setCurrentIndex(0)
            elif freq == "relaxed":
                self.demotion_frequency_combo.setCurrentIndex(2)
            else:
                self.demotion_frequency_combo.setCurrentIndex(1)  # normal
    
    def _sync_to_game_state(self):
        """Sync UI controls to game state"""
        if not self.game_state:
            return False
        
        # Weather toggle
        self.game_state.weather_enabled = self.weather_check.isChecked()
        
        # Auto order priority
        idx = self.order_priority_combo.currentIndex()
        if idx == 0:
            self.game_state.auto_order_priority = "ability"
        elif idx == 1:
            self.game_state.auto_order_priority = "condition"
        else:
            self.game_state.auto_order_priority = "balanced"
        
        # Auto order enabled for player team
        self.game_state.auto_order_enabled = self.auto_order_check.isChecked()
        
        # Pitcher stamina weight
        self.game_state.pitcher_stamina_weight = self.stamina_weight_slider.value() / 100.0
        
        # Substitute thresholds
        self.game_state.substitute_stamina_threshold = self.sub_stamina_slider.value()
        self.game_state.pinch_hitter_inning = self.pinch_hitter_spin.value()
        
        # AI settings
        self.game_state.ai_bunt_tendency = self.ai_bunt_slider.value()
        self.game_state.ai_steal_tendency = self.ai_steal_slider.value()
        self.game_state.ai_pitching_change_tendency = self.ai_pitch_change_slider.value()
        self.game_state.ai_defensive_shift = self.ai_shift_check.isChecked()
        
        # Injuries
        self.game_state.injuries_enabled = self.injuries_check.isChecked()
        
        # Autosave
        self.game_state.autosave_enabled = self.autosave_check.isChecked()
        self.game_state.autosave_interval = self.autosave_spin.value()
        
        # Auto demotion frequency
        demotion_idx = self.demotion_frequency_combo.currentIndex()
        if demotion_idx == 0:
            self.game_state.auto_demotion_frequency = "strict"
        elif demotion_idx == 2:
            self.game_state.auto_demotion_frequency = "relaxed"
        else:
            self.game_state.auto_demotion_frequency = "normal"
        
        return True
    
    def _setup_ui(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        self.setStyleSheet(f"background: {self.theme.bg_dark};")
        
        # Header - Angular style
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
                border-radius: 0px;
            }}
        """)
        
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(0)
        
        # Title
        title = QLabel("SETTINGS")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 800;
            color: {self.theme.text_primary};
            letter-spacing: 4px;
        """)
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # Reset button
        reset_btn = QPushButton("RESET")
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.theme.text_secondary};
                border: 1px solid {self.theme.border};
                border-radius: 0px;
                padding: 10px 20px;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {self.theme.danger};
                color: white;
                border-color: {self.theme.danger};
            }}
        """)
        reset_btn.clicked.connect(self._reset_settings)
        header_layout.addWidget(reset_btn)
        
        main_layout.addWidget(header)
        
        # Separator
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {self.theme.border};")
        main_layout.addWidget(sep)
        
        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: {self.theme.bg_dark};
            }}
            QScrollBar:vertical {{
                background: {self.theme.bg_card};
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.theme.text_muted};
                min-height: 30px;
            }}
        """)
        
        content = QWidget()
        content.setStyleSheet(f"background: {self.theme.bg_dark};")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(16)
        
        # === GAMEPLAY SECTION ===
        gameplay_section = SettingSection("GAMEPLAY")
        
        # Weather toggle
        row = SettingRow("天候システム", "雨天中止やコールドゲームを有効化")
        self.weather_check = QCheckBox()
        self.weather_check.setChecked(True)
        self.weather_check.setStyleSheet(self._get_checkbox_style())
        row.set_control(self.weather_check)
        gameplay_section.add_widget(row)
        
        # Injuries
        row = SettingRow("故障発生", "選手の故障が発生")
        self.injuries_check = QCheckBox()
        self.injuries_check.setChecked(True)
        self.injuries_check.setStyleSheet(self._get_checkbox_style())
        row.set_control(self.injuries_check)
        gameplay_section.add_widget(row)
        
        content_layout.addWidget(gameplay_section)
        
        # === ORDER SETTINGS SECTION ===
        order_section = SettingSection("ORDER SETTINGS")
        
        # Auto order toggle for player team
        row = SettingRow("自動オーダー調整", "自チームのオーダーを自動調整（オフ時は怪我人のみ交代）")
        self.auto_order_check = QCheckBox()
        self.auto_order_check.setChecked(False)  # Default OFF - manual control
        self.auto_order_check.setStyleSheet(self._get_checkbox_style())
        row.set_control(self.auto_order_check)
        order_section.add_widget(row)
        
        # Auto order priority
        row = SettingRow("自動オーダー優先", "オート編成時の優先順位")
        self.order_priority_combo = QComboBox()
        self.order_priority_combo.addItems(["能力優先", "調子優先", "バランス"])
        self.order_priority_combo.setStyleSheet(self._get_combo_style())
        row.set_control(self.order_priority_combo)
        order_section.add_widget(row)
        
        # Pitcher stamina weight
        row = SettingRow("投手スタミナ重視度", "オーダー決定時のスタミナの考慮度")
        stamina_layout = QHBoxLayout()
        stamina_layout.setSpacing(8)
        self.stamina_weight_slider = QSlider(Qt.Horizontal)
        self.stamina_weight_slider.setRange(0, 100)
        self.stamina_weight_slider.setValue(50)
        self.stamina_weight_slider.setFixedWidth(120)
        self.stamina_weight_slider.setStyleSheet(self._get_slider_style())
        stamina_layout.addWidget(self.stamina_weight_slider)
        self.stamina_weight_label = QLabel("50%")
        self.stamina_weight_label.setStyleSheet(f"font-weight: 700; color: {self.theme.primary}; min-width: 40px;")
        stamina_layout.addWidget(self.stamina_weight_label)
        self.stamina_weight_slider.valueChanged.connect(lambda v: self.stamina_weight_label.setText(f"{v}%"))
        row.control_layout.addLayout(stamina_layout)
        order_section.add_widget(row)
        
        # Substitute stamina threshold
        row = SettingRow("代打スタミナ閾値", "この値以下で代打を考慮")
        sub_layout = QHBoxLayout()
        sub_layout.setSpacing(8)
        self.sub_stamina_slider = QSlider(Qt.Horizontal)
        self.sub_stamina_slider.setRange(10, 50)
        self.sub_stamina_slider.setValue(30)
        self.sub_stamina_slider.setFixedWidth(120)
        self.sub_stamina_slider.setStyleSheet(self._get_slider_style())
        sub_layout.addWidget(self.sub_stamina_slider)
        self.sub_stamina_label = QLabel("30%")
        self.sub_stamina_label.setStyleSheet(f"font-weight: 700; color: {self.theme.primary}; min-width: 40px;")
        sub_layout.addWidget(self.sub_stamina_label)
        self.sub_stamina_slider.valueChanged.connect(lambda v: self.sub_stamina_label.setText(f"{v}%"))
        row.control_layout.addLayout(sub_layout)
        order_section.add_widget(row)
        
        # Pinch hitter inning
        row = SettingRow("代打開始イニング", "代打を使い始めるイニング")
        self.pinch_hitter_spin = QSpinBox()
        self.pinch_hitter_spin.setRange(5, 9)
        self.pinch_hitter_spin.setValue(7)
        self.pinch_hitter_spin.setStyleSheet(self._get_spinbox_style())
        row.set_control(self.pinch_hitter_spin)
        order_section.add_widget(row)
        
        # Auto demotion frequency
        row = SettingRow("自動降格頻度", "成績不振選手の降格判定期間（厳格:10日 / 通常:15日 / 緩め:20日）")
        self.demotion_frequency_combo = QComboBox()
        self.demotion_frequency_combo.addItems(["厳格 (10日)", "通常 (15日)", "緩め (20日)"])
        self.demotion_frequency_combo.setCurrentIndex(1)  # Default: normal
        self.demotion_frequency_combo.setStyleSheet(self._get_combo_style())
        row.set_control(self.demotion_frequency_combo)
        order_section.add_widget(row)
        
        content_layout.addWidget(order_section)
        
        # === AI SETTINGS SECTION ===
        ai_section = SettingSection("AI SETTINGS")
        
        # AI bunt tendency
        row = SettingRow("AIバント傾向", "AIがバントを選択する傾向")
        bunt_layout = QHBoxLayout()
        bunt_layout.setSpacing(8)
        self.ai_bunt_slider = QSlider(Qt.Horizontal)
        self.ai_bunt_slider.setRange(0, 100)
        self.ai_bunt_slider.setValue(50)
        self.ai_bunt_slider.setFixedWidth(120)
        self.ai_bunt_slider.setStyleSheet(self._get_slider_style())
        bunt_layout.addWidget(self.ai_bunt_slider)
        self.ai_bunt_label = QLabel("50")
        self.ai_bunt_label.setStyleSheet(f"font-weight: 700; color: {self.theme.primary}; min-width: 30px;")
        bunt_layout.addWidget(self.ai_bunt_label)
        self.ai_bunt_slider.valueChanged.connect(lambda v: self.ai_bunt_label.setText(f"{v}"))
        row.control_layout.addLayout(bunt_layout)
        ai_section.add_widget(row)
        
        # AI steal tendency
        row = SettingRow("AI盗塁傾向", "AIが盗塁を試みる傾向")
        steal_layout = QHBoxLayout()
        steal_layout.setSpacing(8)
        self.ai_steal_slider = QSlider(Qt.Horizontal)
        self.ai_steal_slider.setRange(0, 100)
        self.ai_steal_slider.setValue(50)
        self.ai_steal_slider.setFixedWidth(120)
        self.ai_steal_slider.setStyleSheet(self._get_slider_style())
        steal_layout.addWidget(self.ai_steal_slider)
        self.ai_steal_label = QLabel("50")
        self.ai_steal_label.setStyleSheet(f"font-weight: 700; color: {self.theme.primary}; min-width: 30px;")
        steal_layout.addWidget(self.ai_steal_label)
        self.ai_steal_slider.valueChanged.connect(lambda v: self.ai_steal_label.setText(f"{v}"))
        row.control_layout.addLayout(steal_layout)
        ai_section.add_widget(row)
        
        # AI pitching change tendency
        row = SettingRow("AI継投傾向", "AIが投手交代を行う傾向")
        pitch_layout = QHBoxLayout()
        pitch_layout.setSpacing(8)
        self.ai_pitch_change_slider = QSlider(Qt.Horizontal)
        self.ai_pitch_change_slider.setRange(0, 100)
        self.ai_pitch_change_slider.setValue(50)
        self.ai_pitch_change_slider.setFixedWidth(120)
        self.ai_pitch_change_slider.setStyleSheet(self._get_slider_style())
        pitch_layout.addWidget(self.ai_pitch_change_slider)
        self.ai_pitch_label = QLabel("50")
        self.ai_pitch_label.setStyleSheet(f"font-weight: 700; color: {self.theme.primary}; min-width: 30px;")
        pitch_layout.addWidget(self.ai_pitch_label)
        self.ai_pitch_change_slider.valueChanged.connect(lambda v: self.ai_pitch_label.setText(f"{v}"))
        row.control_layout.addLayout(pitch_layout)
        ai_section.add_widget(row)
        
        # AI defensive shift
        row = SettingRow("AIシフト守備", "AIがシフト守備を使用")
        self.ai_shift_check = QCheckBox()
        self.ai_shift_check.setChecked(True)
        self.ai_shift_check.setStyleSheet(self._get_checkbox_style())
        row.set_control(self.ai_shift_check)
        ai_section.add_widget(row)
        
        content_layout.addWidget(ai_section)
        
        # === AUTOSAVE SECTION ===
        save_section = SettingSection("AUTOSAVE")
        
        # Auto-save toggle
        row = SettingRow("オートセーブ", "自動的にゲームを保存")
        self.autosave_check = QCheckBox()
        self.autosave_check.setChecked(True)
        self.autosave_check.setStyleSheet(self._get_checkbox_style())
        row.set_control(self.autosave_check)
        save_section.add_widget(row)
        
        # Auto-save interval
        row = SettingRow("オートセーブ間隔", "自動保存の頻度（日数）")
        self.autosave_spin = QSpinBox()
        self.autosave_spin.setRange(1, 30)
        self.autosave_spin.setValue(5)
        self.autosave_spin.setStyleSheet(self._get_spinbox_style())
        row.set_control(self.autosave_spin)
        save_section.add_widget(row)
        
        content_layout.addWidget(save_section)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
        # Bottom buttons
        button_bar = QFrame()
        button_bar.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
            }}
        """)
        button_layout = QHBoxLayout(button_bar)
        button_layout.setContentsMargins(20, 12, 20, 12)
        button_layout.setSpacing(12)
        
        button_layout.addStretch()
        
        # Apply button
        self.apply_btn = QPushButton("APPLY")
        self.apply_btn.setMinimumSize(120, 40)
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                color: black;
                border: none;
                border-radius: 0px;
                padding: 12px 32px;
                font-weight: 700;
                font-size: 12px;
                letter-spacing: 2px;
            }}
            QPushButton:hover {{
                background: #e0e0e0;
            }}
            QPushButton:pressed {{
                background: #cccccc;
            }}
        """)
        self.apply_btn.clicked.connect(self._apply_settings)
        button_layout.addWidget(self.apply_btn)
        
        main_layout.addWidget(button_bar)
    
    def _get_checkbox_style(self):
        return f"""
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border: 2px solid {self.theme.border};
                background: {self.theme.bg_input};
            }}
            QCheckBox::indicator:checked {{
                background: {self.theme.primary};
                border-color: {self.theme.primary};
            }}
        """
    
    def _get_combo_style(self):
        return f"""
            QComboBox {{
                background: {self.theme.bg_input};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                padding: 8px 12px;
                min-width: 120px;
                font-weight: 500;
            }}
            QComboBox:hover {{
                border-color: {self.theme.primary};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background: {self.theme.bg_card};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                selection-background-color: {self.theme.primary};
            }}
        """
    
    def _get_slider_style(self):
        return f"""
            QSlider::groove:horizontal {{
                background: {self.theme.bg_input};
                height: 6px;
            }}
            QSlider::handle:horizontal {{
                background: {self.theme.primary};
                width: 16px;
                height: 16px;
                margin: -5px 0;
            }}
            QSlider::sub-page:horizontal {{
                background: {self.theme.primary};
            }}
        """
    
    def _get_spinbox_style(self):
        return f"""
            QSpinBox {{
                background: {self.theme.bg_input};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                padding: 6px 10px;
                min-width: 80px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 20px;
                border: none;
                background: {self.theme.bg_card_hover};
            }}
        """
    
    def _sync_to_game_state(self):
        """Sync UI settings to GameState object"""
        if not self.game_state:
            return False
            
        try:
            # Game System Settings
            self.game_state.weather_enabled = self.weather_check.isChecked()
            self.game_state.injuries_enabled = self.injuries_check.isChecked()
            self.game_state.auto_order_enabled = self.auto_order_check.isChecked()
            
            p_map = ["ability", "condition", "balanced"]
            if self.order_priority_combo.currentIndex() < len(p_map):
                self.game_state.auto_order_priority = p_map[self.order_priority_combo.currentIndex()]
            
            # Numeric Settings
            self.game_state.pitcher_stamina_weight = self.stamina_weight_slider.value() / 100.0
            self.game_state.substitute_stamina_threshold = self.sub_stamina_slider.value()
            self.game_state.pinch_hitter_inning = self.pinch_hitter_spin.value()
            self.game_state.starter_rest_days = self.starter_rest_spin.value()
            
            # AI Settings
            self.game_state.ai_bunt_tendency = self.ai_bunt_slider.value()
            self.game_state.ai_steal_tendency = self.ai_steal_slider.value()
            self.game_state.ai_pitching_change_tendency = self.ai_pitch_change_slider.value()
            self.game_state.ai_defensive_shift = self.ai_shift_check.isChecked()
            
            # Autosave Settings
            self.game_state.autosave_enabled = self.autosave_check.isChecked()
            self.game_state.autosave_interval = self.autosave_spin.value()
            
            return True
        except Exception:
            return False
    
    def _apply_settings(self):
        """Apply current settings to game state"""
        success = self._sync_to_game_state()
        
        # Collect all settings
        self.settings = {
            "weather_enabled": self.weather_check.isChecked(),
            "injuries_enabled": self.injuries_check.isChecked(),
            "auto_order_enabled": self.auto_order_check.isChecked(),
            "order_priority": self.order_priority_combo.currentIndex(),
            "pitcher_stamina_weight": self.stamina_weight_slider.value(),
            "substitute_stamina_threshold": self.sub_stamina_slider.value(),
            "pinch_hitter_inning": self.pinch_hitter_spin.value(),
            "ai_bunt_tendency": self.ai_bunt_slider.value(),
            "ai_steal_tendency": self.ai_steal_slider.value(),
            "ai_pitching_change_tendency": self.ai_pitch_change_slider.value(),
            "ai_defensive_shift": self.ai_shift_check.isChecked(),
            "autosave_enabled": self.autosave_check.isChecked(),
            "autosave_interval": self.autosave_spin.value(),
        }
        
        self.settings_changed.emit(self.settings)
        
        # Show confirmation dialog (always show)
        QMessageBox.information(self, "設定", "設定を適用しました")
    
    def _reset_settings(self):
        """Reset to default settings"""
        self.weather_check.setChecked(True)
        self.injuries_check.setChecked(True)
        self.auto_order_check.setChecked(True)  # Default ON
        self.order_priority_combo.setCurrentIndex(0)
        self.stamina_weight_slider.setValue(50)
        self.sub_stamina_slider.setValue(30)
        self.pinch_hitter_spin.setValue(7)
        self.starter_rest_spin.setValue(6)
        self.ai_bunt_slider.setValue(50)
        self.ai_steal_slider.setValue(50)
        self.ai_pitch_change_slider.setValue(50)
        self.ai_shift_check.setChecked(True)
        self.theme_combo.setCurrentIndex(0)
        self.font_combo.setCurrentIndex(1)
        self.autosave_check.setChecked(True)
        self.autosave_spin.setValue(5)
        
        QMessageBox.information(self, "設定", "設定をデフォルトに戻しました")
    
    def refresh(self):
        """Refresh settings from game state"""
        self._sync_from_game_state()
