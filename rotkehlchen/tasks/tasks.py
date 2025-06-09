"""Async implementation of background tasks

This replaces gevent-based background tasks with native asyncio tasks
for better performance and cleaner code.
"""
import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from rotkehlchen.api.websockets.async_notifier import AsyncRotkiNotifier
from rotkehlchen.chain.aggregator import ChainsAggregator
from rotkehlchen.db.async_handler import AsyncDBHandler
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AsyncPeriodicTask:
    """Base class for periodic async tasks"""

    def __init__(
        self,
        name: str,
        interval: float,
        task_fn: Callable,
        immediate: bool = False,
    ):
        self.name = name
        self.interval = interval
        self.task_fn = task_fn
        self.immediate = immediate
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self.last_run: datetime | None = None
        self.next_run: datetime | None = None
        self.run_count = 0
        self.error_count = 0

    async def start(self):
        """Start the periodic task"""
        if self._task is not None:
            return

        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop())
        log.info(f'Started periodic task: {self.name}')

    async def stop(self):
        """Stop the periodic task"""
        if self._task is None:
            return

        self._stop_event.set()
        await self._task
        self._task = None
        log.info(f'Stopped periodic task: {self.name}')

    async def _run_loop(self):
        """Main task loop"""
        try:
            # Run immediately if requested
            if self.immediate:
                await self._run_once()

            while not self._stop_event.is_set():
                # Calculate next run time
                self.next_run = datetime.now() + timedelta(seconds=self.interval)

                # Wait for interval or stop signal
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.interval,
                    )
                    break  # Stop event was set
                except TimeoutError:
                    # Normal timeout, run the task
                    await self._run_once()

        except Exception as e:
            log.error(f'Periodic task {self.name} crashed: {e}')
            raise

    async def _run_once(self):
        """Run the task once"""
        self.last_run = datetime.now()
        self.run_count += 1

        try:
            log.debug(f'Running periodic task: {self.name}')
            await self.task_fn()
        except Exception as e:
            self.error_count += 1
            log.error(f'Error in periodic task {self.name}: {e}')


class AsyncBalanceUpdater:
    """Async task for updating blockchain balances"""

    def __init__(
        self,
        chains_aggregator: ChainsAggregator,
        async_db: AsyncDBHandler,
        ws_notifier: AsyncRotkiNotifier,
    ):
        self.chains_aggregator = chains_aggregator
        self.async_db = async_db
        self.ws_notifier = ws_notifier

    async def update_balances(self, addresses: list[str] | None = None):
        """Update balances for all or specific addresses"""
        log.info('Starting async balance update')

        try:
            # Get addresses to update
            if addresses is None:
                # Get all tracked addresses from DB
                addresses = await self._get_tracked_addresses()

            # Update balances for each chain concurrently
            tasks = [self._update_chain_balances(chain, addresses) for chain in self.chains_aggregator.get_chains() if hasattr(chain, 'async_node_inquirer')]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            all_balances = {}
            for result in results:
                if isinstance(result, dict):
                    all_balances.update(result)
                elif isinstance(result, Exception):
                    log.error(f'Error updating balances: {result}')

            # Save to database
            await self._save_balances(all_balances)

            # Notify via WebSocket
            await self.ws_notifier.balance_update(all_balances)

            log.info(f'Balance update completed for {len(addresses)} addresses')

        except Exception as e:
            log.error(f'Failed to update balances: {e}')
            raise

    async def _get_tracked_addresses(self) -> list[str]:
        """Get all tracked addresses from database"""
        # Implementation would query the database
        return []

    async def _update_chain_balances(
        self,
        chain: Any,
        addresses: list[str],
    ) -> dict[str, Any]:
        """Update balances for a specific chain"""
        inquirer = chain.async_node_inquirer

        # Get native token balances
        native_balances = await inquirer.get_balances(addresses)

        # Get token balances (would implement token detection)
        token_balances = {}

        return {
            'chain': chain.chain_id,
            'native': native_balances,
            'tokens': token_balances,
        }

    async def _save_balances(self, balances: dict[str, Any]):
        """Save balance data to database"""
        # Implementation would save to DB


