# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Stats Page
Premium Statistics Dashboard (Redesigned with Full Horizontal Scroll)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QComboBox, QPushButton, QScrollArea, QAbstractItemView, QButtonGroup,
    QScrollBar
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.panels import ToolbarPanel
from UI.widgets.tables import SortableTableWidgetItem
from models import TeamLevel, PlayerRecord
from stats_records import update_league_stats

class StatsTable(QTableWidget):
    """
    Custom Table for displaying statistics with sorting & horizontal scrolling
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                border: none;
                gridline-color: {self.theme.border_muted};
            }}
            QTableWidget::item {{
                padding: 4px;
                color: {self.theme.text_primary};
                border-bottom: 1px solid {self.theme.border_muted};
            }}
            QTableWidget::item:selected {{
                background-color: {self.theme.primary};
                color: white;
            }}
            QTableWidget::item:hover {{
                background-color: {self.theme.bg_hover};
            }}
            QHeaderView::section {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 {self.theme.bg_card_elevated},
                    stop:1 {self.theme.bg_card});
                color: {self.theme.text_secondary};
                font-weight: 600;
                font-size: 11px;
                padding: 8px 4px;
                border: none;
                border-bottom: 2px solid {self.theme.primary};
                border-right: 1px solid {self.theme.border_muted};
            }}
        """)

        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(32)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setShowGrid(True) # グリッド表示で見やすく
        self.setAlternatingRowColors(False)
        self.setWordWrap(False) # 横スクロールのために折り返し無効

        # Sort setup
        self.setSortingEnabled(False)
        self.horizontalHeader().setSectionsClickable(True)
        self.horizontalHeader().setSortIndicatorShown(True)
        self.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        
        # Horizontal Scroll Setup
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive) # ユーザーリサイズ可能に
        self.horizontalHeader().setStretchLastSection(False) # 最後の列を伸ばさない
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def _on_header_clicked(self, logicalIndex):
        header = self.horizontalHeader()
        current_column = header.sortIndicatorSection()
        current_order = header.sortIndicatorOrder()
        
        if current_column != logicalIndex:
            new_order = Qt.DescendingOrder
        else:
            new_order = Qt.AscendingOrder if current_order == Qt.DescendingOrder else Qt.DescendingOrder

        self.sortItems(logicalIndex, new_order)
        header.setSortIndicator(logicalIndex, new_order)

    def set_data(self, data_list: list, mode: str = "batter"):
        self.clear()
        
        if mode == "batter":
            # 超詳細指標 (30カラム以上)
            headers = [
                "名前", "チーム", "Pos", "試合", "打席", "打数", "打率", "安打", "二塁", "三塁", "本塁", 
                "打点", "得点", "三振", "四球", "死球", "犠打", "犠飛", "盗塁", "盗塁死", "併殺",
                "出塁率", "長打率", "OPS", "ISO", "IsoD", "BABIP", "BB/K", "PA/K",
                "wOBA", "wRC", "wRC+", "RC", "RC27", "XR", "XR27", "WAR", "UZR"
            ]
            # 幅設定 (固定幅)
            widths = [
                140, 60, 40, 45, 45, 45, 60, 45, 40, 40, 40, 
                45, 45, 45, 45, 40, 40, 40, 40, 40, 40, 
                60, 60, 60, 50, 50, 60, 50, 50,
                60, 50, 55, 50, 50, 50, 50, 55, 55
            ]
        else:
            # 投手詳細指標
            headers = [
                "名前", "チーム", "Pos", "登板", "先発", "完投", "完封", "無四球", "勝利", "敗戦", "S", "H", "勝率",
                "防御率", "投球回", "打者", "被安", "被本", "四球", "死球", "奪三振", "暴投", "ボーク", "失点", "自責",
                "K/9", "BB/9", "HR/9", "K/BB", "WHIP", "被打率", "LOB%", "FIP", "xFIP", "QS率", "WAR"
            ]
            widths = [
                140, 60, 40, 45, 45, 40, 40, 45, 40, 40, 35, 35, 50,
                60, 60, 45, 45, 40, 40, 40, 50, 40, 40, 40, 40,
                50, 50, 50, 50, 55, 55, 50, 55, 55, 50, 55
            ]

        self.setColumnCount(len(headers))
        self.setHorizontalHeaderLabels(headers)

        header = self.horizontalHeader()
        for i, width in enumerate(widths):
            header.resizeSection(i, width)
        
        self.setRowCount(len(data_list))

        for row, (player, team_name, record) in enumerate(data_list):
            if mode == "batter":
                avg = record.batting_average
                obp = record.obp
                slg = record.slg
                ops = record.ops
                iso = record.iso
                isod = obp - avg
                bb_k = record.walks / record.strikeouts if record.strikeouts > 0 else 0
                pa_k = record.plate_appearances / record.strikeouts if record.strikeouts > 0 else 0
                
                # RC Calculation (Basic)
                a = record.hits + record.walks + record.hit_by_pitch - record.caught_stealing - record.grounded_into_dp
                b = record.total_bases + (0.26 * (record.walks + record.hit_by_pitch)) + (0.52 * (record.sacrifice_hits + record.sacrifice_flies)) + (0.2 * record.stolen_bases)
                c = record.plate_appearances + record.walks + record.hit_by_pitch + record.sacrifice_hits + record.sacrifice_flies
                rc = ((a + 2.4 * c) * (b + 3 * c)) / (9 * c) - 0.9 * c if c > 0 else 0
                
                outs = record.at_bats - record.hits + record.caught_stealing + record.sacrifice_hits + record.sacrifice_flies + record.grounded_into_dp
                rc27 = (rc * 27) / outs if outs > 0 else 0
                
                # XR Calculation
                single = record.hits - record.doubles - record.triples - record.home_runs
                xr = (0.5 * single + 0.72 * record.doubles + 1.04 * record.triples + 1.44 * record.home_runs + 
                      0.34 * (record.walks + record.hit_by_pitch) + 0.18 * record.stolen_bases - 0.32 * record.caught_stealing - 
                      0.09 * (record.at_bats - record.hits - record.strikeouts) - 0.098 * record.strikeouts - 0.37 * record.grounded_into_dp + 
                      0.37 * record.sacrifice_flies + 0.04 * record.sacrifice_hits)
                xr27 = (xr * 27) / outs if outs > 0 else 0

                vals = [
                    player.name, team_name[:2], player.position.value[:2],
                    record.games, record.plate_appearances, record.at_bats,
                    f".{int(avg * 1000):03d}", record.hits, record.doubles, record.triples, record.home_runs,
                    record.rbis, record.runs, record.strikeouts, record.walks, record.hit_by_pitch,
                    record.sacrifice_hits, record.sacrifice_flies, record.stolen_bases, record.caught_stealing, record.grounded_into_dp,
                    f".{int(obp * 1000):03d}", f".{int(slg * 1000):03d}", f".{int(ops * 1000):03d}",
                    f".{int(iso * 1000):03d}", f".{int(isod * 1000):03d}", f".{int(record.babip * 1000):03d}",
                    f"{bb_k:.2f}", f"{pa_k:.1f}",
                    f".{int(record.woba * 1000):03d}", f"{record.wrc:.1f}", f"{int(record.wrc_plus)}",
                    f"{rc:.1f}", f"{rc27:.2f}", f"{xr:.1f}", f"{xr27:.2f}",
                    f"{record.war:.1f}", f"{record.uzr:.1f}"
                ]
                
                sort_vals = [
                    player.name, team_name, player.position.value,
                    record.games, record.plate_appearances, record.at_bats,
                    avg, record.hits, record.doubles, record.triples, record.home_runs,
                    record.rbis, record.runs, record.strikeouts, record.walks, record.hit_by_pitch,
                    record.sacrifice_hits, record.sacrifice_flies, record.stolen_bases, record.caught_stealing, record.grounded_into_dp,
                    obp, slg, ops, iso, isod, record.babip, bb_k, pa_k,
                    record.woba, record.wrc, record.wrc_plus, rc, rc27, xr, xr27,
                    record.war, record.uzr
                ]
            else:
                qs_rate = (record.quality_starts / record.games_started * 100) if record.games_started > 0 else 0
                avg_against = record.hits_allowed / (record.hits_allowed + record.balls_in_play + record.strikeouts_pitched) if (record.hits_allowed + record.balls_in_play + record.strikeouts_pitched) > 0 else 0 # Approx
                
                vals = [
                    player.name, team_name[:2], player.pitch_type.value[:2] if player.pitch_type else "投",
                    record.games_pitched, record.games_started, record.complete_games, record.shutouts, 0, # 無四球はデータなし
                    record.wins, record.losses, record.saves, record.holds,
                    f".{int(record.winning_percentage * 1000):03d}",
                    f"{record.era:.2f}", f"{record.innings_pitched:.1f}", 
                    int(record.hits_allowed + record.walks_allowed + record.hit_batters + record.strikeouts_pitched + record.balls_in_play), # TBF Approx
                    record.hits_allowed, record.home_runs_allowed, record.walks_allowed, record.hit_batters,
                    record.strikeouts_pitched, record.wild_pitches, record.balks, record.runs_allowed, record.earned_runs,
                    f"{record.k_per_9:.2f}", f"{record.bb_per_9:.2f}", f"{record.hr_per_9:.2f}", f"{record.k_bb_ratio:.2f}",
                    f"{record.whip:.2f}", f".{int(avg_against * 1000):03d}", f"{record.lob_rate * 100:.1f}%",
                    f"{record.fip:.2f}", f"{record.xfip:.2f}", f"{qs_rate:.1f}%", f"{record.war:.1f}"
                ]
                
                sort_vals = [
                    player.name, team_name, "P",
                    record.games_pitched, record.games_started, record.complete_games, record.shutouts, 0,
                    record.wins, record.losses, record.saves, record.holds, record.winning_percentage,
                    record.era if record.innings_pitched > 0 else 99, record.innings_pitched, 
                    record.hits_allowed, # TBF placeholder
                    record.hits_allowed, record.home_runs_allowed, record.walks_allowed, record.hit_batters,
                    record.strikeouts_pitched, record.wild_pitches, record.balks, record.runs_allowed, record.earned_runs,
                    record.k_per_9, record.bb_per_9, record.hr_per_9, record.k_bb_ratio,
                    record.whip if record.innings_pitched > 0 else 99, avg_against, record.lob_rate,
                    record.fip, record.xfip, qs_rate, record.war
                ]

            for col, (v, s) in enumerate(zip(vals, sort_vals)):
                item = SortableTableWidgetItem(str(v))
                item.setData(Qt.UserRole, s)
                if col < 3: item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                else: item.setTextAlignment(Qt.AlignCenter)
                self.setItem(row, col, item)


