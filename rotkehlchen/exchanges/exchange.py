"""Async implementation of exchange base class

Replaces gevent-based exchange implementations with native asyncio.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

import aiohttp
from aiohttp import ClientError, ClientTimeout

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.data_structures import AssetMovement, MarginPosition, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ApiKey, ApiSecret, Location, Timestamp
from rotkehlchen.utils.misc import ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AsyncExchangeInterface(ABC):
    """Async interface for exchange implementations"""

    def __init__(
        self,
        name: str,
        location: Location,
        api_key: ApiKey,
        secret: ApiSecret,
        database: Any,
        msg_aggregator: Any,
    ):
        self.name = name
        self.location = location
        self.api_key = api_key
        self.secret = secret
        self.database = database
        self.msg_aggregator = msg_aggregator

        # HTTP session configuration
        self.session: aiohttp.ClientSession | None = None
        self.timeout = ClientTimeout(total=30)
        self.rate_limit = asyncio.Semaphore(10)  # Max concurrent requests

        # Cache
        self._balances_cache: dict[Asset, Balance] = {}
        self._cache_timestamp: Timestamp = Timestamp(0)
        self.cache_ttl = 300  # 5 minutes

    async def initialize(self):
        """Initialize async resources"""
        if self.session is None:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=20,
            )
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
            )

    async def close(self):
        """Clean up async resources"""
        if self.session:
            await self.session.close()
            self.session = None

    @abstractmethod
    async def query_balances(self) -> dict[Asset, Balance]:
        """Query account balances - must be implemented by each exchange"""

    @abstractmethod
    async def query_trade_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query trade history - must be implemented by each exchange"""

    async def _api_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make an API request with rate limiting and error handling"""
        if self.session is None:
            await self.initialize()

        async with self.rate_limit:  # Rate limiting
            try:
                async with self.session.request(
                    method=method,
                    url=endpoint,
                    params=params,
                    json=json_data,
                    headers=headers,
                ) as response:
                    response.raise_for_status()
                    return await response.json()

            except ClientError as e:
                log.error(f'{self.name} API request failed: {e}')
                raise RemoteError(f'{self.name} API error: {e}') from e

    async def get_balances_with_cache(
        self,
        force_refresh: bool = False,
    ) -> dict[Asset, Balance]:
        """Get balances with caching"""
        now = ts_now()

        # Check cache
        if (
            not force_refresh and
            self._balances_cache and
            now - self._cache_timestamp < self.cache_ttl
        ):
            return self._balances_cache.copy()

        # Query fresh balances
        balances = await self.query_balances()

        # Update cache
        self._balances_cache = balances
        self._cache_timestamp = now

        return balances

    async def query_deposits_withdrawals(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[AssetMovement]:
        """Query deposits and withdrawals - can be overridden"""
        return []

    async def query_margin_positions(self) -> list[MarginPosition]:
        """Query margin positions - can be overridden"""
        return []


class AsyncKraken(AsyncExchangeInterface):
    """Async implementation of Kraken exchange"""

    def __init__(self, *args, **kwargs):
        super().__init__('kraken', Location.KRAKEN, *args, **kwargs)
        self.base_url = 'https://api.kraken.com'

    async def query_balances(self) -> dict[Asset, Balance]:
        """Query Kraken account balances"""
        endpoint = f'{self.base_url}/0/private/Balance'

        # Would implement proper signature generation
        headers = self._generate_headers('Balance', {})

        response = await self._api_request(
            method='POST',
            endpoint=endpoint,
            headers=headers,
        )

        balances = {}
        if response.get('error'):
            raise RemoteError(f"Kraken error: {response['error']}")

        for asset_str, amount_str in response.get('result', {}).items():
            # Convert Kraken asset names
            asset = self._deserialize_asset(asset_str)
            amount = FVal(amount_str)

            if amount > ZERO:
                # Would query USD value
                usd_value = amount * FVal('1')  # Placeholder
                balances[asset] = Balance(amount=amount, usd_value=usd_value)

        return balances

    async def query_trade_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query Kraken trade history"""
        endpoint = f'{self.base_url}/0/private/TradesHistory'

        params = {
            'start': start_ts,
            'end': end_ts,
        }

        headers = self._generate_headers('TradesHistory', params)

        response = await self._api_request(
            method='POST',
            endpoint=endpoint,
            json_data=params,
            headers=headers,
        )

        trades = []
        if response.get('error'):
            raise RemoteError(f"Kraken error: {response['error']}")

        for trade_id, trade_data in response.get('result', {}).get('trades', {}).items():
            # Parse trade data
            trade = self._deserialize_trade(trade_id, trade_data)
            trades.append(trade)

        return trades

    def _generate_headers(self, endpoint: str, data: dict) -> dict[str, str]:
        """Generate API headers with signature"""
        # Would implement proper Kraken signature generation
        return {
            'API-Key': self.api_key,
            'API-Sign': 'signature',
        }

    def _deserialize_asset(self, kraken_asset: str) -> Asset:
        """Convert Kraken asset name to standard"""
        # Would implement proper mapping
        return Asset(kraken_asset)

    def _deserialize_trade(self, trade_id: str, trade_data: dict) -> Trade:
        """Deserialize Kraken trade data"""
        # Would implement proper deserialization
        return Trade(
            timestamp=Timestamp(int(trade_data['time'])),
            location=self.location,
            base_asset=Asset('ETH'),
            quote_asset=Asset('USD'),
            trade_type='buy',
            amount=FVal(trade_data['vol']),
            rate=FVal(trade_data['price']),
            fee=FVal(trade_data['fee']),
            fee_currency=Asset('USD'),
            link=trade_id,
        )


