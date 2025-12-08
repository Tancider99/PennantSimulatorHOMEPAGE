# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Order Page
Advanced Drag & Drop Order Management with DH support
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QSplitter, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QScrollArea, QSizePolicy, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QMimeData, QByteArray, QDataStream, QIODevice, QPoint, QSize
from PySide6.QtGui import QColor, QFont, QIcon, QDrag, QPixmap, QPainter, QBrush, QPen

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.panels import ToolbarPanel
from models import PlayerStats

# MIME Types
MIME_PLAYER_DATA = "application/x-pennant-player-data"
MIME_POS_SWAP = "application/x-pennant-pos-swap"

def get_rank_color(rank: str, theme) -> QColor:
    """Return color based on rank (S-G)"""
    if rank == "S": return QColor("#FFD700") # Gold
    if rank == "A": return QColor("#FF4500") # Orange Red
    if rank == "B": return QColor("#FFA500") # Orange
    if rank == "C": return QColor("#32CD32") # Lime Green
    # 修正: テーマカラー（文字列）をQColorオブジェクトに変換
    if rank == "D": return QColor(theme.text_primary)
    if rank == "E": return QColor(theme.text_secondary)
    if rank == "F": return QColor(theme.text_muted)
    if rank == "G": return QColor("#808080") # Gray
    return QColor(theme.text_primary)

def get_pos_color(pos: str) -> str:
    """Return background color code for position badge"""
    if pos == "投": return "#3498db"
    if pos == "捕": return "#27ae60"
    if pos in ["一", "二", "三", "遊"]: return "#e67e22"
    if pos in ["左", "中", "右"]: return "#9b59b6"
    if pos == "DH": return "#e74c3c"
    return "#7f8c8d"

class DraggableTableWidget(QTableWidget):
    """Enhanced TableWidget supporting Drag & Drop for Order Management"""
    
    items_changed = Signal()
    position_swapped = Signal(int, int)

    def __init__(self, mode="batter", parent=None):
        super().__init__(parent)
        self.mode = mode # 'lineup', 'bench', 'rotation', 'bullpen', 'farm_batter', 'farm_pitcher'
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setViewportMargins(0, 0, 0, 0)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.horizontalHeader().setStretchLastSection(True)
        self.setShowGrid(False)
        self.setFocusPolicy(Qt.ClickFocus)
        self.theme = get_theme()

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item: return

        row = item.row()
        col = item.column()
        player_idx = item.data(Qt.UserRole)
        
        mime = QMimeData()
        data = QByteArray()
        stream = QDataStream(data, QIODevice.WriteOnly)
        
        # Lineup Position Swap (Column 1)
        is_pos_swap = (self.mode == "lineup" and col == 1)
        
        if is_pos_swap:
            stream.writeInt32(row)
            mime.setData(MIME_POS_SWAP, data)
            text = item.text()
            pixmap = self._create_drag_pixmap(f"守備: {text}", is_pos=True)
        else:
            if player_idx is None: return
            stream.writeInt32(player_idx)
            stream.writeInt32(row)
            mime.setData(MIME_PLAYER_DATA, data)
            
            # Name column index varies
            name_col = 2 if self.mode == "lineup" else 1
            name_text = self.item(row, name_col).text()
            pixmap = self._create_drag_pixmap(name_text, is_pos=False)

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        drag.exec(Qt.MoveAction)

    def _create_drag_pixmap(self, text, is_pos=False):
        width = 160 if is_pos else 200
        height = 40
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 角張った背景 (Rect) - 黒背景
        bg_color = QColor("#222222")
        if is_pos:
            bg_color = QColor("#c0392b") # Darker red for pos

        # 完全に四角い描画
        painter.setBrush(bg_color)
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.drawRect(0, 0, width, height)
        
        # Text
        painter.setPen(Qt.white)
        font = QFont("Yu Gothic UI", 11, QFont.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
        painter.end()
        return pixmap

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_PLAYER_DATA) or event.mimeData().hasFormat(MIME_POS_SWAP):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME_PLAYER_DATA) or event.mimeData().hasFormat(MIME_POS_SWAP):
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        pos = event.position().toPoint()
        target_item = self.itemAt(pos)
        target_row = target_item.row() if target_item else self.rowCount() - 1
        if target_row < 0: target_row = 0

        if event.mimeData().hasFormat(MIME_POS_SWAP):
            if self.mode != "lineup": return
            data = event.mimeData().data(MIME_POS_SWAP)
            stream = QDataStream(data, QIODevice.ReadOnly)
            source_row = stream.readInt32()
            if source_row != target_row:
                self.position_swapped.emit(source_row, target_row)
            event.accept()
            
        elif event.mimeData().hasFormat(MIME_PLAYER_DATA):
            data = event.mimeData().data(MIME_PLAYER_DATA)
            stream = QDataStream(data, QIODevice.ReadOnly)
            player_idx = stream.readInt32()
            
            # Pass data to parent via properties/signals
            self.dropped_player_idx = player_idx
            self.dropped_target_row = target_row
            
            event.accept()
            self.items_changed.emit()

