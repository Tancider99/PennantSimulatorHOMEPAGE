# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Contracts Management Page
Includes Draft Scouting, Foreign Player Scouting, and Trade management.
Full implementation with staff dispatch, scouting progress, and trade system.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QSplitter,
    QStackedWidget, QPushButton, QLabel, QSizePolicy, QGridLayout,
    QScrollArea, QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QComboBox, QMessageBox, QProgressBar, QSpinBox,
    QStyledItemDelegate, QStyle, QDialog
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QBrush, QPen, QPainter

import sys
import os
import random
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from UI.theme import get_theme, Theme
from UI.widgets.tables import SortableTableWidgetItem, RatingDelegate

# modelsやplayer_generatorのインポート
try:
    from models import Position, PitchType, PlayerStats, Player, Team
    import player_generator
except ImportError:
    pass

THEME = get_theme()

# ========================================
# Data Models for Contracts System
# ========================================

class ScoutingStatus(Enum):
    NOT_STARTED = "未調査"
    IN_PROGRESS = "調査中"
    COMPLETED = "調査完了"


@dataclass
class Scout:
    """スカウトスタッフ"""
    name: str
    skill: int = 50  # 1-99: 調査能力
    specialty: str = "汎用"  # 野手/投手/汎用
    is_available: bool = True
    current_mission_id: Optional[int] = None

    @property
    def daily_progress(self) -> float:
        """1日あたりの調査進捗率 (%)"""
        # 5%前後になるように調整 (スキル50で5%)
        # スキル範囲1-99 -> 2.0% ~ 8.0% 程度
        return 2.0 + (self.skill * 0.06)


@dataclass
class DraftProspect:
    """ドラフト候補選手 (UI表示用拡張)"""
    id: int
    name: str
    position: Position
    pitch_type: Optional[PitchType] = None
    age: int = 18
    school: str = "" # 出身・所属

    # 実能力 (調査が完了するまで完全に見えない)
    true_stats: PlayerStats = field(default_factory=PlayerStats)
    true_potential: int = 50  # 潜在能力: 1-99

    # 調査状態
    scout_level: float = 0.0  # 0-100%
    scouting_status: ScoutingStatus = ScoutingStatus.NOT_STARTED
    assigned_scout: Optional[Scout] = None

    # 推定値キャッシュ (リストと詳細で値を一致させるため)
    _cached_visible_stats: Dict[str, int] = field(default_factory=dict)
    
    # 推定総合力の範囲 (min, max)
    _cached_est_overall_range: tuple = (0, 0)
    
    # 推定潜在能力の範囲 (minランク, maxランク) - 数値で保持して表示時に変換
    _cached_est_potential_range: tuple = (0, 0)

    def __post_init__(self):
        """初期化時に推定値を計算"""
        self.recalculate_estimates()

    def recalculate_estimates(self):
        """調査度に基づいて推定値を再計算しキャッシュする"""
        # 調査度に応じた誤差範囲を決定
        uncertainty = 1.0 - (self.scout_level / 100.0)
        
        # 1. 個別ステータスの推定値決定（詳細画面用）
        noise_max = int(20 * uncertainty)
        
        if self.position == Position.PITCHER:
            stats_list = ['stuff', 'control', 'stamina', 'velocity', 'movement']
        else:
            stats_list = ['contact', 'power', 'speed', 'arm', 'fielding']

        new_stats = {}
        for stat in stats_list:
            if stat == 'fielding':
                true_val = self.true_stats.fielding
            else:
                true_val = getattr(self.true_stats, stat, 50)

            noise = random.randint(-noise_max, noise_max)
            if stat == 'velocity':
                est_val = max(120, min(170, true_val + noise))
            else:
                est_val = max(1, min(99, true_val + noise))
            new_stats[stat] = est_val

        self._cached_visible_stats = new_stats

        # 2. 推定総合力の範囲決定 (一覧画面用)
        if self.position == Position.PITCHER:
            true_overall = self.true_stats.stuff + self.true_stats.control + self.true_stats.stamina
        else:
            true_overall = (self.true_stats.contact + self.true_stats.power + 
                           self.true_stats.speed + self.true_stats.arm + self.true_stats.fielding)
        
        range_half_width = int(40 * uncertainty)
        min_ovr = max(0, true_overall - random.randint(0, range_half_width))
        max_ovr = true_overall + random.randint(0, range_half_width)
        
        if range_half_width > 10 and (max_ovr - min_ovr) < 20:
             max_ovr += 20
             min_ovr = max(0, min_ovr - 10)

        self._cached_est_overall_range = (min_ovr, max_ovr)

        # 3. 推定潜在能力の範囲決定
        true_pot = self.true_potential
        pot_uncertainty = max(0.2, uncertainty) 
        pot_width = int(12 * pot_uncertainty) 
        min_pot = max(1, true_pot - random.randint(0, pot_width))
        max_pot = min(99, true_pot + random.randint(0, pot_width))
        
        self._cached_est_potential_range = (min_pot, max_pot)

    def get_visible_stats(self) -> Dict[str, int]:
        """キャッシュされた可視能力値を返す"""
        return self._cached_visible_stats

    def get_overall_display(self) -> str:
        """推定総合力の表示文字列"""
        min_v, max_v = self._cached_est_overall_range
        if min_v == max_v:
            return f"★{min_v}"
        return f"★{min_v}～★{max_v}"
    
    def get_potential_display(self) -> str:
        """推定潜在能力の表示文字列"""
        min_v, max_v = self._cached_est_potential_range
        min_rank = self._value_to_rank(min_v)
        max_rank = self._value_to_rank(max_v)
        if min_rank == max_rank:
            return min_rank
        return f"{min_rank}～{max_rank}"

    def get_max_estimated_overall(self) -> int:
        return self._cached_est_overall_range[1]
    
    def get_max_estimated_potential(self) -> int:
        return self._cached_est_potential_range[1]

    @staticmethod
    def _value_to_rank(value: int) -> str:
        if value >= 90: return "S"
        elif value >= 80: return "A"
        elif value >= 70: return "B"
        elif value >= 60: return "C"
        elif value >= 50: return "D"
        elif value >= 40: return "E"
        elif value >= 30: return "F"
        else: return "G"
        
    @property
    def position_order(self) -> int:
        order = {
            Position.PITCHER: 1, Position.CATCHER: 2, Position.FIRST: 3,
            Position.SECOND: 4, Position.THIRD: 5, Position.SHORTSTOP: 6,
            Position.LEFT: 7, Position.CENTER: 8, Position.RIGHT: 9, Position.DH: 10
        }
        return order.get(self.position, 99)


@dataclass
class ForeignPlayerCandidate:
    """外国人選手候補 (UI表示用拡張)"""
    id: int
    name: str
    position: Position
    pitch_type: Optional[PitchType] = None
    age: int = 28
    country: str = "USA"

    # 実能力
    true_stats: PlayerStats = field(default_factory=PlayerStats)
    true_potential: int = 50  # 潜在能力
    salary_demand: int = 100000000  # 年俸要求額
    bonus_demand: int = 50000000 # 契約金要求額
    years_demand: int = 2  # 契約年数要求

    # 調査状態
    scout_level: float = 0.0
    scouting_status: ScoutingStatus = ScoutingStatus.NOT_STARTED
    assigned_scout: Optional[Scout] = None

    # 交渉状態
    negotiation_started: bool = False
    negotiation_progress: int = 0  # 0-100
    interest_level: int = 50  # 興味度: 0-100

    # 推定値キャッシュ
    _cached_visible_stats: Dict[str, int] = field(default_factory=dict)
    _cached_est_overall_range: tuple = (0, 0)
    _cached_est_potential_range: tuple = (0, 0)

    def __post_init__(self):
        """初期化時に推定値を計算"""
        self.recalculate_estimates()

    def recalculate_estimates(self):
        """調査度に基づいて推定値を再計算しキャッシュする"""
        uncertainty = 1.0 - (self.scout_level / 100.0)
        
        # 外国人は情報が少ないのでブレ幅を大きくする
        noise_max = int(30 * uncertainty)

        if self.position == Position.PITCHER:
            stats_list = ['stuff', 'control', 'stamina', 'velocity', 'movement']
        else:
            stats_list = ['contact', 'power', 'speed', 'arm', 'fielding']

        new_stats = {}
        for stat in stats_list:
            if stat == 'fielding':
                true_val = self.true_stats.fielding
            else:
                true_val = getattr(self.true_stats, stat, 50)

            noise = random.randint(-noise_max, noise_max)
            if stat == 'velocity':
                est_val = max(120, min(170, true_val + noise))
            else:
                est_val = max(1, min(99, true_val + noise))
            new_stats[stat] = est_val

        self._cached_visible_stats = new_stats

        # 総合力の推定 (ブレ幅大)
        if self.position == Position.PITCHER:
            true_overall = self.true_stats.stuff + self.true_stats.control + self.true_stats.stamina
        else:
            true_overall = (self.true_stats.contact + self.true_stats.power + 
                           self.true_stats.speed + self.true_stats.arm + self.true_stats.fielding)
        
        # 範囲を大きく
        range_half_width = int(60 * uncertainty)
        min_ovr = max(0, true_overall - random.randint(0, range_half_width))
        max_ovr = true_overall + random.randint(0, range_half_width)
        
        if range_half_width > 10 and (max_ovr - min_ovr) < 30:
             max_ovr += 30
             min_ovr = max(0, min_ovr - 20)

        self._cached_est_overall_range = (min_ovr, max_ovr)

        # 潜在能力の推定 (ブレ幅大)
        true_pot = self.true_potential
        pot_uncertainty = max(0.3, uncertainty)
        pot_width = int(20 * pot_uncertainty)
        
        min_pot = max(1, true_pot - random.randint(0, pot_width))
        max_pot = min(99, true_pot + random.randint(0, pot_width))
        
        self._cached_est_potential_range = (min_pot, max_pot)

    def get_visible_stats(self) -> Dict[str, int]:
        return self._cached_visible_stats

    def get_overall_display(self) -> str:
        min_v, max_v = self._cached_est_overall_range
        if min_v == max_v:
            return f"★{min_v}"
        return f"★{min_v}～★{max_v}"
    
    def get_potential_display(self) -> str:
        min_v, max_v = self._cached_est_potential_range
        min_rank = self._value_to_rank(min_v)
        max_rank = self._value_to_rank(max_v)
        if min_rank == max_rank:
            return min_rank
        return f"{min_rank}～{max_rank}"

    def get_max_estimated_overall(self) -> int:
        return self._cached_est_overall_range[1]
    
    def get_max_estimated_potential(self) -> int:
        return self._cached_est_potential_range[1]
    
    def get_total_cost(self) -> int:
        return self.salary_demand + self.bonus_demand
    
    def get_total_cost_display(self) -> str:
        total = self.get_total_cost() // 1000000 # 百万円単位
        return f"{total}百万"

    @staticmethod
    def _value_to_rank(value: int) -> str:
        if value >= 90: return "S"
        elif value >= 80: return "A"
        elif value >= 70: return "B"
        elif value >= 60: return "C"
        elif value >= 50: return "D"
        elif value >= 40: return "E"
        elif value >= 30: return "F"
        else: return "G"

    @property
    def position_order(self) -> int:
        order = {
            Position.PITCHER: 1, Position.CATCHER: 2, Position.FIRST: 3,
            Position.SECOND: 4, Position.THIRD: 5, Position.SHORTSTOP: 6,
            Position.LEFT: 7, Position.CENTER: 8, Position.RIGHT: 9, Position.DH: 10
        }
        return order.get(self.position, 99)


