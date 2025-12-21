from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGridLayout, QFrame, QScrollArea, QSizePolicy, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from UI.theme import get_theme
from UI.widgets.panels import ContentPanel
from UI.widgets.score_board import LineScoreTable
from UI.widgets.cards import Card, StatCard

class ScoreResultCard(Card):
    """Main Score Display with Line Score"""
    def __init__(self, parent=None):
        super().__init__(title="FINAL SCORE", parent=parent)
        self.theme = get_theme()
        self._setup_content()

    def _setup_content(self):
        layout = QVBoxLayout()
        layout.setSpacing(5) # Minimal spacing

        # Big Score Area
        score_container = QWidget()
        score_layout = QHBoxLayout(score_container)
        score_layout.setSpacing(10)
        score_layout.setContentsMargins(0, 5, 0, 5)
        score_layout.setAlignment(Qt.AlignCenter)

        # Away Team
        self.away_widget = self._create_team_score_widget()
        score_layout.addWidget(self.away_widget)

        # Separator (VS or -)
        sep = QLabel("-")
        sep.setStyleSheet(f"font-size: 24px; color: {self.theme.text_secondary}; font-weight: 300;")
        score_layout.addWidget(sep)

        # Home Team
        self.home_widget = self._create_team_score_widget()
        score_layout.addWidget(self.home_widget)

        layout.addWidget(score_container)

        # Line Score Table Container
        self.line_score_table = LineScoreTable()
        self.line_score_table.setFixedHeight(75) # Robust height (60 was too small)
        layout.addWidget(self.line_score_table)

        self.add_layout(layout)

    def _create_team_score_widget(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(2)
        
        name = QLabel("TEAM")
        name.setObjectName("name")
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {self.theme.text_secondary}; letter-spacing: 1px;")
        
        score = QLabel("0")
        score.setObjectName("score")
        score.setAlignment(Qt.AlignCenter)
        # Reduced from 48->36->32
        score.setStyleSheet(f"font-size: 32px; font-weight: 900; color: {self.theme.text_primary}; font-family: 'Consolas';")
        
        l.addWidget(name)
        l.addWidget(score)
        return w

    def set_score(self, h_name, a_name, h_score, a_score):
        # Away
        self.away_widget.findChild(QLabel, "name").setText(a_name)
        sc_a = self.away_widget.findChild(QLabel, "score")
        sc_a.setText(str(a_score))
        
        # Home
        self.home_widget.findChild(QLabel, "name").setText(h_name)
        sc_h = self.home_widget.findChild(QLabel, "score")
        sc_h.setText(str(h_score))

        # Colorize Winner
        base_color = self.theme.text_primary
        win_color = self.theme.accent_orange
        
        if h_score > a_score:
            sc_h.setStyleSheet(sc_h.styleSheet().replace(base_color, win_color))
            sc_a.setStyleSheet(sc_a.styleSheet().replace(win_color, base_color)) 
        elif a_score > h_score:
            sc_a.setStyleSheet(sc_a.styleSheet().replace(base_color, win_color))
            sc_h.setStyleSheet(sc_h.styleSheet().replace(win_color, base_color))
        else:
            sc_h.setStyleSheet(sc_h.styleSheet().replace(win_color, base_color))
            sc_a.setStyleSheet(sc_a.styleSheet().replace(win_color, base_color))

class PitchingResultCard(Card):
    """Win/Loss/Save Display"""
    def __init__(self, parent=None):
        super().__init__(title="PITCHING DECISIONS", parent=parent)
        self.theme = get_theme()
        self._setup_content()

    def _setup_content(self):
        grid = QGridLayout()
        grid.setSpacing(10) # Reduced

        self.win_lbl = self._create_row(grid, 0, "WIN", "胜利投手")
        self.loss_lbl = self._create_row(grid, 1, "LOSS", "敗戦投手")
        self.save_lbl = self._create_row(grid, 2, "SAVE", "セーブ")

        self.add_layout(grid)

    def _create_row(self, layout, row, label_en, label_jp):
        # Tag
        tag = QLabel(label_en)
        tag.setStyleSheet(f"font-size: 10px; font-weight: 800; color: {self.theme.text_muted}; background: {self.theme.bg_input}; padding: 2px 6px; border-radius: 4px;")
        tag.setFixedWidth(40)
        tag.setAlignment(Qt.AlignCenter)
        layout.addWidget(tag, row, 0)

        # Name
        name = QLabel("---")
        name.setStyleSheet(f"font-size: 12px; font-weight: 600; color: {self.theme.text_primary};")
        layout.addWidget(name, row, 1)

        return name

    def set_pitchers(self, win, loss, save):
        self.win_lbl.setText(win.name if win else "なし")
        self.loss_lbl.setText(loss.name if loss else "なし")
        self.save_lbl.setText(save.name if save else "なし")


class HighlightsCard(Card):
    """Home Runs and Batting Highlights"""
    def __init__(self, parent=None):
        super().__init__(title="GAME HIGHLIGHTS", parent=parent)
        self.theme = get_theme()
        self._setup_content()

    def _setup_content(self):
        # Home Runs
        l1 = QLabel("HOME RUNS")
        l1.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {self.theme.accent_blue}; margin-bottom: 5px;")
        self.add_widget(l1)

        self.hr_container = QWidget()
        self.hr_layout = QVBoxLayout(self.hr_container)
        self.hr_layout.setContentsMargins(0,0,0,0)
        self.hr_layout.setSpacing(2)
        self.add_widget(self.hr_container)
        
        # Placeholder for empty
        self.empty_lbl = QLabel("No Home Runs")
        self.empty_lbl.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 12px; font-style: italic;")
        self.hr_layout.addWidget(self.empty_lbl)

    def set_homeruns(self, hrs):
        # Clear existing
        while self.hr_layout.count():
            item = self.hr_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        if not hrs:
            # Recreate empty label since old one may have been deleted
            self.empty_lbl = QLabel("本塁打なし")
            self.empty_lbl.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 12px; font-style: italic;")
            self.hr_layout.addWidget(self.empty_lbl)
            return

        # Don't add empty label, just show HR data
        
        # Max limit to prevent layout explosion
        MAX_ITEMS = 5
        visible_items = hrs[:MAX_ITEMS]
        remaining = len(hrs) - MAX_ITEMS
        
        for item in visible_items:
            # Handle both dict format (from _analyze_highlights) and tuple format (legacy)
            if isinstance(item, dict):
                # Dict format: {"category": "PERFORMANCE", "message": "...", "team": "...", "score": 100}
                message = item.get("message", "")
                team = item.get("team", "")
                
                row = QHBoxLayout()
                msg_label = QLabel(message)
                msg_label.setStyleSheet(f"font-size: 12px; color: {self.theme.text_primary};")
                msg_label.setWordWrap(True)
                
                row.addWidget(msg_label)
                row.addStretch()
            else:
                # Tuple format: (name, count, team)
                try:
                    name, count, team = item
                except (ValueError, TypeError):
                    continue
                    
                row = QHBoxLayout()
                n = QLabel(name)
                n.setStyleSheet(f"font-size: 12px; color: {self.theme.text_primary}; font-weight: 600;")
                
                c = QLabel(f"({count}号)")
                c.setStyleSheet(f"font-size: 11px; color: {self.theme.text_secondary};")

                t = QLabel(team)
                t.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted}; background: {self.theme.bg_input}; padding: 1px 4px; border-radius: 3px;")

                row.addWidget(n)
                row.addWidget(c)
                row.addStretch()
                row.addWidget(t)
            
            w = QWidget()
            w.setLayout(row)
            self.hr_layout.addWidget(w)
            
        if remaining > 0:
            more_lbl = QLabel(f"... 他 {remaining} 件")
            more_lbl.setAlignment(Qt.AlignCenter)
            more_lbl.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted}; margin-top: 2px;")
            self.hr_layout.addWidget(more_lbl)

