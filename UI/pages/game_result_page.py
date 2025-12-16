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
        layout.setSpacing(20)

        # Big Score Area
        score_container = QWidget()
        score_layout = QHBoxLayout(score_container)
        score_layout.setSpacing(40)
        score_layout.setContentsMargins(0, 10, 0, 10)
        score_layout.setAlignment(Qt.AlignCenter)

        # Away Team
        self.away_widget = self._create_team_score_widget()
        score_layout.addWidget(self.away_widget)

        # Separator (VS or -)
        sep = QLabel("-")
        sep.setStyleSheet(f"font-size: 40px; color: {self.theme.text_secondary}; font-weight: 300;")
        score_layout.addWidget(sep)

        # Home Team
        self.home_widget = self._create_team_score_widget()
        score_layout.addWidget(self.home_widget)

        layout.addWidget(score_container)

        # Line Score Table Container
        self.line_score_table = LineScoreTable()
        self.line_score_table.setFixedHeight(95)
        # Remove default styling of table to blend with card if needed, 
        # but LineScoreTable has its own strong style. We keep it as is.
        layout.addWidget(self.line_score_table)

        self.add_layout(layout)

    def _create_team_score_widget(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setSpacing(5)
        
        name = QLabel("TEAM")
        name.setObjectName("name")
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet(f"font-size: 20px; font-weight: 700; color: {self.theme.text_secondary}; letter-spacing: 1px;")
        
        score = QLabel("0")
        score.setObjectName("score")
        score.setAlignment(Qt.AlignCenter)
        score.setStyleSheet(f"font-size: 64px; font-weight: 900; color: {self.theme.text_primary}; font-family: 'Consolas';")
        
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
            sc_a.setStyleSheet(sc_a.styleSheet().replace(win_color, base_color)) # Reset loser
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
        grid.setSpacing(15)

        self.win_lbl = self._create_row(grid, 0, "WIN", "胜利投手")
        self.loss_lbl = self._create_row(grid, 1, "LOSS", "敗戦投手")
        self.save_lbl = self._create_row(grid, 2, "SAVE", "セーブ")

        self.add_layout(grid)

    def _create_row(self, layout, row, label_en, label_jp):
        # Tag
        tag = QLabel(label_en)
        tag.setStyleSheet(f"font-size: 10px; font-weight: 800; color: {self.theme.text_muted}; background: {self.theme.bg_input}; padding: 4px 8px; border-radius: 4px;")
        tag.setFixedWidth(50)
        tag.setAlignment(Qt.AlignCenter)
        layout.addWidget(tag, row, 0)

        # Name
        name = QLabel("---")
        name.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {self.theme.text_primary};")
        layout.addWidget(name, row, 1)

        # Stat (e.g. W-L or S) - Optional, here we stick to simple replacement
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
        self.hr_layout.setSpacing(4)
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
            self.hr_layout.addWidget(self.empty_lbl)
            self.empty_lbl.setVisible(True)
            return

        self.empty_lbl.setVisible(False)
        for name, count, team in hrs:
            row = QHBoxLayout()
            n = QLabel(name)
            n.setStyleSheet(f"font-size: 13px; color: {self.theme.text_primary}; font-weight: 600;")
            
            c = QLabel(f"({count}号)")
            c.setStyleSheet(f"font-size: 12px; color: {self.theme.text_secondary};")

            t = QLabel(team)
            t.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted}; background: {self.theme.bg_input}; padding: 2px 6px; border-radius: 3px;")

            row.addWidget(n)
            row.addWidget(c)
            row.addStretch()
            row.addWidget(t)
            
            w = QWidget()
            w.setLayout(row)
            self.hr_layout.addWidget(w)

