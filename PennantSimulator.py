# -*- coding: utf-8 -*-
"""
Pennant Simulator 2027 - Premium UI Launcher
Unified window flow: Loading -> Title -> Team Select -> Game
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QMainWindow, QStackedWidget, QApplication
from PySide6.QtCore import Qt, QTimer


def main():
    """Launch the Premium PySide6 UI with unified window flow"""
    try:
        from PySide6.QtWidgets import (
            QApplication, QMainWindow, QStackedWidget, QWidget,
            QVBoxLayout
        )
        from PySide6.QtGui import QFont, QColor
        from PySide6.QtCore import Qt, QTimer

        from UI.theme import ThemeManager, get_theme
        from UI.screens.loading_screen import LoadingScreen
        from UI.screens.title_screen import TitleScreen
        from UI.screens.team_select_screen import TeamSelectScreen
        from UI.main_window import MainWindow
        from game_state import GameStateManager
        from team_generator import load_or_create_teams

        # Create Qt Application with High DPI support
        app = QApplication(sys.argv)

        # Enable High DPI scaling (Qt6 style)
        app.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )

        # Apply Premium theme
        ThemeManager.apply_theme(app)

        # Set Japanese font with fallback
        font = QFont("Yu Gothic UI", 10)
        if not font.exactMatch():
            font = QFont("Meiryo UI", 10)
            if not font.exactMatch():
                font = QFont("Meiryo", 10)
        app.setFont(font)

        print("=" * 60)
        print("  PENNANT SIMULATOR 2027")
        print("  Premium Edition")
        print("=" * 60)

        # Create the game controller
        controller = GameController(app)
        controller.show()

        sys.exit(app.exec())

    except ImportError as e:
        print(f"Error: Required module not found: {e}")
        print("\nPlease install PySide6:")
        print("  pip install PySide6")
        sys.exit(1)

    except Exception as e:
        print(f"\nError occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


class GameController(QMainWindow):
    """
    Main game controller that manages the unified window flow.
    Loading -> Title -> Team Select -> Main Game
    """

    def show_manage_mode(self, home_team, away_team):
        """Show the tactical one-pitch mode (LiveManagePage) in MainWindow"""
        if hasattr(self, 'main_window'):
            self.main_window.show_live_manage(home_team, away_team)
            self.stack.setCurrentWidget(self.main_window)
        else:
            print("MainWindow not initialized yet.")

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.game_state = None
        self.north_teams = []
        self.south_teams = []

        # Import screens here to avoid circular imports
        from UI.screens.loading_screen import LoadingScreen
        from UI.screens.title_screen import TitleScreen
        from UI.screens.team_select_screen import TeamSelectScreen

        self.LoadingScreen = LoadingScreen
        self.TitleScreen = TitleScreen
        self.TeamSelectScreen = TeamSelectScreen

        self._setup_window()
        self._setup_screens()
        self._start_loading()

    def _setup_window(self):
        """Configure the main window"""
        self.setWindowTitle("Pennant Simulator 2027")
        self.setMinimumSize(1280, 720)

        # Set window style
        from UI.theme import get_theme
        theme = get_theme()
        self.setStyleSheet(f"background-color: {theme.bg_dark};")

    def show(self):
        """Show window in fullscreen by default"""
        super().showFullScreen()

    def _setup_screens(self):
        """Set up all screens in a stacked widget"""
        self.stack = QStackedWidget()
        # 修正: QMainWindowのメソッド名は setCentralWidget のままである必要があります
        self.setCentralWidget(self.stack)
        
        # Disable default status bar to prevent unwanted white bar at bottom
        self.statusBar().hide()
        self.statusBar().setStyleSheet("background: transparent; min-height: 0px; height: 0px; border: none;")
        
        # Create screens
        self.loading_screen = self.LoadingScreen()
        self.title_screen = self.TitleScreen()
        self.team_select_screen = self.TeamSelectScreen()

        # Add screens to stack
        self.stack.addWidget(self.loading_screen)      # Index 0
        self.stack.addWidget(self.title_screen)         # Index 1
        self.stack.addWidget(self.team_select_screen)   # Index 2

        # Robustly ensure no frame on stack
        from PySide6.QtWidgets import QFrame
        self.stack.setFrameShape(QFrame.NoFrame)
        self.stack.setLineWidth(0)

        # Connect signals
        self.loading_screen.loading_complete.connect(self._on_loading_complete)
        self.title_screen.new_game_clicked.connect(self._on_new_game)
        self.title_screen.continue_clicked.connect(self._on_continue)
        self.title_screen.load_game_clicked.connect(self._on_load_game)
        self.title_screen.settings_clicked.connect(self._on_settings)
        self.title_screen.exit_clicked.connect(self._on_exit)
        self.team_select_screen.back_clicked.connect(self._on_team_select_back)
        self.team_select_screen.confirm_clicked.connect(self._on_team_confirmed)

    def _start_loading(self):
        """Start the loading sequence"""
        self.stack.setCurrentIndex(0)

        # Simulate loading with progress updates
        from PySide6.QtCore import QTimer
        self.load_progress = 0
        self.load_timer = QTimer()
        self.load_timer.timeout.connect(self._update_loading)
        self.load_timer.start(50)

    def _update_loading(self):
        """Update loading progress"""
        messages = {
            0: "Initializing...",
            15: "Loading theme...",
            30: "Loading team data...",
            50: "Generating players...",
            70: "Setting up game state...",
            85: "Preparing interface...",
            95: "Almost ready..."
        }

        # Perform actual loading at specific points
        if self.load_progress == 30:
            self._load_teams()
        elif self.load_progress == 70:
            self._create_game_state()

        # Update progress bar
        message = messages.get(self.load_progress)
        if message:
            self.loading_screen.set_progress(self.load_progress, message)
        else:
            self.loading_screen.set_progress(self.load_progress)

        self.load_progress += 2

        if self.load_progress >= 100:
            self.load_timer.stop()
            self.loading_screen.set_progress(100, "Complete")

    def _load_teams(self):
        """Load or create teams"""
        from team_generator import load_or_create_teams

        # Fictional team names for copyright compliance
        # North League 
        north_team_names = [
            "Tokyo Bravers",
            "Osaka Thunders",
            "Nagoya Sparks",
            "Hiroshima Phoenix",
            "Yokohama Mariners",
            "Shinjuku Spirits"
        ]
        # South League
        south_team_names = [
            "Fukuoka Phoenix",
            "Saitama Bears",
            "Sendai Flames",
            "Chiba Mariners",
            "Sapporo Fighters",
            "Kobe Buffaloes"
        ]

        print("  Loading team data...")
        self.north_teams, self.south_teams = load_or_create_teams(
            north_team_names, south_team_names
        )
        print(f"  North League: {len(self.north_teams)} teams")
        print(f"  South League: {len(self.south_teams)} teams")

    def _create_game_state(self):
        """Create the game state manager"""
        from game_state import GameStateManager

        print("  Initializing game state...")
        self.game_state = GameStateManager()
        self.game_state.north_teams = self.north_teams
        self.game_state.south_teams = self.south_teams
        self.game_state.all_teams = self.north_teams + self.south_teams
        self.game_state.current_year = 2027

        total_players = sum(len(team.players) for team in self.game_state.all_teams)
        print(f"  Total players: {total_players}")
        # Set new league names
        self.game_state.north_league_name = "North League"
        self.game_state.south_league_name = "South League"

        # Initialize league schedule engine
        print("  Generating league schedule...")
        self.game_state.initialize_schedule()
        if self.game_state.schedule:
            print(f"  Schedule: {len(self.game_state.schedule.games)} games generated")
        
        # Initialize staff data from files
        print("  Loading staff data...")
        from UI.pages.staff_page import initialize_staff_from_files
        initialize_staff_from_files(self.game_state)

    def _on_loading_complete(self):
        """Handle loading completion"""
        print("-" * 60)
        print("  Loading complete!")
        print("-" * 60)

        # Check for existing save
        # For now, just show title screen
        self.title_screen.set_has_save(False)
        self.stack.setCurrentIndex(1)

    def _on_new_game(self):
        """Handle new game button click"""
        print("  Starting new game...")
        # Pass team data to team select screen for overview display
        self.team_select_screen.set_teams(self.north_teams, self.south_teams)
        self.stack.setCurrentIndex(2)

    def _on_continue(self):
        """Handle continue button click"""
        print("  Continuing saved game...")
        # Load most recent save and start game
        self._start_main_game()

    def _on_load_game(self):
        """Handle load game button click"""
        print("  Opening load game dialog...")
        # Show load game dialog
        # For now, just start a new game
        self._on_new_game()

    def _on_settings(self):
        """Handle settings button click from title screen"""
        print("  Opening settings...")
        # Show settings dialog
        # For now, this is a placeholder

    def _on_exit(self):
        """Handle exit button click"""
        print("  Exiting game...")
        self.close()

    def _on_team_select_back(self):
        """Handle back button on team selection"""
        self.stack.setCurrentIndex(1)

    def _on_team_confirmed(self, team_name: str):
        """Handle team selection confirmation"""
        print(f"  Team selected: {team_name}")

        # Find the selected team
        selected_team = None
        for team in self.game_state.all_teams:
            if team.name == team_name:
                selected_team = team
                break

        if selected_team:
            self.game_state.player_team = selected_team
            
            # ユーザーのリクエスト対応: ゲーム開始時に投手のオーダーを空にする
            # (初期化時に全チーム自動編成が走ってしまうため、ここでリセット)
            selected_team.rotation = [-1] * 8
            selected_team.closers = [-1] * 4  # 抑え枠
            selected_team.setup_pitchers = [-1] * 8
            # 念のためスタメンもリセットしたければここでおこなうが、リクエストは投手のみ
            
        else:
            # Default to first team if not found
            self.game_state.player_team = self.north_teams[0]

        # 新しいロード画面を表示（コールバックで完了時にゲーム開始）
        from UI.screens.game_loading_screen import GameLoadingScreen
        def on_complete():
            self._start_main_game()
        self.game_loading_screen = GameLoadingScreen(on_complete=on_complete, parent=self.stack)
        self.stack.addWidget(self.game_loading_screen)
        self.stack.setCurrentWidget(self.game_loading_screen)

    def _start_main_game(self):
        """Start the main game interface"""
        from UI.main_window import MainWindow

        print("-" * 60)
        print("  Starting game!")
        print("  F11: Toggle fullscreen")
        print("  Ctrl+1-0: Navigate to pages")
        print("-" * 60)

        # Create main window
        self.main_window = MainWindow()
        self.main_window.set_game_state(self.game_state)

        # Add to stack and show
        self.stack.addWidget(self.main_window)
        self.stack.setCurrentWidget(self.main_window)

    def keyPressEvent(self, event):
        """Handle key press events"""
        from PySide6.QtCore import Qt

        if event.key() == Qt.Key_F11:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif event.key() == Qt.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
        else:
            super().keyPressEvent(event)


if __name__ == "__main__":
    main()