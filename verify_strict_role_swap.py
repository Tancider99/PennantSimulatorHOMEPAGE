from models import Team, Player, Position, TeamLevel, PlayerStats
from game_state import GameStateManager

class MockStats:
    def __init__(self, era=4.0, ops=0.7):
        self.era = era
        self.ops = ops

original_get_recent_stats = Player.get_recent_stats
def mock_get_recent_stats(self, date, days):
    # If high velocity, assume good stats
    if self.stats.velocity > 155: return MockStats(era=2.00)
    if self.stats.velocity < 135: return MockStats(era=20.00) # Bad
    return MockStats(era=4.00)
Player.get_recent_stats = mock_get_recent_stats

def create_team():
    team = Team(name="TestRole", league="North")
    
    # 13 Pitchers
    # 0-5: Starters
    # 6: Closer
    # 7-12: Relief
    for i in range(13): 
        p = Player(name=f"AP_{i}", position=Position.PITCHER, age=20)
        p.stats = PlayerStats()
        p.stats.velocity = 150
        p.stats.control = 80
        p.stats.stamina = 80
        team.players.append(p)
        team.active_roster.append(team.players.index(p))
    
    # Set rotation manually
    team.rotation = list(range(6))
    
    # 18 Batters
    for _ in range(18):
        p = Player(name="AB", position=Position.CATCHER, age=20)
        p.stats = PlayerStats()
        team.players.append(p)
        team.active_roster.append(team.players.index(p))
        
    # Farm Players
    # F0: Starter Aptitude Only (S)
    p = Player(name="F_Starter", position=Position.PITCHER, age=20)
    p.stats = PlayerStats()
    p.starter_aptitude = 4
    p.middle_aptitude = 1
    p.closer_aptitude = 1
    p.stats.velocity = 160 # High score
    p.stats.control = 90
    team.players.append(p)
    team.farm_roster.append(team.players.index(p))
    
    # F1: Relief Aptitude Only (S)
    p = Player(name="F_Relief", position=Position.PITCHER, age=20)
    p.stats = PlayerStats()
    p.starter_aptitude = 1
    p.middle_aptitude = 4
    p.closer_aptitude = 4
    p.stats.velocity = 160 # High score
    p.stats.control = 90
    team.players.append(p)
    team.farm_roster.append(team.players.index(p))
    
    return team

gsm = GameStateManager()
team = create_team()
gsm.all_teams = [team]

# Case 1: Relief Pitcher Demoted (Performance)
# Demote index 12 (last relief)
team.players[12].condition = 1
team.players[12].stats.velocity = 130 # Make score low

# Run moves
print("Starting Roster Moves...")
print(f"Demotion Candidate Condition: {team.players[12].condition}")
print(f"Demotion Candidate Stats Vel: {team.players[12].stats.velocity}")
gsm._perform_roster_moves(team)
print("Finished Roster Moves.")

# Expectation: index 12 demoted, replaced by F_Relief (idx 32)
# F_Starter (idx 31) should NOT be used
if 32 in team.active_roster and 12 in team.farm_roster:
    print("Test 1 Passed: Relief replaced by Relief Aptitude")
elif 31 in team.active_roster:
    print("Test 1 Failed: Relief replaced by Starter Aptitude")
else:
    print("Test 1 Failed: No swap occurred or unexpected")

# Reset
team = create_team()
gsm.all_teams = [team]

# Case 2: Starter Pitcher Demoted (Performance)
# Demote index 0 (Starter)
team.players[0].condition = 1
team.players[0].stats.velocity = 130

gsm._perform_roster_moves(team)

# Expectation: index 0 demoted, replaced by F_Starter (idx 31)
if 31 in team.active_roster and 0 in team.farm_roster:
    print("Test 2 Passed: Starter replaced by Starter Aptitude")
elif 32 in team.active_roster:
    print("Test 2 Failed: Starter replaced by Relief Aptitude")
else:
    print("Test 2 Failed: No swap occurred")
