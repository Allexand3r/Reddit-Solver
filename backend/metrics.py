from prometheus_client import Counter, Histogram, Gauge
from datetime import datetime

# --- твои метрики ---
LOGIN_COUNTER = Counter("reddit_logins_total", "Number of login attempts", ["status"])
REQUEST_LATENCY = Histogram("request_latency_seconds", "Request latency", ["endpoint"])
MESSAGES_COUNTER = Counter("messages_processed_total", "Messages processed", ["status"])
RECONNECTS = Counter("reconnections_total", "Number of reconnections")
ONLINE_USERS_GAUGE = Gauge("online_users", "Users detected online")

def format_timestamp(ts: float) -> str:
    if not ts:
        return "N/A"
    dt = datetime.utcfromtimestamp(ts)
    return dt.strftime("%Y-%m-%d %H:%M:%S (UTC)")

def prometheus_response() -> tuple[bytes, int, dict]:
    """
    Возвращает только кастомные метрики в формате Prometheus text.
    Дата для reconnections_created сразу читаемая.
    """
    login_success = LOGIN_COUNTER.labels(status="success")._value.get() or 0
    reconnects = RECONNECTS._value.get() or 0
    online_users = ONLINE_USERS_GAUGE._value.get() or 0
    try:
        reconnects_created_ts = RECONNECTS_CREATED._value.get() or 0
        reconnects_created_str = format_timestamp(reconnects_created_ts)
    except Exception:
        reconnects_created_str = "N/A"

    output = [
        f'reddit_logins_total{{status="success"}} {login_success}',
        f'reconnections_total {reconnects}',
        f'reconnections_created {reconnects_created_str}',
        f'online_users {online_users}',
    ]

    text = "\n".join(output).encode()
    return text, 200, {"Content-Type": "text/plain"}