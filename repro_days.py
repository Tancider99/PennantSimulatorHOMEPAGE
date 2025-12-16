from models import Player, Position
from game_state import GameStateManager

# Create dummy player
p = Player(name="TestPlayer", position=Position.PITCHER)
p.days_until_promotion = 10

print(f"Initial days: {p.days_until_promotion}")

# Simulate daily update
try:
    p.recover_daily()
    print(f"After daily update: {p.days_until_promotion}")
except Exception as e:
    print(f"Error: {e}")

# Verify logic in context of simple loop
for i in range(5):
    p.recover_daily()
print(f"After 5 more days: {p.days_until_promotion}")

# Check hasattr just in case
print(f"Has recover_daily: {hasattr(p, 'recover_daily')}")
