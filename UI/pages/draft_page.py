# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Draft Page
Premium Professional Draft System
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QPushButton,
    QComboBox, QProgressBar, QFrame, QScrollArea, QGridLayout,
    QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.charts import RadarChart


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


class PremiumButton(QPushButton):
    """Premium styled button with gradient and effects"""

    def __init__(self, text: str, subtitle: str = "", style: str = "primary", parent=None):
        super().__init__(text, parent)
        self.theme = get_theme()
        self.button_style = style
        self.subtitle = subtitle

        self._setup_style()

    def _setup_style(self):
        if self.button_style == "primary":
            self.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {self.theme.primary},
                        stop:1 {self.theme.accent});
                    color: white;
                    border: none;
                    border-radius: 12px;
                    padding: 16px 32px;
                    font-size: 15px;
                    font-weight: 700;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 {self.theme.accent},
                        stop:1 {self.theme.primary});
                }}
                QPushButton:pressed {{
                    background: {self.theme.primary};
                }}
                QPushButton:disabled {{
                    background: {self.theme.bg_input};
                    color: {self.theme.text_muted};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background: {self.theme.bg_card};
                    color: {self.theme.text_primary};
                    border: 1px solid {self.theme.border};
                    border-radius: 12px;
                    padding: 16px 32px;
                    font-size: 15px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: {self.theme.bg_card_elevated};
                    border-color: {self.theme.primary};
                }}
                QPushButton:pressed {{
                    background: {self.theme.bg_input};
                }}
            """)


class DraftPage(QWidget):
    """Premium styled draft page with prospect scouting and selection"""

    player_drafted = Signal(object)  # Emitted when a player is drafted

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.draft_pool = []
        self.current_round = 1
        self.current_pick = 1
        self.selected_prospect = None

        self._setup_ui()

    def _setup_ui(self):
        """Create the draft page layout"""
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

        title = QLabel("ドラフト会議")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 700;
            color: {self.theme.text_primary};
            background: transparent;
        """)
        title_layout.addWidget(title)

        subtitle = QLabel("Professional Draft")
        subtitle.setStyleSheet(f"""
            font-size: 12px;
            color: {self.theme.text_muted};
            background: transparent;
        """)
        title_layout.addWidget(subtitle)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        # Draft round badge
        self.round_badge = QFrame()
        self.round_badge.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.gold},
                    stop:1 #FFA500);
                border-radius: 8px;
            }}
        """)
        badge_layout = QHBoxLayout(self.round_badge)
        badge_layout.setContentsMargins(16, 8, 16, 8)

        self.round_label = QLabel("第1巡")
        self.round_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 700;
            color: #1a1a1a;
            background: transparent;
        """)
        badge_layout.addWidget(self.round_label)
        header_layout.addWidget(self.round_badge)

        main_layout.addWidget(header_frame)

        # Main content splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {self.theme.border};
                width: 2px;
            }}
        """)

        # Left side - Available prospects
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # Filter controls
        filter_frame = QFrame()
        filter_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border: 1px solid {self.theme.border_muted};
                border-radius: 8px;
            }}
        """)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(12, 8, 12, 8)

        position_label = QLabel("ポジション:")
        position_label.setStyleSheet(f"color: {self.theme.text_secondary}; background: transparent;")
        filter_layout.addWidget(position_label)

        self.position_filter = QComboBox()
        self.position_filter.addItems(["全て", "投手", "捕手", "内野手", "外野手"])
        self.position_filter.setStyleSheet(f"""
            QComboBox {{
                background: {self.theme.bg_input};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 100px;
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
        self.position_filter.currentIndexChanged.connect(self._filter_prospects)
        filter_layout.addWidget(self.position_filter)

        filter_layout.addSpacing(16)

        sort_label = QLabel("並び替え:")
        sort_label.setStyleSheet(f"color: {self.theme.text_secondary}; background: transparent;")
        filter_layout.addWidget(sort_label)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["総合力", "ポテンシャル", "年齢", "名前"])
        self.sort_combo.setStyleSheet(f"""
            QComboBox {{
                background: {self.theme.bg_input};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 6px;
                padding: 6px 12px;
                min-width: 100px;
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
        self.sort_combo.currentIndexChanged.connect(self._sort_prospects)
        filter_layout.addWidget(self.sort_combo)

        filter_layout.addStretch()
        left_layout.addWidget(filter_frame)

        # Prospects table
        prospects_card = PremiumCard("ドラフト候補選手", "")

        self.prospects_table = QTableWidget()
        self.prospects_table.setColumnCount(7)
        self.prospects_table.setHorizontalHeaderLabels([
            "名前", "ポジション", "年齢", "投/打", "総合", "潜在", "出身"
        ])

        self.prospects_table.setStyleSheet(f"""
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

        header = self.prospects_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 7):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        self.prospects_table.verticalHeader().setVisible(False)
        self.prospects_table.verticalHeader().setDefaultSectionSize(40)
        self.prospects_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.prospects_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.prospects_table.setSelectionMode(QTableWidget.SingleSelection)
        self.prospects_table.setShowGrid(False)
        self.prospects_table.itemSelectionChanged.connect(self._on_prospect_selected)

        prospects_card.add_widget(self.prospects_table)
        left_layout.addWidget(prospects_card)

        splitter.addWidget(left_widget)

        # Right side - Scout report
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Scout report card
        self.scout_card = PremiumCard("スカウトレポート", "")

        # Player info
        self.scout_name = QLabel("選手を選択してください")
        self.scout_name.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 700;
            color: {self.theme.text_primary};
            background: transparent;
        """)
        self.scout_card.add_widget(self.scout_name)

        # Position/Age info
        self.scout_info = QLabel("")
        self.scout_info.setStyleSheet(f"""
            font-size: 14px;
            color: {self.theme.text_secondary};
            margin-bottom: 16px;
            background: transparent;
        """)
        self.scout_card.add_widget(self.scout_info)

        # Radar chart for abilities
        self.radar_chart = RadarChart()
        self.radar_chart.setFixedHeight(220)
        self.scout_card.add_widget(self.radar_chart)

        # Attributes grid
        self.attrs_widget = QWidget()
        self.attrs_widget.setStyleSheet("background: transparent;")
        attrs_layout = QGridLayout(self.attrs_widget)
        attrs_layout.setSpacing(8)

        self.attr_labels = {}
        attrs = [
            ("球速", 0, 0), ("変化球", 0, 1), ("コントロール", 0, 2),
            ("スタミナ", 1, 0), ("ミート", 1, 1), ("パワー", 1, 2),
            ("走力", 2, 0), ("肩力", 2, 1), ("守備力", 2, 2)
        ]

        for name, row, col in attrs:
            container = QFrame()
            container.setStyleSheet(f"""
                QFrame {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {self.theme.bg_card_elevated},
                        stop:1 {self.theme.bg_input});
                    border-radius: 8px;
                    border: 1px solid {self.theme.border_muted};
                }}
            """)
            v_layout = QVBoxLayout(container)
            v_layout.setContentsMargins(10, 6, 10, 6)
            v_layout.setSpacing(2)

            label = QLabel(name)
            label.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 10px; background: transparent;")
            v_layout.addWidget(label)

            value = QLabel("--")
            value.setStyleSheet(f"color: {self.theme.text_primary}; font-size: 16px; font-weight: 700; background: transparent;")
            v_layout.addWidget(value)

            self.attr_labels[name] = value
            attrs_layout.addWidget(container, row, col)

        self.scout_card.add_widget(self.attrs_widget)

        # Scout notes
        self.scout_notes = QLabel("")
        self.scout_notes.setWordWrap(True)
        self.scout_notes.setStyleSheet(f"""
            color: {self.theme.text_secondary};
            font-size: 13px;
            padding: 12px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {self.theme.bg_input},
                stop:1 {self.theme.bg_card});
            border-radius: 8px;
            border: 1px solid {self.theme.border_muted};
        """)
        self.scout_card.add_widget(self.scout_notes)

        right_layout.addWidget(self.scout_card)

        # Draft button
        self.draft_button = PremiumButton("この選手を指名", "ドラフト1巡目指名", "primary")
        self.draft_button.clicked.connect(self._draft_player)
        self.draft_button.setEnabled(False)
        right_layout.addWidget(self.draft_button)

        splitter.addWidget(right_widget)
        splitter.setSizes([550, 450])

        main_layout.addWidget(splitter)

        # Draft order section
        order_card = PremiumCard("指名順", "")

        self.order_scroll = QScrollArea()
        self.order_scroll.setWidgetResizable(True)
        self.order_scroll.setMaximumHeight(80)
        self.order_scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """)

        self.order_widget = QWidget()
        self.order_widget.setStyleSheet("background: transparent;")
        self.order_layout = QHBoxLayout(self.order_widget)
        self.order_layout.setSpacing(8)
        self.order_layout.setContentsMargins(0, 0, 0, 0)
        self.order_scroll.setWidget(self.order_widget)

        order_card.add_widget(self.order_scroll)
        main_layout.addWidget(order_card)

    def set_game_state(self, game_state):
        """Update with game state"""
        self.game_state = game_state
        if not game_state:
            return

        self._generate_draft_pool()
        self._update_draft_order()
        self._update_prospects_table()

    def _generate_draft_pool(self):
        """Generate draft prospects"""
        if not self.game_state:
            return

        import random

        positions = ["投手", "捕手", "一塁手", "二塁手", "三塁手", "遊撃手", "外野手"]
        origins = ["大学", "高校", "社会人", "独立リーグ"]
        throws = ["右", "左"]
        bats = ["右", "左", "両"]

        self.draft_pool = []

        surnames = ["田中", "鈴木", "佐藤", "山田", "伊藤", "高橋", "渡辺", "中村", "小林", "加藤",
                   "吉田", "山本", "松本", "井上", "木村", "林", "斎藤", "清水", "山口", "森"]
        first_names = ["大翔", "翔太", "健太", "拓也", "雄太", "達也", "和也", "直樹", "亮", "太郎",
                      "一郎", "二郎", "俊介", "慎吾", "剛", "翼", "颯", "蓮", "陽", "海"]

        for i in range(60):
            name = random.choice(surnames) + " " + random.choice(first_names)
            position = random.choice(positions)
            age = random.randint(18, 23)
            throw = random.choice(throws)
            bat = random.choice(bats)
            overall = random.randint(35, 70)
            potential = random.randint(overall, min(99, overall + 30))
            origin = random.choice(origins)

            # Generate abilities
            if position == "投手":
                abilities = {
                    "球速": random.randint(40, 80),
                    "変化球": random.randint(30, 75),
                    "コントロール": random.randint(30, 70),
                    "スタミナ": random.randint(40, 75),
                    "ミート": random.randint(10, 30),
                    "パワー": random.randint(10, 30),
                    "走力": random.randint(20, 50),
                    "肩力": random.randint(50, 80),
                    "守備力": random.randint(30, 60)
                }
            else:
                abilities = {
                    "球速": random.randint(20, 50),
                    "変化球": random.randint(10, 30),
                    "コントロール": random.randint(10, 30),
                    "スタミナ": random.randint(30, 60),
                    "ミート": random.randint(35, 80),
                    "パワー": random.randint(35, 85),
                    "走力": random.randint(40, 80),
                    "肩力": random.randint(40, 75),
                    "守備力": random.randint(40, 75)
                }

            prospect = {
                "name": name,
                "position": position,
                "age": age,
                "throw": throw,
                "bat": bat,
                "overall": overall,
                "potential": potential,
                "origin": origin,
                "abilities": abilities
            }
            self.draft_pool.append(prospect)

        self.draft_pool.sort(key=lambda x: x["overall"], reverse=True)

    def _update_draft_order(self):
        """Update the draft order display"""
        while self.order_layout.count():
            item = self.order_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.game_state:
            return

        teams = sorted(self.game_state.teams,
                      key=lambda t: (t.wins / max(1, t.wins + t.losses)))

        for i, team in enumerate(teams):
            is_current = (i == self.current_pick - 1)

            team_frame = QFrame()
            team_frame.setStyleSheet(f"""
                QFrame {{
                    background: {'qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 ' + self.theme.primary + ', stop:1 ' + self.theme.accent + ')' if is_current else self.theme.bg_card};
                    border-radius: 8px;
                    border: 1px solid {self.theme.primary if is_current else self.theme.border_muted};
                    padding: 4px;
                }}
            """)
            frame_layout = QVBoxLayout(team_frame)
            frame_layout.setContentsMargins(12, 6, 12, 6)
            frame_layout.setSpacing(2)

            pick_label = QLabel(f"#{i + 1}")
            pick_label.setStyleSheet(f"""
                font-size: 10px;
                color: {'white' if is_current else self.theme.text_muted};
                background: transparent;
            """)
            frame_layout.addWidget(pick_label)

            from models import TEAM_ABBRS
            team_abbr = TEAM_ABBRS.get(team.name, team.name[:4])
            team_label = QLabel(team_abbr)
            team_label.setStyleSheet(f"""
                font-size: 12px;
                font-weight: {'700' if is_current else '500'};
                color: {'white' if is_current else self.theme.text_primary};
                background: transparent;
            """)
            frame_layout.addWidget(team_label)

            self.order_layout.addWidget(team_frame)

        self.order_layout.addStretch()

    def _update_prospects_table(self):
        """Update the prospects table"""
        self.prospects_table.setRowCount(len(self.draft_pool))

        for row, prospect in enumerate(self.draft_pool):
            # Name
            name_item = QTableWidgetItem(prospect["name"])
            name_item.setData(Qt.UserRole, prospect)
            name_item.setFont(QFont("", -1, QFont.Bold))
            self.prospects_table.setItem(row, 0, name_item)

            # Position
            pos_item = QTableWidgetItem(prospect["position"])
            pos_item.setTextAlignment(Qt.AlignCenter)
            self.prospects_table.setItem(row, 1, pos_item)

            # Age
            age_item = QTableWidgetItem(str(prospect["age"]))
            age_item.setTextAlignment(Qt.AlignCenter)
            self.prospects_table.setItem(row, 2, age_item)

            # Throw/Bat
            tb_item = QTableWidgetItem(f"{prospect['throw']}/{prospect['bat']}")
            tb_item.setTextAlignment(Qt.AlignCenter)
            self.prospects_table.setItem(row, 3, tb_item)

            # Overall
            ovr_item = QTableWidgetItem(str(prospect["overall"]))
            ovr_item.setTextAlignment(Qt.AlignCenter)
            ovr_item.setForeground(QBrush(QColor(self._get_rating_color(prospect["overall"]))))
            font = QFont()
            font.setBold(True)
            ovr_item.setFont(font)
            self.prospects_table.setItem(row, 4, ovr_item)

            # Potential
            pot_item = QTableWidgetItem(str(prospect["potential"]))
            pot_item.setTextAlignment(Qt.AlignCenter)
            pot_item.setForeground(QBrush(QColor(self._get_rating_color(prospect["potential"]))))
            self.prospects_table.setItem(row, 5, pot_item)

            # Origin
            origin_item = QTableWidgetItem(prospect["origin"])
            origin_item.setTextAlignment(Qt.AlignCenter)
            self.prospects_table.setItem(row, 6, origin_item)

    def _get_rating_color(self, rating: int) -> str:
        """Get color for rating value"""
        if rating >= 80:
            return self.theme.rating_s
        elif rating >= 70:
            return self.theme.rating_a
        elif rating >= 60:
            return self.theme.rating_b
        elif rating >= 50:
            return self.theme.rating_c
        elif rating >= 40:
            return self.theme.rating_d
        else:
            return self.theme.rating_e

    def _on_prospect_selected(self):
        """Handle prospect selection"""
        selected = self.prospects_table.selectedItems()
        if not selected:
            self.selected_prospect = None
            self.draft_button.setEnabled(False)
            return

        row = selected[0].row()
        self.selected_prospect = self.prospects_table.item(row, 0).data(Qt.UserRole)
        self._update_scout_report()
        self.draft_button.setEnabled(True)

    def _update_scout_report(self):
        """Update the scout report panel"""
        if not self.selected_prospect:
            self.scout_name.setText("選手を選択してください")
            self.scout_info.setText("")
            self.scout_notes.setText("")
            return

        p = self.selected_prospect

        self.scout_name.setText(p["name"])
        self.scout_info.setText(
            f"{p['position']} | {p['age']}歳 | {p['throw']}投{p['bat']}打 | {p['origin']}"
        )

        # Update radar chart
        if p["position"] == "投手":
            abilities = [
                p["abilities"]["球速"],
                p["abilities"]["変化球"],
                p["abilities"]["コントロール"],
                p["abilities"]["スタミナ"],
                p["abilities"]["守備力"]
            ]
            labels = ["球速", "変化球", "制球", "スタミナ", "守備"]
        else:
            abilities = [
                p["abilities"]["ミート"],
                p["abilities"]["パワー"],
                p["abilities"]["走力"],
                p["abilities"]["肩力"],
                p["abilities"]["守備力"]
            ]
            labels = ["ミート", "パワー", "走力", "肩力", "守備"]

        self.radar_chart.set_data(abilities, labels)

        # Update attribute labels
        for name, label in self.attr_labels.items():
            if name in p["abilities"]:
                value = p["abilities"][name]
                label.setText(str(value))
                label.setStyleSheet(f"""
                    color: {self._get_rating_color(value)};
                    font-size: 16px;
                    font-weight: 700;
                    background: transparent;
                """)

        # Generate scout notes
        notes = self._generate_scout_notes(p)
        self.scout_notes.setText(notes)

    def _generate_scout_notes(self, prospect: dict) -> str:
        """Generate scout notes for a prospect"""
        notes = []

        if prospect["position"] == "投手":
            if prospect["abilities"]["球速"] >= 70:
                notes.append("速球派で、最速150km/h超の可能性。")
            if prospect["abilities"]["変化球"] >= 65:
                notes.append("変化球のキレが良く、決め球として使える。")
            if prospect["abilities"]["コントロール"] >= 65:
                notes.append("制球力が高く、四球が少ない。")
            if prospect["abilities"]["スタミナ"] >= 65:
                notes.append("体力があり、先発完投も期待できる。")
        else:
            if prospect["abilities"]["ミート"] >= 70:
                notes.append("バットコントロールが優秀で、高打率が期待できる。")
            if prospect["abilities"]["パワー"] >= 70:
                notes.append("長打力があり、ホームランバッターとしての素質あり。")
            if prospect["abilities"]["走力"] >= 70:
                notes.append("足が速く、盗塁や守備範囲で貢献できる。")
            if prospect["abilities"]["守備力"] >= 65:
                notes.append("守備が堅実で、失策が少ない。")

        # Potential assessment
        gap = prospect["potential"] - prospect["overall"]
        if gap >= 25:
            notes.append(f"伸びしろが大きく、将来は{prospect['potential']}クラスまで成長する可能性。")
        elif gap >= 15:
            notes.append("順調に成長すれば、レギュラークラスに成長する素材。")

        if not notes:
            notes.append("平均的な選手。特筆すべき点は少ないが、堅実なプレーが期待できる。")

        return " ".join(notes)

    def _filter_prospects(self):
        """Filter prospects by position"""
        filter_text = self.position_filter.currentText()

        for row in range(self.prospects_table.rowCount()):
            pos_item = self.prospects_table.item(row, 1)
            if not pos_item:
                continue

            position = pos_item.text()

            if filter_text == "全て":
                self.prospects_table.setRowHidden(row, False)
            elif filter_text == "投手":
                self.prospects_table.setRowHidden(row, position != "投手")
            elif filter_text == "捕手":
                self.prospects_table.setRowHidden(row, position != "捕手")
            elif filter_text == "内野手":
                self.prospects_table.setRowHidden(row, position not in ["一塁手", "二塁手", "三塁手", "遊撃手"])
            elif filter_text == "外野手":
                self.prospects_table.setRowHidden(row, position != "外野手")

    def _sort_prospects(self):
        """Sort prospects by selected criteria"""
        sort_key = self.sort_combo.currentText()

        if sort_key == "総合力":
            self.draft_pool.sort(key=lambda x: x["overall"], reverse=True)
        elif sort_key == "ポテンシャル":
            self.draft_pool.sort(key=lambda x: x["potential"], reverse=True)
        elif sort_key == "年齢":
            self.draft_pool.sort(key=lambda x: x["age"])
        elif sort_key == "名前":
            self.draft_pool.sort(key=lambda x: x["name"])

        self._update_prospects_table()

    def _draft_player(self):
        """Draft the selected player"""
        if not self.selected_prospect:
            return

        # Remove from pool
        self.draft_pool.remove(self.selected_prospect)

        # Emit signal
        self.player_drafted.emit(self.selected_prospect)

        # Update display
        self._update_prospects_table()
        self.selected_prospect = None
        self._update_scout_report()
        self.draft_button.setEnabled(False)

        # Move to next pick
        self.current_pick += 1
        if self.current_pick > 12:  # 12 teams
            self.current_round += 1
            self.current_pick = 1
            self.round_label.setText(f"第{self.current_round}巡")

        self._update_draft_order()
