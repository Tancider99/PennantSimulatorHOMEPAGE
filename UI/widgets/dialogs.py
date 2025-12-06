# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Dialog Widgets
OOTP-Style Modal Dialogs and Popups
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QFrame, QGraphicsDropShadowEffect, QMessageBox,
    QLineEdit, QComboBox, QSpinBox, QTextEdit
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

import sys
sys.path.insert(0, '..')
from UI.theme import get_theme


class BaseDialog(QDialog):
    """Base dialog with OOTP styling"""

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._title = title

        self.setWindowTitle(title)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self._setup_ui()

    def _setup_ui(self):
        # Main container
        self.container = QFrame(self)
        self.container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 12px;
            }}
        """)

        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 10)
        self.container.setGraphicsEffect(shadow)

        # Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)

        self.content_layout = QVBoxLayout(self.container)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.setSpacing(20)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel(self._title)
        title_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 600;
            color: {self.theme.text_primary};
        """)
        header_layout.addWidget(title_label)

        header_layout.addStretch()

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.theme.text_muted};
                border: none;
                border-radius: 16px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.danger};
                color: white;
            }}
        """)
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)

        self.content_layout.addLayout(header_layout)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"background-color: {self.theme.border};")
        separator.setFixedHeight(1)
        self.content_layout.addWidget(separator)

        # Content area
        self.body_layout = QVBoxLayout()
        self.body_layout.setSpacing(16)
        self.content_layout.addLayout(self.body_layout)

        # Button area
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(12)
        self.content_layout.addLayout(self.button_layout)

    def add_content(self, widget: QWidget):
        """Add widget to dialog body"""
        self.body_layout.addWidget(widget)

    def add_button(self, text: str, style: str = "default", callback=None) -> QPushButton:
        """Add a button to the dialog"""
        btn = QPushButton(text)
        btn.setMinimumHeight(40)
        btn.setCursor(Qt.PointingHandCursor)

        if style == "primary":
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme.primary};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 24px;
                    font-size: 14px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {self.theme.primary_hover};
                }}
            """)
        elif style == "danger":
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme.danger};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 24px;
                    font-size: 14px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {self.theme.danger_hover};
                }}
            """)
        else:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme.bg_input};
                    color: {self.theme.text_primary};
                    border: 1px solid {self.theme.border};
                    border-radius: 6px;
                    padding: 10px 24px;
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: {self.theme.bg_card_hover};
                }}
            """)

        if callback:
            btn.clicked.connect(callback)

        self.button_layout.addWidget(btn)
        return btn

    def add_stretch_to_buttons(self):
        """Add stretch to button layout"""
        self.button_layout.insertStretch(0)


class ConfirmDialog(BaseDialog):
    """Confirmation dialog"""

    confirmed = Signal()

    def __init__(self, title: str, message: str, confirm_text: str = "確認",
                 cancel_text: str = "キャンセル", danger: bool = False, parent=None):
        super().__init__(title, parent)
        self.setFixedWidth(400)

        # Message
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet(f"""
            font-size: 14px;
            color: {self.theme.text_secondary};
            line-height: 1.5;
        """)
        self.add_content(message_label)

        # Buttons
        self.add_stretch_to_buttons()
        self.add_button(cancel_text, callback=self.reject)
        confirm_btn = self.add_button(
            confirm_text,
            style="danger" if danger else "primary",
            callback=self._on_confirm
        )

    def _on_confirm(self):
        self.confirmed.emit()
        self.accept()


class InputDialog(BaseDialog):
    """Input dialog with text field"""

    submitted = Signal(str)

    def __init__(self, title: str, prompt: str, default_value: str = "",
                 placeholder: str = "", parent=None):
        super().__init__(title, parent)
        self.setFixedWidth(450)

        # Prompt
        prompt_label = QLabel(prompt)
        prompt_label.setStyleSheet(f"""
            font-size: 14px;
            color: {self.theme.text_secondary};
        """)
        self.add_content(prompt_label)

        # Input field
        self.input_field = QLineEdit()
        self.input_field.setText(default_value)
        self.input_field.setPlaceholderText(placeholder)
        self.add_content(self.input_field)

        # Buttons
        self.add_stretch_to_buttons()
        self.add_button("キャンセル", callback=self.reject)
        self.add_button("決定", style="primary", callback=self._on_submit)

    def _on_submit(self):
        self.submitted.emit(self.input_field.text())
        self.accept()

    def get_value(self) -> str:
        return self.input_field.text()


