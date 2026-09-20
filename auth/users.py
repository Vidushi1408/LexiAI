# auth/users.py
"""
Local user store: scrypt-hashed passwords, roles, and login throttling.
Kept behind a tiny interface (authenticate / create_user) so an OIDC/SSO provider can replace it later.
"""
import hashlib, hmac, json, os, re, secrets, tempfile, threading, time

from config import settings

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


def _load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(path: str, users: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)          # atomic


def has_users(path: str | None = None) -> bool:
    return bool(_load(path or settings.users_path))


def list_users(path: str | None = None) -> list[dict]:
    return [{"username": u, "role": d["role"]} for u, d in sorted(_load(path or settings.users_path).items())]


def create_user(username: str, password: str, role: str = "analyst", path: str | None = None) -> None:
    """Raises ValueError with a user-presentable message if the input is invalid."""
    path = path or settings.users_path
    username = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9._-]{3,32}", username):
        raise ValueError("Username must be 3-32 characters: letters, digits, dot, dash or underscore.")
    if role not in ROLES:
        raise ValueError(f"Role must be one of {', '.join(ROLES)}.")
    if len(password) < MIN_PASSWORD_LEN:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LEN} characters.")
    with _lock:
        users = _load(path)
        if username in users:
            raise ValueError("That username already exists.")
        users[username] = {"role": role, "password": hash_password(password)}
        _save(path, users)


def authenticate(username: str, password: str, path: str | None = None) -> tuple[dict | None, str]:
    """Returns (user, message). user is {'username', 'role'} on success, else None."""
    username = username.strip().lower()
    now = time.time()
    with _lock:
        fails, locked_until = _failures.get(username, (0, 0.0))
        if locked_until > now:
            return None, f"Too many failed attempts. Try again in {int(locked_until - now) + 1}s."
        record = _load(path or settings.users_path).get(username)
        # verify against a dummy hash for unknown users so timing doesn't reveal which usernames exist
        ok = verify_password(password, record["password"] if record else hash_password("x" * 12, b"\0" * 16))
        if record and ok:
            _failures.pop(username, None)
            return {"username": username, "role": record["role"]}, "ok"
        fails += 1
        _failures[username] = (fails, now + LOCKOUT_SECONDS if fails >= MAX_FAILURES else 0.0)
        return None, "Invalid username or password."


def reset_throttle() -> None:
    _failures.clear()
