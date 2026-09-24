# Agent Town — AI Multi-Agent Office Simulation (v1)

Agent Town is a text-based multi-agent simulation of workplace social and economic life. Six persistent agents live in a shared company environment where they balance physiological and emotional needs (energy, hunger, morale, stress, social), form evolving coworker relationships and rivalries, execute client deliverables across four functional departments, and make daily decisions powered by local LLM reasoning grounded in structured episodic memory.

---

## System Architecture

```
                               ┌───────────────────────────┐
                               │   Daily Simulation Loop   │
                               │   (engine/scheduler.py)   │
                               └─────────────┬─────────────┘
                                             │
               ┌─────────────────────────────┼─────────────────────────────┐
               ▼                             ▼                             ▼
   ┌───────────────────────┐    ┌─────────────────────────┐   ┌─────────────────────────┐
   │  Hard Rule Overrides  │    │   LLM Decision Engine   │   │     Company Economy     │
   │  - Hunger >= 60 (EAT) │    │  (engine/llm_client.py) │   │   (engine/economy.py)   │
   │  - Stress >= 85 (REST)│    │  - llama3.2:3b via Ollama │ │  - Client Deliverables  │
   │  - Energy 0 (BURNOUT) │    │  - temp=0.85, repeat=1.3│   │  - Treasury & Salaries  │
   └───────────────────────┘    │  - Tolerant JSON Parser │   │  - Market Mood Cycles   │
                                │  - Rule-based Fallback  │   └─────────────────────────┘
                                └────────────┬────────────┘
                                             │
               ┌─────────────────────────────┴─────────────────────────────┐
               ▼                                                           ▼
   ┌───────────────────────┐                                  ┌─────────────────────────┐
   │ Dynamic Memory System │                                  │ Social Dynamics & Team  │
   │  (engine/memory.py)   │                                  │ - Pairwise Affinity     │
   │  - Recency Decay      │                                  │ - Friendship (>= 70)    │
   │  - Importance Scored  │                                  │ - Tension (< 30, -2 pen)│
   │  - 3-Day Refl Blackout│                                  │ - Weekly Meeting Scene  │
   └───────────────────────┘                                  └─────────────────────────┘
```

### 1. The Six Persistent Agents (`engine/agent.py`)
Each agent has a distinct personality vector (`diligence`, `ambition`, `honesty`, `sociability`, `risk_tolerance` on a 0–100 scale), department affiliation, and living memory:
* **Sam** (Engineering): High diligence, anxiety around delivery deadlines, prone to overreporting work when stressed.
* **Priya** (Sales): Balanced sociability, vulnerable to seeking comfort in food/breaks during project crunches.
* **Alex** (Support): Diligent, seeks external peer validation, highly observant of coworker transparency.
* **Jordan** (Marketing): High honesty and perfectionism, struggles with balancing strict standards and self-care.
* **Riya** (Marketing): Sociable and validation-seeking, thrives in interpersonal catch-ups.
* **Vikram** (Support): Low sociability, low honesty, high risk tolerance, susceptible to imposter anxiety and defensiveness.

### 2. LLM Decision Layer (`engine/llm_client.py`)
* **Model**: Local Ollama execution (`llama3.2:3b`) with 20s execution timeout and retry wrapper.
* **Sampling Parameters**: `temperature=0.85` and `repeat_penalty=1.3` to ensure narrative variety without breaking structure.
* **Tolerant JSON Parser**: Automatically strips key whitespace (e.g., `" action"` $\rightarrow$ `"action"`), normalizes near-valid actions (e.g., `"self-care"` $\rightarrow$ `"rest"`), rejects blank templates, and logs rescued instances.
* **Deterministic Fallback**: If LLM retries fail, a deterministic rule-based backup guarantees zero crash interruption.

### 3. Memory & Reflection Engine (`engine/memory.py`, `engine/chronicle.py`)
* **Episodic Retrieval**: Memories are ranked via `score = (recency_weight * importance) + keyword_bonus`.
* **3-Day Reflection Blackout**: Agents are blocked from retrieving their own weekly reflections into daily action prompts for 3 days, permanently breaking semantic feedback echo chambers.
* **Weekly Reflections**: Agents generate 1–2 sentence first-person psychological reflections every 7 days.
* **Team Meeting Narrative**: Every 7 days, a unified group narrative scene is generated from individual states and logged to the chronicle.

### 4. Economy, Projects & Rivalries (`engine/economy.py`, `engine/scheduler.py`)
* **Department Projects**: Engineering, Sales, Support, and Marketing work on live projects with deadlines and values. Completions pay bonuses into the treasury; missed deadlines trigger financial penalties and market scrutiny.
* **Relationship Dynamics**: Affinity scales 0–100. Pairs crossing $\ge 70$ trigger friendship status. Pairs dropping below 30 enter active **tension**, inflicting a persistent **-2 morale penalty** on department colleagues whenever they work together.

---

## How to Run

Ensure Ollama is running locally with `llama3.2:3b`:
```bash
ollama run llama3.2:3b
```

Run the simulation for any number of days $N$:
```bash
# Run for 7 simulation days
python main.py run 7

# Run for 15 simulation days
python main.py run 15

# Shorthand syntax
python main.py 30
```

### Key Diagnostic & Analysis Scripts
* `python generate_highlights.py`: Generates a curated highlight reel of historical milestones in `output/highlights.md`.
* `python parse_latest_run.py`: Analyzes recent decisions, fallback counts, and tolerance parser rescue metrics.
* `output/llm_failures.log`: Live audit log of LLM parser recoveries, timeouts, and fallback events.

---

## Current Simulation State (v1 Snapshot)

* **Current Day**: **Day 1031**
* **Company Budget**: **$213,134**
* **Company Reputation**: **99 / 100**
* **Workplace Morale**: **97 / 100**
* **Current Market Mood**: **Boom**
* **Active Relationship Status**:
  * Strong friendships established across departments (Sam & Priya, Alex & Jordan, Priya & Riya, etc.).
  * Rivalry mechanic active in Support: **Alex & Vikram (Affinity 27/100)** with confirmed department morale drag.
