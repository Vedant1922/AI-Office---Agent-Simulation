import io, re, json

try:
    with io.open('all_agents_test.txt', 'r', encoding='utf-16le') as f:
        lines = f.readlines()
except Exception:
    with io.open('all_agents_test.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()

agents = ['Sam', 'Priya', 'Alex', 'Jordan', 'Riya']
stats = {a: {'llm_work': 0, 'llm_rest': 0, 'llm_social': 0, 'rule_work': 0, 'rule_rest': 0, 'rule_social': 0, 'reasons': []} for a in agents}

for line in lines:
    if 'Day' not in line: continue
    
    parts = line.split('|')
    if len(parts) > 5:
        day_str = parts[0].strip()
        agent_summaries = parts[5:]
        for summary in agent_summaries:
            for agent in agents:
                if summary.strip().startswith(agent):
                    is_llm = '[LLM]' in summary or 'RESTED[LLM]' in summary or 'SOCIAL[LLM]' in summary or 'WORKED[LLM]' in summary
                    
                    if 'WORKED' in summary:
                        if is_llm: stats[agent]['llm_work'] += 1
                        else: stats[agent]['rule_work'] += 1
                    elif 'RESTED' in summary:
                        if is_llm: stats[agent]['llm_rest'] += 1
                        else: stats[agent]['rule_rest'] += 1
                    elif 'SOCIAL' in summary:
                        if is_llm: stats[agent]['llm_social'] += 1
                        else: stats[agent]['rule_social'] += 1
                    break

# Now read memory for reasoning strings (Work, Rest, Social) and traits
with open('data/agents.json', 'r') as f:
    agent_data = json.load(f)

for agent in agent_data:
    name = agent['name']
    sociability = agent['personality']['sociability']
    stats[name]['sociability'] = sociability
    
    # We want reasoning strings from memory that were added during this run (roughly last 25 days)
    # Since the run takes ~25 days, we can just grab the most recent LLM tags from their memory
    memories = agent.get('memory', [])
    llm_mems = [m for m in memories if '[LLM:' in m]
    # We just want a mix, so we grab up to 4 recent ones
    for m in llm_mems[-15:]:
        # Extract action and reason
        # Format: "Day 540: Sam worked [LLM: reason here]"
        # or "Day 540: Sam chose to rest [LLM: reason here]"
        # or "Day 540: Sam caught up with Priya [LLM: reason here]"
        match = re.search(r'(worked|rest|caught up with|chatted with).*?\[LLM:\s*(.*?)\]', m, re.IGNORECASE)
        if match:
            action = match.group(1).lower()
            if 'work' in action: act_type = 'Work'
            elif 'rest' in action: act_type = 'Rest'
            else: act_type = 'Social'
            
            reason = match.group(2).strip()
            # Append if reason is unique to keep variety
            if not any(r['reason'] == reason for r in stats[name]['reasons']):
                stats[name]['reasons'].append({'type': act_type, 'reason': reason})

print('--- FINAL AGENT STATS ---')
for name in agents:
    s = stats[name]
    print(f"[{name}] (Sociability: {s['sociability']})")
    print(f"  Work    - LLM: {s['llm_work']}, Fallback: {s['rule_work']}")
    print(f"  Rest    - LLM: {s['llm_rest']}, Fallback: {s['rule_rest']}")
    print(f"  Social  - LLM: {s['llm_social']}, Fallback: {s['rule_social']}")
    print("  Sample Reasons:")
    
    # Try to grab one of each type if possible
    types_seen = set()
    samples = []
    for r in reversed(s['reasons']):
        if r['type'] not in types_seen:
            samples.append(r)
            types_seen.add(r['type'])
    # If we need more, just add others
    if len(samples) < 3:
        for r in reversed(s['reasons']):
            if r not in samples and len(samples) < 3:
                samples.append(r)
    
    for r in samples:
        print(f"    - {r['type']}: \"{r['reason']}\"")
    print('-' * 40)
