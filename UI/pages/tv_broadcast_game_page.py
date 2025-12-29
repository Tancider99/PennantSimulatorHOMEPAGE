# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - TV Broadcast Game Page
Updated: Accurate Field Dimensions (Stadium PF), Fixed Trajectory Line
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, 
    QPushButton, QSizePolicy, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDialog, QAbstractItemView, QSlider, QGridLayout, QCheckBox, QProgressBar,
    QStyledItemDelegate, QStyle, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QTimer, QPointF, QRectF, QSize, QCoreApplication
from PySide6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QPainterPath, QPolygonF, QIcon, QPixmap
)

import sys
import os
import math
import traceback

# パス設定
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    from UI.theme import get_theme
    from UI.widgets.tables import RatingDelegate, apply_premium_table_style
    from live_game_engine import PitchData, BattedBallData, BattedBallType
    from UI.widgets.score_board import LineScoreTable
    from UI.widgets.substitution_table import SubstitutionPlayerTable
    from UI.pages.player_detail_page import PlayerDetailPage
except ImportError:
    pass

# ========================================
# デザイン定数
# ========================================
THEME = get_theme()

class VisualStyle:
    BG_MAIN = QColor(THEME.bg_darkest)
    BG_PANEL = QColor(THEME.bg_card)
    BG_FIELD = QColor("#16181C") 
    
    TEXT_MAIN = QColor(THEME.text_primary)
    TEXT_SUB = QColor(THEME.text_secondary)
    
    COLOR_STRIKE = QColor(THEME.accent_orange)
    COLOR_BALL = QColor(THEME.success)
    COLOR_OUT = QColor(THEME.accent_red)
    COLOR_HIT = QColor(THEME.accent_blue)
    COLOR_FOUL = QColor("#FFD700")
    COLOR_RUNNER = QColor(THEME.accent_orange)
    
    BORDER = QColor(THEME.border)
    FONT_NUM = "Consolas"

    @staticmethod
    def get_result_color(result: str):
        res = str(result)
        if "本塁打" in res: return QColor("#E040FB")
        if any(x in res for x in ["安打", "二塁打", "三塁打"]): return VisualStyle.COLOR_HIT
        if any(x in res for x in ["アウト", "フライ", "ゴロ", "ライナー", "併殺", "失策", "犠", "三振"]): return VisualStyle.COLOR_OUT
        if "ボール" in res or "四球" in res or "死球" in res: return VisualStyle.COLOR_BALL
        if "ファウル" in res: return VisualStyle.COLOR_FOUL
        return VisualStyle.COLOR_STRIKE

class LineupDialog(QDialog):
    """Lineup Dialog - Styled like Substitution Window with in-place player detail"""
    
    def __init__(self, home_team, away_team, parent=None):
        super().__init__(parent)
        self.setWindowTitle("STARTING LINEUPS")
        self.resize(900, 650)
        self.theme = get_theme()
        self.home_team = home_team
        self.away_team = away_team
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.theme.bg_dark};
                color: {self.theme.text_primary};
            }}
            QTableWidget {{
                background-color: {self.theme.bg_card};
                border: none;
                gridline-color: {self.theme.border_muted};
            }}
            QTableWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {self.theme.border_muted};
            }}
            QTableWidget::item:selected {{
                background-color: #ffffff;
                color: #111111;
            }}
            QHeaderView::section {{
                background-color: {self.theme.bg_card_elevated};
                color: {self.theme.text_secondary};
                font-weight: bold;
                padding: 6px;
                border: none;
            }}
            QPushButton {{
                background-color: {self.theme.bg_card_elevated};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme.bg_hover};
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # スタックウィジェット
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        
        # ページ0: ラインナップ一覧
        self.lineup_page = QWidget()
        lineup_layout = QHBoxLayout(self.lineup_page)
        lineup_layout.setSpacing(15)
        
        self.away_widget, self.away_table = self._create_table(away_team, "AWAY")
        lineup_layout.addWidget(self.away_widget)
        
        self.home_widget, self.home_table = self._create_table(home_team, "HOME")
        lineup_layout.addWidget(self.home_widget)
        
        self.stack.addWidget(self.lineup_page)
        
        # ページ1: 選手詳細
        self.detail_page = QWidget()
        detail_layout = QVBoxLayout(self.detail_page)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        
        # 詳細ページコンテナ
        self.detail_container = QVBoxLayout()
        detail_layout.addLayout(self.detail_container)
        
        self.stack.addWidget(self.detail_page)
        
    def _on_double_click(self, row, col):
        """ダブルクリックで選手詳細画面を開く"""
        table = self.sender()
        item = table.item(row, 0)
        if item:
            player = item.data(Qt.UserRole)
            if player:
                self._show_player_detail(player)
    
    def _show_player_detail(self, player):
        """選手詳細を同じダイアログ内に表示"""
        # 既存の詳細ページをクリア
        while self.detail_container.count():
            child = self.detail_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        try:
            detail_page = PlayerDetailPage()
            detail_page.set_player(player, None)
            
            # バックボタンでラインナップに戻る
            detail_page.back_requested.connect(lambda: self.stack.setCurrentIndex(0))
            
            # 詳細統計ボタン
            detail_page.detail_stats_requested.connect(self._show_full_stats)
            
            self.detail_container.addWidget(detail_page)
            self.stack.setCurrentIndex(1)
        except Exception:
            pass
    
    def _show_full_stats(self, player):
        """詳細統計をポップアップで表示"""
        try:
            from UI.widgets.dialogs import PlayerStatsDialog
            dialog = PlayerStatsDialog(player, self)
            dialog.exec()
        except Exception:
            pass
        
    def _create_table(self, team, title):
        container = QWidget()
        l = QVBoxLayout(container)
        l.setContentsMargins(5, 5, 5, 5)
        
        # Title
        lbl = QLabel(f"{title}: {team.name}")
        lbl.setStyleSheet(f"font-weight: bold; font-size: 16px; color: {self.theme.text_highlight}; margin-bottom: 8px;")
        l.addWidget(lbl)
        
        # Table
        table = QTableWidget()
        table.setColumnCount(7)
        table.setHorizontalHeaderLabels(["#", "調", "名前", "Pos", "打率", "HR", "打点"])
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # スクロールバー非表示
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # ダブルクリックで選手詳細
        table.cellDoubleClicked.connect(self._on_double_click)
        
        lineup = team.current_lineup
        pos = team.lineup_positions if hasattr(team, 'lineup_positions') and team.lineup_positions else [""] * 9
        
        table.setRowCount(len(lineup))
        for i, pid in enumerate(lineup):
            if pid == -1: continue
            if pid >= len(team.players): continue
            p = team.players[pid]
            record = p.record
            
            # Condition
            cond = getattr(p, 'condition', 5)
            cond_map = {1: "絶不調", 2: "不調", 3: "不調", 4: "普通", 5: "普通", 6: "好調", 7: "好調", 8: "絶好調", 9: "絶好調"}
            cond_text = cond_map.get(cond, "-")
            
            # Data
            avg = record.batting_average if record.at_bats > 0 else 0
            avg_str = f".{int(avg*1000):03d}" if record.at_bats > 0 else "---"
            
            row_data = [
                str(i+1),
                cond_text,
                p.name,
                pos[i] if i < len(pos) else p.position.value[:2],
                avg_str,
                str(record.home_runs),
                str(record.rbis)
            ]
            
            for col, val in enumerate(row_data):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter if col != 2 else Qt.AlignLeft | Qt.AlignVCenter)
                
                # 最初のカラムに選手オブジェクトを保存
                if col == 0:
                    item.setData(Qt.UserRole, p)
                
                # Condition color
                if col == 1:
                    if cond >= 8:
                        item.setForeground(QColor("#ff6b6b"))
                    elif cond >= 6:
                        item.setForeground(QColor("#ff9800"))
                    elif cond <= 2:
                        item.setForeground(QColor("#5fbcd3"))
                    else:
                        item.setForeground(QColor("#f0f0f0"))
                
                table.setItem(i, col, item)
        
        # Column widths
        header = table.horizontalHeader()
        header.resizeSection(0, 35)  # #
        header.resizeSection(1, 50)  # 調
        header.resizeSection(2, 130) # 名前
        header.resizeSection(3, 50)  # Pos
        header.resizeSection(4, 55)  # 打率
        header.resizeSection(5, 45)  # HR
        header.setStretchLastSection(True)  # 打点
        
        l.addWidget(table)
        return container, table

# ========================================
# カスタムウィジェット
# ========================================

