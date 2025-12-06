# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Team Selection Screen
Starfield Style Mission Briefing Interface
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGridLayout, QScrollArea, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, Signal, Property, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPainter, QPen

from UI.theme import get_theme

class TeamListItem(QPushButton):
    """Selectable Team Item (Data Strip)"""
    
    def __init__(self, team_name: str, league: str, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._team_name = team_name
        self._league = league
        self._selected = False
        
        self.setFixedHeight(32)
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 16, 0)
        layout.setSpacing(12)
        
        # League Indicator Bar
        self.bar = QFrame()
        self.bar.setFixedSize(4, 32)
        c = self.theme.central_league if league == "central" else self.theme.pacific_league
        self.bar.setStyleSheet(f"background-color: {c};")
        layout.addWidget(self.bar)
        
        # Name
        self.name_label = QLabel(team_name.upper())
        self.name_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {self.theme.text_primary};
            letter-spacing: 1px;
        """)
        layout.addWidget(self.name_label)
        
        layout.addStretch()
        
        # Selection Marker
        self.marker = QLabel("◄")
        self.marker.setStyleSheet(f"color: {self.theme.primary}; font-size: 12px;")
        self.marker.hide()
        layout.addWidget(self.marker)
        
        self._update_style()

    def set_selected(self, selected: bool):
        self._selected = selected
        if selected:
            self.marker.show()
            self.name_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: 700;")
            self.setStyleSheet(f"background-color: {self.theme.bg_card_hover}; border: none; border-radius: 0px;")
        else:
            self.marker.hide()
            self.name_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: 700;")
            self._update_style()

    def _update_style(self):
        if not self._selected:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    border-radius: 0px;
                    text-align: left;
                }}
                QPushButton:hover {{
                    background-color: {self.theme.bg_card_elevated};
                }}
            """)

class StatBox(QFrame):
    """Industrial Stat Box"""
    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.setStyleSheet(f"""
            background-color: {self.theme.bg_card};
            border: none;
            border-radius: 0px;
        """)
        l = QVBoxLayout(self)
        l.setContentsMargins(12, 8, 12, 8)
        l.setSpacing(2)
        
        self.lbl = QLabel(label)
        self.lbl.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 10px; text-transform: uppercase;")
        l.addWidget(self.lbl)
        
        self.val = QLabel("--")
        self.val.setStyleSheet(f"color: {self.theme.text_primary}; font-size: 18px; font-family: 'Consolas'; font-weight: 700;")
        l.addWidget(self.val)

    def set_value(self, value):
        self.val.setText(str(value))

class TeamOverviewPanel(QFrame):
    """Large Data Display Panel"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._setup_ui()
        
    def _setup_ui(self):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                border-top: 4px solid {self.theme.primary};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        self.header_label = QLabel("NO DATA SELECTED")
        self.header_label.setStyleSheet(f"""
            font-size: 32px;
            font-weight: 300;
            color: {self.theme.text_primary};
            letter-spacing: 4px;
        """)
        layout.addWidget(self.header_label)
        
        self.sub_header = QLabel("WAITING FOR INPUT...")
        self.sub_header.setStyleSheet(f"color: {self.theme.text_secondary}; font-family: 'Consolas';")
        layout.addWidget(self.sub_header)
        
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {self.theme.border};")
        layout.addWidget(line)
        
        # Stats Grid
        self.stats_grid = QGridLayout()
        self.stats_grid.setSpacing(10)
        
        self.boxes = {}
        keys = [("PLAYERS", 0, 0), ("PITCHERS", 0, 1), ("BATTERS", 0, 2),
                ("AVG AGE", 1, 0), ("AVG OVR", 1, 1), ("STAR", 1, 2)]
        
        for k, r, c in keys:
            box = StatBox(k)
            self.boxes[k] = box
            self.stats_grid.addWidget(box, r, c)
            
        layout.addLayout(self.stats_grid)
        
        # Confirm Button (Industrial Style)
        layout.addStretch()
        self.confirm_btn = QPushButton("INITIATE SEQUENCE [CONFIRM]")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setCursor(Qt.PointingHandCursor)
        self.confirm_btn.setFixedHeight(50)
        self.confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.bg_card_elevated};
                color: {self.theme.text_muted};
                border: 1px solid {self.theme.border};
                font-family: 'Consolas';
                font-weight: 700;
                letter-spacing: 2px;
            }}
            QPushButton:enabled {{
                background-color: {self.theme.primary};
                color: {self.theme.bg_darkest};
                border-color: {self.theme.primary};
            }}
            QPushButton:enabled:hover {{
                background-color: {self.theme.primary_hover};
            }}
        """)
        layout.addWidget(self.confirm_btn)

    def set_team(self, team, name, league):
        self.header_label.setText(name.upper())
        self.sub_header.setText(f"LEAGUE: {league.upper()} | STATUS: ACTIVE")
        self.confirm_btn.setEnabled(True)
        
        # Update boxes (Mock data logic)
        if team:
            players = team.players
            self.boxes["PLAYERS"].set_value(len(players))
            self.boxes["PITCHERS"].set_value(len([p for p in players if p.position.value == "投手"]))
            self.boxes["BATTERS"].set_value(len([p for p in players if p.position.value != "投手"]))
            
            avg_ovr = sum(p.overall_rating for p in players) / len(players) if players else 0
            self.boxes["AVG OVR"].set_value(f"{avg_ovr:.1f}")
            self.boxes["AVG AGE"].set_value(f"{24.5}") # Placeholder
            
            top = max(players, key=lambda p: p.overall_rating) if players else None
            self.boxes["STAR"].set_value(top.name if top else "--")

