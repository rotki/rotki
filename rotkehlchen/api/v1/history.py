"""Async implementation of history processing endpoints

This module provides high-performance async history operations.
"""
import asyncio
import logging
from pathlib import Path
from typing import Any

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rotkehlchen.rotkehlchen import Rotkehlchen

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from rotkehlchen.api.v1.dependencies import get_rotkehlchen
from rotkehlchen.api.v1.schemas_fastapi import (
    create_error_response,
    create_success_response,
)
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.timing import TIMESTAMP_MAX_VALUE
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Location, Timestamp
from rotkehlchen.utils.misc import timestamp_to_date

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix='/api/1', tags=['history'])


# Pydantic models
class HistoryProcessingQuery(BaseModel):
    """Parameters for history processing"""
    from_timestamp: int = Field(0, ge=0)
    to_timestamp: int = Field(TIMESTAMP_MAX_VALUE, ge=0)
    async_query: bool = Field(default=True)


class HistoryExportQuery(BaseModel):
    """Parameters for history export"""
    directory_path: Path | None = None
    from_timestamp: int | None = Field(default=None, ge=0)
    to_timestamp: int | None = Field(default=None, ge=0)


class HistoryEventQuery(BaseModel):
    """Parameters for querying history events"""
    filter_query: dict | None = None
    async_query: bool = Field(default=False)


class CreateHistoryEvent(BaseModel):
    """Model for creating a history event"""
    event_identifier: str
    sequence_index: int
    timestamp: int = Field(..., ge=0)
    location: str
    event_type: str
    event_subtype: str | None = None
    asset: str
    amount: str
    usd_value: str | None = None
    notes: str | None = None
    location_label: str | None = None
    address: str | None = None
    transaction_hash: str | None = None


# Dependency injection
async def get_rotkehlchen() -> "Rotkehlchen":
    """Get Rotkehlchen instance - will be injected by the app"""
    raise NotImplementedError('Rotkehlchen injection not configured')


