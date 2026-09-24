import re

with open('engine/llm_client.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. TIMEOUT
content = content.replace("TIMEOUT = 10", "TIMEOUT = 20")

# 2. Trim memory & relationships & reflections
old_rel_str = """        note = rv.get("note", "")
        note_str = f", Note: {note}" if note else ""
        top_rels.append(f"{rname} (affinity {rv['affinity']}/100{note_str})")"""
new_rel_str = """        note = rv.get("note", "")
        # trim note to roughly 1-2 sentences
        if note:
            note = ". ".join(note.split(". ")[:2])
            if not note.endswith("."): note += "."
        note_str = f", Note: {note}" if note else ""
        top_rels.append(f"{rname} (affinity {rv['affinity']}/100{note_str})")"""
content = content.replace(old_rel_str, new_rel_str)

old_mem = "recent_mems = retrieve_relevant_memories(agent, context_keywords, curr_day, top_n=5)"
new_mem = "recent_mems = retrieve_relevant_memories(agent, context_keywords, curr_day, top_n=3)"
content = content.replace(old_mem, new_mem)

old_ref = "latest_ref = f\"\\nLatest reflection: \\\"{reflections[-1]['text']}\\\"\" if reflections else \"\""
new_ref = "latest_ref = f\"\\nLatest reflection: \\\"{reflections[-1]['text'][:200]}...\\\"\" if reflections else \"\""
content = content.replace(old_ref, new_ref)

# 3. Simplify JSON shape & add Example
old_schema = """        f"Respond with ONLY valid JSON — no extra text, no markdown. Use this exact schema:\\n"
        f'{{\\n'
        f'  "thought": "2-3 sentences, first person, {angle}, referencing your real situation but not forced into reciting stats",\\n'
        f'  "action": "work" | "rest" | "socialize",\\n'
        f'  "who": "name of coworker if action is socialize, otherwise null"\\n'
        f'}}'"""
new_schema = """        f"Respond with ONLY valid JSON — no extra text, no markdown. Use this exact schema:\\n"
        f'{{\\n'
        f'  "thought": "2-3 sentences, first person, {angle}",\\n'
        f'  "action": "work" | "rest" | "socialize",\\n'
        f'  "who": "name of coworker if action is socialize, otherwise null"\\n'
        f'}}\\n\\n'
        f'EXAMPLE VALID OUTPUT:\\n'
        f'{{\\n'
        f'  "thought": "I feel quite exhausted today and my energy levels are low. Taking a break will help me recover so I can focus on my project tomorrow.",\\n'
        f'  "action": "rest",\\n'
        f'  "who": null\\n'
        f'}}'"""
content = content.replace(old_schema, new_schema)

# 4. Retry loop in decide_action
old_decide = """    try:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(_call_ollama, prompt, agent["name"])
        try:
            res = future.result(timeout=TIMEOUT)
            executor.shutdown(wait=False)
            return res
        except concurrent.futures.TimeoutError:
            log_llm_failure(agent["name"], "timeout", f"Thread timed out after {TIMEOUT}s")
            executor.shutdown(wait=False)
            return None
    except Exception as e:
        log_llm_failure(agent["name"], "executor_error", str(e))
        return None"""

new_decide = """    for attempt in range(2):
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
            
    return None"""
content = content.replace(old_decide, new_decide)

with open('engine/llm_client.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated llm_client.py successfully!")
