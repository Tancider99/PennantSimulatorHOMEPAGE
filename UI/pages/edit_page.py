# -*- coding: utf-8 -*-
"""
In-Game Edit Page - Simplified with per-pitch and main position defense editing
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QLabel, QPushButton, QFrame, QListWidget,
    QLineEdit, QComboBox, QGridLayout,
    QMessageBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor, QPolygon
from PySide6.QtCore import QPoint

from UI.theme import get_theme


# ========== TriangleButton / TriangleSpinBox (same as EditScreen) ==========
class TriangleButton(QPushButton):
    """Triangle-shaped button for up/down controls"""
    def __init__(self, direction: str = "up", parent=None):
        super().__init__(parent)
        self.direction = direction
        self.theme = get_theme()
        self.setFixedSize(32, 24)
        self.setCursor(Qt.PointingHandCursor)
        self._pressed = False
        self.setStyleSheet("background: transparent; border: none;")
    
    def mousePressEvent(self, event):
        self._pressed = True
        self.update()
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        self._pressed = False
        self.update()
        super().mouseReleaseEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self._pressed:
            painter.fillRect(self.rect(), QColor(self.theme.primary_dark))
        else:
            painter.fillRect(self.rect(), QColor(self.theme.bg_card))
        
        w, h = self.width(), self.height()
        cx = w // 2
        
        if self.direction == "up":
            triangle = QPolygon([QPoint(cx, 4), QPoint(cx - 8, h - 4), QPoint(cx + 8, h - 4)])
        else:
            triangle = QPolygon([QPoint(cx, h - 4), QPoint(cx - 8, 4), QPoint(cx + 8, 4)])
        
        painter.setBrush(QColor(self.theme.text_primary))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(triangle)


class TriangleSpinBox(QWidget):
    """Custom SpinBox with triangle buttons"""
    valueChanged = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._value = 50
        self._min = 1
        self._max = 99
        self._step = 1
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        self.down_btn = TriangleButton("down")
        self.down_btn.clicked.connect(self._decrement)
        layout.addWidget(self.down_btn)
        
        self.value_edit = QLineEdit()
        self.value_edit.setAlignment(Qt.AlignCenter)
        self.value_edit.setStyleSheet(f"""
            background: {self.theme.bg_dark};
            color: {self.theme.text_primary};
            border: 1px solid {self.theme.border};
            padding: 4px;
            font-size: 13px;
            font-weight: 600;
            min-width: 50px;
        """)
        self.value_edit.editingFinished.connect(self._on_edit_finished)
        layout.addWidget(self.value_edit)
        
        self.up_btn = TriangleButton("up")
        self.up_btn.clicked.connect(self._increment)
        layout.addWidget(self.up_btn)
    
    def _increment(self):
        self.setValue(self._value + self._step)
    
    def _decrement(self):
        self.setValue(self._value - self._step)
    
    def _on_edit_finished(self):
        try:
            val = int(self.value_edit.text().replace(",", ""))
            self.setValue(val)
        except ValueError:
            self._update_display()
    
    def _update_display(self):
        self.value_edit.setText(str(self._value))
    
    def setValue(self, value: int):
        value = max(self._min, min(self._max, value))
        self._value = value
        self._update_display()
        self.valueChanged.emit(self._value)
    
    def value(self) -> int:
        return self._value
    
    def setRange(self, min_val: int, max_val: int):
        self._min = min_val
        self._max = max_val
    
    def setSingleStep(self, step: int):
        self._step = step


# ========== Main EditPage ==========
class EditPage(QWidget):
    """Simplified In-Game Data Editor with per-pitch editing"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.game_state = None
        self.theme = get_theme()
        self.current_team = None
        self.current_player = None
        self.current_staff = None
        self.players_list = []
        self.staff_list_data = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        # Tab Buttons
        tabs_layout = QHBoxLayout()
        tabs_layout.setSpacing(2)
        
        self.btn_team = self._create_tab_button("チーム")
        self.btn_team.setChecked(True)
        self.btn_team.clicked.connect(lambda: self._switch_tab(0))
        tabs_layout.addWidget(self.btn_team)
        
        self.btn_player = self._create_tab_button("選手")
        self.btn_player.clicked.connect(lambda: self._switch_tab(1))
        tabs_layout.addWidget(self.btn_player)
        
        self.btn_staff = self._create_tab_button("スタッフ")
        self.btn_staff.clicked.connect(lambda: self._switch_tab(2))
        tabs_layout.addWidget(self.btn_staff)
        
        tabs_layout.addStretch()
        
        # Save All Button
        self.save_all_btn = QPushButton("すべて保存")
        self.save_all_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.success};
                color: white;
                border: none;
                padding: 6px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{ background: #33cc66; }}
        """)
        self.save_all_btn.clicked.connect(self._save_all)
        tabs_layout.addWidget(self.save_all_btn)
        
        layout.addLayout(tabs_layout)
        
        # Content Stack
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        
        self.stack.addWidget(self._create_team_editor())
        self.stack.addWidget(self._create_player_editor())
        self.stack.addWidget(self._create_staff_editor())
    
    def _create_tab_button(self, text):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setFixedHeight(28)
        btn.setMinimumWidth(70)
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.theme.text_muted};
                border: none;
                padding: 4px 12px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {self.theme.bg_card};
                color: {self.theme.text_primary};
            }}
            QPushButton:checked {{
                background: #ffffff;
                color: #666666;
                font-weight: 600;
            }}
        """)
        return btn
    
    def _switch_tab(self, index):
        self.stack.setCurrentIndex(index)
        self.btn_team.setChecked(index == 0)
        self.btn_player.setChecked(index == 1)
        self.btn_staff.setChecked(index == 2)
    
    # ==================== Team Editor ====================
    def _create_team_editor(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)
        
        # Team List
        list_frame = self._create_list_frame("チーム一覧", 160)
        self.team_list = QListWidget()
        self.team_list.setStyleSheet(self._list_style())
        self.team_list.currentRowChanged.connect(self._on_team_selected)
        list_frame.layout().addWidget(self.team_list)
        layout.addWidget(list_frame)
        
        # Team Details (Fan count only)
        detail_frame = QFrame()
        detail_frame.setStyleSheet(f"background: {self.theme.bg_card};")
        detail_layout = QVBoxLayout(detail_frame)
        detail_layout.setContentsMargins(12, 12, 12, 12)
        detail_layout.setSpacing(10)
        
        self.team_name_label = QLabel("チーム名: -")
        self.team_name_label.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.theme.primary};")
        detail_layout.addWidget(self.team_name_label)
        
        self._add_section_label(detail_layout, "ファン層")
        fan_grid = QGridLayout()
        fan_grid.setSpacing(10)
        fan_grid.setVerticalSpacing(12)
        
        fan_grid.addWidget(QLabel("ライト層:"), 0, 0)
        self.light_fans_spin = TriangleSpinBox()
        self.light_fans_spin.setRange(10000, 5000000)
        self.light_fans_spin.setSingleStep(10000)
        fan_grid.addWidget(self.light_fans_spin, 0, 1)
        
        fan_grid.addWidget(QLabel("ミドル層:"), 1, 0)
        self.middle_fans_spin = TriangleSpinBox()
        self.middle_fans_spin.setRange(5000, 2000000)
        self.middle_fans_spin.setSingleStep(5000)
        fan_grid.addWidget(self.middle_fans_spin, 1, 1)
        
        fan_grid.addWidget(QLabel("コア層:"), 2, 0)
        self.core_fans_spin = TriangleSpinBox()
        self.core_fans_spin.setRange(1000, 500000)
        self.core_fans_spin.setSingleStep(1000)
        fan_grid.addWidget(self.core_fans_spin, 2, 1)
        
        detail_layout.addLayout(fan_grid)
        detail_layout.addStretch()
        layout.addWidget(detail_frame, 1)
        
        return widget
    
    # ==================== Player Editor ====================
    def _create_player_editor(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)
        
        # Left: Team + Player List
        left_frame = self._create_list_frame("選手一覧", 180)
        
        self.player_team_combo = QComboBox()
        self.player_team_combo.setStyleSheet(self._input_style())
        self.player_team_combo.currentTextChanged.connect(self._on_player_team_changed)
        left_frame.layout().addWidget(self.player_team_combo)
        
        self.player_list = QListWidget()
        self.player_list.setStyleSheet(self._list_style())
        self.player_list.currentRowChanged.connect(self._on_player_selected)
        left_frame.layout().addWidget(self.player_list)
        
        self.player_count_label = QLabel("選手: 0")
        self.player_count_label.setStyleSheet(f"font-size: 12px; color: {self.theme.text_muted};")
        left_frame.layout().addWidget(self.player_count_label)
        
        layout.addWidget(left_frame)
        
        # Right: Player Stats with scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        detail_widget = QWidget()
        detail_widget.setStyleSheet(f"background: {self.theme.bg_card};")
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(12, 12, 12, 12)
        detail_layout.setSpacing(8)
        
        # Player name
        self.player_name_label = QLabel("選手名: -")
        self.player_name_label.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.theme.primary};")
        detail_layout.addWidget(self.player_name_label)
        
        self.player_type_label = QLabel("")
        self.player_type_label.setStyleSheet(f"font-size: 12px; color: {self.theme.accent_blue};")
        detail_layout.addWidget(self.player_type_label)
        
        # Batter Main Stats
        self._add_section_label(detail_layout, "野手主要能力")
        batter_grid = QGridLayout()
        batter_grid.setSpacing(10)
        batter_grid.setVerticalSpacing(12)
        
        self.stat_spins = {}
        batter_main = [
            ("ミート", "contact"), ("パワー", "power"), ("走力", "speed"),
            ("肩力", "arm"), ("守備", "fielding"), ("捕球", "error")
        ]
        
        for i, (label, key) in enumerate(batter_main):
            row, col = divmod(i, 3)
            batter_grid.addWidget(QLabel(f"{label}:"), row, col * 2)
            spin = TriangleSpinBox()
            spin.setRange(1, 99)
            batter_grid.addWidget(spin, row, col * 2 + 1)
            self.stat_spins[key] = spin
        
        detail_layout.addLayout(batter_grid)
        
        # Pitcher Base Stats
        self._add_section_label(detail_layout, "投手基本能力")
        pitcher_grid = QGridLayout()
        pitcher_grid.setSpacing(10)
        pitcher_grid.setVerticalSpacing(12)
        
        pitcher_base = [
            ("球速", "velocity"), ("スタミナ", "stamina"), ("ゴロ傾向", "gb_tendency")
        ]
        
        for i, (label, key) in enumerate(pitcher_base):
            pitcher_grid.addWidget(QLabel(f"{label}:"), 0, i * 2)
            spin = TriangleSpinBox()
            if key == "velocity":
                spin.setRange(100, 170)
            else:
                spin.setRange(1, 99)
            pitcher_grid.addWidget(spin, 0, i * 2 + 1)
            self.stat_spins[key] = spin
        
        detail_layout.addLayout(pitcher_grid)
        
        # Per-Pitch Stats Section
        self._add_section_label(detail_layout, "球種別能力 (変球種選択)")
        
        # Pitch selector
        pitch_select_layout = QHBoxLayout()
        pitch_select_layout.addWidget(QLabel("球種:"))
        self.pitch_combo = QComboBox()
        self.pitch_combo.setStyleSheet(self._input_style())
        self.pitch_combo.setMinimumWidth(120)
        self.pitch_combo.currentTextChanged.connect(self._on_pitch_selected)
        pitch_select_layout.addWidget(self.pitch_combo)
        pitch_select_layout.addStretch()
        detail_layout.addLayout(pitch_select_layout)
        
        # Per-pitch spin boxes
        pitch_grid = QGridLayout()
        pitch_grid.setSpacing(10)
        
        self.pitch_spins = {}
        pitch_stats = [("制球", "control"), ("球威", "stuff"), ("変化量", "movement")]
        
        for i, (label, key) in enumerate(pitch_stats):
            pitch_grid.addWidget(QLabel(f"{label}:"), 0, i * 2)
            spin = TriangleSpinBox()
            spin.setRange(1, 99)
            pitch_grid.addWidget(spin, 0, i * 2 + 1)
            self.pitch_spins[key] = spin
        
        detail_layout.addLayout(pitch_grid)
        
        detail_layout.addStretch()
        scroll.setWidget(detail_widget)
        layout.addWidget(scroll, 1)
        
        return widget
    
    # ==================== Staff Editor ====================
    def _create_staff_editor(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(8)
        
        left_frame = self._create_list_frame("スタッフ一覧", 180)
        
        self.staff_team_combo = QComboBox()
        self.staff_team_combo.setStyleSheet(self._input_style())
        self.staff_team_combo.currentTextChanged.connect(self._on_staff_team_changed)
        left_frame.layout().addWidget(self.staff_team_combo)
        
        self.staff_list = QListWidget()
        self.staff_list.setStyleSheet(self._list_style())
        self.staff_list.currentRowChanged.connect(self._on_staff_selected)
        left_frame.layout().addWidget(self.staff_list)
        
        layout.addWidget(left_frame)
        
        detail_frame = QFrame()
        detail_frame.setStyleSheet(f"background: {self.theme.bg_card};")
        detail_layout = QVBoxLayout(detail_frame)
        detail_layout.setContentsMargins(12, 12, 12, 12)
        detail_layout.setSpacing(10)
        
        self.staff_name_label = QLabel("スタッフ名: -")
        self.staff_name_label.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.theme.primary};")
        detail_layout.addWidget(self.staff_name_label)
        
        self._add_section_label(detail_layout, "能力値")
        info_grid = QGridLayout()
        info_grid.setSpacing(10)
        
        info_grid.addWidget(QLabel("能力:"), 0, 0)
        self.staff_ability_spin = TriangleSpinBox()
        self.staff_ability_spin.setRange(1, 99)
        info_grid.addWidget(self.staff_ability_spin, 0, 1)
        
        detail_layout.addLayout(info_grid)
        detail_layout.addStretch()
        layout.addWidget(detail_frame, 1)
        
        return widget
    
    # ==================== Helpers ====================
    def _create_list_frame(self, title, width):
        frame = QFrame()
        frame.setStyleSheet(f"background: {self.theme.bg_card};")
        frame.setFixedWidth(width)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        
        lbl = QLabel(title)
        lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {self.theme.text_primary};")
        layout.addWidget(lbl)
        
        return frame
    
    def _add_section_label(self, layout, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {self.theme.primary}; margin-top: 6px;")
        layout.addWidget(lbl)
    
    def _list_style(self):
        return f"""
            QListWidget {{
                background: {self.theme.bg_dark};
                color: {self.theme.text_primary};
                border: none;
                font-size: 12px;
            }}
            QListWidget::item {{ padding: 3px; }}
            QListWidget::item:selected {{ background: {self.theme.primary}; }}
        """
    
    def _input_style(self):
        return f"""
            background: {self.theme.bg_dark};
            color: {self.theme.text_primary};
            border: 1px solid {self.theme.border};
            padding: 4px;
            font-size: 12px;
        """
    
    # ==================== Data Loading ====================
    def set_game_state(self, game_state):
        self.game_state = game_state
        self._load_teams()
    
    def _load_teams(self):
        if not self.game_state:
            return
        
        self.team_list.clear()
        self.player_team_combo.clear()
        self.staff_team_combo.clear()
        
        for team in self.game_state.teams:
            self.team_list.addItem(team.name)
            self.player_team_combo.addItem(team.name)
            self.staff_team_combo.addItem(team.name)
    
    def _on_team_selected(self, row):
        if row < 0 or not self.game_state:
            return
        self.current_team = self.game_state.teams[row]
        t = self.current_team
        
        self.team_name_label.setText(f"チーム名: {t.name}")
        
        finance = getattr(t, 'finance', None)
        if finance and hasattr(finance, 'fan_base'):
            fb = finance.fan_base
            self.light_fans_spin.setValue(fb.light_fans)
            self.middle_fans_spin.setValue(fb.middle_fans)
            self.core_fans_spin.setValue(fb.core_fans)
    
    def _on_player_team_changed(self, team_name):
        self.player_list.clear()
        self.players_list = []
        self.current_player = None
        
        if not team_name or not self.game_state:
            return
        
        for team in self.game_state.teams:
            if team.name == team_name:
                self.players_list = team.players
                for p in team.players:
                    self.player_list.addItem(f"#{p.uniform_number} {p.name}")
                self.player_count_label.setText(f"選手: {len(team.players)}")
                break
    
    def _on_player_selected(self, row):
        if row < 0 or row >= len(self.players_list):
            return
        
        self.current_player = self.players_list[row]
        p = self.current_player
        
        self.player_name_label.setText(f"選手名: {p.name} (#{p.uniform_number})")
        pos_text = p.position.value if hasattr(p.position, 'value') else str(p.position)
        self.player_type_label.setText(f"{pos_text} | {p.age}歳")
        
        # Load batter stats
        for key, spin in self.stat_spins.items():
            if hasattr(p.stats, key):
                val = getattr(p.stats, key, 50)
            elif key == "fielding":
                # Get from main position's defense range
                pos_name = p.position.value if hasattr(p.position, 'value') else str(p.position)
                val = p.stats.defense_ranges.get(pos_name, 50)
            else:
                val = 50
            spin.setValue(int(val))
        
        # Load pitch types into combo
        self.pitch_combo.blockSignals(True)
        self.pitch_combo.clear()
        pitches = getattr(p.stats, 'pitches', {})
        if pitches:
            for pitch_name in pitches.keys():
                self.pitch_combo.addItem(pitch_name)
        else:
            self.pitch_combo.addItem("ストレート")
        self.pitch_combo.blockSignals(False)
        
        # Trigger load of first pitch
        if self.pitch_combo.count() > 0:
            self._on_pitch_selected(self.pitch_combo.currentText())
    
    def _on_pitch_selected(self, pitch_name):
        if not self.current_player or not pitch_name:
            return
        
        p = self.current_player
        stats = p.stats
        
        # Get pitch data
        pitch_data = stats.pitches.get(pitch_name, {})
        
        if isinstance(pitch_data, dict):
            self.pitch_spins["control"].setValue(pitch_data.get("control", 50))
            self.pitch_spins["stuff"].setValue(pitch_data.get("stuff", 50))
            self.pitch_spins["movement"].setValue(pitch_data.get("movement", 50))
        elif isinstance(pitch_data, int):
            # Old format - just one value for all
            self.pitch_spins["control"].setValue(pitch_data)
            self.pitch_spins["stuff"].setValue(pitch_data)
            self.pitch_spins["movement"].setValue(pitch_data)
        else:
            for spin in self.pitch_spins.values():
                spin.setValue(50)
    
    def _on_staff_team_changed(self, team_name):
        self.staff_list.clear()
        self.staff_list_data = []
        self.current_staff = None
        
        if not team_name or not self.game_state:
            return
        
        for team in self.game_state.teams:
            if team.name == team_name:
                self.staff_list_data = getattr(team, 'staff', []) or []
                for s in self.staff_list_data:
                    self.staff_list.addItem(f"{s.name} ({s.role.value})")
                break
    
    def _on_staff_selected(self, row):
        if row < 0 or row >= len(self.staff_list_data):
            return
        
        self.current_staff = self.staff_list_data[row]
        s = self.current_staff
        
        self.staff_name_label.setText(f"スタッフ名: {s.name}")
        self.staff_ability_spin.setValue(s.ability)
    
    # ==================== Bulk Save ====================
    def _save_all(self):
        """Save all modified data"""
        # Save current team fan data
        if self.current_team:
            t = self.current_team
            if hasattr(t, 'finance') and t.finance and hasattr(t.finance, 'fan_base'):
                t.finance.fan_base.light_fans = self.light_fans_spin.value()
                t.finance.fan_base.middle_fans = self.middle_fans_spin.value()
                t.finance.fan_base.core_fans = self.core_fans_spin.value()
        
        # Save current player
        if self.current_player:
            p = self.current_player
            
            # Save main stats
            for key, spin in self.stat_spins.items():
                if key == "fielding":
                    # Save to main position's defense_ranges
                    pos_name = p.position.value if hasattr(p.position, 'value') else str(p.position)
                    p.stats.defense_ranges[pos_name] = spin.value()
                elif hasattr(p.stats, key):
                    setattr(p.stats, key, spin.value())
            
            # Save current pitch stats
            pitch_name = self.pitch_combo.currentText()
            if pitch_name and pitch_name in p.stats.pitches:
                pitch_data = p.stats.pitches[pitch_name]
                if isinstance(pitch_data, dict):
                    pitch_data["control"] = self.pitch_spins["control"].value()
                    pitch_data["stuff"] = self.pitch_spins["stuff"].value()
                    pitch_data["movement"] = self.pitch_spins["movement"].value()
                else:
                    # Convert to dict format
                    p.stats.pitches[pitch_name] = {
                        "control": self.pitch_spins["control"].value(),
                        "stuff": self.pitch_spins["stuff"].value(),
                        "movement": self.pitch_spins["movement"].value()
                    }
        
        # Save current staff
        if self.current_staff:
            self.current_staff.ability = self.staff_ability_spin.value()
        
        QMessageBox.information(self, "保存", "データを更新しました")
    
    def refresh(self):
        self._load_teams()
