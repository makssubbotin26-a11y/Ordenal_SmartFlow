import asyncio
import signal
import sys
from datetime import datetime
from typing import Set, Dict, List
from enum import Enum

from config.settings import CONFIG
from core.database import DatabaseManager
from core.api_client import PolymarketAPI
from core.analyzer import SmartMoneyAnalyzer
from ui.interface import ScannerUI


class ScanMode(Enum):
    GLOBAL_LEADERBOARDS = "1"
    PER_EVENT = "2"
    COMBINED = "3"


class SmartMoneyScanner:
    def __init__(self):
        self.db = DatabaseManager()
        self.analyzer = SmartMoneyAnalyzer()
        self.ui = ScannerUI()
        self.session_start = datetime.now()
        self.new_traders_count = 0
        self.processed_events = 0
        self.seen_addresses: Set[str] = set()
        self.running = True
        
    async def initialize(self):
        await self.db.init_tables()
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        print("\n[bold red]Shutting down gracefully...[/]")
        self.running = False

    def show_menu(self):
        print("\n" + "="*60)
        print("  SMARTFLOW SCANNER - Выбор режима")
        print("="*60)
        print("\n[1] Глобальные лидерборды (БЫСТРО)")
        print("[2] По событиям (ГЛУБОКО)")
        print("[3] Комбинированный")
        print("[4] Выход")
        print("="*60)

    async def scan_global_leaderboards(self, api: PolymarketAPI):
        categories = ["POLITICS", "SPORTS", "CRYPTO", "ECONOMICS", 
                     "CULTURE", "FINANCE", "TECH", "WEATHER"]
        
        print(f"\n[РЕЖИМ 1] Глобальные лидерборды")
        total_wallets = 0
        
        for category in categories:
            if not self.running:
                break
            
            print(f"\n[{category}] Сканирование...")
            traders_data = await api.get_global_leaderboard(category, limit=1000)
            category_new = 0
            
            for trader_data in traders_data:
                if not self.running:
                    break
                
                wallet = trader_data.get("proxyWallet") or trader_data.get("user")
                if not wallet:
                    continue
                
                wallet_lower = wallet.lower()
                if wallet_lower in self.seen_addresses:
                    continue
                
                self.seen_addresses.add(wallet_lower)
                total_wallets += 1
                
                should_scan = await self.db.should_scan_trader(wallet, CONFIG.ttl_days)
                if not should_scan:
                    continue
                
                activities = await api.get_user_activity(wallet)
                
                # ОТЛАДКА
                print(f"[DEBUG] Адрес: {wallet[:15]}...")
                print(f"[DEBUG] Activities: {len(activities)}")
                if activities:
                    print(f"[DEBUG] Типы: {[a.get('type') for a in activities[:10]]}")
                
                if not activities or len(activities) < 3:
                    await self.db.add_to_blacklist(wallet, "Not enough activity")
                    continue
                
                profile = self.analyzer.analyze_from_activities(wallet, activities)
                
                if profile:
                    await self.db.save_trader(profile)
                    self.new_traders_count += 1
                    category_new += 1
                
                await asyncio.sleep(0.3)
            
            print(f"[{category}] Новых: {category_new}, Всего: {total_wallets}")

    async def run(self):
        await self.initialize()
        self.show_menu()
        
        choice = input("\nВыберите режим (1-4): ").strip()
        
        if choice == "4":
            return
        
        async with PolymarketAPI() as api:
            if choice == "1":
                await self.scan_global_leaderboards(api)
            else:
                print("Неверный выбор. Запускаю режим 1...")
                await self.scan_global_leaderboards(api)
        
        print(f"\nСканирование завершено!")
        print(f"Уникальных адресов: {len(self.seen_addresses)}")
        print(f"Новых смарт-трейдеров: {self.new_traders_count}")


async def main():
    scanner = SmartMoneyScanner()
    await scanner.run()

if __name__ == "__main__":
    asyncio.run(main())
