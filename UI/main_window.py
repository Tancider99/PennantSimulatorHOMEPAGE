# -*- coding: utf-8 -*-
"""
Pennant Simulator 2027 - Main Window
Professional Main Interface with Premium Features
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QApplication, QSplashScreen, QMessageBox,
    QMenu, QMenuBar, QSystemTrayIcon, QSizeGrip
)
from PySide6.QtCore import Qt, QTimer, Signal, QSize, QSettings, QPoint
from PySide6.QtGui import QIcon, QPixmap, QFont, QAction, QKeySequence, QScreen

import sys
import os
import random

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from UI.theme import ThemeManager, get_theme
from UI.widgets.panels import SidebarPanel, HeaderPanel, StatusPanel, PageContainer
from UI.widgets.buttons import ActionButton
from farm_game_simulator import simulate_farm_games_for_day
from models import GameStatus
# from UI.dialogs.game_result_dialog import GameResultDialog # No longer used
from UI.pages.game_result_page import GameResultPage


class MainWindow(QMainWindow):
    """Main application window with custom layout and resizable features"""

    # Signals
    fullscreen_changed = Signal(bool)
    window_size_changed = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.theme = get_theme()
        self.game_state = None
        self.settings = QSettings("PennantSim", "PennantSimulator")
        
        # Navigation State
        self.current_section = "home"
        self.previous_section = "home"

        # ページインスタンスのキャッシュ（永続化が必要なページ用）
        self.persistent_pages = {}
        # ★追加: 自動生成されたページのキャッシュ用セット
        # インスタンスを保持するように辞書に変更
        self.cached_pages = {} 

        self._setup_window()
        self._setup_ui()
        self._setup_connections()
        self._setup_shortcuts()
        self._restore_window_state()

        # Start with home page
        self._navigate_to("home")

    def _setup_window(self):
        """Configure main window properties"""
        self.setWindowTitle("Pennant Simulator 2027")
        self.setMinimumSize(1024, 600)
        self.resize(1600, 1000)
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint |
            Qt.WindowCloseButtonHint
        )
        self._center_on_screen()

    def _center_on_screen(self):
        """Center window on the primary screen"""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

    def _setup_ui(self):
        """Create the main UI layout"""
        # Main container widget
        main_container = QWidget()
        main_container.setStyleSheet(f"background-color: {self.theme.bg_dark};") # 背景色設定
        self.setCentralWidget(main_container)

        main_layout = QHBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar navigation
        self.sidebar = self._create_sidebar()
        main_layout.addWidget(self.sidebar)

        # Main content area
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Page container
        self.pages = PageContainer()
        self._create_persistent_pages() # 永続ページの作成
        content_layout.addWidget(self.pages)

        # Status bar
        self.status = StatusPanel()
        content_layout.addWidget(self.status)

        main_layout.addWidget(content_area)

    def _create_sidebar(self) -> SidebarPanel:
        """Create the navigation sidebar"""
        sidebar = SidebarPanel()

        # HOME, ROSTER, ORDER
        sidebar.add_nav_item("", "HOME", "home")
        sidebar.add_nav_item("", "ROSTER", "roster")
        sidebar.add_nav_item("", "ORDER", "order")

        # SEASON
        sidebar.add_separator("SEASON")
        sidebar.add_nav_item("", "SCHEDULE", "schedule")
        # STANDINGS removed
        sidebar.add_nav_item("", "STATS", "stats")

        # MANAGEMENT
        sidebar.add_separator("MANAGEMENT")
        sidebar.add_nav_item("", "FARM", "farm_swap")
        sidebar.add_nav_item("", "CONTRACTS", "contract_changes")
        sidebar.add_nav_item("", "ACQUISITIONS", "reinforcement")
        sidebar.add_nav_item("", "TRAINING", "training")

        # BUSINESS
        sidebar.add_separator("BUSINESS")
        sidebar.add_nav_item("", "STAFF", "staff")
        sidebar.add_nav_item("", "FINANCE", "finance")

        # SYSTEM
        sidebar.add_separator("SYSTEM")
        sidebar.add_nav_item("", "SAVE / LOAD", "save_load")
        sidebar.add_nav_item("", "SETTINGS", "settings")
        sidebar.add_nav_item("", "TITLE", "title")

        sidebar.navigation_clicked.connect(self._on_sidebar_nav)

        return sidebar

    def _on_sidebar_nav(self, section: str):
        if section == "title":
            self.pages.show_page("title")
        else:
            self._navigate_to(section)

    def _create_persistent_pages(self):
        """Create pages that should persist across navigation"""
        from UI.pages.player_detail_page import PlayerDetailPage
        
        # Player Detail Page
        self.player_detail_page = PlayerDetailPage(self)
        # Connect back signal to dynamic handler
        self.player_detail_page.back_requested.connect(self._on_player_detail_back)
        # ★追加: 詳細統計ボタンのシグナル接続
        self.player_detail_page.detail_stats_requested.connect(self._show_player_stats_detail)
        
        self.pages.add_page("player_detail", self.player_detail_page)
        self.persistent_pages["player_detail"] = self.player_detail_page

    def _create_page_instance(self, section: str):
        """Create a new instance of a page based on section name (Factory Method)"""
        # Lazy imports to avoid circular dependencies and heavy startup
        from UI.pages.home_page import HomePage
        from UI.pages.roster_page import RosterPage
        from UI.pages.schedule_page import SchedulePage
        from UI.pages.stats_page import StatsPage
        from UI.pages.settings_page import SettingsPage
        from UI.pages.order_page import OrderPage
        from UI.pages.farm_swap_page import FarmSwapPage
        from UI.pages.tv_broadcast_game_page import TVBroadcastGamePage  # TV中継風ゲームページ
        from UI.pages.contracts_page import ContractsPage # ContractsPageをインポート
        from UI.pages.pre_game_page import PreGamePage # ★追加
        from UI.pages.acquisitions_page import AcquisitionsPage # ★追加: 補強ページ

        
        page = None
        
        if section == "home":
            page = HomePage(self)
            page.game_requested.connect(self._on_game_requested)
            page.view_roster_requested.connect(lambda: self._navigate_to("roster"))
            page.player_detail_requested.connect(self._show_player_detail)
            self.home_page = page 
            
        elif section == "roster":
            page = RosterPage(self)
            # Roster needs to connect to the persistent player detail page
            page.show_player_detail_requested = lambda p: self._show_player_detail(p)
            self.roster_page = page
            
        elif section == "order":
            page = OrderPage(self)
            page.order_saved.connect(self._on_order_saved)
            # 修正: 選手詳細シグナルをメインウィンドウのメソッドに接続
            page.player_detail_requested.connect(self._show_player_detail)
            self.order_page = page

        elif section == "schedule":
            self.schedule_page = SchedulePage(self)
            # Link contracts_page for scouting progress during bulk skip
            if hasattr(self, 'contracts_page') and self.contracts_page:
                self.schedule_page.contracts_page = self.contracts_page
            page = self.schedule_page 

        elif section == "stats":
            self.stats_page = StatsPage(self)
            # 修正: スタッツページからの選手詳細リクエストを接続
            self.stats_page.player_detail_requested.connect(self._show_player_detail)
            page = self.stats_page

        elif section == "farm_swap":  # 追加
            page = FarmSwapPage(self)
            # ★追加: 選手詳細シグナルをメインウィンドウのメソッドに接続
            page.player_detail_requested.connect(self._show_player_detail)
            self.farm_swap_page = page
            
        elif section == "game": # TV中継風ゲームページ
            page = TVBroadcastGamePage(self)
            page.game_finished.connect(self._on_game_finished)
            if hasattr(page, 'go_to_player_detail'):
                page.go_to_player_detail.connect(self._show_player_detail)
            self.game_page = page # 属性として保持
            
        elif section == "contract_changes": # ★追加: 契約ページ
            page = ContractsPage(self)
            # 選手詳細画面への遷移シグナルを接続 (ContractsPageから飛べるように)
            if hasattr(page, 'go_to_player_detail'):
                page.go_to_player_detail.connect(self._show_player_detail)
            if hasattr(page, 'go_to_player_detail'):
                page.go_to_player_detail.connect(self._show_player_detail)
            self.contracts_page = page

        elif section == "game_result": # ★追加: 試合結果ページ
            page = GameResultPage(self)
            page.return_home.connect(lambda: self._navigate_to("home"))
            self.game_result_page = page

        elif section == "pre_game": # ★追加: 試合前確認ページ
            page = PreGamePage(self)
            page.start_game_requested.connect(self._on_pre_game_start)
            page.edit_order_requested.connect(self._on_edit_order_requested)
            # 詳細画面への遷移シグナルを接続
            page.player_detail_requested.connect(self._show_player_detail)
            self.pre_game_page = page

        elif section == "reinforcement":
            page = AcquisitionsPage(self)
            if hasattr(page, 'player_detail_requested'):
                page.player_detail_requested.connect(self._show_player_detail)
            self.acquisitions_page = page

        elif section == "training":
            from UI.pages.training_page import TrainingPage
            page = TrainingPage(self)
            page.training_saved.connect(self._on_training_saved)
            if hasattr(page, 'player_detail_requested'):
                page.player_detail_requested.connect(self._show_player_detail)
            self.training_page = page
        
        # Unimplemented pages (kept for code reference but not in sidebar)
            
        elif section == "settings":
            page = SettingsPage(self)
            page.settings_changed.connect(self._on_settings_changed)
            self.settings_page = page

        # New sidebar items (farm_swap, contract_changes, reinforcement, staff, finance, save_load)
        # are currently unimplemented and return None.

        return page

    def _create_placeholder(self, name: str) -> QWidget:
        """Create a placeholder page"""
        from UI.widgets.panels import ContentPanel
        from PySide6.QtWidgets import QLabel

        page = ContentPanel()
        label = QLabel(f"{name}\n\nCOMING SOON")
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"""
            font-size: 24px;
            font-weight: 300;
            letter-spacing: 2px;
            color: {self.theme.text_muted};
        """)
        page.add_widget(label)
        return page

    def _setup_connections(self):
        """Set up global signal connections"""
        self.pages.page_changed.connect(self._on_page_changed)

    def _on_game_requested(self):
        """Handle game request from home page"""
        if not self.game_state:
            return

        # プレイヤーチーム
        player_team = self.game_state.player_team
        
        # 有効性チェック
        valid_starters = len([x for x in player_team.current_lineup if x != -1])
        valid_rotation = len([x for x in player_team.rotation if x != -1])
        
        if valid_starters < 9:
            QMessageBox.critical(self, "エラー", f"チーム {player_team.name} のスタメンが9人未満です。\nオーダー画面で設定してください。")
            return
        if valid_rotation == 0:
            QMessageBox.critical(self, "エラー", f"チーム {player_team.name} の先発投手が設定されていません。\nオーダー画面で設定してください。")
            return

        # 【修正】ランダムではなく、その日のスケジュールから対戦相手を取得する
        today_games = self.game_state.get_today_games()
        target_game = None
        
        # 自チームの試合を探す
        for g in today_games:
            if g.home_team_name == player_team.name or g.away_team_name == player_team.name:
                target_game = g
                break
        
        if target_game:
            # 予定通りの試合を開始
            home_team = next((t for t in self.game_state.teams if t.name == target_game.home_team_name), None)
            away_team = next((t for t in self.game_state.teams if t.name == target_game.away_team_name), None)
            
            if home_team and away_team:
                # 相手チームのロースター自動修正（念のため）
                opponent = away_team if home_team == player_team else home_team
                opponent.auto_assign_rosters()
                opponent.auto_set_bench()
                
                self.show_pre_game(home_team, away_team) # 修正: 直接試合開始ではなくPreGameへ
            else:
                QMessageBox.warning(self, "エラー", "対戦チームデータが見つかりませんでした。")
        else:
            # 試合がない場合 -> 二軍戦などを消化して日付を進める
            # ★追加: 二軍・三軍試合のシミュレーション
            try:
                simulate_farm_games_for_day(self.game_state.teams, self.game_state.current_date)
            except Exception as e:
                print(f"Farm Simulation Error: {e}")

            # Create contracts_page if not yet navigated to
            if not hasattr(self, 'contracts_page') or not self.contracts_page:
                from UI.pages.contracts_page import ContractsPage
                self.contracts_page = ContractsPage(self)
                if hasattr(self.contracts_page, 'go_to_player_detail'):
                    self.contracts_page.go_to_player_detail.connect(self._show_player_detail)
            self.contracts_page.advance_day()

            self.game_state.finish_day_and_advance()
            
            # 画面更新 (Refresh current page)
            current_page = self.pages.currentWidget()
            if current_page and hasattr(current_page, 'set_game_state'):
                current_page.set_game_state(self.game_state)
            
            # ステータスバー更新
            self._on_page_changed(0)
            
            QMessageBox.information(self, "日程進行", "本日は試合がありませんでした。次の日へ進みます。")

    def show_pre_game(self, home_team, away_team):
        """Show pre-game confirmation page"""
        self._navigate_to("pre_game")
        self.pre_game_page.set_teams(home_team, away_team)
    
    def _on_pre_game_start(self, params):
        """Handle start/skip from pre-game page"""
        mode = params.get("mode")
        home = self.pre_game_page.home_team
        away = self.pre_game_page.away_team
        
        if mode == "manual":
            self.show_game(home, away)
        elif mode == "fast":
            self._simulate_fast_forward_game(home, away)

    def _on_edit_order_requested(self, team=None):
        """Handle request to edit a team's order"""
        if not team: return
        self._navigate_to("order")
        # OrderPageに特定のチームを表示させるハック
        # 通常は game_state.player_team を表示するが、ここでは一時的に上書き
        if hasattr(self, 'order_page') and self.order_page:
            self.order_page.current_team = team
            self.order_page.team_name_label.setText(team.name)
            self.order_page._load_team_data()
            self.order_page._refresh_all()
            # 戻るボタン的なものがないので、ナビゲーションで戻る必要がある
            # ここではシンプルにOrderPageへ飛ばすだけ（再度PreGameに戻るのはユーザー操作）

    def _simulate_fast_forward_game(self, home_team, away_team):
        """Simulate game headlessly and go to results"""
        from live_game_engine import LiveGameEngine, PlayResult
        
        # UIをブロックしないようにしたいが、簡単のため同期実行 (Fast forward is fast enough usually)
        from models import TeamLevel
        engine = LiveGameEngine(home_team, away_team, TeamLevel.FIRST)
        
        # Track Stats
        score_history = {"top": [], "bot": []}
        hr_list = []
        
        # State tracking for line score
        prev_inning = 1
        prev_is_top = True
        scores_at_inning_start = { "home": 0, "away": 0 }
        
        def record_inning_score(inning, is_top, current_home, current_away):
            # Previous half-inning ended. Record its score.
            # If current is Top 2, then Bot 1 ended.
            # If current is Bot 1, then Top 1 ended.
            
            # Identify which half-inning justify ended
            if is_top: 
                # Top of new inning -> Bottom of previous inning ended
                # prev_inning was same as (inning - 1) usually
                target_key = "bot"
                # Runs scored by Home Team
                runs = current_home - scores_at_inning_start["home"]
                # Ensure list is long enough
                while len(score_history["bot"]) < (inning - 1): score_history["bot"].append(0)
                score_history["bot"].append(runs)
                scores_at_inning_start["home"] = current_home
            else:
                # Bottom of inning -> Top of same inning ended
                target_key = "top"
                # Runs scored by Away Team
                runs = current_away - scores_at_inning_start["away"]
                while len(score_history["top"]) < inning: score_history["top"].append(0)
                score_history["top"].append(runs)
                scores_at_inning_start["away"] = current_away

        # 安全策: 無限ループ防止のため最大300打席程度で切る
        max_steps = 2000 
        steps = 0
        
        while not engine.is_game_over() and steps < max_steps:
            # Capture state before pitch
            curr_inn = engine.state.inning
            curr_top = engine.state.is_top
            
            # Detect Inning Change
            if (curr_inn != prev_inning) or (curr_top != prev_is_top):
                record_inning_score(curr_inn, curr_top, engine.state.home_score, engine.state.away_score)
                prev_inning = curr_inn
                prev_is_top = curr_top
            
            engine.simulate_pitch()
            steps += 1
            
        
            
        # Finalize Last Inning
        # If Game Over at Top 9 3 outs -> Bot 9 not played (if home winning)
        # or Bot 9 3 outs -> End.
        # record_inning_score needs 'next' state. 
        # But engine.state is final.
        # Logic: If game ended after Top 9, we need to record Top 9 score.
        # If game ended after Bot 9, record Bot 9 score.
        
        # If currently Top (meaning Top ended? No, simulate_pitch ends AFTER outcome).
        # If state.outs == 3, inning changes in engine? 
        # engine.is_game_over checks state.
        # If game over, verify if we recorded the last half-inning.
        
        # Simple approach: Calculate final runs for the last active half-inning.
        # If is_top: Away team was batting. Record Top score.
        # If !is_top: Home team was batting. Record Bot score.
        
        # But wait, if X-Game (Home leads, Bot 9 skipped)?
        # Then we justrecord Top 9.
        
        # Just use total score diff
        # Total Away - Sum(score_history['top']) -> Add to Top?
        # Total Home - Sum(score_history['bot']) -> Add to Bot?
        # This is safer than state tracking for the final bit.
        
        sum_top = sum(score_history["top"])
        sum_bot = sum(score_history["bot"])
        
        rem_away = engine.state.away_score - sum_top
        rem_home = engine.state.home_score - sum_bot
        
        if rem_away > 0 or len(score_history["top"]) < engine.state.inning: 
             score_history["top"].append(rem_away)
        
        # Don't append if X-game and already finished?
        # Use simple diff check.
        # Actually simplest: Just append the diff. 
        # If X game (9回表終了時), then Bot 9 didn't happen. rem_home should be 0 (if valid).
        if rem_home != 0 or (not engine.state.is_top and engine.state.outs==3): 
             # If bottom ended
             score_history["bot"].append(rem_home)
        elif engine.state.home_score > engine.state.away_score and engine.state.is_top and engine.state.inning >= 9:
             # X Game: Home team didn't bat separate inning?
             # Or if they batted earlier innings.
             if rem_home > 0: score_history["bot"].append(rem_home)
             else: pass 
            
        # Finalize
        current_date = self.game_state.current_date if self.game_state else "2027-01-01"
        stats_result = engine.finalize_game_stats(current_date)
        
        # Build HR List (Format must be Tuples: Name, Count, TeamName)
        hr_list = []
        if stats_result and "game_stats" in stats_result:
             for p, stats in stats_result["game_stats"].items():
                 if stats.get('home_runs', 0) > 0:
                     # Determine Team Name
                     # Check if player in home/away team objects (safer than lineup indices)
                     t_name = away_team.name # default
                     if any(p.name == hp.name and p.uniform_number == hp.uniform_number for hp in home_team.players):
                         t_name = home_team.name
                     elif any(p.name == ap.name and p.uniform_number == ap.uniform_number for ap in away_team.players):
                         t_name = away_team.name
                     
                     hr_list.append((p.name, stats['home_runs'], t_name))

        # ★追加: Highlight Logging
        if stats_result and "highlights" in stats_result:
            for h in stats_result["highlights"]:
                self.game_state.log_news(
                    category=h['category'],
                    message=h['message'],
                    team_name=h['team']
                )

        result = {
            "home_team": home_team,
            "away_team": away_team,
            "home_score": engine.state.home_score,
            "away_score": engine.state.away_score,
            "game_result": engine.state, 
            "game_stats": stats_result.get("game_stats", {}),
            "score_history": score_history,
            "home_runs": hr_list,
            "pitcher_result": {
                "win": stats_result.get("win"),
                "loss": stats_result.get("loss"),
                "save": stats_result.get("save")
            },
            "hits": (engine.state.home_hits, engine.state.away_hits),
            "errors": (engine.state.home_errors, engine.state.away_errors)
        }
        
        self._on_game_finished(result)

    def _on_game_finished(self, result):
        """Handle game finish"""
        # Show sidebar and status bar again
        self.set_sidebar_visible(True)
        
        # Navigate to game result page
        self._navigate_to("game_result")
        if hasattr(self, 'game_result_page') and self.game_result_page:
            self.game_result_page.set_result(result)
        
        # Call post-game processing
        self._on_game_finished_post(result)

    def _on_training_saved(self):
        """Handle training saved"""
        self.status.show_message("トレーニング設定を保存しました", 3000)

    def _on_game_finished_post(self, result):
        """Post-game processing after user saw result"""
        home_team = result['home_team']
        away_team = result['away_team']
        home_score = result['home_score']
        away_score = result['away_score']
        
        winner_name = "DRAW"
        if home_score > away_score:
            winner_name = home_team.name
        elif away_score > home_score:
            winner_name = away_team.name
            
        if self.game_state:
            # 【重要】試合結果の履歴を記録（勝敗数更新含む）
            self.game_state.record_game_result(home_team, away_team, home_score, away_score)
            
            # 【重要】スケジュールの試合ステータスを更新
            today_games = self.game_state.get_today_games()
            for g in today_games:
                if g.home_team_name == home_team.name and g.away_team_name == away_team.name:
                    g.status = GameStatus.COMPLETED
                    g.home_score = home_score
                    g.away_score = away_score
                    
                    # 先発ローテーションを進める（試合消化時のみ）
                    home_team.rotation_index = (home_team.rotation_index + 1) % 6
                    away_team.rotation_index = (away_team.rotation_index + 1) % 6
                    break
            
            # ★追加: 二軍・三軍試合のシミュレーション
            try:
                simulate_farm_games_for_day(self.game_state.teams, self.game_state.current_date)
            except Exception as e:
                print(f"Farm Simulation Error: {e}")

            # ★追加: 契約関連（スカウト）の日付進行処理
            # Create contracts_page if not yet navigated to
            if not hasattr(self, 'contracts_page') or not self.contracts_page:
                from UI.pages.contracts_page import ContractsPage
                self.contracts_page = ContractsPage(self)
                if hasattr(self.contracts_page, 'go_to_player_detail'):
                    self.contracts_page.go_to_player_detail.connect(self._show_player_detail)
            self.contracts_page.advance_day()


            # ★追加: Highlight Logging from Manual Game (or any source passing 'highlights' in result)
            if "highlights" in result:
                for h in result["highlights"]:
                    self.game_state.log_news(
                        category=h['category'],
                        message=h['message'],
                        team_name=h['team']
                    )

            # 【重要】他球場試合を消化し、日付を進める
            self.game_state.finish_day_and_advance()
        
        # Show NPB Style Result Page
        # dialog = GameResultDialog(result, self)
        # dialog.exec()
        
        # Navigate to Game Result Page
        if self.game_state:
            # Create page if not exists (via navigate logic)
            self._navigate_to("game_result")
            self.game_result_page.set_result(result)
            
        # self._navigate_to("home") # Removed auto nav to home


    def set_sidebar_visible(self, visible: bool):
        """Toggle sidebar and status bar visibility"""
        self.sidebar.setVisible(visible)
        self.status.setVisible(visible)

    def _setup_shortcuts(self):
        """Set up keyboard shortcuts"""
        shortcuts = {
            "1": "home",
            "2": "roster",
            "3": "stats",
            "4": "schedule",
            # "5": "standings",  <-- Removed shortcut
            "6": "game",
            "0": "settings",
        }

        for key, page in shortcuts.items():
            action = QAction(self)
            action.setShortcut(QKeySequence(f"Ctrl+{key}"))
            action.triggered.connect(lambda checked, p=page: self._navigate_to(p))
            self.addAction(action)

        escape_action = QAction(self)
        escape_action.setShortcut(QKeySequence("Escape"))
        escape_action.triggered.connect(self._exit_fullscreen)
        self.addAction(escape_action)

    def _navigate_to(self, section: str):
        """Navigate to a section, preserving page state where possible"""
        
        # ページがまだ存在しない場合のみ新規作成するロジック
        is_persistent = section in self.persistent_pages or section == "title"
        is_cached = section in self.cached_pages
        
        # 1. Update Sidebar Visual Selection
        self._update_sidebar_selection(section)

        # 2. Page Handling
        if is_persistent:
            self.pages.show_page(section)
            # ★追加: 永続ページも表示時にデータを最新化
            page = self.persistent_pages.get(section)
            if page and self.game_state and hasattr(page, 'set_game_state'):
                page.set_game_state(self.game_state)
                
        elif is_cached:
            # 既にキャッシュされている場合は単に表示する
            self.pages.show_page(section)
            
            # ★追加: キャッシュページも表示時にデータを最新化
            page = self.cached_pages.get(section)
            if page:
                # set_game_state があれば呼ぶ
                if self.game_state and hasattr(page, 'set_game_state'):
                    page.set_game_state(self.game_state)
                
                # 手動リフレッシュメソッドがあれば呼ぶ（念のため）
                if hasattr(page, 'refresh'):
                    try: page.refresh()
                    except: pass
                elif hasattr(page, '_refresh_all'):
                    try: page._refresh_all()
                    except: pass
                if hasattr(page, '_load_team_data'):
                    try: page._load_team_data()
                    except: pass
        else:
            # 新規作成
            new_page = self._create_page_instance(section)
            if new_page is not None:
                self.pages.add_page(section, new_page)
                self.cached_pages[section] = new_page # キャッシュに登録
                
                if self.game_state and hasattr(new_page, 'set_game_state'):
                    new_page.set_game_state(self.game_state)
                
                self.pages.show_page(section)
            else:
                # 未実装ページの処理など
                pass

        # 3. Handle Sidebar Visibility
        if section == "game":
            self.set_sidebar_visible(False)
        elif section == "player_detail" and self.previous_section == "game":
            self.set_sidebar_visible(False)
        elif section == "player_stats_detail" and self.previous_section == "game":
            self.set_sidebar_visible(False)
        else:
            self.set_sidebar_visible(True)
            
        # 4. Update Navigation State
        self.current_section = section

    def _update_sidebar_selection(self, section: str):
        """Update the sidebar buttons to reflect current section"""
        # Map section IDs to button labels (as defined in _create_sidebar)
        section_map = {
            "home": "HOME", "roster": "ROSTER", "order": "ORDER", 
            "schedule": "SCHEDULE", "stats": "STATS", # STANDINGS removed
            "farm_swap": "FARM", "contract_changes": "CONTRACTS",
            "reinforcement": "ACQUISITIONS", "training": "TRAINING",
            "staff": "STAFF", "finance": "FINANCE",
            "save_load": "SAVE / LOAD", "settings": "SETTINGS", "title": "TITLE"
        }
        
        target_label = section_map.get(section)
        if not target_label:
            return

        # Find buttons in sidebar and update checked state
        buttons = self.sidebar.findChildren(ActionButton)
        for btn in buttons:
            if btn.text() == target_label:
                btn.setChecked(True)
            else:
                btn.setChecked(False)

    def _on_page_changed(self, index: int):
        """Handle page change"""
        if self.game_state:
            self.status.set_left_text(f"Year {self.game_state.current_year} | {self.game_state.current_date}")
            self.status.set_right_text(f"Team: {self.game_state.player_team.name if self.game_state.player_team else 'None'}")

    def _on_settings_changed(self, settings: dict):
        """Handle settings changes"""
        if settings.get("fullscreen", False):
            if not self.isFullScreen():
                self.showFullScreen()
        else:
            if self.isFullScreen():
                self.showNormal()

            if "window_size" in settings:
                size_str = settings["window_size"]
                if " x " in size_str:
                    parts = size_str.split(" x ")
                    try:
                        width = int(parts[0])
                        height = int(parts[1].split()[0])
                        self._set_window_size(width, height)
                    except (ValueError, IndexError):
                        pass

            if settings.get("start_maximized", False) and not self.isMaximized():
                self.showMaximized()

        if "ui_scale" in settings:
            self._set_ui_scale(settings["ui_scale"])

        for key, value in settings.items():
            self.settings.setValue(key, value)

    def set_game_state(self, game_state):
        """Set the current game state"""
        self.game_state = game_state

        # Update persistent pages
        for page in self.persistent_pages.values():
            if hasattr(page, 'set_game_state'):
                page.set_game_state(game_state)

        # Update current visible page if it exists
        current_widget = self.pages.currentWidget()
        if current_widget and hasattr(current_widget, 'set_game_state'):
            current_widget.set_game_state(game_state)
        
        # Pre-create contracts_page to avoid freeze during game result
        if not hasattr(self, 'contracts_page') or not self.contracts_page:
            from UI.pages.contracts_page import ContractsPage
            self.contracts_page = ContractsPage(self)
            if hasattr(self.contracts_page, 'go_to_player_detail'):
                self.contracts_page.go_to_player_detail.connect(self._show_player_detail)
            
        # Ensure initial sidebar state is correct if just started
        self._on_page_changed(0)

    def _show_player_detail(self, player):
        """Navigate to player detail page"""
        # Save current section to return to it later
        if self.current_section != "player_detail":
            self.previous_section = self.current_section
            
        # チーム名を検索
        team_name = None
        if self.game_state:
            for team in self.game_state.teams:
                # オブジェクトIDで比較、またはplayersリストに含まれているか
                if player in team.players:
                    team_name = team.name
                    break
            
        self.player_detail_page.set_player(player, team_name)
        self._navigate_to("player_detail")
        
    def _on_player_detail_back(self):
        """Handle back button from player detail page"""
        # Return to the previous section
        target = self.previous_section if self.previous_section else "home"
        self._navigate_to(target)

    def _show_player_stats_detail(self, player):
        """詳細統計画面を表示"""
        # まだ作成されていない場合は作成して登録
        if "player_stats_detail" not in self.persistent_pages:
            from UI.pages.player_stats_detail_page import PlayerStatsDetailPage
            self.player_stats_detail_page = PlayerStatsDetailPage(self)
            self.player_stats_detail_page.back_requested.connect(self._on_player_stats_detail_back)
            self.pages.add_page("player_stats_detail", self.player_stats_detail_page)
            self.persistent_pages["player_stats_detail"] = self.player_stats_detail_page
        else:
            self.player_stats_detail_page = self.persistent_pages["player_stats_detail"]

        self.player_stats_detail_page.set_player(player, self.game_state.current_year)
        self._navigate_to("player_stats_detail")

    def _on_player_stats_detail_back(self):
        """詳細統計画面から戻る"""
        self._navigate_to("player_detail")

    def _on_order_saved(self):
        """Handle order saved"""
        pass

    def show_game(self, home_team, away_team):
        """Switch to game page and start a game"""
        self._navigate_to("game")
        # Hide sidebar during game
        self.set_sidebar_visible(False)
        if self.game_page:
            # 日付も渡す
            current_date = self.game_state.current_date if self.game_state else "2027-01-01"
            self.game_page.start_game(home_team, away_team, current_date)

    def _set_window_size(self, width: int, height: int):
        if self.isFullScreen():
            self.showNormal()
        self.resize(width, height)
        self._center_on_screen()
        self.window_size_changed.emit(width, height)

    def _exit_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_changed.emit(False)

    def _set_ui_scale(self, scale: float):
        ThemeManager.set_scale(scale)
        app = QApplication.instance()
        if app:
            base_size = 10
            font = app.font()
            font.setPointSize(int(base_size * scale))
            app.setFont(font)
        self.settings.setValue("ui_scale", scale)

    def _save_window_state(self):
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("isMaximized", self.isMaximized())
        self.settings.setValue("isFullScreen", self.isFullScreen())

    def _restore_window_state(self):
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

        scale = self.settings.value("ui_scale", 1.0, type=float)
        if scale != 1.0:
            self._set_ui_scale(scale)

        if self.settings.value("isFullScreen", False, type=bool):
            self.showFullScreen()
        elif self.settings.value("isMaximized", False, type=bool):
            self.showMaximized()

    def closeEvent(self, event):
        self._save_window_state()
        event.accept()

    def resizeEvent(self, event):
        super().resizeEvent(event)


def run_app():
    """Run the application"""
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)
    ThemeManager.apply_theme(app)

    font = QFont("Yu Gothic UI", 10)
    if not font.exactMatch():
        font = QFont("Meiryo", 10)
    app.setFont(font)

    window = MainWindow()

    from game_state import GameState
    from team_generator import create_all_teams

    # Demo setup
    teams = create_all_teams()
    game_state = GameState(
        teams=teams,
        current_year=2027,
        player_team_index=0
    )
    window.set_game_state(game_state)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()