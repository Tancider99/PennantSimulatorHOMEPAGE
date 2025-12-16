from models import Team, Player, Position, TeamLevel, PlayerStats
import random

def create_dummy_player(pos):
    p = Player(name=f"Player_{random.randint(1000,9999)}", position=pos, age=20)
    p.stats = PlayerStats()  # Use default
    return p

team = Team(name="TestTeam", league="North")

# Create 40 pitchers and 40 batters
for _ in range(40): team.players.append(create_dummy_player(Position.PITCHER))
for _ in range(40): team.players.append(create_dummy_player(Position.CATCHER))

team.auto_assign_rosters()

active_pitchers = [p for i, p in enumerate(team.players) if i in team.active_roster and p.position == Position.PITCHER]
active_batters = [p for i, p in enumerate(team.players) if i in team.active_roster and p.position != Position.PITCHER]

print(f"Active Pitchers: {len(active_pitchers)}")
print(f"Active Batters: {len(active_batters)}")
assert len(active_pitchers) == 13
assert len(active_batters) == 18
print("Verification Passed")
