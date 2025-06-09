"""FastAPI resources to gradually replace Flask resources"""
import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from rotkehlchen.api.feature_flags import AsyncFeature, async_features, get_migration_metrics
from rotkehlchen.api.rest import RestAPI, process_result
from rotkehlchen.api.v1.schemas_fastapi import (
    AsyncQueryModel,
    AsyncTaskResponseModel,
    CreateHistoryEventModel,
    DatabaseInfoModel,
    EditHistoryEventModel,
    HistoryEventModel,
    PaginationModel,
    TimestampFilterModel,
    create_error_response,
    create_success_response,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    # This is a placeholder - actual implementation would get from app state
    raise NotImplementedError('RestAPI injection not configured')


async def require_logged_in_user():
    """Dependency to check if user is logged in"""
    # Placeholder - actual implementation would check auth
    # raise HTTPException(status_code=401, detail="No user is currently logged in")


# Create router
router = APIRouter(prefix='/api/1', tags=['v1'])


# Simple endpoints
@router.get('/ping', response_model=dict)
async def ping():
    """Simple ping endpoint - matches Flask implementation exactly"""
    if not async_features.is_enabled(AsyncFeature.PING_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    # Match Flask response exactly
    return {'result': True, 'message': ''}


@router.get('/info', response_model=dict)
async def get_info(
    check_for_updates: bool = Query(default=False),
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Get application information - async version of Flask endpoint"""
    if not async_features.is_enabled(AsyncFeature.INFO_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Run sync method in thread pool to avoid blocking
        loop = asyncio.get_event_loop()

        def _get_info():
            # This matches the Flask implementation
            result = rest_api.get_info(check_for_updates=check_for_updates)
            # Extract the actual data from the Flask Response
            if hasattr(result, 'json'):
                return result.json
            elif hasattr(result, 'get_json'):
                return result.get_json()
            else:
                # If it's already a dict, return it
                return result

        return await loop.run_in_executor(None, _get_info)

        # Return in same format as Flask

    except Exception as e:
        log.error(f'Error getting info: {e}')
        return JSONResponse(
            content={'result': None, 'message': str(e), 'error': True},
            status_code=500,
        )


# Database endpoints
@router.get('/database/info', dependencies=[Depends(require_logged_in_user)])
async def get_database_info(
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Get database information"""
    # Placeholder implementation
    db_info = DatabaseInfoModel(
        version=46,
        size=1024000,
        last_write_ts=1234567890,
        backup_path='/backups/latest.db',
    )
    return create_success_response(db_info.model_dump())


# Settings endpoints
@router.get('/settings', dependencies=[Depends(require_logged_in_user)], response_model=dict)
async def get_settings(
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Get current settings - async version"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        loop = asyncio.get_event_loop()

        def _get_settings():
            # Match Flask implementation
            with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
                settings = process_result(rest_api.rotkehlchen.get_settings(cursor))
                cache = rest_api.rotkehlchen.data.db.get_cache_for_api(cursor)
            return {'result': settings | cache, 'message': ''}

        return await loop.run_in_executor(None, _get_settings)

    except Exception as e:
        log.error(f'Error getting settings: {e}')
        return JSONResponse(
            content={'result': None, 'message': str(e), 'error': True},
            status_code=500,
        )


@router.patch('/settings', dependencies=[Depends(require_logged_in_user)], response_model=dict)
async def update_settings(
    settings: dict,  # Accept raw dict to match Flask
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Update settings - async version"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        loop = asyncio.get_event_loop()

        def _update_settings():
            # Call the Flask implementation
            result = rest_api.set_settings(settings)
            if hasattr(result, 'json'):
                return result.json
            elif hasattr(result, 'get_json'):
                return result.get_json()
            return result

        return await loop.run_in_executor(None, _update_settings)

    except Exception as e:
        log.error(f'Error updating settings: {e}')
        return JSONResponse(
            content={'result': None, 'message': str(e), 'error': True},
            status_code=500,
        )


# History events endpoints with async query support
@router.post('/history/events', dependencies=[Depends(require_logged_in_user)])
async def query_history_events(
    async_query: AsyncQueryModel,
    filters: TimestampFilterModel,
    pagination: PaginationModel,
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Query history events"""
    if async_query.async_query:
        # Start async task
        task_id = 'task_123'  # Would generate real task ID
        return create_success_response({
            'task_id': task_id,
            'status': 'pending',
        })

    # Synchronous query (placeholder)
    events = [
        HistoryEventModel(
            identifier=1,
            event_identifier='0x123',
            sequence_index=0,
            timestamp=1234567890,
            location='ethereum',
            event_type='deposit',
            asset='ETH',
            amount='1.5',
        ),
    ]

    return create_success_response({
        'entries': [e.model_dump() for e in events],
        'total': 1,
        'limit': pagination.limit,
        'offset': pagination.offset,
    })


@router.put('/history/events', dependencies=[Depends(require_logged_in_user)])
async def add_history_event(
    event: CreateHistoryEventModel,
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Add a new history event"""
    # Validate event data
    try:
        # Placeholder - would call rest_api.add_history_event()
        created_event = HistoryEventModel(
            identifier=999,
            **event.model_dump(),
        )
        return create_success_response(created_event.model_dump(), 201)
    except ValueError as e:
        return JSONResponse(
            content=create_error_response(f'Invalid event data: {e}', 400),
            status_code=400,
        )


@router.patch('/history/events', dependencies=[Depends(require_logged_in_user)])
async def edit_history_event(
    event: EditHistoryEventModel,
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Edit an existing history event"""
    # Placeholder - would call rest_api.edit_history_event()
    return create_success_response(event.model_dump())


# Async task status endpoint
@router.get('/tasks/{task_id}', dependencies=[Depends(require_logged_in_user)])
async def get_task_status(
    task_id: str,
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Get async task status"""
    # Placeholder - would check actual task status
    task_response = AsyncTaskResponseModel(
        result={
            'task_id': task_id,
            'status': 'completed',
            'result': {'data': 'example'},
        },
    )
    return task_response.model_dump()


# Helper to create migrated endpoints
def create_migrated_endpoint(flask_resource_class):
    """Create a FastAPI endpoint from a Flask resource class

    This helps with gradual migration by wrapping Flask resources
    """
    # This would analyze the Flask resource and create FastAPI equivalents
    # For now, it's a conceptual helper


# Migration management endpoints
@router.get('/async/features', response_model=dict)
async def get_async_features():
    """Get status of async feature flags"""
    return create_success_response(get_migration_metrics())


@router.put('/async/features/{feature}', response_model=dict)
async def toggle_async_feature(
    feature: str,
    enabled: bool = Query(...),
):
    """Toggle an async feature flag"""
    try:
        feature_enum = AsyncFeature(feature)
        if enabled:
            async_features.enable(feature_enum)
        else:
            async_features.disable(feature_enum)

        return create_success_response({
            'feature': feature,
            'enabled': enabled,
            'all_features': async_features.get_status(),
        })
    except ValueError:
        return JSONResponse(
            content=create_error_response(f'Unknown feature: {feature}', 400),
            status_code=400,
        )


# Export router for inclusion in main app
__all__ = ['router']
