"""
engine/llm_client.py
--------------------
Thin wrapper around Ollama for agent decision-making.

Public API
----------
decide_action(agent, world_state, department_state) -> dict | None
    Returns {"action": "work"|"rest"|"socialize", "reason": "<12 words>"}
    or None if the call fails, times out, or produces invalid JSON/action.
"""

import json
import time
import concurrent.futures

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────
MODEL   = "llama3.2:3b"
TIMEOUT = 20          # seconds before we give up and fall back to rule logic
VALID_ACTIONS = {"work", "rest", "socialize"}


# ─────────────────────────────────────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_prompt(agent: dict, world_state: dict, department_state: dict) -> str:
    """
    Construct a compact, information-dense prompt from the agent's current state.
    Keeps it short so the 3B model stays on-task.
    """
    p    = agent["personality"]
    name = agent["name"]
    dept = agent.get("department", "Unknown")

    from engine.memory import retrieve_relevant_memories

    context_keywords = [dept]

    # Top-2 relationships by affinity
    rels = agent.get("relationships", {})
    rel_names = agent.get("_rel_names", {})   # {id: name}, injected by caller
    sorted_rels = sorted(rels.items(), key=lambda x: -x[1]["affinity"])
    top_rels = []
    for rid, rv in sorted_rels[:2]:
        rname = rel_names.get(rid, f"coworker-{rid}")
        context_keywords.append(rname)
        note = rv.get("note", "")
        # trim note to roughly 1-2 sentences
        if note:
            note = ". ".join(note.split(". ")[:2])
            if not note.endswith("."): note += "."
        note_str = f", Note: {note}" if note else ""
        top_rels.append(f"{rname} (affinity {rv['affinity']}/100{note_str})")
    rel_str = "Closest coworkers: " + (", ".join(top_rels) if top_rels else "no close relationships yet")

    # Department / project context
    active = department_state.get("active_project")
    if active:
        context_keywords.append(active['name'])
        days_left = active.get("deadline_day", 0) - world_state.get("current_day", 0)
        proj_str  = (
            f"Your department ({dept}) is working on: {active['name']} at {active['progress']:.0f}% progress "
            f"(deadline in {days_left} days, value ${active['value']:,})"
        )
    else:
        proj_str = f"Your department ({dept}) has no active project right now"

    budget = world_state.get("company_budget", 0)
    rep    = world_state.get("reputation", 50)
    mood   = world_state.get("market_mood", "stable")

    # Retrieve memory
    curr_day = world_state.get("current_day", 0)
    recent_mems = retrieve_relevant_memories(agent, context_keywords, curr_day, top_n=3)
    mem_str = "\n".join(f"- {m['text']}" for m in recent_mems) if recent_mems else "No relevant memories."

    # Latest reflection
    reflections = [m for m in agent.get("memory", []) if m.get("type") == "reflection"]
    latest_ref = f"\nLatest reflection: \"{reflections[-1]['text'][:200]}...\"" if reflections else ""

    import random
    angles = [
        "what's on your mind today",
        "how do you feel about your closest coworker right now",
        "what's something you're worried or excited about beyond just work",
        "reflect on yesterday"
    ]
    angle = random.choice(angles)
    pronoun = agent.get("pronoun", "they/them")

    prompt = (
        f"You are {name} ({pronoun}), an employee at a small company.\n\n"
        f"Personality (0-100): diligence={p['diligence']}, ambition={p['ambition']}, "
        f"honesty={p['honesty']}, sociability={p['sociability']}, "
        f"risk_tolerance={p['risk_tolerance']}\n\n"
        f"Current state: energy={agent['energy']}, morale={agent['morale']}, "
        f"hunger={agent['hunger']}, social={agent['social']}, stress={agent['stress']}{latest_ref}\n\n"
        f"{rel_str}\n\n"
        f"{proj_str}\n\n"
        f"Company: budget=${budget:,}, reputation={rep}/100, market={mood}\n\n"
        f"Recent relevant memories:\n{mem_str}\n\n"
        f"Based on your personality and current state, choose your action for today.\n"
        f"Respond with ONLY valid JSON — no extra text, no markdown. Use this exact schema:\n"
        f'{{\n'
        f'  "thought": "2-3 sentences, first person, {angle}",\n'
        f'  "action": "work" | "rest" | "socialize",\n'
        f'  "who": "name of coworker if action is socialize, otherwise null"\n'
        f'}}\n\n'
        f'EXAMPLE VALID OUTPUT:\n'
        f'{{\n'
        f'  "thought": "I feel quite exhausted today and my energy levels are low. Taking a break will help me recover so I can focus on my project tomorrow.",\n'
        f'  "action": "rest",\n'
        f'  "who": null\n'
        f'}}'
    )
    return prompt


