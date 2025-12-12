# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Order Page
Advanced Drag & Drop Order Management with DH support
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QSplitter, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QScrollArea, QSizePolicy, QCheckBox, QStyledItemDelegate,
    QStyle
)
from PySide6.QtCore import Qt, Signal, QMimeData, QByteArray, QDataStream, QIODevice, QPoint, QSize
from PySide6.QtGui import QColor, QFont, QIcon, QDrag, QPixmap, QPainter, QBrush, QPen

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.panels import ToolbarPanel
from UI.widgets.tables import SortableTableWidgetItem, RatingDelegate
from models import PlayerStats, TeamLevel

# MIME Types
MIME_PLAYER_DATA = "application/x-pennant-player-data"
MIME_POS_SWAP = "application/x-pennant-pos-swap"

# Custom Role for Drag & Drop Player Index
ROLE_PLAYER_IDX = Qt.UserRole + 1

def get_pos_color(pos: str) -> str:
    """Return background color code for position badge"""
    if pos == "投": return "#3498db"
    if pos == "捕": return "#27ae60"
    if pos in ["一", "二", "三", "遊"]: return "#e67e22"
    if pos in ["左", "中", "右"]: return "#9b59b6"
    if pos == "DH": return "#e74c3c"
    return "#7f8c8d"

