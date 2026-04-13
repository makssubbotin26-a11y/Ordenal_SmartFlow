from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskID
from rich.panel import Panel
from rich.live import Live
from typing import List, Optional
from core.database import TraderProfile
from datetime import datetime

class ScannerUI:
    def __init__(self):
        self.console = Console()
        self.progress: Optional[Progress] = None
        self.live: Optional[Live] = None
        self.task_events: Optional[TaskID] = None
        self.task_traders: Optional[TaskID] = None
        
    def start(self, total_events: int, target_traders: int):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            console=self.console
        )
        
        self.task_events = self.progress.add_task(
            "[cyan]Scanning Events...", total=total_events
        )
        self.task_traders = self.progress.add_task(
            "[green]Smart Traders Found...", total=target_traders
        )
        
        self.live = Live(
            Panel(self.progress, title="Polymarket Smart Scanner", border_style="green"),
            console=self.console,
            refresh_per_second=2
        )
        self.live.start()
    
    def update_events(self, advance: int = 1):
        if self.task_events:
            self.progress.advance(self.task_events, advance)
    
    def update_traders(self, advance: int = 1):
        if self.task_traders:
            self.progress.advance(self.task_traders, advance)
    
    def display_new_trader(self, profile: TraderProfile):
        """Отображение нового найденного трейдера"""
        table = Table(title=f"New Smart Money Detected: {profile.address[:12]}...", 
                     show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Score", f"{profile.score:.2f}")
        table.add_row("Win Rate", f"{profile.win_rate:.1f}%")
        table.add_row("PnL", f"${profile.pnl:,.2f} ({profile.pnl_percent:.1f}%)")
        table.add_row("Niche", profile.niche)
        table.add_row("Trades", str(profile.trades))
        
        self.console.print(table)
    
    def stop(self):
        if self.live:
            self.live.stop()
    
    def show_final_results(self, traders: List[TraderProfile]):
        self.console.clear()
        self.console.print("[bold green]Scan Complete! Top Smart Money Traders:[/]")
        
        table = Table(show_header=True, header_style="bold white")
        table.add_column("Rank", style="dim")
        table.add_column("Address")
        table.add_column("Niche", style="cyan")
        table.add_column("Score", style="green")
        table.add_column("Win Rate", style="yellow")
        table.add_column("PnL %", style="magenta")
        table.add_column("Trades")
        
        for i, t in enumerate(traders[:20], 1):
            table.add_row(
                str(i),
                t.address[:16] + "...",
                t.niche,
                f"{t.score:.1f}",
                f"{t.win_rate:.1f}%",
                f"{t.pnl_percent:.1f}%",
                str(t.trades)
            )
        
        self.console.print(table)
