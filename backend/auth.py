import os, time, json
import requests
from typing import Dict, Any, Optional, List
from storage import set_session_cookies
from metrics import LOGIN_COUNTER
from proxy_manager import ProxyManager, ProxyConfig, ProxyType, check_socks_support

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
            res = requests.post("https://api.capsolver.com/getTaskResult",
                                json={"clientKey": api_key, "taskId": task_id}, timeout=30).json()
            if res.get("status") == "ready":
                return res["solution"].get("gRecaptchaResponse") or res["solution"].get("token")
        return None
    except Exception:
        return None


def _get_proxy_ip(proxies: Optional[Dict[str, str]]) -> Optional[str]:
    """Получает IP адрес прокси"""
    if not proxies:
        return None
    try:
        response = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=10)
        if response.status_code == 200:
            return response.json().get("origin")
    except requests.exceptions.InvalidSchema as e:
        if "Missing dependencies for SOCKS support" in str(e):
            print("⚠️  For SOCKS5 you have to install: pip install requests[socks]")
        return None
    except Exception:
        pass
    return None


def _create_proxy_manager(proxy_requests: List[Dict], rotation_mode: str) -> Optional[ProxyManager]:
    """Создает менеджер прокси из запроса"""
    if not proxy_requests:
        return None

    has_socks = any(p.get("proxy_type") == "socks5" for p in proxy_requests)
    if has_socks and not check_socks_support():
        raise ValueError("SOCKS5 not installed. Try it: pip install requests[socks]")

    proxy_configs = []
    for proxy_req in proxy_requests:
        proxy_type = ProxyType.HTTP
        if proxy_req.get("proxy_type") == "socks5":
            proxy_type = ProxyType.SOCKS5
        elif proxy_req.get("proxy_type") == "https":
            proxy_type = ProxyType.HTTPS

        config = ProxyConfig(
            host=proxy_req["host"],
            port=proxy_req["port"],
            username=proxy_req.get("username"),
            password=proxy_req.get("password"),
            proxy_type=proxy_type
        )
        proxy_configs.append(config)

    return ProxyManager(proxy_configs)


def login(username: str, password: str, otp: Optional[str],
          proxy_requests: Optional[List[Dict]] = None,
          rotation_mode: str = "sequential",
          use_global_proxies: bool = True) -> Dict[str, Any]:
    proxies_to_use = None
    proxy_info = {}

    try:
        if proxy_requests:
            manager = _create_proxy_manager(proxy_requests, rotation_mode)
            if manager:
                if rotation_mode == "random":
                    proxies_to_use = manager.get_random_proxy()
                elif rotation_mode == "first_working":
                    proxies_to_use = manager.get_working_proxy()
                else:  # sequential
                    proxies_to_use = manager.get_next_proxy()
        elif use_global_proxies:
            from proxy_manager import proxy_manager
            proxies_to_use = proxy_manager.get_next_proxy()

        if proxies_to_use:
            proxy_ip = _get_proxy_ip(proxies_to_use)
            proxy_info = {
                "proxy_config": proxies_to_use,
                "proxy_ip": proxy_ip,
                "rotation_mode": rotation_mode
            }
            print(f"Used: {proxies_to_use}")
            if proxy_ip:
                print(f"IP proxy: {proxy_ip}")
        else:
            print("Proxy not used")

    except ValueError as e:
        return {
            "ok": False,
            "error": str(e),
            "proxy_info": {
                "proxy_config": proxy_requests[0] if proxy_requests else None,
                "proxy_ip": None,
                "rotation_mode": rotation_mode
            }
        }

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko)",
        "Referer": REDDIT_LOGIN_URL,
        "Origin": "https://www.reddit.com"
    })

    if proxies_to_use:
        s.proxies.update(proxies_to_use)

    try:
        r = s.get(REDDIT_LOGIN_URL, timeout=30)
        r.raise_for_status()
        csrf_token = s.cookies.get("csrf_token") or ""
        captcha_token = None
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

        if ok:
            if proxies_to_use and proxy_info.get("proxy_ip"):
                print(f"✅ Login success {rotation_mode} proxy with IP: {proxy_info['proxy_ip']}")
            else:
                print("✅ Login success without proxy")

        result = {
            "ok": ok,
            "status_code": r2.status_code,
            "cookies": requests.utils.dict_from_cookiejar(s.cookies)
        }

        if proxy_info:
            result["proxy_info"] = proxy_info

        return result

    except requests.exceptions.InvalidSchema as e:
        if "Missing dependencies for SOCKS support" in str(e):
            error_msg = "Missing dependencies for SOCKS support."
        else:
            error_msg = str(e)

        LOGIN_COUNTER.labels(status="error").inc()
        error_result = {"ok": False, "error": error_msg}
        if proxy_info:
            error_result["proxy_info"] = proxy_info
        return error_result

    except Exception as e:
        LOGIN_COUNTER.labels(status="error").inc()
        error_result = {"ok": False, "error": str(e)}
        if proxy_info:
            error_result["proxy_info"] = proxy_info
        return error_result