# ─────────────────────────────────────────────────────────────────────────────
# Ollama call (runs in a thread so we can enforce the timeout)
# ─────────────────────────────────────────────────────────────────────────────


def log_llm_failure(agent_name: str, reason: str, details: str, raw: str = ""):
    import os
    os.makedirs("output", exist_ok=True)
    with open("output/llm_failures.log", "a", encoding="utf-8") as f:
        f.write(f"[{agent_name}] {reason}: {details}\n")
        if raw:
            f.write(f"Raw Output:\n{raw}\n")
        f.write("-" * 40 + "\n")

# Action fuzzy-match map: model outputs that should be normalised to a valid action
_ACTION_FUZZY_MAP = {
    "self": "rest",
    "self-care": "rest",
    "selfcare": "rest",
    "take a break": "rest",
    "break": "rest",
    "sleep": "rest",
    "relax": "rest",
    "working": "work",
    "works": "work",
    "socialise": "socialize",
    "chat": "socialize",
    "talk": "socialize",
}


def _parse_action_response(raw: str, agent_name: str) -> dict | None:
    """
    Tolerant parser for the decide_action JSON response.
    Handles:
      - Leading/trailing whitespace in keys  (" action" -> "action")
      - Near-valid action values via fuzzy map ("self" -> "rest")
      - Blank template responses ({"thought":"","action":"","who":""}) -> failure
    Logs which tolerance rule fired, if any.
    Returns the normalised dict on success, None on failure.
    """
    # ── 1. JSON parse ─────────────────────────────────────────────────────────
    try:
        data = json.loads(raw)
    except Exception as e:
        log_llm_failure(agent_name, "invalid_json", str(e), raw)
        return None

    # ── 2. Strip whitespace from ALL keys (catches " action", " thought", etc.) ─
    cleaned = {k.strip(): v for k, v in data.items()}
    if cleaned.keys() != data.keys():
        log_llm_failure(agent_name, "tolerance_key_whitespace",
                        f"Stripped whitespace from keys: {list(data.keys())} -> {list(cleaned.keys())}", raw)
    data = cleaned

    # ── 3. Blank-template guard ───────────────────────────────────────────────
    thought_val = str(data.get("thought", "")).strip()
    action_val  = str(data.get("action",  "")).strip()
    who_val     = str(data.get("who",     "")).strip()
    if not thought_val and not action_val:
        log_llm_failure(agent_name, "blank_template",
                        "All fields empty — model returned unfilled template", raw)
        return None

    # ── 4. Action type guard ──────────────────────────────────────────────────
    action = action_val.lower()
    if not isinstance(data.get("action", ""), str):
        log_llm_failure(agent_name, "invalid_action_type",
                        f"Action was {type(data.get('action'))}", raw)
        return None

    # ── 5. Exact match ────────────────────────────────────────────────────────
    if action in VALID_ACTIONS:
        pass  # clean output, no tolerance needed

    # ── 6. Fuzzy match ────────────────────────────────────────────────────────
    elif action in _ACTION_FUZZY_MAP:
        mapped = _ACTION_FUZZY_MAP[action]
        log_llm_failure(agent_name, "tolerance_fuzzy_action",
                        f"Mapped '{action}' -> '{mapped}'", raw)
        action = mapped

    # ── 7. Unrecognised action → genuine failure ──────────────────────────────
    else:
        log_llm_failure(agent_name, "missing_or_invalid_action",
                        f"Action value: '{action}' — not recognised, not fuzzy-matched", raw)
        return None

    # ── 8. Build clean return dict ────────────────────────────────────────────
    data["action"]  = action
    data["thought"] = thought_val[:500]
    data["who"]     = who_val[:50] if who_val and who_val.lower() not in ("null", "none", "") else None
    return data


