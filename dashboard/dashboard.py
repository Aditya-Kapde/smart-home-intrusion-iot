import streamlit as st
import requests
import json
import os
import time
import pandas as pd

st.set_page_config(page_title="Smart Security", layout="wide")

API_URL = "http://localhost:5000"

# ---------- SESSION ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False


# ---------- LOGIN ----------
def login_ui():
    st.title("🔐 Smart Home Security Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        res = requests.post(f"{API_URL}/login", json={
            "username": username,
            "password": password
        })

        if res.status_code == 200:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid credentials")


# ---------- DASHBOARD ----------
def dashboard_ui():
    st.sidebar.title("⚙️ Controls")

    refresh_rate = st.sidebar.slider("Refresh Rate (sec)", 1, 5, 2)

    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

    st.title("🏠 Smart Intrusion Detection System")
    st.markdown("### Real-time Analytics Dashboard")

    file_path = os.path.join(os.path.dirname(__file__), "../backend/events.json")

    placeholder = st.empty()

    while True:
        with placeholder.container():

            try:
                with open(file_path, "r") as f:
                    events = json.load(f)
            except:
                events = []

            st.divider()

            # ---------- KPI CARDS ----------
            total = len(events)
            intrusions = sum(1 for e in events if e["intrusion"])
            safe = total - intrusions

            col1, col2, col3 = st.columns(3)
            col1.metric("📊 Total Events", total)
            col2.metric("🚨 Intrusions", intrusions)
            col3.metric("✅ Safe Events", safe)

            st.divider()

            # ---------- ALERTS ----------
            st.subheader("🚨 Recent Alerts")

            if not events:
                st.success("No intrusions detected")
            else:
                cols = st.columns(3)
                for i, event in enumerate(reversed(events[-6:])):
                    with cols[i % 3]:
                        st.error(f"""
                        🚨 Intrusion  
                        🕒 {event['timestamp']}  
                        📢 {event['message']}
                        """)

            # ---------- ANALYTICS ----------
            if events:
                df = pd.DataFrame(events)
                df["timestamp"] = pd.to_datetime(df["timestamp"])

                st.divider()
                st.subheader("📈 Analytics")

                # Layout
                colA, colB = st.columns(2)

                # 🔹 LINE CHART (Trend)
                with colA:
                    st.markdown("#### Intrusion Trend")
                    st.line_chart(df.set_index("timestamp")["intrusion"])

                # 🔹 BAR CHART (Hourly)
                with colB:
                    st.markdown("#### Hourly Activity")
                    df["hour"] = df["timestamp"].dt.hour
                    hourly = df.groupby("hour")["intrusion"].sum()
                    st.bar_chart(hourly)

                # 🔹 PIE CHART (Distribution)
                st.markdown("#### Event Distribution")
                pie_data = pd.DataFrame({
                    "Type": ["Intrusion", "Safe"],
                    "Count": [intrusions, safe]
                }).set_index("Type")

                st.bar_chart(pie_data)  # (Streamlit doesn't have pie → clean alt)

                # 🔹 TABLE (Raw Data)
                st.markdown("#### Event Log")
                st.dataframe(df.sort_values("timestamp", ascending=False))

        time.sleep(refresh_rate)


# ---------- MAIN ----------
if not st.session_state.logged_in:
    login_ui()
else:
    dashboard_ui()