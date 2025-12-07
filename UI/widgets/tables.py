# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Table Widgets
OOTP-Style Data Tables and Lists
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLabel, QLineEdit, QComboBox,
    QFrame, QPushButton, QMenu, QStyledItemDelegate
)
from PySide6.QtCore import Qt, Signal, QSortFilterProxyModel
from PySide6.QtGui import QColor, QBrush, QFont, QPainter

import sys
sys.path.insert(0, '..')
from UI.theme import get_theme, Theme


def apply_premium_table_style(table: QTableWidget, theme=None) -> None:
    """Apply consistent premium OOTP-style to any QTableWidget"""
    if theme is None:
        theme = get_theme()

    table.setStyleSheet(f"""
        QTableWidget {{
            background-color: transparent;
            border: none;
            gridline-color: transparent;
        }}
        QTableWidget::item {{
            padding: 6px;
            color: {theme.text_primary};
            border-bottom: 1px solid {theme.border_muted};
        }}
        QTableWidget::item:selected {{
            background-color: {theme.primary};
            color: white;
        }}
        QTableWidget::item:hover {{
            background-color: {theme.bg_hover};
        }}
        QHeaderView::section {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {theme.bg_card_elevated},
                stop:1 {theme.bg_card});
            color: {theme.text_secondary};
            font-weight: 600;
            font-size: 11px;
            padding: 8px 6px;
            border: none;
            border-bottom: 2px solid {theme.primary};
        }}
    """)

    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(36)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setSelectionMode(QTableWidget.SingleSelection)
    table.setShowGrid(False)


