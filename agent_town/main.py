import sys
from engine.scheduler import run_world_for

if __name__ == "__main__":
    days = 7
    if len(sys.argv) >= 3 and sys.argv[1] == "run":
        try:
            days = int(sys.argv[2])
        except ValueError:
            days = 7
    elif len(sys.argv) >= 2:
        try:
            days = int(sys.argv[1])
        except ValueError:
            days = 7
    print(f"=== Agent Town: Running World Simulation for {days} days ===\n")
    run_world_for(days)
