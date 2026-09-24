import json

agents = json.load(open('data/agents.json', encoding='utf-8'))
vikram = next(a for a in agents if a['name'] == 'Vikram')
for rid, rdata in vikram['relationships'].items():
    other = next(a['name'] for a in agents if a['id'] == int(rid))
    print(f"Vikram -> {other} (id {rid}): affinity={rdata.get('affinity')}, interactions={rdata.get('interactions')}")
