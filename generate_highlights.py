import json
import os
import re

world_path = 'data/world_state.json'
agents_path = 'data/agents.json'
chronicle_dir = 'data/chronicle'

world = json.load(open(world_path, 'r', encoding='utf-8'))
agents = json.load(open(agents_path, 'r', encoding='utf-8'))
event_log = world.get('event_log', [])

# 1. Friendship threshold crossings
friends = [e for e in event_log if "becoming close friends" in e]

# 2. Tension moments
tensions = [e for e in event_log if "growing tense" in e or "morale penalty (-2)" in e]

# 3. Deadline misses
deadline_misses = [e for e in event_log if "failed" in e.lower() or "missed" in e.lower() or "deadline" in e.lower() and ("failed" in e.lower() or "penalty" in e.lower())]

# 4. Project completions & largest projects
project_events = []
for e in event_log:
    if "completed" in e.lower() and "earned $" in e:
        # e.g.: Day 1013: Marketing completed 'Bolt Corp Support Overhaul' — earned $2,060 in revenue
        m = re.search(r"earned \$([0-9,]+)", e)
        if m:
            val = int(m.group(1).replace(",", ""))
            project_events.append((val, e))

# Sort by value descending
project_events.sort(key=lambda x: x[0], reverse=True)
top_3_projects = project_events[:3]

# 5. Market shifts
market_shifts = [e for e in event_log if "market shifted" in e.lower()]

# 6. Distinct reflections from Part A
reflections = [
    {
        "agent": "Sam",
        "day": 840,
        "text": "As I look back on the past week, I've come to realize that I've been falling into a pattern of quiet self-sabotage, where I prioritize short-term relief over long-term growth, and my tendency to overreport my work is a symptom of a deeper struggle to acknowledge and address my own limitations and vulnerabilities. I'm starting to see that my fear of vulnerability and rejection is driving this behavior, and it's only by acknowledging and confronting this fear that I can begin to break free from it and develop healthier habits."
    },
    {
        "agent": "Priya",
        "day": 903,
        "text": "I'm starting to notice that every time I feel anxious or stressed - whether it's due to work pressure, looming deadlines, or simply my own self-doubt - a familiar pattern emerges: as soon as I start to flag in energy levels and lose focus on what needs to be done next for Titan Corp API Integration. What strikes me is how seemingly rational decisions like 'taking breaks' become quietly overreported versions of themselves when under pressure, revealing an intricate web that links self-care with the very habits meant to alleviate my stress - it's a sobering reminder I need some deeper introspection about what truly helps (and hinders) myself."
    },
    {
        "agent": "Alex",
        "day": 959,
        "text": "As I reflect on my recent behavior patterns, it's striking to me that whenever Sam and our catch-ups were particularly impactful in boosting my morale, there seems to be a ripple effect where subsequent stress days start popping up sooner than usual - suggesting that perhaps the emotional high is not enough to sustain itself without some form of proactive self-care intervention. This realization prompts me to ask myself if I'm relying too heavily on external validation and support systems rather than developing internal resilience mechanisms, which could help mitigate these post-catch-up slumps in a more lasting way."
    }
]

# Generate Markdown content
lines = []
lines.append("# Agent Town — Highlights Reel (Days 1 – 1031)")
lines.append("*A curated chronicling of pivotal social milestones, professional triumphs, high-stakes crises, and psychological insights across 1,000+ days in Agent Town.*\n")
lines.append("---\n")

lines.append("## 1. Social Milestones: Friendship Thresholds (Affinity ≥ 70)")
lines.append("Through hundreds of shared meetings, coffee breaks, and mutual support, deep bonds forged across departments:")
if friends:
    for f in friends:
        lines.append(f"- **{f.split(':')[0]}**: {':'.join(f.split(':')[1:]).strip()}")
else:
    lines.append("- *No friendship thresholds logged in world event log.*")
lines.append("")

lines.append("## 2. Workplace Friction: The Support Department Rivalry")
lines.append("While most relationships in Agent Town flourished into mutual trust, the Support department experienced a historic fracture:")
for t in tensions:
    lines.append(f"- **{t.split(':')[0]}**: {':'.join(t.split(':')[1:]).strip()}")
lines.append("")
lines.append("> **Context**: Long-standing friction over transparency in ticket handling culminated on Day 1029 when Alex and Vikram crossed below the 30-affinity tension threshold (dropping to 27). This triggered immediate active departmental drag on Day 1030, reducing both colleagues' morale whenever working together.\n")

lines.append("## 3. High-Value Project Triumphs (Top 3 by Value)")
lines.append("Agent Town's economy is fueled by intense departmental delivery sprints. The three largest revenue-generating contract completions in company history:")
for idx, (val, ev) in enumerate(top_3_projects, 1):
    lines.append(f"{idx}. **${val:,}** — {ev}")
lines.append("")

lines.append("## 4. Economic Cycles & Market Shifts")
lines.append("The company navigated through turbulent market transitions, testing its budget reserves:")
for m in market_shifts:
    lines.append(f"- {m}")
lines.append("")

if deadline_misses:
    lines.append("## 5. Critical Deadline Failures & Penalties")
    for d in deadline_misses:
        lines.append(f"- {d}")
    lines.append("")

lines.append("## 6. Psychological Portraits: Standout Agent Reflections")
lines.append("Every week, agents reflect deeply on their habits, vulnerabilities, and coping strategies. Here are three of the most candid self-assessments:\n")
for r in reflections:
    lines.append(f"### {r['agent']} (Day {r['day']})")
    lines.append(f"> \"{r['text']}\"\n")

lines.append("---\n")
lines.append(f"**Current World State Snapshot**:")
lines.append(f"- **Simulation Day**: {world.get('current_day', 1031)}")
lines.append(f"- **Company Budget**: ${world.get('company_budget', 0):,}")
lines.append(f"- **Company Reputation**: {world.get('reputation', 100)}/100")
lines.append(f"- **Market Mood**: {world.get('market_mood', 'stable')}")

os.makedirs('output', exist_ok=True)
out_path = 'output/highlights.md'
with open(out_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(lines))

print(f"Highlights reel successfully generated at: {out_path}")