@dataclass
class TradeOffer:
    """トレード提案"""
    id: int
    offering_team: str
    receiving_team: str
    offered_player_ids: List[int] = field(default_factory=list)
    requested_player_ids: List[int] = field(default_factory=list)
    status: str = "提案中"  # 提案中/成立/拒否
    evaluation_score: float = 0.0  # 相手チームの評価スコア


# ========================================
# Negotiation Dialog
# ========================================

class ForeignNegotiationDialog(QDialog):
    """外国人選手との契約交渉ダイアログ"""
    def __init__(self, parent, candidate: ForeignPlayerCandidate, theme):
        super().__init__(parent)
        self.candidate = candidate
        self.theme = theme
        self.setWindowTitle("契約交渉")
        self.setFixedSize(500, 450)  # Increased size for text visibility
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {self.theme.bg_card}; color: {self.theme.text_primary}; }}
            QLabel {{ color: {self.theme.text_primary}; }}
        """)
        
        self.offered_salary = 0
        self.offered_years = 0
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)  # Reduced spacing
        
        # ヘッダー情報
        info_frame = QFrame()
        info_frame.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-radius: 4px; padding: 10px;")
        info_layout = QVBoxLayout(info_frame)
        
        name_lbl = QLabel(f"{self.candidate.name}")
        name_lbl.setStyleSheet("font-size: 18px; font-weight: bold;")
        info_layout.addWidget(name_lbl)
        
        detail_lbl = QLabel(f"{short_pos_name(self.candidate.position)} / {self.candidate.age}歳 / {self.candidate.country}")
        detail_lbl.setStyleSheet(f"color: {self.theme.text_secondary};")
        info_layout.addWidget(detail_lbl)
        
        layout.addWidget(info_frame)
        
        # 要求条件
        demand_lbl = QLabel("【要求条件】")
        demand_lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(demand_lbl)
        
        demand_grid = QGridLayout()
        demand_grid.addWidget(QLabel("希望年俸:"), 0, 0)
        demand_grid.addWidget(QLabel(f"{self.candidate.salary_demand // 1000000} 百万円"), 0, 1)
        demand_grid.addWidget(QLabel("契約金:"), 1, 0)
        demand_grid.addWidget(QLabel(f"{self.candidate.bonus_demand // 1000000} 百万円"), 1, 1)
        demand_grid.addWidget(QLabel("希望年数:"), 2, 0)
        demand_grid.addWidget(QLabel(f"{self.candidate.years_demand} 年"), 2, 1)
        layout.addLayout(demand_grid)
        
        layout.addSpacing(10)
        
        # 提示条件入力
        offer_lbl = QLabel("【提示条件】")
        offer_lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(offer_lbl)
        
        offer_grid = QGridLayout()
        offer_grid.setSpacing(8)
        
        offer_grid.addWidget(QLabel("提示年俸:"), 0, 0)
        self.salary_input = QLineEdit()
        self.salary_input.setText(str(self.candidate.salary_demand // 1000000))
        self.salary_input.setFixedWidth(100)
        self.salary_input.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 6px;")
        offer_grid.addWidget(self.salary_input, 0, 1)
        offer_grid.addWidget(QLabel("百万円"), 0, 2)
        
        offer_grid.addWidget(QLabel("提示年数:"), 1, 0)
        self.years_input = QLineEdit()
        self.years_input.setText(str(self.candidate.years_demand))
        self.years_input.setFixedWidth(60)
        self.years_input.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 6px;")
        offer_grid.addWidget(self.years_input, 1, 1)
        offer_grid.addWidget(QLabel("年 (最大15年)"), 1, 2)
        
        layout.addLayout(offer_grid)
        
        layout.addStretch()
        
        # ボタン
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.setStyleSheet(f"""
            background-color: {self.theme.bg_hover}; color: {self.theme.text_primary};
            border: 1px solid {self.theme.border}; border-radius: 4px; padding: 8px;
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        offer_btn = QPushButton("提示する")
        offer_btn.setStyleSheet(f"""
            background-color: {self.theme.accent_blue}; color: white;
            border: none; border-radius: 4px; padding: 8px; font-weight: bold;
        """)
        offer_btn.clicked.connect(self.accept)
        btn_layout.addWidget(offer_btn)
        
        layout.addLayout(btn_layout)

    def get_values(self):
        try:
            salary = int(self.salary_input.text())
        except:
            salary = 10
        try:
            years = min(15, max(1, int(self.years_input.text())))  # Clamp to 1-15
        except:
            years = 1
        return salary, years


# ========================================
# Custom Table Widget (Order Page Style)
# ========================================

