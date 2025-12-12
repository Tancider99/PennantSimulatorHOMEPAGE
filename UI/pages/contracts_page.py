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
    QStyledItemDelegate, QStyle
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

try:
    from models import Position, PitchType, PlayerStats, Player, Team
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
        return 5.0 + (self.skill / 10.0)  # 5-15%程度


@dataclass
class DraftProspect:
    """ドラフト候補選手"""
    id: int
    name: str
    position: Position
    pitch_type: Optional[PitchType] = None
    age: int = 18
    school: str = ""

    # 実能力 (調査が完了するまで完全に見えない)
    true_stats: PlayerStats = field(default_factory=PlayerStats)
    true_potential: int = 50  # 伸びしろ: 1-99

    # 調査状態
    scout_level: float = 0.0  # 0-100%
    scouting_status: ScoutingStatus = ScoutingStatus.NOT_STARTED
    assigned_scout: Optional[Scout] = None

    # 表示用の推定ランク (調査度に応じてブレが減る)
    estimated_rank: str = "?"
    estimated_potential_rank: str = "?"

    def get_visible_stats(self) -> Dict[str, int]:
        """調査度に応じた可視能力値を返す"""
        visible = {}
        base_noise = max(0, 30 - int(self.scout_level * 0.3))  # 0-30のノイズ

        if self.position == Position.PITCHER:
            stats_list = ['stuff', 'control', 'stamina', 'velocity']
        else:
            stats_list = ['contact', 'power', 'speed', 'arm', 'fielding']

        for stat in stats_list:
            # fieldingはpropertyなのでgetattr経由で取得
            if stat == 'fielding':
                true_val = self.true_stats.fielding
            else:
                true_val = getattr(self.true_stats, stat, 50)

            if self.scout_level < 20:
                # 20%未満: ほぼ見えない
                visible[stat] = -1
            elif self.scout_level < 50:
                # 50%未満: 大きなブレあり
                noise = random.randint(-base_noise, base_noise)
                visible[stat] = max(1, min(99, true_val + noise))
            elif self.scout_level < 80:
                # 80%未満: 小さなブレあり
                noise = random.randint(-base_noise // 2, base_noise // 2)
                visible[stat] = max(1, min(99, true_val + noise))
            else:
                # 80%以上: ほぼ正確
                visible[stat] = true_val

        return visible

    def get_visible_potential(self) -> int:
        """調査度に応じた伸びしろ推定値"""
        if self.scout_level < 30:
            return -1
        elif self.scout_level < 60:
            noise = random.randint(-20, 20)
            return max(1, min(99, self.true_potential + noise))
        elif self.scout_level < 90:
            noise = random.randint(-10, 10)
            return max(1, min(99, self.true_potential + noise))
        else:
            return self.true_potential

    def update_estimated_ranks(self):
        """推定ランクを更新"""
        if self.scout_level < 20:
            self.estimated_rank = "?"
            self.estimated_potential_rank = "?"
        else:
            visible = self.get_visible_stats()
            avg = sum(v for v in visible.values() if v > 0) / max(1, len([v for v in visible.values() if v > 0]))
            self.estimated_rank = self._value_to_rank(int(avg))

            pot = self.get_visible_potential()
            self.estimated_potential_rank = self._value_to_rank(pot) if pot > 0 else "?"

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


@dataclass
class ForeignPlayerCandidate:
    """外国人選手候補"""
    id: int
    name: str
    position: Position
    pitch_type: Optional[PitchType] = None
    age: int = 28
    country: str = "USA"

    # 実能力
    true_stats: PlayerStats = field(default_factory=PlayerStats)
    salary_demand: int = 100000000  # 年俸要求額
    years_demand: int = 2  # 契約年数要求

    # 調査状態
    scout_level: float = 0.0
    scouting_status: ScoutingStatus = ScoutingStatus.NOT_STARTED
    assigned_scout: Optional[Scout] = None

    # 交渉状態
    negotiation_started: bool = False
    negotiation_progress: int = 0  # 0-100
    interest_level: int = 50  # 興味度: 0-100

    def get_visible_stats(self) -> Dict[str, int]:
        """調査度に応じた可視能力値"""
        visible = {}
        base_noise = max(0, 25 - int(self.scout_level * 0.25))

        if self.position == Position.PITCHER:
            stats_list = ['stuff', 'control', 'stamina', 'velocity']
        else:
            stats_list = ['contact', 'power', 'speed', 'arm', 'fielding']

        for stat in stats_list:
            # fieldingはpropertyなのでgetattr経由で取得
            if stat == 'fielding':
                true_val = self.true_stats.fielding
            else:
                true_val = getattr(self.true_stats, stat, 50)

            if self.scout_level < 10:
                visible[stat] = -1
            elif self.scout_level < 40:
                noise = random.randint(-base_noise, base_noise)
                visible[stat] = max(1, min(99, true_val + noise))
            else:
                noise = random.randint(-base_noise // 2, base_noise // 2)
                visible[stat] = max(1, min(99, true_val + noise))

        return visible

    def get_overall_estimate(self) -> int:
        """推定総合力"""
        visible = self.get_visible_stats()
        valid_stats = [v for v in visible.values() if v > 0]
        if not valid_stats:
            return 0
        return int(sum(valid_stats) / len(valid_stats))


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
                selection-background-color: {self.theme.bg_input};
                outline: none;
            }}
            QTableWidget::item:selected {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_primary};
                border: none;
                outline: none;
            }}
            QTableWidget::item:focus {{
                background-color: {self.theme.bg_input};
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
    """ランク表示用アイテムを作成 (RatingDelegate用)"""
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


def get_rank_color(rank: str) -> QColor:
    """ランクに対応する色を返す"""
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
    return colors.get(rank.upper(), QColor(THEME.text_muted))


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
        """ダミーデータ生成"""
        # スカウト生成
        scout_names = ["田中 誠", "山本 健一", "鈴木 太郎", "佐藤 次郎", "高橋 三郎"]
        specialties = ["野手", "投手", "汎用", "野手", "投手"]
        for i, (name, spec) in enumerate(zip(scout_names, specialties)):
            self.scouts.append(Scout(
                name=name,
                skill=random.randint(40, 80),
                specialty=spec
            ))

        # ドラフト候補生成
        first_names = ["翔太", "健太", "大輝", "拓海", "蓮", "悠斗", "颯太", "陸", "樹", "優斗"]
        last_names = ["佐藤", "田中", "高橋", "渡辺", "伊藤", "山本", "中村", "小林", "加藤", "吉田"]
        schools = ["○○大学", "△△高校", "□□大学", "◇◇高校", "☆☆大学"]

        positions = [Position.PITCHER, Position.CATCHER, Position.SHORTSTOP,
                    Position.SECOND, Position.CENTER, Position.FIRST,
                    Position.THIRD, Position.LEFT, Position.RIGHT]

        for i in range(20):
            pos = random.choice(positions)
            is_pitcher = pos == Position.PITCHER

            if is_pitcher:
                stats = PlayerStats(
                    stuff=random.randint(30, 90),
                    control=random.randint(30, 90),
                    stamina=random.randint(30, 90),
                    velocity=random.randint(135, 155)
                )
            else:
                defense_val = random.randint(30, 90)
                stats = PlayerStats(
                    contact=random.randint(30, 90),
                    power=random.randint(30, 90),
                    speed=random.randint(30, 90),
                    arm=random.randint(30, 90),
                    defense_ranges={pos.value: defense_val}
                )

            prospect = DraftProspect(
                id=i,
                name=f"{random.choice(last_names)} {random.choice(first_names)}",
                position=pos,
                pitch_type=random.choice([PitchType.STARTER, PitchType.RELIEVER]) if is_pitcher else None,
                age=random.randint(18, 22),
                school=random.choice(schools),
                true_stats=stats,
                true_potential=random.randint(30, 95)
            )
            prospect.update_estimated_ranks()
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

        splitter.setSizes([600, 400])
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

        header = QLabel("候補選手リスト")
        header.setStyleSheet(f"font-weight: bold; color: {self.theme.text_secondary}; font-size: 13px;")
        layout.addWidget(header)

        self.prospect_table = ContractsTableWidget()
        self.rating_delegate = RatingDelegate(self)

        cols = ["名前", "Pos", "年齢", "学校", "推定", "潜力", "調査度", "状態"]
        widths = [100, 40, 40, 80, 45, 45, 60, 70]

        self.prospect_table.setColumnCount(len(cols))
        self.prospect_table.setHorizontalHeaderLabels(cols)
        for i, w in enumerate(widths):
            self.prospect_table.setColumnWidth(i, w)

        # ランク列にデリゲート設定
        # (推定・潜力はランク文字なので、専用処理が必要)

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
        layout.addWidget(self.detail_header)

        # 能力詳細フレーム
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-radius: 4px; padding: 10px;")
        stats_layout = QGridLayout(self.stats_frame)
        stats_layout.setSpacing(8)

        self.stat_labels = {}
        stat_names = ["ミート", "パワー", "走力", "肩力", "守備", "球威", "制球", "スタミナ", "球速"]
        for i, name in enumerate(stat_names):
            row, col = i // 3, (i % 3) * 2
            label = QLabel(name)
            label.setStyleSheet(f"color: {self.theme.text_secondary};")
            stats_layout.addWidget(label, row, col)

            value_label = QLabel("?")
            value_label.setStyleSheet(f"color: {self.theme.text_muted}; font-weight: bold;")
            stats_layout.addWidget(value_label, row, col + 1)
            self.stat_labels[name] = value_label

        layout.addWidget(self.stats_frame)

        # 伸びしろ表示
        potential_frame = QFrame()
        potential_frame.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-radius: 4px; padding: 10px;")
        potential_layout = QHBoxLayout(potential_frame)

        potential_layout.addWidget(QLabel("伸びしろ:"))
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

        layout.addWidget(progress_frame)

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
        # フィルター適用
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

        self.prospect_table.setRowCount(len(filtered))

        for row, prospect in enumerate(filtered):
            prospect.update_estimated_ranks()

            # 名前
            name_item = create_text_item(prospect.name, Qt.AlignLeft | Qt.AlignVCenter)
            name_item.setData(Qt.UserRole, prospect)
            self.prospect_table.setItem(row, 0, name_item)

            # ポジション
            pos_item = create_text_item(short_pos_name(prospect.position))
            self.prospect_table.setItem(row, 1, pos_item)

            # 年齢
            age_item = create_text_item(str(prospect.age))
            self.prospect_table.setItem(row, 2, age_item)

            # 学校
            school_item = create_text_item(prospect.school, Qt.AlignLeft | Qt.AlignVCenter)
            self.prospect_table.setItem(row, 3, school_item)

            # 推定ランク
            rank_item = create_text_item(prospect.estimated_rank)
            rank_item.setForeground(get_rank_color(prospect.estimated_rank))
            font = rank_item.font()
            font.setBold(True)
            rank_item.setFont(font)
            self.prospect_table.setItem(row, 4, rank_item)

            # 潜力ランク
            pot_item = create_text_item(prospect.estimated_potential_rank)
            pot_item.setForeground(get_rank_color(prospect.estimated_potential_rank))
            font = pot_item.font()
            font.setBold(True)
            pot_item.setFont(font)
            self.prospect_table.setItem(row, 5, pot_item)

            # 調査度
            progress_item = create_progress_item(prospect.scout_level)
            self.prospect_table.setItem(row, 6, progress_item)

            # 状態
            status_item = create_status_item(prospect.scouting_status)
            self.prospect_table.setItem(row, 7, status_item)

    def _on_prospect_clicked(self, row: int):
        """候補選択時"""
        item = self.prospect_table.item(row, 0)
        if item:
            prospect = item.data(Qt.UserRole)
            if prospect:
                self.selected_prospect = prospect
                self._update_detail_panel()

    def _on_prospect_selected(self, row: int):
        """候補ダブルクリック時"""
        self._on_prospect_clicked(row)

    def _update_detail_panel(self):
        """詳細パネルを更新"""
        p = self.selected_prospect
        if not p:
            return

        self.detail_header.setText(f"{p.name} ({short_pos_name(p.position)}) - {p.school}")

        # 能力値更新
        visible = p.get_visible_stats()

        # 野手能力
        for name, key in [("ミート", "contact"), ("パワー", "power"), ("走力", "speed"), ("肩力", "arm"), ("守備", "fielding")]:
            val = visible.get(key, -1)
            label = self.stat_labels.get(name)
            if label:
                if val > 0:
                    rank = Theme.get_rating_rank(val)
                    label.setText(f"{rank} ({val})")
                    label.setStyleSheet(f"color: {Theme.get_rating_color(val)}; font-weight: bold;")
                else:
                    label.setText("?")
                    label.setStyleSheet(f"color: {self.theme.text_muted}; font-weight: bold;")

        # 投手能力
        for name, key in [("球威", "stuff"), ("制球", "control"), ("スタミナ", "stamina"), ("球速", "velocity")]:
            val = visible.get(key, -1)
            label = self.stat_labels.get(name)
            if label:
                if key == "velocity" and val > 0:
                    label.setText(f"{val}km/h")
                    label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold;")
                elif val > 0:
                    rank = Theme.get_rating_rank(val)
                    label.setText(f"{rank} ({val})")
                    label.setStyleSheet(f"color: {Theme.get_rating_color(val)}; font-weight: bold;")
                else:
                    label.setText("?")
                    label.setStyleSheet(f"color: {self.theme.text_muted}; font-weight: bold;")

        # 伸びしろ
        pot = p.get_visible_potential()
        if pot > 0:
            rank = Theme.get_rating_rank(pot)
            self.potential_label.setText(f"{rank} ({pot})")
            self.potential_label.setStyleSheet(f"color: {Theme.get_rating_color(pot)}; font-weight: bold; font-size: 18px;")
        else:
            self.potential_label.setText("?")
            self.potential_label.setStyleSheet(f"color: {self.theme.text_muted}; font-weight: bold; font-size: 18px;")

        # 進捗バー
        self.progress_bar.setValue(int(p.scout_level))

        # ボタン状態更新
        self.dispatch_btn.setEnabled(
            p.scouting_status != ScoutingStatus.IN_PROGRESS and
            p.scout_level < 100 and
            any(s.is_available for s in self.scouts)
        )
        self.recall_btn.setEnabled(p.scouting_status == ScoutingStatus.IN_PROGRESS)

    def _update_scout_combo(self):
        """スカウトコンボボックスを更新"""
        self.scout_combo.clear()
        for scout in self.scouts:
            status = "空き" if scout.is_available else "派遣中"
            self.scout_combo.addItem(f"{scout.name} (能力:{scout.skill} / {scout.specialty}) [{status}]", scout)

    def _update_scout_status(self):
        """スカウト状態ラベルを更新"""
        available = sum(1 for s in self.scouts if s.is_available)
        total = len(self.scouts)
        self.scout_status_label.setText(f"スカウト: {available}/{total} 空き")

    def _dispatch_scout(self):
        """スカウトを派遣"""
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
            f"{scout_data.name}を{self.selected_prospect.name}の調査に派遣しました。\n"
            f"1日あたり約{scout_data.daily_progress:.1f}%の進捗が期待できます。")

        self._update_scout_combo()
        self._update_scout_status()
        self._update_detail_panel()
        self._refresh_table()

    def _recall_scout(self):
        """スカウトを帰還させる"""
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
        """日付を進める (ゲーム進行時に呼び出し)"""
        for prospect in self.prospects:
            if prospect.scouting_status == ScoutingStatus.IN_PROGRESS and prospect.assigned_scout:
                progress = prospect.assigned_scout.daily_progress
                prospect.scout_level = min(100, prospect.scout_level + progress)

                if prospect.scout_level >= 100:
                    prospect.scouting_status = ScoutingStatus.COMPLETED
                    prospect.assigned_scout.is_available = True
                    prospect.assigned_scout.current_mission_id = None
                    prospect.assigned_scout = None

                prospect.update_estimated_ranks()

        self._update_scout_combo()
        self._update_scout_status()
        self._refresh_table()
        if self.selected_prospect:
            self._update_detail_panel()


# ========================================
# 2. Foreign Player Scouting Page
# ========================================

class ForeignPlayerScoutingPage(QWidget):
    """外国人選手調査ページ"""

    player_selected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.candidates: List[ForeignPlayerCandidate] = []
        self.scouts: List[Scout] = []
        self.selected_candidate: Optional[ForeignPlayerCandidate] = None

        self._generate_dummy_data()
        self._setup_ui()

    def _generate_dummy_data(self):
        """ダミーデータ生成"""
        # スカウト生成
        scout_names = ["John Smith", "Mike Johnson", "Carlos Garcia"]
        for name in scout_names:
            self.scouts.append(Scout(
                name=name,
                skill=random.randint(50, 85),
                specialty="汎用"
            ))

        # 外国人選手候補生成
        first_names = ["James", "Michael", "Robert", "David", "Chris", "Jose", "Carlos", "Pedro", "Juan", "Luis"]
        last_names = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Rodriguez", "Martinez", "Lopez", "Gonzalez"]
        countries = ["USA", "Dominican", "Cuba", "Venezuela", "Mexico", "Korea", "Taiwan"]

        positions = [Position.PITCHER, Position.FIRST, Position.LEFT,
                    Position.RIGHT, Position.CENTER, Position.SHORTSTOP]

        for i in range(15):
            pos = random.choice(positions)
            is_pitcher = pos == Position.PITCHER

            if is_pitcher:
                stats = PlayerStats(
                    stuff=random.randint(50, 95),
                    control=random.randint(40, 90),
                    stamina=random.randint(40, 90),
                    velocity=random.randint(145, 160)
                )
            else:
                defense_val = random.randint(40, 85)
                stats = PlayerStats(
                    contact=random.randint(40, 90),
                    power=random.randint(50, 95),
                    speed=random.randint(40, 85),
                    arm=random.randint(40, 85),
                    defense_ranges={pos.value: defense_val}
                )

            candidate = ForeignPlayerCandidate(
                id=i,
                name=f"{random.choice(first_names)} {random.choice(last_names)}",
                position=pos,
                pitch_type=random.choice([PitchType.STARTER, PitchType.RELIEVER, PitchType.CLOSER]) if is_pitcher else None,
                age=random.randint(24, 35),
                country=random.choice(countries),
                true_stats=stats,
                salary_demand=random.randint(50, 300) * 1000000,
                years_demand=random.randint(1, 4),
                interest_level=random.randint(30, 80)
            )
            self.candidates.append(candidate)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ツールバー
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # メインコンテンツ
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {self.theme.border}; width: 1px; }}")

        # 左: 候補リスト
        left_widget = self._create_candidate_list()
        splitter.addWidget(left_widget)

        # 右: 詳細 & 交渉
        right_widget = self._create_detail_panel()
        splitter.addWidget(right_widget)

        splitter.setSizes([600, 400])
        layout.addWidget(splitter)

    def _create_toolbar(self) -> QWidget:
        toolbar = QFrame()
        toolbar.setFixedHeight(50)
        toolbar.setStyleSheet(f"background-color: {self.theme.bg_card}; border-bottom: 1px solid {self.theme.border};")

        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(12, 0, 12, 0)

        title = QLabel("助っ人調査")
        title.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; font-size: 16px;")
        layout.addWidget(title)

        layout.addSpacing(20)

        self.pos_filter = QComboBox()
        self.pos_filter.addItems(["全ポジション", "投手", "野手"])
        self.pos_filter.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 4px;")
        self.pos_filter.currentIndexChanged.connect(self._refresh_table)
        layout.addWidget(self.pos_filter)

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

        header = QLabel("外国人選手候補リスト")
        header.setStyleSheet(f"font-weight: bold; color: {self.theme.text_secondary}; font-size: 13px;")
        layout.addWidget(header)

        self.candidate_table = ContractsTableWidget()
        self.rating_delegate = RatingDelegate(self)

        cols = ["名前", "Pos", "年齢", "国籍", "推定", "調査度", "年俸", "状態"]
        widths = [120, 40, 40, 70, 45, 60, 80, 70]

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
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # 選手詳細ヘッダー
        self.detail_header = QLabel("選手を選択してください")
        self.detail_header.setStyleSheet(f"color: {self.theme.text_primary}; font-size: 16px; font-weight: bold;")
        layout.addWidget(self.detail_header)

        # 能力詳細フレーム
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-radius: 4px; padding: 10px;")
        stats_layout = QGridLayout(self.stats_frame)
        stats_layout.setSpacing(8)

        self.stat_labels = {}
        stat_names = ["ミート", "パワー", "走力", "肩力", "守備", "球威", "制球", "スタミナ", "球速"]
        for i, name in enumerate(stat_names):
            row, col = i // 3, (i % 3) * 2
            label = QLabel(name)
            label.setStyleSheet(f"color: {self.theme.text_secondary};")
            stats_layout.addWidget(label, row, col)

            value_label = QLabel("?")
            value_label.setStyleSheet(f"color: {self.theme.text_muted}; font-weight: bold;")
            stats_layout.addWidget(value_label, row, col + 1)
            self.stat_labels[name] = value_label

        layout.addWidget(self.stats_frame)

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

        layout.addWidget(progress_frame)

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

        # 交渉セクション
        negotiation_frame = QFrame()
        negotiation_frame.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border-radius: 4px; padding: 10px;")
        negotiation_layout = QVBoxLayout(negotiation_frame)

        negotiation_layout.addWidget(QLabel("契約交渉"))

        # 興味度表示
        interest_layout = QHBoxLayout()
        interest_layout.addWidget(QLabel("興味度:"))
        self.interest_label = QLabel("?")
        self.interest_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold;")
        interest_layout.addWidget(self.interest_label)
        interest_layout.addStretch()
        negotiation_layout.addLayout(interest_layout)

        # 提示条件
        offer_layout = QGridLayout()
        offer_layout.addWidget(QLabel("提示年俸:"), 0, 0)
        self.salary_spin = QSpinBox()
        self.salary_spin.setRange(10, 1000)
        self.salary_spin.setSuffix(" 百万円")
        self.salary_spin.setValue(100)
        self.salary_spin.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 4px;")
        offer_layout.addWidget(self.salary_spin, 0, 1)

        offer_layout.addWidget(QLabel("提示年数:"), 1, 0)
        self.years_spin = QSpinBox()
        self.years_spin.setRange(1, 5)
        self.years_spin.setValue(2)
        self.years_spin.setSuffix(" 年")
        self.years_spin.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 4px;")
        offer_layout.addWidget(self.years_spin, 1, 1)

        negotiation_layout.addLayout(offer_layout)

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
        """テーブルを更新"""
        filtered = self.candidates.copy()

        pos_filter = self.pos_filter.currentText()
        if pos_filter == "投手":
            filtered = [c for c in filtered if c.position == Position.PITCHER]
        elif pos_filter == "野手":
            filtered = [c for c in filtered if c.position != Position.PITCHER]

        self.candidate_table.setRowCount(len(filtered))

        for row, candidate in enumerate(filtered):
            # 名前
            name_item = create_text_item(candidate.name, Qt.AlignLeft | Qt.AlignVCenter)
            name_item.setData(Qt.UserRole, candidate)
            self.candidate_table.setItem(row, 0, name_item)

            # ポジション
            pos_item = create_text_item(short_pos_name(candidate.position))
            self.candidate_table.setItem(row, 1, pos_item)

            # 年齢
            age_item = create_text_item(str(candidate.age))
            self.candidate_table.setItem(row, 2, age_item)

            # 国籍
            country_item = create_text_item(candidate.country)
            self.candidate_table.setItem(row, 3, country_item)

            # 推定総合
            ovr = candidate.get_overall_estimate()
            if ovr > 0:
                rank = Theme.get_rating_rank(ovr)
                rank_item = create_text_item(rank)
                rank_item.setForeground(QColor(Theme.get_rating_color(ovr)))
            else:
                rank_item = create_text_item("?")
                rank_item.setForeground(QColor(self.theme.text_muted))
            font = rank_item.font()
            font.setBold(True)
            rank_item.setFont(font)
            self.candidate_table.setItem(row, 4, rank_item)

            # 調査度
            progress_item = create_progress_item(candidate.scout_level)
            self.candidate_table.setItem(row, 5, progress_item)

            # 年俸
            salary_text = f"{candidate.salary_demand // 1000000}百万" if candidate.scout_level >= 30 else "?"
            salary_item = create_text_item(salary_text)
            self.candidate_table.setItem(row, 6, salary_item)

            # 状態
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
            self.candidate_table.setItem(row, 7, status_item)

    def _on_candidate_clicked(self, row: int):
        """候補選択時"""
        item = self.candidate_table.item(row, 0)
        if item:
            candidate = item.data(Qt.UserRole)
            if candidate:
                self.selected_candidate = candidate
                self._update_detail_panel()

    def _on_candidate_selected(self, row: int):
        """候補ダブルクリック時"""
        self._on_candidate_clicked(row)

    def _update_detail_panel(self):
        """詳細パネルを更新"""
        c = self.selected_candidate
        if not c:
            return

        self.detail_header.setText(f"{c.name} ({short_pos_name(c.position)}) - {c.country}")

        # 能力値更新
        visible = c.get_visible_stats()

        for name, key in [("ミート", "contact"), ("パワー", "power"), ("走力", "speed"), ("肩力", "arm"), ("守備", "fielding")]:
            val = visible.get(key, -1)
            label = self.stat_labels.get(name)
            if label:
                if val > 0:
                    rank = Theme.get_rating_rank(val)
                    label.setText(f"{rank} ({val})")
                    label.setStyleSheet(f"color: {Theme.get_rating_color(val)}; font-weight: bold;")
                else:
                    label.setText("?")
                    label.setStyleSheet(f"color: {self.theme.text_muted}; font-weight: bold;")

        for name, key in [("球威", "stuff"), ("制球", "control"), ("スタミナ", "stamina"), ("球速", "velocity")]:
            val = visible.get(key, -1)
            label = self.stat_labels.get(name)
            if label:
                if key == "velocity" and val > 0:
                    label.setText(f"{val}km/h")
                    label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold;")
                elif val > 0:
                    rank = Theme.get_rating_rank(val)
                    label.setText(f"{rank} ({val})")
                    label.setStyleSheet(f"color: {Theme.get_rating_color(val)}; font-weight: bold;")
                else:
                    label.setText("?")
                    label.setStyleSheet(f"color: {self.theme.text_muted}; font-weight: bold;")

        # 進捗バー
        self.progress_bar.setValue(int(c.scout_level))

        # 興味度
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

        # ボタン状態更新
        self.dispatch_btn.setEnabled(
            c.scouting_status != ScoutingStatus.IN_PROGRESS and
            c.scout_level < 100 and
            any(s.is_available for s in self.scouts)
        )
        self.recall_btn.setEnabled(c.scouting_status == ScoutingStatus.IN_PROGRESS)
        self.negotiate_btn.setEnabled(c.scout_level >= 50 and not c.negotiation_started)

    def _update_scout_combo(self):
        """スカウトコンボボックスを更新"""
        self.scout_combo.clear()
        for scout in self.scouts:
            status = "空き" if scout.is_available else "派遣中"
            self.scout_combo.addItem(f"{scout.name} (能力:{scout.skill}) [{status}]", scout)

    def _update_scout_status(self):
        """スカウト状態ラベルを更新"""
        available = sum(1 for s in self.scouts if s.is_available)
        total = len(self.scouts)
        self.scout_status_label.setText(f"海外スカウト: {available}/{total} 空き")

    def _dispatch_scout(self):
        """スカウトを派遣"""
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
        """スカウトを帰還させる"""
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
        """交渉開始"""
        c = self.selected_candidate
        if not c or c.scout_level < 50:
            return

        offered_salary = self.salary_spin.value() * 1000000
        offered_years = self.years_spin.value()

        # 交渉成功率計算
        salary_ratio = offered_salary / c.salary_demand
        years_ratio = offered_years / c.years_demand

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

        success_chance = max(5, min(95, base_chance))

        result = random.randint(1, 100)

        if result <= success_chance:
            QMessageBox.information(self, "交渉成功",
                f"{c.name}との契約が成立しました！\n"
                f"年俸: {offered_salary // 1000000}百万円 / {offered_years}年契約")
            c.negotiation_started = True
            # ここで実際のPlayer作成とチーム追加を行う
        else:
            QMessageBox.warning(self, "交渉失敗",
                f"{c.name}は提示条件に満足しませんでした。\n"
                f"(成功率: {success_chance}%)")
            c.interest_level = max(10, c.interest_level - 5)

        self._update_detail_panel()
        self._refresh_table()

    def advance_day(self):
        """日付を進める"""
        for candidate in self.candidates:
            if candidate.scouting_status == ScoutingStatus.IN_PROGRESS and candidate.assigned_scout:
                progress = candidate.assigned_scout.daily_progress
                candidate.scout_level = min(100, candidate.scout_level + progress)

                if candidate.scout_level >= 100:
                    candidate.scouting_status = ScoutingStatus.COMPLETED
                    candidate.assigned_scout.is_available = True
                    candidate.assigned_scout.current_mission_id = None
                    candidate.assigned_scout = None

        self._update_scout_combo()
        self._update_scout_status()
        self._refresh_table()
        if self.selected_candidate:
            self._update_detail_panel()


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
        "助っ人調査": 1,
        "トレード": 2,
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ContractsPage")
        self.theme = get_theme()
        self.setStyleSheet(f"background-color: {self.theme.bg_dark};")

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
        self.trade_page.set_game_state(game_state)

    def advance_day(self):
        """日付を進める (ゲーム進行時に呼び出し)"""
        self.draft_page.advance_day()
        self.foreign_page.advance_day()

    def load_data(self, data_manager):
        """外部からデータをロード・更新"""
        pass
