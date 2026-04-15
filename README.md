# ShieldHome: Smart Home Intrusion Detection (IoT + Flask + Live Dashboard)

## Overview

ShieldHome is an IoT security project that combines:

1. Sensor-based intrusion detection (PIR, ultrasonic distance, LDR, touch).
2. Host network monitoring (connections, suspicious ports, traffic bursts).
3. A real-time Flask dashboard with analytics, event logs, and secured login flow.

The system is designed for end-to-end demonstration with Python simulation, optional ESP32/Wokwi integration, backend APIs, and a modern browser dashboard.

## What Is Implemented

### Security and Authentication

1. Login-first routing: opening the website root shows login page first.
2. User registration with email OTP verification.
3. Existing-user direct login (email + password).
4. Server-side Flask session/cookie enforcement for protected pages and APIs.
5. Logout clears both browser session data and Flask server session.

### Detection and Monitoring

1. Intrusion detection logic in backend for incoming sensor payloads.
2. Event persistence in JSON storage with thread-safe writes.
3. Host network monitor with:
     1. external IP/connection detection,
     2. suspicious port detection,
     3. traffic burst alerts.

### Dashboard

1. Live KPIs (total, intrusions, safe, alert rate, network alerts).
2. Event log with filtering (including network event type).
3. Combined analytics chart for all four sensors.
4. API status view and latest network event snapshot.
5. Login and profile pages integrated with dashboard flow.

## Architecture

```text
ESP32/Wokwi or Python Sensor Simulator
                                |
                                v
             Flask Backend API (port 5000)
                - Auth, detect, profile
                - Network monitor thread
                                |
                                v
        JSON Event Store (backend/events.json)
                                |
                                v
            Flask Dashboard Server (port 8050)
            - Login, dashboard, profile pages
            - Protected dashboard APIs
```

## Tech Stack

### Backend

1. Python
2. Flask, Flask-CORS
3. python-dotenv
4. MongoDB (PyMongo) for users and device tokens
5. psutil for host network telemetry

### Frontend

1. HTML/CSS/JavaScript
2. Chart.js

### Simulation and IoT

1. Python sensor simulator
2. ESP32 simulation via Wokwi

## Project Structure

```text
smart-home-intrusion-iot/
    backend/
        app.py
        routes.py
        detector.py
        network_monitor.py
        storage.py
        db.py
        events.json
    dashboard/
        dashboard.py
        smart_home_intrusion_full_dashboard.html
        login.html
        profile.html
    simulator/
        sensor_simulator.py
    esp32-sim/
        sketch.ino
        diagram.json
        wokwi.toml
    requirements.txt
    .env
    README.md
```

## Environment Variables (.env)

Required/used keys include:

1. `MONGO_URI`
2. `MONGO_DB_NAME`
3. `SMTP_HOST`
4. `SMTP_PORT`
5. `SMTP_USER`
6. `SMTP_PASS`
7. `MAIL_FROM`
8. `FLASK_SECRET_KEY`

Optional network monitor tuning:

1. `NETWORK_MONITOR_INTERVAL`
2. `NETWORK_BURST_BYTES`
3. `NETWORK_SUSPICIOUS_PORTS`
4. `NETWORK_MONITORED_PORTS`

## Setup and Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run backend API (port 5000)

```bash
cd backend
python app.py
```

### 3. Run dashboard server (port 8050)

```bash
cd dashboard
python dashboard.py
```

### 4. Optional: run Python sensor simulator

```bash
cd simulator
python sensor_simulator.py
```

Open:

1. `http://localhost:8050` -> login page
2. After login -> dashboard at `http://localhost:8050/dashboard`

## Auth and Access Flow

1. Root `/` always starts at login (unless already authenticated).
2. Protected pages:
     1. `/dashboard`
     2. `/profile`
3. Protected dashboard APIs under `/dashboard/api/*` return `401` when unauthenticated.
4. `/logout` clears server-side session and redirects to login.

## Main Endpoints

### Backend (port 5000)

1. `POST /login`
2. `POST /register`
3. `POST /verify-register-otp`
4. `POST /profile`
5. `POST /detect`

### Dashboard (port 8050)

1. `GET /dashboard/api/events`
2. `GET /dashboard/api/stats`
3. `GET /dashboard/api/sensors/latest`
4. `GET /dashboard/api/network/latest`
5. `GET /dashboard/api/health`
6. Proxy endpoints: `/proxy/login`, `/proxy/register`, `/proxy/verify-register-otp`, `/proxy/detect`, `/proxy/profile`

## Default Seed Users

On first run (empty users collection), backend seeds:

1. `user@shieldhome.local` / `pass123`
2. `security@shieldhome.local` / `secure123`

## Optional ESP32/Wokwi Integration

1. Start backend on port 5000.
2. Expose backend with ngrok:

```bash
ngrok http 5000
```

3. Update ESP32 API URL in `esp32-sim/sketch.ino`.

## Recent Updates

1. Added host network monitoring and network alert ingestion.
2. Added Network Alerts KPI and network event filtering in dashboard.
3. Added combined 4-sensor analytics graph.
4. Enforced login-first navigation.
5. Added server-side Flask session protection for pages and APIs.
6. Added logout endpoint with proper server session invalidation.

## Notes

1. Current implementation stores passwords in plain text in MongoDB (demo mode).
2. For production use, add password hashing and stricter cookie security.
3. Rotate any exposed credentials and do not commit secrets to public repositories.