class BoxScoreCard(Card):
    """Full Box Score with Separate Tabs for Batting/Pitching (Side-by-Side)"""
    def __init__(self, parent=None):
        super().__init__(title="BOX SCORE", parent=parent)
        self.theme = get_theme()
        self._setup_content()

    def _setup_content(self):
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{
                background: {self.theme.bg_input};
                color: {self.theme.text_secondary};
                padding: 8px 16px; 
                margin-right: 2px;
                border-radius: 0px; /* Angular */
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background: #FFFFFF;
                color: #000000;
            }}
        """)
        self.add_widget(self.tabs)

    def set_data(self, h_team, a_team, game_stats):
        self.tabs.clear()
        
        # 1. Batting Tab
        bat_widget = QWidget()
        bat_layout = QHBoxLayout(bat_widget)
        bat_layout.setContentsMargins(0, 10, 0, 0)
        bat_layout.setSpacing(20)
        
        # Side-by-side batting panels (Visitor Left, Home Right)
        bat_layout.addWidget(self._create_stats_panel(a_team, game_stats, is_home=False, mode="batting"), stretch=1)
        bat_layout.addWidget(self._create_stats_panel(h_team, game_stats, is_home=True, mode="batting"), stretch=1)
        
        self.tabs.addTab(bat_widget, "Batting Stats")
        
        # 2. Pitching Tab
        pit_widget = QWidget()
        pit_layout = QHBoxLayout(pit_widget)
        pit_layout.setContentsMargins(0, 10, 0, 0)
        pit_layout.setSpacing(20)
        
        pit_layout.addWidget(self._create_stats_panel(a_team, game_stats, is_home=False, mode="pitching"), stretch=1)
        pit_layout.addWidget(self._create_stats_panel(h_team, game_stats, is_home=True, mode="pitching"), stretch=1)
        
        self.tabs.addTab(pit_widget, "Pitching Stats")

    def _create_stats_panel(self, team, game_stats, is_home, mode):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Team Header
        header = QLabel(f"{team.name} ({'HOME' if is_home else 'VISITOR'})")
        header.setStyleSheet(f"color: {self.theme.primary}; font-size: 13px; font-weight: bold; border-bottom: 2px solid {self.theme.primary}; padding-bottom: 4px;")
        layout.addWidget(header)

        # Extract stats
        batters, pitchers = self._extract_stats(team, game_stats)
        
        if mode == "batting":
            layout.addWidget(self._create_batter_table(batters))
        else:
            layout.addWidget(self._create_pitcher_table(pitchers))
        
        return container

    def _extract_stats(self, team, game_stats):
        batters = []
        pitchers = []
        
        # 1. Batters (Starters + Subs)
        processed_pids = set()
        
        # Starters
        for pid in team.current_lineup:
            if 0 <= pid < len(team.players):
                p = team.players[pid]
                if p not in processed_pids:
                    s = self._get_player_stats(p, game_stats)
                    # Include even if no plate app for starters
                    batters.append((p, s))
                    processed_pids.add(p)

        # Subs (Anyone else with stats)
        for p in team.players:
            if p in processed_pids: continue
            s = self._get_player_stats(p, game_stats)
            if s.get('plate_appearances', 0) > 0:
                batters.append((p, s))
                processed_pids.add(p)
                
        # Pitchers (Anyone with pitching stats)
        for p in team.players:
            s = self._get_player_stats(p, game_stats)
            if s.get('innings_pitched', 0) > 0 or s.get('games_pitched', 0) > 0:
                pitchers.append((p, s))
                
        return batters, pitchers

    def _get_player_stats(self, player, game_stats):
        if player in game_stats: return game_stats[player]
        return {}

    def _create_batter_table(self, player_stats_pairs):
        cols = ["NAME", "AVG", "AB", "H", "HR", "RBI", "SO", "BB"]
        t = self._create_base_table(cols)
        t.setRowCount(len(player_stats_pairs))
        
        for i, (p, s) in enumerate(player_stats_pairs):
            avg = f"{p.record.batting_average:.3f}"
            row_data = [
                p.name, avg, 
                str(s.get('at_bats', 0)), str(s.get('hits', 0)),
                str(s.get('home_runs', 0)), str(s.get('rbis', 0)),
                str(s.get('strikeouts', 0)), str(s.get('walks', 0))
            ]
            for c, val in enumerate(row_data):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter if c > 0 else Qt.AlignLeft | Qt.AlignVCenter)
                t.setItem(i, c, item)
        return t

    def _create_pitcher_table(self, player_stats_pairs):
        cols = ["NAME", "ERA", "IP", "H", "R", "SO", "BB"]
        t = self._create_base_table(cols)
        t.setRowCount(len(player_stats_pairs))
        
        for i, (p, s) in enumerate(player_stats_pairs):
            era = f"{p.record.era:.2f}"
            ip_val = s.get('innings_pitched', 0.0)
            outs = int(round(ip_val * 3))
            ip = f"{outs // 3}.{outs % 3}"
            
            row_data = [
                p.name, era, ip, 
                str(s.get('hits_allowed', 0)), str(s.get('runs_allowed', 0)),
                str(s.get('strikeouts_pitched', 0)), str(s.get('walks_allowed', 0))
            ]
            for c, val in enumerate(row_data):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter if c > 0 else Qt.AlignLeft | Qt.AlignVCenter)
                t.setItem(i, c, item)
        return t

    def _create_base_table(self, headers):
        t = QTableWidget()
        t.setColumnCount(len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.verticalHeader().setVisible(False)
        t.setShowGrid(False)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setSelectionMode(QAbstractItemView.NoSelection)
        t.setFocusPolicy(Qt.NoFocus)
        t.setStyleSheet(f"""
            QTableWidget {{ background: transparent; border: none; }}
            QHeaderView::section {{ background: transparent; color: {self.theme.text_secondary}; font-size: 10px; font-weight: bold; border: none; padding: 2px; }}
            QTableWidget::item {{ color: {self.theme.text_primary}; padding: 2px; border-bottom: 1px solid {self.theme.border_muted}; font-size: 12px; }}
        """)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch) # Name stretches
        
        # Compact rows for "Single Screen"
        t.verticalHeader().setDefaultSectionSize(24)
        t.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding) # Flexible height
        return t


class GameResultPage(ContentPanel):
    """
    Modern Sci-Fi Dashboard Style Game Result Page
    """
    return_home = Signal()
    return_schedule = Signal()  # For returning to schedule page from past game view

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._setup_ui()

    def _setup_ui(self):
        # Main Layout
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(15)

        # Dashboard Container
        dashboard = QVBoxLayout()
        dashboard.setSpacing(15)
        self.content_layout.addLayout(dashboard)

        # 1. Top Section: Score Result & Line Score
        self.score_card = ScoreResultCard()
        # Slightly reduce height impact
        # self.score_card.setFixedHeight(220) 
        dashboard.addWidget(self.score_card)

        # 2. Bottom Section: Split Left (Box) vs Right (Pitcher/Highlights)
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(15)
        dashboard.addLayout(bottom_row, stretch=1)

        # Left: Box Score
        self.box_score_card = BoxScoreCard()
        bottom_row.addWidget(self.box_score_card, stretch=6)

        # Right: Pitching & Highlights
        right_col = QVBoxLayout()
        right_col.setSpacing(15)
        
        self.pitcher_card = PitchingResultCard()
        # self.pitcher_card.setFixedHeight(180)
        right_col.addWidget(self.pitcher_card)
        
        self.highlight_card = HighlightsCard()
        right_col.addWidget(self.highlight_card, stretch=1)
        
        bottom_row.addLayout(right_col, stretch=4)
        
        # Footer: Return Button
        btn_box = QHBoxLayout()
        btn_box.addStretch()
        self.btn_home = QPushButton("BACK TO HOME")
        self.btn_home.setCursor(Qt.PointingHandCursor)
        self.btn_home.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: #000000;
                font-weight: 700;
                padding: 12px 40px;
                border: 1px solid #CCCCCC;
                border-radius: 0px;
                font-size: 14px;
                letter-spacing: 2px;
            }}
            QPushButton:hover {{
                background-color: #F0F0F0;
                border: 1px solid #AAAAAA;
            }}
        """)
        # Default behavior (will be overridden by set_mode)
        self.btn_home.clicked.connect(self.return_home.emit)
        btn_box.addWidget(self.btn_home)
        btn_box.addStretch()
        
        dashboard.addLayout(btn_box)

    def set_mode(self, is_past_game: bool):
        """戻るボタンの挙動を設定"""
        try: self.btn_home.clicked.disconnect()
        except: pass
            
        if is_past_game:
            self.btn_home.setText("BACK TO SCHEDULE")
            self.btn_home.clicked.connect(self.return_schedule.emit)
        else:
            self.btn_home.setText("BACK TO HOME")
            self.btn_home.clicked.connect(self.return_home.emit)

    def set_result(self, data):
        # Unpack Data
        if not data: return
        
        h_team = data["home_team"]
        a_team = data["away_team"]
        h_score = data["home_score"]
        a_score = data["away_score"]
        
        # Score Card
        self.score_card.set_score(h_team.name, a_team.name, h_score, a_score)
        
        # Line Score - Support both score_history (from live games) and home_innings/away_innings (from past games)
        score_hist = data.get("score_history", None)
        if score_hist:
            top_scores = score_hist.get("top", [])
            bot_scores = score_hist.get("bot", [])
        else:
            # Use home_innings/away_innings from past game data
            # Note: top = away (visitor bats first), bot = home
            top_scores = data.get("away_innings", [])
            bot_scores = data.get("home_innings", [])
        
        # Determine max inning (remove trailing zeros/nones?)
        # Use actual length
        max_inn = max(len(top_scores), len(bot_scores))
        if max_inn < 9: max_inn = 9 # Minimum 9
            
        self.score_card.line_score_table.set_inning_count(max_inn)
        self.score_card.line_score_table.update_names(h_team.name, a_team.name)
        
        # Set innings
        for i in range(len(top_scores)):
             if top_scores[i] is not None:
                self.score_card.line_score_table.set_inning_score(i+1, True, top_scores[i])
        for i in range(len(bot_scores)):
             if bot_scores[i] is not None:
                self.score_card.line_score_table.set_inning_score(i+1, False, bot_scores[i])
                
        # Total Stats (R, H, E)
        hits = data.get("hits", (0, 0))
        errs = data.get("errors", (0, 0))
        self.score_card.line_score_table.update_score_data(
            h_score, a_score, hits[0], hits[1], errs[0], errs[1]
        )

        # Pitching Result
        p_res = data.get("pitcher_result", {})
        self.pitcher_card.set_pitchers(p_res.get("win"), p_res.get("loss"), p_res.get("save"))
        
        # Highlights
        hrs = data.get("home_runs", [])
        self.highlight_card.set_homeruns(hrs)
        
        # Box Score
        g_stats = data.get("game_stats", {})
        self.box_score_card.set_data(h_team, a_team, g_stats)

        


