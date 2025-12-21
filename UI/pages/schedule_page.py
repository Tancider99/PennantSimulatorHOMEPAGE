# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Schedule Page
Calendar-based Schedule & Results with Visual Game Info (Fixed: Popup Double Issue)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCalendarWidget,
    QPushButton, QFrame, QSplitter, QProgressBar, QDialog, 
    QGraphicsDropShadowEffect, QTableWidget, QTableWidgetItem, 
    QHeaderView, QAbstractItemView, QMessageBox
)
from PySide6.QtCore import Qt, QDate, Signal, QThread, QRect, QPoint, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QBrush, QTextOption

import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.cards import Card
from models import GameStatus

class SimulationWorker(QThread):
    progress_updated = Signal(int, int, str)
    day_advanced = Signal()  # Signal to main thread to call advance_day
    finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, game_state, target_date, parent=None):
        super().__init__(parent)
        self.game_state = game_state
        self.target_date = target_date
        self.is_cancelled = False

    def run(self):
        try:
            if not self.game_state.current_date:
                self.finished.emit()
                return

            current_qdate = self._str_to_date(self.game_state.current_date)
            # 翌日からターゲット日付まで
            days_to_sim = current_qdate.daysTo(self.target_date)
            
            if days_to_sim < 0: # 修正: 0日(当日)も含めるため < 0 に変更
                self.finished.emit()
                return

            for i in range(days_to_sim): # 当日〜ターゲット日の前日まで（ターゲット日は含めない）
                if self.is_cancelled: break
                
                # 修正: 当日から順にシミュレート
                sim_date = current_qdate.addDays(i) 
                date_str = sim_date.toString("yyyy-MM-dd")
                
                self.progress_updated.emit(i + 1, days_to_sim, f"Simulating: {date_str}")
                
                # GameStateに処理を委譲（エラーハンドリング済み）
                self.game_state.process_date(date_str)
                
                # Emit signal for main thread to handle contracts/scouting updates
                self.day_advanced.emit()
            
            # After simulation, advance the current_date to the target date
            if not self.is_cancelled:
                self.game_state.current_date = self.target_date.toString("yyyy-MM-dd")
                
            self.finished.emit()
            
        except Exception as e:
            traceback.print_exc()
            self.error_occurred.emit(str(e))

    def _str_to_date(self, d_str):
        try:
            y, m, d = map(int, d_str.split('-'))
            return QDate(y, m, d)
        except:
            return QDate.currentDate()

