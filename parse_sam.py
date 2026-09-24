import io
import re

try:
    with io.open('sam_test_output.txt', 'r', encoding='utf-16le') as f:
        lines = f.readlines()
except:
    with io.open('sam_test_output.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()

agents = ['Sam', 'Priya', 'Alex', 'Jordan', 'Riya']
stats = {a: {'llm_work': 0, 'llm_rest': 0, 'llm_social': 0, 'rule_work': 0, 'rule_rest': 0, 'rule_social': 0, 'reasons': []} for a in agents}

sam_log = []

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
                    
                    if is_llm:
                        m = re.search(r"reason='([^']+)'", summary)
                        if m:
                            stats[agent]['reasons'].append((day_str, m.group(1), summary.strip().split(':')[0]))
                    
                    if agent == 'Sam':
                        sam_log.append(f'{day_str}: {summary.strip()}')
                    break

print('--- STATS ---')
for agent in agents:
    s = stats[agent]
    print(f"{agent}: LLM(W={s['llm_work']}, R={s['llm_rest']}, S={s['llm_social']}) | Rule(W={s['rule_work']}, R={s['rule_rest']}, S={s['rule_social']})")

print('\n--- SAM REASONS ---')
for day, reason, prefix in stats['Sam']['reasons']:
    print(f'{day} | {prefix} | {reason}')

print('\n--- SAM FULL LOG (first 10 days) ---')
for log in sam_log[:10]:
    print(log)
