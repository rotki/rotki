"""Performance monitoring and profiling tools for async migration

Provides tools to measure and compare performance between sync and async
implementations.
"""
import asyncio
import functools
import logging
import time
from collections import defaultdict
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import psutil
from prometheus_client import Counter, Gauge, Histogram

from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# Prometheus metrics
request_count = Counter(
    'rotki_requests_total',
    'Total number of requests',
    ['method', 'endpoint', 'implementation'],
)

request_duration = Histogram(
    'rotki_request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint', 'implementation'],
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
)

active_tasks = Gauge(
    'rotki_active_tasks',
    'Number of active async tasks',
    ['task_type'],
)

db_connections = Gauge(
    'rotki_db_connections',
    'Number of active database connections',
    ['connection_type'],
)

memory_usage = Gauge(
    'rotki_memory_usage_bytes',
    'Memory usage in bytes',
    ['type'],
)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""

    operation: str
    implementation: str  # 'sync' or 'async'
    start_time: float
    end_time: float
    duration: float
    memory_before: int
    memory_after: int
    memory_delta: int
    cpu_percent: float
    error: str | None = None
    result: Any = None

    @property
    def ops_per_second(self) -> float:
        """Calculate operations per second"""
        return 1.0 / self.duration if self.duration > 0 else 0


class PerformanceMonitor:
    """Monitor and collect performance metrics"""

    def __init__(self):
        self.metrics: list[PerformanceMetrics] = []
        self._process = psutil.Process()

    @contextmanager
    def measure(self, operation: str, implementation: str = 'sync'):
        """Context manager to measure performance"""
        # Collect initial metrics
        self._process.cpu_percent()  # First call to initialize
        memory_before = self._process.memory_info().rss
        start_time = time.time()

        metric = PerformanceMetrics(
            operation=operation,
            implementation=implementation,
            start_time=start_time,
            end_time=0,
            duration=0,
            memory_before=memory_before,
            memory_after=0,
            memory_delta=0,
            cpu_percent=0,
        )

        try:
            yield metric
        except Exception as e:
            metric.error = str(e)
            raise
        finally:
            # Collect final metrics
            end_time = time.time()
            memory_after = self._process.memory_info().rss
            cpu_percent = self._process.cpu_percent()

            metric.end_time = end_time
            metric.duration = end_time - start_time
            metric.memory_after = memory_after
            metric.memory_delta = memory_after - memory_before
            metric.cpu_percent = cpu_percent

            self.metrics.append(metric)

            # Update Prometheus metrics
            request_duration.labels(
                method='operation',
                endpoint=operation,
                implementation=implementation,
            ).observe(metric.duration)

            memory_usage.labels(type=implementation).set(memory_after)

    def get_summary(self) -> dict[str, Any]:
        """Get performance summary"""
        if not self.metrics:
            return {}

        summary = defaultdict(lambda: {
            'count': 0,
            'total_duration': 0,
            'avg_duration': 0,
            'min_duration': float('inf'),
            'max_duration': 0,
            'total_memory': 0,
            'errors': 0,
        })

        for metric in self.metrics:
            key = f'{metric.operation}_{metric.implementation}'
            stats = summary[key]

            stats['count'] += 1
            stats['total_duration'] += metric.duration
            stats['min_duration'] = min(stats['min_duration'], metric.duration)
            stats['max_duration'] = max(stats['max_duration'], metric.duration)
            stats['total_memory'] += metric.memory_delta

            if metric.error:
                stats['errors'] += 1

        # Calculate averages
        for stats in summary.values():
            if stats['count'] > 0:
                stats['avg_duration'] = stats['total_duration'] / stats['count']
                stats['avg_memory'] = stats['total_memory'] / stats['count']

        return dict(summary)

    def compare_implementations(self, operation: str) -> dict[str, Any]:
        """Compare sync vs async performance for an operation"""
        sync_metrics = [m for m in self.metrics if m.operation == operation and m.implementation == 'sync']
        async_metrics = [m for m in self.metrics if m.operation == operation and m.implementation == 'async']

        if not sync_metrics or not async_metrics:
            return {}

        sync_avg = sum(m.duration for m in sync_metrics) / len(sync_metrics)
        async_avg = sum(m.duration for m in async_metrics) / len(async_metrics)

        return {
            'operation': operation,
            'sync_avg_duration': sync_avg,
            'async_avg_duration': async_avg,
            'speedup': sync_avg / async_avg if async_avg > 0 else 0,
            'improvement_percent': ((sync_avg - async_avg) / sync_avg) * 100 if sync_avg > 0 else 0,
        }


# Global monitor instance
performance_monitor = PerformanceMonitor()


