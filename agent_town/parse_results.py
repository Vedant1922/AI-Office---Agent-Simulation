import json

with open("data/agents.json", "r") as f:
    agents = json.load(f)

print("=== SAMPLE WEEKLY REFLECTIONS ===")
for a in agents:
    reflections = [m for m in a.get("memory", []) if isinstance(m, dict) and m.get("type") == "reflection"]
    if reflections:
        print(f"[{a['name']}]: {reflections[-1]['text']}")

print("\n=== SAMPLE RELATIONSHIP NOTES ===")
for a in agents:
    rels = a.get("relationships", {})
    for b_id, rel in list(rels.items())[:1]: # just get the first one
        # find name of b_id
        b_name = next((x["name"] for x in agents if x["id"] == b_id), b_id)
        note = rel.get("note")
        if note:
            print(f"[{a['name']} -> {b_name}]: {note} (affinity: {rel['affinity']})")

print("\n=== SAMPLE LLM REASONING ===")
for a in agents[:3]:
    thoughts = [m for m in a.get("memory", []) if isinstance(m, dict) and "[LLM Thought:" in m.get("text", "")]
    if thoughts:
        print(f"[{a['name']}]: {thoughts[-1]['text']}")
