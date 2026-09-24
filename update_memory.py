import re
import os

with open("engine/scheduler.py", "r") as f:
    content = f.read()

# Make sure we add the import at the top
if "from engine.memory import create_memory" not in content:
    content = content.replace("import random", "import random\nfrom engine.memory import create_memory")

# The replacements with their importances
replacements = [
    # 103
    (r'agent\["memory"\]\.append\(f"Day {day}: {agent\[\'name\'\]} caught up with {friend\[\'name\'\]}"\)',
     r'agent["memory"].append(create_memory(day, f"Day {day}: {agent[\'name\']} caught up with {friend[\'name\']}", importance=2))'),
    # 108
    (r'agent\["memory"\]\.append\(f"Day {day}: {agent\[\'name\'\]} made a point to chat with coworkers\."\)',
     r'agent["memory"].append(create_memory(day, f"Day {day}: {agent[\'name\']} made a point to chat with coworkers.", importance=2))'),
    # 154
    (r'agent\["memory"\]\.append\(f"Day {day}: {name} stopped to eat"\)',
     r'agent["memory"].append(create_memory(day, f"Day {day}: {name} stopped to eat", importance=4))'),
    # 161
    (r'agent\["memory"\]\.append\(f"Day {day}: {name} took a stress day"\)',
     r'agent["memory"].append(create_memory(day, f"Day {day}: {name} took a stress day", importance=4))'),
    # 169
    (r'agent\["memory"\]\.append\(f"Day {day}: {name} burned out and rested \(morale too low\)"\)',
     r'agent["memory"].append(create_memory(day, f"Day {day}: {name} burned out and rested (morale too low)", importance=4))'),
    # 196
    (r'agent\["memory"\]\.append\(f"Day {day}: {name} chose to rest \[LLM Thought: \{thought\}\]"\)',
     r'agent["memory"].append(create_memory(day, f"Day {day}: {name} chose to rest [LLM Thought: {thought}]", importance=2))'),
    # 226
    (r'agent\["memory"\]\.append\(f"Day {day}: {name} caught up with \{friend\[\'name\'\]\} \[LLM Thought: \{thought\}\]"\)',
     r'agent["memory"].append(create_memory(day, f"Day {day}: {name} caught up with {friend[\'name\']} [LLM Thought: {thought}]", importance=2))'),
    # 231
    (r'agent\["memory"\]\.append\(f"Day {day}: {name} chatted with coworkers \[LLM Thought: \{thought\}\]"\)',
     r'agent["memory"].append(create_memory(day, f"Day {day}: {name} chatted with coworkers [LLM Thought: {thought}]", importance=2))'),
    # 245
    (r'agent\["memory"\]\.append\(\s*f"Day \{day\}: \{name\} rested early \(low diligence=\{diligence\}\)"\s*if diligence < 50 else\s*f"Day \{day\}: \{name\} rested \(threshold=\{rest_threshold:\.0f\}\)"\s*\)',
     r'agent["memory"].append(create_memory(day, f"Day {day}: {name} rested early (low diligence={diligence})" if diligence < 50 else f"Day {day}: {name} rested (threshold={rest_threshold:.0f})", importance=2))'),
    # 267
    (r'agent\["memory"\]\.append\(f"Day {day}: {name} worked \[LLM Thought: \{llm_result\[\'thought\'\]\}\]"\)',
     r'agent["memory"].append(create_memory(day, f"Day {day}: {name} worked [LLM Thought: {llm_result[\'thought\']}]", importance=3))'),
    # 269
    (r'agent\["memory"\]\.append\(f"Day {day}: {name} worked \(diligence-driven, earned \{money_earned\}\)"\)',
     r'agent["memory"].append(create_memory(day, f"Day {day}: {name} worked (diligence-driven, earned {money_earned})", importance=3))'),
    # 289
    (r'agent\["memory"\]\.append\(f"Day {day}: {name} contributed to \{proj_note\}"\)',
     r'agent["memory"].append(create_memory(day, f"Day {day}: {name} contributed to {proj_note}", importance=3))'),
    # 295
    (r'agent\["memory"\]\.append\(f"Day {day}: {name} quietly overreported their work\."\)',
     r'agent["memory"].append(create_memory(day, f"Day {day}: {name} quietly overreported their work.", importance=3))'),
    # 374
    (r'agent\["memory"\]\.append\(f"Day {day}: {agent\[\'name\'\]} attended the team meeting"\)',
     r'agent["memory"].append(create_memory(day, f"Day {day}: {agent[\'name\']} attended the team meeting", importance=2))'),
]

for pat, rep in replacements:
    content = re.sub(pat, rep, content)

with open("engine/scheduler.py", "w") as f:
    f.write(content)

print("done")
