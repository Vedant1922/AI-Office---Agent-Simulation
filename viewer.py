"""
viewer.py — Agent Town Visual Replay Viewer (v2 — Visual Upgrade)

A separate, read-only visualization tool for Agent Town.
READS:
  - data/agents.json
  - data/daily_actions.jsonl
  - data/daily_world_snapshot.jsonl
NEVER writes to any of these files or modifies engine state.

Visual Features (v2):
  - Grid-based tile rendering for floors and walls
  - Procedural furniture (desks, chairs, plants, monitors, whiteboards)
  - Smooth LERP agent movement between day transitions (15 frames)
  - Character sprites with head/body/shadow rendering
  - Particle effects (floating motes, stress sparks)
  - Ambient lighting and zone glow effects
"""

import sys
import os
import json
import math
import random
import pygame

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS & STYLING
# ─────────────────────────────────────────────────────────────────────────────
WIDTH, HEIGHT = 1100, 780
FPS = 60
TILE_SIZE = 32

# Palette — rich, modern office feel
BG_COLOR         = (18, 22, 30)        # Deep navy
FLOOR_BASE       = (42, 50, 66)        # Tile base
FLOOR_ALT        = (38, 46, 60)        # Tile alt (checkerboard)
WALL_COLOR       = (55, 65, 82)        # Wall fill
WALL_BORDER      = (74, 85, 104)       # Wall edge
PANEL_BG         = (28, 35, 50)        # Info panel bg
HEADER_BG        = (14, 18, 28)        # Header
BORDER_COLOR     = (60, 72, 95)
ACCENT_COLOR     = (66, 153, 225)      # Blue
TABLE_COLOR      = (101, 78, 55)       # Wooden table
TABLE_DARK       = (82, 62, 42)        # Table edge
DESK_COLOR       = (85, 95, 115)       # Metal desk
MONITOR_COLOR    = (22, 28, 38)        # Monitor screen
MONITOR_GLOW     = (70, 140, 200)      # Screen glow
PLANT_GREEN      = (56, 142, 80)       # Plant leaves
PLANT_DARK       = (38, 100, 56)       # Plant leaves shade
POT_COLOR        = (150, 110, 75)      # Plant pot
CHAIR_COLOR      = (55, 62, 78)        # Office chair
WHITEBOARD_BG    = (220, 225, 235)     # Whiteboard surface
WHITEBOARD_FRAME = (140, 148, 160)     # Frame
COFFEE_MACHINE   = (70, 60, 55)        # Machine body
TEXT_WHITE       = (237, 242, 247)
TEXT_MUTED       = (140, 155, 175)
TEXT_GOLD        = (240, 200, 70)
TEXT_GREEN       = (72, 195, 120)
TEXT_RED          = (235, 75, 75)
SHADOW_COLOR     = (10, 12, 18, 100)

AGENT_COLORS = {
    "1": (80, 165, 235),    # Sam: Sky Blue
    "2": (72, 200, 120),    # Priya: Emerald
    "3": (165, 130, 240),   # Alex: Lavender
    "4": (245, 155, 60),    # Jordan: Amber
    "5": (240, 105, 175),   # Riya: Rose
    "6": (235, 80, 80),     # Vikram: Crimson
}

AGENT_SKIN_TONES = {
    "1": (225, 190, 160),
    "2": (195, 150, 115),
    "3": (230, 200, 175),
    "4": (180, 135, 100),
    "5": (210, 170, 135),
    "6": (185, 140, 105),
}

AGENT_RADIUS = 18

# Department zone rects (adjusted for wider window)
ZONES = {
    "Engineering":  pygame.Rect(30,  85, 290, 225),
    "Sales":        pygame.Rect(340, 85, 290, 225),
    "Support":      pygame.Rect(30,  330, 290, 225),
    "Marketing":    pygame.Rect(340, 330, 290, 225),
    "Meeting Room": pygame.Rect(650, 85, 420, 225),
    "Break Room":   pygame.Rect(650, 330, 420, 225),
}

ZONE_ACCENT_COLORS = {
    "Engineering":  (60, 130, 200, 25),
    "Sales":        (60, 180, 100, 25),
    "Support":      (180, 120, 230, 25),
    "Marketing":    (230, 140, 60, 25),
    "Meeting Room": (100, 160, 200, 25),
    "Break Room":   (180, 160, 100, 25),
}

ZONE_ICONS = {
    "Engineering":  "⚙",
    "Sales":        "📊",
    "Support":      "🎧",
    "Marketing":    "📣",
    "Meeting Room": "🏛",
    "Break Room":   "☕",
}

