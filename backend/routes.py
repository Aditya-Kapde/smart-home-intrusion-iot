"""
routes.py - ShieldHome Backend Route Blueprint
==============================================
All API routes registered as a Flask Blueprint.
User accounts and device tokens are stored in MongoDB via db.py.
"""
import cv2
import os
import threading
import smtplib
import mimetypes
from datetime import datetime, timedelta
from email.message import EmailMessage
from secrets import randbelow

from flask import Blueprint, request, jsonify

from camera import capture_image
from yolo_detector import detect_person_details
from image_classifier import get_classification_confidence
from detector import detect_intrusion
from storage import save_event
from db import (
    find_user, create_user, seed_default_users,
    create_device_token, verify_device_token,
    update_user_login, get_user_profile, list_alert_recipients,
    set_active_alert_recipient, get_active_alert_recipient,
)

api_bp = Blueprint("api", __name__)

# In-memory OTP store for login MFA (short-lived)
OTP_STORE: dict = {}
# In-memory store for pending registrations (email verification)
REGISTER_STORE: dict = {}
OTP_TTL_MINUTES = 5


# Seed demo users on blueprint registration
@api_bp.record_once
def _on_register(state):
    try:
        seed_default_users()
    except Exception as exc:
        print(f"[WARNING] Could not seed default users: {exc}")


