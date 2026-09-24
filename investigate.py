import json
import re

with open("data/agents.json", "r") as f:
    agents = json.load(f)

# The time window we analyzed was day >= 883
# Let's count all events

stats = {
    "llm_action_calls": 0,
    "hard_override_ate": 0,
    "hard_override_stress": 0,
    "hard_override_burnout": 0,
    "hard_override_rest_early": 0,
    "meetings_attended": 0,
    
    "reflections_generated": 0,
    
    "reciprocal_social": 0,
    "quiet_overreport_drift": 0,
    "project_done": 0,
    "deadline_failed": 0
}

phrases_to_find = [
    "cycle of overreporting",
    "coping mechanism",
    "root issues",
    "root cause"
]

agent_phrase_counts = {a["name"]: {p: 0 for p in phrases_to_find} for a in agents}

for agent in agents:
    recent_mems = [m for m in agent.get("memory", []) if m.get("day", 0) >= 943]
    
    for m in recent_mems:
        text = m.get("text", "")
        t_low = text.lower()
        
        # 1. Classification
        if "LLM Thought:" in text:
            stats["llm_action_calls"] += 1
        elif "stopped to eat" in text:
            stats["hard_override_ate"] += 1
        elif "took a stress day" in text:
            stats["hard_override_stress"] += 1
        elif "burned out and rested" in text:
            stats["hard_override_burnout"] += 1
        elif "rested early" in text:
            stats["hard_override_rest_early"] += 1
        elif "attended the team meeting" in text:
            stats["meetings_attended"] += 1
        elif m.get("type") == "reflection":
            stats["reflections_generated"] += 1
        elif "caught up with" in text:
            stats["reciprocal_social"] += 1
        elif "quietly overreported" in text:
            stats["quiet_overreport_drift"] += 1
        elif "PROJECT DONE" in text:
            stats["project_done"] += 1
        elif "failed to meet the deadline" in text:
            stats["deadline_failed"] += 1
            
        # 2. Phrase matching (including reflections and thoughts)
        for p in phrases_to_find:
            if p in t_low:
                agent_phrase_counts[agent["name"]][p] += 1

print("--- Event Reconciliation ---")
for k, v in stats.items():
    print(f"{k}: {v}")
    
print("\n--- Phrase Matching ---")
for name, counts in agent_phrase_counts.items():
    total_phrases = sum(counts.values())
    if total_phrases > 0:
        print(f"[{name}] Total: {total_phrases}")
        for p, c in counts.items():
            if c > 0:
                print(f"  - '{p}': {c}")
