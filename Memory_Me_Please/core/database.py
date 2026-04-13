import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

@dataclass
class TraderProfile:
    address: str
    username: Optional[str]
    trades: int
    win_rate: float
    pnl: float
    pnl_percent: float
    invested_capital: float
    avg_bet: float
    events_count: int
    max_loss: float
    account_age_days: int
    niche: str
    score: float
    last_scan: datetime
    max_loss_pnl_ratio: float

class DatabaseManager:
    def __init__(self, db_path: str = "polymarket_traders.db"):
        self.db_path = db_path
    
    async def init_tables(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS traders (
                    address TEXT PRIMARY KEY,
                    username TEXT,
                    trades INTEGER,
                    win_rate REAL,
                    pnl REAL,
                    pnl_percent REAL,
                    invested_capital REAL,
                    avg_bet REAL,
                    events_count INTEGER,
                    max_loss REAL,
                    account_age_days INTEGER,
                    niche TEXT,
                    score REAL,
                    last_scan TIMESTAMP,
                    max_loss_pnl_ratio REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS blacklist (
                    address TEXT PRIMARY KEY,
                    reason TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS scan_progress (
                    id INTEGER PRIMARY KEY CHECK (id = 0),
                    current_event_index INTEGER DEFAULT 0,
                    total_events INTEGER DEFAULT 0,
                    session_start TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS events_cache (
                    event_id TEXT PRIMARY KEY,
                    slug TEXT,
                    category TEXT,
                    status TEXT,
                    resolved_at TIMESTAMP,
                    scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            await db.commit()
    
    async def should_scan_trader(self, address: str, ttl_days: int) -> bool:
        """Проверка TTL: если прошло < 7 дней - пропускаем"""
        async with aiosqlite.connect(self.db_path) as db:
            # Проверяем blacklist
            cursor = await db.execute(
                "SELECT 1 FROM blacklist WHERE address = ?", (address,)
            )
            if await cursor.fetchone():
                return False
            
            # Проверяем существующую запись и дату
            cursor = await db.execute(
                "SELECT last_scan FROM traders WHERE address = ?", (address,)
            )
            row = await cursor.fetchone()
            
            if not row:
                return True
            
            last_scan = datetime.fromisoformat(row[0].replace('Z', '+00:00'))
            cutoff_date = datetime.now() - timedelta(days=ttl_days)
            
            return last_scan < cutoff_date
    
    async def get_scan_progress(self) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT current_event_index, total_events, session_start FROM scan_progress WHERE id = 0"
            )
            row = await cursor.fetchone()
            if row:
                return {
                    "current_index": row[0],
                    "total": row[1],
                    "session_start": row[2]
                }
            return None
    
    async def update_progress(self, current_index: int, total: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO scan_progress (id, current_event_index, total_events, session_start)
                VALUES (0, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    current_event_index = excluded.current_event_index,
                    total_events = excluded.total_events,
                    updated_at = CURRENT_TIMESTAMP
            """, (current_index, total))
            await db.commit()
    
    async def save_trader(self, profile: TraderProfile):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO traders (
                    address, username, trades, win_rate, pnl, pnl_percent,
                    invested_capital, avg_bet, events_count, max_loss,
                    account_age_days, niche, score, last_scan, max_loss_pnl_ratio
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.address, profile.username, profile.trades,
                profile.win_rate, profile.pnl, profile.pnl_percent,
                profile.invested_capital, profile.avg_bet, profile.events_count,
                profile.max_loss, profile.account_age_days, profile.niche,
                profile.score, datetime.now().isoformat(), profile.max_loss_pnl_ratio
            ))
            await db.commit()
    
    async def add_to_blacklist(self, address: str, reason: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO blacklist (address, reason) VALUES (?, ?)",
                (address, reason)
            )
            await db.commit()
    
    async def get_traders_count_since(self, since: datetime) -> int:
        """Количество трейдеров, обновленных с начала сессии"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM traders WHERE last_scan > ?",
                (since.isoformat(),)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
    
    async def get_top_traders(self, limit: int = 100) -> List[TraderProfile]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT address, username, trades, win_rate, pnl, pnl_percent,
                       invested_capital, avg_bet, events_count, max_loss,
                       account_age_days, niche, score, last_scan, max_loss_pnl_ratio
                FROM traders ORDER BY score DESC LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            return [TraderProfile(*row) for row in rows]
