import os, json, base64, time
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet

STATE_FILE = os.path.join(os.path.dirname(__file__), ".state.enc")

def _get_key() -> bytes:
    key = os.getenv("ENCRYPTION_KEY", "").strip()
    if not key:
        key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        os.environ["ENCRYPTION_KEY"] = key
    return key.encode()

def _fernet() -> Fernet:
    return Fernet(_get_key())

def save_state(obj: Dict[str, Any]) -> None:
    f = _fernet()
    data = json.dumps(obj, ensure_ascii=False).encode()
    token = f.encrypt(data)
    with open(STATE_FILE, "wb") as fh:
        fh.write(token)

def load_state() -> Dict[str, Any]:
    if not os.path.exists(STATE_FILE):
        return {}
    f = _fernet()
    with open(STATE_FILE, "rb") as fh:
        token = fh.read()
    try:
        data = f.decrypt(token)
        return json.loads(data.decode())
    except Exception:
        return {}

def get_session_cookies() -> Optional[Dict[str, Any]]:
    s = load_state()
    return s.get("cookies")

def set_session_cookies(cookies: Dict[str, Any]) -> None:
    s = load_state()
    s["cookies"] = cookies
    s["last_login_at"] = time.time()
    save_state(s)

def get_last_login_at() -> Optional[float]:
    s = load_state()
    return s.get("last_login_at")
