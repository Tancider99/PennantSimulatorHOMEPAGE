
import sys
import os
import random
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Team, Player, Position, League, TeamLevel
from live_game_engine import LiveGameEngine, AIManager, GameState

def create_mock_team(name):
    team = Team(name, League.NORTH)
    for i in range(10):
        pos = Position.PITCHER if i==0 else list(Position)[i]
        p = Player(f"{name}_{pos.name}", pos)
        # Standard stats
        p.stats.trajectory = 2
        p.stats.contact = 50
        p.stats.power = 50
        p.stats.speed = 50
        p.stats.arm = 50
        p.stats.defense_ranges = {pos: 50}
        p.stats.error = 50
        p.stats.bunt_sac = 50
        
        team.players.append(p)
    team.current_lineup = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    return team

def verify_ai_strategy():
    print("=== Verifying AI Strategy ===")
    home = create_mock_team("HOME")
    away = create_mock_team("AWAY")
    
    # Needs to init engine to set up state
    _ = LiveGameEngine(home, away)
    ai = AIManager()
    state = GameState()
    
    # 1. Verify Squeeze
    state.top_bot = 0 # Bottom (Home attacking)
    state.outs = 1
    state.runner_3b = home.players[8] # Runner on 3rd
    state.home_score = 0; state.away_score = 1 # Losing by 1
    state.inning = 9
    
    batter = home.players[0] # Pitcher (weak hitter)
    batter.stats.contact = 10
    
    strategy = ai.decide_strategy(state, home, away, batter)
    print(f"Scenario: 1 Out, Runner 3B, Losing by 1, Pitcher Batting -> Strategy: {strategy}")
    if strategy != "SQUEEZE" and strategy != "BUNT": # Bunt is also acceptable
        print("FAIL: Expected SQUEEZE or BUNT")
        
    # 2. Verify Infield Forward Shift
    # Same scenario
    defense_ai_shifts = ai.decide_defensive_shifts(state, home, away, batter, away.players[0])
    print(f"Scenario: Runner 3B, < 2 Outs, Close Game -> Defense: {defense_ai_shifts['infield']}")
    if defense_ai_shifts['infield'] != "前進守備":
        print("FAIL: Expected '前進守備'")

    # 3. Verify Outfield Deep Shift (Slugger)
    slugger = home.players[4] # Cleanup?
    slugger.stats.power = 85
    state.runner_3b = None
    state.outs = 0
    state.inning = 1
    
    defense_ai_shifts = ai.decide_defensive_shifts(state, home, away, slugger, away.players[0])
    print(f"Scenario: Slugger (Power 85) -> Defense: {defense_ai_shifts['outfield']}")
    if defense_ai_shifts['outfield'] != "外野深め":
        print("FAIL: Expected '外野深め'")

    # 4. Verify Nagashi (Runner 1B, Right Hitter)
    state.runner_1b = home.players[1]
    state.outs = 1
    contact_hitter = home.players[2]
    contact_hitter.stats.contact = 60
    contact_hitter.bats = "右" # Set right handed manually
    
    # Force random seed or loop to hit probability
    found_nagashi = False
    for _ in range(20):
        strat = ai.decide_strategy(state, home, away, contact_hitter)
        if strat == "NAGASHI":
            found_nagashi = True
            break
    print(f"Scenario: Runner 1B, Contact Hitter -> Found Nagashi? {found_nagashi}")
    
    print("AI Strategy Verification Done")

if __name__ == "__main__":
    verify_ai_strategy()
