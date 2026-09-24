import json

with open('data/agents.json', 'r', encoding='utf-8') as f:
    agents = json.load(f)

print('=== SIMULATION VALIDATION REPORT (Days 958 - 1018) ===')
cluster_words = ['coping mechanism', 'root issue', 'root cause', 'cycle of overreporting', 'cycle of']
found_phrases = {w: [] for w in cluster_words}
llm_success_total = 0
fallback_total = 0

for a in agents:
    name = a['name']
    mems = [m for m in a.get('memory', []) if isinstance(m, dict) and m.get('day', 0) >= 958]
    llm_s, fb = 0, 0
    actions = {'work': 0, 'rest': 0, 'social': 0}
    for m in mems:
        t = m.get('text', '')
        day = m.get('day', 0)
        for w in cluster_words:
            if w in t.lower():
                found_phrases[w].append((name, day, t))
        if any(k in t for k in ['stopped to eat', 'stress day', 'burned out', 'attended the team meeting', 'PROJECT DONE']):
            continue
        
        is_act = False
        if 'worked' in t.lower():
            actions['work'] += 1
            is_act = True
        elif 'rested' in t.lower() or 'chose to rest' in t.lower():
            actions['rest'] += 1
            is_act = True
        elif 'social' in t.lower() or 'caught up with' in t.lower() or 'chatted' in t.lower():
            actions['social'] += 1
            is_act = True
            
        if is_act:
            if '[LLM Thought:' in t:
                llm_s += 1
            else:
                fb += 1

    print(f"{name:8s} | Work: {actions['work']:2d} | Rest: {actions['rest']:2d} | Social: {actions['social']:2d} | LLM OK: {llm_s:2d} | Fallback: {fb:2d}")
    llm_success_total += llm_s
    fallback_total += fb

total_calls = llm_success_total + fallback_total
rate = (llm_success_total / total_calls * 100) if total_calls > 0 else 0
print('-' * 60)
print(f"Total Decision Calls: {total_calls}")
print(f"LLM Successes:       {llm_success_total} ({rate:.1f}%)")
print(f"Deterministic FB:    {fallback_total} ({100-rate:.1f}%)")

print('\n=== PHRASE CLUSTERING CHECK ===')
total_cluster_hits = sum(len(v) for v in found_phrases.values())
print(f"Total cluster occurrences: {total_cluster_hits}")
for w, hits in found_phrases.items():
    print(f" - '{w}': {len(hits)}")
    for name, day, text in hits:
        print(f"    * Day {day} [{name}]: {text[:140]}...")

# Parse tolerance rules from llm_failures.log
print('\n=== TOLERANCE PARSER METRICS ===')
with open('output/llm_failures.log', 'r', encoding='utf-8') as f:
    log_content = f.read()

rules = {
    'tolerance_key_whitespace': log_content.count('tolerance_key_whitespace'),
    'tolerance_fuzzy_action': log_content.count('tolerance_fuzzy_action'),
    'blank_template': log_content.count('blank_template'),
    'missing_or_invalid_action': log_content.count('missing_or_invalid_action'),
    'timeout': log_content.count('timeout'),
    'connection_error': log_content.count('connection_error')
}
for r, count in rules.items():
    print(f" - {r}: {count}")
