from models import Team, Player, Position, TeamLevel, PlayerStats, GameResult
from game_state import GameStateManager
import random

# Mock get_recent_stats since it's hard to populate history in test
original_get_recent_stats = Player.get_recent_stats
def mock_get_recent_stats(self, date, days):
    return None # Simplify to rely on overall_rating
Player.get_recent_stats = mock_get_recent_stats

def create_team():
    team = Team(name="TestStrict", league="North")
    
    # Active: 13 Pitchers, 18 Batters
    for _ in range(13): 
        p = Player(name=f"AP_{_}", position=Position.PITCHER, age=20)
        p.stats = PlayerStats()  
        p.stats.velocity = 150 # High rating
        p.stats.control = 80 # A
        p.stats.stamina = 70 # B
        team.players.append(p)
        team.active_roster.append(team.players.index(p))
        
    for _ in range(18):
        p = Player(name=f"AB_{_}", position=Position.CATCHER, age=20) 
        p.stats = PlayerStats()
        p.stats.contact = 3 # High rating
        p.stats.power = 150
        team.players.append(p)
        team.active_roster.append(team.players.index(p))
        
    # Farm: 5 Pitchers, 5 Batters (Catchers)
    for _ in range(5):
        p = Player(name=f"FP_{_}", position=Position.PITCHER, age=20)
        p.stats = PlayerStats()
        team.players.append(p)
        team.farm_roster.append(team.players.index(p))
        
    for _ in range(5):
        p = Player(name=f"FB_{_}", position=Position.CATCHER, age=20)
        p.stats = PlayerStats()
        p.stats.contact = 1 # Low rating
        p.stats.power = 50
        team.players.append(p)
        team.farm_roster.append(team.players.index(p))
    
    return team

gsm = GameStateManager()
team = create_team()
gsm.all_teams = [team]

# Case 1: Active Pitcher Injured (Force Swap)
injured_p_idx = team.active_roster[0]
injured_p = team.players[injured_p_idx]
injured_p.injury_days = 10 # Injured
print(f"Injured Player: {injured_p.name} (Idx: {injured_p_idx})")

# Farm pitcher good score
good_farm_p_idx = team.farm_roster[0]
good_farm_p = team.players[good_farm_p_idx]
good_farm_p.stats.velocity = 155 # Better
good_farm_p.stats.control = 90 # S
print(f"Farm Candidate: {good_farm_p.name} (Idx: {good_farm_p_idx})")

# Run moves
gsm._perform_roster_moves(team)

# Verify Swap
if injured_p_idx in team.farm_roster and good_farm_p_idx in team.active_roster:
    print("Test 1 Passed: Injured Pitcher swapped with Farm Pitcher")
else:
    print(f"Test 1 Failed: Injured in Level {injured_p.team_level}, Farm in Level {good_farm_p.team_level}")
    print(f"Active Roster: {team.active_roster}")
    print(f"Farm Roster: {team.farm_roster}")

# Case 2: Active Catcher Slumping (Performance Swap), but Farm Catcher is bad (No Swap)
# Pick a random catcher from active
slump_c_idx = team.active_roster[-1] # Last batter
slump_c = team.players[slump_c_idx]
slump_c.condition = 1 # Bad condition
slump_c.stats.contact = 1 # Low stats to ensure low score

# Ensure farm catcher is bad
bad_farm_c_idx = team.farm_roster[-1]
bad_farm_c = team.players[bad_farm_c_idx]
bad_farm_c.stats.contact = 1
bad_farm_c.stats.power = 10 

print(f"Slumping Catcher: {slump_c.name}")
print(f"Bad Farm Catcher: {bad_farm_c.name}")

# Reset moves count limit by re-instantiating or just calling again (limit is local variable)
gsm._perform_roster_moves(team)

if slump_c_idx in team.active_roster:
    print("Test 2 Passed: Slumping Catcher NOT swapped suitable replacement")
else:
    print("Test 2 Failed: Slummping Catcher was swapped incorrectly")

p_count = len([i for i in team.active_roster if team.players[i].position == Position.PITCHER])
b_count = len([i for i in team.active_roster if team.players[i].position != Position.PITCHER])
print(f"Active Pitchers: {p_count}")
print(f"Active Batters: {b_count}")
if p_count == 13 and b_count == 18:
    print("Roster Balance Verified")
else:
    print("Roster Balance FAILED")
