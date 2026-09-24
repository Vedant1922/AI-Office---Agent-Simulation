"""
viewer_web.py — Web-based Pixel Art Viewer Launcher for Agent Town

Reads simulation data (READ-ONLY), starts a local HTTP server,
and opens the pixel-art viewer in your browser.

READS: data/agents.json, data/daily_actions.jsonl, data/daily_world_snapshot.jsonl
NEVER writes to any data file.

Usage:  python viewer_web.py
"""

import http.server
import json
import os
import sys
import webbrowser
import threading

PORT = 8765
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
WEB_DIR = os.path.join(BASE_DIR, "web_viewer")


def load_simulation_data():
    """Read-only loading of all simulation data."""
    agents_path = os.path.join(DATA_DIR, "agents.json")
    actions_path = os.path.join(DATA_DIR, "daily_actions.jsonl")
    snapshot_path = os.path.join(DATA_DIR, "daily_world_snapshot.jsonl")

    with open(agents_path, "r", encoding="utf-8") as f:
        agents = json.load(f)

    actions = []
    if os.path.exists(actions_path):
        with open(actions_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    actions.append(json.loads(line))

    snapshots = []
    if os.path.exists(snapshot_path):
        with open(snapshot_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    snapshots.append(json.loads(line))

    return {"agents": agents, "actions": actions, "snapshots": snapshots}


# Cache the data once at startup
SIM_DATA = None


class ViewerHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        if self.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(json.dumps(SIM_DATA).encode("utf-8"))
        else:
            super().do_GET()

    def log_message(self, format, *args):
        # Suppress noisy HTTP request logs
        pass


def main():
    global SIM_DATA
    print("=" * 55)
    print("  AGENT TOWN — Pixel Art Viewer (Web Edition)")
    print("=" * 55)
    print()
    print("Loading simulation data (read-only)...")
    SIM_DATA = load_simulation_data()
    n_agents = len(SIM_DATA["agents"])
    n_actions = len(SIM_DATA["actions"])
    n_snaps = len(SIM_DATA["snapshots"])
    print(f"  ✓ {n_agents} agents, {n_actions} action records, {n_snaps} world snapshots")
    print()

    server = http.server.HTTPServer(("localhost", PORT), ViewerHandler)
    url = f"http://localhost:{PORT}"
    print(f"  Server running at {url}")
    print(f"  Press Ctrl+C to stop.\n")

    # Open browser after a short delay
    def open_browser():
        import time
        time.sleep(0.8)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
