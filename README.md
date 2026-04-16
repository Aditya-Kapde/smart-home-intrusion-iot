# ShieldHome

Professional Smart Home Intrusion Detection Platform combining IoT telemetry, host-network monitoring, deep-learning-assisted webcam verification, secure dashboard access, and real-time alerting.

## Overview

ShieldHome is an end-to-end smart security project designed to monitor a home environment through multiple sensing layers:

- physical intrusion signals from IoT-style sensor inputs such as PIR, ultrasonic, LDR, and touch
- host-level network activity monitoring for suspicious traffic and port-based anomalies
- webcam-assisted human verification using deep learning and computer vision
- a secured web dashboard for live visibility, analytics, event review, and alert handling
- email-based alert notification for verified human detections

The project is structured for academic demonstration, prototyping, and controlled local deployment. It supports both simulation and hardware-oriented workflows, making it suitable for presentation, experimentation, and future extension.

## Key Features

- Secure login-first dashboard experience with protected routes and APIs
- Email OTP-based user registration workflow
- MongoDB-backed user and session-related data
- Sensor intrusion ingestion through a Flask backend
- JSON-based event persistence for a lightweight real-time event pipeline
- Host network monitoring using `psutil`
- Deep-learning-assisted human detection through webcam capture
- Human-priority alert classification: if a person appears with another object, the event is still classified as human
- Email notification for verified human detections
- Real-time dashboard analytics and event visualization
- Mobile-accessible dashboard over the local network
- ESP32 / Wokwi simulation support
- Python sensor simulator for development and demos

## System Capabilities

### IoT and Physical Security

ShieldHome supports intrusion-related sensor data such as:

- PIR motion
- ultrasonic distance
- LDR light intensity
- touch activation

These inputs are evaluated by the backend intrusion logic and can trigger downstream verification, persistence, dashboard updates, and alerts.

### Network Security Monitoring

The platform includes host-network observation to complement physical monitoring. The network monitor records notable events such as:

- suspicious port usage
- burst traffic behavior
- monitored connection-state anomalies

This gives the system a hybrid security posture: physical intrusion awareness plus local network-awareness.

### Deep Learning and Computer Vision

ShieldHome includes a webcam-assisted verification stage for motion-triggered events.

- YOLO-based person detection is used to identify human presence in captured frames
- a ResNet50-based image classifier is available as a fallback for non-person categorization
- face detection is also used within the classifier path
- person detection currently takes precedence over object presence, so `person + object` is treated as `human`

This makes the detection flow more aligned with a real-world security objective: prioritize actual human presence over generic object classification.

## High-Level Architecture

```text
IoT Sensors / ESP32 / Python Simulator
                  |
                  v
        Flask Backend API (Port 5000)
        - intrusion detection
        - webcam capture
        - YOLO person detection
        - image classification fallback
        - network monitor integration
        - event storage
        - email alert generation
                  |
                  +--------------------> MongoDB Atlas / MongoDB
                  |                      - users
                  |                      - device tokens
                  |                      - alert recipient state
                  |
                  +--------------------> events.json
                                         - lightweight event log persistence
                                         - dashboard data source
                  |
                  v
       Dashboard Server (Port 8050)
       - login page
       - profile page
       - protected dashboard APIs
       - real-time analytics and logs
                  |
                  v
       Desktop / Mobile Browser Clients
```

## Project Modules

### Backend

The backend is responsible for:

- authentication and user operations
- intrusion event ingestion
- webcam-based verification
- event storage
- network-monitor signal capture
- alert-email generation

Main files:

- [backend/app.py](C:/Users/asus/Desktop/IOT/smart-home-intrusion-iot/backend/app.py)
- [backend/routes.py](C:/Users/asus/Desktop/IOT/smart-home-intrusion-iot/backend/routes.py)
- [backend/detector.py](C:/Users/asus/Desktop/IOT/smart-home-intrusion-iot/backend/detector.py)
- [backend/yolo_detector.py](C:/Users/asus/Desktop/IOT/smart-home-intrusion-iot/backend/yolo_detector.py)
- [backend/image_classifier.py](C:/Users/asus/Desktop/IOT/smart-home-intrusion-iot/backend/image_classifier.py)
- [backend/network_monitor.py](C:/Users/asus/Desktop/IOT/smart-home-intrusion-iot/backend/network_monitor.py)
- [backend/storage.py](C:/Users/asus/Desktop/IOT/smart-home-intrusion-iot/backend/storage.py)
- [backend/db.py](C:/Users/asus/Desktop/IOT/smart-home-intrusion-iot/backend/db.py)

### Dashboard

The dashboard layer is a dedicated Flask server that:

- serves login, profile, and dashboard pages
- protects access using server-side sessions
- reads live event data from backend storage
- provides analytics endpoints for frontend consumption

Main files:

