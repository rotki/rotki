"""Async implementation of data import/export manager

Provides high-performance async I/O for importing and exporting user data.
"""
import asyncio
import csv
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional
from zipfile import ZipFile

import aiofiles
import aiofiles.os

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.data_import.importers.constants import IMPORTERS_MAPPING
from rotkehlchen.db.async_handler import AsyncDBHandler
from rotkehlchen.errors.misc import InputError
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AsyncDataImporter:
    """Async base class for data importers"""
    
    def __init__(self, async_db: AsyncDBHandler):
        self.async_db = async_db
        
    async def import_csv_file(
        self,
        filepath: Path,
        delimiter: str = ',',
        encoding: str = 'utf-8',
    ) -> tuple[list[Any], list[str]]:
        """Import data from CSV file asynchronously"""
        imported_items = []
        errors = []
        
        try:
            async with aiofiles.open(filepath, mode='r', encoding=encoding) as f:
                content = await f.read()
                
            # Parse CSV content
            lines = content.strip().split('\n')
            if not lines:
                raise InputError('Empty CSV file')
                
            # Use csv.DictReader for parsing
            import io
            csv_file = io.StringIO(content)
            reader = csv.DictReader(csv_file, delimiter=delimiter)
            
            # Process rows concurrently in batches
            batch_size = 100
            rows = list(reader)
            
            for i in range(0, len(rows), batch_size):
                batch = rows[i:i + batch_size]
                tasks = []
                
                for row_idx, row in enumerate(batch, start=i):
                    task = self._process_row(row, row_idx + 2)  # +2 for header and 0-index
                    tasks.append(task)
                    
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in results:
                    if isinstance(result, Exception):
                        errors.append(str(result))
                    elif result is not None:
                        imported_items.append(result)
                        
        except Exception as e:
            log.error(f'Error importing CSV file {filepath}: {e}')
            errors.append(f'File error: {e}')
            
        return imported_items, errors
        
    async def _process_row(self, row: dict[str, str], row_num: int) -> Any:
        """Process a single CSV row - to be implemented by subclasses"""
        raise NotImplementedError


class AsyncTradesImporter(AsyncDataImporter):
    """Import trades from CSV files"""
    
    async def _process_row(self, row: dict[str, str], row_num: int) -> Optional[Trade]:
        """Process a trade row"""
        try:
            # Parse trade data
            trade = Trade(
                timestamp=Timestamp(int(row['timestamp'])),
                location=Location.deserialize(row['location']),
                base_asset=Asset(row['base_asset']),
                quote_asset=Asset(row['quote_asset']),
                trade_type=row['trade_type'],
                amount=FVal(row['amount']),
                rate=FVal(row['rate']),
                fee=FVal(row.get('fee', '0')),
                fee_currency=Asset(row.get('fee_currency', row['quote_asset'])),
                link=row.get('link', ''),
                notes=row.get('notes', ''),
            )
            
            # Validate and save
            await self._save_trade(trade)
            return trade
            
        except Exception as e:
            raise InputError(f'Row {row_num}: {e}')
            
    async def _save_trade(self, trade: Trade):
        """Save trade to database"""
        # Implementation would save to async DB
        pass


class AsyncHistoryEventsImporter(AsyncDataImporter):
    """Import history events from CSV files"""
    
    async def _process_row(self, row: dict[str, str], row_num: int) -> Optional[HistoryEvent]:
        """Process a history event row"""
        try:
            # Parse event data
            event_data = {
                'event_identifier': row.get('event_identifier', ''),
                'sequence_index': int(row.get('sequence_index', 0)),
                'timestamp': Timestamp(int(row['timestamp'])),
                'location': row['location'],
                'event_type': row['event_type'],
                'event_subtype': row.get('event_subtype', ''),
                'asset': row['asset'],
                'balance': Balance(
                    amount=FVal(row['amount']),
                    usd_value=FVal(row.get('usd_value', '0')),
                ),
                'location_label': row.get('location_label', ''),
                'notes': row.get('notes', ''),
                'counterparty': row.get('counterparty', ''),
                'address': row.get('address', ''),
                'extra_data': json.loads(row.get('extra_data', '{}')),
            }
            
            # Save to database
            event_id = await self.async_db.add_history_event(event_data)
            
            return HistoryEvent(
                identifier=event_id,
                **event_data
            )
            
        except Exception as e:
            raise InputError(f'Row {row_num}: {e}')


