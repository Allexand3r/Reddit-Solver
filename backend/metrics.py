from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

LOGIN_COUNTER = Counter("reddit_logins_total", "Number of login attempts", ["status"])
REQUEST_LATENCY = Histogram("request_latency_seconds", "Request latency", ["endpoint"])
MESSAGES_COUNTER = Counter("messages_processed_total", "Messages processed", ["status"])
RECONNECTS = Counter("reconnections_total", "Number of reconnections", [])
ONLINE_USERS_GAUGE = Gauge("online_users", "Users detected online")

def prometheus_response():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}
