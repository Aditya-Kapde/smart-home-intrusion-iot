# 🏠 Smart Home Intrusion Detection System (IoT + Cloud + Dashboard)

## 📌 Overview

This project is an IoT-based Smart Home Intrusion Detection System that monitors motion events in real time using simulated sensors and provides live alerts through a cloud-connected dashboard.

The system integrates IoT simulation, backend APIs, and a professional analytics dashboard to demonstrate a complete end-to-end smart security solution.

---

## 🚀 Features

* 🔐 User Authentication (Login System)
* 📡 Real-time IoT Data Simulation
* 🚨 Intrusion Detection Alerts
* 📊 Live Analytics Dashboard
* 📈 Trend Visualization & Charts
* 📋 Event Logging System
* 🌐 Cloud Exposure using ngrok (for IoT integration)
* ⚙️ Adjustable refresh rate & controls

---

## 🧠 System Architecture

```
IoT Sensor (ESP32 / Simulator)
            ↓
        Backend API (Flask)
            ↓
        Data Storage (JSON)
            ↓
     Analytics Dashboard (Streamlit)
```

---

## 🛠️ Tech Stack

### 🔹 Backend

* Python
* Flask

### 🔹 Frontend / Dashboard

* Streamlit
* Pandas

### 🔹 IoT Simulation

* Python Simulator
* ESP32 (Wokwi)

### 🔹 Networking

* ngrok (for public API exposure)

---

## 📂 Project Structure

```
iot/
│
├── backend/
│   ├── app.py
│   ├── detector.py
│   ├── storage.py
│
├── dashboard/
│   └── dashboard.py
│
├── simulator/
│   └── sensor_simulator.py
│
├── esp32-sim/
│   ├── sketch.ino
│   └── diagram.json
│
├── requirements.txt
└── README.md
```

---

## ⚙️ Getting Started

### 1️⃣ Clone Repository

```
git clone <your-repo-url>
cd iot
```

---

### 2️⃣ Setup Virtual Environment

```
python3 -m venv venv
source venv/bin/activate
```

---

### 3️⃣ Install Dependencies

```
pip install -r requirements.txt
```

---

### 4️⃣ Run Backend Server

```
cd backend
python app.py
```

---

### 5️⃣ Run Dashboard

```
cd dashboard
streamlit run dashboard.py
```

---

### 6️⃣ Run IoT Simulator

```
cd simulator
python sensor_simulator.py
```

---

## 🔐 Login Credentials

```
Username: admin
Password: 1234
```

---

## 🌐 Optional: IoT Integration (ESP32 via Wokwi)

1. Start backend
2. Run ngrok:

   ```
   ngrok http 5000
   ```
3. Replace API URL in ESP32 code with ngrok URL

---

## 📊 Dashboard Highlights

* Real-time intrusion alerts
* KPI metrics (Total events, Intrusions, Safe events)
* Intrusion trend graph
* Hourly activity analysis
* Event distribution visualization
* Event log table

---

## ⚠️ Notes

* Wokwi simulations may have network limitations when connecting to local servers.
* For reliable testing, use the Python simulator.

---

## 🎯 Future Improvements

* Role-based access control
* Email / SMS alerts
* Mobile app integration
* Camera-based detection
* Cloud deployment (AWS / GCP)

---

## 👨‍💻 Contributors

* Aditya Kapde
* Team Members

---

## 📜 License

This project is for educational purposes.