class AsyncPriceUpdater:
    """Async task for updating asset prices"""

    def __init__(
        self,
        inquirer: Inquirer,
        async_db: AsyncDBHandler,
        ws_notifier: AsyncRotkiNotifier,
    ):
        self.inquirer = inquirer
        self.async_db = async_db
        self.ws_notifier = ws_notifier
        self.coingecko = Coingecko()

    async def update_prices(self, assets: list[str] | None = None):
        """Update prices for assets"""
        log.info('Starting async price update')

        try:
            # Get assets to update
            if assets is None:
                assets = await self._get_tracked_assets()

            # Batch price queries
            batch_size = 100
            all_prices = {}

            for i in range(0, len(assets), batch_size):
                batch = assets[i:i + batch_size]

                # Query prices concurrently from multiple sources
                tasks = [
                    self._query_coingecko_prices(batch),
                    self._query_cryptocompare_prices(batch),
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Merge results with priority
                for result in results:
                    if isinstance(result, dict):
                        all_prices.update(result)

            # Save to database
            await self._save_prices(all_prices)

            # Notify via WebSocket
            await self.ws_notifier.price_update(all_prices)

            log.info(f'Price update completed for {len(assets)} assets')

        except Exception as e:
            log.error(f'Failed to update prices: {e}')
            raise

    async def _get_tracked_assets(self) -> list[str]:
        """Get all tracked assets from database"""
        # Implementation would query the database
        return []

    async def _query_coingecko_prices(
        self,
        assets: list[str],
    ) -> dict[str, FVal]:
        """Query prices from Coingecko"""
        # Async implementation of Coingecko queries
        return {}

    async def _query_cryptocompare_prices(
        self,
        assets: list[str],
    ) -> dict[str, FVal]:
        """Query prices from CryptoCompare"""
        # Async implementation of CryptoCompare queries
        return {}

    async def _save_prices(self, prices: dict[str, FVal]):
        """Save price data to database"""
        # Implementation would save to DB


class AsyncHistoryProcessor:
    """Async task for processing blockchain history"""

    def __init__(
        self,
        chains_aggregator: ChainsAggregator,
        async_db: AsyncDBHandler,
        ws_notifier: AsyncRotkiNotifier,
    ):
        self.chains_aggregator = chains_aggregator
        self.async_db = async_db
        self.ws_notifier = ws_notifier

    async def process_history(
        self,
        from_timestamp: Timestamp | None = None,
        to_timestamp: Timestamp | None = None,
    ):
        """Process blockchain history for all chains"""
        log.info('Starting async history processing')

        try:
            # Process each chain concurrently
            tasks = [self._process_chain_history(
                            chain,
                            from_timestamp,
                            to_timestamp,
                        ) for chain in self.chains_aggregator.get_chains() if hasattr(chain, 'async_node_inquirer')]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count processed transactions
            total_processed = 0
            for result in results:
                if isinstance(result, int):
                    total_processed += result
                elif isinstance(result, Exception):
                    log.error(f'Error processing history: {result}')

            # Notify completion
            await self.ws_notifier.history_processing_complete(total_processed)

            log.info(f'History processing completed: {total_processed} transactions')

        except Exception as e:
            log.error(f'Failed to process history: {e}')
            raise

    async def _process_chain_history(
        self,
        chain: Any,
        from_timestamp: Timestamp | None,
        to_timestamp: Timestamp | None,
    ) -> int:
        """Process history for a specific chain"""
        # Implementation would query blockchain and process transactions
        return 0


class AsyncTaskOrchestrator:
    """Orchestrates all async background tasks"""

    def __init__(
        self,
        chains_aggregator: ChainsAggregator,
        async_db: AsyncDBHandler,
        ws_notifier: AsyncRotkiNotifier,
        inquirer: Inquirer,
    ):
        self.chains_aggregator = chains_aggregator
        self.async_db = async_db
        self.ws_notifier = ws_notifier
        self.inquirer = inquirer

        # Initialize task handlers
        self.balance_updater = AsyncBalanceUpdater(
            chains_aggregator,
            async_db,
            ws_notifier,
        )
        self.price_updater = AsyncPriceUpdater(
            inquirer,
            async_db,
            ws_notifier,
        )
        self.history_processor = AsyncHistoryProcessor(
            chains_aggregator,
            async_db,
            ws_notifier,
        )

        # Periodic tasks
        self.tasks: dict[str, AsyncPeriodicTask] = {}

    async def start(self):
        """Start all background tasks"""
        log.info('Starting async task orchestrator')

        # Balance update task (every 5 minutes)
        self.tasks['balance_update'] = AsyncPeriodicTask(
            name='balance_update',
            interval=300,
            task_fn=self.balance_updater.update_balances,
            immediate=True,
        )

        # Price update task (every 30 minutes)
        self.tasks['price_update'] = AsyncPeriodicTask(
            name='price_update',
            interval=1800,
            task_fn=self.price_updater.update_prices,
            immediate=True,
        )

        # History processing task (every hour)
        self.tasks['history_processing'] = AsyncPeriodicTask(
            name='history_processing',
            interval=3600,
            task_fn=self.history_processor.process_history,
            immediate=False,
        )

        # Start all tasks
        for task in self.tasks.values():
            await task.start()

    async def stop(self):
        """Stop all background tasks"""
        log.info('Stopping async task orchestrator')

        # Stop all tasks
        tasks = [task.stop() for task in self.tasks.values()]
        await asyncio.gather(*tasks)

        self.tasks.clear()

    def get_task_status(self) -> dict[str, dict[str, Any]]:
        """Get status of all tasks"""
        status = {}
        for name, task in self.tasks.items():
            status[name] = {
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'next_run': task.next_run.isoformat() if task.next_run else None,
                'run_count': task.run_count,
                'error_count': task.error_count,
                'interval': task.interval,
            }
        return status
