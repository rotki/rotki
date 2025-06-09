"""Async implementation of database management endpoints

This module provides high-performance async database operations.
"""
import asyncio
import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from rotkehlchen.api.rest import RestAPI
from rotkehlchen.api.v1.schemas_fastapi import (
    create_error_response,
    create_success_response,
)
from rotkehlchen.errors.misc import DBUpgradeError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

router = APIRouter(prefix='/api/1', tags=['database'])


# Pydantic models
class DatabaseInfo(BaseModel):
    """Database information model"""
    version: int
    size: int
    last_write_ts: Timestamp
    backup_path: str | None = None


class DatabaseBackup(BaseModel):
    """Database backup request"""
    action: str = Field(..., regex='^(create|download|upload)$')
    path: Path | None = None


class TagData(BaseModel):
    """Tag data model"""
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1000)
    background_color: str = Field(..., regex='^#[0-9A-Fa-f]{6}$')
    foreground_color: str = Field(..., regex='^#[0-9A-Fa-f]{6}$')


# Dependency injection
async def get_rest_api() -> RestAPI:
    """Get RestAPI instance - will be injected by the app"""
    raise NotImplementedError('RestAPI injection not configured')


@router.get('/database/info', response_model=dict)
async def get_database_info(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get database information"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get database info
        db = rest_api.rotkehlchen.data.db
        info = DatabaseInfo(
            version=db.get_version(),
            size=db.get_db_size(),
            last_write_ts=db.get_last_write_ts(),
            backup_path=str(db.user_data_dir / 'backups') if db.user_data_dir else None,
        )

        return create_success_response(info.dict())

    except Exception as e:
        log.error(f'Error getting database info: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/database/backups', response_model=dict)
async def manage_database_backup(
    action: str = Query(..., regex='^(create|download)$'),
    rest_api: RestAPI = Depends(get_rest_api),
) -> Any:
    """Create or download database backup"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        if action == 'create':
            # Create backup
            backup_path = await asyncio.to_thread(
                rest_api.rotkehlchen.data.db.create_backup,
            )

            return create_success_response({
                'result': True,
                'backup_path': str(backup_path),
            })

        elif action == 'download':
            # Create and download backup
            with TemporaryDirectory() as temp_dir:
                backup_path = await asyncio.to_thread(
                    rest_api.rotkehlchen.data.db.create_backup,
                    directory=Path(temp_dir),
                )

                return FileResponse(
                    path=backup_path,
                    filename=backup_path.name,
                    media_type='application/octet-stream',
                )

    except Exception as e:
        log.error(f'Error managing database backup: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/database/backups/upload', response_model=dict)
async def upload_database_backup(
    file: UploadFile = File(...),
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Upload and restore database backup"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Save uploaded file
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / (file.filename or 'backup.db')

            content = await file.read()
            temp_path.write_bytes(content)

            # Restore from backup
            await asyncio.to_thread(
                rest_api.rotkehlchen.data.db.restore_backup,
                backup_path=temp_path,
            )

        return create_success_response({'result': True})

    except DBUpgradeError as e:
        return JSONResponse(
            content=create_error_response(f'Database upgrade required: {e}'),
            status_code=426,
        )
    except Exception as e:
        log.error(f'Error restoring database backup: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.get('/tags', response_model=dict)
async def get_tags(
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Get all tags"""
    if not async_features.is_enabled(AsyncFeature.TAGS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Get tags from database
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            tags_data = rest_api.rotkehlchen.data.db.get_tags(cursor)

        # Format response
        tags = {}
        for tag_name, tag_data in tags_data.items():
            tags[tag_name] = {
                'name': tag_name,
                'description': tag_data.description,
                'background_color': tag_data.background_color,
                'foreground_color': tag_data.foreground_color,
            }

        return create_success_response(tags)

    except Exception as e:
        log.error(f'Error getting tags: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.put('/tags', response_model=dict)
async def add_tag(
    tag: TagData,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Add a new tag"""
    if not async_features.is_enabled(AsyncFeature.TAGS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Check if tag already exists
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            existing_tags = rest_api.rotkehlchen.data.db.get_tags(cursor)

        if tag.name in existing_tags:
            return JSONResponse(
                content=create_error_response(f"Tag '{tag.name}' already exists"),
                status_code=409,
            )

        # Add tag to database
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            rest_api.rotkehlchen.data.db.add_tag(
                write_cursor,
                name=tag.name,
                description=tag.description,
                background_color=tag.background_color,
                foreground_color=tag.foreground_color,
            )

        return create_success_response({tag.name: tag.dict()})

    except Exception as e:
        log.error(f'Error adding tag: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.patch('/tags/{name}', response_model=dict)
async def edit_tag(
    name: str,
    tag: TagData,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Edit an existing tag"""
    if not async_features.is_enabled(AsyncFeature.TAGS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Check if tag exists
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            existing_tags = rest_api.rotkehlchen.data.db.get_tags(cursor)

        if name not in existing_tags:
            return JSONResponse(
                content=create_error_response(f"Tag '{name}' not found"),
                status_code=404,
            )

        # Edit tag in database
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            rest_api.rotkehlchen.data.db.edit_tag(
                write_cursor,
                old_name=name,
                new_name=tag.name,
                description=tag.description,
                background_color=tag.background_color,
                foreground_color=tag.foreground_color,
            )

        return create_success_response({tag.name: tag.dict()})

    except Exception as e:
        log.error(f'Error editing tag: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.delete('/tags/{name}', response_model=dict)
async def delete_tag(
    name: str,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Delete a tag"""
    if not async_features.is_enabled(AsyncFeature.TAGS_ENDPOINT):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Check if tag exists
        with rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
            existing_tags = rest_api.rotkehlchen.data.db.get_tags(cursor)

        if name not in existing_tags:
            return JSONResponse(
                content=create_error_response(f"Tag '{name}' not found"),
                status_code=404,
            )

        # Delete tag from database
        with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
            rest_api.rotkehlchen.data.db.delete_tag(write_cursor, name)

        return create_success_response({'result': True})

    except Exception as e:
        log.error(f'Error deleting tag: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


@router.post('/cache/{cache_type}/clear', response_model=dict)
async def clear_cache(
    cache_type: str,
    rest_api: RestAPI = Depends(get_rest_api),
) -> dict:
    """Clear various caches"""
    if not async_features.is_enabled(AsyncFeature.DATABASE_ENDPOINTS):
        raise HTTPException(status_code=404, detail='Endpoint not migrated')

    try:
        # Check authentication
        if not rest_api.rotkehlchen.user_is_logged_in:
            return JSONResponse(
                content=create_error_response('No user is logged in'),
                status_code=401,
            )

        # Clear cache based on type
        if cache_type == 'icons':
            await asyncio.to_thread(
                rest_api.rotkehlchen.icon_manager.clear_cache,
            )
        elif cache_type == 'avatars':
            await asyncio.to_thread(
                rest_api.rotkehlchen.avatars_manager.clear_cache,
            )
        elif cache_type == 'history':
            with rest_api.rotkehlchen.data.db.user_write() as write_cursor:
                rest_api.rotkehlchen.data.db.clear_history_cache(write_cursor)
        else:
            return JSONResponse(
                content=create_error_response(f'Unknown cache type: {cache_type}'),
                status_code=400,
            )

        return create_success_response({'result': True})

    except Exception as e:
        log.error(f'Error clearing cache: {e}')
        return JSONResponse(
            content=create_error_response(str(e)),
            status_code=500,
        )


# Export router
__all__ = ['router']