- [dashboard/dashboard.py](C:/Users/asus/Desktop/IOT/smart-home-intrusion-iot/dashboard/dashboard.py)
- [dashboard/smart_home_intrusion_full_dashboard.html](C:/Users/asus/Desktop/IOT/smart-home-intrusion-iot/dashboard/smart_home_intrusion_full_dashboard.html)
- [dashboard/login.html](C:/Users/asus/Desktop/IOT/smart-home-intrusion-iot/dashboard/login.html)
- [dashboard/profile.html](C:/Users/asus/Desktop/IOT/smart-home-intrusion-iot/dashboard/profile.html)

### Simulation

Simulation is supported in two forms:

- Python-based simulator for sensor event generation
- ESP32/Wokwi-based integration for embedded-style demonstration

Relevant files:

- [simulator/sensor_simulator.py](C:/Users/asus/Desktop/IOT/smart-home-intrusion-iot/simulator/sensor_simulator.py)
- [esp32-sim/sketch.ino](C:/Users/asus/Desktop/IOT/smart-home-intrusion-iot/esp32-sim/sketch.ino)

## Technology Stack

### Backend and Services

- Python
- Flask
- Flask-CORS
- python-dotenv
- PyMongo
- psutil
- requests

### Data and Persistence

- MongoDB / MongoDB Atlas
- JSON event storage via `backend/events.json`

### Deep Learning and Vision

- PyTorch
- TorchVision
- ResNet50
- YOLO model integration
- OpenCV
- Pillow

### Frontend

- HTML
- CSS
- JavaScript
- Chart.js

### IoT and Demonstration

- ESP32 simulation via Wokwi
- Python simulator
- local webcam capture with OpenCV

## Repository Structure

```text
smart-home-intrusion-iot/
├── backend/
│   ├── app.py
│   ├── camera.py
│   ├── db.py
│   ├── detector.py
│   ├── image_classifier.py
│   ├── network_monitor.py
│   ├── routes.py
│   ├── storage.py
│   ├── yolo_detector.py
│   ├── events.json
│   └── captures/
├── dashboard/
│   ├── dashboard.py
│   ├── login.html
│   ├── profile.html
│   └── smart_home_intrusion_full_dashboard.html
├── simulator/
│   └── sensor_simulator.py
├── esp32-sim/
│   ├── sketch.ino
│   ├── diagram.json
│   └── wokwi.toml
├── requirements.txt
├── .env
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.10+ recommended
- MongoDB Atlas or local MongoDB instance
- webcam connected to the host machine if using human detection
- SMTP credentials for email-based alerts

### Installation

```bash
pip install -r requirements.txt
```

If your environment does not already contain the YOLO dependency, install:

```bash
pip install ultralytics opencv-python
```

### Environment Configuration

Configure [`.env`](C:/Users/asus/Desktop/IOT/smart-home-intrusion-iot/.env) with the required values.

Common keys include:

- `MONGO_URI`
- `MONGO_DB_NAME`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASS`
- `MAIL_FROM`
- `FLASK_SECRET_KEY`

Optional and model/security-related keys:

- `ALERT_EMAIL_RECIPIENTS`
- `YOLO_PERSON_CONFIDENCE`
- `NETWORK_MONITOR_INTERVAL`
- `NETWORK_BURST_BYTES`
- `NETWORK_SUSPICIOUS_PORTS`
- `NETWORK_MONITORED_PORTS`

### Running the System

Start the backend:

```bash
cd backend
python app.py
```

Start the dashboard server:

```bash
cd dashboard
python dashboard.py
```

Optional: start the Python sensor simulator:

```bash
cd simulator
python sensor_simulator.py
```

Open the application in a browser:

- `http://localhost:8050`

After login, the protected dashboard is available at:

- `http://localhost:8050/dashboard`

## Mobile Access on Local Network

The dashboard server is configured for LAN access. To open it from a phone on the same Wi-Fi network:

1. Start the backend and dashboard on the laptop
2. Find the laptop IPv4 address using `ipconfig`
3. Open the dashboard on mobile as:

```text
http://<laptop-ip>:8050
```

Example:

```text
http://192.168.0.217:8050
```

Notes:

- both devices must be on the same Wi-Fi network
- Windows Firewall must allow the Python process on private networks
- some institutional routers block device-to-device access through AP/client isolation

## Authentication and Access Control

ShieldHome currently uses a login-first model.

- opening `/` shows the login page unless a valid session already exists
- protected pages include `/dashboard` and `/profile`
- dashboard APIs under `/dashboard/api/*` return `401` when unauthenticated
- logout clears the server session and redirects to login

The project currently supports:

- direct login with email and password
- OTP-based email verification for new-user registration
- protected dashboard API access
- active alert-recipient tracking based on the logged-in dashboard user

## Alerting Workflow

