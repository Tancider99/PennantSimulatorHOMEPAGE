# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Starfield Style Card Widgets
Industrial Sci-Fi Information Cards
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QGraphicsDropShadowEffect, QSizePolicy, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont

import sys
sys.path.insert(0, '..')
# UI.theme がインポートできない場合のフォールバック
try:
    from UI.theme import get_theme, Theme
except ImportError:
    pass

class Card(QFrame):
    """Base Industrial Card Widget"""

    clicked = Signal()

    def __init__(self, title: str = "", icon: str = "", parent=None):
        # 【修正】引数に icon を追加し、TradePage からの呼び出し (str, str) に対応
        
        # 互換性維持のための引数調整: 
        # 第2引数(icon)にQWidgetが渡された場合は parent とみなす
        real_parent = parent
        real_icon = icon
        
        if isinstance(icon, QWidget) and parent is None:
            real_parent = icon
            real_icon = ""

        # QFrameのコンストラクタには parent (QWidget) のみを渡す
        super().__init__(real_parent)
        
        try:
            self.theme = get_theme()
        except:
            from UI.theme import get_theme
            self.theme = get_theme()

        self._hover_progress = 0.0
        self._is_clickable = False
        self._title = title
        self._icon = real_icon  # アイコンを保存

        self.setObjectName("Card")
        self._setup_style()
        self._setup_layout()
        self._setup_animation()

    def _setup_style(self):
        # 角丸なし、枠線なし、背景色超控えめ
        self.setStyleSheet(f"""
            #Card {{
                background-color: rgba(30,33,38,0.7); /* bg_card, alpha控えめ */
                border: none;
                border-radius: 0px;
            }}
            #Card:hover {{
                background-color: rgba(38,42,48,0.8); /* bg_card_elevated, alpha控えめ */
            }}
        """)

    def _setup_layout(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # Header Section (Industrial Strip)
        if self._title:
            header = QFrame()
            header.setStyleSheet(f"""
                background-color: rgba(38,42,48,0.5); /* bg_card_elevated, alpha控えめ */
                border-bottom: none;
                border-radius: 0px;
            """)
            header_layout = QHBoxLayout(header)
            header_layout.setContentsMargins(16, 8, 16, 8)

            # Decorative square
            deco = QFrame()
            deco.setFixedSize(8, 8)
            deco.setStyleSheet(f"background-color: {self.theme.accent_orange}; border-radius: 0px;")
            header_layout.addWidget(deco)

            # Title
            title_label = QLabel(self._title)
            title_label.setStyleSheet(f"""
                font-size: 13px;
                font-weight: 700;
                color: {self.theme.text_primary};
                text-transform: uppercase;
                letter-spacing: 2px;
                background: transparent;
                border: none;
            """)
            header_layout.addWidget(title_label)
            
            # Icon (if present)
            if self._icon:
                icon_label = QLabel(self._icon)
                icon_label.setStyleSheet(f"""
                    font-size: 14px;
                    color: {self.theme.text_secondary};
                    margin-left: 8px;
                """)
                header_layout.addWidget(icon_label)

            header_layout.addStretch()
            
            # Tech ID
            tech_id = QLabel("DAT-01")
            tech_id.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 10px;")
            header_layout.addWidget(tech_id)

            self.main_layout.addWidget(header)

        # Content Area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(16, 16, 16, 16)
        self.content_layout.setSpacing(12)
        self.main_layout.addWidget(self.content_widget)

    def _setup_animation(self):
        self._animation = QPropertyAnimation(self, b"hover_progress")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.OutQuad)

    def get_hover_progress(self):
        return self._hover_progress

    def set_hover_progress(self, value):
        self._hover_progress = value

    hover_progress = Property(float, get_hover_progress, set_hover_progress)

    def set_clickable(self, clickable: bool):
        self._is_clickable = clickable
        self.setCursor(Qt.PointingHandCursor if clickable else Qt.ArrowCursor)

    def mousePressEvent(self, event):
        if self._is_clickable and event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def add_widget(self, widget: QWidget):
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        self.content_layout.addLayout(layout)

    def set_title(self, title: str):
        """Update the card title"""
        self._title = title
        # Find and update the title label in header
        for i in range(self.main_layout.count()):
            item = self.main_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                # Look for QLabel in header frame
                title_label = widget.findChild(QLabel)
                if title_label and hasattr(widget, 'layout'):
                    # Find the title label (second widget after deco)
                    header_layout = widget.layout()
                    if header_layout and header_layout.count() >= 2:
                        label_item = header_layout.itemAt(1)
                        if label_item and label_item.widget():
                            label_widget = label_item.widget()
                            if isinstance(label_widget, QLabel):
                                label_widget.setText(title)
                                return