class SelectDialog(BaseDialog):
    """Selection dialog with dropdown"""

    selected = Signal(int, str)  # index, text

    def __init__(self, title: str, prompt: str, options: list, parent=None):
        super().__init__(title, parent)
        self.setFixedWidth(450)

        # Prompt
        prompt_label = QLabel(prompt)
        prompt_label.setStyleSheet(f"""
            font-size: 14px;
            color: {self.theme.text_secondary};
        """)
        self.add_content(prompt_label)

        # Dropdown
        self.combo = QComboBox()
        self.combo.addItems(options)
        self.add_content(self.combo)

        # Buttons
        self.add_stretch_to_buttons()
        self.add_button("キャンセル", callback=self.reject)
        self.add_button("選択", style="primary", callback=self._on_select)

    def _on_select(self):
        self.selected.emit(self.combo.currentIndex(), self.combo.currentText())
        self.accept()

    def get_selection(self) -> tuple:
        return (self.combo.currentIndex(), self.combo.currentText())


class PlayerDetailDialog(BaseDialog):
    """Dialog for displaying player details"""

    def __init__(self, player=None, parent=None):
        super().__init__("選手詳細", parent)
        self.setMinimumSize(600, 500)
        self.player = player

        if player:
            self._create_player_view(player)

        # Close button
        self.add_stretch_to_buttons()
        self.add_button("閉じる", callback=self.accept)

    def _create_player_view(self, player):
        from .cards import PlayerCard
        from .charts import RadarChart

        # Header with basic info
        header = QHBoxLayout()

        # Player card
        card = PlayerCard(player, show_stats=False)
        card.set_clickable(False)
        header.addWidget(card)

        # Radar chart
        radar = RadarChart()
        radar.setFixedSize(250, 250)
        is_pitcher = player.position.value == "投手"
        radar.set_player_stats(player, is_pitcher)
        header.addWidget(radar)

        header_widget = QWidget()
        header_widget.setLayout(header)
        self.add_content(header_widget)

        # Stats details
        self._add_stats_section(player)

        # Career stats
        self._add_career_section(player)

    def _add_stats_section(self, player):
        """Add detailed stats section"""
        from .panels import InfoPanel

        stats = player.stats
        is_pitcher = player.position.value == "投手"

        panel = InfoPanel("能力値")

        if is_pitcher:
            panel.add_row("球速", f"{stats.speed_to_kmh()} km/h")
            panel.add_row("制球", f"{stats.control} ({stats.get_rank(stats.control)})")
            panel.add_row("スタミナ", f"{stats.stamina} ({stats.get_rank(stats.stamina)})")
            panel.add_row("変化球", f"{stats.breaking} ({stats.get_rank(stats.breaking)})")

            # Breaking balls
            if stats.breaking_balls:
                panel.add_row("持ち球", ", ".join(stats.breaking_balls))
        else:
            panel.add_row("ミート", f"{stats.contact} ({stats.get_rank(stats.contact)})")
            panel.add_row("パワー", f"{stats.power} ({stats.get_rank(stats.power)})")
            panel.add_row("走力", f"{stats.run} ({stats.get_rank(stats.run)})")
            panel.add_row("肩力", f"{stats.arm} ({stats.get_rank(stats.arm)})")
            panel.add_row("守備", f"{stats.fielding} ({stats.get_rank(stats.fielding)})")
            panel.add_row("捕球", f"{stats.catching} ({stats.get_rank(stats.catching)})")

        self.add_content(panel)

    def _add_career_section(self, player):
        """Add career stats section"""
        from .panels import InfoPanel

        record = player.record
        is_pitcher = player.position.value == "投手"

        panel = InfoPanel("今季成績")

        if is_pitcher:
            panel.add_row("登板", str(record.games_pitched))
            panel.add_row("勝敗", f"{record.wins}勝 {record.losses}敗")
            panel.add_row("セーブ", str(record.saves))
            panel.add_row("防御率", f"{record.era:.2f}" if record.innings_pitched > 0 else "-.--")
            panel.add_row("投球回", f"{record.innings_pitched:.1f}")
            panel.add_row("奪三振", str(record.strikeouts_pitched))
        else:
            panel.add_row("打率", f".{int(record.batting_average * 1000):03d}" if record.at_bats > 0 else "---")
            panel.add_row("打数", str(record.at_bats))
            panel.add_row("安打", str(record.hits))
            panel.add_row("本塁打", str(record.home_runs))
            panel.add_row("打点", str(record.rbis))
            panel.add_row("盗塁", str(record.stolen_bases))

        self.add_content(panel)


