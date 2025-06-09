"""FastAPI resources to gradually replace Flask resources"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.v1.schemas_fastapi import (
    AppInfoModel,
    AppInfoResponseModel,
    AsyncQueryModel,
    AsyncTaskResponseModel,
    CreateHistoryEventModel,
    DatabaseInfoModel,
    EditHistoryEventModel,
    EditSettingsModel,
    HistoryEventModel,
    PaginationModel,
    PingResponseModel,
    SettingsModel,
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
    raise NotImplementedError("RestAPI injection not configured")


async def require_logged_in_user():
    """Dependency to check if user is logged in"""
    # Placeholder - actual implementation would check auth
    # raise HTTPException(status_code=401, detail="No user is currently logged in")
    pass


# Create router
router = APIRouter(prefix="/api/1", tags=["v1"])


# Simple endpoints
@router.get("/ping", response_model=PingResponseModel)
async def ping():
    """Simple ping endpoint"""
    return create_success_response({"status": "pong"})


@router.get("/info", response_model=AppInfoResponseModel)
async def get_info(
    check_for_updates: bool = Query(default=False),
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Get application information"""
    # Adapt sync RestAPI method to async
    # In real implementation, RestAPI methods would be made async
    try:
        # For now, simulate the response
        info = AppInfoModel(
            version="1.35.0",
            latest_version="1.35.0" if check_for_updates else None,
            data_directory="/home/user/.rotki",
            log_level="debug",
            accept_docker_risk=False,
            backend_default_arguments={},
        )
        return create_success_response(info.model_dump())
    except Exception as e:
        log.error(f"Error getting info: {e}")
        return JSONResponse(
            content=create_error_response(str(e), 500),
            status_code=500,
        )


# Database endpoints
@router.get("/database/info", dependencies=[Depends(require_logged_in_user)])
async def get_database_info(
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Get database information"""
    # Placeholder implementation
    db_info = DatabaseInfoModel(
        version=46,
        size=1024000,
        last_write_ts=1234567890,
        backup_path="/backups/latest.db",
    )
    return create_success_response(db_info.model_dump())


# Settings endpoints
@router.get("/settings", dependencies=[Depends(require_logged_in_user)])
async def get_settings(
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Get current settings"""
    # Placeholder - would call rest_api.get_settings()
    settings = SettingsModel()
    return create_success_response(settings.model_dump())


@router.patch("/settings", dependencies=[Depends(require_logged_in_user)])
async def update_settings(
    settings: EditSettingsModel,
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Update settings"""
    # Validate and update only provided fields
    update_data = settings.model_dump(exclude_unset=True)
    if not update_data:
        return JSONResponse(
            content=create_error_response("No settings to update", 400),
            status_code=400,
        )
    
    # Placeholder - would call rest_api.update_settings()
    return create_success_response({"updated": list(update_data.keys())})


# History events endpoints with async query support
@router.post("/history/events", dependencies=[Depends(require_logged_in_user)])
async def query_history_events(
    async_query: AsyncQueryModel,
    filters: TimestampFilterModel,
    pagination: PaginationModel,
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Query history events"""
    if async_query.async_query:
        # Start async task
        task_id = "task_123"  # Would generate real task ID
        return create_success_response({
            "task_id": task_id,
            "status": "pending",
        })
    
    # Synchronous query (placeholder)
    events = [
        HistoryEventModel(
            identifier=1,
            event_identifier="0x123",
            sequence_index=0,
            timestamp=1234567890,
            location="ethereum",
            event_type="deposit",
            asset="ETH",
            amount="1.5",
        )
    ]
    
    return create_success_response({
        "entries": [e.model_dump() for e in events],
        "total": 1,
        "limit": pagination.limit,
        "offset": pagination.offset,
    })


@router.put("/history/events", dependencies=[Depends(require_logged_in_user)])
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
            **event.model_dump()
        )
        return create_success_response(created_event.model_dump(), 201)
    except ValueError as e:
        return JSONResponse(
            content=create_error_response(f"Invalid event data: {e}", 400),
            status_code=400,
        )


@router.patch("/history/events", dependencies=[Depends(require_logged_in_user)])
async def edit_history_event(
    event: EditHistoryEventModel,
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Edit an existing history event"""
    # Placeholder - would call rest_api.edit_history_event()
    return create_success_response(event.model_dump())


# Async task status endpoint
@router.get("/tasks/{task_id}", dependencies=[Depends(require_logged_in_user)])
async def get_task_status(
    task_id: str,
    rest_api: RestAPI = Depends(get_rest_api),
):
    """Get async task status"""
    # Placeholder - would check actual task status
    task_response = AsyncTaskResponseModel(
        result={
            "task_id": task_id,
            "status": "completed",
            "result": {"data": "example"},
        }
    )
    return task_response.model_dump()


# Helper to create migrated endpoints
def create_migrated_endpoint(flask_resource_class):
    """Create a FastAPI endpoint from a Flask resource class
    
    This helps with gradual migration by wrapping Flask resources
    """
    # This would analyze the Flask resource and create FastAPI equivalents
    # For now, it's a conceptual helper
    pass


# Export router for inclusion in main app
__all__ = ['router']