# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Farm Swap Page
Manage roster moves between Farm (2nd Team) and Third Team (3rd Team)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTableWidget, QTableWidgetItem, 
    QHeaderView, QAbstractItemView, QFrame, QMessageBox, QSplitter
)
from PySide6.QtCore import Qt, Signal, QSize, QMimeData
from PySide6.QtGui import QColor, QFont, QIcon, QDrag

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
ROLE_ORIGINAL_LEVEL = Qt.UserRole + 2

class DraggableTableWidget(QTableWidget):
    """ドラッグ＆ドロップ対応のテーブルウィジェット"""
    
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
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.horizontalHeader().setStretchLastSection(True)
        self.setShowGrid(False)

    def startDrag(self, supportedActions):
        """ドラッグ開始時の処理"""
        item = self.item(self.currentRow(), 0)
        if not item:
            return
            
        # プレイヤーIDを取得
        p_idx = item.data(ROLE_PLAYER_IDX)
        if p_idx is None:
            return
        
        # MIMEデータにプレイヤーIDを格納
        mime = QMimeData()
        mime.setText(str(p_idx))
        
        drag = QDrag(self)
        drag.setMimeData(mime)
        
        # ドラッグ実行
        drag.exec(supportedActions, Qt.MoveAction)

    def dragEnterEvent(self, event):
        """ドラッグが入ってきたとき"""
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """ドラッグ中の移動"""
        if event.mimeData().hasText():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """ドロップされたとき"""
        if event.mimeData().hasText():
            try:
                p_idx = int(event.mimeData().text())
                self.itemDropped.emit(p_idx)
                event.accept()
            except ValueError:
                event.ignore()
        else:
            event.ignore()


