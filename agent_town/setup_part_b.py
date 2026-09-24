import json

agents_path = 'data/agents.json'
agents = json.load(open(agents_path, 'r', encoding='utf-8'))

alex = next(a for a in agents if a['name'] == 'Alex')
vikram = next(a for a in agents if a['name'] == 'Vikram')

print("Before update:")
print(f"Alex -> Vikram affinity: {alex['relationships']['6']['affinity']}")
print(f"Vikram -> Alex affinity: {vikram['relationships']['3']['affinity']}")

# 1. Update affinity to 32
alex['relationships']['6']['affinity'] = 32
vikram['relationships']['3']['affinity'] = 32

# 2. Add shared friction context
friction_mem = {
    "day": 1018,
    "text": "Alex confronted Vikram about low transparency and friction in support ticket coverage.",
    "type": "event",
    "importance": 7
}
alex.setdefault('memory', []).append(friction_mem)
vikram.setdefault('memory', []).append(friction_mem)

with open(agents_path, 'w', encoding='utf-8') as f:
    json.dump(agents, f, indent=2)

print("\nAfter update:")
print(f"Alex -> Vikram affinity: {alex['relationships']['6']['affinity']}")
print(f"Vikram -> Alex affinity: {vikram['relationships']['3']['affinity']}")
print("Friction context added to shared memories.")