def measure_performance(implementation: str = 'sync'):
    """Decorator to measure function performance"""
    def decorator(func):
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with performance_monitor.measure(func.__name__, implementation) as metric:
                result = func(*args, **kwargs)
                metric.result = result
                return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with performance_monitor.measure(func.__name__, implementation) as metric:
                result = await func(*args, **kwargs)
                metric.result = result
                return result

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class AsyncProfiler:
    """Profile async code execution"""

    def __init__(self):
        self.task_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'min_time': float('inf'),
            'max_time': 0,
            'active': 0,
        })

    @contextmanager
    def profile_task(self, task_name: str):
        """Profile an async task"""
        stats = self.task_stats[task_name]
        stats['active'] += 1
        active_tasks.labels(task_type=task_name).inc()

        start_time = time.time()

        try:
            yield
        finally:
            duration = time.time() - start_time

            stats['count'] += 1
            stats['total_time'] += duration
            stats['min_time'] = min(stats['min_time'], duration)
            stats['max_time'] = max(stats['max_time'], duration)
            stats['active'] -= 1

            active_tasks.labels(task_type=task_name).dec()

    def get_task_summary(self) -> dict[str, Any]:
        """Get summary of all profiled tasks"""
        summary = {}

        for task_name, stats in self.task_stats.items():
            if stats['count'] > 0:
                summary[task_name] = {
                    'count': stats['count'],
                    'avg_time': stats['total_time'] / stats['count'],
                    'min_time': stats['min_time'],
                    'max_time': stats['max_time'],
                    'total_time': stats['total_time'],
                    'active': stats['active'],
                }

        return summary


# Global profiler instance
async_profiler = AsyncProfiler()


class ConcurrencyMonitor:
    """Monitor concurrent operations"""

    def __init__(self):
        self.concurrent_operations = defaultdict(int)
        self.max_concurrent = defaultdict(int)
        self._lock = asyncio.Lock()

    @asynccontextmanager
    async def track_concurrent(self, operation: str):
        """Track concurrent execution of an operation"""
        async with self._lock:
            self.concurrent_operations[operation] += 1
            self.max_concurrent[operation] = max(
                self.max_concurrent[operation],
                self.concurrent_operations[operation],
            )

        try:
            yield self.concurrent_operations[operation]
        finally:
            async with self._lock:
                self.concurrent_operations[operation] -= 1

    def get_stats(self) -> dict[str, Any]:
        """Get concurrency statistics"""
        return {
            'current': dict(self.concurrent_operations),
            'max': dict(self.max_concurrent),
        }


# Global concurrency monitor
concurrency_monitor = ConcurrencyMonitor()


async def benchmark_comparison(
    sync_func: Callable,
    async_func: Callable,
    iterations: int = 100,
    concurrent: bool = False,
) -> dict[str, Any]:
    """Benchmark sync vs async implementations"""
    results = {
        'iterations': iterations,
        'concurrent': concurrent,
    }

    # Benchmark sync implementation
    sync_start = time.time()
    if concurrent:
        # Run sync functions in threads
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(sync_func) for _ in range(iterations)]
            [f.result() for f in futures]
    else:
        [sync_func() for _ in range(iterations)]
    sync_duration = time.time() - sync_start

    # Benchmark async implementation
    async_start = time.time()
    if concurrent:
        # Run async functions concurrently
        tasks = [async_func() for _ in range(iterations)]
        async_results = await asyncio.gather(*tasks)
    else:
        async_results = []
        for _ in range(iterations):
            result = await async_func()
            async_results.append(result)
    async_duration = time.time() - async_start

    results['sync'] = {
        'duration': sync_duration,
        'ops_per_second': iterations / sync_duration,
        'avg_duration': sync_duration / iterations,
    }

    results['async'] = {
        'duration': async_duration,
        'ops_per_second': iterations / async_duration,
        'avg_duration': async_duration / iterations,
    }

    results['improvement'] = {
        'speedup': sync_duration / async_duration if async_duration > 0 else 0,
        'percent': ((sync_duration - async_duration) / sync_duration) * 100 if sync_duration > 0 else 0,
    }

    return results


def export_metrics(filepath: Path):
    """Export collected metrics to file"""
    data = {
        'timestamp': datetime.now().isoformat(),
        'performance_metrics': [
            {
                'operation': m.operation,
                'implementation': m.implementation,
                'duration': m.duration,
                'memory_delta': m.memory_delta,
                'cpu_percent': m.cpu_percent,
                'error': m.error,
            }
            for m in performance_monitor.metrics
        ],
        'summary': performance_monitor.get_summary(),
        'task_profile': async_profiler.get_task_summary(),
        'concurrency': concurrency_monitor.get_stats(),
    }

    import json
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    log.info(f'Performance metrics exported to {filepath}')
