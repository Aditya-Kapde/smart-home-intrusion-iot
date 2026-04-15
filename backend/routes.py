"""
routes.py — ShieldHome Backend Route Blueprint
===============================================
All API routes registered as a Flask Blueprint.
User accounts and device tokens are stored in MongoDB via db.py.
"""
import cv2
import os
from camera import capture_image
from yolo_detector import detect_person
import threading
import os
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from secrets import randbelow

from flask import Blueprint, request, jsonify

from detector import detect_intrusion
from storage import save_event
from db import (
    find_user, create_user, seed_default_users,
    create_device_token, verify_device_token,
    update_user_login, get_user_profile,
)

api_bp = Blueprint("api", __name__)

# In-memory OTP store for login MFA (short-lived)
OTP_STORE: dict = {}
# In-memory store for pending registrations (email verification)
REGISTER_STORE: dict = {}
OTP_TTL_MINUTES = 5


# ── Seed demo users on blueprint registration ──────────────────────────────────
@api_bp.record_once
def _on_register(state):
    try:
        seed_default_users()
    except Exception as exc:
        print(f"[WARNING] Could not seed default users: {exc}")


# ── SMTP helper ────────────────────────────────────────────────────────────────

def _send_otp_email(
    recipient_email: str,
    otp: str,
    subject: str = "ShieldHome — Your OTP",
    body: str | None = None,
) -> None:
    if body is None:
        body = (
            f"Your ShieldHome one-time password is:\n\n"
            f"  {otp}\n\n"
            f"This code expires in {OTP_TTL_MINUTES} minutes.\n"
            "If you did not request this, please ignore this email."
        )
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_user = (os.getenv("SMTP_USER") or "").strip()
    smtp_pass = (os.getenv("SMTP_PASS") or "").replace(" ", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    mail_from = os.getenv("MAIL_FROM", smtp_user or "no-reply@shieldhome.local")

    if not smtp_user or not smtp_pass:
        raise RuntimeError(
            "SMTP credentials missing. Set SMTP_USER and SMTP_PASS in your .env file."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"]    = mail_from
    msg["To"]      = recipient_email
    msg.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
        server.ehlo()
        server.starttls()   # TLS only on port 587 — do NOT combine with SSL
        server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


def process_motion(base_result):
    frame = capture_image()

    if frame is None:
        print("Camera error")
        return

    is_person = detect_person(frame)

    if is_person:
        print("🚨 Person detected")

        # Create folder if not exists
        os.makedirs("captures", exist_ok=True)

        # Unique filename using timestamp
        filename = f"captures/intrusion_{int(datetime.utcnow().timestamp())}.jpg"

        # Save image
        cv2.imwrite(filename, frame)

        # Update result
        base_result["verified"] = True
        base_result["type"] = "unknown"
        base_result["source"] = "YOLO"
        base_result["time"] = str(datetime.utcnow())
        base_result["image"] = filename   # VERY IMPORTANT

        save_event(base_result)

    else:
        print("No person detected")


# ── Auth Routes ────────────────────────────────────────────────────────────────

@api_bp.route("/register", methods=["POST"])
def register():
    """
    Step 1 of registration: validate input and send email OTP.
    Does NOT create the account yet — that happens in /verify-register-otp.
    """
    data         = request.get_json(silent=True) or {}
    email        = str(data.get("email", "")).strip().lower()
    password     = str(data.get("password", "")).strip()
    display_name = str(data.get("display_name", "")).strip()

    if not email or not password:
        return jsonify({"status": "fail", "message": "Email and password are required."}), 400
    if len(password) < 6:
        return jsonify({"status": "fail", "message": "Password must be at least 6 characters."}), 400

    # Check if email is already registered
    if find_user(email):
        return jsonify({"status": "fail", "message": "Email already registered."}), 409

    # Generate OTP and store pending registration
    otp = f"{randbelow(900000) + 100000:06d}"
    REGISTER_STORE[email] = {
        "password":     password,
        "display_name": display_name or email.split("@")[0],
        "otp":          otp,
        "expires_at":   datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES),
    }

    try:
        _send_otp_email(
            email,
            otp,
            subject="ShieldHome — Verify Your Email",
            body=(
                f"Welcome to ShieldHome!\n\n"
                f"Your email verification code is:\n\n"
                f"  {otp}\n\n"
                f"Enter this code to complete your registration.\n"
                f"It expires in {OTP_TTL_MINUTES} minutes.\n\n"
                "If you did not create a ShieldHome account, please ignore this email."
            ),
        )
    except Exception as exc:
        REGISTER_STORE.pop(email, None)
        return jsonify({"status": "error", "message": f"Could not send verification email: {exc}"}), 500

    return jsonify({
        "status":  "otp_sent",
        "message": f"Verification code sent to {email}. Enter it to complete registration.",
    })


@api_bp.route("/verify-register-otp", methods=["POST"])
def verify_register_otp():
    """
    Step 2 of registration: verify email OTP and create the user in MongoDB.
    """
    data  = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    otp   = str(data.get("otp", "")).strip()

    pending = REGISTER_STORE.get(email)
    if not pending:
        return jsonify({"status": "fail", "message": "No pending registration for this email."}), 400
    if datetime.utcnow() > pending["expires_at"]:
        REGISTER_STORE.pop(email, None)
        return jsonify({"status": "fail", "message": "Verification code expired. Please register again."}), 401
    if pending["otp"] != otp:
        return jsonify({"status": "fail", "message": "Invalid verification code."}), 401

    REGISTER_STORE.pop(email, None)

    # Now create the verified user in MongoDB
    try:
        user = create_user(email, pending["password"], pending["display_name"])
    except ValueError as exc:
        return jsonify({"status": "fail", "message": str(exc)}), 409
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Database error: {exc}"}), 500

    return jsonify({
        "status":  "success",
        "message": "Email verified! Account created successfully. You can now sign in.",
        "user":    user,
    })


@api_bp.route("/login", methods=["POST"])
def login():
    """Direct login for existing users (email + password only)."""
    data         = request.get_json(silent=True) or {}
    email        = str(data.get("email", "")).strip().lower()
    password     = data.get("password", "")

    user = find_user(email)
    if not user or user.get("password") != password:
        return jsonify({"status": "fail", "message": "Invalid email or password."}), 401

    try:
        update_user_login(email)
    except Exception:
        pass

    return jsonify({
        "status": "success",
        "message": "Logged in successfully.",
        "user": {
            "email":        email,
            "display_name": user.get("display_name", email.split("@")[0]),
            "role":         user.get("role", "user"),
        },
    })


@api_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    """Step 2: verify OTP, optionally issue a persistent device token."""
    data           = request.get_json(silent=True) or {}
    email          = str(data.get("email", "")).strip().lower()
    otp            = str(data.get("otp", "")).strip()
    remember_device = bool(data.get("remember_device", False))

    otp_entry = OTP_STORE.get(email)
    user      = find_user(email)

    if not user or not otp_entry:
        return jsonify({"status": "fail", "message": "OTP not requested or already used."}), 401
    if datetime.utcnow() > otp_entry["expires_at"]:
        OTP_STORE.pop(email, None)
        return jsonify({"status": "fail", "message": "OTP expired. Please login again."}), 401
    if otp_entry["otp"] != otp:
        return jsonify({"status": "fail", "message": "Invalid OTP."}), 401

    OTP_STORE.pop(email, None)

    # ── Track login in DB ──────────────────────────────────────────────────────
    try:
        update_user_login(email)
    except Exception as exc:
        print(f"[WARNING] Could not update login info: {exc}")

    # ── Persist device token in MongoDB if requested ───────────────────────────
    device_token = None
    if remember_device:
        try:
            device_token = create_device_token(email, days=30)
        except Exception as exc:
            print(f"[WARNING] Could not persist device token: {exc}")

    return jsonify({
        "status":        "success",
        "device_token":  device_token,
        "user": {
            "email":        email,
            "display_name": user.get("display_name", email.split("@")[0]),
            "role":         user.get("role", "user"),
        },
    })


# ── Profile Route ──────────────────────────────────────────────────────────────

@api_bp.route("/profile", methods=["POST"])
def profile():
    """Return user profile from MongoDB (no password)."""
    data  = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    if not email:
        return jsonify({"status": "fail", "message": "Email required."}), 400
    prof = get_user_profile(email)
    if not prof:
        return jsonify({"status": "fail", "message": "User not found."}), 404
    return jsonify({"status": "success", "user": prof})


# ── Detection Route ────────────────────────────────────────────────────────────

@api_bp.route("/detect", methods=["POST"])
def detect():
    data = request.get_json(silent=True) or {}

    result = detect_intrusion(data)

    # If PIR says motion → trigger YOLO
    if result.get("intrusion"):

        # Run in background (VERY IMPORTANT)
        threading.Thread(target=process_motion, args=(result,)).start()
    return jsonify(result)
