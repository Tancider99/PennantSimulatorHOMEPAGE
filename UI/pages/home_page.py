# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Home Page
Industrial Sci-Fi Dashboard with High Information Density
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QFrame, QPushButton, QScrollArea, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.cards import Card, StatCard, TeamCard, StandingsCard, PlayerCard
from UI.widgets.panels import ContentPanel, InfoPanel
from UI.widgets.buttons import ActionButton
from models import TEAM_COLORS


class TeamColorBar(QWidget):
    """Team color indicator bar"""
    def __init__(self, team, height=80, width=8, parent=None):
        super().__init__(parent)
        self.team = team
        self.setFixedSize(width, height)
        self.theme = get_theme()
        color = getattr(team, 'color', None)
        if not color:
            color = TEAM_COLORS.get(getattr(team, 'name', ''), self.theme.primary)
        self.setStyleSheet(f"background-color: {color}; border-radius: 0px;")


class CompactStatCard(QFrame):
    """Compact stat card for high density display"""
    def __init__(self, label: str, value: str, sub: str = "", color: str = None, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._color = color or self.theme.text_primary

        self.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
                border-radius: 0px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted}; letter-spacing: 1px; font-weight: 600;")
        layout.addWidget(lbl)

        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {self._color};")
        layout.addWidget(self._value_label)

        self._sub_label = QLabel(sub)
        self._sub_label.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted};")
        layout.addWidget(self._sub_label)

    def set_value(self, value: str):
        self._value_label.setText(value)

    def set_sub(self, sub: str):
        self._sub_label.setText(sub)

    def set_text_color(self, color: str):
        """Set the text color of the value label"""
        self._value_label.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {color};")


class MatchupCard(QFrame):
    """Next game matchup card"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()

        self.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
                border-radius: 0px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        header = QLabel("NEXT GAME")
        header.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted}; letter-spacing: 2px; font-weight: 600;")
        layout.addWidget(header)

        self.matchup_layout = QHBoxLayout()
        self.matchup_layout.setSpacing(12)

        self.away_label = QLabel("---")
        self.away_label.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.theme.text_primary};")
        self.away_label.setAlignment(Qt.AlignCenter)

        vs_label = QLabel("@")
        vs_label.setStyleSheet(f"font-size: 12px; color: {self.theme.text_muted};")
        vs_label.setAlignment(Qt.AlignCenter)

        self.home_label = QLabel("---")
        self.home_label.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.theme.text_primary};")
        self.home_label.setAlignment(Qt.AlignCenter)

        self.matchup_layout.addWidget(self.away_label)
        self.matchup_layout.addWidget(vs_label)
        self.matchup_layout.addWidget(self.home_label)
        layout.addLayout(self.matchup_layout)

        self.date_label = QLabel("---")
        self.date_label.setStyleSheet(f"font-size: 11px; color: {self.theme.text_secondary};")
        layout.addWidget(self.date_label)

        self.pitcher_label = QLabel("---")
        self.pitcher_label.setStyleSheet(f"font-size: 10px; color: {self.theme.accent_blue};")
        layout.addWidget(self.pitcher_label)

    def set_matchup(self, home: str, away: str, date: str, pitcher: str = ""):
        self.home_label.setText(home[:8] if home else "---")
        self.away_label.setText(away[:8] if away else "---")
        self.date_label.setText(date)
        self.pitcher_label.setText(f"Starter: {pitcher}" if pitcher else "")


class RecentResultsCard(QFrame):
    """Recent game results card"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()

        self.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
                border-radius: 0px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        header = QLabel("RECENT RESULTS")
        header.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted}; letter-spacing: 2px; font-weight: 600;")
        layout.addWidget(header)

        self.results_layout = QHBoxLayout()
        self.results_layout.setSpacing(4)
        self.result_labels = []

        for i in range(10):
            lbl = QLabel("-")
            lbl.setFixedSize(24, 24)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"""
                font-size: 11px;
                font-weight: 700;
                color: {self.theme.text_muted};
                background: {self.theme.bg_input};
                border-radius: 0px;
            """)
            self.results_layout.addWidget(lbl)
            self.result_labels.append(lbl)

        layout.addLayout(self.results_layout)

    def set_results(self, results: list):
        """Set recent results (list of 'W', 'L', 'D')"""
        for i, lbl in enumerate(self.result_labels):
            if i < len(results):
                r = results[i]
                if r == 'W':
                    lbl.setText("W")
                    lbl.setStyleSheet(f"""
                        font-size: 11px; font-weight: 700;
                        color: white; background: {self.theme.success};
                        border-radius: 0px;
                    """)
                elif r == 'L':
                    lbl.setText("L")
                    lbl.setStyleSheet(f"""
                        font-size: 11px; font-weight: 700;
                        color: white; background: {self.theme.danger};
                        border-radius: 0px;
                    """)
                else:
                    lbl.setText("D")
                    lbl.setStyleSheet(f"""
                        font-size: 11px; font-weight: 700;
                        color: white; background: {self.theme.text_muted};
                        border-radius: 0px;
                    """)
            else:
                lbl.setText("-")
                lbl.setStyleSheet(f"""
                    font-size: 11px; font-weight: 700;
                    color: {self.theme.text_muted}; background: {self.theme.bg_input};
                    border-radius: 0px;
                """)


