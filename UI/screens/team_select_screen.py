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
        
        self.setFixedHeight(40)  # 高さを確保
        self.setCursor(Qt.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 16, 0)
        layout.setSpacing(12)
        
        # League Indicator Bar
        self.bar = QFrame()
        self.bar.setFixedSize(4, 40)
        c = self.theme.north_league if league == "north" else self.theme.south_league
        self.bar.setStyleSheet(f"background-color: {c};")
        layout.addWidget(self.bar)
        
        # Name (等幅フォント)
        self.name_label = QLabel(team_name.upper())
        self.name_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 700;
            color: {self.theme.text_primary};
            letter-spacing: 1px;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            border: none;
        """)
        layout.addWidget(self.name_label)
        
        layout.addStretch()
        
        self._update_style()

    def set_selected(self, selected: bool):
        self._selected = selected
        if selected:
            self.bar.setFixedWidth(6)
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme.bg_card_hover};
                    border: none;
                    outline: none;
                }}
            """)
        else:
            self.bar.setFixedWidth(4)
            self._update_style()

    def _update_style(self):
        if not self._selected:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    text-align: left;
                    outline: none;
                }}
                QPushButton:hover {{
                    background-color: {self.theme.bg_card_elevated};
                }}
            """)

class StatRow(QWidget):
    """詳細パネル内の1行データ表示用"""
    def __init__(self, label, value, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 12px; border: none;")
        layout.addWidget(lbl)
        
        layout.addStretch()
        
        self.val = QLabel(str(value))
        self.val.setStyleSheet(f"color: {self.theme.text_primary}; font-size: 13px; font-weight: bold; font-family: 'Consolas', monospace; border: none;")
        layout.addWidget(self.val)

    def set_value(self, value):
        self.val.setText(str(value))

class TeamOverviewPanel(QFrame):
    """Large Data Display Panel - Enhanced"""
    
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
            QLabel {{
                border: none;
                background: transparent;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        # Header Section
        self.header_label = QLabel("NO DATA SELECTED")
        self.header_label.setStyleSheet(f"""
            font-size: 28px;
            font-weight: 700;
            color: {self.theme.text_primary};
            letter-spacing: 2px;
            font-family: 'Consolas', sans-serif;
        """)
        layout.addWidget(self.header_label)
        
        self.sub_header = QLabel("WAITING FOR INPUT...")
        self.sub_header.setStyleSheet(f"color: {self.theme.primary}; font-family: 'Consolas'; font-size: 14px; font-weight: bold;")
        layout.addWidget(self.sub_header)
        
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {self.theme.border}; border: none;")
        layout.addWidget(line)
        
        # Main Content Area
        content_layout = QGridLayout()
        content_layout.setSpacing(20)
        
        # --- Section 1: Team Info ---
        group1 = self._create_group_box("TEAM INFO")
        self.info_rows = {
            "BUDGET": StatRow("資金", "--"),
            "SALARY": StatRow("総年俸", "--"),
            "YEARS": StatRow("平均在籍", "--"),
            "AGE": StatRow("平均年齢", "--"),
        }
        for w in self.info_rows.values():
            group1.layout().addWidget(w)
        content_layout.addWidget(group1, 0, 0)
        
        # --- Section 2: Roster Breakdown ---
        group2 = self._create_group_box("ROSTER")
        self.roster_rows = {
            "TOTAL": StatRow("総人数", "--"),
            "PITCHERS": StatRow("投手", "--"),
            "CATCHERS": StatRow("捕手", "--"),
            "INFIELD": StatRow("内野手", "--"),
            "OUTFIELD": StatRow("外野手", "--"),
            "FOREIGN": StatRow("外国人", "--"),
        }
        for w in self.roster_rows.values():
            group2.layout().addWidget(w)
        content_layout.addWidget(group2, 0, 1)

        # --- Section 3: Performance Ratings (Batting) ---
        group3 = self._create_group_box("OFFENSE RATINGS")
        self.offense_rows = {
            "AVG_CONTACT": StatRow("ミート力", "--"),
            "AVG_POWER": StatRow("パワー", "--"),
            "AVG_SPEED": StatRow("走力", "--"),
            "BEST_BATTER": StatRow("注目打者", "--"),
        }
        for w in self.offense_rows.values():
            group3.layout().addWidget(w)
        content_layout.addWidget(group3, 1, 0)

        # --- Section 4: Performance Ratings (Pitching) ---
        group4 = self._create_group_box("PITCHING RATINGS")
        self.pitching_rows = {
            "AVG_VEL": StatRow("平均球速", "--"),
            "AVG_CTRL": StatRow("制球力", "--"),
            "AVG_STAMINA": StatRow("スタミナ", "--"),
            "BEST_PITCHER": StatRow("エース", "--"),
        }
        for w in self.pitching_rows.values():
            group4.layout().addWidget(w)
        content_layout.addWidget(group4, 1, 1)

        layout.addLayout(content_layout)
        layout.addStretch()
        
        # Confirm Button
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
                font-size: 16px;
                outline: none;
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

    def _create_group_box(self, title):
        box = QFrame()
        # 枠線(border)を削除しました
        box.setStyleSheet(f"background-color: {self.theme.bg_input}; border-radius: 4px; border: none;")
        l = QVBoxLayout(box)
        l.setContentsMargins(15, 15, 15, 15)
        l.setSpacing(5)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {self.theme.accent_blue}; font-size: 11px; font-weight: bold; margin-bottom: 5px; border: none;")
        l.addWidget(title_lbl)
        return box

    def set_team(self, team, name, league):
        self.header_label.setText(name.upper())
        league_display = "North League" if league.lower() == "north" else ("South League" if league.lower() == "south" else league)
        self.sub_header.setText(f"LEAGUE: {league_display} | STATUS: ACTIVE")
        self.confirm_btn.setEnabled(True)
        
        if team:
            players = team.players
            pitchers = [p for p in players if "投手" in str(p.position.value)]
            batters = [p for p in players if "投手" not in str(p.position.value)]
            catchers = [p for p in players if "捕手" in str(p.position.value)]
            infielders = [p for p in players if any(x in str(p.position.value) for x in ["一塁", "二塁", "三塁", "遊撃"])]
            outfielders = [p for p in players if "外野" in str(p.position.value)]
            foreign = [p for p in players if p.is_foreign]

            # Info
            budget_oku = team.budget / 100000000
            total_salary_oku = sum(p.salary for p in players) / 100000000
            avg_age = sum(p.age for p in players) / len(players) if players else 0
            avg_years = sum(p.years_pro for p in players) / len(players) if players else 0
            
            self.info_rows["BUDGET"].set_value(f"{budget_oku:.1f}億円")
            self.info_rows["SALARY"].set_value(f"{total_salary_oku:.1f}億円")
            self.info_rows["YEARS"].set_value(f"{avg_years:.1f}年")
            self.info_rows["AGE"].set_value(f"{avg_age:.1f}歳")

            # Roster
            self.roster_rows["TOTAL"].set_value(f"{len(players)}名")
            self.roster_rows["PITCHERS"].set_value(f"{len(pitchers)}名")
            self.roster_rows["CATCHERS"].set_value(f"{len(catchers)}名")
            self.roster_rows["INFIELD"].set_value(f"{len(infielders)}名")
            self.roster_rows["OUTFIELD"].set_value(f"{len(outfielders)}名")
            self.roster_rows["FOREIGN"].set_value(f"{len(foreign)}名")
            
            # Offense Stats
            if batters:
                avg_contact = sum(p.stats.contact for p in batters) / len(batters)
                avg_power = sum(p.stats.power for p in batters) / len(batters)
                avg_speed = sum(p.stats.speed for p in batters) / len(batters)
                best_batter = max(batters, key=lambda p: p.stats.overall_batting())
                
                self.offense_rows["AVG_CONTACT"].set_value(f"{avg_contact:.0f}")
                self.offense_rows["AVG_POWER"].set_value(f"{avg_power:.0f}")
                self.offense_rows["AVG_SPEED"].set_value(f"{avg_speed:.0f}")
                self.offense_rows["BEST_BATTER"].set_value(best_batter.name)
            else:
                for k in self.offense_rows: self.offense_rows[k].set_value("--")

            # Pitching Stats
            if pitchers:
                avg_vel = sum(p.stats.velocity for p in pitchers) / len(pitchers)
                avg_ctrl = sum(p.stats.control for p in pitchers) / len(pitchers)
                avg_stam = sum(p.stats.stamina for p in pitchers) / len(pitchers)
                best_pitcher = max(pitchers, key=lambda p: p.stats.overall_pitching())

                self.pitching_rows["AVG_VEL"].set_value(f"{avg_vel:.0f} km/h")
                self.pitching_rows["AVG_CTRL"].set_value(f"{avg_ctrl:.0f}")
                self.pitching_rows["AVG_STAMINA"].set_value(f"{avg_stam:.0f}")
                self.pitching_rows["BEST_PITCHER"].set_value(best_pitcher.name)
            else:
                for k in self.pitching_rows: self.pitching_rows[k].set_value("--")

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
            font-family: 'Consolas', monospace; text-align: left; font-size: 14px;
            outline: none;
        """)
        left_layout.addWidget(back)
        
        title = QLabel("TEAM SELECTION")
        title.setStyleSheet(f"font-size: 24px; font-weight: 300; letter-spacing: 4px; color: {self.theme.text_primary}; margin-top: 20px; margin-bottom: 20px; border: none;")
        left_layout.addWidget(title)
        
        # Team Lists (ScrollAreaを廃止し、QVBoxLayoutに直接配置)
        teams_container = QWidget()
        teams_layout = QVBoxLayout(teams_container)
        teams_layout.setContentsMargins(0, 0, 0, 0)
        teams_layout.setSpacing(4)
        
        self.items = []
        
        # Headers & Teams - Load from team_data_manager TEAM_CONFIGS
        from team_data_manager import TEAM_CONFIGS
        
        # Get teams by league (first 6 are North, last 6 are South based on config order)
        north_teams = ["Tokyo Bravers", "Osaka Thunders", "Nagoya Sparks",
                       "Hiroshima Phoenix", "Yokohama Mariners", "Shinjuku Spirits"]
        south_teams = ["Fukuoka Phoenix", "Saitama Bears", "Sendai Flames",
                       "Chiba Mariners", "Sapporo Fighters", "Kobe Buffaloes"]
        
        # Filter to only show teams that exist in TEAM_CONFIGS
        north_teams = [t for t in north_teams if t in TEAM_CONFIGS]
        south_teams = [t for t in south_teams if t in TEAM_CONFIGS]
        
        teams_layout.addWidget(self._create_header("NORTH ORBIT"))
        self._add_teams(teams_layout, "north", north_teams)
        
        teams_layout.addSpacing(20)
        
        teams_layout.addWidget(self._create_header("SOUTH ORBIT"))
        self._add_teams(teams_layout, "south", south_teams)
        
        teams_layout.addStretch()
        left_layout.addWidget(teams_container)
        
        layout.addWidget(left)
        
        # Right Panel: Details
        self.overview = TeamOverviewPanel()
        self.overview.confirm_btn.clicked.connect(self._on_confirm)
        layout.addWidget(self.overview)

    def _create_header(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {self.theme.accent_blue}; font-size: 12px; letter-spacing: 2px; font-weight: 700; margin-bottom: 8px; margin-top: 10px; border: none;")
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