
from live_game_engine import NPBPitcherManager, GameState
from models import Team, Player, Position, PitcherRole, PitchType
from unittest.mock import MagicMock
import random

def create_mock_player(name, role_type, stamina=100, is_left=False, overall=50):
    p = Player(name=name, position=Position.PITCHER)
    p.stats = MagicMock()
    p.stats.stamina = stamina
    p.stats.overall_pitching.return_value = overall
    p.current_stamina = float(stamina) # Initially full
    p.throw_hand = "左" if is_left else "右" # Use correct attribute if known, else mock
    p.throws = "左" if is_left else "右"
    p.pitch_type = role_type
    p.team_level = None 
    return p

def verify_logic():
    print("Verifying Pitcher Logic...")
    manager = NPBPitcherManager()
    
    # Setup Team
    team = Team(name="TestTeam", league="North")
    
    # 1. Create Staff
    starter1 = create_mock_player("Starter1", PitchType.STARTER, stamina=80)
    setupA = create_mock_player("SetupA", PitchType.RELIEVER, stamina=40, overall=85)
    setupB = create_mock_player("SetupB", PitchType.RELIEVER, stamina=40, overall=80)
    closer = create_mock_player("Closer", PitchType.CLOSER, stamina=40, overall=90)
    middle1 = create_mock_player("Middle1", PitchType.RELIEVER, stamina=50, overall=70) # Lefty?
    
    team.players = [starter1, setupA, setupB, closer, middle1]
    # Indices
    team.active_roster = [0, 1, 2, 3, 4]
    team.rotation = [0]
    team.setup_pitchers = [1, 2] # A=1, B=2
    team.closers = [3]
    
    # --- Check 1: Starter Fatigue ---
    state = GameState()
    state.is_top = True # Home team pitching (Defending)
    state.home_score = 3
    state.away_score = 0
    state.inning = 6
    state.outs = 0
    state.home_pitchers_used = []  # Initialize list
    
    # Mock engine state values
    state.home_pitcher_stamina = 10.0 # Low!
    state.home_pitch_count = 100
    state.home_current_pitcher_runs = 2
    
    # Next batter (irrelevant mostly)
    batter = MagicMock()
    batter.bats = "右"
    
    # Call check
    replacement = manager.check_pitcher_change(state, team, MagicMock(), batter, starter1)
    
    print(f"Test 1 (Starter Fatigue < 20): Replacement = {replacement.name if replacement else 'None'}")
    if replacement is None: print("FAIL: Should have replaced tired starter")
    
    # --- Check 2: Setup A Usage (Winning Pattern, 8th inning) ---
    state.inning = 8
    state.outs = 0
    state.home_score = 3
    state.away_score = 2 # Lead by 1, Close!
    
    # Starter is done. Current pitcher is... say Middle1, who just finished 7th?
    # Or actually, we assume current is Starter and needs replacement.
    # verify _select_reliever output directly.
    
    # Mock state so starter is definitely out
    state.home_pitcher_stamina = 5.0
    
    reliever = manager._select_reliever(team, state, 1, batter, starter1) # score_diff 1
    print(f"Test 2 (8th Inning Lead): Reliever = {reliever.name if reliever else 'None'}")
    if reliever != setupA: print(f"FAIL: Expected SetupA, got {reliever.name if reliever else 'None'}")

    # --- Check 3: Closer Usage (9th Inning Save) ---
    state.inning = 9
    reliever = manager._select_reliever(team, state, 1, batter, setupA)
    print(f"Test 3 (9th Inning Lead): Reliever = {reliever.name if reliever else 'None'}")
    if reliever != closer: print(f"FAIL: Expected Closer, got {reliever.name if reliever else 'None'}")

    # --- Check 4: Straddle Prevention (Middle Reliever) ---
    state.inning = 7
    state.outs = 0
    state.home_score = 0
    state.away_score = 5 # Losing
    
    # Current pitcher is Middle1, pitched last inning (IP > 0)
    # Pitcher Role check needs to identify him as Middle
    
    # Simulate Middle1 having pitched 0.1 innings previous inning
    current_ip = 0.1 
    state.home_pitchers_used = [middle1] # Key fix: Mark as used
    
    # check_pitcher_change
    # NOTE: middle1 is NOT setup/closer.
    
    reason_change = manager.check_pitcher_change(state, team, MagicMock(), batter, middle1, current_pitcher_ip=current_ip)
    
    print(f"Test 4 (Straddle Prevention): Change Middle1 at start of inning? {reason_change.name if reason_change else 'None'}")
    if reason_change is None: print("FAIL: Should have changed Middle reliever at start of new inning")


if __name__ == "__main__":
    verify_logic()
