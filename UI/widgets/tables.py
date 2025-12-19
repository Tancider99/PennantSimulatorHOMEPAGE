# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Table Widgets
Custom Data Tables and Lists
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLabel, QLineEdit, QComboBox,
    QFrame, QPushButton, QMenu, QStyledItemDelegate, QStyle
)
from PySide6.QtCore import Qt, Signal, QSortFilterProxyModel, QMimeData, QByteArray, QDataStream, QPoint, QIODevice, QSize
from PySide6.QtGui import QColor, QBrush, QFont, QPainter, QPen, QPixmap, QDrag, QPalette

import sys
sys.path.insert(0, '..')
from UI.theme import get_theme, Theme
# PlayerStatsの静的メソッドを利用するためにインポート
try:
    from models import PlayerStats
except ImportError:
    pass

# MIME Types for Drag & Drop
MIME_PLAYER_DATA = "application/x-pennant-player-data"
MIME_POS_SWAP = "application/x-pennant-pos-swap"
ROLE_PLAYER_IDX = Qt.UserRole + 1


def apply_premium_table_style(table: QTableWidget, theme=None) -> None:
    """Apply consistent premium custom style to any QTableWidget"""
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
            color: #222222;
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
            # 修正: 文字色を白から黒系(#222222)に変更
            painter.setPen(QColor("#222222"))
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(option.rect, Qt.AlignCenter, rank)
            painter.restore()
        else:
            super().paint(painter, option, index)


class StarDelegate(QStyledItemDelegate):
    """Delegate for Total Rating (Gold Text)"""
    def paint(self, painter, option, index):
        painter.save()
        
        # Initialize option to get default style
        self.initStyleOption(option, index)
        
        # Override palette logic for Text
        # Note: If we just draw text manually, we must handle background correct.
        # Call base style to draw background, but we want to change text color.
        
        # Easiest way: Modify option.palette for Text roles
        option.palette.setColor(QPalette.Text, QColor("#FFD700"))
        option.palette.setColor(QPalette.HighlightedText, QColor("#FFD700"))
        
        # Also force Bold font
        option.font.setBold(True)
        
        # Call base paint (which uses option)
        super().paint(painter, option, index)
        
        painter.restore()


class SortableTableWidgetItem(QTableWidgetItem):
    """
    数値でのソートを正しく行うためのカスタムアイテムクラス
    UserRoleに数値がある場合はそれを優先し、なければテキストを数値変換して比較する
    """
    def __lt__(self, other):
        # 1. UserRole (能力値などの隠しデータ) での比較
        v1 = self.data(Qt.UserRole)
        v2 = other.data(Qt.UserRole)
        
        # v1, v2 がともに数値として有効な場合
        if v1 is not None and v2 is not None:
             try:
                 f1 = float(v1)
                 f2 = float(v2)
                 return f1 < f2
             except (ValueError, TypeError):
                 pass # 数値変換できない場合は後続の処理へ

        # 2. テキストを数値変換して比較 (背番号、成績など)
        t1 = self.text().replace(',', '').replace('★ ', '').strip()
        t2 = other.text().replace(',', '').replace('★ ', '').strip()

        # プレースホルダーの処理: "---" や "-.--" は最小値（または最大値）として扱う
        # ここでは最小値として扱い、常に下に来るようにする（降順ソート時に下、昇順時に上に来る）
        # ただし、空データ同士の比較も考慮
        is_empty1 = (t1 in ["---", "-.--", "", "-"])
        is_empty2 = (t2 in ["---", "-.--", "", "-"])

        if is_empty1 and is_empty2:
            return False
        if is_empty1:
            return True # t1 is "smaller" (empty), so t1 < t2
        if is_empty2:
            return False # t2 is empty, so t1 > t2

        try:
            d1 = float(t1)
            d2 = float(t2)
            return d1 < d2
        except ValueError:
            pass
            
        # 3. フォールバック: 通常の文字列比較（大文字小文字区別なし推奨）
        return t1.lower() < t2.lower()


