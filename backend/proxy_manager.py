import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import random


class ProxyType(Enum):
    HTTP = "http"
    HTTPS = "https"
    SOCKS5 = "socks5"


@dataclass
class ProxyConfig:
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    proxy_type: ProxyType = ProxyType.HTTP

    def to_dict(self) -> Dict[str, str]:
        if self.username and self.password:
            auth = f"{self.username}:{self.password}@"
        else:
            auth = ""

        proxy_url = f"{self.proxy_type.value}://{auth}{self.host}:{self.port}"

        return {
            "http": proxy_url,
            "https": proxy_url
        }


class ProxyManager:
    def __init__(self, proxies: List[ProxyConfig]):
        self.proxies = proxies
        self.current_index = 0

    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Получить следующий прокси в ротации"""
        if not self.proxies:
            return None

        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy.to_dict()

    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        """Получить случайный прокси"""
        if not self.proxies:
            return None

        proxy = random.choice(self.proxies)
        return proxy.to_dict()

    def get_working_proxy(self) -> Optional[Dict[str, str]]:
        """Найти рабочий прокси, проверив каждый"""
        for proxy_config in self.proxies:
            proxy_dict = proxy_config.to_dict()
            if self._test_proxy(proxy_dict):
                return proxy_dict
        return None

    def _test_proxy(self, proxy_dict: Dict[str, str]) -> bool:
        """Проверить работоспособность прокси"""
        try:
            response = requests.get(
                "https://httpbin.org/ip",
                proxies=proxy_dict,
                timeout=10
            )
            return response.status_code == 200
        except requests.exceptions.InvalidSchema as e:
            if "Missing dependencies for SOCKS support" in str(e):
                print("⚠️  SOCKS pip install requests[socks]")
                return False
        except Exception as e:
            print(f"Error: {e}")
            return False
        return False


def check_socks_support():
    """Проверить поддержку SOCKS"""
    try:
        import socks
        return True
    except ImportError:
        return False