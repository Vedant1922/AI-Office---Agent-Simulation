import json
import sys
from engine.llm_client import generate_weekly_reflection, decide_relationship_update

def main():
    print("Loading agents...")
    with open("data/agents.json", "r") as f:
        agents = json.load(f)
        
    sam = agents[0]
    priya = agents[1]
    
    print("\n=== GENERATING SAMPLE WEEKLY REFLECTION (Sam) ===")
    recent_mems = sam.get("memory", [])[-15:]
    reflection = generate_weekly_reflection(sam, recent_mems)
    print(f"Result: {reflection}")
    
    print("\n=== GENERATING SAMPLE RELATIONSHIP UPDATE (Sam & Priya) ===")
    shared = []
    for m in sam.get("memory", [])[-30:]:
        if priya["name"] in m.get("text", ""): shared.append(m)
    for m in priya.get("memory", [])[-30:]:
        if sam["name"] in m.get("text", ""): shared.append(m)
        
    res = decide_relationship_update(sam, priya, shared)
    print(f"Result Note: {res.get('note') if res else 'None'}")
    print(f"Result Affinity Delta: {res.get('affinity_delta') if res else 'None'}")

if __name__ == "__main__":
    main()
