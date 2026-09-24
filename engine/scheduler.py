import os
import json
import random
from engine.memory import create_memory
from engine.world import load_world, save_world, apply_daily_drift
from engine.agent import load_agents, save_agents, create_agent, wire_relationships
from engine.economy import tick_departments, check_deadlines, apply_project_progress
from engine.llm_client import decide_action as llm_decide

def _log_daily_action(day: int, agent: dict, action: str, target_agent_id: str | None = None, reasoning: str | None = None) -> None:
    record = {
        "day": int(day),
        "agent_id": str(agent["id"]),
        "name": agent["name"],
        "department": agent.get("department", "?"),
        "action": action,
        "target_agent_id": str(target_agent_id) if target_agent_id is not None else None,
        "reasoning": reasoning
    }
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "daily_actions.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

def _log_daily_world_snapshot(day: int, world: dict) -> None:
    record = {
        "day": int(day),
        "budget": world.get("company_budget", 0),
        "reputation": world.get("reputation", 50),
        "market_mood": str(world.get("market_mood", "stable"))
    }
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, "daily_world_snapshot.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

# All agents now use the LLM
LLM_AGENTS = {"Sam", "Priya", "Alex", "Jordan", "Riya", "Vikram"}

# ── Roster: every agent the world should always have ─────────────────────────
AGENT_ROSTER = [
    ("1", "Sam",    "Employee", "Engineering"),
    ("2", "Priya",  "Employee", "Sales"),
    ("3", "Alex",   "Employee", "Support"),
    ("4", "Jordan", "Employee", "Marketing"),
    ("5", "Riya",   "Employee", "Marketing"),
    ("6", "Vikram", "Employee", "Support"),
]

AUSTERITY_THRESHOLD  = -3000
PASSIVE_REP_INTERVAL = 10    # days of quiet before +2 rep (was 14 days/+1)


def _ensure_all_agents(agents: list) -> list:
    """
    Add any missing agents from AGENT_ROSTER without wiping existing ones.
    After adding new agents, calls wire_relationships so all pairs are linked.
    """
    existing_ids = {a["id"] for a in agents}
    added_any    = False
    for agent_id, name, role, dept in AGENT_ROSTER:
        if agent_id not in existing_ids:
            agents.append(create_agent(agent_id, name, role, department=dept))
            added_any = True
    if added_any:
        wire_relationships(agents)
    return agents


# ─────────────────────────────────────────────────────────────────────────────
# HUMAN NEEDS
# ─────────────────────────────────────────────────────────────────────────────

def _tick_needs(agent: dict) -> None:
    """
    Decay human needs at the start of every day (before work/rest decision).
    hunger -15  |  social -6  |  stress +5   (clamped 0-100)
    Social decay reduced from -10 to -6 (Part A balance fix).
    """
    agent["hunger"] = max(0, agent["hunger"] - 15)
    agent["social"] = max(0, agent["social"] - 6)   # was -10
    agent["stress"] = min(100, agent["stress"] + 5)


def _apply_work_needs(agent: dict) -> None:
    """Extra needs cost of a working day."""
    agent["social"] = max(0, agent["social"] - 5)
    agent["stress"] = min(100, agent["stress"] + 8)


def _apply_rest_needs(agent: dict) -> None:
    """Needs recovery on a rest day."""
    agent["social"] = max(0, agent["social"] - 2)
    agent["stress"] = max(0, agent["stress"] - 10)


# ─────────────────────────────────────────────────────────────────────────────
# SOCIABILITY SEED (Part C — targeted friend interaction)
# ─────────────────────────────────────────────────────────────────────────────

