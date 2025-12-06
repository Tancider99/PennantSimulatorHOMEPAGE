# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Schedule Page
OOTP-Style Premium Game Schedule and Results
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCalendarWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QComboBox, QFrame, QGraphicsDropShadowEffect, QScrollArea
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor, QBrush, QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme


class PremiumCard(QFrame):
    """Premium styled card with gradient background and shadow"""

    def __init__(self, title: str, icon: str = "", parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.title_text = title
        self.icon = icon

        self._setup_ui()

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

        # Shadow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 16)
        self.main_layout.setSpacing(0)

        # Header with gradient accent
        header = QFrame()
        header.setFixedHeight(48)
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.primary},
                    stop:1 {self.theme.accent});
                border: none;
                border-radius: 16px 16px 0 0;
            }}
        """)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        title_label = QLabel(f"{self.icon}  {self.title_text}" if self.icon else self.title_text)
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
        self.content_widget = QWidget()
        self.content_widget.setStyleSheet("background: transparent; border: none;")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(16, 16, 16, 0)
        self.content_layout.setSpacing(12)

        self.main_layout.addWidget(self.content_widget)

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        self.content_layout.addLayout(layout)


class SchedulePage(QWidget):
    """Premium styled game schedule and results page"""

    game_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None

        self._setup_ui()

    def _setup_ui(self):
        """Create the schedule page layout"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(20)

        # Premium page header
        header_frame = QFrame()
        header_frame.setFixedHeight(80)
        header_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.bg_card},
                    stop:0.5 {self.theme.bg_card_elevated},
                    stop:1 {self.theme.bg_card});
                border: 1px solid {self.theme.border};
                border-radius: 16px;
            }}
        """)

        header_shadow = QGraphicsDropShadowEffect(header_frame)
        header_shadow.setBlurRadius(15)
        header_shadow.setOffset(0, 3)
        header_shadow.setColor(QColor(0, 0, 0, 60))
        header_frame.setGraphicsEffect(header_shadow)

        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(24, 0, 24, 0)

        # Title with icon
        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)

        title = QLabel("日程・試合結果")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 700;
            color: {self.theme.text_primary};
            background: transparent;
        """)
        title_layout.addWidget(title)

        subtitle = QLabel("Game Schedule & Results")
        subtitle.setStyleSheet(f"""
            font-size: 12px;
            color: {self.theme.text_muted};
            background: transparent;
        """)
        title_layout.addWidget(subtitle)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        # Month navigation
        nav_frame = QFrame()
        nav_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_input};
                border-radius: 8px;
                border: 1px solid {self.theme.border_muted};
            }}
        """)
        nav_layout = QHBoxLayout(nav_frame)
        nav_layout.setContentsMargins(8, 4, 8, 4)
        nav_layout.setSpacing(8)

        self.prev_month_btn = QPushButton("◀")
        self.prev_month_btn.setFixedSize(32, 32)
        self.prev_month_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.theme.text_primary};
                border: none;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {self.theme.bg_hover};
                border-radius: 4px;
            }}
        """)
        self.prev_month_btn.clicked.connect(self._prev_month)
        nav_layout.addWidget(self.prev_month_btn)

        self.month_label = QLabel("2024年4月")
        self.month_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {self.theme.text_primary};
            padding: 0 12px;
            background: transparent;
        """)
        nav_layout.addWidget(self.month_label)

        self.next_month_btn = QPushButton("▶")
        self.next_month_btn.setFixedSize(32, 32)
        self.next_month_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {self.theme.text_primary};
                border: none;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {self.theme.bg_hover};
                border-radius: 4px;
            }}
        """)
        self.next_month_btn.clicked.connect(self._next_month)
        nav_layout.addWidget(self.next_month_btn)

        header_layout.addWidget(nav_frame)
        main_layout.addWidget(header_frame)

        # Main content
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Left - Calendar and upcoming games
        left_panel = QVBoxLayout()
        left_panel.setSpacing(16)

        # Mini calendar
        calendar_card = PremiumCard("カレンダー", "")
        self.calendar = QCalendarWidget()
        self.calendar.setStyleSheet(f"""
            QCalendarWidget {{
                background-color: {self.theme.bg_card};
                border: none;
            }}
            QCalendarWidget QWidget {{
                alternate-background-color: {self.theme.bg_input};
                color: {self.theme.text_primary};
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                background-color: {self.theme.bg_card};
                color: {self.theme.text_primary};
                selection-background-color: {self.theme.primary};
                selection-color: white;
            }}
            QCalendarWidget QWidget#qt_calendar_navigationbar {{
                background-color: {self.theme.bg_card_elevated};
            }}
            QCalendarWidget QToolButton {{
                color: {self.theme.text_primary};
                background: transparent;
                border: none;
                padding: 4px;
            }}
            QCalendarWidget QToolButton:hover {{
                background: {self.theme.bg_hover};
                border-radius: 4px;
            }}
        """)
        self.calendar.clicked.connect(self._on_date_selected)
        calendar_card.add_widget(self.calendar)
        left_panel.addWidget(calendar_card)

        # Upcoming games
        upcoming_card = PremiumCard("今後の試合", "")
        self.upcoming_table = self._create_schedule_table(compact=True)
        upcoming_card.add_widget(self.upcoming_table)
        left_panel.addWidget(upcoming_card)

        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        content_layout.addWidget(left_widget, stretch=1)

        # Right - Full schedule/results
        right_panel = QVBoxLayout()
        right_panel.setSpacing(16)

        # Filter toolbar
        filter_frame = QFrame()
        filter_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: 1px solid {self.theme.border_muted};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(12, 8, 12, 8)

        filter_label = QLabel("表示:")
        filter_label.setStyleSheet(f"color: {self.theme.text_secondary}; background: transparent;")
        filter_layout.addWidget(filter_label)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全試合", "自チームのみ", "未消化のみ", "終了のみ"])
        self.filter_combo.setStyleSheet(f"""
            QComboBox {{
                background: {self.theme.bg_input};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 120px;
            }}
            QComboBox:hover {{
                border-color: {self.theme.primary};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background: {self.theme.bg_card};
                color: {self.theme.text_primary};
                selection-background-color: {self.theme.primary};
            }}
        """)
        self.filter_combo.currentIndexChanged.connect(self._filter_games)
        filter_layout.addWidget(self.filter_combo)

        filter_layout.addStretch()
        right_panel.addWidget(filter_frame)

        # Full schedule table
        schedule_card = PremiumCard("試合一覧", "")
        self.schedule_table = self._create_schedule_table()
        schedule_card.add_widget(self.schedule_table)
        right_panel.addWidget(schedule_card)

        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        content_layout.addWidget(right_widget, stretch=2)

        main_layout.addLayout(content_layout)

        # Recent results section
        self._create_results_section(main_layout)

    def _create_schedule_table(self, compact: bool = False) -> QTableWidget:
        """Create a premium styled schedule table"""
        table = QTableWidget()

        if compact:
            headers = ["日付", "対戦", "時間"]
            widths = [80, 180, 60]
        else:
            headers = ["#", "日付", "ホーム", "", "スコア", "", "アウェイ", "状態"]
            widths = [40, 100, 120, 30, 80, 30, 120, 80]

        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                border: none;
                gridline-color: transparent;
            }}
            QTableWidget::item {{
                padding: 8px;
                color: {self.theme.text_primary};
                border-bottom: 1px solid {self.theme.border_muted};
            }}
            QTableWidget::item:selected {{
                background-color: {self.theme.primary};
                color: white;
            }}
            QTableWidget::item:hover {{
                background-color: {self.theme.bg_hover};
            }}
            QHeaderView::section {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated},
                    stop:1 {self.theme.bg_card});
                color: {self.theme.text_secondary};
                font-weight: 600;
                font-size: 11px;
                padding: 10px 8px;
                border: none;
                border-bottom: 2px solid {self.theme.primary};
            }}
        """)

        header = table.horizontalHeader()
        for i, width in enumerate(widths):
            header.resizeSection(i, width)
        header.setStretchLastSection(True)

        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(40)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setShowGrid(False)
        table.setAlternatingRowColors(False)

        return table

    def _create_results_section(self, parent_layout):
        """Create recent results section"""
        results_card = PremiumCard("最近の結果", "")

        results_scroll = QScrollArea()
        results_scroll.setWidgetResizable(True)
        results_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        results_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """)
        results_scroll.setFixedHeight(120)

        results_widget = QWidget()
        results_widget.setStyleSheet("background: transparent;")
        results_layout = QHBoxLayout(results_widget)
        results_layout.setSpacing(12)
        results_layout.setContentsMargins(0, 0, 0, 0)

        # Placeholder for recent game cards
        self.result_frames = []
        for i in range(5):
            result_frame = self._create_result_card()
            results_layout.addWidget(result_frame)
            self.result_frames.append(result_frame)

        results_layout.addStretch()
        results_scroll.setWidget(results_widget)
        results_card.add_widget(results_scroll)
        parent_layout.addWidget(results_card)

    def _create_result_card(self) -> QFrame:
        """Create a mini result card"""
        frame = QFrame()
        frame.setFixedSize(140, 90)
        frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated},
                    stop:1 {self.theme.bg_card});
                border-radius: 12px;
                border: 1px solid {self.theme.border_muted};
            }}
            QFrame:hover {{
                border-color: {self.theme.primary};
            }}
        """)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Date
        date_label = QLabel("4/1")
        date_label.setStyleSheet(f"""
            font-size: 10px;
            color: {self.theme.text_muted};
            background: transparent;
        """)
        layout.addWidget(date_label)

        # Score
        score_label = QLabel("5 - 3")
        score_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 700;
            color: {self.theme.text_primary};
            background: transparent;
        """)
        score_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(score_label)

        # Result
        result_label = QLabel("勝利")
        result_label.setStyleSheet(f"""
            font-size: 11px;
            color: {self.theme.success};
            font-weight: 600;
            background: transparent;
        """)
        result_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(result_label)

        return frame

    def set_game_state(self, game_state):
        """Update with game state"""
        self.game_state = game_state
        if not game_state:
            return

        self._update_schedule()

    def _update_schedule(self):
        """Update schedule tables"""
        if not self.game_state or not hasattr(self.game_state, 'schedule'):
            return

        schedule = self.game_state.schedule
        if not schedule or not hasattr(schedule, 'games'):
            return

        games = schedule.games

        # Filter based on current filter
        filter_idx = self.filter_combo.currentIndex()
        if filter_idx == 1 and self.game_state.player_team:
            # My team only
            team_name = self.game_state.player_team.name
            games = [g for g in games if g.home_team_name == team_name or g.away_team_name == team_name]
        elif filter_idx == 2:
            # Unplayed only
            games = [g for g in games if not g.is_completed]
        elif filter_idx == 3:
            # Completed only
            games = [g for g in games if g.is_completed]

        # Fill main schedule table
        self.schedule_table.setRowCount(min(50, len(games)))

        for row, game in enumerate(games[:50]):
            # Game number
            num_item = QTableWidgetItem(str(game.game_number))
            num_item.setTextAlignment(Qt.AlignCenter)
            self.schedule_table.setItem(row, 0, num_item)

            # Date
            date_item = QTableWidgetItem(game.date)
            date_item.setTextAlignment(Qt.AlignCenter)
            self.schedule_table.setItem(row, 1, date_item)

            # Home team
            home_item = QTableWidgetItem(game.home_team_name)
            home_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            home_item.setFont(QFont("", -1, QFont.Bold))
            self.schedule_table.setItem(row, 2, home_item)

            # VS
            vs_item = QTableWidgetItem("vs")
            vs_item.setTextAlignment(Qt.AlignCenter)
            vs_item.setForeground(QBrush(QColor(self.theme.text_muted)))
            self.schedule_table.setItem(row, 3, vs_item)

            # Score
            if game.is_completed:
                score = f"{game.home_score} - {game.away_score}"
            else:
                score = "---"
            score_item = QTableWidgetItem(score)
            score_item.setTextAlignment(Qt.AlignCenter)
            score_item.setFont(QFont("", -1, QFont.Bold))
            if game.is_completed:
                score_item.setForeground(QBrush(QColor(self.theme.gold)))
            self.schedule_table.setItem(row, 4, score_item)

            # (right side separator)
            self.schedule_table.setItem(row, 5, QTableWidgetItem(""))

            # Away team
            away_item = QTableWidgetItem(game.away_team_name)
            away_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            away_item.setFont(QFont("", -1, QFont.Bold))
            self.schedule_table.setItem(row, 6, away_item)

            # Status
            status_item = QTableWidgetItem(game.status.value)
            status_item.setTextAlignment(Qt.AlignCenter)
            if game.is_completed:
                status_item.setForeground(QBrush(QColor(self.theme.success)))
            else:
                status_item.setForeground(QBrush(QColor(self.theme.text_muted)))
            self.schedule_table.setItem(row, 7, status_item)

        # Fill upcoming games (next 5)
        if self.game_state.player_team:
            team_name = self.game_state.player_team.name
            upcoming = [g for g in schedule.games
                       if (g.home_team_name == team_name or g.away_team_name == team_name)
                       and not g.is_completed][:5]

            self.upcoming_table.setRowCount(len(upcoming))
            for row, game in enumerate(upcoming):
                # Date
                date_item = QTableWidgetItem(game.date)
                date_item.setTextAlignment(Qt.AlignCenter)
                self.upcoming_table.setItem(row, 0, date_item)

                # Opponent
                if game.home_team_name == team_name:
                    opponent = f"vs {game.away_team_name}"
                else:
                    opponent = f"@ {game.home_team_name}"
                opp_item = QTableWidgetItem(opponent)
                self.upcoming_table.setItem(row, 1, opp_item)

                # Time
                time_item = QTableWidgetItem("18:00")
                time_item.setTextAlignment(Qt.AlignCenter)
                self.upcoming_table.setItem(row, 2, time_item)

    def _filter_games(self):
        """Apply game filter"""
        self._update_schedule()

    def _on_date_selected(self, date: QDate):
        """Handle date selection from calendar"""
        # Filter to show games on selected date
        pass

    def _prev_month(self):
        """Go to previous month"""
        current = self.calendar.selectedDate()
        self.calendar.setSelectedDate(current.addMonths(-1))
        self._update_month_label()

    def _next_month(self):
        """Go to next month"""
        current = self.calendar.selectedDate()
        self.calendar.setSelectedDate(current.addMonths(1))
        self._update_month_label()

    def _update_month_label(self):
        """Update the month label"""
        current = self.calendar.selectedDate()
        self.month_label.setText(f"{current.year()}年{current.month()}月")
