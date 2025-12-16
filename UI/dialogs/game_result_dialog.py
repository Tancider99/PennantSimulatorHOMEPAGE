# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QGridLayout, QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt
from UI.theme import get_theme
from UI.widgets.score_board import LineScoreTable

class GameResultDialog(QDialog):
    """
    NPB公式風の試合結果画面
    """
    def __init__(self, result_data, parent=None):
        super().__init__(parent)
        self.data = result_data
        self.theme = get_theme()
        self.setWindowTitle("試合結果")
        self.setFixedWidth(850)
        self.setFixedHeight(600)
        self._setup_ui()
        self._populate_data()

    def _setup_ui(self):
        self.setStyleSheet(f"background-color: {self.theme.bg_dark}; color: {self.theme.text_primary};")
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header = QLabel("GAME RESULT")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {self.theme.primary}; letter-spacing: 2px;")
        layout.addWidget(header)

        # Score Area (Big Scores)
        score_container = QWidget()
        score_layout = QHBoxLayout(score_container)
        score_layout.setSpacing(40)
        score_layout.setAlignment(Qt.AlignCenter)
        
        # Home Team
        self.home_name = QLabel()
        self.home_name.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.home_score = QLabel()
        self.home_score.setStyleSheet(f"font-size: 64px; font-weight: 900; color: {self.theme.text_primary};")
        
        # Away Team
        self.away_name = QLabel()
        self.away_name.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.away_score = QLabel()
        self.away_score.setStyleSheet(f"font-size: 64px; font-weight: 900; color: {self.theme.text_primary};")
        
        # VS / Winner Logic handled in populate
        
        # Layout: Away - Score - VS - Score - Home (assuming NPB style: Away is First/Top?)
        # NPB typically shows Home on Right or Bottom. 
        # LineScore: Top=Away, Bottom=Home.
        
        v_away = QVBoxLayout()
        v_away.addWidget(self.away_name, 0, Qt.AlignCenter)
        v_away.addWidget(self.away_score, 0, Qt.AlignCenter)
        
        v_home = QVBoxLayout()
        v_home.addWidget(self.home_name, 0, Qt.AlignCenter)
        v_home.addWidget(self.home_score, 0, Qt.AlignCenter)
        
        score_layout.addLayout(v_away)
        score_layout.addWidget(QLabel("-", styleSheet="font-size: 48px; color: #666;"))
        score_layout.addLayout(v_home)
        
        layout.addWidget(score_container)

        # Line Score Table
        self.line_score_table = LineScoreTable()
        self.line_score_table.setFixedHeight(90) # slightly taller
        layout.addWidget(self.line_score_table)

        # Details Area (Grid)
        details = QFrame()
        details.setStyleSheet(f"background-color: {self.theme.bg_card}; border-radius: 8px; padding: 15px;")
        d_layout = QGridLayout(details)
        d_layout.setSpacing(15)
        
        # Labels
        lbl_style = f"color: {self.theme.text_secondary}; font-weight: bold;"
        d_layout.addWidget(QLabel("勝利投手", styleSheet=lbl_style), 0, 0)
        d_layout.addWidget(QLabel("敗戦投手", styleSheet=lbl_style), 1, 0)
        d_layout.addWidget(QLabel("セーブ", styleSheet=lbl_style), 2, 0)
        d_layout.addWidget(QLabel("本塁打", styleSheet=lbl_style), 3, 0)
        
        # Values
        self.lbl_win = QLabel()
        self.lbl_loss = QLabel()
        self.lbl_save = QLabel()
        self.lbl_hr = QLabel()
        self.lbl_hr.setWordWrap(True)
        
        d_layout.addWidget(self.lbl_win, 0, 1)
        d_layout.addWidget(self.lbl_loss, 1, 1)
        d_layout.addWidget(self.lbl_save, 2, 1)
        d_layout.addWidget(self.lbl_hr, 3, 1)
        
        layout.addWidget(details)
        
        layout.addStretch()
        
        # Footer Button
        btn_close = QPushButton("閉じる")
        btn_close.setFixedSize(200, 50)
        btn_close.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.primary};
                color: {self.theme.bg_dark};
                border-radius: 25px;
                font-size: 16px; font-weight: bold;
            }}
            QPushButton:hover {{ background-color: {self.theme.primary_hover}; }}
        """)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, 0, Qt.AlignCenter)

    def _populate_data(self):
        d = self.data
        h_team = d['home_team']
        a_team = d['away_team']
        
        self.home_name.setText(h_team.name)
        self.away_name.setText(a_team.name)
        self.home_score.setText(str(d['home_score']))
        self.away_score.setText(str(d['away_score']))
        
        # Colorize winner
        res = d['win_pitcher_name'] if 'win_pitcher_name' in d else "" # unused
        
        if d['home_score'] > d['away_score']:
             self.home_score.setStyleSheet(f"font-size: 64px; font-weight: 900; color: {self.theme.accent_orange};")
        elif d['away_score'] > d['home_score']:
             self.away_score.setStyleSheet(f"font-size: 64px; font-weight: 900; color: {self.theme.accent_orange};")
        
        # Line Score
        self.line_score_table.update_names(h_team.name, a_team.name)
        
        # Update columns based on inning count
        hist = d.get('score_history', {'top': [], 'bot': []})
        top_scores = hist.get('top', [])
        bot_scores = hist.get('bot', [])
        
        max_inn = max(len(top_scores), len(bot_scores))
        
        # Set scores
        current_cols = self.line_score_table.columnCount()
        for i in range(max_inn):
            # Inning i (0-based) -> Column i+1
            s_top = top_scores[i] if i < len(top_scores) else ""
            s_bot = bot_scores[i] if i < len(bot_scores) else ""
            
            # Need to handle table size dynamically
            # LineScoreTable.set_inning_score handles expansion
            self.line_score_table.set_inning_score(i+1, True, s_top)
            self.line_score_table.set_inning_score(i+1, False, s_bot)
            
        # Update Totals
        hits = d.get('hits', (0,0))
        errs = d.get('errors', (0,0))
        self.line_score_table.update_score_data(
            d['home_score'], d['away_score'],
            hits[0], hits[1],
            errs[0], errs[1]
        )
        
        # Pitchers
        pres = d.get('pitcher_result', {})
        win = pres.get('win')
        lose = pres.get('loss')
        save = pres.get('save')
        
        def fmt_p(p):
            if not p: return "なし"
            stats = d.get('pitcher_result', {}).get('game_stats', {}) # Wait, game_stats is nested?
            # actually we don't have game_stats inside pitcher_result unless we passed it.
            # We passed the dict from finalize_game_stats.
            # Let's assume p is Player object which has name.
            return f"{p.name}"

        self.lbl_win.setText(fmt_p(win))
        self.lbl_loss.setText(fmt_p(lose))
        self.lbl_save.setText(fmt_p(save))
        
        # HRs
        hrs = d.get('home_runs', [])
        if hrs:
            # list of (name, count, team)
            # Format: Name (Team), Name 2(Team) ...
            txt = ", ".join([f"{name} ({count}号)" for name, count, team in hrs])
            self.lbl_hr.setText(txt)
        else:
            self.lbl_hr.setText("なし")