class LeaderCard(QFrame):
    """Team leader stat card"""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._title = title

        self.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        header = QLabel(title)
        header.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted}; letter-spacing: 1px; font-weight: 600;")
        layout.addWidget(header)

        self.entries_layout = QVBoxLayout()
        self.entries_layout.setSpacing(4)
        layout.addLayout(self.entries_layout)

    def set_leaders(self, leaders: list):
        """Set leaders list [(name, value), ...]"""
        while self.entries_layout.count():
            item = self.entries_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, (name, value) in enumerate(leaders[:3]):
            row = QHBoxLayout()
            rank = QLabel(f"{i+1}.")
            rank.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted}; min-width: 16px;")
            row.addWidget(rank)

            name_lbl = QLabel(name[:8])
            name_lbl.setStyleSheet(f"font-size: 11px; color: {self.theme.text_primary};")
            row.addWidget(name_lbl)
            row.addStretch()

            val_lbl = QLabel(str(value))
            val_lbl.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {self.theme.accent_blue};")
            row.addWidget(val_lbl)

            container = QWidget()
            container.setLayout(row)
            self.entries_layout.addWidget(container)


class TodayGamesCard(QFrame):
    """Today's all games card"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()

        self.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        header = QLabel("TODAY'S GAMES")
        header.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted}; letter-spacing: 2px; font-weight: 600;")
        layout.addWidget(header)

        self.games_layout = QVBoxLayout()
        self.games_layout.setSpacing(4)
        layout.addLayout(self.games_layout)

    def set_games(self, games: list, teams_dict: dict = None):
        """Set today's games [(home, away, home_score, away_score, status), ...]"""
        while self.games_layout.count():
            item = self.games_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not games:
            no_games = QLabel("No games today")
            no_games.setStyleSheet(f"font-size: 11px; color: {self.theme.text_muted};")
            self.games_layout.addWidget(no_games)
            return

        for game in games[:6]:
            row = QHBoxLayout()
            row.setSpacing(8)

            away_name = game.away_team_name[:6] if hasattr(game, 'away_team_name') else str(game[1])[:6]
            home_name = game.home_team_name[:6] if hasattr(game, 'home_team_name') else str(game[0])[:6]

            away_lbl = QLabel(away_name)
            away_lbl.setStyleSheet(f"font-size: 11px; color: {self.theme.text_primary}; min-width: 60px;")
            away_lbl.setAlignment(Qt.AlignRight)
            row.addWidget(away_lbl)

            at_lbl = QLabel("@")
            at_lbl.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted};")
            row.addWidget(at_lbl)

            home_lbl = QLabel(home_name)
            home_lbl.setStyleSheet(f"font-size: 11px; color: {self.theme.text_primary}; min-width: 60px;")
            row.addWidget(home_lbl)

            row.addStretch()

            status = getattr(game, 'status', None)
            if status and str(status) == "GameStatus.COMPLETED":
                score_lbl = QLabel(f"{game.away_score}-{game.home_score}")
                score_lbl.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {self.theme.accent_blue};")
            else:
                score_lbl = QLabel("--")
                score_lbl.setStyleSheet(f"font-size: 11px; color: {self.theme.text_muted};")
            row.addWidget(score_lbl)

            container = QWidget()
            container.setLayout(row)
            self.games_layout.addWidget(container)


