import os
from dataclasses import dataclass
from typing import Tuple, Optional, List, Any
from dotenv import load_dotenv

load_dotenv()

@dataclass
class ScannerConfig:
    target_traders: int = int(os.getenv("TARGET_TRADERS", 100))
    max_events: int = int(os.getenv("MAX_EVENTS", 100))
    ttl_days: int = int(os.getenv("TTL_DAYS", 7))
    concurrent_requests: int = int(os.getenv("CONCURRENT_REQUESTS", 5))
    proxy_rotation_interval: int = int(os.getenv("PROXY_ROTATION_INTERVAL", 10))
    
    # API
    api_base: str = os.getenv("API_BASE_URL", "https://gamma-api.polymarket.com")
    events_endpoint: str = os.getenv("API_EVENTS_ENDPOINT", "/events")
    positions_endpoint: str = os.getenv("API_POSITIONS_ENDPOINT", "/positions")
    trades_endpoint: str = os.getenv("API_TRADES_ENDPOINT", "/trades")
    
    # Retry
    max_retries: int = int(os.getenv("MAX_RETRIES", 3))
    retry_delay: float = float(os.getenv("RETRY_DELAY", 2.0))
    rate_limit_pause: int = int(os.getenv("RATE_LIMIT_PAUSE", 60))
    
    # Filters Stage 1
    min_trades: int = int(os.getenv("MIN_TRADES", 20))
    min_account_age_days: int = int(os.getenv("MIN_ACCOUNT_AGE_DAYS", 90))
    min_winrate: float = float(os.getenv("MIN_WINRATE", 55.0))
    min_events_count: int = int(os.getenv("MIN_EVENTS", 3))
    min_avg_bet: float = float(os.getenv("MIN_AVG_BET", 10.0))
    min_pnl: float = float(os.getenv("MIN_PNL", 0.0))
    max_loss_pnl_ratio: float = float(os.getenv("MAX_LOSS_PNL_RATIO", 3.0))


class ProxyManager:
    def __init__(self, filepath: str = "proxies.txt"):
        self.proxies: List[Tuple[str, str]] = []
        self.current_index = 0
        self._load_proxies(filepath)

    def _load_proxies(self, filepath: str):
        if not os.path.exists(filepath):
            return
        
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    parts = line.split(':')
                    if len(parts) == 4:
                        ip, port, user, pwd = parts
                        proxy_url = f"http://{user}:{pwd}@{ip}:{port}"
                        self.proxies.append((proxy_url, line))
                    elif len(parts) == 2:
                        # Формат ip:port без auth
                        ip, port = parts
                        proxy_url = f"http://{ip}:{port}"
                        self.proxies.append((proxy_url, line))
            
            if self.proxies:
                print(f"[INFO] Loaded {len(self.proxies)} proxies")
            else:
                print("[INFO] No proxies loaded, using direct connection")
                
        except Exception as e:
            print(f"[WARNING] Error loading proxies: {e}")

    def get_next(self) -> Tuple[Optional[str], str]:
        if not self.proxies:
            return None, "direct"
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy

    def mark_failed(self, proxy_line: str):
        # Можно реализовать удаление неработающих прокси
        pass


CONFIG = ScannerConfig()
PROXY_MANAGER = ProxyManager()
