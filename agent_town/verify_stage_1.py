import json
import os

print("=== STAGE 1 VERIFICATION AUDIT ===")

# ── 1. Check agents.json and world_state.json ─────────────────────────────────
world = json.load(open('data/world_state.json', encoding='utf-8'))
agents = json.load(open('data/agents.json', encoding='utf-8'))

expected_world_keys = ['company_budget', 'current_day', 'departments', 'event_log', 'last_negative_rep_day', 'last_quarter_revenue_snapshot', 'market_days_remaining', 'market_mood', 'morale_index', 'reputation']
actual_world_keys = sorted(list(world.keys()))

expected_agent_keys = ['department', 'energy', 'hunger', 'id', 'memory', 'money', 'morale', 'name', 'personality', 'pronoun', 'relationships', 'role', 'social', 'stress']
actual_agent_keys = sorted(list(agents[0].keys()))

print("1. File Schema & Integrity:")
print(f" - world_state.json current_day: {world['current_day']} (advanced 5 days from 1031 to 1036)")
print(f" - world_state.json keys match expected: {actual_world_keys == expected_world_keys}")
print(f" - agents.json agent count: {len(agents)} (all 6 persistent agents)")
print(f" - agents.json keys match expected: {actual_agent_keys == expected_agent_keys}")

# ── 2. Check daily_world_snapshot.jsonl ───────────────────────────────────────
snap_path = 'data/daily_world_snapshot.jsonl'
print(f"\n2. daily_world_snapshot.jsonl ({snap_path}):")
print(f" - Exists: {os.path.exists(snap_path)}")
with open(snap_path, 'r', encoding='utf-8') as f:
    snap_lines = [json.loads(line) for line in f if line.strip()]

print(f" - Total lines: {len(snap_lines)} (expected 5, exactly 1 per day)")
for s in snap_lines:
    print(f"   * {s}")

# ── 3. Check daily_actions.jsonl ──────────────────────────────────────────────
act_path = 'data/daily_actions.jsonl'
print(f"\n3. daily_actions.jsonl ({act_path}):")
print(f" - Exists: {os.path.exists(act_path)}")
with open(act_path, 'r', encoding='utf-8') as f:
    act_lines = [json.loads(line) for line in f if line.strip()]

print(f" - Total lines: {len(act_lines)} (expected 30: 5 days * 6 agents)")
days_found = sorted(list(set(a['day'] for a in act_lines)))
print(f" - Days covered: {days_found}")

for d in days_found:
    day_acts = [a for a in act_lines if a['day'] == d]
    print(f"   Day {d}: {len(day_acts)} agent actions logged:")
    for act in day_acts:
        r_snippet = str(act['reasoning'])[:60] if act['reasoning'] else 'None'
        print(f"     [{act['agent_id']}] {act['name']:<7} ({act['department']:<11}): {act['action']:<12} | target={act['target_agent_id']} | reason={r_snippet}...")