class StatsPage(QWidget):
    """
    Redesigned Stats Page with Sabermetrics and Horizontal Scrolling
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.current_team = None 
        self.current_league = "All"
        self.current_level = TeamLevel.FIRST
        
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.toolbar = self._create_toolbar()
        layout.addWidget(self.toolbar)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {self.theme.border}; border-radius: 8px; background-color: {self.theme.bg_card}; margin: 16px; }}
            QTabBar::tab {{ background-color: transparent; color: {self.theme.text_secondary}; padding: 10px 30px; font-weight: bold; font-size: 13px; }}
            QTabBar::tab:selected {{ color: {self.theme.primary}; border-bottom: 2px solid {self.theme.primary}; }}
            QTabBar::tab:hover {{ color: {self.theme.text_primary}; }}
        """)

        self.batter_table = StatsTable()
        self.tabs.addTab(self.batter_table, "野手成績") # Wrapper不要（スクロールはTable自体が持つ）

        self.pitcher_table = StatsTable()
        self.tabs.addTab(self.pitcher_table, "投手成績")

        layout.addWidget(self.tabs)

    def _create_toolbar(self) -> ToolbarPanel:
        toolbar = ToolbarPanel(); toolbar.setFixedHeight(50)
        
        lbl_lg = QLabel("リーグ:"); lbl_lg.setStyleSheet(f"color: {self.theme.text_secondary}; margin-left: 16px;")
        toolbar.add_widget(lbl_lg)
        self.league_combo = QComboBox(); self.league_combo.setMinimumWidth(120); self.league_combo.addItems(["全リーグ", "North League", "South League"])
        self.league_combo.setStyleSheet(self._get_combo_style())
        self.league_combo.currentIndexChanged.connect(self._on_league_changed)
        toolbar.add_widget(self.league_combo)
        toolbar.add_separator()

        lbl_tm = QLabel("チーム:"); lbl_tm.setStyleSheet(f"color: {self.theme.text_secondary};")
        toolbar.add_widget(lbl_tm)
        self.team_combo = QComboBox(); self.team_combo.setMinimumWidth(180)
        self.team_combo.setStyleSheet(self._get_combo_style())
        self.team_combo.currentIndexChanged.connect(self._on_team_changed)
        toolbar.add_widget(self.team_combo)
        toolbar.add_separator()

        self.btn_group = QButtonGroup(self); self.btn_group.setExclusive(True)
        self.btn_first = self._create_toggle_btn("一軍", True)
        self.btn_second = self._create_toggle_btn("二軍")
        self.btn_third = self._create_toggle_btn("三軍")
        self.btn_group.addButton(self.btn_first, 1)
        self.btn_group.addButton(self.btn_second, 2)
        self.btn_group.addButton(self.btn_third, 3)
        self.btn_group.idClicked.connect(self._on_level_changed)
        toolbar.add_widget(self.btn_first); toolbar.add_widget(self.btn_second); toolbar.add_widget(self.btn_third)
        toolbar.add_stretch()
        return toolbar

    def _get_combo_style(self):
        return f"QComboBox {{ background-color: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; border-radius: 4px; padding: 4px 8px; }} QComboBox::drop-down {{ border: none; }} QComboBox QAbstractItemView {{ background-color: {self.theme.bg_card}; color: {self.theme.text_primary}; selection-background-color: {self.theme.primary}; }}"

    def _create_toggle_btn(self, text, checked=False):
        btn = QPushButton(text); btn.setCheckable(True); btn.setChecked(checked); btn.setFixedSize(80, 32); btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(f"QPushButton {{ background-color: {self.theme.bg_card}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; border-radius: 4px; font-weight: bold; margin-right: 8px; }} QPushButton:checked {{ background-color: {self.theme.primary}; color: {self.theme.text_highlight}; border-color: {self.theme.primary}; }} QPushButton:hover {{ background-color: {self.theme.bg_card_hover}; }}")
        return btn

    def set_game_state(self, game_state):
        self.game_state = game_state
        if not game_state: return
        
        # 統計データを最新化
        update_league_stats(game_state.teams)

        self.team_combo.blockSignals(True)
        self.team_combo.clear()
        self.team_combo.addItem("全チーム", None)
        for team in game_state.teams:
            name = team.name + (" (自チーム)" if game_state.player_team and team == game_state.player_team else "")
            self.team_combo.addItem(name, team)
        self.team_combo.setCurrentIndex(0)
        self.team_combo.blockSignals(False)
        self._refresh_stats()

    def _on_league_changed(self, index):
        if index == 0: self.current_league = "All"
        elif index == 1: self.current_league = "North League"
        elif index == 2: self.current_league = "South League"
        self._refresh_stats()

    def _on_team_changed(self, index):
        self.current_team = self.team_combo.itemData(index)
        self._refresh_stats()

    def _on_level_changed(self, btn_id):
        if btn_id == 1: self.current_level = TeamLevel.FIRST
        elif btn_id == 2: self.current_level = TeamLevel.SECOND
        elif btn_id == 3: self.current_level = TeamLevel.THIRD
        self._refresh_stats()

    def _refresh_stats(self):
        if not self.game_state: return
        level = self.current_level
        batters_data = []
        pitchers_data = []
        target_teams = [self.current_team] if self.current_team else (self.game_state.teams if self.current_league == "All" else [t for t in self.game_state.teams if t.league.value == self.current_league])

        for team in target_teams:
            for player in team.players:
                record = player.get_record_by_level(level)
                if player.position.value == "投手":
                    if record.games_pitched > 0: pitchers_data.append((player, team.name, record))
                else:
                    if record.games > 0: batters_data.append((player, team.name, record))

        self.batter_table.set_data(batters_data, mode="batter")
        self.pitcher_table.set_data(pitchers_data, mode="pitcher")