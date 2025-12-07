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


        # North League Card
        self.north_card = StandingsCard("NORTH LEAGUE")
        self.tables_layout.addWidget(self.north_card)

        # South League Card
        self.south_card = StandingsCard("SOUTH LEAGUE")
        self.tables_layout.addWidget(self.south_card)

        self.add_layout(self.tables_layout)
        self.add_stretch()

    def set_game_state(self, game_state):
        self.game_state = game_state
        if not game_state or not hasattr(game_state, 'all_teams'):
            return

        north_teams = [t for t in game_state.all_teams if getattr(t.league, 'value', '').lower() == "north" or getattr(t.league, 'name', '').upper() == "NORTH"]
        south_teams = [t for t in game_state.all_teams if getattr(t.league, 'value', '').lower() == "south" or getattr(t.league, 'name', '').upper() == "SOUTH"]

        north_teams.sort(key=lambda x: x.winning_percentage, reverse=True)
        south_teams.sort(key=lambda x: x.winning_percentage, reverse=True)

        self.north_card.set_standings(north_teams)
        self.south_card.set_standings(south_teams)