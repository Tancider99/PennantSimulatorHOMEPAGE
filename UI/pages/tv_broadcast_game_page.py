# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - TV Broadcast Game Page
Updated: Accurate Field Dimensions (Stadium PF), Fixed Trajectory Line
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout, QSizePolicy, QTableWidget, 
    QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QTimer, QPointF, QRectF
from PySide6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QPainterPath, QPolygonF
)

import sys
import os
import math
import traceback

# パス設定
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
try:
    from UI.theme import get_theme
    from live_game_engine import PitchData, BattedBallData
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

    def set_runners_only(self, runners):
        self.runners = runners
        self.update()

    def clear(self):
        self.batted_ball = None
        self.result_str = ""
        self.is_animating = False
        self.anim_timer.stop()
        self.update()

    def _update_anim(self):
        self.anim_progress += 0.008
        if self.anim_progress >= 1.0:
            self.anim_progress = 1.0
            self.is_animating = False
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
        
        ctrl_x = tx / 2
        h_factor = ball.hang_time * 40 * scale
        ctrl_y = (ty / 2) - h_factor
        
        # 現在位置
        curr_x = cx + (2 * (1-t) * t * ctrl_x + t*t * tx)
        curr_y = cy + (2 * (1-t) * t * ctrl_y + t*t * ty)
        
        path = QPainterPath()
        path.moveTo(cx, cy)
        
        # ★修正: 軌跡の線がボールを追い越さないように計算を修正
        # 全体を50分割したとして、現在のtまでに相当するステップだけ線を描く
        total_segments = 50
        current_segments = int(total_segments * t)
        
        for i in range(1, current_segments + 1):
            st = i / total_segments
            # ベジェ計算
            sx = cx + (2 * (1-st) * st * ctrl_x + st*st * tx)
            sy = cy + (2 * (1-st) * st * ctrl_y + st*st * ty)
            path.lineTo(sx, sy)
            
        # 最後に現在地点まで繋ぐ
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
                if p_type in sliders: is_pointing_left = True  
                elif p_type in shoots: is_pointing_left = False 
            else: 
                if p_type in sliders: is_pointing_left = False 
                elif p_type in shoots: is_pointing_left = True  
            
            if is_pointing_left:
                poly = QPolygonF([QPointF(x+size*0.8, y-size), QPointF(x+size*0.8, y+size), QPointF(x-size*0.8, y)])
            else:
                poly = QPolygonF([QPointF(x-size*0.8, y-size), QPointF(x-size*0.8, y+size), QPointF(x+size*0.8, y)])
            painter.drawPolygon(poly)
            
        painter.setPen(Qt.black)
        painter.setFont(QFont(VisualStyle.FONT_NUM, 8, QFont.Bold))
        painter.drawText(QRectF(x-size, y-size, size*2, size*2), Qt.AlignCenter, text)