class ContractsTableWidget(QTableWidget):
    """オーダーページ風のテーブルウィジェット"""

    row_double_clicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self._setup_style()
        self.itemDoubleClicked.connect(self._on_double_click)

    def _setup_style(self):
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.horizontalHeader().setStretchLastSection(True)

        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                gridline-color: {self.theme.border_muted};
                selection-background-color: #ffffff;
                selection-color: #000000;
                outline: none;
            }}
            QTableWidget::item:selected {{
                background-color: #ffffff;
                color: #000000;
                border: none;
                outline: none;
            }}
            QTableWidget::item:focus {{
                background-color: #ffffff;
                border: none;
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
            QHeaderView::section:hover {{
                background-color: {self.theme.bg_hover};
            }}
            QTableWidget::item {{
                padding: 2px;
                border-bottom: 1px solid {self.theme.border_muted};
            }}
        """)

    def _on_double_click(self, item):
        self.row_double_clicked.emit(item.row())


# ========================================
# Helper Functions
# ========================================

def create_rank_item(value: int, show_value: bool = False) -> QTableWidgetItem:
    """ランク表示用アイテムを作成"""
    item = SortableTableWidgetItem()
    if value > 0:
        item.setData(Qt.UserRole, value)
        item.setData(Qt.DisplayRole, "")
    else:
        item.setText("?")
        item.setForeground(QColor(THEME.text_muted))
    item.setTextAlignment(Qt.AlignCenter)
    return item


def create_text_item(text: str, align=Qt.AlignCenter, color=None) -> QTableWidgetItem:
    """テキストアイテムを作成"""
    item = SortableTableWidgetItem()
    item.setText(str(text))
    item.setTextAlignment(align)
    if color:
        item.setForeground(QColor(color))
    return item


def create_progress_item(value: float) -> QTableWidgetItem:
    """進捗表示用アイテム"""
    item = SortableTableWidgetItem()
    item.setText(f"{value:.0f}%")
    item.setData(Qt.UserRole, value)
    item.setTextAlignment(Qt.AlignCenter)

    if value >= 80:
        item.setForeground(QColor(THEME.success))
    elif value >= 50:
        item.setForeground(QColor(THEME.warning))
    elif value > 0:
        item.setForeground(QColor(THEME.accent_orange))
    else:
        item.setForeground(QColor(THEME.text_muted))

    return item


def create_status_item(status: ScoutingStatus) -> QTableWidgetItem:
    """ステータス表示用アイテム"""
    item = SortableTableWidgetItem()
    item.setText(status.value)
    item.setTextAlignment(Qt.AlignCenter)

    if status == ScoutingStatus.COMPLETED:
        item.setForeground(QColor(THEME.success))
    elif status == ScoutingStatus.IN_PROGRESS:
        item.setForeground(QColor(THEME.accent_blue))
    else:
        item.setForeground(QColor(THEME.text_muted))

    return item


def get_rank_color(rank_str: str) -> QColor:
    """ランク文字（範囲含む）から色を決定"""
    if "~" in rank_str:
        ranks = rank_str.split("~")
        target = ranks[1] if len(ranks) > 1 else ranks[0]
    else:
        target = rank_str
        
    colors = {
        'S': QColor(THEME.rating_s),
        'A': QColor(THEME.rating_a),
        'B': QColor(THEME.rating_b),
        'C': QColor(THEME.rating_c),
        'D': QColor(THEME.rating_d),
        'E': QColor(THEME.rating_e),
        'F': QColor(THEME.rating_f),
        'G': QColor(THEME.rating_g),
        '?': QColor(THEME.text_muted),
    }
    return colors.get(target.strip().upper(), QColor(THEME.text_muted))


def short_pos_name(pos: Position) -> str:
    """ポジションの短縮名"""
    mapping = {
        Position.PITCHER: "投",
        Position.CATCHER: "捕",
        Position.FIRST: "一",
        Position.SECOND: "二",
        Position.THIRD: "三",
        Position.SHORTSTOP: "遊",
        Position.LEFT: "左",
        Position.CENTER: "中",
        Position.RIGHT: "右",
        Position.DH: "DH"
    }
    return mapping.get(pos, "?")


# ========================================
# 1. Draft Scouting Page
# ========================================

class DraftScoutingPage(QWidget):
    """ドラフト候補調査ページ"""

    prospect_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.prospects: List[DraftProspect] = []
        self.scouts: List[Scout] = []
        self.selected_prospect: Optional[DraftProspect] = None

        self._generate_dummy_data()
        self._setup_ui()

    def _generate_dummy_data(self):
        """データ生成 (300人)"""
        # スカウト生成
        scout_names = ["田中 誠", "山本 健一", "鈴木 太郎", "佐藤 次郎", "高橋 三郎"]
        specialties = ["野手", "投手", "汎用", "野手", "投手"]
        for i, (name, spec) in enumerate(zip(scout_names, specialties)):
            self.scouts.append(Scout(
                name=name,
                skill=random.randint(40, 80),
                specialty=spec
            ))

        # 学校名・チーム名パーツ
        univ_names = ["明帝", "東都", "六大学", "関西", "北海", "九州", "国際"]
        hs_names = ["大阪", "横浜", "仙台", "広島", "智辯", "浦和", "星稜"]
        indep_names = ["四国", "BC", "九州", "関西", "北海道"]
        social_names = ["自動車", "製鉄", "ガス", "通運", "生命"]

        positions = [Position.PITCHER, Position.CATCHER, Position.SHORTSTOP,
                    Position.SECOND, Position.CENTER, Position.FIRST,
                    Position.THIRD, Position.LEFT, Position.RIGHT]

        # 300人に増やす
        for i in range(300):
            pos = random.choice(positions)
            
            # player_generatorを使って能力生成
            gen_prospect = player_generator.create_draft_prospect(pos)
            
            # 学校名の補完
            origin = gen_prospect.origin
            school = ""
            if origin == "高校":
                school = random.choice(hs_names) + random.choice(["高校", "学園", "実業", "桐蔭"])
            elif origin == "大学":
                school = random.choice(univ_names) + random.choice(["大学", "学院"])
            elif origin == "社会人":
                school = random.choice(["日本", "東京", "大阪"]) + random.choice(social_names)
            else:
                school = random.choice(indep_names) + "アイランドリーグ"

            adjusted_potential = int(gen_prospect.potential * 0.8)
            true_potential = max(1, min(99, adjusted_potential))

            prospect = DraftProspect(
                id=i,
                name=gen_prospect.name,
                position=gen_prospect.position,
                pitch_type=gen_prospect.pitch_type,
                age=gen_prospect.age,
                school=school,
                true_stats=gen_prospect.stats,
                true_potential=true_potential
            )
            self.prospects.append(prospect)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ツールバー
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # メインコンテンツ (スプリッター)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {self.theme.border}; width: 1px; }}")

        # 左: 候補リスト
        left_widget = self._create_prospect_list()
        splitter.addWidget(left_widget)

        # 右: 詳細 & スカウト派遣
        right_widget = self._create_detail_panel()
        splitter.addWidget(right_widget)

        splitter.setSizes([650, 350])
        layout.addWidget(splitter)

    def _create_toolbar(self) -> QWidget:
        toolbar = QFrame()
        toolbar.setFixedHeight(50)
        toolbar.setStyleSheet(f"background-color: {self.theme.bg_card}; border-bottom: 1px solid {self.theme.border};")

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(12, 0, 12, 0)

        title = QLabel("ドラフト候補調査")
        title.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; font-size: 16px;")
        layout.addWidget(title)

        # フィルター
        layout.addSpacing(20)

        self.pos_filter = QComboBox()
        self.pos_filter.addItems(["全ポジション", "投手", "捕手", "内野手", "外野手"])
        self.pos_filter.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 4px;")
        self.pos_filter.currentIndexChanged.connect(self._refresh_table)
        layout.addWidget(self.pos_filter)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["全ステータス", "未調査", "調査中", "調査完了"])
        self.status_filter.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 4px;")
        self.status_filter.currentIndexChanged.connect(self._refresh_table)
        layout.addWidget(self.status_filter)

        layout.addStretch()

        # 利用可能スカウト表示
        self.scout_status_label = QLabel()
        self.scout_status_label.setStyleSheet(f"color: {self.theme.text_secondary};")
        layout.addWidget(self.scout_status_label)
        self._update_scout_status()

        return toolbar

    def _create_prospect_list(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QLabel("候補選手リスト (300名)")
        header.setStyleSheet(f"font-weight: bold; color: {self.theme.text_secondary}; font-size: 13px;")
        layout.addWidget(header)

        self.prospect_table = ContractsTableWidget()
        self.rating_delegate = RatingDelegate(self)

        cols = ["名前", "Pos", "年齢", "推定総合", "推定潜在", "調査度", "状態"]
        widths = [140, 40, 40, 100, 80, 60, 70]

        self.prospect_table.setColumnCount(len(cols))
        self.prospect_table.setHorizontalHeaderLabels(cols)
        for i, w in enumerate(widths):
            self.prospect_table.setColumnWidth(i, w)

        self.prospect_table.row_double_clicked.connect(self._on_prospect_selected)
        self.prospect_table.itemClicked.connect(lambda item: self._on_prospect_clicked(item.row()))

        layout.addWidget(self.prospect_table)

        self._refresh_table()
        return widget

    def _create_detail_panel(self) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet(f"background-color: {self.theme.bg_card};")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 選手詳細ヘッダー
        self.detail_header = QLabel("選手を選択してください")
        self.detail_header.setStyleSheet(f"color: {self.theme.text_primary}; font-size: 16px; font-weight: bold;")
        self.detail_header.setWordWrap(True)
        layout.addWidget(self.detail_header)

        # 能力詳細フレーム
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-radius: 4px; padding: 10px;")
        
        self.stats_layout = QGridLayout(self.stats_frame)
        self.stats_layout.setSpacing(8)

        layout.addWidget(self.stats_frame)

        # 潜在能力表示
        potential_frame = QFrame()
        potential_frame.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-radius: 4px; padding: 10px;")
        potential_layout = QHBoxLayout(potential_frame)

        potential_layout.addWidget(QLabel("推定潜在能力:"))
        self.potential_label = QLabel("?")
        self.potential_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; font-size: 18px;")
        potential_layout.addWidget(self.potential_label)
        potential_layout.addStretch()

        layout.addWidget(potential_frame)

        # 調査進捗
        progress_frame = QFrame()
        progress_frame.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-radius: 4px; padding: 10px;")
        progress_layout = QVBoxLayout(progress_frame)

        progress_layout.addWidget(QLabel("調査進捗"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.theme.bg_input};
                border: 1px solid {self.theme.border};
                border-radius: 2px;
                text-align: center;
                color: {self.theme.text_primary};
            }}
            QProgressBar::chunk {{
                background-color: {self.theme.accent_blue};
            }}
        """)
        progress_layout.addWidget(self.progress_bar)

        # スカウト派遣セクション
        scout_frame = QFrame()
        scout_frame.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-radius: 4px; padding: 10px;")
        scout_layout = QVBoxLayout(scout_frame)

        scout_layout.addWidget(QLabel("スカウト派遣"))

        self.scout_combo = QComboBox()
        self.scout_combo.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 4px;")
        self._update_scout_combo()
        scout_layout.addWidget(self.scout_combo)

        btn_layout = QHBoxLayout()

        self.dispatch_btn = QPushButton("スカウト派遣")
        self.dispatch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.accent_blue};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent_blue_hover};
            }}
            QPushButton:disabled {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_muted};
            }}
        """)
        self.dispatch_btn.clicked.connect(self._dispatch_scout)
        self.dispatch_btn.setEnabled(False)
        btn_layout.addWidget(self.dispatch_btn)

        self.recall_btn = QPushButton("スカウト帰還")
        self.recall_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.accent_orange};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent_orange_hover};
            }}
            QPushButton:disabled {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_muted};
            }}
        """)
        self.recall_btn.clicked.connect(self._recall_scout)
        self.recall_btn.setEnabled(False)
        btn_layout.addWidget(self.recall_btn)

        scout_layout.addLayout(btn_layout)
        layout.addWidget(scout_frame)

        layout.addStretch()
        return widget

    def _refresh_table(self):
        """テーブルを更新"""
        filtered = self.prospects.copy()

        pos_filter = self.pos_filter.currentText()
        if pos_filter == "投手":
            filtered = [p for p in filtered if p.position == Position.PITCHER]
        elif pos_filter == "捕手":
            filtered = [p for p in filtered if p.position == Position.CATCHER]
        elif pos_filter == "内野手":
            filtered = [p for p in filtered if p.position in [Position.FIRST, Position.SECOND, Position.THIRD, Position.SHORTSTOP]]
        elif pos_filter == "外野手":
            filtered = [p for p in filtered if p.position in [Position.LEFT, Position.CENTER, Position.RIGHT]]

        status_filter = self.status_filter.currentText()
        if status_filter == "未調査":
            filtered = [p for p in filtered if p.scouting_status == ScoutingStatus.NOT_STARTED]
        elif status_filter == "調査中":
            filtered = [p for p in filtered if p.scouting_status == ScoutingStatus.IN_PROGRESS]
        elif status_filter == "調査完了":
            filtered = [p for p in filtered if p.scouting_status == ScoutingStatus.COMPLETED]

        # ソート: ポジション順 -> 年齢順 -> 推定総合力の範囲の最大値順(降順)
        filtered.sort(key=lambda p: (p.position_order, p.age, -p.get_max_estimated_overall()))

        self.prospect_table.setRowCount(len(filtered))

        for row, prospect in enumerate(filtered):
            name_item = create_text_item(prospect.name, Qt.AlignLeft | Qt.AlignVCenter)
            name_item.setData(Qt.UserRole, prospect)
            self.prospect_table.setItem(row, 0, name_item)

            pos_item = create_text_item(short_pos_name(prospect.position))
            self.prospect_table.setItem(row, 1, pos_item)

            age_item = create_text_item(str(prospect.age))
            self.prospect_table.setItem(row, 2, age_item)

            ovr_text = prospect.get_overall_display()
            rank_item = create_text_item(ovr_text)
            
            max_ovr = prospect.get_max_estimated_overall()
            if max_ovr >= 240: rank_item.setForeground(QColor(THEME.rating_s))
            elif max_ovr >= 220: rank_item.setForeground(QColor(THEME.rating_a))
            elif max_ovr >= 200: rank_item.setForeground(QColor(THEME.rating_b))
            elif max_ovr >= 180: rank_item.setForeground(QColor(THEME.text_primary))
            else: rank_item.setForeground(QColor(THEME.text_muted))
            
            font = rank_item.font()
            font.setBold(True)
            rank_item.setFont(font)
            self.prospect_table.setItem(row, 3, rank_item)

            pot_text = prospect.get_potential_display()
            pot_item = create_text_item(pot_text)
            pot_item.setForeground(get_rank_color(pot_text))
            font = pot_item.font()
            font.setBold(True)
            pot_item.setFont(font)
            self.prospect_table.setItem(row, 4, pot_item)

            progress_item = create_progress_item(prospect.scout_level)
            self.prospect_table.setItem(row, 5, progress_item)

            status_item = create_status_item(prospect.scouting_status)
            self.prospect_table.setItem(row, 6, status_item)

    def _on_prospect_clicked(self, row: int):
        item = self.prospect_table.item(row, 0)
        if item:
            prospect = item.data(Qt.UserRole)
            if prospect:
                self.selected_prospect = prospect
                self._update_detail_panel()

    def _on_prospect_selected(self, row: int):
        self._on_prospect_clicked(row)

    def _update_detail_panel(self):
        p = self.selected_prospect
        if not p:
            return

        try:
            self.detail_header.setText(f"{p.name} ({short_pos_name(p.position)}) - {p.school}")

            while self.stats_layout.count():
                item = self.stats_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            visible = p.get_visible_stats()

            if p.position == Position.PITCHER:
                items = [
                    ("球速", "velocity"), ("球威", "stuff"), ("制球", "control"),
                    ("スタミナ", "stamina"), ("変化球", "movement")
                ]
            else:
                items = [
                    ("ミート", "contact"), ("パワー", "power"), ("走力", "speed"),
                    ("肩力", "arm"), ("守備", "fielding")
                ]

            for i, (name, key) in enumerate(items):
                row, col = i // 3, (i % 3) * 2
                
                label = QLabel(name)
                label.setStyleSheet(f"color: {self.theme.text_secondary};")
                self.stats_layout.addWidget(label, row, col)

                val = visible.get(key, -1)
                value_label = QLabel("?")
                value_label.setStyleSheet(f"color: {self.theme.text_muted}; font-weight: bold;")
                
                if val > 0:
                    if key == "velocity":
                        value_label.setText(f"{val}km/h")
                        value_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold;")
                    else:
                        rank = Theme.get_rating_rank(val)
                        value_label.setText(f"{rank} ({val})")
                        value_label.setStyleSheet(f"color: {Theme.get_rating_color(val)}; font-weight: bold;")
                
                self.stats_layout.addWidget(value_label, row, col + 1)

            pot_text = p.get_potential_display()
            self.potential_label.setText(pot_text)
            self.potential_label.setStyleSheet(f"color: {get_rank_color(pot_text).name()}; font-weight: bold; font-size: 18px;")

            # Check enable conditions FIRST (before widgets that might fail)
            can_dispatch = (
                p.scouting_status != ScoutingStatus.IN_PROGRESS and
                p.scout_level < 100 and
                any(s.is_available for s in self.scouts)
            )
            
            # Enable buttons (these should work)
            try:
                self.dispatch_btn.setEnabled(can_dispatch)
                self.recall_btn.setEnabled(p.scouting_status == ScoutingStatus.IN_PROGRESS)
            except RuntimeError:
                pass  # Buttons deleted
            
            # Progress bar (might be deleted)
            try:
                self.progress_bar.setValue(int(p.scout_level))
            except RuntimeError:
                pass  # Progress bar deleted
                
        except RuntimeError as e:
            print(f"[ERROR] _update_detail_panel RuntimeError: {e}")

    def _update_scout_combo(self):
        self.scout_combo.clear()
        for scout in self.scouts:
            status = "空き" if scout.is_available else "派遣中"
            self.scout_combo.addItem(f"{scout.name} (能力:{scout.skill} / {scout.specialty}) [{status}]", scout)

    def _update_scout_status(self):
        available = sum(1 for s in self.scouts if s.is_available)
        total = len(self.scouts)
        self.scout_status_label.setText(f"スカウト: {available}/{total} 空き")

    def _dispatch_scout(self):
        if not self.selected_prospect:
            return

        scout_data = self.scout_combo.currentData()
        if not scout_data or not scout_data.is_available:
            QMessageBox.warning(self, "エラー", "利用可能なスカウトを選択してください。")
            return

        scout_data.is_available = False
        scout_data.current_mission_id = self.selected_prospect.id

        self.selected_prospect.scouting_status = ScoutingStatus.IN_PROGRESS
        self.selected_prospect.assigned_scout = scout_data

        QMessageBox.information(self, "派遣完了",
            f"{scout_data.name}を{self.selected_prospect.name}の調査に派遣しました。")

        self._update_scout_combo()
        self._update_scout_status()
        self._update_detail_panel()
        self._refresh_table()

    def _recall_scout(self):
        if not self.selected_prospect or not self.selected_prospect.assigned_scout:
            return

        scout = self.selected_prospect.assigned_scout
        scout.is_available = True
        scout.current_mission_id = None

        self.selected_prospect.scouting_status = ScoutingStatus.NOT_STARTED if self.selected_prospect.scout_level < 100 else ScoutingStatus.COMPLETED
        self.selected_prospect.assigned_scout = None

        QMessageBox.information(self, "帰還完了", f"{scout.name}が帰還しました。")

        self._update_scout_combo()
        self._update_scout_status()
        self._update_detail_panel()
        self._refresh_table()

    def advance_day(self):
        self._auto_assign_scouts()
        
        for prospect in self.prospects:
            if prospect.scouting_status == ScoutingStatus.IN_PROGRESS and prospect.assigned_scout:
                progress = prospect.assigned_scout.daily_progress
                prospect.scout_level = min(100, prospect.scout_level + progress)

                if prospect.scout_level >= 100:
                    prospect.scouting_status = ScoutingStatus.COMPLETED
                    prospect.assigned_scout.is_available = True
                    prospect.assigned_scout.current_mission_id = None
                    prospect.assigned_scout = None

                prospect.recalculate_estimates()

        self._update_scout_combo()
        self._update_scout_status()
        self._refresh_table()
        if self.selected_prospect:
            self._update_detail_panel()

    def _auto_assign_scouts(self):
        """Available scouts work on top unscouted prospects automatically"""
        free_scouts = [s for s in self.scouts if s.is_available]
        if not free_scouts:
            return

        # Find unscouted prospects
        unscouted = [p for p in self.prospects 
                     if p.scouting_status == ScoutingStatus.NOT_STARTED 
                     and not p.assigned_scout]
        
        # Assign to first available (assuming list is roughly sorted by value/rank)
        for scout in free_scouts:
            if not unscouted:
                break
            
            target = unscouted.pop(0)
            target.assigned_scout = scout
            target.scouting_status = ScoutingStatus.IN_PROGRESS
            scout.is_available = False
            scout.current_mission_id = target.name


