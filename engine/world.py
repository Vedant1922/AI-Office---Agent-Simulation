import json
import random
import os

# Path to the world state file, relative to this file's location
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "world_state.json")

# Original small flavor events (unchanged)
MINOR_EVENTS = [
    "Minor budget review",
    "Office maintenance day",
    "Quiet news day",
    "Local market shifted slightly",
]

MARKET_MOODS    = ["stable", "stable", "stable", "boom", "boom", "recession", "recession"]
DEPT_NAMES      = ["Engineering", "Sales", "Support", "Marketing"]


def load_world() -> dict:
    """Read world_state.json and return it as a Python dict."""
    with open(DATA_PATH, "r") as f:
        return json.load(f)


def save_world(world_state: dict) -> None:
    """Write the world state dict back to world_state.json."""
    with open(DATA_PATH, "w") as f:
        json.dump(world_state, f, indent=4)


def _migrate_world(world_state: dict) -> dict:
    """
    Defensively add any new top-level fields that might be missing from older saves.
    Never overwrites existing values.
    """
    defaults = {
        "reputation":                    50,
        "market_mood":                   "stable",
        "market_days_remaining":         random.randint(10, 20),
        "last_quarter_revenue_snapshot": 0,
        "last_negative_rep_day":         0,
        "departments": {
            dept: {"active_project": None, "queue": [], "completed_count": 0, "total_revenue": 0}
            for dept in DEPT_NAMES
        },
    }
    for key, val in defaults.items():
        if key not in world_state:
            world_state[key] = val
    # Ensure all 4 departments exist inside the departments dict
    for dept in DEPT_NAMES:
        if dept not in world_state["departments"]:
            world_state["departments"][dept] = {
                "active_project": None, "queue": [], "completed_count": 0, "total_revenue": 0
            }
    return world_state


def apply_daily_drift(world_state: dict) -> dict:
    """
    Simulate the world ticking forward one day.

    Changes applied:
    - company_budget  : decreases by a random amount between 20 and 80,
                        modified by market_mood (boom -25%, recession +50%)
    - market_mood     : timer counts down; when it hits 0 a new mood is rolled
    - morale_index    : NOT randomly drifted — computed from agents in scheduler.py
    - event_log       : minor flavor event (15% chance) always checked;
                        PLUS three major world events checked independently (Part F)
    - reputation      : modified by major events
    """
    world_state = _migrate_world(world_state)
    day         = world_state["current_day"]

    # ── Market mood countdown ─────────────────────────────────────────────────
    world_state["market_days_remaining"] -= 1
    if world_state["market_days_remaining"] <= 0:
        new_mood = random.choice(MARKET_MOODS)   # weighted 3:2:2
        world_state["market_mood"]           = new_mood
        world_state["market_days_remaining"] = random.randint(10, 20)
        world_state["event_log"].append(
            f"Day {day}: Market shifted to '{new_mood}'"
        )

    # ── Budget drift (market-modified operating cost) ─────────────────────────
    # Range reduced from $20-80 to $10-40 (Part B: right-sized for company scale)
    base_cost = random.randint(10, 40)
    mood      = world_state["market_mood"]
    if mood == "boom":
        daily_cost = int(base_cost * 0.75)    # 25% cheaper in a boom
    elif mood == "recession":
        daily_cost = int(base_cost * 1.50)    # 50% more expensive in recession
    else:
        daily_cost = base_cost

    # Austerity mode: budget below -3000 triggers cost-cutting (50% reduction)
    if world_state["company_budget"] < -3000:
        daily_cost = max(1, daily_cost // 2)

    world_state["company_budget"] -= daily_cost

    # ── Minor flavor event (15% chance) ──────────────────────────────────────
    if random.random() < 0.15:
        event     = random.choice(MINOR_EVENTS)
        world_state["event_log"].append(f"Day {day}: {event}")

    # ── Part F: Major world events (independent rolls) ────────────────────────
    reputation = world_state.get("reputation", 50)

    # Major client signed (10% chance, only if reputation > 40)
    if reputation > 40 and random.random() < 0.10:
        from engine.economy import generate_project
        dept_name = random.choice(DEPT_NAMES)
        big_proj  = generate_project(day, dept_name)
        big_proj["value"] = random.randint(1500, 2500)   # override to large value
        world_state["departments"][dept_name]["queue"].append(big_proj)
        world_state["event_log"].append(
            f"Day {day}: Major client signed! "
            f"'{big_proj['name']}' added to {dept_name} queue (value ${big_proj['value']:,})"
        )

    # PR scandal (3% daily chance, reduced from 5%)
    if random.random() < 0.03:
        world_state["reputation"] = max(5, world_state.get("reputation", 50) - 15)
        world_state["last_negative_rep_day"] = day   # track for passive drift
        world_state["event_log"].append(
            f"Day {day}: PR scandal! Reputation dropped by 15 "
            f"(now {world_state['reputation']})"
        )

    # Industry award (5% daily chance, only if reputation > 70)
    if world_state.get("reputation", 50) > 70 and random.random() < 0.05:
        world_state["reputation"] = min(100, world_state.get("reputation", 50) + 10)
        world_state["event_log"].append(
            f"Day {day}: Industry award won! Reputation +10 "
            f"(now {world_state['reputation']})"
        )

    return world_state