When a human is verified through the webcam flow:

1. the backend stores the event in `events.json`
2. an image capture is saved in `backend/captures`
3. the event is classified as `human`
4. an email alert is sent
5. the alert recipient defaults to the most recently logged-in dashboard user

Fallback recipient priority:

1. current active dashboard login email
2. `ALERT_EMAIL_RECIPIENTS` from `.env`
3. security/admin users in MongoDB

## Deep Learning Design

ShieldHome’s human-verification logic is designed around practical alert prioritization.

### Current Decision Flow

1. motion/intrusion is triggered from sensor input
2. webcam frame is captured
3. YOLO checks whether a person is present
4. if a person is detected above the configured confidence threshold, the event is labeled `human`
5. if not, the fallback classifier may label the frame as `animal` or `object`

### Current Thresholds

- person detection threshold defaults to `0.35`
- animal classification threshold defaults to `0.30`

### Important Behavioral Rule

If a frame contains a person together with another object, the event is still classified as `human`.

This is intentional and aligns with the security goal of prioritizing human presence.

## Network Security Scope

The project is not limited to physical intrusion detection. It also models a broader smart-home security perspective by monitoring host-level network behavior.

The network monitor can contribute:

- suspicious activity events
- network burst notifications
- port-related observations

These events are ingested into the same dashboard ecosystem, allowing the platform to unify physical and cyber observability in one interface.

## Cloud Computing Context

ShieldHome already uses cloud components selectively:

- MongoDB Atlas can be used as the cloud database
- SMTP email delivery depends on an external mail provider
- ngrok or similar tunneling can be used for external testing

However, the current backend is not intended for pure cloud deployment without architectural changes because:

- webcam capture depends on local device hardware
- `cv2.VideoCapture(0)` assumes direct access to a physical camera
- cloud runtimes do not have access to the host webcam in the same way

### Recommended Deployment Model

For the current architecture, the best deployment strategy is:

- backend on a local or edge machine with webcam access
- dashboard on the same machine or local network
- MongoDB Atlas in the cloud
- SMTP alert delivery via cloud email provider

This hybrid model preserves the deep-learning verification path without code changes.

## API Summary

### Backend API on Port 5000

- `POST /login`
- `POST /register`
- `POST /verify-register-otp`
- `POST /verify-otp`
- `POST /profile`
- `POST /detect`

### Dashboard API on Port 8050

- `GET /dashboard/api/events`
- `GET /dashboard/api/stats`
- `GET /dashboard/api/sensors/latest`
- `GET /dashboard/api/network/latest`
- `GET /dashboard/api/health`

Dashboard proxy endpoints also exist for authentication and selected backend calls.

## ESP32 / Wokwi Integration

The project includes embedded simulation support through Wokwi.

Typical flow:

1. run the backend locally on port `5000`
2. expose it externally if needed using a tunnel such as ngrok
3. point the ESP32 simulated sketch to the exposed `/detect` endpoint

This makes it possible to demonstrate an IoT-to-web-to-alert pipeline without requiring fully assembled hardware.

## Default Seed Users

If the users collection is empty, the system seeds demo users:

- `user@shieldhome.local` / `pass123`
- `security@shieldhome.local` / `secure123`

These are demo credentials only and should not be used outside controlled development.

## Security Notes

This project is strong as a prototype and demonstration platform, but some production-grade controls are still pending.

Current limitations include:

- passwords are currently stored in plain text
- JSON event storage is suitable for prototyping but not ideal for scalable production analytics
- LAN/mobile access may depend on local firewall configuration
- email and database secrets must never be committed to a public repository
- webcam capture binds the backend to the local host machine

Recommended future improvements:

- password hashing with `bcrypt` or `argon2`
- CSRF protection where appropriate
- role-based authorization beyond basic session gating
- persistent production-grade event storage
- audit logging
- secure secrets management
- known-person authorization flow for suppressing alerts on trusted identities

## Present Status

At the current stage, the project includes:

- secure dashboard login flow
- email-verified registration
- live dashboard analytics
- network-monitor event ingestion
- YOLO-backed human detection
- human-priority webcam alert classification
- email alerting to the logged-in dashboard user
- local-network mobile dashboard support
- mobile-responsive dashboard improvements

## Future Enhancements

The following are natural next steps for the project:

- known-person / authorized-face recognition
- cloud-ready edge-to-server separation
- production deployment packaging with Docker or systemd
- richer alert escalation workflows
- push notifications in addition to email
- camera stream snapshots or timeline review
- better event replay and forensic search

## Disclaimer

ShieldHome is currently best understood as a professional prototype / academic demonstration platform. It showcases a strong integration of IoT monitoring, cyber-observability, dashboard engineering, and deep-learning-assisted verification, but it still requires production-hardening before real-world deployment in high-risk environments.