def _send_otp_email(
    recipient_email: str,
    otp: str,
    subject: str = "ShieldHome - Your OTP",
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
    msg["From"] = mail_from
    msg["To"] = recipient_email
    msg.set_content(body)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


def _resolve_alert_recipients() -> list[str]:
    active_email = get_active_alert_recipient()
    if active_email:
        return [active_email]

    configured = os.getenv("ALERT_EMAIL_RECIPIENTS", "").strip()
    if configured:
        emails = [email.strip().lower() for email in configured.split(",") if email.strip()]
        if emails:
            return sorted(set(emails))
    return list_alert_recipients()


def _send_human_detection_email(event: dict) -> None:
    recipients = _resolve_alert_recipients()
    if not recipients:
        print("[INFO] No alert email recipients configured; skipping intrusion email.")
        return

    detected_at = event.get("timestamp") or event.get("time") or datetime.utcnow().isoformat()
    confidence = float(event.get("classification_confidence", 0.0) or 0.0)
    threshold = float(event.get("classification_threshold", 0.0) or 0.0)
    person_boxes = int(event.get("person_boxes", 0) or 0)
    image_path = event.get("image", "")
    image_name = os.path.basename(image_path) if image_path else None

    subject = "ShieldHome Security Alert: Human Detected on Webcam"
    text_body = (
        "ShieldHome Security Alert\n"
        "=========================\n\n"
        "A human presence was detected by the webcam and classified as a verified intrusion event.\n\n"
        f"Detection time (UTC): {detected_at}\n"
        f"Classification: {event.get('classification', 'human')}\n"
        f"Detection confidence: {confidence:.2%}\n"
        f"Alert threshold: {threshold:.2%}\n"
        f"Person boxes detected: {person_boxes}\n"
        f"Event message: {event.get('message', 'Motion detected! Possible intrusion.')}\n"
        f"Captured image: {image_name or 'Not attached'}\n\n"
        "Please review the dashboard and investigate the premises as appropriate.\n\n"
        "Regards,\n"
        "ShieldHome Monitoring System"
    )

    html_body = f"""
<html>
  <body style="font-family:Arial,Helvetica,sans-serif;color:#17212b;line-height:1.5;">
    <h2 style="margin-bottom:8px;color:#b42318;">ShieldHome Security Alert</h2>
    <p style="margin-top:0;">A human presence was detected by the webcam and classified as a verified intrusion event.</p>
    <table style="border-collapse:collapse;margin:16px 0;">
      <tr><td style="padding:6px 12px;border:1px solid #d0d5dd;"><strong>Detection time (UTC)</strong></td><td style="padding:6px 12px;border:1px solid #d0d5dd;">{detected_at}</td></tr>
      <tr><td style="padding:6px 12px;border:1px solid #d0d5dd;"><strong>Classification</strong></td><td style="padding:6px 12px;border:1px solid #d0d5dd;">{event.get('classification', 'human')}</td></tr>
      <tr><td style="padding:6px 12px;border:1px solid #d0d5dd;"><strong>Detection confidence</strong></td><td style="padding:6px 12px;border:1px solid #d0d5dd;">{confidence:.2%}</td></tr>
      <tr><td style="padding:6px 12px;border:1px solid #d0d5dd;"><strong>Alert threshold</strong></td><td style="padding:6px 12px;border:1px solid #d0d5dd;">{threshold:.2%}</td></tr>
      <tr><td style="padding:6px 12px;border:1px solid #d0d5dd;"><strong>Person boxes detected</strong></td><td style="padding:6px 12px;border:1px solid #d0d5dd;">{person_boxes}</td></tr>
      <tr><td style="padding:6px 12px;border:1px solid #d0d5dd;"><strong>Event message</strong></td><td style="padding:6px 12px;border:1px solid #d0d5dd;">{event.get('message', 'Motion detected! Possible intrusion.')}</td></tr>
      <tr><td style="padding:6px 12px;border:1px solid #d0d5dd;"><strong>Captured image</strong></td><td style="padding:6px 12px;border:1px solid #d0d5dd;">{image_name or 'Attached below if available'}</td></tr>
    </table>
    <p>Please review the dashboard and investigate the premises as appropriate.</p>
    <p style="margin-top:24px;">Regards,<br/>ShieldHome Monitoring System</p>
  </body>
</html>
""".strip()

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
    msg["From"] = mail_from
    msg["To"] = ", ".join(recipients)
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    if image_path and os.path.isfile(image_path):
        mime_type, _ = mimetypes.guess_type(image_path)
        maintype, subtype = (mime_type or "image/jpeg").split("/", 1)
        with open(image_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype=maintype,
                subtype=subtype,
                filename=image_name or "intrusion.jpg",
            )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


def _send_human_detection_email_safe(event: dict) -> None:
    try:
        _send_human_detection_email(event)
        print("[INFO] Human-detection email alert sent successfully.")
    except Exception as exc:
        print(f"[WARNING] Could not send human-detection email alert: {exc}")


def process_motion(base_result):
    frame = capture_image()

    if frame is None:
        print("Camera error")
        return

    person_detection = detect_person_details(frame)

    if person_detection["detected"]:
        print(
            "Human detected by YOLO "
            f"(confidence={person_detection['best_confidence']:.2%}, "
            f"threshold={person_detection['threshold']:.2%}, "
            f"boxes={person_detection['person_boxes']})"
        )

        os.makedirs("captures", exist_ok=True)
        filename = f"captures/intrusion_{int(datetime.utcnow().timestamp())}.jpg"
        cv2.imwrite(filename, frame)

        # If a person is present with an object, classify the whole event as human.
        base_result["verified"] = True
        base_result["type"] = "human"
        base_result["source"] = "YOLO person detector"
        base_result["time"] = str(datetime.utcnow())
        base_result["image"] = filename
        base_result["classification"] = "human"
        base_result["classification_confidence"] = person_detection["best_confidence"]
        base_result["classification_threshold"] = person_detection["threshold"]
        base_result["person_boxes"] = person_detection["person_boxes"]
        base_result["timestamp"] = datetime.utcnow().isoformat(timespec="seconds")

        save_event(base_result)
        threading.Thread(
            target=_send_human_detection_email_safe,
            args=(dict(base_result),),
            daemon=True,
        ).start()
        return

    image_result = get_classification_confidence(frame)
    print(
        "No human alert. "
        f"YOLO best person confidence={person_detection['best_confidence']:.2%} "
        f"(threshold={person_detection['threshold']:.2%}). "
        f"Fallback category={image_result['category']} "
        f"confidence={image_result['confidence']:.2%}. "
        f"{image_result['details']}"
    )


@api_bp.route("/register", methods=["POST"])
def register():
    """
    Step 1 of registration: validate input and send email OTP.
    Does NOT create the account yet - that happens in /verify-register-otp.
    """
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", "")).strip()
    display_name = str(data.get("display_name", "")).strip()

    if not email or not password:
        return jsonify({"status": "fail", "message": "Email and password are required."}), 400
    if len(password) < 6:
        return jsonify({"status": "fail", "message": "Password must be at least 6 characters."}), 400

    if find_user(email):
        return jsonify({"status": "fail", "message": "Email already registered."}), 409

    otp = f"{randbelow(900000) + 100000:06d}"
    REGISTER_STORE[email] = {
        "password": password,
        "display_name": display_name or email.split("@")[0],
        "otp": otp,
        "expires_at": datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES),
    }

    try:
        _send_otp_email(
            email,
            otp,
            subject="ShieldHome - Verify Your Email",
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
        "status": "otp_sent",
        "message": f"Verification code sent to {email}. Enter it to complete registration.",
    })


