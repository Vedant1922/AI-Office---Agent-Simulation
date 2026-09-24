import re

with open('engine/scheduler.py', 'r') as f:
    content = f.read()

# 1. Update _agent_day signature
content = re.sub(
    r'def _agent_day\(agent: dict, world: dict, day: int, austerity: bool = False, all_agents: list = None\) -> str:',
    'def _agent_day(agent: dict, world: dict, day: int, austerity: bool = False, all_agents: list = None, day_data: dict = None) -> str:',
    content
)

# 2. Update llm_result handling in _agent_day
old_llm_block = r'''    if llm_result:
        chosen = llm_result\["action"\]
        reason = llm_result\["reason"\]

        if chosen == "rest":
            agent\["energy"\] = min\(100, agent\["energy"\] \+ 20\)
            agent\["morale"\] = min\(100, agent\["morale"\] \+ 8\)
            _apply_rest_needs\(agent\)
            agent\["memory"\].append\(f"Day \{day\}: \{name\} chose to rest \[LLM: \{reason\}\]"\)
            return _header\(f"RESTED\[LLM\]"\) \+ f" \(nrg=\{agent\['energy'\]:>3\}, \$=\{agent\['money'\]:>5,\}, reason='\{reason\}'\)"

        if chosen == "socialize":
            # Reuse the full sociability-seed path regardless of sociability trait
            rels      = agent.get\("relationships", \{\}\)
            all_ag    = agent.get\("_all_agents", \[\]\)
            agent_map = \{a\["id"\]: a for a in all_ag if a\["id"\] != agent\["id"\]\}
            if rels and agent_map:
                best_id = max\(rels, key=lambda rid: rels.get\(rid, \{\}\).get\("affinity", 0\)\)
                friend  = agent_map.get\(best_id\)
                if friend:
                    agent\["social"\]  = min\(100, agent\["social"\]  \+ 10\)
                    friend\["social"\] = min\(100, friend\["social"\] \+ 10\)
                    rels\[best_id\]\["affinity"\] = min\(100, rels\[best_id\]\["affinity"\] \+ 2\)
                    f_rels = friend.get\("relationships", \{\}\)
                    if agent\["id"\] in f_rels:
                        f_rels\[agent\["id"\]\]\["affinity"\] = min\(100, f_rels\[agent\["id"\]\]\["affinity"\] \+ 2\)
                    agent\["memory"\].append\(f"Day \{day\}: \{name\} caught up with \{friend\['name'\]\} \[LLM: \{reason\}\]"\)
                    return _header\(f"SOCIAL\[LLM\]"\) \+ f" \(soc=\{agent\['social'\]:>3\}, reason='\{reason\}'\)"
            # Fallback if no relationships
            agent\["social"\] = min\(100, agent\["social"\] \+ 10\)
            agent\["memory"\].append\(f"Day \{day\}: \{name\} chatted with coworkers \[LLM: \{reason\}\]"\)
            return _header\("SOCIAL\[LLM\]"\) \+ f" \(soc=\{agent\['social'\]:>3\}, reason='\{reason\}'\)"'''

new_llm_block = '''    if llm_result:
        chosen = llm_result.get("action", "work")
        thought = llm_result.get("thought", "")
        who = llm_result.get("who")
        
        if day_data is not None:
            day_data["thoughts"][name] = thought

        if chosen == "rest":
            agent["energy"] = min(100, agent["energy"] + 20)
            agent["morale"] = min(100, agent["morale"] + 8)
            _apply_rest_needs(agent)
            agent["memory"].append(f"Day {day}: {name} chose to rest [LLM Thought: {thought}]")
            return _header(f"RESTED[LLM]") + f" (nrg={agent['energy']:>3}, $={agent['money']:>5,})"

        if chosen == "socialize":
            rels      = agent.get("relationships", {})
            all_ag    = agent.get("_all_agents", [])
            agent_map = {a["id"]: a for a in all_ag if a["id"] != agent["id"]}
            
            friend = None
            best_id = None
            if rels and agent_map:
                # If LLM specified 'who', try to find them
                if who:
                    for aid, a_data in agent_map.items():
                        if a_data["name"].lower() == who.lower():
                            best_id = aid
                            friend = a_data
                            break
                # Fallback to closest if 'who' not found or not provided
                if not friend:
                    best_id = max(rels, key=lambda rid: rels.get(rid, {}).get("affinity", 0))
                    friend  = agent_map.get(best_id)
                    
                if friend and best_id:
                    agent["social"]  = min(100, agent["social"]  + 10)
                    friend["social"] = min(100, friend["social"] + 10)
                    rels[best_id]["affinity"] = min(100, rels[best_id]["affinity"] + 2)
                    f_rels = friend.get("relationships", {})
                    if agent["id"] in f_rels:
                        f_rels[agent["id"]]["affinity"] = min(100, f_rels[agent["id"]]["affinity"] + 2)
                    agent["memory"].append(f"Day {day}: {name} caught up with {friend['name']} [LLM Thought: {thought}]")
                    return _header(f"SOCIAL[LLM]") + f" (soc={agent['social']:>3})"
                    
            # Fallback if no relationships
            agent["social"] = min(100, agent["social"] + 10)
            agent["memory"].append(f"Day {day}: {name} chatted with coworkers [LLM Thought: {thought}]")
            return _header("SOCIAL[LLM]") + f" (soc={agent['social']:>3})"'''

