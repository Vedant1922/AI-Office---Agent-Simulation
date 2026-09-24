import json

agents = json.load(open('data/agents.json', encoding='utf-8'))
for a in agents:
    print(f"{a['id']}: {a['name']}, Dept: {a['department']}, Honesty: {a['personality']['honesty']}, Sociability: {a['personality']['sociability']}")
