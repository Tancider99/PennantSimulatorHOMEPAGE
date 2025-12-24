# -*- coding: utf-8 -*-
"""
Baseball Team Architect 2027 - Schedule Page
Calendar-based Schedule & Results with Visual Game Info (Fixed: Popup Double Issue)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCalendarWidget,
    QPushButton, QFrame, QSplitter, QProgressBar, QDialog, 
    QGraphicsDropShadowEffect, QTableWidget, QTableWidgetItem, 
    QHeaderView, QAbstractItemView, QMessageBox, QScrollArea, QSizePolicy, QCheckBox
)
from PySide6.QtCore import Qt, QDate, Signal, QThread, QRect, QPoint, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QBrush, QTextOption, QPen

import sys
import os
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from UI.theme import get_theme
from UI.widgets.cards import Card
from models import GameStatus

class SimulationWorker(QThread):
    progress_updated = Signal(int, int, str, dict) # Added dict for simulation data
    day_advanced = Signal()  # Signal to main thread to call advance_day
    finished = Signal()
    error_occurred = Signal(str)

    def __init__(self, game_state, target_date, stop_conditions=None, parent=None):
        super().__init__(parent)
        self.game_state = game_state
        self.target_date = target_date
        self.stop_conditions = stop_conditions or {} # {key: bool}
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
                
                self.progress_updated.emit(i + 1, days_to_sim, f"Simulating: {date_str}", {})
                
                # GameStateに処理を委譲（エラーハンドリング済み）
                self.game_state.process_date(date_str)
                
                # オフシーズン突入チェック - ポストシーズン終了でシミュレーション停止
                if getattr(self.game_state, 'is_offseason', False):
                    self.is_cancelled = True
                    break
                
                # データ収集 - BEFORE stop condition check so data is available when stopping
                sim_data = {}
                
                # 1. 順位履歴 (グラフ用)
                if hasattr(self.game_state, 'daily_rankings'):
                    sim_data['rankings'] = self.game_state.daily_rankings
                
                # 2. 当日の試合結果 (雨天中止も含む)
                daily_results = []
                if self.game_state.schedule:
                    daily_results = [g for g in self.game_state.schedule.games 
                                     if g.date == date_str and (g.is_completed or g.status == GameStatus.CANCELLED)]
                sim_data['results'] = daily_results
                
                # 3. 現在の順位とゲーム差
                from models import League
                sim_data['standings_north'] = self.game_state._get_league_standings(League.NORTH)
                sim_data['standings_south'] = self.game_state._get_league_standings(League.SOUTH)
                
                # 4. 通知 (怪我、トレードなど) - news_feed contains dicts with keys: date, category, message, team
                notifications = []
                # Calculate dates for checking recent news (last 3 days)
                valid_dates = {
                    date_str,  # Today
                    sim_date.addDays(-1).toString("yyyy-MM-dd"),  # Yesterday
                    sim_date.addDays(-2).toString("yyyy-MM-dd"),  # 2 days ago
                }
                
                if self.game_state.news_feed:
                    already_shown = set()  # Avoid duplicates
                    for news in self.game_state.news_feed[:30]:  # Check first 30 (newest first)
                        if isinstance(news, dict):
                            news_date = news.get('date', '')
                            # Accept news from last 3 days
                            if news_date in valid_dates:
                                msg = news.get('message', '')
                                cat = news.get('category', '')
                                # Avoid duplicates
                                if msg in already_shown:
                                    continue
                                already_shown.add(msg)
                                
                                notif_type = 'news'
                                if cat == '怪我': notif_type = 'injury'
                                elif 'トレード' in cat: notif_type = 'trade'
                                notifications.append({'type': notif_type, 'message': msg})

                sim_data['notifications'] = notifications



                self.progress_updated.emit(i + 1, days_to_sim, f"Simulating: {date_str}", sim_data)
                
                # Track last simulated date for cancel handling
                last_sim_date = sim_date
                
                # Emit signal for main thread to handle contracts/scouting updates
                self.day_advanced.emit()

            
            # After simulation, advance the current_date
            if self.is_cancelled:
                # キャンセル時: 最後にシミュレートした日の翌日を設定（試合前の状態）
                if 'last_sim_date' in dir():
                    next_day = last_sim_date.addDays(1).toString("yyyy-MM-dd")
                    self.game_state.current_date = next_day
            else:
                # 正常終了: ターゲット日を設定
                self.game_state.current_date = self.target_date.toString("yyyy-MM-dd")
                
            self.finished.emit()

            
        except Exception as e:
            traceback.print_exc()
            self.error_occurred.emit(str(e))

    def _check_stop_conditions(self, date_str, yesterday_date=None):
        """中断条件をチェック"""
        if not self.stop_conditions: return None
        
        # Build list of valid dates (today and yesterday)
        valid_dates = {date_str}
        if yesterday_date:
            valid_dates.add(yesterday_date)
        
        # Check all news items for the current date or yesterday
        if self.game_state.news_feed:
            for news in self.game_state.news_feed[:30]:  # Check first 30
                if not isinstance(news, dict):
                    continue
                news_date = news.get('date', '')
                if news_date not in valid_dates:
                    continue  # Skip news from other dates
                
                msg = news.get('message', '')
                cat = news.get('category', '')
                team = news.get('team', '')
                
                # 1. 怪我人が出た場合 (category='怪我')
                if self.stop_conditions.get("injury", False):
                    if cat == "怪我" and team == self.game_state.player_team.name:
                        return f"自チーム選手に負傷が発生しました: {msg}"
                
                # 2. トレード結果が出た場合 (category='トレード')
                if self.stop_conditions.get("trade", False):
                    if "トレード" in cat and (team == self.game_state.player_team.name or "成立" in msg):
                        return f"トレード結果が出ました: {msg}"

        # 3. シーズン終了 (デフォルトで止まるべきだが明示的に)
        if self.stop_conditions.get("season_end", True):
            if self.game_state.schedule_engine and self.game_state.schedule_engine.is_regular_season_complete():
                return "レギュラーシーズンが終了しました"
                
        return None



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
        self.setMaximumDate(QDate(2027, 11, 30))
        
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
        max_date = QDate(2027, 11, 30)
        
        for game in games:
            try:
                y, m, d = map(int, game.date.split('-'))
                qdate = QDate(y, m, d)
                self.games_map[qdate] = game
                
                if qdate < min_date: min_date = qdate
                if qdate > max_date: max_date = qdate
            except: pass
            
        self.setMinimumDate(QDate(min_date.year(), 3, 1))
        self.setMaximumDate(QDate(max_date.year(), 11, 30))
        
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
                bg_color = QColor("#2196F3"); text_color = QColor("white")  # Blue for rain cancellation
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


class SimulationProgressDialog(QDialog):
    """拡張シミュレーションウィンドウ"""
    def __init__(self, parent=None, game_state=None):
        super().__init__(parent)
        self.theme = get_theme()
        self.game_state = game_state
        self.setWindowTitle("シミュレーション中...")
        self.resize(900, 600)
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        self.setStyleSheet(f"background-color: {self.theme.bg_card}; color: {self.theme.text_primary};")
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 上部: グラフ (大きく表示) と 順位表 (縦に並べる)
        top_splitter = QSplitter(Qt.Horizontal)
        
        # グラフエリア (プレイヤーリーグのみ、大きく)
        graph_widget = QWidget()
        graph_layout = QVBoxLayout(graph_widget)
        graph_layout.setContentsMargins(0, 0, 0, 0)
        graph_layout.setSpacing(2)
        self.lbl_graph_title = QLabel("MY LEAGUE RANKING")
        self.lbl_graph_title.setAlignment(Qt.AlignCenter)
        self.lbl_graph_title.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {self.theme.text_secondary};")
        graph_layout.addWidget(self.lbl_graph_title)
        self.graph_view = RankingGraphWidget(self.theme)
        graph_layout.addWidget(self.graph_view, 1)  # Stretch
        top_splitter.addWidget(graph_widget)
        
        # 順位表エリア (プレイヤーリーグのみ、1列)
        standings_widget = QWidget()
        standings_layout = QVBoxLayout(standings_widget)
        standings_layout.setContentsMargins(0, 0, 0, 0)
        self.lbl_league_title = QLabel("STANDINGS")
        self.lbl_league_title.setAlignment(Qt.AlignCenter)
        self.lbl_league_title.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {self.theme.text_secondary};")
        standings_layout.addWidget(self.lbl_league_title)
        self.table_standings = QTableWidget()
        self._setup_std_table(self.table_standings)
        standings_layout.addWidget(self.table_standings)
        top_splitter.addWidget(standings_widget)
        
        top_splitter.setSizes([600, 300])  # Graph larger
        layout.addWidget(top_splitter, 3)  # Weight 3

        # 中部: プレイヤーチーム試合結果 (左) + 通知エリア (右)
        mid_widget = QWidget()
        mid_layout = QHBoxLayout(mid_widget)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.setSpacing(8)
        
        # プレイヤーチーム試合結果 (1枚のカード)
        self.player_result_card = QFrame()
        self.player_result_card.setFixedWidth(220)
        self.player_result_card.setStyleSheet(f"background-color: {self.theme.bg_card}; border: 1px solid {self.theme.border};")  # Angular
        self.player_result_layout = QVBoxLayout(self.player_result_card)
        self.player_result_layout.setAlignment(Qt.AlignCenter)
        mid_layout.addWidget(self.player_result_card)
        
        # 通知エリア (トレード、怪我など)
        notif_frame = QFrame()
        notif_frame.setStyleSheet(f"background-color: {self.theme.bg_card}; border: 1px solid {self.theme.border};")
        notif_layout = QVBoxLayout(notif_frame)
        notif_layout.setContentsMargins(8, 8, 8, 8)
        lbl_notif_title = QLabel("NOTIFICATIONS")
        lbl_notif_title.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {self.theme.text_secondary};")
        notif_layout.addWidget(lbl_notif_title)
        self.notification_list = QVBoxLayout()
        self.notification_list.setSpacing(4)
        notif_layout.addLayout(self.notification_list)
        notif_layout.addStretch()
        mid_layout.addWidget(notif_frame, 1)  # Stretch
        
        layout.addWidget(mid_widget, 1)  # Weight 1
        
        # 下部: プログレスバー
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        self.p_label = QLabel("準備中...")
        bottom_layout.addWidget(self.p_label)
        self.p_bar = QProgressBar()
        self.p_bar.setTextVisible(True)
        self.p_bar.setFormat("%p%")
        # Use stylesheet that makes text readable on both filled and unfilled parts
        self.p_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {self.theme.border};
                text-align: center;
                color: {self.theme.text_primary};
                background-color: {self.theme.bg_input};
            }}
            QProgressBar::chunk {{
                background-color: {self.theme.primary};
            }}
        """)
        bottom_layout.addWidget(self.p_bar)
        
        self.cancel_btn = QPushButton("キャンセル")
        bottom_layout.addWidget(self.cancel_btn)
        
        layout.addWidget(bottom_widget)

    def _setup_std_table(self, table):
        # 2 columns: Team Name, Magic/GB
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["チーム", "M/GB"])
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.setStyleSheet(f"background: {self.theme.bg_input}; border: 1px solid {self.theme.border};")
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        # Stretch rows to fill the table height (will be set dynamically in _fill_std_table)

    def update_data(self, current, total, message, data):
        self.p_bar.setMaximum(total)
        self.p_bar.setValue(current)
        self.p_label.setText(message)
        
        if not data: return

        
        # Determine player's league using League enum
        from models import League
        my_team = self.game_state.player_team
        my_league = getattr(my_team, 'league', League.NORTH) if my_team else League.NORTH
        is_north = my_league == League.NORTH
        league_label = "NORTH LEAGUE" if is_north else "SOUTH LEAGUE"
        self.lbl_graph_title.setText(league_label + " RANKING")
        self.lbl_league_title.setText(league_label + " STANDINGS")
        
        # 1. Update Graph (Player League Only)
        if 'rankings' in data:
            # Filter rankings to player's league teams
            filtered_rankings = self._filter_rankings_by_league(data['rankings'], my_league)
            self.graph_view.set_data(filtered_rankings, my_league)
            
        # 2. Update Standings (Player League Only)
        if 'standings_north' in data and 'standings_south' in data:
            my_standings = data['standings_north'] if is_north else data['standings_south']
            self._fill_std_table(self.table_standings, my_standings)
            
        # 3. Update Results (Player Team Only)
        if 'results' in data:
            self._update_player_result(data['results'])
            
        # 4. Update Notifications
        if 'notifications' in data:
            self._update_notifications(data['notifications'])


    def _filter_rankings_by_league(self, rankings, league):
        """Filter rankings dict to only include teams from specified league."""
        from models import League
        # Filter teams by checking each team's league attribute
        target_names = set()
        for team in self.game_state.teams:
            if getattr(team, 'league', None) == league:
                target_names.add(team.name)
        
        filtered = {}
        for date, team_ranks in rankings.items():
            filtered[date] = {team: rank for team, rank in team_ranks.items() if team in target_names}
        return filtered

    def _fill_std_table(self, table, standings):
        num_teams = len(standings)
        table.setRowCount(num_teams)
        
        # Calculate row height to fill the table
        available_height = table.height() - table.horizontalHeader().height() - 4
        row_height = max(20, available_height // max(1, num_teams))
        table.verticalHeader().setDefaultSectionSize(row_height)
        
        games_per_season = 143  # NPB regular season games
        
        # Get 1st place team data
        t1 = None
        t1_wins = 0
        t1_losses = 0
        t1_remaining = 0
        if standings:
            t1_name = standings[0][0]
            t1 = next((t for t in self.game_state.teams if t.name == t1_name), None)
            if t1:
                # Use direct team attributes (wins/losses/draws) not team_record
                t1_wins = t1.wins
                t1_losses = t1.losses
                t1_games = t1_wins + t1_losses + t1.draws
                t1_remaining = games_per_season - t1_games
        
        # Calculate NPB magic number for 1st place
        # NPB勝率計算: 勝率 = 勝利数 / (勝利数 + 敗北数)
        # 自力優勝消滅の判定:
        #   対象チームの最大勝率 (残り全勝想定) < 1位の最終勝率
        #   1位の最終勝率 = 対象チームとの直接対決は全敗、その他は全勝想定
        # マジック点灯: 1位以外の全チームの自力優勝が消滅している時のみ
        magic = None
        champion = False
        show_magic = False
        
        def calc_win_rate(wins, losses):
            """NPB勝率計算: 勝利/(勝利+敗北)"""
            total = wins + losses
            if total == 0:
                return 0.5  # No games played yet
            return wins / total
        
        def get_remaining_matchups(team1_name, team2_name):
            """Get number of remaining games between two teams"""
            if not self.game_state.schedule_engine:
                return 0
            count = 0
            current_date = self.game_state.current_date
            for game in self.game_state.schedule_engine.schedule.games:
                if game.date > current_date and game.status == GameStatus.SCHEDULED:
                    if (game.home_team_name == team1_name and game.away_team_name == team2_name) or \
                       (game.home_team_name == team2_name and game.away_team_name == team1_name):
                        count += 1
            return count
        
        if len(standings) >= 2 and t1:
            all_eliminated = True  # 全チーム自力優勝消滅か
            magic_target_wins = 0  # マジック対象チームの最大勝利数
            magic_target_losses = 0  # マジック対象チームの敗北数
            
            # 1位チームの残り試合数
            t1_remaining = games_per_season - t1_games
            
            for j, (other_name, _) in enumerate(standings[1:], 1):
                other_team = next((t for t in self.game_state.teams if t.name == other_name), None)
                if other_team:
                    other_wins = other_team.wins
                    other_losses = other_team.losses
                    other_games = other_wins + other_losses + other_team.draws
                    other_remaining = games_per_season - other_games
                    
                    # 対象チームの最大勝率 (残り全勝想定)
                    other_max_wins = other_wins + other_remaining
                    other_max_win_rate = calc_win_rate(other_max_wins, other_losses)
                    
                    # 1位と対象チームの残り直接対決数
                    remaining_h2h = get_remaining_matchups(t1.name, other_name)
                    
                    # 1位の最終勝率 (対象チームとの直接対決は全敗、その他は全勝想定)
                    t1_final_wins = t1_wins + (t1_remaining - remaining_h2h)  # Win all except H2H
                    t1_final_losses = t1_losses + remaining_h2h  # Lose all H2H games
                    t1_final_win_rate = calc_win_rate(t1_final_wins, t1_final_losses)
                    
                    # 自力優勝消滅チェック: 対象の最大勝率 < 1位の最終勝率
                    if other_max_win_rate >= t1_final_win_rate:
                        # このチームはまだ自力優勝可能
                        all_eliminated = False
                    
                    # マジック対象チーム = 残り全勝時に最も勝率が高くなるチーム
                    if other_max_win_rate > calc_win_rate(magic_target_wins, magic_target_losses) or magic_target_wins == 0:
                        magic_target_wins = other_max_wins
                        magic_target_losses = other_losses
            
            # マジック点灯条件: 全チームの自力優勝が消滅
            if all_eliminated and t1_games > 0:
                show_magic = True
                # NPBマジック計算式: 対象チームの最大勝利数 - 1位の勝利数 + 1
                magic = magic_target_wins - t1_wins + 1
                if magic <= 0:
                    champion = True
                    magic = 0



        for i, (name, rank) in enumerate(standings):
            # Column 0: Team name
            item_name = QTableWidgetItem(name)
            item_name.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            if name == self.game_state.player_team.name:
                item_name.setBackground(QColor(self.theme.primary_dark))
            table.setItem(i, 0, item_name)
            
            # Column 1: Magic/GB
            if i == 0:
                # 1st place: show Magic or 優勝
                if champion:
                    item_mgb = QTableWidgetItem("優勝")
                    item_mgb.setForeground(QColor("#FFD700"))  # Gold
                elif show_magic and magic is not None:
                    item_mgb = QTableWidgetItem(f"M{magic}")
                    item_mgb.setForeground(QColor(self.theme.warning))
                else:
                    item_mgb = QTableWidgetItem("-")  # No magic yet (season too early)
            else:
                # Other places: show GB
                curr_team = next((t for t in self.game_state.teams if t.name == name), None)
                if curr_team and t1:
                    curr_wins = curr_team.wins
                    curr_losses = curr_team.losses
                    gb = ((t1_wins - curr_wins) + (curr_losses - t1_losses)) / 2.0
                    item_mgb = QTableWidgetItem(f"{gb:.1f}" if gb > 0 else "0.0")
                else:
                    item_mgb = QTableWidgetItem("-")

            
            item_mgb.setTextAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            table.setItem(i, 1, item_mgb)




    def _update_player_result(self, games):
        """Update player team result card only."""
        # Block updates during layout changes for synchronized display
        self.player_result_card.setUpdatesEnabled(False)
        
        # Clear existing layout
        while self.player_result_layout.count():
            item = self.player_result_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        my_team = self.game_state.player_team.name
        my_game = None
        for game in games:
            if game.home_team_name == my_team or game.away_team_name == my_team:
                my_game = game
                break
        
        if not my_game:
            self.player_result_card.setStyleSheet("")  # Reset style
            lbl = QLabel("本日は試合なし")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 14px; border: none;")
            self.player_result_layout.addWidget(lbl)
            self.player_result_card.setUpdatesEnabled(True)
            return

        
        # Check for rain cancellation first
        is_cancelled = my_game.status == GameStatus.CANCELLED
        
        if is_cancelled:
            # Rain cancellation - Blue background
            bg = "#1a3a5a"; border_color = "#2196F3"; status_color = "#2196F3"
            self.player_result_card.setStyleSheet(f"background-color: {bg}; border: 2px solid {border_color};")
            
            # Matchup Label
            opponent = my_game.away_team_name if my_game.home_team_name == my_team else my_game.home_team_name
            location = "vs" if my_game.home_team_name == my_team else "@"
            lbl_matchup = QLabel(f"{location} {opponent[:6]}")
            lbl_matchup.setAlignment(Qt.AlignCenter)
            lbl_matchup.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 11px; border: none;")
            self.player_result_layout.addWidget(lbl_matchup)
            
            # Cancellation Label
            lbl_cancel = QLabel("雨天中止")
            lbl_cancel.setAlignment(Qt.AlignCenter)
            lbl_cancel.setStyleSheet(f"color: {status_color}; font-weight: bold; font-size: 24px; border: none;")
            self.player_result_layout.addWidget(lbl_cancel)
            
            # Sub Label
            lbl_sub = QLabel("RAIN OUT")
            lbl_sub.setAlignment(Qt.AlignCenter)
            lbl_sub.setStyleSheet(f"color: {status_color}; font-weight: 900; font-size: 16px; border: none;")
            self.player_result_layout.addWidget(lbl_sub)
            self.player_result_card.setUpdatesEnabled(True)
            return
        
        # Win/Loss determination
        win = False; draw = False
        if my_game.home_team_name == my_team:
            if my_game.home_score > my_game.away_score: win = True
            elif my_game.home_score == my_game.away_score: draw = True
        else:
            if my_game.away_score > my_game.home_score: win = True
            elif my_game.away_score == my_game.home_score: draw = True
        
        # Color based on result
        if win: bg = "#1a3a1a"; border_color = "#28a745"; status_color = "#28a745"
        elif draw: bg = "#3a3a3a"; border_color = "#6c757d"; status_color = "#6c757d"
        else: bg = "#3a1a1a"; border_color = "#dc3545"; status_color = "#dc3545"
        
        self.player_result_card.setStyleSheet(f"background-color: {bg}; border: 2px solid {border_color};")
        
        # Matchup Label
        lbl_matchup = QLabel(f"{my_game.away_team_name[:6]} vs {my_game.home_team_name[:6]}")
        lbl_matchup.setAlignment(Qt.AlignCenter)
        lbl_matchup.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 11px; border: none;")
        self.player_result_layout.addWidget(lbl_matchup)
        
        # Score Label
        lbl_score = QLabel(f"{my_game.away_score} - {my_game.home_score}")
        lbl_score.setAlignment(Qt.AlignCenter)
        lbl_score.setStyleSheet(f"color: {self.theme.text_primary}; font-weight: bold; font-size: 24px; border: none;")
        self.player_result_layout.addWidget(lbl_score)
        
        # Result Label
        res_text = "WIN" if win else ("DRAW" if draw else "LOSE")
        lbl_res = QLabel(res_text)
        lbl_res.setAlignment(Qt.AlignCenter)
        lbl_res.setStyleSheet(f"color: {status_color}; font-weight: 900; font-size: 16px; border: none;")
        self.player_result_layout.addWidget(lbl_res)
        
        # Pitcher Results (if available)
        pitcher_result = getattr(my_game, 'pitcher_result', None)
        if pitcher_result:
            pitcher_info = []
            if pitcher_result.get('win'):
                pitcher_info.append(f"○{pitcher_result['win']}")
            if pitcher_result.get('lose') or pitcher_result.get('loss'):
                lose_name = pitcher_result.get('lose') or pitcher_result.get('loss')
                pitcher_info.append(f"●{lose_name}")
            if pitcher_result.get('save'):
                pitcher_info.append(f"S{pitcher_result['save']}")
            if pitcher_info:
                lbl_pitcher = QLabel(" ".join(pitcher_info))
                lbl_pitcher.setAlignment(Qt.AlignCenter)
                lbl_pitcher.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 10px; border: none;")
                self.player_result_layout.addWidget(lbl_pitcher)
        
        
        # Re-enable updates
        self.player_result_card.setUpdatesEnabled(True)



    def _update_notifications(self, notifications):
        """Update notification area with trade, injury, etc."""
        # Clear existing notifications
        while self.notification_list.count():
            item = self.notification_list.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        
        if not notifications:
            lbl = QLabel("新しい通知はありません")
            lbl.setStyleSheet(f"color: {self.theme.text_muted}; font-size: 10px;")
            self.notification_list.addWidget(lbl)
            return
        
        for notif in notifications[-5:]:  # Last 5 notifications
            notif_card = QFrame()
            notif_card.setStyleSheet(f"background-color: {self.theme.bg_card_elevated}; border: 1px solid {self.theme.border};")
            nl = QHBoxLayout(notif_card)
            nl.setContentsMargins(4, 2, 4, 2)
            
            # Icon based on type
            icon_text = "i"  # Default info
            notif_type = notif.get('type', '') if isinstance(notif, dict) else ''
            if notif_type == 'injury': icon_text = "!"
            elif notif_type == 'trade': icon_text = "T"
            elif notif_type == 'news': icon_text = "N"
            
            lbl_icon = QLabel(icon_text)
            lbl_icon.setStyleSheet(f"color: {self.theme.text_accent}; font-weight: bold;")
            nl.addWidget(lbl_icon)
            
            msg = notif.get('message', str(notif)) if isinstance(notif, dict) else str(notif)
            lbl_msg = QLabel(msg)
            lbl_msg.setWordWrap(True)
            lbl_msg.setStyleSheet(f"color: {self.theme.text_secondary}; font-size: 10px;")
            nl.addWidget(lbl_msg, 1)
            
            self.notification_list.addWidget(notif_card)


class RankingGraphWidget(QWidget):
    """順位推移グラフ"""
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.rankings_history = {} # {date: {team: rank}}
        self.target_league = None # 表示対象リーグ
        
        # NPB Team Colors
        self.team_colors = {
            "Tokyo Bravers": "#002569", # Chunichi Blue
            "Nagoya Sparks": "#F97709", # Giants Orange
            "Chiba Mariners": "#0055A5", # DeNA Blue
            "Sapporo Fighters": "#F6C900", # Tigers Yellow
            "Osaka Thunders": "#FF0000", # Carp Red
            "Hiroshima Phoenix": "#072C58", # Yakult Navy
            "Fukuoka Phoenix": "#F9C304", # Softbank Yellow
            "Sendai Flames": "#860010", # Rakuten Crimson
            "Yokohama Mariners": "#006298", # Nippon-Ham Blue/Gold
            "Saitama Bears": "#1F366A", # Seibu Blue
            "Kobe Buffaloes": "#000019", # Orix Navy
            "Shinjuku Spirits": "#333333", # Lotte Black
        }
        
    def set_data(self, history, league=None):
        # 直近10日分のみ保持・描画
        sorted_dates = sorted(history.keys())
        recent_dates = sorted_dates[-10:]
        
        self.rankings_history = {d: history[d] for d in recent_dates}
        self.target_league = league
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(self.theme.bg_dark))
        
        if not self.rankings_history:
            return
            
        dates = sorted(self.rankings_history.keys())
        if not dates: return
        
        # チームフィルタリング (リーグ)
        # 最初の日のデータを使ってリーグフィルタリングする (履歴内でチームが変わることはないと仮定)
        first_day_data = self.rankings_history[dates[0]]
        active_teams = list(first_day_data.keys())
        
        # 座標計算 - Align with table (account for table header)
        w = self.width(); h = self.height()
        # Top margin increased more to align with table rows
        margin_x = 40
        margin_top = 55  # Increased further for better alignment
        margin_bottom = 5

        
        y_step = (h - (margin_top + margin_bottom)) / 6 # 6位まで
        x_step = (w - 2*margin_x) / max(1, len(dates)-1)
        
        # Draw Guidelines
        painter.setPen(QPen(QColor(self.theme.border), 1, Qt.DashLine))
        for i in range(1, 7):
            y = margin_top + (i-1)*y_step
            painter.drawLine(margin_x, int(y), w - margin_x, int(y))
            painter.drawText(5, int(y)+5, f"{i}位")
            
        # Draw Lines
        for team in active_teams:
            color = QColor(self.team_colors.get(team, "#FFFFFF"))
            pen = QPen(color, 3)
            painter.setPen(pen)
            
            path_points = []
            for i, d in enumerate(dates):
                if team in self.rankings_history[d]:
                    rank = self.rankings_history[d][team]
                    x = margin_x + i * x_step
                    y = margin_top + (rank - 1) * y_step
                    path_points.append(QPoint(int(x), int(y)))
            
            if len(path_points) > 1:
                painter.drawPolyline(path_points)
                # Draw team name at the end
                painter.drawText(path_points[-1] + QPoint(5, 5), team[:3])

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
        from PySide6.QtWidgets import QComboBox
        
        panel = QWidget(); panel.setStyleSheet(f"background-color: {self.theme.bg_dark};")
        layout = QVBoxLayout(panel); layout.setContentsMargins(20, 20, 10, 20)
        lbl = QLabel("SEASON SCHEDULE"); lbl.setStyleSheet(f"font-size: 24px; font-weight: 800; color: {self.theme.text_primary}; letter-spacing: 2px;")
        layout.addWidget(lbl)
        
        # カスタムナビゲーション（年・月選択）
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(10)
        
        # 年ドロップダウン（2027〜現在のゲーム年）
        self.year_combo = QComboBox()
        self.year_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                font-weight: bold;
                min-width: 100px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.theme.bg_card};
                color: {self.theme.text_primary};
                selection-background-color: {self.theme.primary};
            }}
        """)
        # 初期値（後でset_game_stateで更新）
        self.year_combo.addItem("2027", 2027)
        self.year_combo.currentIndexChanged.connect(self._on_year_month_changed)
        nav_layout.addWidget(self.year_combo)
        
        # 月ドロップダウン（3月〜11月のみ）
        self.month_combo = QComboBox()
        self.month_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {self.theme.bg_input};
                color: {self.theme.text_primary};
                border: 1px solid {self.theme.border};
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
                font-weight: bold;
                min-width: 80px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.theme.bg_card};
                color: {self.theme.text_primary};
                selection-background-color: {self.theme.primary};
            }}
        """)
        # 3月〜11月のみ追加
        month_names = ["", "", "", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月"]
        for m in range(3, 12):  # 3〜11月
            self.month_combo.addItem(month_names[m], m)
        self.month_combo.currentIndexChanged.connect(self._on_year_month_changed)
        nav_layout.addWidget(self.month_combo)
        
        nav_layout.addStretch()
        layout.addLayout(nav_layout)
        
        # 現在表示中の年月ラベル
        self.current_ym_label = QLabel("2027年 3月")
        self.current_ym_label.setStyleSheet(f"""
            font-size: 28px;
            font-weight: bold;
            color: {self.theme.text_primary};
            padding: 10px 0;
        """)
        self.current_ym_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.current_ym_label)
        
        # カレンダーウィジェット
        self.calendar = GameCalendarWidget()
        self.calendar.setNavigationBarVisible(False)  # デフォルトナビゲーションを非表示
        
        # カレンダーを3月〜11月のみに制限
        current_year = 2027  # デフォルト（後でゲーム年で更新）
        self.calendar.setMinimumDate(QDate(current_year, 3, 1))  # 3月1日
        self.calendar.setMaximumDate(QDate(current_year, 11, 30))  # 11月30日
        
        self.calendar.clicked.connect(self._on_date_selected)
        self.calendar.clicked.connect(self._on_calendar_page_changed)  # クリック時にラベル更新
        self.calendar.currentPageChanged.connect(self._on_calendar_page_changed)  # ページ変更時にラベル更新
        self.calendar.activated.connect(self._on_date_double_clicked)  # Double-click
        layout.addWidget(self.calendar)
        return panel
    
    def _on_calendar_page_changed(self, arg1=None, arg2=None):
        """カレンダーのページ変更時（スクロール、クリック等）にラベルを更新
        
        currentPageChanged: (int year, int month)
        clicked: (QDate date)
        """
        # 引数の型を判定
        if isinstance(arg1, QDate):
            # clicked シグナルから呼ばれた場合
            year = arg1.year()
            month = arg1.month()
        elif arg1 is not None and arg2 is not None:
            # currentPageChanged シグナルから呼ばれた場合
            year = arg1
            month = arg2
        else:
            # 引数なしの場合はカレンダーから取得
            current_date = self.calendar.selectedDate()
            year = current_date.year()
            month = current_date.month()
        
        # ラベルを更新
        self.current_ym_label.setText(f"{year}年 {month}月")
        
        # ドロップダウンも同期（シグナルをブロックして無限ループ防止）
        self.year_combo.blockSignals(True)
        self.month_combo.blockSignals(True)
        
        year_index = self.year_combo.findData(year)
        if year_index >= 0:
            self.year_combo.setCurrentIndex(year_index)
        
        month_index = self.month_combo.findData(month)
        if month_index >= 0:
            self.month_combo.setCurrentIndex(month_index)
        
        self.year_combo.blockSignals(False)
        self.month_combo.blockSignals(False)
    
    def _on_year_month_changed(self):
        """年・月ドロップダウン変更時の処理"""
        year = self.year_combo.currentData()
        month = self.month_combo.currentData()
        if year and month:
            # 年月ラベルを更新
            self.current_ym_label.setText(f"{year}年 {month}月")
            
            # カレンダーの日付範囲を選択した年に更新
            self.calendar.setMinimumDate(QDate(year, 3, 1))  # 3月1日
            self.calendar.setMaximumDate(QDate(year, 11, 30))  # 11月30日
            
            # カレンダーを選択した年月に移動
            self.calendar.setSelectedDate(QDate(year, month, 1))
            self.calendar.setCurrentPage(year, month)

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
        
        # オフシーズンモード検出
        is_offseason = getattr(game_state, 'is_offseason', False)
        
        if is_offseason:
            self._setup_offseason_schedule(game_state)
            return
        
        # 通常シーズンモード：カレンダーを復元
        self._restore_regular_season_view()
        
        if hasattr(game_state, 'current_date'):
            try:
                y, m, d = map(int, game_state.current_date.split('-'))
                
                # 年ドロップダウンを更新（2027〜現在のゲーム年）
                self.year_combo.blockSignals(True)
                self.year_combo.clear()
                for year in range(2027, y + 1):
                    self.year_combo.addItem(str(year), year)
                # 現在の年を選択
                year_index = self.year_combo.findData(y)
                if year_index >= 0:
                    self.year_combo.setCurrentIndex(year_index)
                self.year_combo.blockSignals(False)
                
                # 月ドロップダウンで現在の月を選択（3〜11月のみ有効）
                self.month_combo.blockSignals(True)
                month_index = self.month_combo.findData(m)
                if month_index >= 0:
                    self.month_combo.setCurrentIndex(month_index)
                else:
                    # 範囲外の月の場合は3月を選択
                    self.month_combo.setCurrentIndex(0)
                self.month_combo.blockSignals(False)
                
                # 年月ラベルを更新
                display_month = m if m >= 3 and m <= 11 else 3
                self.current_ym_label.setText(f"{y}年 {display_month}月")
                
                # カレンダーの日付範囲をゲーム年の3月〜11月に設定
                self.calendar.setMinimumDate(QDate(y, 3, 1))  # 3月1日
                self.calendar.setMaximumDate(QDate(y, 11, 30))  # 11月30日
                self.calendar.setSelectedDate(QDate(y, m, d)); self.selected_date = QDate(y, m, d)
            except: pass
        self._refresh_calendar_data(); self._refresh_info_panel()
    
    def _restore_regular_season_view(self):
        """通常シーズン表示に戻す（オフシーズンから復帰時）"""
        # カレンダーを表示
        self.calendar.show()
        
        # 年月ドロップダウンを表示
        if hasattr(self, 'year_combo'):
            self.year_combo.show()
        if hasattr(self, 'month_combo'):
            self.month_combo.show()
        
        # オフシーズン予定表を非表示
        if hasattr(self, 'offseason_schedule_widget'):
            self.offseason_schedule_widget.hide()
    
    def _setup_offseason_schedule(self, game_state):
        """オフシーズンスケジュールの表示設定"""
        # ヘッダーを更新
        self.current_ym_label.setText("🏆 OFFSEASON SCHEDULE")
        
        # カレンダーを非表示
        self.calendar.hide()
        
        # 年月ドロップダウンを非表示
        if hasattr(self, 'year_combo'):
            self.year_combo.hide()
        if hasattr(self, 'month_combo'):
            self.month_combo.hide()
        
        # オフシーズン予定表ウィジェットを作成（なければ）
        if not hasattr(self, 'offseason_schedule_widget'):
            self._create_offseason_schedule_widget()
        
        # オフシーズン予定表を表示
        self.offseason_schedule_widget.show()
        
        # オフシーズンスケジュールを取得して更新
        self._update_offseason_schedule_display(game_state)
        
        # Info panel にオフシーズン情報を表示
        current_phase = ""
        if hasattr(game_state, 'get_current_offseason_phase'):
            current_phase = game_state.get_current_offseason_phase()
        
        self.matchup_label.setText("🌟 オフシーズン")
        self.score_label.setText(f"{current_phase}" if current_phase else "---")
        self.status_label.setText("ホームタブから次のイベントへ進めます")
    
    def _create_offseason_schedule_widget(self):
        """オフシーズン予定表ウィジェットを作成"""
        from PySide6.QtWidgets import QScrollArea
        
        # スクロールエリア
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background: {self.theme.bg_card};
                border-radius: 12px;
            }}
        """)
        
        # コンテナ
        container = QWidget()
        container.setStyleSheet(f"background: {self.theme.bg_card};")
        self.offseason_events_layout = QVBoxLayout(container)
        self.offseason_events_layout.setContentsMargins(20, 20, 20, 20)
        self.offseason_events_layout.setSpacing(10)
        
        scroll.setWidget(container)
        
        # カレンダーの親レイアウトに追加
        if self.calendar.parent():
            parent_layout = self.calendar.parent().layout()
            if parent_layout:
                parent_layout.addWidget(scroll)
        
        self.offseason_schedule_widget = scroll
        self.offseason_schedule_widget.hide()
    
    def _update_offseason_schedule_display(self, game_state):
        """オフシーズン予定表の内容を更新"""
        if not hasattr(self, 'offseason_events_layout'):
            return
        
        # 既存の項目をクリア
        while self.offseason_events_layout.count():
            item = self.offseason_events_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # ヘッダー
        header = QLabel("📅 オフシーズンイベント一覧")
        header.setStyleSheet(f"""
            font-size: 20px;
            font-weight: bold;
            color: {self.theme.text_primary};
            padding: 10px 0;
            background: transparent;
        """)
        self.offseason_events_layout.addWidget(header)
        
        # イベントリスト取得
        offseason_events = []
        if hasattr(game_state, 'get_offseason_schedule'):
            offseason_events = game_state.get_offseason_schedule()
        
        current_phase = None
        if hasattr(game_state, 'offseason_phase'):
            current_phase = game_state.offseason_phase
        
        # 各イベントを表示
        for event_date, phase in offseason_events:
            row = QFrame()
            row.setStyleSheet(f"""
                QFrame {{
                    background: {self.theme.bg_card_elevated if current_phase == phase else 'transparent'};
                    border-radius: 8px;
                    padding: 5px;
                }}
            """)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(15, 12, 15, 12)
            
            # 日付
            date_str = event_date.strftime("%m月%d日") if hasattr(event_date, 'strftime') else str(event_date)
            date_label = QLabel(date_str)
            date_label.setStyleSheet(f"""
                font-size: 14px;
                color: {self.theme.text_secondary};
                background: transparent;
                min-width: 80px;
            """)
            row_layout.addWidget(date_label)
            
            # フェーズ名
            phase_name = phase.value if hasattr(phase, 'value') else str(phase)
            is_current = current_phase and phase == current_phase
            
            phase_label = QLabel(phase_name)
            if is_current:
                phase_label.setStyleSheet(f"""
                    font-size: 16px;
                    font-weight: bold;
                    color: {self.theme.accent_blue};
                    background: transparent;
                """)
            else:
                phase_label.setStyleSheet(f"""
                    font-size: 14px;
                    color: {self.theme.text_primary};
                    background: transparent;
                """)
            row_layout.addWidget(phase_label, 1)
            
            # ステータスアイコン
            if is_current:
                status_label = QLabel("🔵 現在")
                status_label.setStyleSheet(f"""
                    font-size: 12px;
                    color: {self.theme.accent_blue};
                    background: transparent;
                """)
            else:
                status_label = QLabel("⚪")
                status_label.setStyleSheet("background: transparent;")
            row_layout.addWidget(status_label)
            
            self.offseason_events_layout.addWidget(row)
        
        self.offseason_events_layout.addStretch()

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
            
            # Check for rain cancellation
            if target_game.status == GameStatus.CANCELLED:
                self.score_label.setText("雨天中止"); self.status_label.setText("RAIN OUT")
            elif target_game.is_completed:
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

        # 直接シミュレーション開始（詳細設定ダイアログをスキップ）
        self.stop_conditions = {}  # 停止条件なし
        self._start_simulation()



    def _start_simulation(self):
        # 新しい拡張ダイアログを使用
        self.progress_dialog = SimulationProgressDialog(self, self.game_state)
        # キャンセルボタンの接続はSimulationProgressDialog内で行われるが、ここからworkerを操作するためにコールバックが必要かも
        # あるいはprogress_dialogのcancel_btnをクリックしたら self._cancel_simulation を呼ぶ
        self.progress_dialog.cancel_btn.clicked.connect(self._cancel_simulation)
        
        # stop_conditionsを渡す
        conditions = getattr(self, 'stop_conditions', {})
        self.worker = SimulationWorker(self.game_state, self.selected_date, conditions, parent=self)
        self.worker.progress_updated.connect(self._update_progress)
        self.worker.day_advanced.connect(self._on_day_advanced)  # Handle in main thread
        self.worker.finished.connect(self._on_simulation_finished)
        self.worker.error_occurred.connect(self._on_simulation_error)
        self.worker.start()
        
        # ▼▼▼ 修正: exec()の戻り値で処理を分岐し、二重表示を防ぐ ▼▼▼
        # ダイアログが閉じられるまでここでブロックされる
        result = self.progress_dialog.exec()
        
        # Always refresh calendar (to show rain postponements, completed games, etc.)
        self._refresh_calendar_data()
        self._refresh_info_panel()
        
        if result == QDialog.Accepted:
            QMessageBox.information(self, "完了", "指定日までの日程消化が完了しました。")
        # ▲▲▲ 修正終了 ▲▲▲


    def _update_progress(self, current, total, message, data=None): # data引数追加
        if hasattr(self, 'progress_dialog') and isinstance(self.progress_dialog, SimulationProgressDialog):
            self.progress_dialog.update_data(current, total, message, data)
        else: # Fallback for old dialog if any
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

class SkipOptionsDialog(QDialog):
    """スキップ詳細設定ダイアログ"""
    def __init__(self, target_date, parent=None):
        super().__init__(parent)
        self.setWindowTitle("シミュレーション詳細設定")
        self.theme = get_theme()
        self.setStyleSheet(f"background-color: {self.theme.bg_card}; color: {self.theme.text_primary};")
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"{target_date.toString('yyyy/MM/dd')} までスキップします。"))
        layout.addWidget(QLabel("以下の条件で停止しますか？"))
        
        self.chk_season_end = QCheckBox("レギュラーシーズン終了時")
        self.chk_season_end.setChecked(True)
        self.chk_season_end.setStyleSheet(f"color: {self.theme.text_primary};")
        layout.addWidget(self.chk_season_end)
        
        self.chk_injury = QCheckBox("自チーム選手に怪我が発生した場合")
        self.chk_injury.setChecked(True)
        self.chk_injury.setStyleSheet(f"color: {self.theme.text_primary};")
        layout.addWidget(self.chk_injury)
        
        self.chk_trade = QCheckBox("トレードの結果が出た場合")
        self.chk_trade.setChecked(True)
        self.chk_trade.setStyleSheet(f"color: {self.theme.text_primary};")
        layout.addWidget(self.chk_trade)
        
        btns = QHBoxLayout()
        ok_btn = QPushButton("実行")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setStyleSheet(f"background-color: {self.theme.primary}; color: {self.theme.text_highlight}; padding: 6px 12px; border-radius: 4px;")
        
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet(f"background-color: {self.theme.bg_input}; color: {self.theme.text_primary}; padding: 6px 12px; border-radius: 4px;")
        
        btns.addWidget(cancel_btn)
        btns.addWidget(ok_btn)
        layout.addLayout(btns)
        
    def get_conditions(self):
        return {
            "season_end": self.chk_season_end.isChecked(),
            "injury": self.chk_injury.isChecked(),
            "trade": self.chk_trade.isChecked()
        }