def _maybe_socialize(agent: dict, all_agents: list, day: int) -> None:
    """
    If agent's sociability > 50 AND social < 50:
      - Find the coworker with highest affinity (closest friend).
      - Both get social +10.
      - That pair's affinity +2 (in both directions).
      - Log "caught up with [Name]".
    Fallback: if no relationships exist, generic +10 social and generic log.
    Threshold changed from >60 to >50 (Part A balance fix).
    """
    sociability = agent["personality"]["sociability"]
    if not (sociability > 50 and agent["social"] < 50):
        return

    rels = agent.get("relationships", {})
    agent_map = {a["id"]: a for a in all_agents if a["id"] != agent["id"]}

    if rels and agent_map:
        # Find coworker with highest affinity
        best_id = max(rels, key=lambda rid: rels.get(rid, {}).get("affinity", 0))
        friend  = agent_map.get(best_id)

        if friend:
            agent["social"]  = min(100, agent["social"]  + 10)
            friend["social"] = min(100, friend["social"] + 10)

            # Reinforce affinity in both directions
            rels[best_id]["affinity"] = min(100, rels[best_id]["affinity"] + 2)
            f_rels = friend.get("relationships", {})
            if agent["id"] in f_rels:
                f_rels[agent["id"]]["affinity"] = min(100, f_rels[agent["id"]]["affinity"] + 2)

            agent["memory"].append(create_memory(day, f"Day {day}: {agent['name']} caught up with {friend['name']}", importance=2))
            return

    # Fallback — no relationships or no matching agent found
    agent["social"] = min(100, agent["social"] + 10)
    agent["memory"].append(create_memory(day, f"Day {day}: {agent['name']} made a point to chat with coworkers.", importance=2))


# ─────────────────────────────────────────────────────────────────────────────
# CORE AGENT DAY
# ─────────────────────────────────────────────────────────────────────────────

