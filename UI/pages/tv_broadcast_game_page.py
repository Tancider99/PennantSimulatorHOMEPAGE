# -*- coding: utf-8 -*-
"""
Pennant Simulator 2027 - TV Broadcast Game Page
MLB The Show風のTV放送スタイル試合画面 - 高品質版
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton,
    QFrame, QSizePolicy, QScrollArea, QComboBox, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QTimer, QPointF, QRectF, QSize
from PySide6.QtGui import (
    QColor, QPainter, QPen, QFont, QPainterPath, QPixmap,
    QLinearGradient, QRadialGradient, QPolygonF, QBrush, QFontMetrics,
    QConicalGradient
)

import sys
import os
import math
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from live_game_engine import PitchData, BattedBallData, LiveGameEngine
from models import Player, Position


# ========================================
# Colors & Style Constants (MLB The Show Style)
# ========================================
class C:
    """Color constants for TV broadcast style"""
    # Main backgrounds
    BG_DARK = QColor("#050a14")
    BG_PANEL = QColor("#0a1528")
    BG_HEADER = QColor("#0f2040")
    BG_ROW_ODD = QColor("#0a1422")
    BG_ROW_EVEN = QColor("#0c1830")
    BG_SELECTED = QColor("#1a4590")

    # Team colors
    TEAM_BLUE = QColor("#003087")
    TEAM_RED = QColor("#c41e3a")
    TEAM_NAVY = QColor("#0c2340")
    TEAM_TEAL = QColor("#005c5c")
    TEAM_WHITE_SOX = QColor("#27251f")
    TEAM_MARINERS = QColor("#0c2c56")

    # Text
    WHITE = QColor("#ffffff")
    GRAY = QColor("#8899aa")
    LIGHT_GRAY = QColor("#b0c0d0")
    GOLD = QColor("#ffd700")
    YELLOW = QColor("#ffff00")
    CYAN = QColor("#00ddff")

    # Status colors
    BALL_GREEN = QColor("#00cc66")
    STRIKE_YELLOW = QColor("#ffcc00")
    OUT_RED = QColor("#ff3333")

    # Rating colors
    RATING_HIGH = QColor("#ff4444")
    RATING_MID_HIGH = QColor("#ff8800")
    RATING_MID = QColor("#ffcc00")
    RATING_LOW = QColor("#4488ff")

    # Scoreboard colors
    SCORE_BG = QColor("#1a2a4a")
    SCORE_BORDER = QColor("#3a6090")

    @staticmethod
    def rating_color(value: int) -> QColor:
        if value >= 80:
            return C.RATING_HIGH
        elif value >= 65:
            return C.RATING_MID_HIGH
        elif value >= 50:
            return C.RATING_MID
        else:
            return C.RATING_LOW


# ========================================
# Top Scoreboard Widget (High Quality)
# ========================================
class TopScoreboard(QWidget):
    """MLB The Show style top scoreboard with full innings display"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(115)

        # Data
        self.stadium_name = "STADIUM"
        self.away_abbr = "AWAY"
        self.home_abbr = "HOME"
        self.away_logo_color = C.TEAM_NAVY
        self.home_logo_color = C.TEAM_TEAL
        self.away_runs_by_inning = [None] * 9
        self.home_runs_by_inning = [None] * 9
        self.away_total = {"R": 0, "H": 0, "E": 0}
        self.home_total = {"R": 0, "H": 0, "E": 0}
        self.current_inning = 1
        self.is_top = True
        self.balls = 0
        self.strikes = 0
        self.outs = 0
        self.last_pitch_type = "FB"
        self.last_pitch_speed = 0
        self.game_time = "0:00"

    def set_teams(self, away: str, home: str, stadium: str = "STADIUM"):
        self.away_abbr = away[:3].upper()
        self.home_abbr = home[:3].upper()
        self.stadium_name = stadium.upper()
        self.update()

    def set_inning(self, inning: int, is_top: bool):
        self.current_inning = inning
        self.is_top = is_top
        self.update()

    def set_count(self, balls: int, strikes: int, outs: int):
        self.balls = balls
        self.strikes = strikes
        self.outs = outs
        self.update()

    def set_score(self, away_r: int, home_r: int, away_h: int = 0, home_h: int = 0, away_e: int = 0, home_e: int = 0):
        self.away_total = {"R": away_r, "H": away_h, "E": away_e}
        self.home_total = {"R": home_r, "H": home_h, "E": home_e}
        self.update()

    def set_pitch_info(self, pitch_type: str, speed: int):
        self.last_pitch_type = pitch_type
        self.last_pitch_speed = speed
        self.update()

    def set_inning_score(self, inning: int, is_away: bool, runs: int):
        if 1 <= inning <= 9:
            if is_away:
                self.away_runs_by_inning[inning - 1] = runs
            else:
                self.home_runs_by_inning[inning - 1] = runs
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()

        # Main background gradient
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor("#1a2a4a"))
        grad.setColorAt(0.5, QColor("#0f1a30"))
        grad.setColorAt(1, QColor("#0a1220"))
        p.fillRect(0, 0, w, h, grad)

        # Top highlight line
        p.setPen(QPen(QColor("#4080c0"), 1))
        p.drawLine(0, 1, w, 1)

        # Bottom border
        p.setPen(QPen(QColor("#2a4a6a"), 2))
        p.drawLine(0, h - 1, w, h - 1)

        # Draw sections
        self._draw_scoreboard(p, 8, 8, 560, h - 16)
        self._draw_count_display(p, 578, 8, 160, h - 16)
        self._draw_controls_hint(p, 748, 8, w - 758, h - 16)

    def _draw_scoreboard(self, p: QPainter, x: int, y: int, w: int, h: int):
        """Draw main scoreboard with innings"""
        # Stadium name box
        p.fillRect(x, y, 70, 18, QColor("#0a1528"))
        p.setPen(C.LIGHT_GRAY)
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(x + 4, y + 13, self.stadium_name[:12])

        # Time display
        p.setPen(C.GRAY)
        p.setFont(QFont("Consolas", 8))
        # p.drawText(x + 150, y + 13, self.game_time)

        # Innings header
        inn_start_x = x + 75
        inn_width = 30
        p.fillRect(inn_start_x - 2, y, 9 * inn_width + 4, 18, QColor("#0f1830"))
        p.setPen(C.GRAY)
        p.setFont(QFont("Consolas", 10, QFont.Bold))
        for i in range(1, 10):
            ix = inn_start_x + (i - 1) * inn_width
            # Highlight current inning header
            if i == self.current_inning:
                p.fillRect(int(ix), y, inn_width - 2, 18, QColor("#2050a0"))
            p.drawText(QRectF(ix, y, inn_width, 18), Qt.AlignCenter, str(i))

        # R H E headers
        rhe_x = inn_start_x + 9 * inn_width + 15
        p.fillRect(int(rhe_x) - 5, y, 100, 18, QColor("#0f1830"))
        for i, label in enumerate(["R", "H", "E"]):
            p.setPen(C.LIGHT_GRAY)
            p.drawText(QRectF(rhe_x + i * 32, y, 30, 18), Qt.AlignCenter, label)

        # Away team row
        away_y = y + 22
        # Team name background with gradient
        away_grad = QLinearGradient(x, 0, x + 72, 0)
        away_grad.setColorAt(0, self.away_logo_color)
        away_grad.setColorAt(1, self.away_logo_color.darker(150))
        p.fillRect(x, away_y, 72, 32, away_grad)

        # Team logo placeholder (circle with first letter)
        p.setBrush(QColor(255, 255, 255, 40))
        p.setPen(Qt.NoPen)
        p.drawEllipse(x + 4, away_y + 4, 24, 24)
        p.setPen(C.WHITE)
        p.setFont(QFont("Arial Black", 12))
        p.drawText(QRectF(x + 4, away_y + 4, 24, 24), Qt.AlignCenter, self.away_abbr[0])

        # Team abbreviation with arrow indicator
        arrow = "▲" if self.is_top else ""
        p.setPen(C.WHITE if self.is_top else C.GRAY)
        p.setFont(QFont("Segoe UI", 14, QFont.Bold))
        p.drawText(x + 32, away_y + 22, f"{self.away_abbr}")
        if self.is_top:
            p.setFont(QFont("Segoe UI", 10))
            p.drawText(x + 62, away_y + 12, arrow)

        # Away innings scores
        p.setFont(QFont("Consolas", 12, QFont.Bold))
        for i in range(9):
            ix = inn_start_x + i * inn_width
            # Background
            is_current = (self.current_inning == i + 1 and self.is_top)
            bg_col = QColor("#1a4080") if is_current else (QColor("#0c1628") if i % 2 == 0 else QColor("#0a1220"))
            p.fillRect(int(ix), away_y, inn_width - 2, 32, bg_col)

            # Score
            score = self.away_runs_by_inning[i]
            if score is not None:
                p.setPen(C.WHITE)
                p.drawText(QRectF(ix, away_y, inn_width - 2, 32), Qt.AlignCenter, str(score))

        # Away R/H/E totals
        p.fillRect(int(rhe_x) - 5, away_y, 100, 32, QColor("#0a1528"))
        p.setPen(C.WHITE)
        p.setFont(QFont("Consolas", 14, QFont.Bold))
        for i, key in enumerate(["R", "H", "E"]):
            p.drawText(QRectF(rhe_x + i * 32, away_y, 30, 32), Qt.AlignCenter, str(self.away_total[key]))

        # Home team row
        home_y = away_y + 36
        home_grad = QLinearGradient(x, 0, x + 72, 0)
        home_grad.setColorAt(0, self.home_logo_color)
        home_grad.setColorAt(1, self.home_logo_color.darker(150))
        p.fillRect(x, home_y, 72, 32, home_grad)

        # Home team logo
        p.setBrush(QColor(255, 255, 255, 40))
        p.setPen(Qt.NoPen)
        p.drawEllipse(x + 4, home_y + 4, 24, 24)
        p.setPen(C.WHITE)
        p.setFont(QFont("Arial Black", 12))
        p.drawText(QRectF(x + 4, home_y + 4, 24, 24), Qt.AlignCenter, self.home_abbr[0])

        arrow = "▼" if not self.is_top else ""
        p.setPen(C.WHITE if not self.is_top else C.GRAY)
        p.setFont(QFont("Segoe UI", 14, QFont.Bold))
        p.drawText(x + 32, home_y + 22, f"{self.home_abbr}")
        if not self.is_top:
            p.setFont(QFont("Segoe UI", 10))
            p.drawText(x + 62, home_y + 12, arrow)

        # Home innings scores
        p.setFont(QFont("Consolas", 12, QFont.Bold))
        for i in range(9):
            ix = inn_start_x + i * inn_width
            is_current = (self.current_inning == i + 1 and not self.is_top)
            bg_col = QColor("#1a4080") if is_current else (QColor("#0c1628") if i % 2 == 0 else QColor("#0a1220"))
            p.fillRect(int(ix), home_y, inn_width - 2, 32, bg_col)

            score = self.home_runs_by_inning[i]
            if score is not None:
                p.setPen(C.WHITE)
                p.drawText(QRectF(ix, home_y, inn_width - 2, 32), Qt.AlignCenter, str(score))

        # Home R/H/E totals
        p.fillRect(int(rhe_x) - 5, home_y, 100, 32, QColor("#0a1528"))
        p.setPen(C.WHITE)
        p.setFont(QFont("Consolas", 14, QFont.Bold))
        for i, key in enumerate(["R", "H", "E"]):
            p.drawText(QRectF(rhe_x + i * 32, home_y, 30, 32), Qt.AlignCenter, str(self.home_total[key]))

    def _draw_count_display(self, p: QPainter, x: int, y: int, w: int, h: int):
        """Draw Ball-Strike-Out count and pitch info"""
        # Background panel
        p.fillRect(x, y, w, h, QColor(0, 0, 0, 180))
        p.setPen(QPen(QColor("#3060a0"), 1))
        p.drawRect(x, y, w, h)

        # Inning indicator at top
        p.fillRect(x + 2, y + 2, w - 4, 22, QColor("#0a2040"))
        p.setPen(C.WHITE)
        p.setFont(QFont("Consolas", 11, QFont.Bold))
        inn_arrow = "▲" if self.is_top else "▼"
        p.drawText(QRectF(x, y + 2, w, 22), Qt.AlignCenter, f"{inn_arrow} {self.current_inning}")

        # BSO indicators with labels
        bso_y = y + 30
        indicator_x = x + 12

        # Ball row
        p.setPen(C.LIGHT_GRAY)
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(indicator_x - 2, bso_y + 11, "B")
        p.setPen(Qt.NoPen)
        for i in range(4):
            if i < self.balls:
                # Lit indicator with glow
                glow = QRadialGradient(QPointF(indicator_x + 18 + i * 22 + 7, bso_y + 7), 12)
                glow.setColorAt(0, QColor(0, 255, 100, 100))
                glow.setColorAt(1, QColor(0, 255, 100, 0))
                p.setBrush(glow)
                p.drawEllipse(indicator_x + 18 + i * 22 - 5, bso_y - 5, 24, 24)

                p.setBrush(C.BALL_GREEN)
            else:
                p.setBrush(QColor(30, 40, 50))
            p.drawEllipse(indicator_x + 18 + i * 22, bso_y, 14, 14)

        # Strike row
        bso_y += 22
        p.setPen(C.LIGHT_GRAY)
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(indicator_x - 2, bso_y + 11, "S")
        p.setPen(Qt.NoPen)
        for i in range(3):
            if i < self.strikes:
                glow = QRadialGradient(QPointF(indicator_x + 18 + i * 22 + 7, bso_y + 7), 12)
                glow.setColorAt(0, QColor(255, 200, 0, 100))
                glow.setColorAt(1, QColor(255, 200, 0, 0))
                p.setBrush(glow)
                p.drawEllipse(indicator_x + 18 + i * 22 - 5, bso_y - 5, 24, 24)

                p.setBrush(C.STRIKE_YELLOW)
            else:
                p.setBrush(QColor(30, 40, 50))
            p.drawEllipse(indicator_x + 18 + i * 22, bso_y, 14, 14)

        # Out row
        bso_y += 22
        p.setPen(C.LIGHT_GRAY)
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(indicator_x - 2, bso_y + 11, "O")
        p.setPen(Qt.NoPen)
        for i in range(3):
            if i < self.outs:
                glow = QRadialGradient(QPointF(indicator_x + 18 + i * 22 + 7, bso_y + 7), 12)
                glow.setColorAt(0, QColor(255, 50, 50, 100))
                glow.setColorAt(1, QColor(255, 50, 50, 0))
                p.setBrush(glow)
                p.drawEllipse(indicator_x + 18 + i * 22 - 5, bso_y - 5, 24, 24)

                p.setBrush(C.OUT_RED)
            else:
                p.setBrush(QColor(30, 40, 50))
            p.drawEllipse(indicator_x + 18 + i * 22, bso_y, 14, 14)

        # Pitch info at bottom
        p.fillRect(x + 2, y + h - 22, w - 4, 20, QColor("#0a2040"))
        p.setPen(C.WHITE)
        p.setFont(QFont("Consolas", 10, QFont.Bold))
        if self.last_pitch_speed > 0:
            pitch_text = f"PITCH: {self.last_pitch_type} {self.last_pitch_speed} MPH"
        else:
            pitch_text = "PITCH: --"
        p.drawText(QRectF(x + 2, y + h - 22, w - 4, 20), Qt.AlignCenter, pitch_text)

    def _draw_controls_hint(self, p: QPainter, x: int, y: int, w: int, h: int):
        """Draw control hints area"""
        # Title
        p.fillRect(x, y, w, 18, QColor("#1a3050"))
        p.setPen(C.WHITE)
        p.setFont(QFont("Segoe UI", 8, QFont.Bold))
        p.drawText(x + 8, y + 13, "CONTROLS")

        controls = [
            ("1", "PITCH TO BATTER!"),
            ("2", "PITCH AROUND"),
            ("3", "PITCH TO CONTACT"),
            ("4", "INTENTIONAL WALK"),
        ]

        ctrl_y = y + 24
        p.setFont(QFont("Segoe UI", 7))

        for i, (key, label) in enumerate(controls):
            if i >= 4:
                break
            # Key box
            p.fillRect(x + 5, ctrl_y + i * 20, 16, 16, QColor("#2a5a9a"))
            p.setPen(QPen(QColor("#4080c0"), 1))
            p.drawRect(x + 5, ctrl_y + i * 20, 16, 16)
            p.setPen(C.WHITE)
            p.setFont(QFont("Consolas", 9, QFont.Bold))
            p.drawText(QRectF(x + 5, ctrl_y + i * 20, 16, 16), Qt.AlignCenter, key)

            # Label
            p.setPen(C.LIGHT_GRAY)
            p.setFont(QFont("Segoe UI", 7))
            p.drawText(x + 26, ctrl_y + i * 20 + 12, label[:18])


