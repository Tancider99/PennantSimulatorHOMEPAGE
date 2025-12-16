
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from team_generator import create_team
from models import League, TeamLevel
from live_game_engine import LiveGameEngine

def run_debug_game():
    print("Generating teams...")
    home = create_team("HomeTeam", League.NORTH)
    away = create_team("AwayTeam", League.SOUTH)
    
    # Ensure they have rotations set up
    print("Assigning Roles...")
    home.auto_assign_pitching_roles(TeamLevel.FIRST)
    print(f"Home Rotation after assign: {home.rotation}")

    print("Assigning Rosters...")
    home.auto_assign_rosters()
    print(f"Home Rotation after roster assign: {home.rotation}")
    
    # Re-assign roles if roster assignment wiped it?
    if not home.rotation:
        print("Rotation emptied! Re-assigning...")
        home.auto_assign_pitching_roles(TeamLevel.FIRST)
        print(f"Home Rotation after Re-assign: {home.rotation}")

    away.auto_assign_pitching_roles(TeamLevel.FIRST)
    away.auto_assign_rosters()
        
    print("Starting simulation...")
    engine = LiveGameEngine(home, away)
    print(f"Home Rotation inside engine (via object): {engine.home_team.rotation}")
    
    # Run slightly less loop to just check start
    step = 0
    while not engine.is_game_over() and step < 20:
        engine.simulate_pitch()
        step += 1
        
    print(f"Game Over. Score: {engine.state.home_score} - {engine.state.away_score}")
    print(f"Home Pitchers Used: {len(engine.state.home_pitchers_used)}")
    print(f"Away Pitchers Used: {len(engine.state.away_pitchers_used)}")

if __name__ == "__main__":
    run_debug_game()
