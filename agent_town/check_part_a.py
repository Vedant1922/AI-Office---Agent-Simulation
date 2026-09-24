import json

agents = json.load(open('data/agents.json', encoding='utf-8'))
world = json.load(open('data/world_state.json', encoding='utf-8'))

print("=== PART A.1: 4 VERBATIM WEEKLY REFLECTIONS ===")
# Find reflections from 4 different agents at 4 different weeks
chosen = []
agent_names = ["Sam", "Priya", "Alex", "Jordan", "Riya", "Vikram"]
target_agents = ["Sam", "Priya", "Alex", "Vikram"]

for a in agents:
    if a["name"] in target_agents:
        reflections = [m for m in a.get("memory", []) if isinstance(m, dict) and m.get("type") == "reflection"]
        if reflections:
            # Let's pick different weeks/periods for variety
            chosen.append((a["name"], reflections))

# Print 4 distinct reflections
for name, refs in chosen:
    print(f"\nAgent: {name} (Total reflections: {len(refs)})")
    # pick one representative from different points
    if name == "Sam":
        r = refs[len(refs)//4] # early-mid
    elif name == "Priya":
        r = refs[len(refs)//2] # mid
    elif name == "Alex":
        r = refs[3*len(refs)//4] # mid-late
    else:
        r = refs[-1] # late
    print(f"Day {r.get('day')}: \"{r.get('text')}\"")

print("\n=== PART A.2: SEARCH FOR 'TENSE' IN FULL EVENT LOG & MEMORIES ===")
event_log = world.get("event_log", [])
tense_events = [e for e in event_log if "tense" in e.lower() or "growing tense" in e.lower()]
print(f"Total 'tense' events in world event_log ({len(event_log)} total events): {len(tense_events)}")
for e in tense_events:
    print(f" - {e}")

# Also check chronicle files and all agent memories
tense_in_mem = []
for a in agents:
    for m in a.get("memory", []):
        t = m.get("text", "") if isinstance(m, dict) else str(m)
        if "tense" in t.lower() or "growing tense" in t.lower():
            tense_in_mem.append((a["name"], m.get("day") if isinstance(m, dict) else "unknown", t))

print(f"Total 'tense' mentions in agent memories: {len(tense_in_mem)}")
for name, d, t in tense_in_mem:
    print(f" - [{name} Day {d}]: {t}")

print("\n=== PART A.3: CHECK FOR 'relationship_notes' IN agents.json ===")
has_rel_notes_field = False
rel_notes_examples = []

for a in agents:
    # Check top level
    if "relationship_notes" in a:
        has_rel_notes_field = True
        rel_notes_examples.append((a["name"], "top-level", a["relationship_notes"]))
    # Check inside relationships dict: a["relationships"][other_id]["note"] or "relationship_notes"
    rels = a.get("relationships", {})
    for other_id, rdata in rels.items():
        if isinstance(rdata, dict):
            if "relationship_notes" in rdata:
                has_rel_notes_field = True
                rel_notes_examples.append((a["name"], f"rel to {other_id}", rdata["relationship_notes"]))
            if "note" in rdata and rdata["note"]:
                rel_notes_examples.append((a["name"], f"rel.note to {other_id}", rdata["note"]))

print(f"Direct key 'relationship_notes' exists? {has_rel_notes_field}")
print(f"Total relationship notes/notes found: {len(rel_notes_examples)}")
for ex in rel_notes_examples[:5]:
    print(f" - [{ex[0]} -> {ex[1]}]: {ex[2]}")