class OrderPage(QWidget):
    """Redesigned Order Page with DH, Color Coding, and Advanced Filters"""
    
    order_saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.current_team = None
        
        # Filter States
        self.show_dev_batters = False
        self.show_dev_pitchers = False
        self.sort_key_batter = "overall" # overall, meet, power, speed, age
        self.sort_key_pitcher = "overall" # overall, speed, control, stamina, age
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Main Tabs
        self.main_tabs = QTabWidget()
        self.main_tabs.setStyleSheet(self._get_main_tab_style())
        
        self.batter_page = self._create_batter_page()
        self.main_tabs.addTab(self.batter_page, "野手オーダー")
        
        self.pitcher_page = self._create_pitcher_page()
        self.main_tabs.addTab(self.pitcher_page, "投手オーダー")
        
        layout.addWidget(self.main_tabs)

    def _create_toolbar(self) -> ToolbarPanel:
        toolbar = ToolbarPanel()
        toolbar.setFixedHeight(50)

        label = QLabel("チーム:")
        label.setStyleSheet(f"color: {self.theme.text_secondary}; margin-left: 12px;")
        toolbar.add_widget(label)

        self.team_selector = QComboBox()
        self.team_selector.setMinimumWidth(200)
        self.team_selector.setFixedHeight(32)
        self.team_selector.currentIndexChanged.connect(self._on_team_changed)
        self.team_selector.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; border-radius: 4px;")
        toolbar.add_widget(self.team_selector)
        
        self.status_label = QLabel("一軍登録: --/--")
        self.status_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; margin-left: 20px;")
        toolbar.add_widget(self.status_label)

        toolbar.add_stretch()
        
        auto_btn = QPushButton("自動編成")
        auto_btn.setCursor(Qt.PointingHandCursor)
        auto_btn.setStyleSheet(f"background: {self.theme.bg_card}; color: {self.theme.text_primary}; padding: 6px 12px; border: 1px solid {self.theme.border}; border-radius: 4px;")
        auto_btn.clicked.connect(self._auto_fill)
        toolbar.add_widget(auto_btn)

        save_btn = QPushButton("保存")
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet(f"background: {self.theme.primary}; color: white; padding: 6px 20px; border: none; border-radius: 4px; font-weight: bold;")
        save_btn.clicked.connect(self._save_order)
        toolbar.add_widget(save_btn)

        return toolbar

    def _create_batter_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {self.theme.border}; width: 1px; }}")

        # LEFT: Order
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 8, 8)
        
        l_header = QLabel("スタメン & ベンチ")
        l_header.setStyleSheet(f"font-weight: bold; color: {self.theme.text_secondary}; font-size: 13px;")
        left_layout.addWidget(l_header)
        
        self.lineup_table = self._create_table("lineup")
        self.lineup_table.setMinimumHeight(350)
        left_layout.addWidget(self.lineup_table)
        
        left_layout.addSpacing(4)
        
        self.bench_table = self._create_table("bench")
        left_layout.addWidget(self.bench_table)
        splitter.addWidget(left_widget)

        # RIGHT: Farm List
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 8, 8, 8)
        
        # Filter/Sort Controls
        ctrl_layout = QHBoxLayout()
        r_header = QLabel("二軍選手一覧")
        r_header.setStyleSheet(f"font-weight: bold; color: {self.theme.text_secondary}; font-size: 13px;")
        ctrl_layout.addWidget(r_header)
        
        ctrl_layout.addStretch()
        
        self.batter_sort_combo = QComboBox()
        self.batter_sort_combo.addItems(["総合力順", "ミート順", "パワー順", "走力順", "年齢順"])
        self.batter_sort_combo.currentIndexChanged.connect(self._refresh_batter_farm_list)
        self.batter_sort_combo.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 2px;")
        ctrl_layout.addWidget(self.batter_sort_combo)
        
        self.batter_dev_check = QCheckBox("育成")
        self.batter_dev_check.setStyleSheet(f"color: {self.theme.text_primary};")
        self.batter_dev_check.stateChanged.connect(self._refresh_batter_farm_list)
        ctrl_layout.addWidget(self.batter_dev_check)
        
        right_layout.addLayout(ctrl_layout)
        
        self.farm_batter_table = self._create_table("farm_batter")
        right_layout.addWidget(self.farm_batter_table)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 400])
        layout.addWidget(splitter)
        return page

    def _create_pitcher_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {self.theme.border}; width: 1px; }}")

        # LEFT
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 8, 8)
        
        l_header = QLabel("投手陣容 (先発・中継ぎ・抑え)")
        l_header.setStyleSheet(f"font-weight: bold; color: {self.theme.text_secondary}; font-size: 13px;")
        left_layout.addWidget(l_header)
        
        self.rotation_table = self._create_table("rotation")
        self.rotation_table.setMinimumHeight(240)
        left_layout.addWidget(self.rotation_table)
        
        left_layout.addSpacing(4)
        
        self.bullpen_table = self._create_table("bullpen")
        left_layout.addWidget(self.bullpen_table)
        splitter.addWidget(left_widget)

        # RIGHT
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 8, 8, 8)
        
        ctrl_layout = QHBoxLayout()
        r_header = QLabel("二軍投手一覧")
        r_header.setStyleSheet(f"font-weight: bold; color: {self.theme.text_secondary}; font-size: 13px;")
        ctrl_layout.addWidget(r_header)
        
        ctrl_layout.addStretch()
        
        self.pitcher_sort_combo = QComboBox()
        self.pitcher_sort_combo.addItems(["総合力順", "球速順", "コン順", "スタ順", "年齢順"])
        self.pitcher_sort_combo.currentIndexChanged.connect(self._refresh_pitcher_farm_list)
        self.pitcher_sort_combo.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 2px;")
        ctrl_layout.addWidget(self.pitcher_sort_combo)
        
        self.pitcher_dev_check = QCheckBox("育成")
        self.pitcher_dev_check.setStyleSheet(f"color: {self.theme.text_primary};")
        self.pitcher_dev_check.stateChanged.connect(self._refresh_pitcher_farm_list)
        ctrl_layout.addWidget(self.pitcher_dev_check)
        
        right_layout.addLayout(ctrl_layout)
        
        self.farm_pitcher_table = self._create_table("farm_pitcher")
        right_layout.addWidget(self.farm_pitcher_table)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([600, 400])
        layout.addWidget(splitter)
        return page

    def _create_table(self, mode) -> DraggableTableWidget:
        table = DraggableTableWidget(mode)
        table.items_changed.connect(lambda: self._on_table_changed(table))
        
        if mode == "lineup":
            cols = ["順", "守", "選手名", "ミ", "パ", "走", "肩", "守", "総合"]
            widths = [30, 40, 130, 35, 35, 35, 35, 35, 45]
            table.position_swapped.connect(self._on_pos_swapped)
            
        elif mode == "bench" or mode == "farm_batter":
            cols = ["適性", "選手名", "ミ", "パ", "走", "肩", "守", "総合"]
            widths = [70, 130, 35, 35, 35, 35, 35, 45]

        elif mode == "rotation" or mode == "bullpen" or mode == "farm_pitcher":
            cols = ["役", "選手名", "球速", "コ", "ス", "変", "先", "中", "抑", "総合"]
            widths = [40, 130, 50, 35, 35, 35, 35, 35, 35, 45]

        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        for i, w in enumerate(widths):
            table.setColumnWidth(i, w)

        table.setStyleSheet(self._get_table_style())
        return table

    def _get_table_style(self):
        return f"""
            QTableWidget {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                gridline-color: {self.theme.border_muted};
                selection-background-color: {self.theme.primary_light}40;
                selection-color: {self.theme.text_primary};
            }}
            QHeaderView::section {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_secondary};
                border: none;
                border-bottom: 1px solid {self.theme.border};
                padding: 4px;
                font-size: 12px;
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: 2px;
                border-bottom: 1px solid {self.theme.border_muted};
            }}
        """
    
    def _get_main_tab_style(self):
        return f"""
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{
                background: {self.theme.bg_dark};
                color: {self.theme.text_secondary};
                padding: 8px 24px;
                border-bottom: 2px solid {self.theme.border};
                font-weight: bold;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                color: {self.theme.primary};
                border-bottom: 2px solid {self.theme.primary};
                background: {self.theme.bg_input};
            }}
        """

    def set_game_state(self, game_state):
        self.game_state = game_state
        if not game_state: return
        self.team_selector.clear()
        for team in game_state.teams:
            self.team_selector.addItem(team.name, team)
        
        if game_state.player_team:
            idx = game_state.teams.index(game_state.player_team)
            self.team_selector.setCurrentIndex(idx)

    def _on_team_changed(self, index):
        if index >= 0:
            self.current_team = self.team_selector.itemData(index)
            self._refresh_all()

    def _ensure_lists_initialized(self):
        """Ensure team lists have correct length to avoid crashes"""
        team = self.current_team
        if not team: return
        
        # Lineup: 9 slots
        while len(team.current_lineup) < 9:
            team.current_lineup.append(-1)
            
        # Rotation: 6 slots
        while len(team.rotation) < 6:
            team.rotation.append(-1)
            
        # Setup: 6 slots
        while len(team.setup_pitchers) < 6:
            team.setup_pitchers.append(-1)
            
        # Lineup positions
        if not hasattr(team, 'lineup_positions') or len(team.lineup_positions) != 9:
            team.lineup_positions = ["捕", "一", "二", "三", "遊", "左", "中", "右", "DH"]

    def _refresh_all(self):
        if not self.current_team: return
        
        self._ensure_lists_initialized()
        
        self._refresh_lineup_table()
        self._refresh_bench_table()
        self._refresh_batter_farm_list()
        self._refresh_rotation_table()
        self._refresh_bullpen_table()
        self._refresh_pitcher_farm_list()
        self._update_status_label()

    def _update_status_label(self):
        team = self.current_team
        # Count unique non-negative indices in all order slots
        active_set = set()
        active_set.update([x for x in team.current_lineup if x >= 0])
        active_set.update([x for x in team.bench_batters if x >= 0])
        active_set.update([x for x in team.rotation if x >= 0])
        active_set.update([x for x in team.setup_pitchers if x >= 0])
        if team.closer_idx >= 0: active_set.add(team.closer_idx)
        
        count = len(active_set)
        limit = team.ACTIVE_ROSTER_LIMIT
        self.status_label.setText(f"一軍登録数: {count}/{limit}")
        color = self.theme.success if count <= limit else self.theme.danger
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold; margin-left: 20px;")

    # === Data Helpers ===
    
    def _create_item(self, text, align=Qt.AlignCenter, rank_color=False, pos_badge=None, is_star=False):
        """Rich Table Item Factory"""
        item = QTableWidgetItem(str(text))
        item.setTextAlignment(align)
        
        if pos_badge:
            item.setBackground(QColor(get_pos_color(pos_badge)))
            item.setForeground(Qt.white)
            font = QFont()
            font.setBold(True)
            item.setFont(font)
        elif rank_color:
            color = get_rank_color(text, self.theme)
            item.setForeground(color)
            font = QFont()
            font.setBold(True)
            item.setFont(font)
        elif is_star:
            item.setForeground(QColor("#FFD700")) # Gold for overall star
            font = QFont()
            font.setBold(True)
            item.setFont(font)
            
        return item

    def _get_short_pos(self, p):
        mapping = {
            "投手": "投", "捕手": "捕", "一塁手": "一", "二塁手": "二",
            "三塁手": "三", "遊撃手": "遊", "左翼手": "左", "中堅手": "中",
            "右翼手": "右", "指名打者": "DH"
        }
        return mapping.get(p.position.value, p.position.value[:1])

    def _format_aptitude(self, p):
        """Create a string like '二A 遊B'"""
        if p.position.value == "投手": return "投手"
        parts = []
        if hasattr(p.stats, 'defense_ranges'):
            # Sort by rank score roughly
            def sort_key(item): return item[1]
            sorted_ranges = sorted(p.stats.defense_ranges.items(), key=sort_key, reverse=True)
            
            mapping = {"捕手":"捕","一塁手":"一","二塁手":"二","三塁手":"三",
                       "遊撃手":"遊","左翼手":"左","中堅手":"中","右翼手":"右"}
            
            for pos, val in sorted_ranges:
                if val >= 20: # Show only relevant
                    short = mapping.get(pos, pos[0])
                    rank = p.stats.get_rank(val)
                    parts.append(f"{short}{rank}")
        return " ".join(parts[:3]) # Limit to 3

    # === Table Fillers ===

    def _refresh_lineup_table(self):
        team = self.current_team
        table = self.lineup_table
        table.setRowCount(9)
            
        for i in range(9):
            p_idx = -1
            if i < len(team.current_lineup):
                p_idx = team.current_lineup[i]
            
            pos_label = team.lineup_positions[i]
            
            # 1. Order
            table.setItem(i, 0, self._create_item(f"{i+1}"))
            
            # 2. Position (Draggable)
            pos_item = self._create_item(pos_label, pos_badge=pos_label)
            pos_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
            table.setItem(i, 1, pos_item)
            
            if p_idx != -1 and p_idx < len(team.players):
                p = team.players[p_idx]
                table.setItem(i, 2, self._create_item(p.name, Qt.AlignLeft))
                
                s = p.stats
                table.setItem(i, 3, self._create_item(s.get_rank(s.contact), rank_color=True))
                table.setItem(i, 4, self._create_item(s.get_rank(s.power), rank_color=True))
                table.setItem(i, 5, self._create_item(s.get_rank(s.speed), rank_color=True))
                table.setItem(i, 6, self._create_item(s.get_rank(s.arm), rank_color=True))
                table.setItem(i, 7, self._create_item(s.get_rank(s.error), rank_color=True))
                table.setItem(i, 8, self._create_item(f"★{p.overall_rating}", is_star=True))
                
                # Store user role
                for c in range(table.columnCount()):
                    if table.item(i, c): table.item(i, c).setData(Qt.UserRole, p_idx)
            else:
                self._clear_row(table, i, 2)

    def _refresh_bench_table(self):
        team = self.current_team
        table = self.bench_table
        table.setRowCount(len(team.bench_batters) + 2) # Extra space for dropping
        
        for i, p_idx in enumerate(team.bench_batters):
            if p_idx != -1 and p_idx < len(team.players):
                p = team.players[p_idx]
                self._fill_batter_row(table, i, p, p_idx)
            else:
                self._clear_row(table, i, 0)
        
        # Clear remaining
        for i in range(len(team.bench_batters), table.rowCount()):
             self._clear_row(table, i, 0)

    def _refresh_batter_farm_list(self):
        team = self.current_team
        table = self.farm_batter_table
        
        active_ids = set(team.current_lineup + team.bench_batters)
        candidates = []
        for i, p in enumerate(team.players):
            if p.position.value != "投手" and i not in active_ids:
                if not self.batter_dev_check.isChecked() and p.is_developmental: continue
                candidates.append((i, p))
                
        # Sort
        key = self.batter_sort_combo.currentText()
        if "総合" in key: candidates.sort(key=lambda x: x[1].overall_rating, reverse=True)
        elif "ミート" in key: candidates.sort(key=lambda x: x[1].stats.contact, reverse=True)
        elif "パワー" in key: candidates.sort(key=lambda x: x[1].stats.power, reverse=True)
        elif "走力" in key: candidates.sort(key=lambda x: x[1].stats.speed, reverse=True)
        elif "年齢" in key: candidates.sort(key=lambda x: x[1].age)
        
        table.setRowCount(len(candidates))
        for i, (p_idx, p) in enumerate(candidates):
            self._fill_batter_row(table, i, p, p_idx)

    def _fill_batter_row(self, table, row, p, p_idx):
        apt = self._format_aptitude(p)
        table.setItem(row, 0, self._create_item(apt))
        table.setItem(row, 1, self._create_item(p.name, Qt.AlignLeft))
        
        s = p.stats
        table.setItem(row, 2, self._create_item(s.get_rank(s.contact), rank_color=True))
        table.setItem(row, 3, self._create_item(s.get_rank(s.power), rank_color=True))
        table.setItem(row, 4, self._create_item(s.get_rank(s.speed), rank_color=True))
        table.setItem(row, 5, self._create_item(s.get_rank(s.arm), rank_color=True))
        table.setItem(row, 6, self._create_item(s.get_rank(s.error), rank_color=True))
        table.setItem(row, 7, self._create_item(f"★{p.overall_rating}", is_star=True))
        
        for c in range(table.columnCount()):
            if table.item(row, c): table.item(row, c).setData(Qt.UserRole, p_idx)

    def _refresh_rotation_table(self):
        team = self.current_team
        table = self.rotation_table
        table.setRowCount(6)
        for i in range(6):
            p_idx = -1
            if i < len(team.rotation):
                p_idx = team.rotation[i]
            self._fill_pitcher_row_role(table, i, "先発", p_idx)

    def _refresh_bullpen_table(self):
        team = self.current_team
        table = self.bullpen_table
        table.setRowCount(7)
        # Setup 1-6
        for i in range(6):
            p_idx = -1
            if i < len(team.setup_pitchers):
                p_idx = team.setup_pitchers[i]
            self._fill_pitcher_row_role(table, i, "中継", p_idx)
        # Closer
        self._fill_pitcher_row_role(table, 6, "抑え", team.closer_idx)

    def _fill_pitcher_row_role(self, table, row, role_lbl, p_idx):
        table.setItem(row, 0, self._create_item(role_lbl, pos_badge=role_lbl[0])) # Color badge
        if p_idx != -1 and p_idx < len(self.current_team.players):
            p = self.current_team.players[p_idx]
            self._fill_pitcher_data(table, row, p, p_idx, start_col=1)
        else:
            self._clear_row(table, row, 1)

    def _refresh_pitcher_farm_list(self):
        team = self.current_team
        table = self.farm_pitcher_table
        
        active_ids = set([x for x in team.rotation if x >= 0])
        active_ids.update([x for x in team.setup_pitchers if x >= 0])
        if team.closer_idx != -1: active_ids.add(team.closer_idx)
        
        candidates = []
        for i, p in enumerate(team.players):
            if p.position.value == "投手" and i not in active_ids:
                if not self.pitcher_dev_check.isChecked() and p.is_developmental: continue
                candidates.append((i, p))
                
        # Sort
        key = self.pitcher_sort_combo.currentText()
        if "総合" in key: candidates.sort(key=lambda x: x[1].overall_rating, reverse=True)
        elif "球速" in key: candidates.sort(key=lambda x: x[1].stats.speed, reverse=True)
        elif "コン" in key: candidates.sort(key=lambda x: x[1].stats.control, reverse=True)
        elif "スタ" in key: candidates.sort(key=lambda x: x[1].stats.stamina, reverse=True)
        elif "年齢" in key: candidates.sort(key=lambda x: x[1].age)
        
        table.setRowCount(len(candidates))
        for i, (p_idx, p) in enumerate(candidates):
            # Determine role apt
            role = p.pitch_type.value[:2]
            table.setItem(i, 0, self._create_item(role))
            self._fill_pitcher_data(table, i, p, p_idx, start_col=1)

    def _fill_pitcher_data(self, table, row, p, p_idx, start_col):
        table.setItem(row, start_col, self._create_item(p.name, Qt.AlignLeft))
        kmh = p.stats.speed_to_kmh()
        table.setItem(row, start_col+1, self._create_item(f"{kmh}km"))
        table.setItem(row, start_col+2, self._create_item(p.stats.get_rank(p.stats.control), rank_color=True))
        table.setItem(row, start_col+3, self._create_item(p.stats.get_rank(p.stats.stamina), rank_color=True))
        table.setItem(row, start_col+4, self._create_item(p.stats.get_rank(p.stats.stuff), rank_color=True))
        
        # Aptitude Icons
        st = "◎" if p.pitch_type.value == "先発" else "△"
        rl = "◎" if p.pitch_type.value == "中継ぎ" else "△"
        cl = "◎" if p.pitch_type.value == "抑え" else "△"
        table.setItem(row, start_col+5, self._create_item(st))
        table.setItem(row, start_col+6, self._create_item(rl))
        table.setItem(row, start_col+7, self._create_item(cl))
        table.setItem(row, start_col+8, self._create_item(f"★{p.overall_rating}", is_star=True))

        for c in range(table.columnCount()):
            if table.item(row, c): table.item(row, c).setData(Qt.UserRole, p_idx)

    def _clear_row(self, table, row, start_col):
        for c in range(start_col, table.columnCount()):
            table.setItem(row, c, QTableWidgetItem(""))
        if start_col < table.columnCount():
            table.setItem(row, start_col, QTableWidgetItem("---"))

    # === Event Handlers ===
    
    def _on_table_changed(self, table):
        """Handle Drops"""
        if not hasattr(table, 'dropped_player_idx'): return
        p_idx = table.dropped_player_idx
        row = table.dropped_target_row
        team = self.current_team
        
        self._remove_player_from_active(p_idx)
        
        if table == self.lineup_table:
            while len(team.current_lineup) <= row: team.current_lineup.append(-1)
            team.current_lineup[row] = p_idx
        elif table == self.bench_table:
            if row < len(team.bench_batters): team.bench_batters[row] = p_idx
            else: team.bench_batters.append(p_idx)
        elif table == self.rotation_table:
            while len(team.rotation) <= row: team.rotation.append(-1)
            team.rotation[row] = p_idx
        elif table == self.bullpen_table:
            if row == 6: team.closer_idx = p_idx
            else:
                while len(team.setup_pitchers) <= row: team.setup_pitchers.append(-1)
                team.setup_pitchers[row] = p_idx
        
        self._refresh_all()
        del table.dropped_player_idx

    def _on_pos_swapped(self, r1, r2):
        """Swap position assignments in lineup"""
        team = self.current_team
        pos_list = team.lineup_positions
        if r1 < 9 and r2 < 9:
            pos_list[r1], pos_list[r2] = pos_list[r2], pos_list[r1]
            self._refresh_lineup_table()

    def _remove_player_from_active(self, idx):
        t = self.current_team
        if idx in t.current_lineup: t.current_lineup[t.current_lineup.index(idx)] = -1
        if idx in t.bench_batters: t.bench_batters.remove(idx)
        if idx in t.rotation: t.rotation[t.rotation.index(idx)] = -1
        if idx in t.setup_pitchers: t.setup_pitchers[t.setup_pitchers.index(idx)] = -1
        if t.closer_idx == idx: t.closer_idx = -1

    def _auto_fill(self):
        if not self.current_team: return
        t = self.current_team
        
        # Reset
        t.current_lineup = [-1] * 9
        t.bench_batters = []
        t.rotation = [-1] * 6
        t.setup_pitchers = [-1] * 6
        t.closer_idx = -1
        t.lineup_positions = ["捕", "一", "二", "三", "遊", "左", "中", "右", "DH"]
        
        # Logic: Pick best players for positions
        # Simple implementation: Sort batters by rating, fill positions first, then DH, then bench
        batters = [i for i,p in enumerate(t.players) if p.position.value != "投手" and not p.is_developmental]
        batters.sort(key=lambda i: t.players[i].overall_rating, reverse=True)
        
        # Fill Lineup (Naive)
        for i in range(min(9, len(batters))):
            t.current_lineup[i] = batters[i]
                
        # Fill Bench
        if len(batters) > 9:
            t.bench_batters = batters[9:15] # Max 6 bench
            
        # Pitchers
        pitchers = [i for i,p in enumerate(t.players) if p.position.value == "投手" and not p.is_developmental]
        pitchers.sort(key=lambda i: t.players[i].overall_rating, reverse=True)
        
        # Starters
        starters = [i for i in pitchers if t.players[i].pitch_type.value == "先発"]
        relievers = [i for i in pitchers if i not in starters]
        
        # Fallback if shortage
        if len(starters) < 6: starters += relievers[:6-len(starters)]
        
        t.rotation = starters[:6]
        rem_relievers = [i for i in relievers if i not in t.rotation]
        
        if rem_relievers:
            t.closer_idx = rem_relievers[0]
            t.setup_pitchers = rem_relievers[1:7]
            
        self._refresh_all()

    def _save_order(self):
        self.order_saved.emit()
        self._update_status_label()
        QMessageBox.information(self, "保存", "オーダーを保存しました。")