class RatingDelegate(QStyledItemDelegate):
    """Custom delegate for rating cells with color backgrounds"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()

    def paint(self, painter: QPainter, option, index):
        value = index.data(Qt.UserRole)
        if value is not None and isinstance(value, int):
            # Get rating color
            color = Theme.get_rating_color(value)
            rank = Theme.get_rating_rank(value)

            # Draw background
            painter.save()
            painter.fillRect(option.rect.adjusted(2, 2, -2, -2),
                           QColor(color))

            # Draw text
            painter.setPen(QColor("white"))
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(option.rect, Qt.AlignCenter, rank)
            painter.restore()
        else:
            super().paint(painter, option, index)


class PlayerTable(QWidget):
    """OOTP-Style Player Table with sorting, filtering, and stats"""

    player_selected = Signal(object)  # Emits player object
    player_double_clicked = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.players = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Table
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Set delegate for rating columns
        self.rating_delegate = RatingDelegate(self)

        # Connect signals
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed) if self.table.selectionModel() else None
        self.table.cellDoubleClicked.connect(self._on_double_click)

        layout.addWidget(self.table)

        # Status bar
        self.status_label = QLabel("0 選手")
        self.status_label.setStyleSheet(f"""
            font-size: 12px;
            color: {self.theme.text_muted};
            padding: 4px;
        """)
        layout.addWidget(self.status_label)

    def _create_toolbar(self) -> QWidget:
        toolbar = QWidget()
        toolbar.setStyleSheet(f"background-color: transparent;")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # 入力コントロール用の共通スタイルを定義
        input_style = f"""
            QLineEdit, QComboBox {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 2px solid {self.theme.text_secondary};
                border-bottom: 2px solid {self.theme.text_secondary};
                width: 8px;
                height: 8px;
                margin-right: 8px;
                transform: rotate(-45deg);
                margin-top: -2px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.theme.bg_card};
                color: {self.theme.text_primary};
                selection-background-color: {self.theme.primary};
                selection-color: {self.theme.text_highlight};
                border: 1px solid {self.theme.border};
                outline: none;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {self.theme.primary};
            }}
        """

        # Search
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("選手検索...")
        self.search_input.setMinimumWidth(200)
        self.search_input.setStyleSheet(input_style)  # スタイルを適用
        self.search_input.textChanged.connect(self._filter_players)
        layout.addWidget(self.search_input)

        # Position filter
        self.position_filter = QComboBox()
        self.position_filter.addItems([
            "全ポジション", "投手", "捕手", "一塁手", "二塁手",
            "三塁手", "遊撃手", "外野手"
        ])
        self.position_filter.setStyleSheet(input_style)  # スタイルを適用
        self.position_filter.currentIndexChanged.connect(self._filter_players)
        layout.addWidget(self.position_filter)

        # Type filter (for pitchers)
        self.type_filter = QComboBox()
        self.type_filter.addItems(["全タイプ", "先発", "中継ぎ", "抑え"])
        self.type_filter.setStyleSheet(input_style)  # スタイルを適用
        self.type_filter.currentIndexChanged.connect(self._filter_players)
        layout.addWidget(self.type_filter)

        layout.addStretch()

        # View mode buttons
        self.view_batter_btn = QPushButton("野手表示")
        self.view_batter_btn.setCheckable(True)
        self.view_batter_btn.setChecked(True)
        self.view_batter_btn.clicked.connect(lambda: self._set_view_mode("batter"))

        self.view_pitcher_btn = QPushButton("投手表示")
        self.view_pitcher_btn.setCheckable(True)
        self.view_pitcher_btn.clicked.connect(lambda: self._set_view_mode("pitcher"))

        layout.addWidget(self.view_batter_btn)
        layout.addWidget(self.view_pitcher_btn)

        return toolbar

    def _set_view_mode(self, mode: str):
        """Switch between batter and pitcher stat views"""
        self.view_batter_btn.setChecked(mode == "batter")
        self.view_pitcher_btn.setChecked(mode == "pitcher")
        self._refresh_columns(mode)

    def _refresh_columns(self, mode: str = "batter"):
        """Set up table columns based on view mode"""
        self.table.clear()

        if mode == "batter":
            headers = [
                "#", "名前", "Pos", "年齢", "ミート", "パワー", "走力",
                "肩力", "守備", "捕球", "打率", "HR", "打点", "総合"
            ]
            widths = [40, 120, 60, 50, 55, 55, 55, 55, 55, 55, 60, 50, 50, 60]
        else:
            headers = [
                "#", "名前", "役割", "年齢", "球速", "制球", "スタ",
                "変化", "勝", "敗", "S", "ERA", "K", "総合"
            ]
            widths = [40, 120, 60, 50, 55, 55, 55, 55, 40, 40, 40, 60, 50, 60]

        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        # Set column widths
        header = self.table.horizontalHeader()
        for i, width in enumerate(widths):
            header.resizeSection(i, width)
        header.setStretchLastSection(True)

        # Set rating delegates for stat columns
        rating_cols = [4, 5, 6, 7, 8, 9] if mode == "batter" else [4, 5, 6, 7]
        for col in rating_cols:
            self.table.setItemDelegateForColumn(col, self.rating_delegate)

        # Refresh data
        self._populate_table(mode)

    def set_players(self, players: list, mode: str = "batter"):
        """Set the player list and refresh the table"""
        self.players = players
        self._refresh_columns(mode)
        self._update_status()

    def _populate_table(self, mode: str = "batter"):
        """Fill table with player data"""
        # Filter players first
        filtered = self._get_filtered_players()

        self.table.setRowCount(len(filtered))

        for row, player in enumerate(filtered):
            self._set_player_row(row, player, mode)

        self._update_status()

    def _set_player_row(self, row: int, player, mode: str):
        """Set a single row with player data"""
        stats = player.stats
        record = player.record

        if mode == "batter":
            data = [
                str(player.uniform_number),
                player.name,
                player.position.value[:2],
                str(player.age),
                stats.contact,
                stats.power,
                stats.run,
                stats.arm,
                stats.fielding,
                stats.catching,
                f".{int(record.batting_average * 1000):03d}" if record.at_bats > 0 else "---",
                str(record.home_runs),
                str(record.rbis),
                str(player.overall_rating)
            ]
            rating_cols = [4, 5, 6, 7, 8, 9]
        else:
            pitch_role = player.pitch_type.value[:2] if player.pitch_type else "投"
            era = record.era if record.innings_pitched > 0 else 0
            data = [
                str(player.uniform_number),
                player.name,
                pitch_role,
                str(player.age),
                stats.speed,
                stats.control,
                stats.stamina,
                stats.breaking,
                str(record.wins),
                str(record.losses),
                str(record.saves),
                f"{era:.2f}" if era > 0 else "-.--",
                str(record.strikeouts_pitched),
                str(player.overall_rating)
            ]
            rating_cols = [4, 5, 6, 7]

        for col, value in enumerate(data):
            item = QTableWidgetItem()

            if col in rating_cols:
                # Rating column - store actual value for delegate
                item.setData(Qt.UserRole, value)
                item.setData(Qt.DisplayRole, "")
                item.setTextAlignment(Qt.AlignCenter)
            else:
                item.setText(str(value))
                item.setTextAlignment(Qt.AlignCenter if col != 1 else Qt.AlignLeft | Qt.AlignVCenter)

            # Store player reference in first column
            if col == 0:
                item.setData(Qt.UserRole, player)

            self.table.setItem(row, col, item)

    def _get_filtered_players(self) -> list:
        """Apply filters to player list"""
        filtered = self.players

        # Search filter
        search = self.search_input.text().strip()
        if search:
            filtered = [p for p in filtered if search.lower() in p.name.lower()]

        # Position filter
        pos_idx = self.position_filter.currentIndex()
        if pos_idx > 0:
            positions = ["投手", "捕手", "一塁手", "二塁手", "三塁手", "遊撃手", "外野手"]
            target_pos = positions[pos_idx - 1]
            filtered = [p for p in filtered if p.position.value == target_pos]

        # Type filter (pitchers)
        type_idx = self.type_filter.currentIndex()
        if type_idx > 0 and self.view_pitcher_btn.isChecked():
            types = ["先発", "中継ぎ", "抑え"]
            target_type = types[type_idx - 1]
            filtered = [p for p in filtered if p.pitch_type and p.pitch_type.value == target_type]

        return filtered

    def _filter_players(self):
        """Re-filter and refresh table"""
        mode = "pitcher" if self.view_pitcher_btn.isChecked() else "batter"
        self._populate_table(mode)

    def _update_status(self):
        """Update status bar text"""
        visible = self.table.rowCount()
        total = len(self.players)
        self.status_label.setText(f"{visible} / {total} 選手")

    def _on_selection_changed(self, selected, deselected):
        """Handle row selection"""
        indexes = selected.indexes()
        if indexes:
            row = indexes[0].row()
            item = self.table.item(row, 0)
            if item:
                player = item.data(Qt.UserRole)
                if player:
                    self.player_selected.emit(player)

    def _on_double_click(self, row: int, col: int):
        """Handle double click"""
        item = self.table.item(row, 0)
        if item:
            player = item.data(Qt.UserRole)
            if player:
                self.player_double_clicked.emit(player)

    def get_selected_player(self):
        """Get currently selected player"""
        selection = self.table.selectionModel().selectedRows()
        if selection:
            row = selection[0].row()
            item = self.table.item(row, 0)
            if item:
                return item.data(Qt.UserRole)
        return None


class RosterTable(QWidget):
    """Compact roster table for lineup management"""

    player_selected = Signal(object)
    lineup_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.players = []
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setDragDropMode(QAbstractItemView.InternalMove)
        self.table.setDragEnabled(True)
        self.table.setAcceptDrops(True)

        # Headers
        headers = ["打順", "#", "名前", "Pos", "総合"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        header = self.table.horizontalHeader()
        header.resizeSection(0, 50)
        header.resizeSection(1, 40)
        header.resizeSection(2, 120)
        header.resizeSection(3, 50)
        header.setStretchLastSection(True)

        layout.addWidget(self.table)

    def set_lineup(self, players: list):
        """Set lineup (9 players in order)"""
        self.players = players
        self.table.setRowCount(len(players))

        for row, player in enumerate(players):
            # Batting order
            order_item = QTableWidgetItem(str(row + 1))
            order_item.setTextAlignment(Qt.AlignCenter)
            order_item.setData(Qt.UserRole, player)
            self.table.setItem(row, 0, order_item)

            # Number
            num_item = QTableWidgetItem(str(player.uniform_number))
            num_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, num_item)

            # Name
            name_item = QTableWidgetItem(player.name)
            self.table.setItem(row, 2, name_item)

            # Position
            pos_item = QTableWidgetItem(player.position.value[:2])
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, pos_item)

            # Overall
            overall_item = QTableWidgetItem(str(player.overall_rating))
            overall_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 4, overall_item)

    def get_lineup(self) -> list:
        """Get current lineup order"""
        lineup = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                player = item.data(Qt.UserRole)
                if player:
                    lineup.append(player)
        return lineup


class ScheduleTable(QWidget):
    """Game schedule table"""

    game_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(True)

        headers = ["#", "日付", "ホーム", "スコア", "アウェイ", "状態"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        header = self.table.horizontalHeader()
        header.resizeSection(0, 50)
        header.resizeSection(1, 100)
        header.resizeSection(2, 120)
        header.resizeSection(3, 80)
        header.resizeSection(4, 120)
        header.setStretchLastSection(True)

        layout.addWidget(self.table)

    def set_schedule(self, games: list):
        """Set game schedule"""
        self.table.setRowCount(len(games))

        for row, game in enumerate(games):
            # Game number
            num_item = QTableWidgetItem(str(game.game_number))
            num_item.setTextAlignment(Qt.AlignCenter)
            num_item.setData(Qt.UserRole, game)
            self.table.setItem(row, 0, num_item)

            # Date
            date_item = QTableWidgetItem(game.date)
            date_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, date_item)

            # Home team
            home_item = QTableWidgetItem(game.home_team_name)
            self.table.setItem(row, 2, home_item)

            # Score
            if game.is_completed:
                score = f"{game.home_score} - {game.away_score}"
            else:
                score = "vs"
            score_item = QTableWidgetItem(score)
            score_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 3, score_item)

            # Away team
            away_item = QTableWidgetItem(game.away_team_name)
            self.table.setItem(row, 4, away_item)

            # Status
            status_item = QTableWidgetItem(game.status.value)
            status_item.setTextAlignment(Qt.AlignCenter)
            if game.is_completed:
                status_item.setForeground(QBrush(QColor(self.theme.success)))
            self.table.setItem(row, 5, status_item)


class StatsLeaderTable(QWidget):
    """Stats leader table (batting/pitching titles)"""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.title = title
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if self.title:
            title_label = QLabel(self.title)
            title_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: 600;
                color: {self.theme.text_primary};
                padding: 8px 0;
            """)
            layout.addWidget(title_label)

        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        layout.addWidget(self.table)

    def set_leaders(self, stat_name: str, leaders: list):
        """Set leader data: [(rank, player, team, value), ...]"""
        headers = ["順", "選手", "チーム", stat_name]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)

        header = self.table.horizontalHeader()
        header.resizeSection(0, 40)
        header.resizeSection(1, 100)
        header.resizeSection(2, 80)
        header.setStretchLastSection(True)

        self.table.setRowCount(len(leaders))

        for row, (rank, player, team, value) in enumerate(leaders):
            # Rank
            rank_item = QTableWidgetItem(str(rank))
            rank_item.setTextAlignment(Qt.AlignCenter)
            if rank <= 3:
                rank_item.setForeground(QBrush(QColor(self.theme.gold)))
            self.table.setItem(row, 0, rank_item)

            # Player name
            name_item = QTableWidgetItem(player.name if hasattr(player, 'name') else str(player))
            self.table.setItem(row, 1, name_item)

            # Team
            team_item = QTableWidgetItem(str(team))
            self.table.setItem(row, 2, team_item)

            # Value
            value_item = QTableWidgetItem(str(value))
            value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value_item.setFont(QFont("", -1, QFont.Bold))
            self.table.setItem(row, 3, value_item)
