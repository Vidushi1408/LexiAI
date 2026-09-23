# auth/users.py
"""
User store: scrypt-hashed passwords, roles, API keys and login throttling — backed by the
`users` table (db.py), Postgres in production. Kept behind a small interface (authenticate /
create_user) so an OIDC/SSO provider could replace it later.
"""
import hashlib, hmac, re, secrets, threading, time

from sqlalchemy.orm import Session

from db import User, new_session

ROLES = ("viewer", "analyst", "admin")
MIN_PASSWORD_LEN = 10
MAX_FAILURES, LOCKOUT_SECONDS = 5, 60

_lock = threading.Lock()
_failures: dict[str, tuple[int, float]] = {}   # username -> (consecutive failures, locked_until)


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$")
        assert scheme == "scrypt"
        expected = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(expected.hex(), digest_hex)
    except (ValueError, AssertionError):
        return False


def _session(session: Session | None):
    """Returns (session, owns_it) — a caller-supplied session is left open for them to reuse/close."""
    return (session, False) if session is not None else (new_session(), True)


def has_users(session: Session | None = None) -> bool:
    s, owns = _session(session)
    try:
        return s.query(User.username).first() is not None
    finally:
        if owns:
            s.close()


def list_users(session: Session | None = None) -> list[dict]:
    s, owns = _session(session)
    try:
        rows = s.query(User).order_by(User.username).all()
        return [{"username": u.username, "role": u.role} for u in rows]
    finally:
        if owns:
            s.close()


def create_user(username: str, password: str, role: str = "analyst", session: Session | None = None) -> None:
    """Raises ValueError with a user-presentable message if the input is invalid."""
    username = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9._-]{3,32}", username):
        raise ValueError("Username must be 3-32 characters: letters, digits, dot, dash or underscore.")
    if role not in ROLES:
        raise ValueError(f"Role must be one of {', '.join(ROLES)}.")
    if len(password) < MIN_PASSWORD_LEN:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LEN} characters.")
    s, owns = _session(session)
    try:
        with _lock:
            if s.get(User, username) is not None:
                raise ValueError("That username already exists.")
            s.add(User(username=username, role=role, password_hash=hash_password(password)))
            s.commit()
    finally:
        if owns:
            s.close()


def authenticate(username: str, password: str, session: Session | None = None) -> tuple[dict | None, str]:
    """Returns (user, message). user is {'username', 'role'} on success, else None."""
    username = username.strip().lower()
    now = time.time()
    s, owns = _session(session)
    try:
        with _lock:
            fails, locked_until = _failures.get(username, (0, 0.0))
            if locked_until > now:
                return None, f"Too many failed attempts. Try again in {int(locked_until - now) + 1}s."
            record = s.get(User, username)
            # verify against a dummy hash for unknown users so timing doesn't reveal which usernames exist
            ok = verify_password(password, record.password_hash if record else hash_password("x" * 12, b"\0" * 16))
            if record and ok:
                _failures.pop(username, None)
                return {"username": username, "role": record.role}, "ok"
            fails += 1
            _failures[username] = (fails, now + LOCKOUT_SECONDS if fails >= MAX_FAILURES else 0.0)
            return None, "Invalid username or password."
    finally:
        if owns:
            s.close()


def _fast_hash(key: str) -> str:
    """SHA-256, not scrypt — API keys are high-entropy random tokens, not user-chosen passwords,
    so there is nothing to slow a guesser down for, and this lets lookup be a single indexed
    equality query instead of an O(n) scrypt verify against every user with a key set."""
    return hashlib.sha256(key.encode()).hexdigest()


def set_api_key(username: str, session: Session | None = None) -> str:
    """Generates a new API key for `username`, replacing any previous one. Returns the raw key —
    shown to the user exactly once; only its hash is stored."""
    key = "lexi_" + secrets.token_urlsafe(32)
    s, owns = _session(session)
    try:
        user = s.get(User, username)
        if user is None:
            raise ValueError("No such user.")
        user.api_key_hash = _fast_hash(key)
        s.commit()
        return key
    finally:
        if owns:
            s.close()


def authenticate_api_key(key: str, session: Session | None = None) -> dict | None:
    """Returns {'username', 'role'} for a valid API key, else None."""
    if not key or not key.startswith("lexi_"):
        return None
    s, owns = _session(session)
    try:
        user = s.query(User).filter(User.api_key_hash == _fast_hash(key)).first()
        return {"username": user.username, "role": user.role} if user else None
    finally:
        if owns:
            s.close()


def reset_throttle() -> None:
    _failures.clear()
