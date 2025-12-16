from models import Team, Player, Position, TeamLevel, PlayerStats
from game_state import GameStateManager

# Mock auto_assign_rosters to track calls
call_count = 0
original_auto = Team.auto_assign_rosters
def mock_auto_assign(self):
    global call_count
    call_count += 1
    # Call original to actually fix it
    original_auto(self)

Team.auto_assign_rosters = mock_auto_assign

def create_broken_team():
    team = Team(name="BrokenTeam", league="North")
    
    # 12 Pitchers (Old Logic)
    for _ in range(12): 
        p = Player(name=f"AP_{_}", position=Position.PITCHER, age=20)
        p.stats = PlayerStats()
        team.players.append(p)
        team.active_roster.append(team.players.index(p))
        
    # 19 Batters (Old Logic) -> Total 31
    for _ in range(19):
        p = Player(name=f"AB_{_}", position=Position.CATCHER, age=20)
        p.stats = PlayerStats()
        team.players.append(p)
        team.active_roster.append(team.players.index(p))
        
    # Add extra players to pool for auto-assign to work
    for _ in range(10): team.players.append(Player(name="ExtraP", position=Position.PITCHER, stats=PlayerStats()))
    for _ in range(10): team.players.append(Player(name="ExtraB", position=Position.CATCHER, stats=PlayerStats()))
        
    return team

gsm = GameStateManager()
team = create_broken_team()
gsm.all_teams = [team]

print(f"Initial Pitchers: {len([i for i in team.active_roster if team.players[i].position == Position.PITCHER])}")
print(f"Initial Total: {len(team.active_roster)}")

# Run manager
# This should trigger auto_assign_rosters because Pitchers (12) < 13
gsm._manage_all_teams_rosters()

print(f"Auto Assign Calls: {call_count}")
p_count = len([i for i in team.active_roster if team.players[i].position == Position.PITCHER])
print(f"Final Pitchers: {p_count}")

if call_count > 0 and p_count == 13:
    print("Verification Passed")
else:
    print("Verification Failed")
