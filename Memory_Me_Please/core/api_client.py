import asyncio
import aiohttp
import backoff
from typing import Optional, Dict, List, Any
from config.settings import CONFIG


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
        """Внутренний метод для запросов к API"""
        async with self.semaphore:
            try:
                # Добавляем заголовки, чтобы API не блокировал запросы как "подозрительные"
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
                        print("[WARNING] Rate limited (429), waiting...")
                        raise aiohttp.ClientError("Rate limited")
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"[ERROR] HTTP {response.status} for {endpoint}")
                        return None
                    
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                print(f"[ERROR] Network error: {e}")
                raise
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=CONFIG.max_retries
    )
    async def get_resolved_events(self, limit: int = 100) -> List[Dict]:
        """Получение последних завершенных рынков (новый API)"""
        params = {
            "limit": limit,
            "offset": 0
        }

        
        print(f"[DEBUG] URL: {self.base_url}{CONFIG.events_endpoint}")
        print(f"[DEBUG] Params: {params}")
        
        data = await self._get_with_proxy(CONFIG.events_endpoint, params)
        
        print(f"[DEBUG] Response preview: {str(data)[:300] if data else 'None'}...")
        
        if data is None:
            print("[ERROR] API returned None")
            return []
        
        # Новый API возвращает прямо список или {markets: [...]}
        if isinstance(data, list):
            events = data
        else:
            events = data.get("markets") or data.get("events") or []
        
        print(f"[INFO] Found {len(events)} markets/events")
        return events
    
    @backoff.on_exception(backoff.expo, aiohttp.ClientError, max_tries=3)
    async def get_event_positions(self, event_slug: str) -> List[str]:
        """Получение трейдеров - временно заглушка"""
        print(f"[DEBUG] Skipping {event_slug[:20]}...")
        return []

    
    @backoff.on_exception(backoff.expo, aiohttp.ClientError, max_tries=3)
    async def get_user_stats(self, address: str) -> Optional[Dict]:
        """Получение статистики пользователя"""
        endpoint = f"/portfolio/user/{address}/stats"
        return await self._get_with_proxy(endpoint)
    
    @backoff.on_exception(backoff.expo, aiohttp.ClientError, max_tries=3)
    async def get_portfolio_history(self, address: str) -> Dict[str, Any]:
        """Получение истории позиций"""
        endpoint = f"{CONFIG.positions_endpoint}/{address}"
        data = await self._get_with_proxy(endpoint)
        return {"positions": data.get("positions", [])} if data else {"positions": []}
