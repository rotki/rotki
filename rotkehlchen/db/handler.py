"""Async database handler for gradual migration from DBHandler

This provides async equivalents of DBHandler methods while maintaining
compatibility with the existing codebase.
"""
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Optional

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.drivers.async_sqlcipher import AsyncDBConnection, DBConnectionWrapper
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AsyncDBHandler:
    """Async version of DBHandler for migrated endpoints
    
    This class provides async methods while maintaining compatibility
    with the sync DBHandler interface during the migration period.
    """
    
    def __init__(
        self,
        db_path: Path,
        password: str,
        msg_aggregator: MessagesAggregator,
        sql_vm_instructions_cb: int = 0,
    ):
        self.db_path = db_path
        self.password = password
        self.msg_aggregator = msg_aggregator
        
        # Create async connection
        self.async_conn = AsyncDBConnection(
            path=db_path / 'rotkehlchen.db',
            password=password,
            timeout=30.0,
            max_connections=10,
        )
        
        # Compatibility wrapper
        self.conn = DBConnectionWrapper(self.async_conn)
        
        # Cache for settings
        self._settings_cache: Optional[dict[str, Any]] = None
        
    async def initialize(self):
        """Initialize the async database connection"""
        await self.async_conn.initialize()
        
        # Load initial settings into cache
        async with self.async_conn.read_ctx() as cursor:
            await cursor.execute('SELECT name, value FROM settings')
            rows = await cursor.fetchall()
            
            self._settings_cache = {}
            for name, value in rows:
                try:
                    self._settings_cache[name] = json.loads(value)
                except json.JSONDecodeError:
                    self._settings_cache[name] = value
    
    async def get_settings(self) -> dict[str, Any]:
        """Get all settings asynchronously"""
        if self._settings_cache is None:
            await self.initialize()
            
        return self._settings_cache.copy()
    
    async def get_setting(self, name: str) -> Optional[Any]:
        """Get a specific setting value"""
        if self._settings_cache is None:
            await self.initialize()
            
        return self._settings_cache.get(name)
    
    async def set_settings(self, settings: ModifiableDBSettings) -> dict[str, Any]:
        """Update settings asynchronously"""
        async with self.async_conn.write_ctx() as cursor:
            for setting_name, value in settings:
                if value is not None:
                    # Update in database
                    json_value = json.dumps(value)
                    await cursor.execute(
                        'INSERT OR REPLACE INTO settings(name, value) VALUES(?, ?)',
                        (setting_name, json_value)
                    )
                    # Update cache
                    if self._settings_cache is not None:
                        self._settings_cache[setting_name] = value
        
        return await self.get_settings()
    
    async def get_main_currency(self) -> Asset:
        """Get the main currency setting"""
        currency_str = await self.get_setting('main_currency')
        if currency_str:
            return Asset(currency_str)
        return A_USD
    
    async def get_cache_for_api(self) -> dict[str, Any]:
        """Get cached values for API responses"""
        cache = {}
        
        async with self.async_conn.read_ctx() as cursor:
            # Get last data upload timestamp
            await cursor.execute(
                'SELECT value FROM key_value_cache WHERE name=?',
                ('last_data_upload_ts',)
            )
            result = await cursor.fetchone()
            if result:
                cache['last_data_upload_ts'] = int(result[0])
            else:
                cache['last_data_upload_ts'] = 0
                
            # Get last balance save timestamp
            await cursor.execute(
                'SELECT MAX(timestamp) FROM balance_snapshots'
            )
            result = await cursor.fetchone()
            if result and result[0]:
                cache['last_balance_save'] = result[0]
            else:
                cache['last_balance_save'] = 0
        
        return cache
    
    async def query_balances(
        self,
        location: Optional[Location] = None,
        asset: Optional[Asset] = None,
    ) -> dict[Asset, Balance]:
        """Query current balances"""
        balances = {}
        
        query = 'SELECT asset, amount, usd_value FROM balances WHERE 1=1'
        params = []
        
        if location:
            query += ' AND location=?'
            params.append(location.serialize())
            
        if asset:
            query += ' AND asset=?'
            params.append(asset.identifier)
            
        async with self.async_conn.read_ctx() as cursor:
            await cursor.execute(query, tuple(params) if params else None)
            rows = await cursor.fetchall()
            
            for asset_id, amount, usd_value in rows:
                asset_obj = Asset(asset_id)
                balances[asset_obj] = Balance(
                    amount=FVal(amount),
                    usd_value=FVal(usd_value),
                )
        
        return balances
    
    async def get_history_events_count(
        self,
        filter_query: Optional[str] = None,
        filter_params: Optional[list] = None,
    ) -> int:
        """Get count of history events matching filters"""
        query = 'SELECT COUNT(*) FROM history_events'
        
        if filter_query:
            query += f' WHERE {filter_query}'
            
        async with self.async_conn.read_ctx() as cursor:
            if filter_params:
                await cursor.execute(query, tuple(filter_params))
            else:
                await cursor.execute(query)
            result = await cursor.fetchone()
            
        return result[0] if result else 0
    
    async def get_history_events(
        self,
        filter_query: Optional[str] = None,
        filter_params: Optional[list] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: str = 'timestamp DESC',
    ) -> list[dict[str, Any]]:
        """Query history events asynchronously"""
        query = '''
            SELECT 
                identifier, event_identifier, sequence_index, timestamp,
                location, location_label, asset, balance, notes,
                event_type, event_subtype
            FROM history_events
        '''
        
        if filter_query:
            query += f' WHERE {filter_query}'
            
        query += f' ORDER BY {order_by}'
        
        if limit:
            query += f' LIMIT {limit}'
            if offset:
                query += f' OFFSET {offset}'
                
        async with self.async_conn.read_ctx() as cursor:
            if filter_params:
                await cursor.execute(query, tuple(filter_params))
            else:
                await cursor.execute(query)
            rows = await cursor.fetchall()
            
        events = []
        for row in rows:
            events.append({
                'identifier': row[0],
                'event_identifier': row[1],
                'sequence_index': row[2],
                'timestamp': row[3],
                'location': row[4],
                'location_label': row[5],
                'asset': row[6],
                'balance': row[7],
                'notes': row[8],
                'event_type': row[9],
                'event_subtype': row[10],
            })
            
        return events
    
    async def add_history_event(self, event_data: dict[str, Any]) -> int:
        """Add a new history event"""
        async with self.async_conn.write_ctx() as cursor:
            await cursor.execute('''
                INSERT INTO history_events (
                    event_identifier, sequence_index, timestamp,
                    location, location_label, asset, balance, notes,
                    event_type, event_subtype
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_data['event_identifier'],
                event_data.get('sequence_index', 0),
                event_data['timestamp'],
                event_data['location'],
                event_data.get('location_label'),
                event_data['asset'],
                str(event_data['balance']),
                event_data.get('notes'),
                event_data['event_type'],
                event_data.get('event_subtype'),
            ))
            
            return cursor.lastrowid
    
    async def get_transactions_count(
        self,
        chain: Optional[str] = None,
        address: Optional[str] = None,
        from_ts: Optional[Timestamp] = None,
        to_ts: Optional[Timestamp] = None,
    ) -> int:
        """Get count of transactions matching filters"""
        query = 'SELECT COUNT(*) FROM ethereum_transactions WHERE 1=1'
        params = []
        
        if chain:
            query += ' AND chain=?'
            params.append(chain)
            
        if address:
            query += ' AND (from_address=? OR to_address=?)'
            params.extend([address, address])
            
        if from_ts:
            query += ' AND timestamp >= ?'
            params.append(from_ts)
            
        if to_ts:
            query += ' AND timestamp <= ?'
            params.append(to_ts)
            
        async with self.async_conn.read_ctx() as cursor:
            await cursor.execute(query, tuple(params) if params else None)
            result = await cursor.fetchone()
            
        return result[0] if result else 0
    
    async def close(self):
        """Close the async database connection"""
        await self.async_conn.close()
    
    # Sync compatibility methods
    def get_settings_sync(self) -> dict[str, Any]:
        """Synchronous version for compatibility"""
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.get_settings())
        finally:
            loop.close()


# Factory function to create appropriate handler based on feature flags
def create_db_handler(
    db_path: Path,
    password: str,
    msg_aggregator: MessagesAggregator,
    use_async: bool = False,
) -> DBHandler | AsyncDBHandler:
    """Create appropriate database handler based on feature flags"""
    if use_async:
        return AsyncDBHandler(db_path, password, msg_aggregator)
    else:
        return DBHandler(db_path, password, msg_aggregator)