# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Contract Renewal Page
Offseason Contract Management
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTabWidget,
    QSplitter, QFrame, QPushButton, QScrollArea, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QComboBox,
    QDialog, QSpinBox, QGridLayout
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.panels import InfoPanel


def format_salary(salary_yen: int) -> str:
    """年俸を億万表記にフォーマット (salary is in 円 units)"""
    man = salary_yen // 10000
    if man >= 10000:
        oku = man // 10000
        remainder = man % 10000
        if remainder > 0:
            return f"{oku}億{remainder}万"
        return f"{oku}億"
    return f"{man}万"


def ovr_to_stars(ovr: int) -> str:
    """総合力を★表記に変換"""
    return f"★{ovr}"


class SortableTableWidgetItem(QTableWidgetItem):
    """数値ソート対応のテーブルアイテム"""
    def __lt__(self, other):
        v1 = self.data(Qt.UserRole)
        v2 = other.data(Qt.UserRole)
        if v1 is not None and v2 is not None:
            try:
                return float(v1) < float(v2)
            except (ValueError, TypeError):
                pass
        return super().__lt__(other)


class ContractNegotiationDialog(QDialog):
    """契約交渉ダイアログ（年数×年俸形式）"""
    
    def __init__(self, player, team_budget: int, parent=None):
        super().__init__(parent)
        self.player = player
        self.team_budget = team_budget
        self.theme = get_theme()
        self.result_years = 1
        self.result_salary = 0
        
        self.setWindowTitle("契約交渉")
        self.setFixedSize(600, 400)
        self.setModal(True)
        self._setup_ui()
    
    def _setup_ui(self):
        self.setStyleSheet(f"""
            QDialog {{
                background: {self.theme.bg_card};
            }}
            QLabel {{
                color: {self.theme.text_primary};
            }}
            QSpinBox {{
                background: {self.theme.bg_input};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                padding: 8px;
                font-size: 18px;
                font-weight: bold;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # ヘッダー（球団資金）
        header = QFrame()
        header.setStyleSheet(f"background: {self.theme.bg_dark}; padding: 8px;")
        header_layout = QHBoxLayout(header)
        budget_label = QLabel(f"球団資金: {format_salary(self.team_budget)}")
        budget_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header_layout.addWidget(budget_label)
        header_layout.addStretch()
        layout.addWidget(header)
        
        # 選手情報
        player_info = QLabel(f"{self.player.name} ({self.player.position.value}) - {self.player.age}歳")
        player_info.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {self.theme.primary};")
        layout.addWidget(player_info)
        
        # 契約グリッド
        grid = QGridLayout()
        grid.setSpacing(12)
        
        # ヘッダー行
        headers = ["", "年数", "", "年俸（1年分）", "", "契約金総額"]
        for col, h in enumerate(headers):
            lbl = QLabel(h)
            lbl.setStyleSheet(f"font-size: 12px; color: {self.theme.text_secondary};")
            lbl.setAlignment(Qt.AlignCenter)
            grid.addWidget(lbl, 0, col)
        
        # 契約行
        contract_label = QLabel("契約")
        contract_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        grid.addWidget(contract_label, 1, 0)
        
        self.years_spin = QSpinBox()
        self.years_spin.setRange(1, 5)
        self.years_spin.setValue(1)
        self.years_spin.setFixedWidth(80)
        self.years_spin.valueChanged.connect(self._update_totals)
        grid.addWidget(self.years_spin, 1, 1)
        
        grid.addWidget(QLabel("×"), 1, 2)
        
        self.salary_spin = QSpinBox()
        self.salary_spin.setRange(500, 100000)
        self.salary_spin.setSingleStep(100)
        desired = getattr(self.player, 'desired_salary', 10000000) // 10000
        self.salary_spin.setValue(desired)
        self.salary_spin.setSuffix("万円")
        self.salary_spin.setFixedWidth(150)
        self.salary_spin.valueChanged.connect(self._update_totals)
        grid.addWidget(self.salary_spin, 1, 3)
        
        grid.addWidget(QLabel("="), 1, 4)
        
        self.total_label = QLabel("")
        self.total_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {self.theme.success};")
        grid.addWidget(self.total_label, 1, 5)
        
        # 選手希望行
        demand_label = QLabel("選手希望")
        demand_label.setStyleSheet(f"font-size: 14px; color: {self.theme.accent_blue};")
        grid.addWidget(demand_label, 2, 0)
        
        desired_years = getattr(self.player, 'desired_years', 1)
        desired_salary = getattr(self.player, 'desired_salary', 10000000)
        
        years_lbl = QLabel(f"{desired_years}年")
        years_lbl.setStyleSheet(f"font-size: 16px; color: {self.theme.accent_blue};")
        years_lbl.setAlignment(Qt.AlignCenter)
        grid.addWidget(years_lbl, 2, 1)
        
        grid.addWidget(QLabel("×"), 2, 2)
        
        salary_lbl = QLabel(format_salary(desired_salary))
        salary_lbl.setStyleSheet(f"font-size: 16px; color: {self.theme.accent_blue};")
        salary_lbl.setAlignment(Qt.AlignCenter)
        grid.addWidget(salary_lbl, 2, 3)
        
        grid.addWidget(QLabel("="), 2, 4)
        
        total_demand = desired_years * desired_salary
        demand_total = QLabel(format_salary(total_demand))
        demand_total.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {self.theme.accent_blue};")
        grid.addWidget(demand_total, 2, 5)
        
        layout.addLayout(grid)
        
        # FA情報
        years_to_fa = max(0, 8 - getattr(self.player, 'years_pro', 1))
        fa_label = QLabel(f"FA権取得まで残り {years_to_fa}年")
        fa_label.setStyleSheet(f"font-size: 12px; color: {self.theme.text_muted};")
        fa_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(fa_label)
        
        layout.addStretch()
        
        # ボタン
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.bg_card_elevated};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                padding: 10px 24px;
                font-size: 14px;
            }}
            QPushButton:hover {{ background: {self.theme.bg_card_hover}; }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("決定")
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background: {self.theme.success};
                color: white;
                border: none;
                padding: 10px 24px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: {self.theme.success_hover}; }}
        """)
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
        
        self._update_totals()
    
    def _update_totals(self):
        years = self.years_spin.value()
        salary = self.salary_spin.value() * 10000
        total = years * salary
        self.total_label.setText(format_salary(total))
        self.result_years = years
        self.result_salary = salary
    
    def get_contract(self):
        return self.result_years, self.result_salary


