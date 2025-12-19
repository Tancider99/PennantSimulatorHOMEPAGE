# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
    QTableWidget, QTableWidgetItem, QHeaderView, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from UI.widgets.panels import Card
from UI.theme import get_theme
from models import League, Position, TeamLevel

class CompactTable(QTableWidget):
    """Data-dense table for dashboard"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet("background: transparent; border: none;")
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setFocusPolicy(Qt.NoFocus)
        self.setSelectionMode(QTableWidget.NoSelection)

class LeadersWidget(Card):
    def __init__(self, title, league, stat_key, is_pitcher=False, parent=None):
        super().__init__(title, parent, bordered=False)
        self.league = league
        self.stat_key = stat_key
        self.is_pitcher = is_pitcher
        self.table = CompactTable()
        self.layout.addWidget(self.table)
        
    def set_game_state(self, game_state):
        leaders = game_state.get_league_leaders(self.league, self.stat_key, 5, self.is_pitcher)
        self.table.setRowCount(len(leaders))
        self.table.setColumnCount(3)
        theme = get_theme()
        
        font_small = QFont("Yu Gothic UI", 9)
        font_mono = QFont("Consolas", 10, QFont.Bold)

        for i, p in enumerate(leaders):
            # Rank/Pos? Just Name & Stat
            # Col 1: Name
            name_item = QTableWidgetItem(f"{i+1}. {p.name[0]}. {p.name.split()[-1] if ' ' in p.name else p.name}")
            name_item.setForeground(QColor(theme.text_primary))
            name_item.setFont(font_small)
            self.table.setItem(i, 0, name_item)
            
            # Col 2: Team - Optional, skipping for density
            
            # Col 3: Stat Value
            val = getattr(p.record, self.stat_key, 0)
            if self.stat_key in ["batting_average", "obp", "slg", "ops", "winning_percentage"]:
                val_str = f"{val:.3f}"[1:] if val < 1 else f"{val:.3f}"
            elif self.stat_key in ["era", "whip", "fip"]:
                val_str = f"{val:.2f}"
            else:
                val_str = str(val)
                
            val_item = QTableWidgetItem(val_str)
            val_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            val_item.setForeground(QColor(theme.primary))
            val_item.setFont(font_mono)
            self.table.setItem(i, 2, val_item)
            
        self.table.resizeRowsToContents()

class TeamRankingsWidget(Card):
    def __init__(self, parent=None):
        super().__init__("TEAM RANKS", parent, bordered=False)
        self.layout.setSpacing(4)
        
    def set_game_state(self, game_state):
        # Clear existing
        while self.layout.count() > 1: # Keep title
            item = self.layout.takeAt(1)
            if item.widget(): item.widget().deleteLater()
            
        team = game_state.player_team
        if not team: return
        
        ranks = game_state.get_team_rankings(team)
        theme = get_theme()
        
        for cat, rank in ranks.items():
            row = QHBoxLayout()
            lbl = QLabel(cat.upper())
            lbl.setStyleSheet(f"color: {theme.text_muted}; font-size: 10px;")
            val = QLabel(f"{rank}th" if isinstance(rank, int) else str(rank))
            val.setStyleSheet(f"color: {theme.text_primary}; font-weight: bold; font-size: 11px;")
            
            row.addWidget(lbl)
            row.addStretch()
            row.addWidget(val)
            self.layout.addLayout(row)

class RosterOverviewWidget(Card):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__("ROSTER SNAPSHOT", parent, bordered=False)
        self.table = CompactTable()
        self.layout.addWidget(self.table)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)
        
    def set_game_state(self, game_state):
        team = game_state.player_team
        if not team: return
        
        # Display Lineup (1-9)
        self.table.setRowCount(9)
        self.table.setColumnCount(3) # Pos, Name, Avg/HR/RBI (Combined?)
        theme = get_theme()
        
        font_small = QFont("Yu Gothic UI", 9)
        
        lineup = team.current_lineup
        for i, idx in enumerate(lineup):
            if 0 <= idx < len(team.players):
                p = team.players[idx]
                
                pos_item = QTableWidgetItem(f"{i+1}")
                pos_item.setForeground(QColor(theme.text_muted))
                self.table.setItem(i, 0, pos_item)
                
                name_item = QTableWidgetItem(p.name)
                name_item.setForeground(QColor(theme.text_primary))
                name_item.setFont(font_small)
                self.table.setItem(i, 1, name_item)
                
                stats = f"{p.record.batting_average:.3f} {p.record.home_runs}HR"
                stat_item = QTableWidgetItem(stats)
                stat_item.setForeground(QColor(theme.text_secondary))
                stat_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                stat_item.setFont(font_small)
                self.table.setItem(i, 2, stat_item)
                
        self.table.resizeRowsToContents()

class FarmSystemWidget(Card):
    def __init__(self, parent=None):
        super().__init__("ファーム", parent, bordered=False)
        self.layout.setSpacing(8)
        
    def set_game_state(self, game_state):
        # Clear
        while self.layout.count() > 1:
            item = self.layout.takeAt(1)
            if item.widget(): item.widget().deleteLater()
            
        team = game_state.player_team
        if not team: return
        
        # Farm Team (AAA equivalent)
        self._add_team_row("二軍", team.record_farm)
        # Third Team (A equivalent)
        self._add_team_row("三軍", team.record_third)
        
    def _add_team_row(self, name, record):
        theme = get_theme()
        row = QVBoxLayout()
        row.setSpacing(2)
        
        name_lbl = QLabel(name) # Should be team name ideally
        name_lbl.setStyleSheet(f"color: {theme.primary}; font-weight: bold; font-size: 11px;")
        row.addWidget(name_lbl)
        
        rec_lbl = QLabel(f"Rec: {record.wins}-{record.losses}-{record.draws}")
        rec_lbl.setStyleSheet(f"color: {theme.text_secondary}; font-size: 10px;")
        row.addWidget(rec_lbl)
        
        self.layout.addLayout(row)

class ProspectsWidget(Card):
    player_selected = Signal(object) # Emits Player object

    def __init__(self, parent=None):
        super().__init__("TOP PROSPECTS", parent, bordered=False)
        self.table = CompactTable()
        self.layout.addWidget(self.table)
        self.table.cellDoubleClicked.connect(self._on_row_double_clicked)
        self._prospects = []
        
    def _on_row_double_clicked(self, row, col):
        if 0 <= row < len(self._prospects):
            self.player_selected.emit(self._prospects[row])
        
    def set_game_state(self, game_state):
        team = game_state.player_team
        if not team: return
        
        self._prospects = game_state.get_top_prospects(team, 5)
        self.table.setRowCount(len(self._prospects))
        self.table.setColumnCount(2)
        theme = get_theme()
        font_small = QFont("Yu Gothic UI", 9)
        
        for i, p in enumerate(self._prospects):
            pos_str = "P" if p.position == Position.PITCHER else p.position.value[0] # Short pos
            
            name_item = QTableWidgetItem(f"{pos_str} {p.name}")
            name_item.setForeground(QColor(theme.text_primary))
            name_item.setFont(font_small)
            # Make read-only / non-editable implicitly by table settings, but ensure interaction
            name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(i, 0, name_item)
            
            lvl = "二軍" if p.team_level == TeamLevel.SECOND else "三軍" # Simplified
            lvl_item = QTableWidgetItem(lvl)
            lvl_item.setForeground(QColor(theme.text_muted))
            lvl_item.setTextAlignment(Qt.AlignRight)
            lvl_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(i, 1, lvl_item)

class InjuriesWidget(Card):
    def __init__(self, parent=None):
        super().__init__("CURRENT INJURIES", parent, bordered=False)
        self.lbl = QLabel("No Injuries")
        self.lbl.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
        self.layout.addWidget(self.lbl)
        
    def set_game_state(self, game_state):
        # Placeholder for now
        pass
        
class ScheduleWidget(Card):
    def __init__(self, parent=None):
        super().__init__("SCHEDULE", parent, bordered=False)
        self.table = CompactTable()
        self.layout.addWidget(self.table)
        
    def set_game_state(self, game_state):
        if not game_state.schedule: 
            self._show_empty()
            return
            
        team_name = game_state.player_team.name
        # Get pending games
        from models import GameStatus
        games = game_state.schedule.get_team_games(team_name, status=GameStatus.SCHEDULED)
        
        # Sort just in case? Usually chronological.
        # Take next 5
        upcoming = games[:5]
        
        self.table.setRowCount(len(upcoming))
        self.table.setColumnCount(2)
        theme = get_theme()
        font_normal = QFont("Yu Gothic UI", 10)
        
        for i, g in enumerate(upcoming):
            # Date (YYYY-MM-DD -> MM/DD)
            try:
                dt_str = g.date[5:].replace("-", "/")
            except:
                dt_str = g.date
            
            date_item = QTableWidgetItem(dt_str)
            date_item.setForeground(QColor(theme.text_secondary))
            date_item.setFont(font_normal) # Increased from 9 to 10
            self.table.setItem(i, 0, date_item)
            
            # Opponent
            is_home = (g.home_team_name == team_name)
            opp_name = g.away_team_name if is_home else g.home_team_name
            prefix = "vs " if is_home else "@ "
            
            # Convert full name to abbr if possible? 
            # We don't have easy Abbr map here without searchingall teams.
            # Just use full name for now or slice it
            opp_display = f"{prefix}{opp_name}"
            
            opp_item = QTableWidgetItem(opp_display)
            opp_item.setForeground(QColor(theme.text_primary))
            opp_item.setFont(font_normal)
            self.table.setItem(i, 1, opp_item)
            
        self.table.resizeRowsToContents()

    def _show_empty(self):
        self.table.setRowCount(0)
