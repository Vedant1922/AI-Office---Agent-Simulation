import json
from engine.memory import retrieve_relevant_memories

def test_memory_leak():
    with open("data/agents.json", "r") as f:
        agents = json.load(f)
    with open("data/world_state.json", "r") as f:
        world = json.load(f)
        
    curr_day = world.get("current_day", 898)
    
    # Pick 3 agents: Sam, Priya, Vikram
    target_names = ["Sam", "Priya", "Vikram"]
    
    for agent in agents:
        name = agent["name"]
        if name not in target_names:
            continue
            
        dept = agent.get("department", "Unknown")
        context_keywords = [dept]
        
        # Add relationships
        rels = agent.get("relationships", {})
        sorted_rels = sorted(rels.items(), key=lambda x: -x[1]["affinity"])
        
        # We need name_map to get relationship names
        agent_map = {a["id"]: a["name"] for a in agents}
        for rid, rv in sorted_rels[:2]:
            rname = agent_map.get(rid, f"coworker-{rid}")
            context_keywords.append(rname)
            
        recent_mems = retrieve_relevant_memories(agent, context_keywords, curr_day, top_n=3)
        
        print(f"\n{'='*40}")
        print(f"Agent: {name} | Context Keywords: {context_keywords}")
        print(f"{'='*40}")
        for mem in recent_mems:
            print(f"[{mem.get('day')}] {mem.get('text')}")

if __name__ == "__main__":
    test_memory_leak()
