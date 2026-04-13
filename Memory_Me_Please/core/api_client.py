import asyncio
import aiohttp
import backoff
from typing import Optional, Dict, List, Any, Set
from config.settings import CONFIG

# Адреса API
DATA_API = "https://data-api.polymarket.com"
GAMMA_API = "https://gamma-api.polymarket.com"


class PolymarketAPI:
    def __init__(self):
        self.base_url = CONFIG.api_base
        self.semaphore = asyncio.Semaphore(CONFIG.concurrent_requests)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=20)
        self.session = aiohttp.ClientSession(connector=connector)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def _get_with_proxy(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Запросы к Gamma API"""
        async with self.semaphore:
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json'
                }
                
                async with self.session.get(
                    f"{self.base_url}{endpoint}",
                    params=params,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 429:
                        print("[WARNING] Rate limited, waiting...")
                        raise aiohttp.ClientError("Rate limited")
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        return None
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                raise

    # ═══════════════════════════════════════════════════════════════
    # РЕЖИМ 1: Глобальные лидерборды (быстро, 8к трейдеров)
    # ═══════════════════════════════════════════════════════════════
    async def get_global_leaderboard(self, category: str, limit: int = 1000) -> List[Dict]:
        """
        Глобальный лидерборд по категории (все время).
        limit: максимум 1000 (ограничение API)
        """
        url = f"{DATA_API}/v1/leaderboard"
        params = {
            "category": category,
            "timePeriod": "ALL",
            "orderBy": "PNL",
            "limit": min(limit, 1000)  # API не даст больше 1000
        }
        
        print(f"[Global Leaderboard] Загружаю топ-{limit} для {category}...")
        
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and isinstance(data, list):
                        print(f"[Global Leaderboard] Получено {len(data)} трейдеров")
                        return data
                else:
                    print(f"[Global Leaderboard] HTTP {resp.status}")
        except Exception as e:
            print(f"[Global Leaderboard] Error: {e}")
        
        return []

    # ═══════════════════════════════════════════════════════════════
    # РЕЖИМ 2: По событиям (глубоко, больше трейдеров)
    # ═══════════════════════════════════════════════════════════════
    async def get_event_leaderboard(self, condition_id: str, limit: int = 500) -> List[Dict]:
        """
        Лидерборд по конкретному событию (conditionId).
        limit: до 1000, но рекомендую 500 чтобы не перегружать API
        """
        if not condition_id:
            return []
        
        url = f"{DATA_API}/v1/leaderboard"
        params = {
            "conditionId": condition_id,
            "timePeriod": "ALL",
            "orderBy": "PNL",
            "limit": min(limit, 1000)
        }
        
        try:
            async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and isinstance(data, list):
                        return data
                elif resp.status == 429:
                    print(f"[Event Leaderboard] Rate limit, ждем...")
                    await asyncio.sleep(2)
        except Exception as e:
            print(f"[Event Leaderboard] Error: {e}")
        
        return []

    async def get_active_events(self, category: Optional[str] = None, limit: int = 100) -> List[Dict]:
        """Получение активных рынков для режима 'по событиям'"""
        params = {
            "active": "true",
            "closed": "false",
            "limit": limit
        }
        if category:
            params["category"] = category
            
        data = await self._get_with_proxy("/markets", params)
        
        if data:
            markets = data if isinstance(data, list) else data.get("markets", [])
            # Фильтруем только с conditionId
            return [m for m in markets if m.get("conditionId")]
        return []

    # ═══════════════════════════════════════════════════════════════
    # Data API для истории трейдера (используется в обоих режимах)
    # ═══════════════════════════════════════════════════════════════
    async def get_user_activity(self, address: str, max_records: int = 5000) -> List[Dict]:
        """Полная история трейдера (включая закрытые рынки)"""
        url = f"{DATA_API}/activity"
        all_activities = []
        limit = 500
        offset = 0
        
        while len(all_activities) < max_records:
            params = {
                "user": address,
                "limit": limit,
                "offset": offset,
                "sortBy": "TIMESTAMP",
                "sortDirection": "DESC"
            }
            
            try:
                async with self.session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        break
                    
                    data = await resp.json()
                    if not data or len(data) == 0:
                        break
                    
                    all_activities.extend(data)
                    
                    if len(data) < limit:
                        break
                    
                    offset += limit
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                print(f"[Data API Error] {e}")
                break
        
        return all_activities
