import asyncio
import signal
import sys
from datetime import datetime
from typing import Set

from config.settings import CONFIG, PROXY_MANAGER
from core.database import DatabaseManager
from core.api_client import PolymarketAPI
from core.analyzer import SmartMoneyAnalyzer
from ui.interface import ScannerUI

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
    
    async def scan(self):
        async with PolymarketAPI() as api:
            # Получаем прогресс для resume
            progress = await self.db.get_scan_progress()
            start_from = progress["current_index"] if progress else 0
            
            # Получаем 100 завершенных событий
            events = await api.get_resolved_events(CONFIG.max_events)
            total_events = len(events)
            
            self.ui.start(total_events, CONFIG.target_traders)
            
            for idx, event in enumerate(events[start_from:], start=start_from):
                if not self.running:
                    break
                
                if self.new_traders_count >= CONFIG.target_traders:
                    self.ui.console.print("[green]Target reached! Stopping...[/]")
                    break
                
                # Сохраняем прогресс для resume
                await self.db.update_progress(idx, total_events)
                
                event_slug = event.get("slug")
                category = event.get("category")
                
                if not event_slug:
                    self.ui.update_events()
                    continue
                
                try:
                    # Получаем трейдеров события
                    addresses = await api.get_event_positions(event_slug)
                    
                    for addr in addresses:
                        if addr in self.seen_addresses:
                            continue
                        self.seen_addresses.add(addr)
                        
                        # Проверка TTL
                        should_scan = await self.db.should_scan_trader(
                            addr, CONFIG.ttl_days
                        )
                        
                        if not should_scan:
                            continue
                        
                        # Получаем детали трейдера
                        stats = await api.get_user_stats(addr)
                        if not stats:
                            continue
                        
                        positions = await api.get_portfolio_history(addr)
                        pos_list = positions.get("positions", [])
                        
                        # Анализ
                        profile = self.analyzer.analyze_trader(addr, stats, pos_list)
                        
                        if profile:
                            await self.db.save_trader(profile)
                            self.new_traders_count += 1
                            self.ui.update_traders()
                            self.ui.display_new_trader(profile)
                        else:
                            await self.db.add_to_blacklist(addr, "Failed Stage 1 filters")
                            
                        # Rate limiting
                        await asyncio.sleep(0.5)
                        
                except Exception as e:
                    self.ui.console.print(f"[red]Error processing event {event_slug}: {e}[/]")
                    continue
                
                self.ui.update_events()
                self.processed_events += 1
            
            self.ui.stop()
            
            # Финальные результаты
            top_traders = await self.db.get_top_traders(20)
            self.ui.show_final_results(top_traders)
            
            print(f"\nSession Summary:")
            print(f"- Events processed: {self.processed_events}")
            print(f"- New/Updated Smart Traders: {self.new_traders_count}")
            print(f"- Database: polymarket_traders.db")

async def main():
    scanner = SmartMoneyScanner()
    await scanner.initialize()
    await scanner.scan()

if __name__ == "__main__":
    asyncio.run(main())
