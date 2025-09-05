import time
from typing import Dict, Any, List
import requests

REDDIT_BASE = "https://www.reddit.com"

def _now() -> float:
    return time.time()

def _headers() -> Dict[str,str]:
    return {
        "User-Agent": "reddit-outreach-bot/0.1 (by u/tester)",
        "Accept": "application/json"
    }

def fetch_new_posts(subreddit: str, limit: int = 25) -> List[Dict[str, Any]]:
    url = f"{REDDIT_BASE}/{subreddit}/new.json?limit={limit}"
    r = requests.get(url, headers=_headers(), timeout=30)
    r.raise_for_status()
    data = r.json()
    return [c["data"] for c in data.get("data", {}).get("children", [])]

def fetch_comments(post_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    url = f"{REDDIT_BASE}/comments/{post_id}.json?limit={limit}&sort=new"
    r = requests.get(url, headers=_headers(), timeout=30)
    r.raise_for_status()
    data = r.json()
    if not isinstance(data, list) or len(data) < 2:
        return []
    comments = data[1].get("data", {}).get("children", [])
    out = []
    for c in comments:
        d = c.get("data", {})
        if d.get("author") and not str(d.get("author")).startswith("[deleted]"):
            out.append(d)
    return out

def collect_active_users(subreddit: str, online_window_minutes: int = 60, max_users: int = 20) -> List[Dict[str, Any]]:
    posts = fetch_new_posts(subreddit, limit=25)
    users: Dict[str, Dict[str, Any]] = {}
    now = _now()
    for p in posts:
        post_id = p.get("id")
        if not post_id:
            continue
        comments = fetch_comments(post_id, limit=100)
        for d in comments:
            author = d.get("author")
            created_utc = d.get("created_utc", 0)
            if not author:
                continue
            entry = users.setdefault(author, {"username": author, "comments": [], "last_active_utc": 0})
            entry["comments"].append({
                "permalink": f"{REDDIT_BASE}{d.get('permalink','')}",
                "body": d.get("body","")[:400],
                "created_utc": created_utc
            })
            entry["last_active_utc"] = max(entry["last_active_utc"], created_utc)
    active: List[Dict[str, Any]] = []
    for u in users.values():
        minutes = (now - u["last_active_utc"]) / 60.0 if u["last_active_utc"] else 10**9
        if minutes <= online_window_minutes:
            u["online_within_minutes"] = int(minutes)
            u["comments"] = sorted(u["comments"], key=lambda x: x["created_utc"], reverse=True)[:3]
            active.append(u)
    active = sorted(active, key=lambda x: x["last_active_utc"], reverse=True)[:max_users]
    return active
