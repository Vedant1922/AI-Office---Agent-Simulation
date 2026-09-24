import json

with open("data/agents.json", "r") as f:
    agents = json.load(f)

lines = []
lines.append("# 15-Day Simulation Report (Days 883 - 897)")
lines.append("\nHere are the aggregated statistics and samples for all agents across the full 15-day simulation. This includes action breakdowns, LLM fallback frequencies, and samples of their internal reasoning.")

for agent in agents:
    name = agent["name"]
    soc = agent["personality"]["sociability"]
    
    # Filter memories from the last 15 days
    recent_mems = [m for m in agent.get("memory", []) if isinstance(m, dict) and m.get("day", 0) >= 883]
    
    counts = {"work": 0, "rest": 0, "social": 0}
    llm_success = 0
    fallback = 0
    samples = []
    
    for m in recent_mems:
        text = m.get("text", "")
        # Skip hard overrides and non-action memories
        if "stopped to eat" in text or "stress day" in text or "burned out" in text or "rested early" in text or "attended the team meeting" in text or "failed to meet" in text or "PROJECT DONE" in text:
            continue
        
        is_action = False
        if "worked" in text.lower():
            counts["work"] += 1
            is_action = True
        elif "rested" in text.lower() or "chose to rest" in text.lower():
            counts["rest"] += 1
            is_action = True
        elif "social" in text.lower() or "caught up with" in text.lower() or "chatted" in text.lower():
            counts["social"] += 1
            is_action = True
            
        if is_action:
            if "LLM Thought:" in text: 
                llm_success += 1
                if len(samples) < 3: samples.append(text)
            else: 
                fallback += 1
            
    lines.append(f"\n## {name} (Sociability: {soc})")
    lines.append(f"- **Actions**: Work: {counts['work']} | Rest: {counts['rest']} | Socialize: {counts['social']}")
    lines.append(f"- **LLM Status**: Successes: {llm_success} | Fallbacks: {fallback}")
    lines.append("- **Sample Reasoning**:")
    for s in samples[:2]:
        # Extract just the thought
        thought = s.split("[LLM Thought:")[-1].replace("]", "").strip() if "[LLM Thought:" in s else s
        lines.append(f"  - \"{thought}\"")

with open(r"C:\Users\HP\.gemini\antigravity-ide\brain\60983343-fee7-4c65-973f-30810bcb2c9d\15_day_report_artifact.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
