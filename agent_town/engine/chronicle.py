import os
import json

def compile_weekly_chronicle(start_day: int, end_day: int) -> str:
    """
    Gathers the week's agent thoughts + meeting narration into one readable markdown file.
    Reads from data/chronicle/day_X.json.
    Outputs to weekly_chronicle_{start_day}_{end_day}.md in the root directory.
    """
    chron_dir = os.path.join(os.path.dirname(__file__), "..", "data", "chronicle")
    out_file = os.path.join(os.path.dirname(__file__), "..", f"weekly_chronicle_{start_day}_{end_day}.md")
    
    lines = []
    lines.append(f"# Agent Town Chronicle (Days {start_day} to {end_day})")
    lines.append("\n*A narrative record of the company, straight from the minds of the agents.*\n")
    
    for day in range(start_day, end_day + 1):
        day_path = os.path.join(chron_dir, f"day_{day}.json")
        if not os.path.exists(day_path):
            continue
            
        with open(day_path, "r") as f:
            data = json.load(f)
            
        thoughts = data.get("thoughts", {})
        meeting_scene = data.get("meeting_scene", "")
        
        if not thoughts and not meeting_scene:
            continue
            
        lines.append(f"## Day {day}")
        
        if thoughts:
            lines.append("### Inner Thoughts")
            for agent_name, thought in thoughts.items():
                lines.append(f"**{agent_name}**: *\"{thought}\"*")
            lines.append("")
            
        if meeting_scene:
            lines.append("### Team Meeting Scene")
            lines.append(meeting_scene)
            lines.append("")
            
        lines.append("---")
        
    final_text = "\n".join(lines)
    with open(out_file, "w") as f:
        f.write(final_text)
        
    print(f"Chronicle compiled and saved to {out_file}")
    return out_file

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 3:
        compile_weekly_chronicle(int(sys.argv[1]), int(sys.argv[2]))
    else:
        print("Usage: python chronicle.py <start_day> <end_day>")