class AsyncBinance(AsyncExchangeInterface):
    """Async implementation of Binance exchange"""

    def __init__(self, *args, **kwargs):
        super().__init__('binance', Location.BINANCE, *args, **kwargs)
        self.base_url = 'https://api.binance.com'

    async def query_balances(self) -> dict[Asset, Balance]:
        """Query Binance account balances"""
        endpoint = f'{self.base_url}/api/v3/account'

        # Would implement proper signature generation
        params = {
            'timestamp': ts_now() * 1000,
        }
        params['signature'] = self._generate_signature(params)

        headers = {
            'X-MBX-APIKEY': self.api_key,
        }

        response = await self._api_request(
            method='GET',
            endpoint=endpoint,
            params=params,
            headers=headers,
        )

        balances = {}
        for balance_data in response.get('balances', []):
            asset_str = balance_data['asset']
            free = FVal(balance_data['free'])
            locked = FVal(balance_data['locked'])
            amount = free + locked

            if amount > ZERO:
                asset = Asset(asset_str)
                # Would query USD value
                usd_value = amount * FVal('1')  # Placeholder
                balances[asset] = Balance(amount=amount, usd_value=usd_value)

        return balances

    async def query_trade_history(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query Binance trade history"""
        # Would implement pagination for large histories
        all_trades = []

        # Query each trading pair
        pairs = await self._get_traded_pairs(start_ts, end_ts)

        tasks = []
        for pair in pairs:
            task = self._query_pair_trades(pair, start_ts, end_ts)
            tasks.append(task)

        # Query all pairs concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_trades.extend(result)
            elif isinstance(result, Exception):
                log.error(f'Error querying trades: {result}')

        return all_trades

    async def _get_traded_pairs(
        self,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[str]:
        """Get list of traded pairs in time range"""
        # Would query from database or API
        return ['ETHUSDT', 'BTCUSDT']

    async def _query_pair_trades(
        self,
        symbol: str,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> list[Trade]:
        """Query trades for a specific pair"""
        endpoint = f'{self.base_url}/api/v3/myTrades'

        params = {
            'symbol': symbol,
            'startTime': start_ts * 1000,
            'endTime': end_ts * 1000,
            'timestamp': ts_now() * 1000,
        }
        params['signature'] = self._generate_signature(params)

        headers = {
            'X-MBX-APIKEY': self.api_key,
        }

        response = await self._api_request(
            method='GET',
            endpoint=endpoint,
            params=params,
            headers=headers,
        )

        trades = []
        for trade_data in response:
            trade = self._deserialize_trade(trade_data)
            trades.append(trade)

        return trades

    def _generate_signature(self, params: dict) -> str:
        """Generate Binance signature"""
        # Would implement proper HMAC signature
        return 'signature'

    def _deserialize_trade(self, trade_data: dict) -> Trade:
        """Deserialize Binance trade data"""
        # Would implement proper deserialization
        return Trade(
            timestamp=Timestamp(trade_data['time'] // 1000),
            location=self.location,
            base_asset=Asset('ETH'),
            quote_asset=Asset('USDT'),
            trade_type='buy' if trade_data['isBuyer'] else 'sell',
            amount=FVal(trade_data['qty']),
            rate=FVal(trade_data['price']),
            fee=FVal(trade_data['commission']),
            fee_currency=Asset(trade_data['commissionAsset']),
            link=str(trade_data['id']),
        )


class AsyncExchangeManager:
    """Manages multiple async exchange connections"""

    def __init__(self, database: Any, msg_aggregator: Any):
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.exchanges: dict[Location, AsyncExchangeInterface] = {}

    async def add_exchange(
        self,
        location: Location,
        api_key: ApiKey,
        api_secret: ApiSecret,
    ) -> AsyncExchangeInterface:
        """Add a new exchange connection"""
        # Create appropriate exchange instance
        if location == Location.KRAKEN:
            exchange = AsyncKraken(
                api_key=api_key,
                secret=api_secret,
                database=self.database,
                msg_aggregator=self.msg_aggregator,
            )
        elif location == Location.BINANCE:
            exchange = AsyncBinance(
                api_key=api_key,
                secret=api_secret,
                database=self.database,
                msg_aggregator=self.msg_aggregator,
            )
        else:
            raise ValueError(f'Unsupported exchange: {location}')

        await exchange.initialize()
        self.exchanges[location] = exchange

        return exchange

    async def remove_exchange(self, location: Location):
        """Remove an exchange connection"""
        if location in self.exchanges:
            await self.exchanges[location].close()
            del self.exchanges[location]

    async def get_all_balances(self) -> dict[Location, dict[Asset, Balance]]:
        """Get balances from all connected exchanges"""
        tasks = {}
        for location, exchange in self.exchanges.items():
            tasks[location] = exchange.get_balances_with_cache()

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)

        all_balances = {}
        for location, result in zip(tasks.keys(), results, strict=False):
            if isinstance(result, dict):
                all_balances[location] = result
            elif isinstance(result, Exception):
                log.error(f'Error getting {location} balances: {result}')
                all_balances[location] = {}

        return all_balances

    async def close_all(self):
        """Close all exchange connections"""
        tasks = [exchange.close() for exchange in self.exchanges.values()]
        await asyncio.gather(*tasks)
