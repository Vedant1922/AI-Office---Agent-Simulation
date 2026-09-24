import re

with open('engine/llm_client.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add import time at the top
if 'import time' not in content:
    content = content.replace("import json", "import json\nimport time")

# Add delay in decide_action
old_decide = """    try:
        prompt = _build_prompt(agent, world_state, department_state)
    finally:
        agent.pop("_rel_names", None)

    for attempt in range(2):"""
new_decide = """    try:
        prompt = _build_prompt(agent, world_state, department_state)
    finally:
        agent.pop("_rel_names", None)

    time.sleep(1.5)  # Add a small delay between agents' calls to prevent connection errors
    
    for attempt in range(2):"""
content = content.replace(old_decide, new_decide)

with open('engine/llm_client.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Added connection delay!")