@api_bp.route("/verify-register-otp", methods=["POST"])
def verify_register_otp():
    """
    Step 2 of registration: verify email OTP and create the user in MongoDB.
    """
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    otp = str(data.get("otp", "")).strip()

    pending = REGISTER_STORE.get(email)
    if not pending:
        return jsonify({"status": "fail", "message": "No pending registration for this email."}), 400
    if datetime.utcnow() > pending["expires_at"]:
        REGISTER_STORE.pop(email, None)
        return jsonify({"status": "fail", "message": "Verification code expired. Please register again."}), 401
    if pending["otp"] != otp:
        return jsonify({"status": "fail", "message": "Invalid verification code."}), 401

    REGISTER_STORE.pop(email, None)

    try:
        user = create_user(email, pending["password"], pending["display_name"])
    except ValueError as exc:
        return jsonify({"status": "fail", "message": str(exc)}), 409
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Database error: {exc}"}), 500

    return jsonify({
        "status": "success",
        "message": "Email verified! Account created successfully. You can now sign in.",
        "user": user,
    })


@api_bp.route("/login", methods=["POST"])
def login():
    """Direct login for existing users (email + password only)."""
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    user = find_user(email)
    if not user or user.get("password") != password:
        return jsonify({"status": "fail", "message": "Invalid email or password."}), 401

    try:
        update_user_login(email)
        set_active_alert_recipient(email)
    except Exception:
        pass

    return jsonify({
        "status": "success",
        "message": "Logged in successfully.",
        "user": {
            "email": email,
            "display_name": user.get("display_name", email.split("@")[0]),
            "role": user.get("role", "user"),
        },
    })


@api_bp.route("/verify-otp", methods=["POST"])
def verify_otp():
    """Step 2: verify OTP, optionally issue a persistent device token."""
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    otp = str(data.get("otp", "")).strip()
    remember_device = bool(data.get("remember_device", False))

    otp_entry = OTP_STORE.get(email)
    user = find_user(email)

    if not user or not otp_entry:
        return jsonify({"status": "fail", "message": "OTP not requested or already used."}), 401
    if datetime.utcnow() > otp_entry["expires_at"]:
        OTP_STORE.pop(email, None)
        return jsonify({"status": "fail", "message": "OTP expired. Please login again."}), 401
    if otp_entry["otp"] != otp:
        return jsonify({"status": "fail", "message": "Invalid OTP."}), 401

    OTP_STORE.pop(email, None)

    try:
        update_user_login(email)
        set_active_alert_recipient(email)
    except Exception as exc:
        print(f"[WARNING] Could not update login info: {exc}")

    device_token = None
    if remember_device:
        try:
            device_token = create_device_token(email, days=30)
        except Exception as exc:
            print(f"[WARNING] Could not persist device token: {exc}")

    return jsonify({
        "status": "success",
        "device_token": device_token,
        "user": {
            "email": email,
            "display_name": user.get("display_name", email.split("@")[0]),
            "role": user.get("role", "user"),
        },
    })


@api_bp.route("/profile", methods=["POST"])
def profile():
    """Return user profile from MongoDB (no password)."""
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    if not email:
        return jsonify({"status": "fail", "message": "Email required."}), 400
    prof = get_user_profile(email)
    if not prof:
        return jsonify({"status": "fail", "message": "User not found."}), 404
    return jsonify({"status": "success", "user": prof})


@api_bp.route("/detect", methods=["POST"])
def detect():
    data = request.get_json(silent=True) or {}

    result = detect_intrusion(data)

    if result.get("intrusion"):
        threading.Thread(target=process_motion, args=(result,)).start()
    return jsonify(result)