class PlayerTable(QWidget):
    """Player Table with sorting, filtering, and stats"""

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
        apply_premium_table_style(self.table, self.theme) # Apply style
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        
        # 手動ソート制御
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().setSectionsClickable(True)
        self.table.horizontalHeader().setSortIndicatorShown(True)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Set delegate for rating columns
        self.rating_delegate = RatingDelegate(self)
        self.star_delegate = StarDelegate(self)

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
        
        # 以前のデリゲート設定をクリア
        for i in range(self.table.columnCount()):
            self.table.setItemDelegateForColumn(i, None)

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
            
        # Set StarDelegate for Total column (Last column)
        self.table.setItemDelegateForColumn(len(headers)-1, self.star_delegate)

        # Refresh data
        self._populate_table(mode)

    def set_players(self, players: list, mode: str = "batter"):
        """Set the player list and refresh the table"""
        self.players = players
        self._refresh_columns(mode)
        self._update_status()

    def _on_header_clicked(self, logicalIndex):
        """
        ヘッダー列クリック時のカスタムソートハンドラ
        """
        if logicalIndex in [1, 2]:
            return

        # Initialize manual tracking if needed
        if not hasattr(self, "_sort_col"):
            self._sort_col = -1
            self._sort_order = Qt.DescendingOrder

        # Toggle if same column, else default to Descending
        if self._sort_col == logicalIndex:
            if self._sort_order == Qt.DescendingOrder:
                self._sort_order = Qt.AscendingOrder
            else:
                self._sort_order = Qt.DescendingOrder
        else:
            self._sort_col = logicalIndex
            self._sort_order = Qt.DescendingOrder

        header = self.table.horizontalHeader()
        self.table.sortItems(self._sort_col, self._sort_order)
        header.setSortIndicator(self._sort_col, self._sort_order)

    def _populate_table(self, mode: str = "batter"):
        """Fill table with player data"""
        # Filter players first
        filtered = self._get_filtered_players()

        self.table.setRowCount(len(filtered))

        for row, player in enumerate(filtered):
            self._set_player_row(row, player, mode)

        # データ入力後に現在のソート状態に従ってソートを実行
        # データ入力後に現在のソート状態に従ってソートを実行
        if hasattr(self, "_sort_col") and self._sort_col >= 0:
            self.table.sortItems(self._sort_col, self._sort_order)
        # else: No sort or default order applied by Qt logic? 
        # Actually header.sortIndicatorSection() returns 0 by default. 
        # If we want default sort (Total Ability?), we can set it. 
        # But for now just respecting manual state is enough.
        
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
                f"★ {player.overall_rating}"
            ]
            rating_cols = [4, 5, 6, 7, 8, 9]
        else:
            pitch_role = player.pitch_type.value[:2] if player.pitch_type else "投"
            era = record.era if record.innings_pitched > 0 else 0
            
            # 球速(km/h)をランク用数値(1-99)に変換
            if hasattr(stats, 'kmh_to_rating'):
                vel_rating = stats.kmh_to_rating(stats.velocity)
            else:
                vel_rating = int(max(1, min(99, (stats.velocity - 130) * 2 + 30)))

            data = [
                str(player.uniform_number),
                player.name,
                pitch_role,
                str(player.age),
                vel_rating,
                stats.control,
                stats.stamina,
                stats.breaking,
                str(record.wins),
                str(record.losses),
                str(record.saves),
                f"{era:.2f}" if era > 0 else "-.--",
                str(record.strikeouts_pitched),
                f"★ {player.overall_rating}"
            ]
            rating_cols = [4, 5, 6, 7]

        for col, value in enumerate(data):
            # SortableTableWidgetItem を使用してソート対応
            item = SortableTableWidgetItem()

            if col in rating_cols:
                # Rating column - store actual value for delegate
                item.setData(Qt.UserRole, value)
                item.setData(Qt.DisplayRole, "")
                item.setTextAlignment(Qt.AlignCenter)
            else:
                item.setText(str(value))
                item.setTextAlignment(Qt.AlignCenter if col != 1 else Qt.AlignLeft | Qt.AlignVCenter)
                
                # 総合力の場合は数値でソートできるように設定
                if "★" in str(value):
                    item.setForeground(QColor("#FFD700"))
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)
                    try:
                        val_num = int(str(value).replace("★ ", ""))
                        item.setData(Qt.UserRole, val_num)
                    except:
                        pass

            # Store player reference in first column (Note: col 0 has #, UserRole is used for player obj)
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

        # Type filter (for pitchers)
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
            overall_item = SortableTableWidgetItem(f"★ {player.overall_rating}")
            overall_item.setData(Qt.UserRole, player.overall_rating)
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
            
            if self.mode == "lineup": name_col = 4 # 0:順 1:守 2:調 3:疲 4:名前
            elif self.mode == "bench": name_col = 3 # 0:役割 1:調 2:疲 3:名前
            elif self.mode == "farm_batter": name_col = 1 
            elif self.mode in ["rotation", "bullpen"]: name_col = 3 # 0:役割 1:調 2:疲 3:名前
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
