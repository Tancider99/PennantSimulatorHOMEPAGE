# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Farm Swap Page
Manage roster moves between Farm (2nd Team) and Third Team (3rd Team)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QAbstractItemView, QFrame, QMessageBox, QSplitter,
    QStyledItemDelegate, QStyle
)
from PySide6.QtCore import Qt, Signal, QSize, QMimeData, QByteArray, QDataStream, QIODevice, QPoint
from PySide6.QtGui import QColor, QFont, QIcon, QDrag, QPixmap, QPainter, QBrush, QPen

import sys
import os

# パス設定
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.panels import ToolbarPanel
from UI.widgets.tables import SortableTableWidgetItem, RatingDelegate
from models import TeamLevel, Position

# ユーザーロール定義
ROLE_PLAYER_IDX = Qt.UserRole + 1
MIME_PLAYER_DATA = "application/x-pennant-player-data"

def get_pos_color(pos: str) -> str:
    """Return background color code for position badge"""
    if pos == "投": return "#3498db"
    if pos == "捕": return "#27ae60"
    if pos in ["一", "二", "三", "遊"]: return "#e67e22"
    if pos in ["左", "中", "右"]: return "#9b59b6"
    if pos == "DH": return "#e74c3c"
    return "#7f8c8d"

class DefenseDelegate(QStyledItemDelegate):
    """Custom delegate to draw Main Position Large and Sub Positions Small"""
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme

    def paint(self, painter, option, index):
        painter.save()
        
        raw_data = index.data(Qt.DisplayRole)
        text = str(raw_data) if raw_data is not None else ""

        if "|" in text:
            parts = text.split("|", 1)
            main_pos = parts[0]
            sub_pos = parts[1] if len(parts) > 1 else ""
        else:
            main_pos, sub_pos = text, ""

        rect = option.rect
        
        # 1. Main Position (Large)
        if option.state & QStyle.StateFlag.State_Selected:
             painter.setPen(QColor(self.theme.text_primary)) 
        else:
             fg_color = index.model().data(index, Qt.ForegroundRole)
             if isinstance(fg_color, QBrush): 
                 fg_color = fg_color.color()
             painter.setPen(fg_color if fg_color else QColor(self.theme.text_primary))
             
        font = painter.font()
        font.setPointSize(12) 
        font.setBold(True)
        painter.setFont(font)
        
        fm = painter.fontMetrics()
        main_width = fm.horizontalAdvance(main_pos)
        
        main_rect = rect.adjusted(4, 0, 0, 0)
        painter.drawText(main_rect, Qt.AlignLeft | Qt.AlignVCenter, main_pos)
        
        # 2. Sub Positions (Small)
        if sub_pos:
            font.setPointSize(9)
            font.setBold(False)
            painter.setFont(font)
            
            if option.state & QStyle.StateFlag.State_Selected:
                painter.setPen(QColor(self.theme.text_secondary))
            else:
                painter.setPen(QColor(self.theme.text_secondary))
            
            sub_rect = rect.adjusted(main_width + 10, 0, 0, 0)
            painter.drawText(sub_rect, Qt.AlignLeft | Qt.AlignVCenter, sub_pos)
        
        # 3. Draw Bottom Border manually
        painter.setPen(QPen(QColor(self.theme.border_muted), 1))
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())
            
        painter.restore()

