from typing import Dict, List, Any, Optional
from collections import defaultdict
from datetime import datetime
from core.database import TraderProfile

class SmartMoneyAnalyzer:
    def __init__(self):
        self.category_keywords = {
            "Politics": ["politics", "election", "biden", "trump", "congress", "senate"],
            "Crypto": ["crypto", "bitcoin", "ethereum", "btc", "eth", "defi", "nft"],
            "Sports": ["sports", "nba", "nfl", "football", "soccer", "baseball"],
            "Finance": ["finance", "market", "stock", "sp500", "nasdaq", "trading"],
            "Economics": ["economics", "fed", "inflation", "recession"],
            "Culture": ["culture", "entertainment", "music", "awards"],
            "Tech": ["tech", "technology", "ai", "software"],
            "Weather": ["weather", "climate", "temperature"]
        }

    def analyze_from_activities(self, address: str, activities: List[Dict]) -> Optional[TraderProfile]:
        print(f"[DEBUG] Анализирую {len(activities)} записей")
        if activities:
            sample = activities[0]
            print(f"[DEBUG] Первая запись: type={sample.get('type')}, PnL={sample.get('realizedPnl')}")

        if not activities or len(activities) < 3:
            return None
        
        # Фильтруем только TRADE
        trades = [a for a in activities if a.get("type") == "TRADE"]
        
        if len(trades) < 3:
            print(f"  [Отсеяно] Мало TRADE: {len(trades)}")
            return None
        
        # Группируем по рынкам
        market_trades = defaultdict(list)
        for trade in trades:
            slug = trade.get("slug") or trade.get("eventSlug")
            if slug:
                market_trades[slug].append(trade)
        
        # Считаем PnL ПО РЫНКАМ (через BUY/SELL)
        wins = 0
        losses = 0
        total_pnl = 0.0
        total_invested = 0.0
        
        for slug, market_list in market_trades.items():
            # Покупки и продажи
            buys = sum(t.get("usdcSize", 0) for t in market_list if t.get("side") == "BUY")
            sells = sum(t.get("usdcSize", 0) for t in market_list if t.get("side") == "SELL")
            
            # PnL = продано - куплено
            market_pnl = sells - buys
            total_pnl += market_pnl
            total_invested += buys
            
            if market_pnl > 0:
                wins += 1
            elif market_pnl < 0:
                losses += 1
        
        total_trades = len(trades)
        unique_markets = len(market_trades)
        win_rate = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
        
        print(f"  [Анализ] Рынков: {unique_markets}, Wins: {wins}, Losses: {losses}, PnL: ${total_pnl:.2f}")
        
        # Фильтры (ослабленные)
        if total_trades < 5:
            print(f"  [Отсеяно] Мало сделок")
            return None
        
        if win_rate < 30:  # Было 5%, стало 30%
            print(f"  [Отсеяно] Низкий WR: {win_rate:.1f}%")
            return None
        
        if total_pnl <= 0:
            print(f"  [Отсеяно] Отрицательный PnL")
            return None
        
        avg_bet = total_invested / total_trades if total_trades else 0
        niche = self._detect_niche(trades)
        
        # Score
        score = (win_rate * 0.35) + (min(max(total_pnl/100, 0), 200) * 0.30) + (min(total_trades, 200)/200 * 15) + 20
        
        print(f"  [✓] СМАРТ: {address[:12]}... | WR:{win_rate:.1f}% | PnL:${total_pnl:.0f} | Score:{score:.1f}")
        
        return TraderProfile(
            address=address,
            username=None,
            trades=total_trades,
            win_rate=round(win_rate, 2),
            pnl=round(total_pnl, 2),
            pnl_percent=round((total_pnl/total_invested*100) if total_invested else 0, 2),
            invested_capital=round(total_invested, 2),
            avg_bet=round(avg_bet, 2),
            events_count=unique_markets,
            max_loss=0,
            account_age_days=90,
            niche=niche,
            score=round(score, 2),
            last_scan=datetime.now(),
            max_loss_pnl_ratio=0
        )

    def _detect_niche(self, trades: List[Dict]) -> str:
        niche_counts = defaultdict(int)
        for trade in trades:
            text = (trade.get("title", "") + " " + trade.get("slug", "")).lower()
            for cat, kws in self.category_keywords.items():
                if any(k in text for k in kws):
                    niche_counts[cat] += 1
                    break
        return max(niche_counts.items(), key=lambda x: x[1])[0] if niche_counts else "General"
