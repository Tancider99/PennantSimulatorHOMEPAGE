# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Stats Page
OOTP-Style Premium Statistics Dashboard
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QComboBox, QPushButton, QScrollArea, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.panels import ContentPanel


class PremiumCard(QFrame):
    """Premium styled card for stats sections"""

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


class StatsPage(QWidget):
    """Premium statistics page"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None

        self._setup_ui()

    def _setup_ui(self):
        """Create the premium stats page layout"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Page header
        header = self._create_page_header()
        layout.addWidget(header)

        # Filter toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Stats tabs
        self.tabs = self._create_stats_tabs()
        layout.addWidget(self.tabs)

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

        title_layout = QVBoxLayout()
        title = QLabel("STATISTICS")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 700;
            color: {self.theme.text_primary};
            letter-spacing: 2px;
        """)
        subtitle = QLabel("シーズン成績とリーダーボード")
        subtitle.setStyleSheet(f"""
            font-size: 13px;
            color: {self.theme.text_secondary};
        """)
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)

        header_layout.addStretch()

        shadow = QGraphicsDropShadowEffect(header_frame)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 50))
        shadow.setOffset(0, 4)
        header_frame.setGraphicsEffect(shadow)

        return header_frame

    def _create_toolbar(self) -> QWidget:
        """Create filter toolbar"""
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated}, stop:1 {self.theme.bg_card});
                border: 1px solid {self.theme.border};
                border-radius: 12px;
            }}
        """)
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(20, 12, 20, 12)

        league_label = QLabel("リーグ:")
        league_label.setStyleSheet(f"color: {self.theme.text_secondary}; font-weight: 600;")
        layout.addWidget(league_label)

        self.league_combo = QComboBox()
        self.league_combo.addItems(["両リーグ", "セ・リーグ", "パ・リーグ"])
        self.league_combo.currentIndexChanged.connect(self._filter_stats)
        self.league_combo.setMinimumWidth(140)
        layout.addWidget(self.league_combo)

        layout.addStretch()

        return toolbar

    def _create_stats_tabs(self) -> QTabWidget:
        """Create tabbed stats display"""
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                background-color: transparent;
                border: none;
            }}
            QTabBar::tab {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card}, stop:1 {self.theme.bg_dark});
                color: {self.theme.text_secondary};
                border: 1px solid {self.theme.border};
                border-bottom: none;
                padding: 14px 28px;
                margin-right: 4px;
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
                font-size: 14px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.primary}, stop:1 {self.theme.primary_dark});
                color: white;
                border-color: {self.theme.primary};
            }}
            QTabBar::tab:hover:!selected {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_hover}, stop:1 {self.theme.bg_card});
                color: {self.theme.text_primary};
            }}
        """)

        tabs.addTab(self._create_batting_tab(), "打撃成績")
        tabs.addTab(self._create_pitching_tab(), "投手成績")
        tabs.addTab(self._create_team_tab(), "チーム成績")

        return tabs

    def _create_batting_tab(self) -> QWidget:
        """Create batting stats tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(8, 16, 8, 16)

        leaders_layout = QHBoxLayout()
        leaders_layout.setSpacing(16)

        avg_card = PremiumCard("首位打者")
        self.avg_table = self._create_leader_table()
        avg_card.add_widget(self.avg_table)
        leaders_layout.addWidget(avg_card)

        hr_card = PremiumCard("本塁打王")
        self.hr_table = self._create_leader_table()
        hr_card.add_widget(self.hr_table)
        leaders_layout.addWidget(hr_card)

        rbi_card = PremiumCard("打点王")
        self.rbi_table = self._create_leader_table()
        rbi_card.add_widget(self.rbi_table)
        leaders_layout.addWidget(rbi_card)

        layout.addLayout(leaders_layout)

        secondary_layout = QHBoxLayout()
        secondary_layout.setSpacing(16)

        hits_card = PremiumCard("安打")
        self.hits_table = self._create_leader_table()
        hits_card.add_widget(self.hits_table)
        secondary_layout.addWidget(hits_card)

        sb_card = PremiumCard("盗塁")
        self.sb_table = self._create_leader_table()
        sb_card.add_widget(self.sb_table)
        secondary_layout.addWidget(sb_card)

        runs_card = PremiumCard("得点")
        self.runs_table = self._create_leader_table()
        runs_card.add_widget(self.runs_table)
        secondary_layout.addWidget(runs_card)

        layout.addLayout(secondary_layout)
        layout.addStretch()

        scroll.setWidget(widget)
        return scroll

    def _create_pitching_tab(self) -> QWidget:
        """Create pitching stats tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(8, 16, 8, 16)

        leaders_layout = QHBoxLayout()
        leaders_layout.setSpacing(16)

        era_card = PremiumCard("最優秀防御率")
        self.era_table = self._create_leader_table()
        era_card.add_widget(self.era_table)
        leaders_layout.addWidget(era_card)

        wins_card = PremiumCard("最多勝")
        self.wins_table = self._create_leader_table()
        wins_card.add_widget(self.wins_table)
        leaders_layout.addWidget(wins_card)

        saves_card = PremiumCard("最多セーブ")
        self.saves_table = self._create_leader_table()
        saves_card.add_widget(self.saves_table)
        leaders_layout.addWidget(saves_card)

        layout.addLayout(leaders_layout)

        secondary_layout = QHBoxLayout()
        secondary_layout.setSpacing(16)

        so_card = PremiumCard("奪三振")
        self.so_table = self._create_leader_table()
        so_card.add_widget(self.so_table)
        secondary_layout.addWidget(so_card)

        ip_card = PremiumCard("投球回")
        self.ip_table = self._create_leader_table()
        ip_card.add_widget(self.ip_table)
        secondary_layout.addWidget(ip_card)

        whip_card = PremiumCard("WHIP")
        self.whip_table = self._create_leader_table()
        whip_card.add_widget(self.whip_table)
        secondary_layout.addWidget(whip_card)

        layout.addLayout(secondary_layout)
        layout.addStretch()

        scroll.setWidget(widget)
        return scroll

    def _create_team_tab(self) -> QWidget:
        """Create team stats tab"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(8, 16, 8, 16)

        batting_card = PremiumCard("チーム打撃成績")
        self.team_batting_table = self._create_team_stats_table("batting")
        batting_card.add_widget(self.team_batting_table)
        layout.addWidget(batting_card)

        pitching_card = PremiumCard("チーム投手成績")
        self.team_pitching_table = self._create_team_stats_table("pitching")
        pitching_card.add_widget(self.team_pitching_table)
        layout.addWidget(pitching_card)

        layout.addStretch()

        scroll.setWidget(widget)
        return scroll

    def _create_leader_table(self) -> QTableWidget:
        """Create a premium leader table"""
        table = QTableWidget()
        table.setRowCount(10)
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["#", "選手", "チーム", "値"])
        table.setMinimumHeight(300)

        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.theme.bg_input};
                border: none;
                border-radius: 8px;
                gridline-color: {self.theme.border_muted};
            }}
            QTableWidget::item {{
                padding: 10px;
                border-bottom: 1px solid {self.theme.border_muted};
            }}
            QTableWidget::item:selected {{
                background-color: {self.theme.primary};
                color: white;
            }}
            QHeaderView::section {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated}, stop:1 {self.theme.bg_card});
                color: {self.theme.text_secondary};
                font-weight: 700;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 1px;
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid {self.theme.primary};
            }}
        """)

        header = table.horizontalHeader()
        header.resizeSection(0, 35)
        header.resizeSection(1, 100)
        header.resizeSection(2, 70)
        header.setStretchLastSection(True)

        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(32)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)

        return table

    def _create_team_stats_table(self, stat_type: str) -> QTableWidget:
        """Create team stats table"""
        table = QTableWidget()
        table.setRowCount(12)

        if stat_type == "batting":
            headers = ["チーム", "打率", "OBP", "SLG", "OPS", "HR", "打点", "得点", "安打", "盗塁"]
        else:
            headers = ["チーム", "ERA", "勝", "敗", "S", "K", "BB", "WHIP", "IP", "失点"]

        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setMinimumHeight(350)

        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.theme.bg_input};
                border: none;
                border-radius: 8px;
                gridline-color: {self.theme.border_muted};
            }}
            QTableWidget::item {{
                padding: 10px;
                border-bottom: 1px solid {self.theme.border_muted};
            }}
            QTableWidget::item:selected {{
                background-color: {self.theme.primary};
                color: white;
            }}
            QHeaderView::section {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated}, stop:1 {self.theme.bg_card});
                color: {self.theme.text_secondary};
                font-weight: 700;
                font-size: 11px;
                text-transform: uppercase;
                padding: 12px 6px;
                border: none;
                border-bottom: 2px solid {self.theme.primary};
            }}
        """)

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(32)
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        return table

    def set_game_state(self, game_state):
        """Update with game state"""
        self.game_state = game_state
        if not game_state:
            return
        self._update_stats()

    def _update_stats(self):
        """Update all stats tables"""
        if not self.game_state:
            return
        self._update_batting_leaders()
        self._update_pitching_leaders()

    def _update_batting_leaders(self):
        """Update batting leader tables"""
        if not self.game_state:
            return

        all_batters = []
        for team in self.game_state.teams:
            for player in team.players:
                if player.position.value != "投手":
                    all_batters.append((player, team))

        league_filter = self.league_combo.currentIndex()
        if league_filter == 1:
            all_batters = [(p, t) for p, t in all_batters if t.league.value == "セントラル"]
        elif league_filter == 2:
            all_batters = [(p, t) for p, t in all_batters if t.league.value == "パシフィック"]

        qualified = [(p, t) for p, t in all_batters if p.record.at_bats >= 50]
        avg_leaders = sorted(qualified, key=lambda x: x[0].record.batting_average, reverse=True)[:10]
        self._fill_leader_table(self.avg_table, avg_leaders,
                               lambda p: f".{int(p.record.batting_average * 1000):03d}")

        hr_leaders = sorted(all_batters, key=lambda x: x[0].record.home_runs, reverse=True)[:10]
        self._fill_leader_table(self.hr_table, hr_leaders,
                               lambda p: str(p.record.home_runs))

        rbi_leaders = sorted(all_batters, key=lambda x: x[0].record.rbis, reverse=True)[:10]
        self._fill_leader_table(self.rbi_table, rbi_leaders,
                               lambda p: str(p.record.rbis))

        hits_leaders = sorted(all_batters, key=lambda x: x[0].record.hits, reverse=True)[:10]
        self._fill_leader_table(self.hits_table, hits_leaders,
                               lambda p: str(p.record.hits))

        sb_leaders = sorted(all_batters, key=lambda x: x[0].record.stolen_bases, reverse=True)[:10]
        self._fill_leader_table(self.sb_table, sb_leaders,
                               lambda p: str(p.record.stolen_bases))

        runs_leaders = sorted(all_batters, key=lambda x: x[0].record.runs, reverse=True)[:10]
        self._fill_leader_table(self.runs_table, runs_leaders,
                               lambda p: str(p.record.runs))

    def _update_pitching_leaders(self):
        """Update pitching leader tables"""
        if not self.game_state:
            return

        all_pitchers = []
        for team in self.game_state.teams:
            for player in team.players:
                if player.position.value == "投手":
                    all_pitchers.append((player, team))

        league_filter = self.league_combo.currentIndex()
        if league_filter == 1:
            all_pitchers = [(p, t) for p, t in all_pitchers if t.league.value == "セントラル"]
        elif league_filter == 2:
            all_pitchers = [(p, t) for p, t in all_pitchers if t.league.value == "パシフィック"]

        qualified = [(p, t) for p, t in all_pitchers if p.record.innings_pitched >= 20]
        era_leaders = sorted(qualified, key=lambda x: x[0].record.era)[:10]
        self._fill_leader_table(self.era_table, era_leaders,
                               lambda p: f"{p.record.era:.2f}")

        wins_leaders = sorted(all_pitchers, key=lambda x: x[0].record.wins, reverse=True)[:10]
        self._fill_leader_table(self.wins_table, wins_leaders,
                               lambda p: str(p.record.wins))

        saves_leaders = sorted(all_pitchers, key=lambda x: x[0].record.saves, reverse=True)[:10]
        self._fill_leader_table(self.saves_table, saves_leaders,
                               lambda p: str(p.record.saves))

        so_leaders = sorted(all_pitchers, key=lambda x: x[0].record.strikeouts_pitched, reverse=True)[:10]
        self._fill_leader_table(self.so_table, so_leaders,
                               lambda p: str(p.record.strikeouts_pitched))

        ip_leaders = sorted(all_pitchers, key=lambda x: x[0].record.innings_pitched, reverse=True)[:10]
        self._fill_leader_table(self.ip_table, ip_leaders,
                               lambda p: f"{p.record.innings_pitched:.1f}")

    def _fill_leader_table(self, table: QTableWidget, leaders: list, value_func):
        """Fill a leader table with data"""
        for row, (player, team) in enumerate(leaders):
            rank_item = QTableWidgetItem(str(row + 1))
            rank_item.setTextAlignment(Qt.AlignCenter)
            if row < 3:
                rank_item.setForeground(QBrush(QColor(self.theme.gold)))
                font = QFont()
                font.setBold(True)
                rank_item.setFont(font)
            table.setItem(row, 0, rank_item)

            name_item = QTableWidgetItem(player.name)
            table.setItem(row, 1, name_item)

            team_item = QTableWidgetItem(team.name[:4])
            team_item.setForeground(QBrush(QColor(self.theme.text_secondary)))
            table.setItem(row, 2, team_item)

            value_item = QTableWidgetItem(value_func(player))
            value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value_item.setFont(QFont("", -1, QFont.Bold))
            table.setItem(row, 3, value_item)

    def _filter_stats(self):
        """Apply league filter"""
        self._update_stats()
