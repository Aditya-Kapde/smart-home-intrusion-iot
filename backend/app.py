"""
app.py — ShieldHome Backend Entry Point
========================================
Loads environment variables, creates the Flask app,
registers the routes Blueprint, and starts the server.

Run:
    python app.py
"""

import os
from dotenv import load_dotenv
from flask import Flask
from flask_cors import CORS

# Load .env from project root (one level up from backend/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from routes import api_bp  # noqa: E402 — import after env is loaded
from network_monitor import start_network_monitor  # noqa: E402

app = Flask(__name__)
CORS(app)

# Register all API routes
app.register_blueprint(api_bp)


if __name__ == "__main__":
    # if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
    #     start_network_monitor()
    app.run(host="0.0.0.0", port=5000, debug=True)