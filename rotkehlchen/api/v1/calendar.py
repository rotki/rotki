"""Async implementation of calendar and reminder endpoints

This module provides high-performance async calendar and reminder operations.
"""
import asyncio
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.v1.schemas_fastapi import (
    create_error_response,
    create_success_response,
)
from rotkehlchen.errors.api import APIError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix="/api/1", tags=["calendar"])


# Pydantic models
class CalendarEntry(BaseModel):
    """Data for calendar entries"""
    name: str
    description: Optional[str] = None
    timestamp: int = Field(..., ge=0)
    color: Optional[str] = None


class CalendarUpdate(BaseModel):
    """Data for updating calendar entries"""
    identifier: int
    name: Optional[str] = None
    description: Optional[str] = None
    timestamp: Optional[int] = Field(default=None, ge=0)
    color: Optional[str] = None


class CalendarReminderData(BaseModel):
    """Data for calendar reminders"""
    calendar_id: int
    secs_before: int = Field(..., ge=0)


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    raise NotImplementedError("RestAPI injection not configured")


@router.get("/calendar", response_model=dict)
async def get_calendar_entries(
    from_timestamp: Optional[int] = Query(default=None, ge=0),
    to_timestamp: Optional[int] = Query(default=None, ge=0),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get calendar entries"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get calendar entries
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            entries = rest_api.rotkehlchen.data.db.get_calendar_entries(
                cursor,
                from_timestamp=Timestamp(from_timestamp) if from_timestamp else None,
                to_timestamp=Timestamp(to_timestamp) if to_timestamp else None,
            )
        
        # Format response
        result = []
        for entry in entries:
            result.append({
                'identifier': entry.identifier,
                'name': entry.name,
                'description': entry.description,
                'timestamp': entry.timestamp,
                'color': entry.color,
            })
        
        return create_success_response({'entries': result})
        
    except Exception as e:
        log.error(f"Error getting calendar entries: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put("/calendar", response_model=dict)
async def add_calendar_entry(
    entry_data: CalendarEntry,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Add a calendar entry"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Add calendar entry
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            identifier = rest_api.rotkehlchen.data.db.add_calendar_entry(
                write_cursor,
                name=entry_data.name,
                description=entry_data.description,
                timestamp=Timestamp(entry_data.timestamp),
                color=entry_data.color,
            )
        
        return create_success_response({
            'identifier': identifier,
            'entry': {
                'identifier': identifier,
                'name': entry_data.name,
                'description': entry_data.description,
                'timestamp': entry_data.timestamp,
                'color': entry_data.color,
            }
        })
        
    except Exception as e:
        log.error(f"Error adding calendar entry: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.patch("/calendar", response_model=dict)
async def update_calendar_entry(
    update_data: CalendarUpdate,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Update a calendar entry"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Update calendar entry
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            success = rest_api.rotkehlchen.data.db.update_calendar_entry(
                write_cursor,
                identifier=update_data.identifier,
                name=update_data.name,
                description=update_data.description,
                timestamp=Timestamp(update_data.timestamp) if update_data.timestamp else None,
                color=update_data.color,
            )
        
        if not success:
            return JSONResponse(
                content=create_error_response(f"Calendar entry {update_data.identifier} not found"),
                status_code=404,
            )
        
        return create_success_response({'result': True})
        
    except Exception as e:
        log.error(f"Error updating calendar entry: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete("/calendar", response_model=dict)
async def delete_calendar_entries(
    identifiers: list[int] = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Delete calendar entries"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Delete calendar entries
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            deleted_count = rest_api.rotkehlchen.data.db.delete_calendar_entries(
                write_cursor,
                identifiers=identifiers,
            )
        
        return create_success_response({
            'result': True,
            'deleted': deleted_count,
        })
        
    except Exception as e:
        log.error(f"Error deleting calendar entries: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/calendar", response_model=dict)
async def create_calendar_from_history(
    query_data: dict = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Create calendar entries from history events"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Create entries from history
        created_entries = await asyncio.to_thread(
            rest_api.rotkehlchen.create_calendar_from_history,
            query_data=query_data,
        )
        
        return create_success_response({
            'entries': created_entries,
            'created': len(created_entries),
        })
        
    except Exception as e:
        log.error(f"Error creating calendar from history: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/calendar/reminders", response_model=dict)
async def get_calendar_reminders(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get calendar reminders"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get reminders
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            reminders = rest_api.rotkehlchen.data.db.get_calendar_reminders(cursor)
        
        # Format response
        result = []
        for reminder in reminders:
            result.append({
                'identifier': reminder.identifier,
                'calendar_id': reminder.calendar_id,
                'secs_before': reminder.secs_before,
            })
        
        return create_success_response({'entries': result})
        
    except Exception as e:
        log.error(f"Error getting calendar reminders: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put("/calendar/reminders", response_model=dict)
async def add_calendar_reminder(
    reminder_data: CalendarReminderData,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Add a calendar reminder"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Add reminder
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            identifier = rest_api.rotkehlchen.data.db.add_calendar_reminder(
                write_cursor,
                calendar_id=reminder_data.calendar_id,
                secs_before=reminder_data.secs_before,
            )
        
        return create_success_response({
            'identifier': identifier,
            'reminder': {
                'identifier': identifier,
                'calendar_id': reminder_data.calendar_id,
                'secs_before': reminder_data.secs_before,
            }
        })
        
    except Exception as e:
        log.error(f"Error adding calendar reminder: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.patch("/calendar/reminders", response_model=dict)
async def update_calendar_reminder(
    reminder_data: dict = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Update a calendar reminder"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Update reminder
        identifier = reminder_data.get('identifier')
        if not identifier:
            return JSONResponse(
                content=create_error_response("identifier is required"),
                status_code=400,
            )
        
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            success = rest_api.rotkehlchen.data.db.update_calendar_reminder(
                write_cursor,
                identifier=identifier,
                secs_before=reminder_data.get('secs_before'),
            )
        
        if not success:
            return JSONResponse(
                content=create_error_response(f"Calendar reminder {identifier} not found"),
                status_code=404,
            )
        
        return create_success_response({'result': True})
        
    except Exception as e:
        log.error(f"Error updating calendar reminder: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete("/calendar/reminders", response_model=dict)
async def delete_calendar_reminders(
    identifiers: list[int] = Body(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Delete calendar reminders"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Delete reminders
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            deleted_count = rest_api.rotkehlchen.data.db.delete_calendar_reminders(
                write_cursor,
                identifiers=identifiers,
            )
        
        return create_success_response({
            'result': True,
            'deleted': deleted_count,
        })
        
    except Exception as e:
        log.error(f"Error deleting calendar reminders: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post("/calendar/reminders", response_model=dict)
async def process_calendar_reminders(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Process due calendar reminders"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Process reminders
        processed = await asyncio.to_thread(
            rest_api.rotkehlchen.process_calendar_reminders,
        )
        
        return create_success_response({
            'processed': processed,
        })
        
    except Exception as e:
        log.error(f"Error processing calendar reminders: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']