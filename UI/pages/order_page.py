# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Order Page
Advanced Drag & Drop Order Management with DH support
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QSplitter, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QScrollArea, QSizePolicy, QCheckBox, QStyledItemDelegate,
    QStyle, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QMimeData, QByteArray, QDataStream, QIODevice, QPoint, QSize
from PySide6.QtGui import QColor, QFont, QIcon, QDrag, QPixmap, QPainter, QBrush, QPen

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.panels import ToolbarPanel
from UI.widgets.tables import SortableTableWidgetItem, RatingDelegate, DefenseDelegate, DraggableTableWidget
from models import TeamLevel

# MIME Types
MIME_PLAYER_DATA = "application/x-pennant-player-data"
MIME_POS_SWAP = "application/x-pennant-pos-swap"

# Custom Role for Drag & Drop Player Index
ROLE_PLAYER_IDX = Qt.UserRole + 1

def get_pos_color(pos: str) -> str:
    """Return background color code for position badge"""
    if pos == "投": return "#3498db"
    if pos == "捕": return "#27ae60"
    if pos in ["一", "二", "三", "遊"]: return "#e67e22"
    if pos in ["左", "中", "右"]: return "#9b59b6"
    if pos == "DH": return "#e74c3c"
    return "#7f8c8d"





class OrderPage(QWidget):
    """Redesigned Order Page with DH, Color Coding, and Advanced Filters"""
    
    order_saved = Signal()
    player_detail_requested = Signal(object)

    def __init__(self, parent=None, is_best_order_mode=False):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.current_team = None
        self.is_best_order_mode = is_best_order_mode
        
        self.defense_delegate = DefenseDelegate(self.theme)
        self.rating_delegate = RatingDelegate(self)
        
        # 編集中の状態を保持する辞書（保存ボタンを押すまではここにのみ反映）
        self.edit_state = {}
        self.has_unsaved_changes = False
        
        self._setup_ui()

    def refresh(self):
        """外部から画面更新を要求するメソッド"""
        self._load_team_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        self.main_tabs = QTabWidget()
        self.main_tabs.setStyleSheet(self._get_main_tab_style())
        
        self.batter_page = self._create_batter_page()
        self.main_tabs.addTab(self.batter_page, "野手オーダー")
        
        if not self.is_best_order_mode:
            # ベストオーダー設定では投手は不要か、あるいは野手のみが一般的だが、
            # ユーザー要望は「オーダー画面とほぼ全く同じUI」なので一応入れておくか？
            # 「ベストオーダー」という言葉は通常打順を指すため、混乱を避けるなら野手のみにする手もあるが
            # ここでは一応入れておくが、ベストオーダー＝打順固定とするなら投手タブは無視される運用にする
            self.pitcher_page = self._create_pitcher_page()
            self.main_tabs.addTab(self.pitcher_page, "投手オーダー")
        else:
             # ベストオーダーモードでも一応表示しておく（将来的なベストローテ対応のため）
             # ただし保存対象は要検討。今回は打順のみにフォーカスするがUIは残す
             self.pitcher_page = self._create_pitcher_page()
             self.main_tabs.addTab(self.pitcher_page, "投手オーダー")

        layout.addWidget(self.main_tabs)

    def showEvent(self, event):
        """タブが表示されたときにデータを更新する"""
        super().showEvent(event)
        self.refresh()

    def refresh(self):
        """外部から呼び出し可能なリフレッシュメソッド"""
        if self.current_team:
            self._ensure_lists_initialized()
            self._load_team_data()
            self._refresh_all()

    def _create_toolbar(self) -> ToolbarPanel:
        toolbar = ToolbarPanel()
        toolbar.setFixedHeight(50)

        if self.is_best_order_mode:
            self.team_name_label = QLabel("ベストオーダー設定")
        else:
            self.team_name_label = QLabel("チーム名")
            
        self.team_name_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; font-size: 16px; margin-left: 12px;")
        toolbar.add_widget(self.team_name_label)
        
        self.status_label = QLabel("一軍登録: --/--")
        self.status_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; margin-left: 20px;")
        toolbar.add_widget(self.status_label)

        toolbar.add_stretch()
        
        # 自動編成ボタン (ベストオーダー作成時も便利なので残す)
        auto_btn = QPushButton("自動編成")
        auto_btn.setCursor(Qt.PointingHandCursor)
        auto_btn.setStyleSheet(f"background: {self.theme.bg_card}; color: {self.theme.text_primary}; padding: 6px 12px; border: 1px solid {self.theme.border}; border-radius: 4px; margin-left: 8px;")
        auto_btn.clicked.connect(self._auto_fill)
        toolbar.add_widget(auto_btn)

        if not self.is_best_order_mode:
            self.open_best_btn = QPushButton("ベストオーダー設定")
            self.open_best_btn.setCursor(Qt.PointingHandCursor)
            self.open_best_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme.accent_blue};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                    margin-right: 10px;
                }}
                QPushButton:hover {{
                    background-color: {self.theme.accent_blue_hover};
                }}
            """)
            self.open_best_btn.clicked.connect(self._open_best_order_settings)
            toolbar.add_widget(self.open_best_btn)
        else:
            self.clear_best_btn = QPushButton("ベストオーダー削除")
            self.clear_best_btn.setCursor(Qt.PointingHandCursor)
            self.clear_best_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme.error};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                    margin-right: 10px;
                }}
                QPushButton:hover {{
                    background-color: {self.theme.danger_hover};
                }}
            """)
            self.clear_best_btn.clicked.connect(self._clear_best_order)
            toolbar.add_widget(self.clear_best_btn)


        self.save_btn = QPushButton("保存")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.primary};
                color: {self.theme.text_highlight};
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-weight: bold;
            }}
            QPushButton:disabled {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_muted};
            }}
        """)
        self.save_btn.clicked.connect(self._save_changes)
        self.save_btn.setEnabled(False)
        toolbar.add_widget(self.save_btn)

        self.cancel_btn = QPushButton("キャンセル")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.theme.error};
                border: 1px solid {self.theme.error};
                border-radius: 4px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.error}22;
            }}
            QPushButton:disabled {{
                color: {self.theme.text_muted};
                border-color: {self.theme.border};
            }}
        """)
        self.cancel_btn.clicked.connect(self._discard_changes)
        self.cancel_btn.setEnabled(False)
        toolbar.add_widget(self.cancel_btn)

        return toolbar

    def _create_batter_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {self.theme.border}; width: 1px; }}")

        # LEFT
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 8, 8)
        
        l_header = QLabel("スタメン & ベンチ")
        l_header.setStyleSheet(f"font-weight: bold; color: {self.theme.text_secondary}; font-size: 13px;")
        left_layout.addWidget(l_header)
        
        self.lineup_table = self._create_table("lineup")
        self.lineup_table.setMinimumHeight(350)
        left_layout.addWidget(self.lineup_table)
        
        left_layout.addSpacing(4)
        
        self.bench_table = self._create_table("bench")
        left_layout.addWidget(self.bench_table)
        splitter.addWidget(left_widget)

        # RIGHT
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 8, 8, 8)
        
        ctrl_layout = QHBoxLayout()
        r_header = QLabel("野手リスト (支配下)")
        r_header.setStyleSheet(f"font-weight: bold; color: {self.theme.text_secondary}; font-size: 13px;")
        ctrl_layout.addWidget(r_header)
        
        ctrl_layout.addStretch()
        
        self.batter_pos_filter = QComboBox()
        self.batter_pos_filter.addItems(["全ポジション", "捕手", "一塁手", "二塁手", "三塁手", "遊撃手", "外野手"])
        self.batter_pos_filter.currentIndexChanged.connect(self._refresh_batter_farm_list)
        self.batter_pos_filter.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 2px;")
        ctrl_layout.addWidget(self.batter_pos_filter)
        
        right_layout.addLayout(ctrl_layout)
        
        self.farm_batter_table = self._create_table("farm_batter")
        right_layout.addWidget(self.farm_batter_table)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([500, 500])
        layout.addWidget(splitter)
        return page

    def _create_pitcher_page(self) -> QWidget:
        page = QWidget()
        layout = QHBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {self.theme.border}; width: 1px; }}")

        # LEFT
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(8, 8, 8, 8)
        
        l_header = QLabel("投手陣容 (先発・中継ぎ・抑え)")
        l_header.setStyleSheet(f"font-weight: bold; color: {self.theme.text_secondary}; font-size: 13px;")
        left_layout.addWidget(l_header)
        
        self.rotation_table = self._create_table("rotation")
        self.rotation_table.setMinimumHeight(240)
        left_layout.addWidget(self.rotation_table)
        
        left_layout.addSpacing(4)
        
        self.bullpen_table = self._create_table("bullpen")
        left_layout.addWidget(self.bullpen_table)
        splitter.addWidget(left_widget)

        # RIGHT
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(8, 8, 8, 8)
        
        ctrl_layout = QHBoxLayout()
        r_header = QLabel("投手リスト (支配下)")
        r_header.setStyleSheet(f"font-weight: bold; color: {self.theme.text_secondary}; font-size: 13px;")
        ctrl_layout.addWidget(r_header)
        
        ctrl_layout.addStretch()
        
        self.pitcher_type_filter = QComboBox()
        self.pitcher_type_filter.addItems(["全タイプ", "先発", "中継ぎ", "抑え"])
        self.pitcher_type_filter.currentIndexChanged.connect(self._refresh_pitcher_farm_list)
        self.pitcher_type_filter.setStyleSheet(f"background: {self.theme.bg_input}; color: {self.theme.text_primary}; border: 1px solid {self.theme.border}; padding: 2px;")
        ctrl_layout.addWidget(self.pitcher_type_filter)
        
        right_layout.addLayout(ctrl_layout)
        
        self.farm_pitcher_table = self._create_table("farm_pitcher")
        right_layout.addWidget(self.farm_pitcher_table)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([500, 500])
        layout.addWidget(splitter)
        return page

    def _create_table(self, mode) -> DraggableTableWidget:
        if mode in ["lineup", "rotation", "bullpen"]:
            table = DraggableTableWidget(mode)
            table.items_changed.connect(lambda: self._on_table_changed(table))
            table.position_swapped.connect(self._on_pos_swapped)
        else:
            table = DraggableTableWidget(mode) # DraggableTableWidget wrapper seems to be used for all, based on previous code.
            # Wait, line 303 in previous view: table = DraggableTableWidget(mode)
            # But line 455 in Step 109 proposal: if table_type in ...Draggable... else QTableWidget
            # Let's stick to previous working logic but apply style.
            # Original code used DraggableTableWidget(mode) for ALL tables in this method?
            # Looking at Step 92 lines 209, 215, 239... `self._create_table("lineup")`.
            # Step 114 shows `table = DraggableTableWidget(mode)` at line 303.
            # So I should use DraggableTableWidget(mode).
            pass
        
        # It seems I wanted to use QTableWidget for some? 
        # But `DraggableTableWidget` is a subclass of QTableWidget. 
        # Let's use `DraggableTableWidget(mode)` as it was in line 303 of Step 114 to be safe.
        table = DraggableTableWidget(mode)
        table.items_changed.connect(lambda: self._on_table_changed(table))
        if mode == "lineup":
             table.position_swapped.connect(self._on_pos_swapped)
        
        table.itemDoubleClicked.connect(self._on_player_double_clicked)

        cols = []
        widths = []
        
        if mode == "lineup":
            cols = ["順", "守", "調", "疲", "選手名", "ミ", "パ", "走", "肩", "守", "適正", "総合"]
            widths = [30, 40, 50, 35, 120, 35, 35, 35, 35, 35, 80, 45]
            for c in [5, 6, 7, 8, 9]:
                table.setItemDelegateForColumn(c, self.rating_delegate)
            table.setItemDelegateForColumn(10, self.defense_delegate)
            
        elif mode == "bench":
            cols = ["適性", "調", "疲", "選手名", "ミ", "パ", "走", "肩", "守", "適正", "総合"]
            widths = [70, 50, 35, 120, 35, 35, 35, 35, 35, 80, 45]
            for c in [4, 5, 6, 7, 8]:
                table.setItemDelegateForColumn(c, self.rating_delegate)
            table.setItemDelegateForColumn(9, self.defense_delegate)

        elif mode == "farm_batter":
            cols = ["調", "選手名", "年齢", "ミ", "パ", "走", "肩", "守", "守備適正", "総合"]
            widths = [50, 130, 40, 35, 35, 35, 35, 35, 80, 45]
            for c in [3, 4, 5, 6, 7]:
                table.setItemDelegateForColumn(c, self.rating_delegate)
            table.setItemDelegateForColumn(8, self.defense_delegate)

        elif mode == "rotation":
            cols = ["役", "調", "疲", "選手名", "間隔", "球速", "コ", "ス", "変", "先", "中", "抑", "総合"]
            widths = [40, 50, 35, 120, 50, 50, 35, 35, 35, 35, 35, 35, 45]
            for c in [6, 7, 8]:
                table.setItemDelegateForColumn(c, self.rating_delegate)
            table.cellClicked.connect(self._on_rotation_cell_clicked)

        elif mode == "bullpen":
            cols = ["役", "調", "疲", "選手名", "球速", "コ", "ス", "変", "先", "中", "抑", "総合"]
            widths = [40, 50, 35, 120, 50, 35, 35, 35, 35, 35, 35, 45]
            for c in [5, 6, 7]:
                table.setItemDelegateForColumn(c, self.rating_delegate)

        elif mode == "farm_pitcher":
            cols = ["タイプ", "調", "選手名", "年齢", "球速", "コ", "ス", "変", "先", "中", "抑", "総合"]
            widths = [45, 50, 120, 40, 50, 35, 35, 35, 35, 35, 35, 45]
            for c in [5, 6, 7]:
                table.setItemDelegateForColumn(c, self.rating_delegate)

        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        for i, w in enumerate(widths):
            table.setColumnWidth(i, w)
            
        # Apply White/Black selection style
        table.setStyleSheet(f"""
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

        return table
    
    def _get_main_tab_style(self):
        return f"""
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{
                background: {self.theme.bg_dark};
                color: {self.theme.text_secondary};
                padding: 8px 24px;
                border-bottom: 2px solid {self.theme.border};
                font-weight: bold;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                color: {self.theme.primary};
                border-bottom: 2px solid {self.theme.primary};
                background: {self.theme.bg_input};
            }}
        """

    def set_game_state(self, game_state):
        self.game_state = game_state
        if not game_state: return
        
        if game_state.player_team:
            self.current_team = game_state.player_team
            self.team_name_label.setText(self.current_team.name)
            
            # 初期化と表示更新
            self._ensure_lists_initialized()
            self._load_team_data()
            self._refresh_all()
        else:
            self.current_team = None
            if self.is_best_order_mode:
                self.team_name_label.setText("ベストオーダー設定")
            else:
                self.team_name_label.setText("チーム選択なし")
    


    def _ensure_lists_initialized(self):
        team = self.current_team
        if not team: return
        
        while len(team.current_lineup) < 9: team.current_lineup.append(-1)
        while len(team.rotation) < 8: team.rotation.append(-1)
        while len(team.setup_pitchers) < 8: team.setup_pitchers.append(-1)
        if not hasattr(team, 'closers'): team.closers = []
        while len(team.closers) < 2: team.closers.append(-1)
            
        if not hasattr(team, 'lineup_positions') or len(team.lineup_positions) != 9:
            team.lineup_positions = ["捕", "一", "二", "三", "遊", "左", "中", "右", "DH"]

    def _load_team_data(self):
        """チームデータをローカルの編集用ステートにコピー"""
        if not self.current_team: return
        
        # ベストオーダーモードの場合、best_orderから読み込む
        if self.is_best_order_mode:
            bo = getattr(self.current_team, 'best_order', None)
            # best_orderは辞書形式 {'current_lineup': [], 'lineup_positions': [], ...} を想定
            # なければ空（-1埋め）で初期化
            
            empty_lineup = [-1] * 9
            empty_pos = [""] * 9
            # デフォルトポジション
            def_pos = ["捕", "一", "二", "三", "遊", "左", "中", "右", "DH"]
            
            # ベストオーダーがなければ、現在のオーダーを初期値としてコピーするか？
            # ユーザー体験としては、最初は現在のオーダーが入っている方が楽かもしれない。
            # しかし「ベストオーダー設定」というからには、明示的に設定するもの。
            # いったん現在のオーダーをコピーしてあげるのが親切。
            
            if not bo:
                # コピー初期化
                self.edit_state = {
                    'current_lineup': list(self.current_team.current_lineup),
                    'lineup_positions': list(self.current_team.lineup_positions),
                    'bench_batters': list(self.current_team.bench_batters),
                    'rotation': list(self.current_team.rotation),
                    'setup_pitchers': list(self.current_team.setup_pitchers),
                    'closers': list(self.current_team.closers)
                }
            else:
                # 保存されたベストオーダーを展開
                # 辞書形式でない場合（旧仕様のリストのみ）の互換性チェック
                if isinstance(bo, list):
                     # 旧仕様: 打順だけリストで入っている -> convert
                     self.edit_state = {
                        'current_lineup': list(bo),
                        'lineup_positions': list(def_pos), # ポジション不明なのでデフォルト
                        'bench_batters': [],
                        'rotation': [-1]*8,
                        'setup_pitchers': [-1]*8,
                        'closers': [-1]*2
                     }
                else:
                    self.edit_state = {
                        'current_lineup': list(bo.get('current_lineup', [-1]*9)),
                        'lineup_positions': list(bo.get('lineup_positions', def_pos)),
                        'bench_batters': list(bo.get('bench_batters', [])),
                        'rotation': list(bo.get('rotation', [-1]*8)),
                        'setup_pitchers': list(bo.get('setup_pitchers', [-1]*8)),
                        'closers': list(bo.get('closers', [-1]*2))
                    }
        else:
            # 通常モード
            self.edit_state = {
                'current_lineup': list(self.current_team.current_lineup),
                'lineup_positions': list(self.current_team.lineup_positions),
                'bench_batters': list(self.current_team.bench_batters),
                'rotation': list(self.current_team.rotation),
                'setup_pitchers': list(self.current_team.setup_pitchers),
                'closers': list(self.current_team.closers)
            }
        
        self.has_unsaved_changes = False
        self.save_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)

    def _mark_as_changed(self):
        self.has_unsaved_changes = True
        self.save_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)

    def _save_changes(self):
        if not self.current_team: return
        t = self.current_team
        
        # --- バリデーションチェック ---
        
        # --- ベストオーダーモードの保存処理 ---
        if self.is_best_order_mode:
            # バリデーションは緩くする（怪我人でも設定は可能とするのが一般的）
            # ただし、人数等の基礎チェックはあってもいいが、未完成でも保存させたいならチェックなし
            # ここでは「スタメン9人埋まってなくてもOK」とする（作りかけ保存OK）
            
            # 辞書として保存
            best_order_data = {
                'current_lineup': list(self.edit_state['current_lineup']),
                'lineup_positions': list(self.edit_state['lineup_positions']),
                'bench_batters': list(self.edit_state['bench_batters']),
                'rotation': list(self.edit_state['rotation']),
                'setup_pitchers': list(self.edit_state['setup_pitchers']),
                'closers': list(self.edit_state['closers'])
            }
            t.best_order = best_order_data
            
            self.order_saved.emit()
            self._load_team_data() # 状態リセット
            self._refresh_all()
            QMessageBox.information(self, "完了", "ベストオーダーを保存しました。")
            
            # ダイアログなら閉じる？ いったんそのまま
            return


        # --- 通常モードの保存処理 ---
        
        # --- バリデーションチェック ---
        
        # 1. 基礎チェック (人数)
        valid_starters = len([x for x in self.edit_state['current_lineup'] if x != -1])
        valid_rotation = len([x for x in self.edit_state['rotation'] if x != -1])
        
        if valid_starters < 9:
            QMessageBox.warning(self, "エラー", "スタメンが9人未満です。保存できません。")
            return
        if valid_rotation == 0:
            QMessageBox.warning(self, "エラー", "先発投手が設定されていません。保存できません。")
            return

        # 2. スタメンの怪我人チェック & 再登録待機選手のチェック
        active_ids = set()
        active_ids.update([x for x in self.edit_state['current_lineup'] if x != -1])
        active_ids.update([x for x in self.edit_state['bench_batters'] if x != -1])
        active_ids.update([x for x in self.edit_state['rotation'] if x != -1])
        active_ids.update([x for x in self.edit_state['setup_pitchers'] if x != -1])
        active_ids.update([x for x in self.edit_state['closers'] if x != -1])

        invalid_players = []
        for p_idx in active_ids:
            if 0 <= p_idx < len(t.players):
                p = t.players[p_idx]
                
                # スタメンに怪我人がいるかチェック
                if p_idx in self.edit_state['current_lineup']:
                    if p.is_injured:
                        invalid_players.append(f"{p.name} (怪我: スタメン不可)")
                
                # 再登録待機チェック (ベンチ・投手含め一軍全体NG)
                if hasattr(p, 'days_until_promotion') and p.days_until_promotion > 0:
                    invalid_players.append(f"{p.name} (登録抹消中: 残{p.days_until_promotion}日)")

        if invalid_players:
            msg = "以下の選手に問題があるため保存できません：\n\n" + "\n".join(invalid_players)
            QMessageBox.warning(self, "保存不可", msg)
            return

        # --- ロースター変更処理（登録抹消・昇格） ---
        
        # 初回保存かどうか（初回は降格ペナルティなし）
        is_first_save = not getattr(t, 'order_initialized', True)
        
        # 現在の一軍メンバーセット
        old_roster_set = set(t.active_roster)
        
        # 新しい一軍メンバーセット
        new_roster_set = active_ids # 上で作成済み
        
        # 1. 登録抹消（二軍降格）処理
        # 元々一軍にいたが、新編成で外れた選手
        demoted = old_roster_set - new_roster_set
        for p_idx in demoted:
            if 0 <= p_idx < len(t.players):
                p = t.players[p_idx]
                
                # 初回保存時は降格ペナルティなし（単純にファームへ移動のみ）
                if not is_first_save:
                    p.days_until_promotion = 10  # 10日間の再登録禁止
                
                p.team_level = TeamLevel.SECOND
                
                # リスト更新
                if p_idx in t.active_roster:
                    t.active_roster.remove(p_idx)
                if p_idx not in t.farm_roster:
                    t.farm_roster.append(p_idx)
                    
        # 2. 昇格処理
        # 新編成で追加された選手
        promoted = new_roster_set - old_roster_set
        for p_idx in promoted:
            if 0 <= p_idx < len(t.players):
                p = t.players[p_idx]
                p.days_until_promotion = 0 # リセット
                p.team_level = TeamLevel.FIRST
                
                if p_idx not in t.active_roster:
                    t.active_roster.append(p_idx)
                if p_idx in t.farm_roster:
                    t.farm_roster.remove(p_idx)
                if p_idx in t.third_roster:
                    t.third_roster.remove(p_idx)

        # 各種オーダーリストの反映
        t.current_lineup = list(self.edit_state['current_lineup'])
        t.lineup_positions = list(self.edit_state['lineup_positions'])
        t.bench_batters = list(self.edit_state['bench_batters'])
        t.rotation = list(self.edit_state['rotation'])
        t.setup_pitchers = list(self.edit_state['setup_pitchers'])
        t.closers = list(self.edit_state['closers'])
        
        # 初回保存でオーダー初期化フラグを立てる
        t.order_initialized = True
        
        self.order_saved.emit()
        self._load_team_data() # 状態リセット
        self._refresh_all() # 画面更新
        self._update_status_label()
        QMessageBox.information(self, "保存完了", "オーダーを保存しました。\n一軍から外れた選手は10日間再登録できません。")

    def _discard_changes(self):
        if not self.current_team: return
        self._load_team_data() # リロード（変更破棄）
        self._refresh_all()

    def _open_best_order_settings(self):
        """ベストオーダー設定ウィンドウを開く"""
        from PySide6.QtWidgets import QDialog
        
        dialog = QDialog(self)
        dialog.setWindowTitle("ベストオーダー設定")
        dialog.setFixedSize(1100, 800)
        dialog.setStyleSheet(f"background-color: {self.theme.bg_dark}; color: {self.theme.text_primary};")
        
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create separate OrderPage instance in Best Order Mode
        best_order_page = OrderPage(None, is_best_order_mode=True)
        best_order_page.set_game_state(self.game_state)
        # Ensure it shows the same team
        best_order_page.current_team = self.current_team
        best_order_page._ensure_lists_initialized()
        best_order_page._load_team_data()
        best_order_page._refresh_all()
        
        layout.addWidget(best_order_page)
        
        dialog.exec()
        
    def _clear_best_order(self):
        if not self.current_team: return
        msg = "ベストオーダー設定を削除してもよろしいですか？"
        reply = QMessageBox.question(self, "確認", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.current_team.best_order = None
            self._load_team_data()
            self._refresh_all()
            QMessageBox.information(self, "完了", "ベストオーダー設定を削除しました。")

    def _refresh_all(self):
        if not self.current_team or not self.edit_state: return
        
        self._refresh_lineup_table()
        self._refresh_bench_table()
        self._refresh_batter_farm_list()
        self._refresh_rotation_table()
        self._refresh_bullpen_table()
        self._refresh_pitcher_farm_list()
        self._update_status_label()

    def _get_active_player_count(self) -> int:
        if not self.current_team: return 0
        # チームのactive_rosterから直接取得（自動昇格後も正確に反映）
        if hasattr(self.current_team, 'active_roster'):
            return len(self.current_team.active_roster)
        # フォールバック: edit_stateから計算
        if not self.edit_state: return 0
        active_set = set()
        active_set.update([x for x in self.edit_state['current_lineup'] if x >= 0])
        active_set.update([x for x in self.edit_state['bench_batters'] if x >= 0])
        active_set.update([x for x in self.edit_state['rotation'] if x >= 0])
        active_set.update([x for x in self.edit_state['setup_pitchers'] if x >= 0])
        active_set.update([x for x in self.edit_state['closers'] if x >= 0])
        active_set.update([x for x in self.edit_state.get('bench_pitchers', []) if x >= 0])
        return len(active_set)

    def _update_status_label(self):
        if not self.current_team: return
        count = self._get_active_player_count()
        limit = 31
        if hasattr(self.current_team, 'ACTIVE_ROSTER_LIMIT'):
            limit = self.current_team.ACTIVE_ROSTER_LIMIT

        self.status_label.setText(f"一軍登録数: {count}/{limit}")
        color = self.theme.success if count <= limit else self.theme.danger
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold; margin-left: 20px;")

    # === Data Helpers ===
    
    def _create_item(self, value, align=Qt.AlignCenter, rank_color=False, pos_badge=None, is_star=False, sort_val=None, text_color=None):
        item = SortableTableWidgetItem()
        
        if rank_color:
            if sort_val is None: sort_val = value
            item.setData(Qt.UserRole, value)
            item.setData(Qt.DisplayRole, "")
        else:
            item.setText(str(value))
            if pos_badge:
                item.setBackground(QColor(get_pos_color(pos_badge)))
                item.setForeground(Qt.white)
                font = QFont()
                font.setBold(True)
                item.setFont(font)
            elif is_star:
                item.setForeground(QColor("#FFD700"))
                font = QFont()
                font.setBold(True)
                item.setFont(font)
        
        if text_color:
            item.setForeground(text_color)

        item.setTextAlignment(align)
        
        if sort_val is not None:
             item.setData(Qt.UserRole, sort_val)
        elif not rank_color:
            try:
                if isinstance(value, str) and "★" in value:
                    num = int(value.replace("★", ""))
                    item.setData(Qt.UserRole, num)
                elif isinstance(value, (int, float)):
                    item.setData(Qt.UserRole, value)
            except:
                pass
            
        return item

    def _create_condition_item(self, player):
        item = SortableTableWidgetItem()
        item.setTextAlignment(Qt.AlignCenter)
        
        # ★登録抹消中（再登録待機期間）のチェック
        if hasattr(player, 'days_until_promotion') and player.days_until_promotion > 0:
            item.setText(f"抹{player.days_until_promotion}") # "抹消"だと幅をとるので短縮
            item.setForeground(QColor("#e74c3c")) # 赤色で強調
            font = QFont()
            font.setBold(True)
            item.setFont(font)
            item.setToolTip(f"出場選手登録抹消中: 再登録まであと{player.days_until_promotion}日")
            item.setData(Qt.UserRole, -99)
            return item
        
        if hasattr(player, 'is_injured') and player.is_injured:
            item.setText(f"残{player.injury_days}日")
            item.setForeground(QColor("#95a5a6"))
            item.setToolTip(f"怪我: 残り{player.injury_days}日")
            item.setData(Qt.UserRole, -1)
        else:
            cond = player.condition
            if cond >= 8:
                text, color, sort_val = "絶", "#e67e22", 5
            elif cond >= 6:
                text, color, sort_val = "好", "#f1c40f", 4
            elif cond >= 4:
                text, color, sort_val = "普", "#ecf0f1", 3
            elif cond >= 2:
                text, color, sort_val = "不", "#3498db", 2
            else:
                text, color, sort_val = "絶", "#9b59b6", 1
            
            item.setText(text)
            item.setForeground(QColor(color))
            font = QFont()
            font.setBold(True)
            item.setFont(font)
            item.setData(Qt.UserRole, sort_val)
            
        return item

    def _create_fatigue_item(self, player):
        """疲労度アイテムを作成（0-100、色分け）"""
        item = SortableTableWidgetItem()
        item.setTextAlignment(Qt.AlignCenter)
        
        fatigue = round(getattr(player, 'fatigue', 0))  # 四捨五入で整数に
        
        if fatigue <= 30:
            color = "#27ae60"  # 緑（元気）
        elif fatigue <= 60:
            color = "#f39c12"  # 黄（疲労）
        else:
            color = "#e74c3c"  # 赤（限界）
        
        item.setText(str(fatigue))
        item.setForeground(QColor(color))
        item.setData(Qt.UserRole, fatigue)
        
        if fatigue > 60:
            font = QFont()
            font.setBold(True)
            item.setFont(font)
        
        return item

    def _format_aptitude_delegate(self, p):
        main_pos = self._short_pos_name(p.position.value)
        subs = []
        if hasattr(p.stats, 'defense_ranges'):
            sorted_ranges = sorted(p.stats.defense_ranges.items(), key=lambda x: x[1], reverse=True)
            for pos_name, val in sorted_ranges:
                if pos_name != p.position.value and val > 10: 
                    subs.append(self._short_pos_name(pos_name))
        sub_str = " ".join(subs)
        return f"{main_pos}|{sub_str}"

    def _short_pos_name(self, long_name):
        mapping = {"投手":"投","捕手":"捕","一塁手":"一","二塁手":"二","三塁手":"三",
                   "遊撃手":"遊","左翼手":"左","中堅手":"中","右翼手":"右"}
        return mapping.get(long_name, long_name[0])

    # === Table Fillers using edit_state ===

    def _refresh_lineup_table(self):
        team = self.current_team
        table = self.lineup_table
        table.setRowCount(9)
        pos_order = {"捕": 2, "一": 3, "二": 4, "三": 5, "遊": 6, "左": 7, "中": 8, "右": 9, "DH": 10}
        
        current_lineup = self.edit_state['current_lineup']
        lineup_positions = self.edit_state['lineup_positions']
            
        for i in range(9):
            p_idx = -1
            if i < len(current_lineup):
                p_idx = current_lineup[i]
            
            pos_label = lineup_positions[i]
            
            table.setItem(i, 0, self._create_item(f"{i+1}"))
            
            pos_item = self._create_item(pos_label, pos_badge=pos_label)
            pos_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled)
            table.setItem(i, 1, pos_item)
            
            if p_idx != -1 and p_idx < len(team.players):
                p = team.players[p_idx]
                is_injured = hasattr(p, 'is_injured') and p.is_injured
                row_color = QColor("#95a5a6") if is_injured else None

                table.setItem(i, 2, self._create_condition_item(p))
                table.setItem(i, 3, self._create_fatigue_item(p))  # 疲労
                table.setItem(i, 4, self._create_item(p.name, Qt.AlignLeft, text_color=row_color))
                
                s = p.stats
                table.setItem(i, 5, self._create_item(s.contact, rank_color=True))
                table.setItem(i, 6, self._create_item(s.power, rank_color=True))
                table.setItem(i, 7, self._create_item(s.speed, rank_color=True))
                table.setItem(i, 8, self._create_item(s.arm, rank_color=True))
                table.setItem(i, 9, self._create_item(s.fielding, rank_color=True))
                
                apt_data = self._format_aptitude_delegate(p)
                p_pos_char = self._short_pos_name(p.position.value)
                sort_val = pos_order.get(p_pos_char, 99)
                table.setItem(i, 10, self._create_item(apt_data, sort_val=sort_val, text_color=row_color))
                table.setItem(i, 11, self._create_item(f"★{p.overall_rating}", is_star=True))
                
                for c in range(table.columnCount()):
                    if table.item(i, c): table.item(i, c).setData(ROLE_PLAYER_IDX, p_idx)
            else:
                self._clear_row(table, i, 2)

    def _refresh_bench_table(self):
        team = self.current_team
        table = self.bench_table
        bench_batters = self.edit_state['bench_batters']
        table.setRowCount(len(bench_batters) + 2)
        pos_order = {"捕": 2, "一": 3, "二": 4, "三": 5, "遊": 6, "左": 7, "中": 8, "右": 9, "DH": 10}
        
        for i, p_idx in enumerate(bench_batters):
            if p_idx != -1 and p_idx < len(team.players):
                p = team.players[p_idx]
                main_pos = self._short_pos_name(p.position.value)
                is_injured = hasattr(p, 'is_injured') and p.is_injured
                row_color = QColor("#95a5a6") if is_injured else None

                table.setItem(i, 0, self._create_item(main_pos, text_color=row_color))
                table.setItem(i, 1, self._create_condition_item(p))
                table.setItem(i, 2, self._create_fatigue_item(p))  # 疲労
                table.setItem(i, 3, self._create_item(p.name, Qt.AlignLeft, text_color=row_color))
                
                s = p.stats
                table.setItem(i, 4, self._create_item(s.contact, rank_color=True))
                table.setItem(i, 5, self._create_item(s.power, rank_color=True))
                table.setItem(i, 6, self._create_item(s.speed, rank_color=True))
                table.setItem(i, 7, self._create_item(s.arm, rank_color=True))
                table.setItem(i, 8, self._create_item(s.fielding, rank_color=True))
                
                apt_data = self._format_aptitude_delegate(p)
                p_pos_char = main_pos
                sort_val = pos_order.get(p_pos_char, 99)
                table.setItem(i, 9, self._create_item(apt_data, sort_val=sort_val, text_color=row_color))
                table.setItem(i, 10, self._create_item(f"★{p.overall_rating}", is_star=True))
                
                for c in range(table.columnCount()):
                    if table.item(i, c): table.item(i, c).setData(ROLE_PLAYER_IDX, p_idx)
            else:
                self._clear_row(table, i, 0)
        
        for i in range(len(bench_batters), table.rowCount()):
             self._clear_row(table, i, 0)

    def _refresh_batter_farm_list(self):
        team = self.current_team
        table = self.farm_batter_table
        
        # edit_state から登録済み選手を除外
        active_ids = set(self.edit_state['current_lineup'] + self.edit_state['bench_batters'])
        
        candidates = []
        pos_filter = self.batter_pos_filter.currentText()
        
        for i, p in enumerate(team.players):
            if p.position.value != "投手" and i not in active_ids:
                if p.is_developmental: continue
                if pos_filter != "全ポジション" and p.position.value != pos_filter:
                    continue
                candidates.append((i, p))
        
        pos_order = {"捕": 2, "一": 3, "二": 4, "三": 5, "遊": 6, "左": 7, "中": 8, "右": 9, "DH": 10}

        table.setRowCount(len(candidates))
        for i, (p_idx, p) in enumerate(candidates):
            is_injured = hasattr(p, 'is_injured') and p.is_injured
            row_color = QColor("#95a5a6") if is_injured else None
            
            # 再登録待機中の選手はグレーアウト
            if hasattr(p, 'days_until_promotion') and p.days_until_promotion > 0:
                row_color = QColor("#7f8c8d")

            table.setItem(i, 0, self._create_condition_item(p))
            table.setItem(i, 1, self._create_item(p.name, Qt.AlignLeft, text_color=row_color))
            table.setItem(i, 2, self._create_item(p.age, text_color=row_color)) 
            
            s = p.stats
            table.setItem(i, 3, self._create_item(s.contact, rank_color=True))
            table.setItem(i, 4, self._create_item(s.power, rank_color=True))
            table.setItem(i, 5, self._create_item(s.speed, rank_color=True))
            table.setItem(i, 6, self._create_item(s.arm, rank_color=True))
            table.setItem(i, 7, self._create_item(s.fielding, rank_color=True))
            
            apt_data = self._format_aptitude_delegate(p)
            p_pos_char = self._short_pos_name(p.position.value)
            sort_val = pos_order.get(p_pos_char, 99)
            
            apt_item = self._create_item(apt_data, sort_val=sort_val, text_color=row_color) 
            table.setItem(i, 8, apt_item)
            table.setItem(i, 9, self._create_item(f"★{p.overall_rating}", is_star=True))
            
            for c in range(table.columnCount()):
                if table.item(i, c): table.item(i, c).setData(ROLE_PLAYER_IDX, p_idx)

        header = table.horizontalHeader()
        table.sortItems(header.sortIndicatorSection(), header.sortIndicatorOrder())

    def _refresh_rotation_table(self):
        table = self.rotation_table
        table.setRowCount(8)
        rotation = self.edit_state['rotation']
        for i in range(8):
            p_idx = -1
            if i < len(rotation):
                p_idx = rotation[i]
            self._fill_pitcher_row_role(table, i, "先発", p_idx, show_interval=True)

    def _refresh_bullpen_table(self):
        table = self.bullpen_table
        table.setRowCount(10)
        setup = self.edit_state['setup_pitchers']
        closers = self.edit_state['closers']
        
        for i in range(8):
            p_idx = -1
            if i < len(setup):
                p_idx = setup[i]
            self._fill_pitcher_row_role(table, i, "中継", p_idx)
            
        for i in range(2):
            p_idx = -1
            if i < len(closers):
                p_idx = closers[i]
            self._fill_pitcher_row_role(table, 8 + i, "抑え", p_idx)

    def _fill_pitcher_row_role(self, table, row, role_lbl, p_idx, show_interval=False):
        table.setItem(row, 0, self._create_item(role_lbl, pos_badge=role_lbl[0]))
        if p_idx != -1 and p_idx < len(self.current_team.players):
            p = self.current_team.players[p_idx]
            self._fill_pitcher_data(table, row, p, p_idx, start_col=1, show_interval=show_interval)
        else:
            self._clear_row(table, row, 1)

    def _refresh_pitcher_farm_list(self):
        team = self.current_team
        table = self.farm_pitcher_table
        
        active_ids = set([x for x in self.edit_state['rotation'] if x >= 0])
        active_ids.update([x for x in self.edit_state['setup_pitchers'] if x >= 0])
        active_ids.update([x for x in self.edit_state['closers'] if x >= 0])
        
        candidates = []
        type_filter = self.pitcher_type_filter.currentText()
        
        for i, p in enumerate(team.players):
            if p.position.value == "投手" and i not in active_ids:
                if p.is_developmental: continue
                # None check for pitch_type
                p_type_val = p.pitch_type.value if p.pitch_type else "不明"
                if type_filter != "全タイプ" and p_type_val != type_filter:
                    # Fallback: check aptitudes if None? For now just skip logic or allow match if "All"
                    # If type_filter is specific (e.g. "Start"), and p_type is None, we might look at aptitude?
                    # But simpler: if None, valid only for "全タイプ" (already checked)
                    continue
                candidates.append((i, p))
                
        table.setRowCount(len(candidates))
        for i, (p_idx, p) in enumerate(candidates):
            is_injured = hasattr(p, 'is_injured') and p.is_injured
            row_color = QColor("#95a5a6") if is_injured else None
            
            # 再登録待機中の選手はグレーアウト
            if hasattr(p, 'days_until_promotion') and p.days_until_promotion > 0:
                row_color = QColor("#7f8c8d")

            role = p.pitch_type.value[:2] if p.pitch_type else "－"
            table.setItem(i, 0, self._create_item(role, text_color=row_color))
            table.setItem(i, 1, self._create_condition_item(p))
            table.setItem(i, 2, self._create_item(p.name, Qt.AlignLeft, text_color=row_color))
            table.setItem(i, 3, self._create_item(p.age, text_color=row_color))
            
            kmh = p.stats.speed_to_kmh()
            table.setItem(i, 4, self._create_item(f"{kmh}km", sort_val=kmh, text_color=row_color))
            
            table.setItem(i, 5, self._create_item(p.stats.control, rank_color=True))
            table.setItem(i, 6, self._create_item(p.stats.stamina, rank_color=True))
            table.setItem(i, 7, self._create_item(p.stats.stuff, rank_color=True))
            
            st = p.get_aptitude_symbol(p.starter_aptitude)
            rl = p.get_aptitude_symbol(p.middle_aptitude)
            cl = p.get_aptitude_symbol(p.closer_aptitude)
            table.setItem(i, 8, self._create_item(st, sort_val=p.starter_aptitude, text_color=row_color))
            table.setItem(i, 9, self._create_item(rl, sort_val=p.middle_aptitude, text_color=row_color))
            table.setItem(i, 10, self._create_item(cl, sort_val=p.closer_aptitude, text_color=row_color))
            table.setItem(i, 11, self._create_item(f"★{p.overall_rating}", is_star=True))

            for c in range(table.columnCount()):
                if table.item(i, c): table.item(i, c).setData(ROLE_PLAYER_IDX, p_idx)
                
        header = table.horizontalHeader()
        table.sortItems(header.sortIndicatorSection(), header.sortIndicatorOrder())

    def _fill_pitcher_data(self, table, row, p, p_idx, start_col, show_interval=False):
        is_injured = hasattr(p, 'is_injured') and p.is_injured
        row_color = QColor("#95a5a6") if is_injured else None

        table.setItem(row, start_col, self._create_condition_item(p))
        table.setItem(row, start_col+1, self._create_fatigue_item(p))  # 疲労
        table.setItem(row, start_col+2, self._create_item(p.name, Qt.AlignLeft, text_color=row_color))
        
        current_col = start_col + 3
        if show_interval:
             int_val = getattr(p, 'rotation_interval', 6)
             item = self._create_item(f"中{int_val}日")
             item.setForeground(QColor("#3498db"))
             font = QFont()
             font.setBold(True)
             item.setFont(font)
             item.setData(ROLE_PLAYER_IDX, p_idx) # Ensure ID is set
             table.setItem(row, current_col, item)
             current_col += 1

        kmh = p.stats.speed_to_kmh()
        table.setItem(row, current_col, self._create_item(f"{kmh}km", text_color=row_color))
        
        table.setItem(row, current_col+1, self._create_item(p.stats.control, rank_color=True))
        table.setItem(row, current_col+2, self._create_item(p.stats.stamina, rank_color=True))
        table.setItem(row, current_col+3, self._create_item(p.stats.stuff, rank_color=True))
        
        st = p.get_aptitude_symbol(p.starter_aptitude)
        rl = p.get_aptitude_symbol(p.middle_aptitude)
        cl = p.get_aptitude_symbol(p.closer_aptitude)
        table.setItem(row, current_col+4, self._create_item(st, sort_val=p.starter_aptitude, text_color=row_color))
        table.setItem(row, current_col+5, self._create_item(rl, sort_val=p.middle_aptitude, text_color=row_color))
        table.setItem(row, current_col+6, self._create_item(cl, sort_val=p.closer_aptitude, text_color=row_color))
        table.setItem(row, current_col+7, self._create_item(f"★{p.overall_rating}", is_star=True))

        for c in range(table.columnCount()):
            if table.item(row, c): table.item(row, c).setData(ROLE_PLAYER_IDX, p_idx)

    def _clear_row(self, table, row, start_col):
        for c in range(start_col, table.columnCount()):
            table.setItem(row, c, QTableWidgetItem(""))
        if start_col < table.columnCount():
            table.setItem(row, start_col, QTableWidgetItem("---"))

    def _on_rotation_cell_clicked(self, row, col):
        table = self.rotation_table
        # Interval is at column 4
        if col == 4:
            item = table.item(row, col)
            if not item: return
            p_idx = item.data(ROLE_PLAYER_IDX)
            
            if p_idx is None or p_idx == -1: return
            if p_idx >= len(self.current_team.players): return
            
            p = self.current_team.players[p_idx]
            curr = getattr(p, 'rotation_interval', 6)
            
            curr = getattr(p, 'rotation_interval', 6)
            
            items = [f"中{i}日" for i in range(1, 11)]
            current_text = f"中{curr}日"
            current_idx = 5 # Default to 6th item (index 5)
            if current_text in items: current_idx = items.index(current_text)
            
            val, ok = QInputDialog.getItem(self, "登板間隔設定", f"{p.name} の登板間隔:", items, current_idx, False)
            if ok:
                days = int(val.replace("中", "").replace("日", ""))
                p.rotation_interval = days
                self._refresh_rotation_table()

    def _on_table_changed(self, table):
        if not hasattr(table, 'dropped_player_idx'): return
        p_idx = table.dropped_player_idx
        row = table.dropped_target_row
        
        # ★ペナルティチェック: 再登録待機中の選手を一軍枠（スタメン・ベンチ・投手陣）へ移動しようとした場合
        player = self.current_team.players[p_idx]
        is_target_active = False
        if table in [self.lineup_table, self.bench_table, self.rotation_table, self.bullpen_table]:
            is_target_active = True
        
        if is_target_active and hasattr(player, 'days_until_promotion') and player.days_until_promotion > 0:
            QMessageBox.warning(self, "登録不可", f"この選手は登録抹消中のため、一軍登録できません。\n再登録可能まであと {player.days_until_promotion} 日です。")
            del table.dropped_player_idx
            self._refresh_all() # 変更を元に戻す
            return
        
        # ★怪我人チェック: 怪我人をスタメンに入れようとした場合のみ禁止（ベンチはOK）
        if table == self.lineup_table and player.is_injured:
            QMessageBox.warning(self, "出場不可", f"この選手は怪我のためスタメン起用できません。")
            del table.dropped_player_idx
            self._refresh_all()
            return

        # 変更があればフラグを立てる
        self._mark_as_changed()
        
        # edit_state を操作
        state = self.edit_state
        
        source_list = None
        source_idx = -1
        
        if p_idx in state['current_lineup']:
            source_list = state['current_lineup']
            source_idx = state['current_lineup'].index(p_idx)
        elif p_idx in state['bench_batters']:
            source_list = state['bench_batters']
            source_idx = state['bench_batters'].index(p_idx)
        elif p_idx in state['rotation']:
            source_list = state['rotation']
            source_idx = state['rotation'].index(p_idx)
        elif p_idx in state['setup_pitchers']:
            source_list = state['setup_pitchers']
            source_idx = state['setup_pitchers'].index(p_idx)
        elif p_idx in state['closers']:
            source_list = state['closers']
            source_idx = state['closers'].index(p_idx)
            
        target_list = None
        target_p_idx = -1
        
        if table == self.lineup_table:
            target_list = state['current_lineup']
            while len(target_list) <= row: target_list.append(-1)
            target_p_idx = target_list[row]
            
        elif table == self.bench_table:
            target_list = state['bench_batters']
            while len(target_list) <= row: target_list.append(-1)
            target_p_idx = target_list[row]
            
        elif table == self.rotation_table:
            target_list = state['rotation']
            while len(target_list) <= row: target_list.append(-1)
            target_p_idx = target_list[row]
            
        elif table == self.bullpen_table:
            if row >= 8: # Closer
                target_list = state['closers']
                c_row = row - 8
                while len(target_list) <= c_row: target_list.append(-1)
                target_p_idx = target_list[c_row]
                row = c_row 
            else:
                target_list = state['setup_pitchers']
                while len(target_list) <= row: target_list.append(-1)
                target_p_idx = target_list[row]
                
        if target_list is not None:
             target_list[row] = p_idx
        
        if source_list is not None:
             if target_list is not None:
                 # Swap: put target's old player into source's old slot
                 if source_idx < len(source_list):
                      source_list[source_idx] = target_p_idx
             else:
                 # Remove: target is farm/None, so just clear source slot
                 if source_idx < len(source_list):
                      source_list[source_idx] = -1

        self._refresh_all()
        del table.dropped_player_idx

    def _on_pos_swapped(self, r1, r2):
        pos_list = self.edit_state['lineup_positions']
        if r1 < 9 and r2 < 9:
            pos_list[r1], pos_list[r2] = pos_list[r2], pos_list[r1]
            self._mark_as_changed()
            self._refresh_lineup_table()

    def _auto_fill(self):
        if not self.current_team: return
        t = self.current_team
        
        # 自動編成も edit_state 上で行う
        self._mark_as_changed()
        
        state = self.edit_state
        # 初期化
        state['current_lineup'] = [-1] * 9
        state['lineup_positions'] = [""] * 9
        state['bench_batters'] = []
        state['rotation'] = [-1] * 8
        state['setup_pitchers'] = [-1] * 8 
        state['closers'] = [-1] * 2

        TOTAL_LIMIT = 31
        if hasattr(t, 'ACTIVE_ROSTER_LIMIT'):
            TOTAL_LIMIT = t.ACTIVE_ROSTER_LIMIT
            
        # 投手15人/野手16人の固定配分
        PITCHER_TARGET = 15
        BATTER_TARGET = 16

        active_roster_set = set(t.active_roster)
        used_indices = set()
        
        # Get auto order priority from settings
        order_priority = "ability"  # default
        if self.game_state and hasattr(self.game_state, 'auto_order_priority'):
            order_priority = self.game_state.auto_order_priority

        # ヘルパー関数
        def get_incumbency_mult(p_idx):
            return 1.15 if p_idx in active_roster_set else 1.0

        def get_condition_mult(p):
            # 設定に基づいて調子の影響度を変更
            if order_priority == "condition":
                # 調子優先: より大きな影響
                return 1.0 + (p.condition - 5) * 0.15
            elif order_priority == "balanced":
                # バランス: 中程度の影響
                return 1.0 + (p.condition - 5) * 0.10
            else:
                # 能力優先: 小さな影響
                return 1.0 + (p.condition - 5) * 0.03

        def get_batting_score(p, p_idx):
            s = p.stats
            if order_priority == "condition":
                # 調子優先: 基礎能力は抑えめ、調子を重視
                val = (s.contact * 0.8 + s.power * 0.8 + s.speed * 0.4 + s.eye * 0.4)
            elif order_priority == "balanced":
                # バランス
                val = (s.contact * 0.9 + s.power * 1.0 + s.speed * 0.5 + s.eye * 0.5)
            else:
                # 能力優先
                val = (s.contact * 1.0 + s.power * 1.2 + s.speed * 0.5 + s.eye * 0.5)
            return val * get_condition_mult(p) * get_incumbency_mult(p_idx)

        def get_defense_score(p, pos_name_long):
            apt = p.stats.defense_ranges.get(pos_name_long, 0)
            if apt < 20: return 0
            s = p.stats
            def_val = (apt * 1.5 + s.error * 0.5 + s.arm * 0.5)
            return def_val
            
        def get_pitcher_score(p, role, p_idx):
            s = p.stats
            base = s.overall_pitching() * 99
            apt_mult = 1.0
            if role == 'starter':
                apt_mult = p.starter_aptitude / 50.0
                base += s.stamina * 0.5
            elif role == 'closer':
                apt_mult = p.closer_aptitude / 50.0
                base += (s.velocity - 130) * 2 + s.stuff * 0.5
            else:
                apt_mult = p.middle_aptitude / 50.0
            return base * apt_mult * get_condition_mult(p) * get_incumbency_mult(p_idx)

        def is_available(p_idx, p):
            if p.is_injured: return False
            if hasattr(p, 'days_until_promotion') and p.days_until_promotion > 0: return False
            return True

        # --- ベストオーダー適用 (通常モードかつ設定ある場合) ---
        bo = getattr(t, 'best_order', None)
        has_best_order = (bo is not None and not self.is_best_order_mode)
        
        if has_best_order:
            # 辞書形式チェック
            if isinstance(bo, list): 
                # 旧形式互換（スタメンのみ）
                bo_lineup = bo
                bo_pos = [""] * 9
                bo_rot = [-1]*8
                bo_setup = [-1]*8
                bo_closer = [-1]*2
            else:
                bo_lineup = bo.get('current_lineup', [-1]*9)
                bo_pos = bo.get('lineup_positions', [""]*9)
                bo_rot = bo.get('rotation', [-1]*8)
                bo_setup = bo.get('setup_pitchers', [-1]*8)
                bo_closer = bo.get('closers', [-1]*2)

            # 1. 投手（ローテ・勝ちパ）の固定
            # ローテーション
            for i, p_idx in enumerate(bo_rot):
                if i < 8 and p_idx != -1 and p_idx < len(t.players):
                    if is_available(p_idx, t.players[p_idx]):
                        state['rotation'][i] = p_idx
                        used_indices.add(p_idx)
            
            # クローザー
            for i, p_idx in enumerate(bo_closer):
                if i < 2 and p_idx != -1 and p_idx < len(t.players):
                    if is_available(p_idx, t.players[p_idx]):
                        state['closers'][i] = p_idx
                        used_indices.add(p_idx)
            
            # セットアッパー
            for i, p_idx in enumerate(bo_setup):
                if i < 8 and p_idx != -1 and p_idx < len(t.players):
                    if is_available(p_idx, t.players[p_idx]):
                        state['setup_pitchers'][i] = p_idx
                        used_indices.add(p_idx)
            
            # 2. 野手スタメンの固定
            for i, p_idx in enumerate(bo_lineup):
                pos_str = bo_pos[i] if i < len(bo_pos) else ""
                if i < 9 and p_idx != -1 and p_idx < len(t.players):
                    if is_available(p_idx, t.players[p_idx]):
                        state['current_lineup'][i] = p_idx
                        state['lineup_positions'][i] = pos_str
                        used_indices.add(p_idx)
        
        # --- 残りの枠を自動充填 ---
        
        # 1. 投手充填
        pitchers = [i for i, p in enumerate(t.players) 
                   if p.position.value == "投手" and not p.is_developmental 
                   and is_available(i, p) and i not in used_indices]
        
        # Rotation gaps
        for i in range(6): # 基本6人ローテ
            if state['rotation'][i] == -1:
                # Find best starter
                cands = sorted(pitchers, key=lambda x: get_pitcher_score(t.players[x], 'starter', x), reverse=True)
                if cands:
                     best = cands[0]
                     state['rotation'][i] = best
                     used_indices.add(best)
                     pitchers.remove(best)
        
        remaining_pitchers = pitchers
        
        # Closer gaps
        for i in range(1): # Main closer
            if state['closers'][0] == -1:
                cands = sorted(remaining_pitchers, key=lambda x: get_pitcher_score(t.players[x], 'closer', x), reverse=True)
                if cands:
                    best = cands[0]
                    state['closers'][0] = best
                    used_indices.add(best)
                    remaining_pitchers.remove(best)

        # Setup/Relief gaps
        # Fill rest of active limit
        used_p_count = len([x for x in state['rotation'] if x != -1]) + len([x for x in state['closers'] if x != -1]) + len([x for x in state['setup_pitchers'] if x != -1])
        setup_limit = max(0, PITCHER_TARGET - used_p_count)
        
        current_setup_idx = 0
        remaining_pitchers.sort(key=lambda x: get_pitcher_score(t.players[x], 'relief', x), reverse=True)
        
        while setup_limit > 0 and remaining_pitchers:
            # Find empty slot
            while current_setup_idx < 8 and state['setup_pitchers'][current_setup_idx] != -1:
                current_setup_idx += 1
            if current_setup_idx >= 8: break
            
            p_idx = remaining_pitchers.pop(0)
            state['setup_pitchers'][current_setup_idx] = p_idx
            used_indices.add(p_idx)
            setup_limit -= 1

        # 2. 野手スタメン充填
        batters = [i for i, p in enumerate(t.players) 
                  if p.position.value != "投手" and not p.is_developmental
                  and is_available(i, p) and i not in used_indices]

        # 埋まっていないポジションを特定
        pos_map = {
            "捕": "捕手", "遊": "遊撃手", "二": "二塁手", "中": "中堅手", 
            "三": "三塁手", "右": "右翼手", "左": "左翼手", "一": "一塁手"
        }
        
        # すでに埋まっているポジションの確認
        filled_positions_count = {}
        for p_str in state['lineup_positions']:
            if p_str and p_str in pos_map: # Valid pos
                # スタメンでそのポジションに選手がいるか
                idx = state['lineup_positions'].index(p_str)
                if state['current_lineup'][idx] != -1:
                   filled_positions_count[p_str] = filled_positions_count.get(p_str, 0) + 1
        
        # 必要なポジション (DH含む)
        required_pos = ["捕", "遊", "二", "中", "三", "右", "左", "一", "DH"]
        
        # ポジションごとにベストを選出（まだ埋まってない場合）
        selected_starters = {} # short_pos -> player_idx
        temp_used_in_logic = set()

        for short_pos in required_pos:
            # DH is special
            if short_pos == "DH": continue
            
            # Check if already satisfied in lineup
            # Note: There could be multiple players at same position in current_lineup if Best Order set it so. (e.g. 2 catchers?). 
            # But usually we need 1 of each field pos.
            if filled_positions_count.get(short_pos, 0) >= 1:
                continue
                
            long_pos = pos_map[short_pos]
            best_idx = -1
            best_score = -1
            
            for idx in batters:
                if idx in temp_used_in_logic: continue
                p = t.players[idx]
                
                apt = p.stats.defense_ranges.get(long_pos, 0)
                if apt < 20: continue 
                
                def_weight = 1.0
                if short_pos in ["捕", "遊", "二"]: def_weight = 1.5
                score = (get_batting_score(p, idx) + get_defense_score(p, long_pos) * def_weight)
                
                if score > best_score:
                    best_score = score
                    best_idx = idx
            
            if best_idx != -1:
                selected_starters[short_pos] = best_idx
                temp_used_in_logic.add(best_idx)

        # DH Selection (if empty)
        if state['lineup_positions'].count("DH") == 0: # DH not fixed (or fixed to empty)
             # Find empty slot that is meant for DH? Or just pick best hitter?
             # If Best Order fixed DH, it's handled. If not, pick DH.
             dh_candidates = [i for i in batters if i not in temp_used_in_logic]
             dh_candidates.sort(key=lambda i: get_batting_score(t.players[i], i), reverse=True)
             if dh_candidates:
                 selected_starters["DH"] = dh_candidates[0]
                 temp_used_in_logic.add(dh_candidates[0])

        # Assign selected starters to empty slots
        # Need to determine optimal batting order for these NEWLY selected players + EXISTING players?
        # Re-shuffling the WHOLE lineup might break Best Order's specific batting slots.
        # Requirement: "Auto-fill should respect Best Order". Usually means "Keep Best Order players in their slots".
        # So we only fill EMPTY slots (`-1`).

        # Collect all players (Fixed + New)
        # But we need to assign positions to the new players.

        for short_pos, p_idx in selected_starters.items():
            # Find an empty slot in lineup?
            # Or append to a list and then assign to empty slots.
            # We need to assign `lineup_positions[i]` too if it's empty.
            
            # Simple approach: Fill first available empty slot
            for i in range(9):
                if state['current_lineup'][i] == -1:
                    state['current_lineup'][i] = p_idx
                    state['lineup_positions'][i] = short_pos
                    used_indices.add(p_idx)
                    break
        
        # 3. ベンチ充填
        remaining_bench = [i for i in enumerate(t.players) if i[0] not in used_indices and i[1].position.value != "投手" and not i[1].is_developmental and is_available(i[0], i[1])]
        remaining_bench_indices = [x[0] for x in remaining_bench]
        remaining_bench_indices.sort(key=lambda x: t.players[x].overall_rating, reverse=True)
        
        bench_limit = max(0, BATTER_TARGET - 9)
        state['bench_batters'] = remaining_bench_indices[:bench_limit]
        
        self._refresh_all()
    
    def _on_player_double_clicked(self, item):
        p_idx = item.data(ROLE_PLAYER_IDX)
        if p_idx is not None and isinstance(p_idx, int) and p_idx >= 0:
            if p_idx < len(self.current_team.players):
                player = self.current_team.players[p_idx]
                self.player_detail_requested.emit(player)