class TeamSelectScreen(QWidget):
    """Starfield Style Team Select"""
    
    team_selected = Signal(str)
    back_clicked = Signal()
    confirm_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._teams_data = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(40)
        
        # Left Panel: Navigation / List
        left = QWidget()
        left.setFixedWidth(400)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Back Button
        back = QPushButton("<< RETURN")
        back.clicked.connect(self.back_clicked.emit)
        back.setStyleSheet(f"""
            background: transparent; border: none; color: {self.theme.text_muted};
            font-family: 'Consolas'; text-align: left;
        """)
        left_layout.addWidget(back)
        
        title = QLabel("TEAM SELECTION")
        title.setStyleSheet(f"font-size: 24px; font-weight: 300; letter-spacing: 4px; color: {self.theme.text_primary}; margin-top: 10px;")
        left_layout.addWidget(title)
        
        # Team Lists
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(2)
        
        self.items = []
        
        # Headers
        scroll_layout.addWidget(self._create_header("CENTRAL ORBIT"))
        self._add_teams(scroll_layout, "central", [
            "Yomiuri Giants", "Hanshin Tigers", "Chunichi Dragons",
            "Hiroshima Toyo Carp", "Yokohama DeNA BayStars", "Tokyo Yakult Swallows"
        ])
        
        scroll_layout.addSpacing(20)
        
        scroll_layout.addWidget(self._create_header("PACIFIC ORBIT"))
        self._add_teams(scroll_layout, "pacific", [
            "Fukuoka SoftBank Hawks", "Saitama Seibu Lions", "Tohoku Rakuten Golden Eagles",
            "Chiba Lotte Marines", "Hokkaido Nippon-Ham Fighters", "Orix Buffaloes"
        ])
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll)
        
        layout.addWidget(left)
        
        # Right Panel: Details
        self.overview = TeamOverviewPanel()
        self.overview.confirm_btn.clicked.connect(self._on_confirm)
        layout.addWidget(self.overview)

    def _create_header(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {self.theme.accent_blue}; font-size: 11px; letter-spacing: 2px; font-weight: 700; margin-bottom: 8px;")
        return lbl

    def _add_teams(self, layout, league, names):
        for name in names:
            item = TeamListItem(name, league)
            item.clicked.connect(lambda c=False, n=name, l=league, i=item: self._on_select(n, l, i))
            layout.addWidget(item)
            self.items.append(item)

    def _on_select(self, name, league, item):
        for i in self.items: i.set_selected(False)
        item.set_selected(True)
        
        self._selected_team = name
        team_obj = self._teams_data.get(name)
        self.overview.set_team(team_obj, name, league)

    def _on_confirm(self):
        if hasattr(self, '_selected_team'):
            self.confirm_clicked.emit(self._selected_team)

    def set_teams(self, c_teams, p_teams):
        for t in c_teams + p_teams:
            self._teams_data[t.name] = t