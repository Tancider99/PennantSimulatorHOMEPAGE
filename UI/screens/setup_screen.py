# -*- coding: utf-8 -*-
"""
NPB Pennant Simulator - Game Setup Screen
Initial configuration after team selection
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QComboBox, QCheckBox, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QFont

import sys

try:
    from ..theme import get_theme
    from ..widgets.buttons import PremiumButton
except ImportError:
    sys.path.insert(0, '..')
    from UI.theme import get_theme
    from UI.widgets.buttons import PremiumButton

class SettingRow(QWidget):
    """A single row for a setting option"""
    def __init__(self, title: str, description: str, widget: QWidget, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 10, 0, 10)
        
        # Labels
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"font-size: 14px; color: #ffffff; font-weight: bold;")
        
        desc_label = QLabel(description)
        desc_label.setStyleSheet(f"font-size: 11px; color: {self.theme.text_secondary};")
        
        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)
        
        layout.addLayout(text_layout, 2)
        layout.addWidget(widget, 1)

class SetupScreen(QWidget):
    """Game setup screen displayed after team selection"""

    start_game_clicked = Signal(dict) # Emits settings dictionary
    back_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme = get_theme()
        self._selected_team_id = None
        self._setup_ui()

    def set_selected_team(self, team_id: str):
        """Update the UI to show which team was selected"""
        self._selected_team_id = team_id
        # Ideally, fetch team name from a manager, but for now just display ID or placeholder
        self.team_label.setText(f"SELECTED TEAM: {team_id}")

    def _setup_ui(self):
        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Header Section
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("SEASON CONFIGURATION")
        title.setStyleSheet("font-size: 32px; font-weight: 300; letter-spacing: 5px; color: #ffffff;")
        title.setAlignment(Qt.AlignCenter)
        
        self.team_label = QLabel("SELECTED TEAM: ---")
        self.team_label.setStyleSheet(f"font-size: 14px; color: {self._theme.accent_blue}; letter-spacing: 2px;")
        self.team_label.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(self.team_label)
        
        layout.addWidget(header)

        # Settings Container (Center)
        settings_frame = QFrame()
        settings_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {self._theme.bg_card};
                border: 1px solid {self._theme.border};
                border-radius: 4px;
            }}
        """)
        settings_layout = QVBoxLayout(settings_frame)
        settings_layout.setContentsMargins(30, 30, 30, 30)
        settings_layout.setSpacing(0)

        # --- Settings Widgets ---

        # 1. Games per Season
        self.games_combo = QComboBox()
        self.games_combo.addItems(["143 Games (Standard)", "50 Games (Short)", "10 Games (Debug)"])
        self.games_combo.setStyleSheet(self._get_combo_style())
        settings_layout.addWidget(SettingRow(
            "Season Length", "Number of games per team in the regular season.", self.games_combo
        ))
        settings_layout.addWidget(self._create_divider())

        # 2. Difficulty
        self.diff_combo = QComboBox()
        self.diff_combo.addItems(["Rookie", "Veteran", "All-Star", "Hall of Fame"])
        self.diff_combo.setCurrentIndex(1)
        self.diff_combo.setStyleSheet(self._get_combo_style())
        settings_layout.addWidget(SettingRow(
            "Difficulty Level", "Affects trade AI logic and match simulation variance.", self.diff_combo
        ))
        settings_layout.addWidget(self._create_divider())

        # 3. Financial System
        self.finance_check = QCheckBox("Enable Salary Cap & Budget")
        self.finance_check.setChecked(True)
        self.finance_check.setStyleSheet(self._get_checkbox_style())
        settings_layout.addWidget(SettingRow(
            "Financial System", "Manage team budget, player salaries, and ticket prices.", self.finance_check
        ))
        settings_layout.addWidget(self._create_divider())
        
        # 4. DH Rule
        self.dh_combo = QComboBox()
        self.dh_combo.addItems(["Pacific League Only", "Universal DH", "No DH"])
        self.dh_combo.setStyleSheet(self._get_combo_style())
        settings_layout.addWidget(SettingRow(
            "Designated Hitter", "Rules for the Designated Hitter position.", self.dh_combo
        ))

        settings_layout.addStretch()
        layout.addWidget(settings_frame)

        # Footer Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)
        
        self.back_btn = PremiumButton("BACK", "secondary")
        self.back_btn.clicked.connect(self.back_clicked.emit)
        
        self.start_btn = PremiumButton("START SEASON", "primary")
        self.start_btn.clicked.connect(self._on_start_clicked)
        
        button_layout.addStretch()
        button_layout.addWidget(self.back_btn)
        button_layout.addWidget(self.start_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)

    def _create_divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet(f"background-color: {self._theme.border_muted}; margin-top: 5px; margin-bottom: 5px;")
        line.setFixedHeight(1)
        return line

    def _get_combo_style(self):
        return f"""
            QComboBox {{
                background-color: {self._theme.bg_input};
                color: {self._theme.text_primary};
                border: 1px solid {self._theme.border};
                padding: 5px;
                min-width: 200px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """

    def _get_checkbox_style(self):
        return f"""
            QCheckBox {{
                color: {self._theme.text_primary};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                background-color: {self._theme.bg_input};
                border: 1px solid {self._theme.border};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self._theme.primary};
                border-color: {self._theme.primary};
            }}
        """

    def _on_start_clicked(self):
        # Gather settings
        games_map = {0: 143, 1: 50, 2: 10}
        
        settings = {
            "games_per_season": games_map[self.games_combo.currentIndex()],
            "difficulty": self.diff_combo.currentText(),
            "financials_enabled": self.finance_check.isChecked(),
            "dh_rule": self.dh_combo.currentText(),
            "selected_team": self._selected_team_id
        }
        self.start_game_clicked.emit(settings)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        # Match background with other screens
        painter.fillRect(self.rect(), QColor(self._theme.bg_dark))