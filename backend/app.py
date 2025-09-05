import os, json, time
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models import LoginRequest, HealthResponse, ScrapeRequest, UserProfile, SuggestRequest, Suggestion, SendRequest, SendResponse
from auth import login as reddit_login
from storage import get_session_cookies, get_last_login_at, set_session_cookies
from scraper import collect_active_users
from ai import generate_suggestions
from metrics import prometheus_response, REQUEST_LATENCY, MESSAGES_COUNTER, ONLINE_USERS_GAUGE, RECONNECTS

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "example.virtual"), override=False)

app = FastAPI(title="Reddit Outreach Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DRY_RUN = os.getenv("DRY_RUN", "true").lower() == "true"

try:
    PROXIES = json.loads(os.getenv("PROXIES","") or "{}")
except Exception:
    PROXIES = None

@app.get("/metrics")
def metrics():
    data, code, headers = prometheus_response()
    return PlainTextResponse(data, status_code=code, headers=headers)

@app.get("/health", response_model=HealthResponse)
def health():
    cookies = get_session_cookies() or {}
    ll = get_last_login_at()
    return HealthResponse(
        logged_in=bool(cookies),
        last_login_at=None if not ll else __import__("datetime").datetime.fromtimestamp(ll),
        cookie_names=list(cookies.keys())
    )

@app.post("/login")
def login(req: LoginRequest):
    if DRY_RUN:
        set_session_cookies({"reddit_session": "dry-run-cookie"})
        return {"ok": True, "dry_run": True}
    res = reddit_login(req.username, req.password, req.otp, PROXIES)
    if not res.get("ok"):
        raise HTTPException(status_code=400, detail=res)
    return res

@app.post("/scrape")
def scrape(req: ScrapeRequest):
    from time import time as _now
    start = _now()
    sub = req.subreddit if req.subreddit.startswith("r/") else f"r/{req.subreddit}"
    online_window = int(os.getenv("ONLINE_WINDOW_MINUTES", "60"))
    max_users = int(os.getenv("MAX_USERS", "20"))
    users = collect_active_users(sub, online_window_minutes=online_window, max_users=max_users)
    ONLINE_USERS_GAUGE.set(len(users))
    REQUEST_LATENCY.labels(endpoint="/scrape").observe(_now() - start)
    return users

@app.post("/suggest", response_model=List[Suggestion])
def suggest(req: SuggestRequest):
    suggestions = generate_suggestions(req.user.model_dump(), req.history, req.max_suggestions)
    return [Suggestion(**x) for x in suggestions]

_IDEMPOTENCY = {}

@app.post("/send", response_model=SendResponse)
def send(req: SendRequest):
    key = req.idempotency_key
    if key in _IDEMPOTENCY:
        return SendResponse(accepted=True, reason="duplicate")
    if len(req.message) > 1000:
        MESSAGES_COUNTER.labels(status="error").inc()
        raise HTTPException(status_code=429, detail="Message too long")
    _IDEMPOTENCY[key] = {"ts": time.time(), "username": req.username, "message": req.message}
    MESSAGES_COUNTER.labels(status="ok").inc()
    return SendResponse(accepted=True)

@app.get("/ws-ping")
def ws_ping():
    RECONNECTS.inc()
    return {"ok": True, "ts": time.time()}
