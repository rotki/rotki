#!/usr/bin/env python
"""Benchmark script to compare gevent vs asyncio performance

This script helps measure the performance impact of migrating from
gevent to asyncio, ensuring no regression in key metrics.
"""
import asyncio
import concurrent.futures
import json
import sqlite3
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import aiosqlite
import gevent
from gevent import socket as gsocket
from gevent.pool import Pool as GeventPool

# Performance test results
@dataclass
class BenchmarkResult:
    test_name: str
    implementation: str
    iterations: int
    total_time: float
    avg_time: float
    min_time: float
    max_time: float
    std_dev: float
    ops_per_second: float


class PerformanceBenchmark:
    """Compare performance between gevent and asyncio implementations"""
    
    def __init__(self, iterations: int = 1000):
        self.iterations = iterations
        self.results: list[BenchmarkResult] = []
    
    def measure_time(self, func: Callable, *args, **kwargs) -> float:
        """Measure execution time of a function"""
        start = time.perf_counter()
        func(*args, **kwargs)
        return time.perf_counter() - start
    
    async def measure_async_time(self, coro) -> float:
        """Measure execution time of a coroutine"""
        start = time.perf_counter()
        await coro
        return time.perf_counter() - start
    
    def run_benchmark(
        self,
        test_name: str,
        gevent_func: Callable,
        asyncio_func: Callable,
        warmup: int = 10,
    ) -> None:
        """Run benchmark comparing gevent and asyncio implementations"""
        print(f"\n{'='*60}")
        print(f"Benchmarking: {test_name}")
        print(f"Iterations: {self.iterations}")
        print(f"{'='*60}")
        
        # Warmup
        print("Warming up...")
        for _ in range(warmup):
            gevent_func()
            asyncio.run(asyncio_func())
        
        # Benchmark gevent
        print("Testing gevent implementation...")
        gevent_times = []
        total_start = time.perf_counter()
        
        for i in range(self.iterations):
            duration = self.measure_time(gevent_func)
            gevent_times.append(duration)
            if i % 100 == 0:
                print(f"  Progress: {i}/{self.iterations}", end='\r')
        
        gevent_total = time.perf_counter() - total_start
        
        # Benchmark asyncio
        print("\nTesting asyncio implementation...")
        asyncio_times = []
        total_start = time.perf_counter()
        
        async def run_async_iterations():
            for i in range(self.iterations):
                duration = await self.measure_async_time(asyncio_func())
                asyncio_times.append(duration)
                if i % 100 == 0:
                    print(f"  Progress: {i}/{self.iterations}", end='\r')
        
        asyncio.run(run_async_iterations())
        asyncio_total = time.perf_counter() - total_start
        
        # Calculate results
        for impl, times, total in [
            ("gevent", gevent_times, gevent_total),
            ("asyncio", asyncio_times, asyncio_total)
        ]:
            result = BenchmarkResult(
                test_name=test_name,
                implementation=impl,
                iterations=self.iterations,
                total_time=total,
                avg_time=statistics.mean(times),
                min_time=min(times),
                max_time=max(times),
                std_dev=statistics.stdev(times) if len(times) > 1 else 0,
                ops_per_second=self.iterations / total,
            )
            self.results.append(result)
            
            print(f"\n{impl} Results:")
            print(f"  Total time: {result.total_time:.3f}s")
            print(f"  Avg time per op: {result.avg_time*1000:.3f}ms")
            print(f"  Min/Max: {result.min_time*1000:.3f}ms / {result.max_time*1000:.3f}ms")
            print(f"  Std dev: {result.std_dev*1000:.3f}ms")
            print(f"  Ops/second: {result.ops_per_second:.1f}")
    
    def print_summary(self) -> None:
        """Print benchmark summary"""
        print(f"\n{'='*60}")
        print("BENCHMARK SUMMARY")
        print(f"{'='*60}")
        
        # Group results by test
        tests = {}
        for result in self.results:
            if result.test_name not in tests:
                tests[result.test_name] = {}
            tests[result.test_name][result.implementation] = result
        
        # Compare implementations
        for test_name, impls in tests.items():
            if "gevent" in impls and "asyncio" in impls:
                gevent_result = impls["gevent"]
                asyncio_result = impls["asyncio"]
                
                speedup = gevent_result.avg_time / asyncio_result.avg_time
                ops_improvement = asyncio_result.ops_per_second / gevent_result.ops_per_second
                
                print(f"\n{test_name}:")
                print(f"  Asyncio is {speedup:.2f}x {'faster' if speedup > 1 else 'slower'}")
                print(f"  Throughput: {ops_improvement:.2f}x {'better' if ops_improvement > 1 else 'worse'}")
                print(f"  Gevent: {gevent_result.ops_per_second:.1f} ops/s")
                print(f"  Asyncio: {asyncio_result.ops_per_second:.1f} ops/s")


