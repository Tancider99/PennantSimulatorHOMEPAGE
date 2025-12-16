
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from live_game_engine import GameState, NPBPitcherManager, Team, Player, Position
from unittest.mock import MagicMock

def create_mock_team(name):
    t = Team(name=name, league=None)
    t.players = []
    # Create rotation
    for i in range(6):
        p = Player(name=f"{name}_Starter{i}", position=Position.PITCHER)
        p.stats = MagicMock()
        p.stats.stamina = 50
        p.current_stamina = 100
        p.stats.overall_pitching = lambda: 80
        p.starter_aptitude = 4 # Ensure they are seen as starters
        t.players.append(p)
    t.rotation = [0, 1, 2, 3, 4, 5] # Indices
    
    # Create relievers
    for i in range(5):
        p = Player(name=f"{name}_Reliever{i}", position=Position.PITCHER)
        p.stats = MagicMock()
        p.stats.stamina = 30
        p.current_stamina = 100
        p.stats.overall_pitching = lambda: 70
        t.players.append(p)
    t.active_roster = list(range(len(t.players)))
    t.current_lineup = [0] * 9 # Dummy
    return t

def verify_pitcher_logic():
    manager = NPBPitcherManager()
    
    home = create_mock_team("Home")
    away = create_mock_team("Away")
    
    # Test 1: Top of Inning (Home Pitching)
    # Home pitcher is tired. Away pitcher (bench) is fresh.
    # Before fix: it checked Away stamina (fresh) -> No change.
    # After fix: it checks Home stamina (tired) -> Change.
    
    state = GameState()
    state.is_top = True # Top inning, Home pitches
    state.home_pitcher_stamina = 10.0 # Tired
    state.away_pitcher_stamina = 100.0 # Fresh
    state.home_pitchers_used = [home.players[0]]
    state.away_pitchers_used = [away.players[0]]
    
    current_pitcher = home.players[0] # Starter
    batter = away.players[6] # Some batter
    
    # Force condition where change is expected if checking correct stats
    # Starter with < 20 stamina -> should change
    
    print("Test 1: Home Pitching (Top), Tired (10), Bench Away Fresh (100)")
    
    result = manager.check_pitcher_change(state, home, away, batter, current_pitcher)
    
    if result is not None:
        print("PASS: Home pitcher changed (Correctly identified tired home pitcher)")
    else:
        print("FAIL: Home pitcher NOT changed (Likely checked fresh away pitcher)")

    # Test 2: Bottom of Inning (Away Pitching)
    # Away pitcher is tired. Home pitcher (bench) is fresh.
    state.is_top = False # Bottom inning, Away pitches
    state.home_pitcher_stamina = 100.0 # Fresh
    state.away_pitcher_stamina = 10.0 # Tired
    
    current_pitcher = away.players[0] # Starter
    batter = home.players[6]
    
    print("\nTest 2: Away Pitching (Bottom), Tired (10), Bench Home Fresh (100)")
    
    result = manager.check_pitcher_change(state, away, home, batter, current_pitcher)
    
    if result is not None:
        print("PASS: Away pitcher changed (Correctly identified tired away pitcher)")
    else:
        print("FAIL: Away pitcher NOT changed (Likely checked fresh home pitcher)")

if __name__ == "__main__":
    verify_pitcher_logic()