# ========================================
# Team Lineup Panel (Enhanced)
# ========================================
class TeamLineupPanel(QWidget):
    """Team lineup panel with player stats"""

    player_clicked = Signal(object)

    def __init__(self, is_home: bool = False, parent=None):
        super().__init__(parent)
        self.is_home = is_home
        self.setFixedWidth(265)

        self.team_name = "TEAM"
        self.team_color = C.TEAM_BLUE
        self.lineup = []
        self.bullpen = []
        self.current_batter_idx = -1

    def set_team(self, name: str, color: QColor = None):
        self.team_name = name.upper()
        if color:
            self.team_color = color
        self.update()

    def set_lineup(self, lineup: list):
        self.lineup = lineup
        self.update()

    def set_current_batter(self, idx: int):
        self.current_batter_idx = idx
        self.update()

    def set_bullpen(self, pitchers: list):
        self.bullpen = pitchers
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()

        # Background with gradient
        bg_grad = QLinearGradient(0, 0, 0, h)
        bg_grad.setColorAt(0, C.BG_DARK)
        bg_grad.setColorAt(1, QColor("#030810"))
        p.fillRect(0, 0, w, h, bg_grad)

        # Team header with gradient
        header_h = 30
        header_grad = QLinearGradient(0, 0, w, 0)
        header_grad.setColorAt(0, self.team_color)
        header_grad.setColorAt(0.7, self.team_color.darker(130))
        header_grad.setColorAt(1, self.team_color.darker(180))
        p.fillRect(0, 0, w, header_h, header_grad)

        # Team name with icon placeholder
        p.setBrush(QColor(255, 255, 255, 50))
        p.setPen(Qt.NoPen)
        p.drawEllipse(6, 4, 22, 22)
        p.setPen(C.WHITE)
        p.setFont(QFont("Arial Black", 10))
        p.drawText(QRectF(6, 4, 22, 22), Qt.AlignCenter, self.team_name[0] if self.team_name else "T")

        p.setFont(QFont("Segoe UI", 11, QFont.Bold))
        p.drawText(34, 21, self.team_name)

        # Column headers
        col_y = header_h + 2
        p.fillRect(0, col_y, w, 18, C.BG_HEADER)
        p.setPen(C.GRAY)
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))

        cols = [("#", 18), ("-", 14), ("PLAYER", 78), ("POS", 28), ("AVG", 34), ("HR", 24), ("RBI", 26), ("SB", 24)]
        col_x = 4
        for label, cw in cols:
            p.drawText(QRectF(col_x, col_y, cw, 18), Qt.AlignCenter, label)
            col_x += cw

        # Player rows
        row_h = 21
        row_y = col_y + 20

        for i, (player, pos_str) in enumerate(self.lineup[:9]):
            is_current = (i == self.current_batter_idx)

            # Row background
            if is_current:
                # Highlighted current batter with glow effect
                glow_grad = QLinearGradient(0, row_y, 0, row_y + row_h)
                glow_grad.setColorAt(0, QColor("#1a5090"))
                glow_grad.setColorAt(0.5, QColor("#2060b0"))
                glow_grad.setColorAt(1, QColor("#1a5090"))
                p.fillRect(0, row_y, w, row_h, glow_grad)
                # Yellow left indicator
                p.fillRect(0, row_y, 3, row_h, C.YELLOW)
            else:
                bg = C.BG_ROW_EVEN if i % 2 == 0 else C.BG_ROW_ODD
                p.fillRect(0, row_y, w, row_h, bg)

            col_x = 4
            p.setFont(QFont("Consolas", 9))

            # Order number
            p.setPen(C.WHITE if is_current else C.LIGHT_GRAY)
            p.drawText(QRectF(col_x, row_y, 18, row_h), Qt.AlignCenter, str(i + 1))
            col_x += 18

            # Handedness
            if player:
                bats = getattr(player, 'bats', '右')
                bats_str = 'L' if bats == '左' else ('S' if bats == '両' else 'R')
            else:
                bats_str = 'R'
            p.setPen(C.GRAY)
            p.drawText(QRectF(col_x, row_y, 14, row_h), Qt.AlignCenter, bats_str)
            col_x += 14

            # Player name
            p.setPen(C.WHITE if is_current else C.LIGHT_GRAY)
            name = self._shorten_name(player.name) if player else ""
            p.drawText(QRectF(col_x + 2, row_y, 76, row_h), Qt.AlignLeft | Qt.AlignVCenter, name)
            col_x += 78

            # Position
            p.setPen(C.CYAN if is_current else C.GRAY)
            p.drawText(QRectF(col_x, row_y, 28, row_h), Qt.AlignCenter, pos_str)
            col_x += 28

            # Stats
            if player and hasattr(player, 'record'):
                avg_val = player.record.batting_average
                avg = f".{int(avg_val * 1000):03d}"[1:] if avg_val > 0 else ".000"
                hr = str(player.record.home_runs)
                rbi = str(player.record.rbi)
                sb = str(player.record.stolen_bases)
            else:
                avg, hr, rbi, sb = ".000", "0", "0", "0"

            p.setPen(C.WHITE)
            p.setFont(QFont("Consolas", 8))
            p.drawText(QRectF(col_x, row_y, 34, row_h), Qt.AlignCenter, avg)
            col_x += 34
            p.drawText(QRectF(col_x, row_y, 24, row_h), Qt.AlignCenter, hr)
            col_x += 24
            p.drawText(QRectF(col_x, row_y, 26, row_h), Qt.AlignCenter, rbi)
            col_x += 26
            p.drawText(QRectF(col_x, row_y, 24, row_h), Qt.AlignCenter, sb)

            row_y += row_h

        # Bullpen section
        bullpen_y = row_y + 8
        p.fillRect(0, bullpen_y, w, 22, C.BG_HEADER)
        p.setPen(C.WHITE)
        p.setFont(QFont("Segoe UI", 9, QFont.Bold))
        p.drawText(10, bullpen_y + 16, "BULLPEN")

        # Bullpen ready indicator
        bp_y = bullpen_y + 26
        p.setBrush(C.BALL_GREEN)
        p.setPen(Qt.NoPen)
        p.drawEllipse(14, bp_y + 4, 10, 10)
        p.setPen(C.LIGHT_GRAY)
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(30, bp_y + 13, "Ready")

    def _shorten_name(self, name: str) -> str:
        if len(name) <= 9:
            return name
        parts = name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}. {parts[-1][:7]}"
        return name[:9]