def _agent_day(agent: dict, world: dict, day: int,
               austerity: bool = False,
               all_agents: list = None,
               day_data: dict = None) -> str:
    """
    Apply one day of logic to an agent.

    Decision priority (checked in order, first match wins):
      1. hunger < 25    -> eat       (hunger +40, money -20, no work)
      2. stress > 80    -> stress day (stress -30, morale +5, no work)
      3. morale < 20    -> burnout rest (energy +20, morale +8, no work)
      4. energy < rest_threshold -> normal rest (energy +20, morale +8)
      5. otherwise      -> work

    Part C sociability seed runs BEFORE the decision tree on non-meeting days.
    Part D department relationship morale effects applied inside the WORK path.
    """
    name        = agent["name"]
    diligence   = agent["personality"]["diligence"]
    ambition    = agent["personality"]["ambition"]
    honesty     = agent["personality"]["honesty"]
    dept        = agent.get("department", "?")

    def _header(action: str) -> str:
        return (
            f"{name}[{dept},d={diligence},"
            f"mor={agent['morale']:>3},"
            f"hgr={agent['hunger']:>3},"
            f"soc={agent['social']:>3},"
            f"str={agent['stress']:>3}]: {action}"
        )

    # ── Sociability seed (Part C) ─────────────────────────────────────────────
    _maybe_socialize(agent, all_agents or [], day)

    # ── 1. HUNGER OVERRIDE ────────────────────────────────────────────────────
    if agent["hunger"] < 25:
        agent["hunger"] = min(100, agent["hunger"] + 40)
        agent["money"]  = max(0, agent["money"] - 20)
        agent["memory"].append(create_memory(day, f"Day {day}: {name} stopped to eat", importance=4))
        _log_daily_action(day, agent, "eat", target_agent_id=None, reasoning="Hunger critical, stopped to eat")
        return _header("ATE") + f" (hgr={agent['hunger']:>3}, $={agent['money']:>5,})"

    # ── 2. STRESS OVERRIDE ────────────────────────────────────────────────────
    if agent["stress"] > 80:
        agent["stress"] = max(0, agent["stress"] - 30)
        agent["morale"] = min(100, agent["morale"] + 5)
        agent["memory"].append(create_memory(day, f"Day {day}: {name} took a stress day", importance=4))
        _log_daily_action(day, agent, "stress-day", target_agent_id=None, reasoning="Stress critical, took a stress day")
        return _header("STRESS-DAY") + f" (str={agent['stress']:>3}, mor={agent['morale']:>3})"

    # ── 3. BURNOUT OVERRIDE ───────────────────────────────────────────────────
    if agent["morale"] < 20:
        agent["energy"] = min(100, agent["energy"] + 20)
        agent["morale"] = min(100, agent["morale"] + 8)
        _apply_rest_needs(agent)
        agent["memory"].append(create_memory(day, f"Day {day}: {name} burned out and rested (morale too low)", importance=4))
        _log_daily_action(day, agent, "burnout-rest", target_agent_id=None, reasoning="Morale critical, burned out and rested")
        return _header("BURNOUT-REST") + f" (nrg={agent['energy']:>3}, $={agent['money']:>5,})"

    # ── 3b. LLM GATE (overrides diligence rule for LLM_AGENTS) ───────────────
    # Hunger/stress/burnout already had a chance to short-circuit above.
    # Now ask the LLM what to do. If it fails, fall through to rule logic.
    llm_result = None
    llm_source  = "rule"
    if name in LLM_AGENTS:
        dept_state = world.get("departments", {}).get(dept, {})
        name_map   = agent.get("_name_map", {})
        llm_result = llm_decide(agent, world, dept_state, name_map=name_map)
        if llm_result:
            llm_source = "llm"

    if llm_result:
        chosen = llm_result.get("action", "work")
        thought = llm_result.get("thought", "")
        who = llm_result.get("who")
        
        if day_data is not None:
            day_data["thoughts"][name] = thought

        if chosen == "rest":
            agent["energy"] = min(100, agent["energy"] + 20)
            agent["morale"] = min(100, agent["morale"] + 8)
            _apply_rest_needs(agent)
            agent["memory"].append(create_memory(day, f"Day {day}: {name} chose to rest [LLM Thought: {thought}]", importance=2))
            _log_daily_action(day, agent, "rest", target_agent_id=None, reasoning=thought)
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
                    agent["memory"].append(create_memory(day, f"Day {day}: {name} caught up with {friend['name']} [LLM Thought: {thought}]", importance=2))
                    _log_daily_action(day, agent, "socialize", target_agent_id=str(best_id), reasoning=thought)
                    return _header(f"SOCIAL[LLM]") + f" (soc={agent['social']:>3})"
                    
            # Fallback if no relationships
            agent["social"] = min(100, agent["social"] + 10)
            agent["memory"].append(create_memory(day, f"Day {day}: {name} chatted with coworkers [LLM Thought: {thought}]", importance=2))
            _log_daily_action(day, agent, "socialize", target_agent_id=None, reasoning=thought)
            return _header("SOCIAL[LLM]") + f" (soc={agent['social']:>3})"

        # chosen == "work" — fall through to work path below
        # (reason will be appended inside the work block)

    # ── 4. DILIGENCE REST THRESHOLD ───────────────────────────────────────────
    rest_threshold = 50 - (diligence - 50) * 0.4
    rest_threshold = max(10, min(50, rest_threshold))

    if agent["energy"] < rest_threshold and llm_source == "rule":
        agent["energy"] = min(100, agent["energy"] + 20)
        agent["morale"] = min(100, agent["morale"] + 8)
        _apply_rest_needs(agent)
        agent["memory"].append(create_memory(day, f"Day {day}: {name} rested early (low diligence={diligence})" if diligence < 50 else f"Day {day}: {name} rested (threshold={rest_threshold:.0f})", importance=2))
        _log_daily_action(day, agent, "rest", target_agent_id=None, reasoning="Diligence threshold rest")
        return _header("RESTED") + f" (nrg={agent['energy']:>3}, $={agent['money']:>5,})"

    # ── 5. WORK ───────────────────────────────────────────────────────────────
    money_earned = int(40 + diligence * 0.2)
    if austerity:
        money_earned = int(money_earned * 0.85)

    agent["energy"]         = max(0, agent["energy"] - 10)
    agent["money"]          += money_earned
    # Company deducted 65% of wage (agent take-home is unchanged) — Part B
    world["company_budget"] -= int(money_earned * 0.65)

    morale_drain = 2 if ambition > 65 else 5
    agent["morale"] = max(0, agent["morale"] - morale_drain)

    _apply_work_needs(agent)
    if llm_result and llm_result.get("thought"):
        agent["memory"].append(create_memory(day, f"Day {day}: {name} worked [LLM Thought: {llm_result['thought']}]", importance=3))
    else:
        agent["memory"].append(create_memory(day, f"Day {day}: {name} worked (diligence-driven, earned {money_earned})", importance=3))

    # ── Part D: Department relationship morale effects ─────────────────────────
    dept_coworkers = [
        a for a in (all_agents or [])
        if a["id"] != agent["id"] and a.get("department") == dept
    ]
    agent_rels = agent.get("relationships", {})
    has_friend  = any(agent_rels.get(cw["id"], {}).get("affinity", 50) > 70
                      for cw in dept_coworkers)
    has_tension = any(agent_rels.get(cw["id"], {}).get("affinity", 50) < 30
                      for cw in dept_coworkers)
    if has_friend:
        agent["morale"] = min(100, agent["morale"] + 2)
    if has_tension:
        agent["morale"] = max(0, agent["morale"] - 2)
        penalty_msg = f"Day {day}: {name} suffered a department morale penalty (-2) due to tension with a coworker (morale now {agent['morale']})."
        world.setdefault("event_log", []).append(penalty_msg)
        print(f"\n >>> [TENSION PENALTY] {penalty_msg}")

    # Project progress
    proj_note = apply_project_progress(agent, world, day)
    if proj_note:
        # proj_note is only returned when a project is DONE
        agent["memory"].append(create_memory(day, f"Day {day}: {name} finished {proj_note}", importance=7))

    # Honesty cheat
    cheat_chance = (100 - honesty) / 100
    if random.random() < cheat_chance:
        agent["money"] += 5
        agent["memory"].append(create_memory(day, f"Day {day}: {name} quietly overreported their work.", importance=3))
        money_earned += 5

    proj_str = f" {proj_note}" if proj_note else ""
    src_tag  = "[LLM]" if llm_source == "llm" else ""
    work_thought = llm_result.get("thought") if (llm_result and llm_result.get("thought")) else None
    _log_daily_action(day, agent, "work", target_agent_id=None, reasoning=work_thought)
    return _header(f"WORKED{src_tag}") + (
        f" (nrg={agent['energy']:>3}, $={agent['money']:>5,},"
        f" earned={money_earned}){proj_str}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TEAM MEETING (every 7th day)  — Part B relationship updates included
# ─────────────────────────────────────────────────────────────────────────────

def _team_meeting(agents: list, world: dict, day: int, day_data: dict = None) -> list:
    """
    Replace individual work/rest with a full-team meeting.

    Every agent:  social +25 (was +20), stress -15, morale +10

    Part B: For every pair, compute personality compatibility and apply
    a small affinity change.  Logs threshold crossings to event_log
    (first time a pair crosses 70 upward = friends, or 30 downward = tension).
    Threshold detection uses A's view of B to avoid double-logging.
    """
    # ── Part B: Relationship updates for all pairs ────────────────────────────
    for i in range(len(agents)):
        for j in range(i + 1, len(agents)):
            a = agents[i]
            b = agents[j]

            rel_ab = a["relationships"].setdefault(b["id"], {"affinity": 50, "interactions": 0})
            rel_ba = b["relationships"].setdefault(a["id"], {"affinity": 50, "interactions": 0})
            
            old_ab = rel_ab["affinity"]
            old_ba = rel_ba["affinity"]

            # Only do the expensive update if in same department or affinity > 60
            if a.get("department") == b.get("department") or old_ab > 60:
                from engine.llm_client import decide_relationship_update
                import random
                
                # Gather recent shared memories
                shared = []
                for m in a.get("memory", [])[-30:]:
                    if b["name"] in m.get("text", ""): shared.append(m)
                for m in b.get("memory", [])[-30:]:
                    if a["name"] in m.get("text", ""): shared.append(m)
                
                res = decide_relationship_update(a, b, shared)
                if res:
                    try:
                        delta = int(res.get("affinity_delta", 0))
                    except (ValueError, TypeError):
                        delta = 0
                    rel_ab["note"] = res.get("note", "")
                    rel_ba["note"] = res.get("note", "")
                else:
                    delta = random.randint(-1, 1)
            else:
                import random
                delta = random.randint(-1, 1)

            rel_ab["affinity"]     = max(0, min(100, old_ab + delta))
            rel_ab["interactions"] += 1
            rel_ba["affinity"]     = max(0, min(100, old_ba + delta))
            rel_ba["interactions"] += 1

            # Threshold crossing — log once per pair (using A's view)
            new_ab = rel_ab["affinity"]
            if old_ab < 70 and new_ab >= 70:
                msg = f"Day {day}: {a['name']} and {b['name']} are becoming close friends."
                world["event_log"].append(msg)
                a["memory"].append(create_memory(day, msg, importance=8))
                b["memory"].append(create_memory(day, msg, importance=8))
            elif old_ab >= 30 and new_ab < 30:
                msg = f"Day {day}: {a['name']} and {b['name']} are growing tense with each other."
                world["event_log"].append(msg)
                print(f"\n >>> [TENSION EVENT] {msg}")
                a["memory"].append(create_memory(day, msg, importance=8))
                b["memory"].append(create_memory(day, msg, importance=8))

    # ── Group Meeting Narrative ──────────────────────────────────────────────
    if day_data is not None:
        from engine.llm_client import decide_group_meeting_narrative
        scene = decide_group_meeting_narrative(agents)
        if scene:
            day_data["meeting_scene"] = scene

    # ── Meeting benefits for every agent ─────────────────────────────────────
    summaries = []
    for agent in agents:
        _log_daily_action(day, agent, "meeting", target_agent_id=None, reasoning="Attended weekly team meeting")
        agent["social"] = min(100, agent["social"] + 25)  # was +20
        agent["stress"] = max(0,   agent["stress"] - 15)
        agent["morale"] = min(100, agent["morale"] + 10)
        agent["memory"].append(create_memory(day, f"Day {day}: {agent['name']} attended the team meeting", importance=2))
        
        # Weekly reflection
        from engine.llm_client import generate_weekly_reflection
        recent_mems = agent.get("memory", [])[-15:] # Last 15 events
        reflection = generate_weekly_reflection(agent, recent_mems)
        if reflection:
            agent["memory"].append(create_memory(day, reflection, type="reflection", importance=9))
        summaries.append(
            f"{agent['name']}[{agent['department']},"
            f"mor={agent['morale']:>3},"
            f"soc={agent['social']:>3},"
            f"str={agent['stress']:>3}]: MEETING"
        )
    return summaries


# ─────────────────────────────────────────────────────────────────────────────
# QUARTERLY REPORT
# ─────────────────────────────────────────────────────────────────────────────

def _quarterly_report(world: dict, agents: list) -> None:
    """Print a distinct quarterly summary block."""
    depts         = world["departments"]
    snap          = world.get("last_quarter_revenue_snapshot", 0)
    total_rev_now = sum(d["total_revenue"] for d in depts.values())
    quarter_rev   = total_rev_now - snap

    print("\n" + "=" * 70)
    print(f"  *** QUARTERLY REPORT  --  End of Day {world['current_day']} ***")
    print("=" * 70)
    print(f"  Revenue this quarter : ${quarter_rev:>8,}")
    print(f"  Company budget       : ${world['company_budget']:>8,}")
    print(f"  Reputation           : {world['reputation']:>3}/100")
    print(f"  Market mood          : {world['market_mood']}")
    print()
    for dept_name, dept in depts.items():
        print(f"  {dept_name:<12} | completed: {dept['completed_count']:>3}  |  "
              f"total revenue: ${dept['total_revenue']:>7,}")
    print()
    for agent in agents:
        # Show top relationship
        rels = agent.get("relationships", {})
        if rels:
            top_id  = max(rels, key=lambda rid: rels[rid]["affinity"])
            top_aff = rels[top_id]["affinity"]
            top_name = next((a["name"] for a in agents if a["id"] == top_id), top_id)
            rel_str  = f"  closest={top_name}({top_aff})"
        else:
            rel_str = ""
        print(f"  {agent['name']:<8} [{agent['department']}]  "
              f"morale={agent['morale']:>3}  energy={agent['energy']:>3}  "
              f"hunger={agent['hunger']:>3}  stress={agent['stress']:>3}  "
              f"money=${agent['money']:>6,}{rel_str}")
    print("=" * 70 + "\n")

    world["last_quarter_revenue_snapshot"] = total_rev_now


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────────────

def run_world_for(days: int) -> None:
    """
    Load world + agents, simulate for `days`, save both.

    Daily flow:
    1. apply_daily_drift    -- budget cost, market, minor + major events
    2. tick_departments     -- queue management, project arrival
    3. check_deadlines      -- cancel overdue projects, rep penalty
    4. Passive rep drift    -- +1 every 14 quiet days (Part A)
    5. Team meeting OR individual agent day
       - Meeting (day % 7 == 0): social +25, stress -15, morale +10 + relationship update
       - Individual: tick_needs, sociability seed, work/rest/eat/stress decision
    6. World morale_index   -- average of agents' morale
    7. Quarterly report     -- every 30th day
    8. Increment day, print summary
    Finally: save world + agents.
    """
    world  = load_world()
    agents = _ensure_all_agents(load_agents())

    for _ in range(days):
        world = apply_daily_drift(world)
        day   = world["current_day"]

        tick_departments(world)
        check_deadlines(world, agents)

        # ── Part A: Passive reputation drift every 14 quiet days ──────────────
        if day % PASSIVE_REP_INTERVAL == 0:
            last_neg = world.get("last_negative_rep_day", 0)
            if day - last_neg >= PASSIVE_REP_INTERVAL:
                world["reputation"] = min(100, world.get("reputation", 50) + 2)
                world["event_log"].append(
                    f"Day {day}: Quiet period paid off -- reputation +2 "
                    f"(now {world['reputation']})"
                )

        austerity = world["company_budget"] < AUSTERITY_THRESHOLD

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
            ]

            # Clean up transient keys so they don't pollute the saved JSON
            for agent in agents:
                agent.pop("_name_map",   None)
                agent.pop("_all_agents", None)

            meeting_note = ""

            if austerity:
                world["event_log"].append(
                    f"Day {day}: Austerity mode active -- budget critical"
                )

        # World morale = average of all agents
        world["morale_index"] = round(
            sum(a["morale"] for a in agents) / len(agents)
        )

        _log_daily_world_snapshot(day, world)

        world["current_day"] += 1

        # Save chronicle data if anything happened
        if day_data["thoughts"] or day_data.get("meeting_scene"):
            import os, json
            chron_dir = os.path.join(os.path.dirname(__file__), "..", "data", "chronicle")
            os.makedirs(chron_dir, exist_ok=True)
            with open(os.path.join(chron_dir, f"day_{day}.json"), "w") as f:
                json.dump(day_data, f, indent=4)

        # Quarterly report every 30th day
        if world["current_day"] % 30 == 0:
            _quarterly_report(world, agents)

        # Active project summary
        active = []
        for dept_name, dept in world["departments"].items():
            p = dept["active_project"]
            if p:
                active.append(f"{dept_name}:{p['name'][:12]}({p['progress']:.0f}%)")
        proj_line    = "  Projects: " + ", ".join(active) if active else ""
        austerity_flag = " [AUSTERITY]" if austerity else ""

        print(
            f"Day {day:>3}{austerity_flag} | "
            f"Budget: ${world['company_budget']:>8,} | "
            f"Rep: {world.get('reputation', 50):>3} | "
            f"Mood: {world['market_mood']:<10} | "
            f"WMorale: {world['morale_index']:>3} | "
            + " | ".join(agent_summaries)
            + proj_line
            + meeting_note
        )

    save_world(world)
    save_agents(agents)
    print("\nWorld state and agents saved.")
