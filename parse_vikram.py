import io, re, json

try:
    with io.open('vikram_test_output.txt', 'r', encoding='utf-16le') as f:
        lines = f.readlines()
except Exception:
    with io.open('vikram_test_output.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()

agents = ['Sam', 'Priya', 'Alex', 'Jordan', 'Riya', 'Vikram']
stats = {a: {'energy_deltas': 0, 'calm_work': 0, 'calm_rest': 0, 'calm_social': 0} for a in agents}

support_calm_days = set()

for line in lines:
    if 'Day' not in line: continue
    
    parts = line.split('|')
    if len(parts) > 5:
        day_str = parts[0].strip()
        
        # Check if Support is calm (no project, or progress is very low indicating start of new one)
        # Find the Projects list
        proj_part = [p for p in parts if 'Projects:' in p]
        is_support_calm = True
        if proj_part:
            projects = proj_part[0]
            if 'Support:' in projects:
                # e.g., "Support:Acme Corp(10%)"
                m = re.search(r'Support:.*?\((\d+)%\)', projects)
                if m and int(m.group(1)) > 20: # If progress > 20%, it's not calm anymore
                    is_support_calm = False
        
        if is_support_calm:
            support_calm_days.add(day_str)

        agent_summaries = parts[5:]
        for summary in agent_summaries:
            for agent in agents:
                if summary.strip().startswith(agent):
                    # extract nrg delta
                    nrg_match = re.search(r'nrg=\s*(-?\d+)', summary)
                    if nrg_match:
                        stats[agent]['energy_deltas'] += int(nrg_match.group(1))
                    
                    if agent == 'Vikram' and is_support_calm:
                        if 'WORKED' in summary:
                            stats['Vikram']['calm_work'] += 1
                        elif 'RESTED' in summary:
                            stats['Vikram']['calm_rest'] += 1
                        elif 'SOCIAL' in summary:
                            stats['Vikram']['calm_social'] += 1
                    break

with open('data/agents.json', 'r') as f:
    agent_data = json.load(f)

print('--- ENERGY TRENDS (Start -> End) ---')
for agent in agent_data:
    name = agent['name']
    end_energy = agent.get('energy', 100)
    # Calculate start energy = end_energy - sum(deltas)
    start_energy = end_energy - stats[name]['energy_deltas']
    # energy is technically capped at 100, so if start_energy > 100 it means they were at 100 and tried to rest more
    if start_energy > 100: start_energy = 100
    print(f"[{name}] Start: {start_energy} -> End: {end_energy} (Net change: {end_energy - start_energy})")

print('\n--- VIKRAM TENSION / RIVALRY (< 30 Affinity) ---')
vikram_data = next(a for a in agent_data if a['name'] == 'Vikram')
name_map = {a['id']: a['name'] for a in agent_data}
found_tension = False
for rid, rel in vikram_data.get('relationships', {}).items():
    if rel['affinity'] < 30:
        found_tension = True
        print(f"Tension with {name_map.get(rid, rid)}: affinity = {rel['affinity']}")
if not found_tension:
    print("No relationships dropped below 30 affinity.")

print('\n--- VIKRAM CALM-DAY BEHAVIOR (Support dept under 20% progress) ---')
print(f"Work: {stats['Vikram']['calm_work']}, Rest: {stats['Vikram']['calm_rest']}, Social: {stats['Vikram']['calm_social']}")

print('\n--- VIKRAM REASONING SAMPLES ---')
mems = [m for m in vikram_data.get('memory', []) if '[LLM:' in m]
keywords = ['honest', 'ambiti', 'risk', 'toleran', 'diligen', 'social', 'low', 'high']
for m in mems:
    # Just print all of them so we can pick out the good ones in the report
    print(m)
