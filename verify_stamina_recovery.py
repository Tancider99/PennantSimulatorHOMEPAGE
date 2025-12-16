
from models import Player, Position, PlayerStats
from unittest.mock import MagicMock

def test_stamina_recovery():
    print("Testing Stamina Recovery Logic...")
    
    # Mock Player
    p = Player(name="TestPitcher", position=Position.PITCHER)
    p.stats = MagicMock()
    p.stats.stamina = 50 # Standard Stamina
    
    # 1. Simulate Tired State
    p.current_stamina = 0.0
    p.days_rest = 0
    # p.is_injured = False (Property)
    p.injury_days = 0
    
    print(f"Initial State: Stamina={p.current_stamina}, Rest={p.days_rest}")
    
    # 2. Daily Recovery (Day 1)
    p.recover_daily()
    print(f"Day 1 Recovery: Stamina={p.current_stamina}, Rest={p.days_rest}")
    
    # Expected: rest=1, stamina += 30 + (50*0.2) = 40 => 40.0
    if p.days_rest != 1: print("FAIL: Days rest not incremented")
    if p.current_stamina < 39: print("FAIL: Stamina not recovered enough")
    
    # 3. Daily Recovery (Day 2)
    p.recover_daily()
    print(f"Day 2 Recovery: Stamina={p.current_stamina}, Rest={p.days_rest}")
    
    # Expected: rest=2, stamina += 40 => 80.0
    if p.days_rest != 2: print("FAIL: Days rest not incremented")
    if p.current_stamina < 79: print("FAIL: Stamina not recovered enough")

    # 4. Daily Recovery (Day 3)
    p.recover_daily()
    print(f"Day 3 Recovery: Stamina={p.current_stamina}, Rest={p.days_rest}")
    
    # Expected: rest=3, stamina += 40 => 100.0 (Max)
    if p.days_rest != 3: print("FAIL: Days rest not incremented")
    if p.current_stamina < 100: print(f"FAIL: Stamina not fully recovered (Got {p.current_stamina})")
    
    print("Test Complete.")

if __name__ == "__main__":
    test_stamina_recovery()