class LineScoreTable(QTableWidget):
    """イニングスコア"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(75)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setVisible(True)
        self.setShowGrid(False)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setFocusPolicy(Qt.NoFocus)
        
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.setStyleSheet(f"""
            QTableWidget {{ background-color: transparent; border: none; }}
            QHeaderView::section {{
                background-color: transparent;
                color: {THEME.text_secondary};
                font-size: 10px; font-weight: bold;
                border: none; border-bottom: 1px solid {THEME.border};
            }}
            QTableWidget::item {{
                color: {THEME.text_primary};
                font-family: '{VisualStyle.FONT_NUM}';
                font-size: 14px; font-weight: bold;
                border-bottom: 1px solid {THEME.border_muted};
            }}
        """)
        
        self.cols = ["TEAM"] + [str(i) for i in range(1, 10)] + ["R", "H", "E"]
        self.setColumnCount(len(self.cols))
        self.setHorizontalHeaderLabels(self.cols)
        self.setRowCount(2)
        
        self.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        h = self.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Stretch)

    def update_names(self, home, away):
        self.setItem(0, 0, QTableWidgetItem(away[:3].upper()))
        self.setItem(1, 0, QTableWidgetItem(home[:3].upper()))

    def update_score_data(self, inning, is_top, h_runs, a_runs, h_hits, a_hits, h_err, a_err):
        self.setItem(0, 10, QTableWidgetItem(str(a_runs)))
        self.setItem(0, 11, QTableWidgetItem(str(a_hits)))
        self.setItem(0, 12, QTableWidgetItem(str(a_err)))
        self.setItem(1, 10, QTableWidgetItem(str(h_runs)))
        self.setItem(1, 11, QTableWidgetItem(str(h_hits)))
        self.setItem(1, 12, QTableWidgetItem(str(h_err)))

    def set_inning_score(self, inning, is_top, score):
        if inning < 1 or inning > 9: return
        row = 0 if is_top else 1
        self.setItem(row, inning, QTableWidgetItem(str(score)))


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
        
        self.line_score = LineScoreTable()
        layout.addWidget(self.line_score)

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
        self.line_score.update_score_data(st.inning, st.is_top, st.home_score, st.away_score, 
                                          h_stats.get('hits',0), a_stats.get('hits',0),
                                          h_stats.get('errors',0), a_stats.get('errors',0))


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
        l.addWidget(h)
        
        self.lbl_name = QLabel("---")
        self.lbl_name.setStyleSheet(f"color:{THEME.text_primary}; font-size:18px; font-weight:900;")
        self.lbl_name.setAlignment(Qt.AlignRight if align_right else Qt.AlignLeft)
        l.addWidget(self.lbl_name)
        
        self.lbl_sub = QLabel("---")
        self.lbl_sub.setStyleSheet(f"color:{THEME.text_secondary}; font-size:11px;")
        self.lbl_sub.setAlignment(Qt.AlignRight if align_right else Qt.AlignLeft)
        l.addWidget(self.lbl_sub)
        
        self.stats_box = QHBoxLayout()
        l.addLayout(self.stats_box)

    def mousePressEvent(self, e):
        if self.player: self.clicked.emit(self.player)
        super().mousePressEvent(e)

    def update_player(self, p, sub, stats):
        self.player = p
        self.lbl_name.setText(p.name)
        self.lbl_sub.setText(sub)
        
        while self.stats_box.count(): 
            w = self.stats_box.takeAt(0).widget()
            if w: w.deleteLater()
            
        for k, v, c in stats:
            bx = QVBoxLayout(); bx.setSpacing(0)
            l = QLabel(k); l.setAlignment(Qt.AlignCenter)
            l.setStyleSheet("color:#888; font-size:9px;")
            val = QLabel(str(v)); val.setAlignment(Qt.AlignCenter)
            val.setStyleSheet(f"color:{c.name()}; font-size:14px; font-weight:bold; font-family:'Consolas';")
            bx.addWidget(l); bx.addWidget(val)
            self.stats_box.addLayout(bx)


# ========================================
# メイン画面クラス
# ========================================
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
        
        self.score_history = {"top": [0]*10, "bot": [0]*10}
        self.prev_state_score = (0, 0)
        self.prev_state_inning = (1, True)
        
        self._setup_ui()
        self._setup_timer()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.scoreboard = ScoreBoardWidget()
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
        
        self.field_widget = TacticalField()
        self.field_widget.animation_finished.connect(self._on_animation_step_finished)
        cl.addWidget(self.field_widget, stretch=4)
        
        right = QVBoxLayout(); right.setSpacing(10)
        self.batter_card = PlayerInfoPanel("BATTER", True)
        self.batter_card.clicked.connect(self._on_player_clicked)
        right.addWidget(self.batter_card)
        
        self.log_area = QScrollArea()
        self.log_area.setWidgetResizable(True)
        self.log_area.setStyleSheet(f"background:{THEME.bg_card}; border:none; border-radius:4px;")
        self.log_content = QWidget()
        self.log_layout = QVBoxLayout(self.log_content)
        self.log_layout.setAlignment(Qt.AlignTop)
        self.log_area.setWidget(self.log_content)
        right.addWidget(self.log_area, stretch=1)
        
        ctrl = QHBoxLayout()
        self.btn_pitch = QPushButton("NEXT PITCH")
        self.btn_pitch.setStyleSheet(f"background:{THEME.primary}; color:black; font-weight:bold; padding:12px; border-radius:4px; border:none;")
        self.btn_pitch.clicked.connect(self._on_pitch)
        
        self.btn_skip = QPushButton("SKIP")
        self.btn_skip.setStyleSheet(f"background:{THEME.bg_card_elevated}; color:{THEME.text_primary}; padding:12px; border-radius:4px; border:none;")
        self.btn_skip.clicked.connect(self._on_skip)
        
        ctrl.addWidget(self.btn_pitch, 2)
        ctrl.addWidget(self.btn_skip, 1)
        right.addLayout(ctrl)
        
        cl.addLayout(right, stretch=2)
        main_layout.addWidget(content)

    def _setup_timer(self):
        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self._on_pitch)

    def start_game(self, home, away, date_str="2027-01-01"):
        self.date_str = date_str
        from live_game_engine import LiveGameEngine
        self.live_engine = LiveGameEngine(home, away)
        
        # ★修正: 試合開始時にスタジアム情報をUIにセット
        self.field_widget.set_stadium(self.live_engine.stadium)
        
        self.zone_widget.clear()
        self.field_widget.clear()
        self.track_panel.update_pitch(None)
        self.track_panel.update_batted_ball(None)
        self.need_zone_reset = False
        
        self.score_history = {"top": [None]*10, "bot": [None]*10}
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

            # ★修正: simulate_pitch呼び出し前に状態を保存（イニングチェンジ後に状態が変わるため）
            batter, order_idx = self.live_engine.get_current_batter()
            pitcher, _ = self.live_engine.get_current_pitcher()
            st = self.live_engine.state
            pre_inning = st.inning
            pre_is_top = st.is_top

            play_res, pitch, ball = self.live_engine.simulate_pitch()

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
            self.btn_pitch.setEnabled(False)
            self.btn_skip.setEnabled(False)

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
            self.btn_pitch.setEnabled(True)
            self.btn_skip.setEnabled(True)

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
            'POPUP_OUT': '飛球', 'DOUBLE_PLAY': '併殺', 'SACRIFICE_FLY': '犠飛',
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
        if self.zone_widget.is_animating or self.field_widget.is_animating: return
        self.is_animating = False
        self.btn_pitch.setEnabled(True)
        self.btn_skip.setEnabled(True)
        self._update_display()
        
        if self.live_engine.is_game_over(): self._finish()

    def _update_display(self):
        st = self.live_engine.state
        h = self.live_engine.home_team
        a = self.live_engine.away_team
        
        prev_inn, prev_top = self.prev_state_inning
        
        diff_h = st.home_score - self.prev_state_score[0]
        diff_a = st.away_score - self.prev_state_score[1]
        
        target_idx = prev_inn - 1
        if target_idx < 10:
            if self.score_history["top"][target_idx] is None: self.score_history["top"][target_idx] = 0
            if self.score_history["bot"][target_idx] is None: self.score_history["bot"][target_idx] = 0
            
            if prev_top: self.score_history["top"][target_idx] += diff_a
            else: self.score_history["bot"][target_idx] += diff_h
                
        self.prev_state_score = (st.home_score, st.away_score)
        self.prev_state_inning = (st.inning, st.is_top)
        
        curr_idx = st.inning - 1
        if curr_idx < 10:
            if self.score_history["top"][curr_idx] is None: self.score_history["top"][curr_idx] = 0
            if self.score_history["bot"][curr_idx] is None: self.score_history["bot"][curr_idx] = 0

        for i in range(min(st.inning, 9)):
            val_top = self.score_history["top"][i]
            val_bot = self.score_history["bot"][i]
            if val_top is not None: self.scoreboard.line_score.set_inning_score(i+1, True, val_top)
            if val_bot is not None: self.scoreboard.line_score.set_inning_score(i+1, False, val_bot)
            
        self.scoreboard.update_display(st, h.name, a.name, {}, {})
        
        p, _ = self.live_engine.get_current_pitcher()
        b, _ = self.live_engine.get_current_batter()
        
        if p:
            self.pitcher_card.update_player(p, f"#{p.uniform_number} {p.pitch_type.value[:1]}", [
                ("ERA", f"{p.record.era:.2f}", VisualStyle.TEXT_MAIN),
                ("SO", p.record.strikeouts_pitched, VisualStyle.COLOR_HIT),
                ("STM", int(st.current_pitcher_stamina()), VisualStyle.COLOR_BALL)
            ])
        if b:
            self.batter_card.update_player(b, f"#{b.uniform_number} {b.position.value[:2]}", [
                ("AVG", f"{b.record.batting_average:.3f}", VisualStyle.TEXT_MAIN),
                ("HR", b.record.home_runs, VisualStyle.COLOR_STRIKE),
                ("RBI", b.record.rbis, VisualStyle.COLOR_OUT)
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
        self.btn_skip.setEnabled(False)
        self.live_engine.finalize_game_stats(self.date_str)
        self._log("=== GAME SET ===", True)
        res = {
            "home_team": self.live_engine.home_team,
            "away_team": self.live_engine.away_team,
            "home_score": self.live_engine.state.home_score,
            "away_score": self.live_engine.state.away_score,
            "winner": self.live_engine.get_winner()
        }
        self.game_finished.emit(res)

    def _log(self, text, highlight=False):
        l = QLabel(text)
        col = THEME.primary if highlight else THEME.text_secondary
        l.setStyleSheet(f"color: {col}; font-size: 11px; margin-bottom: 2px;")
        self.log_layout.insertWidget(0, l)