def _call_ollama(prompt: str, agent_name: str) -> dict | None:
    """Blocking Ollama call — run inside a thread so caller can time it out."""
    try:
        import ollama
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
            options={"temperature": 0.85, "repeat_penalty": 1.3}
        )
    except Exception as e:
        log_llm_failure(agent_name, "connection_error", str(e))
        return None

    raw = response.get("message", {}).get("content", "")
    return _parse_action_response(raw, agent_name)


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def decide_action(agent: dict,
                  world_state: dict,
                  department_state: dict,
                  name_map: dict = None) -> dict | None:
    """
    Ask the LLM what the agent should do today.

    Parameters
    ----------
    agent            : the full agent dict
    world_state      : the full world_state dict
    department_state : the agent's department dict from world_state["departments"]
    name_map         : {agent_id: agent_name} for relationship labels (optional but
                       strongly recommended for readable prompts)

    Returns
    -------
    {"action": "work"|"rest"|"socialize", "reason": str}  on success
    None  on any failure (timeout, bad JSON, wrong action value, Ollama down, etc.)
    """
    # Inject name_map into agent temporarily (avoids changing the agent schema)
    agent["_rel_names"] = name_map or {}
    try:
        prompt = _build_prompt(agent, world_state, department_state)
    finally:
        agent.pop("_rel_names", None)

    time.sleep(1.5)  # Add a small delay between agents' calls to prevent connection errors
    
    for attempt in range(2):
        try:
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            future = executor.submit(_call_ollama, prompt, agent["name"])
            try:
                res = future.result(timeout=TIMEOUT)
                executor.shutdown(wait=False)
                if res is not None:
                    return res
                # if res is None, we failed due to invalid json/action, so we loop to retry
            except concurrent.futures.TimeoutError:
                log_llm_failure(agent["name"], "timeout", f"Thread timed out after {TIMEOUT}s (attempt {attempt+1})")
                executor.shutdown(wait=False)
                # loop to retry
        except Exception as e:
            log_llm_failure(agent["name"], "executor_error", str(e))
            
    return None

# ─────────────────────────────────────────────────────────────────────────────
# Meeting Narrative
# ─────────────────────────────────────────────────────────────────────────────

def _call_meeting_ollama(prompt: str) -> str | None:
    try:
        import ollama
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            # No JSON format forced here because we want a 2-3 sentence string
            options={"temperature": 0.85, "repeat_penalty": 1.3}
        )
        return response["message"]["content"].strip()
    except Exception:
        return None

def decide_group_meeting_narrative(agents: list) -> str | None:
    """
    Generate a 4-6 sentence narrative of the whole team meeting.
    """
    attendees_info = []
    for a in agents:
        recent_thought = [m for m in a.get("memory", []) if "[LLM Thought:" in m]
        fact = recent_thought[-1] if recent_thought else "No recent thoughts."
        pronoun = a.get("pronoun", "they/them")
        attendees_info.append(f"- {a['name']} ({pronoun}): morale={a['morale']}, stress={a['stress']}. Fact: {fact}")
        
    attendees_str = "\n".join(attendees_info)
    
    prompt = (
        f"You are the narrator of a company simulator.\n\n"
        f"Attendees of the weekly team meeting:\n"
        f"{attendees_str}\n\n"
        f"Write a single 4-6 sentence narrated scene of the whole meeting, naturally weaving in 2-3 specific character beats rather than covering everyone equally.\n"
        f"Rules:\n"
        f"1. Do not use the same sentence structure for multiple people.\n"
        f"2. Vary who speaks first.\n"
        f"3. Only reference affinity/deadlines when it's the most interesting thing about that person right now, not by default.\n"
        f"4. Do not use markdown, just output the narrative text directly."
    )
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call_meeting_ollama, prompt)
            try:
                narrative = future.result(timeout=180) # Increased timeout for a bigger prompt
                return narrative[:1000] if narrative else None
            except concurrent.futures.TimeoutError:
                return None
    except Exception:
        return None

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
            options={"temperature": 0.85, "repeat_penalty": 1.3}
        )
        return json.loads(response["message"]["content"])
    except Exception:
        return None

def generate_weekly_reflection(agent: dict, recent_memories: list) -> str | None:
    """
    Ask the agent to write a short first-person reflection noticing a pattern.
    """
    mems_str = "\n".join([f"- {m.get('text', '')}" for m in recent_memories]) if recent_memories else "No significant memories this week."
    prompt = (
        f"You are {agent['name']}, looking back on the past week.\n\n"
        f"Recent memories:\n{mems_str}\n\n"
        f"Write a short first-person reflection (1-2 sentences) noticing a pattern about yourself. "
        f"Do not summarize the events. Instead, share an actual realization or insight about how you've been behaving or feeling."
    )
    return _call_meeting_ollama(prompt)

def decide_relationship_update(agent_a: dict, agent_b: dict, shared_memories: list) -> dict | None:
    """
    Given shared memories and personality, return interpreted relationship note and affinity delta.
    """
    mems_str = "\n".join([f"- {m.get('text', '')}" for m in shared_memories]) if shared_memories else "No specific shared memories."
    prompt = (
        f"You are evaluating the relationship between {agent_a['name']} and {agent_b['name']}.\n\n"
        f"{agent_a['name']} Personality: {agent_a['personality']}\n"
        f"{agent_b['name']} Personality: {agent_b['personality']}\n\n"
        f"Shared context:\n{mems_str}\n\n"
        f"Respond ONLY with valid JSON exactly matching this schema:\n"
        f"{{\n"
        f'  "note": "2-3 sentences on how they currently feel about each other, in third person",\n'
        f'  "affinity_delta": integer from -5 to +5 based on recent interactions (use 0 if nothing significant happened)\n'
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
