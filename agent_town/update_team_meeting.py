import re

with open("engine/scheduler.py", "r") as f:
    content = f.read()

# We want to replace lines 320 to 358:
replacement = '''    # ── Part B: Relationship updates for all pairs ────────────────────────────
    for i in range(len(agents)):
        for j in range(i + 1, len(agents)):
            a = agents[i]
            b = agents[j]

            rel_ab = a["relationships"].setdefault(b["id"], {"affinity": 50, "interactions": 0})
            rel_ba = b["relationships"].setdefault(a["id"], {"affinity": 50, "interactions": 0})
            
            old_ab = rel_ab["affinity"]
            old_ba = rel_ba["affinity"]

            # Only do the expensive update if in same department or affinity > 60
            if a.get("department") == b.get("department") or old_ab > 60:
                from engine.llm_client import decide_relationship_update
                
                # Gather recent shared memories
                shared = []
                for m in a.get("memory", [])[-30:]:
                    if b["name"] in m.get("text", ""): shared.append(m)
                for m in b.get("memory", [])[-30:]:
                    if a["name"] in m.get("text", ""): shared.append(m)
                
                res = decide_relationship_update(a, b, shared)
                if res:
                    delta = res.get("affinity_delta", 0)
                    rel_ab["note"] = res.get("note", "")
                    rel_ba["note"] = res.get("note", "")
                else:
                    delta = random.randint(-1, 1)
            else:
                delta = random.randint(-1, 1)

            rel_ab["affinity"]     = max(0, min(100, old_ab + delta))
            rel_ab["interactions"] += 1
            rel_ba["affinity"]     = max(0, min(100, old_ba + delta))
            rel_ba["interactions"] += 1

            # Threshold crossing — log once per pair (using A's view)
            new_ab = rel_ab["affinity"]
            if old_ab < 70 and new_ab >= 70:
                msg = f"Day {day}: {a['name']} and {b['name']} are becoming close friends."
                world["event_log"].append(msg)
                a["memory"].append(create_memory(day, msg, importance=8))
                b["memory"].append(create_memory(day, msg, importance=8))
            elif old_ab >= 30 and new_ab < 30:
                msg = f"Day {day}: {a['name']} and {b['name']} are growing tense with each other."
                world["event_log"].append(msg)
                a["memory"].append(create_memory(day, msg, importance=8))
                b["memory"].append(create_memory(day, msg, importance=8))
'''

# Use regex to find the block
pattern = re.compile(r'    # ── Part B: Relationship updates for all pairs ────────────────────────────.*?(?=    # ── Group Meeting Narrative ──────────────────────────────────────────────)', re.DOTALL)
content = pattern.sub(replacement, content)

# Now find where we process each agent after the meeting, to add weekly reflection
pattern2 = re.compile(r'        agent\["memory"\]\.append\(create_memory\(day, f"Day \{day\}: \{agent\[\\\'name\\\'\]\} attended the team meeting", importance=2\)\)')
rep2 = '''        agent["memory"].append(create_memory(day, f"Day {day}: {agent['name']} attended the team meeting", importance=2))
        
        # Weekly reflection
        from engine.llm_client import generate_weekly_reflection
        recent_mems = agent.get("memory", [])[-15:] # Last 15 events
        reflection = generate_weekly_reflection(agent, recent_mems)
        if reflection:
            agent["memory"].append(create_memory(day, reflection, type="reflection", importance=9))'''
            
content = content.replace('        agent["memory"].append(create_memory(day, f"Day {day}: {agent[\'name\']} attended the team meeting", importance=2))', rep2)

with open("engine/scheduler.py", "w") as f:
    f.write(content)
print("Updated team meeting logic successfully")
