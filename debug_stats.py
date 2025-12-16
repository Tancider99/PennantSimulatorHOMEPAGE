
import sys
import random
from models import Team, Player, Position, PlayerStats, TeamLevel
from live_game_engine import LiveGameEngine, GameState
from player_generator import create_random_player

def create_mock_team(name):
    t = Team(name=name, league=None)
    # Create 9 batters
    for i in range(9):
        p = create_random_player(Position.CENTER) # generic
        p.name = f"{name} Batter {i}"
        p.uniform_number = 10 + i
        t.players.append(p)
    
    # Create Pitchers
    for i in range(5):
        p = create_random_player(Position.PITCHER)
        p.name = f"{name} Pitcher {i}"
        p.uniform_number = 20 + i
        t.players.append(p)
        
    t.current_lineup = list(range(9))
    t.rotation = [9] # Pitcher 0
    t.starting_pitcher_idx = 9
    return t

def test_stats():
    h_team = create_mock_team("Home")
    a_team = create_mock_team("Away")
    
    engine = LiveGameEngine(h_team, a_team, TeamLevel.FIRST)
    
    # Simulate full game
    print("Simulating game...")
    while not engine.is_game_over:
        engine.simulate_play()
        
    results = engine.finalize_game_stats()
    stats = results['game_stats']
    
    print(f"Game Over. Score: {engine.state.home_score}-{engine.state.away_score}")
    print(f"Stats keys count: {len(stats)}")
    
    if len(stats) == 0:
        print("FAILURE: game_stats is empty!")
        return

    # Check content
    sample_key = list(stats.keys())[0]
    print(f"Sample Key Type: {type(sample_key)}")
    print(f"Sample Key Repr: {sample_key}")
    print(f"Sample Val: {stats[sample_key]}")
    
    # Check if keys match original objects
    p_orig = h_team.players[0]
    found = False
    for k in stats.keys():
        if k is p_orig:
            found = True
            print("SUCCESS: Found original player object in stats keys (Identity match)")
            break
        if k.name == p_orig.name:
            print("INFO: Found name match but not identity match?")
    
    if not found:
        print("WARNING: Original player object not found in stats keys by identity.")

if __name__ == "__main__":
    test_stats()
