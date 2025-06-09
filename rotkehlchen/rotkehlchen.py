"""Async implementation of main Rotkehlchen class

This is the async equivalent of the main Rotkehlchen class,
providing a clean asyncio-based API.
"""
import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.accountant import Accountant
from rotkehlchen.api.server import APIServer
from rotkehlchen.api.v1.auth import AuthManager
from rotkehlchen.api.websockets.notifier import RotkiNotifier
from rotkehlchen.chain.aggregator import ChainsAggregator
from rotkehlchen.chain.ethereum.manager import EthereumInquirer
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.handler import DBHandler
from rotkehlchen.exchanges.manager import ExchangeManager
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import CryptoCompare
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

from rotkehlchen.tasks.manager import TaskManager
from rotkehlchen.types import Timestamp
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.premium.premium import Premium

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Rotkehlchen:
    """Main async Rotkehlchen class coordinating all modules"""

    def __init__(
        self,
        data_dir: Path,
        args: Any,
    ):
        self.data_dir = data_dir
        self.args = args

        # Message aggregator for user notifications
        self.msg_aggregator = MessagesAggregator()

        # Database handler
        self.data = DataHandler(
            data_dir=data_dir,
            msg_aggregator=self.msg_aggregator,
        )

        # Async database
        self.async_db: DBHandler | None = None

        # WebSocket notifier
        self.ws_notifier = RotkiNotifier()

        # Task manager
        self.task_manager = TaskManager(self.msg_aggregator)

        # Auth manager
        self.auth_manager: AuthManager | None = None

        # Exchange manager
        self.exchange_manager: AsyncExchangeManager | None = None

        # Chains aggregator
        self.chains_aggregator: ChainsAggregator | None = None

        # Task orchestrator
        self.task_orchestrator: AsyncTaskOrchestrator | None = None

        # API server
        self.api_server: AsyncAPIServer | None = None

        # Price historian
        self.price_historian: PriceHistorian | None = None

        # Accountant
        self.accountant: Accountant | None = None

        # Premium
        self.premium: Premium | None = None

        # Running flag
        self._running = False

    async def initialize(self):
        """Initialize all async components"""
        log.info('Initializing AsyncRotkehlchen')

        try:
            # Initialize async database
            self.async_db = DBHandler(
                db_path=self.data.user_data_dir,
                password=self.args.sqlite_init_code,
                msg_aggregator=self.msg_aggregator,
            )
            await self.async_db.initialize()

            # Initialize auth manager
            self.auth_manager = AuthManager(self.async_db)

            # Initialize inquirer (singleton)
            Inquirer(
                data_dir=self.data_dir,
                cryptocompare=CryptoCompare(self.data_dir),
                coingecko=Coingecko(),
            )

            # Initialize price historian
            self.price_historian = PriceHistorian(
                data_directory=self.data_dir,
                cryptocompare=CryptoCompare(self.data_dir),
                coingecko=Coingecko(),
            )

            # Initialize chains aggregator with async node inquirers
            await self._initialize_chains()

            # Initialize exchange manager
            self.exchange_manager = AsyncExchangeManager(
                database=self.data.db,
                msg_aggregator=self.msg_aggregator,
            )

            # Initialize accountant
            self.accountant = Accountant(
                db=self.data.db,
                user_directory=self.data.user_data_dir,
                msg_aggregator=self.msg_aggregator,
                chains_aggregator=self.chains_aggregator,
            )

            # Initialize task orchestrator
            self.task_orchestrator = AsyncTaskOrchestrator(
                chains_aggregator=self.chains_aggregator,
                async_db=self.async_db,
                ws_notifier=self.ws_notifier,
                inquirer=Inquirer(),
            )

            # Initialize API server
            self.api_server = APIServer(
                rotkehlchen=self,
                ws_notifier=self.ws_notifier,
                cors_domain_list=self.args.cors_domain_list,
                db_handler=self.data.db,
                task_manager=self.task_manager,
            )

            # Inject dependencies
            self.api_server.app.state.auth_manager = self.auth_manager

            log.info('AsyncRotkehlchen initialization complete')

        except Exception as e:
            log.error(f'Failed to initialize AsyncRotkehlchen: {e}')
            raise

    async def _initialize_chains(self):
        """Initialize blockchain connections with async node inquirers"""
        # Would implement proper chain initialization
        # For now, create a basic setup
        self.chains_aggregator = ChainsAggregator(
            blockchain_accounts=[],
            data_directory=self.data_dir,
            ethereum_inquirer=EthereumInquirer(
                task_manager=TaskManager(self.msg_aggregator),
                database=self.data.db,
                connect_at_start=[],
            ),
            msg_aggregator=self.msg_aggregator,
            database=self.data.db,
            task_manager=TaskManager(self.msg_aggregator),
            premium=self.premium,
            eth_modules=[],
            data_updater=None,
        )

    async def start(self):
        """Start all async services"""
        if self._running:
            return

        log.info('Starting AsyncRotkehlchen services')

        try:
            # Start WebSocket notifier
            await self.ws_notifier.start()

            # Start task manager
            await self.task_manager.start()

            # Start background tasks
            await self.task_orchestrator.start()

            # Start API server
            server_task = asyncio.create_task(
                self.api_server.start(
                    host=self.args.api_host,
                    rest_port=self.args.api_port,
                ),
            )

            self._running = True
            log.info('AsyncRotkehlchen services started')

            # Keep running until stopped
            await server_task

        except Exception as e:
            log.error(f'Error starting services: {e}')
            await self.stop()
            raise

    async def stop(self):
        """Stop all async services"""
        if not self._running:
            return

        log.info('Stopping AsyncRotkehlchen services')

        try:
            # Stop API server
            if self.api_server:
                await self.api_server.stop()

            # Stop background tasks
            if self.task_orchestrator:
                await self.task_orchestrator.stop()

            # Stop task manager
            if self.task_manager:
                await self.task_manager.stop()

            # Stop WebSocket notifier
            if self.ws_notifier:
                await self.ws_notifier.stop()

            # Close exchange connections
            if self.exchange_manager:
                await self.exchange_manager.close_all()

            # Close database
            if self.async_db:
                await self.async_db.close()

            self._running = False
            log.info('AsyncRotkehlchen services stopped')

        except Exception as e:
            log.error(f'Error stopping services: {e}')

    async def unlock_user(
        self,
        username: str,
        password: str,
        create_new: bool = False,
    ) -> dict[str, Any]:
        """Unlock user database"""
        if create_new:
            user_data = await self.auth_manager.create_user(
                username=username,
                password=password,
            )
        else:
            # Verify password
            # Would implement proper unlock logic
            user_data = {
                'username': username,
                'user_id': 1,
            }

        # Load user settings
        settings = await self.async_db.get_settings()

        return {
            'user': user_data,
            'settings': settings,
        }

    def get_settings(self) -> dict[str, Any]:
        """Get current settings"""
        # Would implement async version
        return {
            'main_currency': A_USD.identifier,
            'version': 1,
        }

    async def query_balances(self) -> dict[str, Any]:
        """Query all balances"""
        tasks = []

        # Blockchain balances
        if self.chains_aggregator:
            tasks.append(self._query_blockchain_balances())

        # Exchange balances
        if self.exchange_manager:
            tasks.append(self._query_exchange_balances())

        # Manual balances
        tasks.append(self._query_manual_balances())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_balances = {}
        for result in results:
            if isinstance(result, dict):
                all_balances.update(result)
            elif isinstance(result, Exception):
                log.error(f'Error querying balances: {result}')

        return all_balances

    async def _query_blockchain_balances(self) -> dict[str, Any]:
        """Query blockchain balances"""
        # Would implement proper balance querying
        return {'blockchain': {}}

    async def _query_exchange_balances(self) -> dict[str, Any]:
        """Query exchange balances"""
        balances = await self.exchange_manager.get_all_balances()
        return {'exchanges': balances}

    async def _query_manual_balances(self) -> dict[str, Any]:
        """Query manual balances"""
        # Would implement manual balance querying
        return {'manual': {}}

    async def process_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> dict[str, Any]:
        """Process history for given time range"""
        # Spawn as background task
        task = await self.task_manager.spawn_and_track(
            task_name='process_history',
            coro=self._do_process_history(start_ts, end_ts),
            timeout=3600,  # 1 hour timeout
        )

        return {
            'task_id': task.id,
            'status': 'processing',
        }

    async def _do_process_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> dict[str, Any]:
        """Actually process history"""
        # Would implement full history processing
        await asyncio.sleep(1)  # Simulate work

        return {
            'events': 1000,
            'trades': 500,
        }


async def create_app(args: Any) -> AsyncRotkehlchen:
    """Create and initialize AsyncRotkehlchen app"""
    # Setup data directory
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        data_dir.mkdir(parents=True)

    # Create app
    app = AsyncRotkehlchen(data_dir=data_dir, args=args)

    # Initialize
    await app.initialize()

    return app


async def main():
    """Main entry point for async Rotkehlchen"""
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', default='~/.rotki')
    parser.add_argument('--api-host', default='127.0.0.1')
    parser.add_argument('--api-port', type=int, default=5042)
    parser.add_argument('--cors-domain-list', nargs='*', default=[])
    parser.add_argument('--sqlite-init-code', default='')

    args = parser.parse_args()

    # Create and start app
    app = await create_app(args)

    try:
        await app.start()
    except KeyboardInterrupt:
        log.info('Received interrupt signal')
    finally:
        await app.stop()


if __name__ == '__main__':
    asyncio.run(main())
