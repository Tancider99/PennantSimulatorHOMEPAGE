# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Home Page
Industrial Sci-Fi Dashboard with High Information Density
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QFrame, QPushButton, QScrollArea, QGraphicsDropShadowEffect,
    QButtonGroup
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.cards import Card, StatCard, TeamCard, StandingsCard, PlayerCard
from UI.widgets.panels import ContentPanel, InfoPanel
from UI.widgets.buttons import ActionButton
from models import TEAM_COLORS


class CompactStandingsCard(QFrame):
    """Compact standings with league toggle"""
    league_changed = Signal(str)  # Emits "north" or "south"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.current_league = "north"
        self.north_teams = []
        self.south_teams = []
        
        self.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)
        
        # Header with toggle
        header_layout = QHBoxLayout()
        header_layout.setSpacing(4)
        
        header = QLabel("STANDINGS")
        header.setStyleSheet(f"font-size: 9px; color: {self.theme.text_muted}; letter-spacing: 2px; font-weight: 600;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        # Toggle buttons
        self.north_btn = QPushButton("N")
        self.south_btn = QPushButton("S")
        
        for btn in [self.north_btn, self.south_btn]:
            btn.setFixedSize(22, 18)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setCheckable(True)
        
        self.north_btn.setChecked(True)
        self._update_btn_styles()
        
        self.north_btn.clicked.connect(lambda: self._switch_league("north"))
        self.south_btn.clicked.connect(lambda: self._switch_league("south"))
        
        header_layout.addWidget(self.north_btn)
        header_layout.addWidget(self.south_btn)
        layout.addLayout(header_layout)
        
        # Standings rows
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(1)
        layout.addLayout(self.rows_layout)
    
    def _update_btn_styles(self):
        for btn, is_active in [(self.north_btn, self.current_league == "north"),
                               (self.south_btn, self.current_league == "south")]:
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {self.theme.primary};
                        color: white;
                        border: none;
                        font-size: 9px;
                        font-weight: 700;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {self.theme.bg_input};
                        color: {self.theme.text_muted};
                        border: none;
                        font-size: 9px;
                    }}
                    QPushButton:hover {{
                        background: {self.theme.bg_card_hover};
                    }}
                """)
    
    def _switch_league(self, league):
        self.current_league = league
        self.north_btn.setChecked(league == "north")
        self.south_btn.setChecked(league == "south")
        self._update_btn_styles()
        self._refresh_standings()
        self.league_changed.emit(league)
    
    def set_standings(self, north_teams: list, south_teams: list):
        """Set both league standings"""
        self.north_teams = north_teams
        self.south_teams = south_teams
        self._refresh_standings()
    
    def _refresh_standings(self):
        """Refresh with current league"""
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        teams = self.north_teams if self.current_league == "north" else self.south_teams
        if not teams:
            return
        
        top_pct = teams[0].winning_percentage if teams else 0
        
        for i, team in enumerate(teams[:6]):  # Show all 6 teams
            row = QHBoxLayout()
            row.setSpacing(4)
            
            rank = QLabel(f"{i+1}")
            rank.setFixedWidth(14)
            rank.setStyleSheet(f"font-size: 10px; font-weight: 700; color: {self.theme.accent_orange if i < 3 else self.theme.text_muted};")
            row.addWidget(rank)
            
            # Get first word from team name (split on capital letters or spaces)
            import re
            name_parts = re.split(r'_|\s', team.name)
            first_word = name_parts[0] if name_parts else team.name[:6]
            name = QLabel(first_word)
            name.setStyleSheet(f"font-size: 10px; color: {self.theme.text_primary};")
            row.addWidget(name)
            row.addStretch()
            
            # Record with draws: W-L-D
            record = QLabel(f"{team.wins}-{team.losses}-{team.draws}")
            record.setStyleSheet(f"font-size: 10px; color: {self.theme.text_secondary};")
            row.addWidget(record)
            
            # Winning percentage
            pct = QLabel(f".{int(team.winning_percentage * 1000):03d}")
            pct.setStyleSheet(f"font-size: 10px; font-weight: 600; color: {self.theme.text_primary};")
            row.addWidget(pct)
            
            container = QWidget()
            container.setLayout(row)
            if i % 2 == 0:
                container.setStyleSheet(f"background: {self.theme.bg_card_elevated};")
            self.rows_layout.addWidget(container)


class TeamColorBar(QWidget):
    """Team color indicator bar"""
    def __init__(self, team, height=80, width=8, parent=None):
        super().__init__(parent)
        self.team = team
        self.setFixedSize(width, height)
        self.theme = get_theme()
        
        # NPB Color Map (Consistent with SchedulePage)
        npb_colors = {
            "Tokyo Bravers": "#002569", # Chunichi Blue
            "Nagoya Sparks": "#F97709", # Giants Orange
            "Chiba Mariners": "#0055A5", # DeNA Blue
            "Sapporo Fighters": "#F6C900", # Tigers Yellow
            "Osaka Thunders": "#FF0000", # Carp Red
            "Hiroshima Phoenix": "#072C58", # Yakult Navy
            "Fukuoka Phoenix": "#F9C304", # Softbank Yellow
            "Sendai Flames": "#860010", # Rakuten Crimson
            "Yokohama Mariners": "#006298", # Nippon-Ham Blue/Gold
            "Saitama Bears": "#1F366A", # Seibu Blue
            "Kobe Buffaloes": "#000019", # Orix Navy
            "Shinjuku Spirits": "#333333", # Lotte Black
        }
        
        color = getattr(team, 'color', None)
        if not color:
            color = npb_colors.get(getattr(team, 'name', ''), self.theme.primary)
            
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
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(1)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 9px; color: {self.theme.text_muted}; letter-spacing: 1px; font-weight: 600;")
        layout.addWidget(lbl)

        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {self._color};")
        layout.addWidget(self._value_label)

        self._sub_label = QLabel(sub)
        self._sub_label.setStyleSheet(f"font-size: 9px; color: {self.theme.text_muted};")
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
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)

        header = QLabel("NEXT GAME")
        header.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted}; letter-spacing: 2px; font-weight: 600;")
        layout.addWidget(header)

        self.matchup_layout = QHBoxLayout()
        self.matchup_layout.setSpacing(12)

        self.away_label = QLabel("---")
        self.away_label.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {self.theme.text_primary};")
        self.away_label.setAlignment(Qt.AlignCenter)

        vs_label = QLabel("@")
        vs_label.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted};")
        vs_label.setAlignment(Qt.AlignCenter)

        self.home_label = QLabel("---")
        self.home_label.setStyleSheet(f"font-size: 13px; font-weight: 700; color: {self.theme.text_primary};")
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
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(4)

        header = QLabel("RECENT RESULTS")
        header.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted}; letter-spacing: 2px; font-weight: 600;")
        layout.addWidget(header)

        self.results_layout = QHBoxLayout()
        self.results_layout.setSpacing(4)
        self.result_labels = []

        for i in range(10):
            lbl = QLabel("-")
            lbl.setFixedSize(18, 18)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"""
                font-size: 9px;
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
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        header = QLabel(title)
        header.setStyleSheet(f"font-size: 9px; color: {self.theme.text_muted}; letter-spacing: 1px; font-weight: 600;")
        layout.addWidget(header)

        self.entries_layout = QVBoxLayout()
        self.entries_layout.setSpacing(2)
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


