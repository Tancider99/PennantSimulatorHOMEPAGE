# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Trade Page
OOTP-Style Premium Professional Trade System
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QPushButton,
    QComboBox, QFrame, QScrollArea, QMessageBox, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.cards import PremiumCard


class TradePackage(QFrame):
    """Premium styled widget displaying one side of a trade"""

    player_added = Signal(object)
    player_removed = Signal(object)

    def __init__(self, team_name: str, is_user_team: bool = False, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.team_name = team_name
        self.is_user_team = is_user_team
        self.players = []

        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated},
                    stop:1 {self.theme.bg_card});
                border: 1px solid {self.theme.border};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 12)
        layout.setSpacing(0)

        # Team header
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.primary if self.is_user_team else self.theme.accent},
                    stop:1 {self.theme.accent if self.is_user_team else self.theme.primary});
                border-radius: 12px 12px 0 0;
                border: none;
            }}
        """)
        header.setFixedHeight(40)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)

        self.header_label = QLabel(self.team_name)
        self.header_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: white;
            background: transparent;
        """)
        header_layout.addWidget(self.header_label)

        layout.addWidget(header)

        # Players list
        self.players_widget = QWidget()
        self.players_widget.setStyleSheet("background: transparent;")
        self.players_layout = QVBoxLayout(self.players_widget)
        self.players_layout.setContentsMargins(12, 12, 12, 12)
        self.players_layout.setSpacing(6)

        self.empty_label = QLabel("選手をダブルクリックして追加")
        self.empty_label.setStyleSheet(f"""
            color: {self.theme.text_muted};
            font-style: italic;
            padding: 20px;
            background: transparent;
        """)
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.players_layout.addWidget(self.empty_label)

        self.players_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(self.players_widget)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(180)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: transparent;
            }}
        """)
        layout.addWidget(scroll)

        # Value indicator
        value_frame = QFrame()
        value_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_input};
                border-radius: 6px;
                margin: 0 12px;
            }}
        """)
        value_layout = QHBoxLayout(value_frame)
        value_layout.setContentsMargins(12, 8, 12, 8)

        value_icon = QLabel("Value")
        value_icon.setStyleSheet("background: transparent; color: {self.theme.text_muted};")
        value_layout.addWidget(value_icon)

        self.value_label = QLabel("トレード価値: 0")
        self.value_label.setStyleSheet(f"""
            color: {self.theme.text_secondary};
            font-size: 13px;
            font-weight: 600;
            background: transparent;
        """)
        value_layout.addWidget(self.value_label)
        value_layout.addStretch()

        layout.addWidget(value_frame)

    def set_team(self, team_name: str):
        """Set the team name"""
        self.team_name = team_name
        self.header_label.setText(team_name)

    def add_player(self, player):
        """Add a player to the trade package"""
        if player in self.players:
            return

        self.players.append(player)
        self.empty_label.hide()

        # Create player widget
        player_frame = QFrame()
        player_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated},
                    stop:1 {self.theme.bg_input});
                border-radius: 8px;
                border: 1px solid {self.theme.border_muted};
            }}
            QFrame:hover {{
                border-color: {self.theme.primary};
            }}
        """)
        player_frame.setProperty("player", player)

        h_layout = QHBoxLayout(player_frame)
        h_layout.setContentsMargins(12, 8, 12, 8)

        name_label = QLabel(f"{player.name} ({player.position.value})")
        name_label.setStyleSheet(f"color: {self.theme.text_primary}; background: transparent; font-weight: 600;")
        h_layout.addWidget(name_label)

        h_layout.addStretch()

        # Overall rating
        overall = self._calculate_overall(player)
        overall_label = QLabel(str(overall))
        overall_label.setStyleSheet(f"""
            color: {self._get_rating_color(overall)};
            font-weight: 700;
            font-size: 14px;
            background: transparent;
        """)
        h_layout.addWidget(overall_label)

        # Remove button
        if self.is_user_team:
            remove_btn = QPushButton("×")
            remove_btn.setFixedSize(24, 24)
            remove_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {self.theme.danger};
                    color: white;
                    border: none;
                    border-radius: 12px;
                    font-weight: bold;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background: #ff6b6b;
                }}
            """)
            remove_btn.clicked.connect(lambda: self.remove_player(player))
            h_layout.addWidget(remove_btn)

        # Insert before stretch
        self.players_layout.insertWidget(self.players_layout.count() - 1, player_frame)

        self._update_value()
        self.player_added.emit(player)

    def remove_player(self, player):
        """Remove a player from the trade package"""
        if player not in self.players:
            return

        self.players.remove(player)

        # Find and remove the widget
        for i in range(self.players_layout.count()):
            widget = self.players_layout.itemAt(i).widget()
            if widget and widget.property("player") == player:
                widget.deleteLater()
                break

        if not self.players:
            self.empty_label.show()

        self._update_value()
        self.player_removed.emit(player)

    def clear(self):
        """Clear all players"""
        for player in list(self.players):
            self.remove_player(player)

    def _calculate_overall(self, player) -> int:
        """Calculate player's overall rating"""
        stats = player.stats
        if player.position.value == "投手":
            return int((stats.speed + stats.breaking + stats.control + stats.stamina) / 4)
        else:
            return int((stats.contact + stats.power + stats.run + stats.arm + stats.fielding) / 5)

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

    def _update_value(self):
        """Update the trade value display"""
        total_value = sum(self._calculate_overall(p) for p in self.players)
        self.value_label.setText(f"トレード価値: {total_value}")

    def get_trade_value(self) -> int:
        """Get total trade value"""
        return sum(self._calculate_overall(p) for p in self.players)


