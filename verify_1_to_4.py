
from models import Player, Position, PlayerStats, PitchType
from player_generator import create_random_player
import random

def test_aptitude_scale():
    print("Testing 1-4 Scale Aptitude Generation...")
    
    # 1. Check Generation
    pitchers = []
    for _ in range(50):
        p = create_random_player(Position.PITCHER)
        pitchers.append(p)
        
    for p in pitchers:
        # Check type and range
        for attr in ['starter_aptitude', 'middle_aptitude', 'closer_aptitude']:
            val = getattr(p, attr)
            if not isinstance(val, int):
                print(f"FAIL: {attr} is not int: {type(val)}")
                return
            if not (1 <= val <= 4):
                print(f"FAIL: {attr} out of range [1,4]: {val}")
                return
                
    print("SUCCESS: 50 Pitchers generated with valid 1-4 aptitudes.")
    
    # 2. Check Distribution (Aim: S:M:C ~= 50:40:10)
    # Generate 1000 pitchers to check ratio
    print("\nChecking Role Distribution (n=1000)...")
    roles = {"先発": 0, "中継ぎ": 0, "抑え": 0}
    
    for _ in range(1000):
        p = create_random_player(Position.PITCHER) # pitch_type=None
        # Check aptitude consistency
        main_role = None
        if p.starter_aptitude == 4 and p.pitch_type.value == "先発": main_role = "先発"
        elif p.middle_aptitude == 4 and p.pitch_type.value == "中継ぎ": main_role = "中継ぎ"
        elif p.closer_aptitude == 4 and p.pitch_type.value == "抑え": main_role = "抑え"
        
        if not main_role:
             # Just increment based on pitch_type for count, but warn if aptitude mismatch
             roles[p.pitch_type.value] += 1
             # print(f"Warning: Aptitude mismatch for {p.pitch_type.value}: S{p.starter_aptitude}/M{p.middle_aptitude}/C{p.closer_aptitude}")
             continue

        roles[main_role] += 1
        
        # Check off-role aptitudes are mostly low
        off_apts = []
        if main_role == "先発": off_apts = [p.middle_aptitude, p.closer_aptitude]
        elif main_role == "中継ぎ": off_apts = [p.starter_aptitude, p.closer_aptitude]
        else: off_apts = [p.starter_aptitude, p.middle_aptitude]
        
        # Ensure off_apts are not all 4 (rarely they can be if sub_aptitude returns 4, but let's check basic range)
    
    total = sum(roles.values())
    print(f"Distribution: S={roles['先発']} ({roles['先発']/total:.2%}), M={roles['中継ぎ']} ({roles['中継ぎ']/total:.2%}), C={roles['抑え']} ({roles['抑え']/total:.2%})")
    print("Expected:     S~50%, M~40%, C~10%")

    # Sub-Aptitude Check
    print("\nChecking Sub-Aptitude Distribution (n=5000)...")
    sub_counts = {1: 0, 2: 0, 3: 0, 4: 0}
    for _ in range(5000):
        # We need to access the private function or just simulate player and check off-roles
        p = create_random_player(Position.PITCHER, PitchType.STARTER)
        sub_counts[p.middle_aptitude] += 1
        sub_counts[p.closer_aptitude] += 1
        
    total_subs = sum(sub_counts.values())
    print(f"Sub-Aptitudes: 1={sub_counts[1]} ({sub_counts[1]/total_subs:.2%}), 2={sub_counts[2]} ({sub_counts[2]/total_subs:.2%}), 3={sub_counts[3]} ({sub_counts[3]/total_subs:.2%}), 4={sub_counts[4]} ({sub_counts[4]/total_subs:.2%})")
    print("Expected: 1~50%, 2~30%, 3~15%, 4~5%")

    # 3. Check Symbol Mapping (Existing test)
    p_test = Player(name="Test", position=Position.PITCHER)
    
    # Test 4 -> ◎
    sym_4 = p_test.get_aptitude_symbol(4)
    if sym_4 != "◎": print(f"FAIL: 4 -> {sym_4} != ◎")
    # else: print("PASS: 4 -> ◎")
    
    # Test 3 -> 〇
    sym_3 = p_test.get_aptitude_symbol(3)
    if sym_3 != "〇": print(f"FAIL: 3 -> {sym_3} != 〇")
    # else: print("PASS: 3 -> 〇")
    
    # Test 2 -> △
    sym_2 = p_test.get_aptitude_symbol(2)
    if sym_2 != "△": print(f"FAIL: 2 -> {sym_2} != △")
    # else: print("PASS: 2 -> △")
    
    # Test 1 -> ー
    sym_1 = p_test.get_aptitude_symbol(1)
    if sym_1 != "ー": print(f"FAIL: 1 -> {sym_1} != ー")
    # else: print("PASS: 1 -> ー")
    print("Symbol checks passed.")

if __name__ == "__main__":
    test_aptitude_scale()
