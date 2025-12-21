
import sys
import os
import math
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import Team, Player, Position, League, TeamLevel
from live_game_engine import LiveGameEngine, AdvancedDefenseEngine, FIELD_COORDS

def create_mock_team(name):
    team = Team(name, League.NORTH)
    for i in range(10):
        p = Player(f"{name}_P{i}", Position.PITCHER if i==0 else Position.CATCHER)
        # Give some base stats
        p.record.at_bats = 10
        p.record.hits = 3 # Avg .300
        p.record.home_runs = 1
        p.record.rbis = 2
        
        p.record.innings_pitched = 9.0
        p.record.earned_runs = 3 # ERA 3.00
        p.record.strikeouts_pitched = 5
        
        team.players.append(p)
    
    # Set lineup
    team.current_lineup = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    return team

def verify_realtime_stats():
    print("=== Verifying Real-time Stats ===")
    home = create_mock_team("HOME")
    away = create_mock_team("AWAY")
    engine = LiveGameEngine(home, away)
    
    player = home.players[1] # Catcher
    
    # Check initial (Season only)
    rt = engine.get_realtime_stats(player)
    print(f"Initial: AVG {rt['avg']:.3f}, HR {rt['hr']}, ERA {rt['era']:.2f}")
    
    if abs(rt['avg'] - 0.300) > 0.001: print("FAIL: Initial AVG mismatch")
    
    # Simulate some game stats
    engine.game_stats[player]['at_bats'] = 4
    engine.game_stats[player]['hits'] = 2 # 2-for-4
    engine.game_stats[player]['home_runs'] = 1
    engine.game_stats[player]['rbis'] = 3
    
    # Check new stats
    # Total AB: 10 + 4 = 14
    # Total Hits: 3 + 2 = 5
    # New AVG: 5/14 = .357
    rt = engine.get_realtime_stats(player)
    print(f"Updated: AVG {rt['avg']:.3f}, HR {rt['hr']}, RBI {rt['rbi']}")
    
    if abs(rt['avg'] - 0.357) > 0.001: print("FAIL: Real-time AVG mismatch")
    if rt['hr'] != 2: print("FAIL: Real-time HR mismatch")
    if rt['rbi'] != 5: print("FAIL: Real-time RBI mismatch")
    
    print("Real-time Stats Verification Done")

def verify_defense_shifts():
    print("\n=== Verifying Defense Shifts ===")
    home = create_mock_team("HOME")
    # Need to set positions for players to be found
    home.players[1].position = Position.FIRST
    home.players[2].position = Position.SECOND
    home.players[3].position = Position.THIRD
    home.players[4].position = Position.SHORTSTOP
    home.players[5].position = Position.LEFT
    home.players[6].position = Position.CENTER
    home.players[7].position = Position.RIGHT
    
    eng = AdvancedDefenseEngine()
    
    # 1. Normal
    _, _, init_normal = eng._find_nearest_fielder((0, 95), home, TeamLevel.FIRST, None)
    print(f"Normal Center: {init_normal} (Expected around 0, 95)")
    
    # 2. Outfield Forward (Shallow)
    shifts = {'outfield': '外野浅め'}
    _, _, init_shallow = eng._find_nearest_fielder((0, 95), home, TeamLevel.FIRST, None, shifts=shifts)
    print(f"Shallow Center: {init_shallow}")
    
    if init_shallow[1] >= init_normal[1]:
        print("FAIL: Outfield Shallow did not reduce Y coordinate")

    # 3. Infield Forward
    shifts = {'infield': '前進守備'}
    # Test Shortstop position (normally (-10, 42))
    _, _, init_if_fwd = eng._find_nearest_fielder((-10, 42), home, TeamLevel.FIRST, None, shifts=shifts)
    print(f"Infield Fwd SS: {init_if_fwd} (Normal: {FIELD_COORDS[Position.SHORTSTOP]})")
    
    if init_if_fwd[1] >= FIELD_COORDS[Position.SHORTSTOP][1]:
        print("FAIL: Infield Forward did not reduce Y coordinate")

    # 4. DP Shift (Double Play)
    shifts = {'infield': 'ゲッツーシフト'}
    _, _, init_dp = eng._find_nearest_fielder((-6, 36), home, TeamLevel.FIRST, None, shifts=shifts)
    print(f"DP Shift SS: {init_dp}")
    # Expected SS to be around (-6, 36)
    if init_dp[0] != -6.0 or init_dp[1] != 36.0:
        print("FAIL: DP Shift coordinates incorrect")

    print("Defense Shift Verification Done")

if __name__ == "__main__":
    verify_realtime_stats()
    verify_defense_shifts()
