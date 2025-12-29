# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Pre-Game Briefing
Industrial Sci-Fi Dashboard for Game Preparation
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QPushButton, QScrollArea, QGridLayout, QSizePolicy, QHeaderView,
    QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont

from UI.theme import get_theme
from UI.widgets.cards import Card, StatCard, TeamCard
from UI.widgets.tables import DraggableTableWidget, RatingDelegate, SortableTableWidgetItem
from models import Team, Player, Position

class ClickableLabel(QLabel):
    clicked = Signal()
    def mousePressEvent(self, event):
        self.clicked.emit()

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
    # Removed starter_clicked signal as starter is moved own widget
    
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
            border: none;
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
        
        # Removed Starter info from here
        
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
            
            # Starter info removed from here

        update_strip(self.home_stats, home)
        update_strip(self.away_stats, away)

class PreGamePage(QWidget):
    """
    Pre-Game Confirmation Page
    Industrial Sci-Fi Design
    """
    start_game_requested = Signal(dict) # params: mode='manual'|'fast'
    edit_order_requested = Signal(object) # Pass the team object
    player_detail_requested = Signal(object)  # Emit player for detail view

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.home_team = None
        self.away_team = None
        self.game_state = None  # Will be set via set_game_state
        
        self.setup_ui()
    
    def set_game_state(self, game_state):
        """Set game state to determine player team"""
        self.game_state = game_state

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(20)
        
        # 1. Matchup Header
        self.header = MatchupHeader()
        layout.addWidget(self.header)
        
        # 2. Comparison Row
        self.comparison = TeamComparisonRow()
        # Removed starter_clicked connection
        layout.addWidget(self.comparison)
        
        # 3. Lineup (Home Team Only)
        lineup_container = QVBoxLayout()
        lineup_container.setSpacing(8)
        
        header_l = QLabel("STARTING LINEUP")
        header_l.setStyleSheet(f"font-size: 14px; font-weight: 700; color: {self.theme.text_muted}; letter-spacing: 1px;")
        lineup_container.addWidget(header_l)
        
        self.lineup_table = DraggableTableWidget("lineup")
        self.lineup_table.setDragEnabled(False) # Read-only view here
        self.lineup_table.setAcceptDrops(False)
        
        # Setup columns - Expanded Stats
        # OBP, SLG, OPS, SB added. Overall changed to numeric.
        # 順, 守, 調, 選手名, ミ, パ, 走, 肩, 守, 率, 本, 点, 盗, 出, 長, O, 総合(★)
        cols = ["順", "守", "調", "選手名", "ミ", "パ", "走", "肩", "守", "率", "本", "点", "盗", "出", "長", "OPS", "総合"]
        widths = [30, 40, 30, 100, 35, 35, 35, 35, 35, 50, 35, 35, 35, 50, 50, 50, 50]
        
        self.lineup_table.setColumnCount(len(cols))
        self.lineup_table.setHorizontalHeaderLabels(cols)
        for i, w in enumerate(widths):
            self.lineup_table.setColumnWidth(i, w)
        
        # Set Delegates
        self.rating_delegate = RatingDelegate(self)
        from UI.widgets.tables import DefenseDelegate
        self.defense_delegate = DefenseDelegate(self.theme)
        
        # Name column is 3
        # Stats Rating columns: 4-8. Overall (16) NO DELEGATE (Numeric)
        
        self.lineup_table.setItemDelegateForColumn(1, self.defense_delegate)
        for c in [4, 5, 6, 7, 8]:
             self.lineup_table.setItemDelegateForColumn(c, self.rating_delegate)
        # Removed delegate for Overall column to show text
        
        # Style
        self.lineup_table.setStyleSheet(self._get_table_style())
        
        # Double-click to view player details
        self.lineup_table.cellDoubleClicked.connect(self._on_lineup_double_click)
        
        # Enforce minimum height to show all 9 rows + header
        self.lineup_table.setMinimumHeight(400)
        
        lineup_container.addWidget(self.lineup_table)
        
        # Add Starting Pitcher Table below Lineup (Label removed)
        self.starter_table = DraggableTableWidget("starter")
        self.starter_table.setDragEnabled(False)
        self.starter_table.setAcceptDrops(False)
        self.starter_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.starter_table.cellDoubleClicked.connect(self._on_starter_double_click)
        
        # Columns for Starter (Table format)
        # 役割, 投, 調, 選手名, 球, コ, ス, 球種, 防, 勝, 負, 回, 三, 総合
        s_cols = ["役割", "投", "調", "選手名", "球", "コ", "ス", "球種", "防", "勝", "負", "回", "三", "総合"]
        s_widths = [50, 30, 30, 110, 35, 30, 30, 40, 45, 30, 30, 40, 35, 45]
        
        self.starter_table.setColumnCount(len(s_cols))
        self.starter_table.setHorizontalHeaderLabels(s_cols)
        for i, w in enumerate(s_widths):
            self.starter_table.setColumnWidth(i, w)
            
        # Set height for 1 row + header
        self.starter_table.setFixedHeight(80)
        
        # Apply Rating Delegate for Control (5) and Stamina (6)
        self.starter_table.setItemDelegateForColumn(5, RatingDelegate(self))
        self.starter_table.setItemDelegateForColumn(6, RatingDelegate(self)) 
        
        # Style
        self.starter_table.setStyleSheet(self._get_table_style())
        
        lineup_container.addWidget(self.starter_table)
        
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
                outline: none;
            }}
            QTableWidget::item:selected {{
                background-color: #FFFFFF;
                color: #000000;
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
        
        # Always show player team's order (could be home or away)
        # Determine which team is the player's team
        player_team = home_team  # Default to home
        if hasattr(self, 'game_state') and self.game_state and self.game_state.player_team:
            if self.game_state.player_team == away_team:
                player_team = away_team
            else:
                player_team = home_team
        
        self._refresh_lineup_table(player_team)

    def _refresh_lineup_table(self, team: Team):
        from PySide6.QtWidgets import QTableWidgetItem
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor, QFont
        from UI.widgets.tables import SortableTableWidgetItem, ROLE_PLAYER_IDX
        
        self.lineup_table.setRowCount(0)
        self.starter_table.setRowCount(0)
        
        if not team: return
            
        # Update Starter Table
        starter = team.get_today_starter()
        if starter:
            self.starter_table.insertRow(0)
            
            # 0. 役割 (Role)
            role_item = QTableWidgetItem("推奨" if team == self.home_team else "予想") # "先発" or "Starter"
            role_item.setText("先発")
            role_item.setTextAlignment(Qt.AlignCenter)
            self.starter_table.setItem(0, 0, role_item)
            
            # 1. 投 (Hand)
            hand_item = QTableWidgetItem(starter.throws)
            hand_item.setTextAlignment(Qt.AlignCenter)
            self.starter_table.setItem(0, 1, hand_item)
            
            # 2. 調 (Condition)
            cond_item = QTableWidgetItem(str(starter.condition))
            cond_item.setTextAlignment(Qt.AlignCenter)
            self.starter_table.setItem(0, 2, cond_item)
            
            # 3. Name
            name_item = QTableWidgetItem(starter.name)
            name_item.setData(Qt.UserRole, starter)
            self.starter_table.setItem(0, 3, name_item)
            
            # Stats
            rec = starter.record
            era = f"{rec.era:.2f}"
            wins = str(rec.wins)
            losses = str(rec.losses)
            ip = f"{rec.innings_pitched:.1f}"
            so = str(rec.strikeouts)
            
            # Ability Stats
            stats = starter.stats
            vel = f"{stats.velocity}"
            
            # Delegate uses UserRole for ranking
            con_val = stats.control
            stm_val = stats.stamina
            pt = str(len(stats.pitches))
            
            # 4. Vel
            self._set_item_starter(0, 4, vel)
            
            # 5. Con (Delegate)
            self._set_item_starter(0, 5, "")
            self.starter_table.item(0, 5).setData(Qt.UserRole, con_val)
            
            # 6. Stm (Delegate)
            self._set_item_starter(0, 6, "")
            self.starter_table.item(0, 6).setData(Qt.UserRole, stm_val)
            
            # 7. PitchTypes
            self._set_item_starter(0, 7, pt)
            
            # 8. ERA
            self._set_item_starter(0, 8, era)
            # 9. Wins
            self._set_item_starter(0, 9, wins)
            # 10. Losses
            self._set_item_starter(0, 10, losses)
            # 11. IP
            self._set_item_starter(0, 11, ip)
            # 12. SO
            self._set_item_starter(0, 12, so)
            
            # 13. Overall
            oa = starter.stats.overall_pitching()
            oa_item = QTableWidgetItem(f"★{oa}")
            oa_item.setTextAlignment(Qt.AlignCenter)
            oa_item.setForeground(QColor(self.theme.accent_gold))
            oa_item.setFont(QFont("Arial", 10, QFont.Bold))
            self.starter_table.setItem(0, 13, oa_item)

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
             
             # 3. Condition
             cond_item = QTableWidgetItem("---") # Default if no player
             cond_item.setTextAlignment(Qt.AlignCenter)
             self.lineup_table.setItem(i, 2, cond_item)
             
             # 4. Name
             name_item = QTableWidgetItem("---") # Default if no player
             self.lineup_table.setItem(i, 3, name_item)
             
             if pid == -1:
                 # If no player, set default values for remaining columns
                 for col_idx in range(4, self.lineup_table.columnCount()):
                     item = QTableWidgetItem("---")
                     item.setTextAlignment(Qt.AlignCenter)
                     self.lineup_table.setItem(i, col_idx, item)
                 continue
                 
             player = team.players[pid]
             player_idx = pid # Store the actual index in the team's player list
             
             # Update Condition
             cond_item.setText(str(player.condition))
             
             # Update Name
             name_item.setText(player.name)
             name_item.setData(Qt.UserRole, player)  # Store player object for drag/drop and double-click
             name_item.setData(ROLE_PLAYER_IDX, player_idx) # Optional, kept for compatibility
             
             # 4-8. Stats: ミ,パ,走,肩,守 (Indices 4,5,6,7,8)
             stat_indices = [4, 5, 6, 7, 8]
            
             def_val = player.stats.get_defense_range(player.position)
            
             vals = [player.stats.contact, player.stats.power, player.stats.speed, player.stats.arm, def_val]
            
             for col_idx, val in zip(stat_indices, vals):
                 it = SortableTableWidgetItem(str(val))
                 it.setData(Qt.UserRole, val)
                 it.setTextAlignment(Qt.AlignCenter)
                 self.lineup_table.setItem(i, col_idx, it)

             # Stats Calculation
             rec = player.record
             ab = rec.at_bats
             hits = rec.hits
             doubles = rec.doubles
             triples = rec.triples
             hr = rec.home_runs
             bb = rec.walks
             hbp = rec.hit_by_pitch
             sf = rec.sacrifice_flies
             sb = rec.stolen_bases
             
             # 9. 打率 (AVG)
             if ab > 0:
                 avg = f".{int(rec.batting_average * 1000):03d}"
             else:
                 avg = "---"
             self._set_item(i, 9, avg)
            
             # 10. 本塁打 (HR)
             self._set_item(i, 10, str(hr))
            
             # 11. 打点 (RBI)
             self._set_item(i, 11, str(rec.rbis))
             
             # 12. 盗塁 (SB)
             self._set_item(i, 12, str(sb))
             
             # 13. 出塁率 (OBP) = (H + BB + HBP) / (AB + BB + HBP + SF)
             numerator = hits + bb + hbp
             denominator = ab + bb + hbp + sf
             obp_val = numerator / denominator if denominator > 0 else 0.0
             self._set_item(i, 13, f".{int(obp_val * 1000):03d}")
             
             # 14. 長打率 (SLG) = (1B + 2*2B + 3*3B + 4*HR) / AB
             singles = hits - doubles - triples - hr
             total_bases = singles + 2*doubles + 3*triples + 4*hr
             slg_val = total_bases / ab if ab > 0 else 0.0
             self._set_item(i, 14, f".{int(slg_val * 1000):03d}")
             
             # 15. OPS
             ops_val = obp_val + slg_val
             self._set_item(i, 15, f".{int(ops_val * 1000):03d}")
             
             # 16. Overall (★数値)
             oa = player.stats.overall_batting(player.position)
             oa_item = QTableWidgetItem(f"★{oa}")
             oa_item.setTextAlignment(Qt.AlignCenter)
             oa_item.setForeground(QColor(self.theme.accent_gold)) # Gold color for stars
             oa_item.setFont(QFont("Arial", 10, QFont.Bold))
             # Remove delegate logic -> simple text
             self.lineup_table.setItem(i, 16, oa_item)

    def _set_item(self, row, col, text):
        from PySide6.QtWidgets import QTableWidgetItem
        from PySide6.QtCore import Qt
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        self.lineup_table.setItem(row, col, item)

    def _set_item_starter(self, row, col, text):
        from PySide6.QtWidgets import QTableWidgetItem
        from PySide6.QtCore import Qt
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        self.starter_table.setItem(row, col, item)

    def _on_starter_double_click(self, row, col):
        """Handle double-click on starter table"""
        item = self.starter_table.item(row, 3) # Name col
        if item:
            player = item.data(Qt.UserRole)
            if player:
                self.player_detail_requested.emit(player)

    def _on_lineup_double_click(self, row, col):
        """Handle double-click on lineup table to show player details"""
        item = self.lineup_table.item(row, 3)  # Name column
        if not item:
            return
        
        # Get player from stored data
        from PySide6.QtCore import Qt
        player = item.data(Qt.UserRole)
        
        # If no player stored in item, try to find from home team
        if not player and self.home_team:
            try:
                if row < len(self.home_team.current_lineup):
                    p_idx = self.home_team.current_lineup[row]
                    if 0 <= p_idx < len(self.home_team.players):
                        player = self.home_team.players[p_idx]
            except:
                pass
        
        if player:
            self.player_detail_requested.emit(player)