class TacticalField(QWidget):
    """中央フィールド"""
    animation_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(400, 400)
        self.runners = [False, False, False]
        self.batted_ball = None
        self.result_str = ""
        self.stadium = None # スタジアム情報を保持
        
        self.anim_timer = QTimer(self)
        self.anim_timer.interval = 16 
        self.anim_timer.timeout.connect(self._update_anim)
        self.anim_progress = 0.0
        self.is_animating = False
        
        # 盗塁アニメーション用
        self.steal_info = None
        self.steal_animating = False
        self.steal_progress = 0.0
        self.steal_runners_before = [False, False, False]

    def set_stadium(self, stadium):
        """スタジアム情報をセット（パークファクター反映用）"""
        self.stadium = stadium
        self.update()

    def animate_ball(self, ball: BattedBallData, runners, result_str: str):
        self.batted_ball = ball
        self.runners = runners
        self.result_str = result_str
        self.anim_progress = 0.0
        self.is_animating = True
        self.anim_timer.start()

    def animate_steal(self, steal_info: dict, runners_before: list):
        """盗塁アニメーションを開始"""
        self.steal_info = steal_info
        self.steal_runners_before = runners_before.copy()
        self.steal_progress = 0.0
        self.steal_animating = True
        if not self.anim_timer.isActive():
            self.anim_timer.start()

    def set_runners_only(self, runners):
        self.runners = runners
        self.update()

    def clear(self):
        self.batted_ball = None
        self.result_str = ""
        self.is_animating = False
        self.steal_info = None
        self.steal_animating = False
        self.anim_timer.stop()
        self.update()

    def _update_anim(self):
        any_animating = False
        
        if self.is_animating:
            self.anim_progress += 0.008
            if self.anim_progress >= 1.0:
                self.anim_progress = 1.0
                self.is_animating = False
            else:
                any_animating = True
        
        if self.steal_animating:
            self.steal_progress += 0.01  # 更に遅く（修正）
            if self.steal_progress >= 1.0:
                self.steal_progress = 1.0
                self.steal_animating = False
            else:
                any_animating = True
        
        if not any_animating:
            self.anim_timer.stop()
            self.animation_finished.emit()
        
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        
        painter.fillRect(self.rect(), VisualStyle.BG_FIELD)
        self._draw_grid(painter, w, h)

        cx = w / 2
        cy = h * 0.92
        # スケール調整: 広い球場でも入るように少し余裕を持たせる
        scale = min(w, h) / 165.0

        painter.save()
        painter.translate(cx, cy)
        
        # ★修正: スタジアムのPFを反映したフィールド形状を描画
        pf_hr = self.stadium.pf_hr if self.stadium else 1.0
        
        field_poly_points = [QPointF(0, 0)]
        # 左翼線(-45度)から右翼線(+45度)まで
        for angle in range(-45, 46):
            abs_a = abs(angle)
            # エンジン(AdvancedDefenseEngine)と同じ計算式で距離を算出
            # 基準: センター122m, 両翼100m
            base_dist = 122.0 - (abs_a / 45.0) * (122.0 - 100.0)
            
            # パークファクター補正: PF>1.0なら狭く(距離が短く), PF<1.0なら広く
            dist_m = base_dist / math.sqrt(pf_hr)
            
            # 座標変換
            rad = math.radians(angle)
            px = dist_m * scale * math.sin(rad)
            py = -dist_m * scale * math.cos(rad)
            field_poly_points.append(QPointF(px, py))
            
        field_poly_points.append(QPointF(0, 0))
        field_path = QPainterPath()
        field_path.addPolygon(QPolygonF(field_poly_points))
        
        # フェアゾーン描画
        painter.setPen(QPen(QColor(255, 255, 255, 10), 1))
        painter.setBrush(QColor(255, 255, 255, 5))
        painter.drawPath(field_path)
        
        # ファウルライン
        line_pen = QPen(VisualStyle.BORDER, 2)
        painter.setPen(line_pen)
        # ポリゴンの頂点を使ってラインを引く
        p_left = field_poly_points[1] # -45度
        p_right = field_poly_points[-2] # +45度
        painter.drawLine(0, 0, p_left.x(), p_left.y())
        painter.drawLine(0, 0, p_right.x(), p_right.y())
        
        # ダイヤモンド
        base_dist = 27.43 * scale
        diamond_pts = [QPointF(0,0), QPointF(base_dist, -base_dist), QPointF(0, -base_dist*2), QPointF(-base_dist, -base_dist)]
        painter.setPen(QPen(QColor(THEME.primary), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawPolygon(QPolygonF(diamond_pts))
        
        painter.restore()
        
        # ベース & ランナー
        base_coords = [
            (cx + base_dist, cy - base_dist),
            (cx, cy - base_dist*2),
            (cx - base_dist, cy - base_dist)
        ]
        
        painter.setBrush(Qt.white); painter.setPen(Qt.NoPen)
        painter.drawPolygon(QPolygonF([QPointF(cx, cy), QPointF(cx+6, cy-6), QPointF(cx+6, cy-12), QPointF(cx-6, cy-12), QPointF(cx-6, cy-6)]))

        for i, (bx, by) in enumerate(base_coords):
            is_occ = self.runners[i]
            painter.setPen(Qt.NoPen); painter.setBrush(QColor(255,255,255, 80))
            painter.drawPolygon(QPolygonF([QPointF(bx, by+6), QPointF(bx+6, by), QPointF(bx, by-6), QPointF(bx-6, by)]))
            if is_occ:
                painter.setBrush(VisualStyle.COLOR_RUNNER)
                painter.setPen(QPen(Qt.white, 2))
                painter.drawEllipse(QPointF(bx, by), 10, 10)

        if self.batted_ball:
            self._draw_batted_ball(painter, cx, cy, scale)
        
        # 盗塁アニメーション
        if self.steal_info and self.steal_animating:
            self._draw_steal_animation(painter, cx, cy, base_dist)
    
    def _draw_steal_animation(self, painter, cx, cy, base_dist):
        """盗塁アニメーションを描画"""
        steal_type = self.steal_info.get('steal_type', '2B')
        success = self.steal_info.get('success', True)
        t = self.steal_progress
        
        # 開始位置と終了位置を決定
        if steal_type == '3B':  # 三盗（2塁→3塁）
            start_x, start_y = cx, cy - base_dist * 2
            end_x, end_y = cx - base_dist, cy - base_dist
        else:  # 二盗（1塁→2塁）
            start_x, start_y = cx + base_dist, cy - base_dist
            end_x, end_y = cx, cy - base_dist * 2
        
        # ランナーの現在位置
        if success:
            runner_x = start_x + (end_x - start_x) * t
            runner_y = start_y + (end_y - start_y) * t
        else:
            # 失敗時はアウトになる位置で止まる
            runner_x = start_x + (end_x - start_x) * min(t, 0.85)
            runner_y = start_y + (end_y - start_y) * min(t, 0.85)
        
        # ランナー描画
        painter.setBrush(VisualStyle.COLOR_RUNNER)
        painter.setPen(QPen(Qt.white, 2))
        painter.drawEllipse(QPointF(runner_x, runner_y), 12, 12)
        
        # 成功/失敗テキスト
        if t >= 0.9:
            painter.setFont(QFont("Arial", 14, QFont.Bold))
            if success:
                painter.setPen(QColor(100, 255, 100))
                painter.drawText(int(end_x - 25), int(end_y - 25), "SAFE!")
            else:
                painter.setPen(QColor(255, 100, 100))
                painter.drawText(int(end_x - 20), int(end_y - 25), "OUT!")


    def _draw_grid(self, painter, w, h):
        painter.setPen(QPen(QColor(255, 255, 255, 10), 1, Qt.DotLine))
        for x in range(0, w, 50): painter.drawLine(x, 0, x, h)
        for y in range(0, h, 50): 
            if y < h: painter.drawLine(0, y, w, y)

    def _draw_batted_ball(self, painter, cx, cy, scale):
        ball = self.batted_ball
        t = self.anim_progress
        
        tx = ball.landing_x * scale
        ty = -ball.landing_y * scale
        
        # ゴロの場合は野手位置まで地面を転がる軌跡を表示
        is_groundball = ball.hit_type == BattedBallType.GROUNDBALL
        
        if is_groundball:
            # ゴロ: 直線的に野手位置まで転がる
            curr_x = cx + tx * t
            curr_y = cy + ty * t
            
            path = QPainterPath()
            path.moveTo(cx, cy)
            
            total_segments = 50
            current_segments = int(total_segments * t)
            
            for i in range(1, current_segments + 1):
                st = i / total_segments
                sx = cx + tx * st
                sy = cy + ty * st
                path.lineTo(sx, sy)
            
            path.lineTo(curr_x, curr_y)
        else:
            # フライ/ライナー/ポップフライ: 山なりの軌跡
            ctrl_x = tx / 2
            h_factor = ball.hang_time * 40 * scale
            ctrl_y = (ty / 2) - h_factor
            
            curr_x = cx + (2 * (1-t) * t * ctrl_x + t*t * tx)
            curr_y = cy + (2 * (1-t) * t * ctrl_y + t*t * ty)
            
            path = QPainterPath()
            path.moveTo(cx, cy)
            
            total_segments = 50
            current_segments = int(total_segments * t)
            
            for i in range(1, current_segments + 1):
                st = i / total_segments
                sx = cx + (2 * (1-st) * st * ctrl_x + st*st * tx)
                sy = cy + (2 * (1-st) * st * ctrl_y + st*st * ty)
                path.lineTo(sx, sy)
            
            path.lineTo(curr_x, curr_y)
            
        col = VisualStyle.get_result_color(self.result_str)
        painter.setPen(QPen(col, 2)); painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        painter.setBrush(col); painter.setPen(Qt.white)
        painter.drawEllipse(QPointF(curr_x, curr_y), 5, 5)
        
        if t >= 1.0:
            painter.setPen(Qt.white)
            painter.setFont(QFont(VisualStyle.FONT_NUM, 10, QFont.Bold))
            painter.drawText(int(curr_x) + 10, int(curr_y), f"{self.result_str} ({int(ball.distance)}m)")


class StrikeZoneWidget(QWidget):
    """ストライクゾーン"""
    animation_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(220, 260)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.pitches = [] 
        self.last_pitch = None
        self.last_result = ""
        self.pitcher_hand = "右"
        
        self.anim_timer = QTimer(self)
        self.anim_timer.interval = 16
        self.anim_timer.timeout.connect(self.update_anim)
        self.anim_step = 0
        self.is_animating = False

    def set_pitcher_hand(self, hand):
        self.pitcher_hand = hand

    def animate_pitch(self, pitch: PitchData, result: str):
        self.last_pitch = pitch
        self.last_result = result
        self.anim_step = 0
        self.is_animating = True
        self.anim_timer.start()

    def clear(self):
        self.pitches = []
        self.last_pitch = None
        self.is_animating = False
        self.anim_timer.stop()
        self.update()

    def update_anim(self):
        self.anim_step += 1
        if self.anim_step > 100: 
            self.is_animating = False
            self.anim_timer.stop()
            self.pitches.append((self.last_pitch, self.last_result))
            if len(self.pitches) > 10: self.pitches.pop(0)
            self.animation_finished.emit()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        
        painter.fillRect(self.rect(), VisualStyle.BG_PANEL)
        
        margin_x = w * 0.30
        zone_w = w - 2 * margin_x
        zone_h = zone_w * (0.56 / 0.432)
        zone_x = (w - zone_w) / 2
        zone_y = (h - zone_h) / 2
        
        painter.setPen(QPen(QColor(255,255,255,30), 2))
        box_bottom = min(h - 10, zone_y + zone_h + 80)
        painter.drawLine(int(zone_x - 20), int(zone_y + zone_h), int(zone_x - 20), int(box_bottom))
        painter.drawLine(int(zone_x + zone_w + 20), int(zone_y + zone_h), int(zone_x + zone_w + 20), int(box_bottom))

        painter.setPen(QPen(QColor(255,255,255,100), 2))
        painter.setBrush(QColor(255,255,255,5))
        painter.drawRect(QRectF(zone_x, zone_y, zone_w, zone_h))
        
        painter.setPen(QPen(QColor(255,255,255,40), 1, Qt.DotLine))
        painter.drawLine(QPointF(zone_x + zone_w/3, zone_y), QPointF(zone_x + zone_w/3, zone_y + zone_h))
        painter.drawLine(QPointF(zone_x + zone_w*2/3, zone_y), QPointF(zone_x + zone_w*2/3, zone_y + zone_h))
        painter.drawLine(QPointF(zone_x, zone_y + zone_h/3), QPointF(zone_x + zone_w, zone_y + zone_h/3))
        painter.drawLine(QPointF(zone_x, zone_y + zone_h*2/3), QPointF(zone_x + zone_w, zone_y + zone_h*2/3))
        
        hp_y = zone_y + zone_h + 15
        hp_pts = [QPointF(zone_x, hp_y), QPointF(zone_x+zone_w, hp_y), QPointF(zone_x+zone_w/2, hp_y+15), QPointF(zone_x, hp_y)]
        painter.setBrush(QColor(220,220,220)); painter.setPen(Qt.NoPen)
        painter.drawPolygon(QPolygonF(hp_pts))

        for idx, (pitch, result) in enumerate(self.pitches):
            alpha = 120 if idx < len(self.pitches)-1 else 255
            self._draw_pitch(painter, pitch, result, zone_x, zone_y, zone_w, zone_h, idx+1, alpha)

        if self.is_animating and self.last_pitch:
            progress = self.anim_step / 100.0
            self._draw_animated_pitch(painter, self.last_pitch, self.last_result, zone_x, zone_y, zone_w, zone_h, progress)

    def _loc_to_screen(self, lx, lz, zx, zy, zw, zh):
        sx = zx + (zw / 2) + (lx / 0.432) * zw
        sz = zy + (zh / 2) - ((lz - 0.75) / 0.56) * zh
        return sx, sz

    def _draw_pitch(self, painter, pitch, result, zx, zy, zw, zh, num, alpha=255):
        sx, sy = self._loc_to_screen(pitch.location.x, pitch.location.z, zx, zy, zw, zh)
        color = VisualStyle.get_result_color(result)
        color.setAlpha(alpha)
        self._draw_symbol(painter, sx, sy, pitch.pitch_type, color, str(num))

    def _draw_animated_pitch(self, painter, pitch, result, zx, zy, zw, zh, progress):
        ex, ey = self._loc_to_screen(pitch.location.x, pitch.location.z, zx, zy, zw, zh)
        offset_x = -50 if self.pitcher_hand == "左" else 50
        start_x = (zx + zw/2) + offset_x
        start_y = -80
        
        ctrl_x = (start_x + ex) / 2
        hb = pitch.horizontal_break
        ctrl_x += (hb * 2.0) 
        
        curr_x = (1-progress)**2 * start_x + 2*(1-progress)*progress * ctrl_x + progress**2 * ex
        curr_y = (1-progress)**2 * start_y + 2*(1-progress)*progress * ((start_y+ey)/2) + progress**2 * ey
        
        path = QPainterPath(); path.moveTo(start_x, start_y)
        steps = int(20 * progress) + 1
        for i in range(1, steps+1):
            t = i / 20.0 * progress if progress > 0 else 0
            if progress == 1.0: t = i/20.0
            px = (1-t)**2 * start_x + 2*(1-t)*t * ctrl_x + t**2 * ex
            py = (1-t)**2 * start_y + 2*(1-t)*t * ((start_y+ey)/2) + t**2 * ey
            path.lineTo(px, py)
            
        painter.setPen(QPen(VisualStyle.get_result_color(result), 3, Qt.SolidLine, Qt.RoundCap))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
        
        if progress < 1.0:
            size = 4 + 10 * progress
            painter.setBrush(Qt.white); painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(curr_x, curr_y), size/2, size/2)
        else:
            self._draw_pitch(painter, pitch, result, zx, zy, zw, zh, len(self.pitches)+1)

    def _draw_symbol(self, painter, x, y, p_type, color, text):
        painter.setBrush(color); painter.setPen(QPen(Qt.white, 1))
        size = 10
        
        if p_type in ["ストレート", "ツーシーム"]:
            painter.drawEllipse(QPointF(x, y), size, size)
        elif p_type in ["フォーク", "SFF", "チェンジアップ", "ナックル", "スプリット"]:
            poly = QPolygonF([QPointF(x-size, y-size), QPointF(x+size, y-size), QPointF(x, y+size)])
            painter.drawPolygon(poly)
        else:
            is_pointing_left = True 
            sliders = ["スライダー", "カーブ", "カットボール"]
            shoots = ["シュート", "シンカー"]
            
            if self.pitcher_hand == "右":
                if p_type in sliders: is_pointing_left = False 
                elif p_type in shoots: is_pointing_left = True 
            else: 
                if p_type in sliders: is_pointing_left = True 
                elif p_type in shoots: is_pointing_left = False
            
            if is_pointing_left:
                poly = QPolygonF([QPointF(x+size*0.8, y-size), QPointF(x+size*0.8, y+size), QPointF(x-size*0.8, y)])
            else:
                poly = QPolygonF([QPointF(x-size*0.8, y-size), QPointF(x-size*0.8, y+size), QPointF(x+size*0.8, y)])
            painter.drawPolygon(poly)
            
        painter.setPen(Qt.black)
        painter.setFont(QFont(VisualStyle.FONT_NUM, 8, QFont.Bold))
        painter.drawText(QRectF(x-size, y-size, size*2, size*2), Qt.AlignCenter, text)





class ScoreBoardWidget(QFrame):
    """スコアボードコンテナ"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(110)
        self.setStyleSheet(f"background-color: {THEME.bg_card_elevated}; border: none; border-radius: 4px;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.setSpacing(20)
        
        self.info_box = self._create_info_box()
        layout.addWidget(self.info_box)
        
        self.line_score = LineScoreTable(self)
        layout.addWidget(self.line_score, stretch=1)  # 横幅いっぱいに広げる

    def _create_info_box(self):
        w = QWidget()
        w.setFixedWidth(120)
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0,5,0,5)
        
        self.lbl_inning = QLabel("1st TOP")
        self.lbl_inning.setAlignment(Qt.AlignCenter)
        self.lbl_inning.setStyleSheet(f"color: {THEME.primary}; font-size: 18px; font-weight: 900; font-family: 'Segoe UI Black';")
        vl.addWidget(self.lbl_inning)
        
        grid = QGridLayout()
        grid.setSpacing(2)
        self.dots_b = self._mk_dots(3, VisualStyle.COLOR_BALL)
        self.dots_s = self._mk_dots(2, VisualStyle.COLOR_STRIKE)
        self.dots_o = self._mk_dots(2, VisualStyle.COLOR_OUT)
        
        l_style = "font-weight:bold; font-size:12px;"
        grid.addWidget(QLabel("B", styleSheet=f"color:{VisualStyle.COLOR_BALL.name()};"+l_style), 0, 0)
        grid.addLayout(self.dots_b[0], 0, 1)
        grid.addWidget(QLabel("S", styleSheet=f"color:{VisualStyle.COLOR_STRIKE.name()};"+l_style), 1, 0)
        grid.addLayout(self.dots_s[0], 1, 1)
        grid.addWidget(QLabel("O", styleSheet=f"color:{VisualStyle.COLOR_OUT.name()};"+l_style), 2, 0)
        grid.addLayout(self.dots_o[0], 2, 1)
        
        vl.addLayout(grid)
        return w

    def _mk_dots(self, n, col):
        l = QHBoxLayout(); l.setSpacing(2)
        dots = []
        for _ in range(n):
            d = QLabel("●")
            d.setStyleSheet(f"color: {THEME.bg_card}; font-size: 10px;")
            l.addWidget(d); dots.append(d)
        l.addStretch()
        return l, dots

    def update_display(self, st, h_name, a_name, h_stats, a_stats):
        inn_str = f"{st.inning}{'表' if st.is_top else '裏'}"
        self.lbl_inning.setText(inn_str)
        
        for i, d in enumerate(self.dots_b[1]): d.setStyleSheet(f"color: {VisualStyle.COLOR_BALL.name() if st.balls > i else THEME.bg_card};")
        for i, d in enumerate(self.dots_s[1]): d.setStyleSheet(f"color: {VisualStyle.COLOR_STRIKE.name() if st.strikes > i else THEME.bg_card};")
        for i, d in enumerate(self.dots_o[1]): d.setStyleSheet(f"color: {VisualStyle.COLOR_OUT.name() if st.outs > i else THEME.bg_card};")
        
        self.line_score.update_names(h_name, a_name)
        
        # 変数定義
        a_runs = st.away_score
        h_runs = st.home_score
        a_hits = st.away_hits
        h_hits = st.home_hits
        a_err = st.away_errors
        h_err = st.home_errors
        
        # R, H, Eの更新 (stats辞書から値を取得)
        # カラム位置は末尾3つ
        col_count = self.line_score.columnCount()
        r_col, h_col, e_col = col_count-3, col_count-2, col_count-1
        
        items = [
            (0, r_col, str(a_runs)), (0, h_col, str(a_hits)), (0, e_col, str(a_err)),
            (1, r_col, str(h_runs)), (1, h_col, str(h_hits)), (1, e_col, str(h_err))
        ]
        for r, c, val in items:
            it = QTableWidgetItem(val)
            it.setTextAlignment(Qt.AlignCenter)
            self.line_score.setItem(r, c, it)


class TrackingDataPanel(QFrame):
    """詳細トラッキングデータ表示"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {THEME.bg_card}; border: none; border-radius: 4px;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        title = QLabel("TRACKING DATA")
        title.setStyleSheet(f"color: {THEME.text_secondary}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(title)
        
        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        layout.addLayout(self.grid)
        
        self.labels = {}
        self.items = [
            ("P_Speed", "球速"), ("P_Spin", "回転数"), 
            ("P_HBreak", "変化(H)"), ("P_VBreak", "変化(V)"),
            ("B_ExitV", "打球速度"), ("B_Angle", "角度"),
            ("B_Dist", "飛距離"), ("B_Hang", "滞空")
        ]
        
        for i, (key, label_text) in enumerate(self.items):
            row = i // 2
            col = (i % 2) * 2
            
            lbl_k = QLabel(label_text)
            lbl_k.setStyleSheet("color: #888; font-size: 9px;")
            lbl_v = QLabel("-")
            lbl_v.setStyleSheet(f"color: {THEME.text_primary}; font-size: 12px; font-weight: bold; font-family: 'Consolas';")
            lbl_v.setAlignment(Qt.AlignRight)
            
            self.grid.addWidget(lbl_k, row, col)
            self.grid.addWidget(lbl_v, row, col+1)
            self.labels[key] = lbl_v

    def update_pitch(self, p: PitchData):
        if not p:
            for k in ["P_Speed", "P_Spin", "P_HBreak", "P_VBreak"]: self.labels[k].setText("-")
            return
        self.labels["P_Speed"].setText(f"{int(p.velocity)} km")
        self.labels["P_Spin"].setText(f"{p.spin_rate} rpm")
        self.labels["P_HBreak"].setText(f"{p.horizontal_break:+.1f}")
        self.labels["P_VBreak"].setText(f"{p.vertical_break:+.1f}")

    def update_batted_ball(self, b: BattedBallData):
        if not b:
            for k in ["B_ExitV", "B_Angle", "B_Dist", "B_Hang"]: self.labels[k].setText("-")
            return
        self.labels["B_ExitV"].setText(f"{int(b.exit_velocity)} km")
        self.labels["B_Angle"].setText(f"{int(b.launch_angle)} deg")
        self.labels["B_Dist"].setText(f"{int(b.distance)} m")
        self.labels["B_Hang"].setText(f"{b.hang_time:.1f} s")


class PlayerInfoPanel(QFrame):
    clicked = Signal(object)
    def __init__(self, title, align_right=False, parent=None):
        super().__init__(parent)
        self.player = None
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"background: {THEME.bg_card}; border: none; border-radius: 4px;")
        
        l = QVBoxLayout(self)
        l.setContentsMargins(15,10,15,10); l.setSpacing(2)
        
        h = QLabel(title)
        h.setStyleSheet(f"color:{THEME.text_secondary}; font-size:10px; font-weight:bold; letter-spacing:1px;")
        h.setAlignment(Qt.AlignRight if align_right else Qt.AlignLeft)
        h.setAttribute(Qt.WA_TransparentForMouseEvents) # マウスイベント透過
        l.addWidget(h)
        
        self.lbl_name = QLabel("---")
        self.lbl_name.setStyleSheet(f"color:{THEME.text_primary}; font-size:18px; font-weight:900;")
        self.lbl_name.setAlignment(Qt.AlignRight if align_right else Qt.AlignLeft)
        self.lbl_name.setAttribute(Qt.WA_TransparentForMouseEvents)
        l.addWidget(self.lbl_name)
        
        self.lbl_sub = QLabel("---")
        self.lbl_sub.setStyleSheet(f"color:{THEME.text_secondary}; font-size:11px;")
        self.lbl_sub.setAlignment(Qt.AlignRight if align_right else Qt.AlignLeft)
        self.lbl_sub.setAttribute(Qt.WA_TransparentForMouseEvents)
        l.addWidget(self.lbl_sub)
        
        self.stats_box = QHBoxLayout()
        l.addLayout(self.stats_box)

    def mousePressEvent(self, e):
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e):
        if self.player: self.clicked.emit(self.player)
        super().mouseDoubleClickEvent(e)

    def update_player(self, p, sub, stats):
        self.player = p
        self.lbl_name.setText(p.name)
        self.lbl_sub.setText(sub)
        
        # レイアウトクリア処理の改善
        while self.stats_box.count(): 
            item = self.stats_box.takeAt(0)
            if item.widget(): 
                item.widget().deleteLater()
            elif item.layout():
                # サブレイアウトの中身を削除
                l = item.layout()
                while l.count():
                    si = l.takeAt(0)
                    if si.widget(): si.widget().deleteLater()
                l.deleteLater()
            
            
        for k, v, c in stats:
            bx = QVBoxLayout(); bx.setSpacing(1)
            l = QLabel(k); l.setAlignment(Qt.AlignCenter)
            l.setStyleSheet("color:#888; font-size:9px;")
            
            # Rank Display Logic
            # Caller should pass value as "S", "A", ... for ranks or just raw string.
            # We colorize if it matches known ranks.
            
            display_text = str(v)
            text_color = c.name()
            font_size = "14px"
            
            if display_text in ["S", "A", "B", "C", "D", "E", "F", "G"]:
                # Use Theme colors for ranks
                # We need to map Letter back to color or just use passed color 'c' if caller set it right
                # Assuming caller sets 'c' correctly for the rank.
                pass
            
            if k == "STM":
                # スタミナバー表示
                val_bar = QProgressBar()
                val_bar.setRange(0, 100)
                try: val_int = int(v)
                except: val_int = 0
                val_bar.setValue(val_int)
                val_bar.setTextVisible(True)
                val_bar.setFormat(f"{val_int}")
                val_bar.setAlignment(Qt.AlignCenter)
                val_bar.setFixedHeight(14)
                
                # 色設定
                val_bar.setStyleSheet(f"""
                    QProgressBar {{
                        border: none;
                        background-color: #333;
                        border-radius: 2px;
                        color: white;
                        font-family: 'Consolas'; font-size: 10px; font-weight: bold;
                    }}
                    QProgressBar::chunk {{
                        background-color: {c.name()};
                        border-radius: 2px;
                    }}
                """)
                bx.addWidget(l)
                bx.addWidget(val_bar)
            else:
                val = QLabel(display_text); val.setAlignment(Qt.AlignCenter)
                val.setStyleSheet(f"color:{text_color}; font-size:{font_size}; font-weight:bold; font-family:'Consolas';")
                bx.addWidget(l); bx.addWidget(val)
                
            self.stats_box.addLayout(bx)