class InjuriesCard(QFrame):
    """Current injuries card with internal scroll"""
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
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        header = QLabel("INJURIES")
        header.setStyleSheet(f"font-size: 9px; color: {self.theme.text_muted}; letter-spacing: 2px; font-weight: 600;")
        layout.addWidget(header)

        # Scroll area for entries
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.entries_widget = QWidget()
        self.entries_layout = QVBoxLayout(self.entries_widget)
        self.entries_layout.setContentsMargins(0, 0, 0, 0)
        self.entries_layout.setSpacing(1)
        self.entries_layout.addStretch()
        
        scroll.setWidget(self.entries_widget)
        layout.addWidget(scroll, stretch=1)

    def set_injuries(self, injuries: list):
        """Set injuries list [(player_name, position, days_left), ...]"""
        while self.entries_layout.count() > 1:
            item = self.entries_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not injuries:
            no_injury = QLabel("故障者なし")
            no_injury.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted}; font-style: italic;")
            self.entries_layout.insertWidget(0, no_injury)
            return

        for name, pos, days in injuries:
            row = QHBoxLayout()
            row.setSpacing(4)

            pos_lbl = QLabel(pos)
            pos_lbl.setStyleSheet(f"font-size: 9px; color: {self.theme.text_muted}; min-width: 16px;")
            row.addWidget(pos_lbl)

            name_lbl = QLabel(name[:8])
            name_lbl.setStyleSheet(f"font-size: 10px; color: {self.theme.text_primary};")
            row.addWidget(name_lbl)
            row.addStretch()

            days_lbl = QLabel(f"{days}日")
            days_lbl.setStyleSheet(f"font-size: 9px; font-weight: 600; color: {self.theme.danger};")
            row.addWidget(days_lbl)

            container = QWidget()
            container.setLayout(row)
            self.entries_layout.insertWidget(self.entries_layout.count() - 1, container)


