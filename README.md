# Reddit Outreach Practical Test — Reference Implementation (Python/FastAPI)

## Overview

This project implements an automated outreach system for Reddit, covering everything from programmatic login, scraping active users, generating AI-personalized messages, to (optionally) simulating user behavior via a browser extension.  
The backend is designed for reliability, extensibility, and observability.

---

## Main Components

### 1. Authentication & Session Management

- **Login:**  
  The `/login` endpoint performs programmatic login to Reddit using an HTTP client.
  - With `DRY_RUN=true` (default), login is simulated for safe testing.
  - With `DRY_RUN=false`, a real login flow is executed:
    - Handles CSRF tokens, cookies, and supports SOCKS5/HTTP proxies.
    - Includes a ready-to-integrate CapSolver captcha solving function.
    - Session cookies are securely stored via Fernet encryption (key in `.env`).
- **Session Health:**  
  The `/health` endpoint reports session status, last login time, and stored cookie names.
- **Metrics:**  
  The `/metrics` endpoint exposes Prometheus-format metrics: login attempts, latency, message counts, online users, and WebSocket reconnections.

---

### 2. Scraping & Data Orchestration

- **User Scraping:**  
  The `/scrape` endpoint collects 50–100 users from a selected subreddit (e.g., r/programming) using Reddit’s public JSON API.
  - For each user: extracts username, online estimation, and last 2–3 comments.
  - Filters users: only those active within the last hour, capped at 20 users per run.
  - All parameters are configurable via `.env`.
- **Connection Monitoring:**  
  The `/ws-ping` endpoint simulates a ping/pong to monitor connection status and increments the reconnection counter.

---

### 3. AI-Integrated Message Sender

- **Message Generation:**  
  The `/suggest` endpoint takes a user profile and message history, returning 1–2 personalized outreach suggestions.
  - **Suggestion logic:**  
    - The base version uses template-based keyword matching (e.g., if “Python” is mentioned in comments, the message will reference Python).
    - For production, you can integrate an AI API (OpenAI/Claude) or a local ML model (DistilBERT, GPT-Neo).
  - Each suggestion includes a relevance score (0–1).
- **Send Simulation:**  
  The `/send` endpoint simulates message sending with idempotency (prevents duplicate sends), enforces message length limits, and logs result status.

---

### 4. Proxy Management

- **Supported Proxy Types:**
  - **HTTP** – Standard HTTP proxies.
  - **HTTPS** – Secure HTTP proxies.
  - **SOCKS5** – SOCKS5 proxies with authentication support.

- **Proxy Rotation Modes:**
  - **Sequential:**  
    Proxies are used in order, cycling through the list:
    ```
    Request 1 → Proxy 1
    Request 2 → Proxy 2
    Request 3 → Proxy 3
    Request 4 → Proxy 1 (cycle repeats)
    ```
  - **Random:**  
    A random proxy is selected for each request:
    ```
    Request 1 → Proxy 2 (random)
    Request 2 → Proxy 1 (random)
    Request 3 → Proxy 2 (random, may repeat)
    ```
  - **First Working:**  
    Tests all proxies and uses the first one that works for all requests:
    ```
    Test Proxy 1 → Failed
    Test Proxy 2 → Success ✓
    Use Proxy 2 for all requests
    ```

- Proxies are automatically applied for login and scraping when enabled through environment variables.

### 5. Observability

- **Structured Logging:**  
  All key actions are logged in structured (JSON) format with trace IDs for tracking.
- **Prometheus Metrics:**  
  Metrics are available for monitoring performance, errors, and processed users/messages.
- **Dry-run Feature:**  
  Easily switch between safe simulation and real API calls by toggling `DRY_RUN` in `.env`.

---

### 6. (Bonus) Chrome Extension

- (Optional) Chrome extension or Playwright script:
  - Simulates user clicks inside Reddit threads.
  - Reads DOM and sends extracted data to backend for AI suggestions.
  - Displays 2 AI-generated suggestions in the extension UI.

---

## How to Run

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp example.virtual.example example.virtual
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
- For real Reddit login:  
  Set `DRY_RUN=false` in `.env`, and provide working proxies and CapSolver key.

---

## Docker

```bash
docker build -t reddit-outreach-backend ./backend
docker run -p 8000:8000 --env-file ./backend/example.virtual reddit-outreach-backend
```
Or use docker-compose:

```yaml
version: "3.8"
services:
  backend:
    build: backend
    env_file: backend/example.virtual
    ports: [ "8000:8000" ]
```

---

## API Endpoints Quick Reference

```
GET  /health       # Session status and cookies
GET  /metrics      # Prometheus metrics
POST /login        # Reddit login
POST /scrape       # Scrape active users from subreddit
POST /suggest      # Generate AI message suggestions
POST /send         # Simulate sending a message
GET  /ws-ping      # Connection monitoring
```

---

## Potential Improvements

- Solidify login flow: implement full captcha handling and device fingerprinting.
- Switch to async HTTP (httpx), add retries/backoff.
- Integrate Redis for 24h quotas and message history tracking.
- Add OpenAI/Claude calls for higher-quality personalization.
- Add OpenTelemetry tracing and a dashboard.

---

## AI Approach

The reference implementation uses keyword-matching templates for quick, relevant message generation.  
For production, it is recommended to integrate with an AI API or local ML model for richer personalization.

---


**Login Request Example:**

```jsonc
{
  "username": "your_reddit_username",
  "password": "your_reddit_password",
  "otp": "123456",
  "proxies": [
    {
      "host": "socks5.example.com",
      "port": 1080,
      "username": "proxy_user",
      "password": "proxy_pass",
      "proxy_type": "socks5"
    },
    {
      "host": "http.example.com",
      "port": 8080,
      "proxy_type": "http"
    }
  ],
  "proxy_rotation_mode": "random",
}

