from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from config.settings import CONFIG
from core.database import TraderProfile

class SmartMoneyAnalyzer:
    def __init__(self):
        self.category_keywords = {
            "Politics": ["politics", "election", "biden", "trump", "congress", "senate"],
            "Crypto": ["crypto", "bitcoin", "ethereum", "btc", "eth", "defi", "nft"],
            "Sports": ["sports", "nba", "nfl", "football", "soccer", "baseball"],
            "Finance": ["finance", "market", "stock", "sp500", "nasdaq", "trading"]
        }
    
    def calculate_pnl_percent(self, pnl: float, invested: float) -> float:
        if invested == 0:
            return 0.0
        return (pnl / invested) * 100
    
    def stage1_filter(self, data: Dict[str, Any]) -> bool:
        """Stage 1: Базовая фильтрация"""
        trades = data.get("totalTrades", 0)
        win_rate = data.get("winRate", 0)
        pnl = data.get("totalPnl", 0)
        invested = data.get("totalInvested", 1)
        max_loss = abs(data.get("maxLoss", 0))
        events_count = data.get("uniqueEvents", 0)
        avg_bet = data.get("averageBet", 0)
        created_at = data.get("createdAt", "")
        
        # Проверка возраста аккаунта
        try:
            account_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            age_days = (datetime.now() - account_date).days
        except:
            age_days = 0
        
        # Max Loss / PnL ratio
        pnl_ratio = max_loss / pnl if pnl > 0 else float('inf')
        
        checks = {
            "trades": trades >= CONFIG.min_trades,
            "age": age_days >= CONFIG.min_account_age_days,
            "winrate": win_rate >= CONFIG.min_winrate,
            "events": events_count >= CONFIG.min_events_count,
            "avg_bet": avg_bet >= CONFIG.min_avg_bet,
            "pnl_positive": pnl > CONFIG.min_pnl,
            "loss_ratio": pnl_ratio <= CONFIG.max_loss_pnl_ratio
        }
        
        return all(checks.values())
    
    def stage2_identify_niche(self, positions: List[Dict]) -> str:
        """Stage 2: Определение ниши по истории"""
        category_stats = {cat: {"wins": 0, "pnl": 0, "count": 0} 
                         for cat in self.category_keywords.keys()}
        
        for pos in positions:
            market_slug = pos.get("marketSlug", "").lower()
            outcome = pos.get("outcome")
            pnl = pos.get("pnl", 0)
            
            for category, keywords in self.category_keywords.items():
                if any(kw in market_slug for kw in keywords):
                    category_stats[category]["count"] += 1
                    category_stats[category]["pnl"] += pnl
                    if outcome == "YES" and pnl > 0:  # Условная логика победы
                        category_stats[category]["wins"] += 1
        
        # Выбор ниши с лучшим соотношением Winrate + PnL
        best_niche = "General"
        best_score = 0
        
        for cat, stats in category_stats.items():
            if stats["count"] > 0:
                winrate = (stats["wins"] / stats["count"]) * 100
                score = winrate + (stats["pnl"] / 1000)  # Нормализация PnL
                if score > best_score:
                    best_score = score
                    best_niche = cat
        
        return best_niche
    
    def stage3_calculate_score(self, win_rate: float, pnl_percent: float, 
                              trades: int, max_loss: float, pnl: float) -> float:
        """Stage 3: Расчет Smart Money Score"""
        # Нормализация значений
        wr_component = win_rate * 35
        
        pnl_capped = min(pnl_percent, 200)
        pnl_component = (pnl_capped / 2) * 30
        
        trades_capped = min(trades, 200)
        volume_component = (trades_capped / 200) * 100 * 15
        
        # Risk component: (1 - min(max_loss/pnl, 3))/3 * 100 * 20
        ratio = min(max_loss / pnl, 3) if pnl > 0 else 3
        risk_component = ((1 - ratio) / 3) * 100 * 20
        
        return wr_component + pnl_component + volume_component + risk_component
    
    def analyze_trader(self, address: str, stats: Dict, 
                      positions: List[Dict]) -> Optional[TraderProfile]:
        """Полный анализ трейдера"""
        if not self.stage1_filter(stats):
            return None
        
        # Метрики
        trades = stats.get("totalTrades", 0)
        win_rate = stats.get("winRate", 0)
        pnl = stats.get("totalPnl", 0)
        invested = stats.get("totalInvested", 0)
        max_loss = abs(stats.get("maxLoss", 0))
        events_count = stats.get("uniqueEvents", 0)
        avg_bet = stats.get("averageBet", 0)
        username = stats.get("username")
        
        created_at = stats.get("createdAt", "")
        try:
            age_days = (datetime.now() - datetime.fromisoformat(
                created_at.replace('Z', '+00:00'))).days
        except:
            age_days = 90
        
        pnl_percent = self.calculate_pnl_percent(pnl, invested)
        niche = self.stage2_identify_niche(positions)
        score = self.stage3_calculate_score(win_rate, pnl_percent, trades, max_loss, pnl)
        
        return TraderProfile(
            address=address,
            username=username,
            trades=trades,
            win_rate=win_rate,
            pnl=pnl,
            pnl_percent=pnl_percent,
            invested_capital=invested,
            avg_bet=avg_bet,
            events_count=events_count,
            max_loss=max_loss,
            account_age_days=age_days,
            niche=niche,
            score=score,
            last_scan=datetime.now(),
            max_loss_pnl_ratio=max_loss/pnl if pnl > 0 else 0
        )