class BoxScoreCard(Card):
    """Full Box Score with Tabs for Teams"""
    def __init__(self, parent=None):
        super().__init__(title="BOX SCORE", parent=parent)
        self.theme = get_theme()
        self._setup_content()

    def _setup_content(self):
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{
                background: {self.theme.bg_card};
                color: {self.theme.text_secondary};
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                font-weight: bold;
            }}
            QTabBar::tab:selected {{
                background: {self.theme.bg_card_elevated};
                color: {self.theme.accent_orange};
                border-bottom: 2px solid {self.theme.accent_orange};
            }}
        """)
        self.add_widget(self.tabs)

    def set_data(self, h_team, a_team, game_stats):
        self.tabs.clear()
        self.tabs.addTab(self._create_team_stats(a_team, game_stats), a_team.name)
        self.tabs.addTab(self._create_team_stats(h_team, game_stats), h_team.name)

    def _create_team_stats(self, team, game_stats):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 10, 0, 0)
        l.setSpacing(15)

        # Split stats into Batters and Pitchers
        batters = []
        pitchers = []
        
        # Filter stats for this team
        team_players = set(team.players)
        
        # Sort by lineup order for batters?
        # A simple approach: Iterate team.current_lineup for starters, then others
        # But game_stats only has players who played.
        
        # Batters:
        # First, starters in order
        for pid in team.current_lineup:
            p = team.players[pid]
            s = self._get_player_stats(p, game_stats)
            if s.get('pa', 0) > 0 or s.get('games_pitched', 0) == 0: # Ensure fielders show up even if 0 PA but played? Or just PA > 0
                if s.get('pa', 0) > 0: # Only show if they had PA
                    batters.append((p, s))
        
        # Then substitutes (search all players in team)
        for p in team.players:
            # Skip if already added
            if any(b[0].name == p.name and b[0].uniform_number == p.uniform_number for b in batters):
                continue
            
            s = self._get_player_stats(p, game_stats)
            if s.get('pa', 0) > 0:
                batters.append((p, s))
                
        # Pitchers:
        # Include anyone who pitched (ip_outs > 0 or games_pitched > 0)
        for p in team.players:
            s = self._get_player_stats(p, game_stats)
            if s.get('ip_outs', 0) > 0 or s.get('games_pitched', 0) > 0:
                pitchers.append((p, s))
        
        # Also check game_stats for players who might not be in the current team object list?
        # (Rare case: trade/release mid-game? Unlikely in this sim scope)
        # But we should iterate game_stats keys to find any missed "phantom" players just in case
        for p_key, stats in game_stats.items():
            # Check if this player belongs to this team (by name match?)
            # This is hard without team ref in p_key. 
            # Skipping for now as team.players iteration covers 99% cases.
            pass
                
        # Batting Table
        l.addWidget(self._create_section_label("BATTING"))
        l.addWidget(self._create_batter_table(batters))
        
        # Pitching Table
        l.addWidget(self._create_section_label("PITCHING"))
        l.addWidget(self._create_pitcher_table(pitchers))
        
        return w

    def _get_player_stats(self, player, game_stats):
        """Robust lookup for player stats"""
        # 1. Direct lookup
        if player in game_stats:
            return game_stats[player]
        
        # 2. Fallback: Match by Name + Number
        # Game stats keys might be different instances (due to copy/pickle?)
        for p_key, stats in game_stats.items():
            if p_key.name == player.name and p_key.uniform_number == player.uniform_number:
                return stats
        return {}

    def _create_section_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 11px; font-weight: 700; border-bottom: 1px solid {self.theme.border}; padding-bottom: 4px;")
        return lbl

    def _create_batter_table(self, player_stats_pairs):
        cols = ["NAME", "AVG", "AB", "R", "H", "RBI", "HR", "SO", "BB"]
        t = self._create_base_table(cols)
        t.setRowCount(len(player_stats_pairs))
        
        for i, (p, s) in enumerate(player_stats_pairs):
            # s is already the stats dictionary
            record = p.record # Seasonal record for AVG
            avg = f"{record.batting_average:.3f}"
            row_data = [
                p.name, avg, 
                str(s.get('ab', 0)), str(s.get('run', 0)), str(s.get('h', 0)),
                str(s.get('rbi', 0)), str(s.get('hr', 0)), str(s.get('so', 0)), str(s.get('bb', 0))
            ]
            for c, val in enumerate(row_data):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter if c > 0 else Qt.AlignLeft | Qt.AlignVCenter)
                t.setItem(i, c, item)
        return t

    def _create_pitcher_table(self, player_stats_pairs):
        cols = ["NAME", "ERA", "IP", "H", "R", "ER", "SO", "BB"]
        t = self._create_base_table(cols)
        t.setRowCount(len(player_stats_pairs))
        
        for i, (p, s) in enumerate(player_stats_pairs):
            # s is already the stats dictionary
            record = p.record
            era = f"{record.era:.2f}"
            
            outs = s.get('ip_outs', 0)
            ip = f"{outs // 3}.{outs % 3}"
            
            row_data = [
                p.name, era, ip, 
                str(s.get('p_h', 0)), str(s.get('p_run', 0)), str(s.get('er', 0)),
                str(s.get('p_so', 0)), str(s.get('p_bb', 0))
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
            QHeaderView::section {{ background: transparent; color: {self.theme.text_secondary}; font-size: 10px; font-weight: bold; border: none; }}
            QTableWidget::item {{ color: {self.theme.text_primary}; padding: 4px; border-bottom: 1px solid {self.theme.border_muted}; }}
        """)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        t.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        # Calculate height roughly
        t.setFixedHeight(300) # Fixed height or dynamic?
        return t


