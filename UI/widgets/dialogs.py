# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Dialog Widgets
Custom Modal Dialogs and Popups
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QFrame, QGraphicsDropShadowEffect, QMessageBox,
    QLineEdit, QComboBox, QSpinBox, QTextEdit, QListWidget, 
    QListWidgetItem, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QIcon

import sys
sys.path.insert(0, '..')
from UI.theme import get_theme


class BaseDialog(QDialog):
    """Base dialog with custom styling"""

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
    """Detailed Player Stats Dialog (Power Pros Style)"""

    def __init__(self, player=None, parent=None):
        super().__init__(f"選手詳細データ - {player.name if player else ''}", parent)
        self.setMinimumSize(900, 650)
        self.player = player
        self.theme = get_theme()

        if player:
            self._create_premium_view(player)

        # Close button
        self.add_stretch_to_buttons()
        self.add_button("閉じる", callback=self.accept)

    def _create_premium_view(self, player):
        """Create the enhanced detailed view"""
        main_layout = QHBoxLayout()
        main_layout.setSpacing(24)

        # === Left Column: Profile & Radar ===
        left_col = QVBoxLayout()
        
        # 1. Profile Header
        profile_frame = self._create_profile_header(player)
        left_col.addWidget(profile_frame)

        # 2. Radar Chart
        chart_container = QFrame()
        chart_container.setStyleSheet(f"background: {self.theme.bg_card_elevated}; border-radius: 8px;")
        chart_layout = QVBoxLayout(chart_container)
        
        self.radar = RadarChart()
        self.radar.setFixedSize(300, 300)
        is_pitcher = player.position.value == "投手"
        self.radar.set_player_stats(player, is_pitcher)
        
        chart_layout.addWidget(self.radar, 0, Qt.AlignCenter)
        left_col.addWidget(chart_container)
        
        left_col.addStretch()
        main_layout.addLayout(left_col, stretch=1)

        # === Right Column: Detailed Stats Grid ===
        right_col = QVBoxLayout()
        right_col.setSpacing(16)

        # 3. Main Ability Stats (Grid with Ranks)
        abilities_frame = self._create_abilities_grid(player)
        right_col.addWidget(abilities_frame)

        # 4. Special Abilities / Details
        details_frame = self._create_details_list(player)
        right_col.addWidget(details_frame, stretch=1)

        main_layout.addLayout(right_col, stretch=2)

        container = QWidget()
        container.setLayout(main_layout)
        self.add_content(container)

    def _create_profile_header(self, player):
        frame = QFrame()
        frame.setStyleSheet(f"background: {self.theme.bg_card}; border-left: 4px solid {self.theme.primary};")
        layout = QVBoxLayout(frame)
        
        # Name & Number
        top_row = QHBoxLayout()
        name_lbl = QLabel(player.name)
        name_lbl.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {self.theme.text_primary};")
        
        num_lbl = QLabel(f"#{player.uniform_number}")
        num_lbl.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {self.theme.text_muted}; font-family: Consolas;")
        
        top_row.addWidget(name_lbl)
        top_row.addStretch()
        top_row.addWidget(num_lbl)
        layout.addLayout(top_row)
        
        # Info Row
        type_str = player.player_type.value if player.player_type else "タイプ未定"
        info_text = f"{player.position.value} ({type_str}) | {player.age}歳 | プロ{player.years_pro}年目 | {player.salary//10000}万円"
        info_lbl = QLabel(info_text)
        info_lbl.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 13px;")
        layout.addWidget(info_lbl)
        
        return frame

    def _create_abilities_grid(self, player):
        frame = QFrame()
        frame.setStyleSheet(f"background: {self.theme.bg_card}; border-radius: 8px;")
        layout = QGridLayout(frame)
        layout.setSpacing(8)  # Reduced from 10 to prevent wrapping
        
        stats = player.stats
        is_pitcher = player.position.value == "投手"
        
        # Create Stat Block Helper
        def create_stat_block(label, value, row, col):
            container = QWidget()
            vbox = QVBoxLayout(container)
            vbox.setContentsMargins(0,0,0,0)
            vbox.setSpacing(2)
            
            lbl = QLabel(label)
            lbl.setStyleSheet(f"font-size: 11px; color: {self.theme.text_muted};")
            
            # Rank Color & Text
            rank = stats.get_rank(value)
            color = stats.get_rank_color(value)
            
            val_layout = QHBoxLayout()
            rank_lbl = QLabel(rank)
            rank_lbl.setStyleSheet(f"font-size: 20px; font-weight: 900; color: {color};")
            
            num_lbl = QLabel(str(value))
            num_lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {self.theme.text_primary}; padding-top: 4px;")
            
            val_layout.addWidget(rank_lbl)
            val_layout.addWidget(num_lbl)
            val_layout.addStretch()
            
            vbox.addWidget(lbl)
            vbox.addLayout(val_layout)
            
            # Bar
            bar = QFrame()
            bar.setFixedHeight(4)
            bar.setStyleSheet(f"background: {self.theme.bg_input}; border-radius: 2px;")
            fill = QFrame(bar)
            fill.setFixedHeight(4)
            fill.setFixedWidth(int(100 * (value/100))) # roughly
            fill.setStyleSheet(f"background: {color}; border-radius: 2px;")
            vbox.addWidget(bar)
            
            layout.addWidget(container, row, col)

        if is_pitcher:
            # Pitcher Main Stats
            speed_kmh = stats.speed_to_kmh()
            # 球速は特殊表示
            speed_widget = QWidget()
            sl = QVBoxLayout(speed_widget)
            sl.setContentsMargins(0,0,0,0)
            sl.addWidget(QLabel("球速"))
            sl.addWidget(QLabel(f"{speed_kmh} km/h"))
            sl.itemAt(0).widget().setStyleSheet(f"font-size: 11px; color: {self.theme.text_muted};")
            sl.itemAt(1).widget().setStyleSheet(f"font-size: 22px; font-weight: 800; color: {self.theme.text_primary};")
            layout.addWidget(speed_widget, 0, 0, 1, 2)
            
            create_stat_block("コントロール", stats.control, 0, 2)
            create_stat_block("スタミナ", stats.stamina, 0, 3)
            create_stat_block("変化球", stats.breaking, 1, 0)
            create_stat_block("対左打者", stats.vs_left_pitcher, 1, 1)
            create_stat_block("対ピンチ", stats.vs_pinch, 1, 2)
            create_stat_block("打たれ強さ", stats.mental, 1, 3)
            
        else:
            # Batter Main Stats
            # 弾道 (特殊)
            traj_widget = QWidget()
            tl = QVBoxLayout(traj_widget)
            tl.setContentsMargins(0,0,0,0)
            tl.addWidget(QLabel("弾道"))
            tl.addWidget(QLabel(str(stats.trajectory)))
            tl.itemAt(0).widget().setStyleSheet(f"font-size: 11px; color: {self.theme.text_muted};")
            tl.itemAt(1).widget().setStyleSheet(f"font-size: 22px; font-weight: 800; color: {self.theme.accent_orange};")
            layout.addWidget(traj_widget, 0, 0)
            
            create_stat_block("ミート", stats.contact, 0, 1)
            create_stat_block("パワー", stats.power, 0, 2)
            create_stat_block("走力", stats.run, 0, 3)
            create_stat_block("肩力", stats.arm, 1, 0)
            create_stat_block("守備力", stats.fielding, 1, 1)
            create_stat_block("捕球", stats.catching, 1, 2)
            create_stat_block("チャンス", stats.chance, 1, 3)

        return frame

    def _create_details_list(self, player):
        frame = QFrame()
        frame.setStyleSheet(f"background: {self.theme.bg_card}; border-radius: 8px;")
        layout = QVBoxLayout(frame)
        
        lbl = QLabel("詳細能力 & 特殊能力")
        lbl.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {self.theme.text_secondary};")
        layout.addWidget(lbl)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        content = QWidget()
        grid = QGridLayout(content)
        grid.setSpacing(8)  # Reduced spacing
        
        stats = player.stats
        is_pitcher = player.position.value == "投手"
        
        # Helper for sub stats
        def add_sub_stat(label, value, r, c):
            rank = stats.get_rank(value)
            color = stats.get_rank_color(value)
            l = QLabel(f"{label}: {rank} ({value})")
            l.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: 600; border-left: 3px solid {color}; padding-left: 6px;")
            grid.addWidget(l, r, c)

        r, c = 0, 0
        
        if is_pitcher:
            add_sub_stat("クイック", stats.quick, 0, 0)
            add_sub_stat("安定感", stats.stability, 0, 1)
            add_sub_stat("ケガしにくさ", stats.injury_resistance, 1, 0)
            add_sub_stat("回復", stats.recovery, 1, 1)
            
            # Breaking balls
            bb_label = QLabel(f"変化球: {stats.get_breaking_balls_display()}")
            bb_label.setStyleSheet(f"color: {self.theme.accent_blue}; margin-top: 8px;")
            grid.addWidget(bb_label, 2, 0, 1, 2)
            
        else:
            add_sub_stat("対左投手", stats.vs_left_batter, 0, 0)
            add_sub_stat("盗塁", stats.steal, 0, 1)
            add_sub_stat("走塁", stats.base_running, 1, 0)
            add_sub_stat("送球", stats.arm, 1, 1) # Reuse arm? or separate stat if available
            add_sub_stat("ケガしにくさ", stats.injury_resistance, 2, 0)
            add_sub_stat("回復", stats.recovery, 2, 1)
            add_sub_stat("バント", stats.bunt, 3, 0)

        # Special Abilities from object (if exists)
        if player.special_abilities:
            # ここは実装に合わせて調整。現状は文字列リストなどを想定
            pass

        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return frame


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


