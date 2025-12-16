# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Pre-Game Briefing
Industrial Sci-Fi Dashboard for Game Preparation
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QPushButton, QScrollArea, QGridLayout, QSizePolicy, QHeaderView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from UI.theme import get_theme
from UI.widgets.cards import Card, StatCard, TeamCard
from UI.widgets.tables import DraggableTableWidget, RatingDelegate
from models import Team, Player, Position

class MatchupHeader(QFrame):
    """Next Game Matchup Header"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {self.theme.bg_card};
                border: none;
                border-radius: 0px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        
        # Away Team
        self.away_label = QLabel("AWAY TEAM")
        self.away_label.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {self.theme.text_secondary};")
        layout.addWidget(self.away_label)
        
        layout.addStretch()
        
        # VS Center
        center_layout = QVBoxLayout()
        vs_label = QLabel("VS")
        vs_label.setAlignment(Qt.AlignCenter)
        vs_label.setStyleSheet(f"font-size: 32px; font-weight: 900; color: {self.theme.accent_gold}; font-family: 'Consolas';")
        center_layout.addWidget(vs_label)
        
        self.stadium_label = QLabel("Stadium Name")
        self.stadium_label.setAlignment(Qt.AlignCenter)
        self.stadium_label.setStyleSheet(f"font-size: 12px; color: {self.theme.text_muted};")
        center_layout.addWidget(self.stadium_label)
        layout.addLayout(center_layout)
        
        layout.addStretch()
        
        # Home Team
        self.home_label = QLabel("HOME TEAM")
        self.home_label.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {self.theme.text_primary};")
        layout.addWidget(self.home_label)

    def set_teams(self, home: Team, away: Team):
        self.home_label.setText(home.name.upper())
        self.away_label.setText(away.name.upper())
        if home.stadium:
            self.stadium_label.setText(home.stadium.name)

class TeamComparisonRow(QWidget):
    """Team Stats Comparison"""
    # ... (Same as before, abbreviated for brevity in prompt, but full code will be written)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        
        # Away Stats
        self.away_stats = self._create_stats_strip(is_home=False)
        layout.addWidget(self.away_stats)
        
        # Home Stats
        self.home_stats = self._create_stats_strip(is_home=True)
        layout.addWidget(self.home_stats)

    def _create_stats_strip(self, is_home):
        frame = QFrame()
        frame.setStyleSheet(f"""
            background-color: {self.theme.bg_card};
            border-left: 4px solid {self.theme.accent_gold if is_home else self.theme.accent_blue};
        """)
        l = QHBoxLayout(frame)
        l.setContentsMargins(16, 12, 16, 12)
        
        self.stat_labels = {}
        target_labels = self.stat_labels
        
        stats = ["W-L-D", "AVG", "HR", "ERA"]
        
        for stat in stats:
            container = QVBoxLayout()
            lbl = QLabel(stat)
            lbl.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted};")
            val = QLabel("---")
            val.setStyleSheet(f"font-size: 16px; font-weight: 700; color: {self.theme.text_primary}; font-family: 'Consolas';")
            
            container.addWidget(lbl)
            container.addWidget(val)
            l.addLayout(container)
            l.addSpacing(20)
            target_labels[stat] = val
            
        l.addStretch()
        
        starter_layout = QVBoxLayout()
        s_lbl = QLabel("STARTER")
        s_lbl.setStyleSheet(f"font-size: 10px; color: {self.theme.text_muted};")
        s_val = QLabel("---")
        s_val.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {self.theme.text_highlight};")
        starter_layout.addWidget(s_lbl)
        starter_layout.addWidget(s_val)
        l.addLayout(starter_layout)
        
        target_labels["STARTER"] = s_val
        frame.labels = target_labels
        return frame

    def set_stats(self, home: Team, away: Team):
        def update_strip(frame, team):
            lbs = frame.labels
            lbs["W-L-D"].setText(f"{team.wins}-{team.losses}-{team.draws}")
            
            total_hits = sum(p.record.hits for p in team.players)
            total_ab = sum(p.record.at_bats for p in team.players)
            avg = total_hits / total_ab if total_ab > 0 else 0.000
            lbs["AVG"].setText(f".{int(avg*1000):03d}")
            
            total_hr = sum(p.record.home_runs for p in team.players)
            lbs["HR"].setText(str(total_hr))
            
            total_er = sum(p.record.earned_runs for p in team.players)
            total_ip = sum(p.record.innings_pitched for p in team.players)
            era = (total_er * 9) / total_ip if total_ip > 0 else 0.00
            lbs["ERA"].setText(f"{era:.2f}")
            
            starter = team.get_today_starter()
            if starter:
                lbs["STARTER"].setText(f"{starter.name} (ERA: {starter.record.era:.2f})")
            else:
                lbs["STARTER"].setText("TBD")

        update_strip(self.home_stats, home)
        update_strip(self.away_stats, away)

class PreGamePage(QWidget):
    """
    Pre-Game Confirmation Page
    Industrial Sci-Fi Design
    """
    start_game_requested = Signal(dict) # params: mode='manual'|'fast'
    edit_order_requested = Signal(object) # Pass the team object

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.home_team = None
        self.away_team = None
        
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # 1. Matchup Header
        self.header = MatchupHeader()
        layout.addWidget(self.header)
        
        # 2. Comparison Row
        self.comparison = TeamComparisonRow()
        layout.addWidget(self.comparison)
        
        # 3. Lineup (Home Team Only)
        lineup_container = QVBoxLayout()
        lineup_container.setSpacing(8)
        
        header_l = QLabel("STARTING LINEUP")
        header_l.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {self.theme.text_muted}; letter-spacing: 1px;")
        lineup_container.addWidget(header_l)
        
        # Recycle DraggableTableWidget logic but simplified for display or reuse it directly
        # Since we want to display it exactly like OrderPage, we'll reuse DraggableTableWidget for consistent styling
        # But we need to disable drag/drop if it's read-only here, or allow it?
        # User asked to "style own lineup like Order Tab".
        # Let's use DraggableTableWidget in 'lineup' mode.
        
        self.lineup_table = DraggableTableWidget("lineup")
        self.lineup_table.setDragEnabled(False) # Read-only view here
        self.lineup_table.setAcceptDrops(False)
        
        # Setup columns same as OrderPage
        cols = ["順", "守", "調", "選手名", "ミ", "パ", "走", "肩", "守", "適正", "総合"]
        widths = [30, 40, 30, 130, 35, 35, 35, 35, 35, 80, 45]
        
        self.lineup_table.setColumnCount(len(cols))
        self.lineup_table.setHorizontalHeaderLabels(cols)
        for i, w in enumerate(widths):
            self.lineup_table.setColumnWidth(i, w)
            
        # Set Delegates
        self.rating_delegate = RatingDelegate(self)
        from UI.pages.order_page import DefenseDelegate # Import locally to avoid circular if any
        self.defense_delegate = DefenseDelegate(self.theme)
        
        for c in [4, 5, 6, 7, 8]:
             self.lineup_table.setItemDelegateForColumn(c, self.rating_delegate)
        self.lineup_table.setItemDelegateForColumn(9, self.defense_delegate)
        
        # Style
        self.lineup_table.setStyleSheet(self._get_table_style())
        
        lineup_container.addWidget(self.lineup_table)
        layout.addLayout(lineup_container, stretch=1)
        
        # 4. Action Footer
        footer = QFrame()
        footer.setStyleSheet(f"background-color: {self.theme.bg_card};")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(20, 16, 20, 16)
        
        edit_btn = QPushButton("EDIT ORDER")
        edit_btn.setStyleSheet(self._get_btn_style("secondary"))
        edit_btn.clicked.connect(lambda: self.edit_order_requested.emit(self.home_team))
        fl.addWidget(edit_btn)
        
        fl.addStretch()
        
        # Skip Game (Fast Forward)
        skip_btn = QPushButton("FAST FORWARD")
        skip_btn.setStyleSheet(self._get_btn_style("secondary"))
        skip_btn.clicked.connect(lambda: self.start_game_requested.emit({'mode': 'fast'}))
        fl.addWidget(skip_btn)
        
        fl.addSpacing(16)
        
        # Play Ball
        play_btn = QPushButton("PLAY BALL")
        play_btn.setMinimumWidth(200)
        play_btn.setStyleSheet(self._get_btn_style("primary"))
        play_btn.clicked.connect(lambda: self.start_game_requested.emit({'mode': 'manual'}))
        fl.addWidget(play_btn)
        
        layout.addWidget(footer)

    def _get_table_style(self):
        return f"""
            QTableWidget {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                gridline-color: {self.theme.border_muted};
                selection-background-color: {self.theme.bg_input};
                outline: none;
            }}
            QHeaderView::section {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_secondary};
                border: none;
                border-bottom: 1px solid {self.theme.border};
                padding: 4px;
                font-size: 12px;
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: 2px;
                border-bottom: 1px solid {self.theme.border_muted};
            }}
        """

    def _get_btn_style(self, variant="primary"):
        base_color = self.theme.accent_gold if variant == "primary" else self.theme.bg_input
        text_color = self.theme.bg_dark if variant == "primary" else self.theme.text_primary
        hover_color = self.theme.gradient_end if variant == "primary" else self.theme.bg_card_elevated
        
        return f"""
            QPushButton {{
                background-color: {base_color};
                color: {text_color};
                border: none;
                padding: 12px 24px;
                font-weight: 700;
                font-size: 13px;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
        """

    def set_teams(self, home_team: Team, away_team: Team):
        self.home_team = home_team
        self.away_team = away_team
        
        self.header.set_teams(home_team, away_team)
        self.comparison.set_stats(home_team, away_team)
        
        self._refresh_lineup_table(home_team)

    def _refresh_lineup_table(self, team: Team):
        from PySide6.QtWidgets import QTableWidgetItem
        from UI.widgets.tables import SortableTableWidgetItem
        
        self.lineup_table.setRowCount(0)
        
        lineup_ids = team.current_lineup
        positions = team.lineup_positions
        
        # Only show 9 rows
        for i in range(9):
             pid = lineup_ids[i] if i < len(lineup_ids) else -1
             pos_name = positions[i] if i < len(positions) else "DH"
             
             self.lineup_table.insertRow(i)
             
             # 1. Order
             ord_item = QTableWidgetItem(str(i+1))
             ord_item.setTextAlignment(Qt.AlignCenter)
             ord_item.setForeground(QColor(self.theme.accent_gold))
             self.lineup_table.setItem(i, 0, ord_item)
             
             # 2. Position
             pos_item = QTableWidgetItem(pos_name)
             pos_item.setTextAlignment(Qt.AlignCenter)
             self.lineup_table.setItem(i, 1, pos_item)
             
             if pid == -1:
                 self.lineup_table.setItem(i, 3, QTableWidgetItem("---"))
                 continue
                 
             player = team.players[pid]
             
             # 3. Condition
             cond_item = QTableWidgetItem(str(player.condition)) # Keep simple for now
             self.lineup_table.setItem(i, 2, cond_item)
             
             # 4. Name
             name_item = QTableWidgetItem(player.name)
             self.lineup_table.setItem(i, 3, name_item)
             
             # 5-9. Stats (Contact, Power, Speed, Arm, Defense)
             # Use SortableTableWidgetItem with UserRole for sorting/coloring
             stats = [
                 player.stats.contact,
                 player.stats.power,
                 player.stats.speed,
                 player.stats.arm,
                 player.stats.get_defense_range(player.position) # Show defense for main position?? Or generic? OrderPage uses defense_range(pos) logic?
                 # OrderPage.py lines 509 assign rating_delegate to cols 4,5,6,7,8 corresponding to these.
             ]
             # Note: OrderPage uses specific indices. Here cols are:
             # 0:Ord, 1:Pos, 2:Cond, 3:Name, 4:Con, 5:Pow, 6:Spd, 7:Arm, 8:Def, 9:Aptitude, 10:Overall
             
             # Re-checking OrderPage logic for stats:
             # OrderPage uses: Contact, Power, Speed, Arm, Defense
             # Defense logic in OrderPage usually takes the stat based on position.
             # Let's just use raw stats for now.
             
             stat_indices = [4, 5, 6, 7, 8]
             # 守備力はポジションに依存するが、ここでは簡易的にメインポジションの守備力を表示するか、
             # player.stats.error / defense_range mix?
             # OrderPage view uses:
             # 守備力 = Stats.defense_ranges[pos] ???
             # Let's just use Main Position defense for simplicity or generic
             
             # 修正: OrderPageの実装を見ると、 stats.contact 等をそのまま表示している。
             # 守備列(8)については、OrderPageでは `player.stats.get_defense_range(position)` ではなく、特化した値を使っているか確認が必要。
             # ひとまず一般的な守備力 (fielding skill) がないので、メインポジションの守備力を使う。
             
             # For simpler implementation, copy stats directly
             def_val = player.stats.get_defense_range(player.position)
             
             vals = [player.stats.contact, player.stats.power, player.stats.speed, player.stats.arm, def_val]
             
             for col_idx, val in zip(stat_indices, vals):
                 it = SortableTableWidgetItem(str(val))
                 it.setData(Qt.UserRole, val)
                 it.setTextAlignment(Qt.AlignCenter)
                 self.lineup_table.setItem(i, col_idx, it)

             # 9. Main/Sub Position (Defense Delegate)
             # Format: "Main|Sub"
             main_pos_str = player.position.value
             # Sub positions
             subs = []
             for k, v in player.stats.defense_ranges.items():
                 if v >= 20 and k != player.position.value and k != "投":
                     subs.append(k)
             sub_str = " ".join(subs)
             full_pos_str = f"{main_pos_str}|{sub_str}"
             
             pos_viz_item = QTableWidgetItem(full_pos_str)
             self.lineup_table.setItem(i, 9, pos_viz_item)
             
             # 10. Overall
             oa = player.stats.overall_batting(player.position) # Simplified
             oa_item = QTableWidgetItem(str(oa))
             oa_item.setTextAlignment(Qt.AlignCenter)
             self.lineup_table.setItem(i, 10, oa_item)