class TradePage(QWidget):
    """Premium styled trade page with player trading interface"""

    trade_completed = Signal(list, list)  # user_players, other_players

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.user_team = None
        self.trade_partner = None

        self._setup_ui()

    def _setup_ui(self):
        """Create the trade page layout"""
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

        title = QLabel("トレード")
        title.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 700;
            color: {self.theme.text_primary};
            background: transparent;
        """)
        title_layout.addWidget(title)

        subtitle = QLabel("Player Trade System")
        subtitle.setStyleSheet(f"""
            font-size: 12px;
            color: {self.theme.text_muted};
            background: transparent;
        """)
        title_layout.addWidget(subtitle)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        # Trade partner selector
        partner_frame = QFrame()
        partner_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_input};
                border-radius: 8px;
                border: 1px solid {self.theme.border_muted};
            }}
        """)
        partner_layout = QHBoxLayout(partner_frame)
        partner_layout.setContentsMargins(12, 8, 12, 8)

        partner_label = QLabel("トレード相手:")
        partner_label.setStyleSheet(f"color: {self.theme.text_secondary}; background: transparent;")
        partner_layout.addWidget(partner_label)

        self.partner_combo = QComboBox()
        self.partner_combo.setMinimumWidth(180)
        self.partner_combo.setStyleSheet(f"""
            QComboBox {{
                background: {self.theme.bg_card};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 6px;
                padding: 6px 12px;
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
        self.partner_combo.currentIndexChanged.connect(self._on_partner_changed)
        partner_layout.addWidget(self.partner_combo)

        header_layout.addWidget(partner_frame)
        main_layout.addWidget(header_frame)

        # Main trade interface
        trade_splitter = QSplitter(Qt.Horizontal)
        trade_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {self.theme.border};
                width: 2px;
            }}
        """)

        # Left side - User team players
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        # User team roster
        self.user_roster_card = PremiumCard("自チームロスター", "")

        self.user_roster_table = self._create_roster_table()
        self.user_roster_table.itemDoubleClicked.connect(self._add_user_player)
        self.user_roster_card.add_widget(self.user_roster_table)

        left_layout.addWidget(self.user_roster_card)

        # User trade package
        self.user_package = TradePackage("", is_user_team=True)
        left_layout.addWidget(self.user_package)

        trade_splitter.addWidget(left_widget)

        # Center - Trade controls
        center_widget = QWidget()
        center_widget.setFixedWidth(140)
        center_layout = QVBoxLayout(center_widget)
        center_layout.setAlignment(Qt.AlignCenter)
        center_layout.setSpacing(16)

        center_layout.addStretch()

        # Trade arrow/indicator
        arrow_frame = QFrame()
        arrow_frame.setStyleSheet(f"""
            QFrame {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated},
                    stop:1 {self.theme.bg_card});
                border-radius: 20px;
                border: 1px solid {self.theme.border};
            }}
        """)
        arrow_frame.setFixedSize(80, 80)
        arrow_layout = QVBoxLayout(arrow_frame)
        arrow_layout.setAlignment(Qt.AlignCenter)

        arrow_label = QLabel("⇌")
        arrow_label.setStyleSheet(f"""
            font-size: 36px;
            color: {self.theme.accent};
            background: transparent;
        """)
        arrow_label.setAlignment(Qt.AlignCenter)
        arrow_layout.addWidget(arrow_label)

        center_layout.addWidget(arrow_frame, alignment=Qt.AlignCenter)

        # Trade fairness indicator
        self.fairness_frame = QFrame()
        self.fairness_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border-radius: 8px;
                border: 1px solid {self.theme.success};
            }}
        """)
        fairness_layout = QVBoxLayout(self.fairness_frame)
        fairness_layout.setContentsMargins(12, 8, 12, 8)

        self.fairness_label = QLabel("公平")
        self.fairness_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {self.theme.success};
            background: transparent;
        """)
        self.fairness_label.setAlignment(Qt.AlignCenter)
        fairness_layout.addWidget(self.fairness_label)

        center_layout.addWidget(self.fairness_frame)

        center_layout.addStretch()

        # Execute trade button
        self.execute_btn = QPushButton("トレード実行")
        self.execute_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.primary},
                    stop:1 {self.theme.accent});
                color: white;
                border: none;
                border-radius: 10px;
                padding: 14px 20px;
                font-size: 14px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.theme.accent},
                    stop:1 {self.theme.primary});
            }}
            QPushButton:disabled {{
                background: {self.theme.bg_input};
                color: {self.theme.text_muted};
            }}
        """)
        self.execute_btn.clicked.connect(self._execute_trade)
        self.execute_btn.setEnabled(False)
        center_layout.addWidget(self.execute_btn)

        # Reset button
        reset_btn = QPushButton("リセット")
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.bg_card};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 10px;
                padding: 12px 20px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {self.theme.bg_card_elevated};
                border-color: {self.theme.primary};
            }}
        """)
        reset_btn.clicked.connect(self._reset_trade)
        center_layout.addWidget(reset_btn)

        center_layout.addStretch()

        trade_splitter.addWidget(center_widget)

        # Right side - Trade partner players
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Partner team roster
        self.partner_roster_card = PremiumCard("相手チームロスター", "")

        self.partner_roster_table = self._create_roster_table()
        self.partner_roster_table.itemDoubleClicked.connect(self._add_partner_player)
        self.partner_roster_card.add_widget(self.partner_roster_table)

        right_layout.addWidget(self.partner_roster_card)

        # Partner trade package
        self.partner_package = TradePackage("")
        right_layout.addWidget(self.partner_package)

        trade_splitter.addWidget(right_widget)

        trade_splitter.setSizes([400, 140, 400])
        main_layout.addWidget(trade_splitter)

        # Connect value change signals
        self.user_package.player_added.connect(self._update_fairness)
        self.user_package.player_removed.connect(self._update_fairness)
        self.partner_package.player_added.connect(self._update_fairness)
        self.partner_package.player_removed.connect(self._update_fairness)

    def _create_roster_table(self) -> QTableWidget:
        """Create a premium styled roster table"""
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["名前", "ポジション", "年齢", "総合", "年俸"])

        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                border: none;
                gridline-color: transparent;
            }}
            QTableWidget::item {{
                padding: 6px;
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
                padding: 8px 6px;
                border: none;
                border-bottom: 2px solid {self.theme.primary};
            }}
        """)

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(36)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setShowGrid(False)

        return table

    def set_game_state(self, game_state):
        """Update with game state"""
        self.game_state = game_state
        if not game_state:
            return

        # Set user team
        self.user_team = game_state.teams[0]  # Assuming first team is user's
        self.user_package.set_team(self.user_team.name)

        # Populate partner combo
        self.partner_combo.clear()
        for team in game_state.teams:
            if team != self.user_team:
                self.partner_combo.addItem(team.name, team)

        self._update_user_roster()

    def _on_partner_changed(self):
        """Handle trade partner change"""
        self.trade_partner = self.partner_combo.currentData()
        if self.trade_partner:
            self.partner_package.set_team(self.trade_partner.name)
            self.partner_roster_card.set_title(f"{self.trade_partner.name}ロスター")
            self._update_partner_roster()
            self._reset_trade()

    def _update_user_roster(self):
        """Update user team roster table"""
        if not self.user_team:
            return

        self._fill_roster_table(self.user_roster_table, self.user_team.players)

    def _update_partner_roster(self):
        """Update partner team roster table"""
        if not self.trade_partner:
            return

        self._fill_roster_table(self.partner_roster_table, self.trade_partner.players)

    def _fill_roster_table(self, table: QTableWidget, players: list):
        """Fill a roster table with players"""
        table.setRowCount(len(players))

        for row, player in enumerate(players):
            # Name
            name_item = QTableWidgetItem(player.name)
            name_item.setData(Qt.UserRole, player)
            name_item.setFont(QFont("", -1, QFont.Bold))
            table.setItem(row, 0, name_item)

            # Position
            pos_item = QTableWidgetItem(player.position.value)
            pos_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 1, pos_item)

            # Age
            age_item = QTableWidgetItem(str(player.age))
            age_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 2, age_item)

            # Overall
            overall = self._calculate_overall(player)
            ovr_item = QTableWidgetItem(str(overall))
            ovr_item.setTextAlignment(Qt.AlignCenter)
            ovr_item.setForeground(QBrush(QColor(self._get_rating_color(overall))))
            font = QFont()
            font.setBold(True)
            ovr_item.setFont(font)
            table.setItem(row, 3, ovr_item)

            # Salary
            salary_item = QTableWidgetItem(f"¥{player.salary:,}")
            salary_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 4, salary_item)

    def _calculate_overall(self, player) -> int:
        """Calculate player's overall rating"""
        stats = player.stats
        if player.position.value == "投手":
            return int((stats.speed + stats.breaking + stats.control + stats.stamina) / 4)
        else:
            return int((stats.contact + stats.power + stats.run + stats.arm + stats.fielding) / 5)

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

    def _add_user_player(self, item):
        """Add user player to trade package"""
        row = item.row()
        player = self.user_roster_table.item(row, 0).data(Qt.UserRole)
        if player and player not in self.user_package.players:
            self.user_package.add_player(player)

    def _add_partner_player(self, item):
        """Add partner player to trade package"""
        row = item.row()
        player = self.partner_roster_table.item(row, 0).data(Qt.UserRole)
        if player and player not in self.partner_package.players:
            self.partner_package.add_player(player)

    def _update_fairness(self):
        """Update trade fairness indicator"""
        user_value = self.user_package.get_trade_value()
        partner_value = self.partner_package.get_trade_value()

        if user_value == 0 and partner_value == 0:
            self.fairness_label.setText("選手を選択")
            self.fairness_frame.setStyleSheet(f"""
                QFrame {{
                    background: {self.theme.bg_card};
                    border-radius: 8px;
                    border: 1px solid {self.theme.border_muted};
                }}
            """)
            self.fairness_label.setStyleSheet(f"""
                font-size: 14px;
                font-weight: 700;
                color: {self.theme.text_muted};
                background: transparent;
            """)
            self.execute_btn.setEnabled(False)
            return

        # Calculate fairness
        if user_value == 0 or partner_value == 0:
            ratio = 0
        else:
            ratio = min(user_value, partner_value) / max(user_value, partner_value)

        if ratio >= 0.8:
            fairness_text = "FAIR"
            fairness_color = self.theme.success
            border_color = self.theme.success
            can_trade = True
        elif ratio >= 0.6:
            fairness_text = "UNEVEN"
            fairness_color = self.theme.warning
            border_color = self.theme.warning
            can_trade = True
        else:
            if user_value > partner_value:
                fairness_text = "BAD DEAL"
            else:
                fairness_text = "REJECTED"
            fairness_color = self.theme.danger
            border_color = self.theme.danger
            can_trade = user_value > partner_value  # Can still accept bad deals

        self.fairness_label.setText(fairness_text)
        self.fairness_frame.setStyleSheet(f"""
            QFrame {{
                background: {self.theme.bg_card};
                border-radius: 8px;
                border: 2px solid {border_color};
            }}
        """)
        self.fairness_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {fairness_color};
            background: transparent;
        """)

        # Enable execute button if both sides have players
        self.execute_btn.setEnabled(
            can_trade and
            len(self.user_package.players) > 0 and
            len(self.partner_package.players) > 0
        )

    def _execute_trade(self):
        """Execute the trade"""
        if not self.user_team or not self.trade_partner:
            return

        user_players = list(self.user_package.players)
        partner_players = list(self.partner_package.players)

        if not user_players or not partner_players:
            return

        # Confirm dialog
        user_names = ", ".join(p.name for p in user_players)
        partner_names = ", ".join(p.name for p in partner_players)

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Question)
        msg.setWindowTitle("トレード確認")
        msg.setText(f"以下のトレードを実行しますか？\n\n"
                   f"放出: {user_names}\n"
                   f"獲得: {partner_names}")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        if msg.exec_() == QMessageBox.Yes:
            # Execute trade
            for player in user_players:
                self.user_team.players.remove(player)
                self.trade_partner.players.append(player)

            for player in partner_players:
                self.trade_partner.players.remove(player)
                self.user_team.players.append(player)

            # Emit signal
            self.trade_completed.emit(user_players, partner_players)

            # Reset and refresh
            self._reset_trade()
            self._update_user_roster()
            self._update_partner_roster()

            # Show success message
            QMessageBox.information(
                self, "トレード完了",
                f"{partner_names}を獲得しました！"
            )

    def _reset_trade(self):
        """Reset the trade"""
        self.user_package.clear()
        self.partner_package.clear()
        self._update_fairness()