# ========================================
# メイン画面クラス
# ========================================

# ========================================
# 選手選択ダイアログ (OrderPage風リメイク)
# ========================================

class SubstitutionDefenseDelegate(QStyledItemDelegate):
    """メイン・サブポジション表示用デリゲート"""
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
        
        painter.restore()

class PlayerSelectionDialog(QDialog):
    def __init__(self, players, title="選手選択", parent=None, mode=None):
        super().__init__(parent)
        self.mode = mode
        self.setWindowTitle(title)
        self.resize(1000, 700) 
        self.theme = get_theme()
        self.setStyleSheet(f"background-color: {self.theme.bg_card}; color: {self.theme.text_primary};")
        self.selected_player = None
                
        # Main Layout is a Stack
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.stack = QStackedWidget()
        self.main_layout.addWidget(self.stack)
        
        # Page 0: Player List
        self.page_list = QWidget()
        self._setup_list_page(self.page_list, players)
        self.stack.addWidget(self.page_list)
        
        # Page 1: Player Detail
        self.page_detail = QWidget()
        self._setup_detail_page(self.page_detail)
        self.stack.addWidget(self.page_detail)
        
        self.stack.setCurrentIndex(0)
    
    def _setup_list_page(self, parent_widget, players):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # ヘッダー説明
        desc = QLabel("交代する選手を選択してください。ダブルクリックで詳細を表示します。")
        desc.setStyleSheet(f"color: {self.theme.text_secondary}; margin-bottom: 10px;")
        layout.addWidget(desc)

        # ★ カスタムテーブルを使用
        self.table = SubstitutionPlayerTable(self)
        # 接続
        self.table.player_double_clicked.connect(self._on_player_double_clicked)
        self.table.player_selected.connect(self._on_player_selected)
        
        layout.addWidget(self.table)
        
        # ボタン
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("キャンセル")
        btn_cancel.setFixedSize(120, 40)
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("決定")
        btn_ok.setFixedSize(120, 40)
        btn_ok.setStyleSheet(f"background-color: {self.theme.primary}; color: {self.theme.bg_dark}; font-weight: bold; border-radius: 4px;")
        btn_ok.clicked.connect(self._on_ok)
        
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_ok)
        layout.addLayout(btn_box)
        
        self._set_data(players)

    def _setup_detail_page(self, parent_widget):
        layout = QVBoxLayout(parent_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Detail Content (PlayerDetailPage has its own Toolbar with Back button)
        self.detail_view = PlayerDetailPage(parent_widget)
        # Connect built-in back signal
        self.detail_view.back_requested.connect(self._on_back_to_list)
        layout.addWidget(self.detail_view)

    def _set_data(self, players):
        if not players: return

        # 投手判定ロジック
        is_pitcher = False
        if self.mode == "pitcher":
            is_pitcher = True
        elif self.mode == "fielder" or self.mode == "batter":
            is_pitcher = False
        else:
            try:
                 for p in players:
                     if hasattr(p, 'position') and (str(p.position) == "Position.PITCHER" or "PITCHER" in str(p.position).upper() or getattr(p.position, 'name', '') == 'PITCHER'):
                         is_pitcher = True; break
            except: pass

        # テーブルにデータセット
        target_mode = "pitcher" if is_pitcher else "batter"
        
        # ★ Strict Mode 適用 (ボタンなどを非表示に)
        self.table.set_strict_mode(target_mode)
        self.table.set_players(players, mode=target_mode)

    def _on_player_selected(self, player):
        self.selected_player = player

    def _on_player_double_clicked(self, player):
        # ダブルクリックで埋め込み詳細表示
        self.detail_view.set_player(player, team_name="") # Team info if possible
        self.stack.setCurrentIndex(1)

    def _on_back_to_list(self):
        self.stack.setCurrentIndex(0)

    def _on_ok(self):
        if self.selected_player:
            self.accept()
        else:
            # 念のためテーブルから取得
            player = self.table.get_selected_player()
            if player:
                self.selected_player = player
                self.accept()





class TVBroadcastGamePage(QWidget):
    game_finished = Signal(object)
    go_to_player_detail = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.live_engine = None
        self.is_simulating = False
        self.is_animating = False 
        self.need_zone_reset = False 
        self.date_str = "2027-01-01"
        self.game_type = "normal"  # normal, ai_vs_ai
        
        # 采配関連
        self.is_fast_forwarding = False
        self.batting_strategy = "AUTO"
        
        self.score_history = {"top": [0]*10, "bot": [0]*10}
        self.prev_state_score = (0, 0)
        self.prev_state_inning = (1, True)
        
        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.scoreboard = ScoreBoardWidget(self)
        main_layout.addWidget(self.scoreboard)

        content = QWidget()
        content.setStyleSheet(f"background: {VisualStyle.BG_MAIN.name()};")
        cl = QHBoxLayout(content)
        cl.setContentsMargins(15, 15, 15, 15)
        cl.setSpacing(15)
        
        left = QVBoxLayout(); left.setSpacing(10)
        self.pitcher_card = PlayerInfoPanel("PITCHER")
        self.pitcher_card.clicked.connect(self._on_player_clicked)
        left.addWidget(self.pitcher_card)
        
        self.zone_widget = StrikeZoneWidget()
        self.zone_widget.animation_finished.connect(self._on_animation_step_finished)
        left.addWidget(self.zone_widget, stretch=1)
        
        self.track_panel = TrackingDataPanel()
        left.addWidget(self.track_panel)
        
        self.lbl_pitch_res = QLabel("---")
        self.lbl_pitch_res.setAlignment(Qt.AlignCenter)
        self.lbl_pitch_res.setStyleSheet(f"background:{THEME.bg_card}; color:{THEME.text_primary}; padding:10px; border-radius:4px; font-weight:bold; font-size:14px;")
        left.addWidget(self.lbl_pitch_res)
        
        cl.addLayout(left, stretch=2)
        
        # フィールドとシフト表示のコンテナ
        field_container = QVBoxLayout()
        field_container.setSpacing(4)
        
        # シフト表示ラベル（フィールド上部に配置）
        self.lbl_shift_indicator = QLabel("■ 内野: 通常 | 外野: 通常")
        self.lbl_shift_indicator.setStyleSheet(f"""
            background: rgba(0, 0, 0, 0.7);
            color: {THEME.primary};
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: bold;
        """)
        self.lbl_shift_indicator.setAlignment(Qt.AlignRight)
        field_container.addWidget(self.lbl_shift_indicator)
        
        self.field_widget = TacticalField()
        self.field_widget.animation_finished.connect(self._on_animation_step_finished)
        field_container.addWidget(self.field_widget, stretch=1)
        
        cl.addLayout(field_container, stretch=4)
        
        right = QVBoxLayout(); right.setSpacing(10)
        self.batter_card = PlayerInfoPanel("BATTER", True)
        self.batter_card.clicked.connect(self._on_player_clicked)
        right.addWidget(self.batter_card)
        
        # --- 采配パネル ---
        # --- 采配パネル (Expanded) ---
        # --- 采配パネル (Expanded) ---
        self.manager_frame = QFrame()
        self.manager_frame.setStyleSheet(f"background:{THEME.bg_card}; border-radius:4px;")
        mgr_layout = QVBoxLayout(self.manager_frame)
        mgr_layout.setContentsMargins(10, 8, 10, 8)
        mgr_layout.setSpacing(6)
        
        # タイトル
        self.mgr_title = QLabel("[采配] ホーム 攻撃中")
        self.mgr_title.setStyleSheet(f"color:{THEME.primary}; font-weight:bold; font-size:12px;")
        mgr_layout.addWidget(self.mgr_title)
        
        # --- 攻撃用パネル ---
        self.attack_panel = QWidget()
        atk_layout = QVBoxLayout(self.attack_panel)
        atk_layout.setContentsMargins(0, 0, 0, 0)
        atk_layout.setSpacing(4)
        
        bat_row = QHBoxLayout(); bat_row.setSpacing(3)
        self.bat_buttons = {}
        btn_style = f"QPushButton {{ background:{THEME.bg_card_elevated}; color:{THEME.text_primary}; border:1px solid {THEME.border}; border-radius:3px; padding:4px 6px; font-size:10px; }} QPushButton:checked {{ background:{THEME.primary}; color:black; }} QPushButton:disabled {{ background:{THEME.bg_card}; color:#666; }}"
        
        for strat in ["AUTO", "通常", "強振", "流し", "バント", "盗塁"]:
            btn = QPushButton(strat)
            btn.setCheckable(True)
            btn.setChecked(strat == "AUTO")
            btn.setStyleSheet(btn_style)
            btn.clicked.connect(lambda checked, s=strat: self._set_batting_strategy(s))
            bat_row.addWidget(btn)
            self.bat_buttons[strat] = btn
        atk_layout.addLayout(bat_row)
        
        # 攻撃オプション（代打・代走）
        atk_opt_row = QHBoxLayout(); atk_opt_row.setSpacing(4)
        btn_ph = QPushButton("代打")
        btn_ph.setStyleSheet(btn_style)
        btn_ph.clicked.connect(self._open_ph_dialog)
        atk_opt_row.addWidget(btn_ph)
        
        btn_pr = QPushButton("代走")
        btn_pr.setStyleSheet(btn_style)
        btn_pr.clicked.connect(self._open_pr_dialog)
        atk_opt_row.addWidget(btn_pr)
        atk_opt_row.addStretch()
        atk_layout.addLayout(atk_opt_row)
        
        mgr_layout.addWidget(self.attack_panel)
        
        # --- 守備用パネル ---
        self.defense_panel = QWidget()
        def_layout = QVBoxLayout(self.defense_panel)
        def_layout.setContentsMargins(0, 0, 0, 0)
        def_layout.setSpacing(4)
        
        def_row = QHBoxLayout(); def_row.setSpacing(4)
        
        self.btn_ibb = QPushButton("敬遠")
        self.btn_ibb.setStyleSheet(btn_style)
        self.btn_ibb.clicked.connect(lambda: self._execute_ibb())
        def_row.addWidget(self.btn_ibb)
        
        self.cmb_infield = QComboBox()
        self.cmb_infield.addItems(["内野通常", "前進守備", "ゲッツーシフト", "バントシフト"])
        self.cmb_infield.setStyleSheet(f"background:{THEME.bg_card_elevated}; color:{THEME.text_primary}; border:1px solid {THEME.border}; border-radius:3px; padding:2px; font-size:10px;")
        def_row.addWidget(self.cmb_infield)
        
        self.cmb_outfield = QComboBox()
        self.cmb_outfield.addItems(["外野通常", "外野深め", "外野浅め"])
        self.cmb_outfield.setStyleSheet(f"background:{THEME.bg_card_elevated}; color:{THEME.text_primary}; border:1px solid {THEME.border}; border-radius:3px; padding:2px; font-size:10px;")
        def_row.addWidget(self.cmb_outfield)
        def_row.addStretch()
        def_layout.addLayout(def_row)
        
        # 守備オプション（AUTO・継投・交代）
        def_opt_row = QHBoxLayout(); def_opt_row.setSpacing(4)
        
        self.btn_auto_def = QPushButton("守備AUTO")
        self.btn_auto_def.setCheckable(True)
        self.btn_auto_def.setStyleSheet(btn_style)
        self.btn_auto_def.clicked.connect(self._toggle_auto_defense)
        def_opt_row.addWidget(self.btn_auto_def)
        
        btn_pch = QPushButton("継投")
        btn_pch.setStyleSheet(btn_style)
        btn_pch.clicked.connect(self._open_pitcher_sub_dialog)
        def_opt_row.addWidget(btn_pch)
        
        btn_def = QPushButton("守備交代")
        btn_def.setStyleSheet(btn_style)
        btn_def.clicked.connect(self._open_def_sub_dialog)
        def_opt_row.addWidget(btn_def)
        
        def_opt_row.addStretch()
        def_layout.addLayout(def_opt_row)

        mgr_layout.addWidget(self.defense_panel)
        
        right.addWidget(self.manager_frame)
        
        # --- Log Area ---
        self.log_area = QScrollArea()
        self.log_area.setWidgetResizable(True)
        self.log_area.setStyleSheet(f"background:{THEME.bg_card}; border:none; border-radius:4px;")
        self.log_content = QWidget()
        self.log_layout = QVBoxLayout(self.log_content)
        self.log_layout.setAlignment(Qt.AlignTop)
        self.log_area.setWidget(self.log_content)
        right.addWidget(self.log_area, stretch=1)
        
        # --- Skip Control Panel (New) ---
        skip_frame = QFrame()
        skip_frame.setStyleSheet(f"background:{THEME.bg_card}; border-radius:4px;")
        skip_layout = QVBoxLayout(skip_frame)
        skip_layout.setContentsMargins(6, 6, 6, 6)
        skip_layout.setSpacing(4)
        
        # ★追加: ラインアップボタン
        self.btn_lineup = QPushButton("LINEUP")
        self.btn_lineup.setStyleSheet(f"background:{THEME.bg_card_elevated}; color:{THEME.text_secondary}; border:1px solid {THEME.border}; padding:4px; font-size:10px;")
        self.btn_lineup.clicked.connect(self._open_lineup_dialog)
        skip_layout.addWidget(self.btn_lineup)
        
        # Attack Skip
        askip_row = QHBoxLayout()
        askip_lbl = QLabel("攻:")
        askip_lbl.setStyleSheet(f"color:{THEME.text_secondary}; font-size:10px;")
        askip_row.addWidget(askip_lbl)
        
        self.cmb_ff_attack = QComboBox()
        self.cmb_ff_attack.addItems([
            "イニング終了", "得点圏", "チャンス", "満塁", "犠牲フライ圏",
            "3回まで", "5回まで", "7回まで", "9回まで", "試合終了"
        ])
        self.cmb_ff_attack.setStyleSheet(f"background:{THEME.bg_card_elevated}; color:{THEME.text_primary}; border:1px solid {THEME.border}; border-radius:3px; padding:2px; font-size:10px;")
        askip_row.addWidget(self.cmb_ff_attack, stretch=1)
        skip_layout.addLayout(askip_row)
        
        # Defense Skip
        dskip_row = QHBoxLayout()
        dskip_lbl = QLabel("守:")
        dskip_lbl.setStyleSheet(f"color:{THEME.text_secondary}; font-size:10px;")
        dskip_row.addWidget(dskip_lbl)
        
        self.cmb_ff_defense = QComboBox()
        self.cmb_ff_defense.addItems([
            "イニング終了", "得点圏", "ピンチ", "満塁", 
            "3回まで", "5回まで", "7回まで", "9回まで", "試合終了"
        ])
        self.cmb_ff_defense.setStyleSheet(f"background:{THEME.bg_card_elevated}; color:{THEME.text_primary}; border:1px solid {THEME.border}; border-radius:3px; padding:2px; font-size:10px;")
        dskip_row.addWidget(self.cmb_ff_defense, stretch=1)
        skip_layout.addLayout(dskip_row)
        
        # Speed & Execute
        ctrl_row = QHBoxLayout()
        sp_lbl = QLabel("速度:")
        sp_lbl.setStyleSheet(f"color:{THEME.text_secondary}; font-size:10px;")
        ctrl_row.addWidget(sp_lbl)
        
        self.sld_speed = QSlider(Qt.Horizontal)
        self.sld_speed.setRange(1, 10)
        self.sld_speed.setValue(9) # デフォルト速め
        self.sld_speed.setFixedWidth(120)
        self.sld_speed.valueChanged.connect(self._on_speed_change)
        ctrl_row.addWidget(self.sld_speed)
        
        self.btn_skip_start = QPushButton("早送り開始")
        self.btn_skip_start.setStyleSheet(btn_style) # 再利用
        self.btn_skip_start.clicked.connect(self._on_skip_click_unified)
        ctrl_row.addWidget(self.btn_skip_start)
        
        self.chk_auto_sub = QCheckBox("自動交代")
        self.chk_auto_sub.setStyleSheet(f"color:{THEME.text_primary}; font-size:10px;")
        self.chk_auto_sub.setChecked(True) # デフォルトON
        ctrl_row.addWidget(self.chk_auto_sub)
        
        skip_layout.addLayout(ctrl_row)
        
        right.addWidget(skip_frame)

        # --- Next Pitch Button ---
        self.btn_pitch = QPushButton("NEXT PITCH")
        self.btn_pitch.setStyleSheet(f"background:{THEME.primary}; color:black; font-weight:bold; padding:12px; border-radius:4px; border:none;")
        self.btn_pitch.clicked.connect(self._on_pitch)
        right.addWidget(self.btn_pitch)
        
        cl.addLayout(right, stretch=2)
        main_layout.addWidget(content)

    def _setup_timer(self):
        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self._on_pitch)

        # ★追加: アニメーションタイムアウト用タイマー（5秒でタイムアウト）
        self.anim_timeout_timer = QTimer(self)
        self.anim_timeout_timer.setSingleShot(True)
        self.anim_timeout_timer.timeout.connect(self._on_animation_timeout)

    def _on_animation_timeout(self):
        """アニメーションがタイムアウトした場合の処理"""
        if self.is_animating:
            # 強制的にアニメーションを停止
            self.zone_widget.is_animating = False
            self.zone_widget.anim_timer.stop()
            self.field_widget.is_animating = False
            self.field_widget.anim_timer.stop()
            self.is_animating = False
            self.btn_pitch.setEnabled(True)
            self.btn_skip.setEnabled(True)
            self._update_display()
            if self.live_engine and self.live_engine.is_game_over():
                self._finish()

    def start_game(self, home, away, date_str="2027-01-01", game_state=None):
        self.date_str = date_str
        from live_game_engine import LiveGameEngine
        self.live_engine = LiveGameEngine(home, away, game_state_manager=game_state)
        
        # スタジアム情報をUIにセット
        self.field_widget.set_stadium(self.live_engine.stadium)
        
        self.zone_widget.clear()
        self.field_widget.clear()
        self.track_panel.update_pitch(None)
        self.track_panel.update_batted_ball(None)
        self.need_zone_reset = False
        
        # 状態リセット（2試合目対策）
        self.user_team_side = 'home' # ユーザーはホームチームと仮定
        self.is_animating = False
        self.is_fast_forwarding = False
        self.ff_mode = None
        self.batting_strategy = "AUTO"
        self.auto_defense = False
        
        # タイマー停止
        if hasattr(self, 'ff_timer') and self.ff_timer.isActive():
            self.ff_timer.stop()
        if hasattr(self, 'sim_timer') and self.sim_timer.isActive():
            self.sim_timer.stop()
        
        # ボタン有効化
        self.btn_pitch.setEnabled(True)
        if hasattr(self, 'bat_buttons'):
            self._set_batting_strategy("AUTO")
        if hasattr(self, 'cmb_ff_attack'):
            self.cmb_ff_attack.setCurrentIndex(0)
        if hasattr(self, 'cmb_ff_defense'):
            self.cmb_ff_defense.setCurrentIndex(0)
        if hasattr(self, 'btn_skip_attack'):
            self.btn_skip_attack.setText("実行")
            self.btn_skip_attack.setEnabled(True)
        if hasattr(self, 'btn_skip_defense'):
            self.btn_skip_defense.setText("実行")
            self.btn_skip_defense.setEnabled(True)
        
        self.score_history = {"top": [], "bot": []}
        self.prev_state_score = (0, 0)
        self.prev_state_inning = (1, True)
        
        while self.log_layout.count():
            w = self.log_layout.takeAt(0).widget()
            if w: w.deleteLater()
            
        self._update_display()
        self._log("=== PLAY BALL ===", True)

    def _on_pitch(self):
        try:
            if self.is_animating or not self.live_engine or self.live_engine.is_game_over():
                return

            self.field_widget.clear()
            self.track_panel.update_batted_ball(None)

            if self.need_zone_reset:
                self.zone_widget.clear()
                self.track_panel.update_pitch(None)
                self.need_zone_reset = False

            # simulate_pitch呼び出し前に状態を保存
            batter, order_idx = self.live_engine.get_current_batter()
            pitcher, _ = self.live_engine.get_current_pitcher()
            st = self.live_engine.state
            pre_inning = st.inning
            pre_is_top = st.is_top

            # 自チーム（ユーザー）のターン判定
            user_is_attacking = (not st.is_top and self.user_team_side == 'home') or (st.is_top and self.user_team_side == 'away')
            user_is_defending = (st.is_top and self.user_team_side == 'home') or (not st.is_top and self.user_team_side == 'away')

            # 戦略の決定
            manual_strat = None
            shifts = None
            
            if user_is_attacking:
                manual_strat = None if self.batting_strategy == "AUTO" else self.batting_strategy
            
            if user_is_defending:
                shifts = {
                    'infield': self.cmb_infield.currentText(),
                    'outfield': self.cmb_outfield.currentText()
                }

            play_res, pitch, ball, steal_info = self.live_engine.simulate_pitch(manual_strategy=manual_strat, shifts=shifts)
            
            # 盗塁があった場合はログとアニメーションを表示
            if steal_info:
                steal_type = steal_info.get('steal_type', '2B')
                steal_name = "三盗" if steal_type == '3B' else "盗塁"
                if steal_info['success']:
                    self._log(f">> {steal_info['runner_name']} {steal_name}成功!", True)
                else:
                    self._log(f">> {steal_info['runner_name']} {steal_name}失敗 (アウト)", True)
                
                # 盗塁前のランナー状態を設定
                if steal_type == '3B':
                    runners_before = [False, True, False]  # 2塁にランナー
                else:
                    runners_before = [True, False, False]  # 1塁にランナー
                
                # 盗塁アニメーションを開始
                self.field_widget.animate_steal(steal_info, runners_before)
                self.is_animating = True
                self.btn_pitch.setEnabled(False)
                self._update_display()
                return

            res_name = play_res.name if hasattr(play_res, 'name') else str(play_res)
            display_res = self._get_display_result(res_name, st)

            # ★修正: pitchがNoneの場合（盗塁など）はアニメーションをスキップ
            if pitch is None and ball is None:
                # アニメーションなし - 直接表示更新
                self.lbl_pitch_res.setText(f"{display_res}")
                col = VisualStyle.get_result_color(display_res)
                self.lbl_pitch_res.setStyleSheet(f"background:{THEME.bg_card}; color:{col.name()}; padding:10px; border-left:4px solid {col.name()}; border-radius:4px; font-weight:bold; font-size:14px;")
                self._update_display()

                if self.live_engine.is_game_over():
                    self._finish()
                return

            self.is_animating = True
            self.is_animating = True
            self.btn_pitch.setEnabled(False)
            # ★追加: タイムアウトタイマー開始（5秒）
            self.anim_timeout_timer.start(5000)

            if pitch:
                self.zone_widget.set_pitcher_hand(getattr(pitcher, 'throws', '右'))
                self.zone_widget.animate_pitch(pitch, display_res)
                self.track_panel.update_pitch(pitch)

                self.lbl_pitch_res.setText(f"{int(pitch.velocity)}km {pitch.pitch_type}\n{display_res}")
                col = VisualStyle.get_result_color(display_res)
                self.lbl_pitch_res.setStyleSheet(f"background:{THEME.bg_card}; color:{col.name()}; padding:10px; border-left:4px solid {col.name()}; border-radius:4px; font-weight:bold; font-size:14px;")

            if ball:
                runners = [st.runner_1b is not None, st.runner_2b is not None, st.runner_3b is not None]
                self.field_widget.animate_ball(ball, runners, display_res)
                self.track_panel.update_batted_ball(ball)

            # ★修正: 保存しておいた状態を使用してログ出力
            if self._is_at_bat_end(res_name, st):
                team_side = "表" if pre_is_top else "裏"
                order_num = order_idx + 1
                self._log(f"[{pre_inning}回{team_side} {order_num}番] {batter.name}: {display_res}", True)
                self.need_zone_reset = True

        except Exception as e:
            traceback.print_exc()
            self._log(f"Error: {str(e)}", True)
            self.is_animating = False
            self.is_animating = False
            self.btn_pitch.setEnabled(True)

    def _get_display_result(self, res_name, st):
        if st.balls == 0 and st.strikes == 0:
            if "STRIKE" in res_name:
                if "CALLED" in res_name: return "見逃し三振"
                if "SWINGING" in res_name: return "空振り三振"
                return "三振"
            if res_name == "BALL": return "四球"
            if res_name == "HIT_BY_PITCH": return "死球"

        if res_name == "STRIKE_CALLED": return "見逃し"
        if res_name == "STRIKE_SWINGING": return "空振り"
        if res_name == "FOUL": return "ファウル"
        if res_name == "BALL": return "ボール"
        
        m = {
            'SINGLE': '安打', 'DOUBLE': '二塁打', 'TRIPLE': '三塁打', 'HOME_RUN': '本塁打', 
            'ERROR': '失策', 'GROUNDOUT': 'ゴロ', 'FLYOUT': 'フライ', 'LINEOUT': 'ライナー',
            'POPUP_OUT': 'フライ', 'DOUBLE_PLAY': '併殺', 'SACRIFICE_FLY': '犠飛',
            'SACRIFICE_BUNT': '犠打', 'FIELDERS_CHOICE': '野選'
        }
        
        if res_name == "IN_PLAY": return "ファウル"
        
        return m.get(res_name, res_name)

    def _is_at_bat_end(self, res_name, st):
        end_results = ['SINGLE', 'DOUBLE', 'TRIPLE', 'HOME_RUN', 'ERROR', 
                       'GROUNDOUT', 'FLYOUT', 'LINEOUT', 'POPUP_OUT', 
                       'DOUBLE_PLAY', 'SACRIFICE_FLY', 'SACRIFICE_BUNT',
                       'HIT_BY_PITCH', 'WALK', 'STRIKEOUT', 'FIELDERS_CHOICE']
        if res_name in end_results: return True
        if st.balls == 0 and st.strikes == 0: return True
        return False

    def _on_animation_step_finished(self):
        try:
            if self.zone_widget.is_animating or self.field_widget.is_animating: return
            # ★追加: タイムアウトタイマー停止
            self.anim_timeout_timer.stop()
            self.is_animating = False
            self.is_animating = False
            self.btn_pitch.setEnabled(True)
            self._update_display()
            
            # AI vs AI: Auto Advance
            if getattr(self, 'game_type', 'normal') == 'ai_vs_ai' and not self.live_engine.is_game_over():
                if not self.is_fast_forwarding:
                     QTimer.singleShot(800, self._on_pitch)

            if self.live_engine.is_game_over(): self._finish()
        except Exception as e:
            traceback.print_exc()
            # ★修正: 例外発生時もフリーズしないようにリカバリー
            self.anim_timeout_timer.stop()
            self.is_animating = False
            self.is_animating = False
            self.btn_pitch.setEnabled(True)

    def _open_lineup_dialog(self):
        if not self.live_engine: return
        dialog = LineupDialog(self.live_engine.home_team, self.live_engine.away_team, self)
        dialog.exec()

    def _update_player_panels(self):
        if not self.live_engine: return
        
        pitcher, _ = self.live_engine.get_current_pitcher()
        batter, batter_idx = self.live_engine.get_current_batter()
        
        if pitcher:
            # Stats Ranks
            vel = pitcher.stats.velocity
            v_rate = int(max(1, min(99, (vel - 130) * 2 + 30)))
            v_rank = THEME.get_rating_rank(v_rate)
            v_col = QColor(THEME.get_rating_color(v_rate))
            
            c_rank = THEME.get_rating_rank(pitcher.stats.control)
            c_col = QColor(THEME.get_rating_color(pitcher.stats.control))
            
            b_rank = THEME.get_rating_rank(pitcher.stats.breaking)
            b_col = QColor(THEME.get_rating_color(pitcher.stats.breaking))
            
            stm = pitcher.stats.stamina
            stm_col = QColor(THEME.get_rating_color(stm))

            p_stats = [
                ("SPD", v_rank, v_col),
                ("CON", c_rank, c_col),
                ("BRK", b_rank, b_col),
                ("STM", stm, stm_col)
            ]
            self.pitcher_card.update_player(pitcher, f"PITCHER (ERA: {pitcher.record.era:.2f})", p_stats)
            
        if batter:
            # Stats Ranks
            ct_rank = THEME.get_rating_rank(batter.stats.contact)
            ct_col = QColor(THEME.get_rating_color(batter.stats.contact))
            
            pw_rank = THEME.get_rating_rank(batter.stats.power)
            pw_col = QColor(THEME.get_rating_color(batter.stats.power))
            
            sp_rank = THEME.get_rating_rank(batter.stats.speed)
            sp_col = QColor(THEME.get_rating_color(batter.stats.speed))
            
            def_val = batter.stats.get_defense_range(batter.position)
            df_rank = THEME.get_rating_rank(def_val)
            df_col = QColor(THEME.get_rating_color(def_val))
            
            b_stats = [
                ("CON", ct_rank, ct_col),
                ("POW", pw_rank, pw_col),
                ("SPD", sp_rank, sp_col),
                ("DEF", df_rank, df_col)
            ]
            
            sub_text = f"BATTER {batter.position.value} (AVG: .{int(batter.record.batting_average*1000):03d})"
            self.batter_card.update_player(batter, sub_text, b_stats)

    def _update_display(self):
        st = self.live_engine.state
        h = self.live_engine.home_team
        a = self.live_engine.away_team
        
        # 攻守判定とパネル切り替え
        user_is_attacking = (not st.is_top and self.user_team_side == 'home') or (st.is_top and self.user_team_side == 'away')
        user_is_defending = (st.is_top and self.user_team_side == 'home') or (not st.is_top and self.user_team_side == 'away')
        
        self.attack_panel.setVisible(user_is_attacking)
        self.defense_panel.setVisible(user_is_defending)
        
        # AI観戦モードなら采配パネル全体を隠す
        if getattr(self, 'game_type', 'normal') == 'ai_vs_ai':
            self.manager_frame.setVisible(False)
        else:
            self.manager_frame.setVisible(True)
            
        if hasattr(self, 'cmb_ff_attack'): self.cmb_ff_attack.setVisible(True) # 常に表示
        if hasattr(self, 'cmb_ff_defense'): self.cmb_ff_defense.setVisible(True) # 常に表示
        # ボタンの有効無効制御
        if self.is_fast_forwarding:
            self.btn_pitch.setEnabled(False)
            self.btn_skip_start.setText("停止")
            self.btn_skip_start.setEnabled(True)
        else:
            self.btn_pitch.setEnabled(not self.is_animating)
            self.btn_skip_start.setText("早送り開始")
            self.btn_skip_start.setEnabled(not self.is_animating)

        if user_is_attacking:
            self.mgr_title.setText(f"[采配] {self.user_team_side.upper()} 攻撃 (操作中)")
            self.mgr_title.setStyleSheet(f"color:{THEME.primary}; font-weight:bold; font-size:11px; background:#331111; padding:2px;")
        elif user_is_defending:
            self.mgr_title.setText(f"[采配] {self.user_team_side.upper()} 守備 (操作中)")
            self.mgr_title.setStyleSheet(f"color:{THEME.primary}; font-weight:bold; font-size:11px; background:#111133; padding:2px;")
        else:
            self.mgr_title.setText(f"[観戦] AI対戦中")
            self.mgr_title.setStyleSheet(f"color:#888; font-weight:bold; font-size:11px;")
        
        # シフト表示を更新
        if hasattr(self, 'lbl_shift_indicator') and hasattr(self, 'cmb_infield') and hasattr(self, 'cmb_outfield'):
            infield_shift = self.cmb_infield.currentText()
            outfield_shift = self.cmb_outfield.currentText()
            self.lbl_shift_indicator.setText(f"⬡ 内野: {infield_shift.replace('内野', '')} | 外野: {outfield_shift.replace('外野', '')}")
        
        # Scoreboard Update

        
        # Player Panels Update
        self._update_player_panels()
        
        prev_inn, prev_top = self.prev_state_inning
        
        diff_h = st.home_score - self.prev_state_score[0]
        diff_a = st.away_score - self.prev_state_score[1]
        
        target_idx = prev_inn - 1
        # Dynamic extension for target_idx
        while len(self.score_history["top"]) <= target_idx: self.score_history["top"].append(0)
        while len(self.score_history["bot"]) <= target_idx: self.score_history["bot"].append(0)
        
        if prev_top: self.score_history["top"][target_idx] += diff_a
        else: self.score_history["bot"][target_idx] += diff_h
                
        self.prev_state_score = (st.home_score, st.away_score)
        self.prev_state_inning = (st.inning, st.is_top)
        
        curr_idx = st.inning - 1
        # Dynamic extension for current inning
        # Only extend if we are not Game Over to avoid ghost innings (e.g. 10th inning recorded after 9th walkoff)
        # But if inning logic actually advanced to 10th (Tie), we DO want it.
        # The engine sets is_game_over() = True if inning>=9 and win condition met.
        # If is_game_over(), we should typically NOT start a new empty inning column.
        should_extend = True
        if self.live_engine.is_game_over():
            # If game over, only extend if strict index needs it? 
            # If inning is 9 (game ended), curr_idx is 8. If len is 8, we append.
            # If inning advanced to 10 (Tie end?), curr_idx 9.
            # Usually if Game Over, we stop updating future innings.
            # If we are strictly at the end of last played inning.
            pass

        # Append 0 for current inning if needed
        while len(self.score_history["top"]) <= curr_idx: self.score_history["top"].append(0)
        while len(self.score_history["bot"]) <= curr_idx: self.score_history["bot"].append(0)
 
        for i in range(len(self.score_history["top"])):
            val_top = self.score_history["top"][i]
            val_bot = self.score_history["bot"][i]
            if val_top is not None: self.scoreboard.line_score.set_inning_score(i+1, True, val_top)
            if val_bot is not None: self.scoreboard.line_score.set_inning_score(i+1, False, val_bot)
        
        # スタッツの辞書を作成して渡す
        h_stats = {'hits': st.home_hits, 'errors': st.home_errors}
        a_stats = {'hits': st.away_hits, 'errors': st.away_errors}
        self.scoreboard.update_display(st, h.name, a.name, h_stats, a_stats)
        
        p, _ = self.live_engine.get_current_pitcher()
        b, _ = self.live_engine.get_current_batter()
        
        # チーム名の判定
        p_team_name = h.name if st.is_top else a.name
        b_team_name = a.name if st.is_top else h.name

        if p:
            rt_p = self.live_engine.get_realtime_stats(p)
            p_type_char = p.pitch_type.value[:1] if hasattr(p.pitch_type, "value") else "投"
            self.pitcher_card.update_player(p, f"[{p_team_name}] #{p.uniform_number} {p_type_char}", [
                ("ERA", f"{rt_p['era']:.2f}", VisualStyle.TEXT_MAIN),
                ("SO", rt_p['so'], VisualStyle.COLOR_HIT),
                ("STM", int(st.current_pitcher_stamina()), VisualStyle.COLOR_BALL)
            ])
        if b:
            rt_b = self.live_engine.get_realtime_stats(b)
            self.batter_card.update_player(b, f"[{b_team_name}] #{b.uniform_number} {b.position.value[:2]}", [
                ("AVG", f"{rt_b['avg']:.3f}", VisualStyle.TEXT_MAIN),
                ("HR", rt_b['hr'], VisualStyle.COLOR_STRIKE),
                ("RBI", rt_b['rbi'], VisualStyle.COLOR_OUT)
            ])
            
        if not self.is_animating:
            runners = [st.runner_1b is not None, st.runner_2b is not None, st.runner_3b is not None]
            self.field_widget.set_runners_only(runners)

    def _on_player_clicked(self, p):
        self.go_to_player_detail.emit(p)

    def _on_skip(self):
        if not self.live_engine: return
        self.is_animating = True
        self.btn_pitch.setEnabled(False)
        self.btn_skip.setEnabled(False)
        
        try:
            while not self.live_engine.is_game_over():
                self.live_engine.simulate_pitch()
        except Exception:
            traceback.print_exc()
            
        self.zone_widget.clear()
        self.field_widget.clear()
        self.is_animating = False
        self._update_display()
        self._finish()

    def _finish(self):
        self.sim_timer.stop()
        self.btn_pitch.setEnabled(False)
        if hasattr(self, 'btn_skip_start'): self.btn_skip_start.setEnabled(False)
        game_result = self.live_engine.finalize_game_stats(self.date_str)
        self._log("=== GAME SET ===", True)
        
        # Collect Home Run info
        hr_list = []
        if game_result and "game_stats" in game_result:
             for p, stats in game_result["game_stats"].items():
                 if stats['home_runs'] > 0:
                     team_name = self.live_engine.home_team.name if p in self.live_engine.home_team.players else self.live_engine.away_team.name
                     hr_list.append((p.name, stats['home_runs'], team_name))
        
        res = {
            "home_team": self.live_engine.home_team,
            "away_team": self.live_engine.away_team,
            "home_score": self.live_engine.state.home_score,
            "away_score": self.live_engine.state.away_score,
            "winner": self.live_engine.get_winner(),
            "pitcher_result": {
                "win": game_result.get("win"),
                "loss": game_result.get("loss"),
                "save": game_result.get("save")
            } if game_result else {},
            "home_runs": hr_list,
            "score_history": self.score_history, # {"top": [], "bot": []}
            "hits": (self.live_engine.state.home_hits, self.live_engine.state.away_hits),
            "errors": (self.live_engine.state.home_errors, self.live_engine.state.away_errors),
            "game_stats": game_result.get("game_stats", {}),
            "highlights": game_result.get("highlights", []),
            "home_pitchers_used": list(self.live_engine.state.home_pitchers_used),
            "away_pitchers_used": list(self.live_engine.state.away_pitchers_used)
        }
        self.game_finished.emit(res)

    def _log(self, text, highlight=False):
        l = QLabel(text)
        col = THEME.primary if highlight else THEME.text_secondary
        l.setStyleSheet(f"color: {col}; font-size: 11px; margin-bottom: 2px;")
        self.log_layout.insertWidget(0, l)
    
    def _set_batting_strategy(self, strategy):
        """打撃戦略を設定"""
        # UIの戦略名をエンジン用に変換
        strategy_map = {
            "AUTO": "AUTO", "通常": "SWING", "強振": "POWER", "流し": "NAGASHI",
            "バント": "BUNT", "盗塁": "STEAL"
        }
        self.batting_strategy = strategy_map.get(strategy, "AUTO")
        for s, btn in self.bat_buttons.items():
            btn.setChecked(s == strategy)
    
    def _execute_ibb(self):
        """敬遠四球を実行"""
        if not self.live_engine or self.live_engine.is_game_over():
            return
        # 4ボールを与えて歩かせる
        self.live_engine.state.balls = 4
        self.live_engine._walk()
        self._log(">> 敬遠四球", True)
        self._update_display()
    
    def _open_def_sub_dialog(self):
        """守備交代"""
        if self._is_user_attacking(): return
        
        team = self.live_engine.home_team if self.user_team_side == 'home' else self.live_engine.away_team
        
        # 交代対象を選択（現在の守備についている選手）
        fielders_for_display = []
        for pid in team.current_lineup:
            p = team.players[pid]
            # 投手は「継投」で変えるので除外すべきか？ Userの自由度のため含めるか。
            # わかりやすさのため投手は除外（継投を使ってね、とする）
            is_pitcher_or_dh = False
            try:
                if hasattr(p.position, 'name'):
                    if p.position.name in ["PITCHER", "DH"]: is_pitcher_or_dh = True
                elif str(p.position) in ["Position.PITCHER", "Position.DH"] or "PITCHER" in str(p.position).upper():
                    is_pitcher_or_dh = True
            except: 
                pass
                
            if not is_pitcher_or_dh:
                fielders_for_display.append(p)
                
        dialog = PlayerSelectionDialog(fielders_for_display, "交代する選手を選択", self, mode="fielder")
        if dialog.exec():
            target = dialog.selected_player
            # 交代相手を選択（ベンチ）
            candidates = []
            lineup_pids = set(team.current_lineup)
            for p in team.get_active_roster_players():
                pid = team.players.index(p)
                if pid not in lineup_pids:
                    candidates.append(p)
            
            sub_dialog = PlayerSelectionDialog(candidates, f"{target.name} に代わる選手", self, mode="fielder")
            if sub_dialog.exec():
                new_player = sub_dialog.selected_player
                self._substitute_fielder(target, new_player)
                self._log(f"守備交代: {target.name} -> {new_player.name}", True)

    def _substitute_fielder(self, target, new_player):
        self._substitute_runner(target, new_player) # 実装は同じ（ラインアップのID書き換え）なので再利用

    def _perform_auto_substitution(self):
        """自動選手交代ロジック"""
        if not self.chk_auto_sub.isChecked(): return
        
        st = self.live_engine.state
        user_is_attacking = self._is_user_attacking()
        
        # 攻撃時: 代打・代走
        if user_is_attacking:
            batter, order_idx = self.live_engine.get_current_batter()
            
            # 代打: 7回以降、チャンスor敗戦処理、打力が低い(投手etc)場合に代打
            # 簡易ロジック: 投手ならほぼ確実に代打 (DHなし時)
            # 得点圏で打率低いなら代打
            is_pitcher = (batter.position.name == "PITCHER")
            is_chance = (st.runner_2b or st.runner_3b)
            is_late_game = (st.inning >= 7)
            
            should_ph = False
            if is_pitcher and is_chance: should_ph = True
            elif is_pitcher and is_late_game: should_ph = True
            elif is_chance and is_late_game and batter.stats.contact < 60: should_ph = True # 簡易
            
            if should_ph:
                # 候補選定: ミートが高い順
                team = self.live_engine.home_team if self.user_team_side == 'home' else self.live_engine.away_team
                candidates = []
                lineup_pids = set(team.current_lineup)
                for p in team.get_active_roster_players():
                    if team.players.index(p) not in lineup_pids and p.position.name != "PITCHER":
                        candidates.append(p)
                candidates.sort(key=lambda x: x.stats.contact, reverse=True)
                
                if candidates:
                    ph = candidates[0]
                    self._substitute_batter(ph)
                    self._log(f"[AUTO] 代打: {batter.name} -> {ph.name}", True)
                    return # 1ターンに1回

            # 代走: 終盤、僅差、出塁ランナーが遅い場合
            if is_late_game and abs(st.home_score - st.away_score) <= 3:
                runners = []
                if st.runner_1b: runners.append(('1B', st.runner_1b))
                if st.runner_2b: runners.append(('2B', st.runner_2b))
                if st.runner_3b: runners.append(('3B', st.runner_3b))
                
                for base, runner in runners:
                    if runner.stats.speed < 60:
                        # 候補: 足が速い順
                        team = self.live_engine.home_team if self.user_team_side == 'home' else self.live_engine.away_team
                        candidates = []
                        lineup_pids = set(team.current_lineup)
                        for p in team.get_active_roster_players():
                            if team.players.index(p) not in lineup_pids and p.position.name != "PITCHER":
                                candidates.append(p)
                        candidates.sort(key=lambda x: x.stats.speed, reverse=True)
                        
                        if candidates and candidates[0].stats.speed > 75:
                            pr = candidates[0]
                            self._substitute_runner(runner, pr)
                            self._log(f"[AUTO] 代走: {runner.name} -> {pr.name}", True)
                            return
        
        # 守備時: 投手交代などはエンジン任せだが、ここでも補完できる
        else:
             # エンジン側で処理されているので何もしない
             pass

    def _toggle_auto_defense(self):
        self.auto_defense = not self.auto_defense
        s = "ON" if self.auto_defense else "OFF"
        self._log(f"守備AUTOモード: {s}", True)
        self.btn_auto_def.setChecked(self.auto_defense)

    # --- 選手交代ロジック ---
    def _open_ph_dialog(self):
        """代打"""
        if not self._is_user_attacking():
            self._log("攻撃中のみ可能です", False); return
        
        team = self.live_engine.home_team if self.user_team_side == 'home' else self.live_engine.away_team
        
        # 候補: ベンチ入り野手 (スタメン以外)
        # 簡易的に active_roster から current_lineup にいない選手
        candidates = []
        lineup_pids = set(team.current_lineup)
        for p in team.get_active_roster_players():
            pid = team.players.index(p)
            is_pitcher = False
            if hasattr(p.position, 'name'):
                 if p.position.name == "PITCHER": is_pitcher = True
            elif "PITCHER" in str(p.position).upper(): is_pitcher = True

            if pid not in lineup_pids and not is_pitcher:
                candidates.append(p)
        
        dialog = PlayerSelectionDialog(candidates, "代打選択", self, mode="fielder")
        if dialog.exec():
            p = dialog.selected_player
            self._log(f"代打起用: {p.name}", True)
            self._substitute_batter(p)

    def _open_pr_dialog(self):
        """代走"""
        if not self._is_user_attacking(): return
        st = self.live_engine.state
        runners = []
        if st.runner_1b: runners.append(st.runner_1b)
        if st.runner_2b: runners.append(st.runner_2b)
        if st.runner_3b: runners.append(st.runner_3b)
        
        if not runners:
            self._log("ランナーがいません", False); return
            
        target = runners[0] # デフォルト
        if len(runners) > 1:
            # 複数いる場合は簡易的に一番前のランナーなど...あるいは選択画面をもう一個出すのが面倒なので
            # 「代走」ボタンを押したらランナー全員クリック可能にして...というのは複雑。
            # 今回はリストダイアログで「誰を変える？」と聞くのが正解だが、
            # リクエスト実装優先のため、最も先のランナーを対象とする（または実装簡略化）
            # ここでは「先頭ランナー」を対象にします
            if st.runner_3b: target = st.runner_3b
            elif st.runner_2b: target = st.runner_2b
            elif st.runner_1b: target = st.runner_1b
            
        team = self.live_engine.home_team if self.user_team_side == 'home' else self.live_engine.away_team
        candidates = []
        lineup_pids = set(team.current_lineup)
        for p in team.get_active_roster_players():
            pid = team.players.index(p)
            is_pitcher = False
            if hasattr(p.position, 'name'):
                 if p.position.name == "PITCHER": is_pitcher = True
            elif "PITCHER" in str(p.position).upper(): is_pitcher = True
            
            if pid not in lineup_pids and not is_pitcher:
                candidates.append(p)
                
        dialog = PlayerSelectionDialog(candidates, f"代走選択 (対象: {target.name})", self, mode="fielder")
        if dialog.exec():
            p = dialog.selected_player
            self._log(f"代走起用: {target.name} -> {p.name}", True)
            self._substitute_runner(target, p)
            
    def _open_pitcher_sub_dialog(self):
        """投手交代"""
        # 守備中のみ
        if self._is_user_attacking(): return
        
        team = self.live_engine.home_team if self.user_team_side == 'home' else self.live_engine.away_team
        candidates = []
        # ブルペン（ベンチ入り投手）
        # current_lineupにいてもDHなしなら投手も打席立つので、厳密には「現在の投手以外」
        current_pitcher, _ = self.live_engine.get_current_pitcher()
        for p in team.get_active_roster_players():
            is_pitcher = False
            if hasattr(p.position, 'name'):
                 if p.position.name == "PITCHER": is_pitcher = True
            elif "PITCHER" in str(p.position).upper(): is_pitcher = True
            
            # Rotation Filter
            pid = team.players.index(p)
            if pid in team.rotation:
                continue

            if is_pitcher and p != current_pitcher:
                candidates.append(p)
        
        dialog = PlayerSelectionDialog(candidates, "救援投手選択", self, mode="pitcher")
        if dialog.exec():
            p = dialog.selected_player
            self._log(f"投手交代: {current_pitcher.name} -> {p.name}", True)
            self.live_engine.change_pitcher(p)
            self._update_display()

    def _substitute_batter(self, new_player):
        # 現在の打者（の打順）を探して入れ替え
        team = self.live_engine.home_team if self.user_team_side == 'home' else self.live_engine.away_team
        # 打順インデックス
        st = self.live_engine.state
        order_idx = st.home_batter_order if self.user_team_side == 'home' else st.away_batter_order
        # lineup更新
        try:
            lineup = team.current_lineup # List[int] (player index)
            new_pid = team.players.index(new_player)
            lineup[order_idx] = new_pid # 上書き
            self._update_display()
        except:
            pass

    def _substitute_runner(self, target_runner, new_player):
        st = self.live_engine.state
        team = self.live_engine.home_team if self.user_team_side == 'home' else self.live_engine.away_team
        
        # State上のランナー差し替え
        if st.runner_1b == target_runner: st.runner_1b = new_player
        elif st.runner_2b == target_runner: st.runner_2b = new_player
        elif st.runner_3b == target_runner: st.runner_3b = new_player
        
        # Lineup上の差し替え (ランナーも打順にいるはず)
        try:
            old_pid = team.players.index(target_runner)
            new_pid = team.players.index(new_player)
            lineup = team.current_lineup
            if old_pid in lineup:
                idx = lineup.index(old_pid)
                lineup[idx] = new_pid
            self._update_display()
        except:
            pass

    def _on_skip_click_unified(self):
        """統合スキップボタンクリック時"""
        if self.is_fast_forwarding:
            self._stop_skip()
        else:
            # 現在の状態に応じてモードを自動決定して開始
            # 攻撃中ならattack、守備中ならdefense、ただしcondition checkは両方見る（停止条件として）
            # ロジック上は _fast_forward_step で毎回 check_condition するのでモードは不要だが
            # ログ出力などに使うため判定
            mode = 'attack' if self._is_user_attacking() else 'defense'
            self._start_skip(mode)

    def _is_user_attacking(self):
        st = self.live_engine.state
        return (not st.is_top and self.user_team_side == 'home') or (st.is_top and self.user_team_side == 'away')

    def _start_skip(self, mode):
        if not self.live_engine or self.live_engine.is_game_over(): return
        
        self.ff_mode = mode # 現在のフェーズ (attack/defense)
        self.is_fast_forwarding = True
        self.ff_start_inning = self.live_engine.state.inning
        self.ff_start_is_top = self.live_engine.state.is_top
        self.ff_start_batter = self.live_engine.get_current_batter()[0]
        
        self.btn_skip_start.setText("停止")
        self._update_display() 
        
        self.ff_timer = QTimer()
        self.ff_timer.timeout.connect(self._fast_forward_step)
        # スライダー: 1(遅い) ~ 10(速い)
        # 1 -> 545ms, 10 -> 50ms
        val = self.sld_speed.value()
        interval = max(50, 600 - val * 55)
        self.ff_timer.start(interval)
    
    def _stop_skip(self):
        self.is_fast_forwarding = False
        self.ff_mode = None
        if hasattr(self, 'ff_timer') and self.ff_timer.isActive():
            self.ff_timer.stop()
        
        self.btn_skip_start.setText("早送り開始")
        self._log(">> 早送り停止", True)
        self._update_display()

    def _fast_forward_step(self):
        """早送り1ステップ"""
        if not self.live_engine or self.live_engine.is_game_over():
            self._stop_skip()
            if self.live_engine.is_game_over():
                self._finish()
            return
        
        if self._check_ff_stop_condition():
            self._stop_skip()
            return

        # 状態保存（ログ用）
        st = self.live_engine.state
        pre_inning = st.inning
        pre_is_top = st.is_top
        batter, _ = self.live_engine.get_current_batter()

        # 自動選手交代チェック
        self._perform_auto_substitution()
        # 交代が行われた場合、batter変数は古いままなので再取得したほうがログには正しいが
        # simulate_pitch内でget_current_batter呼ぶので動作はOK
        batter, _ = self.live_engine.get_current_batter() # ログ用に更新しておく


        # シミュレート 
        # 守備AUTOなら自動、そうでなければUI設定...だがFF中は簡略化のため現状維持
        # 本当はシフトなども考慮すべきだが、FF速度優先でNone
        manual_strat = None
        shifts = None
        
        # 自チーム采配のみ適用（AUTOモードでない場合）
        # ただしFF中は「お任せ」で進むのが基本
        
        play_res, pitch, ball, steal_info = self.live_engine.simulate_pitch(manual_strategy=None, shifts=None)

        if steal_info:
            steal_type = steal_info.get('steal_type', '2B')
            s_res = "成功" if steal_info['success'] else "失敗"
            self._log(f">> {steal_type}盗塁{s_res}", True)
        
        res_name = play_res.name if hasattr(play_res, 'name') else str(play_res)
        display_res = self._get_display_result(res_name, st)

        # 打席完了時のみログ出力
        if self._is_at_bat_end(res_name, st):
            top_bot = "表" if pre_is_top else "裏"
            self._log(f"[{pre_inning}回{top_bot}] {batter.name}: {display_res}", True)
        elif res_name in ["STRIKEOUT", "WALK", "HIT_BY_PITCH"]: 
             top_bot = "表" if pre_is_top else "裏"
             self._log(f"[{pre_inning}回{top_bot}] {batter.name}: {display_res}", True)

        self._update_display()
    
    def _check_ff_stop_condition(self):
        """早送り停止条件をチェック"""
        st = self.live_engine.state
        
        # 現在攻撃中か守備中か
        user_is_attacking = self._is_user_attacking()
        
        if user_is_attacking:
            cond = self.cmb_ff_attack.currentText()
            self.ff_mode = 'attack'
        else:
            cond = self.cmb_ff_defense.currentText()
            self.ff_mode = 'defense'
            
        # 条件判定
        if cond == "次の打者":
            current_batter = self.live_engine.get_current_batter()[0]
            return current_batter != self.ff_start_batter
        elif cond == "イニング終了":
            return st.inning != self.ff_start_inning or st.is_top != self.ff_start_is_top
        elif cond == "チャンス":
            return user_is_attacking and (st.runner_2b or st.runner_3b)
        elif cond == "ピンチ":
            return (not user_is_attacking) and (st.runner_2b or st.runner_3b)
        elif cond == "満塁":
            return st.runner_1b and st.runner_2b and st.runner_3b
        elif cond == "得点圏":
            return st.runner_2b or st.runner_3b
        elif cond == "犠牲フライ圏":
            return st.runner_3b and st.outs < 2
        elif cond.endswith("回まで"):
            try:
                target_inn = int(cond.replace("回まで", ""))
                return st.inning >= target_inn
            except:
                return False
        elif cond == "試合終了":
            return False 
            
        return False
    
    def _on_speed_change(self, val):
        if self.is_fast_forwarding and hasattr(self, 'ff_timer') and self.ff_timer.isActive():
            interval = max(50, 600 - val * 55)
            self.ff_timer.start(interval) # startでインターバル更新
