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
from PySide6.QtCore import Qt, Signal, QTimer, QMimeData
from PySide6.QtGui import QColor, QFont, QBrush, QPen, QPainter, QDrag

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
    import player_generator
except ImportError:
    pass

from game_state import PendingTrade


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
    staff_member_ref: Optional[object] = None  # Reference to original StaffMember

    @property
    def daily_progress(self) -> float:
        """1日あたりの調査進捗率 (%)"""
        # 5%前後になるように調整 (スキル50で5%)
        # スキル範囲1-99 -> 2.0% ~ 8.0% 程度
        return 2.0 + (self.skill * 0.06)


def get_scouts_from_team(team, scout_type: str = "all") -> List[Scout]:
    """
    チームのスタッフからスカウトを取得してScoutオブジェクトに変換
    team.staff が存在する場合はそこから取得、なければ空リストを返す
    
    Args:
        team: Team object
        scout_type: "all", "domestic", or "international"
    """
    from models import StaffRole
    
    if not team or not hasattr(team, 'staff') or not team.staff:
        return []
    
    scouts = []
    for staff in team.staff:
        if staff.is_scout:
            # Filter by type if specified
            if scout_type == "domestic" and staff.role != StaffRole.SCOUT_DOMESTIC:
                continue
            if scout_type == "international" and staff.role != StaffRole.SCOUT_INTERNATIONAL:
                continue
            
            # Create a Scout wrapper that references the StaffMember
            scout = Scout(
                name=staff.name,
                skill=staff.ability,
                specialty=staff.specialty or "汎用",
                is_available=staff.is_available,
                current_mission_id=staff.current_mission_id,
                staff_member_ref=staff
            )
            scouts.append(scout)
    return scouts