# ========================================
# Pitcher Stats Panel (Enhanced)
# ========================================
class PitcherStatsPanel(QWidget):
    """Bottom left pitcher stats panel with full stats"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(145)

        self.pitcher = None
        self.throws = "R"
        self.name = "PITCHER"
        self.season_stats = {"W-L": "0-0", "IP": "0.0", "H": "0", "ER": "0", "BB": "0", "K": "0", "ERA": "0.00"}
        self.today_stats = {"IP": "0.0", "H": "0", "ER": "0", "BB": "0", "K": "0"}
        self.ratings = {"Overall": 50, "STU": 50, "MOV": 50, "CON": 50}
        self.stamina = 100
        self.pitches = 0
        self.velo = "90-92"
        self.pitch_type = "FB"

    def set_pitcher(self, player: Player):
        self.pitcher = player
        if player:
            self.name = player.name
            self.throws = "L" if getattr(player, 'throws', '右') == "左" else "R"

            if hasattr(player, 'stats'):
                self.ratings["Overall"] = int(player.stats.overall_pitching())
                self.ratings["STU"] = int(getattr(player.stats, 'stuff', 50))
                self.ratings["MOV"] = int(getattr(player.stats, 'movement', 50))
                self.ratings["CON"] = int(getattr(player.stats, 'control', 50))

            if hasattr(player, 'record'):
                rec = player.record
                self.season_stats["W-L"] = f"{rec.wins}-{rec.losses}"
                self.season_stats["IP"] = f"{rec.innings_pitched:.1f}"
                self.season_stats["ERA"] = f"{rec.era:.2f}"
                self.season_stats["K"] = str(rec.strikeouts)
                self.season_stats["BB"] = str(rec.walks_allowed)
                self.season_stats["H"] = str(rec.hits_allowed)
                self.season_stats["ER"] = str(rec.earned_runs)

        self.update()

    def set_game_stats(self, ip: float, h: int, er: int, bb: int, k: int, pitches: int, stamina: float):
        self.today_stats["IP"] = f"{ip:.1f}"
        self.today_stats["H"] = str(h)
        self.today_stats["ER"] = str(er)
        self.today_stats["BB"] = str(bb)
        self.today_stats["K"] = str(k)
        self.pitches = pitches
        self.stamina = int(stamina)
        self.update()

    def set_pitch_info(self, velo_range: str, pitch_type: str):
        self.velo = velo_range
        self.pitch_type = pitch_type
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()

        # Background
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor("#0c1830"))
        grad.setColorAt(1, QColor("#050a14"))
        p.fillRect(0, 0, w, h, grad)

        # Top accent line (red for pitcher)
        p.fillRect(0, 0, w, 3, QColor("#cc3344"))

        # Header
        p.fillRect(5, 6, w - 10, 22, QColor("#0a1528"))
        p.setPen(C.WHITE)
        p.setFont(QFont("Segoe UI", 10, QFont.Bold))
        header_text = f"PITCHING: {self.throws}HP {self.name.upper()}"
        p.drawText(12, 22, header_text[:35])

        # Stats table
        stats_y = 32
        p.fillRect(5, stats_y, w - 10, 16, QColor("#0f1a30"))
        p.setPen(C.GRAY)
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))

        stat_cols = ["STATS", "W-L", "IP", "H", "ER", "BB", "K", "ERA", "Stamina"]
        col_widths = [42, 34, 38, 24, 24, 24, 24, 34, 50]
        col_x = 8
        for label, cw in zip(stat_cols, col_widths):
            p.drawText(QRectF(col_x, stats_y, cw, 16), Qt.AlignCenter, label)
            col_x += cw

        # Season row
        stats_y += 18
        p.fillRect(5, stats_y, w - 10, 16, QColor("#0a1422"))
        p.setPen(C.WHITE)
        p.setFont(QFont("Consolas", 8))

        col_x = 8
        p.drawText(QRectF(col_x, stats_y, 42, 16), Qt.AlignLeft | Qt.AlignVCenter, " Season")
        col_x += 42

        season_vals = [self.season_stats["W-L"], self.season_stats["IP"], self.season_stats["H"],
                       self.season_stats["ER"], self.season_stats["BB"], self.season_stats["K"],
                       self.season_stats["ERA"], str(self.stamina)]

        for val, cw in zip(season_vals, col_widths[1:]):
            p.drawText(QRectF(col_x, stats_y, cw, 16), Qt.AlignCenter, val)
            col_x += cw

        # Today row
        stats_y += 18
        p.fillRect(5, stats_y, w - 10, 16, QColor("#0c1628"))
        col_x = 8
        p.drawText(QRectF(col_x, stats_y, 42, 16), Qt.AlignLeft | Qt.AlignVCenter, " Today")
        col_x += 42

        today_vals = ["", self.today_stats["IP"], self.today_stats["H"],
                      self.today_stats["ER"], self.today_stats["BB"], self.today_stats["K"], "", ""]

        for val, cw in zip(today_vals, col_widths[1:]):
            p.drawText(QRectF(col_x, stats_y, cw, 16), Qt.AlignCenter, val)
            col_x += cw

        # Ratings section
        ratings_y = stats_y + 22
        p.setPen(C.GRAY)
        p.setFont(QFont("Segoe UI", 7, QFont.Bold))
        p.drawText(8, ratings_y + 12, "RATINGS")

        rating_labels = ["Overall", "STU", "MOV", "CON"]
        rating_x = 55
        for label in rating_labels:
            val = self.ratings.get(label, 50)
            box_col = C.rating_color(val)

            # Rating box with border
            p.fillRect(rating_x, ratings_y, 32, 22, box_col)
            p.setPen(QPen(box_col.lighter(130), 1))
            p.drawRect(rating_x, ratings_y, 32, 22)

            p.setPen(C.WHITE)
            p.setFont(QFont("Consolas", 11, QFont.Bold))
            p.drawText(QRectF(rating_x, ratings_y, 32, 22), Qt.AlignCenter, str(val))

            p.setPen(C.GRAY)
            p.setFont(QFont("Segoe UI", 6))
            p.drawText(QRectF(rating_x, ratings_y + 22, 32, 12), Qt.AlignCenter, label)

            rating_x += 40

        # Velo and pitch info
        p.setPen(C.WHITE)
        p.setFont(QFont("Consolas", 9))
        p.drawText(rating_x + 15, ratings_y + 12, f"VELO")
        p.setPen(C.CYAN)
        p.drawText(rating_x + 50, ratings_y + 12, f"{self.velo} Mph")

        p.setPen(C.WHITE)
        p.drawText(rating_x + 15, ratings_y + 28, f"Pitches")
        p.setPen(C.GOLD)
        p.drawText(rating_x + 65, ratings_y + 28, str(self.pitches))


# ========================================
# Batter Stats Panel (Enhanced)
# ========================================
class BatterStatsPanel(QWidget):
    """Bottom right batter stats panel with full stats"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(145)

        self.batter = None
        self.bats = "R"
        self.name = "BATTER"
        self.position = "DH"
        self.season_stats = {"AB": "0", "H": "0", "HR": "0", "RBI": "0", "AVG": ".000", "OBP": ".000", "OPS": ".000"}
        self.today_stats = {"AB": "0", "H": "0", "HR": "0", "RBI": "0"}
        self.ratings = {"Overall": 50, "CON": 50, "POW": 50, "EYE": 50, "SPE": 50}
        self.bunt_hit = 50
        self.sac_bunt = 50
        self.vs_lhp = 50

    def set_batter(self, player: Player, position_str: str = ""):
        self.batter = player
        if player:
            self.name = player.name
            self.position = position_str or self._get_pos_abbr(player.position)
            bats = getattr(player, 'bats', '右')
            self.bats = "L" if bats == "左" else ("S" if bats == "両" else "R")

            if hasattr(player, 'stats'):
                self.ratings["Overall"] = int(player.stats.overall_batting())
                self.ratings["CON"] = int(getattr(player.stats, 'contact', 50))
                self.ratings["POW"] = int(getattr(player.stats, 'power', 50))
                self.ratings["EYE"] = int(getattr(player.stats, 'eye', 50))
                self.ratings["SPE"] = int(getattr(player.stats, 'speed', 50))
                self.bunt_hit = int(getattr(player.stats, 'bunt_hit', 50))
                self.sac_bunt = int(getattr(player.stats, 'bunt_sac', 50))
                self.vs_lhp = int(getattr(player.stats, 'vs_left_pitcher', 50))

            if hasattr(player, 'record'):
                rec = player.record
                self.season_stats["AB"] = str(rec.at_bats)
                self.season_stats["H"] = str(rec.hits)
                self.season_stats["HR"] = str(rec.home_runs)
                self.season_stats["RBI"] = str(rec.rbi)
                avg = rec.batting_average
                self.season_stats["AVG"] = f".{int(avg * 1000):03d}"[1:] if avg > 0 else ".000"
                obp = rec.on_base_percentage
                self.season_stats["OBP"] = f".{int(obp * 1000):03d}"[1:] if obp > 0 else ".000"
                ops = obp + rec.slugging_percentage
                self.season_stats["OPS"] = f".{int(ops * 1000):03d}"[1:] if ops > 0 else ".000"

        self.update()

    def _get_pos_abbr(self, pos: Position) -> str:
        pos_map = {
            Position.PITCHER: "P", Position.CATCHER: "C",
            Position.FIRST: "1B", Position.SECOND: "2B",
            Position.THIRD: "3B", Position.SHORTSTOP: "SS",
            Position.LEFT: "LF", Position.CENTER: "CF",
            Position.RIGHT: "RF", Position.DH: "DH"
        }
        return pos_map.get(pos, "DH")

    def set_game_stats(self, ab: int, h: int, hr: int, rbi: int):
        self.today_stats["AB"] = str(ab)
        self.today_stats["H"] = str(h)
        self.today_stats["HR"] = str(hr)
        self.today_stats["RBI"] = str(rbi)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        w, h = self.width(), self.height()

        # Background
        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0, QColor("#0c1830"))
        grad.setColorAt(1, QColor("#050a14"))
        p.fillRect(0, 0, w, h, grad)

        # Top accent line (teal for batter)
        p.fillRect(0, 0, w, 3, QColor("#00aa99"))

        # Header
        p.fillRect(5, 6, w - 10, 22, QColor("#0a1528"))
        p.setPen(C.WHITE)
        p.setFont(QFont("Segoe UI", 10, QFont.Bold))
        header_text = f"AT BAT: {self.bats}HB {self.name.upper()}, {self.position}"
        p.drawText(12, 22, header_text[:40])

        # Left side: Situational ratings
        sit_x = 8
        sit_y = 34

        situational = [("Bunt/Hit", self.bunt_hit), ("Sac Bunt", self.sac_bunt), ("Vs LHP", self.vs_lhp)]

        for label, val in situational:
            p.setPen(C.GRAY)
            p.setFont(QFont("Segoe UI", 7))
            p.drawText(sit_x, sit_y + 10, label)

            box_col = C.rating_color(val)
            p.fillRect(sit_x + 50, sit_y, 26, 14, box_col)
            p.setPen(C.WHITE)
            p.setFont(QFont("Consolas", 9, QFont.Bold))
            p.drawText(QRectF(sit_x + 50, sit_y, 26, 14), Qt.AlignCenter, str(val))

            sit_y += 18

        # Stats table (right side)
        stats_x = 95
        stats_y = 34

        p.fillRect(stats_x, stats_y, w - stats_x - 8, 14, QColor("#0f1a30"))
        p.setPen(C.GRAY)
        p.setFont(QFont("Segoe UI", 6, QFont.Bold))

        stat_cols = ["STATS", "AB", "H", "HR", "RBI", "AVG", "OBP", "OPS"]
        col_widths = [38, 28, 24, 24, 28, 32, 32, 38]
        col_x = stats_x + 4
        for label, cw in zip(stat_cols, col_widths):
            p.drawText(QRectF(col_x, stats_y, cw, 14), Qt.AlignCenter, label)
            col_x += cw

        # Season row
        stats_y += 16
        p.fillRect(stats_x, stats_y, w - stats_x - 8, 14, QColor("#0a1422"))
        p.setPen(C.WHITE)
        p.setFont(QFont("Consolas", 8))

        col_x = stats_x + 4
        p.drawText(QRectF(col_x, stats_y, 38, 14), Qt.AlignLeft | Qt.AlignVCenter, " Season")
        col_x += 38

        season_vals = [self.season_stats["AB"], self.season_stats["H"], self.season_stats["HR"],
                       self.season_stats["RBI"], self.season_stats["AVG"], self.season_stats["OBP"],
                       self.season_stats["OPS"]]

        for val, cw in zip(season_vals, col_widths[1:]):
            p.drawText(QRectF(col_x, stats_y, cw, 14), Qt.AlignCenter, val)
            col_x += cw

        # Today row
        stats_y += 16
        p.fillRect(stats_x, stats_y, w - stats_x - 8, 14, QColor("#0c1628"))
        col_x = stats_x + 4
        p.drawText(QRectF(col_x, stats_y, 38, 14), Qt.AlignLeft | Qt.AlignVCenter, " Today")
        col_x += 38

        today_vals = [self.today_stats["AB"], self.today_stats["H"], self.today_stats["HR"],
                      self.today_stats["RBI"], "", "", ""]

        for val, cw in zip(today_vals, col_widths[1:]):
            p.drawText(QRectF(col_x, stats_y, cw, 14), Qt.AlignCenter, val)
            col_x += cw

        # Ratings section
        ratings_y = stats_y + 20
        p.setPen(C.GRAY)
        p.setFont(QFont("Segoe UI", 6, QFont.Bold))
        p.drawText(stats_x + 4, ratings_y + 10, "RATINGS")

        rating_labels = ["Overall", "CON", "POW", "EYE", "SPE"]
        rating_x = stats_x + 50
        for label in rating_labels:
            val = self.ratings.get(label, 50)
            box_col = C.rating_color(val)

            p.fillRect(rating_x, ratings_y, 28, 18, box_col)
            p.setPen(QPen(box_col.lighter(130), 1))
            p.drawRect(rating_x, ratings_y, 28, 18)

            p.setPen(C.WHITE)
            p.setFont(QFont("Consolas", 10, QFont.Bold))
            p.drawText(QRectF(rating_x, ratings_y, 28, 18), Qt.AlignCenter, str(val))

            p.setPen(C.GRAY)
            p.setFont(QFont("Segoe UI", 5))
            p.drawText(QRectF(rating_x, ratings_y + 18, 28, 10), Qt.AlignCenter, label)

            rating_x += 34


