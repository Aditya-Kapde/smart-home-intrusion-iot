"""
db.py — MongoDB connection and user/device-token DAL
======================================================
All database operations are centralised here so routes.py
stays clean.  The module lazily connects on first use so
the backend still starts even if MONGO_URI is wrong (it
will just raise on the first DB call).
"""

import os
from datetime import datetime, timedelta
from secrets import randbelow

from pymongo import MongoClient, ASCENDING
from pymongo.errors import DuplicateKeyError

# ── Connection ─────────────────────────────────────────────────────────────────
_client: MongoClient | None = None


def get_db():
    """Return the MongoDB database handle, creating the connection on first call."""
    global _client
    if _client is None:
        uri  = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        name = os.getenv("MONGO_DB_NAME", "shieldhome")
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        # Ensure indexes on first connect
        db = _client[name]
        db["users"].create_index("email", unique=True)
        db["device_tokens"].create_index("token", unique=True)
        db["device_tokens"].create_index("expires_at", expireAfterSeconds=0)  # TTL index
    return _client[os.getenv("MONGO_DB_NAME", "shieldhome")]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _users():
    return get_db()["users"]

def _tokens():
    return get_db()["device_tokens"]


def _app_settings():
    return get_db()["app_settings"]


# ── User operations ────────────────────────────────────────────────────────────

def find_user(email: str) -> dict | None:
    """Return user document (without _id) or None."""
    doc = _users().find_one({"email": email.lower()}, {"_id": 0})
    return doc


def get_user_profile(email: str) -> dict | None:
    """Return safe user info (no password) or None."""
    doc = _users().find_one(
        {"email": email.lower()},
        {"_id": 0, "password": 0}
    )
    if doc and "created_at" in doc:
        doc["created_at"] = doc["created_at"].isoformat()
    if doc and "last_login" in doc:
        doc["last_login"] = doc["last_login"].isoformat()
    return doc


def create_user(email: str, password: str, display_name: str = "", role: str = "user") -> dict:
    """
    Insert a new user.
    Raises ValueError if email already exists.
    """
    email = email.lower().strip()
    display_name = display_name.strip() or email.split("@")[0]
    doc = {
        "email":        email,
        "password":     password,   # hash before storing in production!
        "display_name": display_name,
        "role":         role,
        "created_at":   datetime.utcnow(),
        "last_login":   None,
        "login_count":  0,
    }
    try:
        _users().insert_one(doc)
    except DuplicateKeyError:
        raise ValueError("Email already registered.")
    return {"email": email, "display_name": display_name, "role": role}


def update_user_login(email: str) -> None:
    """Stamp last_login and increment login_count after successful OTP."""
    _users().update_one(
        {"email": email.lower()},
        {
            "$set": {"last_login": datetime.utcnow()},
            "$inc": {"login_count": 1},
        },
    )


def list_alert_recipients() -> list[str]:
    """Return preferred email recipients for intrusion alerts."""
    docs = list(
        _users().find(
            {"role": {"$in": ["security", "admin"]}},
            {"_id": 0, "email": 1},
        )
    )
    emails = [str(doc.get("email", "")).strip().lower() for doc in docs if doc.get("email")]
    if emails:
        return sorted(set(emails))

    docs = list(_users().find({}, {"_id": 0, "email": 1}))
    emails = [str(doc.get("email", "")).strip().lower() for doc in docs if doc.get("email")]
    return sorted(set(emails))


def set_active_alert_recipient(email: str) -> None:
    """Persist the most recently authenticated dashboard user for alert delivery."""
    normalized = str(email or "").strip().lower()
    if not normalized:
        return
    _app_settings().update_one(
        {"key": "active_alert_recipient"},
        {
            "$set": {
                "key": "active_alert_recipient",
                "email": normalized,
                "updated_at": datetime.utcnow(),
            }
        },
        upsert=True,
    )


def get_active_alert_recipient() -> str | None:
    """Return the most recent dashboard login email used for alert delivery."""
    doc = _app_settings().find_one({"key": "active_alert_recipient"}, {"_id": 0, "email": 1})
    if not doc:
        return None
    email = str(doc.get("email", "")).strip().lower()
    return email or None


def seed_default_users():
    """
    Insert demo accounts if the users collection is empty.
    Safe to call on every startup.
    """
    if _users().count_documents({}) == 0:
        for user in [
            {
                "email": "user@shieldhome.local",
                "password": "pass123",
                "display_name": "Shield User",
                "role": "user",
                "created_at": datetime.utcnow(),
            },
            {
                "email": "security@shieldhome.local",
                "password": "secure123",
                "display_name": "Security Operator",
                "role": "security",
                "created_at": datetime.utcnow(),
            },
        ]:
            try:
                _users().insert_one(user)
            except DuplicateKeyError:
                pass


# ── Device-token operations ────────────────────────────────────────────────────

def create_device_token(email: str, days: int = 30) -> str:
    """Persist a new device token; returns the token string."""
    token   = f"dev_{randbelow(10**12):012d}"
    expires = datetime.utcnow() + timedelta(days=days)
    _tokens().insert_one({
        "token":      token,
        "email":      email.lower(),
        "expires_at": expires,          # MongoDB TTL index auto-deletes when expired
        "created_at": datetime.utcnow(),
    })
    return token


def verify_device_token(token: str, email: str) -> bool:
    """Return True if token exists, belongs to email, and has not expired."""
    if not token:
        return False
    doc = _tokens().find_one({"token": token, "email": email.lower()})
    if not doc:
        return False
    if doc["expires_at"] < datetime.utcnow():
        _tokens().delete_one({"token": token})
        return False
    return True