def sync_scout_to_staff(scout: Scout):
    """Sync Scout state back to its StaffMember reference"""
    if scout.staff_member_ref:
        scout.staff_member_ref.is_available = scout.is_available
        scout.staff_member_ref.current_mission_id = scout.current_mission_id


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

        # 総合力の推定 (実際のoverall計算を使用)
        if self.position == Position.PITCHER:
            true_overall = self.true_stats.overall_pitching()
        else:
            true_overall = self.true_stats.overall_batting(self.position)
        
        # 範囲を大きく（真の値が必ず範囲内に含まれるよう保証）
        range_half_width = int(50 * uncertainty) + 10  # 最低10の幅
        min_offset = random.randint(5, range_half_width)  # 最低5のオフセット
        max_offset = random.randint(5, range_half_width)
        
        min_ovr = max(1, true_overall - min_offset)
        max_ovr = min(999, true_overall + max_offset)
        
        # 最小幅を保証
        if (max_ovr - min_ovr) < 30:
            min_ovr = max(1, min_ovr - 15)
            max_ovr = min(999, max_ovr + 15)

        self._cached_est_overall_range = (min_ovr, max_ovr)

        # 潜在能力の推定（真の値が必ず範囲内に含まれるよう保証）
        true_pot = self.true_potential
        pot_uncertainty = max(0.3, uncertainty)
        pot_width = int(15 * pot_uncertainty) + 5  # 最低5の幅
        
        min_pot = max(1, true_pot - random.randint(3, pot_width))
        max_pot = min(99, true_pot + random.randint(3, pot_width))
        
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
        total_yen = self.get_total_cost()
        man = total_yen // 10000
        if man >= 10000:
            oku = man // 10000
            remainder = man % 10000
            return f"{oku}億{remainder}万" if remainder > 0 else f"{oku}億"
        return f"{man}万"

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
    def __init__(self, parent, candidate: ForeignPlayerCandidate, theme, is_developmental_tab: bool = False):
        super().__init__(parent)
        self.candidate = candidate
        self.theme = theme
        self.is_developmental_tab = is_developmental_tab  # 育成タブからの呼び出しか
        self.setWindowTitle("契約交渉")
        self.setFixedSize(600, 550)  # Increased size for text visibility
        self.setModal(True)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {self.theme.bg_card}; color: {self.theme.text_primary}; }}
            QLabel {{ color: {self.theme.text_primary}; }}
        """)
        
        self.offered_salary = 0
        self.offered_years = 0
        self.is_developmental = is_developmental_tab  # 育成タブならデフォルトON
        
        # 育成タブなら育成契約可能、そうでなければ支配下のみ
        self.can_be_developmental = is_developmental_tab
        
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
        # 年俸を億万形式で表示
        salary_yen = self.candidate.salary_demand
        sal_man = salary_yen // 10000
        if sal_man >= 10000:
            sal_oku = sal_man // 10000
            sal_rem = sal_man % 10000
            sal_text = f"{sal_oku}億{sal_rem}万" if sal_rem > 0 else f"{sal_oku}億"
        else:
            sal_text = f"{sal_man}万"
        
        bonus_yen = self.candidate.bonus_demand
        bon_man = bonus_yen // 10000
        if bon_man >= 10000:
            bon_oku = bon_man // 10000
            bon_rem = bon_man % 10000
            bon_text = f"{bon_oku}億{bon_rem}万" if bon_rem > 0 else f"{bon_oku}億"
        else:
            bon_text = f"{bon_man}万"
        
        demand_grid.addWidget(QLabel("希望年俸:"), 0, 0)
        demand_grid.addWidget(QLabel(sal_text), 0, 1)
        demand_grid.addWidget(QLabel("契約金:"), 1, 0)
        demand_grid.addWidget(QLabel(bon_text), 1, 1)
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
        
        # 育成契約チェックボックス（育成タブの場合のみ表示）
        from PySide6.QtWidgets import QCheckBox
        self.dev_checkbox = QCheckBox("育成契約で獲得する")
        self.dev_checkbox.setStyleSheet(f"color: {self.theme.text_primary}; margin-top: 8px;")
        
        if self.is_developmental_tab:
            # 育成タブ: チェックボックスを表示・デフォルトON
            self.dev_checkbox.setEnabled(True)
            self.dev_checkbox.setChecked(True)  # デフォルトON
            self.dev_checkbox.setToolTip("育成契約で獲得します")
            layout.addWidget(self.dev_checkbox)
        else:
            # 即戦力タブ: チェックボックスを非表示
            self.dev_checkbox.setVisible(False)
        
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
        is_developmental = self.dev_checkbox.isChecked()
        return salary, years, is_developmental


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
        self.game_state = None

        self._generate_dummy_data()
        self._setup_ui()
        
        # Hide initially to prevent appearing at (0,0) before being properly added to layout
        self.hide()

    def set_game_state(self, game_state):
        """ゲーム状態を設定し、スカウトを同期"""
        self.game_state = game_state
        
        # Sync domestic scouts from team.staff
        if game_state and game_state.player_team:
            domestic_scouts = get_scouts_from_team(game_state.player_team, "domestic")
            if domestic_scouts:
                self.scouts = domestic_scouts
                self._update_scout_combo()
                self._update_scout_status()

    def _generate_dummy_data(self):
        """データ生成 (300人)"""
        # スカウト生成 (fallback if no team.staff)
        if not self.scouts:
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
        sync_scout_to_staff(scout_data)  # Sync to StaffMember

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
        sync_scout_to_staff(scout)  # Sync to StaffMember

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
                    sync_scout_to_staff(prospect.assigned_scout)  # Sync to StaffMember
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
        
        # Sort by estimated potential (descending) so scouts pick the best prospects first
        unscouted.sort(key=lambda p: p.get_max_estimated_overall(), reverse=True)
        
        # Assign to first available (assuming list is roughly sorted by value/rank)
        for scout in free_scouts:
            if not unscouted:
                break
            
            target = unscouted.pop(0)
            target.assigned_scout = scout
            target.scouting_status = ScoutingStatus.IN_PROGRESS
            scout.is_available = False
            scout.current_mission_id = target.name
            sync_scout_to_staff(scout)  # Sync to StaffMember


# ========================================
# 2. Foreign Player Scouting Page
# ========================================

class ForeignPlayerScoutingPage(QWidget):
    """新外国人調査ページ"""

    player_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        # 二層システム: 即戦力候補と育成候補を分離
        self.main_roster_candidates: List[ForeignPlayerCandidate] = []    # 即戦力層
        self.developmental_candidates: List[ForeignPlayerCandidate] = []  # 育成層
        self.candidates: List[ForeignPlayerCandidate] = []  # 現在表示中の候補リスト（参照）
        self.scouts: List[Scout] = []
        self.selected_candidate: Optional[ForeignPlayerCandidate] = None
        self.game_state = None
        self.current_tab_mode = "main_roster"  # "main_roster" or "developmental"
        
        # New features
        self.negotiated_ids = set() # Set of candidate IDs negotiated with today
        self.last_reset_year = None # Last year we reset candidates

        self._setup_ui()
        self._generate_dummy_data()
        
        # Hide initially to prevent appearing at (0,0) before being properly added to layout
        self.hide()
    
    def set_game_state(self, game_state):
        """ゲーム状態を設定"""
        self.game_state = game_state
        
        # Sync international scouts from team.staff
        if game_state and game_state.player_team:
            international_scouts = get_scouts_from_team(game_state.player_team, "international")
            if international_scouts:
                self.scouts = international_scouts
                self._update_scout_combo()
                self._update_scout_status()
        
        self._update_detail_panel()

    def _generate_dummy_data(self):
        """ダミーデータ生成 (二層システム)"""
        # スカウトはgame_stateから取得するため、ここでは生成しない (fallbackのみ)
        # game_stateがまだない場合は外国人スカウト 4人 (専門分野なし) を生成
        if not self.scouts:
            scout_names = ["John Smith", "Mike Johnson", "Carlos Garcia", "Pedro Martinez"]
            for name in scout_names:
                self.scouts.append(Scout(
                    name=name,
                    skill=random.randint(55, 85),
                    specialty="汎用"
                ))

        # reset_candidatesを呼び出して候補を生成
        self.reset_candidates()
        
        # スカウトUIを更新
        self._update_scout_combo()
        self._update_scout_status()

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
        
        # タブ切り替えボタン
        self.main_roster_btn = QPushButton("即戦力")
        self.main_roster_btn.setCheckable(True)
        self.main_roster_btn.setChecked(True)
        self.main_roster_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.accent_blue};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }}
            QPushButton:!checked {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_secondary};
            }}
        """)
        self.main_roster_btn.clicked.connect(lambda: self._switch_tab("main_roster"))
        layout.addWidget(self.main_roster_btn)
        
        layout.addSpacing(4)
        
        self.developmental_btn = QPushButton("育成")
        self.developmental_btn.setCheckable(True)
        self.developmental_btn.setChecked(False)
        self.developmental_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.success};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }}
            QPushButton:!checked {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_secondary};
            }}
        """)
        self.developmental_btn.clicked.connect(lambda: self._switch_tab("developmental"))
        layout.addWidget(self.developmental_btn)
        
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
    
    def _switch_tab(self, mode: str):
        """タブ切り替え"""
        self.current_tab_mode = mode
        self.main_roster_btn.setChecked(mode == "main_roster")
        self.developmental_btn.setChecked(mode == "developmental")
        
        # 候補リストを切り替え
        if mode == "main_roster":
            self.candidates = self.main_roster_candidates
        else:
            self.candidates = self.developmental_candidates
        
        self.selected_candidate = None
        self._refresh_table()
        self._update_detail_panel()

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
        sync_scout_to_staff(scout_data)  # Sync to StaffMember

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
        sync_scout_to_staff(scout)  # Sync to StaffMember

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

        # ★支配下枚数チェック
        if self.game_state and self.game_state.player_team:
            team = self.game_state.player_team
            shihaika_count = len([p for p in team.players if not p.is_developmental])
            if shihaika_count >= 70:
                QMessageBox.warning(self, "支配下枚いっぱい", 
                    "支配下登録選手が70人に達しているため、\n新たな外国人選手との交渉を開始できません。\n先に選手を解雇または育成枚に降格してください。")
                return

        # Check negotiation limit
        if c.id in self.negotiated_ids:
            QMessageBox.warning(self, "交渉不可", "この選手とは本日すでに交渉済みです。")
            return

        # ★追加: 交渉画面(ダイアログ)を開く（育成タブかどうかを渡す）
        is_dev_tab = self.current_tab_mode == "developmental"
        dlg = ForeignNegotiationDialog(self, c, self.theme, is_developmental_tab=is_dev_tab)
        if dlg.exec() != QDialog.Accepted:
            return
            
        # Add to negotiated set (consumed daily attempt)
        self.negotiated_ids.add(c.id)

        # ダイアログから値を取得 (育成契約フラグ追加)
        offered_salary_val, offered_years, is_developmental_contract = dlg.get_values()
        offered_salary = offered_salary_val * 1000000

        # 育成契約の場合の特別処理
        if is_developmental_contract:
            # 能力280以上は育成契約不可（成功率0%）
            if not getattr(c, 'is_developmental_candidate', False):
                QMessageBox.warning(self, "育成契約不可", 
                    f"{c.name}は即戦力級の選手のため、育成契約での獲得はできません。\n"
                    "支配下契約での獲得をお試しください。")
                return
            # 育成契約は高い成功率
            success_chance = 70 + (offered_salary_val // 100) * 5  # 年俸提示に応じてボーナス
            success_chance = min(95, success_chance)
        else:
            # 支配下契約の通常処理
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
                
                # 育成契約でない場合のみ支配下枠チェック
                if not is_developmental_contract:
                    MAX_SHIHAIKA = 70
                    shihaika_count = len([p for p in self.game_state.player_team.players if not p.is_developmental])
                    if shihaika_count >= MAX_SHIHAIKA:
                        QMessageBox.warning(self, "登録枠超過", 
                            f"支配下登録枠({MAX_SHIHAIKA}人)が一杯です。\n"
                            "先に選手を自由契約にするか、トレードで放出してください。")
                        return
                
                # Create Player from candidate
                new_player = Player(
                    name=c.name,
                    position=c.position,
                    age=c.age,
                    stats=c.true_stats,
                    pitch_type=c.pitch_type,
                    uniform_number=self._get_available_uniform_number() if not is_developmental_contract else random.randint(101, 199),
                    is_foreign=True
                )
                new_player.salary = offered_salary
                new_player.contract_years = offered_years
                new_player.potential = c.true_potential
                new_player.is_developmental = is_developmental_contract
                
                # Add to player's team
                self.game_state.player_team.players.append(new_player)
                
                contract_type = "育成" if is_developmental_contract else "支配下"
                # 年俸を億万形式で表示
                sal_man = offered_salary // 10000
                if sal_man >= 10000:
                    sal_oku = sal_man // 10000
                    sal_rem = sal_man % 10000
                    sal_text = f"{sal_oku}億{sal_rem}万" if sal_rem > 0 else f"{sal_oku}億"
                else:
                    sal_text = f"{sal_man}万"
                QMessageBox.information(self, "契約成功",
                    f"{c.name}との{contract_type}契約が成立！\n"
                    f"年俸: {sal_text} / {offered_years}年契約\n"
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
        """Reset and regenerate foreign candidates (二層システム)"""
        self.main_roster_candidates.clear()
        self.developmental_candidates.clear()
        self.selected_candidate = None
        
        countries = ["USA", "Dominican", "Cuba", "Venezuela", "Mexico", "Korea", "Taiwan", "Puerto Rico", "Canada", "Australia"]
        positions = [Position.PITCHER, Position.FIRST, Position.LEFT,
                    Position.RIGHT, Position.CENTER, Position.SHORTSTOP, Position.THIRD, Position.SECOND, Position.CATCHER]
        
        # 即戦力層を生成 (70人)
        for i in range(70):
            pos = random.choice(positions)
            # 強制的に即戦力層を生成 (年齢26-35)
            gen_player = self._generate_main_roster_candidate(pos)
            
            country = random.choice(countries)
            salary = gen_player.salary
            bonus = gen_player.contract_bonus
            
            if gen_player.age < 30: pot_base = 55
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
            candidate.is_developmental_candidate = False
            self.main_roster_candidates.append(candidate)
        
        # 育成層を生成 (30人)
        for i in range(30):
            pos = random.choice(positions)
            # 強制的に育成層を生成 (年齢18-25)
            gen_player = self._generate_developmental_candidate(pos)
            
            country = random.choice(countries)
            salary = gen_player.salary
            bonus = gen_player.contract_bonus
            
            if gen_player.age < 22: pot_base = 70
            elif gen_player.age < 24: pot_base = 65
            else: pot_base = 55
            pot = max(1, min(99, int(random.gauss(pot_base, 15))))

            candidate = ForeignPlayerCandidate(
                id=50 + i,  # IDが被らないようにオフセット
                name=gen_player.name,
                position=gen_player.position,
                pitch_type=gen_player.pitch_type,
                age=gen_player.age,
                country=country,
                true_stats=gen_player.stats,
                true_potential=pot,
                salary_demand=salary,
                bonus_demand=bonus,
                years_demand=random.choice([1, 1, 2]),
                interest_level=random.randint(30, 80)
            )
            candidate.is_developmental_candidate = True
            self.developmental_candidates.append(candidate)
        
        # 現在のタブに応じて表示リストを設定
        if self.current_tab_mode == "main_roster":
            self.candidates = self.main_roster_candidates
        else:
            self.candidates = self.developmental_candidates
            
        self._refresh_table()
        self._update_detail_panel()
        
        # Record reset year if needed
        if self.game_state and self.game_state.current_date:
            try:
                self.last_reset_year = int(self.game_state.current_date.split('-')[0])
            except: pass
    
    def _generate_main_roster_candidate(self, pos: Position):
        """即戦力外国人を生成 (年齢26-35, 総合力330+)"""
        import player_generator
        from models import Position as ModelPosition
        # create_foreign_free_agentを呼び出すが、確実に即戦力層になるまで再試行
        for _ in range(20):
            player = player_generator.create_foreign_free_agent(pos)
            # 年齢と総合力の両方をチェック
            if pos == ModelPosition.PITCHER:
                overall = player.stats.overall_pitching()
            else:
                overall = player.stats.overall_batting(pos)
            if player.age >= 26 and overall >= 330:
                return player
        # 20回試してダメなら最後のものを使う（年齢だけ調整）
        player.age = max(26, player.age)
        return player
    
    def _generate_developmental_candidate(self, pos: Position):
        """育成外国人を生成 (年齢18-25, 総合力330未満)"""
        import player_generator
        from models import Position as ModelPosition
        # create_foreign_free_agentを呼び出すが、確実に育成層になるまで再試行
        for _ in range(20):
            player = player_generator.create_foreign_free_agent(pos)
            # 年齢と総合力の両方をチェック
            if pos == ModelPosition.PITCHER:
                overall = player.stats.overall_pitching()
            else:
                overall = player.stats.overall_batting(pos)
            if player.age <= 25 and overall < 330:
                return player
        # 20回試してダメなら最後のものを使う（年齢だけ調整）
        player.age = min(25, player.age)
        return player

    def advance_day(self):
        # Clear daily negotiation limit
        self.negotiated_ids.clear()
        
        # Auto-assign unassigned scouts to best candidates
        self._auto_assign_scouts()
        
        # 両方のリストを更新 (即戦力と育成)
        all_candidates = self.main_roster_candidates + self.developmental_candidates
        for candidate in all_candidates:
            if candidate.scouting_status == ScoutingStatus.IN_PROGRESS and candidate.assigned_scout:
                progress = candidate.assigned_scout.daily_progress
                candidate.scout_level = min(100, candidate.scout_level + progress)

                if candidate.scout_level >= 100:
                    candidate.scouting_status = ScoutingStatus.COMPLETED
                    candidate.assigned_scout.is_available = True
                    candidate.assigned_scout.current_mission_id = None
                    sync_scout_to_staff(candidate.assigned_scout)  # Sync to StaffMember
                    candidate.assigned_scout = None
                
                candidate.recalculate_estimates()

        self._update_scout_combo()
        self._update_scout_status()
        self._refresh_table()
        if self.selected_candidate:
            self._update_detail_panel()
    
    def _auto_assign_scouts(self):
        """Automatically assign free scouts to the best unassigned candidates (両リストから均等に)"""
        # Get free scouts
        free_scouts = [s for s in self.scouts if s.is_available]
        if not free_scouts:
            return
        
        # 両方のリストから未調査候補を取得
        main_unscouted = [c for c in self.main_roster_candidates 
                         if c.scouting_status == ScoutingStatus.NOT_STARTED 
                         and not c.assigned_scout]
        dev_unscouted = [c for c in self.developmental_candidates 
                        if c.scouting_status == ScoutingStatus.NOT_STARTED 
                        and not c.assigned_scout]
        
        # 即戦力を優先してソート (推定能力順)
        main_unscouted.sort(key=lambda x: x.get_max_estimated_overall(), reverse=True)
        dev_unscouted.sort(key=lambda x: x.get_max_estimated_overall(), reverse=True)
        
        # 交互に割り当て (即戦力優先: 2:1の比率)
        unscouted_queue = []
        main_idx, dev_idx = 0, 0
        while main_idx < len(main_unscouted) or dev_idx < len(dev_unscouted):
            # 即戦力を2つ追加
            for _ in range(2):
                if main_idx < len(main_unscouted):
                    unscouted_queue.append(main_unscouted[main_idx])
                    main_idx += 1
            # 育成を1つ追加
            if dev_idx < len(dev_unscouted):
                unscouted_queue.append(dev_unscouted[dev_idx])
                dev_idx += 1
        
        # Assign scouts to top candidates
        for scout in free_scouts:
            if not unscouted_queue:
                break
            
            candidate = unscouted_queue.pop(0)
            candidate.assigned_scout = scout
            candidate.scouting_status = ScoutingStatus.IN_PROGRESS
            scout.is_available = False
            scout.current_mission_id = candidate.name
            sync_scout_to_staff(scout)  # Sync to StaffMember


# ========================================
# 3. Trade Page
# ========================================

class DragPlayerTable(QTableWidget):
    """ドラッグ時にplayer_idxとチーム情報をmimeDataに含めるテーブル"""
    row_double_clicked = Signal(int)
    
    # ソート不可列: 0=名前, 1=Pos
    NON_SORTABLE_COLS = [0, 1]
    
    def __init__(self, parent=None, is_self_team=True):
        super().__init__(parent)
        self.theme = get_theme()
        self.is_self_team = is_self_team  # True=自チーム, False=相手チーム
        self.setDragEnabled(True)
        self.setAcceptDrops(False)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        # 手動ソート制御（特定列のソートを無効化するため）
        self.setSortingEnabled(False)
        self.horizontalHeader().setSectionsClickable(True)
        self.horizontalHeader().setSortIndicatorShown(True)
        self.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self._sort_col = -1
        self._sort_order = Qt.DescendingOrder
        
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.verticalHeader().setVisible(False)
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.theme.bg_card};
                color: {self.theme.text_primary};
                border: none;
                gridline-color: {self.theme.border};
            }}
            QTableWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {self.theme.border};
            }}
            QTableWidget::item:selected {{
                background-color: {self.theme.accent_blue};
                color: white;
            }}
            QHeaderView::section {{
                background-color: {self.theme.bg_card_elevated};
                color: {self.theme.text_secondary};
                padding: 6px;
                border: none;
                font-weight: bold;
            }}
        """)
    
    def _on_header_clicked(self, logicalIndex: int):
        """カラムヘッダークリック時のソート処理"""
        # 名前・ポジション列はソート不可
        if logicalIndex in self.NON_SORTABLE_COLS:
            return
        
        # 同じ列ならトグル、違う列ならデフォルト降順
        if self._sort_col == logicalIndex:
            if self._sort_order == Qt.DescendingOrder:
                self._sort_order = Qt.AscendingOrder
            else:
                self._sort_order = Qt.DescendingOrder
        else:
            self._sort_col = logicalIndex
            self._sort_order = Qt.DescendingOrder
        
        self.sortItems(self._sort_col, self._sort_order)
        self.horizontalHeader().setSortIndicator(self._sort_col, self._sort_order)
    
    def startDrag(self, supportedActions):
        """Override to provide player_idx and team info in mime data with visual"""
        row = self.currentRow()
        if row < 0:
            return
        
        name_item = self.item(row, 0)
        if not name_item:
            return
        
        player_idx = name_item.data(Qt.UserRole)
        if player_idx is None:
            return
        
        # プレイヤー名を取得
        player_name = name_item.text()
        
        drag = QDrag(self)
        mime_data = QMimeData()
        # フォーマット: "player_idx:is_self_team" (例: "5:True")
        mime_data.setText(f"{player_idx}:{self.is_self_team}")
        drag.setMimeData(mime_data)
        
        # ドラッグ中に表示するピクスマップを作成
        from PySide6.QtGui import QPixmap
        pixmap = QPixmap(150, 30)
        pixmap.fill(QColor(self.theme.bg_card_elevated))
        painter = QPainter(pixmap)
        painter.setPen(QColor(self.theme.text_primary))
        painter.setFont(QFont("Meiryo", 10, QFont.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, player_name)
        painter.end()
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())
        
        drag.exec(Qt.CopyAction)


