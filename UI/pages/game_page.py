# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Game Page
OOTP-Style Premium Live Game Simulation
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout, QProgressBar,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QColor

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.cards import Card
from UI.widgets.panels import ContentPanel, InfoPanel
from UI.widgets.buttons import SimButton, SpeedControl


class PremiumCard(QFrame):
    """Premium styled card for game sections"""

    def __init__(self, title: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._title = title
        self._icon = icon

        self._setup_ui()
        self._add_shadow()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated},
                    stop:0.5 {self.theme.bg_card},
                    stop:1 {self.theme.bg_card_elevated});
                border: 1px solid {self.theme.border};
                border-radius: 16px;
            }}
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(16)

        # Header with gradient accent
        if self._title:
            header = QFrame()
            header.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {self.theme.primary}, stop:1 {self.theme.primary_light});
                    border-radius: 10px;
                    border: none;
                }}
            """)
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(16, 12, 16, 12)

            title_text = f"{self._icon}  {self._title}" if self._icon else self._title
            title_label = QLabel(title_text)
            title_label.setStyleSheet(f"""
                font-size: 15px;
                font-weight: 700;
                color: white;
                background: transparent;
                border: none;
            """)
            header_layout.addWidget(title_label)
            header_layout.addStretch()

            self.main_layout.addWidget(header)

        # Content area
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(12)
        self.main_layout.addLayout(self.content_layout)

    def _add_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)

    def add_widget(self, widget: QWidget):
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        self.content_layout.addLayout(layout)


class GamePage(QWidget):
    """Premium live game simulation page"""

    game_finished = Signal(object)  # Emits game result

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.simulator = None
        self.is_simulating = False
        self.sim_speed = 1

        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        """Create the premium game page layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Page header
        header = self._create_page_header()
        layout.addWidget(header)

        # Scoreboard
        self.scoreboard = self._create_scoreboard()
        layout.addWidget(self.scoreboard)

        # Main content
        content = QHBoxLayout()
        content.setSpacing(20)

        # Left - Play by play
        left_panel = self._create_play_by_play_panel()
        content.addWidget(left_panel, stretch=2)

        # Right - Game info and controls
        right_panel = self._create_game_info_panel()
        content.addWidget(right_panel, stretch=1)

        layout.addLayout(content)

    def _create_page_header(self) -> QWidget:
        """Create premium page header"""
        header_frame = QFrame()
        header_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.bg_card}, stop:1 {self.theme.bg_card_elevated});
                border: 1px solid {self.theme.border};
                border-radius: 16px;
            }}
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(24, 16, 24, 16)

        # Title
        title_layout = QVBoxLayout()
        title = QLabel("LIVE GAME")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 700;
            color: {self.theme.text_primary};
            letter-spacing: 2px;
        """)
        subtitle = QLabel("リアルタイム試合シミュレーション")
        subtitle.setStyleSheet(f"""
            font-size: 13px;
            color: {self.theme.text_secondary};
        """)
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        # Add shadow
        shadow = QGraphicsDropShadowEffect(header_frame)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow)

        return header_frame

    def _create_scoreboard(self) -> QWidget:
        """Create the premium scoreboard widget"""
        scoreboard = QFrame()
        scoreboard.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated},
                    stop:0.5 {self.theme.bg_card},
                    stop:1 {self.theme.bg_card_elevated});
                border: 1px solid {self.theme.border};
                border-radius: 16px;
            }}
        """)

        # Add shadow
        shadow = QGraphicsDropShadowEffect(scoreboard)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 6)
        scoreboard.setGraphicsEffect(shadow)

        layout = QVBoxLayout(scoreboard)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)

        # Main score display
        score_layout = QHBoxLayout()
        score_layout.setSpacing(60)

        # Away team
        away_layout = QVBoxLayout()
        away_layout.setAlignment(Qt.AlignCenter)

        self.away_name = QLabel("AWAY")
        self.away_name.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {self.theme.text_secondary};
            letter-spacing: 2px;
        """)
        self.away_name.setAlignment(Qt.AlignCenter)

        self.away_score = QLabel("0")
        self.away_score.setStyleSheet(f"""
            font-size: 72px;
            font-weight: 800;
            color: {self.theme.text_primary};
        """)
        self.away_score.setAlignment(Qt.AlignCenter)

        away_layout.addWidget(self.away_name)
        away_layout.addWidget(self.away_score)

        score_layout.addLayout(away_layout)

        # VS with decorative element
        vs_container = QVBoxLayout()
        vs_container.setAlignment(Qt.AlignCenter)

        vs_label = QLabel("VS")
        vs_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 300;
            color: {self.theme.primary};
            letter-spacing: 4px;
        """)
        vs_label.setAlignment(Qt.AlignCenter)
        vs_container.addWidget(vs_label)

        score_layout.addLayout(vs_container)

        # Home team
        home_layout = QVBoxLayout()
        home_layout.setAlignment(Qt.AlignCenter)

        self.home_name = QLabel("HOME")
        self.home_name.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {self.theme.text_secondary};
            letter-spacing: 2px;
        """)
        self.home_name.setAlignment(Qt.AlignCenter)

        self.home_score = QLabel("0")
        self.home_score.setStyleSheet(f"""
            font-size: 72px;
            font-weight: 800;
            color: {self.theme.text_primary};
        """)
        self.home_score.setAlignment(Qt.AlignCenter)

        home_layout.addWidget(self.home_name)
        home_layout.addWidget(self.home_score)

        score_layout.addLayout(home_layout)

        layout.addLayout(score_layout)

        # Inning info with premium badge style
        inning_layout = QHBoxLayout()
        inning_layout.setAlignment(Qt.AlignCenter)
        inning_layout.setSpacing(16)

        self.inning_label = QLabel("1回表")
        self.inning_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: white;
            padding: 10px 28px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {self.theme.primary_light}, stop:1 {self.theme.primary});
            border-radius: 20px;
        """)

        self.count_label = QLabel("0アウト")
        self.count_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {self.theme.text_secondary};
            padding: 10px 20px;
            background: {self.theme.bg_input};
            border-radius: 20px;
        """)

        inning_layout.addWidget(self.inning_label)
        inning_layout.addWidget(self.count_label)

        layout.addLayout(inning_layout)

        # Inning-by-inning scores
        self.inning_scores = self._create_inning_scores()
        layout.addWidget(self.inning_scores)

        return scoreboard

    def _create_inning_scores(self) -> QWidget:
        """Create premium inning-by-inning score display"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        # Headers
        headers = ["", "1", "2", "3", "4", "5", "6", "7", "8", "9", "R", "H", "E"]
        self.score_labels = {}

        for i, h in enumerate(headers):
            col = QVBoxLayout()
            col.setSpacing(4)

            # Header
            header = QLabel(h)
            header.setFixedWidth(36 if i == 0 else 28)
            header.setAlignment(Qt.AlignCenter)
            header.setStyleSheet(f"""
                font-size: 11px;
                font-weight: 700;
                color: {self.theme.text_muted};
                letter-spacing: 1px;
            """)
            col.addWidget(header)

            # Away row
            away_cell = QLabel("-" if i > 0 else "")
            away_cell.setFixedWidth(36 if i == 0 else 28)
            away_cell.setFixedHeight(28)
            away_cell.setAlignment(Qt.AlignCenter)
            away_cell.setStyleSheet(f"""
                font-size: 13px;
                font-weight: 600;
                color: {self.theme.text_primary};
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated}, stop:1 {self.theme.bg_input});
                border-radius: 4px;
            """)
            col.addWidget(away_cell)
            self.score_labels[f"away_{i}"] = away_cell

            # Home row
            home_cell = QLabel("-" if i > 0 else "")
            home_cell.setFixedWidth(36 if i == 0 else 28)
            home_cell.setFixedHeight(28)
            home_cell.setAlignment(Qt.AlignCenter)
            home_cell.setStyleSheet(f"""
                font-size: 13px;
                font-weight: 600;
                color: {self.theme.text_primary};
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated}, stop:1 {self.theme.bg_input});
                border-radius: 4px;
            """)
            col.addWidget(home_cell)
            self.score_labels[f"home_{i}"] = home_cell

            layout.addLayout(col)

        return widget

    def _create_play_by_play_panel(self) -> QWidget:
        """Create premium play-by-play log panel"""
        panel = PremiumCard("PLAY BY PLAY", "")

        # Play log scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)
        scroll.setMinimumHeight(300)

        self.log_container = QWidget()
        self.log_layout = QVBoxLayout(self.log_container)
        self.log_layout.setAlignment(Qt.AlignTop)
        self.log_layout.setSpacing(8)

        scroll.setWidget(self.log_container)
        panel.add_widget(scroll)

        return panel

    def _create_game_info_panel(self) -> QWidget:
        """Create premium game info and control panel"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # Simulation controls
        controls_card = PremiumCard("SIMULATION", "")

        controls_layout = QHBoxLayout()
        controls_layout.setAlignment(Qt.AlignCenter)
        controls_layout.setSpacing(16)

        self.play_btn = SimButton("play")
        self.play_btn.clicked.connect(self._toggle_simulation)
        controls_layout.addWidget(self.play_btn)

        self.step_btn = SimButton("step")
        self.step_btn.clicked.connect(self._step_simulation)
        controls_layout.addWidget(self.step_btn)

        controls_card.add_layout(controls_layout)

        # Speed control
        self.speed_control = SpeedControl()
        self.speed_control.speed_changed.connect(self._on_speed_changed)
        controls_card.add_widget(self.speed_control)

        layout.addWidget(controls_card)

        # Current matchup
        matchup_card = PremiumCard("MATCHUP", "")

        self.batter_label = QLabel("打者: -")
        self.batter_label.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 600;
            color: {self.theme.text_primary};
            padding: 8px;
            background: {self.theme.bg_input};
            border-radius: 8px;
        """)

        self.pitcher_label = QLabel("投手: -")
        self.pitcher_label.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 600;
            color: {self.theme.text_primary};
            padding: 8px;
            background: {self.theme.bg_input};
            border-radius: 8px;
        """)

        matchup_card.add_widget(self.batter_label)
        matchup_card.add_widget(self.pitcher_label)

        layout.addWidget(matchup_card)

        # Runners on base
        base_card = PremiumCard("RUNNERS", "")
        self.base_display = self._create_base_display()
        base_card.add_widget(self.base_display)
        layout.addWidget(base_card)

        # Pitcher stats
        pitcher_card = PremiumCard("PITCHER STATS", "")

        # Create stat rows
        stats_layout = QVBoxLayout()
        stats_layout.setSpacing(8)

        self.pitch_count_label = self._create_stat_row("投球数", "0")
        self.hits_allowed_label = self._create_stat_row("被安打", "0")
        self.runs_allowed_label = self._create_stat_row("失点", "0")

        stats_layout.addWidget(self.pitch_count_label)
        stats_layout.addWidget(self.hits_allowed_label)
        stats_layout.addWidget(self.runs_allowed_label)

        pitcher_card.add_layout(stats_layout)
        layout.addWidget(pitcher_card)

        layout.addStretch()

        return panel

    def _create_stat_row(self, label: str, value: str) -> QWidget:
        """Create a premium stat row"""
        row = QFrame()
        row.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_input};
                border-radius: 8px;
                padding: 4px;
            }}
        """)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(12, 8, 12, 8)

        label_widget = QLabel(label)
        label_widget.setStyleSheet(f"""
            font-size: 13px;
            color: {self.theme.text_secondary};
            font-weight: 500;
        """)

        value_widget = QLabel(value)
        value_widget.setObjectName("value")
        value_widget.setStyleSheet(f"""
            font-size: 15px;
            font-weight: 700;
            color: {self.theme.text_primary};
        """)

        row_layout.addWidget(label_widget)
        row_layout.addStretch()
        row_layout.addWidget(value_widget)

        return row

    def _create_base_display(self) -> QWidget:
        """Create premium baseball diamond base display"""
        widget = QWidget()
        widget.setFixedSize(140, 120)

        layout = QGridLayout(widget)
        layout.setSpacing(8)

        # Base indicators with premium styling
        self.base_labels = {}

        base_style_empty = f"""
            font-size: 28px;
            color: {self.theme.border_light};
        """
        base_style_occupied = f"""
            font-size: 28px;
            color: {self.theme.warning};
        """

        # Second base (top)
        second = QLabel("◇")
        second.setAlignment(Qt.AlignCenter)
        second.setStyleSheet(base_style_empty)
        layout.addWidget(second, 0, 1)
        self.base_labels[1] = second

        # Third base (left)
        third = QLabel("◇")
        third.setAlignment(Qt.AlignCenter)
        third.setStyleSheet(base_style_empty)
        layout.addWidget(third, 1, 0)
        self.base_labels[2] = third

        # First base (right)
        first = QLabel("◇")
        first.setAlignment(Qt.AlignCenter)
        first.setStyleSheet(base_style_empty)
        layout.addWidget(first, 1, 2)
        self.base_labels[0] = first

        # Home (bottom)
        home = QLabel("⬠")
        home.setAlignment(Qt.AlignCenter)
        home.setStyleSheet(f"font-size: 28px; color: {self.theme.primary};")
        layout.addWidget(home, 2, 1)

        return widget

    def _setup_timer(self):
        """Set up simulation timer"""
        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self._simulate_step)

    def set_game_state(self, game_state):
        """Update with game state"""
        self.game_state = game_state

    def start_game(self, home_team, away_team):
        """Start a new game simulation"""
        from game_simulator import GameSimulator

        # Create simulator
        self.simulator = GameSimulator(home_team, away_team, fast_mode=False)

        # Update display
        self.home_name.setText(home_team.name)
        self.away_name.setText(away_team.name)
        self.home_score.setText("0")
        self.away_score.setText("0")
        self.inning_label.setText("1回表")
        self.count_label.setText("0アウト")

        # Update team labels
        self.score_labels["away_0"].setText(away_team.name[:3])
        self.score_labels["home_0"].setText(home_team.name[:3])

        # Clear log
        while self.log_layout.count():
            item = self.log_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._add_log_entry(f"{away_team.name} vs {home_team.name}", is_highlight=True)

    def _toggle_simulation(self):
        """Toggle simulation play/pause"""
        if self.is_simulating:
            self._pause_simulation()
        else:
            self._start_simulation()

    def _start_simulation(self):
        """Start auto simulation"""
        self.is_simulating = True
        self.play_btn.set_active(True)
        self.play_btn.set_mode("pause")

        # Start timer based on speed
        interval = 1000 // self.sim_speed
        self.sim_timer.start(interval)

    def _pause_simulation(self):
        """Pause simulation"""
        self.is_simulating = False
        self.play_btn.set_active(False)
        self.play_btn.set_mode("play")
        self.sim_timer.stop()

    def _step_simulation(self):
        """Run one step of simulation"""
        if not self.simulator:
            return

        self._simulate_step()

    def _simulate_step(self):
        """Execute one simulation step"""
        if not self.simulator:
            return

        # For now, run the full game (to be broken into steps later)
        if not hasattr(self.simulator, '_game_started'):
            self.simulator._game_started = True
            home_score, away_score = self.simulator.simulate_game()

            # Update display
            self.home_score.setText(str(home_score))
            self.away_score.setText(str(away_score))

            # Add log entries
            for log_line in self.simulator.log[-10:]:
                self._add_log_entry(log_line)

            # Update inning scores
            for i, score in enumerate(self.simulator.inning_scores_away[:9]):
                self.score_labels[f"away_{i+1}"].setText(str(score))
            for i, score in enumerate(self.simulator.inning_scores_home[:9]):
                if isinstance(score, int):
                    self.score_labels[f"home_{i+1}"].setText(str(score))
                else:
                    self.score_labels[f"home_{i+1}"].setText(str(score))

            # Final totals
            self.score_labels["away_10"].setText(str(away_score))
            self.score_labels["home_10"].setText(str(home_score))

            self._pause_simulation()

            # Emit finished
            self.game_finished.emit({
                'home_score': home_score,
                'away_score': away_score,
                'home_team': self.simulator.home_team,
                'away_team': self.simulator.away_team
            })

    def _add_log_entry(self, text: str, is_highlight: bool = False):
        """Add a premium log entry to the play-by-play"""
        label = QLabel(text)
        label.setWordWrap(True)

        if is_highlight:
            label.setStyleSheet(f"""
                padding: 12px 16px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.primary}, stop:1 {self.theme.primary_light});
                border-radius: 8px;
                font-size: 14px;
                font-weight: 600;
                color: white;
            """)
        else:
            label.setStyleSheet(f"""
                padding: 10px 14px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated}, stop:1 {self.theme.bg_input});
                border-radius: 8px;
                font-size: 13px;
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border_muted};
            """)
        self.log_layout.addWidget(label)

    def _on_speed_changed(self, speed: int):
        """Handle speed change"""
        self.sim_speed = speed
        if self.is_simulating:
            interval = 1000 // speed
            self.sim_timer.setInterval(interval)

    def _update_bases(self, runners: list):
        """Update base display"""
        for i, has_runner in enumerate(runners[:3]):
            if has_runner:
                self.base_labels[i].setText("◆")
                self.base_labels[i].setStyleSheet(f"font-size: 28px; color: {self.theme.warning};")
            else:
                self.base_labels[i].setText("◇")
                self.base_labels[i].setStyleSheet(f"font-size: 28px; color: {self.theme.border_light};")
