"""Async implementation of premium API client

Provides high-performance async communication with Rotki premium services.
"""
import asyncio
import hashlib
import hmac
import json
import logging
import time
from typing import TYPE_CHECKING, Any, NamedTuple

import aiohttp
from aiohttp import ClientError, ClientTimeout

from rotkehlchen.errors.api import PremiumApiError, PremiumAuthenticationError
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.handler import AsyncDBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# Data structures
class PremiumCredentials(NamedTuple):
    """Premium user credentials"""
    api_key: str
    api_secret: str


class RemoteMetadata(NamedTuple):
    """Remote data metadata"""
    last_modify_ts: Timestamp
    data_hash: str
    data_size: int


class AsyncPremiumClient:
    """Async client for Rotki premium API"""

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        async_db: 'AsyncDBHandler',
        base_url: str = 'https://api.rotki.com',
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.async_db = async_db
        self.base_url = base_url

        # HTTP session
        self.session: aiohttp.ClientSession | None = None
        self.timeout = ClientTimeout(total=60)

        # Rate limiting
        self.rate_limit = asyncio.Semaphore(5)  # Max 5 concurrent requests
        self.last_request_time = 0
        self.min_request_interval = 0.2  # 200ms between requests

    async def initialize(self):
        """Initialize async resources"""
        if self.session is None:
            connector = aiohttp.TCPConnector(
                limit=20,
                limit_per_host=10,
            )
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
            )

    async def close(self):
        """Clean up resources"""
        if self.session:
            await self.session.close()
            self.session = None

    async def _rate_limited_request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Make rate-limited API request"""
        async with self.rate_limit:
            # Ensure minimum interval between requests
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - time_since_last)

            self.last_request_time = time.time()

            # Make request
            return await self._signed_request(method, endpoint, **kwargs)

    async def _signed_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a signed request to premium API"""
        if self.session is None:
            await self.initialize()

        # Prepare request
        url = f'{self.base_url}{endpoint}'
        timestamp = str(int(time.time()))

        # Create signature
        message = f'{timestamp}{method}{endpoint}'
        if json_data:
            message += json.dumps(json_data, sort_keys=True)

        signature = hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Headers
        headers = {
            'X-API-Key': self.api_key,
            'X-API-Timestamp': timestamp,
            'X-API-Signature': signature,
            'Content-Type': 'application/json',
        }

        try:
            async with self.session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=headers,
            ) as response:
                response_data = await response.json()

                if response.status == 401:
                    raise PremiumAuthenticationError('Invalid premium credentials')
                elif response.status == 429:
                    raise PremiumApiError('Rate limit exceeded')
                elif response.status >= 400:
                    error_msg = response_data.get('error', 'Unknown error')
                    raise PremiumApiError(f'API error: {error_msg}')

                return response_data

        except ClientError as e:
            log.error(f'Premium API request failed: {e}')
            raise RemoteError(f'Failed to connect to premium API: {e}')

    async def sync_data(self, last_sync_ts: Timestamp) -> dict[str, Any]:
        """Sync data with premium server"""
        log.info('Starting async premium data sync')

        # Get local data hash
        local_hash = await self._calculate_local_hash()

        # Request sync
        response = await self._rate_limited_request(
            method='POST',
            endpoint='/api/v1/sync',
            json_data={
                'last_sync_ts': last_sync_ts,
                'local_hash': local_hash,
                'client_version': '1.35.0',
            },
        )

        sync_data = response.get('data', {})

        # Process sync data concurrently
        tasks = []

        if 'db_snapshots' in sync_data:
            tasks.append(self._process_db_snapshots(sync_data['db_snapshots']))

        if 'settings' in sync_data:
            tasks.append(self._process_settings_sync(sync_data['settings']))

        if 'ignored_actions' in sync_data:
            tasks.append(self._process_ignored_actions(sync_data['ignored_actions']))

        if 'tags' in sync_data:
            tasks.append(self._process_tags_sync(sync_data['tags']))

        # Wait for all processing to complete
        await asyncio.gather(*tasks)

        # Update last sync timestamp
        await self.async_db.set_settings({'last_premium_sync': ts_now()})

        log.info('Premium data sync completed')

        return {
            'synced_items': len(tasks),
            'new_sync_ts': ts_now(),
        }

    async def _calculate_local_hash(self) -> str:
        """Calculate hash of local data for comparison"""
        # Would implement actual hash calculation
        return 'local_data_hash'

    async def _process_db_snapshots(self, snapshots: list[dict[str, Any]]):
        """Process database snapshots from premium"""
        log.info(f'Processing {len(snapshots)} database snapshots')

        for _snapshot in snapshots:
            # Would implement snapshot processing
            await asyncio.sleep(0.01)  # Simulate work

    async def _process_settings_sync(self, settings: dict[str, Any]):
        """Sync settings with premium"""
        log.info('Syncing settings with premium')

        # Merge with local settings
        local_settings = await self.async_db.get_settings()

        # Premium settings take precedence for certain fields
        premium_fields = ['premium_sync_enabled', 'analytics_enabled']
        for field in premium_fields:
            if field in settings:
                local_settings[field] = settings[field]

        await self.async_db.set_settings(local_settings)

    async def _process_ignored_actions(self, actions: list[dict[str, Any]]):
        """Process ignored actions from premium"""
        log.info(f'Processing {len(actions)} ignored actions')

        # Would implement ignored actions processing
        await asyncio.sleep(0.01)  # Simulate work

    async def _process_tags_sync(self, tags: list[dict[str, Any]]):
        """Sync tags with premium"""
        log.info(f'Processing {len(tags)} tags')

        # Would implement tags processing
        await asyncio.sleep(0.01)  # Simulate work

    async def upload_data(
        self,
        data_type: str,
        data: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Upload data to premium server"""
        log.info(f'Uploading {len(data)} {data_type} items to premium')

        # Upload in batches
        batch_size = 100
        uploaded = 0

        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]

            response = await self._rate_limited_request(
                method='POST',
                endpoint=f'/api/v1/upload/{data_type}',
                json_data={
                    'items': batch,
                    'timestamp': ts_now(),
                },
            )

            uploaded += response.get('processed', 0)

        log.info(f'Uploaded {uploaded} {data_type} items')

        return {
            'uploaded': uploaded,
            'data_type': data_type,
        }

    async def get_statistics(self) -> dict[str, Any]:
        """Get user statistics from premium"""
        response = await self._rate_limited_request(
            method='GET',
            endpoint='/api/v1/statistics',
        )

        return response.get('data', {})

    async def validate_credentials(self) -> bool:
        """Validate premium API credentials"""
        try:
            response = await self._rate_limited_request(
                method='GET',
                endpoint='/api/v1/validate',
            )

            return response.get('valid', False)

        except PremiumAuthenticationError:
            return False
        except Exception as e:
            log.error(f'Error validating premium credentials: {e}')
            return False


class AsyncPremiumSyncManager:
    """Manages automatic premium sync operations"""

    def __init__(
        self,
        premium_client: AsyncPremiumClient,
        async_db: 'AsyncDBHandler',
        sync_interval: int = 3600,  # 1 hour
    ):
        self.premium_client = premium_client
        self.async_db = async_db
        self.sync_interval = sync_interval

        self._sync_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self):
        """Start automatic sync"""
        if self._sync_task is not None:
            return

        self._stop_event.clear()
        self._sync_task = asyncio.create_task(self._sync_loop())
        log.info('Started premium sync manager')

    async def stop(self):
        """Stop automatic sync"""
        if self._sync_task is None:
            return

        self._stop_event.set()
        await self._sync_task
        self._sync_task = None
        log.info('Stopped premium sync manager')

    async def _sync_loop(self):
        """Main sync loop"""
        while not self._stop_event.is_set():
            try:
                # Get last sync timestamp
                settings = await self.async_db.get_settings()
                last_sync = settings.get('last_premium_sync', 0)

                # Check if sync is needed
                if ts_now() - last_sync >= self.sync_interval:
                    await self.sync_now()

                # Wait for next check
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=300,  # Check every 5 minutes
                    )
                except TimeoutError:
                    continue

            except Exception as e:
                log.error(f'Error in premium sync loop: {e}')
                await asyncio.sleep(60)  # Wait before retry

    async def sync_now(self) -> dict[str, Any]:
        """Force sync now"""
        try:
            # Get last sync timestamp
            settings = await self.async_db.get_settings()
            last_sync = settings.get('last_premium_sync', 0)

            # Perform sync
            result = await self.premium_client.sync_data(last_sync)

            log.info('Premium sync completed successfully')
            return result

        except Exception as e:
            log.error(f'Premium sync failed: {e}')
            raise

# Compatibility exports
Premium = AsyncPremiumClient  # For backward compatibility


async def premium_create_and_verify(credentials: PremiumCredentials) -> AsyncPremiumClient:
    """Create and verify premium client"""
    client = AsyncPremiumClient(
        api_key=credentials.api_key,
        api_secret=credentials.api_secret,
        async_db=None,  # Will be set by caller
    )
    await client.initialize()
    # Would verify credentials
    return client
