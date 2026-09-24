import os
import re

with open("engine/llm_client.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add log_llm_failure function at the top of _call_ollama section
log_func = """
def log_llm_failure(agent_name: str, reason: str, details: str, raw: str = ""):
    import os
    os.makedirs("output", exist_ok=True)
    with open("output/llm_failures.log", "a", encoding="utf-8") as f:
        f.write(f"[{agent_name}] {reason}: {details}\\n")
        if raw:
            f.write(f"Raw Output:\\n{raw}\\n")
        f.write("-" * 40 + "\\n")

"""

# Replace _call_ollama
old_call_ollama = """def _call_ollama(prompt: str) -> dict | None:
    \"\"\"Blocking Ollama call — run inside a thread so caller can time it out.\"\"\"
    try:
        import ollama
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )
        raw = response["message"]["content"]
        data = json.loads(raw)
        action = data.get("action", "").lower().strip()
        if action not in VALID_ACTIONS:
            return None
        data["action"] = action   # normalise case
        
        # Trim fields to be safe
        thought = str(data.get("thought", "")).strip()
        data["thought"] = thought[:500]   # Cap to avoid massive paragraphs
        
        who = data.get("who")
        data["who"] = str(who).strip()[:50] if who else None
        
        return data
    except Exception:
        return None"""

new_call_ollama = """def _call_ollama(prompt: str, agent_name: str) -> dict | None:
    \"\"\"Blocking Ollama call — run inside a thread so caller can time it out.\"\"\"
    try:
        import ollama
        response = ollama.chat(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            format="json",
        )
    except Exception as e:
        log_llm_failure(agent_name, "connection_error", str(e))
        return None
        
    raw = response.get("message", {}).get("content", "")
    try:
        import json
        data = json.loads(raw)
    except Exception as e:
        log_llm_failure(agent_name, "invalid_json", str(e), raw)
        return None
        
    action = data.get("action", "")
    if not isinstance(action, str):
        log_llm_failure(agent_name, "invalid_action_type", f"Action was {type(action)}", raw)
        return None
        
    action = action.lower().strip()
    if action not in VALID_ACTIONS:
        log_llm_failure(agent_name, "missing_or_invalid_action", f"Action value: '{action}'", raw)
        return None
        
    data["action"] = action
    thought = str(data.get("thought", "")).strip()
    data["thought"] = thought[:500]
    who = data.get("who")
    data["who"] = str(who).strip()[:50] if who else None
    
    return data"""

content = content.replace(old_call_ollama, log_func + new_call_ollama)

# Replace decide_action thread block
old_thread_block = """    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call_ollama, prompt)
            try:
                return future.result(timeout=TIMEOUT)
            except concurrent.futures.TimeoutError:
                return None
    except Exception:
        return None"""

new_thread_block = """    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call_ollama, prompt, agent["name"])
            try:
                return future.result(timeout=TIMEOUT)
            except concurrent.futures.TimeoutError:
                log_llm_failure(agent["name"], "timeout", f"Thread timed out after {TIMEOUT}s")
                return None
    except Exception as e:
        log_llm_failure(agent["name"], "executor_error", str(e))
        return None"""

content = content.replace(old_thread_block, new_thread_block)

with open("engine/llm_client.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated engine/llm_client.py")