class FarmSwapPage(QWidget):
    """二軍・三軍 入れ替え管理ページ"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.current_team = None
        
        # フィルタ状態 (0: 投手, 1: 野手)
        self.current_filter_mode = "pitcher" 
        
        self.rating_delegate = RatingDelegate(self)
        
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
        
        # スタイル適用
        table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {self.theme.bg_card};
                border: 1px solid {self.theme.border};
                gridline-color: {self.theme.border_muted};
                selection-background-color: {self.theme.primary}40;
                selection-color: {self.theme.text_primary};
                outline: none;
            }}
            QTableWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {self.theme.border_muted};
            }}
            QHeaderView::section {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_secondary};
                border: none;
                border-bottom: 1px solid {self.theme.border};
                padding: 4px;
                font-weight: bold;
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
        """テーブルの列定義を設定"""
        table.clear() 
        
        if is_pitcher:
            # 調子, 名前, 年齢, 球速, コン, スタ, 変化, 適正, 総合
            headers = ["調", "選手名", "年齢", "球速", "コ", "ス", "変", "適", "総合"]
            widths = [30, 140, 40, 50, 35, 35, 35, 45, 45]
            delegate_cols = [4, 5, 6] # コ, ス, 変
        else:
            # 調子, 名前, 年齢, ミート, パワー, 走力, 守力, 位置, 総合
            headers = ["調", "選手名", "年齢", "ミ", "パ", "走", "守", "位置", "総合"]
            widths = [30, 140, 40, 35, 35, 35, 35, 45, 45]
            delegate_cols = [3, 4, 5, 6] # ミ, パ, 走, 守

        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        
        for i, w in enumerate(widths):
            table.setColumnWidth(i, w)
            
        # レーティング表示用のデリゲート適用
        for col in delegate_cols:
            table.setItemDelegateForColumn(col, self.rating_delegate)

    def set_game_state(self, game_state):
        """ゲーム状態のセット"""
        self.game_state = game_state
        if not game_state or not game_state.player_team:
            return

        self.current_team = game_state.player_team
        self.team_label.setText(self.current_team.name)

        # ファーム・三軍ロスターが空なら自動分配
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
        """テーブルの内容を更新"""
        if not self.current_team:
            return

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

        # ソート（背番号順）
        farm_players.sort(key=lambda x: x[1].uniform_number)
        third_players.sort(key=lambda x: x[1].uniform_number)

        # テーブルへの入力
        self._fill_table(self.farm_table, farm_players, is_pitcher)
        self._fill_table(self.third_table, third_players, is_pitcher)

        # 人数表示更新 (人数制限の撤廃)
        # farm_limit = getattr(self.current_team, 'FARM_ROSTER_LIMIT', 40)
        
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
                if p.is_injured:
                    text_color = QColor("#95a5a6")
                
                # 0: 調子 (Cond)
                table.setItem(row, 0, self._create_condition_item(p))

                # 1: 名前 (Name)
                name_item = self._create_item(p.name, align=Qt.AlignLeft, text_color=text_color)
                if p.is_injured:
                    name_item.setToolTip(f"怪我: {p.injury_name} (残{p.injury_days}日)")
                table.setItem(row, 1, name_item)

                # 2: 年齢 (Age)
                table.setItem(row, 2, self._create_item(str(p.age), text_color=text_color))

                # Stats
                if is_pitcher:
                    # 3: Speed
                    kmh = p.stats.speed_to_kmh()
                    table.setItem(row, 3, self._create_item(f"{kmh}km", text_color=text_color))
                    # 4,5,6: Con, Stm, Stuff
                    table.setItem(row, 4, self._create_item(p.stats.control, is_rating=True))
                    table.setItem(row, 5, self._create_item(p.stats.stamina, is_rating=True))
                    table.setItem(row, 6, self._create_item(p.stats.stuff, is_rating=True))
                    
                    # 7: Aptitude/Role (適正)
                    role_str = "先"
                    apt_val = 50
                    
                    # 役割と適正値の取得
                    if hasattr(p, 'pitch_type') and p.pitch_type:
                        try:
                            full_role = p.pitch_type.value
                            role_str = full_role[:1] # "先", "中", "抑"
                            
                            if "先発" in full_role: apt_val = p.starter_aptitude
                            elif "中継" in full_role: apt_val = p.middle_aptitude
                            elif "抑" in full_role: apt_val = p.closer_aptitude
                        except:
                            pass
                    else:
                        apt_val = p.starter_aptitude

                    # ランク取得 (★ここを修正しました★)
                    # p.get_rank ではなく p.stats.get_rank を使用
                    rank = p.stats.get_rank(apt_val)
                    
                    apt_item = self._create_item(f"{role_str}{rank}")
                    # 色分け: 適正に応じて
                    bg_color = None
                    if role_str == "先": bg_color = "#e67e22"
                    elif role_str == "抑": bg_color = "#e74c3c"
                    else: bg_color = "#3498db"
                    
                    apt_item.setBackground(QColor(bg_color))
                    apt_item.setForeground(Qt.white)
                    apt_item.setFont(QFont("Yu Gothic UI", 9, QFont.Bold))
                    table.setItem(row, 7, apt_item)

                else:
                    # 3,4,5,6: Con, Pwr, Spd, Fld
                    table.setItem(row, 3, self._create_item(p.stats.contact, is_rating=True))
                    table.setItem(row, 4, self._create_item(p.stats.power, is_rating=True))
                    table.setItem(row, 5, self._create_item(p.stats.speed, is_rating=True))
                    table.setItem(row, 6, self._create_item(p.stats.fielding, is_rating=True))
                    
                    # 7: Position Name (位置)
                    try:
                        pos_str = p.position.value[0] if hasattr(p.position, 'value') else str(p.position)[0]
                    except:
                        pos_str = "-"
                        
                    pos_item = self._create_item(pos_str, text_color=text_color)
                    
                    from UI.pages.order_page import get_pos_color
                    color_code = get_pos_color(pos_str)
                    pos_item.setBackground(QColor(color_code))
                    pos_item.setForeground(Qt.white)
                    pos_item.setFont(QFont("Yu Gothic UI", 9, QFont.Bold))
                    
                    table.setItem(row, 7, pos_item)

                # 8: Overall
                star_item = self._create_item(f"★{p.overall_rating}")
                star_item.setForeground(QColor("#FFD700"))
                star_item.setFont(QFont("Yu Gothic UI", 9, QFont.Bold))
                table.setItem(row, 8, star_item)

                # ユーザーデータとしてプレイヤーインデックスを保存 (ドラッグ＆ドロップで使用)
                for c in range(table.columnCount()):
                    item = table.item(row, c)
                    if item:
                        item.setData(ROLE_PLAYER_IDX, p_idx)
            except Exception as e:
                # デバッグ用にエラーを出力（必要であればコンソールで確認）
                print(f"Error filling table row {row}: {e}")
                continue

    def _create_item(self, text, align=Qt.AlignCenter, is_rating=False, text_color=None):
        item = SortableTableWidgetItem(str(text))
        item.setTextAlignment(align)
        if text_color:
            item.setForeground(text_color)
        
        if is_rating:
            try:
                val = int(text)
                item.setData(Qt.UserRole, val) 
                item.setText(str(text)) 
            except:
                pass
        
        return item

    def _create_condition_item(self, player):
        item = SortableTableWidgetItem()
        item.setTextAlignment(Qt.AlignCenter)
        
        if hasattr(player, 'is_injured') and player.is_injured:
            item.setText("傷")
            item.setForeground(QColor("#95a5a6"))
            item.setToolTip(f"全治まであと{player.injury_days}日")
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

    def _on_dropped_to_farm(self, p_idx):
        """二軍テーブルにドロップされた時の処理"""
        if p_idx is None: return

        # 制限チェックを削除（無制限）
        # farm_limit = getattr(self.current_team, 'FARM_ROSTER_LIMIT', 40)
        
        # 既に二軍にいる場合は何もしない
        if p_idx in self.current_team.farm_roster:
            return

        # 人数チェックを削除
        # if len(self.current_team.farm_roster) >= farm_limit:
        #    QMessageBox.warning(self, "登録上限", f"二軍の登録枠({farm_limit}人)がいっぱいです。")
        #    return

        # 移動ロジック実行 (ActiveやThirdからFarmへ)
        if self.current_team.move_to_farm_roster(p_idx):
            self._refresh_tables()

    def _on_dropped_to_third(self, p_idx):
        """三軍テーブルにドロップされた時の処理"""
        if p_idx is None: return
        
        # 既に三軍にいる場合は何もしない
        if p_idx in self.current_team.third_roster:
            return

        # 移動ロジック実行 (ActiveやFarmからThirdへ)
        if self.current_team.move_to_third_roster(p_idx):
            self._refresh_tables()