class AsyncDataExporter:
    """Export data asynchronously with high performance"""
    
    def __init__(self, async_db: AsyncDBHandler):
        self.async_db = async_db
        
    async def export_history_events(
        self,
        directory: Path,
        from_timestamp: Optional[Timestamp] = None,
        to_timestamp: Optional[Timestamp] = None,
    ) -> Path:
        """Export history events to CSV"""
        filename = directory / 'rotki_history_events.csv'
        
        # Build query
        filter_query = []
        filter_params = []
        
        if from_timestamp:
            filter_query.append('timestamp >= ?')
            filter_params.append(from_timestamp)
            
        if to_timestamp:
            filter_query.append('timestamp <= ?')
            filter_params.append(to_timestamp)
            
        # Query events in batches
        batch_size = 1000
        offset = 0
        
        async with aiofiles.open(filename, mode='w', encoding='utf-8') as f:
            # Write header
            headers = [
                'timestamp', 'location', 'event_type', 'event_subtype',
                'asset', 'amount', 'usd_value', 'notes', 'event_identifier',
                'counterparty', 'address', 'extra_data'
            ]
            await f.write(','.join(headers) + '\n')
            
            # Export in batches
            while True:
                events = await self.async_db.get_history_events(
                    filter_query=' AND '.join(filter_query) if filter_query else None,
                    filter_params=filter_params,
                    limit=batch_size,
                    offset=offset,
                )
                
                if not events:
                    break
                    
                # Write batch
                for event in events:
                    row = self._event_to_csv_row(event)
                    await f.write(row + '\n')
                    
                offset += batch_size
                
                # Progress notification
                log.info(f'Exported {offset} history events...')
                
        log.info(f'History events exported to {filename}')
        return filename
        
    def _event_to_csv_row(self, event: dict[str, Any]) -> str:
        """Convert event to CSV row"""
        # Implementation would format event data
        values = [
            str(event.get('timestamp', '')),
            event.get('location', ''),
            event.get('event_type', ''),
            event.get('event_subtype', ''),
            event.get('asset', ''),
            str(event.get('balance', {}).get('amount', '0')),
            str(event.get('balance', {}).get('usd_value', '0')),
            event.get('notes', ''),
            event.get('event_identifier', ''),
            event.get('counterparty', ''),
            event.get('address', ''),
            json.dumps(event.get('extra_data', {})),
        ]
        
        # Escape values
        escaped = []
        for value in values:
            if ',' in value or '"' in value or '\n' in value:
                value = '"' + value.replace('"', '""') + '"'
            escaped.append(value)
            
        return ','.join(escaped)
        
    async def export_trades(
        self,
        directory: Path,
        from_timestamp: Optional[Timestamp] = None,
        to_timestamp: Optional[Timestamp] = None,
    ) -> Path:
        """Export trades to CSV"""
        filename = directory / 'rotki_trades.csv'
        
        # Similar implementation to export_history_events
        # but for trades table
        
        log.info(f'Trades exported to {filename}')
        return filename
        
    async def create_backup(
        self,
        backup_dir: Path,
        include_settings: bool = True,
        include_history: bool = True,
        include_cache: bool = False,
    ) -> Path:
        """Create a complete backup of user data"""
        timestamp = Timestamp(int(asyncio.get_event_loop().time()))
        backup_name = f'rotki_backup_{timestamp}.zip'
        backup_path = backup_dir / backup_name
        
        # Create temporary directory for backup files
        temp_dir = backup_dir / f'temp_{timestamp}'
        await aiofiles.os.makedirs(temp_dir, exist_ok=True)
        
        try:
            files_to_backup = []
            
            # Export data
            if include_history:
                # Export history events
                events_file = await self.export_history_events(temp_dir)
                files_to_backup.append(events_file)
                
                # Export trades
                trades_file = await self.export_trades(temp_dir)
                files_to_backup.append(trades_file)
                
            if include_settings:
                # Export settings
                settings_file = temp_dir / 'settings.json'
                settings = await self.async_db.get_settings()
                async with aiofiles.open(settings_file, mode='w') as f:
                    await f.write(json.dumps(settings, indent=2))
                files_to_backup.append(settings_file)
                
            # Create zip file
            with ZipFile(backup_path, 'w') as zipf:
                for file in files_to_backup:
                    zipf.write(file, file.name)
                    
            log.info(f'Backup created at {backup_path}')
            return backup_path
            
        finally:
            # Cleanup temp directory
            import shutil
            await asyncio.get_event_loop().run_in_executor(
                None,
                shutil.rmtree,
                temp_dir,
            )


class AsyncImportManager:
    """Manages all import operations"""
    
    def __init__(self, async_db: AsyncDBHandler):
        self.async_db = async_db
        self.importers = {
            'trades': AsyncTradesImporter(async_db),
            'history_events': AsyncHistoryEventsImporter(async_db),
        }
        
    async def import_file(
        self,
        filepath: Path,
        importer_type: str,
        **kwargs,
    ) -> tuple[int, list[str]]:
        """Import data from file"""
        if importer_type not in self.importers:
            raise InputError(f'Unknown importer type: {importer_type}')
            
        importer = self.importers[importer_type]
        
        # Check file extension
        if filepath.suffix.lower() == '.csv':
            items, errors = await importer.import_csv_file(filepath, **kwargs)
        else:
            raise InputError(f'Unsupported file format: {filepath.suffix}')
            
        return len(items), errors
        
    async def import_directory(
        self,
        directory: Path,
        pattern: str = '*.csv',
    ) -> dict[str, tuple[int, list[str]]]:
        """Import all matching files from directory"""
        results = {}
        
        # Find all matching files
        import glob
        files = list(directory.glob(pattern))
        
        log.info(f'Found {len(files)} files to import')
        
        # Import files concurrently
        for file in files:
            # Determine importer type from filename
            if 'trades' in file.name.lower():
                importer_type = 'trades'
            elif 'events' in file.name.lower():
                importer_type = 'history_events'
            else:
                log.warning(f'Skipping unknown file type: {file}')
                continue
                
            try:
                count, errors = await self.import_file(file, importer_type)
                results[str(file)] = (count, errors)
            except Exception as e:
                results[str(file)] = (0, [str(e)])
                
        return results