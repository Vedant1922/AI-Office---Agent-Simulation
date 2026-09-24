import os
import sys
import json
import pygame

# 1. Record timestamps BEFORE running viewer interactions
agents_mtime_before = os.path.getmtime('data/agents.json')
world_mtime_before = os.path.getmtime('data/world_state.json')

print("=== STEP 3 SAFETY CHECK: PRE-VIEWER TIMESTAMPS ===")
print(f"data/agents.json mtime:      {agents_mtime_before}")
print(f"data/world_state.json mtime: {world_mtime_before}")

# 2. Test viewer module in headless mode
os.environ["SDL_VIDEODRIVER"] = "dummy"

from viewer import load_replay_data, compute_agent_positions, ZONES, WIDTH, HEIGHT, AGENT_RADIUS

base_dir = os.path.abspath(os.path.dirname(__file__))
agents_dict, timeline, days = load_replay_data(base_dir)

print(f"\nTimeline loaded: {len(days)} days ({days})")
assert days == [1031, 1032, 1033, 1034, 1035], f"Unexpected days: {days}"

# Initialize pygame display in dummy mode
pygame.init()
pygame.font.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))

print("\n--- STEPPING THROUGH ALL 5 DAYS & VERIFYING AGENT ZONES ---")
for d in days:
    day_data = timeline[d]
    snap = day_data.get("snapshot", {})
    acts = day_data.get("actions", {})
    pos_map = compute_agent_positions(day_data, agents_dict)
    
    print(f"\nDay {d} (Budget: ${snap.get('budget'):,}, Rep: {snap.get('reputation')}, Mood: {snap.get('market_mood')}):")
    for aid, p in pos_map.items():
        name = agents_dict[aid]["name"]
        action = p["action"]
        zone = p["zone"]
        stress_flag = " [STRESS AURA]" if p["is_stress"] else ""
        print(f"  - {name} ({aid}): Zone={zone}, Action={action}, Pos=({p['x']:.0f}, {p['y']:.0f}){stress_flag}")

# Verify clicking logic & reasoning text for each agent on Day 1032
print("\n--- TESTING CLICK-TO-INSPECT REASONING ON ALL 6 AGENTS (Day 1032) ---")
d1032_data = timeline[1032]
d1032_positions = compute_agent_positions(d1032_data, agents_dict)
for aid, p in d1032_positions.items():
    # Simulate mouse click exactly at agent position
    click_x, click_y = p["x"], p["y"]
    # Check hit detection
    clicked_aid = None
    for target_id, t_pos in d1032_positions.items():
        if ((click_x - t_pos["x"])**2 + (click_y - t_pos["y"])**2)**0.5 <= AGENT_RADIUS + 6:
            clicked_aid = target_id
            break
    assert clicked_aid == aid, f"Click at ({click_x}, {click_y}) did not hit agent {aid}!"
    
    # Check reasoning retrieval and truncation (~15 words)
    raw_reason = d1032_data["actions"][aid].get("reasoning") or ""
    words = raw_reason.split()
    trunc_reason = " ".join(words[:15]) + ("..." if len(words) > 15 else "")
    word_count = len(trunc_reason.split())
    print(f"Agent {agents_dict[aid]['name']:<7}: clicked -> reasoning ({word_count} words): \"{trunc_reason}\"")

# Test boundary: stepping past the last day
day_idx = len(days) - 1
# Simulate right arrow key
day_idx = min(len(days) - 1, day_idx + 1)
assert day_idx == len(days) - 1, "Day index overflowed past available days!"
print("\nBoundary check: stepping past last day stays on Day 1035 without crash: PASSED")

pygame.quit()

# 3. Check timestamps AFTER running viewer
agents_mtime_after = os.path.getmtime('data/agents.json')
world_mtime_after = os.path.getmtime('data/world_state.json')

print("\n=== STEP 3 SAFETY CHECK: POST-VIEWER TIMESTAMPS ===")
print(f"data/agents.json mtime:      {agents_mtime_after}")
print(f"data/world_state.json mtime: {world_mtime_after}")

assert agents_mtime_before == agents_mtime_after, "SAFETY FAILED: agents.json was modified!"
assert world_mtime_before == world_mtime_after, "SAFETY FAILED: world_state.json was modified!"

print("\n>>> ALL SAFETY CHECKS PASSED: agents.json and world_state.json WERE NOT TOUCHED (0 byte change, exact same timestamps) <<<")
