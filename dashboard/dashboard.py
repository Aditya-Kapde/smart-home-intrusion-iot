"""
dashboard.py - ShieldHome Dashboard Server
==========================================
Runs a Flask server that:
  1. Serves the professional HTML dashboard at http://localhost:8050
  2. Exposes dashboard API endpoints that read from events.json in real time
  3. Proxies auth/detect calls to the backend Flask API on port 5000

Run:
    python dashboard.py
"""

import os
import sys
import json
import time
import threading
import webbrowser
from datetime import datetime, timedelta
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS

# Fix Windows console encoding so ASCII art prints correctly
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
EVENTS_FILE = os.path.join(BASE_DIR, "..", "backend", "events.json")
BACKEND_URL = "http://localhost:5000"
DASHBOARD_PORT = 8050

# ── Flask App ──────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=BASE_DIR)
CORS(app)  # allow cross-origin requests from the HTML

# ── Helper: read events.json safely ───────────────────────────────────────
def load_events():
    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def format_event_for_dashboard(ev, idx=0):
    """Convert a raw events.json record into dashboard log format."""
    ts = ev.get("timestamp", "")
    # Parse timestamp → HH:MM:SS display
    try:
        dt = datetime.fromisoformat(str(ts))
        ts_display = dt.strftime("%H:%M:%S")
    except Exception:
        ts_display = str(ts)[:8] if len(str(ts)) >= 8 else str(ts)

    intrusion = ev.get("intrusion", False)
    message   = ev.get("message", "")
    distance  = ev.get("distance", ev.get("dist", "--"))
    source    = ev.get("source", "Python Sim")

    if intrusion:
        ev_type = 0   # Intrusion
    elif "warn" in message.lower() or "approach" in message.lower():
        ev_type = 2   # Warning
    elif "boot" in message.lower() or "start" in message.lower() or "init" in message.lower():
        ev_type = 3   # System
    else:
        ev_type = 1   # Safe

    dist_str = f"{distance} cm" if isinstance(distance, (int, float)) else str(distance)

    return {
        "id":   idx,
        "ts":   ts_display,
        "src":  source,
        "ev":   ev_type,
        "dist": dist_str,
        "note": message,
        "raw_ts": str(ts),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  ROUTES — Static Files
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Serve the main HTML dashboard."""
    return send_from_directory(BASE_DIR, "smart_home_intrusion_full_dashboard.html")


@app.route("/login")
def login_page():
    """Serve the login page."""
    return send_from_directory(BASE_DIR, "login.html")


@app.route("/profile")
def profile_page():
    """Serve the profile page."""
    return send_from_directory(BASE_DIR, "profile.html")


@app.route("/<path:filename>")
def static_files(filename):
    """Serve any other static file from the dashboard directory."""
    return send_from_directory(BASE_DIR, filename)


# ═══════════════════════════════════════════════════════════════════════════
#  ROUTES — Dashboard API
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/dashboard/api/events", methods=["GET"])
def api_events():
    """
    Return all events from events.json formatted for the dashboard.
    Query params:
      ?limit=N   — max events to return (default 200)
      ?type=N    — filter by event type (0=intrusion,1=safe,2=warn,3=system)
    """
    events = load_events()
    limit  = int(request.args.get("limit", 200))
    ev_filter = request.args.get("type", None)

    # Sort newest first
    def sort_key(e):
        try:
            return datetime.fromisoformat(str(e.get("timestamp", "")))
        except Exception:
            return datetime.min

    events.sort(key=sort_key, reverse=True)

    formatted = [format_event_for_dashboard(ev, i) for i, ev in enumerate(events)]

    if ev_filter is not None:
        formatted = [e for e in formatted if e["ev"] == int(ev_filter)]

    return jsonify(formatted[:limit])


@app.route("/dashboard/api/stats", methods=["GET"])
def api_stats():
    """Return KPI statistics computed from events.json."""
    events = load_events()

    total      = len(events)
    intrusions = sum(1 for e in events if e.get("intrusion", False))
    safe_ev    = total - intrusions
    alert_rate = round((intrusions / total * 100), 1) if total > 0 else 0.0

    # Today's events
    today = datetime.now().date()
    today_events = []
    for ev in events:
        try:
            dt = datetime.fromisoformat(str(ev.get("timestamp", "")))
            if dt.date() == today:
                today_events.append(ev)
        except Exception:
            pass

    today_total      = len(today_events)
    today_intrusions = sum(1 for e in today_events if e.get("intrusion", False))

    # Hourly breakdown (last 24h)
    now = datetime.now()
    hourly = [0] * 24
    for ev in events:
        try:
            dt = datetime.fromisoformat(str(ev.get("timestamp", "")))
            if (now - dt).total_seconds() <= 86400:
                hourly[dt.hour] += 1
        except Exception:
            pass

    # 7-day trend
    weekly = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_intr = 0
        day_safe = 0
        for ev in events:
            try:
                dt = datetime.fromisoformat(str(ev.get("timestamp", "")))
                if dt.date() == day:
                    if ev.get("intrusion", False):
                        day_intr += 1
                    else:
                        day_safe += 1
            except Exception:
                pass
        weekly.append({"day": day.strftime("%a"), "intrusions": day_intr, "safe": day_safe})

    return jsonify({
        "total":           total,
        "intrusions":      intrusions,
        "safe":            safe_ev,
        "alert_rate":      alert_rate,
        "today_total":     today_total,
        "today_intrusions":today_intrusions,
        "hourly":          hourly,
        "weekly":          weekly,
        "events_file":     EVENTS_FILE,
        "last_updated":    datetime.now().isoformat(),
    })


@app.route("/dashboard/api/sensors/latest", methods=["GET"])
def api_sensors_latest():
    """Return the most recent sensor reading from events.json."""
    events = load_events()
    if not events:
        return jsonify({
            "pir": "LOW", "distance": "--", "ldr": "--",
            "touch": "Idle", "intrusion": False,
            "message": "No events yet", "timestamp": None
        })

    # Sort by timestamp and return latest
    def sort_key(e):
        try:
            return datetime.fromisoformat(str(e.get("timestamp", "")))
        except Exception:
            return datetime.min

    latest = sorted(events, key=sort_key, reverse=True)[0]
    return jsonify({
        "pir":       latest.get("pir", "LOW"),
        "distance":  latest.get("distance", "--"),
        "ldr":       latest.get("ldr", "--"),
        "touch":     latest.get("touch", "Idle"),
        "intrusion": latest.get("intrusion", False),
        "message":   latest.get("message", ""),
        "timestamp": latest.get("timestamp", ""),
    })


@app.route("/dashboard/api/health", methods=["GET"])
def api_health():
    """Health check — also checks if backend is reachable."""
    import urllib.request
    backend_ok = False
    try:
        urllib.request.urlopen(f"{BACKEND_URL}/", timeout=2)
        backend_ok = True
    except Exception:
        # backend may not have a GET / but might still be running
        try:
            urllib.request.urlopen(f"{BACKEND_URL}/detect", timeout=2)
        except Exception:
            # Even a 405 Method Not Allowed means the server is up
            backend_ok = True

    events_readable = os.path.isfile(EVENTS_FILE)

    return jsonify({
        "dashboard": "ok",
        "backend_flask": "ok" if backend_ok else "unreachable",
        "events_file":   "ok" if events_readable else "missing",
        "events_path":   EVENTS_FILE,
        "timestamp":     datetime.now().isoformat(),
    })


# ═══════════════════════════════════════════════════════════════════════════
#  PROXY — Forward calls to the backend (port 5000)
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/proxy/login", methods=["POST"])
def proxy_login():
    import urllib.request, urllib.error
    try:
        payload = json.dumps(request.json).encode()
        req = urllib.request.Request(
            f"{BACKEND_URL}/login",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return jsonify(json.loads(resp.read())), resp.status
    except urllib.error.HTTPError as e:
        body = {"status": "fail"}
        try:
            body = json.loads(e.read())
        except Exception:
            pass
        return jsonify(body), e.code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 503


@app.route("/proxy/verify-otp", methods=["POST"])
def proxy_verify_otp():
    import urllib.request, urllib.error
    try:
        payload = json.dumps(request.json).encode()
        req = urllib.request.Request(
            f"{BACKEND_URL}/verify-otp",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return jsonify(json.loads(resp.read())), resp.status
    except urllib.error.HTTPError as e:
        body = {"status": "fail"}
        try:
            body = json.loads(e.read())
        except Exception:
            pass
        return jsonify(body), e.code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 503


@app.route("/proxy/register", methods=["POST"])
def proxy_register():
    """Step 1 of registration: send verification OTP to the given email."""
    import urllib.request, urllib.error
    try:
        payload = json.dumps(request.json).encode()
        req = urllib.request.Request(
            f"{BACKEND_URL}/register",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return jsonify(json.loads(resp.read())), resp.status
    except urllib.error.HTTPError as e:
        body = {"status": "fail"}
        try:
            body = json.loads(e.read())
        except Exception:
            pass
        return jsonify(body), e.code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 503


@app.route("/proxy/verify-register-otp", methods=["POST"])
def proxy_verify_register_otp():
    """Step 2 of registration: verify email OTP and create account in MongoDB."""
    import urllib.request, urllib.error
    try:
        payload = json.dumps(request.json).encode()
        req = urllib.request.Request(
            f"{BACKEND_URL}/verify-register-otp",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return jsonify(json.loads(resp.read())), resp.status
    except urllib.error.HTTPError as e:
        body = {"status": "fail"}
        try:
            body = json.loads(e.read())
        except Exception:
            pass
        return jsonify(body), e.code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 503


@app.route("/proxy/detect", methods=["POST"])
def proxy_detect():
    import urllib.request, urllib.error
    try:
        payload = json.dumps(request.json).encode()
        req = urllib.request.Request(
            f"{BACKEND_URL}/detect",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return jsonify(json.loads(resp.read())), resp.status
    except urllib.error.HTTPError as e:
        body = {}
        try:
            body = json.loads(e.read())
        except Exception:
            pass
        return jsonify(body), e.code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 503


@app.route("/proxy/profile", methods=["POST"])
def proxy_profile():
    """Fetch user profile (email, display_name, role, last_login, login_count) from backend."""
    import urllib.request, urllib.error
    try:
        payload = json.dumps(request.json).encode()
        req = urllib.request.Request(
            f"{BACKEND_URL}/profile",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return jsonify(json.loads(resp.read())), resp.status
    except urllib.error.HTTPError as e:
        body = {"status": "fail"}
        try:
            body = json.loads(e.read())
        except Exception:
            pass
        return jsonify(body), e.code
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 503


# ═══════════════════════════════════════════════════════════════════════════
#  STARTUP
# ═══════════════════════════════════════════════════════════════════════════

def open_browser():
    """Open the browser after a short delay."""
    time.sleep(1.5)
    url = f"http://localhost:{DASHBOARD_PORT}"
    print(f"\n  ✅  Dashboard ready → {url}\n")
    webbrowser.open(url)


def print_banner():
    print("""
+----------------------------------------------------------+
|         ShieldHome - IoT Intrusion Dashboard             |
|                  Aegis Sentinel v2.0                     |
+----------------------------------------------------------+
|                                                          |
|   Dashboard :  http://localhost:8050                     |
|   Events API:  http://localhost:8050/dashboard/api/events|
|   Stats API :  http://localhost:8050/dashboard/api/stats |
|   Health    :  http://localhost:8050/dashboard/api/health|
|                                                          |
|   Backend (Flask):  http://localhost:5000                |
|   Events file  :  ../backend/events.json                 |
|                                                          |
|   Press  Ctrl+C  to stop                                 |
+----------------------------------------------------------+
""")


if __name__ == "__main__":
    print_banner()

    # Check events file
    if os.path.isfile(EVENTS_FILE):
        events = load_events()
        print(f"  📂  events.json found — {len(events)} events loaded")
    else:
        print(f"  ⚠   events.json not found at: {EVENTS_FILE}")
        print(f"      The dashboard will still run with simulated data.")

    # Auto-open browser in background thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Start Flask
    app.run(
        host="0.0.0.0",
        port=DASHBOARD_PORT,
        debug=False,        # keep False so browser only opens once
        use_reloader=False  # keep False to avoid double-start
    )