class GameResultPage(ContentPanel):
    """
    Modern Sci-Fi Dashboard Style Game Result Page
    """
    return_home = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._setup_ui()

    def _setup_ui(self):
        # Main Layout
        self.content_layout.setContentsMargins(40, 30, 40, 30)
        self.content_layout.setSpacing(20)

        # Scroll Area for result content (Box score can be long)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setSpacing(20)
        self.scroll.setWidget(self.scroll_content)
        
        # Header Section
        self._create_header()

        # Dashboard Grid
        grid = QGridLayout()
        grid.setSpacing(20)
        
        # Main Score Card (Top Full Width)
        self.score_card = ScoreResultCard()
        grid.addWidget(self.score_card, 0, 0, 1, 2) # Row 0, Col 0, Span 1x2

        # Pitching Decisions (Row 1, Left)
        self.pitching_card = PitchingResultCard()
        self.pitching_card.setFixedHeight(200) # Fixed height for aesthetics
        grid.addWidget(self.pitching_card, 1, 0)

        # Highlights (Row 1, Right)
        self.highlights_card = HighlightsCard()
        self.highlights_card.setFixedHeight(200)
        grid.addWidget(self.highlights_card, 1, 1)

        self.scroll_layout.addLayout(grid)

        # Box Score (Full Width, below grid)
        self.box_score_card = BoxScoreCard()
        self.scroll_layout.addWidget(self.box_score_card)

        self.add_widget(self.scroll)

        # Footer Actions
        self._create_footer()

    def _create_header(self):
        header_widget = QWidget()
        layout = QHBoxLayout(header_widget)
        layout.setContentsMargins(0, 0, 0, 20)
        
        title = QLabel("GAME RESULT")
        title.setStyleSheet(f"""
            font-size: 24px; 
            font-weight: 800; 
            color: {self.theme.text_primary}; 
            letter-spacing: 2px;
        """)
        
        self.date_label = QLabel("2027-04-01")
        self.date_label.setStyleSheet(f"font-size: 14px; color: {self.theme.text_muted}; font-weight: 600;")
        
        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.date_label)
        
        self.content_layout.addWidget(header_widget) # Add directly to main layout (fixed header)

    def _create_footer(self):
        footer = QWidget()
        layout = QHBoxLayout(footer)
        layout.setAlignment(Qt.AlignCenter)
        
        btn = QPushButton("RETURN TO HOME")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedSize(280, 50)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.text_primary};
                color: {self.theme.bg_dark};
                border: none;
                border-radius: 0px;
                font-size: 14px;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.text_secondary};
            }}
        """)
        btn.clicked.connect(self.return_home.emit)
        
        layout.addWidget(btn)
        self.content_layout.addWidget(footer)

    def set_result(self, result_data):
        if not result_data: return
        d = result_data
        
        h_team = d['home_team']
        a_team = d['away_team']
        
        # Update Header
        self.date_label.setText(d.get('date', 'Today'))

        # Update Score Card
        self.score_card.set_score(h_team.name, a_team.name, d['home_score'], d['away_score'])
        
        # Score History Logic
        hist = d.get('score_history', {'top': [], 'bot': []})
        top_scores = hist.get('top', [])
        bot_scores = hist.get('bot', [])
        
        # Determine strict max inning based on data presence
        # Filter out trailing/placeholder None/0 if not needed?
        # Typically we want at least 9, unless it's a cold game.
        # But user requested "hide unplayed". So we count innings with actual data.
        # In PennantSimulator, empty innings might be None or 0.
        # We assume len(top_scores) is the number of innings started.
        
        max_inn = max(len(top_scores), len(bot_scores))
        
        # Update Line Score Columns
        self.score_card.line_score_table.set_inning_count(max_inn)
        self.score_card.line_score_table.update_names(h_team.name, a_team.name)
        
        for i in range(max_inn):
            s_top = top_scores[i] if i < len(top_scores) else ""
            s_bot = bot_scores[i] if i < len(bot_scores) else ""
            self.score_card.line_score_table.set_inning_score(i+1, True, s_top)
            self.score_card.line_score_table.set_inning_score(i+1, False, s_bot)
            
        hits = d.get('hits', (0,0))
        errs = d.get('errors', (0,0))
        self.score_card.line_score_table.update_score_data(
            d['home_score'], d['away_score'],
            hits[0], hits[1],
            errs[0], errs[1]
        )

        # Update Pitching
        pres = d.get('pitcher_result', {})
        self.pitching_card.set_pitchers(pres.get('win'), pres.get('loss'), pres.get('save'))

        # Update Highlights
        self.highlights_card.set_homeruns(d.get('home_runs', []))
        
        # Update Box Score
        if 'game_stats' in d:
            self.box_score_card.set_data(h_team, a_team, d['game_stats'])
        else:
            self.box_score_card.setVisible(False)
