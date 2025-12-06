# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Roster Page
OOTP-Style Team Roster Management
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QSplitter, QFrame, QPushButton, QComboBox
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
from UI.widgets.dialogs import PlayerDetailDialog


class RosterPage(QWidget):
    """Team roster management page"""

    player_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.current_team = None

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

        # Team selector
        team_label = QLabel("チーム:")
        team_label.setStyleSheet(f"color: {self.theme.text_secondary}; margin-left: 8px;")
        toolbar.add_widget(team_label)

        self.team_selector = QComboBox()
        self.team_selector.setMinimumWidth(180)
        self.team_selector.currentIndexChanged.connect(self._on_team_changed)
        toolbar.add_widget(self.team_selector)

        toolbar.add_separator()

        # Filter buttons
        self.show_all_btn = QPushButton("全員")
        self.show_all_btn.setCheckable(True)
        self.show_all_btn.setChecked(True)
        self.show_all_btn.clicked.connect(lambda: self._filter_players("all"))
        toolbar.add_widget(self.show_all_btn)

        self.show_active_btn = QPushButton("支配下")
        self.show_active_btn.setCheckable(True)
        self.show_active_btn.clicked.connect(lambda: self._filter_players("active"))
        toolbar.add_widget(self.show_active_btn)

        self.show_dev_btn = QPushButton("育成")
        self.show_dev_btn.setCheckable(True)
        self.show_dev_btn.clicked.connect(lambda: self._filter_players("developmental"))
        toolbar.add_widget(self.show_dev_btn)

        toolbar.add_stretch()

        # Actions
        edit_lineup_btn = QPushButton("打順編集")
        edit_lineup_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.primary};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.primary_hover};
            }}
        """)
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
                padding: 10px 20px;
            }}
        """)

        # Batters tab
        self.batter_table = PlayerTable()
        self.batter_table.player_selected.connect(self._on_player_selected)
        self.batter_table.player_double_clicked.connect(self._on_player_double_clicked)
        self.tabs.addTab(self.batter_table, "野手")

        # Pitchers tab
        self.pitcher_table = PlayerTable()
        self.pitcher_table.player_selected.connect(self._on_player_selected)
        self.pitcher_table.player_double_clicked.connect(self._on_player_double_clicked)
        self.tabs.addTab(self.pitcher_table, "投手")

        # Starting lineup tab
        self.lineup_table = RosterTable()
        self.tabs.addTab(self.lineup_table, "スタメン")

        # Rotation tab
        self.rotation_table = RosterTable()
        self.tabs.addTab(self.rotation_table, "ローテーション")

        layout.addWidget(self.tabs)

        return panel

    def _create_player_detail_panel(self) -> QWidget:
        """Create the player detail panel"""
        panel = QWidget()
        panel.setStyleSheet(f"background-color: {self.theme.bg_dark};")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 16, 16, 16)
        layout.setSpacing(16)

        # Player card
        self.detail_card = PlayerCard(show_stats=True)
        self.detail_card.set_clickable(False)
        layout.addWidget(self.detail_card)

        # Radar chart
        self.radar_chart = RadarChart()
        self.radar_chart.setMinimumHeight(250)
        layout.addWidget(self.radar_chart)

        # Info panel
        self.info_panel = InfoPanel("選手情報")
        self.info_panel.add_row("年齢", "-")
        self.info_panel.add_row("年俸", "-")
        self.info_panel.add_row("プロ年数", "-")
        self.info_panel.add_row("ステータス", "-")
        layout.addWidget(self.info_panel)

        # Stats panel
        self.stats_panel = InfoPanel("今季成績")
        layout.addWidget(self.stats_panel)

        layout.addStretch()

        # Action buttons
        btn_layout = QHBoxLayout()

        detail_btn = QPushButton("詳細")
        detail_btn.clicked.connect(self._show_player_detail)
        btn_layout.addWidget(detail_btn)

        if self.game_state:
            trade_btn = QPushButton("トレード")
            btn_layout.addWidget(trade_btn)

        layout.addLayout(btn_layout)

        return panel

    def set_game_state(self, game_state):
        """Update with game state"""
        self.game_state = game_state
        if not game_state:
            return

        # Update team selector
        self.team_selector.clear()
        for team in game_state.teams:
            self.team_selector.addItem(team.name, team)

        # Set current team
        if game_state.player_team:
            index = game_state.teams.index(game_state.player_team)
            self.team_selector.setCurrentIndex(index)

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
        batters = [p for p in team.players if p.position.value != "投手"]
        pitchers = [p for p in team.players if p.position.value == "投手"]

        # Apply current filter
        if self.show_active_btn.isChecked():
            batters = [p for p in batters if not p.is_developmental]
            pitchers = [p for p in pitchers if not p.is_developmental]
        elif self.show_dev_btn.isChecked():
            batters = [p for p in batters if p.is_developmental]
            pitchers = [p for p in pitchers if p.is_developmental]

        # Update tables
        self.batter_table.set_players(batters, mode="batter")
        self.pitcher_table.set_players(pitchers, mode="pitcher")

        # Update lineup
        if team.current_lineup:
            lineup_players = [team.players[i] for i in team.current_lineup if 0 <= i < len(team.players)]
            self.lineup_table.set_lineup(lineup_players)

        # Update rotation
        if team.rotation:
            rotation_players = [team.players[i] for i in team.rotation if 0 <= i < len(team.players)]
            self.rotation_table.set_lineup(rotation_players)

    def _filter_players(self, filter_type: str):
        """Apply player filter"""
        # Update button states
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
        """Show player detail dialog"""
        player = self.batter_table.get_selected_player() or self.pitcher_table.get_selected_player()
        if player:
            dialog = PlayerDetailDialog(player, self)
            dialog.exec()