class DefenseDelegate(QStyledItemDelegate):
    """Custom delegate to draw Main Position Large and Sub Positions Small"""
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme

    def paint(self, painter, option, index):
        painter.save()
        
        raw_data = index.data(Qt.DisplayRole)
        text = str(raw_data) if raw_data is not None else ""

        if "|" in text:
            parts = text.split("|", 1)
            main_pos = parts[0]
            sub_pos = parts[1] if len(parts) > 1 else ""
        else:
            main_pos, sub_pos = text, ""

        rect = option.rect
        
        # 1. Main Position (Large)
        if option.state & QStyle.StateFlag.State_Selected:
             painter.setPen(QColor(self.theme.text_primary)) 
        else:
             fg_color = index.model().data(index, Qt.ForegroundRole)
             if isinstance(fg_color, QBrush): 
                 fg_color = fg_color.color()
             painter.setPen(fg_color if fg_color else QColor(self.theme.text_primary))
             
        font = painter.font()
        font.setPointSize(12) 
        font.setBold(True)
        painter.setFont(font)
        
        fm = painter.fontMetrics()
        main_width = fm.horizontalAdvance(main_pos)
        
        main_rect = rect.adjusted(4, 0, 0, 0)
        painter.drawText(main_rect, Qt.AlignLeft | Qt.AlignVCenter, main_pos)
        
        # 2. Sub Positions (Small)
        if sub_pos:
            font.setPointSize(9)
            font.setBold(False)
            painter.setFont(font)
            
            if option.state & QStyle.StateFlag.State_Selected:
                painter.setPen(QColor(self.theme.text_secondary))
            else:
                painter.setPen(QColor(self.theme.text_secondary))
            
            sub_rect = rect.adjusted(main_width + 10, 0, 0, 0)
            painter.drawText(sub_rect, Qt.AlignLeft | Qt.AlignVCenter, sub_pos)
        
        # 3. Draw Bottom Border manually
        painter.setPen(QPen(QColor(self.theme.border_muted), 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
            
        painter.restore()

class DraggableTableWidget(QTableWidget):
    """Enhanced TableWidget supporting Drag & Drop for Order Management"""
    
    items_changed = Signal()
    position_swapped = Signal(int, int)

    def __init__(self, mode="batter", parent=None):
        super().__init__(parent)
        self.mode = mode 
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
        
        self.setSortingEnabled(False)
        
        if "farm" in mode:
            header = self.horizontalHeader()
            header.setSectionsClickable(True)
            header.setSortIndicatorShown(True)
            header.sectionClicked.connect(self._on_header_clicked)

    def _on_header_clicked(self, logicalIndex):
        header_text = self.horizontalHeaderItem(logicalIndex).text()
        if header_text in ["選手名", "適正", "守備適正"]:
            return

        header = self.horizontalHeader()
        current_column = header.sortIndicatorSection()
        current_order = header.sortIndicatorOrder()
        
        if current_column != logicalIndex:
            new_order = Qt.DescendingOrder
        else:
            if current_order == Qt.DescendingOrder:
                new_order = Qt.AscendingOrder
            else:
                new_order = Qt.DescendingOrder

        self.sortItems(logicalIndex, new_order)
        header.setSortIndicator(logicalIndex, new_order)

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item: return

        row = item.row()
        col = item.column()
        player_idx = item.data(ROLE_PLAYER_IDX)
        
        mime = QMimeData()
        data = QByteArray()
        stream = QDataStream(data, QIODevice.WriteOnly)
        
        is_pos_swap = (self.mode == "lineup" and col == 1)
        
        if is_pos_swap:
            stream.writeInt32(row)
            mime.setData(MIME_POS_SWAP, data)
            text = item.text()
            pixmap = self._create_drag_pixmap(text, is_pos=True)
        else:
            if player_idx is None: return
            stream.writeInt32(player_idx)
            stream.writeInt32(row)
            mime.setData(MIME_PLAYER_DATA, data)
            
            if self.mode == "lineup": name_col = 3 
            elif self.mode == "bench": name_col = 2 
            elif self.mode == "farm_batter": name_col = 1 
            elif self.mode in ["rotation", "bullpen"]: name_col = 2 
            elif self.mode == "farm_pitcher": name_col = 2 
            else: name_col = 1
            
            name_item = self.item(row, name_col)
            name_text = name_item.text() if name_item else "Player"
            pixmap = self._create_drag_pixmap(name_text, is_pos=False)

        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        drag.exec(Qt.MoveAction)

    def _create_drag_pixmap(self, text, is_pos=False):
        width = 40 if is_pos else 200
        height = 40
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        bg_color = QColor("#222222")
        if is_pos:
            bg_color = QColor("#c0392b") 

        painter.setBrush(bg_color)
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.drawRect(0, 0, width, height)
        
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
            
            self.dropped_player_idx = player_idx
            self.dropped_target_row = target_row
            
            event.accept()
            self.items_changed.emit()

class OrderPage(QWidget):
    """Redesigned Order Page with DH, Color Coding, and Advanced Filters"""
    
    order_saved = Signal()
    player_detail_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.current_team = None
        
        self.defense_delegate = DefenseDelegate(self.theme)
        self.rating_delegate = RatingDelegate(self)
        
        # 編集中の状態を保持する辞書（保存ボタンを押すまではここにのみ反映）
        self.edit_state = {}
        self.has_unsaved_changes = False
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        self.main_tabs = QTabWidget()
        self.main_tabs.setStyleSheet(self._get_main_tab_style())
        
        self.batter_page = self._create_batter_page()
        self.main_tabs.addTab(self.batter_page, "野手オーダー")
        
        self.pitcher_page = self._create_pitcher_page()
        self.main_tabs.addTab(self.pitcher_page, "投手オーダー")
        
        layout.addWidget(self.main_tabs)

    def showEvent(self, event):
        """タブが表示されたときにデータを更新する"""
        super().showEvent(event)
        # 操作せずとも最新のデータを反映させる
        if self.current_team:
            self._load_team_data()
            self._refresh_all()

    def _create_toolbar(self) -> ToolbarPanel:
        toolbar = ToolbarPanel()
        toolbar.setFixedHeight(50)

        self.team_name_label = QLabel("チーム名")
        self.team_name_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; font-size: 16px; margin-left: 12px;")
        toolbar.add_widget(self.team_name_label)
        
        self.status_label = QLabel("一軍登録: --/--")
        self.status_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; margin-left: 20px;")
        toolbar.add_widget(self.status_label)

        toolbar.add_stretch()
        
        auto_btn = QPushButton("自動編成")
        auto_btn.setCursor(Qt.PointingHandCursor)
        auto_btn.setStyleSheet(f"background: {self.theme.bg_card}; color: {self.theme.text_primary}; padding: 6px 12px; border: 1px solid {self.theme.border}; border-radius: 4px;")
        auto_btn.clicked.connect(self._auto_fill)
        toolbar.add_widget(auto_btn)

        self.set_best_btn = QPushButton("ベストオーダーに設定")
        self.set_best_btn.setCursor(Qt.PointingHandCursor)
        self.set_best_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.accent_blue};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                margin-right: 10px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent_blue_hover};
            }}
        """)
        self.set_best_btn.clicked.connect(self._set_current_as_best)
        toolbar.add_widget(self.set_best_btn)

        self.save_btn = QPushButton("保存")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.primary};
                color: {self.theme.text_highlight};
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }}
            QPushButton:disabled {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_muted};
            }}
        """)
        self.save_btn.clicked.connect(self._save_changes)
        self.save_btn.setEnabled(False)
        toolbar.add_widget(self.save_btn)

        self.cancel_btn = QPushButton("キャンセル")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.theme.error};
                border: 1px solid {self.theme.error};
                border-radius: 4px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.error}22;
            }}
            QPushButton:disabled {{
                color: {self.theme.text_muted};
                border-color: {self.theme.border};
            }}
        """)
        self.cancel_btn.clicked.connect(self._discard_changes)
        self.cancel_btn.setEnabled(False)
        toolbar.add_widget(self.cancel_btn)

        return toolbar

    def _create_batter_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {self.theme.border}; width: 1px; }}")

        # LEFT
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

        # RIGHT
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 8, 8, 8)
        
        ctrl_layout = QHBoxLayout()
        r_header = QLabel("野手リスト (支配下)")
        r_header.setStyleSheet(f"font-weight: bold; color: {self.theme.text_secondary}; font-size: 13px;")
        ctrl_layout.addWidget(r_header)
        
        ctrl_layout.addStretch()
        
        self.batter_pos_filter = QComboBox()
        self.batter_pos_filter.addItems(["全ポジション", "捕手", "一塁手", "二塁手", "三塁手", "遊撃手", "外野手"])
        self.batter_pos_filter.currentIndexChanged.connect(self._refresh_batter_farm_list)
        self.batter_pos_filter.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 2px;")
        ctrl_layout.addWidget(self.batter_pos_filter)
        
        right_layout.addLayout(ctrl_layout)
        
        self.farm_batter_table = self._create_table("farm_batter")
        right_layout.addWidget(self.farm_batter_table)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([500, 500])
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
        r_header = QLabel("投手リスト (支配下)")
        r_header.setStyleSheet(f"font-weight: bold; color: {self.theme.text_secondary}; font-size: 13px;")
        ctrl_layout.addWidget(r_header)
        
        ctrl_layout.addStretch()
        
        self.pitcher_type_filter = QComboBox()
        self.pitcher_type_filter.addItems(["全タイプ", "先発", "中継ぎ", "抑え"])
        self.pitcher_type_filter.currentIndexChanged.connect(self._refresh_pitcher_farm_list)
        self.pitcher_type_filter.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 2px;")
        ctrl_layout.addWidget(self.pitcher_type_filter)
        
        right_layout.addLayout(ctrl_layout)
        
        self.farm_pitcher_table = self._create_table("farm_pitcher")
        right_layout.addWidget(self.farm_pitcher_table)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([500, 500])
        layout.addWidget(splitter)
        return page

    def _create_table(self, mode) -> DraggableTableWidget:
        table = DraggableTableWidget(mode)
        table.items_changed.connect(lambda: self._on_table_changed(table))
        
        table.itemDoubleClicked.connect(self._on_player_double_clicked)

        if mode == "lineup":
            cols = ["順", "守", "調", "選手名", "ミ", "パ", "走", "肩", "守", "適正", "総合"]
            widths = [30, 40, 30, 130, 35, 35, 35, 35, 35, 80, 45]
            table.position_swapped.connect(self._on_pos_swapped)
            for c in [4, 5, 6, 7, 8]:
                table.setItemDelegateForColumn(c, self.rating_delegate)
            table.setItemDelegateForColumn(9, self.defense_delegate)
            
        elif mode == "bench":
            cols = ["適性", "調", "選手名", "ミ", "パ", "走", "肩", "守", "適正", "総合"]
            widths = [70, 30, 130, 35, 35, 35, 35, 35, 80, 45]
            for c in [3, 4, 5, 6, 7]:
                table.setItemDelegateForColumn(c, self.rating_delegate)
            table.setItemDelegateForColumn(8, self.defense_delegate)

        elif mode == "farm_batter":
            cols = ["調", "選手名", "年齢", "ミ", "パ", "走", "肩", "守", "守備適正", "総合"]
            widths = [30, 130, 40, 35, 35, 35, 35, 35, 80, 45]
            for c in [3, 4, 5, 6, 7]:
                table.setItemDelegateForColumn(c, self.rating_delegate)
            table.setItemDelegateForColumn(8, self.defense_delegate)

        elif mode == "rotation" or mode == "bullpen":
            cols = ["役", "調", "選手名", "球速", "コ", "ス", "変", "先", "中", "抑", "総合"]
            widths = [40, 30, 130, 50, 35, 35, 35, 35, 35, 35, 45]
            for c in [4, 5, 6]:
                table.setItemDelegateForColumn(c, self.rating_delegate)

        elif mode == "farm_pitcher":
            cols = ["タイプ", "調", "選手名", "年齢", "球速", "コ", "ス", "変", "先", "中", "抑", "総合"]
            widths = [45, 30, 130, 40, 50, 35, 35, 35, 35, 35, 35, 45]
            for c in [5, 6, 7]:
                table.setItemDelegateForColumn(c, self.rating_delegate)

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
                selection-background-color: {self.theme.bg_input};
                outline: none;
            }}
            QTableWidget::item:selected {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_primary};
                border: none;
                outline: none;
            }}
            QTableWidget::item:focus {{
                background-color: {self.theme.bg_input};
                border: none;
                outline: none;
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
            QHeaderView::section:hover {{
                background-color: {self.theme.bg_hover};
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
        
        if game_state.player_team:
            self.current_team = game_state.player_team
            self.team_name_label.setText(self.current_team.name)
            
            # 初期化と表示更新
            self._ensure_lists_initialized()
            self._load_team_data()
            self._refresh_all()
        else:
            self.current_team = None
            self.team_name_label.setText("チーム選択なし")

    def _ensure_lists_initialized(self):
        team = self.current_team
        if not team: return
        
        while len(team.current_lineup) < 9: team.current_lineup.append(-1)
        while len(team.rotation) < 8: team.rotation.append(-1)
        while len(team.setup_pitchers) < 8: team.setup_pitchers.append(-1)
        if not hasattr(team, 'closers'): team.closers = []
        while len(team.closers) < 2: team.closers.append(-1)
            
        if not hasattr(team, 'lineup_positions') or len(team.lineup_positions) != 9:
            team.lineup_positions = ["捕", "一", "二", "三", "遊", "左", "中", "右", "DH"]

    def _load_team_data(self):
        """チームデータをローカルの編集用ステートにコピー"""
        if not self.current_team: return
        
        self.edit_state = {
            'current_lineup': list(self.current_team.current_lineup),
            'lineup_positions': list(self.current_team.lineup_positions),
            'bench_batters': list(self.current_team.bench_batters),
            'rotation': list(self.current_team.rotation),
            'setup_pitchers': list(self.current_team.setup_pitchers),
            'closers': list(self.current_team.closers)
        }
        self.has_unsaved_changes = False
        self.save_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)

    def _mark_as_changed(self):
        self.has_unsaved_changes = True
        self.save_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)

    def _save_changes(self):
        if not self.current_team: return
        t = self.current_team
        
        # --- バリデーションチェック ---
        
        # 1. 基礎チェック (人数)
        valid_starters = len([x for x in self.edit_state['current_lineup'] if x != -1])
        valid_rotation = len([x for x in self.edit_state['rotation'] if x != -1])
        
        if valid_starters < 9:
            QMessageBox.warning(self, "エラー", "スタメンが9人未満です。保存できません。")
            return
        if valid_rotation == 0:
            QMessageBox.warning(self, "エラー", "先発投手が設定されていません。保存できません。")
            return

        # 2. スタメンの怪我人チェック & 再登録待機選手のチェック
        active_ids = set()
        active_ids.update([x for x in self.edit_state['current_lineup'] if x != -1])
        active_ids.update([x for x in self.edit_state['bench_batters'] if x != -1])
        active_ids.update([x for x in self.edit_state['rotation'] if x != -1])
        active_ids.update([x for x in self.edit_state['setup_pitchers'] if x != -1])
        active_ids.update([x for x in self.edit_state['closers'] if x != -1])

        invalid_players = []
        for p_idx in active_ids:
            if 0 <= p_idx < len(t.players):
                p = t.players[p_idx]
                
                # スタメンに怪我人がいるかチェック
                if p_idx in self.edit_state['current_lineup']:
                    if p.is_injured:
                        invalid_players.append(f"{p.name} (怪我: スタメン不可)")
                
                # 再登録待機チェック (ベンチ・投手含め一軍全体NG)
                if hasattr(p, 'days_until_promotion') and p.days_until_promotion > 0:
                    invalid_players.append(f"{p.name} (登録抹消中: 残{p.days_until_promotion}日)")

        if invalid_players:
            msg = "以下の選手に問題があるため保存できません：\n\n" + "\n".join(invalid_players)
            QMessageBox.warning(self, "保存不可", msg)
            return

        # --- ロースター変更処理（登録抹消・昇格） ---
        
        # 現在の一軍メンバーセット
        old_roster_set = set(t.active_roster)
        
        # 新しい一軍メンバーセット
        new_roster_set = active_ids # 上で作成済み
        
        # 1. 登録抹消（二軍降格）処理
        # 元々一軍にいたが、新編成で外れた選手 -> 10日間の再登録不可ペナルティ
        demoted = old_roster_set - new_roster_set
        for p_idx in demoted:
            if 0 <= p_idx < len(t.players):
                p = t.players[p_idx]
                p.days_until_promotion = 10  # ★10日間の再登録禁止
                p.team_level = TeamLevel.SECOND
                
                # リスト更新
                if p_idx in t.active_roster:
                    t.active_roster.remove(p_idx)
                if p_idx not in t.farm_roster:
                    t.farm_roster.append(p_idx)
                    
        # 2. 昇格処理
        # 新編成で追加された選手
        promoted = new_roster_set - old_roster_set
        for p_idx in promoted:
            if 0 <= p_idx < len(t.players):
                p = t.players[p_idx]
                p.days_until_promotion = 0 # リセット
                p.team_level = TeamLevel.FIRST
                
                if p_idx not in t.active_roster:
                    t.active_roster.append(p_idx)
                if p_idx in t.farm_roster:
                    t.farm_roster.remove(p_idx)
                if p_idx in t.third_roster:
                    t.third_roster.remove(p_idx)

        # 各種オーダーリストの反映
        t.current_lineup = list(self.edit_state['current_lineup'])
        t.lineup_positions = list(self.edit_state['lineup_positions'])
        t.bench_batters = list(self.edit_state['bench_batters'])
        t.rotation = list(self.edit_state['rotation'])
        t.setup_pitchers = list(self.edit_state['setup_pitchers'])
        t.closers = list(self.edit_state['closers'])
        
        self.order_saved.emit()
        self._load_team_data() # 状態リセット
        self._update_status_label()
        QMessageBox.information(self, "保存完了", "オーダーを保存しました。\n一軍から外れた選手は10日間再登録できません。")

    def _discard_changes(self):
        if not self.current_team: return
        self._load_team_data() # リロード（変更破棄）
        self._refresh_all()

    def _set_current_as_best(self):
        if not self.current_team: return
        
        if self.has_unsaved_changes:
            QMessageBox.warning(self, "警告", "変更が保存されていません。先に保存してください。")
            return
            
        reply = QMessageBox.question(
            self, 'ベストオーダー設定',
            '現在表示されているオーダーを「ベストオーダー」として設定しますか？\n'
            '（試合スキップ時や自動編成の際、このオーダーが優先的に使用されます）',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.current_team.best_order = list(self.edit_state['current_lineup'])
            QMessageBox.information(self, "設定完了", "ベストオーダーを設定しました。")

    def _refresh_all(self):
        if not self.current_team or not self.edit_state: return
        
        self._refresh_lineup_table()
        self._refresh_bench_table()
        self._refresh_batter_farm_list()
        self._refresh_rotation_table()
        self._refresh_bullpen_table()
        self._refresh_pitcher_farm_list()
        self._update_status_label()

    def _get_active_player_count(self) -> int:
        if not self.current_team or not self.edit_state: return 0
        active_set = set()
        active_set.update([x for x in self.edit_state['current_lineup'] if x >= 0])
        active_set.update([x for x in self.edit_state['bench_batters'] if x >= 0])
        active_set.update([x for x in self.edit_state['rotation'] if x >= 0])
        active_set.update([x for x in self.edit_state['setup_pitchers'] if x >= 0])
        active_set.update([x for x in self.edit_state['closers'] if x >= 0])
        return len(active_set)

    def _update_status_label(self):
        if not self.current_team: return
        count = self._get_active_player_count()
        limit = 31
        if hasattr(self.current_team, 'ACTIVE_ROSTER_LIMIT'):
            limit = self.current_team.ACTIVE_ROSTER_LIMIT

        self.status_label.setText(f"一軍登録数: {count}/{limit}")
        color = self.theme.success if count <= limit else self.theme.danger
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold; margin-left: 20px;")

    # === Data Helpers ===
    
    def _create_item(self, value, align=Qt.AlignCenter, rank_color=False, pos_badge=None, is_star=False, sort_val=None, text_color=None):
        item = SortableTableWidgetItem()
        
        if rank_color:
            if sort_val is None: sort_val = value
            item.setData(Qt.UserRole, value)
            item.setData(Qt.DisplayRole, "")
        else:
            item.setText(str(value))
            if pos_badge:
                item.setBackground(QColor(get_pos_color(pos_badge)))
                item.setForeground(Qt.white)
                font = QFont()
                font.setBold(True)
                item.setFont(font)
            elif is_star:
                item.setForeground(QColor("#FFD700"))
                font = QFont()
                font.setBold(True)
                item.setFont(font)
        
        if text_color:
            item.setForeground(text_color)

        item.setTextAlignment(align)
        
        if sort_val is not None:
             item.setData(Qt.UserRole, sort_val)
        elif not rank_color:
            try:
                if isinstance(value, str) and "★" in value:
                    num = int(value.replace("★", ""))
                    item.setData(Qt.UserRole, num)
                elif isinstance(value, (int, float)):
                    item.setData(Qt.UserRole, value)
            except:
                pass
            
        return item

    def _create_condition_item(self, player):
        item = SortableTableWidgetItem()
        item.setTextAlignment(Qt.AlignCenter)
        
        # ★登録抹消中（再登録待機期間）のチェック
        if hasattr(player, 'days_until_promotion') and player.days_until_promotion > 0:
            item.setText(f"抹{player.days_until_promotion}") # "抹消"だと幅をとるので短縮
            item.setForeground(QColor("#7f8c8d")) # グレー
            item.setToolTip(f"出場選手登録抹消中: 再登録まであと{player.days_until_promotion}日")
            item.setData(Qt.UserRole, -99)
            return item
        
        if hasattr(player, 'is_injured') and player.is_injured:
            item.setText(f"残{player.injury_days}日")
            item.setForeground(QColor("#95a5a6"))
            item.setToolTip(f"怪我: 残り{player.injury_days}日")
            item.setData(Qt.UserRole, -1)
        else:
            cond = player.condition
            if cond >= 8:
                text, color, sort_val = "絶", "#e67e22", 5
            elif cond >= 6:
                text, color, sort_val = "好", "#f1c40f", 4
            elif cond >= 4:
                text, color, sort_val = "普", "#ecf0f1", 3
            elif cond >= 2:
                text, color, sort_val = "不", "#3498db", 2
            else:
                text, color, sort_val = "絶", "#9b59b6", 1
            
            item.setText(text)
            item.setForeground(QColor(color))
            font = QFont()
            font.setBold(True)
            item.setFont(font)
            item.setData(Qt.UserRole, sort_val)
            
        return item

    def _format_aptitude_delegate(self, p):
        main_pos = self._short_pos_name(p.position.value)
        subs = []
        if hasattr(p.stats, 'defense_ranges'):
            sorted_ranges = sorted(p.stats.defense_ranges.items(), key=lambda x: x[1], reverse=True)
            for pos_name, val in sorted_ranges:
                if pos_name != p.position.value and val > 10: 
                    subs.append(self._short_pos_name(pos_name))
        sub_str = " ".join(subs)
        return f"{main_pos}|{sub_str}"

    def _short_pos_name(self, long_name):
        mapping = {"投手":"投","捕手":"捕","一塁手":"一","二塁手":"二","三塁手":"三",
                   "遊撃手":"遊","左翼手":"左","中堅手":"中","右翼手":"右"}
        return mapping.get(long_name, long_name[0])

    # === Table Fillers using edit_state ===

    def _refresh_lineup_table(self):
        team = self.current_team
        table = self.lineup_table
        table.setRowCount(9)
        pos_order = {"捕": 2, "一": 3, "二": 4, "三": 5, "遊": 6, "左": 7, "中": 8, "右": 9, "DH": 10}
        
        current_lineup = self.edit_state['current_lineup']
        lineup_positions = self.edit_state['lineup_positions']
            
        for i in range(9):
            p_idx = -1
            if i < len(current_lineup):
                p_idx = current_lineup[i]
            
            pos_label = lineup_positions[i]
            
            table.setItem(i, 0, self._create_item(f"{i+1}"))
            
            pos_item = self._create_item(pos_label, pos_badge=pos_label)
            pos_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
            table.setItem(i, 1, pos_item)
            
            if p_idx != -1 and p_idx < len(team.players):
                p = team.players[p_idx]
                is_injured = hasattr(p, 'is_injured') and p.is_injured
                row_color = QColor("#95a5a6") if is_injured else None

                table.setItem(i, 2, self._create_condition_item(p))
                table.setItem(i, 3, self._create_item(p.name, Qt.AlignLeft, text_color=row_color))
                
                s = p.stats
                table.setItem(i, 4, self._create_item(s.contact, rank_color=True))
                table.setItem(i, 5, self._create_item(s.power, rank_color=True))
                table.setItem(i, 6, self._create_item(s.speed, rank_color=True))
                table.setItem(i, 7, self._create_item(s.arm, rank_color=True))
                table.setItem(i, 8, self._create_item(s.fielding, rank_color=True))
                
                apt_data = self._format_aptitude_delegate(p)
                p_pos_char = self._short_pos_name(p.position.value)
                sort_val = pos_order.get(p_pos_char, 99)
                table.setItem(i, 9, self._create_item(apt_data, sort_val=sort_val, text_color=row_color))
                table.setItem(i, 10, self._create_item(f"★{p.overall_rating}", is_star=True))
                
                for c in range(table.columnCount()):
                    if table.item(i, c): table.item(i, c).setData(ROLE_PLAYER_IDX, p_idx)
            else:
                self._clear_row(table, i, 2)

    def _refresh_bench_table(self):
        team = self.current_team
        table = self.bench_table
        bench_batters = self.edit_state['bench_batters']
        table.setRowCount(len(bench_batters) + 2)
        pos_order = {"捕": 2, "一": 3, "二": 4, "三": 5, "遊": 6, "左": 7, "中": 8, "右": 9, "DH": 10}
        
        for i, p_idx in enumerate(bench_batters):
            if p_idx != -1 and p_idx < len(team.players):
                p = team.players[p_idx]
                main_pos = self._short_pos_name(p.position.value)
                is_injured = hasattr(p, 'is_injured') and p.is_injured
                row_color = QColor("#95a5a6") if is_injured else None

                table.setItem(i, 0, self._create_item(main_pos, text_color=row_color))
                table.setItem(i, 1, self._create_condition_item(p))
                table.setItem(i, 2, self._create_item(p.name, Qt.AlignLeft, text_color=row_color))
                
                s = p.stats
                table.setItem(i, 3, self._create_item(s.contact, rank_color=True))
                table.setItem(i, 4, self._create_item(s.power, rank_color=True))
                table.setItem(i, 5, self._create_item(s.speed, rank_color=True))
                table.setItem(i, 6, self._create_item(s.arm, rank_color=True))
                table.setItem(i, 7, self._create_item(s.fielding, rank_color=True))
                
                apt_data = self._format_aptitude_delegate(p)
                p_pos_char = main_pos
                sort_val = pos_order.get(p_pos_char, 99)
                table.setItem(i, 8, self._create_item(apt_data, sort_val=sort_val, text_color=row_color))
                table.setItem(i, 9, self._create_item(f"★{p.overall_rating}", is_star=True))
                
                for c in range(table.columnCount()):
                    if table.item(i, c): table.item(i, c).setData(ROLE_PLAYER_IDX, p_idx)
            else:
                self._clear_row(table, i, 0)
        
        for i in range(len(bench_batters), table.rowCount()):
             self._clear_row(table, i, 0)

    def _refresh_batter_farm_list(self):
        team = self.current_team
        table = self.farm_batter_table
        
        # edit_state から登録済み選手を除外
        active_ids = set(self.edit_state['current_lineup'] + self.edit_state['bench_batters'])
        
        candidates = []
        pos_filter = self.batter_pos_filter.currentText()
        
        for i, p in enumerate(team.players):
            if p.position.value != "投手" and i not in active_ids:
                if p.is_developmental: continue
                if pos_filter != "全ポジション" and p.position.value != pos_filter:
                    continue
                candidates.append((i, p))
        
        pos_order = {"捕": 2, "一": 3, "二": 4, "三": 5, "遊": 6, "左": 7, "中": 8, "右": 9, "DH": 10}

        table.setRowCount(len(candidates))
        for i, (p_idx, p) in enumerate(candidates):
            is_injured = hasattr(p, 'is_injured') and p.is_injured
            row_color = QColor("#95a5a6") if is_injured else None
            
            # 再登録待機中の選手はグレーアウト
            if hasattr(p, 'days_until_promotion') and p.days_until_promotion > 0:
                row_color = QColor("#7f8c8d")

            table.setItem(i, 0, self._create_condition_item(p))
            table.setItem(i, 1, self._create_item(p.name, Qt.AlignLeft, text_color=row_color))
            table.setItem(i, 2, self._create_item(p.age, text_color=row_color)) 
            
            s = p.stats
            table.setItem(i, 3, self._create_item(s.contact, rank_color=True))
            table.setItem(i, 4, self._create_item(s.power, rank_color=True))
            table.setItem(i, 5, self._create_item(s.speed, rank_color=True))
            table.setItem(i, 6, self._create_item(s.arm, rank_color=True))
            table.setItem(i, 7, self._create_item(s.fielding, rank_color=True))
            
            apt_data = self._format_aptitude_delegate(p)
            p_pos_char = self._short_pos_name(p.position.value)
            sort_val = pos_order.get(p_pos_char, 99)
            
            apt_item = self._create_item(apt_data, sort_val=sort_val, text_color=row_color) 
            table.setItem(i, 8, apt_item)
            table.setItem(i, 9, self._create_item(f"★{p.overall_rating}", is_star=True))
            
            for c in range(table.columnCount()):
                if table.item(i, c): table.item(i, c).setData(ROLE_PLAYER_IDX, p_idx)

        header = table.horizontalHeader()
        table.sortItems(header.sortIndicatorSection(), header.sortIndicatorOrder())

    def _refresh_rotation_table(self):
        table = self.rotation_table
        table.setRowCount(8)
        rotation = self.edit_state['rotation']
        for i in range(8):
            p_idx = -1
            if i < len(rotation):
                p_idx = rotation[i]
            self._fill_pitcher_row_role(table, i, "先発", p_idx)

    def _refresh_bullpen_table(self):
        table = self.bullpen_table
        table.setRowCount(10)
        setup = self.edit_state['setup_pitchers']
        closers = self.edit_state['closers']
        
        for i in range(8):
            p_idx = -1
            if i < len(setup):
                p_idx = setup[i]
            self._fill_pitcher_row_role(table, i, "中継", p_idx)
            
        for i in range(2):
            p_idx = -1
            if i < len(closers):
                p_idx = closers[i]
            self._fill_pitcher_row_role(table, 8 + i, "抑え", p_idx)

    def _fill_pitcher_row_role(self, table, row, role_lbl, p_idx):
        table.setItem(row, 0, self._create_item(role_lbl, pos_badge=role_lbl[0]))
        if p_idx != -1 and p_idx < len(self.current_team.players):
            p = self.current_team.players[p_idx]
            self._fill_pitcher_data(table, row, p, p_idx, start_col=1)
        else:
            self._clear_row(table, row, 1)

    def _refresh_pitcher_farm_list(self):
        team = self.current_team
        table = self.farm_pitcher_table
        
        active_ids = set([x for x in self.edit_state['rotation'] if x >= 0])
        active_ids.update([x for x in self.edit_state['setup_pitchers'] if x >= 0])
        active_ids.update([x for x in self.edit_state['closers'] if x >= 0])
        
        candidates = []
        type_filter = self.pitcher_type_filter.currentText()
        
        for i, p in enumerate(team.players):
            if p.position.value == "投手" and i not in active_ids:
                if p.is_developmental: continue
                if type_filter != "全タイプ" and p.pitch_type.value != type_filter:
                    continue
                candidates.append((i, p))
                
        table.setRowCount(len(candidates))
        for i, (p_idx, p) in enumerate(candidates):
            is_injured = hasattr(p, 'is_injured') and p.is_injured
            row_color = QColor("#95a5a6") if is_injured else None
            
            # 再登録待機中の選手はグレーアウト
            if hasattr(p, 'days_until_promotion') and p.days_until_promotion > 0:
                row_color = QColor("#7f8c8d")

            role = p.pitch_type.value[:2]
            table.setItem(i, 0, self._create_item(role, text_color=row_color))
            table.setItem(i, 1, self._create_condition_item(p))
            table.setItem(i, 2, self._create_item(p.name, Qt.AlignLeft, text_color=row_color))
            table.setItem(i, 3, self._create_item(p.age, text_color=row_color))
            
            kmh = p.stats.speed_to_kmh()
            table.setItem(i, 4, self._create_item(f"{kmh}km", sort_val=kmh, text_color=row_color))
            
            table.setItem(i, 5, self._create_item(p.stats.control, rank_color=True))
            table.setItem(i, 6, self._create_item(p.stats.stamina, rank_color=True))
            table.setItem(i, 7, self._create_item(p.stats.stuff, rank_color=True))
            
            st = "◎" if p.pitch_type.value == "先発" else "△"
            rl = "◎" if p.pitch_type.value == "中継ぎ" else "△"
            cl = "◎" if p.pitch_type.value == "抑え" else "△"
            table.setItem(i, 8, self._create_item(st, sort_val=2 if st=="◎" else 1, text_color=row_color))
            table.setItem(i, 9, self._create_item(rl, sort_val=2 if rl=="◎" else 1, text_color=row_color))
            table.setItem(i, 10, self._create_item(cl, sort_val=2 if cl=="◎" else 1, text_color=row_color))
            table.setItem(i, 11, self._create_item(f"★{p.overall_rating}", is_star=True))

            for c in range(table.columnCount()):
                if table.item(i, c): table.item(i, c).setData(ROLE_PLAYER_IDX, p_idx)
                
        header = table.horizontalHeader()
        table.sortItems(header.sortIndicatorSection(), header.sortIndicatorOrder())

    def _fill_pitcher_data(self, table, row, p, p_idx, start_col):
        is_injured = hasattr(p, 'is_injured') and p.is_injured
        row_color = QColor("#95a5a6") if is_injured else None

        table.setItem(row, start_col, self._create_condition_item(p))
        table.setItem(row, start_col+1, self._create_item(p.name, Qt.AlignLeft, text_color=row_color))
        kmh = p.stats.speed_to_kmh()
        table.setItem(row, start_col+2, self._create_item(f"{kmh}km", text_color=row_color))
        
        table.setItem(row, start_col+3, self._create_item(p.stats.control, rank_color=True))
        table.setItem(row, start_col+4, self._create_item(p.stats.stamina, rank_color=True))
        table.setItem(row, start_col+5, self._create_item(p.stats.stuff, rank_color=True))
        
        st = "◎" if p.pitch_type.value == "先発" else "△"
        rl = "◎" if p.pitch_type.value == "中継ぎ" else "△"
        cl = "◎" if p.pitch_type.value == "抑え" else "△"
        table.setItem(row, start_col+6, self._create_item(st, text_color=row_color))
        table.setItem(row, start_col+7, self._create_item(rl, text_color=row_color))
        table.setItem(row, start_col+8, self._create_item(cl, text_color=row_color))
        table.setItem(row, start_col+9, self._create_item(f"★{p.overall_rating}", is_star=True))

        for c in range(table.columnCount()):
            if table.item(row, c): table.item(row, c).setData(ROLE_PLAYER_IDX, p_idx)

    def _clear_row(self, table, row, start_col):
        for c in range(start_col, table.columnCount()):
            table.setItem(row, c, QTableWidgetItem(""))
        if start_col < table.columnCount():
            table.setItem(row, start_col, QTableWidgetItem("---"))

    def _on_table_changed(self, table):
        if not hasattr(table, 'dropped_player_idx'): return
        p_idx = table.dropped_player_idx
        row = table.dropped_target_row
        
        # ★ペナルティチェック: 再登録待機中の選手を一軍枠（スタメン・ベンチ・投手陣）へ移動しようとした場合
        player = self.current_team.players[p_idx]
        is_target_active = False
        if table in [self.lineup_table, self.bench_table, self.rotation_table, self.bullpen_table]:
            is_target_active = True
        
        if is_target_active and hasattr(player, 'days_until_promotion') and player.days_until_promotion > 0:
            QMessageBox.warning(self, "登録不可", f"この選手は登録抹消中のため、一軍登録できません。\n再登録可能まであと {player.days_until_promotion} 日です。")
            del table.dropped_player_idx
            self._refresh_all() # 変更を元に戻す
            return
        
        # ★怪我人チェック: 怪我人をスタメンに入れようとした場合のみ禁止（ベンチはOK）
        if table == self.lineup_table and player.is_injured:
            QMessageBox.warning(self, "出場不可", f"この選手は怪我のためスタメン起用できません。")
            del table.dropped_player_idx
            self._refresh_all()
            return

        # 変更があればフラグを立てる
        self._mark_as_changed()
        
        # edit_state を操作
        state = self.edit_state
        
        source_list = None
        source_idx = -1
        
        if p_idx in state['current_lineup']:
            source_list = state['current_lineup']
            source_idx = state['current_lineup'].index(p_idx)
        elif p_idx in state['bench_batters']:
            source_list = state['bench_batters']
            source_idx = state['bench_batters'].index(p_idx)
        elif p_idx in state['rotation']:
            source_list = state['rotation']
            source_idx = state['rotation'].index(p_idx)
        elif p_idx in state['setup_pitchers']:
            source_list = state['setup_pitchers']
            source_idx = state['setup_pitchers'].index(p_idx)
        elif p_idx in state['closers']:
            source_list = state['closers']
            source_idx = state['closers'].index(p_idx)
            
        target_list = None
        target_p_idx = -1
        
        if table == self.lineup_table:
            target_list = state['current_lineup']
            while len(target_list) <= row: target_list.append(-1)
            target_p_idx = target_list[row]
            
        elif table == self.bench_table:
            target_list = state['bench_batters']
            while len(target_list) <= row: target_list.append(-1)
            target_p_idx = target_list[row]
            
        elif table == self.rotation_table:
            target_list = state['rotation']
            while len(target_list) <= row: target_list.append(-1)
            target_p_idx = target_list[row]
            
        elif table == self.bullpen_table:
            if row >= 8: # Closer
                target_list = state['closers']
                c_row = row - 8
                while len(target_list) <= c_row: target_list.append(-1)
                target_p_idx = target_list[c_row]
                row = c_row 
            else:
                target_list = state['setup_pitchers']
                while len(target_list) <= row: target_list.append(-1)
                target_p_idx = target_list[row]
                
        if target_list is not None:
             target_list[row] = p_idx
        
        if source_list is not None:
             if target_list is not None:
                 # Swap: put target's old player into source's old slot
                 if source_idx < len(source_list):
                      source_list[source_idx] = target_p_idx
             else:
                 # Remove: target is farm/None, so just clear source slot
                 if source_idx < len(source_list):
                      source_list[source_idx] = -1

        self._refresh_all()
        del table.dropped_player_idx

    def _on_pos_swapped(self, r1, r2):
        pos_list = self.edit_state['lineup_positions']
        if r1 < 9 and r2 < 9:
            pos_list[r1], pos_list[r2] = pos_list[r2], pos_list[r1]
            self._mark_as_changed()
            self._refresh_lineup_table()

    def _auto_fill(self):
        if not self.current_team: return
        t = self.current_team
        
        # 自動編成も edit_state 上で行う
        self._mark_as_changed()
        
        state = self.edit_state
        state['current_lineup'] = [-1] * 9
        state['lineup_positions'] = [""] * 9
        state['bench_batters'] = []
        state['rotation'] = [-1] * 8
        state['setup_pitchers'] = [-1] * 8 
        state['closers'] = [-1] * 2

        TOTAL_LIMIT = 31
        if hasattr(t, 'ACTIVE_ROSTER_LIMIT'):
            TOTAL_LIMIT = t.ACTIVE_ROSTER_LIMIT
            
        PITCHER_TARGET = int(TOTAL_LIMIT * (13/31))
        BATTER_TARGET = TOTAL_LIMIT - PITCHER_TARGET

        def get_condition_mult(p):
            return 1.0 + (p.condition - 5) * 0.05

        def get_batting_score(p):
            s = p.stats
            val = (s.contact * 1.0 + s.power * 1.2 + s.speed * 0.5 + s.eye * 0.5)
            return val * get_condition_mult(p)

        def get_defense_score(p, pos_name_long):
            apt = p.stats.defense_ranges.get(pos_name_long, 0)
            if apt < 20: return 0
            s = p.stats
            def_val = (apt * 1.5 + s.error * 0.5 + s.arm * 0.5)
            return def_val

        def get_pitcher_score(p, role):
            s = p.stats
            base = s.overall_pitching() * 99
            apt_mult = 1.0
            if role == 'starter':
                apt_mult = p.starter_aptitude / 50.0
                base += s.stamina * 0.5
            elif role == 'closer':
                apt_mult = p.closer_aptitude / 50.0
                base += (s.velocity - 130) * 2 + s.stuff * 0.5
            else:
                apt_mult = p.middle_aptitude / 50.0
            return base * apt_mult * get_condition_mult(p)

        # ★自動編成でも再登録待機中の選手は除外する
        pitchers = [i for i, p in enumerate(t.players) 
                   if p.position.value == "投手" and not p.is_developmental 
                   and (not hasattr(p, 'days_until_promotion') or p.days_until_promotion == 0)]
        
        pitchers.sort(key=lambda i: get_pitcher_score(t.players[i], 'starter'), reverse=True)
        
        rotation_count = 6
        rotation_candidates = pitchers[:rotation_count]
        remaining_pitchers = pitchers[rotation_count:]
        
        for i in range(min(rotation_count, len(rotation_candidates))):
            state['rotation'][i] = rotation_candidates[i]
            
        if remaining_pitchers:
            remaining_pitchers.sort(key=lambda i: get_pitcher_score(t.players[i], 'closer'), reverse=True)
            state['closers'][0] = remaining_pitchers.pop(0)
            
        remaining_pitchers.sort(key=lambda i: get_pitcher_score(t.players[i], 'relief'), reverse=True)
        
        used_p = len([x for x in state['rotation'] if x != -1]) + len([x for x in state['closers'] if x != -1])
        setup_limit = max(0, PITCHER_TARGET - used_p)
        
        for i in range(min(8, setup_limit, len(remaining_pitchers))):
            state['setup_pitchers'][i] = remaining_pitchers[i]
            
        batters = [i for i, p in enumerate(t.players) 
                  if p.position.value != "投手" and not p.is_developmental
                  and (not hasattr(p, 'days_until_promotion') or p.days_until_promotion == 0)]
        
        pos_map = {
            "捕": "捕手", "遊": "遊撃手", "二": "二塁手", "中": "中堅手", 
            "三": "三塁手", "右": "右翼手", "左": "左翼手", "一": "一塁手"
        }
        def_priority = ["捕", "遊", "二", "中", "三", "右", "左", "一"]
        
        selected_starters = {}
        used_indices = set()
        
        for short_pos in def_priority:
            long_pos = pos_map[short_pos]
            best_idx = -1
            best_score = -1
            
            for idx in batters:
                if idx in used_indices: continue
                p = t.players[idx]
                
                # ★スタメン選出では怪我人を除外
                if p.is_injured: continue

                apt = p.stats.defense_ranges.get(long_pos, 0)
                if apt < 20: continue 
                
                def_weight = 1.0
                if short_pos in ["捕", "遊", "二"]: def_weight = 1.5
                score = (get_batting_score(p) + get_defense_score(p, long_pos) * def_weight)
                
                if score > best_score:
                    best_score = score
                    best_idx = idx
            
            if best_idx != -1:
                selected_starters[short_pos] = best_idx
                used_indices.add(best_idx)
        
        # DH選出（怪我人除外）
        dh_candidates = [i for i in batters if i not in used_indices and not t.players[i].is_injured]
        dh_candidates.sort(key=lambda i: get_batting_score(t.players[i]), reverse=True)
        if dh_candidates:
            selected_starters["DH"] = dh_candidates[0]
            used_indices.add(dh_candidates[0])
            
        missing_positions = [p for p in def_priority + ["DH"] if p not in selected_starters]
        for p in missing_positions:
            remaining = [i for i in batters if i not in used_indices and not t.players[i].is_injured]
            if remaining:
                remaining.sort(key=lambda i: get_batting_score(t.players[i]), reverse=True)
                selected_starters[p] = remaining[0]
                used_indices.add(remaining[0])

        lineup_candidates = []
        for pos, idx in selected_starters.items():
            if idx == -1: continue
            lineup_candidates.append({"pos": pos, "idx": idx, "p": t.players[idx]})
            
        final_order = [None] * 9
        
        if len(lineup_candidates) >= 1:
            def pick_best(candidates, sort_key):
                if not candidates: return None
                best = max(candidates, key=sort_key)
                candidates.remove(best)
                return best

            final_order[3] = pick_best(lineup_candidates, lambda x: x['p'].stats.power)
            final_order[2] = pick_best(lineup_candidates, lambda x: get_batting_score(x['p']))
            final_order[0] = pick_best(lineup_candidates, lambda x: x['p'].stats.speed)
            final_order[4] = pick_best(lineup_candidates, lambda x: x['p'].stats.power)
            final_order[1] = pick_best(lineup_candidates, lambda x: x['p'].stats.contact + x['p'].stats.bunt_sac)
            
            lineup_candidates.sort(key=lambda x: get_batting_score(x['p']), reverse=True)
            for i in range(len(lineup_candidates)):
                found_slot = False
                for slot in range(5, 9):
                    if final_order[slot] is None:
                        final_order[slot] = lineup_candidates[i]
                        found_slot = True
                        break
                if not found_slot:
                     for slot in range(5):
                        if final_order[slot] is None:
                            final_order[slot] = lineup_candidates[i]
                            break

            for i in range(9):
                if final_order[i]:
                    state['current_lineup'][i] = final_order[i]['idx']
                    state['lineup_positions'][i] = final_order[i]['pos']

        # ★ベンチ選出: 怪我人も含める（優先度は下げる）
        remaining_bench = [i for i in batters if i not in used_indices]
        # 怪我をしていない選手を優先し、その中で能力順
        remaining_bench.sort(key=lambda i: (not t.players[i].is_injured, t.players[i].overall_rating), reverse=True)
        
        bench_limit = max(0, BATTER_TARGET - 9)
        state['bench_batters'] = remaining_bench[:bench_limit]
        
        self._refresh_all()
    
    def _on_player_double_clicked(self, item):
        p_idx = item.data(ROLE_PLAYER_IDX)
        if p_idx is not None and isinstance(p_idx, int) and p_idx >= 0:
            if p_idx < len(self.current_team.players):
                player = self.current_team.players[p_idx]
                self.player_detail_requested.emit(player)