content = re.sub(old_llm_block, new_llm_block, content, flags=re.DOTALL)

# Fix the work memory append
content = content.replace(
    'if llm_result and llm_result.get("reason"):\n        agent["memory"].append(f"Day {day}: {name} worked [LLM: {llm_result[\'reason\']}]")',
    'if llm_result and llm_result.get("thought"):\n        agent["memory"].append(f"Day {day}: {name} worked [LLM Thought: {llm_result[\'thought\']}]")'
)

# 3. Update _team_meeting signature
content = re.sub(
    r'def _team_meeting\(agents: list, world: dict, day: int\) -> list:',
    'def _team_meeting(agents: list, world: dict, day: int, day_data: dict = None) -> list:',
    content
)

# Insert the decide_meeting_narrative call
old_threshold_block = r'''            # Threshold crossing — log once per pair \(using A's view\)
            new_ab = rel_ab\["affinity"\]
            if old_ab < 70 and new_ab >= 70:
                world\["event_log"\].append\(
                    f"Day \{day\}: \{a\['name'\]\} and \{b\['name'\]\} are becoming close friends."
                \)
            elif old_ab >= 30 and new_ab < 30:
                world\["event_log"\].append\(
                    f"Day \{day\}: \{a\['name'\]\} and \{b\['name'\]\} are growing tense with each other."
                \)'''

new_threshold_block = '''            # Meeting Narrative
            from engine.llm_client import decide_meeting_narrative
            narrative = decide_meeting_narrative(a, b)
            if narrative:
                rel_ab["last_meeting_narrative"] = narrative
                rel_ba["last_meeting_narrative"] = narrative
                if day_data is not None:
                    day_data["meetings"].append({"agents": [a["name"], b["name"]], "narrative": narrative})

            # Threshold crossing — log once per pair (using A's view)
            new_ab = rel_ab["affinity"]
            if old_ab < 70 and new_ab >= 70:
                world["event_log"].append(
                    f"Day {day}: {a['name']} and {b['name']} are becoming close friends."
                )
            elif old_ab >= 30 and new_ab < 30:
                world["event_log"].append(
                    f"Day {day}: {a['name']} and {b['name']} are growing tense with each other."
                )'''

content = re.sub(old_threshold_block, new_threshold_block, content, flags=re.DOTALL)

# 4. Update run_world_for loop
old_day_loop = r'''        austerity = world\["company_budget"\] < AUSTERITY_THRESHOLD

        # ── TEAM MEETING \(every 7th day\) ──────────────────────────────────────
        if day % 7 == 0:
            agent_summaries = _team_meeting\(agents, world, day\)
            world\["event_log"\].append\(
                f"Day \{day\}: Team meeting held -- all agents refreshed"
            \)
            meeting_note = "  \*\*\* TEAM MEETING \*\*\*"
        else:
            # ── Normal individual day ─────────────────────────────────────────
            for agent in agents:
                _tick_needs\(agent\)

            # Build name map once per day for LLM prompt labels
            name_map = \{a\["id"\]: a\["name"\] for a in agents\}

            # Inject transient context into each agent \(cleaned up after the call\)
            for agent in agents:
                agent\["_name_map"\]   = name_map
                agent\["_all_agents"\] = agents

            agent_summaries = \[
                _agent_day\(agent, world, day, austerity=austerity, all_agents=agents\)
                for agent in agents
            \]'''

new_day_loop = '''        austerity = world["company_budget"] < AUSTERITY_THRESHOLD

        day_data = {"day": day, "thoughts": {}, "meetings": []}

        # ── TEAM MEETING (every 7th day) ──────────────────────────────────────
        if day % 7 == 0:
            agent_summaries = _team_meeting(agents, world, day, day_data=day_data)
            world["event_log"].append(
                f"Day {day}: Team meeting held -- all agents refreshed"
            )
            meeting_note = "  *** TEAM MEETING ***"
        else:
            # ── Normal individual day ─────────────────────────────────────────
            for agent in agents:
                _tick_needs(agent)

            # Build name map once per day for LLM prompt labels
            name_map = {a["id"]: a["name"] for a in agents}

            # Inject transient context into each agent (cleaned up after the call)
            for agent in agents:
                agent["_name_map"]   = name_map
                agent["_all_agents"] = agents

            agent_summaries = [
                _agent_day(agent, world, day, austerity=austerity, all_agents=agents, day_data=day_data)
                for agent in agents
            ]'''

content = re.sub(old_day_loop, new_day_loop, content, flags=re.DOTALL)
    
# Save day_data at the end of the loop iteration
old_end_loop = r'''        if world\["current_day"\] % 30 == 0:
            _quarterly_report\(world, agents\)'''

new_end_loop = '''        # Save chronicle data if anything happened
        if day_data["thoughts"] or day_data["meetings"]:
            import os, json
            chron_dir = os.path.join(os.path.dirname(__file__), "..", "data", "chronicle")
            os.makedirs(chron_dir, exist_ok=True)
            with open(os.path.join(chron_dir, f"day_{day}.json"), "w") as f:
                json.dump(day_data, f, indent=4)

        if world["current_day"] % 30 == 0:
            _quarterly_report(world, agents)'''

content = re.sub(old_end_loop, new_end_loop, content, flags=re.DOTALL)

with open('engine/scheduler.py', 'w') as f:
    f.write(content)
print("Regex replace finished.")
