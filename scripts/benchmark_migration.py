#!/usr/bin/env python
"""Benchmark script to compare gevent vs asyncio performance

This script runs performance tests on both implementations to measure:
- Request latency
- Throughput
- Concurrent connection handling
- Database query performance
"""
import asyncio
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()


class MigrationBenchmark:
    """Benchmark gevent vs asyncio implementations"""
    
    def __init__(
        self,
        flask_url: str = "http://127.0.0.1:5042",
        fastapi_url: str = "http://127.0.0.1:5043",
    ):
        self.flask_url = flask_url
        self.fastapi_url = fastapi_url
        self.results = {
            "flask": {},
            "fastapi": {},
            "timestamp": datetime.now().isoformat(),
        }
    
    async def benchmark_endpoint(
        self,
        endpoint: str,
        method: str = "GET",
        iterations: int = 100,
        concurrent: int = 10,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Benchmark a single endpoint"""
        console.print(f"\n[cyan]Benchmarking {method} {endpoint}[/cyan]")
        
        # Benchmark Flask/gevent
        flask_times = await self._benchmark_server(
            url=f"{self.flask_url}{endpoint}",
            method=method,
            iterations=iterations,
            concurrent=concurrent,
            payload=payload,
            server_type="Flask/gevent",
        )
        
        # Benchmark FastAPI/asyncio
        fastapi_times = await self._benchmark_server(
            url=f"{self.fastapi_url}{endpoint}",
            method=method,
            iterations=iterations,
            concurrent=concurrent,
            payload=payload,
            server_type="FastAPI/asyncio",
        )
        
        # Calculate statistics
        flask_stats = self._calculate_stats(flask_times)
        fastapi_stats = self._calculate_stats(fastapi_times)
        
        # Store results
        self.results["flask"][endpoint] = flask_stats
        self.results["fastapi"][endpoint] = fastapi_stats
        
        # Display comparison
        self._display_comparison(endpoint, flask_stats, fastapi_stats)
        
        return {
            "flask": flask_stats,
            "fastapi": fastapi_stats,
            "improvement": {
                "latency": ((flask_stats["mean"] - fastapi_stats["mean"]) / flask_stats["mean"]) * 100,
                "throughput": ((fastapi_stats["throughput"] - flask_stats["throughput"]) / flask_stats["throughput"]) * 100,
            }
        }
    
    async def _benchmark_server(
        self,
        url: str,
        method: str,
        iterations: int,
        concurrent: int,
        payload: dict[str, Any] | None,
        server_type: str,
    ) -> list[float]:
        """Benchmark a specific server implementation"""
        times = []
        errors = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn(f"[progress.description]{server_type}"),
            transient=True,
        ) as progress:
            task = progress.add_task(f"Running {iterations} requests...", total=iterations)
            
            async with httpx.AsyncClient() as client:
                # Run requests in batches
                for batch_start in range(0, iterations, concurrent):
                    batch_size = min(concurrent, iterations - batch_start)
                    
                    # Create batch of requests
                    tasks = []
                    for _ in range(batch_size):
                        if method == "GET":
                            task_coro = client.get(url, timeout=30.0)
                        elif method == "POST":
                            task_coro = client.post(url, json=payload, timeout=30.0)
                        else:
                            task_coro = client.request(method, url, json=payload, timeout=30.0)
                        
                        tasks.append(self._time_request(task_coro))
                    
                    # Execute batch concurrently
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Process results
                    for result in batch_results:
                        if isinstance(result, Exception):
                            errors += 1
                        elif result is not None:
                            times.append(result)
                    
                    progress.update(task, advance=batch_size)
        
        if errors > 0:
            console.print(f"[yellow]  Errors: {errors}/{iterations}[/yellow]")
        
        return times
    
    async def _time_request(self, request_coro) -> float | None:
        """Time a single request"""
        start = time.time()
        try:
            response = await request_coro
            if response.status_code >= 400:
                return None
            return time.time() - start
        except Exception:
            return None
    
    def _calculate_stats(self, times: list[float]) -> dict[str, float]:
        """Calculate statistics from timing data"""
        if not times:
            return {
                "mean": 0,
                "median": 0,
                "p95": 0,
                "p99": 0,
                "min": 0,
                "max": 0,
                "throughput": 0,
            }
        
        sorted_times = sorted(times)
        return {
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "p95": sorted_times[int(len(times) * 0.95)],
            "p99": sorted_times[int(len(times) * 0.99)],
            "min": min(times),
            "max": max(times),
            "throughput": len(times) / sum(times),  # requests per second
        }
    
    def _display_comparison(
        self,
        endpoint: str,
        flask_stats: dict[str, float],
        fastapi_stats: dict[str, float],
    ):
        """Display comparison table"""
        table = Table(title=f"Benchmark Results: {endpoint}")
        table.add_column("Metric", style="cyan")
        table.add_column("Flask/gevent", style="yellow")
        table.add_column("FastAPI/asyncio", style="green")
        table.add_column("Improvement", style="magenta")
        
        metrics = [
            ("Mean latency (ms)", "mean", lambda x: f"{x*1000:.2f}"),
            ("Median latency (ms)", "median", lambda x: f"{x*1000:.2f}"),
            ("P95 latency (ms)", "p95", lambda x: f"{x*1000:.2f}"),
            ("P99 latency (ms)", "p99", lambda x: f"{x*1000:.2f}"),
            ("Throughput (req/s)", "throughput", lambda x: f"{x:.2f}"),
        ]
        
        for name, key, formatter in metrics:
            flask_val = flask_stats[key]
            fastapi_val = fastapi_stats[key]
            
            if key == "throughput":
                improvement = ((fastapi_val - flask_val) / flask_val) * 100 if flask_val else 0
            else:
                improvement = ((flask_val - fastapi_val) / flask_val) * 100 if flask_val else 0
            
            improvement_str = f"{improvement:+.1f}%" if improvement != 0 else "—"
            
            table.add_row(
                name,
                formatter(flask_val),
                formatter(fastapi_val),
                improvement_str,
            )
        
        console.print(table)
    
    async def benchmark_concurrent_connections(self, max_concurrent: int = 1000):
        """Test maximum concurrent connections"""
        console.print("\n[cyan]Testing concurrent connection limits[/cyan]")
        
        endpoint = "/api/1/ping"
        
        for server_type, base_url in [("Flask/gevent", self.flask_url), ("FastAPI/asyncio", self.fastapi_url)]:
            console.print(f"\n[yellow]Testing {server_type}[/yellow]")
            
            # Binary search for max concurrent connections
            low, high = 1, max_concurrent
            max_successful = 0
            
            while low <= high:
                mid = (low + high) // 2
                
                # Test with mid concurrent connections
                async with httpx.AsyncClient() as client:
                    tasks = [
                        client.get(f"{base_url}{endpoint}", timeout=10.0)
                        for _ in range(mid)
                    ]
                    
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    successful = sum(1 for r in results if not isinstance(r, Exception) and r.status_code == 200)
                    
                    if successful == mid:
                        max_successful = mid
                        low = mid + 1
                    else:
                        high = mid - 1
                
                console.print(f"  Testing {mid} connections: {successful}/{mid} successful")
            
            console.print(f"  [green]Max concurrent: {max_successful}[/green]")
            self.results[server_type.lower().split('/')[0]]["max_concurrent"] = max_successful
    
    async def benchmark_database_operations(self):
        """Benchmark database-heavy operations"""
        console.print("\n[cyan]Benchmarking database operations[/cyan]")
        
        # Test history events query (database-heavy)
        await self.benchmark_endpoint(
            "/api/1/history/events?limit=1000",
            iterations=50,
            concurrent=5,
        )
        
        # Test settings (cached vs uncached)
        await self.benchmark_endpoint(
            "/api/1/settings",
            iterations=100,
            concurrent=10,
        )
    
    async def run_full_benchmark(self):
        """Run complete benchmark suite"""
        console.print("[bold cyan]Rotki AsyncIO Migration Performance Benchmark[/bold cyan]")
        console.print("=" * 50)
        
        # Basic endpoints
        await self.benchmark_endpoint("/api/1/ping", iterations=1000, concurrent=50)
        await self.benchmark_endpoint("/api/1/info", iterations=100, concurrent=10)
        
        # Database operations
        await self.benchmark_database_operations()
        
        # Concurrent connections
        await self.benchmark_concurrent_connections()
        
        # WebSocket performance would be tested separately
        
        # Save results
        output_file = Path("benchmark_results.json")
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2)
        
        console.print(f"\n[green]Results saved to {output_file}[/green]")
        
        # Display summary
        self._display_summary()
    
    def _display_summary(self):
        """Display overall summary"""
        console.print("\n[bold cyan]Summary[/bold cyan]")
        
        improvements = []
        for endpoint in self.results["flask"]:
            if endpoint in self.results["fastapi"] and "mean" in self.results["flask"][endpoint]:
                flask_mean = self.results["flask"][endpoint]["mean"]
                fastapi_mean = self.results["fastapi"][endpoint]["mean"]
                if flask_mean > 0:
                    improvement = ((flask_mean - fastapi_mean) / flask_mean) * 100
                    improvements.append((endpoint, improvement))
        
        if improvements:
            avg_improvement = statistics.mean(imp[1] for imp in improvements)
            console.print(f"\nAverage latency improvement: [green]{avg_improvement:.1f}%[/green]")
            
            console.print("\nTop improvements:")
            for endpoint, improvement in sorted(improvements, key=lambda x: x[1], reverse=True)[:5]:
                console.print(f"  {endpoint}: [green]{improvement:.1f}%[/green]")


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Benchmark gevent vs asyncio")
    parser.add_argument("--flask-url", default="http://127.0.0.1:5042", help="Flask server URL")
    parser.add_argument("--fastapi-url", default="http://127.0.0.1:5043", help="FastAPI server URL")
    parser.add_argument("--quick", action="store_true", help="Run quick benchmark")
    
    args = parser.parse_args()
    
    benchmark = MigrationBenchmark(
        flask_url=args.flask_url,
        fastapi_url=args.fastapi_url,
    )
    
    if args.quick:
        # Quick test
        await benchmark.benchmark_endpoint("/api/1/ping", iterations=100, concurrent=10)
    else:
        # Full benchmark
        await benchmark.run_full_benchmark()


if __name__ == "__main__":
    asyncio.run(main())