# ... (GameCalendarWidget クラスは変更なしのため省略) ...
class GameCalendarWidget(QCalendarWidget):
    """Custom Calendar Widget that paints game info in cells"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.games_map = {} # {QDate: Game}
        self.player_team_name = ""
        
        self.setGridVisible(True)
        self.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.setNavigationBarVisible(True)
        
        self.setMinimumDate(QDate(2027, 3, 1))
        self.setMaximumDate(QDate(2027, 10, 31))
        
        self.setStyleSheet(f"""
            QCalendarWidget {{ background-color: {self.theme.bg_card}; border: none; }}
            QCalendarWidget QWidget {{ alternate-background-color: {self.theme.bg_input}; }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: {self.theme.text_primary}; background-color: {self.theme.bg_card};
                selection-background-color: transparent; selection-color: {self.theme.text_primary}; outline: none;
            }}
            QCalendarWidget QToolButton {{ color: {self.theme.text_primary}; background-color: transparent; icon-size: 24px; font-weight: bold; }}
            QCalendarWidget QMenu {{ background-color: {self.theme.bg_card}; color: {self.theme.text_primary}; }}
            QCalendarWidget QSpinBox {{ color: {self.theme.text_primary}; background-color: {self.theme.bg_input}; }}
        """)

    def set_data(self, games, player_team_name, player_league=None):
        self.games_map = {}
        self.player_team_name = player_team_name
        self.player_league = player_league
        
        min_date = QDate(2027, 3, 1)
        max_date = QDate(2027, 10, 31)
        
        for game in games:
            try:
                y, m, d = map(int, game.date.split('-'))
                qdate = QDate(y, m, d)
                self.games_map[qdate] = game
                
                if qdate < min_date: min_date = qdate
                if qdate > max_date: max_date = qdate
            except: pass
            
        self.setMinimumDate(QDate(min_date.year(), 3, 1))
        self.setMaximumDate(QDate(max_date.year(), 10, 31))
        
        self.updateCells()

    def paintCell(self, painter: QPainter, rect: QRect, date: QDate):
        painter.save()
        if date == self.selectedDate(): painter.fillRect(rect, QColor(self.theme.primary_hover))
        else: painter.fillRect(rect, QColor(self.theme.bg_card))
        if date.month() != self.monthShown(): painter.fillRect(rect, QColor(0, 0, 0, 160)) 
        
        painter.setPen(QColor(self.theme.text_primary))
        if date.month() != self.monthShown(): painter.setPen(QColor(self.theme.text_muted))
        font = painter.font(); font.setBold(True); font.setPointSize(10)
        painter.setFont(font)
        painter.drawText(rect.topLeft() + QPoint(6, 16), str(date.day()))

        if date in self.games_map:
            game = self.games_map[date]
            opponent = ""
            # ホーム/ビジター情報付きで対戦相手を表示
            if "ALL-" in game.home_team_name or "ALL-" in game.away_team_name:
                opponent = "ALL STAR"
            elif game.home_team_name == self.player_team_name:
                opponent = f"vs {game.away_team_name[:3]}"  # ホーム
            elif game.away_team_name == self.player_team_name:
                opponent = f"@ {game.home_team_name[:3]}"   # ビジター
            else:
                opponent = f"{game.away_team_name[:1]}-{game.home_team_name[:1]}"

            bg_color = QColor(self.theme.bg_input); text_color = QColor(self.theme.text_secondary)
            status_text = ""

            # 雨天中止チェック
            is_cancelled = game.status == GameStatus.CANCELLED

            if is_cancelled:
                bg_color = QColor("#666666"); text_color = QColor("white")
                status_text = "雨天中止"
            elif game.is_completed:
                is_win, is_draw = False, False
                if self.player_team_name:
                    if game.home_team_name == self.player_team_name:
                        if game.home_score > game.away_score: is_win = True
                        elif game.home_score == game.away_score: is_draw = True
                    elif game.away_team_name == self.player_team_name:
                        if game.away_score > game.home_score: is_win = True
                        elif game.away_score == game.home_score: is_draw = True

                if is_win: bg_color = QColor(self.theme.success); text_color = QColor("white")
                elif is_draw: bg_color = QColor(self.theme.text_muted); text_color = QColor("white")
                else: bg_color = QColor(self.theme.danger); text_color = QColor("white")

                # All-Star Special Coloring
                if "ALL-" in game.home_team_name or "ALL-" in game.away_team_name:
                    if self.player_league:
                        # Determine Winner
                        winner_name = ""
                        if game.home_score > game.away_score: winner_name = game.home_team_name
                        elif game.away_score > game.home_score: winner_name = game.away_team_name
                        else: winner_name = "DRAW"
                        
                        # Normalize League Name
                        p_league_str = str(self.player_league.value) if hasattr(self.player_league, 'value') else str(self.player_league)
                        
                        is_my_league_win = False
                        if "North" in p_league_str and "ALL-NORTH" in winner_name: is_my_league_win = True
                        elif "South" in p_league_str and "ALL-SOUTH" in winner_name: is_my_league_win = True
                        
                        if winner_name == "DRAW":
                            bg_color = QColor(self.theme.text_muted)
                        elif is_my_league_win:
                            bg_color = QColor(self.theme.success)
                        else:
                            bg_color = QColor(self.theme.danger)
            else:
                # 試合予定（未消化） - 白背景・黒文字
                bg_color = QColor("white"); text_color = QColor("black")

            info_rect = QRect(rect.left() + 2, rect.top() + 22, rect.width() - 4, 18)
            painter.fillRect(info_rect, bg_color)
            painter.setPen(text_color); font.setPointSize(9); painter.setFont(font)
            painter.drawText(info_rect, Qt.AlignCenter, opponent)

            # スコアまたはステータス表示
            score_rect = QRect(rect.left() + 2, rect.top() + 42, rect.width() - 4, 16)
            painter.setPen(QColor(self.theme.text_primary))
            if is_cancelled:
                painter.drawText(score_rect, Qt.AlignCenter, status_text)
            elif game.is_completed:
                painter.drawText(score_rect, Qt.AlignCenter, f"{game.away_score}-{game.home_score}")
        painter.restore()

class SchedulePage(QWidget):
    """Calendar-based schedule management page"""
    game_selected = Signal(object)
    watch_game_requested = Signal(object) # New Signal
    view_result_requested = Signal(object)  # Signal to navigate to past game result

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = None
        self.contracts_page = None  # Set by main_window for scouting processing
        self.selected_date = QDate.currentDate()
        self.worker = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0); layout.setSpacing(0)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {self.theme.border}; width: 1px; }}")
        left_panel = self._create_calendar_panel()
        splitter.addWidget(left_panel)
        right_panel = self._create_info_panel()
        splitter.addWidget(right_panel)
        splitter.setSizes([700, 300])
        layout.addWidget(splitter)

    def _create_calendar_panel(self) -> QWidget:
        panel = QWidget(); panel.setStyleSheet(f"background-color: {self.theme.bg_dark};")
        layout = QVBoxLayout(panel); layout.setContentsMargins(20, 20, 10, 20)
        lbl = QLabel("SEASON SCHEDULE"); lbl.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {self.theme.text_primary}; letter-spacing: 2px;")
        layout.addWidget(lbl)
        self.calendar = GameCalendarWidget()
        self.calendar.clicked.connect(self._on_date_selected)
        self.calendar.activated.connect(self._on_date_double_clicked)  # Double-click
        layout.addWidget(self.calendar)
        return panel

    def _create_info_panel(self) -> QWidget:
        panel = QWidget(); panel.setStyleSheet(f"background-color: {self.theme.bg_card}; border-left: 1px solid {self.theme.border};")
        layout = QVBoxLayout(panel); layout.setContentsMargins(20, 20, 20, 20); layout.setSpacing(20)
        self.date_label = QLabel("---"); self.date_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {self.theme.text_primary};")
        self.date_label.setAlignment(Qt.AlignCenter); layout.addWidget(self.date_label)

        self.detail_card = Card(); self.detail_card.setFixedHeight(200)
        container = QWidget(); container.setStyleSheet("background: transparent;")
        card_layout = QVBoxLayout(container); card_layout.setContentsMargins(0,0,0,0); card_layout.setSpacing(8)
        self.matchup_label = QLabel("NO GAME"); self.matchup_label.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {self.theme.text_primary}; background: transparent;")
        self.matchup_label.setAlignment(Qt.AlignCenter); card_layout.addWidget(self.matchup_label)
        self.score_label = QLabel(""); self.score_label.setStyleSheet(f"font-size: 32px; font-weight: bold; color: {self.theme.accent_blue}; background: transparent;")
        self.score_label.setAlignment(Qt.AlignCenter); card_layout.addWidget(self.score_label)
        self.status_label = QLabel(""); self.status_label.setStyleSheet(f"font-size: 14px; color: {self.theme.text_secondary}; background: transparent;")
        self.status_label.setAlignment(Qt.AlignCenter); card_layout.addWidget(self.status_label)
        self.detail_card.add_widget(container); layout.addWidget(self.detail_card)
        
        # Action Buttons Layout
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(10)
        
        # Watch / Play Button
        # Watch Button Removed
        # self.watch_btn = QPushButton("試合を見る")...
        # btn_layout.addWidget(self.watch_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()
        
        # Skip Button (Moved to Bottom)
        self.skip_btn = QPushButton("この日までスキップ"); self.skip_btn.setCursor(Qt.PointingHandCursor); self.skip_btn.setFixedHeight(50)
        self.skip_btn.setStyleSheet(f"QPushButton {{ background-color: {self.theme.primary}; color: {self.theme.text_highlight}; border: none; border-radius: 8px; font-size: 14px; font-weight: bold; padding: 10px; }} QPushButton:hover {{ background-color: {self.theme.primary_hover}; }} QPushButton:disabled {{ background-color: {self.theme.bg_input}; color: {self.theme.text_muted}; border: 1px solid {self.theme.border}; }}")
        self.skip_btn.clicked.connect(self._on_skip_clicked); self.skip_btn.setEnabled(False)
        layout.addWidget(self.skip_btn)
        
        return panel

    def set_game_state(self, game_state):
        self.game_state = game_state
        if not game_state: return
        if hasattr(game_state, 'current_date'):
            try:
                y, m, d = map(int, game_state.current_date.split('-'))
                self.calendar.setSelectedDate(QDate(y, m, d)); self.selected_date = QDate(y, m, d)
            except: pass
        self._refresh_calendar_data(); self._refresh_info_panel()

    def _refresh_calendar_data(self):
        if not self.game_state or not self.game_state.schedule: return
        my_team_name = self.game_state.player_team.name if self.game_state.player_team else ""
        # Include My Team games AND All-Star games
        games = [g for g in self.game_state.schedule.games if 
                 g.home_team_name == my_team_name or 
                 g.away_team_name == my_team_name or
                 g.home_team_name in ["ALL-NORTH", "ALL-SOUTH"] or
                 g.away_team_name in ["ALL-NORTH", "ALL-SOUTH"]]
        
        player_league = getattr(self.game_state.player_team, 'league', None) if self.game_state.player_team else None
        self.calendar.set_data(games, my_team_name, player_league)

    def _get_allstar_games(self, as_engine, calendar):
        """Construct dummy ScheduledGame objects for All-Star display"""
        from league_schedule_engine import ScheduledGame, GameStatus
        games = []
        
        # Game 1
        g1 = ScheduledGame(
            game_number=1, date=calendar.allstar_day1.strftime("%Y-%m-%d"),
            home_team_name="ALL-NORTH", away_team_name="ALL-SOUTH"
        )
        if as_engine.game1_result:
            g1.status = GameStatus.COMPLETED
            g1.home_score, g1.away_score = as_engine.game1_result
            # Swap if defined differently in engine (North vs South? Engine doesn't specify home/away explicitly in result tuple logic, assumed order)
            # Engine.get_winner logic: game1_result[0] vs [1].
            # Let's assume Tuple is (Team1, Team2) -> (North, South) for now based on typical ordering? 
            # North teams usually listed first.
            g1.home_score = as_engine.game1_result[0] # North
            g1.away_score = as_engine.game1_result[1] # South
        else:
             g1.status = GameStatus.SCHEDULED
             
        games.append(g1)
        
        # Game 2
        g2 = ScheduledGame(
            game_number=2, date=calendar.allstar_day2.strftime("%Y-%m-%d"),
            home_team_name="ALL-SOUTH", away_team_name="ALL-NORTH"
        )
        if as_engine.game2_result:
            g2.status = GameStatus.COMPLETED
            g2.home_score = as_engine.game2_result[0] # South (Home)
            g2.away_score = as_engine.game2_result[1] # North (Away)
        else:
             g2.status = GameStatus.SCHEDULED
             
        games.append(g2)
        
        return games
    
    def _get_postseason_games_for_team(self, ps_engine, team_name: str) -> list:
        """自チームが参加しているポストシーズンの試合を取得"""
        games = []
        
        series_list = [
            ps_engine.cs_north_first,
            ps_engine.cs_south_first,
            ps_engine.cs_north_final,
            ps_engine.cs_south_final,
            ps_engine.japan_series
        ]
        
        for series in series_list:
            if series and (series.team1 == team_name or series.team2 == team_name):
                # Add games from this series
                if hasattr(series, 'schedule') and series.schedule:
                    games.extend(series.schedule)
        
        return games

    def _on_date_selected(self, date):
        self.selected_date = date; self._refresh_info_panel()

    def _on_date_double_clicked(self, date):
        """Handle double-click on calendar date to view completed game result"""
        if not self.game_state or not self.game_state.schedule:
            return
        
        date_str = date.toString("yyyy-MM-dd")
        my_team_name = self.game_state.player_team.name if self.game_state.player_team else ""
        
        for game in self.game_state.schedule.games:
            if game.date == date_str and (
                game.home_team_name == my_team_name or 
                game.away_team_name == my_team_name or
                game.home_team_name in ["ALL-NORTH", "ALL-SOUTH"] or
                game.away_team_name in ["ALL-NORTH", "ALL-SOUTH"]
            ):
                if game.is_completed:
                    self.view_result_requested.emit(game)
                    return
                break

    def _refresh_info_panel(self):
        date_str = self.selected_date.toString("yyyy-MM-dd")
        self.date_label.setText(self.selected_date.toString("yyyy年M月d日"))
        target_game = None
        if self.game_state and self.game_state.schedule:
            my_team_name = self.game_state.player_team.name if self.game_state.player_team else ""
            for game in self.game_state.schedule.games:
                # プレイヤーチームの試合 または オールスターゲームを表示
                if game.date == date_str and (
                    game.home_team_name == my_team_name or 
                    game.away_team_name == my_team_name or
                    game.home_team_name in ["ALL-NORTH", "ALL-SOUTH"] or
                    game.away_team_name in ["ALL-NORTH", "ALL-SOUTH"]
                ):
                    target_game = game; break
        
        if target_game:
            self.current_target_game = target_game
            self.matchup_label.setText(f"{target_game.away_team_name} vs {target_game.home_team_name}")
            if target_game.is_completed:
                self.score_label.setText(f"{target_game.away_score} - {target_game.home_score}"); self.status_label.setText("試合終了")

            else: 
                self.score_label.setText("-"); self.status_label.setText("試合予定")
                
                # Check for Watch Availability (Today & Scheduled)
                current_gdate = self._get_current_game_date()
                target_gdate = self._str_to_date(target_game.date)
                
                # Watch Button removed as per request
                # if target_gdate == current_gdate: ...

        else:
            self.current_target_game = None
            self.matchup_label.setText("一軍試合なし"); self.score_label.setText(""); self.status_label.setText("")
            # self.watch_btn.setVisible(False)

        current_gdate = self._get_current_game_date()
        if self.selected_date > current_gdate:
            self.skip_btn.setEnabled(True)
            diff = self.selected_date.toJulianDay() - current_gdate.toJulianDay()
            self.skip_btn.setText(f"{diff}日分をスキップ (全軍自動消化)")
        else: self.skip_btn.setEnabled(False); self.skip_btn.setText("過去または当日のためスキップ不可")

    # _on_watch_clicked removed


    def _get_current_game_date(self) -> QDate:
        if self.game_state and hasattr(self.game_state, 'current_date'):
            try:
                y, m, d = map(int, self.game_state.current_date.split('-'))
                return QDate(y, m, d)
            except: pass
        return QDate.currentDate()

    def _on_skip_clicked(self):
        if not self.game_state: return
        player_team = self.game_state.player_team
        if player_team:
            valid_starters = len([x for x in player_team.current_lineup if x != -1])
            valid_rotation = len([x for x in player_team.rotation if x != -1])
            if valid_starters < 9: QMessageBox.warning(self, "スキップ不可", "一軍スタメンが9人未満です。オーダー画面で設定してください。"); return
            if valid_rotation == 0: QMessageBox.warning(self, "スキップ不可", "一軍先発投手が設定されていません。オーダー画面で設定してください。"); return

        reply = QMessageBox.question(self, "シミュレーション実行", f"{self.selected_date.toString('yyyy/MM/dd')} までの全試合（一軍・二軍・三軍）をスキップしますか？\n処理には時間がかかる場合があります。", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes: self._start_simulation()

    def _start_simulation(self):
        self.progress_dialog = QDialog(self); self.progress_dialog.setWindowTitle("シミュレーション中..."); self.progress_dialog.setFixedSize(400, 150)
        self.progress_dialog.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint); self.progress_dialog.setStyleSheet(f"background-color: {self.theme.bg_card}; color: {self.theme.text_primary};")
        p_layout = QVBoxLayout(self.progress_dialog)
        self.p_label = QLabel("準備中..."); self.p_label.setAlignment(Qt.AlignCenter); p_layout.addWidget(self.p_label)
        self.p_bar = QProgressBar(); self.p_bar.setStyleSheet(f"QProgressBar {{ border: 1px solid {self.theme.border}; border-radius: 4px; text-align: center; color: {self.theme.text_primary}; }} QProgressBar::chunk {{ background-color: {self.theme.primary}; }}")
        p_layout.addWidget(self.p_bar)
        
        # キャンセルボタン追加
        cancel_btn = QPushButton("キャンセル"); cancel_btn.clicked.connect(self._cancel_simulation); p_layout.addWidget(cancel_btn)

        self.worker = SimulationWorker(self.game_state, self.selected_date, parent=self)
        self.worker.progress_updated.connect(self._update_progress)
        self.worker.day_advanced.connect(self._on_day_advanced)  # Handle in main thread
        self.worker.finished.connect(self._on_simulation_finished)
        self.worker.error_occurred.connect(self._on_simulation_error)
        self.worker.start()
        
        # ▼▼▼ 修正: exec()の戻り値で処理を分岐し、二重表示を防ぐ ▼▼▼
        # ダイアログが閉じられるまでここでブロックされる
        if self.progress_dialog.exec() == QDialog.Accepted:
            self._refresh_calendar_data()
            self._refresh_info_panel()
            QMessageBox.information(self, "完了", "指定日までの日程消化が完了しました。")
        # ▲▲▲ 修正終了 ▲▲▲

    def _update_progress(self, current, total, message): 
        self.p_bar.setMaximum(total); self.p_bar.setValue(current); self.p_label.setText(message)
        
    def _cancel_simulation(self):
        if self.worker: self.worker.is_cancelled = True; self.worker.wait()
        self.progress_dialog.reject() # rejectで閉じる
    
    def _on_simulation_finished(self):
        # 修正: accept()を呼ぶだけで、メッセージボックスはexec()の後で処理する
        self.progress_dialog.accept()

    def _on_day_advanced(self):
        """Handle day advanced signal from worker thread - run in main thread"""
        if self.contracts_page:
            try:
                self.contracts_page.advance_day()
            except Exception:
                pass  # Ignore errors in contracts page

    def _on_simulation_error(self, message): 
        # エラー時はrejectで閉じる
        self.progress_dialog.reject()
        QMessageBox.critical(self, "エラー", f"シミュレーション中にエラーが発生しました:\n{message}")
    
    def closeEvent(self, event):
        if self.worker and self.worker.isRunning(): self.worker.is_cancelled = True; self.worker.wait()
        super().closeEvent(event)

    def _get_current_game_date(self):
        if self.game_state and self.game_state.current_date:
            return self._str_to_date(self.game_state.current_date)
        return QDate.currentDate()

    def _str_to_date(self, d_str):
        try:
            y, m, d = map(int, d_str.split('-'))
            return QDate(y, m, d)
        except:
            return QDate.currentDate()