# Test implementations
class SQLiteBenchmark:
    """Benchmark SQLite operations"""
    
    def __init__(self):
        self.db_path = ":memory:"
        self.setup_database()
    
    def setup_database(self):
        """Create test database schema"""
        conn = sqlite3.connect(self.db_path)
        conn.execute('''
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY,
                data TEXT,
                value REAL
            )
        ''')
        
        # Insert test data
        for i in range(1000):
            conn.execute(
                "INSERT INTO test_table (data, value) VALUES (?, ?)",
                (f"data_{i}", i * 1.5)
            )
        conn.commit()
        conn.close()
    
    def gevent_query(self):
        """Gevent-style database query with context switching"""
        conn = sqlite3.connect(self.db_path)
        
        # Simulate progress callback for context switching
        def progress_callback():
            gevent.sleep(0)  # Yield to other greenlets
            return 0
        
        conn.set_progress_handler(progress_callback, 100)
        
        cursor = conn.execute("SELECT * FROM test_table WHERE value > 500")
        results = cursor.fetchall()
        conn.close()
        return results
    
    async def asyncio_query(self):
        """Asyncio database query"""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("SELECT * FROM test_table WHERE value > 500")
            results = await cursor.fetchall()
            return results


class TaskSpawningBenchmark:
    """Benchmark task spawning and management"""
    
    def gevent_spawn_tasks(self):
        """Spawn and wait for gevent tasks"""
        def task(n):
            gevent.sleep(0.001)  # Simulate work
            return n * 2
        
        greenlets = [gevent.spawn(task, i) for i in range(100)]
        gevent.joinall(greenlets)
        return [g.value for g in greenlets]
    
    async def asyncio_spawn_tasks(self):
        """Spawn and wait for asyncio tasks"""
        async def task(n):
            await asyncio.sleep(0.001)  # Simulate work
            return n * 2
        
        tasks = [asyncio.create_task(task(i)) for i in range(100)]
        results = await asyncio.gather(*tasks)
        return results


class ConcurrentRequestsBenchmark:
    """Benchmark concurrent I/O operations"""
    
    def gevent_concurrent_io(self):
        """Simulate concurrent I/O with gevent"""
        def fetch_data(n):
            # Simulate network delay
            gevent.sleep(0.01)
            return f"data_{n}"
        
        pool = GeventPool(50)
        results = pool.map(fetch_data, range(50))
        return list(results)
    
    async def asyncio_concurrent_io(self):
        """Simulate concurrent I/O with asyncio"""
        async def fetch_data(n):
            # Simulate network delay
            await asyncio.sleep(0.01)
            return f"data_{n}"
        
        tasks = [fetch_data(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        return results


def run_benchmarks():
    """Run all benchmarks"""
    benchmark = PerformanceBenchmark(iterations=100)
    
    # SQLite benchmark
    sqlite_bench = SQLiteBenchmark()
    benchmark.run_benchmark(
        "SQLite Query",
        sqlite_bench.gevent_query,
        sqlite_bench.asyncio_query,
    )
    
    # Task spawning benchmark
    task_bench = TaskSpawningBenchmark()
    benchmark.run_benchmark(
        "Task Spawning (100 tasks)",
        task_bench.gevent_spawn_tasks,
        task_bench.asyncio_spawn_tasks,
        warmup=5,
    )
    
    # Concurrent I/O benchmark
    io_bench = ConcurrentRequestsBenchmark()
    benchmark.run_benchmark(
        "Concurrent I/O (50 operations)",
        io_bench.gevent_concurrent_io,
        io_bench.asyncio_concurrent_io,
        warmup=5,
    )
    
    # Print summary
    benchmark.print_summary()
    
    # Save results
    results_data = [
        {
            "test": r.test_name,
            "implementation": r.implementation,
            "avg_time_ms": r.avg_time * 1000,
            "ops_per_second": r.ops_per_second,
        }
        for r in benchmark.results
    ]
    
    with open("benchmark_results.json", "w") as f:
        json.dump(results_data, f, indent=2)
    
    print(f"\nResults saved to benchmark_results.json")


if __name__ == "__main__":
    print("Starting gevent vs asyncio benchmark...")
    
    # Monkey patch for gevent
    from gevent import monkey
    monkey.patch_all()
    
    run_benchmarks()