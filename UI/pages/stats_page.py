# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Stats Page
Premium Statistics Dashboard
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
                background: rgba(38,42,48,0.5); /* bg_card_elevated, alpha控えめ */
                border: none;
                border-radius: 0px;
            }}
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(16)

        if self._title:
            header = QFrame()
            header.setStyleSheet(f"""
                QFrame {{
                    background: rgba(255,255,255,0.08); /* 白系の超控えめ */
                    border-radius: 0px;
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

        # リーグ選択
        league_label = QLabel("リーグ:")
        league_label.setStyleSheet(f"color: {self.theme.text_secondary}; font-weight: 600;")
        layout.addWidget(league_label)

        self.league_combo = QComboBox()
        self.league_combo.addItems(["両リーグ", "North League", "South League"])
        self.league_combo.currentIndexChanged.connect(self._filter_stats)
        self.league_combo.setMinimumWidth(140)
        layout.addWidget(self.league_combo)

        layout.addSpacing(20)

        # 軍選択
        level_label = QLabel("軍:")
        level_label.setStyleSheet(f"color: {self.theme.text_secondary}; font-weight: 600;")
        layout.addWidget(level_label)

        self.level_combo = QComboBox()
        self.level_combo.addItems(["一軍", "二軍", "三軍", "全軍合計"])
        self.level_combo.currentIndexChanged.connect(self._filter_stats)
        self.level_combo.setMinimumWidth(120)
        layout.addWidget(self.level_combo)

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
        tabs.addTab(self._create_advanced_batting_tab(), "打撃セイバー")
        tabs.addTab(self._create_advanced_pitching_tab(), "投手セイバー")
        tabs.addTab(self._create_team_tab(), "チーム成績")
        tabs.addTab(self._create_full_stats_tab(), "全選手一覧")

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
        self._update_advanced_batting_leaders()
        self._update_advanced_pitching_leaders()
        self._update_full_stats_tables()

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
            all_batters = [(p, t) for p, t in all_batters if t.league.value == "North League"]
        elif league_filter == 2:
            all_batters = [(p, t) for p, t in all_batters if t.league.value == "South League"]

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
            all_pitchers = [(p, t) for p, t in all_pitchers if t.league.value == "North League"]
        elif league_filter == 2:
            all_pitchers = [(p, t) for p, t in all_pitchers if t.league.value == "South League"]

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

    def _create_advanced_batting_tab(self) -> QWidget:
        """Create advanced batting stats tab (Sabermetrics)"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(8, 16, 8, 16)

        # Row 1: wOBA, OPS, ISO
        leaders_layout1 = QHBoxLayout()
        leaders_layout1.setSpacing(16)

        woba_card = PremiumCard("wOBA")
        self.woba_table = self._create_leader_table()
        woba_card.add_widget(self.woba_table)
        leaders_layout1.addWidget(woba_card)

        ops_card = PremiumCard("OPS")
        self.ops_table = self._create_leader_table()
        ops_card.add_widget(self.ops_table)
        leaders_layout1.addWidget(ops_card)

        iso_card = PremiumCard("ISO (純長打力)")
        self.iso_table = self._create_leader_table()
        iso_card.add_widget(self.iso_table)
        leaders_layout1.addWidget(iso_card)

        layout.addLayout(leaders_layout1)

        # Row 2: BB%, K%, BABIP
        leaders_layout2 = QHBoxLayout()
        leaders_layout2.setSpacing(16)

        bb_pct_card = PremiumCard("BB%")
        self.bb_pct_table = self._create_leader_table()
        bb_pct_card.add_widget(self.bb_pct_table)
        leaders_layout2.addWidget(bb_pct_card)

        k_pct_card = PremiumCard("K% (最少)")
        self.k_pct_table = self._create_leader_table()
        k_pct_card.add_widget(self.k_pct_table)
        leaders_layout2.addWidget(k_pct_card)

        babip_card = PremiumCard("BABIP")
        self.babip_table = self._create_leader_table()
        babip_card.add_widget(self.babip_table)
        leaders_layout2.addWidget(babip_card)

        layout.addLayout(leaders_layout2)
        layout.addStretch()

        scroll.setWidget(widget)
        return scroll

    def _create_advanced_pitching_tab(self) -> QWidget:
        """Create advanced pitching stats tab (Sabermetrics)"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        layout.setContentsMargins(8, 16, 8, 16)

        # Row 1: FIP, xFIP, WHIP
        leaders_layout1 = QHBoxLayout()
        leaders_layout1.setSpacing(16)

        fip_card = PremiumCard("FIP")
        self.fip_table = self._create_leader_table()
        fip_card.add_widget(self.fip_table)
        leaders_layout1.addWidget(fip_card)

        xfip_card = PremiumCard("xFIP")
        self.xfip_table = self._create_leader_table()
        xfip_card.add_widget(self.xfip_table)
        leaders_layout1.addWidget(xfip_card)

        whip_card = PremiumCard("WHIP")
        self.whip_table = self._create_leader_table()
        whip_card.add_widget(self.whip_table)
        leaders_layout1.addWidget(whip_card)

        layout.addLayout(leaders_layout1)

        # Row 2: K/9, BB/9, K/BB
        leaders_layout2 = QHBoxLayout()
        leaders_layout2.setSpacing(16)

        k9_card = PremiumCard("K/9")
        self.k9_table = self._create_leader_table()
        k9_card.add_widget(self.k9_table)
        leaders_layout2.addWidget(k9_card)

        bb9_card = PremiumCard("BB/9 (最少)")
        self.bb9_table = self._create_leader_table()
        bb9_card.add_widget(self.bb9_table)
        leaders_layout2.addWidget(bb9_card)

        kbb_card = PremiumCard("K/BB")
        self.kbb_table = self._create_leader_table()
        kbb_card.add_widget(self.kbb_table)
        leaders_layout2.addWidget(kbb_card)

        layout.addLayout(leaders_layout2)
        layout.addStretch()

        scroll.setWidget(widget)
        return scroll

    def _create_full_stats_tab(self) -> QWidget:
        """Create full player stats table"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        layout.setContentsMargins(8, 16, 8, 16)

        # 打者テーブル
        batting_card = PremiumCard("全打者成績")
        self.full_batting_table = self._create_full_player_table("batting")
        batting_card.add_widget(self.full_batting_table)
        layout.addWidget(batting_card)

        # 投手テーブル
        pitching_card = PremiumCard("全投手成績")
        self.full_pitching_table = self._create_full_player_table("pitching")
        pitching_card.add_widget(self.full_pitching_table)
        layout.addWidget(pitching_card)

        layout.addStretch()
        scroll.setWidget(widget)
        return scroll

    def _create_full_player_table(self, stat_type: str) -> QTableWidget:
        """Create full player stats table"""
        table = QTableWidget()

        if stat_type == "batting":
            headers = ["選手", "チーム", "試合", "打率", "OBP", "SLG", "OPS", "HR", "打点",
                      "安打", "四球", "三振", "盗塁", "wOBA", "ISO", "BABIP"]
        else:
            headers = ["選手", "チーム", "登板", "勝", "敗", "S", "防御率", "投球回",
                      "奪三振", "四球", "WHIP", "K/9", "BB/9", "FIP", "xFIP"]

        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setMinimumHeight(400)

        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.theme.bg_input};
                border: none;
                border-radius: 8px;
                gridline-color: {self.theme.border_muted};
            }}
            QTableWidget::item {{
                padding: 8px;
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
                font-size: 10px;
                padding: 10px 4px;
                border: none;
                border-bottom: 2px solid {self.theme.primary};
            }}
        """)

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(28)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)

        return table

    def _get_player_record(self, player, level_filter: int):
        """Get player record based on level filter"""
        from models import TeamLevel
        if level_filter == 0:  # 一軍
            return player.record
        elif level_filter == 1:  # 二軍
            return player.record_farm
        elif level_filter == 2:  # 三軍
            return player.record_third
        else:  # 全軍合計
            return player.get_current_season_total()

    def _filter_stats(self):
        """Apply league filter"""
        self._update_stats()

    def _update_advanced_batting_leaders(self):
        """Update advanced batting leader tables"""
        if not self.game_state:
            return

        all_batters = []
        level_filter = self.level_combo.currentIndex()

        for team in self.game_state.teams:
            for player in team.players:
                if player.position.value != "投手":
                    record = self._get_player_record(player, level_filter)
                    all_batters.append((player, team, record))

        league_filter = self.league_combo.currentIndex()
        if league_filter == 1:
            all_batters = [(p, t, r) for p, t, r in all_batters if t.league.value == "North League"]
        elif league_filter == 2:
            all_batters = [(p, t, r) for p, t, r in all_batters if t.league.value == "South League"]

        # wOBA
        qualified = [(p, t, r) for p, t, r in all_batters if r.plate_appearances >= 50]
        woba_leaders = sorted(qualified, key=lambda x: x[2].woba, reverse=True)[:10]
        self._fill_leader_table_with_record(self.woba_table, woba_leaders,
                                           lambda r: f".{int(r.woba * 1000):03d}")

        # OPS
        ops_leaders = sorted(qualified, key=lambda x: x[2].ops, reverse=True)[:10]
        self._fill_leader_table_with_record(self.ops_table, ops_leaders,
                                           lambda r: f".{int(r.ops * 1000):03d}")

        # ISO
        iso_leaders = sorted(qualified, key=lambda x: x[2].iso, reverse=True)[:10]
        self._fill_leader_table_with_record(self.iso_table, iso_leaders,
                                           lambda r: f".{int(r.iso * 1000):03d}")

        # BB%
        bb_leaders = sorted(qualified, key=lambda x: x[2].bb_rate, reverse=True)[:10]
        self._fill_leader_table_with_record(self.bb_pct_table, bb_leaders,
                                           lambda r: f"{r.bb_rate * 100:.1f}%")

        # K% (lowest is best)
        k_leaders = sorted(qualified, key=lambda x: x[2].k_rate)[:10]
        self._fill_leader_table_with_record(self.k_pct_table, k_leaders,
                                           lambda r: f"{r.k_rate * 100:.1f}%")

        # BABIP
        babip_leaders = sorted(qualified, key=lambda x: x[2].babip, reverse=True)[:10]
        self._fill_leader_table_with_record(self.babip_table, babip_leaders,
                                           lambda r: f".{int(r.babip * 1000):03d}")

    def _update_advanced_pitching_leaders(self):
        """Update advanced pitching leader tables"""
        if not self.game_state:
            return

        all_pitchers = []
        level_filter = self.level_combo.currentIndex()

        for team in self.game_state.teams:
            for player in team.players:
                if player.position.value == "投手":
                    record = self._get_player_record(player, level_filter)
                    all_pitchers.append((player, team, record))

        league_filter = self.league_combo.currentIndex()
        if league_filter == 1:
            all_pitchers = [(p, t, r) for p, t, r in all_pitchers if t.league.value == "North League"]
        elif league_filter == 2:
            all_pitchers = [(p, t, r) for p, t, r in all_pitchers if t.league.value == "South League"]

        # Qualified pitchers
        qualified = [(p, t, r) for p, t, r in all_pitchers if r.innings_pitched >= 20]

        # FIP (lower is better)
        fip_leaders = sorted(qualified, key=lambda x: x[2].fip)[:10]
        self._fill_leader_table_with_record(self.fip_table, fip_leaders,
                                           lambda r: f"{r.fip:.2f}")

        # xFIP (lower is better)
        xfip_leaders = sorted(qualified, key=lambda x: x[2].xfip)[:10]
        self._fill_leader_table_with_record(self.xfip_table, xfip_leaders,
                                           lambda r: f"{r.xfip:.2f}")

        # WHIP (lower is better)
        whip_leaders = sorted(qualified, key=lambda x: x[2].whip)[:10]
        self._fill_leader_table_with_record(self.whip_table, whip_leaders,
                                           lambda r: f"{r.whip:.2f}")

        # K/9 (higher is better)
        k9_leaders = sorted(qualified, key=lambda x: x[2].k_per_9, reverse=True)[:10]
        self._fill_leader_table_with_record(self.k9_table, k9_leaders,
                                           lambda r: f"{r.k_per_9:.2f}")

        # BB/9 (lower is better)
        bb9_leaders = sorted(qualified, key=lambda x: x[2].bb_per_9)[:10]
        self._fill_leader_table_with_record(self.bb9_table, bb9_leaders,
                                           lambda r: f"{r.bb_per_9:.2f}")

        # K/BB (higher is better)
        kbb_leaders = sorted(qualified, key=lambda x: x[2].k_bb_ratio, reverse=True)[:10]
        self._fill_leader_table_with_record(self.kbb_table, kbb_leaders,
                                           lambda r: f"{r.k_bb_ratio:.2f}")

    def _fill_leader_table_with_record(self, table: QTableWidget, leaders: list, value_func):
        """Fill a leader table with record data"""
        table.setRowCount(len(leaders))
        for row, (player, team, record) in enumerate(leaders):
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

            value_item = QTableWidgetItem(value_func(record))
            value_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            value_item.setFont(QFont("", -1, QFont.Bold))
            table.setItem(row, 3, value_item)

    def _update_full_stats_tables(self):
        """Update full player stats tables"""
        if not self.game_state:
            return

        level_filter = self.level_combo.currentIndex()
        league_filter = self.league_combo.currentIndex()

        # Batting
        all_batters = []
        for team in self.game_state.teams:
            if league_filter == 1 and team.league.value != "North League":
                continue
            if league_filter == 2 and team.league.value != "South League":
                continue
            for player in team.players:
                if player.position.value != "投手":
                    record = self._get_player_record(player, level_filter)
                    if record.games > 0:
                        all_batters.append((player, team, record))

        all_batters.sort(key=lambda x: x[2].ops, reverse=True)
        self.full_batting_table.setRowCount(len(all_batters))

        for row, (player, team, record) in enumerate(all_batters):
            avg = record.batting_average
            values = [
                player.name,
                team.name[:6],
                str(record.games),
                f".{int(avg * 1000):03d}" if record.at_bats > 0 else "-",
                f".{int(record.obp * 1000):03d}" if record.plate_appearances > 0 else "-",
                f".{int(record.slg * 1000):03d}" if record.at_bats > 0 else "-",
                f".{int(record.ops * 1000):03d}" if record.plate_appearances > 0 else "-",
                str(record.home_runs),
                str(record.rbis),
                str(record.hits),
                str(record.walks),
                str(record.strikeouts),
                str(record.stolen_bases),
                f".{int(record.woba * 1000):03d}" if record.plate_appearances > 0 else "-",
                f".{int(record.iso * 1000):03d}" if record.at_bats > 0 else "-",
                f".{int(record.babip * 1000):03d}" if record.at_bats > 0 else "-",
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self.full_batting_table.setItem(row, col, item)

        # Pitching
        all_pitchers = []
        for team in self.game_state.teams:
            if league_filter == 1 and team.league.value != "North League":
                continue
            if league_filter == 2 and team.league.value != "South League":
                continue
            for player in team.players:
                if player.position.value == "投手":
                    record = self._get_player_record(player, level_filter)
                    if record.games_pitched > 0:
                        all_pitchers.append((player, team, record))

        all_pitchers.sort(key=lambda x: x[2].innings_pitched, reverse=True)
        self.full_pitching_table.setRowCount(len(all_pitchers))

        for row, (player, team, record) in enumerate(all_pitchers):
            values = [
                player.name,
                team.name[:6],
                str(record.games_pitched),
                str(record.wins),
                str(record.losses),
                str(record.saves),
                f"{record.era:.2f}" if record.innings_pitched > 0 else "-",
                f"{record.innings_pitched:.1f}",
                str(record.strikeouts_pitched),
                str(record.walks_allowed),
                f"{record.whip:.2f}" if record.innings_pitched > 0 else "-",
                f"{record.k_per_9:.2f}" if record.innings_pitched > 0 else "-",
                f"{record.bb_per_9:.2f}" if record.innings_pitched > 0 else "-",
                f"{record.fip:.2f}" if record.innings_pitched > 0 else "-",
                f"{record.xfip:.2f}" if record.innings_pitched > 0 else "-",
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                self.full_pitching_table.setItem(row, col, item)