class TradeDialog(BaseDialog):
    """Trade negotiation dialog"""

    trade_proposed = Signal(list, list)  # give_players, receive_players

    def __init__(self, my_team, other_team, parent=None):
        super().__init__(f"トレード: {other_team.name}", parent)
        self.setMinimumSize(800, 600)

        self.my_team = my_team
        self.other_team = other_team
        self.give_players = []
        self.receive_players = []

        self._create_trade_view()

        # Buttons
        self.add_stretch_to_buttons()
        self.add_button("キャンセル", callback=self.reject)
        self.add_button("トレード提案", style="primary", callback=self._on_propose)

    def _create_trade_view(self):
        """Create trade interface"""
        main_layout = QHBoxLayout()

        # My team side
        my_side = QVBoxLayout()
        my_label = QLabel(f"OUT: {self.my_team.name}")
        my_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {self.theme.text_primary};")
        my_side.addWidget(my_label)
        # TODO: Add player selection list
        my_placeholder = QLabel("放出選手をここに追加")
        my_placeholder.setStyleSheet(f"color: {self.theme.text_muted};")
        my_side.addWidget(my_placeholder)

        # Other team side
        other_side = QVBoxLayout()
        other_label = QLabel(f"IN: {self.other_team.name}")
        other_label.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {self.theme.text_primary};")
        other_side.addWidget(other_label)
        # TODO: Add player selection list
        other_placeholder = QLabel("獲得選手をここに追加")
        other_placeholder.setStyleSheet(f"color: {self.theme.text_muted};")
        other_side.addWidget(other_placeholder)

        main_layout.addLayout(my_side)
        main_layout.addLayout(other_side)

        container = QWidget()
        container.setLayout(main_layout)
        self.add_content(container)

    def _on_propose(self):
        self.trade_proposed.emit(self.give_players, self.receive_players)
        self.accept()


class SaveLoadDialog(BaseDialog):
    """Save/Load game dialog"""

    save_selected = Signal(int)
    load_selected = Signal(int)

    def __init__(self, mode: str = "save", save_slots: list = None, parent=None):
        title = "セーブ" if mode == "save" else "ロード"
        super().__init__(title, parent)
        self.setMinimumSize(500, 400)

        self.mode = mode
        self.save_slots = save_slots or []

        self._create_slots_view()

        # Buttons
        self.add_stretch_to_buttons()
        self.add_button("キャンセル", callback=self.reject)

    def _create_slots_view(self):
        """Create save slot list"""
        for i in range(10):
            slot = self._create_slot_widget(i)
            self.add_content(slot)

    def _create_slot_widget(self, slot_index: int) -> QWidget:
        """Create a save slot widget"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)

        # Slot number
        num_label = QLabel(f"#{slot_index + 1}")
        num_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 600;
            color: {self.theme.text_primary};
            min-width: 40px;
        """)
        layout.addWidget(num_label)

        # Slot info
        if slot_index < len(self.save_slots) and self.save_slots[slot_index]:
            slot_data = self.save_slots[slot_index]
            info_text = f"{slot_data.get('team', '?')} - {slot_data.get('year', '?')}年"
            date_text = slot_data.get('date', '不明')
        else:
            info_text = "空きスロット"
            date_text = ""

        info_label = QLabel(info_text)
        info_label.setStyleSheet(f"color: {self.theme.text_primary}; font-size: 14px;")
        layout.addWidget(info_label)

        layout.addStretch()

        if date_text:
            date_label = QLabel(date_text)
            date_label.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 12px;")
            layout.addWidget(date_label)

        # Action button
        btn_text = "セーブ" if self.mode == "save" else "ロード"
        action_btn = QPushButton(btn_text)
        action_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.primary};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.primary_hover};
            }}
        """)
        action_btn.clicked.connect(lambda: self._on_slot_action(slot_index))
        layout.addWidget(action_btn)

        widget.setStyleSheet(f"""
            QWidget {{
                background-color: {self.theme.bg_input};
                border-radius: 6px;
            }}
            QWidget:hover {{
                background-color: {self.theme.bg_card_hover};
            }}
        """)

        return widget

    def _on_slot_action(self, slot_index: int):
        if self.mode == "save":
            self.save_selected.emit(slot_index)
        else:
            self.load_selected.emit(slot_index)
        self.accept()


def show_message(parent, title: str, message: str, msg_type: str = "info"):
    """Show a simple message dialog"""
    dialog = ConfirmDialog(title, message, confirm_text="OK", parent=parent)
    dialog.button_layout.itemAt(0).widget().hide()  # Hide cancel button
    return dialog.exec()


def show_confirm(parent, title: str, message: str, danger: bool = False) -> bool:
    """Show a confirmation dialog and return result"""
    dialog = ConfirmDialog(title, message, danger=danger, parent=parent)
    return dialog.exec() == QDialog.Accepted


def show_input(parent, title: str, prompt: str, default: str = "") -> str:
    """Show an input dialog and return the entered text"""
    dialog = InputDialog(title, prompt, default, parent=parent)
    if dialog.exec() == QDialog.Accepted:
        return dialog.get_value()
    return None
