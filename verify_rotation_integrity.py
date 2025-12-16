
from models import Team, Player, Position, TeamLevel
from live_game_engine import LiveGameEngine
from unittest.mock import MagicMock

def create_test_team(name):
    t = Team(name=name, league="North")
    t.players = []
    # Create 6 starters
    for i in range(6):
        p = Player(name=f"Starter{i}", position=Position.PITCHER)
        p.stats = MagicMock()
        p.stats.stamina = 50
        p.stats.overall_pitching.return_value = 50
        p.current_stamina = 100
        p.days_rest = 6 # Fully rested
        p.starter_aptitude = 4
        p.midle_aptitude = 1
        p.closer_aptitude = 1
        t.players.append(p)
    
    t.active_roster = list(range(6))
    t.rotation = list(range(6)) # 0..5
    t.rotation_index = 0
    return t

def diagnose_rotation():
    print("Starting Rotation Diagnosis...")
    home = create_test_team("Home")
    
    # Simulate 7 days
    for day in range(1, 8):
        print(f"\n--- Day {day} ---")
        
        # 1. Update Status (Morning)
        print("Updating Status (recover_daily)...")
        for p in home.players:
            # Emulate recover_daily
            p.days_rest += 1
            # (stamina recovery omitted for brevity, focusing on Rest)
        
        # 2. Select Starter
        starter = home.get_today_starter()
        print(f"Selected Starter: {starter.name} (Rest: {starter.days_rest})")
        
        # 3. Simulate Game (Mock)
        # Assume starter pitches
        if starter:
            starter.days_rest = 0 # Reset rest
            print(f"Game played. {starter.name} days_rest reset to 0.")
        
        # 4. Rotate Index
        home.rotation_index = (home.rotation_index + 1) % len(home.rotation)
        print(f"Rotation Index advanced to {home.rotation_index}")
        
        # Check against "Same Pitcher" bug
        if day > 1 and starter.name == "Starter0" and day < 6:
            print("FAILURE: Starter0 pitched again too soon!")

if __name__ == "__main__":
    diagnose_rotation()
