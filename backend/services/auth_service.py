"""Local account sessions. Keep the database outside the source checkout."""
import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from pathlib import Path
from contextlib import contextmanager


@contextmanager
def connect():
    path = Path(os.environ.get("ONAIR_AUTH_DB", str(Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "ON-AIR" / "accounts.sqlite3")))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, salt TEXT NOT NULL, password_hash TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires REAL NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS guest_sessions (token_hash TEXT PRIMARY KEY, guest_id TEXT NOT NULL, expires REAL NOT NULL)")
    try:
        yield db
        db.commit()
    finally:
        db.close()


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 600000).hex()


def register(username, password):
    salt = secrets.token_hex(16)
    hashed = password_hash(password, salt)
    with connect() as db:
        db.execute("INSERT INTO users (username,salt,password_hash) VALUES (?,?,?)", (username, salt, hashed))


def authenticate(username, password):
    with connect() as db:
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    # Keep the expensive operation even for unknown accounts.
    candidate = password_hash(password, user["salt"] if user else "00" * 16)
    return dict(user) if user and hmac.compare_digest(candidate, user["password_hash"]) else None


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    with connect() as db:
        db.execute("DELETE FROM sessions WHERE expires < ?", (time.time(),))
        db.execute("INSERT INTO sessions VALUES (?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), user_id, time.time() + 7 * 86400))
    return token


def current_user(token):
    if not token:
        return None
    with connect() as db:
        user = db.execute("SELECT u.id,u.username FROM users u JOIN sessions s ON u.id=s.user_id WHERE s.token_hash=? AND s.expires>?", (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
        if not user:
            guest = db.execute("SELECT guest_id FROM guest_sessions WHERE token_hash=? AND expires>?", (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
            if guest:
                return {"id": guest["guest_id"], "username": "게스트", "isGuest": True}
    return dict(user) if user else None


def create_guest_session():
    token = secrets.token_urlsafe(32)
    guest_id = "guest-" + secrets.token_hex(16)
    with connect() as db:
        db.execute("DELETE FROM guest_sessions WHERE expires < ?", (time.time(),))
        db.execute("INSERT INTO guest_sessions VALUES (?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), guest_id, time.time() + 86400))
    return token, {"id": guest_id, "username": "게스트", "isGuest": True}


def logout(token):
    with connect() as db:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256((token or "").encode()).hexdigest(),))
        db.execute("DELETE FROM guest_sessions WHERE token_hash=?", (hashlib.sha256((token or "").encode()).hexdigest(),))
