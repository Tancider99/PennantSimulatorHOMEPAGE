# -*- coding: utf-8 -*-
"""
Training Page - 練習タブ
選手の練習メニュー管理UI (インタラクティブな能力バー操作)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea,
    QPushButton, QTabWidget, QSplitter, QAbstractItemView,
    QMessageBox, QGridLayout, QSizePolicy, QComboBox, QInputDialog, QProgressBar
)
from PySide6.QtCore import Qt, Signal, QSize, QEvent
from PySide6.QtGui import QColor, QFont, QIcon, QMouseEvent

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.panels import ContentPanel
from UI.widgets.charts import RadarChart
from UI.widgets.tables import SortableTableWidgetItem
from models import Position, TeamLevel, PlayerType, TrainingMenu
from training_system import (
    assign_default_player_type, TRAINING_STAT_MAP, STAT_DISPLAY_NAMES, 
    resolve_auto_training, get_available_pitches, learn_specific_pitch
)

# 逆引きマップ (Stat Key -> TrainingMenu)
# すべての能力をマッピング
KEY_TO_MENU_PITCHER = {
    # Basic
    "velocity": TrainingMenu.VELOCITY, 
    "control": TrainingMenu.CONTROL,
    "stamina": TrainingMenu.STAMINA, 
    "breaking": TrainingMenu.MOVEMENT,
    "movement": TrainingMenu.MOVEMENT,
    "stuff": TrainingMenu.STUFF,
    "mental": TrainingMenu.MENTAL, 
    
    # Special
    "vs_left_pitcher": TrainingMenu.VS_LEFT,
    "vs_pinch": TrainingMenu.VS_PINCH, 
    "hold_runners": TrainingMenu.HOLD_RUNNERS,
    "recovery": TrainingMenu.RECOVERY, 
    "stability": TrainingMenu.STABILITY,
    "durability": TrainingMenu.DURABILITY, 
    "intelligence": TrainingMenu.INTELLIGENCE,
    "gb_tendency": TrainingMenu.MENTAL,  # ゴロ傾向はメンタル練習で向上
    "new_pitch_progress": TrainingMenu.NEW_PITCH,
}

KEY_TO_MENU_BATTER = {
    # Basic
    "trajectory": TrainingMenu.TRAJECTORY, 
    "contact": TrainingMenu.CONTACT, 
    "power": TrainingMenu.POWER,
    "speed": TrainingMenu.SPEED, 
    "arm": TrainingMenu.ARM,
    "fielding": TrainingMenu.FIELDING, 
    "error": TrainingMenu.ERROR,
    
    # Advanced / Special
    "chance": TrainingMenu.CHANCE, 
    "vs_left_batter": TrainingMenu.VS_LEFT,
    "steal": TrainingMenu.STEAL,
    "baserunning": TrainingMenu.BASERUNNING,
    "bunt_sac": TrainingMenu.BUNT,
    "bunt_hit": TrainingMenu.BUNT, # Map both
    "gap": TrainingMenu.GAP,
    "eye": TrainingMenu.EYE,
    "avoid_k": TrainingMenu.AVOID_K,
    
    # Fielding Special
    "catcher_lead": TrainingMenu.CATCHER_LEAD,
    "turn_dp": TrainingMenu.TURN_DP,
    
    # Common
    "mental": TrainingMenu.MENTAL,
    "recovery": TrainingMenu.RECOVERY,
    "durability": TrainingMenu.DURABILITY,
    "intelligence": TrainingMenu.INTELLIGENCE,
}

# Reverse mapping (TrainingMenu -> Stat Key) for display highlighting
MENU_TO_KEY_PITCHER = {v: k for k, v in KEY_TO_MENU_PITCHER.items() if v is not None}
MENU_TO_KEY_BATTER = {v: k for k, v in KEY_TO_MENU_BATTER.items() if v is not None}
# Manually fix ambiguous mappings (TrainingMenu.BUNT maps to 'bunt_hit' by default, override to 'bunt_sac')
if TrainingMenu.BUNT in MENU_TO_KEY_BATTER:
    MENU_TO_KEY_BATTER[TrainingMenu.BUNT] = "bunt_sac"

class TrainingStatWidget(QFrame):
    """
    Interactive Stat Widget:
    Click to set as training target.
    """
    clicked = Signal(str) # Emits stat_key

    def __init__(self, label, value, stat_key, theme, max_val=100, is_special=False, is_selected=False, xp_val=0.0):
        super().__init__()
        self.stat_key = stat_key
        self.theme = theme
        self.is_selected = is_selected
        self.stat_value = value
        self.setCursor(Qt.PointingHandCursor)
        
        # Height to accommodate XP bar
        self.setFixedHeight(40)
        
        # Apply selected styling
        if is_selected:
            self.setStyleSheet(f"""
                TrainingStatWidget {{
                    background-color: {theme.bg_card_hover};
                    border: 2px solid {theme.primary};
                    border-radius: 4px;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                TrainingStatWidget {{
                    background-color: {theme.bg_input};
                    border: 1px solid transparent;
                    border-radius: 4px;
                }}
            """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)
        
        # Top Row: Label ... Value
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0,0,0,0)
        
        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 10px; color: {theme.text_secondary if not is_selected else theme.primary}; font-weight: {700 if is_selected else 500};")
        top_row.addWidget(lbl)
        top_row.addStretch()
        
        # Value logic
        disp_val = str(int(value))
        if label == "球速": 
            disp_val += " km/h"
            ratio = max(0, min(1, (value - 120) / (170-120)))
            color = theme.accent_orange
        elif is_special: # Trajectory (1-4)
            ratio = max(0, min(1, value / 4.0))
            color = theme.accent_orange
        else:
            ratio = max(0, min(100, value)) / 100.0
            # Use PlayerStats.get_rank_color for consistency with player detail page
            from models import PlayerStats
            stats_util = PlayerStats()
            color = stats_util.get_rank_color(value)
            
        val_lbl = QLabel(disp_val)
        val_lbl.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {color};")
        top_row.addWidget(val_lbl)
        
        layout.addLayout(top_row)
        
        # XP Progress Bar
        xp_progress = QProgressBar()
        xp_progress.setFixedHeight(4)
        xp_progress.setTextVisible(False)
        xp_progress.setRange(0, 100)
        xp_progress.setValue(int(xp_val))
        xp_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {theme.bg_dark};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {theme.accent_blue if not is_selected else theme.primary};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(xp_progress)
        
        # Ability Bar
        bar_bg = QFrame()
        bar_bg.setFixedHeight(3)
        grad_stop = f"{ratio:.3f}"
        grad_stop_next = f"{min(1.0, ratio+0.001):.3f}"
        bar_bg.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
            stop:0 {color}, stop:{grad_stop} {color},
            stop:{grad_stop_next} {theme.bg_dark}, stop:1 {theme.bg_dark});
            border-radius: 2px;
        """)
        layout.addWidget(bar_bg)
        
        # XP Bar (Underneath)
        # Calculate frac
        frac = value - int(value)
        xp_color = "#00cec9" # Cyan/Teal for XP
        xp_stop = f"{frac:.3f}"
        xp_stop_next = f"{min(1.0, frac+0.001):.3f}"
        
        xp_bar = QFrame()
        xp_bar.setFixedHeight(2)
        xp_bar.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
            stop:0 {xp_color}, stop:{xp_stop} {xp_color},
            stop:{xp_stop_next} transparent, stop:1 transparent);
            border-radius: 1px;
        """)
        layout.addWidget(xp_bar)
        
    def mousePressEvent(self, event: QMouseEvent):
        self.clicked.emit(self.stat_key)
        super().mousePressEvent(event)


class TrainingPage(ContentPanel):
    """Refactored Training Page (Per-Pitch + New Pitch)"""
    
    training_saved = Signal()
    player_detail_requested = Signal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.current_team = None
        self.selected_player = None
        self.selected_stat_key = None  # Track which stat was clicked
        self._skip_selection_key_update = False  # Flag to prevent overwriting selected_stat_key during stat click
        
        self._setup_ui()
    
    def _setup_ui(self):
        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 1. Header
        header = QFrame()
        header.setFixedHeight(40)
        header.setStyleSheet(f"background: {self.theme.bg_card}; border-bottom: 1px solid {self.theme.border};")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(16, 0, 16, 0)
        title = QLabel("TRAINING")
        title.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {self.theme.text_primary};")
        hl.addWidget(title)
        
        desc = QLabel("※能力をクリックして練習を設定")
        desc.setStyleSheet(f"font-size: 11px; color: {self.theme.text_muted}; margin-left: 20px;")
        hl.addWidget(desc)
        hl.addStretch()
        layout.addWidget(header)
        
        # 2. Splitter
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setStyleSheet(f"QSplitter::handle {{ background: {self.theme.border}; width: 1px; }}")
        
        # Left Panel (Tabs -> Table)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(self._get_tab_style())
        
        self.batter_table = self._create_table("batter")
        self.pitcher_table = self._create_table("pitcher")
        
        self.tabs.addTab(self.batter_table, "野手")
        self.tabs.addTab(self.pitcher_table, "投手")
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        container_left = QWidget()
        lc = QVBoxLayout(container_left)
        lc.setContentsMargins(0,0,0,0)
        lc.addWidget(self.tabs)
        self.splitter.addWidget(container_left)
        
        # Right Panel (Detail Interactive)
        self.right_panel = self._create_detail_panel()
        self.splitter.addWidget(self.right_panel)
        
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 6)
        self.splitter.setSizes([450, 650])   
        
        layout.addWidget(self.splitter)
        
    def _get_tab_style(self):
        return f"""
            QTabWidget::pane {{ border: none; background: {self.theme.bg_dark}; }}
            QTabBar::tab {{
                background: {self.theme.bg_card};
                color: {self.theme.text_secondary};
                padding: 6px 12px;
                border: none;
                font-weight: 600;
                min-width: 50px;
                font-size: 11px;
            }}
            QTabBar::tab:selected {{
                background: {self.theme.primary};
                color: black; 
            }}
        """

    def _create_table(self, mode: str):
        table = QTableWidget()
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.setSortingEnabled(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        headers = ["No.", "名前", "年齢", "総合", "メニュー"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        header = table.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch) 
        
        table.setStyleSheet(f"""
            QTableWidget {{ background: {self.theme.bg_dark}; border: none; color: {self.theme.text_primary}; }}
            QTableWidget::item {{ padding: 4px; border-bottom: 1px solid {self.theme.bg_card}; }}
            QTableWidget::item:selected {{ background: white; color: black; }}
            QHeaderView::section {{ background: {self.theme.bg_card}; color: {self.theme.text_muted}; padding: 4px; border: none; font-weight: 600; }}
        """)
        
        table.itemSelectionChanged.connect(self._on_selection_changed)
        table.cellDoubleClicked.connect(lambda r, c: self._on_double_click(table, r))
        table.setProperty("mode", mode)
        return table

    def _create_detail_panel(self):
        container = QWidget()
        container.setStyleSheet(f"background: {self.theme.bg_card};")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Header (Name + Type)
        self.detail_header_lbl = QLabel("選手を選択してください")
        self.detail_header_lbl.setStyleSheet(f"font-size: 15px; font-weight: 700; color: {self.theme.text_primary};")
        layout.addWidget(self.detail_header_lbl)
        
        self.type_lbl = QLabel("")
        self.type_lbl.setStyleSheet(f"font-size: 11px; color: {self.theme.accent_blue}; font-weight: 700; background: {self.theme.bg_dark}; padding: 2px 6px; border-radius: 4px;")
        layout.addWidget(self.type_lbl)
        
        # Charts & Interactive Grid
        main_content = QHBoxLayout()
        main_content.setSpacing(12)
        
        # Left: Radar & Info
        left_box = QVBoxLayout()
        self.radar_chart = RadarChart()
        self.radar_chart.setFixedSize(140, 140)
        left_box.addWidget(self.radar_chart)
        
        # Overall Frame
        self.overall_val_lbl = QLabel("-")
        self.overall_val_lbl.setStyleSheet(f"color: {self.theme.text_primary}; font-size: 18px; font-weight: 800; qproperty-alignment: AlignCenter;")
        left_box.addWidget(self.overall_val_lbl)
        
        # お任せ (Auto) Button
        self.auto_btn = QPushButton("お任せ")
        self.auto_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.accent_blue};
                color: {self.theme.bg_darkest};
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: 700;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.primary};
            }}
        """)
        self.auto_btn.clicked.connect(self._on_auto_training_clicked)
        self.auto_btn.hide()  # Hide until player selected
        left_box.addWidget(self.auto_btn)
        
        # Hidden Combo Box for internal use (not displayed)
        self.menu_combo = QComboBox()
        self.menu_combo.hide()  # Hidden from UI
        self.menu_combo.currentIndexChanged.connect(self._on_menu_combo_changed)
        
        left_box.addStretch()
        main_content.addLayout(left_box)
        
        # Right: Interactive Stats Grid DIRECTLY (No Scroll)
        stats_container = QWidget()
        stats_container.setStyleSheet("background: transparent;")
        self.stats_grid = QGridLayout(stats_container)
        self.stats_grid.setContentsMargins(0,0,0,0)
        self.stats_grid.setSpacing(4)
        
        # Add stretch to keep it tight
        main_content.addWidget(stats_container, stretch=1)
        
        layout.addLayout(main_content)
        
        return container

    def set_game_state(self, game_state):
        self.game_state = game_state
        if game_state and game_state.player_team:
            self.current_team = game_state.player_team
            self.refresh()

    def refresh(self):
        if not self.current_team: return
        for p in self.current_team.players:
            if not p.player_type: assign_default_player_type(p)
        self._refresh_tables()
        self._update_detail_view()

    def _refresh_tables(self):
        if not self.current_team: return
        
        # Block signals during refresh to prevent _on_selection_changed from being triggered
        self.batter_table.blockSignals(True)
        self.pitcher_table.blockSignals(True)
        
        try:
            self._refresh_tables_internal()
        finally:
            # Restore signals
            self.batter_table.blockSignals(False)
            self.pitcher_table.blockSignals(False)

    def _refresh_tables_internal(self):
        """Internal refresh without signal blocking - use when caller already blocks signals"""
        if not self.current_team: return
        
        batters = [p for p in self.current_team.players if p.position != Position.PITCHER]
        batters.sort(key=lambda p: (p.team_level.value, -p.stats.overall_batting(p.position)))
        self._fill_table(self.batter_table, batters)
        
        pitchers = [p for p in self.current_team.players if p.position == Position.PITCHER]
        pitchers.sort(key=lambda p: (p.team_level.value, -p.stats.overall_pitching()))
        self._fill_table(self.pitcher_table, pitchers)

    def _fill_table(self, table, players):
        table.setSortingEnabled(False)
        selected_player_name = self.selected_player.name if self.selected_player else None
        
        table.setRowCount(len(players))
        table.players = players
        mode = table.property("mode")
        PLAYER_DATA_ROLE = Qt.UserRole + 1
        
        for row, p in enumerate(players):
            self._set_item(table, row, 0, f"#{p.uniform_number}", p.uniform_number)
            
            item_name = SortableTableWidgetItem(f"{p.name}")
            item_name.setData(PLAYER_DATA_ROLE, row) 
            item_name.sort_key = p.name
            table.setItem(row, 1, item_name)
            
            self._set_item(table, row, 2, str(p.age), p.age)
            
            ovr = p.stats.overall_batting(p.position) if mode == "batter" else p.stats.overall_pitching()
            self._set_item(table, row, 3, f"★{ovr}", ovr)
            
            # Menu Check
            if p.training_menu:
                m_text = p.training_menu.value
            else:
                m_text = "お任せ" # Auto
                
            item_menu = SortableTableWidgetItem(m_text)
            item_menu.sort_key = m_text
            item_menu.setTextAlignment(Qt.AlignCenter)
            if not p.training_menu: # Auto
                 item_menu.setForeground(QColor(self.theme.text_muted))
            table.setItem(row, 4, item_menu)
            
            if selected_player_name and p.name == selected_player_name:
                table.selectRow(row)
        table.setSortingEnabled(True)

    def _set_item(self, table, row, col, text, sort_key):
        item = SortableTableWidgetItem(text)
        item.setData(Qt.UserRole, sort_key)
        item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, col, item)

    def _on_tab_changed(self):
        self._on_selection_changed()

    def _on_selection_changed(self):
        table = self.tabs.currentWidget()
        if not hasattr(table, 'players'): return
        rows = table.selectionModel().selectedRows()
        if not rows:
            self.selected_player = None
            self.selected_stat_key = None  # Reset selection
        else:
            row = rows[0].row()
            name_item = table.item(row, 1)
            PLAYER_DATA_ROLE = Qt.UserRole + 1
            if name_item:
                idx = name_item.data(PLAYER_DATA_ROLE)
                if idx is not None and 0 <= idx < len(table.players):
                     self.selected_player = table.players[idx]
                     # Set selected_stat_key based on player's current training menu
                     # Skip if we just handled a stat click (flag prevents overwriting)
                     if self._skip_selection_key_update:
                         self._skip_selection_key_update = False
                     else:
                         p = self.selected_player
                         if p.training_menu:
                             is_pitcher = p.position == Position.PITCHER
                             menu_to_key = MENU_TO_KEY_PITCHER if is_pitcher else MENU_TO_KEY_BATTER
                             self.selected_stat_key = menu_to_key.get(p.training_menu)
                     
                             # Fallback: If menu is string (loaded from JSON) but keys are Enums
                             if not self.selected_stat_key and isinstance(p.training_menu, str):
                                 for m_enum, k_val in menu_to_key.items():
                                     if hasattr(m_enum, 'value') and m_enum.value == p.training_menu:
                                         self.selected_stat_key = k_val
                                         break
                         else:
                             self.selected_stat_key = None  # Auto mode (お任せ)
        self._update_detail_view()

    def _on_double_click(self, table, row):
        PLAYER_DATA_ROLE = Qt.UserRole + 1
        name_item = table.item(row, 1)
        if name_item:
            idx = name_item.data(PLAYER_DATA_ROLE)
            if idx is not None:
                 self.player_detail_requested.emit(table.players[idx])

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                # CRITICAL: Detach from parent to remove from visual hierarchy immediately
                widget.setParent(None)
                # Also hide and disable mouse events as backup
                widget.hide()
                widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                # Disconnect signals
                try:
                    widget.clicked.disconnect()
                except (RuntimeError, AttributeError):
                    pass
                widget.deleteLater()

    def _update_menu_combo(self, player):
        """Update combo box options based on player type"""
        self.menu_combo.blockSignals(True)
        self.menu_combo.clear()
        
        # Add "Auto"
        self.menu_combo.addItem("お任せ", None)
        
        # Get appropriate menus
        is_pitcher = player.position == Position.PITCHER
        
        # All TrainingMenus
        menus = []
        if is_pitcher:
            # Add Pitcher specific + Common
            # Use KEY_TO_MENU_PITCHER values, unique sorted
            seen = set()
            for m in KEY_TO_MENU_PITCHER.values():
                if m and m not in seen:
                    seen.add(m)
                    menus.append(m)
        else:
            seen = set()
            for m in KEY_TO_MENU_BATTER.values():
                if m and m not in seen:
                    seen.add(m)
                    menus.append(m)
        
        # Sort menus by name or logical order? 
        # Just use list order based on Enum definition if possible, or name
        # menus.sort(key=lambda m: m.value)
        
        for m in menus:
            self.menu_combo.addItem(m.value, m)
            
        # Set selection
        if player.training_menu:
            idx = self.menu_combo.findData(player.training_menu)
            if idx >= 0:
                self.menu_combo.setCurrentIndex(idx)
            else:
                self.menu_combo.setCurrentIndex(0)
        else:
            self.menu_combo.setCurrentIndex(0)
            
        self.menu_combo.blockSignals(False)

    def _on_menu_combo_changed(self, index):
        if not self.selected_player: return
        data = self.menu_combo.itemData(index)
        self.selected_player.training_menu = data # Can be None (Auto)
        self._refresh_tables()
        self._update_detail_view(update_combo=False) # Don't rebuild combo loop
        self.training_saved.emit()

    def _update_detail_view(self, update_combo=True):
        if not self.selected_player:
            self.detail_header_lbl.setText("選手を選択してください")
            self.type_lbl.setText("")
            self.radar_chart.hide()
            self.auto_btn.hide()  # Hide when no player
            self.overall_val_lbl.setText("-")
            self.menu_combo.clear()
            self._clear_layout(self.stats_grid)
            return

        p = self.selected_player
        self.detail_header_lbl.setText(f"{p.name} #{p.uniform_number}  - {p.position.value}")
        if p.player_type:
             self.type_lbl.setText(f"◆ {p.player_type.value}")
        else:
             self.type_lbl.setText("◆ 不明")
             
        self.radar_chart.show()
        self.auto_btn.show()  # Show when player selected
        is_pitcher = p.position == Position.PITCHER
        self.radar_chart.set_player_stats(p, is_pitcher)
        
        ovr = p.stats.overall_pitching() if is_pitcher else p.stats.overall_batting(p.position)
        self.overall_val_lbl.setText(f"★{ovr}")
        
        # Update Combo (Only if not triggered by combo itself to avoid loop/flicker)
        if update_combo:
            self._update_menu_combo(p)

        # Rebuild Stats Grid with ALL stats
        self._clear_layout(self.stats_grid)
        stats = p.stats
        current_map = KEY_TO_MENU_PITCHER if is_pitcher else KEY_TO_MENU_BATTER
        
        # Define layout order for ALL stats: (Label, Key, MaxVal, IsSpec)
        items = []
        
        if is_pitcher:
            # Per-Pitch Logic:
            # Use 2 columns to prevent wrapping
            cols_count = 2
            
            # Group 1: Physical / Global - (Label, Value, Key, MaxVal, IsSpecial)
            items.append(("球速", stats.velocity, "velocity", 170, True))
            items.append(("スタミナ", stats.stamina, "stamina", 100, False))
            items.append(("クイック", stats.hold_runners, "hold_runners", 100, False))
            items.append(("対左打", stats.vs_left_pitcher, "vs_left_pitcher", 100, False))
            items.append(("対ピンチ", stats.vs_pinch, "vs_pinch", 100, False))
            items.append(("安定感", stats.stability, "stability", 100, False))
            items.append(("回復", stats.recovery, "recovery", 100, False))
            items.append(("メンタル", stats.mental, "mental", 100, False))
            
            # Group 2: 全体の球威/制球/変化量（球種平均）- ダブルクリックで球種練習
            items.append(("球威", stats.stuff, "stuff", 100, False))
            items.append(("制球", stats.control, "control", 100, False))
            items.append(("変化量", stats.movement, "movement", 100, False))
            items.append(("ゴロ傾向", stats.gb_tendency, "gb_tendency", 100, False))
            items.append(("新球種習得", stats.new_pitch_progress, "new_pitch_progress", 100, False))
            
        else:
            cols_count = 3
            # Batter stats - (Label, Value, Key, MaxVal, IsSpecial)
            items = [
                # Main
                ("弾道", stats.trajectory, "trajectory", 4, True),
                ("ミート", stats.contact, "contact", 100, False),
                ("パワー", stats.power, "power", 100, False),
                ("走力", stats.speed, "speed", 100, False),
                ("肩力", stats.arm, "arm", 100, False),
                ("守備力", stats.fielding, "fielding", 100, False),
                ("捕球", stats.error, "error", 100, False),
                # Sub
                ("ギャップ", stats.gap, "gap", 100, False), 
                ("選球眼", stats.eye, "eye", 100, False),
                ("三振回避", stats.avoid_k, "avoid_k", 100, False),
                # Special
                ("チャンス", stats.chance, "chance", 100, False),
                ("対左投", stats.vs_left_batter, "vs_left_batter", 100, False),
                ("盗塁", stats.steal, "steal", 100, False),
                ("走塁", stats.baserunning, "baserunning", 100, False),
                ("バント", stats.bunt_sac, "bunt_sac", 100, False),
                # Common
                ("回復", stats.recovery, "recovery", 100, False),
                ("メンタル", stats.mental, "mental", 100, False),
                ("ケガしにくさ", stats.durability, "durability", 100, False),
                ("野球脳", stats.intelligence, "intelligence", 100, False),
            ]
            if p.position == Position.CATCHER:
                items.append(("リード", stats.catcher_lead, "catcher_lead", 100, False))
            items.append(("併殺処理", stats.turn_dp, "turn_dp", 100, False))

        # Render GRID
        row, col = 0, 0
        
        for tup in items:
            if len(tup) == 5:
                label, val, key, max_val, is_spec = tup
            else: continue
            
            # Check if this is the selected stat
            is_selected = (self.selected_stat_key == key)
            
            # Get XP
            xp_val = 0.0
            if hasattr(p, 'training_xp') and p.training_xp:
                xp_val = p.training_xp.get(key, 0.0)
            
            widget = TrainingStatWidget(label, val, key, self.theme, max_val, is_spec, is_selected, xp_val=xp_val)
            widget.clicked.connect(self._on_stat_selected)
            self.stats_grid.addWidget(widget, row, col)
            
            col += 1
            if col >= cols_count:
                col = 0
                row += 1

    def _on_stat_selected(self, stat_key):
        if not self.selected_player: 
            return
        p = self.selected_player
        is_pitcher = p.position == Position.PITCHER
        
        # Special handling for new pitch selection
        if stat_key == "new_pitch_progress" and is_pitcher:
            self._show_new_pitch_dialog(p)
            return
        
        menu_map = KEY_TO_MENU_PITCHER if is_pitcher else KEY_TO_MENU_BATTER
        menu = menu_map.get(stat_key)
        
        if menu:
            p.training_menu = menu
            self.selected_stat_key = stat_key  # Track which stat was clicked
            
            # Block signals during ENTIRE update process
            self.batter_table.blockSignals(True)
            self.pitcher_table.blockSignals(True)
            try:
                # Trigger immediate save
                self.training_saved.emit() 
                self._refresh_tables_internal()  # Use internal method without signal blocking
                self._update_detail_view(update_combo=True) # Reflect in combo
            finally:
                self.batter_table.blockSignals(False)
                self.pitcher_table.blockSignals(False)
        else:
            pass

    def _show_new_pitch_dialog(self, player):
        """新球種選択ダイアログを表示"""
        available = get_available_pitches(player)
        
        if not available:
            QMessageBox.information(self, "新球種習得", "習得可能な球種がありません。")
            return
        
        pitch, ok = QInputDialog.getItem(
            self, 
            "新球種習得", 
            "習得する球種を選択してください:",
            available, 
            0, 
            False
        )
        
        if ok and pitch:
            success = learn_specific_pitch(player, pitch)
            if success:
                QMessageBox.information(self, "新球種習得", f"{pitch}を習得しました！")
                self.training_saved.emit()
                self._refresh_tables()
                self._update_detail_view()
            else:
                QMessageBox.warning(self, "エラー", "球種の習得に失敗しました。")

    def _on_auto_training_clicked(self):
        """お任せボタンクリック時 - 練習メニューをNone(自動)に設定"""
        if not self.selected_player:
            return
        
        self.selected_player.training_menu = None  # Auto mode
        self.selected_stat_key = None  # Reset selection
        self.training_saved.emit()
        self._refresh_tables()
        self._update_detail_view()
