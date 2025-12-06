# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Home Page
OOTP-Style Ultra Premium Dashboard with Team Overview
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGridLayout,
    QFrame, QPushButton, QScrollArea, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.cards import Card, StatCard, TeamCard, StandingsCard, PlayerCard
from UI.widgets.panels import ContentPanel, InfoPanel
from UI.widgets.buttons import ActionButton


class PremiumWelcomeCard(QFrame):
    """Ultra Premium Welcome Banner with gradient and effects"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._setup_ui()
        self._add_shadow()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0.5,
                    stop:0 {self.theme.bg_card_elevated},
                    stop:0.3 {self.theme.primary}30,
                    stop:0.7 {self.theme.bg_card},
                    stop:1 {self.theme.bg_card_elevated});
                border: 1px solid {self.theme.border};
                border-radius: 16px;
            }}
        """)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(24, 20, 24, 20)
        self.main_layout.setSpacing(20)

    def _add_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 8)
        self.setGraphicsEffect(shadow)


class PremiumStatCard(QFrame):
    """Ultra Premium Stat Card with gradient and icon"""

    def __init__(self, title: str, value: str, subtitle: str = "",
                 icon: str = "", color: str = None, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._color = color or self.theme.primary

        self._setup_ui(title, value, subtitle, icon)
        self._add_shadow()

    def _setup_ui(self, title: str, value: str, subtitle: str, icon: str):
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated},
                    stop:0.5 {self.theme.bg_card},
                    stop:1 {self.theme.bg_card_elevated});
                border: 1px solid {self.theme.border};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border-color: {self._color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        # Top row with icon
        top_layout = QHBoxLayout()
        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet(f"""
                font-size: 24px;
                background: transparent;
            """)
            top_layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 700;
            color: {self.theme.text_secondary};
            text-transform: uppercase;
            letter-spacing: 1px;
            background: transparent;
        """)
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        # Value with premium styling
        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(f"""
            font-size: 32px;
            font-weight: 800;
            color: {self._color};
            background: transparent;
        """)
        layout.addWidget(self._value_label)

        # Subtitle
        self._subtitle_label = QLabel(subtitle)
        self._subtitle_label.setStyleSheet(f"""
            font-size: 12px;
            color: {self.theme.text_muted};
            background: transparent;
        """)
        layout.addWidget(self._subtitle_label)

    def _add_shadow(self):
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 40))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

    def set_value(self, value: str):
        self._value_label.setText(value)

    def set_subtitle(self, subtitle: str):
        self._subtitle_label.setText(subtitle)


class QuickActionButton(QFrame):
    """Premium Quick Action Button with icon and description"""

    clicked = Signal()

    def __init__(self, title: str, subtitle: str, icon: str, color: str = None, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._color = color or self.theme.primary

        self._setup_ui(title, subtitle, icon)
        self.setCursor(Qt.PointingHandCursor)

    def _setup_ui(self, title: str, subtitle: str, icon: str):
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated}, stop:1 {self.theme.bg_card});
                border: 1px solid {self.theme.border};
                border-radius: 12px;
            }}
            QFrame:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_hover}, stop:1 {self.theme.bg_card_elevated});
                border-color: {self._color};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(14)

        # Icon
        icon_frame = QFrame()
        icon_frame.setFixedSize(44, 44)
        icon_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self._color}, stop:1 {self._color}cc);
                border-radius: 10px;
            }}
        """)
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet(f"""
            font-size: 20px;
            color: white;
            background: transparent;
        """)
        icon_layout.addWidget(icon_label)
        layout.addWidget(icon_frame)

        # Text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {self.theme.text_primary};
            background: transparent;
        """)
        text_layout.addWidget(title_label)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet(f"""
            font-size: 11px;
            color: {self.theme.text_muted};
            background: transparent;
        """)
        text_layout.addWidget(subtitle_label)

        layout.addLayout(text_layout)
        layout.addStretch()

        # Arrow
        arrow = QLabel("→")
        arrow.setStyleSheet(f"""
            font-size: 18px;
            color: {self.theme.text_muted};
            background: transparent;
        """)
        layout.addWidget(arrow)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class HomePage(ContentPanel):
    """Home page with ultra premium team dashboard"""

    game_requested = Signal()
    view_roster_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None

        self._create_ui()

    def _create_ui(self):
        """Create the premium home page layout"""
        # Welcome section
        self._create_welcome_section()

        # Quick stats row
        self._create_stats_row()

        # Main content grid
        content_grid = QHBoxLayout()
        content_grid.setSpacing(20)

        # Left column - Team info and actions
        left_col = QVBoxLayout()
        left_col.setSpacing(16)
        self._create_team_section(left_col)
        self._create_actions_section(left_col)
        left_col.addStretch()

        left_widget = QWidget()
        left_widget.setLayout(left_col)
        content_grid.addWidget(left_widget, stretch=2)

        # Right column - Standings and news
        right_col = QVBoxLayout()
        right_col.setSpacing(16)
        self._create_standings_section(right_col)
        self._create_news_section(right_col)
        right_col.addStretch()

        right_widget = QWidget()
        right_widget.setLayout(right_col)
        content_grid.addWidget(right_widget, stretch=1)

        self.add_layout(content_grid)
        self.add_stretch()

    def _create_welcome_section(self):
        """Create premium welcome header"""
        welcome_card = PremiumWelcomeCard()

        # Team logo placeholder with premium styling
        logo = QLabel("NPB")
        logo.setFixedSize(80, 80)
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet(f"""
            font-size: 48px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {self.theme.bg_card_elevated}, stop:1 {self.theme.bg_input});
            border-radius: 16px;
            border: 2px solid {self.theme.border};
        """)
        welcome_card.main_layout.addWidget(logo)

        # Welcome text
        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)

        self.team_name_label = QLabel("チームを選択してください")
        self.team_name_label.setStyleSheet(f"""
            font-size: 32px;
            font-weight: 800;
            color: {self.theme.text_primary};
            background: transparent;
        """)

        self.season_label = QLabel("2024年シーズン")
        self.season_label.setStyleSheet(f"""
            font-size: 14px;
            color: {self.theme.text_secondary};
            background: transparent;
        """)

        text_layout.addWidget(self.team_name_label)
        text_layout.addWidget(self.season_label)
        welcome_card.main_layout.addLayout(text_layout)

        welcome_card.main_layout.addStretch()

        # Quick action buttons
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(8)

        sim_btn = QPushButton("▶  次の試合をプレイ")
        sim_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.success_light}, stop:1 {self.theme.success});
                color: white;
                border: none;
                border-radius: 10px;
                padding: 14px 28px;
                font-size: 15px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.success_hover}, stop:1 {self.theme.success_light});
            }}
        """)
        sim_btn.clicked.connect(lambda: self.game_requested.emit())
        buttons_layout.addWidget(sim_btn)

        sim_week_btn = QPushButton("⏩ 1週間シミュレート")
        sim_week_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_hover}, stop:1 {self.theme.bg_card});
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 10px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.primary_light}, stop:1 {self.theme.primary});
                border-color: {self.theme.primary};
                color: white;
            }}
        """)
        buttons_layout.addWidget(sim_week_btn)

        welcome_card.main_layout.addLayout(buttons_layout)

        self.add_widget(welcome_card)

    def _create_stats_row(self):
        """Create premium quick stats cards"""
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        # Record
        self.wins_card = PremiumStatCard(
            "戦績", "0勝", "0敗 0分",
            "", self.theme.success_light
        )
        stats_layout.addWidget(self.wins_card)

        # Win %
        self.pct_card = PremiumStatCard(
            "勝率", ".000", "リーグ順位: -",
            "", self.theme.accent_gold
        )
        stats_layout.addWidget(self.pct_card)

        # Games back
        self.gb_card = PremiumStatCard(
            "首位差", "-", "首位まで",
            "", self.theme.primary_light
        )
        stats_layout.addWidget(self.gb_card)

        # Next game
        self.next_game_card = PremiumStatCard(
            "次の対戦", "未定", "日程未確定",
            "", self.theme.info_light
        )
        stats_layout.addWidget(self.next_game_card)

        self.add_layout(stats_layout)

    def _create_team_section(self, layout: QVBoxLayout):
        """Create team information section"""
        team_card = Card("チーム情報")

        # Team stats grid
        info_grid = QGridLayout()
        info_grid.setSpacing(12)
        info_grid.setContentsMargins(8, 8, 8, 8)

        self.info_labels = {}
        info_items = [
            ("監督", "-", 0, 0),
            ("本拠地", "-", 0, 1),
            ("支配下選手", "- / 70", 1, 0),
            ("育成選手", "- / 30", 1, 1),
        ]

        for label, value, row, col in info_items:
            frame = QFrame()
            frame.setStyleSheet(f"""
                QFrame {{
                    background: {self.theme.bg_input};
                    border-radius: 8px;
                }}
            """)
            frame_layout = QVBoxLayout(frame)
            frame_layout.setContentsMargins(12, 10, 12, 10)
            frame_layout.setSpacing(4)

            lbl = QLabel(label)
            lbl.setStyleSheet(f"""
                font-size: 11px;
                color: {self.theme.text_muted};
                text-transform: uppercase;
            """)
            frame_layout.addWidget(lbl)

            val = QLabel(value)
            val.setStyleSheet(f"""
                font-size: 16px;
                font-weight: 600;
                color: {self.theme.text_primary};
            """)
            frame_layout.addWidget(val)
            self.info_labels[label] = val

            info_grid.addWidget(frame, row, col)

        team_card.add_layout(info_grid)
        layout.addWidget(team_card)

        # Top players
        top_players_card = Card("注目選手")
        self.top_players_layout = QVBoxLayout()
        self.top_players_layout.setSpacing(10)

        # Placeholder
        placeholder = QLabel("選手データを読み込み中...")
        placeholder.setStyleSheet(f"""
            color: {self.theme.text_muted};
            padding: 20px;
            text-align: center;
        """)
        placeholder.setAlignment(Qt.AlignCenter)
        self.top_players_layout.addWidget(placeholder)

        top_players_card.add_layout(self.top_players_layout)
        layout.addWidget(top_players_card)

    def _create_actions_section(self, layout: QVBoxLayout):
        """Create premium quick action buttons"""
        actions_card = Card("クイックアクション")

        actions_grid = QGridLayout()
        actions_grid.setSpacing(12)

        # Action buttons with premium styling
        roster_btn = QuickActionButton(
            "ロースター編集", "スタメン・ベンチの設定",
            "R", self.theme.primary
        )
        roster_btn.clicked.connect(lambda: self.view_roster_requested.emit())
        actions_grid.addWidget(roster_btn, 0, 0)

        lineup_btn = QuickActionButton(
            "打順変更", "打順とポジションの設定",
            "L", self.theme.info
        )
        actions_grid.addWidget(lineup_btn, 0, 1)

        rotation_btn = QuickActionButton(
            "投手運用", "先発ローテーション設定",
            "P", self.theme.warning
        )
        actions_grid.addWidget(rotation_btn, 1, 0)

        farm_btn = QuickActionButton(
            "ファーム管理", "二軍選手の育成・昇格",
            "F", self.theme.success
        )
        actions_grid.addWidget(farm_btn, 1, 1)

        actions_card.add_layout(actions_grid)
        layout.addWidget(actions_card)

    def _create_standings_section(self, layout: QVBoxLayout):
        """Create premium standings preview"""
        self.standings_card = StandingsCard("リーグ順位")
        layout.addWidget(self.standings_card)

    def _create_news_section(self, layout: QVBoxLayout):
        """Create premium news/recent events section"""
        news_card = Card("最近の出来事")

        self.news_layout = QVBoxLayout()
        self.news_layout.setSpacing(10)

        # Sample news items
        news_items = [
            ("試合結果", "ジャイアンツ 5 - 3 タイガース", "本日"),
            ("ニュース", "新外国人選手が入団決定", "1日前"),
            ("達成", "チーム通算3000勝まであと10勝", "2日前"),
        ]

        for title, content, time in news_items:
            news_item = self._create_news_item(title, content, time)
            self.news_layout.addWidget(news_item)

        news_card.add_layout(self.news_layout)
        layout.addWidget(news_card)

    def _create_news_item(self, title: str, content: str, time: str) -> QWidget:
        """Create a premium news item widget"""
        item = QFrame()
        item.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_input}, stop:1 {self.theme.bg_card});
                border: 1px solid {self.theme.border_muted};
                border-radius: 10px;
            }}
            QFrame:hover {{
                border-color: {self.theme.primary};
                background: {self.theme.bg_card_elevated};
            }}
        """)

        layout = QVBoxLayout(item)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-weight: 700;
            font-size: 13px;
            color: {self.theme.text_primary};
            background: transparent;
        """)
        header.addWidget(title_label)

        time_label = QLabel(time)
        time_label.setStyleSheet(f"""
            color: {self.theme.text_muted};
            font-size: 11px;
            background: transparent;
        """)
        header.addWidget(time_label)

        layout.addLayout(header)

        content_label = QLabel(content)
        content_label.setStyleSheet(f"""
            color: {self.theme.text_secondary};
            font-size: 13px;
            background: transparent;
        """)
        layout.addWidget(content_label)

        return item

    def set_game_state(self, game_state):
        """Update page with game state"""
        self.game_state = game_state
        if not game_state:
            return

        team = game_state.player_team
        if not team:
            return

        # Update welcome section
        self.team_name_label.setText(team.name)
        self.season_label.setText(f"{game_state.current_year}年シーズン  |  {team.league.value}")

        # Update stats cards
        self.wins_card.set_value(f"{team.wins}勝")
        self.wins_card.set_subtitle(f"{team.losses}敗 {team.draws}分")

        pct = team.winning_percentage
        self.pct_card.set_value(f".{int(pct * 1000):03d}")

        # Update team info
        roster_count = len([p for p in team.players if not p.is_developmental])
        dev_count = len([p for p in team.players if p.is_developmental])
        self.info_labels["支配下選手"].setText(f"{roster_count} / 70")
        self.info_labels["育成選手"].setText(f"{dev_count} / 30")

        # Update standings
        if hasattr(game_state, 'all_teams') and game_state.all_teams:
            league_teams = [t for t in game_state.all_teams if t.league == team.league]
            league_teams.sort(key=lambda t: t.winning_percentage, reverse=True)
            self.standings_card.set_standings(league_teams[:6])

        # Update top players
        self._update_top_players(team)

    def _update_top_players(self, team):
        """Update top players display with premium cards"""
        # Clear existing
        while self.top_players_layout.count():
            item = self.top_players_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get top players
        batters = [p for p in team.players if p.position.value != "投手" and not p.is_developmental]
        pitchers = [p for p in team.players if p.position.value == "投手" and not p.is_developmental]

        batters.sort(key=lambda p: p.overall_rating, reverse=True)
        pitchers.sort(key=lambda p: p.overall_rating, reverse=True)

        # Add section headers and mini player cards
        if batters:
            self._add_player_section("野手トップ", batters[:2])

        if pitchers:
            self._add_player_section("投手トップ", pitchers[:2])

    def _add_player_section(self, title: str, players: list):
        """Add a section of player cards"""
        header = QLabel(title)
        header.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 700;
            color: {self.theme.text_secondary};
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 4px 0;
        """)
        self.top_players_layout.addWidget(header)

        for player in players:
            card = PlayerCard(player, show_stats=True)
            card.setMaximumHeight(120)
            self.top_players_layout.addWidget(card)