class PremiumStatCard(Card):
    """HUD Style Stat Display"""

    def __init__(self, title: str, value: str, subtitle: str = "",
                 icon: str = None, color: str = None, parent=None):
        # Card.__init__ is compatible with keyword args
        super().__init__(title="", parent=parent)
        self.theme = get_theme()
        self._stat_color = color or self.theme.primary
        
        self.setStyleSheet(f"""
            #Card {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
            }}
            #Card:hover {{
                border-color: {self._stat_color};
            }}
        """)

        layout = QVBoxLayout()
        layout.setSpacing(4)

        # Header row
        header_row = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 600;
            color: {self.theme.text_secondary};
            text-transform: uppercase;
            letter-spacing: 2px;
        """)
        header_row.addWidget(title_label)
        header_row.addStretch()
        
        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet(f"font-size: 16px; color: {self._stat_color};")
            header_row.addWidget(icon_label)
        layout.addLayout(header_row)

        # Value
        self._value_label = QLabel(value)
        self._value_label.setStyleSheet(f"""
            font-family: "Consolas", monospace;
            font-size: 28px;
            font-weight: 700;
            color: {self.theme.text_primary};
        """)
        layout.addWidget(self._value_label)

        # Bar decoration
        bar = QFrame()
        bar.setFixedHeight(2)
        bar.setStyleSheet(f"background-color: {self._stat_color};")
        layout.addWidget(bar)

        if subtitle:
            self._subtitle_label = QLabel(subtitle)
            self._subtitle_label.setStyleSheet(f"""
                font-size: 11px;
                color: {self.theme.text_muted};
                margin-top: 4px;
            """)
            layout.addWidget(self._subtitle_label)

        self.add_layout(layout)

    def set_value(self, value: str):
        self._value_label.setText(value)

    def set_subtitle(self, subtitle: str):
        if hasattr(self, '_subtitle_label'):
            self._subtitle_label.setText(subtitle)

# Aliases
StatCard = PremiumStatCard
PremiumCard = Card 

class PlayerCard(Card):
    """ID Badge Style Player Card"""

    def __init__(self, player=None, show_stats: bool = True, parent=None):
        super().__init__(title="", parent=parent)
        self.theme = get_theme()
        self.player = player
        self.set_clickable(True)

        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        self._create_layout(show_stats)
        if player:
            self.set_player(player)

    def _create_layout(self, show_stats: bool):
        wrapper = QHBoxLayout()
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.setSpacing(0)

        # Left: Color Strip & Position Code
        self.pos_strip = QFrame()
        self.pos_strip.setFixedWidth(40)
        self.pos_strip.setStyleSheet(f"""
            background-color: {self.theme.bg_card_elevated};
            border-right: 1px solid {self.theme.border};
        """)
        pos_layout = QVBoxLayout(self.pos_strip)
        pos_layout.setContentsMargins(0, 10, 0, 10)
        
        self.pos_label = QLabel("POS")
        self.pos_label.setAlignment(Qt.AlignCenter)
        self.pos_label.setStyleSheet(f"""
            color: {self.theme.text_secondary};
            font-weight: 700;
            font-size: 12px;
        """)
        pos_layout.addWidget(self.pos_label)
        pos_layout.addStretch()
        wrapper.addWidget(self.pos_strip)

        # Right: Info
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(12, 10, 12, 10)
        info_layout.setSpacing(4)

        # Top row: Name & Number
        top_row = QHBoxLayout()
        self.name_label = QLabel("PLAYER NAME")
        self.name_label.setStyleSheet(f"""
            font-size: 16px;
            font-weight: 700;
            color: {self.theme.text_primary};
            text-transform: uppercase;
        """)
        top_row.addWidget(self.name_label)
        top_row.addStretch()
        
        self.number_label = QLabel("#00")
        self.number_label.setStyleSheet(f"""
            font-family: "Consolas", monospace;
            color: {self.theme.accent_orange};
            font-weight: 700;
        """)
        top_row.addWidget(self.number_label)
        info_layout.addLayout(top_row)

        # Rating Row
        rating_row = QHBoxLayout()
        rating_label = QLabel("OVR RATING")
        rating_label.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 10px; letter-spacing: 1px;")
        rating_row.addWidget(rating_label)
        rating_row.addStretch()
        
        self.overall_label = QLabel("00")
        self.overall_label.setStyleSheet(f"""
            font-family: "Consolas", monospace;
            font-size: 18px;
            font-weight: 700;
            color: {self.theme.text_primary};
        """)
        rating_row.addWidget(self.overall_label)
        info_layout.addLayout(rating_row)

        if show_stats:
            line = QFrame()
            line.setFixedHeight(1)
            line.setStyleSheet(f"background-color: {self.theme.border};")
            info_layout.addWidget(line)
            self.stats_layout = QHBoxLayout()
            info_layout.addLayout(self.stats_layout)

        wrapper.addWidget(info_widget)
        self.add_layout(wrapper)

    def set_player(self, player):
        self.player = player
        if not player: return

        self.name_label.setText(player.name)
        self.number_label.setText(f"#{player.uniform_number}")
        
        pos = player.position.value
        if pos == "投手":
            self.pos_label.setText("P")
            self.pos_strip.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-right: 3px solid {self.theme.accent_orange};")
        else:
            self.pos_label.setText(pos[:2]) 
            self.pos_strip.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-right: 3px solid {self.theme.accent_blue};")

        # 総合力を ★ 数値 で表示
        ovr = getattr(player, 'overall_rating', 0)
        self.overall_label.setText(f"★ {ovr}")
        color = self.theme.get_rating_color(ovr)
        self.overall_label.setStyleSheet(f"""
            font-family: "Consolas", monospace;
            font-size: 18px;
            font-weight: 700;
            color: {self.theme.gold}; /* テーマのゴールド色を使用 */
        """)

        if hasattr(self, 'stats_layout'):
            self._update_stats(player)

    def _update_stats(self, player):
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        stats = player.stats
        if player.position.value == "投手":
            items = [("SPD", stats.speed), ("CON", stats.control), ("STM", stats.stamina)]
        else:
            items = [("CON", stats.contact), ("PWR", stats.power), ("RUN", stats.run)]

        for label, val in items:
            col = QVBoxLayout()
            col.setSpacing(0)
            l = QLabel(label)
            l.setStyleSheet(f"font-size: 9px; color: {self.theme.text_muted};")
            # 1-99スケールをランク表示
            v = QLabel(Theme.get_rating_rank(val))
            v.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {Theme.get_rating_color(val)};")
            col.addWidget(l, alignment=Qt.AlignCenter)
            col.addWidget(v, alignment=Qt.AlignCenter)
            self.stats_layout.addLayout(col)

class TeamCard(Card):
    """Team Info Card"""

    def __init__(self, team=None, parent=None):
        super().__init__(title="TEAM OVERVIEW", parent=parent)
        self.theme = get_theme()
        self.team = team
        self.set_clickable(True)
        self._create_layout()
        if team:
            self.set_team(team)

    def _create_layout(self):
        # Header Info
        header = QHBoxLayout()
        self.name_label = QLabel("TEAM NAME")
        self.name_label.setStyleSheet(f"""
            font-size: 20px;
            font-weight: 700;
            color: {self.theme.text_primary};
            letter-spacing: 1px;
        """)
        header.addWidget(self.name_label)
        header.addStretch()
        self.add_layout(header)

        # League Info
        self.league_label = QLabel("LEAGUE")
        self.league_label.setStyleSheet(f"color: {self.theme.text_accent}; font-size: 12px; font-weight: 600; margin-bottom: 12px;")
        self.add_widget(self.league_label)

        # Record Grid
        grid = QGridLayout()
        grid.setSpacing(8)
        
        self.wins = self._create_stat_box("WINS")
        self.losses = self._create_stat_box("LOSS")
        self.draws = self._create_stat_box("DRAW")
        self.pct = self._create_stat_box("PCT")

        grid.addWidget(self.wins, 0, 0)
        grid.addWidget(self.losses, 0, 1)
        grid.addWidget(self.draws, 1, 0)
        grid.addWidget(self.pct, 1, 1)
        self.add_layout(grid)

    def _create_stat_box(self, label):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border: 1px solid {self.theme.border}; border-radius: 0;")
        l = QVBoxLayout(frame)
        l.setContentsMargins(8, 6, 8, 6)
        l.setSpacing(2)
        
        lbl = QLabel(label)
        lbl.setStyleSheet(f"font-size: 9px; color: {self.theme.text_muted};")
        l.addWidget(lbl)
        
        val = QLabel("--")
        val.setObjectName("value")
        val.setStyleSheet(f"font-family: 'Consolas'; font-size: 16px; font-weight: 700; color: {self.theme.text_primary};")
        l.addWidget(val)
        return frame

    def set_team(self, team):
        self.team = team
        if not team: return
        self.name_label.setText(team.name)
        self.league_label.setText(team.league.value)

        # チームカラー取得（例: セ・パで色分け、または team.color 属性があれば利用）
        team_color = None
        if hasattr(team, 'color') and team.color:
            team_color = team.color
        elif hasattr(team, 'league'):
            if team.league.value == "North League":
                team_color = self.theme.north_league
            elif team.league.value == "South League":
                team_color = self.theme.south_league
        # 背景色にチームカラー要素を反映（控えめな透明度）
        if team_color:
            self.setStyleSheet(f"""
                #Card {{
                    background-color: {team_color}33; /* チームカラー+控えめ透明度 */
                    border: none;
                    border-radius: 0px;
                }}
            """)
            self.name_label.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {self.theme.text_highlight if team_color.lower() in ['#0b0c10','#141619'] else team_color}; letter-spacing: 1px;")
        else:
            self.setStyleSheet(f"""
                #Card {{
                    background-color: rgba(30,33,38,0.7);
                    border: none;
                    border-radius: 0px;
                }}
            """)
            self.name_label.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {self.theme.text_primary}; letter-spacing: 1px;")

        self.wins.findChild(QLabel, "value").setText(str(team.wins))
        self.losses.findChild(QLabel, "value").setText(str(team.losses))
        self.draws.findChild(QLabel, "value").setText(str(team.draws))
        self.pct.findChild(QLabel, "value").setText(f".{int(team.winning_percentage * 1000):03d}")

class StandingsCard(Card):
    """Data Grid Style Standings"""

    def __init__(self, title: str = "LEAGUE STANDINGS", parent=None):
        super().__init__(title=title, parent=parent)
        self.theme = get_theme()
        self._create_layout()

    def _create_layout(self):
        header = QHBoxLayout()
        header.setContentsMargins(8, 0, 8, 8)
        headers = ["RANK", "TEAM", "W", "L", "D", "PCT", "GB"]
        widths = [40, 120, 40, 40, 40, 60, 40]
        
        for h, w in zip(headers, widths):
            lbl = QLabel(h)
            lbl.setFixedWidth(w)
            lbl.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 10px; font-weight: 700;")
            header.addWidget(lbl)
        
        self.add_layout(header)
        
        self.rows_layout = QVBoxLayout()
        self.rows_layout.setSpacing(2)
        self.add_layout(self.rows_layout)

    def set_standings(self, teams: list):
        while self.rows_layout.count():
            item = self.rows_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        top_pct = teams[0].winning_percentage if teams else 0
        
        for i, team in enumerate(teams):
            row = QWidget()
            row.setStyleSheet(f"background-color: {self.theme.bg_card_elevated if i % 2 == 0 else 'transparent'}; border-radius: 0;")
            layout = QHBoxLayout(row)
            layout.setContentsMargins(8, 4, 8, 4)
            
            widths = [40, 120, 40, 40, 40, 60, 40]
            
            rank = QLabel(f"{i+1}")
            rank.setFixedWidth(widths[0])
            rank.setStyleSheet(f"font-family: 'Consolas'; font-weight: 700; color: {self.theme.accent_orange if i < 3 else self.theme.text_secondary};")
            layout.addWidget(rank)
            
            name = QLabel(team.name)
            name.setFixedWidth(widths[1])
            name.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: 600;")
            layout.addWidget(name)
            
            for val in [team.wins, team.losses, team.draws]:
                l = QLabel(str(val))
                l.setFixedWidth(40)
                l.setStyleSheet(f"font-family: 'Consolas'; color: {self.theme.text_secondary};")
                layout.addWidget(l)
            
            pct = QLabel(f".{int(team.winning_percentage * 1000):03d}")
            pct.setFixedWidth(widths[5])
            pct.setStyleSheet(f"font-family: 'Consolas'; color: {self.theme.text_primary}; font-weight: 700;")
            layout.addWidget(pct)
            
            gb_val = "-" if i == 0 else f"{(top_pct - team.winning_percentage) * 143:.1f}"
            gb = QLabel(gb_val)
            gb.setFixedWidth(widths[6])
            gb.setStyleSheet(f"font-family: 'Consolas'; color: {self.theme.text_muted};")
            layout.addWidget(gb)
            
            self.rows_layout.addWidget(row)