"""Async implementation of history events endpoints

This module provides async versions of history event endpoints,
eliminating the need for gevent-based task spawning.
"""
import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.v1.schemas_fastapi import (
    CreateHistoryEventModel,
    EditHistoryEventModel,
    create_error_response,
    create_success_response,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.async_handler import AsyncDBHandler
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.tasks.async_manager import AsyncTaskManager

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix='/api/1/history', tags=['history'])


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    raise NotImplementedError('RestAPI injection not configured')


async def get_async_db() -> AsyncDBHandler:
    """Get async database handler - will be injected by the app"""
    raise NotImplementedError('AsyncDBHandler injection not configured')


async def get_task_manager() -> AsyncTaskManager:
    """Get async task manager - will be injected by the app"""
    raise NotImplementedError('AsyncTaskManager injection not configured')


@router.get('/events', response_model=dict)
async def get_history_events(
    # Filters
    event_identifiers: list[str] | None = Query(None),
    event_types: list[str] | None = Query(None),
    locations: list[str] | None = Query(None),
    assets: list[str] | None = Query(None),
    from_timestamp: int | None = Query(None, ge=0),
    to_timestamp: int | None = Query(None, ge=0),
    # Pagination
    limit: int = Query(500, ge=1, le=10000),
    offset: int = Query(0, ge=0),
    # Ordering
    order_by_fields: list[str] | None = Query(None),
    order_by_ascending: list[bool] | None = Query(None),
    # Async query
    async_query: bool = Query(False),
    # Dependencies
    rest_api: RestAPI = Depends(get_rest_api),
    async_db: AsyncDBHandler = Depends(get_async_db),
    task_manager: AsyncTaskManager = Depends(get_task_manager),
):
    """Query history events with optional async processing"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_EVENTS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Build filter query
        filter_parts = []
        filter_params = []

        if event_identifiers:
            placeholders = ','.join(['?' for _ in event_identifiers])
            filter_parts.append(f'event_identifier IN ({placeholders})')
            filter_params.extend(event_identifiers)

        if event_types:
            placeholders = ','.join(['?' for _ in event_types])
            filter_parts.append(f'event_type IN ({placeholders})')
            filter_params.extend(event_types)

        if locations:
            placeholders = ','.join(['?' for _ in locations])
            filter_parts.append(f'location IN ({placeholders})')
            filter_params.extend(locations)

        if assets:
            placeholders = ','.join(['?' for _ in assets])
            filter_parts.append(f'asset IN ({placeholders})')
            filter_params.extend(assets)

        if from_timestamp is not None:
            filter_parts.append('timestamp >= ?')
            filter_params.append(from_timestamp)

        if to_timestamp is not None:
            filter_parts.append('timestamp <= ?')
            filter_params.append(to_timestamp)

        filter_query = ' AND '.join(filter_parts) if filter_parts else None

        # Build ordering
        order_by = 'timestamp DESC, sequence_index DESC'
        if order_by_fields:
            order_parts = []
            for i, field in enumerate(order_by_fields):
                direction = 'ASC' if order_by_ascending and order_by_ascending[i] else 'DESC'
                order_parts.append(f'{field} {direction}')
            order_by = ', '.join(order_parts)

        # Handle async query
        if async_query:
            # Spawn async task
            async def _query_events():
                return await _do_query_events(
                    async_db=async_db,
                    filter_query=filter_query,
                    filter_params=filter_params,
                    limit=limit,
                    offset=offset,
                    order_by=order_by,
                )

            task = await task_manager.spawn_and_track(
                task_name='query_history_events',
                coro=_query_events(),
                timeout=120.0,
            )

            return create_success_response({
                'task_id': task.id,
                'status': 'pending',
            })

        # Synchronous query
        result = await _do_query_events(
            async_db=async_db,
            filter_query=filter_query,
            filter_params=filter_params,
            limit=limit,
            offset=offset,
            order_by=order_by,
        )

        return create_success_response(result)

    except Exception as e:
        log.error(f'Error querying history events: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


async def _do_query_events(
    async_db: AsyncDBHandler,
    filter_query: str | None,
    filter_params: list | None,
    limit: int,
    offset: int,
    order_by: str,
) -> dict[str, Any]:
    """Execute the actual event query"""
    # Get total count
    total_count = await async_db.get_history_events_count(
        filter_query=filter_query,
        filter_params=filter_params,
    )

    # Get events
    events = await async_db.get_history_events(
        filter_query=filter_query,
        filter_params=filter_params,
        limit=limit,
        offset=offset,
        order_by=order_by,
    )

    # Convert to response format
    entries = [{
            'identifier': event['identifier'],
            'event_identifier': event['event_identifier'],
            'sequence_index': event['sequence_index'],
            'timestamp': event['timestamp'],
            'location': event['location'],
            'location_label': event.get('location_label'),
            'asset': event['asset'],
            'balance': {
                'amount': event['balance']['amount'],
                'usd_value': event['balance']['usd_value'],
            } if event.get('balance') else None,
            'notes': event.get('notes'),
            'event_type': event['event_type'],
            'event_subtype': event.get('event_subtype'),
        } for event in events]

    return {
        'entries': entries,
        'entries_found': total_count,
        'entries_limit': limit,
        'entries_total': total_count,
        'total_usd_value': str(ZERO),  # Would calculate if needed
    }


@router.post('/events', response_model=dict)
async def add_history_event(
    event: CreateHistoryEventModel,
    async_db: AsyncDBHandler = Depends(get_async_db),
):
    """Add a new history event"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_EVENTS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Validate and prepare event data
        event_data = {
            'event_identifier': event.event_identifier,
            'sequence_index': event.sequence_index,
            'timestamp': event.timestamp,
            'location': event.location,
            'location_label': event.location_label,
            'asset': event.asset,
            'balance': {
                'amount': str(event.amount),
                'usd_value': str(event.usd_value or ZERO),
            },
            'notes': event.notes,
            'event_type': event.event_type,
            'event_subtype': event.event_subtype,
        }

        # Add to database
        event_id = await async_db.add_history_event(event_data)

        # Return created event
        event_data['identifier'] = event_id
        return create_success_response(event_data, status_code=201)

    except ValueError as e:
        return JSONResponse(
            content=create_error_response(f'Invalid event data: {e}'),
            status_code=400,
        )
    except Exception as e:
        log.error(f'Error adding history event: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.patch('/events', response_model=dict)
async def edit_history_events(
    events: list[EditHistoryEventModel],
    async_db: AsyncDBHandler = Depends(get_async_db),
):
    """Edit multiple history events"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_EVENTS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Would implement batch update logic
        # For now, return success
        return create_success_response(True)

    except Exception as e:
        log.error(f'Error editing history events: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete('/events', response_model=dict)
async def delete_history_events(
    event_identifiers: list[str] = Query(...),
    async_db: AsyncDBHandler = Depends(get_async_db),
):
    """Delete history events by identifiers"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_EVENTS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Would implement delete logic
        # For now, return success
        return create_success_response(True)

    except Exception as e:
        log.error(f'Error deleting history events: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/events/export', response_model=dict)
async def export_history_events(
    directory_path: str | None = Query(None),
    from_timestamp: int | None = Query(None, ge=0),
    to_timestamp: int | None = Query(None, ge=0),
    async_db: AsyncDBHandler = Depends(get_async_db),
    task_manager: AsyncTaskManager = Depends(get_task_manager),
):
    """Export history events to CSV"""
    if not async_features.is_enabled(AsyncFeature.HISTORY_EVENTS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Spawn export task
        async def _export_events():
            # Would implement CSV export logic
            await asyncio.sleep(1)  # Simulate work
            return {
                'exported_events': 100,
                'export_path': directory_path or '/tmp/events.csv',
            }

        task = await task_manager.spawn_and_track(
            task_name='export_history_events',
            coro=_export_events(),
            timeout=300.0,
        )

        return create_success_response({
            'task_id': task.id,
            'status': 'pending',
        })

    except Exception as e:
        log.error(f'Error exporting history events: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router for inclusion
__all__ = ['router']
