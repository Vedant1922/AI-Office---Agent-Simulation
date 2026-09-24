import re

with open("engine/scheduler.py", "r") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "create_memory" in line and "[\'" in line:
        # replace the outermost f"..." with f'...' and inside use "
        # Or simply, fix the specific ones
        pass

# Actually, I can just read content and do re.sub
with open("engine/scheduler.py", "r") as f:
    content = f.read()

# Replace `agent[\'name\']` with `agent["name"]` ? Wait, if the string is enclosed in `f"..."`, then `"` inside `{}` is valid in Python 3.12 but what version are we using?
# Let's just fix it without f-strings or by changing quotes.
# f"Day {day}: {agent['name']}..." is fine if we don't escape the single quote!
# Python allows f"Day {day}: {agent['name']}". It's just my regex replacement that put `\'`.

content = content.replace("agent[\\'name\\']", "agent['name']")
content = content.replace("friend[\\'name\\']", "friend['name']")
content = content.replace("llm_result[\\'thought\\']", "llm_result['thought']")

with open("engine/scheduler.py", "w") as f:
    f.write(content)
print("fixed")