class DropZoneFrame(QFrame):
    """ドロップを受け付けるフレーム（チーム検証付き）"""
    player_dropped = Signal(int)  # player_idx
    
    def __init__(self, parent=None, accepts_self_team=True):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.theme = get_theme()
        self.accepts_self_team = accepts_self_team  # True=自チーム選手のみ受け付け
        self._normal_style = ""
        self._hover_style = ""
    
    def set_styles(self, normal: str, hover: str):
        self._normal_style = normal
        self._hover_style = hover
        self.setStyleSheet(normal)
    
    def _parse_mime_data(self, mime_data):
        """mimeDataをパースしてplayer_idxとis_self_teamを返す"""
        if not mime_data.hasText():
            return None, None
        text = mime_data.text()
        try:
            parts = text.split(":")
            if len(parts) == 2:
                player_idx = int(parts[0])
                is_self_team = parts[1] == "True"
                return player_idx, is_self_team
        except ValueError:
            pass
        return None, None
    
    def dragEnterEvent(self, event):
        player_idx, is_self_team = self._parse_mime_data(event.mimeData())
        if player_idx is None:
            event.ignore()
            return
        
        # チーム検証: 自チームゾーンには自チーム、相手ゾーンには相手チームのみ
        if is_self_team == self.accepts_self_team:
            event.acceptProposedAction()
            self.setStyleSheet(self._hover_style)
        else:
            # 不正なチーム→無視（禁止カーソルなし）
            event.ignore()
    
    def dragLeaveEvent(self, event):
        self.setStyleSheet(self._normal_style)
    
    def dropEvent(self, event):
        self.setStyleSheet(self._normal_style)
        player_idx, is_self_team = self._parse_mime_data(event.mimeData())
        
        if player_idx is None:
            event.ignore()
            return
        
        # チーム検証
        if is_self_team == self.accepts_self_team:
            self.player_dropped.emit(player_idx)
            event.acceptProposedAction()
        else:
            event.ignore()

