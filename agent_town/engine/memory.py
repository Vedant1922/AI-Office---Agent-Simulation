def create_memory(day: int, text: str, type: str = "event", importance: int = 3) -> dict:
    """
    Creates a standardized memory object.
    type should be 'event' or 'reflection'.
    importance from 1-10.
    """
    return {
        "day": day,
        "text": text,
        "type": type,
        "importance": importance
    }

def retrieve_relevant_memories(agent: dict, context_keywords: list[str], current_day: int, top_n: int = 5) -> list[dict]:
    """
    Scores every memory by:
      1/(1 + days_ago*0.1) * importance + (2 points per context_keyword matched)
    Returns the top N memories, sorted by score descending.
    """
    memories = agent.get("memory", [])
    if not memories:
        return []

    scored = []
    # Make keywords lowercase for simpler matching
    keywords = [kw.lower() for kw in context_keywords if kw]

    for m in memories:
        days_ago = max(0, current_day - m.get("day", current_day))
        
        # Break the feedback loop: exclude recent reflections
        if m.get("type") == "reflection" and days_ago < 3:
            continue
            
        recency = 1.0 / (1.0 + days_ago * 0.1)
        
        text_lower = m.get("text", "").lower()
        matches = sum(1 for kw in keywords if kw in text_lower)
        
        score = (recency * m.get("importance", 3)) + (2.0 * matches)
        scored.append((score, m))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:top_n]]