# ========================================
# Field View Widget (3D Stadium - Enhanced)
# ========================================
class FieldView(QWidget):
    """3D stadium field view widget with enhanced graphics - no camera switching"""

    done = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(600, 400)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._tick)

        self.phase = "idle"
        self.t = 0.0
        self.pitch: PitchData = None
        self.ball: BattedBallData = None
        self.result = ""
        self.runners = [False, False, False]
        self.is_homerun = False
        self.fireworks = []
        self.flash_alpha = 0.0
        self.result_display_time = 0  # Counter for result display duration

    def start_pitch(self, pitch: PitchData, result: str):
        self.pitch = pitch
        self.result = result
        self.ball = None
        self.phase = "pitch"
        self.t = 0.0
        self.result_display_time = 0
        self.timer.start()

    def start_hit(self, ball: BattedBallData, result: str):
        self.ball = ball
        self.result = result
        self.phase = "hit"
        self.t = 0.0
        self.result_display_time = 0
        self.is_homerun = "ホームラン" in result or "本塁打" in result
        if self.is_homerun:
            self.flash_alpha = 200
        self.timer.start()

    def set_runners(self, r: list):
        self.runners = r
        self.update()

    def reset(self):
        self.timer.stop()
        self.phase = "idle"
        self.pitch = None
        self.ball = None
        self.is_homerun = False
        self.fireworks = []
        self.flash_alpha = 0.0
        self.result_display_time = 0
        self.update()

    def _tick(self):
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - 12)

        if self.phase == "pitch":
            spd = 0.025 + (self.pitch.velocity / 5000 if self.pitch else 0)
            self.t += spd
            if self.t >= 1.0:
                self.t = 1.0
                # Show result for longer time
                self.result_display_time += 1
                if self.result_display_time >= 60:  # About 1 second at 60fps
                    self.timer.stop()
                    self.phase = "idle"
                    self.done.emit()

        elif self.phase == "hit":
            hang = self.ball.hang_time if self.ball else 2.0
            spd = 1.0 / max(35, hang * 55)  # Slower ball animation
            self.t += spd
            if self.t >= 1.0:
                self.t = 1.0
                # Show result for longer time
                self.result_display_time += 1
                if self.is_homerun:
                    if self.result_display_time >= 30:  # Start celebration after delay
                        self.phase = "celebration"
                        self._spawn_fireworks()
                        self.result_display_time = 0
                else:
                    if self.result_display_time >= 90:  # About 1.5 seconds for result display
                        self.timer.stop()
                        self.phase = "idle"
                        self.done.emit()

        elif self.phase == "celebration":
            self._update_fireworks()
            if random.random() < 0.12 and len(self.fireworks) < 60:
                self._spawn_firework()
            self.result_display_time += 1
            # Longer celebration
            if self.result_display_time >= 150 and len([f for f in self.fireworks if f['alpha'] > 0]) < 10:
                self.timer.stop()
                self.phase = "idle"
                self.done.emit()

        self.update()

    def _spawn_firework(self):
        w, h = self.width(), self.height()
        self.fireworks.append({
            'x': random.uniform(w * 0.15, w * 0.85),
            'y': random.uniform(h * 0.05, h * 0.35),
            'vx': random.uniform(-2.5, 2.5),
            'vy': random.uniform(-1.5, 1),
            'color': random.choice([QColor("#ff6688"), QColor("#ffdd44"), QColor("#ffffff"),
                                    QColor("#ff44aa"), QColor("#44ffaa")]),
            'size': random.uniform(4, 9),
            'alpha': 255
        })

    def _spawn_fireworks(self):
        for _ in range(25):
            self._spawn_firework()

    def _update_fireworks(self):
        for f in self.fireworks:
            f['x'] += f['vx']
            f['y'] += f['vy']
            f['vy'] += 0.06
            f['alpha'] = max(0, f['alpha'] - 4)
            f['size'] = max(1, f['size'] - 0.03)
        self.fireworks = [f for f in self.fireworks if f['alpha'] > 0]

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        w, h = self.width(), self.height()

        # Sky gradient (realistic)
        sky = QLinearGradient(0, 0, 0, h * 0.55)
        sky.setColorAt(0, QColor("#3a7cb8"))
        sky.setColorAt(0.3, QColor("#5aa0d0"))
        sky.setColorAt(0.6, QColor("#8cc8e8"))
        sky.setColorAt(1, QColor("#c0dce8"))
        p.fillRect(0, 0, w, int(h * 0.55), sky)

        # Clouds (simple)
        p.setBrush(QColor(255, 255, 255, 60))
        p.setPen(Qt.NoPen)
        for cx, cy, cw in [(w * 0.2, h * 0.1, 80), (w * 0.6, h * 0.15, 100), (w * 0.85, h * 0.08, 70)]:
            p.drawEllipse(QPointF(cx, cy), cw, cw * 0.4)

        # Stadium
        self._draw_stadium(p, w, h)

        # Always show field view first (background)
        self._draw_field_view(p, w, h)

        # Always show batter view (strike zone overlay) - smaller and positioned
        self._draw_batter_view(p, w, h)

        # Flash effect
        if self.flash_alpha > 0:
            p.fillRect(0, 0, w, h, QColor(255, 255, 255, int(self.flash_alpha)))

        # Fireworks with glow
        for f in self.fireworks:
            col = QColor(f['color'])
            col.setAlpha(int(f['alpha']))

            # Glow
            glow = QRadialGradient(QPointF(f['x'], f['y']), f['size'] * 2.5)
            glow.setColorAt(0, QColor(col.red(), col.green(), col.blue(), int(f['alpha'] * 0.4)))
            glow.setColorAt(1, QColor(col.red(), col.green(), col.blue(), 0))
            p.setBrush(glow)
            p.setPen(Qt.NoPen)
            p.drawEllipse(QPointF(f['x'], f['y']), f['size'] * 2.5, f['size'] * 2.5)

            # Core
            p.setBrush(col)
            p.drawEllipse(QPointF(f['x'], f['y']), f['size'], f['size'])

        # Celebration text
        if self.phase == "celebration" or (self.is_homerun and self.t >= 1.0):
            self._draw_celebration(p, w, h)

    def _draw_stadium(self, p: QPainter, w: int, h: int):
        """Draw detailed stadium background"""
        # Upper deck (dark)
        p.setBrush(QColor("#2a3848"))
        p.setPen(Qt.NoPen)

        # Left stands
        pts_left = [QPointF(0, h * 0.28), QPointF(w * 0.28, h * 0.38),
                    QPointF(w * 0.28, h * 0.52), QPointF(0, h * 0.48)]
        p.drawPolygon(QPolygonF(pts_left))

        # Right stands
        pts_right = [QPointF(w, h * 0.28), QPointF(w * 0.72, h * 0.38),
                     QPointF(w * 0.72, h * 0.52), QPointF(w, h * 0.48)]
        p.drawPolygon(QPolygonF(pts_right))

        # Center field stands
        p.setBrush(QColor("#354858"))
        pts_center = [QPointF(w * 0.25, h * 0.32), QPointF(w * 0.75, h * 0.32),
                      QPointF(w * 0.72, h * 0.42), QPointF(w * 0.28, h * 0.42)]
        p.drawPolygon(QPolygonF(pts_center))

        # Scoreboard in center field
        p.fillRect(int(w * 0.4), int(h * 0.25), int(w * 0.2), int(h * 0.1), QColor("#1a2a3a"))
        p.setPen(QPen(QColor("#3a5a7a"), 1))
        p.drawRect(int(w * 0.4), int(h * 0.25), int(w * 0.2), int(h * 0.1))

        # Outfield wall
        wall_grad = QLinearGradient(0, h * 0.45, 0, h * 0.52)
        wall_grad.setColorAt(0, QColor("#1a5a3a"))
        wall_grad.setColorAt(1, QColor("#0a3a2a"))
        p.fillRect(int(w * 0.12), int(h * 0.45), int(w * 0.76), int(h * 0.07), wall_grad)

        # Wall padding (yellow line)
        p.fillRect(int(w * 0.12), int(h * 0.45), int(w * 0.76), 3, QColor("#cccc00"))

    def _draw_batter_view(self, p: QPainter, w: int, h: int):
        """Draw batter's eye view with strike zone as overlay"""
        # Strike zone positioned in center-upper area
        zw = min(w, h) * 0.18
        zh = zw * 1.15
        zx = (w - zw) / 2
        zy = h * 0.15

        # Semi-transparent background for strike zone area
        bg_rect = QRectF(zx - 20, zy - 20, zw + 40, zh + 40)
        p.fillRect(bg_rect, QColor(0, 0, 0, 80))

        # Zone outline
        p.setPen(QPen(QColor(255, 255, 255, 200), 2))
        p.setBrush(Qt.NoBrush)
        p.drawRect(QRectF(zx, zy, zw, zh))

        # Grid
        p.setPen(QPen(QColor(255, 255, 255, 60), 1, Qt.DashLine))
        for i in range(1, 3):
            p.drawLine(QPointF(zx + i * zw / 3, zy), QPointF(zx + i * zw / 3, zy + zh))
            p.drawLine(QPointF(zx, zy + i * zh / 3), QPointF(zx + zw, zy + i * zh / 3))

        # Current pitch animation
        if self.phase == "pitch" and self.pitch:
            self._draw_pitch_animation(p, w, h, zx, zy, zw, zh, 255)

    def _draw_pitch_animation(self, p: QPainter, w: int, h: int, zx: float, zy: float, zw: float, zh: float, alpha: int):
        t = self.t
        pitch = self.pitch
        et = t ** 0.6

        start_size = 4
        end_size = 16

        end_x = zx + ((pitch.location.x + 0.3) / 0.6) * zw
        end_y = zy + (1.0 - (pitch.location.z - 0.3) / 0.9) * zh

        cx = (w / 2) * (1 - et) + end_x * et
        cy = (zy - zh * 0.5) * (1 - et) + end_y * et
        size = start_size * (1 - et) + end_size * et

        if et > 0.5:
            bf = (et - 0.5) / 0.5
            cx += pitch.horizontal_break * 0.18 * bf
            cy -= pitch.vertical_break * 0.09 * bf

        # Ball glow
        ball_glow = QRadialGradient(QPointF(cx, cy), size * 2)
        ball_glow.setColorAt(0, QColor(255, 255, 255, int(alpha * 0.3)))
        ball_glow.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(ball_glow)
        p.setPen(Qt.NoPen)
        p.drawEllipse(QPointF(cx, cy), size * 2, size * 2)

        # Ball
        grad = QRadialGradient(QPointF(cx - size * 0.25, cy - size * 0.25), size * 1.1)
        grad.setColorAt(0, QColor(255, 255, 255, alpha))
        grad.setColorAt(0.7, QColor(230, 230, 230, alpha))
        grad.setColorAt(1, QColor(180, 180, 180, alpha))
        p.setBrush(grad)
        p.drawEllipse(QPointF(cx, cy), size, size)

        # Velocity display
        if t >= 0.85:
            p.setPen(QColor(255, 255, 255, alpha))
            p.setFont(QFont("Impact", 32))
            p.drawText(int(w / 2 - 45), int(h / 2 + 85), f"{int(pitch.velocity)}")
            p.setFont(QFont("Segoe UI", 14))
            p.drawText(int(w / 2 + 25), int(h / 2 + 85), "km/h")
            p.setFont(QFont("Segoe UI", 12))
            p.drawText(int(w / 2 - 45), int(h / 2 + 110), pitch.pitch_type)

    def _draw_field_view(self, p: QPainter, w: int, h: int):
        """Draw overhead field view - always visible"""
        alpha = 255  # Always fully visible

        def proj(x: float, y: float, z: float) -> QPointF:
            cam_y = -8
            cam_z = 3.5
            ry = y - cam_y
            rz = z - cam_z
            if ry < 0.5:
                ry = 0.5
            fov = h * 0.95
            return QPointF(w / 2 + (x / ry) * fov, h * 0.62 - (rz / ry) * fov)

        # Grass with stripes
        grass_dark = QColor(25, 85, 35, alpha)
        grass_light = QColor(35, 105, 45, alpha)

        for i in range(16):
            y1, y2 = i * 7, (i + 1) * 7
            col = grass_dark if i % 2 == 0 else grass_light

            pts = []
            for ang in range(-48, 49, 8):
                rad = math.radians(ang)
                pts.append(proj(y1 * math.sin(rad) * 0.72, y1 * math.cos(rad), 0))
            for ang in range(48, -49, -8):
                rad = math.radians(ang)
                pts.append(proj(y2 * math.sin(rad) * 0.72, y2 * math.cos(rad), 0))

            if len(pts) > 2:
                path = QPainterPath()
                path.moveTo(pts[0])
                for pt in pts[1:]:
                    path.lineTo(pt)
                path.closeSubpath()
                p.fillPath(path, col)

        # Infield dirt
        dirt = QColor(110, 75, 55, alpha)
        p.setBrush(dirt)
        p.setPen(Qt.NoPen)
        inf = []
        for ang in range(0, 361, 12):
            rad = math.radians(ang)
            inf.append(proj(22 * math.sin(rad) * 0.42, 22 * math.cos(rad) * 0.36 + 15, 0))
        if inf:
            path = QPainterPath()
            path.moveTo(inf[0])
            for pt in inf[1:]:
                path.lineTo(pt)
            p.drawPath(path)

        # Base paths (white lines)
        p.setPen(QPen(QColor(255, 255, 255, int(alpha * 0.7)), 2))
        hp = proj(0, 0, 0)
        b1 = proj(15, 15, 0)
        b2 = proj(0, 30, 0)
        b3 = proj(-15, 15, 0)
        p.drawLine(hp, b1)
        p.drawLine(hp, b3)

        # Bases
        for i, (bx, by) in enumerate([(15, 15), (0, 30), (-15, 15)]):
            pt = proj(bx, by, 0)
            sz = 5

            # Glow for occupied base
            if self.runners[i]:
                glow = QRadialGradient(pt, sz * 3)
                glow.setColorAt(0, QColor(255, 215, 0, int(alpha * 0.5)))
                glow.setColorAt(1, QColor(255, 215, 0, 0))
                p.setBrush(glow)
                p.setPen(Qt.NoPen)
                p.drawEllipse(pt, sz * 3, sz * 3)

            diamond = QPolygonF([
                QPointF(pt.x(), pt.y() - sz),
                QPointF(pt.x() + sz, pt.y()),
                QPointF(pt.x(), pt.y() + sz),
                QPointF(pt.x() - sz, pt.y()),
            ])
            col = QColor(255, 215, 0, alpha) if self.runners[i] else QColor(255, 255, 255, alpha)
            p.setBrush(col)
            p.setPen(QPen(QColor(200, 200, 200, alpha), 1))
            p.drawPolygon(diamond)

        # Home plate
        p.setBrush(QColor(255, 255, 255, alpha))
        p.setPen(Qt.NoPen)
        p.drawEllipse(hp, 4, 2)

        # Ball animation
        if self.ball and self.phase in ["hit", "celebration"]:
            self._draw_hit_ball(p, w, h, proj, alpha)

    def _draw_hit_ball(self, p: QPainter, w: int, h: int, proj, alpha: int):
        ball = self.ball
        t = self.t

        angle = math.radians(ball.spray_angle)
        dist = ball.distance

        curr_d = dist * t
        curr_x = curr_d * math.sin(angle)
        curr_y = curr_d * math.cos(angle)

        peak = (ball.hang_time ** 2) * 2.2
        curr_z = 4 * peak * t * (1 - t) + 1.2 * (1 - t)

        ball_pt = proj(curr_x, curr_y, curr_z)

        # Shadow
        shadow_pt = proj(curr_x, curr_y, 0)
        p.setBrush(QColor(0, 0, 0, 50))
        p.setPen(Qt.NoPen)
        p.drawEllipse(shadow_pt, max(2, 7 - curr_z * 0.12), max(1, 3.5 - curr_z * 0.06))

        # Trail
        for i in range(min(12, int(t * 18))):
            tt = i / 18.0
            tx = dist * tt * math.sin(angle)
            ty = dist * tt * math.cos(angle)
            tz = 4 * peak * tt * (1 - tt) + 1.2 * (1 - tt)
            tpt = proj(tx, ty, tz)
            a = int(alpha * 0.55 * tt)
            p.setBrush(QColor(255, 220, 120, a))
            p.drawEllipse(tpt, 2.5, 2.5)

        # Ball
        ball_size = max(4, 11 - curr_y * 0.035)
        grad = QRadialGradient(QPointF(ball_pt.x() - ball_size * 0.2, ball_pt.y() - ball_size * 0.2), ball_size * 1.15)
        grad.setColorAt(0, QColor(255, 255, 255, alpha))
        grad.setColorAt(0.75, QColor(235, 235, 235, alpha))
        grad.setColorAt(1, QColor(200, 200, 200, alpha))
        p.setBrush(grad)
        p.drawEllipse(ball_pt, ball_size, ball_size)

        # Statcast
        if t > 0.3:
            self._draw_statcast(p, w, h, ball, alpha)

        # Result
        if t >= 0.95 and not self.is_homerun:
            self._draw_result(p, w, h, alpha)

    def _draw_statcast(self, p: QPainter, w: int, h: int, ball: BattedBallData, alpha: int):
        bx, by = int(w / 2 - 130), h - 55
        bw, bh = 260, 48

        # Background with border
        p.fillRect(bx, by, bw, bh, QColor(0, 0, 0, int(200 * alpha / 255)))
        p.setPen(QPen(QColor(100, 140, 180, alpha), 1))
        p.drawRect(bx, by, bw, bh)

        items = [
            (f"{ball.exit_velocity:.0f}", "km/h", "EXIT VELO"),
            (f"{ball.launch_angle:.0f}", "°", "LAUNCH"),
            (f"{ball.distance:.0f}", "m", "DISTANCE"),
        ]

        for i, (val, unit, label) in enumerate(items):
            x = bx + 15 + i * 85
            p.setPen(QColor(180, 190, 200, alpha))
            p.setFont(QFont("Segoe UI", 7))
            p.drawText(x, by + 12, label)

            p.setPen(QColor(255, 215, 0, alpha))
            p.setFont(QFont("Impact", 18))
            p.drawText(x, by + 38, val)

            p.setPen(QColor(150, 160, 170, alpha))
            p.setFont(QFont("Segoe UI", 9))
            p.drawText(x + 42, by + 38, unit)

    def _draw_result(self, p: QPainter, w: int, h: int, alpha: int):
        bh = 50
        p.fillRect(0, int(h / 2 - bh / 2), w, bh, QColor(0, 0, 0, int(210 * alpha / 255)))

        p.setPen(QColor(255, 255, 255, alpha))
        p.setFont(QFont("Impact", 26))
        p.drawText(QRectF(0, h / 2 - bh / 2, w, bh), Qt.AlignCenter, self.result)

    def _draw_celebration(self, p: QPainter, w: int, h: int):
        # Background
        grad = QLinearGradient(0, h * 0.32, 0, h * 0.62)
        grad.setColorAt(0, QColor(0, 0, 0, 0))
        grad.setColorAt(0.2, QColor(0, 0, 0, 200))
        grad.setColorAt(0.8, QColor(0, 0, 0, 200))
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(0, int(h * 0.32), w, int(h * 0.3), grad)

        # Glow text effect
        p.setPen(QColor(255, 100, 150, 80))
        p.setFont(QFont("Impact", 54, QFont.Bold))
        for dx, dy in [(-2, -2), (2, -2), (-2, 2), (2, 2)]:
            p.drawText(QRectF(dx, h * 0.36 + dy, w, 65), Qt.AlignCenter, "HOME RUN!")

        p.setPen(QColor(255, 255, 255))
        p.drawText(QRectF(0, h * 0.36, w, 65), Qt.AlignCenter, "HOME RUN!")

        if self.ball:
            p.setPen(QColor(255, 215, 0))
            p.setFont(QFont("Impact", 28))
            p.drawText(QRectF(0, h * 0.52, w, 45), Qt.AlignCenter, f"{self.ball.distance:.0f}m")


