# -*- coding: utf-8 -*-
"""
Pennant Simulator 2027 - Main Window
OOTP-Style Professional Main Interface with Premium Features
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


class MainWindow(QMainWindow):
    """Main application window with OOTP-style layout and resizable features"""

    # Signals
    fullscreen_changed = Signal(bool)
    window_size_changed = Signal(int, int)

    # Window size presets
    SIZE_PRESETS = {
        "1280x720": (1280, 720),
        "1366x768": (1366, 768),
        "1600x900": (1600, 900),
        "1920x1080": (1920, 1080),
        "2560x1440": (2560, 1440),
        "3840x2160": (3840, 2160),
    }

    def __init__(self):
        super().__init__()
        self.theme = get_theme()
        self.game_state = None
        self.settings = QSettings("NPBSimulator", "PennantSimulator")

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
        # Central widget
        central = QWidget()
        central.setStyleSheet(f"background-color: {self.theme.bg_dark};") # 背景色設定
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
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
        self._create_pages()
        content_layout.addWidget(self.pages)

        # Status bar
        self.status = StatusPanel()
        content_layout.addWidget(self.status)

        main_layout.addWidget(content_area)

    def _create_sidebar(self) -> SidebarPanel:
        """Create the navigation sidebar"""
        sidebar = SidebarPanel()

        sidebar.add_nav_item("", "HOME", "home")
        sidebar.add_nav_item("", "ROSTER", "roster")
        sidebar.add_nav_item("", "STATS", "stats")

        sidebar.add_separator("SEASON")
        sidebar.add_nav_item("", "SCHEDULE", "schedule")
        sidebar.add_nav_item("", "STANDINGS", "standings")
        sidebar.add_nav_item("", "GAME", "game")

        sidebar.add_separator("MANAGEMENT")
        sidebar.add_nav_item("", "TRADE", "trade")
        sidebar.add_nav_item("", "DRAFT", "draft")
        sidebar.add_nav_item("", "FREE AGENCY", "free_agency")

        sidebar.add_separator("SYSTEM")
        sidebar.add_nav_item("", "SAVE / LOAD", "save_load")
        sidebar.add_nav_item("", "SETTINGS", "settings")

        sidebar.add_stretch()
        sidebar.add_nav_item("", "TITLE", "title")

        sidebar.navigation_clicked.connect(self._on_sidebar_nav)

        return sidebar

    def _on_sidebar_nav(self, section: str):
        if section == "title":
            self.pages.show_page("title")
        else:
            self._navigate_to(section)

    def _create_pages(self):
        """Create all application pages"""
        from UI.pages.home_page import HomePage
        from UI.pages.roster_page import RosterPage
        from UI.pages.live_game_page import LiveGamePage 
        from UI.pages.standings_page import StandingsPage
        from UI.pages.schedule_page import SchedulePage
        from UI.pages.stats_page import StatsPage
        from UI.pages.draft_page import DraftPage
        from UI.pages.trade_page import TradePage
        from UI.pages.fa_page import FAPage
        from UI.pages.settings_page import SettingsPage

        # Create page instances
        self.home_page = HomePage(self)
        self.roster_page = RosterPage(self)
        self.game_page = LiveGamePage(self)
        self.standings_page = StandingsPage(self)
        self.schedule_page = SchedulePage(self)
        self.stats_page = StatsPage(self)
        self.draft_page = DraftPage(self)
        self.trade_page = TradePage(self)
        self.fa_page = FAPage(self)
        self.settings_page = SettingsPage(self)

        # Connect settings page signals
        self.settings_page.settings_changed.connect(self._on_settings_changed)

        # Add pages to container
        self.pages.add_page("home", self.home_page)
        self.pages.add_page("roster", self.roster_page)
        self.pages.add_page("game", self.game_page)
        self.pages.add_page("standings", self.standings_page)
        self.pages.add_page("schedule", self.schedule_page)
        self.pages.add_page("stats", self.stats_page)
        self.pages.add_page("draft", self.draft_page)
        self.pages.add_page("trade", self.trade_page)
        self.pages.add_page("free_agency", self.fa_page)
        self.pages.add_page("settings", self.settings_page)

        # Placeholder for save/load
        self.pages.add_page("save_load", self._create_placeholder("セーブ/ロード"))

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
        """Set up signal connections"""
        self.pages.page_changed.connect(self._on_page_changed)
        
        self.home_page.game_requested.connect(self._on_game_requested)
        self.home_page.view_roster_requested.connect(lambda: self._navigate_to("roster"))
        
        # 試合終了時のシグナル接続
        self.game_page.game_finished.connect(self._on_game_finished)

    def _on_game_requested(self):
        """Handle game request from home page"""
        if not self.game_state:
            return

        # 対戦相手決定ロジック（簡易版）
        player_team = self.game_state.player_team
        opponents = [t for t in self.game_state.teams if t.name != player_team.name]
        
        if not opponents:
            return

        opponent = random.choice(opponents)
        is_home_game = random.choice([True, False])
        
        home_team = player_team if is_home_game else opponent
        away_team = opponent if is_home_game else player_team
        
        self.show_game(home_team, away_team)

    def _on_game_finished(self, result):
        """Handle game finish"""
        # サイドバーとステータスバーを再表示
        self.set_sidebar_visible(True)
        
        # 試合結果を表示してホームに戻る
        msg = f"試合終了\n\n{result['away_team'].name} {result['away_score']} - {result['home_score']} {result['home_team'].name}\n\n勝者: {result['winner']}"
        QMessageBox.information(self, "試合結果", msg)
        
        self._navigate_to("home")
        self.home_page.set_game_state(self.game_state)

    def set_sidebar_visible(self, visible: bool):
        """サイドバーとステータスバーの表示切り替え"""
        self.sidebar.setVisible(visible)
        self.status.setVisible(visible)

    def _setup_shortcuts(self):
        """Set up keyboard shortcuts"""
        shortcuts = {
            "1": "home",
            "2": "roster",
            "3": "stats",
            "4": "schedule",
            "5": "standings",
            "6": "game",
            "7": "trade",
            "8": "draft",
            "9": "free_agency",
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
        """Navigate to a section"""
        # 試合画面以外に移動する場合はサイドバーを表示
        if section != "game":
            self.set_sidebar_visible(True)
        
        self.pages.show_page(section)

    def _on_page_changed(self, index: int):
        """Handle page change"""
        if self.game_state:
            self.status.set_left_text(f"{self.game_state.current_year}年")
            self.status.set_right_text(f"チーム: {self.game_state.player_team.name if self.game_state.player_team else '未選択'}")

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

        pages_to_update = [
            self.home_page, self.roster_page, self.game_page,
            self.standings_page, self.schedule_page, self.stats_page,
            self.draft_page, self.trade_page, self.fa_page
        ]

        for page in pages_to_update:
            if hasattr(page, 'set_game_state'):
                page.set_game_state(game_state)

        self._on_page_changed(0)

    def show_game(self, home_team, away_team):
        """Switch to game page and start a game"""
        self._navigate_to("game")
        # 試合開始時はサイドバーを非表示
        self.set_sidebar_visible(False)
        self.game_page.start_game(home_team, away_team)

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
        size = event.size()
        self.status.set_right_text(f"{size.width()}x{size.height()}")


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
    from team_generator import create_all_npb_teams

    # Demo setup
    teams = create_all_npb_teams()
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