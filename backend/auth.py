import os, time, json
import requests
from typing import Dict, Any, Optional
from storage import set_session_cookies
from metrics import LOGIN_COUNTER

REDDIT_LOGIN_URL = "https://www.reddit.com/login"

def _solve_captcha(site_key: str, url: str) -> Optional[str]:
    api_key = os.getenv("CAPSOLVER_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        task_payload = {
            "clientKey": api_key,
            "task": {
                "type": "HCaptchaTaskProxyless",
                "websiteURL": url,
                "websiteKey": site_key
            }
        }
        create = requests.post("https://api.capsolver.com/createTask", json=task_payload, timeout=30).json()
        task_id = create.get("taskId")
        if not task_id:
            return None
        for _ in range(60):
            time.sleep(2)
            res = requests.post("https://api.capsolver.com/getTaskResult", json={"clientKey": api_key, "taskId": task_id}, timeout=30).json()
            if res.get("status") == "ready":
                return res["solution"].get("gRecaptchaResponse") or res["solution"].get("token")
        return None
    except Exception:
        return None

def login(username: str, password: str, otp: Optional[str], proxies: Optional[Dict[str,str]] = None) -> Dict[str, Any]:
    # Demonstration of CSRF + cookies web-login attempt; set DRY_RUN=false to try real call.
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)",
        "Referer": REDDIT_LOGIN_URL,
        "Origin": "https://www.reddit.com"
    })
    if proxies:
        s.proxies.update(proxies)
    try:
        r = s.get(REDDIT_LOGIN_URL, timeout=30)
        r.raise_for_status()
        csrf_token = s.cookies.get("csrf_token") or ""
        captcha_token = None  # _solve_captcha(site_key="SITE_KEY_PLACEHOLDER", url=REDDIT_LOGIN_URL)
        payload = {
            "csrf_token": csrf_token,
            "otp": otp or "",
            "password": password,
            "dest": "https://www.reddit.com",
            "username": username,
            "captcha": captcha_token or ""
        }
        r2 = s.post(REDDIT_LOGIN_URL, data=payload, timeout=30, allow_redirects=True)
        ok = ("reddit_session" in s.cookies) or (r2.status_code in (200, 302))
        status = "success" if ok else "failure"
        LOGIN_COUNTER.labels(status=status).inc()
        set_session_cookies(requests.utils.dict_from_cookiejar(s.cookies))
        return {"ok": ok, "status_code": r2.status_code, "cookies": requests.utils.dict_from_cookiejar(s.cookies)}
    except Exception as e:
        LOGIN_COUNTER.labels(status="error").inc()
        return {"ok": False, "error": str(e)}