class OrderDialog(BaseDialog):
    """Lineup ordering dialog"""
    
    def __init__(self, team, parent=None):
        super().__init__(f"打順設定: {team.name}", parent)
        self.setMinimumSize(800, 600)
        self.team = team
        
        self._setup_lists()
        
        # Buttons
        self.add_stretch_to_buttons()
        self.add_button("キャンセル", callback=self.reject)
        self.add_button("決定", style="primary", callback=self._on_save)

    def _setup_lists(self):
        container = QWidget()
        main_layout = QHBoxLayout(container)
        main_layout.setSpacing(16)
        
        # --- Left: Starting Lineup ---
        left_layout = QVBoxLayout()
        lineup_label = QLabel("スターティングメンバー")
        lineup_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: 600;")
        left_layout.addWidget(lineup_label)
        
        self.lineup_list = QListWidget()
        self.lineup_list.setDragDropMode(QAbstractItemView.DragDrop)
        self.lineup_list.setDefaultDropAction(Qt.MoveAction)
        self.lineup_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.lineup_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {self.theme.bg_input};
                border: 1px solid {self.theme.border};
                border-radius: 4px;
                color: {self.theme.text_primary};
                font-size: 14px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {self.theme.border};
            }}
            QListWidget::item:selected {{
                background-color: {self.theme.primary_light};
                color: white;
            }}
        """)
        left_layout.addWidget(self.lineup_list)
        
        # Initialize Lineup
        if self.team.current_lineup:
            for idx in self.team.current_lineup:
                if 0 <= idx < len(self.team.players):
                    p = self.team.players[idx]
                    self._add_player_item(self.lineup_list, p, idx)
        
        # Fix lineup size to 9 (add placeholders if less)
        while self.lineup_list.count() < 9:
            item = QListWidgetItem("--- 空き ---")
            item.setData(Qt.UserRole, -1)
            self.lineup_list.addItem(item)
            
        main_layout.addLayout(left_layout, stretch=1)
        
        # --- Center: Controls ---
        center_layout = QVBoxLayout()
        center_layout.addStretch()
        
        to_bench_btn = QPushButton("→")
        to_bench_btn.setFixedSize(40, 40)
        to_bench_btn.clicked.connect(self._move_to_bench)
        center_layout.addWidget(to_bench_btn)
        
        to_lineup_btn = QPushButton("←")
        to_lineup_btn.setFixedSize(40, 40)
        to_lineup_btn.clicked.connect(self._move_to_lineup)
        center_layout.addWidget(to_lineup_btn)
        
        center_layout.addStretch()
        main_layout.addLayout(center_layout)
        
        # --- Right: Bench ---
        right_layout = QVBoxLayout()
        bench_label = QLabel("ベンチ (野手)")
        bench_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: 600;")
        right_layout.addWidget(bench_label)
        
        self.bench_list = QListWidget()
        self.bench_list.setDragDropMode(QAbstractItemView.DragDrop)
        self.bench_list.setDefaultDropAction(Qt.MoveAction)
        self.bench_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.bench_list.setStyleSheet(self.lineup_list.styleSheet())
        right_layout.addWidget(self.bench_list)
        
        # Initialize Bench (Active batters not in lineup)
        roster = self.team.get_roster_players()
        lineup_idxs = set(self.team.current_lineup)
        
        for p in roster:
            p_idx = self.team.players.index(p)
            # Exclude pitchers and already in lineup
            if p.position.value != "投手" and p_idx not in lineup_idxs:
                self._add_player_item(self.bench_list, p, p_idx)
                
        main_layout.addLayout(right_layout, stretch=1)
        
        self.add_content(container)

    def _add_player_item(self, list_widget, player, index):
        item = QListWidgetItem(f"{player.position.value}  {player.name}")
        item.setData(Qt.UserRole, index)
        # item.setForeground(...) 
        list_widget.addItem(item)

    def _move_to_bench(self):
        row = self.lineup_list.currentRow()
        if row < 0: return
        
        item = self.lineup_list.takeItem(row)
        idx = item.data(Qt.UserRole)
        
        if idx != -1:
            self.bench_list.addItem(item)
            
        # Replace lineup slot with placeholder
        placeholder = QListWidgetItem("--- 空き ---")
        placeholder.setData(Qt.UserRole, -1)
        self.lineup_list.insertItem(row, placeholder)

    def _move_to_lineup(self):
        row = self.bench_list.currentRow()
        if row < 0: return
        
        # Find a placeholder or swap with selected lineup item
        target_row = self.lineup_list.currentRow()
        
        # If no selection in lineup, find first empty
        if target_row < 0:
            for i in range(self.lineup_list.count()):
                if self.lineup_list.item(i).data(Qt.UserRole) == -1:
                    target_row = i
                    break
        
        if target_row < 0:
            # Lineup full, maybe swap? For now just return
            return 
            
        item = self.bench_list.takeItem(row)
        
        # Handle swap if target not empty
        target_item = self.lineup_list.item(target_row)
        target_idx = target_item.data(Qt.UserRole)
        
        self.lineup_list.takeItem(target_row)
        self.lineup_list.insertItem(target_row, item)
        
        if target_idx != -1:
            # Return displaced player to bench
            self.bench_list.addItem(target_item)

    def _on_save(self):
        new_lineup = []
        for i in range(self.lineup_list.count()):
            idx = self.lineup_list.item(i).data(Qt.UserRole)
            if idx != -1:
                new_lineup.append(idx)
        
        self.team.current_lineup = new_lineup
        self.team.auto_set_bench() # Refresh bench based on new lineup
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