class NewsCard(QFrame):
    """Recent news card with clean modern design"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()

        self.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
                border-radius: 4px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        header = QLabel("NEWS")
        header.setStyleSheet(f"""
            font-size: 11px; 
            color: {self.theme.text_muted}; 
            letter-spacing: 3px; 
            font-weight: 700;
            padding-bottom: 4px;
            border-bottom: 1px solid {self.theme.border};
        """)
        layout.addWidget(header)

        # Scroll area for entries
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.entries_widget = QWidget()
        self.entries_layout = QVBoxLayout(self.entries_widget)
        self.entries_layout.setContentsMargins(0, 4, 0, 0)
        self.entries_layout.setSpacing(6)
        self.entries_layout.addStretch()
        
        scroll.setWidget(self.entries_widget)
        layout.addWidget(scroll, stretch=1)

    def set_news(self, news_items: list):
        """Set news list [(date, headline, type), ...]"""
        while self.entries_layout.count() > 1:
            item = self.entries_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not news_items:
            no_news = QLabel("ニュースはありません")
            no_news.setStyleSheet(f"font-size: 13px; color: {self.theme.text_muted}; font-style: italic; padding: 8px 0;")
            self.entries_layout.insertWidget(0, no_news)
            return

        # Color map for news types
        type_colors = {
            "trade": self.theme.accent_blue,
            "sign": "#4CAF50",  # Green
            "record": "#FFD700",  # Gold
            "injury": self.theme.danger,
            "game": self.theme.primary
        }

        for date, headline, news_type in news_items:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.setContentsMargins(0, 2, 0, 2)

            # Colored indicator dot
            dot_color = type_colors.get(news_type, self.theme.text_muted)
            dot = QLabel("●")
            dot.setFixedWidth(16)
            dot.setStyleSheet(f"font-size: 8px; color: {dot_color};")
            row.addWidget(dot)

            # Headline text - larger, clearer, with word wrap
            headline_lbl = QLabel(headline)
            headline_lbl.setStyleSheet(f"""
                font-size: 13px; 
                color: {self.theme.text_primary};
            """)
            headline_lbl.setWordWrap(True)
            row.addWidget(headline_lbl, stretch=1)

            container = QWidget()
            container.setLayout(row)
            self.entries_layout.insertWidget(self.entries_layout.count() - 1, container)


class HomePage(ContentPanel):
    """Home page with high-density industrial dashboard"""

    game_requested = Signal()
    view_roster_requested = Signal()
    player_detail_requested = Signal(object)  # Required by MainWindow

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self._create_ui()

    def _create_ui(self):
        """Create the dashboard layout"""
        # Header section
        self._create_header()

        # Main grid layout
        main_grid = QGridLayout()
        main_grid.setSpacing(4)
        main_grid.setContentsMargins(8, 4, 8, 8)

        # Row 0: Stats cards (4 columns)
        self._create_stats_row(main_grid, 0)

        # Row 1: Matchup + Results
        self._create_info_row(main_grid, 1)

        # Row 2: Leaders (left, col 0-1)
        self._create_leaders_widget(main_grid, 2, 0)

        # Row 3: Injuries (left, col 0-1)
        self.injuries_card = InjuriesCard()
        main_grid.addWidget(self.injuries_card, 3, 0, 1, 2)

        # Row 2-3: News + Standings (right, col 2-3, rowspan 2)
        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(4)
        
        self.news_card = NewsCard()
        right_layout.addWidget(self.news_card, stretch=2)
        
        self.standings_card = CompactStandingsCard()
        right_layout.addWidget(self.standings_card, stretch=1)
        
        main_grid.addWidget(right_widget, 2, 2, 2, 2)  # rowspan=2

        # Set row stretches - rows 2 and 3 expand
        main_grid.setRowStretch(0, 0)
        main_grid.setRowStretch(1, 0)
        main_grid.setRowStretch(2, 1)
        main_grid.setRowStretch(3, 1)

        self.add_layout(main_grid)

    def showEvent(self, event):
        """画面表示時にデータを更新"""
        super().showEvent(event)
        # 確実に最新データを反映させるため少し遅延してset_game_stateを呼ぶ
        if self.game_state:
            QTimer.singleShot(0, lambda: self.set_game_state(self.game_state))

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
        
        # Color Bar Container (Inserted before info_layout)
        self.color_bar_container = QWidget()
        self.color_bar_layout = QVBoxLayout(self.color_bar_container)
        self.color_bar_layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.color_bar_container)
        
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
        
        # Debug: Skip to Offseason button
        self.debug_skip_btn = QPushButton("⚡ SKIP TO OFFSEASON")
        self.debug_skip_btn.setCursor(Qt.PointingHandCursor)
        self.debug_skip_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.accent_orange};
                color: white;
                border: none;
                border-radius: 0px;
                padding: 14px 20px;
                font-size: 11px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: {self.theme.accent_orange_hover};
            }}
        """)
        self.debug_skip_btn.clicked.connect(self._on_debug_skip_to_offseason)
        btn_layout.addWidget(self.debug_skip_btn)

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

    def _create_leaders_widget(self, grid: QGridLayout, row: int, col: int):
        """Create leaders widget for grid placement"""
        leaders_frame = QFrame()
        leaders_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
                border-radius: 0px;
            }}
        """)
        leaders_layout = QVBoxLayout(leaders_frame)
        leaders_layout.setContentsMargins(8, 6, 8, 6)
        leaders_layout.setSpacing(4)

        leaders_header = QLabel("TEAM LEADERS")
        leaders_header.setStyleSheet(f"font-size: 9px; color: {self.theme.text_muted}; letter-spacing: 2px; font-weight: 600;")
        leaders_layout.addWidget(leaders_header)

        leaders_grid = QGridLayout()
        leaders_grid.setSpacing(4)

        self.avg_leaders = LeaderCard("AVG")
        leaders_grid.addWidget(self.avg_leaders, 0, 0)

        self.hr_leaders = LeaderCard("HR")
        leaders_grid.addWidget(self.hr_leaders, 0, 1)

        self.era_leaders = LeaderCard("ERA")
        leaders_grid.addWidget(self.era_leaders, 1, 0)

        self.wins_leaders = LeaderCard("W")
        leaders_grid.addWidget(self.wins_leaders, 1, 1)

        leaders_layout.addLayout(leaders_grid)
        grid.addWidget(leaders_frame, row, col, 1, 2)  # colspan=2

    def _create_leaders_panel(self, parent_layout):
        """Create leaders panel for layout (legacy)"""
        leaders_frame = QFrame()
        leaders_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: none;
                border-radius: 0px;
            }}
        """)
        leaders_layout = QVBoxLayout(leaders_frame)
        leaders_layout.setContentsMargins(12, 8, 12, 8)
        leaders_layout.setSpacing(6)

        leaders_header = QLabel("TEAM LEADERS")
        leaders_header.setStyleSheet(f"font-size: 9px; color: {self.theme.text_muted}; letter-spacing: 2px; font-weight: 600;")
        leaders_layout.addWidget(leaders_header)

        leaders_grid = QGridLayout()
        leaders_grid.setSpacing(4)

        self.avg_leaders = LeaderCard("AVG")
        leaders_grid.addWidget(self.avg_leaders, 0, 0)

        self.hr_leaders = LeaderCard("HR")
        leaders_grid.addWidget(self.hr_leaders, 0, 1)

        self.era_leaders = LeaderCard("ERA")
        leaders_grid.addWidget(self.era_leaders, 1, 0)

        self.wins_leaders = LeaderCard("W")
        leaders_grid.addWidget(self.wins_leaders, 1, 1)

        leaders_layout.addLayout(leaders_grid)
        parent_layout.addWidget(leaders_frame)

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

        # Standings (compact with league toggle)
        self.standings_card = CompactStandingsCard()
        grid.addWidget(self.standings_card, row, 2, 1, 2)

    def _create_extra_row(self, grid: QGridLayout, row: int):
        """Create injuries and news row"""
        # Injuries
        self.injuries_card = InjuriesCard()
        grid.addWidget(self.injuries_card, row, 0, 1, 2)

        # News
        self.news_card = NewsCard()
        grid.addWidget(self.news_card, row, 2, 1, 2)
    
    def _on_debug_skip_to_offseason(self):
        """デバッグ用: オフシーズンまでスキップ"""
        if not self.game_state:
            return
        
        from PySide6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self, "デバッグ: オフシーズンスキップ",
            "レギュラーシーズンとポストシーズンをスキップして\nオフシーズンを開始しますか？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 強制的にオフシーズンを開始
            self.game_state.start_offseason()
            
            # UIを更新
            self.set_game_state(self.game_state)
            
            QMessageBox.information(self, "オフシーズン開始", "オフシーズンを開始しました。\n「NEXT: 契約更改」ボタンを押してください。")

    def set_game_state(self, game_state):
        """Update page with game state"""
        self.game_state = game_state
        if not game_state:
            return

        team = game_state.player_team
        if not team:
            return

        # オフシーズンモード検出
        is_offseason = getattr(game_state, 'is_offseason', False)
        
        # オフシーズン時のUI変更
        if is_offseason:
            self._setup_offseason_mode(game_state, team)
            return

        # Header
        self.team_name_label.setText(team.name.upper())
        league_name = "North League" if getattr(team.league, 'value', None) == "North League" else ("South League" if getattr(team.league, 'value', None) == "South League" else (team.league.value if team.league else ""))
        date_str = getattr(game_state, 'current_date', '2027-03-29')
        self.season_label.setText(f"{game_state.current_year} SEASON  |  {league_name}  |  {date_str}")
        
        # Update Color Bar
        # Clear previous
        while self.color_bar_layout.count():
            item = self.color_bar_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        color_bar = TeamColorBar(team, height=50, width=6)
        self.color_bar_layout.addWidget(color_bar)

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

            # Standings - set both leagues
            north_teams = [t for t in game_state.teams 
                          if getattr(t.league, 'value', '').lower() == "north league" 
                          or getattr(t.league, 'name', '').upper() == "NORTH"]
            south_teams = [t for t in game_state.teams 
                          if getattr(t.league, 'value', '').lower() == "south league" 
                          or getattr(t.league, 'name', '').upper() == "SOUTH"]
            north_teams.sort(key=lambda t: t.winning_percentage, reverse=True)
            south_teams.sort(key=lambda t: t.winning_percentage, reverse=True)
            self.standings_card.set_standings(north_teams, south_teams)

        # Games progress
        games_played = team.wins + team.losses + team.draws
        progress = (games_played / 143) * 100
        self.games_card.set_value(f"{games_played}/143")
        self.games_card.set_sub(f"Progress: {progress:.0f}%")

        # Show game-related cards
        self.matchup_card.show()
        self.results_card.show()
        self.record_card.show()
        self.rank_card.show()
        self.games_card.show()
        self.streak_card.show()

        # Next game from schedule & Button Text Update
        game_status = self._update_next_game(game_state, team)
        
        # Update Button Text based on game availability
        if game_status == "watch":
            self.play_btn.setText("SIMULATE ALL-STAR GAMES")
            self.play_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {self.theme.accent_orange};
                    color: white;
                    border: none;
                    border-radius: 0px;
                    padding: 14px 28px;
                    font-size: 13px;
                    font-weight: 700;
                    letter-spacing: 1px;
                }}
                QPushButton:hover {{
                    background: #ff9800;
                }}
            """)
        elif game_status == "play":
            self.play_btn.setText("PLAY NEXT GAME")
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
        else:
            self.play_btn.setText("NEXT DAY")
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

        # Recent results
        self._update_recent_results(game_state, team)

        # Leaders
        self._update_leaders(team)

        # Injuries
        self._update_injuries(team)

        # News
        self._update_news(game_state)
    
    def _setup_offseason_mode(self, game_state, team):
        """オフシーズンモードのUI設定"""
        # Header更新
        self.team_name_label.setText(team.name.upper())
        phase_name = game_state.get_current_offseason_phase() if hasattr(game_state, 'get_current_offseason_phase') else "オフシーズン"
        date_str = getattr(game_state, 'current_date', '')
        self.season_label.setText(f"{game_state.current_year} OFFSEASON  |  {phase_name}  |  {date_str}")
        
        # Color Bar更新
        while self.color_bar_layout.count():
            item = self.color_bar_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        color_bar = TeamColorBar(team, height=50, width=6)
        self.color_bar_layout.addWidget(color_bar)
        
        # 試合関連カードを非表示
        self.matchup_card.hide()
        self.results_card.hide()
        
        # ボタンをオフシーズン用に変更
        self.play_btn.setText(f"NEXT: {phase_name}")
        self.play_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.accent_blue};
                color: white;
                border: none;
                border-radius: 0px;
                padding: 14px 28px;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: #5c9ce6;
            }}
        """)
        
        # ニュースを更新
        self._update_news(game_state)

    def _update_next_game(self, game_state, team):
        """Update next game display and return status ('play', 'watch', 'none')"""
        today_str = getattr(game_state, 'current_date', '')
        
        # 1. Check for All-Star Game TODAY
        if hasattr(game_state, 'schedule'):
            for g in game_state.schedule.games:
                if g.date == today_str and ("ALL-" in g.home_team_name or "ALL-" in g.away_team_name):
                    self.matchup_card.set_matchup(g.home_team_name, g.away_team_name, today_str, "(AI Broadcast)")
                    return "watch"

        # 2. Regular Next Game Logic
        next_game = game_state.get_next_game() if hasattr(game_state, 'get_next_game') else None
        
        has_game_today = False
        
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
            
        return "play" if has_game_today else "none"

    def _update_recent_results(self, game_state, team):
        """Update recent results display"""
        results = []
        if hasattr(game_state, 'get_recent_results'):
            results = game_state.get_recent_results(team.name, 10)
        self.results_card.set_results(results)

    def _update_leaders(self, team):
        """Update team leaders"""
        # ★修正: 最新の成績 (p.record) を使用してリーダーボードを更新
        # 以前の実装では古いデータを参照している可能性があったため、ここで再取得
        
        # ロースターに含まれる全選手（一軍・二軍問わず、あるいは一軍のみにするかは要件次第だが、
        # ここではチーム全体のリーダーを表示するため全選手から抽出）
        # ただし育成選手は除外
        batters = [p for p in team.players if p.position.value != "投手" and not p.is_developmental]
        pitchers = [p for p in team.players if p.position.value == "投手" and not p.is_developmental]

        # Games Played
        team_games = team.wins + team.losses + team.draws
        if team_games == 0: team_games = 1 # Avoid division by zero start of season

        # Batting average (Qualify: PA >= 3.1 * Team Games)
        qualified_batters = [p for p in batters if p.record.plate_appearances >= team_games * 3.1]
        # If no one qualifies (early season), maybe show top by PA? Or just allow all.
        # Strict regulation implies showing nothing or strict.
        # Fallback to top 3 by PA if qualified < 3? No, keep strict.
        
        target_batters = qualified_batters if qualified_batters else batters
        batters_sorted = sorted(target_batters, key=lambda p: p.record.batting_average, reverse=True)
        
        self.avg_leaders.set_leaders([
            (p.name, f".{int(p.record.batting_average * 1000):03d}" if p.record.at_bats > 0 else ".---")
            for p in batters_sorted[:3]
        ])

        # Home runs
        hr_sorted = sorted(batters, key=lambda p: p.record.home_runs, reverse=True)
        self.hr_leaders.set_leaders([
            (p.name, p.record.home_runs) for p in hr_sorted[:3]
        ])

        # ERA (Qualify: IP >= Team Games)
        qualified_pitchers = [p for p in pitchers if p.record.innings_pitched >= team_games * 1.0]
        target_pitchers = qualified_pitchers if qualified_pitchers else [p for p in pitchers if p.record.innings_pitched > 0]
        
        pitchers_sorted_era = sorted(target_pitchers, key=lambda p: p.record.era)
        
        self.era_leaders.set_leaders([
            (p.name, f"{p.record.era:.2f}")
            for p in pitchers_sorted_era[:3]
        ])

        # Wins
        wins_sorted = sorted(pitchers, key=lambda p: p.record.wins, reverse=True)
        self.wins_leaders.set_leaders([
            (p.name, p.record.wins) for p in wins_sorted[:3]
        ])

    def _update_injuries(self, team):
        """Update injuries display"""
        injured = [(p.name, "P" if p.position.value == "投手" else p.position.value[0], 
                    getattr(p, 'injury_days', 0)) 
                   for p in team.players if getattr(p, 'is_injured', False)]
        self.injuries_card.set_injuries(injured)

    def _update_news(self, game_state):
        """Update news display with game highlights"""
        news_items = []
        
        # Calculate 5-day cutoff date for non-game news expiry
        from datetime import datetime, timedelta
        current_date = game_state.current_date if hasattr(game_state, 'current_date') else None
        cutoff_date = None
        if current_date:
            try:
                current_dt = datetime.strptime(current_date, "%Y-%m-%d")
                cutoff_dt = current_dt - timedelta(days=5)
                cutoff_date = cutoff_dt.strftime("%Y-%m-%d")
            except:
                pass
        
        # Get news from game_state.news_feed (injuries, trades, etc.)
        if hasattr(game_state, 'news_feed') and game_state.news_feed:
            for n in game_state.news_feed[:20]:  # Check more items but filter by date
                if isinstance(n, dict):
                    date = n.get('date', '')
                    message = n.get('message', '')
                    category = n.get('category', '')
                    
                    # Filter out news older than 5 days
                    if cutoff_date and date < cutoff_date:
                        continue
                    
                    # Determine news type based on category
                    if category == '怪我':
                        news_type = 'injury'
                    elif 'トレード' in category:
                        news_type = 'trade'
                    else:
                        news_type = 'general'
                    news_items.append((date, message, news_type))

        
        # Get news from game_state (legacy methods)
        elif hasattr(game_state, 'get_recent_news'):
            raw_news = game_state.get_recent_news(limit=5)
            for n in raw_news:
                date = n.get('date', '')
                headline = n.get('headline', n.get('title', ''))
                news_type = n.get('type', 'general')
                news_items.append((date, headline, news_type))
        elif hasattr(game_state, 'news_log'):
            for n in game_state.news_log[:5]:
                date = n.get('date', '')
                headline = n.get('headline', n.get('title', ''))
                news_type = n.get('type', 'general')
                news_items.append((date, headline, news_type))

        
        # Add game highlights from recent games
        if hasattr(game_state, 'schedule') and game_state.schedule:
            recent_games = []
            for game in game_state.schedule.games:
                if hasattr(game, 'status') and str(game.status) == "GameStatus.COMPLETED":
                    recent_games.append(game)
            
            # Get last 5 completed games for highlights
            for game in recent_games[-5:]:
                # Check for notable performances
                highlights = getattr(game, 'highlights', [])
                if highlights:
                    for h in highlights[:2]:  # Max 2 per game
                        # Handle both dict format and string format
                        if isinstance(h, dict):
                            headline = h.get('message', '')
                        else:
                            headline = str(h)
                        if headline:
                            news_items.insert(0, (game.date, headline, "game"))
                elif hasattr(game, 'mvp_name') and game.mvp_name:
                    headline = f"{game.mvp_name}が活躍! {game.away_team_name} vs {game.home_team_name}"
                    news_items.insert(0, (game.date, headline, "game"))
        
        self.news_card.set_news(news_items[:10])  # Show up to 10 items