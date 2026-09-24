import json
import os
import random

# Path to the agents data file
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "agents.json")

DEPARTMENTS = ["Engineering", "Sales", "Support", "Marketing"]


def create_agent(agent_id: str, name: str, role: str,
                 department: str = None) -> dict:
    """
    Return a brand-new agent dict with randomized personality traits.

    Parameters
    ----------
    agent_id   : str        -- unique identifier
    name       : str        -- human-readable name
    role       : str        -- job in the company
    department : str | None -- if None, picks one at random

    relationships starts empty; call wire_relationships(all_agents) after
    adding the new agent to the list so all pairs are connected.
    """
    return {
        "id":            agent_id,
        "name":          name,
        "role":          role,
        "energy":        100,
        "morale":        70,
        "money":         500,
        "hunger":        80,
        "social":        60,
        "stress":        20,
        "department":    department or random.choice(DEPARTMENTS),
        "relationships": {},   # {other_agent_id: {"affinity": 50, "interactions": 0}}
        "personality": {
            "diligence":      random.randint(20, 80),
            "ambition":       random.randint(20, 80),
            "honesty":        random.randint(20, 80),
            "sociability":    random.randint(20, 80),
            "risk_tolerance": random.randint(20, 80),
        },
        "memory": [],
    }


def wire_relationships(agents: list) -> None:
    """
    Ensure every pair of agents has a bidirectional relationship entry.
    Called after loading AND after adding any new agent.
    Never overwrites existing affinity/interaction values — only adds missing entries.
    """
    for agent in agents:
        if "relationships" not in agent:
            agent["relationships"] = {}

    for i, a in enumerate(agents):
        for j, b in enumerate(agents):
            if i == j:
                continue
            # Add B to A's relationships if missing
            if b["id"] not in a["relationships"]:
                a["relationships"][b["id"]] = {"affinity": 50, "interactions": 0}


def migrate_agents(agents: list) -> list:
    """
    Defensively add any missing fields to agents loaded from agents.json.
    Called once on load — never overwrites existing values.

    Migrations applied:
    - "department"    : round-robin if missing
    - "hunger"        : default 80
    - "social"        : default 60
    - "stress"        : default 20
    - "relationships" : wired up by wire_relationships() at the end
    """
    for i, agent in enumerate(agents):
        if "department"    not in agent:
            agent["department"]    = DEPARTMENTS[i % len(DEPARTMENTS)]
        if "hunger"        not in agent:
            agent["hunger"]        = 80
        if "social"        not in agent:
            agent["social"]        = 60
        if "stress"        not in agent:
            agent["stress"]        = 20
        if "relationships" not in agent:
            agent["relationships"] = {}
        
        # Energy clamp (Part A)
        agent["energy"] = max(0, min(100, agent.get("energy", 100)))

        # Memory migration (Part B)
        for m_idx, m in enumerate(agent.get("memory", [])):
            if isinstance(m, str):
                day_val = 0
                if m.startswith("Day "):
                    try:
                        day_val = int(m.split(":")[0].replace("Day ", ""))
                    except ValueError:
                        pass
                agent["memory"][m_idx] = {
                    "day": day_val,
                    "text": m,
                    "type": "event",
                    "importance": 3
                }

    # Wire all pairs — adds missing entries, preserves existing
    wire_relationships(agents)
    return agents


def load_agents() -> list:
    """
    Read data/agents.json and return the list of agent dicts.
    Returns an empty list if the file doesn't exist yet.
    Runs migrate_agents() to add any missing fields with safe defaults.
    """
    if not os.path.exists(DATA_PATH):
        return []

    with open(DATA_PATH, "r") as f:
        agents = json.load(f)

    return migrate_agents(agents)


def save_agents(agents: list) -> None:
    """Write the list of agent dicts back to data/agents.json."""
    with open(DATA_PATH, "w") as f:
        json.dump(agents, f, indent=4)
