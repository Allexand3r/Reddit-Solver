from enum import Enum

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class ProxyRotationMode(str, Enum):
    SEQUENTIAL = "sequential"  # proxy by proxy
    RANDOM = "random"         # random
    FIRST_WORKING = "first_working"  # first_working

class ProxyRequest(BaseModel):
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: Optional[str] = "http"  # http, https, socks5

class LoginRequest(BaseModel):
    username: str
    password: str
    otp: Optional[str] = None
    proxies: Optional[List[ProxyRequest]] = None
    proxy_rotation_mode: Optional[ProxyRotationMode] = ProxyRotationMode.SEQUENTIAL

class HealthResponse(BaseModel):
    logged_in: bool
    last_login_at: Optional[datetime] = None
    cookie_names: List[str] = []

class ScrapeRequest(BaseModel):
    subreddit: str = Field(example="r/programming")
    limit_posts: int = 25

class UserComment(BaseModel):
    permalink: str
    body: str
    created_utc: float

class UserProfile(BaseModel):
    username: str
    last_active_utc: float
    online_within_minutes: int
    comments: List[UserComment]

class SuggestRequest(BaseModel):
    user: UserProfile
    history: List[Dict[str, Any]] = []
    max_suggestions: int = 2

class Suggestion(BaseModel):
    text: str
    score: float

class SendRequest(BaseModel):
    username: str
    message: str
    idempotency_key: str

class SendResponse(BaseModel):
    accepted: bool
    reason: Optional[str] = None