# ========================================
# 2. Foreign Player Scouting Page
# ========================================

class ForeignPlayerScoutingPage(QWidget):
    """新外国人調査ページ"""

    player_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.candidates: List[ForeignPlayerCandidate] = []
        self.scouts: List[Scout] = []
        self.selected_candidate: Optional[ForeignPlayerCandidate] = None
        self.game_state = None
        
        # New features
        self.negotiated_ids = set() # Set of candidate IDs negotiated with today
        self.last_reset_year = None # Last year we reset candidates

        self._generate_dummy_data()
        self._setup_ui()
    
    def set_game_state(self, game_state):
        """ゲーム状態を設定"""
        self.game_state = game_state
        self._update_detail_panel()

    def _generate_dummy_data(self):
        """ダミーデータ生成 (100人)"""
        scout_names = ["John Smith", "Mike Johnson", "Carlos Garcia"]
        for name in scout_names:
            self.scouts.append(Scout(
                name=name,
                skill=random.randint(50, 85),
                specialty="汎用"
            ))

        countries = ["USA", "Dominican", "Cuba", "Venezuela", "Mexico", "Korea", "Taiwan", "Puerto Rico", "Canada", "Australia"]

        positions = [Position.PITCHER, Position.FIRST, Position.LEFT,
                    Position.RIGHT, Position.CENTER, Position.SHORTSTOP, Position.THIRD, Position.SECOND, Position.CATCHER]

        # 100人に増やす
        for i in range(100):
            pos = random.choice(positions)
            
            # player_generatorを利用 (外国人選手)
            gen_player = player_generator.create_foreign_free_agent(pos)
            
            # 能力値の底上げ（ユーザー要望）
            if pos == Position.PITCHER:
                 gen_player.stats.velocity += random.randint(0, 3)
                 gen_player.stats.stuff = min(99, int(gen_player.stats.stuff * 1.05))
                 gen_player.stats.control = min(99, int(gen_player.stats.control * 1.05))
            else:
                 gen_player.stats.contact = min(99, int(gen_player.stats.contact * 1.05))
                 gen_player.stats.power = min(99, int(gen_player.stats.power * 1.05))

            country = random.choice(countries)
            
            # 総額 5000万 ~ 10億
            total_budget = random.randint(50, 1000) * 1000000
            
            # 契約金比率 10% ~ 40%
            bonus_ratio = random.uniform(0.1, 0.4)
            bonus = int(total_budget * bonus_ratio)
            # 100万単位に丸める
            bonus = (bonus // 1000000) * 1000000
            if bonus < 0: bonus = 0

            salary = total_budget - bonus
            # 100万単位に丸める
            salary = (salary // 1000000) * 1000000
            if salary < 10000000: salary = 10000000 # 最低1000万

            # ポテンシャルは年齢に応じて（若いほど高く、ベテランは低い）
            # 外国人選手は即戦力期待なので少し高めに設定（ユーザー要望でさらに+5~10）
            if gen_player.age < 24:
                pot_base = 65 
            elif gen_player.age < 30:
                pot_base = 55
            else:
                pot_base = 40
            
            true_potential = max(1, min(99, int(random.gauss(pot_base, 15))))

            candidate = ForeignPlayerCandidate(
                id=i,
                name=gen_player.name,
                position=gen_player.position,
                pitch_type=gen_player.pitch_type,
                age=gen_player.age,
                country=country,
                true_stats=gen_player.stats,
                true_potential=true_potential,
                salary_demand=salary,
                bonus_demand=bonus,
                years_demand=random.choice([1, 1, 1, 2, 2, 3]),
                interest_level=random.randint(30, 80)
            )
            self.candidates.append(candidate)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {self.theme.border}; width: 1px; }}")

        left_widget = self._create_candidate_list()
        splitter.addWidget(left_widget)

        right_widget = self._create_detail_panel()
        splitter.addWidget(right_widget)

        splitter.setSizes([650, 350])
        layout.addWidget(splitter)

    def _create_toolbar(self) -> QWidget:
        toolbar = QFrame()
        toolbar.setFixedHeight(50)
        toolbar.setStyleSheet(f"background-color: {self.theme.bg_card}; border-bottom: 1px solid {self.theme.border};")

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(12, 0, 12, 0)

        title = QLabel("新外国人調査")
        title.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; font-size: 16px;")
        layout.addWidget(title)

        layout.addSpacing(20)

        self.pos_filter = QComboBox()
        self.pos_filter.addItems(["全ポジション", "投手", "野手"])
        self.pos_filter.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 4px;")
        self.pos_filter.currentIndexChanged.connect(self._refresh_table)
        layout.addWidget(self.pos_filter)
        
        layout.addSpacing(10)
        
        # ソート機能追加
        layout.addWidget(QLabel("並び順:"))
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["推定総合(最高値)", "推定潜在(最高値)", "予想総額", "年齢"])
        self.sort_combo.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 4px;")
        self.sort_combo.currentIndexChanged.connect(self._refresh_table)
        layout.addWidget(self.sort_combo)

        layout.addStretch()

        self.scout_status_label = QLabel()
        self.scout_status_label.setStyleSheet(f"color: {self.theme.text_secondary};")
        layout.addWidget(self.scout_status_label)
        self._update_scout_status()

        return toolbar

    def _create_candidate_list(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        header = QLabel("外国人選手候補リスト (100名)")
        header.setStyleSheet(f"font-weight: bold; color: {self.theme.text_secondary}; font-size: 13px;")
        layout.addWidget(header)

        self.candidate_table = ContractsTableWidget()
        self.rating_delegate = RatingDelegate(self)

        cols = ["名前", "Pos", "年齢", "国籍", "推定総合", "推定潜在", "予想総額", "調査度", "状態"]
        widths = [140, 40, 40, 70, 100, 80, 80, 60, 70]

        self.candidate_table.setColumnCount(len(cols))
        self.candidate_table.setHorizontalHeaderLabels(cols)
        for i, w in enumerate(widths):
            self.candidate_table.setColumnWidth(i, w)

        self.candidate_table.row_double_clicked.connect(self._on_candidate_selected)
        self.candidate_table.itemClicked.connect(lambda item: self._on_candidate_clicked(item.row()))

        layout.addWidget(self.candidate_table)

        self._refresh_table()
        return widget

    def _create_detail_panel(self) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet(f"background-color: {self.theme.bg_card};")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)  # Reduced spacing for better fit

        self.detail_header = QLabel("選手を選択してください")
        self.detail_header.setStyleSheet(f"color: {self.theme.text_primary}; font-size: 14px; font-weight: bold;")
        self.detail_header.setWordWrap(True)
        layout.addWidget(self.detail_header)
        
        # 期限切れ警告ラベル
        self.deadline_label = QLabel("")
        self.deadline_label.setStyleSheet(f"color: {self.theme.danger}; font-weight: bold;")
        self.deadline_label.setVisible(False)
        layout.addWidget(self.deadline_label)

        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-radius: 4px; padding: 10px;")
        
        # グリッドレイアウトを保持
        self.stats_layout = QGridLayout(self.stats_frame)
        self.stats_layout.setSpacing(8)

        layout.addWidget(self.stats_frame)

        potential_frame = QFrame()
        potential_frame.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-radius: 4px; padding: 6px;")
        potential_layout = QHBoxLayout(potential_frame)
        potential_layout.setContentsMargins(6, 4, 6, 4)

        pot_lbl = QLabel("潜在:")
        pot_lbl.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 11px;")
        potential_layout.addWidget(pot_lbl)
        self.potential_label = QLabel("?")
        self.potential_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; font-size: 14px;")
        potential_layout.addWidget(self.potential_label)
        potential_layout.addStretch()

        layout.addWidget(potential_frame)

        progress_frame = QFrame()
        progress_frame.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-radius: 4px; padding: 6px;")
        progress_layout = QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(6, 4, 6, 4)
        progress_layout.setSpacing(4)

        prog_lbl = QLabel("調査進捗")
        prog_lbl.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 11px;")
        progress_layout.addWidget(prog_lbl)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.theme.bg_input};
                border: 1px solid {self.theme.border};
                border-radius: 2px;
                text-align: center;
                color: {self.theme.text_primary};
                font-size: 10px;
            }}
            QProgressBar::chunk {{
                background-color: {self.theme.accent_blue};
            }}
        """)
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(progress_frame)

        scout_frame = QFrame()
        scout_frame.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-radius: 4px; padding: 10px;")
        scout_layout = QVBoxLayout(scout_frame)

        scout_layout.addWidget(QLabel("スカウト派遣"))

        self.scout_combo = QComboBox()
        self.scout_combo.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 4px;")
        self._update_scout_combo()
        scout_layout.addWidget(self.scout_combo)

        btn_layout = QHBoxLayout()

        self.dispatch_btn = QPushButton("スカウト派遣")
        self.dispatch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.accent_blue};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent_blue_hover};
            }}
            QPushButton:disabled {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_muted};
            }}
        """)
        self.dispatch_btn.clicked.connect(self._dispatch_scout)
        self.dispatch_btn.setEnabled(False)
        btn_layout.addWidget(self.dispatch_btn)

        self.recall_btn = QPushButton("スカウト帰還")
        self.recall_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.accent_orange};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent_orange_hover};
            }}
            QPushButton:disabled {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_muted};
            }}
        """)
        self.recall_btn.clicked.connect(self._recall_scout)
        self.recall_btn.setEnabled(False)
        btn_layout.addWidget(self.recall_btn)

        scout_layout.addLayout(btn_layout)
        layout.addWidget(scout_frame)

        # 契約交渉フレーム
        negotiation_frame = QFrame()
        negotiation_frame.setMinimumWidth(300)  # Prevent text cutoff
        negotiation_frame.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-radius: 4px; padding: 12px;")
        negotiation_layout = QVBoxLayout(negotiation_frame)
        negotiation_layout.setContentsMargins(12, 12, 12, 12)

        neg_title = QLabel("契約交渉")
        neg_title.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; font-size: 14px;")
        negotiation_layout.addWidget(neg_title)

        interest_layout = QHBoxLayout()
        interest_layout.addWidget(QLabel("興味度:"))
        self.interest_label = QLabel("?")
        self.interest_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold;")
        interest_layout.addWidget(self.interest_label)
        interest_layout.addStretch()
        negotiation_layout.addLayout(interest_layout)

        # 交渉開始ボタン
        self.negotiate_btn = QPushButton("交渉開始")
        self.negotiate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.success};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme.success_hover};
            }}
            QPushButton:disabled {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_muted};
            }}
        """)
        self.negotiate_btn.clicked.connect(self._start_negotiation)
        self.negotiate_btn.setEnabled(False)
        negotiation_layout.addWidget(self.negotiate_btn)

        layout.addWidget(negotiation_frame)

        layout.addStretch()
        return widget

    def _refresh_table(self):
        filtered = self.candidates.copy()

        pos_filter = self.pos_filter.currentText()
        if pos_filter == "投手":
            filtered = [c for c in filtered if c.position == Position.PITCHER]
        elif pos_filter == "野手":
            filtered = [c for c in filtered if c.position != Position.PITCHER]

        # ソート処理
        sort_key = self.sort_combo.currentText()
        if sort_key == "推定総合(最高値)":
            filtered.sort(key=lambda p: -p.get_max_estimated_overall())
        elif sort_key == "推定潜在(最高値)":
            filtered.sort(key=lambda p: -p.get_max_estimated_potential())
        elif sort_key == "予想総額":
            filtered.sort(key=lambda p: -p.get_total_cost())
        elif sort_key == "年齢":
            filtered.sort(key=lambda p: p.age)

        self.candidate_table.setRowCount(len(filtered))

        for row, candidate in enumerate(filtered):
            name_item = create_text_item(candidate.name, Qt.AlignLeft | Qt.AlignVCenter)
            name_item.setData(Qt.UserRole, candidate)
            self.candidate_table.setItem(row, 0, name_item)

            pos_item = create_text_item(short_pos_name(candidate.position))
            self.candidate_table.setItem(row, 1, pos_item)

            age_item = create_text_item(str(candidate.age))
            self.candidate_table.setItem(row, 2, age_item)

            country_item = create_text_item(candidate.country)
            self.candidate_table.setItem(row, 3, country_item)

            ovr_text = candidate.get_overall_display()
            rank_item = create_text_item(ovr_text)
            
            max_ovr = candidate.get_max_estimated_overall()
            if max_ovr >= 320: rank_item.setForeground(QColor(THEME.rating_s))
            elif max_ovr >= 280: rank_item.setForeground(QColor(THEME.rating_a))
            elif max_ovr >= 240: rank_item.setForeground(QColor(THEME.rating_b))
            elif max_ovr >= 200: rank_item.setForeground(QColor(THEME.text_primary))
            else: rank_item.setForeground(QColor(THEME.text_muted))
            
            font = rank_item.font()
            font.setBold(True)
            rank_item.setFont(font)
            self.candidate_table.setItem(row, 4, rank_item)

            pot_text = candidate.get_potential_display()
            pot_item = create_text_item(pot_text)
            pot_item.setForeground(get_rank_color(pot_text))
            font = pot_item.font()
            font.setBold(True)
            pot_item.setFont(font)
            self.candidate_table.setItem(row, 5, pot_item)

            # 予想総額
            cost_text = candidate.get_total_cost_display()
            cost_item = create_text_item(cost_text)
            self.candidate_table.setItem(row, 6, cost_item)

            progress_item = create_progress_item(candidate.scout_level)
            self.candidate_table.setItem(row, 7, progress_item)

            if candidate.negotiation_started:
                status = "交渉中"
                color = self.theme.success
            elif candidate.scouting_status == ScoutingStatus.IN_PROGRESS:
                status = "調査中"
                color = self.theme.accent_blue
            elif candidate.scout_level >= 50:
                status = "交渉可能"
                color = self.theme.warning
            else:
                status = "未調査"
                color = self.theme.text_muted

            status_item = create_text_item(status)
            status_item.setForeground(QColor(color))
            self.candidate_table.setItem(row, 8, status_item)

    def _on_candidate_clicked(self, row: int):
        item = self.candidate_table.item(row, 0)
        if item:
            candidate = item.data(Qt.UserRole)
            if candidate:
                self.selected_candidate = candidate
                self._update_detail_panel()

    def _on_candidate_selected(self, row: int):
        self._on_candidate_clicked(row)

    def _update_detail_panel(self):
        c = self.selected_candidate
        if not c:
            return

        # 期限チェック (8月1日以降～12月末まで獲得不可とする)
        is_deadline_passed = False
        # ★修正: .date -> .current_date (GameStateManagerの属性名に合わせる)
        if self.game_state and hasattr(self.game_state, 'current_date'):
            try:
                # current_dateは "YYYY-MM-DD" 形式
                m = int(self.game_state.current_date.split('-')[1])
                # 8月以降は獲得停止
                if m >= 8 and m <= 12:
                    is_deadline_passed = True
            except:
                pass

        self.detail_header.setText(f"{c.name} ({short_pos_name(c.position)}) - {c.country}")

        if is_deadline_passed:
            self.deadline_label.setText("※8月1日を過ぎたため、今シーズンの獲得は終了しました")
            self.deadline_label.setVisible(True)
        else:
            self.deadline_label.setVisible(False)

        # 詳細パネルの能力表示をクリアして再生成
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        visible = c.get_visible_stats()

        # ポジションに応じた能力表示
        if c.position == Position.PITCHER:
            items = [
                ("球速", "velocity"), ("球威", "stuff"), ("制球", "control"),
                ("スタミナ", "stamina"), ("変化球", "movement")
            ]
        else:
            items = [
                ("ミート", "contact"), ("パワー", "power"), ("走力", "speed"),
                ("肩力", "arm"), ("守備", "fielding")
            ]

        for i, (name, key) in enumerate(items):
            row, col = i // 3, (i % 3) * 2
            
            label = QLabel(name)
            label.setStyleSheet(f"color: {self.theme.text_secondary};")
            self.stats_layout.addWidget(label, row, col)

            val = visible.get(key, -1)
            value_label = QLabel("?")
            value_label.setStyleSheet(f"color: {self.theme.text_muted}; font-weight: bold;")
            
            if val > 0:
                if key == "velocity":
                    value_label.setText(f"{val}km/h")
                    value_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold;")
                else:
                    rank = Theme.get_rating_rank(val)
                    value_label.setText(f"{rank} ({val})")
                    value_label.setStyleSheet(f"color: {Theme.get_rating_color(val)}; font-weight: bold;")
            
            self.stats_layout.addWidget(value_label, row, col + 1)

        pot_text = c.get_potential_display()
        self.potential_label.setText(pot_text)
        self.potential_label.setStyleSheet(f"color: {get_rank_color(pot_text).name()}; font-weight: bold; font-size: 18px;")

        self.progress_bar.setValue(int(c.scout_level))

        if c.scout_level >= 40:
            self.interest_label.setText(f"{c.interest_level}%")
            if c.interest_level >= 70:
                self.interest_label.setStyleSheet(f"color: {self.theme.success}; font-weight: bold;")
            elif c.interest_level >= 40:
                self.interest_label.setStyleSheet(f"color: {self.theme.warning}; font-weight: bold;")
            else:
                self.interest_label.setStyleSheet(f"color: {self.theme.danger}; font-weight: bold;")
        else:
            self.interest_label.setText("?")
            self.interest_label.setStyleSheet(f"color: {self.theme.text_muted}; font-weight: bold;")

        # スカウト派遣ボタン制御
        self.dispatch_btn.setEnabled(
            not is_deadline_passed and
            c.scouting_status != ScoutingStatus.IN_PROGRESS and
            c.scout_level < 100 and
            any(s.is_available for s in self.scouts)
        )
        # 帰還は期限後でも可能
        self.recall_btn.setEnabled(c.scouting_status == ScoutingStatus.IN_PROGRESS)
        
        # 交渉ボタン制御 (調査度50%以上で可能)
        self.negotiate_btn.setEnabled(
            not is_deadline_passed and
            c.scout_level >= 50 and 
            not c.negotiation_started
        )

    def _update_scout_combo(self):
        self.scout_combo.clear()
        for scout in self.scouts:
            status = "空き" if scout.is_available else "派遣中"
            self.scout_combo.addItem(f"{scout.name} (能力:{scout.skill}) [{status}]", scout)

    def _update_scout_status(self):
        available = sum(1 for s in self.scouts if s.is_available)
        total = len(self.scouts)
        self.scout_status_label.setText(f"海外スカウト: {available}/{total} 空き")

    def _dispatch_scout(self):
        if not self.selected_candidate:
            return

        scout_data = self.scout_combo.currentData()
        if not scout_data or not scout_data.is_available:
            QMessageBox.warning(self, "エラー", "利用可能なスカウトを選択してください。")
            return

        scout_data.is_available = False
        scout_data.current_mission_id = self.selected_candidate.id

        self.selected_candidate.scouting_status = ScoutingStatus.IN_PROGRESS
        self.selected_candidate.assigned_scout = scout_data

        QMessageBox.information(self, "派遣完了",
            f"{scout_data.name}を{self.selected_candidate.name}の調査に派遣しました。")

        self._update_scout_combo()
        self._update_scout_status()
        self._update_detail_panel()
        self._refresh_table()

    def _recall_scout(self):
        if not self.selected_candidate or not self.selected_candidate.assigned_scout:
            return

        scout = self.selected_candidate.assigned_scout
        scout.is_available = True
        scout.current_mission_id = None

        self.selected_candidate.scouting_status = ScoutingStatus.NOT_STARTED
        self.selected_candidate.assigned_scout = None

        QMessageBox.information(self, "帰還完了", f"{scout.name}が帰還しました。")

        self._update_scout_combo()
        self._update_scout_status()
        self._update_detail_panel()
        self._refresh_table()

    def _start_negotiation(self):
        c = self.selected_candidate
        if not c or c.scout_level < 50:
            return

        # Check negotiation limit
        if c.id in self.negotiated_ids:
            QMessageBox.warning(self, "交渉不可", "この選手とは本日すでに交渉済みです。")
            return

        # ★追加: 交渉画面(ダイアログ)を開く
        dlg = ForeignNegotiationDialog(self, c, self.theme)
        if dlg.exec() != QDialog.Accepted:
            return
            
        # Add to negotiated set (consumed daily attempt)
        self.negotiated_ids.add(c.id)

        # ダイアログから値を取得
        offered_salary_val, offered_years = dlg.get_values()
        offered_salary = offered_salary_val * 1000000

        salary_ratio = offered_salary / c.salary_demand
        years_ratio = offered_years / c.years_demand

        # If salary is less than 2/3 of demand, success rate is 0%
        if salary_ratio < 0.67:
            success_chance = 0
        else:
            base_chance = c.interest_level
            if salary_ratio >= 1.2:
                base_chance += 20
            elif salary_ratio >= 1.0:
                base_chance += 10
            elif salary_ratio >= 0.8:
                base_chance -= 10
            else:
                base_chance -= 30

            if years_ratio >= 1.0:
                base_chance += 10
            else:
                base_chance -= 10
            
            # Longer contracts reduce success rate (each year above demand = -3%)
            if offered_years > c.years_demand:
                extra_years = offered_years - c.years_demand
                base_chance -= extra_years * 3

            success_chance = max(5, min(95, base_chance))

        result = random.randint(1, 100)

        if result <= success_chance:
            # ★ 交渉成功 - 選手を実際にチームに追加
            if self.game_state and self.game_state.player_team:
                from models import Player
                
                # Create Player from candidate
                new_player = Player(
                    name=c.name,
                    position=c.position,
                    age=c.age,
                    stats=c.true_stats,
                    pitch_type=c.pitch_type,
                    uniform_number=self._get_available_uniform_number(),
                    is_foreign=True
                )
                new_player.salary = offered_salary
                new_player.contract_years = offered_years
                new_player.potential = c.true_potential
                
                # Add to player's team
                self.game_state.player_team.players.append(new_player)
                
                QMessageBox.information(self, "契約成功",
                    f"{c.name}との契約が成立！\n"
                    f"年俸: {offered_salary // 1000000}百万円 / {offered_years}年契約\n"
                    f"選手がチームに加わりました！")
                
                # Remove from candidates list
                c.negotiation_started = True
                self.candidates.remove(c)
                self.selected_candidate = None
            else:
                QMessageBox.warning(self, "エラー", "チームデータがありません。")
        else:
            QMessageBox.warning(self, "交渉失敗",
                f"{c.name}は提示条件に満足しませんでした。")
            c.interest_level = max(10, c.interest_level - 5)

        self._update_detail_panel()
        self._refresh_table()
    
    def _get_available_uniform_number(self) -> int:
        """Get an available uniform number (1-99)"""
        if not self.game_state or not self.game_state.player_team:
            return random.randint(50, 99)
        used = {p.uniform_number for p in self.game_state.player_team.players}
        for n in range(1, 100):
            if n not in used:
                return n
        return 99

    def reset_candidates(self):
        """Reset and regenerate foreign candidates"""
        self.candidates.clear()
        self.selected_candidate = None
        
        # Regenerate candidates (logic from _generate_dummy_data)
        countries = ["USA", "Dominican", "Cuba", "Venezuela", "Mexico", "Korea", "Taiwan", "Puerto Rico", "Canada", "Australia"]
        positions = [Position.PITCHER, Position.FIRST, Position.LEFT,
                    Position.RIGHT, Position.CENTER, Position.SHORTSTOP, Position.THIRD, Position.SECOND, Position.CATCHER]
                    
        for i in range(100):
            pos = random.choice(positions)
            gen_player = player_generator.create_foreign_free_agent(pos)
            
            # Boost stats
            if pos == Position.PITCHER:
                 gen_player.stats.velocity += random.randint(0, 3)
                 gen_player.stats.stuff = min(99, int(gen_player.stats.stuff * 1.05))
                 gen_player.stats.control = min(99, int(gen_player.stats.control * 1.05))
            else:
                 gen_player.stats.contact = min(99, int(gen_player.stats.contact * 1.05))
                 gen_player.stats.power = min(99, int(gen_player.stats.power * 1.05))

            country = random.choice(countries)
            total = random.randint(50, 1000) * 1000000
            bonus = int(total * random.uniform(0.1, 0.4))
            bonus = (bonus // 1000000) * 1000000
            salary = total - bonus
            salary = (salary // 1000000) * 1000000
            if salary < 10000000: salary = 10000000

            if gen_player.age < 24: pot_base = 65 
            elif gen_player.age < 30: pot_base = 55
            else: pot_base = 40
            pot = max(1, min(99, int(random.gauss(pot_base, 15))))

            candidate = ForeignPlayerCandidate(
                id=i,
                name=gen_player.name,
                position=gen_player.position,
                pitch_type=gen_player.pitch_type,
                age=gen_player.age,
                country=country,
                true_stats=gen_player.stats,
                true_potential=pot,
                salary_demand=salary,
                bonus_demand=bonus,
                years_demand=random.choice([1, 1, 1, 2, 2, 3]),
                interest_level=random.randint(30, 80)
            )
            self.candidates.append(candidate)
            
        self._refresh_table()
        self._update_detail_panel()
        
        # Record reset year if needed
        if self.game_state and self.game_state.current_date:
            try:
                self.last_reset_year = int(self.game_state.current_date.split('-')[0])
            except: pass

    def advance_day(self):
        # Clear daily negotiation limit
        self.negotiated_ids.clear()
        
        # Auto-assign unassigned scouts to best candidates
        self._auto_assign_scouts()
        
        for candidate in self.candidates:
            if candidate.scouting_status == ScoutingStatus.IN_PROGRESS and candidate.assigned_scout:
                progress = candidate.assigned_scout.daily_progress
                candidate.scout_level = min(100, candidate.scout_level + progress)

                if candidate.scout_level >= 100:
                    candidate.scouting_status = ScoutingStatus.COMPLETED
                    candidate.assigned_scout.is_available = True
                    candidate.assigned_scout.current_mission_id = None
                    candidate.assigned_scout = None
                
                candidate.recalculate_estimates()

        self._update_scout_combo()
        self._update_scout_status()
        self._refresh_table()
        if self.selected_candidate:
            self._update_detail_panel()
    
    def _auto_assign_scouts(self):
        """Automatically assign free scouts to the best unassigned candidates"""
        # Get free scouts
        free_scouts = [s for s in self.scouts if s.is_available]
        if not free_scouts:
            return
        
        # Get candidates that need scouting (not scouted, not being scouted)
        unscouted = [c for c in self.candidates 
                     if c.scouting_status == ScoutingStatus.NOT_STARTED 
                     and not c.assigned_scout]
        
        if not unscouted:
            return
        
        # Sort by interest level (highest first) for best candidates
        unscouted.sort(key=lambda x: x.interest_level, reverse=True)
        
        # Assign scouts to top candidates
        for scout in free_scouts:
            if not unscouted:
                break
            
            candidate = unscouted.pop(0)
            candidate.assigned_scout = scout
            candidate.scouting_status = ScoutingStatus.IN_PROGRESS
            scout.is_available = False
            scout.current_mission_id = candidate.name


# ========================================
# 3. Trade Page
# ========================================

class TradePage(QWidget):
    """トレードページ"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.current_team = None
        self.target_team = None

        self.offered_players: List[int] = []  # 提供する選手のインデックス
        self.requested_players: List[int] = []  # 要求する選手のインデックス

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ツールバー
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # メインコンテンツ
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 左: 自チーム
        self_panel = self._create_team_panel("自チーム (提供)", is_self=True)
        main_layout.addWidget(self_panel, 1)

        # 中央: トレード操作
        center_panel = self._create_trade_center()
        main_layout.addWidget(center_panel)

        # 右: 相手チーム
        target_panel = self._create_team_panel("相手チーム (獲得)", is_self=False)
        main_layout.addWidget(target_panel, 1)

        layout.addWidget(main_widget)

    def _create_toolbar(self) -> QWidget:
        toolbar = QFrame()
        toolbar.setFixedHeight(50)
        toolbar.setStyleSheet(f"background-color: {self.theme.bg_card}; border-bottom: 1px solid {self.theme.border};")

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(12, 0, 12, 0)

        title = QLabel("トレード")
        title.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; font-size: 16px;")
        layout.addWidget(title)

        layout.addSpacing(20)

        layout.addWidget(QLabel("相手チーム:"))
        self.team_combo = QComboBox()
        self.team_combo.setMinimumWidth(200)
        self.team_combo.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 4px;")
        self.team_combo.currentIndexChanged.connect(self._on_target_team_changed)
        layout.addWidget(self.team_combo)

        layout.addStretch()

        return toolbar

    def _create_team_panel(self, title: str, is_self: bool) -> QWidget:
        panel = QFrame()
        color = self.theme.accent_blue if is_self else self.theme.accent_orange
        panel.setStyleSheet(f"background-color: {self.theme.bg_card}; border: 2px solid {color}; border-radius: 4px;")

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header = QLabel(title)
        header.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        layout.addWidget(header)

        # 選手リスト
        if is_self:
            self.self_table = ContractsTableWidget()
            table = self.self_table
        else:
            self.target_table = ContractsTableWidget()
            table = self.target_table

        cols = ["名前", "Pos", "年齢", "総合"]
        widths = [100, 40, 40, 50]

        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        for i, w in enumerate(widths):
            table.setColumnWidth(i, w)

        table.row_double_clicked.connect(
            lambda row: self._add_to_offer(row, is_self)
        )

        layout.addWidget(table, 2)

        # トレード対象リスト
        offer_label = QLabel("トレード対象:")
        offer_label.setStyleSheet(f"color: {self.theme.text_secondary}; margin-top: 8px;")
        layout.addWidget(offer_label)

        if is_self:
            self.self_offer_table = ContractsTableWidget()
            offer_table = self.self_offer_table
        else:
            self.target_offer_table = ContractsTableWidget()
            offer_table = self.target_offer_table

        offer_table.setColumnCount(len(cols))
        offer_table.setHorizontalHeaderLabels(cols)
        for i, w in enumerate(widths):
            offer_table.setColumnWidth(i, w)

        offer_table.setMaximumHeight(150)
        offer_table.row_double_clicked.connect(
            lambda row: self._remove_from_offer(row, is_self)
        )

        layout.addWidget(offer_table, 1)

        # 合計評価
        if is_self:
            self.self_value_label = QLabel("合計評価: 0")
        else:
            self.target_value_label = QLabel("合計評価: 0")

        value_label = self.self_value_label if is_self else self.target_value_label
        value_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold;")
        layout.addWidget(value_label)

        return panel

    def _create_trade_center(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(150)
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)

        layout.addStretch()

        # 評価バランス表示
        self.balance_label = QLabel("評価差: 0")
        self.balance_label.setAlignment(Qt.AlignCenter)
        self.balance_label.setStyleSheet(f"color: {self.theme.text_primary}; font-size: 16px; font-weight: bold;")
        layout.addWidget(self.balance_label)

        self.balance_indicator = QLabel("---")
        self.balance_indicator.setAlignment(Qt.AlignCenter)
        self.balance_indicator.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 14px;")
        layout.addWidget(self.balance_indicator)

        layout.addSpacing(20)

        # トレードボタン
        self.trade_btn = QPushButton("トレード提案")
        self.trade_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.accent_blue};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 12px 24px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.accent_blue_hover};
            }}
            QPushButton:disabled {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_muted};
            }}
        """)
        self.trade_btn.clicked.connect(self._propose_trade)
        self.trade_btn.setEnabled(False)
        layout.addWidget(self.trade_btn)

        # クリアボタン
        clear_btn = QPushButton("クリア")
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.bg_card};
                color: {self.theme.text_secondary};
                border: 1px solid {self.theme.border};
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.bg_hover};
            }}
        """)
        clear_btn.clicked.connect(self._clear_trade)
        layout.addWidget(clear_btn)

        layout.addStretch()

        return panel

    def set_game_state(self, game_state):
        """ゲーム状態を設定"""
        self.game_state = game_state
        if game_state and game_state.player_team:
            self.current_team = game_state.player_team
            self._update_team_combo()
            self._refresh_self_table()

    def _update_team_combo(self):
        """チームコンボボックスを更新"""
        self.team_combo.clear()
        if not self.game_state:
            return

        all_teams = self.game_state.north_teams + self.game_state.south_teams
        for team in all_teams:
            if team != self.current_team:
                self.team_combo.addItem(team.name, team)

    def _on_target_team_changed(self):
        """相手チーム変更時"""
        self.target_team = self.team_combo.currentData()
        self._refresh_target_table()
        self._clear_trade()

    def _refresh_self_table(self):
        """自チームテーブルを更新"""
        if not self.current_team:
            return

        players = [p for p in self.current_team.players if not p.is_developmental]
        self._fill_player_table(self.self_table, players, self.current_team)

    def _refresh_target_table(self):
        """相手チームテーブルを更新"""
        if not self.target_team:
            self.target_table.setRowCount(0)
            return

        players = [p for p in self.target_team.players if not p.is_developmental]
        self._fill_player_table(self.target_table, players, self.target_team)

    def _fill_player_table(self, table: ContractsTableWidget, players: List[Player], team: Team):
        """選手テーブルを埋める"""
        table.setRowCount(len(players))

        for row, player in enumerate(players):
            player_idx = team.players.index(player)

            # 名前
            name_item = create_text_item(player.name, Qt.AlignLeft | Qt.AlignVCenter)
            name_item.setData(Qt.UserRole, player_idx)
            table.setItem(row, 0, name_item)

            # ポジション
            pos_item = create_text_item(short_pos_name(player.position))
            table.setItem(row, 1, pos_item)

            # 年齢
            age_item = create_text_item(str(player.age))
            table.setItem(row, 2, age_item)

            # 総合
            ovr = player.overall_rating
            ovr_item = create_text_item(f"★{ovr}")
            ovr_item.setForeground(QColor("#FFD700"))
            font = ovr_item.font()
            font.setBold(True)
            ovr_item.setFont(font)
            table.setItem(row, 3, ovr_item)

    def _add_to_offer(self, row: int, is_self: bool):
        """トレード対象に追加"""
        if is_self:
            table = self.self_table
            offer_list = self.offered_players
            team = self.current_team
        else:
            table = self.target_table
            offer_list = self.requested_players
            team = self.target_team

        if not team:
            return

        item = table.item(row, 0)
        if not item:
            return

        player_idx = item.data(Qt.UserRole)
        if player_idx is None or player_idx in offer_list:
            return

        if len(offer_list) >= 5:
            QMessageBox.warning(self, "上限", "一度にトレードできる選手は5人までです。")
            return

        offer_list.append(player_idx)
        self._refresh_offer_tables()
        self._update_trade_balance()

    def _remove_from_offer(self, row: int, is_self: bool):
        """トレード対象から削除"""
        if is_self:
            offer_table = self.self_offer_table
            offer_list = self.offered_players
        else:
            offer_table = self.target_offer_table
            offer_list = self.requested_players

        item = offer_table.item(row, 0)
        if not item:
            return

        player_idx = item.data(Qt.UserRole)
        if player_idx in offer_list:
            offer_list.remove(player_idx)

        self._refresh_offer_tables()
        self._update_trade_balance()

    def _refresh_offer_tables(self):
        """トレード対象テーブルを更新"""
        # 自チーム
        if self.current_team:
            players = [self.current_team.players[i] for i in self.offered_players if 0 <= i < len(self.current_team.players)]
            self._fill_offer_table(self.self_offer_table, players, self.current_team)

        # 相手チーム
        if self.target_team:
            players = [self.target_team.players[i] for i in self.requested_players if 0 <= i < len(self.target_team.players)]
            self._fill_offer_table(self.target_offer_table, players, self.target_team)

    def _fill_offer_table(self, table: ContractsTableWidget, players: List[Player], team: Team):
        """オファーテーブルを埋める"""
        table.setRowCount(len(players))

        for row, player in enumerate(players):
            player_idx = team.players.index(player)

            name_item = create_text_item(player.name, Qt.AlignLeft | Qt.AlignVCenter)
            name_item.setData(Qt.UserRole, player_idx)
            table.setItem(row, 0, name_item)

            pos_item = create_text_item(short_pos_name(player.position))
            table.setItem(row, 1, pos_item)

            age_item = create_text_item(str(player.age))
            table.setItem(row, 2, age_item)

            ovr = player.overall_rating
            ovr_item = create_text_item(f"★{ovr}")
            ovr_item.setForeground(QColor("#FFD700"))
            font = ovr_item.font()
            font.setBold(True)
            ovr_item.setFont(font)
            table.setItem(row, 3, ovr_item)

    def _update_trade_balance(self):
        """トレードバランスを更新"""
        self_value = 0
        target_value = 0

        if self.current_team:
            for idx in self.offered_players:
                if 0 <= idx < len(self.current_team.players):
                    self_value += self.current_team.players[idx].overall_rating

        if self.target_team:
            for idx in self.requested_players:
                if 0 <= idx < len(self.target_team.players):
                    target_value += self.target_team.players[idx].overall_rating

        self.self_value_label.setText(f"合計評価: {self_value}")
        self.target_value_label.setText(f"合計評価: {target_value}")

        diff = self_value - target_value
        self.balance_label.setText(f"評価差: {diff:+d}")

        if diff >= 50:
            self.balance_indicator.setText("相手有利")
            self.balance_indicator.setStyleSheet(f"color: {self.theme.success}; font-size: 14px;")
        elif diff >= 10:
            self.balance_indicator.setText("やや相手有利")
            self.balance_indicator.setStyleSheet(f"color: {self.theme.success}; font-size: 14px;")
        elif diff >= -10:
            self.balance_indicator.setText("均衡")
            self.balance_indicator.setStyleSheet(f"color: {self.theme.warning}; font-size: 14px;")
        elif diff >= -50:
            self.balance_indicator.setText("やや自チーム有利")
            self.balance_indicator.setStyleSheet(f"color: {self.theme.danger}; font-size: 14px;")
        else:
            self.balance_indicator.setText("自チーム有利")
            self.balance_indicator.setStyleSheet(f"color: {self.theme.danger}; font-size: 14px;")

        # トレードボタン有効化
        self.trade_btn.setEnabled(
            len(self.offered_players) > 0 and
            len(self.requested_players) > 0
        )

    def _propose_trade(self):
        """トレード提案"""
        if not self.current_team or not self.target_team:
            return

        if not self.offered_players or not self.requested_players:
            return

        # トレード成功率計算
        self_value = sum(self.current_team.players[i].overall_rating for i in self.offered_players if 0 <= i < len(self.current_team.players))
        target_value = sum(self.target_team.players[i].overall_rating for i in self.requested_players if 0 <= i < len(self.target_team.players))

        diff = self_value - target_value

        # 基本成功率
        if diff >= 100:
            base_chance = 90
        elif diff >= 50:
            base_chance = 75
        elif diff >= 20:
            base_chance = 60
        elif diff >= 0:
            base_chance = 45
        elif diff >= -20:
            base_chance = 30
        elif diff >= -50:
            base_chance = 15
        else:
            base_chance = 5

        result = random.randint(1, 100)

        if result <= base_chance:
            # 成功
            QMessageBox.information(self, "トレード成立",
                f"トレードが成立しました！\n(成功率: {base_chance}%)")

            # 選手交換処理
            offered_copy = list(self.offered_players)
            requested_copy = list(self.requested_players)

            for idx in offered_copy:
                if 0 <= idx < len(self.current_team.players):
                    player = self.current_team.players[idx]
                    self.target_team.players.append(player)

            for idx in requested_copy:
                if 0 <= idx < len(self.target_team.players):
                    player = self.target_team.players[idx]
                    self.current_team.players.append(player)

            # 元のリストから削除 (逆順で)
            for idx in sorted(offered_copy, reverse=True):
                if 0 <= idx < len(self.current_team.players):
                    self.current_team.players.pop(idx)

            for idx in sorted(requested_copy, reverse=True):
                if 0 <= idx < len(self.target_team.players):
                    self.target_team.players.pop(idx)

            self._clear_trade()
            self._refresh_self_table()
            self._refresh_target_table()
        else:
            QMessageBox.warning(self, "トレード不成立",
                f"相手チームがトレードを拒否しました。\n(成功率: {base_chance}%)")

    def _clear_trade(self):
        """トレード内容をクリア"""
        self.offered_players.clear()
        self.requested_players.clear()
        self._refresh_offer_tables()
        self._update_trade_balance()


# ========================================
# Main Contracts Page
# ========================================

class ContractsPage(QWidget):
    """契約管理メインページ"""

    page_changed = Signal(str)
    go_to_player_detail = Signal(object)

    PAGES = {
        "ドラフト候補調査": 0,
        "新外国人調査": 1,
        "トレード": 2,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ContractsPage")
        self.theme = get_theme()
        self.setStyleSheet(f"background-color: {self.theme.bg_dark};")
        self.game_state = None  # Will be set via set_game_state()

        self.current_index = self.PAGES["ドラフト候補調査"]

        self._setup_ui()

        self.stacked_widget.setCurrentIndex(self.current_index)
        self.nav_buttons[self.current_index].setChecked(True)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ナビゲーションバー
        nav_bar = QFrame()
        nav_bar.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-bottom: 1px solid {self.theme.border};")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        self.nav_buttons = []
        for text, index in self.PAGES.items():
            btn = self._create_nav_button(text, index)
            self.nav_buttons.append(btn)
            nav_layout.addWidget(btn)

        nav_layout.addStretch()
        main_layout.addWidget(nav_bar)

        # メインコンテンツ
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background: transparent; border: none;")

        # サブページ
        self.draft_page = DraftScoutingPage()
        self.foreign_page = ForeignPlayerScoutingPage()
        self.trade_page = TradePage()

        self.stacked_widget.addWidget(self.draft_page)
        self.stacked_widget.addWidget(self.foreign_page)
        self.stacked_widget.addWidget(self.trade_page)

        main_layout.addWidget(self.stacked_widget, 1)

    def _create_nav_button(self, text: str, index: int) -> QPushButton:
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setMinimumHeight(45)
        btn.setMinimumWidth(150)

        style = f"""
            QPushButton {{
                background-color: {self.theme.bg_card_elevated};
                color: {self.theme.text_secondary};
                border: none;
                border-bottom: 3px solid transparent;
                padding: 12px 20px;
                font-weight: 700;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.bg_hover};
                color: {self.theme.text_primary};
            }}
            QPushButton:checked {{
                background-color: {self.theme.bg_dark};
                color: {self.theme.text_primary};
                border-bottom: 3px solid {self.theme.accent_blue};
            }}
        """
        btn.setStyleSheet(style)

        def on_clicked(checked):
            if checked:
                self.stacked_widget.setCurrentIndex(index)
                self.current_index = index
                self._update_nav_buttons(index)
                self.page_changed.emit(text)

        btn.clicked.connect(on_clicked)
        return btn

    def _update_nav_buttons(self, active_index: int):
        """アクティブなボタンのみをチェック済みにする"""
        for i, btn in enumerate(self.nav_buttons):
            if i != active_index:
                btn.setChecked(False)

    def set_game_state(self, game_state):
        """ゲーム状態を設定"""
        self.game_state = game_state
        self.trade_page.set_game_state(game_state)
        self.foreign_page.set_game_state(game_state)
        self._update_tab_availability()

    def advance_day(self):
        """日付を進める (ゲーム進行時に呼び出し)"""
        self.draft_page.advance_day()
        self.foreign_page.advance_day()
        
        self._update_tab_availability()
        
        # Check for Foreign Candidate Reset (Offseason Start: 11-01)
        if self.game_state and self.game_state.current_date:
            try:
                md = self.game_state.current_date.split('-')
                if len(md) >= 3 and int(md[1]) == 11 and int(md[2]) == 1:
                    self.foreign_page.reset_candidates()
            except: pass

    def _update_tab_availability(self):
        """日付に応じてタブの有効/無効を切り替え"""
        if not hasattr(self, 'game_state') or not self.game_state or not self.game_state.current_date:
            return
            
        try:
            m = int(self.game_state.current_date.split('-')[1])
            # Foreign Scout (Index 1) Disabled: 8(Aug), 9(Sep), 10(Oct)
            is_foreign_disabled = (m in [8, 9, 10])
            
            # Button 1 is "新外国人調査"
            if len(self.nav_buttons) > 1:
                btn = self.nav_buttons[1]
                btn.setEnabled(not is_foreign_disabled)
                
                # If currently selected and disabled, switch to Draft
                if is_foreign_disabled and self.stacked_widget.currentIndex() == 1:
                     self.nav_buttons[0].click()
        except: pass

    def load_data(self, data_manager):
        """外部からデータをロード・更新"""
        pass