
from live_game_engine import LiveGameEngine
from models import Team, Player, Position
from unittest.mock import MagicMock, patch

@patch('live_game_engine.generate_best_lineup')
def verify_stamina_init(mock_gen_lineup):
    mock_gen_lineup.return_value = [0] * 9 # return valid-ish lineup indices
    print("Verifying Stamina Initialization...")
    
    # Create Mock Team
    team = Team(name="MockTeam", league="North")
    
    # Create Starter
    starter = Player(name="Starter", position=Position.PITCHER)
    starter.stats = MagicMock()
    starter.stats.stamina = 50 # Base stats
    starter.stats.get_defense_range.return_value = 50 # Valid defense
    starter.current_stamina = 100 # Current Condition
    
    team.players = [starter]
    team.rotation = [0]
    team.active_roster = [0]
    team.get_today_starter = MagicMock(return_value=starter)
    
    # Create Engine
    # We need two teams
    away = Team(name="Away", league="South")
    away_p = Player(name="AwayP", position=Position.PITCHER)
    away_p.stats = MagicMock()
    away_p.stats.stamina = 50
    away_p.stats.get_defense_range.return_value = 50
    away_p.current_stamina = 100
    away.players = [away_p]
    away.rotation = [0]
    away.active_roster = [0]
    
    engine = LiveGameEngine(team, away)
    
    # Check initialized stamina
    # Expected: 50 * 2.2 * (100/100) = 110.0
    home_stamina = engine.state.home_pitcher_stamina
    print(f"Home Starter Stamina: {home_stamina}")
    
    expected = 50 * 2.2
    if abs(home_stamina - expected) < 0.1:
        print("PASS: Stamina multiplier is 2.2")
    else:
        print(f"FAIL: Expected {expected}, got {home_stamina}")

if __name__ == "__main__":
    verify_stamina_init()
