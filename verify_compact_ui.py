
import sys
try:
    from PyQt5.QtWidgets import QApplication
except:
    from PySide6.QtWidgets import QApplication

from UI.pages.training_page import TrainingPage
from models import Player, PlayerStats, Position, PlayerType

try:
    app = QApplication(sys.argv)
except:
    app = QApplication.instance()

p = Player(name="TestPitcher", age=20, position=Position.PITCHER, uniform_number=18)
p.stats.pitches = {
    "ストレート": {"quality": 50, "stuff": 50, "control": 50, "movement": 0},
    "スライダー": {"quality": 40, "stuff": 40, "control": 40, "movement": 40}
}
p.player_type = PlayerType.POWER_PITCHER

try:
    page = TrainingPage()
    page.selected_player = p
    page._update_detail_view()
    print("TrainingPage (Round 8 Compact Fix) updated successfully.")
except Exception as e:
    print(f"FAILED to update detail view: {e}")
    import traceback
    traceback.print_exc()