# ========================================
# Control Panel
# ========================================
class ControlPanel(QWidget):
    pitch_clicked = Signal()
    skip_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.setSpacing(12)

        self.pitch_btn = QPushButton("⚾ PITCH")
        self.pitch_btn.setFixedSize(110, 40)
        self.pitch_btn.clicked.connect(self.pitch_clicked.emit)
        self.pitch_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3090d0, stop:1 #2070b0);
                color: white;
                font: bold 14px 'Segoe UI';
                border: 1px solid #40a0e0;
                border-radius: 4px;
            }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #40b0f0, stop:1 #3090d0); }
            QPushButton:pressed { background: #2070b0; }
            QPushButton:disabled { background: #405060; color: #708090; border-color: #506070; }
        """)
        layout.addWidget(self.pitch_btn)

        self.skip_btn = QPushButton("SKIP GAME")
        self.skip_btn.setFixedSize(100, 40)
        self.skip_btn.clicked.connect(self.skip_clicked.emit)
        self.skip_btn.setStyleSheet("""
            QPushButton {
                background: #252535;
                color: #90a0b0;
                font: bold 11px 'Segoe UI';
                border: 1px solid #404050;
                border-radius: 4px;
            }
            QPushButton:hover { background: #353545; color: #b0c0d0; }
        """)
        layout.addWidget(self.skip_btn)

        layout.addStretch()

    def set_enabled(self, enabled: bool):
        self.pitch_btn.setEnabled(enabled)


# ========================================
# Main Page
# ========================================
class TVBroadcastGamePage(QWidget):
    game_finished = Signal(object)
    go_to_player_detail = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine: LiveGameEngine = None
        self.animating = False
        self.pending_ball = None
        self.date_str = "2027-01-01"
        self.new_ab = False

        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("background: #050810;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.scoreboard = TopScoreboard()
        main_layout.addWidget(self.scoreboard)

        middle_layout = QHBoxLayout()
        middle_layout.setContentsMargins(0, 0, 0, 0)
        middle_layout.setSpacing(0)

        self.away_panel = TeamLineupPanel(is_home=False)
        middle_layout.addWidget(self.away_panel)

        self.field_view = FieldView()
        self.field_view.done.connect(self._on_animation_done)
        middle_layout.addWidget(self.field_view, 1)

        self.home_panel = TeamLineupPanel(is_home=True)
        middle_layout.addWidget(self.home_panel)

        main_layout.addLayout(middle_layout, 1)

        bottom_layout = QHBoxLayout()
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(0)

        self.pitcher_panel = PitcherStatsPanel()
        bottom_layout.addWidget(self.pitcher_panel)

        self.control_panel = ControlPanel()
        self.control_panel.pitch_clicked.connect(self._pitch)
        self.control_panel.skip_clicked.connect(self._skip)
        bottom_layout.addWidget(self.control_panel, 1)

        self.batter_panel = BatterStatsPanel()
        bottom_layout.addWidget(self.batter_panel)

        main_layout.addLayout(bottom_layout)

    def start_game(self, home, away, date: str = "2027-01-01"):
        self.date_str = date
        self.engine = LiveGameEngine(home, away)

        stadium_name = home.stadium.name if hasattr(home, 'stadium') and home.stadium else "STADIUM"
        self.scoreboard.set_teams(away.name[:3], home.name[:3], stadium_name)
        self.scoreboard.set_score(0, 0)
        self.scoreboard.set_inning(1, True)
        self.scoreboard.set_count(0, 0, 0)

        self.away_panel.set_team(away.name, C.TEAM_NAVY)
        self.home_panel.set_team(home.name, C.TEAM_TEAL)

        self._update_lineups()
        self.field_view.reset()
        self._refresh()

    def _update_lineups(self):
        if not self.engine:
            return

        # Away lineup - use current_lineup instead of batting_order
        away_lineup = []
        lineup = getattr(self.engine.away_team, 'current_lineup', [])
        for i in range(min(9, len(lineup))):
            player_idx = lineup[i] if i < len(lineup) else -1
            if 0 <= player_idx < len(self.engine.away_team.players):
                player = self.engine.away_team.players[player_idx]
                pos_str = self._get_pos_abbr(player.position)
                away_lineup.append((player, pos_str))
            else:
                away_lineup.append((None, ""))
        while len(away_lineup) < 9:
            away_lineup.append((None, ""))
        self.away_panel.set_lineup(away_lineup)

        # Home lineup
        home_lineup = []
        lineup = getattr(self.engine.home_team, 'current_lineup', [])
        for i in range(min(9, len(lineup))):
            player_idx = lineup[i] if i < len(lineup) else -1
            if 0 <= player_idx < len(self.engine.home_team.players):
                player = self.engine.home_team.players[player_idx]
                pos_str = self._get_pos_abbr(player.position)
                home_lineup.append((player, pos_str))
            else:
                home_lineup.append((None, ""))
        while len(home_lineup) < 9:
            home_lineup.append((None, ""))
        self.home_panel.set_lineup(home_lineup)

    def _get_pos_abbr(self, pos: Position) -> str:
        pos_map = {
            Position.PITCHER: "P", Position.CATCHER: "C",
            Position.FIRST: "1B", Position.SECOND: "2B",
            Position.THIRD: "3B", Position.SHORTSTOP: "SS",
            Position.LEFT: "LF", Position.CENTER: "CF",
            Position.RIGHT: "RF", Position.DH: "DH"
        }
        return pos_map.get(pos, "DH")

    def _pitch(self):
        if self.animating or not self.engine or self.engine.is_game_over():
            return

        if self.new_ab:
            self.new_ab = False

        result, pitch, ball = self.engine.simulate_pitch()
        self.animating = True
        self.control_panel.set_enabled(False)

        res_name = result.name if hasattr(result, 'name') else str(result)
        res_map = {
            'BALL': 'ボール', 'STRIKE_CALLED': 'ストライク', 'STRIKE_SWINGING': '空振り',
            'FOUL': 'ファウル', 'HIT_BY_PITCH': '死球', 'SINGLE': 'ヒット',
            'DOUBLE': '二塁打', 'TRIPLE': '三塁打', 'HOME_RUN': 'ホームラン',
            'ERROR': 'エラー', 'SACRIFICE_FLY': '犠飛', 'SACRIFICE_BUNT': '犠打',
            'DOUBLE_PLAY': 'ゲッツー', 'GROUNDOUT': 'ゴロアウト', 'FLYOUT': 'フライアウト',
            'LINEOUT': 'ライナー', 'POPUP_OUT': 'ポップ', 'FIELDERS_CHOICE': '野選',
        }
        display = res_map.get(res_name, str(result.value) if hasattr(result, 'value') else str(result))

        self.pending_ball = (ball, display) if ball else None

        if pitch:
            self.field_view.start_pitch(pitch, display)
            self.scoreboard.set_pitch_info(pitch.pitch_type[:2].upper(), int(pitch.velocity * 0.621371))

            pitcher, _ = self.engine.get_current_pitcher()
            if pitcher:
                self.pitcher_panel.set_pitch_info(
                    f"{int(pitch.velocity - 3)}-{int(pitch.velocity)}",
                    pitch.pitch_type[:2].upper()
                )

        st = self.engine.state
        if res_name in ['SINGLE', 'DOUBLE', 'TRIPLE', 'HOME_RUN', 'ERROR', 'SACRIFICE_FLY',
                        'SACRIFICE_BUNT', 'DOUBLE_PLAY', 'GROUNDOUT', 'FLYOUT', 'LINEOUT',
                        'POPUP_OUT', 'FIELDERS_CHOICE', 'STRIKEOUT']:
            self.new_ab = True
        elif st.balls == 0 and st.strikes == 0:
            self.new_ab = True

    def _on_animation_done(self):
        if self.pending_ball:
            ball, display = self.pending_ball
            self.pending_ball = None

            self.field_view.set_runners([
                self.engine.state.runner_1b is not None,
                self.engine.state.runner_2b is not None,
                self.engine.state.runner_3b is not None
            ])

            QTimer.singleShot(150, lambda: self.field_view.start_hit(ball, display))
            return

        self.animating = False
        self.control_panel.set_enabled(True)
        self._refresh()

        if self.engine.is_game_over():
            self._finish()

    def _refresh(self):
        if not self.engine:
            return

        st = self.engine.state

        self.scoreboard.set_score(st.away_score, st.home_score)
        self.scoreboard.set_inning(st.inning, st.is_top)
        self.scoreboard.set_count(st.balls, st.strikes, st.outs)

        # Update current batter indicator
        if st.is_top:
            self.away_panel.set_current_batter(st.away_batter_order % 9)
            self.home_panel.set_current_batter(-1)
        else:
            self.away_panel.set_current_batter(-1)
            self.home_panel.set_current_batter(st.home_batter_order % 9)

        self.field_view.set_runners([
            st.runner_1b is not None,
            st.runner_2b is not None,
            st.runner_3b is not None
        ])

        # Update pitcher panel
        pitcher, _ = self.engine.get_current_pitcher()
        if pitcher:
            self.pitcher_panel.set_pitcher(pitcher)
            pitch_count = st.home_pitch_count if st.is_top else st.away_pitch_count
            stamina = st.home_pitcher_stamina if st.is_top else st.away_pitcher_stamina
            self.pitcher_panel.set_game_stats(0, 0, 0, 0, 0, pitch_count, stamina)

        # Update batter panel
        batter, _ = self.engine.get_current_batter()
        if batter:
            pos_str = self._get_pos_abbr(batter.position)
            self.batter_panel.set_batter(batter, pos_str)

    def _skip(self):
        if not self.engine or self.animating:
            return

        while not self.engine.is_game_over():
            self.engine.simulate_pitch()

        self.field_view.reset()
        self._refresh()
        self._finish()

    def _finish(self):
        if self.engine:
            self.engine.finalize_game_stats(self.date_str)

        self.game_finished.emit({
            "home_team": self.engine.home_team,
            "away_team": self.engine.away_team,
            "home_score": self.engine.state.home_score,
            "away_score": self.engine.state.away_score,
            "winner": self.engine.get_winner()
        })
