# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Starfield Standings Page
Industrial Sci-Fi League Standings
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel
)
from PySide6.QtCore import Qt
from UI.theme import get_theme
from UI.widgets.panels import ContentPanel
from UI.widgets.cards import StandingsCard

class StandingsPage(ContentPanel):
    """Starfield Style Standings Page"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self._setup_ui()

    def _setup_ui(self):
        # Header
        header = QLabel("LEAGUE STANDINGS")
        header.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 300;
            color: {self.theme.text_primary};
            letter-spacing: 4px;
            margin-bottom: 16px;
        """)
        self.add_widget(header)

        # Standings Layout
        self.tables_layout = QHBoxLayout()
        self.tables_layout.setSpacing(24)

        # Central League Card
        self.central_card = StandingsCard("CENTRAL LEAGUE")
        self.tables_layout.addWidget(self.central_card)

        # Pacific League Card
        self.pacific_card = StandingsCard("PACIFIC LEAGUE")
        self.tables_layout.addWidget(self.pacific_card)

        self.add_layout(self.tables_layout)
        self.add_stretch()

    def set_game_state(self, game_state):
        self.game_state = game_state
        if not game_state or not hasattr(game_state, 'all_teams'):
            return

        central_teams = [t for t in game_state.all_teams if t.league.value == "central" or t.league.name == "CENTRAL"]
        pacific_teams = [t for t in game_state.all_teams if t.league.value == "pacific" or t.league.name == "PACIFIC"]

        central_teams.sort(key=lambda x: x.winning_percentage, reverse=True)
        pacific_teams.sort(key=lambda x: x.winning_percentage, reverse=True)

        self.central_card.set_standings(central_teams)
        self.pacific_card.set_standings(pacific_teams)