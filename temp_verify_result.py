import sys
import os
from PySide6.QtWidgets import QApplication

# Adjust path to find modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from UI.theme import Theme
from UI.pages.game_result_page import GameResultPage
from models import Team, Player, Position

def verify():
    app = QApplication(sys.argv)
    
    # Mock Data
    h_team = Team("Giants", "North League")
    a_team = Team("Tigers", "North League")
    
    # Mock Players for Pitching
    win_p = Player("Winner", 18, Position.PITCHER)
    loss_p = Player("Loser", 20, Position.PITCHER)
    slugger = Player("Slugger", 55, Position.CENTER)
    
    result_data = {
        'home_team': h_team,
        'away_team': a_team,
        'home_score': 5,
        'away_score': 3,
        'date': '2027-05-15',
        'score_history': {
            'top': [0,0,0,1,0,2],
            'bot': [1,0,0,0,3,0] # 6 innings
        },
        'hits': (8, 6),
        'errors': (0, 1),
        'pitcher_result': {
            'win': win_p,
            'loss': loss_p,
            'save': None
        },
        'home_runs': [('Slugger', 10, 'Giants')],
        'game_stats': {
            slugger: {'pa': 4, 'ab': 4, 'run': 1, 'h': 2, 'hr': 1, 'rbi': 2, 'so': 1, 'bb': 0},
            win_p: {'ip_outs': 18, 'p_h': 3, 'p_run': 1, 'er': 1, 'p_so': 5, 'p_bb': 1},
            loss_p: {'ip_outs': 15, 'p_h': 5, 'p_run': 4, 'er': 3, 'p_so': 2, 'p_bb': 2}
        }
    }
    
    page = GameResultPage()
    page.set_result(result_data)
    page.show()
    
    print("GameResultPage instantiated successfully")
    # app.exec() # Don't block
    return True

if __name__ == "__main__":
    verify()