LERP_FRAMES = 15  # frames for smooth movement transitions


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING (READ-ONLY)
# ─────────────────────────────────────────────────────────────────────────────
def load_replay_data(base_dir: str):
    """
    Read-only loading of agents and timeline from data files.
    Returns:
      agents_dict: {agent_id: agent_data}
      timeline: {day: {"snapshot": dict, "actions": {agent_id: dict}}}
      days: sorted list of days
    """
    data_dir = os.path.join(base_dir, "data")
    agents_path = os.path.join(data_dir, "agents.json")
    actions_path = os.path.join(data_dir, "daily_actions.jsonl")
    snapshot_path = os.path.join(data_dir, "daily_world_snapshot.jsonl")

    # 1. Load agents
    with open(agents_path, "r", encoding="utf-8") as f:
        agents_list = json.load(f)
    agents_dict = {str(a["id"]): a for a in agents_list}

    # 2. Load snapshots
    timeline = {}
    if os.path.exists(snapshot_path):
        with open(snapshot_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    day = rec["day"]
                    timeline.setdefault(day, {})["snapshot"] = rec

    # 3. Load daily actions
    if os.path.exists(actions_path):
        with open(actions_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line)
                    day = rec["day"]
                    timeline.setdefault(day, {}).setdefault("actions", {})[str(rec["agent_id"])] = rec

    days = sorted(list(timeline.keys()))
    return agents_dict, timeline, days


# ─────────────────────────────────────────────────────────────────────────────
# POSITIONING LOGIC
# ─────────────────────────────────────────────────────────────────────────────
def compute_agent_positions(day_data: dict, agents_dict: dict) -> dict:
    """
    Calculates (x, y) coordinates and display status for each agent for the given day.
    Returns: {agent_id: {"x": float, "y": float, "action": str, "is_stress": bool, ...}}
    """
    positions = {}
    actions = day_data.get("actions", {})

    # Group agents by target zone
    break_room_agents = []
    meeting_agents = []
    dept_agents = {"Engineering": [], "Sales": [], "Support": [], "Marketing": []}
    stress_agents = []

    for aid, a_info in agents_dict.items():
        act_rec = actions.get(aid, {})
        action = act_rec.get("action", "work").lower()

        if action == "eat":
            break_room_agents.append(aid)
        elif action == "meeting":
            meeting_agents.append(aid)
        elif action in ("stress-day", "burnout-rest"):
            stress_agents.append(aid)
        else:
            dept = a_info.get("department", "Engineering")
            dept_agents.setdefault(dept, []).append(aid)

    # 1. Place Break Room agents
    br_rect = ZONES["Break Room"]
    for i, aid in enumerate(break_room_agents):
        col = i % 3
        row = i // 3
        x = br_rect.left + 80 + col * 120
        y = br_rect.top + 90 + row * 80
        positions[aid] = {
            "x": x, "y": y, "zone": "Break Room",
            "action": actions.get(aid, {}).get("action", "eat"),
            "is_stress": False
        }

    # 2. Place Meeting Room agents (around conference table)
    mr_rect = ZONES["Meeting Room"]
    table_center_x = mr_rect.centerx
    table_center_y = mr_rect.centery + 10
    total_meet = len(meeting_agents)
    for i, aid in enumerate(meeting_agents):
        angle = (2 * math.pi / max(1, total_meet)) * i - math.pi / 2
        x = table_center_x + math.cos(angle) * 120
        y = table_center_y + math.sin(angle) * 65
        positions[aid] = {
            "x": x, "y": y, "zone": "Meeting Room",
            "action": "meeting",
            "is_stress": False
        }

    # 3. Place Department agents
    for dept, aids in dept_agents.items():
        d_rect = ZONES.get(dept, ZONES["Engineering"])
        for idx, aid in enumerate(aids):
            if len(aids) == 1:
                x = d_rect.centerx
                y = d_rect.centery + 20
            else:
                spacing = 110
                offset = (idx - (len(aids) - 1) / 2) * spacing
                x = d_rect.centerx + offset
                y = d_rect.centery + 20
            positions[aid] = {
                "x": x, "y": y, "zone": dept,
                "action": actions.get(aid, {}).get("action", "work"),
                "is_stress": False
            }

    # 4. Place Stress-Day agents
    for aid in stress_agents:
        dept = agents_dict[aid].get("department", "Engineering")
        d_rect = ZONES.get(dept, ZONES["Engineering"])
        x = d_rect.right - 50
        y = d_rect.top + 50
        positions[aid] = {
            "x": x, "y": y, "zone": dept,
            "action": actions.get(aid, {}).get("action", "stress-day"),
            "is_stress": True
        }

    return positions


# ─────────────────────────────────────────────────────────────────────────────
# PROCEDURAL RENDERING HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def draw_tiled_floor(surface, rect, base_col, alt_col):
    """Draw a checkerboard tile pattern inside a rect."""
    for tx in range(rect.left, rect.right, TILE_SIZE):
        for ty in range(rect.top, rect.bottom, TILE_SIZE):
            tile_rect = pygame.Rect(tx, ty, TILE_SIZE, TILE_SIZE)
            tile_rect = tile_rect.clip(rect)
            is_alt = ((tx - rect.left) // TILE_SIZE + (ty - rect.top) // TILE_SIZE) % 2
            col = alt_col if is_alt else base_col
            pygame.draw.rect(surface, col, tile_rect)


def draw_desk(surface, x, y, facing_right=True):
    """Draw a small office desk with monitor."""
    # Desk surface
    desk_rect = pygame.Rect(x, y, 48, 28)
    pygame.draw.rect(surface, DESK_COLOR, desk_rect, border_radius=3)
    pygame.draw.rect(surface, BORDER_COLOR, desk_rect, width=1, border_radius=3)
    # Monitor
    mx = x + 8 if facing_right else x + 22
    mon_rect = pygame.Rect(mx, y - 14, 20, 14)
    pygame.draw.rect(surface, MONITOR_COLOR, mon_rect, border_radius=2)
    pygame.draw.rect(surface, MONITOR_GLOW, mon_rect, width=1, border_radius=2)
    # Screen glow dot
    pygame.draw.circle(surface, MONITOR_GLOW, (mx + 10, y - 7), 2)


def draw_chair(surface, x, y):
    """Draw a small office chair."""
    pygame.draw.circle(surface, CHAIR_COLOR, (x, y), 10)
    pygame.draw.circle(surface, BORDER_COLOR, (x, y), 10, width=1)
    # Backrest
    pygame.draw.arc(surface, BORDER_COLOR, pygame.Rect(x - 10, y - 14, 20, 16), 0.3, 2.8, 2)


def draw_plant(surface, x, y):
    """Draw a decorative potted plant."""
    # Pot
    pot_pts = [(x - 8, y), (x + 8, y), (x + 6, y + 14), (x - 6, y + 14)]
    pygame.draw.polygon(surface, POT_COLOR, pot_pts)
    pygame.draw.polygon(surface, TABLE_DARK, pot_pts, width=1)
    # Leaves
    for angle_off in [-40, -10, 20, 45]:
        rad = math.radians(angle_off - 90)
        lx = x + math.cos(rad) * 14
        ly = y - abs(math.sin(rad)) * 18 - 4
        col = PLANT_GREEN if angle_off % 2 == 0 else PLANT_DARK
        pygame.draw.circle(surface, col, (int(lx), int(ly)), 7)


def draw_whiteboard(surface, x, y, w=70, h=40):
    """Draw a wall-mounted whiteboard."""
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surface, WHITEBOARD_BG, rect, border_radius=3)
    pygame.draw.rect(surface, WHITEBOARD_FRAME, rect, width=2, border_radius=3)
    # Scribble lines
    for i in range(3):
        ly = y + 10 + i * 10
        lw = w - 20 - i * 8
        pygame.draw.line(surface, TEXT_MUTED, (x + 10, ly), (x + 10 + lw, ly), 1)


def draw_coffee_machine(surface, x, y):
    """Draw a coffee machine."""
    body = pygame.Rect(x, y, 24, 30)
    pygame.draw.rect(surface, COFFEE_MACHINE, body, border_radius=4)
    pygame.draw.rect(surface, BORDER_COLOR, body, width=1, border_radius=4)
    # Drip area
    pygame.draw.rect(surface, (40, 35, 30), pygame.Rect(x + 6, y + 18, 12, 10), border_radius=2)
    # Light
    pygame.draw.circle(surface, TEXT_GREEN, (x + 12, y + 6), 3)


def draw_conference_table(surface, rect):
    """Draw an oval conference table."""
    # Shadow
    shadow_rect = rect.move(3, 3)
    pygame.draw.ellipse(surface, (20, 24, 32), shadow_rect)
    # Table
    pygame.draw.ellipse(surface, TABLE_COLOR, rect)
    pygame.draw.ellipse(surface, TABLE_DARK, rect, width=2)
    # Center highlight
    inner = rect.inflate(-30, -16)
    pygame.draw.ellipse(surface, (120, 95, 70), inner, width=1)


def draw_dining_table(surface, x, y, w=50, h=30):
    """Draw a small dining / café table."""
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surface, TABLE_COLOR, rect, border_radius=6)
    pygame.draw.rect(surface, TABLE_DARK, rect, width=1, border_radius=6)