@router.get('/history/status', response_model=dict)
async def get_history_status(
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get status of history processing"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get processing status
        status = rotkehlchen.history_manager.get_history_status()

        return create_success_response({
            'processing': status.processing,
            'total_progress': f'{status.progress:.2f}%',
            'current_step': status.current_step,
        })

    except Exception as e:
        log.error(f'Error getting history status: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/history', response_model=dict)
async def process_history(
    query: HistoryProcessingQuery,
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Process history for given time range"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Validate time range
        if query.from_timestamp >= query.to_timestamp:
            return JSONResponse(
                content=create_error_response('from_timestamp must be less than to_timestamp'),
                status_code=400,
            )

        if query.async_query:
            # Spawn async task
            task = rotkehlchen.task_manager.spawn_task(
                task_name='process_history',
                method=rotkehlchen.process_history,
                from_timestamp=Timestamp(query.from_timestamp),
                to_timestamp=Timestamp(query.to_timestamp),
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous processing
        result = await asyncio.to_thread(
            rotkehlchen.process_history,
            from_timestamp=Timestamp(query.from_timestamp),
            to_timestamp=Timestamp(query.to_timestamp),
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error processing history: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/history/export', response_model=dict)
async def export_history(
    query: HistoryExportQuery,
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Export processed history to CSV files"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Use user directory if not specified
        if query.directory_path is None:
            query.directory_path = rotkehlchen.user_directory / 'exports'

        # Create directory if needed
        query.directory_path.mkdir(parents=True, exist_ok=True)

        # Export history
        from_ts = Timestamp(query.from_timestamp) if query.from_timestamp else Timestamp(0)
        to_ts = Timestamp(query.to_timestamp) if query.to_timestamp else Timestamp(TIMESTAMP_MAX_VALUE)

        exported_files = await asyncio.to_thread(
            rotkehlchen.history_exporter.export,
            directory=query.directory_path,
            from_timestamp=from_ts,
            to_timestamp=to_ts,
        )

        return create_success_response({
            'exported_files': [str(f) for f in exported_files],
            'directory': str(query.directory_path),
        })

    except Exception as e:
        log.error(f'Error exporting history: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/history/download', response_model=Any)
async def download_history(
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> Any:
    """Download exported history as zip file"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Create zip file
        import zipfile
        from tempfile import NamedTemporaryFile

        export_dir = rotkehlchen.user_directory / 'exports'

        with NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
            with zipfile.ZipFile(tmp_file, 'w') as zip_file:
                for file_path in export_dir.glob('*.csv'):
                    zip_file.write(file_path, file_path.name)

            return FileResponse(
                path=tmp_file.name,
                filename=f'rotki_history_{timestamp_to_date(Timestamp.now())}.zip',
                media_type='application/zip',
            )

    except Exception as e:
        log.error(f'Error downloading history: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/history/events', response_model=dict)
async def get_history_events(
    limit: int = Query(500, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    order_by_attribute: str | None = Query(default='timestamp'),
    ascending: bool = Query(default=False),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get history events"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Query events from database
        with rotkehlchen.data.db.conn.read_ctx() as cursor:
            events, total_count = rotkehlchen.data.db.get_history_events(
                cursor=cursor,
                limit=limit,
                offset=offset,
                order_by_attribute=order_by_attribute,
                ascending=ascending,
            )

        # Serialize events
        serialized_events = [event.serialize() for event in events]

        return create_success_response({
            'entries': serialized_events,
            'entries_found': len(serialized_events),
            'entries_limit': limit,
            'entries_total': total_count,
        })

    except Exception as e:
        log.error(f'Error getting history events: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/history/events', response_model=dict)
async def add_history_event(
    event_data: CreateHistoryEvent,
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Add a new history event"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Validate location
        try:
            location = Location.deserialize(event_data.location)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid location: {e}'),
                status_code=400,
            )

        # Validate event type
        try:
            event_type = HistoryEventType.deserialize(event_data.event_type)
        except Exception as e:
            return JSONResponse(
                content=create_error_response(f'Invalid event type: {e}'),
                status_code=400,
            )

        # Validate event subtype
        event_subtype = None
        if event_data.event_subtype:
            try:
                event_subtype = HistoryEventSubType.deserialize(event_data.event_subtype)
            except Exception as e:
                return JSONResponse(
                    content=create_error_response(f'Invalid event subtype: {e}'),
                    status_code=400,
                )

        # Create event
        event = HistoryEvent(
            event_identifier=event_data.event_identifier,
            sequence_index=event_data.sequence_index,
            timestamp=Timestamp(event_data.timestamp),
            location=location,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=Asset(event_data.asset),
            amount=FVal(event_data.amount),
            usd_value=FVal(event_data.usd_value) if event_data.usd_value else None,
            notes=event_data.notes,
            location_label=event_data.location_label,
            address=event_data.address,
            transaction_hash=event_data.transaction_hash,
        )

        # Add to database
        with rotkehlchen.data.db.user_write() as write_cursor:
            identifier = rotkehlchen.data.db.add_history_event(write_cursor, event)

        return create_success_response({
            'identifier': identifier,
            'entry': event.serialize(),
        })

    except Exception as e:
        log.error(f'Error adding history event: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.patch('/history/events', response_model=dict)
async def edit_history_event(
    event_data: dict = Body(...),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Edit an existing history event"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get event identifier
        identifier = event_data.get('identifier')
        if not identifier:
            return JSONResponse(
                content=create_error_response('identifier is required'),
                status_code=400,
            )

        # Update event in database
        with rotkehlchen.data.db.user_write() as write_cursor:
            success = rotkehlchen.data.db.edit_history_event(
                write_cursor,
                identifier=identifier,
                event_data=event_data,
            )

        if not success:
            return JSONResponse(
                content=create_error_response(f'Event with identifier {identifier} not found'),
                status_code=404,
            )

        return create_success_response({'result': True})

    except Exception as e:
        log.error(f'Error editing history event: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete('/history/events', response_model=dict)
async def delete_history_events(
    identifiers: list[int] = Body(...),
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Delete history events"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Delete events from database
        with rotkehlchen.data.db.user_write() as write_cursor:
            deleted_count = rotkehlchen.data.db.delete_history_events(
                write_cursor,
                identifiers=identifiers,
            )

        return create_success_response({
            'result': True,
            'deleted': deleted_count,
        })

    except Exception as e:
        log.error(f'Error deleting history events: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/history/actionable_items', response_model=dict)
async def get_actionable_items(
    rotkehlchen: "Rotkehlchen" = Depends(get_rotkehlchen),
) -> dict:
    """Get actionable items from history processing"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get actionable items
        items = await asyncio.to_thread(
            rotkehlchen.get_actionable_items,
        )

        return create_success_response(items)

    except Exception as e:
        log.error(f'Error getting actionable items: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']
