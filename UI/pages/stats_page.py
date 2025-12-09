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
    player_double_clicked = Signal(object)  # 追加: 選手ダブルクリック時のシグナル

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._setup_ui()

    def _setup_ui(self):
        # 修正: 選択時の文字色を黒系に変更して視認性を向上
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
                color: #111111; /* 白背景で見にくい問題を修正: 黒文字に変更 */
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

        # 追加: ダブルクリックシグナルの接続
        self.cellDoubleClicked.connect(self._on_double_click)

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

    # 追加: ダブルクリックハンドラ
    def _on_double_click(self, row, col):
        item = self.item(row, 0)
        if item:
            # UserRole + 1 から選手オブジェクトを取得
            player = item.data(Qt.UserRole + 1)
            if player:
                self.player_double_clicked.emit(player)

    def set_data(self, data_list: list, mode: str = "batter"):
        self.clear()
        
        if mode == "batter":
            # 基本指標を復元し、新指標(Plate Discipline)を追加。「得点」を削除。
            headers = [
                "名前", "チーム", "Pos", "試合", "打席", "打数", "安打", "二塁", "三塁", "本塁", "打点", "三振", "四球", "盗塁", 
                "打率", "出塁", "長打", "OPS", "wOBA", "wRC+", "WAR",
                "ISO", "BABIP", "K%", "BB%", 
                "Hard%", "Mid%", "Soft%", "GB%", "FB%", "LD%", "IFFB%", "HR/FB",
                "Pull%", "Cent%", "Oppo%", 
                "O-Swing%", "Z-Swing%", "Swing%", "O-Contact%", "Z-Contact%", "Contact%", "Whiff%", "SwStr%",
                "wSB", "UBR", "UZR"
            ]
            widths = [
                140, 60, 40, 40, 45, 45, 45, 40, 40, 40, 40, 40, 40, 40,
                55, 55, 55, 55, 55, 50, 50,
                50, 55, 50, 50, 
                50, 50, 50, 50, 50, 50, 50, 50,
                50, 50, 50,
                65, 65, 60, 65, 65, 60, 60, 60,
                50, 50, 50
            ]
        else:
            # 基本指標を復元し、新指標(Plate Discipline)を追加
            headers = [
                "名前", "チーム", "Pos", "試合", "先発", "完投", "完封", "投球回", "被安", "被本", "与四", "奪三", "失点", "自責", 
                "防御率", "勝利", "敗戦", "S", "H", "WHIP", "FIP", "xFIP", "WAR",
                "K/9", "BB/9", "K/BB", "HR/9", "K%", "BB%", "LOB%", 
                "Hard%", "Mid%", "Soft%", "GB%", "FB%", "LD%", "IFFB%", "HR/FB",
                "O-Swing%", "Z-Swing%", "Swing%", "O-Contact%", "Z-Contact%", "Contact%", "Whiff%", "SwStr%"
            ]
            widths = [
                140, 60, 40, 40, 40, 40, 40, 55, 45, 40, 40, 45, 40, 40, 
                55, 40, 40, 35, 35, 50, 50, 50, 50,
                50, 50, 50, 50, 50, 50, 50, 
                50, 50, 50, 50, 50, 50, 50, 50,
                65, 65, 60, 65, 65, 60, 60, 60
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
                ops = record.ops
                
                vals = [
                    player.name, team_name[:2], player.position.value[:2],
                    record.games, record.plate_appearances, record.at_bats, record.hits, record.doubles, record.triples, record.home_runs, record.rbis, record.strikeouts, record.walks, record.stolen_bases,
                    f".{int(avg * 1000):03d}", f".{int(record.obp * 1000):03d}", f".{int(record.slg * 1000):03d}", f".{int(ops * 1000):03d}", 
                    f".{int(record.woba * 1000):03d}", int(record.wrc_plus), f"{record.war:.1f}",
                    f"{record.iso:.3f}", f"{record.babip:.3f}", f"{record.k_pct*100:.1f}%", f"{record.bb_pct*100:.1f}%",
                    f"{record.hard_pct*100:.1f}%", f"{record.mid_pct*100:.1f}%", f"{record.soft_pct*100:.1f}%",
                    f"{record.gb_pct*100:.1f}%", f"{record.fb_pct*100:.1f}%", f"{record.ld_pct*100:.1f}%", f"{record.iffb_pct*100:.1f}%", f"{record.hr_fb*100:.1f}%",
                    f"{record.pull_pct*100:.1f}%", f"{record.cent_pct*100:.1f}%", f"{record.oppo_pct*100:.1f}%",
                    f"{record.o_swing_pct*100:.1f}%", f"{record.z_swing_pct*100:.1f}%", f"{record.swing_pct*100:.1f}%",
                    f"{record.o_contact_pct*100:.1f}%", f"{record.z_contact_pct*100:.1f}%", f"{record.contact_pct*100:.1f}%", f"{record.whiff_pct*100:.1f}%", f"{record.swstr_pct*100:.1f}%",
                    f"{record.wsb:.1f}", f"{record.ubr:.1f}", f"{record.uzr:.1f}"
                ]
                
                sort_vals = [
                    player.name, team_name, player.position.value,
                    record.games, record.plate_appearances, record.at_bats, record.hits, record.doubles, record.triples, record.home_runs, record.rbis, record.strikeouts, record.walks, record.stolen_bases,
                    avg, record.obp, record.slg, ops, 
                    record.woba, record.wrc_plus, record.war,
                    record.iso, record.babip, record.k_pct, record.bb_pct,
                    record.hard_pct, record.mid_pct, record.soft_pct,
                    record.gb_pct, record.fb_pct, record.ld_pct, record.iffb_pct, record.hr_fb,
                    record.pull_pct, record.cent_pct, record.oppo_pct,
                    record.o_swing_pct, record.z_swing_pct, record.swing_pct,
                    record.o_contact_pct, record.z_contact_pct, record.contact_pct, record.whiff_pct, record.swstr_pct,
                    record.wsb, record.ubr, record.uzr
                ]
            else:
                k_pct = record.k_rate_pitched
                bb_pct = record.bb_rate_pitched
                
                vals = [
                    player.name, team_name[:2], player.pitch_type.value[:2] if player.pitch_type else "投",
                    record.games_pitched, record.games_started, record.complete_games, record.shutouts, f"{record.innings_pitched:.1f}", record.hits_allowed, record.home_runs_allowed, record.walks_allowed, record.strikeouts_pitched, record.runs_allowed, record.earned_runs,
                    f"{record.era:.2f}", record.wins, record.losses, record.saves, record.holds, f"{record.whip:.2f}", f"{record.fip:.2f}", f"{record.xfip:.2f}", f"{record.war:.1f}",
                    f"{record.k_per_9:.2f}", f"{record.bb_per_9:.2f}", f"{record.k_bb_ratio:.2f}", f"{record.hr_per_9:.2f}",
                    f"{k_pct*100:.1f}%", f"{bb_pct*100:.1f}%", f"{record.lob_rate*100:.1f}%",
                    f"{record.hard_pct*100:.1f}%", f"{record.mid_pct*100:.1f}%", f"{record.soft_pct*100:.1f}%",
                    f"{record.gb_pct*100:.1f}%", f"{record.fb_pct*100:.1f}%", f"{record.ld_pct*100:.1f}%", f"{record.iffb_pct*100:.1f}%", f"{record.hr_fb*100:.1f}%",
                    f"{record.o_swing_pct*100:.1f}%", f"{record.z_swing_pct*100:.1f}%", f"{record.swing_pct*100:.1f}%",
                    f"{record.o_contact_pct*100:.1f}%", f"{record.z_contact_pct*100:.1f}%", f"{record.contact_pct*100:.1f}%", f"{record.whiff_pct*100:.1f}%", f"{record.swstr_pct*100:.1f}%"
                ]
                
                sort_vals = [
                    player.name, team_name, "P",
                    record.games_pitched, record.games_started, record.complete_games, record.shutouts, record.innings_pitched, record.hits_allowed, record.home_runs_allowed, record.walks_allowed, record.strikeouts_pitched, record.runs_allowed, record.earned_runs,
                    record.era if record.innings_pitched > 0 else 99, record.wins, record.losses, record.saves, record.holds, record.whip if record.innings_pitched > 0 else 99, 
                    record.fip, record.xfip, record.war,
                    record.k_per_9, record.bb_per_9, record.k_bb_ratio, record.hr_per_9,
                    k_pct, bb_pct, record.lob_rate,
                    record.hard_pct, record.mid_pct, record.soft_pct,
                    record.gb_pct, record.fb_pct, record.ld_pct, record.iffb_pct, record.hr_fb,
                    record.o_swing_pct, record.z_swing_pct, record.swing_pct,
                    record.o_contact_pct, record.z_contact_pct, record.contact_pct, record.whiff_pct, record.swstr_pct
                ]

            for col, (v, s) in enumerate(zip(vals, sort_vals)):
                item = SortableTableWidgetItem(str(v))
                item.setData(Qt.UserRole, s)
                if col == 0:
                    item.setData(Qt.UserRole + 1, player)
                
                if col < 3: item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                else: item.setTextAlignment(Qt.AlignCenter)
                self.setItem(row, col, item)


class StatsPage(QWidget):
    """
    Redesigned Stats Page with Sabermetrics and Horizontal Scrolling
    """
    player_detail_requested = Signal(object)  # 追加: 詳細リクエストシグナル

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
        self.tabs.addTab(self.batter_table, "野手成績") 
        # 追加: シグナル接続
        self.batter_table.player_double_clicked.connect(self.player_detail_requested.emit)

        self.pitcher_table = StatsTable()
        self.tabs.addTab(self.pitcher_table, "投手成績")
        # 追加: シグナル接続
        self.pitcher_table.player_double_clicked.connect(self.player_detail_requested.emit)

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