class TeamStatsCard(QFrame):
    """Team stats summary card"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()

        self.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        header = QLabel("TEAM STATS")
        header.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted}; letter-spacing: 2px; font-weight: 600;")
        layout.addWidget(header)

        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(8)

        self.stat_labels = {}
        stats = [("AVG", 0, 0), ("HR", 0, 1), ("RBI", 1, 0), ("ERA", 1, 1)]
        for label, r, c in stats:
            stat_widget = QWidget()
            stat_layout = QVBoxLayout(stat_widget)
            stat_layout.setContentsMargins(0, 0, 0, 0)
            stat_layout.setSpacing(2)

            name_lbl = QLabel(label)
            name_lbl.setStyleSheet(f"font-size: 9px; color: {self.theme.text_muted};")
            stat_layout.addWidget(name_lbl)

            val_lbl = QLabel("---")
            val_lbl.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {self.theme.text_primary};")
            stat_layout.addWidget(val_lbl)

            self.stat_labels[label] = val_lbl
            self.stats_grid.addWidget(stat_widget, r, c)

        layout.addLayout(self.stats_grid)

    def set_team_stats(self, avg: str, hr: int, rbi: int, era: str):
        """Set team stats"""
        self.stat_labels["AVG"].setText(avg)
        self.stat_labels["HR"].setText(str(hr))
        self.stat_labels["RBI"].setText(str(rbi))
        self.stat_labels["ERA"].setText(era)


class HomePage(ContentPanel):
    """Home page with high-density industrial dashboard"""

    game_requested = Signal()
    view_roster_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self._create_ui()

    def _create_ui(self):
        """Create the dashboard layout"""
        # Header section
        self._create_header()

        # Main grid
        main_grid = QGridLayout()
        main_grid.setSpacing(12)
        main_grid.setContentsMargins(0, 0, 0, 0)

        # Row 1: Stats cards
        self._create_stats_row(main_grid, 0)

        # Row 2: Matchup + Results + Actions
        self._create_info_row(main_grid, 1)

        # Row 3: Leaders + Standings
        self._create_data_row(main_grid, 2)

        self.add_layout(main_grid)
        self.add_stretch()

    def _create_header(self):
        """Create header with team info and action buttons"""
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
                border-radius: 0px;
            }}
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)

        # Team info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        self.team_name_label = QLabel("SELECT TEAM")
        self.team_name_label.setStyleSheet(f"""
            font-size: 28px;
            font-weight: 800;
            color: {self.theme.text_primary};
            letter-spacing: 1px;
            border: none;
        """)
        info_layout.addWidget(self.team_name_label)

        self.season_label = QLabel("2027 SEASON")
        self.season_label.setStyleSheet(f"font-size: 12px; color: {self.theme.text_secondary};")
        info_layout.addWidget(self.season_label)

        layout.addLayout(info_layout)
        layout.addStretch()

        # Action buttons - stylish and sharp
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.play_btn = QPushButton("PLAY NEXT GAME")
        self.play_btn.setCursor(Qt.PointingHandCursor)
        self.play_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.text_primary};
                color: {self.theme.bg_dark};
                border: none;
                border-radius: 0px;
                padding: 14px 28px;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: {self.theme.text_secondary};
            }}
        """)
        self.play_btn.clicked.connect(lambda: self.game_requested.emit())
        btn_layout.addWidget(self.play_btn)

        # Removed Skip Button as requested
        # self.sim_btn = QPushButton("SKIP 1 WEEK")
        # ...

        layout.addLayout(btn_layout)

        self.add_widget(header)

    def _create_stats_row(self, grid: QGridLayout, row: int):
        """Create stats cards row"""
        self.record_card = CompactStatCard("RECORD", "0-0-0", "Win%: .000", self.theme.text_primary)
        grid.addWidget(self.record_card, row, 0)

        # Changed to text_primary for muted look
        self.rank_card = CompactStatCard("RANK", "-", "Games Back: -", self.theme.text_primary)
        grid.addWidget(self.rank_card, row, 1)

        # Changed to text_primary for muted look
        self.games_card = CompactStatCard("GAMES", "0/143", "Progress: 0%", self.theme.text_primary)
        grid.addWidget(self.games_card, row, 2)

        self.streak_card = CompactStatCard("STREAK", "-", "Last 10: -", self.theme.success)
        grid.addWidget(self.streak_card, row, 3)

    def _create_info_row(self, grid: QGridLayout, row: int):
        """Create info cards row"""
        self.matchup_card = MatchupCard()
        grid.addWidget(self.matchup_card, row, 0, 1, 2)

        self.results_card = RecentResultsCard()
        grid.addWidget(self.results_card, row, 2, 1, 2)

    def _create_data_row(self, grid: QGridLayout, row: int):
        """Create data cards row"""
        # Leaders section
        leaders_frame = QFrame()
        leaders_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
                border-radius: 0px;
            }}
        """)
        leaders_layout = QVBoxLayout(leaders_frame)
        leaders_layout.setContentsMargins(16, 12, 16, 12)
        leaders_layout.setSpacing(8)

        leaders_header = QLabel("TEAM LEADERS")
        leaders_header.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted}; letter-spacing: 2px; font-weight: 600;")
        leaders_layout.addWidget(leaders_header)

        leaders_grid = QGridLayout()
        leaders_grid.setSpacing(8)

        self.avg_leaders = LeaderCard("BATTING AVG")
        leaders_grid.addWidget(self.avg_leaders, 0, 0)

        self.hr_leaders = LeaderCard("HOME RUNS")
        leaders_grid.addWidget(self.hr_leaders, 0, 1)

        self.era_leaders = LeaderCard("ERA")
        leaders_grid.addWidget(self.era_leaders, 1, 0)

        self.wins_leaders = LeaderCard("WINS")
        leaders_grid.addWidget(self.wins_leaders, 1, 1)

        leaders_layout.addLayout(leaders_grid)
        grid.addWidget(leaders_frame, row, 0, 1, 2)

        # Standings
        self.standings_card = StandingsCard("STANDINGS")
        grid.addWidget(self.standings_card, row, 2, 1, 2)

    def set_game_state(self, game_state):
        """Update page with game state"""
        self.game_state = game_state
        if not game_state:
            return

        team = game_state.player_team
        if not team:
            return

        # Header
        self.team_name_label.setText(team.name.upper())
        league_name = "North League" if getattr(team.league, 'value', None) == "North League" else ("South League" if getattr(team.league, 'value', None) == "South League" else (team.league.value if team.league else ""))
        date_str = getattr(game_state, 'current_date', '2027-03-29')
        self.season_label.setText(f"{game_state.current_year} SEASON  |  {league_name}  |  {date_str}")

        # Record
        self.record_card.set_value(f"{team.wins}-{team.losses}-{team.draws}")
        pct = team.winning_percentage
        self.record_card.set_sub(f"Win%: .{int(pct * 1000):03d}")

        # Rank
        if hasattr(game_state, 'teams') and game_state.teams:
            league_teams = [t for t in game_state.teams if t.league == team.league]
            league_teams.sort(key=lambda t: t.winning_percentage, reverse=True)
            rank = next((i + 1 for i, t in enumerate(league_teams) if t.name == team.name), 0)
            self.rank_card.set_value(f"#{rank}" if rank else "-")

            # Update rank color: Gold for 1st place, default color otherwise
            if rank == 1:
                self.rank_card.set_text_color("#e6b422")
            else:
                self.rank_card.set_text_color(self.theme.text_primary)

            if rank > 1 and league_teams:
                leader = league_teams[0]
                gb = ((leader.wins - team.wins) + (team.losses - leader.losses)) / 2
                self.rank_card.set_sub(f"Games Back: {gb:.1f}")
            else:
                self.rank_card.set_sub("Leading")

            # Standings
            self.standings_card.set_standings(league_teams[:6])

        # Games progress
        games_played = team.wins + team.losses + team.draws
        progress = (games_played / 143) * 100
        self.games_card.set_value(f"{games_played}/143")
        self.games_card.set_sub(f"Progress: {progress:.0f}%")

        # Next game from schedule & Button Text Update
        has_game_today = self._update_next_game(game_state, team)
        
        # Update Button Text based on game availability
        if has_game_today:
            self.play_btn.setText("PLAY NEXT GAME")
        else:
            self.play_btn.setText("NEXT DAY")

        # Recent results
        self._update_recent_results(game_state, team)

        # Leaders
        self._update_leaders(team)

    def _update_next_game(self, game_state, team):
        """Update next game display from schedule and return True if game exists today"""
        next_game = game_state.get_next_game() if hasattr(game_state, 'get_next_game') else None
        
        has_game_today = False
        today_str = getattr(game_state, 'current_date', '')
        
        if next_game:
            home = next_game.home_team_name
            away = next_game.away_team_name
            date = next_game.date
            
            if date == today_str:
                has_game_today = True
            
            # Find opponent's starter
            starter_name = ""
            opponent_name = away if home == team.name else home
            for t in game_state.teams:
                if t.name == opponent_name:
                    starter = t.get_today_starter()
                    if starter:
                        starter_name = starter.name
                    break
            self.matchup_card.set_matchup(home, away, date, starter_name)
        else:
            self.matchup_card.set_matchup("---", "---", "No games scheduled", "")
            
        return has_game_today

    def _update_recent_results(self, game_state, team):
        """Update recent results display"""
        results = []
        if hasattr(game_state, 'get_recent_results'):
            results = game_state.get_recent_results(team.name, 10)
        self.results_card.set_results(results)

    def _update_leaders(self, team):
        """Update team leaders"""
        batters = [p for p in team.players if p.position.value != "投手" and not p.is_developmental]
        pitchers = [p for p in team.players if p.position.value == "投手" and not p.is_developmental]

        # Batting average
        batters_sorted = sorted(batters, key=lambda p: p.record.batting_average, reverse=True)
        self.avg_leaders.set_leaders([
            (p.name, f".{int(p.record.batting_average * 1000):03d}" if p.record.at_bats > 0 else ".---")
            for p in batters_sorted[:3]
        ])

        # Home runs
        hr_sorted = sorted(batters, key=lambda p: p.record.home_runs, reverse=True)
        self.hr_leaders.set_leaders([
            (p.name, p.record.home_runs) for p in hr_sorted[:3]
        ])

        # ERA
        pitchers_sorted = sorted(pitchers, key=lambda p: p.record.era if p.record.innings_pitched > 0 else 99)
        self.era_leaders.set_leaders([
            (p.name, f"{p.record.era:.2f}" if p.record.innings_pitched > 0 else "-.--")
            for p in pitchers_sorted[:3]
        ])

        # Wins
        wins_sorted = sorted(pitchers, key=lambda p: p.record.wins, reverse=True)
        self.wins_leaders.set_leaders([
            (p.name, p.record.wins) for p in wins_sorted[:3]
        ])