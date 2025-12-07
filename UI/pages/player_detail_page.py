# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Player Detail Page
Comprehensive Player Information Display
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout, QSizePolicy, QTabWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
import random

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.panels import ToolbarPanel, InfoPanel
from UI.widgets.charts import RadarChart, BarChart, StatMeter


class StatBlock(QFrame):
    """A block displaying a single stat with rank badge"""

    def __init__(self, label: str, value: int, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._setup_ui(label, value)

    def _setup_ui(self, label: str, value: int):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 6px;
                padding: 8px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Label
        lbl = QLabel(label)
        lbl.setStyleSheet(f"""
            font-size: 11px;
            color: {self.theme.text_muted};
            border: none;
            background: transparent;
        """)
        layout.addWidget(lbl)

        # Value with rank
        from models import PlayerStats
        stats = PlayerStats()
        rank = stats.get_rank(value)
        color = stats.get_rank_color(value)

        value_layout = QHBoxLayout()
        value_layout.setSpacing(8)

        rank_label = QLabel(rank)
        rank_label.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 900;
            color: {color};
            border: none;
            background: transparent;
        """)
        value_layout.addWidget(rank_label)

        num_label = QLabel(str(value))
        num_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 600;
            color: {self.theme.text_primary};
            border: none;
            background: transparent;
            padding-top: 8px;
        """)
        value_layout.addWidget(num_label)
        value_layout.addStretch()

        layout.addLayout(value_layout)

        # Progress bar
        bar_container = QFrame()
        bar_container.setFixedHeight(6)
        bar_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_input};
                border-radius: 3px;
                border: none;
            }}
        """)

        fill_width = int(100 * value / 200)  # Scale based on 200 max
        if fill_width > 100: fill_width = 100
        if fill_width < 0: fill_width = 0
        
        # Simple bar implementation using layout
        bar_layout = QHBoxLayout(bar_container)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        bar_layout.setSpacing(0)
        
        filled = QFrame()
        filled.setStyleSheet(f"background-color: {color}; border-radius: 3px;")
        
        empty = QFrame()
        empty.setStyleSheet("background-color: transparent;")
        
        if fill_width > 0:
            bar_layout.addWidget(filled, fill_width)
        bar_layout.addWidget(empty, 100 - fill_width)

        layout.addWidget(bar_container)


class PlayerDetailPage(QWidget):
    """Detailed player information page"""

    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.current_player = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # Main content in scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {self.theme.bg_dark};
                border: none;
            }}
        """)

        content = QWidget()
        content.setStyleSheet(f"background-color: {self.theme.bg_dark};")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(24, 24, 24, 24)
        self.content_layout.setSpacing(24)

        # Placeholder - will be populated when player is set
        self.placeholder = QLabel("選手を選択してください")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet(f"""
            font-size: 18px;
            color: {self.theme.text_muted};
        """)
        self.content_layout.addWidget(self.placeholder)

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_toolbar(self) -> ToolbarPanel:
        toolbar = ToolbarPanel()
        toolbar.setFixedHeight(50)

        # Back button
        back_btn = QPushButton("← 戻る")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setFixedHeight(32)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.theme.text_secondary};
                border: 1px solid {self.theme.border};
                border-radius: 6px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.bg_card_hover};
                color: {self.theme.text_primary};
            }}
        """)
        back_btn.clicked.connect(self._on_back)
        toolbar.add_widget(back_btn)

        toolbar.add_separator()

        # Player name label
        self.player_name_label = QLabel("選手詳細")
        self.player_name_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 700;
            color: {self.theme.text_primary};
        """)
        toolbar.add_widget(self.player_name_label)

        toolbar.add_stretch()

        return toolbar

    def set_player(self, player):
        """Set the player to display"""
        self.current_player = player

        if not player:
            self.placeholder.show()
            self.player_name_label.setText("選手詳細")
            return

        self.placeholder.hide()
        self.player_name_label.setText(f"{player.name} - 選手詳細")

        # Clear existing content
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        # Build the detail view
        self._create_detail_view(player)

    def _create_detail_view(self, player):
        """Create the detailed player view"""
        # === Header Section ===
        header = self._create_header(player)
        self.content_layout.addWidget(header)

        # === Main Content: Two columns ===
        main_layout = QHBoxLayout()
        main_layout.setSpacing(24)

        # Left column: Radar chart and basic info
        left_col = self._create_left_column(player)
        main_layout.addLayout(left_col, stretch=1)

        # Right column: Stats grid
        right_col = self._create_right_column(player)
        main_layout.addLayout(right_col, stretch=2)

        main_container = QWidget()
        main_container.setLayout(main_layout)
        self.content_layout.addWidget(main_container)

        # === Stats Tables ===
        stats_section = self._create_stats_section(player)
        self.content_layout.addWidget(stats_section)

        # Stretch at the end
        self.content_layout.addStretch()

    def _create_header(self, player) -> QFrame:
        """Create the player header"""
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-left: 4px solid {self.theme.primary};
                border-radius: 8px;
            }}
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 20, 24, 20)

        # Left: Name and basic info
        left_layout = QVBoxLayout()
        left_layout.setSpacing(4)

        name_layout = QHBoxLayout()
        name_label = QLabel(player.name)
        name_label.setStyleSheet(f"""
            font-size: 32px;
            font-weight: 800;
            color: {self.theme.text_primary};
            border: none;
            background: transparent;
        """)
        name_layout.addWidget(name_label)

        number_label = QLabel(f"#{player.uniform_number}")
        number_label.setStyleSheet(f"""
            font-size: 32px;
            font-weight: 800;
            color: {self.theme.text_muted};
            font-family: 'Consolas', monospace;
            margin-left: 16px;
            border: none;
            background: transparent;
        """)
        name_layout.addWidget(number_label)
        name_layout.addStretch()

        left_layout.addLayout(name_layout)

        # Info line
        pitch_type_str = ""
        if player.position.value == "投手" and player.pitch_type:
            pitch_type_str = f" ({player.pitch_type.value})"
            
        pos_str = f"{player.position.value}{pitch_type_str}"
        status_str = "外国人" if player.is_foreign else "国内"
        if player.is_developmental:
            status_str += " / 育成"

        info_text = f"{pos_str} | {status_str}"
        info_label = QLabel(info_text)
        info_label.setStyleSheet(f"""
            font-size: 16px;
            color: {self.theme.text_secondary};
            font-weight: 500;
            border: none;
            background: transparent;
        """)
        left_layout.addWidget(info_label)
        
        layout.addLayout(left_layout)
        return header

    def _create_left_column(self, player) -> QVBoxLayout:
        """Create the left column with radar chart and info card"""
        layout = QVBoxLayout()
        layout.setSpacing(16)

        # 1. Radar chart container
        chart_container = QFrame()
        chart_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
            }}
        """)
        chart_layout = QVBoxLayout(chart_container)
        chart_layout.setContentsMargins(16, 16, 16, 16)

        chart_title = QLabel("能力チャート")
        chart_title.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {self.theme.text_secondary};
            border: none;
            background: transparent;
        """)
        chart_layout.addWidget(chart_title)

        radar = RadarChart()
        radar.setFixedSize(280, 280)
        is_pitcher = player.position.value == "投手"
        radar.set_player_stats(player, is_pitcher)
        chart_layout.addWidget(radar, 0, Qt.AlignCenter)

        layout.addWidget(chart_container)

        # 2. Player Info Card (Moved from Header)
        info_card = QFrame()
        info_card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding) # Expand vertically
        info_card.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
            }}
        """)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(16, 16, 16, 16)
        info_layout.setSpacing(12)

        info_title = QLabel("プロフィール")
        info_title.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {self.theme.text_secondary};
            border: none;
            background: transparent;
        """)
        info_layout.addWidget(info_title)

        # Info Grid
        info_grid = QGridLayout()
        info_grid.setSpacing(16)
        
        # --- Improved Auto-Generation Logic ---
        # Years Pro & Draft
        display_years = player.years_pro
        display_draft = player.draft_round
        
        # Seed for consistency per player session
        seed = sum(ord(c) for c in player.name) + player.age
        rng = random.Random(seed)

        if display_years == 0:
            # Estimate join age: High School (18), College (22), Adult (24)
            # Probability distribution
            r = rng.random()
            if r < 0.4: join_age = 18   # 40% High School
            elif r < 0.8: join_age = 22 # 40% College
            else: join_age = 24         # 20% Adult/Industrial
            
            display_years = max(1, player.age - join_age)
        
        years_str = f"{display_years}年目"

        # Draft
        draft_str = "ドラフト外"
        if display_draft > 0:
            draft_str = f"{display_draft}位"
        else:
            # Generate fake draft info for display if 0
            # Higher salary/stats might imply better draft
            if player.salary > 50000000:
                est_draft = rng.randint(1, 2)
            elif player.salary > 20000000:
                est_draft = rng.randint(2, 4)
            else:
                est_draft = rng.randint(3, 7)
            draft_str = f"{est_draft}位"

        # Hometown (Random generation from 47 prefectures)
        prefectures = [
            "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
            "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
            "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
            "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
            "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
            "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
            "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県"
        ]
        # Weighted slightly towards major areas (indices for Tokyo, Osaka, etc.)
        # Simple weighted choice
        weights = [1] * 47
        # Boost Tokyo(12), Kanagawa(13), Osaka(26), Aichi(22), Fukuoka(39), Hokkaido(0)
        weights[12] = 5 # Tokyo
        weights[13] = 3 # Kanagawa
        weights[26] = 3 # Osaka
        weights[22] = 3 # Aichi
        weights[39] = 2 # Fukuoka
        weights[0]  = 2 # Hokkaido
        
        hometown_str = getattr(player, 'hometown', None)
        if not hometown_str:
            hometown_str = rng.choices(prefectures, weights=weights, k=1)[0]

        # Salary
        salary_str = f"{player.salary // 10000:,}万円"

        def add_card_item(row, col, label, value, color=None):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"font-size: 11px; color: {self.theme.text_muted}; border:none; background: transparent;")
            val = QLabel(value)
            c = color if color else self.theme.text_primary
            val.setStyleSheet(f"font-size: 15px; font-weight: 600; color: {c}; border:none; background: transparent;")
            
            container = QVBoxLayout()
            container.setContentsMargins(0,0,0,0)
            container.setSpacing(2)
            container.addWidget(lbl)
            container.addWidget(val)
            
            w = QWidget()
            w.setLayout(container)
            info_grid.addWidget(w, row, col)

        add_card_item(0, 0, "推定年俸", salary_str, self.theme.success)
        add_card_item(0, 1, "年齢", f"{player.age}歳")
        add_card_item(1, 0, "プロ年数", years_str)
        add_card_item(1, 1, "ドラフト", draft_str)
        add_card_item(2, 0, "出身地", hometown_str)

        info_layout.addLayout(info_grid)
        info_layout.addStretch() # Push content to top, but card expands
        layout.addWidget(info_card, stretch=1) # Let info card take remaining space

        # 3. Position info
        if player.sub_positions:
            pos_container = QFrame()
            pos_container.setStyleSheet(f"""
                QFrame {{
                    background-color: {self.theme.bg_card};
                    border: 1px solid {self.theme.border};
                    border-radius: 8px;
                }}
            """)
            pos_layout = QVBoxLayout(pos_container)
            pos_layout.setContentsMargins(16, 12, 16, 12)

            pos_title = QLabel("守備適性")
            pos_title.setStyleSheet(f"""
                font-size: 14px;
                font-weight: 700;
                color: {self.theme.text_secondary};
                border: none;
                background: transparent;
            """)
            pos_layout.addWidget(pos_title)

            main_pos = QLabel(f"メイン: {player.position.value}")
            main_pos.setStyleSheet(f"""
                font-size: 13px;
                color: {self.theme.text_primary};
                border: none;
                background: transparent;
            """)
            pos_layout.addWidget(main_pos)

            sub_pos_text = ", ".join([p.value for p in player.sub_positions])
            sub_pos = QLabel(f"サブ: {sub_pos_text}")
            sub_pos.setStyleSheet(f"""
                font-size: 13px;
                color: {self.theme.text_muted};
                border: none;
                background: transparent;
            """)
            pos_layout.addWidget(sub_pos)

            layout.addWidget(pos_container)

        # layout.addStretch() # Removed stretch from bottom to let cards fill space
        return layout

    def _create_right_column(self, player) -> QVBoxLayout:
        """Create the right column with comprehensive stats grid"""
        layout = QVBoxLayout()
        layout.setSpacing(16)

        is_pitcher = player.position.value == "投手"
        stats = player.stats

        # === 1. Main Stats Container (基本能力) ===
        stats_container = QFrame()
        stats_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
            }}
        """)
        stats_layout = QVBoxLayout(stats_container)
        stats_layout.setContentsMargins(16, 16, 16, 16)
        stats_layout.setSpacing(16)

        stats_title = QLabel("基本能力")
        stats_title.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {self.theme.text_secondary};
            border: none;
            background: transparent;
        """)
        stats_layout.addWidget(stats_title)

        grid = QGridLayout()
        grid.setSpacing(12)

        if is_pitcher:
            # Pitcher Main Stats
            speed_kmh = stats.speed_to_kmh()
            
            # Speed display
            speed_block = QFrame()
            speed_block.setStyleSheet(f"""
                QFrame {{
                    background-color: {self.theme.bg_input};
                    border: 1px solid {self.theme.border};
                    border-radius: 6px;
                    padding: 8px;
                }}
            """)
            speed_layout = QVBoxLayout(speed_block)
            speed_layout.setContentsMargins(12, 8, 12, 8)
            speed_lbl = QLabel("球速")
            speed_lbl.setStyleSheet(f"font-size: 11px; color: {self.theme.text_muted}; border: none; background: transparent;")
            speed_val = QLabel(f"{speed_kmh} km/h")
            speed_val.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {self.theme.text_primary}; border: none; background: transparent;")
            speed_layout.addWidget(speed_lbl)
            speed_layout.addWidget(speed_val)
            grid.addWidget(speed_block, 0, 0)

            grid.addWidget(StatBlock("コントロール", stats.control), 0, 1)
            grid.addWidget(StatBlock("スタミナ", stats.stamina), 0, 2)
            grid.addWidget(StatBlock("変化球(Stuff)", stats.stuff), 0, 3)

            grid.addWidget(StatBlock("ムーブメント", stats.movement), 1, 0)
            grid.addWidget(StatBlock("対左打者", stats.vs_left_pitcher if hasattr(stats, 'vs_left_pitcher') else 50), 1, 1)
            grid.addWidget(StatBlock("対ピンチ", stats.vs_pinch if hasattr(stats, 'vs_pinch') else 50), 1, 2)
            grid.addWidget(StatBlock("クイック", stats.hold_runners), 1, 3)

        else:
            # Batter Main Stats
            # Trajectory display
            traj_block = QFrame()
            traj_block.setStyleSheet(f"""
                QFrame {{
                    background-color: {self.theme.bg_input};
                    border: 1px solid {self.theme.border};
                    border-radius: 6px;
                    padding: 8px;
                }}
            """)
            traj_layout = QVBoxLayout(traj_block)
            traj_layout.setContentsMargins(12, 8, 12, 8)
            traj_lbl = QLabel("弾道")
            traj_lbl.setStyleSheet(f"font-size: 11px; color: {self.theme.text_muted}; border: none; background: transparent;")
            traj_val = QLabel(str(stats.trajectory))
            traj_val.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {self.theme.accent_orange}; border: none; background: transparent;")
            traj_layout.addWidget(traj_lbl)
            traj_layout.addWidget(traj_val)
            grid.addWidget(traj_block, 0, 0)

            grid.addWidget(StatBlock("ミート", stats.contact), 0, 1)
            grid.addWidget(StatBlock("パワー", stats.power), 0, 2)
            grid.addWidget(StatBlock("走力", stats.speed), 0, 3)

            grid.addWidget(StatBlock("ギャップ", stats.gap), 1, 0)
            grid.addWidget(StatBlock("選球眼", stats.eye), 1, 1)
            grid.addWidget(StatBlock("三振回避", stats.avoid_k), 1, 2)
            grid.addWidget(StatBlock("チャンス", stats.chance), 1, 3)

        stats_layout.addLayout(grid)
        layout.addWidget(stats_container)

        # === 2. Detailed Stats Container (詳細能力) ===
        additional_container = QFrame()
        additional_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
            }}
        """)
        additional_layout = QVBoxLayout(additional_container)
        additional_layout.setContentsMargins(16, 16, 16, 16)
        additional_layout.setSpacing(12)

        additional_title = QLabel("詳細能力")
        additional_title.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {self.theme.text_secondary};
            border: none;
            background: transparent;
        """)
        additional_layout.addWidget(additional_title)

        add_grid = QGridLayout()
        add_grid.setSpacing(8)

        if is_pitcher:
            # Pitcher Details
            self._add_detail_stat(add_grid, "安定感", stats.control, 0, 0) # Mapped to control for simplicity
            self._add_detail_stat(add_grid, "メンタル", stats.mental, 0, 1)
            self._add_detail_stat(add_grid, "ゴロ傾向", stats.gb_tendency, 0, 2)
            
            self._add_detail_stat(add_grid, "回復", stats.recovery, 1, 0)
            self._add_detail_stat(add_grid, "ケガしにくさ", stats.durability, 1, 1)
            self._add_detail_stat(add_grid, "練習態度", stats.work_ethic, 1, 2)

            additional_layout.addLayout(add_grid)

            # Breaking balls
            if stats.breaking_balls:
                bb_label = QLabel(f"持ち球: {stats.get_breaking_balls_display()}")
                bb_label.setStyleSheet(f"""
                    font-size: 13px;
                    color: {self.theme.accent_blue};
                    margin-top: 8px;
                    border: none;
                    background: transparent;
                """)
                additional_layout.addWidget(bb_label)
        else:
            # Batter Details
            self._add_detail_stat(add_grid, "対左投手", stats.vs_left_batter, 0, 0)
            self._add_detail_stat(add_grid, "盗塁", stats.steal, 0, 1)
            self._add_detail_stat(add_grid, "走塁意識", stats.baserunning, 0, 2)
            
            self._add_detail_stat(add_grid, "送りバント", stats.bunt_sac, 1, 0)
            self._add_detail_stat(add_grid, "セーフティ", stats.bunt_hit, 1, 1)
            self._add_detail_stat(add_grid, "メンタル", stats.mental, 1, 2)

            self._add_detail_stat(add_grid, "回復", stats.recovery, 2, 0)
            self._add_detail_stat(add_grid, "ケガしにくさ", stats.durability, 2, 1)
            self._add_detail_stat(add_grid, "練習態度", stats.work_ethic, 2, 2)
            
            additional_layout.addLayout(add_grid)

        layout.addWidget(additional_container)
        
        # === 3. Fielding Stats (守備能力) ===
        fielding_container = QFrame()
        fielding_container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
            }}
        """)
        fielding_layout = QVBoxLayout(fielding_container)
        fielding_layout.setContentsMargins(16, 16, 16, 16)
        fielding_layout.setSpacing(12)
        
        fielding_title = QLabel("守備能力詳細")
        fielding_title.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {self.theme.text_secondary};
            border: none;
            background: transparent;
        """)
        fielding_layout.addWidget(fielding_title)
        
        f_grid = QGridLayout()
        f_grid.setSpacing(8)
        
        # Infield
        self._add_detail_stat(f_grid, "内野守備", stats.inf_range, 0, 0)
        self._add_detail_stat(f_grid, "内野エラー", stats.inf_error, 0, 1)
        self._add_detail_stat(f_grid, "内野肩", stats.inf_arm, 0, 2)
        self._add_detail_stat(f_grid, "併殺処理", stats.turn_dp, 0, 3)
        
        # Outfield
        self._add_detail_stat(f_grid, "外野守備", stats.of_range, 1, 0)
        self._add_detail_stat(f_grid, "外野エラー", stats.of_error, 1, 1)
        self._add_detail_stat(f_grid, "外野肩", stats.of_arm, 1, 2)
        
        # Catcher
        self._add_detail_stat(f_grid, "捕手リード", stats.catcher_ability, 2, 0)
        self._add_detail_stat(f_grid, "捕手肩", stats.catcher_arm, 2, 1)
        
        fielding_layout.addLayout(f_grid)
        layout.addWidget(fielding_container)

        layout.addStretch()
        return layout

    def _add_detail_stat(self, grid: QGridLayout, label: str, value: int, row: int, col: int):
        """Add a detail stat row to the grid"""
        from models import PlayerStats
        stats = PlayerStats()
        rank = stats.get_rank(value)
        color = stats.get_rank_color(value)

        stat_label = QLabel(f"{label}: {rank} ({value})")
        stat_label.setStyleSheet(f"""
            font-size: 13px;
            color: {self.theme.text_primary};
            font-weight: 600;
            border-left: 3px solid {color};
            padding-left: 8px;
            background: transparent;
        """)
        grid.addWidget(stat_label, row, col)

    def _create_stats_section(self, player) -> QFrame:
        """Create the season stats section with Tabs for 1st/2nd/3rd team"""
        container = QFrame()
        container.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-radius: 8px;
            }}
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("今季成績")
        title.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {self.theme.text_secondary};
            border: none;
            background: transparent;
        """)
        layout.addWidget(title)

        # Tab Widget
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 0px solid {self.theme.border};
                border-radius: 4px;
                background-color: transparent;
            }}
            QTabBar::tab {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_secondary};
                padding: 6px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 4px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background-color: {self.theme.primary};
                color: #FFFFFF;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {self.theme.bg_card_hover};
            }}
        """)

        # データの取得（存在しない場合は安全にダミーを使用）
        # 現在の実装ではrecordは1つだが、将来的に拡張されることを想定
        from models import PlayerRecord
        
        # 1軍 (既存のrecordを使用)
        rec_first = player.record
        
        # 2軍 (属性があれば使用、なければダミー)
        rec_second = getattr(player, 'record_farm', PlayerRecord())
        
        # 3軍 (属性があれば使用、なければダミー)
        rec_third = getattr(player, 'record_third', PlayerRecord())

        tab_widget.addTab(self._create_stats_grid(player, rec_first), "一軍")
        tab_widget.addTab(self._create_stats_grid(player, rec_second), "二軍")
        tab_widget.addTab(self._create_stats_grid(player, rec_third), "三軍")

        layout.addWidget(tab_widget)
        return container

    def _create_stats_grid(self, player, record) -> QWidget:
        """Helper to create a stats grid for a specific record"""
        wrapper = QWidget()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 16, 0, 0)

        is_pitcher = player.position.value == "投手"
        stats_grid = QGridLayout()
        stats_grid.setSpacing(16)

        if is_pitcher:
            stats_data = [
                ("登板", str(record.games_pitched)),
                ("勝利", str(record.wins)),
                ("敗戦", str(record.losses)),
                ("セーブ", str(record.saves)),
                ("投球回", f"{record.innings_pitched:.1f}"),
                ("防御率", f"{record.era:.2f}" if record.innings_pitched > 0 else "-.--"),
                ("奪三振", str(record.strikeouts_pitched)),
                ("被安打", str(record.hits_allowed)),
                ("与四球", str(record.walks_allowed)),
                ("被本塁打", str(record.home_runs_allowed)),
            ]
        else:
            avg = record.batting_average if record.at_bats > 0 else 0
            stats_data = [
                ("打率", f".{int(avg * 1000):03d}" if record.at_bats > 0 else "---"),
                ("打数", str(record.at_bats)),
                ("安打", str(record.hits)),
                ("二塁打", str(record.doubles)),
                ("三塁打", str(record.triples)),
                ("本塁打", str(record.home_runs)),
                ("打点", str(record.rbis)),
                ("得点", str(record.runs)),
                ("四球", str(record.walks)),
                ("三振", str(record.strikeouts)),
                ("盗塁", str(record.stolen_bases)),
                ("盗塁死", str(record.caught_stealing)),
            ]

        for i, (stat_name, stat_value) in enumerate(stats_data):
            row = i // 6
            col = i % 6

            stat_container = QVBoxLayout()
            name_label = QLabel(stat_name)
            name_label.setStyleSheet(f"""
                font-size: 11px;
                color: {self.theme.text_muted};
                border: none;
                background: transparent;
            """)
            value_label = QLabel(stat_value)
            value_label.setStyleSheet(f"""
                font-size: 18px;
                font-weight: 700;
                color: {self.theme.text_primary};
                font-family: 'Consolas', monospace;
                border: none;
                background: transparent;
            """)
            stat_container.addWidget(name_label)
            stat_container.addWidget(value_label)

            item_wrapper = QWidget()
            item_wrapper.setLayout(stat_container)
            stats_grid.addWidget(item_wrapper, row, col)

        wrapper_layout.addLayout(stats_grid)
        return wrapper

    def _on_back(self):
        """Handle back button click"""
        self.back_requested.emit()