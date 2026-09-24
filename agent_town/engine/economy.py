"""
engine/economy.py
Handles client projects: generation, queue management, progress, completion, deadlines.
"""
import random
import uuid

DEPARTMENTS = ["Engineering", "Sales", "Support", "Marketing"]

# Words used to build randomized project names
_CLIENT_NAMES = [
    "Acme", "Zenith", "Apex", "Nova", "Bolt", "Crest", "Titan", "Vortex",
    "Pixel", "Flux", "Orbit", "Pinnacle", "Dusk", "Ember", "Cipher",
]
_PROJECT_TYPES = [
    "Website Redesign", "App Launch", "Market Campaign", "Data Migration",
    "Brand Refresh", "Customer Portal", "API Integration", "Sales Funnel",
    "Support Overhaul", "Infrastructure Audit", "Product Rollout", "SEO Blitz",
]


def generate_project(current_day: int, department: str = None) -> dict:
    """
    Create and return a new client project dict.

    Parameters
    ----------
    current_day : int   — used to compute the deadline
    department  : str   — if None, picks one at random from DEPARTMENTS
    """
    dept       = department or random.choice(DEPARTMENTS)
    difficulty = random.randint(1, 10)
    value      = 300 + difficulty * 220
    client     = random.choice(_CLIENT_NAMES)
    ptype      = random.choice(_PROJECT_TYPES)

    return {
        "id":           str(uuid.uuid4())[:8],
        "name":         f"{client} Corp {ptype}",
        "department":   dept,
        "difficulty":   difficulty,
        "value":        value,
        "progress":     0,
        "deadline_day": current_day + random.randint(15, 30),
    }


def tick_departments(world: dict) -> None:
    """
    Called once per day BEFORE agents act.

    For each department:
    1. If no active_project and queue is non-empty  → pop next project into active slot.
    2. If no active_project AND queue is empty       → roll for new project arrival.
       Arrival chance = base 20%
                      + (reputation - 50) * 0.3   (Part C)
                      + market modifier            (Part D: boom +15, recession -15)
    """
    reputation   = world.get("reputation", 50)
    market_mood  = world.get("market_mood", "stable")
    current_day  = world["current_day"]
    departments  = world["departments"]

    market_bonus = {"boom": 15, "stable": 0, "recession": -15}.get(market_mood, 0)
    arrival_pct  = 20 + (reputation - 50) * 0.3 + market_bonus   # percentage
    arrival_prob = max(0.0, min(1.0, arrival_pct / 100))

    for dept_name, dept in departments.items():
        if dept["active_project"] is None:
            if dept["queue"]:
                dept["active_project"] = dept["queue"].pop(0)
            elif random.random() < arrival_prob:
                new_proj = generate_project(current_day, dept_name)
                dept["queue"].append(new_proj)
                # Immediately pop it into active (queue was empty)
                dept["active_project"] = dept["queue"].pop(0)


def check_deadlines(world: dict, agents: list) -> None:
    """
    Called once per day AFTER agents act.
    Any active project past its deadline is cancelled: no revenue, reputation -5.
    Also logs the failure to each relevant agent's memory.
    """
    from engine.memory import create_memory
    current_day = world["current_day"]
    departments = world["departments"]

    for dept_name, dept in departments.items():
        proj = dept["active_project"]
        if proj is None:
            continue
        if current_day > proj["deadline_day"] and proj["progress"] < 100:
            world["event_log"].append(
                f"Day {current_day}: {dept_name} missed the deadline on "
                f"'{proj['name']}' — client walked away"
            )
            world["reputation"] = max(5, world.get("reputation", 50) - 5)
            world["last_negative_rep_day"] = current_day   # track for passive drift
            dept["active_project"] = None
            
            # Log failure to agents in this department
            for agent in agents:
                if agent.get("department") == dept_name:
                    agent["memory"].append(create_memory(
                        current_day,
                        f"Day {current_day}: I failed to meet the deadline for '{proj['name']}'",
                        type="event",
                        importance=7
                    ))


def apply_project_progress(agent: dict, world: dict, day: int) -> str | None:
    """
    When an agent works, contribute progress to their department's active project.
    Returns a log string if a project completes, else None.

    progress_gained = 8 + diligence * 0.15   (capped so project stays <= 100)
    On completion:
      - world["company_budget"]    += project value
      - department total_revenue   += project value
      - department completed_count += 1
      - reputation                 += 3 (capped 100)
      - active_project             = None
    """
    dept_name   = agent.get("department")
    if not dept_name:
        return None

    dept = world["departments"].get(dept_name)
    if not dept or dept["active_project"] is None:
        return None

    proj      = dept["active_project"]
    diligence = agent["personality"]["diligence"]
    # progress rate raised from (8 + diligence*0.15) to (10 + diligence*0.18) — Part B
    gain      = 10 + diligence * 0.18
    proj["progress"] = min(100, proj["progress"] + gain)

    if proj["progress"] >= 100:
        value = proj["value"]
        world["company_budget"]      += value
        dept["total_revenue"]        += value
        dept["completed_count"]      += 1
        world["reputation"]           = min(100, world.get("reputation", 50) + 4)
        world["event_log"].append(
            f"Day {day}: {dept_name} completed '{proj['name']}' "
            f"— earned ${value:,} in revenue"
        )
        dept["active_project"] = None
        return f"[PROJECT DONE: {proj['name']} +${value:,}]"

    return None
