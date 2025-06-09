#!/usr/bin/env python
"""Monitor the asyncio migration progress

This script provides real-time monitoring of the migration status,
performance metrics, and error rates.
"""
import asyncio
import json
import time
from collections import defaultdict
from datetime import datetime
from typing import Any

import httpx
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn


console = Console()


class MigrationMonitor:
    """Monitor migration metrics and status"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:5042"):
        self.base_url = base_url
        self.metrics = {
            "requests": defaultdict(lambda: {"count": 0, "errors": 0, "total_time": 0}),
            "features": {},
            "start_time": time.time(),
        }
    
    async def fetch_feature_status(self) -> dict[str, Any]:
        """Fetch current feature flag status"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/api/1/async/features")
                if response.status_code == 200:
                    data = response.json()
                    return data.get("result", {})
            except Exception as e:
                console.print(f"[red]Error fetching features: {e}[/red]")
        return {}
    
    async def test_endpoint(self, endpoint: str, method: str = "GET") -> tuple[bool, float]:
        """Test an endpoint and return success status and response time"""
        async with httpx.AsyncClient() as client:
            start = time.time()
            try:
                if method == "GET":
                    response = await client.get(f"{self.base_url}{endpoint}")
                else:
                    response = await client.request(method, f"{self.base_url}{endpoint}")
                
                duration = time.time() - start
                success = response.status_code < 400
                
                # Update metrics
                self.metrics["requests"][endpoint]["count"] += 1
                self.metrics["requests"][endpoint]["total_time"] += duration
                if not success:
                    self.metrics["requests"][endpoint]["errors"] += 1
                
                return success, duration
            except Exception as e:
                duration = time.time() - start
                self.metrics["requests"][endpoint]["count"] += 1
                self.metrics["requests"][endpoint]["errors"] += 1
                return False, duration
    
    def create_dashboard(self) -> Layout:
        """Create the monitoring dashboard layout"""
        layout = Layout()
        
        # Header
        header = Panel(
            f"[bold cyan]Rotki AsyncIO Migration Monitor[/bold cyan]\n"
            f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            style="bold white on blue"
        )
        
        # Feature status table
        feature_table = Table(title="Feature Flag Status", show_header=True)
        feature_table.add_column("Feature", style="cyan")
        feature_table.add_column("Status", style="green")
        feature_table.add_column("Type", style="yellow")
        
        if self.metrics["features"]:
            status = self.metrics["features"].get("status", {})
            for feature, enabled in status.items():
                status_text = "[green]✓ Enabled[/green]" if enabled else "[red]✗ Disabled[/red]"
                feature_type = "Endpoint" if "endpoint" in feature.lower() else "Core"
                feature_table.add_row(feature, status_text, feature_type)
        
        # Endpoint performance table
        perf_table = Table(title="Endpoint Performance", show_header=True)
        perf_table.add_column("Endpoint", style="cyan")
        perf_table.add_column("Requests", style="white")
        perf_table.add_column("Avg Time", style="yellow")
        perf_table.add_column("Error Rate", style="red")
        perf_table.add_column("Status", style="green")
        
        for endpoint, stats in self.metrics["requests"].items():
            count = stats["count"]
            if count > 0:
                avg_time = stats["total_time"] / count
                error_rate = (stats["errors"] / count) * 100
                status = "[green]✓[/green]" if error_rate < 5 else "[red]✗[/red]"
                
                perf_table.add_row(
                    endpoint,
                    str(count),
                    f"{avg_time*1000:.1f}ms",
                    f"{error_rate:.1f}%",
                    status
                )
        
        # Migration progress
        if self.metrics["features"]:
            progress_data = self.metrics["features"]
            progress_panel = Panel(
                f"[bold]Migration Progress[/bold]\n\n"
                f"Total Features: {progress_data.get('total_features', 0)}\n"
                f"Enabled Features: {progress_data.get('enabled_features', 0)}\n"
                f"Progress: {progress_data.get('progress_percentage', 0):.1f}%\n\n"
                f"[bold]Endpoint Migration[/bold]\n"
                f"Total: {progress_data.get('endpoint_migration', {}).get('total', 0)}\n"
                f"Migrated: {progress_data.get('endpoint_migration', {}).get('migrated', 0)}\n"
                f"Progress: {progress_data.get('endpoint_migration', {}).get('percentage', 0):.1f}%",
                style="bold white on dark_blue"
            )
        else:
            progress_panel = Panel("[yellow]Loading migration status...[/yellow]")
        
        # Arrange layout
        layout.split_column(
            Layout(header, size=3),
            Layout(name="main"),
        )
        
        layout["main"].split_row(
            Layout(feature_table),
            Layout(name="right"),
        )
        
        layout["right"].split_column(
            Layout(progress_panel, size=12),
            Layout(perf_table),
        )
        
        return layout
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        test_endpoints = [
            "/api/1/ping",
            "/api/1/info",
            "/api/1/settings",
            "/api/1/async/features",
        ]
        
        while True:
            # Fetch feature status
            features = await self.fetch_feature_status()
            if features:
                self.metrics["features"] = features
            
            # Test endpoints
            for endpoint in test_endpoints:
                await self.test_endpoint(endpoint)
            
            # Wait before next iteration
            await asyncio.sleep(5)
    
    async def run(self):
        """Run the monitor with live display"""
        # Start monitoring in background
        monitor_task = asyncio.create_task(self.monitor_loop())
        
        # Live display
        with Live(self.create_dashboard(), refresh_per_second=1) as live:
            try:
                while True:
                    await asyncio.sleep(1)
                    live.update(self.create_dashboard())
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopping monitor...[/yellow]")
                monitor_task.cancel()
                
        # Print final summary
        self.print_summary()
    
    def print_summary(self):
        """Print summary statistics"""
        console.print("\n[bold cyan]Migration Monitor Summary[/bold cyan]")
        console.print("="*50)
        
        total_requests = sum(s["count"] for s in self.metrics["requests"].values())
        total_errors = sum(s["errors"] for s in self.metrics["requests"].values())
        
        console.print(f"Total Requests: {total_requests}")
        console.print(f"Total Errors: {total_errors}")
        if total_requests > 0:
            console.print(f"Error Rate: {(total_errors/total_requests)*100:.2f}%")
        
        # Save metrics to file
        with open("migration_metrics.json", "w") as f:
            json.dump(self.metrics, f, indent=2)
        console.print("\n[green]Metrics saved to migration_metrics.json[/green]")


async def main():
    """Main entry point"""
    console.print("[bold cyan]Rotki AsyncIO Migration Monitor[/bold cyan]")
    console.print("Press Ctrl+C to stop\n")
    
    monitor = MigrationMonitor()
    await monitor.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitor stopped[/yellow]")