# ─────────────────────────────────────────────────────────────────────────────
# AGENT SPRITE RENDERING
# ─────────────────────────────────────────────────────────────────────────────
def draw_agent_sprite(surface, cx, cy, agent_id, name, is_selected, is_stress,
                      action_name, font_sub, font_init, tick):
    """Draw a character sprite with head, body, shadow, and labels."""
    color = AGENT_COLORS.get(agent_id, ACCENT_COLOR)
    skin = AGENT_SKIN_TONES.get(agent_id, (210, 180, 150))

    # Shadow (ellipse under feet)
    shadow_surf = pygame.Surface((36, 12), pygame.SRCALPHA)
    pygame.draw.ellipse(shadow_surf, (0, 0, 0, 60), (0, 0, 36, 12))
    surface.blit(shadow_surf, (cx - 18, cy + 14))

    # Selection glow ring
    if is_selected:
        glow_r = AGENT_RADIUS + 8
        glow_surf = pygame.Surface((glow_r * 2 + 4, glow_r * 2 + 4), pygame.SRCALPHA)
        pulse = abs(math.sin(tick * 0.05)) * 0.4 + 0.6
        glow_alpha = int(180 * pulse)
        glow_col = (TEXT_GOLD[0], TEXT_GOLD[1], TEXT_GOLD[2], glow_alpha)
        pygame.draw.circle(glow_surf, glow_col, (glow_r + 2, glow_r + 2), glow_r, width=3)
        surface.blit(glow_surf, (cx - glow_r - 2, cy - glow_r - 2))

    # Stress aura (red pulsing ring)
    if is_stress:
        pulse = abs(math.sin(tick * 0.08)) * 0.5 + 0.5
        stress_alpha = int(200 * pulse)
        stress_surf = pygame.Surface((60, 60), pygame.SRCALPHA)
        stress_col = (235, 70, 70, stress_alpha)
        pygame.draw.circle(stress_surf, stress_col, (30, 30), 26, width=3)
        surface.blit(stress_surf, (cx - 30, cy - 30))

    # Body (rounded rectangle)
    body_rect = pygame.Rect(cx - 10, cy - 6, 20, 22)
    pygame.draw.rect(surface, color, body_rect, border_radius=5)
    # Body highlight
    highlight_rect = pygame.Rect(cx - 7, cy - 4, 6, 14)
    highlight_col = tuple(min(255, c + 40) for c in color)
    pygame.draw.rect(surface, highlight_col, highlight_rect, border_radius=3)

    # Head (circle)
    head_y = cy - 14
    pygame.draw.circle(surface, skin, (cx, head_y), 10)
    # Hair (arc on top)
    hair_col = tuple(max(0, c - 60) for c in color)
    pygame.draw.arc(surface, hair_col, pygame.Rect(cx - 10, head_y - 12, 20, 16), 0.3, 2.84, 3)

    # Eyes (two small dots)
    pygame.draw.circle(surface, (30, 30, 40), (cx - 3, head_y - 1), 2)
    pygame.draw.circle(surface, (30, 30, 40), (cx + 3, head_y - 1), 2)

    # Name tag
    name_surf = font_sub.render(name, True, TEXT_WHITE)
    # Background pill for name
    name_bg = pygame.Surface((name_surf.get_width() + 10, name_surf.get_height() + 4), pygame.SRCALPHA)
    pygame.draw.rect(name_bg, (0, 0, 0, 120), name_bg.get_rect(), border_radius=4)
    surface.blit(name_bg, (cx - name_surf.get_width() // 2 - 5, cy + 28))
    surface.blit(name_surf, (cx - name_surf.get_width() // 2, cy + 30))

    # Action pill
    act_upper = str(action_name).upper()
    if act_upper in ("REST", "EAT"):
        act_col = TEXT_GOLD
    elif act_upper in ("STRESS-DAY", "BURNOUT-REST"):
        act_col = TEXT_RED
    elif act_upper == "MEETING":
        act_col = TEXT_GREEN
    else:
        act_col = TEXT_MUTED
    act_surf = font_sub.render(act_upper, True, act_col)
    surface.blit(act_surf, (cx - act_surf.get_width() // 2, cy + 44))

    # Stress label
    if is_stress:
        stress_tag = font_sub.render("⚠ STRESSED", True, TEXT_RED)
        surface.blit(stress_tag, (cx - stress_tag.get_width() // 2, cy - 36))


# ─────────────────────────────────────────────────────────────────────────────
# PARTICLE SYSTEM (ambient floating motes)
# ─────────────────────────────────────────────────────────────────────────────
class Particle:
    def __init__(self, bounds):
        self.bounds = bounds
        self.reset()

    def reset(self):
        self.x = random.uniform(self.bounds.left, self.bounds.right)
        self.y = random.uniform(self.bounds.top, self.bounds.bottom)
        self.vx = random.uniform(-0.15, 0.15)
        self.vy = random.uniform(-0.3, -0.08)
        self.life = random.uniform(60, 180)
        self.max_life = self.life
        self.size = random.uniform(1.5, 3.0)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        if self.life <= 0 or not self.bounds.collidepoint(self.x, self.y):
            self.reset()

    def draw(self, surface):
        alpha = int(60 * (self.life / self.max_life))
        s = max(1, int(self.size * (self.life / self.max_life)))
        dot_surf = pygame.Surface((s * 2 + 2, s * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(dot_surf, (180, 200, 230, alpha), (s + 1, s + 1), s)
        surface.blit(dot_surf, (int(self.x) - s - 1, int(self.y) - s - 1))


# ─────────────────────────────────────────────────────────────────────────────
# LERP HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def lerp(a, b, t):
    """Linear interpolation between a and b by factor t in [0, 1]."""
    return a + (b - a) * t


def ease_in_out(t):
    """Smooth ease-in-out curve."""
    if t < 0.5:
        return 2.0 * t * t
    return -1.0 + (4.0 - 2.0 * t) * t


# ─────────────────────────────────────────────────────────────────────────────
# ROOM DECORATION RENDERING
# ─────────────────────────────────────────────────────────────────────────────
def draw_room_decorations(surface, zone_name, rect):
    """Draw furniture and props inside a zone."""
    if zone_name == "Engineering":
        # Desks
        draw_desk(surface, rect.left + 30, rect.top + 60)
        draw_desk(surface, rect.left + 30, rect.top + 130, facing_right=False)
        draw_desk(surface, rect.right - 85, rect.top + 60)
        # Whiteboard
        draw_whiteboard(surface, rect.left + 15, rect.top + 35, 55, 20)
        # Plant in corner
        draw_plant(surface, rect.right - 25, rect.bottom - 30)

    elif zone_name == "Sales":
        draw_desk(surface, rect.left + 35, rect.top + 65)
        draw_desk(surface, rect.right - 90, rect.top + 65, facing_right=False)
        draw_desk(surface, rect.centerx - 24, rect.top + 140)
        draw_whiteboard(surface, rect.right - 80, rect.top + 35, 60, 22)
        draw_plant(surface, rect.left + 20, rect.bottom - 30)

    elif zone_name == "Support":
        draw_desk(surface, rect.left + 30, rect.top + 65)
        draw_desk(surface, rect.right - 85, rect.top + 65)
        draw_desk(surface, rect.left + 30, rect.top + 140, facing_right=False)
        draw_plant(surface, rect.right - 25, rect.top + 45)
        draw_whiteboard(surface, rect.left + 15, rect.top + 35, 50, 20)

    elif zone_name == "Marketing":
        draw_desk(surface, rect.left + 35, rect.top + 70)
        draw_desk(surface, rect.right - 90, rect.top + 70, facing_right=False)
        draw_whiteboard(surface, rect.centerx - 35, rect.top + 35, 70, 24)
        draw_plant(surface, rect.left + 20, rect.bottom - 30)
        draw_plant(surface, rect.right - 25, rect.bottom - 30)

    elif zone_name == "Meeting Room":
        # Large conference table
        tbl_rect = pygame.Rect(rect.centerx - 100, rect.centery - 25, 200, 75)
        draw_conference_table(surface, tbl_rect)
        # Whiteboard on wall
        draw_whiteboard(surface, rect.left + 20, rect.top + 35, 80, 28)
        # Plants in corners
        draw_plant(surface, rect.right - 25, rect.top + 50)
        draw_plant(surface, rect.right - 25, rect.bottom - 30)

    elif zone_name == "Break Room":
        # Dining tables
        draw_dining_table(surface, rect.left + 50, rect.top + 60, 55, 35)
        draw_dining_table(surface, rect.left + 160, rect.top + 60, 55, 35)
        draw_dining_table(surface, rect.left + 270, rect.top + 60, 55, 35)
        # Coffee machine
        draw_coffee_machine(surface, rect.left + 30, rect.bottom - 55)
        draw_coffee_machine(surface, rect.left + 60, rect.bottom - 55)
        # Counter
        counter_rect = pygame.Rect(rect.left + 90, rect.bottom - 50, rect.width - 120, 25)
        pygame.draw.rect(surface, DESK_COLOR, counter_rect, border_radius=4)
        pygame.draw.rect(surface, BORDER_COLOR, counter_rect, width=1, border_radius=4)
        # Plant
        draw_plant(surface, rect.right - 25, rect.top + 50)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN VIEWER APPLICATION
# ─────────────────────────────────────────────────────────────────────────────
def run_viewer(headless_test: bool = False):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    agents_dict, timeline, days = load_replay_data(base_dir)

    if not days:
        print("Error: No simulation days found in data/daily_actions.jsonl or data/daily_world_snapshot.jsonl!")
        return False

    if headless_test:
        os.environ["SDL_VIDEODRIVER"] = "dummy"

    pygame.init()
    pygame.font.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Agent Town — Visual Replay Viewer v2")
    clock = pygame.time.Clock()

    # Fonts
    font_title = pygame.font.SysFont("Arial", 18, bold=True)
    font_bold  = pygame.font.SysFont("Arial", 14, bold=True)
    font_sub   = pygame.font.SysFont("Arial", 12)
    font_init  = pygame.font.SysFont("Arial", 14, bold=True)
    font_big   = pygame.font.SysFont("Arial", 22, bold=True)

    # State
    day_index = 0
    is_playing = False
    step_timer = 0.0
    playback_speed = 1.0
    selected_agent_id = "1"
    tick = 0

    # LERP state
    lerp_progress = 1.0  # 1.0 = fully arrived at current day
    prev_positions = {}
    curr_positions = {}

    # Particles
    particles = []
    for zone_name, rect in ZONES.items():
        for _ in range(6):
            particles.append(Particle(rect))

    # Pre-render the static background (tiles + walls + furniture) onto a cached surface
    bg_cache = pygame.Surface((WIDTH, HEIGHT))
    bg_cache.fill(BG_COLOR)

    for zone_name, rect in ZONES.items():
        # Floor tiles
        draw_tiled_floor(bg_cache, rect, FLOOR_BASE, FLOOR_ALT)

        # Wall border (thick at top to simulate wall)
        wall_top = pygame.Rect(rect.left, rect.top, rect.width, 8)
        pygame.draw.rect(bg_cache, WALL_COLOR, wall_top)
        # Side walls
        pygame.draw.rect(bg_cache, WALL_COLOR, pygame.Rect(rect.left, rect.top, 6, rect.height))
        pygame.draw.rect(bg_cache, WALL_COLOR, pygame.Rect(rect.right - 6, rect.top, 6, rect.height))
        # Bottom edge
        pygame.draw.rect(bg_cache, WALL_COLOR, pygame.Rect(rect.left, rect.bottom - 4, rect.width, 4))

        # Room border
        pygame.draw.rect(bg_cache, WALL_BORDER, rect, width=2, border_radius=3)

        # Zone label
        z_surf = font_bold.render(f" {zone_name.upper()} ", True, TEXT_WHITE)
        label_bg = pygame.Surface((z_surf.get_width() + 8, z_surf.get_height() + 4), pygame.SRCALPHA)
        pygame.draw.rect(label_bg, (WALL_COLOR[0], WALL_COLOR[1], WALL_COLOR[2], 200),
                         label_bg.get_rect(), border_radius=3)
        bg_cache.blit(label_bg, (rect.left + 10, rect.top + 10))
        bg_cache.blit(z_surf, (rect.left + 14, rect.top + 12))

        # Furniture
        draw_room_decorations(bg_cache, zone_name, rect)

    # Compute initial positions
    first_day_data = timeline.get(days[0], {})
    curr_positions = compute_agent_positions(first_day_data, agents_dict)
    prev_positions = dict(curr_positions)  # same as current initially

    # ── Headless Test Mode ────────────────────────────────────────────────────
    if headless_test:
        print(f"Running automated headless test across {len(days)} days: {days}")
        for idx in range(len(days)):
            curr_day = days[idx]
            day_data = timeline[curr_day]
            pos_map = compute_agent_positions(day_data, agents_dict)
            assert len(pos_map) == 6, f"Day {curr_day} does not have all 6 agent positions!"

            for aid, p in pos_map.items():
                act = day_data.get("actions", {}).get(aid, {})
                action_name = act.get("action", "").lower()
                if action_name == "eat":
                    assert p["zone"] == "Break Room", f"Day {curr_day} agent {aid} ({action_name}) not in Break Room!"
                elif action_name == "meeting":
                    assert p["zone"] == "Meeting Room", f"Day {curr_day} agent {aid} ({action_name}) not in Meeting Room!"
                elif action_name in ("work", "rest", "stress-day", "burnout-rest"):
                    expected_dept = agents_dict[aid].get("department")
                    assert p["zone"] == expected_dept, f"Day {curr_day} agent {aid} ({action_name}) not in {expected_dept}!"

            # Verify reasoning accessible
            for aid in agents_dict:
                act = day_data.get("actions", {}).get(aid, {})
                _ = act.get("reasoning")
        print("Headless verification logic passed 100%!")
        pygame.quit()
        return True

    # ── Main Loop ─────────────────────────────────────────────────────────────
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        tick += 1

        current_day = days[day_index]
        day_data = timeline.get(current_day, {})
        snapshot = day_data.get("snapshot", {})
        actions  = day_data.get("actions", {})

        # ── Handle Events ────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    is_playing = not is_playing
                elif event.key == pygame.K_LEFT:
                    if day_index > 0:
                        prev_positions = dict(curr_positions)
                        day_index -= 1
                        new_day_data = timeline.get(days[day_index], {})
                        curr_positions = compute_agent_positions(new_day_data, agents_dict)
                        lerp_progress = 0.0
                    is_playing = False
                elif event.key == pygame.K_RIGHT:
                    if day_index < len(days) - 1:
                        prev_positions = dict(curr_positions)
                        day_index += 1
                        new_day_data = timeline.get(days[day_index], {})
                        curr_positions = compute_agent_positions(new_day_data, agents_dict)
                        lerp_progress = 0.0
                    is_playing = False
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    playback_speed = max(0.25, playback_speed - 0.25)
                elif event.key in (pygame.K_MINUS, pygame.K_UNDERSCORE, pygame.K_KP_MINUS):
                    playback_speed = min(3.0, playback_speed + 0.25)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                # Check agent click in current interpolated positions
                for aid in agents_dict:
                    p_curr = curr_positions.get(aid)
                    p_prev = prev_positions.get(aid)
                    if p_curr:
                        if lerp_progress >= 1.0 or not p_prev:
                            ax, ay = p_curr["x"], p_curr["y"]
                        else:
                            t = ease_in_out(min(1.0, lerp_progress))
                            ax = lerp(p_prev["x"], p_curr["x"], t)
                            ay = lerp(p_prev["y"], p_curr["y"], t)
                        dist = math.hypot(mx - ax, my - ay)
                        if dist <= AGENT_RADIUS + 10:
                            selected_agent_id = aid
                            break

        # ── Auto-play ────────────────────────────────────────────────────────
        if is_playing and lerp_progress >= 1.0:
            step_timer += dt
            if step_timer >= playback_speed:
                step_timer = 0.0
                if day_index < len(days) - 1:
                    prev_positions = dict(curr_positions)
                    day_index += 1
                    new_day_data = timeline.get(days[day_index], {})
                    curr_positions = compute_agent_positions(new_day_data, agents_dict)
                    lerp_progress = 0.0
                    current_day = days[day_index]
                    day_data = timeline.get(current_day, {})
                    snapshot = day_data.get("snapshot", {})
                    actions = day_data.get("actions", {})
                else:
                    is_playing = False

        # ── Update LERP ──────────────────────────────────────────────────────
        if lerp_progress < 1.0:
            lerp_progress += 1.0 / LERP_FRAMES
            if lerp_progress > 1.0:
                lerp_progress = 1.0

        # ── Update Particles ─────────────────────────────────────────────────
        for p in particles:
            p.update()

        # ── Render Frame ─────────────────────────────────────────────────────
        # Blit cached background (tiles + walls + furniture)
        screen.blit(bg_cache, (0, 0))

        # Zone accent glow overlay
        for zone_name, rect in ZONES.items():
            accent = ZONE_ACCENT_COLORS.get(zone_name, (100, 100, 100, 20))
            glow_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.rect(glow_surf, accent, glow_surf.get_rect(), border_radius=3)
            screen.blit(glow_surf, rect.topleft)

        # Particles
        for p in particles:
            p.draw(screen)

        # ── Header Bar ────────────────────────────────────────────────────────
        header_rect = pygame.Rect(0, 0, WIDTH, 72)
        pygame.draw.rect(screen, HEADER_BG, header_rect)
        # Gradient line under header
        for i in range(3):
            alpha = 180 - i * 60
            line_surf = pygame.Surface((WIDTH, 1), pygame.SRCALPHA)
            line_surf.fill((ACCENT_COLOR[0], ACCENT_COLOR[1], ACCENT_COLOR[2], alpha))
            screen.blit(line_surf, (0, 72 + i))

        # Day info
        status_str = f"▶ PLAYING ({playback_speed:.1f}s/day)" if is_playing else "⏸ PAUSED"
        status_color = TEXT_GREEN if is_playing else TEXT_GOLD

        day_surf = font_big.render(f"DAY {current_day}", True, TEXT_WHITE)
        screen.blit(day_surf, (30, 12))
        title_surf = font_bold.render("AGENT TOWN — SIMULATION REPLAY", True, TEXT_MUTED)
        screen.blit(title_surf, (30, 42))

        status_surf = font_bold.render(status_str, True, status_color)
        screen.blit(status_surf, (250, 16))

        # Economic bar
        budget = snapshot.get("budget", 0)
        rep = snapshot.get("reputation", 100)
        mood = str(snapshot.get("market_mood", "boom")).upper()

        # Colored metric pills
        metrics_x = 250
        metrics_y = 42

        for label, value, col in [
            ("BUDGET", f"${budget:,}", TEXT_GREEN),
            ("REPUTATION", f"{rep}/100", ACCENT_COLOR),
            ("MARKET", mood, TEXT_GOLD)
        ]:
            lbl_surf = font_sub.render(f"{label}: ", True, TEXT_MUTED)
            val_surf = font_bold.render(value, True, col)
            screen.blit(lbl_surf, (metrics_x, metrics_y))
            metrics_x += lbl_surf.get_width()
            screen.blit(val_surf, (metrics_x, metrics_y - 1))
            metrics_x += val_surf.get_width() + 20

        # Controls legend
        controls_surf = font_sub.render("Space: Play/Pause  |  ← →: Step  |  +/-: Speed  |  Click: Inspect", True, TEXT_MUTED)
        screen.blit(controls_surf, (WIDTH - controls_surf.get_width() - 20, 52))

        # Day progress bar
        if len(days) > 1:
            progress = day_index / (len(days) - 1)
            bar_rect = pygame.Rect(WIDTH - 220, 16, 200, 12)
            pygame.draw.rect(screen, BORDER_COLOR, bar_rect, border_radius=6)
            fill_w = int(bar_rect.width * progress)
            if fill_w > 0:
                fill_rect = pygame.Rect(bar_rect.left, bar_rect.top, fill_w, bar_rect.height)
                pygame.draw.rect(screen, ACCENT_COLOR, fill_rect, border_radius=6)
            day_prog_txt = font_sub.render(f"Day {day_index + 1}/{len(days)}", True, TEXT_WHITE)
            screen.blit(day_prog_txt, (bar_rect.centerx - day_prog_txt.get_width() // 2, bar_rect.bottom + 2))

        # ── Render Agents (with LERP) ─────────────────────────────────────────
        t = ease_in_out(min(1.0, lerp_progress))

        # Sort agents by y for depth ordering
        agent_render_list = []
        for aid in agents_dict:
            p_curr = curr_positions.get(aid)
            p_prev = prev_positions.get(aid)
            if p_curr:
                if lerp_progress >= 1.0 or not p_prev:
                    ax = p_curr["x"]
                    ay = p_curr["y"]
                else:
                    ax = lerp(p_prev["x"], p_curr["x"], t)
                    ay = lerp(p_prev["y"], p_curr["y"], t)
                agent_render_list.append((ay, aid, ax, ay, p_curr))

        # Sort by Y for painter's algorithm (back-to-front)
        agent_render_list.sort(key=lambda item: item[0])

        for _, aid, ax, ay, p_curr in agent_render_list:
            agent_data = agents_dict.get(aid, {})
            name = agent_data.get("name", f"Agent {aid}")
            is_selected = (aid == selected_agent_id)
            is_stress = p_curr.get("is_stress", False)
            action_name = str(p_curr.get("action", "work"))

            draw_agent_sprite(screen, int(ax), int(ay), aid, name,
                              is_selected, is_stress, action_name,
                              font_sub, font_init, tick)

        # ── Bottom Inspector Panel ────────────────────────────────────────────
        info_rect = pygame.Rect(30, HEIGHT - 195, WIDTH - 60, 170)
        # Panel background with subtle gradient
        panel_surf = pygame.Surface((info_rect.width, info_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(panel_surf, (PANEL_BG[0], PANEL_BG[1], PANEL_BG[2], 230),
                         panel_surf.get_rect(), border_radius=10)
        screen.blit(panel_surf, info_rect.topleft)
        pygame.draw.rect(screen, BORDER_COLOR, info_rect, width=2, border_radius=10)

        # Accent line at top of panel
        accent_line = pygame.Surface((info_rect.width - 20, 2), pygame.SRCALPHA)
        accent_line.fill((*ACCENT_COLOR, 120))
        screen.blit(accent_line, (info_rect.left + 10, info_rect.top + 6))

        if selected_agent_id and selected_agent_id in agents_dict:
            sel_agent = agents_dict[selected_agent_id]
            sel_act = actions.get(selected_agent_id, {})
            sel_color = AGENT_COLORS.get(selected_agent_id, ACCENT_COLOR)

            # Agent info header
            dept_str = sel_agent.get("department", "?")
            action_str = str(sel_act.get("action", "work")).upper()

            # Colored dot
            pygame.draw.circle(screen, sel_color, (info_rect.left + 22, info_rect.top + 28), 6)

            header_text = f"{sel_agent['name']}  •  {dept_str}  •  {action_str}"
            header_surf = font_bold.render(header_text, True, sel_color)
            screen.blit(header_surf, (info_rect.left + 36, info_rect.top + 22))

            # Agent stats
            energy = sel_agent.get("energy", "?")
            stress_val = sel_agent.get("stress", "?")
            morale_val = sel_agent.get("morale", "?")
            stats_text = f"Energy: {energy}  |  Stress: {stress_val}  |  Morale: {morale_val}"
            stats_surf = font_sub.render(stats_text, True, TEXT_MUTED)
            screen.blit(stats_surf, (info_rect.left + 36, info_rect.top + 44))

            # Target
            target_id = sel_act.get("target_agent_id")
            if target_id and target_id in agents_dict:
                target_str = f"→ Interacting with: {agents_dict[target_id]['name']}"
                t_surf = font_sub.render(target_str, True, TEXT_GOLD)
                screen.blit(t_surf, (info_rect.right - t_surf.get_width() - 25, info_rect.top + 24))

            # Reasoning box
            reason_box = pygame.Rect(info_rect.left + 16, info_rect.top + 64, info_rect.width - 32, 80)
            pygame.draw.rect(screen, (18, 22, 32), reason_box, border_radius=6)
            pygame.draw.rect(screen, BORDER_COLOR, reason_box, width=1, border_radius=6)

            raw_reason = sel_act.get("reasoning") or "No explicit reasoning logged for this action."

            # Word-wrap reasoning text
            words = raw_reason.split()
            lines = []
            current_line = ""
            max_line_width = reason_box.width - 20
            for word in words:
                test_line = current_line + " " + word if current_line else word
                test_surf = font_sub.render(test_line, True, TEXT_WHITE)
                if test_surf.get_width() <= max_line_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)

            # Render up to 4 lines
            for i, line_text in enumerate(lines[:4]):
                if i == 3 and len(lines) > 4:
                    line_text += "..."
                line_surf = font_sub.render(f'  "{line_text}"' if i == 0 else f'   {line_text}', True, TEXT_WHITE)
                screen.blit(line_surf, (reason_box.left + 8, reason_box.top + 8 + i * 18))

            # Hint
            hint_surf = font_sub.render("Click other agents on the floor to inspect their reasoning", True, TEXT_MUTED)
            screen.blit(hint_surf, (info_rect.left + 20, info_rect.bottom - 22))
        else:
            prompt_surf = font_bold.render("Click on any agent to inspect their daily reasoning.", True, TEXT_MUTED)
            screen.blit(prompt_surf, (info_rect.left + 20, info_rect.top + 60))

        pygame.display.flip()

    pygame.quit()
    return True


if __name__ == "__main__":
    is_test = "--test" in sys.argv
    run_viewer(headless_test=is_test)
