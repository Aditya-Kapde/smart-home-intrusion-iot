"""
db.py - MongoDB connection and user/device-token DAL
====================================================
All database operations are centralized here so routes.py
stays clean. When MongoDB is unavailable, the module falls
back to a local JSON store so the demo can continue working.
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta
from secrets import randbelow

import certifi
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

_client: MongoClient | None = None
_LOCAL_LOCK = threading.Lock()
_WARNED_FALLBACK_KEYS: set[str] = set()
LOCAL_AUTH_FILE = os.path.join(os.path.dirname(__file__), "local_auth_store.json")
_DB_DISABLED_UNTIL = 0.0
_DB_LAST_ERROR: Exception | None = None


def _mongo_cooldown_seconds() -> float:
    return max(5.0, float(os.getenv("MONGO_FALLBACK_COOLDOWN_SECONDS", "30")))


def _mongo_is_temporarily_disabled() -> bool:
    return time.monotonic() < _DB_DISABLED_UNTIL


def _record_mongo_failure(exc: Exception) -> None:
    global _client, _DB_DISABLED_UNTIL, _DB_LAST_ERROR
    _client = None
    _DB_LAST_ERROR = exc
    _DB_DISABLED_UNTIL = time.monotonic() + _mongo_cooldown_seconds()


def _warn_local_fallback_once(key: str, exc: Exception) -> None:
    if key in _WARNED_FALLBACK_KEYS:
        return
    _WARNED_FALLBACK_KEYS.add(key)
    print(f"[WARNING] MongoDB unavailable for {key}. Falling back to local auth store: {exc}")


def _iso_or_none(value):
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _dt_or_none(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _default_local_store() -> dict:
    return {
        "users": [],
        "device_tokens": [],
        "app_settings": {},
    }


def _load_local_store() -> dict:
    with _LOCAL_LOCK:
        try:
            with open(LOCAL_AUTH_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return _default_local_store()
            base = _default_local_store()
            base.update(data)
            return base
        except (FileNotFoundError, json.JSONDecodeError):
            return _default_local_store()


def _save_local_store(data: dict) -> None:
    with _LOCAL_LOCK:
        with open(LOCAL_AUTH_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def _local_find_user(email: str) -> dict | None:
    target = email.lower()
    store = _load_local_store()
    for user in store["users"]:
        if str(user.get("email", "")).lower() == target:
            return dict(user)
    return None


def _local_upsert_user(doc: dict) -> dict:
    store = _load_local_store()
    users = store["users"]
    email = str(doc.get("email", "")).lower()
    for idx, user in enumerate(users):
        if str(user.get("email", "")).lower() == email:
            users[idx] = dict(doc)
            _save_local_store(store)
            return {"email": email, "display_name": doc.get("display_name", ""), "role": doc.get("role", "user")}
    users.append(dict(doc))
    _save_local_store(store)
    return {"email": email, "display_name": doc.get("display_name", ""), "role": doc.get("role", "user")}


def get_db():
    """Return the MongoDB database handle, creating the connection on first call."""
    global _client
    if _mongo_is_temporarily_disabled():
        raise RuntimeError(f"MongoDB temporarily disabled after recent failure: {_DB_LAST_ERROR}")
    if _client is None:
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        name = os.getenv("MONGO_DB_NAME", "shieldhome")

        client_kwargs = {
            "serverSelectionTimeoutMS": int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "2000")),
            "connectTimeoutMS": int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "2000")),
            "socketTimeoutMS": int(os.getenv("MONGO_SOCKET_TIMEOUT_MS", "5000")),
        }

        if uri.startswith("mongodb+srv://") or "tls=true" in uri.lower() or "ssl=true" in uri.lower():
            client_kwargs["tls"] = True
            client_kwargs["tlsCAFile"] = certifi.where()

        try:
            _client = MongoClient(uri, **client_kwargs)
            db = _client[name]
            db["users"].create_index("email", unique=True)
            db["device_tokens"].create_index("token", unique=True)
            db["device_tokens"].create_index("expires_at", expireAfterSeconds=0)
        except Exception as exc:
            _record_mongo_failure(exc)
            raise
    return _client[os.getenv("MONGO_DB_NAME", "shieldhome")]


def _users():
    return get_db()["users"]


def _tokens():
    return get_db()["device_tokens"]


def _app_settings():
    return get_db()["app_settings"]


def find_user(email: str) -> dict | None:
    """Return user document (without _id) or None."""
    try:
        return _users().find_one({"email": email.lower()}, {"_id": 0})
    except Exception as exc:
        _warn_local_fallback_once("find_user", exc)
        return _local_find_user(email)


def get_user_profile(email: str) -> dict | None:
    """Return safe user info (no password) or None."""
    try:
        doc = _users().find_one(
            {"email": email.lower()},
            {"_id": 0, "password": 0}
        )
        if doc and "created_at" in doc:
            doc["created_at"] = doc["created_at"].isoformat()
        if doc and "last_login" in doc:
            doc["last_login"] = doc["last_login"].isoformat()
        return doc
    except Exception as exc:
        _warn_local_fallback_once("get_user_profile", exc)
        doc = _local_find_user(email)
        if not doc:
            return None
        doc.pop("password", None)
        doc["created_at"] = _iso_or_none(doc.get("created_at"))
        doc["last_login"] = _iso_or_none(doc.get("last_login"))
        return doc


def create_user(email: str, password: str, display_name: str = "", role: str = "user") -> dict:
    """Insert a new user. Raises ValueError if email already exists."""
    email = email.lower().strip()
    display_name = display_name.strip() or email.split("@")[0]
    doc = {
        "email": email,
        "password": password,
        "display_name": display_name,
        "role": role,
        "created_at": datetime.utcnow(),
        "last_login": None,
        "login_count": 0,
    }
    try:
        _users().insert_one(doc)
    except DuplicateKeyError:
        raise ValueError("Email already registered.")
    except Exception as exc:
        _warn_local_fallback_once("create_user", exc)
        if _local_find_user(email):
            raise ValueError("Email already registered.")
        local_doc = dict(doc)
        local_doc["created_at"] = _iso_or_none(local_doc["created_at"])
        local_doc["last_login"] = _iso_or_none(local_doc["last_login"])
        return _local_upsert_user(local_doc)
    return {"email": email, "display_name": display_name, "role": role}


def update_user_login(email: str) -> None:
    """Stamp last_login and increment login_count after successful login."""
    try:
        _users().update_one(
            {"email": email.lower()},
            {
                "$set": {"last_login": datetime.utcnow()},
                "$inc": {"login_count": 1},
            },
        )
    except Exception as exc:
        _warn_local_fallback_once("update_user_login", exc)
        store = _load_local_store()
        target = email.lower()
        for user in store["users"]:
            if str(user.get("email", "")).lower() == target:
                user["last_login"] = datetime.utcnow().isoformat()
                user["login_count"] = int(user.get("login_count", 0) or 0) + 1
                _save_local_store(store)
                return


def list_alert_recipients() -> list[str]:
    """Return preferred email recipients for intrusion alerts."""
    try:
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
    except Exception as exc:
        _warn_local_fallback_once("list_alert_recipients", exc)
        store = _load_local_store()
        priority = [
            str(user.get("email", "")).strip().lower()
            for user in store["users"]
            if str(user.get("role", "")).lower() in {"security", "admin"} and user.get("email")
        ]
        if priority:
            return sorted(set(priority))
        emails = [str(user.get("email", "")).strip().lower() for user in store["users"] if user.get("email")]
        return sorted(set(emails))


def set_active_alert_recipient(email: str) -> None:
    """Persist the most recently authenticated dashboard user for alert delivery."""
    normalized = str(email or "").strip().lower()
    if not normalized:
        return
    try:
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
    except Exception as exc:
        _warn_local_fallback_once("set_active_alert_recipient", exc)
        store = _load_local_store()
        store["app_settings"]["active_alert_recipient"] = {
            "email": normalized,
            "updated_at": datetime.utcnow().isoformat(),
        }
        _save_local_store(store)


def get_active_alert_recipient() -> str | None:
    """Return the most recent dashboard login email used for alert delivery."""
    try:
        doc = _app_settings().find_one({"key": "active_alert_recipient"}, {"_id": 0, "email": 1})
        if not doc:
            return None
        email = str(doc.get("email", "")).strip().lower()
        return email or None
    except Exception as exc:
        _warn_local_fallback_once("get_active_alert_recipient", exc)
        store = _load_local_store()
        doc = store["app_settings"].get("active_alert_recipient", {})
        email = str(doc.get("email", "")).strip().lower()
        return email or None


def seed_default_users():
    """Insert demo accounts if the store is empty."""
    defaults = [
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
    ]
    try:
        if _users().count_documents({}) == 0:
            for user in defaults:
                try:
                    _users().insert_one(user)
                except DuplicateKeyError:
                    pass
    except Exception as exc:
        _warn_local_fallback_once("seed_default_users", exc)
        store = _load_local_store()
        if not store["users"]:
            for user in defaults:
                local_user = dict(user)
                local_user["created_at"] = _iso_or_none(local_user["created_at"])
                local_user["last_login"] = None
                local_user["login_count"] = 0
                store["users"].append(local_user)
            _save_local_store(store)


def create_device_token(email: str, days: int = 30) -> str:
    """Persist a new device token; returns the token string."""
    token = f"dev_{randbelow(10**12):012d}"
    expires = datetime.utcnow() + timedelta(days=days)
    try:
        _tokens().insert_one({
            "token": token,
            "email": email.lower(),
            "expires_at": expires,
            "created_at": datetime.utcnow(),
        })
    except Exception as exc:
        _warn_local_fallback_once("create_device_token", exc)
        store = _load_local_store()
        store["device_tokens"].append({
            "token": token,
            "email": email.lower(),
            "expires_at": expires.isoformat(),
            "created_at": datetime.utcnow().isoformat(),
        })
        _save_local_store(store)
    return token


def verify_device_token(token: str, email: str) -> bool:
    """Return True if token exists, belongs to email, and has not expired."""
    if not token:
        return False
    try:
        doc = _tokens().find_one({"token": token, "email": email.lower()})
        if not doc:
            return False
        if doc["expires_at"] < datetime.utcnow():
            _tokens().delete_one({"token": token})
            return False
        return True
    except Exception as exc:
        _warn_local_fallback_once("verify_device_token", exc)
        store = _load_local_store()
        now = datetime.utcnow()
        kept_tokens = []
        valid = False
        for doc in store["device_tokens"]:
            expires_at = _dt_or_none(doc.get("expires_at"))
            if expires_at and expires_at >= now:
                kept_tokens.append(doc)
                if doc.get("token") == token and str(doc.get("email", "")).lower() == email.lower():
                    valid = True
        store["device_tokens"] = kept_tokens
        _save_local_store(store)
        return valid