class TradePage(QWidget):
    """トレードページ (Order Page Style - 完全リニューアル)
    
    特徴:
    - 各チーム最大3選手まで
    - 金銭調整（100万円単位）
    - 支配下70人制限チェック
    - ドラッグ＆ドロップ選手選択
    - ダブルクリックで選手詳細へ
    - 総合力ソート・ポジション絞り込み
    """
    
    player_detail_requested = Signal(object)  # 選手詳細画面へ遷移
    
    MAX_TRADE_PLAYERS = 3  # 各チーム最大選手数
    MAX_SHIHAIKA = 70  # 支配下登録上限
    MONEY_UNIT = 1000000  # 100万円単位

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.current_team = None
        self.target_team = None

        self.offered_players: List[int] = []  # 自チームから放出する選手
        self.requested_players: List[int] = []  # 相手チームから獲得する選手
        self.money_adjustment: int = 0  # 自チームが支払う金額（負なら受け取る）

        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ツールバー
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # メインコンテンツ（3カラム）
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {self.theme.border}; width: 2px; }}")

        # 左: 自チーム選手リスト
        left_panel = self._create_player_list_panel("自チーム", is_self=True)
        splitter.addWidget(left_panel)

        # 中央: トレード内容
        center_panel = self._create_trade_content_panel()
        splitter.addWidget(center_panel)

        # 右: 相手チーム選手リスト
        right_panel = self._create_player_list_panel("相手チーム", is_self=False)
        splitter.addWidget(right_panel)

        splitter.setSizes([350, 300, 350])
        layout.addWidget(splitter)

    def _create_toolbar(self) -> QWidget:
        toolbar = QFrame()
        toolbar.setFixedHeight(55)
        toolbar.setStyleSheet(f"background-color: {self.theme.bg_card}; border-bottom: 1px solid {self.theme.border};")

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(16, 0, 16, 0)

        # タイトル
        title = QLabel("トレード")
        title.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; font-size: 18px;")
        layout.addWidget(title)

        # トレード承認待ちステータス
        self.pending_status_label = QLabel("")
        self.pending_status_label.setStyleSheet(f"color: {self.theme.warning}; font-weight: bold; background-color: {self.theme.bg_dark}; padding: 4px 8px; border-radius: 4px;")
        self.pending_status_label.hide()
        layout.addWidget(self.pending_status_label)
        
        layout.addSpacing(20)

        # 相手チーム選択
        layout.addWidget(QLabel("相手チーム:"))
        self.team_combo = QComboBox()
        self.team_combo.setMinimumWidth(180)
        self.team_combo.setStyleSheet(f"""
            QComboBox {{
                background: {self.theme.bg_input}; 
                color: {self.theme.text_primary}; 
                border: 1px solid {self.theme.border}; 
                padding: 6px 12px;
                border-radius: 4px;
            }}
        """)
        self.team_combo.currentIndexChanged.connect(self._on_target_team_changed)
        layout.addWidget(self.team_combo)

        layout.addStretch()

        # 支配下人数表示
        self.roster_info_label = QLabel("支配下: --/70人")
        self.roster_info_label.setStyleSheet(f"color: {self.theme.text_secondary}; font-weight: bold;")
        layout.addWidget(self.roster_info_label)

        layout.addSpacing(20)

        # トレード提案ボタン
        self.trade_btn = QPushButton("トレード提案")
        self.trade_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.primary};
                color: {self.theme.text_highlight};
                border: none;
                border-radius: 4px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.primary_hover};
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
                background-color: transparent;
                color: {self.theme.error};
                border: 1px solid {self.theme.error};
                border-radius: 4px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.error}22;
            }}
        """)
        clear_btn.clicked.connect(self._clear_trade)
        layout.addWidget(clear_btn)

        return toolbar

    def _create_player_list_panel(self, title: str, is_self: bool) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ヘッダー
        color = self.theme.accent_blue if is_self else self.theme.accent_orange
        header = QLabel(title)
        header.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")
        layout.addWidget(header)

        # フィルターのみ（ソートはヘッダークリック）
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(6)

        # ポジションフィルター
        pos_combo = QComboBox()
        pos_combo.addItem("全ポジション", None)
        pos_combo.addItem("投手", "投手")
        pos_combo.addItem("捕手", "捕手")
        pos_combo.addItem("内野手", "内野手")
        pos_combo.addItem("外野手", "外野手")
        pos_combo.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 3px;")
        pos_combo.setMaximumWidth(100)
        filter_layout.addWidget(pos_combo)
        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # 選手テーブル (ドラッグ専用 - DragPlayerTable使用)
        table = DragPlayerTable(is_self_team=is_self)
        
        cols = ["名前", "Pos", "年齢", "総合", "年俸"]
        widths = [100, 35, 35, 50, 70]
        
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        for i, w in enumerate(widths):
            table.setColumnWidth(i, w)
        
        # 最後の列を広げてスペースを消す
        table.horizontalHeader().setStretchLastSection(True)

        # ダブルクリックで選手詳細へ
        table.itemDoubleClicked.connect(lambda item: self._on_player_table_double_clicked(item, is_self))

        if is_self:
            self.self_table = table
            self.self_pos_filter = pos_combo
            pos_combo.currentIndexChanged.connect(lambda: self._apply_filter(is_self=True))
        else:
            self.target_table = table
            self.target_pos_filter = pos_combo
            pos_combo.currentIndexChanged.connect(lambda: self._apply_filter(is_self=False))

        layout.addWidget(table)
        
        return panel

    def _on_player_table_double_clicked(self, item, is_self: bool):
        """ダブルクリックで選手詳細画面へ"""
        if item is None:
            return
        row = item.row()
        team = self.current_team if is_self else self.target_team
        table = self.self_table if is_self else self.target_table
        
        if not team:
            return
            
        name_item = table.item(row, 0)
        if name_item:
            player_idx = name_item.data(Qt.UserRole)
            if player_idx is not None and 0 <= player_idx < len(team.players):
                player = team.players[player_idx]
                self.player_detail_requested.emit(player)

    def _apply_filter(self, is_self: bool):
        """ソート・フィルターを適用してテーブルを再描画"""
        if is_self:
            self._refresh_self_table()
        else:
            self._refresh_target_table()

    def _create_trade_content_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(f"background-color: {self.theme.bg_card};")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # --- 自チーム放出 ---
        self_header = QLabel("▼ 放出選手（自チーム）")
        self_header.setStyleSheet(f"color: {self.theme.accent_blue}; font-weight: bold;")
        layout.addWidget(self_header)

        self.self_offer_list = DropZoneFrame(accepts_self_team=True)  # 自チーム選手のみ受け付け
        normal_style = f"background-color: {self.theme.bg_input};"
        hover_style = f"background-color: {self.theme.accent_blue}; border: 2px dashed white;"
        self.self_offer_list.set_styles(normal_style, hover_style)
        self.self_offer_list.setMinimumHeight(100)
        self.self_offer_list.player_dropped.connect(lambda idx: self._on_drop_player(idx, is_self=True))
        self.self_offer_layout = QVBoxLayout(self.self_offer_list)
        self.self_offer_layout.setContentsMargins(8, 8, 8, 8)
        self.self_offer_layout.setSpacing(4)
        
        self.self_offer_placeholder = QLabel("ここにドラッグして放出選手を追加（最大3人）")
        self.self_offer_placeholder.setStyleSheet(f"color: {self.theme.text_muted}; font-style: italic;")
        self.self_offer_placeholder.setAlignment(Qt.AlignCenter)
        self.self_offer_layout.addWidget(self.self_offer_placeholder)
        
        layout.addWidget(self.self_offer_list)

        # --- 金銭調整 ---
        money_frame = QFrame()
        money_frame.setStyleSheet(f"background-color: {self.theme.bg_card_elevated};")
        money_layout = QVBoxLayout(money_frame)
        money_layout.setContentsMargins(10, 10, 10, 10)
        money_layout.setSpacing(6)

        money_header = QLabel("金銭調整")
        money_header.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold;")
        money_layout.addWidget(money_header)

        money_input_layout = QHBoxLayout()
        money_input_layout.setSpacing(4)

        # QLineEditに変更（編集可能な数値入力）
        self.money_input = QLineEdit()
        self.money_input.setText("0")
        self.money_input.setAlignment(Qt.AlignRight)
        self.money_input.setMaximumWidth(100)
        self.money_input.setStyleSheet(f"""
            QLineEdit {{
                background: {self.theme.bg_input};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                padding: 6px;
                border-radius: 4px;
            }}
        """)
        self.money_input.textChanged.connect(self._on_money_text_changed)
        money_input_layout.addWidget(self.money_input)
        
        # 単位を外に表示
        money_unit_label = QLabel("百万円")
        money_unit_label.setStyleSheet(f"color: {self.theme.text_secondary};")
        money_input_layout.addWidget(money_unit_label)
        
        money_input_layout.addStretch()
        money_layout.addLayout(money_input_layout)

        self.money_desc_label = QLabel("正: 自チーム支払い / 負: 自チーム受取")
        self.money_desc_label.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 11px;")
        money_layout.addWidget(self.money_desc_label)

        layout.addWidget(money_frame)

        # --- 相手チーム獲得 ---
        target_header = QLabel("▲ 獲得選手（相手チーム）")
        target_header.setStyleSheet(f"color: {self.theme.accent_orange}; font-weight: bold;")
        layout.addWidget(target_header)

        self.target_offer_list = DropZoneFrame(accepts_self_team=False)  # 相手チーム選手のみ受け付け
        target_normal = f"background-color: {self.theme.bg_input};"
        target_hover = f"background-color: {self.theme.accent_orange}; border: 2px dashed white;"
        self.target_offer_list.set_styles(target_normal, target_hover)
        self.target_offer_list.setMinimumHeight(100)
        self.target_offer_list.player_dropped.connect(lambda idx: self._on_drop_player(idx, is_self=False))
        self.target_offer_layout = QVBoxLayout(self.target_offer_list)
        self.target_offer_layout.setContentsMargins(8, 8, 8, 8)
        self.target_offer_layout.setSpacing(4)
        
        self.target_offer_placeholder = QLabel("ここにドラッグして獲得選手を追加（最大3人）")
        self.target_offer_placeholder.setStyleSheet(f"color: {self.theme.text_muted}; font-style: italic;")
        self.target_offer_placeholder.setAlignment(Qt.AlignCenter)
        self.target_offer_layout.addWidget(self.target_offer_placeholder)
        
        layout.addWidget(self.target_offer_list)

        # --- 評価バランス ---
        balance_frame = QFrame()
        balance_frame.setStyleSheet(f"background-color: {self.theme.bg_dark};")
        balance_layout = QVBoxLayout(balance_frame)
        balance_layout.setContentsMargins(10, 10, 10, 10)

        self.balance_label = QLabel("評価差: 0")
        self.balance_label.setAlignment(Qt.AlignCenter)
        self.balance_label.setStyleSheet(f"color: {self.theme.text_primary}; font-size: 16px; font-weight: bold;")
        balance_layout.addWidget(self.balance_label)

        self.balance_indicator = QLabel("---")
        self.balance_indicator.setAlignment(Qt.AlignCenter)
        self.balance_indicator.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 13px;")
        balance_layout.addWidget(self.balance_indicator)

        self.success_rate_label = QLabel("成功率: --%")
        self.success_rate_label.setAlignment(Qt.AlignCenter)
        self.success_rate_label.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 12px;")
        balance_layout.addWidget(self.success_rate_label)

        layout.addWidget(balance_frame)
        layout.addStretch()

        return panel
    
    def _on_money_text_changed(self, text: str):
        """金銭入力テキスト変更時"""
        try:
            value = int(text) if text else 0
            self.money_adjustment = value * self.MONEY_UNIT
        except ValueError:
            self.money_adjustment = 0
        self._update_trade_balance()

    def set_game_state(self, game_state):
        """ゲーム状態を設定"""
        self.game_state = game_state
        if game_state and game_state.player_team:
            self.current_team = game_state.player_team
            self._update_team_combo()
            self._refresh_self_table()
            self.current_team = game_state.player_team
            self._update_team_combo()
            self._refresh_self_table()
            self._update_roster_info()
            self._check_pending_trade()

    def _check_pending_trade(self):
        """承認待ちトレードがあるかチェックしてUI更新"""
        if not self.game_state or not self.current_team:
            return

        # 自チームが関わる承認待ちトレードを探す
        pending = next((t for t in self.game_state.pending_trades 
                       if t.offering_team_name == self.current_team.name), None)
        
        if pending:
            self.pending_status_label.setText(f"申請中: 残り{pending.days_remaining}日")
            self.pending_status_label.show()
            self.trade_btn.setEnabled(False)
            self.trade_btn.setText("申請中")
            self.trade_btn.setToolTip("現在進行中のトレード交渉があります")
            
            # 入力系の無効化
            self.team_combo.setEnabled(False)
            self.self_offer_list.setEnabled(False)
            self.target_offer_list.setEnabled(False)
            self.money_input.setEnabled(False)
            
            # 相手チームを合わせる
            idx = self.team_combo.findText(pending.target_team_name)
            if idx >= 0:
                self.team_combo.setCurrentIndex(idx)
                
            # TODO: 申請中の内容を表示復元できるとベストだが、今回はロックのみ
            
        else:
            self.pending_status_label.hide()
            self.trade_btn.setText("トレード提案")
            self.trade_btn.setToolTip("")
            
            self.team_combo.setEnabled(True)
            self.self_offer_list.setEnabled(True)
            self.target_offer_list.setEnabled(True)
            self.money_input.setEnabled(True)
            
            self._update_trade_balance() # ボタン有効無効の再計算


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

    def _update_roster_info(self):
        """支配下人数表示を更新"""
        if not self.current_team:
            self.roster_info_label.setText("支配下: --/70人")
            return
        
        shihaika = len([p for p in self.current_team.players if not p.is_developmental])
        color = self.theme.success if shihaika < self.MAX_SHIHAIKA else self.theme.danger
        self.roster_info_label.setText(f"支配下: <span style='color:{color}'>{shihaika}</span>/{self.MAX_SHIHAIKA}人")

    def _refresh_self_table(self):
        """自チームテーブルを更新（フィルター適用）"""
        if not self.current_team:
            return
        players = [p for p in self.current_team.players if not p.is_developmental]
        
        # ポジションフィルター適用
        if hasattr(self, 'self_pos_filter'):
            pos_filter = self.self_pos_filter.currentData()
            if pos_filter:
                players = [p for p in players if self._match_position_filter(p, pos_filter)]
        
        # ソートはテーブルヘッダークリックでQtが処理
        self._fill_player_table(self.self_table, players, self.current_team)

    def _refresh_target_table(self):
        """相手チームテーブルを更新（フィルター適用）"""
        if not self.target_team:
            self.target_table.setRowCount(0)
            return
        players = [p for p in self.target_team.players if not p.is_developmental]
        
        # ポジションフィルター適用
        if hasattr(self, 'target_pos_filter'):
            pos_filter = self.target_pos_filter.currentData()
            if pos_filter:
                players = [p for p in players if self._match_position_filter(p, pos_filter)]
        
        # ソートはテーブルヘッダークリックでQtが処理
        self._fill_player_table(self.target_table, players, self.target_team)
    
    def _match_position_filter(self, player, filter_name: str) -> bool:
        """ポジションフィルターに一致するか"""
        pos_str = short_pos_name(player.position)
        if filter_name == "投手":
            return pos_str == "投"
        elif filter_name == "捕手":
            return pos_str == "捕"
        elif filter_name == "内野手":
            return pos_str in ["一", "二", "三", "遊"]
        elif filter_name == "外野手":
            return pos_str in ["左", "中", "右", "外"]
        return True

    def _fill_player_table(self, table: DragPlayerTable, players: List[Player], team: Team):
        """選手テーブルを埋める（SortableTableWidgetItem使用）"""
        table.setRowCount(len(players))

        for row, player in enumerate(players):
            player_idx = team.players.index(player)

            # 名前 (ソート不可だがplayer_idxを保持)
            name_item = SortableTableWidgetItem(player.name)
            name_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            name_item.setData(Qt.UserRole, player_idx)
            table.setItem(row, 0, name_item)

            # ポジション (ソート不可)
            pos_item = SortableTableWidgetItem(short_pos_name(player.position))
            pos_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 1, pos_item)

            # 年齢 (数値ソート用にUserRoleに値設定)
            age_item = SortableTableWidgetItem(str(player.age))
            age_item.setData(Qt.UserRole, player.age)
            age_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 2, age_item)

            # 総合 (★ゴールド表記、数値ソート用)
            ovr = player.overall_rating
            ovr_item = SortableTableWidgetItem(f"★{ovr}")
            ovr_item.setData(Qt.UserRole, ovr)
            ovr_item.setForeground(QColor("#FFD700"))  # ゴールド
            font = ovr_item.font()
            font.setBold(True)
            ovr_item.setFont(font)
            ovr_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 3, ovr_item)

            # 年俸（億万表記）
            salary_yen = getattr(player, 'salary', 0)
            sal_man = salary_yen // 10000
            if sal_man >= 10000:
                sal_oku = sal_man // 10000
                sal_rem = sal_man % 10000
                salary_text = f"{sal_oku}億{sal_rem}万" if sal_rem > 0 else f"{sal_oku}億"
            else:
                salary_text = f"{sal_man}万"
            salary_item = SortableTableWidgetItem(salary_text)
            salary_item.setData(Qt.UserRole, salary_yen)
            salary_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 4, salary_item)

    def _on_drop_player(self, player_idx: int, is_self: bool):
        """ドロップ時に選手をトレード対象に追加"""
        if is_self:
            offer_list = self.offered_players
            team = self.current_team
        else:
            offer_list = self.requested_players
            team = self.target_team
        
        if not team:
            return
            
        if player_idx is None or player_idx in offer_list:
            return
        
        if len(offer_list) >= self.MAX_TRADE_PLAYERS:
            QMessageBox.warning(self, "上限", f"一度にトレードできる選手は{self.MAX_TRADE_PLAYERS}人までです。")
            return
        
        offer_list.append(player_idx)
        self._refresh_offer_display()
        self._update_trade_balance()

    def _add_to_offer(self, row: int, is_self: bool):
        """選手をトレード対象に追加"""
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

        if len(offer_list) >= self.MAX_TRADE_PLAYERS:
            QMessageBox.warning(self, "上限", f"一度にトレードできる選手は{self.MAX_TRADE_PLAYERS}人までです。")
            return

        offer_list.append(player_idx)
        self._refresh_offer_display()
        self._update_trade_balance()

    def _remove_from_offer(self, player_idx: int, is_self: bool):
        """選手をトレード対象から削除"""
        if is_self:
            offer_list = self.offered_players
        else:
            offer_list = self.requested_players

        if player_idx in offer_list:
            offer_list.remove(player_idx)

        self._refresh_offer_display()
        self._update_trade_balance()

    def _refresh_offer_display(self):
        """トレード対象表示を更新"""
        # 自チーム
        self._clear_offer_layout(self.self_offer_layout)
        if self.offered_players and self.current_team:
            self.self_offer_placeholder.hide()
            for idx in self.offered_players:
                if 0 <= idx < len(self.current_team.players):
                    p = self.current_team.players[idx]
                    row = self._create_offer_row(p, idx, is_self=True)
                    self.self_offer_layout.addWidget(row)
        else:
            self.self_offer_placeholder.show()

        # 相手チーム
        self._clear_offer_layout(self.target_offer_layout)
        if self.requested_players and self.target_team:
            self.target_offer_placeholder.hide()
            for idx in self.requested_players:
                if 0 <= idx < len(self.target_team.players):
                    p = self.target_team.players[idx]
                    row = self._create_offer_row(p, idx, is_self=False)
                    self.target_offer_layout.addWidget(row)
        else:
            self.target_offer_placeholder.show()

    def _clear_offer_layout(self, layout):
        """レイアウト内のウィジェットをクリア（プレースホルダー以外）"""
        for i in reversed(range(layout.count())):
            widget = layout.itemAt(i).widget()
            if widget and widget not in (self.self_offer_placeholder, self.target_offer_placeholder):
                widget.deleteLater()

    def _create_offer_row(self, player, player_idx: int, is_self: bool) -> QWidget:
        """トレード対象選手の行を作成"""
        row = QFrame()
        row.setStyleSheet(f"background-color: {self.theme.bg_card}; border-radius: 3px;")
        
        layout = QHBoxLayout(row)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # 選手情報
        info = QLabel(f"{player.name} ({short_pos_name(player.position)}) ★{player.overall_rating}")
        info.setStyleSheet(f"color: {self.theme.text_primary};")
        layout.addWidget(info)

        layout.addStretch()

        # 削除ボタン
        remove_btn = QPushButton("×")
        remove_btn.setFixedSize(24, 24)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.danger};
                color: white;
                border: none;
                border-radius: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme.danger_hover};
            }}
        """)
        remove_btn.clicked.connect(lambda: self._remove_from_offer(player_idx, is_self))
        layout.addWidget(remove_btn)

        return row

    def _on_money_changed(self, value):
        """金銭調整値が変更された"""
        self.money_adjustment = value * self.MONEY_UNIT
        self._update_trade_balance()

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

        # 金銭を評価値に換算（1億円 = 10ポイント）
        money_value = self.money_adjustment // 10000000  # 1億円単位

        # 自チームが支払う金銭は自チーム評価に加算
        adjusted_self = self_value + money_value

        diff = adjusted_self - target_value
        self.balance_label.setText(f"評価差: {diff:+d}")

        # 成功率計算
        if diff >= 100:
            base_chance = 95
        elif diff >= 50:
            base_chance = 80
        elif diff >= 20:
            base_chance = 65
        elif diff >= 0:
            base_chance = 50
        elif diff >= -20:
            base_chance = 35
        elif diff >= -50:
            base_chance = 20
        else:
            base_chance = 5

        if diff >= 50:
            self.balance_indicator.setText("相手有利 (高確率)")
            self.balance_indicator.setStyleSheet(f"color: {self.theme.success}; font-size: 13px;")
        elif diff >= 10:
            self.balance_indicator.setText("やや相手有利")
            self.balance_indicator.setStyleSheet(f"color: {self.theme.success}; font-size: 13px;")
        elif diff >= -10:
            self.balance_indicator.setText("均衡")
            self.balance_indicator.setStyleSheet(f"color: {self.theme.warning}; font-size: 13px;")
        elif diff >= -50:
            self.balance_indicator.setText("やや自チーム有利")
            self.balance_indicator.setStyleSheet(f"color: {self.theme.accent_orange}; font-size: 13px;")
        else:
            self.balance_indicator.setText("自チーム有利 (低確率)")
            self.balance_indicator.setStyleSheet(f"color: {self.theme.danger}; font-size: 13px;")

        self.success_rate_label.setText(f"成功率: 約{base_chance}%")

        # ボタン有効化条件
        can_trade = (len(self.offered_players) > 0 or self.money_adjustment > 0) and len(self.requested_players) > 0
        self.trade_btn.setEnabled(can_trade)

    def _propose_trade(self):
        """トレード提案"""
        if not self.current_team or not self.target_team:
            return

        if not self.requested_players:
            return

        # 支配下上限チェック
        current_shihaika = len([p for p in self.current_team.players if not p.is_developmental])
        net_change = len(self.requested_players) - len(self.offered_players)
        
        if current_shihaika + net_change > self.MAX_SHIHAIKA:
            QMessageBox.warning(self, "登録枠超過", 
                f"このトレードが成立すると支配下登録が{self.MAX_SHIHAIKA}人を超えます。\n"
                f"現在: {current_shihaika}人 + 獲得{len(self.requested_players)}人 - 放出{len(self.offered_players)}人 = {current_shihaika + net_change}人\n"
                "先に選手を自由契約にするか、放出選手を追加してください。")
            return

        # 成功率計算
        self_value = sum(self.current_team.players[i].overall_rating for i in self.offered_players if 0 <= i < len(self.current_team.players))
        target_value = sum(self.target_team.players[i].overall_rating for i in self.requested_players if 0 <= i < len(self.target_team.players))
        
        money_value = self.money_adjustment // 10000000
        adjusted_self = self_value + money_value
        diff = adjusted_self - target_value

        if diff >= 100:
            base_chance = 95
        elif diff >= 50:
            base_chance = 80
        elif diff >= 20:
            base_chance = 65
        elif diff >= 0:
            base_chance = 50
        elif diff >= -20:
            base_chance = 35
        elif diff >= -50:
            base_chance = 20
        else:
            base_chance = 5

        # PendingTrade作成
        pending_trade = PendingTrade(
            offering_team_name=self.current_team.name,
            target_team_name=self.target_team.name,
            offered_player_ids=list(self.offered_players),
            requested_player_ids=list(self.requested_players),
            money_adjustment=self.money_adjustment,
            days_remaining=5,
            success_chance=base_chance
        )
        
        self.game_state.pending_trades.append(pending_trade)
        
        QMessageBox.information(self, "提案完了", 
            f"トレードを申し込みました。\n相手球団の回答まで約5日かかります。")
            
        self._check_pending_trade()
        self._clear_trade() # UI上の選択状態はクリア（あるいは残してもいいが、混乱避けるためクリア推奨だがロックされているのでクリアしないほうがいいかも？今回は_check_pending_tradeでロックするのでクリアはしない、またはロック状態で表示維持）
        # _check_pending_tradeでロックされるので、その前にクリアすると見えなくなる
        # UI的には「申請中」としてロックされた状態で見えている方が親切
        # ただし、_clear_tradeを呼ぶとリストが消える
        
        # ここではクリアせずロックだけかける



    def _clear_trade(self):
        """トレード内容をクリア"""
        self.offered_players.clear()
        self.requested_players.clear()
        self.money_adjustment = 0
        self.money_input.setText("0")
        self._refresh_offer_display()
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
        
        # Hide initially to prevent appearing at (0,0) before being properly added to layout
        self.hide()

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
        self.draft_page = DraftScoutingPage(self)
        self.foreign_page = ForeignPlayerScoutingPage(self)
        self.trade_page = TradePage(self)
        
        # TradePage's player detail signal to ContractsPage's signal
        self.trade_page.player_detail_requested.connect(self.go_to_player_detail.emit)

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
                # 新外国人調査タブ (index 1) の制限期間チェック
                if index == 1 and self._is_foreign_tab_closed():
                    QMessageBox.warning(self, "期間外", 
                        "新外国人調査は8月～10月の間は行えません。\n"
                        "外国人選手の調査・獲得は11月から7月までの期間に行ってください。")
                    btn.setChecked(False)
                    return
                
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
    
    def _is_foreign_tab_closed(self) -> bool:
        """新外国人調査タブが閉鎖期間かどうかを判定"""
        if not hasattr(self, 'game_state') or not self.game_state or not self.game_state.current_date:
            return False
        try:
            m = int(self.game_state.current_date.split('-')[1])
            return m in [8, 9, 10]
        except:
            return False

    def set_game_state(self, game_state):
        """ゲーム状態を設定"""
        self.game_state = game_state
        self.draft_page.set_game_state(game_state)
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
        """日付に応じてタブの有効/無効を切り替え (スタイル変更のみ)"""
        if not hasattr(self, 'game_state') or not self.game_state or not self.game_state.current_date:
            return
            
        try:
            is_foreign_disabled = self._is_foreign_tab_closed()
            
            # Button 1 is "新外国人調査" - グレーアウト表示 (ただしクリックは可能)
            if len(self.nav_buttons) > 1:
                btn = self.nav_buttons[1]
                if is_foreign_disabled:
                    btn.setStyleSheet(f"""
                        QPushButton {{
                            background-color: {self.theme.bg_card_elevated};
                            color: {self.theme.text_muted};
                            border: none;
                            border-bottom: 3px solid transparent;
                            padding: 12px 20px;
                            font-weight: 700;
                            font-size: 13px;
                        }}
                    """)
                else:
                    btn.setStyleSheet(f"""
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
                    """)
                
                # If currently selected and disabled, switch to Draft
                if is_foreign_disabled and self.stacked_widget.currentIndex() == 1:
                     self.nav_buttons[0].click()
        except: pass

    def load_data(self, data_manager):
        """外部からデータをロード・更新"""
        pass