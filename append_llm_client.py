import json

with open("engine/llm_client.py", "a", encoding="utf-8") as f:
    f.write('''
# ─────────────────────────────────────────────────────────────────────────────
# Part C & D: Weekly Reflections & Interpreted Relationships
# ─────────────────────────────────────────────────────────────────────────────

def _call_json_ollama(prompt: str) -> dict | None:
    try:
        import ollama
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )
        return json.loads(response["message"]["content"])
    except Exception:
        return None

def generate_weekly_reflection(agent: dict, recent_memories: list) -> str | None:
    """
    Ask the agent to write a short first-person reflection noticing a pattern.
    """
    mems_str = "\\n".join([f"- {m.get('text', '')}" for m in recent_memories]) if recent_memories else "No significant memories this week."
    prompt = (
        f"You are {agent['name']}, looking back on the past week.\\n\\n"
        f"Recent memories:\\n{mems_str}\\n\\n"
        f"Write a short first-person reflection (1-2 sentences) noticing a pattern about yourself. "
        f"Do not summarize the events. Instead, share an actual realization or insight about how you've been behaving or feeling."
    )
    return _call_meeting_ollama(prompt)

def decide_relationship_update(agent_a: dict, agent_b: dict, shared_memories: list) -> dict | None:
    """
    Given shared memories and personality, return interpreted relationship note and affinity delta.
    """
    mems_str = "\\n".join([f"- {m.get('text', '')}" for m in shared_memories]) if shared_memories else "No specific shared memories."
    prompt = (
        f"You are evaluating the relationship between {agent_a['name']} and {agent_b['name']}.\\n\\n"
        f"{agent_a['name']} Personality: {agent_a['personality']}\\n"
        f"{agent_b['name']} Personality: {agent_b['personality']}\\n\\n"
        f"Shared context:\\n{mems_str}\\n\\n"
        f"Respond ONLY with valid JSON exactly matching this schema:\\n"
        f"{{\\n"
        f'  "note": "2-3 sentences on how they currently feel about each other, in third person",\\n'
        f'  "affinity_delta": integer from -5 to +5 based on recent interactions (use 0 if nothing significant happened)\\n'
        f"}}"
    )
    
    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call_json_ollama, prompt)
            try:
                res = future.result(timeout=TIMEOUT)
                if res and "note" in res and "affinity_delta" in res:
                    return res
                return None
            except concurrent.futures.TimeoutError:
                return None
    except Exception:
        return None
''')
print("Appended successfully")