class ContractRenewalPage(QWidget):
    """契約更改ページ"""
    
    completed = Signal()
    back_requested = Signal()
    player_selected = Signal(object)
    show_player_detail_requested = Signal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.current_team = None
        self.selected_player = None
        self.all_batters = []
        self.all_pitchers = []
        self.all_staff = []
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        header = self._create_header()
        layout.addWidget(header)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {self.theme.border}; width: 2px; }}")
        
        left_panel = self._create_player_list_panel()
        splitter.addWidget(left_panel)
        
        right_panel = self._create_detail_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([720, 280])
        
        layout.addWidget(splitter, 1)
        
        footer = self._create_footer()
        layout.addWidget(footer)
    
    def _create_header(self) -> QFrame:
        header = QFrame()
        header.setFixedHeight(100)
        header.setStyleSheet(f"QFrame {{ background: {self.theme.bg_card}; border-bottom: 2px solid {self.theme.border}; }}")
        
        layout = QVBoxLayout(header)
        layout.setContentsMargins(24, 8, 24, 8)
        layout.setSpacing(8)
        
        # 上段: タイトル
        top_row = QHBoxLayout()
        title = QLabel("契約更改")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {self.theme.text_primary};")
        top_row.addWidget(title)
        top_row.addStretch()
        self.progress_label = QLabel("0/0")
        self.progress_label.setStyleSheet(f"font-size: 14px; color: {self.theme.text_secondary};")
        top_row.addWidget(self.progress_label)
        layout.addLayout(top_row)
        
        # 下段: 球団資金バー
        budget_bar = QFrame()
        budget_bar.setStyleSheet(f"background: {self.theme.bg_dark}; border-radius: 4px;")
        budget_layout = QHBoxLayout(budget_bar)
        budget_layout.setContentsMargins(16, 6, 16, 6)
        budget_layout.setSpacing(24)
        
        self.budget_label = QLabel("球団資金: ---")
        self.budget_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {self.theme.primary};")
        budget_layout.addWidget(self.budget_label)
        
        self.payments_label = QLabel("支払い: ---")
        self.payments_label.setStyleSheet(f"font-size: 13px; color: {self.theme.accent_red};")
        budget_layout.addWidget(self.payments_label)
        
        self.remaining_label = QLabel("残高: ---")
        self.remaining_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {self.theme.success};")
        budget_layout.addWidget(self.remaining_label)
        
        budget_layout.addStretch()
        layout.addWidget(budget_bar)
        
        return header
    
    def _create_player_list_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 4, 8)
        layout.setSpacing(6)
        
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: 1px solid {self.theme.border}; background-color: {self.theme.bg_card}; }}
            QTabBar::tab {{ background-color: {self.theme.bg_card}; color: {self.theme.text_secondary}; padding: 8px 20px; border: 1px solid {self.theme.border}; border-bottom: none; font-weight: bold; }}
            QTabBar::tab:selected {{ background-color: {self.theme.primary}; color: #222222; }}
        """)
        
        # 野手タブ
        batter_tab = QWidget()
        batter_layout = QVBoxLayout(batter_tab)
        batter_layout.setContentsMargins(0, 6, 0, 0)
        batter_layout.setSpacing(4)
        batter_filter = self._create_filter_bar("batter")
        batter_layout.addWidget(batter_filter)
        self.batter_table = self._create_player_table("batter")
        batter_layout.addWidget(self.batter_table)
        self.tabs.addTab(batter_tab, "野手")
        
        # 投手タブ
        pitcher_tab = QWidget()
        pitcher_layout = QVBoxLayout(pitcher_tab)
        pitcher_layout.setContentsMargins(0, 6, 0, 0)
        pitcher_layout.setSpacing(4)
        pitcher_filter = self._create_filter_bar("pitcher")
        pitcher_layout.addWidget(pitcher_filter)
        self.pitcher_table = self._create_player_table("pitcher")
        pitcher_layout.addWidget(self.pitcher_table)
        self.tabs.addTab(pitcher_tab, "投手")
        
        # スタッフタブ（選手タブと同様の形式）
        staff_tab = QWidget()
        staff_layout = QVBoxLayout(staff_tab)
        staff_layout.setContentsMargins(0, 6, 0, 0)
        staff_layout.setSpacing(4)
        staff_filter = self._create_filter_bar("staff")
        staff_layout.addWidget(staff_filter)
        self.staff_table = self._create_staff_table()
        staff_layout.addWidget(self.staff_table)
        self.tabs.addTab(staff_tab, "スタッフ")
        
        layout.addWidget(self.tabs)
        return panel
    
    def _create_filter_bar(self, mode: str) -> QWidget:
        bar = QWidget()
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(4, 0, 4, 4)
        
        filter_style = f"""
            QComboBox {{ background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 4px 12px; min-width: 120px; font-size: 12px; }}
            QComboBox::drop-down {{ border: none; width: 20px; }}
            QComboBox QAbstractItemView {{ background: {self.theme.bg_card}; color: {self.theme.text_primary}; selection-background-color: {self.theme.primary}; }}
        """
        
        pos_combo = QComboBox()
        if mode == "batter":
            pos_combo.addItems(["全ポジション", "捕手", "一塁手", "二塁手", "三塁手", "遊撃手", "外野手"])
            pos_combo.currentIndexChanged.connect(lambda: self._filter_batters(pos_combo))
            self.batter_pos_filter = pos_combo
        elif mode == "pitcher":
            pos_combo.addItems(["全タイプ", "先発", "中継ぎ", "抑え"])
            pos_combo.currentIndexChanged.connect(lambda: self._filter_pitchers(pos_combo))
            self.pitcher_type_filter = pos_combo
        else:
            pos_combo.addItems(["全役職", "監督", "コーチ", "スカウト"])
            pos_combo.currentIndexChanged.connect(lambda: self._filter_staff(pos_combo))
            self.staff_role_filter = pos_combo
        pos_combo.setStyleSheet(filter_style)
        layout.addWidget(pos_combo)
        layout.addStretch()
        return bar
    
    def _create_player_table(self, mode: str) -> QTableWidget:
        table = QTableWidget()
        
        if mode == "batter":
            headers = ["#", "名前", "守備", "年齢", "総合", "打率", "HR", "打点", "今季年俸", "希望年俸", "提示年俸"]
            widths = [45, 110, 65, 50, 60, 60, 45, 50, 85, 85, 60]
        else:
            headers = ["#", "名前", "役割", "年齢", "総合", "防御率", "勝", "S", "今季年俸", "希望年俸", "提示年俸"]
            widths = [45, 110, 65, 50, 60, 60, 45, 45, 85, 85, 60]
        
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        for i, w in enumerate(widths):
            table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Fixed)
            table.setColumnWidth(i, w)
        
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(28)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        
        table.setStyleSheet(f"""
            QTableWidget {{ background: {self.theme.bg_card}; alternate-background-color: {self.theme.bg_card_elevated}; color: {self.theme.text_primary}; border: none; font-size: 12px; }}
            QTableWidget::item {{ padding: 4px 6px; border-bottom: 1px solid {self.theme.border_muted}; }}
            QTableWidget::item:selected {{ background: {self.theme.primary}; color: #222222; }}
            QHeaderView::section {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {self.theme.bg_card_elevated}, stop:1 {self.theme.bg_card}); color: {self.theme.text_secondary}; padding: 5px 4px; border: none; border-bottom: 2px solid {self.theme.primary}; font-weight: bold; font-size: 11px; }}
        """)
        table.itemSelectionChanged.connect(lambda: self._on_table_selection(table))
        table.cellDoubleClicked.connect(lambda row, col: self._on_table_double_click(table, row))
        
        header = table.horizontalHeader()
        header.sectionClicked.connect(lambda col: self._toggle_sort(table, col))
        
        return table
    
    def _create_staff_table(self) -> QTableWidget:
        """スタッフテーブル（選手テーブルと同様の形式）"""
        table = QTableWidget()
        headers = ["#", "名前", "役職", "年齢", "能力", "経験年数", "今季年俸", "希望年俸", "提示年俸"]
        widths = [40, 100, 80, 40, 50, 60, 80, 80, 80]
        
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        for i, w in enumerate(widths):
            table.horizontalHeader().setSectionResizeMode(i, QHeaderView.Fixed)
            table.setColumnWidth(i, w)
        
        table.horizontalHeader().setStretchLastSection(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(28)
        table.setShowGrid(False)
        table.setAlternatingRowColors(True)
        table.setSortingEnabled(True)
        
        table.setStyleSheet(f"""
            QTableWidget {{ background: {self.theme.bg_card}; alternate-background-color: {self.theme.bg_card_elevated}; color: {self.theme.text_primary}; border: none; font-size: 12px; }}
            QTableWidget::item {{ padding: 4px 6px; border-bottom: 1px solid {self.theme.border_muted}; }}
            QTableWidget::item:selected {{ background: {self.theme.primary}; color: #222222; }}
            QHeaderView::section {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {self.theme.bg_card_elevated}, stop:1 {self.theme.bg_card}); color: {self.theme.text_secondary}; padding: 5px 4px; border: none; border-bottom: 2px solid {self.theme.primary}; font-weight: bold; font-size: 11px; }}
        """)
        table.itemSelectionChanged.connect(lambda: self._on_staff_selection(table))
        
        header = table.horizontalHeader()
        header.sectionClicked.connect(lambda col: self._toggle_sort(table, col))
        
        return table
    
    def _toggle_sort(self, table, column):
        header = table.horizontalHeader()
        current_order = header.sortIndicatorOrder()
        if header.sortIndicatorSection() != column:
            table.sortItems(column, Qt.DescendingOrder)
        elif current_order == Qt.DescendingOrder:
            table.sortItems(column, Qt.AscendingOrder)
        else:
            table.sortItems(column, Qt.DescendingOrder)
    
    def _create_detail_panel(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"QScrollArea {{ background-color: {self.theme.bg_dark}; border: none; }} QScrollBar:vertical {{ background-color: {self.theme.bg_dark}; width: 6px; }} QScrollBar::handle:vertical {{ background-color: {self.theme.border}; }}")
        
        panel = QWidget()
        panel.setStyleSheet(f"background-color: {self.theme.bg_dark};")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        self.info_panel = InfoPanel("選手情報")
        layout.addWidget(self.info_panel)
        
        self.stats_panel = InfoPanel("今季成績")
        layout.addWidget(self.stats_panel)
        
        action_frame = QFrame()
        action_frame.setStyleSheet(f"QFrame {{ background-color: {self.theme.bg_card}; border: 1px solid {self.theme.border}; }}")
        action_layout = QVBoxLayout(action_frame)
        action_layout.setContentsMargins(10, 10, 10, 10)
        action_layout.setSpacing(6)
        
        action_title = QLabel("アクション")
        action_title.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {self.theme.text_secondary}; letter-spacing: 1px;")
        action_layout.addWidget(action_title)
        
        self.negotiate_btn = self._create_action_button("契約交渉", self._on_negotiate)
        action_layout.addWidget(self.negotiate_btn)
        
        self.retire_btn = self._create_action_button("引退打診", self._on_retire)
        action_layout.addWidget(self.retire_btn)
        
        self.staff_convert_btn = self._create_action_button("スタッフ転身", self._on_staff_convert)
        action_layout.addWidget(self.staff_convert_btn)
        
        self.release_btn = self._create_action_button("自由契約", self._on_release, danger=True)
        action_layout.addWidget(self.release_btn)
        
        layout.addWidget(action_frame)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet(f"font-size: 11px; color: {self.theme.success};")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        
        scroll.setWidget(panel)
        return scroll
    
    def _create_action_button(self, text: str, callback, danger: bool = False) -> QPushButton:
        btn = QPushButton(text)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedHeight(32)
        
        bg_color = self.theme.accent_red if danger else self.theme.bg_card_elevated
        hover_color = self.theme.accent_red_hover if danger else self.theme.bg_card_hover
        text_color = "white" if danger else self.theme.text_primary
        
        btn.setStyleSheet(f"""
            QPushButton {{ background: {bg_color}; color: {text_color}; border: 1px solid {self.theme.border}; font-size: 12px; font-weight: bold; text-align: left; padding-left: 10px; }}
            QPushButton:hover {{ background: {hover_color}; }}
            QPushButton:disabled {{ background: {self.theme.bg_card}; color: {self.theme.text_muted}; }}
        """)
        btn.clicked.connect(callback)
        btn.setEnabled(False)
        return btn
    
    def _create_footer(self) -> QWidget:
        footer = QFrame()
        footer.setFixedHeight(50)
        footer.setStyleSheet(f"QFrame {{ background: {self.theme.bg_card}; border-top: 1px solid {self.theme.border}; }}")
        
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.addStretch()
        
        complete_btn = QPushButton("契約更改完了")
        complete_btn.setCursor(Qt.PointingHandCursor)
        complete_btn.setFixedHeight(36)
        complete_btn.setStyleSheet(f"QPushButton {{ background: {self.theme.success}; color: white; border: none; padding: 0 30px; font-size: 13px; font-weight: bold; letter-spacing: 1px; }} QPushButton:hover {{ background: {self.theme.success_hover}; }}")
        complete_btn.clicked.connect(self._on_complete)
        layout.addWidget(complete_btn)
        
        return footer
    
    # === データメソッド ===
    
    def set_game_state(self, game_state):
        self.game_state = game_state
        if not game_state:
            return
        
        self.current_team = game_state.player_team
        self._init_player_contracts()
        self._refresh_player_lists()
        self._refresh_staff_list()
        self._update_progress()
        self._update_budget_display()
    
    def _update_budget_display(self):
        """球団資金表示を更新"""
        if not self.current_team:
            return
        
        budget = getattr(self.current_team, 'budget', 5000000000)
        total_payments = sum(getattr(p, 'new_salary', getattr(p, 'salary', 10000000)) 
                           for p in self.current_team.players)
        remaining = budget - total_payments
        
        self.budget_label.setText(f"球団資金: {format_salary(budget)}")
        self.payments_label.setText(f"支払い: {format_salary(total_payments)}")
        self.remaining_label.setText(f"残高: {format_salary(remaining)}")
    
    def _init_player_contracts(self):
        if not self.current_team:
            return
        
        for player in self.current_team.players:
            # FA権計算（NPB: 高卒8年、大卒/社会人7年で国内FA、+1年で海外FA）
            years_pro = getattr(player, 'years_pro', 1)
            player.years_to_domestic_fa = max(0, 8 - years_pro)  # 簡略化: 8年
            player.years_to_overseas_fa = max(0, 9 - years_pro)
            player.has_domestic_fa = years_pro >= 8
            player.has_overseas_fa = years_pro >= 9
            
            if not hasattr(player, 'desired_salary') or player.desired_salary is None:
                current = getattr(player, 'salary', 10000000)
                performance_bonus = self._calculate_performance_bonus(player)
                player.desired_salary = max(5000000, int(current * (1 + performance_bonus)))
                player.new_salary = player.desired_salary
            
            # 希望年数（FA前は複数年を嫌う）
            if not hasattr(player, 'desired_years'):
                if player.years_to_domestic_fa <= 2:
                    player.desired_years = 1  # FA直前は単年
                elif player.age >= 35:
                    player.desired_years = 1  # ベテランは単年
                else:
                    player.desired_years = 2
    
    def _calculate_multiyear_premium(self, player, years: int) -> float:
        """複数年契約時の希望年俸増加率を計算（FA前は大幅増）"""
        if years <= 1:
            return 0.0
        
        base_premium = (years - 1) * 0.05  # 基本: 年あたり5%増
        
        # FA前は大幅増
        years_to_fa = getattr(player, 'years_to_domestic_fa', 99)
        if years_to_fa <= 3 and years > years_to_fa:
            # FA権を放棄する形になる → 大幅増
            fa_premium = 0.5 + (3 - years_to_fa) * 0.3  # 50-110%増
            return base_premium + fa_premium
        
        return base_premium
    
    def _calculate_performance_bonus(self, player) -> float:
        if not hasattr(player, 'record') or not player.record:
            return 0.0
        
        record = player.record
        
        if player.position.value == "投手":
            era = getattr(record, 'era', 4.00)
            wins = getattr(record, 'wins', 0)
            bonus = 0.0
            if era < 2.50: bonus += 0.30
            elif era < 3.00: bonus += 0.15
            elif era < 3.50: bonus += 0.05
            bonus += wins * 0.02
            return min(0.5, bonus)
        else:
            avg = getattr(record, 'batting_average', 0.250)
            hr = getattr(record, 'home_runs', 0)
            bonus = 0.0
            if avg > 0.300: bonus += 0.20
            elif avg > 0.280: bonus += 0.10
            bonus += hr * 0.01
            return min(0.5, bonus)
    
    def _refresh_player_lists(self):
        if not self.current_team:
            return
        
        team = self.current_team
        self.all_batters = [p for p in team.players if p.position.value != "投手"]
        self.all_pitchers = [p for p in team.players if p.position.value == "投手"]
        
        self._populate_batter_table(self.all_batters)
        self._populate_pitcher_table(self.all_pitchers)
    
    def _populate_batter_table(self, players):
        self.batter_table.setSortingEnabled(False)
        self.batter_table.setRowCount(len(players))
        
        for row, player in enumerate(players):
            record = player.record if hasattr(player, 'record') else None
            self._set_player_row(self.batter_table, row, player, record, is_pitcher=False)
        
        self.batter_table.setSortingEnabled(True)
    
    def _populate_pitcher_table(self, players):
        self.pitcher_table.setSortingEnabled(False)
        self.pitcher_table.setRowCount(len(players))
        
        for row, player in enumerate(players):
            record = player.record if hasattr(player, 'record') else None
            self._set_player_row(self.pitcher_table, row, player, record, is_pitcher=True)
        
        self.pitcher_table.setSortingEnabled(True)
    
    def _set_player_row(self, table, row, player, record, is_pitcher: bool):
        # #
        num_item = SortableTableWidgetItem(str(player.uniform_number))
        num_item.setData(Qt.UserRole, player.uniform_number)
        num_item.setData(Qt.UserRole + 1, player)
        num_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, 0, num_item)
        
        # 名前
        table.setItem(row, 1, QTableWidgetItem(player.name))
        
        # 守備/役割
        if is_pitcher:
            role = player.pitch_type.value[:3] if hasattr(player, 'pitch_type') and player.pitch_type else "投手"
        else:
            role = player.position.value[:3] if hasattr(player.position, 'value') else str(player.position)[:3]
        role_item = QTableWidgetItem(role)
        role_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, 2, role_item)
        
        # 年齢
        age_item = SortableTableWidgetItem(str(player.age))
        age_item.setData(Qt.UserRole, player.age)
        age_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, 3, age_item)
        
        # 総合
        ovr = getattr(player, 'overall_rating', 50)
        ovr_item = SortableTableWidgetItem(ovr_to_stars(ovr))
        ovr_item.setData(Qt.UserRole, ovr)
        ovr_item.setForeground(QColor("#FFD700"))
        ovr_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, 4, ovr_item)
        
        # 成績
        if record:
            if is_pitcher:
                era = record.era if record.innings_pitched > 0 else 0
                stat1 = SortableTableWidgetItem(f"{era:.2f}")
                stat1.setData(Qt.UserRole, era)
                stat2 = SortableTableWidgetItem(str(record.wins))
                stat2.setData(Qt.UserRole, record.wins)
                stat3 = SortableTableWidgetItem(str(record.saves))
                stat3.setData(Qt.UserRole, record.saves)
            else:
                avg = record.batting_average if record.at_bats > 0 else 0
                stat1 = SortableTableWidgetItem(f".{int(avg * 1000):03d}")
                stat1.setData(Qt.UserRole, avg)
                stat2 = SortableTableWidgetItem(str(record.home_runs))
                stat2.setData(Qt.UserRole, record.home_runs)
                stat3 = SortableTableWidgetItem(str(record.rbis))
                stat3.setData(Qt.UserRole, record.rbis)
            
            for item in [stat1, stat2, stat3]:
                item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 5, stat1)
            table.setItem(row, 6, stat2)
            table.setItem(row, 7, stat3)
        else:
            for col in [5, 6, 7]:
                item = QTableWidgetItem("-")
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(QColor(self.theme.text_muted))
                table.setItem(row, col, item)
        
        # 年俸
        current = getattr(player, 'salary', 10000000)
        desired = getattr(player, 'desired_salary', current)
        offer = getattr(player, 'new_salary', desired)
        
        cur_item = SortableTableWidgetItem(format_salary(current))
        cur_item.setData(Qt.UserRole, current)
        cur_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        table.setItem(row, 8, cur_item)
        
        des_item = SortableTableWidgetItem(format_salary(desired))
        des_item.setData(Qt.UserRole, desired)
        des_item.setForeground(QColor(self.theme.accent_blue))
        des_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        table.setItem(row, 9, des_item)
        
        off_item = SortableTableWidgetItem(format_salary(offer))
        off_item.setData(Qt.UserRole, offer)
        off_item.setForeground(QColor(self.theme.success))
        off_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        table.setItem(row, 10, off_item)
    
    def _filter_batters(self, combo):
        idx = combo.currentIndex()
        if idx == 0:
            filtered = self.all_batters
        else:
            positions = ["捕手", "一塁手", "二塁手", "三塁手", "遊撃手", "外野手"]
            target = positions[idx - 1]
            filtered = [p for p in self.all_batters if p.position.value == target]
        self._populate_batter_table(filtered)
    
    def _filter_pitchers(self, combo):
        idx = combo.currentIndex()
        if idx == 0:
            filtered = self.all_pitchers
        else:
            types = ["先発", "中継ぎ", "抑え"]
            target = types[idx - 1]
            filtered = [p for p in self.all_pitchers if hasattr(p, 'pitch_type') and p.pitch_type and p.pitch_type.value == target]
        self._populate_pitcher_table(filtered)
    
    def _filter_staff(self, combo):
        idx = combo.currentIndex()
        if idx == 0:
            filtered = self.all_staff
        else:
            roles = ["監督", "コーチ", "スカウト"]
            target = roles[idx - 1]
            filtered = [s for s in self.all_staff if target in str(getattr(s, 'role', ''))]
        self._populate_staff_table(filtered)
    
    def _refresh_staff_list(self):
        self.all_staff = []
        if not self.current_team:
            return
        
        staff_list = getattr(self.current_team, 'staff', None)
        if staff_list and isinstance(staff_list, list):
            self.all_staff = staff_list
        
        self._populate_staff_table(self.all_staff)
    
    def _populate_staff_table(self, staff_list):
        self.staff_table.setSortingEnabled(False)
        self.staff_table.setRowCount(len(staff_list))
        
        for row, staff in enumerate(staff_list):
            # #
            num_item = SortableTableWidgetItem(str(row + 1))
            num_item.setData(Qt.UserRole, row + 1)
            num_item.setData(Qt.UserRole + 1, staff)
            num_item.setTextAlignment(Qt.AlignCenter)
            self.staff_table.setItem(row, 0, num_item)
            
            # 名前
            self.staff_table.setItem(row, 1, QTableWidgetItem(getattr(staff, 'name', 'Unknown')))
            
            # 役職
            role = getattr(staff, 'role', 'Staff')
            if hasattr(role, 'value'):
                role = role.value
            role_item = QTableWidgetItem(str(role))
            role_item.setTextAlignment(Qt.AlignCenter)
            self.staff_table.setItem(row, 2, role_item)
            
            # 年齢
            age = getattr(staff, 'age', 50)
            age_item = SortableTableWidgetItem(str(age))
            age_item.setData(Qt.UserRole, age)
            age_item.setTextAlignment(Qt.AlignCenter)
            self.staff_table.setItem(row, 3, age_item)
            
            # 能力
            ability = getattr(staff, 'ability', 50)
            ability_item = SortableTableWidgetItem(str(ability))
            ability_item.setData(Qt.UserRole, ability)
            ability_item.setTextAlignment(Qt.AlignCenter)
            self.staff_table.setItem(row, 4, ability_item)
            
            # 経験年数
            years = getattr(staff, 'years_in_role', 1)
            years_item = SortableTableWidgetItem(f"{years}年")
            years_item.setData(Qt.UserRole, years)
            years_item.setTextAlignment(Qt.AlignCenter)
            self.staff_table.setItem(row, 5, years_item)
            
            # 年俸
            salary = getattr(staff, 'salary', 30000000)
            new_salary = getattr(staff, 'new_salary', salary)
            
            cur_item = SortableTableWidgetItem(format_salary(salary))
            cur_item.setData(Qt.UserRole, salary)
            cur_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.staff_table.setItem(row, 6, cur_item)
            
            des_item = SortableTableWidgetItem(format_salary(salary))
            des_item.setData(Qt.UserRole, salary)
            des_item.setForeground(QColor(self.theme.accent_blue))
            des_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.staff_table.setItem(row, 7, des_item)
            
            off_item = SortableTableWidgetItem(format_salary(new_salary))
            off_item.setData(Qt.UserRole, new_salary)
            off_item.setForeground(QColor(self.theme.success))
            off_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.staff_table.setItem(row, 8, off_item)
        
        self.staff_table.setSortingEnabled(True)
    
    def _update_progress(self):
        if not self.current_team:
            return
        total = len(self.current_team.players)
        self.progress_label.setText(f"{total}/{total}")
    
    # === イベントハンドラ ===
    
    def _on_table_selection(self, table):
        selected = table.selectedItems()
        if not selected:
            self.selected_player = None
            self._enable_buttons(False)
            return
        
        row = selected[0].row()
        item = table.item(row, 0)
        if item:
            player = item.data(Qt.UserRole + 1)
            if player:
                self.selected_player = player
                self._update_info_panel(player)
                self._update_stats_panel(player)
                self._enable_buttons(True)
    
    def _on_staff_selection(self, table):
        selected = table.selectedItems()
        if not selected:
            self._enable_buttons(False)
            return
        self._enable_buttons(True)
    
    def _on_table_double_click(self, table, row):
        item = table.item(row, 0)
        if item:
            player = item.data(Qt.UserRole + 1)
            if player:
                self.show_player_detail_requested.emit(player)
    
    def _update_info_panel(self, player):
        while self.info_panel.content_layout.count():
            item = self.info_panel.content_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
        
        self.info_panel.add_row("名前", player.name)
        self.info_panel.add_row("背番号", str(player.uniform_number))
        pos = player.position.value if hasattr(player.position, 'value') else str(player.position)
        self.info_panel.add_row("ポジション", pos)
        self.info_panel.add_row("年齢", f"{player.age}歳")
        self.info_panel.add_row("プロ年数", f"{getattr(player, 'years_pro', 1)}年目")
        ovr = getattr(player, 'overall_rating', 50)
        self.info_panel.add_row("総合力", ovr_to_stars(ovr))
    
    def _update_stats_panel(self, player):
        while self.stats_panel.content_layout.count():
            item = self.stats_panel.content_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    sub = item.layout().takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
        
        record = player.record if hasattr(player, 'record') else None
        is_pitcher = player.position.value == "投手"
        
        if record:
            if is_pitcher:
                self.stats_panel.add_row("登板", str(record.games_pitched))
                self.stats_panel.add_row("勝敗", f"{record.wins}勝{record.losses}敗")
                self.stats_panel.add_row("セーブ", str(record.saves))
                era = record.era if record.innings_pitched > 0 else 0
                self.stats_panel.add_row("防御率", f"{era:.2f}")
            else:
                avg = record.batting_average if record.at_bats > 0 else 0
                self.stats_panel.add_row("打率", f".{int(avg * 1000):03d}")
                self.stats_panel.add_row("本塁打", str(record.home_runs))
                self.stats_panel.add_row("打点", str(record.rbis))
                self.stats_panel.add_row("盗塁", str(record.stolen_bases))
        else:
            self.stats_panel.add_row("成績", "データなし")
    
    def _enable_buttons(self, enabled):
        self.negotiate_btn.setEnabled(enabled)
        self.retire_btn.setEnabled(enabled)
        self.staff_convert_btn.setEnabled(enabled)
        self.release_btn.setEnabled(enabled)
    
    def _on_negotiate(self):
        if not self.selected_player:
            return
        
        budget = getattr(self.current_team, 'budget', 5000000000) if self.current_team else 5000000000
        dialog = ContractNegotiationDialog(self.selected_player, budget, self)
        
        if dialog.exec() == QDialog.Accepted:
            years, salary = dialog.get_contract()
            player = self.selected_player
            desired = getattr(player, 'desired_salary', 10000000)
            
            # 複数年プレミアム計算
            premium = self._calculate_multiyear_premium(player, years)
            adjusted_desired = int(desired * (1 + premium))
            
            # 交渉成功率計算
            success_rate = self._calculate_negotiation_success(salary, adjusted_desired)
            
            if success_rate <= 0:
                QMessageBox.warning(self, "交渉決裂", 
                    f"{player.name}は提示年俸が低すぎると拒否しました。\n"
                    f"希望年俸の75%以上を提示してください。\n"
                    f"希望: {format_salary(adjusted_desired)} ({years}年契約時)")
                return
            
            # 成功判定
            import random
            if random.random() * 100 < success_rate:
                player.new_salary = salary
                player.contract_years = years
                self._refresh_player_lists()
                self._update_budget_display()
                self._update_info_panel(player)
                self.status_label.setText(f"契約合意: {player.name} → {years}年×{format_salary(salary)}")
            else:
                QMessageBox.information(self, "交渉継続", 
                    f"{player.name}との交渉は継続します。\n成功率: {success_rate:.0f}%")
    
    def _calculate_negotiation_success(self, offered: int, desired: int) -> float:
        """交渉成功率を計算（75%未満は0%）"""
        if desired <= 0:
            return 100.0
        
        ratio = offered / desired
        
        if ratio < 0.75:
            return 0.0  # 75%未満は交渉不成立
        elif ratio >= 1.0:
            return 100.0  # 希望以上は100%
        else:
            # 75%-100%で線形に0-90%
            return (ratio - 0.75) / 0.25 * 90.0
    
    def _on_retire(self):
        if not self.selected_player:
            return
        
        player = self.selected_player
        reply = QMessageBox.question(self, "引退打診", f"{player.name}に引退を打診しますか？\n\n年齢: {player.age}歳", QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            import random
            accept_chance = 0.3 + (player.age - 30) * 0.05
            if random.random() < accept_chance:
                self.status_label.setText(f"{player.name}は引退を受諾しました")
                setattr(player, 'retiring', True)
            else:
                self.status_label.setText(f"{player.name}は現役続行を希望しています")
    
    def _on_staff_convert(self):
        if not self.selected_player:
            return
        
        from PySide6.QtWidgets import QInputDialog
        roles = ["打撃コーチ", "投手コーチ", "守備走塁コーチ", "スカウト"]
        role, ok = QInputDialog.getItem(self, "スタッフ転身", f"{self.selected_player.name}の転身先:", roles, 0, False)
        
        if ok:
            setattr(self.selected_player, 'converting_to_staff', True)
            setattr(self.selected_player, 'staff_role', role)
            self.status_label.setText(f"{self.selected_player.name} → {role}に転身予定")
    
    def _on_release(self):
        if not self.selected_player:
            return
        
        reply = QMessageBox.warning(self, "自由契約", f"{self.selected_player.name}を自由契約にしますか？", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            setattr(self.selected_player, 'released', True)
            self.status_label.setText(f"自由契約: {self.selected_player.name}")
    
    def _on_complete(self):
        reply = QMessageBox.question(self, "契約更改完了", "契約更改を完了しますか？", QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if self.current_team:
                for player in self.current_team.players:
                    new_sal = getattr(player, 'new_salary', getattr(player, 'salary', 10000000))
                    player.salary = new_sal
            self.completed.emit()
