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
        # self._setup_menu_bar()  # メニューバー削除
        self._setup_ui()
        self._setup_connections()
        self._setup_shortcuts()
        self._restore_window_state()

        # Start with home page
        self._navigate_to("home")

    def _setup_window(self):
        """Configure main window properties"""
        self.setWindowTitle("Pennant Simulator 2027")

        # Allow window to be resized
        self.setMinimumSize(1024, 600)

        # Default size
        self.resize(1600, 1000)

        # Enable window flags for proper resizing
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint |
            Qt.WindowCloseButtonHint
        )

        # Center on screen
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

        # Header（削除）
        # self.header = HeaderPanel("ホーム")
        # content_layout.addWidget(self.header)

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

        # Main navigation - no emojis, clean text
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

        # タイトルに戻るボタンを一番下に追加
        sidebar.add_stretch()
        sidebar.add_nav_item("", "TITLE", "title")

        sidebar.navigation_clicked.connect(self._on_sidebar_nav)

        return sidebar

    def _on_sidebar_nav(self, section: str):
        if section == "title":
            # タイトル画面に遷移する処理（titleページに遷移）
            self.pages.show_page("title")
        else:
            self._navigate_to(section)

    def _create_pages(self):
        """Create all application pages"""
        from UI.pages.home_page import HomePage
        from UI.pages.roster_page import RosterPage
        from UI.pages.game_page import GamePage
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
        self.game_page = GamePage(self)
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
        # Page change updates header
        self.pages.page_changed.connect(self._on_page_changed)

    def _setup_shortcuts(self):
        """Set up keyboard shortcuts"""
        # Navigation shortcuts
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

        # Escape to exit fullscreen
        escape_action = QAction(self)
        escape_action.setShortcut(QKeySequence("Escape"))
        escape_action.triggered.connect(self._exit_fullscreen)
        self.addAction(escape_action)

    def _navigate_to(self, section: str):
        """Navigate to a section"""
        # Show page only (header削除)
        self.pages.show_page(section)

    def _on_page_changed(self, index: int):
        """Handle page change"""
        # Update status bar
        if self.game_state:
            self.status.set_left_text(f"{self.game_state.current_year}年")
            self.status.set_right_text(f"チーム: {self.game_state.player_team.name if self.game_state.player_team else '未選択'}")

    def _on_settings_changed(self, settings: dict):
        """Handle settings changes"""
        # Apply fullscreen first
        if settings.get("fullscreen", False):
            if not self.isFullScreen():
                self.showFullScreen()
                self.fullscreen_action.setChecked(True)
        else:
            if self.isFullScreen():
                self.showNormal()
                self.fullscreen_action.setChecked(False)

            # Apply window size if not fullscreen
            if "window_size" in settings:
                size_str = settings["window_size"]
                # Parse size string like "1280 x 720 (HD)"
                if " x " in size_str:
                    parts = size_str.split(" x ")
                    try:
                        width = int(parts[0])
                        height = int(parts[1].split()[0])
                        self._set_window_size(width, height)
                    except (ValueError, IndexError):
                        pass

            # Apply start maximized
            if settings.get("start_maximized", False) and not self.isMaximized():
                self.showMaximized()

        # Apply UI scale
        if "ui_scale" in settings:
            self._set_ui_scale(settings["ui_scale"])

        # Save settings to QSettings
        for key, value in settings.items():
            self.settings.setValue(key, value)

    def set_game_state(self, game_state):
        """Set the current game state"""
        self.game_state = game_state

        # Update all pages with game state
        pages_to_update = [
            self.home_page, self.roster_page, self.game_page,
            self.standings_page, self.schedule_page, self.stats_page,
            self.draft_page, self.trade_page, self.fa_page
        ]

        for page in pages_to_update:
            if hasattr(page, 'set_game_state'):
                page.set_game_state(game_state)

        # Update status bar
        self._on_page_changed(0)

    def show_game(self, home_team, away_team):
        """Switch to game page and start a game"""
        self._navigate_to("game")
        self.game_page.start_game(home_team, away_team)

    # === Window Size and Display Methods ===

    def _set_window_size(self, width: int, height: int):
        """Set window to a specific size"""
        # Exit fullscreen if active
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_action.setChecked(False)

        self.resize(width, height)
        self._center_on_screen()
        self.window_size_changed.emit(width, height)

    def _toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_action.setChecked(False)
            self.fullscreen_changed.emit(False)
        else:
            self.showFullScreen()
            self.fullscreen_action.setChecked(True)
            self.fullscreen_changed.emit(True)

    def _exit_fullscreen(self):
        """Exit fullscreen mode if active"""
        if self.isFullScreen():
            self.showNormal()
            self.fullscreen_action.setChecked(False)
            self.fullscreen_changed.emit(False)

    def _toggle_maximize(self):
        """Toggle maximize/restore"""
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def _set_ui_scale(self, scale: float):
        """Set the UI scale factor"""
        ThemeManager.set_scale(scale)

        # Get current font and scale it
        app = QApplication.instance()
        if app:
            base_size = 10
            font = app.font()
            font.setPointSize(int(base_size * scale))
            app.setFont(font)

        # Save setting
        self.settings.setValue("ui_scale", scale)

    # === Window State Persistence ===

    def _save_window_state(self):
        """Save window geometry and state"""
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("isMaximized", self.isMaximized())
        self.settings.setValue("isFullScreen", self.isFullScreen())

    def _restore_window_state(self):
        """Restore window geometry and state"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

        # Restore scale
        scale = self.settings.value("ui_scale", 1.0, type=float)
        if scale != 1.0:
            self._set_ui_scale(scale)

        # Restore fullscreen/maximized state
        if self.settings.value("isFullScreen", False, type=bool):
            self.showFullScreen()
            self.fullscreen_action.setChecked(True)
        elif self.settings.value("isMaximized", False, type=bool):
            self.showMaximized()

    def closeEvent(self, event):
        """Handle window close event"""
        self._save_window_state()
        event.accept()

    def resizeEvent(self, event):
        """Handle window resize"""
        super().resizeEvent(event)
        # Update status bar with current size
        size = event.size()
        self.status.set_right_text(f"{size.width()}x{size.height()}")

    # === Help Dialogs ===

    def _show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "Pennant Simulator 2027",
            """
            <h2>Pennant Simulator 2027</h2>
            <p><b>OOTP-Style Professional Edition</b></p>
            <p>日本プロ野球ペナントレースシミュレーター</p>
            <hr>
            <p>Version: 2027.0.0</p>
            <p>Engine: PySide6 + Python</p>
            <hr>
            <p>© 2027 Baseball Architect Project</p>
            """
        )

    def _show_shortcuts(self):
        """Show keyboard shortcuts dialog"""
        shortcuts_text = """
        <h3>キーボードショートカット</h3>
        <table>
        <tr><td><b>F11</b></td><td>フルスクリーン切替</td></tr>
        <tr><td><b>Ctrl+M</b></td><td>最大化切替</td></tr>
        <tr><td><b>Escape</b></td><td>フルスクリーン解除</td></tr>
        <tr><td><b>Space</b></td><td>1日進める</td></tr>
        <tr><td><b>Ctrl+Space</b></td><td>1週間進める</td></tr>
        <tr><td colspan="2"><hr></td></tr>
        <tr><td><b>Ctrl+1</b></td><td>ホーム</td></tr>
        <tr><td><b>Ctrl+2</b></td><td>ロースター</td></tr>
        <tr><td><b>Ctrl+3</b></td><td>統計</td></tr>
        <tr><td><b>Ctrl+4</b></td><td>日程・結果</td></tr>
        <tr><td><b>Ctrl+5</b></td><td>順位表</td></tr>
        <tr><td><b>Ctrl+6</b></td><td>試合</td></tr>
        <tr><td><b>Ctrl+7</b></td><td>トレード</td></tr>
        <tr><td><b>Ctrl+8</b></td><td>ドラフト</td></tr>
        <tr><td><b>Ctrl+9</b></td><td>FA</td></tr>
        <tr><td><b>Ctrl+0</b></td><td>設定</td></tr>
        <tr><td colspan="2"><hr></td></tr>
        <tr><td><b>Ctrl+N</b></td><td>新規ゲーム</td></tr>
        <tr><td><b>Ctrl+O</b></td><td>ロード</td></tr>
        <tr><td><b>Ctrl+S</b></td><td>セーブ</td></tr>
        </table>
        """
        QMessageBox.information(self, "ショートカット一覧", shortcuts_text)


def create_splash_screen() -> QSplashScreen:
    """Create a premium splash screen"""
    # Create a gradient splash pixmap
    pixmap = QPixmap(700, 450)
    pixmap.fill(QColor(get_theme().bg_dark))

    splash = QSplashScreen(pixmap)
    splash.setStyleSheet(f"""
        color: {get_theme().text_primary};
        font-size: 28px;
        font-weight: 300;
        letter-spacing: 4px;
    """)
    splash.showMessage(
        "PENNANT SIMULATOR 2027\n\nLOADING...",
        Qt.AlignCenter | Qt.AlignBottom,
        QColor(get_theme().text_primary)
    )

    return splash


def run_app():
    """Run the application"""
    app = QApplication(sys.argv)

    # High DPI support
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)

    # Apply theme
    ThemeManager.apply_theme(app)

    # Set application font
    font = QFont("Yu Gothic UI", 10)
    if not font.exactMatch():
        font = QFont("Meiryo", 10)
    app.setFont(font)

    # Show splash screen
    # splash = create_splash_screen()
    # splash.show()
    # app.processEvents()

    # Create main window
    window = MainWindow()

    # Load game state (if exists) or show new game dialog
    # For now, create a demo game state
    from game_state import GameStateManager, GameState
    from team_generator import create_all_npb_teams

    # Create teams and game state
    teams = create_all_npb_teams()
    game_state = GameState(
        teams=teams,
        current_year=2027,
        player_team_index=0  # Giants as default
    )
    window.set_game_state(game_state)

    # Close splash and show main window
    # splash.finish(window)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