class DraggableTableWidget(QTableWidget):
    """ドラッグ＆ドロップ対応のテーブルウィジェット (OrderPageスタイル)"""
    
    # プレイヤーがドロップされたときに発火するシグナル (player_idx)
    itemDropped = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(False) 
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.horizontalHeader().setStretchLastSection(True)
        self.setShowGrid(False)
        self.setFocusPolicy(Qt.ClickFocus)
        
        # ヘッダークリックでのソートを有効化
        header = self.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        header.sectionClicked.connect(self._on_header_clicked)

    def _on_header_clicked(self, logicalIndex):
        header_text = self.horizontalHeaderItem(logicalIndex).text()
        # ソート対象外のカラム
        if header_text in ["選手名", "適正", "守備適正"]:
            return

        header = self.horizontalHeader()
        current_column = header.sortIndicatorSection()
        current_order = header.sortIndicatorOrder()
        
        if current_column != logicalIndex:
            new_order = Qt.DescendingOrder
        else:
            if current_order == Qt.DescendingOrder:
                new_order = Qt.AscendingOrder
            else:
                new_order = Qt.DescendingOrder

        self.sortItems(logicalIndex, new_order)
        header.setSortIndicator(logicalIndex, new_order)

    def startDrag(self, supportedActions):
        """ドラッグ開始時の処理"""
        item = self.currentItem()
        if not item: return

        row = item.row()
        # 名前カラムは通常2番目 (FarmSwapPageの仕様: [Condition, Name, ...])
        name_col = 1
        if self.columnCount() <= 1: name_col = 0
        
        item_data = self.item(row, 0)
        if not item_data: return

        p_idx = item_data.data(ROLE_PLAYER_IDX)
        if p_idx is None: return

        mime = QMimeData()
        data = QByteArray()
        stream = QDataStream(data, QIODevice.WriteOnly)
        stream.writeInt32(p_idx)
        mime.setData(MIME_PLAYER_DATA, data)
        
        name_item = self.item(row, name_col)
        name_text = name_item.text() if name_item else "Player"
        pixmap = self._create_drag_pixmap(name_text)
        
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, pixmap.height() // 2))
        
        drag.exec(Qt.MoveAction)

    def _create_drag_pixmap(self, text):
        width = 200
        height = 40
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        bg_color = QColor("#222222")
        painter.setBrush(bg_color)
        painter.setPen(QPen(QColor("#555555"), 1))
        painter.drawRect(0, 0, width, height)
        
        painter.setPen(Qt.white)
        font = QFont("Yu Gothic UI", 11, QFont.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, text)
        painter.end()
        return pixmap

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(MIME_PLAYER_DATA):
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(MIME_PLAYER_DATA):
            event.setDropAction(Qt.MoveAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """ドロップされたとき"""
        if event.mimeData().hasFormat(MIME_PLAYER_DATA):
            data = event.mimeData().data(MIME_PLAYER_DATA)
            stream = QDataStream(data, QIODevice.ReadOnly)
            p_idx = stream.readInt32()
            
            self.itemDropped.emit(p_idx)
            event.accept()
        else:
            event.ignore()


class FarmSwapPage(QWidget):
    """二軍・三軍 入れ替え管理ページ"""
    
    # 選手詳細画面遷移用シグナル
    player_detail_requested = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.current_team = None
        
        # フィルタ状態 (0: 投手, 1: 野手)
        self.current_filter_mode = "pitcher" 
        
        self.rating_delegate = RatingDelegate(self)
        self.defense_delegate = DefenseDelegate(self.theme)
        
        self._setup_ui()

    def _setup_ui(self):
        """UIレイアウトの作成"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 1. ツールバー（チーム名表示・フィルタ切り替え）
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)

        # 2. メインコンテンツ（左右分割）
        content_frame = QFrame()
        content_frame.setStyleSheet(f"background-color: {self.theme.bg_dark};")
        content_layout = QHBoxLayout(content_frame)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(24)

        # 左側：二軍リスト
        self.farm_panel = self._create_roster_panel("二軍 (Farm)", TeamLevel.SECOND)
        content_layout.addWidget(self.farm_panel, 1)

        # 右側：三軍リスト
        self.third_panel = self._create_roster_panel("三軍 (3rd)", TeamLevel.THIRD)
        content_layout.addWidget(self.third_panel, 1)

        layout.addWidget(content_frame)

    def _create_toolbar(self) -> ToolbarPanel:
        """ツールバーの作成"""
        toolbar = ToolbarPanel()
        toolbar.setFixedHeight(50)

        # チーム名表示
        self.team_label = QLabel("チーム名")
        self.team_label.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; font-size: 16px; margin-left: 12px;")
        toolbar.add_widget(self.team_label)
        
        toolbar.add_stretch()

        # フィルタボタン
        self.filter_pitcher_btn = QPushButton("投手")
        self.filter_pitcher_btn.setCheckable(True)
        self.filter_pitcher_btn.setChecked(True)
        self.filter_pitcher_btn.clicked.connect(lambda: self._set_filter("pitcher"))
        self._apply_filter_btn_style(self.filter_pitcher_btn)
        toolbar.add_widget(self.filter_pitcher_btn)

        self.filter_fielder_btn = QPushButton("野手")
        self.filter_fielder_btn.setCheckable(True)
        self.filter_fielder_btn.clicked.connect(lambda: self._set_filter("fielder"))
        self._apply_filter_btn_style(self.filter_fielder_btn)
        toolbar.add_widget(self.filter_fielder_btn)

        return toolbar

    def _apply_filter_btn_style(self, btn):
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFixedWidth(80)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme.bg_card};
                color: {self.theme.text_secondary};
                border: 1px solid {self.theme.border};
                border-radius: 4px;
                padding: 6px;
                font-weight: bold;
            }}
            QPushButton:checked {{
                background-color: {self.theme.primary};
                color: {self.theme.text_highlight};
                border-color: {self.theme.primary};
            }}
            QPushButton:hover {{
                border-color: {self.theme.primary};
            }}
        """)

    def _create_roster_panel(self, title, level):
        """各軍のリストパネルを作成"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ヘッダー (タイトル + 人数)
        header_layout = QHBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; font-size: 14px;")
        header_layout.addWidget(title_lbl)
        
        count_lbl = QLabel("0人")
        count_lbl.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 13px;")
        header_layout.addWidget(count_lbl)
        header_layout.addStretch()
        
        layout.addLayout(header_layout)

        # テーブル作成 (DraggableTableWidgetを使用)
        table = DraggableTableWidget()
        
        # ダブルクリックで詳細表示
        table.itemDoubleClicked.connect(self._on_player_double_clicked)
        
        # スタイル適用 (OrderPageと同じ)
        table.setStyleSheet(f"""
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

        # ドロップ時のシグナル接続
        if level == TeamLevel.SECOND:
            table.itemDropped.connect(self._on_dropped_to_farm)
            self.farm_table = table
            self.farm_count_lbl = count_lbl
        else:
            table.itemDropped.connect(self._on_dropped_to_third)
            self.third_table = table
            self.third_count_lbl = count_lbl

        layout.addWidget(table)
        return container

    def _setup_table_columns(self, table, is_pitcher):
        """テーブルの列定義を設定 (OrderPage準拠)"""
        # ★修正: 列数が変わる前にデリゲートをクリアしないと、
        # 以前の列のデリゲート設定が残ってしまい、年齢や球速がランク表示される原因になる
        for col in range(table.columnCount()):
            table.setItemDelegateForColumn(col, None)

        table.clear() 
        
        if is_pitcher:
            # OrderPage: ["タイプ", "調", "選手名", "年齢", "球速", "コ", "ス", "変", "先", "中", "抑", "総合"]
            headers = ["タイプ", "調", "選手名", "年齢", "球速", "コ", "ス", "変", "先", "中", "抑", "総合"]
            widths = [45, 30, 130, 40, 50, 35, 35, 35, 35, 35, 35, 45]
            delegate_cols = [5, 6, 7] # コ, ス, 変
        else:
            # OrderPage: ["調", "選手名", "年齢", "ミ", "パ", "走", "肩", "守", "守備適正", "総合"]
            headers = ["調", "選手名", "年齢", "ミ", "パ", "走", "肩", "守", "守備適正", "総合"]
            widths = [30, 130, 40, 35, 35, 35, 35, 35, 80, 45]
            delegate_cols = [3, 4, 5, 6, 7] # ミ, パ, 走, 肩, 守

        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        for i, w in enumerate(widths):
            table.setColumnWidth(i, w)
            
        # レーティング表示用のデリゲート適用
        for col in delegate_cols:
            table.setItemDelegateForColumn(col, self.rating_delegate)
            
        # 守備適正デリゲート (野手のみ)
        if not is_pitcher:
            table.setItemDelegateForColumn(8, self.defense_delegate)

    def set_game_state(self, game_state):
        """ゲーム状態のセット"""
        self.game_state = game_state
        if not game_state or not game_state.player_team:
            return

        self.current_team = game_state.player_team
        self.team_label.setText(self.current_team.name)

        # リストが空の場合、自動分配を行う (1軍含む)
        if not self.current_team.farm_roster and not self.current_team.third_roster:
            self.current_team.auto_assign_rosters()

        self._refresh_tables()

    def _set_filter(self, mode):
        """投手・野手フィルタの切り替え"""
        if self.current_filter_mode == mode:
            return
            
        self.current_filter_mode = mode
        
        # ボタン状態更新
        self.filter_pitcher_btn.setChecked(mode == "pitcher")
        self.filter_fielder_btn.setChecked(mode == "fielder")
        
        self._refresh_tables()

    def _refresh_tables(self):
        """テーブルの内容を更新（一軍との同期を含む）"""
        if not self.current_team:
            return

        t = self.current_team
        
        # --- 同期処理: 一軍（アクティブ）リストを収集 ---
        active_ids = set()
        def add_ids(lst):
            if lst: active_ids.update([x for x in lst if x >= 0])
            
        add_ids(t.current_lineup)
        add_ids(t.bench_batters)
        add_ids(t.rotation)
        add_ids(t.setup_pitchers)
        add_ids(t.closers)
        
        third_ids = set(t.third_roster)

        # ★修正: 既存のfarm_rosterの順序を維持しつつ同期する
        # 1. 現在farm_rosterにいるが、activeやthirdに移動した選手を除去
        current_farm_cleaned = [pid for pid in t.farm_roster if pid not in active_ids and pid not in third_ids]

        # 2. どこにも所属していない選手（一軍落ちなど）を検出し、リスト末尾に追加
        #    (players配列順に追加することで、ある程度の一貫性は保つ)
        existing_farm_set = set(current_farm_cleaned)
        new_farm_candidates = []
        for i, p in enumerate(t.players):
            if i in active_ids: continue
            if i in third_ids: continue
            # if p.is_developmental: continue  <-- 修正: 育成選手も所属なしならFarmリストに入れる
            if i in existing_farm_set: continue
            new_farm_candidates.append(i)
        
        # 結合して更新
        t.farm_roster = current_farm_cleaned + new_farm_candidates
        # -------------------------------------------------------------

        is_pitcher = (self.current_filter_mode == "pitcher")
        
        # 列定義の更新
        self._setup_table_columns(self.farm_table, is_pitcher)
        self._setup_table_columns(self.third_table, is_pitcher)

        # ファーム・三軍ロスターから直接選手を取得し、フィルタ条件に合う場合のみ表示
        farm_players = []
        third_players = []

        for i in self.current_team.farm_roster:
            p = self.current_team.players[i]
            try:
                pos_val = p.position.value if hasattr(p.position, 'value') else str(p.position)
            except:
                pos_val = ""
            p_is_pitcher = (pos_val == "投手")
            if p_is_pitcher == is_pitcher:
                farm_players.append((i, p))

        for i in self.current_team.third_roster:
            p = self.current_team.players[i]
            try:
                pos_val = p.position.value if hasattr(p.position, 'value') else str(p.position)
            except:
                pos_val = ""
            p_is_pitcher = (pos_val == "投手")
            if p_is_pitcher == is_pitcher:
                third_players.append((i, p))

        # テーブルへの入力 (ソートはヘッダーに任せるが、初期ソートとして総合値で行う)
        self._fill_table(self.farm_table, farm_players, is_pitcher)
        self._fill_table(self.third_table, third_players, is_pitcher)

        # デフォルトソート: 総合(最後の列)の降順
        # ユーザーがソート済みの場合は維持したいが、ここではリセットされる挙動になるため、
        # 必要であればソート状態を保存するロジックが必要だが、まずはデフォルト動作とする
        last_col = self.farm_table.columnCount() - 1
        self.farm_table.sortItems(last_col, Qt.DescendingOrder)
        self.third_table.sortItems(last_col, Qt.DescendingOrder)

        # 人数表示更新
        farm_total = len(farm_players)
        third_total = len(third_players)
        self.farm_count_lbl.setText(f"{farm_total}人")
        self.third_count_lbl.setText(f"{third_total}人")
        self.farm_count_lbl.setStyleSheet(f"color: {self.theme.text_secondary};")

    def _fill_table(self, table, players_data, is_pitcher):
        """テーブルに行データを追加"""
        table.setRowCount(len(players_data))
        
        for row, (p_idx, p) in enumerate(players_data):
            try:
                # 怪我状態などによる文字色
                text_color = None
                if hasattr(p, 'is_injured') and p.is_injured:
                    text_color = QColor("#95a5a6")
                
                if is_pitcher:
                    # ["タイプ", "調", "選手名", "年齢", "球速", "コ", "ス", "変", "先", "中", "抑", "総合"]
                    role_str = p.pitch_type.value[:2] if hasattr(p.pitch_type, 'value') else "先発"
                    table.setItem(row, 0, self._create_item(role_str, text_color=text_color))
                    table.setItem(row, 1, self._create_condition_item(p))
                    table.setItem(row, 2, self._create_item(p.name, align=Qt.AlignLeft, text_color=text_color))
                    table.setItem(row, 3, self._create_item(p.age, text_color=text_color))
                    
                    kmh = p.stats.speed_to_kmh()
                    table.setItem(row, 4, self._create_item(f"{kmh}km", sort_val=kmh, text_color=text_color))
                    
                    table.setItem(row, 5, self._create_item(p.stats.control, rank_color=True))
                    table.setItem(row, 6, self._create_item(p.stats.stamina, rank_color=True))
                    table.setItem(row, 7, self._create_item(p.stats.stuff, rank_color=True))
                    
                    # 適正
                    st = p.get_aptitude_symbol(p.starter_aptitude)
                    rl = p.get_aptitude_symbol(p.middle_aptitude)
                    cl = p.get_aptitude_symbol(p.closer_aptitude)
                    
                    table.setItem(row, 8, self._create_item(st, sort_val=p.starter_aptitude, text_color=text_color))
                    table.setItem(row, 9, self._create_item(rl, sort_val=p.middle_aptitude, text_color=text_color))
                    table.setItem(row, 10, self._create_item(cl, sort_val=p.closer_aptitude, text_color=text_color))
                    
                    table.setItem(row, 11, self._create_item(f"★{p.overall_rating}", is_star=True))

                else:
                    # ["調", "選手名", "年齢", "ミ", "パ", "走", "肩", "守", "守備適正", "総合"]
                    table.setItem(row, 0, self._create_condition_item(p))
                    table.setItem(row, 1, self._create_item(p.name, align=Qt.AlignLeft, text_color=text_color))
                    table.setItem(row, 2, self._create_item(p.age, text_color=text_color))
                    
                    table.setItem(row, 3, self._create_item(p.stats.contact, rank_color=True))
                    table.setItem(row, 4, self._create_item(p.stats.power, rank_color=True))
                    table.setItem(row, 5, self._create_item(p.stats.speed, rank_color=True))
                    table.setItem(row, 6, self._create_item(p.stats.arm, rank_color=True))
                    table.setItem(row, 7, self._create_item(p.stats.fielding, rank_color=True))
                    
                    # 守備適正 (DefenseDelegate用フォーマット: "Main|Sub Sub")
                    apt_data = self._format_aptitude_delegate(p)
                    # ソート用にメインポジションの数値化
                    pos_order = {"捕": 2, "一": 3, "二": 4, "三": 5, "遊": 6, "左": 7, "中": 8, "右": 9, "DH": 10}
                    main_pos_char = self._short_pos_name(p.position.value)
                    sort_val = pos_order.get(main_pos_char, 99)
                    
                    table.setItem(row, 8, self._create_item(apt_data, sort_val=sort_val, text_color=text_color))
                    table.setItem(row, 9, self._create_item(f"★{p.overall_rating}", is_star=True))

                # ユーザーデータとしてプレイヤーインデックスを保存
                for c in range(table.columnCount()):
                    item = table.item(row, c)
                    if item:
                        item.setData(ROLE_PLAYER_IDX, p_idx)
            except Exception as e:
                print(f"Error filling table row {row}: {e}")
                continue

    def _create_item(self, value, align=Qt.AlignCenter, rank_color=False, pos_badge=None, is_star=False, sort_val=None, text_color=None):
        """OrderPage準拠のアイテム作成ヘルパー"""
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
        """調子アイテム作成"""
        item = SortableTableWidgetItem()
        item.setTextAlignment(Qt.AlignCenter)
        
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

    def _format_aptitude_delegate(self, p):
        """守備適正の文字列生成 (Main|Sub Sub)"""
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

    def _on_dropped_to_farm(self, p_idx):
        """二軍テーブルにドロップされた時の処理"""
        if p_idx is None: return
        if p_idx in self.current_team.farm_roster:
            return
        if self.current_team.move_to_farm_roster(p_idx):
            self._refresh_tables()

    def _on_dropped_to_third(self, p_idx):
        """三軍テーブルにドロップされた時の処理"""
        if p_idx is None: return
        if p_idx in self.current_team.third_roster:
            return
        if self.current_team.move_to_third_roster(p_idx):
            self._refresh_tables()

    def _on_player_double_clicked(self, item):
        """プレイヤーダブルクリック時の詳細表示イベント"""
        p_idx = item.data(ROLE_PLAYER_IDX)
        if p_idx is not None and isinstance(p_idx, int) and p_idx >= 0:
            if p_idx < len(self.current_team.players):
                player = self.current_team.players[p_idx]
                self.player_detail_requested.emit(player)