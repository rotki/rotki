"""Async implementation of basic endpoints (ping, info, settings)

This module provides high-performance async implementations of basic endpoints.
"""
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.v1.schemas_fastapi import (
    AppInfoModel,
    EditSettingsModel,
    SettingsModel,
    create_error_response,
    create_success_response,
)
from rotkehlchen.constants.misc import APPNAME, ROTKEHLCHEN_SERVER_TIMEOUT
from rotkehlchen.db.settings import ModifiableDBSettings
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.version_check import get_current_version

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix="/api/1", tags=["base"])


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    raise NotImplementedError("RestAPI injection not configured")


@router.get("/ping", response_model=dict)
async def ping() -> dict:
    """Simple ping endpoint for health checks"""
    if not async_features.is_enabled(AsyncFeature.PING_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    return create_success_response({'result': True})


@router.get("/info", response_model=dict)
async def get_info(
    check_for_updates: bool = Query(default=False),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get application information"""
    if not async_features.is_enabled(AsyncFeature.INFO_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Get version info
        our_version = get_current_version()
        version_info = {
            'version': str(our_version.our_version),
            'latest_version': str(our_version.latest_version) if our_version.latest_version else None,
            'download_url': our_version.latest_version_download_url,
        }
        
        # Update version check if requested
        if check_for_updates:
            try:
                await rest_api.rotkehlchen.perform_version_check()
                # Re-fetch after check
                our_version = get_current_version()
                version_info['latest_version'] = str(our_version.latest_version) if our_version.latest_version else None
                version_info['download_url'] = our_version.latest_version_download_url
            except Exception as e:
                log.error(f"Failed to check for updates: {e}")
        
        # Get configuration info
        config_args = rest_api.rotkehlchen.args
        
        result = AppInfoModel(
            version=version_info['version'],
            latest_version=version_info['latest_version'],
            data_directory=str(rest_api.rotkehlchen.user_directory),
            log_level=logging.getLevelName(logging.root.level),
            accept_docker_risk=config_args.accept_docker_risk,
            backend_default_arguments={
                'max_logfiles_num': config_args.max_logfiles_num,
                'max_size_in_mb_all_logs': config_args.max_size_in_mb_all_logs,
                'sqlite_instructions': config_args.sqlite_instructions,
                'api_cors': config_args.api_cors,
                'api_port': config_args.rest_api_port,
                'api_host': config_args.api_host,
                'data_dir': str(config_args.data_dir),
                'log_dir': str(config_args.logfile),
                'log_from_other_modules': config_args.logfromothermodules,
            },
        )
        
        return create_success_response(result.dict())
        
    except Exception as e:
        log.error(f"Error getting app info: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/settings", response_model=dict)
async def get_settings(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get current settings"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Get settings from database
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            settings = rest_api.rotkehlchen.data.db.get_settings(cursor)
        
        # Convert to dict for response
        settings_dict = settings.serialize()
        
        return create_success_response(settings_dict)
        
    except Exception as e:
        log.error(f"Error getting settings: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put("/settings", response_model=dict)
async def update_settings(
    settings: EditSettingsModel,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Update settings"""
    if not async_features.is_enabled(AsyncFeature.SETTINGS_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response("No user is logged in"),
                status_code=401,
            )
        
        # Convert Pydantic model to ModifiableDBSettings
        settings_dict = settings.dict(exclude_unset=True)
        modifiable_settings = ModifiableDBSettings(**settings_dict)
        
        # Apply settings
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            rest_api.rotkehlchen.data.db.set_settings(write_cursor, modifiable_settings)
        
        # Get updated settings
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            updated_settings = rest_api.rotkehlchen.data.db.get_settings(cursor)
        
        # Update rotkehlchen instance
        rest_api.rotkehlchen.data.db.update_owned_assets_in_globaldb()
        
        return create_success_response(updated_settings.serialize())
        
    except Exception as e:
        log.error(f"Error updating settings: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get("/tasks", response_model=dict)
async def get_async_tasks(
    task_id: int | None = Query(default=None),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Query async task status"""
    if not async_features.is_enabled(AsyncFeature.TASK_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        if task_id is not None:
            # Get specific task
            result = rest_api.rotkehlchen.task_manager.query_task(task_id)
            if result is None:
                return JSONResponse(
                    content=create_error_response(f"No task with id {task_id} found"),
                    status_code=404,
                )
            
            return create_success_response({
                'id': task_id,
                'status': result['status'],
                'result': result.get('result'),
                'error': result.get('error'),
            })
        else:
            # Get all pending tasks
            pending = rest_api.rotkehlchen.task_manager.get_pending_tasks()
            completed = rest_api.rotkehlchen.task_manager.get_completed_tasks()
            
            return create_success_response({
                'pending': pending,
                'completed': completed,
            })
            
    except Exception as e:
        log.error(f"Error querying tasks: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete("/tasks/{task_id}", response_model=dict)
async def delete_async_task(
    task_id: int,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Cancel or delete an async task"""
    if not async_features.is_enabled(AsyncFeature.TASK_ENDPOINT):
        raise HTTPException(status_code=404, detail="Endpoint not migrated")
    
    try:
        success = rest_api.rotkehlchen.task_manager.delete_task(task_id)
        
        if not success:
            return JSONResponse(
                content=create_error_response(f"No task with id {task_id} found"),
                status_code=404,
            )
        
        return create_success_response({'result': True})
        
    except Exception as e:
        log.error(f"Error deleting task: {e}")
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']