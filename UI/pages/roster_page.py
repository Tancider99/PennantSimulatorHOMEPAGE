# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Roster Page
OOTP-Style Team Roster Management
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QSplitter, QFrame, QPushButton, QComboBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.cards import Card, PlayerCard
from UI.widgets.tables import PlayerTable, RosterTable
from UI.widgets.panels import ContentPanel, InfoPanel, ToolbarPanel
from UI.widgets.charts import RadarChart
from UI.widgets.dialogs import PlayerDetailDialog, OrderDialog


class RosterPage(QWidget):
    """Team roster management page"""

    player_selected = Signal(object)
    show_player_detail_requested = None  # Will be set by MainWindow

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.current_team = None
        self.main_window = parent  # Reference to parent for navigation

        self._setup_ui()

    def _setup_ui(self):
        """Create the roster page layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Main content with splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {self.theme.border};
                width: 2px;
            }}
        """)

        # Left panel - Player list
        left_panel = self._create_player_list_panel()
        splitter.addWidget(left_panel)

        # Right panel - Player details
        right_panel = self._create_player_detail_panel()
        splitter.addWidget(right_panel)

        # Set initial sizes (70/30 split)
        splitter.setSizes([700, 300])

        layout.addWidget(splitter)

    def _create_toolbar(self) -> ToolbarPanel:
        """Create the toolbar"""
        toolbar = ToolbarPanel()
        toolbar.setFixedHeight(50)  # Fixed height for consistency

        # Team selector
        team_label = QLabel("チーム:")
        team_label.setStyleSheet(f"color: {self.theme.text_secondary}; margin-left: 8px;")
        toolbar.add_widget(team_label)

        self.team_selector = QComboBox()
        self.team_selector.setMinimumWidth(180)
        self.team_selector.setFixedHeight(32)  # Fixed height
        
        # コンボボックスのスタイル
        self.team_selector.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 2px solid {self.theme.text_secondary};
                border-bottom: 2px solid {self.theme.text_secondary};
                width: 8px;
                height: 8px;
                margin-right: 8px;
                transform: rotate(-45deg);
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.theme.bg_card};
                color: {self.theme.text_primary};
                selection-background-color: {self.theme.primary};
                selection-color: {self.theme.text_highlight};
                border: 1px solid {self.theme.border};
            }}
        """)
        
        self.team_selector.currentIndexChanged.connect(self._on_team_changed)
        toolbar.add_widget(self.team_selector)

        toolbar.add_separator()

        # フィルタボタン用のスタイル（チェック時に白背景・黒文字にする）
        filter_btn_style = f"""
            QPushButton {{
                background-color: {self.theme.bg_card};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 4px;
                padding: 4px 12px;
            }}
            QPushButton:checked {{
                background-color: {self.theme.primary};
                color: {self.theme.text_highlight}; /* 白背景なので文字は濃色 */
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme.bg_card_hover};
                border-color: {self.theme.primary};
            }}
            QPushButton:checked:hover {{
                background-color: {self.theme.primary_hover};
            }}
        """

        # Filter buttons
        self.show_all_btn = QPushButton("全員")
        self.show_all_btn.setCheckable(True)
        self.show_all_btn.setChecked(True)
        self.show_all_btn.setStyleSheet(filter_btn_style)
        self.show_all_btn.clicked.connect(lambda: self._filter_players("all"))
        toolbar.add_widget(self.show_all_btn)

        self.show_active_btn = QPushButton("支配下")
        self.show_active_btn.setCheckable(True)
        self.show_active_btn.setStyleSheet(filter_btn_style)
        self.show_active_btn.clicked.connect(lambda: self._filter_players("active"))
        toolbar.add_widget(self.show_active_btn)

        self.show_dev_btn = QPushButton("育成")
        self.show_dev_btn.setCheckable(True)
        self.show_dev_btn.setStyleSheet(filter_btn_style)
        self.show_dev_btn.clicked.connect(lambda: self._filter_players("developmental"))
        toolbar.add_widget(self.show_dev_btn)

        toolbar.add_stretch()

        # Actions
        edit_lineup_btn = QPushButton("オーダー")
        edit_lineup_btn.setCursor(Qt.PointingHandCursor)
        edit_lineup_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.primary};
                color: {self.theme.text_highlight};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {self.theme.primary_hover};
            }}
        """)
        edit_lineup_btn.clicked.connect(self._show_order_dialog)
        toolbar.add_widget(edit_lineup_btn)

        return toolbar

    def _create_player_list_panel(self) -> QWidget:
        """Create the player list panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 8, 16)

        # Tabs for different views
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {self.theme.border};
                border-radius: 8px;
                background-color: {self.theme.bg_card};
            }}
            QTabBar::tab {{
                background-color: transparent;
                color: {self.theme.text_secondary};
                padding: 10px 20px;
                border-bottom: 2px solid transparent;
            }}
            QTabBar::tab:selected {{
                color: {self.theme.primary};
                border-bottom: 2px solid {self.theme.primary};
            }}
            QTabBar::tab:hover {{
                color: {self.theme.text_primary};
            }}
        """)

        # 【修正】スタイルシートでホバーエフェクトを無効化
        # item:hover の背景色を transparent にし、文字色を通常時と同じに設定
        table_style = f"""
            QTableView {{
                selection-color: #222222;
                background-color: {self.theme.bg_card};
                alternate-background-color: {self.theme.bg_input};
            }}
            QTableView::item:selected {{
                color: #222222;
                background-color: {self.theme.primary};
            }}
            QTableView::item:hover {{
                background-color: transparent;
                color: {self.theme.text_primary};
                border: none;
            }}
            QTableView::item:selected:hover {{
                background-color: {self.theme.primary};
                color: #222222;
            }}
        """

        # Batters tab
        self.batter_table = PlayerTable()
        self.batter_table.setStyleSheet(table_style) # スタイル適用
        self.batter_table.player_selected.connect(self._on_player_selected)
        self.batter_table.player_double_clicked.connect(self._on_player_double_clicked)
        self.tabs.addTab(self.batter_table, "野手")

        # Pitchers tab
        self.pitcher_table = PlayerTable()
        self.pitcher_table.setStyleSheet(table_style) # スタイル適用
        self.pitcher_table.player_selected.connect(self._on_player_selected)
        self.pitcher_table.player_double_clicked.connect(self._on_player_double_clicked)
        self.tabs.addTab(self.pitcher_table, "投手")

        layout.addWidget(self.tabs)

        return panel

    def _create_player_detail_panel(self) -> QWidget:
        """Create the player detail panel"""
        # Use scroll area for the panel to handle overflow
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {self.theme.bg_dark};
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {self.theme.bg_dark};
                width: 8px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {self.theme.border};
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

        panel = QWidget()
        panel.setStyleSheet(f"background-color: {self.theme.bg_dark};")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 16, 8)
        layout.setSpacing(6)

        # Player card - compact version
        self.detail_card = PlayerCard(show_stats=True)
        self.detail_card.set_clickable(False)
        self.detail_card.setFixedHeight(100)
        layout.addWidget(self.detail_card)

        # Radar chart - in a fixed-size container
        chart_container = QFrame()
        chart_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
            }}
        """)
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(4, 4, 4, 4)

        self.radar_chart = RadarChart()
        self.radar_chart.setFixedSize(200, 200)
        chart_layout.addWidget(self.radar_chart, 0, Qt.AlignCenter)

        layout.addWidget(chart_container)

        # Info panel - more compact
        self.info_panel = InfoPanel("選手情報")
        layout.addWidget(self.info_panel)

        # Stats panel
        self.stats_panel = InfoPanel("今季成績")
        layout.addWidget(self.stats_panel)

        layout.addStretch()

        # Action buttons - fixed at bottom
        btn_container = QWidget()
        btn_container.setStyleSheet("background: transparent;")
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.setContentsMargins(0, 4, 0, 0)

        detail_btn = QPushButton("詳細")
        detail_btn.setFixedHeight(34)
        detail_btn.setCursor(Qt.PointingHandCursor)
        # 【修正】文字色をwhiteからtext_highlightに変更（背景がprimary=白のため）
        detail_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.primary};
                color: {self.theme.text_highlight};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {self.theme.primary_hover};
            }}
        """)
        detail_btn.clicked.connect(self._show_player_detail)
        btn_layout.addWidget(detail_btn)

        layout.addWidget(btn_container)

        scroll.setWidget(panel)
        return scroll

    def set_game_state(self, game_state):
        """Update with game state"""
        self.game_state = game_state
        if not game_state:
            return

        # Update team selector
        self.team_selector.clear()
        
        # 自チームを判別しやすくする
        player_team_obj = game_state.player_team
        
        for team in game_state.teams:
            display_name = team.name
            if player_team_obj and team.name == player_team_obj.name:
                display_name = f"{team.name} (自チーム)"
                
            self.team_selector.addItem(display_name, team)

        # Set current team
        if player_team_obj:
            # 名前が変わったのでインデックス検索はオブジェクトの一致で探す
            for i in range(self.team_selector.count()):
                if self.team_selector.itemData(i) == player_team_obj:
                    self.team_selector.setCurrentIndex(i)
                    break
        elif game_state.teams:
            self.team_selector.setCurrentIndex(0)

    def _on_team_changed(self, index: int):
        """Handle team selection change"""
        if index < 0 or not self.game_state:
            return

        self.current_team = self.team_selector.itemData(index)
        self._refresh_player_lists()

    def _refresh_player_lists(self):
        """Refresh all player lists"""
        if not self.current_team:
            return

        team = self.current_team

        # Get filtered players
        all_batters = [p for p in team.players if p.position.value != "投手"]
        all_pitchers = [p for p in team.players if p.position.value == "投手"]

        batters = []
        pitchers = []

        # Apply current filter
        if self.show_active_btn.isChecked():
            batters = [p for p in all_batters if not p.is_developmental]
            pitchers = [p for p in all_pitchers if not p.is_developmental]
        elif self.show_dev_btn.isChecked():
            batters = [p for p in all_batters if p.is_developmental]
            pitchers = [p for p in all_pitchers if p.is_developmental]
        else:
            # Show all
            batters = list(all_batters)
            pitchers = list(all_pitchers)

        # 【修正】並び順を安定させるためにソートを行う (例: 背番号順)
        # 操作によってリスト順序が変わることを防ぐ
        batters.sort(key=lambda p: p.uniform_number if hasattr(p, 'uniform_number') else 0)
        pitchers.sort(key=lambda p: p.uniform_number if hasattr(p, 'uniform_number') else 0)

        # Update tables
        self.batter_table.set_players(batters, mode="batter")
        self.pitcher_table.set_players(pitchers, mode="pitcher")

    def _filter_players(self, filter_type: str):
        """Apply player filter"""
        # Update button states
        # 排他的なチェック状態にする（手動で制御）
        self.show_all_btn.setChecked(filter_type == "all")
        self.show_active_btn.setChecked(filter_type == "active")
        self.show_dev_btn.setChecked(filter_type == "developmental")

        self._refresh_player_lists()

    def _on_player_selected(self, player):
        """Handle player selection"""
        if not player:
            return

        # Update detail card
        self.detail_card.set_player(player)

        # Update radar chart
        is_pitcher = player.position.value == "投手"
        self.radar_chart.set_player_stats(player, is_pitcher)

        # Update info panel
        self._update_info_panel(player)

        # Update stats panel
        self._update_stats_panel(player)

        self.player_selected.emit(player)

    def _update_info_panel(self, player):
        """Update the info panel with player data"""
        # Clear and rebuild
        while self.info_panel.content_layout.count():
            item = self.info_panel.content_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()

        self.info_panel.add_row("年齢", f"{player.age}歳")
        self.info_panel.add_row("年俸", f"{player.salary // 10000}万円")
        self.info_panel.add_row("プロ年数", f"{player.years_pro}年目")

        status = "育成" if player.is_developmental else "支配下"
        if player.is_foreign:
            status += " (外国人)"
        self.info_panel.add_row("ステータス", status)

        # Position info
        pos_text = player.position.value
        if player.sub_positions:
            sub_pos = ", ".join([p.value[:2] for p in player.sub_positions])
            pos_text += f" (サブ: {sub_pos})"
        self.info_panel.add_row("ポジション", pos_text)

    def _update_stats_panel(self, player):
        """Update the stats panel with player stats"""
        # Clear and rebuild
        while self.stats_panel.content_layout.count():
            item = self.stats_panel.content_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()

        record = player.record
        is_pitcher = player.position.value == "投手"

        if is_pitcher:
            self.stats_panel.add_row("登板", str(record.games_pitched))
            self.stats_panel.add_row("勝敗", f"{record.wins}勝{record.losses}敗")
            self.stats_panel.add_row("セーブ", str(record.saves))
            era = record.era if record.innings_pitched > 0 else 0
            self.stats_panel.add_row("防御率", f"{era:.2f}")
            self.stats_panel.add_row("投球回", f"{record.innings_pitched:.1f}")
            self.stats_panel.add_row("奪三振", str(record.strikeouts_pitched))
        else:
            avg = record.batting_average if record.at_bats > 0 else 0
            self.stats_panel.add_row("打率", f".{int(avg * 1000):03d}")
            self.stats_panel.add_row("打数-安打", f"{record.at_bats}-{record.hits}")
            self.stats_panel.add_row("本塁打", str(record.home_runs))
            self.stats_panel.add_row("打点", str(record.rbis))
            self.stats_panel.add_row("盗塁", str(record.stolen_bases))
            self.stats_panel.add_row("三振", str(record.strikeouts))

    def _on_player_double_clicked(self, player):
        """Handle player double click"""
        self._show_player_detail()

    def _show_player_detail(self):
        """Show player detail page"""
        player = self.batter_table.get_selected_player() or self.pitcher_table.get_selected_player()
        if player:
            # Use callback if set by MainWindow, otherwise fall back to dialog
            if self.show_player_detail_requested:
                self.show_player_detail_requested(player)
            else:
                dialog = PlayerDetailDialog(player, self)
                dialog.exec()

    def _show_order_dialog(self):
        """Navigate to order page"""
        if not self.current_team:
            return

        # Navigate to order page via main window
        if self.main_window and hasattr(self.main_window, '_navigate_to'):
            self.main_window._navigate_to("order")
        else:
            # Fallback to dialog if main_window navigation not available
            dialog = OrderDialog(self.current_team, self)
            if dialog.exec():
                self._refresh_player_lists()